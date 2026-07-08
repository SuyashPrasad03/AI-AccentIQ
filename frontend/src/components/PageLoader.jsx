import { useState, useEffect } from "react";

/**
 * PageLoader — shows a branded loading animation for 1-1.5s before revealing content.
 * Creates the perception of a polished, considered loading experience.
 */
export function PageLoader({ children }) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setReady(true), 1200);
    return () => clearTimeout(timer);
  }, []);

  if (!ready) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center gap-5 animate-fade-in">
        {/* Animated logo mark */}
        <div className="relative">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#7F1D1D] to-[#B91C1C] flex items-center justify-center shadow-md">
            <span className="text-white text-lg font-bold">P</span>
          </div>
          {/* Pulse ring */}
          <div className="absolute inset-0 rounded-2xl border-2 border-primary/30 animate-ping" />
        </div>

        {/* Loading bar */}
        <div className="w-48 h-1 bg-border-soft rounded-full overflow-hidden">
          <div className="h-full bg-gradient-to-r from-[#7F1D1D] to-[#B91C1C] rounded-full animate-[loading_1.2s_ease-in-out]" />
        </div>

        <p className="text-sm text-ink-muted">Loading…</p>
      </div>
    );
  }

  return <div className="animate-fade-in">{children}</div>;
}
