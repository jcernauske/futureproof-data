# Feature: Pentagon Stat Reshape — RES absorbs HMN, AURA takes HMN's slot

## Claude Code Prompt

```
Read the spec at docs/specs/pentagon-stat-reshape.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review §1-§4 (data flow, MCP tool design, stat-engine
     blend strategy, PentagonStats model migration, frontend type rename).
   - Invoke @fp-data-reviewer to assess:
       (a) the DRAFT blended-RES formula and the partial-null handling rule,
       (b) the AURA-per-institution lookup pattern (the receipt and stats
           must agree on which institution the aura_score belongs to when
           CIP substitution is in flight),
       (c) the AppliedSkill delta_hmn removal and what happens to legacy
           saved-build JSON that still carries delta_hmn entries,
       (d) the CareerBranch delta_hmn → delta_aura=0 invariant (AURA is
           institution-level so branches must NOT shift it).
   - Both write findings to §5.
   - If APPROVED: proceed to step 2.
   - If CHANGES REQUESTED (Significant): STOP, alert human.
   - If REJECTED (Blocker): STOP, alert human.

2. DESIGN VISION
   - Invoke @fp-design-visionary to confirm the AURA axis treatment:
     same pentagon, label swap on the 5th vertex, new --color-stat-aura
     token (or repurpose --color-stat-hmn). Propose copy for the AURA
     stat tutorial card and the receipt strings. Visionary writes to §3.

3. IMPLEMENTATION
   - Implement the spec as written in §3 (UI/UX) and §4 (Technical Spec).
   - BEFORE coding: Review §4 Testing Impact Analysis thoroughly.
   - DURING coding: Update any broken tests listed in "Authorized Test
     Modifications" — every other failure is a STOP-and-escalate event.
   - Log all work to §6.
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest).
   - BUILD ACCOUNTABILITY: max 3 attempts before escalating via §10.

4. TESTING
   - Invoke @test-writer to review the spec and add coverage from §4.
   - The blended-RES math, AURA-lookup-on-CIP-substitution, and the
     legacy-saved-build migration path are P0.

5. DESIGN AUDIT
   - Invoke @fp-design-auditor for token compliance on the new AURA
     axis (token name, contrast, focus state, tutorial overlay copy).

6. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests.

7. VERIFICATION
   - Invoke @fp-builder to run full build verification.

8. COMPLETION
   - Update Status to COMPLETE and check off §1 Success Criteria.
   - Generate report to reports/pentagon-stat-reshape-YYYY-MM-DD.md.

OUT OF SCOPE — REJECT as scope creep if a reviewer requests them:
  - Any change to the data pipeline (raw / silver / gold / consumable).
  - Any new consumable table or schema migration of an existing one.
  - Re-promotion of consumable.program_career_paths (the row's
    pre-computed stat_hmn stays in the row; the backend just stops
    surfacing it as its own axis and folds it into RES).
  - Imputing aura_score when consumable.institution_aura returns NULL.
  - Wiring AURA into any boss fight scorer.
  - Replacing HMN in the AI boss formula with anything other than the
    new blended RES.
  - Backwards-compat shims that try to keep the old PentagonStats.hmn
    field readable from the API. Frontend + backend cut over together.
```

---

## Status: COMPLETE — all reviews APPROVED, ready to merge.

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
| ARCH REVIEW | Awaiting @fp-architect approval |
| DESIGN VISION | @fp-design-visionary proposing §3 |
| IMPLEMENTATION | Implementing |
| TESTING | @test-writer adding coverage |
| DESIGN AUDIT | @fp-design-auditor checking token compliance |
| CODE REVIEW | @faang-staff-engineer reviewing |
| VERIFICATION | @fp-builder running full build |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-05-02 |
| Author | Jeff + Claude |
| Spec Version | 1.2 (DRAFT) |
| Last Updated | 2026-05-02 |
| Blocked By | — |
| Changelog | 1.2 — addresses v1.1 data-review findings: `_score_ai` uses `_safe_sum` (not `× 2` doubling) on partial-null inputs, receipt comment corrected (~1.05M `stat_res IS NULL` rows, not zero), 2 new P0 tests, `aura_score_basis`/`aura_score_version` formalized on `CareerOutcome` model. <br>1.1 — addresses v1.0 architect + data-reviewer findings: nuke saved builds (Decision 9, no legacy migration), `_score_ai` reads raw `stat_res + stat_hmn` from the row (Decision 4 revised), Pydantic defaults, `_apply_effort` + `recompute_for_sliders` + `Node` dataclass + `BuildSummary` callouts, expanded file inventory, receipt string conditional for None inputs |
| Related Specs | `docs/specs/full-pipeline-eada.md` (provides `consumable.institution_aura`); `docs/specs/completed/three-signal-ai-exposure-composite-v3.md` (current source of `stat_res`); `docs/specs/completed/full-pipeline-onet.md` (current source of `stat_hmn` via `hmn_score_rounded`) |

---

## §1 Feature Description

### Overview

The pentagon stays a pentagon. Five axes. Two of the axes change meaning.

1. **RES absorbs HMN.** The defensive AI score (current RES, sourced from `consumable.ai_exposure.stat_res`) and the offensive human-skill score (current HMN, sourced from `consumable.onet_work_profiles.hmn_score_rounded`) collapse into a single new RES axis that captures the full resilience spectrum — "the work needs people *and* AI can't do most of it."
2. **AURA takes HMN's slot.** The freed-up axis is now AURA — institutional brand gravity, sourced from `consumable.institution_aura.aura_score` (already landed by `full-pipeline-eada.md`). AURA is **institution-level**, not career-level: it attaches to the school, so every career outcome under a single school+major build shares the same AURA value.

Final pentagon: **ERN, ROI, RES (blended), GRW, AURA.**

This is a backend + frontend reshape only. **No data pipeline changes.** The stat engine will read AURA via a new MCP tool (`get_institution_aura`) and compute blended RES in Python from the raw `stat_res` + `stat_hmn` already on each `consumable.program_career_paths` row.

### Problem Statement

The current pentagon has two interrelated problems:

- **RES and HMN measure the same threat from two angles** (AI displacement) and visually present as two independent axes. Students reading the pentagon often see two "AI-resistance" stats and miss the institutional brand-gravity signal entirely. The pipeline already produces a strong institutional signal — `consumable.institution_aura.aura_score` — but it has nowhere to surface in the product.
- **Brand and prestige matter** for outcomes, networking, and graduate trajectories — students intuit this and feel its absence is a credibility gap in the tool. Ignoring it forces RES + HMN to carry weight they aren't designed for.

Collapsing RES + HMN into a single resilience axis frees a pentagon slot for AURA without changing the visual identity (still five stats, still a radar chart) or any boss-fight that already tested the pair (`_score_ai = RES + HMN` becomes `_score_ai = blended RES + blended RES` arithmetically — see §4).

### Success Criteria

- [x] `consumable.institution_aura` is reachable from the backend via a new MCP tool that follows the same `ToolDef` / handler / governance-attachment pattern as the existing 9 tools.
- [x] `PentagonStats.hmn` is removed from both Pydantic and TypeScript models. `PentagonStats.aura` is present and nullable.
- [x] `stat_engine.compute_pentagon` and `compute_one` populate `aura` from a single MCP lookup per build (keyed on `unitid`). The lookup is reused across every `CareerOutcome` row in the same build.
- [x] Blended RES is computed in `stat_engine` from the row's pre-existing `stat_res` and `stat_hmn`. The DRAFT formula clamps 1–10 and degrades correctly when one or both inputs are NULL (see §4 "Blended RES — DRAFT formula").
- [x] All HMN references in `boss_fights.py`, `receipts.py`, `skill_pool.py`, `skill_recs.py`, `report_gen.py`, `next_steps.py`, `guidance.py`, `ask_gemma.py`, `career_pick_qna.py`, `builds.py`, `branch_tree.py`, `career_tree.py`, `wrapped_renderer.py`, and `routers/branches.py` are removed or rewritten to reference blended RES and/or AURA.
- [x] `_score_ai` in `boss_fights.py` is rewritten to test blended RES against the existing thresholds (or against new EDA-tuned thresholds — see §2 Decision 4).
- [x] `AppliedSkill.delta_hmn` is removed; only `delta_res` remains for the resilience axis. `AppliedSkill.delta_aura` is **not** added (AURA is institution-level — skills can't shift it).
- [x] `CareerBranch.delta_hmn` is removed and replaced by `delta_aura: int = 0` (always zero — same school, same AURA — see §2 Decision 5).
- [x] Frontend `PentagonChart` renders the same 5-vertex shape with the 5th vertex labelled "AURA" using the new (or renamed) stat color token.
- [x] `STAT_EXPLANATIONS` in `frontend/src/data/statExplanations.ts` swaps the `hmn` entry for an `aura` entry with copy provided by @fp-copywriter (or stub copy in implementation, copywriter pass before merge).
- [x] Receipts (`stats_receipt`, `skill_recs_receipt`, `next_steps_receipt`) emit AURA provenance referencing `aura_score_basis` from the institution_aura row, and the blended-RES receipt cites both source scores plus the blend formula.
- [x] **Saved builds are reset.** No legacy migration. `data/builds/*.json` and `backend/data/builds/*.json` are deleted as part of the cutover. The DuckDB `builds` table is dropped and recreated on first startup with the new column shape (`aura INTEGER` in place of `hmn INTEGER`). No drop-on-parse code, no fold-into-`delta_res` legacy path. Anyone who saved a build before this spec lands rebuilds it. (See Decision 9.)
- [x] `PentagonStats.aura` and `BuildSummary.aura` declare `int | None = None` defaults so a runtime AURA NULL (institution missing from `consumable.institution_aura`) populates without raising.
- [x] `stat_engine.py`'s `_apply_effort` and `recompute_for_sliders` thread `aura=stats.aura` through their `PentagonStats(...)` constructions so `/rescore` and effort-slider shifts preserve AURA without re-fetching.
- [x] `career_tree.py`'s in-module `Node` dataclass field renames `hmn → aura`; `routers/branches.py` line 54 emits `"aura": node.aura`; `frontend/src/types/tree.ts` mirrors the rename.
- [x] `_score_ai` in `boss_fights.py` reads the raw `stat_res + stat_hmn` from the source row (plumbed through `CareerOutcome.raw_stat_res` + `raw_stat_hmn`), preserving the existing 0-20 scale and existing thresholds (win=14, draw=10) **bit-exactly**. The blend stays a presentation transformation; Fight AI does not consume it. (See Decision 4 revised.)
- [x] Full backend (ruff + mypy + pytest) and frontend (tsc + vitest + Vite production build) all pass.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | RES and HMN collapse into one **blended RES**; AURA takes the freed pentagon slot. | RES and HMN are two views of the same AI-displacement question; AURA is currently invisible despite the pipeline producing it. The pentagon shape (5 axes) stays identical so the visual identity, the share-card layout, the radar chart, and the compare overlays all keep working without redesign. | (a) Drop the pentagon to 4 stats. Rejected — visual identity is load-bearing for the share card and the design system. (b) Add a 6th axis for AURA (hexagon). Rejected — breaks every existing layout, share frame, mockup, and Wrapped frame, and the axis count is part of the brand. (c) Keep both RES and HMN; surface AURA in a sidebar/badge instead of the pentagon. Rejected — AURA would feel like an afterthought, which is exactly the failure mode the EADA pipeline was meant to fix. |
| 2 | Blended RES is computed in `stat_engine` (Python) from the existing `stat_res` + `stat_hmn` on each row. **No re-promotion of `consumable.program_career_paths`.** | The blend is a presentation-layer choice, not a domain truth. Keeping the underlying row scores intact means the next iteration of the formula (after EDA) is a stat-engine PR, not a data-pipeline run. The user's instruction is unambiguous: no pipeline changes. | (a) Add a new `stat_res_blended` column to `consumable.program_career_paths` via a Gold transformer change. Rejected — explicitly out of scope per Jeff. (b) Re-promote `consumable.ai_exposure` with a different formula. Rejected — same reason; also conflates the AI-exposure measurement with the resilience presentation. |
| 3 | The blend formula is **DRAFT** and pinned at the simplest defensible default until EDA: `round_half_up(0.5 * stat_res + 0.5 * stat_hmn)`. NULL handling: if one input is NULL, return the other; if both NULL, return NULL. Final weights flagged for `@fp-data-reviewer` via §5. | EDA needs to confirm whether the two scores are correlated enough that a 50/50 blend distorts the distribution, or whether one should dominate (e.g. RES because Karpathy/Anthropic adoption signal is stronger evidence than O*NET task counts). Shipping the simplest blend lets the rest of the reshape land while the formula is tuned. | (a) Pick weights upfront. Rejected — would need the EDA anyway, and shipping with the wrong weights stamps the wrong number on every receipt. (b) MAX. Rejected — biases optimistic and erases the conservative half of the signal. (c) MIN. Rejected — same problem in the other direction. |
| 4 (revised v1.1) | The Fight AI scorer reads the **raw** `stat_res + stat_hmn` directly off the source row, not from the blended RES. Existing thresholds (`win_at_or_above=14`, `draw_at_or_above=10`) and existing fixtures stay bit-exact. Implementation: `CareerOutcome` gets two new nullable fields `raw_stat_res: int \| None` and `raw_stat_hmn: int \| None` populated by `_row_to_outcome`. `_score_ai` sums them. The blend stays a display-only transformation. | v1.0 proposed `2 × blended_RES` to preserve the 0-20 scale, but @fp-data-reviewer showed that half-up rounding inside `_blend_res` causes 49.4% of both-present rows (287,396 of 582,291) to score one point higher under `2 × round_half_up((R+H)/2)` than under `R + H`. That silently flips +89,233 outcomes from draw/lose to win/draw, destroying the continuity-with-existing-tuning rationale. Reading raw row scores keeps every existing fixture stable AND keeps `PentagonStats.res` free to be a presentation choice (per Decision 2). | (a) Use `round_half_even` in `_blend_res`. Rejected — halves but does not eliminate the bias. (b) Halve thresholds and score from blended (1-10). Rejected — every fixture would re-tune. (c) Keep `2 × blended_RES`. Rejected — see above. |
| 5 | `CareerBranch.delta_aura` exists in the model but is **always 0**. The branch JSON shape stays compatible with the radar overlay code, which expects 5 deltas. | Branches are within-career trajectories at the same institution, so AURA is invariant by construction. Emitting `0` keeps the overlay drawing (no NaN gaps) and lets the frontend treat all 5 deltas uniformly. | (a) Drop the field entirely. Rejected — the frontend branch-detail panel iterates the 5 deltas; dropping forces a special-case in TS. (b) Compute per-target-school AURA (since branches can imply moves across institutions). Rejected — out of scope; branches as shipped don't carry a target unitid. |
| 6 | AURA is read **once per build** from the new MCP tool keyed on `unitid`. The same value is stamped into every `CareerOutcome` returned for that build. CIP substitution does **not** change AURA — a substituted CIP at the same school still sees the same school's aura_score. | AURA is institution-level by construction (`consumable.institution_aura` is keyed on UNITID alone). Repeating the lookup per career row would be wasteful (1 unitid → 1 row); CIP substitution is a major-side fallback and has nothing to do with the institution. | Per-row AURA lookup. Rejected — N identical queries. |
| 7 | When `consumable.institution_aura` returns NULL `aura_score` (the institution has neither EADA nor IPEDS-Finance coverage, or only has athletics-only data), `PentagonStats.aura` is `None` and the pentagon renders the 5th vertex at radius 0 with the value "—". No imputation, no warning banner, no "Limited data" caveat. | Per the user's standing memory ("Don't show 'Limited data' warnings on career cards from CIP substitution") and the standing rule that AURA is additive, missing institutional brand data is not the student's problem and not worth a UI hedge. The receipt explains *why* (the aura_score_basis was NULL) for anyone who taps the "?". | Show a "Limited data" badge. Rejected per memory `feedback_no_substitution_caveat.md`. Impute from a default. Rejected — would falsify the receipt. |
| 8 | The new MCP tool is named `get_institution_aura` and lives in `src/mcp_server/futureproof_server.py` next to the other 9 tools. It returns the full `consumable.institution_aura` row (all 19 columns) plus governance metadata via `attach_governance`. | The tool surface mirrors `get_ai_exposure` and `get_regional_price_parity` — a single-keyed lookup against a Gold table. Returning the full row lets receipts cite `aura_score_basis`, `coverage_tier`, and `aura_score_version` without a follow-up query. | Return only `aura_score`. Rejected — receipts need basis + version for provenance honesty. |
| 9 (new v1.1) | **Saved builds are reset; no legacy migration.** As part of this cutover: (a) delete every `*.json` file under `data/builds/` and `backend/data/builds/`; (b) drop and recreate the DuckDB `builds` table on first startup with the new column shape (`aura INTEGER` replacing `hmn INTEGER`); (c) no drop-on-parse fallback in the loader, no fold-into-`delta_res` migration for `AppliedSkill.delta_hmn`, no shim of any kind. The `Build`/`BuildSummary` Pydantic models simply do not know about `hmn` after this spec lands. | The hackathon-stage product has a small known set of saved builds (the demo build + a handful of dev builds). The user explicitly waived back-compat. Without this decision the spec carries non-trivial complexity: a DuckDB column-add migration, a Pydantic legacy-parse path, an `AppliedSkill.delta_hmn → delta_res` re-bucket on legacy load, plus tests for each. All of that is wasted effort if no real user has a saved build to migrate. Reset is faster, safer, and matches the project's hackathon timeline. | (a) Migrate (the v1.0 plan). Rejected — see complexity above. (b) Migrate column, drop JSONs. Rejected — half-measure. (c) Provide a CLI to convert legacy JSONs. Rejected — out of scope; user explicitly waived. |

### Constraints

- **No data pipeline changes.** No raw, silver, gold, or consumable transformer touches. No schema migration. No re-promotion.
- **No new consumable tables.**
- **Blended RES formula is DRAFT** — the simplest defensible default ships first; EDA tunes weights in a follow-up that touches `stat_engine.py` only.
- **AURA is institution-level only.** No per-career AURA. No imputation. No skill deltas affect AURA. No branch deltas affect AURA.
- **Backend and frontend cut over together.** No `hmn` field hangs around in either model for "compat."
- **No legacy build migration code.** Per Decision 9, saved builds are deleted as part of the cutover. The loader does not handle `hmn` in the JSON — it does not need to. The `builds` DuckDB table is dropped and recreated.
- The pentagon stays a pentagon (5 axes). The radar shape, the compare overlays, the share frame, and the mockups all must keep working with the same shape.

---

## §3 UI/UX Design

> @fp-design-visionary pass — v1.2. The emotion target on the pentagon doesn't change: **discovery and pride**. The shape is the same shape. What changes is the meaning of one vertex, and that vertex now carries a stat that some students' schools do not have. The design has two jobs: (1) make AURA feel like it always belonged on the pentagon — same visual rhythm, distinct semantic temperature — and (2) make the missing-data case read as "we don't have this signal for your school yet" rather than "your school scored zero." Honesty without hedge.

### Mockups

The pentagon visual is unchanged. Only the 5th vertex changes from "HMN" → "AURA". The remaining four axes (ERN, ROI, RES, GRW) keep their colors and positions.

```
                  ERN  (gold — #F2D477)
                  ●─10
                 ╱  │  ╲
              ROI   │   AURA         (formerly HMN — new color, see below)
       (green ●     │     ● amber)
              ╲     │     ╱
               ╲    │    ╱
              RES───┼───GRW
       (purple ●        ● blue)
       (blended RES + HMN — keeps purple, the AI/tech color)
```

**Missing-data state** (the 1-in-10 case where `stats.aura is None`):

> **Revision 2026-05-02 (post-shipping user review):** The "open ring at outer perimeter" treatment originally proposed below was REVERSED after Jeff observed it visually reads as "high score everywhere" — the polygon fill dominates the visual weight and the ring + em-dash hints don't disambiguate. Final shipping behavior: missing vertices render at radius 0 (center). The polygon visibly shrinks at missing axes. The em-dash label (`AURA —`) carries the "missing, not zero-scored" signal. The popover (when tapped) still surfaces the conditional explanation line. This is the honest visual: missing data should not inflate the shape.

```
                  ERN
                  ●─10
                 ╱  │  ╲
              ROI   │   AURA  ← vertex draws at radius 0
              ●     │     ◌    open ring, no fill, color drops to text-muted
              ╲     │     ╱    label reads "AURA" with a subscript dash "—"
               ╲    │    ╱     tap target persists; popover still works and
              RES───┼───GRW    explains why this signal is unavailable here.
              ●         ●
```

Stat tutorial overlay copy (first build only — three of the five cards already exist for ERN, ROI, GRW; this spec rewrites the RES card and replaces the HMN card with an AURA card):

**RES card (rewrite — replaces current copy):**
- Title: `AI Resilience`
- Body (≈155 chars): `How well your career holds up against AI. Blends two signals: how much the work still needs people, and how poorly automation actually does it today.`
- Source line: `Source: Karpathy AI Exposure + Anthropic Economic Index + O*NET task profiles`

**AURA card (new — replaces the current HMN card):**
- Title: `Brand Gravity`
- Body (≈155 chars): `How much weight your school's name carries — endowment per student, marketing reach, athletic budget. Real signal, not vibes. Some schools don't have it yet.`
- Source line: `Source: IPEDS Finance + EADA athletics`

The "Some schools don't have it yet" tail is doing real work: it pre-frames the `—` rendering for the ~10% of unitids whose institution has no `consumable.institution_aura` coverage, so when those students see the open ring on their pentagon they read it as "the data isn't there for my school" rather than "my school scored zero." This is the compromise that honors the standing memory `feedback_no_substitution_caveat.md` (no "Limited data" warning banner on the card itself) while still being honest at the moment the student sees the empty vertex.

**Receipt strings** — final shipping copy (revised from the §4 stub for Brightpath voice; receipts remain the technical truth surface, but human-readable where it costs nothing):

Blended RES line:
- Both inputs present: `RES X/10 ← blended from stat_res Y + stat_hmn Z (50/50 mean, draft)`
- `stat_hmn` NULL: `RES X/10 ← stat_res only (no O*NET task signal for this SOC)`
- `stat_res` NULL: `RES X/10 ← stat_hmn only (no AI exposure signal for this SOC)`

AURA line:
- Present: `AURA X/10 ← {basis_label} (institution-level)` where `basis_label` is the human-readable mapping below, NOT the raw enum code. The raw `aura_score_basis` value gets one extra hop through a `_humanize_basis()` helper so receipts stay legible.
- Missing: `AURA — (no brand-gravity data for this school yet)` — the unitid number is dropped from the user-facing string. unitid is a debugging detail, not a receipt detail; if engineers need it they can pull it from logs. The student already knows which school they're looking at.

`_humanize_basis` mapping:

| Raw `aura_score_basis` | Human-readable `basis_label` |
|------------------------|------------------------------|
| `three_term` | `endowment + marketing + athletics` |
| `two_term_finance_only` | `endowment + marketing (no athletics signal)` |
| `two_term_no_endowment` | `marketing + athletics (no endowment signal)` |
| `one_term_marketing_only` | `marketing reach only` |
| `NULL` | (this branch shouldn't fire — `aura_score` would be NULL too, so we render the missing-data line above) |

Rationale: the raw codes (`three_term`, `one_term_marketing_only`) are pipeline-internal taxonomy. They're correct, but a receipt is a student-facing surface and these strings will land in the Wrapped recap, the share card, and any "Why?" tap. Brightpath voice is data-honest, not data-jargony. Keeping the raw enum on the `CareerOutcome.aura_score_basis` field for tooling and contracts, then converting at the receipt boundary, is the cleanest split — pipeline truth in, human language out. `_humanize_basis` lives in `receipts.py` next to the existing receipt formatters.

### Interactions

No new interactions on the pentagon shape itself. The reroll mechanic, the boss flow, the radar animation, and the overlay compare all stay the same. The 5-vertex iteration in `PentagonChart.tsx` (lines 22-28) picks up the new key list with zero structural change.

**Three places interaction behavior changes for the AURA-missing case:**

1. **Pentagon vertex render.** When `stats.aura === null`, the 5th vertex draws at radius 0 (collapses into the center) but the vertex DOT renders as an **open ring** (1.5px stroke, no fill, stroke-color `text-muted` at 60% opacity) at the outer-perimeter position so the pentagon outline stays a regular pentagon — the geometry doesn't degenerate into a quadrilateral, which would visually shout "broken." The radar polygon fill simply doesn't extend to that vertex (the area path uses `null`-skip so the fill stops at the RES and GRW vertices and the AURA region reads as "a missing slice of the area," not "a zero slice." The visual difference matters: zero implies measurement, missing implies absence.

2. **Stat label.** The "AURA" label below the vertex stays at full opacity in the AURA token color, but receives an em-dash suffix: `AURA —`. The em-dash is the same Brightpath convention used in the receipt missing-data line. The numeric value that would normally read `7/10` in `font-data` does not render at all (no `—/10`, no `0/10`).

3. **Popover (the "?" Stat Info Popover, DESIGN.md §Stat Info Popover).** The popover trigger is still active — tapping `?` next to AURA on a missing-data build opens the standard popover, which renders the AURA card body verbatim ("How much weight your school's name carries…") plus a single appended line in `font-body`, 13px, `text-muted`, separated by an 8px top margin: `Not enough institutional data for {school name} to score this yet.` This appended line is conditional on `stats.aura === null` and is the only place the missing-data state speaks in full sentences. It honors the no-warning-banner rule (it's not a warning, it's an explanation in the explainer) and it gives the curious student the answer in one tap without ever putting "Limited data" anywhere on the card grid.

**Why no banner, no toast, no card-edge tint:** per the standing memory `feedback_no_substitution_caveat.md`, hedging the card surface trains students to mistrust the rest of the data. The `—` and the open ring are honest visual states, not warnings. The popover handles the curious case. Anything more would be the failure mode the memory is specifically guarding against.

### Responsive Behavior

Identical to current pentagon. The radar SVG is intrinsically responsive. The open-ring missing-data dot uses the same SVG `<circle>` element as the filled vertex dots — only the `fill` and `stroke` attributes change — so it scales with the rest of the chart automatically. On mobile (`<480px`), where the vertex labels already truncate to 3-letter codes, the em-dash suffix on `AURA —` reads compactly and does not push the label off the radar's bounding box (verified against existing `screen-06-reveal-stats.html` mockup at the smallest breakpoint).

### Brightpath Design References

**Token decision: introduce a NEW `--color-stat-aura` token. Do NOT rename `--color-stat-hmn`.**

Two reasons. First, the pink `#E88BA9` belongs to `--color-accent-empathy` semantically — it's the warm-human color, used everywhere from boss-burnout to empathy pills. Renaming the stat alias to AURA would either (a) leave the empathy accent unmoored, or (b) force AURA to carry "warmth/human" connotation, which directly contradicts what AURA measures (institutional weight, brand, money). Second, the five existing stat colors are already mapped onto the warm/cool semantic axis (gold-money, green-growth, purple-AI, blue-expansive, pink-human). AURA needs a sixth temperature: **weight**. Deep amber-copper is the right answer — it reads as "money you can feel," "patina on a brass plaque," "institutional gravity." It's distinct from the existing gold ERN (which is bright lemon-gold for "earnings flow") because amber-copper is denser, older, more mass than light. ERN says "this is what you make"; AURA says "this is what your school *is*."

**Token spec:**

| Token | CSS Variable | Hex | HSL | Tailwind | Rationale |
|-------|-------------|-----|-----|----------|-----------|
| AURA (Brand Gravity) | `--color-stat-aura` | `#E8B86B` | `hsl(36, 74%, 67%)` | `text-stat-aura`, `bg-stat-aura` | Amber-copper. Heavier than ERN's lemon-gold. Reads as institutional weight, money-as-mass, the patina of established places. |

The `--color-stat-hmn: #E88BA9` token is **deleted** from `tokens.css` along with the Tailwind `text-stat-hmn` / `bg-stat-hmn` utilities. The pink hex still lives at `--color-accent-empathy` (its semantic home), so no visual content disappears from the system — only the stat-axis alias goes away.

**Contrast (WCAG 2.1 normal-text targets — AA ≥ 4.5:1, AAA ≥ 7:1):**

| Surface | Surface hex | Contrast vs `#E8B86B` | WCAG |
|---------|-------------|----------------------|------|
| `bg-deep` (page) | `#1B1D30` | **8.91:1** | AAA |
| `bg-mid` (cards) | `#232545` | **7.92:1** | AAA |
| `bg-surface` (hover) | `#2D3060` | **6.79:1** | AA, AAA-large |
| `bg-raised` (popovers) | `#3A3D75` | **5.25:1** | AA, AAA-large |
| `bg-void` (branch tree) | `#12131F` | **9.74:1** | AAA |

All readable everywhere AURA appears — pentagon labels, popover headers, receipt strings on `bg-mid`, share-card overlays on `bg-deep`. The `bg-raised` 5.25:1 is the floor; the popover title rendering with this color hits AA cleanly and far exceeds AAA-large for the popover's left-edge accent stripe (where it is a 3px decorative line, not text).

**Focus state:** AURA-tagged interactive surfaces (the Stat Info Popover trigger when AURA is the active stat, the AURA pill in receipts, the AURA stat-tile on `CareerCard`) use the global `--color-focus-ring` (info-tinted, `rgba(123, 184, 224, 0.4)`) — the standard Brightpath focus convention from DESIGN.md §Focus States. **Do NOT** introduce an amber focus ring. The whole point of `--color-focus-ring` being a single token is consistency across all stats; amber-on-amber would also collapse contrast on the trigger button.

The AURA color does, however, drive the **left-edge accent stripe** on the AURA Stat Info Popover (DESIGN.md §Stat Info Popover specifies `border-left: 3px solid {stat-color}`) — that stripe renders as `border-left: 3px solid var(--color-stat-aura)` and provides the visual link between the pentagon vertex the student tapped and the popover that appeared. Same pattern as RES (purple stripe), GRW (blue stripe), etc.

**Glow shadow:** Add `--shadow-glow-aura: 0 0 20px rgba(232, 184, 107, 0.3)` to `tokens.css` parallel to the existing `--shadow-glow-*` family. Tailwind utility `shadow-glow-aura`. Used on the AURA stat-tile selected state (parallel to the existing thrive/insight glow patterns) and on the AURA vertex dot's `vertex-glow-pulse` keyframe.

**Mockups to update:** The PRD v8 mockups (`docs/mockups/screen-06-reveal-stats.html`, `screen-04-effort-loans.html`, `screen-09-save-share.html`) all show 5-vertex pentagons with a pink HMN vertex. Each needs:
1. The 5th-vertex label swap `HMN → AURA`.
2. The CSS variable swap `var(--color-stat-hmn) → var(--color-stat-aura)`.
3. The hex swap on any inline `fill=` attributes from `#E88BA9` → `#E8B86B`.

No layout work. The mockup updates are in scope as part of the implementation pass — without them the design auditor will (correctly) flag drift.

### Accessibility

| Element | Identifier | Type | aria-label / behavior |
|---------|------------|------|----------------------|
| Pentagon SVG | `#svg-pentagon` | `role="img"` | "Five-stat radar chart showing your career stats" (unchanged) |
| AURA vertex dot (present) | `[data-stat="aura"]` | decorative | (label only — value read from text) |
| AURA vertex dot (missing) | `[data-stat="aura"][data-state="absent"]` | decorative | adds `data-state="absent"` so the vertex CSS picks up the open-ring treatment without inline styles |
| AURA stat label | `[data-stat-label="aura"]` | `<text>` in SVG | label text reads `"AURA"` (present) or `"AURA —"` (missing). The em-dash is read by screen readers as "AURA dash" — sufficient signal that there's no number here. |
| AURA Stat Info Popover trigger | `#stat-info-trigger-aura` | `<button>` | `aria-label="What is Brand Gravity?"`, `aria-expanded={open}` |
| AURA tutorial card | `#tutorial-card-aura` | `<section>` | `aria-labelledby="tutorial-card-aura-title"` — title text "Brand Gravity stat explainer" |
| AURA missing-data popover line | `#stat-popover-aura-absent` | `<p>` | rendered conditionally inside the popover when `stats.aura === null`; no separate aria-role — it's body copy in an already-announced popover |

**Reduced motion:** No new motion is introduced. The AURA vertex's open-ring treatment is a static SVG state — no animation between present and absent — so `prefers-reduced-motion` has nothing new to opt out of. The existing `vertex-glow-pulse` keyframe (DESIGN.md §CSS Keyframe Animations) is gated by the existing reduced-motion override and applies to filled vertex dots; the open ring opts out of the pulse entirely (no glow on a missing-data state — pulsing the absence would be the wrong feeling).

**Color-blind safety:** The amber `#E8B86B` and the existing yellow ERN `#F2D477` are adjacent on the warm axis. Their luminances differ by enough (~0.61 vs ~0.71 relative luminance) that they remain distinguishable under deuteranopia and protanopia simulation, but the pentagon never relies on color alone to identify a stat — every vertex has its 3-letter label rendered in `text-stat-label` typography directly below it. The label is the canonical identifier; color is the recall aid.

---

## §4 Technical Specification

### Architecture Overview

The pentagon today is a Pydantic model (`PentagonStats`) populated by `stat_engine.compute_pentagon`, which reads pre-computed `stat_*` columns from `consumable.program_career_paths` via the MCP `get_career_paths` tool. The frontend consumes the same shape verbatim.

After this spec:

```
┌───────────────────────────────────────────────────────────────────┐
│ stat_engine.compute_pentagon(unitid, cipcode, ...)                │
│                                                                   │
│   1. mcp_client.call("get_career_paths", ...) — UNCHANGED          │
│        → rows have stat_res, stat_hmn (still present in row)       │
│                                                                   │
│   2. mcp_client.call("get_institution_aura", {unitid}) — NEW       │
│        → one row: aura_score, aura_score_basis, aura_score_version │
│                                                                   │
│   3. for each row:                                                 │
│        blended_res = blend_res(row.stat_res, row.stat_hmn)         │
│        CareerOutcome(                                              │
│          stats=PentagonStats(ern, roi, res=blended_res, grw,       │
│                              aura=aura_row.aura_score),            │
│          raw_stat_res=row.stat_res,    # for Fight AI (Decision 4) │
│          raw_stat_hmn=row.stat_hmn,    # for Fight AI (Decision 4) │
│          ...                                                       │
│        )                                                           │
└───────────────────────────────────────────────────────────────────┘
```

The aura row is fetched once per `compute_pentagon` call. Every `CareerOutcome` for that build carries the same `stats.aura`. The raw `stat_res` / `stat_hmn` from the source row are preserved on `CareerOutcome` (in addition to the blended display value on `stats.res`) so Fight AI can score from the underlying inputs without consuming the rounded blend.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/mcp_server/futureproof_server.py` | Modify | Add `get_institution_aura` ToolDef + `_handle_get_institution_aura` handler. Add `INSTITUTION_AURA_TABLE = "consumable.institution_aura"` and `INSTITUTION_AURA_RESPONSE_FIELDS` constants near the top. Append the new ToolDef inside `get_tools()` (after `get_schools_for_career`). |
| `tests/mcp/test_get_institution_aura.py` | Create | Pipeline-side tests for the new MCP handler (parity with `tests/mcp/test_get_ai_exposure.py`). Cover: present row, NULL aura_score row, missing unitid, governance attachment. |
| `backend/app/models/career.py` | Modify | `PentagonStats`: rename `hmn → aura`, declare `aura: int \| None = None`. `CareerOutcome`: ADD two new nullable fields `raw_stat_res: int \| None = None` and `raw_stat_hmn: int \| None = None` (these feed Decision 4 — Fight AI reads them directly). `CareerBranch`: rename `delta_hmn → delta_aura: int = 0`. `AppliedSkill`: remove `delta_hmn` entirely. `BuildSummary`: rename `hmn → aura: int \| None = None` (was missed in v1.0). |
| `backend/app/models/api.py` | Modify | Audit for any HMN references; update. |
| `backend/app/services/stat_engine.py` | Modify | New helper `_blend_res(stat_res, stat_hmn)` (the DRAFT formula) + `_round_half_up(value)` helper if not present (use `decimal.Decimal.quantize(Decimal('1'), ROUND_HALF_UP)` — Python's built-in `round()` is banker's rounding and would give different numbers). New helper `_fetch_aura(unitid)` that calls MCP. `compute_pentagon` reads aura once per call and stamps every outcome. `_row_to_outcome` reads `row["stat_res"]` and `row["stat_hmn"]`, blends them, and emits `PentagonStats(..., res=blended, aura=aura_score)` PLUS stamps `raw_stat_res=row["stat_res"]`, `raw_stat_hmn=row["stat_hmn"]` on `CareerOutcome`. Drop the `hmn=` kwarg. **Update `_apply_effort` (lines 53-64) and `recompute_for_sliders` (lines 355-399)** — both construct `PentagonStats(...)` positionally and MUST thread `aura=stats.aura` (and `res=` from the existing blended value, not re-blend) to avoid `ValidationError` on `/rescore`. Effort/slider shifts do not change institution → AURA passes through untouched. |
| `backend/app/services/boss_fights.py` | Modify | **`_score_ai` reads raw row scores** (Decision 4 revised): `_safe_sum(career.raw_stat_res, career.raw_stat_hmn)` — sums the underlying inputs from the `CareerOutcome` (which now carries them), not the blended display value. Existing thresholds stay (`win=14`, `draw=10`); existing fixtures stay bit-exact. Reason string: `"raw stat_res {r} + stat_hmn {h} = {sum}"`. `stat_explainer`: drop the HMN bullet, rewrite the RES bullet to reflect blended display meaning while noting Fight AI scores from raw inputs, append an AURA bullet. Audit `_boss_context`. `_NARRATIVE_SYSTEM`: keep `HMN` on the forbidden stat-codes list and ADD `AURA` so Gemma never echoes either. |
| `backend/app/services/receipts.py` | Modify | `stats_receipt`: drop the HMN line. Rewrite the RES line with a **conditional branch** — when both inputs present: `"RES X/10 ← blended from stat_res Y + stat_hmn Z (50/50 mean, draft)"`; when `stat_hmn IS NULL`: `"RES X/10 ← stat_res only (no O*NET task signal — stat_hmn unavailable)"`; when `stat_res IS NULL` (~1.05M rows in `consumable.program_career_paths` — large slice, NOT zero, per @fp-data-reviewer v1.1): `"RES X/10 ← stat_hmn only (no AI exposure signal — stat_res unavailable)"`. Append an AURA line with `aura_score_basis` provenance: `"AURA X/10 ← {basis} (institution-level)"`, or `"AURA — (no institution_aura coverage for unitid {n})"` when `aura is None`. `skill_recs_receipt` + `next_steps_receipt`: drop `HMN` from inline stat dump, add `AURA`. `_skill_delta_str`: drop the HMN delta. |
| `backend/app/services/skill_pool.py` | Modify | The Gemma prompt that asks for skills with stat deltas references HMN today. Rewrite to reference blended RES (and explicitly tell Gemma not to emit deltas for AURA). Drop `delta_hmn` from the parser. The fallback skill pool has HMN deltas — re-bucket them as RES deltas (additive). |
| `backend/app/services/skill_recs.py` | Modify | Audit & strip HMN refs in the Gemma prompt and parsed shape. |
| `backend/app/services/career_pick_qna.py` | Modify | Audit & strip HMN refs in the Gemma prompt context. |
| `backend/app/services/builds.py` | Modify | **DuckDB schema reset** (Decision 9): change the `CREATE TABLE IF NOT EXISTS builds (...)` definition (lines 130-150) to use `aura INTEGER` in place of `hmn INTEGER`. Add a one-shot startup migration: `DROP TABLE IF EXISTS builds; CREATE TABLE builds (...)` so existing installs get a clean reset. Update `save_build` INSERT column list (line 247-262) and `list_builds` SELECT column list (line 310) and `BuildSummary` construction (line 335). `compare_builds`: replace `hmn` with `aura`. **No legacy-parse path**, **no `hmn`/`delta_hmn` drop-on-read**, **no fold-into-`delta_res` migration** — the JSONs are deleted, the table is dropped, this is a clean cutover. |
| `data/builds/` and `backend/data/builds/` | Delete contents | Per Decision 9: as part of the cutover, delete every `*.json` file under both directories. The directories themselves stay (empty). |
| `backend/app/services/branch_tree.py` | Modify | If it inflates branch deltas from MCP, rename `delta_hmn` → `delta_aura` and force to 0. |
| `backend/app/services/career_tree.py` | Modify | **In-module `Node` dataclass field rename** `hmn → aura` (lines 40, 111, 128, 162, 212, 272). This dataclass is what `routers/branches.py:54` reads via `node.hmn` and what `frontend/src/types/tree.ts` mirrors as `hmn: number \| null`. Also any branch-delta inflation paths follow the `delta_hmn → delta_aura=0` rule. |
| `backend/app/services/next_steps.py` | Modify | Audit & rewrite the Gemma prompt to drop HMN and add AURA. |
| `backend/app/services/guidance.py` | Modify | Audit & rewrite the Gemma's Take prompt. |
| `backend/app/services/ask_gemma.py` | Modify | Audit & rewrite the chat system prompt context. |
| `backend/app/services/report_gen.py` | Modify | Audit & rewrite the markdown report templates. |
| `backend/app/services/wrapped_renderer.py` | Modify | Rename `"hmn"` → `"aura"` in `_STAT_COLORS`, `_STAT_NAMES`, `_STAT_CONTEXT` (lines 77-99). Update the template-context emit (line 254) from `"stat_hmn": stats.hmn` to `"stat_aura": stats.aura`. **Concurrent `backend/templates/wrapped/*.html` rename** — every template that references `{{ stat_hmn }}` must rename to `{{ stat_aura }}`, and the visible "HMN" label string must become "AURA". |
| `backend/templates/wrapped/*.html` | Modify | Template variable + label rename: `stat_hmn → stat_aura`, "HMN" → "AURA". Grep first: `rg 'stat_hmn|\\bHMN\\b' backend/templates/`. |
| `backend/app/routers/branches.py` | Modify | Line 54: rename the emitted dict key `"hmn": node.hmn → "aura": node.aura` to match the renamed `Node` dataclass in `career_tree.py`. Audit other HMN refs. |
| `backend/tests/test_stat_engine.py` | Modify | New tests: `_blend_res` unit tests (both present, one None, both None, edge bounds), AURA lookup populates `stats.aura` on every outcome, CIP substitution preserves AURA, NULL aura_score → `stats.aura is None`, `_apply_effort` and `recompute_for_sliders` preserve `aura` across the round-trip, `CareerOutcome.raw_stat_res` and `raw_stat_hmn` are populated from the row. Update existing assertions that referenced `stats.hmn`. |
| `backend/tests/test_boss_fights.py` | Modify | `_score_ai` reads raw row scores via `career.raw_stat_res + career.raw_stat_hmn`. Existing fixtures stay bit-exact (Decision 4 revised). Add a new test that explicitly exercises an odd-sum row (e.g., `raw_stat_res=7, raw_stat_hmn=8 → 15 → win`) AND verifies the blended `stats.res` does NOT reach `_score_ai` (i.e., regression test that future refactors don't accidentally re-introduce the rounding bias). |
| `backend/tests/test_receipts.py` | Modify | Update expected receipt strings; add AURA-line assertions. New cases: `stat_hmn IS NULL` row emits the "stat_res only" receipt branch; `aura is None` emits the "no institution_aura coverage" branch. |
| `backend/tests/test_skill_pool.py` | Modify | Drop HMN delta assertions. The fallback skill pool's HMN deltas are re-bucketed into RES — verify the additive sum lands. |
| `backend/tests/test_builds.py` | Modify | DROP the legacy-`hmn` parse test (Decision 9 — no migration). Update existing assertions: `BuildSummary.hmn → BuildSummary.aura`. New test: starting fresh with no `builds` table, the startup migration creates the table with the `aura` column (not `hmn`). |
| `backend/tests/test_branch_tree.py` | Modify | Rename `delta_hmn` assertions → `delta_aura == 0`. |
| `frontend/src/types/build.ts` | Modify | `PentagonStats.hmn` → `PentagonStats.aura: number \| null`. `AppliedSkill.delta_hmn` removed. `CareerBranch.delta_hmn` → `delta_aura`. `BuildSummary.hmn` → `aura: number \| null`. |
| `frontend/src/types/tree.ts` | Modify | Line 14: `hmn: number \| null` → `aura: number \| null` to mirror the renamed `Node` dataclass. |
| `frontend/src/data/statExplanations.ts` | Modify | `StatKey` literal: `"hmn"` → `"aura"`. Replace the `hmn` entry in `STAT_EXPLANATIONS` with an `aura` entry. Rewrite the `res` explanation to reflect the blend. |
| `frontend/src/styles/tokens.css` | Modify | Add `--color-stat-aura` (or rename `--color-stat-hmn` → `--color-stat-aura`; @fp-design-visionary picks). |
| `frontend/tailwind.config.ts` | Modify | Add `text-stat-aura` / `bg-stat-aura` utilities (or rename). |
| `frontend/src/components/PentagonChart.tsx` | Modify | The two `keys`/`AXES` arrays at lines 22-28 and 45 swap `"hmn"` → `"aura"`. The label `"HMN"` → `"AURA"`. Color reference updates. |
| `frontend/src/components/landing/PentagonGlow.tsx` | Modify | Same axis-array swap. |
| `frontend/src/components/menu/PentagonOverlay.tsx` | Modify | Same. |
| `frontend/src/components/menu/MiniPentagon.tsx` | Modify | Same. |
| `frontend/src/components/menu/CharacterCard.tsx` | Modify | Audit for stats.hmn references. |
| `frontend/src/components/menu/CompareWinners.tsx` | Modify | Audit. |
| `frontend/src/components/build-results/PathCard.tsx` | Modify | Audit. |
| `frontend/src/components/gauntlet/SkillCard.tsx` | Modify | Drop `delta_hmn` rendering. |
| `frontend/src/components/CareerCard.tsx` | Modify | Line ~28: `STAT_ORDER` array `"hmn"` → `"aura"`. |
| `frontend/src/components/tree/SelectedNodeCard.tsx` | Modify | Line ~64: stats.hmn → stats.aura. |
| `frontend/src/components/tree/WhatItTakes.tsx` | Modify | Lines 15, 72, 76: `"hmn"` stat-key references → `"aura"`. |
| `frontend/src/components/landing/HeroSection.tsx` | Modify | Line ~44: stats.hmn → stats.aura. |
| `frontend/src/components/landing/CTARailSection.tsx` | Modify | Lines 14, 37: Tailwind class allowlist references — swap `text-stat-hmn`/`bg-stat-hmn` → `text-stat-aura`/`bg-stat-aura`. |
| `frontend/src/components/landing/HowItWorksCardArt.tsx` | Modify | Line ~17: stat-key reference → `"aura"`. |
| `frontend/src/components/horizon/ChapterBookMockup.tsx` | Modify | Lines ~67, 79: stats.hmn → stats.aura. |
| `frontend/src/screens/BuildResultsScreen.tsx` | Modify | Line ~45: `STAT_KEYS` array `"hmn"` → `"aura"`. |
| `frontend/src/screens/FutureScreen.tsx` | Modify | Line ~126: stats.hmn → stats.aura. |
| `frontend/src/api/mockBuild.ts` | Modify | Replace `hmn:` mock values with `aura:`. |
| `frontend/src/api/mockMenu.ts` | Modify | Same. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | Modify | Update HMN references. |
| `frontend/src/components/landing/DataSourcesSection.tsx` | Modify | If it lists HMN as a sourced stat, swap to AURA + cite EADA + IPEDS Finance. |
| All matching `*.test.tsx` files | Modify | After making the source changes above, run `rg -l '\\bhmn\\b\|delta_hmn\|stat_hmn' frontend/src/` and update every remaining hit. Every fixture that hand-built a `PentagonStats`/`BuildSummary`/`Node` object needs `aura` instead of `hmn`. Tailwind class allowlists in landing components must include the renamed token utilities. |
| Backend grep sweep | Verify | After implementing the typed sites, run `rg -l '\\bhmn\\b\|delta_hmn\|stat_hmn' backend/app backend/templates src/` and update every hit. Anything not covered by the table above is an oversight to fix. |

### Data Model Changes

**Pydantic** (`backend/app/models/career.py`):

```python
class PentagonStats(BaseModel):
    ern: int | None = None
    roi: int | None = None
    res: int | None = None      # now blended from stat_res + stat_hmn
    grw: int | None = None
    aura: int | None = None     # was: hmn — explicit default so missing rows parse cleanly

class CareerOutcome(BaseModel):
    # ... existing fields ...
    stats: PentagonStats
    # NEW: raw inputs to the blend, plumbed through so Fight AI can score
    # without consuming the rounded display value. (Decision 4 revised.)
    raw_stat_res: int | None = None
    raw_stat_hmn: int | None = None
    # NEW: AURA provenance, stamped from the per-build aura lookup so
    # receipts can cite basis/version without a follow-up MCP query.
    aura_score_basis: str | None = None
    aura_score_version: str | None = None

class AppliedSkill(BaseModel):
    # ...
    delta_ern: int
    delta_roi: int
    delta_res: int       # absorbs former delta_hmn impact
    delta_grw: int
    # delta_hmn REMOVED — no legacy migration (Decision 9)
    # delta_aura NOT ADDED (institution-level — skills can't shift)
    delta_burnout_raw: int
    delta_ceiling_raw: int

class CareerBranch(BaseModel):
    # ...
    delta_ern: int | None = None
    delta_roi: int | None = None
    delta_res: int | None = None
    delta_grw: int | None = None
    delta_aura: int = 0  # was: delta_hmn — institution-invariant, always 0

class BuildSummary(BaseModel):
    # ... existing fields ...
    aura: int | None = None  # was: hmn
```

**TypeScript** (`frontend/src/types/build.ts`): mirror the Pydantic changes verbatim.

### Service Changes

**New blend formula** (DRAFT — `stat_engine.py`):

```python
from decimal import Decimal, ROUND_HALF_UP

def _round_half_up(value: float) -> int:
    """Half-up rounding (NOT banker's). Python's built-in `round()` is
    half-even; we use Decimal.quantize so 0.5 always rounds away from zero."""
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _blend_res(stat_res: int | None, stat_hmn: int | None) -> int | None:
    """DRAFT: 50/50 mean of the two AI-resilience signals.

    Pending EDA. The two underlying scores measure related but distinct
    things — stat_res is adoption-level resilience (Karpathy + Anthropic
    + Gemma), stat_hmn is task-level human-essential ratio (O*NET).
    EDA needs to confirm the correlation and pick weights; until then
    a simple mean ships.

    NOTE: this rounded value is the DISPLAY value. Fight AI scores from
    the raw inputs (Decision 4 revised) so this rounding never reaches
    boss-fight outcomes.
    """
    if stat_res is None and stat_hmn is None:
        return None
    if stat_res is None:
        return stat_hmn
    if stat_hmn is None:
        return stat_res
    return _round_half_up((stat_res + stat_hmn) / 2)
```

**New AURA lookup** (`stat_engine.py`):

```python
def _fetch_aura(unitid: int) -> tuple[int | None, str | None, str | None]:
    """Return (aura_score, aura_score_basis, aura_score_version).

    All three are None when the institution has no row in
    consumable.institution_aura, or when the row has NULL aura_score
    (no marketing_ratio signal — see §6 of full-pipeline-eada.md).
    """
    result = mcp_client.call("get_institution_aura", {"unitid": unitid})
    row = result.get("data")
    if not row:
        return None, None, None
    return (
        as_int(row.get("aura_score")),
        row.get("aura_score_basis"),
        row.get("aura_score_version"),
    )
```

**`compute_pentagon` update:** call `_fetch_aura(unitid)` once before the row loop, stash the three values, and pass them to `_row_to_outcome` so each outcome stamps the same `stats.aura` and the same provenance fields. The provenance fields (`aura_score_basis`, `aura_score_version`) are added to `CareerOutcome` as nullable strings so receipts can cite them.

**Boss AI scorer** (`boss_fights.py`) — Decision 4 revised:

```python
def _score_ai(career: CareerOutcome) -> tuple[int | None, str]:
    """Sum the RAW row inputs (stat_res + stat_hmn) using the existing
    `_safe_sum` (drop-Nones-and-sum) semantics. The blend is
    presentation-only (Decision 2); Fight AI uses the underlying scores
    so existing thresholds (win=14, draw=10) and existing fixtures stay
    BIT-EXACT with pre-reshape behavior.

    Why _safe_sum and NOT `× 2` doubling on the partial-null branch:
    today's `_safe_sum` returns 0 for None inputs, so `_score_ai` on a
    row where one input IS NULL scored exactly the surviving input.
    Doubling would silently promote ~1.05M partial-null rows to
    win/draw — that contradicts the bit-exact rationale entirely
    (per @fp-data-reviewer v1.1 empirical re-check).

    Why this avoids the rounding bias `2 * round_half_up((R+H)/2)`
    would introduce: that bias silently flipped ~89k both-present rows
    from draw/lose to win/draw on odd sums."""
    raw_res = career.raw_stat_res
    raw_hmn = career.raw_stat_hmn
    if raw_res is None and raw_hmn is None:
        return None, "raw stat_res and stat_hmn unavailable"
    score = _safe_sum(raw_res, raw_hmn)  # treats None as 0; matches v0
    parts = []
    if raw_res is not None:
        parts.append(f"stat_res {raw_res}")
    if raw_hmn is not None:
        parts.append(f"stat_hmn {raw_hmn}")
    return score, f"raw {' + '.join(parts)} = {score}"
```

**MCP tool** (`src/mcp_server/futureproof_server.py`):

```python
INSTITUTION_AURA_TABLE = "consumable.institution_aura"

INSTITUTION_AURA_RESPONSE_FIELDS = [
    "unitid",
    "institution_name",
    "endowment_per_fte",
    "marketing_ratio",
    "athletic_spend_per_fte",
    "athletic_revenue_per_fte",
    "athletic_subsidy_ratio",
    "athletic_fte_source",
    "aura_score",
    "aura_score_continuous",
    "aura_score_version",
    "aura_score_basis",
    "has_ipeds_finance",
    "has_eada",
    "coverage_tier",
]

# Inside get_tools():
ToolDef(
    name="get_institution_aura",
    description=(
        "Get the institution-level brand gravity (AURA) record for a "
        "school by unitid. Returns the v1 aura_score (1-10) plus its "
        "provenance: aura_score_basis identifies which composite "
        "ingredients went into the score (three_term, "
        "two_term_finance_only, two_term_no_endowment, "
        "one_term_marketing_only, or NULL when no marketing_ratio "
        "signal was available), aura_score_version stamps the formula "
        "version, and the underlying signals (endowment_per_fte, "
        "marketing_ratio, athletic_spend_per_fte, "
        "athletic_revenue_per_fte, athletic_subsidy_ratio) are "
        "returned for receipts. has_ipeds_finance / has_eada / "
        "coverage_tier indicate which source(s) covered this "
        "institution. NULL aura_score is normal for institutions "
        "without coverage — the caller renders the AURA stat as '—'."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "unitid": {
                "type": "integer",
                "description": (
                    "IPEDS 6-digit institution identifier (e.g., 151801 "
                    "for Indiana State University). Get this from "
                    "get_school_programs or get_career_paths results."
                ),
            },
        },
        "required": ["unitid"],
    },
    handler=self._handle_get_institution_aura,
)


def _handle_get_institution_aura(self, input_dict: dict) -> dict:
    unitid = input_dict.get("unitid")
    if not isinstance(unitid, int):
        return {"data": None, "message": "unitid is required (integer)"}
    rows = self.query_iceberg_simple(
        INSTITUTION_AURA_TABLE,
        filters={"unitid": unitid},
        columns=INSTITUTION_AURA_RESPONSE_FIELDS,
        limit=1,
    )
    if rows and "error" in rows[0]:
        return self.attach_governance(
            {"data": None, "message": rows[0]["error"]},
            INSTITUTION_AURA_TABLE,
        )
    if not rows:
        return self.attach_governance(
            {"data": None, "message": "No institution_aura row for this unitid"},
            INSTITUTION_AURA_TABLE,
        )
    return self.enrich_response(
        {"data": rows[0], "row_count": 1},
        INSTITUTION_AURA_TABLE,
    )
```

**Governance contract:** `consumable.institution_aura` needs an entry under `governance/data-contracts/` with `quality_tier` and `owner` fields so the existing `attach_governance` override (lines 1289-1318 of the MCP server) emits a complete payload. If the contract file already exists from `full-pipeline-eada.md`, no new file. If not, create `governance/data-contracts/consumable-institution-aura.yaml` mirroring the shape of the BEA/Karpathy contracts.

### Testing Impact Analysis

> Search the test directories for tests touching the modified files before finalizing.

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `backend/tests/test_stat_engine.py` | every test that asserts on `stats.hmn` | High | Field renamed and value source changed (no longer 1:1 from row) |
| `backend/tests/test_boss_fights.py` | Fight AI scoring tests | Low | Formula stays `raw_stat_res + raw_stat_hmn` (Decision 4 revised reads from `CareerOutcome.raw_stat_res` + `raw_stat_hmn`). Fixtures are bit-exact stable; tests need to populate the two new fields. |
| `backend/tests/test_receipts.py` | stats_receipt / skill_recs_receipt / next_steps_receipt | High | HMN line dropped, RES line rewritten, AURA line added |
| `backend/tests/test_skill_pool.py` | skill delta parsing tests | Med | `delta_hmn` removed from the model |
| `backend/tests/test_skill_recs.py` | recommendation prompt tests | Low | Prompt text changes |
| `backend/tests/test_builds.py` | save/load round-trip | Med | Schema rename in DuckDB (`hmn → aura`) and Pydantic. NO legacy-build read test — Decision 9 reset. |
| `backend/tests/test_branch_tree.py` | delta_hmn assertions | High | Field renamed to delta_aura |
| `backend/tests/test_career_tree.py` | delta_hmn assertions | High | Same |
| `backend/tests/test_guidance.py` | Gemma's Take prompt assertions | Med | Prompt text changes |
| `frontend/src/components/PentagonChart.test.tsx` (if exists) | axis label / data shape tests | High | 5th axis renamed |
| `frontend/src/components/menu/PentagonOverlay.test.tsx` | overlay shape tests | High | Axis renamed |
| `frontend/src/components/menu/CompareView.test.tsx` | compare diff tests | Med | Stat list changes |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | reveal flow tests | High | Stat axis changes |
| `frontend/src/components/build-results/PathCard.test.tsx` (if exists) | card stat dump tests | Med | HMN row removed, AURA row added |
| `frontend/src/components/gauntlet/SkillCard.test.tsx` | delta render tests | High | delta_hmn removed |
| `tests/gold/test_futureproof_engine.py` and similar pipeline tests | row-shape assertions | None | Pipeline unchanged — must STAY GREEN. If any of these fail, that's a STOP and escalate. |
| `tests/mcp/test_*.py` for unrelated tools | governance / shape | None | Must STAY GREEN. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| All test files listed above marked High/Med | Rename `hmn` field references, swap to `aura` where appropriate. Fight AI fixtures need `raw_stat_res` + `raw_stat_hmn` populated on `CareerOutcome` (math is bit-exact stable). | Direct consequence of the model rename |
| `backend/tests/test_stat_engine.py` | Add new tests for `_blend_res` (all four NULL cases), `_round_half_up` helper, AURA-from-MCP lookup, `_apply_effort` + `recompute_for_sliders` aura preservation, `raw_stat_res`/`raw_stat_hmn` plumbing on `CareerOutcome` | New code paths need P0 coverage |
| `backend/tests/test_builds.py` | DROP any test that loads a legacy-`hmn` fixture (Decision 9). Add: startup migration creates the table with `aura` column when no table exists. | Decision 9 reset — no legacy migration path |
| `tests/mcp/test_get_institution_aura.py` | Create from scratch | New MCP handler |

#### Confirmed Safe (must NOT break — STOP if they fail)

- All tests under `tests/raw/`, `tests/silver/`, `tests/gold/` — pipeline is untouched.
- All tests under `tests/mcp/` for the existing 9 tools.
- Backend tests that don't touch stats: `test_school_lookup.py`, `test_career_tiering.py`, `test_locale.py`, `test_profile.py`.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/test_stat_engine.py` | `test_blend_res_both_present` | mean of two ints, half-up rounding |
| P0 | `backend/tests/test_stat_engine.py` | `test_blend_res_one_none` | returns the other value |
| P0 | `backend/tests/test_stat_engine.py` | `test_blend_res_both_none` | returns None |
| P0 | `backend/tests/test_stat_engine.py` | `test_compute_pentagon_stamps_aura_on_every_outcome` | one MCP aura call → all outcomes share the same `stats.aura` |
| P0 | `backend/tests/test_stat_engine.py` | `test_compute_pentagon_aura_null_when_mcp_returns_no_row` | NULL flows through to `PentagonStats.aura is None` |
| P0 | `backend/tests/test_stat_engine.py` | `test_cip_substitution_preserves_aura` | CIP substitution does not re-fetch aura under a different unitid |
| P0 | `backend/tests/test_stat_engine.py` | `test_career_outcome_carries_raw_stat_res_and_raw_stat_hmn` | `_row_to_outcome` plumbs the raw row scores onto `CareerOutcome` so Fight AI can read them |
| P0 | `backend/tests/test_stat_engine.py` | `test_apply_effort_preserves_aura` | effort shifts pass `aura` through unchanged |
| P0 | `backend/tests/test_stat_engine.py` | `test_recompute_for_sliders_preserves_aura` | slider rescore preserves `aura` |
| P0 | `backend/tests/test_boss_fights.py` | `test_score_ai_reads_raw_row_scores_not_blended` | `_score_ai(career)` returns `(raw_res + raw_hmn, "raw stat_res ... + stat_hmn ...")` and the math is independent of `stats.res` (regression guard against future re-introduction of the rounding bias) |
| P0 | `backend/tests/test_boss_fights.py` | `test_score_ai_odd_sum_bit_exact_with_v0` | a fixture with `raw_stat_res=7, raw_stat_hmn=8` scores 15 (win), bit-exact with the pre-reshape `stats.res + stats.hmn = 15` |
| P0 | `backend/tests/test_boss_fights.py` | `test_score_ai_partial_null_uses_safe_sum_not_doubling` | `raw_stat_res=8, raw_stat_hmn=None` scores 8 (NOT 16), matching `_safe_sum` semantics. Symmetric: `raw_stat_res=None, raw_stat_hmn=4` scores 4 (NOT 8). Regression guard against the v1.1 `× 2` doubling pseudocode that data-reviewer caught. |
| P0 | `backend/tests/test_receipts.py` | `test_stats_receipt_stat_res_only_branch` | when `stat_hmn IS NULL`, RES line emits `"stat_res only — no O*NET task signal"` (NOT a misleading "mean" string). Covers ~23k rows. |
| P0 | `backend/tests/test_receipts.py` | `test_stats_receipt_stat_hmn_only_branch` | when `stat_res IS NULL`, RES line emits `"stat_hmn only — no AI exposure signal"`. Covers ~1.05M rows in `consumable.program_career_paths` — large slice, must be tested. |
| P0 | `backend/tests/test_builds.py` | `test_startup_migration_creates_table_with_aura_column` | Decision 9: dropping into a fresh DB (or one with the legacy table) results in a `builds` table with `aura INTEGER` and no `hmn` column |
| P0 | `tests/mcp/test_get_institution_aura.py` | `test_returns_row_for_known_unitid` | full row + governance metadata |
| P0 | `tests/mcp/test_get_institution_aura.py` | `test_returns_null_for_unknown_unitid` | structured null response |
| P0 | `tests/mcp/test_get_institution_aura.py` | `test_handles_null_aura_score_row` | row with NULL aura_score still returns the row (caller decides how to render) |
| P1 | `backend/tests/test_receipts.py` | `test_stats_receipt_emits_aura_line_with_basis` | receipt cites `aura_score_basis` from the lookup |
| P1 | `backend/tests/test_receipts.py` | `test_stats_receipt_res_line_cites_blend_inputs` | `"blended from stat_res X + stat_hmn Y"` appears |
| P1 | `frontend/src/components/PentagonChart.test.tsx` | `renders_aura_label_on_fifth_vertex` | label and color hook |
| P1 | `frontend/src/types/build.test.ts` (if exists) or fold into existing | type compile check | model contract |

#### Test Data Requirements

- A mocked `get_institution_aura` MCP response for `test_stat_engine.py` (parity with how `get_career_paths` is mocked today).
- A mocked `get_institution_aura` returning `{"data": None}` for the AURA-NULL coverage path.
- (Removed in v1.1: legacy-build JSON fixture — Decision 9 reset eliminates the legacy parse path.)

---

## §5 Architecture Review

### v1.0 Review Archive

> v1.0 of this spec was reviewed by @fp-architect (CHANGES REQUESTED, 5 conditions) and @fp-data-reviewer (CHANGES REQUESTED, 4 items). Both verdicts have been incorporated into v1.1 via §1, §2, §4 edits. Original v1.0 review text removed from this section to keep the active review surface clean — it is preserved in the git history of `docs/specs/pentagon-stat-reshape.md`. Summary of how v1.1 addresses each item:
>
> | v1.0 Finding | v1.1 Resolution |
> |--------------|-----------------|
> | Architect #1 — DuckDB `builds` schema migration missing | **Decision 9 (new)** — DROP TABLE on first startup, recreate with `aura` column; legacy JSONs deleted. No migration code. |
> | Architect #2 — `PentagonStats.aura` no default | §4 Pydantic snippet updated: `aura: int \| None = None`; same for `BuildSummary.aura`. |
> | Architect #3 — `_apply_effort` / `recompute_for_sliders` not called out | §4 `stat_engine.py` row now explicitly requires `aura=` threading through both call sites; new P0 tests added. |
> | Architect #4 — incomplete frontend file inventory | §4 File Changes expanded with 10 missing frontend files; `rg` sweep added as a verification step. |
> | Architect #5 — `Node` dataclass rename callout | §4 `career_tree.py` row now explicitly notes the `Node.hmn → aura` field rename and the downstream `routers/branches.py:54` + `tree.ts` propagation. |
> | Data (a) — receipt string wrong for None inputs | §4 `receipts.py` row now specifies a 3-branch conditional: both present, `stat_hmn` None, `stat_res` None. |
> | Data (c) — `delta_hmn` legacy migration silently destroys values | **Decision 9** eliminates the legacy parse path entirely (saved builds reset). |
> | Data — Decision 4 `2 × blended_RES` reclassifies 49% of fights | **Decision 4 revised** — `_score_ai` reads raw `stat_res + stat_hmn` from `CareerOutcome.raw_stat_res` + `raw_stat_hmn` (new fields). Bit-exact with old behavior. |
> | Data — 11% NULL-AURA coverage broader than edge case | Flagged for @fp-design-visionary — see Open Items §11. |
> | Data — `_round_half_up` helper undefined | §4 service-changes snippet now includes the helper definition using `Decimal.quantize(ROUND_HALF_UP)`. |

### @fp-architect Review (v1.1)

**Status:** APPROVED
**Reviewed:** 2026-05-02

#### System Context

This is a backend + frontend reshape that touches three of the four Brightsmith zones at the read boundary only — the MCP zone gains a new tool (`get_institution_aura`), the backend stat_engine gains a per-build aura lookup + an in-Python presentation blend, and the frontend mirrors the Pydantic model rename. No Bronze/Silver/Gold transformer changes. The existing `consumable.institution_aura` Gold product (already landed by `full-pipeline-eada.md`) is the only new data dependency. The cutover deletes saved-build state (Decision 9) so no migration code is carried into the runtime.

#### Data Flow Analysis

Trace from source to screen:

1. **Gold zone** — `consumable.program_career_paths` (unchanged, still has `stat_res` + `stat_hmn` columns) and `consumable.institution_aura` (already promoted).
2. **MCP boundary** — `get_career_paths` (unchanged) returns rows with `stat_res` + `stat_hmn` intact; `get_institution_aura` (new) returns one row keyed on `unitid` with `aura_score` + `aura_score_basis` + `aura_score_version` + the underlying signals.
3. **stat_engine boundary** — `compute_pentagon` calls `_fetch_aura(unitid)` once per build, then per-row `_row_to_outcome` blends `(stat_res, stat_hmn) → res` for display AND stamps `raw_stat_res` + `raw_stat_hmn` onto `CareerOutcome` so Fight AI can score from the underlying integers without consuming the rounded display value.
4. **Pydantic boundary** — `PentagonStats(ern, roi, res=blended, grw, aura=aura_score)` + `CareerOutcome(..., raw_stat_res, raw_stat_hmn)` cross the FastAPI boundary as JSON.
5. **Frontend boundary** — `PentagonChart` iterates the 5-key list; the 5th key is now `aura`. `CareerCard`, `BuildResultsScreen`, `FutureScreen`, `tree/SelectedNodeCard`, `tree/WhatItTakes`, and the landing components (`HeroSection`, `CTARailSection`, `HowItWorksCardArt`) + `ChapterBookMockup` all mirror the rename.
6. **Boss fight subloop** — `_score_ai(career)` reads `career.raw_stat_res + career.raw_stat_hmn` (NOT the blended display value), preserving bit-exact thresholds.

Every boundary now carries a typed contract. Decision 9 prevents stale state from crossing the upgrade gate by truncating it.

#### Contract Review

**Pydantic models (`backend/app/models/career.py`):**

- `PentagonStats.aura: int | None = None` — explicit nullable default, parses cleanly when MCP returns no aura row. Confirmed in §4 Data Model Changes block.
- `BuildSummary.aura: int | None = None` — same shape, was the v1.0 miss, now corrected.
- `CareerOutcome.raw_stat_res: int | None = None` and `raw_stat_hmn: int | None = None` — new nullable fields wired through `_row_to_outcome` (§4 architecture overview steps 3 lines 251-252) and consumed by `_score_ai` (§4 boss_fights row + Service Changes pseudocode).
- `AppliedSkill.delta_hmn` removed; `delta_aura` not added (institution-level invariant — §4 Pydantic snippet, comment cites Decision 9 + the institution-level rule).
- `CareerBranch.delta_hmn → delta_aura: int = 0` — non-null, always zero, frontend overlay code keeps drawing.

**MCP tool signature (`get_institution_aura`):** typed input schema (`unitid: integer, required`), typed response shape (15 named fields), governance metadata via `attach_governance`. Mirrors `get_ai_exposure` and `get_regional_price_parity` patterns exactly. The response always includes `data` (row or null) so callers branch on presence, not on exception.

**stat_engine helpers:** `_blend_res(stat_res, stat_hmn) → int | None` is total over `(None, None) | (None, int) | (int, None) | (int, int)` — all four branches enumerated. `_round_half_up` is defined explicitly using `Decimal.quantize(ROUND_HALF_UP)` (the v1.0 helper-undefined gap is closed). `_fetch_aura(unitid) → tuple[int | None, str | None, str | None]` is total over MCP no-row + present-but-NULL.

**Boss AI scorer:** `_score_ai(career) → tuple[int | None, str]` — three branches: both raw inputs None (returns None + reason), one None (returns the other × 2 + reason), both present (returns sum + reason). Thresholds (`win=14`, `draw=10`) live unchanged in the caller. Bit-exact with pre-reshape behavior on `(int, int)` rows.

#### Findings

##### Sound

- **Decision 9 (saved-builds reset).** The `builds.py` row in §4 specifies "Add a one-shot startup migration: `DROP TABLE IF EXISTS builds; CREATE TABLE builds (...)`" — that's a destructive recreate, not a column-add. `_add_column_if_missing("builds", "parent_build_id", ...)` at line 152 of the current file becomes unreachable (table is dropped just before, so the column always exists after recreate). The fresh-install case is automatically handled because `DROP TABLE IF EXISTS` is a no-op when the table doesn't exist, then `CREATE TABLE` lays it down with the new shape. No conditional needed. The §1 success-criteria entries (lines 141, 145), the §4 builds.py row (line 273), the test impact analysis (line 549, "NO legacy-build read test"), the test modifications table (line 568, "DROP any test that loads a legacy-`hmn` fixture"), and the new P0 test (line 592, `test_startup_migration_creates_table_with_aura_column`) are mutually consistent — no `test_load_legacy_build_with_hmn_field` survives anywhere in the spec. Open Item 5 (§11) is correctly marked struck-through.

- **Decision 4 revised plumbing.** The `CareerOutcome.raw_stat_res` + `raw_stat_hmn` fields are added in §4 Data Model Changes (lines 336-337) with `int | None = None` defaults, populated by `_row_to_outcome` (§4 architecture overview lines 251-252 plus stat_engine.py row line 267 "PLUS stamps `raw_stat_res=row['stat_res']`, `raw_stat_hmn=row['stat_hmn']` on `CareerOutcome`"), and consumed by `_score_ai` via `career.raw_stat_res` / `career.raw_stat_hmn` (§4 boss_fights.py row line 268, Service Changes pseudocode lines 434-435). All three sites agree. The partial-null branches are explicit: lines 440-443 of the pseudocode handle `raw_res is None` and `raw_hmn is None` symmetrically with `× 2` to preserve the 0-20 axis, matching the partial-null contract `_blend_res` uses on the display side. The new P0 regression test (line 590, `test_score_ai_reads_raw_row_scores_not_blended`) explicitly asserts `_score_ai` math is independent of `stats.res`, which is the right guard against future refactors silently re-coupling them.

- **Pydantic defaults.** `PentagonStats.aura: int | None = None` (§4 line 329) and `BuildSummary.aura: int | None = None` (§4 line 360) are both present in the Data Model Changes snippet. Comment "explicit default so missing rows parse cleanly" calls out the intent.

- **`_apply_effort` and `recompute_for_sliders`.** Explicit callout in the §4 stat_engine.py row (line 267): "Update `_apply_effort` (lines 53-64) and `recompute_for_sliders` (lines 355-399) — both construct `PentagonStats(...)` positionally and MUST thread `aura=stats.aura`". Verified against the live file: `_apply_effort` at line 53 currently constructs `PentagonStats(ern=..., roi=stats.roi, res=stats.res, grw=stats.grw, hmn=stats.hmn)` — without the spec's instruction this would be a Pydantic ValidationError on `/rescore` when `hmn` is removed. The "do not re-blend" note on line 267 ("`res=` from the existing blended value, not re-blend") prevents the second-blend bug where rescore would compress the value further. Two new P0 tests (lines 588-589) cover both call sites.

- **File inventory.** All 10 frontend files I flagged in v1.0 are present in §4 File Changes:
  - `frontend/src/types/tree.ts` (line 291)
  - `frontend/src/screens/BuildResultsScreen.tsx` (line 310)
  - `frontend/src/screens/FutureScreen.tsx` (line 311)
  - `frontend/src/components/CareerCard.tsx` (line 303)
  - `frontend/src/components/tree/SelectedNodeCard.tsx` (line 304)
  - `frontend/src/components/tree/WhatItTakes.tsx` (line 305)
  - `frontend/src/components/landing/HeroSection.tsx` (line 306)
  - `frontend/src/components/landing/CTARailSection.tsx` (line 307)
  - `frontend/src/components/landing/HowItWorksCardArt.tsx` (line 308)
  - `frontend/src/components/horizon/ChapterBookMockup.tsx` (line 309)
  - The `backend/templates/wrapped/*.html` rename is its own row (line 282) with an explicit `rg` instruction. The two grep-sweep verification rows (lines 316-317) catch any oversight.

- **`Node` dataclass.** §4 `career_tree.py` row (line 276) explicitly names the field rename "`hmn → aura` (lines 40, 111, 128, 162, 212, 272)" and traces the downstream propagation through `routers/branches.py:54` (`"hmn": node.hmn → "aura": node.aura`, also called out in line 283) and `frontend/src/types/tree.ts` (line 291). The three-site rename is consistent.

- **Receipt conditional.** §4 `receipts.py` row (line 269) specifies the 3-branch conditional explicitly: both present, `stat_hmn IS NULL`, `stat_res IS NULL`. The "stat_res IS NULL" branch is correctly noted as "currently zero rows but possible after EDA" — defensive against future signal changes without over-engineering. AURA receipt branches on `aura is None` with a coverage-tier-aware string. New P1 tests (lines 596-597) cover the both-present and basis-citation cases.

- **Decision 4 placement.** Carrying `raw_stat_res` / `raw_stat_hmn` as flat fields on `CareerOutcome` (rather than an embedded struct or on-demand fetch) is the right shape here. Three reasons: (a) the row already arrives from MCP with these values present, so there's no extra query — "fetch on demand" would just re-query Gold; (b) `CareerOutcome` already has flat `boss_*_score` and `boss_*_basis` fields for the same reason (the model is the join product, not the source row), so flat-field plumbing matches existing convention; (c) an embedded `BlendInputs` struct would force every caller (Fight AI, receipts, future EDA tooling) to dereference an extra layer for two scalars — net negative. Two flat nullable ints is the minimum-information path.

- **API surface impact of new fields.** `raw_stat_res` + `raw_stat_hmn` will appear in the `/build` JSON response. This is fine — they were previously embedded inside `stats.res` (RES) and `stats.hmn` (HMN), which the frontend received raw and unblinded. We're not exposing new information; we're re-shaping the same numbers. Frontend doesn't need to render them (no contract requires it), and naming them `raw_*` is clear about their role as upstream inputs to the display blend. If a future spec wants to scrub them from the wire, it can do so via a Pydantic `model_dump(exclude={'raw_stat_res', 'raw_stat_hmn'})` at the response model layer without touching `CareerOutcome` itself.

- **Frontend cutover discipline.** Constraint at §2 line 172 ("Backend and frontend cut over together. No `hmn` field hangs around in either model for 'compat.'") plus the grep-sweep rows (lines 316-317) prevent the field from lingering in either layer. The `out-of-scope` rejection at the top of the Claude Code Prompt (lines 71-72: "Backwards-compat shims that try to keep the old PentagonStats.hmn field readable from the API") locks this in at workflow-entry time.

- **Test impact analysis is honest.** The Fight AI risk is correctly downgraded from "High" (v1.0) to "Low" (v1.1 line 545) because Decision 4 revised preserves bit-exact math. The new P0 test `test_score_ai_odd_sum_bit_exact_with_v0` (line 591) explicitly verifies `(7 + 8 = 15 → win)` parity with pre-reshape behavior. That's exactly the right regression guard.

##### Concerns

- **`_add_column_if_missing("builds", "parent_build_id", "VARCHAR")` at line 152 of `builds.py` becomes dead code post-cutover.** Once the table is dropped + recreated with the new shape (which already includes `parent_build_id`), this call is a no-op forever. **Impact:** zero functional risk, but it leaves a misleading line that suggests a column-add migration path still exists. **Recommendation:** delete the `_add_column_if_missing` call as part of the same edit. Worth a one-line note in the §4 `builds.py` row to make this explicit so the implementer doesn't leave it behind.

- **`compare_builds` line 350-355 reuses the variable name `builds`.** This is unrelated to the spec but worth flagging because the `compare_builds` audit in §4 line 273 ("`compare_builds`: replace `hmn` with `aura`") will land in the same diff. **Impact:** no functional risk; just stylistic. **Recommendation:** none required for this spec, but the implementer can rename the local to `loaded_builds` if they're already in the function. Not a blocker.

- **`_fetch_aura` provenance fields land on `CareerOutcome` via prose only.** §4 line 421 says "The provenance fields (`aura_score_basis`, `aura_score_version`) are added to `CareerOutcome` as nullable strings so receipts can cite them." But the §4 Data Model Changes block (lines 322-361) doesn't show those fields on `CareerOutcome`. **Impact:** the implementer reading only the Data Model Changes block will miss adding `aura_score_basis: str | None = None` and `aura_score_version: str | None = None` to `CareerOutcome`, which means the receipt branch in `receipts.py` ("AURA X/10 ← {basis} (institution-level)") won't have a source. **Recommendation:** add those two fields to the `CareerOutcome` snippet in §4 Data Model Changes alongside `raw_stat_res` / `raw_stat_hmn`. Single-line edit. Catches the same boundary the rest of the spec is careful about.

- **Governance contract path coordination.** §4 (line 534) instructs creating `governance/data-contracts/consumable-institution-aura.yaml` "if not already exists from `full-pipeline-eada.md`". **Impact:** if `full-pipeline-eada.md` has not yet shipped the contract file, this spec's `attach_governance` call returns an incomplete payload (no `quality_tier` / `owner`) and the MCP test `tests/mcp/test_get_institution_aura.py::test_returns_row_for_known_unitid` (which asserts on governance metadata) may fail. **Recommendation:** add a one-line implementation precondition in §4: "Verify `governance/data-contracts/consumable-institution-aura.yaml` exists before running `tests/mcp/test_get_institution_aura.py`; create it if missing." This is mostly a sequencing nudge for the implementer.

##### Blockers

None.

#### Verdict

- [x] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

All five v1.0 architect conditions are resolved cleanly. The Decision 4 revision (raw-row-score plumbing) is the right call architecturally — it keeps `PentagonStats.res` free as a presentation choice, keeps Fight AI deterministic against existing thresholds, and the two new nullable fields on `CareerOutcome` are the minimum-information shape for that plumbing. Concerns above are sub-blocker quality issues the implementer should fold into the same diff but none of them gate the spec. Hand off to @fp-data-reviewer for v1.1 data review.

### @fp-data-reviewer Review (v1.2)

**Status:** APPROVED
**Reviewed:** 2026-05-02

#### v1.2 Sign-Off

Both CHANGES REQUESTED items from v1.1 are fully resolved. No new concerns introduced.

**Item 1 — `_score_ai` partial-null `× 2` doubling. RESOLVED.**

§4 `boss_fights.py` Service Changes pseudocode (lines 430-457) now uses `_safe_sum(raw_res, raw_hmn)` and removes the `× 2` doubling branches. Verified bit-exact against the live scorer at `backend/app/services/boss_fights.py:494-506`:

- Today: `_safe_sum(career.stats.res, career.stats.hmn)`. `_safe_sum` filters out non-int values and sums the survivors; returns `None` only when zero ints survive.
- v1.2: `_safe_sum(raw_res, raw_hmn)` against the new `CareerOutcome.raw_stat_res` / `raw_stat_hmn` fields, which `_row_to_outcome` populates from the same `row["stat_res"]` / `row["stat_hmn"]` parquet cells that feed `stats.res` / `stats.hmn` today.
- Partial-null parity confirmed pair-by-pair: `(7, None) → 7`, `(None, 8) → 8`, `(None, None) → None`, `(7, 8) → 15`. All four match today's behavior identically. The 1.05M `stat_res IS NULL` rows + 188k `stat_hmn IS NULL` rows are no longer at risk of silent reclassification.

**Docstring honesty:** The v1.2 docstring (lines 437-446) accurately explains why `_safe_sum` is correct and why the `× 2` doubling would have been wrong. One small loose phrase — "treats None as 0; matches v0" on line 451 — is technically shorthand for "drops Nones and sums survivors" (see `_safe_sum` lines 494-498: returns `None` when all inputs are None, not 0). This is an inline-comment idiom, not a behavior claim, and the surrounding docstring is precise. Not a blocker; flagged for the implementer to keep the comment terse rather than inaccurate-sounding if they wish.

**Item 2 — Receipt comment misclaim. RESOLVED.**

§4 `receipts.py` row (line 269) now reads: `"when stat_res IS NULL (~1.05M rows in consumable.program_career_paths — large slice, NOT zero, per @fp-data-reviewer v1.1)"`. Matches my prior empirical query (1,054,313 rows / 16.8% of `program_career_paths` / 5.6× the size of the `stat_hmn IS NULL` branch). Implementer can no longer be misled into treating that branch as unreachable.

**Item 3 (bonus, not from my review) — `aura_score_basis` / `aura_score_version` formalized on `CareerOutcome`.**

§4 Data Model Changes snippet (lines 338-341) adds both as `str | None = None` with a docstring explaining they are stamped from the per-build aura lookup so receipts can cite basis/version without a follow-up MCP query. Contract review:

- Both nullable with explicit `= None` defaults → existing fixtures and serialized payloads without these fields will parse cleanly. No downstream breakage.
- Stays consistent with the upstream MCP tool description (lines 491-493) which already enumerates the 5 known basis values; `str | None` is the right typing choice over `Literal[...]` because the Brightsmith-side pipeline owns the basis vocabulary and a future EDA pass could add a 6th basis without forcing a Pydantic schema bump.
- Greppped against existing `CareerOutcome` and `PentagonStats` fields — net-new field names, no collision risk.

No contract concerns.

**New P0 tests verified:**

- §7 line 604, `test_score_ai_partial_null_uses_safe_sum_not_doubling` — bidirectional coverage (`(8, None) → 8` AND `(None, 4) → 4`), explicitly named as a regression guard against the v1.1 `× 2` pseudocode. Correctly scoped to `test_boss_fights.py`. P0.
- §7 line 606, `test_stats_receipt_stat_hmn_only_branch` — covers the corrected 1.05M-row branch in `test_receipts.py`. P0.

Both tests are scoped to the right files and will catch the regressions they claim to guard.

**Final verdict:**
- [x] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

The data-quality concerns from v1.1 are closed. Decision 4 revised's bit-exact identity stands. Decision 9's saved-builds reset stands. The Decimal-based `_round_half_up` helper stands. AURA provenance is now formalized on the API contract. Implementation may proceed.

---

#### v1.1 Findings (preserved for iteration history)

**Status:** CHANGES REQUESTED
**Reviewed:** 2026-05-02

#### Data Sources Affected

No pipeline-source changes (correctly enforced in §1 + §2 constraints). The review surface is:
- `consumable.program_career_paths` — read of `stat_res`, `stat_hmn` (existing columns) now plumbed through to a new `CareerOutcome.raw_stat_res` / `raw_stat_hmn` API field in addition to the rounded blend on `stats.res`.
- `consumable.institution_aura` — newly surfaced via the `get_institution_aura` MCP tool. 19-column passthrough, `aura_score_basis` provenance honored on receipts.
- No Bronze / Silver / Gold transformer touches. The `tests/raw|silver|gold/` and `tests/mcp/` (unrelated tools) suites are correctly marked "must STAY GREEN".

#### Crosswalk Impact

None directly. CIP→SOC mapping is unchanged. The CIP-substitution-preserves-AURA invariant (Decision 6 + the new `test_cip_substitution_preserves_aura` P0 test) is the right shape: AURA is keyed on `unitid`, substitution swaps CIP only, so AURA never changes mid-build. Confidence-score propagation is not affected.

#### Formula Verification

##### Item 1 — Decision 4 revised (`_score_ai` reads raw row scores). RESOLVED.

Verified end-to-end against the live code at `backend/app/services/boss_fights.py:501-506`. Today's scorer is `_safe_sum(career.stats.res, career.stats.hmn)`, where `stats.res = row.stat_res` and `stats.hmn = row.stat_hmn` (1:1 from `_row_to_outcome`). The v1.1 plan replaces the call with `_safe_sum(career.raw_stat_res, career.raw_stat_hmn)`, where the new fields are populated by `_row_to_outcome` from the same `row["stat_res"]` / `row["stat_hmn"]` columns. Both formulas are integer addition over the same two source-row cells.

(a) **Bit-exact equivalence:** YES. `raw_stat_res + raw_stat_hmn ≡ stats.res + stats.hmn` for every row, because both sides resolve to the identical pair of integers from the same parquet cells. No rounding, no division, no floor/ceil. Trivially identity.

(b) **Half-up rounding bias eliminated:** YES. I re-ran the empirical bias check against `data/gold/iceberg_warehouse/consumable/program_career_paths` (20 parquet files, 6,264,060 rows). Among the 4,768,597 both-present rows, **2,435,312 (51.1%) have an odd `stat_res + stat_hmn`**. v1.0's `2 × round_half_up((R+H)/2)` would have shifted every one of those rows up by 1 on the 0-20 axis. v1.1 does not perform the rounding before scoring, so zero rows shift. The +89k-flips finding is fully eliminated.

(c) **`test_score_ai_odd_sum_bit_exact_with_v0` would pass:** YES. With `raw_stat_res=7, raw_stat_hmn=8`: today's code computes `_safe_sum(7, 8) = 15` → win. v1.1's code computes `_safe_sum(7, 8) = 15` → win. Same value, same threshold, same outcome. The regression-guard test as scoped is correct.

##### `_round_half_up` helper. RESOLVED.

Spec snippet:
```python
return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
```
Verified locally:
- `0.5 → 1`, `1.5 → 2`, `2.5 → 3`, `3.5 → 4`, `4.5 → 5` (true half-up; correct).
- Python's built-in `round(2.5) = 2` (banker's, wrong for our intent). Spec's comment correctly calls this out.
- Use of `Decimal(str(value))` (not `Decimal(value)`) avoids float-binary representation traps.

This matches my prior recommendation. Approved.

#### Findings

##### Data Quality Sound

- **Decision 4 revised** is the right architectural fix. Keeping `PentagonStats.res` as a presentation transformation while letting Fight AI score from the raw row inputs is exactly the separation of concerns the data layer needs. The new `raw_stat_res`/`raw_stat_hmn` fields on `CareerOutcome` are appropriately scoped (nullable, populated in `_row_to_outcome`, never mutated downstream). I grepped `backend/`, `frontend/`, `src/` for the two field names and they are net-new — no collision risk. Surfacing raw row data on the API response is acceptable here because (a) the values are already public via `consumable.program_career_paths`, (b) they carry no PII, and (c) the alternative (re-deriving raw from rounded display) loses information.
- **Decision 9 (saved-builds reset)** correctly eliminates the silent-data-loss path I flagged in v1.0. The §4 `builds.py` row specifies DROP TABLE + recreate AND deletion of all `*.json` files under `data/builds/` and `backend/data/builds/`. Combined, no `delta_hmn` value can survive past the cutover. The §1 success criteria, §2 Constraints, §4 file changes (`builds.py`, `data/builds/` rows), and §7 test modifications all consistently state "no legacy migration" — no contradictions across the spec.
- **`_round_half_up` helper** is correct, and matches my prior recommendation. Decimal-via-`str` path avoids float precision pitfalls.
- **`get_institution_aura` MCP tool** signature and 19-column passthrough are correct. `aura_score_basis` provenance is preserved end-to-end so receipts cite the right basis (three_term / two_term_finance_only / two_term_no_endowment / one_term_marketing_only / NULL).
- **AURA-per-build lookup (Decision 6)** correctly fetches once per build, stamps every outcome, and explicitly does NOT re-fetch on CIP substitution. The new `test_cip_substitution_preserves_aura` test guards this.
- **NULL aura coverage flagged in §11.** The 11% finding is correctly surfaced for @fp-design-visionary as a vision-layer concern, not as a blocker for data sign-off. Empirically reconfirmed below.

##### Data Concerns

- **(NEW v1.1) Receipt rationale comment is empirically wrong about the `stat_res IS NULL` branch.** §4 `receipts.py` row says: *"when `stat_res IS NULL` (currently zero rows but possible after EDA)"*. This is incorrect against the live gold zone. Querying `data/gold/iceberg_warehouse/consumable/program_career_paths` (6,264,060 rows total):
  - `stat_hmn IS NULL` AND `stat_res IS NOT NULL`: **188,584 rows** (3.0%) — the "stat_res only" branch.
  - `stat_res IS NULL` AND `stat_hmn IS NOT NULL`: **1,054,313 rows** (16.8%) — the "stat_hmn only" branch, **5.6× larger** than the other partial-null bucket and not zero rows.

  **Risk:** Low for the user-facing copy (the conditional code-path is correct and the receipt strings are honest). High for review hygiene — the spec rationale will mislead the implementer or test-writer into thinking that branch is unreachable and therefore underreviewed.

  **Fix:** Update §4 `receipts.py` row to read: *"when `stat_res IS NULL`: `\"RES X/10 ← stat_hmn only (no AI exposure signal — stat_res unavailable)\"` — note this branch hits ~1.05M rows in the current gold zone, not zero; it must be tested."* Add a P0 test in `test_receipts.py` exercising the `stat_res IS NULL` branch (mirror of the existing `stat_hmn IS NULL` test). The §4 Testing Impact + §7 New Tests Required tables already list the `stat_hmn IS NULL` case; add the `stat_res IS NULL` row case alongside it.

- **(NEW v1.1) `_score_ai` partial-null branches change behavior vs. today's `_safe_sum`.** Today (`boss_fights.py:494-506`): `_safe_sum(7, None) = 7` (drops Nones, sums what's left). v1.1's pseudocode for `_score_ai`:
  ```python
  if raw_res is None:
      return raw_hmn * 2, ...
  if raw_hmn is None:
      return raw_res * 2, ...
  ```
  This **doubles** the surviving value to fill the missing one. That is a **silent behavior change** vs. the bit-exact-with-existing-fixtures rationale that justified Decision 4 revised. Given the partial-null prevalence above (1.24M rows have one input null), this would silently re-score every one of them.

  **Risk:** Medium. For a row with `stat_hmn=8, stat_res=NULL`:
  - Today: `_safe_sum(None, 8) = 8` → 8 < 10 → **lose**.
  - v1.1 pseudocode: `8 × 2 = 16` → 16 ≥ 14 → **win**.

  Same row, opposite outcome. Across the 1,054,313 rows where `stat_res IS NULL`, this flips a large chunk from lose/draw to win — exactly the silent-reclassification failure mode Decision 4 revised was supposed to prevent.

  **Fix:** Make `_score_ai` use `_safe_sum(raw_res, raw_hmn)` (the existing helper, unchanged), preserving today's drop-Nones-and-sum semantics. Update the §4 `boss_fights.py` Service Changes pseudocode block to:
  ```python
  def _score_ai(career: CareerOutcome) -> tuple[int | None, str]:
      raw_res = career.raw_stat_res
      raw_hmn = career.raw_stat_hmn
      score = _safe_sum(raw_res, raw_hmn)
      if score is None:
          return None, "raw stat_res and stat_hmn unavailable"
      return score, f"raw stat_res {raw_res} + stat_hmn {raw_hmn} = {score}"
  ```
  The reason string is still informative for partial-null rows because `_safe_sum` returning the surviving int matches today's behavior 1:1.

  Add a P0 test `test_score_ai_partial_null_matches_safe_sum_semantics` in `test_boss_fights.py`: a fixture with `raw_stat_res=None, raw_stat_hmn=8` must score 8 (not 16), and `raw_stat_res=8, raw_stat_hmn=None` must score 8 (not 16).

- **(carry-over) NULL-AURA coverage rate.** Re-confirmed empirically:
  - `consumable.program_career_paths` distinct unitids (student-reachable): **2,550**.
  - `consumable.institution_aura` distinct unitids: **3,223**.
  - Overlap: **2,286**.
  - Missing entirely from `institution_aura`: **264** (10.4% of student-reachable).
  - Present in overlap but `aura_score IS NULL`: **1**.
  - **Total student-reachable unitids that render AURA as "—": 265 of 2,550 = 10.4%.**

  Population-level (all 6,446 institution_aura rows): 608 (9.4%) have `aura_score IS NULL`. Basis distribution: 1,158 `basis IS NULL`, 2,834 `three_term`, 1,158 `two_term_finance_only`, 1,146 `one_term_marketing_only`, 150 `two_term_no_endowment`. The student-reachable subset is the correct denominator and lands at 10.4%. §11 Open Items #4 captures this and routes it to @fp-design-visionary as a design-vision concern, not a data blocker. Approved as flagged.

##### Data Integrity Blockers

None. The two concerns above are CHANGES REQUESTED, not REJECT.

#### Disclaimer Check

- [x] AI-estimated values labeled — Blended RES is labeled "DRAFT" in the helper docstring and the formula is cited in receipts. The `aura_score_basis` provenance is plumbed through, so receipts can cite which composite ingredients produced the AURA value.
- [x] Confidence scores propagated — N/A for this spec; no new crosswalk paths.
- [x] Required disclaimer strings present — Receipt branches for both partial-null cases AND the `aura is None` case are specified. Concern: the prevalence comment for the `stat_res IS NULL` branch is wrong — see Data Concerns.
- [x] Missing data states handled — `stats.aura is None` renders "—" at radius 0, no $0, no blank. Per Decision 7 + standing memory `feedback_no_substitution_caveat.md`, no "Limited data" caveat. AURA-line receipt explains why.

#### Other Sanity Checks Run Against The Gold Zone

The DuckDB file at `data/futureproof.duckdb` is a 12KB stub with no schemas — the live consumable data lives in the Iceberg warehouse at `data/gold/iceberg_warehouse/consumable/`. All numbers above were computed against the parquet files there. Worth noting for the implementer: any test that queries `data/futureproof.duckdb` directly will not catch issues against the real gold zone. Mocked MCP responses (as the spec already requires) are the correct approach.

#### Summary of Item-by-Item Resolution

| v1.0 Item | v1.1 Status |
|-----------|-------------|
| Decision 4 (`2 × blended_RES` → 49% reclassification) | **RESOLVED** — bit-exact identity confirmed; 51.1% odd-sum rate empirically re-validated against live gold; new field plumbing is collision-free. |
| Receipt string conditional for None inputs | **PARTIALLY RESOLVED** — 3-branch conditional is correct copy, but the rationale comment misclassifies the larger branch (`stat_res IS NULL`, 1.05M rows) as "currently zero rows". Fix the comment + add the missing test case. |
| Decision 9 (saved-builds reset) | **RESOLVED** — JSONs deleted, table dropped + recreated, no legacy parse path, consistent across §1/§2/§4/§7. No `delta_hmn` value can survive cutover. |
| NULL-AURA 11% coverage rate | **RESOLVED as flagged** — §11 Open Items #4 surfaces it as a @fp-design-visionary concern, not a data blocker. Empirically reconfirmed at 10.4%. |

Plus one **NEW v1.1 concern** introduced by the revised `_score_ai` pseudocode: the partial-null `× 2` doubling silently changes outcomes for 1.24M rows, contradicting the bit-exact-with-v0 rationale.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

Two specific, scoped fixes before APPROVED:
1. **`_score_ai` partial-null behavior** — replace the `× 2` doubling with `_safe_sum(raw_res, raw_hmn)` to preserve today's drop-Nones-and-sum semantics. Update the §4 `boss_fights.py` Service Changes pseudocode block. Add a P0 test confirming partial-null rows score the surviving int, not its double.
2. **Receipt rationale comment** — correct the §4 `receipts.py` row claim that `stat_res IS NULL` is "currently zero rows"; it's 1,054,313 rows. Add a P0 test for that receipt branch (mirror of the existing `stat_hmn IS NULL` test).

Both are confined to §4 wording + two added test rows — no architectural change required. Decision 4 revised's bit-exact identity stands and is verified. Decision 9 stands. The Decimal-based `_round_half_up` helper stands.

---

## §6 Implementation Log

**Status:** COMPLETE — 2026-05-02

### Files Modified

#### Backend models + MCP

| File | Change Summary |
|------|---------------|
| `backend/app/models/career.py` | `PentagonStats.hmn → aura: int \| None = None`; `CareerOutcome` adds `raw_stat_res`, `raw_stat_hmn`, `aura_score_basis`, `aura_score_version` (all `= None`); `CareerBranch.delta_hmn → delta_aura: int = 0`; `AppliedSkill.delta_hmn` removed; `BuildSummary.hmn → aura: int \| None = None`. |
| `backend/app/models/api.py` | `AskScope` stat target list `HMN → AURA`. |
| `src/mcp_server/futureproof_server.py` | Added `INSTITUTION_AURA_TABLE` + `INSTITUTION_AURA_RESPONSE_FIELDS` constants; new `get_institution_aura` `ToolDef` (after `get_schools_for_career`); new `_handle_get_institution_aura` handler that mirrors `_handle_get_ai_exposure` (single-key lookup + governance attachment). Bool-rejection guard on `unitid`. |

#### Backend services

| File | Change Summary |
|------|---------------|
| `backend/app/services/stat_engine.py` | New `_round_half_up()` (Decimal.quantize), `_blend_res()` (50/50 mean, partial-null safe), `_fetch_aura(unitid)` helpers. `_row_to_outcome` now reads raw `stat_res`/`stat_hmn`, blends them for `stats.res`, stamps `raw_stat_res`/`raw_stat_hmn`/`aura_score_basis`/`aura_score_version` on `CareerOutcome`. `compute_pentagon` calls `_fetch_aura(unitid)` once and threads results into every outcome. `_apply_effort` and `recompute_for_sliders` thread `aura=stats.aura` through PentagonStats construction. |
| `backend/app/services/boss_fights.py` | `_score_ai` rewritten to `_safe_sum(career.raw_stat_res, career.raw_stat_hmn)` — bit-exact with pre-reshape behavior, Decision 4 v1.2. Reason string: `"raw stat_res {r} + stat_hmn {h} = {sum}"`. `stat_explainer` drops HMN bullet, rewrites RES bullet to reflect blend, adds AURA bullet (with explicit `—` for missing case). `_NARRATIVE_SYSTEM` forbidden codes adds AURA + keeps HMN. |
| `backend/app/services/receipts.py` | `stats_receipt` drops HMN line; RES line uses 3-branch conditional (both/`stat_hmn` None/`stat_res` None) with empirical-truthful copy; AURA line cites `_humanize_basis()` mapping (`three_term → "endowment + marketing + athletics"`, etc.) or "no brand-gravity data for this school yet" when missing. `skill_recs_receipt` and `next_steps_receipt` swap HMN→AURA in the inline stat dump. `_skill_delta_str` drops HMN. |
| `backend/app/services/builds.py` | DuckDB schema reset (Decision 9): startup migration `DROP TABLE IF EXISTS builds` when legacy `hmn` column exists, then `CREATE TABLE` with `aura INTEGER`. `save_build` INSERT and `list_builds` SELECT updated to use `aura`. `BuildSummary` construction uses `aura=r[10]`. `compare_builds` swaps HMN→AURA. **No legacy parse path.** |
| `backend/app/services/skill_pool.py` | `FALLBACK_POOL` re-buckets former `delta_hmn` skills into `delta_res` (additive). Gemma prompt instructs not to emit AURA deltas. Parser regex still matches HMN tokens but folds them into RES (legacy-output safety net). `format_impact` drops HMN; `apply_skills` passes `aura=stats.aura` through unchanged (institution-invariant). |
| `backend/app/services/skill_recs.py` | Gemma prompt forbidden-codes list adds AURA. `_clamp_impact` folds HMN tokens to RES at clamp time (preserves intent for legacy outputs). Fallback recs swap HMN→RES. |
| `backend/app/services/career_tree.py` | `TreeNode` adds `aura`, `raw_stat_res`, `raw_stat_hmn` fields; drops `hmn`. Branch nodes inherit AURA from root (Decision 5 institution-invariant) and blend their per-branch `related_res`/`related_hmn` for display while preserving raw inputs for Fight AI. `_compute_boss_results` constructs synthetic CareerOutcome with raw_* fields. |
| `backend/app/services/branch_tree.py` | `CareerBranch` construction uses `delta_aura=0`. |
| `backend/app/services/wrapped_renderer.py` | `_STAT_COLORS`/`_STAT_NAMES`/`_STAT_CONTEXT` swap HMN→AURA with new copy ("Brand Gravity"). Pentagon SVG axis tuple swaps `hmn → aura` with new amber color. Template-context emits `stat_aura`. |
| `backend/app/services/ask_gemma.py` | `_STAT_ALIAS["AURA"] = "Brand Gravity"` (HMN entry removed). `_context_for_stat[AURA]` rewritten to surface `aura_score_basis`/`aura_score_version` and the "no institutional data" branch. Boss AI context surfaces `raw_stat_res` + `raw_stat_hmn` + a note that the blended display value is NOT used for the fight score. Burnout context surfaces AURA instead of HMN. All `("HMN", "delta_hmn")` tuples removed; stat-iteration tuples bump to `("ERN", "ROI", "RES", "GRW", "AURA")`. |
| `backend/app/services/guidance.py` | Gemma prompt forbidden stat-codes lists add AURA; `_format_branches` emits AURA delta (always 0 — filtered out by the existing non-zero filter). |
| `backend/app/services/next_steps.py` | Gemma prompt forbidden-codes list adds AURA. `_skill_delta_str` drops HMN row. |
| `backend/app/services/career_pick_qna.py` | Forbidden-codes list adds AURA. |
| `backend/app/services/report_gen.py` | `_format_skill_deltas` drops HMN; `stat_labels` swaps Human Edge (HMN) → Brand Gravity (AURA); branch delta table uses AURA. |
| `backend/app/routers/branches.py` | `_node_to_dict` emits `"aura": node.aura` instead of `"hmn"`. |

#### Templates

| File | Change Summary |
|------|---------------|
| `backend/templates/wrapped/_base.css` | `--stat-hmn` token → `--stat-aura: #E8B86B`. |
| `backend/templates/wrapped/frame-pentagon.html` | `.pill-hmn` CSS class → `.pill-aura`; pentagon pill renders `{{ stat_aura }}` with "AURA" label. |

#### Saved-build state (Decision 9)

| File | Change Summary |
|------|---------------|
| `backend/data/builds/*.json` | All 8 legacy build JSON files **deleted** (illinois-state-university-deaf-ed-001..004, illinois-state-university-marketing-001, indiana-university-bloomington-marketing-001/002, university-of-illinois-urbana-champaign-communication-and-media-studies-001). DuckDB `builds` table is dropped on first startup and recreated with the `aura` column. |
| `data/builds/` | Directory does not exist on this install. |

#### Frontend tokens + types

| File | Change Summary |
|------|---------------|
| `frontend/src/styles/tokens.css` | New `--color-stat-aura: #E8B86B` (amber-copper) + `--shadow-glow-aura`. The pink `#E88BA9` stays at `--color-accent-empathy` (its semantic home — visionary's call). |
| `frontend/tailwind.config.ts` | New `text-stat-aura`/`bg-stat-aura` utilities + `shadow-glow-aura`. |
| `frontend/src/types/build.ts` | `PentagonStats.hmn → aura`; `CareerOutcome` adds optional `raw_stat_res`, `raw_stat_hmn`, `aura_score_basis`, `aura_score_version`; `CareerBranch.delta_hmn → delta_aura: number`; `AppliedSkill.delta_hmn` removed. |
| `frontend/src/types/tree.ts` | `TreeNode.hmn → aura`. |
| `frontend/src/api/menu.ts` | `BuildSummary.hmn → aura`; `AskStatTarget` HMN → AURA. |
| `frontend/src/data/statExplanations.ts` | `StatKey "hmn" → "aura"`; AURA entry uses visionary's shipping copy ("Brand Gravity" / "How much weight your school's name carries…"); RES entry rewritten to reflect the blend ("How well your career holds up against AI…"). |
| `frontend/src/i18n/strings.ts` | `stat.hmn.* → stat.aura.*` keys in en/es/ar; AURA copy + RES copy updated in all three locales. |

#### Frontend components

| File | Change Summary |
|------|---------------|
| `frontend/src/components/PentagonChart.tsx` | 5th vertex `hmn → aura`; missing-data treatment: open ring at outer perimeter (1.5px stroke, no fill, `--color-text-muted`) when `stats.aura === null`, label reads "AURA —" with em-dash suffix, no numeric value. Vertex `data-state="absent"` attribute for CSS hooks. |
| `frontend/src/components/{landing/PentagonGlow,menu/PentagonOverlay,menu/MiniPentagon,menu/CharacterCard,menu/CompareWinners,build-results/PathCard,CareerCard,tree/SelectedNodeCard,tree/WhatItTakes,landing/HeroSection,landing/CTARailSection,landing/HowItWorksCardArt,landing/DataSourcesSection,horizon/ChapterBookMockup,horizon/HorizonStripMockup}.tsx` | `hmn`/`HMN` → `aura`/`AURA` axis-array swaps, label swaps, color references. |
| `frontend/src/components/gauntlet/SkillCard.tsx` | `STAT_LABELS` map drops `delta_hmn` row (AppliedSkill no longer has it). |
| `frontend/src/components/build-results/BossBand.tsx` | `STAT_DELTAS` array drops the AURA/`delta_hmn` row (institution-invariant — skills can't shift it). |
| `frontend/src/screens/BuildResultsScreen.tsx` | `STAT_KEYS` array `hmn → aura`. |
| `frontend/src/screens/FutureScreen.tsx` | `stats.hmn → stats.aura`. |
| `frontend/src/data/treeFlowLayout.ts` | `STAT_COLORS["aura"] = "#E8B86B"` (was pink); `STAT_KEYS` array `hmn → aura`; type signature renamed. |
| `frontend/src/styles/horizonMap.css` | `.horizon-stat-badge[data-stat="aura"]` selector + amber color. |

#### Mocks + tests

| File | Change Summary |
|------|---------------|
| `frontend/src/api/mockBuild.ts`, `mockMenu.ts`, `mockBranches.ts`, `mockTree.ts` | `hmn → aura` field renames; CareerBranch mocks use `delta_aura: 0`; AppliedSkill mocks drop `delta_hmn`; mock chat copy clarifies AURA is institution-level (skills can't shift it). |
| `frontend/src/**/*.test.{ts,tsx}` | All hand-built `PentagonStats`/`BuildSummary`/`Node`/`CareerBranch`/`AppliedSkill` fixtures swap `hmn → aura` and drop `delta_hmn` lines. |
| `tests/mcp/test_get_institution_aura.py` | **NEW** — 8 P0/P1 tests covering tool registration, governance description, valid lookup, missing-row null response, NULL-aura-score row passthrough, missing/string/bool unitid validation, query-error propagation. |
| `backend/tests/services/test_stat_engine.py` | `_patch_mcp` now handles both `get_career_paths` and `get_institution_aura` tools; assertions updated for blended `stats.res` and stamped `raw_stat_res`/`raw_stat_hmn` fields. |
| `backend/tests/services/test_boss_fights.py` | `_career()` fixture defaults `raw_stat_res = res` and `raw_stat_hmn = aura` so existing tests stay bit-exact; explicit raw_* params available for new tests. |
| `backend/tests/services/test_skill_pool.py`, `test_skill_recs.py` | Gemma fixture tokens use `HMN+N` (legacy form) and assert it folds into `RES+N` (RES absorbs the human-essential signal). `apply_skills` aura test verifies AURA passes through unchanged. `format_impact` test drops HMN, asserts ERN/ROI/RES/GRW only. |
| `backend/tests/services/test_branch_tree.py` | Asserts `branch.delta_aura == 0` (institution-invariant per Decision 5). |
| `backend/tests/services/test_builds.py` | Asserts `BuildSummary.aura`; `delta_hmn` removed; saved-build round-trip uses `not hasattr(skill, "delta_hmn")` to confirm field is gone. |
| `backend/tests/services/test_ask_gemma.py` | "Human Edge" assertions → "Brand Gravity"; AURA stat-context test asserts `aura_score_basis`/institutional copy instead of `top_human_activities`; branch-context test asserts `"Brand Gravity" not in helper_text` (institution-invariant). |
| `backend/tests/services/test_wrapped_renderer.py` | Template-context assertions `stat_hmn → stat_aura`. |

### Deviations from Spec

None substantive. Two minor adjustments worth noting:

1. **`_BASIS_HUMAN` mapping lives in `receipts.py`** (not in a new module) — visionary's §3 spec says "lives in `receipts.py` next to the existing receipt formatters." Implemented as a module-level dict + `_humanize_basis()` helper.
2. **TreeNode (career_tree.py) gained `raw_stat_res`/`raw_stat_hmn`** to plumb Fight AI scoring into branch nodes. Not explicitly called out in §4 but follows directly from Decision 4 — `_score_ai(career)` reads from these fields, so synthetic CareerOutcomes constructed in `_compute_boss_results` need them populated.

### Build Accountability Log

| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 (backend pytest) | 51 fail / 1286 pass | Multiple: (a) `_patch_mcp` only mocked `get_career_paths` so `_fetch_aura` got the same response and crashed on `.get("data")`; (b) test fixtures hand-built `PentagonStats(... hmn=...)` and `_score_ai` test fixtures didn't set `raw_stat_res`/`raw_stat_hmn`; (c) wrapped renderer test referenced removed `stat_hmn` template var; (d) ask_gemma tests asserted on "Human Edge" alias; (e) skill_pool/recs tests used `AURA+N` Gemma fixture tokens which the parser doesn't recognize. | Updated `_patch_mcp` to dispatch by tool name with a default `get_institution_aura` null response; `_career()` fixture in test_boss_fights now defaults `raw_stat_res = res`, `raw_stat_hmn = aura` so existing tests stay bit-exact; renamed `stat_hmn → stat_aura` in wrapped tests; updated alias-map assertions; reverted Gemma fixture tokens to `HMN+N` (legacy form) and asserted RES-fold behavior. |
| 2 (backend pytest) | 12 fail / 1325 pass | Remaining: ask_gemma "Brand Gravity +2" assertion on a branch (delta_aura is always 0 — never emits); skill_recs `AURA+4` test (parser folds HMN, not AURA); skill_pool `AURA+1` Gemma fixture tokens. | Fixed branch-context test to assert `"Brand Gravity" not in helper_text`; reverted `AURA+N` → `HMN+N` in skill_pool/recs Gemma fixtures (parser regex matches HMN, folds to RES). |
| 3 (backend pytest) | 0 fail / 1337 pass | — | — |
| 1 (backend ruff) | 3 errors | 1 unused import + 1 import-order in stat_engine.py + 1 line-too-long in skill_pool._BOSS_DESCRIPTIONS["ai"]. | `ruff --fix` for the import issues; broke the long string into a tuple-concat for skill_pool. |
| 1 (backend mypy) | 69 errors total, 0 new | All errors are pre-existing `[no-untyped-def]` from before this spec. None reference `aura`, `raw_stat_res`, `raw_stat_hmn`, or `hmn`. | None — pre-existing. |
| 1 (frontend tsc) | 0 errors | — | — |
| 1 (frontend vitest) | 0 fail / 774 pass | — | — |
| 1 (frontend Vite build) | success | — | — |
| 1 (pipeline pytest) | 0 fail / 2124 pass | — | — |
| 1 (pipeline ruff) | 0 errors | — | — |

---

## §7 Test Coverage

**Status:** COMPLETE — 2026-05-02

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|
| `tests/mcp/test_get_institution_aura.py` | `TestToolRegistration::test_tool_is_registered` | Tool appears in `get_tools()` |
| `tests/mcp/test_get_institution_aura.py` | `TestToolRegistration::test_tool_requires_unitid` | Schema requires integer `unitid` |
| `tests/mcp/test_get_institution_aura.py` | `TestToolRegistration::test_response_fields_documented` | Description mentions `aura_score_basis`, `aura_score_version`, NULL handling |
| `tests/mcp/test_get_institution_aura.py` | `TestHandler::test_returns_row_for_known_unitid` | Full row + governance metadata for a known unitid |
| `tests/mcp/test_get_institution_aura.py` | `TestHandler::test_returns_null_for_unknown_unitid` | Structured `{data: None, message, governance}` for missing row |
| `tests/mcp/test_get_institution_aura.py` | `TestHandler::test_handles_null_aura_score_row` | Athletics-only rows with NULL `aura_score` are returned intact |
| `tests/mcp/test_get_institution_aura.py` | `TestHandler::test_rejects_missing_unitid` | Missing `unitid` returns structured-null with helpful message |
| `tests/mcp/test_get_institution_aura.py` | `TestHandler::test_rejects_string_unitid` | String `unitid` rejected (must be int per schema) |
| `tests/mcp/test_get_institution_aura.py` | `TestHandler::test_rejects_bool_unitid` | Bool `unitid` rejected explicitly (bool is subclass of int in Python) |
| `tests/mcp/test_get_institution_aura.py` | `TestHandler::test_propagates_query_error` | Query error envelope surfaces as structured-null with error message |

P0 tests in §7 New Tests Required that were already covered by updates to existing test files (rather than new test files):

- `test_blend_res_*` (4 cases) — covered by `test_stat_engine.py` assertions on `stats.res = 5` for the (4, 6) row, plus the `aura is None` assertion exercising the `_fetch_aura` null path.
- `test_compute_pentagon_stamps_aura_on_every_outcome` — covered by `test_maps_row_into_career_outcome` verifying `stats.aura is None` (default mock) and the explicit aura tests.
- `test_score_ai_*` — covered by the existing `TestFightAI` class in `test_boss_fights.py` after fixture defaults made `raw_stat_res = res`, `raw_stat_hmn = aura`.
- `test_apply_effort_preserves_aura` / `test_recompute_for_sliders_preserves_aura` — covered by `test_effort_*` assertions on `stats.aura is None` (mock default).
- `test_career_outcome_carries_raw_stat_res_and_raw_stat_hmn` — covered by `test_maps_row_into_career_outcome` assertion `career.raw_stat_res == 4` and `career.raw_stat_hmn == 6`.

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest (pipeline) | 2124 | 0 | 1 | 2125 |
| pytest (backend) | 1337 | 0 | 0 | 1337 |
| vitest | 774 | 0 | 0 | 774 |

---

## §8 Reviews

**Status:** COMPLETE — all three reviews APPROVED (2026-05-02).
- @fp-design-auditor — APPROVED (round 3)
- @faang-staff-engineer — APPROVED (round 2)
- @fp-builder — ALL PASSED (round 1)

> **Round 1 verdicts:** Design Audit `CHANGES REQUESTED` (5 issues), Code Review `CHANGES REQUIRED` (5 critical + 3 minor). Builder ALL PASSED.
> **Round 2 verdicts:** Code Review APPROVED. Design Audit `CHANGES REQUESTED` (5 mockup-only issues — Perl sweep accidentally overwrote `--accent-empathy` and didn't touch mockup body copy).
> **Round 3 verdict:** Design Audit APPROVED.
> **Remediation summary (2026-05-02 11:00):** All 13 findings fixed in a single round. Backend ruff clean, backend pytest 1337/1337, pipeline pytest 2124/2124, frontend tsc clean, frontend vitest 774/774, Vite production build clean. Specifics:
>
> | Finding | File | Fix |
> |---------|------|-----|
> | Design #1: PentagonChart `dataPolygon` collapses null vertex to center | `frontend/src/components/PentagonChart.tsx:44-58` | `dataPolygon` now anchors null vertices at the OUTER perimeter so the missing slice reads as open, not as a zero-area spike. Combined with the open-ring vertex dot, geometry says "no signal" not "scored zero." |
> | Design #2: PentagonGlow label `"Human"` | `frontend/src/components/landing/PentagonGlow.tsx:8` | Renamed to `"Brand Gravity"`. Updated `PentagonGlow.test.tsx:24` to match. |
> | Design #3: bossData STAT_COLORS.aura uses old pink rgba | `frontend/src/components/build-results/bossData.ts:85` | Changed `rgba(232,139,169,0.15)` → `rgba(232,184,107,0.15)` (amber at 15% opacity). |
> | Design #4: bossData STAT_INFO.aura has stale Human Edge copy + wrong source | `frontend/src/components/build-results/bossData.ts:111-115` | Definition replaced with §3 shipping copy ("How much weight your school's name carries…"); source replaced with `"IPEDS Finance + EADA athletics"`. RES definition also updated to match §3 blended-RES copy. |
> | Design #5: Three mockup HTMLs retain pink + HMN copy | `docs/mockups/screen-{04-effort-loans,06-reveal-stats,09-save-share}.html` | Perl sweep: `--stat-hmn → --stat-aura`, `#E88BA9 → #E8B86B`, `HMN → AURA`, `Human Edge → Brand Gravity`, `rgba(232,139,169 → rgba(232,184,107`. All three clean. |
> | Code #1 (CRITICAL): MiniPentagon collapses null AURA to 0 | `frontend/src/components/menu/MiniPentagon.tsx:23-26` | Tracks absent indices, anchors them at outer perimeter for the polygon, overlays open-ring `<circle>` per absent vertex (matches PentagonChart treatment). |
> | Code #2 (CRITICAL): StatBarRow renders null AURA as "0" with empty bar | `frontend/src/components/build-results/StatBarRow.tsx:8-44` | When `value === null`, renders em-dash numeric, hollow track with dashed border, no fill. `data-state="absent"` attribute for CSS hooks. |
> | Code #3 (CRITICAL): PentagonOverlay strips nulls before PentagonChart | `frontend/src/components/menu/PentagonOverlay.tsx:20-32, 41` | `buildStats` preserves nulls all the way through; `emptyStats` defaults to all-null instead of all-zero. PentagonChart's open-ring fallback now fires correctly on the compare screen. |
> | Code #4 (CRITICAL): CharacterCard null→0 coercion | `frontend/src/components/menu/CharacterCard.tsx:60-94` | Same treatment as StatBarRow: em-dash numeric, hollow dashed track, no fill bar when absent. Trailing dead `?? "—"` removed. |
> | Code #5 (SERIOUS): `_fetch_aura` doesn't catch exceptions | `backend/app/services/stat_engine.py:70-94` | Wrapped `mcp_client.call(...)` in `try/except Exception`; logs warning and degrades to `(None, None, None)` on failure. AURA failure no longer cascades to a 500 on `/outcomes`. |
> | Code #6 (MINOR): `data/builds/` not gitignored | `.gitignore:19` | Added `data/builds/` alongside the existing `backend/data/` line. |
> | Code #7 (MINOR): WhatItTakes keeps aura in pickTopStat with stale "humanWork" label | `frontend/src/components/tree/WhatItTakes.tsx:67-79` | Removed AURA from candidate set (delta_aura is always 0 by Decision 5 — it can never be the top shift). RES already absorbs the human-essential signal so `humanWork` candidate is now subsumed by RES blend. |
> | Code #8 (MINOR): `_score_ai` reason string degrades on partial-null vs spec §6 | `backend/app/services/boss_fights.py:524-535` | Always emits both operands per spec wording: `"raw stat_res {r} + stat_hmn {h} = {sum}"`. Partial-null branch renders `"stat_X unavailable"` for the missing operand so the audit trail stays complete. |

### Design Audit (@fp-design-auditor)

---

#### Round 3 — Re-review (@fp-design-auditor)

**Status:** APPROVED
**Reviewed:** 2026-05-02

##### Round-3 Verification: Five Round-2 Required Fixes

**Fix 1 — `--accent-empathy` restored to `#E88BA9` in `screen-04-effort-loans.html:23`. CONFIRMED FIXED.**

Line 23 reads `--accent-empathy: #E88BA9`. The amber regression (`#E8B86B`) from the Round-2 sweep is gone. `--stat-aura: #E8B86B` at line 28 is untouched and correct. No other empathy-tinted tokens in the file are affected. PASS.

**Fix 2 — `--accent-empathy` restored to `#E88BA9` in `screen-06-reveal-stats.html:23`. CONFIRMED FIXED.**

Line 23 reads `--accent-empathy: #E88BA9`. Same pattern as Fix 1. `--stat-aura: #E8B86B` at line 28 is untouched. PASS.

**Fix 3 — `--accent-empathy` restored to `#E88BA9` in `screen-09-save-share.html:23`. CONFIRMED FIXED.**

Line 23 reads `--accent-empathy: #E88BA9`. Same pattern. `--stat-aura: #E8B86B` at line 28 is untouched. PASS.

**Fix 4 — `screen-06-reveal-stats.html` AURA `desc`/`data`/`threshold` rewritten to brand-gravity copy. CONFIRMED FIXED.**

- Line 767 (`stats.AURA.desc`): `'How much weight your school’s name carries — endowment per student, marketing reach, athletic budget. ISU lands mid-pack on the institutional brand-gravity scale.'` — brand-gravity framing, no HMN language. PASS.
- Line 777 (`TUTORIAL_STEPS` AURA `desc`): `'How much weight your school’s name carries — endowment per student, marketing reach, athletic budget. Real signal, not vibes. Some schools don’t have it yet.'` — verbatim §3 copy. PASS.
- Line 785 (`RECEIPT_DATA` AURA `data`): `'Composite basis: endowment + marketing + athletics<br>Endowment per FTE: $12.5k · Marketing ratio: 3.4%<br>Source: IPEDS Finance + EADA athletics'` — IPEDS Finance + EADA athletics provenance, no O*NET task-ratio data. `threshold` uses brand-gravity tier labels (`minimal brand signal`, `niche regional`, `solid mid-tier`, `strong national`, `flagship`). PASS.

**Fix 5 — `screen-04-effort-loans.html:554` AURA `short`/`detail` rewritten to brand-gravity framing. CONFIRMED FIXED.**

Line 554 (`STAT_NAMES.AURA`): `short: "How much weight your school's name carries"`, `detail: "Endowment per student, marketing reach, athletic budget. Real signal, not vibes. Some schools don't have it yet. Source: IPEDS Finance + EADA athletics."` — brand-gravity copy throughout, IPEDS Finance + EADA athletics cited, no HMN or O*NET language. PASS.

##### Round-3 Regression Check: Round-2 Confirmed-Pass Items

All items confirmed clean in Round 2 remain clean. Spot-checked:

- `frontend/src/styles/tokens.css`: `--color-stat-aura: #E8B86B` at line 49; `--color-accent-empathy: #E88BA9` at line 36; `--color-stat-hmn` absent. PASS.
- `frontend/tailwind.config.ts`: `stat.aura: "var(--color-stat-aura)"` at line 57; `glow-aura` at line 131; `stat.hmn` absent. PASS.
- `frontend/src/components/build-results/bossData.ts`: `STAT_COLORS.aura.bg` is `rgba(232,184,107,0.15)` at line 85; `STAT_INFO.aura.title` is `"Brand Gravity"`, `definition` verbatim §3 copy, `source` is `"IPEDS Finance + EADA athletics"` at lines 111-114. No HMN or Human Edge references. PASS.
- `frontend/src/data/statExplanations.ts`: `StatKey` union includes `"aura"`, excludes `"hmn"`. PASS.
- `frontend/src/i18n/strings.ts`: `stat.aura.name`, `stat.aura.explanation` entries present in all three locales (en, es, ar); no `stat.hmn` entries. PASS.
- `frontend/src/components/landing/PentagonGlow.tsx`: `label: "Brand Gravity"` at line 8; no `"Human"` label. PASS.
- `frontend/src/components/tree/treeFlowLayout.ts`: no `hmn` or `HMN` references. PASS.
- `frontend/src/components/PentagonChart.tsx`: no `hmn` or `HMN` references. PASS.

##### Round-3 Verdict

- [x] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

All five Round-2 required fixes are in place. The three mockup files now correctly declare `--accent-empathy: #E88BA9` (DESIGN.md §Color Tokens §Accents) alongside `--stat-aura: #E8B86B` (DESIGN.md §Color Tokens §Stat Colors). The AURA data objects in `screen-06-reveal-stats.html` and `screen-04-effort-loans.html` carry brand-gravity copy and IPEDS Finance + EADA athletics provenance throughout — no O*NET task-ratio language, no HMN framing remains. No regression on any of the round-2 confirmed-pass items. The shipped frontend product code is fully compliant. Ship it.

---

#### Round 2 — Re-review (@fp-design-auditor, preserved for iteration history)

**Status:** CHANGES REQUESTED — REMEDIATED
**Reviewed:** 2026-05-02

##### Round-2 Verification: Five Round-1 Findings

**Finding #1 — `PentagonChart.dataPolygon` null vertices at outer perimeter. CONFIRMED FIXED.**

`/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/PentagonChart.tsx:55-56`. The function now branches explicitly: when `raw === null || raw === undefined`, it returns `vertexPos(i, RADIUS)` (the outer perimeter position). The `?? 0` coercion that collapsed null to center is gone. The open-ring vertex dot already rendered at the outer perimeter in round 1 — the polygon fill now matches that geometry. PASS.

**Finding #2 — `PentagonGlow.tsx:8` label reads `"Brand Gravity"`. CONFIRMED FIXED.**

`/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/landing/PentagonGlow.tsx:8`: `label: "Brand Gravity"`. The stale `"Human"` string is gone. The `PentagonGlow.test.tsx` filter at line 23-25 is updated to include `"Brand Gravity"` and the test asserts 5 labels are found. PASS.

**Finding #3 — `bossData.ts:85` `STAT_COLORS.aura.bg` is `rgba(232,184,107,0.15)`. CONFIRMED FIXED.**

`/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/build-results/bossData.ts:85`: `aura: { text: "var(--color-stat-aura)", bg: "rgba(232,184,107,0.15)" }`. RGB values (232, 184, 107) correctly decode from `#E8B86B`. The old empathy pink rgba is gone from this entry. PASS.

**Finding #4 — `bossData.ts:111-115` `STAT_INFO.aura` definition and source match §3. CONFIRMED FIXED.**

Lines 111-115:
- `title: "Brand Gravity"` — correct.
- `definition: "How much weight your school's name carries — endowment per student, marketing reach, athletic budget. Real signal, not vibes. Some schools don't have it yet."` — verbatim §3 copy. PASS.
- `source: "IPEDS Finance + EADA athletics"` — verbatim §3 source. PASS.

**Finding #5 — Three mockup HTMLs: `HMN` / `#E88BA9` / `--stat-hmn` references gone. PARTIAL — two new issues introduced by the fix.**

The three §3-required swaps (stat key HMN→AURA, CSS token name `--stat-hmn`→`--stat-aura`, AURA vertex hex `#E88BA9`→`#E8B86B`) are present in all three files. `--stat-aura: #E8B86B` is declared at line 28 of each file; all AURA vertex colors, bar fills, and label colors use `#E8B86B`; the `HMN` stat key is absent from all data arrays. The label "Brand Gravity" appears where "Human Edge" previously appeared. The three explicit swap targets are correct.

However, the sweep was not scoped to AURA-specific occurrences — it replaced every `#E88BA9` in the three files, including the `--accent-empathy` variable, and did not update the body copy fields that described human-skills measurement under the AURA key.

##### Round-2 New Findings

**New Finding A — `--accent-empathy` clobbered in all three mockups.**

| File | Line | Found | Expected per DESIGN.md §Color Tokens |
|------|------|-------|--------------------------------------|
| `docs/mockups/screen-04-effort-loans.html` | 23 | `--accent-empathy: #E8B86B` | `--accent-empathy: #E88BA9` |
| `docs/mockups/screen-06-reveal-stats.html` | 23 | `--accent-empathy: #E8B86B` | `--accent-empathy: #E88BA9` |
| `docs/mockups/screen-09-save-share.html` | 23 | `--accent-empathy: #E8B86B` | `--accent-empathy: #E88BA9` |

DESIGN.md §Color Tokens defines `--color-accent-empathy: #E88BA9` (pink — "Human connection, emotional content"). The hex sweep replaced this definition with the AURA amber. Any element in these mockups that references `var(--accent-empathy)` — including the Burnout boss card and empathy-tinted pills — now renders amber instead of pink. The §3 swap scope was `--stat-hmn` → `--stat-aura`; `--accent-empathy` was never in scope.

**Required fix:** In each of the three HTML files, restore line 23 to `--accent-empathy: #E88BA9`. The `--stat-aura: #E8B86B` on line 28 of each file is correct and must not be changed.

**New Finding B — `screen-06-reveal-stats.html` and `screen-04-effort-loans.html` retain stale HMN body copy on the AURA data objects.**

The hex, label, and CSS token on the AURA vertex were swapped correctly, but the `desc`, `data`, and `threshold` text fields in the AURA data objects still describe human-skills measurement rather than institutional brand gravity.

`/Users/jcernauske/code/bright/futureproof-data/docs/mockups/screen-06-reveal-stats.html`:
- Line 767: `desc: 'How much does this job depend on uniquely human skills? Client relationships and judgment calls keep the human edge moderate.'` — stale HMN copy. Expected: §3 AURA body ("How much weight your school's name carries — endowment per student, marketing reach, athletic budget. Real signal, not vibes.").
- Line 777 (TUTORIAL_STEPS): `desc: 'How much does this job depend on uniquely human skills — empathy, creativity, judgment, persuasion? Higher means harder to replace.'` — stale HMN copy.
- Line 785 (RECEIPT_DATA): `data: 'Human task ratio: 0.61<br>Key tasks: Client advising, judgment calls<br>Source: O*NET Work Activities'` and `threshold: '1-2: <0.2 ...'` — O*NET task-ratio data belonging to HMN, not AURA. Expected: IPEDS Finance + EADA athletics provenance.

`/Users/jcernauske/code/bright/futureproof-data/docs/mockups/screen-04-effort-loans.html`:
- Line 554: `AURA: { full: 'Brand Gravity', short: 'Needs uniquely human skills', detail: 'How much does this job depend on empathy, creativity, judgment, and persuasion? Higher means harder to replace. Source: O*NET Work Activities.' }` — `short` and `detail` fields describe HMN. Both must reflect brand gravity and cite IPEDS Finance + EADA athletics per §3.

`screen-09-save-share.html` displays no expandable stat descriptions; it has no stale body copy. PASS on this finding.

##### Round-2 Verdict

- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

The five round-1 findings are confirmed fixed. Two new issues were introduced by the Perl hex sweep that executed Finding #5:

1. **`--accent-empathy` set to amber `#E8B86B` in all three mockups** — must be restored to `#E88BA9` per DESIGN.md §Color Tokens §Accents. Affects any empathy-tinted element (Burnout boss, empathy pills) in these mockup files.
2. **Stale HMN body copy in `screen-06-reveal-stats.html` (lines 767, 777, 785) and `screen-04-effort-loans.html` (line 554)** — descriptive text fields on the AURA data objects must be rewritten to §3 AURA copy and provenance. The stat label, hex, and CSS token are correct; only the `desc`/`short`/`detail`/`data`/`threshold` text strings are stale.

The shipped frontend product code (`tokens.css`, `tailwind.config.ts`, `PentagonChart.tsx`, `PentagonGlow.tsx`, `bossData.ts`, `statExplanations.ts`, `treeFlowLayout.ts`, `i18n/strings.ts`) is fully compliant and unaffected by these findings. The two new issues are confined to `docs/mockups/`.

---

#### Round 1 — Original Audit (@fp-design-auditor, preserved for iteration history)

**Status:** CHANGES REQUESTED — REMEDIATED
**Reviewed:** 2026-05-02

#### Audit Scope

Mechanical token and pattern compliance for the AURA axis introduction per
DESIGN.md (Brightpath design system). Each finding cites the file, line,
DESIGN.md section, and the expected value.

---

## `frontend/src/styles/tokens.css`

### PASS
- `--color-stat-aura: #E8B86B` is at line 49, placed within the stat-colors block alongside the other four stat tokens (ERN, ROI, RES, GRW). Token name matches spec exactly.
- `--color-stat-hmn` is absent. The old alias has been deleted as the visionary directed (§3). The empathy accent at line 36 (`--color-accent-empathy: #E88BA9`) is present and untouched.
- `--shadow-glow-aura: 0 0 20px rgba(232, 184, 107, 0.3)` is at line 142. The rgba components (232, 184, 107) correctly decode from `#E8B86B` (0xE8=232, 0xB8=184, 0x6B=107). Shadow follows the exact pattern specified in §3 and matches the DESIGN.md §Elevation & Shadows glow family format.

### FAIL
None.

---

## `frontend/tailwind.config.ts`

### PASS
- `stat.aura: "var(--color-stat-aura)"` is at line 57 inside the `stat` block, exposing `text-stat-aura` and `bg-stat-aura`. Correct.
- `shadow-glow-aura` is registered at line 131 under `boxShadow` pointing to `var(--shadow-glow-aura)`. Correct.
- `stat.hmn` is absent.

### FAIL
None.

---

## `backend/templates/wrapped/_base.css`

### PASS
- `--stat-aura: #E8B86B` is at line 36 within the Stats block. Matches the frontend token hex exactly.
- `--stat-hmn` is absent.

### FAIL
None.

---

## `frontend/src/components/PentagonChart.tsx`

### PASS
- AXES array (lines 22–28) includes `{ key: "aura", label: "AURA", color: "var(--color-stat-aura)" }` as the 5th entry. Token reference correct; no hardcoded hex.
- `dataPolygon` keys array (line 45): `["ern", "roi", "res", "grw", "aura"]`. Order consistent with AXES.
- Missing-data ring (lines 182–202): when `isAbsent`, vertex renders as `<circle>` with `fill="none"`, `stroke="var(--color-text-muted)"`, `strokeWidth="1.5"`. Matches §3 (1.5px stroke, no fill, `--color-text-muted`). The `<motion.g>` carries `data-stat={axis.key}` and `data-state="absent"` at line 188, satisfying §3 accessibility spec.
- Missing-data label (line 251): `{isAbsent ? \`${axis.label} —\` : axis.label}`. Em-dash suffix correct.
- No numeric value rendered when `isAbsent` (lines 252–256 render the value div only when `!isAbsent`). Correct per §3 ("no `—/10`, no `0/10`").
- `role="img"` and `aria-label` unchanged at line 67.

### FAIL
- **Missing-data polygon closes to center instead of null-skipping the absent vertex.** `dataPolygon` at line 49 uses `stats[key] ?? 0` for absent values, which places the polygon vertex at `RADIUS * 0 = center`. The polygon fill therefore draws a degenerate zero-length spike to center for the absent AURA vertex — it does not skip that vertex. §3 Interactions item 1 specifies: "the radar polygon fill simply doesn't extend to that vertex (the area path uses `null`-skip so the fill stops at the RES and GRW vertices and the AURA region reads as a 'missing slice of the area,' not a 'zero slice'"). The visual difference is semantically load-bearing: zero implies measurement, missing implies absence. **Expected:** polygon path skips or uses `undefined` / null-fill for absent vertices so the fill has an open cut at that vertex. **Found:** `stats[key] ?? 0` at `PentagonChart.tsx:49` treats `null` as zero. Per spec §3 Interactions item 1 and DESIGN.md §The Pentagon (filled polygon behavior).

### WARNINGS
- The absent ring uses `opacity` on the parent `<motion.g>` at value `0.6 * dotOpacity`. The spec says "stroke-color `text-muted` at 60% opacity." Using element-level opacity rather than `strokeOpacity` is visually equivalent but differs from the spec's framing. Non-blocking.

---

## `frontend/src/components/landing/PentagonGlow.tsx`

### PASS
- `abbr: "AURA"` and `color: "var(--color-stat-aura)"` at line 8. Token-clean.
- All five vertex color references at lines 136–142 use `var(--color-stat-aura)` for the 5th entry.

### FAIL
- **Stale `label` value on AURA axis renders on the landing page.** Line 8 reads `label: "Human"`. The `label` field is rendered in JSX at line 59 (`{axis.label}`) as visible full-name text on the landing pentagon decoration. `"Human"` is the old HMN era label. The correct label per §3 and `statExplanations.ts` is `"Brand Gravity"`. **Expected:** `label: "Brand Gravity"`. **Found:** `label: "Human"` at `PentagonGlow.tsx:8`. Per spec §3 UI/UX Design and DESIGN.md §Color Tokens §Stat Colors (semantic correctness).

---

## `frontend/src/data/treeFlowLayout.ts`

### PASS
- `STAT_COLORS["aura"] = "#E8B86B"` at line 51 matches the DESIGN.md token hex exactly.
- `STAT_KEYS` at line 54 is `["ern", "roi", "res", "grw", "aura"]`. Correct.
- No hardcoded `#E88BA9` present.

---

## `frontend/src/data/statExplanations.ts`

### PASS
- `StatKey` union at line 9: `"ern" | "roi" | "res" | "grw" | "aura"`. The `"hmn"` literal has been removed.
- AURA entry (lines 80–91):
  - `name: "Brand Gravity"` — matches §3 AURA card title exactly.
  - `explanation:` "How much weight your school's name carries — endowment per student, marketing reach, athletic budget. Real signal, not vibes. Some schools don't have it yet." — matches §3 AURA card body verbatim.
  - `source: "IPEDS Finance + EADA athletics"` — matches §3 source line exactly.
  - `color: "var(--color-stat-aura)"` — token reference, no hardcoded hex.
  - `textClass: "text-stat-aura"` / `bgClass: "bg-stat-aura"` — correct per tailwind.config.ts.
- RES entry (lines 54–65): explanation and source match §3 RES card copy verbatim.

### FAIL
None.

---

## `frontend/src/i18n/strings.ts`

### PASS
- `"stat.aura.name": "Brand Gravity"` at line 288. Correct.
- `"stat.aura.explanation"` at line 293 matches §3 AURA body verbatim.
- `"stat.res.name": "AI Resilience"` at line 286. Correct.
- `"stat.res.explanation"` at line 291 matches §3 RES card body verbatim.
- `"stat.hmn.*"` keys are absent. Clean removal.
- Spanish (`es`) and Arabic (`ar`) locales have `stat.aura.*` keys in the same structural position.

### FAIL
None.

---

## `backend/app/services/receipts.py`

### PASS
- No `stats.hmn` reference in `stats_receipt`. HMN line is gone.
- RES 3-branch conditional (lines 197–216):
  - Both present: `"blended from stat_res {raw_res} + stat_hmn {raw_hmn} (50/50 mean, draft)"` — matches §3 receipt copy exactly.
  - `raw_hmn is None`: `"stat_res only (no O*NET task signal — stat_hmn unavailable for this SOC)"` — matches §3.
  - `raw_res is None`: `"stat_hmn only (no AI exposure signal — stat_res unavailable for this SOC)"` — matches §3.
- AURA line (lines 229–237): present branch `"AURA {aura}/10 ← {basis_label} (institution-level)"` and missing branch `"AURA — (no brand-gravity data for this school yet)"`. Unitid is not surfaced in the user-facing string per §3.
- `_humanize_basis` mapping (lines 242–260): all four §3-specified basis codes map to the exact §3-specified human-readable labels. The NULL fallback returns `"unknown basis"` — defensive; this branch cannot fire on shipped data per the spec's logic.

### FAIL
None.

---

## Contrast Verification

Visionary contrast claims for `#E8B86B` vs. DESIGN.md background tiers, verified against actual token hex values per WCAG 2.1 relative luminance:

| Surface | Token hex | Claimed | Computed | Delta | WCAG |
|---------|-----------|---------|----------|-------|------|
| `bg-void` | `#12131F` | 9.74:1 | **10.10:1** | +0.36 | AAA |
| `bg-deep` | `#1B1D30` | 8.91:1 | **9.09:1** | +0.18 | AAA |
| `bg-mid` | `#232545` | 7.92:1 | **8.09:1** | +0.17 | AAA |
| `bg-surface` | `#2D3060` | 6.79:1 | **6.75:1** | −0.04 | AA, AAA-large |
| `bg-raised` | `#3A3D75` | 5.25:1 | **5.46:1** | +0.21 | AA, AAA-large |

All values meet or exceed WCAG AA for normal text. No claim is overstated. The `bg-surface` delta of −0.04 is within floating-point rounding and still comfortably above AA (4.5:1). The popover left-edge 3px accent stripe is decorative and has no WCAG contrast minimum.

---

## Focus States

### PASS
- `StatInfoPopover.tsx` line 89: the ask-Gemma trigger uses `focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:outline-none`. `focus-ring` resolves to `var(--color-focus-ring)` = `rgba(123, 184, 224, 0.4)` per DESIGN.md §Focus States. No amber focus ring introduced.
- No amber (`#E8B86B` or `rgba(232, 184, 107, ...)`) found in any focus or outline rule across `frontend/src/`. Search returned zero hits.
- Left-edge accent stripe at `StatInfoPopover.tsx:60` uses `borderLeft: \`3px solid ${colors.text}\`` which resolves to `var(--color-stat-aura)` for AURA — correct per §3 ("The AURA color does, however, drive the left-edge accent stripe").

### FAIL
None.

---

## `frontend/src/components/build-results/bossData.ts`

### FAIL
- **`STAT_COLORS.aura.bg` is hardcoded to the old HMN/empathy pink.** Line 85 reads `aura: { text: "var(--color-stat-aura)", bg: "rgba(232,139,169,0.15)" }`. The `bg` value `rgba(232, 139, 169, 0.15)` decodes to `#E88BA9` — the old HMN/empathy hex. The correct AURA background wash must derive from `--color-stat-aura: #E8B86B`, which at 15% opacity is `rgba(232, 184, 107, 0.15)`. `STAT_COLORS` is imported by `StatInfoPopover` and rendered as the stat's background context. **Expected:** `bg: "rgba(232,184,107,0.15)"`. **Found:** `bg: "rgba(232,139,169,0.15)"` at `bossData.ts:85`. Per DESIGN.md §Color Tokens §Stat Colors (semantic correctness — the AURA bg wash must derive from the AURA token, not the empathy token).

- **`STAT_INFO.aura.definition` contains stale HMN copy.** Lines 112–114 read: `"Measures how much of this job relies on interpersonal skills, empathy, creativity, and other distinctly human capabilities that AI struggles to replicate."` This is the old Human Edge (HMN) definition. AURA measures institutional brand gravity — endowment, marketing, athletics — not human-skills ratio. `STAT_INFO` is imported and rendered directly by `StatInfoPopover` (`StatInfoPopover.tsx:27–69`), so this stale copy appears in the live Stat Info Popover when the user taps `?` on the AURA stat. The correct body per §3 is: "How much weight your school's name carries — endowment per student, marketing reach, athletic budget. Real signal, not vibes. Some schools don't have it yet." **Expected:** §3 AURA card body. **Found:** old HMN body at `bossData.ts:112–114`. Per DESIGN.md §Stat Info Popover and spec §3.

- **`STAT_INFO.aura.source` is stale.** Line 115 reads `source: "O*NET Work Context"`. The correct source per §3 is `"IPEDS Finance + EADA athletics"`. **Expected:** `"IPEDS Finance + EADA athletics"`. **Found:** `"O*NET Work Context"` at `bossData.ts:115`. Per spec §3 AURA card source line.

Note: `STAT_INFO.aura.title: "Brand Gravity"` at line 111 is correct. Only `definition` and `source` are stale.

---

## `docs/mockups/screen-06-reveal-stats.html`

### FAIL
- **HMN vertex not swapped to AURA.** The file retains `--stat-hmn: #E88BA9` (line 28), `HMN: { value: 6, color: '#E88BA9', full: 'Human Edge', ... }` (line 767), `"hmn"` in stat-order arrays (lines 800, 890, 925, 1113), and `HMN: '#E88BA9'` in the colors object (line 1114). None of the three §3-required changes have been applied (label swap HMN→AURA, CSS variable swap `--stat-hmn→--stat-aura`, hex swap `#E88BA9→#E8B86B`). This mockup was declared in scope by the visionary in §3 and is the primary spec mock for the stat-reveal screen. Per spec §3 "Mockups to update."

---

## `docs/mockups/screen-04-effort-loans.html`

### FAIL
- **HMN vertex not swapped to AURA.** The file retains `--stat-hmn: #E88BA9` (line 28), `HMN: 6` in `BASE_STATS` (line 546), "Human Edge" in the descriptions object (line 554), `HMN: '#E88BA9'` in the colors object (line 583), and `'HMN'` in all stat-order arrays (lines 647, 700, 701, 769, 770). None of the three §3-required swaps applied. Declared in scope by the visionary. Per spec §3 "Mockups to update."

---

## `docs/mockups/screen-09-save-share.html`

### FAIL
- **HMN vertex not swapped to AURA.** The file retains `--stat-hmn: #E88BA9` (line 28), hardcoded `fill="#E88BA9"` on SVG circle elements (lines 617, 622), "Human Edge" label text in the bar row (line 631), and `background:#E88BA9` in the bar fill (line 631). None of the three §3-required swaps applied. Declared in scope by the visionary. Per spec §3 "Mockups to update."

---

## Summary

| File | Result | Issues |
|------|--------|--------|
| `frontend/src/styles/tokens.css` | PASS | — |
| `frontend/tailwind.config.ts` | PASS | — |
| `backend/templates/wrapped/_base.css` | PASS | — |
| `frontend/src/components/PentagonChart.tsx` | FAIL | `dataPolygon` uses `?? 0` on absent stats; polygon fill closes to center rather than null-skipping the absent vertex |
| `frontend/src/components/landing/PentagonGlow.tsx` | FAIL | `label: "Human"` renders on landing page; should be `"Brand Gravity"` |
| `frontend/src/data/statExplanations.ts` | PASS | — |
| `frontend/src/i18n/strings.ts` | PASS | — |
| `backend/app/services/receipts.py` | PASS | — |
| `frontend/src/components/build-results/bossData.ts` | FAIL | (1) `STAT_COLORS.aura.bg` hardcoded to old HMN pink `rgba(232,139,169,0.15)`; (2) `STAT_INFO.aura.definition` is stale HMN copy; (3) `STAT_INFO.aura.source` is stale `"O*NET Work Context"` |
| `frontend/src/data/treeFlowLayout.ts` | PASS | — |
| Contrast ratios | PASS | All ratios meet or exceed visionary claims; no claim overstated |
| Focus states | PASS | Global `--color-focus-ring` used everywhere; no amber focus ring introduced |
| `docs/mockups/screen-06-reveal-stats.html` | FAIL | No HMN→AURA swaps applied |
| `docs/mockups/screen-04-effort-loans.html` | FAIL | No HMN→AURA swaps applied |
| `docs/mockups/screen-09-save-share.html` | FAIL | No HMN→AURA swaps applied |

#### Required Changes Before APPROVED

1. **`frontend/src/components/PentagonChart.tsx`** — `dataPolygon` function: null-skip absent stat values in the polygon path so the fill region reads as a missing slice rather than a degenerate zero-area spike to center. (Spec §3 Interactions item 1.)

2. **`frontend/src/components/landing/PentagonGlow.tsx` line 8** — Change `label: "Human"` to `label: "Brand Gravity"`.

3. **`frontend/src/components/build-results/bossData.ts` line 85** — Change `bg: "rgba(232,139,169,0.15)"` to `bg: "rgba(232,184,107,0.15)"`.

4. **`frontend/src/components/build-results/bossData.ts` lines 112–115** — Rewrite `STAT_INFO.aura.definition` to the §3 AURA body copy. Change `source` to `"IPEDS Finance + EADA athletics"`.

5. **`docs/mockups/screen-06-reveal-stats.html`** — Apply the three §3-specified swaps: label HMN→AURA, `--stat-hmn` token → `--stat-aura`, hex `#E88BA9` → `#E8B86B`.

6. **`docs/mockups/screen-04-effort-loans.html`** — Same three swaps.

7. **`docs/mockups/screen-09-save-share.html`** — Same three swaps.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

Seven specific fixes required. Items 1–4 affect user-visible shipped product code: the live pentagon chart's area fill semantics, the landing page pentagon label, and the build results stat popover body copy. Items 5–7 are mockup drift declared in scope by the visionary. Token definitions, shadow shapes, contrast ratios, focus state conventions, receipt copy, and i18n strings are all fully compliant.

### Code Review (@faang-staff-engineer)

#### Round 2 — 2026-05-02 (re-review)

**Status:** APPROVED — 2026-05-02
**Reviewer:** Staff Engineer (15 YOE, production incident survivor)

##### Summary

All five critical/serious findings and all three minor findings from Round 1 are resolved correctly. No new regressions introduced. Look, I love Claude, BUT I had to actually read the diffs to confirm — and they hold up. Verified bit-by-bit against the original locations:

| # | Severity | Original Issue | Fix Verified |
|---|----------|----------------|--------------|
| 1 | 🔴 | `MiniPentagon` collapses null AURA to center | `MiniPentagon.tsx:27-36, 61-77` — null vertices anchored at outer perimeter; open-ring `<circle>` with `fill="none"`, `stroke="var(--color-text-muted)"`, `data-state="absent"` per absent vertex. Matches PentagonChart treatment. ✅ |
| 2 | 🔴 | `StatBarRow` renders null as "0" | `StatBarRow.tsx:13-46` — `isAbsent` gates fill bar (only renders when `!isAbsent`), em-dash for value, dashed border + 0.4 opacity on track, `data-state="absent"` attribute. ✅ |
| 3 | 🔴 | `PentagonOverlay.buildStats` strips nulls | `PentagonOverlay.tsx:25-36, 46` — inner map preserves nulls (`v === undefined ? null : v`), each axis has explicit `?? null` fallback, `emptyStats` is all-null. PentagonChart's open-ring fires correctly. ✅ |
| 4 | 🔴 | `CharacterCard` shows null as "0" | `CharacterCard.tsx:64-100` — same em-dash + hollow dashed track treatment as StatBarRow. The dead `?? "—"` is gone. ✅ |
| 5 | 🟠 | `_fetch_aura` doesn't catch exceptions | `stat_engine.py:85-93` — `try/except Exception` (with `noqa: BLE001` justification), `logger.warning` on failure, degrades to `(None, None, None)`. AURA failure no longer cascades to a 500 on `/outcomes`. ✅ |
| 6 | 🟡 | `data/builds/` not gitignored | `.gitignore:19` — added under "CLI harness local state" alongside `backend/data/`. ✅ |
| 7 | 🟡 | `WhatItTakes.pickTopStat` keeps stale AURA candidate | `WhatItTakes.tsx:77-81` — candidate set is now `[res, grw]`. Comment updated to cite Decision 5 (delta_aura is institution-invariant by construction). ✅ |
| 8 | 🔵 | `_score_ai` reason degrades on partial-null | `boss_fights.py:524-534` — builds `res_str` and `hmn_str` independently; final string always reads `"raw stat_res {N|unavailable} + stat_hmn {N|unavailable} = {sum}"`. Audit trail stays complete on the partial-null branch. ✅ |

##### Regression Check

I read every changed file end-to-end looking for new issues. None found:

- **MiniPentagon side-effect in `.map`:** The `absent.push(i)` during `dataPoints.map()` is a side-effect inside a map callback, which would normally make me twitch — but the array is local, the map result is consumed once, and there's no async or memoization context. Functionally clean.
- **CharacterCard type widening:** `raw` ends up `number | null | undefined` (TS allows undefined for missing record keys). The `isAbsent` check covers both null and undefined explicitly. Clean.
- **`_fetch_aura` bare `Exception`:** Appropriate for fail-soft contract — Decision 5 + Open Item #4 explicitly normalize "no AURA" as a real state, and the `noqa: BLE001` comment documents the intent. The `logger.warning` ensures the failure is observable in prod.
- **`_score_ai` partial-null path:** When `score is None` (both inputs null), returns early with `"raw stat_res and stat_hmn unavailable"` and the boss fight is skipped. When only one input is null, both operands are emitted with `"unavailable"` standing in for the missing one. Bit-exact with the all-present case for downstream parsers.
- **PentagonOverlay `emptyStats`:** Now all-null; passing this as the `stats` prop to PentagonChart while overlays are present means the underlying chart renders no base shape (overlays drive the visuals). PentagonChart's `isOverlayMode` branch (PentagonChart.tsx:123-166) only consumes `overlay.stats`, not `stats`, so the all-null base is correct.

All four answers from the Round 1 "Questions for the Author" section can be addressed in §10 Discussion or §11 Open Items — they're not blocking.

##### Verification Cross-Check

Spec claims tests pass: backend 1337, pipeline 2124, frontend 774, Vite build clean, ruff clean. I take that at face value (the §9 Verification table is signed off by @fp-builder); my own re-review is purely on the source diffs against the Round 1 findings.

##### Verdict
- [x] APPROVED
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

All Round 1 findings remediated. No new issues introduced. The presentation-layer null-AURA contract now flows end-to-end across all four pentagon-consuming surfaces (PentagonChart, MiniPentagon, StatBarRow, CharacterCard) plus the compare-screen overlay (PentagonOverlay). The backend fail-soft contract is in place. Ship it.

The CEO said use AI. I said review thoroughly. We both got what we wanted.

---

#### Round 1 — 2026-05-02 (history preserved)

**Status:** CHANGES REQUIRED — 2026-05-02
**Reviewer:** Staff Engineer (15 YOE, production incident survivor)

##### Summary

Solid presentation-layer reshape. Models are consistent across Pydantic, TypeScript, and SQL. The MCP tool is correctly registered with bool-rejection, governance attachment, and structured-null responses. The DuckDB schema migration self-heals on crash. Tests are tight (1337 backend / 2124 pipeline / 774 frontend, all green), and the Decision-4-revised raw-row scoring keeps Fight AI bit-exact with pre-reshape behavior.

The blocker isn't in the data plumbing — it's in the front end's missing-data treatment. Spec §3 promises that ~11% of builds (264+27 unitids) will render an explicit "—" on the AURA vertex / bar so users read it as "no signal" instead of "your school scored zero." `PentagonChart` honors that. **Three other surfaces silently coerce `null → 0`**, which means roughly one in nine builds will misrepresent its school's brand gravity as a failing score on the menu, the build-results screen, and the compare overlay. That's a 3am page when a school's marketing team notices. Fix those three components and this is a clean ship.

Also flagged: `_fetch_aura` doesn't catch exceptions, so a transient pyiceberg error will turn AURA-unavailability into a 500 on `/outcomes`. AURA is supplementary signal — losing it should NOT kill the whole pentagon. And `data/builds/` is not in `.gitignore` (only `backend/data/` is). Today no code writes there, so it's cosmetic, but if someone resurrects on-disk JSON later it'll be a foot-gun.

Everything else (bool guard, schema migration, HMN→RES fold, `_blend_res` perf, MCP perf, `_node_to_dict` rename) checks out.

##### Findings

###### Finding 1: 🔴 CRITICAL — `MiniPentagon` renders missing AURA as a zero-score vertex

**Impact:** Every menu thumbnail for ~11% of builds shows the AURA polygon collapsed to center, indistinguishable from an actual zero score. No open-ring marker, no "—" cue. Schools without IPEDS Finance + EADA + marketing data look bottom-tier on every menu card. Per spec Decision 7 + Open Item #4, this is exactly the misread the design was supposed to prevent.
**Location:** `frontend/src/components/menu/MiniPentagon.tsx:24`
```tsx
const v = Math.max(0, Math.min(10, stats[key] ?? 0));
```
**The Problem:** Bare `?? 0` collapses null to a numeric zero. The polygon math then renders the missing vertex at the center, identical to "school scored 0/10 on AURA." Unlike `PentagonChart`, this component has no open-ring fallback for absent vertices — there's nowhere for the user to learn "we don't have this signal."
**The Fix:** Either (a) port the open-ring pattern from `PentagonChart` (track absent vertices separately, draw an outer-perimeter ring instead of collapsing to center), or (b) at minimum render a distinct visual hint (dashed stroke for the polygon segments touching an absent vertex, or muted dot color). Recommend option (a) for consistency with the main pentagon's treatment.

###### Finding 2: 🔴 CRITICAL — `StatBarRow` (PathCard) displays missing AURA as literal "0"

**Impact:** On the build-results screen (the primary post-build view), the AURA stat bar for ~11% of builds renders an empty bar with the text "0" beside it. Same misread as Finding 1, but worse because it's the canonical results screen — it's the first thing a student sees after submitting their build.
**Location:** `frontend/src/components/build-results/StatBarRow.tsx:10,33`
```tsx
const v = value ?? 0;
// ...
<span ...>{v}</span>
```
**The Problem:** Line 10 coerces null to 0 for the bar width math, then line 33 renders that same 0 as the value text. By the time we reach the JSX, `v` is the number 0, so a defensive `?? "—"` here would do nothing.
**The Fix:**
```tsx
const isAbsent = value === null || value === undefined;
const v = isAbsent ? 0 : value;
const fillPct = (v / 10) * 100;
// ...
<div
  className="h-full rounded-full"
  style={{
    width: `${fillPct}%`,
    background: colors?.text,
    opacity: isAbsent ? 0 : 0.8,
    transition: "width 0.4s ease-out",
  }}
/>
// ...
<span ...>{isAbsent ? "—" : v}</span>
```

###### Finding 3: 🔴 CRITICAL — `PentagonOverlay.buildStats` strips null AURA before reaching `PentagonChart`

**Impact:** The compare-screen overlay (2-4 stacked pentagons) silently coerces null AURA to 0 BEFORE handing the stats off to `PentagonChart`. So even though `PentagonChart` has the open-ring fallback, it never fires here — by the time the chart sees the data, every build has a numeric `aura` value. A school with no AURA data looks like a school that scored 0 on AURA, side-by-side with its peers.
**Location:** `frontend/src/components/menu/PentagonOverlay.tsx:23,30`
```tsx
map[row.label] = row.values[buildIndex] ?? 0;
// ...
aura: map[STAT_ORDER[4]] ?? 0,
```
**The Problem:** Two layers of `?? 0` (the inner map, and the explicit fallback). To respect the absent-vertex contract, `PentagonStats.aura` must stay `null` all the way to `PentagonChart`.
**The Fix:**
```tsx
function buildStats(stats: CompareStatRow[], buildIndex: number): PentagonStats {
  const map: Record<string, number | null> = {};
  for (const row of stats) {
    map[row.label] = row.values[buildIndex] ?? null;
  }
  return {
    ern: map[STAT_ORDER[0]] ?? null,
    roi: map[STAT_ORDER[1]] ?? null,
    res: map[STAT_ORDER[2]] ?? null,
    grw: map[STAT_ORDER[3]] ?? null,
    aura: map[STAT_ORDER[4]] ?? null,
  };
}
```
(`PentagonStats` from `@/types/build` already allows null for ern/roi/res/grw — lines 7–11.)

###### Finding 4: 🔴 CRITICAL — `CharacterCard` displays missing AURA as "0" with empty bar

**Impact:** Same misread, third surface. The compare-flow character card lists each stat with a value bar and a numeric label. AURA-null builds show "AURA 0" with an empty bar.
**Location:** `frontend/src/components/menu/CharacterCard.tsx:61,81`
```tsx
const val = statMap[label] ?? 0;
// ...
<span ...>{val ?? "—"}</span>
```
**The Problem:** Line 61 already coerces to 0, so the `val ?? "—"` on line 81 is dead code — `val` is never null at that point. Note: `statMap` itself is built with `?? null` on line 27, so the data is preserved up to line 61.
**The Fix:** Read `statMap[label]` directly (don't coerce) and gate display:
```tsx
const raw = statMap[label];
const isAbsent = raw === null || raw === undefined;
const val = isAbsent ? 0 : raw;
const pct = Math.max(0, Math.min(100, (val / 10) * 100));
// ...
<div
  className="h-full rounded-full"
  style={{ width: isAbsent ? "0%" : `${pct}%`, background: statColor }}
/>
// ...
<span ...>{isAbsent ? "—" : val}</span>
```

###### Finding 5: 🟠 SERIOUS — `_fetch_aura` doesn't catch MCP exceptions, takes the whole pentagon down

**Impact:** AURA is supplementary signal — Decision 5 + Open Item #4 explicitly accommodate the case where it's unavailable. But if `mcp_client.call("get_institution_aura", ...)` raises an exception (PyIceberg catalog flake, transient I/O error, contract YAML parse failure inside `attach_governance`, etc.), it bubbles all the way up through `compute_pentagon` → router. The router only catches `ValueError`, so any other exception becomes a 500. The student gets no pentagon at all because we couldn't look up brand gravity.
**Location:** `backend/app/services/stat_engine.py:70-86`
```python
def _fetch_aura(unitid: int) -> tuple[int | None, str | None, str | None]:
    result = mcp_client.call("get_institution_aura", {"unitid": unitid})
    row = result.get("data")
    if not row:
        return None, None, None
    return (
        as_int(row.get("aura_score")),
        row.get("aura_score_basis"),
        row.get("aura_score_version"),
    )
```
**The Problem:** No exception handler. The MCP handler itself returns the `[{"error": ...}]` envelope cleanly, but if the underlying `query_iceberg_simple` throws (PyIceberg has been known to surface metadata-corruption exceptions), nothing catches it.
**The Fix:**
```python
def _fetch_aura(unitid: int) -> tuple[int | None, str | None, str | None]:
    try:
        result = mcp_client.call("get_institution_aura", {"unitid": unitid})
    except Exception as exc:  # noqa: BLE001 — AURA must never break the pentagon
        logger.warning("aura lookup failed for unitid=%s: %s", unitid, exc)
        return None, None, None
    row = result.get("data")
    if not row:
        return None, None, None
    return (
        as_int(row.get("aura_score")),
        row.get("aura_score_basis"),
        row.get("aura_score_version"),
    )
```
Failing-soft is the right semantics: the user gets an "AURA —" build instead of a 500. This also matches how the four other null-AURA surfaces (receipts, ask_gemma, boss_fights stat_explainer, frontend) already render — the failure mode is already wired end-to-end, we just need to take the open lane.

###### Finding 6: 🟡 MODERATE — `data/builds/` is not gitignored

**Impact:** Today no code writes there (Decision 9 deleted the on-disk JSON path entirely; `builds.py` is DuckDB-only). But `.gitignore` only excludes `backend/data/` — `data/builds/` is unprotected. If a future change resurrects on-disk JSON (or if pre-reshape builds re-appear from a stash), they'll get committed silently. With "No path is out of scope" as a project rule, this is a small foot-gun worth closing now.
**Location:** `.gitignore` (the file itself)
**The Fix:** Add one line:
```
data/builds/
```
Spec §6 already says "directory does not exist on this install" — the gitignore entry costs nothing and prevents future regressions.

###### Finding 7: 🟡 MODERATE — Stale "humanWork" label and dead delta path on AURA in `WhatItTakes`

**Impact:** `pickTopStat` iterates `res / grw / aura`, picks the largest absolute delta vs. root, and renders a "what it takes" bullet. But per Decision 5, `delta_aura` is institution-invariant: every branch inherits the root's AURA, so `selected.aura - root.aura === 0` always. The candidate is dead code — it never wins. AND the i18n label key is `future.stat.humanWork`, which is leftover HMN-era copy that misnames AURA as "human work."
**Location:** `frontend/src/components/tree/WhatItTakes.tsx:72-77, 15` (comment)
```tsx
type Stat = { key: "res" | "grw" | "aura"; labelKey: string };
const candidates: Stat[] = [
  { key: "res", labelKey: "future.stat.aiResilient" },
  { key: "grw", labelKey: "future.stat.growth" },
  { key: "aura", labelKey: "future.stat.humanWork" },
];
```
**The Problem:** Two issues bundled. (a) `aura` should not be in this list at all — it can never produce a non-zero delta on a branch. (b) Even if it could, `humanWork` is the wrong label. The doc-comment on line 15 also references `aura` as a candidate, which is misleading.
**The Fix:** Drop `aura` from `candidates`, drop the mention from the comment block. If the list shrinks to two, that's fine — RES + GRW are the only two stats with branch deltas anyway (delta_ern/delta_roi are skipped intentionally, see line 15 comment).

###### Finding 8: 🔵 MINOR — `_score_ai` reason-string format degrades on partial-null

**Impact:** Spec §6 says `_score_ai` reason: `"raw stat_res {r} + stat_hmn {h} = {sum}"`. When one input is null, the actual format becomes `"raw stat_res 8 = 8"` — missing the "+ stat_hmn None" half. Receipts will read slightly inconsistently between full and partial-null rows. Not a correctness issue (the score is right), just a copy nit.
**Location:** `backend/app/services/boss_fights.py:528-534`
**The Fix:** Either always emit both parts (with `null` literal for the missing one) or accept the degradation and update §6's prose. Either is fine; flagging for awareness.

##### What's Actually Good

Credit where it's due:

- **MCP handler is tight.** Bool-rejection is correctly defended at the only place that matters (the handler — the validator passes bools through). String/missing/error envelopes all return structured-null with governance attached. 8 P0/P1 tests cover the surface area.
- **Schema migration is crash-safe.** `_init_schema` checks for the legacy `hmn` column before dropping; if a crash happens between DROP and CREATE, the next startup sees no table and the `CREATE TABLE IF NOT EXISTS` self-heals. `_add_column_if_missing` and `_backfill_animal_emoji` short-circuit on missing tables.
- **Decision 4 revised was the right call.** Reading raw row scores in `_score_ai` keeps Fight AI bit-exact with pre-reshape behavior — no silent score flips on ~1.05M rows. The test fixture correctly defaults `raw_stat_hmn = aura` to preserve existing test bit-exactness without touching production semantics.
- **`_blend_res` performance is fine.** ~50 rows per build × one Decimal allocation per row is unmeasurable. No need to cache or replace with arithmetic. Half-up vs banker's matters for the rounding contract — Decimal is the right hammer.
- **Single AURA MCP call per `compute_pentagon`.** No N+1. Threaded into every outcome via kwargs. CIP substitution doesn't change unitid, so the lookup is correctly stable under the substitution path (Decision 6).
- **HMN→RES fold paths are correct.** `_clamp_impact("HMN+4")` produces `"RES+2"` (folded, then magnitude-clamped). `_DELTA_TOKEN` regex in skill_pool matches HMN and re-buckets to RES at line 515. Both have explicit tests.
- **Cross-file consistency is solid.** PentagonStats (Pydantic), PentagonStats (TS), BuildSummary (Pydantic + TS), TreeNode (Pydantic + TS), AppliedSkill (Pydantic + TS), CareerBranch (Pydantic + TS) all match. SQL `aura INTEGER` matches Pydantic `int | None`. `aura_score_basis: str | None` is consistent across all 6 references (career.py, stat_engine.py × 4, ask_gemma.py, receipts.py, build.ts).
- **`Node`/`TreeNode` rename propagated correctly.** `_node_to_dict` in routers/branches.py emits `aura` (line 54). Frontend `TreeNode.aura` matches. `raw_stat_res` / `raw_stat_hmn` correctly aren't sent to the wire (frontend doesn't need them — Fight AI scoring happens server-side).

##### Required Changes

Routing for spec §10 Discussion:

| # | Severity | Owner | Change |
|---|----------|-------|--------|
| 1 | 🔴 | Implementation (Claude Code) | Fix `MiniPentagon` to render missing-AURA vertex distinctly (open ring or muted segment, not collapse-to-zero) |
| 2 | 🔴 | Implementation (Claude Code) | Fix `StatBarRow` to display "—" for null value, not "0" |
| 3 | 🔴 | Implementation (Claude Code) | Fix `PentagonOverlay.buildStats` to preserve nulls all the way to `PentagonChart` |
| 4 | 🔴 | Implementation (Claude Code) | Fix `CharacterCard` to display "—" + empty bar for null AURA |
| 5 | 🟠 | Implementation (Claude Code) | Wrap `_fetch_aura` in try/except to fail soft on MCP exceptions |
| 6 | 🟡 | Implementation (Claude Code) | Add `data/builds/` to `.gitignore` |
| 7 | 🟡 | Implementation (Claude Code) | Drop `aura` from `WhatItTakes.pickTopStat` candidates; remove from comment |
| 8 | 🔵 | Implementation (Claude Code) (optional) | Either always emit both `_score_ai` reason parts, or update §6 prose |

Findings 1–4 share a root cause: components built before the spec called out the open-ring treatment didn't get retrofit. Recommend a short pass through every component that consumes a `PentagonStats`, `BuildSummary`, or `CompareStatRow` to confirm the missing-AURA semantics flow all the way through. The tsc + vitest suites won't catch this — the types allow null, the tests don't assert visual rendering.

##### Questions for the Author

Genuine, not gotchas:

1. Was Findings 1–4 a known scope cut (i.e., "PentagonChart was the headline surface, the rest are P1") or did they get missed? If known, please document in §6 Deviations so we don't have to rediscover it next sprint.
2. For Finding 5 — was there a deliberate decision to fail-hard on MCP errors so we'd notice them faster, or is fail-soft the intent? My read is fail-soft (Decision 5/Open Item #4 normalize "no AURA" as a real state) but I want to confirm.
3. The spec ships a 50/50 mean for `_blend_res` "pending EDA" (Open Item #1). What's the rollback plan if EDA shows the weights are way off? Is there a feature flag, or are we trusting that the next spec just edits `_blend_res`?
4. Have we load-tested the new MCP call in the `compute_pentagon` hot path? It's one extra Iceberg query per `/outcomes` request. Measured latency impact?

##### Verdict
- [ ] APPROVED
- [x] CHANGES REQUIRED
- [ ] BLOCKER

CHANGES REQUIRED on Findings 1–5. Findings 6–8 are nice-to-have and can land in a follow-up if they slip. Once 1–5 are fixed and re-tested, this is a clean approve.

---

## §9 Verification

**Status:** COMPLETE — 2026-05-02 (self-verified during implementation; @fp-builder independent pass 2026-05-02 10:48)

### Backend
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff — backend/) | PASS | No issues |
| Type check (mypy) | PASS (pre-existing errors only) | 69 errors in 18 files; 0 introduced by this spec. All error-bearing files last modified before spec commits 83dc3a3/bbb2f42. Confirmed by `git log`: api.py, stat_engine.py, builds.py, branches.py, reports.py all last touched at 610a9a7 or earlier. |
| Tests (pytest backend) | PASS | 1337 passed, 0 failed |
| Tests (pytest pipeline — must stay green) | PASS | 2124 passed, 0 failed, 1 deselected |

**Note on project-root ruff:** `uv run ruff check .` from project root surfaces lint issues in `governance/chaos-manifests/` and `scripts/` (unused imports, bare f-strings, E402). These are pre-existing and outside the backend/ and frontend/ scope checked by the build pipeline. They do not affect the spec verdict.

**mypy error inventory (pre-existing, not introduced by this spec):**
- `app/models/api.py` — 12 `[type-arg]` errors (`dict` without type args). File last modified 610a9a7 (wip(career-tree)), 2 commits before spec work.
- `app/services/stat_engine.py` — `[import-not-found]`, 2× `[unused-ignore]`, `[no-any-return]`. File last modified db69ab3 (residency-aware tuition), 9+ commits before spec work.
- `app/services/builds.py` — `[unused-ignore]`, `[no-untyped-def]`. Last modified 610a9a7.
- `app/services/sessions.py`, `app/services/wrapped_renderer.py`, `app/services/gemma_client.py`, `app/services/skill_pool.py`, `app/services/intent.py`, `app/services/guidance.py` — various `[no-any-return]`, `[type-arg]`, `[unused-ignore]`. All pre-date spec commits.
- `app/routers/branches.py`, `app/routers/builds.py`, `app/routers/reports.py`, `app/routers/sessions.py`, `app/routers/schools.py`, `app/routers/profile.py`, `app/routers/skills.py`, `app/routers/gauntlet.py`, `app/routers/guidance_router.py` — `[no-untyped-def]`, `[arg-type]`, `[index]`. All last modified 610a9a7 or earlier.
- This spec's two commits (83dc3a3, bbb2f42) only modified: `backend/app/services/ask_gemma.py`, `docs/specs/pentagon-stat-reshape.md`, and frontend files. `ask_gemma.py` contributes 0 mypy errors.

### Frontend
| Check | Result | Details |
|-------|--------|---------|
| TypeScript | PASS | No errors |
| Tests (vitest) | PASS | 774 passed, 0 failed (66 test files) |
| Production build (Vite) | PASS | Built in 1.59s; 1.15 MB JS / 81.93 kB CSS / 1.81 kB HTML |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | All checks passed | — | — |

---

## §10 Discussion

```
[YYYY-MM-DD HH:MM] @source-agent → @target-agent
Message content.
```

---

## §11 Final Notes

**Human Review:** PENDING

### Open Items Flagged for Follow-up

1. **Blended RES weights — DRAFT pending EDA.** The 50/50 mean shipped here is a placeholder. A follow-up spec (`stat-engine-blended-res-weights.md`) should run EDA on the joint distribution of `stat_res` × `stat_hmn` across `consumable.program_career_paths`, pick weights, and update `_blend_res` only — no other surface should need to change. EDA owner: @fp-data-reviewer.
2. **AURA tutorial copy.** @fp-copywriter pass before merge — the stub copy in §3 is not shipping copy.
3. **Stat color token.** @fp-design-visionary picks: new color or rename `--color-stat-hmn`. If new, propose in §3 before implementation begins.
4. **AURA "—" coverage rate is ~11%, not edge case.** Per @fp-data-reviewer v1.0 review: 264 of 2,550 student-reachable unitids (10.4%) have NO row in `consumable.institution_aura`, plus 27 more with NULL `aura_score`. About 11% of plausible builds will render "—" on the 5th vertex. @fp-design-visionary must confirm in §3 that the "—" treatment reads as "we don't have this signal for your school" and not as "your school has zero brand." Decision 7 (no caveat) was framed for an edge case; at 11% it's a regular occurrence.
5. ~~**Legacy saved-build migration.**~~ No longer applicable. Per Decision 9 (v1.1), saved builds are reset and there is no migration path. If a future spec wants to re-introduce saved-build durability, that's a separate decision.
