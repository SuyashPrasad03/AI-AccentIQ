import {
  RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell, Legend,
} from "recharts";

const MAROON = "#991B1B";

/**
 * ScoreRadar — radar chart of current recording's metrics.
 */
export function ScoreRadar({ score }) {
  if (!score) return null;

  const data = [
    { metric: "Accuracy", value: score.accuracy_score },
    { metric: "Fluency", value: score.fluency_score },
    { metric: "Overall", value: score.overall_score },
  ];

  // Add word-level derived metrics if available
  if (score.word_scores?.length > 0) {
    const confidences = score.word_scores.map((w) => w.confidence * 100);
    const avgConfidence = confidences.reduce((a, b) => a + b, 0) / confidences.length;
    data.push({ metric: "Confidence", value: Math.round(avgConfidence) });

    const correctPct = (score.word_scores.filter((w) => w.detected_issue === "correct").length / score.word_scores.length) * 100;
    data.push({ metric: "Word Accuracy", value: Math.round(correctPct) });
  }

  return (
    <div className="card p-5 animate-slide-up">
      <h3 className="font-display font-bold text-sm text-ink mb-4">Performance Overview</h3>
      <ResponsiveContainer width="100%" height={220}>
        <RadarChart data={data}>
          <PolarGrid stroke="#E5E9FF" />
          <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11, fill: "#6B7280" }} />
          <Radar name="Score" dataKey="value" stroke={MAROON} fill={MAROON} fillOpacity={0.15} strokeWidth={2} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

/**
 * ScoreBar — bar chart of same metrics for at-a-glance comparison.
 */
export function ScoreBar({ score }) {
  if (!score) return null;

  const data = [
    { name: "Overall", value: score.overall_score },
    { name: "Accuracy", value: score.accuracy_score },
    { name: "Fluency", value: score.fluency_score },
  ];

  return (
    <div className="card p-5 animate-slide-up">
      <h3 className="font-display font-bold text-sm text-ink mb-4">Score Breakdown</h3>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} barSize={32}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E9FF" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#6B7280" }} axisLine={false} tickLine={false} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #E5E9FF", fontSize: 12 }} />
          <Bar dataKey="value" fill={MAROON} radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/**
 * MistakePie — donut chart showing correct/unclear/mispronounced proportions.
 */
export function MistakePie({ wordScores }) {
  if (!wordScores || wordScores.length === 0) return null;

  const counts = { correct: 0, mispronounced: 0, unclear: 0, mistimed: 0 };
  wordScores.forEach((w) => { counts[w.detected_issue] = (counts[w.detected_issue] || 0) + 1; });

  const data = [
    { name: "Correct", value: counts.correct, color: "#2563EB" },
    { name: "Mispronounced", value: counts.mispronounced, color: "#DC2626" },
    { name: "Unclear", value: counts.unclear, color: "#D97706" },
    { name: "Mistimed", value: counts.mistimed, color: "#EA580C" },
  ].filter((d) => d.value > 0);

  return (
    <div className="card p-5 animate-slide-up">
      <h3 className="font-display font-bold text-sm text-ink mb-4">Word Quality Distribution</h3>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie data={data} cx="50%" cy="50%" innerRadius={50} outerRadius={75}
            paddingAngle={3} dataKey="value" strokeWidth={0}>
            {data.map((entry, i) => <Cell key={i} fill={entry.color} />)}
          </Pie>
          <Legend iconType="circle" iconSize={8}
            formatter={(value) => <span style={{ fontSize: 11, color: "#6B7280" }}>{value}</span>} />
          <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #E5E9FF", fontSize: 12 }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
