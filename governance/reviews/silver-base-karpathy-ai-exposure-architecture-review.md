# Principal Data Architect Review — silver-base-karpathy-ai-exposure

**Date:** 2026-04-16
**Reviewer:** @principal-data-architect
**Scope:** Silver → Gold transition review (retroactive)
**Domain:** FutureProof — AI exposure scoring, SOC-keyed
**Spec:** `docs/specs/raw-ingest-karpathy-ai-exposure.md` (single spec governs Bronze + Silver + Gold + MCP + backfill)

---

## Executive Summary

This is the cleanest silver transformer in the FutureProof pipeline. It takes a small, well-behaved source (342 rows of LLM-generated AI-exposure scores), normalizes SOC codes, expands 5-digit broad codes against BLS OOH, and produces 419 rows (389 joinable, 30 unresolved) with a 23/23 DQ rule pass rate on real data. The zone boundary is respected — no scoring math leaks into silver. The two real risks are **non-architectural**: (a) silver only covers 389 of 832 BLS SOCs and 372 of 798 O*NET SOCs, so `stat_res` will be null for more than half of all occupations downstream, and (b) the silver table is already materialized while a consumable.ai_exposure with 389 rows exists in gold, meaning the silver→gold transition has de-facto already happened. This review therefore documents, not gates.

**Verdict: APPROVED.**

---

## 1. Zone Boundary Integrity

**Grade: A.**

The silver transformer (`src/silver/karpathy_ai_exposure_transformer.py`) is a strict normalization layer. It performs exactly the five transformations the spec promises:

1. SOC whitespace-strip + format validation (XX-XXXX)
2. Null-SOC resolution via title matching against `base.bls_ooh`
3. Broad-code expansion (XX-XXX0 → set of detailed XX-XXXX codes)
4. Post-expansion dedup by highest `num_jobs_2024`
5. `bls_match` flag + `soc_resolved_method` classification

No business logic leaks in. The two downstream derivations — `stat_res = MIN(11 - exposure_score, 10)` and `boss_ai_score = MAX(exposure_score, 1)` — live correctly in the gold transformer. `exposure_score` and `rationale` are carried verbatim from bronze, and DQ rule SLV-KAI-003 enforces the range invariant as a data-mutation tripwire.

Minor structural note: the dedup logic uses a private `_num_jobs_2024` temp field on the silver dict that is stripped before `compute_grain_id` is called. That's a legitimate pattern but worth flagging — any future maintainer adding a new field to `GRAIN_FIELDS` must remember that `_num_jobs_2024` is ordering state, not grain state. The code is correct today. It's one comment away from being bulletproof.

---

## 2. Grain & Keys

**Grade: A-.**

- **Declared grain:** one row per `soc_code` where non-null.
- **Verified on real data:** 395 distinct non-null SOC codes across 395 non-null rows → **zero duplicates** (SLV-KAI-001 PASS, live query confirms).
- **Null-SOC rows (24):** deliberately preserved with `record_id` keyed on `slug` to guarantee PK uniqueness (SLV-KAI-008 + SLV-KAI-020 PASS).
- **Hybrid PK strategy is appropriate:** null-SOC rows cannot join to BLS/O*NET/CIP-SOC and are excluded from gold via `bls_match = true` filter. Keeping them for provenance is the right call.

**SOC-axis alignment with other silver tables:**

| Silver table | Distinct SOCs | Overlap with Karpathy (matched) |
|---|---|---|
| `base.bls_ooh` | 832 | 389 (100% of Karpathy-matched) |
| `base.onet_occupations` (via `bls_soc_code`) | 798 | 372 of 389 |
| `base.karpathy_ai_exposure` (matched) | 389 | — |

Karpathy is a **subset** of the BLS OOH universe and mostly a subset of the O*NET universe, which is exactly the topology the gold join expects (LEFT JOIN ai_exposure onto `program_career_paths`). The 17 Karpathy SOCs that exist in BLS but not O*NET are all higher-level aggregation codes (`13-2020`, `17-3019`, `21-1018`, etc.) — that is not a silver defect, it is an O*NET detail-code gap that the silver layer cannot fix.

**Minor concern (not blocking):** the O*NET silver table exposes its SOC via `bls_soc_code`, not `soc_code`. Every other silver SOC-bearing table uses `soc_code`. This is a silver-zone inconsistency introduced by `silver-base-onet`, not by this spec, but gold transformers joining across silver tables must be aware of it. Call it out in gold specs.

---

## 3. Integration Risks for Gold

**Grade: B+.** (Architecturally fine; coverage-limited by source.)

### 3.1 The 389-of-832 (and 372-of-798) coverage gap is the headline risk

The BLS OOH corpus has 832 occupations; Karpathy scored 342 and silver expansion produced 389 joinable SOC rows. That means:

- **443 BLS SOCs** will never have `stat_res` or `boss_ai_score`
- **426 O*NET SOCs** will never have `stat_res` or `boss_ai_score`
- Every `program_career_paths` row whose SOC is outside Karpathy's 389 will carry a null RES stat and null Fight AI boss

This is **a source-data property, not a silver defect.** The silver layer handles it honestly (`bls_match` flag, `soc_resolved_method` classification) and gold will correctly LEFT JOIN with null fill. The frontend implication — that pentagon rendering and gauntlet run must gracefully degrade when RES/Fight AI are null — is an application-layer concern documented in the spec's §4 backfill section. Verified in live data: `consumable.ai_exposure` has exactly 389 rows, matching silver's `bls_match = true` row count (no rows leaked, none lost).

**What gold must do to not make this worse:**

1. `consumable.program_career_paths` backfill MUST keep existing stats intact for SOCs not in Karpathy's 389. The LEFT JOIN pattern in the spec's §4 is correct.
2. `stats_available_count` and `bosses_available_count` MUST be recomputed per-row, not globally. The spec mentions this; gold implementation needs to honor it.
3. The frontend's `LoadingScreen` / pentagon components should already render 4/5 stats for uncovered SOCs (existing placeholder path).

### 3.2 Unresolved-row exclusion is appropriate

The 30 `unresolved` rows (24 null SOC + 6 unmatched-broad) correctly drop out at gold via the `bls_match = true` filter. Spot-checking the unresolved list reveals genuine gaps (e.g., "Military careers" has no single SOC; "Announcers" maps to a Karpathy-level title that BLS splits into `27-3011` + `27-3012`). A future improvement would be to build a tiny manual override file for ~5-10 of these (Financial analysts → `13-2051`, Top executives → `11-1011`, Physicians and surgeons → `29-1229`), but that is a **Silver v1.1 improvement**, not a gold blocker.

### 3.3 The `stat_res` floor (exposure 0 → 10) is mathematically correct but source data never produces it

Real silver data has exposure scores distributed 1–10, with zero rows at exposure 0. The `MIN(11 - exposure_score, 10)` clamp in gold is defensive and correct, but the code path that maps 0 → 10 is untested-in-production. Not a blocker — the rubric permits 0 and the formula is right — but worth a unit test in the gold transformer.

### 3.4 Cross-table consistency at gold

Gold's DQ rule "every soc_code in ai_exposure must exist in consumable.occupation_profiles" is the right referential-integrity gate. This review trusts it is wired (the gold spec asserts it); principal architect recommends the gold review at the NEXT transition verifies the rule is actually executing, not just declared.

---

## 4. Schema Evolution Risk / Contract Readiness

**Grade: A-.**

### Contract status

- `governance/data-contracts/silver-base-karpathy-ai-exposure.yaml` is present and well-formed.
- Status is `draft` in the YAML header and `DRAFT` in the comments — this should be bumped to `ACTIVE` before any gold consumer is promoted, but it is not a correctness issue.
- `record_count: 419` matches live data (exact).
- `quality.volume.row_count_range: [380, 460]` — actual row count 419 is comfortably inside.
- `quality.volume.bls_match_true_pct_min: 90.0` — actual is 389/419 = 92.8%, passing with 2.8pp of headroom. Tight but OK.
- Semantic versioning + 30-day deprecation policy is declared. Good.

### Evolution risk

The biggest schema-evolution concern is **the Karpathy source is a single 2-hour vibe-coded LLM run**. If Karpathy updates `scores.json` with re-scored data or a different occupation set, the silver output count, method distribution, and `bls_match` rate will all shift. The contract's event-driven freshness SLA handles this correctly — but the spec's "Post-Hackathon Re-Scoring with Gemma" plan implicitly promises source-swap without schema change. That is only true as long as the Gemma re-score outputs the same six fields (slug, title, category, SOC, 0-10 score, rationale). Make that an explicit contract clause before post-hackathon re-scoring.

### CDE tagging is thorough

6 fields tagged as CDE with written rationale (`record_id`, `soc_code`, `exposure_score`, `rationale`, `bls_match`, `soc_resolved_method`). That is proportionate — not over-tagged, not under-tagged. `category` and `slug` correctly not CDE.

### DQ coverage is excellent

23 rules, 100% pass on live data, well-distributed across dimensions (7 completeness, 5 validity, 3 consistency, 3 uniqueness, 2 referential integrity, 1 volume, 1 consistency-cross-zone). The anti-theater test is whether rules catch real problems — SLV-KAI-022 (referential: bls_match=true must actually exist in BLS) and SLV-KAI-023 (broad_expansion rows must be bls_match=true) are load-bearing safety checks that a lazy DQ author would have skipped. Those are real.

---

## 5. What I Would Improve (Non-Blocking)

1. **Manual SOC override file.** Add `data/reference/karpathy_soc_overrides.yaml` for the 5-10 unresolved rows with obvious SOC mappings (Financial analysts, Top executives, Physicians and surgeons, Kindergarten teachers, etc.). This would lift silver-matched coverage from 389 to ~395-400 joinable SOCs and recover a handful of important career paths.
2. **Document the O*NET SOC column-name inconsistency.** `base.onet_occupations.bls_soc_code` vs `base.karpathy_ai_exposure.soc_code` vs `base.bls_ooh.soc_code`. Either rename at silver v2 or document it in a cross-silver integration note.
3. **Bump contract status from `draft` to `ACTIVE`.** Procedural, 1-line fix.
4. **Add a gold DQ rule:** "count(program_career_paths where stat_res IS NULL) / count(*) ≤ 0.55" — sets an explicit, tracked ceiling on how much of the user-facing product lacks RES stat. Today that fraction is effectively ~53% (443/832 BLS SOCs without Karpathy). This turns a known limitation into a monitored SLA.

---

## 6. Top Risks

1. **Coverage gap (Source-data risk, MEDIUM).** 443 BLS SOCs and 426 O*NET SOCs have no RES stat. Mitigation: LEFT JOIN with null fill, frontend degrades 5-stat pentagon to 4-stat; principal recommends adding a tracked DQ rule on null-stat fraction.
2. **Silver → Gold already materialized (Process risk, LOW).** `consumable.ai_exposure` has 389 rows and aligns with silver `bls_match = true` row count, i.e., the gold promote already ran. This review is retroactive and documents rather than gates, but every future zone transition should block the promote until the review is written first.
3. **Karpathy methodology limitations carry through (Domain risk, LOW, documented).** Scores are LLM estimates with self-referential bias. Bronze/silver/gold all preserve the `rationale` field and BT-080/BT-081 glossary terms explicitly flag "not an empirical measurement." This is governance done right — the limitation is surfaced to consumers, not hidden.

---

## 7. What I Would Cut

Nothing. This spec is already the right size. 342 source rows, 419 silver rows, 389 gold rows, 23 DQ rules, 6 CDE fields. If anything, it is a model for how right-sized a single-source silver layer should look.

---

## 8. What Is Missing for Production

- ACTIVE contract status (cosmetic).
- Manual SOC override file for ~5-10 recoverable unresolved rows.
- Documented cross-silver SOC column-name normalization decision.

None are silver → gold blockers.

---

## 9. Verdict

### Silver → Gold Transition: **APPROVED**

Grade summary:
- Zone boundary integrity: **A**
- Grain & keys: **A-**
- Integration risk for gold: **B+** (coverage-limited by source, not by silver)
- Schema evolution / contract: **A-**
- Overall silver layer: **A-**

The silver layer is well-engineered, contract-complete, DQ-verified on real data, and correctly scoped. The 389-row coverage ceiling is a property of the Karpathy source, not a defect of this implementation. Gold work may proceed.

### User-Deferred Decisions

None at this transition — review is retroactive and the gold table (`consumable.ai_exposure`, 389 rows) has already been produced per-spec. Future work: if post-hackathon Gemma re-scoring is pursued, a fresh silver → gold architecture review is required at that time, not a minor-version bump.
