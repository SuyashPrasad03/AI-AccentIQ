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

export function HomePage() {
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
      .catch(() => setConsentChecked(true));
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
    <div className="flex-1 flex flex-col">
      <main className="flex-1 w-full mx-auto px-6 sm:px-10 lg:px-16 py-10 flex flex-col gap-8">

        {consentChecked && !hasConsent && (
          <>
            <section className="text-center py-6 animate-fade-in">
              <span className="pill pill-primary text-[11px] mb-4 inline-block">AI-Powered</span>
              <h1 className="font-bold text-3xl sm:text-4xl text-ink mb-3 leading-tight">
                Improve your English<br />pronunciation
              </h1>
              <p className="text-ink-muted text-base max-w-md mx-auto">
                Upload a recording and get instant, personalized feedback on every sound.
              </p>
            </section>
            <ConsentBanner onConsented={() => setHasConsent(true)} />
          </>
        )}

        {consentChecked && hasConsent && (
          <section className="animate-slide-up">
            <AudioUploader />
          </section>
        )}
      </main>

      <footer className="border-t border-card-border py-4 px-6">
        <div className="w-full flex items-center justify-between">
          <StatusFooterDot />
          <span className="text-[11px] text-ink-faint">AccentIQ</span>
        </div>
      </footer>

      {showRegister && <RegisterModal onClose={() => setShowRegister(false)} onSwitchToLogin={() => setShowRegister(false)} />}
    </div>
  );
}
