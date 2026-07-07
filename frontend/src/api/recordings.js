/**
 * API client for recording uploads.
 * Uses FormData (not JSON) for the multipart file upload.
 */

import { store } from "../store/store.js";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiException extends Error {
  constructor(status, errorBody) {
    super(errorBody?.message ?? `HTTP ${status}`);
    this.name = "ApiException";
    this.status = status;
    this.error_code = errorBody?.error_code ?? "UNKNOWN";
    this.details = errorBody?.details ?? null;
  }
}

export async function uploadRecording(file) {
  const accessToken = store.getState().auth.accessToken;
  const formData = new FormData();
  formData.append("file", file);

  const headers = {};
  if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;

  const response = await fetch(`${API_BASE}/recordings/upload`, {
    method: "POST",
    credentials: "include",
    headers,
    body: formData,
  });

  if (!response.ok) {
    let body = { error_code: "UNKNOWN", message: `HTTP ${response.status}` };
    try { body = await response.json(); } catch { /* ignore */ }
    throw new ApiException(response.status, body);
  }

  return response.json();
}
