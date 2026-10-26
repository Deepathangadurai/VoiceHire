import React, { useState } from "react";
import { apiFetch } from "../api";
import { Send, CheckCircle, AlertTriangle, Mail, Zap, Info, Clock, Check } from "lucide-react";

const SEND_FORM_DEFAULTS = {
  to_email: "",
  to_name: "",
  candidate_id: "c1",
  job_role: "Software Engineer",
  assessment_title: "Technical Assessment",
  deadline: "2026-11-15",
  assessment_link: "https://portal.voicehire.ai/assess",
  support_contact: "support@voicehire.ai",
  also_schedule_reminder: true,
};

const FORM_FIELDS = [
  { key: "to_email",         label: "Candidate Email",    placeholder: "alice@example.com",                  required: true  },
  { key: "to_name",          label: "Candidate Name",     placeholder: "Alice Johnson",                      required: true  },
  { key: "candidate_id",     label: "Candidate ID",       placeholder: "c1",                                 required: false },
  { key: "job_role",         label: "Job Role",           placeholder: "Software Engineer",                  required: false },
  { key: "assessment_title", label: "Assessment Title",   placeholder: "Technical Assessment",               required: false },
  { key: "deadline",         label: "Deadline",           placeholder: "2026-11-15",                         required: false },
  { key: "assessment_link",  label: "Assessment Link",    placeholder: "https://portal.voicehire.ai/assess", required: false },
  { key: "support_contact",  label: "Support Contact",    placeholder: "support@voicehire.ai",               required: false },
];

export default function QuickSend({ token }: { token: string }) {
  const [form, setForm]             = useState(SEND_FORM_DEFAULTS);
  const [loading, setLoading]       = useState(false);
  const [result, setResult]         = useState<any>(null);
  const [error, setError]           = useState("");
  const [testEmail, setTestEmail]   = useState("");
  const [testLoading, setTestLoading] = useState(false);
  const [testResult, setTestResult] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  function set(k: string, v: any) {
    setForm(p => ({ ...p, [k]: v }));
  }

  async function sendInvitation() {
    if (!form.to_email || !form.to_name) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await apiFetch("/api/emails/send/assessment-invitation", token, {
        method: "POST",
        body: JSON.stringify(form),
      });
      setResult(data);
    } catch (e: any) {
      setError(e.message || "Failed to dispatch email");
    } finally {
      setLoading(false);
    }
  }

  async function sendTest() {
    if (!testEmail) return;
    setTestLoading(true);
    setTestResult(null);
    try {
      const data = await apiFetch("/api/emails/send-test", token, {
        method: "POST",
        body: JSON.stringify({ to_email: testEmail, to_name: "Test Recruiter" }),
      });
      setTestResult({
        type: "success",
        msg: data.queued ? "Test email queued successfully!" : "Test email sent successfully",
      });
    } catch (e: any) {
      setTestResult({ type: "error", msg: e.message || "Failed to send test email" });
    } finally {
      setTestLoading(false);
    }
  }

  const canSend = !!form.to_email.trim() && !!form.to_name.trim();

  return (
    <div style={{ maxWidth: 860, margin: "0 auto", paddingBottom: 40 }}>
      {/* Main Invitation Card */}
      <div style={{
        background: "#ffffff",
        borderRadius: 14,
        border: "1px solid #e2e8f0",
        boxShadow: "0 1px 3px rgba(15,23,42,0.06), 0 1px 2px rgba(15,23,42,0.03)",
        padding: "24px 28px",
        marginBottom: 20,
      }}>
        {/* Header */}
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          paddingBottom: 18,
          borderBottom: "1px solid #edf2f7",
          marginBottom: 22,
        }}>
          <div style={{
            width: 38,
            height: 38,
            borderRadius: 10,
            background: "#eff6ff",
            border: "1px solid #bfdbfe",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#2563eb",
            flexShrink: 0,
          }}>
            <Send size={18} />
          </div>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: "#0f172a", margin: 0 }}>
              Send Assessment Invitation
            </h2>
            <p style={{ fontSize: 13, color: "#64748b", margin: "2px 0 0" }}>
              Quickly send a personalized assessment link to a candidate.
            </p>
          </div>
        </div>

        {/* 2-Column Form Grid */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "16px 20px",
        }}>
          {FORM_FIELDS.map(({ key, label, placeholder, required }) => (
            <div key={key} style={{ display: "flex", flexDirection: "column" }}>
              <label style={{
                fontSize: 12.5,
                fontWeight: 600,
                color: "#334155",
                marginBottom: 6,
                display: "flex",
                alignItems: "center",
              }}>
                {label}
                {required && (
                  <span style={{ color: "#ef4444", marginLeft: 4, fontWeight: 700 }}>*</span>
                )}
              </label>
              <input
                type="text"
                value={(form as any)[key]}
                onChange={e => set(key, e.target.value)}
                placeholder={placeholder}
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  background: "#ffffff",
                  border: "1px solid #cbd5e1",
                  borderRadius: 8,
                  padding: "9px 12px",
                  fontSize: 13.5,
                  color: "#0f172a",
                  outline: "none",
                  transition: "border-color 0.15s, box-shadow 0.15s",
                }}
                onFocus={e => {
                  e.target.style.borderColor = "#2563eb";
                  e.target.style.boxShadow = "0 0 0 3px rgba(37,99,235,0.12)";
                }}
                onBlur={e => {
                  e.target.style.borderColor = "#cbd5e1";
                  e.target.style.boxShadow = "none";
                }}
              />
            </div>
          ))}
        </div>

        {/* Reminder Checkbox */}
        <div style={{ marginTop: 20 }}>
          <label style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 9,
            padding: "8px 12px",
            background: "#f8fafc",
            borderRadius: 8,
            border: "1px solid #e2e8f0",
            cursor: "pointer",
            userSelect: "none",
          }}>
            <input
              type="checkbox"
              checked={form.also_schedule_reminder}
              onChange={e => set("also_schedule_reminder", e.target.checked)}
              style={{
                width: 16,
                height: 16,
                accentColor: "#2563eb",
                cursor: "pointer",
                margin: 0,
              }}
            />
            <span style={{ fontSize: 13, fontWeight: 500, color: "#334155" }}>
              Also schedule a 48-hour reminder email
            </span>
          </label>
        </div>

        {/* Action Row */}
        <div style={{
          display: "flex",
          gap: 14,
          marginTop: 22,
          alignItems: "center",
          flexWrap: "wrap",
        }}>
          <button
            onClick={sendInvitation}
            disabled={loading || !canSend}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "10px 22px",
              background: canSend ? "#2563eb" : "#94a3b8",
              color: "#ffffff",
              border: "none",
              borderRadius: 8,
              fontSize: 13.5,
              fontWeight: 600,
              cursor: canSend && !loading ? "pointer" : "not-allowed",
              boxShadow: canSend ? "0 2px 6px rgba(37,99,235,0.3)" : "none",
              transition: "all 0.15s ease",
              opacity: loading ? 0.75 : 1,
            }}
          >
            <Mail size={16} />
            {loading ? "Sending Invitation…" : "Send Assessment Invitation"}
          </button>

          {!canSend && (
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              fontSize: 12.5,
              color: "#64748b",
            }}>
              <Info size={14} color="#94a3b8" />
              <span>Fill in required candidate email and name to dispatch</span>
            </div>
          )}
        </div>

        {/* Error Alert */}
        {error && (
          <div style={{
            marginTop: 18,
            padding: "12px 16px",
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: 8,
            color: "#dc2626",
            fontSize: 13,
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}>
            <AlertTriangle size={16} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        {/* Success Alert */}
        {result && (
          <div style={{
            marginTop: 18,
            padding: "14px 16px",
            background: "#f0fdf4",
            border: "1px solid #bbf7d0",
            borderRadius: 8,
            color: "#16a34a",
            fontSize: 13,
            display: "flex",
            alignItems: "flex-start",
            gap: 10,
          }}>
            <CheckCircle size={18} style={{ flexShrink: 0, marginTop: 1 }} />
            <div>
              <strong style={{ fontSize: 13.5 }}>Assessment email queued successfully!</strong>
              <div style={{ marginTop: 6, display: "flex", gap: 10, flexWrap: "wrap", color: "#166534", fontSize: 12 }}>
                <span style={{
                  background: "#dcfce7",
                  border: "1px solid #86efac",
                  padding: "2px 8px",
                  borderRadius: 6,
                  fontFamily: "monospace",
                }}>
                  Job ID: {result.invitation_job_id || "queued"}
                </span>
                {result.reminder_job_id && (
                  <span style={{
                    background: "#dcfce7",
                    border: "1px solid #86efac",
                    padding: "2px 8px",
                    borderRadius: 6,
                    fontFamily: "monospace",
                  }}>
                    Reminder Job: {result.reminder_job_id}
                  </span>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Test Email Card */}
      <div style={{
        background: "#ffffff",
        borderRadius: 14,
        border: "1px solid #e2e8f0",
        boxShadow: "0 1px 3px rgba(15,23,42,0.06), 0 1px 2px rgba(15,23,42,0.03)",
        padding: "22px 28px",
      }}>
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          paddingBottom: 14,
          borderBottom: "1px solid #edf2f7",
          marginBottom: 16,
        }}>
          <div style={{
            width: 36,
            height: 36,
            borderRadius: 9,
            background: "#fef3c7",
            border: "1px solid #fde68a",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#d97706",
            flexShrink: 0,
          }}>
            <Zap size={17} />
          </div>
          <div>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: "#0f172a", margin: 0 }}>
              Send Test Email
            </h3>
            <p style={{ fontSize: 12.5, color: "#64748b", margin: "2px 0 0" }}>
              Verify your SMTP server configuration with an instant delivery test.
            </p>
          </div>
        </div>

        <div style={{ display: "flex", gap: 10, maxWidth: 520 }}>
          <input
            type="email"
            value={testEmail}
            onChange={e => setTestEmail(e.target.value)}
            placeholder="recruiter@example.com"
            style={{
              flex: 1,
              boxSizing: "border-box",
              background: "#ffffff",
              border: "1px solid #cbd5e1",
              borderRadius: 8,
              padding: "9px 12px",
              fontSize: 13.5,
              color: "#0f172a",
              outline: "none",
            }}
            onFocus={e => {
              e.target.style.borderColor = "#2563eb";
              e.target.style.boxShadow = "0 0 0 3px rgba(37,99,235,0.12)";
            }}
            onBlur={e => {
              e.target.style.borderColor = "#cbd5e1";
              e.target.style.boxShadow = "none";
            }}
          />
          <button
            onClick={sendTest}
            disabled={!testEmail.trim() || testLoading}
            style={{
              padding: "9px 18px",
              background: testEmail.trim() ? "#f8fafc" : "#f1f5f9",
              color: testEmail.trim() ? "#0f172a" : "#94a3b8",
              border: "1px solid #cbd5e1",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              cursor: testEmail.trim() && !testLoading ? "pointer" : "not-allowed",
              transition: "all 0.15s ease",
              whiteSpace: "nowrap",
            }}
          >
            {testLoading ? "Sending…" : "Send Test"}
          </button>
        </div>

        {testResult && (
          <div style={{
            marginTop: 14,
            padding: "10px 14px",
            background: testResult.type === "success" ? "#f0fdf4" : "#fef2f2",
            border: `1px solid ${testResult.type === "success" ? "#bbf7d0" : "#fecaca"}`,
            borderRadius: 8,
            color: testResult.type === "success" ? "#16a34a" : "#dc2626",
            fontSize: 13,
            display: "flex",
            alignItems: "center",
            gap: 8,
            maxWidth: 520,
          }}>
            {testResult.type === "success" ? <CheckCircle size={15} /> : <AlertTriangle size={15} />}
            <span>{testResult.msg}</span>
          </div>
        )}
      </div>
    </div>
  );
}
