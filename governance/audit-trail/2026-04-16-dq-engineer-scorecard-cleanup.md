# Audit Trail: DQ Scorecard Cleanup — silver-base-college-scorecard-institution

**Date:** 2026-04-16
**Agent:** @dq-engineer
**Spec:** silver-base-college-scorecard-institution
**Trigger:** @staff-engineer CHANGES REQUIRED in second re-review at
`governance/reviews/silver-base-college-scorecard-institution-staff-review.md`
(the scorecard body still narrated SLV-CSI-022 and SLV-CSI-023 as FAILING
even though the 2026-04-16T04:38:54Z run — `04635d71` — is 23/23 PASS after
the threshold widening).

## Why

The scorecard header and rollup were already correct (23/23 PASS, P0 gate green)
but the body retained stale FAIL narratives for SLV-CSI-022 and SLV-CSI-023
that had been true only at the narrower $30K / $5K caps. Those caps were
widened to the EDA-recommended $40K / $10K values, and both rules now pass
with zero violations. Staff-engineer flagged the mismatch between the header
and body as blocking spec completion.

## What changed

File: `governance/dq-scorecards/silver-base-college-scorecard-institution-scorecard.md`

1. Collapsed the "New-Rule Failures — Analysis" section into a one-paragraph
   "Historical Note — Threshold Adjustments" describing the widening and
   current zero-violation state.
2. Rewrote Observation #3 to state that SLV-CSI-022 and SLV-CSI-023 now pass
   cleanly at the EDA-recommended thresholds (replaced the "fail by
   construction" language).
3. Adjusted Observation #4 to describe legitimate data within the widened
   ranges rather than framing rows as violations.
4. Updated Observation #7 to note that the physical-model CHECK constraints
   were updated in lockstep with the widened rule thresholds.
5. Updated the last two rows of the "Comparison to Logical-Model Draft
   Thresholds" table to reflect the adopted $40K / $10K caps and the PASS
   outcomes, and rewrote the trailing sentence.
6. Rewrote the "Escalation" section as "Resolved — thresholds widened per
   recommendation."
7. Appended an Amendment Log table at the bottom of the scorecard referencing
   run `04635d71`.

## What did NOT change

- DQ rules were not re-executed (already 23/23 PASS at run `04635d71`).
- JSON rule definitions and the JSON result file were not modified.
- The scorecard header, rollup, per-rule result rows, and supplementary
  statistics were left intact.
