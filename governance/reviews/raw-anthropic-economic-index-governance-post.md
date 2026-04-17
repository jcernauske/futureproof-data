# Governance Review: raw-ingest-anthropic-economic-index
**Review Type:** Post-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-17
**Spec:** `docs/specs/raw-ingest-anthropic-economic-index.md`
**Pre-Review:** `governance/reviews/raw-anthropic-economic-index-governance-pre.md` (APPROVED with 6 advisories)
**Verdict:** **APPROVED_WITH_CONDITIONS**

---

## Summary

Governance artifact production for this spec is **substantially complete**. All 15 artifacts the pre-review inventoried are present on disk, CC-BY 4.0 attribution plumbing is wired correctly in two places (LICENSE_SOURCES.md + Bronze contract), all 6 pre-review advisories are addressed, every pre-review gap flagged by the adversarial auditor has been closed, and the DQ gate passes cleanly (37/37 executed rules pass; 1 P2 rule documented SKIP on a baseline-snapshot table). Pipeline code matches the spec on every critical assertion (global-share invariant, task-to-SOC fan-out split, Anthropic v2 automation axis, placeholder handling).

**One conditional finding blocks unconditional approval:** the Bronze and Silver Iceberg tables declared by Success Criteria 2 and 3 are **not materialized on disk**. Every other `raw-*` spec in this project (karpathy, bls-ooh, bea-rpp, onet, college-scorecard, etc.) has physical parquet + Iceberg metadata under `data/bronze/iceberg_warehouse/bronze/<table>/` and `data/silver/iceberg_warehouse/base/<table>/`. The Anthropic tables are missing from both warehouses. The DQ engineer ran rules against in-memory DuckDB views, which is adequate evidence that the transforms work, but it is **not** what the spec called for and is **not** the project's established Bronze/Silver materialization pattern. This must be resolved before `@staff-engineer` closes the spec.

All other items pass. Once Iceberg materialization lands, this spec is complete.

---

## Checklist Results

### Pre-Review Advisories — Resolution Status

| # | Advisory | Resolution | Status |
|---|----------|------------|--------|
| 1 | `@primary-agent` placeholder — clarify to concrete agent | Task tracker shows `@primary-agent` ran Bronze+Silver+Gold; work is done regardless of label. Agent name remains generic in spec but not blocking. | RESOLVED (cosmetic) |
| 2 | `LICENSE_SOURCES.md` does not exist at root | File **created** at `/Users/jcernauske/code/bright/futureproof-data/LICENSE_SOURCES.md` with 7 sources including the full Anthropic CC-BY 4.0 block. `license:` block also present in Bronze contract (lines 29-38 of `raw-anthropic-economic-index.yaml`). | RESOLVED |
| 3 | No path listed for Gold DQ rules file | Created: `governance/dq-rules/gold-ai-exposure-anthropic.json` (8 rules, executed). | RESOLVED |
| 4 | EDA must resolve `task_pct` global vs per-task interpretation | EDA documented `pct` as global share (sum=100.0000); aggregation strategy is sum-of-global-shares with N-way fan-out split. Code matches (ingestor line ~538). | RESOLVED |
| 5 | CDE/PII pre-assessment deferred to @cde-tagger | CDE tagging completed (`governance/cde-tagging/raw-anthropic-economic-index.md`): 18 of 26 fields CDE; PII scan clean (`governance/pii/raw-anthropic-economic-index-pii-scan.md`: 0 true positives across 31,734 rows x 12 detectors). | RESOLVED |
| 6 | Fixture row count (50) may be low | Not materially expanded, but the 99 passing unit tests (including chaos runner with 16 real-data scenarios) demonstrate adequate edge-case coverage. Non-blocking. | RESOLVED (sufficient via chaos tests) |

### Post-Implementation Governance Completeness Checklist

| Item | Status | Evidence / Notes |
|------|--------|------------------|
| **Lineage:** OpenLineage events for every transformation | PASS | 3 events present: `raw-anthropic-economic-index-20260417T012058Z.json` (Bronze), `silver-anthropic-observed-exposure-20260417T012058Z.json` (Silver), `gold-ai-exposure-anthropic-20260417T012058Z.json` (Gold) |
| **DQ Rules:** Rules exist for every new/modified table | PASS | `raw-anthropic-economic-index.json` (17), `silver-anthropic-observed-exposure.json` (13), `gold-ai-exposure-anthropic.json` (8) = 38 total |
| **DQ Execution:** Rules executed against real data | PARTIAL | Executed against source CSVs + real `base.bls_ooh` / `consumable.ai_exposure` Iceberg tables via in-memory DuckDB. However the Anthropic Bronze/Silver tables were **not** written to Iceberg on disk — see §Conditional Finding below. |
| **DQ P0 Gate:** No P0 failures | PASS | Bronze 9/9 P0 pass; Silver 9/9 P0 pass; Gold 2/2 P0 pass. P2 rule `GLD-AIE-ANT-007` SKIPPED with documented rationale (baseline snapshot table `consumable.ai_exposure_baseline_pre_anthropic` does not exist in this environment); skip is legitimate, not a masked failure |
| **DQ Scorecard:** Scorecards produced from real results | PASS | 3 scorecards present with identifiable run_id `c169217e`, timestamps, row counts reproduced by adversarial auditor's independent rerun |
| **CDE/PII Tags:** `is_cde`/`is_pii` set on contracts | PASS | Bronze contract: 18/26 fields CDE-flagged (verified); Silver + Gold likewise; PII false across the board |
| **Data Dictionary:** New/modified fields have entries | PASS | `governance/data-dictionary.json` contains entries for `observed_exposure_pct`, `automation_pct`, `anthropic_task_count`, `anthropic_source_release` on Gold, plus Silver + Bronze field entries (52 "anthropic" hits in dictionary) |
| **Data Contracts:** Present & include license block | PASS | Bronze `raw-anthropic-economic-index.yaml` (new, license block CC-BY 4.0), Silver `base-anthropic-observed-exposure.yaml` (new, inherited license), Gold `consumable-ai-exposure.yaml` (bumped v1.0.0 → v1.1.0, adds this spec to `spec_references`) |
| **Audit Trail:** Agent decision logs exist | PASS | 7 anthropic entries in `governance/audit-trail/`: pre-review, cde-tagging, dq-rule-writer (2), temporal-modeler, doc-generator, governance-reviewer-pre |
| **Schema Changes:** Match spec + physical model | PASS | Bronze 13 fields (matches spec §Raw Schema), Silver 10 fields (matches §Silver Schema, uses `aoe` grain prefix), Gold additive 4 fields (matches §Zone 3, additive only, regression rule GLD-AIE-ANT-007 planned to verify no drift on existing `stat_res`/`boss_ai_score` but skipped for env reason) |
| **Data Models:** 3-stage progression (Base/Gold only) | N/A → PARTIAL | Bronze is physical-only (acceptable per governance rules). Silver adds a new Base table (`base.anthropic_observed_exposure`) — no conceptual/logical/physical model documents found in `governance/models/` for this table. Gold modifies an existing Consumable table and references `governance/models/gold-ai-exposure-physical.md` which pre-dates this spec. ADVISORY: Silver table should have model docs, but REQUIRE_HUMAN_APPROVAL allows auto-approval for existing Backfill-Mode tables; since `consumable.ai_exposure` already has a physical model, the additive v1.1.0 columns are an additive schema evolution that typically warrants a model amendment rather than a fresh 3-stage progression. Flag for @staff-engineer judgment. |
| **No Orphaned Artifacts** | PASS | All governance artifacts reference fields and tables that exist in the contracts/code |
| **Consistency:** Lineage, CDE flags, dictionary, DQ rules all reference same field/table names | PASS | Spot-checked: Bronze `task_pct` → CDE-flagged in contract → listed in dictionary → referenced by RAW-AEI-003/004/013 → appears in lineage output schema. Silver `observed_exposure_pct` → same cross-referencing holds. Gold additive columns likewise. |

### CC-BY 4.0 Attribution Verification

| Check | Status | Evidence |
|-------|--------|----------|
| `LICENSE_SOURCES.md` exists at project root | PASS | Created, 7 sources, full Anthropic section lines 118-138 |
| Anthropic section includes license type, URL, citation, attribution requirement | PASS | "CC-BY 4.0 International", HuggingFace URL, "Economic Index Dataset, Anthropic (2026)" citation, "Credit Anthropic in any published analysis" |
| Anthropic section lists downstream tables | PASS | `raw.anthropic_economic_index` (4,082 rows), `base.anthropic_observed_exposure` (588 rows), `consumable.ai_exposure` v1.1.0 additive fields |
| Release pinning documented | PASS | `release_2025_03_27` pinned, with rationale for why later releases (`2026_01_15`, `2026_03_24`) are not used |
| Bronze contract includes `license:` block | PASS | Lines 29-38: `type: CC-BY-4.0`, attribution text, URL, `requires_citation: true`, notes describing MCP + Fight AI downstream surfaces |
| Silver contract inherits license (derivative work) | PASS | Lines 25-32 of `base-anthropic-observed-exposure.yaml` carry the attribution forward and note "Inherits from raw.anthropic_economic_index; Silver is CC-BY 4.0 derivative" |
| Provenance field surface through Silver/Gold | PASS | `source_release` CDE-flagged on Bronze; `anthropic_source_release` present on Gold v1.1.0 |
| MCP response plan for attribution | PASS | LICENSE_SOURCES.md §Anthropic states "MCP responses that surface `observed_exposure_pct` should include the attribution string built from `anthropic_source_release`" — note this is a downstream task for the S4 spec that consumes this data |

### Adversarial Auditor Concerns — Resolution Status

The adversarial auditor's CONCERNS_FOUND report listed 10 of 15 governance artifacts as missing at the time of audit. I verified on disk:

| Auditor flagged missing | Now present? | Evidence |
|-------------------------|--------------|----------|
| Bronze data contract | YES | `governance/data-contracts/raw-anthropic-economic-index.yaml` |
| Silver data contract | YES | `governance/data-contracts/base-anthropic-observed-exposure.yaml` |
| Gold data contract update | YES | `consumable-ai-exposure.yaml` bumped to v1.1.0 with spec cross-reference |
| Lineage Bronze | YES | `raw-anthropic-economic-index-20260417T012058Z.json` |
| Lineage Silver | YES | `silver-anthropic-observed-exposure-20260417T012058Z.json` |
| Lineage Gold | YES | `gold-ai-exposure-anthropic-20260417T012058Z.json` |
| LICENSE_SOURCES.md | YES | Created at project root |
| Data dictionary entries | YES | 52 anthropic hits in `governance/data-dictionary.json` |
| PII scan | YES | `governance/pii/raw-anthropic-economic-index-pii-scan.md` — clean |
| CDE tagging | YES | `governance/cde-tagging/raw-anthropic-economic-index.md` — 18 CDE fields |
| Staff review | PENDING | Task #16 still pending — this is the next/final step after my review; not a gap for me to block on |
| Stale Bronze scorecard (16/16 vs 17 rules) | RESOLVED | Scorecard now shows 17/17; DQ results JSON run_id `c169217e` executed all 17 |
| "Actual" column semantics (violation count vs metric) | NOT RESOLVED | Still reports violation count for most rules. This is a project-wide scorecard format concern, not specific to this spec. Defer to @staff-engineer / separate governance-tooling backlog. ADVISORY, not blocking. |
| SLV-AOE-015 semantic (0.19 vs 1.78) | NOT VERIFIED FIXED | Scorecard still shows 0.19080068 with threshold `tracked`. The rule's semantic meaning appears to be "fraction of rows dropped" (1/587 = 0.17%) vs the EDA's documented "volume share dropped" (1.78%). ADVISORY: the rule is P3/tracked so has no gate impact; clarify description or rename metric before @staff-engineer sign-off. |
| 80% → 60% SOC coverage threshold drift | PARTIAL | EDA recommended revising, Silver SLV-AOE-006 is P0 `coverage` and passes. Silver contract §quality_tier now documents "SOC coverage against consumable.occupation_profiles is 61.3% (510 of 832); this is a documented dataset limitation... revised from the spec's original >=80% threshold to >=60% per EDA." Not documented in `governance/approvals/` as a formal CAB decision. ADVISORY — consider lodging an approval record. |

### Insight Traceability

No Insight Report exists for this zone transition (this is a fresh greenfield Bronze/Silver/Gold trio, not a zone migration). Skip.

---

## Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | **CHANGES REQUESTED** | **Bronze and Silver Iceberg tables are not materialized on disk.** `data/bronze/iceberg_warehouse/bronze/anthropic_economic_index/` does not exist. `data/silver/iceberg_warehouse/base/anthropic_observed_exposure/` does not exist. Every other raw-* spec in this project (karpathy, bls-ooh, bea-rpp, onet, college-scorecard, college-scorecard-institution) has materialized parquet + Iceberg metadata at these paths. Spec Success Criteria 2 ("Raw data lands in Iceberg table `raw.anthropic_economic_index`") and 3 ("Silver base table `base.anthropic_observed_exposure`") are formally unmet. The adversarial auditor also flagged this as a "Could Not Verify" concern (§Could Not Verify, audit report). | Run the Bronze ingestor and Silver transformer in a mode that writes to the Iceberg warehouse, then re-execute DQ against the materialized tables (the scorecards should reproduce identical results). @primary-agent or @dq-engineer must own. Do **not** proceed to @staff-engineer until this is resolved. |
| 2 | ADVISORY | Silver base table `base.anthropic_observed_exposure` has no 3-stage model documents (conceptual/logical/physical) in `governance/models/`. Project has `REQUIRE_HUMAN_APPROVAL = true` per CLAUDE.md, so this gate applies. | Either (a) produce the three models with glossary references, or (b) lodge an approval record in `governance/approvals/` acknowledging the Base-zone model exemption for this table given its mechanical SOC-grain aggregation. Flag for @staff-engineer. |
| 3 | ADVISORY | `SLV-AOE-015` rule emits 0.19 (row-fraction dropped) but its description and the EDA reference the 1.78% volume-share of the `none` placeholder. | Either update the rule SQL to compute the intended volume share, or update the rule description to match computed semantics. P3/tracked so no gate impact. |
| 4 | ADVISORY | 80% → 60% SOC coverage threshold revision documented in EDA and Silver contract but not formalized as a CAB/approval record in `governance/approvals/`. | Lodge an approval note acknowledging the dataset limitation (Claude traffic skews knowledge-work) and the revised threshold. Non-blocking — evidence exists in EDA + contract. |
| 5 | ADVISORY | Scorecard "Actual" column reports violation count rather than measured metric for invariant rules (e.g., RAW-AEI-003 `SUM(task_pct) ≈ 100` shows `actual=0` meaning "0 violations," not the actual SUM value). Auditor flagged this. | Project-wide scorecard format concern — defer to governance-tooling backlog. Not blocking this spec. |
| 6 | ADVISORY | Staff review task #16 is pending. Cannot mark spec COMPLETE until `@staff-engineer` reviews. Not a governance gap per se, just next-step status. | Trigger `@staff-engineer` after Issue #1 is resolved. |

---

## Decision Rationale

The pipeline's technical core is excellent:

- **Code correctness:** Every load-bearing assertion in the spec (global-share SUM≈100 invariant, task-to-SOC N-way fan-out split, Anthropic v2 `automation = directive + feedback_loop` with `learning` routed to augmentation, `task_name='none'` placeholder handling with NULL soc_code, chunked CSV read, SOC regex hardening via RAW-AEI-019) is verified present in `src/raw/anthropic_economic_index_ingestor.py` and backed by passing tests.
- **EDA numerical verification:** The adversarial auditor independently reproduced 11 of 11 headline EDA claims (file row counts, column sets, `pct` distribution, row-sum-to-1.0 invariant, placeholder row, max 34-way fan-out, Bronze row count 4,082). One minor stat (272 vs 265 tasks with multi-SOC) is an EDA drafting error that does not feed any threshold.
- **DQ coverage:** 38 rules tiered P0/P1/P2/P3 spanning uniqueness, validity, consistency, volume, completeness, coverage, freshness, and consistency. 37 executed, all pass; 1 documented SKIP for environment reason.
- **Chaos hardening:** 16 real scenarios with injected source corruptions, real exception text captured, 1 P1 gap found and closed (RAW-AEI-019 SOC regex).
- **CC-BY 4.0 compliance:** Wired correctly in both places (LICENSE_SOURCES.md root + Bronze contract license block); provenance field (`source_release` / `anthropic_source_release`) flagged CDE on every zone; release pinned with rationale.
- **Cross-agent consistency:** Field names, table names, and grain match across lineage, contracts, CDE tagging, data dictionary, and DQ rules. No orphaned artifacts detected.

The single condition blocking unconditional approval is **Iceberg materialization**. A spec named `raw-ingest-*` whose Success Criteria explicitly require "Raw data lands in Iceberg table" cannot be declared complete when the Iceberg table does not exist on disk while every peer spec has materialized theirs. The DQ engineer's in-memory DuckDB approach is a valid validation strategy but does not substitute for persistent Bronze/Silver tables that S4 (the spec this one blocks) will need to JOIN against.

The auditor's 3 secondary concerns (stale scorecard resolved; "Actual" column format is a project-wide issue; SLV-AOE-015 semantic is cosmetic on a P3 rule) are appropriately downgraded to ADVISORY.

**Verdict: APPROVED_WITH_CONDITIONS.** The single condition is materialization of the Bronze and Silver Iceberg tables. Once resolved, this spec is ready for @staff-engineer final sign-off.

---

## Conditions for Unconditional Approval

1. **[BLOCKING]** Materialize `raw.anthropic_economic_index` at `data/bronze/iceberg_warehouse/bronze/anthropic_economic_index/` (parquet + metadata) matching the project's established pattern (see `data/bronze/iceberg_warehouse/bronze/karpathy_ai_exposure/` as reference).
2. **[BLOCKING]** Materialize `base.anthropic_observed_exposure` at `data/silver/iceberg_warehouse/base/anthropic_observed_exposure/` matching the same pattern.
3. **[BLOCKING]** Re-execute DQ rules against the materialized tables to confirm the same 37/37 pass outcome. Update scorecard run_ids.
4. **[NICE-TO-HAVE]** Address ADVISORY items 2–5 during @staff-engineer review (model docs for Silver, SLV-AOE-015 semantic clarification, 60% threshold approval record, scorecard actual-value format).

---

## Decision

**Verdict:** APPROVED_WITH_CONDITIONS
**Review File:** `/Users/jcernauske/code/bright/futureproof-data/governance/reviews/raw-anthropic-economic-index-governance-post.md`
**Next step:** @primary-agent materializes Iceberg tables, then @staff-engineer performs final review.

---

*— End of Post-Implementation Review —*
