import { useRef } from "react";

export function OtpInput({ value, onChange, disabled }) {
  const refs = useRef([]);
  const digits = value.padEnd(6, " ").split("").slice(0, 6);

  const handleChange = (idx, val) => {
    const digit = val.replace(/\D/g, "").slice(-1);
    const next = [...digits]; next[idx] = digit;
    onChange(next.join("").trimEnd());
    if (digit && idx < 5) refs.current[idx + 1]?.focus();
  };
  const handleKeyDown = (idx, e) => {
    if (e.key === "Backspace" && !digits[idx]?.trim() && idx > 0) refs.current[idx - 1]?.focus();
  };
  const handlePaste = (e) => {
    e.preventDefault();
    onChange(e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6));
  };

  return (
    <div className="flex gap-2.5 justify-center">
      {digits.map((d, i) => (
        <input key={i} ref={(el) => { refs.current[i] = el; }}
          type="text" inputMode="numeric" maxLength={1} value={d.trim()} disabled={disabled}
          className="w-11 h-13 text-center text-lg font-bold border-2 border-card-border rounded-[var(--radius-md)]
                     focus:outline-none focus:border-primary transition-colors
                     disabled:bg-mist disabled:text-ink-faint"
          onChange={(e) => handleChange(i, e.target.value)}
          onKeyDown={(e) => handleKeyDown(i, e)}
          onPaste={handlePaste}
          onFocus={(e) => e.target.select()}
        />
      ))}
    </div>
  );
}
