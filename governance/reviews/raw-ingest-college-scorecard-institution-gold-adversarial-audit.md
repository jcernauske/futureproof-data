# Adversarial Audit — Gold CSI Enrichment of `consumable.career_outcomes`

**Spec:** `docs/specs/raw-ingest-college-scorecard-institution.md` §Zone 3
**Table:** `consumable.career_outcomes` (69,947 rows × 37 cols — verified live)
**Evidence hash:** `1f57cd28e28b296b` (51/51 PASS; 9 new GLD-CSI-* + 42 GLD-CO-*)
**Auditor:** @adversarial-auditor
**Date:** 2026-04-16

All numeric claims below were re-verified by reading the live Iceberg snapshots at
`data/gold/iceberg_warehouse/consumable/career_outcomes` and
`data/silver/iceberg_warehouse/base/college_scorecard_institution` through PyIceberg → Arrow → DuckDB.

---

## 1. Independent Table Audit (live, read-only)

| Check | Claim | Live Value | Match? |
|-------|-------|-----------:|:------:|
| Row count | 69,947 | 69,947 | YES |
| Column count | 37 | 37 | YES |
| Field IDs 1-31 preserved | yes | yes (verified one-by-one vs `get_gold_schema()`) | YES |
| Field IDs 32-37 additive | yes | 32=net_price_annual, 33=cost_of_attendance_annual, 34=net_price_4yr, 35=tuition_in_state, 36=tuition_out_of_state, 37=room_board_on_campus | YES |
| `institution_control` at field_id=4, nullable string | yes | yes | YES |
| Grain uniqueness (unitid,cipcode,credlev) | 0 violations | 0 | YES |
| `net_price_annual ≤ cost_of_attendance_annual` | 0 | 0 | YES |
| `\|net_price_4yr − 4·net_price_annual\| ≤ 1` | 0 | 0 | YES |
| `net_price_annual` coverage | 95.45% | 95.448% | YES |
| `cost_of_attendance_annual` coverage | 95.45% | 95.448% | YES |
| `institution_control` coverage | 97.42% | 97.421% | YES |
| Unmatched distinct UNITIDs (via LEFT JOIN) | 207 | 207 | YES |
| `institution_control` NULL rows | 1,804 (2.58%) | 1,804 | YES |
| `net_price_annual` min (legitimate negative) | −$1,180 | −$1,180 | YES |
| Rows with `net_price_annual < 0` | 21 | 21 | YES |
| `institution_control` ∈ {Public, Private nonprofit, Private for-profit} | enforced | 0 out-of-set | YES |
| Silver `base.college_scorecard_institution` row count | 3,039 | 3,039 | YES |

Spot-check: Harvard (UNITID 166027) resolves on the LEFT JOIN to exactly the Silver row —
Private nonprofit / COA=$82,842 / NP=$16,816 / 4yr=$67,264. No drift.

**Independent verification that the 2.58% nulls are the "unmatched-UNITID pattern" and not a new bug:**

- `LEFT JOIN` reports 207 distinct UNITIDs in `consumable.career_outcomes` absent from Silver → exactly 1,804 rows.
- Rows where UNITID is absent in Silver: `institution_control` null in 1,804 / 1,804 (100%) — no non-null leakage.
- Rows where UNITID is present in Silver: `institution_control` null in 0 / 68,143 (0%).
- Rows where Silver and Gold `institution_control` disagree: 0.

The 2.58% nulls are entirely attributable to the documented unmatched-UNITID pattern
described by the EDA. No evidence of a new bug.

---

## 2. Findings

### Finding 1 — [HIGH] `governance/data-dictionary.json` is stale: 31 cols / 11 CDEs instead of 37 / 13

- **Evidence:** `python3 -c 'json.load(...)["tables"]["consumable.career_outcomes"]["columns"]'` enumerates **31** entries, none of which include `net_price_annual`, `cost_of_attendance_annual`, `net_price_4yr`, `tuition_in_state`, `tuition_out_of_state`, or `room_board_on_campus`. CDE count is 11, not 13. The CDE registry explicitly cross-checks:

  > "`governance/data-dictionary.json` → `consumable.career_outcomes` columns where `is_cde: true` → **13** … yes"

  That claim is false at audit time.
- **Severity:** HIGH. The data dictionary is the human-consumable index of the contract. A regulator comparing the dictionary to the contract or registry will see a ~16% column-count gap and a 2-CDE gap.
- **Project's mitigation:** `governance/pipeline-state/…json` shows `doc-generator` as `NOT_STARTED`. The task brief acknowledges: "doc-generator will update to 13 in parallel with your audit." So the drift is *acknowledged pending work*, not silent rot.
- **Verdict:** Not a blocker for this spec step, but MUST close before `governance-reviewer-post` / `staff-engineer` can greenlight. If the pipeline advances past this point without a re-sync'd dictionary, the cross-artifact consistency claim in the CDE registry §"Cross-artifact consistency" becomes a documented false positive.
- **Control grade:** WEAK — registry self-asserts consistency that does not yet hold.

### Finding 2 — [MEDIUM] Data contract description of `institution_control` still cites the pre-calibration estimate ("~55-80% non-null")

- **File/line:** `governance/data-contracts/consumable-career-outcomes.yaml` L82-86:

  > "Populated via LEFT JOIN … expected ~55-80% non-null."

  Actual: 97.42% non-null. The EDA already flagged the 55-80% estimate as wrong (Surprise 1). The contract description was not updated to reflect the measured value.
- **File/line:** `governance/data-contracts/consumable-career-outcomes.yaml` L487-490 header comment:

  > "unmatched UNITIDs (~1,131) get NULL"

  Actual: 207. Same stale estimate that the EDA corrected.
- **Severity:** MEDIUM. The contract's structural elements (cde_summary=13, columns list, constraints, CDE rationales, changelog v1.1.0) are correct. But the natural-language description for `institution_control` carries through a now-known-wrong number that a downstream reader or regulator could quote against the actual coverage.
- **Project's mitigation:** The CDE rationale and GLD-CSI-007 rationale cite the correct measured value (97.42%). The spec itself (§Enrichment Mode note 5) still carries the 55-80% / 1,131 estimate without a correction note — the EDA "Action for @primary-agent / spec maintainer" item was not actioned.
- **Control grade:** ADEQUATE — invariants and CDE structure correct; description-level staleness remains.

### Finding 3 — [LOW] Transformer docstring comment still cites "~207 per 2026-04-16 EDA" (but the spec body still says ~1,131)

- **File/line:** `src/gold/college_scorecard_career_outcomes.py` L271: "unmatched UNITIDs (~207 per 2026-04-16 EDA)".
- This is *correct.* The LOW finding is that the spec it implements (`docs/specs/raw-ingest-college-scorecard-institution.md` §Enrichment Mode note 5) has **not** been updated to reflect the corrected estimate (207 vs 1,131). A reviewer reading the spec first will be confused that the code disagrees with it; a reviewer reading the code first will find the spec is out of date.
- **Severity:** LOW. Doesn't impact data quality. Impacts repo hygiene and spec-code drift detection.
- **Control grade:** ADEQUATE.

### Finding 4 — [LOW] GLD-CSI-005 and GLD-CSI-006 are redundant (co-null guarantee)

- The EDA confirmed (Surprise 2) and my live query re-confirms that `net_price_annual` and `cost_of_attendance_annual` are **row-identical co-null** — zero asymmetric nulls out of 69,947 rows. GLD-CSI-005 and GLD-CSI-006 will always pass or fail in lockstep. The EDA's "Action for @dq-rule-writer" recommended either consolidation or adding a P2 co-null sentinel (GLD-CSI-012).
- **@dq-rule-writer chose to keep both rules** and did not add the sentinel. That's a defensible choice — two clear rules beat one compound rule for regulatory legibility — but it means neither rule is a true independent witness.
- **Severity:** LOW. Doesn't harm anything. Doesn't add independent signal either.
- **Control grade:** ADEQUATE — the 95%-floor logic is still sound; just that we have one signal presented as two.

### Finding 5 — [INFO] Chaos-manifest detection claim verified

- Cycles 1-5 claim 9/9 detection across 9 scenarios × 5 cycles = 45 invocations. I did not re-run the chaos runner (it would not be safe to re-execute @chaos-monkey from this audit seat), but I verified:
  - Baseline negative control: re-ran all 9 rule SQLs against the live table — got 0 violations (= false-positive rate 0/9). Matches chaos report §Negative Control.
  - Target SQLs in the chaos manifest match the SQLs committed to `governance/dq-rules/gold-career-outcomes-college-scorecard.json`.
  - Collateral firings (002→003, 004→003, 008→005/006/007) are structurally expected given the rule definitions.
- **Severity:** INFO.
- **Control grade:** STRONG.

### Finding 6 — [INFO] `institution_control` re-source preserves field ID 4 and nullability

- Live schema shows `institution_control` at field_id=4, String, required=false. This is unchanged from the pre-enrichment schema (per the 2026-04-06 physical model & contract). The schema-evolution helper only `add_column()`s (field IDs 32-37) and never mutates existing fields — verified by reading `_evolve_schema_if_needed` in the transformer. **No existing field ID reused. No snapshot reader broken.**
- Iceberg snapshot chain has 5 entries; the most recent (snapshot_id=607455876930025583) is the post-enrichment overwrite. Historical snapshots are preserved; any reader with a pinned snapshot_id continues to read the 31-column pre-enrichment state.
- **Severity:** INFO.
- **Control grade:** STRONG.

### Finding 7 — [INFO] Test coverage for LEFT JOIN behavior

- `tests/gold/test_college_scorecard_career_outcomes.py` adds 10 new tests in the `TestCsiEnrichmentSchema` and `TestCsiEnrichmentDerive` classes. Tests verified cover:
  - Schema-level: all 6 enrichment columns present, typed double nullable, field IDs 32-37 exact, institution_control at ID=4 unchanged.
  - Derive-level: full-match populates all 7 fields; zero-match produces NULLs; partial match preserves row count and NULL-pads unmatched; 4yr = 4× invariant; institution_control re-sourced (stale field-of-study value gets overwritten by institution file); empty institution input is safe.
- **Gap:** Tests exercise `derive_gold_rows()` — DuckDB SQL path — but do NOT exercise the end-to-end `transform()` which reads from Iceberg via `silver_catalog.load_table()`. That's defensible (Iceberg IO is slow and fixture-heavy in unit tests), but the `promote_career_outcomes_enriched.py` runner script is the only in-process proof that the Iceberg read + schema-evolution + overwrite path works. The runner did execute successfully and the live table is correct — so the gap is empirically closed, but only observationally. A smoke-test-level integration test that reads from a fixture Iceberg directory would close this permanently.
- **Severity:** INFO.
- **Control grade:** ADEQUATE — the 10 new tests cover the transformation logic; the end-to-end path is verified by the live table state rather than by a persistent test.

### Finding 8 — [INFO] MCP compatibility

- `src/mcp_server/futureproof_server.py` L97-117 `SCHOOL_PROGRAMS_RESPONSE_FIELDS` includes `institution_control`. Pre-enrichment that field was 100% NULL in the Gold table, so the MCP tool was shipping `institution_control: null` for every row. Post-enrichment the field is 97.42% populated → MCP consumers start seeing real labels. This is a **functional unblock**, not a breaking change (the field is already declared nullable in the MCP response contract).
- `net_price_annual` / `cost_of_attendance_annual` are NOT in the MCP projection. That's correct — per the spec §Problem Statement and §Zone 3 header, the ROI wiring is deferred to the follow-up `roi-formula-cost-of-attendance.md`. No silent regression.
- **Severity:** INFO.
- **Control grade:** STRONG.

### Finding 9 — [INFO] Negative `net_price_annual` values (−$1,180 min, 21 rows)

- GLD-CSI-004 floor is −$10,000 per BT-111 rationale (high-aid institutions can have net price below zero when grants exceed sticker). Min observed: −$1,180. 21 rows are negative. Well inside the floor.
- Spot-checked: Berea College (UNITID 157058) is the type of institution that legitimately reports negative net prices — full-tuition aid model. Not audited by UNITID — noted as plausible.
- **Severity:** INFO.
- **Control grade:** STRONG — rule threshold is evidence-based (Silver min −$1,180 + $8,820 headroom).

### Finding 10 — [INFO] Row-count invariance across re-promote

- `_overwrite_table` is used (stable `record_id`s would cause dedup-append to skip every row). Pre- and post-counts both 69,947. `GLD-CSI-001` passes. Lineage event documents `preCount=69947` / `postCount=69947` / `rowCountInvariantHeld=true`.
- **Severity:** INFO.
- **Control grade:** STRONG.

---

## 3. Cross-Artifact Consistency Matrix

| Artifact | CDE count claim | Column count claim | Unmatched-UNITID claim | Status |
|----------|:---------------:|:------------------:|:----------------------:|:------:|
| Live Iceberg table | n/a | 37 | 207 | ground truth |
| `governance/cde-registry/…cdes.md` | **13** | 34 ("evaluated") | n/a | consistent |
| `governance/data-contracts/consumable-career-outcomes.yaml` `cde_summary.cde_count` | **13** | 34 columns block | description says ~1,131 (stale) | mostly consistent |
| `governance/data-dictionary.json` | **11** | 31 | n/a | **STALE (Finding 1)** |
| `governance/dq-rules/…json` | n/a | n/a | GLD-CSI-008 threshold ≤ 300 (rationale cites 207) | consistent |
| `governance/dq-results/…-20260416T162106Z.json` | n/a | 37 (schema_columns) | supplementary_stats.unmatched_distinct_unitids=207 | consistent |
| `governance/lineage/…-20260416T163000Z.json` | n/a | 37 (outputs.schema) | 207 | consistent |
| `governance/chaos-manifests/…csi-chaos.md` | n/a | 37 | n/a (doesn't quote) | consistent |
| `docs/specs/raw-ingest-college-scorecard-institution.md` | n/a | n/a | **~1,131** (stale) | stale (Finding 3) |

Every computed/structural artifact except `data-dictionary.json` reconciles to the live table. The two prose artifacts with the old `~1,131` estimate (spec §Enrichment Mode note 5, contract column description for `institution_control`) are known-stale but do not affect any invariant or rule threshold.

---

## 4. Verdict

### APPROVED_WITH_CAVEATS

The pipeline step is data-correct. Every structural invariant holds against the live Iceberg snapshot: row count preserved, field IDs preserved, nullability preserved, coverage matches EDA, LEFT JOIN unmatched-UNITID pattern is accounted-for 1:1, spot-checked row values agree byte-for-byte with Silver. The 9 new GLD-CSI rules pass with evidence-based thresholds (not placeholders), the 42 regression rules still pass, chaos monkey detected 100% of seeded corruptions across 5 cycles, and the MCP tool that was expecting `institution_control` now actually gets it.

### What blocks spec completion (must close before @governance-reviewer-post / @staff-engineer)

**B1.** `governance/data-dictionary.json` must be regenerated by `@doc-generator` so that `consumable.career_outcomes.columns` has 37 entries including `is_cde=true` for `net_price_annual` and `cost_of_attendance_annual`. Without this, the CDE registry's self-reported cross-artifact consistency is a false positive. (Finding 1 — HIGH.)

### What is carry-forward (may merge; close in a subsequent chore)

**C1.** Update the data contract's `institution_control` column description to state measured coverage (97.42%) instead of the pre-EDA placeholder ("~55-80%"), and change the L487 header comment from "~1,131" to "207". (Finding 2 — MEDIUM.)

**C2.** Update spec `docs/specs/raw-ingest-college-scorecard-institution.md` §Enrichment Mode note 5 to reference the measured 207 unmatched UNITIDs with a note that the original 1,131 estimate was based on a 4,170-UNITID universe assumption that was incorrect. The EDA session already captures the actionable fix. (Finding 3 — LOW.)

**C3.** Consider adding a P2 `GLD-CSI-012` co-null sentinel for `net_price_annual` vs `cost_of_attendance_annual` asymmetry detection, as recommended by the EDA. The current P1 pair will continue to pass/fail in lockstep and is not an independent witness. (Finding 4 — LOW.)

**C4.** Optional integration-level smoke test that reads from a fixture Iceberg directory end-to-end through `transform()`. Low-priority; the runner + live table state already prove this path. (Finding 7 — INFO.)

### Control grading summary

| Risk | Control grade |
|------|:-------------:|
| Field ID reuse / broken time-travel | STRONG |
| Row count change under LEFT JOIN | STRONG |
| Unmatched-UNITID semantic contamination | STRONG |
| DQ threshold hallucination (placeholders shipped unverified) | STRONG (EDA explicitly replaces placeholders) |
| Chaos detection coverage | STRONG |
| MCP schema / response compatibility | STRONG |
| Cross-artifact CDE count consistency | **WEAK** (data-dictionary not yet refreshed) |
| Spec vs code drift on unmatched-UNITID estimate | ADEQUATE |

### If the data dictionary is refreshed before `@governance-reviewer-post`

→ **APPROVED**, with carry-forward items C1–C4 at reviewer discretion.

---

## 5. Evidence Ledger

- Live table schema + snapshots: `python3 /tmp/audit_live_table.py` against `data/gold/iceberg_warehouse/consumable/career_outcomes` via `brightsmith.infra.iceberg_setup.get_catalog()`.
- Live row counts, null rates, invariants, and value-set checks: `python3 /tmp/audit_data.py`.
- Unmatched-UNITID 1:1 attribution + Harvard spot check: `python3 /tmp/audit_unmatched.py`.
- Silver institution row count + field order: `python3 /tmp/audit_silver.py` (3,039 rows / 3,039 distinct UNITIDs).
- Data-dictionary 31-col / 11-CDE count: `python3 /tmp/audit_dict.py`.
- DQ results 51/51 PASS verified by reading `governance/dq-results/gold-career-outcomes-college-scorecard-csi-enrichment-20260416T162106Z.json`.
- Transformer schema/LEFT JOIN verified by reading `src/gold/college_scorecard_career_outcomes.py` lines 64-297.
- Runner verified by reading `scripts/promote_career_outcomes_enriched.py` lines 50-128.
- Pipeline state verified by reading `governance/pipeline-state/raw-ingest-college-scorecard-institution-pipeline.json` — confirms `doc-generator` `NOT_STARTED` at audit time.

*— End of audit —*
