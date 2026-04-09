## DQ Scorecard: raw-ingest-onet
**Spec:** raw-ingest-onet
**Date:** 2026-04-08
**Agent:** @dq-engineer
**Overall Score:** 40/40 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-04-08T03:22:33.152167+00:00)
**Run ID:** 88582a2d

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| RAW-ONET-001 |  | P0 | Every onet_soc_code must match the O*NET-SOC format XX-XXXX.XX (two digits, hyphen, four digits, period, two digits). Deviation indicates a parsing or coercion failure in the ingestor. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-002 |  | P0 | onet_soc_code is the grain field and primary key. Must be present in every row. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-003 |  | P0 | Every occupation must have a title. Required field per schema. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-004 |  | P0 | Every occupation must have a description. Required field per schema. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-005 |  | P0 | The declared grain is one row per O*NET-SOC code. Any duplicate indicates an ingestor dedup failure. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-006 |  | P1 | O*NET 30.2 has 1,016 occupations. Range allows roughly 10% variation across quarterly releases. A count outside this range suggests a download failure or source format change. | PASS | actual=0.0, threshold=result = 0.0 |
| RAW-ONET-007 |  | P1 | The load_date should be recent (within 30 days of query execution). Stale data suggests the pipeline has not been refreshed. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-008 |  | P0 | Every onet_soc_code in Task Statements must match O*NET-SOC format XX-XXXX.XX. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-009 |  | P0 | task_id is part of the grain (onet_soc_code x task_id). Must be present in every row. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-010 |  | P0 | Every task statement must have a non-empty task description text. This is the core content of the table. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-011 |  | P1 | task_type must be one of 'Core', 'Supplemental', or 'n/a' (analyst-derived tasks). The 'n/a' value correlates 1:1 with domain_source='Analyst' (845 rows, 4.5%). | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-012 |  | P0 | Every onet_soc_code in Task Statements must exist in the Occupation Data master table. Orphan SOC codes indicate a data integrity failure. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-013 |  | P1 | O*NET 30.2 has 18,796 task statements. Task lists evolve with rolling updates so a wider range is appropriate. | PASS | actual=0.0, threshold=result = 0.0 |
| RAW-ONET-014 |  | P0 | Every onet_soc_code in Work Activities must match O*NET-SOC format XX-XXXX.XX. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-015 |  | P0 | The declared grain is one row per occupation x activity x scale. Any duplicate indicates an ingestor dedup failure. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-016 |  | P0 | Importance (IM) scale ratings must be in the range [1.0, 5.0] per O*NET Scales Reference. Values outside this range indicate data corruption or parsing failure. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-017 |  | P0 | Level (LV) scale ratings must be in the range [0.0, 7.0] per O*NET Scales Reference. 0.0 indicates 'not relevant'. Values outside this range indicate data corruption. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-018 |  | P0 | Work Activities uses exactly two scales: IM (Importance) and LV (Level). Any other scale_id indicates data contamination or source format change. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-019 |  | P1 | recommend_suppress must be 'Y' (suppress recommended), 'N' (reliable), or 'n/a' (not applicable for expert/analyst sources). O*NET uses this as its primary data quality signal. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-020 |  | P0 | Every onet_soc_code in Work Activities must exist in the Occupation Data master table. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-021 |  | P1 | O*NET 30.2 has 73,308 work activity rows (894 occupations x 41 activities x 2 scales = 73,308). Row count is very stable as it is a product of fixed structure. | PASS | actual=0.0, threshold=result = 0.0 |
| RAW-ONET-022 |  | P0 | Every onet_soc_code in Work Context must match O*NET-SOC format XX-XXXX.XX. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-023 |  | P0 | The grain includes category because CXP/CTP scales produce multiple rows per element (one per response category). The composite key onet_soc_code x element_id x scale_id x category must be unique. Note: category is NULL for CX/CT point-estimate rows. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-024 |  | P0 | Work Context uses exactly four scales: CX (context 5-point), CT (context 3-point), CXP (context 5-category percentage), CTP (context 3-category percentage). Any other value indicates source format change. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-025 |  | P0 | CX (context point estimate) scale ratings must be in [1.0, 5.0]. These are single-value ratings for 5-point context dimensions. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-026 |  | P0 | CT (context 3-point estimate) scale ratings must be in [1.0, 7.0]. EDA observed range 1.00-3.00 for the 2 current CT elements, but the O*NET scale system allows up to 7.0 for context scales. Using the wider domain range for forward compatibility. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-027 |  | P0 | CXP and CTP are percentage scales representing the proportion of respondents choosing each response category. Values must be in [0.0, 100.0]. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-028 |  | P1 | CXP and CTP rows represent specific response categories and must have a category value (1-5 for CXP, 1-3 for CTP). A null category on a percentage row means the category-percentage structure is broken. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-029 |  | P0 | Every onet_soc_code in Work Context must exist in the Occupation Data master table. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-030 |  | P1 | O*NET 30.2 has 297,676 work context rows. This is 6x the original spec estimate due to CXP/CTP category-percentage rows. Row count is relatively stable as it is driven by the fixed 57-element taxonomy. | PASS | actual=0.0, threshold=result = 0.0 |
| RAW-ONET-031 |  | P0 | Every source onet_soc_code must match O*NET-SOC format XX-XXXX.XX. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-032 |  | P0 | Every related_onet_soc_code must match O*NET-SOC format XX-XXXX.XX. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-033 |  | P0 | The declared grain is one row per source-related occupation pair. Any duplicate indicates an ingestor dedup failure. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-034 |  | P0 | Related index must be in [1, 20]. Index 1-5 = Primary-Short, 6-10 = Primary-Long, 11-20 = Supplemental. Values outside this range indicate data corruption. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-035 |  | P0 | is_primary must be true for index 1-10 (Primary-Short and Primary-Long) and false for index 11-20 (Supplemental). This is derived by the ingestor from the Relatedness Tier column. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-036 |  | P0 | An occupation must not be listed as related to itself. Self-references are domain-impossible. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-037 |  | P0 | Every source onet_soc_code in Related Occupations must exist in the Occupation Data master table. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-038 |  | P0 | Every related_onet_soc_code must also exist in the Occupation Data master table. This ensures related occupations are not orphan references. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-039 |  | P1 | Every source occupation should have exactly 20 related occupations (10 primary + 10 supplemental). O*NET 30.2 data is perfectly uniform at 20 per occupation. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-ONET-040 |  | P1 | O*NET 30.2 has 18,460 related occupation rows (923 x 20). Row count scales with the number of occupations surveyed. | PASS | actual=0.0, threshold=result = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
|  | 40 | 40 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.

