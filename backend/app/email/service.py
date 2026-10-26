"""SMTP email service - sends via aiosmtplib or simulates in demo mode."""
from __future__ import annotations
import logging
import math
import re
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape as html_escape

import aiosmtplib
from jinja2 import Environment, BaseLoader, select_autoescape
from sqlalchemy.orm import Session

from app.email.config import get_email_config
from app.email.models import EmailJob, EmailLog, EmailStatus

logger = logging.getLogger(__name__)

# Jinja2 env for template rendering
_jinja = Environment(
    loader=BaseLoader(),
    autoescape=select_autoescape(["html"]),
)


EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def validate_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email.strip())) if email else False


def render_template(template_str: str, context: dict) -> str:
    """Render a Jinja2 template string. Values are auto-escaped for HTML."""
    safe_ctx = {k: html_escape(str(v)) if isinstance(v, str) else v for k, v in context.items()}
    return _jinja.from_string(template_str).render(**safe_ctx)


def _build_mime(job: EmailJob, cfg) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = job.subject
    msg["From"] = f"{cfg.sender_name} <{cfg.sender_email}>"
    msg["To"] = f"{job.to_name} <{job.to_email}>" if job.to_name else job.to_email
    msg["X-Mailer"] = "VoiceHire-AI"
    msg.attach(MIMEText(job.text_body, "plain", "utf-8"))
    msg.attach(MIMEText(job.html_body, "html", "utf-8"))
    return msg


async def send_email(job: EmailJob, db: Session) -> EmailStatus:
    """
    Attempt to deliver one EmailJob.
    Returns final status. Caller must commit db.
    """
    cfg = get_email_config()
    log = EmailLog(
        job_id=job.id,
        attempt_number=job.attempt_count + 1,
        status=EmailStatus.pending,
    )
    job.attempt_count += 1
    db.add(log)

    try:
        if cfg.demo_mode or job.is_simulated:
            # Simulated - never touches real SMTP
            log.status = EmailStatus.simulated
            log.smtp_response = "DEMO MODE - email not sent to real SMTP"
            job.status = EmailStatus.simulated
            job.sent_at = datetime.now(timezone.utc).replace(tzinfo=None)
            logger.info("[EMAIL DEMO] to=%s subject=%s", job.to_email, job.subject)
            return EmailStatus.simulated

        if not cfg.is_configured:
            raise RuntimeError("SMTP not configured. Set SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD and EMAIL_DEMO_MODE=false.")

        msg = _build_mime(job, cfg)
        smtp_kwargs = dict(hostname=cfg.smtp_host, port=cfg.smtp_port, username=cfg.smtp_username, password=cfg.smtp_password)
        if cfg.smtp_use_ssl:
            smtp_kwargs["use_tls"] = True
            await aiosmtplib.send(msg, **smtp_kwargs)
        elif cfg.smtp_use_tls:
            await aiosmtplib.send(msg, start_tls=True, **smtp_kwargs)
        else:
            await aiosmtplib.send(msg, **smtp_kwargs)

        log.status = EmailStatus.accepted
        log.smtp_response = "250 Message queued for delivery"
        job.status = EmailStatus.accepted
        job.sent_at = datetime.now(timezone.utc).replace(tzinfo=None)
        logger.info("[EMAIL SENT] to=%s subject=%s", job.to_email, job.subject)
        return EmailStatus.accepted

    except Exception as exc:
        # Never log passwords or full message bodies
        safe_msg = str(exc)[:300]
        log.status = EmailStatus.failed
        log.error_message = safe_msg
        job.last_error = safe_msg

        if job.attempt_count < job.max_attempts:
            delay = cfg.retry_base_delay_seconds * (2 ** (job.attempt_count - 1))
            job.status = EmailStatus.retrying
            job.next_retry_at = (datetime.now(timezone.utc) + timedelta(seconds=delay)).replace(tzinfo=None)
            logger.warning("[EMAIL RETRY %d/%d] to=%s error=%s next_in=%ds",
                           job.attempt_count, job.max_attempts, job.to_email, safe_msg, delay)
        else:
            job.status = EmailStatus.failed
            logger.error("[EMAIL FAILED] to=%s after %d attempts: %s", job.to_email, job.attempt_count, safe_msg)
        return job.status
