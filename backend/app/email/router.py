"""FastAPI router for /api/emails - full email center API."""
from __future__ import annotations
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.email.config import get_email_config
from app.email.importer import process_import
from app.email.models import (
    CandidateImport, EmailAutomationRule, EmailCategory, EmailJob,
    EmailLog, EmailStatus, EmailSuppression, EmailTemplate
)
from app.email.queue import (
    cancel_reminder_for_assignment, schedule_assessment_invitation,
    schedule_assessment_reminder, schedule_email,
    schedule_interview_invitation, schedule_submission_confirmation,
)
from app.email.service import render_template, send_email, validate_email
from app.voice.deps import VoiceUser, get_voice_user

router = APIRouter(prefix="/api/emails", tags=["emails"])


def _require_recruiter(u: VoiceUser = Depends(get_voice_user)) -> VoiceUser:
    if u.role != "recruiter":
        raise HTTPException(403, "Recruiter access required")
    return u


# ─── SMTP health/config ───────────────────────────────────────────────────────

@router.get("/config")
def get_smtp_config(_: VoiceUser = Depends(_require_recruiter)):
    """Return safe SMTP config (no password)."""
    return get_email_config().smtp_info


@router.post("/test-smtp")
async def test_smtp(_: VoiceUser = Depends(_require_recruiter)):
    """Try to connect to SMTP and return result (no credentials in response)."""
    cfg = get_email_config()
    if cfg.demo_mode:
        return {"ok": True, "message": "Demo mode – SMTP not used. Set EMAIL_DEMO_MODE=false for real sends."}
    try:
        import aiosmtplib
        smtp = aiosmtplib.SMTP(hostname=cfg.smtp_host, port=cfg.smtp_port)
        await smtp.connect()
        if cfg.smtp_use_tls:
            await smtp.starttls()
        await smtp.login(cfg.smtp_username, cfg.smtp_password)
        await smtp.quit()
        return {"ok": True, "message": "SMTP connection and authentication succeeded."}
    except Exception as exc:
        return {"ok": False, "message": str(exc)[:300]}


class TestEmailRequest(BaseModel):
    to_email: str
    to_name: str = "Test Recipient"


@router.post("/send-test")
async def send_test_email(body: TestEmailRequest, u: VoiceUser = Depends(_require_recruiter), db: Session = Depends(get_db)):
    if not validate_email(body.to_email):
        raise HTTPException(400, "Invalid email address")
    job = schedule_email(
        category=EmailCategory.test,
        to_email=body.to_email, to_name=body.to_name,
        context_vars={"candidate_name": body.to_name, "job_role": "Test", "assessment_title": "Test",
                      "deadline": "N/A", "assessment_link": "#", "support_contact": "test@voicehire.ai"},
        recruiter_id=u.user_id, db=db,
        idempotency_suffix=str(uuid.uuid4()),  # always unique for test
    )
    return {"queued": True, "job_id": job.id if job else None}


# ─── Templates ────────────────────────────────────────────────────────────────

@router.get("/templates")
def list_templates(_: VoiceUser = Depends(_require_recruiter), db: Session = Depends(get_db)):
    tpls = db.query(EmailTemplate).all()
    return [{"id": t.id, "category": t.category, "name": t.name, "subject": t.subject,
             "enabled": t.enabled, "variables": t.variables, "updated_at": t.updated_at} for t in tpls]


@router.get("/templates/{template_id}")
def get_template(template_id: str, _: VoiceUser = Depends(_require_recruiter), db: Session = Depends(get_db)):
    t = db.query(EmailTemplate).get(template_id)
    if not t:
        raise HTTPException(404)
    return {"id": t.id, "category": t.category, "name": t.name, "subject": t.subject,
            "html_body": t.html_body, "text_body": t.text_body,
            "enabled": t.enabled, "variables": t.variables}


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    html_body: Optional[str] = None
    text_body: Optional[str] = None
    enabled: Optional[bool] = None


@router.patch("/templates/{template_id}")
def update_template(template_id: str, body: TemplateUpdate,
                    _: VoiceUser = Depends(_require_recruiter), db: Session = Depends(get_db)):
    t = db.query(EmailTemplate).get(template_id)
    if not t:
        raise HTTPException(404)
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(t, field, val)
    db.commit()
    return {"ok": True}


class PreviewRequest(BaseModel):
    template_id: str
    context_vars: dict = {}


@router.post("/templates/preview")
def preview_template(body: PreviewRequest, _: VoiceUser = Depends(_require_recruiter), db: Session = Depends(get_db)):
    t = db.query(EmailTemplate).get(body.template_id)
    if not t:
        raise HTTPException(404)
    ctx = {v: f"[{v}]" for v in (t.variables or [])}
    ctx.update(body.context_vars)
    return {
        "subject": render_template(t.subject, ctx),
        "html_body": render_template(t.html_body, ctx),
        "text_body": render_template(t.text_body, ctx),
    }


# ─── Automation rules ─────────────────────────────────────────────────────────

@router.get("/automation-rules")
def list_rules(_: VoiceUser = Depends(_require_recruiter), db: Session = Depends(get_db)):
    return [{"id": r.id, "category": r.category, "enabled": r.enabled,
             "delay_hours": r.delay_hours} for r in db.query(EmailAutomationRule).all()]


class RuleUpdate(BaseModel):
    enabled: Optional[bool] = None
    delay_hours: Optional[int] = None


@router.patch("/automation-rules/{rule_id}")
def update_rule(rule_id: str, body: RuleUpdate, _: VoiceUser = Depends(_require_recruiter), db: Session = Depends(get_db)):
    r = db.query(EmailAutomationRule).get(rule_id)
    if not r:
        raise HTTPException(404)
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(r, field, val)
    db.commit()
    return {"ok": True}


# ─── Candidate import ─────────────────────────────────────────────────────────

@router.post("/import/upload")
async def upload_candidates(file: UploadFile = File(...), u: VoiceUser = Depends(_require_recruiter),
                             db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(400, "No filename")
    content = await file.read()
    if len(content) > 5_000_000:
        raise HTTPException(413, "File too large (max 5 MB)")
    try:
        result = process_import(file.filename, content)
    except ValueError as e:
        raise HTTPException(400, str(e))

    imp = CandidateImport(
        id=result.import_id,
        filename=file.filename,
        imported_by=u.user_id,
        total_rows=result.total,
        valid_count=len(result.valid),
        duplicate_count=len(result.duplicate_emails),
        invalid_email_count=len([e for e in result.errors if "Invalid email" in e.get("error", "")]),
        error_rows=result.errors,
        candidates=result.valid,
        confirmed=False,
    )
    db.add(imp)
    db.commit()
    return result.to_dict()


class ImportConfirm(BaseModel):
    import_id: str
    send_invitations: bool = False
    job_role: str = "Software Engineer"
    assessment_title: str = "Technical Task & System Design"
    deadline: str = "48 hours"
    assessment_link: str = "https://portal.voicehire.ai/submit"
    meeting_link: str = "https://meet.google.com/xyz-voice-hire"
    candidate_ids: Optional[list[str]] = None


@router.post("/import/sample")
async def import_sample_candidates(u: VoiceUser = Depends(_require_recruiter), db: Session = Depends(get_db)):
    """Load sample candidates from sample_candidates.xlsx automatically."""
    import os
    sample_paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "sample_candidates.xlsx"),
        os.path.join(os.path.dirname(__file__), "..", "..", "test_candidates.xlsx"),
    ]
    file_bytes = None
    fname = "sample_candidates.xlsx"
    for p in sample_paths:
        if os.path.exists(p):
            with open(p, "rb") as f:
                file_bytes = f.read()
            fname = os.path.basename(p)
            break
    if not file_bytes:
        raise HTTPException(404, "Sample file not found on server")

    result = process_import(fname, file_bytes)
    imp = CandidateImport(
        id=result.import_id,
        filename=fname,
        imported_by=u.user_id,
        total_rows=result.total,
        valid_count=len(result.valid),
        duplicate_count=len(result.duplicate_emails),
        invalid_email_count=len([e for e in result.errors if "Invalid email" in e.get("error", "")]),
        error_rows=result.errors,
        candidates=result.valid,
        confirmed=False,
    )
    db.add(imp)
    db.commit()
    return result.to_dict()


@router.post("/import/confirm")
async def confirm_import(body: ImportConfirm, u: VoiceUser = Depends(_require_recruiter), db: Session = Depends(get_db)):
    imp = db.query(CandidateImport).get(body.import_id)
    if not imp:
        raise HTTPException(404, "Import record not found")
    imp.confirmed = True
    db.commit()

    candidates_to_send = imp.candidates
    if body.candidate_ids and len(body.candidate_ids) > 0:
        c_set = set(body.candidate_ids)
        candidates_to_send = [c for c in imp.candidates if c.get("id") in c_set]

    sent_count = 0
    if body.send_invitations and body.job_role:
        for c in candidates_to_send:
            job = schedule_assessment_invitation(
                to_email=c["email"], to_name=c["name"], candidate_id=c["id"],
                job_role=body.job_role, assessment_title=body.assessment_title or "Technical Assessment",
                deadline=body.deadline or "48 hours",
                assessment_link=body.assessment_link or "https://portal.voicehire.ai/submit",
                meeting_link=body.meeting_link or "https://meet.google.com/xyz-voice-hire",
                db=db,
            )
            if job:
                # Immediately deliver so it's not stuck in queued
                await send_email(job, db)
                sent_count += 1
        db.commit()

    return {
        "ok": True,
        "candidates_imported": len(candidates_to_send),
        "emails_queued": sent_count,
        "emails_sent": sent_count,
        "meeting_link": body.meeting_link,
        "assessment_title": body.assessment_title,
    }


# ─── Email jobs / logs ────────────────────────────────────────────────────────

@router.get("/jobs")
def list_jobs(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    candidate_id: Optional[str] = Query(None),
    skip: int = 0, limit: int = 50,
    _: VoiceUser = Depends(_require_recruiter),
    db: Session = Depends(get_db),
):
    q = db.query(EmailJob)
    if status:
        q = q.filter(EmailJob.status == status)
    if category:
        q = q.filter(EmailJob.category == category)
    if candidate_id:
        q = q.filter(EmailJob.candidate_id == candidate_id)
    total = q.count()
    jobs = q.order_by(EmailJob.created_at.desc()).offset(skip).limit(limit).all()
    return {
        "total": total,
        "jobs": [{
            "id": j.id, "category": j.category, "status": j.status,
            "to_email": j.to_email, "to_name": j.to_name, "subject": j.subject,
            "candidate_id": j.candidate_id, "assignment_id": j.assignment_id,
            "scheduled_at": j.scheduled_at, "sent_at": j.sent_at,
            "created_at": j.created_at, "attempt_count": j.attempt_count,
            "last_error": j.last_error, "is_simulated": j.is_simulated,
        } for j in jobs],
    }


@router.get("/jobs/stats")
def job_stats(_: VoiceUser = Depends(_require_recruiter), db: Session = Depends(get_db)):
    counts = {}
    for status in EmailStatus:
        counts[status.value] = db.query(EmailJob).filter_by(status=status).count()
    return counts


@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: str, _: VoiceUser = Depends(_require_recruiter), db: Session = Depends(get_db)):
    job = db.query(EmailJob).get(job_id)
    if not job:
        raise HTTPException(404)
    if job.status not in (EmailStatus.failed,):
        raise HTTPException(409, "Only failed jobs can be manually retried")
    job.status = EmailStatus.queued
    job.next_retry_at = None
    job.last_error = None
    db.commit()
    asyncio.create_task(_fire_job(job_id))
    return {"ok": True}


async def _fire_job(job_id: str):
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        job = db.query(EmailJob).get(job_id)
        if job:
            await send_email(job, db)
            db.commit()
    finally:
        db.close()


@router.get("/jobs/{job_id}/preview")
def get_job_preview(job_id: str, _: VoiceUser = Depends(_require_recruiter), db: Session = Depends(get_db)):
    job = db.query(EmailJob).get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {
        "id": job.id,
        "subject": job.subject,
        "to_email": job.to_email,
        "to_name": job.to_name,
        "html_body": job.html_body,
        "text_body": job.text_body,
        "category": job.category,
        "status": job.status,
        "context_vars": job.context_vars,
        "created_at": job.created_at,
        "sent_at": job.sent_at,
    }


class PipelineTriggerRequest(BaseModel):
    candidate_id: str
    stage: str  # "day2_reminder" | "interview" | "feedback" | "decision"
    candidate_name: str
    candidate_email: str
    job_role: str = "Software Engineer"
    assessment_title: str = "Technical Task & System Design"
    deadline: str = "48 hours"
    assessment_link: str = "https://portal.voicehire.ai/submit"
    meeting_link: str = "https://meet.google.com/xyz-voice-hire"
    feedback_notes: str = "Candidate completed the technical task with excellent problem solving."
    decision: str = "Congratulations! We would like to extend an offer for the position."


@router.post("/pipeline/trigger-stage")
async def trigger_pipeline_stage(body: PipelineTriggerRequest, u: VoiceUser = Depends(_require_recruiter), db: Session = Depends(get_db)):
    """Dispatches a pipeline stage email immediately for a candidate."""
    job = None
    if body.stage == "day2_reminder":
        job = schedule_email(
            category=EmailCategory.assessment_reminder,
            to_email=body.candidate_email, to_name=body.candidate_name,
            candidate_id=body.candidate_id, db=db, delay_hours=0,
            context_vars=dict(
                candidate_name=body.candidate_name, job_role=body.job_role,
                assessment_title=body.assessment_title, deadline=body.deadline,
                assessment_link=body.assessment_link, meeting_link=body.meeting_link
            ),
            idempotency_suffix=f"day2_{uuid.uuid4()}",
        )
    elif body.stage == "interview":
        job = schedule_email(
            category=EmailCategory.interview_invitation,
            to_email=body.candidate_email, to_name=body.candidate_name,
            candidate_id=body.candidate_id, db=db, delay_hours=0,
            context_vars=dict(
                candidate_name=body.candidate_name, job_role=body.job_role,
                interview_datetime="Tomorrow at 3:00 PM IST", timezone="Asia/Kolkata",
                interviewer_name="Engineering Lead", meeting_link=body.meeting_link,
                interview_instructions="Please join via Google Meet on time with camera enabled."
            ),
            idempotency_suffix=f"interview_{uuid.uuid4()}",
        )
    elif body.stage == "feedback":
        job = schedule_email(
            category=EmailCategory.review_ready,
            to_email=body.candidate_email, to_name=body.candidate_name,
            candidate_id=body.candidate_id, db=db, delay_hours=0,
            context_vars=dict(
                candidate_name=body.candidate_name, assessment_title=body.assessment_title,
                submission_datetime="Verified & Evaluated", repo_url=body.assessment_link,
                review_link=body.meeting_link
            ),
            idempotency_suffix=f"feedback_{uuid.uuid4()}",
        )
    elif body.stage == "decision":
        job = schedule_email(
            category=EmailCategory.decision_notification,
            to_email=body.candidate_email, to_name=body.candidate_name,
            candidate_id=body.candidate_id, db=db, delay_hours=0,
            context_vars=dict(
                candidate_name=body.candidate_name, job_role=body.job_role,
                decision_message=body.decision,
                feedback_summary=body.feedback_notes
            ),
            idempotency_suffix=f"decision_{uuid.uuid4()}",
        )
    if not job:
        raise HTTPException(400, "Unable to generate stage email")

    # Send immediately
    await send_email(job, db)
    db.commit()
    return {
        "ok": True,
        "job_id": job.id,
        "stage": body.stage,
        "status": job.status.value,
        "subject": job.subject,
        "recipient": job.to_email,
        "meeting_link": body.meeting_link,
    }


# ─── Bulk send ────────────────────────────────────────────────────────────────

class BulkPreviewRequest(BaseModel):
    candidate_emails: list[str]
    category: EmailCategory
    context_vars: dict = {}


@router.post("/bulk/preview")
def bulk_preview(body: BulkPreviewRequest, _: VoiceUser = Depends(_require_recruiter), db: Session = Depends(get_db)):
    valid = [e for e in body.candidate_emails if validate_email(e)]
    invalid = [e for e in body.candidate_emails if not validate_email(e)]
    tpl = db.query(EmailTemplate).filter_by(category=body.category, enabled=True).first()
    subject_preview = render_template(tpl.subject, body.context_vars) if tpl else "(template not found)"
    return {
        "valid_count": len(valid),
        "invalid_count": len(invalid),
        "invalid_emails": invalid,
        "subject_preview": subject_preview,
        "requires_confirmation": True,
    }


class BulkSendRequest(BaseModel):
    candidate_emails: list[str]
    candidate_names: dict[str, str] = {}  # email -> name
    candidate_ids: dict[str, str] = {}    # email -> candidate_id
    category: EmailCategory
    context_vars: dict = {}
    confirmed: bool = False


@router.post("/bulk/send")
def bulk_send(body: BulkSendRequest, u: VoiceUser = Depends(_require_recruiter), db: Session = Depends(get_db)):
    cfg = get_email_config()
    if cfg.bulk_confirm_required and not body.confirmed:
        raise HTTPException(400, "Bulk send requires confirmed=true. Preview first, then confirm.")
    queued, skipped = 0, 0
    for email in body.candidate_emails:
        if not validate_email(email):
            skipped += 1
            continue
        ctx = {**body.context_vars, "candidate_name": body.candidate_names.get(email, email)}
        job = schedule_email(
            category=body.category, to_email=email,
            to_name=body.candidate_names.get(email),
            candidate_id=body.candidate_ids.get(email),
            recruiter_id=u.user_id, context_vars=ctx, db=db,
            idempotency_suffix=str(uuid.uuid4()),
        )
        if job:
            queued += 1
        else:
            skipped += 1
    return {"queued": queued, "skipped": skipped}


# ─── Suppression ──────────────────────────────────────────────────────────────

@router.post("/suppressions")
def add_suppression(email: str = Body(...), category: Optional[str] = Body(None), reason: Optional[str] = Body(None),
                    _: VoiceUser = Depends(_require_recruiter), db: Session = Depends(get_db)):
    if not validate_email(email):
        raise HTTPException(400, "Invalid email")
    db.add(EmailSuppression(email=email.lower(), category=category, reason=reason))
    db.commit()
    return {"ok": True}


@router.get("/suppressions")
def list_suppressions(_: VoiceUser = Depends(_require_recruiter), db: Session = Depends(get_db)):
    return [{"id": s.id, "email": s.email, "category": s.category, "reason": s.reason,
             "created_at": s.created_at} for s in db.query(EmailSuppression).all()]


# ─── Workflow trigger endpoints ───────────────────────────────────────────────

class AssessmentInviteRequest(BaseModel):
    to_email: str
    to_name: str
    candidate_id: str
    job_role: str
    assessment_title: str
    deadline: str
    assessment_link: str
    support_contact: str = "support@voicehire.ai"
    assignment_id: Optional[str] = None
    also_schedule_reminder: bool = True


@router.post("/send/assessment-invitation")
def send_assessment_invite(body: AssessmentInviteRequest, _: VoiceUser = Depends(_require_recruiter), db: Session = Depends(get_db)):
    job = schedule_assessment_invitation(
        to_email=body.to_email, to_name=body.to_name, candidate_id=body.candidate_id,
        job_role=body.job_role, assessment_title=body.assessment_title,
        deadline=body.deadline, assessment_link=body.assessment_link,
        support_contact=body.support_contact, assignment_id=body.assignment_id, db=db,
    )
    reminder_job = None
    if body.also_schedule_reminder and job:
        reminder_job = schedule_assessment_reminder(
            to_email=body.to_email, to_name=body.to_name, candidate_id=body.candidate_id,
            job_role=body.job_role, assessment_title=body.assessment_title,
            deadline=body.deadline, assessment_link=body.assessment_link,
            assignment_id=body.assignment_id, db=db,
        )
    return {
        "invitation_job_id": job.id if job else None,
        "reminder_job_id": reminder_job.id if reminder_job else None,
        "reminder_scheduled_in_hours": 48,
    }


class CancelReminderRequest(BaseModel):
    assignment_id: str


@router.post("/cancel-reminder")
def cancel_reminder(body: CancelReminderRequest, _: VoiceUser = Depends(_require_recruiter), db: Session = Depends(get_db)):
    cancelled = cancel_reminder_for_assignment(body.assignment_id, db)
    return {"cancelled_count": cancelled}
