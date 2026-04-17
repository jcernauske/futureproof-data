/**
 * wrapped.test.ts — Tests for the wrapped API client's mock mode.
 *
 * Mock mode (VITE_USE_MOCK_API=true) returns 6 placeholder frames
 * with inline SVG data URIs. This test pins the mock's contract:
 * - Exactly 6 frames, indices 0..5, none missing, none duplicated
 * - Each frame's url is a non-empty data URI
 * - Render response has status="ok" and frame_count=6
 *
 * These tests exercise the MOCK functions directly (not via the
 * live/mock switch), so we don't need env-var manipulation.
 */

import { describe, it, expect } from "vitest";
import { mockGetWrapped, mockRenderWrapped } from "./mockWrapped";

describe("mockGetWrapped", () => {
  it("returns exactly 6 frames", async () => {
    const res = await mockGetWrapped("any-build-id");
    expect(res.frames).toHaveLength(6);
  });

  it("each frame has an index matching its position (0..5)", async () => {
    const res = await mockGetWrapped("any-build-id");
    res.frames.forEach((frame, i) => {
      expect(frame.index).toBe(i);
    });
  });

  it("frame indices are 0 through 5 exactly (no gaps, no dupes)", async () => {
    const res = await mockGetWrapped("any-build-id");
    const indices = res.frames.map((f) => f.index).sort();
    expect(indices).toEqual([0, 1, 2, 3, 4, 5]);
  });

  it("each frame's url is a data URI starting with data:image/svg+xml;base64,", async () => {
    const res = await mockGetWrapped("any-build-id");
    res.frames.forEach((frame) => {
      expect(frame.url).toMatch(/^data:image\/svg\+xml;base64,/);
    });
  });

  it("each frame's url is a non-empty data URI", async () => {
    const res = await mockGetWrapped("any-build-id");
    res.frames.forEach((frame) => {
      // The base64 payload after the comma must be non-empty
      const [, payload] = frame.url.split(",");
      expect(payload).toBeDefined();
      expect(payload!.length).toBeGreaterThan(0);
    });
  });

  it("returned data URIs decode back to valid SVG text", async () => {
    /* Regression guard: if the base64 encoding broke, the <img> in
     * WrappedFrame.tsx would silently render a broken-image icon. We
     * decode here to make sure the URI contains what we expect. */
    const res = await mockGetWrapped("any-build-id");
    for (const frame of res.frames) {
      const [, payload] = frame.url.split(",");
      if (!payload) throw new Error("mock frame url has no base64 payload");
      // atob may not exist in some Node runtimes; fall back to Buffer
      const decoded =
        typeof atob === "function"
          ? atob(payload)
          : Buffer.from(payload, "base64").toString("utf-8");
      expect(decoded).toContain("<svg");
      expect(decoded).toContain("</svg>");
    }
  });

  it("each frame's data URI is unique (different placeholder per frame)", async () => {
    /* If all six frames had the same URL, the viewer would look
     * broken even though it technically had "6 frames." */
    const res = await mockGetWrapped("any-build-id");
    const urls = new Set(res.frames.map((f) => f.url));
    expect(urls.size).toBe(6);
  });

  it("ignores the passed buildId (the mock is build-agnostic)", async () => {
    const a = await mockGetWrapped("build-a");
    const b = await mockGetWrapped("build-b");
    expect(a.frames.map((f) => f.index)).toEqual(b.frames.map((f) => f.index));
  });
});

describe("mockRenderWrapped", () => {
  it("returns {status:'ok', frame_count:6}", async () => {
    const res = await mockRenderWrapped();
    expect(res).toEqual({ status: "ok", frame_count: 6 });
  });

  it("returns 'ok' status (never 'cached') in mock mode", async () => {
    /* The real backend uses "cached" when frames exist; the mock
     * always re-renders (there's no cache), so status is always "ok".
     * If this flips, the SaveWrappedScreen mock-mode flow would lose
     * a phase transition. */
    const r1 = await mockRenderWrapped();
    const r2 = await mockRenderWrapped();
    expect(r1.status).toBe("ok");
    expect(r2.status).toBe("ok");
  });

  it("always returns 6 as the frame_count", async () => {
    const res = await mockRenderWrapped();
    expect(res.frame_count).toBe(6);
  });
});
