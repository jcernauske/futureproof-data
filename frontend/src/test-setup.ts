import "@testing-library/jest-dom/vitest";

// React Flow requires ResizeObserver which is not available in jsdom
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}

// Framer Motion's `whileInView` uses IntersectionObserver, which jsdom doesn't
// implement. Stub it so tests render landing sections without throwing.
if (typeof globalThis.IntersectionObserver === "undefined") {
  class IntersectionObserverStub {
    readonly root: Element | null = null;
    readonly rootMargin: string = "";
    readonly thresholds: ReadonlyArray<number> = [];
    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords(): IntersectionObserverEntry[] {
      return [];
    }
  }
  globalThis.IntersectionObserver =
    IntersectionObserverStub as unknown as typeof IntersectionObserver;
}
