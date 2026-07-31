/**
 * PrimaryButton — Full-width maroon gradient button
 * Used in: auth modals, upload CTA, form submissions
 *
 * @param {React.ReactNode} children - Button content
 * @param {boolean} [disabled] - Disabled state
 * @param {boolean} [loading] - Loading state (shows spinner)
 * @param {boolean} [fullWidth] - Whether button takes full width
 * @param {string} [type="button"] - Button type attribute
 * @param {function} [onClick] - Click handler
 */
export function PrimaryButton({
  children,
  disabled = false,
  loading = false,
  fullWidth = true,
  type = "button",
  onClick,
  ...props
}) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      onClick={onClick}
      className={`btn-primary ${fullWidth ? "w-full" : ""}`}
      {...props}
    >
      {loading && (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {children}
    </button>
  );
}
