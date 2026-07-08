/**
 * API client for recording uploads.
 * Uses FormData for multipart file upload.
 */

import { store } from "../store/store.js";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiException extends Error {
  constructor(status, errorBody) {
    super(errorBody?.message ?? `Upload failed (HTTP ${status})`);
    this.name = "ApiException";
    this.status = status;
    this.error_code = errorBody?.error_code ?? "UNKNOWN";
    this.details = errorBody?.details ?? null;
  }
}

export async function uploadRecording(fileOrBlob) {
  const accessToken = store.getState().auth.accessToken;
  const formData = new FormData();

  // Ensure the blob has a proper filename and type for the server
  if (fileOrBlob instanceof Blob && !(fileOrBlob instanceof File)) {
    // Browser-recorded blob — give it a filename so FastAPI/ffprobe can handle it
    const ext = fileOrBlob.type.includes("webm") ? "webm"
      : fileOrBlob.type.includes("mp4") ? "mp4"
      : fileOrBlob.type.includes("ogg") ? "ogg"
      : "webm"; // default for MediaRecorder
    formData.append("file", fileOrBlob, `recording.${ext}`);
  } else {
    formData.append("file", fileOrBlob);
  }

  const headers = {};
  if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;

  let response;
  try {
    response = await fetch(`${API_BASE}/recordings/upload`, {
      method: "POST",
      credentials: "include",
      headers,
      body: formData,
    });
  } catch {
    throw new ApiException(0, { message: "Network error — couldn't reach the server." });
  }

  if (!response.ok) {
    let body = { error_code: "UNKNOWN", message: `Upload failed (HTTP ${response.status})` };
    try { body = await response.json(); } catch { /* ignore */ }
    throw new ApiException(response.status, body);
  }

  return response.json();
}
