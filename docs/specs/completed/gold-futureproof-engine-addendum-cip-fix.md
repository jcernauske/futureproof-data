# Addendum: gold-futureproof-engine — CIP Granularity Fix

**Date:** 2026-04-08
**Applies to:** `docs/specs/gold-futureproof-engine.md`
**Triggered by:** Crosswalk EDA finding — 0% has_scorecard_match under strict CIP matching

## The Problem

College Scorecard stores CIP codes as 4-digit: `XX.XX` (e.g., `52.02` = Business Administration).
The CIP-SOC crosswalk stores CIP codes as 6-digit: `XX.XXXX` (e.g., `52.0201` = Business Administration and Management, General).

Under strict matching (`career_outcomes.cipcode = crosswalk.cipcode`), **zero Scorecard programs match the crosswalk.** The join chain produces zero rows.

## The Fix

**Join on the 4-digit CIP prefix.** Truncate the crosswalk's 6-digit CIP to match Scorecard's 4-digit format:

```sql
JOIN base.cip_soc_crosswalk xw
  ON co.cipcode = LEFT(xw.cipcode, 5)
```

Example: Scorecard `cipcode = "52.02"` matches crosswalk entries `52.0201`, `52.0202`, `52.0203`, etc.

## Coverage (from Crosswalk EDA)

- **91.0%** of Scorecard CIP codes find at least one crosswalk match via 4-digit prefix
- **97.1%** of Scorecard rows are covered
- The ~9% of CIPs without matches tend to be small/niche programs
- Programs with no crosswalk match get **zero rows** in `consumable.program_career_paths` (filtered out by INNER JOIN)

## Cardinality Impact

A single Scorecard CIP (e.g., `52.02`) may match multiple 6-digit crosswalk CIPs (`52.0201`, `52.0202`, `52.0203`), each of which maps to multiple SOC codes. This increases the fan-out per Scorecard program.

**Deduplication:** The same SOC code may appear via multiple 6-digit crosswalk CIPs for the same 4-digit Scorecard CIP. After the join, dedup on the grain `(unitid, cipcode, soc_code)` — the `compute_grain_id` promote pattern handles this naturally.

## Changes to the Spec

### 1. Replace the join chain diagram

**Old (broken):**
```
career_outcomes.cipcode = crosswalk.cipcode (strict 6-digit match)
```

**New (working):**
```
career_outcomes.cipcode = LEFT(crosswalk.cipcode, 5) (4-digit prefix match)
```

### 2. Update the Transformations (Table 1), Step 2

**Old:** "Join to crosswalk on cipcode"
**New:** "Join to crosswalk on `career_outcomes.cipcode = LEFT(crosswalk.cipcode, 5)`. This is a 4-digit prefix join because Scorecard uses XX.XX and crosswalk uses XX.XXXX. Dedup on grain (unitid, cipcode, soc_code) after join."

### 3. Update Row Count Estimate

**Old:** 200,000–350,000
**New:** 150,000–500,000 (wider range due to 4-digit prefix fan-out). DQ rule should flag anything outside this range.

### 4. Update the Golden Dataset verification

**Old:** "crosswalk CIP 52.0201 → SOC 13-2051"
**New:** "Scorecard CIP 52.02 → crosswalk prefix match → 52.0201 (and others) → SOC 13-2051 (and others). Verify that the 4-digit prefix join produces the expected SOC codes."

### 5. Add Open Decision #5

**CIP prefix matching strategy.** The 4-digit prefix join is a coarser match than the crosswalk was designed for. A Business Admin program at ISU (CIP 52.02) now maps to careers from Business Admin AND Management (52.0201), Business Commerce (52.0202), and other 52.02xx programs. This may produce some spurious career paths. For the hackathon, accept the broader match — it's better to show too many career paths than zero. Post-hackathon, consider enriching Scorecard data with 6-digit CIP codes from IPEDS or using Gemma to filter relevant paths.

### 6. Update match_quality derivation

The `has_scorecard_match` flag in the crosswalk Silver table is FALSE for all rows (by design — the Silver spec used strict matching). The Gold engine should **NOT use this flag** for match_quality. Instead, derive match_quality at Gold time based on whether the join actually produced data:

```
match_quality = CASE
  WHEN bls_match AND onet_match THEN 'full'
  WHEN bls_match AND NOT onet_match THEN 'partial_no_onet'
  WHEN NOT bls_match AND onet_match THEN 'partial_no_bls'
  WHEN NOT bls_match AND NOT onet_match THEN 'scorecard_only'
END
```

Where `bls_match` = occupation_profiles join succeeded, `onet_match` = onet_work_profiles join succeeded.
