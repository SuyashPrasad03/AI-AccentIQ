/**
 * IconBadge — Circular pastel-tint icon badge
 * Used in: step cards, feature cards, section headers
 *
 * @param {string} icon - Emoji or text icon
 * @param {string} [size="md"] - "sm" | "md" | "lg"
 * @param {string} [color="primary"] - "primary" | "secondary" | "muted"
 */
export function IconBadge({ icon, size = "md", color = "primary" }) {
  const sizes = {
    sm: "w-8 h-8 text-sm",
    md: "w-12 h-12 text-xl",
    lg: "w-16 h-16 text-2xl",
  };

  const colors = {
    primary: "bg-primary-soft text-primary",
    secondary: "bg-secondary-soft text-secondary",
    muted: "bg-bg-soft text-ink-muted",
  };

  return (
    <div
      className={`inline-flex items-center justify-center rounded-full ${sizes[size]} ${colors[color]}`}
      role="img"
      aria-hidden="true"
    >
      {icon}
    </div>
  );
}
