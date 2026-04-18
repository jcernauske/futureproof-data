import { describe, it, expect } from "vitest";
import { socEmoji } from "./socEmoji";

/**
 * socEmoji tests
 *
 * Verifies SOC major-group prefix -> emoji mapping. These are user-visible
 * strings on every career card; regressions would silently show the wrong
 * emoji family or fall back to the briefcase.
 */
describe("socEmoji", () => {
  it("returns the computer emoji for 15-XXXX SOCs", () => {
    expect(socEmoji("15-1252")).toBe("💻");
    expect(socEmoji("15-2051")).toBe("💻");
  });

  it("returns the management emoji for 11-XXXX SOCs", () => {
    expect(socEmoji("11-3021")).toBe("🧭");
  });

  it("returns the healthcare practitioner emoji for 29-XXXX SOCs", () => {
    expect(socEmoji("29-1141")).toBe("🩺");
  });

  it("returns the engineering emoji for 17-XXXX SOCs", () => {
    expect(socEmoji("17-2061")).toBe("🛠️");
  });

  it("falls back to briefcase for unknown SOC prefixes", () => {
    expect(socEmoji("99-9999")).toBe("💼");
    expect(socEmoji("00-0000")).toBe("💼");
  });

  it("returns briefcase for null or undefined", () => {
    expect(socEmoji(null)).toBe("💼");
    expect(socEmoji(undefined)).toBe("💼");
  });

  it("returns briefcase for empty string (falsy guard)", () => {
    // Empty string is falsy — must hit the early-return, not slice into ""
    // and look up `SOC_MAJOR_GROUP_EMOJI[""]` which would also miss but is a
    // different code path. Guard protects against future changes.
    expect(socEmoji("")).toBe("💼");
  });
});
