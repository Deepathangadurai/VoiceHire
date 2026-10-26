# Testing

## Automated (backend/tests). Written, NOT yet run by the author
`cd backend; $env:PYTHONPATH="."; pytest tests` (needs `pip install -r requirements-voice.txt`).
Covers: candidate cannot call recruiter tools; identity arguments rejected; confirmation required and single-use; other users cannot confirm; dry-run does not execute; argument validation; model cannot claim a pending action is done (scripted fake LLM); yes/no handling; audio type/magic/size checks and temp-file cleanup; remote Ollama URL rejected.

## Manual checklist (record result and date; none have been run yet)
| # | Check | How | Result |
|---|---|---|---|
| 1 | Recruiter queries use real records | Ask "How many candidates have registered?"; compare with DB | |
| 2 | Candidate sees only own data | Ask deadline/status; ask about another candidate by name | |
| 3 | Local STT transcribes | Record a sentence; transcript appears; no network calls to external hosts (browser Network tab, backend logs) | |
| 4 | Reply from local model | Stop Ollama mid-test: error appears, no invented answer; restart: works | |
| 5 | Local TTS plays | Reply is audible; "Stop speaking" interrupts | |
| 6 | Confirmation required | "Assign the Python assessment to eligible candidates" -> card; nothing changes until Confirm | |
| 7 | Unauthorized tool rejected | Candidate token to a recruiter flow; automated tests also cover | |
| 8 | Text fallback | Block mic permission, type request | |
| 9 | Missing models / stopped services | Rename Whisper dir, Piper voice, stop Ollama: each shows the documented message | |
| 10 | No OpenAI key | Clean `.env` without any key; everything works | |
| 11 | No Docker | App and services start without Docker | |
| 12 | Honest outcomes | Force a repo failure and `VOICE_DRY_RUN=true`: assistant reports failure / "not executed" | |
| 13 | Short and long questions | 3-second and 30-second recordings | |
| 14 | Upload limits | Upload >5 MB and a renamed .exe via curl to `/stt`: rejected, no temp file left in `%TEMP%\vh_*` | |

## Latency
Measure on the target PC (browser Network tab timings for `/stt`, `/chat`, `/tts`) for short and long inputs and record them here. Do not describe the assistant as real-time unless the numbers support it.
