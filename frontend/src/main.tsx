import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { AuthProvider } from "./AuthContext";

import "./index.css";

// Inject minimal critical CSS synchronously — no external network requests
const style = document.createElement("style");
style.textContent = `
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html, body, #root { height: 100%; }
  body { font-family: Inter, system-ui, -apple-system, sans-serif; -webkit-font-smoothing: antialiased; background: #f5f6fa; }
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.15); border-radius: 3px; }
  @keyframes spin { to { transform: rotate(360deg); } }
`;
document.head.appendChild(style);

// NO StrictMode — avoids "destroy is not a function" with AudioContext in React 18
ReactDOM.createRoot(document.getElementById("root")!).render(
  <AuthProvider>
    <App />
  </AuthProvider>
);
