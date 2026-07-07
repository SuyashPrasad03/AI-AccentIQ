import { apiFetch } from "./client.js";

export async function getComparison(recordingId) {
  return apiFetch(`/recordings/${recordingId}/comparison`);
}

export async function getProgressHistory(limit = 50, offset = 0) {
  return apiFetch(`/progress/history?limit=${limit}&offset=${offset}`);
}
