# Session Log — 2026-05-06 — `@fp-design-visionary` round-2 refinement pass

- **Session ID:** 2026-05-06-design-visionary-feature-pdf-report-exports
- **Timestamp:** 2026-05-06
- **Agent:** `@fp-design-visionary`
- **Spec:** `docs/specs/feature-pdf-report-exports.md` (status: DESIGN VISION)
- **Round:** 2 (refinement / validation pass — the round-1 print-design pass produced the §3 structural spec and two sample PDFs, which were the input to this session)

## Inputs

- `docs/specs/feature-pdf-report-exports.md` §3 (UI/UX Design) §3.1–§3.10
- `docs/specs/design/feature-pdf-report-exports-mybuild-sample.pdf` (round-1 sample, 2 pages, mock data)
- `docs/specs/design/feature-pdf-report-exports-comparison-sample.pdf` (round-1 sample, 1 page, 3-school)

## Scope

Refine and validate, NOT start from scratch. Four deliverables:

1. Validate samples against §3.
2. Visual judgment on two new round-2 elements: (a) 5th risk-level chip "Insufficient data" and (b) data-coverage caveat line.
3. Audit Brightpath through-line — confirm no dark-mode panel leakage.
4. Validate the round-2 cost-strip change that mixes a percent into a 4-column dollar strip.

Out of scope: copywriter-owned copy templates (verdict line, risk one-liners, glossary, static fallback questions).

## Actions

1. Read §3.1–§3.10 of the spec end-to-end.
2. Visually walked both sample PDFs page by page against §3.
3. Wrote a new `### Design Vision Refinement` block, inserted into §3 directly above `### Interactions`.
4. Made three targeted in-place edits to the existing §3 sub-sections to lock visual decisions:
   - §3.4 — added "Dark-fill usage cap" paragraph capping `INK_PRIMARY` solid fills at the top header band + thin column-header bands only.
   - §3.5 (data-coverage caveat) — added asymmetric spacing rule (`Spacer(1, 6)` above, `Spacer(1, 9)` below), left-alignment, plain rendering (no icon / bold / tint).
   - §3.5 (cost & ROI strip) — added center-alignment requirement for all 4 cells (row 0 labels and row 1 values), with rationale.
   - §3.5 (Career Risk Profile table) — widened Level column from 0.92 in to 1.10 in to fit "Insufficient data" on one line at 7.5pt; corrected chip rendering to Nunito italic 7.5pt (NOT bold) + clarified centered alignment.
5. Wrote this session log.

## Decisions Made (and Rationale)

### Sample validation

- **Three sample-vs-spec staleness items** flagged in the refinement block:
  1. Cost & ROI column 4 still shows "Break-even / Year 7" (sample) instead of "Debt-to-earnings (yr-1) / 39%" (current spec).
  2. Risk chip "LOW" rendered bold-ALL-CAPS in the sample; spec requires roman-no-caps because LOW is the "good" outcome and must read quieter than warning levels.
  3. Sample page 2 includes a QR code; §3.2 explicitly removed it per Decision #9 revision.
- **Resolution:** flag in §6 deviation log when implementation runs; samples stay as historical reference; spec is the contract.

### 5th risk-level chip (`Insufficient data`)

- Approved as proposed at the token level (`#5C5E70` ink, `#EFF0F4` bg, italic Roman sentence-case "Insufficient data") with one correction: weight is **Nunito italic 7.5pt regular, NOT bold**. The other 4 chips' bold-vs-roman distinction tracks loudness; italic is the new orthogonal axis for "this is a meta-state, not a value."
- **Rationale:** chip needs to read quieter than Low (the next-quietest), not compete with warning levels. Neutral chromaless gray reads quieter than green because it has no chroma. Italic + 17-character sentence-case "Insufficient data" makes B&W photocopy distinction from "Low" (3 chars, roman) trivial — the copy itself is the differentiator, color is doing the least work.
- **Token lock-in:** explicit rejection of `INK_MUTED` (`#767888` — too light, would read as broken render) and `INK_SECONDARY` (`#3D3E52` — too dark, would compete with warnings). New dedicated token `#5C5E70` is correct as drawn.
- **Layout:** centered, same vertical alignment as the other 4 chips. Level column widened to 1.10 in to keep on one line. "Insufficient data" is now the binding column-width constraint, not "MODERATE".

### Data-coverage caveat line

- Approved placement: between profile strip and verdict line, italic Nunito 7.5pt INK_MUTED, left-aligned.
- **Refinement:** asymmetric spacing — 6pt above, 9pt below — visually docks the caveat to the verdict line that follows, so a counselor reads it as context for the next sentence, not as the tail of the previous strip.
- **Why not the alternatives:**
  - Inline with verdict — clutters a Fredoka 20pt headline; breaks the conversation-starter tone.
  - Footer / sub-footer — counselor never reads it in a 30-second scan; data-coverage signal must live above the fold.
  - Below cost & ROI strip — would let the verdict line read as falsely confident for the first 6 inches of page 1.
  - Above profile strip — flips the hierarchy by putting caveats above the headline.
- **Conditional rendering:** when `match_quality == "full"`, the caveat AND its surrounding spacers are absent (no reserved empty band).

### Brightpath through-line audit

- Pass. The 5 stat color hues + Fredoka headlines are the only visual through-line. Stat hues appear only as: pentagon vertex dots/labels, comparison stat-row colored abbreviations, suggested-skills bucket headers — never as fills/panels/backgrounds. Fredoka appears only at: verdict, section headers, profile name, comparison title block.
- `INK_PRIMARY` solid fill appears at top header band + Career Risk Profile column-header row (My Build) + three column-header rows on Comparison page. Each is print-letterhead/print-table-header convention, not a dark-mode panel. Acceptable.
- **New constraint:** "Dark-fill usage cap" added to §3.4. Locks `INK_PRIMARY` solid fills at the current 3-band cap. No callout boxes, sidebars, hero panels, or "cover sheet" headers may be added in implementation.

### Mixed-units cost & ROI strip

- Approved as spec'd, with refinement: all 4 cells center-aligned (labels row 0 + values row 1).
- **Why center:** the 3-character percent next to 7-character dollar values in equal-width columns looks stranded if left- or right-aligned. Center kills the asymmetry without breaking the strip's row-0/row-1 symmetry.
- **Why mixed units works here:** labels do unambiguous unit-disambiguation — "4-year cost", "Modeled debt", "Year-1 median earnings", "Debt-to-earnings (yr-1)" — values can render in native units without confusion.
- **Rejected alternatives:** separate strip for percent (wasteful, breaks rhythm); 5-column strip (overcrowds live width); ratio rendering `0.39` (loses immediate readability); subscript unit annotations (unnecessary, label is explicit).
- **Final formatter:** `f"{v * 100:.0f}%"` — no leading symbol, no decimal.

## Artifacts Produced

- `docs/specs/feature-pdf-report-exports.md` — 4 in-place edits to §3.4 and §3.5 + new `### Design Vision Refinement` block inserted before `### Interactions`.
- `docs/sessions/2026-05-06-design-visionary-feature-pdf-report-exports.md` — this log.

## Handoff Notes

The 3 sample-vs-spec staleness items (cost-strip column 4, LOW chip casing, QR code) are not regressions in the design — they are pre-spec-update sample artifacts. Production renderer must follow the spec, not the sample. Flag these in §6 (Implementation Log → Deviations from Spec) as "intentional deltas from round-1 sample reference, see round-2 design refinement". `@fp-design-auditor` should mechanically catch these at audit time against the §3.4 / §3.5 token tables.

The two new visual elements (Insufficient data chip + data-coverage caveat line) are locked at token-level precision in §3.4 and §3.5. No re-rendering of samples is required for round 2 — the implementation will produce the first authoritative renders of these elements.

The `@fp-copywriter` round-2 work is parallel to this pass and was not touched (verdict-line copy templates, risk one-liners, glossary entries, static fallback questions all remain copywriter-owned).
