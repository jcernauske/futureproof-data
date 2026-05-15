/**
 * useHorizonPick — Horizon image bag-walk hook.
 *
 * Returns a random horizon pick on every mount and route change. Uses a
 * shuffled-bag walk persisted in sessionStorage with anti-adjacency.
 * Per-surface bags so desktop/mobile draw independently.
 *
 * SSR-safe: returns null on the first render, populates after mount.
 * Degrades to in-memory bag if sessionStorage is unavailable.
 *
 * Side effect (only on the draw-fresh hook, not on `useHorizonAt`):
 * triggers `<link rel="prefetch">` for the next 2 indices in the bag
 * after a 2s idle window.
 */

import { useEffect, useRef, useState } from "react";
import {
  HORIZON_BASENAMES,
  HORIZON_POOL_SIZE,
} from "@/components/horizon/horizonManifest";
import { HORIZON_CAPTIONS } from "@/components/horizon/horizonCaptions";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type HorizonSurface = "desktop" | "mobile";

export interface HorizonPick {
  /** Index into HORIZON_BASENAMES, 0..HORIZON_POOL_SIZE-1 inclusive. */
  index: number;
  /** Resolved basename, e.g. 'jcern_Flat_orthographic_..._0'. */
  basename: string;
  /** Caption paired with this index via index % 3. */
  caption: string;
}

export interface StoredBag {
  /** Permutation of [0..poolSize-1]. */
  order: number[];
  /** Next index to draw from `order`, in [0..poolSize]. */
  cursor: number;
  /** Most recently shown index, for anti-adjacency on bag refill. */
  lastShown: number | null;
}

// ---------------------------------------------------------------------------
// Storage helpers
// ---------------------------------------------------------------------------

const STORAGE_KEY_PREFIX = "fp.horizon.bag.v1.";

/**
 * In-memory bag — the source of truth. We always write here on every update,
 * then *try* to mirror the write to sessionStorage. Reads consult storage
 * first (so a fresh tab continues from a prior session if the browser allows
 * it), but fall through to the in-memory copy whenever storage doesn't hand
 * us back a usable bag — including the "available-for-reads-but-not-writes"
 * case (Brave shields / Safari ITP iframe sandboxes) where `getItem` returns
 * null because the prior `setItem` silently dropped on the floor.
 *
 * Code review Major #1: previous implementation only consulted in-memory
 * when storage *threw*; now we consult it whenever storage returns null,
 * so anti-adjacency and coverage survive read-after-failed-write.
 */
const inMemoryBags: Map<HorizonSurface, StoredBag> = new Map();

function storageKey(surface: HorizonSurface): string {
  return `${STORAGE_KEY_PREFIX}${surface}`;
}

export function safeReadBag(surface: HorizonSurface): StoredBag | null {
  // sessionStorage path — best effort.
  try {
    if (typeof window !== "undefined" && window.sessionStorage) {
      const raw = window.sessionStorage.getItem(storageKey(surface));
      if (raw) {
        const parsed = JSON.parse(raw) as StoredBag;
        if (
          parsed &&
          Array.isArray(parsed.order) &&
          parsed.order.length === HORIZON_POOL_SIZE &&
          typeof parsed.cursor === "number"
        ) {
          return parsed;
        }
      }
      // Fall through: storage was readable but had no bag for this surface.
      // The in-memory bag may have a more recent state if a prior write
      // silently failed (quota exceeded, sandboxed iframe, etc.).
    }
  } catch {
    // Storage threw (private mode / quota / disabled) — fall through.
  }
  return inMemoryBags.get(surface) ?? null;
}

export function safeWriteBag(surface: HorizonSurface, bag: StoredBag): void {
  // ALWAYS write to in-memory first — it's the source of truth. Then mirror
  // to sessionStorage as a best-effort cross-mount cache.
  inMemoryBags.set(surface, bag);
  try {
    if (typeof window !== "undefined" && window.sessionStorage) {
      window.sessionStorage.setItem(storageKey(surface), JSON.stringify(bag));
    }
  } catch {
    // Storage threw — the in-memory copy is already updated, so the bag
    // walk continues uninterrupted within this session.
  }
}

/**
 * Test-only: clear the module-scoped in-memory bag map between vitest cases.
 * Public to test files via the underscore-prefix convention; do NOT call from
 * production code. (Code review Minor #4.)
 */
export function __resetInMemoryBagsForTesting(): void {
  inMemoryBags.clear();
}

// ---------------------------------------------------------------------------
// Pure helpers
// ---------------------------------------------------------------------------

/**
 * Random number in [0, 1). Uses crypto.getRandomValues when available,
 * falls back to Math.random otherwise. Optional integer seed bypasses
 * randomness entirely for deterministic tests via a tiny LCG.
 */
function randomFloat(seedRef?: { value: number }): number {
  if (seedRef) {
    // Park-Miller LCG, deterministic for tests.
    seedRef.value = (seedRef.value * 16807) % 2147483647;
    return (seedRef.value & 0x7fffffff) / 2147483647;
  }
  if (
    typeof globalThis !== "undefined" &&
    typeof globalThis.crypto !== "undefined" &&
    typeof globalThis.crypto.getRandomValues === "function"
  ) {
    const buf = new Uint32Array(1);
    globalThis.crypto.getRandomValues(buf);
    const sample = buf[0] ?? 0;
    return sample / 0x100000000;
  }
  return Math.random();
}

/**
 * Pure helper: builds a fresh shuffled bag with a Fisher-Yates shuffle.
 * Seeded for deterministic tests; defaults to crypto.getRandomValues.
 */
export function newBag(poolSize: number, seed?: number): StoredBag {
  const order: number[] = Array.from({ length: poolSize }, (_, i) => i);
  const seedRef = seed !== undefined ? { value: Math.max(1, seed) } : undefined;
  for (let i = order.length - 1; i > 0; i--) {
    const j = Math.floor(randomFloat(seedRef) * (i + 1));
    // After construction above, both indices are guaranteed to be defined.
    const a = order[i] as number;
    const b = order[j] as number;
    order[i] = b;
    order[j] = a;
  }
  return { order, cursor: 0, lastShown: null };
}

/**
 * Pure helper: draws the next index from a bag without persistence.
 * Returns the drawn index plus the updated bag. If the bag was exhausted
 * (cursor === poolSize), it is reshuffled before draw, and anti-adjacency
 * swaps the first index with the second when the fresh bag's first item
 * would equal the prior `lastShown`.
 */
export function drawFromBag(
  bag: StoredBag,
  poolSize: number,
): { next: number; bag: StoredBag } {
  let order = bag.order;
  let cursor = bag.cursor;
  const lastShown = bag.lastShown;

  // Refill if exhausted or invalid
  if (cursor >= order.length || order.length !== poolSize) {
    const refreshed = newBag(poolSize);
    order = refreshed.order;
    cursor = 0;
    // Anti-adjacency at the seam: if the new bag's first index matches the
    // most recently shown one, swap with the second index when possible.
    if (
      lastShown !== null &&
      order.length > 1 &&
      order[0] === lastShown
    ) {
      const first = order[0] as number;
      const second = order[1] as number;
      order[0] = second;
      order[1] = first;
    }
  }

  const next = order[cursor] as number;
  const updated: StoredBag = {
    order,
    cursor: cursor + 1,
    lastShown: next,
  };
  return { next, bag: updated };
}

/**
 * Maps a horizon index to its paired caption via index % 3.
 */
export function captionFor(index: number): string {
  const len = HORIZON_CAPTIONS.length;
  // Safe modulo for negative indices (shouldn't occur, but be defensive).
  const normalized = ((index % len) + len) % len;
  return HORIZON_CAPTIONS[normalized] as string;
}

// ---------------------------------------------------------------------------
// Prefetch
// ---------------------------------------------------------------------------

/**
 * Append `<link rel="prefetch">` for the AVIF-1400 of a given basename.
 * Returns the inserted link element (or null if a duplicate already exists,
 * or if document is unavailable). Callers track the returned element so it
 * can be removed in the effect cleanup — preventing unbounded DOM growth
 * across SPA navigation. (Code review Minor #3.)
 */
function appendPrefetchLink(basename: string): HTMLLinkElement | null {
  if (typeof document === "undefined") return null;
  const href = `/campus/${encodeURIComponent(basename)}-1400.avif`;
  // Avoid duplicates within the same document.
  const existing = document.querySelector(
    `link[rel="prefetch"][href="${href}"]`,
  );
  if (existing) return null;
  const link = document.createElement("link");
  link.rel = "prefetch";
  link.as = "image";
  link.href = href;
  document.head.appendChild(link);
  return link;
}

/**
 * Pure helper for non-hook callers that need a one-shot draw without
 * subscribing to the hook's mount-time effect. Reads the bag, draws once,
 * persists, and returns the pick. Use this when the draw is conditional on
 * external state (e.g. "only if horizonIndex is unset") — the hook's auto-
 * effect would otherwise fire on every mount and advance the surface's bag
 * even when the result is then discarded.
 */
export function drawAndPersist(surface: HorizonSurface): HorizonPick {
  const existing = safeReadBag(surface) ?? newBag(HORIZON_POOL_SIZE);
  const { next, bag: updated } = drawFromBag(existing, HORIZON_POOL_SIZE);
  safeWriteBag(surface, updated);
  return {
    index: next,
    basename: HORIZON_BASENAMES[next] as string,
    caption: captionFor(next),
  };
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

/**
 * Returns a random horizon pick on every mount and route change.
 * SSR-safe: returns null on first render, populates after mount.
 */
export function useHorizonPick(surface: HorizonSurface): HorizonPick | null {
  const [pick, setPick] = useState<HorizonPick | null>(null);
  // Track prefetch <link> elements we appended so cleanup can remove them.
  // Without this, repeated mounts (SPA route changes, StrictMode double-mount
  // in dev) would leak <link> nodes into <head>. (Code review Minor #3.)
  const prefetchLinksRef = useRef<HTMLLinkElement[]>([]);

  useEffect(() => {
    let cancelled = false;

    const existing = safeReadBag(surface) ?? newBag(HORIZON_POOL_SIZE);
    const { next, bag: updated } = drawFromBag(existing, HORIZON_POOL_SIZE);
    safeWriteBag(surface, updated);

    if (cancelled) return;

    const drawn: HorizonPick = {
      index: next,
      basename: HORIZON_BASENAMES[next] as string,
      caption: captionFor(next),
    };
    setPick(drawn);

    // Schedule a 2s idle prefetch for the next 2 bag indices.
    let idleHandle: number | null = null;
    let timeoutHandle: number | null = null;
    const schedulePrefetch = () => {
      if (cancelled) return;
      const peek = safeReadBag(surface);
      if (!peek) return;
      // Peek ahead 2 indices without mutating storage.
      const upcoming: number[] = [];
      let cursor = peek.cursor;
      const order = peek.order;
      for (let i = 0; i < 2; i++) {
        if (cursor >= order.length) {
          // Next bag would be a fresh shuffle — skip prefetch since
          // we don't know what it will be without writing it.
          break;
        }
        upcoming.push(order[cursor] as number);
        cursor += 1;
      }
      upcoming.forEach((idx) => {
        const basename = HORIZON_BASENAMES[idx];
        if (basename) {
          const link = appendPrefetchLink(basename);
          if (link) prefetchLinksRef.current.push(link);
        }
      });
    };

    const PREFETCH_DELAY_MS = 2000;
    if (typeof window !== "undefined") {
      const win = window as Window & {
        requestIdleCallback?: (cb: () => void) => number;
        cancelIdleCallback?: (h: number) => void;
      };
      if (typeof win.requestIdleCallback === "function") {
        timeoutHandle = window.setTimeout(() => {
          idleHandle = win.requestIdleCallback!(schedulePrefetch);
        }, PREFETCH_DELAY_MS);
      } else {
        timeoutHandle = window.setTimeout(schedulePrefetch, PREFETCH_DELAY_MS);
      }
    }

    return () => {
      cancelled = true;
      if (timeoutHandle !== null && typeof window !== "undefined") {
        window.clearTimeout(timeoutHandle);
      }
      if (idleHandle !== null && typeof window !== "undefined") {
        const win = window as Window & {
          cancelIdleCallback?: (h: number) => void;
        };
        if (typeof win.cancelIdleCallback === "function") {
          win.cancelIdleCallback(idleHandle);
        }
      }
      // Remove any prefetch <link>s we inserted so the head doesn't
      // accumulate orphan nodes across SPA navigation.
      const links = prefetchLinksRef.current;
      links.forEach((link) => {
        if (link.parentNode) link.parentNode.removeChild(link);
      });
      prefetchLinksRef.current = [];
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [surface]);

  return pick;
}

/**
 * Returns a stable horizon pick locked to a given index.
 * Used by HorizonSilhouette where the build's horizonIndex is fixed.
 * Does NOT trigger any prefetch or sessionStorage writes.
 */
export function useHorizonAt(index: number): HorizonPick {
  const len = HORIZON_POOL_SIZE;
  const safeIndex = ((Math.trunc(index) % len) + len) % len;
  return {
    index: safeIndex,
    basename: HORIZON_BASENAMES[safeIndex] as string,
    caption: captionFor(safeIndex),
  };
}
