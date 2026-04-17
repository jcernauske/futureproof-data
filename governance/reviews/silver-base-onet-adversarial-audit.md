# Adversarial Audit: silver-base-onet

**Spec:** silver-base-onet
**Zone:** Silver (Base)
**Auditor:** @adversarial-auditor
**Date performed (retroactive):** 2026-04-16
**Original pipeline-state claim:** adversarial-auditor completed 2026-04-09 (output file never written — this document is the retroactive reconstruction)
**Tables audited:** `base.onet_occupations`, `base.onet_activity_profiles`, `base.onet_context_profiles`, `base.onet_career_transitions`
**Verdict:** **APPROVED_WITH_CAVEATS**

---

## Executive summary

All four Silver O*NET tables match their declared row counts, schemas, and grain contracts against the live Iceberg data. Every one of the 37 DQ rules that executed against production passed (scorecard validated; spot-checks re-run from the live warehouse reproduced the same counts). The burnout element ID correction documented in the EDA (four wrong IDs + one nonexistent element) was correctly applied in the transformer code and DQ rule SLV-ONET-024.

However, the audit surfaced four governance hallucination risks that must be addressed before this data is propagated to Gold. Three are documentation-only drifts that mean consumers could rely on a specification/glossary that misstates reality. One is a semantic substitution (nonexistent O*NET element replaced with a differently-named element) that was never escalated to human approval via the "Open Decisions" gate the spec itself declared.

None of the findings require re-running the transformer or invalidating the Silver data. Finding F-01 (burnout-element semantic substitution) needs human sign-off before Gold can use `is_burnout_element = true` as a canonical filter. Findings F-02, F-03, F-04 are doc-drift fixes.

**Impact on silver→gold gate:** APPROVED_WITH_CAVEATS permits Gold work to proceed provided F-01 (human sign-off on the substituted burnout element) is logged before any Gold table relies on `is_burnout_element`. F-02/03/04 can be fixed in parallel and do not block.

---

## Evidence base

All evidence was collected against the live Silver Iceberg warehouse on 2026-04-16 via `brightsmith.infra.iceberg_setup.get_catalog` at `data/silver/iceberg_warehouse`, read with `read_with_duckdb`. Files inspected:

- `docs/specs/silver-base-onet.md`
- `src/silver/onet_transformer.py`
- `governance/dq-rules/silver-base-onet.json`
- `governance/dq-scorecards/silver-base-onet-scorecard.md`
- `governance/data-contracts/base-onet-occupations.yaml`
- `governance/data-contracts/base-onet-activity-profiles.yaml`
- `governance/data-contracts/base-onet-context-profiles.yaml`
- `governance/data-contracts/base-onet-career-transitions.yaml`
- `governance/chaos-manifests/silver-base-onet-chaos.md`
- `governance/eda/silver-onet-eda.md`
- `governance/business-glossary.json` (BT-059 .. BT-065)

### Ground-truth measurements against live Iceberg data

| Measure | Claim source | Claimed | Observed | Match |
|---|---|---|---|---|
| `onet_occupations` row count | DQ SLV-ONET-003 | 798 | 798 | YES |
| `onet_occupations` unique `bls_soc_code` | DQ SLV-ONET-002 | 798 | 798 | YES |
| `onet_occupations` multi_detail_flag=True | DQ SLV-ONET-004 | 76 | 76 | YES |
| `onet_occupations` tier distribution | DQ SLV-ONET-005 | full=774, partial=24, none=0 | full=774, partial=24, none=0 | YES |
| `onet_occupations` bls_soc_code format `^\d{2}-\d{4}$` | DQ SLV-ONET-001 | 0 violations | 0 | YES |
| `onet_activity_profiles` row count | DQ SLV-ONET-015 | 31,734 | 31,734 | YES |
| `onet_activity_profiles` distinct element_id | DQ SLV-ONET-012 | 41 | 41 | YES |
| `onet_activity_profiles` importance range | DQ SLV-ONET-011 | [1.0, 5.0] | [1.0, 4.99] | YES (inside) |
| `onet_activity_profiles` rank-gap check | DQ SLV-ONET-013 | 0 SOCs with gaps | 0 | YES |
| `onet_activity_profiles` suppress_flag rate | DQ SLV-ONET-014 | <1% | 0.0032% (1/31,734) | YES |
| `onet_context_profiles` row count | DQ SLV-ONET-027 | 44,118 | 44,118 | YES |
| `onet_context_profiles` scales | DQ SLV-ONET-025 | CX+CT only | CX=42,570; CT=1,548 | YES |
| `onet_context_profiles` distinct CX elements | spec | 55 | 55 | YES |
| `onet_context_profiles` distinct CT elements | spec | 2 | 2 (4.C.3.d.4, 4.C.3.d.8) | YES |
| `onet_context_profiles` CX range | DQ SLV-ONET-021 | [1.0, 5.0] | [1.0, 5.0] | YES |
| `onet_context_profiles` CT range | DQ SLV-ONET-022 | [1.0, 3.0] | [1.0, 3.0] | YES |
| `onet_context_profiles` is_burnout_element distinct IDs | DQ SLV-ONET-024 | 9 | 9 | YES |
| `onet_career_transitions` row count | DQ SLV-ONET-037 | 15,944 | 15,944 | YES |
| `onet_career_transitions` self-refs | DQ SLV-ONET-031 | 0 | 0 | YES |
| `onet_career_transitions` best_index range | DQ SLV-ONET-032 | [1, 20] | [1, 20] | YES |
| `onet_career_transitions` FK src orphans | DQ SLV-ONET-035 | 0 | 0 | YES |
| `onet_career_transitions` FK tgt orphans | DQ SLV-ONET-036 | 0 | 0 | YES |
| `onet_career_transitions` is_primary consistency | DQ SLV-ONET-034 | 0 inconsistent | 0 | YES |
| `onet_career_transitions` tier-vs-index consistency | DQ SLV-ONET-041 | 0 inconsistent | 0 | YES |
| `onet_career_transitions` relationship_type | DQ SLV-ONET-040 | all 'similarity' | all 'similarity' | YES |
| `onet_career_transitions` tier distribution | EDA | PS=4134, PL=3938, Supp=7872 | PS=4134, PL=3938, Supp=7872 | YES |
| activity_profiles FK→occupations | DQ SLV-ONET-016 | 0 orphans | 0 | YES |
| context_profiles FK→occupations | DQ SLV-ONET-026 | 0 orphans | 0 | YES |
| `onet_occupations.partial` flag pattern | implicit | has_wa=F, has_wc=F, has_tasks=T, has_related=T (all 24) | 24/24 match | YES |

Every numeric/structural claim in the spec, DQ rules, contracts, and scorecard is reproducible against the live data. The artifacts are not AI-hallucinated in the numeric-fact sense.

---

## Findings

### F-01 — Semantic substitution of a nonexistent O*NET burnout element was never human-approved (HIGH)

**Risk:** The original spec (§Table 3) proposed 9 burnout-relevant elements and explicitly made "Burnout element selection" Open Decision #1 pending human approval. The EDA discovered that one of the proposed elements — "Responsibility for Outcomes and Results" (spec mapping `4.C.3.b.7`) — does not exist anywhere in O*NET. The EDA proposed substituting `4.C.3.a.2.a` "Impact of Decisions on Co-workers or Company Results" as a closest-match replacement (EDA line 35, 49). The transformer (`src/silver/onet_transformer.py:54`) ships this substitution; DQ rule SLV-ONET-024 codifies it; the scorecard records 9 burnout elements passing.

This is the single Silver-introduced semantic claim in this pipeline that materially drives downstream behavior: every Gold-zone Burnout boss-fight score will weight "Impact of Decisions on Co-workers or Company Results" as if it were a direct proxy for "responsibility pressure." A regulator (or a psychologist reviewing the product) would reasonably challenge whether those two elements are semantically interchangeable. They measure adjacent but distinct constructs — "impact" captures scope of consequence on others, not the felt responsibility burden on the worker.

**Evidence:**
- `docs/specs/silver-base-onet.md:314` — Open Decisions item 1 flags burnout selection for human approval.
- `governance/eda/silver-onet-eda.md:35` — "ELEMENT NOT FOUND -- no element with this name exists."
- `src/silver/onet_transformer.py:54` — `"4.C.3.a.2.a",  # Impact of Decisions on Co-workers or Company Results (CX)`
- `governance/dq-rules/silver-base-onet.json` rule SLV-ONET-024 — 9 specific IDs codified including the substitute.
- `governance/business-glossary.json` BT-059 — definition still names "Responsibility for Outcomes and Results" (not the substitute) — see F-02.
- DQ rule `approved_by: "human", approved_at: 2026-04-09T00:49:35Z"` — this was a bulk timestamp across all rules (all 37 rules share the same 8ms window of approvals), strongly suggesting a programmatic approval rather than deliberate human consideration of the substitution.

**Evidence demanded:**
1. A signed human-approval audit-trail entry explicitly naming: "Original spec proposed `Responsibility for Outcomes and Results`; no such O*NET element exists; substitute chosen is `4.C.3.a.2.a Impact of Decisions on Co-workers or Company Results` (CX). Human reviewer accepts this substitution as an adequate proxy for the original construct and understands it will anchor the Gold Burnout boss-fight score." Must be dated distinctly from the bulk rule-approval timestamp.
2. Either the original proposer or the Gold Burnout-scoring author should co-sign, confirming downstream semantics still hold.
3. OR: drop the substituted element and ship 8 burnout elements, updating the spec, DQ rule, contract, and glossary consistently.

**Controls assessment:** WEAK. The EDA correctly flagged the issue and proposed a fix. The Open Decisions gate in the spec mandated human approval. The bulk-stamped DQ-rule approvals do not meet that bar. No separate escalation note exists in `governance/audit-trail/`.

---

### F-02 — Business glossary BT-059 definition is stale relative to shipped implementation (MEDIUM)

**Risk:** The BT-059 "Burnout Element" definition in `governance/business-glossary.json` still enumerates the original spec's 9 proposed elements, including "Responsibility for Outcomes and Results" — an element that does not exist in O*NET and is not in the shipped data. Any downstream consumer (another agent, a reviewer, or a Gold-zone dev) who reads the glossary to understand `is_burnout_element` will be given a wrong list. The data contract for `base.onet_context_profiles` also references BT-059 on the `is_burnout_element` column, so the misalignment propagates into the contract surface.

**Evidence:**
- `governance/business-glossary.json` BT-059 definition text enumerates ". . . Importance of Repeating Same Tasks, **Responsibility for Outcomes and Results**, and Work Schedules." That element is nowhere in the shipped data (verified: 9 actual burnout IDs listed in the table above).
- `governance/data-contracts/base-onet-context-profiles.yaml:122` references BT-059 as the business term for `is_burnout_element`.

**Evidence demanded:**
Glossary definition updated to list the 9 actual element IDs and names that appear in the data, with a note that the spec's original list contained errors corrected during EDA. Also add a reference to the audit-trail entry from F-01.

**Controls assessment:** MISSING. No DQ rule checks glossary consistency with implementation. The only safeguard is human review of the glossary, and there is no record that BT-059 was re-reviewed after the EDA correction.

---

### F-03 — Business glossary BT-064 partial-occupation count is stale (LOW)

**Risk:** BT-064 "Data Completeness Tier (O*NET)" definition reads: "'partial' means some but not all are present (approximately 29 occupations — typically newer occupations awaiting full survey coverage)." The actual count is 24 (EDA corrected, DQ rule SLV-ONET-005 encodes 24, live data confirms 24). BT-064 also references "'none' means ... the 93 'All Other'/Military residual occupations", but at BLS level only 69 are excluded (867 - 798 = 69). A regulator reading BT-064 alone would be given numbers that disagree with the DQ rules and the scorecard.

**Evidence:**
- `governance/business-glossary.json` BT-064: "approximately 29 occupations"; "the 93 'All Other'/Military residual occupations."
- `governance/dq-rules/silver-base-onet.json` SLV-ONET-003 rationale: "867 derivable BLS SOCs minus 69 truly empty BLS SOCs."
- Live data: 24 partial, 69 excluded.

**Evidence demanded:** Glossary numbers updated to 24 and 69 (or rephrased as "~24" and "~69") to match EDA/DQ reality.

**Controls assessment:** MISSING. Same class of drift as F-02: no automated check, and the glossary was written against the stale spec.

---

### F-04 — Spec (`docs/specs/silver-base-onet.md`) was never revised after EDA invalidated its row-count and element-ID claims (MEDIUM)

**Risk:** The spec is flagged COMPLETE and is the declared "source of truth" per project CLAUDE.md. Yet it still says:

- "~867" rows for `onet_occupations` (actual 798; EDA/DQ agreed on 798)
- "~36,654 rows" (actual 31,734) for activity_profiles — the spec's formula "894 × 41" is based on the pre-exclusion O*NET-SOC count, not the post-aggregation BLS count the pipeline actually produces.
- "~50,958" and "~49,419" for context_profiles (actual 44,118).
- 9 burnout element IDs listed in §Table 3 include 4 wrong IDs and one nonexistent element name.
- "29 partial-data occupations" (actual 24).
- "exclude 93 'All Other'/Military" (at BLS level, 69 are excluded).

The spec does include a caveat at line 135 ("The exact element IDs need to be confirmed against the actual Bronze data") but the spec was never amended after that confirmation. Any future agent reading the spec first will be misinformed. If the Gold layer is generated directly from the spec (as CLAUDE.md mandates), any Gold spec author pulling numbers from this document will inherit wrong expectations.

**Evidence:**
- `docs/specs/silver-base-onet.md:74, 111, 162, 195, 224, 123-133` — all stale against verified reality.

**Evidence demanded:** Either amend the spec with a "§EDA Corrections" section that supersedes the stale numbers and element IDs, or mark the spec as "frozen pre-EDA; see `governance/eda/silver-onet-eda.md` for authoritative numbers."

**Controls assessment:** WEAK. The EDA is the de-facto source of truth, and the DQ rules/scorecard/contracts all align with the EDA. But the spec itself — which CLAUDE.md designates as the primary source of truth — is stale. That is a governance-integrity issue, not a data issue.

---

### F-05 — DQ rule ID gaps (SLV-ONET-008, -009, -018, -019) are not documented (LOW / INFO)

**Risk:** Rule IDs jump from -007 to -010, from -017 to -020. These gaps are likely rules that were proposed and dropped, but the artifact does not record why. A regulator would ask whether those rules were silently removed because they could not be satisfied.

**Evidence:** `governance/dq-rules/silver-base-onet.json` rule sequence: 001–007, 010–017, 020–029, 030–041.

**Evidence demanded:** Either re-number the rules contiguously or add a "rationale for gap" note. Acceptable to record as an INFO finding and defer unless a pattern emerges across other specs.

**Controls assessment:** INFO / cosmetic. No data-quality impact.

---

### F-06 — Chaos-monkey identified 5 rules that never fired; recommendations were never executed (LOW)

**Risk:** The chaos report (`governance/chaos-manifests/silver-base-onet-chaos.md`) identifies 5 rules (SLV-ONET-006, 012, 014, 023, 029) that stayed silent across all 3 cycles and made specific recommendations to `@dq-rule-writer` (tighten thresholds, add self-reference check, add CXP/CTP scale filter check, add detail-count-vs-codes consistency rule, etc.). No follow-up action is recorded. Two of those recommendations (self-references, CXP/CTP scale) are in fact already covered by SLV-ONET-031 and SLV-ONET-025, but the report does not close that loop. The other three recommendations appear un-addressed.

**Evidence:** `governance/chaos-manifests/silver-base-onet-chaos.md` §"Recommendations for @dq-rule-writer."

**Evidence demanded:** A short disposition note per recommendation — either "already covered by rule X" or "deferred because Y" or "new rule added." Without this, a regulator cannot tell whether the chaos findings were addressed or ignored.

**Controls assessment:** ADEQUATE. The P0 gate passed, coverage was 86.5%, and the chaos work itself is strong. But the recommendations loop is open.

---

### F-07 — "1.5% of Work Activity rows" and "2.5% of Work Context rows" claims in BT-062 are not grounded in evidence (LOW)

**Risk:** BT-062 "Suppress Flag" definition says "Affects approximately 1.5% of Work Activity rows and 2.5% of Work Context rows." The actual rates are 0.003% for activity_profiles and far below 1% for context_profiles (EDA: 18 of 49,170 CX = 0.04%; DQ rule SLV-ONET-014 rationale: "0.003%"). The glossary rates are off by ~500x for activity and ~60x for context. A consumer calibrating alerting on this term would overstate the expected incidence by orders of magnitude.

**Evidence:**
- `governance/business-glossary.json` BT-062: "1.5%" and "2.5%."
- `governance/dq-rules/silver-base-onet.json` SLV-ONET-014 and SLV-ONET-029 rationales + live data: 0.003% and 0.04%.

**Evidence demanded:** Correct BT-062 rates or rephrase as "a small fraction (< 1%)."

**Controls assessment:** MISSING. No glossary-vs-data validation exists.

---

## Verdict

**APPROVED_WITH_CAVEATS.**

The Silver data itself is correct, its structural DQ story is solid (37/37 production DQ rules pass, verified against live Iceberg), and chaos hardening is mature (86.5% rule activation across 3 cycles). Row-count, grain, FK, and scale-range claims all match reality.

However, before Gold-zone work consumes `is_burnout_element` as a semantic filter, Finding **F-01 must have an explicit human approval** attached. The substitution of a nonexistent O*NET construct ("Responsibility for Outcomes and Results") with a different, adjacent construct ("Impact of Decisions on Co-workers or Company Results") was a material semantic decision; the spec's own Open Decisions gate required human approval; the batch DQ-rule-approval timestamp does not satisfy that gate.

**This does NOT block the silver→gold transition outright.** Gold work for tables that do not depend on `is_burnout_element` can proceed. Gold work that uses `is_burnout_element` as a canonical filter (e.g., the Burnout boss-fight formula in `gold-futureproof-engine`) must not ship until F-01 is closed with a timestamped human sign-off.

Findings F-02, F-03, F-04, F-07 are documentation drifts: the glossary and spec do not reflect the EDA corrections that the transformer and DQ rules implement correctly. They should be fixed promptly but do not block Gold. Finding F-05 is cosmetic. Finding F-06 is an open chaos-recommendation loop.

## Recommended actions (in order)

1. **BLOCKER for Burnout-dependent Gold work (F-01):** log a distinct human approval for the `4.C.3.a.2.a` substitution in `governance/audit-trail/2026-04-16-burnout-element-substitution-approval.md`, co-signed by the spec's "Open Decisions" reviewer and whoever owns the Gold Burnout formula. Alternative: drop element 9 and ship 8 burnout elements.
2. Update `governance/business-glossary.json` BT-059 to list the 9 actual shipped element IDs and their names (F-02).
3. Update BT-064 partial-count to 24 and BLS-level excluded count to 69 (F-03).
4. Amend `docs/specs/silver-base-onet.md` with an EDA-corrections block or a pointer to `governance/eda/silver-onet-eda.md` as authoritative (F-04).
5. Update BT-062 suppress-rate percentages (F-07).
6. Document dispositions for the 5 never-fired chaos rules (F-06).
7. Close the rule-ID gaps or document them (F-05).
