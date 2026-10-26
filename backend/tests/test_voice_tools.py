import asyncio
from datetime import datetime, timedelta, timezone
from app.voice import tools
from app.voice.repo import RecruitmentRepo


class Seed(RecruitmentRepo):
    def __init__(self): self.assigned, self.audits = [], []
    async def dashboard_metrics(self): return {"registered": 3}
    async def search_candidates(self, s, q, l): return []
    async def review_queue(self): return []
    async def submissions(self, f): return []
    async def evaluation_report(self, c): return {}
    async def assign_assessment(self, a, ids, e): self.assigned.append((a, ids, e)); return {"assigned": ids}
    async def schedule_interviews(self, *a): return {}
    async def send_invitations(self, *a): return {}
    async def send_reminders(self, *a): return {}
    async def advance_stage(self, *a): return {}
    async def approve_feedback(self, c): return {}
    async def my_assignment(self, cid): return {"candidate": cid, "task": "Python"}
    async def my_deadline(self, cid): return None
    async def my_interview(self, cid): return None
    async def my_submission(self, cid): return None
    async def my_status(self, cid): return None
    async def my_released_feedback(self, cid): return None
    async def submit_repo(self, cid, url): return {"recorded": True}
    async def audit(self, e): self.audits.append(e)


def ctx(repo, role="recruiter", uid="u1", real=True):
    return tools.Ctx(uid, role, "c1" if role == "candidate" else None, repo, real)

run = asyncio.run
ASSIGN = {"assessment": "Python", "eligible_only": True}


def test_candidate_cannot_use_recruiter_tool():
    assert run(tools.execute("get_dashboard_metrics", {}, ctx(Seed(), "candidate")))["code"] == "forbidden"

def test_candidate_cannot_pass_other_identity():
    assert run(tools.execute("get_my_assignment", {"candidate_id": "c2"}, ctx(Seed(), "candidate")))["code"] == "invalid_arguments"

def test_candidate_own_data_and_unavailable_is_explicit():
    repo = Seed()
    assert run(tools.execute("get_my_assignment", {}, ctx(repo, "candidate")))["data"]["candidate"] == "c1"
    assert run(tools.execute("get_my_deadline", {}, ctx(repo, "candidate")))["data"]["available"] is False

def test_confirmation_then_execution_and_single_use():
    repo, store = Seed(), tools.ConfirmationStore()
    r = run(tools.execute("assign_assessment", ASSIGN, ctx(repo), store))
    assert r["status"] == "confirmation_required" and repo.assigned == []
    assert run(tools.confirm(r["confirmation_id"], True, ctx(repo), store))["status"] == "ok"
    assert len(repo.assigned) == 1 and any(a["event"] == "executed" for a in repo.audits)
    assert run(tools.confirm(r["confirmation_id"], True, ctx(repo), store))["code"] == "not_found"

def test_other_user_cannot_confirm():
    repo, store = Seed(), tools.ConfirmationStore()
    r = run(tools.execute("assign_assessment", ASSIGN, ctx(repo), store))
    assert run(tools.confirm(r["confirmation_id"], True, ctx(repo, uid="evil"), store))["code"] == "not_found"

def test_demo_mode_does_not_execute():
    repo, store = Seed(), tools.ConfirmationStore()
    r = run(tools.execute("assign_assessment", ASSIGN, ctx(repo, real=False), store))
    assert run(tools.confirm(r["confirmation_id"], True, ctx(repo, real=False), store))["status"] == "simulated"
    assert repo.assigned == []

def test_validation_rejects_bad_args():
    repo = Seed()
    assert run(tools.execute("assign_assessment", {"assessment": "x"}, ctx(repo)))["code"] == "invalid_arguments"
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    assert run(tools.execute("schedule_interview", {"candidate_ids": ["c1"], "start": past}, ctx(repo)))["code"] == "invalid_arguments"
    assert run(tools.execute("submit_github_repository", {"repo_url": "https://evil.com/a/b"}, ctx(repo, "candidate")))["code"] == "invalid_arguments"

def test_candidate_schemas_hide_recruiter_tools():
    names = {t["function"]["name"] for t in tools.tool_schemas("candidate")}
    assert "assign_assessment" not in names and "get_my_interview" in names
