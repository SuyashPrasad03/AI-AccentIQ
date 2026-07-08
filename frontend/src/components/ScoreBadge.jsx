/**
 * ScoreBadge — circular pill showing a score with range-based tint.
 * 80+ green, 60-79 amber, <60 red. Background is soft tint, not solid.
 */
export function ScoreBadge({ score }) {
  const rounded = Math.round(score);
  const { bg, text } = getScoreStyle(rounded);

  return (
    <span className={`inline-flex items-center justify-center w-11 h-11 rounded-full font-bold text-sm ${bg} ${text}`}>
      {rounded}
    </span>
  );
}

function getScoreStyle(score) {
  if (score >= 80) return { bg: "bg-success-soft", text: "text-success" };
  if (score >= 60) return { bg: "bg-warning-soft", text: "text-warning" };
  return { bg: "bg-danger-soft", text: "text-danger" };
}
