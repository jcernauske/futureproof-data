# Audit Trail: DQ Rule Writer - raw-ingest-college-scorecard-institution

**Date:** 2026-04-14
**Agent:** @dq-rule-writer
**Spec:** docs/specs/raw-ingest-college-scorecard-institution.md
**Zone:** Bronze
**EDA Source:** docs/sessions/eda-college-scorecard-institution.md
**Domain Context:** domain/raw-ingest-college-scorecard-institution-context.md

---

## Rules Written

| Rule ID | Dimension | Priority | Description | EDA-Corrected? |
|---------|-----------|----------|-------------|----------------|
| RAW-CSI-001 | Volume | P0 | Row count 2,500-3,500 | YES (spec said 5,000-8,000) |
| RAW-CSI-002 | Uniqueness | P0 | UNITID uniqueness | No |
| RAW-CSI-003 | Completeness | P0 | UNITID not null | No |
| RAW-CSI-004 | Validity | P0 | CONTROL in (1,2,3) | No |
| RAW-CSI-005 | Validity | P0 | COSTT4_A range $5K-$100K | No |
| RAW-CSI-006 | Validity | P0 | NPT4_PUB range -$5K to $60K | YES (spec said $0-$60K) |
| RAW-CSI-007 | Validity | P0 | NPT4_PRIV range -$5K to $80K | YES (spec said $0-$80K) |
| RAW-CSI-008 | Validity | P1 | TUITIONFEE_IN range $0-$75K | YES (spec said $0-$65K, EDA max $69,330) |
| RAW-CSI-009 | Validity | P1 | ROOMBOARD_ON range $1K-$30K | YES (spec said $3K-$25K) |
| RAW-CSI-010 | Completeness | P0 | COA coverage >= 70% | YES (spec said >= 90%) |
| RAW-CSI-011 | Completeness | P1 | Public net price coverage >= 75% | YES (spec said >= 80%) |
| RAW-CSI-012 | Completeness | P1 | Private NP net price coverage >= 65% | YES (spec said >= 80%) |
| RAW-CSI-013 | Consistency | P1 | Quintile Q1 <= Q5 span monotonicity | YES (spec said adjacent Q(n) <= Q(n+1)) |

## Threshold Corrections from EDA

| Rule | Spec Original | EDA-Corrected | Rationale |
|------|--------------|---------------|-----------|
| Row count | 5,000-8,000 | 2,500-3,500 | EDA: 3,039 rows after PREDDEG=3 OR ICLEVEL=1 filter. Spec used unfiltered count. |
| COA non-null | >= 90% | >= 70% | EDA: 73.5% have COA. 806 institutions (26.5%) lack both COSTT4_A and COSTT4_P. |
| NPT4_PUB lower bound | $0 | -$5,000 | EDA: 3 public schools have negative net prices (aid > COA). Min = -$1,180. |
| NPT4_PRIV lower bound | $0 | -$5,000 | EDA: Quintile-level values go negative (MIT Q1 = -$4,129). Consistency with pub rule. |
| TUITIONFEE_IN upper bound | $65,000 | $75,000 | EDA: Max = $69,330, exceeds spec threshold. Raised to $75K. |
| ROOMBOARD_ON floor | $3,000 | $1,000 | EDA: Legitimate minimum of $1,000. Subsidized or partial-year housing. |
| ROOMBOARD_ON ceiling | $25,000 | $30,000 | EDA: Max = $29,874, exceeds spec threshold. Raised to $30K. |
| Public NP coverage | >= 80% | >= 75% | EDA: 89.3% actual, but 75% provides margin for future refreshes. |
| Private NP coverage | >= 80% | >= 65% | EDA: 70.6% for CONTROL=2. Spec threshold would FAIL. |
| Quintile monotonicity | Adjacent Q(n) <= Q(n+1) | Only Q1 <= Q5 full-span | EDA: 37.9% Q1>Q2 inversions in private schools. Known College Scorecard pattern. |

## Rules Considered But Not Written

| Rule | Reason Not Written |
|------|-------------------|
| Freshness (load_date within 30 days) | Table does not exist yet -- ingestor has not been run. Will be added after first successful ingest. |
| UNITID valid 6-digit range | Could be added but deferred to avoid redundancy with UNITID not-null + uniqueness. The existing field-of-study DQ rules already validate UNITID format (RAW-CS-015). |
| COSTT4_P range check | Only 41 rows have COSTT4_P. Range ($11K-$48K) is within COSTT4_A bounds. Low value, deferred. |
| BOOKSUPPLY range check | Not in the 13 requested rules. EDA shows $0-$9,741, allows zero (32 schools include books in tuition). |
| For-profit net price coverage | CONTROL=3 only 52.6% populated. Too low for a meaningful threshold. Documented as known gap, not a DQ failure. |
| Adjacent quintile monotonicity | EDA definitively shows this is NOT a data quality issue: 37.9% Q1>Q2 inversions reflect legitimate merit aid patterns. |
| In-state <= out-of-state tuition | EDA shows 0 violations, but 72 public schools have equal values (legitimate). Not in requested rule set. |

## Execution Results

Rules could not be executed because the Iceberg table `raw.college_scorecard_institution` does not exist yet. The ingestor (Step 2) has been implemented but not run. DQ rule execution will occur at Step 5 (@dq-engineer).

## Output File

`governance/dq-rules/raw-ingest-college-scorecard-institution.json` -- 13 rules, 8 P0, 5 P1.
