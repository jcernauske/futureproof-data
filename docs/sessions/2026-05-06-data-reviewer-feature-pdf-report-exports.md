# Session Log — 2026-05-06 Data Reviewer — feature-pdf-report-exports

| Field | Value |
|---|---|
| Session ID | 2026-05-06-data-reviewer-feature-pdf-report-exports |
| Timestamp (start) | 2026-05-06T20:37:46 (local) |
| Agent | @fp-data-reviewer |
| Spec | `docs/specs/feature-pdf-report-exports.md` |
| Status set | §5 → CHANGES REQUESTED |

## Scope

Verified that every numeric input the PDF renders comes from the same Gold-zone source as the on-screen `/my-build` display and the existing `CompareView`. No re-derived numbers. Specifically traced:

- Pentagon stat values (ERN, ROI, RES, GRW, AURA)
- Cost & ROI strip on My Build PDF page 1: 4-year cost, modeled debt, year-1 median earnings, break-even year
- 5-row Career Risk Profile: WIN/DRAW/LOSE → Low/Moderate/Elevated/High mapping with explicit threshold table per boss
- Comparison PDF leading-cell direction per row
- Same-major guard's 4-digit CIP family logic
- "Where each school pulls ahead" autogen sentence feasibility
- QR code URL composition

## Actions Taken

1. Read the spec in full (902 lines, three reads to handle the size).
2. Read `backend/app/services/boss_fights.py` to extract `BOSS_SPECS` thresholds and the per-boss `_score_*` functions to determine the score scale for each boss.
3. Read `backend/app/services/stat_engine.py` (lines 170–260) to confirm `published_cost_4yr` is the residency-aware cost field and to verify ROI is a "15-year payback multiplier", not a break-even year.
4. Read `backend/app/models/career.py` in full to extract the `CareerOutcome` field schema and confirm provenance comments on `published_cost_4yr` (line 108) vs `net_price_annual` (line 102).
5. Read `frontend/src/components/build-results/FinancesCard.tsx` to confirm which CareerOutcome fields the on-screen cost display uses (`published_cost_4yr` for "Published cost (4 yr)", `net_price_annual` for "Avg net price after aid", `earnings_1yr_median` for "Starting salary", `modeled_total_debt` for "Modeled debt").
6. Read `frontend/src/components/menu/CompareView.tsx` (selected sections) to confirm `bestIndex(values, direction: "high"|"low")` precedent for leading-cell logic and to confirm the comparison view already reads `published_cost_4yr` / `modeled_total_debt` / `earnings_1yr_median` per `compare_builds`.
7. Read `backend/app/services/builds.py` (lines 415–527) to confirm the `compare_builds` shape and `build_id` slug stability.
8. Read `frontend/src/App.tsx` to verify whether `/build/:build_id` route exists. **Confirmed it does NOT exist — the QR code URL in the spec points to a route that would 404.**
9. Searched for `payback` / `break_even` / `breakeven` across the backend and frontend codebases. **Confirmed no existing field corresponds to "break-even year"; the closest is the 15-year payback multiplier (the ROI stat).**
10. Searched for `cipcode[:5]` and `cip_family` across backend and src/silver to confirm the project uses TWO different conventions: `cipcode[:2]` for the 2-digit family in the Silver pipeline, `cipcode[:5]` for the 4-digit family in `intent.py`. The spec's "4-digit CIP family" means `cipcode[:5]` and that is correct.

## Decisions Made

### Concrete `risk_level_for_boss` threshold table

Wrote an explicit per-boss threshold table into §5 of the spec that maps every `(boss_id, raw_score)` pair to one of `Low / Moderate / Elevated / High`, derived deterministically from `BOSS_SPECS.{win_at_or_above, draw_at_or_above}` plus a `floor(draw_at_or_above / 2)` cutoff for the "High" bucket.

Rationale: the §4 docstring suggested "worst quartile of raw_score across the dataset" for "High". I rejected that approach because (a) it requires a DuckDB scan the PDF service does not have, (b) it is non-deterministic across runs as the dataset evolves, and (c) it would split one student's outcome based on what other students got — a property the in-app boss math deliberately does NOT have. The `floor(draw / 2)` rule keeps the PDF deterministic and traceable to existing constants.

Worked example: `loans` has `draw_at_or_above=5`, so `floor(5/2) = 2`. Any `raw_score <= 2` for the loans boss → High. This carves "the worst third of LOSE" off as the new "High" bucket while leaving the rest of LOSE as "Elevated" (3–4), DRAW as "Moderate" (5–6), and WIN as "Low" (≥ 7).

### Comparison PDF leading-cell direction

Wrote an explicit row-by-row direction table into §5. Direction per row:

- ERN, ROI, RES, GRW, AURA, year-1 earnings → higher wins
- 4-year cost, modeled debt → lower wins
- Break-even year → earlier (lower) wins (assuming the field gets resolved per Concern #2)
- Risk level → "Lowest" risk wins (Low > Moderate > Elevated > High)

Tie-handling: ties get no highlight. Null cells never lead.

### Source-of-truth contract table

Wrote a field-by-field table into §5 mapping every PDF element to its `CareerOutcome` source field, the line in `models/career.py` where it's defined, and the on-screen surface that uses the same field. This is the contract the PDF service must read from verbatim — no recomputation.

## Findings That Required Status: CHANGES REQUESTED

Four concerns identified, one of which is a hard blocker:

1. **(Blocker)** "Break-even year" cell on §3.5 and §3.6 has no corresponding `CareerOutcome` field. The closest existing concept is the 15-year payback multiplier (which IS the ROI stat). Implementor would have to invent a derivation, producing a number that exists nowhere else in the app — exactly the "no numeric drift across surfaces" failure this review exists to prevent.
2. **(Significant)** `risk_level_for_boss` "High" threshold was left to this review. Confirmed deterministically per the threshold table above. Spec must be updated.
3. **(Significant)** QR code URL `{public_app_base_url}/build/{build_id}` points to a frontend route that does not exist. `App.tsx` has no `/build/:build_id` route. Either add the route or change the URL composition.
4. **(Significant)** Crosswalk confidence (`Build.career.match_quality`) is not surfaced on the PDF. A `scorecard_only` build looks identical to a `full` build. Either add a one-line caveat for non-`full` builds OR add an explicit Out-of-Scope reasoning. (Note: `feedback_no_substitution_caveat.md` says don't show "Limited data" warnings *from CIP substitution* — that's a different signal from `match_quality`, which is sourced from data coverage.)

Plus four minor changes (cost-strip null handling test, `Build.cipcode` vs `Build.career.cipcode` clarification, the leading-cell direction table going into §3.6, and the source-of-truth contract going into §4).

## Artifacts Produced

- `docs/specs/feature-pdf-report-exports.md` §5 — `### @fp-data-reviewer Review` filled in. Status set to CHANGES REQUESTED. Verdict checkbox set. The `### @fp-architect Review` section was preserved untouched (filled in by the parallel agent).
- This session log.

## Rationale (Why CHANGES REQUESTED, not REJECTED)

The data spine is fundamentally sound: every number the PDF renders has a clean path back to a single `CareerOutcome` field, the `compare_builds` shape already exposes everything needed, and `build_id` is a stable slug. The four concerns are addressable without rearchitecting the PDF — three of them are scope clarifications (specify the threshold, fix the URL, surface match_quality) and one is a small spec edit (resolve break-even year). REJECTED is reserved for fundamentally wrong crosswalk tier or a stat formula using the wrong source. None of those apply here.

---

# Round 2 Re-Review — 2026-05-06

## Context

Spec author applied edits in response to the four round-1 conditions (1 blocker, 3 significant). Re-review verifies each condition against the current spec.

## Verifications

### Condition 1 — Break-even (Blocker): RESOLVED

User picked option (b): replaced the cell with `Build.career.debt_to_earnings_annual` rendered as `f"{v * 100:.0f}%"`. Confirmed:

- Field exists on `CareerOutcome` (`backend/app/models/career.py:91`).
- Field is shown on `FinancesCard.tsx:193-196` as a categorical color-coded label ("ROI: Strong / Solid / Caution / Risky"), NOT as a raw %.
- The PDF rendering raw % is a new display abstraction for an existing field. Same source, different granularity. NOT drift in the source-of-truth sense — counselor sees consistent info at two granularities.
- §3.6 Comparison PDF row updated (4-year cost / Modeled debt / Year-1 earnings / Debt-to-earnings).
- Leading-direction "lower wins" called out in §3.6 explicitly. Consistent with §5 leading-direction table.
- One stale row remains in the §5 round-1 leading-direction table (line 1113 still lists "Break-even year") — this is preserved round-1 history, and the round-2 update notes it.

### Condition 2 — Threshold table (Significant): RESOLVED with one residual

The §4 docstring at `pdf_copy.py:risk_level_for_boss` (lines 664-684) now references the §5 deterministic per-boss table and explicitly rejects dataset-relative quartile cuts. Summary form is correct.

**Residual:** Line 679 says `raw_score is None → "High" (worst-case for missing data)`. Round-1 review explicitly ruled this should render an "Insufficient data" 5th chip and NOT default to High (lines 1081, 1089). This is the "missing data is not zero" failure mode — counselor reads "High Risk" as a finding, not as missing data.

This is a docstring contradiction with the §5 contract. The §5 round-1 contract is unambiguous and governs. Logged as Follow-up C (significant — must fix before code lands), but does not block APPROVED for the spec because the contract layer is correct.

### Condition 3 — QR URL (Significant): RESOLVED

QR fully cut. Verified across §1, §2, §3.2, §3.5, §3.8, §3.9, §4 file table, §4 service signatures, §4 router, and the test list. Three stale prose references remain (cosmetic, not load-bearing):

1. §3.1 line 232 — "sources/QR footer" → should be "sources footer"
2. §3.1 line 236 — "sources line and QR code are drawn" → should drop "and QR code"
3. §4 line 851 — "Mocked QR code library" test data note → should be removed (no QR test exists)

Logged as Follow-up B.

### Condition 4 — match_quality caveat (Significant): RESOLVED

The spec now has:
- §3.5 conditional caveat block (lines 344-348) with two copy templates (`scorecard_only`, `partial_no_onet`)
- §4 `pdf_copy.py:data_coverage_caveat(build) -> str | None` (lines 709-721) with docstring documenting the three-way branch and the distinction from the substitution caveat
- P0 test (`test_data_coverage_caveat_returns_none_for_full_match_quality`) and P1 test (`test_partial_match_quality_renders_caveat_line`)

This matches round-1's recommended option (a). The data-coverage signal is now honestly surfaced to the counselor.

### Additional finding — Comparison PDF debt-to-earnings exposure

`compare_builds` does NOT currently expose `debt_to_earnings_annual` (lines 497-516). The Comparison PDF can either:
1. Read directly from each `Build.career.debt_to_earnings_annual` (recommended — router loads Builds by id anyway), OR
2. Extend `compare_builds` to expose it.

Logged as Follow-up D — implementor's call.

## Round-2 Follow-ups

| ID | Severity | Description |
|---|---|---|
| A | Minor | §3.5 should note the raw-% PDF rendering is a new display abstraction (same source as the on-screen categorical label, different granularity). |
| B | Minor | Clean up 3 stale QR references in §3.1 and §4. |
| C | **Significant** | Fix `risk_level_for_boss` docstring (line 679): `raw_score is None → "Insufficient data"` chip, not "High". The round-1 §5 contract governs. |
| D | Minor | Implementor picks path 1 or path 2 for comparison PDF debt-to-earnings exposure. Note in §6. |

## Verdict

**APPROVED** with Follow-up C required before code lands.

The data spine is correct end-to-end:
- Every number traceable to a `CareerOutcome` source field
- Threshold table deterministic (no DuckDB scan, no dataset-wide cuts)
- Crosswalk-confidence signal honestly disclosed via `data_coverage_caveat`
- QR-route hazard removed entirely
- Comparison PDF leading-directions explicit

Follow-up C is a docstring contradiction with the §5 contract. The contract supersedes the docstring summary; implementer must render the unknown-data state as a 5th "Insufficient data" chip, not silently default to "High". This reviewer will verify the implementation matches the contract during §6 build accountability — not blocking APPROVED on a docstring fix.

## Artifacts Produced

- `docs/specs/feature-pdf-report-exports.md` §5 — `#### Round 2 (re-review)` section appended below the existing round-1 review. Round-1 findings preserved untouched. Verdict updated to APPROVED with one significant follow-up.
- This session log appended.
