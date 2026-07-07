const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export async function fetchHealth() {
  const response = await fetch(`${API_BASE}/health`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error(`Health check returned HTTP ${response.status}`);
  return response.json();
}
