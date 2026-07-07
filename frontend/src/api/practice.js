import { apiFetch } from "./client.js";

export async function getTodayPractice() {
  return apiFetch("/practice/today");
}

export async function regeneratePractice() {
  return apiFetch("/practice/regenerate", { method: "POST" });
}
