import { useNavigate } from "react-router-dom";
import { useSelector } from "react-redux";
import { selectIsAuthenticated } from "../store/authSlice.js";
import { PageLoader } from "../components/PageLoader.jsx";

export function LandingPage() {
  const navigate = useNavigate();
  const isAuth = useSelector(selectIsAuthenticated);

  return (
    <PageLoader>
    <div className="flex-1">
      {/* ── Hero ───────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary-soft via-bg to-secondary-soft opacity-50" />
        <div className="absolute top-10 right-[10%] w-80 h-80 bg-primary/5 rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-[5%] w-96 h-96 bg-secondary/5 rounded-full blur-3xl" />

        <div className="relative max-w-6xl mx-auto px-6 pt-20 pb-24 sm:pt-28 sm:pb-32">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-pill bg-primary-soft border border-border text-primary text-xs font-semibold mb-6">
              <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
              AI-Powered Speech Analysis
            </div>

            <h1 className="font-display text-4xl sm:text-5xl lg:text-[3.5rem] font-bold text-ink leading-[1.15] mb-5">
              AI Pronunciation{" "}
              <span className="bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">Evaluator</span>
            </h1>

            <p className="text-lg text-ink-muted max-w-xl leading-relaxed mb-8">
              Improve your English pronunciation with AI-powered analysis, detailed phoneme-level feedback,
              and actionable suggestions to speak clearly and confidently.
            </p>

            <div className="flex flex-col sm:flex-row items-start gap-3">
              <button className="btn-primary text-base px-7 py-3.5" onClick={() => navigate("/app")}>
                Analyze My Speech
              </button>
              {!isAuth && (
                <button className="btn-secondary px-6 py-3" onClick={() => navigate("/app")}>
                  3 free analyses — no signup
                </button>
              )}
            </div>
          </div>

          {/* Hero illustration — SVG mic + waveform + brain */}
          <div className="hidden lg:block absolute top-20 right-8 w-[340px] h-[340px]" aria-hidden="true">
            <svg viewBox="0 0 340 340" fill="none" className="w-full h-full opacity-80">
              {/* Waveform bars */}
              {[0,1,2,3,4,5,6,7,8,9,10,11].map((i) => (
                <rect key={i} x={80 + i * 16} y={140 - Math.sin(i * 0.8) * 40}
                  width="6" height={40 + Math.sin(i * 0.8) * 40} rx="3"
                  fill={i % 3 === 0 ? "#8B5CF6" : "#3B82F6"} opacity={0.15 + (i % 4) * 0.15}
                  style={{ animation: `breathe ${2 + i * 0.2}s ease-in-out ${i * 0.1}s infinite` }} />
              ))}
              {/* Mic circle */}
              <circle cx="170" cy="240" r="50" fill="#3B82F6" opacity="0.08" />
              <path d="M170 210 a12 12 0 0 0-12 12v20a12 12 0 0 0 24 0v-20a12 12 0 0 0-12-12z" stroke="#3B82F6" strokeWidth="2.5" fill="none" />
              <path d="M152 238v4a18 18 0 0 0 36 0v-4" stroke="#3B82F6" strokeWidth="2.5" fill="none" strokeLinecap="round" />
              <line x1="170" y1="260" x2="170" y2="270" stroke="#3B82F6" strokeWidth="2.5" strokeLinecap="round" />
              {/* Brain/AI circle (purple) */}
              <circle cx="260" cy="100" r="32" fill="#8B5CF6" opacity="0.08" />
              <path d="M248 100c0-6 4-11 9-12 1-5 5-8 10-8 4 0 7 2 9 5 3-2 6-2 9 0 3 2 4 6 3 9 3 2 5 6 4 10-1 4-4 7-8 8" stroke="#8B5CF6" strokeWidth="2" fill="none" strokeLinecap="round" />
            </svg>
          </div>
        </div>
      </section>

      {/* ── How It Works ───────────────────────────────────── */}
      <section className="py-20 bg-bg-soft">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-14">
            <h2 className="font-display text-3xl font-bold text-ink mb-3">How it works</h2>
            <p className="text-ink-muted">Four steps to better pronunciation</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {[
              { step: 1, icon: "⬆️", title: "Upload Audio", desc: "Upload a 30–45 second English recording or record directly.", color: "primary" },
              { step: 2, icon: "🔊", title: "Speech Recognition", desc: "WhisperX transcribes with word-level timestamps.", color: "primary" },
              { step: 3, icon: "🧠", title: "AI Analysis", desc: "Phoneme comparison identifies which sounds need work.", color: "secondary" },
              { step: 4, icon: "📊", title: "Detailed Report", desc: "Get your score, highlighted mistakes, and coaching tips.", color: "primary" },
            ].map((s) => (
              <div key={s.step} className="card card-hover text-center p-7">
                <div className={`w-12 h-12 rounded-xl mx-auto mb-4 flex items-center justify-center text-xl
                  ${s.color === "secondary" ? "bg-secondary-soft" : "bg-primary-soft"}`}>
                  {s.icon}
                </div>
                <div className={`text-[10px] font-bold uppercase tracking-widest mb-2
                  ${s.color === "secondary" ? "text-secondary" : "text-primary"}`}>
                  Step {s.step}
                </div>
                <h3 className="font-display font-bold text-ink text-sm mb-1.5">{s.title}</h3>
                <p className="text-xs text-ink-muted leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ───────────────────────────────────────── */}
      <section className="py-20">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-14">
            <h2 className="font-display text-3xl font-bold text-ink mb-3">Built for serious learners</h2>
            <p className="text-ink-muted">Everything you need to improve, nothing you don't</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[
              { icon: "🎯", title: "Phoneme Scoring", desc: "Every word scored 0-100 on confidence, timing, and phoneme accuracy.", pill: "blue" },
              { icon: "💡", title: "AI Explanations", desc: "Click any word for a coach-like explanation powered by Gemini.", pill: "purple" },
              { icon: "📈", title: "Progress Tracking", desc: "Compare recordings side-by-side. See your improvement over time.", pill: "blue" },
              { icon: "🗣️", title: "Practice Generator", desc: "AI generates sentences targeting your specific weak sounds.", pill: "purple" },
              { icon: "🔒", title: "Privacy First", desc: "Audio auto-deleted after 30 days. DPDP Act compliant. Never shared.", pill: "blue" },
              { icon: "🤖", title: "In-App Assistant", desc: "Ask questions about scores, features, or how to improve.", pill: "purple" },
            ].map((f, i) => (
              <div key={i} className="card card-hover p-6">
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-xl">{f.icon}</span>
                  <span className={`pill ${f.pill === "purple" ? "pill-purple" : "pill-blue"} text-[10px]`}>
                    {f.pill === "purple" ? "AI" : "Core"}
                  </span>
                </div>
                <h3 className="font-display font-bold text-ink text-sm mb-1.5">{f.title}</h3>
                <p className="text-xs text-ink-muted leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ────────────────────────────────────────────── */}
      <section className="py-20 bg-bg-soft">
        <div className="max-w-xl mx-auto px-6 text-center">
          <h2 className="font-display text-2xl font-bold text-ink mb-3">Ready to improve?</h2>
          <p className="text-ink-muted text-sm mb-8">3 free analyses without signing up. No credit card needed.</p>
          <button className="btn-primary text-base px-8 py-3.5" onClick={() => navigate("/app")}>
            Start Speaking →
          </button>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────────── */}
      <footer className="border-t border-border py-10 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-8 mb-8">
            <div>
              <h4 className="font-display font-bold text-xs text-ink uppercase tracking-wider mb-3">Product</h4>
              <ul className="space-y-2 text-sm text-ink-muted">
                <li><button onClick={() => navigate("/app")} className="hover:text-primary transition-colors">Dashboard</button></li>
                <li><span>Pricing (Free)</span></li>
              </ul>
            </div>
            <div>
              <h4 className="font-display font-bold text-xs text-ink uppercase tracking-wider mb-3">Legal</h4>
              <ul className="space-y-2 text-sm text-ink-muted">
                <li><span>Privacy Policy</span></li>
                <li><span>Terms of Service</span></li>
                <li><span>DPDP Compliance</span></li>
              </ul>
            </div>
            <div>
              <h4 className="font-display font-bold text-xs text-ink uppercase tracking-wider mb-3">Support</h4>
              <ul className="space-y-2 text-sm text-ink-muted">
                <li><span>In-App Assistant</span></li>
                <li><span>FAQ</span></li>
              </ul>
            </div>
            <div>
              <h4 className="font-display font-bold text-xs text-ink uppercase tracking-wider mb-3">Built with</h4>
              <ul className="space-y-2 text-sm text-ink-muted">
                <li>WhisperX (ASR)</li>
                <li>FastAPI (Backend)</li>
                <li>React (Frontend)</li>
                <li>Gemini via OpenRouter</li>
                <li>MySQL + MongoDB</li>
              </ul>
            </div>
          </div>
          <div className="border-t border-border pt-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-ink-faint">
            <span>© 2026 Pronunciation Coach · v0.10 · Privacy-first AI</span>
            <span>Made with care for language learners</span>
          </div>
        </div>
      </footer>
    </div>
    </PageLoader>
  );
}
