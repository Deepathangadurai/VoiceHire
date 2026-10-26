import React, { useState } from "react";

interface LoginProps {
  onLogin: (token: string, role: string) => void;
}

export default function Login({ onLogin }: LoginProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loginAs(role: string) {
    setLoading(true); setError("");
    try {
      const res = await fetch(`http://localhost:8000/token?role=${role}`);
      const data = await res.json();
      onLogin(data.token, role);
    } catch (e: any) {
      setError("Cannot reach server. Is the backend running on port 8000?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
      background: "linear-gradient(135deg, #0a1628 0%, #0f2447 50%, #0a1628 100%)",
    }}>
      <div style={{
        background: "rgba(255,255,255,0.05)", backdropFilter: "blur(20px)",
        border: "1px solid rgba(255,255,255,0.1)", borderRadius: 20, padding: "48px 40px",
        maxWidth: 420, width: "100%", textAlign: "center",
      }}>
        <div style={{ fontSize: 48, marginBottom: 12 }}>🎙</div>
        <h1 style={{ color: "#fff", fontSize: 28, fontWeight: 700, margin: "0 0 8px" }}>VoiceHire AI</h1>
        <p style={{ color: "rgba(255,255,255,0.6)", margin: "0 0 36px", fontSize: 15 }}>
          Local-first recruitment platform · No cloud AI required
        </p>
        {error && (
          <p style={{ background: "rgba(239,68,68,0.15)", color: "#ff8a80", border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: 8, padding: "10px 16px", marginBottom: 20, fontSize: 13 }}>{error}</p>
        )}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <button onClick={() => loginAs("recruiter")} disabled={loading} style={btnStyle("#0f6b5c", "#fff")}>
            {loading ? "Loading…" : "🏢 Login as Recruiter"}
          </button>
          <button onClick={() => loginAs("candidate")} disabled={loading} style={btnStyle("#1e40af", "#fff")}>
            {loading ? "Loading…" : "👤 Login as Candidate"}
          </button>
        </div>
        <p style={{ color: "rgba(255,255,255,0.35)", fontSize: 12, marginTop: 24 }}>
          Development mode · Uses local JWT token from /token endpoint
        </p>
      </div>
    </div>
  );
}

function btnStyle(bg: string, color: string): React.CSSProperties {
  return {
    background: bg, color, border: "none", borderRadius: 10, padding: "14px 24px",
    fontSize: 15, fontWeight: 600, cursor: "pointer", fontFamily: "inherit",
    transition: "opacity 0.2s", width: "100%",
  };
}
