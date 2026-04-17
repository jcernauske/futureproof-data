const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

type FastAPIValidationError = { loc: (string | number)[]; msg: string; type: string };

function formatErrorDetail(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown })?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((e) => {
        const err = e as FastAPIValidationError;
        const loc = Array.isArray(err.loc) ? err.loc.slice(1).join(".") : "";
        return loc ? `${loc}: ${err.msg}` : err.msg;
      })
      .filter(Boolean)
      .join("; ") || `API error: ${status}`;
  }
  return `API error: ${status}`;
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const parsed = await res.json().catch(() => ({}));
    throw new Error(formatErrorDetail(parsed, res.status));
  }
  return res.json() as Promise<T>;
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const parsed = await res.json().catch(() => ({}));
    throw new Error(formatErrorDetail(parsed, res.status));
  }
  return res.json() as Promise<T>;
}
