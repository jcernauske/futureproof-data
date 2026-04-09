# Spec: silver-base-onet

**Status:** COMPLETE
**Zone:** Silver
**Primary Agent:** @primary-agent
**Created:** 2026-04-08

## Problem Statement

Transform 5 raw O*NET Bronze tables into 4 clean, purpose-shaped Silver base tables. This is the most complex Silver transformation in the FutureProof pipeline — it consolidates 7 Bronze tables (5 present, 2 missing) into Silver tables shaped specifically for FutureProof's stat system, boss fights, and Stage 3 career branching.

The key Silver decisions: which Work Context elements map to Burnout, which Work Activity dimensions map to Human Edge, how to normalize O*NET-SOC codes for cross-source joining, and how to shape Related Occupations for the branching tree.

## Bronze Input (What We Have)

| Bronze Table | Rows | Status |
|-------------|------|--------|
| raw.onet_occupations | 1,016 | Present |
| raw.onet_task_statements | 18,796 | Present |
| raw.onet_work_activities | 73,308 | Present |
| raw.onet_work_context | 297,676 | Present |
| raw.onet_related_occupations | 18,460 | Present |
| raw.onet_career_changers | — | MISSING (file does not exist in O*NET 30.2) |
| raw.onet_career_starters | — | MISSING (file does not exist in O*NET 30.2) |

## Silver Output (What We Produce)

| # | Silver Table | Grain | Source | Est. Rows | FutureProof Use |
|---|-------------|-------|--------|-----------|-----------------|
| 1 | **base.onet_occupations** | bls_soc_code | raw.onet_occupations | ~867 | Master occupation reference at BLS granularity. Join key to BLS OOH and crosswalk. |
| 2 | **base.onet_activity_profiles** | bls_soc_code × element_id | raw.onet_work_activities | ~35,000 | HMN stat, AI boss fight. One row per occupation × activity, IM scale only (importance). |
| 3 | **base.onet_context_profiles** | bls_soc_code × element_id | raw.onet_work_context | ~49,000 | Burnout boss fight. CX scale only (point estimates). |
| 4 | **base.onet_career_transitions** | bls_soc_code × related_bls_soc_code | raw.onet_related_occupations | ~18,000 | Stage 3 branching tree. Career similarity graph. |

**Not produced in Silver (stays in Bronze for future use):**
- Task Statements — rich text data. Gemma consumes these directly from Bronze for narrative generation. Silver doesn't add value to free-text task descriptions. Task-level AI scoring happens in Gold.
- Work Activities LV (Level) scale — retained in Bronze. Silver uses IM (Importance) only for HMN stat. LV is available for post-hackathon enrichment.
- Work Context CXP/CTP (category percentages) — retained in Bronze. Silver uses CX/CT point estimates only. Distribution data available for post-hackathon Burnout depth.

## Technical Design

### Table 1: base.onet_occupations

The master O*NET occupation reference, aggregated to BLS SOC granularity (XX-XXXX).

**Why aggregate?** O*NET has 1,016 occupations at XX-XXXX.XX granularity. BLS OOH has 832 at XX-XXXX. FutureProof's join key is BLS SOC. Silver aggregates O*NET to BLS level so downstream joins are clean.

**Aggregation rules:**
- For .00 codes (867): direct 1:1 mapping, truncate suffix
- For non-.00 codes (149 codes across 76 BLS SOCs): group by 6-digit prefix, concatenate titles/descriptions, flag as multi-detail
- Exclude the 93 "All Other"/Military occupations with no data in any child table (they are structurally empty)

**Grain:** bls_soc_code (one row per BLS-level occupation)

**Schema:**

| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| record_id | string | derived | yes | `compute_grain_id(row, ['bls_soc_code'], prefix='on')` |
| bls_soc_code | string | derived | yes | 6-digit BLS SOC code (XX-XXXX), truncated from O*NET-SOC |
| primary_title | string | raw.onet_occupations | yes | Title of the .00 base code, or first detailed code if no .00 exists |
| description | string | raw.onet_occupations | yes | Description of the .00 base code |
| onet_detail_codes | string | derived | yes | JSON array of all O*NET-SOC codes that map to this BLS SOC (e.g., `["15-1252.00"]` or `["29-1229.01","29-1229.02","29-1229.03"]`) |
| onet_detail_count | int | derived | yes | Number of O*NET detailed codes (1 for simple, 2+ for splits) |
| multi_detail_flag | boolean | derived | yes | True when onet_detail_count > 1 (76 BLS SOCs) |
| has_work_activities | boolean | derived | yes | True if ANY O*NET detail code for this BLS SOC has Work Activities data |
| has_work_context | boolean | derived | yes | True if ANY O*NET detail code has Work Context data |
| has_tasks | boolean | derived | yes | True if ANY O*NET detail code has Task Statements |
| has_related | boolean | derived | yes | True if ANY O*NET detail code has Related Occupations |
| data_completeness_tier | string | derived | yes | "full" (all 4 present), "partial" (some present), "none" (no child data) |
| source_load_date | date | raw.onet_occupations | yes | |
| ingested_at | timestamp | generated | yes | |

**Row count:** ~867 (1,016 minus 93 "All Other"/Military minus duplicates from multi-detail aggregation, plus any .00-only codes = ~867 unique BLS SOCs with data)

**Filtering:** Exclude occupations where data_completeness_tier = "none" (the 93 structurally empty occupations). They exist in Bronze for lineage; Silver only carries occupations with actual data.

Wait — on reflection, keep all 867 derivable BLS SOCs including those with partial data. The 93 "All Other"/Military codes should be excluded because they have zero data AND their BLS SOC codes overlap with the catchall codes already flagged in BLS OOH Silver. The 29 partial-data occupations stay in — they have useful task and relationship data.

### Table 2: base.onet_activity_profiles

Work Activity importance ratings per occupation, at BLS SOC granularity. This backs the **HMN stat** (Human Edge).

**Why IM scale only?** FutureProof needs to know "how important is this human activity for this job?" (IM = importance, 1-5). The LV (level/complexity, 0-7) scale is interesting but not needed for HMN scoring. Keeping IM only cuts the data in half and simplifies scoring.

**Aggregation for multi-detail codes:** When multiple O*NET detailed codes map to one BLS SOC, average the IM data_value across details (unweighted — employment weights aren't available).

**Grain:** bls_soc_code × element_id

**Schema:**

| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| record_id | string | derived | yes | `compute_grain_id(row, ['bls_soc_code', 'element_id'], prefix='wa')` |
| bls_soc_code | string | derived | yes | 6-digit BLS SOC code |
| element_id | string | raw.onet_work_activities | yes | Content Model element ID (e.g., "4.A.1.a.1") |
| element_name | string | raw.onet_work_activities | yes | Activity name (e.g., "Getting Information") |
| importance | double | raw.onet_work_activities | yes | IM scale data_value, averaged across O*NET details if multi-detail. Range 1.0–5.0. |
| importance_rank | int | derived | yes | Rank of this activity within the occupation (1 = most important, 41 = least) |
| is_high_importance | boolean | derived | yes | True if importance >= 3.5 (top ~40% of the 1-5 scale) |
| onet_details_averaged | int | derived | yes | How many O*NET detail codes contributed to this importance value (1 for most, 2+ for multi-detail) |
| suppress_flag | boolean | derived | yes | True if recommend_suppress = "Y" in ANY contributing Bronze row. Signals unreliable data. |
| source_load_date | date | raw.onet_work_activities | yes | |
| ingested_at | timestamp | generated | yes | |

**Filtering:**
- IM scale only (exclude LV rows)
- Exclude occupations not in base.onet_occupations (the 93 structurally empty ones)
- Preserve recommend_suppress = "Y" rows but flag them — don't drop

**Row count:** ~894 occupations (with data) × 41 activities = ~36,654 rows. After aggregation to BLS level: ~867 × 41 = ~35,547.

### Table 3: base.onet_context_profiles

Work Context point estimates per occupation, at BLS SOC granularity. This backs the **Burnout boss fight**.

**Why CX/CT only?** CXP/CTP category-percentage rows represent 81% of Work Context data but add distributional detail not needed for the MVP Burnout score. CX gives a single scalar per element per occupation — sufficient for scoring. CXP stays in Bronze.

**Burnout-Relevant Elements (proposed):**

These Work Context elements directly signal burnout risk. The Burnout boss fight formula should weight these most heavily:

| Element ID | Element Name | Burnout Signal | Scale |
|-----------|-------------|----------------|-------|
| 4.C.3.d.1 | Time Pressure | Higher = more deadline stress | CX (1-5) |
| 4.C.3.d.8 | Duration of Typical Work Week | Higher = longer hours | CT (1-3, where 3 = ">40 hours") |
| 4.C.3.a.1 | Consequence of Error | Higher = more stress from mistakes | CX (1-5) |
| 4.C.3.d.3 | Pace Determined by Speed of Equipment | Higher = less autonomy over pace | CX (1-5) |
| 4.C.3.b.2 | Frequency of Decision Making | Higher = cognitive load | CX (1-5) |
| 4.C.3.d.4 | Importance of Being Exact or Accurate | Higher = precision pressure | CX (1-5) |
| 4.C.3.d.5 | Importance of Repeating Same Tasks | Higher = monotony (burnout via boredom) | CX (1-5) |
| 4.C.3.b.7 | Responsibility for Outcomes and Results | Higher = pressure | CX (1-5) |
| 4.C.3.d.7 | Work Schedules | Irregular/Seasonal = schedule disruption | CT (1-3) |

**Note:** The exact element IDs need to be confirmed against the actual Bronze data. The EDA shows 57 distinct elements. The IDs above are from O*NET Content Model documentation and may have minor format differences in the actual data. The agent should validate these IDs during implementation.

**Aggregation for multi-detail codes:** Average CX/CT data_value across O*NET details (same approach as Work Activities).

**Grain:** bls_soc_code × element_id

**Schema:**

| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| record_id | string | derived | yes | `compute_grain_id(row, ['bls_soc_code', 'element_id'], prefix='wc')` |
| bls_soc_code | string | derived | yes | 6-digit BLS SOC code |
| element_id | string | raw.onet_work_context | yes | Content Model element ID |
| element_name | string | raw.onet_work_context | yes | Context dimension name |
| scale_id | string | raw.onet_work_context | yes | "CX" or "CT" (point estimate scales only) |
| context_value | double | raw.onet_work_context | yes | CX scale 1.0–5.0, CT scale 1.0–3.0. Averaged across details if multi-detail. |
| is_burnout_element | boolean | derived | yes | True for the ~9 burnout-relevant elements listed above |
| onet_details_averaged | int | derived | yes | How many O*NET detail codes contributed |
| suppress_flag | boolean | derived | yes | True if recommend_suppress = "Y" in ANY contributing row |
| source_load_date | date | raw.onet_work_context | yes | |
| ingested_at | timestamp | generated | yes | |

**Filtering:**
- CX and CT scales only (exclude CXP, CTP rows — drops ~82% of Work Context data)
- Exclude 93 structurally empty occupations
- Preserve suppress_flag rows

**Row count:** ~894 occupations × 57 elements = ~50,958 CX/CT rows. After aggregation to BLS level: ~867 × 57 = ~49,419.

### Table 4: base.onet_career_transitions

Career similarity graph for Stage 3 branching. Each row is a directional relationship: "from this occupation, these are the most similar careers."

**Source:** Related Occupations (the only career relationship data available — Career Changers/Starters matrices don't exist in O*NET 30.2).

**Important caveat:** Related Occupations measures occupational **similarity**, not actual career **transitions**. "Software Developer relates to Database Architect" doesn't mean software developers commonly become database architects. It means the jobs share similar skills/knowledge profiles. This is a weaker signal than actual transition data would be, but it's what we have. The PRD acknowledges this — Stage 3 branches are framed as "paths people in this role commonly take" with disclaimers that they're modeled, not observed.

**Aggregation to BLS level:** Both source and related O*NET-SOC codes truncated to 6-digit. If multiple O*NET details for the same BLS SOC relate to the same target BLS SOC, take the best (lowest) index.

**Grain:** bls_soc_code × related_bls_soc_code

**Schema:**

| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| record_id | string | derived | yes | `compute_grain_id(row, ['bls_soc_code', 'related_bls_soc_code'], prefix='ct')` |
| bls_soc_code | string | derived | yes | Source occupation (6-digit BLS SOC) |
| related_bls_soc_code | string | derived | yes | Related occupation (6-digit BLS SOC) |
| best_index | int | raw.onet_related_occupations | yes | Best (lowest) index across any O*NET detail pairings. 1-20. |
| relatedness_tier | string | raw.onet_related_occupations | yes | "Primary-Short" (index 1-5), "Primary-Long" (index 6-10), "Supplemental" (index 11-20). Uses tier of best_index row. |
| is_primary | boolean | derived | yes | True when relatedness_tier is "Primary-Short" or "Primary-Long" |
| relationship_type | string | static | yes | Always "similarity" for this source. Post-hackathon, if transition data becomes available, this field distinguishes "similarity" from "transition". |
| source_load_date | date | raw.onet_related_occupations | yes | |
| ingested_at | timestamp | generated | yes | |

**Filtering:**
- Exclude self-references (bls_soc_code = related_bls_soc_code) — these can emerge during BLS-level aggregation if two O*NET details of the same BLS SOC relate to each other
- Exclude relationships where either SOC is in the 93 structurally empty set
- Deduplicate after BLS-level aggregation (same BLS pair from multiple O*NET detail pairings → keep best index)

**Row count:** ~18,460 raw rows. After BLS aggregation, dedup, and self-reference removal: estimate ~16,000–18,000.

## SOC Code Normalization

All Silver tables use `bls_soc_code` (XX-XXXX, 6-digit) as the primary identifier, derived by truncating O*NET-SOC codes:

```
O*NET: "15-1252.00" → BLS: "15-1252"
O*NET: "29-1229.01" → BLS: "29-1229"
```

The full O*NET-SOC codes are preserved in `base.onet_occupations.onet_detail_codes` (JSON array) for lineage and O*NET-internal analysis.

**Cross-source join compatibility:**
- `base.onet_occupations.bls_soc_code` joins to `base.bls_ooh.soc_code`
- `base.onet_career_transitions.bls_soc_code` joins to `base.bls_ooh.soc_code`
- CIP→SOC crosswalk (separate spec) bridges `base.college_scorecard.cipcode` to these SOC codes

## Answers to EDA Open Questions

The Bronze EDA flagged 6 unanswered questions. Here are the Silver spec's answers:

1. **Career Changers/Starters → Use Related Occupations as fallback.** Confirmed. base.onet_career_transitions uses Related Occupations with relatedness_tier. The `relationship_type = "similarity"` field documents this is similarity data, not transition data.

2. **Work Context CXP usage → CX point estimates only for MVP.** Confirmed. Silver uses CX/CT only. CXP/CTP retained in Bronze for post-hackathon depth.

3. **Survey freshness threshold → Not enforced in Silver.** Survey dates are metadata, not a quality filter. Gold zone can add a freshness indicator if needed. Silver carries all data regardless of age.

4. **29 partial-data occupations → Include with flags.** base.onet_occupations has has_work_activities, has_work_context, has_tasks, has_related flags and data_completeness_tier. Partial occupations are visible, not hidden.

5. **Relatedness Tier → Capture three-tier column AND derive is_primary.** Confirmed. base.onet_career_transitions has both relatedness_tier (three values) and is_primary (boolean).

6. **AI scoring methodology → Outside Silver scope.** Task-level AI scoring happens in Gold. Silver preserves task text and activity importance ratings at full fidelity for downstream consumption.

## Success Criteria

- [ ] All 4 Silver tables exist with correct schemas
- [ ] All tables use bls_soc_code (XX-XXXX) as primary identifier
- [ ] Multi-detail O*NET codes correctly aggregated (76 BLS SOCs with 2+ O*NET details)
- [ ] 93 "All Other"/Military occupations excluded from Silver
- [ ] Work Activities filtered to IM scale only
- [ ] Work Context filtered to CX/CT scales only (~82% of Bronze rows correctly excluded)
- [ ] Burnout-relevant elements flagged via is_burnout_element
- [ ] Career transitions deduplicated at BLS level with best_index preserved
- [ ] Self-references removed from career transitions
- [ ] Grain integrity enforced on all 4 tables (zero duplicates)
- [ ] Idempotent promote pattern on all 4 tables
- [ ] DQ rules written, executed, and passing
- [ ] Data contracts produced for all 4 tables

## Agent Workflow

1. @governance-reviewer — Pre-implementation review
2. @data-steward — Identify business terms from spec
3. @semantic-modeler — Propose conceptual model → HUMAN APPROVAL GATE
4. @semantic-modeler — Propose logical model → HUMAN APPROVAL GATE
5. @semantic-modeler — Generate physical model from approved logical
6. @data-analyst — EDA on Bronze data (profile for Silver thresholds — can reuse Bronze EDA findings)
7. @dq-rule-writer — Write Silver DQ rules from EDA + logical model
8. @primary-agent — Implement transformers (4 tables, can be 1 or 4 modules)
9. @dq-engineer — Execute rules, produce scorecard
10. @chaos-monkey — 5-cycle adversarial hardening
11. @lineage-tracker — OpenLineage capture
12. @cde-tagger — CDE mapping update
13. @doc-generator — Dictionary + contracts update
14. @governance-reviewer — Post-implementation check
15. @staff-engineer — Final quality review

## Conditionally Skippable Agents

| Agent | Decision | Justification |
|-------|----------|---------------|
| @entity-resolver | SKIP | O*NET-to-BLS SOC mapping is a deterministic truncation, not fuzzy matching. Multi-detail aggregation is a known 1:N relationship (76 cases). |
| @pii-scanner | SKIP | Aggregated occupation-level data from anonymized federal surveys. No individual data. |
| @temporal-modeler | SKIP | Single-snapshot. Full table replace on O*NET release updates. |
| @adversarial-auditor | RUN | First multi-source Silver transformation. BLS-level aggregation, burnout element flagging, and career transition dedup all need adversarial testing. |

## DQ Rules

Expected areas of focus:

**base.onet_occupations:**
- bls_soc_code format: 100% valid XX-XXXX
- bls_soc_code uniqueness: zero duplicates
- Excluded "All Other"/Military count: ~93 fewer than Bronze
- multi_detail_flag: exactly 76 True values
- data_completeness_tier distribution: expect majority "full", ~29 "partial", 0 "none" (none are excluded)

**base.onet_activity_profiles:**
- Grain uniqueness: bls_soc_code × element_id = zero duplicates
- importance range: 1.0–5.0
- Exactly 41 distinct element_ids
- importance_rank: 1–41 per occupation, no gaps
- Rows per occupation: exactly 41
- suppress_flag distribution: < 3% True

**base.onet_context_profiles:**
- Grain uniqueness: bls_soc_code × element_id = zero duplicates
- CX context_value range: 1.0–5.0
- CT context_value range: 1.0–3.0
- Exactly 57 distinct element_ids
- is_burnout_element: exactly 9 True element_ids (confirm count after implementation)
- Row count much smaller than Bronze (~49K vs 298K — CXP/CTP rows excluded)

**base.onet_career_transitions:**
- Grain uniqueness: bls_soc_code × related_bls_soc_code = zero duplicates
- No self-references
- best_index range: 1–20
- relatedness_tier values: exactly {"Primary-Short", "Primary-Long", "Supplemental"}
- is_primary consistency: True ↔ tier is Primary-Short or Primary-Long
- Both SOC codes must be valid XX-XXXX format

**Cross-table referential integrity:**
- All bls_soc_codes in activity_profiles exist in onet_occupations
- All bls_soc_codes in context_profiles exist in onet_occupations
- All bls_soc_codes in career_transitions (both columns) exist in onet_occupations

## Open Decisions for Human Approval

1. **Burnout element selection** — the 9 elements listed above are proposed. Confirm or adjust. Adding/removing elements changes the is_burnout_element flag and downstream Burnout boss fight formula.

2. **Multi-detail aggregation strategy** — unweighted average is proposed. Employment-weighted would be more accurate but requires BLS employment data mapped to O*NET detail codes (not readily available). Confirm unweighted average is acceptable for hackathon.

3. **Task Statements staying in Bronze** — Silver doesn't transform task text. Gemma reads task descriptions directly from Bronze for narrative generation. Gold handles task-level AI scoring. Confirm this is acceptable or if you want a Silver task table.

4. **Excluding 93 "All Other"/Military occupations from Silver** — these have zero O*NET data. BLS OOH Silver already flags them as catchall/broad. Confirm exclusion is acceptable.

## Governance Artifacts

- [ ] Business glossary: `governance/business-glossary.json` (O*NET Silver terms)
- [ ] Conceptual model: `governance/models/silver-base-onet-conceptual.md`
- [ ] Logical model: `governance/models/silver-base-onet-logical.md`
- [ ] Physical model: `governance/models/silver-base-onet-physical.md`
- [ ] EDA report: `governance/eda/silver-onet-eda.md`
- [ ] DQ rules: `governance/dq-rules/silver-base-onet.json`
- [ ] DQ scorecard: `governance/dq-scorecards/silver-base-onet-scorecard.md`
- [ ] Chaos manifest: `governance/chaos-manifests/silver-base-onet-chaos.md`
- [ ] Lineage: `governance/lineage/silver-base-onet-{timestamp}.json`
- [ ] Data contracts: `governance/data-contracts/base-onet-occupations.yaml`, `base-onet-activity-profiles.yaml`, `base-onet-context-profiles.yaml`, `base-onet-career-transitions.yaml`
- [ ] Staff review: `governance/reviews/silver-base-onet-staff-review.md`

## Future Integration Notes

With this Silver spec complete, the full Silver landscape is:

1. **base.college_scorecard** — COMPLETE (69,947 rows, CIP codes)
2. **base.bls_ooh** — COMPLETE (832 rows, SOC codes)
3. **base.onet_occupations** — THIS SPEC (~867 rows, BLS SOC codes)
4. **base.onet_activity_profiles** — THIS SPEC (~35,500 rows, BLS SOC × element)
5. **base.onet_context_profiles** — THIS SPEC (~49,400 rows, BLS SOC × element)
6. **base.onet_career_transitions** — THIS SPEC (~17,000 rows, BLS SOC × BLS SOC)
7. **CIP→SOC crosswalk** — NEXT SPEC (bridges table 1 to tables 2-6)

After this spec and the crosswalk, Gold can produce the unified career data product that powers FutureProof's full loop: school + major → occupations → stats → boss fights → branches.
