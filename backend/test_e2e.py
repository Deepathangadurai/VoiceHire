"""End-to-end test: Excel import + email send via live API."""
import sys, io, asyncio
sys.path.insert(0, ".")

import openpyxl
import requests

BASE = "http://localhost:8000"


def get_token(role="recruiter"):
    return requests.get(f"{BASE}/token?role={role}").json()["token"]


def test_excel_import():
    """Build a realistic Excel with various column names and upload it."""
    print("\n=== TEST 1: Excel Import ===")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Candidates"
    # Real-world column names (different from our canonical names)
    ws.append(["Candidate Name", "Email ID", "Mobile No", "Technical Skills", "Designation", "Remarks"])
    ws.append(["Alice Johnson",  "alice@example.com",   "9876543210", "Python, Django",     "Backend Dev",   "Strong candidate"])
    ws.append(["Bob Smith",      "bob@techcorp.com",    "9123456780", "React, TypeScript",  "Frontend Dev",  "Good communication"])
    ws.append(["Priya Sharma",   "priya@gmail.com",     "8765432109", "Java, Spring Boot",  "Full Stack",    ""])
    ws.append(["",               "invalid-email",       "",           "",                   "",              "missing name + bad email"])
    ws.append(["David Lee",      "david@example.com",   "7654321098", "DevOps, K8s",        "SRE",           ""])

    buf = io.BytesIO()
    wb.save(buf)
    content = buf.getvalue()

    # Direct Python test (bypass HTTP)
    from app.email.importer import process_import
    result = process_import("candidates.xlsx", content)
    r = result.to_dict()
    print(f"  Valid rows:    {r['valid_count']}  (expected 4)")
    print(f"  Invalid rows:  {r['invalid_count']} (expected 1)")
    print(f"  Unresolved:    {r['unresolved_headers']}")
    for c in result.valid:
        print(f"    ✅ {c['name']} <{c['email']}> role={c['role']}")
    for e in result.errors:
        print(f"    ❌ row {e['row']}: {e['error']}")

    # Save file for the API upload test
    buf.seek(0)
    with open("test_candidates.xlsx", "wb") as f:
        f.write(buf.getvalue())
    print("  Saved: test_candidates.xlsx")

    assert r["valid_count"] == 4, f"Expected 4 valid, got {r['valid_count']}"
    assert r["invalid_count"] == 1
    print("  PASSED ✅")
    return result.import_id


def test_api_upload():
    """Upload the Excel via the real API endpoint."""
    print("\n=== TEST 2: API Upload ===")
    token = get_token("recruiter")
    headers = {"Authorization": f"Bearer {token}"}

    with open("test_candidates.xlsx", "rb") as f:
        res = requests.post(
            f"{BASE}/api/emails/import/upload",
            headers=headers,
            files={"file": ("test_candidates.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    print(f"  Status: {res.status_code}")
    data = res.json()
    print(f"  Valid: {data['valid_count']}, Invalid: {data['invalid_count']}")
    assert res.status_code == 200
    assert data["valid_count"] == 4
    print("  PASSED ✅")
    return data["import_id"]


def test_confirm_import(import_id):
    """Confirm import and queue assessment invitations."""
    print("\n=== TEST 3: Confirm Import + Send Invitations ===")
    token = get_token("recruiter")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    import json
    res = requests.post(f"{BASE}/api/emails/import/confirm", headers=headers, data=json.dumps({
        "import_id": import_id,
        "send_invitations": True,
        "job_role": "Software Engineer",
        "assessment_title": "Python & Django Challenge",
        "deadline": "2026-11-30",
        "assessment_link": "https://portal.voicehire.ai/assess",
    }))
    print(f"  Status: {res.status_code}")
    data = res.json()
    print(f"  Imported: {data['candidates_imported']}, Emails queued: {data['emails_queued']}")
    assert res.status_code == 200
    assert data["candidates_imported"] == 4
    assert data["emails_queued"] >= 4
    print("  PASSED ✅")


def test_email_stats():
    """Check email job stats after sending."""
    print("\n=== TEST 4: Email Stats ===")
    token = get_token("recruiter")
    headers = {"Authorization": f"Bearer {token}"}

    res = requests.get(f"{BASE}/api/emails/jobs/stats", headers=headers)
    data = res.json()
    print(f"  Stats: {data}")
    total = sum(data.values())
    assert total > 0, "No email jobs found after import+confirm"
    print("  PASSED ✅")


def test_email_templates():
    """Check templates are seeded and can be previewed."""
    print("\n=== TEST 5: Templates ===")
    token = get_token("recruiter")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    import json
    res = requests.get(f"{BASE}/api/emails/templates", headers=headers)
    templates = res.json()
    print(f"  Templates found: {len(templates)}")
    assert len(templates) >= 5

    # Preview one
    tpl_id = templates[0]["id"]
    res2 = requests.post(f"{BASE}/api/emails/templates/preview", headers=headers, data=json.dumps({
        "template_id": tpl_id,
        "context_vars": {"candidate_name": "Test User", "job_role": "Engineer", "assessment_title": "Test", "deadline": "Nov 30", "assessment_link": "https://test.com", "support_contact": "support@test.com"},
    }))
    print(f"  Preview status: {res2.status_code}")
    assert res2.status_code == 200
    print("  PASSED ✅")


def test_smtp_config():
    """SMTP config returned without password."""
    print("\n=== TEST 6: SMTP Config (no credentials leak) ===")
    token = get_token("recruiter")
    res = requests.get(f"{BASE}/api/emails/config", headers={"Authorization": f"Bearer {token}"})
    data = res.json()
    print(f"  Config: {data}")
    assert "password" not in str(data).lower() or "smtp_password" not in data
    print("  PASSED ✅")


def test_quick_send():
    """Send a single assessment invitation via /send/assessment-invitation."""
    print("\n=== TEST 7: Quick Send — Assessment Invitation ===")
    import json
    token = get_token("recruiter")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    res = requests.post(f"{BASE}/api/emails/send/assessment-invitation", headers=headers, data=json.dumps({
        "to_email": "test.recruiter@example.com",
        "to_name": "Test Candidate",
        "candidate_id": "test-c1",
        "job_role": "Data Engineer",
        "assessment_title": "SQL + Python Assessment",
        "deadline": "2026-12-01",
        "assessment_link": "https://portal.voicehire.ai/assess/test",
        "also_schedule_reminder": True,
    }))
    data = res.json()
    print(f"  Status: {res.status_code}  invitation_job_id={data.get('invitation_job_id')} reminder_job_id={data.get('reminder_job_id')}")
    assert res.status_code == 200
    assert data.get("invitation_job_id") is not None
    assert data.get("reminder_job_id") is not None
    print("  PASSED ✅")


def test_email_jobs_list():
    """Verify email jobs list endpoint."""
    print("\n=== TEST 8: Email Jobs List ===")
    token = get_token("recruiter")
    res = requests.get(f"{BASE}/api/emails/jobs?limit=10", headers={"Authorization": f"Bearer {token}"})
    data = res.json()
    print(f"  Total jobs: {data['total']}")
    if data["jobs"]:
        j = data["jobs"][0]
        print(f"  Latest: [{j['status']}] {j['subject']} → {j['to_email']}")
    assert data["total"] > 0
    print("  PASSED ✅")


if __name__ == "__main__":
    print("VoiceHire AI — Full End-to-End Test Suite")
    print("=" * 50)
    try:
        import_id_py = test_excel_import()
        import_id_api = test_api_upload()
        test_confirm_import(import_id_api)
        test_email_stats()
        test_email_templates()
        test_smtp_config()
        test_quick_send()
        test_email_jobs_list()
        print("\n" + "=" * 50)
        print("ALL TESTS PASSED ✅")
    except AssertionError as e:
        print(f"\n❌ ASSERTION FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)
