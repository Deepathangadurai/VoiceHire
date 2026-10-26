import asyncio
from contextlib import contextmanager

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field

from . import agent, demo, tools
from .audio import save_upload
from .config import get_settings
from .deps import VoiceUser, get_voice_user
from .errors import ServiceError
from .repo import get_repo
from .services.registry import get_llm, get_stt, get_tts

router = APIRouter(prefix="/api/voice", tags=["voice"])  # app.include_router(router)


@contextmanager
def svc():
    try:
        yield
    except ServiceError as e:
        raise HTTPException(e.status, detail={"code": e.code, "message": e.message})


def _ctx(u: VoiceUser) -> tools.Ctx:
    return tools.Ctx(u.user_id, u.role, u.candidate_id, get_repo(), get_settings().real_actions)


class Text(BaseModel):
    text: str = Field(min_length=1, max_length=1000)

class Confirm(BaseModel):
    approve: bool


@router.get("/health")
async def health(u: VoiceUser = Depends(get_voice_user)):
    s = get_settings()
    llm, stt, tts = await asyncio.gather(get_llm().health(), get_stt().health(), get_tts().health())
    return {"local_ai": True, "cloud_services": False, "role": u.role, "dry_run": s.dry_run, "llm": llm, "stt": stt, "tts": tts,
            "limits": {"audio_max_seconds": s.audio_max_seconds, "audio_max_bytes": s.audio_max_bytes}}


@router.post("/stt")
async def speech_to_text(audio: UploadFile = File(...), u: VoiceUser = Depends(get_voice_user)):
    s = get_settings()
    with svc():
        path = await save_upload(audio, s.audio_max_bytes)
        try:
            text = await get_stt().transcribe(str(path))
        finally:
            path.unlink(missing_ok=True)  # audio never persists
    return {"text": text, "empty": not text}


@router.post("/chat")
async def chat(body: Text, u: VoiceUser = Depends(get_voice_user)):
    ctx = _ctx(u)
    try:
        return await agent.handle_turn(body.text, ctx, get_llm())
    except ServiceError as e:
        hit = demo.route(u.role, body.text) if get_settings().demo_fallback and e.code in ("llm_unavailable", "llm_timeout") else None
        if not hit:
            raise HTTPException(e.status, detail={"code": e.code, "message": e.message})
        res = await tools.execute(hit[0], hit[1], ctx)
        txt = str(res.get("data", res.get("message")))[:600]
        return {"reply": f"Demo mode, no AI model ({e.message}) Raw data: {txt}", "source": "demo", "pending": None,
                "tool_events": [{"tool": hit[0], "status": res["status"]}]}


@router.post("/confirm")
async def confirm(body: Confirm, u: VoiceUser = Depends(get_voice_user)):
    return await agent.resolve_pending(body.approve, _ctx(u))


@router.post("/tts")
async def text_to_speech(body: Text, u: VoiceUser = Depends(get_voice_user)):
    with svc():
        wav = await get_tts().synthesize(body.text)
    return Response(wav, media_type="audio/wav", headers={"Cache-Control": "no-store"})


@router.post("/reset")
async def reset(u: VoiceUser = Depends(get_voice_user)):
    agent.CONVOS.clear(u.user_id)
    return {"ok": True}
