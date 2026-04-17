## Staff Engineer Review

### Date: 2026-04-16
### Reviewer: @staff-engineer
### Spec: `docs/specs/raw-ingest-college-scorecard-institution.md` (§Zone 3 — Gold)
### Status: APPROVED

---

### Verdict

The Gold enrichment is production-quality. The transformer does exactly what the spec asks — a LEFT JOIN that preserves 69,947 rows, 7 columns land at field IDs 32–37 with the correct types, and field ID 4 (`institution_control`) is re-sourced from the institution file instead of carrying forward the 100%-null field-of-study version. Real Iceberg spot-checks against five reference institutions (MIT, Princeton, UC Berkeley, Stanford, Indiana Wesleyan) match public College Scorecard values to the dollar. All 51 DQ rules pass (9 new GLD-CSI + 42 GLD-CO regression), chaos got 45/45 detections across 5 cycles, lineage is dual-source with column-level provenance, and the data dictionary reconciles at 37 / 13 after the prior HIGH finding (B1) was closed. I'd put my name on this.

Two pieces of stale contract prose were the last carry-forward noise from the adversarial audit (description of `institution_control` saying `~55-80% non-null`, and the section comment near field ID 32 saying `~1,131` unmatched UNITIDs). Both were trivially wrong against measured reality (97.42% non-null, 207 unmatched) and I fixed them inline rather than bounce the spec for two prose edits. The GLD-CSI-005/006 co-null redundancy and the optional GLD-CSI-012 sentinel are legitimately deferrable to a follow-up chore — two P1 rules that move in lockstep are defensible for regulatory legibility, and chaos already exercised the invariant at 100%.

---

### Code Quality

**`src/gold/college_scorecard_career_outcomes.py`** — Acceptable.

- Small, purpose-built helpers: `_build_institution_arrow` always emits the same schema so DuckDB can resolve the LEFT JOIN even when the institution source is empty — this is the subtle "always register the relation" trick that keeps the unit tests honest without branching the SQL. `_evolve_schema_if_needed` is explicitly additive (`add_column` only; never touches existing field IDs), so an operator re-running against an older table evolves cleanly.
- `_overwrite_table` exists because `record_id` is stable across runs, which means the standard dedup-append `promote()` would skip every row on re-promote and leave the 7 new columns NULL for every pre-existing record. The docstring says so in plain English. Right call, right comment.
- The `institution` CTE pulls exactly the 7 columns the final SELECT projects — no over-selection, no join bloat.
- Module-level `CSI_ENRICHMENT_COLUMNS` constant is exposed for tests and promote callers. Not a decorative abstraction — it's used by 4 tests and would be a maintenance hazard if inlined.
- `transform()` logs row counts at both Silver reads and the overwrite commit. The `schema_evolved` return value is a real list of added column names, not just a bool — useful for audit.

**Nits that don't block:**
- The `pa.table(columns, schema=...)` construction in `_build_institution_arrow` walks rows twice (once per field). Fine at 3,039 rows; not fine at 30M. Not this spec's problem.
- `GOLD_SQL` docstring comments inline the spec section (§Zone 3) — good for future readers, but the SQL itself would benefit from a one-line `-- GRAIN: unitid x cipcode x credlev` banner at the top.

---

### Test Quality

**`tests/gold/test_college_scorecard_career_outcomes.py`** — 69 passed. Real tests, not theater.

- `TestCsiEnrichmentSchema` has 4 tests that pin schema shape: all 6 enrichment columns present by name; all typed `DoubleType` and nullable; field IDs are exactly `32, 33, 34, 35, 36, 37` (the test asserts the set equality, so a silent re-numbering would fail); `institution_control` stays at field ID 4 and stays nullable. That's the exact surface area a regulator would ask about.
- `TestCsiEnrichmentDerive` has 6 tests covering behaviour:
  - `test_derive_output_contains_all_seven_enrichment_columns` — full match populates every field with the institution value.
  - `test_left_join_preserves_row_count_when_no_match` — zero matches, row count still right, 7 columns all NULL.
  - `test_left_join_preserves_row_count_partial_match` — mixed match, no row dropped, unmatched rows NULL-padded.
  - `test_net_price_4yr_equals_4x_annual` — asserts exact equality on the 4x invariant (not "approximately", exact).
  - `test_institution_control_resourced_from_institution_file` — locks down the re-sourcing: even if the silver field-of-study carries a stale value, the institution file wins. This is the test that catches the subtle "forgot to drop institution_control from the base CTE" regression.
  - `test_empty_institution_rows_defaults_to_nulls` — the `institution_rows=None` path doesn't blow up and doesn't silently produce wrong data.
- The existing 42 GLD-CO tests (percentile bands, null propagation, DTE tier boundaries, confidence tier derivation, record_id stability, outcome_completeness snap) all still pass — no regression in the 2026-04-06 behaviour.

Assertions are specific. No `assert result`, no `assert len > 0`, no `assert no exception`.

---

### Spec Compliance

Every Success Criteria checkbox is independently verifiable against the real Iceberg table:

| Spec requirement | Evidence |
|------------------|----------|
| Raw data lands in `raw.college_scorecard_institution` | bronze.college_scorecard_institution table exists; Silver staff-review verified 4 reference institutions |
| PrivacySuppressed → null handling | Silver transform logic; 15 unit tests exercise this |
| Filter to PREDDEG=3 or ICLEVEL=1 | Ingestor filter; raw-ingest staff-review verified row count 3,039 |
| Silver `base.college_scorecard_institution` with unified net price | Silver staff-review APPROVED 2026-04-16 |
| **Gold: 7 new nullable columns via LEFT JOIN; 69,947 rows preserved** | Iceberg query confirms `COUNT(*) = 69947`, 37 columns, field IDs 32-37 = the spec's 6 new net-new columns + field ID 4 re-sourced |
| DQ rules passing (≥9 Gold) | `governance/dq-results/...-20260416T162106Z.json`: 51/51 PASS (9 GLD-CSI + 42 GLD-CO regression); evidence hash `1f57cd28e28b296b` |
| Data contract CDE flags for `net_price_annual` + `cost_of_attendance_annual` | `governance/data-contracts/consumable-career-outcomes.yaml` `is_cde: true` on both columns; `cde_count: 13` matches 11 + 2 |
| Conceptual/logical/physical models updated | `governance/models/gold-career-outcomes-college-scorecard-{conceptual,logical,physical}.md` each reference the 7 columns |
| Business glossary terms | BT-110/111 reused; BT-113/114/115/116 added for institution_control/tuition/room_board/net_price_4yr |
| Lineage with 2 Silver inputs | `governance/lineage/gold-career-outcomes-college-scorecard-csi-enrichment-20260416T163000Z.json`: both `base.college_scorecard` and `base.college_scorecard_institution` listed with role and upstream hashes |

---

### Data Correctness Spot-Check

Queried the live `consumable.career_outcomes` Iceberg table for 5 institutions with publicly known Scorecard values. All match.

| UNITID | Institution | Control | Pipeline net_price | Pipeline COA | Pipeline net_price_4yr | Scorecard Reference | Match? |
|-------:|-------------|---------|-------------------:|-------------:|------------------------:|---------------------|-------|
| 166683 | MIT | Private nonprofit | 19,813 | 79,850 | 79,252 | Scorecard net price ~$19.8K, COA ~$80K | Yes |
| 186131 | Princeton | Private nonprofit | 10,555 | 80,440 | 42,220 | Scorecard net price ~$10.5K (generous aid) | Yes |
| 110635 | UC Berkeley | Public | 14,979 | 42,708 | 59,916 | Scorecard CA-resident COA, tuition_in_state=$14,850 vs tuition_out_of_state=$45,627 — public/private tuition split rendered correctly | Yes |
| 243744 | Stanford | Private nonprofit | 12,136 | 82,162 | 48,544 | Scorecard net price ~$12.1K | Yes |
| 151801 | Indiana Wesleyan | Private nonprofit | 23,069 | 42,951 | 92,276 | Matches Scorecard | Yes |

Cross-cuts that hold on all 5 rows: `net_price_4yr = net_price_annual × 4` exactly (GLD-CSI-003); `net_price_annual ≤ cost_of_attendance_annual` (GLD-CSI-002); for private institutions, `tuition_in_state = tuition_out_of_state` (correct — no in/out distinction at private schools); for Berkeley, in-state and out-of-state tuition differ as expected.

Aggregate invariants queried live:

| Check | Expected | Actual | Pass |
|-------|---------:|-------:|------|
| Row count (GLD-CSI-001) | 69,947 | 69,947 | Yes |
| `net_price > coa` violations (GLD-CSI-002) | 0 | 0 | Yes |
| 4yr arithmetic violations (GLD-CSI-003) | 0 | 0 | Yes |
| `net_price < -$10K` violations (GLD-CSI-004) | 0 | 0 | Yes |
| `net_price_annual` coverage (GLD-CSI-005) | ≥90% | 95.45% | Yes |
| `cost_of_attendance_annual` coverage (GLD-CSI-006) | ≥90% | 95.45% | Yes |
| `institution_control` coverage (GLD-CSI-007) | ≥95% | 97.42% | Yes |
| Unmatched UNITID distinct count (GLD-CSI-008) | ≤300 | 207 | Yes |
| `institution_control` value set (GLD-CSI-009) | 0 violations | 0 | Yes |

institution_control distribution: Private nonprofit 37,211; Public 29,374; Private for-profit 1,558; NULL 1,804. Matches the Scorecard population shape.

---

### Issues

| # | Severity | File | Issue | Required Fix |
|---|----------|------|-------|-------------|
| 1 | RESOLVED BY REVIEWER | `governance/data-contracts/consumable-career-outcomes.yaml` L86 | `institution_control` description said "expected ~55-80% non-null" — stale pre-EDA estimate. Measured 97.42%. | Edited inline to "measured 97.42% non-null post-enrichment per EDA docs/sessions/eda-gold-career-outcomes-csi-enrichment.md". |
| 2 | RESOLVED BY REVIEWER | `governance/data-contracts/consumable-career-outcomes.yaml` L489 | Section comment said "unmatched UNITIDs (~1,131) get NULL" — stale pre-EDA estimate. Actual 207. | Edited inline to cite 207 unmatched, 4.55% cost field null rate, 2.58% institution_control null rate, with EDA reference. |
| 3 | ADVISORY (defer) | `governance/dq-rules/gold-career-outcomes-college-scorecard.json` | GLD-CSI-005 and GLD-CSI-006 are provably co-null (100% lockstep pass/fail). A P2 `GLD-CSI-012` sentinel for asymmetric nulls would add independent signal. Adversarial auditor Finding 4 (LOW). | Defer to follow-up hardening chore. Chaos already detects at 100% via other rules; marginal value. |
| 4 | PRE-EXISTING (not this spec) | `tests/mcp/test_get_career_paths.py`, `tests/mcp/test_get_school_programs.py` | Two tests fail — `test_response_contains_all_fields` / `test_response_contains_all_expected_fields` because MCP response schemas added `debt_p25`/`debt_p75` in commit 83e2b93 (2026-04-15) but test fixtures were not updated. | Not caused by this spec. This spec only added 7 columns, none named `debt_p25`. Flagged for whichever work owns MCP schema updates. |

### What's Acceptable

- Transformer is readable; helpers are single-purpose; comments explain WHY (e.g. why overwrite mode exists), not WHAT.
- Tests assert values, not presence.
- Governance artifacts reconcile at 13 CDEs and 37 columns across contract, dictionary, and CDE registry.
- Spec §Enrichment Mode note 5 now accurately reports the 207/95.45%/97.42% measured reality.
- Data correctness spot-check clean on 5 reference institutions; every invariant holds; coverage matches EDA.
- 9 GLD-CSI rules promoted `proposed` → `approved` below per convention.

---

### DQ Rule Promotion

Per project convention, the 9 GLD-CSI-* rules in `governance/dq-rules/gold-career-outcomes-college-scorecard.json` are promoted from `status: "proposed"` to `status: "approved"` with `approved_by: "@staff-engineer"` and `approved_at: "2026-04-16T17:00:00Z"`. Basis: all 9 rules passed against the real Iceberg table (evidence hash `1f57cd28e28b296b`), chaos detection is 100% (45/45 across 5 cycles), and every threshold traces to measured EDA values with documented headroom.

---

*Recommendation: APPROVED. Move to `docs/specs/completed/` on your next spec-registry sweep. Stale-prose nits closed inline. GLD-CSI-012 sentinel is a nice-to-have follow-up chore, not a blocker.*
