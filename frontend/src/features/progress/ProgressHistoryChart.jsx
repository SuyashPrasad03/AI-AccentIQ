import { useState, useEffect } from "react";
import { getProgressHistory } from "../../api/progress.js";

/**
 * ProgressHistoryChart — simple visual timeline of scores.
 * Uses a CSS-based bar chart (no external charting library for Phase 8).
 * Upgrade path: Recharts in Phase 11.
 */
export function ProgressHistoryChart() {
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    getProgressHistory(20)
      .then((d) => { setHistory(d); setLoading(false); })
      .catch((err) => { setError(err.message); setLoading(false); });
  }, []);

  if (loading) return null;
  if (error) return <div className="form-error">{error}</div>;
  if (!history || history.entries.length === 0) return null;

  // Reverse so oldest is first (left to right)
  const entries = [...history.entries].reverse();

  return (
    <div className="history-chart-card">
      <h3 className="history-title">Score History</h3>
      <div className="history-bars" role="img" aria-label="Score history chart">
        {entries.map((entry, i) => (
          <div key={i} className="history-bar-col">
            <div
              className="history-bar"
              style={{ height: `${Math.max(entry.overall_score, 5)}%` }}
              title={`${Math.round(entry.overall_score)} — ${new Date(entry.created_at).toLocaleDateString()}`}
            />
            <span className="history-bar-label">
              {Math.round(entry.overall_score)}
            </span>
          </div>
        ))}
      </div>
      <p className="history-total">{history.total} total recordings</p>
    </div>
  );
}
