import { useEffect, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { initAuth, selectAuthLoading } from "./store/authSlice.js";
import { Navbar } from "./components/Navbar.jsx";
import { LandingPage } from "./pages/LandingPage.jsx";
import { DashboardPage } from "./pages/DashboardPage.jsx";
import { AssistantWidget } from "./features/rag-assistant/AssistantWidget.jsx";
import "./App.css";

export default function App() {
  const dispatch = useDispatch();
  const initCalled = useRef(false);

  useEffect(() => {
    if (initCalled.current) return;
    initCalled.current = true;
    dispatch(initAuth());
  }, [dispatch]);

  // Don't block rendering — show the app immediately
  // Auth resolves in background; persisted localStorage is used as instant fallback
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-bg flex flex-col">
        <Navbar />
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/app" element={<DashboardPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <AssistantWidget />
      </div>
    </BrowserRouter>
  );
}
