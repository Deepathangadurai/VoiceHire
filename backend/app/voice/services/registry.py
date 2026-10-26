from functools import lru_cache
from ..config import get_settings
from ..errors import ServiceError
from .base import LLMService, STTService, TTSService
from .ollama_llm import OllamaLLM
from .piper_tts import PiperTTS
from .whisper_stt import FasterWhisperSTT


def _pick(kind: str, name: str, table: dict, s):
    if name not in table:
        raise ServiceError("bad_config", f"Unsupported {kind} provider '{name}'. Supported: {', '.join(table)}.", 500)
    return table[name](s)


@lru_cache  # singletons: models are never loaded twice
def get_llm() -> LLMService: s = get_settings(); return _pick("LLM", s.llm_provider, {"ollama": OllamaLLM}, s)
@lru_cache
def get_stt() -> STTService: s = get_settings(); return _pick("STT", s.stt_provider, {"faster-whisper": FasterWhisperSTT}, s)
@lru_cache
def get_tts() -> TTSService: s = get_settings(); return _pick("TTS", s.tts_provider, {"piper": PiperTTS}, s)
