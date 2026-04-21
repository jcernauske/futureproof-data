# Feature: Gold CIP Intent Resolution Data Product

## Claude Code Prompt

```
Read the spec at docs/specs/gold-cip-intent-resolution.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (data model, pipeline integration, MCP changes)
   - Invoke @fp-data-reviewer to review data quality implications (crosswalk coverage, earnings fallback integrity, lineage)
   - Both write findings to §5 (Architecture Review)
   - If APPROVED: proceed to step 2
   - If CHANGES REQUESTED (Significant): STOP, alert human
   - If REJECTED (Blocker): STOP, alert human

2. DESIGN VISION — SKIPPED (backend/pipeline spec)

3. IMPLEMENTATION
   - Implement the spec as written in §4 (Technical Spec)
   - Phase 1: Expand the YAML to full 48-family coverage (~500 entries) — must complete BEFORE pipeline ingestion
   - Phase 2: Ingest the complete YAML as Bronze, build Silver resolution, promote to Gold
   - Phase 3: Update MCP server to query the Gold product instead of runtime substring fallback
   - Phase 4: Backfill — regenerate program_career_paths using the resolution table
   - BEFORE coding: Review §4 Testing Impact Analysis thoroughly
   - DURING coding: Update any broken tests listed in "Authorized Test Modifications"
   - CRITICAL: If any test NOT in the "Authorized Test Modifications" list fails, STOP and escalate to human
   - Log all work to §6 (Implementation Log)
   - Run backend (ruff + mypy + pytest) to verify build
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts)
   - If still broken after 3 attempts: escalate to human via §10 Discussion

4. TESTING
   - Invoke @test-writer to review the full spec
   - @test-writer MUST review §4 Testing Impact Analysis
   - Implement all tests listed in "New Tests Required" by priority (P0 first)
   - Backend tests: pytest in tests/
   - Run ALL tests to catch regressions
   - If still broken after 3 attempts: escalate to human via §10 Discussion

5. DESIGN AUDIT — SKIPPED (backend/pipeline spec)

6. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests
   - Reviewer writes findings to §8 (Code Review)
   - If APPROVED: proceed to step 7
   - If CHANGES REQUIRED: route to originating agent via §10 Discussion
   - If BLOCKER: STOP, alert human

7. VERIFICATION
   - Invoke @fp-builder to run full build verification
   - Backend: ruff check, mypy, pytest
   - Also run: backend/tests/services (171 service tests)
   - Log results to §9 (Verification)
   - If all green: mark status COMPLETE

8. COMPLETION
   - Update top-level Spec Status to COMPLETE
   - Check off all completed Success Criteria in §1
   - Generate report to reports/gold-cip-intent-resolution-YYYY-MM-DD.md
```

---

## Status: DRAFT

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
| ARCH REVIEW | Awaiting @fp-architect approval |
| IMPLEMENTATION | Implementing |
| TESTING | @test-writer adding coverage |
| CODE REVIEW | @faang-staff-engineer reviewing |
| VERIFICATION | @fp-builder running full build |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-12 |
| Author | Jeff + Claude Desktop |
| Spec Version | 1.0 |
| Last Updated | 2026-04-12 |
| Blocked By | — |
| Related Specs | cip-intent-substitution (COMPLETE), gold-futureproof-engine-addendum-cip-fix, spike-intent-substitution, spike-broad-cip-prevalence, spike-cip-hierarchy-fallback |

---

## §1 Feature Description

### Overview

Formalize the CIP intent substitution system as a governed Brightsmith data product. The YAML lookup table (`data/reference/major_to_cip.yaml`) becomes a Bronze source. The CIP-to-CIP resolution logic (specific CIP → crosswalk SOCs + parent CIP → school earnings) becomes a Silver normalization and Gold consumable table. The MCP server queries the Gold product instead of doing runtime substring math.

This also includes expanding the YAML from 56 entries (Business + Education) to full coverage of all 48 CIP families (~400-500 entries), and implementing the CIP disaggregation fallback that allows 6-digit CIP substitutions to work by pairing specific-CIP crosswalk SOCs with parent-CIP school earnings.

### Problem Statement

The CIP intent substitution feature (spec: `cip-intent-substitution`, status: COMPLETE) correctly resolves student-typed major names to specific CIP codes. But a structural gap breaks all 6-digit CIP substitutions:

- `career_outcomes` operates at **4-digit CIP** granularity (XX.YY) — 390 distinct codes
- `base.cip_soc_crosswalk` operates at **6-digit CIP** granularity (XX.YYYY) — 1,949 distinct codes
- **Zero overlap** between the two

When a student types "Deaf Education" → YAML resolves to CIP 13.1003 → substitution fires → query for `career_outcomes` at unitid × cipcode 13.1003 → **no rows found** → crash. The school (ISU) reports CIP 13.10. The crosswalk maps CIP 13.1003 to SOCs 25-2051 through 25-2059. But nobody bridges the two granularities.

This affects **33 of 56 current YAML entries** (all 6-digit CIPs) and will affect every future entry targeting a 6-digit CIP. The gap is structural across all 48 CIP families — 0.0% overlap between crosswalk CIPs and career_outcomes CIPs.

Additionally, the YAML only covers 2 of 48 CIP families (Business and Education). A hackathon judge typing any non-Business, non-Education major will get no substitution benefit.

### Success Criteria

- [ ] `data/reference/major_to_cip.yaml` expanded to all 48 CIP families with SOC crosswalk coverage (~400-500 entries)
- [ ] YAML ingested as a Bronze source via Brightsmith (`raw.cip_intent_lookup`)
- [ ] Silver normalization produces resolution table joining each YAML entry to: its crosswalk SOCs, its parent CIP in `career_outcomes`, and the parent's earnings availability
- [ ] Gold consumable table `consumable.cip_intent_resolution` exists with full lineage
- [ ] Every YAML entry with a 6-digit CIP resolves to a parent 4-digit CIP that has rows in `career_outcomes` (or is explicitly flagged as uncovered)
- [ ] DQ contract: 100% of YAML entries resolve to at least one SOC via crosswalk
- [ ] DQ contract: 100% of 6-digit YAML entries have a parent CIP in `career_outcomes` (or flagged)
- [ ] MCP server updated to query `consumable.cip_intent_resolution` instead of runtime YAML lookup + substring fallback
- [ ] MCP response annotates when parent-CIP earnings are used vs. direct-CIP earnings
- [ ] `consumable.program_career_paths` backfilled with substitution-aware joins
- [ ] Illinois State + "Deaf Education" test case returns special ed teacher SOCs with ISU 13.10 earnings
- [ ] All 1,207+ pipeline tests pass
- [ ] All 171 backend service tests pass

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Gold data product, not runtime fallback | At ~500 entries, the YAML is a governed reference dataset. DQ rules catch problems at build time. Receipts trace to a governed product, not runtime substring math. | Runtime fallback in MCP server — simpler but no governance, no DQ, no lineage, problems discovered at query time not build time |
| 2 | YAML is the Bronze source | The YAML is curated reference data with a defined grain (one row per student-facing major). It follows the same Bronze → Silver → Gold pattern as every other data source. | Keep YAML as a standalone file outside the pipeline — works but no governance |
| 3 | Full 48-family YAML expansion ships with this spec | Can't predict what judges will try. 500 entries is trivial work. Disaggregation fallback must exist first or new entries are broken on arrival. | Incremental family-by-family expansion — slower, same total work |
| 4 | Parent CIP resolution via prefix truncation | Every 6-digit CIP's parent 4-digit CIP exists in career_outcomes. Confirmed by coverage gap analysis: 100% parent availability for all broken entries. | Build a separate parent-mapping reference table — unnecessary indirection |
| 5 | Earnings annotation in response | Students and receipts must know when earnings come from the broader program vs. the specific program. Transparency is a core product value. | Silent fallback — violates "Show Your Work" principle |

### Constraints

- Career_outcomes grain is immutable (unitid × cipcode × credlev at 4-digit CIP). We cannot change Scorecard's reporting granularity.
- Crosswalk grain is immutable (6-digit CIP → SOC). We cannot change NCES CIP-SOC mapping granularity.
- The resolution table bridges the two without modifying either source.

---

## §3 UI/UX Design

> SKIPPED — backend/pipeline spec. No UI changes.

---

## §4 Technical Specification

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ BRONZE                                                          │
│  raw.cip_intent_lookup ← major_to_cip.yaml (ingested as-is)   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│ SILVER                                                          │
│  base.cip_intent_resolution                                     │
│                                                                 │
│  For each YAML entry:                                           │
│   1. Resolve cip4 → crosswalk SOCs (via base.cip_soc_crosswalk)│
│   2. Determine parent CIP:                                      │
│      - If cip4 is 4-digit (XX.YY): parent = self               │
│      - If cip4 is 6-digit (XX.YYYY): parent = LEFT(cip4, 5)   │
│   3. Check parent exists in career_outcomes                     │
│   4. Flag: has_direct_earnings, has_parent_earnings,            │
│           earnings_source ("direct" | "parent" | "none")        │
│   5. Join SOC details from occupation_profiles                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│ GOLD                                                            │
│  consumable.cip_intent_resolution                               │
│                                                                 │
│  Grain: major_name × cip4 × soc_code                           │
│  One row per (YAML entry × resolved SOC)                        │
│                                                                 │
│  Contains:                                                      │
│   - Student-facing major name + aliases                         │
│   - Specific CIP (from YAML)                                   │
│   - Parent CIP (for earnings lookup)                            │
│   - SOC code + occupation title (from crosswalk)                │
│   - earnings_source flag ("direct" | "parent" | "none")        │
│   - Crosswalk match metadata (confidence, match_type)           │
│   - DQ: all entries have ≥1 SOC, all 6-digit have parent       │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│ MCP SERVER                                                      │
│                                                                 │
│  When student_major is provided:                                │
│   1. Query consumable.cip_intent_resolution for major_name      │
│      (fuzzy match against major + aliases)                      │
│   2. Get the resolved SOC codes                                 │
│   3. Get the earnings_source flag + parent_cip                  │
│   4. If earnings_source = "parent":                             │
│      query career_outcomes with parent_cip for ERN/ROI          │
│   5. If earnings_source = "direct":                             │
│      query career_outcomes with cip4 directly                   │
│   6. Annotate response with earnings_source metadata            │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 1: Expand YAML to Full Coverage

Before anything enters the pipeline, the YAML must cover all 48 CIP families. The Gold DQ rules validate coverage at build time — ingesting a partial YAML just produces a governed product that immediately fails its own contracts.

1. Query `base.cip_soc_crosswalk` for all distinct CIP codes with SOC coverage, grouped by 2-digit family
2. For each CIP with coverage, generate a YAML entry with:
   - `major`: teenager-friendly display name (not raw NCES title)
   - `cip4`: the CIP code
   - `cip_family`: 2-digit family
   - `aliases`: 2-5 common alternate names someone would naturally say — this is NOT just teenager slang. It's how normal humans refer to majors vs. how the federal government classifies them. Include: how teenagers say it ("pre-med", "CS", "poli sci"), how parents and counselors say it ("Deaf Education", "Physical Therapy"), how schools market it on their websites ("Data Analytics"), and common misspellings.
3. Skip CIP codes that are catch-all/administrative ("Other", "General") unless they're the only entry in their sub-family
4. Do not duplicate existing family 52 and family 13 entries
5. Validate: YAML parses cleanly, no duplicate major names across families

**Expected output:** ~400-500 total entries across all families.

### Phase 2: Bronze — Ingest YAML as a Source

**Table:** `raw.cip_intent_lookup`
**Source:** `data/reference/major_to_cip.yaml`
**Grain:** One row per YAML entry (one per major name)

| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| record_id | string | derived | yes | Deterministic hash of major_name |
| major_name | string | YAML `major` | yes | Student-facing display name |
| cip4 | string | YAML `cip4` | yes | Target CIP code (4-digit or 6-digit) |
| cip_family | string | YAML `cip_family` | yes | 2-digit family prefix |
| aliases | string (JSON array) | YAML `aliases` | yes | Alternate names, abbreviations |
| cip_granularity | string | derived | yes | "4-digit" or "6-digit" based on length of cip4 |
| parent_cip | string | derived | yes | If 6-digit: LEFT(cip4, 5). If 4-digit: same as cip4 |
| ingested_at | timestamp | system | yes | Ingestion timestamp |
| source_file | string | system | yes | "data/reference/major_to_cip.yaml" |
| load_date | date | system | yes | Date of load |

**Ingestor:** `CipIntentLookupIngestor` extends `BaseIngestor`. Reads YAML, flattens to rows, derives `cip_granularity` and `parent_cip`.

### Phase 3: Silver — Resolution Table

**Table:** `base.cip_intent_resolution`
**Grain:** One row per (YAML entry × resolved SOC code)

For each row in `raw.cip_intent_lookup`:

1. **Resolve SOCs:** Join `cip4` to `base.cip_soc_crosswalk`:
   - If cip4 is 4-digit: `cip4 = LEFT(crosswalk.cipcode, 5)` (existing prefix join pattern)
   - If cip4 is 6-digit: `cip4 = crosswalk.cipcode` (exact match) OR `LEFT(cip4, 5) = LEFT(crosswalk.cipcode, 5)` if exact match yields zero rows (fallback to family)
2. **Resolve parent earnings:** Check if `parent_cip` has rows in `career_outcomes` for any unitid. Set `has_parent_earnings = True/False`.
3. **Resolve direct earnings:** Check if `cip4` has rows in `career_outcomes` for any unitid. Set `has_direct_earnings = True/False`.
4. **Set earnings_source:**
   - If `has_direct_earnings`: `"direct"`
   - Elif `has_parent_earnings`: `"parent"`
   - Else: `"none"`

| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| record_id | string | derived | yes | Hash of (major_name, soc_code) |
| major_name | string | raw.cip_intent_lookup | yes | Student-facing name |
| aliases | string (JSON) | raw.cip_intent_lookup | yes | Alternate names |
| cip4 | string | raw.cip_intent_lookup | yes | Specific CIP |
| cip_family | string | raw.cip_intent_lookup | yes | 2-digit family |
| cip_granularity | string | raw.cip_intent_lookup | yes | "4-digit" or "6-digit" |
| parent_cip | string | raw.cip_intent_lookup | yes | Parent for earnings fallback |
| soc_code | string | base.cip_soc_crosswalk | yes | Resolved occupation code |
| soc_title | string | base.cip_soc_crosswalk | yes | Occupation title |
| crosswalk_cip | string | base.cip_soc_crosswalk | yes | The actual crosswalk CIP that matched |
| crosswalk_match_type | string | derived | yes | "exact_6digit" / "prefix_4digit" |
| has_direct_earnings | boolean | derived | yes | cip4 exists in career_outcomes |
| has_parent_earnings | boolean | derived | yes | parent_cip exists in career_outcomes |
| earnings_source | string | derived | yes | "direct" / "parent" / "none" |

### Phase 4: Gold — Consumable Resolution Table

**Table:** `consumable.cip_intent_resolution`
**Grain:** One row per (major_name × soc_code)
**Promote pattern:** `promote()` with `compute_grain_id(row, ['major_name', 'soc_code'], prefix='cir')`

Carries forward all Silver fields plus:

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| soc_median_wage | double | consumable.occupation_profiles | For display/validation |
| soc_ai_exposure | double | consumable.ai_exposure | For display/validation |
| soc_growth_outlook | string | consumable.occupation_profiles | For display/validation |

**DQ Rules:**

| ID | Rule | Priority | Type |
|----|------|----------|------|
| CIR-001 | Every YAML entry resolves to ≥ 1 SOC | P0 | Completeness |
| CIR-002 | Every 6-digit CIP entry has has_parent_earnings = True | P0 | Referential integrity |
| CIR-003 | No duplicate (major_name, soc_code) rows | P0 | Uniqueness |
| CIR-004 | earnings_source is never null | P0 | Completeness |
| CIR-005 | All soc_code values match XX-XXXX format | P1 | Format |
| CIR-006 | Total row count between 2,000 and 15,000 | P1 | Reasonableness |
| CIR-007 | Every CIP family (01-60) with crosswalk coverage has ≥ 1 YAML entry | P1 | Coverage |
| CIR-008 | Zero YAML entries with earnings_source = "none" (or flagged with explanation) | P1 | Completeness |

**Data Contract:** `dc-cip-intent-resolution`
- Consumer: MCP server (`futureproof_server.py`)
- Grain: major_name × soc_code
- Refresh: Event-driven (when YAML is updated)
- SLA: All P0 DQ rules pass

### Phase 5: MCP Server Update

Replace the current runtime YAML lookup + `_matched_cip_is_more_specific` + substring fallback logic in `futureproof_server.py` with a query against `consumable.cip_intent_resolution`.

**Current flow (runtime, fragile):**
1. Load YAML at startup
2. `_find_major_intent()` fuzzy matches student input against YAML
3. `_is_broad_cip()` or `_matched_cip_is_more_specific()` decides whether to substitute
4. Substitution swaps the CIP for crosswalk purposes
5. **BROKEN:** If 6-digit CIP, career_outcomes lookup fails (no rows)

**New flow (governed, precomputed):**
1. Query `consumable.cip_intent_resolution` WHERE major_name or aliases match student input
2. Get resolved SOC codes directly from the table
3. Get `earnings_source` and `parent_cip` from the table
4. If `earnings_source = "parent"`: query `career_outcomes` with `parent_cip` for ERN/ROI
5. If `earnings_source = "direct"`: query `career_outcomes` with `cip4` for ERN/ROI
6. Annotate response: `"earnings_source": "parent"`, `"earnings_cip": "13.10"`, `"earnings_note": "Earnings data is for the broader Special Education program at this school. Career paths are specific to Deaf Education (CIP 13.1003)."`

**Deprecate:** `_find_major_intent()`, `_is_broad_cip()`, `_matched_cip_is_more_specific()`, and the YAML-loading code in the MCP server. These are replaced by the Gold table query.

### Phase 6: Backfill program_career_paths

After the Gold table and MCP update are in place, backfill `consumable.program_career_paths` to include substitution-aware joins. For schools that report broad CIPs, the program_career_paths table should include rows for the specific-CIP SOCs (from the resolution table) alongside the existing broad-CIP SOC rows.

This is a re-run of the `gold-futureproof-engine` pipeline with the resolution table as an additional input. The existing prefix-join logic stays; the resolution table adds the specific-CIP paths that the prefix join misses.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `data/reference/major_to_cip.yaml` | Modify | Expand from 56 to ~400-500 entries (all 48 families) |
| `src/raw/cip_intent_lookup_ingestor.py` | Create | Bronze ingestor for YAML |
| `src/silver/cip_intent_resolution.py` | Create | Silver resolution logic |
| `src/gold/cip_intent_resolution.py` | Create | Gold promote with DQ rules |
| `src/mcp_server/futureproof_server.py` | Modify | Replace runtime YAML lookup with Gold table query |
| `tests/raw/test_cip_intent_lookup.py` | Create | Bronze ingestor tests |
| `tests/silver/test_cip_intent_resolution.py` | Create | Resolution logic tests |
| `tests/gold/test_cip_intent_resolution.py` | Create | DQ rule tests |
| `tests/mcp/test_cip_substitution.py` | Modify | Update to test new Gold-table-backed flow |

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `tests/mcp/test_cip_substitution.py` | All 18 tests | High | MCP substitution logic completely replaced |
| `backend/tests/services/` | Service tests using substitution | Medium | May reference old `_find_major_intent` interface |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `tests/mcp/test_cip_substitution.py` | Rewrite to test Gold-table-backed resolution | Old tests tested runtime YAML lookup; new tests test precomputed resolution |

#### Confirmed Safe

All other pipeline tests (1,189+ tests not related to CIP substitution) should be unaffected. If any fail, STOP and escalate.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `tests/gold/test_cip_intent_resolution.py` | `test_all_entries_resolve_to_socs` | CIR-001: every YAML entry → ≥1 SOC |
| P0 | `tests/gold/test_cip_intent_resolution.py` | `test_all_6digit_have_parent_earnings` | CIR-002: no broken 6-digit entries |
| P0 | `tests/gold/test_cip_intent_resolution.py` | `test_no_duplicate_grain` | CIR-003: unique (major_name, soc_code) |
| P0 | `tests/gold/test_cip_intent_resolution.py` | `test_earnings_source_never_null` | CIR-004: earnings_source populated |
| P0 | `tests/mcp/test_cip_substitution.py` | `test_deaf_education_isu` | End-to-end: ISU + "Deaf Education" → sped SOCs + 13.10 earnings |
| P0 | `tests/mcp/test_cip_substitution.py` | `test_6digit_fallback_annotated` | Response includes earnings_source="parent" annotation |
| P1 | `tests/gold/test_cip_intent_resolution.py` | `test_all_families_covered` | CIR-007: every family with crosswalk data has entries |
| P1 | `tests/raw/test_cip_intent_lookup.py` | `test_yaml_parses_cleanly` | YAML loads without errors |
| P1 | `tests/raw/test_cip_intent_lookup.py` | `test_no_duplicate_major_names` | No ambiguous entries |
| P1 | `tests/mcp/test_cip_substitution.py` | `test_4digit_direct_match` | 4-digit CIPs still work (Business entries) |

#### Test Data Requirements

- YAML file with known entries for test assertions
- Silver crosswalk fixture with known CIP → SOC mappings
- Career_outcomes fixture with known 4-digit CIP rows
- ISU (unitid 145813) test fixture with CIP 13.10 data

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
[Filled in by @fp-data-reviewer — crosswalk coverage, earnings fallback integrity, lineage chain]
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
[Any divergence from §4 and why]

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
| pytest | | | | |

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@design-builder)
**Status:** SKIPPED (backend/pipeline spec)

### Code Review (@faang-staff-engineer)
**Status:** PENDING
#### Findings
[Filled in by reviewer]
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
| Tests (pytest) | |
| Service tests | |

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

**Context for agents:**

This spec formalizes the CIP intent substitution system as a governed data product. The key insight is that `career_outcomes` (4-digit CIP) and the crosswalk (6-digit CIP) have zero overlap, so any substitution targeting a 6-digit CIP needs a parent-CIP fallback for earnings. This was validated in five spikes (see Related Specs).

The YAML expansion to all 48 families is trivial but load-bearing — judges will type unpredictable majors. The disaggregation fallback (specific CIP's SOCs + parent CIP's earnings) is the mechanism that makes the full expansion work.

The receipts story is strong here: every determination traces from MCP → Gold (`consumable.cip_intent_resolution`) → Silver (resolution logic) → Bronze (YAML source) → the human-curated YAML entry. When parent earnings are used, the receipt explicitly says so with the parent CIP identified. No silent fallbacks.

**Dependency note:** The existing runtime substitution code in `futureproof_server.py` (`_find_major_intent`, `_is_broad_cip`, `_matched_cip_is_more_specific`) should continue to work during implementation. Only deprecate after the Gold table path is verified end-to-end. Implement the Gold path alongside the existing code, swap over, then remove the old code.

**Test case that must pass before marking COMPLETE:**
```
School: Illinois State University (unitid 145813)
Student major: "Deaf Education"
Expected: Career paths from CIP 13.1003 crosswalk (SOCs 25-2051 through 25-2059)
Expected: Earnings from CIP 13.10 (ISU's reported Special Education data)
Expected: Response annotates earnings_source = "parent", earnings_cip = "13.10"
```

---
