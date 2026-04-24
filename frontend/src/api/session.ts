import { apiPost } from "@/api/client";
import type { CheckpointPayload, SessionResponse } from "@/types/session";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function getSession(): Promise<SessionResponse | null> {
  const res = await fetch(`${API_BASE}/session`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Session load failed: ${res.status}`);
  return res.json() as Promise<SessionResponse>;
}

export function saveCheckpoint(payload: CheckpointPayload): Promise<unknown> {
  return apiPost("/session/checkpoint", payload);
}

export async function clearSession(): Promise<void> {
  const res = await fetch(`${API_BASE}/session`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Session clear failed: ${res.status}`);
}
