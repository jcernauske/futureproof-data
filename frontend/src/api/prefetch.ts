/**
 * Build prefetch API. Fires speculative stat-engine + branches + career
 * description computation on /set-your-course so /build/stream can skip
 * the blocking compute phase.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export interface PrefetchParams {
  unitid: number;
  cipcode: string;
  soc_code: string;
  occupation_title: string | null;
  effort: string;
  loan_pct: number;
  student_major: string | null;
  student_cip: string | null;
  intent_keywords: string[];
  home_state: string | null;
}

export async function requestPrefetch(
  params: PrefetchParams,
  signal?: AbortSignal,
): Promise<void> {
  try {
    await fetch(`${API_BASE}/build/prefetch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
      signal,
    });
  } catch {
    // Fire-and-forget — prefetch failure is not user-visible
  }
}
