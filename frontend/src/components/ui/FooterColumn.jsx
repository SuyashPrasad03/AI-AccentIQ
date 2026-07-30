/**
 * FooterColumn — Reusable footer link column
 * Used in: dashboard footer, landing page footer
 *
 * @param {string} title - Column heading
 * @param {string[]} items - List of link/text items
 */
export function FooterColumn({ title, items = [] }) {
  return (
    <div>
      <h4 className="font-display font-bold text-xs text-ink uppercase tracking-wider mb-2">
        {title}
      </h4>
      <ul className="space-y-1.5 text-xs text-ink-muted">
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
