import { useState, useEffect, useRef } from "react";
import { getRecordingStatus, getTranscript } from "../../api/transcription.js";

const POLL_INTERVAL_MS = 3000;

/**
 * ProcessingStatus — polls the recording status and shows progress.
 *
 * Props:
 *   recordingId   – the recording ID to poll
 *   onComplete    – called with the transcript data when processing finishes
 *   onFailed      – called when processing fails
 */
export function ProcessingStatus({ recordingId, onComplete, onFailed }) {
  const [status, setStatus] = useState("uploaded");
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (!recordingId) return;

    const poll = async () => {
      try {
        const data = await getRecordingStatus(recordingId);
        setStatus(data.status);

        if (data.status === "transcribed" || data.status === "scored") {
          clearInterval(intervalRef.current);
          // Fetch the full transcript
          try {
            const transcript = await getTranscript(recordingId);
            onComplete?.(transcript);
          } catch (err) {
            setError("Transcript fetch failed: " + err.message);
            onFailed?.(err.message);
          }
        } else if (data.status === "failed") {
          clearInterval(intervalRef.current);
          setError(data.error_reason || "Transcription failed. Please try again.");
          onFailed?.(data.error_reason);
        }
      } catch (err) {
        // Network error — keep polling, don't give up yet
        console.warn("Status poll error:", err.message);
      }
    };

    // Poll immediately, then on interval
    poll();
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [recordingId, onComplete, onFailed]);

  if (error) {
    return (
      <div className="processing-status processing-error" role="alert">
        <span className="processing-icon">❌</span>
        <p>{error}</p>
      </div>
    );
  }

  const messages = {
    uploaded: "Queued for processing…",
    processing: "Analyzing your speech… usually 15–30 seconds.",
    transcribed: "Transcription complete.",
    scored: "Analysis complete.",
  };

  return (
    <div className="processing-status" aria-live="polite">
      <span className="boot-spinner" aria-hidden="true" />
      <p className="processing-msg">{messages[status] || "Processing…"}</p>
      <p className="processing-hint">
        You can wait here or come back — results are saved.
      </p>
    </div>
  );
}
