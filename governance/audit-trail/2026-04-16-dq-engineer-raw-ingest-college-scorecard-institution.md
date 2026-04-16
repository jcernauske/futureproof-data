# Audit Trail: DQ Execution -- raw-ingest-college-scorecard-institution

**Date:** 2026-04-16T02:36:14Z
**Agent:** @dq-engineer
**Spec:** raw-ingest-college-scorecard-institution
**Action:** Execute 13 DQ rules against live College Scorecard Institution data

---

## Execution Summary

| Metric | Value |
|--------|-------|
| Run ID | c2578683 |
| Rules executed | 13 |
| Rules passed | 13 |
| Rules failed | 0 |
| Rules errored | 0 |
| P0 gate | PASS (7/7) |
| P1 rules | PASS (6/6) |
| Evidence hash | 84ad8e1b415d8734 |

## Execution Method

The Iceberg table `raw.college_scorecard_institution` does not yet exist. Data was downloaded from the source URL, processed through the ingestor's filter/coerce logic (PREDDEG=3 OR ICLEVEL=1, PrivacySuppressed to null, UNITID dedup), and loaded into an in-memory DuckDB instance for rule execution.

Source URL: `https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Institution_04172025.zip`

Note: The primary URL in the ingestor (`ed-public-download.app.cloud.gov`) returns 404. The alternate scorecard.network mirror was used. The ingestor may need a fallback URL update.

## Rules Executed

All 13 rules from `governance/dq-rules/raw-ingest-college-scorecard-institution.json` were executed:
- RAW-CSI-001 through RAW-CSI-013: ALL PASS

## Regressions

No prior runs exist for this spec. This is the baseline execution.

## P0/P1 Failures

None.

## Noteworthy Items

1. RAW-CSI-013 (quintile monotonicity) has 46 inversions against a 50-violation threshold -- monitor on future refreshes.
2. The primary download URL (app.cloud.gov) is returning 404. The ingestor should add a fallback URL to scorecard.network.
3. All data values match the EDA report exactly, confirming data stability.

## Artifacts Produced

- Results: `governance/dq-results/raw-ingest-college-scorecard-institution-20260416T023614Z.json`
- Scorecard: `governance/dq-scorecards/raw-ingest-college-scorecard-institution-scorecard.md`
- Execution script: `scripts/dq_execute_csi.py`

---

*Logged by @dq-engineer*
