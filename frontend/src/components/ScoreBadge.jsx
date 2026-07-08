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
  if (score >= 80) return { bg: "bg-[#2563EB]/10", text: "text-[#2563EB]" };
  if (score >= 60) return { bg: "bg-amber-100", text: "text-amber-700" };
  return { bg: "bg-red-100", text: "text-red-700" };
}
