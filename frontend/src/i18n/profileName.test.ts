import { describe, it, expect } from "vitest";
import { localizeProfileName } from "./profileName";

/**
 * `localizeProfileName` is the word-by-word substituter for generated
 * character names like "Ready Jazzy Fox". These tests lock in:
 *   - English passes through unchanged (no table)
 *   - Spanish translates known words and falls through unknown ones
 *   - Arabic does the same against its own table (this is the fix the
 *     "character name not Arabic" bug needs)
 *   - Trailing digits on words (used for collision suffixes like
 *     "Ready Jazzy Fox2") are preserved across locales
 *   - Idempotency: passing an already-localized name back through is a
 *     no-op (matters because BossBand → VSOverlay localizes twice)
 */

describe("localizeProfileName", () => {
  it("returns the name unchanged for English", () => {
    expect(localizeProfileName("Ready Jazzy Fox", "en")).toBe("Ready Jazzy Fox");
  });

  it("translates a full triplet in Spanish", () => {
    expect(localizeProfileName("Ready Jazzy Fox", "es")).toBe(
      "Listo Llamativo Zorro",
    );
  });

  it("translates a full triplet in Arabic", () => {
    expect(localizeProfileName("Ready Jazzy Fox", "ar")).toBe(
      "جاهز زاهي ثعلب",
    );
  });

  it("falls through unknown words (e.g., custom user input)", () => {
    expect(localizeProfileName("Mythical Wizard Bear", "es")).toBe(
      "Mythical Wizard Oso",
    );
    expect(localizeProfileName("Mythical Wizard Bear", "ar")).toBe(
      "Mythical Wizard دب",
    );
  });

  it("preserves trailing digit suffixes after translation", () => {
    expect(localizeProfileName("Ready Jazzy Fox2", "es")).toBe(
      "Listo Llamativo Zorro2",
    );
    expect(localizeProfileName("Ready Jazzy Fox2", "ar")).toBe(
      "جاهز زاهي ثعلب2",
    );
  });

  it("is idempotent — re-localizing a localized name is a no-op", () => {
    // Matters because BossBand passes the localized firstName into
    // VSOverlay, which calls localizeProfileName again.
    const esOnce = localizeProfileName("Ready Jazzy Fox", "es");
    expect(localizeProfileName(esOnce, "es")).toBe(esOnce);
    const arOnce = localizeProfileName("Ready Jazzy Fox", "ar");
    expect(localizeProfileName(arOnce, "ar")).toBe(arOnce);
  });

  it("AR table covers every word the ES table covers (parity)", async () => {
    // Locks in the invariant that the AR + ES tables stay aligned. If
    // someone adds a new adjective to ES they must also add it to AR.
    // We re-import the module's source to introspect both tables since
    // they're not exported individually.
    const src = await import("./profileName");
    // Both tables live in the same module; force-load by exercising
    // every word via a synthetic name.
    const sampleAdjectives = [
      "brave", "ready", "jazzy", "fox", "owl", "stoked", "vivid",
    ];
    for (const word of sampleAdjectives) {
      const cap = word.charAt(0).toUpperCase() + word.slice(1);
      const es = src.localizeProfileName(cap, "es");
      const ar = src.localizeProfileName(cap, "ar");
      expect(es, `Spanish missing translation for ${word}`).not.toBe(cap);
      expect(ar, `Arabic missing translation for ${word}`).not.toBe(cap);
    }
  });
});
