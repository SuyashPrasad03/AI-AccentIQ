import { useState, useRef, useEffect } from "react";
import { useDispatch } from "react-redux";
import { uploadRecording } from "../../api/recordings.js";
import { fetchQuota } from "../../store/quotaSlice.js";
import { Waveform } from "../../components/waveform/Waveform.jsx";
import { ResultsView } from "../scoring/ResultsView.jsx";
import { ProcessingStatus } from "../scoring/ProcessingStatus.jsx";
import { RecordingHistory } from "../progress/RecordingHistory.jsx";
import { StatsStrip } from "../../components/StatsStrip.jsx";

const MIN_DURATION = 1;
const MAX_DURATION = 45;

export function AudioUploader() {
  const dispatch = useDispatch();
  const [mode, setMode] = useState("idle");
  const [duration, setDuration] = useState(0);
  const [errorMsg, setErrorMsg] = useState("");
  const [result, setResult] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [history, setHistory] = useState(null);

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const startTimeRef = useRef(null);
  const cancelledRef = useRef(false);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") mediaRecorderRef.current.stop();
    };
  }, []);

  const handleFileSelect = async (file) => {
    setErrorMsg(""); setResult(null);
    const fileDuration = await getFileDuration(file);
    if (fileDuration !== null && fileDuration > MAX_DURATION) {
      setErrorMsg(`Too long (${fileDuration.toFixed(1)}s). Maximum is ${MAX_DURATION} seconds.`);
      return;
    }
    await doUpload(file);
  };

  const handleDrop = (e) => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files[0]; if (f) handleFileSelect(f); };
  const handleInputChange = (e) => { const f = e.target.files?.[0]; if (f) handleFileSelect(f); };

  const startRecording = async () => {
    setErrorMsg(""); setResult(null); setDuration(0);
    cancelledRef.current = false;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        if (timerRef.current) clearInterval(timerRef.current);
        // If user cancelled, don't upload
        if (cancelledRef.current) return;
        await new Promise((r) => setTimeout(r, 100));
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        if (blob.size < 1000) { setMode("idle"); setErrorMsg("Recording was too short or empty. Try again."); return; }
        await doUpload(blob);
      };
      recorder.start();
      startTimeRef.current = Date.now();
      setMode("recording");
      timerRef.current = setInterval(() => {
        const elapsed = (Date.now() - startTimeRef.current) / 1000;
        setDuration(elapsed);
        if (elapsed >= MAX_DURATION) stopRecording();
      }, 200);
    } catch (_e) {
      setErrorMsg("Microphone access denied. Please allow permissions.");
      setMode("idle");
    }
  };

  const stopRecording = () => { if (mediaRecorderRef.current?.state !== "inactive") mediaRecorderRef.current.stop(); };

  const doUpload = async (fileOrBlob) => {
    setMode("uploading");
    try {
      const data = await uploadRecording(fileOrBlob);
      setResult(data); setMode("processing"); dispatch(fetchQuota());
    } catch (err) {
      let msg = err.message;
      if (msg.includes("duration") || msg.includes("corrupted")) msg = "We couldn't read that file — try a different format (MP3, WAV, M4A).";
      else if (msg.includes("quota") || msg.includes("Quota")) msg = "You've used all free analyses. Sign up to continue.";
      else if (msg.includes("consent")) msg = "Please accept the privacy consent first.";
      setErrorMsg(msg); setMode("idle");
    }
  };

  // ── Results ─────────────────────────────────────────────
  if (mode === "results" && result) {
    return (
      <div className="animate-slide-up">
        <ResultsView recordingId={result.recording.id} />
        <div className="text-center mt-8">
          <button className="btn-secondary" onClick={() => { setMode("idle"); setResult(null); }}>
            ← Back to dashboard
          </button>
        </div>
      </div>
    );
  }

  // ── Processing ──────────────────────────────────────────
  if (mode === "processing" && result) {
    return (
      <div className="card text-center animate-fade-in py-12">
        <ProcessingStatus recordingId={result.recording.id} onComplete={() => setMode("results")} onFailed={(msg) => { setErrorMsg(msg || "Processing failed."); setMode("idle"); }} />
      </div>
    );
  }

  // ── Uploading ───────────────────────────────────────────
  if (mode === "uploading") {
    return (
      <div className="card flex flex-col items-center gap-4 py-14 animate-fade-in">
        <div className="w-10 h-10 border-[3px] border-card-border border-t-primary rounded-full animate-[spin_0.8s_linear_infinite]" />
        <p className="text-ink-muted text-sm">Uploading and processing…</p>
      </div>
    );
  }

  // ── Recording ───────────────────────────────────────────
  if (mode === "recording") {
    return (
      <div className="card flex flex-col items-center gap-5 py-10 animate-fade-in">
        <div className="h-20 w-full max-w-xs"><Waveform state="recording" bars={35} /></div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 bg-danger rounded-full animate-pulse" />
          <span className="font-mono text-xl font-bold text-danger">{duration.toFixed(1)}s</span>
          <span className="text-ink-faint text-sm">/ {MAX_DURATION}s</span>
        </div>
        <div className="flex gap-3">
          <button className="btn-secondary" onClick={() => {
            cancelledRef.current = true;
            if (mediaRecorderRef.current?.state !== "inactive") {
              mediaRecorderRef.current.stop();
              mediaRecorderRef.current.stream.getTracks().forEach(t => t.stop());
            }
            mediaRecorderRef.current = null;
            if (timerRef.current) clearInterval(timerRef.current);
            setMode("idle"); setDuration(0);
          }}>Cancel</button>
          <button className="btn-primary" onClick={stopRecording} disabled={duration < MIN_DURATION}>
            {duration < MIN_DURATION ? "Recording…" : "⏹ Stop & analyze"}
          </button>
        </div>
      </div>
    );
  }

  // ── Idle — Dashboard ────────────────────────────────────
  return (
    <div className="flex flex-col gap-6">
      {/* Stats strip */}
      <StatsStrip history={history} />

      {/* Upload card — elevated, tinted */}
      <div
        className={`relative overflow-hidden rounded-[var(--radius-card)] border-2 border-dashed transition-all cursor-pointer
          ${dragOver ? "border-primary bg-primary-soft shadow-lg" : "border-primary/30 bg-bg-soft hover:border-primary/60 hover:shadow-card"}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => document.getElementById("file-input").click()}
        role="button" tabIndex={0}
        onKeyDown={(e) => { if (e.key === "Enter") document.getElementById("file-input").click(); }}
      >
        <div className="relative z-10 flex flex-col items-center py-12 gap-3">
          <div className="w-14 h-14 rounded-full bg-primary-soft flex items-center justify-center mb-1">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-primary">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </div>
          <p className="text-ink font-medium text-sm">
            Drop an audio file here, or <span className="text-primary font-semibold">browse</span>
          </p>
          <p className="text-ink-faint text-xs">MP3, WAV, M4A, WebM · up to 45 seconds</p>
        </div>
        <input id="file-input" type="file" accept="audio/*" onChange={handleInputChange} className="hidden" />
      </div>

      {/* Record button */}
      <button className="btn-primary w-full py-4 text-base" onClick={startRecording}>
        🎤 Record with microphone
      </button>

      {/* Tip for best results */}
      <div className="flex items-start gap-2.5 px-4 py-3 bg-blue-50 rounded-[var(--radius-lg)] border border-blue-200">
        <span className="text-base mt-0.5">💡</span>
        <p className="text-xs text-ink-muted leading-relaxed">
          <strong className="text-ink">Tip:</strong> For best results, read an <strong>English</strong> sentence or paragraph aloud.
          The AI compares what you said against standard English pronunciation — speaking clearly for 5-45 seconds gives the most accurate feedback.
        </p>
      </div>

      {/* DPDP Privacy notice — always visible for anonymous users */}
      <div className="flex items-start gap-2.5 px-4 py-3 bg-bg-soft rounded-[var(--radius-lg)] border border-border-soft">
        <span className="text-base mt-0.5">🔒</span>
        <p className="text-xs text-ink-muted leading-relaxed">
          <strong className="text-ink">Privacy:</strong> Your audio is processed securely on our servers, never shared with third parties,
          and automatically deleted after <strong>30 days</strong>. We comply with India's DPDP Act 2023.
          Only text-based analysis is sent to AI — never your raw audio.
        </p>
      </div>

      {/* Error */}
      {errorMsg && (
        <div className="bg-danger-soft border border-danger/20 rounded-[var(--radius-lg)] px-5 py-3.5 animate-slide-up">
          <p className="text-sm text-danger font-medium">{errorMsg}</p>
        </div>
      )}

      {/* Recording history */}
      <RecordingHistory onSelect={(id) => { setResult({ recording: { id } }); setMode("results"); }} onHistoryLoad={setHistory} />
    </div>
  );
}

function getFileDuration(file) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const audio = new Audio();
    audio.addEventListener("loadedmetadata", () => { URL.revokeObjectURL(url); resolve(isFinite(audio.duration) ? audio.duration : null); });
    audio.addEventListener("error", () => { URL.revokeObjectURL(url); resolve(null); });
    audio.src = url;
  });
}
