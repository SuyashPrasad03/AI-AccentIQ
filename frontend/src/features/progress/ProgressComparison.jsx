import { useState, useEffect } from "react";
import { getComparison } from "../../api/progress.js";

/**
 * ProgressComparison — shows N vs N-1 score deltas.
 * For registered users with history.
 */
export function ProgressComparison({ recordingId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!recordingId) return;
    setLoading(true);
    getComparison(recordingId)
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [recordingId]);

  if (loading || !data) return null;
  if (!data.has_previous) {
    return (
      <div className="progress-card progress-empty">
        <p>This is your first recording. Upload another to see your progress.</p>
      </div>
    );
  }

  return (
    <div className="progress-card">
      <h3 className="progress-title">Progress vs. Last Recording</h3>
      <div className="delta-grid">
        <DeltaCard label="Overall" prev={data.overall.prev} curr={data.overall.curr} delta={data.overall.delta} />
        <DeltaCard label="Accuracy" prev={data.accuracy.prev} curr={data.accuracy.curr} delta={data.accuracy.delta} />
        <DeltaCard label="Fluency" prev={data.fluency.prev} curr={data.fluency.curr} delta={data.fluency.delta} />
      </div>

      {data.per_phoneme.length > 0 && (
        <div className="phoneme-deltas">
          <h4>Per Sound</h4>
          <div className="phoneme-delta-list">
            {data.per_phoneme.map((p, i) => (
              <div key={i} className="phoneme-delta-row">
                <span className="phoneme-delta-label">/{p.phoneme}/</span>
                <span className="phoneme-delta-values">
                  {Math.round(p.prev)} → {Math.round(p.curr)}
                </span>
                <DeltaBadge delta={p.delta} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function DeltaCard({ label, prev, curr, delta }) {
  return (
    <div className="delta-card">
      <span className="delta-label">{label}</span>
      <div className="delta-values">
        <span className="delta-prev">{prev != null ? Math.round(prev) : "—"}</span>
        <span className="delta-arrow">→</span>
        <span className="delta-curr">{Math.round(curr)}</span>
      </div>
      <DeltaBadge delta={delta} />
    </div>
  );
}

function DeltaBadge({ delta }) {
  if (delta == null) return null;
  const isPositive = delta > 0;
  const cls = isPositive ? "delta-positive" : delta < 0 ? "delta-negative" : "delta-neutral";
  return (
    <span className={`delta-badge ${cls}`}>
      {isPositive ? "+" : ""}{Math.round(delta)}
    </span>
  );
}
