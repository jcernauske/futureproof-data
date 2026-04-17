# Audit Trail — DQ Rule Writer (Silver Base College Scorecard Institution — Post-Governance Amendment)

- **Date:** 2026-04-14
- **Agent:** @dq-rule-writer
- **Spec:** silver-base-college-scorecard-institution
- **Trigger:** Post-governance review findings (SLV-CSI-post)
- **Target:** `governance/dq-rules/silver-base-college-scorecard-institution.json`

## Scope

Post-governance review identified six field-level validity rules missing from the original 17-rule proposal (SLV-CSI-001..017). This amendment appends SLV-CSI-018 through SLV-CSI-023 to close the gaps for `state_abbr`, `tuition_in_state`, `tuition_out_of_state`, `room_board_on_campus`, `room_board_off_campus`, and `books_supplies`.

## Rules Added

| Rule ID | Dimension | Priority | Target | Threshold |
|---------|-----------|----------|--------|-----------|
| SLV-CSI-018 | validity | P0 | `state_abbr` matches `^[A-Z]{2}$` | 0 violations |
| SLV-CSI-019 | validity | P1 | `tuition_in_state` in [$0, $70,000] when non-null | 0 violations |
| SLV-CSI-020 | validity | P1 | `tuition_out_of_state` in [$0, $75,000] when non-null | 0 violations |
| SLV-CSI-021 | validity | P1 | `room_board_on_campus` in [$1,000, $30,000] when non-null | 0 violations |
| SLV-CSI-022 | validity | P1 | `room_board_off_campus` in [$1,000, $30,000] when non-null | 0 violations |
| SLV-CSI-023 | validity | P2 | `books_supplies` in [$0, $5,000] when non-null | 0 violations |

Existing rules SLV-CSI-001..017 were not re-ordered or modified.

## Threshold Evidence (EDA — docs/sessions/eda-silver-base-college-scorecard-institution.md)

- **SLV-CSI-018** — EDA validity row: "state_abbr matches ^[A-Z]{2}$, regex, 0 violations, 58 distinct (50 states + DC + territories), 100%, P0, Will pass." The logical model sets the field as NOT NULL and the physical model carries `CHECK (state_abbr ~ '^[A-Z]{2}$')`. Threshold 100%.
- **SLV-CSI-019** — EDA Bronze range `[$600, $69,330]`. Cap raised from the draft physical CHECK of $65K to $70K (EDA recommendation).
- **SLV-CSI-020** — EDA Bronze range `[$600, $69,330]`. Post-governance review elected $75K (instead of the EDA-recommended $70K) to give additional headroom; physical model CHECK tightened from $80K to $75K.
- **SLV-CSI-021** — EDA Bronze range `[$1,000, $29,874]`. The draft physical CHECK of `[3000, 25000]` was wrong on both ends. Widened to `[$1,000, $30,000]` to match observed evidence.
- **SLV-CSI-022** — EDA Bronze range `[$2,001, $39,100]`. Post-governance review harmonized to `[$1,000, $30,000]` for symmetry with on-campus floor; off-campus outliers above $30K represent high-cost metros and will be treated as informational outliers rather than hard violations in Silver. Physical model CHECK updated from `[3000, 30000]` to `[1000, 30000]`.
- **SLV-CSI-023** — EDA Bronze range `[$0, $9,741]`. Post-governance review retained the physical model CHECK of `[$0, $5,000]` and downgraded the rule from EDA-recommended P1 to P2: books_supplies is an estimate rather than a transactional amount, so values above $5K are more likely data-entry artifacts than legitimate cost data.

## Physical Model Reconciliation

The user's brief called out a mismatch between the physical model's CHECK constraints and the actual EDA evidence. Reconciliation was performed (option A): the physical model was updated in-place rather than the rule file being annotated with a discrepancy note.

`governance/models/silver-base-college-scorecard-institution-physical.md` changes:

- `tuition_in_state` CHECK: `BETWEEN 0 AND 65000` → `BETWEEN 0 AND 70000`
- `tuition_out_of_state` CHECK: `BETWEEN 0 AND 80000` → `BETWEEN 0 AND 75000`
- `room_board_on_campus` CHECK: `BETWEEN 3000 AND 25000` → `BETWEEN 1000 AND 30000`
- `room_board_off_campus` CHECK: `BETWEEN 3000 AND 30000` → `BETWEEN 1000 AND 30000`
- `books_supplies` CHECK: unchanged (`BETWEEN 0 AND 5000` still matches the new rule)
- `state_abbr` CHECK: unchanged (`CHECK (state_abbr ~ '^[A-Z]{2}$')` already matched)

Both the per-column table (line ~145) and the DDL CHECK block (line ~387) were updated for consistency. Column-level descriptions now carry a trailing note citing the post-governance amendment.

## Validation

- JSON structure validated — file parses cleanly, 23 rules total, rule IDs SLV-CSI-001..023 in order.
- Rules were not executed against live data: the Silver base table has not yet been materialized (task #24 "Silver post-governance and staff engineer" is in-progress). Rules will be validated alongside SLV-CSI-001..017 during the Silver DQ execution run. This is consistent with the `proposed` status carried by all 23 rules.

## Rules Considered But Not Written

- **Dedicated negative-value rule for tuition/room-board fields.** Covered by the range rules' lower bounds (0 or 1,000). No separate rule needed.
- **Cross-field relationship between tuition_in_state and tuition_out_of_state** (in <= out). EDA does not include an invariant check for this pair and public-institution pricing typically satisfies it by definition; private institutions report a single rate in both fields. Deferred to a future consistency rule if an EDA pass identifies violations.
- **EDA-recommended range for books_supplies at [$0, $10,000] (P1).** Post-governance review elected the tighter [$0, $5,000] range at P2. This is an intentional scope narrowing: books_supplies outliers in Bronze (up to $9,741) will be flagged as informational P2 violations in Silver, giving the DQ scorecard visibility into the anomaly without failing the Silver zone. The physical model CHECK remains enforcing at DDL level.

## Files Changed

- `governance/dq-rules/silver-base-college-scorecard-institution.json` — appended SLV-CSI-018..023 (6 new rules)
- `governance/models/silver-base-college-scorecard-institution-physical.md` — updated 4 CHECK constraints (tuition_in_state, tuition_out_of_state, room_board_on_campus, room_board_off_campus) in both the column table and the DDL block; added post-governance amendment notes to column descriptions
