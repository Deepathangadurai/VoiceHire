import asyncio, threading
from ..config import VoiceSettings
from ..errors import ServiceError
from .base import STTService


class FasterWhisperSTT(STTService):
    """One model instance per process, loaded lazily from local files only (download once with scripts/download_models.py)."""
    name = "faster-whisper"

    def __init__(self, s: VoiceSettings):
        self.s, self._model, self._lock, self._sem = s, None, threading.Lock(), asyncio.Semaphore(1)

    def _load(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    try:
                        from faster_whisper import WhisperModel
                    except ImportError:
                        raise ServiceError("stt_unavailable", "faster-whisper is not installed. Run: pip install faster-whisper")
                    try:
                        self._model = WhisperModel(self.s.stt_model, device=self.s.stt_device, compute_type=self.s.stt_compute_type,
                                                   download_root=self.s.stt_model_dir, local_files_only=True)
                    except Exception:
                        raise ServiceError("stt_model_missing", f"Whisper model '{self.s.stt_model}' is not downloaded. Run: python scripts/download_models.py")
        return self._model

    def _run(self, path: str) -> str:
        model = self._load()
        segments, info = model.transcribe(path, language=self.s.stt_language or None, vad_filter=True, beam_size=1)
        if info.duration > self.s.audio_max_seconds:
            raise ServiceError("audio_too_long", f"Audio is longer than {self.s.audio_max_seconds} seconds.", 413)
        return " ".join(seg.text.strip() for seg in segments).strip()

    async def transcribe(self, path: str) -> str:
        async with self._sem:  # one transcription at a time; keeps CPU/RAM predictable
            try:
                return await asyncio.wait_for(asyncio.to_thread(self._run, path), self.s.stt_timeout_seconds)
            except asyncio.TimeoutError:
                raise ServiceError("stt_timeout", "Transcription took too long. Use a shorter recording, a smaller STT_MODEL, or type instead.", 504)
            except ServiceError:
                raise
            except Exception:
                raise ServiceError("stt_failed", "The audio could not be decoded or transcribed. Try again or type instead.", 422)

    async def health(self) -> dict:
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            return {"ok": False, "provider": self.name, "detail": "faster-whisper is not installed."}
        try:
            await asyncio.to_thread(self._load)
        except ServiceError as e:
            return {"ok": False, "provider": self.name, "model": self.s.stt_model, "detail": e.message}
        return {"ok": True, "provider": self.name, "model": self.s.stt_model, "detail": "ready"}
