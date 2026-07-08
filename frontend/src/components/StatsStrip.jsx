import { useSelector } from "react-redux";
import { selectIsAuthenticated } from "../store/authSlice.js";

/**
 * StatsStrip — 3 compact stat cards: Average Score, Best Score, Recordings count.
 * Shows only for authenticated users with history.
 */
export function StatsStrip({ history }) {
  const isAuth = useSelector(selectIsAuthenticated);

  if (!isAuth || !history || history.entries.length === 0) return null;

  const scores = history.entries.map((e) => e.overall_score);
  const avg = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
  const best = Math.round(Math.max(...scores));
  const count = history.total;

  return (
    <div className="grid grid-cols-3 gap-3 animate-fade-in">
      <StatCard label="Average Score" value={avg} suffix="/100" />
      <StatCard label="Best Score" value={best} suffix="/100" />
      <StatCard label="Recordings" value={count} />
    </div>
  );
}

function StatCard({ label, value, suffix }) {
  return (
    <div className="bg-bg-soft rounded-[var(--radius-card)] px-4 py-5 text-center">
      <div className="flex items-baseline justify-center gap-0.5">
        <span className="text-2xl font-bold text-ink">{value}</span>
        {suffix && <span className="text-sm text-ink-faint font-medium">{suffix}</span>}
      </div>
      <p className="text-[11px] text-ink-muted font-medium uppercase tracking-wider mt-1">{label}</p>
    </div>
  );
}
