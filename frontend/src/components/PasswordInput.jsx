import { useState } from "react";

export function PasswordInput({ value, onChange, placeholder = "Password", disabled = false, className = "" }) {
  const [show, setShow] = useState(false);

  return (
    <div className="relative">
      <input
        type={show ? "text" : "password"}
        className={`px-4 py-3 pr-12 border border-card-border rounded-[var(--radius-md)] text-sm focus:outline-none focus:border-primary w-full ${className}`}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        disabled={disabled}
        required
      />
      <button
        type="button"
        className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-faint hover:text-ink text-xs select-none"
        onClick={() => setShow(!show)}
        tabIndex={-1}
      >
        {show ? "Hide" : "Show"}
      </button>
    </div>
  );
}
