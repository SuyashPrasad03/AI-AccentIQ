import { apiFetch } from "./client.js";

export async function askAssistant(question) {
  return apiFetch("/assistant/ask", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}
