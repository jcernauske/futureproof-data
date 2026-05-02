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

## Status: DRAFT

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
| Spec Version | 1.0 (DRAFT) |
| Last Updated | 2026-05-02 |
| Blocked By | — |
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

- [ ] `consumable.institution_aura` is reachable from the backend via a new MCP tool that follows the same `ToolDef` / handler / governance-attachment pattern as the existing 9 tools.
- [ ] `PentagonStats.hmn` is removed from both Pydantic and TypeScript models. `PentagonStats.aura` is present and nullable.
- [ ] `stat_engine.compute_pentagon` and `compute_one` populate `aura` from a single MCP lookup per build (keyed on `unitid`). The lookup is reused across every `CareerOutcome` row in the same build.
- [ ] Blended RES is computed in `stat_engine` from the row's pre-existing `stat_res` and `stat_hmn`. The DRAFT formula clamps 1–10 and degrades correctly when one or both inputs are NULL (see §4 "Blended RES — DRAFT formula").
- [ ] All HMN references in `boss_fights.py`, `receipts.py`, `skill_pool.py`, `skill_recs.py`, `report_gen.py`, `next_steps.py`, `guidance.py`, `ask_gemma.py`, `career_pick_qna.py`, `builds.py`, `branch_tree.py`, `career_tree.py`, `wrapped_renderer.py`, and `routers/branches.py` are removed or rewritten to reference blended RES and/or AURA.
- [ ] `_score_ai` in `boss_fights.py` is rewritten to test blended RES against the existing thresholds (or against new EDA-tuned thresholds — see §2 Decision 4).
- [ ] `AppliedSkill.delta_hmn` is removed; only `delta_res` remains for the resilience axis. `AppliedSkill.delta_aura` is **not** added (AURA is institution-level — skills can't shift it).
- [ ] `CareerBranch.delta_hmn` is removed and replaced by `delta_aura: int = 0` (always zero — same school, same AURA — see §2 Decision 5).
- [ ] Frontend `PentagonChart` renders the same 5-vertex shape with the 5th vertex labelled "AURA" using the new (or renamed) stat color token.
- [ ] `STAT_EXPLANATIONS` in `frontend/src/data/statExplanations.ts` swaps the `hmn` entry for an `aura` entry with copy provided by @fp-copywriter (or stub copy in implementation, copywriter pass before merge).
- [ ] Receipts (`stats_receipt`, `skill_recs_receipt`, `next_steps_receipt`) emit AURA provenance referencing `aura_score_basis` from the institution_aura row, and the blended-RES receipt cites both source scores plus the blend formula.
- [ ] Legacy saved builds on disk (JSON under `data/builds/`) load without raising — `Build.career.stats.hmn` in the JSON is dropped on parse; `aura` defaults to `None` so the legacy build still renders (with the 5th vertex showing "—").
- [ ] Full backend (ruff + mypy + pytest) and frontend (tsc + vitest + Vite production build) all pass.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | RES and HMN collapse into one **blended RES**; AURA takes the freed pentagon slot. | RES and HMN are two views of the same AI-displacement question; AURA is currently invisible despite the pipeline producing it. The pentagon shape (5 axes) stays identical so the visual identity, the share-card layout, the radar chart, and the compare overlays all keep working without redesign. | (a) Drop the pentagon to 4 stats. Rejected — visual identity is load-bearing for the share card and the design system. (b) Add a 6th axis for AURA (hexagon). Rejected — breaks every existing layout, share frame, mockup, and Wrapped frame, and the axis count is part of the brand. (c) Keep both RES and HMN; surface AURA in a sidebar/badge instead of the pentagon. Rejected — AURA would feel like an afterthought, which is exactly the failure mode the EADA pipeline was meant to fix. |
| 2 | Blended RES is computed in `stat_engine` (Python) from the existing `stat_res` + `stat_hmn` on each row. **No re-promotion of `consumable.program_career_paths`.** | The blend is a presentation-layer choice, not a domain truth. Keeping the underlying row scores intact means the next iteration of the formula (after EDA) is a stat-engine PR, not a data-pipeline run. The user's instruction is unambiguous: no pipeline changes. | (a) Add a new `stat_res_blended` column to `consumable.program_career_paths` via a Gold transformer change. Rejected — explicitly out of scope per Jeff. (b) Re-promote `consumable.ai_exposure` with a different formula. Rejected — same reason; also conflates the AI-exposure measurement with the resilience presentation. |
| 3 | The blend formula is **DRAFT** and pinned at the simplest defensible default until EDA: `round_half_up(0.5 * stat_res + 0.5 * stat_hmn)`. NULL handling: if one input is NULL, return the other; if both NULL, return NULL. Final weights flagged for `@fp-data-reviewer` via §5. | EDA needs to confirm whether the two scores are correlated enough that a 50/50 blend distorts the distribution, or whether one should dominate (e.g. RES because Karpathy/Anthropic adoption signal is stronger evidence than O*NET task counts). Shipping the simplest blend lets the rest of the reshape land while the formula is tuned. | (a) Pick weights upfront. Rejected — would need the EDA anyway, and shipping with the wrong weights stamps the wrong number on every receipt. (b) MAX. Rejected — biases optimistic and erases the conservative half of the signal. (c) MIN. Rejected — same problem in the other direction. |
| 4 | The Fight AI scorer keeps its existing thresholds (`win_at_or_above=14`, `draw_at_or_above=10`) but its scoring formula degrades from `RES + HMN` (max 20) to `2 × blended_RES` (max 20). Conceptually identical scale; **arithmetically the same when blended RES = (old RES + old HMN) / 2**. | The thresholds are tuned to a 0–20 score scale. Doubling the blended RES preserves the scale and means existing test outcomes stay stable. If EDA picks a weighted blend, the doubling stays — `2 × blended` is still 0–20. The alternative is rescoring every test fixture; that's wasted churn. | (a) Halve the thresholds and use a single `blended_RES` (1–10). Rejected — every fixture changes and we lose continuity with the existing tuning. (b) Replace the formula with something AURA-flavored. Rejected — AURA does not measure AI exposure; it would fail the "no path is out of scope" rule the moment a student typed "deaf education" into Harvard. |
| 5 | `CareerBranch.delta_aura` exists in the model but is **always 0**. The branch JSON shape stays compatible with the radar overlay code, which expects 5 deltas. | Branches are within-career trajectories at the same institution, so AURA is invariant by construction. Emitting `0` keeps the overlay drawing (no NaN gaps) and lets the frontend treat all 5 deltas uniformly. | (a) Drop the field entirely. Rejected — the frontend branch-detail panel iterates the 5 deltas; dropping forces a special-case in TS. (b) Compute per-target-school AURA (since branches can imply moves across institutions). Rejected — out of scope; branches as shipped don't carry a target unitid. |
| 6 | AURA is read **once per build** from the new MCP tool keyed on `unitid`. The same value is stamped into every `CareerOutcome` returned for that build. CIP substitution does **not** change AURA — a substituted CIP at the same school still sees the same school's aura_score. | AURA is institution-level by construction (`consumable.institution_aura` is keyed on UNITID alone). Repeating the lookup per career row would be wasteful (1 unitid → 1 row); CIP substitution is a major-side fallback and has nothing to do with the institution. | Per-row AURA lookup. Rejected — N identical queries. |
| 7 | When `consumable.institution_aura` returns NULL `aura_score` (the institution has neither EADA nor IPEDS-Finance coverage, or only has athletics-only data), `PentagonStats.aura` is `None` and the pentagon renders the 5th vertex at radius 0 with the value "—". No imputation, no warning banner, no "Limited data" caveat. | Per the user's standing memory ("Don't show 'Limited data' warnings on career cards from CIP substitution") and the standing rule that AURA is additive, missing institutional brand data is not the student's problem and not worth a UI hedge. The receipt explains *why* (the aura_score_basis was NULL) for anyone who taps the "?". | Show a "Limited data" badge. Rejected per memory `feedback_no_substitution_caveat.md`. Impute from a default. Rejected — would falsify the receipt. |
| 8 | The new MCP tool is named `get_institution_aura` and lives in `src/mcp_server/futureproof_server.py` next to the other 9 tools. It returns the full `consumable.institution_aura` row (all 19 columns) plus governance metadata via `attach_governance`. | The tool surface mirrors `get_ai_exposure` and `get_regional_price_parity` — a single-keyed lookup against a Gold table. Returning the full row lets receipts cite `aura_score_basis`, `coverage_tier`, and `aura_score_version` without a follow-up query. | Return only `aura_score`. Rejected — receipts need basis + version for provenance honesty. |

### Constraints

- **No data pipeline changes.** No raw, silver, gold, or consumable transformer touches. No schema migration. No re-promotion.
- **No new consumable tables.**
- **Blended RES formula is DRAFT** — the simplest defensible default ships first; EDA tunes weights in a follow-up that touches `stat_engine.py` only.
- **AURA is institution-level only.** No per-career AURA. No imputation. No skill deltas affect AURA. No branch deltas affect AURA.
- **Backend and frontend cut over together.** No `hmn` field hangs around in either model for "compat." Old saved builds are tolerant on read (drop the unknown field) but never re-written with `hmn`.
- The pentagon stays a pentagon (5 axes). The radar shape, the compare overlays, the share frame, and the mockups all must keep working with the same shape.

---

## §3 UI/UX Design

> @fp-design-visionary fills this section before implementation begins.

### Mockups

The pentagon visual is unchanged. Only the 5th vertex changes from "HMN" → "AURA" with a new (or renamed) color token. The remaining four axes (ERN, ROI, RES, GRW) keep their colors.

```
            ERN
           ●─10
          ╱  │  ╲
       ROI   │   AURA          (formerly HMN)
       ●     │     ●
        ╲    │    ╱
         ╲   │   ╱
        RES──┼──GRW
         ●       ●
       (blended RES + HMN)
```

Stat tutorial overlay copy (first build only) gets two modified cards:

- **RES card:** "AI Resilience. How well this career holds up against AI — both because the daily work needs people and because automation can't do most of it." (rewritten to reflect that it now combines task-level human-essential signal with adoption-level resilience signal)
- **AURA card (new):** stub copy until @fp-copywriter pass — "Brand Gravity. How much institutional weight your school's name carries. Built from athletic spend, marketing spend, and endowment per student. Not every school has this signal."

### Interactions

No new interactions. The reroll mechanic, the boss flow, the radar animation, and the overlay compare all stay the same. The 5-vertex iteration in `PentagonChart.tsx` line 22-28 picks up the new key list with zero structural change.

### Responsive Behavior

Identical to current pentagon. The radar SVG is intrinsically responsive.

### Brightpath Design References

- Token: `--color-stat-aura` (proposed). Either (a) introduce a new token color for institutional brand gravity (suggest a deep amber/copper to differentiate from the existing 5 stats and signal "institutional weight"), or (b) repurpose the existing `--color-stat-hmn: #E88BA9` and rename the CSS variable. @fp-design-visionary picks. The Tailwind utility (`text-stat-aura`, `bg-stat-aura`) follows whichever route.
- The PRD v8 mockups (`docs/mockups/screen-06-reveal-stats.html`, `screen-04-effort-loans.html`, `screen-09-save-share.html`) all show 5-vertex pentagons. They'll need a one-line label swap; no layout work.

### Accessibility

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| Pentagon SVG | `#svg-pentagon` | role=img | "Five-stat radar chart showing your career stats" (unchanged) |
| AURA vertex dot | `[data-stat="aura"]` | decorative | (label only — value read from text) |
| AURA tutorial card | `#tutorial-card-aura` | section | "Brand Gravity stat explainer" |

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
│        PentagonStats(ern, roi, res=blended_res, grw,               │
│                      aura=aura_row.aura_score)                     │
└───────────────────────────────────────────────────────────────────┘
```

The aura row is fetched once per `compute_pentagon` call. Every `CareerOutcome` for that build carries the same `stats.aura`.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/mcp_server/futureproof_server.py` | Modify | Add `get_institution_aura` ToolDef + `_handle_get_institution_aura` handler. Add `INSTITUTION_AURA_TABLE = "consumable.institution_aura"` and `INSTITUTION_AURA_RESPONSE_FIELDS` constants near the top. Append the new ToolDef inside `get_tools()` (after `get_schools_for_career`). |
| `tests/mcp/test_get_institution_aura.py` | Create | Pipeline-side tests for the new MCP handler (parity with `tests/mcp/test_get_ai_exposure.py`). Cover: present row, NULL aura_score row, missing unitid, governance attachment. |
| `backend/app/models/career.py` | Modify | `PentagonStats`: rename `hmn` → `aura`. `CareerBranch`: rename `delta_hmn` → `delta_aura` (always 0). `AppliedSkill`: remove `delta_hmn` entirely. |
| `backend/app/models/api.py` | Modify | Audit for any HMN references; update. |
| `backend/app/services/stat_engine.py` | Modify | New helper `_blend_res(stat_res, stat_hmn)` (the DRAFT formula). New helper `_fetch_aura(unitid)` that calls MCP. `compute_pentagon` reads aura once per call and stamps every outcome. `_row_to_outcome` reads `row["stat_res"]` and `row["stat_hmn"]`, blends them, and emits `PentagonStats(..., res=blended, aura=aura_score)`. Drop the `hmn=` kwarg. |
| `backend/app/services/boss_fights.py` | Modify | `_score_ai`: replace `_safe_sum(career.stats.res, career.stats.hmn)` with `_safe_sum(career.stats.res, career.stats.res)` (i.e. `2 × blended_RES`) and update the reason string. `stat_explainer`: drop the HMN bullet, rewrite the RES bullet to reflect blended meaning, append an AURA bullet. Audit `_boss_context` (no current HMN refs there but verify). Audit `_NARRATIVE_SYSTEM` — it lists `HMN` in the forbidden stat-codes list; keep that line and add `AURA` so Gemma never echoes either. |
| `backend/app/services/receipts.py` | Modify | `stats_receipt`: drop the HMN line, rewrite the RES line to cite the blend (`"RES X/10 ← blended from stat_res Y + stat_hmn Z (mean)"`), append an AURA line with `aura_score_basis` provenance. `skill_recs_receipt` + `next_steps_receipt`: drop `HMN` from the inline stat dump, add `AURA`. `_skill_delta_str`: drop the HMN delta. |
| `backend/app/services/skill_pool.py` | Modify | The Gemma prompt that asks for skills with stat deltas references HMN today. Rewrite to reference blended RES (and explicitly tell Gemma not to emit deltas for AURA). Drop `delta_hmn` from the parser. The fallback skill pool likely has HMN deltas — re-bucket them as RES deltas. |
| `backend/app/services/skill_recs.py` | Modify | Audit & strip HMN refs in the Gemma prompt and parsed shape. |
| `backend/app/services/career_pick_qna.py` | Modify | Audit & strip HMN refs in the Gemma prompt context. |
| `backend/app/services/builds.py` | Modify | `compare_builds` and any per-stat aggregation: replace HMN with AURA. Save/load: tolerate `hmn` in the on-disk JSON (drop the field on parse), never re-emit it. |
| `backend/app/services/branch_tree.py` | Modify | If it inflates branch deltas from MCP, rename `delta_hmn` → `delta_aura` and force to 0. |
| `backend/app/services/career_tree.py` | Modify | Same as branch_tree. |
| `backend/app/services/next_steps.py` | Modify | Audit & rewrite the Gemma prompt to drop HMN and add AURA. |
| `backend/app/services/guidance.py` | Modify | Audit & rewrite the Gemma's Take prompt. |
| `backend/app/services/ask_gemma.py` | Modify | Audit & rewrite the chat system prompt context. |
| `backend/app/services/report_gen.py` | Modify | Audit & rewrite the markdown report templates. |
| `backend/app/services/wrapped_renderer.py` | Modify | The Wrapped frame templates iterate stats — rename labels and confirm 5-stat layout still works. |
| `backend/app/routers/branches.py` | Modify | Audit & strip HMN refs from response shaping. |
| `backend/tests/test_stat_engine.py` | Modify | New tests: `_blend_res` unit tests (both present, one None, both None, edge bounds), AURA lookup populates `stats.aura` on every outcome, CIP substitution preserves AURA, NULL aura_score → `stats.aura is None`. Update existing assertions that referenced `stats.hmn`. |
| `backend/tests/test_boss_fights.py` | Modify | `_score_ai` now scores `2 × RES`. Update fixtures. Verify thresholds still classify correctly. |
| `backend/tests/test_receipts.py` | Modify | Update expected receipt strings; add AURA-line assertions. |
| `backend/tests/test_skill_pool.py` | Modify | Drop HMN delta assertions; verify the parser ignores HMN if Gemma still emits one (back-compat for one release). |
| `backend/tests/test_builds.py` | Modify | New test: load a legacy saved build whose JSON has `hmn` — must parse without raising and emit `aura=None`. Save round-trip must NOT re-emit `hmn`. |
| `backend/tests/test_branch_tree.py` | Modify | Rename `delta_hmn` assertions → `delta_aura == 0`. |
| `frontend/src/types/build.ts` | Modify | `PentagonStats.hmn` → `PentagonStats.aura`. `AppliedSkill.delta_hmn` removed. `CareerBranch.delta_hmn` → `delta_aura`. |
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
| `frontend/src/api/mockBuild.ts` | Modify | Replace `hmn:` mock values with `aura:`. |
| `frontend/src/api/mockMenu.ts` | Modify | Same. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | Modify | Update HMN references. |
| `frontend/src/components/landing/DataSourcesSection.tsx` | Modify | If it lists HMN as a sourced stat, swap to AURA + cite EADA + IPEDS Finance. |
| All matching `*.test.tsx` files for the components above | Modify | Mirror the source changes — every fixture that hand-built a `PentagonStats` object needs `aura` instead of `hmn`. |

### Data Model Changes

**Pydantic** (`backend/app/models/career.py`):

```python
class PentagonStats(BaseModel):
    ern: int | None
    roi: int | None
    res: int | None      # now blended from stat_res + stat_hmn
    grw: int | None
    aura: int | None     # was: hmn

class AppliedSkill(BaseModel):
    # ...
    delta_ern: int
    delta_roi: int
    delta_res: int       # absorbs former delta_hmn impact
    delta_grw: int
    # delta_hmn REMOVED
    # delta_aura NOT ADDED (institution-level — skills can't shift)
    delta_burnout_raw: int
    delta_ceiling_raw: int

class CareerBranch(BaseModel):
    # ...
    delta_ern: int | None
    delta_roi: int | None
    delta_res: int | None
    delta_grw: int | None
    delta_aura: int = 0  # was: delta_hmn — institution-invariant, always 0
```

**TypeScript** (`frontend/src/types/build.ts`): mirror the Pydantic changes verbatim.

### Service Changes

**New blend formula** (DRAFT — `stat_engine.py`):

```python
def _blend_res(stat_res: int | None, stat_hmn: int | None) -> int | None:
    """DRAFT: 50/50 mean of the two AI-resilience signals.

    Pending EDA. The two underlying scores measure related but distinct
    things — stat_res is adoption-level resilience (Karpathy + Anthropic
    + Gemma), stat_hmn is task-level human-essential ratio (O*NET).
    EDA needs to confirm the correlation and pick weights; until then
    a simple mean ships.
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

**Boss AI scorer** (`boss_fights.py`):

```python
def _score_ai(career: CareerOutcome) -> tuple[int | None, str]:
    """Blended RES counted twice — preserves the 0-20 scale of the old
    RES + HMN formula so existing thresholds (win=14, draw=10) still
    classify the same outcomes as before the reshape."""
    if career.stats.res is None:
        return None, "blended RES unavailable"
    score = career.stats.res * 2
    return score, f"blended RES {career.stats.res} ×2 = {score}"
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
| `backend/tests/test_boss_fights.py` | Fight AI scoring tests | High | Formula changes from `RES + HMN` to `2 × blended_RES` |
| `backend/tests/test_receipts.py` | stats_receipt / skill_recs_receipt / next_steps_receipt | High | HMN line dropped, RES line rewritten, AURA line added |
| `backend/tests/test_skill_pool.py` | skill delta parsing tests | Med | `delta_hmn` removed from the model |
| `backend/tests/test_skill_recs.py` | recommendation prompt tests | Low | Prompt text changes |
| `backend/tests/test_builds.py` | save/load round-trip | Med | Need new legacy-build read test |
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
| All test files listed above marked High/Med | Rename `hmn` field references, swap to `aura` where appropriate, update Fight AI fixture math | Direct consequence of the model rename and the blend formula |
| `backend/tests/test_stat_engine.py` | Add new tests for `_blend_res` (all four NULL cases) and for AURA-from-MCP lookup | New code path needs P0 coverage |
| `backend/tests/test_builds.py` | Add legacy-build-read test (a fixture JSON containing `hmn`) | The migration must not break existing saved builds |
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
| P0 | `backend/tests/test_boss_fights.py` | `test_score_ai_uses_doubled_blended_res` | `_score_ai` returns `(2 * stats.res, "...")` and classifies with the existing thresholds |
| P0 | `backend/tests/test_builds.py` | `test_load_legacy_build_with_hmn_field` | a JSON fixture containing `stats.hmn` and `delta_hmn` parses cleanly with `aura=None` and `delta_hmn` dropped |
| P0 | `tests/mcp/test_get_institution_aura.py` | `test_returns_row_for_known_unitid` | full row + governance metadata |
| P0 | `tests/mcp/test_get_institution_aura.py` | `test_returns_null_for_unknown_unitid` | structured null response |
| P0 | `tests/mcp/test_get_institution_aura.py` | `test_handles_null_aura_score_row` | row with NULL aura_score still returns the row (caller decides how to render) |
| P1 | `backend/tests/test_receipts.py` | `test_stats_receipt_emits_aura_line_with_basis` | receipt cites `aura_score_basis` from the lookup |
| P1 | `backend/tests/test_receipts.py` | `test_stats_receipt_res_line_cites_blend_inputs` | `"blended from stat_res X + stat_hmn Y"` appears |
| P1 | `frontend/src/components/PentagonChart.test.tsx` | `renders_aura_label_on_fifth_vertex` | label and color hook |
| P1 | `frontend/src/types/build.test.ts` (if exists) or fold into existing | type compile check | model contract |

#### Test Data Requirements

- A JSON fixture for the legacy-build read test: a real saved build copied from `data/builds/` and renamed under `backend/tests/fixtures/legacy_build_with_hmn.json`. Hand-edit to retain `stats.hmn` and `delta_hmn` so the migration path is exercised.
- A mocked `get_institution_aura` MCP response for `test_stat_engine.py` (parity with how `get_career_paths` is mocked today).

---

## §5 Architecture Review

### @fp-architect Review
**Status:** PENDING
#### Findings
[Filled in by @fp-architect]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

### @fp-data-reviewer Review
**Status:** PENDING
#### Findings
[Filled in by @fp-data-reviewer — explicit assessment of the DRAFT blend formula, the AURA-per-institution lookup pattern under CIP substitution, the AppliedSkill.delta_hmn removal migration, and the CareerBranch.delta_aura=0 invariant]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

---

## §6 Implementation Log

**Status:** PENDING

### Files Modified
| File | Change Summary |
|------|---------------|

### Deviations from Spec
[Any divergence from §3/§4 and why]

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|

---

## §7 Test Coverage

**Status:** PENDING

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest (pipeline) | | | | |
| pytest (backend) | | | | |
| vitest | | | | |

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@fp-design-auditor)
**Status:** PENDING
[Token compliance for the new AURA axis: token name, contrast vs background tiers, focus state, tutorial overlay copy match.]

### Code Review (@faang-staff-engineer)
**Status:** PENDING
#### Findings
[Filled in by reviewer — security, performance, error handling, model migration safety]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

---

## §9 Verification

**Status:** PENDING

### Backend (@fp-builder)
| Check | Result |
|-------|--------|
| Lint (ruff) | |
| Type check (mypy) | |
| Tests (pytest backend) | |
| Tests (pytest pipeline — must stay green) | |

### Frontend (@fp-builder)
| Check | Result |
|-------|--------|
| TypeScript | |
| Tests (vitest) | |
| Production build (Vite) | |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|

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
4. **Legacy saved-build migration.** This spec only handles READ migration (drop unknown `hmn` field). If we ever want to backfill `aura` into existing saved builds, that's a separate spec and not required for this reshape to ship.
