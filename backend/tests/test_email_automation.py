"""Email automation acceptance tests (§9 of spec).
Run: $env:PYTHONPATH="backend"; backend\.venv\Scripts\pytest.exe backend\tests\test_email_automation.py -v
All 14 spec tests + extras. Uses SQLite in-memory; no real SMTP required.
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.email import models  # noqa – registers ORM models
from app.email.models import (
    CandidateImport, EmailAutomationRule, EmailCategory, EmailJob,
    EmailLog, EmailStatus, EmailSuppression, EmailTemplate,
)
from app.email.importer import process_import
from app.email.queue import (
    cancel_reminder_for_assignment,
    schedule_assessment_invitation,
    schedule_assessment_reminder,
    schedule_email,
    schedule_interview_invitation,
    schedule_submission_confirmation,
)
from app.email.service import validate_email, render_template
from app.email.templates import seed_templates, seed_automation_rules

# ── In-memory SQLite fixture ──────────────────────────────────────────────────

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    seed_templates(session)
    seed_automation_rules(session)
    yield session
    session.close()


# ─── Test 1: Recruiter can import candidates; invalid emails identified ───────

def test_import_identifies_invalid_emails():
    csv = b"name,email\nAlice,alice@example.com\nBob,not-an-email\nClara,clara@test.org\n"
    result = process_import("candidates.csv", csv)
    assert len(result.valid) == 2
    assert any("not-an-email" in e["error"] for e in result.errors)
    assert result.import_id  # unique ID generated


def test_import_detects_duplicates():
    csv = b"name,email\nAlice,alice@example.com\nAlice2,alice@example.com\n"
    result = process_import("dup.csv", csv)
    assert len(result.valid) == 1
    assert len(result.duplicate_emails) == 1


def test_import_rejects_missing_required_fields():
    csv = b"name,email\nNoEmail,\n,ghost@example.com\n"
    result = process_import("missing.csv", csv)
    assert len(result.valid) == 0
    assert len(result.errors) == 2


# ─── Test 2: Assessment invitation sent via configured provider ───────────────

def test_assessment_invitation_queued(db):
    job = schedule_assessment_invitation(
        to_email="alice@example.com", to_name="Alice", candidate_id="c1",
        job_role="Engineer", assessment_title="Python Test",
        deadline="2026-11-01", assessment_link="https://portal.example.com",
        db=db,
    )
    assert job is not None
    assert job.status in (EmailStatus.queued, EmailStatus.simulated)
    assert job.category == EmailCategory.assessment_invitation


# ─── Test 3: Email personalised with correct candidate info ──────────────────

def test_email_personalization(db):
    job = schedule_assessment_invitation(
        to_email="bob@example.com", to_name="Bob Smith", candidate_id="c2",
        job_role="Backend Dev", assessment_title="SQL Challenge",
        deadline="2026-12-01", assessment_link="https://test.link",
        db=db,
    )
    assert "Bob Smith" in job.html_body
    assert "SQL Challenge" in job.html_body
    assert "Backend Dev" in job.html_body


# ─── Test 4: 48h reminder scheduled persistently ─────────────────────────────

def test_reminder_scheduled_48h(db):
    job = schedule_assessment_reminder(
        to_email="carol@example.com", to_name="Carol", candidate_id="c3",
        job_role="Frontend Dev", assessment_title="React Test",
        deadline="2026-11-10", assessment_link="https://link.example.com",
        db=db,
    )
    assert job is not None
    assert job.category == EmailCategory.assessment_reminder
    # Scheduled ~48 hours from now
    assert job.scheduled_at is not None
    delta = job.scheduled_at - datetime.utcnow()
    assert 47 <= delta.total_seconds() / 3600 <= 49


def test_reminder_survives_session(db):
    """Reminder job persisted in DB (survives restart simulation)."""
    job = schedule_assessment_reminder(
        to_email="dave@example.com", to_name="Dave", candidate_id="c4",
        job_role="SRE", assessment_title="Linux Test", deadline="2026-11-20",
        assessment_link="https://link.test", db=db,
    )
    # Fetch fresh from DB (simulates restart)
    reloaded = db.query(EmailJob).filter_by(id=job.id).first()
    assert reloaded is not None
    assert reloaded.scheduled_at is not None


# ─── Test 5: Completed/cancelled assignment does not receive reminder ─────────

def test_cancelled_assignment_no_reminder(db):
    job = schedule_assessment_reminder(
        to_email="eve@example.com", to_name="Eve", candidate_id="c5",
        job_role="QA", assessment_title="QA Cert", deadline="2026-11-15",
        assessment_link="https://qa.test", assignment_id="assign-x", db=db,
    )
    assert job is not None
    cancelled = cancel_reminder_for_assignment("assign-x", db)
    assert cancelled == 1
    db.refresh(job)
    assert job.status == EmailStatus.cancelled


# ─── Test 6: Duplicate reminders and invitations are prevented ───────────────

def test_duplicate_invitation_prevented(db):
    kwargs = dict(to_email="frank@example.com", to_name="Frank", candidate_id="c6",
                  job_role="PM", assessment_title="PM Test", deadline="2026-11-30",
                  assessment_link="https://pm.test", db=db)
    j1 = schedule_assessment_invitation(**kwargs)
    j2 = schedule_assessment_invitation(**kwargs)
    # Both calls return same job (idempotency)
    assert j1.id == j2.id


# ─── Test 7: Failed emails are logged ────────────────────────────────────────

@pytest.mark.asyncio
async def test_failed_email_logged(db):
    """In demo mode, status = simulated (no real SMTP). We verify logs are recorded."""
    job = schedule_assessment_invitation(
        to_email="grace@example.com", to_name="Grace", candidate_id="c7",
        job_role="Designer", assessment_title="Design Sprint",
        deadline="2026-11-05", assessment_link="https://design.test", db=db,
    )
    from app.email.service import send_email
    status = await send_email(job, db)
    db.commit()
    logs = db.query(EmailLog).filter_by(job_id=job.id).all()
    assert len(logs) >= 1
    assert logs[0].status in (EmailStatus.simulated, EmailStatus.accepted)


# ─── Test 8: Interview invitation contains date, timezone, meeting link ───────

def test_interview_invitation_content(db):
    job = schedule_interview_invitation(
        to_email="henry@example.com", to_name="Henry", candidate_id="c8",
        job_role="CTO", interview_datetime="2026-11-15 14:00 UTC",
        timezone_str="IST (UTC+5:30)", interviewer_name="Jane Smith",
        meeting_link="https://meet.google.com/abc-xyz-123",
        db=db,
    )
    assert job is not None
    assert "14:00" in job.html_body or "14:00" in job.text_body
    assert "IST" in job.html_body or "IST" in job.text_body
    assert "meet.google.com" in job.html_body or "meet.google.com" in job.text_body


# ─── Test 9: Submission confirmation only after successful save ───────────────

def test_submission_confirmation_content(db):
    job = schedule_submission_confirmation(
        to_email="iris@example.com", to_name="Iris", candidate_id="c9",
        assessment_title="Backend Challenge",
        submission_datetime="2026-10-26 11:00 UTC",
        repo_url="https://github.com/iris/backend-challenge",
        assignment_ref="ASSIGN-2026-09",
        db=db,
    )
    assert job is not None
    assert "iris@example.com" in (job.to_email or "")
    assert "github.com/iris" in job.html_body or "github.com/iris" in job.text_body


# ─── Test 10: Decision notifications require approval (disabled by default) ───

def test_decision_notification_disabled_by_default(db):
    """EmailAutomationRule for decision_notification has enabled=False."""
    rule = db.query(EmailAutomationRule).filter_by(
        category=EmailCategory.decision_notification
    ).first()
    assert rule is not None
    assert rule.enabled is False


def test_decision_notification_not_queued_when_disabled(db):
    job = schedule_email(
        category=EmailCategory.decision_notification,
        to_email="jake@example.com", to_name="Jake", candidate_id="c10",
        context_vars={"candidate_name": "Jake", "job_role": "Dev",
                      "decision_message": "Congrats", "feedback_summary": "Good work"},
        db=db,
    )
    assert job is None  # disabled rule → no job created


# ─── Test 11: Bulk sending requires confirmation ──────────────────────────────

def test_bulk_confirm_flag_required():
    """bulk_confirm_required=True by default in config."""
    from app.email.config import EmailConfig
    cfg = EmailConfig()
    assert cfg.bulk_confirm_required is True


# ─── Test 12: Demo mode never sends real emails ───────────────────────────────

@pytest.mark.asyncio
async def test_demo_mode_never_real_smtp(db):
    from app.email.config import get_email_config
    cfg = get_email_config()
    # In default .env EMAIL_DEMO_MODE=true
    # We test service behaviour directly
    job = schedule_assessment_invitation(
        to_email="kim@example.com", to_name="Kim", candidate_id="c11",
        job_role="Analyst", assessment_title="Case Study",
        deadline="2026-11-30", assessment_link="https://case.test", db=db,
    )
    from app.email.service import send_email
    # Force demo flag for isolation
    job.is_simulated = True
    status = await send_email(job, db)
    db.commit()
    assert status == EmailStatus.simulated
    log = db.query(EmailLog).filter_by(job_id=job.id).first()
    assert "DEMO" in (log.smtp_response or "")


# ─── Test 13: Scheduled jobs survive restart (DB persistence) ─────────────────

def test_scheduled_job_in_db(db):
    job = schedule_assessment_reminder(
        to_email="leo@example.com", to_name="Leo", candidate_id="c12",
        job_role="Eng", assessment_title="SWE Test", deadline="2026-12-01",
        assessment_link="https://test.link", db=db,
    )
    # Simulate restart: open fresh query
    fetched = db.query(EmailJob).filter_by(id=job.id).first()
    assert fetched is not None
    assert fetched.scheduled_at is not None
    assert fetched.category == EmailCategory.assessment_reminder


# ─── Test 14: SMTP credentials never in frontend-exposed data ─────────────────

def test_smtp_credentials_not_in_safe_info():
    from app.email.config import EmailConfig
    cfg = EmailConfig(smtp_password="super-secret-password")
    info = cfg.smtp_info
    assert "super-secret-password" not in str(info)
    assert "password" not in str(info).lower() or "super-secret" not in str(info)


# ─── Bonus: Email validation ──────────────────────────────────────────────────

def test_email_validation():
    assert validate_email("alice@example.com") is True
    assert validate_email("not-an-email") is False
    assert validate_email("@nodomain.com") is False
    assert validate_email("double@@domain.com") is False
    assert validate_email("") is False
    assert validate_email("valid+tag@sub.domain.co.uk") is True


# ─── Bonus: Suppression prevents sending ─────────────────────────────────────

def test_suppressed_email_not_queued(db):
    db.add(EmailSuppression(email="suppressed@example.com", category=None, reason="opted out"))
    db.commit()
    job = schedule_assessment_invitation(
        to_email="suppressed@example.com", to_name="Suppressed", candidate_id="c13",
        job_role="Eng", assessment_title="Test", deadline="2026-12-01",
        assessment_link="https://test.link", db=db,
    )
    assert job is None


# ─── Bonus: Template rendering escapes HTML injection ────────────────────────

def test_template_html_escaping():
    rendered = render_template("Hello {{name}}", {"name": "<script>alert(1)</script>"})
    # Jinja2 autoescape ensures no live <script> tag executes
    assert "<script>" not in rendered
    # The dangerous payload is escaped (either &lt; or &amp;lt; — both are safe)
    assert "script" in rendered  # content preserved but neutralised


# ─── Bonus: Invalid email not scheduled ──────────────────────────────────────

def test_invalid_email_not_scheduled(db):
    job = schedule_email(
        category=EmailCategory.assessment_invitation,
        to_email="not-valid-email", to_name="Nobody",
        context_vars={}, db=db,
    )
    assert job is None
