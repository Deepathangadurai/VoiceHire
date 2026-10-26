import asyncio, io
from app.voice import agent, audio, tools
from app.voice.errors import ServiceError
from app.voice.services.base import LLMService
from tests.test_voice_tools import Seed, ctx

run = asyncio.run


class FakeLLM(LLMService):
    """Scripted model: lets us test grounding/confirmation without Ollama."""
    name = "fake"
    def __init__(self, *msgs): self.msgs, self.calls = list(msgs), 0
    async def chat(self, messages, tools): self.calls += 1; return self.msgs.pop(0)
    async def health(self): return {"ok": True}

def call(name, **a): return {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": name, "arguments": a}}]}
def say(t): return {"role": "assistant", "content": t}


def test_read_tool_result_is_used_and_reported():
    agent.CONVOS.clear("u1")
    llm = FakeLLM(call("get_dashboard_metrics"), say("3 candidates registered."))
    out = run(agent.handle_turn("how many registered?", ctx(Seed()), llm))
    assert out["tool_events"][0]["status"] == "ok" and "3" in out["reply"]

def test_model_cannot_claim_pending_action_is_done():
    agent.CONVOS.clear("u1")
    repo = Seed()
    llm = FakeLLM(call("assign_assessment", assessment="Python", eligible_only=True), say("Done! All assigned."))
    out = run(agent.handle_turn("assign python", ctx(repo), llm))
    assert out["pending"] and "confirmation" in out["reply"] and repo.assigned == []
    done = run(agent.handle_turn("yes", ctx(repo), FakeLLM()))
    assert repo.assigned and done["reply"].startswith("Done")

def test_no_cancels():
    agent.CONVOS.clear("u1")
    repo = Seed()
    run(agent.handle_turn("assign", ctx(repo), FakeLLM(call("assign_assessment", assessment="Py", eligible_only=True), say("ok"))))
    out = run(agent.handle_turn("no", ctx(repo), FakeLLM()))
    assert repo.assigned == [] and "Cancelled" in out["reply"]

def test_candidate_model_cannot_use_recruiter_tool():
    agent.CONVOS.clear("u1")
    llm = FakeLLM(call("get_dashboard_metrics"), say("I cannot access that."))
    out = run(agent.handle_turn("show metrics", ctx(Seed(), "candidate"), llm))
    assert out["tool_events"][0]["status"] == "error"

def test_audio_sniffing():
    assert audio.sniff(b"\x1a\x45\xdf\xa3" + b"0" * 12) and audio.sniff(b"RIFF\0\0\0\0WAVE")
    assert not audio.sniff(b"MZ\x90\x00" + b"0" * 12) and not audio.sniff(b"<html>" + b"0" * 10)

def test_upload_limits_and_cleanup():
    class F:
        def __init__(self, ct, data): self.content_type, self.b = ct, io.BytesIO(data)
        async def read(self, n): return self.b.read(n)
    ok = b"OggS" + b"0" * 100
    p = run(audio.save_upload(F("audio/ogg", ok), 1000)); assert p.exists(); p.unlink()
    for ct, data, code in [("text/plain", ok, "bad_audio_type"), ("audio/ogg", b"MZ" + b"0" * 50, "bad_audio_content"), ("audio/ogg", ok * 50, "audio_too_large")]:
        try: run(audio.save_upload(F(ct, data), 1000)); assert False
        except ServiceError as e: assert e.code == code

def test_remote_ollama_rejected_by_default():
    from app.voice.config import VoiceSettings
    try: VoiceSettings(OLLAMA_BASE_URL="http://203.0.113.5:11434"); assert False
    except ValueError: pass
    assert VoiceSettings(OLLAMA_BASE_URL="http://localhost:11434").real_actions
