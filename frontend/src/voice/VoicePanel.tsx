import { FormEvent, useEffect, useRef } from "react";
import { useState } from "react";
import { useVoiceAssistant } from "./useVoiceAssistant";
import type { Role, ServiceHealth } from "./types";
import "./voice.css";
import {
  Mic, MicOff, Volume2, VolumeX, RotateCcw, Send, Plus,
  Activity, Server, Cpu, Headphones, CheckCircle, AlertTriangle,
  Circle, Loader2
} from "lucide-react";

const STATUS_LABELS = {
  idle:          "Ready",
  recording:     "Listening…",
  transcribing:  "Transcribing…",
  thinking:      "Processing…",
  speaking:      "Speaking",
} as const;

const STATUS_DESCRIPTIONS = {
  idle:          "Click the microphone or type to start",
  recording:     "Recording your voice — click again to send",
  transcribing:  "Converting speech to text…",
  thinking:      "Local model is generating a response…",
  speaking:      "Playing audio response",
} as const;

interface HealthDotProps { name: string; h?: ServiceHealth; Icon: React.ElementType; }

function HealthDot({ name, h, Icon }: HealthDotProps) {
  const cls = h ? (h.ok ? "ok" : "bad") : "unk";
  return (
    <li className={`vp-health-item ${cls}`} title={h?.detail}>
      <div className="vp-health-dot" />
      <Icon size={11} />
      {name}{h && !h.ok ? `: ${h.detail}` : ""}
    </li>
  );
}

export default function VoicePanel({
  role, getToken, apiBase,
}: {
  role: Role;
  getToken: () => string | Promise<string>;
  apiBase?: string;
}) {
  const v    = useVoiceAssistant({ role, getToken, apiBase });
  const [text, setText] = useState("");
  const end  = useRef<HTMLDivElement>(null);

  useEffect(() => { end.current?.scrollIntoView({ block: "end", behavior: "smooth" }); }, [v.lines]);

  const busy    = v.status === "transcribing" || v.status === "thinking";
  const submit  = (e: FormEvent) => {
    e.preventDefault();
    if (text.trim() && !busy) { void v.sendText(text.trim()); setText(""); }
  };
  const example = role === "recruiter"
    ? "\"How many candidates have registered?\""
    : "\"What is my submission deadline?\"";

  return (
    <section className="vp" aria-label={`${role} voice assistant`}>

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="card">
        <div className="vp-header">
          <h2 className="vp-title">
            <Mic size={18} />
            Voice Assistant
          </h2>
          <span className="vp-badge">
            <CheckCircle size={11} />
            Local AI · On-device
          </span>
        </div>

        {/* Service health */}
        <div className="vp-health-card">
          <div className="vp-health-title">
            <Activity size={11} />
            Service Status
          </div>
          <ul className="vp-health-list" aria-label="Local service status">
            <HealthDot name="Language Model" h={v.health?.llm} Icon={Cpu}         />
            <HealthDot name="Speech-to-Text" h={v.health?.stt} Icon={Mic}         />
            <HealthDot name="Text-to-Speech" h={v.health?.tts} Icon={Headphones}  />
            <li>
              <button className="vp-recheck-btn" onClick={v.refreshHealth}>
                <RotateCcw size={11} style={{ display: "inline", marginRight: 3 }} />
                Recheck
              </button>
            </li>
          </ul>
        </div>

        {v.healthError && (
          <div className="vp-error" role="alert">
            <AlertTriangle size={14} /> {v.healthError}
          </div>
        )}
        {v.health?.dry_run && (
          <div className="vp-note">Dry-run mode is on: confirmed actions are not executed.</div>
        )}
        {v.health && !v.canChat && (
          <div className="vp-error" role="alert">
            <AlertTriangle size={14} />
            <div>The local language model is unavailable. {v.health.llm.detail}</div>
          </div>
        )}
        {v.health && v.canChat && !v.canRecord && (
          <div className="vp-note">Voice input is unavailable ({v.health.stt.detail}). You can still type.</div>
        )}
      </div>

      {/* ── Controls ────────────────────────────────────────────────────────── */}
      <div className="vp-controls" style={{ marginTop: 16 }}>
        {/* Mic button */}
        <button
          className={`vp-mic ${v.status === "recording" ? "on" : ""}`}
          onClick={v.toggleRecording}
          aria-pressed={v.status === "recording"}
          disabled={!v.canRecord || busy || !v.canChat}
          aria-label={v.status === "recording" ? "Stop recording and send" : "Start recording"}
        >
          {v.status === "recording" ? <MicOff size={26} /> : <Mic size={26} />}
        </button>

        {/* Status */}
        <div className="vp-status-block">
          <p className="vp-status" aria-live="polite">
            {STATUS_LABELS[v.status]}
            {busy && (
              <Loader2 size={14} style={{ display: "inline", marginLeft: 8, animation: "spin 1s linear infinite" }} />
            )}
          </p>
          <p style={{ margin: 0, fontSize: 12, color: "#94a3b8", marginBottom: 8 }}>
            {STATUS_DESCRIPTIONS[v.status]}
          </p>
          <div className="vp-meter" role="img" aria-label="Live audio level">
            <i style={{ transform: `scaleX(${v.level})` }} data-src={v.status === "speaking" ? "out" : "mic"} />
          </div>
        </div>

        {/* Right controls */}
        <div className="vp-controls-right">
          <button
            className="vp-stop-btn"
            onClick={v.stopSpeaking}
            disabled={v.status !== "speaking"}
          >
            <VolumeX size={13} />
            Stop speaking
          </button>
          <label className="vp-check">
            <input
              type="checkbox"
              checked={v.speak}
              onChange={e => v.setSpeak(e.target.checked)}
            />
            <Volume2 size={13} />
            Speak replies
          </label>
        </div>
      </div>

      <p className="vp-hint">
        Click the microphone to start, click again to send. Click while speaking to interrupt.
      </p>

      {/* Error / Notice */}
      {v.error  && <div className="vp-error"  role="alert">  <AlertTriangle size={14} /> {v.error}  </div>}
      {v.notice && <div className="vp-note"   role="status">                              {v.notice} </div>}

      {/* ── Confirm Dialog ───────────────────────────────────────────────────── */}
      {v.pending && (
        <div className="vp-confirm" role="alertdialog" aria-label="Confirm action">
          <p><strong>Action requires confirmation:</strong> {v.pending.summary}</p>
          <div className="vp-confirm-actions">
            <button className="vp-confirm-yes" onClick={() => v.resolve(true)}>
              <CheckCircle size={13} style={{ display: "inline", marginRight: 4 }} />
              Confirm
            </button>
            <button className="vp-confirm-no"  onClick={() => v.resolve(false)}>Cancel</button>
            <span className="vp-confirm-hint">Or say "yes" / "no".</span>
          </div>
        </div>
      )}

      {/* ── Conversation Log ─────────────────────────────────────────────────── */}
      <div className="vp-log" role="log" aria-live="polite" aria-label="Conversation transcript" tabIndex={0}>
        {v.lines.length === 0 && (
          <p className="vp-empty">
            Record or type a request to begin. Try {example}
          </p>
        )}
        {v.lines.map(l => (
          <div key={l.id} className={`vp-line ${l.speaker}`}>
            <div className="vp-speaker-label">
              {l.speaker === "user"
                ? <><Mic size={10} /> You</>
                : l.speaker === "assistant"
                  ? <><Cpu size={10} /> Assistant</>
                  : <><Server size={10} /> System</>
              }
              {l.tag && <span className="vp-tag">{l.tag}</span>}
            </div>
            <div className="vp-bubble">{l.text}</div>
          </div>
        ))}
        <div ref={end} />
      </div>

      {/* ── Text Input ───────────────────────────────────────────────────────── */}
      <form className="vp-text" onSubmit={submit}>
        <label htmlFor="vp-input" className="sr">Type a message</label>
        <input
          id="vp-input"
          className="vp-text-input"
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="Type instead of speaking…"
          maxLength={1000}
        />
        <button type="submit" className="vp-send-btn" disabled={!text.trim() || busy}>
          <Send size={14} /> Send
        </button>
        <button type="button" className="vp-new-chat-btn" onClick={v.reset}>
          <Plus size={14} style={{ display: "inline", marginRight: 3 }} />
          New chat
        </button>
      </form>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </section>
  );
}
