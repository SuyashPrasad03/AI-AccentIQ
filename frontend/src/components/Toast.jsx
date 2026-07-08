import { useState, createContext, useContext, useCallback } from "react";

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = "info", duration = 4000) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), duration);
  }, []);

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      {/* Toast container */}
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[400] flex flex-col gap-2 pointer-events-none">
        {toasts.map((t) => (
          <div key={t.id} className={`pointer-events-auto px-5 py-3 rounded-[var(--radius-md)] shadow-lg text-sm font-medium animate-slide-up
            ${t.type === "success" ? "bg-success text-white" : ""}
            ${t.type === "error" ? "bg-danger text-white" : ""}
            ${t.type === "info" ? "bg-ink text-white" : ""}
          `}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
