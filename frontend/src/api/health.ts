/**
 * Typed client for the /health endpoint.
 * All API functions live under src/api/ so the rest of the app
 * never calls fetch() directly.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export type ConnectionStatus = "connected" | "disconnected";
export type OverallStatus = "ok" | "degraded";

export interface HealthResponse {
  status: OverallStatus;
  mysql: ConnectionStatus;
  mongo: ConnectionStatus;
}

/**
 * Call GET /health and return the parsed response.
 * Throws a typed Error if the network request itself fails.
 */
export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    throw new Error(`Health check returned HTTP ${response.status}`);
  }

  return response.json() as Promise<HealthResponse>;
}
