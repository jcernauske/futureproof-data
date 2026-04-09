# Audit Trail: Logical Model — silver-base-college-scorecard

**Agent:** @semantic-modeler
**Date:** 2026-04-06
**Stage:** Logical (Stage 2 of 3)
**Mode:** Greenfield
**Prior Stage:** Conceptual (PROPOSED, Rev 2 -- incorporates human feedback on earnings split and institution control)

---

## Stage Progression

| Stage | Status | Date | Notes |
|-------|--------|------|-------|
| Conceptual | PROPOSED (Rev 2) | 2026-04-06 | Revised based on human feedback: earnings split into 1yr/2yr, institution control added, BT-014 renamed to Small Cohort Flag |
| **Logical** | **PROPOSED** | **2026-04-06** | **This artifact. Pending human approval.** |
| Physical | Not started | -- | Blocked on logical approval |

---

## Key Design Decisions

### 1. Single Denormalized Table (Not Normalized)
**Decision:** Map all 8 conceptual entities into attributes of one `base.college_scorecard` table.
**Rationale:** Silver Base tables follow the wide denormalized fact table pattern. The source data is already at the program-offering grain. No many-to-many relationships exist. Normalization would add join complexity with no benefit at this zone.
**Alternatives considered:** Star schema with dimension tables for Institution, Program, Credential. Rejected because Silver Base is not a consumption layer -- Gold zone handles dimensional modeling if needed.

### 2. Earnings Attributes Kept Separate (Not Merged)
**Decision:** `earnings_1yr_median` and `earnings_2yr_median` remain as independent nullable columns rather than a single `earnings_median` with a `measurement_window` qualifier.
**Rationale:** Honors the conceptual model decision (backed by data: 12.3% independent suppression). Also simpler for downstream consumers -- no pivot needed. The two values are not longitudinal and must not be treated as a time series.
**Alternatives considered:** EAV pattern with measurement_window discriminator. Rejected for query complexity and because there are exactly 2 windows with no expectation of more.

### 3. Institution Control as Text Domain (Not Integer)
**Decision:** `institution_control` uses the text domain with human-readable values (Public, Private nonprofit, Private for-profit) rather than the raw integer code (1, 2, 3).
**Rationale:** Silver Base applies business-meaningful names. The raw integer is an implementation artifact. Text values are self-documenting and reduce lookup errors in downstream queries.
**Alternatives considered:** Keep integer code with a separate description column (like credential_level / credential_description). Rejected because institution control has only 3 values and no complex hierarchy.

### 4. small_cohort_flag as NOT NULL Boolean
**Decision:** The flag is always populated (NOT NULL) even when completions_count_1 is NULL.
**Rationale:** Downstream consumers need a definitive filter. The spec defines the derivation rule; the open question is what happens when the source count is NULL. Proposed: treat NULL completions as True (conservative -- assume small cohort when data is missing). Flagged for human confirmation in Open Issues.

### 5. Missing Business Term for Institution Control
**Decision:** Documented as open issue rather than inventing a term.
**Rationale:** The @data-steward owns the glossary. The logical model identifies the gap and recommends BT-018 but does not create it -- that is outside @semantic-modeler scope.

---

## Data Patterns Driving Decisions

| Pattern | Source | Impact on Model |
|---------|--------|----------------|
| 69,947 rows, zero duplicates on unitid x cipcode x credlev | EDA report | Confirms natural key and grain definition |
| 12.3% independent earnings suppression | Conceptual model (from Bronze data analysis) | Validates separate earnings attributes rather than merged |
| 56.1% of rows have both earnings NULL | EDA report | Nullable semantics critical -- NULL = suppressed, not missing |
| CONTROL field in CSV but not in raw Iceberg | Spec technical design | institution_control requires raw schema update (Open Issue #2) |
| All credlev = 3 | EDA report | credential_level kept as natural key component for future extensibility |
| r=0.984 between completions counts | Domain context | Both count windows kept -- not redundant enough to drop |

---

## Inputs Consumed

- Approved conceptual model: `governance/models/silver-base-college-scorecard-conceptual.md` (Rev 2)
- Spec: `docs/specs/silver-base-college-scorecard.md`
- Business glossary: `governance/business-glossary.json` (17 terms, BT-001 through BT-017)
- Domain context: `governance/domain-context.md`
- Human feedback from conceptual review: earnings split, institution control, BT-014 rename

## Outputs Produced

- Logical model: `governance/models/silver-base-college-scorecard-logical.md`
- This audit trail: `governance/audit-trail/silver-base-college-scorecard-logical-model.md`
