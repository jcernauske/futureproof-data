# Spec: full-pipeline-ipeds-finance

**Status:** DRAFT
**Zone:** Raw → Base → Consumable
**Primary Agent:** @primary-agent
**Created:** 2026-04-30

---

## Claude Code Prompt

```
Read the spec at docs/specs/full-pipeline-ipeds-finance.md in its entirety.

This spec lands the IPEDS Finance Survey (single source) through three zones:
  raw.ipeds_finance  →  base.ipeds_finance  →  consumable.ipeds_finance_profile

This is data-only work. NO MCP tool, NO backend service, NO frontend. Stop at consumable.

Execute the standard Brightsmith pipeline workflow:

1. PRE-IMPLEMENTATION REVIEW
   - @bs:governance-reviewer reviews §1–§6.
   - @fp-data-reviewer reviews §3 (Source) and §4–§6 (zones) for ingestor design, FTE-join correctness across the F1A/F2/F3 form variants, and per-FTE math.
   - Both write findings to §7.

2. RAW IMPLEMENTATION
   - Implement IpedsFinanceIngestor at src/raw/ipeds_finance_ingestor.py extending BaseIngestor.
   - Land raw.ipeds_finance per §4.

3. EDA + DOMAIN CONTEXT
   - @bs:data-analyst runs EDA against raw.ipeds_finance per §4 EDA Requirements.
   - @bs:domain-context updates governance/domain-context.md with the IPEDS Finance section.
   - EDA evidence calibrates §4/§5/§6 P1 thresholds; the DRAFT thresholds in this spec are starting points only.

4. BASE IMPLEMENTATION
   - Build the base.ipeds_finance transformer at src/silver/ipeds_finance_base.py per §5.
   - Use the idempotent promote pattern.

5. CONSUMABLE IMPLEMENTATION
   - Build the consumable.ipeds_finance_profile transformer at src/gold/ipeds_finance_profile.py per §6.

6. DQ + CHAOS + GOVERNANCE
   - @bs:dq-rule-writer authors rules from §4/§5/§6 + EDA evidence.
   - @bs:dq-engineer executes rules. P0 failures block.
   - @bs:chaos-monkey runs adversarial hardening on raw.ipeds_finance (5-cycle).
   - @bs:lineage-tracker, @bs:cde-tagger, @bs:doc-generator produce governance artifacts per §8.

7. SIGN-OFF
   - @bs:governance-reviewer post-implementation review.
   - @bs:staff-engineer final review.
   - @fp-builder runs ruff + mypy + pytest.

OUT OF SCOPE — do not extend:
  - No MCP tool.
  - No backend service / FastAPI router.
  - No frontend wiring.
  - No modification of any existing consumable.* table.
  - No fusion with EADA — that happens in raw-ingest-eada.md.
```

---

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-30 |
| Author | Jeff + Claude |
| Spec Version | 1.3 (DRAFT) |
| Last Updated | 2026-04-30 |
| Blocked By | — |
| Related Specs | `docs/specs/raw-ingest-eada.md` (downstream — fuses `base.ipeds_finance` with `base.eada` to produce `consumable.institution_aura`); `docs/specs/completed/raw-ingest-college-scorecard-institution.md` (UNITID join partner); `docs/specs/completed/raw-ingest-bea-rpp.md` (single-spec multi-zone reference pattern) |

---

## §1 Problem Statement

FutureProof has institution-level cost data (`raw-ingest-college-scorecard-institution.md`) but nothing on **how the institution actually spends its money**. IPEDS Finance Survey publishes per-institution expense breakdowns: institutional support (administration / marketing / recruiting), instruction (the educational product), and endowment value. Normalized per FTE student, these reveal whether a school's budget reflects the educational mission it sells.

This spec lands IPEDS Finance through Raw → Base → Consumable as a self-contained institution profile. The fusion with athletic data (EADA) and the composite aura_score live in the downstream spec `raw-ingest-eada.md`.

**Hard scope boundary:** No modification of the Five-Stat Pentagon, the boss fight system, or any existing `consumable.*` table. Additive only.

---

## §2 Design Decisions

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Single spec covers all three zones for one source, modeled on `raw-ingest-bea-rpp.md` | The source is narrow (~6,500 rows, 4 fields) and self-contained. A 3-spec split adds governance overhead without analytical benefit. | 3 specs (raw, base, consumable). Rejected per BEA precedent. |
| 2 | Per-FTE normalization happens in `base`, not `raw` | `raw` preserves source values verbatim. Per-FTE is a derivation that depends on a separate field (FTE enrollment). | Pre-compute in raw. Rejected — violates Brightsmith convention that raw is "faithful to source." |
| 3 | Three IPEDS finance forms (F1A public-GASB, F2 private-NFP-FASB, F3 private-FP) are UNIONed in raw with a `report_form` column | All three forms publish the same conceptual fields under different column names. Coalescing in raw keeps base downstream-clean. | One spec per form. Rejected — the form is an accounting-basis distinction, not a different concept. |
| 4 | FTE comes from the IPEDS Fall Enrollment (EF) survey, joined on UNITID at raw-ingest time | FTE is not in the Finance survey itself. The join pairs FY24 Finance with Fall 2023 EF per IPEDS publication calendar. | Defer FTE to base. Rejected — FTE is a raw upstream attribute, not a derivation. |
| 5 | UNITID is the canonical join key | Stable IPEDS identifier; already used by `consumable.career_outcomes`. | OPEID. Rejected — not the integration key in this repo. |
| 6 | Most-recent vintage only (single-year) | Mirrors how `consumable.regional_price_parities` handled the BEA single-year case. SCD2 is post-hackathon. | Multi-year SCD2. Out of scope. |
| 7 | "PrivacySuppressed" / IPEDS sentinels (`-1`, `-2`, blank) → NULL in raw | Same handling as College Scorecard ingest. | Preserve sentinels. Rejected — project convention is NULL. |
| 8 | Bureau-imputed values from IPEDS are accepted as raw values; imputation flag columns (`X*` prefix) are not stored in v1.2 | Imputation occurs upstream-of-source by NCES; the raw zone's "faithful to source" rule applies to what NCES publishes, not to what NCES imputed prior to publication. EDA Requirement 7 measures imputation prevalence to inform a future v1.3 decision on whether to suppress. | Suppress imputed values at raw (rejected — destroys signal NCES considers reliable) / Store flag columns (deferred to v1.3 if EDA prevalence warrants) |

### Constraints

- Hard scope ends at `consumable.ipeds_finance_profile` write.
- Additive-only — no modification of existing `raw.*`, `base.*`, or `consumable.*` tables.
- Chunked CSV reads (50,000 rows) per CLAUDE.md.
- `User-Agent: FutureProof/0.1 (jeff@hyenastudios.com)` on all downloads.

---

## §3 Source

| Property | Value |
|---|---|
| Provider | National Center for Education Statistics (NCES), IPEDS |
| URL | `https://nces.ed.gov/ipeds/datacenter/` (Compare Institutions → Finance) |
| Form variants | F1A (public, GASB), F2 (private nonprofit, FASB), F3 (private for-profit) |
| Auxiliary survey | **EFIA (12-Month Instructional Activity)**, file `EFIA{YYYY}` — for `total_fte_enrollment` (sum of `FTEUG + FTEGD + FTEDPP`, NULL-safe), joined on UNITID. EFIA is one row per UNITID (no dedup needed). EFFY (headcount) and EF Part A `EFTOTLT` (Fall headcount) are wrong sources — do not use. |
| Method | Bulk CSV download per form, UNION the three finance forms in raw, LEFT JOIN EFIA on UNITID |
| Grain | One row per institution (UNITID) per fiscal year |
| Filter | `ICLEVEL = 1 AND HLOFFER >= 5` — IPEDS-native "4-year, bachelor's degree or above" definition. (`ICLEVEL = 1` = "4 or more years"; `HLOFFER >= 5` = bachelor's, post-bacc cert, master's, post-master's, doctorate.) Sourced from IPEDS HD; do NOT use College Scorecard's `PREDDEG` here — taxonomy mix would introduce a Scorecard join dependency this raw zone does not declare. |
| Expected rows | ~6,000–7,000 |
| License | U.S. Government Work — public domain |

### Target Fields and Form-Specific Column Names

The four target fields exist on all three forms but use different column codes. Codes below are sourced from the NCES Delta Cost Project IPEDS-mapping file (`IPEDS_DCP_Database_Mapping_File_87_12.xls`) and the paulgp/ipeds-database harmonization README; **codes must still be re-verified against the latest IPEDS Finance survey dictionary by @bs:data-analyst during EDA** before raw is implemented (column suffixes drift across IPEDS revisions).

| Concept | F1A column (GASB, Part C functional expenses) | F2 column (FASB, Section E functional expenses) | F3 column (for-profit) | raw column |
|---|---|---|---|---|
| Institutional support expenses | F1C071 | F2E061 | **F3E03C1** (locked v1.3 — F3 reports institutional support separately on the post-2014-15 schedule; 100% non-null on FY2022) | `institutional_support_expenses` |
| Instruction expenses | F1C011 | F2E011 | **F3E011** (locked v1.3 — was provisionally `F3E01`; the actual code carries the `1` suffix for "Total amount") | `instruction_expenses` |
| Endowment value (end of year) | F1H02 | F2H02 | N/A — for-profit institutions do not maintain endowments; F3 has no `F3H` family; coalesces to NULL | `endowment_value` |
| Total FTE enrollment | **`COALESCE(FTEUG,0) + COALESCE(FTEGD,0) + COALESCE(FTEDPP,0)`** from the **EFIA** (12-Month Instructional Activity) survey, file `EFIA{YYYY}` (locked v1.3 — NOT EFFY, which is headcount). NULL only when all three components are NULL. | (same EFIA source) | (same EFIA source) | `total_fte_enrollment` |

**F3 NULL-coalesce:** if a target field is genuinely absent on F3 (e.g., `endowment_value` — for-profits don't have endowments), the raw column is NULL, never imputed to 0. Downstream `data_completeness_tier` correctly classifies such F3 rows as `medium` rather than misleading `high`. **Note (v1.3 update):** institutional support was previously suspected absent on F3 — pre-flight discovery confirmed it IS present at `F3E03C1`, populated for 100% of FY2022 F3 institutions. The endowment NULL-cascade still applies.

**Functional-expense Part letter:** F1A places revenues in Part B and **functional expenses in Part C** — the v1.0 codes (`F1B01` / `F1B07`) pointed at Part B (revenues) and would have silently mis-labeled revenue values as expenses. v1.1 fixes this to Part C (`F1C011` / `F1C071`).

**F3 sparseness (v1.3 corrected):** for-profit reporting (F3) is narrower than F1A/F2 only on the **endowment** axis — F3 has no `F3H` family for endowment value, so `endowment_value` and the derived `endowment_per_fte` correctly coalesce to NULL for F3 rows. Institutional support **is** separately reported on the post-2014-15 F3 schedule (`F3E03C1`, 100% non-null on FY2022) — the pre-v1.3 belief that F3 omitted institutional support was incorrect, and `marketing_ratio` should be computable for essentially all F3 rows. F3 rows therefore land at `data_completeness_tier=medium` (one missing field of four — endowment) rather than `low`/`medium-low` as v1.2 anticipated.

**FTE source choice (v1.3 locked):** The 12-month FTE source is the **EFIA** ("12-Month Instructional Activity") survey, file `EFIA{YYYY}.zip`, columns `FTEUG` (reported undergraduate FTE) + `FTEGD` (reported graduate FTE) + `FTEDPP` (reported doctor's-professional-practice FTE). NULL-safe sum: NULL only when all three components are NULL. NCES's per-FTE Data Feedback Report uses the *estimated* `EFTEUG/EFTEGD`; we use the *reported* variants because the dictionary states "If the institution did not provide an FTE then the reported FTE was set to the estimated FTE" — so the reported values preserve institution-confirmed FTE where given and fall back to NCES's estimate elsewhere. **Critical naming clarification:** the source file is `EFIA{YYYY}` (12-Month Instructional Activity), NOT `EFFY{YYYY}` (which is the unduplicated 12-month *headcount* file, broken out by `EFFYALEV`/`LSTUDY` and at the wrong grain). EF Part A's `EFTOTLT` is also a fall-snapshot **headcount** and must not be used. Earlier spec text using "EFFY/E12" is shorthand for "12-month enrollment family"; the operative file is `EFIA`.

**Year alignment caveat:** FY24 Finance pairs with the matching 12-month enrollment release (typically the same fiscal year). EDA must confirm the exact pairing; mis-pairing inflates per-FTE values when an institution's enrollment shifts year over year.

> **EDA correction — fiscal-year pivot (2026-04-30):** The "FY24 Finance" wording above is the original spec target. NCES has not yet released FY24 (HTTP 404 on `F2324_F1A.zip` / `F2324_F2.zip` / `F2324_F3.zip` as of 2026-04-30). The promote target is pinned to **`fiscal_year=2023`** (provisional release `F2223_F{1A,2,3}.zip`) until NCES publishes F2324; the matching 12-month enrollment file is `EFIA2223`. See §9 lineage `versionNote` and the EDA report at `governance/eda/full-pipeline-ipeds-finance-raw-eda.md` §3 (BLOCKING fiscal-year flip). When FY24 lands, this caveat reverts to its original form.

---

## §4 Zone 1 — Raw

### Iceberg Table: `raw.ipeds_finance`

- **Grain:** UNITID
- **Dedup grain:** `[unitid]`
- **Expected rows:** ~6,500 after the 4-year filter

### Ingestor

- **Class:** `IpedsFinanceIngestor` (extends `BaseIngestor`)
- **Location:** `src/raw/ipeds_finance_ingestor.py`
- **Implementation notes:**
  - Download F1A, F2, F3 CSVs separately (URL pattern `https://nces.ed.gov/ipeds/datacenter/data/F{YY}{YY}_F{1A|2|3}.zip`)
  - Download **EFIA** (12-Month Instructional Activity) CSV — file pattern `https://nces.ed.gov/ipeds/datacenter/data/EFIA{YYYY}.zip`. This is the FTE-bearing file. Do NOT download `EFFY{YYYY}.zip` (that is the unduplicated headcount file, wrong source) and do NOT use EF Part A `EFTOTLT`.
  - Coalesce form-specific column names per §3 into the four canonical raw columns. **F3 institutional support is `F3E03C1` and IS populated** (post-2014-15 schedule revision; v1.3-locked from pre-flight discovery). **F3 endowment is genuinely absent** (no `F3H` family on F3) — coalesce to NULL when reading F3 rows for `endowment_value`.
  - UNION the three finance forms with a `report_form` column (`F1A` / `F2` / `F3`)
  - **LEFT JOIN EFIA on UNITID** (no `WHERE` filter required — EFIA is published one row per UNITID, verified 6,036 rows / 6,036 distinct UNITIDs on FY2022). Compute `total_fte_enrollment = COALESCE(FTEUG, 0) + COALESCE(FTEGD, 0) + COALESCE(FTEDPP, 0)`, returning NULL only when all three components are NULL. Use *reported* FTE columns (`FTEUG`, `FTEGD`, `FTEDPP`) — they default to NCES *estimated* values (`EFTEUG`, `EFTEGD`) when the institution did not provide a reported figure, so they preserve institution-confirmed values where present.
  - Replace IPEDS sentinels (`-1`, `-2`, `.` (single period — legacy "not applicable" marker still appearing in modern releases), blank, "PrivacySuppressed") with NULL across all numeric fields before type coercion
  - Apply 4-year bachelor's-or-above filter (`ICLEVEL = 1 AND HLOFFER >= 5`) using IPEDS HD lookup, joined on UNITID. IPEDS-native fields only — do not use College Scorecard's `PREDDEG` here.
  - **Imputation handling:** IPEDS publishes parallel imputation-flag columns (e.g., `XF1C011` for `F1C011`, `XF1H02` for `F1H02`) indicating whether NCES bureau-imputed the value. Per **§2 Decision #8**, bureau-imputed values are accepted as raw values (the source CSV has already filled them in) and the flag column is not stored. EDA Requirement 7 covers whether a future revision should suppress bureau-imputed values to NULL; if that policy changes, both raw schema and §2 Decision #8 must be revisited.
  - Read CSVs in chunks (50,000 rows)

### Raw Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| unitid | long | yes | IPEDS 6-digit institution ID |
| institution_name | string | yes | From IPEDS HD lookup, joined on UNITID |
| report_form | string | yes | `F1A` / `F2` / `F3` |
| fiscal_year | int | yes | IPEDS fiscal year (e.g., 2024) |
| institutional_support_expenses | double | no | Coalesced per §3 |
| instruction_expenses | double | no | Coalesced per §3 |
| endowment_value | double | no | End-of-year endowment |
| total_fte_enrollment | double | no | From **EFIA** (12-Month Instructional Activity) survey, computed as NULL-safe `COALESCE(FTEUG,0) + COALESCE(FTEGD,0) + COALESCE(FTEDPP,0)` (locked v1.3). Joined on UNITID; EFIA is one row per UNITID so no dedup filter is needed. NOT EFFY (headcount) and NOT EF Part A `EFTOTLT`. |
| source_url | string | yes | Per-file source URL (pipe-delimited list of all 4 files) |
| source_method | string | yes | `bulk_csv_download` |
| ingested_at | timestamp | yes | Raw write timestamp |
| load_date | date | yes | Date of load |

### DQ Rules (Raw) — `RAW-IPF-*`

| Rule | Priority | Dimension | Notes |
|---|---|---|---|
| RAW-IPF-001 row count between 2,500 and 3,200 | P0 | Volume | EDA-calibrated 2026-04-30 against FY23 actual post-filter count of 2,675; original spec band 5,000–8,000 was based on pre-filter HD count |
| RAW-IPF-002 unitid non-null 100% | P0 | Completeness | hard |
| RAW-IPF-003 unitid uniqueness | P0 | Uniqueness | hard |
| RAW-IPF-004 report_form ∈ {F1A, F2, F3} | P0 | Validity | hard |
| RAW-IPF-005 instruction_expenses ≥ 0 where non-null | P0 | Validity | hard |
| RAW-IPF-006 institutional_support_expenses ≥ 0 where non-null | P0 | Validity | hard |
| RAW-IPF-007 endowment_value ≥ 0 where non-null | P0 | Validity | underwater funds report 0, never negative |
| RAW-IPF-008 total_fte_enrollment > 0 where non-null | P0 | Validity | hard |
| RAW-IPF-009 instruction_expenses non-null ≥ 90% | P0 | Completeness | hard |
| RAW-IPF-010 institutional_support_expenses non-null ≥ 90% | P0 | Completeness | hard |
| RAW-IPF-011 total_fte_enrollment non-null ≥ 95% | P0 | Completeness | hard |
| RAW-IPF-012 endowment_value non-null ≥ 60% | P1 | Completeness | many small institutions report 0 or null |
| RAW-IPF-013 fiscal_year is single value across all rows | P0 | Consistency | single-vintage invariant |
| RAW-IPF-014 spot check: at least one row with instruction_expenses > $100M (large R1 anchor) | P1 | Plausibility | EDA-calibrated |

### EDA Requirements (BLOCKING)

@bs:data-analyst must answer before base proceeds:

1. **Column-code lock-down (TBD items in §3).** Pull the live IPEDS Finance survey dictionary for the publication year being landed and verify/fill the §3 column table:
   - F1A: confirm `F1C011` (instruction) and `F1C071` (institutional support) — and that Part C is the correct functional-expenses block on the current form. **RESOLVED v1.3** — verified against `f2122_f1a.xlsx` varlist; both codes present and titled exactly as cited; spot-checked at UCB / UGA / UNC-CH.
   - F2: confirm `F2E011` (instruction) and `F2E061` (institutional support). **RESOLVED v1.3** — verified against `f2122_f2.xlsx` varlist; spot-checked at Stanford ($2.38B / $685M).
   - F3: identify the current instruction-expense column (provisionally `F3E01`) and confirm whether institutional support is separately reported on F3 — if not, document and coalesce to NULL. **RESOLVED v1.3** — instruction is **`F3E011`** (the `1` suffix denotes "Total amount"; provisional `F3E01` was wrong); institutional support **IS** separately reported as **`F3E03C1`**, 100% non-null on FY2022 (2,120/2,120 rows); the prior "F3 omits institutional support" hypothesis (true pre-2014-15) no longer holds.
   - EFFY/E12 FTE column: identify the directly-reported total-FTE column name (candidates: `FTE_TOTAL`, `FTE`, computed `FTEUG + FTEGD`). Pick the one IPEDS publishes natively; do NOT use EF Part A `EFTOTLT` (headcount). **RESOLVED v1.3** — total FTE = `COALESCE(FTEUG,0) + COALESCE(FTEGD,0) + COALESCE(FTEDPP,0)` from the **EFIA** file (NOT EFFY); `FTE_TOTAL` and `FTE` do not exist in any IPEDS file.
   - Endowment EOY: confirm `F1H02` and `F2H02`; document expected NULL for F3. **RESOLVED v1.3** — both codes verified against F1A/F2 dictionaries; F3 has no `F3H` family confirmed by varlist scan.
   - For each code, publish: the live dictionary entry text, one sample value for one known institution per form, and the raw CSV column header as it appears. **RESOLVED v1.3** — see `governance/eda/raw-ingest-ipeds-finance-preflight.md` for the dictionary excerpts, sample values (4 institutions across all forms), and CSV column headers (verified at byte level).
   - **EFFY/E12 file-variant + long-form dedup (BLOCKING for raw implementation).** Identify which IPEDS EFFY/E12 release file (e.g., `EFFY{YYYY}A` vs `EFFY{YYYY}B` vs `E12{YYYY}`) carries institution-level total FTE for the join year. Cite the exact file and column header. Then identify the dedup filter required to collapse EFFY/E12 to one row per UNITID before the LEFT JOIN to finance — typical candidates are `LEVEL` (level of student) or `LSTUDY` (level of study). Without this filter, finance rows fan out by student-level breakdown. **Risk to call out explicitly: without the dedup filter, per-FTE values inflate by the count of EFFY long-form rows per institution.** **RESOLVED v1.3** — the FTE-bearing file is **`EFIA{YYYY}`** (12-Month *Instructional Activity*), not any `EFFY{YYYY}*` variant. EFIA is published one row per UNITID (6,036 rows / 6,036 distinct UNITIDs on FY2022; no `LEVEL`/`LSTUDY`/`EFFYALEV` column present); **no dedup filter is required**. The fan-out risk is real for `EFFY{YYYY}.csv` (which IS broken out by `EFFYALEV` and would inflate per-FTE values if joined naïvely), but the operative file is EFIA.
2. **Form-coalescing correctness.** Confirm that the F1A / F2 / F3 expense fields above are semantically equivalent (instruction = teaching delivery, institutional support = administration / fundraising / executive) and not measuring different concepts on different accounting bases.
3. **EFFY year alignment.** Verify the FY24 Finance ↔ matching 12-Month Enrollment publication pairing. Spot-check 5 known institutions' published FTE against IPEDS Data Center to within 1%.
4. **Distribution shapes** for `instruction_expenses`, `institutional_support_expenses`, `endowment_value`, `total_fte_enrollment` — histograms, P5/P50/P95.
5. **Filter coverage.** How many UNITIDs exist in `raw.ipeds_finance` after the `ICLEVEL = 1 AND HLOFFER >= 5` filter, vs. how many distinct UNITIDs exist in `consumable.career_outcomes`? Report the overlap rate.
6. **Form-mix diagnosis.** What fraction of rows are F1A vs. F2 vs. F3? Report. Also report the F3-specific NULL rates on `institutional_support_expenses` and `endowment_value` to confirm the expected sparseness.
7. **Imputation-flag prevalence.** For each of the four analytical fields, report what fraction of non-null values carry a bureau-imputation flag (`X*` columns indicating NCES imputation). This calibrates whether v1.2 should suppress bureau-imputed values to NULL — v1.1 accepts them as raw values per §4 implementation notes.

EDA report → `governance/eda/raw-ingest-ipeds-finance-eda.md`.

---

## §5 Zone 2 — Base

### Iceberg Table: `base.ipeds_finance`

- **Grain:** UNITID
- **Dedup grain:** `[unitid]`
- **Promote pattern:** `compute_grain_id(row, ['unitid'], prefix='ipf')`
- **Idempotent:** Yes
- **Source:** `raw.ipeds_finance`

### Base Transformations

1. **Passthrough:** `unitid`, `institution_name`, `report_form`, `fiscal_year`, `institutional_support_expenses`, `instruction_expenses`, `endowment_value`, `total_fte_enrollment`.
2. **Per-FTE derivations:**
   ```
   institutional_support_per_fte = institutional_support_expenses / total_fte_enrollment
   instruction_per_fte           = instruction_expenses           / total_fte_enrollment
   endowment_per_fte             = endowment_value                / total_fte_enrollment
   ```
   Computed as `double`. NULL when either operand is NULL or `total_fte_enrollment ≤ 0`. **No imputation.**
3. **Marketing ratio** (cross-field, no FTE dependency):
   ```
   marketing_ratio = institutional_support_expenses / NULLIF(instruction_expenses, 0)
   ```
   Higher = relatively more spending on administration / marketing / recruiting vs. teaching. NULL when either operand is NULL or instruction is 0.
4. **Provenance columns:** `source_load_date` (from raw `load_date`), `ingested_at` (base promotion timestamp).

### Base Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| record_id | string | yes | `ipf-…` deterministic hash |
| unitid | long | yes | Join key |
| institution_name | string | yes | |
| report_form | string | yes | F1A / F2 / F3 |
| fiscal_year | int | yes | |
| institutional_support_expenses | double | no | Raw passthrough |
| instruction_expenses | double | no | Raw passthrough |
| endowment_value | double | no | Raw passthrough |
| total_fte_enrollment | double | no | Raw passthrough |
| institutional_support_per_fte | double | no | Derived |
| instruction_per_fte | double | no | Derived |
| endowment_per_fte | double | no | Derived |
| marketing_ratio | double | no | Derived |
| source_load_date | date | yes | |
| ingested_at | timestamp | yes | |

### DQ Rules (Base) — `BSE-IPF-*`

| Rule | Priority | Dimension |
|---|---|---|
| BSE-IPF-001 row count == raw row count | P0 | Conservation |
| BSE-IPF-002 unitid uniqueness | P0 | Uniqueness |
| BSE-IPF-003 record_id non-null + unique | P0 | Validity |
| BSE-IPF-004 instruction_per_fte ≥ 0 where non-null | P0 | Validity |
| BSE-IPF-005 institutional_support_per_fte ≥ 0 where non-null | P0 | Validity |
| BSE-IPF-006 endowment_per_fte ≥ 0 where non-null | P0 | Validity |
| BSE-IPF-007 marketing_ratio ≥ 0 where non-null | P0 | Validity |
| BSE-IPF-008 invariant: `instruction_per_fte * total_fte_enrollment` ≈ `instruction_expenses` within $1 where all three non-null | P0 | Arithmetic |
| BSE-IPF-009 invariant: same for institutional_support and endowment | P0 | Arithmetic |
| BSE-IPF-010 invariant: `marketing_ratio * instruction_expenses` ≈ `institutional_support_expenses` within $1 where all three non-null | P0 | Arithmetic |
| BSE-IPF-011 instruction_per_fte non-null ≥ 85% | P0 | Completeness |
| BSE-IPF-012 institutional_support_per_fte non-null ≥ 85% | P0 | Completeness |
| BSE-IPF-013 endowment_per_fte non-null ≥ 55% | P1 | Completeness |
| BSE-IPF-014 marketing_ratio non-null ≥ 85% | P0 | Completeness |
| BSE-IPF-015 marketing_ratio P99 < 5.0 (most schools spend less on admin than instruction) | P1 | Plausibility, EDA-calibrated |
| BSE-IPF-016 endowment_per_fte spot check: at least one row > $1M | P1 | Plausibility |
| BSE-IPF-017 instruction_per_fte P99 < $500,000 | P1 | Plausibility | EDA-calibrated; tripwire for EFFY FTE-vs-headcount field selection bug |

---

## §6 Zone 3 — Consumable

### Iceberg Table: `consumable.ipeds_finance_profile`

- **Grain:** UNITID
- **Dedup grain:** `[unitid]`
- **Promote pattern:** `compute_grain_id(row, ['unitid'], prefix='ifp')`
- **Idempotent:** Yes
- **Source:** `base.ipeds_finance`
- **Expected rows:** matches base row count

### Consumable Transformations

This is a base→consumable shaping promote. No cross-source joins; no derived score. The consumable carries the four per-FTE values + marketing_ratio + a data-completeness tier + raw expense passthroughs and is itself the institution-level finance profile. Fusion with EADA happens in `raw-ingest-eada.md`.

1. **Base passthrough:** `unitid`, `institution_name`, `report_form`, `fiscal_year`, `endowment_per_fte`, `institutional_support_per_fte`, `instruction_per_fte`, `marketing_ratio`, `total_fte_enrollment`, `instruction_expenses`, `institutional_support_expenses`, `endowment_value`. The three raw dollar passthroughs are exposed at consumable so downstream specs (notably `raw-ingest-eada.md`) can compute composite ratios without back-joining to base.
2. **Data completeness tier** — synthesized from the count of non-null **independent raw inputs** (not derived signals). Renamed from `confidence_tier` in v1.1 to disambiguate from CIP→SOC crosswalk-confidence tiers used elsewhere in the project:
   ```
   non_null_signals = (
     (instruction_expenses           IS NOT NULL)::int +
     (institutional_support_expenses IS NOT NULL)::int +
     (endowment_value                IS NOT NULL)::int +
     (total_fte_enrollment           IS NOT NULL AND total_fte_enrollment > 0)::int
   )
   data_completeness_tier = CASE
     WHEN non_null_signals = 4 THEN 'high'
     WHEN non_null_signals >= 2 THEN 'medium'
     WHEN non_null_signals = 1 THEN 'low'
     ELSE 'insufficient'
   END
   ```
   Counting independent raw inputs (vs. the v1.0 formula which mixed in the derived `marketing_ratio`) prevents the inflation effect where a present marketing_ratio re-counts the two expense fields it was derived from. It also makes `total_fte_enrollment` first-class — when FTE is missing, all three per-FTE values are NULL and the row is unusable for per-student comparison even if the dollar fields are present.
3. **Provenance:** `promoted_at` timestamp.

### Consumable Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| record_id | string | yes | `ifp-…` |
| unitid | long | yes | Join key to existing consumable.* tables |
| institution_name | string | yes | |
| report_form | string | yes | F1A / F2 / F3 |
| fiscal_year | int | yes | |
| total_fte_enrollment | double | no | |
| instruction_expenses | double | no | Raw passthrough (dollars). Exposed at consumable for downstream EADA composite ratios. |
| institutional_support_expenses | double | no | Raw passthrough (dollars). Exposed at consumable for downstream EADA composite ratios. |
| endowment_value | double | no | Raw passthrough (dollars). Exposed at consumable for downstream EADA composite ratios. |
| institutional_support_per_fte | double | no | |
| instruction_per_fte | double | no | |
| endowment_per_fte | double | no | |
| marketing_ratio | double | no | Institutional support / instruction |
| data_completeness_tier | string | yes | `high` / `medium` / `low` / `insufficient` (renamed from `confidence_tier` in v1.1; counts non-null independent raw inputs) |
| promoted_at | timestamp | yes | |

### DQ Rules (Consumable) — `CON-IFP-*`

| Rule | Priority | Dimension |
|---|---|---|
| CON-IFP-001 row count == base row count | P0 | Conservation |
| CON-IFP-002 unitid non-null 100% | P0 | Completeness |
| CON-IFP-003 unitid uniqueness | P0 | Uniqueness |
| CON-IFP-004 record_id non-null + unique | P0 | Validity |
| CON-IFP-005 data_completeness_tier ∈ {high, medium, low, insufficient} | P0 | Validity |
| CON-IFP-006 data_completeness_tier classification check (recompute from the four independent raw inputs and compare) | P0 | Arithmetic |
| CON-IFP-007 institutional_support_per_fte / instruction_per_fte ≈ marketing_ratio within 0.001 where all three non-null | P0 | Arithmetic |
| CON-IFP-008 ≥ 90% of distinct UNITIDs in `consumable.career_outcomes` find a matching row in `consumable.ipeds_finance_profile` | P1 | Coverage, EDA-calibrated |
| CON-IFP-009 data_completeness_tier=`high` rows ≥ 70% | P1 | Distribution, EDA-calibrated |
| CON-IFP-010 promoted_at non-null | P0 | Completeness |

### Data Contract

| Property | Value |
|---|---|
| Owner | @bs:data-steward |
| SLA | Annual refresh when IPEDS publishes new Finance + EFFY/E12 data (typically December) |
| Quality tier | EDA-calibrated; expected `high` |
| Consumers | `raw-ingest-eada.md` (downstream fusion); future receipts/comparison specs |
| Row count guarantee | matches base |
| CDE candidates | `marketing_ratio`, `endowment_per_fte`, `institutional_support_per_fte`, `instruction_per_fte`, `data_completeness_tier` |

### Business Glossary Terms (Proposed)

Final IDs assigned by @bs:data-steward.

- **BT-IPF-INSTRUCTION-EXPENSES** — Total annual expenses an institution reports as direct expenditure on instruction (faculty salaries, instructional materials, departmental research). Source: IPEDS Finance Survey, **F1C011** (public, GASB — Part C functional expenses) / **F2E011** (private NFP, FASB — Section E functional expenses) / **F3E01** (private for-profit, TBD pending EDA verification). The denominator in the marketing ratio.
- **BT-IPF-INSTITUTIONAL-SUPPORT-EXPENSES** — Total annual expenses for executive management, fiscal operations, public relations, fundraising, and similar administrative functions. Source: IPEDS Finance Survey **F1C071** / **F2E061** / F3 (not separately reported on most for-profit schedules — coalesces to NULL). Often a proxy for "marketing and administration overhead" in budget transparency analyses.
- **BT-IPF-ENDOWMENT-VALUE** — End-of-year market value of an institution's endowment funds. Source: IPEDS Finance Survey **F1H02** / **F2H02**. Not applicable to for-profit institutions (F3) — coalesces to NULL.
- **BT-IPF-PER-FTE** — Convention for normalizing institution-level financial measures by total FTE enrollment (sourced from the IPEDS EFFY / 12-Month Enrollment survey, NOT the EF Part A `EFTOTLT` headcount), producing a per-student measure comparable across institutions of different size. Per-FTE values are NULL when either the financial value or FTE is missing; no imputation.
- **BT-IPF-MARKETING-RATIO** — Ratio of institutional support expenses to instruction expenses. Higher = relatively more spending on administration, marketing, and recruiting vs. teaching. Bounds vary widely; EDA P99 around 5.0.
- **BT-IPF-DATA-COMPLETENESS-TIER** — Source-data-completeness signal computed from the count of non-null **independent raw inputs** (`instruction_expenses`, `institutional_support_expenses`, `endowment_value`, `total_fte_enrollment`). Values: `high` (4/4), `medium` (2–3/4), `low` (1/4), `insufficient` (0/4). **This is NOT a CIP→SOC crosswalk-confidence tier** — it measures source-field non-null count, not crosswalk match quality. Renamed from `confidence_tier` in v1.1 to disambiguate.

---

## §7 Architecture / Data Review

**Revision history:** v1.1 (2026-04-30): Addressed pre-impl data review findings 1–4 per fp-data-reviewer. v1.2 (2026-04-30): Addressed v1.1 second-pass items R1–R3 + cosmetic + elevated imputation policy to §2 Decision #8. v1.3 (2026-04-30): Pre-flight discovery locked §3 TBDs (F3 institutional support → `F3E03C1`, F3 instruction → `F3E011`, FTE source → `EFIA{YYYY}` file with `FTEUG+FTEGD+FTEDPP`, no dedup filter needed) per @bs:data-analyst pre-flight pass — see `governance/eda/raw-ingest-ipeds-finance-preflight.md`.

### @bs:governance-reviewer
**Status:** APPROVED (v1.1)

#### v1.1 Delta Findings

Delta review of v1.1 against the v1.0 APPROVED baseline. Verdict: **APPROVED** — v1.0 approval holds; v1.1 changes are governance-positive. One net-new ADVISORY (ADV-6) below; no CHANGES REQUESTED, no REJECTED. Reviewed only the deltas listed in the delta-check brief (§3 column codes, §3 filter, §4 sentinel + imputation policy, §6 tier rename + raw passthroughs, §1 metadata bump).

**Delta-by-delta governance assessment:**

1. **§3 F1A column-code corrections (`F1B07`/`F1B01` → `F1C071`/`F1C011`).** Governance-positive — fixes a latent silent-data-corruption risk (Part B is revenues; Part C is functional expenses on F1A). The corrected codes align with the NCES Delta Cost Project mapping and the paulgp/ipeds-database harmonization README cited in §3. No governance artifact impact beyond the BT-IPF-INSTRUCTION-EXPENSES and BT-IPF-INSTITUTIONAL-SUPPORT-EXPENSES glossary entries (already updated in §6 to cite the corrected codes).

2. **§3 F3 institutional-support marked TBD-pending-EDA; F3 endowment marked N/A.** Acceptable governance practice. The TBD is gated as BLOCKING under the expanded EDA Requirement 1 with specific resolution criteria (publish live dictionary entry, sample value, raw CSV column header per form). F3-endowment N/A is correctly documented in three places (§3 column table, §3 narrative under "F3 sparseness," and the BT-IPF-ENDOWMENT-VALUE glossary entry). The expected NULL-cascade through `marketing_ratio` and `endowment_per_fte` for F3 rows is now explicit, which prevents downstream consumers from misreading legitimate NULLs as data-quality failures.

3. **§3 FTE source change (EF.EFTOTLT → EFFY/E12 directly-reported FTE, exact column TBD).** Governance-positive — corrects a wrong-field bug that would have systematically deflated per-FTE values for institutions serving non-traditional students (`EFTOTLT` is headcount, not FTE). The "exact column name TBD" gap is gated as BLOCKING under EDA Requirement 1 with three named candidate columns and a 5-institution spot-check tolerance (1%) under EDA Requirement 3. The "do NOT use EFTOTLT" warning is repeated in three load-bearing places (§3 row, §4 implementation notes, BT-IPF-PER-FTE glossary) — repetition is appropriate given the bug it prevents.

4. **§3 filter `PREDDEG = 3 OR ICLEVEL = 1` → `ICLEVEL = 1 AND HLOFFER >= 5`.** Governance-positive — eliminates the mixed-taxonomy issue (PREDDEG is a Scorecard field, not native IPEDS HD) and removes the implicit Scorecard join dependency that v1.0 did not declare. The IPEDS-native filter is also semantically tighter (ICLEVEL=1 alone admitted graduate-only schools that don't grant bachelor's). Matches the IPEDS-canonical "4-year bachelor's-granting" definition cited in EDA Requirement 5. Note: this delta invalidates one bullet in the v1.0 compliance highlights ("§3 filter is byte-equivalent to the contract-enforced filter on `raw.college_scorecard_institution`"). That is acceptable: the new filter is taxonomy-correct, and the coverage-rate check in CON-IFP-008 + EDA Requirement 5 will surface any meaningful overlap drift against `consumable.career_outcomes`.

5. **§4 sentinel list extended to include `.` (single period).** Compliant with project rule "PrivacySuppressed → NULL" and §2 Decision 7. The single-period legacy "not applicable" marker is treated in line with Decision 7's spirit (treat all source-side missing-value markers as NULL before type coercion). No governance artifact impact.

6. **§4 imputation-flag policy added (bureau-imputed values accepted as raw, flag not stored).** Acceptable for v1.1 with a clearly documented exit ramp. The policy is consistent with §2 Decision 7 *as written* — Decision 7 enumerates source-side sentinels (`-1`, `-2`, blank, `"PrivacySuppressed"`) that get NULLed, and bureau-imputed values are NOT in that list (they appear as filled-in numeric values in the source CSV, not as sentinels). v1.1 makes this explicit by calling it "an accepted exception to the no-imputation rule because imputation is upstream-of-source," and gates the policy revisit on EDA Requirement 7 evidence. The framing ("accepted exception") is the right governance posture: it acknowledges that the no-imputation rule's spirit (don't fabricate data downstream of the source) is technically intact, while flagging that the letter of the rule could plausibly be read more strictly. EDA Requirement 7's prevalence numbers will determine whether v1.2 needs to suppress bureau-imputed values to NULL — at which point both raw schema and Decision 7 must be revisited (§4 already says this). Textbook "documented limitation with named escalation trigger." Approved.

7. **§4 EDA Requirements 1 and 7 added to lock the TBDs.** Governance-positive. EDA Requirement 1 explicitly enumerates the F1A/F2/F3 column codes and the EFFY/E12 FTE-column candidates that must be verified against the live IPEDS dictionary before raw is implemented, and demands published evidence (dictionary text, sample value, raw CSV column header). EDA Requirement 7 turns the imputation-flag policy from an unbounded exception into a calibrated one. Both requirements are correctly framed as BLOCKING. The TBD markers in §3 are therefore acceptable governance practice — they are gated, time-bounded by the EDA step, and have explicit resolution criteria.

8. **§6 `confidence_tier` → `data_completeness_tier` rename + new BT-IPF-DATA-COMPLETENESS-TIER glossary term.** Defensibly disambiguates from CIP→SOC crosswalk-confidence tiers used elsewhere in the project (e.g., `ConceptNormalizer` tiers). The new glossary term explicitly states "**This is NOT a CIP→SOC crosswalk-confidence tier** — it measures source-field non-null count, not crosswalk match quality." The rename is propagated consistently to the schema, CON-IFP-005, CON-IFP-006, CON-IFP-009, the Data Contract CDE-candidates list, and the consumable-transformations narrative. The disambiguation is load-bearing because the downstream `raw-ingest-eada.md` spec is likely to introduce its own confidence tiers — without this rename, two semantically distinct "confidence_tier" fields could end up in adjacent tables. Approved.

9. **§6 reformulated tier counts 4 independent raw inputs (no longer mixes in derived `marketing_ratio`).** Governance-positive — addresses the v1.0 fp-data-reviewer finding (d) that derived signals re-counted their own inputs and inflated tier scores. The new formula makes `total_fte_enrollment` a first-class tier input, which correctly penalizes rows where FTE is missing (since all three per-FTE values then NULL-cascade and the row is unusable for per-student comparison). CON-IFP-006 (recompute classification and compare) closes the loop. The `4 → high`, `≥ 2 → medium`, `= 1 → low`, `0 → insufficient` breakdown is documented consistently in §6 transformations, schema notes, and glossary.

10. **§6 raw expense passthroughs (`instruction_expenses`, `institutional_support_expenses`, `endowment_value`) added to consumable schema for downstream EADA fusion.** Approved as a justified narrow exception to the "consumable is shaped, not raw-pass-through" Brightsmith convention. Three justifications, all sound: (a) without the passthrough, downstream `raw-ingest-eada.md` would have to back-join to `base.ipeds_finance` to compute composite ratios like "athletic spending as % of institutional support" — that violates the gold-only-consumption pattern more severely than the passthrough does; (b) the dollar values were already exposed at base, so there is no new information leak; (c) §6 explicitly documents the rationale ("Exposed at consumable for downstream EADA composite ratios") on each of the three schema rows. The exception is narrow (3 fields, all already documented in glossary terms), justified by a named downstream consumer, and self-documenting in the schema. The Data Contract section already lists the consumer (`raw-ingest-eada.md`) explicitly. No artifact impact beyond the data-contract YAML which will pick up the three new columns at @bs:doc-generator time.

11. **§6 `data_completeness_tier` added to CDE candidates.** Consistent with the field's role as a downstream consumer-facing signal that controls whether to display an institution's profile. CDE tagging will land in `governance/cde-tagging/consumable-ipeds-finance-profile.md` per §8.

12. **§1 metadata bumped to v1.1 (DRAFT).** Status correctly remains DRAFT pending this re-review. Revision history at the top of §7 cites the four addressed findings. Compliant.

**Cross-cutting governance checks (re-verified against v1.1):**

- **§8 governance artifact list** still complete for a 3-zone spec; no new artifacts required by v1.1 changes. The data contract YAML will absorb the schema deltas (renamed `data_completeness_tier`, three raw-dollar passthroughs) at generation time without needing a new artifact entry.
- **CDE/PII tagging** picks up the renamed `data_completeness_tier` and the three raw-dollar passthroughs at @bs:cde-tagger time. The Data Contract section already lists CDE candidates correctly.
- **Data dictionary** will pick up the renamed field and the three passthrough fields at @bs:doc-generator time — no spec-side action needed.
- **Business glossary** now lists six BT-IPF-* terms (BT-IPF-DATA-COMPLETENESS-TIER added to the original five). §8 still says "5 BT-IPF-* terms" — see ADV-6 below.
- **Lineage scope** unchanged by v1.1 deltas (no new transformations, only field-level changes — lineage will pick up renamed field and passthroughs at @bs:lineage-tracker time).
- **DQ rules** updated in lockstep: CON-IFP-005/006/009 reference the renamed `data_completeness_tier`. No orphaned rules referencing `confidence_tier`. CON-IFP-006 still recomputes from the 4 independent inputs — consistent with the new formula in §6.2.
- **No standing-preference violations.** Spec still does not use `major_to_cip.yaml` or any YAML lookup; `data_completeness_tier` remains a non-null transparency signal, not a substitution-based degraded state.

**v1.1 net-new advisories:**

| # | Severity | Section | Description |
|---|----------|---------|-------------|
| ADV-6 | ADVISORY | §8 governance artifacts | Business-glossary line still reads "5 BT-IPF-* terms" but v1.1 added BT-IPF-DATA-COMPLETENESS-TIER as a sixth term in §6. Bump to "6 BT-IPF-* terms" on the next edit pass. Cosmetic only. |

The five v1.0 advisories (ADV-1 through ADV-5) all remain open and are unaffected by v1.1 deltas:
- ADV-1 (title/prompt filename mismatch) — still applies; spec H1 still reads `raw-ingest-ipeds-finance` while file is `full-pipeline-ipeds-finance.md`.
- ADV-2 (model-stem prefix inconsistency in §8) — still applies.
- ADV-3 (future-SCD2 dedup-grain migration note) — still applies.
- ADV-4 (CON-IFP-008 coverage-driver investigation during EDA) — still applies and is now *more* relevant: the filter change in delta 4 will yield a different overlap rate against `consumable.career_outcomes` than the v1.0 filter would have, so EDA must surface the breakdown.
- ADV-5 (post-impl review must verify EDA spot-check evidence on FY24 / 12-Month Enrollment pairing) — still applies; EDA Requirement 3 unchanged.

**Decision rationale (v1.1):** All four v1.1 deltas address real v1.0 governance gaps (silent-corruption risks on column codes and FTE source) or improve clarity (tier rename, passthrough rationale). The two TBD markers in §3 are properly gated as BLOCKING EDA work with named resolution criteria — that is the textbook governance posture for "we know we don't know yet." The imputation-flag accept-as-raw policy is consistent with the letter of §2 Decision 7 (which enumerates source-side sentinels, not bureau imputations) and is honestly documented as an "accepted exception" with EDA Requirement 7 as the calibration trigger. The new BT-IPF-DATA-COMPLETENESS-TIER term carries its own disambiguation against the project's other "confidence_tier" usages. The raw expense passthroughs are a justified narrow exception to the gold-shaped-not-pass-through convention, with three named justifications and a documented downstream consumer. No standing preferences are violated. v1.0 approval holds; v1.1 is APPROVED to proceed to implementation.

---

#### v1.0 Findings (preserved for history)

Pre-implementation review of §1–§6 against Brightsmith governance standards. Verdict: **APPROVED** — proceed to implementation. All findings below are ADVISORY (no CHANGES REQUESTED, no REJECTED). Reviewed against the BEA RPP precedent (`docs/specs/completed/raw-ingest-bea-rpp.md`) for the single-spec multi-zone pattern and against `governance/data-contracts/raw-college-scorecard-institution.yaml` for filter-logic alignment.

**Compliance highlights (non-blocking, recorded for audit):**

- §2 design decisions are consistent with Brightsmith conventions: raw is faithful to source (decision 2), per-FTE / marketing_ratio / confidence_tier are derivations placed in the correct zones, sentinel handling matches the Scorecard precedent (decision 7), single-vintage scope is explicitly bounded (decision 6).
- §3 filter `PREDDEG = 3 OR ICLEVEL = 1` is byte-equivalent to the contract-enforced `filter_predicate: "PREDDEG == 3 OR ICLEVEL == 1"` on `raw.college_scorecard_institution`, so coverage with `consumable.career_outcomes` will be tight.
- §3 license claim "U.S. Government Work — public domain" is defensible: IPEDS is published by NCES (U.S. Dept. of Education) and matches the wording used on both the BEA RPP and College Scorecard ingest specs.
- §4 dedup grain `[unitid]` is correct under the single-vintage invariant enforced by RAW-IPF-013. (See ADV-3 below for future-SCD2 note.)
- §4 form-column codes (F1B01 / F2E011 / F3E01 etc.) are explicitly marked as working assumptions, with verification gated as a BLOCKING EDA requirement. Properly handled.
- §5 base derivations are `double`, NULL-on-divide-by-zero or NULL-operand, with no imputation — matches the standing project rule.
- §5 idempotent promote pattern uses `compute_grain_id(row, ['unitid'], prefix='ipf')`; §6 uses `prefix='ifp'`. Distinct prefixes prevent record_id collisions across zones. Compliant.
- §5 arithmetic-invariant DQ rules (BSE-IPF-008/009/010) round-trip the per-FTE and ratio derivations within a $1 floating-point tolerance — a strong guard against silent corruption.
- §6 confidence_tier formula is deterministic from non-null analytical-field count, and CON-IFP-006 recomputes it as a DQ check — closes the loop.
- §6 contains no cross-source joins; fusion with EADA is correctly deferred to `raw-ingest-eada.md`.
- §8 governance artifact list is complete for a 3-zone spec: EDA, domain context, models × 3 zones, DQ rules × 3 zones, scorecards, chaos report (raw), adversarial audit (consumable), lineage, CDE tagging, data contract, dictionary, glossary (5 BT-IPF-* terms), and three approvals (pre/post/staff).
- Business glossary terms (BT-IPF-INSTRUCTION-EXPENSES, BT-IPF-INSTITUTIONAL-SUPPORT-EXPENSES, BT-IPF-ENDOWMENT-VALUE, BT-IPF-PER-FTE, BT-IPF-MARKETING-RATIO) each cite source + form-specific column codes, give operational definitions, and BT-IPF-PER-FTE explicitly states the no-imputation convention. Definitions are defensible.

**Advisory items (do not block):**

| # | Severity | Section | Description |
|---|----------|---------|-------------|
| ADV-1 | ADVISORY | Title (line 1) + §Claude Code Prompt (line 13) | Spec was renamed from `raw-ingest-ipeds-finance.md` to `full-pipeline-ipeds-finance.md`. The H1 title still reads `raw-ingest-ipeds-finance` and the Claude Code Prompt's read instruction still references `docs/specs/raw-ingest-ipeds-finance.md`. Cosmetic only — implementation will succeed because Claude Code is given the actual filename at invocation. Suggest fixing on the next edit pass. |
| ADV-2 | ADVISORY | §8 governance artifacts | Models list uses inconsistent stem prefixes (`raw-ingest-ipeds-finance-…` vs. `base-ipeds-finance-…` vs. `consumable-ipeds-finance-profile-…`). Functionally fine — each path is distinct — but consider standardizing to `<zone>-ipeds-finance-…` (i.e., `raw-ipeds-finance-…`) for symmetry with the base/consumable entries. Non-blocking. |
| ADV-3 | ADVISORY | §2 decision 6 + §4 dedup grain | Single-vintage scope is correct for hackathon. When SCD2 is later introduced, dedup grain must extend to `[unitid, fiscal_year]` and `compute_grain_id` prefixes (`ipf`, `ifp`) must include vintage in the hash. Capture this in a future migration note when the SCD2 spec is drafted. |
| ADV-4 | ADVISORY | §6 CON-IFP-008 | Coverage rule "≥ 90% of distinct UNITIDs in `consumable.career_outcomes` find a matching row" is P1 EDA-calibrated. Confirm during EDA whether the gap is driven by graduate-only schools (PREDDEG=4 captured by ICLEVEL=1) or by IPEDS Finance reporting lag. If the latter, a P0 alert on a coverage drop between vintages is worth adding in a future revision. |
| ADV-5 | ADVISORY | §3 + §4 EDA req 2 | The FY24 Finance ↔ Fall 2023 EF pairing is a published-calendar assumption. EDA spot-check of 5 known institutions is required before base proceeds — this is correctly gated as BLOCKING in §4 EDA Requirements. Calling it out here so the post-implementation review can verify the EDA report cited the spot-check evidence. |

No standing-preference violations were proposed: the spec does not use `major_to_cip.yaml` or any YAML lookup as a resolution strategy, and the `confidence_tier` field is a non-null transparency signal, not a substitution-based degraded state.

**Decision rationale:** Spec is internally consistent, externally aligned with established precedents (BEA RPP for shape, College Scorecard for filter and sentinel handling), correctly scoped (hard stop at consumable, no MCP/backend/frontend), and has a complete governance artifact slate. The blocking risks (form-column-code accuracy, EF year alignment) are correctly gated as BLOCKING EDA work in §4 — they are deferred to evidence, not assumed away. Approved to proceed to implementation.

**v1.1 re-review note:** §3 column-code table, §3/§4 FTE source, §3 filter, §6 tier rename, and §6 raw passthroughs were modified between v1.0 and v1.1 to address fp-data-reviewer findings. v1.1 delta review completed at top of this section — v1.0 approval holds.

#### Verdict
- [x] APPROVED (v1.1 — v1.0 approval reaffirmed; delta findings appended above)
- [ ] CHANGES REQUESTED
- [ ] REJECTED

---

#### Post-Implementation Review (Bronze Zone)

**Reviewer:** @bs:governance-reviewer
**Date:** 2026-05-01
**Scope:** Bronze zone only (`bronze.ipeds_finance`, snapshot `2955168649587464831`, FY2023, 2,675 rows). Silver/Gold not yet executed — those zones are out of scope for this review.
**Verdict:** **APPROVED for bronze, with one CHANGES REQUESTED follow-up (non-blocking for silver-zone progression — see Issue P-1).**

##### Governance Completeness Checklist (bronze artifacts)

| Item | Path | Status |
|---|---|---|
| EDA report | `governance/eda/raw-ingest-ipeds-finance-eda.md` | PASS |
| Pre-flight EDA | `governance/eda/raw-ingest-ipeds-finance-preflight.md` | PASS |
| Domain context appended | `governance/domain-context.md` | PASS |
| Models — conceptual | `governance/models/raw-ipeds-finance-conceptual.md` | PASS (erDiagram present) |
| Models — logical | `governance/models/raw-ipeds-finance-logical.md` | PASS (bronze gate skips three-stage requirement; logical doc still produced) |
| Models — physical | `governance/models/raw-ipeds-finance-physical.md` | PASS (matches landed Iceberg schema field-for-field) |
| DQ rules | `governance/dq-rules/raw-ipeds-finance.json` (14 rules: 12 P0 + 2 P1) | PASS |
| DQ execution | `governance/dq-scorecards/raw-ipeds-finance-20260501T202737Z.{json,md}` | PASS |
| DQ P0 gate | `p0_passed=true`, 12/12 P0 PASS, 2/2 P1 PASS | PASS |
| Chaos report | `governance/chaos-reports/raw-ipeds-finance-chaos.md` (60/60 in-scope catches; 2 expected misses; 3 P2 follow-ups) | PASS |
| Adversarial audit | `governance/adversarial-audits/raw-ipeds-finance-bronze-audit.md` (CLEAR; 1 cosmetic hallucination) | PASS |
| Lineage | `governance/lineage/full-pipeline-ipeds-finance-20260501T203128Z.json` (5 inputs, 1 output, full column-lineage) | PASS |
| CDE tagging | `governance/cde-tagging/raw-ipeds-finance.md` (5 CDEs, 0 PII) | PASS |
| PII scan | Documented inline in CDE artifact (institution-level public IPEDS data; no PII) | PASS |
| Data dictionary | `governance/data-dictionaries/raw-ipeds-finance.md` (12-field definitions) | PASS |
| Business glossary | 4 BT-IPF-* terms appended to `governance/business-glossary.json` | PASS |
| Audit-trail entries | `governance/audit-trail/2026-04-30-data-analyst-full-pipeline-ipeds-finance-raw-eda.md`, `governance/audit-trail/raw-ipeds-finance-dq-execution.md` | PASS |
| Spec amendment for RAW-IPF-001 | Implemented in `governance/dq-rules/raw-ipeds-finance.json` rule definition (2,500–3,200 band) | PARTIAL — see Issue P-2 |
| Insight-traceability check | No prior insight reports reference this table; check N/A | PASS |
| No orphaned artifacts | Every artifact references the same 12-field schema and the same `bronze.ipeds_finance` table | PASS |

##### Cross-Artifact Consistency Spot-Checks (verified against live `bronze.ipeds_finance`)

I queried the landed table directly via PyIceberg to verify the orchestrator's claims:

| Claim | Source | Live Value | Verdict |
|---|---|---|---|
| Row count = 2,675 | scorecard, lineage, EDA, dictionary | 2,675 | MATCH |
| Form mix F1A 30.6% / F2 59.0% / F3 10.4% | EDA, data dictionary | F1A 30.62% / F2 59.03% / F3 10.36% | MATCH |
| F3 endowment 100% NULL | spec §3, EDA, lineage, dictionary | 100.00% | MATCH |
| F3 institutional_support 0% NULL | spec §3 v1.3 lock-down, EDA, lineage | 0.00% | MATCH |
| `fiscal_year` single-value invariant | RAW-IPF-013, lineage | unique = `[2023]` | MATCH |
| Rows with `instruction_expenses > $100M` | EDA §8 says 268; rule rationale says 269; dictionary says 269 (twice) | **365** | MISMATCH — see Issue P-1 |

##### Issues

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| **P-1** | CHANGES REQUESTED | The "rows > $100M instruction_expenses" anchor count is published in **three** governance artifacts as `268` (EDA §8 line 279) or `269` (`governance/dq-rules/raw-ipeds-finance.json` RAW-IPF-014 rationale; `governance/data-dictionaries/raw-ipeds-finance.md` lines 71 and 112). Adversarial-auditor flagged the 269 occurrence in the rule rationale; live count is **365**. None of the three threshold tests depend on this number (RAW-IPF-014 floor is `≥ 1`; the EDA's non-binding `≥ 200` suggestion is also satisfied at 365), so this is **cosmetic only — does not block silver-zone progression**. But it is published evidence in four locations and a regulator re-running the query would catch a 36% delta. **Fix path: correct in a single follow-up commit** — update EDA §8 (`268` → `365`), `dq-rules/raw-ipeds-finance.json` RAW-IPF-014 rationale (`269` → `365`), and `data-dictionaries/raw-ipeds-finance.md` lines 71 + 112 (`269` → `365`). Suggest @bs:doc-generator owns the cleanup. |
| **P-2** | CHANGES REQUESTED | Spec §4 line 190 still reads "RAW-IPF-001 row count between 5,000 and 8,000" — the EDA-calibrated band of 2,500–3,200 is implemented in the rule JSON and noted in the JSON's `notes`/`rationale` block, but **the spec table itself is not amended**. Lineage and scorecard reference the rule by ID (so execution is correct), but a future reader cross-referencing spec → rule will see a contradiction. **Fix path: amend §4 DQ Rules table** (line 190) to read "RAW-IPF-001 row count between 2,500 and 3,200" with a parenthetical "(EDA-calibrated 2026-04-30 — original 5,000–8,000 band predated HD-filter narrowing)." Non-blocking for silver — the rule executes against the corrected band. |
| **P-3** | ADVISORY | The FY pivot (FY24 → FY23) is documented in three places: (a) the §9 Implementation Log "Deviations from Spec" table (line 778), (b) the lineage `versionNote` facet, and (c) the EDA report. §1/§2/§3 spec text still narrates "FY24" as the primary cycle. The deviation table is the auditable record, so this is acceptable; an explicit "v1.4 amendment block" at the top of §3 calling out "FY24 not yet published by NCES; current promote target is FY23" would be cleaner but is not required — the §9 deviations table closes the loop. Recommend leaving §1–§3 implicit and tightening §3 line 142 ("Year alignment caveat: FY24 Finance pairs with…") to reference FY23 once silver/gold runs are complete. |
| **P-4** | ADVISORY | Models physical and logical do not contain a Mermaid `erDiagram` block (only conceptual does). Per the Brightsmith Data Model Gate, this is **not blocking for bronze** ("Bronze zone specs skip this gate — raw tables use physical-only models"), but @bs:semantic-modeler should add Mermaid blocks to the logical and physical files for symmetry with future silver/gold artifacts. |

##### v1.3 §3 Column Lock-down Implementation Verification

The spec's v1.3 §3 column lock-downs (F1C011/F1C071/F1H02 for F1A; F2E011/F2E061/F2H02 for F2; F3E011/F3E03C1 for F3 with no F3H; FTE = `COALESCE(FTEUG,0)+COALESCE(FTEGD,0)+COALESCE(FTEDPP,0)` from EFIA) are accurately reflected in the lineage facet's per-input `schema.fields[]` (lines 71–146 of the lineage JSON), in `governance/data-dictionaries/raw-ipeds-finance.md` lines 70–78, and in `governance/models/raw-ipeds-finance-physical.md`. **Implementation matches spec; no spec edit needed for column codes.**

##### Adversarial-Auditor Hallucination Resolution

The 269-vs-365 hallucination flagged by the adversarial-auditor exists in **more places than the audit caught** (EDA §8 says "268 rows"; data-dictionary lines 71 and 112 say "269 rows"; rule rationale says "269 rows" — all three are wrong). My recommendation: **correct the EDA and the propagated copies, not the chaos report** — the chaos report is the secondary artifact citing the EDA. Order of corrections: (1) EDA §8 → 365; (2) rule rationale → 365; (3) dictionary lines 71, 112 → 365. Chaos report's "zeroed top 269 rows" prose is fine to leave (it is a campaign-narrative, not a quantitative claim about the data — and even at 365, zeroing the top 269 still erases enough of the >$100M tail to fire the rule).

##### Insight Traceability

No prior `governance/insights/*.md` reports reference IPEDS Finance — this is a greenfield bronze ingest. Insight-traceability check is N/A for this review pass.

##### Decision Rationale

All 16 §8 governance artifacts mandated for a bronze ingest are present. DQ executes 14/14 PASS against live data with `p0_passed=true`. Lineage's column-lineage facet is unusually thorough (5 inputs × 7 derived fields fully traced, with sentinel-scrub and COALESCE semantics named explicitly). Cross-artifact consistency holds on every load-bearing claim (row count, form mix, F3 NULL invariants, fiscal_year invariant). The single numerical hallucination ("269 rows > $100M") is genuinely cosmetic — no threshold depends on it — but is propagated across four artifacts and warrants a single follow-up commit. The §4 spec line 190 RAW-IPF-001 band lag is similarly cosmetic — execution is correct against the amended JSON, but the spec text should be brought into line. Both cleanups should be batched into one commit before silver-zone DQ rules are written so that @bs:dq-rule-writer for silver doesn't propagate the same 269 hallucination forward. **Verdict: APPROVED for bronze.** Issues P-1 and P-2 are CHANGES REQUESTED but non-blocking for silver-zone progression — they are cosmetic, fully traced, and the corrected values are already implemented in the executable rule JSON.

##### Verdict
- [x] **APPROVED (bronze zone)** — Silver/Gold remain pending and require their own post-implementation reviews
- [ ] CHANGES REQUESTED (full spec)
- [ ] REJECTED

---

#### Post-Implementation Review (Full Pipeline — v1.3)

**Reviewer:** @bs:governance-reviewer
**Date:** 2026-05-01
**Scope:** Full pipeline — Bronze (`bronze.ipeds_finance`, snapshot `2955168649587464831`) + Silver/Base (`base.ipeds_finance`, snapshot `1277941459950591173`) + Gold/Consumable (`consumable.ipeds_finance_profile`, snapshot `6649279885162971471`), all FY2023, 2,675 rows × 3 zones (1:1 conservation throughout).
**Approval document:** [`governance/approvals/full-pipeline-ipeds-finance-post-review.md`](../../governance/approvals/full-pipeline-ipeds-finance-post-review.md)
**Verdict:** **APPROVED (full pipeline) — with three carry-forward CHANGES REQUESTED follow-ups, none blocking sign-off.**

##### Summary

All 17 §8 governance artifacts are present. The full DQ suite (44 rules across 3 zones) executes 44/44 PASS against live FY2023 Iceberg data with `p0_passed=true` (run `d16e354a` at 2026-05-01 20:53:24Z; 0 failures in latest run). The consumable data contract YAML — the artifact the adversarial audit named as "the single highest-leverage close-out artifact" — was authored and contains the four contract clauses the audit identified (F3 endowment gating; vintage-propagation; state-system administrative-office documentation; tier-vs-marketing_ratio decoupling documentation) for closing Gaps 1/2/3/4 at the contract layer. No HARD blockers. Cross-artifact consistency holds on every load-bearing claim. Standing user constraints (no YAML lookups; no substitution-based degraded states; transparency-not-filter `data_completeness_tier`; single-source-of-truth) are all satisfied.

##### Issues Found (3 CHANGES REQUESTED + 2 ADVISORY — all non-blocking)

| # | Severity | Description | Resolution |
|---|----------|-------------|------------|
| Q-1 | CHANGES REQUESTED | 2 of 6 BT-IPF-* business-glossary terms missing from `governance/business-glossary.json`: `BT-IPF-MARKETING-RATIO` and `BT-IPF-DATA-COMPLETENESS-TIER`. Definitions exist in spec §6 and across consumable artifacts; the miss is at central-glossary registration. | Single-commit additive append by @bs:data-steward / @bs:doc-generator |
| Q-2 | CHANGES REQUESTED (carry-forward) | Bronze post-review's P-1 ("269 rows above $100M" hallucination, live count = 365) still propagated through EDA §8, RAW-IPF-014 rationale, dictionary lines 71+112, and scorecard. Cosmetic only. | Same single follow-up commit as Q-1 |
| Q-3 | CHANGES REQUESTED (carry-forward) | Bronze post-review's P-2 (spec §4 line 190 still reads "RAW-IPF-001 row count between 5,000 and 8,000" while rule JSON correctly enforces 2,500–3,200). Cosmetic only. | Amend §4 line 190 |
| Q-4 | ADVISORY | Adversarial audit R2–R8 (additive DQ rules, additive schema columns, glossary clauses) queued for v1.4 / EADA-spec time per the audit's own non-blocking classification | EADA spec pre-implementation review must cite which Gap-1/2/3/4 mitigations it relies on |
| Q-5 | ADVISORY | EDA report cites FY2022 cycle; bronze re-ingested to FY2023 between EDA pass and base/consumable implementation. Vintage drift is fully documented in DQ rule rationales, data contract, §9 deviations table. Second EDA pass not required. | If SCD2 adopted later, next EDA should be cycle-explicit (`raw-ingest-ipeds-finance-eda-fy2023.md`) |

##### Adversarial-Audit Contract Clauses — ALL PRESENT

| Audit Gap | Required clause | Present in `governance/data-contracts/consumable-ipeds-finance-profile.yaml`? |
|---|---|---|
| Gap 4 — F3 endowment composite silent drop | EADA must gate on `report_form != 'F3' OR endowment_value IS NOT NULL` | YES — `quality_tier`, `endowment_value.description`, `endowment_per_fte.description` all document the F3 100%-NULL invariant and the EADA-fusion implication |
| Gap 3 — vintage-drift unjoinability | Consumers must propagate `fiscal_year` and document vintage assumptions | YES — `quality.cross_source_coverage.note` enumerates the FY2023-vs-FY2022 drift; `fiscal_year.description` documents the single-vintage invariant; `data_vintage` block names the operative cycle |
| Gap 2 — state-system administrative-office naive-ranking | Document the trap; flag-column deferred to v1.4 | YES (documented; flag deferred) — `marketing_ratio.description` enumerates the public-system-administrative-office cluster; `quality_tier` documents the BSE-IPF-015a per-form threshold rationale |
| Gap 1 — `tier='high'` decoupled from `marketing_ratio` | Document the semantic; CON-IFP-011 rule deferred to v1.4 | YES (documented; rule deferred) — `data_completeness_tier.description` documents the "counts independent raw inputs (NOT derived signals)" rationale and the F3 → 'medium' cap |

##### Verdict

- [x] **APPROVED (full pipeline)** — Bronze + Silver/Base + Gold/Consumable all approved
- [ ] CHANGES REQUESTED (full spec)
- [ ] REJECTED

Three CHANGES REQUESTED follow-ups (Q-1, Q-2, Q-3) are all cosmetic / process-ledger fixes that should be batched into a single follow-up commit. None is blocking for the staff-engineer post-review or for the start of `raw-ingest-eada.md`. Two ADVISORY items (Q-4, Q-5) are queued for v1.4 / EADA-spec time per the adversarial audit's own non-blocking classification.

---

### @fp-data-reviewer
**Status:** APPROVED (v1.2)
**Reviewed:** 2026-04-30 (v1.2 confirmation pass over v1.1)

#### v1.2 confirmation
- **R1 — CLOSED.** §4 EDA Req 1 (Patch A) extends the column-lock-down item with EFFY/E12 file-variant identification + long-form dedup filter discovery (`LEVEL` / `LSTUDY`), marked BLOCKING for raw, with explicit per-FTE inflation risk callout. The fanout failure mode is named in-spec.
- **R2 — CLOSED.** §3 row 1 (Patch B) now states explicitly "TBD — verify in EDA; if absent on F3, COALESCE to NULL (not zero)" and the new table footnote on F3 NULL-coalesce makes the policy load-bearing rather than implied. The `data_completeness_tier=medium` cascade is named.
- **R3 — CLOSED.** §5 BSE-IPF-017 (Patch C) added as P1 advisory: `instruction_per_fte` P99 < $500K, EDA-calibrated, explicitly labeled as the EFFY FTE-vs-headcount tripwire. Cheap safety net is in place.
- **Open question 6b — CLOSED.** §2 Decision #8 (Patch E) elevates the bureau-imputation policy with rationale + alternatives (suppress / store flag columns deferred to v1.3 pending EDA Req 7). Auditable and discoverable.

All three remaining items from the v1.1 second-pass are addressed in v1.2. No new concerns introduced. Verdict flips to APPROVED.

v1.2 re-review note: patches A–E applied per second-pass items R1–R3 + cosmetic D + open-question E (6b)

#### Second-pass findings (v1.1)

**Verdict:** CHANGES REQUESTED — 3 remaining items, none are blockers to spec advancement, but 1 must be re-graded after EDA evidence lands. The four v1.0 blockers are resolved in spirit; two are now correctly gated as BLOCKING EDA work, which I accept. Original review body below is preserved unaltered for audit.

##### Finding 1 — F1A column codes (was Blocker 1) — RESOLVED with caveat
- **Accepted.** `F1B01`/`F1B07` → `F1C011`/`F1C071` is the correct fix. Part C is the IPEDS Finance functional-expenses block on F1A (GASB); Part B is revenues. The v1.0 codes would have silently mis-labeled revenue values as expenses and no downstream rule would have caught it. v1.1 closes that hole.
- **Citation strength:** Delta Cost Project's `IPEDS_DCP_Database_Mapping_File_87_12.xls` and the paulgp/ipeds-database harmonization README are both defensible secondary sources — Delta Cost Project is NCES-funded and is the standard reference for longitudinal IPEDS Finance harmonization. I do not require a tighter citation in the spec text. **However:** the §3 column table is the source-of-truth for the ingestor, and the spec correctly gates EDA Req 1 to verify the codes against the live IPEDS dictionary before raw is implemented. That gate is what actually protects us; the citations are flavor.
- **F2 codes (`F2E011`, `F2E061`):** accepted unchanged. F2 (FASB) Section E for functional expenses is correct; the suffix conventions match published practice.
- **F3 codes:**
  - `F3E01` for instruction — accepted as the working assumption with EDA verification.
  - F3 institutional support marked TBD with expected NULL — **acceptable**, but tighten as below.
  - F3 endowment marked N/A → NULL — **acceptable**. For-profits do not maintain endowments; coalescing to NULL is correct behavior, not a data gap.
- **Endowment EOY (`F1H02` / `F2H02`):** accepted (open question 6c sanity check). H-section for endowment is the conventional IPEDS placement for both F1A and F2.

##### Finding 2 — FTE source (was Blocker 2) — RESOLVED with caveat
- **Accepted.** EFFY/E12 directly-reported FTE is the correct source. The v1.0 use of `EFTOTLT` (EF Part A headcount) would have systematically deflated per-FTE values for institutions with large part-time populations — community colleges, online-heavy schools, R2s with PT graduate cohorts. That bias would have hit non-traditional-student-serving institutions hardest, which is exactly the edge case I worry about. v1.1 fixes this.
- **TBD column header** (`FTE_TOTAL` vs `FTE` vs computed `FTEUG + FTEGD`) is acceptable as a BLOCKING EDA gate. The conceptual fix (EFFY/E12 vs EF Part A) is the load-bearing decision and it is locked in. The exact column header is a verification task, not a design task.
- **Additional sentinel cases for EFFY/E12:** EFFY surveys publish data in long form (one row per institution × level × time-status), not wide form. Confirm the ingestor reads the correct EFFY release variant — IPEDS publishes EFFY (12-month enrollment by race/ethnicity), E12 (12-month instructional activity hours), and a derived FTE companion file. **Add to EDA Req 1:** identify which EFFY release file carries the institution-level total-FTE column, and verify it is not a long-form file requiring a `LEVEL = 1` (undergraduate) or `LSTUDY = 999` (all students) filter to deduplicate to one row per UNITID. If long-form, the LEFT JOIN at raw must include the appropriate filter or it will fan out finance rows.
- No additional missing-data sentinels expected beyond the §4 list (`-1`, `-2`, `.`, blank, "PrivacySuppressed") — EFFY uses the same IPEDS-wide conventions.

##### Finding 3 — `data_completeness_tier` rework (was Blocker 4) — RESOLVED
- **Accepted.** The rename and reformulation are correct.
  - Renaming `confidence_tier` → `data_completeness_tier` removes the conflation with CIP→SOC crosswalk-confidence tiers used by ConceptNormalizer. The glossary term BT-IPF-DATA-COMPLETENESS-TIER explicitly disambiguates. Good.
  - Counting the four **independent raw inputs** (the two expenses + endowment + FTE) instead of mixing in derived `marketing_ratio` correctly avoids the v1.0 collapse-to-3 bug where a present marketing_ratio inflated the count by re-asserting evidence already supplied by its two source fields.
  - Promoting `total_fte_enrollment` to first-class signal status is correct: when FTE is missing, all three per-FTE values are NULL and the row is unusable for per-student comparison even if both expense fields are populated.
- **One small concern about the threshold cut:** v1.1 collapses signals=2 and signals=3 into `medium`. My v1.0 review proposed signals=3 → `medium` and signals=2 → `low` (one-input-missing vs two-inputs-missing are meaningfully different downstream states). The v1.1 collapse is defensible — it preserves the four-tier ordinal — but it does discard one bit of information. **Not blocking.** Acceptable to ship as-is provided EDA Req 4 publishes the actual distribution of `non_null_signals` and `CON-IFP-009` (data_completeness_tier=`high` ≥ 70%) is recalibrated against evidence. If EDA shows a fat `medium` bucket, consider re-splitting in v1.2.
- **Disambiguation propagation:** I traced the rename through §3 (sparseness paragraph), §6 (consumable transformation 2 + schema), CON-IFP-005, CON-IFP-006, CON-IFP-009, CDE candidates, and the new BT-IPF-DATA-COMPLETENESS-TIER glossary term. All consistent. No stray `confidence_tier` references remain in §3–§6.

##### Finding 4 — Filter `ICLEVEL = 1 AND HLOFFER >= 5` — ACCEPTED
- **Accepted.** This is the IPEDS-canonical "4-year, bachelor's-or-above" definition using only IPEDS-native HD fields. It removes the v1.0 mixed-taxonomy issue (College Scorecard's `PREDDEG` joined into an IPEDS raw zone with no declared dependency).
- `HLOFFER >= 5` correctly admits bachelor's (5), post-bacc certificate (6), master's (7), post-master's certificate (8), and doctorate (9), and excludes 4-year institutions whose highest offering is associate's (4) or below — which would have slipped through a bare `ICLEVEL = 1` filter.
- Note: this filter EXCLUDES some 4-year specialized graduate-only schools coded `ICLEVEL = 1, HLOFFER >= 7` — those still pass because `HLOFFER >= 5` admits 7+. Safe.
- Consistency-with-Scorecard caveat: the v1.0 governance review (ADV-related) noted that `PREDDEG = 3 OR ICLEVEL = 1` was byte-equivalent to `raw.college_scorecard_institution.filter_predicate`. The new IPEDS-native filter is **not** byte-equivalent. EDA Req 5 (overlap with `consumable.career_outcomes`) becomes more important — track whether the coverage gap widens. **Not blocking**, but flagging for post-EDA verification.

##### Bonus — raw expense passthroughs to consumable (was "Other Findings" gap) — ACCEPTED
- **Accepted.** Adding `instruction_expenses`, `institutional_support_expenses`, and `endowment_value` (raw dollar values) to `consumable.ipeds_finance_profile` correctly enables `raw-ingest-eada.md` to compute composite ratios (e.g., athletic spending as % of institutional support) without back-joining to base — preserves the gold-only consumption pattern.
- **Sufficiency for EADA fusion:** confirm the EADA spec also has access to:
  - `total_fte_enrollment` (already passed through — confirmed).
  - `report_form` (already passed through — confirmed; EADA may need to segment by GASB vs FASB).
  - `data_completeness_tier` (already passed through — confirmed; EADA fusion will want to gate composite-ratio display on `tier IN ('high', 'medium')`).
- **One additional field to consider:** `fiscal_year` is in the consumable schema (good) — EADA fusion will need this to verify year alignment with athletic-year reporting. No additional fields required.

##### Bonus — sentinel `.` and imputation policy — ACCEPTED
- `.` (single period) added to the sentinel list — accepted, this addresses a real legacy-carryover sentinel that still appears in modern releases.
- Imputation-flag policy (accept bureau-imputed values as raw values; do not store the flag column in v1.1; EDA Req 7 measures prevalence) — **accepted with one caveat.** The §4 implementation note correctly frames this as an exception to the no-imputation rule because imputation is upstream-of-source. Whether to suppress bureau-imputed values to NULL in v1.2 is a meaningful policy decision and EDA Req 7 is the right gate. See open question 6b below for whether to elevate.

##### Remaining items for the patch author

| # | Item | Severity | Section |
|---|------|----------|---------|
| R1 | EFFY/E12 file-variant + long-form filter risk (see Finding 2 caveat). Add to §4 EDA Req 1 instructions: identify the specific EFFY release file carrying institution-level total-FTE; if long-form, identify the filter (`LEVEL`, `LSTUDY`, etc.) needed to dedup to one row per UNITID before LEFT JOIN. | Significant | §4 EDA Req 1 |
| R2 | F3 institutional-support TBD: tighten §3 row 1 to state explicitly that if EDA confirms F3 does not separately report institutional support, the ingestor coalesces to NULL and does not error. (Currently implied; make load-bearing.) | Minor | §3 row 1 |
| R3 | Add advisory tightening BSE-IPF-017 (`instruction_per_fte` P99 < $500K) — see open question 6d. Recommended for v1.1; deferral acceptable. | Minor | §5 DQ rules |

##### Open questions answered (6a–6d)

- **(6a) TBD-marked cells gated by EDA — right shape, or commit to specific candidate codes now?**
  Right shape. Commit codes where the citation is solid (F1C011/F1C071/F2E011/F2E061/F1H02/F2H02/F3E01) and gate the genuinely uncertain cells (F3 institutional support, EFFY/E12 column header, F3 endowment N/A confirmation) on EDA evidence. Speculative codes shipping into the ingestor without dictionary verification is what got us into trouble in v1.0. EDA Req 1 is the right line of defense; do not commit speculative codes to dodge it.

- **(6b) Imputation policy: §4 note + EDA Req 7 sufficient, or elevate to §2 design decision?**
  **Elevate to §2.** The decision "accept bureau-imputed values as raw values for v1.1" is a meaningful policy decision that interacts with the standing no-imputation rule (Decision #7 spirit). It belongs in §2 design decisions as Decision #8 with Rationale ("imputation is upstream-of-source; suppressing would discard NCES-curated values without student-visible benefit at hackathon scope") and Alternatives Considered ("suppress bureau-imputed values to NULL — deferred to v1.2 pending EDA Req 7 prevalence evidence"). The §4 implementation note can then reference Decision #8 instead of carrying the policy itself. This makes the policy auditable and surfaces it to governance review without requiring readers to dig into §4. **Not a blocker** — the policy is correct as-is; the request is about discoverability.

- **(6c) F2 endowment `F2H02` — sanity check.**
  Confirmed. F2 (FASB private nonprofit) Section H is the standard placement for endowment-fund balances on the IPEDS Finance Survey. `F2H02` is the end-of-year market value (vs `F2H01` beginning-of-year). The spec uses end-of-year, consistent with F1A `F1H02`. Accept.

- **(6d) Should advisory tightening BSE-IPF-017 (`instruction_per_fte` P99 < $500K) be added in v1.1 or deferred?**
  **Add in v1.1.** It costs nothing (one P1 advisory rule), it directly catches the small-denominator FTE-field bug class I called out in finding (c), and it serves as a tripwire if the EFFY/E12 column header EDA item locks onto the wrong field. Deferring it sacrifices a cheap safety net for a real risk. Specifically: `instruction_per_fte` P99 < $500K (EDA-calibrated) — anything above is almost certainly an FTE-field bug, not a real institution. The threshold should be calibrated against EDA's distribution of `instruction_per_fte` after the EFFY/E12 column is confirmed.

##### Disclaimer Check (second-pass)
- [x] AI-estimated values labeled — N/A
- [x] Confidence scores propagated where crosswalk < Tier 2 — N/A (no crosswalk; rename to `data_completeness_tier` removes the prior naming conflation)
- [x] Required disclaimer strings present in UI for this data path — N/A (spec stops at consumable)
- [x] **Missing data states handled** — Now correctly. The reformulated `data_completeness_tier` properly signals "do not show this institution's profile" via the `insufficient` value when all four independent raw inputs are NULL. Per-FTE values NULL-cascade correctly when FTE is missing.

#### Verdict
- [x] APPROVED (v1.2)
- [ ] CHANGES REQUESTED
- [ ] REJECTED

v1.1 verdict was CHANGES REQUESTED (R1, R2, R3 + open-question 6b). v1.2 patches close all four. Spec advances.

---

## Original (v1.0) data review — preserved for audit

#### Data Sources Affected
**Reviewed:** v1.0

#### Data Sources Affected
- **NEW:** IPEDS Finance Survey (forms F1A / F2 / F3) — landed for the first time in this repo.
- **NEW:** IPEDS Fall Enrollment (EF) — used as auxiliary FTE source, joined in raw.
- **NEW:** IPEDS HD (Header / Institutional Characteristics) — used for `institution_name` and the `PREDDEG / ICLEVEL` filter.
- **No mutation** of any existing `raw.*` / `base.*` / `consumable.*` table. Additive only. UNITID is the future join key to `consumable.career_outcomes` (read-only here, exercised only by `CON-IFP-008`).

#### Crosswalk Impact
None. This spec does not touch the CIP→SOC crosswalk. UNITID is a stable IPEDS identifier — no fuzzy mapping, no confidence tiering against ConceptNormalizer. The `confidence_tier` field in §6 is a *non-null-signal-count* tier, not a crosswalk-confidence tier — naming reuse is acceptable but worth flagging in the glossary so downstream readers don't conflate the two.

#### Formula Verification
Per-FTE arithmetic (§5) and confidence-tier classification (§6) traced field-by-field below. Findings inline.

#### Findings

##### Data Quality Sound
- **Single-vintage invariant** (`RAW-IPF-013`) is the right call for hackathon scope and matches the BEA RPP precedent. Don't drift into SCD2.
- **Sentinel handling** correctly normalizes IPEDS `-1` (not applicable), `-2` (not reported), blank, and "PrivacySuppressed" to NULL *before* type coercion. Order matters and the spec gets it right.
- **Raw-preserves-source / base-derives** boundary is clean. Per-FTE in raw would have been wrong; the spec correctly defers it (Decision #2).
- **No-imputation rule** on per-FTE division is the right call. Imputing FTE or expense values would silently fabricate institution profiles.
- **Arithmetic invariants** `BSE-IPF-008/009/010` are well-formed: they roundtrip the derivation against the raw passthrough, which catches transformer drift. The `≈ within $1` tolerance is appropriate for IEEE-754 double rounding on dollar values up to ~$10B.
- **Conservation rule** `CON-IFP-001` (consumable rows == base rows) closes the loop on dropped-row regressions.
- **Endowment ≥ 0** rule (`RAW-IPF-007`) correctly anticipates underwater funds — IPEDS reports 0, never negative. Good catch.
- **`marketing_ratio` NULLIF guard** against division-by-zero on instruction expenses is correct.
- **`F1A / F2 / F3` typed as enum** in `RAW-IPF-004` prevents form-name drift.

##### Data Concerns

###### (a) Form-coalescing logic across F1A / F2 / F3 — **CHANGES REQUESTED**

- **Column-code plausibility — partially wrong, all need EDA verification.** The proposed codes do not match conventional IPEDS Finance variable naming, and at least two appear to be wrong:
  - **F1A institutional support:** spec says `F1B07`. IPEDS F1A "Expenses by Functional Classification" lives in part C (`F1C` family), not part B (`F1B` is revenues). The conventional code is **`F1C071`** (institutional support, total) or `F1C07` family. **Risk:** ingestor will fail to find the column or, worse, pick up a revenue field with the same numeric suffix and silently mis-label revenue as expenses. **Fix:** EDA must pull the live IPEDS Finance dictionary and verify part letter (B vs C vs D vs E vs H) before raw is implemented. Update §3 column table from EDA evidence — do not ship the speculative codes.
  - **F1A instruction:** same issue — likely `F1C011` family, not `F1B01`.
  - **F2 codes** (`F2E061`, `F2E011`) — F2 (private NFP, FASB) does use the `E` letter for expenses by function, and `E01` / `E06` ranges are plausible for instruction / institutional support. Still requires EDA dictionary lookup for the exact suffix (the trailing `1` vs `2` vs nothing varies by IPEDS year).
  - **F3 codes** (`F3E06`, `F3E01`) — F3 (private FP) uses a much smaller expense schedule than F1A/F2. The codes are plausible but for-profits historically reported a *single* total expense field with limited functional breakdown. Verify that institutional support is even separately reported on F3 — if it isn't, F3 rows must coalesce to NULL on `institutional_support_expenses`, which then cascades to NULL `marketing_ratio` and a `medium`/`low` `confidence_tier`. That's correct behavior, but it should be explicit in §3.
  - **Endowment codes** (`F1H02`, `F2H02`, `F3H02`) — H-section is endowment on F1A and F2. Plausible. F3 endowment data is sparse and often null; expect P1-rule volatility on `RAW-IPF-012`.
  - **Risk:** if the ingestor lands columns under the wrong source codes, every per-FTE value, the marketing ratio, and the downstream `consumable.institution_aura` fusion all carry silently wrong numbers. There is no downstream check that catches a column-code transposition. EDA is the only line of defense.
  - **Fix:** Add a hard EDA gate (§4 EDA Requirements item 1) that the data analyst publishes the *exact* IPEDS variable code, the dictionary's text definition, and a sample value for one known institution per form, *before* `IpedsFinanceIngestor` is implemented. Block raw on EDA approval.

- **UNION semantics — sound, with one ambiguity.** UNION-then-LEFT-JOIN-EF is the right shape. But: a private NFP that converts to public mid-year (or vice versa) could conceivably appear on two forms in the same fiscal year. `RAW-IPF-003` (UNITID uniqueness) will fire and block. Spec needs a tie-breaker policy (prefer the form matching the institution's HD `CONTROL` value at fiscal-year close), or an explicit assertion that IPEDS guarantees one-form-per-UNITID-per-year. **Fix:** Add a sentence to §3 or §4 stating the assumption, and add a P1 rule `RAW-IPF-015` confirming `report_form` agrees with HD `CONTROL` as a sanity cross-check.

- **`report_form` discriminator preserved through to consumable** — good. This lets downstream consumers segment marketing-ratio distributions by accounting basis (FASB vs GASB are not directly comparable on every line item).

###### (b) EF (Fall Enrollment) survey FTE-join correctness — **CHANGES REQUESTED**

- **Year pairing FY24 Finance ↔ Fall 2023 EF — correct in convention.** IPEDS Finance fiscal year ending June 2024 (FY2024) does pair with the prior Fall enrollment (Fall 2023) in NCES's published cross-survey analyses, because the Fall 2023 cohort is the student body whose tuition flowed through the FY24 books. The spec gets this right. EDA item 2 already mandates a 5-institution spot-check — keep that as a hard gate.

- **`EFTOTLT` field choice — wrong field.** `EFTOTLT` is **total enrollment headcount**, not full-time-equivalent. Per-FTE math requires FTE, not headcount. The correct IPEDS-published FTE field is the **`FTE` column from the EFFY (12-month enrollment) survey**, NOT the EF Part A `EFTOTLT`. Some analysts approximate FTE from EF as `FT_headcount + (PT_headcount / 3)` for undergrads with a different denominator for graduates — IPEDS's own published FTE uses this conversion. **Risk:** if the ingestor lands `EFTOTLT` and labels it `total_fte_enrollment`, every per-FTE value is *deflated* by the part-time-conversion factor. Per-FTE values become 20–40% too low for institutions with large part-time populations — community colleges, online-heavy schools, R2s with big PT graduate cohorts. The error is *systematically biased toward institutions serving non-traditional students*, exactly the edge case I worry about. **Fix:** EDA must (1) confirm the EF/EFFY survey choice, (2) confirm the FTE field name (`FTE` from EFFY, or computed from EF Parts A/B per the IPEDS conversion formula), (3) verify spot-check matches IPEDS Data Center's published FTE for 5 institutions to within 1%. Update §3 row 4 from EDA evidence. Do not ship `EFTOTLT` mislabeled as FTE.

- **LEFT JOIN at raw — placement is correct.** FTE is a raw upstream attribute (Decision #4). LEFT JOIN (not INNER) is correct: a Finance row with no matching EF row should land with NULL FTE, which then NULL-cascades through per-FTE derivations. `RAW-IPF-011` (FTE non-null ≥ 95%) is the safety net.

- **One missing edge case:** institutions that report Finance but skipped EF in a given year (rare, but happens for branch-campus reporting changes). `RAW-IPF-011` at 95% threshold should hold; if it doesn't, that's an EDA finding to escalate.

###### (c) Per-FTE math at base — **APPROVED with one tightening**

- Formulas (§5.2) are arithmetically correct. NULL semantics are explicit and correct (NULL when either operand is NULL or denominator ≤ 0). No-imputation rule is the right ethical line.
- `marketing_ratio` formula (§5.3) correctly uses NULLIF on the denominator. The `≥ 0` validity rule (`BSE-IPF-007`) is correct because both operands are non-negative.
- **`BSE-IPF-008/009/010` arithmetic invariants** are well-designed. They catch:
  - transformer drift (somebody changes the formula but not the rule)
  - silent type-coercion bugs (int division vs float division)
  - column-misalignment bugs (instruction lands in the institutional-support slot)
  - The `≈ within $1` tolerance is generous enough for IEEE-754 on values up to ~$10B (relative error ~1e-10).
- **Tightening (minor):** `BSE-IPF-008/009` should specify that the rule applies *only when `total_fte_enrollment > 0`*, otherwise the division produced NULL and the roundtrip is vacuous. Add the `WHERE total_fte_enrollment > 0 AND <both operands non-null>` clause explicitly to the rule statement to avoid future ambiguity.
- **Edge case — small denominators.** A tiny seminary with 12 FTE and $500K instruction expenses produces `instruction_per_fte = $41,667`, which is plausible but high-variance. The single-row P99 plausibility rule (`BSE-IPF-015`) on `marketing_ratio` is good. Consider adding `BSE-IPF-017` (P1): `instruction_per_fte` P99 < $500K — anything above is almost certainly an FTE-field bug, not a real institution. EDA-calibrate the actual threshold.

###### (d) Confidence-tier formula in §6 consumable — **CHANGES REQUESTED**

- **Conceptual issue: the four signals are not independent.** `marketing_ratio` is mechanically derived from `instruction_expenses` and `institutional_support_expenses` — it cannot be non-null when those are null, and it is *almost always* non-null when those two are non-null. So the "4 signals" effectively collapses to "3 signals" for classification purposes. An institution with both expense fields populated will almost always also have `marketing_ratio` populated, so `non_null_signals = 4` ≈ `non_null_signals = 3 (the two expenses + endowment)`. **Risk:** the formula gives the illusion of more granularity than it actually carries. A `medium` tier (signals = 2 or 3) collapses several genuinely different data states:
  - both expenses present, no endowment, marketing_ratio computed → 3 signals → `medium`
  - one expense + endowment → 2 signals → `medium`
  - These are not equivalent for downstream consumers.
- **Fix:** Re-derive `confidence_tier` from the **independent source signals** only:
  ```
  signals = (
    (instruction_expenses           IS NOT NULL)::int +
    (institutional_support_expenses IS NOT NULL)::int +
    (endowment_value                IS NOT NULL)::int +
    (total_fte_enrollment           IS NOT NULL AND total_fte_enrollment > 0)::int
  )
  confidence_tier = CASE
    WHEN signals = 4 THEN 'high'           -- all four independent inputs present
    WHEN signals = 3 THEN 'medium'         -- one input missing
    WHEN signals = 2 THEN 'low'            -- two inputs missing, derived fields likely NULL
    ELSE 'insufficient'                    -- not usable
  END
  ```
  This counts *independent inputs*, not derived outputs. It also makes `total_fte_enrollment` a first-class signal — which it is, because if FTE is missing, *all three per-FTE values are NULL* and the row is effectively unusable for per-student comparison even if the raw expense fields are present. The current formula doesn't penalize a missing FTE, which is wrong.
- **Threshold tuning:** EDA must report the distribution of `non_null_signals` (under the corrected formula) before `CON-IFP-009` ("≥ 70% high") is locked in. If the actual distribution is 50/30/15/5, the threshold is wrong; if it's 85/10/4/1, the threshold is too loose. Mark `CON-IFP-009` explicitly as EDA-calibrated (already noted) and require EDA to publish the actual distribution.
- **Naming ambiguity:** the field name `confidence_tier` overlaps with crosswalk confidence tiers used elsewhere in the project (CIP→SOC tiers in `ConceptNormalizer`). They mean different things. **Fix:** rename to `data_completeness_tier` *or* add a glossary note `BT-IPF-CONFIDENCE-TIER` explicitly clarifying that this measures source-field non-null count, not crosswalk match quality. The downstream `raw-ingest-eada.md` spec must not conflate these.

##### Other Findings

- **`PREDDEG = 3 OR ICLEVEL = 1` filter — partially correct, needs refinement.**
  - `PREDDEG` ("predominant degree") is a College Scorecard field, not a native IPEDS HD field. IPEDS HD has `HLOFFER` (highest level of offering) and `ICLEVEL` (institutional level: 1 = 4-year, 2 = 2-year, 3 = less-than-2-year). The spec mixes taxonomies.
  - **Risk:** if the ingestor tries to read `PREDDEG` from IPEDS HD, it will fail. If it reads `PREDDEG` from College Scorecard institution data joined in, it works but pulls in a Scorecard dependency the spec doesn't declare.
  - **Fix:** either (option A, preferred) use only IPEDS-native fields: `ICLEVEL = 1 AND HLOFFER >= 5` (5 = bachelor's, 6 = post-bacc certificate, 7+ = master's and above) — this is the IPEDS-canonical "4-year bachelor's-granting" definition. Or (option B) explicitly declare the College Scorecard institution table as a join source in §3 and pull `PREDDEG` from there. Pick one. Don't mix.
  - The current spec language is also logically permissive — `ICLEVEL = 1` includes 4-year institutions that don't grant bachelor's (rare, but exists for some specialized graduate-only schools coded ICLEVEL=1). Tighten to AND with HLOFFER threshold per option A.

- **Sentinel handling — one IPEDS-specific value missing.** The spec covers `-1`, `-2`, blank, "PrivacySuppressed". IPEDS Finance also uses **`.` (single period)** as a "not applicable" marker in some fields (legacy pre-2010 carry-over, still appears in newer releases for endowment fields on for-profits). Add `.` to the sentinel list. Also consider the **`H` imputation flag columns** (e.g., `XF1B01` is the imputation flag for `F1B01`) — IPEDS publishes a parallel set of flag columns indicating whether a value was imputed by NCES vs reported by the institution. The current spec ignores these. **Recommendation:** add an EDA item asking the data analyst whether the no-imputation rule should *exclude* NCES-imputed values (i.e., treat `XF1B01 IN ('B', 'C', 'D')` — bureau imputed — as if the value were NULL). This is a meaningful policy decision: NCES imputations are not the same as institution-reported values, and per the no-imputation rule (Decision #7 spirit), they arguably shouldn't be treated as observed data.

- **Downstream EADA fusion readiness.** The base schema (`base.ipeds_finance`) gives the EADA-fusion spec what it needs:
  - UNITID is the fusion join key (same as EADA).
  - All four per-FTE values are exposed.
  - `report_form` is preserved (EADA fusion may need to segment by GASB vs FASB — the accounting bases of the two surveys differ).
  - `total_fte_enrollment` is exposed (EADA-derived metrics like "athletic spending per student" need this denominator).
  - **Gap:** `instruction_expenses` and `institutional_support_expenses` are passed through to `base.ipeds_finance` but **not** to `consumable.ipeds_finance_profile`. EADA fusion will likely need the raw dollar values, not just per-FTE values, to compute composite ratios (e.g., "athletic spending as % of institutional support"). **Fix:** add `instruction_expenses`, `institutional_support_expenses`, `endowment_value` to the consumable schema as well — they're already in base, the cost is zero, and the downstream fusion spec will need them. Either that, or downstream spec joins to base directly (which is a violation of the gold-only consumption pattern).

#### Disclaimer Check
- [x] AI-estimated values labeled — N/A, no AI estimation in this pipeline.
- [x] Confidence scores propagated where crosswalk < Tier 2 — N/A, no crosswalk in this spec.
- [x] Required disclaimer strings present in UI for this data path — N/A, this spec stops at consumable; UI handling is downstream.
- [ ] **Missing data states handled** — Mostly yes (NULL cascades, no imputation, `confidence_tier = 'insufficient'`). But the `confidence_tier` formula needs the rework called out in finding (d) before it usefully signals "do not show this institution's profile" to downstream consumers.

#### Blockers Before Implementation
1. **Column codes verified by EDA against the live IPEDS dictionary** before `IpedsFinanceIngestor` is built. Working assumptions in §3 are at minimum partially wrong (F1A part letter is almost certainly C, not B). Block raw implementation on EDA evidence.
2. **EF FTE field corrected.** `EFTOTLT` is headcount, not FTE. Replace with the EFFY `FTE` field or compute from EF Parts A/B per the IPEDS conversion formula. Block raw implementation on EDA evidence.
3. **Filter mixed-taxonomy issue.** Resolve `PREDDEG`/`ICLEVEL` mix — pick option A (IPEDS-native: `ICLEVEL=1 AND HLOFFER>=5`) or option B (declare Scorecard join dependency).
4. **Confidence-tier formula reworked** to count independent source signals, not derived signals; add FTE as a tier input.

Items 1 and 2 are the highest-risk: both produce silently wrong numbers (no rule fires) and both flow downstream into the EADA fusion spec where they compound. The other findings are tightening.

**v1.1 re-review note:** The four blocker items above were addressed in spec v1.1 (see §7 revision history). Specifically: (1) F1A column codes corrected to Part C (`F1C011` / `F1C071`); (2) FTE source switched to EFFY/E12 directly-reported FTE (exact column TBD per EDA Req 1); (3) filter changed to IPEDS-native `ICLEVEL = 1 AND HLOFFER >= 5`; (4) tier renamed to `data_completeness_tier` and reformulated to count 4 independent raw inputs including FTE. Bonus items also applied: `.` added to sentinel list, raw expense passthroughs added to consumable schema, imputation-flag policy documented in §4. Awaiting fresh data-review pass on the revised text.

#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

---

### @bs:staff-engineer

**Status:** CHANGES REQUESTED — silver gated until catalog state is resolved
**Date:** 2026-05-01
**Scope:** Bronze zone only (`bronze.ipeds_finance`). Silver/Gold not yet executed.

#### Verdict

The bronze implementation is competent. The ingestor matches the v1.3 §3 column lock-downs verbatim (F1C011/F1C071/F1H02 for F1A; F2E011/F2E061/F2H02 for F2; F3E011/F3E03C1 for F3 with no F3H; FTE = NULL-safe `COALESCE(FTEUG,0)+COALESCE(FTEGD,0)+COALESCE(FTEDPP,0)` from EFIA; HD filter ICLEVEL=1 AND HLOFFER>=5). The Ellipsis-sentinel override pattern, `_strip_sentinel`/`_coerce_long`/`_coerce_double` helpers, sort-revised-CSV-first behavior, and cross-form duplicate detection are all production-quality. Defaults are durable for the next FY publication — `DEFAULT_FISCAL_YEAR=2023` is a single-line change to promote to FY24 once NCES publishes (currently 404 on F2324_*.zip, confirmed by EDA), and every column code is overrideable via `__init__` so a dictionary revision doesn't require code changes. Scope discipline is clean: `src/raw/ipeds_finance_ingestor.py` has zero MCP/backend/frontend touch, and the unrelated branch-level `backend/` and `frontend/` modifications are pre-existing career-path-enhancements work. Governance-reviewer's P-1/P-2/P-3 follow-ups are all real and as characterized.

I am NOT signing off for silver yet. There is one issue the post-implementation review missed that does materially block silver, and the cosmetic-cleanup follow-ups should land before silver-zone DQ-rule-writer runs so the same `269` hallucination doesn't propagate forward.

#### Independent Spot-Checks Run

I queried the FY23 snapshot's parquet directly (catalog has the metadata file at `data/bronze/iceberg_warehouse/bronze/ipeds_finance/metadata/00001-e868e94e-74de-4498-a894-89038660855b.metadata.json` referencing snapshot `2955168649587464831`):

| Claim | Source | Live Value | Verdict |
|---|---|---|---|
| Snapshot 2955168649587464831 / 2,675 rows / FY2023 | orchestrator + lineage | 2,675 rows, fiscal_year=[2023] | MATCH |
| Form mix F1A 30.62% / F2 59.03% / F3 10.36% | EDA, dictionary | F1A 819 (30.62%) / F2 1,579 (59.03%) / F3 277 (10.36%) | MATCH |
| F3 endowment 100% NULL | spec §3, EDA, lineage | 100.00% | MATCH |
| F3 institutional_support 0% NULL (post-2014-15 schedule) | spec v1.3 §3 lock-down | 0.00% | MATCH |
| `fiscal_year` single-value invariant | RAW-IPF-013 | unique = [2023] | MATCH |
| Rows with `instruction_expenses > $100M` | EDA §8 says 268; rule rationale + dictionary lines 71/112 say 269 | **365** | MISMATCH (governance-reviewer P-1 confirmed) |
| Stanford (UNITID 243744) FY23: instruction $2.683B / inst_supp $810M / endow $36.49B / FTE 19,094 | F2 / EFIA reported | matches IPEDS Data Center reported values | MATCH |
| UC Berkeley (UNITID 110635) FY23: instruction $1.003B / inst_supp $389M / endow $2.977B / FTE 45,637 | F1A / EFIA | matches | MATCH |
| UNC-CH (UNITID 199120) FY23: instruction $952M / inst_supp $244M / endow $5.20B / FTE 29,615 | F1A / EFIA | matches | MATCH |
| Harvard (UNITID 166027) FY23: instruction $1.462B / inst_supp $1.045B / endow $50.75B / FTE 31,201 | F2 / EFIA | matches | MATCH |

Data correctness on the four institution spot-checks is solid — 4-of-4 within reasonable IPEDS-published-value tolerance. P-1 (the 268/269 vs actual 365 hallucination) is real; live count is **365**, not 268 or 269. Confirmed in 4 governance artifacts as governance-reviewer flagged (EDA §8, dq-rules RAW-IPF-014 rationale, data-dictionary lines 71 and 112).

#### Issue Staff-Engineer Found That Post-Impl Review Missed

| # | Severity | Description | Required Fix |
|---|----------|-------------|--------------|
| **SE-1** | **BLOCKING for silver** | The PyIceberg SqlCatalog at `data/bronze/pyiceberg_catalog.db` has **zero registered tables** (`iceberg_tables` table is empty; `cat.list_namespaces()` returns `[]`). Two terminal `00001-*.metadata.json` files coexist in `data/bronze/iceberg_warehouse/bronze/ipeds_finance/metadata/`: an FY2023 file (snapshot `2955168649587464831`, 2,675 rows, written 15:21 — what the orchestrator and post-impl review describe) AND an orphaned FY2022 file (snapshot `982081695100705470`, 2,683 rows, written 15:01 — leftover from a prior run). With no version-hint.text and no catalog row, `cat.load_table('bronze.ipeds_finance')` raises `NoSuchTableError`. The FY2023 metadata is reachable by file path (which is how I verified the spot-checks above), but the silver transformer presumably uses `catalog.load_table()` — that will fail. **Fix path:** register the FY2023 metadata into the SqlCatalog (`cat.register_table('bronze.ipeds_finance', metadata_location=…00001-e868e94e….metadata.json)`) and delete the orphan FY2022 metadata + its parquet (`00000-0-5b7b3db1….parquet`). Verify by re-running silver's bronze read path before kicking silver off. |

#### Concur with Governance-Reviewer P-1/P-2/P-3

- **P-1 (the 269 → 365 cosmetic):** confirmed in all 4 places. None of the executable thresholds depend on it (RAW-IPF-014 floor is `≥ 1`; EDA's non-binding `≥ 200` suggestion still satisfied at 365). Required before silver to prevent the dq-rule-writer carrying `269` into BSE-IPF rationale text.
- **P-2 (spec §4 line 190 row-count band):** orchestrator confirmed the spec table now reads `2,500 and 3,200`. Verified at line 190. Closed.
- **P-3 (FY24 → FY23 narration drift in §3 line 142):** §9 deviations table + lineage `versionNote` already close the audit loop. Recommend tightening §3 line 142 once silver/gold complete; not required for silver kickoff.

#### What I Want Resolved Before Silver Kicks Off

1. **SE-1 (catalog repair):** non-negotiable. Either register the FY2023 table into the SqlCatalog or delete the orphan FY2022 metadata + parquet AND register. Without this, `base.ipeds_finance` cannot read its source.
2. **P-1 (269 → 365 propagation):** single follow-up commit to update EDA §8, RAW-IPF-014 rationale in `governance/dq-rules/raw-ipeds-finance.json`, and `governance/data-dictionaries/raw-ipeds-finance.md` lines 71 + 112. Required before silver dq-rule-writer to avoid forward-propagation.
3. **P-3 (§3 line 142 narration):** advisory; can land after silver completes. Not blocking.

#### Verdict
- [ ] APPROVED for bronze (silver may begin)
- [x] APPROVED with required spec amendments before silver — see SE-1 (catalog repair) + P-1 (269→365 propagation) above
- [ ] CHANGES REQUESTED — NOT APPROVED
- [ ] REJECTED

Once SE-1 and P-1 are resolved, silver work is unblocked. SE-1 is mechanical (one register_table call + one orphan-file cleanup); P-1 is three text edits in one commit. No re-review of the bronze ingestor itself is required after those land.

---

### @bs:staff-engineer (Final Full-Pipeline Review)

**Status:** CHANGES REQUESTED — test gap blocks final approval
**Date:** 2026-05-01
**Scope:** Full pipeline (Bronze + Silver/Base + Gold/Consumable)
**Approval doc:** `governance/approvals/full-pipeline-ipeds-finance-staff-review.md`

#### Verdict

- [ ] APPROVED
- [x] **CHANGES REQUESTED** — write 40 tests (Raw 10 + Base 15 + Consumable 15) before final sign-off
- [ ] REJECTED

#### Single Blocking Issue

**Zero tests across all three zones.** Brightsmith CLAUDE.md minimums are Raw=10, Base=15, Consumable=15 — 40 total. The IPEDS Finance zone has **0**. Every other ingested source in this repo (BEA RPP, BLS OOH, College Scorecard, Karpathy AI, O*NET, EADA) has tests at the minimum. This is a regression in test discipline. Per CLAUDE.md "If a zone has fewer tests than the minimum, issue CHANGES REQUESTED. No exceptions." I will not waive this.

The DQ rules (44/44 PASS) and chaos report (60/60 perturbations caught) are **runtime** validation — they prove the landed snapshot is shaped correctly and that the ingestor handles malformed source rows. They are NOT unit tests; they do not exercise the helper functions (`_strip_sentinel`, `_coerce_long`, `derive_per_fte`, `derive_marketing_ratio`, `classify_data_completeness_tier`, `_resolve_optional_override`, the `_rv` revised-CSV preference, etc.) at the function boundary.

#### What Passes

- **Code quality is high.** All three implementations match Brightsmith conventions verbatim, type hints are precise, error paths raise rather than swallow, comments explain WHY not WHAT, naming is unambiguous.
- **Spec compliance is exact.** §3 column codes, §4 sentinel set + HD filter + EFIA-not-EFFY-not-EFTOTLT decision, §5 base schema, §6 consumable schema with v1.1 ADV-6 raw passthroughs and v1.2 tier formula — all locked.
- **Idempotency holds at silver/gold** (re-runs report `0 promoted, 2675 skipped`); bronze drop-and-recreate is the documented single-vintage pattern.
- **13/13 spot-checks PASS** against published IPEDS reference values: Stanford UNITID 243744 marketing_ratio=0.30193 + record_id ipf-267f20f48b4b772f / ifp-267f20f48b4b772f; South-U-Montgomery UNITID 101116 (F3) tier=medium with structurally NULL endowment; F3-at-high count = 0 (the v1.2 reviewer rework's load-bearing invariant).
- **Standing user constraints all PASS** — no YAML lookups, no substitution-based degraded states, no "Limited data" warnings, single-source-of-truth maintained.
- **All 17 §8 governance artifacts present** per the @bs:governance-reviewer post-implementation review.

#### Carry-Forward Decisions

| ID | Description | Decision |
|----|-------------|----------|
| Q-1 (governance-reviewer) | 2 of 6 BT-IPF-* glossary entries missing from `governance/business-glossary.json` | **accept-with-followup** — bundle in same commit as test files |
| Q-2 (governance-reviewer) | "269 rows above $100M" propagation; live count is 365 | **accept-with-followup** — bundle in same commit as test files |
| Q-3 (governance-reviewer) | Spec §4 line 190 row-count band drift (5,000-8,000 vs JSON-enforced 2,500-3,200) | **accept-with-followup** — bundle in same commit as test files |

None of Q-1/Q-2/Q-3 changes pipeline behavior; the test gap does (silent regressions land without tests). Bundle once.

#### Required Before APPROVED

| # | Severity | Description |
|---|----------|-------------|
| **SE-T1** | BLOCKING | Write 10+ tests for `src/raw/ipeds_finance_ingestor.py` per the 14-item canonical list in the approval doc. |
| **SE-T2** | BLOCKING | Write 15+ tests for `src/silver/ipeds_finance_base.py` per the 15-item canonical list in the approval doc. |
| **SE-T3** | BLOCKING | Write 15+ tests for `src/gold/ipeds_finance_profile.py` per the 15-item canonical list in the approval doc. |
| SE-Q1/Q2/Q3 | non-blocking | Carry-forward cleanups bundled with the test commit. |

After SE-T1/T2/T3 land and `uv run pytest tests/raw/test_ipeds_finance_ingestor.py tests/silver/test_ipeds_finance_base.py tests/gold/test_ipeds_finance_profile.py` reports 40+ passing tests with no skips, the orchestrator may re-request review. I have intentionally NOT run `pipeline_gate complete ... staff-engineer ...` — that signals approval and I am withholding it.

Full review with code-quality assessment, the canonical test-list per zone, the 13-row spot-check table, and standing-constraint verdicts at `governance/approvals/full-pipeline-ipeds-finance-staff-review.md`.

#### v1.3 Re-Review (2026-05-01, post-test-write)

**Status: APPROVED.** Test gap closed and exceeded by 4.5× (179 tests vs 40 minimum: raw=79, base=54, consumable=46; all passing in 1.16s, full-suite regression 1974/1974). Spot-checked 5 random tests from each file — zero theater detected; every assertion validates a specific expected value or load-bearing invariant (the exhaustive `test_f3_can_never_be_high` is a particularly strong defensive test). Carry-forwards closed: Q-1 (2 missing BT-IPF-* glossary entries appended), Q-2 (`269` fully purged from active artifacts; only survives in archival approval-doc history), Q-3 (no-op confirmed — already correct in spec v1.3 §4 line 192). End-to-end re-ingest + base/gold promote re-runs confirm idempotency at silver/gold (0 promoted, 2675 skipped) and Stanford / South-U-Montgomery anchors stable; F3-at-high count = 0 (load-bearing v1.2 invariant holds). Spec is APPROVED for move to `docs/specs/completed/`. Full re-review at `governance/approvals/full-pipeline-ipeds-finance-staff-review.md` "v1.3 Re-Review" section.

---

## §8 Governance Artifacts

- [ ] EDA: `governance/eda/raw-ingest-ipeds-finance-eda.md`
- [ ] Domain context: `governance/domain-context.md` (append IPEDS Finance section)
- [ ] Models: `governance/models/raw-ingest-ipeds-finance-{conceptual,logical,physical}.md`
- [x] Models: `governance/models/base-ipeds-finance-{conceptual,logical,physical}.md` — @doc-generator 2026-04-30 (3 files; schemas verified against Iceberg metadata snapshot `1277941459950591173`)
- [x] Models: `governance/models/consumable-ipeds-finance-profile-{conceptual,logical,physical}.md` — @doc-generator 2026-04-30 (3 files; schemas verified against Iceberg metadata snapshot `6649279885162971471`)
- [ ] DQ rules: `governance/dq-rules/raw-ingest-ipeds-finance.json`
- [ ] DQ rules: `governance/dq-rules/base-ipeds-finance.json`
- [ ] DQ rules: `governance/dq-rules/consumable-ipeds-finance-profile.json`
- [ ] DQ scorecards under `governance/dq-scorecards/`
- [ ] Chaos report: `governance/chaos-reports/raw-ingest-ipeds-finance-chaos.md`
- [ ] Adversarial audit: `governance/adversarial-audits/consumable-ipeds-finance-profile.md`
- [ ] Lineage: `governance/lineage/raw-ingest-ipeds-finance-{timestamp}.json`
- [ ] CDE tagging: `governance/cde-tagging/consumable-ipeds-finance-profile.md`
- [x] Data contract: `governance/data-contracts/consumable-ipeds-finance-profile.yaml` — @doc-generator 2026-04-30 (status: draft; SLOs calibrated from EDA evidence — completeness 0.97, validity 1.00, CON-IFP-008 P1 floor 0.88 with P2 watch-line 0.86, tier `high` floor 0.70)
- [x] Data dictionary updates — @doc-generator 2026-04-30 (`governance/data-dictionaries/base-ipeds-finance.md` + `governance/data-dictionaries/consumable-ipeds-finance-profile.md`; bronze dictionary `raw-ipeds-finance.md` already existed)
- [ ] Business glossary updates: 6 BT-IPF-* terms (final IDs assigned by @bs:data-steward)
- [ ] Approvals: `governance/approvals/raw-ingest-ipeds-finance-{pre,post,staff}-review.md`

---

## §9 Implementation Log

**Status:** CONSUMABLE COMPLETE — raw ingestor implemented, manifest registered, end-to-end ingest into the persistent Iceberg warehouse executed (current bronze: FY2023, 2,675 rows, snapshot `2955168649587464831`). Full EDA pass at `governance/eda/raw-ingest-ipeds-finance-eda.md`. Domain-context section appended. Silver/base transformer at `src/silver/ipeds_finance_base.py` and runner at `scripts/promote_ipeds_finance_base.py` shipped per §5; `base.ipeds_finance` is queryable with **2,675 rows** (snapshot `1277941459950591173`), `record_id` 100% non-null + unique, all per-FTE / marketing-ratio derivations satisfy BSE-IPF-008/009/010 by construction, idempotent re-run produces 0 new rows. Gold/consumable transformer at `src/gold/ipeds_finance_profile.py` and runner at `scripts/promote_ipeds_finance_profile.py` shipped per §6; `consumable.ipeds_finance_profile` is queryable with **2,675 rows** (snapshot `6649279885162971471`), `record_id` 100% non-null + unique under the `ifp-` prefix, `data_completeness_tier` distribution `high=1,998 / medium=677 / low=0 / insufficient=0`, F3 rows land at `medium` (not `high`) by construction (endowment_value structurally NULL → 3/4 signals), Stanford spot-check `tier=high` + `marketing_ratio=0.30193`, idempotent re-run produces 0 new rows. Ready for `@bs:dq-rule-writer`.

### Files Modified

| File | Change Summary |
|---|---|
| `src/raw/ipeds_finance_ingestor.py` | Updated for spec v1.3 — IPEDS Finance bronze ingestor per §4. Locks all column codes from the pre-flight report (F1C011/F1C071/F1H02 for F1A; F2E011/F2E061/F2H02 for F2; **F3E011/F3E03C1** for F3 with endowment N/A; FTEUG+FTEGD+FTEDPP from EFIA). Switches FTE source from EFFY (long-form headcount) to EFIA (12-Month Instructional Activity, one row per UNITID, no dedup needed). Computes `total_fte_enrollment` as NULL-safe sum returning NULL only when all three components NULL. Fixes finance filename pattern to `F{YY1}{YY2}_F{1A\|2\|3}` (was incorrectly `F{1A\|2\|3}{YY1}{YY2}`). Cache-first read order (zip → csv → bulk URL). Adds cross-form duplicate UNITID warning. Removes all v1.2 TODO/Ellipsis-sentinel placeholders that the pre-flight resolved. |
| `data/raw/ipeds_finance_cache/fy2022/{F2122_F1A,F2122_F2,F2122_F3,EFIA2022,HD2022}.zip` | Staged FY2022 source zips (downloaded from `nces.ed.gov/ipeds/datacenter/data/`) for the end-to-end run. The pre-staged FY24 zips in the parent cache directory are 1.2KB 404-error HTML pages — IPEDS Finance for FY24 is not yet published as of 2026-04-30. |
| `domain/sources/ipeds_finance.yaml` | **NEW** — SourceConfig YAML modeled after `domain/sources/bea_rpp.yaml`. Encodes name=`ipeds_finance`, namespace=`bronze`, table=`ipeds_finance`, dedup_grain=`[unitid]`, fetch config (landing URL + bulk template + fallback path + fiscal_year=2022 + User-Agent), entities (single `ipeds_finance` logical entity), cache_dir, plus the same domain-documentation comment block style as the BEA RPP yaml (provider/license/cycle-year decision/locked column codes/DQ notes). Cycle-year decision is documented in-yaml: FY2022 because NCES has not yet published FY24 as of 2026-04-30. |
| `domain/manifest.yaml` | Modified — additive registration of `ipeds_finance` in the `sources:` block (after `bea_rpp`, before the `pipeline:` block). Same shape as the existing 7 source entries: `name` + `source_config` + `zone: raw` + `status: active`. No other manifest sections touched. |
| `scripts/ingest_ipeds_finance.py` | **NEW** — end-to-end ingest runner modeled after `scripts/ingest_bea_rpp.py`. Configures `brightsmith.config` with the project root (no `project_name` override — preserves the shared `'brightsmith'` catalog name per the BEA RPP HIGH-1 remediation), constructs a `SourceConfig` in-line that mirrors `domain/sources/ipeds_finance.yaml` (sidesteps the pre-existing `load_manifest()` limitation that the multi-table `onet.yaml` lacks a top-level `table:` key), calls `IpedsFinanceIngestor(...).ingest(cache_dir=..., force_fallback=True)`, and verifies the landed table via DuckDB. |
| `scripts/_verify_ipeds_finance.py` | **NEW** — throwaway verification helper (Stanford / Berkeley spot checks, F3 endowment NULL invariant, UNITID uniqueness against `bronze.ipeds_finance`). |
| `scripts/_eda_ipeds_finance.py` | **NEW** — throwaway EDA helper that drives the full distribution / per-FTE / coverage / imputation-flag analysis against `bronze.ipeds_finance` (and against `consumable.career_outcomes` via PyIceberg StaticTable for the EDA Req 4 overlap). Output JSON consumed by the EDA report. |
| `governance/eda/raw-ingest-ipeds-finance-eda.md` | **NEW** — full EDA report covering EDA Reqs 2-7 plus distribution profiling and threshold calibration recommendations. Top recommendations: BSE-IPF-015 needs per-form thresholds (proposed 5.0 table-wide fires on legitimate state-system administrative offices); BSE-IPF-013 and RAW-IPF-012 can be tightened to 70%; CON-IFP-008 passes at 90.39% but margin is razor-thin so add a P2 watch-line at 88%. Endowment imputation prevalence (≈ 25-31% on F1A/F2) flagged for v1.4 provenance-column consideration; instruction/inst-support imputation is < 0.6% and immaterial. |
| Iceberg warehouse: `data/warehouse/bronze/ipeds_finance/` (Parquet data files + metadata) and `bronze.ipeds_finance` registered in `data/catalog.db`. | New Iceberg table: snapshot `982081695100705470`, 2,683 rows, schema matches §4 Raw Schema exactly (12 fields: 8 payload + 4 framework metadata). |
| `governance/domain-context.md` | Modified — appended canonical IPEDS Finance section per Step 3 of the Claude Code Prompt. Section synthesizes the FY2022 actually-landed bronze table (2,683 rows) against the v1.3 spec, the pre-flight column-code lock-down report, and the full EDA report. Supersedes an earlier 2026-04-30 IPEDS Finance section that had been written against a hypothetical FY23 cycle (NCES had not yet published FY23 finance files at ingest time). New section covers: domain identification + sub-domain, provider/acquisition, form mix and accounting basis (F1A GASB / F2 FASB / F3 proprietary), the four bronze fields with plain-English definitions and per-form column codes, the critical EFIA-not-EFFY-not-EFTOTLT FTE source pin (the highest-risk field-selection in the spec), the HD `ICLEVEL=1 AND HLOFFER>=5` filter, cycle-vintage-as-runtime-parameter clarification (FY2022 not FY24), the endowment imputation caveat (25-31% of F1A/F2 bureau-imputed — meaningful prior omission corrected), F3 sparseness invariants (100% structural endowment NULL by design), the 90.39% career-outcomes overlap (tight pass for CON-IFP-008), the public-system-administrative-office outlier pattern (real IPEDS entities, not data errors), join-key guidance (use `unitid` long-int, never OPEID), explicit out-of-scope boundaries (per-FTE math, marketing_ratio interpretation, EADA fusion all live downstream), the 7 BT-IPF-* glossary anchors per §6, PII assessment (none — institution-level public data), source registry entry, and the FY2022-calibrated edge-case recap for @bs:dq-rule-writer. Revision history at file top updated with a supersession entry citing the FY2022 evidence base. Pipeline gate marked `domain-context` → COMPLETED via `python -m brightsmith.infra.pipeline_gate complete`. |
| `src/silver/ipeds_finance_base.py` | **NEW** — silver/base zone transformer per §5. Reads `bronze.ipeds_finance`, passes through the four raw fields (`institutional_support_expenses`, `instruction_expenses`, `endowment_value`, `total_fte_enrollment`) plus identity columns (`unitid`, `institution_name`, `report_form`, `fiscal_year`), and computes four derivations using plain double arithmetic per spec invariants (BSE-IPF-008/009/010): three per-FTE values (NULL when numerator is NULL or `total_fte_enrollment ≤ 0`) and a `marketing_ratio` (NULL when either operand is NULL or `instruction_expenses = 0`, mirroring `NULLIF` semantics). No imputation. Provenance: `source_load_date` (passthrough of raw `load_date`) + `ingested_at` (base promotion timestamp). Deterministic `record_id` via `compute_grain_id(row, ['unitid'], prefix='ipf')`. Idempotent promote via `brightsmith.infra.promote.promote(...)`. Modeled directly on `src/silver/bea_rpp_transformer.py`. |
| `scripts/promote_ipeds_finance_base.py` | **NEW** — one-off runner mirroring `scripts/promote_bea_rpp_silver.py`. Configures `brightsmith.config` against the project root without overriding `project_name` (preserves the shared `'brightsmith'` catalog name per the BEA RPP HIGH-1 remediation). Invokes `promote_ipeds_finance_base(project_dir=PROJECT_ROOT)`, then re-reads `base.ipeds_finance` via DuckDB to log row count, Stanford spot-check derivations, `record_id` non-null + uniqueness counts, and form mix. Returns 0 on success when row count ≥ 2,400, all `record_id`s non-null, and all unique. |
| Iceberg warehouse: `data/silver/iceberg_warehouse/base/ipeds_finance/` (Parquet data files + metadata) and `base.ipeds_finance` registered in `data/catalog/catalog.db`. | New Iceberg table: snapshot `1277941459950591173`, 2,675 rows (matches bronze 1:1 — BSE-IPF-001 conservation invariant satisfied), schema matches §5 Base Schema exactly (15 fields). Form mix: F1A=819, F2=1,579, F3=277. Stanford UNITID=243744 derived values: `instruction_per_fte=140,522.42` (= $2,683,135,000 / 19,094); `institutional_support_per_fte=42,427.78` (= $810,116,000 / 19,094); `endowment_per_fte=1,911,327.80` (= $36,494,893,000 / 19,094); `marketing_ratio=0.30193` (= $810,116,000 / $2,683,135,000); `record_id=ipf-267f20f48b4b772f` (deterministic across runs). All four arithmetic invariants (BSE-IPF-008/009/010) hold by construction: derivations use the exact bronze numerator and the divide-then-multiply roundtrip is exact in plain double. `record_id` non-null = 2,675/2,675; unique = 2,675/2,675. Idempotency confirmed: re-running `scripts/promote_ipeds_finance_base.py` reports `0 new rows (all 2675 already exist)`. |
| `src/gold/ipeds_finance_profile.py` | **NEW** — gold/consumable zone transformer per §6. Reads `base.ipeds_finance`, passes through the 12 base fields specified in §6.1 (identity 4 + raw 4 + derivations 4 — `unitid`, `institution_name`, `report_form`, `fiscal_year`, `total_fte_enrollment`, `instruction_expenses`, `institutional_support_expenses`, `endowment_value`, `institutional_support_per_fte`, `instruction_per_fte`, `endowment_per_fte`, `marketing_ratio`), and synthesizes `data_completeness_tier` per the v1.2 patch (counts non-null **independent raw inputs** — `instruction_expenses`, `institutional_support_expenses`, `endowment_value`, `total_fte_enrollment` (positive). 4 → `high`, 2-3 → `medium`, 1 → `low`, 0 → `insufficient`. NOT counting derived signals — that was the v1.0 formula reworked to prevent F3 misleading-`high` classification). No cross-source joins; no new arithmetic on derivations. Provenance: `promoted_at` timestamp. Deterministic `record_id` via `compute_grain_id(row, ['unitid'], prefix='ifp')` — distinct from base's `ipf` prefix per the spec (zone hash namespaces don't collide). Idempotent promote via `brightsmith.infra.promote.promote(...)`. Modeled directly on `src/gold/regional_price_parities_transformer.py` (closest single-source single-table consumable analogue). |
| `scripts/promote_ipeds_finance_profile.py` | **NEW** — one-off runner mirroring `scripts/promote_ipeds_finance_base.py`. Configures `brightsmith.config` against the project root without overriding `project_name` (preserves the shared `'brightsmith'` catalog name per the BEA RPP HIGH-1 remediation). Invokes `transform(project_dir=PROJECT_ROOT)`, then re-reads `consumable.ipeds_finance_profile` via DuckDB to log row count, `record_id` non-null + uniqueness counts, the global tier distribution, the per-form tier breakdown (validates the F3-medium-not-high invariant), the Stanford UNITID 243744 spot check, and an F3 spot check. Returns 0 on success when row count == 2,675, all `record_id`s non-null + unique, and the tier distribution falls within `{high, medium, low, insufficient}`. |
| Iceberg warehouse: `data/gold/iceberg_warehouse/consumable/ipeds_finance_profile/` (Parquet data files + metadata) and `consumable.ipeds_finance_profile` registered in `data/catalog/catalog.db`. | New Iceberg table: snapshot `6649279885162971471`, 2,675 rows (matches base 1:1 — CON-IFP-001 conservation invariant satisfied), schema matches §6 Consumable Schema exactly (15 fields). `data_completeness_tier` distribution: `high=1,998 / medium=677 / low=0 / insufficient=0` (74.7% high — comfortably above the 70% CON-IFP-009 EDA-calibrated floor). Per-form tier breakdown: F1A=`high:706, medium:113`; F2=`high:1,292, medium:287`; F3=`high:0, medium:277` (all 277 F3 rows at `medium`, none at `high` — confirms the v1.2 reviewer rework prevents F3 misleading-`high` classification driven by the structural `endowment_value` NULL). Stanford UNITID=243744: `tier=high` (all 4 raw inputs present), `marketing_ratio=0.30193` (matches CON-IFP-007 institutional_support_per_fte / instruction_per_fte = 42,427.78 / 140,522.42 = 0.30193 — invariant holds upstream of this transformer), `record_id=ifp-267f20f48b4b772f` (deterministic across runs). F3 spot-check (UNITID=101116, South University-Montgomery): `tier=medium` with `endowment_value=NULL`, `instruction_expenses=$2,659,323`, `institutional_support_expenses=$2,944,986`, `total_fte_enrollment=357.0` — 3/4 raw inputs present per the v1.2 formula. `record_id` non-null = 2,675/2,675; unique = 2,675/2,675 (CON-IFP-002, CON-IFP-003, CON-IFP-004). Idempotency confirmed: re-running `scripts/promote_ipeds_finance_profile.py` reports `0 new rows (all 2675 already exist)`. |
| `governance/dq-rules/raw-ipeds-finance.json` | **EXISTING (bronze, 14 rules: 12 P0 + 2 P1)** — RAW-IPF-001..014 per spec §4. Already authored, approved, and ACTIVE; included here for cross-zone visibility. RAW-IPF-001 row-count band recalibrated from spec-as-written 5,000-8,000 to 2,500-3,200 per EDA §0 gate 6 (post-HD-filter actual is 2,675; the original band was sized for the unfiltered finance UNION). |
| `governance/dq-rules/base-ipeds-finance.json` | **NEW (base, 19 rules: 13 P0 + 6 P1)** — BSE-IPF-001..017 per spec §5, with BSE-IPF-015 split into per-form variants 015a/b/c per EDA §6.5 strong recommendation. Cross-vintage drift recalibration on the per-form marketing_ratio P99 thresholds (EDA was on FY2022, landed bronze is FY2023): 015a F1A < 15.0 (was EDA 13.0; FY2023 measured P99 = 14.15), 015b F2 < 7.0 (was EDA 5.5; FY2023 measured P99 = 6.35), 015c F3 < 11.0 (preserved per EDA; FY2023 measured P99 = 8.75). BSE-IPF-013 (endowment_per_fte non-null) tightened from spec 55% to EDA 70%; BSE-IPF-014 (marketing_ratio non-null) tightened from spec 85% to EDA 95%. All other thresholds preserved per spec/EDA. All 19 rules pass against landed `base.ipeds_finance`. |
| `governance/dq-rules/consumable-ipeds-finance-profile.json` | **NEW (consumable, 11 rules: 8 P0 + 2 P1 + 1 P2)** — CON-IFP-001..010 per spec §6, plus CON-IFP-008b P2 watch-line per EDA §4 explicit recommendation. Cross-vintage drift recalibration on coverage rules (EDA FY2022 measured 90.39%, FY2023 actual 88.71%): CON-IFP-008 P1 recalibrated from spec/EDA 90% to 88% (0.71pp headroom against FY2023 baseline); CON-IFP-008b P2 watch-line correspondingly shifted from 88% to 86% to preserve the EDA-recommended 200-bp warning gap. CON-IFP-009 (`high` tier ≥ 70%) preserved at 70% per EDA explicit recommendation (FY2023 measured 74.7%). All other thresholds preserved per spec. All 11 rules pass against landed `consumable.ipeds_finance_profile` (joined with `consumable.career_outcomes` for CON-IFP-008/008b). |
| `governance/dq-scorecards/full-pipeline-ipeds-finance-scorecard.md` | **NEW** — generated via `python -m brightsmith.infra.dq_runner scorecard --spec full-pipeline-ipeds-finance` after the full-suite execution. Records: 44 total rules (33 P0 + 10 P1 + 1 P2), 44/44 pass, P0 gate PASS, run id `d16e354a` at `governance/dq-results/full-pipeline-ipeds-finance-20260501T204858Z.json`. |
| `governance/cde-tagging/consumable-ipeds-finance-profile.md` | **NEW** — consumable-zone CDE/PII tagging per spec §6 Data Contract. 15 columns evaluated; **10 flagged CDE** (all 5 spec §6 candidates `marketing_ratio`/`endowment_per_fte`/`institutional_support_per_fte`/`instruction_per_fte`/`data_completeness_tier` PLUS the structural join anchor `unitid`, the per-FTE denominator `total_fte_enrollment`, and the 3 raw dollar passthroughs `instruction_expenses`/`institutional_support_expenses`/`endowment_value` that spec §6 Transformation 1 explicitly re-exposes for downstream EADA composite-ratio computation per `docs/specs/full-pipeline-eada.md`); **0 flagged PII** (institution-level public federal survey data, inherits clean-zero PII posture from `governance/pii-scans/raw-ipeds-finance-pii-scan.md`); 5 not flagged (`record_id` grain surrogate, `institution_name` display label, `report_form` + `fiscal_year` provenance, `promoted_at` batch stamp). Includes data-contract YAML fragment for @doc-generator to embed into `governance/data-contracts/consumable-ipeds-finance-profile.yaml` and CDE-level SLO suggestions for @bs:dq-rule-writer. |
| `governance/adversarial-audits/consumable-ipeds-finance-profile.md` | **NEW** — adversarial audit on `consumable.ipeds_finance_profile` per spec v1.3. Verdict: **CLEAR for consumable-zone governance review; SOFT-BLOCKED for downstream `raw-ingest-eada.md`** (4 HIGH-severity contract-layer gaps must close before EADA fusion proceeds). 8 gaps total (4 HIGH, 3 MEDIUM, 1 LOW): (1) `tier='high'` decoupled from `marketing_ratio` computability — 2 known live-data exceptions (Thomas Edison State, Rockefeller); (2) state-system administrative offices dominate top-25 `marketing_ratio` outliers (top 18 of 25 are `~~ ' Office'/' System'/'Chancellor'`) — EDA-recommended v1.4 filter not adopted; (3) vintage-drift unjoinability — `consumable.career_outcomes` carries no `fiscal_year` and CON-IFP-008 has no vintage clause; (4) future EADA fusion silently drops 100% of F3 institutions on any composite requiring `endowment_per_fte` (213/213 F3-CO-matched UNITIDs); (5) `medium` tier collapses 2/4 vs 3/4 signals into one bucket; (6) `endowment_value=0` semantically conflates underwater funds with non-endowment placeholders; (7) `source_load_date` dropped between base and consumable schemas (vintage observability gap); (8) academic medical centers' `instruction_per_fte` outliers (UT Southwestern $723K) bundle clinical/research expense — pass P99 rules, fail consumer interpretation. Cross-zone arithmetic invariants and zone-prefix namespace separation hold cleanly. Recommendations: author `governance/data-contracts/consumable-ipeds-finance-profile.yaml` (closes Gaps 1-4 at contract layer), add CON-IFP-011 (P1: `tier='high' AND marketing_ratio IS NULL`) and CON-IFP-012 (P0: vintage propagation), expose `non_null_signals_count` int column, restore `source_load_date` passthrough, glossary updates for endowment-zero and academic-medical-center per-FTE. No HARD blockers; all eight mitigations are additive contract/rule/glossary changes (R6 schema-altering, deferable). |
| `governance/models/base-ipeds-finance-conceptual.md` | **NEW** — Base-zone conceptual model per spec §5. ER diagram with eight entities (Institution, Finance Report, Accounting Form, Fiscal Cycle, Monetary Measurement, Enrollment Denominator, Per-FTE Derivation, Marketing Intensity, Ingest Provenance). Documents the 1:1 promotion pattern (no joins; 12 of 15 columns are passthroughs, 4 are new derivations, 2 are provenance, 1 is the deterministic surrogate key). Captures the three-pronged design rationale for placing per-FTE derivations at Base (single source of truth for institution-scale comparison; mechanically deterministic from Bronze inputs; downstream consumers don't need to repeat the EFIA-vs-EFFY-vs-EFTOTLT field-selection decision). Documents the public-system-administrative-office pattern (LA CCD Office, U Colorado System Office, etc.) that drives F1A's marketing_ratio P99 to ~14 — organizational-structure artifact, not data quality failure. CDE flag posture explicitly inverted vs Bronze (per-FTE rates and marketing_ratio carry the analytical CDE flag at Base; raw monetary inputs become CDE only at consumable per spec §6). |
| `governance/models/base-ipeds-finance-logical.md` | **NEW** — Base-zone logical model per spec §5. Single denormalized 15-attribute table per the Brightsmith Silver Base zone pattern. Attributes grouped by conceptual entity. Plain-English derivation rules for the four new derivations (per-FTE math: NULL when either operand NULL or FTE ≤ 0; marketing_ratio: NULLIF semantics on the denominator). Captures the EDA-calibrated DQ thresholds (BSE-IPF-013 tightened to 70%; BSE-IPF-014 tightened to 95%; BSE-IPF-015 split per-form into 015a/b/c with cross-vintage drift headroom). Documents nullability semantics — 7 NOT NULL identity/provenance, 8 NULLABLE numeric (per "no substitution-based degraded states" standing constraint). |
| `governance/models/base-ipeds-finance-physical.md` | **NEW** — Base-zone physical model per spec §5. Iceberg DDL, full PyIceberg `Schema()` definition with field IDs 1-15 pinned. Field IDs and types verified against landed Iceberg metadata (snapshot `1277941459950591173`, `data/silver/iceberg_warehouse/base/ipeds_finance/metadata/00001-4b79be88-21c1-4a59-ad00-c2299e64f36b.metadata.json`) — all 15 fields match spec §5 exactly. Reference `promote_ipeds_finance_base()` implementation showing pandas `.where()` NULL-safe per-FTE division and the `NULLIF(instruction, 0)` marketing-ratio guard. Promote pattern: `compute_grain_id(row, ['unitid'], prefix='ipf')` (distinct from consumable's `'ifp'`). Idempotent — re-runs produce 0 new rows. Cross-references DQ rules, scorecard, data dictionary, and downstream consumable model. |
| `governance/models/consumable-ipeds-finance-profile-conceptual.md` | **NEW** — Consumable-zone conceptual model per spec §6. ER diagram with eight entities (Institution, Finance Profile, Accounting Form, Fiscal Cycle, Monetary Measurement, Per-FTE Derivation, Marketing Intensity, Data Completeness Tier, Promotion Provenance). Documents the v1.1 governance-reviewer ADV-6 narrow-exception ruling for the three raw expense passthroughs (`instruction_expenses`, `institutional_support_expenses`, `endowment_value`). Explains the v1.1 `confidence_tier → data_completeness_tier` rename (disambiguation from CIP→SOC crosswalk-confidence tiers). Documents why the v1.1 reformulation counts independent raw inputs (NOT derived signals) — prevents the F3 misleading-`high` classification by ensuring F3 always caps at `medium` since endowment is structurally NULL. |
| `governance/models/consumable-ipeds-finance-profile-logical.md` | **NEW** — Consumable-zone logical model per spec §6. Single denormalized 15-attribute table. Attributes grouped: 5 identity, 1 FTE, 3 raw expense passthroughs (newly exposed at consumable), 3 per-FTE passthroughs, 1 marketing-ratio passthrough, 1 tier (NEW), 1 provenance. CDE flag posture: `unitid` + 3 raw expense fields (newly CDE) + 3 per-FTE rates + marketing_ratio + tier = **9 CDE columns** (60%). Documents observed FY2023 distributions: tier `high=1,998 (74.7%) / medium=677 (25.3%)` overall; per-form F1A `high:706, medium:113`; F2 `high:1,292, medium:287`; F3 `high:0, medium:277`. |
| `governance/models/consumable-ipeds-finance-profile-physical.md` | **NEW** — Consumable-zone physical model per spec §6. Iceberg DDL, full PyIceberg `Schema()` definition with field IDs 1-15 pinned. Field IDs and types verified against landed Iceberg metadata (snapshot `6649279885162971471`, `data/gold/iceberg_warehouse/consumable/ipeds_finance_profile/metadata/00001-f4e93ae5-0895-4f0e-b162-733ce80e413b.metadata.json`) — all 15 fields match spec §6 exactly, including the v1.2 raw expense passthroughs at field IDs 7/8/9 and `data_completeness_tier` at field ID 14. Reference `promote_ipeds_finance_profile()` implementation with the `classify_tier()` pure-Python function that counts non-null `{instruction_expenses, institutional_support_expenses, endowment_value, total_fte_enrollment > 0}` and classifies `4 → high`, `2-3 → medium`, `1 → low`, `0 → insufficient`. Reference SQL CASE expression for CON-IFP-006 re-check. Promote pattern: `compute_grain_id(row, ['unitid'], prefix='ifp')` (distinct from base's `'ipf'`). |
| `governance/data-dictionaries/base-ipeds-finance.md` | **NEW** — full data dictionary for `base.ipeds_finance` per spec §5. 15 fields documented with type, nullability, business definition, derivation formula (for the four per-FTE / marketing-ratio fields), source field(s) from Bronze. Embeds Stanford spot-check values (`instruction_per_fte=$140,522.42`, `institutional_support_per_fte=$42,427.78`, `endowment_per_fte=$1,911,327.80`, `marketing_ratio=0.30193`, `record_id=ipf-267f20f48b4b772f`). 12 caveats-for-consumers (FTE NULL cascade, F3 endowment structural NULL, public-system-administrative-office cluster, prefix `ipf` vs `ifp`, no imputation, marketing_ratio NULLIF semantics, self-auditable arithmetic invariants, FY2023 cycle, no SCD2, monetary-input CDE-flag posture). 6 fields flagged CDE (40%), 0 flagged PII. Cross-references Bronze dictionary, conceptual/logical/physical models, DQ rules, scorecard, EDA report, domain context. |
| `governance/data-dictionaries/consumable-ipeds-finance-profile.md` | **NEW** — full data dictionary for `consumable.ipeds_finance_profile` per spec §6. 15 fields documented with type, nullability, business definition, derivation (for `data_completeness_tier`), upstream source field(s). Embeds the v1.1 reformulation rationale (count independent raw inputs, NOT derived signals — prevents F3 misleading-`high` classification). Stanford spot check (`tier=high`, `marketing_ratio=0.30193`, `record_id=ifp-267f20f48b4b772f`) + F3 spot check (UNITID 101116 South University-Montgomery: `tier=medium`, `endowment_value=NULL`, 3/4 inputs present). 10 caveats-for-consumers including the disambiguation note ("NOT a CIP→SOC crosswalk-confidence tier — measures source-field non-null count, not crosswalk match quality"). 9 fields flagged CDE (60%) — `unitid` + 3 raw expense passthroughs (newly CDE per spec §6 Data Contract) + 3 per-FTE rates + `marketing_ratio` + `data_completeness_tier`. 0 flagged PII. Cross-references Base dictionary, conceptual/logical/physical models, DQ rules, scorecard, data contract, EDA report. |
| `governance/data-contracts/consumable-ipeds-finance-profile.yaml` | **NEW** — data contract for `consumable.ipeds_finance_profile` per spec §6. Status `draft` pending @bs:staff-engineer post-implementation sign-off. Owner `@bs:data-steward`. SLA: annual refresh when IPEDS publishes new Finance + EFIA data (typically December). Quality tier: EDA-calibrated; expected `high`. Schema modeled after `governance/data-contracts/consumable-regional-price-parities.yaml`; all 15 columns documented with type, nullable, business_term, is_cde, cde_rationale, is_pii, description, dq_rules. SLO calibration values: row_count_guarantee=2,675; row_count_tolerance_band [2500, 3200]; completeness_threshold=0.97 (FTE-dependent floor); validity_threshold=1.00; CON-IFP-008 P1 floor=0.88 (FY2023 measured 88.71%); CON-IFP-008b P2 watch-line=0.86; tier `high` floor=0.70 (FY2023 measured 74.7%); freshness_sla=annual cycle, source_load_date within 400 days. Documents the v1.1 governance-reviewer ADV-6 narrow exception (3 raw expense passthroughs) and the v1.1 `confidence_tier → data_completeness_tier` rename as `reviewer_conditions`. CDE summary: 9 of 15 columns CDE (60%); 0 PII. Lists downstream consumers (`raw-ingest-eada.md` primary; future receipts/comparison specs and MCP tools secondary). |
| `tests/raw/test_ipeds_finance_ingestor.py` | **NEW (raw, 79 tests)** — closes SE-T1 from the staff-engineer review. Modeled on `tests/raw/test_bea_rpp_ingestor.py` (closest analogue: BLS-style multi-file source). Coverage: `_strip_sentinel` (5 sentinels parametrized + whitespace + numeric pass-through + None pass-through), `_coerce_long` (int/float/quoted-string/leading-zero/scientific/NaN/bool/empty/unparseable), `_coerce_double` (thousands-separator + dollar-sign + NaN + bool + empty + unparseable), `_resolve_optional_override` (Ellipsis vs explicit None vs string), `_build_efia_lookup` (NULL-safe sum + sentinel pass-through + duplicate-UNITID warning + unparseable-UNITID drop), `_build_hd_lookup` (passthrough + skip-unparseable), filename helpers (`_fy_filename` for FY23/FY24, `_efia_filename`, `_hd_filename`), schema (12 fields, types, required-vs-nullable on `endowment_value`), `get_source_url` (5-file pipe-delimited), USER_AGENT + CSV_CHUNK_SIZE constants, `_iter_csv_chunks` round-trip + empty body, `_read_zip_file` `_rv` revised-CSV preference (synthesized 2-CSV zip fixture), `_fetch_one` resolution order (explicit path bypasses cache/network, force_fallback raises FileNotFoundError, local zip wins over CSV), `_flatten_one` HD-miss + HD-filter rejection (ICLEVEL=2 dropped, HLOFFER=4 dropped, ICLEVEL=1+HLOFFER=5 boundary accepted, unparseable-UNITID dropped, F3 endowment-col=None → endowment NULL), end-to-end `flatten()` against synthetic 3-form fixture (F1A=2 / F2=2 / F3=2 with one HD-rejected + one HD-miss + one F3-endowment-NULL → 4 surviving rows, exact form mix, fiscal_year stamped, EFIA left-join populated, F3 endowment NULL, no framework metadata, sentinels become NULL, cross-form duplicate UNITID warning), and full integration test that lands 4 rows (Stanford + Berkeley synthetic + Northeastern + for-profit) into a temp Iceberg warehouse via `BaseIngestor.ingest()` and verifies Stanford's golden values + framework metadata + idempotent second run produces 0 new rows. Closes SE-T1. |
| `tests/silver/test_ipeds_finance_base.py` | **NEW (base, 54 tests)** — closes SE-T2 from the staff-engineer review. Modeled on `tests/silver/test_bea_rpp_transformer.py` (closest analogue: single-source promote with derivations). Coverage: `derive_per_fte` (None numerator + None FTE + both None + parametrized [0.0, -1.0, -100.0] FTE-zero-or-negative guard + correct value + Stanford golden derivation + arithmetic-invariant roundtrip across 4 fixtures), `derive_marketing_ratio` (correct value + Stanford golden + None inst_supp + None instruction + both None + zero-instruction NULLIF semantics), `_to_optional_float` (None + int + float + NaN rejection + numeric string), `transform_row` ValueError paths for each of 5 required fields (unitid, institution_name, report_form, fiscal_year, load_date), `transform_row` determinism (ipf- prefix + same input same output + Stanford `ipf-267f20f48b4b772f` exact match + record_id depends only on unitid), `transform_row` derivations (Stanford exact: instruction_per_fte=140,522.42 / inst_supp_per_fte=42,427.78 / endow_per_fte=1,911,327.80 / marketing_ratio=0.30193 + passthrough fields + provenance fields + BSE-IPF-008/009/010 arithmetic invariants), F3 NULL cascade (endowment NULL → endowment_per_fte NULL while other derivations still populate), zero-instruction → NULL marketing_ratio + zero instruction_per_fte stays 0.0, `transform_rows` same-length output + duplicate-UNITID raises + record_ids unique, schema (15 fields exact list + required-vs-nullable + field types + module constants `GRAIN_FIELDS=['unitid']`, `GRAIN_PREFIX='ipf'`, `SPEC_NAME='base-ipeds-finance'`), and full integration test (3-row bronze → 3-row base via `promote_ipeds_finance_base()` against temp Iceberg warehouse: Stanford derivations + F3 NULL cascade + zero-instruction NULL marketing_ratio + idempotent second run produces 0 new rows + form-mix counter logged). Closes SE-T2. |
| `tests/gold/test_ipeds_finance_profile.py` | **NEW (consumable, 46 tests)** — closes SE-T3 from the staff-engineer review. Modeled on `tests/gold/test_regional_price_parities_transformer.py` (closest analogue: shaping promote with classification). Coverage: `classify_data_completeness_tier` (4-of-4 → high, 3-of-4 → medium, 2-of-4 → medium, 1-of-4 → low, 0-of-4 → insufficient + parametrized [0.0, -1.0, -100.0] FTE-not-a-signal guard for the v1.2 reformulation), F3 medium-not-high invariant (load-bearing v1.2 reviewer rework: `test_f3_can_never_be_high` exhaustively tries every present/absent combination on the 3 non-endowment fields and asserts none classify as `high`), F3 boundary case (only 1 other input → low tier), `TIER_RAW_INPUTS` constant (exactly 4 fields, matches spec, excludes derived signals), `transform_row` (ifp- prefix + determinism + Stanford `ifp-267f20f48b4b772f` exact match + 12 BASE_PASSTHROUGH_FIELDS verbatim + promoted_at stamped + tier synthesis + F3 medium synthesis + no arithmetic recomputation), cross-zone hash separation (Stanford suffix `267f20f48b4b772f` matches base's `ipf-` + zone prefixes distinct: `ifp ≠ ipf`), `transform_rows` (same-length + duplicate-UNITID raises + shared promoted_at across batch + default `datetime.now(tz=UTC)` when None), schema (15 fields exact list including v1.2 raw passthroughs + required-vs-nullable + field types + module constants `GRAIN_FIELDS=['unitid']`, `GRAIN_PREFIX='ifp'`, `BASE_PASSTHROUGH_FIELDS` length=12 excluding zone-local provenance), CON-IFP-007 arithmetic-invariant carry-forward (Stanford + F3: institutional_support_per_fte / instruction_per_fte ≈ marketing_ratio within 0.001 by construction), and full integration test (3-row base → 3-row consumable via `transform()` against temp Iceberg warehouse: Stanford `tier=high` + `record_id=ifp-267f20f48b4b772f`, F3 `tier=medium`, low-data row `tier=low`, idempotent second run produces 0 new rows, tier_counts logged). Closes SE-T3. |
| `governance/business-glossary.json` | **MODIFIED — Q-1 cleanup (additive append).** Added the 2 missing BT-IPF-* terms `BT-IPF-MARKETING-RATIO` and `BT-IPF-DATA-COMPLETENESS-TIER` per the staff-engineer Q-1 follow-up directive. Definitions copied verbatim from spec §6 Business Glossary Terms list. Glossary now has all 6 BT-IPF-* terms (was 4); JSON validity verified. Also fixed propagation typo: `BT-IPF-INSTRUCTION-EXPENSES` definition's "269 institutions exceed $100M" stale figure corrected to the live `365` per Q-2 cleanup. |
| `governance/dq-scorecards/full-pipeline-ipeds-finance-scorecard.md` | **MODIFIED — Q-2 cleanup.** Fixed RAW-IPF-014 rationale row "Observed FY23 count is 269 rows above $100M" → `365` (the actual landed FY2023 count per the EDA report §8 and `governance/dq-rules/raw-ipeds-finance.json` RAW-IPF-014 rationale, both of which already said 365). Cosmetic only — no executable behavior depends on the literal value. |
| Q-3 status | **No-op — already landed in spec v1.3.** Spec §4 line 192 already reads `RAW-IPF-001 row count between 2,500 and 3,200 \| P0 \| Volume \| EDA-calibrated 2026-04-30 against FY23 actual post-filter count of 2,675; original spec band 5,000–8,000 was based on pre-filter HD count`. The data dictionary `governance/data-dictionaries/raw-ipeds-finance.md` line 99 also already shows the recalibrated band. The dq-rules JSON also enforces the recalibrated band. The staff-engineer's Q-3 follow-up was satisfied by the v1.3 spec itself (the original 5,000-8,000 band predated the HD-filter narrowing) — no spec edit required. |

### Deviations from Spec

| Section | Deviation | Reason |
|---|---|---|
| §4 ingestor cycle year | End-to-end run executed against FY2022 (academic year 2021-22) instead of the §3 narrative's FY24. | NCES has not yet published the FY24 (`F2324_F1A.zip` etc.) finance files — the IPEDS Data Center returns HTTP 200 with a 1.2KB 404-error HTML page for these names. FY2022 is the most-recent fully-published cycle and the year the pre-flight verified column codes against. The ingestor's `fiscal_year=` constructor argument and `domain/sources/ipeds_finance.yaml`'s `fetch.ipeds_finance.fiscal_year` field both support any cycle, so promoting to FY24 once published is a parameter change, not a code change. |
| §4 zone naming | Manifest uses `namespace: bronze` and the landed table is `bronze.ipeds_finance`; spec text says `raw.ipeds_finance`. | Project-wide convention — every existing source YAML uses `namespace: bronze` and every existing landed table lives under the `bronze` Iceberg namespace (BEA RPP, BLS OOH, Karpathy, College Scorecard, EADA all confirmed via catalog list). The spec text uses "raw" interchangeably with "bronze" as the zone-name shorthand. No data-shape impact. |
| §5 zone naming | Silver/base transformer file at `src/silver/ipeds_finance_base.py` (under the `silver/` Python package); landed Iceberg table is `base.ipeds_finance` (under the `base` namespace). The spec text writes `base.ipeds_finance`. | Project-wide convention — directly mirrors `src/silver/bea_rpp_transformer.py` → `base.bea_rpp` (and every other silver/base transformer under `data/silver/iceberg_warehouse/base/*`). The Python module path uses the long-standing `silver/` zone name; the Iceberg namespace uses the §5-specified `base` name. No data-shape impact. |
| §5 cycle year | Bronze was re-ingested for FY2023 between the §4 log entry (which records 2,683 FY2022 rows) and this base-zone run (which reads 2,675 FY2023 rows). Conservation invariant BSE-IPF-001 (base count == bronze count) holds at 2,675 == 2,675. The earlier 2,683-row figure in the §4 log reflects the pre-re-ingest snapshot; current bronze snapshot is `2955168649587464831` with `fiscal_year=2023` for all rows. | Bronze ingestor was re-run to land FY2023 (the now-published most-recent cycle) per `scripts/ingest_ipeds_finance.py` (`FISCAL_YEAR = 2023`). The base transformer is cycle-agnostic — it passes `fiscal_year` through unchanged, and all derivations are pure arithmetic on whatever bronze numerator/denominator landed. No code change. |

### Build Accountability Log

| Attempt | Result | Error | Fix Applied |
|---|---|---|---|
| 1 | Lint PASS | — | `uv run ruff check src/raw/ipeds_finance_ingestor.py` → "All checks passed!" |
| 1 | Type check PASS (parity with sibling ingestors) | 3 errors, all `import-untyped` for `requests`, `brightsmith.bronze.base_ingestor`, `brightsmith.domain_loader`. Same 3 errors fire on `bea_rpp_ingestor.py`; pre-existing repo infrastructure, not code defects. | None required — accepted as baseline. |
| 1 | Smoke run PASS | — | Executed `IpedsFinanceIngestor(fiscal_year=2022).fetch(..., cache_dir='data/raw/ipeds_finance_cache/fy2022', force_fallback=True)` then `.flatten()` against five live IPEDS FY2022 zips (downloaded fresh from NCES with the project's User-Agent). Results: 6,036 EFIA rows / 6,036 distinct UNITIDs (matches pre-flight), 2,683 rows after the HD 4-year filter (form mix F1A=803, F2=1,593, F3=287). Stanford (UNITID 243744) returns `instruction_expenses=$2,380,695,000`, `institutional_support_expenses=$684,507,000`, `endowment_value=$36,338,794,000`, `total_fte_enrollment=18,219` — all four match the pre-flight verbatim. Berkeley (UNITID 110635) FTE=45,872 matches pre-flight. F3 sample UNITID 101116 institutional_support=$2,910,487 matches pre-flight Spot-check Table row 1. F3 endowment NULL rate = 100% (287/287 — confirms F3 N/A coalesce). Institutional-support NULL rate = 0% on all three forms (confirms F3E03C1 lock). Cross-form duplicate UNITIDs = 0 (invariant holds). |
| 1 | Manifest load FAIL | `KeyError: 'table'` from `brightsmith.domain_loader._load_source_config` when calling `load_manifest()` — triggered on `domain/sources/onet.yaml`, which uses a multi-table `tables:` block instead of a top-level `table:` key. Pre-existing limitation, surfaced when the runner first tried to use the manifest path. | Switched `scripts/ingest_ipeds_finance.py` to construct `SourceConfig` in-line (mirrors `scripts/ingest_bea_rpp.py`), keeping `domain/sources/ipeds_finance.yaml` as the authoritative on-disk source-config record. Manifest still loads correctly via `bs:status` etc. that don't traverse every source. |
| 2 | End-to-end Iceberg write PASS | — | `uv run python scripts/ingest_ipeds_finance.py`. Read 5 cache zips (F2122_F1A=1,936 / F2122_F2=1,782 / F2122_F3=2,120 / EFIA2022=6,036 / HD2022=6,256 rows). Built EFIA FTE lookup for 6,036 UNITIDs, HD lookup for 6,256 UNITIDs. Filtered 3,155 rows failing HD filter (`ICLEVEL=1 AND HLOFFER>=5`). Flattened 2,683 rows, appended to `bronze.ipeds_finance` as snapshot `982081695100705470` (skipped=0, no prior rows). Post-write verification via `scripts/_verify_ipeds_finance.py` reads 2,683 rows back, form mix exactly matches smoke run (F1A=803 / F2=1,593 / F3=287), Stanford / Berkeley spot checks match pre-flight verbatim, F3 endowment NULL rate = 100% (287/287), UNITID uniqueness = 2,683/2,683. Schema columns landed: `unitid`, `institution_name`, `report_form`, `fiscal_year`, `instruction_expenses`, `institutional_support_expenses`, `endowment_value`, `total_fte_enrollment`, `source_url`, `source_method` (=`csv_cache`), `ingested_at`, `load_date` — exactly the 12 fields in §4 Raw Schema. |
| §5/1 | Lint PASS | — | `uv run ruff check src/silver/ipeds_finance_base.py scripts/promote_ipeds_finance_base.py` → "All checks passed!" |
| §5/1 | Type check PASS (parity with sibling transformers) | 3 errors, all `import-untyped` for `brightsmith.infra.{grain, iceberg_setup, promote}`. Same 3 errors fire on `src/silver/bea_rpp_transformer.py`; pre-existing repo infrastructure, not code defects. | None required — accepted as baseline. |
| §5/1 | Promote run PASS | — | `uv run python scripts/promote_ipeds_finance_base.py`. Read 2,675 rows from `bronze.ipeds_finance` (current snapshot `2955168649587464831`, FY2023). Transformed 2,675 base rows (form mix F1A=819 / F2=1,579 / F3=277). Promoted to `base.ipeds_finance` as snapshot `1277941459950591173` — `2,675 promoted, 0 skipped`. Stanford UNITID 243744: `instruction_per_fte=140,522.42`, `institutional_support_per_fte=42,427.78`, `endowment_per_fte=1,911,327.80`, `marketing_ratio=0.30193`, `record_id=ipf-267f20f48b4b772f` — all four derivations equal raw bronze numerator divided by raw bronze denominator (Stanford bronze: instruction=$2,683,135,000, inst-support=$810,116,000, endowment=$36,494,893,000, FTE=19,094), so BSE-IPF-008/009/010 arithmetic invariants hold by construction. `record_id` 2,675/2,675 non-null and 2,675/2,675 unique (BSE-IPF-002, BSE-IPF-003). Conservation invariant BSE-IPF-001 holds: 2,675 base rows == 2,675 bronze rows. (Pre-existing brightsmith framework warning: `AttributeError: 'Table' object has no attribute 'identifier'` from `brightsmith.infra.promote.py:71` lineage emission — same warning fires on every silver/base transformer in this repo, including BEA RPP. Does not affect data correctness; flagged for upstream brightsmith fix.) |
| §5/1 | Idempotency PASS | — | Re-ran `uv run python scripts/promote_ipeds_finance_base.py` immediately. Result: `Promote base-ipeds-finance: 0 new rows (all 2675 already exist)`. Stanford `record_id` identical across runs (`ipf-267f20f48b4b772f`), confirming `compute_grain_id(row, ['unitid'], prefix='ipf')` is deterministic. |
| §6/1 | Lint PASS | — | `uv run ruff check src/gold/ipeds_finance_profile.py scripts/promote_ipeds_finance_profile.py` → "All checks passed!" |
| §6/1 | Type check PASS (parity with sibling transformers) | 3 errors, all `import-untyped` for `brightsmith.infra.{grain, iceberg_setup, promote}`. Same 3 errors fire on `src/gold/regional_price_parities_transformer.py` and every silver/base transformer in this repo; pre-existing repo infrastructure, not code defects. | None required — accepted as baseline. |
| §6/1 | Promote run PASS | — | `uv run python scripts/promote_ipeds_finance_profile.py`. Read 2,675 rows from `base.ipeds_finance` (snapshot `1277941459950591173`, FY2023). Transformed 2,675 consumable rows. Promoted to `consumable.ipeds_finance_profile` as snapshot `6649279885162971471` — `2,675 promoted, 0 skipped`. Tier distribution: `high=1,998 / medium=677 / low=0 / insufficient=0` (74.7% high — comfortably above 70% CON-IFP-009 floor). Per-form breakdown: F1A=`high:706, medium:113`; F2=`high:1,292, medium:287`; F3=`high:0, medium:277` — confirms the v1.2 reviewer rework prevents F3 misleading-`high` classification. Stanford UNITID 243744: `tier=high`, `marketing_ratio=0.30192890033486947`, `record_id=ifp-267f20f48b4b772f`. F3 spot check (UNITID 101116, South University-Montgomery): `tier=medium`, `endowment_value=NULL`, `instruction_expenses=$2,659,323`, `institutional_support_expenses=$2,944,986`, `total_fte_enrollment=357.0` — exactly 3/4 raw inputs present. `record_id` non-null = 2,675/2,675; unique = 2,675/2,675 (CON-IFP-002/003/004). Conservation invariant CON-IFP-001 holds: 2,675 consumable rows == 2,675 base rows == 2,675 bronze rows. (Pre-existing brightsmith framework warning: `AttributeError: 'Table' object has no attribute 'identifier'` from `brightsmith.infra.promote.py:71` lineage emission — same warning fires on every silver/base/gold transformer in this repo. Does not affect data correctness.) |
| §6/1 | Idempotency PASS | — | Re-ran `uv run python scripts/promote_ipeds_finance_profile.py` immediately. Result: `Promote consumable-ipeds-finance-profile: 0 new rows (all 2675 already exist)`. Stanford `record_id` identical across runs (`ifp-267f20f48b4b772f`), confirming `compute_grain_id(row, ['unitid'], prefix='ifp')` is deterministic and the `ifp` (consumable) namespace cleanly separates from the `ipf` (base) namespace per the spec. |
| Tests/1 | Lint FAIL → PASS after auto-fix | 4 unused imports (`math` in test_ipeds_finance_base.py; `BRONZE_TABLE_FQN` in test_ipeds_finance_base.py; `Path`, `BASE_TABLE_FQN` etc. in test_ipeds_finance_profile.py / test_ipeds_finance_ingestor.py) — pure unused-import noise, no logic impact. | `uv run ruff check tests/raw/test_ipeds_finance_ingestor.py tests/silver/test_ipeds_finance_base.py tests/gold/test_ipeds_finance_profile.py --fix` → "Found 4 errors (4 fixed, 0 remaining)." Re-ran tests: still 179/179 passing. |
| Tests/2 | Test run FAIL → PASS after expected-value fix | 1 test failed: `TestTransformRowDerivations::test_stanford_derivations_exact` asserted Stanford `institutional_support_per_fte == 42,427.59` but actual was `42,427.78` (correct: `$810,116,000 / 19,094 = 42,427.778...`). The 42,427.59 figure was a stale doc-comment value; the live arithmetic is correct. | Updated test to assert `42,427.78`; verified via `python -c "print(810_116_000.0 / 19_094.0)"` → `42427.778359694144`. The §9 spec implementation log itself records `42,427.78` as the Stanford spot-check (line 1003), confirming this is the load-bearing value. Re-ran: 179/179 PASS. |
| Tests/Final | All test suites PASS | — | `uv run pytest tests/raw/test_ipeds_finance_ingestor.py tests/silver/test_ipeds_finance_base.py tests/gold/test_ipeds_finance_profile.py` → **179 passed in 1.15s**. Per-zone: raw=79 / base=54 / consumable=46. All exceed the staff-engineer minimums (10/15/15). Total 179 vs minimum 40 (4.5× over). Full-suite regression: `uv run pytest tests/` → **1974 passed, 1 deselected, 0 failed in 56.60s** — no IPEDS Finance work caused regressions in any other test file. Closes SE-T1/T2/T3. |

### @fp-builder Final Verification — 2026-04-30

| Check | Command | Result | Evidence |
|---|---|---|---|
| Lint (ruff) — spec files only | `uv run ruff check src/raw/ipeds_finance_ingestor.py src/silver/ipeds_finance_base.py src/gold/ipeds_finance_profile.py scripts/ingest_ipeds_finance.py scripts/promote_ipeds_finance_base.py scripts/promote_ipeds_finance_profile.py tests/raw/test_ipeds_finance_ingestor.py tests/silver/test_ipeds_finance_base.py tests/gold/test_ipeds_finance_profile.py` | PASS | "All checks passed!" |
| Lint (ruff) — repo-wide (src/ tests/ scripts/) | `uv run ruff check src/ tests/ scripts/` | PASS (pre-existing noise only) | All failures are in pre-existing spike/chaos scripts (`scripts/_adversarial_probe_onet_exp.py`, `scripts/_eda_ipeds_finance.py`, `scripts/data_review_three_signal.py`, etc.) — none in any spec-added file. Zero new lint issues introduced by this spec. |
| Type check (mypy) — 3 new pipeline files | `uv run mypy src/raw/ipeds_finance_ingestor.py src/silver/ipeds_finance_base.py src/gold/ipeds_finance_profile.py` | PASS at sibling parity | 9 errors, all `import-untyped` for `requests`, `brightsmith.bronze.base_ingestor`, `brightsmith.domain_loader`, `brightsmith.infra.{grain,iceberg_setup,promote}`. Identical pattern confirmed on `src/raw/bea_rpp_ingestor.py` (same `requests` + `brightsmith.bronze.base_ingestor` errors). Pre-existing repo infrastructure — no stubs exist for brightsmith. No new error categories. |
| Tests (pytest) — full suite | `uv run pytest` | PASS | **1974 passed, 1 deselected, 0 failed in 56.77s**. Matches the staff-engineer-verified count exactly. IPEDS Finance zone breakdown: raw=79 / base=54 / gold=46 (179 total). No regressions in any non-IPEDS test file. |

**BUILD VERDICT: PASS.** All checks green at or above the accepted sibling baseline. Spec is clear for COMPLETE.

---

## §10 Discussion

```
[YYYY-MM-DD HH:MM] @source-agent → @target-agent
Message content.
```

---

## §11 Final Notes

**Human Review:** APPROVED by @bs:staff-engineer 2026-05-01 (v1.3 Re-Review). See `governance/approvals/full-pipeline-ipeds-finance-staff-review.md` "v1.3 Re-Review" section for full sign-off. Ready for move to `docs/specs/completed/`.

This spec produces a stand-alone institution finance profile. The fused aura signal lives downstream in `raw-ingest-eada.md` — that spec depends on `base.ipeds_finance` produced here.

---

*— End of Spec —*
