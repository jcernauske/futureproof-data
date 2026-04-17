# Spec: onet-experience-requirements

**Status:** APPROVED FOR IMPLEMENTATION
**Zone:** Raw → Silver → Gold → MCP
**Primary Agent:** bs:primary-agent
**Created:** 2026-04-16
**Last Revised:** 2026-04-16 (governance blockers addressed)

---

## Problem Statement

The current career tree (`career_tree.py`) shows all O*NET-related occupations as potential branches regardless of experience requirements. A Software Developer node shows "Chief Technology Officer" as a possible branch even though CTOs typically require 10+ years of experience. This creates an overwhelming, unrealistic tree visualization.

O*NET publishes "Education, Training, and Experience" data with percent frequencies showing how much prior work experience each occupation typically requires. By ingesting this data and joining it to `career_branches`, we can:

1. **Gate branches by experience** — only show transitions realistic for the user's career stage
2. **Enable decade-based bucketing** — collapse branches into "Your 20s", "Your 30s", "Your 40s" views
3. **Show unlock progression** — "This path unlocks at 8+ years experience"

## Source Data

- **Source:** O*NET 30.2 Database (same ZIP as existing O*NET ingest)
- **File:** `Education, Training, and Experience.txt`
- **License:** Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Method:** Extract from existing bulk ZIP download at `https://www.onetcenter.org/dl_files/database/db_30_2_text.zip`
- **Fallback:** Read from `data/raw/onet_cache/` directory (existing cache)
- **Rows:** ~35,881 (percent frequency data across all categories)
- **Format:** Tab-delimited text with headers
- **Entities:** 878 O*NET-SOC occupations × 4 scales × variable categories *(spec originally said ~1,016 from Occupation Data; real ETE coverage is 878 per EDA 2026-04-16)*

### What the Data Contains

The file has percent frequency distributions across 4 scales per occupation:
- **RL** — Required Level of Education (12 categories)
- **RW** — Related Work Experience (11 categories) ← **This is what we need**
- **PT** — On-Site or In-Plant Training (9 categories)
- **OJ** — On-the-Job Training (9 categories) *(spec originally said 11; corrected 2026-04-16 after EDA measured 9 in every occupation)*

### Related Work Experience Categories (RW Scale)

| Category | Description | Midpoint Years |
|----------|-------------|----------------|
| 1 | None | 0 |
| 2 | Up to and including 1 month | 0 |
| 3 | Over 1 month, up to and including 3 months | 0.17 |
| 4 | Over 3 months, up to and including 6 months | 0.38 |
| 5 | Over 6 months, up to and including 1 year | 0.75 |
| 6 | Over 1 year, up to and including 2 years | 1.5 |
| 7 | Over 2 years, up to and including 4 years | 3 |
| 8 | Over 4 years, up to and including 6 years | 5 |
| 9 | Over 6 years, up to and including 8 years | 7 |
| 10 | Over 8 years, up to and including 10 years | 9 |
| 11 | Over 10 years | 12 |

## Success Criteria

- [ ] Raw data lands in Iceberg table `raw.onet_experience`
- [ ] All ~1,016 O*NET-SOC occupations ingested across all 4 scales
- [ ] Silver base table `base.onet_experience_profiles` produced at BLS SOC grain (~867 rows)
- [ ] Gold table `consumable.career_branches` updated with `related_experience_years`, `related_experience_tier`, `experience_delta_years`
- [ ] MCP tool `get_career_branches` returns experience fields
- [ ] Service layer `career_tree.py` can filter by experience threshold
- [ ] DQ rules written and passing at each zone
- [ ] Data contracts produced/updated

---

## Zone 1: Bronze (Raw Ingest)

### Iceberg Table: raw.onet_experience

- **Grain:** onet_soc_code × element_id × scale_id × category
- **Dedup grain:** [onet_soc_code, element_id, scale_id, category]
- **Expected rows:** ~35,881

### Ingestor

- **Class:** `OnetExperienceIngestor` (extends `OnetBaseIngestor`)
- **Location:** `src/raw/onet_ingestor.py` — add as the 6th subclass (there are 5 existing concrete subclasses: Occupations, TaskStatements, WorkActivities, WorkContext, RelatedOccupations). Do NOT create a new file.
- **Implementation notes:**
  - Reuse existing `OnetBaseIngestor` ZIP download/cache mechanism (`raw-ingest-onet.md`)
  - Extract `Education, Training, and Experience.txt` from ZIP
  - Tab-delimited parsing with headers
  - Ingest ALL rows (all 4 scales: RL, RW, PT, OJ) — Silver filters to RW only
  - Preserve `recommend_suppress` flag for DQ
  - Update module docstring to accurately reflect "six thin subclasses" (the prior "seven" language was aspirational/incorrect)

### Raw Schema

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| onet_soc_code | string | yes | O*NET-SOC code (XX-XXXX.XX format) |
| element_id | string | yes | Content Model element ID (e.g., "3.A.1" for Related Work Experience) |
| element_name | string | yes | Element name (e.g., "Related Work Experience") |
| scale_id | string | yes | Scale identifier ("RL", "RW", "PT", "OJ") |
| category | int | yes | Category value (1-11 for RW scale, varies by scale) |
| data_value | double | yes | Percent frequency for this category |
| n | int | no | Sample size |
| standard_error | double | no | |
| lower_ci_bound | double | no | |
| upper_ci_bound | double | no | |
| recommend_suppress | string | no | "Y" or "N" |
| date | string | no | Data collection date |
| domain_source | string | no | "Incumbent" or "Occupational Expert" |
| ingested_at | timestamp | yes | Ingestion timestamp |
| source_url | string | yes | Download URL |
| source_method | string | yes | "bulk_zip_download" |
| load_date | date | yes | Date of load |

### DQ Rules (Bronze)

*Thresholds calibrated against real ingest of 35,998 rows on 2026-04-16. See `governance/eda/raw-onet-experience-eda.md`.*

- Row count: 30,000 ≤ count ≤ 45,000 (P0 — allow for O*NET version variance)
- onet_soc_code format: XX-XXXX.XX (P0)
- scale_id IN ('RL', 'RW', 'PT', 'OJ') (P0)
- data_value range: 0.0 ≤ data_value ≤ 100.0 (P0 — it's a percentage)
- Sum of data_values per occupation × scale ≈ 100.0, tolerance ±0.1 (P1 — measured max deviation 0.03)
- element_id non-null: 100% (P0)
- onet_soc_code uniqueness at grain level (P0)
- RW scale rows: 9,000 ≤ count ≤ 12,500 (P1 — 878 occupations × 11 categories ≈ 9,658 observed)
- Occupation coverage: 800 ≤ distinct(onet_soc_code) ≤ 1,100 (P1 — 878 observed)
- Per-scale category counts: RL=12, RW=11, PT=9, OJ=9 (P1 — exact match expected)

---

## Zone 2: Silver (Normalize + Model)

### Iceberg Table: base.onet_experience_profiles

- **Grain:** bls_soc_code (one row per BLS-level occupation)
- **Dedup grain:** [bls_soc_code]
- **Promote pattern:** `compute_grain_id(row, ['bls_soc_code'], prefix='exp')`
- **Expected rows:** ~765 BLS-SOC roots *(original spec said ~867 based on 1,016 O*NET details; real ETE coverage is 878 details → ~765 BLS-SOC after collapse per EDA 2026-04-16)*

### Silver Transformations

1. **Filter to RW scale:** Only `scale_id = "RW"` and `element_id = "3.A.1"` (Related Work Experience)

2. **Compute weighted median category:** For each O*NET-SOC code, use percent frequencies (`data_value`) as weights to find the median category (1-11). The median is the category where cumulative frequency crosses 50%.

3. **Map category to years:** Convert median category to `experience_years_typical` using the midpoint table above.

4. **Derive experience tier:**
   - 0-1 years → "entry"
   - 1-4 years → "early"
   - 4-8 years → "mid"
   - 8+ years → "senior"

5. **Aggregate to BLS SOC:** Truncate O*NET-SOC (XX-XXXX.XX) to BLS SOC (XX-XXXX). For multi-detail codes, average `experience_years_typical` across details (unweighted).

6. **Preserve distribution:** Store full category distribution as JSON for optional downstream use.

### Silver Schema

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| record_id | string | yes | Deterministic grain hash (prefix: `exp`) |
| bls_soc_code | string | yes | 6-digit BLS SOC code |
| experience_category_median | int | yes | Weighted median category (1-11) |
| experience_years_typical | double | yes | Midpoint years for median category |
| experience_tier | string | yes | "entry", "early", "mid", "senior" |
| experience_category_mode | int | yes | Most common category (highest percent) |
| experience_distribution | string | yes | JSON: `{"1": 5.2, "7": 45.3, ...}` |
| onet_details_averaged | int | yes | Count of O*NET detail codes aggregated |
| suppress_flag | boolean | yes | True if recommend_suppress = "Y" in any contributing row |
| source_load_date | date | yes | From Bronze |
| ingested_at | timestamp | yes | Silver promotion timestamp |

### DQ Rules (Silver)

*Calibrated against real Bronze ingest; see `governance/eda/raw-onet-experience-eda.md`.*

- Row count: 720 ≤ count ≤ 810 (P0 — ~765 expected; 878 O*NET details → 765 BLS-SOC roots)
- bls_soc_code format: XX-XXXX (P0)
- bls_soc_code uniqueness (P0)
- experience_years_typical range: 0 ≤ years ≤ 15 (P0)
- experience_tier IN ('entry', 'early', 'mid', 'senior') (P0)
- experience_category_median range: 1 ≤ cat ≤ 11 (P0)
- All 4 tiers represented (P1)
- Spot check: "11-1011" (Chief Executives) tier = "senior" (P0 — observed: category 11, years=12, tier=senior)
- Spot check: "15-1252" (Software Developers) tier = "mid" (P0 — observed: category 9, years=7, tier=mid)
- Spot check: "41-2031" (Retail Salespersons) tier = "entry" (P0 — observed: bimodal RW distribution, weighted median category=5, years=0.75, tier=entry). Rules of form `median_category ≤ 3 for entry` would FAIL on real data and must not be written.

### Business Glossary Terms

| Term ID | Name | Definition |
|---------|------|-----------|
| BT-117 | Related Work Experience | O*NET measure of typical prior work experience required to enter an occupation, expressed as a percent frequency distribution across 11 duration categories (None to 10+ years). Source: O*NET Data Collection Program, incumbent survey. |
| BT-118 | Experience Tier | FutureProof-derived classification of occupations by typical experience requirement: entry (0-1 years), early (1-4 years), mid (4-8 years), senior (8+ years). Used to gate career branch visibility in the evolution tree. Thresholds human-approved 2026-04-16 — see `governance/approvals/onet-experience-requirements-open-decisions.md`. |

**Note:** BT-110 and BT-111 were initially proposed but collide with existing auto-approved terms (Cost of Attendance, Net Price). Reassigned to BT-117/BT-118 (next free IDs; BT-116 is the current max).

---

## Zone 3: Gold (Consumable Product)

### Iceberg Table Modification: consumable.career_branches

Modify the existing `career_branches` Gold table to include experience data for the *target* occupation in each branch.

**New columns:**

| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| related_experience_years | double | base.onet_experience_profiles | no | Typical years for the target occupation |
| related_experience_tier | string | base.onet_experience_profiles | no | Experience tier for target occupation |
| source_experience_years | double | base.onet_experience_profiles | no | Typical years for the source occupation |
| experience_delta_years | double | derived | no | `related - source` — how much more experience needed |

**Join logic in transformer:**
```sql
-- Join experience for the RELATED (target) occupation
LEFT JOIN base.onet_experience_profiles exp_related
  ON career_branches.related_soc_code = exp_related.bls_soc_code

-- Join experience for the SOURCE occupation  
LEFT JOIN base.onet_experience_profiles exp_source
  ON career_branches.soc_code = exp_source.bls_soc_code
```

**Derived field (NULL-propagating):**
```sql
-- Only compute delta when both sides have experience data; otherwise NULL
experience_delta_years = CASE
    WHEN exp_related.experience_years_typical IS NULL
      OR exp_source.experience_years_typical  IS NULL
    THEN NULL
    ELSE exp_related.experience_years_typical - exp_source.experience_years_typical
END
```

Rationale: the original `COALESCE(..., 0)` variant overstated the gap when source had no experience data (e.g., entry-level occupations with insufficient O*NET coverage), reporting `related - 0`. NULL propagation makes "unknown" explicit and lets downstream consumers filter or badge as appropriate.

### DQ Rules (Gold — additions)

- related_experience_years null rate < 5% (P1 — most branches should have data)
- experience_delta_years range: -12 ≤ delta ≤ 12 (P1 — tightened from draft -10/+15 to match mathematically-exact midpoint bounds; see governance/approvals/onet-experience-requirements-open-decisions.md and rule GLD-CB-EXP-002 rationale)
- Where related_experience_tier = "senior", related_experience_years >= 8 (P0)

### Data Contract Update: consumable.career_branches

Add to existing contract:

| Property | Value |
|----------|-------|
| New fields | related_experience_years, related_experience_tier, source_experience_years, experience_delta_years |
| Schema version | Increment by 1 |
| Migration | Additive only — no breaking changes |

---

## Zone 4: MCP (Tool Interface)

### Modified MCP Tool: `get_career_branches`

Update `CAREER_BRANCHES_RESPONSE_FIELDS` in `src/mcp_server/futureproof_server.py`:

```python
CAREER_BRANCHES_RESPONSE_FIELDS = [
    # ... existing fields ...
    "related_experience_years",
    "related_experience_tier",
    "source_experience_years", 
    "experience_delta_years",
]
```

No handler logic changes needed — new columns flow through automatically via `query_iceberg_simple`.

**Updated response example:**
```json
{
  "soc_code": "15-1252",
  "source_title": "Software Developers",
  "related_soc_code": "11-3021",
  "related_title": "Computer and Information Systems Managers",
  "best_index": 3,
  "relatedness_tier": "Primary-Short",
  "related_experience_years": 7.0,
  "related_experience_tier": "mid",
  "source_experience_years": 3.0,
  "experience_delta_years": 4.0
}
```

---

## Zone 5: Service Layer (Backend Integration)

### Model Update: backend/app/models/career.py

```python
@dataclass
class CareerBranch:
    # ... existing fields ...
    experience_years: float | None = None
    experience_tier: str | None = None
    experience_delta: float | None = None
```

### Service Update: backend/app/services/branch_tree.py

Map MCP response to model:

```python
branches.append(
    CareerBranch(
        # ... existing fields ...
        experience_years=row.get("related_experience_years"),
        experience_tier=row.get("related_experience_tier"),
        experience_delta=row.get("experience_delta_years"),
    )
)
```

### Service Update: backend/app/services/career_tree.py

Add experience filtering to `build_tree()`:

```python
def build_tree(
    build: Build,
    *,
    max_depth: int = 3,
    max_experience_years: float | None = None,  # NEW
) -> tuple[TreeNode, TreeStats]:
```

Filter during expansion:

```python
for row in rows:
    # NEW: experience gating
    if max_experience_years is not None:
        exp_years = row.get("related_experience_years")
        if exp_years is not None and exp_years > max_experience_years:
            continue  # Skip branches requiring too much experience
```

Add to TreeNode:

```python
@dataclass
class TreeNode:
    # ... existing fields ...
    experience_years: float | None = None
    experience_tier: str | None = None
```

---

## Agent Workflow

The spec crosses four zones. The orchestrator (`/bs:run`) dispatches each agent below via `Agent(subagent_type: "bs:<agent-name>", ...)`.

### Phase 0 — Pre-Implementation Gate
1. **bs:governance-reviewer** — Pre-implementation review (Bronze zone gate)

### Phase 1 — Semantic Models (BEFORE any implementation; greenfield gate)
2. **bs:data-steward** — Approve new business glossary terms BT-117, BT-118
3. **bs:semantic-modeler** — Conceptual → Logical → Physical for `base.onet_experience_profiles` in `governance/models/silver-base-onet-experience-{conceptual,logical,physical}.md`; plus a physical-model addendum to `gold-futureproof-engine-physical.md` covering the 4 additive `career_branches` columns. Human approval required before step 4.

### Phase 2 — Bronze (Raw Ingest)
4. **bs:primary-agent** — Implement `OnetExperienceIngestor` as the 8th subclass in `src/raw/onet_ingestor.py`
5. **bs:data-analyst** — EDA on `raw.onet_experience` (scale distribution, RW validation, suppression rate)
6. **bs:domain-context** — Append O*NET ETE methodology section to `governance/domain-context.md`
7. **bs:dq-rule-writer** — Write Bronze DQ rules → `governance/dq-rules/raw-onet-experience.json`
8. **bs:dq-engineer** — Execute rules → `governance/dq-results/`, `governance/dq-scorecards/`
9. **bs:chaos-monkey** — Adversarial hardening (weighted median edge cases — see §Test Matrix)
10. **bs:entity-resolver** — SKIP justified (O*NET-SOC is an external standard identifier, no resolution needed)
11. **bs:pii-scanner** — SKIP justified (occupation-level aggregates, no PII)
12. **bs:temporal-modeler** — SKIP justified (static annual snapshot, no temporal dimension)
13. **bs:lineage-tracker** — Emit OpenLineage event for Bronze ingest → `governance/lineage/onet-experience-raw-{timestamp}.json`
14. **bs:cde-tagger** — Apply CDE tags per §CDE & PII Assessment
15. **bs:doc-generator** — Data dictionary entries → `governance/data-dictionary.json`
16. **bs:adversarial-auditor** — SKIP ONLY if `@chaos-monkey` reports no gaps after 5 cycles

### Phase 3 — Silver (Normalize + Model)
17. **bs:dq-rule-writer** — Write Silver DQ rules → `governance/dq-rules/silver-onet-experience.json`
18. **bs:primary-agent** — Build Silver transformer (`src/silver/onet_experience_transformer.py`) with weighted-median logic
19. **bs:dq-engineer** — Execute Silver rules, chaos harden
20. **bs:lineage-tracker** — OpenLineage event for Silver transformation
21. **bs:cde-tagger** — Apply CDE tags on Silver fields
22. **bs:doc-generator** — Data dictionary entries for Silver columns

### Phase 4 — Gold (Modify career_branches)
23. **bs:cab-agent** — Schema-modification review for additive columns on `consumable.career_branches` (existing Silver/Gold table change → severity classification required)
24. **bs:dq-rule-writer** — Addendum DQ rules → `governance/dq-rules/gold-career-branches-experience.json`
25. **bs:primary-agent** — Modify Gold transformer (join experience to `career_branches`); bump contract to v1.2.0
26. **bs:dq-engineer** — Execute Gold addendum rules
27. **bs:lineage-tracker** — OpenLineage event for Gold join
28. **bs:doc-generator** — Data dictionary entries for 4 new Gold columns; update `consumable-career-branches.yaml` contract

### Phase 5 — MCP + Service Layer
29. **bs:primary-agent** — Update `CAREER_BRANCHES_RESPONSE_FIELDS` in `src/mcp_server/futureproof_server.py`
30. **bs:primary-agent** — Update backend: `backend/app/models/career.py`, `backend/app/services/branch_tree.py`, `backend/app/services/career_tree.py`

### Phase 6 — Post-Implementation Gate
31. **bs:governance-reviewer** — Post-implementation review (all zones)
32. **bs:staff-engineer** — Final review (special attention to service-layer changes + MCP contract)

### Agent Dispatch Rules (non-negotiable)
- All Brightsmith agents use the `bs:` namespace prefix at dispatch time.
- `bs:primary-agent`, `bs:governance-reviewer`, `bs:staff-engineer`, `bs:data-analyst`, `bs:dq-rule-writer`, `bs:dq-engineer`, `bs:chaos-monkey`, `bs:lineage-tracker`, `bs:cde-tagger`, `bs:doc-generator` are NEVER skippable.
- Skips on `bs:entity-resolver`, `bs:pii-scanner`, `bs:temporal-modeler`, `bs:adversarial-auditor` must be registered via `pipeline_gate skip` with a justification.

---

## CDE & PII Assessment

### PII Risk: NONE

O*NET publishes only occupation-level aggregate statistics (percent frequency distributions across duration categories). No individuals are identifiable; no survey-respondent identifiers flow into any zone. `bs:pii-scanner` is formally skipped under this spec with justification referencing this section.

### Critical Data Element (CDE) Dispositions

| Zone | Field | `is_cde` | `is_pii` | Rationale |
|------|-------|:--------:|:--------:|-----------|
| Raw (`raw.onet_experience`) | `onet_soc_code` | ✅ | ❌ | Join key across O*NET pipeline |
| Raw | `element_id` | ✅ | ❌ | Filters to `3.A.1` (Related Work Experience) in Silver |
| Raw | `scale_id` | ✅ | ❌ | Filters to `RW` in Silver |
| Raw | `category` | ❌ | ❌ | Dimensional input to weighted median |
| Raw | `data_value` | ❌ | ❌ | Percent frequency — weight input |
| Raw | `recommend_suppress` | ❌ | ❌ | DQ/provenance flag |
| Silver (`base.onet_experience_profiles`) | `bls_soc_code` | ✅ | ❌ | Grain key; join to Gold `career_branches` |
| Silver | `experience_years_typical` | ✅ | ❌ | Primary metric; feeds Gold + MCP + branching UI |
| Silver | `experience_tier` | ✅ | ❌ | Drives career-tree gating UX decision (cross-boundary classifier) |
| Silver | `experience_category_median` | ❌ | ❌ | Internal derivation |
| Silver | `experience_category_mode` | ❌ | ❌ | Internal derivation |
| Silver | `experience_distribution` | ❌ | ❌ | Optional downstream diagnostic |
| Silver | `onet_details_averaged` | ❌ | ❌ | Provenance count |
| Silver | `suppress_flag` | ❌ | ❌ | DQ flag |
| Gold (`consumable.career_branches`) | `related_experience_years` | ✅ | ❌ | Shown to users; feeds default-view filter |
| Gold | `related_experience_tier` | ✅ | ❌ | UX gating + decade bucketing |
| Gold | `source_experience_years` | ✅ | ❌ | Delta computation input |
| Gold | `experience_delta_years` | ✅ | ❌ | Primary default-view threshold (≤ 5 years) |

`bs:cde-tagger` must apply these flags to `governance/data-contracts/base-onet-experience-profiles.yaml` and to the addendum in `governance/data-contracts/consumable-career-branches.yaml`.

---

## Test Matrix — Weighted Median Edge Cases

`bs:chaos-monkey` and the implementing test writer must cover:

| Case | Input | Expected Behavior |
|------|-------|-------------------|
| Empty distribution | No RW rows for an O*NET-SOC | Skip occupation; log provenance |
| Single category 100% | One RW category at `data_value=100.0` | Median = that category |
| All suppressed | Every RW row has `recommend_suppress='Y'` | `suppress_flag=True`; exclude from DQ spot checks |
| Tie at 50% | Cumulative frequency lands exactly on a category boundary | Pick the lower-numbered (more-conservative) category |
| Multi-detail aggregation | `15-1252.00` and `15-1252.01` both present | Unweighted average of `experience_years_typical`; `onet_details_averaged=2` |
| Missing source experience (Gold) | `exp_source.experience_years_typical` NULL | `experience_delta_years` NULL (NULL-propagating — see §Zone 3) |
| Known-value spot checks | `11-1011` (Chief Executives), `41-2031` (Retail Salespersons) | Senior / Entry tier respectively |

---

## Governance Artifacts

### Human Approvals (pre-implementation)
- [x] Open-decisions approvals: `governance/approvals/onet-experience-requirements-open-decisions.md` (tier thresholds, 10+ midpoint, multi-detail aggregation — approved 2026-04-16)
- [ ] Semantic-model approvals (conceptual/logical/physical): `governance/approvals/silver-base-onet-experience-{conceptual,logical,physical}-approval.md`
- [ ] Business-terms approval (BT-117, BT-118): `governance/approvals/silver-base-onet-experience-business-terms-approval.md`

### EDA & Domain Context
- [ ] EDA report: `governance/eda/raw-onet-experience-eda.md`
- [ ] Domain context append: `governance/domain-context.md` (O*NET ETE methodology section)

### Data Models
- [ ] Conceptual: `governance/models/silver-base-onet-experience-conceptual.md`
- [ ] Logical: `governance/models/silver-base-onet-experience-logical.md`
- [ ] Physical: `governance/models/silver-base-onet-experience-physical.md`
- [ ] Physical addendum for Gold 4 additive columns: `governance/models/gold-futureproof-engine-physical.md` (append section)

### DQ Rules (written)
- [ ] Bronze: `governance/dq-rules/raw-onet-experience.json`
- [ ] Silver: `governance/dq-rules/silver-onet-experience.json`
- [ ] Gold addendum: `governance/dq-rules/gold-career-branches-experience.json`

### DQ Execution (by `bs:dq-engineer`)
- [ ] Bronze results: `governance/dq-results/raw-onet-experience-{timestamp}.json`
- [ ] Silver results: `governance/dq-results/silver-onet-experience-{timestamp}.json`
- [ ] Gold addendum results: `governance/dq-results/gold-career-branches-experience-{timestamp}.json`
- [ ] DQ scorecards: `governance/dq-scorecards/{bronze,silver,gold}-onet-experience.md`

### Chaos Hardening
- [ ] Chaos report: `governance/chaos-reports/onet-experience-{timestamp}.md`

### Data Contracts
- [ ] New contract: `governance/data-contracts/base-onet-experience-profiles.yaml`
- [ ] Updated contract: `governance/data-contracts/consumable-career-branches.yaml` (v1.1.0 → v1.2.0, additive schema change)

### Lineage (three OpenLineage events — one per transformation boundary)
- [ ] Bronze: `governance/lineage/onet-experience-raw-{timestamp}.json`
- [ ] Silver: `governance/lineage/onet-experience-silver-{timestamp}.json`
- [ ] Gold: `governance/lineage/onet-experience-gold-{timestamp}.json`

### Business Glossary
- [ ] Add BT-117 (Related Work Experience) and BT-118 (Experience Tier) to `governance/business-glossary.json`
- [ ] Update `used_in_models` on all existing BLS-SOC-keyed terms to include the new Silver/Gold models

### Data Dictionary
- [ ] Entries for 11 new Silver columns and 4 new Gold columns in `governance/data-dictionary.json`

### CDE Tagging Output
- [ ] Per-field `is_cde`/`is_pii` flags applied to both new/updated contracts (see §CDE & PII Assessment)

### Review Artifacts
- [ ] Pre-review: `governance/approvals/onet-experience-requirements-pre-review.md` (in-spec appendix is the canonical record)
- [ ] Post-review: `governance/approvals/onet-experience-requirements-post-review.md`
- [ ] Staff-engineer sign-off: `governance/approvals/onet-experience-requirements-staff-review.md`

---

## Cross-Source Integration Notes

This extends the existing O*NET pipeline:

**Before:**
```
raw.onet_* (7 tables) → base.onet_* (4 tables) → consumable.career_branches
```

**After:**
```
raw.onet_* (8 tables) → base.onet_* (5 tables) → consumable.career_branches (+ experience fields)
                                                        ↓
                                              get_career_branches MCP tool
                                                        ↓
                                              career_tree.py (experience filtering)
```

The experience data joins at the Gold level to `career_branches`, not as a separate Gold table. This keeps the MCP tool simple — one call returns branch + experience data.

---

## Open Decisions — Resolved

All design decisions below were approved by Jeff Cernauske on 2026-04-16. Durable record: `governance/approvals/onet-experience-requirements-open-decisions.md`.

1. **Experience tier thresholds — APPROVED.** `0–1 / 1–4 / 4–8 / 8+` years map to `entry / early / mid / senior`. Baked into Silver transformer tier derivation and Silver DQ spot-check rules (`11-1011 = senior`, `41-2031 = entry`).

2. **"Over 10 years" midpoint — APPROVED.** 12 years. Encoded in the midpoint mapping table; affects `experience_years_typical` for the entire senior tier and the `experience_delta_years` range DQ rule (`-10 ≤ delta ≤ 15`).

3. **Multi-detail aggregation — APPROVED.** Unweighted average of `experience_years_typical` across O*NET detail codes (e.g., `15-1252.00` and `15-1252.01`) when aggregating to BLS SOC. Matches existing O*NET Silver precedent.

4. **Filter vs. dim branches — DEFERRED to frontend spec.** This pipeline spec implements `max_experience_years` as a hide/filter in `career_tree.py`. Whether the UI surfaces filtered branches as dimmed ("locked") or removes them entirely is a frontend concern captured in a downstream frontend spec — not blocking.

---

## Estimated Effort

Small addition to existing O*NET pipeline. Reuses ZIP download, extends existing patterns.

| Step | Estimate |
|------|----------|
| Bronze ingestor | 1 hour |
| Silver transformer (weighted median) | 2 hours |
| Gold transformer modification | 1 hour |
| MCP + service layer updates | 1 hour |
| DQ rules + governance | 2 hours |
| Testing | 2 hours |
| **Total** | **~9-10 hours** |

---

## Frontend Integration Notes (For Future Spec)

Once this ships, the career tree can:

1. **Default view:** Only show branches where `experience_delta_years <= 5` (realistic 5-year hops)
2. **Decade bucketing:** Group branches by `related_experience_tier`
3. **Progressive disclosure:** Show locked branches with "Unlocks at 8+ years" badges
4. **Compare mode:** Show experience deltas between two career paths

---

*— End of Spec —*

---

## Post-Closure Cleanup (2026-04-17)

Minor service-layer DRY cleanup executed after spec closure, captured here for traceability. Not part of any of the 32 workflow steps; neither governance-reviewer nor staff-engineer flagged these as blocking. Done opportunistically while the spec's code paths were still top-of-mind.

**Advisory origin:** `governance/approvals/onet-experience-requirements-staff-review-mcp.md` §9 noted `_as_float` duplication between `branch_tree.py` and `career_tree.py` — both defs were byte-identical 7-line helpers added as part of this spec's Zone 5 work. Inspection also surfaced `_as_int` duplicated across three files (`branch_tree.py`, `career_tree.py`, `stat_engine.py`), pre-dating this spec but matching the same pattern.

**Changes:**

| Action | Path |
|--------|------|
| New | `backend/app/services/_coercion.py` — hosts `as_float()` and `as_int()` |
| Removed | `_as_float` duplicate in `backend/app/services/branch_tree.py` |
| Removed | `_as_float` duplicate in `backend/app/services/career_tree.py` |
| Removed | `_as_int` duplicate in `backend/app/services/branch_tree.py` |
| Removed | `_as_int` duplicate in `backend/app/services/career_tree.py` |
| Removed | `_as_int` duplicate in `backend/app/services/stat_engine.py` |

**Verification:**
- 267/267 backend service tests green (`pytest tests/services/`)
- Ruff clean on all four modified files + new module
- Call sites renamed from `_as_float` / `_as_int` to `as_float` / `as_int` (public names — they're intentionally importable now)

**Not done:** No signature changes, no behavioral changes, no new or modified tests. Pure move-and-import refactor; existing test coverage of the call sites transitively covers the consolidated helpers.

---

## Revision Response to Pre-Implementation Review (2026-04-16)

The 6 blockers raised in the pre-implementation review below have been addressed as follows. Advisory items are also resolved inline.

| # | Blocker | Resolution |
|---|---------|------------|
| 1 | `@primary-agent` placeholder | Replaced with `bs:primary-agent` at spec header; §Agent Workflow restructured to use `bs:`-namespaced dispatch names throughout (32 steps across 6 phases). |
| 2 | CDE/PII disposition missing | New §CDE & PII Assessment section with per-field `is_cde`/`is_pii` table covering all 11 Silver fields and 4 Gold additive columns. PII risk formally declared NONE with pii-scanner skip justification inline. |
| 3 | Missing Silver data models + ordering | `bs:semantic-modeler` moved to Phase 1 (step 3) to run BEFORE any Bronze/Silver implementation. Three Silver models listed under §Governance Artifacts; a physical-model addendum for the 4 additive `career_branches` columns appended to `gold-futureproof-engine-physical.md`. Human approval required before Phase 2 begins. |
| 4 | BT-110 / BT-111 collision | Reassigned to BT-117 (Related Work Experience) and BT-118 (Experience Tier) in §Business Glossary Terms. |
| 5 | Tier thresholds + "10+" midpoint + multi-detail aggregation as open decisions | Resolved and captured in `governance/approvals/onet-experience-requirements-open-decisions.md` (human-approved 2026-04-16). §Open Decisions renamed to §Open Decisions — Resolved and cross-links to the approval file. |
| 6 | Incomplete §Governance Artifacts | Rewritten as 9 subsections (Approvals, EDA & Domain Context, Data Models, DQ Rules, DQ Execution, Chaos, Data Contracts, Lineage, Glossary, Data Dictionary, CDE Tagging Output, Review Artifacts) with explicit paths and checkboxes. |

**Advisory items also addressed:**

- A7 (single lineage file for three jobs): rewritten as three explicit OpenLineage events — Bronze, Silver, Gold — under §Governance Artifacts.
- A8 (ingestor reuse naming): §Ingestor section now specifies `OnetExperienceIngestor extends OnetBaseIngestor` and directs implementation into `src/raw/onet_ingestor.py` as the 8th subclass. Module docstring update noted.
- A9 (`experience_delta_years` COALESCE overstating the gap): switched to NULL-propagating `CASE` expression in §Zone 3; rationale captured inline.
- A10 (no explicit weighted-median test matrix): new §Test Matrix — Weighted Median Edge Cases with 7 test cases including ties, empty distributions, all-suppressed, multi-detail averaging, and spot checks.

Ready for re-review.

---

## Governance Review — Pre-Implementation

**Review Type:** Pre-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-16
**Verdict:** CHANGES REQUESTED

### Scope Summary

Cross-zone spec (Bronze → Silver → Gold → MCP → Service) that extends the existing O*NET pipeline with a new raw table (`raw.onet_experience`), a new Silver table (`base.onet_experience_profiles`), four additive columns on the existing Gold `consumable.career_branches`, plus MCP + backend wiring. Reuses the bulk ZIP download/cache already in place for the other seven O*NET tables. PII risk is trivial — all data is occupation-level aggregates from the O*NET public data collection.

### Pre-Implementation Checklist

| # | Item | Status | Note |
|---|------|--------|------|
| 1 | Problem statement & success criteria | PASS | §Problem Statement and §Success Criteria are explicit; 8 acceptance items enumerated. |
| 2 | Input data sources identified with paths | PASS | `db_30_2_text.zip` / `Education, Training, and Experience.txt` / `data/raw/onet_cache/` fallback — mirrors existing pattern. |
| 3 | Output artifacts defined with paths & formats | PASS | `raw.onet_experience`, `base.onet_experience_profiles`, `consumable.career_branches` (+4 cols); all field types listed. |
| 4 | Transformations described | PASS | Weighted-median logic, midpoint mapping, tier bucketing, BLS-SOC truncation, multi-detail aggregation, JSON distribution preservation. |
| 5 | Zone assignments correct | PASS | Raw vs. Silver-on-BLS-SOC vs. Gold-join vs. MCP-passthrough boundaries are clean and consistent with `raw-ingest-onet` / `silver-base-onet` / `gold-onet-profiles`. |
| 6 | Primary implementation agent identified | FAIL — BLOCKER #1 | Agent slug shown as literal `@primary-agent` at both §Primary Agent and in §Agent Workflow steps 2, 8, 9, 10, 11. Must be replaced with a real agent (the sibling O*NET specs use Claude Code general or a named primary implementation agent). |
| 7 | DQ rule categories specified | PASS | Eight Bronze rules with P0/P1 severity, eight Silver rules including two value-specific spot checks (11-1011 = senior, 41-2031 = entry), three Gold addendum rules. Matches density of `silver-base-onet.json` (35 rules) directionally. |
| 8 | CDE mapping impact assessed | FAIL — BLOCKER #2 | Agent workflow step 14 names `@cde-tagger`, but §Governance Artifacts omits any explicit CDE tagging output (no mention of which new fields are CDE). At minimum `experience_tier` drives a UX-gating decision in `career_tree.py` and should be evaluated for CDE status; `related_experience_years` feeds the `experience_delta_years` derivation. Spec should call out expected `is_cde` dispositions on the four new `career_branches` columns and on the Silver schema. |
| 9 | Lineage scope defined | PARTIAL | §Governance Artifacts lists one combined `onet-experience-{timestamp}.json` lineage file, but this spec crosses three transformation boundaries (Bronze ingest, Silver weighted-median, Gold join onto career_branches). OpenLineage convention in this repo emits one event per transformation job. Advisory: expect three events, one per zone transition — document the breakdown or keep the single-file note but clarify it contains three jobs. |
| 10 | Breaking changes flagged | PASS | §Data Contract Update explicitly states "Additive only — no breaking changes" and requires a schema version bump on the existing `consumable-career-branches.yaml` contract (currently `1.1.0` — bump to `1.2.0`). |
| 11 | Testing approach defined | PARTIAL | §Estimated Effort budgets 2h for testing but the spec body does not enumerate test cases (e.g., weighted-median edge cases — all-zero frequency, single-category 100%, suppression row behavior, multi-detail averaging for `15-1252.00` vs. `15-1252.01`). Chaos Monkey is in the workflow but its adversarial targets are not listed. Advisory: add a test matrix or defer to @test-writer with a §5 in the agent workflow. |

### Data Model Gate (Base zone greenfield)

The spec creates a new Base zone table (`base.onet_experience_profiles`). The 3-stage data-modeling progression applies in **greenfield mode** — models must exist and be approved before implementation begins.

| Stage | Path | Status |
|-------|------|--------|
| Conceptual | `governance/models/silver-base-onet-experience-conceptual.md` | NOT PRESENT — FAIL BLOCKER #3 |
| Logical | `governance/models/silver-base-onet-experience-logical.md` | NOT PRESENT — FAIL BLOCKER #3 |
| Physical | `governance/models/silver-base-onet-experience-physical.md` | NOT PRESENT — FAIL BLOCKER #3 |

Agent workflow step 7 (`@semantic-modeler`) is scheduled AFTER the Bronze ingestor (step 2) and BEFORE the Silver transformer (step 8). That is the correct ordering for greenfield Base work, but it violates the governance-reviewer's pre-implementation gate: models must be authored and human-approved BEFORE any Bronze or Silver implementation starts (CLAUDE.md `REQUIRE_HUMAN_APPROVAL: true`). Reorder the workflow so `@semantic-modeler` runs at step 2 (before Bronze), with human approval captured before Claude Code writes any ingestor code.

Also note: since `consumable.career_branches` already has an approved physical model (`gold-futureproof-engine-physical.md`), the four additive columns need a physical-model diff/addendum — not a new triplet — but the diff must still be authored and approved.

### Business Glossary — HARD CONFLICT

FAIL — BLOCKER #4. The spec proposes:

| Proposed | Spec name | Already assigned in `governance/business-glossary.json` |
|----------|-----------|---------------------------------------------------------|
| BT-110 | "Related Work Experience" | "Cost of Attendance (COA)" — auto-approved, used in college-scorecard-institution models |
| BT-111 | "Experience Tier" | "Net Price" — auto-approved, used in ROI denominator |

Highest currently assigned term ID is BT-116 (Room and Board). BT-108 and BT-109 are skipped/unassigned in the file but should be verified. Proposed assignments for this spec should move to **BT-117** (Related Work Experience) and **BT-118** (Experience Tier) at minimum. Rewrite §Business Glossary Terms to use free IDs and update all cross-references (the proposed `related_terms` arrays that currently point back at BT-110/BT-111 will need updating too).

### Open Decisions — Blockers vs. Advisory

§Open Decisions for Human Approval lists four items. Per the project's `REQUIRE_HUMAN_APPROVAL: true` policy, all four need resolution before implementation — but their disposition varies:

| Decision | Severity | Rationale |
|----------|----------|-----------|
| Experience tier thresholds (0-1/1-4/4-8/8+) | **BLOCKER #5** | Thresholds are hardcoded into Silver transformer logic AND appear in DQ spot-check rules (`11-1011 = "senior"` assumes 8+ year cutoff). Must be pinned before Silver implementation or both the code and the DQ rules drift. |
| Midpoint for "Over 10 years" (12 vs 15) | BLOCKER #5 | Directly encoded in midpoint mapping; affects `experience_years_typical` values for the entire senior tier; affects `experience_delta_years` range DQ rule (-10 ≤ delta ≤ 15). |
| Multi-detail aggregation (unweighted average) | Advisory | Matches existing O*NET Silver precedent; defensible default. Confirm but not blocking. |
| Filter vs. dim branches | Advisory | Spec commits to filter/hide; UI concern belongs in a downstream frontend spec. Not blocking for this pipeline spec. |

### Ingestor Reuse — Naming Discrepancy

Advisory. §Ingestor says the new class "extends existing O*NET ingestor base or `BaseIngestor`". The existing base is `OnetBaseIngestor` in `src/raw/onet_ingestor.py` (confirmed — handles ZIP download, caching, User-Agent headers, and common coercion). New ingestor MUST extend `OnetBaseIngestor` to reuse the cached ZIP, not `BaseIngestor` directly. Recommend consolidating into `src/raw/onet_ingestor.py` as the eighth subclass alongside the other seven, rather than a standalone `src/raw/onet_experience_ingestor.py` file — that matches the existing "seven thin subclasses" architecture comment at the top of the file. If consolidation is rejected, at least update the spec to say `OnetBaseIngestor` explicitly.

### Governance Artifacts — Missing Items

The §Governance Artifacts checklist is missing several expected items per the post-implementation checklist:

| Missing artifact | Severity |
|-----------------|----------|
| Data dictionary entries for 4 new Gold columns + 11 Silver columns (`governance/data-dictionary.json`) | CHANGES REQUESTED — add explicitly |
| CDE tagging outcome (per-field `is_cde`/`is_pii` flags on the updated `consumable-career-branches.yaml` and new `base-onet-experience-profiles.yaml`) | CHANGES REQUESTED — add explicitly |
| Agent decision logs (`governance/audit-trail/onet-experience-*.md`) | Advisory — implicit from workflow but not listed |
| DQ execution results (`governance/dq-results/`) AND scorecard (`governance/dq-scorecards/`) from real data | CHANGES REQUESTED — add explicitly; listed only as "Execute rules" in the workflow |
| Chaos report (`governance/chaos-reports/`) from @chaos-monkey | Advisory — implicit from workflow but not listed |

### Consistency Checks (Cross-Zone)

PASS with one nit:
- Silver `bls_soc_code` format check and Gold `related_soc_code` / `soc_code` regex (`^\d{2}-\d{4}$`) are consistent — join keys match.
- `experience_tier` enum identical in Silver schema, DQ rules, and MCP response example.
- `experience_years_typical` (Silver) vs. `related_experience_years` / `source_experience_years` (Gold) naming is intentional (grain shift + join-direction) and documented in the join logic.
- Nit: §Zone 3 `experience_delta_years` uses `COALESCE(..., 0) - COALESCE(..., 0)` — when source has no experience data, delta reports as `related - 0`, which overstates the gap. Consider `NULL` propagation instead, or add a DQ rule flagging rows where only one side was coalesced. Advisory.

### Insight Traceability

N/A — no Insight Report currently references this work. If any exists in `governance/insights/` that flagged "career tree shows unrealistic senior transitions," add an Insight-Closure note to the spec tying this work back. Advisory.

### Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | CHANGES REQUESTED | `@primary-agent` is a placeholder, not a real agent; appears in §Header and 5× in §Agent Workflow | Replace with a real agent name (Claude Code general, or a named implementation agent consistent with sibling O*NET specs). |
| 2 | CHANGES REQUESTED | CDE/PII disposition not stated for new fields | Add explicit `is_cde` / `is_pii` expectation to §Governance Artifacts and/or a dedicated §CDE Assessment section for the four Gold additions and eleven Silver fields. |
| 3 | CHANGES REQUESTED | Three Silver data-model stages do not exist for `base.onet_experience_profiles`; workflow also runs `@semantic-modeler` AFTER Bronze ingest, which violates the greenfield gate | Author conceptual/logical/physical models in `governance/models/silver-base-onet-experience-{conceptual,logical,physical}.md` with Mermaid `erDiagram` blocks; obtain human approval; reorder §Agent Workflow so `@semantic-modeler` runs before `@primary-agent` implementation of Bronze or Silver. Also add an addendum to `gold-futureproof-engine-physical.md` covering the four new `career_branches` columns. |
| 4 | CHANGES REQUESTED | Proposed term IDs BT-110 and BT-111 collide with existing approved terms ("Cost of Attendance" and "Net Price") | Reassign to **BT-117** (Related Work Experience) and **BT-118** (Experience Tier); update `related_terms` arrays accordingly. |
| 5 | CHANGES REQUESTED | Tier thresholds (0-1/1-4/4-8/8+) and "Over 10 years" midpoint are listed as open decisions but are baked into DQ rules and transformer logic | Convert to design decisions with human approval captured in `governance/approvals/` before Silver implementation starts. |
| 6 | CHANGES REQUESTED | §Governance Artifacts is missing data dictionary entries, CDE tagging output, DQ execution results, and DQ scorecard | Add each as explicit checklist items so post-implementation review has artifacts to verify. |
| 7 | ADVISORY | Lineage listed as one file for three transformation boundaries | Document expectation of three OpenLineage events (Bronze, Silver, Gold-join) even if serialized into a single file. |
| 8 | ADVISORY | New ingestor should extend `OnetBaseIngestor` (confirmed existing in `src/raw/onet_ingestor.py`), and ideally land as the 8th subclass in that file rather than a new file | Update §Ingestor Location to say `src/raw/onet_ingestor.py::OnetExperienceIngestor` (consolidate) and specify the base class by its real name. |
| 9 | ADVISORY | `experience_delta_years` COALESCE-to-zero may distort the metric when source occupation has no experience data | Either switch to NULL propagation or add a DQ rule to audit one-sided coalesces. |
| 10 | ADVISORY | No explicit test matrix for weighted-median edge cases (empty, all-suppressed, single-category-100%, multi-detail averaging) | Enumerate in §Testing or defer explicitly to @test-writer via an §Agent Workflow step. |

### Decision Rationale

The spec is well-structured, follows sibling O*NET spec patterns correctly, defines a clean cross-zone architecture, and has strong DQ coverage and clear success criteria — the implementation plan is sound. However, three hard blockers stop it from proceeding today:

1. **Glossary ID collision (Issue #4)** — shipping as-is would corrupt an auto-approved public glossary by overwriting real terms consumed by the college-scorecard-institution pipeline. This is not a drafting nit; it is a data-governance integrity violation.
2. **Missing Base-zone data models (Issue #3)** — `REQUIRE_HUMAN_APPROVAL: true` plus the greenfield Base gate require conceptual/logical/physical models to exist and be approved BEFORE implementation, not authored inline during it.
3. **Placeholder primary agent (Issue #1)** — `@primary-agent` is not a real dispatchable agent; implementation cannot be kicked off with this handle.

Issues #2, #5, and #6 are standard pre-implementation governance gaps. Issues #7–#10 are advisory and can be addressed in-line during implementation.

No PII concerns. No security concerns. No architectural concerns beyond the reuse nit (Issue #8).

Once blockers #1–#6 are resolved, this spec is ready for implementation. Estimate: 1–2 hours of spec revision + 30 min human approval cycle on the three Silver data models.

**Verdict: CHANGES REQUESTED**

---

## Governance Re-Review — Pre-Implementation (2026-04-16)

**Review Type:** Pre-Implementation (re-review following revision)
**Reviewer:** @governance-reviewer
**Date:** 2026-04-16
**Verdict:** APPROVED

### Scope of Re-Review

Verified each of the 6 blockers raised in the prior CHANGES REQUESTED verdict, plus advisories A7–A10. Read the entire revised spec (573 lines of spec body + the Revision Response table) and cross-checked against on-disk artifacts (`governance/approvals/`, `governance/business-glossary.json`).

### Blocker Verification

| # | Blocker | Required Fix | Evidence in Revised Spec | Verdict |
|---|---------|--------------|---------------------------|---------|
| 1 | `@primary-agent` placeholder | Replace with dispatchable `bs:`-namespaced agent in header + all workflow steps | Header line 5 reads `Primary Agent: bs:primary-agent`. §Agent Workflow enumerates exactly **32 numbered steps** across 6 phases, every step prefixed `bs:`. Verified via regex scan: no `@primary-agent` literal remains. | RESOLVED |
| 2 | CDE/PII disposition missing | New §CDE Assessment with per-field tables for Raw/Silver/Gold | §CDE & PII Assessment (lines 404–434) declares PII risk NONE with pii-scanner skip justification, then lists a 3-block disposition table covering 6 Raw fields, 8 Silver fields, and all 4 Gold additive columns with explicit `is_cde`/`is_pii` marks. `bs:cde-tagger` binding to contract files named. | RESOLVED |
| 3 | Missing Silver data models + step ordering | `bs:semantic-modeler` runs BEFORE Bronze implementation; three Silver models + Gold physical-model addendum listed in §Governance Artifacts | Phase 1 step 3 is `bs:semantic-modeler` (line 356); first `bs:primary-agent` implementation step is step 4 (Phase 2, line 359). Human approval explicitly required before step 4. §Governance Artifacts > Data Models (lines 465–468) lists all three Silver models as explicit paths plus the Gold physical-model addendum. | RESOLVED |
| 4 | BT-110 / BT-111 collision | Reassign to next-free IDs; update cross-references | §Business Glossary Terms (lines 183–186) uses BT-117 (Related Work Experience) and BT-118 (Experience Tier). Cross-checked against `governance/business-glossary.json` — BT-116 (Room and Board) is current max; BT-110/BT-111 remain safely assigned to Cost of Attendance and Net Price. Note at line 186 explicitly documents the collision and reassignment. | RESOLVED |
| 5 | Open decisions as human approvals | Capture in `governance/approvals/` before Silver implementation | File `governance/approvals/onet-experience-requirements-open-decisions.md` exists (verified on disk, 5953 bytes, approved 2026-04-16 by Jeff Cernauske). It pins all three blocker decisions: tier thresholds `0-1/1-4/4-8/8+ → entry/early/mid/senior`, "Over 10 years" midpoint = 12, multi-detail aggregation = unweighted average. §Open Decisions — Resolved (lines 532–542) cross-links to the approval file and §Governance Artifacts > Human Approvals line 456 checks it off with `[x]`. | RESOLVED |
| 6 | Incomplete §Governance Artifacts | Rewrite into explicit subsections with paths + checkboxes | §Governance Artifacts (lines 453–506) restructured into 10 subsections: Human Approvals, EDA & Domain Context, Data Models, DQ Rules, DQ Execution, Chaos Hardening, Data Contracts, Lineage (three events), Business Glossary, Data Dictionary, CDE Tagging Output, Review Artifacts. Every item is a checkbox with an explicit artifact path. | RESOLVED |

### Advisory Verification

| # | Advisory | Evidence | Verdict |
|---|----------|----------|---------|
| A7 | Three separate OpenLineage events (Bronze, Silver, Gold) | §Governance Artifacts > Lineage (lines 488–491) enumerates three distinct files. Workflow steps 13, 20, 27 each explicitly emit one lineage event. | RESOLVED |
| A8 | `OnetBaseIngestor` reuse in `src/raw/onet_ingestor.py` as the 8th subclass | §Ingestor (lines 78–87) names the base class `OnetBaseIngestor` and specifies the location as `src/raw/onet_ingestor.py` as "the 8th subclass alongside the existing seven," with a "Do NOT create a new file" directive and a module-docstring update note. | RESOLVED |
| A9 | NULL-propagating `experience_delta_years` | §Zone 3 (lines 217–227) switches from `COALESCE(..., 0)` to a `CASE WHEN ... IS NULL ... THEN NULL` expression with rationale comment explaining the overstatement risk in the prior approach. | RESOLVED |
| A10 | Test matrix for weighted-median edge cases | New §Test Matrix — Weighted Median Edge Cases (lines 437–449) enumerates 7 explicit cases: empty distribution, single category 100%, all suppressed, tie at 50% (with tiebreaker rule), multi-detail aggregation, missing source experience, and known-value spot checks. | RESOLVED |

### Completeness Checklist (re-run)

| # | Item | Status |
|---|------|--------|
| 1 | Problem statement & success criteria | PASS |
| 2 | Input data sources identified with paths | PASS |
| 3 | Output artifacts defined with paths & formats | PASS |
| 4 | Transformations described | PASS |
| 5 | Zone assignments correct | PASS |
| 6 | Primary implementation agent identified (dispatchable) | PASS (was FAIL) |
| 7 | DQ rule categories specified | PASS |
| 8 | CDE mapping impact assessed | PASS (was FAIL) |
| 9 | Lineage scope defined | PASS (was PARTIAL) |
| 10 | Breaking changes flagged | PASS |
| 11 | Testing approach defined | PASS (was PARTIAL) |

### Data Model Gate (Base greenfield)

Workflow ordering now correctly places `bs:semantic-modeler` before any Bronze or Silver implementation. Models themselves (`governance/models/silver-base-onet-experience-*.md`) are NOT YET authored — but the gate on this re-review is that (a) the models are required and explicitly scheduled, (b) human approval is required before downstream steps, (c) paths and scope are enumerated in §Governance Artifacts. All three conditions met. Authoring and approval happen in Phase 1 step 3 during execution — before any code is written.

### Issues Found

None blocking. None advisory.

### Decision Rationale

All 6 prior blockers are resolved with concrete, verifiable artifacts (either in the spec body or on-disk in `governance/approvals/`). All 4 advisory items are also resolved. The glossary collision check passes — BT-117/BT-118 are confirmed free against the actual `business-glossary.json` file (max assigned is BT-116). The human-approval file for open decisions exists, is signed and dated, and pins every value the Silver transformer and DQ rules depend on. Step ordering now respects the greenfield data-model gate.

The revised spec is ready for implementation. `/bs:run` may proceed starting at Phase 1 step 3 (`bs:semantic-modeler`) to author the three Silver models + Gold physical-model addendum, obtain human approval on those, and then continue through Phase 2 Bronze implementation.

**Verdict: APPROVED**
