import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import {
  describe,
  it,
  expect,
  vi,
  beforeEach,
  afterEach,
} from "vitest";
import { MajorInput } from "./MajorInput";
import type {
  IntentResult,
  ProgramResult,
  SchoolSelection,
} from "@/types/buildInput";

/**
 * MajorInput — tiered Gemma match card tests.
 *
 * The component has four render phases after the user submits text:
 *   - "match"  → MatchContent (high or medium tier)
 *   - "clarify" → ClarifyContent (low tier OR "Not quite")
 *   - "audit_fail" → hard-reject card
 *   - "fallback" → apiPost threw; show program picker
 *
 * These tests pin the behaviors added by the tiered-matching spec
 * (feature-gemma-tiered-matching.md §4):
 *   1. High tier → no alternatives list rendered, "That's right" CTA.
 *   2. Medium tier → alternatives list (AlternativesList) with correct
 *      aria semantics, "Close enough" CTA, "best guess" pill.
 *   3. Clicking an alternative fires onConfirm with THAT alt's CIP/title,
 *      after the 320ms thrive flash — the primary's values must not leak
 *      through.
 *   4. Low tier → needs_clarification=true routes to ClarifyContent; the
 *      match card never sees confidence === "low".
 *
 * Harness pattern is copied from SchoolMajorScreen.test.tsx (vi.mock on
 * @/api/client, fake timers, type the input + click submit, then
 * findByRole/findByText for the resulting UI).
 */

// -------------------------------------------------------------------------
// Mocks
// -------------------------------------------------------------------------

vi.mock("@/api/client", () => ({
  apiPost: vi.fn(),
  apiGet: vi.fn(),
}));

import { apiPost } from "@/api/client";
const mockedApiPost = apiPost as unknown as ReturnType<typeof vi.fn>;

// -------------------------------------------------------------------------
// Fixtures
// -------------------------------------------------------------------------

const SCHOOL: SchoolSelection = {
  unitid: 123456,
  name: "University of Central Anywhere",
  institutionControl: "Public",
  netPriceAnnual: 14200,
  costOfAttendanceAnnual: 28000,
};

const PROGRAMS: ProgramResult[] = [
  {
    unitid: 123456,
    institution_name: "University of Central Anywhere",
    cipcode: "52.0201",
    program_name: "Business Administration",
    cip_family_name: "Business",
    earnings_1yr_median: 50000,
    debt_median: 25000,
  },
  {
    unitid: 123456,
    institution_name: "University of Central Anywhere",
    cipcode: "52.0801",
    program_name: "Finance, General",
    cip_family_name: "Business",
    earnings_1yr_median: 55000,
    debt_median: 24000,
  },
  {
    unitid: 123456,
    institution_name: "University of Central Anywhere",
    cipcode: "52.1401",
    program_name: "Marketing/Marketing Management, General",
    cip_family_name: "Business",
    earnings_1yr_median: 48000,
    debt_median: 23000,
  },
];

function makeIntentResult(
  overrides: Partial<IntentResult> = {},
): IntentResult {
  return {
    matched_cip: "52.0201",
    matched_title: "Business Administration",
    confidence: "high",
    reasoning: "unambiguous match",
    careers_preview: [
      "Financial Analyst",
      "Marketing Manager",
      "Operations Manager",
    ],
    audit_flag: null,
    audit_message: null,
    needs_clarification: false,
    alternatives: null,
    parent_cip: "",
    ...overrides,
  };
}

async function typeAndSubmit(major: string): Promise<void> {
  const input = screen.getByRole("textbox", {
    name: /what do you want to study/i,
  });
  // fireEvent.change is the canonical vitest/RTL path when the project
  // isn't using @testing-library/user-event (package.json confirms that).
  fireEvent.change(input, { target: { value: major } });
  const submit = screen.getByRole("button", { name: /submit major/i });
  // Wrap the click + microtask flush in act() so React 19 can commit
  // the state updates (phase transition: thinking → match/clarify)
  // without emitting `not wrapped in act(...)` warnings.
  await act(async () => {
    fireEvent.click(submit);
    // Flush the microtask that resolves apiPost so React commits the
    // next phase before the test asserts.
    await Promise.resolve();
    await Promise.resolve();
  });
}

function renderMajorInput(onConfirm = vi.fn()) {
  const utils = render(
    <MajorInput school={SCHOOL} programs={PROGRAMS} onConfirm={onConfirm} />,
  );
  return { ...utils, onConfirm };
}

// -------------------------------------------------------------------------
// Setup/teardown
// -------------------------------------------------------------------------

beforeEach(() => {
  mockedApiPost.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

// -------------------------------------------------------------------------
// P0 tests
// -------------------------------------------------------------------------

describe("MajorInput — tiered rendering (P0)", () => {
  it("renders high-tier card with no alternatives list", async () => {
    // High tier: confidence="high", alternatives=[]. The card must not
    // render the "Other close matches" region even when the alternatives
    // array is an empty list (not just null).
    mockedApiPost.mockResolvedValueOnce(
      makeIntentResult({
        matched_cip: "51.2308",
        matched_title: "Physical Therapy/Therapist",
        confidence: "high",
        alternatives: [],
      }),
    );

    renderMajorInput();
    await typeAndSubmit("pre-PT");

    // The matched title is the signal we landed in the match phase.
    await screen.findByText("Physical Therapy/Therapist");

    // CTA label is the high-tier form.
    expect(
      screen.getByRole("button", { name: "That's right" }),
    ).toBeInTheDocument();
    // Not the medium label.
    expect(
      screen.queryByRole("button", { name: "Close enough" }),
    ).toBeNull();

    // The AlternativesList surfaces a <ul role="list"> with aria-label
    // "Other close matches". On the high tier it must not render.
    expect(
      screen.queryByRole("list", { name: /other close matches/i }),
    ).toBeNull();

    // And no "best guess" pill on a confident match.
    expect(screen.queryByText(/best guess/i)).toBeNull();
  });

  it("renders medium-tier card with alternatives list", async () => {
    // Medium tier: 3 alternatives, caution styling, "Close enough" CTA.
    mockedApiPost.mockResolvedValueOnce(
      makeIntentResult({
        matched_cip: "52.0201",
        matched_title: "Business Administration",
        confidence: "medium",
        alternatives: [
          {
            cip: "52.0801",
            title: "Finance",
            why: "core markets and capital",
          },
          {
            cip: "52.1401",
            title: "Marketing",
            why: "how you grow a customer base",
          },
          {
            cip: "52.0701",
            title: "Entrepreneurship",
            why: "starting and running your own",
          },
        ],
      }),
    );

    renderMajorInput();
    await typeAndSubmit("business");

    // Primary match landed.
    await screen.findByText("Business Administration");

    // Medium-tier CTA + pill.
    expect(
      screen.getByRole("button", { name: "Close enough" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/best guess/i)).toBeInTheDocument();

    // AlternativesList with the exact aria semantics from §3.
    const altsList = screen.getByRole("list", {
      name: /other close matches/i,
    });
    expect(altsList).toBeInTheDocument();

    // Three alternative buttons, one per alt, with the spec's
    // `aria-label="Select {title}"` convention.
    expect(
      screen.getByRole("button", { name: "Select Finance" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Select Marketing" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Select Entrepreneurship" }),
    ).toBeInTheDocument();
  });

  it("clicking an alternative triggers onConfirm with that CIP", async () => {
    // The critical assertion: primary is "Business Administration"
    // / 52.0201, but the student clicked "Finance" / 52.0801. onConfirm
    // must receive the Finance values, not the primary's.
    vi.useFakeTimers({ shouldAdvanceTime: true });

    mockedApiPost.mockImplementation((path: string) => {
      if (path === "/intent/") {
        return Promise.resolve(
          makeIntentResult({
            matched_cip: "52.0201",
            matched_title: "Business Administration",
            confidence: "medium",
            alternatives: [
              { cip: "52.0801", title: "Finance", why: "markets" },
              { cip: "52.1401", title: "Marketing", why: "growth" },
              {
                cip: "52.0701",
                title: "Entrepreneurship",
                why: "founding",
              },
            ],
          }),
        );
      }
      // /intent/confirm fire-and-forget — resolve so the unhandled-
      // rejection handler on `handleConfirm` has nothing to swallow.
      return Promise.resolve({});
    });

    const { onConfirm } = renderMajorInput();
    await typeAndSubmit("business");

    const financeButton = await screen.findByRole("button", {
      name: "Select Finance",
    });
    fireEvent.click(financeButton);

    // The 320ms flash must run before onConfirm fires. Before advancing
    // timers, onConfirm must NOT have been called.
    expect(onConfirm).not.toHaveBeenCalled();

    // Advance past the 320ms thrive-flash window.
    await vi.advanceTimersByTimeAsync(320);

    expect(onConfirm).toHaveBeenCalledTimes(1);
    const payload = onConfirm.mock.calls[0][0];
    // Critical — the primary's values must NOT leak through.
    expect(payload.cipCode).toBe("52.0801");
    expect(payload.cipTitle).toBe("Finance");
    expect(payload.cipCode).not.toBe("52.0201");
    expect(payload.cipTitle).not.toBe("Business Administration");
    // careersPreview was derived from the primary; spec §3 D6 says we
    // drop it when the student picks an alt rather than show the wrong
    // list.
    expect(payload.careersPreview).toEqual([]);
    expect(payload.substitutionApplied).toBe(false);
    expect(payload.rawText).toBe("business");
  });

  it("low-tier result renders clarify picker, not match card", async () => {
    // Low tier: the service sets needs_clarification=true. MajorInput
    // routes to the clarify phase BEFORE MatchContent ever renders.
    // The markers we check are the ClarifyContent-specific header
    // ("Let's find the right one") and the filter input.
    mockedApiPost.mockResolvedValueOnce(
      makeIntentResult({
        matched_cip: "19.0101",
        matched_title: "Family and Consumer Sciences",
        confidence: "low",
        needs_clarification: true,
        alternatives: [
          { cip: "51.3801", title: "Nursing", why: "clinical care" },
          { cip: "44.0701", title: "Social Work", why: "community" },
        ],
      }),
    );

    renderMajorInput();
    await typeAndSubmit("helping people");

    // Clarify-phase header.
    await screen.findByText(/let's find the right one/i);

    // Clarify filter input.
    expect(
      screen.getByPlaceholderText(/filter programs/i),
    ).toBeInTheDocument();

    // MatchContent-specific markers must NOT be on screen.
    expect(
      screen.queryByRole("button", { name: "That's right" }),
    ).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Close enough" }),
    ).toBeNull();
    // And no alternatives list (the clarify phase uses the program
    // picker, not the medium-tier alternatives UI).
    expect(
      screen.queryByRole("list", { name: /other close matches/i }),
    ).toBeNull();
  });
});

// -------------------------------------------------------------------------
// P1 tests
// -------------------------------------------------------------------------

describe("MajorInput — tiered rendering (P1)", () => {
  it("medium-tier card with zero alternatives still renders primary", async () => {
    // Degenerate case from §3 D7: medium confidence with empty or null
    // alternatives. The card must still wear caution styling (best-guess
    // pill, "Close enough" CTA) but the alternatives section is omitted.
    mockedApiPost.mockResolvedValueOnce(
      makeIntentResult({
        matched_cip: "52.0201",
        matched_title: "Business Administration",
        confidence: "medium",
        alternatives: [],
      }),
    );

    renderMajorInput();
    await typeAndSubmit("business");

    // Primary title + caution signals still render.
    await screen.findByText("Business Administration");
    expect(
      screen.getByRole("button", { name: "Close enough" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/best guess/i)).toBeInTheDocument();

    // But no alternatives list because the array is empty.
    expect(
      screen.queryByRole("list", { name: /other close matches/i }),
    ).toBeNull();
  });

  it("confirm flash fires on alternative click same as primary", async () => {
    // Spec §3 D6: clicking an alt must disable the primary CTA + every
    // other alt button for the 320ms flash so the student can't
    // double-fire the confirm handoff.
    vi.useFakeTimers({ shouldAdvanceTime: true });

    mockedApiPost.mockImplementation((path: string) => {
      if (path === "/intent/") {
        return Promise.resolve(
          makeIntentResult({
            matched_cip: "52.0201",
            matched_title: "Business Administration",
            confidence: "medium",
            alternatives: [
              { cip: "52.0801", title: "Finance", why: "markets" },
              { cip: "52.1401", title: "Marketing", why: "growth" },
              {
                cip: "52.0701",
                title: "Entrepreneurship",
                why: "founding",
              },
            ],
          }),
        );
      }
      return Promise.resolve({});
    });

    renderMajorInput();
    await typeAndSubmit("business");

    const financeBtn = await screen.findByRole("button", {
      name: "Select Finance",
    });
    const marketingBtn = screen.getByRole("button", {
      name: "Select Marketing",
    });
    const entrepreneurshipBtn = screen.getByRole("button", {
      name: "Select Entrepreneurship",
    });
    const primaryCta = screen.getByRole("button", { name: "Close enough" });
    const notQuite = screen.getByRole("button", { name: /not quite/i });

    // Pre-click: nothing is disabled.
    expect(financeBtn).not.toBeDisabled();
    expect(marketingBtn).not.toBeDisabled();
    expect(entrepreneurshipBtn).not.toBeDisabled();
    expect(primaryCta).not.toBeDisabled();
    expect(notQuite).not.toBeDisabled();

    fireEvent.click(financeBtn);

    // Flash is in-flight. Everything else must be disabled so the
    // student can't double-confirm.
    await waitFor(() => {
      expect(marketingBtn).toBeDisabled();
    });
    expect(financeBtn).toBeDisabled();
    expect(entrepreneurshipBtn).toBeDisabled();
    expect(primaryCta).toBeDisabled();
    expect(notQuite).toBeDisabled();
  });
});
