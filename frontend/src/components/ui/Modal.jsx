/**
 * Modal — Shared modal shell with backdrop
 * Used in: sign-in, sign-up, any future modals
 *
 * @param {boolean} isOpen - Whether modal is visible
 * @param {function} onClose - Close handler (backdrop click + escape key)
 * @param {string} [title] - Optional modal title
 * @param {React.ReactNode} children - Modal content
 * @param {string} [maxWidth="md"] - "sm" | "md" | "lg"
 */
import { useEffect } from "react";

export function Modal({ isOpen, onClose, title, children, maxWidth = "md" }) {
  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [isOpen, onClose]);

  // Prevent body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [isOpen]);

  if (!isOpen) return null;

  const widths = {
    sm: "max-w-sm",
    md: "max-w-md",
    lg: "max-w-lg",
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? "modal-title" : undefined}
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal content */}
      <div
        className={`relative bg-bg rounded-xl shadow-lg p-6 w-full ${widths[maxWidth]} animate-scale-in`}
        style={{ boxShadow: "var(--shadow-lg)" }}
      >
        {title && (
          <h2 id="modal-title" className="font-display font-bold text-lg text-ink mb-4">
            {title}
          </h2>
        )}
        {children}
      </div>
    </div>
  );
}
