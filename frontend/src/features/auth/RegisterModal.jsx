import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { OtpInput } from "./OtpInput.jsx";
import { verifyOtpAndRegister, selectAuthError, clearError } from "../../store/authSlice.js";
import { registerEmail } from "../../api/auth.js";

export function RegisterModal({ onClose, onSwitchToLogin }) {
  const dispatch = useDispatch();
  const authError = useSelector(selectAuthError);
  const [step, setStep] = useState(1);
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

  const handleVerify = async (e) => {
    e.preventDefault();
    setLocalError(""); dispatch(clearError());
    if (otp.replace(/\s/g, "").length < 6) { setLocalError("Enter the full 6-digit code."); return; }
    if (password.length < 8) { setLocalError("Password needs at least 8 characters."); return; }
    if (password !== confirmPassword) { setLocalError("Passwords don't match."); return; }
    setSubmitting(true);
    const result = await dispatch(verifyOtpAndRegister({ email, otp: otp.replace(/\s/g, ""), password }));
    setSubmitting(false);
    if (verifyOtpAndRegister.fulfilled.match(result)) onClose();
  };

  const err = localError || authError;

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-ink/25 backdrop-blur-sm animate-fade-in">
      <div className="bg-bg rounded-[var(--radius-card)] shadow-lg w-full max-w-sm p-7 relative animate-slide-up">
        <button className="absolute top-5 right-5 text-ink-faint hover:text-ink" onClick={onClose}>✕</button>
        <h2 className="font-bold text-xl text-ink mb-1">{step === 1 ? "Create your account" : "Verify your email"}</h2>
        <p className="text-sm text-ink-muted mb-6">
          {step === 1 ? "Enter your email to get started." : <>Code sent to <strong className="text-ink">{email}</strong></>}
        </p>
        {err && <p className="text-sm text-danger bg-danger-soft rounded-lg px-4 py-2.5 mb-4">{err}</p>}

        {step === 1 ? (
          <form onSubmit={handleSendOtp} className="flex flex-col gap-4">
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-semibold text-ink-muted">Email address</span>
              <input type="email" className="px-4 py-3 border border-card-border rounded-[var(--radius-md)] text-sm focus:outline-none focus:border-primary" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required />
            </label>
            <button className="btn-primary w-full" type="submit" disabled={sending}>
              {sending ? "Sending…" : "Send verification code"}
            </button>
          </form>
        ) : (
          <form onSubmit={handleVerify} className="flex flex-col gap-4">
            <div>
              <span className="text-xs font-semibold text-ink-muted block mb-2">Verification code</span>
              <OtpInput value={otp} onChange={setOtp} disabled={submitting} />
            </div>
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
              {submitting ? "Creating…" : "Create account"}
            </button>
            <button type="button" className="btn-ghost text-xs w-full" onClick={() => { setStep(1); setOtp(""); }}>← Change email</button>
          </form>
        )}
        <p className="text-xs text-ink-muted text-center mt-5">
          Already have an account? <button className="text-primary font-semibold hover:underline" onClick={onSwitchToLogin}>Sign in</button>
        </p>
      </div>
    </div>
  );
}
