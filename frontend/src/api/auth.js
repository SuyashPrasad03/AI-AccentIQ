import { apiFetch } from "./client.js";

const REFRESH_TOKEN_KEY = "accentiq_refresh_token";

export function storeRefreshToken(token) {
  if (token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
  }
}

export function getStoredRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function clearStoredRefreshToken() {
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export async function registerEmail(email) {
  return apiFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function verifyOtp(email, otp, password) {
  const data = await apiFetch("/auth/verify-otp", {
    method: "POST",
    body: JSON.stringify({ email, otp, password }),
  });
  if (data.refresh_token) storeRefreshToken(data.refresh_token);
  return data;
}

export async function loginUser(email, password) {
  const data = await apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (data.refresh_token) storeRefreshToken(data.refresh_token);
  return data;
}

export async function refreshToken() {
  const stored = getStoredRefreshToken();
  const data = await apiFetch("/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: stored || "" }),
  });
  if (data.refresh_token) storeRefreshToken(data.refresh_token);
  return data;
}

export async function logoutUser() {
  const stored = getStoredRefreshToken();
  clearStoredRefreshToken();
  return apiFetch("/auth/logout", {
    method: "POST",
    body: JSON.stringify({ refresh_token: stored || "" }),
  });
}

export async function getMe() {
  return apiFetch("/auth/me");
}
