"""Candidate import from CSV/Excel — robust header detection & fallback column logic."""
from __future__ import annotations
import csv
import io
import re
import uuid
from difflib import get_close_matches
from typing import Any

import openpyxl

from app.email.service import validate_email

REQUIRED_FIELDS = ["name", "email"]
OPTIONAL_FIELDS = ["phone", "skills", "role", "notes"]

# ── Comprehensive column-header → canonical-field mapping ─────────────────────
# All entries are lowercase; strip + lower is applied before lookup.
COLUMN_MAP: dict[str, str] = {
    # name
    "name": "name", "full name": "name", "fullname": "name",
    "candidate name": "name", "candidatename": "name",
    "applicant name": "name", "applicantname": "name",
    "first name": "name", "firstname": "name",
    "last name": "name", "lastname": "name",
    "candidate": "name", "person": "name", "contact name": "name",
    "employee name": "name", "student name": "name",
    # email
    "email": "email", "email address": "email", "emailaddress": "email",
    "e-mail": "email", "e mail": "email", "mail": "email",
    "email id": "email", "emailid": "email",
    "contact email": "email", "work email": "email",
    "personal email": "email", "candidate email": "email",
    # phone
    "phone": "phone", "phone number": "phone", "phonenumber": "phone",
    "mobile": "phone", "mobile number": "phone", "mobilenumber": "phone",
    "contact number": "phone", "cell": "phone", "cell number": "phone",
    "telephone": "phone", "tel": "phone", "contact": "phone",
    "whatsapp": "phone", "mob": "phone", "ph": "phone",
    # skills
    "skills": "skills", "skill set": "skills", "skillset": "skills",
    "skill": "skills", "technical skills": "skills",
    "expertise": "skills", "technologies": "skills",
    "tech stack": "skills", "competencies": "skills",
    # role
    "role": "role", "job role": "role", "jobrole": "role",
    "position": "role", "designation": "role", "job title": "role",
    "jobtitle": "role", "title": "role", "applied role": "role",
    "applied for": "role", "job": "role", "department": "role",
    "profile": "role", "function": "role",
    # notes
    "notes": "notes", "note": "notes", "comments": "notes",
    "comment": "notes", "remarks": "notes", "remark": "notes",
    "additional info": "notes", "additionalinfo": "notes",
    "description": "notes", "details": "notes", "info": "notes",
}

# ── Positional fallback: if headers can't be resolved, try column-index guess ─
# Maps 0-based column index → canonical field (for common ordering: name, email, phone…)
POSITIONAL_FALLBACK = {0: "name", 1: "email", 2: "phone", 3: "skills", 4: "role", 5: "notes"}


def _clean_header(raw: Any) -> str:
    """Normalise a cell value for header matching."""
    if raw is None:
        return ""
    return re.sub(r"\s+", " ", str(raw)).strip().lower()


def _fuzzy_lookup(key: str) -> str | None:
    """Exact then fuzzy match against COLUMN_MAP keys."""
    k = key.strip().lower()
    if k in COLUMN_MAP:
        return COLUMN_MAP[k]
    # Remove common suffixes/prefixes and retry
    cleaned = re.sub(r"[^a-z\s]", "", k).strip()
    if cleaned in COLUMN_MAP:
        return COLUMN_MAP[cleaned]
    # Fuzzy match (cutoff=0.75)
    matches = get_close_matches(k, COLUMN_MAP.keys(), n=1, cutoff=0.75)
    if matches:
        return COLUMN_MAP[matches[0]]
    return None


def _resolve_headers(raw_headers: list[Any]) -> tuple[dict[int, str], list[str]]:
    """
    Map column indices to canonical field names.
    Returns (index→field, list of unresolved header strings).
    """
    resolved: dict[int, str] = {}
    unresolved: list[str] = []

    for i, raw in enumerate(raw_headers):
        h = _clean_header(raw)
        if not h:
            # Empty header — use positional fallback
            if i in POSITIONAL_FALLBACK and POSITIONAL_FALLBACK[i] not in resolved.values():
                resolved[i] = POSITIONAL_FALLBACK[i]
            continue
        canon = _fuzzy_lookup(h)
        if canon:
            if canon not in resolved.values():  # first occurrence wins
                resolved[i] = canon
        else:
            unresolved.append(h)

    return resolved, unresolved


def _parse_csv(content: bytes) -> tuple[list[dict], list[str]]:
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    all_rows = list(reader)
    if not all_rows:
        return [], []

    header_row = all_rows[0]
    idx_map, unresolved = _resolve_headers(header_row)

    result = []
    for row in all_rows[1:]:
        record: dict[str, str] = {}
        for i, cell in enumerate(row):
            if i in idx_map:
                record[idx_map[i]] = str(cell).strip() if cell else ""
        result.append(record)
    return result, unresolved


def _parse_excel(content: bytes) -> tuple[list[dict], list[str]]:
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    all_rows = list(ws.iter_rows(values_only=True))
    if not all_rows:
        return [], []

    # Skip completely empty rows at the top (some Excel templates have blank rows)
    start = 0
    for idx, row in enumerate(all_rows):
        if any(c is not None and str(c).strip() for c in row):
            start = idx
            break

    data_rows = all_rows[start:]
    if not data_rows:
        return [], []

    header_row = data_rows[0]
    idx_map, unresolved = _resolve_headers(list(header_row))

    result = []
    for row in data_rows[1:]:
        # Skip fully-empty rows
        if not any(c is not None and str(c).strip() for c in row):
            continue
        record: dict[str, str] = {}
        for i, cell in enumerate(row):
            if i in idx_map:
                record[idx_map[i]] = str(cell).strip() if cell is not None else ""
        result.append(record)

    return result, unresolved


# ── Result container ──────────────────────────────────────────────────────────

class ImportResult:
    def __init__(self):
        self.import_id = str(uuid.uuid4())
        self.valid: list[dict] = []
        self.errors: list[dict] = []
        self.duplicate_emails: list[str] = []
        self.seen_emails: set[str] = set()
        self.unresolved_headers: list[str] = []
        self.detected_headers: dict[str, str] = {}  # column_name → canonical

    @property
    def total(self):
        return len(self.valid) + len(self.errors)

    def to_dict(self) -> dict:
        return {
            "import_id": self.import_id,
            "total_rows": self.total,
            "valid_count": len(self.valid),
            "invalid_count": len(self.errors),
            "duplicate_count": len(self.duplicate_emails),
            "unresolved_headers": self.unresolved_headers,
            "candidates": self.valid,
            "errors": self.errors,
        }


def process_import(filename: str, content: bytes) -> ImportResult:
    result = ImportResult()

    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext in ("xlsx", "xls"):
        raw_rows, unresolved = _parse_excel(content)
    elif ext == "csv":
        raw_rows, unresolved = _parse_csv(content)
    else:
        raise ValueError(f"Unsupported file type '.{ext}'. Please upload a .csv or .xlsx file.")

    result.unresolved_headers = unresolved

    if not raw_rows:
        raise ValueError("The file appears to be empty or has no data rows after the header.")

    for i, row in enumerate(raw_rows, start=2):  # row 1 = header
        # Required field checks
        missing = [f for f in REQUIRED_FIELDS if not row.get(f)]
        if missing:
            result.errors.append({
                "row": i, "data": row,
                "error": f"Missing required fields: {', '.join(missing)}"
                + (f". Unrecognised headers: {unresolved}" if unresolved and i == 2 else ""),
            })
            continue

        # Email validation
        email = row["email"].lower().strip()
        if not validate_email(email):
            result.errors.append({"row": i, "data": row, "error": f"Invalid email: '{email}'"})
            continue

        # Duplicate detection
        if email in result.seen_emails:
            result.duplicate_emails.append(email)
            result.errors.append({"row": i, "data": row, "error": f"Duplicate email: {email}"})
            continue

        result.seen_emails.add(email)
        result.valid.append({
            "id": str(uuid.uuid4()),
            "name": row.get("name", "").strip(),
            "email": email,
            "phone": row.get("phone", ""),
            "skills": row.get("skills", ""),
            "role": row.get("role", ""),
            "notes": row.get("notes", ""),
        })

    return result
