# Principal Data Architect Review — silver-base-bea-rpp

**Date:** 2026-04-16
**Reviewer:** @principal-data-architect
**Scope:** Silver → Gold transition, spec `silver-base-bea-rpp` (retroactive)
**Spec status at review time:** Silver COMPLETE, staff-engineer signed off 2026-04-10 (APPROVED WITH CONDITIONS).
**Domain:** U.S. state cost-of-living (BEA Regional Price Parities) — salary purchasing-power adjustment reference.

---

## Executive Summary

`base.bea_rpp` is the smallest and cleanest Silver table in the FutureProof pipeline, and it earns that reputation. It is a 51-row closed-set reference table (50 states + DC), a 1:1 promote from Bronze with three derivations (`state_abbr`, `census_region`, `purchasing_power_multiplier`) and one per-row provenance column (`verification_status`) that cleanly discharges Bronze staff-review Condition 6. All 39 DQ rules (36 P0, 3 P1) pass against the live Iceberg table; I re-ran them and independently verified the 8/43 verification split, the inverse invariant (max error 1.42e-14 — twelve orders of magnitude inside tolerance), and byte-for-byte spot checks on all 8 BEA-verified states. The architecture is right for the data: Silver is strictly a shaping/provenance layer, the gold consumer (`consumable.regional_price_parities`) is already built and the MCP surface is specified with `verification_status` propagation hard-wired as a gate. The only real architectural risk is non-technical — 43 of 51 rows are primary-agent **estimates**, not BEA-sourced values, and the project depends on every downstream surface (Gold, MCP, frontend) actually reading and surfacing `verification_status`. The data flag is correct; the discipline of honoring it downstream is the bet.

## 1. Zone Boundary Integrity

**Grade: A**

Silver holds cleanly to Silver responsibilities. The transformer in `src/silver/bea_rpp_transformer.py` does exactly what Silver is supposed to do and nothing more:

- **Normalization / shaping:** `geo_fips → state_fips` rename, `geo_name → state_name` passthrough, type canonicalization. ✔
- **Static reference enrichment:** `state_abbr` via a 51-entry FIPS → USPS dict and `census_region` via a 51-entry FIPS → Census region dict, both carried in `src/silver/_us_state_reference.py` with an import-time `_self_check()` that cross-validates key parity against the Bronze ingestor. ✔
- **Pre-computed measure materialization:** `purchasing_power_multiplier = 100.0 / rpp_all_items`. This is a pure function of a single column, not business logic — it is semantically equivalent to storing an inverse index to avoid repeated division in every downstream consumer. Correct placement at Silver. ✔
- **Per-row provenance materialization:** `verification_status` from an 8-entry allow-list. This is provenance shaping, not business classification. ✔

**What Silver explicitly does NOT do (and this is right):** no joins, no concept normalization, no entity resolution, no cross-source work, no salary math (`adjusted_30k/50k/75k/100k` correctly land in Gold, not here), no cost-tier bucketing (correctly in Gold). The spec calls cross-source integration out as "None" by name, and the transformer honors that.

The one line worth watching is the `cost_tier` boundary: the spec does not bucket `rpp_all_items` at Silver, and the Gold spec puts the 5-bucket enum there. This is the right call — the buckets are a presentation artifact for boss-fight difficulty selection, not a structural property of the RPP index, so they belong downstream. If someone in a future refactor tries to push `cost_tier` into Silver "for convenience," that should be rejected.

**Minor note:** the `EXPECTED_ROW_COUNT != len(bronze_rows)` branch in `transform_rows` logs a warning instead of raising. The staff review flagged this as deliberate and I concur — the DQ row-count rule is the correct enforcement point; raising here would mask the real failure against a partial warehouse.

## 2. Grain & Keys

**Grade: A**

- **Grain:** one row per U.S. state or DC (`state_fips`). This is the right grain for a national-baseline cost-of-living reference. The grain is unambiguous, closed-set, and stable across refreshes.
- **Natural key:** `state_fips` — ANSI/FIPS 5-2 code, zero-padded 2-digit string. The `_FIPS_PATTERN = r"^\d{2}$"` validator is correct, and SIL-BEA-039 additionally enforces membership in the canonical 51-member set (closing the chaos probe E6 gap where `state_fips='99'` was silently accepted as a format-valid string). ✔
- **Surrogate key:** `record_id` via `compute_grain_id(row, ['state_fips'], prefix='rpp')`. SHA-256-based, deterministic, and the `test_record_id_depends_only_on_state_fips` test confirms it is a pure function of the grain, not the other columns. ✔
- **Bijections enforced:** `state_fips ↔ state_name` and `state_fips ↔ state_abbr` are both P0 rules. All three identifiers round-trip cleanly through `USPS_TO_FIPS` / `STATE_NAME_TO_FIPS` reverse lookups used by the MCP tool spec. ✔
- **Year dimension:** `data_year` is a single-valued column pinned to 2024 by two P0 rules (SIL-BEA-027 `= 2024`, SIL-BEA-028 `COUNT(DISTINCT data_year) = 1`). The supersession contract is **full-table replacement, not SCD2** — which is the right call for a small annual-refresh reference table. No history, no version dimension, no as-of semantics. When the 2025 BEA release lands, the table atomically replaces and both DQ rules bump in lockstep. The contract's `breaking_changes` block documents this as a minor version bump, not a breaking change.

**FIPS state code handling is correct end-to-end.** The type is `string` (not float, not int) — preserves the leading zero for 1-digit-worth codes like `'06'` California and `'11'` DC. The regex validator + membership rule + bijection checks form a belt-and-suspenders setup that would catch a float-coercion regression (`'06' → '6.0'`) within a single run. I verified this against the live table: `06` stays `06`, `11` stays `11`.

## 3. Integration Risks When This Rolls Into Gold

**Grade: A (architecturally); B (operationally, due to estimate-row provenance)**

This is the section where I initially expected to find trouble. I found almost none, for one simple reason: **RPP is orthogonal to the SOC/CIP join graph**. This is explicitly documented in the Silver spec's "Cross-Source Integration: None" section, and it holds end-to-end.

### Currency / rebasing

- RPP is a **ratio index with national = 100.0** for the 2024 vintage. There is no currency (no USD, no base year conversion). Every downstream salary multiplication is `salary × purchasing_power_multiplier`, which has identity at national average. No rebasing risk.
- The `rpp_all_items` bound is widened at Silver from Bronze's `[80, 130]` to `[70, 130]` (SIL-BEA-017) to give equal headroom around 100. The observed range is `[86.9, 110.7]`, well inside both bounds. No risk of clipping real states.
- `purchasing_power_multiplier ∈ [0.7, 1.3]` (SIL-BEA-020) is the exact inverse of the RPP bound — derived, not independent, and the inverse invariant (SIL-BEA-021) guarantees the two cannot drift apart.

### Join behavior with SOC/CIP data

- **No join exists at the pipeline layer.** The Silver spec says so. The Gold spec `gold-regional-price-parities.md` describes Gold as "pure shaping" — row-for-row promote with 4 derived salary-adjustment columns. There is **no Gold table that joins RPP × career outcomes × institution**.
- I grepped every Gold spec (`gold-career-outcomes-college-scorecard.md`, `gold-futureproof-engine.md`, etc.) for `rpp`, `bea`, `regional_price_parities`, `purchasing_power`. **Zero matches.** The `consumable.program_career_paths` table — the product's core data product — does not carry RPP values. Neither does `consumable.career_outcomes`.
- The join happens **at query time, in the MCP tool layer**, keyed by the student's selected state, not by SOC/CIP. This is the right architecture for a reference table that multiplies every career outcome by a single scalar.
- **Implication:** when the silver→gold cast runs for career_outcomes (or any other non-RPP consumable), `base.bea_rpp` is not a dependency. Silver-to-Gold for RPP is a separate, orthogonal flow. The `consumable.regional_price_parities` table already exists in the catalog (51 rows, 15 columns) — Gold for RPP is effectively done — so the silver→gold transition for RPP itself has no open integration risk.

### Cross-state salary adjustment arithmetic

- `purchasing_power_multiplier` is materialized at Silver, not recomputed downstream. The Gold `adjusted_30k/50k/75k/100k` columns are `N × purchasing_power_multiplier` rounded to 2 decimal places. The MCP `compare_purchasing_power` tool computes `salary × purchasing_power_multiplier` the same way using Python `round()` (banker's rounding, matching DuckDB). This is consistent across Silver → Gold → MCP, which is a real architectural win — there is one canonical multiplier, not three.
- **Residual risk (minor):** if a downstream consumer ever decides to divide by `rpp_all_items / 100` instead of multiplying by `purchasing_power_multiplier`, float rounding at the 5th+ decimal will diverge. Not a correctness bug, but the contract should continue to document `purchasing_power_multiplier` as the single source of truth. The current contract does so by naming it a CDE with the rationale "Every adjusted_30k/50k/75k/100k field in Gold is just N × purchasing_power_multiplier."

### Provenance propagation (the real risk)

- 43 of 51 rows are primary-agent **estimates**. The mitigation — `verification_status` per-row, enforced at DQ — is correct, but **the mitigation only works if every downstream surface reads it**.
- **Gold** (`consumable.regional_price_parities`) does carry `verification_status` as column 13. ✔ Verified in the live table.
- **MCP** (`mcp-bea-rpp.md`) specifies `data_source` (renamed from `verification_status`) in every tool response, and a `verified_only: true` strict mode that returns `null` for estimate rows. ✔ Specified, not yet implemented (MCP spec is READY).
- **Frontend** — not yet verified in code. Silver's staff-review Condition B (echo of Bronze Condition 7) mandates that `@governance-reviewer` enforce `verification_status` propagation at the Gold and MCP pre-review gates; the Silver staff review signs off on the condition being a **governance policy anchor**, not code. The risk here is that if the MCP implementation ships without the `data_source` field (or ships with it but the frontend ignores it), a hackathon demo could quietly show `adjusted_75k = $85,422` for Texas without disclosing that Texas's RPP is an estimate. **This is a material trust risk that lives outside the Silver zone but is inherited from it.**
- **Mitigation already in the DQ suite:** SIL-BEA-023 pins `COUNT(*) WHERE verification_status='bea_official' = 8` as a P0 rule. When the live BEA API refresh lands post-hackathon, this rule flips to `= 51` and the risk evaporates. The contract's `breaking_changes.policy` correctly classifies this as a non-breaking minor version bump.

## 4. Schema Evolution Risk / Contract Readiness

**Grade: A**

### Contract readiness

`governance/data-contracts/silver-base-bea-rpp.yaml` is `status: active`, version `1.0.0`, 51-row guarantee, 11 columns fully documented with real `dq_rules` arrays (verified rule-by-rule), 8 CDEs correctly flagged, 0 PII (public data), and — this is the best part — the `staff_review_conditions` block names Bronze Condition 6 as implemented here AND names Condition 7 as forward-only with the explicit owner `@primary-agent on gold-regional-price-parities and mcp-bea-rpp specs`. Inherited debt is tracked by name, not lost in commit history. This is the cleanest contract in the project.

### Schema evolution vectors

I can think of four realistic evolutions for this table. Each is well-handled or explicitly blocked:

1. **Live BEA API refresh (all 51 rows become `bea_official`).** Handled as a minor version bump: `BEA_VERIFIED_FIPS` expands to 51, SIL-BEA-023 flips from `= 8` to `= 51`, SIL-BEA-024 allow-list expands. **Zero code structure change required.** The contract's `breaking_changes` block documents this explicitly.
2. **New data year (2025).** Handled as a minor version bump with a full-table replacement: SIL-BEA-027 bumps from `= 2024` to `= 2025`, SIL-BEA-028 still holds (single `data_year` at rest). No SCD2, no history, no versioning. Simple.
3. **Additional RPP line codes (goods-only, services-only, rents-only).** Not handled — would require a new column and grain-expansion decision. The current grain is `state_fips`; adding line-code variants would either move to `[state_fips, line_code]` (grain change → major version) or wide-pivot into sibling columns (`rpp_goods`, `rpp_services` → minor version). The contract does not pre-decide this, which is correct for a feature that is not yet required.
4. **Metro-area RPPs.** Explicitly out of scope and architecturally separate (different grain, different source, different refresh cadence). The frontend product only needs state-level RPP. Do not expand this table; build a sibling.

### Contract posture

`partial_verification` quality tier is the right label and is pre-disclosed at every surface: contract header, column rationales, CDE tagging, and the `verification_status` column itself. The honesty on this is the reason I am not deducting for the 43 estimated rows — the contract does not claim more than it can deliver, and the DQ rule pins the current state exactly.

**What I did NOT find and would have penalized for:**

- No silent coercion of `estimate` rows into `bea_official`.
- No optimistic freshness SLA (the 400-day guardrail inherited from Bronze is realistic for an annual publication).
- No overclaim in the `uniqueness_guarantee` block (state_fips, record_id, state_abbr, state_name are all real bijections, verified).
- No "draft" contract flipped to "active" without staff sign-off — the sign-off was formal (2026-04-10).

## 5. Secondary Observations

### What's genuinely good

- The `_us_state_reference.py` import-time `_self_check()` is the right pattern for structural reference data. It cross-validates against `BeaRppIngestor.VALID_STATE_FIPS` at import — any Bronze-Silver drift fails at module load, not silently at row-level. Any future renaming sweep will fail-loud.
- The chaos harness (28 probes, 5 cycles) found 2 gaps (SIL-BEA-018 cross-zone SQL form + SIL-BEA-039 non-canonical FIPS membership) and both were actually fixed, not papered over. The chaos workflow is doing real work here.
- The 8 byte-for-byte spot-check rules (SIL-BEA-031..038) each assert `state_abbr`, `census_region`, `purchasing_power_multiplier` (±0.001) AND `verification_status` in a single row filter. If any single cell in the 8-state reference drifts, the exact rule that catches it will name it.
- The DQ suite correctly carves out SIL-BEA-018 from shadow-mode (cross-zone join against `bronze.bea_rpp`) via `evaluation_mode: production_only` + `chaos_exclude: true`. The audit flagged HIGH-1 that these fields are decorative — true — but the hard-coded `SHADOW_EXCLUDED_RULE_IDS` set in the chaos runner is the effective enforcement. Deferred as a brightsmith framework ticket, correctly.

### What I'd do differently if starting over (minor)

- **Externalize the FIPS-to-USPS and FIPS-to-Census-region dictionaries as a committed NIST/Census CSV under `governance/reference-data/` with SHA-256-anchored loading.** The in-code dict is fine for 51 entries, but a CSV anchor would let a regulator / auditor see the exact bytes that back these mappings without reading Python. MEDIUM-2 from the adversarial audit flagged this; I concur and would prioritize it if this pipeline were heading toward a regulated consumer. Not blocking for a hackathon.
- **Contract-level per-row provenance API.** Right now `verification_status` is column-level and each downstream zone re-derives it (`data_source` in MCP). A framework-level `per_row_provenance_column: verification_status` contract field exists (see line 42 of the contract) but no framework code reads it. Parallel to HIGH-1 — the metadata is honest but decorative. A future brightsmith version should read this field natively.

### Test quality

101 tests / 0.63s. The staff review correctly pointed out that the real correctness-anchoring count is closer to ~30 (8 spot checks + 8 verification parametrizations + error-path coverage + integration round-trip), with the rest being moderately tautological dict-shape tests. That does not make the 70 or so remaining tests worthless — they do catch some hallucination classes — but the "101 tests" framing overstates signal. Not a blocker; an honesty item for future test counts in this project.

## 6. Top Risks

1. **MCP layer never ships the `data_source` field (or the frontend ignores it).** Impact: the product presents estimate-based salary adjustments with the same confidence as BEA-official values, quietly eroding trust. Mitigation: Condition B of the Silver staff review mandates `@governance-reviewer` enforcement at the MCP pre-review gate; this review now formally echoes that requirement. If the MCP spec reaches staff sign-off without verifying `data_source` in every tool response, this review recommends automatic CHANGES REQUESTED back to the MCP spec.
2. **The 43 estimated RPP values are never refreshed before production.** Impact: 84% of states surface `adjusted_*` values derived from primary-agent guesses. This is not a silver-zone problem; it's a data provenance problem inherited from Bronze. Mitigation: the contract pre-discloses `partial_verification` at every layer and SIL-BEA-023 flips atomically when the live BEA API refresh lands. Ship discipline, not a blocker.
3. **A future refactor pushes `cost_tier` or salary-adjustment math into Silver.** Impact: Silver stops being a pure shaping layer; Gold loses its reason to exist for this table. Mitigation: the spec and this review both name the zone boundary explicitly. Any PR that moves cost-tier bucketing or `adjusted_30k/50k/75k/100k` into `base.bea_rpp` should be blocked at CODE-REVIEW.

## 7. Verdict for Silver → Gold Transition

**APPROVED.**

All five dimensions (zone boundary, grain/keys, integration risk, schema evolution, contract readiness) check out. The Silver → Gold transition for BEA RPP specifically has **no open integration risk** because the Gold consumer (`consumable.regional_price_parities`) already exists in the catalog, is a pure row-for-row promote with 4 derived columns, and does not participate in the SOC/CIP join graph. The main project-wide silver→gold cast (for `career_outcomes`, `program_career_paths`, etc.) does not depend on this table at all, so this review does not gate the other silver→gold transitions either.

Both staff-review conditions remain active and are echoed here:

- **Condition A (HIGH-1 deferral):** Brightsmith framework ticket for `dq_runner` + chaos harness to natively honor `evaluation_mode: production_only` and `chaos_exclude: true`. Framework-level, out of project scope. **Tracked, non-blocking.**
- **Condition B (Bronze Condition 7 enforcement):** `@governance-reviewer` must verify at the MCP pre-review gate that every tool response includes a `data_source` field derived from `verification_status`, with a strict-mode `verified_only: true` option that returns structured null for estimate rows. **Tracked, non-blocking at the Silver gate; mandatory at the MCP gate.**

No CHANGES REQUESTED. Cleared for the project-wide silver→gold transition. `@insight-manager` may proceed.

---

## User-Deferred Decisions

None. No interactive questions were raised at this transition; the architecture choices (pure shaping at Silver, salary-math materialization at Silver, cost-tier bucketing at Gold, no cross-source join) are all spec-correct and evidence-backed.

---

*— End of Review —*
