/** Thin fetch wrapper that injects Bearer token and handles errors. */
export async function apiFetch(path: string, token: string, init: RequestInit = {}): Promise<any> {
  const res = await fetch(`http://localhost:8000${path}`, {
    ...init,
    headers: {
      ...(init.headers || {}),
      Authorization: `Bearer ${token}`,
      ...(init.body && typeof init.body === "string" ? { "Content-Type": "application/json" } : {}),
    },
  });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try { const d = await res.json(); msg = d?.detail?.message || d?.detail || msg; } catch {}
    throw new Error(msg);
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("json") ? res.json() : res.text();
}
