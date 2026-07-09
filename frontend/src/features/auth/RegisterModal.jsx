import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { OtpInput } from "./OtpInput.jsx";
import { verifyOtpAndRegister, selectAuthError, clearError } from "../../store/authSlice.js";
import { registerEmail } from "../../api/auth.js";

export function RegisterModal({ onClose, onSwitchToLogin }) {
  const dispatch = useDispatch();
  const authError = useSelector(selectAuthError);
  const [step, setStep] = useState(1); // 1=email, 2=OTP, 3=password
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [localError, setLocalError] = useState("");
  const [sending, setSending] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSendOtp = async (e) => {
    e.preventDefault();
    setLocalError(""); dispatch(clearError());
    if (!email) { setLocalError("Email is required."); return; }
    setSending(true);
    try { await registerEmail(email); setStep(2); }
    catch (err) { setLocalError(err.message); }
    finally { setSending(false); }
  };

  const handleVerifyOtp = (e) => {
    e.preventDefault();
    setLocalError(""); dispatch(clearError());
    if (otp.replace(/\s/g, "").length < 6) { setLocalError("Enter the full 6-digit code."); return; }
    // OTP looks good — proceed to password step
    setStep(3);
  };

  const handleSetPassword = async (e) => {
    e.preventDefault();
    setLocalError(""); dispatch(clearError());
    if (password.length < 8) { setLocalError("Password needs at least 8 characters."); return; }
    if (password !== confirmPassword) { setLocalError("Passwords don't match."); return; }
    setSubmitting(true);
    const result = await dispatch(verifyOtpAndRegister({ email, otp: otp.replace(/\s/g, ""), password }));
    setSubmitting(false);
    if (verifyOtpAndRegister.fulfilled.match(result)) onClose();
  };

  const err = localError || authError;

  const titles = {
    1: "Create your account",
    2: "Verify your email",
    3: "Set your password",
  };
  const subtitles = {
    1: "Enter your email to get started.",
    2: <>Code sent to <strong className="text-ink">{email}</strong></>,
    3: "Choose a secure password for your account.",
  };

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-ink/25 backdrop-blur-sm animate-fade-in">
      <div className="bg-bg rounded-[var(--radius-card)] shadow-lg w-full max-w-sm p-7 relative animate-slide-up">
        <button className="absolute top-5 right-5 text-ink-faint hover:text-ink" onClick={onClose}>✕</button>
        <h2 className="font-bold text-xl text-ink mb-1">{titles[step]}</h2>
        <p className="text-sm text-ink-muted mb-6">{subtitles[step]}</p>

        {/* Step indicator */}
        <div className="flex items-center gap-2 mb-5">
          {[1, 2, 3].map((s) => (
            <div key={s} className={`flex-1 h-1 rounded-full transition-colors ${s <= step ? "bg-primary" : "bg-border-soft"}`} />
          ))}
        </div>

        {err && <p className="text-sm text-danger bg-danger-soft rounded-lg px-4 py-2.5 mb-4">{err}</p>}

        {step === 1 && (
          <form onSubmit={handleSendOtp} className="flex flex-col gap-4">
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-semibold text-ink-muted">Email address</span>
              <input type="email" className="px-4 py-3 border border-card-border rounded-[var(--radius-md)] text-sm focus:outline-none focus:border-primary" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required />
            </label>
            <button className="btn-primary w-full" type="submit" disabled={sending}>
              {sending ? "Sending…" : "Send verification code"}
            </button>
          </form>
        )}

        {step === 2 && (
          <form onSubmit={handleVerifyOtp} className="flex flex-col gap-4">
            <div>
              <span className="text-xs font-semibold text-ink-muted block mb-2">Verification code</span>
              <OtpInput value={otp} onChange={setOtp} />
            </div>
            <button className="btn-primary w-full" type="submit">
              Verify code
            </button>
            <button type="button" className="btn-ghost text-xs w-full" onClick={() => { setStep(1); setOtp(""); }}>← Change email</button>
          </form>
        )}

        {step === 3 && (
          <form onSubmit={handleSetPassword} className="flex flex-col gap-4">
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-semibold text-ink-muted">Password</span>
              <input type="password" className="px-4 py-3 border border-card-border rounded-[var(--radius-md)] text-sm focus:outline-none focus:border-primary" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="At least 8 characters" required />
              <span className="text-[11px] text-ink-faint">Min 8 characters, must include at least one letter</span>
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-semibold text-ink-muted">Confirm password</span>
              <input type="password" className="px-4 py-3 border border-card-border rounded-[var(--radius-md)] text-sm focus:outline-none focus:border-primary" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="Repeat password" required />
            </label>
            <button className="btn-primary w-full" type="submit" disabled={submitting}>
              {submitting ? "Creating account…" : "Create account"}
            </button>
            <button type="button" className="btn-ghost text-xs w-full" onClick={() => setStep(2)}>← Back to verification</button>
          </form>
        )}

        <p className="text-xs text-ink-muted text-center mt-5">
          Already have an account? <button className="text-primary font-semibold hover:underline" onClick={onSwitchToLogin}>Sign in</button>
        </p>
      </div>
    </div>
  );
}
