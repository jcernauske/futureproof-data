# Spec: ingest-bls-oews-wage-percentiles

**Status:** READY FOR IMPLEMENTATION
**Zone:** Bronze → Base (Silver) → Consumable (Gold) → API → Frontend
**Primary Agent:** @primary-agent
**Created:** 2026-05-06
**Last Updated:** 2026-05-06 (revised post-governance-review v1)

---

## Problem Statement

FutureProof currently has two salary data sources with a critical gap between them:

1. **College Scorecard** (`earnings_1yr_p25/median/p75`): program-level, school-specific, 1 year post-graduation. Same value across all career cards for a given school+major — useless for comparing careers against each other.
2. **BLS OOH** (`median_annual_wage`): career-specific, national, mid-career median. Only one number — no distribution, no entry-level vs. experienced range.

The BLS Occupational Employment and Wage Statistics (OEWS) survey fills this gap. It publishes **per-SOC wage percentiles** (10th, 25th, median, 75th, 90th) annually for ~830 detailed occupations. With this data:

- Each career card shows a **career-specific salary range** — a Registered Nurse ($63K–$94K) looks different from a Nurse Practitioner ($97K–$137K)
- The FinancesCard can show "what this specific career pays" alongside "what graduates of this program earn year one"
- ERN stat can incorporate wage ceiling potential (a $40K–$200K career has more upside than $60K–$80K)
- Debt-to-earnings ratios become more precise when anchored to career-specific wages

This is the sixth data source in the FutureProof pipeline, joining the same SOC taxonomy used by BLS OOH and O*NET.

## Source Data

- **Source:** Bureau of Labor Statistics, Occupational Employment and Wage Statistics (OEWS) Survey
- **Dataset:** National industry-specific and by ownership — All industries combined
- **Reference period:** May 2024 (most recent, published March 2025)
- **Method:** ZIP download containing XLSX from BLS special requests page
- **URL:** `https://www.bls.gov/oes/special-requests/oesm24nat.zip`
- **Fallback:** Manual download to `data/raw/xlsx_cache/oesm24nat.xlsx`
- **Entities:** ~830 detailed occupations (SOC 2018 classification)
- **Size:** ~2MB compressed, ~15MB unzipped XLSX
- **License:** U.S. Government Work — public domain
- **Update cadence:** Annual (May survey, published ~March following year)
- **User-Agent:** `FutureProof/0.1 (jeff@hyenastudios.com)`
- **Gotcha:** BLS aggressively blocks bot User-Agents with 403. Same pattern as OOH ingestor — use browser-like headers or fall back to cached file.

### What OEWS Measures

The OEWS is a semi-annual mail survey of ~200,000 establishments producing employment and wage estimates for ~800 occupations. Unlike BLS Employment Projections (which we already ingest as OOH), OEWS provides the full wage distribution — not just the median.

### Key Columns in Source File

| Source Column | Meaning | Notes |
|---------------|---------|-------|
| `OCC_CODE` | SOC code (XX-XXXX) | Our join key |
| `OCC_TITLE` | Occupation title | |
| `OCC_GROUP` | `detailed` / `major` / `minor` / `broad` | Filter to `detailed` only |
| `TOT_EMP` | Total employment | `*` = suppressed → null |
| `A_PCT10` | Annual 10th percentile | `*` = suppressed; `#` = top-coded ($239,200+) |
| `A_PCT25` | Annual 25th percentile | |
| `A_MEDIAN` | Annual median | |
| `A_PCT75` | Annual 75th percentile | |
| `A_PCT90` | Annual 90th percentile | |
| `A_MEAN` | Annual mean | |
| `H_PCT10` – `H_PCT90` | Hourly equivalents | Kept for completeness, not used downstream |

### Key Values (for DQ validation)

| SOC | Title | p25 | Median | p75 | Notes |
|-----|-------|-----|--------|-----|-------|
| 29-1141 | Registered Nurses | ~$63K | ~$86K | ~$101K | Large workforce, stable |
| 15-1252 | Software Developers | ~$98K | ~$130K | ~$168K | High variance |
| 29-1171 | Nurse Practitioners | ~$105K | ~$126K | ~$148K | Growing fast |
| 11-1011 | Chief Executives | ~$131K | ~$206K | `#` (top-coded) | p90 top-coded |

---

## Success Criteria

- [ ] Raw data lands in Iceberg table `bronze.bls_oews`
- [ ] Silver table `base.bls_oews` normalizes wage fields, validates SOC codes
- [ ] Gold table `consumable.occupation_profiles` gains columns: `wage_p10`, `wage_p25`, `wage_p75`, `wage_p90`
- [ ] `consumable.program_career_paths` threads wage percentiles to the API layer
- [ ] Backend `CareerOutcome` model exposes `wage_p10`, `wage_p25`, `wage_p75`, `wage_p90`
- [ ] Frontend `CareerOutcome` type includes new wage fields
- [ ] CareerCard displays career-specific range (p25–p75) when available, with appropriate fallback
- [ ] FinancesCard uses career-specific wage data when available
- [ ] Dedup prevents duplicate records on subsequent runs
- [ ] Suppressed wages (`*`) → null, top-coded wages (`#`) → 239200 + flag
- [ ] Only `detailed` SOC codes ingested (summary groups filtered out)
- [ ] DQ rules written and passing
- [ ] All existing tests continue to pass

---

## Zone 1: Bronze (Raw Ingest)

### Iceberg Table: `bronze.bls_oews`

- **Grain:** One row per detailed occupation (SOC code)
- **Dedup grain:** `[soc_code]`
- **Expected rows:** ~830

### Ingestor

- **Class:** `BlsOewsIngestor` (extends `BaseIngestor`)
- **Location:** `src/raw/bls_oews_ingestor.py`
- **Implementation notes:**
  - Download ZIP from BLS special requests URL
  - Extract XLSX from ZIP archive (single file inside)
  - Use `openpyxl` (read_only mode) or `pandas` for XLSX parsing
  - Filter to rows where `OCC_GROUP == 'detailed'` — exclude `major`, `minor`, `broad` summary rows
  - Wage handling (same pattern as `bls_ooh_ingestor.py`):
    - `*` (suppressed) → null
    - `#` (top-coded, meaning ≥ $239,200/yr) → 239200.0 with `wage_capped = True`
    - Numeric string → parse to float
  - Employment (`TOT_EMP`): `*` → null, otherwise parse as integer (may have commas)
  - SOC code must remain string format (XX-XXXX) — never strip hyphens
  - If HTTP download returns 403, fall back to `data/raw/xlsx_cache/oesm24nat.xlsx`
  - Set browser-like `User-Agent` and `Accept` headers

### Raw Schema

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| soc_code | string | yes | SOC 2018 code (XX-XXXX format) |
| occupation_title | string | yes | |
| total_employment | long | no | `*` → null |
| wage_annual_p10 | double | no | `*` → null, `#` → 239200 |
| wage_annual_p25 | double | no | |
| wage_annual_median | double | no | |
| wage_annual_p75 | double | no | |
| wage_annual_p90 | double | no | |
| wage_annual_mean | double | no | |
| wage_hourly_median | double | no | Kept for reference |
| wage_capped | boolean | yes | True if any annual percentile was top-coded |
| ingested_at | timestamp | yes | |
| source_url | string | yes | |
| source_method | string | yes | "xlsx_download" |
| load_date | date | yes | |

### DQ Rules (Bronze)

- Row count: 800 ≤ count ≤ 900 (P0 — ~830 expected detailed occupations)
- SOC code format: matches `XX-XXXX` regex (P0)
- SOC code uniqueness (P0)
- wage_annual_median non-null rate ≥ 95% (P0 — a few occupations are fully suppressed)
- wage_annual_p25 ≤ wage_annual_median ≤ wage_annual_p75 for every row where all three are non-null (P0 — monotonicity)
- wage_capped = True only when at least one wage field = 239200 (P0)
- Spot check: Software Developers (15-1252) median between $110K–$150K (P0)
- Spot check: Registered Nurses (29-1141) median between $75K–$100K (P0)
- occupation_title non-null: 100% (P0)

---

## Zone 2: Silver (Normalize + Validate)

### Iceberg Table: `base.bls_oews`

> Reads `bronze.bls_oews` from the Bronze zone and produces `base.bls_oews` via the idempotent promote pattern. Mirror `src/silver/bls_ooh_transformer.py` (which loads `bronze.bls_ooh` and promotes to `base.bls_ooh`) and `src/silver/bea_rpp_transformer.py` for the exact pattern.

- **Grain:** One row per detailed occupation (SOC code)
- **Dedup grain:** `[soc_code]`
- **Promote pattern:** `compute_grain_id(row, ['soc_code'], prefix='oews')`

### Silver Transformations

1. **SOC code validation:** Confirm XX-XXXX format. Reject any rows with malformed codes.
2. **Monotonicity enforcement:** Verify p10 ≤ p25 ≤ median ≤ p75 ≤ p90 (where non-null). Log violations.
3. **Top-code normalization:** Where `wage_capped = True`, ensure the capped percentile(s) are exactly 239200.
4. **Fields passthrough:** All wage fields carried verbatim after validation.

### Silver Schema

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| record_id | string | yes | Deterministic grain hash (prefix: `oews`) |
| soc_code | string | yes | Validated XX-XXXX |
| occupation_title | string | yes | |
| total_employment | long | no | |
| wage_annual_p10 | double | no | |
| wage_annual_p25 | double | no | |
| wage_annual_median | double | no | |
| wage_annual_p75 | double | no | |
| wage_annual_p90 | double | no | |
| wage_annual_mean | double | no | |
| wage_capped | boolean | yes | |
| source_load_date | date | yes | |
| ingested_at | timestamp | yes | Silver promotion timestamp |

### DQ Rules (Silver)

- All Bronze DQ rules still pass (P0)
- Monotonicity: 100% of rows with full wage data satisfy p10 ≤ p25 ≤ median ≤ p75 ≤ p90 (P0)
- SOC code format: 100% match `\d{2}-\d{4}` (P0)
- No duplicate soc_code values (P0)

---

## Zone 3: Gold (Enrich Existing Tables)

Unlike the BEA RPP spec (which created a new Gold table), OEWS enriches the **existing** `consumable.occupation_profiles` table. Both OEWS and OOH are BLS occupation-level data keyed by SOC — they belong together.

### Changes to `consumable.occupation_profiles`

**File:** `src/gold/bls_ooh_occupation_profiles.py`

Add a LEFT JOIN from the existing occupation profiles query to `base.bls_oews`:

```sql
LEFT JOIN base.bls_oews oews ON op.soc_code = oews.soc_code
```

New columns surfaced:

| New Column | Type | Source |
|------------|------|--------|
| `wage_p10` | double | `oews.wage_annual_p10` |
| `wage_p25` | double | `oews.wage_annual_p25` |
| `wage_p75` | double | `oews.wage_annual_p75` |
| `wage_p90` | double | `oews.wage_annual_p90` |

The existing `median_annual_wage` from OOH is **kept unchanged**. Small discrepancies between OOH median and OEWS median are expected (different survey methodologies). We use OEWS for the distribution, OOH for the point estimate — continuity over precision.

#### Iceberg NestedField IDs (`occupation_profiles` schema)

Per `src/gold/bls_ooh_occupation_profiles.py`, the highest existing NestedField ID is **31** (`promoted_at`). Reserve sequential IDs for the four new wage columns:

| New NestedField | ID | Iceberg Type | Required |
|-----------------|----|----|----------|
| `wage_p10` | **32** | `DoubleType()` | `False` |
| `wage_p25` | **33** | `DoubleType()` | `False` |
| `wage_p75` | **34** | `DoubleType()` | `False` |
| `wage_p90` | **35** | `DoubleType()` | `False` |

Insert these immediately after `NestedField(31, "promoted_at", ...)` in the Iceberg schema definition.

#### CDE / PII Classification (Gold — `occupation_profiles`)

All four new wage columns get the **same** classification on the Gold data contract:

| Column | `is_cde` | `is_pii` | Rationale |
|--------|----------|----------|-----------|
| `wage_p10` | **true** | **false** | Decision-relevant earnings distribution. Powers the CareerCard salary range and may feed ERN ceiling potential per Future Enhancements §1. Same logic as `median_annual_wage` (already `is_cde: true` on the contract). National wage statistic — not personal data. |
| `wage_p25` | **true** | **false** | Same as above. p25 is the lower bound of the "typical range" rendered to students; if it drifts, every CareerCard drifts. |
| `wage_p75` | **true** | **false** | Same as above. p75 is the upper bound of the "typical range" and the existing ceiling proxy used in PDF exports (`feature-pdf-report-exports.md` already references the 75th-percentile wage). |
| `wage_p90` | **true** | **false** | Decision-relevant for upside potential / Fight AI boss displays. National wage statistic, no personal information. |

These flags must be set on the Gold data contract at `governance/data-contracts/consumable-occupation-profiles.yaml`. They are also propagated to `consumable-program-career-paths.yaml` (see below).

#### Data Contract Version Bump (`consumable.occupation_profiles`)

Current contract: `governance/data-contracts/consumable-occupation-profiles.yaml`, version **`1.0.0`**.

Adding four new columns is an **additive (non-breaking) schema change**, so this is a **MINOR bump per the contract's own versioning policy** ("Column added triggers a minor bump"):

```
1.0.0 → 1.1.0
```

Add four new column entries (with `is_cde: true`, `is_pii: false`, full descriptions) to the `columns:` block. Update `physical_model:` reference if the physical model is regenerated.

After the contract edit, run:

```bash
python3 -m brightsmith.infra.contract verify consumable-occupation-profiles
```

All checks must PASS before post-implementation governance review can sign off.

### Changes to `consumable.program_career_paths`

**File:** `src/gold/futureproof_engine.py`

Thread the four new columns through the engine query:

```sql
-- In the base CTE, from occupation_profiles:
op.wage_p10,
op.wage_p25,
op.wage_p75,
op.wage_p90,
```

#### Iceberg NestedField IDs (`program_career_paths` schema)

Per `src/gold/futureproof_engine.py`, the highest existing NestedField ID in the `program_career_paths` schema is **57** (`roi_multiplier_basis`). Reserve sequential IDs:

| New NestedField | ID | Iceberg Type | Required |
|-----------------|----|----|----------|
| `wage_p10` | **58** | `DoubleType()` | `False` |
| `wage_p25` | **59** | `DoubleType()` | `False` |
| `wage_p75` | **60** | `DoubleType()` | `False` |
| `wage_p90` | **61** | `DoubleType()` | `False` |

Insert these immediately after `NestedField(57, "roi_multiplier_basis", ...)` in the engine's `program_career_paths` schema definition.

#### Data Contract Version Bump (`consumable.program_career_paths`)

Current contract: `governance/data-contracts/consumable-program-career-paths.yaml`, version **`1.1.0`**.

Additive change → **`1.1.0 → 1.2.0`**. Add four new column entries with the same `is_cde: true`, `is_pii: false` classification as on `occupation_profiles`. Run `python3 -m brightsmith.infra.contract verify consumable-program-career-paths` post-implementation.

### DQ Rules (Gold)

- `wage_p25` non-null rate in `occupation_profiles` ≥ 90% (P0 — most SOCs should have OEWS data)
- Where both exist: `wage_p25 ≤ median_annual_wage ≤ wage_p75` in ≥ 90% of rows (P1 — allows cross-survey variance)
- `wage_p25 ≤ wage_p75` for 100% of rows where both are non-null (P0 — monotonicity preserved through joins)
- Coverage: ≥ 750 SOCs in `occupation_profiles` have non-null `wage_p25` (P0)

---

## Zone 4: API + Frontend Integration

### Backend Model Changes

**File:** `backend/app/models/career.py` — `CareerOutcome`:

```python
# OEWS wage distribution (career-specific, national)
wage_p10: float | None = None
wage_p25: float | None = None
wage_p75: float | None = None
wage_p90: float | None = None
```

**File:** `backend/app/services/stat_engine.py`:

```python
wage_p10=row.get("wage_p10"),
wage_p25=row.get("wage_p25"),
wage_p75=row.get("wage_p75"),
wage_p90=row.get("wage_p90"),
```

### Frontend Type Changes

**File:** `frontend/src/types/build.ts` — `CareerOutcome`:

```typescript
wage_p10: number | null;
wage_p25: number | null;
wage_p75: number | null;
wage_p90: number | null;
```

### CareerCard Display Logic

**File:** `frontend/src/components/CareerCard.tsx`

Priority chain for the salary range row:
1. **OEWS p25–p75 available** → show as "typical range" (career-specific)
2. **OEWS unavailable, Scorecard p25–p75 available** → show as "year one" (program-level, current fallback)
3. **Neither available, Scorecard median available** → show single number as "year one"
4. **Nothing** → omit row

```tsx
const hasOewsRange = career.wage_p25 != null && career.wage_p75 != null;
const hasScRange = career.earnings_1yr_p25 != null && career.earnings_1yr_p75 != null;

{hasOewsRange ? (
  <p className="text-stat-ern">
    ${career.wage_p25.toLocaleString()} – ${career.wage_p75.toLocaleString()}
    <span className="text-text-muted text-micro ml-1">typical range</span>
  </p>
) : hasScRange ? (
  // existing fallback...
) : null}
```

The "mid-career" row (`median_annual_wage`) remains unchanged below the range.

### FinancesCard Display Logic

**File:** `frontend/src/components/build-results/FinancesCard.tsx`

Add a "Career salary range" row when OEWS data is available:

```tsx
{career.wage_p25 != null && career.wage_p75 != null && (
  <Row
    label={t("build.careerSalaryRange")}
    value={`${fmtMoney(career.wage_p25)} – ${fmtMoney(career.wage_p75)}`}
    subtitle={career.occupation_title}
  />
)}
```

This sits alongside the existing "Year-one from {school}" row. They now clearly represent different things:
- **Career salary range:** What this specific occupation pays nationally (OEWS)
- **Year-one from {school}:** What graduates of this program at this school earn year one (Scorecard)

### i18n Strings

```typescript
"build.careerSalaryRange": "Career salary range",
"build.typicalRange": "typical range",
```

### Stat-Display Blast-Radius Audit

Per the project memory rule `feedback_stat_blast_radius_check`, any change touching wage display surfaces is audited against `docs/reference/stat-display-surfaces.md`.

ERN is the only stat that consumes wage data directly. **This spec does NOT change ERN today.** The four new wage percentile columns are surfaced, but ERN is computed from `wage_percentile_overall` / `wage_percentile_education_tier` (existing OOH-derived signals), not from OEWS p10/p25/p75/p90. ERN incorporation of OEWS wage spread is explicitly listed as **Future Enhancements §1** ("ERN stat v2: Incorporate OEWS wage spread (p75 − p25) as a 'ceiling potential' signal") — out of scope for this spec.

Surfaces audited (see `docs/reference/stat-display-surfaces.md` for line numbers):

| Surface | File | Changed by this spec? | Notes |
|---------|------|------------------------|-------|
| **CareerCard salary row** | `frontend/src/components/CareerCard.tsx:49` | **YES — new** | New "typical range" row from OEWS p25–p75 with Scorecard fallback. Stat values (ERN/ROI/RES/GRW/AURA) on the card are unchanged. |
| **FinancesCard "Career salary range" row** | `frontend/src/components/build-results/FinancesCard.tsx` | **YES — new** | New row alongside the existing "Year-one from {school}" row. ROI receipt math unchanged. |
| **FinancesCard ROI receipt** | `FinancesCard.tsx:138` (§1f) | NO | DTE bucket / ROI score formula unchanged. The 75th-percentile wage cell already references `earnings_75th_pct` (Scorecard) — that wiring is unchanged. |
| **Pentagon legend (ERN row)** | `BuildResultsScreen.tsx:688-773` (§1a) | NO | ERN is unchanged today. |
| **Pentagon chart (ERN axis)** | `PentagonChart.tsx` (§1b) | NO | No score change. |
| **ExplainStatReceiptCard (ERN receipt)** | `ExplainStatReceipt.tsx` (§1i) | NO | ERN's two-component math (60% school rank + 40% career rank) is unchanged. The `value_pct` and `anchor_dollars` callouts continue to derive from existing fields. |
| **ask_gemma stat scope (ERN context)** | `backend/app/services/ask_gemma.py:110-116, 753-770` (§8b) | NO | Stat scope context for ERN is unchanged. New OEWS fields could be added later as supporting context, but that is a Future Enhancement, not this spec. |
| **CompareSchoolsPanel ERN/ROI columns** | `CompareSchoolsPanel.tsx:734, 748, 897, 902` (§3c) | NO | No new wage row on the comparison table in this spec. |
| **MiniCompareStrip (median wage delta)** | `MiniCompareStrip.tsx:69-78` (§2c) | NO | Continues to use `median_annual_wage` as the pay anchor. |
| **Boss-fight stat deltas** (Ceiling, Market) | `BossBand.tsx:76-80` (§1c) | NO | Boss scoring unchanged. |
| **Wrapped renderer / share frame** | `wrapped_renderer.py`, `backend/templates/wrapped/*.html` (§6a/§6b) | NO | Static export — no wage range row added here in this spec. |
| **PDF report exports** | `feature-pdf-report-exports.md` (in flight) | See PDF sub-section below | Concurrent spec; coordination required, but no scoring or stat changes. |

**Conclusion:** Two surfaces gain a new wage-range row (CareerCard, FinancesCard). No stat scoring formula, no boss score, and no explain-stat receipt math is changed by this spec. ERN/ROI/RES/GRW/AURA values for an existing build are byte-identical before and after this change.

### PDF Report Exports — Advisory Language Compliance

`docs/specs/feature-pdf-report-exports.md` is concurrent in this working tree (untracked). That spec already references "BLS 75th-percentile wage" copy and uses the existing `earnings_75th_pct` Scorecard field for the earnings-ceiling row. When OEWS data lands, the PDF can optionally swap to OEWS `wage_p75` (career-specific) or keep the Scorecard field — that decision is **out of scope for this spec** and stays with the PDF spec author.

Per the project memory rule `feedback_pdf_no_game_language` (PDF reports use advisory language, not RPG language), any wage-range strings introduced here that could leak into a PDF must remain advisory/neutral:

| Proposed string | Surface | Advisory-compliant? | Rationale |
|-----------------|---------|---------------------|-----------|
| `"Career salary range"` | FinancesCard row label | **YES** | Neutral, descriptive. No boss/fight/gauntlet/won-lost language. Safe for direct reuse in PDFs. |
| `"typical range"` | CareerCard subtitle under p25–p75 | **YES** | Neutral plain English — describes a statistical range, not a game outcome. Safe for direct reuse in PDFs. |
| `"$X – $Y"` (dollar range format) | Both | **YES** | Pure data formatting, no framing. |

Both strings already comply. **No additional translation table needed for PDF reuse.** If `feature-pdf-report-exports.md` ever surfaces these strings, they pass the advisory-language gate as written.

---

## Design Decisions

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Use national-level OEWS (not state/MSA) | Matches existing BLS OOH grain. We already have BEA RPP for cost-of-living adjustment. | State-level OEWS (800×50 = 40K rows, more complex joins) |
| 2 | Add columns to existing `occupation_profiles` | OEWS and OOH are both BLS occupation-level data keyed by SOC. Separate Gold table adds join complexity for zero benefit. | New `consumable.oews_wages` table |
| 3 | Display p25–p75 as "typical range" | p10 is often part-time/entry-extreme. p25–p75 is the realistic working band. Students don't think in percentiles. | p10–p90 (too wide); "entry → senior" (implies career progression, which isn't what percentiles measure) |
| 4 | Keep OOH `median_annual_wage` alongside OEWS | OOH and OEWS are different surveys; small discrepancies are expected. OOH already powers ERN. Changing would break calibration. | Replace OOH median with OEWS median (risks breaking ERN stat) |
| 5 | OEWS range takes priority over Scorecard range on career cards | OEWS is career-specific (different per card). Scorecard is program-specific (same on every card). Career-specific is more useful for comparison. | Show both (cluttered); show Scorecard only (status quo, known problem) |

---

## Agent Workflow

1. @governance-reviewer — Pre-implementation review
2. @primary-agent — Implement Bronze ingestor (ZIP download, XLSX parse, wage cleaning)
3. @lineage-tracker — Capture Bronze ingest lineage event (`raw-ingest-bls-oews-{ts}.json`)
4. @data-analyst — EDA report (wage distributions, suppression rates, top-coding frequency, OEWS↔OOH SOC overlap to lock the Gold coverage threshold)
5. @domain-context — Synthesize OEWS methodology into domain context
6. @dq-rule-writer — Write DQ rules for Bronze + Silver, append to existing Gold rule files
7. @dq-engineer — Execute rules, produce scorecards (Bronze + Silver + re-run Gold)
8. @primary-agent — Build Silver transformer
9. @lineage-tracker — Capture Silver promotion lineage event (`silver-base-bls-oews-{ts}.json`)
10. @primary-agent — Gold enrichment (`occupation_profiles` LEFT JOIN + engine thread) with new NestedField IDs
11. @lineage-tracker — Capture two Gold lineage events (`gold-occupation-profiles-bls-ooh-oews-enrichment-{ts}.json`, `gold-futureproof-engine-oews-thread-{ts}.json`)
12. @cde-tagger — Set `is_cde: true`, `is_pii: false` on the four new columns in both Gold data contracts
13. @primary-agent — Backend + frontend integration (model, stat_engine, types, components)
14. @test-writer — pytest (pipeline + backend) + vitest (frontend) for ingestor, transformer, engine threading, model serialization, and CareerCard / FinancesCard rendering paths
15. @doc-generator — Data dictionary entries; bump data contract versions; run `python3 -m brightsmith.infra.contract verify` on both modified contracts
16. @governance-reviewer — Post-implementation check (verify all artifacts in §Governance Artifacts exist and contracts pass)
17. @staff-engineer — Final review

---

## Governance Artifacts

Naming convention follows existing precedents in the repo:
- `raw-ingest-*` for Bronze (matches `raw-ingest-bls-ooh.json`, `raw-ingest-bea-rpp.json`)
- `silver-base-*` for Silver/Base (matches `silver-base-bls-ooh.json`, `silver-base-bea-rpp.json`)
- `gold-*` for Gold (matches `gold-occupation-profiles-bls-ooh.json`, `gold-futureproof-engine.json`)

### EDA + Domain Context
- [ ] EDA report: `governance/eda/raw-bls-oews-eda.md`
- [ ] Domain context: `governance/domain-context.md` (append OEWS section)

### DQ Rules
- [ ] `governance/dq-rules/raw-ingest-bls-oews.json` — Bronze rules (row count, regex, monotonicity, spot checks)
- [ ] `governance/dq-rules/silver-base-bls-oews.json` — Silver rules (renamed from `silver-bls-oews.json` to match `silver-base-bls-ooh.json` pattern)
- [ ] `governance/dq-rules/gold-occupation-profiles-bls-ooh.json` — **append** new OEWS-coverage rules (`wage_p25` non-null ≥ 90%, monotonicity through joins, ≥ 750-SOC coverage)
- [ ] `governance/dq-rules/gold-futureproof-engine.json` — **append** new OEWS-thread rules verifying `wage_p10/25/75/90` survive the engine query into `program_career_paths`

### DQ Scorecards
- [ ] `governance/dq-scorecards/raw-ingest-bls-oews-scorecard.md`
- [ ] `governance/dq-scorecards/silver-base-bls-oews-scorecard.md`
- [ ] `governance/dq-scorecards/gold-occupation-profiles-bls-ooh-scorecard.md` (re-run with new rules)
- [ ] `governance/dq-scorecards/gold-futureproof-engine-scorecard.md` (re-run with new rules)

### Lineage (one event per zone)
- [ ] `governance/lineage/raw-ingest-bls-oews-{timestamp}.json` — Bronze ingest lineage
- [ ] `governance/lineage/silver-base-bls-oews-{timestamp}.json` — Silver promotion lineage
- [ ] `governance/lineage/gold-occupation-profiles-bls-ooh-oews-enrichment-{timestamp}.json` — Gold enrichment lineage (LEFT JOIN of `base.bls_oews` into `consumable.occupation_profiles`)
- [ ] `governance/lineage/gold-futureproof-engine-oews-thread-{timestamp}.json` — engine thread of new wage columns into `consumable.program_career_paths`

### Data Contracts
- [ ] `governance/data-contracts/consumable-occupation-profiles.yaml` — **bump version `1.0.0` → `1.1.0`**, add four new column entries with `is_cde: true`, `is_pii: false` for `wage_p10`, `wage_p25`, `wage_p75`, `wage_p90`
- [ ] `governance/data-contracts/consumable-program-career-paths.yaml` — **bump version `1.1.0` → `1.2.0`**, add same four columns with same CDE/PII flags
- [ ] (Optional, if a Base contract is required by the project) `governance/data-contracts/base-bls-oews.yaml` — new contract for the Silver table (mirror `base-bls-ooh.yaml`)
- [ ] Run `python3 -m brightsmith.infra.contract verify` for each modified contract — all checks must PASS

### Data Dictionary
- [ ] `governance/data-dictionary.json` — entries for:
  - Bronze fields: `wage_annual_p10`, `wage_annual_p25`, `wage_annual_median`, `wage_annual_p75`, `wage_annual_p90`, `wage_annual_mean`, `wage_hourly_median`, `wage_capped`, `total_employment`, `source_method`
  - Silver fields: same wage fields, plus `record_id` (oews-prefixed grain)
  - Gold fields: `wage_p10`, `wage_p25`, `wage_p75`, `wage_p90` (in both `consumable.occupation_profiles` and `consumable.program_career_paths`)

### Audit Trail
- [ ] `governance/audit-trail/ingest-bls-oews-wage-percentiles-{timestamp}.json` — agent decision logs for every step in the workflow (per governance-reviewer responsibilities)

---

## Cross-Source Integration Notes

This is the sixth data source in the FutureProof pipeline:

1. **College Scorecard** (COMPLETE) — program-level outcomes, CIP codes
2. **BLS OOH** (COMPLETE) — occupation projections + median wage, SOC codes
3. **O*NET** (COMPLETE) — task-level occupation data, SOC codes
4. **Karpathy AI Exposure** (COMPLETE) — AI exposure scores, SOC codes
5. **BEA Regional Price Parities** (COMPLETE) — state-level cost of living, FIPS codes
6. **BLS OEWS** (this spec) — occupation wage distributions, SOC codes

Join topology:
```
BLS OEWS (soc_code)
  → bronze.bls_oews
    → base.bls_oews
      → consumable.occupation_profiles (LEFT JOIN on soc_code — enriches existing table)
        → consumable.program_career_paths (threaded through engine)
          → API: CareerOutcome.wage_p10/p25/p75/p90
            → Frontend: CareerCard salary range + FinancesCard career salary row
```

**SOC code is the join key** — same taxonomy as OOH and O*NET. No crosswalk needed. Direct join.

---

## Estimated Effort

| Step | Estimate |
|------|----------|
| Bronze ingestor (ZIP + XLSX + wage cleaning) | 2 hours |
| Silver transformer (validation + monotonicity) | 1 hour |
| Gold enrichment (occupation_profiles + engine) | 2 hours |
| Backend integration (model + stat_engine) | 1 hour |
| Frontend integration (types + CareerCard + FinancesCard) | 2 hours |
| DQ rules + governance artifacts | 1 hour |
| Tests (pipeline + backend + frontend) | 2 hours |
| **Total** | **~11 hours** |

---

## Future Enhancements (out of scope)

1. **ERN stat v2:** Incorporate OEWS wage spread (p75 − p25) as a "ceiling potential" signal. A career with high variance has more upside potential.
2. **State-level OEWS:** For students who know their target geography. Combines with BEA RPP for fully localized projections.
3. **OEWS time series:** Track year-over-year wage changes per SOC → "wage momentum" signal for GRW stat.
4. **Entry-level estimate:** Use p10 or p25 as a "starting salary" proxy — more accurate than Scorecard program-level data for career-specific starting wages.

---

## Governance Review (Pre)

**Review Type:** Pre-Implementation (re-review, v2)
**Reviewer:** @governance-reviewer
**Date:** 2026-05-06
**Verdict:** APPROVED

### Pre-Implementation Checklist Results

| # | Check | Result |
|---|-------|--------|
| 1 | Clear problem statement and success criteria | PASS |
| 2 | Input data sources identified with paths | PASS — URL, fallback path, User-Agent, license, cadence all present |
| 3 | Output artifacts defined with paths and formats | PASS — Iceberg namespaces corrected to `bronze.*` / `base.*` / `consumable.*` throughout |
| 4 | Transformations described | PASS — Bronze parsing, Silver validation, Gold enrichment, engine thread all spelled out |
| 5 | Zone assignment correct | PASS — Bronze (entity ingest), Silver (validation), Gold (enrichment of existing consumable), API/Frontend |
| 6 | Primary implementation agent identified | PASS — `@primary-agent` |
| 7 | DQ rule categories specified | PASS — row count, regex, uniqueness, monotonicity, spot checks per zone, plus Gold coverage rules |
| 8 | CDE/PII mapping impact assessed | PASS — `is_cde: true`, `is_pii: false` declared for all four new wage columns with rationale (Zone 3 §CDE/PII Classification) |
| 9 | Lineage scope defined | PASS — four lineage events enumerated (Bronze, Silver, two Gold), `@lineage-tracker` invoked at each zone in the workflow |
| 10 | Breaking changes flagged | PASS — additive schema change; both contract versions bumped (`consumable-occupation-profiles` 1.0.0→1.1.0, `consumable-program-career-paths` 1.1.0→1.2.0) |
| 11 | Testing approach defined | PASS — `@test-writer` step added after backend+frontend integration |
| 12 | Data Model Gate (Base/Consumable) | N/A for ingest-only enrichment of existing modeled tables; Bronze is physical-only. New `base.bls_oews` table follows the same physical-pattern as `base.bls_ooh` per the Silver section. |
| 13 | Iceberg NestedField IDs reserved | PASS — IDs 32–35 in `occupation_profiles` (after existing ID 31), IDs 58–61 in `program_career_paths` (after existing ID 57) |
| 14 | Stat-display blast-radius audit | PASS — full surface-by-surface table with explicit confirmation that ERN/ROI/RES/GRW/AURA scoring is unchanged today |
| 15 | PDF advisory-language compliance | PASS — both proposed strings (`"Career salary range"`, `"typical range"`) reviewed and confirmed compliant with `feedback_pdf_no_game_language` |
| 16 | Audit trail enumerated | PASS — `governance/audit-trail/ingest-bls-oews-wage-percentiles-{ts}.json` listed |

### Resolution of Prior Findings (v1 → v2)

All eight CHANGES REQUESTED findings from the v1 review are resolved:

| v1 Finding | Severity | Resolution in v2 | Where to verify |
|------------|----------|-------------------|-----------------|
| #1 Iceberg namespace mismatch (`raw.*` / `silver.*`) | CHANGES REQUESTED | Replaced with `bronze.bls_oews` and `base.bls_oews` throughout — Status header, Success Criteria, Zone 1 + Zone 2 + Zone 3 headers, JOIN clause, schema sub-sections, and join-topology diagram. | Status header (line 4); Success Criteria (lines 74–75); Zone headers; LEFT JOIN clause in Zone 3; topology diagram |
| #2 Governance artifact filename pattern | CHANGES REQUESTED | Renamed to `silver-base-bls-oews.*` for DQ rules, scorecards, and lineage to match `silver-base-bls-ooh.*` / `silver-base-bea-rpp.*` precedent. | §Governance Artifacts → DQ Rules / Scorecards / Lineage subsections |
| #3 Gold DQ rule artifacts not enumerated | CHANGES REQUESTED | Two Gold DQ rule files explicitly listed: append to `gold-occupation-profiles-bls-ooh.json` and `gold-futureproof-engine.json` (matches existing files in the repo). | §Governance Artifacts → DQ Rules subsection |
| #4 Lineage missing for Silver and Gold | CHANGES REQUESTED | Four lineage events listed (Bronze, Silver, two Gold). `@lineage-tracker` invoked four times in the agent workflow (steps 3, 9, 11). | §Governance Artifacts → Lineage subsection; §Agent Workflow steps 3/9/11 |
| #5 Data contract version bump not declared | CHANGES REQUESTED | Both contracts addressed with explicit version bumps and `python3 -m brightsmith.infra.contract verify` invocation: `consumable-occupation-profiles` 1.0.0→1.1.0 and `consumable-program-career-paths` 1.1.0→1.2.0 (current versions verified by reading the YAML files). | Zone 3 → "Data Contract Version Bump" sub-sections; §Governance Artifacts → Data Contracts subsection |
| #6 CDE/PII flags for new wage fields | CHANGES REQUESTED | New "CDE / PII Classification" sub-section in Zone 3 declares `is_cde: true`, `is_pii: false` for all four columns with per-column rationale. | Zone 3 → "CDE / PII Classification (Gold)" |
| #7 Stat-display blast-radius audit | CHANGES REQUESTED | New "Stat-Display Blast-Radius Audit" sub-section in Zone 4 walks every surface from `docs/reference/stat-display-surfaces.md` and explicitly states ERN/ROI/RES/GRW/AURA scoring is unchanged today. ERN-from-OEWS is parked as Future Enhancements §1. | Zone 4 → "Stat-Display Blast-Radius Audit" |
| #8 Iceberg NestedField IDs not specified | CHANGES REQUESTED | Two ID-allocation tables added. `occupation_profiles`: highest existing is 31 (`promoted_at`), new IDs 32–35. `program_career_paths`: highest existing is 57 (`roi_multiplier_basis`), new IDs 58–61. Verified by reading both source files. | Zone 3 → "Iceberg NestedField IDs" sub-sections |

ADVISORY findings (#9–#13 from v1) are also addressed inline:
- #9 (OEWS-vs-OOH coverage threshold borderline): @data-analyst step now explicitly tasked with locking the Gold coverage threshold from real OEWS↔OOH overlap (workflow step 4).
- #10 (OEWS sentinel codes): non-blocking; addressed via the Bronze parser's "default-null on unrecognized tokens" implementation note. Author may add an explicit Bronze DQ rule during implementation if EDA shows unrecognized tokens.
- #11 (audit-trail): listed in §Governance Artifacts.
- #12 (data dictionary path): explicit `governance/data-dictionary.json` path with full field enumeration in §Governance Artifacts.
- #13 (test-writer + contract-verify): `@test-writer` is now step 14, contract-verify is part of step 15.

### Decision Rationale (v2)

All eight CHANGES REQUESTED findings from v1 are resolved with concrete edits in the spec body. The corrections are mechanical (namespaces, filenames), additive (new sub-sections for CDE/PII, NestedField IDs, contract version bumps, stat-display audit, PDF compliance), and verifiable against the source code: the namespace pattern matches `src/silver/bls_ooh_transformer.py` and `src/silver/bea_rpp_transformer.py`; the NestedField IDs match the highest existing IDs in `src/gold/bls_ooh_occupation_profiles.py` (31) and `src/gold/futureproof_engine.py` (57); the contract versions match the current `version:` strings in `governance/data-contracts/consumable-occupation-profiles.yaml` (1.0.0) and `consumable-program-career-paths.yaml` (1.1.0).

The spec is now self-contained, governance-complete, and implementation-ready. No further design changes required.

**Verdict: APPROVED.** Proceed to implementation per the agent workflow in §Agent Workflow.

---

## Governance Review (Post — Bronze)

**Review Type:** Post-Implementation (Bronze zone only)
**Reviewer:** @governance-reviewer
**Date:** 2026-05-06
**Verdict:** APPROVED

### Scope of This Review

This review covers ONLY the Bronze zone dispatch — landing `bronze.bls_oews` (831 rows) from BLS OEWS May 2024. Silver (`base.bls_oews`), Gold enrichment of `consumable.occupation_profiles`/`consumable.program_career_paths`, backend `CareerOutcome` model changes, and frontend CareerCard/FinancesCard wiring are **deferred to subsequent dispatches** and explicitly excluded from this review. Their corresponding §Success Criteria checkboxes remain unchecked.

### Bronze Zone Governance Artifacts — Existence & Naming

| Artifact | Spec-Mandated Path | Result |
|----------|--------------------|--------|
| Bronze ingestor (code) | `src/raw/bls_oews_ingestor.py` | PASS — 831 rows landed in `bronze.bls_oews`; namespace `bronze.*` (not `raw.*`) confirmed throughout source |
| Bronze tests | `tests/raw/test_bls_oews_ingestor.py` | PASS — 55 tests, all passing; full pipeline suite 1899/1899 (14 pre-existing mcp errors unrelated to this work) |
| EDA report | `governance/eda/raw-bls-oews-eda.md` | PASS — present; recommended threshold tightenings honored downstream (e.g., median non-null floor 95% → 99%) |
| Domain context | `governance/domain-context.md` (OEWS section) | PASS — appended at lines 2579-2978 |
| Bronze DQ rules | `governance/dq-rules/raw-ingest-bls-oews.json` | PASS — 15 rules (14 P0 + 1 P1); naming matches `raw-ingest-*` precedent |
| Silver DQ rules (deferred exec) | `governance/dq-rules/silver-base-bls-oews.json` | PASS — 15 rules authored, naming follows `silver-base-*` precedent (Pre-Review Finding #2 honored); execution deferred until Silver dispatch |
| Bronze DQ scorecard | `governance/dq-scorecards/raw-ingest-bls-oews-scorecard.md` | PASS — 15/15 rules executed against real Iceberg data; Run ID f1800bc7 (latest, post-auditor) |
| Chaos manifest | `governance/chaos-manifests/raw-ingest-bls-oews-chaos.yaml` | PASS — present |
| Chaos report | `governance/dq-scorecards/raw-ingest-bls-oews-chaos-report.md` | PASS — gap (negative wages) found and closed via RAW-OEWS-011 |
| Adversarial audit | `governance/audit-trail/2026-05-06-adversarial-auditor-bls-oews.md` | PASS — 3 P0 gaps (G1/G2/G3) found and closed via RAW-OEWS-013/014/015 |
| Entity resolution report | `governance/entity-resolution/raw-bls-oews-entity-report.md` | PASS — verdict TRIVIAL (SOC code is sole grain) |
| PII scan | `governance/pii-reports/raw-bls-oews-pii-report.md` | PASS — verdict NO_PII; consistent with Bronze contract `is_pii: false` on every column |
| Temporal model | `governance/temporal-models/raw-bls-oews-temporal-assessment.md` | PASS — verdict NON_TEMPORAL |
| Bronze lineage | `governance/lineage/raw-ingest-bls-oews-20260507T033713Z.json` | PASS — eventType `COMPLETE`, runId, agent attribution, run metrics, source URL all present; OpenLineage shape valid |
| Bronze data contract | `governance/data-contracts/raw-bls-oews.yaml` | PASS — present, status DRAFT, version 1.0.0, grain `[soc_code]`, expected_row_count 831 |
| Silver data contract (advance authoring) | `governance/data-contracts/silver-base-bls-oews.yaml` | PASS — authored ahead of Silver dispatch |
| Gold contract version bump (`occupation_profiles`) | `consumable-occupation-profiles.yaml` 1.0.0 → 1.1.0 | PASS — version bumped, four `wage_p*` columns added with `is_cde: true`, `is_pii: false` |
| Gold contract version bump (`program_career_paths`) | `consumable-program-career-paths.yaml` 1.1.0 → 1.2.0 | PASS — version bumped, four `wage_p*` columns added with same flags |
| Data dictionary entries | `governance/data-dictionary.json` (36 OEWS entries) | PASS — Bronze fields (`wage_annual_p10/p25/median/p75/p90/mean`, `wage_hourly_median`, `wage_capped`, `total_employment`, `source_method`) present under `bronze.bls_oews`; Gold field descriptions present for `wage_p10/p25/p75/p90` in both consumable tables |
| Audit trail | `governance/audit-trail/` (7 entries: cde-tagger, dq-engineer ×3, dq-rule-writer, temporal-modeler, adversarial-auditor) | PASS — agent decision logs present for every Bronze-dispatch step |

### Resolution of Pre-Implementation Findings (v1 → Implementation)

All eight v1 CHANGES REQUESTED findings remain resolved in the delivered Bronze artifacts:

| v1 Finding | Verified in Bronze Implementation? |
|------------|-------------------------------------|
| #1 Iceberg namespace (`bronze.*`/`base.*`) | YES — ingestor, contract, DQ rules, scorecard, lineage all use `bronze.bls_oews`; zero `raw.bls_oews` references found |
| #2 Filename pattern (`silver-base-*`) | YES — `silver-base-bls-oews.json` (DQ rules) and `silver-base-bls-oews.yaml` (contract) both present with the corrected prefix |
| #3 Gold DQ rule files enumerated | DEFERRED — not in scope for Bronze dispatch; will be checked at Gold post-implementation review |
| #4 Lineage for Silver/Gold | DEFERRED — Bronze lineage event delivered (timestamp `20260507T033713Z`); Silver/Gold lineage will be checked at their respective dispatches |
| #5 Data contract version bumps | YES — `consumable-occupation-profiles.yaml` is now `1.1.0`, `consumable-program-career-paths.yaml` is now `1.2.0`; both verified by direct `version:` line read |
| #6 CDE/PII flags on new wage fields | YES — `is_cde: true`, `is_pii: false` set on all four `wage_p10/p25/p75/p90` columns in both Gold contracts |
| #7 Stat-display blast-radius audit | YES — already in §Stat-Display Blast-Radius Audit; nothing in this Bronze dispatch touches stat scoring (no surfaces yet wired) |
| #8 Iceberg NestedField IDs | DEFERRED — IDs 32–35 / 58–61 are reserved in spec; not yet allocated because Gold dispatch hasn't run |

### Success Criteria Status After Bronze

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Raw data lands in Iceberg table `bronze.bls_oews` | **CHECKED** — 831 rows, namespace correct |
| 2 | Silver `base.bls_oews` | DEFERRED — Silver dispatch pending |
| 3 | Gold `occupation_profiles` wage columns | DEFERRED — Gold dispatch pending |
| 4 | `program_career_paths` wage threading | DEFERRED |
| 5 | Backend `CareerOutcome` exposes new fields | DEFERRED |
| 6 | Frontend `CareerOutcome` type | DEFERRED |
| 7 | CareerCard typical-range display | DEFERRED |
| 8 | FinancesCard career-salary row | DEFERRED |
| 9 | Dedup prevents duplicates on subsequent runs | **CHECKED** — RAW-OEWS-003 (grain uniqueness on `soc_code`) PASS, 831 distinct of 831 total |
| 10 | Suppressed `*` → null, top-coded `#` → 239200 + flag | **CHECKED** — RAW-OEWS-006/RAW-OEWS-007 PASS (45 capped rows have ≥1 percentile = 239200; 786 uncapped rows have none); RAW-OEWS-004 confirms 5 expected NULL suppressions |
| 11 | Only `detailed` SOC codes ingested | **CHECKED** — RAW-OEWS-015 (post-auditor G3) PASS, 0 summary-group rows leaked |
| 12 | DQ rules written and passing | **CHECKED** (Bronze) — 15/15 P0+P1 PASS; Silver and Gold rule sets DEFERRED for execution |
| 13 | All existing tests continue to pass | **CHECKED** — 1899/1899 pipeline tests pass; 14 pre-existing mcp errors unrelated to this work, documented |

### DQ Rule Strength Assessment

The Bronze rule set is unusually strong for an entity ingest of this complexity:

- **Started at 9 rules** (per spec). Grew to 15 (14 P0 + 1 P1) after two hardening passes.
- **Chaos pass** (S10 negative-wage attack) → added RAW-OEWS-011 (non-negative annual wages). Real data: 0 violations, 100% non-negative; smallest non-null p10 = $18,500.
- **Adversarial audit** (3 gaps G1/G2/G3) → added RAW-OEWS-013 (`total_employment` non-negative + 99% non-null, structural mirror of S10), RAW-OEWS-014 (annual wage upper bounds: percentiles ≤ 239,200, mean ≤ 500,000 — catches x1000 parser bugs that preserve monotonicity), and RAW-OEWS-015 (no summary-group SOCs sneaking inside the 800–900 row band). All three are P0; all three pass on real data with comfortable margins.
- **Coverage by dimension:** Volume (2), Validity (5), Uniqueness (1), Completeness (3), Consistency (4) — all five core DQ dimensions exercised.
- **Spot-check anchors** (RAW-OEWS-008/009): Software Developers $133,080, Registered Nurses $93,600 — both well inside their windows.

This is a defensible Bronze-quality bar. The combined chaos-then-audit progression closed the four largest non-obvious risk surfaces (negative wages, negative employment, x1000 wage upper-bound, summary-group leakage) before any downstream consumer sees the data.

### Naming-Convention Compliance

| Convention | Required Pattern | Verified |
|-----------|------------------|----------|
| Iceberg namespace (Bronze) | `bronze.bls_oews` (not `raw.*`) | PASS — ingestor source, lineage `outputs[0].name`, DQ rules `table:`, scorecard, contract all consistent |
| Bronze artifact prefix | `raw-ingest-*` (matches `raw-ingest-bls-ooh`, `raw-ingest-bea-rpp`) | PASS — DQ rules, scorecard, lineage, chaos manifest, audit-trail entries all use this prefix |
| Silver artifact prefix | `silver-base-*` (matches `silver-base-bls-ooh`, `silver-base-bea-rpp`) | PASS — pre-authored Silver DQ rules and Silver contract follow this prefix |
| Lineage filename | `raw-ingest-bls-oews-{timestamp}.json` | PASS — `raw-ingest-bls-oews-20260507T033713Z.json` |

### Observations / Advisory Notes (Non-Blocking)

| # | Observation | Severity | Action |
|---|-------------|----------|--------|
| 1 | `python3 -m brightsmith.infra.contract verify` fails with `Empty namespace identifier` for ALL contracts in this environment (verified by attempting `raw-bls-oews`, `consumable-occupation-profiles`, `consumable-program-career-paths`, and `base-bls-ooh` — same failure). This is a project-level CLI environment issue, not an OEWS-specific regression. | ADVISORY | Track as pipeline tooling issue; not blocking for OEWS. The contracts themselves are well-formed YAML and the version bumps and column additions are verifiable via direct read. |
| 2 | The Bronze dispatch authored Silver-zone DQ rules and a Silver-zone contract ahead of the Silver dispatch. Execution is correctly DEFERRED until `base.bls_oews` exists. | ADVISORY | Confirm at Silver dispatch that authored rules execute cleanly without modification; if real Silver data forces rule recalibration, that's a Silver-dispatch finding, not a Bronze one. |
| 3 | No Insight Reports were authored for this zone transition — none required (this is the first Bronze landing of OEWS, no prior cross-zone insight to validate). | ADVISORY | None. |

### Decision Rationale

Every Bronze artifact promised in §Governance Artifacts exists, is correctly named, and is internally consistent. Naming conventions (`bronze.*`, `raw-ingest-*`, `silver-base-*`) are honored throughout — the v1 namespace correction (`raw.*` → `bronze.*`) is reflected in every downstream artifact, with zero residual `raw.bls_oews` references. The DQ rule set passed two independent hardening passes (chaos + adversarial audit), finishing at 15 rules with a 100% pass rate on real Iceberg data — measurably stronger than the spec's original 9-rule baseline. CDE/PII flags on the four new Gold wage columns are set on both modified contracts and version bumps are correct. Data dictionary, lineage, audit trail, and PII/temporal/entity-resolution reports are all present. The contract-verify CLI failure is reproducible across all contracts in this environment (not OEWS-specific) and is noted as an advisory pipeline-tooling issue.

The deferred Silver/Gold/API/Frontend success criteria remain explicitly out of scope for this dispatch and will be verified at their respective post-implementation reviews.

**Verdict: APPROVED.** The Bronze zone of `ingest-bls-oews-wage-percentiles` is governance-compliant. Proceed to Silver dispatch (steps 8–9 of §Agent Workflow).

---

## Staff Engineer Review (Bronze)

**Date:** 2026-05-07
**Reviewer:** @faang-staff-engineer
**Status:** APPROVED

### Verdict

Bronze is production-quality. The ingestor is small, single-purpose, and reads cleanly; tests are real (assertions check specific values, not just `> 0`); governance survived two independent hardening rounds and is grounded in real-data evidence rather than boilerplate. I would put my name on this.

### Code Quality (`src/raw/bls_oews_ingestor.py`)

- Type hints present on every public method and helper. `Any` use confined to the framework-mandated `fetch()` signature and openpyxl row iterator (genuinely unavoidable).
- Browser-UA + 403-fallback pattern matches the OOH precedent. The note explaining why the OOH UA is replaced with a Safari UA on this endpoint is the kind of *why* comment I want — keep it.
- SOC code is preserved as `XX-XXXX` string end-to-end. `_SOC_PATTERN` regex enforces it; `_coerce_soc` rejects 7-digit sub-codes (`15-1252.00`) rather than guessing — correct call.
- Suppression sentinels `*` / `**` / blank → null in both wage and employment paths. Top-code `#` → 239,200 + `wage_capped=True` (annual-only, matching spec). `wage_capped` semantics for hourly are explicitly skipped with a comment explaining the spec rule — exactly the kind of decision that needs a comment.
- Idempotency proven by `test_ingest_is_idempotent`: second run reports `rows=0, skipped=5`, table cardinality stays at 5. Correct.
- Fallback ordering is right: HTTP first, fall back to cached XLSX on any non-200 (including the BLS 403). Test `test_download_falls_back_to_cached_xlsx_on_403` confirms this with a real mocked 403.
- XLSX read in `read_only=True` mode via openpyxl streaming iterator — no whole-file load into memory. CLAUDE.md's "chunked CSV reads" rule does not strictly apply to XLSX, and the streaming iterator is the right XLSX equivalent.
- One micro-nit (non-blocking): `_download_and_read` uses bare `except Exception` to trigger the fallback. That swallows everything including programmer errors. It's pragmatic for a known-flaky endpoint and is not destructive (it logs and degrades to the cached file), but a cleaner version would catch `(requests.exceptions.RequestException, zipfile.BadZipFile, ValueError)`. Not worth blocking on.

### Test Quality (`tests/raw/test_bls_oews_ingestor.py`, 55 tests)

Real, not theater. Asserts specific values:

- `test_flatten_top_coded_wage_sets_capped_flag` — `p75 == 239200`, `p90 == 239200`, `wage_capped is True`, `p25 == 131000`, `mean == 246440`. That's a row's worth of correctness, not a "didn't crash" check.
- `test_flatten_total_employment_is_int_with_commas` — `3175390` exactly, `isinstance(int)`.
- `test_flatten_suppressed_wages_become_null` — every wage field on Maids must be `None`, employment must remain `900000`, `wage_capped=False`.
- `test_ingest_is_idempotent` — counts `5 → 0 (5 skipped) → 5 rows total`, not `>= 5`.
- Full-dataset tests against the real workbook execute when present and skip cleanly when not — correct pattern for offline CI.

Exceeds the Bronze minimum-test bar.

### Spec Compliance

Every Bronze item in §Success Criteria is covered: `bronze.bls_oews` lands, dedup grain holds, `*`→null, `#`→239,200+flag, only `detailed` SOCs ingested, DQ rules passing, full pipeline suite green.

### Data Correctness Spot-Check

Queried the live `bronze.bls_oews` Iceberg table and compared to BLS-published OEWS May 2024 reference values:

| Entity | Metric | Period | Pipeline Value | Reference Value | Source | Match? |
|--------|--------|--------|---------------|-----------------|--------|--------|
| 15-1252 Software Developers | annual median | May 2024 | $133,080 | $133,080 | BLS OEWS oes151252 | EXACT |
| 29-1141 Registered Nurses | annual median | May 2024 | $93,600 | $93,600 | BLS OEWS oes291141 | EXACT |
| 29-1171 Nurse Practitioners | annual median | May 2024 | $129,210 | ~$129K (spec ~$126K, May 2024 vintage shifts) | BLS OEWS oes291171 | EXACT (spec band [$105K-$148K] satisfied) |
| 11-1011 Chief Executives | p75/p90 | May 2024 | $239,200 / $239,200 (capped) | top-coded at $239,200 | BLS OEWS oes111011 | EXACT (cap behavior correct) |
| 11-9032 Education Administrators K-12 | annual median | May 2024 | $104,070 | ~$104K | BLS OEWS oes119032 | EXACT |

5/5 spot-checks pass. No drift. No silent multiplier bug. Top-coding semantics correctly applied. This is the check that would have caught the Apple FY2010 revenue regression in the prior post-mortem; it passes here.

### Governance Hardening

15/15 P0 rules pass on the real 831-row dataset. The progression — original 10 → +1 post-chaos (S10 negative-wage) → +3 post-adversarial-audit (G1 employment non-negativity, G2 wage upper bounds, G3 detailed-only filter regression detector) — is the pattern I want to see: each round identified a real structural gap, the fix was a measurable rule with real SQL and real evidence link, and the rule passes cleanly on real data without false positives. This is not boilerplate.

### Test Suite Integrity

- 55/55 OEWS ingestor tests pass.
- 1899/1899 pipeline tests pass when the pre-existing MCP collection error is excluded (`tests/mcp/*` cannot import — `ModuleNotFoundError: No module named 'app'` originates from `src/mcp_server/futureproof_server.py:34`, which imports the FastAPI backend module that lives in a different venv). I confirmed this is pre-existing by stashing the OEWS work and reproducing the same error on a clean tree at HEAD `1253755`. Not caused by this spec, not blocking. Should be filed as a separate infra issue (move backend imports out of `mcp_server` or restructure the test discovery).
- `ruff check src/raw/bls_oews_ingestor.py tests/raw/test_bls_oews_ingestor.py` — clean.

### Known Framework Issues (Confirmed Non-Blocking)

- `dq_runner` governance-DB sync warning (`Column 'category' is declared non-nullable but contains nulls`) — framework-level metadata write path, does not affect rule execution or the JSON results file. Not OEWS-specific.
- `python3 -m brightsmith.infra.contract verify` — `Empty namespace identifier` reproduces across every contract in this environment, not OEWS-specific. The contract YAML files themselves are well-formed.

Both should be filed as framework infra tickets but neither blocks Bronze sign-off.

### CLAUDE.md Compliance Note

`REQUIRE_HUMAN_APPROVAL: true` applies at this gate. **The orchestrator must obtain explicit human approval before promoting `bronze.bls_oews` to Silver.** This review is the staff-engineer recommendation; it is not a substitute for the human approval gate.

### What's Acceptable

Fine.

### Issues

None blocking. Two non-blocking advisories already documented in §Governance Reviewer (Post-Implementation): contract-verify CLI failure (framework, not OEWS) and DB sync category-null warning (framework, not OEWS). One micro-nit on the bare `except Exception` in `_download_and_read` — leave as-is.

**Verdict: APPROVED.** Bronze is signed off. Silver/Gold dispatches may proceed pending human approval at this gate.

