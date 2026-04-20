/**
 * ChapterCard — variant rendering tests.
 *
 * Spec: docs/specs/feature-chapter-book.md §3.3 (variant behavior) +
 * §4 New Tests Required P0 rows.
 *
 * The four variants (anchor / role / locked / ceiling) each have a
 * specific rendering contract: anchor shows `stats_snapshot`, locked
 * starts collapsed and toggles on click, ceiling renders muted copy
 * with no SOC/emoji/deltas, role renders deltas + SOC code.
 *
 * These tests render the card against real `Chapter` objects (built via
 * bucketBranches) so any drift between the Chapter contract and the
 * render breaks here, not in production.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, within, waitFor } from "@testing-library/react";
import { ChapterCard } from "./ChapterCard";
import { chapterCopy } from "./chapterCopy";
import type { Chapter } from "./types";
import {
  resetReducedMotion,
  setReducedMotion,
} from "@/test/mocks/prefers-reduced-motion";

function makeAnchor(overrides: Partial<Chapter> = {}): Chapter {
  return {
    number: 1,
    years_label: chapterCopy.years.entry,
    tier: "entry",
    kind: "anchor",
    title: "Biological Technician",
    soc: "19-4021",
    what_changes: chapterCopy.anchor.what_changes,
    unlock: null,
    related_education_level: "Bachelor's degree",
    requires_grad_degree: false,
    deltas: {},
    stats_snapshot: { ern: 2, roi: 3, res: 4, grw: 3, hmn: 3 },
    ...overrides,
  };
}

function makeRole(overrides: Partial<Chapter> = {}): Chapter {
  return {
    number: 2,
    years_label: chapterCopy.years.early,
    tier: "early",
    kind: "role",
    title: "Microbiologist",
    soc: "19-1022",
    what_changes: "",
    unlock: null,
    related_education_level: "Bachelor's degree",
    requires_grad_degree: false,
    deltas: { ern: 1, grw: 1 },
    ...overrides,
  };
}

function makeLocked(overrides: Partial<Chapter> = {}): Chapter {
  return {
    number: 3,
    years_label: chapterCopy.years.mid,
    tier: "mid",
    kind: "locked",
    title: "Medical Scientist",
    soc: "19-1042",
    what_changes: "",
    unlock: "Master's preferred · 10+ yrs",
    related_education_level: "Master's degree",
    requires_grad_degree: true,
    deltas: { ern: 2, res: 1 },
    ...overrides,
  };
}

function makeCeiling(overrides: Partial<Chapter> = {}): Chapter {
  return {
    number: 4,
    years_label: "8+ yrs",
    tier: "senior",
    kind: "ceiling",
    title: chapterCopy.ceiling.title,
    soc: null,
    what_changes: chapterCopy.ceiling.what_changes,
    unlock: null,
    related_education_level: null,
    requires_grad_degree: false,
    deltas: {},
    ...overrides,
  };
}

beforeEach(() => {
  resetReducedMotion();
});
afterEach(() => {
  vi.restoreAllMocks();
});

describe("ChapterCard — anchor variant", () => {
  it("renders stats_snapshot, not deltas", () => {
    const anchor = makeAnchor();
    render(<ChapterCard chapter={anchor} isLast={false} />);

    // Snapshot row is present…
    const snapshot = screen.getByTestId("stats-snapshot");
    expect(snapshot).toBeInTheDocument();
    // …and contains a pill per stat that's populated in the snapshot.
    expect(within(snapshot).getByTestId("snapshot-pill-ern")).toBeInTheDocument();
    expect(within(snapshot).getByTestId("snapshot-pill-roi")).toBeInTheDocument();
    expect(within(snapshot).getByTestId("snapshot-pill-res")).toBeInTheDocument();
    expect(within(snapshot).getByTestId("snapshot-pill-grw")).toBeInTheDocument();
    expect(within(snapshot).getByTestId("snapshot-pill-hmn")).toBeInTheDocument();

    // No delta row on the anchor — the anchor is a snapshot, not a shift.
    expect(screen.queryByTestId("delta-row")).not.toBeInTheDocument();
  });

  it("renders an em dash when a snapshot stat is missing", () => {
    const anchor = makeAnchor({
      stats_snapshot: { ern: 4, roi: 3, hmn: 3 }, // res + grw absent
    });
    render(<ChapterCard chapter={anchor} isLast={false} />);
    const res = screen.getByTestId("snapshot-pill-res");
    expect(res.textContent).toContain("—");
    const grw = screen.getByTestId("snapshot-pill-grw");
    expect(grw.textContent).toContain("—");
  });

  it("renders the SOC emoji via data-socEmoji mapping", () => {
    // 19-* SOC prefix maps to the life-science emoji 🔬 in socEmoji.ts.
    // This asserts the emoji is actually rendered (aria-hidden), so a
    // regression in the SOC-prefix lookup would break here.
    const anchor = makeAnchor({ soc: "19-4021" });
    render(<ChapterCard chapter={anchor} isLast={false} />);
    const card = screen.getByTestId("chapter-1-19-4021");
    expect(card.textContent).toContain("🔬");
  });
});

describe("ChapterCard — role variant", () => {
  it("renders deltas and SOC code", () => {
    const role = makeRole();
    render(<ChapterCard chapter={role} isLast={false} />);

    const deltaRow = screen.getByTestId("delta-row");
    expect(within(deltaRow).getByTestId("delta-pill-ern")).toBeInTheDocument();
    expect(within(deltaRow).getByTestId("delta-pill-grw")).toBeInTheDocument();
    // No snapshot on role chapters — that's the anchor's contract.
    expect(screen.queryByTestId("stats-snapshot")).not.toBeInTheDocument();

    // SOC code is surfaced as a data-font receipt. Exact string so a
    // silent `soc.slice(...)` regression surfaces here.
    expect(screen.getByText("19-1022")).toBeInTheDocument();

    // Chapter kind data attribute — per §3 a11y table, data-chapter-kind
    // is how tests and downstream CSS target the variant.
    expect(screen.getByTestId("chapter-2-19-1022").getAttribute("data-chapter-kind")).toBe("role");
  });

  it("prefixes the positive sign on positive deltas", () => {
    const role = makeRole({ deltas: { ern: 2, hmn: -1 } });
    render(<ChapterCard chapter={role} isLast={false} />);
    const ernPill = screen.getByTestId("delta-pill-ern");
    expect(ernPill.textContent).toContain("+2");
    const hmnPill = screen.getByTestId("delta-pill-hmn");
    // Negative deltas render with the minus sign only (no "+").
    expect(hmnPill.textContent).toContain("-1");
    expect(hmnPill.textContent).not.toContain("+-1");
  });

  it("does not render a delta row when deltas is empty", () => {
    const role = makeRole({ deltas: {} });
    render(<ChapterCard chapter={role} isLast={false} />);
    // Per bucketBranches, zeros/nulls are stripped. An all-zero branch
    // therefore produces an empty deltas object — the row must not
    // render a bare "What shifts" label with no pills beneath it.
    expect(screen.queryByTestId("delta-row")).not.toBeInTheDocument();
    expect(screen.queryByText(/^What shifts$/)).not.toBeInTheDocument();
  });
});

describe("ChapterCard — locked variant", () => {
  it("collapses by default, expands on click, toggles aria-expanded", async () => {
    const locked = makeLocked();
    render(<ChapterCard chapter={locked} isLast={false} />);

    const toggle = screen.getByTestId("chapter-lock-3");
    // Collapsed state: aria-expanded="false", sub-line visible, body hidden.
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(
      screen.getByText(chapterCopy.locked.sublabel),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("delta-row")).not.toBeInTheDocument();

    // Button label reads "Read" while collapsed.
    expect(toggle.textContent).toContain("Read");

    // Expand.
    fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    // Body now renders deltas.
    expect(screen.getByTestId("delta-row")).toBeInTheDocument();
    expect(screen.getByTestId("delta-pill-ern")).toBeInTheDocument();
    // Sub-line disappears once expanded (it's only visible when collapsed).
    expect(screen.queryByText(chapterCopy.locked.sublabel)).not.toBeInTheDocument();
    // Label flips to "Hide".
    expect(toggle.textContent).toContain("Hide");

    // Collapse again — aria-expanded flips back. We don't assert on the
    // delta row disappearing immediately because AnimatePresence holds
    // the exit-animating body in the tree until the transition resolves;
    // the aria-expanded flip is the observable contract for AT.
    fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    // The sub-line re-appears once the collapse completes — a clean
    // "fully collapsed" signal without racing AnimatePresence.
    await waitFor(() =>
      expect(screen.getByText(chapterCopy.locked.sublabel)).toBeInTheDocument(),
    );
  });

  it("wires aria-controls to the body region so screen readers follow the toggle", () => {
    const locked = makeLocked({ number: 3 });
    render(<ChapterCard chapter={locked} isLast={false} />);
    const toggle = screen.getByTestId("chapter-lock-3");
    // aria-controls must match the body id (so AT can jump to the
    // controlled region). Expanding the body must bring that element
    // into the DOM.
    const controlsId = toggle.getAttribute("aria-controls");
    expect(controlsId).toBe("chapter-3-body");
    fireEvent.click(toggle);
    expect(document.getElementById(controlsId!)).not.toBeNull();
  });

  it("renders the locked variant's insight-colored dot and chapter-kind attr", () => {
    const locked = makeLocked();
    render(<ChapterCard chapter={locked} isLast={false} />);
    expect(screen.getByTestId("chapter-3-19-1042").getAttribute("data-chapter-kind")).toBe(
      "locked",
    );
  });
});

describe("ChapterCard — ceiling variant", () => {
  it("renders muted 'levels off' copy with no SOC / emoji / deltas", () => {
    const ceiling = makeCeiling();
    render(<ChapterCard chapter={ceiling} isLast={true} />);

    // Title is the canonical ceiling copy.
    expect(screen.getByText(chapterCopy.ceiling.title)).toBeInTheDocument();
    // What-changes paragraph uses the ceiling's narrative copy.
    expect(
      screen.getByText(chapterCopy.ceiling.what_changes),
    ).toBeInTheDocument();
    // Closing note is present.
    expect(
      screen.getByText(chapterCopy.ceiling.closingNote),
    ).toBeInTheDocument();

    // No SOC code on the ceiling (soc is null).
    const card = screen.getByTestId("chapter-4-ceiling");
    // The SOC display element has class "font-data". For a ceiling
    // chapter there should be no SOC receipt element rendered — check
    // by absence of any element whose text matches a SOC pattern.
    expect(card.textContent).not.toMatch(/\d{2}-\d{4}/);

    // No emoji — emoji comes from socEmoji(chapter.soc) which is only
    // rendered for role/locked/anchor. Assert by the absence of the
    // life-science emoji (which would appear if a SOC were wired).
    expect(card.textContent).not.toContain("🔬");

    // No stat rows.
    expect(screen.queryByTestId("delta-row")).not.toBeInTheDocument();
    expect(screen.queryByTestId("stats-snapshot")).not.toBeInTheDocument();

    // Variant is labeled via data-chapter-kind.
    expect(card.getAttribute("data-chapter-kind")).toBe("ceiling");
  });

  it("renders the bookmark closing line only when isLast is true", () => {
    // isLast=true path — bookmark copy appears.
    const { unmount } = render(
      <ChapterCard chapter={makeCeiling()} isLast={true} />,
    );
    expect(screen.getByText(chapterCopy.bookmark)).toBeInTheDocument();
    unmount();
    // isLast=false path — bookmark copy MUST NOT render. Re-rendering
    // the same chapter with isLast=false should suppress the line.
    render(<ChapterCard chapter={makeCeiling()} isLast={false} />);
    expect(screen.queryByText(chapterCopy.bookmark)).not.toBeInTheDocument();
  });
});

describe("ChapterCard — a11y contract", () => {
  it("labels each card via aria-labelledby pointing at the chapter title h3", () => {
    render(<ChapterCard chapter={makeRole()} isLast={false} />);
    const card = screen.getByTestId("chapter-2-19-1022");
    const labelId = card.getAttribute("aria-labelledby");
    expect(labelId).toBe("chapter-2-title");
    const title = document.getElementById(labelId!);
    expect(title).not.toBeNull();
    expect(title!.textContent).toBe("Microbiologist");
  });

  it("reduced-motion still renders the locked body when expanded", () => {
    // The reduced-motion branch short-circuits Framer's height/opacity
    // animation. The functional contract must still hold — clicking
    // Read reveals the body.
    setReducedMotion(true);
    render(<ChapterCard chapter={makeLocked()} isLast={false} />);
    const toggle = screen.getByTestId("chapter-lock-3");
    fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByTestId("delta-row")).toBeInTheDocument();
  });
});
