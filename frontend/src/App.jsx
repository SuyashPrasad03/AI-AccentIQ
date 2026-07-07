import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { initAuth, selectAuthLoading } from "./store/authSlice.js";
import { Navbar } from "./components/Navbar.jsx";
import { HomePage } from "./pages/HomePage.jsx";
import { AssistantWidget } from "./features/rag-assistant/AssistantWidget.jsx";
import "./App.css";

export default function App() {
  const dispatch = useDispatch();
  const isLoading = useSelector(selectAuthLoading);

  // Attempt silent refresh on every cold load.
  // If the httpOnly refresh-token cookie exists the server rotates it and
  // returns a fresh access token; otherwise we stay anonymous.
  useEffect(() => {
    dispatch(initAuth());
  }, [dispatch]);

  if (isLoading) {
    return (
      <div className="boot-loading" aria-label="Loading application">
        <span className="boot-spinner" aria-hidden="true" />
        <p>Loading…</p>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/" element={<HomePage />} />
      </Routes>
      <AssistantWidget />
    </BrowserRouter>
  );
}
