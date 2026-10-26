"""Turn handler: local LLM proposes tool calls; the backend validates/authorizes/executes them.
Consequential actions are confirmed by the user (yes/no or buttons), never by the model."""
import json, re, time
from . import tools
from .config import get_settings, system_prompt
from .services.base import LLMService

YES = re.compile(r"^\W*(yes|yeah|yep|confirm(ed)?|go ahead|do it|proceed|ok|okay)\b", re.I)
NO = re.compile(r"^\W*(no|nope|cancel|stop|don'?t|never mind)\b", re.I)


class Conversations:
    def __init__(self, max_msgs: int = 12, ttl: int = 1800):
        self.max, self.ttl, self._h = max_msgs, ttl, {}

    def get(self, uid: str) -> list[dict]:
        now = time.time()
        self._h = {k: v for k, v in self._h.items() if v[0] > now}
        return list(self._h.get(uid, (0, []))[1])

    def add(self, uid: str, *msgs: dict):
        hist = (self.get(uid) + list(msgs))[-self.max:]
        self._h[uid] = (time.time() + self.ttl, hist)

    def clear(self, uid: str):
        self._h.pop(uid, None)
        PENDING.pop(uid, None)


CONVOS = Conversations()
PENDING: dict[str, dict] = {}  # user_id -> {"id", "summary"}


def describe(res: dict) -> str:
    st = res.get("status")
    if st == "ok":
        return "Done. " + json.dumps(res.get("data"), default=str)[:300]
    if st in ("cancelled", "simulated"):
        return res.get("message", st)
    return f"That did not complete: {res.get('message', 'unknown error')} Nothing is confirmed as done."


async def resolve_pending(approve: bool, ctx: tools.Ctx) -> dict:
    p = PENDING.pop(ctx.user_id, None)
    if not p:
        return {"reply": "There is nothing waiting for confirmation.", "source": "system", "tool_events": [], "pending": None}
    res = await tools.confirm(p["id"], approve, ctx)
    reply = describe(res)
    CONVOS.add(ctx.user_id, {"role": "assistant", "content": reply})
    return {"reply": reply, "source": "system", "tool_events": [], "pending": None, "result": res}


def _args(c: dict) -> dict:
    a = c.get("function", {}).get("arguments") or {}
    if isinstance(a, str):
        try:
            a = json.loads(a)
        except ValueError:
            a = {}
    return a if isinstance(a, dict) else {}


async def handle_turn(text: str, ctx: tools.Ctx, llm: LLMService) -> dict:
    uid = ctx.user_id
    if uid in PENDING and YES.match(text):
        return await resolve_pending(True, ctx)
    if uid in PENDING and NO.match(text):
        return await resolve_pending(False, ctx)

    s = get_settings()
    schemas = tools.tool_schemas(ctx.role)
    user_msg = {"role": "user", "content": text}
    messages = [{"role": "system", "content": system_prompt(ctx.role)}, *CONVOS.get(uid), user_msg]
    events, new_pending, reply = [], None, ""
    for _ in range(s.llm_max_tool_rounds):
        msg = await llm.chat(messages, schemas)
        messages.append(msg)
        calls = msg.get("tool_calls") or []
        if not calls:
            reply = (msg.get("content") or "").strip()
            break
        for c in calls:
            name = c.get("function", {}).get("name", "")
            res = await tools.execute(name, _args(c), ctx)
            events.append({"tool": name, "status": res["status"], "message": res.get("message")})
            if res["status"] == "confirmation_required":
                new_pending = {"id": res["confirmation_id"], "summary": res["summary"]}
            messages.append({"role": "tool", "tool_name": name, "content": json.dumps(res, default=str)[:4000]})
    else:
        reply = "I could not finish that request. Please rephrase it or ask for one thing at a time."
    if new_pending:  # deterministic wording: the model must never claim a pending action is done
        PENDING[uid] = new_pending
        reply = f"I need your confirmation before I do this: {new_pending['summary']}. Say yes to confirm or no to cancel."
    elif not reply:
        reply = "I could not produce an answer. Please try again."
    CONVOS.add(uid, user_msg, {"role": "assistant", "content": reply})
    return {"reply": reply, "source": "ollama", "tool_events": events, "pending": new_pending}
