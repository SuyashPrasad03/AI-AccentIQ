import { useState, useEffect } from "react";
import { getScore } from "../../api/scoring.js";
import { ScoreCard } from "./ScoreCard.jsx";
import { HighlightedTranscript } from "./HighlightedTranscript.jsx";

/**
 * ResultsView — displays the full scoring results after processing completes.
 *
 * Props:
 *   recordingId — the recording to fetch scores for
 */
export function ResultsView({ recordingId }) {
  const [score, setScore] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!recordingId) return;
    setLoading(true);
    getScore(recordingId)
      .then((data) => { setScore(data); setLoading(false); })
      .catch((err) => { setError(err.message); setLoading(false); });
  }, [recordingId]);

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
        onWordClick={(w) => {
          // Phase 6 will add the "Explain My Mistake" modal here
          console.log("Word clicked:", w);
        }}
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
    </div>
  );
}
