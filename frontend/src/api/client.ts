const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(
      (detail as { detail?: string }).detail || `API error: ${res.status}`,
    );
  }
  return res.json() as Promise<T>;
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(
      (detail as { detail?: string }).detail || `API error: ${res.status}`,
    );
  }
  return res.json() as Promise<T>;
}
