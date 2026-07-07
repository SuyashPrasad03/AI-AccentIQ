import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { fetchHealth } from "../api/health.js";
import { fetchQuota } from "../store/quotaSlice.js";
import { selectIsAuthenticated } from "../store/authSlice.js";
import { selectRequiresAuth } from "../store/quotaSlice.js";
import { ConsentBanner } from "../features/auth/ConsentBanner.jsx";
import { QuotaBar } from "../components/QuotaBar.jsx";
import { getConsentStatus } from "../api/quota.js";
import { RegisterModal } from "../features/auth/RegisterModal.jsx";
import { AudioUploader } from "../features/upload/AudioUploader.jsx";

export function HomePage() {
  const dispatch = useDispatch();
  const isAuth = useSelector(selectIsAuthenticated);
  const requiresAuth = useSelector(selectRequiresAuth);

  const [health, setHealth] = useState(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [healthError, setHealthError] = useState("");

  // Consent state
  const [hasConsent, setHasConsent] = useState(false);
  const [consentChecked, setConsentChecked] = useState(false);

  // Registration prompt
  const [showRegister, setShowRegister] = useState(false);

  // Load health on mount
  useEffect(() => {
    fetchHealth()
      .then((d) => { setHealth(d); setHealthLoading(false); })
      .catch((err) => { setHealthError(err.message); setHealthLoading(false); });
  }, []);

  // Check existing consent on mount
  useEffect(() => {
    getConsentStatus()
      .then((s) => {
        setHasConsent(s.has_audio_processing_consent && s.has_privacy_policy_consent);
        setConsentChecked(true);
      })
      .catch(() => setConsentChecked(true));
  }, []);

  // Refresh quota after auth state changes
  useEffect(() => {
    dispatch(fetchQuota());
  }, [dispatch, isAuth]);

  // Show register modal when quota is exhausted for anon user
  useEffect(() => {
    if (requiresAuth && !isAuth) setShowRegister(true);
  }, [requiresAuth, isAuth]);

  return (
    <div className="page-container">
      {/* Health status */}
      <section className="health-card" aria-label="Service health">
        {healthLoading && <p className="loading-text">Checking services…</p>}
        {healthError && (
          <div className="error-banner" role="alert">
            <strong>Backend unreachable.</strong>
            <p>{healthError}</p>
          </div>
        )}
        {health && (
          <>
            <div className={`overall-status ${health.status === "ok" ? "overall-ok" : "overall-degraded"}`}>
              {health.status === "ok" ? "✅ All Systems Operational" : "⚠️ Degraded"}
            </div>
            <div className="status-list">
              <StatusRow label="Backend" connected />
              <StatusRow label="MySQL" connected={health.mysql === "connected"} />
              <StatusRow label="MongoDB" connected={health.mongo === "connected"} />
            </div>
          </>
        )}
      </section>

      {/* Quota bar */}
      <QuotaBar />

      {/* Consent → then Upload */}
      {consentChecked && !hasConsent && !isAuth && (
        <ConsentBanner onConsented={() => setHasConsent(true)} />
      )}

      {consentChecked && (hasConsent || isAuth) && (
        <AudioUploader />
      )}

      {showRegister && (
        <RegisterModal
          onClose={() => setShowRegister(false)}
          onSwitchToLogin={() => setShowRegister(false)}
        />
      )}

      <footer className="app-footer">
        <small>Phase 3 — Audio Upload &amp; Preprocessing</small>
      </footer>
    </div>
  );
}

function StatusRow({ label, connected }) {
  return (
    <div className="status-row">
      <span className="status-label">{label}</span>
      <span className={`status-badge ${connected ? "badge-ok" : "badge-error"}`}>
        {connected ? "✓ Connected" : "✗ Disconnected"}
      </span>
    </div>
  );
}
