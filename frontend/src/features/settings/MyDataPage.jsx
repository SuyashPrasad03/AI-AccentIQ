import { useState, useEffect } from "react";
import { useDispatch } from "react-redux";
import { apiFetch } from "../../api/client.js";
import { logout } from "../../store/authSlice.js";

export function MyDataPage() {
  const dispatch = useDispatch();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [withdrawing, setWithdrawing] = useState(false);

  useEffect(() => {
    apiFetch("/me/data-summary")
      .then((d) => { setSummary(d); setLoading(false); })
      .catch((err) => { setError(err.message); setLoading(false); });
  }, []);

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await apiFetch("/me", { method: "DELETE" });
      dispatch(logout());
    } catch (err) {
      setError(err.message);
      setDeleting(false);
    }
  };

  const handleWithdraw = async () => {
    setWithdrawing(true);
    try {
      await apiFetch("/me/consent/withdraw", { method: "POST" });
      alert("Audio processing consent withdrawn. You will need to re-consent before uploading.");
    } catch (err) {
      setError(err.message);
    } finally {
      setWithdrawing(false);
    }
  };

  if (loading) return <div className="page-container"><p className="loading-text">Loading your data summary…</p></div>;
  if (error) return <div className="page-container"><div className="form-error">{error}</div></div>;
  if (!summary) return null;

  return (
    <div className="page-container">
      <section className="mydata-card">
        <h2>My Data</h2>
        <p className="mydata-intro">
          Here is a summary of what we store. You can delete your account and all data at any time.
        </p>

        <div className="mydata-grid">
          <div className="mydata-item">
            <span className="mydata-label">Email</span>
            <span className="mydata-value">{summary.email}</span>
          </div>
          <div className="mydata-item">
            <span className="mydata-label">Recordings</span>
            <span className="mydata-value">{summary.recordings_count}</span>
          </div>
          <div className="mydata-item">
            <span className="mydata-label">Consent events</span>
            <span className="mydata-value">{summary.consent_events_count}</span>
          </div>
          <div className="mydata-item">
            <span className="mydata-label">Audio retention</span>
            <span className="mydata-value">{summary.audio_retention_days} days (auto-deleted)</span>
          </div>
          <div className="mydata-item">
            <span className="mydata-label">Account created</span>
            <span className="mydata-value">{new Date(summary.account_created_at).toLocaleDateString()}</span>
          </div>
        </div>

        <div className="mydata-actions">
          <button className="btn btn-outline" onClick={handleWithdraw} disabled={withdrawing}>
            {withdrawing ? "Withdrawing…" : "Withdraw audio consent"}
          </button>

          {!confirmDelete ? (
            <button className="btn btn-danger" onClick={() => setConfirmDelete(true)}>
              Delete my account and all data
            </button>
          ) : (
            <div className="mydata-confirm">
              <p className="mydata-warning">
                This will permanently delete your account, all recordings, scores, and progress.
                This action cannot be undone.
              </p>
              <button className="btn btn-danger" onClick={handleDelete} disabled={deleting}>
                {deleting ? "Deleting…" : "Yes, permanently delete everything"}
              </button>
              <button className="btn btn-ghost" onClick={() => setConfirmDelete(false)}>
                Cancel
              </button>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
