/**
 * HighlightedTranscript — renders words with color-coded highlighting
 * based on the mistake classification taxonomy.
 *
 * Colors:
 *   correct       → green
 *   mispronounced → red
 *   unclear       → yellow/orange
 *   mistimed      → blue
 */
export function HighlightedTranscript({ wordScores, onWordClick }) {
  if (!wordScores || wordScores.length === 0) {
    return <p className="transcript-empty">No transcript available.</p>;
  }

  const getClass = (issue) => {
    switch (issue) {
      case "correct": return "word-correct";
      case "mispronounced": return "word-mispronounced";
      case "unclear": return "word-unclear";
      case "mistimed": return "word-mistimed";
      default: return "";
    }
  };

  return (
    <div className="highlighted-transcript" role="region" aria-label="Pronunciation analysis">
      {wordScores.map((w, i) => (
        <button
          key={i}
          className={`word-chip ${getClass(w.detected_issue)}`}
          onClick={() => onWordClick?.(w, i)}
          title={`${w.detected_issue} (score: ${w.word_score})`}
          aria-label={`${w.word}: ${w.detected_issue}, score ${Math.round(w.word_score)}`}
        >
          {w.word}
        </button>
      ))}
      <div className="transcript-legend">
        <span className="legend-item"><span className="legend-dot word-correct" /> Correct</span>
        <span className="legend-item"><span className="legend-dot word-mispronounced" /> Mispronounced</span>
        <span className="legend-item"><span className="legend-dot word-unclear" /> Unclear</span>
        <span className="legend-item"><span className="legend-dot word-mistimed" /> Mistimed</span>
      </div>
    </div>
  );
}
