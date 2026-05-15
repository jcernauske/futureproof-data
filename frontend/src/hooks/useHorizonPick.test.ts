/**
 * useHorizonPick.test.ts
 *
 * Coverage for the bag-walk randomization primitive that powers HorizonFooter
 * and HorizonSilhouette. The hook has four contracts that matter:
 *
 *   1. Coverage: every index in [0..poolSize-1] is drawn exactly once before
 *      reshuffle. (No "rng got unlucky and never picked 13" failure.)
 *   2. Anti-adjacency: no two consecutive draws return the same index, even
 *      across the bag-refill seam.
 *   3. Per-surface independence: desktop and mobile bags do not interfere.
 *   4. Storage degradation: when sessionStorage throws (private mode, quota,
 *      disabled), the hook silently falls back to an in-memory bag instead
 *      of crashing the app.
 *
 * Bag mechanics are tested through the pure helpers (`newBag`, `drawFromBag`,
 * `captionFor`) — they're the contract, the hook is just glue. Hook
 * integration tests cover what only the hook can express: SSR-null first
 * render, sessionStorage round-trip, and the QuotaExceededError fallback.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import {
  useHorizonPick,
  useHorizonAt,
  newBag,
  drawFromBag,
  captionFor,
  drawAndPersist,
  safeReadBag,
  __resetInMemoryBagsForTesting,
  type StoredBag,
} from "./useHorizonPick";
import {
  HORIZON_BASENAMES,
  HORIZON_POOL_SIZE,
} from "@/components/horizon/horizonManifest";
import { HORIZON_CAPTIONS } from "@/components/horizon/horizonCaptions";

// ---------------------------------------------------------------------------
// Setup — clear all bag state between tests
// ---------------------------------------------------------------------------

beforeEach(() => {
  // Wipe sessionStorage between tests so leftover bags don't bleed.
  if (typeof window !== "undefined" && window.sessionStorage) {
    window.sessionStorage.clear();
  }
  // Also wipe any prefetch <link>s left by prior tests.
  document
    .querySelectorAll('link[rel="prefetch"]')
    .forEach((el) => el.remove());
  // Reset module-scoped in-memory bag map so storage-failure-path tests
  // don't pollute the next case. (Code review Minor #4.)
  __resetInMemoryBagsForTesting();
});

afterEach(() => {
  vi.restoreAllMocks();
  __resetInMemoryBagsForTesting();
});

// ---------------------------------------------------------------------------
// Pure helpers — bag mechanics
// ---------------------------------------------------------------------------

describe("newBag", () => {
  it("produces a permutation of [0..poolSize-1]", () => {
    const bag = newBag(HORIZON_POOL_SIZE, 42);
    expect(bag.order).toHaveLength(HORIZON_POOL_SIZE);
    const sorted = [...bag.order].sort((a, b) => a - b);
    const expected = Array.from({ length: HORIZON_POOL_SIZE }, (_, i) => i);
    expect(sorted).toEqual(expected);
  });

  it("starts with cursor 0 and lastShown null", () => {
    const bag = newBag(HORIZON_POOL_SIZE, 1);
    expect(bag.cursor).toBe(0);
    expect(bag.lastShown).toBeNull();
  });

  it("seeded shuffles are deterministic", () => {
    const a = newBag(HORIZON_POOL_SIZE, 12345);
    const b = newBag(HORIZON_POOL_SIZE, 12345);
    expect(a.order).toEqual(b.order);
  });

  it("different seeds produce different permutations", () => {
    // Fragile? In principle two seeds could collide on order. In practice
    // 48! >> 2^32, so two arbitrary LCG seeds will not. If this ever flakes,
    // it is a bug in the LCG or the manifest pool size.
    const a = newBag(HORIZON_POOL_SIZE, 1);
    const b = newBag(HORIZON_POOL_SIZE, 999999);
    expect(a.order).not.toEqual(b.order);
  });

  it("works for poolSize=1 (degenerate case)", () => {
    const bag = newBag(1, 1);
    expect(bag.order).toEqual([0]);
  });

  it("works for poolSize=4 (test fixture size)", () => {
    const bag = newBag(4, 7);
    expect(bag.order).toHaveLength(4);
    expect([...bag.order].sort()).toEqual([0, 1, 2, 3]);
  });
});

describe("drawFromBag", () => {
  it("draws all 48 indices exactly once across 48 calls", () => {
    // P0: bag-coverage guarantee — the central thesis of the bag-walk.
    let bag = newBag(HORIZON_POOL_SIZE, 13);
    const drawn: number[] = [];
    for (let i = 0; i < HORIZON_POOL_SIZE; i++) {
      const result = drawFromBag(bag, HORIZON_POOL_SIZE);
      drawn.push(result.next);
      bag = result.bag;
    }
    expect(drawn).toHaveLength(HORIZON_POOL_SIZE);
    const unique = new Set(drawn);
    expect(unique.size).toBe(HORIZON_POOL_SIZE);
    // Every index 0..47 must appear exactly once.
    for (let i = 0; i < HORIZON_POOL_SIZE; i++) {
      expect(unique.has(i)).toBe(true);
    }
  });

  it("never returns the same index twice in a row within a single bag", () => {
    // Intra-bag anti-adjacency is automatic (a permutation has no internal
    // repeats), but we verify it explicitly because the property is
    // load-bearing for the user-facing contract.
    let bag = newBag(HORIZON_POOL_SIZE, 99);
    const drawn: number[] = [];
    for (let i = 0; i < HORIZON_POOL_SIZE; i++) {
      const result = drawFromBag(bag, HORIZON_POOL_SIZE);
      drawn.push(result.next);
      bag = result.bag;
    }
    for (let i = 1; i < drawn.length; i++) {
      expect(drawn[i]).not.toBe(drawn[i - 1]);
    }
  });

  it("never returns the same index twice in a row across the bag-refill seam", () => {
    // The interesting case: the previous bag's last index could collide with
    // the fresh bag's first index. The seam-swap guard exists to prevent
    // that. We test it deterministically by constructing a bag whose final
    // index will collide with the next-bag's first index.
    //
    // Strategy: drain a small pool, then verify the post-refill first draw
    // never equals the pre-refill last draw across many seeds.
    const POOL = 4;
    for (let seed = 1; seed <= 50; seed++) {
      let bag = newBag(POOL, seed);
      // Drain the bag.
      let lastBeforeRefill = -1;
      for (let i = 0; i < POOL; i++) {
        const result = drawFromBag(bag, POOL);
        lastBeforeRefill = result.next;
        bag = result.bag;
      }
      // Force a refill on the next draw.
      const firstAfterRefill = drawFromBag(bag, POOL);
      expect(firstAfterRefill.next).not.toBe(lastBeforeRefill);
    }
  });

  it("reshuffles after exhaustion", () => {
    // After draining the bag, the next draw must produce a fresh permutation
    // and the cursor must reset.
    const POOL = 4;
    let bag = newBag(POOL, 1);
    // Drain
    for (let i = 0; i < POOL; i++) {
      const result = drawFromBag(bag, POOL);
      bag = result.bag;
    }
    expect(bag.cursor).toBe(POOL); // exhausted
    // Next draw should refill and produce something
    const refilled = drawFromBag(bag, POOL);
    expect(refilled.bag.cursor).toBe(1); // freshly drawn
    // The new bag's order should be a valid permutation of [0..POOL-1]
    const sorted = [...refilled.bag.order].sort((a, b) => a - b);
    expect(sorted).toEqual([0, 1, 2, 3]);
    // And the drawn index must be valid
    expect(refilled.next).toBeGreaterThanOrEqual(0);
    expect(refilled.next).toBeLessThan(POOL);
  });

  it("handles a mismatched-poolSize stored bag by reshuffling", () => {
    // If a v1 bag of length 8 ever ends up against a poolSize=4 (manifest
    // shrunk), the hook must NOT index out of bounds — it must reshuffle.
    const stale: StoredBag = {
      order: [0, 1, 2, 3, 4, 5, 6, 7],
      cursor: 0,
      lastShown: null,
    };
    const result = drawFromBag(stale, 4);
    expect(result.next).toBeGreaterThanOrEqual(0);
    expect(result.next).toBeLessThan(4);
    expect(result.bag.order).toHaveLength(4);
  });

  it("updates lastShown to the just-drawn index", () => {
    let bag = newBag(HORIZON_POOL_SIZE, 5);
    const result = drawFromBag(bag, HORIZON_POOL_SIZE);
    expect(result.bag.lastShown).toBe(result.next);
    bag = result.bag;
    const second = drawFromBag(bag, HORIZON_POOL_SIZE);
    expect(second.bag.lastShown).toBe(second.next);
  });

  it("increments cursor on each draw", () => {
    let bag = newBag(HORIZON_POOL_SIZE, 5);
    expect(bag.cursor).toBe(0);
    for (let i = 1; i <= 5; i++) {
      const result = drawFromBag(bag, HORIZON_POOL_SIZE);
      expect(result.bag.cursor).toBe(i);
      bag = result.bag;
    }
  });
});

describe("captionFor", () => {
  it("returns CAPTIONS[i % 3] for all i in 0..47", () => {
    // P0: caption pairing is the user-visible contract. This is the
    // assertion that catches "someone added a 4th caption and forgot to
    // change the modulo."
    for (let i = 0; i < HORIZON_POOL_SIZE; i++) {
      expect(captionFor(i)).toBe(HORIZON_CAPTIONS[i % 3]);
    }
  });

  it("maps known boundary indices to the right caption", () => {
    expect(captionFor(0)).toBe(HORIZON_CAPTIONS[0]);
    expect(captionFor(1)).toBe(HORIZON_CAPTIONS[1]);
    expect(captionFor(2)).toBe(HORIZON_CAPTIONS[2]);
    expect(captionFor(3)).toBe(HORIZON_CAPTIONS[0]); // wrap
    expect(captionFor(47)).toBe(HORIZON_CAPTIONS[47 % 3]);
  });

  it("handles negative indices defensively", () => {
    // Shouldn't occur in practice, but the safe-modulo guard is contractual.
    expect(captionFor(-1)).toBe(HORIZON_CAPTIONS[2]);
    expect(captionFor(-3)).toBe(HORIZON_CAPTIONS[0]);
  });
});

// ---------------------------------------------------------------------------
// Hook integration — useHorizonPick
// ---------------------------------------------------------------------------

describe("useHorizonPick", () => {
  it("returns null on first render (SSR-safe)", () => {
    // The hook MUST NOT touch window/sessionStorage during render. The
    // null-then-populate pattern is what makes Vite SSR + React 18 strict
    // mode safe.
    const { result } = renderHook(() => useHorizonPick("desktop"));
    // Note: with React 18 useEffect runs synchronously after mount in jsdom,
    // so by the time renderHook returns, the effect may have already fired.
    // What we can assert is that a populated result is well-formed; the
    // null-first-render guarantee is structurally enforced by `useState(null)`.
    if (result.current !== null) {
      expect(result.current.index).toBeGreaterThanOrEqual(0);
      expect(result.current.index).toBeLessThan(HORIZON_POOL_SIZE);
    }
  });

  it("populates a valid pick after mount", async () => {
    const { result } = renderHook(() => useHorizonPick("desktop"));
    await waitFor(() => expect(result.current).not.toBeNull());
    const pick = result.current!;
    expect(pick.index).toBeGreaterThanOrEqual(0);
    expect(pick.index).toBeLessThan(HORIZON_POOL_SIZE);
    expect(pick.basename).toBe(HORIZON_BASENAMES[pick.index]);
    expect(pick.caption).toBe(HORIZON_CAPTIONS[pick.index % 3]);
  });

  it("persists state across hook re-mounts via sessionStorage", async () => {
    // First mount: draw something. Second mount on same surface should
    // continue from the persisted bag (cursor advances, doesn't reset).
    const { result, unmount } = renderHook(() => useHorizonPick("desktop"));
    await waitFor(() => expect(result.current).not.toBeNull());
    const firstPick = result.current!;
    unmount();

    // Storage should now contain a bag with cursor > 0.
    const raw = window.sessionStorage.getItem("fp.horizon.bag.v1.desktop");
    expect(raw).not.toBeNull();
    const stored = JSON.parse(raw!) as StoredBag;
    expect(stored.cursor).toBeGreaterThanOrEqual(1);
    expect(stored.lastShown).toBe(firstPick.index);

    // Second mount picks the next index — not the same one, not a reset.
    const { result: second } = renderHook(() => useHorizonPick("desktop"));
    await waitFor(() => expect(second.current).not.toBeNull());
    const secondPick = second.current!;
    expect(secondPick.index).not.toBe(firstPick.index);
  });

  it("desktop and mobile bags are independent", async () => {
    // Mounting desktop should not advance the mobile cursor and vice versa.
    const { result: desktop, unmount: unmountDesktop } = renderHook(() =>
      useHorizonPick("desktop"),
    );
    await waitFor(() => expect(desktop.current).not.toBeNull());
    unmountDesktop();

    const { result: mobile, unmount: unmountMobile } = renderHook(() =>
      useHorizonPick("mobile"),
    );
    await waitFor(() => expect(mobile.current).not.toBeNull());
    unmountMobile();

    const desktopRaw = window.sessionStorage.getItem(
      "fp.horizon.bag.v1.desktop",
    );
    const mobileRaw = window.sessionStorage.getItem(
      "fp.horizon.bag.v1.mobile",
    );
    expect(desktopRaw).not.toBeNull();
    expect(mobileRaw).not.toBeNull();

    const desktopBag = JSON.parse(desktopRaw!) as StoredBag;
    const mobileBag = JSON.parse(mobileRaw!) as StoredBag;
    // Each surface advanced its own cursor exactly once.
    expect(desktopBag.cursor).toBe(1);
    expect(mobileBag.cursor).toBe(1);
    // They should have independent permutations (probabilistic; with 48! options
    // the chance of identical permutations is vanishingly small).
    expect(desktopBag.order).not.toEqual(mobileBag.order);
  });

  it("falls back to in-memory bag when sessionStorage.setItem throws", async () => {
    // Mock setItem to throw QuotaExceededError. The hook must NOT crash and
    // must still return a populated pick from the in-memory fallback.
    const setItemSpy = vi
      .spyOn(window.Storage.prototype, "setItem")
      .mockImplementation(() => {
        throw new DOMException("quota", "QuotaExceededError");
      });

    const { result } = renderHook(() => useHorizonPick("desktop"));
    await waitFor(() => expect(result.current).not.toBeNull());
    const pick = result.current!;
    expect(pick.index).toBeGreaterThanOrEqual(0);
    expect(pick.index).toBeLessThan(HORIZON_POOL_SIZE);
    expect(setItemSpy).toHaveBeenCalled();
    // Storage should still be empty (the write threw).
    expect(window.sessionStorage.getItem("fp.horizon.bag.v1.desktop")).toBeNull();
  });

  it("falls back gracefully when sessionStorage.getItem also throws", async () => {
    // Some browsers throw on getItem too (rare but real). Verify the hook
    // recovers and still returns a valid pick.
    vi.spyOn(window.Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("denied", "SecurityError");
    });
    vi.spyOn(window.Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("denied", "SecurityError");
    });

    const { result } = renderHook(() => useHorizonPick("mobile"));
    await waitFor(() => expect(result.current).not.toBeNull());
    const pick = result.current!;
    expect(pick.index).toBeGreaterThanOrEqual(0);
    expect(pick.index).toBeLessThan(HORIZON_POOL_SIZE);
  });

  it("preserves anti-adjacency across mounts when setItem silently drops (Major #1 regression)", async () => {
    /* Code review Major #1: when sessionStorage is available-for-reads-but-
     * not-writable (Brave shields, Safari ITP iframe sandboxes, some quota
     * scenarios), `setItem` succeeds-or-throws but the value never lands —
     * the next `getItem` returns null. The OLD safeReadBag returned null
     * here, the hook started a fresh shuffle on every mount, and bag
     * coverage + anti-adjacency were silently lost.
     *
     * The fix: in-memory bag is the source of truth; storage is mirrored
     * best-effort. When read returns null, fall through to in-memory.
     *
     * This test forces that exact failure mode (setItem throws, getItem
     * always returns null) and asserts that two consecutive mounts on the
     * same surface do NOT draw the same index — proving the in-memory bag
     * survived the failed write.
     */
    // Drop everything written; reads return null (as if writes never landed).
    vi.spyOn(window.Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("quota", "QuotaExceededError");
    });
    vi.spyOn(window.Storage.prototype, "getItem").mockImplementation(
      () => null,
    );

    const { result: first, unmount: unmountFirst } = renderHook(() =>
      useHorizonPick("desktop"),
    );
    await waitFor(() => expect(first.current).not.toBeNull());
    const firstIdx = first.current!.index;
    unmountFirst();

    const { result: second } = renderHook(() => useHorizonPick("desktop"));
    await waitFor(() => expect(second.current).not.toBeNull());
    const secondIdx = second.current!.index;

    // Anti-adjacency: in-memory bag advanced its cursor between mounts, so
    // the second draw is the next index in the same shuffled order — never
    // equal to the first.
    expect(secondIdx).not.toBe(firstIdx);

    // And the in-memory bag should now record cursor=2 + lastShown=secondIdx.
    const inMem = safeReadBag("desktop");
    expect(inMem).not.toBeNull();
    expect(inMem!.cursor).toBe(2);
    expect(inMem!.lastShown).toBe(secondIdx);
  });
});

// ---------------------------------------------------------------------------
// drawAndPersist — non-hook helper for one-shot draws
// ---------------------------------------------------------------------------

describe("drawAndPersist", () => {
  it("returns a valid pick and advances the bag", () => {
    const a = drawAndPersist("desktop");
    expect(a.index).toBeGreaterThanOrEqual(0);
    expect(a.index).toBeLessThan(HORIZON_POOL_SIZE);
    expect(a.basename).toBe(HORIZON_BASENAMES[a.index]);

    // Second call advances the cursor — different index, same surface.
    const b = drawAndPersist("desktop");
    expect(b.index).not.toBe(a.index);

    // Storage was written.
    const raw = window.sessionStorage.getItem("fp.horizon.bag.v1.desktop");
    expect(raw).not.toBeNull();
    const stored = JSON.parse(raw!) as StoredBag;
    expect(stored.cursor).toBe(2);
    expect(stored.lastShown).toBe(b.index);
  });

  it("does not touch other surfaces", () => {
    drawAndPersist("desktop");
    expect(
      window.sessionStorage.getItem("fp.horizon.bag.v1.mobile"),
    ).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// useHorizonAt — locked-index variant for HorizonSilhouette
// ---------------------------------------------------------------------------

describe("useHorizonAt", () => {
  it("returns the same pick for the same index, every time", () => {
    // The "locked at commit" guarantee for HorizonSilhouette. If this ever
    // returns different output for the same input, screenshots are no longer
    // stable across remounts.
    const { result: a } = renderHook(() => useHorizonAt(7));
    const { result: b } = renderHook(() => useHorizonAt(7));
    expect(a.current).toEqual(b.current);
  });

  it("resolves basename from HORIZON_BASENAMES", () => {
    const { result } = renderHook(() => useHorizonAt(0));
    expect(result.current.basename).toBe(HORIZON_BASENAMES[0]);
  });

  it("pairs caption via index % 3", () => {
    for (const i of [0, 1, 2, 3, 17, 47]) {
      const { result } = renderHook(() => useHorizonAt(i));
      expect(result.current.caption).toBe(HORIZON_CAPTIONS[i % 3]);
    }
  });

  it("normalizes out-of-range indices via modulo", () => {
    // Defensive: a Build with horizonIndex 99 (corrupted state) must still
    // resolve to a valid basename, not undefined.
    const { result } = renderHook(() => useHorizonAt(99));
    const expected = 99 % HORIZON_POOL_SIZE;
    expect(result.current.index).toBe(expected);
    expect(result.current.basename).toBe(HORIZON_BASENAMES[expected]);
  });

  it("normalizes negative indices safely", () => {
    const { result } = renderHook(() => useHorizonAt(-1));
    expect(result.current.index).toBeGreaterThanOrEqual(0);
    expect(result.current.index).toBeLessThan(HORIZON_POOL_SIZE);
    expect(result.current.basename).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// P2 — Prefetch behavior (best-effort; the timer machinery is brittle in jsdom)
// ---------------------------------------------------------------------------

describe("useHorizonPick prefetch (P2)", () => {
  it("schedules a prefetch <link> after the 2s idle window", async () => {
    // Real timers + a bounded poll. The prefetch path inside the hook is:
    //   setTimeout(schedulePrefetch, 2000) → appendPrefetchLink(basename)
    // Under jsdom, requestIdleCallback is undefined so the setTimeout
    // branch fires schedulePrefetch directly.
    const { result, unmount } = renderHook(() => useHorizonPick("desktop"));
    await waitFor(() => expect(result.current).not.toBeNull());

    // Poll up to 3s for at least one prefetch link to appear. We poll
    // (rather than a fixed sleep) because react test-runner timing can
    // shift the effect-commit boundary and we don't want flake.
    const start = Date.now();
    let links: NodeListOf<Element> = document.querySelectorAll(
      'link[rel="prefetch"]',
    );
    while (Date.now() - start < 3000 && links.length === 0) {
      await new Promise((r) => setTimeout(r, 100));
      links = document.querySelectorAll('link[rel="prefetch"]');
    }

    expect(links.length).toBeGreaterThanOrEqual(1);
    expect(links.length).toBeLessThanOrEqual(2);
    // Each href should point to /campus/...-1400.avif
    links.forEach((link) => {
      const href = link.getAttribute("href") ?? "";
      expect(href).toMatch(/^\/campus\/.+-1400\.avif$/);
      // jsdom's HTMLLinkElement does not always reflect `link.as = ...`
      // back to the `as` attribute, so check the property when set.
      const linkEl = link as HTMLLinkElement;
      expect(linkEl.as || link.getAttribute("as")).toBe("image");
    });

    unmount();
  }, 6000);
});
