"""Default email templates seeded at startup."""
from app.email.models import EmailCategory, EmailTemplate


DEFAULT_TEMPLATES = [
    EmailTemplate(
        category=EmailCategory.assessment_invitation,
        name="Assessment Invitation",
        subject="{{job_role}} Assessment & Interview – Action Required by {{deadline}}",
        html_body="""<!DOCTYPE html><html><body style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;color:#1c2330;background:#f8fafc;padding:24px">
<div style="background:#fff;border-radius:12px;padding:32px;border:1px solid #e2e8f0;box-shadow:0 4px 12px rgba(0,0,0,0.05)">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
    <div style="background:#2563eb;color:#fff;width:36px;height:36px;border-radius:8px;text-align:center;line-height:36px;font-size:18px;font-weight:bold">V</div>
    <span style="font-size:18px;font-weight:700;color:#0f172a">VoiceHire AI</span>
  </div>
  <h1 style="color:#2563eb;font-size:22px;margin:0 0 8px">Assessment Task &amp; Interview Invitation</h1>
  <hr style="border:0;border-top:1px solid #e2e8f0;margin:16px 0">
  <p>Hi <strong>{{candidate_name}}</strong>,</p>
  <p>You have been shortlisted for the <strong>{{job_role}}</strong> role. We have assigned you a technical assessment task and scheduled your briefing session.</p>
  
  <table style="width:100%;border-collapse:collapse;margin:16px 0;background:#f8f9fc;border-radius:8px;overflow:hidden">
    <tr><td style="padding:10px 14px;font-weight:600;color:#475569;border-bottom:1px solid #e2e8f0">Assigned Task</td><td style="padding:10px 14px;font-weight:700;color:#0f172a;border-bottom:1px solid #e2e8f0">{{assessment_title}}</td></tr>
    <tr><td style="padding:10px 14px;font-weight:600;color:#475569;border-bottom:1px solid #e2e8f0">Position</td><td style="padding:10px 14px;color:#0f172a;border-bottom:1px solid #e2e8f0">{{job_role}}</td></tr>
    <tr><td style="padding:10px 14px;font-weight:600;color:#475569;border-bottom:1px solid #e2e8f0">Google Meet Link</td><td style="padding:10px 14px;border-bottom:1px solid #e2e8f0"><a href="{{meeting_link}}" style="color:#2563eb;font-weight:600;text-decoration:underline" target="_blank">{{meeting_link}}</a></td></tr>
    <tr><td style="padding:10px 14px;font-weight:600;color:#475569">Submission Deadline</td><td style="padding:10px 14px;color:#dc2626;font-weight:700">{{deadline}}</td></tr>
  </table>

  <div style="margin:24px 0;text-align:center">
    <a href="{{meeting_link}}" style="display:inline-block;padding:12px 24px;background:#16a34a;color:#fff;text-decoration:none;border-radius:8px;font-weight:700;margin-right:8px" target="_blank">📹 Join Google Meet Session →</a>
    <a href="{{assessment_link}}" style="display:inline-block;padding:12px 24px;background:#2563eb;color:#fff;text-decoration:none;border-radius:8px;font-weight:700" target="_blank">🚀 View Task &amp; Submission Link →</a>
  </div>

  <p style="font-size:13px;color:#64748b">Please join the Google Meet session at the assigned time. If you have any questions, reply to this email or reach out to {{support_contact}}.</p>
  <hr style="border:0;border-top:1px solid #e2e8f0;margin:16px 0">
  <p style="font-size:11px;color:#94a3b8">VoiceHire AI · Automated Recruitment &amp; Evaluation Pipeline</p>
</div></body></html>""",
        text_body="""Hi {{candidate_name}},

You have been assigned the {{assessment_title}} assessment for {{job_role}}.

Google Meet Link: {{meeting_link}}
Submission Link: {{assessment_link}}
Deadline: {{deadline}}
Contact: {{support_contact}}

VoiceHire AI""",
        variables=["candidate_name", "job_role", "assessment_title", "deadline", "assessment_link", "meeting_link", "support_contact"],
    ),
    EmailTemplate(
        category=EmailCategory.assessment_reminder,
        name="Assessment Reminder (48h)",
        subject="⏰ Day 2 Reminder: {{assessment_title}} Submission Due {{deadline}}",
        html_body="""<!DOCTYPE html><html><body style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;color:#1c2330;background:#f8fafc;padding:24px">
<div style="background:#fff;border-radius:12px;padding:32px;border:1px solid #e2e8f0;box-shadow:0 4px 12px rgba(0,0,0,0.05)">
  <h1 style="color:#c05c00;font-size:22px;margin:0 0 8px">⏰ Day 2 Reminder: Submission Due Soon</h1>
  <hr style="border:0;border-top:1px solid #e2e8f0;margin:16px 0">
  <p>Hi <strong>{{candidate_name}}</strong>,</p>
  <p>This is a reminder that your task submission for <strong>{{assessment_title}}</strong> ({{job_role}}) is due soon.</p>
  
  <table style="width:100%;border-collapse:collapse;margin:16px 0;background:#fffbeb;border-radius:8px;overflow:hidden">
    <tr><td style="padding:10px 14px;font-weight:600;color:#92400e">Assigned Task</td><td style="padding:10px 14px;color:#92400e;font-weight:700">{{assessment_title}}</td></tr>
    <tr><td style="padding:10px 14px;font-weight:600;color:#92400e">Deadline</td><td style="padding:10px 14px;color:#dc2626;font-weight:700">{{deadline}}</td></tr>
    <tr><td style="padding:10px 14px;font-weight:600;color:#92400e">Google Meet (Q&amp;A)</td><td style="padding:10px 14px"><a href="{{meeting_link}}" style="color:#2563eb;font-weight:600">{{meeting_link}}</a></td></tr>
  </table>

  <div style="text-align:center;margin:24px 0">
    <a href="{{assessment_link}}" style="display:inline-block;padding:14px 28px;background:#c05c00;color:#fff;text-decoration:none;border-radius:8px;font-weight:700">📤 Open Submission Portal →</a>
  </div>
  <p style="font-size:12px;color:#64748b">Once submitted, our team will review your work and advance you to the next stage.</p>
</div></body></html>""",
        text_body="""Hi {{candidate_name}},

Reminder: your {{assessment_title}} assessment for {{job_role}} is due soon.
Submission Link: {{assessment_link}}
Google Meet: {{meeting_link}}
Deadline: {{deadline}}

VoiceHire AI""",
        variables=["candidate_name", "job_role", "assessment_title", "deadline", "assessment_link", "meeting_link"],
    ),
    EmailTemplate(
        category=EmailCategory.submission_confirmation,
        name="Submission Confirmation",
        subject="Submission Received – {{assessment_title}}",
        html_body="""<!DOCTYPE html><html><body style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;color:#1c2330;background:#f8fafc;padding:24px">
<div style="background:#fff;border-radius:12px;padding:32px;border:1px solid #e2e8f0">
  <h1 style="color:#0f6b5c;font-size:22px">✅ Submission Confirmed</h1>
  <p>Hi <strong>{{candidate_name}}</strong>,</p>
  <p>We have successfully received your submission for <strong>{{assessment_title}}</strong>.</p>
  <table style="width:100%;border-collapse:collapse;margin:16px 0">
    <tr><td style="padding:8px;background:#f0faf8;font-weight:600">Submitted</td><td style="padding:8px">{{submission_datetime}}</td></tr>
    <tr><td style="padding:8px;font-weight:600">Repository</td><td style="padding:8px">{{repo_url}}</td></tr>
    <tr><td style="padding:8px;background:#f0faf8;font-weight:600">Reference</td><td style="padding:8px">{{assignment_ref}}</td></tr>
  </table>
  <p>Our team will review your submission and get back to you.</p>
</div></body></html>""",
        text_body="""Hi {{candidate_name}},

Your submission for {{assessment_title}} was received.
Submitted: {{submission_datetime}}
Repository: {{repo_url}}
Reference: {{assignment_ref}}

VoiceHire AI""",
        variables=["candidate_name", "assessment_title", "submission_datetime", "repo_url", "assignment_ref"],
    ),
    EmailTemplate(
        category=EmailCategory.interview_invitation,
        name="Interview Invitation",
        subject="Interview Scheduled – {{job_role}} on {{interview_datetime}}",
        html_body="""<!DOCTYPE html><html><body style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;color:#1c2330;background:#f8fafc;padding:24px">
<div style="background:#fff;border-radius:12px;padding:32px;border:1px solid #e2e8f0">
  <h1 style="color:#0f6b5c;font-size:22px">🎙 Interview Invitation</h1>
  <p>Hi <strong>{{candidate_name}}</strong>,</p>
  <p>Congratulations! You have been invited to an interview for <strong>{{job_role}}</strong>.</p>
  <table style="width:100%;border-collapse:collapse;margin:16px 0">
    <tr><td style="padding:8px;background:#f0faf8;font-weight:600">Date &amp; Time</td><td style="padding:8px"><strong>{{interview_datetime}}</strong></td></tr>
    <tr><td style="padding:8px;font-weight:600">Timezone</td><td style="padding:8px">{{timezone}}</td></tr>
    <tr><td style="padding:8px;background:#f0faf8;font-weight:600">Interviewer</td><td style="padding:8px">{{interviewer_name}}</td></tr>
  </table>
  <div style="text-align:center;margin:24px 0">
    <a href="{{meeting_link}}" style="display:inline-block;padding:14px 28px;background:#0f6b5c;color:#fff;text-decoration:none;border-radius:8px;font-weight:600">Join Meeting →</a>
  </div>
  <p style="font-size:13px;color:#5b6575">{{interview_instructions}}</p>
</div></body></html>""",
        text_body="""Hi {{candidate_name}},

You are invited to an interview for {{job_role}}.
Date & Time: {{interview_datetime}} ({{timezone}})
Interviewer: {{interviewer_name}}
Meeting link: {{meeting_link}}

{{interview_instructions}}

VoiceHire AI""",
        variables=["candidate_name", "job_role", "interview_datetime", "timezone", "interviewer_name", "meeting_link", "interview_instructions"],
    ),
    EmailTemplate(
        category=EmailCategory.interview_reschedule,
        name="Interview Rescheduled",
        subject="Interview Rescheduled – {{job_role}}",
        html_body="""<!DOCTYPE html><html><body style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;color:#1c2330;padding:24px">
<div style="background:#fff;border-radius:12px;padding:32px;border:1px solid #e2e8f0">
  <h1 style="color:#c05c00;font-size:22px">📅 Interview Rescheduled</h1>
  <p>Hi <strong>{{candidate_name}}</strong>,</p>
  <p>Your interview for <strong>{{job_role}}</strong> has been rescheduled.</p>
  <table style="width:100%;border-collapse:collapse;margin:16px 0">
    <tr><td style="padding:8px;background:#fef3ee;font-weight:600">Previous time</td><td style="padding:8px;text-decoration:line-through;color:#888">{{previous_datetime}}</td></tr>
    <tr><td style="padding:8px;font-weight:600">New time</td><td style="padding:8px"><strong>{{interview_datetime}}</strong></td></tr>
    <tr><td style="padding:8px;background:#f0faf8;font-weight:600">Meeting link</td><td style="padding:8px"><a href="{{meeting_link}}">{{meeting_link}}</a></td></tr>
  </table>
</div></body></html>""",
        text_body="""Hi {{candidate_name}},

Your interview for {{job_role}} has been rescheduled.
Previous: {{previous_datetime}}
New time: {{interview_datetime}}
Meeting: {{meeting_link}}

VoiceHire AI""",
        variables=["candidate_name", "job_role", "previous_datetime", "interview_datetime", "meeting_link"],
    ),
    EmailTemplate(
        category=EmailCategory.decision_notification,
        name="Recruitment Decision",
        subject="Update on Your Application – {{job_role}}",
        html_body="""<!DOCTYPE html><html><body style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;color:#1c2330;padding:24px">
<div style="background:#fff;border-radius:12px;padding:32px;border:1px solid #e2e8f0">
  <h1 style="color:#0f6b5c;font-size:22px">Application Update</h1>
  <p>Hi <strong>{{candidate_name}}</strong>,</p>
  <p>Thank you for your interest in the <strong>{{job_role}}</strong> position.</p>
  <div style="background:#f0faf8;border-radius:8px;padding:16px;margin:16px 0">
    <p style="margin:0">{{decision_message}}</p>
  </div>
  <p style="font-size:13px;color:#5b6575">{{feedback_summary}}</p>
</div></body></html>""",
        text_body="""Hi {{candidate_name}},

Re: {{job_role}} application.

{{decision_message}}

{{feedback_summary}}

VoiceHire AI""",
        variables=["candidate_name", "job_role", "decision_message", "feedback_summary"],
    ),
    EmailTemplate(
        category=EmailCategory.review_ready,
        name="Review Ready (Recruiter Notification)",
        subject="[VoiceHire] Submission ready for review – {{candidate_name}}",
        html_body="""<!DOCTYPE html><html><body style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;color:#1c2330;padding:24px">
<div style="background:#fff;border-radius:12px;padding:32px;border:1px solid #e2e8f0">
  <h1 style="color:#0f6b5c">📋 Submission Ready</h1>
  <p>A candidate has submitted their assessment and is ready for review.</p>
  <table style="width:100%;border-collapse:collapse;margin:16px 0">
    <tr><td style="padding:8px;background:#f0faf8;font-weight:600">Candidate</td><td style="padding:8px">{{candidate_name}}</td></tr>
    <tr><td style="padding:8px;font-weight:600">Assessment</td><td style="padding:8px">{{assessment_title}}</td></tr>
    <tr><td style="padding:8px;background:#f0faf8;font-weight:600">Submitted</td><td style="padding:8px">{{submission_datetime}}</td></tr>
    <tr><td style="padding:8px;font-weight:600">Repository</td><td style="padding:8px"><a href="{{repo_url}}">{{repo_url}}</a></td></tr>
  </table>
  <a href="{{review_link}}" style="display:inline-block;padding:12px 24px;background:#0f6b5c;color:#fff;text-decoration:none;border-radius:8px;font-weight:600">Review Submission →</a>
</div></body></html>""",
        text_body="""Candidate submission ready for review.

Candidate: {{candidate_name}}
Assessment: {{assessment_title}}
Submitted: {{submission_datetime}}
Repository: {{repo_url}}
Review: {{review_link}}

VoiceHire AI""",
        variables=["candidate_name", "assessment_title", "submission_datetime", "repo_url", "review_link"],
    ),
]


def seed_templates(db) -> None:
    """Insert or update default templates."""
    from app.email.models import EmailTemplate as ET
    for tpl_ref in DEFAULT_TEMPLATES:
        existing = db.query(ET).filter_by(category=tpl_ref.category).first()
        if not existing:
            fresh = ET(
                category=tpl_ref.category,
                name=tpl_ref.name,
                subject=tpl_ref.subject,
                html_body=tpl_ref.html_body,
                text_body=tpl_ref.text_body,
                variables=tpl_ref.variables,
                enabled=True,
            )
            db.add(fresh)
        else:
            # Update to include meeting_link and new template design
            existing.subject = tpl_ref.subject
            existing.html_body = tpl_ref.html_body
            existing.text_body = tpl_ref.text_body
            existing.variables = tpl_ref.variables
    db.commit()


def seed_automation_rules(db) -> None:
    """Insert default automation rules."""
    from app.email.models import EmailAutomationRule, EmailCategory
    defaults = [
        (EmailCategory.assessment_invitation, True, 0),
        (EmailCategory.assessment_reminder, True, 48),
        (EmailCategory.submission_confirmation, True, 0),
        (EmailCategory.interview_invitation, True, 0),
        (EmailCategory.interview_reschedule, True, 0),
        (EmailCategory.decision_notification, False, 0),  # requires approval
        (EmailCategory.review_ready, True, 0),
    ]
    for cat, enabled, delay in defaults:
        exists = db.query(EmailAutomationRule).filter_by(category=cat).first()
        if not exists:
            db.add(EmailAutomationRule(category=cat, enabled=enabled, delay_hours=delay))
    db.commit()
