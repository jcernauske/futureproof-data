import { apiPost } from "@/api/client";
import type { CheckpointPayload } from "@/types/session";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export function saveCheckpoint(payload: CheckpointPayload): Promise<unknown> {
  return apiPost("/session/checkpoint", payload);
}

export async function clearSession(): Promise<void> {
  const res = await fetch(`${API_BASE}/session`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Session clear failed: ${res.status}`);
}
