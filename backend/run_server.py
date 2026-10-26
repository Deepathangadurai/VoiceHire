"""VoiceHire Local – Development server with in-memory seeded repo + full email automation."""
import asyncio
import logging
import jwt
import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db, SessionLocal
from app.email.router import router as email_router
from app.email.queue import start_scheduler, stop_scheduler
from app.email.templates import seed_templates, seed_automation_rules
from app.voice.router import router as voice_router
from app.voice.repo import RecruitmentRepo, set_repo
from app.voice.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("voicehire")


# ─── In-memory demo repository ───────────────────────────────────────────────

class InMemoryRecruitmentRepo(RecruitmentRepo):
    """Demo repo with seeded data. Replace with your SQLAlchemy repo in production."""
    def __init__(self):
        self.assigned = []
        self.audits = []

    async def dashboard_metrics(self):
        return {"registered": 12, "overdue": 2, "pending_review": 3, "passed_technical": 5}

    async def search_candidates(self, status=None, query=None, limit=10):
        data = [
            {"id": "c1", "name": "Alice Johnson", "email": "alice@example.com", "status": "pending_review", "score": 88},
            {"id": "c2", "name": "Bob Smith", "email": "bob@example.com", "status": "passed_technical", "score": 94},
            {"id": "c3", "name": "Priya Sharma", "email": "priya@example.com", "status": "overdue", "score": None},
            {"id": "c4", "name": "David Lee", "email": "david@example.com", "status": "pending_review", "score": 76},
        ]
        if status:
            data = [c for c in data if c["status"] == status]
        if query:
            data = [c for c in data if query.lower() in c["name"].lower()]
        return data[:limit]

    async def review_queue(self):
        return [
            {"id": "c1", "name": "Alice Johnson", "assessment": "Python Challenge", "submitted_at": "2026-10-25"},
            {"id": "c4", "name": "David Lee", "assessment": "React Frontend", "submitted_at": "2026-10-24"},
        ]

    async def submissions(self, flt: str):
        if flt == "overdue":
            return [{"id": "c3", "name": "Priya Sharma", "due_date": "2026-10-24"}]
        if flt == "not_submitted":
            return [{"id": "c3", "name": "Priya Sharma"}, {"id": "c4", "name": "David Lee (late)"}]
        return [{"id": "c1", "name": "Alice Johnson", "submitted": True}]

    async def evaluation_report(self, candidate_id: str):
        return {"candidate_id": candidate_id, "summary": "Strong algorithm skills. Code is clean and well-tested."}

    async def assign_assessment(self, assessment: str, candidate_ids, eligible_only: bool):
        self.assigned.append((assessment, candidate_ids, eligible_only))
        return {"assigned_count": 3, "assessment": assessment}

    async def schedule_interviews(self, candidate_ids, start, minutes: int):
        return {"scheduled_count": len(candidate_ids), "start": str(start), "minutes": minutes}

    async def send_invitations(self, candidate_ids, kind: str):
        return {"sent_count": len(candidate_ids), "kind": kind}

    async def send_reminders(self, candidate_ids, overdue_only: bool):
        return {"reminders_sent": 1 if overdue_only else 3}

    async def advance_stage(self, candidate_id: str, stage: str):
        return {"candidate_id": candidate_id, "new_stage": stage}

    async def approve_feedback(self, candidate_id: str):
        return {"candidate_id": candidate_id, "feedback_approved": True}

    async def my_assignment(self, cid: str):
        return {"candidate_id": cid, "task": "Full-stack Python & React assessment",
                "repo_url": "https://github.com/sample/repo"}

    async def my_deadline(self, cid: str):
        return {"candidate_id": cid, "deadline": "2026-10-30 23:59 UTC", "days_left": 4}

    async def my_interview(self, cid: str):
        return {"candidate_id": cid, "scheduled_at": "2026-10-28 14:00 UTC", "interviewer": "Tech Lead"}

    async def my_submission(self, cid: str):
        return {"candidate_id": cid, "status": "In progress", "submitted": False}

    async def my_status(self, cid: str):
        return {"candidate_id": cid, "stage": "Technical Assessment", "updated_at": "2026-10-25"}

    async def my_released_feedback(self, cid: str):
        return {"candidate_id": cid, "feedback": "Completed coding screening with strong scores."}

    async def submit_repo(self, cid: str, url: str):
        return {"recorded": True, "repo_url": url}

    async def audit(self, entry: dict):
        self.audits.append(entry)
        logger.info("[AUDIT] %s", entry)


# ─── App lifecycle ────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("[STARTUP] Initialising database …")
    init_db()
    db = SessionLocal()
    try:
        seed_templates(db)
        seed_automation_rules(db)
        logger.info("[STARTUP] Email templates seeded.")
    finally:
        db.close()
    start_scheduler()
    logger.info("[STARTUP] Email scheduler started.")
    yield
    # Shutdown
    stop_scheduler()
    logger.info("[SHUTDOWN] Scheduler stopped.")


# ─── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="VoiceHire AI – Local Voice + Email Automation",
    description="Local-first recruitment platform. Voice assistant + full email automation. No cloud AI required.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

set_repo(InMemoryRecruitmentRepo())
app.include_router(voice_router)
app.include_router(email_router)


# ─── Helper: generate test tokens ────────────────────────────────────────────

@app.get("/token", tags=["dev"])
def get_sample_token(role: str = "recruiter", candidate_id: str = "c1"):
    """Dev helper – generate a JWT for Swagger UI / Postman / cURL testing."""
    settings = get_settings()
    payload = {"sub": "u1", "role": role}
    if role == "candidate":
        payload["candidate_id"] = candidate_id
    token = jwt.encode(payload, settings.jwt_secret or "dev-secret", algorithm="HS256")
    return {
        "token": token,
        "role": role,
        "authorization_header": f"Bearer {token}",
        "swagger_hint": "Click 'Authorize' in Swagger UI and paste the authorization_header value.",
    }


@app.get("/", tags=["dev"])
def root():
    return {
        "service": "VoiceHire AI",
        "docs": "http://localhost:8000/docs",
        "token_helper": "http://localhost:8000/token",
        "email_center": "http://localhost:8000/api/emails/jobs",
        "voice_health": "http://localhost:8000/api/voice/health",
    }


if __name__ == "__main__":
    uvicorn.run("run_server:app", host="127.0.0.1", port=8000, reload=True)
