import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { logout, selectIsAuthenticated, selectUser } from "../store/authSlice.js";
import { LoginModal } from "../features/auth/LoginModal.jsx";
import { RegisterModal } from "../features/auth/RegisterModal.jsx";

export function Navbar() {
  const dispatch = useDispatch();
  const isAuth = useSelector(selectIsAuthenticated);
  const user = useSelector(selectUser);
  const [modal, setModal] = useState(null); // null | "login" | "register"

  const handleLogout = () => dispatch(logout());

  return (
    <>
      <nav className="navbar">
        <span className="navbar-brand">🎤 Pronunciation Coach</span>
        <div className="navbar-actions">
          {isAuth ? (
            <>
              <span className="navbar-user">{user?.email}</span>
              <button className="btn btn-outline" onClick={handleLogout}>Sign out</button>
            </>
          ) : (
            <>
              <button className="btn btn-ghost" onClick={() => setModal("login")}>Sign in</button>
              <button className="btn btn-primary" onClick={() => setModal("register")}>Sign up free</button>
            </>
          )}
        </div>
      </nav>

      {modal === "login" && (
        <LoginModal
          onClose={() => setModal(null)}
          onSwitchToRegister={() => setModal("register")}
        />
      )}
      {modal === "register" && (
        <RegisterModal
          onClose={() => setModal(null)}
          onSwitchToLogin={() => setModal("login")}
        />
      )}
    </>
  );
}
