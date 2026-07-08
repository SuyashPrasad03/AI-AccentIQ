import { useState } from "react";
import { recordConsent } from "../../api/quota.js";

export function ConsentBanner({ onConsented }) {
  const [checked, setChecked] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleAccept = async () => {
    if (!checked) return;
    setSaving(true);
    try {
      await recordConsent("privacy_policy");
      await recordConsent("audio_processing");
      await recordConsent("data_retention");
      onConsented();
    } catch (err) { setError(err.message || "Something went wrong."); }
    finally { setSaving(false); }
  };

  return (
    <div className="card border-primary/20 bg-primary-soft/30 animate-fade-in">
      <h3 className="font-bold text-lg text-ink mb-2">Before we begin</h3>
      <p className="text-sm text-ink-muted leading-relaxed mb-4">
        We process your audio on our servers to analyze pronunciation. It's never shared
        with third parties, and raw recordings are automatically deleted after <strong className="text-ink">30 days</strong>.
      </p>
      <label className="flex items-start gap-3 cursor-pointer mb-4">
        <input type="checkbox" checked={checked} onChange={(e) => setChecked(e.target.checked)}
          className="mt-0.5 w-4 h-4 rounded border-card-border text-primary focus:ring-primary cursor-pointer" />
        <span className="text-sm text-ink-muted">
          I agree to the <a href="/privacy" className="text-primary font-medium hover:underline">Privacy Policy</a> and
          consent to audio processing.
        </span>
      </label>
      {error && <p className="text-xs text-danger mb-3">{error}</p>}
      <button className="btn-primary" onClick={handleAccept} disabled={!checked || saving}>
        {saving ? "Saving…" : "Accept & continue"}
      </button>
    </div>
  );
}
