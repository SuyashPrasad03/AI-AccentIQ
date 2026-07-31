/**
 * StepCard — STEP N label + icon badge + title + description
 * Used in: "How it works" section on landing page
 *
 * @param {number} step - Step number (1, 2, 3, ...)
 * @param {string} icon - Emoji icon for the badge
 * @param {string} title - Step title
 * @param {string} description - Step description text
 */
import { IconBadge } from "./IconBadge.jsx";
import { MicroLabel } from "./MicroLabel.jsx";

export function StepCard({ step, icon, title, description }) {
  return (
    <div className="card flex flex-col items-center text-center gap-3 p-6">
      <MicroLabel text={`Step ${step}`} />
      <IconBadge icon={icon} size="md" />
      <h3 className="font-display font-bold text-ink text-base">{title}</h3>
      <p className="text-sm text-ink-muted leading-relaxed">{description}</p>
    </div>
  );
}
