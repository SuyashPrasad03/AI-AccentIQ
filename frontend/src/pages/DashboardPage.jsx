import { useEffect, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import { fetchQuota } from "../store/quotaSlice.js";
import { selectIsAuthenticated } from "../store/authSlice.js";
import { AudioUploader } from "../features/upload/AudioUploader.jsx";
import { StatusFooterDot } from "../features/system-status/StatusFooterDot.jsx";
import { PageLoader } from "../components/PageLoader.jsx";

export function DashboardPage() {
  const dispatch = useDispatch();
  const isAuth = useSelector(selectIsAuthenticated);
  const initCalled = useRef(false);

  useEffect(() => {
    if (initCalled.current) return;
    initCalled.current = true;
    dispatch(fetchQuota());
  }, []); // eslint-disable-line

  return (
    <PageLoader>
    <div className="flex-1 flex flex-col">
      <main className="flex-1 w-full max-w-5xl mx-auto px-6 py-8 flex flex-col gap-8">
        <div>
          <h1 className="text-2xl font-bold text-ink">Dashboard</h1>
          <p className="text-ink-muted text-sm mt-1">Upload a recording to analyze your pronunciation</p>
        </div>

        <AudioUploader />
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
                <li>Deepgram (ASR)</li>
                <li>FastAPI (Backend)</li>
                <li>React (Frontend)</li>
                <li>Gemini via OpenRouter</li>
              </ul>
            </div>
          </div>
          <div className="border-t border-border pt-4 flex flex-col sm:flex-row items-center justify-between gap-2">
            <StatusFooterDot />
            <span className="text-[11px] text-ink-faint">© 2026 AccentIQ · v0.10</span>
          </div>
        </div>
      </footer>
    </div>
    </PageLoader>
  );
}
