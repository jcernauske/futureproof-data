# EDA Report: bronze.ipeds_finance — `endowment_value_flag` (v1.4 narrow)

**Spec:** `docs/specs/ipeds-finance-v1.4.md` (DRAFT, v1.1 amendment)
**Predecessor EDA:** `governance/eda/raw-ingest-ipeds-finance-eda.md` (v1.3, FY2022)
**Source table:** `bronze.ipeds_finance` (Iceberg)
**Snapshot:** `8612278722865929234`
**Cycle:** FY2023 (academic year 2022-23)
**Date:** 2026-05-01
**Agent:** `@bs:data-analyst`
**Record Count:** 2,675
**New column under analysis:** `endowment_value_flag` (string, nullable)

This is a **narrow-scope refresh** in service of the v1.4 spec's Items 1 and BSE-IPF-019/RAW-IPF-015 calibration. The full v1.3 EDA pass (column-by-column distributions, marketing_ratio outliers, per-FTE preview, etc.) is not re-run here. Refer to `governance/eda/raw-ingest-ipeds-finance-eda.md` for the v1.3 baseline; the v1.3 numbers are quoted where they are load-bearing for drift analysis.

---

## §1 Scope

This report covers exactly the v1.4 EDA Requirements named in the spec's §4 and §6 (BLOCKING for base + consumable):

1. **Value-domain confirmation** of `endowment_value_flag` against the **live FY2023 IPEDS Finance dictionary** (authoritative per v1.1 §3 amendment), with a verbatim dictionary excerpt.
2. **Prevalence by form** (F1A vs F2), characterized as drift against the v1.3 FY2022 baseline; the FY2023 9.77% F1A / 18.05% F2 prevalence figures are *outside* the spec's pre-implementation 20-40% band assumption and constitute a SIGNIFICANT escalation. This report tests three drift hypotheses (NCES methodology shift / sample shift / reporting discipline shift) and recommends a concrete band for `BSE-IPF-019`.
3. **Cross-tab integrity** with `report_form` and `endowment_value` NULL pattern (F3 NULL invariant; F1A/F2 flag-without-value invariant; imputed-zero / value-suppressed pattern).

Out of scope (deferred to the full v1.3 EDA, no re-run): distribution shapes for the four target dollar/FTE columns, marketing_ratio outliers, per-FTE thresholds, career-outcomes overlap, form-mix religious/secular split. Those are unchanged from v1.3 by design — only the new flag column is touched.

---

## §2 Bronze Snapshot

| Property | Value |
|---|---|
| Iceberg table | `bronze.ipeds_finance` |
| Snapshot ID | `8612278722865929234` |
| Snapshot timestamp | 2026-05-01 (timestamp_ms 1777689072044) |
| Record count | **2,675** |
| Field count | 13 (12 v1.3 fields + new `endowment_value_flag`) |
| Cycle | FY2023 (single-vintage; `fiscal_year = 2023` for all rows) |
| Form mix | F1A=819, F2=1,579, F3=277 |

For comparison, the v1.3 FY2022 snapshot (`982081695100705470`) landed 2,683 rows / F1A=803, F2=1,593, F3=287. The 8-row swing across forms (+16 F1A, -14 F2, -10 F3) is normal cycle-over-cycle reclassification at NCES (institutions changing accounting standard, mergers, closures); it is not a sample-construction anomaly.

The full schema is unchanged from v1.3 with the single `endowment_value_flag` (string, nullable) appended at field_id 13. All v1.3 columns retain their types and nullability.

---

## §3 Value-Domain Confirmation (AUTHORITATIVE: live FY2023 IPEDS dictionary)

### 3.1 Dictionary excerpt — VERBATIM (per v1.1 §3 amendment requirement)

The IPEDS Finance FY2023 dictionary publishes a single shared lookup for **all** `X*` imputation flag columns (including `XF1H02` for F1A endowment and `XF2H02` for F2 endowment). The lookup is the `imputation values` worksheet inside both per-form dictionary files.

**Source — F1A:** `https://nces.ed.gov/ipeds/datacenter/data/F2223_F1A_Dict.zip` → `f2223_f1a.xlsx` → sheet **`imputation values`**

**Source — F2:** `https://nces.ed.gov/ipeds/datacenter/data/F2223_F2_Dict.zip` → `f2223_f2.xlsx` → sheet **`imputation values`**

Verbatim contents (identical across both per-form dictionaries):

```
Code values for item imputation variables Xvarname

CodeValue | ValueLabel
A         | Not applicable
B         | Institution left item blank
C         | Analyst corrected reported value
D         | Do not know
G         | Data generated from other data values
H         | Value not derived - data not usable
J         | Logical imputation
K         | Ratio adjustment
L         | Imputed using the Group Median procedure
N         | Imputed using Nearest Neighbor procedure
P         | Imputed using Carry Forward procedure
R         | Reported
Z         | Implied zero;
```

**13 codes total**, with the trailing semicolon present in `Z`'s label as published. The dictionary's `varlist` sheet for F1H02 and F2H02 separately confirms `imputationvar = XF1H02` and `imputationvar = XF2H02` respectively, and both `varTitle = "Value of endowment assets at the end of the fiscal year"`.

**Cross-check against FY2022:** the FY2022 F1A dictionary (`F2122_F1A_Dict.zip` → `f2122_f1a.xlsx` → `imputation values`) contains the **identical 13-code lookup** — the dictionary semantics are unchanged across cycles. The cycle-to-cycle stability matters for the §4 hypothesis test below.

### 3.2 Empirical scan — landed FY2023 codes by form

```
flag | report_form | n
-----+-------------+------
A    | F1A         |   80
N    | F1A         |    1
P    | F1A         |    1
R    | F1A         |  737
A    | F2          |  285
P    | F2          |    1
R    | F2          | 1293
NULL | F3          |  277
```

Landed observations: `{R, A, P, N}` on F1A; `{R, A, P}` on F2; `NULL` on every F3 row. **All four observed non-NULL codes are inside the dictionary's 13-code set; no undocumented code is observed.** No `Z` is observed in this cycle (zero-imputation is rare for endowment), no `B/C/D/G/H/J/K/L` is observed.

### 3.3 Verdict — and a load-bearing semantic correction

**Empirical scan PASS:** every observed code is in the dictionary's allowed set; no undocumented code exists in the data; no `Significant` escalation is needed under v1.1 §3's "no silent allowed-set extension" rule on the empirical-scan side.

**However:** the v1.3 EDA §7 narrative documented the meaning of the `A` code as `"NCES analytical / model-imputed (often imputed using a prior-year ratio applied to current-year revenue, or a mean-of-similar-institutions imputation)"`. That description has been **inherited verbatim** into v1.4 spec §3 (allowed-set introduction), §4 (RAW-IPF-015 description), §6 (consumer interpretation guidance for `endowment_value_provenance`), and the proposed `BT-IPF-ENDOWMENT-PROVENANCE` glossary term. **The dictionary semantic is different.** The authoritative FY2023 (and FY2022) dictionary defines:

| Code | v1.3 EDA / v1.4 spec narrative | Authoritative dictionary |
|---|---|---|
| `R` | Reported by institution | Reported |
| `A` | NCES analytical / model-imputed | **Not applicable** |
| `P` | Prior-year carryforward | Imputed using Carry Forward procedure |
| `Z` | Imputed using zero | Implied zero |
| `N` | Not applicable | **Imputed using Nearest Neighbor procedure** |

Notably, `A` and `N` are **swapped** between the v1.4 spec narrative and the dictionary. The eight other dictionary codes (`B/C/D/G/H/J/K/L`) are not mentioned in the spec at all — RAW-IPF-015's allowed set `{R, A, P, Z, N}` is a **strict subset** of the dictionary's 13-code domain.

The empirical evidence in §5 below is fully consistent with the **dictionary** semantic (every `A`-flagged row has `endowment_value IS NULL`, exactly as `"Not applicable"` would predict — the institution does not have an endowment to report). It is **inconsistent** with the v1.3 narrative (`A` cannot mean "model-imputed" if it is exclusively coupled to NULL values).

This is a **classification escalation**, not a value-domain escalation. Under the v1.1 §3 amendment's rule, the trigger for a `Significant` escalation is "any code observed in FY2023 data that is not in the dictionary excerpt OR any code in the dictionary excerpt that is not in `{R, A, P, Z, N}` requires explicit spec-author sign-off". The empirical observations satisfy the dictionary side; the dictionary's 13 documented codes vs spec's 5 allowed codes does **not** strictly satisfy the second clause as written ("not in `{R, A, P, Z, N}`" applies in the direction of the rule's allowed set, and the unobserved 8 codes are not currently surfacing). But the spirit of the v1.1 amendment ("dictionary is authoritative; do not silently extend the allowed set") points **toward** an escalation here — the spec-narrative-vs-dictionary mismatch on code semantics is a real spec-amendment item that should not land silently in `consumable.ipeds_finance_profile` or in `BT-IPF-ENDOWMENT-PROVENANCE`.

**Verdict:**

- **Allowed-set domain (RAW-IPF-015):** `{R, A, P, Z, N}` is **CONFIRMED** to cover 100% of empirically-observed FY2023 codes. The set is a strict subset of the 13-code dictionary domain; recommend documenting that subset relationship explicitly (see §6 Recommendations).
- **Code semantics (v1.4 spec §3 / §6 / glossary):** **REJECTED**. The narrative descriptions for `A` and `N` are inverted relative to the dictionary; spec authors must amend before consumable lands. The `A` flag in landed data is **NCES "Not applicable" — institution has no endowment to report**, NOT "model-imputed". This changes the downstream interpretation guidance in §6 of the spec materially (see §6 Recommendations).

---

## §4 Prevalence by Form (BSE-IPF-019 calibration)

### 4.1 Measured FY2023 prevalence — denominator = rows with `endowment_value_flag IS NOT NULL`

```
form | n_nonnull |  R  |  A  | P | N | pct_R  | pct_A  | pct_P  | pct_N
-----+-----------+-----+-----+---+---+--------+--------+--------+--------
F1A  |     819   | 737 |  80 | 1 | 1 | 89.99% |  9.77% | 0.122% | 0.122%
F2   |    1579   |1293 | 285 | 1 | 0 | 81.89% | 18.05% | 0.063% | 0.000%
```

For both forms, the non-null-flag denominator equals the total form-row count (every F1A row and every F2 row carries a flag; the NOT-NULL rate is 100% on each form, NULL is exclusively on F3 — see §5).

**FY2023 measured `A`-rate:**

- F1A: **9.77%** (80 / 819)
- F2: **18.05%** (285 / 1,579)

Both fall **outside** the v1.4 spec §2 Decision F's 20-40% band that `BSE-IPF-019` was dimensioned against. F1A is ~10pp below the lower bound; F2 is ~2pp below.

### 4.2 v1.3 FY2022 baseline — re-stated on the same denominator

The v1.3 EDA reported FY2022 imputation prevalence numbers at **31.10% F1A / 25.31% F2**, which are quoted in v1.4 §2 Decision F and §3 as the baselines BSE-IPF-019's band was calibrated against. **Those numbers were measured on the FULL pre-HD-filter FY2022 source CSVs** (1,936 F1A source rows; 1,782 F2 source rows — quoted in v1.3 EDA §7), not on the LANDED bronze table (which after HD-filtering kept 803 F1A and 1,593 F2 rows).

This is an apples-to-oranges comparison. The v1.3 LANDED bronze had `endowment_value` NULL counts of:

| Form | v1.3 landed rows | v1.3 NULL count | v1.3 NULL rate (landed) |
|---|---|---|---|
| F1A | 803 | 77 | **9.59%** (per v1.3 EDA §3.3 table) |
| F2 | 1,593 | 286 | **17.95%** (per v1.3 EDA §3.3 table) |

§5 below establishes that in the FY2023 landed data, the `A` flag is **exclusively** coupled to `endowment_value IS NULL` (every `A`-flagged row has a NULL endowment value, and every endowment-NULL row on F1A/F2 carries the `A` flag). Because the v1.3 ingestor stripped the flag column, the FY2022 LANDED `A`-rate cannot be measured directly, but the dictionary semantic of `A = "Not applicable"` predicts the same coupling — so the FY2022 LANDED `A`-rate would be 9.59% F1A / 17.95% F2 under the same coupling.

**Apples-to-apples drift on landed bronze, FY2022 → FY2023:**

| Form | FY2022 LANDED `A`-rate (inferred) | FY2023 LANDED `A`-rate (measured) | Δ |
|---|---|---|---|
| F1A | 9.59% (77 / 803) | 9.77% (80 / 819) | **+0.18 pp** |
| F2 | 17.95% (286 / 1,593) | 18.05% (285 / 1,579) | **+0.10 pp** |

**Drift is noise-level.** The 21pp F1A drop and 7pp F2 drop the raw implementer flagged are an artifact of comparing FY2023 LANDED rates against FY2022 PRE-HD source-CSV rates — two different denominators by an order of magnitude (sub-baccalaureate institutions, which are dominantly `A` because community-college branches don't have endowments, are filtered out of the LANDED data by the `ICLEVEL=1 AND HLOFFER>=5` HD-filter).

### 4.3 Hypothesis tests (per the spec's Claude Code Prompt requirement)

**Hypothesis A — NCES methodology shift between FY2022 and FY2023.**
TEST: compare the dictionary's `imputation values` lookup across cycles.
RESULT: **NOT SUPPORTED.** The FY2022 and FY2023 dictionaries publish the **identical 13-code set with identical labels** (verified in §3.1). No methodology shift is documented.

**Hypothesis B — sample shift (fewer F1A/F2 institutions filed in FY2023).**
TEST: compare landed row counts by form.
RESULT: **NOT SUPPORTED.** Landed F1A: 803 (FY2022) → 819 (FY2023), +16 rows. Landed F2: 1,593 → 1,579, -14 rows. Net change is well within normal cycle drift; the F1A row count actually *grew*. Sample shift cannot explain a putative 21pp drop on F1A.

**Hypothesis C — reporting discipline shift (more institutions reported on time, so fewer needed `A`).**
TEST: compare `R` count change against `A` count change.
RESULT: **NOT SUPPORTED AS A DRIFT EXPLANATION** because the underlying drift is itself spurious. Under the inferred FY2022 LANDED measurements: F1A (R=726, A=77) → FY2023 (R=737, A=80); F2 (R=1,307, A=286) → FY2023 (R=1,293, A=285). Both R and A are essentially flat on landed.

**Conclusive finding:** the apparent "21pp F1A drop and 7pp F2 drop" is **not a real cycle-over-cycle drift**. It is a **denominator artifact** caused by the v1.3 EDA §7 measurement being computed on the FULL pre-HD-filter FY2022 source CSV (where many sub-baccalaureate institutions push the `A`-rate up because they have no endowment fund), while the FY2023 measurement is computed on the LANDED post-HD-filter universe (where 4-year-bachelor's-and-above institutions dominate and most have an endowment). The drift is **not structural** in any meaningful sense — neither methodology, nor sample, nor reporting discipline has shifted.

### 4.4 Recommended `BSE-IPF-019` band

The 20-40% band the spec dimensioned `BSE-IPF-019` against was computed from the wrong baseline. The **correct steady-state baseline on the LANDED bronze surface** that base + consumable inherits from is:

- F1A: **~9-10%** `A`-rate
- F2: **~17-18%** `A`-rate

These are the values the rule should be calibrated against. A wide-but-not-too-wide band is appropriate per §2 Decision F's logic ("absorb cycle drift, catch structural break"). Three options for the spec authors to choose from, in increasing order of permissiveness:

| Option | F1A band | F2 band | Pros | Cons |
|---|---|---|---|---|
| **Option 1 (per-form, tight)** | 5-15% | 12-25% | Tightly calibrated to inferred FY2022 + measured FY2023 baselines (+/- ~5pp on each side); will fire on a real structural break. | Per-form rule is two rules (or a single rule with a per-form WHERE clause). Slightly more complex. |
| **Option 2 (per-form, wider)** | 5-25% | 10-30% | Doubles the cushion; insulates against an uncharacteristic single-cycle blip. | Less sensitive to a slow structural drift. |
| **Option 3 (table-wide)** | combined 8-22% across both forms | (single rule across F1A∪F2) | Single rule. | Conflates F1A (~10%) and F2 (~18%) baselines; band must be wide enough to admit both, which makes the band so loose it loses signal. **Not recommended.** |

**Headline recommendation: Option 1 (per-form, tight: F1A 5-15%, F2 12-25%).** This is the EDA-evidence-driven band; it sits ~5pp on each side of the measured baseline (9.77% / 18.05%), tight enough to fire on a real shift (NCES dictionary change, large reporting-discipline change, sample composition change) but wide enough to absorb noise. The per-form split mirrors the existing per-form pattern in the spec's BSE-IPF rules (e.g., F3-NULL-cascade behavior, BSE-IPF-013 form-aware semantics) and preserves fail-traceability.

If the spec authors prefer table-wide simplicity, **Option 2 in a per-form variant** is the second-best choice: per-form (F1A 5-25%, F2 10-30%) trades calibration tightness for resilience against unusual single-cycle fluctuations.

**Reject:** the original 20-40% band. F1A would fire constantly (9.77% measured) and F2 would fire near-constantly (18.05% measured, at the edge of the 20% lower bound). The 20-40% band would hide a real structural break by being miscalibrated to baseline.

### 4.5 Note on the `R / A / P / N` distribution shape

Beyond the `A`-rate, the FY2023 distribution is dominated by `R` (Reported) on both forms (89.99% F1A / 81.89% F2), with `P` (Carry Forward — NCES carries the prior cycle's value) and `N` (Nearest Neighbor — NCES imputes from a similar institution) collectively at well under 0.2% on both forms. This is a meaningful signal for downstream consumers: the **vast majority of non-NULL endowment values in `consumable.ipeds_finance_profile` are institution-reported, with NCES imputation-with-value affecting at most 3 rows in the entire dataset**. The interpretation guidance in v1.4 §6 ("longitudinal consumers should filter to `R`-provenance") is therefore *less* impactful than it sounds, because the non-`R` non-`A` codes that DO carry a value (`P`, `N`, plus theoretically `G/J/K/L/Z`) are negligible in count. The much larger signal is the `A` flag's coupling to NULL — see §5 below.

---

## §5 Cross-Tab Integrity

Three invariants from the v1.4 spec §4 EDA Requirements item 3.

### 5.1 F3 NULL invariant — PASS

The structural invariant is: **every F3 row has both `endowment_value` IS NULL and `endowment_value_flag` IS NULL** (because F3 has no `F3H` family per v1.3 §3 — F3 institutions don't report endowment).

| Metric | Count |
|---|---|
| F3 rows | 277 |
| F3 rows with `endowment_value_flag IS NULL` | 277 |
| F3 rows with `endowment_value IS NULL` | 277 |

**Result: 277 / 277 = 100%** on both columns. Invariant holds exactly. The raw implementer's spot check is reproduced.

### 5.2 F1A/F2 flag-without-value invariant — PASS

The invariant is: **on F1A and F2, no row should have `endowment_value IS NOT NULL AND endowment_value_flag IS NULL`** (a flag should accompany every reported endowment value).

| Form | Rows | `value NOT NULL AND flag NULL` |
|---|---|---|
| F1A | 819 | **0** |
| F2 | 1,579 | **0** |

**Result: 0 violations**. Invariant holds.

A stronger invariant also holds empirically: **on F1A and F2, no row has `flag IS NULL` at all** (every F1A and F2 row carries a flag, regardless of value-nullness). This is the bronze ingestor's COALESCE-into-form-union behavior working correctly.

### 5.3 The `A`-flag-vs-value coupling — load-bearing finding

The cross-tab below is the **headline empirical finding** of this EDA pass.

```
form |  flag  |   n   | endowment_value IS NULL | endowment_value IS NOT NULL | min  | max
-----+--------+-------+-------------------------+-----------------------------+------+-----------
F1A  |   A    |   80  |          80             |             0               |  -   |     -
F1A  |   N    |    1  |           0             |             1               |  29.97M  |  29.97M
F1A  |   P    |    1  |           0             |             1               |   7.06M  |   7.06M
F1A  |   R    |  737  |           0             |           737               |   0      |  43.88B
F2   |   A    |  285  |         285             |             0               |  -   |     -
F2   |   P    |    1  |           0             |             1               |   5.99M  |   5.99M
F2   |   R    | 1293  |           0             |          1293               |   148    |  50.75B
```

**Critical finding: every single `A`-flagged row has `endowment_value IS NULL`, and every endowment-NULL row on F1A/F2 carries the `A` flag.** The coupling is exact and bidirectional on both forms.

This is fully consistent with the dictionary's `A = "Not applicable"` semantic — these are institutions that have no endowment fund to report, so both the flag (saying "not applicable") and the value (no number to publish) are aligned. It is **inconsistent** with the v1.3 / v1.4-spec narrative that `A` means "NCES analytical / model-imputed", because under that narrative the `A`-flagged rows should carry an imputed positive value rather than a NULL.

The "imputed-zero or imputed-with-suppression cases" the spec asked to count (`endowment_value IS NULL AND endowment_value_flag = 'A'`) is therefore **80 on F1A and 285 on F2** — but they are not "imputed-zero" cases in the sense of NCES having computed a value and suppressed it. They are **`"Not applicable"` cases** where the institution does not maintain an endowment, and NCES has flagged the row accordingly.

The 80 F1A `A`-flagged rows divide approximately as:

- **10 of 80** have `instruction_expenses = 0 OR NULL` and **14 of 80** have `total_fte_enrollment NULL or 0` — these are the system-office / central-office signal (the v1.4 spec's Item 2 cluster). System offices have no endowment because they have no instructional mission.
- **41 of 80** are 4-year teaching institutions with `instruction_expenses > $10M AND total_fte_enrollment > 1,000` — community colleges (e.g., Arapahoe Community College, Cypress College, Glendale Community College, Henry Ford College, Highline College), tribal colleges (e.g., Haskell Indian Nations University, Fond du Lac Tribal), state-system branch campuses (e.g., Kent State at Ashtabula / East Liverpool / Geauga, Ana G. Mendez branches), and full-name regional 4-year publics that don't maintain an institution-level endowment fund (Alabama A&M, Georgia Gwinnett College, Colorado State University Global). These are real teaching institutions with real instruction and real students, but no separately-reported endowment fund — typically because their endowment is held by a state-system foundation or a regional foundation reported on F1B (which this spec correctly does not pull) rather than at the institution level.
- The remainder are smaller specialized institutions (medical schools, professional programs, and nursing schools whose endowment is held at the parent system level).

The 285 F2 `A`-flagged rows are dominantly **theological seminaries, micro-religious institutions, Yeshiva-tradition institutions (Bais Medrash, Mesivta, Beth Rivkah-style), acupuncture / oriental-medicine / integrative-medicine schools, and small specialty graduate institutions** — institutions that genuinely operate without an endowment fund.

**This finding has consequences for the v1.4 consumable interpretation guidance** (§6 Recommendations).

---

## §6 Recommendations

The recommendations are ordered by criticality. Recommendation 1 is the headline; recommendations 2-3 are calibration; recommendations 4-6 are spec-narrative corrections that follow from the dictionary read in §3.

### 6.1 [HEADLINE] `BSE-IPF-019` band: replace 20-40% with **per-form 5-15% F1A / 12-25% F2** (Option 1 from §4.4)

**Why:** the 20-40% band was calibrated against the wrong baseline (v1.3 EDA's pre-HD-filter source-CSV measurement, not the LANDED-bronze measurement that base inherits from). The correct steady-state baseline is 9.77% F1A / 18.05% F2 on the LANDED bronze surface. A 5-15% / 12-25% per-form band gives ~5pp cushion on each side of measured baseline, fires on a real structural shift, absorbs cycle noise. The drift is NOT structural — neither methodology, nor sample, nor reporting discipline has shifted between FY2022 and FY2023. The apparent "21pp drop / 7pp drop" the raw implementer's ad-hoc check measured is a denominator artifact, not a real signal.

**Acceptable alternative:** per-form 5-25% / 10-30% (Option 2 from §4.4) for spec authors who prefer extra cushion against single-cycle fluctuation. Reject the 20-40% original band; reject any table-wide single-band variant (Option 3) because it conflates two materially different baselines.

### 6.2 `RAW-IPF-015` allowed set: keep `{R, A, P, Z, N}` AND document the dictionary subset relationship

**Why:** the spec's allowed set is a strict subset of the dictionary's full 13-code set `{A, B, C, D, G, H, J, K, L, N, P, R, Z}`. Empirically only 4 codes appear in FY2023 landed data (`R, A, P, N`); the other 9 are unobserved but **dictionary-legitimate** (any future cycle could surface a `B`/`C`/`D`/`G`/`H`/`J`/`K`/`L` row, especially `G` "Data generated from other data values" and `H` "Value not derived - data not usable" which are plausible in an irregular cycle).

**Action:** keep `{R, A, P, Z, N}` as the rule's allowed set (current empirical observations are 100% inside it), but add to the rule's `notes` field a one-line documentation that the dictionary publishes 13 codes total and the rule's narrow allowed set is the empirically-observed subset. If a future cycle surfaces any of the 8 currently-unobserved codes, the rule will fire — at that point, treat the fire as a `Significant` escalation per the v1.1 §3 amendment rule rather than auto-extending. This preserves the v1.1 amendment's intent while giving downstream operators a clear breadcrumb.

### 6.3 Spec narrative correction (§3, §4, §6, glossary): `A` and `N` are inverted in v1.4 spec

**Why:** the dictionary defines `A = "Not applicable"` and `N = "Imputed using Nearest Neighbor procedure"`; the v1.4 spec inherited the v1.3 EDA §7 narrative which inverted both. The empirical evidence (every `A`-flagged row has `endowment_value IS NULL`) is fully consistent with the dictionary semantic and inconsistent with the spec narrative.

**Action — load-bearing changes the spec authors should make before consumable lands:**

| Spec location | Current text (paraphrased) | Corrected text |
|---|---|---|
| §3 (allowed-set narrative) | "A = NCES analytical / model-imputed (the 25-31% prevalence target)" | "A = Not applicable (institution has no endowment to report; coupled to `endowment_value IS NULL`)" |
| §4 RAW-IPF-015 description | "A = NCES analytical / model-imputed" | "A = Not applicable" |
| §6 `endowment_value_provenance` field doc | "`A` = NCES analytical / model-imputed (~25-31% prevalence per v1.3 EDA — not the same provenance as a Reported value)" | "`A` = Not applicable (institution does not maintain an endowment fund; ~10% F1A / ~18% F2 of landed rows. Coupled to `endowment_value IS NULL`. Distinct provenance from Reported, but for reasons of structural absence, not model imputation.)" |
| §6 longitudinal-filter guidance | "consumers running longitudinal endowment analyses should filter to `endowment_value_provenance = 'R'` to avoid mixing institution-reported with model-imputed values" | "consumers running endowment analyses should filter to `endowment_value_provenance = 'R'` to focus on institutions that report an endowment value. Note that filtering to `R` is essentially equivalent to filtering to `endowment_value IS NOT NULL` because the `A` flag is exclusively coupled to NULL values (institutions with no endowment to report). NCES-imputed values that DO carry a number (`P`, `N`, plus theoretically `G/J/K/L/Z`) are negligible in count (~3 rows total in FY2023)." |
| §6 BT-IPF-ENDOWMENT-PROVENANCE glossary | "A = analytical / model-imputed using prior-year ratio scaled by market-return factor; P = prior-year carryforward; Z = imputed using zero; N = not applicable" | "A = Not applicable (institution has no endowment to report); P = Imputed using Carry Forward procedure; Z = Implied zero; N = Imputed using Nearest Neighbor procedure. Per the FY2023 IPEDS dictionary's `imputation values` sheet (identical to FY2022); see `governance/eda/ipeds-finance-v1.4-flag-eda.md` §3.1 for verbatim excerpt." |

This is a SIGNIFICANT escalation under the v1.1 §3 amendment because it changes the documented semantic of a CDE-flagged column (`endowment_value_provenance`) before consumable landing. **Strong recommendation:** do not let `consumable.ipeds_finance_profile` land with the inverted narrative; the contract artifact (`consumable-ipeds-finance-profile.yaml`) and the BT-IPF-ENDOWMENT-PROVENANCE glossary entry are downstream-consumer-facing and a misread there propagates to every consumer of the table.

### 6.4 Add to `BSE-IPF-019` (or sister rule): a coupling-invariant assertion

**Why:** the `A`-flag-vs-value coupling (every `A` ↔ `endowment_value IS NULL`) is a tight structural invariant under the dictionary's "Not applicable" semantic. If a future cycle violates the coupling, that's evidence of either (a) NCES changing its imputation methodology to populate values for `A`-flagged rows (which would be the structural break BSE-IPF-019's distribution band is dimensioned to catch, but a coupling assertion catches it sooner and more crisply), or (b) a v1.4 ingestor bug causing the flag to drift away from the value.

**Suggested phrasing for the dq-rule-writer to consider:** add a P0 invariant rule (could be `BSE-IPF-019b` if the spec authors prefer a sub-rule, or a new `BSE-IPF-020`):

> 0 rows in `base.ipeds_finance` have `(endowment_value_flag = 'A' AND endowment_value IS NOT NULL) OR (endowment_value_flag IN ('R','P','N','Z') AND endowment_value IS NULL)` for F1A and F2 forms.

This is mechanically simple SQL; it would have caught the v1.3 EDA's narrative inversion at landing time if it had existed. Suggest P0 priority because a coupling break is a structural data event, not a calibration drift.

This is a **suggestion** to the dq-rule-writer; the EDA does not author rules, and the v1.4 spec does not currently scope this rule. Treat as a recommendation that the spec authors may choose to add to v1.4 or defer to v1.4.1.

### 6.5 Cross-tab invariants 5.1 and 5.2 are PASS — no spec change needed for `BSE-IPF-018`/`CON-IFP-013`

The F3-NULL-100% invariant and the F1A/F2 flag-always-present invariant both hold exactly. The proposed BSE-IPF-018 (passthrough fidelity) and CON-IFP-013 (rename passthrough fidelity) rules will operate on a clean upstream surface; no calibration adjustment is needed for those rules.

### 6.6 Drift escalation status — **NOT STRUCTURAL; NO RESPEC NEEDED ON METHODOLOGY**

The raw implementer's ad-hoc finding (FY2022 31.10%/25.31% → FY2023 9.77%/18.05% = "21pp drop on F1A, 7pp drop on F2, outside the 20-40% band") is a **measurement-comparability artifact**, not a structural cycle drift. The recommended response is:

- **Update the v1.4 spec's §3 narrative** to replace the FY2022 source-CSV measurement (1,936 / 1,782 row denominators) with the LANDED-bronze measurement (803 / 1,593 row denominators in FY2022, inferred under the `A`==NULL coupling) so that future drift comparisons use consistent denominators.
- **Recalibrate `BSE-IPF-019`** to per-form 5-15% / 12-25% (recommendation 6.1).
- **Do not** treat the prevalence finding as evidence of an NCES methodology shift; the dictionary did not change.

The narrative-vs-dictionary mismatch on `A` and `N` semantics (recommendation 6.3) is the **only** SIGNIFICANT escalation surfaced by this EDA pass; recommend routing it as a v1.4 spec amendment in-cycle (before consumable lands) rather than a v1.4.1 follow-on.

---

## §7 Audit Trail

| Step | Action | Result |
|---|---|---|
| 1 | Loaded `bronze.ipeds_finance` via `brightsmith.infra.iceberg_setup.get_catalog()` (warehouse `data/bronze/iceberg_warehouse`, catalog DB `data/catalog/catalog.db`) | Verified snapshot id `8612278722865929234`, 2,675 rows, 13-field schema with new `endowment_value_flag` at field_id 13 |
| 2 | Materialized into DuckDB in-memory; ran value-domain scan + cross-tab queries | §3.2, §4.1, §5 tables |
| 3 | Downloaded FY2023 dictionaries `F2223_F1A_Dict.zip` and `F2223_F2_Dict.zip` from `https://nces.ed.gov/ipeds/datacenter/data/` (UA `FutureProof/0.1`) | Both HTTP 200; XLSX extracted cleanly. `imputation values` sheet contains 13 codes (see §3.1 verbatim excerpt) |
| 4 | Cross-checked FY2022 dictionary `F2122_F1A_Dict.zip` for cycle-over-cycle dictionary stability | FY2022 `imputation values` sheet is byte-identical to FY2023 — methodology shift hypothesis ruled out |
| 5 | Computed apples-to-apples drift on landed bronze under the inferred `A`-flag-equals-NULL coupling | FY2022 → FY2023 drift: F1A +0.18pp / F2 +0.10pp; noise-level |
| 6 | Sampled F1A 'A'-flagged institution names + characteristics; sampled F2 'A'-flagged | Confirmed `A` semantic = "Not applicable" empirically: community colleges, tribal colleges, branch campuses, theological seminaries, system offices — institutions with no endowment fund of their own |
| 7 | Verified F3 NULL invariant (277/277) and F1A/F2 flag-without-value invariant (0/0) | §5.1, §5.2 |

**Audit trail entry:** `governance/audit-trail/` — log entry: this EDA refresh found that the apparent 21pp/7pp prevalence drop was a denominator artifact rather than a structural break; that the FY2023 dictionary publishes 13 codes (not 5); and that the v1.3-inherited spec narrative inverts the semantic of `A` (which is "Not applicable", not "model-imputed") and `N` (which is "Nearest Neighbor", not "Not applicable"). Recommended response: per-form `BSE-IPF-019` band of 5-15% F1A / 12-25% F2; spec narrative amendment for `A`/`N` semantics before consumable lands.

---

## §8 Standing Preferences

- No YAML lookup tables proposed.
- No substitution-based degraded states proposed; the `A` flag is a faithful passthrough of the IPEDS-published code, not a sidecar or fallback.
- All threshold recommendations cite measured numbers and the row counts from this EDA pass.
- No sanitizing of decision-relevant negative info: §6.3's correction surfaces *more* signal to downstream consumers (an `A`-flag-equals-NULL coupling is a clearer story than "model-imputed" for a longitudinal-analysis caveat).
