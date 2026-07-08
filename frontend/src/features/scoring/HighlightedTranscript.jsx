import { useState } from "react";

export function HighlightedTranscript({ wordScores, onWordClick }) {
  const [tooltip, setTooltip] = useState(null);

  if (!wordScores || wordScores.length === 0) return null;

  const getStyle = (issue) => {
    switch (issue) {
      case "correct": return "bg-success-soft text-success border-success/20 hover:bg-success/10";
      case "mispronounced": return "bg-danger-soft text-danger border-danger/20 hover:bg-danger/10";
      case "unclear": return "bg-warning-soft text-warning border-warning/20 hover:bg-warning/10";
      case "mistimed": return "bg-secondary-soft text-secondary border-secondary/20 hover:bg-secondary/10";
      default: return "bg-bg-soft text-ink-muted border-border";
    }
  };

  return (
    <div className="card animate-slide-up">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-display font-bold text-sm text-ink">Word-by-word analysis</h3>
        <span className="text-[10px] text-ink-faint">Click any word for details</span>
      </div>

      <div className="flex flex-wrap gap-1.5 mb-4 relative">
        {wordScores.map((w, i) => (
          <button
            key={i}
            className={`relative px-2.5 py-1 rounded-md text-sm font-medium border transition-all duration-150
              hover:scale-105 hover:shadow-sm cursor-pointer ${getStyle(w.detected_issue)}`}
            onClick={() => onWordClick?.(w, i)}
            onMouseEnter={() => setTooltip({ word: w, index: i })}
            onMouseLeave={() => setTooltip(null)}
            onFocus={() => setTooltip({ word: w, index: i })}
            onBlur={() => setTooltip(null)}
            aria-label={`${w.word}: ${w.detected_issue}, score ${Math.round(w.word_score)}`}
          >
            {w.word}

            {/* Tooltip */}
            {tooltip?.index === i && w.detected_issue !== "correct" && (
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 pointer-events-none animate-fade-in">
                <div className="bg-ink text-white text-[11px] rounded-lg px-3 py-2 shadow-lg whitespace-nowrap max-w-[200px]">
                  <div className="font-semibold mb-0.5">{w.detected_issue}</div>
                  {w.expected_phonemes?.length > 0 && (
                    <div className="font-mono text-[10px] opacity-80">
                      Expected: /{w.expected_phonemes.join("")}/
                    </div>
                  )}
                  {w.substituted_as?.length > 0 && (
                    <div className="font-mono text-[10px] opacity-80">
                      Detected: /{w.substituted_as.join("")}/
                    </div>
                  )}
                  <div className="text-[10px] opacity-70 mt-0.5">Score: {Math.round(w.word_score)}</div>
                  {/* Arrow */}
                  <div className="absolute top-full left-1/2 -translate-x-1/2 w-2 h-2 bg-ink rotate-45 -mt-1" />
                </div>
              </div>
            )}
          </button>
        ))}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 pt-3 border-t border-border-soft">
        <Legend color="bg-success" label="Correct" />
        <Legend color="bg-danger" label="Mispronounced" />
        <Legend color="bg-warning" label="Unclear" />
        <Legend color="bg-secondary" label="Mistimed" />
      </div>
    </div>
  );
}

function Legend({ color, label }) {
  return (
    <span className="flex items-center gap-1.5 text-[11px] text-ink-muted">
      <span className={`w-2.5 h-2.5 rounded-full ${color}`} />
      {label}
    </span>
  );
}
