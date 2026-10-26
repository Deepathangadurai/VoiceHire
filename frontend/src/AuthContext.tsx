import React, { createContext, useContext, useState, useCallback } from "react";

interface AuthCtx {
  token: string;
  role: string;
  getToken: () => string;
  login: (token: string, role: string) => void;
}

const AuthContext = createContext<AuthCtx>({
  token: "", role: "recruiter", getToken: () => "", login: () => {},
});

export const useAuth = () => useContext(AuthContext);

function safeGet(key: string, fallback: string): string {
  try { return localStorage.getItem(key) || fallback; } catch { return fallback; }
}
function safeSet(key: string, val: string): void {
  try { localStorage.setItem(key, val); } catch { /* ignore */ }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState(() => safeGet("vh_token", ""));
  const [role, setRole] = useState(() => safeGet("vh_role", "recruiter"));

  const login = useCallback((t: string, r: string) => {
    setToken(t);
    setRole(r || "recruiter");
    if (t) { safeSet("vh_token", t); safeSet("vh_role", r || "recruiter"); }
    else { try { localStorage.removeItem("vh_token"); localStorage.removeItem("vh_role"); } catch {} }
  }, []);

  const getToken = useCallback(() => token, [token]);

  return (
    <AuthContext.Provider value={{ token, role, getToken, login }}>
      {children}
    </AuthContext.Provider>
  );
}
