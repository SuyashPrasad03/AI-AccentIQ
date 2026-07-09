import { useState, useEffect, useRef } from "react";
import { getScore } from "../../api/scoring.js";
import { ScoreCard } from "./ScoreCard.jsx";
import { MetricCards } from "./MetricCards.jsx";
import { HighlightedTranscript } from "./HighlightedTranscript.jsx";
import { ExplainMistakeModal } from "./ExplainMistakeModal.jsx";
import { ScoreRadar, ScoreBar, MistakePie } from "./Charts.jsx";
import { ExportButtons } from "./ExportButtons.jsx";

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
    // Allow clicking any word — correct words get a brief positive note,
    // non-correct words get a full explanation
    setExplainTarget({ wordData, index });
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

  const totalWords = score.word_scores?.length || 0;
  const correctWords = score.word_scores?.filter(w => w.detected_issue === "correct").length || 0;
  const problemWords = totalWords - correctWords;

  return (
    <div className="flex flex-col gap-5" id="results-container">
      {/* Export actions */}
      <div className="flex items-center justify-between">
        <h2 className="font-display font-bold text-lg text-ink">Results</h2>
        <ExportButtons score={score} recordingId={recordingId} />
      </div>

      <ScoreCard overall={score.overall_score} accuracy={score.accuracy_score} fluency={score.fluency_score} />

      {/* AI Summary / Interpretation */}
      <div className="card bg-bg-soft border-border-soft animate-slide-up">
        <h3 className="font-display font-bold text-sm text-ink mb-3 flex items-center gap-2">
          <span>🧠</span> What this means
        </h3>
        <div className="text-sm text-ink-muted leading-relaxed space-y-2">
          <p>
            <strong className="text-ink">Accuracy ({Math.round(score.accuracy_score)}%):</strong>{" "}
            {score.accuracy_score >= 90
              ? "Your pronunciation of individual sounds is excellent — nearly native quality."
              : score.accuracy_score >= 70
              ? "Most sounds are clear and recognizable. A few words could be sharper."
              : "Several sounds weren't recognized correctly. Focus on the highlighted words below."}
          </p>
          <p>
            <strong className="text-ink">Fluency ({Math.round(score.fluency_score)}%):</strong>{" "}
            {score.fluency_score >= 80
              ? "Your speech rhythm and pacing sound natural."
              : score.fluency_score >= 60
              ? "Your pacing has some pauses or hesitations. Try speaking more smoothly."
              : "The rhythm feels choppy — practice reading aloud to build natural flow."}
          </p>
          {totalWords > 0 && (
            <p>
              <strong className="text-ink">Words:</strong>{" "}
              {problemWords === 0
                ? `All ${totalWords} words were pronounced clearly. Great job!`
                : `${correctWords} of ${totalWords} words were clear. ${problemWords} need${problemWords === 1 ? "s" : ""} work — click the highlighted words below for specific tips.`}
            </p>
          )}
        </div>
      </div>

      <MetricCards score={score} />
      <HighlightedTranscript wordScores={score.word_scores} onWordClick={handleWordClick} />

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <ScoreRadar score={score} />
        <MistakePie wordScores={score.word_scores} />
      </div>
      <ScoreBar score={score} />

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

      {/* Guide section — How to read this */}
      <details className="card animate-slide-up">
        <summary className="font-display font-bold text-sm text-ink cursor-pointer flex items-center gap-2">
          <span>❓</span> How to read this report
        </summary>
        <div className="mt-4 text-sm text-ink-muted space-y-3 leading-relaxed">
          <p><strong className="text-ink">Score ring (top):</strong> Your overall pronunciation quality out of 100. Above 80 is great.</p>
          <p><strong className="text-ink">Accuracy:</strong> How correctly you pronounced each individual sound (phoneme). Based on AI speech recognition confidence.</p>
          <p><strong className="text-ink">Fluency:</strong> Your speech rhythm, pacing, and naturalness. Pauses, restarts, or uneven tempo lower this.</p>
          <p><strong className="text-ink">Word colors:</strong></p>
          <ul className="list-none space-y-1 ml-1">
            <li className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-blue-600 shrink-0" /> <strong>Blue</strong> = Correct — the sound was clear and recognized</li>
            <li className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-red-500 shrink-0" /> <strong>Red</strong> = Mispronounced — a different sound was detected than expected</li>
            <li className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-amber-500 shrink-0" /> <strong>Amber</strong> = Unclear — the AI couldn't confidently identify the sound</li>
            <li className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-orange-500 shrink-0" /> <strong>Orange</strong> = Mistimed — the word was too fast, too slow, or had awkward pauses</li>
          </ul>
          <p><strong className="text-ink">Click any word</strong> to get an AI-powered explanation of what happened and tips to improve.</p>
          <p><strong className="text-ink">Tip:</strong> Record a 15-45 second clip of you reading an English paragraph for the best results.</p>
        </div>
      </details>

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
