import { useEffect, useState } from "react";
import { fetchHealth, HealthResponse } from "./api/health";
import "./App.css";

type LoadState = "idle" | "loading" | "success" | "error";

function StatusBadge({
  label,
  status,
}: {
  label: string;
  status: "connected" | "disconnected" | undefined;
}) {
  const connected = status === "connected";
  return (
    <div className="status-row">
      <span className="status-label">{label}</span>
      <span className={`status-badge ${connected ? "badge-ok" : "badge-error"}`}>
        {connected ? "✓ Connected" : "✗ Disconnected"}
      </span>
    </div>
  );
}

export default function App() {
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>("");

  useEffect(() => {
    setLoadState("loading");
    fetchHealth()
      .then((data) => {
        setHealth(data);
        setLoadState("success");
      })
      .catch((err: Error) => {
        setErrorMsg(err.message);
        setLoadState("error");
      });
  }, []);

  return (
    <main className="app-container">
      <header className="app-header">
        <h1>🎤 AI Pronunciation Coach</h1>
        <p className="subtitle">System Health</p>
      </header>

      <section className="health-card" aria-live="polite" aria-label="Service health status">
        {loadState === "loading" && (
          <p className="loading-text">Checking services…</p>
        )}

        {loadState === "error" && (
          <div className="error-banner" role="alert">
            <strong>Could not reach the backend.</strong>
            <p>{errorMsg}</p>
          </div>
        )}

        {loadState === "success" && health && (
          <>
            <div
              className={`overall-status ${health.status === "ok" ? "overall-ok" : "overall-degraded"}`}
              aria-label={`Overall status: ${health.status}`}
            >
              {health.status === "ok" ? "✅ All Systems Operational" : "⚠️ Degraded"}
            </div>
            <div className="status-list">
              <StatusBadge label="Backend" status="connected" />
              <StatusBadge label="MySQL" status={health.mysql} />
              <StatusBadge label="MongoDB" status={health.mongo} />
            </div>
          </>
        )}
      </section>

      <footer className="app-footer">
        <small>Phase 1 — Foundation Skeleton</small>
      </footer>
    </main>
  );
}
