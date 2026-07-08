import { useState, useEffect } from "react";

export function ScoreCard({ overall, accuracy, fluency }) {
  const [displayScore, setDisplayScore] = useState(0);
  const [animatedOffset, setAnimatedOffset] = useState(440);

  useEffect(() => {
    const target = Math.round(overall);
    const duration = 1200;
    const start = performance.now();
    const animate = (now) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayScore(Math.round(target * eased));
      setAnimatedOffset(440 - (440 * (target / 100) * eased));
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [overall]);

  const getColor = (s) => s >= 80 ? "#2563EB" : s >= 60 ? "#D97706" : "#DC2626";
  const getLabel = (s) => s >= 90 ? "Excellent" : s >= 80 ? "Great" : s >= 70 ? "Good" : s >= 60 ? "Fair" : "Needs Work";
  const color = getColor(overall);

  return (
    <div className="card text-center py-10 animate-scale-in">
      {/* Score ring */}
      <div className="score-ring mx-auto mb-6">
        <svg width="160" height="160" viewBox="0 0 160 160">
          <circle className="track" cx="80" cy="80" r="70" />
          <circle className="progress" cx="80" cy="80" r="70"
            stroke={color} strokeDasharray="440" strokeDashoffset={animatedOffset} />
        </svg>
        <div className="value">
          <span className="text-4xl font-bold" style={{ color }}>{displayScore}</span>
          <span className="text-xs text-ink-faint font-medium">/100</span>
        </div>
      </div>

      <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-pill text-xs font-semibold mb-6"
        style={{ background: `${color}15`, color }}>
        {getLabel(overall)}
      </div>

      {/* Sub-scores */}
      <div className="flex justify-center gap-10">
        <SubScore label="Accuracy" value={accuracy} />
        <SubScore label="Fluency" value={fluency} />
      </div>
    </div>
  );
}

function SubScore({ label, value }) {
  const color = value >= 80 ? "text-[#2563EB]" : value >= 60 ? "text-amber-600" : "text-red-600";
  return (
    <div className="flex flex-col items-center">
      <span className={`text-2xl font-bold ${color}`}>{Math.round(value)}</span>
      <span className="text-[11px] text-ink-muted uppercase tracking-wide mt-0.5 font-medium">{label}</span>
    </div>
  );
}
