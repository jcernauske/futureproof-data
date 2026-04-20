/**
 * ChapterBook — integration tests.
 *
 * Spec: docs/specs/feature-chapter-book.md §4 New Tests Required +
 * §3.2 focus management + §3.6 loading/error states + §3 accessibility
 * contract.
 *
 * These tests render the real <ChapterBook /> component with a mocked
 * `getBranchesForSoc`. The component fetches on mount, buckets the
 * response via the real bucketBranches, and lays out chapters in a
 * stagger. We cover:
 *
 *   - Successful fetch + chapter ordering
 *   - Back button (onBack prop)
 *   - Escape key closes the book
 *   - Loading state
 *   - Error state + retry
 *   - Focus management on mount
 *   - Live-region announcement on ready
 *   - prefers-reduced-motion (P1)
 *   - ARIA labels on interactive elements (P2)
 */
import {
  describe,
  it,
  expect,
  vi,
  beforeEach,
  afterEach,
} from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react";

// Mock the tree API BEFORE importing ChapterBook so the component picks
// up the mock. No network leaves the test boundary.
vi.mock("@/api/tree", () => ({
  getBranchesForSoc: vi.fn(),
}));

import { ChapterBook } from "./ChapterBook";
import { getBranchesForSoc } from "@/api/tree";
import { makeCareer, branchesFullArc } from "./__fixtures__/branches";
import { chapterCopy } from "./chapterCopy";
import {
  resetReducedMotion,
  setReducedMotion,
} from "@/test/mocks/prefers-reduced-motion";

const getBranchesMock = vi.mocked(getBranchesForSoc);

beforeEach(() => {
  resetReducedMotion();
  getBranchesMock.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("ChapterBook — happy path", () => {
  it("fetches branches for the career SOC and renders chapters in order 1→2→3→4", async () => {
    getBranchesMock.mockResolvedValue(branchesFullArc);
    const career = makeCareer(); // soc_code: 19-4021
    const onBack = vi.fn();

    render(<ChapterBook career={career} onBack={onBack} />);

    // API is called with the career's SOC — not a hardcoded or stale value.
    expect(getBranchesMock).toHaveBeenCalledWith("19-4021");

    // Wait for the ready state.
    const chapter1 = await screen.findByTestId("chapter-1-19-4021");
    expect(chapter1).toBeInTheDocument();

    // All four chapters are present and ordered by chapter number. We
    // read them back in the order the DOM emits them (which is the
    // mount order — bucketBranches returns [anchor, early, mid, senior]).
    // Per spec §3.8 the testid is "chapter-{n}-{soc|ceiling}"; the SOCs
    // here come from branchesFullArc.
    // Narrow to the <article> cards only — the title h3s also use a
    // "chapter-N-title" testid that would otherwise collide with the
    // "chapter-N-..." card pattern.
    const chapterEls = screen
      .getAllByTestId(/^chapter-[1-4]-/)
      .filter((el) => el.getAttribute("data-chapter-kind") !== null);
    expect(chapterEls.map((el) => el.getAttribute("data-testid"))).toEqual([
      "chapter-1-19-4021",
      "chapter-2-19-1022",
      "chapter-3-19-1042",
      "chapter-4-11-9121",
    ]);

    // Chapter kinds come from bucketBranches (anchor / role / locked /
    // role for this fixture). The integration must preserve them.
    expect(chapterEls[0]!.getAttribute("data-chapter-kind")).toBe("anchor");
    expect(chapterEls[1]!.getAttribute("data-chapter-kind")).toBe("role");
    expect(chapterEls[2]!.getAttribute("data-chapter-kind")).toBe("locked"); // Master's
    expect(chapterEls[3]!.getAttribute("data-chapter-kind")).toBe("role");

    // Career title appears in the title-page header (and again on the
    // anchor card — getAllByText handles both).
    expect(screen.getAllByText(career.occupation_title).length).toBeGreaterThan(0);
  });

  it("refetches when the career SOC changes", async () => {
    getBranchesMock.mockResolvedValue([]);
    const firstCareer = makeCareer({ soc_code: "19-4021" });
    const { rerender } = render(
      <ChapterBook career={firstCareer} onBack={vi.fn()} />,
    );
    await waitFor(() => expect(getBranchesMock).toHaveBeenCalledWith("19-4021"));

    const secondCareer = makeCareer({ soc_code: "11-9121" });
    rerender(<ChapterBook career={secondCareer} onBack={vi.fn()} />);
    await waitFor(() => expect(getBranchesMock).toHaveBeenCalledWith("11-9121"));
  });
});

describe("ChapterBook — back navigation", () => {
  it("back button calls onBack exactly once per click", async () => {
    getBranchesMock.mockResolvedValue(branchesFullArc);
    const onBack = vi.fn();
    render(<ChapterBook career={makeCareer()} onBack={onBack} />);

    await screen.findByTestId("chapter-1-19-4021");
    const back = screen.getByTestId("chapter-book-back");
    fireEvent.click(back);
    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it("Esc keydown anywhere in the book calls onBack", async () => {
    getBranchesMock.mockResolvedValue(branchesFullArc);
    const onBack = vi.fn();
    render(<ChapterBook career={makeCareer()} onBack={onBack} />);

    const book = await screen.findByTestId("chapter-book-19-4021");
    // fireEvent dispatches a real KeyboardEvent on the book region; the
    // keydown handler is attached to the book ref via addEventListener.
    fireEvent.keyDown(book, { key: "Escape" });
    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it("keys that aren't Escape do not trigger onBack", async () => {
    getBranchesMock.mockResolvedValue(branchesFullArc);
    const onBack = vi.fn();
    render(<ChapterBook career={makeCareer()} onBack={onBack} />);
    const book = await screen.findByTestId("chapter-book-19-4021");
    fireEvent.keyDown(book, { key: "Enter" });
    fireEvent.keyDown(book, { key: " " });
    fireEvent.keyDown(book, { key: "Tab" });
    expect(onBack).not.toHaveBeenCalled();
  });
});

describe("ChapterBook — loading state", () => {
  it("renders the skeleton while the fetch is pending", async () => {
    // Hold the promise open so the component sits in the loading state.
    let resolve!: (v: unknown[]) => void;
    getBranchesMock.mockImplementation(
      () =>
        new Promise((res) => {
          resolve = res as (v: unknown[]) => void;
        }),
    );

    render(<ChapterBook career={makeCareer()} onBack={vi.fn()} />);

    // Skeleton present; chapters absent.
    expect(screen.getByTestId("chapter-book-skeleton")).toBeInTheDocument();
    expect(screen.queryByTestId("chapter-1-19-4021")).not.toBeInTheDocument();
    expect(screen.queryByTestId("chapter-book-error")).not.toBeInTheDocument();

    // Let the promise resolve so React can clean up before the test ends.
    await act(async () => {
      resolve([]);
    });
  });

  it("suppresses the live-region announcement while loading", async () => {
    let resolve!: (v: unknown[]) => void;
    getBranchesMock.mockImplementation(
      () =>
        new Promise((res) => {
          resolve = res as (v: unknown[]) => void;
        }),
    );

    render(<ChapterBook career={makeCareer()} onBack={vi.fn()} />);
    // The polite live region is the only node with aria-live="polite" on
    // this surface. While loading it must be empty — otherwise students
    // on screen readers hear a half-built announcement.
    const live = document.querySelector('[aria-live="polite"]');
    expect(live).not.toBeNull();
    expect(live!.textContent?.trim() ?? "").toBe("");

    await act(async () => {
      resolve([]);
    });
  });
});

describe("ChapterBook — error state", () => {
  it("renders an inline retry when the fetch rejects; book does not unmount", async () => {
    getBranchesMock.mockRejectedValueOnce(new Error("boom"));
    render(<ChapterBook career={makeCareer()} onBack={vi.fn()} />);

    const errorBlock = await screen.findByTestId("chapter-book-error");
    expect(errorBlock).toBeInTheDocument();
    // Book surface is still present — the header/title page stays; only
    // the chapter stack is replaced by the error.
    expect(screen.getByTestId("chapter-book-19-4021")).toBeInTheDocument();
    expect(screen.queryByTestId("chapter-1-19-4021")).not.toBeInTheDocument();
    // Retry affordance is wired.
    expect(screen.getByTestId("chapter-book-retry")).toBeInTheDocument();
  });

  it("retry triggers a refetch and recovers to the ready state", async () => {
    getBranchesMock
      .mockRejectedValueOnce(new Error("first attempt fails"))
      .mockResolvedValueOnce(branchesFullArc);
    render(<ChapterBook career={makeCareer()} onBack={vi.fn()} />);

    const retry = await screen.findByTestId("chapter-book-retry");
    // First call happened on mount; retry should trigger a second.
    expect(getBranchesMock).toHaveBeenCalledTimes(1);
    fireEvent.click(retry);
    await waitFor(() => expect(getBranchesMock).toHaveBeenCalledTimes(2));

    // Error cleared; chapters render.
    expect(await screen.findByTestId("chapter-1-19-4021")).toBeInTheDocument();
    expect(screen.queryByTestId("chapter-book-error")).not.toBeInTheDocument();
  });

  it("surfaces the Error message to the student, not a generic fallback", async () => {
    getBranchesMock.mockRejectedValueOnce(
      new Error("The data source was briefly unreachable. Try again in a moment."),
    );
    render(<ChapterBook career={makeCareer()} onBack={vi.fn()} />);
    const block = await screen.findByTestId("chapter-book-error");
    expect(block.textContent).toContain("briefly unreachable");
  });
});

describe("ChapterBook — focus management + announcement", () => {
  it("focus lands on the back button when the book mounts", async () => {
    getBranchesMock.mockResolvedValue(branchesFullArc);
    render(<ChapterBook career={makeCareer()} onBack={vi.fn()} />);

    // Focus lands on the back button via a useEffect on mount. That
    // effect fires before the branches resolve, so we can assert
    // synchronously — but waitFor gives us a race-free anchor under
    // strict React timing.
    await waitFor(() => {
      const back = screen.getByTestId("chapter-book-back");
      expect(document.activeElement).toBe(back);
    });
  });

  it("announces the career title + chapter count in a polite live region once ready", async () => {
    getBranchesMock.mockResolvedValue(branchesFullArc);
    const career = makeCareer({ occupation_title: "Biological Technician" });
    render(<ChapterBook career={career} onBack={vi.fn()} />);

    await screen.findByTestId("chapter-1-19-4021");
    const live = document.querySelector('[aria-live="polite"]');
    expect(live).not.toBeNull();
    // Announcement mentions the career title and the chapter count.
    // The exact phrasing is owned by ChapterBook.tsx — we assert on
    // the load-bearing substrings so a wording polish by @fp-copywriter
    // doesn't falsely break this test.
    expect(live!.textContent).toContain("Biological Technician");
    expect(live!.textContent).toContain("4 chapters");
  });

  it("uses a singular 'chapter' token for a one-chapter arc — but the book never emits one", async () => {
    // Smallest real book is 2 chapters (anchor + ceiling). Verify the
    // announcement is plural for the minimum. This guards against a
    // silly "1 chapter" render when the fetch returns zero branches.
    getBranchesMock.mockResolvedValue([]);
    render(<ChapterBook career={makeCareer()} onBack={vi.fn()} />);

    await screen.findByTestId("chapter-1-19-4021");
    const live = document.querySelector('[aria-live="polite"]');
    expect(live!.textContent).toContain("2 chapters");
  });
});

describe("ChapterBook — reduced motion (P1)", () => {
  it("renders the ready state without relying on animation completion", async () => {
    // Under prefers-reduced-motion, ChapterBook.tsx passes undefined
    // variants so the stagger is skipped — chapters mount fully
    // without waiting on the spring. We assert they're immediately
    // queryable, same as the motion-enabled path.
    setReducedMotion(true);
    getBranchesMock.mockResolvedValue(branchesFullArc);
    render(<ChapterBook career={makeCareer()} onBack={vi.fn()} />);

    // Use findByTestId so we tolerate a single microtask for the fetch
    // to resolve — but we do NOT advance timers or await animations.
    expect(await screen.findByTestId("chapter-1-19-4021")).toBeInTheDocument();
    expect(screen.getByTestId("chapter-2-19-1022")).toBeInTheDocument();
    expect(screen.getByTestId("chapter-3-19-1042")).toBeInTheDocument();
    expect(screen.getByTestId("chapter-4-11-9121")).toBeInTheDocument();
  });

  it("keeps the error state rendering under reduced motion", async () => {
    setReducedMotion(true);
    getBranchesMock.mockRejectedValueOnce(new Error("offline"));
    render(<ChapterBook career={makeCareer()} onBack={vi.fn()} />);
    expect(await screen.findByTestId("chapter-book-error")).toBeInTheDocument();
  });

  it("skeleton renders without relying on motion either", async () => {
    setReducedMotion(true);
    let resolve!: (v: unknown[]) => void;
    getBranchesMock.mockImplementation(
      () =>
        new Promise((res) => {
          resolve = res as (v: unknown[]) => void;
        }),
    );
    render(<ChapterBook career={makeCareer()} onBack={vi.fn()} />);
    expect(screen.getByTestId("chapter-book-skeleton")).toBeInTheDocument();
    await act(async () => {
      resolve([]);
    });
  });
});

describe("ChapterBook — aria-label contract (P2)", () => {
  it("back affordance exposes the spec'd aria-label and visible copy", async () => {
    getBranchesMock.mockResolvedValue(branchesFullArc);
    render(<ChapterBook career={makeCareer()} onBack={vi.fn()} />);

    const back = await screen.findByTestId("chapter-book-back");
    expect(back.getAttribute("aria-label")).toBe(chapterCopy.back.ariaLabel);
    expect(back.textContent).toContain(chapterCopy.back.label);
  });

  it("book region is labeled so AT announces 'The arc ahead for <career>'", async () => {
    getBranchesMock.mockResolvedValue(branchesFullArc);
    render(
      <ChapterBook
        career={makeCareer({ occupation_title: "Biological Technician" })}
        onBack={vi.fn()}
      />,
    );
    const book = await screen.findByTestId("chapter-book-19-4021");
    expect(book.getAttribute("role")).toBe("region");
    // Spec §3.8: section is labeled via aria-labelledby pointing at the
    // h2 that carries the career title.
    const labelId = book.getAttribute("aria-labelledby");
    expect(labelId).toBe("chapter-book-title-19-4021");
    const title = document.getElementById(labelId!);
    expect(title).not.toBeNull();
    expect(title!.textContent).toBe("Biological Technician");
  });

  it("locked-chapter toggle exposes aria-expanded and aria-controls", async () => {
    getBranchesMock.mockResolvedValue(branchesFullArc);
    render(<ChapterBook career={makeCareer()} onBack={vi.fn()} />);

    // Chapter 3 is the Master's-gated Medical Scientist in branchesFullArc.
    await screen.findByTestId("chapter-3-19-1042");
    const toggle = screen.getByTestId("chapter-lock-3");
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(toggle.getAttribute("aria-controls")).toBe("chapter-3-body");
  });
});
