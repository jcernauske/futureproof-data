## DQ Scorecard: raw-ingest-bea-rpp
**Spec:** raw-ingest-bea-rpp
**Date:** 2026-04-10
**Agent:** @dq-engineer
**Overall Score:** 19/19 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-04-10T22:33:36.177127+00:00)
**Run ID:** 1170adf0

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| RAW-BEA-001 |  | P0 | The BEA SARPP table at LineCode=1 (All Items), Year=2024, GeoFips=STATE returns exactly 51 geographic entities: 50 U.S. states plus the District of Columbia. Any other count indicates the ingestor dropped rows, double-loaded, or picked up metro-level GeoFips values. | PASS | actual=0.0, threshold=result = 0.0 |
| RAW-BEA-002 |  | P0 | rpp_all_items is the single core measure of this reference table. Every row must have a numeric value; null means a parse failure in the ingestor (BEA DataValue field arrived as a string that could not be coerced to float). | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-BEA-003 |  | P0 | BEA's historical range of state-level All Items RPPs over the last decade has been ~85-113. The [80.0, 130.0] guardrail gives ~5 point headroom below the historical floor and ~17 point headroom above the historical ceiling. Any value outside this range signals a unit error, decimal-point parse error, or a non-state GeoFips leaking into the load. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-BEA-004 |  | P0 | geo_fips is the declared dedup grain (one row per state FIPS). Any duplicate indicates a dedup failure in the ingestor or a double-append to the Iceberg table. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-BEA-005 |  | P0 | geo_name is the human-readable state/DC name. Required by schema. Null indicates a BEA API response parse failure. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-BEA-006 |  | P0 | This load targets the BEA SARPP Year=2024 release (published February 2026). Every row must carry data_year=2024. On annual refresh, bump this rule to the new target year. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-BEA-007 |  | P0 | Sanity spot-check against a known high-cost state. California's RPP has ranged ~108.5-111.0 over the past 5 BEA publications. The [108.0, 115.0] window covers that history with generous upside headroom. A value outside this window means the row for CA is stale, mis-keyed, or corrupted. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-BEA-008 |  | P0 | Sanity spot-check against a known lowest-cost state. Arkansas's RPP has ranged ~85.6-87.9 over the past decade. The [84.0, 90.0] window covers that history with headroom on both sides. A value outside this window means the row for AR is stale, mis-keyed, or corrupted. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-BEA-009 |  | P0 | District of Columbia is not a state but BEA includes it in SARPP at FIPS=11. Many state-only filters accidentally drop DC. This rule guards against that regression -- the row count rule (RAW-BEA-001) would still catch a total miscount, but this rule points directly at the DC-specific failure mode. | PASS | actual=0.0, threshold=result = 0.0 |
| RAW-BEA-010 |  | P0 | The canonical set of 51 2-digit FIPS codes for the 50 states + DC. Note intentional gaps at 03, 07, 14, 43, 52 (unassigned FIPS codes). This rule catches silent single-row drops that the row count rule alone would not distinguish from a double-load offset, AND it rejects unexpected FIPS codes (e.g., territories like PR=72, metro-area codes) that happen to land at count 51 by coincidence. | PASS | actual=0.0, threshold=result = 0.0 |
| RAW-BEA-011 |  | P1 | geo_fips must be a 2-character string of exactly two decimal digits (e.g., '06', not '6' or '06.0'). This catches float coercion errors (where '06' becomes 6.0) and zero-padding regressions. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-BEA-012 |  | P1 | source_method is a provenance signal with exactly two allowed values per spec: 'bea_api' (live BEA API call succeeded) or 'csv_cache' (fell back to cached CSV at data/raw/bea_cache/bea_rpp_2024.csv). The rule uses an IN list rather than an equality because the current load is 100% csv_cache but a future load with a working BEA_API_KEY will be 100% bea_api. Both are valid steady states; neither should be pinned. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-BEA-013 |  | P1 | source_url captures the BEA API URL (with API key redacted) that logically sourced this row, regardless of whether the live API call or the CSV fallback was used. Required by schema and by downstream lineage/contract consumers. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-BEA-014 |  | P1 | load_date is a required provenance column (date of the batch load). This rule enforces non-null only; it deliberately does NOT pin load_date to a specific value because it is a load-batch stamp that changes on every ingest run. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-BEA-015 |  | P1 | ingested_at is a required provenance column (timestamp of the batch load). Non-null only; never pinned to an exact value because the ingested_at stamp is constant within a load but changes between loads. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-BEA-016 |  | P2 | BEA publishes RPPs annually (each February for the prior year). A 400-day freshness window allows one full BEA release cycle of slack before raising a stale-data signal. This is intentionally looser than the 30-day freshness rules used for quarterly sources (College Scorecard, BLS OOH, O*NET) because RPP data has no within-year revisions and no business need for monthly refresh. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-BEA-017 |  | P2 | A simple arithmetic mean of all 51 state RPPs should land near but not exactly at the BEA national baseline of 100.0 because the baseline is population-weighted while the simple mean is not. Historically this value sits in the ~96-98 range. The [94.0, 100.0] window tolerates both the current estimates-in-place state (observed 96.98) and a future live-BEA refresh while still catching catastrophic unit errors that a pointwise range rule might miss. | PASS | actual=0.0, threshold=result = 0.0 |
| RAW-BEA-018 |  | P2 | The cheapest state in BEA's last decade of publications has been Arkansas or Mississippi in the ~85.6-87.9 range. Floor of 84.0 gives ~1.6 point headroom below the historical floor. Complements the pointwise range rule (RAW-BEA-003) by monitoring the tail directly. | PASS | actual=0.0, threshold=result = 0.0 |
| RAW-BEA-019 |  | P2 | The most expensive state in BEA's last decade has been California (peak ~113 in 2013). Ceiling of 115.0 gives ~2 point headroom above the historical ceiling. Complements RAW-BEA-003 and RAW-BEA-007 by monitoring the upper tail directly. | PASS | actual=0.0, threshold=result = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
|  | 19 | 19 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.

