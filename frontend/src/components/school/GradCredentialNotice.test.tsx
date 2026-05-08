import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import {
  GradCredentialNotice,
  type FeederMajorData,
  type GradCredentialNoticeProps,
} from "./GradCredentialNotice";

/**
 * GradCredentialNotice — component tests
 *
 * Covers:
 * - Caution tone renders the accent-caution stripe class.
 * - Info tone renders the accent-info stripe class.
 * - Feeder card tap fires onAcceptFeeder with the correct cip4.
 * - Feeders with offered_at_school=false render a "not offered" indicator.
 * - Header shows the full credential name and acronym.
 * - Body copy interpolates school name and credential acronym.
 * - Pre-flag prose override replaces the default subhead.
 */

const SAMPLE_FEEDERS: FeederMajorData[] = [
  {
    cip4: "31.05",
    cip_title: "Exercise Science",
    note: "Strong anatomy and physiology core",
    offered_at_school: true,
  },
  {
    cip4: "26.01",
    cip_title: "Biology",
    note: "Covers all prerequisite sciences",
    offered_at_school: true,
  },
  {
    cip4: "51.22",
    cip_title: "Public Health",
    note: "Population health perspective",
    offered_at_school: false,
  },
];

function renderNotice(
  overrides: Partial<GradCredentialNoticeProps> = {},
) {
  const onAcceptFeeder = overrides.onAcceptFeeder ?? vi.fn();
  const props: GradCredentialNoticeProps = {
    credentialNameFull: "Doctor of Physical Therapy",
    credentialAcronym: "DPT",
    targetCareerTitle: "Physical Therapist",
    schoolName: "Indiana University",
    feeders: SAMPLE_FEEDERS,
    tone: "caution",
    onAcceptFeeder,
    ...overrides,
  };
  const result = render(<GradCredentialNotice {...props} />);
  return { ...result, onAcceptFeeder };
}

// ---------------------------------------------------------------------------
// Tone / Stripe Tests
// ---------------------------------------------------------------------------

describe("GradCredentialNotice — tone rendering", () => {
  it("renders accent-caution stripe class when tone is caution", () => {
    renderNotice({ tone: "caution" });
    const section = screen.getByTestId("grad-credential-notice");
    expect(section.className).toContain("border-l-accent-caution");
    expect(section.className).not.toContain("border-l-accent-info");
  });

  it("renders accent-info stripe class when tone is info", () => {
    renderNotice({ tone: "info" });
    const section = screen.getByTestId("grad-credential-notice");
    expect(section.className).toContain("border-l-accent-info");
    expect(section.className).not.toContain("border-l-accent-caution");
  });
});

// ---------------------------------------------------------------------------
// Header / Copy Tests
// ---------------------------------------------------------------------------

describe("GradCredentialNotice — header and copy", () => {
  it("renders the full credential name and acronym in the header", () => {
    renderNotice();
    const heading = screen.getByRole("heading", { level: 3 });
    expect(heading.textContent).toContain("Doctor of Physical Therapy");
    expect(heading.textContent).toContain("(DPT)");
  });

  it("renders the BLS citation subhead by default", () => {
    renderNotice({ tone: "caution" });
    expect(
      screen.getByText(/Bureau of Labor Statistics/),
    ).toBeInTheDocument();
    // "Physical Therapist" appears in both the subhead and footer, so
    // use getAllByText and verify at least one match.
    const matches = screen.getAllByText(/Physical Therapist/);
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it("renders pre-flag prose override when preFlagProse is set", () => {
    const customProse =
      "Pre-PT isn't an undergrad major itself — it's a track toward DPT school.";
    renderNotice({ tone: "info", preFlagProse: customProse });
    expect(screen.getByText(customProse)).toBeInTheDocument();
    // The default BLS-citation subhead should NOT appear.
    expect(
      screen.queryByText(/Bureau of Labor Statistics/),
    ).not.toBeInTheDocument();
  });

  it("interpolates school name in the body copy", () => {
    renderNotice({ schoolName: "Purdue University" });
    expect(
      screen.getByText(/Purdue University/),
    ).toBeInTheDocument();
  });

  it("has an aria-label for accessibility", () => {
    renderNotice();
    const section = screen.getByTestId("grad-credential-notice");
    expect(section.getAttribute("aria-label")).toContain(
      "Doctor of Physical Therapy",
    );
  });
});

// ---------------------------------------------------------------------------
// Feeder Card Interaction Tests
// ---------------------------------------------------------------------------

describe("GradCredentialNotice — feeder card interactions", () => {
  it("renders all feeder cards", () => {
    renderNotice();
    screen.getByTestId("feeder-cards-row");
    // Each feeder has a data-testid like "feeder-card-31.05"
    expect(
      screen.getByTestId("feeder-card-31.05"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("feeder-card-26.01"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("feeder-card-51.22"),
    ).toBeInTheDocument();
  });

  it("calls onAcceptFeeder with the cip4 when a feeder card is tapped", () => {
    const onAcceptFeeder = vi.fn();
    renderNotice({ onAcceptFeeder });

    const exSciCard = screen.getByTestId("feeder-card-31.05");
    fireEvent.click(exSciCard);

    expect(onAcceptFeeder).toHaveBeenCalledTimes(1);
    expect(onAcceptFeeder).toHaveBeenCalledWith("31.05");
  });

  it("calls onAcceptFeeder with correct cip4 for each feeder", () => {
    const onAcceptFeeder = vi.fn();
    renderNotice({ onAcceptFeeder });

    // Click Biology card
    fireEvent.click(screen.getByTestId("feeder-card-26.01"));
    expect(onAcceptFeeder).toHaveBeenLastCalledWith("26.01");

    // Click Public Health card
    fireEvent.click(screen.getByTestId("feeder-card-51.22"));
    expect(onAcceptFeeder).toHaveBeenLastCalledWith("51.22");

    expect(onAcceptFeeder).toHaveBeenCalledTimes(2);
  });

  it("renders feeder cip_title and note text", () => {
    renderNotice();
    expect(screen.getByText("Exercise Science")).toBeInTheDocument();
    expect(
      screen.getByText("Strong anatomy and physiology core"),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Offered-at-School Visual Diff Tests
// ---------------------------------------------------------------------------

describe("GradCredentialNotice — offered_at_school visual diff", () => {
  it("does NOT render 'not offered' pill for feeders offered at school", () => {
    renderNotice();
    // Exercise Science is offered (offered_at_school=true)
    const exSciCard = screen.getByTestId("feeder-card-31.05");
    expect(
      exSciCard.querySelector('[data-testid="feeder-not-offered-pill"]'),
    ).toBeNull();
  });

  it("renders 'not offered here' pill for feeders NOT offered at school", () => {
    renderNotice();
    // Public Health is NOT offered (offered_at_school=false)
    const pubHealthCard = screen.getByTestId("feeder-card-51.22");
    const pill = pubHealthCard.querySelector(
      '[data-testid="feeder-not-offered-pill"]',
    );
    expect(pill).not.toBeNull();
    expect(pill!.textContent).toContain("not offered here");
  });

  it("renders all offered pills when all feeders are not offered", () => {
    const allNotOffered: FeederMajorData[] = SAMPLE_FEEDERS.map((f) => ({
      ...f,
      offered_at_school: false,
    }));
    renderNotice({ feeders: allNotOffered });

    const pills = screen.getAllByTestId("feeder-not-offered-pill");
    expect(pills.length).toBe(3);
  });

  it("renders no pills when all feeders are offered", () => {
    const allOffered: FeederMajorData[] = SAMPLE_FEEDERS.map((f) => ({
      ...f,
      offered_at_school: true,
    }));
    renderNotice({ feeders: allOffered });

    expect(screen.queryAllByTestId("feeder-not-offered-pill")).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// Footer
// ---------------------------------------------------------------------------

describe("GradCredentialNotice — footer guidance", () => {
  it("renders footer guidance mentioning the career title", () => {
    renderNotice();
    expect(
      screen.getByText(/Physical Therapist path/),
    ).toBeInTheDocument();
  });
});
