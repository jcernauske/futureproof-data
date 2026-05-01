import { describe, it, expect } from "vitest";
import {
  DEFAULT_LOCALE,
  isRtlLocale,
  localeDirection,
  normalizeLocale,
} from "./locales";

/**
 * Mirrors the backend normalize_locale contract: only exact "es" / "ar"
 * produce themselves; everything else normalizes to "en".
 */

describe("normalizeLocale", () => {
  it("returns 'es' for exact 'es'", () => {
    expect(normalizeLocale("es")).toBe("es");
  });

  it("returns 'ar' for exact 'ar'", () => {
    expect(normalizeLocale("ar")).toBe("ar");
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

  it("returns 'en' for uppercase 'AR'", () => {
    expect(normalizeLocale("AR")).toBe("en");
  });
});

describe("DEFAULT_LOCALE", () => {
  it("is 'en'", () => {
    expect(DEFAULT_LOCALE).toBe("en");
  });
});

describe("isRtlLocale", () => {
  it("returns true for Arabic", () => {
    expect(isRtlLocale("ar")).toBe(true);
  });

  it("returns false for English", () => {
    expect(isRtlLocale("en")).toBe(false);
  });

  it("returns false for Spanish", () => {
    expect(isRtlLocale("es")).toBe(false);
  });
});

describe("localeDirection", () => {
  it("returns 'rtl' for Arabic", () => {
    expect(localeDirection("ar")).toBe("rtl");
  });

  it("returns 'ltr' for English", () => {
    expect(localeDirection("en")).toBe("ltr");
  });

  it("returns 'ltr' for Spanish", () => {
    expect(localeDirection("es")).toBe("ltr");
  });
});
