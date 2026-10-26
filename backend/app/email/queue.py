"""Email queue: schedule, dispatch and retry email jobs.
Runs a background APScheduler process that survives app restarts via DB persistence.
"""
from __future__ import annotations
import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.email.config import get_email_config
from app.email.models import (
    EmailAutomationRule, EmailCategory, EmailJob, EmailLog,
    EmailStatus, EmailSuppression, EmailTemplate
)
from app.email.service import render_template, send_email, validate_email

logger = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="UTC")
    return _scheduler


def start_scheduler() -> None:
    sched = get_scheduler()
    if not sched.running:
        sched.add_job(_process_due_jobs, "interval", minutes=1, id="email_worker", replace_existing=True)
        sched.add_job(_process_retries, "interval", minutes=2, id="email_retries", replace_existing=True)
        sched.start()
        logger.info("[EMAIL] Scheduler started")


def stop_scheduler() -> None:
    sched = get_scheduler()
    if sched.running:
        sched.shutdown(wait=False)


# ─── Core scheduling helpers ──────────────────────────────────────────────────

def _idempotency_key(category: EmailCategory, candidate_id: str, extra: str = "") -> str:
    return f"{category.value}:{candidate_id}:{extra}"


def is_suppressed(email: str, category: EmailCategory, db: Session) -> bool:
    return bool(
        db.query(EmailSuppression).filter(
            EmailSuppression.email == email.lower(),
            (EmailSuppression.category == category) | (EmailSuppression.category.is_(None))
        ).first()
    )


def schedule_email(
    *,
    category: EmailCategory,
    to_email: str,
    to_name: str | None,
    context_vars: dict,
    candidate_id: str | None = None,
    assignment_id: str | None = None,
    recruiter_id: str | None = None,
    delay_hours: int = 0,
    db: Session,
    idempotency_suffix: str = "",
    force_simulate: bool = False,
) -> EmailJob | None:
    """
    Create a pending EmailJob from a template. Returns None if suppressed,
    duplicate, or automation disabled.
    """
    if not validate_email(to_email):
        logger.warning("[EMAIL] Invalid email skipped: %s", to_email)
        return None

    # Check automation rule
    rule = db.query(EmailAutomationRule).filter_by(category=category).first()
    if rule and not rule.enabled:
        return None

    # Suppression check
    if is_suppressed(to_email, category, db):
        logger.info("[EMAIL] Suppressed: %s %s", category.value, to_email)
        return None

    # Idempotency - prevent duplicate jobs
    ikey = _idempotency_key(category, candidate_id or to_email, idempotency_suffix)
    existing = db.query(EmailJob).filter_by(idempotency_key=ikey).filter(
        EmailJob.status.notin_([EmailStatus.failed, EmailStatus.cancelled])
    ).first()
    if existing:
        logger.info("[EMAIL] Duplicate prevented: %s", ikey)
        return existing

    # Fetch template
    tpl: EmailTemplate | None = db.query(EmailTemplate).filter_by(category=category, enabled=True).first()
    if not tpl:
        logger.warning("[EMAIL] No enabled template for category: %s", category.value)
        return None

    # Render
    subject = render_template(tpl.subject, context_vars)
    html_body = render_template(tpl.html_body, context_vars)
    text_body = render_template(tpl.text_body, context_vars)

    cfg = get_email_config()
    scheduled_at = None
    actual_delay = delay_hours if delay_hours >= 0 else (rule.delay_hours if rule else 0)
    if actual_delay > 0:
        scheduled_at = (datetime.now(timezone.utc) + timedelta(hours=actual_delay)).replace(tzinfo=None)

    job = EmailJob(
        id=str(uuid.uuid4()),
        idempotency_key=ikey,
        template_id=tpl.id,
        category=category,
        status=EmailStatus.queued,
        to_email=to_email.lower().strip(),
        to_name=to_name,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        context_vars=context_vars,
        candidate_id=candidate_id,
        assignment_id=assignment_id,
        recruiter_id=recruiter_id,
        scheduled_at=scheduled_at,
        is_simulated=force_simulate or cfg.demo_mode,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    if not scheduled_at:
        # Fire immediately in background (safe in both async app and sync test contexts)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_send_job(job.id))
        except RuntimeError:
            pass  # Not in an async context (e.g., tests); scheduler will pick it up

    return job


# ─── High-level workflow helpers ──────────────────────────────────────────────

def schedule_assessment_invitation(
    *, to_email: str, to_name: str, candidate_id: str, job_role: str,
    assessment_title: str, deadline: str, assessment_link: str,
    meeting_link: str = "https://meet.google.com/xyz-voice-hire",
    support_contact: str = "support@voicehire.ai",
    assignment_id: str | None = None, db: Session,
) -> EmailJob | None:
    return schedule_email(
        category=EmailCategory.assessment_invitation,
        to_email=to_email, to_name=to_name, candidate_id=candidate_id,
        assignment_id=assignment_id, db=db,
        context_vars=dict(
            candidate_name=to_name, job_role=job_role, assessment_title=assessment_title,
            deadline=deadline, assessment_link=assessment_link, meeting_link=meeting_link,
            support_contact=support_contact
        ),
    )


def schedule_assessment_reminder(
    *, to_email: str, to_name: str, candidate_id: str, job_role: str,
    assessment_title: str, deadline: str, assessment_link: str,
    meeting_link: str = "https://meet.google.com/xyz-voice-hire",
    assignment_id: str | None = None, db: Session, delay_hours: int = 48,
) -> EmailJob | None:
    return schedule_email(
        category=EmailCategory.assessment_reminder,
        to_email=to_email, to_name=to_name, candidate_id=candidate_id,
        assignment_id=assignment_id, db=db, delay_hours=delay_hours,
        context_vars=dict(
            candidate_name=to_name, job_role=job_role, assessment_title=assessment_title,
            deadline=deadline, assessment_link=assessment_link, meeting_link=meeting_link
        ),
        idempotency_suffix=assessment_title,
    )


def schedule_submission_confirmation(
    *, to_email: str, to_name: str, candidate_id: str,
    assessment_title: str, submission_datetime: str, repo_url: str,
    assignment_ref: str, db: Session,
) -> EmailJob | None:
    return schedule_email(
        category=EmailCategory.submission_confirmation,
        to_email=to_email, to_name=to_name, candidate_id=candidate_id, db=db,
        context_vars=dict(candidate_name=to_name, assessment_title=assessment_title,
                         submission_datetime=submission_datetime, repo_url=repo_url, assignment_ref=assignment_ref),
        idempotency_suffix=assignment_ref,
    )


def schedule_interview_invitation(
    *, to_email: str, to_name: str, candidate_id: str, job_role: str,
    interview_datetime: str, timezone_str: str, interviewer_name: str,
    meeting_link: str, interview_instructions: str = "Please join on time.",
    db: Session,
) -> EmailJob | None:
    return schedule_email(
        category=EmailCategory.interview_invitation,
        to_email=to_email, to_name=to_name, candidate_id=candidate_id, db=db,
        context_vars=dict(candidate_name=to_name, job_role=job_role, interview_datetime=interview_datetime,
                         timezone=timezone_str, interviewer_name=interviewer_name,
                         meeting_link=meeting_link, interview_instructions=interview_instructions),
    )


def cancel_reminder_for_assignment(assignment_id: str, db: Session) -> int:
    """Cancel pending reminders when an assignment is completed/cancelled."""
    jobs = db.query(EmailJob).filter_by(
        assignment_id=assignment_id,
        category=EmailCategory.assessment_reminder,
        status=EmailStatus.queued,
    ).all()
    for job in jobs:
        job.status = EmailStatus.cancelled
    db.commit()
    return len(jobs)


# ─── Background workers ───────────────────────────────────────────────────────

async def _send_job(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.query(EmailJob).filter_by(id=job_id).first()
        if not job or job.status == EmailStatus.cancelled:
            return
        await send_email(job, db)
        db.commit()
    except Exception as exc:
        logger.error("[EMAIL WORKER] job=%s error=%s", job_id, str(exc)[:200])
    finally:
        db.close()


async def _process_due_jobs() -> None:
    """Pick up queued jobs whose scheduled_at is now."""
    now = datetime.utcnow()
    db = SessionLocal()
    try:
        due = db.query(EmailJob).filter(
            EmailJob.status == EmailStatus.queued,
            (EmailJob.scheduled_at.is_(None)) | (EmailJob.scheduled_at <= now),
        ).limit(50).all()
        for job in due:
            await send_email(job, db)
        if due:
            db.commit()
    except Exception as exc:
        logger.error("[EMAIL WORKER] process error: %s", str(exc)[:200])
    finally:
        db.close()


async def _process_retries() -> None:
    """Retry jobs ready for their next attempt."""
    now = datetime.utcnow()
    db = SessionLocal()
    try:
        ready = db.query(EmailJob).filter(
            EmailJob.status == EmailStatus.retrying,
            EmailJob.next_retry_at <= now,
        ).limit(20).all()
        for job in ready:
            await send_email(job, db)
        if ready:
            db.commit()
    except Exception as exc:
        logger.error("[EMAIL RETRY WORKER] error: %s", str(exc)[:200])
    finally:
        db.close()
