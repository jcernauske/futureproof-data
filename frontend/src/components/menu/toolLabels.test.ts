import { describe, expect, it } from "vitest";
import {
  DEFAULT_TOOL_LABEL,
  TOOL_LABEL_MAP,
  resolveToolLabel,
} from "@/components/menu/toolLabels";

// Mirrors the canonical 5-tuple in backend/app/services/ask_gemma.py
// (_TOOLS). If a tool is added there, the corresponding entry must
// appear here too — this test is the gate.
const CHAT_TOOLS = [
  "get_career_paths",
  "get_occupation_data",
  "get_regional_price_parity",
  "compare_purchasing_power",
  "get_career_branches",
] as const;

describe("TOOL_LABEL_MAP", () => {
  it("test_all_chat_tools_have_label_entries", () => {
    for (const tool of CHAT_TOOLS) {
      expect(TOOL_LABEL_MAP[tool]).toBeDefined();
      expect(TOOL_LABEL_MAP[tool]?.label).toBeTruthy();
      expect(TOOL_LABEL_MAP[tool]?.icon).toBeTruthy();
      expect(typeof TOOL_LABEL_MAP[tool]?.hint).toBe("function");
    }
  });

  it("test_hint_templates_handle_realistic_args", () => {
    expect(
      TOOL_LABEL_MAP.get_career_paths!.hint({
        student_major: "Marketing",
      }),
    ).toBe("Looking up career outcomes for Marketing.");

    expect(
      TOOL_LABEL_MAP.get_career_paths!.hint({
        cipcode: "52.1401",
        unitid: 151351,
      }),
    ).toBe(
      "Looking up career outcomes for program 52.1401 at school 151351.",
    );

    expect(
      TOOL_LABEL_MAP.get_occupation_data!.hint({ soc_code: "13-2052" }),
    ).toBe("Pulling BLS data for occupation 13-2052.");

    expect(
      TOOL_LABEL_MAP.get_regional_price_parity!.hint({ state: "Indiana" }),
    ).toBe("Checking cost-of-living for Indiana.");

    expect(
      TOOL_LABEL_MAP.compare_purchasing_power!.hint({
        state_a: "Indiana",
        state_b: "California",
      }),
    ).toBe(
      "Comparing purchasing power between Indiana and California.",
    );

    expect(
      TOOL_LABEL_MAP.get_career_branches!.hint({ soc_code: "13-2052" }),
    ).toBe("Looking up career branches from 13-2052.");
  });

  it("hint templates degrade gracefully with empty args", () => {
    for (const tool of CHAT_TOOLS) {
      const sentence = TOOL_LABEL_MAP[tool]!.hint({});
      // Always returns a non-empty, sentence-shaped string ending
      // with a period. Never crashes.
      expect(sentence).toMatch(/\.$/);
      expect(sentence.length).toBeGreaterThan(5);
    }
  });
});

describe("resolveToolLabel", () => {
  it("returns the entry for a known tool name", () => {
    const label = resolveToolLabel("get_career_paths");
    expect(label).toBe(TOOL_LABEL_MAP.get_career_paths);
  });

  it("test_unknown_tool_returns_default_label", () => {
    const label = resolveToolLabel("get_nonexistent_xyz");
    expect(label).toBe(DEFAULT_TOOL_LABEL);
    expect(label.label).toBe("Tool call");
    expect(label.icon).toBe("IconWrench");
    expect(label.hint({ anything: "at all" })).toBe(
      "Gemma is consulting a tool.",
    );
  });
});
