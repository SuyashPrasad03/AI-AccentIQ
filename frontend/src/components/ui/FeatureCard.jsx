/**
 * FeatureCard — Category pill + icon + title + description
 * Used in: feature grid on landing page, capability sections
 *
 * @param {string} icon - Emoji icon
 * @param {string} label - Category label ("Core" | "AI" | etc.)
 * @param {string} title - Feature title
 * @param {string} description - Feature description
 * @param {string} [labelColor="primary"] - Pill color variant
 */
import { IconBadge } from "./IconBadge.jsx";
import { MicroLabel } from "./MicroLabel.jsx";

export function FeatureCard({ icon, label, title, description, labelColor = "primary" }) {
  return (
    <div className="card card-hover p-5 flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <IconBadge icon={icon} size="sm" color={labelColor === "AI" ? "secondary" : "primary"} />
        <MicroLabel text={label} />
      </div>
      <h3 className="font-display font-bold text-ink text-sm">{title}</h3>
      <p className="text-xs text-ink-muted leading-relaxed">{description}</p>
    </div>
  );
}
