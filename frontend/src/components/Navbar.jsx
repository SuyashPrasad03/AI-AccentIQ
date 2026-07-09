import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate, useLocation } from "react-router-dom";
import { logout, selectIsAuthenticated, selectUser } from "../store/authSlice.js";
import { selectQuota } from "../store/quotaSlice.js";
import { LoginModal } from "../features/auth/LoginModal.jsx";
import { RegisterModal } from "../features/auth/RegisterModal.jsx";

export function Navbar() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const isAuth = useSelector(selectIsAuthenticated);
  const user = useSelector(selectUser);
  const quota = useSelector(selectQuota);
  const [modal, setModal] = useState(null);

  const isLanding = location.pathname === "/";

  return (
    <>
      <nav className="sticky top-0 z-50 bg-glass backdrop-blur-xl border-b border-border/50">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <button onClick={() => navigate("/")} className="flex items-center gap-2.5 hover:opacity-80 transition-opacity">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#7F1D1D] to-[#B91C1C] flex items-center justify-center">
              <span className="text-white text-xs font-bold">P</span>
            </div>
            <span className="font-display font-bold text-ink text-sm tracking-tight hidden sm:inline">
              AccentIQ
            </span>
          </button>

          <div className="flex items-center gap-2.5">
            {/* Quota pill on dashboard — hide for unlimited (registered) quota */}
            {!isAuth && !isLanding && (quota.status === "succeeded" || quota.status === "idle") && quota.limit < 1000 && (
              <span className="pill pill-muted text-[10px]">{quota.remaining}/{quota.limit} free</span>
            )}

            {/* Dashboard link on landing */}
            {isLanding && (
              <button className="btn-ghost text-xs" onClick={() => navigate("/app")}>Dashboard</button>
            )}

            {isAuth ? (
              <>
                <span className="text-xs text-ink-muted hidden md:inline truncate max-w-[140px]">{user?.email}</span>
                <button className="btn-ghost text-xs" onClick={() => dispatch(logout())}>Sign out</button>
              </>
            ) : (
              <>
                <button className="btn-ghost text-xs" onClick={() => setModal("login")}>Sign in</button>
                <button className="btn-blue !text-xs !px-4 !py-1.5 !rounded-md" onClick={() => setModal("register")}>Get started</button>
              </>
            )}
          </div>
        </div>
      </nav>
      {modal === "login" && <LoginModal onClose={() => setModal(null)} onSwitchToRegister={() => setModal("register")} />}
      {modal === "register" && <RegisterModal onClose={() => setModal(null)} onSwitchToLogin={() => setModal("login")} />}
    </>
  );
}
