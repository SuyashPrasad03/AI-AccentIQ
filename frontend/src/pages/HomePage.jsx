import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { fetchHealth } from "../api/health.js";
import { fetchQuota } from "../store/quotaSlice.js";
import { selectIsAuthenticated } from "../store/authSlice.js";
import { selectQuota, selectRequiresAuth } from "../store/quotaSlice.js";
import { ConsentBanner } from "../features/auth/ConsentBanner.jsx";
import { QuotaBar } from "../components/QuotaBar.jsx";
import { getConsentStatus, incrementQuotaStub } from "../api/quota.js";
import { RegisterModal } from "../features/auth/RegisterModal.jsx";

export function HomePage() {
  const dispatch = useDispatch();
  const isAuth = useSelector(selectIsAuthenticated);
  const quota = useSelector(selectQuota);
  const requiresAuth = useSelector(selectRequiresAuth);

  const [health, setHealth] = useState(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [healthError, setHealthError] = useState("");

  // Consent state
  const [hasConsent, setHasConsent] = useState(false);
  const [consentChecked, setConsentChecked] = useState(false);

  // Demo "analyze" state
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeMsg, setAnalyzeMsg] = useState("");
  const [showRegister, setShowRegister] = useState(false);

  // Load health on mount
  useEffect(() => {
    fetchHealth()
      .then((d) => { setHealth(d); setHealthLoading(false); })
      .catch((err) => { setHealthError(err.message); setHealthLoading(false); });
  }, []);

  // Check existing consent on mount (cookie-identified anon session)
  useEffect(() => {
    getConsentStatus()
      .then((s) => {
        setHasConsent(s.has_audio_processing_consent && s.has_privacy_policy_consent);
        setConsentChecked(true);
      })
      .catch(() => setConsentChecked(true)); // if it fails, show banner anyway
  }, []);

  // Refresh quota after auth state changes
  useEffect(() => {
    dispatch(fetchQuota());
  }, [dispatch, isAuth]);

  const handleAnalyzeDemo = async () => {
    if (requiresAuth && !isAuth) {
      setShowRegister(true);
      return;
    }
    setAnalyzing(true);
    setAnalyzeMsg("");
    try {
      const result = await incrementQuotaStub();
      dispatch(fetchQuota()); // refresh bar
      setAnalyzeMsg(
        `✅ Analysis counted — you have used ${result.used} / ${result.limit} free analyses.`
      );
    } catch (err) {
      if (err.status === 402) {
        setShowRegister(true);
      } else {
        setAnalyzeMsg(`❌ ${err.message}`);
      }
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="page-container">
      {/* ── Health status ─────────────────────────────────── */}
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

      {/* ── Quota bar ─────────────────────────────────────── */}
      <QuotaBar />

      {/* ── Consent or Analyze ────────────────────────────── */}
      {consentChecked && !hasConsent && !isAuth && (
        <ConsentBanner onConsented={() => setHasConsent(true)} />
      )}

      {consentChecked && (hasConsent || isAuth) && (
        <section className="demo-section">
          <h2>Try an analysis</h2>
          <p className="demo-desc">
            {isAuth
              ? "You're signed in — unlimited analyses available."
              : `${quota.remaining} free ${quota.remaining === 1 ? "analysis" : "analyses"} remaining.`}
          </p>
          <button
            className="btn btn-primary btn-large"
            onClick={handleAnalyzeDemo}
            disabled={analyzing}
          >
            {analyzing ? "Analysing…" : "🎤 Analyse (demo)"}
          </button>
          {analyzeMsg && <p className="demo-result">{analyzeMsg}</p>}
        </section>
      )}

      {showRegister && (
        <RegisterModal
          onClose={() => setShowRegister(false)}
          onSwitchToLogin={() => setShowRegister(false)}
        />
      )}

      <footer className="app-footer">
        <small>Phase 2 — Auth, Quota &amp; Consent</small>
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
