# Voice API (`/api/voice`, all require `Authorization: Bearer <token>`)

Errors: `{"detail": {"code": "...", "message": "..."}}` with the HTTP status below.

| Endpoint | Request | Success response |
|---|---|---|
| `GET /health` | none | `{local_ai, cloud_services:false, dry_run, llm:{ok,detail,model}, stt:{...}, tts:{...}, limits:{audio_max_seconds, audio_max_bytes}}` |
| `POST /stt` | multipart field `audio` (webm/ogg/wav/mp4/mp3) | `{text, empty}` |
| `POST /chat` | `{text}` (1-1000 chars) | `{reply, source: "ollama"\|"system"\|"demo", pending:{id,summary}\|null, tool_events:[{tool,status,message}]}` |
| `POST /confirm` | `{approve: bool}` (confirms the caller's own pending action) | `{reply, source:"system", result:{status,...}}` |
| `POST /tts` | `{text}` | `audio/wav` body |
| `POST /reset` | none | `{ok:true}` clears history and pending action |

## Error codes
`llm_unavailable` 503, `llm_model_missing` 503, `llm_no_tools` 503, `llm_timeout` 504, `llm_error` 502,
`stt_unavailable`/`stt_model_missing` 503, `stt_timeout` 504, `stt_failed` 422, `audio_too_long`/`audio_too_large` 413,
`bad_audio_type`/`bad_audio_content` 415, `empty_audio` 400, `tts_unavailable`/`tts_voice_missing` 503, `tts_timeout` 504, `tts_failed` 500, `bad_config` 500. 401/403 for auth.

## Tool results (internal, shown as `tool_events`)
`ok` | `confirmation_required` | `cancelled` | `simulated` (dry run) | `error` (`forbidden`, `invalid_arguments`, `tool_failed`).

## Tools
Recruiter: `get_dashboard_metrics`, `search_candidates`, `get_review_queue`, `get_submission_status`, `get_evaluation_report`, and (confirmation required) `assign_assessment`, `schedule_interview`, `send_invitation`, `send_submission_reminder`, `advance_candidate_stage`, `approve_candidate_feedback`.
Candidate: `get_my_assignment`, `get_my_deadline`, `get_my_interview`, `get_my_submission_status`, `get_my_application_status`, `get_my_released_feedback`, and (confirmation required) `submit_github_repository`.
Not implemented yet: `create_assessment`, `save_interviewer_review`, changing deadlines (add as `Tool(...)` entries plus `RecruitmentRepo` methods; mark consequential ones).
