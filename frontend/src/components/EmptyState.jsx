/**
 * EmptyState — reusable illustrated empty/error state.
 */
export function EmptyState({ icon, title, description, action, actionLabel }) {
  return (
    <div className="flex flex-col items-center text-center py-14 animate-fade-in">
      <div className="w-16 h-16 rounded-2xl bg-primary-soft flex items-center justify-center text-2xl mb-5">
        {icon}
      </div>
      <h3 className="font-display font-bold text-ink text-base mb-2">{title}</h3>
      <p className="text-sm text-ink-muted max-w-sm leading-relaxed mb-6">{description}</p>
      {action && (
        <button className="btn-blue text-sm" onClick={action}>{actionLabel || "Try again"}</button>
      )}
    </div>
  );
}

/**
 * ErrorState — for API/processing errors. Always shows what happened + what to do.
 */
export function ErrorState({ message, onRetry }) {
  return (
    <div className="card border-danger/20 bg-danger-soft/30 p-6 text-center animate-fade-in">
      <div className="w-12 h-12 rounded-full bg-danger-soft flex items-center justify-center text-xl mx-auto mb-4">⚠️</div>
      <p className="text-sm text-danger font-medium mb-4">{message}</p>
      {onRetry && (
        <button className="btn-secondary !text-xs" onClick={onRetry}>↻ Try again</button>
      )}
    </div>
  );
}
