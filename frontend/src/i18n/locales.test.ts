import { describe, it, expect } from "vitest";
import { DEFAULT_LOCALE, normalizeLocale } from "./locales";

/**
 * Frontend normalizeLocale tests
 *
 * Mirrors the backend normalize_locale contract: only exact "es" produces
 * "es"; everything else normalizes to "en".
 */

describe("normalizeLocale", () => {
  it("returns 'es' for exact 'es'", () => {
    expect(normalizeLocale("es")).toBe("es");
  });

  it("returns 'en' for 'en'", () => {
    expect(normalizeLocale("en")).toBe("en");
  });

  it("returns 'en' for undefined", () => {
    expect(normalizeLocale(undefined)).toBe("en");
  });

  it("returns 'en' for null", () => {
    expect(normalizeLocale(null)).toBe("en");
  });

  it("returns 'en' for unsupported locale string", () => {
    expect(normalizeLocale("fr")).toBe("en");
  });

  it("returns 'en' for number", () => {
    expect(normalizeLocale(42)).toBe("en");
  });

  it("returns 'en' for empty string", () => {
    expect(normalizeLocale("")).toBe("en");
  });

  it("returns 'en' for uppercase 'ES'", () => {
    expect(normalizeLocale("ES")).toBe("en");
  });
});

describe("DEFAULT_LOCALE", () => {
  it("is 'en'", () => {
    expect(DEFAULT_LOCALE).toBe("en");
  });
});
