/**
 * HorizonSilhouette.test.tsx
 *
 * Coverage for the muted-variant silhouette rendered behind the share card on
 * /app/save. This component MUST be deterministic for a given index — the
 * "screenshot-stable across remounts" guarantee in §1 hinges on it.
 *
 * What we test:
 *   - The image at the given index is the one rendered (basename match).
 *   - Opacity is locked at 60% so the share card reads above it.
 *   - Re-renders with the same index produce the same output (stability).
 *   - Out-of-range indices normalize via the hook's modulo guard.
 */

import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { HorizonSilhouette } from "./HorizonSilhouette";
import { HORIZON_BASENAMES } from "./horizonManifest";

function getRoot(container: HTMLElement): HTMLElement {
  const el = container.querySelector("#horizon-silhouette");
  if (!el) throw new Error("#horizon-silhouette not found");
  return el as HTMLElement;
}

function getImg(container: HTMLElement): HTMLImageElement {
  const img = container.querySelector("#horizon-silhouette img");
  if (!img) throw new Error("silhouette img not found");
  return img as HTMLImageElement;
}

function getSources(container: HTMLElement): HTMLSourceElement[] {
  return Array.from(
    container.querySelectorAll("#horizon-silhouette source"),
  ) as HTMLSourceElement[];
}

describe("HorizonSilhouette", () => {
  it("renders image at given index — picture sources point to that basename", () => {
    const { container } = render(<HorizonSilhouette index={5} />);
    const sources = getSources(container);
    expect(sources.length).toBeGreaterThan(0);
    const expectedBasename = encodeURIComponent(HORIZON_BASENAMES[5]);
    sources.forEach((s) => {
      const srcset = s.getAttribute("srcset") ?? "";
      expect(srcset).toContain(expectedBasename);
    });
  });

  it("renders at 60% opacity (the share card reads on top)", () => {
    const { container } = render(<HorizonSilhouette index={0} />);
    const root = getRoot(container);
    expect(root.style.opacity).toBe("0.6");
  });

  it("locked: re-renders with same index produce same image src", () => {
    // Stability contract for /app/save device-screenshots.
    const { container: a } = render(<HorizonSilhouette index={11} />);
    const { container: b } = render(<HorizonSilhouette index={11} />);
    expect(getImg(a).src).toBe(getImg(b).src);
    // And that src points to the locked basename.
    const expected = encodeURIComponent(HORIZON_BASENAMES[11]);
    expect(getImg(a).src).toContain(expected);
  });

  it("different indices produce different image sources", () => {
    const { container: a } = render(<HorizonSilhouette index={0} />);
    const { container: b } = render(<HorizonSilhouette index={1} />);
    expect(getImg(a).src).not.toBe(getImg(b).src);
  });

  it("decorative: empty alt + role=presentation on the img", () => {
    const { container } = render(<HorizonSilhouette index={0} />);
    const img = getImg(container);
    expect(img.getAttribute("alt")).toBe("");
    expect(img.getAttribute("role")).toBe("presentation");
  });

  it("uses eager loading + async decoding", () => {
    // Silhouette mounts only in the viewer phase, after a 6-18s save+render
    // wait, and is in-viewport at mount. Eager loading avoids an unnecessary
    // blank → silhouette pop-in. (Code review Minor #6 / spec §8.)
    const { container } = render(<HorizonSilhouette index={0} />);
    const img = getImg(container);
    expect(img.getAttribute("loading")).toBe("eager");
    expect(img.getAttribute("decoding")).toBe("async");
  });

  it("emits AVIF before WebP source order (modern format wins)", () => {
    const { container } = render(<HorizonSilhouette index={0} />);
    const sources = getSources(container);
    // We expect 4 sources: AVIF-2048, WebP-2048, AVIF-1400, WebP-1400.
    expect(sources).toHaveLength(4);
    expect(sources[0]!.getAttribute("type")).toBe("image/avif");
    expect(sources[1]!.getAttribute("type")).toBe("image/webp");
    expect(sources[2]!.getAttribute("type")).toBe("image/avif");
    expect(sources[3]!.getAttribute("type")).toBe("image/webp");
  });

  it("accepts an optional className (caller-controlled positioning)", () => {
    const { container } = render(
      <HorizonSilhouette index={0} className="my-test-class" />,
    );
    const root = getRoot(container);
    expect(root.className).toContain("my-test-class");
  });

  it("defends against an out-of-range index by wrapping into the pool", () => {
    // The hook normalizes; the rendered basename must be valid (not undefined
    // in the URL). We don't assert the specific normalized value — only that
    // the resulting srcset is a real basename, never literal "undefined".
    const { container } = render(<HorizonSilhouette index={9999} />);
    const img = getImg(container);
    expect(img.src).not.toContain("undefined");
    expect(img.src).toMatch(/jcern_Flat_orthographic/);
  });
});
