import { useState, useEffect, useRef } from "react";
import { useSelector } from "react-redux";
import { selectIsAuthenticated } from "../../store/authSlice.js";
import { getProgressHistory } from "../../api/progress.js";
import { apiFetch } from "../../api/client.js";
import { ScoreBadge } from "../../components/ScoreBadge.jsx";

const PAGE_SIZE = 10;

export function RecordingHistory({ onSelect, onHistoryLoad }) {
  const isAuth = useSelector(selectIsAuthenticated);
  const [entries, setEntries] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [offset, setOffset] = useState(0);
  const [selectMode, setSelectMode] = useState(false);
  const [selected, setSelected] = useState(new Set());
  const [deleting, setDeleting] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editValue, setEditValue] = useState("");
  const fetched = useRef(false);

  const fetchPage = (pageOffset = 0, append = false) => {
    setLoading(true);
    getProgressHistory(PAGE_SIZE, pageOffset)
      .then((data) => {
        const newEntries = append ? [...entries, ...data.entries] : data.entries;
        setEntries(newEntries);
        setTotal(data.total);
        setOffset(pageOffset + data.entries.length);
        onHistoryLoad?.({ entries: newEntries, total: data.total });
      })
      .catch((_e) => { /* ignore */ })
      .finally(() => setLoading(false));
  };

  const prevAuth = useRef(isAuth);

  useEffect(() => {
    // When auth state changes (login/logout/switch user), reset history
    if (prevAuth.current !== isAuth) {
      prevAuth.current = isAuth;
      fetched.current = false;
      setEntries([]);
      setTotal(0);
      setOffset(0);
      setSelected(new Set());
      setSelectMode(false);
      onHistoryLoad?.(null);
    }

    if (!isAuth) return;
    if (fetched.current) return;
    fetched.current = true;
    fetchPage(0);
  }, [isAuth]); // eslint-disable-line

  const toggleSelect = (id) => {
    setSelected((prev) => { const n = new Set(prev); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  };
  const selectAll = () => {
    setSelected(selected.size === entries.length ? new Set() : new Set(entries.map((e) => e.recording_id)));
  };

  const handleDeleteSelected = async () => {
    if (selected.size === 0) return;
    if (!confirm(`Delete ${selected.size} recording${selected.size > 1 ? "s" : ""}?`)) return;
    setDeleting(true);
    for (const id of selected) {
      try { await apiFetch(`/recordings/${id}`, { method: "DELETE" }); } catch (_e) { /* ignore */ }
    }
    const updated = entries.filter((e) => !selected.has(e.recording_id));
    setEntries(updated); setTotal((p) => p - selected.size);
    setSelected(new Set()); setSelectMode(false); setDeleting(false);
    onHistoryLoad?.({ entries: updated, total: total - selected.size });
  };

  const startRename = (entry, e) => {
    e.stopPropagation();
    setEditingId(entry.recording_id);
    setEditValue(entry.title || `Recording ${total - entries.indexOf(entry)}`);
  };

  const saveRename = async (id) => {
    const trimmed = editValue.trim();
    if (trimmed) {
      try { await apiFetch(`/recordings/${id}`, { method: "PATCH", body: JSON.stringify({ title: trimmed }) }); } catch (_e) { /* ignore */ }
      setEntries((p) => p.map((e) => e.recording_id === id ? { ...e, title: trimmed } : e));
    }
    setEditingId(null);
  };

  const hasMore = entries.length < total;
  if (!isAuth) return null;

  // Empty state
  if (!loading && entries.length === 0) {
    return (
      <div className="text-center py-12 animate-fade-in">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary-soft flex items-center justify-center">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-primary">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>
          </svg>
        </div>
        <p className="text-ink font-semibold mb-1">No recordings yet</p>
        <p className="text-ink-muted text-sm">Upload your first recording to see your pronunciation score</p>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-bold text-base text-ink">
          Your recordings <span className="text-ink-faint font-normal text-sm ml-1">({total})</span>
        </h3>
        <div className="flex items-center gap-2">
          {selectMode ? (
            <>
              <button className="text-xs text-ink-muted hover:text-ink" onClick={selectAll}>
                {selected.size === entries.length ? "Deselect all" : "Select all"}
              </button>
              <button className="text-xs font-semibold text-danger hover:underline disabled:opacity-40"
                onClick={handleDeleteSelected} disabled={selected.size === 0 || deleting}>
                {deleting ? "Deleting…" : `Delete (${selected.size})`}
              </button>
              <button className="text-xs text-ink-faint hover:text-ink" onClick={() => { setSelectMode(false); setSelected(new Set()); }}>
                Cancel
              </button>
            </>
          ) : (
            <button className="text-xs font-semibold text-danger hover:underline" onClick={() => setSelectMode(true)}>
              Delete
            </button>
          )}
        </div>
      </div>

      {/* List */}
      <div className="flex flex-col gap-2">
        {entries.map((entry) => (
          <div
            key={entry.recording_id}
            className={`flex items-center gap-4 p-4 rounded-[var(--radius-lg)] transition-all cursor-pointer
              ${selected.has(entry.recording_id) ? "bg-danger-soft ring-1 ring-danger/20" : "bg-bg-soft hover:bg-card-border/40"}`}
            onClick={() => {
              if (selectMode) toggleSelect(entry.recording_id);
              else if (!editingId) onSelect?.(entry.recording_id);
            }}
          >
            {/* Checkbox in select mode */}
            {selectMode && (
              <input type="checkbox" checked={selected.has(entry.recording_id)}
                onChange={() => toggleSelect(entry.recording_id)}
                className="w-4 h-4 rounded border-card-border text-primary focus:ring-primary cursor-pointer shrink-0"
                onClick={(e) => e.stopPropagation()} />
            )}

            {/* Mini waveform */}
            <div className="flex items-end gap-[2px] h-6 shrink-0">
              {[40, 70, 55, 85, 45].map((h, i) => (
                <div key={i} className="w-[3px] rounded-full bg-primary/30" style={{ height: `${h}%` }} />
              ))}
            </div>

            {/* Title + date — flex-1 makes this fill remaining space */}
            <div className="flex-1 min-w-0" onClick={(e) => editingId && e.stopPropagation()}>
              {editingId === entry.recording_id ? (
                <input type="text" value={editValue} onChange={(e) => setEditValue(e.target.value)}
                  className="w-full px-2 py-1 text-sm border border-card-border rounded-lg focus:outline-none focus:border-primary bg-bg"
                  autoFocus maxLength={255}
                  onBlur={() => saveRename(entry.recording_id)}
                  onKeyDown={(e) => { if (e.key === "Enter") saveRename(entry.recording_id); if (e.key === "Escape") setEditingId(null); }}
                  onClick={(e) => e.stopPropagation()} />
              ) : (
                <>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-ink truncate">
                      {entry.title || `Recording ${total - entries.indexOf(entry)}`}
                    </span>
                    {!selectMode && (
                      <button className="text-[11px] text-ink-faint hover:text-primary shrink-0"
                        onClick={(e) => startRename(entry, e)} title="Rename">✏️</button>
                    )}
                  </div>
                  <p className="text-[11px] text-ink-faint mt-0.5">
                    {new Date(entry.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                  </p>
                </>
              )}
            </div>

            {/* Score badge */}
            <ScoreBadge score={entry.overall_score} />
          </div>
        ))}
      </div>

      {/* Load more */}
      {hasMore && (
        <div className="text-center mt-5">
          <button className="btn-ghost text-xs" onClick={() => fetchPage(offset, true)} disabled={loading}>
            {loading ? "Loading…" : `Show more (${total - entries.length} remaining)`}
          </button>
        </div>
      )}
    </div>
  );
}
