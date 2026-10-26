"""Email configuration loaded from environment variables.
Never exposes SMTP credentials to frontend or logs.
"""
import os
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass
class EmailConfig:
    # SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""       # kept server-side only, never logged
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False

    # Sender identity
    sender_email: str = ""
    sender_name: str = "VoiceHire AI"

    # Behaviour
    demo_mode: bool = True         # True: simulate, do NOT send real emails
    max_retries: int = 5
    retry_base_delay_seconds: int = 60    # exponential backoff base
    bulk_confirm_required: bool = True
    reminder_delay_hours: int = 48

    # Feature flags
    send_assessment_invitations: bool = True
    send_assessment_reminders: bool = True
    send_submission_confirmations: bool = True
    send_interview_invitations: bool = True
    send_decision_notifications: bool = True

    @property
    def is_configured(self) -> bool:
        """True only when SMTP credentials are set and demo mode is off."""
        return bool(self.smtp_host and self.smtp_username and self.smtp_password and not self.demo_mode)

    @property
    def smtp_info(self) -> dict:
        """Safe SMTP info to expose (NO password)."""
        return {
            "host": self.smtp_host or "(not set)",
            "port": self.smtp_port,
            "username": self.smtp_username or "(not set)",
            "use_tls": self.smtp_use_tls,
            "use_ssl": self.smtp_use_ssl,
            "sender": f"{self.sender_name} <{self.sender_email}>" if self.sender_email else "(not set)",
            "demo_mode": self.demo_mode,
            "is_configured": self.is_configured,
        }


@lru_cache(maxsize=1)
def get_email_config() -> EmailConfig:
    return EmailConfig(
        smtp_host=os.getenv("SMTP_HOST", ""),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_username=os.getenv("SMTP_USERNAME", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        smtp_use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
        smtp_use_ssl=os.getenv("SMTP_USE_SSL", "false").lower() == "true",
        sender_email=os.getenv("SMTP_SENDER_EMAIL", ""),
        sender_name=os.getenv("SMTP_SENDER_NAME", "VoiceHire AI"),
        demo_mode=os.getenv("EMAIL_DEMO_MODE", "true").lower() == "true",
        max_retries=int(os.getenv("EMAIL_MAX_RETRIES", "5")),
        retry_base_delay_seconds=int(os.getenv("EMAIL_RETRY_BASE_DELAY_SECONDS", "60")),
        bulk_confirm_required=os.getenv("EMAIL_BULK_CONFIRM_REQUIRED", "true").lower() == "true",
        reminder_delay_hours=int(os.getenv("EMAIL_REMINDER_DELAY_HOURS", "48")),
        send_assessment_invitations=os.getenv("EMAIL_SEND_ASSESSMENT_INVITATIONS", "true").lower() == "true",
        send_assessment_reminders=os.getenv("EMAIL_SEND_ASSESSMENT_REMINDERS", "true").lower() == "true",
        send_submission_confirmations=os.getenv("EMAIL_SEND_SUBMISSION_CONFIRMATIONS", "true").lower() == "true",
        send_interview_invitations=os.getenv("EMAIL_SEND_INTERVIEW_INVITATIONS", "true").lower() == "true",
        send_decision_notifications=os.getenv("EMAIL_SEND_DECISION_NOTIFICATIONS", "true").lower() == "true",
    )
