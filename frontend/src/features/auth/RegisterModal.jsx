import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { OtpInput } from "./OtpInput.jsx";
import { verifyOtpAndRegister, selectAuthError, clearError } from "../../store/authSlice.js";
import { registerEmail } from "../../api/auth.js";

/**
 * Two-step registration modal:
 *   Step 1 — enter email → sends OTP
 *   Step 2 — enter 6-digit OTP + new password → creates account + logs in
 */
export function RegisterModal({ onClose, onSwitchToLogin }) {
  const dispatch = useDispatch();
  const authError = useSelector(selectAuthError);

  const [step, setStep] = useState(1);        // 1 = email, 2 = otp+password
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [localError, setLocalError] = useState("");
  const [sending, setSending] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSendOtp = async (e) => {
    e.preventDefault();
    setLocalError("");
    dispatch(clearError());
    if (!email) { setLocalError("Email is required."); return; }
    setSending(true);
    try {
      await registerEmail(email);
      setStep(2);
    } catch (err) {
      setLocalError(err.message);
    } finally {
      setSending(false);
    }
  };

  const handleVerify = async (e) => {
    e.preventDefault();
    setLocalError("");
    dispatch(clearError());
    if (otp.replace(/\s/g, "").length < 6) { setLocalError("Please enter the full 6-digit code."); return; }
    if (password.length < 8) { setLocalError("Password must be at least 8 characters."); return; }
    if (password !== confirmPassword) { setLocalError("Passwords do not match."); return; }
    setSubmitting(true);
    const result = await dispatch(verifyOtpAndRegister({ email, otp: otp.replace(/\s/g, ""), password }));
    setSubmitting(false);
    if (verifyOtpAndRegister.fulfilled.match(result)) {
      onClose();
    }
  };

  const displayError = localError || authError;

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Create account">
      <div className="modal-box">
        <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>

        <h2 className="modal-title">
          {step === 1 ? "Create your account" : "Verify your email"}
        </h2>

        {step === 1 && (
          <p className="modal-subtitle">
            Enter your email and we'll send a verification code.
          </p>
        )}
        {step === 2 && (
          <p className="modal-subtitle">
            We sent a 6-digit code to <strong>{email}</strong>.
          </p>
        )}

        {displayError && (
          <div className="form-error" role="alert">{displayError}</div>
        )}

        {step === 1 ? (
          <form onSubmit={handleSendOtp} noValidate>
            <label className="form-label">
              Email address
              <input
                type="email"
                className="form-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
                required
              />
            </label>
            <button className="btn btn-primary" type="submit" disabled={sending}>
              {sending ? "Sending code…" : "Send verification code"}
            </button>
          </form>
        ) : (
          <form onSubmit={handleVerify} noValidate>
            <div className="form-group">
              <label className="form-label">Verification code</label>
              <OtpInput value={otp} onChange={setOtp} disabled={submitting} />
            </div>
            <label className="form-label">
              New password
              <input
                type="password"
                className="form-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters"
                autoComplete="new-password"
                minLength={8}
                required
              />
            </label>
            <label className="form-label">
              Confirm password
              <input
                type="password"
                className="form-input"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Repeat your password"
                autoComplete="new-password"
                required
              />
            </label>
            <button className="btn btn-primary" type="submit" disabled={submitting}>
              {submitting ? "Creating account…" : "Create account"}
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => { setStep(1); setOtp(""); setPassword(""); setConfirmPassword(""); }}
            >
              ← Change email
            </button>
          </form>
        )}

        <p className="modal-footer-text">
          Already have an account?{" "}
          <button className="link-btn" onClick={onSwitchToLogin}>Sign in</button>
        </p>
      </div>
    </div>
  );
}
