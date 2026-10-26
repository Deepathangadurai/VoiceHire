# Demo script (about 5 minutes)

Before: Ollama running, models downloaded, seeded data loaded, panel status lines all "ready". Optionally set `VOICE_DRY_RUN=true` for a rehearsal (actions are confirmed but not executed, and the assistant says so).

**Recruiter**
1. Point out "Local AI · on this machine" and the three status lines.
2. Click the mic: "How many candidates have registered?" -> transcript, tool line, spoken answer. Cross-check with the dashboard.
3. Type: "Who is overdue?" (text fallback).
4. "Assign the Python assessment to eligible candidates." -> confirmation card; say "yes". Show the audit log row and the dashboard change.
5. Interrupt the assistant mid-reply by clicking the mic.

**Candidate**
1. Log in as a candidate: "What is my submission deadline?" then "When is my interview?"
2. Ask "What is the status of Priya's application?" (another candidate) -> refused/unavailable.
3. Ask "Will I get the job?" -> no promise; only released decisions are explained.

**Failure handling**
Stop Ollama -> clear error, no invented answer. Start it again and retry.

Tell the audience: replies take a few seconds on local hardware; a small model can misunderstand, which is why actions need confirmation and tool data is shown.
