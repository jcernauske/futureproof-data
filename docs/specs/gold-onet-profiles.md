# Spec: gold-onet-profiles

**Status:** COMPLETE
**Zone:** Gold
**Primary Agent:** @primary-agent
**Created:** 2026-04-08

## Problem Statement

Build two consumable Gold data products from O*NET Silver tables: an **occupation work profile** (HMN score, Burnout score, activity summaries, context summaries) and a **career transition graph** (Stage 3 branching data). These are the third and fourth Gold data products in FutureProof, completing the occupation-level data needed for the full five-stat pentagon and all boss fights.

## What This Gold Spec Produces

| # | Gold Table | Grain | Source | FutureProof Use |
|---|-----------|-------|--------|-----------------|
| 1 | **consumable.onet_work_profiles** | bls_soc_code | base.onet_occupations + base.onet_activity_profiles + base.onet_context_profiles | HMN score, Burnout score, AI boss context, Gemma career descriptions |
| 2 | **consumable.career_transitions** | bls_soc_code × related_bls_soc_code | base.onet_career_transitions + base.onet_occupations | Stage 3 branching tree |

## Source Data (from Silver)

| Silver Table | Rows | Key Content |
|-------------|------|-------------|
| base.onet_occupations | 798 | Master O*NET occupation reference at BLS granularity |
| base.onet_activity_profiles | 31,734 | 774 SOCs × 41 work activities (IM importance only) |
| base.onet_context_profiles | 44,118 | 774 SOCs × 57 context elements (CX/CT point estimates) |
| base.onet_career_transitions | 15,944 | Career similarity graph |

## Technical Design

### Table 1: consumable.onet_work_profiles

One row per occupation. Pivots the activity and context profile data from Silver (many rows per occupation) into a single occupation-level record with derived scores.

**Why pivot?** Silver has 41 activity rows and 57 context rows per occupation. Gold consumers (Gemma, the frontend, the stat engine) need one row per occupation with pre-computed scores, not raw rating tables. The pivot aggregates the profiles into occupation-level metrics.

**Grain:** bls_soc_code (one row per occupation with work data)

**Schema:**

#### Identity (carried from Silver)
| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| record_id | string | derived | yes | `compute_grain_id(row, ['bls_soc_code'], prefix='wp')` |
| bls_soc_code | string | base.onet_occupations | yes | 6-digit BLS SOC. Join key to consumable.occupation_profiles. |
| primary_title | string | base.onet_occupations | yes | Occupation title |
| description | string | base.onet_occupations | yes | Occupation description |
| multi_detail_flag | boolean | base.onet_occupations | yes | True for 76 BLS SOCs with multiple O*NET details |
| data_completeness_tier | string | base.onet_occupations | yes | "full" or "partial" |

#### HMN Score (Human Edge)
| Field | Type | Derivation | Required | Notes |
|-------|------|-----------|----------|-------|
| hmn_score | double | See derivation below | no | Human Edge stat on 1–10 scale. Null for partial-data occupations without activity profiles. |
| hmn_score_rounded | int | ROUND(hmn_score) | no | Integer 1–10 for pentagon display |
| top_human_activities | string | JSON array | no | Top 5 work activities by importance that are classified as "human-intensive". Powers Gemma's "what the human edge looks like" narrative. |
| human_activity_count | int | derived | no | How many of the 41 activities are classified as human-intensive for this occupation |

#### Burnout Score
| Field | Type | Derivation | Required | Notes |
|-------|------|-----------|----------|-------|
| burnout_score | double | See derivation below | no | Burnout risk on 1–10 scale. Higher = more burnout risk. Null for partial-data occupations without context profiles. |
| burnout_score_rounded | int | ROUND(burnout_score) | no | Integer 1–10 for boss fight |
| burnout_drivers | string | JSON array | no | Top 3 burnout-contributing Work Context elements with their values. Powers Gemma's burnout narrative. |
| time_pressure | double | CX value for element 4.C.3.d.1 | no | Individual burnout element — Time Pressure (1-5). Direct from Silver. |
| work_hours | double | CT value for element 4.C.3.d.8 | no | Duration of Typical Work Week (1-3, where 3 = ">40 hrs"). Direct from Silver. |
| consequence_of_error | double | CX value for element 4.C.3.a.1 | no | Consequence of Error (1-5). Direct from Silver. |

#### Activity Profile Summary
| Field | Type | Derivation | Required | Notes |
|-------|------|-----------|----------|-------|
| activity_importance_mean | double | Mean of all 41 IM values | no | Overall "how many things does this job involve at high importance?" |
| top_5_activities | string | JSON array | no | Top 5 activities by importance rank (name + importance value). Powers Gemma descriptions. |
| activity_profile_available | boolean | derived | yes | True if base.onet_activity_profiles has rows for this SOC |

#### Context Profile Summary
| Field | Type | Derivation | Required | Notes |
|-------|------|-----------|----------|-------|
| context_profile_available | boolean | derived | yes | True if base.onet_context_profiles has rows for this SOC |

#### Data Quality
| Field | Type | Derivation | Required | Notes |
|-------|------|-----------|----------|-------|
| confidence_tier | string | See derivation below | yes | "high", "medium", "low" |
| suppress_pct_activities | double | derived | no | Percentage of activity profile rows with suppress_flag = True |
| suppress_pct_context | double | derived | no | Percentage of context profile rows with suppress_flag = True |

#### FutureProof Mapping
| Field | Type | Derivation | Required | Notes |
|-------|------|-----------|----------|-------|
| backs_stats | string | static | yes | "HMN" for all rows |
| backs_bosses | string | static | yes | "AI,Burnout" for all rows |

#### Metadata
| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| source_load_date | date | base.onet_occupations | yes | |
| promoted_at | timestamp | generated | yes | |

### HMN Score Derivation (1–10 Scale)

The Human Edge stat measures how much an occupation depends on distinctly human skills — things AI struggles with: interpersonal judgment, creative problem-solving, physical presence, emotional intelligence, leadership.

**Step 1: Classify the 41 work activities into "human-intensive" vs. "automatable".**

Activities are classified based on their nature. This classification is static — the same for all occupations:

**Human-intensive activities** (activities that require judgment, creativity, interpersonal skill, or physical presence — hard for AI to replicate):

| Element ID | Activity Name | Why Human |
|-----------|--------------|-----------|
| 4.A.4.a.1 | Guiding, Directing, and Motivating Subordinates | Leadership, interpersonal |
| 4.A.4.a.2 | Coaching and Developing Others | Mentorship, emotional intelligence |
| 4.A.4.a.4 | Resolving Conflicts and Negotiating with Others | Judgment, empathy |
| 4.A.4.a.5 | Performing for or Working Directly with the Public | Physical presence, social |
| 4.A.4.a.8 | Establishing and Maintaining Interpersonal Relationships | Relationship building |
| 4.A.4.b.4 | Developing and Building Teams | Leadership |
| 4.A.4.b.5 | Training and Teaching Others | Interpersonal, adaptive |
| 4.A.4.b.6 | Selling or Influencing Others | Persuasion, social intelligence |
| 4.A.4.a.1 | Coordinating the Work and Activities of Others | Coordination, judgment |
| 4.A.2.b.2 | Thinking Creatively | Creativity |
| 4.A.2.b.4 | Making Decisions and Solving Problems | Judgment |
| 4.A.1.e.2 | Performing General Physical Activities | Physical presence |
| 4.A.3.a.3 | Handling and Moving Objects | Physical |
| 4.A.3.b.5 | Assisting and Caring for Others | Empathy, physical |

**Note:** The exact element IDs and classification need to be validated against the actual Silver activity data. The agent should extract the full list of 41 element_ids from `base.onet_activity_profiles` and confirm the classification. Some IDs above may be incorrect — use the element_name field to identify the correct IDs.

**Step 2: Compute HMN score.**

For each occupation:
1. Get the importance values (IM, 1-5) for all 41 activities
2. Compute `human_importance_sum` = sum of importance values for the human-intensive activities
3. Compute `total_importance_sum` = sum of importance values for ALL activities
4. Compute `human_ratio` = human_importance_sum / total_importance_sum (0.0–1.0)
5. Map to 1–10 scale: `hmn_score = 1.0 + 9.0 * human_ratio`

This gives a score where:
- HMN 10.0 = all of the occupation's important activities are human-intensive
- HMN 5.5 = roughly equal human and automatable importance
- HMN 1.0 = all important activities are automatable

Null if the occupation has no activity profile data.

### Burnout Score Derivation (1–10 Scale)

Combines the 9 burnout-relevant Work Context elements into a single burnout risk score.

**The 9 burnout elements** (confirmed in Silver DQ rule SLV-ONET-024):

| Element ID | Element Name | Scale | Range | Burnout Direction |
|-----------|-------------|-------|-------|-------------------|
| 4.C.3.d.1 | Time Pressure | CX | 1-5 | Higher = more stress |
| 4.C.3.d.8 | Duration of Typical Work Week | CT | 1-3 | Higher = longer hours |
| 4.C.3.a.1 | Consequence of Error | CX | 1-5 | Higher = more pressure |
| 4.C.3.d.3 | Pace Determined by Speed of Equipment | CX | 1-5 | Higher = less autonomy |
| 4.C.3.a.2.b | Frequency of Decision Making | CX | 1-5 | Higher = cognitive load |
| 4.C.3.b.4 | Importance of Being Exact or Accurate | CX | 1-5 | Higher = precision pressure |
| 4.C.3.b.7 | Responsibility for Outcomes and Results | CX | 1-5 | Higher = stakes pressure |
| 4.C.3.d.4 | Importance of Repeating Same Tasks | CX | 1-5 | Higher = monotony |
| 4.C.3.a.2.a | Responsibility for Others' Health and Safety | CX | 1-5 | Higher = stakes pressure |

**Note:** Element IDs 4.C.3.a.2.a (Responsibility for Others' Health and Safety) and 4.C.3.a.2.b (Frequency of Decision Making) replaced the originally proposed elements from the Silver spec. The EDA-corrected IDs are confirmed by SLV-ONET-024.

**Computation:**
1. For each occupation, retrieve the context_value for all 9 burnout elements
2. Normalize each to a 0-1 scale:
   - CX elements (1-5): `normalized = (value - 1.0) / 4.0`
   - CT elements (1-3): `normalized = (value - 1.0) / 2.0`
3. Compute weighted average: all 9 elements weighted equally (unweighted average of normalized values)
4. Map to 1-10 scale: `burnout_score = 1.0 + 9.0 * weighted_average`

This gives:
- Burnout 10.0 = maximum on all burnout indicators
- Burnout 5.5 = moderate burnout risk across indicators
- Burnout 1.0 = minimum burnout risk

Null if the occupation has no context profile data.

### Confidence Tier Derivation

| Tier | Criteria |
|------|----------|
| high | data_completeness_tier = "full" AND suppress_pct_activities < 5% AND suppress_pct_context < 5% |
| medium | data_completeness_tier = "full" AND (suppress_pct_activities >= 5% OR suppress_pct_context >= 5%) |
| low | data_completeness_tier = "partial" |

### Transformations (Table 1)

1. **Read all 3 Silver tables** into DuckDB
2. **Pivot activity profiles:** For each bls_soc_code, aggregate 41 activity rows into: activity_importance_mean, top_5_activities (JSON), human_ratio → hmn_score
3. **Classify activities** as human-intensive vs. automatable. Count human_activity_count. Build top_human_activities JSON.
4. **Pivot context profiles:** For each bls_soc_code, extract the 9 burnout elements → normalize → burnout_score. Extract individual values for time_pressure, work_hours, consequence_of_error. Build burnout_drivers JSON (top 3).
5. **Join to occupations** for title, description, flags
6. **Compute confidence tier** from completeness + suppress percentages
7. **Set static fields** (backs_stats, backs_bosses)
8. **Compute record_id** and promote

**Row count:** 798 (one per occupation in base.onet_occupations). Of these, 774 will have full scores (both activity + context data). 24 will have partial data (HMN and/or Burnout may be null).

### Transformer

- **Module:** `src/gold/onet_work_profiles.py`
- **Function:** `transform()`
- **Pattern:** Read 3 Silver tables, pivot/aggregate, promote to `consumable.onet_work_profiles`

---

### Table 2: consumable.career_transitions

Career similarity graph for Stage 3 branching. Enriched with occupation titles from Silver and BLS OOH growth data for "where is this related career headed?"

**Grain:** bls_soc_code × related_bls_soc_code

**Schema:**

| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| record_id | string | derived | yes | `compute_grain_id(row, ['bls_soc_code', 'related_bls_soc_code'], prefix='tr')` |
| bls_soc_code | string | base.onet_career_transitions | yes | Source occupation |
| source_title | string | base.onet_occupations | yes | Source occupation title |
| related_bls_soc_code | string | base.onet_career_transitions | yes | Related occupation |
| related_title | string | base.onet_occupations | yes | Related occupation title |
| best_index | int | base.onet_career_transitions | yes | Similarity rank (1 = most similar) |
| relatedness_tier | string | base.onet_career_transitions | yes | Primary-Short / Primary-Long / Supplemental |
| is_primary | boolean | base.onet_career_transitions | yes | True for Primary-Short or Primary-Long |
| relationship_type | string | base.onet_career_transitions | yes | "similarity" |
| source_has_work_profile | boolean | derived | yes | True if source SOC exists in consumable.onet_work_profiles with full data |
| related_has_work_profile | boolean | derived | yes | True if related SOC exists in consumable.onet_work_profiles with full data |
| backs_feature | string | static | yes | "Stage3Branching" for all rows |
| source_load_date | date | base.onet_career_transitions | yes | |
| promoted_at | timestamp | generated | yes | |

**Row count:** 15,944 (carried from Silver, enriched with titles and flags)

### Transformations (Table 2)

1. **Read career transitions from Silver**
2. **Join source occupation** title from base.onet_occupations
3. **Join related occupation** title from base.onet_occupations
4. **Flag work profile availability** by checking if each SOC exists in the onet_work_profiles result set
5. **Set static fields** (backs_feature)
6. **Compute record_id** and promote

### Transformer

- **Module:** `src/gold/onet_career_transitions.py`
- **Function:** `transform()`
- **Pattern:** Read Silver + Gold work profiles, enrich, promote to `consumable.career_transitions`

**Note:** Table 2 depends on Table 1 being built first (it checks `consumable.onet_work_profiles` for the has_work_profile flags). Build order: work_profiles first, career_transitions second.

---

## Success Criteria

- [ ] Both Gold tables exist with correct schemas
- [ ] HMN score computed on 1–10 scale for all occupations with activity data (774)
- [ ] Burnout score computed on 1–10 scale for all occupations with context data (774)
- [ ] top_human_activities and burnout_drivers JSON arrays populated
- [ ] Individual burnout element values (time_pressure, work_hours, consequence_of_error) extracted
- [ ] Career transitions enriched with titles and work profile flags
- [ ] Confidence tiers assigned to all work profile rows
- [ ] Grain integrity on both tables
- [ ] DQ rules written, executed, and passing
- [ ] Golden dataset with verifiable derivation chains
- [ ] Data contracts produced for both tables

## Agent Workflow

1. @governance-reviewer — Pre-implementation review
2. @data-steward — Identify business terms
3. @semantic-modeler — Conceptual model → HUMAN APPROVAL GATE
4. @semantic-modeler — Logical model → HUMAN APPROVAL GATE
5. @semantic-modeler — Physical model
6. @data-analyst — EDA on Silver data (validate score distributions)
7. @dq-rule-writer — Gold DQ rules
8. @primary-agent — Implement 2 transformers (work_profiles first, career_transitions second)
9. @dq-engineer — Execute rules, produce scorecard
10. @chaos-monkey — 5-cycle hardening
11. @lineage-tracker — OpenLineage capture
12. @cde-tagger — CDE mapping
13. @doc-generator — Dictionary + contracts
14. @governance-reviewer — Post-implementation check
15. @staff-engineer — Final review

## Conditionally Skippable Agents

| Agent | Decision | Justification |
|-------|----------|---------------|
| @entity-resolver | SKIP | Single-source Gold product at BLS SOC granularity. |
| @pii-scanner | SKIP | Aggregated occupation-level data. |
| @temporal-modeler | SKIP | Single-snapshot. Full table replace. |
| @adversarial-auditor | RUN | HMN and Burnout score formulas need adversarial testing — these directly produce FutureProof stat values. Activity classification (human-intensive vs. automatable) is a subjective judgment that needs scrutiny. |

## DQ Rules

Expected areas of focus:

**consumable.onet_work_profiles:**
- hmn_score range: 1.0–10.0 when non-null
- burnout_score range: 1.0–10.0 when non-null
- hmn_score null count: 24 (partial-data occupations without activity profiles)
- burnout_score null count: 24 (same set)
- Scores should have meaningful spread (std dev > 1.0 for both)
- top_human_activities and burnout_drivers must be valid JSON arrays
- time_pressure, work_hours, consequence_of_error within expected ranges
- confidence_tier distribution: expect majority "high"
- Row count: exactly 798

**consumable.career_transitions:**
- Grain uniqueness: bls_soc_code × related_bls_soc_code = 0 duplicates
- No self-references
- Row count: exactly 15,944
- All titles non-null (join succeeded)
- backs_feature = "Stage3Branching" for all rows

## Golden Dataset

**Work Profiles:**
1. **Software Developers (15-1252)** — should have high HMN (creative problem-solving, team coordination) and moderate Burnout (time pressure but good work-life). Verify score derivation chain.
2. **Registered Nurses (29-1141)** — should have high HMN (caring for others, interpersonal) and high Burnout (consequence of error, hours, time pressure). Verify burnout_drivers includes relevant elements.
3. **A low-HMN occupation** (e.g., from Production or Office/Admin group) — verify human_ratio is low, HMN score reflects that.

**Career Transitions:**
4. **Software Developers → related occupations** — verify titles populated, relatedness_tier correct, has_work_profile flags accurate.

## Open Decisions for Human Approval

1. **Human-intensive activity classification** — the list of ~14 activities above is proposed. The adversarial auditor should challenge which activities are truly "human-intensive" vs. "automatable by AI." This is the most subjective decision in the entire data pipeline and directly determines the HMN stat. Confirm or adjust.

2. **Burnout weighting** — all 9 elements weighted equally is proposed. An alternative: weight Time Pressure and Work Hours higher than monotony indicators. Equal weighting is simpler and more defensible. Confirm.

3. **HMN formula using importance ratio** — the proposed formula computes what fraction of an occupation's important work is human-intensive. An alternative: use absolute importance values (occupations where human activities are rated highly, regardless of other activities). Ratio approach is better because it normalizes across occupations with different overall activity intensity. Confirm.

## Governance Artifacts

- [ ] Business glossary: `governance/business-glossary.json`
- [ ] Conceptual model: `governance/models/gold-onet-profiles-conceptual.md`
- [ ] Logical model: `governance/models/gold-onet-profiles-logical.md`
- [ ] Physical model: `governance/models/gold-onet-profiles-physical.md`
- [ ] EDA report: `governance/eda/gold-onet-profiles-eda.md`
- [ ] DQ rules: `governance/dq-rules/gold-onet-profiles.json`
- [ ] DQ scorecard: `governance/dq-scorecards/gold-onet-profiles-scorecard.md`
- [ ] Chaos manifest: `governance/chaos-manifests/gold-onet-profiles-chaos.md`
- [ ] Golden dataset: `governance/golden-datasets/gold-onet-profiles-golden.json`
- [ ] Lineage: `governance/lineage/gold-onet-profiles-{timestamp}.json`
- [ ] Data contracts: `governance/data-contracts/consumable-onet-work-profiles.yaml`, `governance/data-contracts/consumable-career-transitions.yaml`
- [ ] Staff review: `governance/reviews/gold-onet-profiles-staff-review.md`

## FutureProof Integration: The Complete Picture

After this Gold spec, the consumable layer has:

| Gold Table | Stats/Bosses | Join Key |
|-----------|-------------|----------|
| consumable.career_outcomes (College Scorecard) | ERN, ROI | cipcode |
| consumable.occupation_profiles (BLS OOH) | ERN, GRW, Market boss, Ceiling boss | soc_code |
| consumable.onet_work_profiles (this spec) | HMN, Burnout boss, AI boss context | bls_soc_code |
| consumable.career_transitions (this spec) | Stage 3 branching | bls_soc_code pairs |

**What's still missing:**
- **CIP→SOC crosswalk** — bridges career_outcomes (CIP) to the three SOC-coded tables
- **RES stat (AI Resilience)** — needs Karpathy scores + task-level AI scoring (separate Gold spec)
- **Unified cross-source product** — joins everything via crosswalk into one queryable surface

The crosswalk is the next spec after this one.
