# Domain Context: College Scorecard Institution-Level Cost Data

**Date:** 2026-04-14
**Agent:** @domain-context
**Based On:** docs/sessions/eda-college-scorecard-institution.md (2026-04-15)
**Spec:** docs/specs/raw-ingest-college-scorecard-institution.md
**Data Source:** U.S. Department of Education College Scorecard, Most-Recent-Cohorts-Institution.csv
**Confidence:** High

---

## Relationship to Main Domain Context

This document is a **source-specific supplement** to `governance/domain-context.md`, which covers the full FutureProof domain. This source (College Scorecard Institution-Level) is the sixth data source in the pipeline and a direct extension of the first (College Scorecard Field of Study). It adds institution-level cost structure to the existing program-level earnings and debt data.

**Join topology:** `base.college_scorecard_institution.unitid` LEFT JOINs to `consumable.career_outcomes.unitid`.

---

## Domain Identification

**Domain:** Higher Education Outcomes
**Sub-domain:** Institution-Level Cost of Attendance and Net Price
**Description:** This data captures the cost structure of U.S. postsecondary institutions: what they charge (cost of attendance), what students actually pay after grants and scholarships (net price), and how net price varies by family income bracket. The data is published by the U.S. Department of Education from IPEDS institutional surveys and covers Title IV institutions filtered to 4-year bachelor's-granting schools. It complements the existing field-of-study data by adding the denominator for a true ROI formula: `earnings / (net_price x 4 x loan_pct)` instead of `earnings / debt_median`.

---

## Domain Vocabulary

### Core Terms

| Term | Definition | Source | Notes for @data-steward |
|------|-----------|--------|------------------------|
| Cost of Attendance (COA) | The total annual cost of attending an institution, including tuition, fees, books, supplies, room and board, and living expenses. This is the "sticker price" before financial aid. Two variants exist: COSTT4_A (academic-year programs, 2,192 rows) and COSTT4_P (program-year programs, 41 rows). They are mutually exclusive -- no institution has both. | IPEDS / College Scorecard (external standard) | Auto-approve. BT-110 already proposed in spec. |
| Net Price | The average annual cost students actually pay after subtracting grants and scholarships from COA. Separate fields exist for public (NPT4_PUB) and private (NPT4_PRIV) institutions -- a school populates exactly one based on its CONTROL value. | IPEDS / College Scorecard (external standard) | Auto-approve. BT-111 already proposed in spec. |
| Net Price by Income Quintile | Net price broken down by family income bracket. Five quintiles: Q1=$0-30K, Q2=$30-48K, Q3=$48-75K, Q4=$75-110K, Q5=$110K+. Lower-income families typically receive more aid, resulting in lower net prices -- but this is not guaranteed (see edge cases). | IPEDS / College Scorecard (external standard) | Auto-approve. BT-112 already proposed in spec. |
| CONTROL | Institution control classification: 1=Public, 2=Private nonprofit, 3=Private for-profit. Determines which net price field (PUB vs PRIV) to read. | IPEDS (external standard) | Auto-approve. Critical routing field for Silver unified net price logic. |
| PREDDEG | Predominant degree awarded: 0=Not classified, 1=Certificate, 2=Associate's, 3=Bachelor's, 4=Graduate. Used as a filter (PREDDEG=3 OR ICLEVEL=1) but the filtered set includes all PREDDEG values. | IPEDS (external standard) | Auto-approve. Note: filtered set is NOT only PREDDEG=3 -- it includes 288 unclassified, 153 certificate, 335 associate's, and 280 graduate-dominant institutions captured by the ICLEVEL=1 fallback. |
| ICLEVEL | Institution level: 1=Four-year, 2=Two-year, 3=Less-than-two-year. Used as a secondary filter criterion. | IPEDS (external standard) | Auto-approve. |
| UNITID | 6-digit IPEDS institution identifier. Same key used in the field-of-study file. Join key between these two sources. | NCES/IPEDS (external standard) | Already approved in main domain context. |
| Tuition and Fees | The published charge for instruction and mandatory fees. Separate in-state and out-of-state values for public institutions. Private/for-profit institutions report the same value for both. Does NOT include room, board, books, or living expenses. | IPEDS (external standard) | Auto-approve. Important: this is a component of COA, not the same as COA. |
| Room and Board | The charge for housing and meals. On-campus and off-campus variants reported separately. 43.4% of institutions lack on-campus housing data (schools without dormitories). | IPEDS (external standard) | Auto-approve. |

### Taxonomy/Classification Systems

| System | Description | Authority | Coverage in Data |
|--------|-------------|-----------|-----------------|
| IPEDS UNITID | 6-digit institutional identifiers | NCES/IPEDS | 3,039 distinct institutions. All values valid. |
| CONTROL | Institution control (1/2/3) | IPEDS | 100% populated. 867 public (28.5%), 1,754 private nonprofit (57.7%), 418 for-profit (13.8%). |
| PREDDEG | Predominant degree (0-4) | IPEDS | 100% populated. Distribution varies within filtered set (see EDA). |
| STABBR | 2-letter state/territory codes | USPS / FIPS | 100% populated. 56 distinct values (50 states + DC + territories). |

### Enumerated Values with Business Meaning

| Field | Values | Meaning |
|-------|--------|---------|
| CONTROL | 1, 2, 3 | 1=Public (state-funded, lower tuition for residents), 2=Private nonprofit (endowment-supported, merit/need aid), 3=Private for-profit (tuition-dependent, historically higher costs with less aid) |
| PREDDEG | 0, 1, 2, 3, 4 | Predominant degree: 0=Not classified, 1=Certificate, 2=Associate's, 3=Bachelor's, 4=Graduate. Only present because ICLEVEL=1 filter captures 4-year schools regardless of predominant degree. |

---

## Entity Types

### Primary Entities

| Entity Type | Identifier Field(s) | Example | Notes for @entity-resolver |
|-------------|---------------------|---------|---------------------------|
| Institution | unitid | 166027 (MIT) | **SKIP entity resolution.** UNITID is the sole grain key, guaranteed unique (3,039 rows, 3,039 distinct UNITIDs, 0 duplicates). Resolution is trivial -- ID-based, no ambiguity. |

### Entity Resolution Complexity: TRIVIAL

This source has the simplest possible entity structure: a single integer primary key (UNITID) with no duplicates, no composite grain, no name-based matching needed. The @entity-resolver agent can be **skipped** for this source.

### Entity Lifecycle Events

| Event Type | How It Appears in Data | Frequency |
|-----------|----------------------|-----------|
| Institution closure | UNITID absent from future refreshes | Cannot detect in single snapshot. Track across refreshes. |
| Cost reporting gap | Cost fields null for a UNITID that exists | Common for for-profit (47.4% missing net price) and some private nonprofits (29.4% missing). |

---

## Temporal Patterns

### Temporal Modeling Needs: NONE (Single Snapshot)

This data has **no temporal dimension**. It is a single point-in-time snapshot of the most recent cohort data. All 3,039 rows share the same load date. There is no time-series, no slowly changing dimension, no bi-temporal modeling needed for this initial load.

**Recommendation for @temporal-modeler:** SKIP for this source. If future annual refreshes are ingested, revisit and consider SCD Type 1 (overwrite) since the data represents "current cost structure" not historical trends.

### Valid Time

| Pattern | Description | Notes for @temporal-modeler |
|---------|-------------|---------------------------|
| Annual institutional snapshot | Cost and net price data reflects the most recent reporting year available to the Department of Education. No date field within the data identifies which year's costs are reported. | The `load_date` and `ingested_at` metadata fields are the only temporal markers. Model as a snapshot table. |

### Amendment/Correction Patterns

| Pattern | Description | Frequency |
|---------|-------------|-----------|
| Annual full replace | Each annual College Scorecard release replaces the prior year entirely. | Annual. Handle as full-table overwrite, not incremental. |

---

## Data Quality Considerations

### Known Edge Cases

| Edge Case | Description | Impact | Notes for @dq-rule-writer |
|-----------|-------------|--------|--------------------------|
| Row count is 3,039, not ~6,500 | The spec estimated ~6,500 based on the unfiltered file (6,429 rows). After PREDDEG=3 OR ICLEVEL=1 filtering, only 3,039 remain. | **SPEC CORRECTION NEEDED.** DQ row count rule must be 2,500-3,500, not 5,000-8,000. | Set row count bounds: 2,500-3,500 (P0). |
| COA coverage is 73.5%, not 90% | 806 institutions (26.5%) have neither COSTT4_A nor COSTT4_P. Concentrated in PREDDEG=0 (288) and PREDDEG=4 (280). | **SPEC CORRECTION NEEDED.** The DQ rule "at least one of costt4_a or costt4_p non-null >= 90%" will FAIL. | Lower threshold to >= 70% (P0). Actual is 73.5%. |
| Negative net prices are legitimate | 3 public schools (e.g., San Diego Mesa at -$904) and 5 private quintile values (e.g., MIT Q1 at -$4,129) have negative net prices. Aid exceeds total cost. | Valid data. DQ rules must allow negatives. | NPT4_PUB range: -$5,000 to $35,000. Quintile ranges: -$5,000 to $80,000. Do NOT use $0 as lower bound. |
| Zero PrivacySuppressed values | Unlike the field-of-study file where PS is common, this institution-level file has zero PS values in any cost field. All nulls are genuine blanks. | Defensive PS handling in ingestor is correct but will convert zero values in practice. | No special PS-related rules needed. Document as observation. |
| For-profit data coverage is poor | CONTROL=3 institutions: only 52.6% have net price, 44.3% have COA. | Expected. For-profit schools underreport to IPEDS. | Do NOT set coverage thresholds above 55% for CONTROL=3. Consider splitting DQ rules by CONTROL. |
| Private nonprofit coverage below spec | CONTROL=2: NPT4_PRIV populated at 70.6%. Spec assumed >= 80%. | **SPEC CORRECTION NEEDED.** DQ rule "control=2 -> npt4_priv non-null >= 80%" will FAIL. | Lower to >= 65% or split CONTROL=2 and CONTROL=3 into separate rules. |
| Quintile monotonicity violations | Q1 > Q2 in 37.9% of private institutions. This is a known College Scorecard pattern: merit aid to Q2 students can exceed need-based aid for Q1. | NOT a data error. Do NOT enforce adjacent-pair monotonicity. | Only enforce Q1 <= Q5 (full-span), and expect ~3.2% violation rate. Do NOT write Q[n] <= Q[n+1] rules. |
| COSTT4_A and COSTT4_P are mutually exclusive | Zero institutions have both. COSTT4_A covers 2,192 academic-year programs, COSTT4_P covers 41 program-year programs. | The Silver COALESCE(costt4_a, costt4_p) transformation is safe and will never face a collision. | No special rule needed. The mutual exclusivity is structural. |
| 72 public schools with equal in/out-of-state tuition | Tribal colleges, online-only, and uniform-pricing state systems. | NOT a data error. Do NOT flag tuition_in == tuition_out as anomalous. | Allow equal in/out-of-state tuition. It is valid for ~8.9% of public institutions. |
| ROOMBOARD_ON minimum is $1,000 | Spec DQ floor of $3,000 will reject this legitimate value. | **SPEC CORRECTION NEEDED.** | Lower ROOMBOARD_ON floor to $1,000 (or $500 with margin). |
| BOOKSUPPLY = $0 for 32 schools | Schools that include books in tuition or provide free textbooks. | Valid. Allow zero. | Allow BOOKSUPPLY >= $0. |
| 207 FoS schools with no institution match | 8.1% of field-of-study UNITIDs will get NULL cost data after the Gold LEFT JOIN. | Expected. These schools report program-level data but not institution-level cost data, or were excluded by the PREDDEG/ICLEVEL filter. | Document as known coverage gap. Not a DQ failure. |

### Domain-Specific Validity Rules

| Rule | Description | Source |
|------|-------------|--------|
| UNITID must be a positive integer | IPEDS institutional identifiers are assigned as positive integers in the 6-digit range. | NCES/IPEDS specification. |
| CONTROL must be in (1, 2, 3) | Only three institution control types exist. | IPEDS data dictionary. |
| CONTROL determines which net price field is populated | CONTROL=1 -> NPT4_PUB; CONTROL=2,3 -> NPT4_PRIV. Cross-contamination (public school with NPT4_PRIV or private with NPT4_PUB) is structurally impossible. | EDA verified: zero cross-contamination in 3,039 rows. |
| Net price <= COA where both non-null | Net price is COA minus grants/scholarships. It cannot exceed sticker price. Exception: negative net prices are valid (aid > COA). | EDA verified: 0 violations across all 774 public and 1,418 private rows. |
| COSTT4_A and COSTT4_P are mutually exclusive | No institution reports both. COALESCE is safe. | EDA verified: zero overlap. |
| In-state tuition <= out-of-state tuition | In-state can equal out-of-state (private schools, some public), but cannot exceed it. | EDA verified: 0 violations in 2,518 rows. |

---

## PII Assessment: NONE

| PII Type | Expected? | Sensitivity | Notes for @pii-scanner |
|----------|-----------|-------------|----------------------|
| Personal names | No | N/A | All data is institution-level aggregate statistics. No individual student data. |
| SSNs / Tax IDs | No | N/A | Federal aggregate data source. |
| Addresses | No | N/A | State abbreviations only (STABBR), not street addresses. |
| Financial records | No | N/A | All values are institutional averages, not individual student financials. |

**Recommendation for @pii-scanner:** SKIP for this source. This is a public federal dataset containing only institution-level aggregate statistics. No PII is present or possible.

---

## Regulatory and Compliance Context

### Applicable Regulations

| Regulation | Relevance | Key Requirements | Notes for @bcbs239-auditor |
|-----------|-----------|-----------------|---------------------------|
| Higher Education Act (HEA) | Source authority | Mandates institutional reporting to IPEDS, which feeds College Scorecard. Data quality is the Department of Education's responsibility. | FutureProof is a consumer of public data, not a reporter. No compliance obligation beyond accurate representation. |
| FERPA | Not directly applicable | Student-level data is already aggregated/suppressed at source. FutureProof receives only aggregate institution-level data. | No FERPA obligations for this source. All individual privacy protections applied upstream by the Department of Education. |

---

## Concept Mapping Guidance

### Source Codes to Business Concepts

| Source Code Pattern | Maps To | Confidence | Notes for @cde-tagger |
|--------------------|---------|------------|----------------------|
| COSTT4_A, COSTT4_P | Cost of Attendance (annual) | Exact | Silver COALESCE produces single `cost_of_attendance_annual` field. |
| NPT4_PUB, NPT4_PRIV | Net Price (annual) | Exact | Silver CASE on CONTROL produces single `net_price_annual` field. |
| NPT4[1-5]_PUB, NPT4[1-5]_PRIV | Net Price by Income Quintile | Exact | Silver CASE on CONTROL produces `net_price_q1` through `net_price_q5`. |
| TUITIONFEE_IN, TUITIONFEE_OUT | Tuition and Fees | Exact | Carried through as separate in-state / out-of-state fields. |
| ROOMBOARD_ON, ROOMBOARD_OFF | Room and Board | Exact | Carried through as separate on-campus / off-campus fields. |
| CONTROL | Institution Control Type | Exact | Silver maps 1/2/3 to "Public"/"Private nonprofit"/"Private for-profit". |

### Known Mapping Ambiguities

None. All source fields have unambiguous business meaning defined by the IPEDS data dictionary.

---

## Cross-Source Integration

### Join to Existing Data

| Target Table | Join Key | Coverage | Notes |
|-------------|----------|----------|-------|
| consumable.career_outcomes | unitid | 91.9% (2,352 of 2,559 FoS UNITIDs match) | LEFT JOIN. 207 FoS schools (8.1%) will get null cost data. These schools report program-level earnings/debt but not institution-level cost, or were excluded by PREDDEG/ICLEVEL filter. |

### What This Source Adds to the Pipeline

| Metric | Before This Source | After This Source |
|--------|-------------------|-------------------|
| ROI formula denominator | `debt_median` (what past grads borrowed) | `net_price_annual x 4 x loan_pct` (what the school actually costs after aid) |
| Cost transparency | None | Full cost breakdown: COA, net price, tuition, room/board, books |
| Income-aware pricing | None | Net price by 5 family income quintiles (Q1-Q5) |
| `debt_median` role | Primary ROI input | Reference/comparison field ("median grad borrowed $X") |

---

## Conditional Agent Decisions

Based on EDA findings, the following conditional agents should be **skipped** for this source:

| Agent | Decision | Rationale |
|-------|----------|-----------|
| @entity-resolver | **SKIP** | UNITID is the sole grain key. 3,039 rows, 3,039 distinct UNITIDs, 0 duplicates. No name-based matching, no composite key ambiguity. Entity resolution is trivial. |
| @pii-scanner | **SKIP** | Public federal dataset containing only institution-level aggregate statistics. No individual student data. No PII present or possible. |
| @temporal-modeler | **SKIP** | Single point-in-time snapshot. No time-series dimension. No SCD needed for initial load. Revisit if annual refresh pipeline is built. |
| @adversarial-auditor | **RUN** (standard) | Standard adversarial testing applies -- verify that the ingestor handles malformed CSVs, network failures, and unexpected column changes gracefully. No domain-specific adversarial concerns. |

---

## Spec Corrections Required

The EDA revealed several discrepancies between the spec and actual data. These must be corrected before DQ rules are written:

| Spec Assumption | Actual | Required Change |
|----------------|--------|-----------------|
| ~6,500 rows after filter | 3,039 rows | DQ row count: 2,500-3,500 |
| COA non-null >= 90% | 73.5% | Lower to >= 70% |
| NPT4_PUB range $0-$60K | -$1,180 to $32,598 | Change to -$5,000 to $35,000 |
| CONTROL=2 -> NPT4_PRIV >= 80% | 70.6% | Lower to >= 65% |
| ROOMBOARD_ON floor $3,000 | Min is $1,000 | Lower to $1,000 |
| Adjacent quintile monotonicity | 37.9% Q1>Q2 violations (private) | Only enforce Q1 <= Q5 (full-span) |

---

## Confidence Notes

**High confidence on:**
- Domain identification (same source as existing field-of-study data, well-documented by Department of Education)
- Entity resolution complexity (trivial -- single integer PK, verified by EDA)
- PII assessment (public aggregate data, no individual records)
- Temporal assessment (single snapshot, no time dimension)
- Join coverage (91.9% UNITID overlap verified by EDA)
- All DQ threshold corrections (backed by EDA distribution analysis)

**No uncertainty flags.** This is a well-understood, well-documented federal data source that extends an existing pipeline source using the same join key and the same data provider. The EDA was thorough and all findings are backed by distribution analysis across the full dataset.
