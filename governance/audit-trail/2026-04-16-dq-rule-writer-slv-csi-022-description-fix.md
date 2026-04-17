# Audit Trail — DQ Rule Writer (SLV-CSI-022 Description Fix)

- **Date:** 2026-04-16
- **Agent:** @dq-rule-writer
- **Spec:** silver-base-college-scorecard-institution
- **Trigger:** @staff-engineer second re-review, CHANGES REQUIRED (lines 245–246 of `governance/reviews/silver-base-college-scorecard-institution-staff-review.md`)
- **Target:** `governance/dq-rules/silver-base-college-scorecard-institution.json` — rule SLV-CSI-022 only

## Scope

Text-only amendment. Only the `description` field on SLV-CSI-022 was rewritten. The `name`, `sql`, `evidence`, `threshold`, and `priority` fields were not touched, and no other rule was modified.

## Finding

Prior to this fix, SLV-CSI-022's `description` read with an outdated "$30,000" upper bound plus a trailing justification sentence defending the $30K cap — inconsistent with the already-widened `name`, `sql`, and `evidence` that all reference the [$1,000, $40,000] range. The submission note had claimed the description was in sync; staff-engineer re-review found it was not.

## Change

**Old `description`:**

> "When non-null, room_board_off_campus must be between $1,000 and $40,000. Bronze observed max is $39,100 (high-cost metro areas including California institutions). Physical model CHECK updated to BETWEEN 1000 AND 40000 to match. Low-cost off-campus living exists at institutions with inexpensive surrounding housing markets; high-cost values are legitimate at metro schools."

**New `description`:**

> "When non-null, room_board_off_campus must be between $1,000 and $40,000. Bronze observed max is $39,100 at high-cost-metro institutions (including California schools). Physical model CHECK updated to BETWEEN 1000 AND 40000 to match."

Style mirrors SLV-CSI-023's already-accepted description: state the widened range, cite Bronze-observed max as supporting evidence for the cap, then a one-line physical-model reconciliation note. Trailing $30K-cap justification sentence removed.

## Validation

- `python3 -c "import json; json.load(...)"` parses cleanly (23 rules preserved).
- No occurrence of "$30,000" in connection with `room_board_off_campus` remains in the file.
- No other rule modified.
