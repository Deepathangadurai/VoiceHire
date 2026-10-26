"""Email automation database models."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey,
    Integer, String, Text, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # store UTC naive


class EmailStatus(str, PyEnum):
    pending = "pending"
    queued = "queued"
    accepted = "accepted"       # SMTP accepted (not confirmed delivery)
    failed = "failed"
    retrying = "retrying"
    cancelled = "cancelled"
    simulated = "simulated"     # demo mode – not actually sent


class EmailCategory(str, PyEnum):
    assessment_invitation = "assessment_invitation"
    assessment_reminder = "assessment_reminder"
    submission_confirmation = "submission_confirmation"
    interview_invitation = "interview_invitation"
    interview_reschedule = "interview_reschedule"
    interview_cancellation = "interview_cancellation"
    review_ready = "review_ready"
    decision_notification = "decision_notification"
    deadline_warning = "deadline_warning"
    overdue_notification = "overdue_notification"
    custom = "custom"
    test = "test"


# ─── EmailTemplate ────────────────────────────────────────────────────────────

class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    category = Column(Enum(EmailCategory), nullable=False, unique=True)
    name = Column(String(200), nullable=False)
    subject = Column(String(500), nullable=False)
    html_body = Column(Text, nullable=False)
    text_body = Column(Text, nullable=False)   # plain-text fallback
    variables = Column(JSON, default=list)     # list of supported var names
    enabled = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    jobs = relationship("EmailJob", back_populates="template")


# ─── EmailJob ─────────────────────────────────────────────────────────────────

class EmailJob(Base):
    """A scheduled or immediate email to one recipient."""
    __tablename__ = "email_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    idempotency_key = Column(String(200), unique=True, nullable=True)  # prevent duplicates

    template_id = Column(String(36), ForeignKey("email_templates.id"), nullable=True)
    category = Column(Enum(EmailCategory), nullable=False)
    status = Column(Enum(EmailStatus), default=EmailStatus.pending, nullable=False)

    # Recipient
    to_email = Column(String(320), nullable=False)
    to_name = Column(String(200), nullable=True)

    # Content (rendered at send time if template; stored after rendering)
    subject = Column(String(500), nullable=False)
    html_body = Column(Text, nullable=False)
    text_body = Column(Text, nullable=False)
    context_vars = Column(JSON, default=dict)   # vars used to render

    # References
    candidate_id = Column(String(36), nullable=True)
    assignment_id = Column(String(36), nullable=True)
    recruiter_id = Column(String(36), nullable=True)

    # Scheduling
    scheduled_at = Column(DateTime, nullable=True)   # UTC; None = send ASAP
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_now)

    # Retry tracking
    attempt_count = Column(Integer, default=0)
    max_attempts = Column(Integer, default=5)
    next_retry_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

    # Demo flag
    is_simulated = Column(Boolean, default=False)

    template = relationship("EmailTemplate", back_populates="jobs")
    logs = relationship("EmailLog", back_populates="job", cascade="all, delete-orphan")


# ─── EmailLog ─────────────────────────────────────────────────────────────────

class EmailLog(Base):
    """One delivery attempt log row per EmailJob attempt."""
    __tablename__ = "email_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey("email_jobs.id"), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    attempted_at = Column(DateTime, default=_now)
    status = Column(Enum(EmailStatus), nullable=False)
    smtp_response = Column(Text, nullable=True)   # SMTP response text (no secrets)
    error_message = Column(Text, nullable=True)

    job = relationship("EmailJob", back_populates="logs")


# ─── EmailAutomationRule ──────────────────────────────────────────────────────

class EmailAutomationRule(Base):
    __tablename__ = "email_automation_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    category = Column(Enum(EmailCategory), nullable=False, unique=True)
    enabled = Column(Boolean, default=True)
    delay_hours = Column(Integer, default=0)     # 0 = immediate; 48 = reminder
    conditions = Column(JSON, default=dict)       # e.g., {"only_if_status": "pending"}
    updated_at = Column(DateTime, default=_now, onupdate=_now)


# ─── EmailSuppression ─────────────────────────────────────────────────────────

class EmailSuppression(Base):
    __tablename__ = "email_suppressions"
    __table_args__ = (UniqueConstraint("email", "category"),)

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(320), nullable=False)
    category = Column(Enum(EmailCategory), nullable=True)  # None = all categories
    reason = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=_now)


# ─── CandidateImport ──────────────────────────────────────────────────────────

class CandidateImport(Base):
    """Tracks CSV/Excel import sessions."""
    __tablename__ = "candidate_imports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(300), nullable=False)
    imported_by = Column(String(36), nullable=True)   # recruiter user_id
    total_rows = Column(Integer, default=0)
    valid_count = Column(Integer, default=0)
    duplicate_count = Column(Integer, default=0)
    invalid_email_count = Column(Integer, default=0)
    error_rows = Column(JSON, default=list)
    candidates = Column(JSON, default=list)   # list of validated dicts
    confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_now)
