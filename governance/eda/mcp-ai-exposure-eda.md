## EDA Report: MCP Tool get_ai_exposure
**Source:** consumable.ai_exposure (389 rows, Gold zone)
**Date:** 2026-04-09
**Agent:** @data-analyst
**Record Count:** 389 (backing table)
**Response Field Count:** 7

### Domain Context
**Layer:** MCP (Zone 5) -- read-only tool serving governed Gold data to AI agents
**Primary Entity:** SOC occupation with AI exposure score
**Access Pattern:** Point lookup by soc_code (single row)
**Transformation:** None -- direct passthrough from consumable.ai_exposure

### Key Findings

- **Direct passthrough, no transformation.** The MCP tool queries consumable.ai_exposure by soc_code and returns 7 of 9 Gold columns verbatim. record_id and promoted_at are excluded as pipeline metadata not needed by consumers.
- **7 response fields:** soc_code, occupation_title, exposure_score, stat_res, boss_ai_score, rationale, category. All non-null in the backing table (0% null rate across all fields).
- **389 rows addressable.** Every row has a unique soc_code in XX-XXXX format. The tool returns at most 1 row per query.
- **Null case is well-defined.** When a soc_code is not found (invalid format, nonexistent, empty), the tool returns `{"data": null, "message": "..."}` with governance metadata.
- **Eval set covers 62 cases across 5 categories:** 34 point lookups, 8 comparisons, 5 rankings, 7 aggregations, 8 edge cases. Edge cases include invalid SOC format, nonexistent SOC, empty string, partial code, and format without hyphen.
- **No data quality risk at MCP layer.** All quality guarantees are enforced by the 15 Gold-zone DQ rules on consumable.ai_exposure (GLD-AIE-001 through GLD-AIE-015). The MCP tool inherits these.

### Response Field Profiles

#### soc_code
- **Type:** STRING
- **Null Rate:** 0% (guaranteed by Gold NOT NULL constraint)
- **Cardinality:** 389 distinct (100% unique, this is the lookup key)
- **Pattern:** XX-XXXX (regex `^\d{2}-\d{4}$`)

#### occupation_title
- **Type:** STRING
- **Null Rate:** 0%
- **Cardinality:** 389 distinct
- **Notes:** Display label from Karpathy source data

#### exposure_score
- **Type:** INTEGER
- **Null Rate:** 0%
- **Range:** 1-10 (actual), 0-10 (domain allows)
- **Distribution:** mean=5.20, median=5.0, mode=7 (71 rows)

#### stat_res
- **Type:** INTEGER
- **Null Rate:** 0%
- **Range:** 1-10
- **Derivation:** MIN(11 - exposure_score, 10)

#### boss_ai_score
- **Type:** INTEGER
- **Null Rate:** 0%
- **Range:** 1-10
- **Derivation:** MAX(exposure_score, 1)

#### rationale
- **Type:** STRING
- **Null Rate:** 0%
- **Length:** min=297, max=587, median=404 characters

#### category
- **Type:** STRING
- **Null Rate:** 0%
- **Cardinality:** 24 distinct values (e.g., 'healthcare', 'business-and-financial')

### Eval Set Profile

| Category | Count | Description |
|----------|-------|-------------|
| point_lookup | 34 | Direct soc_code -> field value lookups |
| comparison | 8 | Compare two SOC codes on a metric |
| ranking | 5 | Find extremes (highest/lowest score, category averages) |
| aggregation | 7 | Category-level counts and averages |
| edge_case | 8 | Invalid input, null handling, invariant checks |
| **Total** | **62** | |

### Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation |
|-------------|-------|------------|----------------|
| Eval set size | 62 cases | N/A | Pass threshold: >= 80% (50 of 62) per Brightsmith MCP convention |
| Null-case coverage in eval | 5 cases | 8.1% of eval set | Sufficient coverage of invalid/missing/empty soc_code inputs |
| Response completeness | 7 fields per response | 100% | Every response must contain all 7 fields when data is found |

### Anomalies

| Field | Type | Count | Severity | Details |
|-------|------|-------|----------|---------|
| (none) | -- | -- | -- | No anomalies. MCP layer is a clean passthrough with no transformation logic. |
