import { useState, useEffect, useRef } from "react";
import { getRecordingStatus } from "../../api/transcription.js";

const POLL_INTERVAL_MS = 2500;

const STAGES = [
  { key: "queued", label: "Upload complete", icon: "✓" },
  { key: "transcribing", label: "Transcribing speech…", icon: "🔊" },
  { key: "scoring", label: "Analyzing pronunciation…", icon: "🧠" },
  { key: "complete", label: "Report ready", icon: "📊" },
];

export function ProcessingStatus({ recordingId, onComplete, onFailed }) {
  const [currentStage, setCurrentStage] = useState("queued");
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);
  const doneRef = useRef(false);

  useEffect(() => {
    if (!recordingId || doneRef.current) return;

    const poll = async () => {
      if (doneRef.current) return;
      try {
        const data = await getRecordingStatus(recordingId);
        const stage = data.stage || "queued";
        setCurrentStage(stage);

        if (data.status === "scored" || stage === "complete") {
          doneRef.current = true;
          if (intervalRef.current) clearInterval(intervalRef.current);
          setTimeout(() => onComplete?.(), 600); // brief pause so user sees "complete"
        } else if (data.status === "failed" || stage === "failed") {
          doneRef.current = true;
          if (intervalRef.current) clearInterval(intervalRef.current);
          setError(`Processing failed at: ${stage}`);
          onFailed?.(data.error_reason || `Failed during ${stage}`);
        }
      } catch (_e) { /* network hiccup, keep polling */ }
    };

    poll();
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [recordingId]); // eslint-disable-line

  const currentIdx = STAGES.findIndex((s) => s.key === currentStage);

  if (error) {
    return (
      <div className="flex flex-col items-center gap-4 py-8">
        <div className="w-12 h-12 rounded-full bg-danger-soft flex items-center justify-center text-xl">❌</div>
        <p className="text-sm text-danger font-medium text-center">{error}</p>
        <p className="text-xs text-ink-muted">Please try uploading again.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-8 py-8">
      {/* Animated loader */}
      <div className="relative">
        <div className="w-16 h-16 border-[3px] border-border-soft border-t-secondary rounded-full animate-[spin_1.2s_linear_infinite]" />
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-lg">{STAGES[Math.max(currentIdx, 0)]?.icon || "⏳"}</span>
        </div>
      </div>

      {/* Stage list */}
      <div className="flex flex-col gap-3 w-full max-w-xs">
        {STAGES.map((stage, i) => {
          const isDone = i < currentIdx || currentStage === "complete";
          const isCurrent = i === currentIdx && currentStage !== "complete";
          

          return (
            <div key={stage.key} className={`flex items-center gap-3 transition-all duration-300
              ${isDone ? "opacity-100" : isCurrent ? "opacity-100" : "opacity-40"}`}>
              {/* Status dot */}
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 transition-all
                ${isDone ? "bg-success text-white" : isCurrent ? "bg-secondary text-white animate-pulse" : "bg-border-soft text-ink-faint"}`}>
                {isDone ? "✓" : isCurrent ? "●" : i + 1}
              </div>
              {/* Label */}
              <span className={`text-sm transition-colors
                ${isDone ? "text-ink line-through" : isCurrent ? "text-ink font-medium" : "text-ink-faint"}`}>
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* ETA */}
      <p className="text-xs text-ink-faint">
        {currentStage === "transcribing" && "Usually takes 15–30 seconds…"}
        {currentStage === "scoring" && "Almost done…"}
        {currentStage === "queued" && "Starting analysis…"}
      </p>
    </div>
  );
}
