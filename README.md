# VoiceHire AI – Local-First Recruitment Platform

> **Voice assistant + full email automation. Runs entirely on your machine. No cloud AI. No API keys required.**

## ✅ Test Results

```
37 passed in 1.73s
├── 22 email automation tests (all 14 spec acceptance tests + 8 bonus)
└── 15 voice assistant tests
```

---

## 🚀 Quick Start

### Prerequisites (already satisfied on this machine)
| Tool | Version | Status |
|---|---|---|
| Python | 3.10+ | ✅ 3.10.1 |
| Node.js | 18+ | ✅ 26.4.0 |
| Ollama | any | ✅ 0.40.11 |
| `llama3.2:3b` model | — | ✅ downloaded |

### Step 1 – Copy environment config
```powershell
copy .env.example .env
```
Then set `JWT_SECRET` to a random string. Everything else works out of the box.

### Step 2 – Install dependencies (one-time)

**Backend:**
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements-voice.txt
.\.venv\Scripts\pip install uvicorn sqlalchemy alembic aiosmtplib jinja2 openpyxl apscheduler aiofiles
```

**Frontend:**
```powershell
cd frontend
npm install
npm approve-scripts esbuild
```

### Step 3 – Download AI models (one-time, ~150 MB)
```powershell
cd backend
.\.venv\Scripts\python.exe scripts\download_models.py
```

---

## ▶️ Running the Project

### Backend (Terminal 1)
```powershell
cd d:\voicehire-voice-local\backend
.\.venv\Scripts\python.exe run_server.py
```
→ **http://localhost:8000**  
→ Swagger UI: **http://localhost:8000/docs**

### Frontend (Terminal 2)
```powershell
cd d:\voicehire-voice-local\frontend
npm run dev
```
→ **http://localhost:3000**

> Both must be running at the same time. Open **http://localhost:3000** in your browser.

---

## 🏗 Architecture

```
Browser (localhost:3000 Vite)
  ↓ Vite proxy /api → localhost:8000
FastAPI backend (run_server.py)
  ├── /api/voice/*     Voice assistant (Ollama LLM + Whisper STT + Piper TTS)
  └── /api/emails/*    Email automation (SMTP / demo mode + APScheduler)
        ├── SQLite DB   voicehire.db  (swap DATABASE_URL for PostgreSQL)
        └── Scheduler   every 60s process due jobs, every 120s retry failed
```

---

## 📧 Email Automation System

### How it works
- **Demo mode** (default, `EMAIL_DEMO_MODE=true`): all emails are **simulated** and stored in the DB clearly marked. Nothing is sent to any real SMTP server.
- **Live mode** (`EMAIL_DEMO_MODE=false`): requires valid `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`.

### Email workflows implemented
| Event | Template | Trigger |
|---|---|---|
| Assessment invitation | `assessment_invitation` | Recruiter sends via API or UI |
| 48h reminder | `assessment_reminder` | Auto-scheduled 48h after invitation |
| Submission confirmation | `submission_confirmation` | After repo URL saved successfully |
| Interview invitation | `interview_invitation` | After interview scheduled |
| Interview reschedule | `interview_reschedule` | After reschedule saved |
| Decision notification | `decision_notification` | After recruiter approval (disabled by default) |
| Review ready (recruiter) | `review_ready` | When candidate submits |

### Key guarantees
- ✅ **No duplicate emails** — idempotency keys prevent double-sends
- ✅ **Reminder cancellation** — `POST /api/emails/cancel-reminder` stops a pending 48h reminder when assignment is completed/cancelled
- ✅ **SMTP credentials never logged** — passwords never appear in logs, API responses, or frontend code
- ✅ **HTML injection prevented** — Jinja2 autoescape on all template variables
- ✅ **Persistent scheduler** — APScheduler with DB-backed jobs; jobs survive server restart
- ✅ **Exponential backoff** — retries: 60s, 120s, 240s, 480s, 960s (bounded)
- ✅ **Bulk send confirmation** — `confirmed: true` required; preview endpoint shows recipient count first

### Configure Gmail SMTP (live mode)
1. Enable 2FA on your Google account
2. Create an App Password: Google Account → Security → App Passwords
3. Set in `.env`:
```
EMAIL_DEMO_MODE=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=you@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx   # App Password, NOT your login password
SMTP_SENDER_EMAIL=you@gmail.com
SMTP_SENDER_NAME=VoiceHire AI
```
> Gmail free limit: ~500 emails/day. Google Workspace: ~2000/day. Provider-specific limits apply.

---

## 🎙 Voice Assistant

Runs entirely locally. No internet required after model download.

- **LLM**: Ollama `llama3.2:3b` (tool-calling capable)
- **STT**: faster-whisper `base.en` (speech → text)
- **TTS**: Piper `en_US-lessac-medium` (text → speech, GPL-3.0)

Check status: `GET /api/voice/health` (requires Bearer token)

---

## 🧪 Running Tests

```powershell
cd d:\voicehire-voice-local\backend
.\.venv\Scripts\pytest.exe tests -v
```

| Suite | Tests | Coverage |
|---|---|---|
| `test_email_automation.py` | 22 | All 14 spec acceptance tests + import, escaping, suppression, validation |
| `test_voice_pipeline.py` | 7 | Agent turns, confirmations, audio checks, remote Ollama rejection |
| `test_voice_tools.py` | 8 | RBAC, identity injection, dry-run, confirmation lifecycle |

---

## 🌐 Key URLs

| URL | Description |
|---|---|
| http://localhost:3000 | Frontend app (login → recruiter/candidate) |
| http://localhost:8000 | Backend root |
| http://localhost:8000/docs | Swagger UI (interactive API) |
| http://localhost:8000/token?role=recruiter | Get test JWT token |
| http://localhost:8000/api/emails/jobs | Email job queue (JSON) |
| http://localhost:8000/api/emails/jobs/stats | Email stats by status |
| http://localhost:8000/api/voice/health | Voice service health |

---

## 📁 Project Structure

```
voicehire-voice-local/
├── .env.example              # All config variables documented
├── backend/
│   ├── run_server.py         # ← START HERE (FastAPI + scheduler + seeding)
│   ├── app/
│   │   ├── database.py       # SQLAlchemy setup (SQLite/PostgreSQL)
│   │   ├── email/
│   │   │   ├── models.py     # EmailTemplate, EmailJob, EmailLog, AutomationRule
│   │   │   ├── config.py     # SMTP config (no credentials in logs/frontend)
│   │   │   ├── service.py    # SMTP send / demo simulate
│   │   │   ├── queue.py      # APScheduler, idempotency, retry, workflow helpers
│   │   │   ├── templates.py  # Default HTML+text templates + seeder
│   │   │   ├── importer.py   # CSV/Excel import + email validation
│   │   │   └── router.py     # /api/emails/* FastAPI routes
│   │   └── voice/            # Voice assistant (unchanged)
│   ├── tests/
│   │   ├── test_email_automation.py   # 22 acceptance tests
│   │   ├── test_voice_pipeline.py
│   │   └── test_voice_tools.py
│   └── requirements-voice.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # Main app + sidebar navigation
│   │   ├── AuthContext.tsx   # JWT token storage
│   │   ├── api.ts            # Fetch helper
│   │   ├── email/
│   │   │   ├── EmailCenter.tsx   # Full email dashboard UI
│   │   │   └── QuickSend.tsx     # Assessment invitation form
│   │   └── voice/
│   │       └── VoicePanel.tsx    # Voice assistant UI
│   └── package.json
└── docs/
    ├── SETUP_WINDOWS.md
    ├── ARCHITECTURE.md
    ├── API_DOCUMENTATION.md
    └── TESTING.md
```

---

## ⚠️ Important Notes

- **Email delivery ≠ inbox delivery**: SMTP `accepted` status means the mail server accepted the message for delivery. Actual inbox delivery depends on the recipient's mail server, spam filters, and provider policies. No open/click tracking is implemented.
- **Demo mode is the safe default**: `EMAIL_DEMO_MODE=true` in `.env`. Switch to `false` only with valid SMTP credentials.
- **Decision emails require approval**: The `decision_notification` automation rule is `enabled=false` by default. Enable it via `PATCH /api/emails/automation-rules/{id}` after recruiter review.
- **Piper TTS is GPL-3.0**: Check licensing obligations before distributing.
- **JWT_SECRET**: Change `dev-secret-change-in-production` in `.env` before any real deployment.
