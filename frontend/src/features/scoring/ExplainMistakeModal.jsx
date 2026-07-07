import { useState, useEffect } from "react";
import { explainWord } from "../../api/feedback.js";

/**
 * ExplainMistakeModal — shows AI-generated pronunciation feedback
 * when a user clicks a highlighted word.
 *
 * Props:
 *   recordingId – current recording ID
 *   wordIndex   – index of the clicked word in the scores array
 *   wordData    – { word, detected_issue, word_score, ... }
 *   onClose     – callback to close the modal
 */
export function ExplainMistakeModal({ recordingId, wordIndex, wordData, onClose }) {
  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (recordingId == null || wordIndex == null) return;
    setLoading(true);
    setError(null);

    explainWord(recordingId, wordIndex)
      .then((data) => { setExplanation(data); setLoading(false); })
      .catch((err) => { setError(err.message); setLoading(false); });
  }, [recordingId, wordIndex]);

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Pronunciation explanation">
      <div className="modal-box explain-modal">
        <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>

        <div className="explain-header">
          <span className="explain-word">{wordData?.word}</span>
          <span className={`explain-badge issue-${wordData?.detected_issue}`}>
            {wordData?.detected_issue}
          </span>
        </div>

        {loading && (
          <div className="explain-loading">
            <span className="boot-spinner" />
            <p>Getting explanation…</p>
          </div>
        )}

        {error && (
          <div className="form-error" role="alert">{error}</div>
        )}

        {explanation && !loading && (
          <div className="explain-content">
            <section className="explain-section">
              <h4>What happened</h4>
              <p>{explanation.explanation}</p>
            </section>

            <section className="explain-section">
              <h4>How to fix it</h4>
              <p>{explanation.mouth_position_tip}</p>
            </section>

            {explanation.practice_words && explanation.practice_words.length > 0 && (
              <section className="explain-section">
                <h4>Practice these words</h4>
                <div className="practice-word-list">
                  {explanation.practice_words.map((w, i) => (
                    <span key={i} className="practice-word-chip">{w}</span>
                  ))}
                </div>
              </section>
            )}

            {explanation.from_cache && (
              <p className="explain-cache-note">⚡ Instant (cached explanation)</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
