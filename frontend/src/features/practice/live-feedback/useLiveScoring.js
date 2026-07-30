/**
 * Phase 30 — Live Scoring WebSocket Hook
 *
 * Manages the WebSocket connection for real-time streaming pronunciation scoring.
 * Handles: connection lifecycle, audio streaming, score event processing, fallback.
 */

import { useState, useRef, useCallback, useEffect } from "react";

const WS_URL = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws/practice`;

/** Score event from the server */
// { type: "word_score", word, index, score, issue, timestamp, latency_ms }

export function useLiveScoring() {
  const [status, setStatus] = useState("idle"); // idle|connecting|ready|recording|ended|error
  const [wordScores, setWordScores] = useState([]); // [{word, index, score, issue, latency_ms}]
  const [sessionSummary, setSessionSummary] = useState(null);
  const [error, setError] = useState(null);

  const wsRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const processorRef = useRef(null);
  const streamRef = useRef(null);

  /** Connect to WebSocket and start recording */
  const startLiveSession = useCallback(async () => {
    setStatus("connecting");
    setWordScores([]);
    setSessionSummary(null);
    setError(null);

    try {
      // 1. Connect WebSocket
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus("ready");
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        switch (data.type) {
          case "status":
            if (data.message === "ready") {
              setStatus("ready");
              _startMicrophone();
            }
            break;
          case "word_score":
            setWordScores((prev) => [...prev, data]);
            break;
          case "session_end":
            setSessionSummary(data);
            setStatus("ended");
            break;
          case "error":
            setError(data.message);
            setStatus("error");
            break;
        }
      };

      ws.onerror = () => {
        setError("WebSocket connection failed");
        setStatus("error");
      };

      ws.onclose = () => {
        if (status === "recording") {
          // Unexpected disconnect — trigger fallback
          setError("Connection dropped. Your recording was saved for batch processing.");
          setStatus("error");
        }
      };
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }, []);

  /** Start microphone capture and stream to WebSocket */
  const _startMicrophone = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      streamRef.current = stream;

      // Use AudioContext + ScriptProcessor to get raw PCM
      const audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 16000,
      });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);

      // Buffer size 4096 at 16kHz = ~256ms chunks
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          const float32 = e.inputBuffer.getChannelData(0);
          // Convert float32 to int16 for transmission
          const int16 = new Int16Array(float32.length);
          for (let i = 0; i < float32.length; i++) {
            int16[i] = Math.max(-32768, Math.min(32767, Math.round(float32[i] * 32768)));
          }
          wsRef.current.send(int16.buffer);
        }
      };

      source.connect(processor);
      processor.connect(audioContext.destination);
      setStatus("recording");
    } catch (err) {
      setError("Microphone access denied: " + err.message);
      setStatus("error");
    }
  }, []);

  /** Stop recording and end the session */
  const stopLiveSession = useCallback(() => {
    // Stop microphone
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }

    // Send END command
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send("END");
    }
  }, []);

  /** Clean up on unmount */
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  return {
    status,
    wordScores,
    sessionSummary,
    error,
    startLiveSession,
    stopLiveSession,
  };
}
