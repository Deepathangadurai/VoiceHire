"""Recruitment data boundary. FastAPI + PostgreSQL stay the source of truth.

Implement this class on top of YOUR existing SQLAlchemy models/services (email, scheduler, GitHub).
Candidate methods receive the authenticated candidate_id ONLY from the server-side auth context.
Return plain dicts. Candidate methods must return only released/authorized fields.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class RecruitmentRepo(ABC):
    # ---- recruiter reads
    @abstractmethod
    async def dashboard_metrics(self) -> dict[str, Any]: ...
    @abstractmethod
    async def search_candidates(self, status: str | None, query: str | None, limit: int) -> list[dict]: ...
    @abstractmethod
    async def review_queue(self) -> list[dict]: ...
    @abstractmethod
    async def submissions(self, flt: str) -> list[dict]: ...
    @abstractmethod
    async def evaluation_report(self, candidate_id: str) -> dict: ...
    # ---- recruiter writes (called only after confirmation)
    @abstractmethod
    async def assign_assessment(self, assessment: str, candidate_ids: list[str] | None, eligible_only: bool) -> dict: ...
    @abstractmethod
    async def schedule_interviews(self, candidate_ids: list[str], start: datetime, minutes: int) -> dict: ...
    @abstractmethod
    async def send_invitations(self, candidate_ids: list[str], kind: str) -> dict: ...
    @abstractmethod
    async def send_reminders(self, candidate_ids: list[str] | None, overdue_only: bool) -> dict: ...
    @abstractmethod
    async def advance_stage(self, candidate_id: str, stage: str) -> dict: ...
    @abstractmethod
    async def approve_feedback(self, candidate_id: str) -> dict: ...
    # ---- candidate (own data only)
    @abstractmethod
    async def my_assignment(self, cid: str) -> dict | None: ...
    @abstractmethod
    async def my_deadline(self, cid: str) -> dict | None: ...
    @abstractmethod
    async def my_interview(self, cid: str) -> dict | None: ...
    @abstractmethod
    async def my_submission(self, cid: str) -> dict | None: ...
    @abstractmethod
    async def my_status(self, cid: str) -> dict | None: ...
    @abstractmethod
    async def my_released_feedback(self, cid: str) -> dict | None: ...
    @abstractmethod
    async def submit_repo(self, cid: str, url: str) -> dict: ...
    # ---- audit
    @abstractmethod
    async def audit(self, entry: dict) -> None: ...


_repo: RecruitmentRepo | None = None


def set_repo(repo: RecruitmentRepo) -> None:
    """Call once at app startup: set_repo(MySqlAlchemyRepo(session_factory))."""
    global _repo
    _repo = repo


def get_repo() -> RecruitmentRepo:
    if _repo is None:
        raise RuntimeError("Voice repo not configured. Call app.voice.repo.set_repo(...) at startup.")
    return _repo
