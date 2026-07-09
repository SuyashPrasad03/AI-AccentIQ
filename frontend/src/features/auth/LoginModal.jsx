import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { login, selectAuthError, clearError } from "../../store/authSlice.js";
import { ForgotPasswordModal } from "./ForgotPasswordModal.jsx";

export function LoginModal({ onClose, onSwitchToRegister }) {
  const dispatch = useDispatch();
  const authError = useSelector(selectAuthError);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [showForgot, setShowForgot] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    dispatch(clearError());
    setSubmitting(true);
    const result = await dispatch(login({ email, password }));
    setSubmitting(false);
    if (login.fulfilled.match(result)) onClose();
  };

  if (showForgot) {
    return <ForgotPasswordModal onClose={onClose} onBack={() => setShowForgot(false)} />;
  }

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-ink/25 backdrop-blur-sm animate-fade-in">
      <div className="bg-bg rounded-[var(--radius-card)] shadow-lg w-full max-w-sm p-7 relative animate-slide-up">
        <button className="absolute top-5 right-5 text-ink-faint hover:text-ink" onClick={onClose}>✕</button>
        <h2 className="font-bold text-xl text-ink mb-1">Welcome back</h2>
        <p className="text-sm text-ink-muted mb-6">Sign in to your account</p>
        {authError && <p className="text-sm text-danger bg-danger-soft rounded-lg px-4 py-2.5 mb-4">{authError}</p>}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-semibold text-ink-muted">Email</span>
            <input type="email" className="px-4 py-3 border border-card-border rounded-[var(--radius-md)] text-sm focus:outline-none focus:border-primary" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required />
          </label>
          <label className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-ink-muted">Password</span>
              <button type="button" className="text-[11px] text-primary hover:underline" onClick={() => setShowForgot(true)}>Forgot password?</button>
            </div>
            <input type="password" className="px-4 py-3 border border-card-border rounded-[var(--radius-md)] text-sm focus:outline-none focus:border-primary" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Your password" required />
          </label>
          <button className="btn-primary w-full mt-2" type="submit" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className="text-xs text-ink-muted text-center mt-5">
          No account? <button className="text-primary font-semibold hover:underline" onClick={onSwitchToRegister}>Create one</button>
        </p>
      </div>
    </div>
  );
}
