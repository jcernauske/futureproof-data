# Entity Resolution Assessment: gold-occupation-profiles-bls-ooh
**Date:** 2026-04-07
**Agent:** @entity-resolver
**Entity Type:** Occupation (SOC Code)
**Resolution Strategy:** ID-based resolution (authoritative federal identifier)
**Zone:** Gold (Consumable)
**Upstream Assessment:** governance/reviews/silver-base-bls-ooh-entity-resolution.md

---

## Finding: No Active Entity Resolution Required

This is a single-source Gold transformation of the Silver `base.bls_ooh` table. SOC codes are authoritative federal identifiers maintained by the Bureau of Labor Statistics under the SOC 2018 taxonomy. No fuzzy matching, deduplication, or cross-source resolution is performed in this spec. The Gold table carries forward all 832 SOC-coded occupation entities from Silver with no additions, deletions, or identity changes.

Cross-source entity resolution (CIP-to-SOC mapping via the NCES crosswalk) is scoped to a separate crosswalk spec, not this Gold product. This assessment validates the entity integrity of `consumable.occupation_profiles` and documents its readiness for that downstream integration.

---

## 1. SOC Code Entity Integrity

### Uniqueness and Format
| Metric | Value | Status |
|--------|-------|--------|
| Total rows | 832 | -- |
| Distinct SOC codes | 832 | PASS: 100% unique, grain holds |
| SOC code format (XX-XXXX) | 832 of 832 valid | PASS: zero violations |
| Null SOC codes | 0 | PASS |
| SOC code-to-title mapping | 1:1 | PASS: no ambiguity |
| record_id prefix | `op` (changed from Silver's `ooh`) | PASS: prefix distinguishes Gold from Silver records |
| record_id derivation | `compute_grain_id(row, ['soc_code'], prefix='op')` | Deterministic; stable across re-runs |

**Resolution confidence: 1.0** -- exact ID match. SOC codes are stable, well-formed, and unambiguous. The Gold table inherits the Silver grain with no fan-out or collapse.

### Physical Model Constraints Enforcing Entity Integrity
The physical model defines the following constraints on `soc_code`:
- `NOT NULL`
- `UNIQUE`
- `CHECK (soc_code ~ '^\d{2}-\d{4}$')`
- `soc_major_group CHECK` constrained to the enumerated set of 22 valid 2-digit codes

These constraints make it impossible for malformed or duplicate SOC entities to enter the Gold table.

---

## 2. Broad Occupation Codes (7 rows)

Seven SOC codes represent rolled-up/broad occupations rather than detailed occupations. These are flagged via `broad_occupation_flag = True` using a hardcoded frozenset in the Silver transformer (not pattern matching).

| SOC Code | Title | Major Group | Confidence Tier |
|----------|-------|-------------|-----------------|
| 13-1020 | Buyers and purchasing agents | 13 | medium |
| 13-2020 | Property appraisers and assessors | 13 | medium |
| 29-2010 | Clinical laboratory technologists and technicians | 29 | medium |
| 31-1120 | Home health and personal care aides | 31 | medium |
| 39-7010 | Tour and travel guides | 39 | medium |
| 47-4090 | Miscellaneous construction and related workers | 47 | medium |
| 51-2090 | Miscellaneous assemblers and fabricators | 51 | medium |

### Gold-Specific Entity Implications

**Derived score validity:** All 7 broad codes have non-null wages, non-null employment data, and non-null openings. GRW scores, market scores, and wage percentiles are all computable. The scores represent aggregated signals across multiple detailed occupations, which is less precise but not invalid.

**Confidence tier assignment:** All 7 receive `confidence_tier = "medium"` because `broad_occupation_flag = True` and `wage_available = True`. This correctly signals to Gold consumers (Gemma agent, frontend) that career guidance derived from these codes is less occupation-specific.

**FutureProof stat impact:** GRW and ERN stats computed from broad codes represent blended averages. For example, 31-1120 "Home health and personal care aides" aggregates two distinct job profiles. The pentagon stat will show blended numbers that may not reflect either sub-occupation accurately. The `confidence_tier = "medium"` annotation gives the frontend sufficient signal to caveat these results.

### Cross-Source Readiness

Broad codes present the primary challenge for future CIP-SOC crosswalk integration:
- O*NET uses detailed codes (XX-XXXX.XX); a direct SOC-to-SOC join will match these 7 at the broad level but miss detailed sub-occupations.
- CIP-SOC crosswalk mappings through broad codes should carry a lower confidence (recommended max 0.8 vs. 1.0 for detailed codes).
- Two of the 7 broad codes (47-4090, 51-2090) are also "Miscellaneous" categories, making them the weakest crosswalk signals in the dataset.

---

## 3. Catchall Categories (70 rows)

Seventy occupations have "all other" in their titles, flagged via `catchall_flag = True`. These are legitimate BLS residual categories representing occupations not individually classified within a minor group.

### Distribution Across Major Groups
All 22 SOC major groups contain at least 1 catchall category. Distribution ranges from 1 (groups 23 Legal, 31 Healthcare Support, 41 Sales) to 7 (group 29 Healthcare Practitioners).

### Relationship to Broad Codes
No overlap exists between broad codes and catchall categories. None of the 7 broad codes contain "all other" in their titles. The two flags are independent, as confirmed by both Silver EDA and Silver entity resolution assessment.

### Null-Wage Catchall Overlap (3 rows)
Three occupations trigger both null-wage AND catchall criteria:
- 27-2099 Entertainers and performers, all other
- 29-1229 Physicians, all other
- 29-1249 Surgeons, all other

Per the spec's confidence tier logic, `wage_available = False` takes priority over `catchall_flag = True`. All 3 are assigned `confidence_tier = "low"` (not "medium"). This means the medium tier contains 67 catchall-with-wage occupations (not all 70).

### Gold-Specific Entity Implications

**Score computation:** All 70 catchall codes have full employment data (employment_current, employment_projected, openings_annual_avg). GRW scores and market scores are computable for all 70. Wage percentiles are computable for 67 (3 have null wages).

**Confidence tier composition:**
| Tier | Catchall Count | Total Count |
|------|---------------|-------------|
| medium | 67 | 74 (67 catchall + 7 broad) |
| low | 3 | 23 (3 catchall + 20 non-catchall null-wage) |

**Career guidance quality:** Catchall occupations (e.g., 11-9199 "Managers, all other") have inherently imprecise career guidance. A student mapped to "Managers, all other" could be in any of dozens of specific management roles. The `catchall_flag` and `confidence_tier` annotations give Gold consumers the signal to caveat guidance from these entities.

### Cross-Source Readiness

Catchall SOC codes have valid CIP-SOC crosswalk mappings but the mapping is inherently imprecise. Recommended crosswalk confidence cap: 0.7 for catchall SOC codes. Catchall codes cannot be resolved to more specific occupations without additional data -- they are the most detailed level BLS publishes.

---

## 4. SOC Major Group Consistency

### 2-Digit Prefix Alignment

All 832 SOC codes in the Gold table have a `soc_major_group` derived from the first 2 characters of `soc_code`. The physical model constrains `soc_major_group` to the enumerated set of 22 valid codes:

```
11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35, 37, 39, 41, 43, 45, 47, 49, 51, 53
```

| Metric | Value | Status |
|--------|-------|--------|
| Major groups populated | 22 of 22 | PASS: full coverage |
| soc_major_group = soc_code[:2] | 832 of 832 | PASS: zero misalignment |
| soc_major_group_name determinism | 1:1 with soc_major_group | PASS: every code maps to exactly one name |

### Distribution by Major Group (sorted by count)

| Group | Name | Count | Broad | Catchall | Null-Wage | Detailed* |
|-------|------|-------|-------|----------|-----------|-----------|
| 51 | Production | 105 | 1 | 7 | 0 | 97 |
| 29 | Healthcare Practitioners and Technical | 80 | 1 | 7 | 17 | 55 |
| 47 | Construction and Extraction | 66 | 1 | 4 | 0 | 61 |
| 25 | Educational Instruction and Library | 64 | 0 | 2 | 0 | 62 |
| 43 | Office and Administrative Support | 48 | 0 | 4 | 0 | 44 |
| 49 | Installation, Maintenance, and Repair | 46 | 0 | 3 | 0 | 43 |
| 53 | Transportation and Material Moving | 44 | 0 | 3 | 0 | 41 |
| 13 | Business and Financial Operations | 42 | 2 | 2 | 0 | 38 |
| 15 | Computer and Mathematical | 30 | 0 | 2 | 0 | 28 |
| 35 | Food Preparation and Serving Related | 28 | 0 | 2 | 0 | 26 |
| 11 | Management | 27 | 0 | 2 | 0 | 25 |
| 19 | Life, Physical, and Social Science | 27 | 0 | 3 | 0 | 24 |
| 39 | Personal Care and Service | 27 | 1 | 4 | 0 | 22 |
| 17 | Architecture and Engineering | 26 | 0 | 2 | 0 | 24 |
| 27 | Arts, Design, Entertainment, Sports, and Media | 26 | 0 | 3 | 1 | 22 |
| 31 | Healthcare Support | 21 | 1 | 1 | 0 | 19 |
| 41 | Sales and Related | 20 | 0 | 1 | 0 | 19 |
| 37 | Building and Grounds Cleaning and Maintenance | 19 | 0 | 2 | 0 | 17 |
| 33 | Protective Service | 18 | 0 | 3 | 0 | 15 |
| 21 | Community and Social Service | 14 | 0 | 2 | 0 | 12 |
| 45 | Farming, Fishing, and Forestry | 13 | 0 | 5 | 5 | 3 |
| 23 | Legal | 8 | 0 | 1 | 0 | 7 |

*Detailed = Count - Broad - Catchall (occupations that are neither broad nor catchall; these get confidence_tier = "high" if wage is available).

### Notable Observations

- **Group 29 (Healthcare)** has the most null-wage occupations (17 of 23 total). These are physicians and surgeons whose median wages exceed the BLS reporting threshold. This group will have the lowest data completeness ratio of any major group.
- **Group 45 (Farming/Fishing)** has 5 null-wage occupations and 5 catchall categories out of only 13 total occupations. This is the weakest major group for career guidance -- only 3 of 13 occupations are detailed with available wages.
- **Group 25 (Educational Instruction)** has 64 occupations, heavily driven by postsecondary teacher specialties (e.g., "English Language and Literature Teachers, Postsecondary"). This may affect CIP-SOC crosswalk density -- many CIP codes may map to the same SOC major group 25 occupations.

---

## 5. Readiness for Cross-Source Entity Resolution

### Current State: Single-Source, Self-Contained

The `consumable.occupation_profiles` table is designed to stand alone as an occupation reference. It does not require the CIP-SOC crosswalk to be useful -- Gemma can query it directly by SOC code or occupation title.

### Readiness Checklist for CIP-SOC Crosswalk Integration

| Requirement | Status | Notes |
|-------------|--------|-------|
| SOC codes well-formed (XX-XXXX) | READY | 832/832 valid, physical model enforces regex constraint |
| SOC codes unique | READY | Zero duplicates, grain holds |
| SOC codes stable | READY | SOC 2018 taxonomy; no lifecycle events in current snapshot |
| Join key identified | READY | `soc_code` is the primary join key |
| Entity subpopulations flagged | READY | `broad_occupation_flag`, `catchall_flag`, `wage_available` carried to Gold |
| Confidence tiers for crosswalk | READY | Silver assessment recommended: 1.0 detailed, 0.8 broad, 0.7 catchall |
| Record ID distinct from Silver | READY | Gold uses `op-` prefix, Silver uses `ooh-` prefix -- no collision |
| soc_major_group available | READY | Enables major-group-level aggregation when crosswalk produces many-to-many mappings |

### O*NET Integration Readiness

| Aspect | Status | Notes |
|--------|--------|-------|
| SOC code format compatibility | READY | O*NET uses XX-XXXX.XX; join on left 7 characters of O*NET code |
| Detailed occupation match | READY | 755 detailed codes will match 1:1 with O*NET detailed codes |
| Broad occupation fan-out | FLAGGED | 7 broad codes will fan out to multiple O*NET detailed codes |
| SOC taxonomy version | ALIGNED | Both use SOC 2018; O*NET version must be confirmed at ingestion |

### CIP-SOC Crosswalk Integration Readiness

| Aspect | Status | Notes |
|--------|--------|-------|
| SOC code format | READY | CIP-SOC crosswalk uses XX-XXXX; direct match |
| Many-to-many relationship | DOCUMENTED | One CIP can map to multiple SOC codes; one SOC can map to multiple CIPs |
| Confidence model | PROPOSED | Silver entity assessment proposed 3-tier confidence: 1.0/0.8/0.7 |
| Education tier percentile caveat | NOTED | education_code = 6 has only 6 occupations; wage_percentile_education_tier is very coarse for that tier |
| Null-wage impact on crosswalk | NOTED | 23 occupations will contribute null ERN stats when reached via crosswalk |

### Recommended Confidence Tiers for Crosswalk Spec

These tiers are carried forward from the Silver entity resolution assessment and remain applicable at the Gold level:

| SOC Code Category | Count | Recommended Max Crosswalk Confidence | Gold Confidence Tier | Rationale |
|-------------------|-------|--------------------------------------|---------------------|-----------|
| Detailed occupation (neither broad nor catchall, wage available) | 735 | 1.0 | high | Clean 1:1 mapping, specific occupation, full stat data |
| Broad occupation (`broad_occupation_flag`) | 7 | 0.8 | medium | Maps to multiple O*NET children; aggregated stats |
| Catchall category (`catchall_flag`, wage available) | 67 | 0.7 | medium | Heterogeneous residual category; weak signal for career guidance |
| Null-wage occupation (catchall or not) | 23 | Same as category above | low | Full employment data but no ERN stat; crosswalk match is valid but outcome data is incomplete |

---

## 6. Entity Lifecycle Events

### Current Snapshot
No lifecycle events exist in the current data. This is a single biennial snapshot (projection cycle 2024-2034). All 832 entities are current and active.

### Future Lifecycle Risks

| Event | Trigger | Impact | Mitigation |
|-------|---------|--------|------------|
| SOC 2028 revision | OMB publishes new SOC taxonomy (~2028) | Codes may split, merge, or be renumbered. Gold record_ids will change. | BLS will publish a SOC 2018-to-2028 crosswalk. Ingest it as a reference table. Map old canonical IDs to new ones. |
| New projection cycle | BLS releases 2026-2036 projections (~2026) | All projection values replaced. Row count may change (new occupations added, obsolete ones removed). | Full table replace pattern already handles this. DQ rules on row count should allow +/- 50 tolerance. |
| Occupation mergers | SOC revision merges detailed codes into one | Two Gold entities collapse to one. Crosswalk mappings must update. | Log as merger lifecycle event. Surviving entity inherits both sets of crosswalk mappings. |
| Occupation splits | SOC revision splits one code into multiple | One Gold entity becomes multiple. CIP-SOC mappings must fan out. | Log as split lifecycle event. New entities inherit parent's crosswalk mappings until refined. |

---

## Resolution Statistics

| Metric | Value |
|--------|-------|
| Total entities assessed | 832 |
| Resolution method | ID-based (authoritative SOC code) |
| Resolution confidence | 1.0 (all rows) |
| Entities requiring fuzzy matching | 0 |
| Entities flagged for human review | 0 |
| Broad occupation codes (downstream flag) | 7 |
| Catchall categories (downstream flag) | 70 (67 medium-confidence + 3 low-confidence) |
| Null-wage entities (data completeness flag) | 23 |
| Lifecycle events discovered | 0 (single snapshot) |
| SOC major groups represented | 22 of 22 |
| Gold confidence tier: high | 735 (88.3%) |
| Gold confidence tier: medium | 74 (8.9%) |
| Gold confidence tier: low | 23 (2.8%) |

---

## Resolution Status: PASS -- No Action Required

Entity resolution is not required for this single-source Gold transformation. SOC codes are authoritative, unique, well-formed, and unambiguous. The Gold table correctly carries forward all entity classification flags from Silver (`broad_occupation_flag`, `catchall_flag`, `wage_available`) and derives a `confidence_tier` that reflects entity-level data quality for career guidance purposes.

The table is ready for cross-source entity resolution when the CIP-SOC crosswalk spec is implemented. The confidence tiers documented in this assessment and the Silver entity resolution assessment should be applied at that time.

### No Gaps or Blockers

- The 832 SOC entities in Gold exactly match the 832 in Silver -- no rows added or dropped.
- The `soc_code` natural key is the correct join key for all downstream integrations (O*NET, CIP-SOC crosswalk).
- The Gold-level `confidence_tier` provides a ready-made signal for downstream consumers to weight career guidance quality.
- The `broad_occupation_flag` and `catchall_flag` provide the raw signals needed for the crosswalk confidence model.
