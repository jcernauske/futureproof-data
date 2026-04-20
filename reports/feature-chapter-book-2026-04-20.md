# Completion Report — feature-chapter-book

**Spec:** `docs/specs/completed/feature-chapter-book.md`
**Status:** COMPLETE
**Session:** 2026-04-19 → 2026-04-20
**Author:** Jeff Cernauske + Claude Code
**Build state:** 568/568 frontend tests green · 1022/1022 backend tests green · tsc clean · ruff clean · mypy 0 new errors · vite production build clean

---

## What shipped

`/set-your-course` now has a Chapter Book career progression reveal. When the student taps a career row in the common/uncommon tiered list, the right column swaps from the list into a book of up to four chapters keyed to the Silver canonical experience tiers (`entry 0–1 yr`, `early 1–4 yr`, `mid 4–8 yr`, `senior 8+ yr`). The book replaces the list with a `← Back to all paths` affordance; screen-local state cleared on Gemma re-resolution per Decision #13.

The layout also rebalanced from `desktop:grid-cols-[7fr_5fr]` → `desktop:grid-cols-[4fr_8fr]` so the book has room to breathe at ≥1200 px; below 1200 px the grid falls back to the existing single-column stack.

## Decisions locked (§2)

Sixteen decisions made it into the Decision Log. The load-bearing ones:
- **#1** Chapter Book chosen over Horizon Strip after Jeff compared both interactive mockups in Firefox.
- **#2** Replace-the-list rather than coexist — maximum focus; list comes back on `← Back`.
- **#3** Ceiling case rendered frontend-only; data-side follow-up filed as out-of-scope.
- **#9 / #12** Frontend `CareerBranch` TS interface brought into parity with backend Pydantic (added `experience_years | experience_tier | experience_delta | related_education_level`); backend added a typed `related_education_level` field instead of regex-parsing the `unlock` display string.
- **#10 / #14 / #15 / #16** Verbatim ceiling rule (terminating vs bridge), Silver-canonical year labels (not the author's pre-audit `"Years 0–3"` fiction), self-referencing branch filter, honest anchor `requires_grad_degree` inheritance.

## Pipeline flow

- **ARCH REVIEW** — two `CHANGES REQUESTED` passes, then APPROVED on pass 3. First pass caught the stale frontend `CareerBranch` type; second pass caught the Silver-tier-range mismatch. Third pass clean.
- **DESIGN VISION** — @fp-design-visionary filled §3 with layout wireframes, transition springs (`springs.smooth` + 60 ms delay), token audit, `chapterCopy.ts` voice strings, a11y table. Expanded the spec's original a11y table with `aria-labelledby` wiring and dynamic testids.
- **IMPLEMENTATION** — landed in one pass across four phases: backend + type parity, pure functions + copy, components, screen integration.
- **TESTING** — @test-writer added 37 tests (13 ChapterCard, 19 ChapterBook, 5 SetYourCourseScreen).
- **DESIGN AUDIT** — @fp-design-auditor found 6 a11y-wiring violations; all resolved in one remediation pass (`useReducedMotion` gate + dynamic testids + `aria-labelledby` + skeleton `aria-busy` + lock toggle `aria-label`). Verdict flipped to APPROVED.
- **CODE REVIEW** — @faang-staff-engineer: zero critical, zero significant, five nit-level notes. APPROVED.
- **VERIFICATION** — @fp-builder ran ruff + mypy + pytest + tsc + vitest + Vite build. All green.

## Files added / modified

**Backend (minor surface):**
- `backend/app/models/career.py` — `CareerBranch.related_education_level: str | None = None`
- `backend/app/services/branch_tree.py` — populate from MCP row
- `backend/tests/services/test_branch_tree.py` — two new tests

**Frontend (where the feature lives):**
- `frontend/src/types/build.ts` — `CareerBranch` interface extended with four fields
- `frontend/src/api/mockBranches.ts`, `mockBuild.ts` — fixture updates
- `frontend/src/components/chapter-book/types.ts` (new)
- `frontend/src/components/chapter-book/chapterCopy.ts` (new)
- `frontend/src/components/chapter-book/bucketBranches.ts` (new, pure)
- `frontend/src/components/chapter-book/bucketBranches.test.ts` (new, 13 tests)
- `frontend/src/components/chapter-book/ChapterCard.tsx` (new)
- `frontend/src/components/chapter-book/ChapterCard.test.tsx` (new, 13 tests)
- `frontend/src/components/chapter-book/ChapterBook.tsx` (new)
- `frontend/src/components/chapter-book/ChapterBook.test.tsx` (new, 19 tests)
- `frontend/src/components/chapter-book/__fixtures__/branches.ts` (new)
- `frontend/src/components/BranchChip.test.tsx`, `CareerLineageSheet.test.tsx` — authorized fixture updates for the new `CareerBranch` fields
- `frontend/src/screens/SetYourCourseScreen.tsx` — grid ratio swap + `selectedChapterCareer` state + `AnimatePresence` wiring + `useReducedMotion` gating
- `frontend/src/screens/SetYourCourseScreen.test.tsx` — 5 new tests

## Known follow-ups

1. **Pipeline-side ceiling marker** — this spec rendered the ceiling chapter client-side (Decision #3). File a separate spec to move the synthesis into Silver/Gold; the verbatim rule in §2 Decision #10 is the reference so the two implementations agree.
2. **Chapter `id` attributes are not scoped by SOC** (code-review nit). Today only one book mounts at a time, so there's no collision. If a future spec ever mounts two books side-by-side (compare-two-careers), every pair of identical chapter numbers produces duplicate `id`s. One-line fix when it bites.
3. **`handleCareerSelect` preserves two side-effects** — commit telemetry (`setSelectedCareer` + `setCommittedClick`) AND opening the book. Cleanup is deferred until a separate "post-book commit affordance" spec lands; the commit path isn't redundant yet.
4. **`useEffect` on `matched_cip` fires once on mount** with a no-op `setSelectedChapterCareer(null)`. Cosmetic.
5. **Horizon Strip mockup files remain in the tree** at `frontend/src/components/horizon/` as reference material — deliberately not deleted.
6. **Chapter Book in other flows** — `/career-pick`, `/reveal`, a deep-read modal — all explicitly out-of-scope per §2 Out of Scope. Ship when their respective users need them.
7. **Chat guardrails** — `feature-chat-guardrails` remains the ship-blocker for external audience. This spec did not displace it; the work was additive.

## What worked

Three-pass arch review caught real bugs without derailing the timeline. Mockups at `/mockups/horizon` let Jeff make the Shape B vs Shape A call in Firefox in minutes — better than any written ranking would have.

Front-loading the frontend `CareerBranch` type update (Decision #9) unblocked every downstream test and kept the spec honest about what it was touching on the backend.

The product partner's initial pushback — "the response shouldn't be fewer nodes, it should be fewer dimensions" — got re-litigated by the visionary's build and ended up right in a different way than either predicted. Chapter Book won on depth-per-career; the 2-col layout + replace-the-list interaction answered the "students can't commit before scanning" critique by keeping the list one click away.

## What took longer than expected

- First arch review returned `CHANGES REQUESTED` on a spec the author (Claude) wrote. Author did not verify the frontend `CareerBranch` type, the Brightpath breakpoint tokens, or the real tap site before writing. Three-pass review is the right tool; self-verification earlier would have saved a round-trip.
- Design audit caught a11y-wiring mismatches that the implementer missed because the spec's §3.8 table grew during DESIGN VISION and wasn't cross-checked against the implementation.

## Ship path

Spec moved to `docs/specs/completed/feature-chapter-book.md`. Feature is live in the dev build; route is `/set-your-course`. No feature flag. No external exposure until `feature-chat-guardrails` ships.
