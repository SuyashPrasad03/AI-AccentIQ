import { useState } from "react";
import { useDispatch } from "react-redux";
import { OtpInput } from "./OtpInput.jsx";
import { PasswordInput } from "../../components/PasswordInput.jsx";
import { forgotPassword, resetPassword } from "../../api/auth.js";
import { setAccessToken } from "../../store/authSlice.js";

export function ForgotPasswordModal({ onClose, onBack }) {
  const dispatch = useDispatch();
  const [step, setStep] = useState(1); // 1=email, 2=OTP+new password
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSendReset = async (e) => {
    e.preventDefault();
    setError("");
    if (!email) { setError("Email is required."); return; }
    setSending(true);
    try {
      await forgotPassword(email);
      setStep(2);
    } catch (err) { setError(err.message); }
    finally { setSending(false); }
  };

  const handleReset = async (e) => {
    e.preventDefault();
    setError("");
    if (otp.replace(/\s/g, "").length < 6) { setError("Enter the full 6-digit code."); return; }
    if (password.length < 8) { setError("Password needs at least 8 characters."); return; }
    if (password !== confirmPassword) { setError("Passwords don't match."); return; }
    setSubmitting(true);
    try {
      const data = await resetPassword(email, otp.replace(/\s/g, ""), password);
      // Auto-login after successful reset
      dispatch(setAccessToken(data.access_token));
      // Persist auth
      localStorage.setItem("accentiq_auth", JSON.stringify({ user: data.user, accessToken: data.access_token }));
      onClose();
    } catch (err) { setError(err.message); }
    finally { setSubmitting(false); }
  };

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-ink/25 backdrop-blur-sm animate-fade-in">
      <div className="bg-bg rounded-[var(--radius-card)] shadow-lg w-full max-w-sm p-7 relative animate-slide-up">
        <button className="absolute top-5 right-5 text-ink-faint hover:text-ink" onClick={onClose}>✕</button>
        <h2 className="font-bold text-xl text-ink mb-1">{step === 1 ? "Reset password" : "Set new password"}</h2>
        <p className="text-sm text-ink-muted mb-6">
          {step === 1
            ? "Enter your email and we'll send a reset code."
            : <>Code sent to <strong className="text-ink">{email}</strong></>}
        </p>

        {error && <p className="text-sm text-danger bg-danger-soft rounded-lg px-4 py-2.5 mb-4">{error}</p>}

        {step === 1 ? (
          <form onSubmit={handleSendReset} className="flex flex-col gap-4">
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-semibold text-ink-muted">Email address</span>
              <input type="email" className="px-4 py-3 border border-card-border rounded-[var(--radius-md)] text-sm focus:outline-none focus:border-primary" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required />
            </label>
            <button className="btn-primary w-full" type="submit" disabled={sending}>
              {sending ? "Sending…" : "Send reset code"}
            </button>
            <button type="button" className="btn-ghost text-xs w-full" onClick={onBack}>← Back to sign in</button>
          </form>
        ) : (
          <form onSubmit={handleReset} className="flex flex-col gap-4">
            <div>
              <span className="text-xs font-semibold text-ink-muted block mb-2">Reset code</span>
              <OtpInput value={otp} onChange={setOtp} disabled={submitting} />
            </div>
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-semibold text-ink-muted">New password</span>
              <PasswordInput value={password} onChange={(e) => setPassword(e.target.value)} placeholder="At least 8 characters" />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-semibold text-ink-muted">Confirm new password</span>
              <PasswordInput value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="Repeat password" />
            </label>
            <button className="btn-primary w-full" type="submit" disabled={submitting}>
              {submitting ? "Resetting…" : "Reset password"}
            </button>
            <button type="button" className="btn-ghost text-xs w-full" onClick={() => { setStep(1); setOtp(""); }}>← Change email</button>
          </form>
        )}
      </div>
    </div>
  );
}
