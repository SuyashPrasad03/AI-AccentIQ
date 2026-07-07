import { apiFetch } from "./client.js";

export async function explainWord(recordingId, wordIndex) {
  return apiFetch(`/recordings/${recordingId}/words/${wordIndex}/explain`);
}
