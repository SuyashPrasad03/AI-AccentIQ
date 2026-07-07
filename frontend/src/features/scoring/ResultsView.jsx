import { useState, useEffect } from "react";
import { getScore } from "../../api/scoring.js";
import { ScoreCard } from "./ScoreCard.jsx";
import { HighlightedTranscript } from "./HighlightedTranscript.jsx";
import { ExplainMistakeModal } from "./ExplainMistakeModal.jsx";

/**
 * ResultsView — displays the full scoring results after processing completes.
 */
export function ResultsView({ recordingId }) {
  const [score, setScore] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [explainTarget, setExplainTarget] = useState(null); // { wordData, index }

  useEffect(() => {
    if (!recordingId) return;
    setLoading(true);
    getScore(recordingId)
      .then((data) => { setScore(data); setLoading(false); })
      .catch((err) => { setError(err.message); setLoading(false); });
  }, [recordingId]);

  const handleWordClick = (wordData, index) => {
    if (wordData.detected_issue !== "correct") {
      setExplainTarget({ wordData, index });
    }
  };

  if (loading) {
    return (
      <div className="results-loading">
        <span className="boot-spinner" />
        <p>Loading results…</p>
      </div>
    );
  }

  if (error) {
    return <div className="form-error" role="alert">{error}</div>;
  }

  if (!score) return null;

  return (
    <div className="results-view">
      <ScoreCard
        overall={score.overall_score}
        accuracy={score.accuracy_score}
        fluency={score.fluency_score}
      />

      <HighlightedTranscript
        wordScores={score.word_scores}
        onWordClick={handleWordClick}
      />

      {score.weak_phonemes && score.weak_phonemes.length > 0 && (
        <div className="weak-phonemes-section">
          <h3>Sounds to practice</h3>
          <div className="weak-phoneme-chips">
            {score.weak_phonemes.map((ph, i) => (
              <span key={i} className="phoneme-chip">{ph}</span>
            ))}
          </div>
        </div>
      )}

      {explainTarget && (
        <ExplainMistakeModal
          recordingId={recordingId}
          wordIndex={explainTarget.index}
          wordData={explainTarget.wordData}
          onClose={() => setExplainTarget(null)}
        />
      )}
    </div>
  );
}
