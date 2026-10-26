import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatResponse, Health, Line, Pending, Role, Status } from "./types";

interface Opts { role: Role; getToken: () => string | Promise<string>; apiBase?: string }

export function useVoiceAssistant({ getToken, apiBase = "/api" }: Opts) {
  const [status, setStatus] = useState<Status>("idle");
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState<string>();
  const [lines, setLines] = useState<Line[]>([]);
  const [level, setLevel] = useState(0);
  const [error, setError] = useState<string>();
  const [notice, setNotice] = useState<string>();
  const [pending, setPending] = useState<Pending | null>(null);
  const [speak, setSpeak] = useState(true);

  const rec = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const chunks = useRef<Blob[]>([]);
  const audioCtx = useRef<AudioContext | null>(null);
  const micAn = useRef<AnalyserNode | null>(null);
  const outAn = useRef<AnalyserNode | null>(null);
  const player = useRef<HTMLAudioElement | null>(null);
  const raf = useRef(0);
  const stopTimer = useRef<number>();
  const statusRef = useRef<Status>("idle");
  const set = (s: Status) => { statusRef.current = s; setStatus(s); };

  const call = useCallback(async (path: string, init: RequestInit = {}, raw = false) => {
    let r: Response;
    try {
      r = await fetch(`${apiBase}/voice${path}`, { ...init, headers: { ...(init.headers || {}), Authorization: `Bearer ${await getToken()}` } });
    } catch { throw new Error("Cannot reach the VoiceHire server. Check that the backend is running."); }
    if (!r.ok) {
      let m = `Request failed (HTTP ${r.status}).`;
      try { const d = (await r.json()).detail; m = typeof d === "string" ? d : d?.message ?? m; } catch { /* keep default */ }
      throw new Error(m);
    }
    return raw ? r : r.json();
  }, [apiBase, getToken]);
  const json = (b: object): RequestInit => ({ method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b) });

  const refreshHealth = useCallback(async () => {
    try { setHealth(await call("/health")); setHealthError(undefined); }
    catch (e: any) { setHealth(null); setHealthError(e.message); }
  }, [call]);
  useEffect(() => { void refreshHealth(); }, [refreshHealth]);

  const add = (speaker: Line["speaker"], text: string, tag?: string) =>
    setLines((p) => [...p, { id: crypto.randomUUID(), speaker, text, tag }]);

  // Real levels: RMS of actual mic / playback samples. Zero when nothing is capturing or playing.
  const meter = useCallback(() => {
    const an = statusRef.current === "recording" ? micAn.current : statusRef.current === "speaking" ? outAn.current : null;
    if (an) {
      const b = new Uint8Array(an.fftSize); an.getByteTimeDomainData(b);
      let s = 0; for (const v of b) s += ((v - 128) / 128) ** 2;
      setLevel(Math.min(1, Math.sqrt(s / b.length) * 3));
    } else setLevel(0);
    raf.current = requestAnimationFrame(meter);
  }, []);
  useEffect(() => { raf.current = requestAnimationFrame(meter); return () => cancelAnimationFrame(raf.current); }, [meter]);

  const ensureAudio = () => {
    if (!audioCtx.current) {
      audioCtx.current = new AudioContext();
      player.current = new Audio();
      const src = audioCtx.current.createMediaElementSource(player.current);
      outAn.current = audioCtx.current.createAnalyser(); outAn.current.fftSize = 512;
      src.connect(outAn.current); outAn.current.connect(audioCtx.current.destination);
    }
    void audioCtx.current.resume();
  };

  const stopSpeaking = useCallback(() => {
    player.current?.pause();
    if (statusRef.current === "speaking") set("idle");
  }, []);

  const speakText = useCallback(async (text: string) => {
    if (!speak) { set("idle"); return; }
    try {
      const r = await call("/tts", json({ text }), true);
      const url = URL.createObjectURL(await r.blob());
      ensureAudio();
      const el = player.current!;
      el.src = url;
      el.onended = () => { URL.revokeObjectURL(url); if (statusRef.current === "speaking") set("idle"); };
      set("speaking");
      await el.play();
    } catch (e: any) { setNotice(`Spoken reply unavailable: ${e.message} The answer is shown as text.`); set("idle"); }
  }, [call, speak]);

  const handleReply = useCallback(async (r: ChatResponse) => {
    r.tool_events.forEach((t) => add("system", `Looked up with tool ${t.tool}: ${t.status}${t.message ? ` (${t.message})` : ""}`));
    add("assistant", r.reply, "Local AI");
    setPending(r.pending);
    await speakText(r.reply);
  }, [speakText]);

  const chat = useCallback(async (text: string) => {
    set("thinking"); setError(undefined);
    try { await handleReply(await call("/chat", json({ text }))); }
    catch (e: any) { setError(e.message); set("idle"); void refreshHealth(); }
  }, [call, handleReply, refreshHealth]);

  const sendText = useCallback(async (text: string) => { stopSpeaking(); add("user", text); await chat(text); }, [chat, stopSpeaking]);

  const resolve = useCallback(async (approve: boolean) => {
    setPending(null); set("thinking");
    try { const r = await call("/confirm", json({ approve })); add("assistant", r.reply, "System"); await speakText(r.reply); }
    catch (e: any) { setError(e.message); set("idle"); }
  }, [call, speakText]);

  const transcribe = useCallback(async (blob: Blob) => {
    set("transcribing");
    try {
      const fd = new FormData(); fd.append("audio", blob, "voice." + (blob.type.includes("mp4") ? "m4a" : blob.type.includes("ogg") ? "ogg" : "webm"));
      const r = await call("/stt", { method: "POST", body: fd });
      if (!r.text) { setNotice("No speech was detected. Try again, speak closer to the microphone, or type."); set("idle"); return; }
      add("user", r.text); await chat(r.text);
    } catch (e: any) { setError(`${e.message} You can type your request instead.`); set("idle"); void refreshHealth(); }
  }, [call, chat, refreshHealth]);

  const releaseMic = () => { stream.current?.getTracks().forEach((t) => t.stop()); stream.current = null; micAn.current = null; };

  const stopRecording = useCallback(() => { clearTimeout(stopTimer.current); if (rec.current?.state === "recording") rec.current.stop(); }, []);

  const startRecording = useCallback(async () => {
    setError(undefined); setNotice(undefined);
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") { setError("This browser cannot record audio here (HTTPS or localhost required). Use the text box."); return; }
    try { stream.current = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } }); }
    catch (e: any) {
      setError(e?.name === "NotAllowedError" ? "Microphone access is blocked. Allow it in the browser's site settings, or use the text box."
        : e?.name === "NotFoundError" ? "No microphone was found." : "The microphone could not be started.");
      return;
    }
    ensureAudio();
    const src = audioCtx.current!.createMediaStreamSource(stream.current);
    micAn.current = audioCtx.current!.createAnalyser(); micAn.current.fftSize = 512; src.connect(micAn.current);
    const mime = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"].find((m) => MediaRecorder.isTypeSupported(m));
    const mr = (rec.current = new MediaRecorder(stream.current, mime ? { mimeType: mime } : undefined));
    chunks.current = [];
    mr.ondataavailable = (e) => e.data.size && chunks.current.push(e.data);
    mr.onerror = () => { setError("Recording failed."); releaseMic(); set("idle"); };
    mr.onstop = () => {
      releaseMic();
      const blob = new Blob(chunks.current, { type: mr.mimeType || "audio/webm" });
      if (blob.size < 1500) { setNotice("The recording was too short."); set("idle"); } else void transcribe(blob);
    };
    mr.start(); set("recording");   // "recording" is only ever set while MediaRecorder is actually capturing
    stopTimer.current = window.setTimeout(() => { setNotice("Maximum recording length reached."); stopRecording(); }, (health?.limits.audio_max_seconds ?? 60) * 1000);
  }, [health, stopRecording, transcribe]);

  const toggleRecording = useCallback(() => {
    if (statusRef.current === "recording") stopRecording();
    else if (statusRef.current === "speaking") { stopSpeaking(); void startRecording(); } // barge-in
    else if (statusRef.current === "idle") void startRecording();
  }, [startRecording, stopRecording, stopSpeaking]);

  useEffect(() => () => { clearTimeout(stopTimer.current); rec.current?.state === "recording" && rec.current.stop(); releaseMic(); player.current?.pause(); audioCtx.current?.close(); }, []);

  const reset = async () => { try { await call("/reset", { method: "POST" }); } catch { /* ignore */ } setLines([]); setPending(null); setError(undefined); setNotice(undefined); };
  return { status, health, healthError, lines, level, error, notice, pending, speak, setSpeak, toggleRecording, stopSpeaking, sendText, resolve, reset, refreshHealth,
           canRecord: !!health?.stt.ok, canChat: !!health?.llm.ok };
}
