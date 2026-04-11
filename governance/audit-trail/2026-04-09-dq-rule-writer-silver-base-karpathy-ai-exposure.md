# Audit Trail: DQ Rule Writer - silver-base-karpathy-ai-exposure

**Agent:** @dq-rule-writer
**Spec:** silver-base-karpathy-ai-exposure
**Zone:** Silver (Base)
**Date:** 2026-04-09
**Table:** base.karpathy_ai_exposure (does not exist yet -- rules written in advance of transformer build)

---

## Evidence Sources Read

1. `governance/domain-context.md` -- Karpathy AI Exposure section (lines 1168-1340)
2. `governance/eda/silver-base-karpathy-ai-exposure-eda.md` -- PRIMARY EVIDENCE (199 lines)
3. `governance/models/silver-base-karpathy-ai-exposure-physical.md` -- Physical model constraints
4. `docs/specs/raw-ingest-karpathy-ai-exposure.md` -- Spec Zone 2 DQ Rules section
5. `governance/dq-rules/raw-ingest-karpathy-ai-exposure.json` -- Bronze DQ rules (format reference)

---

## Rules Written (23 total)

| Rule ID | Dimension | Priority | Summary |
|---------|-----------|----------|---------|
| SLV-KAI-001 | Uniqueness | P0 | Grain uniqueness on soc_code (non-null) |
| SLV-KAI-002 | Validity | P0 | SOC code format XX-XXXX where non-null |
| SLV-KAI-003 | Validity | P0 | Exposure score range 0-10 |
| SLV-KAI-004 | Completeness | P0 | Exposure score not null |
| SLV-KAI-005 | Validity | P0 | soc_resolved_method enum check |
| SLV-KAI-006 | Referential Integrity | P0 | BLS match rate >= 90% among non-null SOC |
| SLV-KAI-007 | Completeness | P0 | Slug not null |
| SLV-KAI-008 | Uniqueness | P0 | record_id unique and not null |
| SLV-KAI-009 | Volume | P0 | Row count 380-500 |
| SLV-KAI-010 | Validity | P1 | Rationale length >= 250 chars |
| SLV-KAI-011 | Consistency | P1 | soc_resolved_method: direct >= 50% |
| SLV-KAI-012 | Consistency | P1 | soc_resolved_method: unresolved <= 15% |
| SLV-KAI-013 | Consistency | P0 | Null SOC implies unresolved method |
| SLV-KAI-014 | Consistency | P1 | Non-null SOC + bls_match=true implies NOT unresolved |
| SLV-KAI-015 | Consistency | P0 | Null SOC implies bls_match = false |
| SLV-KAI-016 | Completeness | P0 | occupation_title not null |
| SLV-KAI-017 | Completeness | P0 | category not null |
| SLV-KAI-018 | Completeness | P0 | source_load_date not null |
| SLV-KAI-019 | Completeness | P0 | ingested_at not null |
| SLV-KAI-020 | Validity | P0 | record_id format kai-<16 hex> |
| SLV-KAI-021 | Validity | P0 | Exposure score is integer |
| SLV-KAI-022 | Referential Integrity | P0 | bls_match=true implies soc_code exists in base.bls_ooh |
| SLV-KAI-023 | Consistency | P0 | broad_expansion rows must have bls_match = true |

---

## Threshold Decisions

| Rule ID | Threshold | EDA Evidence | Decision Rationale |
|---------|-----------|-------------|-------------------|
| SLV-KAI-001 | 0 duplicates | EDA: zero duplicates predicted after expansion | Hard block. Grain integrity is foundational. |
| SLV-KAI-006 | >= 90% | EDA: predicted ~98% | 90% threshold provides 8% margin below predicted rate. Catches vintage mismatches. |
| SLV-KAI-009 | 380-500 rows | EDA: predicted ~412 | Tightened from physical model's 400-700. EDA recommends 380-500. |
| SLV-KAI-010 | >= 250 chars | EDA: min observed 297, all pass | Physical model constraint. 47 chars headroom. |
| SLV-KAI-011 | >= 50% direct | EDA: predicted ~59% | Spec said 70% but EDA corrected to ~59%. Set floor at 50% for margin. |
| SLV-KAI-012 | <= 15% unresolved | EDA: predicted ~7% | Set ceiling at double the predicted rate to catch systemic failures. |

---

## Rules Considered but Not Written

| Consideration | Decision | Rationale |
|--------------|----------|-----------|
| Exposure score distribution (mean/stddev check) | Not written | P3 statistical monitoring not warranted for passthrough field. Bronze DQ already validates range. Distribution shift is expected (more low-score rows from expansion). |
| Category cardinality = 25 | Not written | Category is a passthrough from Bronze. Bronze DQ validates. Expanded rows inherit category. No new categories can appear. |
| Cross-validation: Silver exposure_score matches Bronze exposure_score for direct rows | Not written | Would require joining Silver back to Bronze, which adds complexity. The range check (SLV-KAI-003) and passthrough nature provide sufficient guardrails. If mutation occurred, it would likely produce out-of-range values. |
| Freshness check on ingested_at | Not written | This is Silver zone (no freshness dimension per rule dimensions table). Source_load_date freshness already covered in Bronze. |
| Title match accuracy validation | Not written | Cannot validate title match quality via DQ rules alone -- would require manual review. The distribution check (SLV-KAI-012 unresolved cap) is the proxy guard. |
| broad_expansion count per slug | Not written | P3 monitoring. EDA shows range 2-6 expansions per broad code. No hard constraint needed. |

---

## Execution Status

Rules cannot be executed yet -- the table base.karpathy_ai_exposure does not exist. Rules are written in advance of the Silver transformer build. The @primary-agent will build the transformer next, after which @dq-engineer will execute the rules and produce scorecards.

---

## Notes

- The spec's predicted soc_resolved_method distribution (70% direct / 15% broad_expansion / 10% title_match / 5% unresolved) was corrected by the EDA to ~59% direct / ~27% broad_expansion / ~7% title_match / ~7% unresolved. All thresholds use the EDA-corrected values.
- The physical model's row count range (400-700) was tightened to 380-500 per EDA recommendation.
- The rationale length threshold uses the physical model's 250-char minimum, not the spec's 100-char minimum. The physical model is authoritative and the EDA confirms all rows exceed 250 with margin.
- 6 "unmatched broad codes" (XX-X000 pattern) are a known edge case. They will have non-null soc_code + soc_resolved_method='unresolved' + bls_match=false. Rule SLV-KAI-014 is designed to accommodate this pattern.
