import { useState, useRef, useEffect } from "react";
import { useDispatch } from "react-redux";
import { uploadRecording } from "../../api/recordings.js";
import { fetchQuota } from "../../store/quotaSlice.js";

const MIN_DURATION = 15;
const MAX_DURATION = 45;

/**
 * AudioUploader — supports both file upload and in-browser mic recording.
 *
 * Features:
 *   - File picker with drag-and-drop
 *   - Live mic recording with duration display + auto-stop at MAX_DURATION
 *   - Client-side duration pre-check (UX nicety — server is authoritative)
 *   - Upload progress indication
 */
export function AudioUploader() {
  const dispatch = useDispatch();

  const [mode, setMode] = useState("idle"); // idle | recording | uploading | success | error
  const [duration, setDuration] = useState(0);
  const [errorMsg, setErrorMsg] = useState("");
  const [result, setResult] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  // Mic recording refs
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const startTimeRef = useRef(null);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  // ── File picker / drag-drop ────────────────────────────────────────────────

  const handleFileSelect = async (file) => {
    setErrorMsg("");
    setResult(null);

    // Client-side duration check (UX only — server re-validates)
    const fileDuration = await getFileDuration(file);
    if (fileDuration !== null) {
      if (fileDuration < MIN_DURATION) {
        setErrorMsg(`Recording is too short (${fileDuration.toFixed(1)}s). Minimum is ${MIN_DURATION}s.`);
        return;
      }
      if (fileDuration > MAX_DURATION) {
        setErrorMsg(`Recording is too long (${fileDuration.toFixed(1)}s). Maximum is ${MAX_DURATION}s.`);
        return;
      }
    }

    await doUpload(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  };

  const handleInputChange = (e) => {
    const file = e.target.files?.[0];
    if (file) handleFileSelect(file);
  };

  // ── Mic recording ─────────────────────────────────────────────────────────

  const startRecording = async () => {
    setErrorMsg("");
    setResult(null);
    setDuration(0);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        if (timerRef.current) clearInterval(timerRef.current);

        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const elapsed = (Date.now() - startTimeRef.current) / 1000;

        if (elapsed < MIN_DURATION) {
          setMode("error");
          setErrorMsg(`Recording too short (${elapsed.toFixed(1)}s). Minimum is ${MIN_DURATION}s.`);
          return;
        }

        await doUpload(blob);
      };

      recorder.start(250); // collect in 250ms chunks
      startTimeRef.current = Date.now();
      setMode("recording");

      // Live timer
      timerRef.current = setInterval(() => {
        const elapsed = (Date.now() - startTimeRef.current) / 1000;
        setDuration(elapsed);

        // Auto-stop at max
        if (elapsed >= MAX_DURATION) {
          stopRecording();
        }
      }, 200);
    } catch (err) {
      setErrorMsg("Microphone access denied. Please allow mic permissions.");
      setMode("error");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
  };

  // ── Upload ─────────────────────────────────────────────────────────────────

  const doUpload = async (fileOrBlob) => {
    setMode("uploading");
    try {
      const data = await uploadRecording(fileOrBlob);
      setResult(data);
      setMode("success");
      dispatch(fetchQuota()); // refresh quota bar
    } catch (err) {
      setErrorMsg(err.message || "Upload failed.");
      setMode("error");
    }
  };

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="uploader-container">
      <h2 className="uploader-title">Upload or Record</h2>
      <p className="uploader-subtitle">
        {MIN_DURATION}–{MAX_DURATION} seconds of spoken English
      </p>

      {/* Drop zone / file picker */}
      {(mode === "idle" || mode === "error" || mode === "success") && (
        <div
          className={`drop-zone ${dragOver ? "drop-zone-active" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          role="button"
          tabIndex={0}
          aria-label="Drop audio file here or click to select"
        >
          <p className="drop-zone-text">
            📁 Drag & drop an audio file here, or{" "}
            <label className="file-label">
              browse
              <input type="file" accept="audio/*" onChange={handleInputChange} hidden />
            </label>
          </p>
        </div>
      )}

      {/* Mic recording UI */}
      {mode === "idle" && (
        <button className="btn btn-primary btn-large" onClick={startRecording}>
          🎤 Record with microphone
        </button>
      )}

      {mode === "recording" && (
        <div className="recording-live">
          <div className="recording-indicator" aria-label="Recording in progress">
            <span className="recording-dot" />
            <span>Recording… {duration.toFixed(1)}s / {MAX_DURATION}s</span>
          </div>
          <div className="recording-bar-track">
            <div
              className="recording-bar-fill"
              style={{ width: `${Math.min((duration / MAX_DURATION) * 100, 100)}%` }}
            />
          </div>
          <button className="btn btn-primary" onClick={stopRecording} disabled={duration < MIN_DURATION}>
            ⏹ Stop {duration < MIN_DURATION ? `(min ${MIN_DURATION}s)` : "and upload"}
          </button>
        </div>
      )}

      {mode === "uploading" && (
        <div className="upload-progress">
          <span className="boot-spinner" />
          <p>Uploading and processing…</p>
        </div>
      )}

      {/* Results / errors */}
      {errorMsg && (
        <div className="form-error" role="alert">{errorMsg}</div>
      )}

      {mode === "success" && result && (
        <div className="upload-success" role="status">
          <p>✅ Upload successful</p>
          <p className="upload-detail">
            Duration: {result.recording.duration_seconds.toFixed(1)}s — Status: {result.recording.status}
          </p>
          <button className="btn btn-ghost" onClick={() => { setMode("idle"); setResult(null); }}>
            Upload another
          </button>
        </div>
      )}
    </div>
  );
}

// ── Utility: read duration from file via HTMLAudioElement ─────────────────────

function getFileDuration(file) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const audio = new Audio();
    audio.addEventListener("loadedmetadata", () => {
      URL.revokeObjectURL(url);
      resolve(isFinite(audio.duration) ? audio.duration : null);
    });
    audio.addEventListener("error", () => {
      URL.revokeObjectURL(url);
      resolve(null); // can't determine — let server decide
    });
    audio.src = url;
  });
}
