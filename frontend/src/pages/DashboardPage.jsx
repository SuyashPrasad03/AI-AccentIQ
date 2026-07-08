import { useEffect, useState, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import { fetchQuota } from "../store/quotaSlice.js";
import { selectIsAuthenticated } from "../store/authSlice.js";
import { selectRequiresAuth } from "../store/quotaSlice.js";
import { ConsentBanner } from "../features/auth/ConsentBanner.jsx";
import { getConsentStatus } from "../api/quota.js";
import { RegisterModal } from "../features/auth/RegisterModal.jsx";
import { AudioUploader } from "../features/upload/AudioUploader.jsx";
import { StatusFooterDot } from "../features/system-status/StatusFooterDot.jsx";
import { PageLoader } from "../components/PageLoader.jsx";

export function DashboardPage() {
  const dispatch = useDispatch();
  const isAuth = useSelector(selectIsAuthenticated);
  const requiresAuth = useSelector(selectRequiresAuth);
  const initCalled = useRef(false);

  const [hasConsent, setHasConsent] = useState(false);
  const [consentChecked, setConsentChecked] = useState(false);
  const [showRegister, setShowRegister] = useState(false);

  useEffect(() => {
    if (initCalled.current) return;
    initCalled.current = true;
    getConsentStatus()
      .then((s) => { setHasConsent(s.has_audio_processing_consent && s.has_privacy_policy_consent); setConsentChecked(true); })
      .catch((_e) => setConsentChecked(true));
    dispatch(fetchQuota());
  }, []); // eslint-disable-line

  const prevAuth = useRef(isAuth);
  useEffect(() => {
    if (prevAuth.current !== isAuth) { prevAuth.current = isAuth; dispatch(fetchQuota()); }
  }, [isAuth, dispatch]);

  useEffect(() => {
    if (requiresAuth && !isAuth) setShowRegister(true);
  }, [requiresAuth, isAuth]);

  return (
    <PageLoader>
    <div className="flex-1 flex flex-col">
      <main className="flex-1 w-full max-w-5xl mx-auto px-6 py-8 flex flex-col gap-8">
        {/* Page header */}
        <div>
          <h1 className="text-2xl font-bold text-ink">Dashboard</h1>
          <p className="text-ink-muted text-sm mt-1">Upload a recording to analyze your pronunciation</p>
        </div>

        {consentChecked && !hasConsent && <ConsentBanner onConsented={() => setHasConsent(true)} />}
        {consentChecked && hasConsent && <AudioUploader />}
      </main>

      <footer className="border-t border-border py-8 px-6 mt-auto">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 mb-6">
            <div>
              <h4 className="font-display font-bold text-xs text-ink uppercase tracking-wider mb-2">Product</h4>
              <ul className="space-y-1.5 text-xs text-ink-muted">
                <li>Upload & Analyze</li>
                <li>AI Coaching</li>
                <li>Practice Generator</li>
                <li>Progress Tracking</li>
              </ul>
            </div>
            <div>
              <h4 className="font-display font-bold text-xs text-ink uppercase tracking-wider mb-2">Legal</h4>
              <ul className="space-y-1.5 text-xs text-ink-muted">
                <li>Privacy Policy</li>
                <li>Terms of Service</li>
                <li>DPDP Compliance</li>
              </ul>
            </div>
            <div>
              <h4 className="font-display font-bold text-xs text-ink uppercase tracking-wider mb-2">Support</h4>
              <ul className="space-y-1.5 text-xs text-ink-muted">
                <li>In-App Assistant</li>
                <li>FAQ</li>
                <li>Troubleshooting</li>
              </ul>
            </div>
            <div>
              <h4 className="font-display font-bold text-xs text-ink uppercase tracking-wider mb-2">Built with</h4>
              <ul className="space-y-1.5 text-xs text-ink-muted">
                <li>WhisperX (ASR)</li>
                <li>FastAPI (Backend)</li>
                <li>React (Frontend)</li>
                <li>Gemini via OpenRouter</li>
              </ul>
            </div>
          </div>
          <div className="border-t border-border pt-4 flex flex-col sm:flex-row items-center justify-between gap-2">
            <StatusFooterDot />
            <span className="text-[11px] text-ink-faint">© 2026 Pronunciation Coach · v0.10</span>
          </div>
        </div>
      </footer>

      {showRegister && <RegisterModal onClose={() => setShowRegister(false)} onSwitchToLogin={() => setShowRegister(false)} />}
    </div>
    </PageLoader>
  );
}
