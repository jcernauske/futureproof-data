/**
 * Wrapped (Screen 9) API client.
 *
 * Backend endpoints (backend/app/routers/wrapped.py):
 *   POST /build/{id}/wrapped/render   → RenderResponse
 *   GET  /build/{id}/wrapped          → WrappedResponse
 *   GET  /build/{id}/wrapped/{idx}    → PNG binary
 *
 * Frame PNGs are served relative to VITE_API_BASE_URL. The url field
 * on each frame is a relative path — getFrameUrl composes the full
 * URL for <img src> and download links.
 */

import { apiGet, apiPost } from "@/api/client";
import { mockGetWrapped, mockRenderWrapped } from "@/api/mockWrapped";

const USE_MOCK = import.meta.env.VITE_USE_MOCK_API === "true";

export interface WrappedFrameInfo {
  index: number;
  url: string;
}

export interface WrappedResponse {
  frames: WrappedFrameInfo[];
}

export interface RenderResponse {
  status: "ok" | "cached";
  frame_count: number;
}

export async function renderWrapped(buildId: string): Promise<RenderResponse> {
  if (USE_MOCK) return mockRenderWrapped();
  return apiPost<RenderResponse>(`/build/${buildId}/wrapped/render`);
}

export async function getWrapped(buildId: string): Promise<WrappedResponse> {
  if (USE_MOCK) return mockGetWrapped(buildId);
  const response = await apiGet<WrappedResponse>(`/build/${buildId}/wrapped`);
  // Backend returns relative URLs like "/build/.../wrapped/0". The frontend
  // runs on a different origin (Vite dev server vs FastAPI), so resolve
  // them to absolute URLs here — one consumer source of truth.
  const base =
    import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  return {
    frames: response.frames.map((f) => ({
      ...f,
      url: /^https?:/.test(f.url) ? f.url : `${base}${f.url}`,
    })),
  };
}

/**
 * Compose the absolute URL for a frame PNG.
 *
 * In real mode, this returns the API base + the server's path. In mock
 * mode, the mock URL is already absolute (data URI), so we pass it
 * through unchanged — the caller fetches it via getWrapped() and uses
 * the url field directly.
 */
export function getFrameUrl(buildId: string, frameIndex: number): string {
  if (USE_MOCK) {
    // Mock uses data URIs from getWrapped; callers should read .url
    // from the frame object rather than composing via this function.
    return "";
  }
  const base = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  return `${base}/build/${buildId}/wrapped/${frameIndex}`;
}
