import { apiFetch } from "./client.js";

export async function getQuotaStatus() {
  return apiFetch("/quota/status");
}

export async function incrementQuotaStub() {
  return apiFetch("/quota/increment", { method: "POST" });
}

export async function recordConsent(consent_type) {
  return apiFetch("/consent", {
    method: "POST",
    body: JSON.stringify({ consent_type }),
  });
}

export async function getConsentStatus() {
  return apiFetch("/consent/status");
}
