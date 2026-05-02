# Adversarial Audit — consumable.ipeds_finance_profile

**Auditor:** adversarial-auditor (skeptical data-governance role)
**Spec:** `docs/specs/full-pipeline-ipeds-finance.md` v1.3
**Targets reviewed:**
- `governance/dq-rules/consumable-ipeds-finance-profile.json` (11 rules: 8 P0, 2 P1, 1 P2 watch-line)
- `governance/dq-rules/base-ipeds-finance.json` (cross-zone reference for upstream guards: 19 rules)
- `governance/dq-rules/raw-ipeds-finance.json` (cross-zone reference: 14 rules)
- `governance/eda/raw-ingest-ipeds-finance-eda.md` (FY2022 evidence base for thresholds)
- `governance/adversarial-audits/raw-ipeds-finance-bronze-audit.md` (structural pattern)
- `src/gold/ipeds_finance_profile.py` (consumable transformer)
- `src/silver/ipeds_finance_base.py` (base transformer — cross-zone arithmetic)
- `data/gold/iceberg_warehouse/consumable/ipeds_finance_profile/data/00000-0-619e4d06-a2d5-42b0-b2af-0fab07486c57.parquet` (live snapshot 6649279885162971471, 2,675 rows, FY2023)
- `data/gold/iceberg_warehouse/consumable/career_outcomes/data/*.parquet` (cross-table join target, 2,559 distinct UNITIDs)
**Date:** 2026-04-30
**Verdict (TL;DR):** **CLEAR for governance review with FOUR HIGH-severity gaps requiring documented mitigations before downstream EADA fusion proceeds.** No P0 blockers; the consumable shape is internally consistent (CON-IFP-006 holds, conservation holds, distributions are within calibrated bands). The risks below are all *consumer-misuse* gaps that the bronze adversarial audit could not surface — they live entirely at the consumable contract surface and the downstream-consumer documentation surface. Eight gaps total: 4 HIGH, 3 MEDIUM, 1 LOW.

---

## 1. Risk Register

### Gap 1 — `data_completeness_tier='high'` is decoupled from `marketing_ratio` computability — **HIGH**

Per spec §6.2 and the transformer (`src/gold/ipeds_finance_profile.py:174-190`), `data_completeness_tier` counts non-null *independent raw inputs*: `instruction_expenses`, `institutional_support_expenses`, `endowment_value`, `total_fte_enrollment > 0`. A row with `instruction_expenses = 0` (a legitimate value, not NULL) counts as "present" for the tier signal — but `marketing_ratio = institutional_support_expenses / NULLIF(instruction_expenses, 0)` evaluates to NULL on that row.

**Live evidence:** 2 rows in the landed table land at `data_completeness_tier='high'` with `marketing_ratio IS NULL`:

| UNITID | Institution | tier | marketing_ratio | instruction_expenses |
|---|---|---|---|---|
| 187046 | Thomas Edison State University | high | NULL | $0 |
| 195049 | The Rockefeller University | high | NULL | $0 |

A downstream EADA-fusion or comparison spec that gates "include in marketing-ratio analysis" on `tier IN ('high', 'medium')` (the contract pattern explicitly recommended in fp-data-reviewer's bonus-section guidance, §7) will admit these two rows — and then crash, NULL-cascade, or silently drop them depending on how the downstream join is written.

**Why this is HIGH and not LOW:**
- It is a **semantic-mismatch risk**: the tier is documented (BT-IPF-DATA-COMPLETENESS-TIER glossary entry; spec §6.2) as a "source-data-completeness signal." Consumers will reasonably interpret `high` as "all fields usable" — but it actually means "all source fields non-null." A reported `0` is non-null but unusable as a divisor.
- The two rows that exhibit this pattern (a state online-degree completion mill and a private graduate research institution) are *exactly the institutions* a transparency report would want to include or exclude with full awareness — not silently mis-handle.
- No DQ rule in the consumable rule set (CON-IFP-001..010 + 008b) catches this disagreement. CON-IFP-006 verifies the tier is correctly *classified per the spec formula*, not that the tier *means what consumers think it means*.

**Severity:** HIGH (semantic contract violation; affects downstream rankings and gating logic).

### Gap 2 — Marketing-ratio outliers are dominated by state-system administrative offices; no consumer-facing exclusion guidance — **HIGH**

The top 25 rows by `marketing_ratio` in the landed table are *not* "the most marketing-heavy institutions" in any meaningful sense. They are administrative offices that report institutional overhead but no instructional spend:

| UNITID | Institution | marketing_ratio |
|---|---|---|
| 242060 | Sistema Universitario Ana G. Mendez | **5,265.5** |
| 128300 | University of Colorado System Office | 502.8 |
| 149587 | University of Illinois System Offices | 150.0 |
| 117681 | Los Angeles Community College District Office | 84.3 |
| 492263 | The University of Tennessee System Office | 83.7 |
| 195827 | SUNY-System Office | 62.1 |
| 438665 | Rancho Santiago Community College District Office | 32.7 |
| 222497 | Alamo Community College District Central Office | 27.8 |
| 231156 | Vermont State Colleges-Office of the Chancellor | 19.8 |
| 242671 | Inter American University of Puerto Rico-Central Office | 14.0 |
| 166665 | University of Massachusetts-Central Office | 13.7 |
| 428453 | Minnesota State Colleges and Universities System Office | 9.1 |
| ... | (continues with 13 more administrative offices in the top 25) |

The EDA already identified this pattern (EDA §6, §10) and recommended a v1.4 second-tier filter at the bronze→base boundary excluding UNITIDs whose names match `~~ ' Office' OR ' System' OR 'Chancellor'`. **That filter was NOT adopted.** All 25 of these rows landed in the consumable.

A naïve downstream UI that ranks "institutions by spending breakdown" descending by `marketing_ratio` (or any equivalent — e.g., a "schools spending the most on admin per dollar of teaching" leaderboard) will surface SUNY-System Office, the LA CCD Office, and U Colorado System Office in the top 10, presenting them as institutional-malfeasance outliers when they are **organizational artifacts**.

**Live evidence:** of the 25 highest-marketing_ratio rows, 18 (72%) have `' Office'`, `'System'`, or `'Chancellor'` in the institution name; 24 of 25 have FTE NULL or < 200 (the 25th — Sistema Universitario Ana G. Mendez at 5,265× — has FTE NULL).

**Severity:** HIGH (high-visibility consumer-misuse risk; downstream ranking UIs are explicitly named in the "future receipts/comparison specs" line of the §6 Data Contract Consumers list).

### Gap 3 — Vintage drift is unjoinable: `consumable.career_outcomes` carries no `fiscal_year` column — **HIGH**

Per the landed schema, `consumable.ipeds_finance_profile.fiscal_year = 2023` (single-value invariant). But `consumable.career_outcomes` schema does NOT contain a `fiscal_year` column (verified via DESCRIBE). The CON-IFP-008 coverage rule joins on `unitid` only — there is no vintage-aware constraint on the join.

**Cascading risk:** when bronze is re-ingested for FY24 (per spec §9 deviations table, this is a parameter change, not a code change), the consumable will land with `fiscal_year=2024` for all 2,675 rows. If `consumable.career_outcomes` retains its FY2022 (or whatever its current vintage is) and a downstream consumer joins the two unconditionally, the consumer is silently performing **cross-vintage analysis** with no warning.

**The bronze re-ingest already happened once in this project's history** — the §9 deviations table records that bronze was re-ingested from FY2022 (2,683 rows) to FY2023 (2,675 rows) between the §4 implementation log and the §5 base-zone run. The same operation is documented as routine. So this is not a hypothetical: it has happened and will happen again.

**Live evidence:**
- `consumable.ipeds_finance_profile`: `fiscal_year IN (2023)`, single-valued.
- `consumable.career_outcomes`: no `fiscal_year` column.
- CON-IFP-008 SQL: `WHERE EXISTS (SELECT 1 FROM consumable.ipeds_finance_profile ifp WHERE ifp.unitid = co.unitid)` — no vintage clause.

**Severity:** HIGH (silent cross-vintage analysis is the canonical regulator-attention failure mode; the join key carries no temporal alignment).

### Gap 4 — Future EADA fusion silently drops 100% of F3 institutions on any composite that requires `endowment_per_fte` — **HIGH**

The user's hypothesis is confirmed: 277 / 277 F3 (private for-profit) institutions land with `endowment_per_fte = NULL` (structural — F3 has no `F3H` family per spec §3 v1.3 lock). Of those 277 F3 rows, 213 also appear in `consumable.career_outcomes`. A downstream EADA-fusion `aura_score` formula that includes `endowment_per_fte` as an additive or multiplicative component will silently drop **all 213 F3-with-CO-match institutions**.

**Live evidence:** distinct UNITIDs by report_form that match consumable.career_outcomes AND have `endowment_per_fte IS NOT NULL`:

| report_form | matched UNITIDs | with endow | drop rate on endow-required formula |
|---|---|---|---|
| F1A | 729 | 674 | 7.5% |
| F2 | 1,328 | 1,107 | 16.6% |
| F3 | 213 | **0** | **100%** |

CON-IFP-005 catches a tier outside the enum. CON-IFP-006 catches tier-classification arithmetic. Neither catches the case where a future EADA spec assumes `endowment_per_fte` is non-NULL for all consumable rows.

**Why this is HIGH:** the §6 Data Contract names `raw-ingest-eada.md` as the primary downstream consumer. The `report_form` column IS in the consumable schema (so segmentation is *possible*), but there is no contract clause requiring EADA to gate on `report_form != 'F3'` for endowment-dependent composites. A contract clause is the only thing standing between a future agent writing an EADA aura_score formula and a 100% F3 silent drop.

**Severity:** HIGH (a named downstream consumer; a structural NULL pattern; no contract-level mitigation).

### Gap 5 — `data_completeness_tier='medium'` lumps semantically distinct states — **MEDIUM**

`tier='medium'` covers `non_null_signals IN (2, 3)`. The fp-data-reviewer flagged this concern in the original v1.0/v1.1 review (Finding 3 caveat: "v1.1 collapses signals=2 and signals=3 into `medium`. My v1.0 review proposed signals=3 → `medium` and signals=2 → `low`...The v1.1 collapse is defensible — it preserves the four-tier ordinal — but it does discard one bit of information"). The distribution of `medium` rows in the landed table:

- 2/4 signals (least-complete medium): 4 rows — e.g., DeVry University-Administrative Office (FTE NULL, endowment NULL, both expenses present)
- 3/4 signals (most-complete medium): 673 rows — primarily F3 institutions where endowment is structurally NULL

These are downstream-different states. The 4-row group at 2/4 has `marketing_ratio` computed but per-FTE values NULL. The 673-row group has per-FTE values populated and `marketing_ratio` computed but `endowment_per_fte` NULL.

A downstream consumer that filters `tier='medium'` will admit both. The 4-row group is much more degraded than the 673-row group, but the tier signal does not differentiate.

**Severity:** MEDIUM (information-loss in the tier signal; not a correctness defect but a transparency-design weakness).

### Gap 6 — `endowment_value = 0` is treated as a "present" signal, conflating "underwater funds" with "doesn't have an endowment" — **MEDIUM**

Spec §3 RAW-IPF-007 documents: "underwater funds report 0, never negative." The consumable transformer (`classify_data_completeness_tier`) counts a `value is None` check only — `0.0` counts as present.

**Live evidence:** exactly 1 row has `endowment_value = 0.0` exactly: UNITID 126100 (Yosemite Community College District Office) — `report_form='F1A'`, `endowment_value=0.0`, `endowment_per_fte=NULL` (because FTE is NULL). This is a community college district office; it is highly unlikely it has an actual endowment that went underwater to 0. The 0.0 is more plausibly a placeholder filed by NCES or by the reporting institution.

The conflation is small in landed data (n=1) but the *contract* is unclear: is `endowment_value = 0` an institution-reported "we have an endowment with current market value zero" or "we don't have an endowment and reported a placeholder"? IPEDS does not natively distinguish.

**Severity:** MEDIUM (semantic ambiguity in a CDE-tagged field; affects any "endowment-poor" comparison logic).

### Gap 7 — `fiscal_year` is the only vintage signal in the consumable; `source_load_date` was dropped between base and consumable — **MEDIUM**

`base.ipeds_finance` schema includes `source_load_date date` per spec §5. `consumable.ipeds_finance_profile` schema (per spec §6 and verified DESCRIBE) does NOT include `source_load_date` — only `promoted_at`. A consumer wanting to verify "which date did this finance data get loaded" must back-join to base, which violates the gold-only-consumption pattern that the v1.1 raw-passthrough exception was justified to preserve.

`fiscal_year` is technically sufficient for vintage alignment (and it IS propagated), but `source_load_date` would let a consumer detect *when an FY23 cycle was re-loaded mid-vintage* (e.g., NCES corrects a Stanford figure in November 2024 and the bronze re-ingestor picks it up). With only `fiscal_year`, that re-load is invisible to the consumer.

**Severity:** MEDIUM (vintage observability gap; not a correctness defect).

### Gap 8 — `instruction_per_fte` outliers (small-FTE specialty institutions) land at `tier='high'` and pass all P99-percentile rules — **LOW**

The base rule BSE-IPF-017 fires only on P99 (currently $86,893; threshold < $500K — passes with margin). But individual rows with absurd values land:

| UNITID | Institution | FTE | instruction_expenses | instruction_per_fte | tier |
|---|---|---|---|---|---|
| 228635 | UT Southwestern Medical Center | 2,165 | $1.57B | **$723,521** | high |
| 445054 | Toyota Technological Institute at Chicago | 16 | $4.68M | $292,208 | high |
| 190424 | Weill Medical College of Cornell | 1,286 | $323M | $251,155 | medium |
| 229300 | UT Health Science Center at Houston | 4,486 | $1.11B | $246,597 | high |

UT Southwestern at $723K/FTE exceeds the BSE-IPF-017 anchor threshold of $500K but the *rule is on the P99*, not on individual rows — so the rule passes. The EDA explicitly accepts this as "a legitimate small-FTE specialty medical school" (§6).

A downstream consumer that uses `instruction_per_fte` as a proxy for "spending per student" — exactly what the BT-IPF-PER-FTE glossary entry frames it as — will see UT Southwestern as a 7×-the-next-most-expensive institution outlier. UT Southwestern's FTE of 2,165 is the medical-residency-program FTE, not "all students taught with this $1.57B," so the per-FTE math is technically correct but semantically misleading (the $1.57B includes substantial clinical, research, and patient-care expense that is bundled into the IPEDS "instruction" function for academic medical centers).

**Severity:** LOW (per-FTE math is correct by definition; the semantic-misuse risk is inherent to the field, not specific to this consumable; medical schools are a known long-recognized IPEDS-finance edge case).

---

## 2. Evidence Demands

For each gap, what evidence would satisfy a regulator that the gap is mitigated:

| Gap | Required evidence |
|---|---|
| **1 — tier=high decoupled from marketing_ratio** | Either (a) a new DQ rule CON-IFP-011 asserting `tier='high' AND marketing_ratio IS NULL → fail` (with a documented N=2 known-exception list for the FY2023 vintage), OR (b) a contract clause that consumers gating on `tier='high'` must independently null-check `marketing_ratio` before computing ratios, OR (c) tier-classification rework to count `marketing_ratio IS NOT NULL` as a fifth signal (rejected per v1.1 review — but that rejection rested on derivative-double-counting concerns that the zero-instruction edge case re-opens). |
| **2 — system-office marketing_ratio outliers** | A documented data-contract clause that downstream rankings on `marketing_ratio` MUST exclude institutions where `instruction_expenses = 0 OR instruction_expenses < $1M`, OR a v1.4 spec amendment adopting the EDA's recommended `~~ ' Office' OR ' System' OR 'Chancellor'` name filter at the bronze→base boundary, OR a new boolean column `is_administrative_office` in the consumable. The current state — "the EDA flagged it, the spec didn't adopt it" — is the worst of all worlds: the project knows the trap and ships into it. |
| **3 — vintage-drift unjoinability** | One of: (a) add `fiscal_year` to `consumable.career_outcomes` and add a vintage-equality clause to CON-IFP-008's SQL; (b) add a contract clause requiring downstream consumers to propagate `consumable.ipeds_finance_profile.fiscal_year` into any join result and assert it matches their own vintage; (c) document the cross-vintage join risk in a CDE-tagging artifact for the `fiscal_year` field on this consumable. Evidence required: the CON-IFP-008 rule SQL or a new CON-IFP-011 rule that surfaces a vintage-mismatch warning. |
| **4 — F3 100% drop on EADA-aura formulas** | A contract clause in `governance/data-contracts/consumable-ipeds-finance-profile.yaml` (note: this file does not yet exist in `governance/data-contracts/` per `ls`) that downstream consumers MUST gate composite calculations involving `endowment_per_fte` on `report_form != 'F3'` OR equivalently `endowment_per_fte IS NOT NULL`, AND a corresponding section in the future `raw-ingest-eada.md` spec that enforces this gate. Evidence: the data contract YAML and the EADA spec's downstream-compatibility note. |
| **5 — medium tier ambiguity** | Either (a) re-split: signals=3 → `medium`, signals=2 → `medium-low`, leaving the four-tier ordinal intact at five tiers; (b) expose a `non_null_signals_count` int column alongside `data_completeness_tier` so consumers can disambiguate when needed; (c) data-contract clause documenting the two-state-collapse and identifying the 4-row 2/4-signals subset by name as known-administrative-offices. Option (b) is cheapest. |
| **6 — endowment=0 ambiguity** | A documented CDE-tagging clause for `endowment_value` indicating "0.0 means institution-reported zero and may indicate either an underwater fund or a non-endowment-bearing institutional placeholder; consumers cannot distinguish." Or an upstream improvement to the bronze ingestor that maps a separately-imputed endowment-presence flag (the X-flag column from raw IPEDS — currently dropped per §2 Decision #8) to a new `endowment_provenance` column. The EDA already recommended the latter as a v1.4 follow-up (EDA §7.2). |
| **7 — source_load_date dropped at consumable** | Add `source_load_date` to consumable schema as an optional passthrough (cost: one column, additive change). Or document the gap explicitly in the data contract. |
| **8 — per-FTE plausibility for academic medical centers** | A documented BT-IPF-PER-FTE glossary clause that academic medical centers' instruction_per_fte values are not directly comparable to non-medical-school per-FTE values; or a per-Carnegie-class flag column (rejected at hackathon scope but documentable). |

---

## 3. Assessment — Grading the Project's Existing Controls

| Gap | Existing mitigation | Strength |
|---|---|---|
| **1 — tier=high decoupled from marketing_ratio** | None. CON-IFP-006 verifies tier classification matches the spec formula but the spec formula itself produces the gap. The BT-IPF-DATA-COMPLETENESS-TIER glossary text disambiguates the tier from CIP→SOC tiers but does NOT mention the zero-instruction edge case. | **Missing** |
| **2 — system-office marketing_ratio outliers** | EDA explicitly identified the pattern (§6, §10) and recommended a v1.4 filter; that filter was deferred. Per-form BSE-IPF-015a/b/c thresholds were calibrated to *tolerate* the existence of these outliers (so the rules don't fire on legitimate state-system data). The base zone has no rule that excludes them and the consumable has no rule that warns about them. | **Weak** (the EDA findings exist; the mitigation does not) |
| **3 — vintage-drift unjoinability** | `fiscal_year` is propagated through to consumable (verified). CON-IFP-008's SQL joins on `unitid` only and has no vintage clause. The §9 deviations table documents one prior cross-vintage operation. | **Weak** (vintage IS in the consumable; nothing enforces vintage in joins) |
| **4 — F3 100% drop on EADA-aura formulas** | `report_form` is in the consumable schema (so segmentation is *possible*). The fp-data-reviewer's bonus section explicitly noted "EADA fusion may need to segment by GASB vs FASB" but did not extend this to "and must gate on report_form for endowment composites." No data contract YAML exists yet for this consumable. | **Missing at contract layer** (the column exists; the contract doesn't) |
| **5 — medium tier ambiguity** | The fp-data-reviewer flagged this in the v1.1 second-pass review and accepted the v1.1 collapse with the caveat "if EDA shows a fat `medium` bucket, consider re-splitting in v1.2." EDA showed 25.3% of rows in `medium` (677/2,675) — fat. v1.2 did not re-split. | **Adequate-with-known-defect** (acknowledged; not mitigated) |
| **6 — endowment=0 ambiguity** | RAW-IPF-007 documents "underwater funds report 0, never negative." No consumable-zone documentation of the "0 vs missing" semantic gap. | **Weak** (raw-zone disclaimer; no consumable-zone surfacing) |
| **7 — source_load_date dropped at consumable** | None. Spec §6 omitted the field; reviewers did not flag. | **Missing** |
| **8 — per-FTE plausibility for academic medical centers** | EDA accepted UT Southwestern at $634K (FY22, now $723K FY23) as "a legitimate small-FTE specialty medical school" (§6). BSE-IPF-017 P99 < $500K passes because P99 = $86.9K. The BT-IPF-PER-FTE glossary entry does not call out academic medical centers as a known outlier class. | **Weak** (EDA accepts the rows; consumers are not warned) |

---

## 4. Recommendations — What to Add to Close Gaps

Numbered by gap, ordered by severity and bang-for-buck:

### R1 (Gap 4 — HIGH) — Author the consumable data contract YAML with EADA-fusion guidance
Create `governance/data-contracts/consumable-ipeds-finance-profile.yaml` with explicit downstream-consumer guidance:
- **Endowment composites:** any downstream metric incorporating `endowment_value` or `endowment_per_fte` MUST be computed only for rows where `report_form != 'F3'` OR `endowment_value IS NOT NULL`. Document the F3 100%-NULL invariant as a structural property, not a quality defect.
- **Marketing-ratio rankings:** any downstream metric ranking institutions by `marketing_ratio` MUST exclude rows where `instruction_expenses = 0` OR `instruction_expenses < $1,000,000` (the latter to filter administrative offices that report nominal instructional spend).
- **Vintage gating:** consumers joining `consumable.ipeds_finance_profile` to other consumables MUST propagate `fiscal_year` and assert vintage equality where the join target carries vintage; where it does not (e.g., `consumable.career_outcomes`), consumers MUST document the vintage assumption in their own spec.
- **Tier interpretation:** `tier='high'` means "all 4 raw inputs non-null" — it does NOT guarantee `marketing_ratio` is non-NULL (zero-instruction rows can land at high; see N=2 known exceptions for FY2023).

This single artifact closes Gaps 1, 2, 3, and 4 at the contract layer.

### R2 (Gap 1 — HIGH) — Add CON-IFP-011 (P1) — tier=high marketing_ratio coherence
Proposed rule:
```sql
SELECT * FROM consumable.ipeds_finance_profile
WHERE data_completeness_tier = 'high'
  AND marketing_ratio IS NULL
```
Threshold: `result_count <= 5` (currently 2; soft-pin to allow vintage drift for community colleges and online universities reporting zero instruction). Marked P1 because the underlying issue is a contract semantic, not an arithmetic invariant — but the rule surfaces drift if the count grows past the documented exceptions.

### R3 (Gap 3 — HIGH) — Add CON-IFP-012 (P0) — fiscal_year present and single-valued at consumable
Proposed rule:
```sql
SELECT CASE WHEN (SELECT COUNT(DISTINCT fiscal_year) FROM consumable.ipeds_finance_profile) = 1
            AND (SELECT COUNT(*) FROM consumable.ipeds_finance_profile WHERE fiscal_year IS NULL) = 0
            THEN 0 ELSE 1 END AS violation
```
Mirrors RAW-IPF-013 at the consumable layer. Closes the upstream-only-enforcement gap and gives downstream consumers a single inspection point for vintage assertion.

### R4 (Gap 2 — HIGH) — Adopt the EDA's `is_administrative_office` flag as a v1.4 amendment
Either as a transformer-side derivation (`institution_name ~~ 'Office'|' System'|'Chancellor'`, with an exception list), OR as a passthrough boolean from a future bronze HD-derived column. The exact mechanism is less important than the surfaced flag — a downstream UI ranking by `marketing_ratio` should be able to filter `WHERE NOT is_administrative_office` in one clause.

### R5 (Gap 5 — MEDIUM) — Expose `non_null_signals_count` as an integer column
Cheap (one column, integer, computed identically to the tier formula). Lets downstream consumers gate on `signals >= 3` if they want fewer rows than `tier IN ('high', 'medium')` would admit. No DQ rule needed — the column's values are mechanically derived from the existing 4 raw input columns.

### R6 (Gap 7 — MEDIUM) — Restore `source_load_date` in consumable schema
One additive column passthrough from base. Lets consumers detect re-loads within a vintage; preserves the gold-only-consumption pattern.

### R7 (Gap 6 — MEDIUM) — CDE-tagging clause on `endowment_value`
In the future `governance/cde-tagging/consumable-ipeds-finance-profile.md` artifact (§8 lists this as required, status TBD), document the `0.0 vs NULL` semantic ambiguity for `endowment_value` and recommend the v1.4 `endowment_value_provenance` column the EDA already proposed (§7.2).

### R8 (Gap 8 — LOW) — Glossary clause on academic medical centers
Append to BT-IPF-PER-FTE: "Academic medical centers (e.g., UT Southwestern, Weill Cornell Medicine, UCSF) report instructional spend that bundles clinical, research, and patient-care expenses into the IPEDS 'instruction' function. Per-FTE values for these institutions are not directly comparable to non-medical-school institutions and should be either segmented or excluded from generalized 'per-student spending' comparisons."

---

## 5. Cross-zone semantic-drift findings (negative results — controls hold)

The user's prompt asked specifically about three cross-zone semantic-drift questions. I tested each and found NO drift:

| Question | Finding |
|---|---|
| Per-FTE arithmetic identity holds? | YES — verified `instruction_per_fte` IS NULL when `total_fte_enrollment` IS NULL (0 violations across 2,675 rows); same for instruction_expenses. CON-IFP-007 (marketing_ratio = inst_supp_per_fte / inst_per_fte within 0.001) is a P0 rule that holds by construction. |
| Record_id namespace separation between base and consumable? | YES — all 2,675 record_ids in consumable have prefix `ifp-`; base record_ids have prefix `ipf-` (per spec §5/§6 and `compute_grain_id` calls). No collision possible. Stanford's record_ids: base = `ipf-267f20f48b4b772f`, consumable = `ifp-267f20f48b4b772f`. The 12-char hash suffix is identical because the grain (`unitid`) is identical, but the prefix discriminates the zone. |
| Tier classification holds against the spec formula? | YES — CON-IFP-006 reconstructs the formula in SQL and the rule passes 2,675/2,675. I independently re-ran the formula in Python against the live data: 0 mismatches. |

These three are cleanly mitigated by existing controls. The eight gaps above are all *additional* surfaces the existing rules don't reach.

---

## 6. Hostile-input scenarios from the prompt — re-tested at full strength

The user's prompt named three hostile-input scenarios. Test results:

### 6.1 EADA fusion assumes `endowment_per_fte` non-NULL → F3 silent drop
**Confirmed at scale.** 213 / 213 F3-with-CO-match institutions would silently drop. See Gap 4 above.

### 6.2 UI ranks by `marketing_ratio` ascending → 31 zero-instruction rows produce NULL marketing_ratio
**Confirmed.** DuckDB's default sort behavior:
- `ORDER BY marketing_ratio ASC` → NULLs sort LAST (DuckDB default), so zero-instruction rows appear at the BOTTOM of the ascending sort. UI shows them as "least marketing-heavy" only if NULLs are skipped.
- `ORDER BY marketing_ratio DESC` → NULLs sort LAST again, so zero-instruction rows do NOT appear at the top of "most marketing-heavy" (good — they're filtered automatically).
- BUT: the 16 institutions with `marketing_ratio = 0.0` (positive instruction, zero institutional support — University of Florida-Online, online-only schools, theological micro-colleges, regional hospital training programs) DO sort to the top of the ascending sort. A consumer presenting "schools that spend least on admin per dollar of instruction" would see "University of Florida-Online" as the #1 — a meaningful but possibly misleading interpretation (the school has institutional support reported elsewhere in the parent FY entity).

The risk is genuine. Mitigation belongs in the data contract (R1).

### 6.3 "Best ROI" comparisons misuse `instruction_per_fte` as a quality signal
**Confirmed for academic medical centers.** UT Southwestern's $723K/FTE is correct arithmetic on a misleading numerator (the "instruction" line bundles clinical & research expenses for medical schools). 5 rows exceed $200K/FTE, all academic medical or specialty institutions. The BSE-IPF-017 P99 < $500K rule passes because the count is small enough not to move the percentile. See Gap 8 and R8.

---

## 7. The `data_completeness_tier` transparency-vs-filtering question

Per the user prompt and the standing project preference (memory entry: "data_completeness_tier is for transparency, not substitution"), I checked whether any path treats `medium`/`low` rows as "exclude":

- The transformer (`src/gold/ipeds_finance_profile.py`): no filtering — all rows promoted regardless of tier.
- The DQ rules (`governance/dq-rules/consumable-ipeds-finance-profile.json`): none filter by tier; CON-IFP-009 sets a *distribution* invariant (`high >= 70%`) but doesn't drop rows.
- The data contract YAML: does not yet exist.

**Contract requirement to add (closes Gap 4 + the standing preference):** the future data contract MUST explicitly state "Consumers SHOULD use `data_completeness_tier` as a transparency signal (e.g., display alongside the institution's profile). Consumers MUST NOT silently exclude `medium`/`low`/`insufficient` rows from analytical results without surfacing the exclusion to the end user." This locks the standing preference into a regulator-readable artifact.

---

## 8. Final assessments

| Question | Verdict | Evidence |
|---|---|---|
| Are the 11 consumable DQ rules sufficient for the consumable contract surface? | **No — eight surfaces are uncovered (4 HIGH, 3 MEDIUM, 1 LOW)** | Live queries against the landed parquet show 2 known tier-vs-marketing_ratio decoupling rows, 25 administrative-office outliers in the top-25 marketing_ratio, 213 F3-CO-matched rows that would drop on EADA endow composites, no fiscal_year on the join target |
| Is the v1.2 `data_completeness_tier` formula correct? | **Yes — but the consumer-facing semantics are under-documented** | CON-IFP-006 verifies the formula; the formula's edge cases (zero-instruction admin offices landing at `high`, F3 capped at `medium`) are partially documented in glossary, partially not |
| Are the existing thresholds well-grounded in EDA evidence? | **Yes — with documented vintage drift accommodation** | CON-IFP-008 was correctly recalibrated from spec/EDA's 90% to 88% (FY2023 measured 88.71%); CON-IFP-009 preserved at 70% (FY2023 measured 74.7%); rule rationale text accurately documents the recalibration |
| Are downstream consumers protected from silent failure? | **No — the consumable data contract YAML has not been authored** | `ls governance/data-contracts/` shows no `consumable-ipeds-finance-profile.yaml` |
| Is vintage drift safely handled across consumable joins? | **No — `consumable.career_outcomes` carries no `fiscal_year` and CON-IFP-008 has no vintage clause** | Verified via DESCRIBE; the §9 deviations table records that re-ingestion has happened |
| Cross-zone arithmetic invariants hold? | **Yes** | CON-IFP-007 (marketing_ratio identity) holds 0 violations; record_id namespace separation holds; FTE-NULL-cascade holds 0 violations |

---

## 9. CLEAR / BLOCKED for governance review

**CLEAR for consumable-zone governance review** — none of the eight gaps rises to a P0 BLOCKING level for the consumable as it stands today. All eight are *contract-layer* and *consumer-documentation* gaps that can be closed without re-running the pipeline.

However, **SOFT-BLOCKED for the downstream `raw-ingest-eada.md` spec** — Gaps 1, 2, 3, and 4 must be closed at the data-contract layer before EADA fusion can safely consume `consumable.ipeds_finance_profile`. The recommended close-out order:

1. **Author** `governance/data-contracts/consumable-ipeds-finance-profile.yaml` per R1 — a single artifact closes Gaps 1, 2, 3, 4 at the contract layer.
2. **Add** CON-IFP-011 (P1, R2) and CON-IFP-012 (P0, R3) to `governance/dq-rules/consumable-ipeds-finance-profile.json`.
3. **Spec amendment v1.4**: adopt R4 (administrative-office flag) and R5 (`non_null_signals_count` column) as additive consumable schema fields.
4. **Glossary update** (R7, R8): clarify endowment=0 and per-FTE for academic medical centers.

None of these require a re-build of the consumable; they are additive contract and rule changes. R6 (restore `source_load_date`) requires a re-promote and is the only schema-altering change among the recommendations — defer to v1.4 if EADA fusion does not need it.

**No HARD blocker requiring a v1.4 spec change to land before the EADA spec begins.** The EADA spec can proceed in parallel provided its own §6/§7 explicitly cite which Gap-1/2/3/4 mitigation it relies on. If the EADA spec lands without the data contract YAML, the F3 100%-drop scenario (Gap 4) becomes a real defect at EADA-fusion time.

---

## 10. Audit reproducibility

Every claim in this audit is reproducible by:

```bash
# Live consumable data view
uv run python -c "
import duckdb
con = duckdb.connect()
con.execute(\"CREATE VIEW ifp AS SELECT * FROM 'data/gold/iceberg_warehouse/consumable/ipeds_finance_profile/data/*.parquet'\")
con.execute(\"CREATE VIEW co  AS SELECT * FROM 'data/gold/iceberg_warehouse/consumable/career_outcomes/data/*.parquet'\")

# Gap 1 — tier=high decoupled from marketing_ratio
print(con.execute(\"SELECT unitid, institution_name, instruction_expenses, marketing_ratio FROM ifp WHERE data_completeness_tier='high' AND marketing_ratio IS NULL\").fetchall())

# Gap 2 — top 25 marketing_ratio outliers
print(con.execute(\"SELECT unitid, institution_name, instruction_expenses, institutional_support_expenses, marketing_ratio FROM ifp WHERE marketing_ratio IS NOT NULL ORDER BY marketing_ratio DESC LIMIT 25\").fetchall())

# Gap 3 — career_outcomes has no fiscal_year column
print([r for r in con.execute('DESCRIBE co').fetchall() if 'year' in r[0].lower()])

# Gap 4 — F3 with CO-match would drop on endow composite
print(con.execute(\"SELECT ifp.report_form, COUNT(DISTINCT ifp.unitid) match_unitids, COUNT(DISTINCT CASE WHEN ifp.endowment_per_fte IS NOT NULL THEN ifp.unitid END) with_endow FROM ifp WHERE EXISTS (SELECT 1 FROM co WHERE co.unitid = ifp.unitid) GROUP BY ifp.report_form\").fetchall())
"
```

**Auditor sign-off:** the consumable-zone IPEDS Finance pipeline is internally correct (the v1.2 tier rework, the v1.3 column lock-down, the cross-vintage threshold recalibration are all valid and well-reasoned). The eight gaps surfaced in this audit are *consumer-facing contract* gaps, not pipeline-internal defects. They are mitigatable with one data contract YAML, two new DQ rules, two additive schema columns, and three glossary clauses. None blocks the consumable. Four of them block the future EADA fusion if not closed first.

The pattern is consistent with the bronze adversarial audit: the implementation is competent; the surface where it interfaces with future consumers is under-specified. A regulator would accept the eight findings as "known-and-named risks awaiting documented mitigation," provided the mitigations land before the EADA spec executes.
