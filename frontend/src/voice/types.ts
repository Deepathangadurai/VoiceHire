export type Role = "recruiter" | "candidate";
export type Status = "idle" | "recording" | "transcribing" | "thinking" | "speaking";
export interface ServiceHealth { ok: boolean; detail: string; provider?: string; model?: string; voice?: string }
export interface Health {
  local_ai: boolean; cloud_services: boolean; dry_run: boolean;
  llm: ServiceHealth; stt: ServiceHealth; tts: ServiceHealth;
  limits: { audio_max_seconds: number; audio_max_bytes: number };
}
export interface Line { id: string; speaker: "user" | "assistant" | "system"; text: string; tag?: string }
export interface Pending { summary: string }
export interface ChatResponse {
  reply: string; source: "ollama" | "system" | "demo"; pending: Pending | null;
  tool_events: { tool: string; status: string; message?: string }[];
}
