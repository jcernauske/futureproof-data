# Audit Trail: DQ Rule Writing for silver-base-onet

**Date:** 2026-04-08
**Agent:** @dq-rule-writer
**Spec:** docs/specs/silver-base-onet.md
**Evidence:** governance/eda/silver-onet-eda.md
**Model:** governance/models/silver-base-onet-logical.md
**Output:** governance/dq-rules/silver-base-onet.json

---

## Summary

Wrote 32 DQ rules across 4 Silver tables for the silver-base-onet spec. All thresholds are evidence-based from the EDA report. Rules cover all 8 dimensions: Uniqueness (4), Validity (14), Volume (4), Completeness (4), Referential Integrity (4), Consistency (2), and informational (suppress_flag monitoring, 2).

## Rules Written

### base.onet_occupations (7 rules)

| Rule ID | Dimension | Priority | Description |
|---------|-----------|----------|-------------|
| SLV-ONET-001 | Validity | P0 | bls_soc_code format XX-XXXX |
| SLV-ONET-002 | Uniqueness | P0 | bls_soc_code grain integrity |
| SLV-ONET-003 | Volume | P0 | Row count = 798 (EDA-corrected from spec ~867) |
| SLV-ONET-004 | Validity | P1 | multi_detail_flag count = 76 |
| SLV-ONET-005 | Validity | P1 | data_completeness_tier: 774 full, 24 partial, 0 none |
| SLV-ONET-006 | Validity | P0 | No 'All Other'/Military with none tier present |
| SLV-ONET-007 | Completeness | P0 | All 14 fields NOT NULL |

### base.onet_activity_profiles (8 rules)

| Rule ID | Dimension | Priority | Description |
|---------|-----------|----------|-------------|
| SLV-ONET-010 | Uniqueness | P0 | Grain: bls_soc_code x element_id |
| SLV-ONET-011 | Validity | P0 | importance range 1.0-5.0 |
| SLV-ONET-012 | Validity | P0 | Exactly 41 distinct element_ids |
| SLV-ONET-013 | Validity | P1 | importance_rank 1-41 per occupation, no gaps |
| SLV-ONET-014 | Validity | P2 | suppress_flag < 1% |
| SLV-ONET-015 | Volume | P1 | Row count = 31,734 |
| SLV-ONET-016 | Referential Integrity | P0 | FK bls_soc_code to onet_occupations |
| SLV-ONET-017 | Completeness | P0 | All 11 fields NOT NULL |

### base.onet_context_profiles (10 rules)

| Rule ID | Dimension | Priority | Description |
|---------|-----------|----------|-------------|
| SLV-ONET-020 | Uniqueness | P0 | Grain: bls_soc_code x element_id |
| SLV-ONET-021 | Validity | P0 | CX context_value range 1.0-5.0 |
| SLV-ONET-022 | Validity | P0 | CT context_value range 1.0-3.0 |
| SLV-ONET-023 | Validity | P0 | Exactly 57 distinct element_ids |
| SLV-ONET-024 | Validity | P1 | is_burnout_element: 9 element_ids (EDA-corrected) |
| SLV-ONET-025 | Validity | P0 | No CXP/CTP scale rows |
| SLV-ONET-026 | Referential Integrity | P0 | FK bls_soc_code to onet_occupations |
| SLV-ONET-027 | Volume | P1 | Row count = 44,118 |
| SLV-ONET-028 | Completeness | P0 | All 11 fields NOT NULL |
| SLV-ONET-029 | Validity | P2 | suppress_flag < 1% |

### base.onet_career_transitions (7 rules)

| Rule ID | Dimension | Priority | Description |
|---------|-----------|----------|-------------|
| SLV-ONET-030 | Uniqueness | P0 | Grain: bls_soc_code x related_bls_soc_code |
| SLV-ONET-031 | Validity | P0 | No self-references |
| SLV-ONET-032 | Validity | P0 | best_index range 1-20 |
| SLV-ONET-033 | Validity | P0 | relatedness_tier exactly 3 valid values |
| SLV-ONET-034 | Consistency | P0 | is_primary consistent with tier |
| SLV-ONET-035 | Referential Integrity | P0 | FK bls_soc_code to onet_occupations |
| SLV-ONET-036 | Referential Integrity | P0 | FK related_bls_soc_code to onet_occupations |
| SLV-ONET-037 | Volume | P1 | Row count = 15,944 |
| SLV-ONET-038 | Validity | P0 | Both SOC codes valid XX-XXXX |
| SLV-ONET-039 | Completeness | P0 | All 9 fields NOT NULL |
| SLV-ONET-040 | Validity | P0 | relationship_type always 'similarity' |
| SLV-ONET-041 | Consistency | P1 | tier-to-best_index range consistency |

## Key Threshold Decisions

### EDA Corrections Incorporated

1. **Row count 798, not ~867:** EDA proved that at BLS level, only 69 BLS SOCs are truly empty (not 93 as spec counted at O*NET level). 24 of the 93 zero-data O*NET codes share a BLS prefix with data-bearing detail codes.

2. **24 partial, not 29:** Some partial O*NET codes share BLS SOCs with full-data codes, promoting them to "full" at BLS level.

3. **Burnout element IDs corrected:** 4 of 9 spec IDs were wrong. Rule SLV-ONET-024 uses the EDA-corrected list:
   - 4.C.3.d.1 (Time Pressure) -- CORRECT
   - 4.C.3.d.8 (Duration of Typical Work Week) -- CORRECT
   - 4.C.3.a.1 (Consequence of Error) -- CORRECT
   - 4.C.3.d.3 (Pace Determined by Speed of Equipment) -- CORRECT
   - 4.C.3.a.2.b (Frequency of Decision Making) -- WAS 4.C.3.b.2
   - 4.C.3.b.4 (Importance of Being Exact or Accurate) -- WAS 4.C.3.d.4
   - 4.C.3.b.7 (Importance of Repeating Same Tasks) -- WAS 4.C.3.d.5
   - 4.C.3.d.4 (Work Schedules) -- WAS 4.C.3.d.7
   - 4.C.3.a.2.a (Impact of Decisions on Co-workers or Company Results) -- REPLACES nonexistent "Responsibility for Outcomes and Results"

4. **Career transitions = 15,944:** EDA computed: 18,460 raw - 343 self-refs - 2,173 deduped = 15,944.

### Suppress Flag Thresholds

Set at <1% for both activity_profiles and context_profiles. EDA shows 0.003% for IM and 0.04% for CX. The 1% threshold provides ~25-250x headroom, appropriate for P2 informational monitoring.

## Rules Considered But Not Written

1. **Freshness rule:** Not applicable. Single-snapshot data from O*NET 30.2. All tables share the same source_load_date. Freshness is a Bronze-zone concern.

2. **Cross-source FK (onet_occupations.bls_soc_code to base.bls_ooh.soc_code):** Logical model notes this is NOT a strict FK (O*NET has ~798 SOCs vs BLS OOH 832, partial overlap). Coverage rule would be appropriate in Gold zone when the sources are joined, not in Silver where they are independent.

3. **onet_detail_codes JSON validity:** Could validate that onet_detail_codes is valid JSON array with O*NET-SOC formatted entries. Deferred as lower priority -- the field is lineage metadata, not used for joins.

4. **importance distribution monitoring (P3):** EDA shows mean=3.15, median=3.23, stdev=0.86. Could write a distribution drift rule. Deferred -- single-snapshot data, no temporal comparison possible yet.

5. **Exact 41 rows per occupation in activity_profiles:** Implied by grain uniqueness (SLV-ONET-010) + element count (SLV-ONET-012) + row count (SLV-ONET-015). A separate rows-per-occupation rule would be redundant.

6. **Context value distribution monitoring:** EDA provides mean/median/stdev for CX and CT. Deferred as P3 -- no temporal comparison baseline.

## Execution

Rules cannot be executed yet -- Silver tables do not exist. @primary-agent will implement the 4 Silver transformers (step 8), then @dq-engineer will execute rules and produce the scorecard (step 9).
