/**
 * Phase 32 — Admin Observability Dashboard
 *
 * Shows AI pipeline metrics: latency, cost, quality per stage.
 * Access-restricted to authenticated users.
 * Uses Recharts for visualization.
 */

import { useState, useEffect } from "react";
import { useSelector } from "react-redux";
import { selectIsAuthenticated } from "../../store/authSlice.js";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export function AdminDashboard() {
  const isAuth = useSelector(selectIsAuthenticated);
  const [summary, setSummary] = useState(null);
  const [recentRecords, setRecentRecords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hours, setHours] = useState(24);

  useEffect(() => {
    if (isAuth) fetchMetrics();
  }, [isAuth, hours]);

  async function fetchMetrics() {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("access_token");
      const headers = token ? { Authorization: `Bearer ${token}` } : {};

      const [summaryRes, recentRes] = await Promise.all([
        fetch(`${API_BASE}/admin/metrics/summary?hours=${hours}`, { headers, credentials: "include" }),
        fetch(`${API_BASE}/admin/metrics/recent?limit=30`, { headers, credentials: "include" }),
      ]);

      if (summaryRes.ok) setSummary(await summaryRes.json());
      if (recentRes.ok) setRecentRecords((await recentRes.json()).records || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (!isAuth) {
    return (
      <div className="p-8 text-center text-gray-500">
        <p>Sign in to view the admin dashboard.</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">🔍 AI Pipeline Observability</h1>
        <div className="flex items-center gap-2">
          <select
            value={hours}
            onChange={(e) => setHours(Number(e.target.value))}
            className="text-sm border border-gray-200 rounded px-2 py-1"
          >
            <option value={1}>Last 1 hour</option>
            <option value={6}>Last 6 hours</option>
            <option value={24}>Last 24 hours</option>
            <option value={168}>Last 7 days</option>
          </select>
          <button
            onClick={fetchMetrics}
            className="text-sm px-3 py-1 rounded bg-gray-100 hover:bg-gray-200 transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>

      {error && <div className="mb-4 p-3 rounded bg-red-50 text-red-700 text-sm">{error}</div>}
      {loading && <div className="text-gray-500 text-sm mb-4">Loading metrics...</div>}

      {summary && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
            <MetricCard label="Total Requests" value={summary.total_requests} />
            <MetricCard label="Total Cost" value={`$${summary.total_cost_usd.toFixed(4)}`} />
            <MetricCard label="Stages Tracked" value={Object.keys(summary.stages).length} />
            <MetricCard label="Period" value={`${summary.period_hours}h`} />
          </div>

          {/* Per-stage breakdown */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden mb-6">
            <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
              <h2 className="text-sm font-semibold text-gray-700">Pipeline Stage Metrics</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-500 uppercase border-b">
                    <th className="px-4 py-2">Stage</th>
                    <th className="px-4 py-2">Count</th>
                    <th className="px-4 py-2">p50 (ms)</th>
                    <th className="px-4 py-2">p95 (ms)</th>
                    <th className="px-4 py-2">Mean (ms)</th>
                    <th className="px-4 py-2">Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(summary.stages).map(([stage, data]) => (
                    <tr key={stage} className="border-b border-gray-50 hover:bg-gray-50">
                      <td className="px-4 py-2 font-medium text-gray-800">{stage}</td>
                      <td className="px-4 py-2 text-gray-600">{data.count}</td>
                      <td className="px-4 py-2">
                        <LatencyBadge ms={data.latency_p50} />
                      </td>
                      <td className="px-4 py-2">
                        <LatencyBadge ms={data.latency_p95} />
                      </td>
                      <td className="px-4 py-2 text-gray-600">{data.latency_mean}</td>
                      <td className="px-4 py-2 text-gray-600">
                        {data.cost_total > 0 ? `$${data.cost_total.toFixed(4)}` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Recent records */}
          {recentRecords.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
                <h2 className="text-sm font-semibold text-gray-700">Recent Pipeline Events</h2>
              </div>
              <div className="max-h-64 overflow-y-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-left text-gray-500 uppercase border-b sticky top-0 bg-white">
                      <th className="px-3 py-1.5">Time</th>
                      <th className="px-3 py-1.5">Stage</th>
                      <th className="px-3 py-1.5">Latency</th>
                      <th className="px-3 py-1.5">Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentRecords.map((rec, i) => (
                      <tr key={i} className="border-b border-gray-50">
                        <td className="px-3 py-1 text-gray-500">
                          {rec.timestamp ? new Date(rec.timestamp).toLocaleTimeString() : "—"}
                        </td>
                        <td className="px-3 py-1 font-medium">{rec.stage}</td>
                        <td className="px-3 py-1">
                          <LatencyBadge ms={rec.latency_ms} />
                        </td>
                        <td className="px-3 py-1 text-gray-500">
                          {rec.cost_usd ? `$${rec.cost_usd.toFixed(5)}` : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {!summary && !loading && (
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg mb-2">No metrics data yet</p>
          <p className="text-sm">Metrics will appear here after recordings are processed through the pipeline.</p>
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>
      <div className="text-xl font-bold text-gray-800 mt-1">{value}</div>
    </div>
  );
}

function LatencyBadge({ ms }) {
  let color = "bg-green-100 text-green-700";
  if (ms > 5000) color = "bg-red-100 text-red-700";
  else if (ms > 2000) color = "bg-amber-100 text-amber-700";

  return (
    <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-medium ${color}`}>
      {ms > 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)}ms`}
    </span>
  );
}
