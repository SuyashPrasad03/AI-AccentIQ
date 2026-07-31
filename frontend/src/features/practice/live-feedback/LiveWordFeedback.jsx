/**
 * Phase 30 — Live Word-Level Feedback Component
 *
 * Renders words in real-time with color-coded scores as they're spoken:
 *   - Green: score >= 70 (correct)
 *   - Yellow/Orange: score 40-69 (unclear/needs work)
 *   - Red: score < 40 (mispronounced)
 *
 * Visually the most impressive feature: words light up as you speak.
 */

import { useState } from "react";
import { useLiveScoring } from "./useLiveScoring.js";

function getWordColor(score, issue) {
  if (issue === "correct" || score >= 70) return "text-green-600 bg-green-50";
  if (score >= 40) return "text-amber-600 bg-amber-50";
  return "text-red-600 bg-red-50";
}

function getScoreBadge(score) {
  if (score >= 70) return "bg-green-100 text-green-700";
  if (score >= 40) return "bg-amber-100 text-amber-700";
  return "bg-red-100 text-red-700";
}

export function LiveWordFeedback() {
  const {
    status,
    wordScores,
    sessionSummary,
    error,
    startLiveSession,
    stopLiveSession,
  } = useLiveScoring();

  return (
    <div className="live-feedback-container p-4 rounded-xl border border-gray-200 bg-white">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-800">
          🎙️ Live Practice Mode
        </h3>
        <StatusIndicator status={status} />
      </div>

      {/* Controls */}
      <div className="flex gap-3 mb-4">
        {(status === "idle" || status === "ended" || status === "error") && (
          <button
            onClick={startLiveSession}
            className="px-4 py-2 rounded-lg bg-[#8B2E2E] text-white font-medium hover:bg-[#7A2828] transition-colors"
          >
            Start Live Session
          </button>
        )}
        {status === "recording" && (
          <button
            onClick={stopLiveSession}
            className="px-4 py-2 rounded-lg bg-gray-700 text-white font-medium hover:bg-gray-800 transition-colors flex items-center gap-2"
          >
            <span className="w-2 h-2 rounded-full bg-red-400 animate-pulse" />
            Stop Recording
          </button>
        )}
      </div>

      {/* Error display */}
      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Live word display */}
      {wordScores.length > 0 && (
        <div className="mb-4">
          <p className="text-xs text-gray-500 mb-2 uppercase tracking-wide font-medium">
            Words scored in real-time:
          </p>
          <div className="flex flex-wrap gap-2">
            {wordScores.map((ws, i) => (
              <div
                key={i}
                className={`inline-flex flex-col items-center px-3 py-1.5 rounded-lg transition-all duration-300 ${getWordColor(ws.score, ws.issue)}`}
                title={`Score: ${ws.score.toFixed(0)}/100 | Issue: ${ws.issue} | Latency: ${ws.latency_ms}ms`}
              >
                <span className="font-medium text-sm">{ws.word}</span>
                <span className={`text-[10px] font-bold rounded px-1 mt-0.5 ${getScoreBadge(ws.score)}`}>
                  {Math.round(ws.score)}
                </span>
              </div>
            ))}
            {status === "recording" && (
              <span className="inline-flex items-center px-3 py-1.5 text-gray-400 animate-pulse">
                ...
              </span>
            )}
          </div>
        </div>
      )}

      {/* Session summary */}
      {sessionSummary && (
        <div className="p-4 rounded-lg bg-gray-50 border border-gray-100">
          <h4 className="font-semibold text-gray-700 mb-2">Session Complete</h4>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <Stat label="Overall" value={`${sessionSummary.overall_score}/100`} />
            <Stat label="Words" value={sessionSummary.total_words} />
            <Stat label="Duration" value={`${sessionSummary.duration_seconds}s`} />
            <Stat label="Avg Latency" value={`${sessionSummary.avg_latency_ms}ms`} />
          </div>
        </div>
      )}

      {/* Instructions when idle */}
      {status === "idle" && wordScores.length === 0 && (
        <p className="text-sm text-gray-500">
          Start a live session to get real-time word-by-word pronunciation feedback as you speak.
          Words will light up green, yellow, or red based on your pronunciation quality.
        </p>
      )}
    </div>
  );
}

function StatusIndicator({ status }) {
  const config = {
    idle: { color: "bg-gray-300", text: "Ready" },
    connecting: { color: "bg-yellow-400 animate-pulse", text: "Connecting..." },
    ready: { color: "bg-blue-400 animate-pulse", text: "Initializing..." },
    recording: { color: "bg-red-500 animate-pulse", text: "Recording" },
    ended: { color: "bg-green-500", text: "Done" },
    error: { color: "bg-red-500", text: "Error" },
  };
  const { color, text } = config[status] || config.idle;

  return (
    <div className="flex items-center gap-1.5">
      <span className={`w-2 h-2 rounded-full ${color}`} />
      <span className="text-xs text-gray-500 font-medium">{text}</span>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div>
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-sm font-bold text-gray-800">{value}</div>
    </div>
  );
}
