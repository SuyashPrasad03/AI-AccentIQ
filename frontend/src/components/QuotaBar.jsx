import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { fetchQuota, selectQuota } from "../store/quotaSlice.js";
import { selectIsAuthenticated } from "../store/authSlice.js";

/**
 * Displays the anonymous analysis quota as a progress bar.
 * Hidden for authenticated users.
 */
export function QuotaBar() {
  const dispatch = useDispatch();
  const isAuth = useSelector(selectIsAuthenticated);
  const { used, limit, requires_auth, status } = useSelector(selectQuota);

  useEffect(() => {
    if (!isAuth) dispatch(fetchQuota());
  }, [dispatch, isAuth]);

  if (isAuth || status === "idle" || status === "loading") return null;

  const pct = Math.min((used / limit) * 100, 100);
  const colorClass = requires_auth ? "quota-bar-full" : used >= limit - 1 ? "quota-bar-warn" : "quota-bar-ok";

  return (
    <div className="quota-bar-wrapper" aria-label="Free analysis quota">
      <div className="quota-bar-labels">
        <span>Free analyses</span>
        <span>{used} / {limit} used</span>
      </div>
      <div className="quota-bar-track" role="progressbar" aria-valuenow={used} aria-valuemax={limit}>
        <div className={`quota-bar-fill ${colorClass}`} style={{ width: `${pct}%` }} />
      </div>
      {requires_auth && (
        <p className="quota-bar-cta">
          You've used all your free analyses. Sign up to continue.
        </p>
      )}
    </div>
  );
}
