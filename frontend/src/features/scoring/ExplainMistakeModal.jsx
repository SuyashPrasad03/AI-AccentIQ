import { useState, useEffect } from "react";
import { explainWord } from "../../api/feedback.js";

export function ExplainMistakeModal({ recordingId, wordIndex, wordData, onClose }) {
  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (recordingId == null || wordIndex == null) return;
    setLoading(true);
    explainWord(recordingId, wordIndex)
      .then((data) => { setExplanation(data); setLoading(false); })
      .catch((err) => { setError(err.message); setLoading(false); });
  }, [recordingId, wordIndex]);

  const issueStyle = {
    mispronounced: "pill-danger",
    unclear: "pill-warning",
    mistimed: "pill-primary",
  }[wordData?.detected_issue] || "pill-muted";

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-ink/30 backdrop-blur-sm animate-fade-in">
      <div className="bg-bg rounded-[var(--radius-card)] shadow-lg w-full max-w-md p-7 relative animate-slide-up">
        <button className="absolute top-5 right-5 text-ink-faint hover:text-ink text-lg" onClick={onClose}>✕</button>

        <div className="flex items-center gap-3 mb-5">
          <span className="text-2xl font-bold text-ink">{wordData?.word}</span>
          <span className={`pill ${issueStyle}`}>{wordData?.detected_issue}</span>
        </div>

        {loading && (
          <div className="flex flex-col items-center gap-3 py-8">
            <div className="w-8 h-8 border-[3px] border-mist border-t-primary rounded-full animate-[spin_0.8s_linear_infinite]" />
            <p className="text-sm text-ink-muted">Getting explanation…</p>
          </div>
        )}

        {error && <p className="text-sm text-danger bg-danger-soft rounded-lg px-4 py-3">{error}</p>}

        {explanation && !loading && (
          <div className="flex flex-col gap-4">
            <div className="card-soft">
              <h4 className="text-[11px] uppercase tracking-widest text-ink-muted font-semibold mb-1.5">What happened</h4>
              <p className="text-sm text-ink leading-relaxed">{explanation.explanation}</p>
            </div>
            <div className="card-soft">
              <h4 className="text-[11px] uppercase tracking-widest text-ink-muted font-semibold mb-1.5">How to fix it</h4>
              <p className="text-sm text-ink leading-relaxed">{explanation.mouth_position_tip}</p>
            </div>
            {explanation.practice_words?.length > 0 && (
              <div className="card-soft">
                <h4 className="text-[11px] uppercase tracking-widest text-ink-muted font-semibold mb-2">Practice these</h4>
                <div className="flex flex-wrap gap-2">
                  {explanation.practice_words.map((w, i) => (
                    <span key={i} className="pill pill-primary font-mono text-xs">{w}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
