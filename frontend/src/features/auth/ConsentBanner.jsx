import { useState } from "react";
import { recordConsent } from "../../api/quota.js";

/**
 * DPDP consent capture.
 *
 * Must be accepted before the "Analyze" button is enabled.
 * On confirmation, records three consent events server-side:
 *   audio_processing, data_retention, privacy_policy
 *
 * Props:
 *   onConsented – called after all three events are persisted
 */
export function ConsentBanner({ onConsented }) {
  const [checked, setChecked] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleAccept = async () => {
    if (!checked) return;
    setSaving(true);
    setError("");
    try {
      // Record all three consent types in sequence
      await recordConsent("privacy_policy");
      await recordConsent("audio_processing");
      await recordConsent("data_retention");
      onConsented();
    } catch (err) {
      setError(err.message || "Could not save consent. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="consent-banner" role="region" aria-label="Privacy consent">
      <h3 className="consent-title">Before you continue</h3>
      <p className="consent-body">
        To analyse your pronunciation, we need to process your audio recording.
        Your audio is processed on our servers and is never shared with third parties.
        Raw recordings are automatically deleted after{" "}
        <strong>30 days</strong> in accordance with our{" "}
        <a href="/privacy" className="consent-link" target="_blank" rel="noreferrer">
          Privacy Policy
        </a>
        .
      </p>

      <label className="consent-check-label">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => setChecked(e.target.checked)}
          aria-label="I accept the privacy policy and consent to audio processing"
        />
        <span>
          I have read and agree to the{" "}
          <a href="/privacy" className="consent-link" target="_blank" rel="noreferrer">
            Privacy Policy
          </a>{" "}
          and consent to my audio being processed for pronunciation analysis.
        </span>
      </label>

      {error && <p className="form-error" role="alert">{error}</p>}

      <button
        className="btn btn-primary"
        onClick={handleAccept}
        disabled={!checked || saving}
        aria-disabled={!checked || saving}
      >
        {saving ? "Saving…" : "Accept and continue"}
      </button>
    </div>
  );
}
