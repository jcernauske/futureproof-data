# Insight Report: Silver → Gold (silver-base-onet)

**Date:** 2026-04-16
**Agent:** @insight-manager
**Retroactive:** Yes — produced after silver-base-onet marked COMPLETE to satisfy the
silver→gold transition gate.
**Source Tables:** `base.onet_occupations`, `base.onet_activity_profiles`,
`base.onet_context_profiles`, `base.onet_career_transitions` (Iceberg, verified
against live warehouse 2026-04-16)
**Entities:** 798 BLS-level occupations
**Records:** 92,594 total Silver rows (798 + 31,734 + 44,118 + 15,944)
**Time Range:** Single-snapshot (O*NET 30.2 release)

---

## 1. Domain Context

FutureProof is an RPG-style career planner. O*NET Silver supplies the
occupation-side half of the pipeline (the college scorecard supplies the
education-side half, bridged by the CIP→SOC crosswalk). Silver O*NET powers
three FutureProof user-facing artifacts:

- **HMN stat (Human Edge)** — the fifth leg of the stat pentagon, from Work
  Activities importance (IM).
- **Burnout boss fight** — from nine Work Context elements flagged
  `is_burnout_element`.
- **Stage 3 branching tree** — from `onet_career_transitions` (occupational
  similarity, not observed transitions).

Task text for AI-boss narratives stays in Bronze by design; Silver does not
transform free text.

---

## 2. What Silver Provides (verified)

### 2.1 `base.onet_occupations` (798 rows)
- Master occupation reference at BLS SOC granularity (XX-XXXX).
- 798 = 867 derivable BLS SOCs − 69 structurally empty "All Other"/Military
  catch-all codes.
- `data_completeness_tier`: 774 `full`, 24 `partial`, 0 `none`.
- `multi_detail_flag`: 76 BLS SOCs aggregate ≥ 2 O*NET detailed codes (e.g.,
  `29-1229.01/.02/.03`); the remaining 722 are 1:1.
- `has_work_activities`, `has_work_context`, `has_tasks`, `has_related` flags
  tell downstream consumers which child tables they can safely join.
- **Join keys:** `bls_soc_code` is the universal SOC key used by BLS OOH Silver,
  Karpathy AI exposure, and the CIP-SOC crosswalk. Clean.

### 2.2 `base.onet_activity_profiles` (31,734 rows)
- Grain: `bls_soc_code × element_id`.
- 774 SOCs × 41 Generalized Work Activities, IM scale only (importance 1.0–5.0).
- Per-SOC complete `importance_rank` sequence 1–41 (zero gaps, zero duplicates).
- `is_high_importance` (importance ≥ 3.5) pre-computed.
- Multi-detail averaging: `onet_details_averaged` records how many detailed
  O*NET codes contributed; for 76 multi-detail SOCs this ranges 2–5.
- Suppress rate 0.003% (1 row). Effectively clean.
- **Feeds HMN stat** (requires classifying activities into human-intensive vs
  automatable).

### 2.3 `base.onet_context_profiles` (44,118 rows)
- Grain: `bls_soc_code × element_id`.
- 774 SOCs × 57 Work Context elements. 55 CX (1–5 scale, 42,570 rows) + 2 CT
  (1–3 scale, 1,548 rows). CXP/CTP category-percentage rows (82.9% of Bronze)
  excluded — CXP/CTP stay in Bronze for post-hackathon depth.
- `is_burnout_element` pre-flags 9 element IDs, giving O(1) SQL lookup for the
  Burnout boss.
- Suppress rate 0.04%. Clean.
- **Feeds Burnout boss fight.** See §5 for the F-01 caveat.

### 2.4 `base.onet_career_transitions` (15,944 rows)
- Grain: `bls_soc_code × related_bls_soc_code`.
- Distribution: Primary-Short 4,134 / Primary-Long 3,938 / Supplemental 7,872.
- Self-references removed (343 emerged during BLS-level aggregation).
- Zero FK orphans in either direction.
- **Important semantic:** `relationship_type = "similarity"`. Related
  Occupations measures occupational similarity, not observed career transitions
  (Career Changers/Starters files do not exist in O*NET 30.2). Any product
  built on this must surface the "modeled, not observed" disclaimer.
- **Feeds Stage 3 branching tree.**

### 2.5 Cross-table integrity
All FK constraints verified zero-orphan in the adversarial audit:
`activity_profiles.bls_soc_code`, `context_profiles.bls_soc_code`,
`career_transitions.bls_soc_code`, `career_transitions.related_bls_soc_code`
all resolve to `onet_occupations.bls_soc_code`. This is the table the
crosswalk and `base.bls_ooh.soc_code` can safely join.

---

## 3. Existing Gold Consumers & Traffic Patterns

Two Gold tables already consume O*NET Silver (`docs/specs/gold-onet-profiles.md`
status COMPLETE; `consumable.onet_work_profiles` = 798 rows and
`consumable.career_transitions` = 15,944 rows per the project CLAUDE.md
table inventory — actual DuckDB verification deferred to the gold cast run):

| Gold Table | Grain | Silver Inputs | FutureProof Use |
|------------|-------|----------------|-----------------|
| `consumable.onet_work_profiles` | bls_soc_code | occupations + activity_profiles + context_profiles | HMN score, Burnout score, `top_human_activities` and `burnout_drivers` JSON for Gemma narratives, `time_pressure` / `work_hours` / `consequence_of_error` scalar passthrough, `confidence_tier` |
| `consumable.career_transitions` | bls_soc_code × related_bls_soc_code | onet_career_transitions + occupations (for titles) | Stage 3 branching graph, enriched with source/related titles and `source_has_work_profile` / `related_has_work_profile` flags |

Downstream of those two Gold tables, `consumable.program_career_paths` (the
core 626,406-row CIP×SOC product) pulls HMN, Burnout, and top-activity JSON
per SOC. `consumable.career_branches` (15,944 rows) denormalises
`career_transitions` with computed stat deltas for the branch-tree UI.

**MCP traffic patterns (inferred from tool wiring):**
- `get_task_breakdown(soc_code)` → reads `consumable.onet_work_profiles` filtered
  on `bls_soc_code`, returns the whole row (includes `top_5_activities`,
  `top_human_activities`, `burnout_drivers`, scalar burnout drivers). Used for
  AI-boss narratives and Burnout-boss setup. One row per call.
- `get_career_branches(soc_code, primary_only=True)` → reads
  `consumable.career_branches`, filters to `is_primary=True` by default, sorts
  by `best_index`. Used for Stage 3 tree. 0–10 rows per call typically; cap
  reached via `CAREER_BRANCHES_SCAN_LIMIT`.
- Both tools are point-lookups by `bls_soc_code`. The hot path is
  `program_career_paths → list of SOCs → iterate → get_task_breakdown per SOC`
  during boss-fight construction in the backend.

**Coverage math against traffic:** Gemma calls keyed on BLS SOC resolve to a
Silver row 100% of the time for the 774 "full" occupations and degrade
gracefully for the 24 "partial" ones (null HMN/Burnout but present titles and
descriptions).

---

## 4. Proposed Additional Gold Products

The existing two O*NET Gold tables cover the FutureProof MVP surface
(HMN + Burnout + Stage 3). Below are ranked additions that the current
Silver can support without new Bronze work.

### Tier 1 — MANDATORY (auto-convert to specs if accepted)

**Note:** None of the Tier 1 mandatory boilerplate products (deduplicated
metrics table, computed ratios, YoY deltas) apply here — Silver O*NET is
single-snapshot, already deduplicated at BLS grain, and exposes IM/CX/CT on
the O*NET-defined scales. No additional Tier 1 products are required before
gold-zone work proceeds.

### Tier 2 — HIGH VALUE, MODERATE EFFORT

| # | Data Product | Description | Source | Key Metric | Why It Matters |
|---|---|---|---|---|---|
| T2-01 | `consumable.onet_activity_taxonomy` | 41-row lookup table: element_id, element_name, `is_human_intensive` flag, `is_automatable` flag, rationale string. Static dictionary, one row per Generalized Work Activity. | `base.onet_activity_profiles` distinct element_ids + the Gold-spec human-intensive classification | `is_human_intensive` coverage of all 41 elements | Today the "human-intensive" classification is hard-coded inside `src/gold/onet_work_profiles.py`. Pulling it into a governed table makes the HMN formula auditable, lets the UI explain "why is this activity human?" to students, and gives reviewers one file to challenge. Verifiable via DQ: `is_human_intensive` count matches the Gold-spec proposal. |
| T2-02 | `consumable.onet_burnout_taxonomy` | 9-row lookup: element_id, element_name, scale, burnout_direction ("higher=worse"), narrative blurb. | `base.onet_context_profiles` where `is_burnout_element=True` + Gold-spec burnout copy | Row count = 9 exactly | Same rationale as T2-01 — makes the Burnout boss formula legible and gives Gemma an explicit vocabulary for "why is this job burning people out?" **GATED by F-01** (see §5). |
| T2-03 | `consumable.onet_profile_narratives` | Pre-generated Gemma narrative snippets per SOC: `what_you_do`, `human_edge_summary`, `burnout_summary`, `ai_exposure_framing`. Precomputed at pipeline time to cut cold-start latency. | `base.onet_occupations` (description, primary_title) + `base.onet_task_statements` (Bronze, read-through) + `consumable.onet_work_profiles` | All 798 SOCs have non-null narrative; 774 have burnout + human-edge narrative | Removes Gemma from the critical path for narrative content during boss fights. Today the backend calls Gemma live, which is fine for Ollama but burns OpenRouter budget in the cloud demo. Pre-generating 798 × 4 snippets = 3,192 total calls done once, cached forever. **Verification:** one-shot Gemma eval harness checks non-empty + under token budget. |
| T2-04 | `consumable.onet_activity_signatures` | For each SOC, the top-5 and bottom-5 activity elements as a compact JSON blob. | `base.onet_activity_profiles` | `signature_complete` boolean = True for all 774 full-data SOCs | Powers "which careers match this activity profile?" queries — a natural UX for career exploration. Today there's no way to ask "find me jobs that rank high on Creative Thinking." Having pre-computed signatures makes this a cheap cosine similarity. |

### Tier 3 — EXPLORATORY / DEFERRED

| # | Data Product | Description | Dependency |
|---|---|---|---|
| T3-01 | `consumable.onet_work_context_deep` | Expose CXP/CTP category-percentage distributions for Burnout depth (e.g., "what % of the workforce reports >40hr weeks" rather than the point-estimate average). | Silver refactor to add `base.onet_context_distributions` — CXP/CTP currently stay in Bronze. |
| T3-02 | `consumable.onet_cross_rater_skills` | Join O*NET Skills + Abilities + Knowledge to Work Activities for a richer human-edge signal. | Bronze ingest of O*NET Skills/Abilities/Knowledge tables (not ingested today). |
| T3-03 | `consumable.onet_transition_weighted` | Re-weight career transitions by combined similarity + BLS OOH demand growth (i.e., "similar AND has jobs"). | Requires `base.bls_ooh` growth_projection join, stable today but needs a Gold join spec. |
| T3-04 | `consumable.task_ai_exposure` | Task-level AI exposure score per SOC — attach Karpathy SOC-level scores to the Bronze task list and let Gemma reason at task grain. | Requires a new Gold spec that reads Bronze task statements directly — crosses the Silver-stays-pure guideline and needs justification. |

### Recommendation: confirm existing Gold covers the MVP

All FutureProof hackathon-critical surfaces (HMN, Burnout, Stage 3, branching
with stat deltas, program × career paths) are already covered by the
completed `gold-onet-profiles`, `gold-futureproof-engine`, and
`gold-ai-exposure` specs. **No new Gold spec is required to ship the MVP.**
The Tier 2 items above are enhancements that become valuable if the scope
extends to post-hackathon iteration.

---

## 5. Burnout Dependency — F-01 Gate

The adversarial audit
(`governance/reviews/silver-base-onet-adversarial-audit.md`, Finding F-01)
documents that one of the nine `is_burnout_element` IDs (`4.C.3.a.2.a` —
"Impact of Decisions on Co-workers or Company Results" per the transformer
comment, versus "Responsibility for Others' Health and Safety" per the gold
spec — the two artifacts disagree on the element name) was **substituted
without the human-approval gate** the spec itself required. The original
Silver spec proposed "Responsibility for Outcomes and Results" (element
`4.C.3.b.7`), which does not exist in O*NET; the EDA proposed a replacement;
the transformer ships the replacement; but the documented "Open Decisions"
gate (spec §Open Decisions item 1) was bulk-approved alongside the DQ rules
rather than explicitly signed off.

**Consequence for this report and downstream gold work:**

- **Existing gold-onet-profiles (`consumable.onet_work_profiles`, burnout_score,
  burnout_drivers) already ships the substitution.** Every Burnout boss-fight
  score in the running pipeline uses the substituted element. This is live
  risk, not future risk.
- **No new burnout-dependent gold product may be added until F-01 is
  closed** with a dated, distinct audit-trail entry. That includes Tier 2
  item T2-02 (`onet_burnout_taxonomy`) and Tier 3 item T3-01 (CXP/CTP
  deep burnout).
- **Further, the gold-spec table (`docs/specs/gold-onet-profiles.md:160`)
  names the substituted element differently from the transformer comment
  (`src/silver/onet_transformer.py:54`).** The two artifacts must be
  reconciled as part of closing F-01 — otherwise downstream narrative
  generation will produce drifted Gemma copy between
  `burnout_drivers[*].name` (data) and the design-system tooltip text
  (frontend reads from the spec).
- **Non-burnout Gold work is not blocked.** Tier 2 items T2-01, T2-03, T2-04
  and all Tier 3 items except T3-01 touch only activity / transition /
  narrative data and can proceed. HMN, Stage 3, and career-branch products
  are unaffected.

**Recommended action order (mirrors the adversarial auditor's):**
1. Log the explicit burnout-substitution approval in
   `governance/audit-trail/` with a distinct, human-initiated timestamp.
2. Reconcile the element name between `onet_transformer.py:54` and
   `gold-onet-profiles.md:160`.
3. Update `governance/business-glossary.json` BT-059 to list the nine
   *actually shipped* element IDs (F-02).
4. Only then open new specs that key on `is_burnout_element`.

---

## 6. How Gemma Uses This via MCP for Boss Fights

The MCP surface exposes two tools sourced directly from O*NET Gold —
`get_task_breakdown` and `get_career_branches` — plus implicit consumption
via `get_career_paths` (which joins `program_career_paths` → SOC).

### 6.1 Burnout boss
- Gemma receives a SOC via the ongoing session (from `get_career_paths`).
- Backend calls `get_task_breakdown(soc_code)` →
  `consumable.onet_work_profiles` row filtered on `bls_soc_code`.
- Fields used: `burnout_score`, `burnout_score_rounded`, `burnout_drivers`
  (JSON array of the top 3 elements with values), plus the scalar passthroughs
  `time_pressure`, `work_hours`, `consequence_of_error`.
- Gemma synthesises the boss-fight narrative ("Registered Nurse: high
  consequence-of-error, long hours, time-pressure triad — your boss is
  Exhaustion"). The scalars give Gemma concrete numbers to cite.
- **F-01 impact:** `burnout_drivers` entry for element `4.C.3.a.2.a` may cite
  an element whose *name* drift-differs between data, spec, and glossary.
  Gemma will quote the name from the data blob — this is the single
  user-visible consequence.

### 6.2 Market & Ceiling bosses
- These draw primarily from `consumable.occupation_profiles` (BLS OOH
  growth/employment projections), not from O*NET. O*NET Silver's role is
  secondary: `career_transitions` lets Gemma narrate "if this market
  collapses, here's where people go" for the Market boss.

### 6.3 AI boss
- Primary source: `consumable.ai_exposure` (Karpathy) + task text from Bronze.
- O*NET's role: `top_human_activities` JSON gives Gemma the "what humans still
  do best in this job" counter-narrative. This is one of the main pay-offs
  of the HMN stat beyond the pentagon display.

### 6.4 Stage 3 branching
- `get_career_branches(soc_code)` → `consumable.career_branches` filtered on
  `soc_code`, `is_primary=True` by default, sorted by `best_index`.
- Each branch row carries pre-computed stat deltas; the UI renders them as a
  tree via the xyflow component.
- **"Modeled, not observed" disclaimer is required copy on the branch-tree
  screen** because `relationship_type = "similarity"` never becomes
  "transition" in O*NET 30.2.

---

## 7. Coverage Gaps & Risks

| Gap | Impact | Mitigation |
|---|---|---|
| 24 `partial` SOCs with null HMN and/or Burnout | These 24 SOCs will show "—" for HMN / Burnout in the pentagon and cannot be boss-fight targets. | Fallback: backend uses `confidence_tier` = "low" to substitute a CIP-level average or neighbour SOC via `career_transitions`. Already handled by the career-path-fallback spec. |
| 69 BLS SOCs excluded entirely ("All Other"/Military) | Crosswalk may return a CIP → SOC mapping that has no O*NET side. | BLS OOH Silver already flags these as catch-all; program_career_paths must filter them out. Verify via a DQ rule on the Gold side. |
| F-01 burnout semantic substitution | Live in every Burnout boss today. | Close F-01 per §5. Blocks new burnout gold products only. |
| `relationship_type = "similarity"` framed as "transitions" in UI | User may interpret the branch tree as "these are real career paths people follow" rather than "these are jobs with similar skills." | Hardcoded disclaimer on the branch-tree screen (already spec'd in `screen-branch-tree.md`). |
| Multi-detail averaging is unweighted | 76 BLS SOCs aggregate 2–5 O*NET details via simple mean. Employment-weighted means (more accurate) are deferred. | Accept for hackathon. Flag in `multi_detail_flag` so downstream can de-weight if needed. |
| Single snapshot | No way to show "how burnout has trended over time" for a SOC. | Outside scope — O*NET releases are annual and the snapshot cadence is fine for this product. |

---

## 8. AI-Ready Considerations

- **JSON-array columns (`top_human_activities`, `burnout_drivers`,
  `top_5_activities`) are already the right shape for Gemma.** The backend
  passes them through as-is via the MCP tool output. No further transformation
  needed.
- **Pre-compute narratives (T2-03).** The most expensive thing Gemma does
  today is synthesise the HMN and Burnout blurbs live. One-shot these at
  pipeline time into `onet_profile_narratives` and the MCP server becomes
  sub-second on the OpenRouter demo path.
- **Element-name drift is the #1 hallucination risk.** If the data says
  "Impact of Decisions on Co-workers" and the glossary/tooltip says
  "Responsibility for Others' Health and Safety," Gemma will eventually
  quote one and display the other. Resolve F-02 in lockstep with F-01.
- **Grounding context for Gemma's system prompt:** the substituted burnout
  element, the "similarity not transition" semantic, and the
  `confidence_tier` values are the three caveats most likely to catch Gemma
  off-guard. They belong in the system-prompt grounding at chat-agent build
  time (gold→mcp transition).

---

## 9. Chat Agent Design Considerations (preliminary, gold→mcp)

At the next zone boundary the MCP server will need a chat-agent surface
beyond the current structured tools. Early thoughts:

- **Tools the chat agent will call most (from this Silver):**
  `get_task_breakdown` (Burnout + HMN context), `get_career_branches`
  (Stage 3 exploration queries).
- **Grounding context required in the system prompt:**
  - Stage 3 branches are similarity, not observed transitions.
  - Burnout is a modelled composite of 9 O*NET elements (name them explicitly
    after F-01 closes).
  - HMN is a ratio-based score (0.0–1.0 importance ratio mapped to 1–10) —
    say this so Gemma doesn't over-interpret small deltas.
- **Common user questions this Silver can answer:**
  - "Why is this career considered high-burnout?" → burnout_drivers JSON
  - "What makes this job distinctly human?" → top_human_activities JSON
  - "Where do people go from here?" → career_transitions filtered to
    Primary-Short
  - "Which of these related jobs has more growth?" → needs BLS OOH join, not
    O*NET alone
- **Eval-set design for gold→mcp:** should include a boss-fight Burnout eval
  specifically for SOCs where the substituted element is one of the top-3
  `burnout_drivers` — that's the thin-ice scenario and should have ≥ 5 test
  cases.

---

## 10. Priorities

**Before any new burnout-dependent gold work:**
1. Close F-01 (audit-trail entry for the burnout element substitution).
2. Close F-02 (glossary BT-059 alignment).
3. Reconcile the element-name drift between `onet_transformer.py:54` and
   `gold-onet-profiles.md:160`.

**Recommended gold spec order from here:**
1. Crosswalk CIP-SOC (already COMPLETE per CLAUDE.md) — prerequisite for
   everything cross-source.
2. `gold-futureproof-engine` (already COMPLETE) — the core 626K-row
   program×career product.
3. T2-01 `onet_activity_taxonomy` — cheap, high clarity for HMN.
4. T2-04 `onet_activity_signatures` — unlocks similarity-search UX.
5. T2-03 `onet_profile_narratives` — only after F-01/F-02 close, since the
   burnout narrative reads the glossary.
6. T2-02 `onet_burnout_taxonomy` — **gated on F-01**.

**Do NOT prioritise (Tier 3):**
- T3-01, T3-02, T3-04 require Bronze refactor or new Bronze ingest and do
  not fit within the hackathon window.

---

## 11. Verification Criteria (per recommendation)

- **T2-01 `onet_activity_taxonomy`:** DQ rule — row count = 41 exactly; every
  `element_id` joins to at least one row in `base.onet_activity_profiles`;
  `is_human_intensive` count matches the list in `gold-onet-profiles.md`.
  Failure shape: row count drift, or orphan element_id.
- **T2-02 `onet_burnout_taxonomy`:** DQ rule — row count = 9 exactly; every
  `element_id` has `is_burnout_element = True` in `base.onet_context_profiles`.
  Failure shape: count ≠ 9, or mismatched element lists between the taxonomy
  and the flagged column. **Blocked on F-01.**
- **T2-03 `onet_profile_narratives`:** DQ rule — 798 rows, all non-null
  `what_you_do`; 774 non-null `human_edge_summary` and `burnout_summary`;
  token length under budget. Failure shape: null narrative for a full-data
  SOC, or narrative over 1,024 tokens.
- **T2-04 `onet_activity_signatures`:** DQ rule — 774 rows (signatures only
  defined for full-data SOCs); every signature JSON has exactly 5 top and 5
  bottom elements. Failure shape: missing SOC, or malformed signature shape.

---

## 12. Open Items / Follow-ups

- F-01 through F-07 from the adversarial audit are open. Insight-manager
  work assumes they will be closed or deferred per the audit's recommended
  ordering.
- The three spec/data/glossary drifts on the burnout substitution are the
  only items in this report that directly affect user-facing copy; close
  them before the OpenRouter demo.
- This report is retroactive. The silver→gold pipeline-state gate can now
  complete for this spec.
