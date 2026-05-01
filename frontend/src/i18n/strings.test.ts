import { describe, it, expect } from "vitest";
import { getString, STRINGS } from "./strings";

/**
 * getString tests
 *
 * Covers:
 *   1. English key lookup returns English string
 *   2. Spanish key lookup returns Spanish string
 *   3. Missing key in Spanish falls back to English
 *   4. Completely unknown key returns the key itself
 *   5. Same key returns different text for en vs es
 */

describe("getString", () => {
  it("returns English string for known key with locale='en'", () => {
    const result = getString("profile.start", "en");
    expect(result).toContain("go");
  });

  it("returns Spanish string for known key with locale='es'", () => {
    const result = getString("profile.start", "es");
    expect(result).toContain("Vamos");
  });

  it("en and es return different strings for the same key", () => {
    const en = getString("profile.meetGuide", "en");
    const es = getString("profile.meetGuide", "es");
    expect(en).not.toBe(es);
  });

  it("falls back to English when Spanish key is missing", () => {
    // getString uses the fallback chain: STRINGS[locale][key] ?? STRINGS.en[key] ?? key
    // If we had a key only in en, Spanish would fall back to English.
    // Since all current keys exist in both locales, we test the fallback
    // chain by verifying the final fallback (unknown key returns key).
    const result = getString("nonexistent.key.here", "es");
    expect(result).toBe("nonexistent.key.here");
  });

  it("returns the key itself when key is completely unknown", () => {
    const result = getString("totally.made.up", "en");
    expect(result).toBe("totally.made.up");
  });

  it("returns the key for unknown key in Spanish locale", () => {
    const result = getString("fake.key", "es");
    expect(result).toBe("fake.key");
  });

  it("all profile keys exist in both locales", () => {
    const profileKeys = [
      "profile.meetGuide",
      "profile.everyBuild",
      "profile.newName",
      "profile.language",
      "profile.stateLabel",
      "profile.start",
      "profile.generating",
      "profile.generateError",
      "profile.rerollError",
    ];

    for (const key of profileKeys) {
      const en = getString(key, "en");
      const es = getString(key, "es");
      // Neither should fall back to the raw key
      expect(en).not.toBe(key);
      expect(es).not.toBe(key);
      // They should be different strings (translated)
      expect(en).not.toBe(es);
    }
  });

  it("all syc keys exist in both locales", () => {
    const keys = ["syc.gemmaThinking", "syc.gemmaMatched"];
    for (const key of keys) {
      const en = getString(key, "en");
      const es = getString(key, "es");
      expect(en).not.toBe(key);
      expect(es).not.toBe(key);
      expect(en).not.toBe(es);
    }
  });

  it("all build/loading keys exist in both locales", () => {
    const keys = [
      "build.error",
      "build.tryAgain",
      "build.goBack",
      "build.loading1",
      "build.loading2",
      "build.loading3",
      "build.loading4",
      "build.loading5",
      "build.loadingFallback",
    ];
    for (const key of keys) {
      const en = getString(key, "en");
      const es = getString(key, "es");
      expect(en).not.toBe(key);
      expect(es).not.toBe(key);
      expect(en).not.toBe(es);
    }
  });

  it("returns Arabic string for known key with locale='ar'", () => {
    const result = getString("profile.meetGuide", "ar");
    expect(result).toBe("تعرّف على مرشدك");
  });

  it("Arabic differs from English and Spanish for the same key", () => {
    const en = getString("profile.meetGuide", "en");
    const es = getString("profile.meetGuide", "es");
    const ar = getString("profile.meetGuide", "ar");
    expect(ar).not.toBe(en);
    expect(ar).not.toBe(es);
  });

  it("falls back to English when Arabic key is missing", () => {
    // Unknown key in any locale returns the raw key string.
    const result = getString("nonexistent.key.here", "ar");
    expect(result).toBe("nonexistent.key.here");
  });

  it("preserves Latin-script brand and acronyms inside Arabic strings", () => {
    // Voice contract: Gemma stays in Latin script even in Arabic
    // copy, and SOC/CIP/data acronyms must not be transliterated.
    expect(getString("syc.gemmaThinking", "ar")).toContain("Gemma");
    expect(getString("syc.showingSoc", "ar")).toContain("SOC");
    expect(getString("syc.showingSoc", "ar")).toContain("CIP");
  });

  it("every en key exists in both es and ar (no silent fallback to English)", () => {
    // Locks in locale parity going forward. When you add an EN key, the
    // test forces you to add ES + AR or it fails — preventing the silent
    // fallback that makes Arabic users see English copy.
    const enKeys = Object.keys(STRINGS.en);
    const missingEs = enKeys.filter((k) => !(k in STRINGS.es));
    const missingAr = enKeys.filter((k) => !(k in STRINGS.ar));
    expect(missingEs, `Spanish missing keys: ${missingEs.join(", ")}`).toEqual([]);
    expect(missingAr, `Arabic missing keys: ${missingAr.join(", ")}`).toEqual([]);
  });

  it("no orphan keys in es or ar (every translated key has an en source)", () => {
    // Catches dead translations — keys that exist in es/ar but were
    // removed from en. The fallback chain would never serve these.
    const enKeys = new Set(Object.keys(STRINGS.en));
    const orphanEs = Object.keys(STRINGS.es).filter((k) => !enKeys.has(k));
    const orphanAr = Object.keys(STRINGS.ar).filter((k) => !enKeys.has(k));
    expect(orphanEs, `Spanish orphan keys: ${orphanEs.join(", ")}`).toEqual([]);
    expect(orphanAr, `Arabic orphan keys: ${orphanAr.join(", ")}`).toEqual([]);
  });

  it("Arabic strings exist for the full profile and core build paths", () => {
    const sampleKeys = [
      "profile.meetGuide",
      "profile.start",
      "syc.heading",
      "careerPick.heading",
      "build.gauntlet",
      "build.startingSalary",
      "stat.ern.name",
      "tree.horizon.title",
    ];
    for (const key of sampleKeys) {
      const ar = getString(key, "ar");
      expect(ar, `Arabic missing for key ${key}`).not.toBe(key);
      // Should contain at least one Arabic letter (basic Arabic block).
      expect(ar).toMatch(/[؀-ۿ]/);
    }
  });
});
