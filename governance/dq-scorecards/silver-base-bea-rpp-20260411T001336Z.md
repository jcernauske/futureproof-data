## DQ Scorecard: silver-base-bea-rpp
**Spec:** silver-base-bea-rpp
**Date:** 2026-04-11
**Agent:** @dq-engineer
**Overall Score:** 38/38 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-04-11T00:13:36.915249+00:00)
**Run ID:** ef5a8a52

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| SIL-BEA-001 | volume | P0 | base.bea_rpp must contain exactly 51 rows — the closed set of 50 U.S. states plus the District of Columbia. The Silver transformer is a 1:1 passthrough of the 51-row Bronze table; any deviation indicates a dedup bug, a dropped row, or a double-load. | PASS | actual=0.0, threshold=result = 0.0 |
| SIL-BEA-002 | completeness | P0 | state_fips is the natural key of base.bea_rpp and drives every downstream lookup (state_abbr, census_region, verification_status derivations). | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-003 | uniqueness | P0 | state_fips is the declared dedup grain of base.bea_rpp. Any duplicate indicates a promote-pattern dedup failure. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-004 | validity | P0 | state_fips must be a 2-character zero-padded numeric string (e.g., '06' California, '11' DC). Catches float coercion regressions where '06' decays to '6' or '6.0'. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-005 | completeness | P0 | state_name is the human-readable display name required by the frontend and the data contract. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-006 | consistency | P0 | Every state_fips must map to exactly one state_name and vice versa. Bijection failure means either (a) a duplicate state_name (two FIPS codes sharing a display name) or (b) a drift in the 51-row expected set. | PASS | actual=0.0, threshold=result = 0.0 |
| SIL-BEA-007 | completeness | P0 | state_abbr is the USPS 2-letter code the frontend and MCP tools use as the primary state key. Null means a FIPS value was not found in the FIPS_TO_USPS in-code lookup. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-008 | validity | P0 | USPS abbreviations are always 2 uppercase ASCII letters. Catches whitespace, casing, or truncation regressions in the FIPS_TO_USPS lookup. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-009 | validity | P0 | state_abbr must come from the canonical 51-member USPS set (50 states + DC). Rejects unexpected territory codes (PR, GU, VI, AS, MP) or corrupted lookups. The IN list is the exact output of the in-code FIPS_TO_USPS constant and includes DC. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-010 | uniqueness | P0 | 51 rows must yield 51 distinct USPS abbreviations. Enforces uniqueness without relying on GROUP BY (which the Iceberg engine would evaluate separately). | PASS | actual=0.0, threshold=result = 0.0 |
| SIL-BEA-011 | consistency | P0 | Every state_fips must map to exactly one state_abbr and vice versa. Bijection failure indicates a FIPS_TO_USPS lookup collision or an unexpected FIPS value. | PASS | actual=0.0, threshold=result = 0.0 |
| SIL-BEA-012 | completeness | P0 | census_region is derived from the FIPS_TO_CENSUS_REGION in-code lookup. Null means a state_fips missed the lookup — a hard bug. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-013 | validity | P0 | census_region is a closed 4-value enum per the U.S. Census Bureau convention. DC is intentionally placed in 'South' per Census quirk — this rule accepts that mapping. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-014 | completeness | P0 | All four U.S. Census regions must appear in the output. Coverage check that catches a regression where, e.g., the 9 Northeast states all dropped to 'South'. | PASS | actual=0.0, threshold=result = 0.0 |
| SIL-BEA-015 | consistency | P1 | The 51 rows must split across regions exactly as {Northeast: 9, Midwest: 12, South: 17, West: 13}. These are structural properties of U.S. Census geography (with DC in South) and will not change across refreshes. Catches silent drift in the FIPS_TO_CENSUS_REGION lookup table. | PASS | actual=0.0, threshold=result = 0.0 |
| SIL-BEA-016 | completeness | P0 | rpp_all_items is the core measure of base.bea_rpp. Null breaks every downstream salary adjustment. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-017 | validity | P0 | Silver sanity bound for the RPP index on the national=100 scale. Kept wider than the Bronze bound [80,130] to give Silver equal headroom on both sides of 100. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-018 | referential_integrity | P0 | Every Silver row's rpp_all_items must equal the Bronze row's rpp_all_items for the same state identity. Silver is a pure passthrough for this column — the test is that no row is missing from Bronze AND no row has been silently rescaled or rounded. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-019 | completeness | P0 | purchasing_power_multiplier is the pre-computed salary scaling factor used by every downstream consumer. Null would mean a divide-by-zero or a rpp_all_items null that escaped SIL-BEA-016. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-020 | validity | P0 | Silver sanity bound on the pre-computed salary multiplier. The bound [0.7, 1.3] is the inverse of the rpp_all_items bound [70, 130] / 100. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-021 | consistency | P0 | Mathematical derivation invariant: the multiplier is defined as 100.0 / rpp_all_items, so multiplier × rpp_all_items must equal 100.0 for every row. Tolerance of 0.01 is a deliberate robustness margin — the observed deviation in the dry-run was 1.42e-14, twelve orders of magnitude tighter than the threshold. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-022 | validity | P0 | verification_status is a closed 2-value enum. Closes Bronze HIGH-3 per staff-review Condition 6 by surfacing per-row provenance on every Silver row. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-023 | consistency | P0 | The current Bronze verification state has exactly 8 BEA-verified rows (CA, HI, DC, NJ, AR, MS, IA, OK). Silver must honor that contract and not claim more verification than Bronze has. When the live BEA API refresh lands post-hackathon, this rule flips to '= 51' and the rest of the pipeline is refresh-ready without further schema changes. | PASS | actual=0.0, threshold=result = 0.0 |
| SIL-BEA-024 | consistency | P0 | The 8 BEA-verified state_fips values are a fixed allow-list: {'05','06','11','15','19','28','34','40'} (AR, CA, DC, HI, IA, MS, NJ, OK). Any other FIPS with verification_status='bea_official' means the BEA_VERIFIED_FIPS set in the transformer has drifted. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-025 | completeness | P0 | record_id is the deterministic surrogate key produced by compute_grain_id(row, ['state_fips'], prefix='rpp'). Null means the grain ID helper failed. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-026 | uniqueness | P0 | record_id is the primary key of base.bea_rpp. Duplicate means either a state_fips collision or a grain-ID hash collision (extraordinarily unlikely with SHA-256). | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-027 | validity | P0 | This Silver table mirrors the Bronze single-vintage contract (RAW-BEA-006). Every row must carry data_year=2024. When the BEA releases a new vintage, both Bronze and Silver rules bump to the new target year in lockstep. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-028 | consistency | P0 | base.bea_rpp uses full-table-replacement supersession, not SCD2. At any point in time the table must contain exactly one data_year. Multiple years means either the replacement strategy broke or rows from a stale load leaked through. | PASS | actual=0.0, threshold=result = 0.0 |
| SIL-BEA-029 | completeness | P1 | source_load_date is a required provenance column carried from Bronze load_date. Non-null only; never pinned to an exact value because it changes on every load. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-030 | completeness | P1 | ingested_at is the Silver promotion timestamp. Non-null only; never pinned to a specific value because it changes every run. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-031 | validity | P0 | California spot check against the spec's BEA-verified value table. rpp_all_items=110.7 → multiplier=0.9034 within ±0.001. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-032 | validity | P0 | Hawaii spot check. rpp_all_items=110.0 → multiplier=0.9091 within ±0.001. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-033 | validity | P0 | District of Columbia spot check. rpp_all_items=109.9 → multiplier=0.9099 within ±0.001. DC in 'South' is the documented Census convention quirk and is correct. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-034 | validity | P0 | New Jersey spot check. rpp_all_items=108.8 → multiplier=0.9191 within ±0.001. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-035 | validity | P0 | Arkansas spot check — lowest-cost state. rpp_all_items=86.9 → multiplier=1.1507 within ±0.001. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-036 | validity | P0 | Mississippi spot check. rpp_all_items=87.0 → multiplier=1.1494 within ±0.001. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-037 | validity | P0 | Iowa spot check. rpp_all_items=87.8 → multiplier=1.1390 within ±0.001. | PASS | actual=0, threshold=result_count = 0.0 |
| SIL-BEA-038 | validity | P0 | Oklahoma spot check. rpp_all_items=87.8 → multiplier=1.1390 within ±0.001. Note: IA and OK legitimately tie at rpp=87.8 (same Bronze dedup tie). | PASS | actual=0, threshold=result_count = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
| completeness | 10 | 10 | 100% |
| consistency | 7 | 7 | 100% |
| referential_integrity | 1 | 1 | 100% |
| uniqueness | 3 | 3 | 100% |
| validity | 16 | 16 | 100% |
| volume | 1 | 1 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.

