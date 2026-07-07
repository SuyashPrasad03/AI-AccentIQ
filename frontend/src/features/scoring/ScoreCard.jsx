/**
 * ScoreCard — displays the overall pronunciation score and sub-metrics.
 */
export function ScoreCard({ overall, accuracy, fluency }) {
  const getColorClass = (score) => {
    if (score >= 80) return "score-good";
    if (score >= 60) return "score-okay";
    return "score-poor";
  };

  return (
    <div className="score-card">
      <div className={`score-main ${getColorClass(overall)}`}>
        <span className="score-number">{Math.round(overall)}</span>
        <span className="score-label">Overall Score</span>
      </div>
      <div className="score-subs">
        <div className="score-sub">
          <span className={`score-sub-value ${getColorClass(accuracy)}`}>
            {Math.round(accuracy)}
          </span>
          <span className="score-sub-label">Accuracy</span>
        </div>
        <div className="score-sub">
          <span className={`score-sub-value ${getColorClass(fluency)}`}>
            {Math.round(fluency)}
          </span>
          <span className="score-sub-label">Fluency</span>
        </div>
      </div>
    </div>
  );
}
