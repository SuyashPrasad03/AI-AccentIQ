import { useState, useEffect, useRef } from "react";
import { fetchHealth } from "../../api/health.js";

/**
 * StatusFooterDot — subtle system health indicator in the footer.
 * Green dot = all connected, amber = degraded, red = down.
 * Tooltip on hover shows the detail.
 */
export function StatusFooterDot() {
  const [health, setHealth] = useState(null);
  const [showDetail, setShowDetail] = useState(false);
  const fetched = useRef(false);

  useEffect(() => {
    if (fetched.current) return;
    fetched.current = true;
    fetchHealth()
      .then(setHealth)
      .catch(() => setHealth({ status: "error", mysql: "disconnected", mongo: "disconnected" }));
  }, []);

  const dotColor = !health
    ? "bg-ink-faint"
    : health.status === "ok"
    ? "bg-success"
    : "bg-warning";

  const statusText = !health
    ? "Checking…"
    : health.status === "ok"
    ? "All systems operational"
    : "Some services degraded";

  return (
    <div className="relative inline-flex items-center">
      <button
        className="flex items-center gap-2 text-xs text-ink-faint hover:text-ink-muted transition-colors"
        onClick={() => setShowDetail(!showDetail)}
        aria-label="System status"
      >
        <span className={`w-2 h-2 rounded-full ${dotColor}`} />
        <span className="hidden sm:inline">{statusText}</span>
      </button>

      {showDetail && health && (
        <div className="absolute bottom-full left-0 mb-2 p-3 bg-white rounded-card shadow-glow border border-mist text-xs min-w-[180px] animate-fade-in">
          <div className="flex items-center gap-2 mb-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${health.mysql === "connected" ? "bg-success" : "bg-danger"}`} />
            <span className="text-ink-muted">MySQL: {health.mysql}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-1.5 h-1.5 rounded-full ${health.mongo === "connected" ? "bg-success" : "bg-danger"}`} />
            <span className="text-ink-muted">MongoDB: {health.mongo}</span>
          </div>
        </div>
      )}
    </div>
  );
}
