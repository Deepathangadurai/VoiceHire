import asyncio, io, threading, wave
from pathlib import Path
from ..config import VoiceSettings
from ..errors import ServiceError
from .base import TTSService


class PiperTTS(TTSService):
    """Piper (piper-tts, GPL-3.0). Needs <voice>.onnx and <voice>.onnx.json from scripts/download_models.py."""
    name = "piper"

    def __init__(self, s: VoiceSettings):
        self.s, self._voice, self._lock, self._sem = s, None, threading.Lock(), asyncio.Semaphore(1)

    def _load(self):
        if self._voice is None:
            with self._lock:
                if self._voice is None:
                    p = Path(self.s.piper_voice_path)
                    if not p.exists() or not Path(str(p) + ".json").exists():
                        raise ServiceError("tts_voice_missing", f"Piper voice files not found at {p}. Run: python scripts/download_models.py")
                    try:
                        from piper import PiperVoice
                    except ImportError:
                        raise ServiceError("tts_unavailable", "Piper is not installed. Run: pip install piper-tts")
                    try:
                        self._voice = PiperVoice.load(str(p))
                    except Exception:
                        raise ServiceError("tts_failed", "Piper could not load the voice model.")
        return self._voice

    def _run(self, text: str) -> bytes:
        voice = self._load()
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            voice.synthesize_wav(text, wf)
        return buf.getvalue()

    async def synthesize(self, text: str) -> bytes:
        async with self._sem:
            try:
                return await asyncio.wait_for(asyncio.to_thread(self._run, text[: self.s.tts_max_chars]), self.s.tts_timeout_seconds)
            except asyncio.TimeoutError:
                raise ServiceError("tts_timeout", "Speech generation took too long. The reply is available as text.", 504)
            except ServiceError:
                raise
            except Exception:
                raise ServiceError("tts_failed", "Speech generation failed. The reply is available as text.", 500)

    async def health(self) -> dict:
        try:
            await asyncio.to_thread(self._load)
        except ServiceError as e:
            return {"ok": False, "provider": self.name, "detail": e.message}
        return {"ok": True, "provider": self.name, "voice": Path(self.s.piper_voice_path).stem, "detail": "ready"}
