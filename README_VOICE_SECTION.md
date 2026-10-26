<!-- Paste into README.md -->
## Voice assistant (free, local-first)

Recruiters and candidates can talk to VoiceHire AI. Everything runs on your machine with no API keys:
**Ollama** (local LLM) + **faster-whisper** (speech-to-text) + **Piper** (text-to-speech), behind FastAPI tools that enforce permissions.

Quick start (Windows details in `docs/SETUP_WINDOWS.md`):
1. Install Ollama, then `pip install -r backend/requirements-voice.txt`
2. `copy .env.example .env`, then `python backend/scripts/download_models.py` (one-time download)
3. Start the backend and frontend as usual; open the recruiter dashboard or candidate portal; check the status badges in the voice panel.

Status: implemented, not yet verified end to end. Follow `docs/TESTING.md` before relying on it. Latency depends on your hardware; nothing here is claimed as real-time.
