/**
 * Base API client.
 *
 * - Reads the access token directly from the Redux store on each call.
 * - On a 401, attempts one silent refresh before re-throwing.
 * - All API functions in src/api/ use `apiFetch` — never raw fetch().
 */

import { store } from "../store/store.js";
import { setAccessToken } from "../store/authSlice.js";

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
    "Content-Type": "application/json",
    ...(options.headers ?? {}),
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
  };

  let response = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers,
  });

  // One silent refresh attempt on 401
  if (response.status === 401 && accessToken) {
    const newToken = await tryRefresh();
    if (newToken) {
      store.dispatch(setAccessToken(newToken));
      response = await fetch(`${API_BASE}${path}`, {
        ...options,
        credentials: "include",
        headers: { ...headers, Authorization: `Bearer ${newToken}` },
      });
    }
  }

  if (!response.ok) {
    let body = { error_code: "UNKNOWN", message: `HTTP ${response.status}` };
    try { body = await response.json(); } catch { /* ignore */ }
    throw new ApiException(response.status, body);
  }

  if (response.status === 204) return undefined;
  return response.json();
}
