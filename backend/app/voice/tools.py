"""Controlled tool layer: role check -> argument validation -> confirmation -> execution -> audit.
The LLM never touches SQL, shell or arbitrary HTTP; it can only name a tool from this registry."""
import json, logging, time, uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from .repo import RecruitmentRepo

log = logging.getLogger("voice.audit")
CID = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
Stage = Literal["registered", "assessment_assigned", "submitted", "under_review", "interview", "offer", "rejected"]


@dataclass(frozen=True)
class Ctx:
    user_id: str
    role: Literal["recruiter", "candidate"]
    candidate_id: str | None
    repo: RecruitmentRepo
    real_actions: bool


class Args(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown args (e.g. candidate_id on candidate tools) are rejected


class NoArgs(Args): ...
class SearchArgs(Args):
    status: Literal["registered", "pending_review", "assessment_assigned", "submitted", "passed_technical", "interview", "rejected"] | None = None
    query: str | None = Field(None, max_length=80)
    limit: int = Field(10, ge=1, le=25)
class SubArgs(Args):
    filter: Literal["all", "not_submitted", "overdue"] = "all"
class AssignArgs(Args):
    assessment: str = Field(min_length=1, max_length=100)
    candidate_ids: list[str] | None = Field(None, max_length=50)
    eligible_only: bool = False
    @model_validator(mode="after")
    def _sel(self):
        if not self.candidate_ids and not self.eligible_only:
            raise ValueError("choose candidate_ids or eligible_only=true")
        return self
class InterviewArgs(Args):
    candidate_ids: list[str] = Field(min_length=1, max_length=50)
    start: datetime
    duration_minutes: int = Field(45, ge=15, le=180)
    @field_validator("start")
    @classmethod
    def _future(cls, v):
        if v.tzinfo is None:
            raise ValueError("start must include a timezone offset")
        if v <= datetime.now(timezone.utc):
            raise ValueError("start must be in the future")
        return v
class InviteArgs(Args):
    candidate_ids: list[str] = Field(min_length=1, max_length=50)
    kind: Literal["task", "interview"]
class ReminderArgs(Args):
    candidate_ids: list[str] | None = Field(None, max_length=50)
    overdue_only: bool = True
class AdvanceArgs(Args):
    candidate_id: str = CID
    stage: Stage
class OneCandidate(Args):
    candidate_id: str = CID
class RepoArgs(Args):
    repo_url: str = Field(pattern=r"^https://github\.com/[\w.-]+/[\w.-]+/?$", max_length=200)


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    roles: frozenset
    args: type[Args]
    handler: Callable[[Ctx, Any], Awaitable[Any]]
    consequential: bool = False


R, C = frozenset({"recruiter"}), frozenset({"candidate"})


def _me(ctx: Ctx) -> str:
    if not ctx.candidate_id:
        raise PermissionError("no candidate identity")
    return ctx.candidate_id


async def _mine(coro):  # unavailable data must be stated, never invented
    v = await coro
    return v if v is not None else {"available": False, "note": "Not available or not yet released."}

TOOLS: dict[str, Tool] = {t.name: t for t in [
    Tool("get_dashboard_metrics", "Counts of candidates by stage, pending reviews, overdue submissions.", R, NoArgs, lambda c, a: c.repo.dashboard_metrics()),
    Tool("search_candidates", "Find candidates by status or name/email text.", R, SearchArgs, lambda c, a: c.repo.search_candidates(a.status, a.query, a.limit)),
    Tool("get_review_queue", "Reviews awaiting approval.", R, NoArgs, lambda c, a: c.repo.review_queue()),
    Tool("get_submission_status", "Submissions: all, not_submitted, or overdue.", R, SubArgs, lambda c, a: c.repo.submissions(a.filter)),
    Tool("get_evaluation_report", "Evaluation report for one candidate.", R, OneCandidate, lambda c, a: c.repo.evaluation_report(a.candidate_id)),
    Tool("assign_assessment", "Assign an assessment to listed candidates or all eligible ones. Requires confirmation.", R, AssignArgs,
         lambda c, a: c.repo.assign_assessment(a.assessment, a.candidate_ids, a.eligible_only), True),
    Tool("schedule_interview", "Schedule interviews. Requires confirmation.", R, InterviewArgs,
         lambda c, a: c.repo.schedule_interviews(a.candidate_ids, a.start, a.duration_minutes), True),
    Tool("send_invitation", "Send task or interview invitation emails. Requires confirmation.", R, InviteArgs,
         lambda c, a: c.repo.send_invitations(a.candidate_ids, a.kind), True),
    Tool("send_submission_reminder", "Email submission reminders. Requires confirmation.", R, ReminderArgs,
         lambda c, a: c.repo.send_reminders(a.candidate_ids, a.overdue_only), True),
    Tool("advance_candidate_stage", "Change a candidate's stage. Requires confirmation.", R, AdvanceArgs,
         lambda c, a: c.repo.advance_stage(a.candidate_id, a.stage), True),
    Tool("approve_candidate_feedback", "Release reviewed feedback to the candidate. Requires confirmation.", R, OneCandidate,
         lambda c, a: c.repo.approve_feedback(a.candidate_id), True),
    # candidate tools: identity comes ONLY from the auth context, never from model arguments
    Tool("get_my_assignment", "My assigned task and requirements.", C, NoArgs, lambda c, a: _mine(c.repo.my_assignment(_me(c)))),
    Tool("get_my_deadline", "My submission deadline.", C, NoArgs, lambda c, a: _mine(c.repo.my_deadline(_me(c)))),
    Tool("get_my_interview", "My interview time and meeting link.", C, NoArgs, lambda c, a: _mine(c.repo.my_interview(_me(c)))),
    Tool("get_my_submission_status", "Whether my submission was recorded.", C, NoArgs, lambda c, a: _mine(c.repo.my_submission(_me(c)))),
    Tool("get_my_application_status", "My application status (released info only).", C, NoArgs, lambda c, a: _mine(c.repo.my_status(_me(c)))),
    Tool("get_my_released_feedback", "Feedback released to me.", C, NoArgs, lambda c, a: _mine(c.repo.my_released_feedback(_me(c)))),
    Tool("submit_github_repository", "Submit my GitHub repository URL. Requires confirmation.", C, RepoArgs,
         lambda c, a: c.repo.submit_repo(_me(c), a.repo_url), True),
]}


def _simplify(s):
    """Plain JSON-schema (no titles, no null-unions): small local models call these more reliably."""
    if isinstance(s, dict):
        s = {k: _simplify(v) for k, v in s.items() if k != "title"}
        opts = [o for o in s.get("anyOf", []) if o.get("type") != "null"]
        if "anyOf" in s and len(opts) == 1:
            s.pop("anyOf"); s.update(opts[0])
        return s
    return [_simplify(i) for i in s] if isinstance(s, list) else s


def tool_schemas(role: str) -> list[dict]:
    """Ollama tool format. Only tools allowed for the role are shown to the model (backend re-checks every call)."""
    return [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": _simplify(t.args.model_json_schema())}}
            for t in TOOLS.values() if role in t.roles]


class ConfirmationStore:
    """In-memory; use Redis/DB if you run multiple workers."""
    def __init__(self, ttl: int = 120):
        self.ttl, self._d = ttl, {}

    def put(self, user_id: str, tool: str, args: Args) -> str:
        cid = uuid.uuid4().hex
        self._d[cid] = (user_id, tool, args, time.time() + self.ttl)
        return cid

    def take(self, cid: str, user_id: str):
        now = time.time()
        self._d = {k: v for k, v in self._d.items() if v[3] > now}
        item = self._d.get(cid)
        if not item or item[0] != user_id:
            return None
        del self._d[cid]
        return item


STORE = ConfirmationStore()


def _err(code: str, msg: str) -> dict:
    return {"status": "error", "code": code, "message": msg}


async def _audit(ctx: Ctx, tool: str, event: str, args: Any = None, result: Any = None):
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "user": ctx.user_id, "role": ctx.role, "tool": tool, "event": event,
             "args": args.model_dump(mode="json", exclude_none=True) if isinstance(args, BaseModel) else args,
             "result_status": result.get("status") if isinstance(result, dict) else None}
    log.info(json.dumps(entry, default=str))
    try:
        await ctx.repo.audit(entry)
    except Exception:  # audit-store failure is logged, never silently swallowed
        log.exception("audit persistence failed")


async def _run(ctx: Ctx, tool: Tool, args: Args) -> dict:
    try:
        return {"status": "ok", "data": await tool.handler(ctx, args)}
    except PermissionError:
        return _err("forbidden", "Not permitted.")
    except Exception:
        log.exception("tool %s failed", tool.name)
        return _err("tool_failed", "The operation failed. Do not assume anything was changed or sent; check the dashboard.")


async def execute(name: str, raw: dict | None, ctx: Ctx, store: ConfirmationStore = STORE) -> dict:
    tool = TOOLS.get(name)
    if not tool or ctx.role not in tool.roles:
        await _audit(ctx, name, "denied")
        return _err("forbidden", "This tool is not available for your account.")
    try:
        args = tool.args.model_validate(raw or {})
    except ValidationError as e:
        return _err("invalid_arguments", "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()))
    if tool.consequential:
        cid = store.put(ctx.user_id, name, args)
        await _audit(ctx, name, "confirmation_requested", args)
        return {"status": "confirmation_required", "confirmation_id": cid,
                "summary": f"{name}: {args.model_dump_json(exclude_none=True)}",
                "instruction": "Read this summary to the user and ask them to confirm or cancel. Nothing has been done yet."}
    return await _run(ctx, tool, args)


async def confirm(confirmation_id: str, approve: bool, ctx: Ctx, store: ConfirmationStore = STORE) -> dict:
    item = store.take(confirmation_id, ctx.user_id)
    if not item:
        return _err("not_found", "Confirmation expired, already used, or not yours.")
    _, name, args, _ = item
    tool = TOOLS[name]
    if ctx.role not in tool.roles:  # re-check at execution time
        return _err("forbidden", "Not permitted.")
    if not approve:
        await _audit(ctx, name, "cancelled", args)
        return {"status": "cancelled", "message": "Cancelled. Nothing was changed."}
    if not ctx.real_actions:
        await _audit(ctx, name, "simulated", args)
        return {"status": "simulated", "message": "Demo mode: confirmed but NOT executed. No emails sent, no records changed."}
    result = await _run(ctx, tool, args)
    await _audit(ctx, name, "executed", args, result)
    return result
