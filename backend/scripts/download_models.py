"""One-time model download (run during setup, NOT at app start):  python scripts/download_models.py"""
import shutil, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.voice.config import get_settings  # noqa: E402

s = get_settings()
print(f"[1/3] faster-whisper model '{s.stt_model}' -> {s.stt_model_dir}")
from faster_whisper.utils import download_model  # noqa: E402
Path(s.stt_model_dir).mkdir(parents=True, exist_ok=True)
download_model(s.stt_model, cache_dir=s.stt_model_dir)

voice = Path(s.piper_voice_path)
print(f"[2/3] Piper voice '{voice.stem}' -> {voice.parent}")
voice.parent.mkdir(parents=True, exist_ok=True)
subprocess.check_call([sys.executable, "-m", "piper.download_voices", voice.stem], cwd=voice.parent)

print(f"[3/3] Ollama model '{s.ollama_model}'")
if shutil.which("ollama"):
    subprocess.check_call(["ollama", "pull", s.ollama_model])
else:
    print(f"Ollama CLI not found. Install from https://ollama.com then run: ollama pull {s.ollama_model}")
print("Done. Check status with GET /api/voice/health")
