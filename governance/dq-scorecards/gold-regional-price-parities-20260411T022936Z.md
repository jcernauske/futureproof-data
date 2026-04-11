## DQ Scorecard: gold-regional-price-parities
**Spec:** gold-regional-price-parities
**Date:** 2026-04-11
**Agent:** @dq-engineer
**Overall Score:** 55/55 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-04-11T02:29:36.184197+00:00)
**Run ID:** ddabd852

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| GLD-RPP-001 | volume | P0 | consumable.regional_price_parities must contain exactly 51 rows — the closed set of 50 U.S. states plus the District of Columbia. The Gold transformer is a row-for-row derivation from the 51-row Silver table; any deviation indicates a dedup bug, a dropped row, or a double-load. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-RPP-002 | completeness | P0 | state_fips is the natural key of consumable.regional_price_parities and drives every lookup and join into this table. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-003 | uniqueness | P0 | state_fips is the declared dedup grain of consumable.regional_price_parities. Any duplicate indicates a promote-pattern dedup failure. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-004 | validity | P0 | state_fips must be a 2-character zero-padded numeric string (e.g., '06' California, '11' DC). Catches float coercion regressions where '06' decays to '6' or '6.0'. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-005 | validity | P0 | Every row's state_fips must be in the canonical 51-member set of FIPS codes assigned to the 50 U.S. states plus DC (FIPS 11). The set intentionally contains gaps at 03, 07, 14, 43, and 52 — those codes are unassigned in the federal FIPS standard. A format-only regex is insufficient because it would admit bogus codes like '99', '03', or '43'. Mirrors SIL-BEA-039 which closed Silver chaos Gap 2. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-RPP-006 | completeness | P0 | state_name is the human-readable display name required by the frontend and the data contract. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-007 | consistency | P0 | Every state_fips must map to exactly one state_name and vice versa. Bijection failure means either a duplicate state_name or a drift in the 51-row expected set. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-RPP-008 | completeness | P0 | state_abbr is the USPS 2-letter code the frontend and MCP tools use as the primary state key. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-009 | validity | P0 | USPS abbreviations are always 2 uppercase ASCII letters. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-010 | validity | P0 | state_abbr must come from the canonical 51-member USPS set (50 states + DC). Rejects unexpected territory codes (PR, GU, VI, AS, MP). | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-011 | uniqueness | P0 | 51 rows must yield 51 distinct USPS abbreviations. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-RPP-012 | consistency | P0 | Every state_fips must map to exactly one state_abbr and vice versa. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-RPP-013 | completeness | P0 | census_region is a required carry-forward from Silver. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-014 | validity | P0 | census_region is a closed 4-value enum per the U.S. Census Bureau convention. DC is intentionally placed in 'South' per Census quirk. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-015 | completeness | P0 | All four U.S. Census regions must appear in the output. Catches a regression where an entire region's states drop. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-RPP-016 | completeness | P0 | rpp_all_items is the core measure driving every Gold derivation (cost_tier, adjusted_Nk). Null breaks all downstream calculations. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-017 | validity | P0 | Gold sanity bound for the RPP index on the national=100 scale, matching the Silver bound. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-018 | completeness | P0 | purchasing_power_multiplier is the pre-computed salary scaling factor used by every adjusted_Nk derivation. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-019 | validity | P0 | Gold sanity bound on the pre-computed salary multiplier. The bound [0.7, 1.3] is the inverse of the rpp_all_items bound [70, 130] / 100. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-020 | consistency | P0 | Mathematical derivation invariant: the multiplier is defined as 100.0 / rpp_all_items, so multiplier × rpp_all_items must equal 100.0 for every row. Tolerance of 0.01 is a deliberate robustness margin — the observed Gold deviation is 1.42e-14. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-021 | completeness | P0 | cost_tier is derived at Gold via a CASE expression with a final ELSE branch, so it cannot legitimately be null. Null means the transformer wrote a null before the derivation was applied. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-022 | validity | P0 | cost_tier is a closed 5-value enum per the frozen BT-106 definition. The CASE expression in the transformer can only emit these 5 values; any other value means either the transformer was hand-edited or the column was corrupted post-write. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-023 | consistency | P0 | For every row, the persisted cost_tier must equal the result of the canonical CASE expression applied to the row's rpp_all_items. The SQL re-runs the frozen classifier (breakpoints 108, 103, 97, 91, left-closed) and counts mismatches. This is the single most important derivation-correctness rule at Gold — it catches any breakpoint drift, any tier-label typo, any off-by-one in the left-closed semantics, and any boundary-flip regression on the 17 states that sit within 1.0 RPP of a breakpoint. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-RPP-024 | consistency | P0 | Tennessee sits exactly on the 91.0 breakpoint between 'very_low' and 'low'. Under the frozen left-closed convention (`rpp >= 91.0` → 'low'), TN must be classified as 'low', not 'very_low'. This is a dedicated witness rule for the left-closed semantics: any accidental swap to right-closed (`rpp > 91.0`) would flip TN from 'low' to 'very_low' and this rule would fire. Hardens GLD-RPP-023 against a specific regression that is otherwise hard to spot. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-025 | completeness | P0 | adjusted_30k is derived at Gold from a non-null purchasing_power_multiplier and cannot legitimately be null. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-026 | consistency | P0 | Every adjusted_30k must equal `round(30000.0 * purchasing_power_multiplier, 2)` within 0.01. Robustness tolerance kept at spec value despite EDA max delta = 0.0. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-027 | completeness | P0 | adjusted_50k is the canonical salary benchmark used by the frontend salary-adjustment UI. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-028 | consistency | P0 | Every adjusted_50k must equal `round(50000.0 * purchasing_power_multiplier, 2)` within 0.01. Robustness tolerance kept at spec value despite EDA max delta = 0.0. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-029 | completeness | P0 | adjusted_75k is a non-null Gold derivation. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-030 | consistency | P0 | Every adjusted_75k must equal `round(75000.0 * purchasing_power_multiplier, 2)` within 0.01. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-031 | completeness | P0 | adjusted_100k is a non-null Gold derivation. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-032 | consistency | P0 | Every adjusted_100k must equal `round(100000.0 * purchasing_power_multiplier, 2)` within 0.01. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-033 | consistency | P0 | California is a high-cost state (rpp_all_items=110.7, ppm<1.0), so adjusted_50k must be strictly less than $50,000. Catches any sign-flip or inversion in the multiplier. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-034 | consistency | P0 | Iowa is a low-cost state (rpp_all_items=87.8, ppm>1.0), so adjusted_50k must be strictly greater than $50,000. Paired with GLD-RPP-033 this proves the multiplier is oriented correctly. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-035 | validity | P0 | verification_status is a closed 2-value enum carried forward from Silver per Bronze staff-review Condition 7. Surfaces per-row provenance on every Gold row. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-036 | consistency | P0 | The current Silver verification state has exactly 8 BEA-verified rows (CA, HI, DC, NJ, AR, MS, IA, OK). Gold must honor that contract and not claim more or less verification than Silver. When the live BEA API refresh lands post-hackathon, this rule flips to '= 51' in lockstep with SIL-BEA-023. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-RPP-037 | consistency | P0 | The 8 BEA-verified state_fips values are a fixed allow-list: {'05','06','11','15','19','28','34','40'} (AR, CA, DC, HI, IA, MS, NJ, OK). Any other FIPS with verification_status='bea_official' at Gold means the Condition 7 carry-forward has drifted from Silver. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-038 | completeness | P0 | record_id is the deterministic surrogate key produced by compute_grain_id(row, ['state_fips'], prefix='rpc'). Null means the grain ID helper failed. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-039 | uniqueness | P0 | record_id is the primary key of consumable.regional_price_parities. Duplicate means either a state_fips collision or a hash collision (extraordinarily unlikely with SHA-256). | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-040 | validity | P0 | record_id must follow the canonical `rpc-` prefix format (16 lowercase hex chars). The `rpc` prefix distinguishes Gold consumable record_ids from Silver's `rpp-` prefix — any row with a mismatched prefix means the compute_grain_id call was passed the wrong prefix argument. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-041 | validity | P0 | This Gold table mirrors the Silver single-vintage contract. Every row must carry data_year=2024. When the BEA releases a new vintage, Bronze/Silver/Gold rules bump to the new target year in lockstep. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-042 | consistency | P0 | consumable.regional_price_parities uses full-table-replacement supersession, not SCD2. At any point in time the table must contain exactly one data_year. Multiple years means either the replacement strategy broke or rows from a stale load leaked through. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-RPP-043 | referential_integrity | P0 | Each of {state_name, state_abbr, census_region, rpp_all_items, purchasing_power_multiplier, verification_status, data_year} in Gold must equal the Silver row's value for the same state_fips (joined to the Gold-native state_fips itself, which is implicitly covered by the INNER resolution). Gold is a pure passthrough for these 8 columns (state_fips included as the join key); the 4 added columns (cost_tier, adjusted_30k/50k/75k/100k) are derivations and are validated separately by GLD-RPP-023, GLD-RPP-026, GLD-RPP-028, GLD-RPP-030, GLD-RPP-032. The join returns all Gold rows LEFT-joined to Silver and counts any row where (a) the Silver match is missing or (b) any carried-forward column differs. Floating-point columns use a 1e-9 tolerance to avoid spurious diffs from DOUBLE round-trips (same tolerance as SIL-BEA-018). | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-RPP-044 | validity | P0 | California spot check against the spec's BEA-verified value table. rpp_all_items=110.7 → cost_tier='very_high', adjusted_50k=$45,167.12. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-045 | validity | P0 | Hawaii spot check. rpp_all_items=110.0 → cost_tier='very_high', adjusted_50k=$45,454.55. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-046 | validity | P0 | District of Columbia spot check. rpp_all_items=109.9 → cost_tier='very_high', adjusted_50k=$45,495.91. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-047 | validity | P0 | New Jersey spot check. rpp_all_items=108.8 → cost_tier='very_high', adjusted_50k=$45,955.88. NJ is the only bea_official row near a breakpoint (+0.80 above 108.0) and anchors the very_high lower boundary. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-048 | validity | P0 | Arkansas spot check — lowest-cost state, highest adjusted_50k. rpp_all_items=86.9 → cost_tier='very_low', adjusted_50k=$57,537.40. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-049 | validity | P0 | Mississippi spot check. rpp_all_items=87.0 → cost_tier='very_low', adjusted_50k=$57,471.26. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-050 | validity | P0 | Iowa spot check. rpp_all_items=87.8 → cost_tier='very_low', adjusted_50k=$56,947.61. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-051 | validity | P0 | Oklahoma spot check. rpp_all_items=87.8 → cost_tier='very_low', adjusted_50k=$56,947.61. Note: IA and OK legitimately tie at rpp=87.8. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-052 | completeness | P1 | All 5 cost_tier values ('very_high','high','average','low','very_low') must be present in the output. Soft coverage guarantee: the current data has 51 states spread across all 5 tiers and the distribution is stable enough that any refresh that collapses to 4 tiers is worth investigating. Not pinned to exact per-tier counts because estimates may shift on refresh. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-RPP-053 | coverage | P1 | Explicit per-tier coverage check: each of the 5 cost_tier values must have at least 1 row. Complementary to GLD-RPP-052's distinct-count rule — this one surfaces which specific tier is empty, rather than just that total distinct < 5. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-RPP-054 | completeness | P1 | promoted_at is the Gold promotion timestamp. Non-null only; never pinned to a specific value because it changes every run. Replaces Silver's ingested_at/source_load_date metadata pair. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-RPP-055 | freshness | P1 | The upstream Silver table base.bea_rpp must have been loaded within the last 400 days. This enforces a soft vintage staleness bound: BEA publishes RPPs on an annual cadence (roughly December of year N+1 for vintage N), so 400 days covers one full vintage cycle plus a 35-day grace period. Any value > 400 days stale means a vintage refresh has been missed. | PASS | actual=0.0, threshold=result = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
| completeness | 15 | 15 | 100% |
| consistency | 14 | 14 | 100% |
| coverage | 1 | 1 | 100% |
| freshness | 1 | 1 | 100% |
| referential_integrity | 1 | 1 | 100% |
| uniqueness | 3 | 3 | 100% |
| validity | 19 | 19 | 100% |
| volume | 1 | 1 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.

