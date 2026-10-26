# Windows setup (no Docker, no API keys)

## Hardware (estimates, not measurements: measure on your machine)
| RAM / GPU | Suggested `OLLAMA_MODEL` | Suggested `STT_MODEL` |
|---|---|---|
| 8 GB, CPU only | `llama3.2:3b` (default) | `base.en` or `tiny.en` |
| 16 GB, CPU only | `qwen2.5:7b` (slow on CPU) or stay on 3B | `base.en` / `small.en` |
| 16 GB + NVIDIA GPU (8 GB VRAM) | `qwen2.5:7b` or `llama3.1:8b` | `small.en` (`STT_DEVICE=cuda`, needs CUDA libraries) |
Chosen model must support tool calling. Start small; larger models give better tool selection but slower replies.
Check what is loaded and how much memory it uses with `ollama ps`.

## Steps
1. **Prerequisites:** Python 3.10+, Node 18+, your existing PostgreSQL. (ffmpeg is not required.)
2. **Ollama:** install from https://ollama.com, then in PowerShell: `ollama pull llama3.2:3b` and `ollama list`. It listens on `http://127.0.0.1:11434` by default. Do not expose that port.
3. **Python deps:** `cd backend`, `python -m venv .venv`, `.venv\Scripts\activate`, `pip install -r requirements-voice.txt`.
   If `piper-tts` fails to install, upgrade pip and use a supported Python version (see the Piper repo).
4. **Config:** `copy ..\.env.example ..\.env` (or place values in `backend\.env`); set `JWT_SECRET` and tune models.
5. **Download models once:** `python scripts\download_models.py` (Whisper model, Piper voice via `python -m piper.download_voices`, and `ollama pull`).
   The app never downloads models at startup; missing models give an error with the exact command to run.
6. **Wire into your app:** `set_repo(YourRepo(...))`, include `app.voice.router.router`, replace `deps.get_voice_user` with your auth.
7. **Run:** make sure Ollama is running (tray icon), then start the backend (`uvicorn ...`) and frontend (`npm run dev`).
8. **Microphone:** use `http://localhost` (or HTTPS). On first use the browser asks for permission; if blocked, click the lock icon in the address bar -> Site settings -> Microphone -> Allow. Check Windows Settings -> Privacy -> Microphone allows desktop/browser apps.
9. Open the voice panel and confirm all three status lines show "ready" (also `GET /api/voice/health`).

## Troubleshooting
| Symptom | Fix |
|---|---|
| "Ollama is not running" | Start Ollama from the Start menu or `ollama serve`; check `OLLAMA_BASE_URL` |
| "Model ... is not installed" | `ollama pull <OLLAMA_MODEL>` |
| "does not support tool calling" | Choose a tool-capable model (e.g. `llama3.2:3b`, `qwen2.5:7b`) |
| Replies very slow / timeouts | Smaller `OLLAMA_MODEL`, close other apps, raise `LLM_TIMEOUT_SECONDS`; use text input |
| "Whisper model ... not downloaded" | `python scripts\download_models.py`; check `STT_MODEL_DIR` |
| "Piper voice files not found" | Check `PIPER_VOICE_PATH` has both `.onnx` and `.onnx.json` |
| Transcription inaccurate | Try `small.en`; use a closer microphone; reduce background noise |
| Mic button disabled | STT unavailable (see status line) or LLM unavailable; text input still works if the LLM is up |
| 401 errors | Token missing/expired; check `JWT_SECRET` and your auth adapter |
