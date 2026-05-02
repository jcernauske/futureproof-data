# Adversarial Audit — `consumable.institution_aura`

**Spec:** `docs/specs/full-pipeline-eada.md`
**Snapshot under audit:** `5887248523326294782` (parquet `00000-0-0be00d2a-…`, MD5 `6a4a3f66009e40bfb428eb962326d0c4`, 3,223 rows × 19 cols)
**Audit date:** 2026-04-30
**Auditor:** adversarial-auditor (skeptical data governance reviewer)
**Methodology:** Independent re-execution against the live parquet bytes — bypassing the chaos runner, the dq_runner, and the EDA assertions. Every number below was recomputed by this audit; nothing is restated from upstream artifacts.

---

## §1 Scope of independent verification

| Independent check | Method | Result |
|---|---|---|
| Parquet MD5 pre/post audit | `md5(.parquet)` | `6a4a3f66009e40bfb428eb962326d0c4` unchanged |
| 14-anchor v1 score re-derivation | Reimplemented `percent_rank → MAX+MEAN → P5/P95 → ROUND` from scratch in Python; compared to stored `aura_score` | **14/14 EXACT** |
| Full-population v1 reproduction | Same Python recompute on all 3,223 rows | **0 basis mismatches, 0 integer-score mismatches, 0 continuous mismatches >1e-9** |
| Chaos T1 re-execution (FULL OUTER → INNER) | Drop `coverage_tier ∈ {finance_only, athletics_only}` → `n=1492 < 2675` floor | CON-AUR-001 fires (confirmed) |
| Chaos T6 re-execution (NULL-iff break) | Set `aura_score_basis=NULL` while `aura_score=5` | CON-AUR-011 + CON-AUR-034 fire (confirmed) |
| **Chaos T10 re-execution (stratum collapse)** | **Push 92% of three_term → bucket 7 on full population** | **CON-AUR-030 does NOT fire — strata still cover 10/10 buckets** ⚠️ |
| CON-AUR-021 coverage measurement | `2,295 matched / 2,559 distinct career_outcomes UNITIDs` | **89.6835%** (gap = 0.3165pp below 90%) — reproduces scorecard exactly |
| CON-AUR-033 5th-invalid-case scan | `WHERE basis NOT IN (4 enums) AND basis IS NOT NULL` | 0 rows |
| 579 NULL-aura decomposition | `coverage_tier` breakdown of NULL-aura rows | 548 athletics_only + 31 finance_only (matches EDA Item 4 narrative) |
| `aura_score_version` stamp | `GROUP BY aura_score_version` | 3,223 / 3,223 = `'v1'` |

---

## §2 Risk Register

### R1 — Chaos T10 attribution defect (HIGH severity, governance credibility issue)

**Risk:** The chaos report claims T10 (push 92% of `three_term` to bucket 7) caused CON-AUR-030 to fire as part of the headline "10/10 targeted attacks caught" tally. Independent re-execution shows T10 alone does **not** trigger CON-AUR-030 — the remaining 8% of `three_term` rows (114 rows on the full population, or ~113 of 1,302 within the 'both' subset post-T1) still span all 10 integer buckets.

**Evidence (independent replay, Python):**
- T10 applied to pristine data only: per-stratum bucket counts post-T10 are `{'three_term': 10, 'two_term_finance_only': 10, 'two_term_no_endowment': 10, 'one_term_marketing_only': 10}`. CON-AUR-030 production SQL (`per_stratum.MIN(bucket_count) < 4 OR overall < 6`) returns FALSE.
- Looking at the chaos runner's own `…-chaos-results.json`: in the targeted-run, CON-AUR-030 fires with `detail = "strata failing >=4/10 coverage: ['invalid_value:1/10']"` — i.e., the stratum that fails is the **`'invalid_value'` stratum created by T7**, not the `three_term` stratum that T10 was supposed to collapse.
- The runner's `targeted_inject` runs T1–T10 in order on the same `out` list, then evaluates DQ once at the end. Because T7 (basis-enum corruption) precedes the evaluation and the runner's CON-AUR-030 implementation does NOT pre-filter strata against the valid enum, the bogus `'invalid_value'` basis becomes its own degenerate stratum. T10's actual contribution (three_term collapse) is invisible.

**Why this matters:** The chaos report's "10/10 caught" headline depends on the implicit claim that each targeted attack would, in isolation, fire its expected rule. T10 fails that claim. If a real-world regression collapsed three_term into a single bucket, **CON-AUR-030 as written would not catch it** unless the collapse went below 4 buckets per stratum — and a 92%-to-one-bucket distortion sits at 10 buckets thanks to the long tail. The threshold is structurally too lax for stratum-skew detection at this population size.

**Production-rule severity:** The production CON-AUR-030 SQL filters `WHERE aura_score_basis IS NOT NULL`, so it does NOT include an `'invalid_value'` row in the per-stratum count (DuckDB groups by literal value, including the bogus one) — meaning **production CON-AUR-030 would also fire on T7 due to the bogus stratum**, but that's redundant with CON-AUR-033. The production rule still does NOT fire on T10 alone.

**Severity:** HIGH (chaos credibility — the headline metric is misleading). Mitigations exist (CON-AUR-013 catches arithmetic break, CON-AUR-014 catches range break, CON-AUR-031 catches median drift) but the specific "stratum collapse" attack class is not actually defended.

---

### R2 — CON-AUR-030 threshold structurally too lax (MEDIUM severity)

**Risk:** A `< 4 of 10 buckets` per-stratum threshold permits an attacker / regression to push 90+% of a stratum to a single bucket without triggering. With 1,417 `three_term` rows in the population, a pathological transform that smooths/quantizes the score distribution to 4 modes would pass.

**Evidence:** Independent replay confirms 92% one-bucket collapse leaves `three_term` at 10/10 buckets. Even pushing 95% to one bucket would leave ~71 rows over 10 buckets — likely still ≥4/10. The threshold doesn't sense **distribution shape**, only **support cardinality**.

**Recommendation:** Add a P1 entropy / Gini concentration rule per stratum (e.g., `top-1 bucket share < 0.50`), or tighten CON-AUR-030 to a **mode-share** check rather than a bucket-count check.

**Severity:** MEDIUM.

---

### R3 — CON-AUR-021 sub-threshold (P1 FAIL, 89.68% vs 90%) (LOW severity, recommend documentation)

**Risk:** 264 of 2,559 distinct UNITIDs in `consumable.career_outcomes` do not have a row in `consumable.institution_aura`. Pentagon UI joining `career_outcomes → institution_aura` will silently drop the aura column for these 264 institutions.

**Evidence:** Independent recompute: `2,295 matched / 2,559 = 89.6835%`. Reproduces the scorecard exactly.

**Whether the gap is structural or a defect:** The 264 missing UNITIDs are College Scorecard institutions absent from BOTH `base.ipeds_finance` AND `base.eada`. Plausible structural causes:
- College Scorecard's Field-of-Study file ingests programs whose institution did not file IPEDS Finance F1A/F2/F3 in the target FY 2022 cycle (e.g., specialty colleges, recently-closed campuses, sub-2-yr programs not subject to IPEDS Finance survey).
- EADA only covers Title-IV institutions with intercollegiate athletics — a non-athletics non-Title-IV institution would be absent from both bases.

**Whether the rule is over-precise:** Yes, the 90% threshold is spec-pinned without empirical calibration. Per the scorecard's own diagnosis: *"the 90% threshold is spec-pinned (not EDA-calibrated) pending one full annual cycle of observation."* The threshold has **no evidentiary basis**; it is a placeholder.

**Recommendation:** I cannot recommend silently widening to 89% — that hides the actual delta from future readers. **Preferred remediation:** enumerate the 264 missing UNITIDs in the EDA report under "documented drift" with at least a domain-class breakdown (specialty college / sub-2yr / closed / international / other), then either:
- (a) keep threshold at 90% with documented-drift exception list, OR
- (b) widen to 89% with a comment that explicitly references the 264-row drift and the next-annual-cycle re-tightening commitment.

Option (a) is governance-cleaner; option (b) is operationally simpler. Either is defensible. **Silently flipping the threshold without enumerating the drift is not.**

**Severity:** LOW (P1 sub-threshold, does not block P0 gate, drift is structurally explainable).

---

### R4 — `aura_score_basis` enum exhaustiveness — VERIFIED (no risk)

**Check:** `SELECT * FROM consumable.institution_aura WHERE aura_score_basis IS NOT NULL AND aura_score_basis NOT IN ('three_term', 'two_term_finance_only', 'two_term_no_endowment', 'one_term_marketing_only')` → **0 rows**.

**5-value enum coverage:**
- `three_term`: 1,417 (has_ipeds_finance ∧ has_eada, non-null endow ∧ ath)
- `two_term_finance_only`: 579 (has_finance ∧ NOT has_eada, non-null endow ∧ NULL ath)
- `two_term_no_endowment`: 75 (has_finance ∧ has_eada, NULL endow ∧ non-null ath)
- `one_term_marketing_only`: 573 (has_finance ∧ NOT has_eada, NULL endow ∧ NULL ath)
- NULL: 579 (548 athletics_only + 31 finance_only with `marketing_ratio IS NULL OR instruction_per_fte = 0`)

Total: 3,223 ✅. Enum is exhaustive on this snapshot.

**Caveat:** EDA narrative numbers are slightly stale (EDA Item 4 said `581 / 75 / 602 / 548` ≈ 1,806; live is `579 / 75 / 573 / 579` = 1,806). The drift is in finance_only buckets (581→579, 602→573) — likely a silver-zone re-ingest between EDA and gold-promote. **Not a hallucination — just a reconciliation lag.** Recommend updating the EDA narrative numbers to match the snapshot 5887248523326294782 live state.

**Severity:** NONE (enum exhaustiveness verified). Documentation drift only.

---

### R5 — v1 formula reproduction — PASS (no risk)

**Check:** Re-implemented in fresh Python — `PERCENT_RANK` (ties share lowest rank, n=1→0.0, NULL→NULL), `0.65·MAX + 0.35·MEAN` over available rp_*, P5=0.1413/P95=0.9400 linear rescale, clamp to [0,1], stretch to [1,10], `int(round(...))`. Compared to stored `aura_score` and `aura_score_continuous` for **all 3,223 rows**.

**Result:**
- 0/3,223 basis mismatches.
- 0/3,223 integer score mismatches.
- 0/3,223 continuous mismatches (tolerance 1e-9).
- 14/14 anchor schools match expected EDA scores AND match observed parquet AND match my recompute.

**This is the strongest possible evidence: the gold transformer faithfully implements the v1 formula as specified by the EDA, end-to-end, on the production population.**

**Severity:** NONE.

---

### R6 — Other targeted attacks — independently re-executed (NO additional risk)

| Attack | Independent verdict |
|---|---|
| T1 (FULL OUTER → INNER, drop to 1,492 rows) | CON-AUR-001 fires (1,492 < 2,675 floor) ✅ |
| T6 (basis=NULL while aura_score=5) | CON-AUR-011 + CON-AUR-034 both fire (1 row violates iff) ✅ |

T2, T3, T4, T5, T7, T8, T9 not independently re-executed by this audit (their rule-firing semantics are simple cardinality / range / enum checks; the independent v1 formula reproduction already validated the underlying data is correct, so these attacks reduce to "does the rule SQL do what it says" — a code-review concern, not a hallucination concern).

---

## §3 Hallucination findings — summary

| Artifact | Hallucination found? | Detail |
|---|---|---|
| DQ rules JSON (`governance/dq-rules/consumable-institution-aura.json`) | NO | All 19 rule SQL statements grounded in observed data; thresholds traceable to spec or EDA. CON-AUR-021 is acknowledged as spec-pinned not EDA-calibrated. |
| Scorecard MD/JSON | NO | All numbers reproduce against live parquet to the digit. |
| Chaos report MD | YES (1) | T10 → CON-AUR-030 attribution is incorrect. The report claims T10 caused CON-AUR-030 to fire; independent replay shows the actual cause was T7 (`'invalid_value'` basis creating a degenerate-singleton stratum). The "10/10 caught" headline is technically true only because the cycle-injector's coarser `coverage_strata_collapse` attack at higher rates trips the rule via the same mechanism — not because the targeted attack semantics are sound. |
| EDA report MD | NO (with caveat) | All structural findings (correlation matrix, anchor pass/fail under v0/v1, P5/P95 calibration) reproduce. Distribution counts (581/602/548) are stale by ~30 rows total relative to the snapshot under audit (`579/573/579`). Reconciliation lag, not hallucination. |
| Gold transformer (`src/gold/institution_aura.py`) | NO | Code matches the EDA-specified algorithm exactly; 3,223/3,223 rows independently reproducible. |

---

## §4 Recommendations to close gaps

1. **R1 (HIGH):** Either (a) replace T10 in the chaos manifest with a stronger collapse (e.g., push 99% to one bucket so remaining n × support < 4) and re-run, OR (b) tighten CON-AUR-030 to detect mode-share concentration, not just bucket cardinality. **Until one of these lands, do not advertise "stratum collapse" as a defended attack class.**
2. **R2 (MEDIUM):** Add a P1 entropy or top-1 mode-share rule per stratum — e.g., `MAX(stratum_bucket_share) < 0.40`. This is the actual semantic check the spec wanted.
3. **R3 (LOW):** Enumerate the 264 missing-from-aura UNITIDs in the EDA report with a domain-class breakdown. Then either keep CON-AUR-021 at 90% with a documented-drift exception list, or widen to 89% with a comment cross-referencing the enumeration. Do not silently widen.
4. **R4 (DOC):** Update the EDA narrative `581/602/548` numbers to match the snapshot under audit (`579/573/579`). Single-line edit.
5. **(Bonus) Chaos runner hygiene:** When attacks compose (T1–T10 applied in sequence and evaluated once), per-attack attribution becomes ambiguous. Re-run each targeted attack in isolation against pristine data and emit per-attack independent rule-firing tables in the chaos report.

---

## §5 Adversarial verdict

| Question | Answer |
|---|---|
| Did the AI agents hallucinate the v1 formula? | **NO.** 14/14 anchors and 3,223/3,223 rows reproduce exactly under independent recompute. |
| Did the AI agents hallucinate the DQ rules? | **NO.** Every rule SQL was independently traced to its evidentiary source; thresholds are either reproducibly EDA-calibrated or explicitly flagged as spec-pinned. |
| Did the AI agents hallucinate the chaos coverage? | **PARTIALLY.** The "10/10 targeted attacks caught" headline is overstated: T10's expected rule (CON-AUR-030 stratum collapse) does NOT actually fire on T10's corruption alone — the rule fires for an unrelated reason (T7's `'invalid_value'` basis). The defended attack class "stratum collapse" is, in practice, undefended at typical population sizes. |
| Did the AI agents hallucinate the basis enum? | **NO.** 5-value enum is exhaustive on the snapshot; 0 rows fall outside. |
| Is CON-AUR-021's 89.68% real or threshold over-precision? | **Real coverage gap, but structurally explainable.** 264 institutions are absent from both base sources by construction. Threshold is spec-pinned without empirical basis. Recommend documented-drift enumeration before widening. |

---

## §6 Decision

**CLEAR for governance-reviewer with conditions.**

Conditions:
- (C1) Acknowledge R1 (T10 attribution defect) in the §8 spec entry. Either tighten CON-AUR-030 (per R2 recommendation) before a v2 refresh, or annotate the chaos report to make clear that stratum-collapse defense relies on the redundant CON-AUR-031 (median sanity) and CON-AUR-013 (round-of-continuous) rules rather than CON-AUR-030 alone.
- (C2) Acknowledge R3 (CON-AUR-021 sub-threshold) and pick a path: enumerate the 264 missing UNITIDs in the EDA, OR widen to 89% with rationale. **Don't ship without picking.**
- (C3) Update EDA narrative basis-counts to match snapshot 5887248523326294782.

The v1 aura formula itself is **trustworthy** — independent reproduction confirms zero hallucination in the gold transformer. The DQ rule set is **mostly trustworthy** — the only real gap is CON-AUR-030's structural laxity. The chaos report's headline is **slightly misleading** but the underlying production rules are sound.

**A regulator would accept this pipeline conditional on C1–C3 being addressed in writing before promotion.**

---

**Independent verification artifacts (in this audit, not from upstream):**
- 14-anchor recompute: 14/14 exact match
- 3,223-row recompute: 0 mismatches (basis, integer, continuous to 1e-9)
- T1 replay: confirms CON-AUR-001 fires
- T6 replay: confirms CON-AUR-011 + CON-AUR-034 fire
- T10 replay: **does NOT fire CON-AUR-030 alone** ⚠️
- CON-AUR-021 recompute: 89.6835% (matches scorecard)
- Basis enum scan: 0 invalid values
- 579 NULL decomposition: 548 athletics_only + 31 finance_only (matches EDA Item 4)
- Pre/post audit MD5: `6a4a3f66009e40bfb428eb962326d0c4` unchanged
