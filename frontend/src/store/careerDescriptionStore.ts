import { fetchCareerDescription } from "@/api/careers";
import type { CareerDescription } from "@/types/build";

/**
 * SOC-keyed cache for CareerDescription with single-flight semantics.
 *
 * Mirrors the backend's `dict[(soc, prompt_version), asyncio.Future]`
 * single-flight pattern (feature-career-description-on-pdf.md §2 #13).
 * Concurrent sparkle clicks for the same hot SOC dedupe to one network
 * call. The resolved value is cached for instant reopens until the page
 * reloads.
 *
 * Failures don't cache: if a fetch rejects, the entry is evicted so a
 * later sparkle click can retry.
 */

const _resolved = new Map<string, CareerDescription>();
const _inflight = new Map<string, Promise<CareerDescription>>();

/**
 * Returns a cached `CareerDescription` synchronously, or null if not cached.
 */
export function getCachedCareerDescription(
  socCode: string,
): CareerDescription | null {
  return _resolved.get(socCode) ?? null;
}

/**
 * Fetch (or join an in-flight fetch for) the CareerDescription for a SOC.
 * Returns the same promise to concurrent callers. On success the value is
 * cached; on failure the entry is evicted so the next call retries.
 */
export function loadCareerDescription(
  socCode: string,
  occupationTitle: string,
): Promise<CareerDescription> {
  const cached = _resolved.get(socCode);
  if (cached !== undefined) return Promise.resolve(cached);

  const inflight = _inflight.get(socCode);
  if (inflight !== undefined) return inflight;

  const promise = fetchCareerDescription(socCode, occupationTitle)
    .then((desc) => {
      _resolved.set(socCode, desc);
      return desc;
    })
    .finally(() => {
      _inflight.delete(socCode);
    });

  _inflight.set(socCode, promise);
  return promise;
}

/**
 * Test/operator helper. Drops both the resolved and in-flight maps.
 */
export function clearCareerDescriptionCache(): void {
  _resolved.clear();
  _inflight.clear();
}
