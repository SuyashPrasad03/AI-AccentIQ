/**
 * MicroLabel — Small-caps letter-spaced accent-colored label
 * Used in: step cards ("STEP 1"), feature cards ("CORE", "AI"), section headers
 *
 * @param {string} text - Label text (displayed uppercased)
 * @param {string} [color="primary"] - "primary" | "secondary" | "muted"
 */
export function MicroLabel({ text, color = "primary" }) {
  const colors = {
    primary: "text-primary",
    secondary: "text-secondary",
    muted: "text-ink-muted",
  };

  return (
    <span
      className={`text-xs font-display font-semibold uppercase tracking-wider ${colors[color]}`}
    >
      {text}
    </span>
  );
}
