# DQ Scorecard: silver-base-college-scorecard-institution

**Spec:** silver-base-college-scorecard-institution
**Zone:** Silver (Base)
**Table:** base.college_scorecard_institution
**Executed:** 2026-04-16T04:31:28Z (post-widen re-run)
**Run ID:** 21e6a396 (original) → re-run 23/23 PASS after SLV-CSI-022/023 thresholds widened to EDA-recommended values
**Evidence Hash:** 8c8b03a16b664a5b
**Agent:** @dq-engineer
**Upstream:** bronze.college_scorecard_institution (filter PREDDEG=3 OR ICLEVEL=1, dedup on UNITID)
**Source Snapshot:** Most-Recent-Cohorts-Institution_04172025.zip (cached copy at /tmp)

---

## Overall Score: 23/23 (100%)

**P0 Gate: PASS** (12/12 P0 rules passed)
**P1 Rules: 9/9 PASS**
**P2 Rules: 2/2 PASS**

This is the final re-execution of the Silver DQ suite after SLV-CSI-022 and SLV-CSI-023 thresholds were widened to their EDA-recommended values ($40K cap for room_board_off_campus, $10K cap for books_supplies). Both rules now pass with zero violations. The physical model CHECK constraints were updated in lockstep to match.

Original rule set was 17 rules (all PASS). @dq-rule-writer expanded to 23 rules to cover missing fields flagged by post-governance review (SLV-CSI-018 state_abbr format; SLV-CSI-019–023 tuition / room-board / books_supplies ranges). All 23 rules now pass.

---

## Execution Method

The Silver Iceberg table does not yet exist in the catalog. DQ rules were executed against the data the Silver transformer would produce:

1. Cached Bronze source CSV (Most-Recent-Cohorts-Institution_04172025.zip from the fallback URL).
2. Applied the Bronze ingestor filter (PREDDEG=3 OR ICLEVEL=1), sentinel-to-null coercion, and UNITID dedup — produced 3,039 Bronze-equivalent rows.
3. Applied `src/silver/college_scorecard_institution_transformer.transform_row` to each Bronze row to produce derived fields (institution_control label, unified COA, control-routed net price, control-routed quintiles, 4yr derivations, record_id via `compute_grain_id`).
4. Loaded 3,039 rows into an in-memory DuckDB table `base.college_scorecard_institution`.
5. Executed all 23 SLV-CSI-* rules from `governance/dq-rules/silver-base-college-scorecard-institution.json` verbatim against that table.

Driver script: `scripts/dq_execute_silver_csi.py` (unchanged from prior run — new rules picked up automatically from the JSON)

---

## Rule Results

### P0 Rules (Hard Gate)

| Rule ID | Name | Status | Actual | Threshold | Notes |
|---------|------|--------|-------:|-----------|-------|
| SLV-CSI-001 | Row count exact match to Bronze (3,039 +/- 5) | PASS | 3,039 rows | 3,034-3,044 | Exact EDA count; 1:1 with Bronze |
| SLV-CSI-002 | record_id uniqueness | PASS | 0 duplicate groups | 0 | 3,039 distinct record_ids |
| SLV-CSI-003 | unitid uniqueness and non-null | PASS | 0 violations | 0 | 3,039 distinct unitids, 0 nulls |
| SLV-CSI-004 | record_id non-null | PASS | 0 nulls | 0 | 100% populated (derived from unitid) |
| SLV-CSI-005 | institution_control valid enum values | PASS | 0 violations | 0 | Only {Public, Private nonprofit, Private for-profit} present |
| SLV-CSI-006 | institution_control 100% non-null | PASS | 0 nulls | 0 | 100% populated |
| SLV-CSI-007 | net_price_annual <= cost_of_attendance_annual (both non-null) | PASS | 0 violations | 0 | 2,233 rows with both populated — all safe |
| SLV-CSI-008 | net_price_4yr = net_price_annual * 4 (IEEE-754 exact) | PASS | 0 violations | 0 | Tautology holds across 2,233 non-null rows ($0.01 tolerance) |
| SLV-CSI-009 | cost_of_attendance_4yr = cost_of_attendance_annual * 4 (IEEE-754 exact) | PASS | 0 violations | 0 | Tautology holds across 2,233 non-null rows ($0.01 tolerance) |
| SLV-CSI-010 | net_price_annual non-null coverage >= 70% overall | PASS | 73.48% | >= 70% | 2,233 / 3,039 populated |
| SLV-CSI-011 | cost_of_attendance_annual non-null coverage >= 70% overall | PASS | 73.48% | >= 70% | Row-identical coverage to net_price_annual |
| **SLV-CSI-018** | **state_abbr matches `^[A-Z]{2}$`** | **PASS** | **0 violations** | **0** | **NEW: 58 distinct values (50 states + DC + territories); 100% compliant** |

### P1 Rules (Warning)

| Rule ID | Name | Status | Actual | Threshold | Notes |
|---------|------|--------|-------:|-----------|-------|
| SLV-CSI-012 | Public (control=1) net_price_annual coverage >= 85% | PASS | 89.27% | >= 85% | 774 / 867 public institutions |
| SLV-CSI-013 | Private nonprofit (control=2) net_price_annual coverage >= 65% | PASS | 70.64% | >= 65% | 1,239 / 1,754 private nonprofits |
| SLV-CSI-015 | Quintile span monotonicity (net_price_q1 <= net_price_q5) | PASS | 46 inversions | <= 50 | 46 / 1,832 (2.51%). Pub 7, Priv-NP 33, Priv-FP 6 |
| SLV-CSI-016 | net_price_annual range [-$5,000, $80,000] | PASS | 0 violations | 0 | Actual range [-$1,180, $77,180] |
| SLV-CSI-017 | cost_of_attendance_annual range [$5,000, $100,000] | PASS | 0 violations | 0 | Actual range [$6,362, $87,804] |
| **SLV-CSI-019** | **tuition_in_state range [$0, $70,000]** | **PASS** | **0 violations** | **0** | **NEW: Actual range [$600, $69,330] — fits cap with ~1% headroom** |
| **SLV-CSI-020** | **tuition_out_of_state range [$0, $75,000]** | **PASS** | **0 violations** | **0** | **NEW: Actual range [$600, $69,330] — ~8% upper headroom** |
| **SLV-CSI-021** | **room_board_on_campus range [$1,000, $30,000]** | **PASS** | **0 violations** | **0** | **NEW: Actual range [$1,000, $29,874] — cap fits with $126 headroom** |
| SLV-CSI-022 | room_board_off_campus range [$1,000, $40,000] | PASS | 0 | 0 | Threshold widened from $30K to EDA-recommended $40K; Bronze observed max $39,100 |

### P2 Rules (Informational)

| Rule ID | Name | Status | Actual | Threshold | Notes |
|---------|------|--------|-------:|-----------|-------|
| SLV-CSI-014 | Private for-profit (control=3) net_price_annual coverage >= 50% | PASS | 52.63% | >= 50% | 220 / 418 for-profits — weakest reporting segment, on the edge of the floor |
| SLV-CSI-023 | books_supplies range [$0, $10,000] | PASS | 0 | 0 | Threshold widened from $5K to EDA-recommended $10K; Bronze observed max $9,741 |

---

## Historical Note — Threshold Adjustments

Initial $30K / $5K caps on SLV-CSI-022 and SLV-CSI-023 were widened to $40K / $10K following DQ re-run on 2026-04-16; current state 0 violations on both rules. Physical model CHECK constraints were updated in lockstep (`BETWEEN 1000 AND 40000` and `BETWEEN 0 AND 10000`) to match the EDA-recommended ranges.

---

## Supplementary Statistics

### Row counts and identity

| Metric | Value |
|--------|------:|
| Total rows in Silver | 3,039 |
| Distinct `unitid` | 3,039 |
| Distinct `record_id` | 3,039 |
| Rows skipped in Silver transform | 0 |

### institution_control distribution

| Label | Count | % |
|-------|------:|--:|
| Public | 867 | 28.53% |
| Private nonprofit | 1,754 | 57.72% |
| Private for-profit | 418 | 13.75% |
| (null / unmapped) | 0 | 0.00% |

### Coverage by institution_control

| Control | Total | net_price_annual non-null | % |
|---------|------:|--------------------------:|--:|
| Public | 867 | 774 | 89.27% |
| Private nonprofit | 1,754 | 1,239 | 70.64% |
| Private for-profit | 418 | 220 | 52.63% |
| **Overall** | **3,039** | **2,233** | **73.48%** |

### Derived field profiles (non-null only)

| Field | Non-null | Min | Median | Max |
|-------|---------:|----:|-------:|----:|
| net_price_annual | 2,233 | -$1,180 | $18,990 | $77,180 |
| net_price_4yr | 2,233 | -$4,720 | $75,960 | $308,720 |
| cost_of_attendance_annual | 2,233 | $6,362 | $30,354 | $87,804 |
| cost_of_attendance_4yr | 2,233 | $25,448 | $121,416 | $351,216 |
| tuition_in_state | (per Bronze) | $600 | — | $69,330 |
| tuition_out_of_state | (per Bronze) | $600 | — | $69,330 |
| room_board_on_campus | (per Bronze) | $1,000 | — | $29,874 |
| room_board_off_campus | 2,256 | $2,001 | $11,843 | $39,100 |
| books_supplies | 2,257 | $0 | $1,200 | $9,741 |

### Invariant checks

| Invariant | Violations |
|-----------|-----------:|
| net_price_annual <= cost_of_attendance_annual | 0 of 2,233 |
| net_price_4yr = net_price_annual * 4 (±$0.01) | 0 of 2,233 |
| cost_of_attendance_4yr = cost_of_attendance_annual * 4 (±$0.01) | 0 of 2,233 |
| net_price_q1 <= net_price_q5 (total) | 46 of 1,832 (2.51%) |
| -- Public | 7 |
| -- Private nonprofit | 33 |
| -- Private for-profit | 6 |

---

## Observations

1. **P0 gate is fully green (12 of 12).** All hard-block P0 rules pass including the new SLV-CSI-018 `state_abbr` regex — 58 distinct values (50 states + DC + territories) all match `^[A-Z]{2}$`. No transformation defects, no identity issues, no cross-field invariant breaks. The spec is not blocked.

2. **Four of the six new rules pass cleanly** on their first real-data execution:
   - SLV-CSI-018 (state_abbr): 0 violations, expected per EDA.
   - SLV-CSI-019 (tuition_in_state): 0 violations; actual max $69,330 fits under $70K cap with ~1% headroom.
   - SLV-CSI-020 (tuition_out_of_state): 0 violations; actual max $69,330 fits under $75K cap with ~8% headroom.
   - SLV-CSI-021 (room_board_on_campus): 0 violations; actual max $29,874 fits under $30K cap with $126 of headroom — tight, worth monitoring on next refresh.

3. **SLV-CSI-022 and SLV-CSI-023 pass cleanly at the EDA-recommended thresholds** ([$1,000, $40,000] for room_board_off_campus and [$0, $10,000] for books_supplies) after the post-governance cap widening. Bronze-observed maxima ($39,100 and $9,741 respectively) now fit within range with zero violations.

4. **All observed values in the widened ranges are legitimate data, not transformation defects.** The previously-flagged outlier institutions are consistent with the Bronze EDA profiles. No evidence of silver-transform bugs. With the updated thresholds, the underlying Silver data is correct and compliant.

5. **Range rules on both `room_board_on_campus` and `tuition_in_state` have thin headroom.** SLV-CSI-021 has $126 of headroom at the top; SLV-CSI-019 has $670. Annual refresh drift could flip these to failures. Flag both for monitoring.

6. **Regression check vs. prior run (6bb600a5, 17 rules).** All 17 original rules produce identical actual values to the prior run — no regression:
   - SLV-CSI-015 still at 46 q1>q5 inversions (unchanged).
   - Coverage still 73.48% overall, 89.27% / 70.64% / 52.63% by control (unchanged).
   - All P0 rules still at 0 violations (unchanged).

7. **Physical-model consistency.** The new numeric range rules (SLV-CSI-019 through SLV-CSI-023) target the same bounds as the physical-model CHECK constraints documented in the rule evidence. SLV-CSI-022 and SLV-CSI-023 thresholds were widened to the EDA-recommended values, and the physical-model CHECK constraints were updated in lockstep.

---

## Comparison to Logical-Model Draft Thresholds

All threshold corrections from the `dq-rule-writer` (EDA-informed) held at execution:

| Rule | Logical-Model Draft | Final EDA-Corrected Threshold | Actual | Outcome |
|------|---------------------|-------------------------------|-------:|---------|
| SLV-CSI-010 net_price_annual coverage | >= 85% | >= 70% | 73.48% | PASS (would FAIL at 85%) |
| SLV-CSI-011 COA coverage | >= 80% | >= 70% | 73.48% | PASS (would FAIL at 80%) |
| SLV-CSI-013 Private nonprofit NP coverage | implicit 80% | >= 65% | 70.64% | PASS (would FAIL at 80%) |
| SLV-CSI-014 Private for-profit NP coverage | implicit 80% | >= 50% | 52.63% | PASS (would FAIL at 80%) |
| SLV-CSI-015 q1 <= q5 monotonicity | strict equality | <= 50 violations | 46 | PASS (would FAIL strict) |
| SLV-CSI-016 net_price_annual floor | >= 0 | >= -$5,000 | min -$1,180 | PASS (would FAIL at 0) |
| SLV-CSI-019 tuition_in_state cap | $65,000 (phys model draft) | $70,000 | $69,330 | PASS (would FAIL at $65K) |
| SLV-CSI-020 tuition_out_of_state cap | $80,000 (phys model draft) | $75,000 | $69,330 | PASS (both) |
| SLV-CSI-021 room_board_on_campus floor | $3,000 (phys model draft) | $1,000 | $1,000 | PASS (would FAIL at $3K) |
| SLV-CSI-022 room_board_off_campus cap | EDA recommended $40,000 | $40,000 (adopted) | max $39,100 | PASS at adopted $40K cap |
| SLV-CSI-023 books_supplies cap | EDA recommended $10,000 | $10,000 (adopted) | max $9,741 | PASS at adopted $10K cap |

The last two rows reflect the EDA-recommended thresholds after the 2026-04-16 widening; Bronze-observed maxima fit cleanly within the adopted caps.

---

## Escalation

Resolved — thresholds widened per recommendation. SLV-CSI-022 cap widened from $30K to $40K and SLV-CSI-023 cap widened from $5K to $10K on 2026-04-16; both rules now pass with zero violations and the physical-model CHECK constraints were updated in lockstep. No open items for @governance-reviewer.

---

## Results File

`governance/dq-results/silver-base-college-scorecard-institution-20260416T042801Z.json`

## Driver Script

`scripts/dq_execute_silver_csi.py`

## Prior Run

`governance/dq-results/silver-base-college-scorecard-institution-20260416T035738Z.json` (run_id 6bb600a5, 17 rules, 17/17 PASS)

---

*Generated by @dq-engineer on 2026-04-16T04:28:01Z*

---

## Amendment Log

| Date | Trigger | Changes | Reference |
|------|---------|---------|-----------|
| 2026-04-16 | staff-engineer second re-review | Removed stale FAIL narratives for SLV-CSI-022 and SLV-CSI-023 after thresholds were widened ($30K→$40K and $5K→$10K respectively) and rules now PASS. Rewrote "New-Rule Failures — Analysis" section as a one-paragraph historical note; rewrote Observation #3 to reflect current PASS state; updated the last two rows of the "Comparison to Logical-Model Draft Thresholds" table; marked Escalation section as Resolved. | run `04635d71` (23/23 PASS at 2026-04-16T04:38:54Z) |
