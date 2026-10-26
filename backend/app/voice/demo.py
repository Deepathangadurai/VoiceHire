"""Opt-in (VOICE_DEMO_FALLBACK=true) keyword router used only when Ollama is down. Output is labelled; it is NOT an AI answer."""
import re

RULES = {
    "recruiter": [(r"how many|registered|metrics|dashboard", "get_dashboard_metrics", {}),
                  (r"overdue", "get_submission_status", {"filter": "overdue"}),
                  (r"not submitted|haven.?t submitted", "get_submission_status", {"filter": "not_submitted"}),
                  (r"review", "get_review_queue", {}),
                  (r"passed|technical", "search_candidates", {"status": "passed_technical"}),
                  (r"waiting|pending", "search_candidates", {"status": "pending_review"})],
    "candidate": [(r"deadline|due", "get_my_deadline", {}), (r"interview|meet", "get_my_interview", {}),
                  (r"recorded|submitted|submission", "get_my_submission_status", {}), (r"feedback", "get_my_released_feedback", {}),
                  (r"status", "get_my_application_status", {}), (r"task|assign|requirement|assessment", "get_my_assignment", {})],
}


def route(role: str, text: str):
    for pat, tool, args in RULES[role]:
        if re.search(pat, text.lower()):
            return tool, args
    return None
