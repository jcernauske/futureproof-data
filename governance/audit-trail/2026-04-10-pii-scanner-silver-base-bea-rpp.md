# Audit Trail: @pii-scanner — silver-base-bea-rpp

**Date:** 2026-04-10
**Agent:** @pii-scanner
**Spec:** docs/specs/silver-base-bea-rpp.md
**Parent spec:** docs/specs/raw-ingest-bea-rpp.md
**Zone:** Silver
**Dataset:** base.bea_rpp (51 rows, 11 columns)
**Artifact produced:** governance/pii-scans/silver-base-bea-rpp.md
**Decision:** NO PII — zero-PII claim holds across all 11 Silver columns
**Confidence:** HIGH

---

## Context

This is the Silver-layer PII verification for BEA Regional Price Parities. The Bronze scan at `governance/pii-scans/raw-ingest-bea-rpp.md` (2026-04-10) already certified `bronze.bea_rpp` as zero-PII with a k-anonymity floor of ~584,000 (Wyoming). The Silver spec adds three derived columns on top of Bronze:

1. `state_abbr` — 2-letter USPS code from in-code FIPS→USPS lookup
2. `census_region` — U.S. Census region from in-code FIPS→region lookup
3. `purchasing_power_multiplier` — `100.0 / rpp_all_items`, a pure reciprocal

plus a new grain identifier (`record_id`), a new provenance label (`verification_status`), a Silver batch timestamp (`ingested_at`), and 5 passthrough/renamed columns from Bronze. Total Silver schema: 11 columns, grain unchanged at `[state_fips]`, row count unchanged at 51.

The Silver spec's agent-workflow step 10 explicitly calls for @pii-scanner to produce a skip recommendation documented as "no PII." This audit-trail entry is that documentation.

## Inputs Consulted

- `docs/specs/silver-base-bea-rpp.md` — full Silver spec including the 11-column schema, DQ rules, and derivation logic
- `governance/pii-scans/raw-ingest-bea-rpp.md` — Bronze PII scan (prior zero-PII certification)
- `governance/domain-context.md` — BEA RPP section (lines 1352–1611), specifically the **PII Expectations** subsection (starting line 1495), which states:
  - Personal names: not expected
  - SSN/Tax ID: not expected
  - Location data (individual): not expected — state-level only, categorically non-PII under HIPAA Safe Harbor
  - Health records: not expected
  - Financial records (individual): not expected — RPP is a macroeconomic index
  - Education records: not expected
- The Silver spec's agent-workflow note (step 10): "no PII; skip recommendation documented"

## Scanning Method

**Delta scan.** Bronze has already been certified zero-PII with full field-by-field analysis. The Silver-layer scan does not re-scan the Bronze fields from scratch; instead it verifies three specific risk vectors that could break the Bronze claim at the Silver boundary:

1. **Grain refinement** — did the Silver transformation split rows to a finer grain? → NO (grain unchanged at `[state_fips]`, 51 rows)
2. **Introduction of person-level fields** via joins or derivations? → NO (no joins; all derivations are deterministic lookups or arithmetic on non-PII inputs)
3. **Quasi-identifier combination** that could fingerprint a cell below the k-anonymity floor? → NO (every new field is a 1:1 or generalizing function of `state_fips`; cells remain state-level, floor unchanged at ~584,000)

Each of the 11 Silver columns was then classified individually for PII category, sensitivity, and quasi-identifier risk. Full per-field analysis is documented in the scan report.

## Decisions and Rationale

### Decision 1: record_id is non-PII
- **Rationale:** `record_id = compute_grain_id(row, ['state_fips'], prefix='rpp')`. It is a deterministic hash/prefix of a non-PII input (state FIPS). A pseudonym for a state is a pseudonym for a jurisdiction, not a person. Cannot be de-anonymized to an individual because its input represents an entire state (~584K to ~39M people).

### Decision 2: state_abbr is non-PII
- **Rationale:** 2-letter USPS postal code, derived deterministically from `state_fips` via a 51-entry structural lookup. By DQ rule, `state_abbr` is in a 1:1 bijection with `state_fips`. A 1:1 function of a non-PII field is non-PII. The value space is a bounded public set of 51 postal codes with no overlap with personal initials or sensitive ID formats.

### Decision 3: census_region is non-PII
- **Rationale:** 4-valued enum (`Northeast`, `Midwest`, `South`, `West`), derived deterministically from `state_fips`. This is a **generalization** (51 → 4), which *strengthens* k-anonymity rather than weakening it. The smallest region by population is the Northeast at ~57 million residents. DC's assignment to South is a documented Census Bureau quirk, not a privacy concern.

### Decision 4: purchasing_power_multiplier is non-PII
- **Rationale:** `100.0 / rpp_all_items`. A pure reciprocal of a state-level macroeconomic index. A function of a single non-PII aggregate is still a non-PII aggregate. Encodes no information about any individual; encodes only the reciprocal of a state-level price index.

### Decision 5: verification_status is non-PII
- **Rationale:** 2-valued categorical enum (`bea_official`, `estimate`) derived from a hard-coded allow-list of 8 `state_fips` codes. Encodes data-quality provenance of a row, not anything about individuals. The allow-list itself contains only public state FIPS codes. A provenance tag on a state-level aggregate inherits the non-PII status of the aggregate.

### Decision 6: Silver `ingested_at` and `source_load_date` are non-PII
- **Rationale:** Both are batch-level timestamps, identical across all 51 rows. They identify when the ETL job ran, not when any individual did anything. No within-row temporal variation that could enable behavioral fingerprinting. Standard operational provenance fields, categorically non-PII.

### Decision 7: No grain change, no k-anonymity change
- **Rationale:** Silver grain is `[state_fips]`, identical to Bronze. Row count is 51. Every row continues to represent an entire U.S. state (or DC). The k-anonymity floor is unchanged at ~584,000 (Wyoming). This mechanically means Silver cannot be less private than Bronze.

### Decision 8: Full zero-PII verdict holds
- **Rationale:** All 11 columns classify as non-PII. No quasi-identifiers introduced. No direct personal fields introduced. No grain refinement. No temporal linkability risk. No external-join amplification risk. The Bronze zero-PII certification propagates cleanly through Silver.

## False Positive Decisions

| Potential Match | Source of False Positive | Decision | Rationale |
|----------------|--------------------------|----------|-----------|
| `state_abbr` — "initials" | Naive NER or PII regex that flags 2-letter uppercase tokens as personal initials | NOT PII | Value space is strictly the canonical 51-member USPS set; values are public jurisdiction codes, not personal initials. |
| `census_region` — "geographic location data" | Naive location-PII matcher that flags any geographic string | NOT PII | 4-valued enum; each value covers tens of millions of residents. A region is a jurisdiction grouping, not an address or coordinate. |
| `record_id` — "pseudonymized identifier" | Pattern-based PII scanner that treats hashed IDs as potentially personal | NOT PII | Pseudonym for a state, not a person. Derived from non-PII input. De-anonymization target is an entire state (~584K+ people) which is definitionally not an individual. |
| `verification_status` — "user status" | Field-name heuristic that flags `*_status` as user/account status | NOT PII | Values `{bea_official, estimate}` describe data-quality provenance of the row, not a user account. |

## Downstream Handoff

- **@policy-engineer:** No RLS, no column masking, no encryption-beyond-baseline required for PII reasons. `base.bea_rpp` may be published at `data_classification: public`.
- **@data-contract-author:** Contract declares `pii_classification: none` and `data_classification: public` for all 11 columns.
- **@cde-tagger:** No PII/sensitivity CDE tags; business-critical CDE tagging proceeds independently.
- **@doc-generator:** Data dictionary entries for all 11 columns may note `pii: false, sensitivity: public`.
- **Gold/MCP scans for this source:** May reference this Silver report and confirm that downstream derivations (`cost_tier`, `adjusted_*` salary columns, etc.) are further transformations of the same non-PII inputs.

## Spec Agent-Workflow Alignment

Per `docs/specs/silver-base-bea-rpp.md` agent workflow step 10: "@pii-scanner — no PII; skip recommendation documented." This audit-trail entry and the accompanying scan report at `governance/pii-scans/silver-base-bea-rpp.md` satisfy that step.

## Artifacts Produced

- `governance/pii-scans/silver-base-bea-rpp.md` — full Silver PII scan report with field-by-field delta analysis
- `governance/audit-trail/2026-04-10-pii-scanner-silver-base-bea-rpp.md` — this file

## One-Line Justification

"Zero-PII claim from `bronze.bea_rpp` holds across all 11 `base.bea_rpp` columns — the 3 new derived columns are deterministic 1:1 or generalizing functions of a non-PII state FIPS code, grain is unchanged at 51 state rows, and the k-anonymity floor remains ~584,000."
