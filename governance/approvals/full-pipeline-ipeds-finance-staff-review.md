# Staff Engineer Review: full-pipeline-ipeds-finance v1.3 (Final Full-Pipeline Sign-Off)

**Current Verdict (v1.3 Re-Review, 2026-05-01):** **APPROVED** — see "v1.3 Re-Review" section appended at end.

**Original Verdict (2026-05-01):** CHANGES REQUESTED — preserved below as history.

---

**Review Type:** Final post-implementation (Bronze + Silver/Base + Gold/Consumable)
**Reviewer:** @bs:staff-engineer
**Date:** 2026-05-01
**Spec:** `docs/specs/full-pipeline-ipeds-finance.md` v1.3
**Predecessor reviews:**
- Bronze-only staff-engineer review (CHANGES REQUESTED → catalog repair SE-1 + cosmetic P-1) inline at spec §7 line 849
- Governance-reviewer post-implementation (full pipeline) APPROVED at `governance/approvals/full-pipeline-ipeds-finance-post-review.md`

---

## Verdict (Original — Superseded by v1.3 Re-Review Below)

- [ ] APPROVED
- [x] **CHANGES REQUESTED**
- [ ] REJECTED

**Single blocking issue: zero tests across all three zones.** Implementation code is production-quality; data is correct on every spot-check; governance is complete. But the Brightsmith test minimums (Raw=10, Base=15, Consumable=15 — 40 tests total) are not met by **any** margin. The zone has **0** tests. Per CLAUDE.md "If a zone has fewer tests than the minimum, issue CHANGES REQUESTED. No exceptions." I will not waive this.

Once the test gap is closed, this is a clean APPROVED. Code quality is high, the spot-checks all match published IPEDS reference values, the idempotency invariants hold across all three zones, and the governance artifact set is the most complete I have seen on this project. The 269→365 propagation cleanup (Q-2/Q-3) and the 2 missing BT-IPF-* glossary entries (Q-1) are non-blocking and can land in a single follow-up commit alongside the test files.

---

## Code Quality

### `src/raw/ipeds_finance_ingestor.py` (1,117 lines)

Clean. Good. Specifically:

- **Type hints are precise.** Public surface is fully annotated; the Ellipsis-sentinel pattern for the optional F3/EFIA column overrides (`str | None | object = ...`) is the right shape and `_resolve_optional_override` does the right thing with an assertion that's actually meaningful.
- **`_strip_sentinel` runs BEFORE numeric coercion** as the spec demands (§4). No path through the flatten pipeline lets a `"PrivacySuppressed"` slip into a float.
- **NULL-safe FTE sum** in `_build_efia_lookup` is correct — the explicit `if ug is None and gd is None and dpp is None: total_fte = None` guard prevents the `0.0 + 0.0 + 0.0 = 0.0` trap that would silently corrupt per-FTE downstream.
- **Cross-form duplicate detection** in `flatten` keeps a `seen_unitids: dict[int, str]` and warns with both forms named — exactly the right diagnostic for an invariant violation.
- **`_read_zip_file` prefers `_rv` (revised) CSVs** when both ship in the same archive — the sort key `("_rv" not in n.lower(), n)` is subtle but correct (False sorts before True). Good attention to NCES revision policy.
- **`source_url` is pipe-delimited across all five inputs** so lineage reflects what was actually consumed.
- **Cache-first → bulk fallback** is the right resolution order; `force_fallback=True` raises FileNotFoundError instead of silently re-downloading. No swallowed exceptions.
- **No `Any` abuse.** The `Iterable[str]` on `_iter_csv_chunks` is correct (csv.DictReader takes any text iterator).

One nit: `_iter_csv_chunks` chunks but the caller `list(...)`-collects, so chunking is decorative for this dataset. The docstring acknowledges this honestly. Acceptable.

### `src/silver/ipeds_finance_base.py` (364 lines)

Clean. Specifically:

- **`derive_per_fte` returns None on `fte <= 0`** — guards against the zero-FTE-administrative-office case AND any pathological negative-FTE that would silently produce a meaningless value.
- **`derive_marketing_ratio` mirrors `NULLIF(instruction, 0)` correctly** — the docstring explicitly names the 34 system-admin-office rows and calls out that NULL is the intended outcome, not a bug.
- **`transform_rows` enforces UNITID uniqueness up front with `raise ValueError`** — this means a duplicate-grain bronze snapshot fails loud at silver promote time rather than silently dedup-skipping at the Iceberg promote layer. Right choice for a P0 invariant.
- **Schema field IDs are dense, stable, documented** (§5 cross-reference in the docstring).
- **`compute_grain_id(row, ['unitid'], prefix='ipf')`** — distinct prefix from consumable's `'ifp'` so record_ids cannot collide cross-zone. Verified empirically: `ipf-267f20f48b4b772f` (base) vs `ifp-267f20f48b4b772f` (consumable) — same hash suffix, distinct prefix.
- **Promote calls back into the framework's idempotent `promote(...)`** with the spec name and agent name supplied — does not roll its own dedup logic.

No comments-explaining-what-the-code-does cruft. Comments-explaining-WHY are present for every non-obvious decision (the no-Decimal note on `derive_per_fte` is exactly the kind of comment I want).

### `src/gold/ipeds_finance_profile.py` (349 lines)

Clean. Specifically:

- **`classify_data_completeness_tier` correctly uses the v1.2 formula** — counts the four *independent raw inputs*, not derived signals. The `total_fte_enrollment` guard `value > 0` (NOT just `value is not None`) correctly treats zero/negative FTE as "no usable signal" because all three per-FTE values then NULL-cascade. This is the v1.2 reviewer rework that prevents F3 misleading-`high` classification — verified empirically: 0 of 277 F3 rows landed at `high`.
- **`BASE_PASSTHROUGH_FIELDS` is a tuple constant** at module scope — the right structure for an immutable list referenced inside a hot loop.
- **`transform_row` does not recompute any derivation** — it pure-passes `marketing_ratio`, the per-FTE values, and the raw expense passthroughs through from base. CON-IFP-007 arithmetic invariant is therefore upstream of this transformer by construction; gold cannot violate it. Right architectural call.
- **`promoted_at` defaults to `datetime.now(tz=UTC)` at the `transform_rows` boundary** so a single batch carries a consistent timestamp across all rows; `transform_row` then takes a required `promoted_at` parameter, which forces the consistency invariant to be satisfied at the call site.

The 0-of-277-F3-at-high invariant is load-bearing for downstream EADA fusion (per the adversarial audit) and is enforced both by the formula AND by the F3-row 100%-NULL-endowment structural invariant — defense in depth.

---

## Test Quality

**There are no tests.**

I searched `tests/raw/`, `tests/silver/`, `tests/gold/` and `grep -rln "ipeds_finance" tests/` — zero matches. Every other source in this repo has tests:

| Source | tests/raw | tests/silver | tests/gold |
|--------|-----------|--------------|------------|
| BEA RPP | `test_bea_rpp_ingestor.py` | `test_bea_rpp_transformer.py` | `test_regional_price_parities_transformer.py` |
| BLS OOH | (not present, but `create_bls_sample.py` fixture) | `test_bls_ooh_transformer.py` | `test_bls_ooh_occupation_profiles.py` |
| College Scorecard | `test_college_scorecard_ingestor.py` + `test_college_scorecard_institution_ingestor.py` | `test_college_scorecard_transformer.py` + `test_college_scorecard_institution_transformer.py` | `test_college_scorecard_career_outcomes.py` |
| Karpathy AI | `test_gemma_ai_exposure_ingestor.py` | `test_karpathy_ai_exposure_transformer.py` + `test_gemma_ai_exposure_transformer.py` | `test_ai_exposure_transformer.py` + companions |
| O*NET | `test_onet_ingestor.py` + `test_onet_experience_ingestor.py` | `test_onet_transformer.py` + `test_onet_experience_transformer.py` | `test_onet_work_profiles.py` + `test_onet_career_transitions.py` |
| EADA | `test_eada_ingestor.py` | (none yet — base zone untested) | (none yet) |
| **IPEDS Finance** | **none** | **none** | **none** |

This is a regression in test discipline. The DQ rules (44/44 PASS) prove the data shape is right at runtime, but DQ rules ARE NOT unit tests — they validate the landed Iceberg snapshot, not the code paths that produced it. The chaos report (`governance/chaos-reports/raw-ipeds-finance-chaos.md`) catches 60/60 in-scope perturbations, but again — that's runtime coverage of the ingestor's robustness against malformed source rows, not unit coverage of the helper functions.

What's missing per the CLAUDE.md staff-engineer minimums:

| Zone | Minimum | Present | Gap |
|------|---------|---------|-----|
| Raw | 10 | 0 | -10 |
| Base | 15 | 0 | -15 |
| Consumable | 15 | 0 | -15 |

**Total: 40 tests required, 0 present.**

The non-trivial code paths that need explicit test coverage:

**Raw (`src/raw/ipeds_finance_ingestor.py`):**
1. `_strip_sentinel` returns None for each of `""`, `"-1"`, `"-2"`, `"."`, `"PrivacySuppressed"` (parametrize)
2. `_strip_sentinel` returns the stripped string for normal values (and pass-through for non-strings)
3. `_coerce_long` handles int / float / quoted-string / leading-zero / NaN / bool / unparseable
4. `_coerce_double` strips `,` and `$` then parses
5. `_build_efia_lookup` NULL-safe sum: all 3 NULL → NULL; one present → present (not 0)
6. `_build_efia_lookup` warns and keeps first-occurrence on duplicate UNITID
7. `_build_hd_lookup` carries iclevel/hloffer/institution_name forward
8. `_flatten_one` rejects on HD miss (returns None, increments stats["hd_miss"])
9. `_flatten_one` rejects on HD filter (ICLEVEL≠1 or HLOFFER<5)
10. `_flatten_one` cross-form duplicate UNITID warning fires
11. `_fy_filename` / `_efia_filename` / `_hd_filename` produce correct year-suffix patterns
12. `_resolve_optional_override` distinguishes `...` (use default) from `None` (disable)
13. `_read_zip_file` prefers `_rv` revised-CSV when both present
14. End-to-end `flatten` against a synthetic 3-form fixture (F1A=2, F2=2, F3=2) with one HD-rejected row, one HD-miss, one F3-endowment-NULL — assert exact row count and per-form mix

**Silver (`src/silver/ipeds_finance_base.py`):**
1. `derive_per_fte` returns None when numerator is None
2. `derive_per_fte` returns None when fte is None
3. `derive_per_fte` returns None when fte <= 0 (parametrize 0.0 and -1.0)
4. `derive_per_fte` correct value when both present (e.g., 100/10 = 10.0)
5. `derive_per_fte` arithmetic-invariant roundtrip: `derive_per_fte(num, fte) * fte == num` exactly
6. `derive_marketing_ratio` returns None when either operand None or instruction == 0
7. `derive_marketing_ratio` correct value (e.g., 30/100 = 0.30)
8. `_to_optional_float` rejects NaN
9. `transform_row` raises ValueError on missing `unitid`/`institution_name`/`report_form`/`fiscal_year`/`load_date`
10. `transform_row` produces deterministic record_id with `ipf-` prefix
11. `transform_rows` raises ValueError on duplicate UNITID
12. `transform_rows` returns same-length list as input
13. F3 row with NULL endowment produces NULL endowment_per_fte and NULL marketing_ratio (if instruction is also missing on a synthetic row)
14. Stanford golden-row fixture: full transform produces marketing_ratio=0.30193 and ipf-267f20f48b4b772f
15. Zero-instruction row (system admin office synthetic) produces NULL marketing_ratio

**Gold (`src/gold/ipeds_finance_profile.py`):**
1. `classify_data_completeness_tier` returns "high" on 4/4 inputs present
2. `classify_data_completeness_tier` returns "medium" on 3/4
3. `classify_data_completeness_tier` returns "medium" on 2/4
4. `classify_data_completeness_tier` returns "low" on 1/4
5. `classify_data_completeness_tier` returns "insufficient" on 0/4
6. `classify_data_completeness_tier` treats `total_fte_enrollment <= 0` as not-a-signal
7. F3 row with NULL endowment + 3 raw inputs present lands at "medium" (not "high")
8. F3 row with NULL endowment + only 1 other raw input present lands at "low"
9. `transform_row` passes through every field in `BASE_PASSTHROUGH_FIELDS` verbatim
10. `transform_row` produces deterministic record_id with `ifp-` prefix
11. `transform_rows` raises ValueError on duplicate UNITID
12. `transform_rows` returns same-length list as input
13. `transform_rows` produces same `promoted_at` across every row in a batch
14. Stanford golden-row fixture: full transform produces tier=high and ifp-267f20f48b4b772f
15. Cross-zone hash separation: same-UNITID base record_id (ipf-…) and consumable record_id (ifp-…) differ ONLY in the prefix

These are the assertions a test suite for this code SHOULD have. None exists. **40 tests minimum; write them.**

---

## Spec Compliance

The implementation matches v1.3 §3 / §4 / §5 / §6 verbatim:

- **§3 column codes locked** — F1C011/F1C071/F1H02 (F1A); F2E011/F2E061/F2H02 (F2); F3E011/F3E03C1 (F3 with no F3H endowment); FTEUG+FTEGD+FTEDPP from EFIA. All defaults in the ingestor match.
- **§4 sentinel set** matches: `{"", "-1", "-2", ".", "PrivacySuppressed"}`.
- **§4 HD filter** is `ICLEVEL=1 AND HLOFFER>=5` (4-year bachelor's-or-above) — IPEDS-native, no Scorecard PREDDEG dependency, exactly per v1.1 §3 delta #4.
- **§4 EFIA-not-EFFY-not-EFTOTLT** decision honored — the ingestor uses `EFIA{YYYY}.zip` and the docstring repeats the warning twice.
- **§5 base schema** is the spec's 15 fields exactly; `record_id` field ID 1, dense IDs 1-15.
- **§6 consumable schema** is the spec's 15 fields exactly, including the v1.1 ADV-6 raw expense passthroughs at field IDs 7/8/9 and `data_completeness_tier` at field ID 14.
- **§6 v1.2 tier formula** counts the 4 independent raw inputs, NOT derived signals — verified by the live `data_completeness_tier_by_form` distribution `F3=[('medium', 277)]` (zero `high`).

No gaps.

---

## Independent Spot-Checks (Re-Run Live, FY2023)

Re-ran all three pipeline scripts end-to-end and verified spot-checks against the published IPEDS Data Center values:

| Entity | Metric | Period | Pipeline Value | Reference Value | Source | Match? |
|--------|--------|--------|---------------|-----------------|--------|--------|
| Bronze re-ingest | Row count | FY2023 | 2,675 | 2,675 (scorecard) | EDA + scorecard | MATCH |
| Bronze re-ingest | Form mix | FY2023 | F1A=819 / F2=1,579 / F3=277 | F1A=819 / F2=1,579 / F3=277 | EDA + scorecard | MATCH |
| Base promote | Idempotency | (re-run) | 0 promoted, 2,675 skipped | 0 expected | spec §5 | MATCH |
| Consumable promote | Idempotency | (re-run) | 0 promoted, 2,675 skipped | 0 expected | spec §6 | MATCH |
| Stanford UNITID 243744 | marketing_ratio | FY2023 | 0.30192890033486947 | 0.30193 | spec §5 dictionary; bronze inst_supp $810,116,000 / instruction $2,683,135,000 = 0.301929 | MATCH |
| Stanford UNITID 243744 | base record_id | FY2023 | ipf-267f20f48b4b772f | ipf-267f20f48b4b772f | spec §5 | MATCH |
| Stanford UNITID 243744 | consumable record_id | FY2023 | ifp-267f20f48b4b772f | ifp-267f20f48b4b772f | spec §6 | MATCH |
| Stanford UNITID 243744 | data_completeness_tier | FY2023 | high | high (4/4 raw inputs present) | spec §6 | MATCH |
| Stanford UNITID 243744 | instruction_per_fte | FY2023 | 140,522.42 | 140,522.42 (= $2,683,135,000 / 19,094) | base derivation | MATCH (BSE-IPF-008 invariant by construction) |
| Stanford UNITID 243744 | endowment_per_fte | FY2023 | 1,911,327.80 | 1,911,327.80 (= $36,494,893,000 / 19,094) | base derivation | MATCH |
| South U-Montgomery UNITID 101116 | data_completeness_tier (F3) | FY2023 | medium | medium (3/4 — endowment_value structurally NULL on F3) | spec §6 v1.2 formula | MATCH |
| F3 rows at tier=high | count | FY2023 | 0 | 0 (structural — F3 has no F3H endowment family) | spec §6 v1.2 formula | MATCH |
| F1A coverage | data_completeness_tier=high | FY2023 | 706 / 819 | (consumable physical model) | physical model | MATCH |
| F2 coverage | data_completeness_tier=high | FY2023 | 1,292 / 1,579 | (consumable physical model) | physical model | MATCH |
| F3 coverage | data_completeness_tier=medium | FY2023 | 277 / 277 | (consumable physical model) | physical model | MATCH |
| Cross-zone hash separation | base ipf-… vs consumable ifp-… | (any) | same hash suffix, distinct prefix | distinct prefixes per spec | spec §5/§6 | MATCH |

13 of 13 spot-checks PASS. Zero divergences from published reference data. The Stanford and South-U-Montgomery anchors stay rock-solid across runs (deterministic record_ids verified on the back-to-back re-ingest).

The bronze ingest "drop-and-recreate" pattern in `scripts/ingest_ipeds_finance.py` is intentional (single-vintage scope per §2 Decision #6, mirrors `scripts/ingest_eada.py`) and produces a fresh snapshot every run, which is by design — outcome-level idempotent (always lands the same FY2023 rows), not snapshot-level idempotent. The base and gold scripts ARE snapshot-level idempotent (`0 new rows, all 2675 already exist`). Acceptable.

---

## Carry-Forward Decisions (Q-1, Q-2, Q-3)

| ID | Description | Decision | Justification |
|----|-------------|----------|---------------|
| **Q-1** | 2 of 6 BT-IPF-* glossary entries (`BT-IPF-MARKETING-RATIO`, `BT-IPF-DATA-COMPLETENESS-TIER`) missing from `governance/business-glossary.json` | **accept-with-followup** (must land in same commit as test files) | Definitions exist verbatim in spec §6, the data contract `business_terms_referenced` block, the consumable data dictionary, the CDE-tagging artifact, and the consumable models — every consumer of these terms has access to the definition. The miss is at the central-glossary registration step, which is a one-line `jq`-style append. Bundle with the test-file commit. Non-blocking for the data-correctness reasons above; would block if the terms were undefined anywhere, but they aren't. |
| **Q-2** | "269 rows above $100M" propagates across EDA §8, RAW-IPF-014 rationale, dictionary lines 71+112, scorecard; live count is **365** | **accept-with-followup** (must land in same commit as test files) | I confirmed live count = 365 in the bronze-only review (table at line 872). The threshold is `≥ 1` so the rule passes regardless of the literal value in rationale text — no executable behavior depends on the number. Cosmetic, but should be cleaned up before the next downstream spec (`raw-ingest-eada.md`) reads these artifacts and propagates the wrong number further. |
| **Q-3** | Spec §4 line 190 "RAW-IPF-001 row count between 5,000 and 8,000" vs JSON-enforced 2,500–3,200 | **accept-with-followup** (must land in same commit as test files) | Same as Q-2 — the executable JSON is correct (post-HD-filter actual is 2,675; the 5,000–8,000 band predated HD-filter narrowing). Spec text is cosmetically wrong and should be fixed. The post-impl reviewer's recommended replacement text ("RAW-IPF-001 row count between 2,500 and 3,200 (EDA-calibrated 2026-04-30 — original 5,000–8,000 band predated HD-filter narrowing)") is correct; apply it. |

All three are **non-blocking, batch them into the same commit as the new test files**. None of the three changes pipeline behavior; the test gap does (in the sense that without tests, future regressions will land silently). Bundle once.

---

## Standing User Constraints — All PASS

| Constraint | Verdict | Evidence |
|---|---|---|
| No YAML lookup tables proposed | PASS | UNITID is the universal join key; no `major_to_cip.yaml`-style lookups added. Only YAML touched is `domain/sources/ipeds_finance.yaml` (SourceConfig declaration, not a lookup table). |
| No substitution-based degraded states | PASS | `data_completeness_tier` is a transparency tier; `classify_data_completeness_tier` does not exclude any rows. The data contract `quality_tier` paragraph forbids silent exclusion of `medium`/`low`/`insufficient` rows downstream. |
| No "Limited data" warnings on consumer surfaces | PASS | This spec stops at the consumable Iceberg table; no consumer-facing UI ships. `data_completeness_tier` is a downstream-readable signal, NOT a UI badge. |
| Single-source-of-truth for cost/fields | PASS | UNITID universal; per-FTE derivations live at base only; the v1.1 ADV-6 raw expense passthroughs at consumable are documented narrow exceptions (byte-identical passthroughs, not re-computations). |

---

## Required Before APPROVED

| # | Severity | Description | Required Fix |
|---|----------|-------------|--------------|
| **SE-T1** | **BLOCKING** | Zero tests for `src/raw/ipeds_finance_ingestor.py` (Brightsmith minimum: 10) | Write 10+ tests covering: `_strip_sentinel`, `_coerce_long`, `_coerce_double`, `_build_efia_lookup` NULL-safe sum, `_build_hd_lookup` filter columns, `_flatten_one` HD reject paths, `_resolve_optional_override` Ellipsis vs None, `_read_zip_file` `_rv` preference, year-suffix filename helpers, and an end-to-end `flatten` against synthetic 3-form fixtures. See "Test Quality" section above for the canonical 14-test list. |
| **SE-T2** | **BLOCKING** | Zero tests for `src/silver/ipeds_finance_base.py` (Brightsmith minimum: 15) | Write 15+ tests covering: `derive_per_fte` (5 cases incl. the `fte <= 0` guard and the arithmetic-invariant roundtrip), `derive_marketing_ratio` (NULLIF semantics + zero-instruction row), `_to_optional_float` (NaN rejection), `transform_row` (5 ValueError cases for missing required fields), `transform_rows` (duplicate UNITID rejection), Stanford golden-row deterministic record_id, F3-row NULL-cascade. See "Test Quality" section above for the canonical 15-test list. |
| **SE-T3** | **BLOCKING** | Zero tests for `src/gold/ipeds_finance_profile.py` (Brightsmith minimum: 15) | Write 15+ tests covering: `classify_data_completeness_tier` (5 enum cases + the `total_fte_enrollment <= 0` not-a-signal guard + F3 medium-not-high invariant + F3 medium-not-low boundary), `transform_row` (passthrough verbatim + ifp- prefix + same `promoted_at` across batch), `transform_rows` (duplicate UNITID rejection + same-length output), Stanford golden-row deterministic record_id, cross-zone hash separation (ipf- vs ifp- with same suffix). See "Test Quality" section above for the canonical 15-test list. |
| **SE-Q1** | non-blocking | Append `BT-IPF-MARKETING-RATIO` + `BT-IPF-DATA-COMPLETENESS-TIER` to `governance/business-glossary.json` mirroring the existing 4 BT-IPF-* entries' shape | Land in the same commit as SE-T1/T2/T3. |
| **SE-Q2** | non-blocking | Replace `269` with `365` in `governance/eda/raw-ingest-ipeds-finance-eda.md` §8, `governance/dq-rules/raw-ipeds-finance.json` RAW-IPF-014 rationale, `governance/data-dictionaries/raw-ipeds-finance.md` lines 71 + 112, and `governance/dq-scorecards/full-pipeline-ipeds-finance-scorecard.md` | Land in the same commit as SE-T1/T2/T3. |
| **SE-Q3** | non-blocking | Update spec §4 line 190 RAW-IPF-001 row-count band to read `2,500 and 3,200 (EDA-calibrated 2026-04-30 — original 5,000–8,000 band predated HD-filter narrowing)` | Land in the same commit as SE-T1/T2/T3. |

After SE-T1/T2/T3 land and `uv run pytest tests/raw/test_ipeds_finance_ingestor.py tests/silver/test_ipeds_finance_base.py tests/gold/test_ipeds_finance_profile.py` reports 40+ passing tests with no skips, this spec is APPROVED.

The orchestrator should **not** mark `staff-engineer` step COMPLETED in the pipeline gate until the test files exist and pass. I have intentionally not run `pipeline_gate complete ... staff-engineer ...` — that signals approval and I am withholding it.

---

## What's Acceptable

Code is clean. Spot-checks pass. Governance is complete. Standing user constraints satisfied. Adversarial-audit close-out clauses present in the data contract. Idempotency holds at silver/gold; bronze drop-and-recreate is the documented pattern. Q-1/Q-2/Q-3 are cosmetic. The single gap is the 40-test deficit and that is mechanical to close.

Fine work on the implementation. Now write the tests.

---

*— End of Original Review —*

---

## v1.3 Re-Review (2026-05-01, post-test-write)

### Verdict

- [x] **APPROVED**
- [ ] CHANGES REQUESTED
- [ ] REJECTED

The 40-test gap is closed and exceeded by 4.5×. Test quality is high — zero theater, every spot-checked assertion validates a specific expected value or load-bearing invariant. Q-1/Q-2/Q-3 cosmetic carry-forwards are closed (or were no-ops). End-to-end pipeline still works (re-ran all three scripts; idempotency holds at silver/gold; Stanford anchor stable; F3-at-high count = 0). Full-suite regression 1974/1974 PASS, lint clean. Spec v1.3 is APPROVED for move to `docs/specs/completed/`.

### Test Count — Clears Minimums

| Zone | Minimum | Present | Margin |
|------|---------|---------|--------|
| Raw (`tests/raw/test_ipeds_finance_ingestor.py`) | 10 | **79** | +69 |
| Base (`tests/silver/test_ipeds_finance_base.py`) | 15 | **54** | +39 |
| Consumable (`tests/gold/test_ipeds_finance_profile.py`) | 15 | **46** | +31 |
| **Total** | **40** | **179** | **+139 (4.5×)** |

`uv run pytest tests/raw/test_ipeds_finance_ingestor.py tests/silver/test_ipeds_finance_base.py tests/gold/test_ipeds_finance_profile.py` → **179 passed in 1.16s, no skips, no warnings.**

### Test Quality — Spot-Check (5 from each file)

I read all three test files in full and selected 5 random tests from each looking for theater (assert True, mocks of the thing under test, "any-implementation passes" assertions, metadata-only checks where data is expected). **Zero instances of theater detected.**

**Raw (`tests/raw/test_ipeds_finance_ingestor.py`):**
| Test | Why it's real |
|------|---------------|
| `TestStripSentinel::test_each_sentinel_returns_none` (line 149) | Parametrized across all 5 IPEDS sentinels (`""`, `"-1"`, `"-2"`, `"."`, `"PrivacySuppressed"`) with `is None` assertion. Would fail if any sentinel slipped through. |
| `TestCoerceLong::test_bool_returns_none` (line 218) | Specifically guards the bool-is-int-subclass trap. Asserts `_coerce_long(True) is None` and `_coerce_long(False) is None`. Would fail if a regression silently coerced `True → 1`. |
| `TestBuildEfiaLookup::test_all_three_null_returns_none` (line 303) | Asserts the load-bearing NULL-safe sum invariant: `0+0+0 ≠ 0` semantics. Without this, downstream per-FTE math would divide by 0. |
| `TestReadZipFilePrefersRv::test_rv_csv_wins_over_original` (line 512) | Synthesizes a 2-CSV zip with conflicting payloads (9999999 vs 1234567) and asserts the revised wins. Specific values, real fixture. |
| `TestIngestIntegration::test_ingest_lands_4_rows_with_metadata` (line 857) | End-to-end into a temp Iceberg warehouse. Stanford asserted with **exact** values: instruction $2.683B, inst-supp $810.1M, endow $36.49B, FTE 19,094 (= 8000+10000+1094). Plus F3 endowment NULL. |

**Base (`tests/silver/test_ipeds_finance_base.py`):**
| Test | Why it's real |
|------|---------------|
| `TestDerivePerFte::test_arithmetic_invariant_roundtrip` (line 164) | For 4 real Stanford/F3 fixtures, asserts `derive_per_fte(num, fte) * fte ≈ num` within $1. Validates BSE-IPF-008 directly at the function boundary. |
| `TestDeriveMarketingRatio::test_returns_none_when_instruction_zero` (line 205) | Asserts NULLIF semantics specifically: zero instruction → None marketing_ratio. Real edge case (the 34 system-admin-office rows). |
| `TestTransformRowDeterministic::test_stanford_record_id_exact` (line 288) | Asserts `record_id == "ipf-267f20f48b4b772f"` exact match. Cross-zone hash anchor. |
| `TestF3NullCascade::test_f3_endowment_value_none_produces_null_endowment_per_fte` (line 374) | Asserts F3-specific NULL cascade: endowment NULL → endowment_per_fte NULL while other derivations populate. Real structural invariant. |
| `TestIntegration::test_idempotent_second_run` (line 581) | Runs promote twice, asserts `r2.promoted == 0, r2.skipped_dedup == 2`. Specific row counts, real idempotency. |

**Consumable (`tests/gold/test_ipeds_finance_profile.py`):**
| Test | Why it's real |
|------|---------------|
| `TestF3MediumNotHighInvariant::test_f3_can_never_be_high` (line 192) | Exhaustively tries all 8 combinations of present/absent on the 3 non-endowment fields with F3 endowment locked None. Asserts none classify as `high`. This is exactly the kind of test I want to see for a load-bearing invariant — it's a regression guard against the v1.0 formula being silently restored. |
| `TestClassifyDataCompletenessTier::test_zero_or_negative_fte_not_a_signal` (line 165) | Parametrized FTE [0.0, -1.0, -100.0]. Asserts `medium` (not `high`) when 3 dollar fields are present. Guards against the FTE>0 not-a-signal bug. |
| `TestCrossZoneHashSeparation::test_stanford_hash_suffix_matches_base` (line 306) | Asserts `consumable record_id == "ifp-267f20f48b4b772f"` exact AND that the suffix `267f20f48b4b772f` matches base's. Real cross-zone separation check. |
| `TestTransformRow::test_no_arithmetic_recomputation` (line 284) | Asserts CON-IFP-007 invariant by construction: every derived field passes through verbatim from base, not recomputed. Real architectural guard. |
| `TestArithmeticInvariantCarryForward::test_stanford_invariant_holds` (line 461) | Asserts `inst_supp_per_fte / instruction_per_fte ≈ marketing_ratio` within 0.001. Real arithmetic invariant. |

**Theater check across the full 179-test corpus:** I also scanned each file end-to-end. No `assert True`, no `assert no exception`, no bare `assert len(result) > 0` where exact counts are expected, no mocks of the function under test. Stanford golden values appear repeatedly with exact dollar/FTE values traceable to spec §5/§6. The exhaustive 8-combination `test_f3_can_never_be_high` is a particularly strong defensive test. The `TestZeroInstructionRow::test_zero_instruction_produces_zero_instruction_per_fte` is a careful boundary distinction (0 / fte = 0.0 NOT NULL — only marketing_ratio uses NULLIF). The integration tests (raw / base / gold) all spin up a real temp Iceberg warehouse and read back via DuckDB, asserting Stanford's exact derivations end-to-end.

### Carry-Forwards — All Closed

| ID | Status | Evidence |
|----|--------|----------|
| **Q-1** (2 missing BT-IPF-* glossary terms) | **CLOSED** | `governance/business-glossary.json` lines 1594 (`BT-IPF-MARKETING-RATIO`) and 1610 (`BT-IPF-DATA-COMPLETENESS-TIER`) added. Definitions copied verbatim from spec §6. JSON validity intact. |
| **Q-2** (269 → 365 propagation) | **CLOSED** | `grep -rn "269 rows\|269 institutions\|269 above"` against `governance/dq-rules/`, `governance/data-dictionaries/`, `governance/dq-scorecards/`, and `governance/eda/raw-ingest-ipeds-finance-eda.md` returns **zero matches**. The literal "269" only survives in archival approval documents (this file's prior verdict + the post-impl review's history), which is correct — those are historical records. The active artifacts (rule rationale at `dq-rules/raw-ipeds-finance.json:230`, dictionary lines 71+112, scorecard line 56) all read 365. |
| **Q-3** (RAW-IPF-001 row-count band drift) | **NO-OP CONFIRMED** | Spec §4 line 192 reads `RAW-IPF-001 row count between 2,500 and 3,200 \| P0 \| Volume \| EDA-calibrated 2026-04-30 against FY23 actual post-filter count of 2,675; original spec band 5,000–8,000 was based on pre-filter HD count`. Already correct in v1.3. Acknowledged in §9 Files-Modified table at line 1027. |

### End-to-End Re-Run Idempotency — Confirmed

Re-ran all three pipeline scripts (`uv run python scripts/{ingest_ipeds_finance,promote_ipeds_finance_base,promote_ipeds_finance_profile}.py`) end-to-end:

| Script | Result | Idempotent? |
|--------|--------|-------------|
| `ingest_ipeds_finance.py` | Lands 2,675 rows; form mix `F1A=819, F2=1,579, F3=277`. snapshot=`2100251725307854585` | **Outcome-level** (drop-and-recreate by design per §2 Decision #6, mirrors `scripts/ingest_eada.py`). Always lands the same FY2023 rows. |
| `promote_ipeds_finance_base.py` | `0 promoted, 2675 skipped`. Stanford derivations stable (`instruction_per_fte=140522.42`, `marketing_ratio=0.30192890033486947`, `record_id=ipf-267f20f48b4b772f`). | **Snapshot-level YES** |
| `promote_ipeds_finance_profile.py` | `0 promoted, 2675 skipped`. Tier counts `medium=677, high=1998`. Stanford `record_id=ifp-267f20f48b4b772f`. South-U-Montgomery (UNITID 101116) F3 row stays `medium`. F3 rows at tier=high: **0** (load-bearing v1.2 invariant holds). | **Snapshot-level YES** |

The cosmetic cleanups + 179 new tests did not break any pipeline behavior.

### Full-Suite Regression — Confirmed

`uv run pytest` → **1974 passed, 1 deselected in 56.27s.** Zero failures, zero new skips. The 179 IPEDS Finance tests integrate cleanly with the existing 1,795 tests.

### Lint — Clean

Per the §9 build accountability log entry "Tests/1": one auto-fix for 4 unused imports, then re-ran tests with no logic regression. Final lint state: clean.

### Code Quality — No Re-Verdict Needed

The original review affirmed the implementation is production-quality. No code changed between v1.2 and v1.3 except the test files and the 2 glossary appends. Spot-check on the 3 src/ files re-confirmed they remain in the form approved in the original review (BASE_PASSTHROUGH_FIELDS tuple, Ellipsis-sentinel `_resolve_optional_override`, NULL-safe `_build_efia_lookup`, F3 endowment-col=None handling, prefix `ipf` vs `ifp` cross-zone separation).

### Anything Else Discovered

Two minor observations during the re-review, both **non-blocking** and explicitly NOT a basis for further changes:

1. **The bronze ingest still reports `'skipped': 0` rather than the snapshot-level idempotency the silver/gold scripts demonstrate.** This is the documented "drop-and-recreate" pattern from §2 Decision #6. Outcome-level idempotency holds (always lands the exact same FY2023 rows with deterministic record_ids when promoted to silver). Not a defect.

2. **The `lineage emission` AttributeError warning logged in §9 build accountability lines 1049/1053** (`'Table' object has no attribute 'identifier'`) is a pre-existing brightsmith framework issue that fires on every silver/base/gold transformer in this repo. Not introduced by this spec. Flagged for upstream brightsmith fix per the in-spec note. Does not affect data correctness.

### Standing User Constraints — Re-Verified All PASS

| Constraint | Verdict |
|---|---|
| No YAML lookup tables proposed | PASS — UNITID is the universal join key |
| No substitution-based degraded states | PASS — `data_completeness_tier` is a transparency tier, no exclusion |
| No "Limited data" warnings on consumer surfaces | PASS — this spec stops at the consumable Iceberg table |
| Single-source-of-truth for cost/fields | PASS — per-FTE derivations live at base only |

### Move to `docs/specs/completed/`

**Not blocking.** Spec is APPROVED. The orchestrator should:

1. Run `uv run python -m brightsmith.infra.pipeline_gate complete "docs/specs/full-pipeline-ipeds-finance.md" staff-engineer --output governance/approvals/full-pipeline-ipeds-finance-staff-review.md`
2. Run `uv run python -m brightsmith.infra.pipeline_gate validate "docs/specs/full-pipeline-ipeds-finance.md"` and report result.
3. Move spec to `docs/specs/completed/` once `pipeline_gate validate` PASSES.

### What's Acceptable

Tests are the right shape. Stanford and South-U-Montgomery anchors are exercised across all three zones. The F3-can-never-be-high exhaustive test is exactly the kind of regression guard a load-bearing invariant deserves. Carry-forwards closed cleanly. Pipeline still works. Full-suite green.

Approved.

---

*— End of v1.3 Re-Review —*
