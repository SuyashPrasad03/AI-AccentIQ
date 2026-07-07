import { useState, useEffect } from "react";
import { getTodayPractice, regeneratePractice } from "../../api/practice.js";

/**
 * PracticePanel — shows today's personalized practice sentences
 * based on the user's weak phonemes.
 */
export function PracticePanel() {
  const [practice, setPractice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    getTodayPractice()
      .then((data) => { setPractice(data); setLoading(false); })
      .catch((err) => { setError(err.message); setLoading(false); });
  }, []);

  const handleRegenerate = async () => {
    setRegenerating(true);
    setError(null);
    try {
      const data = await regeneratePractice();
      setPractice(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setRegenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="practice-panel practice-loading">
        <span className="boot-spinner" />
        <p>Loading practice set…</p>
      </div>
    );
  }

  if (error) {
    return <div className="practice-panel form-error">{error}</div>;
  }

  if (!practice || practice.weak_phonemes.length === 0) {
    return (
      <div className="practice-panel practice-empty">
        <h3>Your Practice</h3>
        <p>Upload a recording to get personalized practice sentences based on your pronunciation patterns.</p>
      </div>
    );
  }

  return (
    <div className="practice-panel">
      <div className="practice-header">
        <h3>Today&apos;s Practice</h3>
        <button
          className="btn btn-ghost btn-sm"
          onClick={handleRegenerate}
          disabled={regenerating}
        >
          {regenerating ? "Generating…" : "🔄 New sentences"}
        </button>
      </div>

      {/* Weak sound chips */}
      <div className="practice-sounds">
        <span className="practice-sounds-label">Sounds to work on:</span>
        <div className="weak-phoneme-chips">
          {practice.weak_phonemes.map((ph, i) => (
            <span key={i} className="phoneme-chip">{ph}</span>
          ))}
        </div>
      </div>

      {/* Sentence list */}
      <div className="practice-sentences">
        {practice.sentences.map((s, i) => (
          <div key={i} className="practice-sentence-card">
            <div className="practice-sentence-text">{s.text}</div>
            {s.targets && s.targets.length > 0 && (
              <div className="practice-sentence-targets">
                Targets: {s.targets.map((t, j) => (
                  <span key={j} className="target-tag">/{t}/</span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {practice.is_cached && (
        <p className="practice-cached-note">
          Stable for today — click &quot;New sentences&quot; for fresh practice.
        </p>
      )}
    </div>
  );
}
