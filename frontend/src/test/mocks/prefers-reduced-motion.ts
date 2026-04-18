/**
 * Test helper: mocks `window.matchMedia` so tests can flip
 * `prefers-reduced-motion` on and off around Framer Motion's
 * `useReducedMotion()` hook.
 *
 * Usage:
 *   import { setReducedMotion, resetReducedMotion } from "@/test/mocks/prefers-reduced-motion";
 *
 *   beforeEach(() => resetReducedMotion());
 *   it("collapses reveal when reduced motion is set", () => {
 *     setReducedMotion(true);
 *     // ...render + assert
 *   });
 */

type Listener = (event: MediaQueryListEvent) => void;

const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

let reducedMotion = false;
const listeners = new Set<Listener>();

function buildMediaQueryList(query: string): MediaQueryList {
  const matches = query === REDUCED_MOTION_QUERY ? reducedMotion : false;
  return {
    matches,
    media: query,
    onchange: null,
    addEventListener: (_type: string, listener: EventListener) => {
      listeners.add(listener as unknown as Listener);
    },
    removeEventListener: (_type: string, listener: EventListener) => {
      listeners.delete(listener as unknown as Listener);
    },
    addListener: (listener: Listener) => listeners.add(listener),
    removeListener: (listener: Listener) => listeners.delete(listener),
    dispatchEvent: () => true,
  } as MediaQueryList;
}

export function installMatchMediaMock(): void {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: (query: string) => buildMediaQueryList(query),
  });
}

export function setReducedMotion(enabled: boolean): void {
  installMatchMediaMock();
  reducedMotion = enabled;
  const event = {
    matches: enabled,
    media: REDUCED_MOTION_QUERY,
  } as MediaQueryListEvent;
  listeners.forEach((listener) => listener(event));
}

export function resetReducedMotion(): void {
  reducedMotion = false;
  listeners.clear();
  installMatchMediaMock();
}
