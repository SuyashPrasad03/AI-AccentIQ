import { apiFetch } from "./client.js";

export async function getRecordingStatus(recordingId) {
  return apiFetch(`/recordings/${recordingId}/status`);
}

export async function getTranscript(recordingId) {
  return apiFetch(`/recordings/${recordingId}/transcript`);
}
