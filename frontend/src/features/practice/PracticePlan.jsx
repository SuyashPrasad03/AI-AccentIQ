/**
 * Phase 31 — Practice Plan UI with Checkpoint Tracking
 *
 * Displays the user's adaptive multi-day practice plan:
 * - Day-by-day breakdown with focus phonemes
 * - Sentence cards with difficulty indicators
 * - Checkpoint markers for re-assessment days
 * - Generate/regenerate buttons
 */

import { useState, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export function PracticePlan() {
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [generating, setGenerating] = useState(false);

  // Fetch active plan on mount
  useEffect(() => {
    fetchPlan();
  }, []);

  async function fetchPlan() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/practice/plan`, { credentials: "include" });
      const data = await res.json();
      if (data.has_plan) {
        setPlan(data.plan);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function generatePlan() {
    setGenerating(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/practice/plan/generate`, {
        method: "POST",
        credentials: "include",
      });
      const data = await res.json();
      if (data.has_plan) {
        setPlan(data.plan);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  }

  if (loading) {
    return <div className="p-4 text-gray-500 text-sm">Loading practice plan...</div>;
  }

  return (
    <div className="practice-plan p-4 rounded-xl border border-gray-200 bg-white">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-800">📋 Practice Plan</h3>
        <button
          onClick={generatePlan}
          disabled={generating}
          className="px-3 py-1.5 text-xs rounded-lg bg-[#8B2E2E] text-white font-medium hover:bg-[#7A2828] disabled:opacity-50 transition-colors"
        >
          {generating ? "Generating..." : plan ? "Regenerate Plan" : "Generate Plan"}
        </button>
      </div>

      {error && (
        <div className="mb-3 p-2 rounded bg-red-50 text-red-700 text-xs">{error}</div>
      )}

      {!plan && !loading && (
        <p className="text-sm text-gray-500">
          Generate a personalized practice plan based on your pronunciation history.
          The plan adapts to your weak areas and structures practice over 7 days.
        </p>
      )}

      {plan && (
        <div className="space-y-4">
          {/* Plan header */}
          <div className="flex flex-wrap gap-2 mb-3">
            <span className="text-xs px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 font-medium">
              {plan.duration_days} days
            </span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 font-medium">
              {plan.total_items} exercises
            </span>
            {plan.target_phonemes?.map((ph) => (
              <span key={ph} className="text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 font-medium">
                /{ph}/
              </span>
            ))}
            {plan.improvement_trend && plan.improvement_trend !== "insufficient_data" && (
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                plan.improvement_trend === "improving"
                  ? "bg-green-50 text-green-700"
                  : plan.improvement_trend === "regressing"
                  ? "bg-red-50 text-red-700"
                  : "bg-gray-50 text-gray-700"
              }`}>
                {plan.improvement_trend === "improving" ? "📈" : plan.improvement_trend === "regressing" ? "📉" : "➡️"} {plan.improvement_trend}
              </span>
            )}
          </div>

          {/* Day cards */}
          <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
            {plan.days?.map((day) => (
              <DayCard key={day.day_number} day={day} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function DayCard({ day }) {
  const [expanded, setExpanded] = useState(false);
  const isToday = day.date === new Date().toISOString().split("T")[0];

  return (
    <div
      className={`border rounded-lg p-3 cursor-pointer transition-colors ${
        isToday ? "border-[#8B2E2E] bg-red-50/30" : "border-gray-100 hover:border-gray-200"
      } ${day.is_checkpoint ? "ring-1 ring-purple-200" : ""}`}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-gray-500">Day {day.day_number}</span>
          {isToday && <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#8B2E2E] text-white">TODAY</span>}
          {day.is_checkpoint && <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-100 text-purple-700">CHECKPOINT</span>}
        </div>
        <div className="flex gap-1">
          {day.focus_phonemes?.map((ph) => (
            <span key={ph} className="text-xs px-1.5 py-0.5 rounded bg-amber-50 text-amber-700">
              /{ph}/
            </span>
          ))}
        </div>
      </div>

      {expanded && day.items && (
        <div className="mt-2 space-y-2">
          {day.items.map((item, i) => (
            <div key={i} className="pl-3 border-l-2 border-gray-200">
              <div className="flex items-center gap-1.5 mb-0.5">
                <DifficultyBadge difficulty={item.difficulty} />
                <span className="text-[10px] text-gray-400">/{item.target_phoneme}/</span>
              </div>
              <p className="text-sm text-gray-700 italic">"{item.sentence}"</p>
              <p className="text-[11px] text-gray-500 mt-0.5">{item.focus_description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DifficultyBadge({ difficulty }) {
  const config = {
    warmup: { label: "Warmup", color: "bg-green-100 text-green-700" },
    focus: { label: "Focus", color: "bg-blue-100 text-blue-700" },
    challenge: { label: "Challenge", color: "bg-orange-100 text-orange-700" },
  };
  const { label, color } = config[difficulty] || config.focus;
  return <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${color}`}>{label}</span>;
}
