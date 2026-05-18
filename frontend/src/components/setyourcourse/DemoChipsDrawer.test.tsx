/**
 * DemoChipsDrawer.test.tsx
 *
 * Covers two sections:
 *   - Single picks: 10 standalone chips
 *   - Cost comparisons: 3 pairs (better / worse) rendered with contrast
 *
 * Each chip click fires onPick with the right DemoChip (school + major
 * intact) so the parent screen can seed + resolve.
 */

import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DemoChipsDrawer } from "./DemoChipsDrawer";
import { DEMO_CHIPS, DEMO_COMPARISONS } from "@/data/demoChips";

describe("DemoChipsDrawer — top-level", () => {
  it("collapsed_by_default — trigger shows, panel hidden", () => {
    render(<DemoChipsDrawer onPick={vi.fn()} />);
    const trigger = screen.getByTestId("demo-chips-trigger");
    expect(trigger).toBeInTheDocument();
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByTestId("demo-chips-panel")).toBeNull();
  });

  it("expands_on_click — panel visible, aria-expanded flips", () => {
    render(<DemoChipsDrawer onPick={vi.fn()} />);
    const trigger = screen.getByTestId("demo-chips-trigger");
    fireEvent.click(trigger);
    expect(trigger.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByTestId("demo-chips-panel")).toBeInTheDocument();
  });
});

describe("DemoChipsDrawer — single picks section", () => {
  it("renders_section_header_and_all_10_chips", () => {
    render(<DemoChipsDrawer onPick={vi.fn()} />);
    fireEvent.click(screen.getByTestId("demo-chips-trigger"));

    expect(screen.getByTestId("demo-section-single")).toBeInTheDocument();
    expect(DEMO_CHIPS).toHaveLength(10);

    // Spot-check a couple of recognizable labels render.
    expect(screen.getByText(/UC Berkeley · Computer Science/)).toBeInTheDocument();
    expect(screen.getByText(/NYU · Film/)).toBeInTheDocument();
  });

  it("chip_click_fires_onPick_with_full_school_payload", () => {
    const onPick = vi.fn();
    render(<DemoChipsDrawer onPick={onPick} />);
    fireEvent.click(screen.getByTestId("demo-chips-trigger"));
    fireEvent.click(
      screen.getByTestId("demo-chip-single-110635-computer-science"),
    );
    expect(onPick).toHaveBeenCalledTimes(1);
    const chip = onPick.mock.calls[0]?.[0];
    expect(chip?.school.unitid).toBe(110635);
    expect(chip?.school.name).toBe("University of California-Berkeley");
    expect(chip?.majorText).toBe("Computer Science");
  });
});

describe("DemoChipsDrawer — comparison pairs section", () => {
  it("renders_section_header_subtitle_and_3_pairs", () => {
    render(<DemoChipsDrawer onPick={vi.fn()} />);
    fireEvent.click(screen.getByTestId("demo-chips-trigger"));

    expect(screen.getByTestId("demo-section-comparisons")).toBeInTheDocument();
    // Header + subtitle are intentionally neutral — no spoilers.
    expect(screen.getByText(/Try some comparisons/i)).toBeInTheDocument();
    expect(
      screen.getByText(/same field of study at 2 different schools/i),
    ).toBeInTheDocument();
    expect(DEMO_COMPARISONS).toHaveLength(3);

    // Each pair renders a row identified by major slug.
    expect(
      screen.getByTestId("demo-comparison-computer-science"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("demo-comparison-industrial-engineering"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("demo-comparison-marketing"),
    ).toBeInTheDocument();
  });

  it("each_pair_renders_both_chips_as_plain_school_labels_no_judgement", () => {
    render(<DemoChipsDrawer onPick={vi.fn()} />);
    fireEvent.click(screen.getByTestId("demo-chips-trigger"));

    // CS row: both Berkeley and BU appear as the two options. Neither
    // chip carries a "Better ROI" / "Higher cost" tag — let the build
    // tell the story when the user clicks.
    const csRow = screen.getByTestId("demo-comparison-computer-science");
    expect(
      within(csRow).getByTestId("demo-chip-compare-110635-computer-science"),
    ).toBeInTheDocument();
    expect(
      within(csRow).getByTestId("demo-chip-compare-164988-computer-science"),
    ).toBeInTheDocument();
    expect(within(csRow).queryByText(/Better ROI/i)).toBeNull();
    expect(within(csRow).queryByText(/Higher cost/i)).toBeNull();
  });

  it("worse_chip_click_fires_onPick_with_boston_university_cs_payload", () => {
    const onPick = vi.fn();
    render(<DemoChipsDrawer onPick={onPick} />);
    fireEvent.click(screen.getByTestId("demo-chips-trigger"));
    fireEvent.click(
      screen.getByTestId("demo-chip-compare-164988-computer-science"),
    );
    expect(onPick).toHaveBeenCalledTimes(1);
    const chip = onPick.mock.calls[0]?.[0];
    expect(chip?.school.unitid).toBe(164988);
    expect(chip?.school.name).toBe("Boston University");
    expect(chip?.majorText).toBe("Computer Science");
  });

  it("better_chip_click_for_indiana_marketing_fires_onPick", () => {
    const onPick = vi.fn();
    render(<DemoChipsDrawer onPick={onPick} />);
    fireEvent.click(screen.getByTestId("demo-chips-trigger"));
    fireEvent.click(screen.getByTestId("demo-chip-compare-151351-marketing"));
    expect(onPick).toHaveBeenCalledTimes(1);
    const chip = onPick.mock.calls[0]?.[0];
    expect(chip?.school.unitid).toBe(151351);
    expect(chip?.majorText).toBe("Marketing");
  });

  it("comparison_chips_render_with_neutral_styling — no green/amber spoilers", () => {
    render(<DemoChipsDrawer onPick={vi.fn()} />);
    fireEvent.click(screen.getByTestId("demo-chips-trigger"));

    const ge = screen.getByTestId("demo-chip-compare-139755-industrial-engineering");
    const nw = screen.getByTestId("demo-chip-compare-147767-industrial-engineering");
    expect(ge.className).not.toContain("text-accent-thrive");
    expect(ge.className).not.toContain("text-accent-alert");
    expect(nw.className).not.toContain("text-accent-thrive");
    expect(nw.className).not.toContain("text-accent-alert");
  });
});

describe("DemoChipsDrawer — disabled", () => {
  it("disabled_blocks_chip_clicks — single-pick chips inert", () => {
    const onPick = vi.fn();
    render(<DemoChipsDrawer onPick={onPick} disabled />);
    fireEvent.click(screen.getByTestId("demo-chips-trigger"));
    fireEvent.click(
      screen.getByTestId("demo-chip-single-110635-computer-science"),
    );
    expect(onPick).not.toHaveBeenCalled();
  });

  it("disabled_blocks_chip_clicks — comparison chips inert", () => {
    const onPick = vi.fn();
    render(<DemoChipsDrawer onPick={onPick} disabled />);
    fireEvent.click(screen.getByTestId("demo-chips-trigger"));
    fireEvent.click(
      screen.getByTestId("demo-chip-compare-164988-computer-science"),
    );
    expect(onPick).not.toHaveBeenCalled();
  });
});
