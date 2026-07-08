/**
 * MetricCards — breakdown of scoring components as visual cards.
 * Only shows metrics that have real data from the backend.
 */
export function MetricCards({ score }) {
  if (!score) return null;

  const metrics = [
    { label: "Accuracy", value: score.accuracy_score, icon: "🎯", desc: "Phoneme precision" },
    { label: "Fluency", value: score.fluency_score, icon: "💬", desc: "Pace & rhythm" },
    { label: "Words Analyzed", value: score.word_scores?.length || 0, icon: "📝", desc: "Total words", isCount: true },
    { label: "Weak Sounds", value: score.weak_phonemes?.length || 0, icon: "⚠️", desc: "Phonemes to practice", isCount: true },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 animate-slide-up">
      {metrics.map((m) => (
        <div key={m.label} className="card p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-base">{m.icon}</span>
            <span className="text-[11px] text-ink-muted font-medium uppercase tracking-wide">{m.label}</span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className={`text-2xl font-bold ${m.isCount ? "text-ink" : getScoreColor(m.value)}`}>
              {Math.round(m.value)}
            </span>
            {!m.isCount && <span className="text-xs text-ink-faint">/100</span>}
          </div>
          {!m.isCount && <ProgressBar value={m.value} />}
          <p className="text-[10px] text-ink-faint mt-1">{m.desc}</p>
        </div>
      ))}
    </div>
  );
}

function ProgressBar({ value }) {
  const color = value >= 80 ? "bg-[#2563EB]" : value >= 60 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="w-full h-1.5 bg-border-soft rounded-full mt-2 overflow-hidden">
      <div className={`h-full rounded-full transition-all duration-1000 ${color}`} style={{ width: `${Math.min(value, 100)}%` }} />
    </div>
  );
}

function getScoreColor(v) {
  if (v >= 80) return "text-[#2563EB]";
  if (v >= 60) return "text-amber-600";
  return "text-red-600";
}
