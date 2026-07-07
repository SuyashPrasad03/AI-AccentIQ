import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { login, selectAuthError, clearError } from "../../store/authSlice.js";

export function LoginModal({ onClose, onSwitchToRegister }) {
  const dispatch = useDispatch();
  const authError = useSelector(selectAuthError);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    dispatch(clearError());
    setSubmitting(true);
    const result = await dispatch(login({ email, password }));
    setSubmitting(false);
    if (login.fulfilled.match(result)) onClose();
  };

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Sign in">
      <div className="modal-box">
        <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        <h2 className="modal-title">Sign in</h2>

        {authError && (
          <div className="form-error" role="alert">{authError}</div>
        )}

        <form onSubmit={handleSubmit} noValidate>
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
          <label className="form-label">
            Password
            <input
              type="password"
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Your password"
              autoComplete="current-password"
              required
            />
          </label>
          <button className="btn btn-primary" type="submit" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="modal-footer-text">
          No account yet?{" "}
          <button className="link-btn" onClick={onSwitchToRegister}>Create one</button>
        </p>
      </div>
    </div>
  );
}
