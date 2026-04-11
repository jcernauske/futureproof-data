## DQ Scorecard: silver-base-karpathy-ai-exposure
**Spec:** silver-base-karpathy-ai-exposure
**Date:** 2026-04-09
**Agent:** @dq-engineer
**Overall Score:** 23/23 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-04-09T20:26:07.013021+00:00)
**Run ID:** e830d061

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| SLV-KAI-001 |  | P0 | The declared grain is one row per occupation by soc_code (where non-null). After broad code expansion and deduplication, no two rows should share the same soc_code. Duplicate SOC codes would cause fan-out in downstream Gold zone joins and corrupt consumable tables. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-KAI-002 |  | P0 | All non-null SOC codes must match the XX-XXXX format (two digits, hyphen, four digits). After Silver transformation, broad codes (XX-XXX0) should have been expanded to detailed codes (XX-XXXX) or kept as-is if they match BLS exactly. The 6 unmatched broad codes (XX-X000 pattern) will have soc_resolved_method='unresolved' but still pass this regex since XX-X000 matches the XX-XXXX pattern. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-KAI-003 |  | P0 | Exposure score is a passthrough from Bronze. Must remain in the 0-10 integer range defined by Karpathy's rubric. The effective range is 1-10 (no zeros observed), but the rubric permits 0, so the DQ rule allows it. Any out-of-range value indicates a data mutation during Silver transformation. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-KAI-004 |  | P0 | exposure_score is NOT NULL in the physical model. Every row -- whether direct, expanded, title-matched, or unresolved -- must carry a score. Expanded rows inherit the broad code's score; unresolved rows retain their Bronze score. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-KAI-005 |  | P0 | soc_resolved_method must be one of exactly four valid values: 'direct', 'title_match', 'broad_expansion', 'unresolved'. Any other value indicates a bug in the SOC resolution logic. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-KAI-006 |  | P0 | At least 90% of rows with non-null soc_code must have bls_match = true (meaning the SOC code was found in base.bls_ooh). If less than 90% match, the SOC vintage is wrong or the BLS OOH data is incomplete, and investigation is required before Gold promotion. | PASS | actual=0.0, threshold=result = 0.0 |
| SLV-KAI-007 |  | P0 | slug is NOT NULL in the physical model. Every row must retain its Karpathy slug for provenance and traceability. For broad_expansion rows, the original slug of the broad-code row is carried to all expanded detailed-code rows. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-KAI-008 |  | P0 | record_id is the surrogate primary key. It must be non-null and unique across all rows. It is a deterministic SHA-256 hash (prefix 'kai') computed from soc_code (when non-null) or slug (when soc_code is null). Duplicates would indicate a grain collision in the hash function. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-KAI-009 |  | P0 | After broad code expansion (342 Bronze rows + ~110 expansion rows - dedup + ~28 title matches), the expected row count is approximately 412. The range 380-500 provides margin for variation in title matching outcomes and expansion counts. Below 380 suggests expansion logic failed; above 500 suggests uncontrolled 1:N expansion. | PASS | actual=0.0, threshold=result = 0.0 |
| SLV-KAI-010 |  | P1 | Rationale must be at least 250 characters long per the physical model CHECK constraint. This ensures the LLM-generated explanation is substantive enough to be meaningful for the Fight AI boss narrative display. The shortest observed rationale is 297 chars (47 chars of headroom). | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-KAI-011 |  | P1 | The 'direct' resolution method should account for the majority of rows. EDA predicts ~59% direct (244 of ~412). A drop below 50% would indicate the SOC resolution logic is misclassifying direct matches or the broad expansion is producing disproportionately many rows. | PASS | actual=0.0, threshold=result = 0.0 |
| SLV-KAI-012 |  | P1 | Unresolved rows (no SOC code after all resolution attempts) should not exceed 15% of total rows. EDA predicts ~7% unresolved (~30 of ~412). Exceeding 15% would indicate title matching and broad expansion are both failing at higher-than-expected rates. | PASS | actual=0.0, threshold=result = 0.0 |
| SLV-KAI-013 |  | P0 | Rows with null soc_code must have soc_resolved_method = 'unresolved'. Any other value on a null-SOC row indicates a bug in the resolution logic (e.g., a title_match that didn't actually populate the soc_code). | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-KAI-014 |  | P1 | Rows with non-null soc_code and bls_match = true should NOT have soc_resolved_method = 'unresolved'. Note: 6 rows will have non-null SOC + unresolved + bls_match=false (unmatched broad codes like XX-X000). Those are acceptable. But a row that matched BLS should never be classified as unresolved. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-KAI-015 |  | P0 | Rows with null soc_code must have bls_match = false. You cannot have a BLS match without a SOC code to match on. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-KAI-016 |  | P0 | occupation_title is NOT NULL in the physical model. Every row must have a title, whether direct from Bronze or inherited during expansion. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-KAI-017 |  | P0 | category is NOT NULL in the physical model. Every row must be assigned to one of Karpathy's 25 BLS category groups. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-KAI-018 |  | P0 | source_load_date is NOT NULL in the physical model. Pipeline metadata field renamed from Bronze load_date. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-KAI-019 |  | P0 | ingested_at is NOT NULL in the physical model. Silver zone write timestamp generated at transformation time. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-KAI-020 |  | P0 | record_id must follow the format 'kai-' followed by exactly 16 lowercase hexadecimal characters. This is the deterministic SHA-256 truncated hash produced by compute_grain_id(). | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-KAI-021 |  | P0 | exposure_score must be an integer. Fractional values would indicate a type coercion error during Silver transformation. Score is a passthrough from Bronze where it is already validated as integer. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-KAI-022 |  | P0 | If bls_match is true, the soc_code must actually exist in base.bls_ooh. A true bls_match with no corresponding BLS record indicates the bls_match flag was set incorrectly during transformation. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-KAI-023 |  | P0 | Rows created by broad code expansion are by definition matched to BLS detailed codes. If a broad_expansion row has bls_match = false, the expansion logic created a row for a SOC code that doesn't exist in BLS, which is a bug. | PASS | actual=0, threshold=result_count = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
|  | 23 | 23 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.

