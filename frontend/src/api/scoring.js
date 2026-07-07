import { apiFetch } from "./client.js";

export async function getScore(recordingId) {
  return apiFetch(`/recordings/${recordingId}/score`);
}
