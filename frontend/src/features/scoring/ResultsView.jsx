import { useState, useEffect, useRef } from "react";
import { getScore } from "../../api/scoring.js";
import { ScoreCard } from "./ScoreCard.jsx";
import { MetricCards } from "./MetricCards.jsx";
import { HighlightedTranscript } from "./HighlightedTranscript.jsx";
import { ExplainMistakeModal } from "./ExplainMistakeModal.jsx";

export function ResultsView({ recordingId }) {
  const [score, setScore] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [explainTarget, setExplainTarget] = useState(null);
  const fetchedRef = useRef(null);

  useEffect(() => {
    if (!recordingId || fetchedRef.current === recordingId) return;
    fetchedRef.current = recordingId;
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
      <div className="flex flex-col items-center gap-4 py-16">
        <div className="w-10 h-10 border-[3px] border-border border-t-primary rounded-full animate-[spin_0.8s_linear_infinite]" />
        <p className="text-ink-muted text-sm">Loading results…</p>
      </div>
    );
  }

  if (error) return <div className="card bg-danger-soft border-danger/20 text-danger text-sm p-4">{error}</div>;
  if (!score) return null;

  return (
    <div className="flex flex-col gap-5">
      <ScoreCard overall={score.overall_score} accuracy={score.accuracy_score} fluency={score.fluency_score} />
      <MetricCards score={score} />
      <HighlightedTranscript wordScores={score.word_scores} onWordClick={handleWordClick} />

      {/* Weak phonemes */}
      {score.weak_phonemes?.length > 0 && (
        <div className="card animate-slide-up">
          <h3 className="font-display font-bold text-sm text-ink mb-3">Sounds to practice</h3>
          <div className="flex flex-wrap gap-2">
            {score.weak_phonemes.map((ph, i) => (
              <span key={i} className="pill pill-danger font-mono text-xs">{ph}</span>
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
