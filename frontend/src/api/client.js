/**
 * Base API client.
 * - Attaches JWT from Redux store.
 * - On 401: does NOT auto-retry for auth endpoints (login, verify-otp).
 * - Surfaces real error messages from the server, never raw "Failed to fetch".
 */

import { store } from "../store/store.js";
import { setAccessToken } from "../store/authSlice.js";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiException extends Error {
  constructor(status, errorBody) {
    super(errorBody?.message ?? `Request failed (HTTP ${status})`);
    this.name = "ApiException";
    this.status = status;
    this.error_code = errorBody?.error_code ?? "UNKNOWN";
    this.details = errorBody?.details ?? null;
  }
}

// Auth endpoints should NOT trigger silent refresh on 401
const AUTH_PATHS = ["/auth/login", "/auth/register", "/auth/verify-otp", "/auth/refresh"];

async function tryRefresh() {
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.access_token;
  } catch {
    return null;
  }
}

export async function apiFetch(path, options = {}) {
  const accessToken = store.getState().auth.accessToken;

  const headers = {
    ...(options.headers ?? {}),
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
  };

  // Only set Content-Type for non-FormData requests
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      credentials: "include",
      headers,
    });
  } catch (networkError) {
    throw new ApiException(0, { message: "Network error — is the backend running?", error_code: "NETWORK_ERROR" });
  }

  // Only attempt silent refresh for non-auth endpoints
  if (response.status === 401 && accessToken && !AUTH_PATHS.includes(path)) {
    const newToken = await tryRefresh();
    if (newToken) {
      store.dispatch(setAccessToken(newToken));
      try {
        response = await fetch(`${API_BASE}${path}`, {
          ...options,
          credentials: "include",
          headers: { ...headers, Authorization: `Bearer ${newToken}` },
        });
      } catch {
        throw new ApiException(0, { message: "Network error on retry.", error_code: "NETWORK_ERROR" });
      }
    }
  }

  if (!response.ok) {
    let body = { error_code: "UNKNOWN", message: `Request failed (HTTP ${response.status})` };
    try { body = await response.json(); } catch { /* ignore */ }
    throw new ApiException(response.status, body);
  }

  if (response.status === 204) return undefined;
  return response.json();
}
