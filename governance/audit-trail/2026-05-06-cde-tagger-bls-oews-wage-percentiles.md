# Audit Trail: CDE/PII Tagging — BLS OEWS Wage Percentiles

**Date:** 2026-05-06
**Agent:** @cde-tagger
**Spec:** docs/specs/ingest-bls-oews-wage-percentiles.md
**Domain Context:** governance/domain-context.md §"BLS OEWS"
**PII Verdict (input):** NO_PII — governance/pii-reports/raw-bls-oews-pii-report.md

---

## Files Created

1. `governance/data-contracts/raw-bls-oews.yaml` — Bronze contract for `bronze.bls_oews` (15 columns, version 1.0.0).
2. `governance/data-contracts/silver-base-bls-oews.yaml` — Silver contract for `base.bls_oews` (12 columns including `record_id` grain hash and `source_load_date`, version 1.0.0).

## Files Modified

3. `governance/data-contracts/consumable-occupation-profiles.yaml` — bumped 1.0.0 → 1.1.0; added four new columns (`wage_p10`, `wage_p25`, `wage_p75`, `wage_p90`); added version-history block; updated `lineage.source_tables` to include `base.bls_oews`.
4. `governance/data-contracts/consumable-program-career-paths.yaml` — bumped 1.1.0 → 1.2.0; added the same four columns threaded from `consumable.occupation_profiles`; added version-history block.

---

## CDE Tier Scheme (introduced in this tagging round)

The OEWS contracts introduce an explicit `cde_tier` field alongside `is_cde`:

- **P0** — drives a downstream user-facing stat, scored signal, or join key. Errors here directly mislead students or break the pipeline.
- **P1** — supports analytics, display, or methodology interpretation. Errors here degrade the product but do not directly corrupt user-facing values.
- _(no tier)_ — pipeline provenance metadata (`ingested_at`, `source_url`, `source_method`, `load_date`, `source_load_date`, `record_id`). Not a CDE.

This matches the tier guidance the user provided in the tagging request and follows the recommendations in `governance/domain-context.md` §"BLS OEWS" → "Concept Mapping Guidance" → "Source Codes to Business Concepts" (which calls out each percentile as a CDE in its own right).

---

## Decisions — `bronze.bls_oews` (15 fields)

| Field | is_cde | cde_tier | is_pii | Rationale (one-line) |
|-------|--------|----------|--------|----------------------|
| `soc_code` | true | P0 | false | Primary key; direct join into OOH, O*NET, AI exposure, CIP-SOC crosswalk. |
| `occupation_title` | true | P1 | false | Display label; not a join key. |
| `total_employment` | true | P1 | false | Sanity floor and potential weighting input; not user-facing in v1. |
| `wage_annual_p10` | true | P0 | false | Lower tail of career salary distribution; feeds future ERN v2 spread. |
| `wage_annual_p25` | true | P0 | false | Lower bound of CareerCard/FinancesCard "typical range." |
| `wage_annual_median` | true | P0 | false | Canonical single-figure career salary (per domain context). |
| `wage_annual_p75` | true | P0 | false | Upper bound of CareerCard/FinancesCard "typical range"; PDF ceiling proxy. |
| `wage_annual_p90` | true | P0 | false | Upside potential / Fight AI boss framing; most-capped percentile. |
| `wage_annual_mean` | true | P0 | false | Complementary single-figure salary; published uncapped (`mean > p90` is expected on capped SOCs). |
| `wage_hourly_median` | true | P1 | false | Reference-only; not consumed by v1 surfaces. |
| `wage_capped` | true | P0 | false | Top-code interpretation flag — capped percentile values are meaningless without it. |
| `ingested_at` | false | — | false | Pipeline provenance. |
| `source_url` | false | — | false | Pipeline provenance. |
| `source_method` | false | — | false | Pipeline provenance. |
| `load_date` | false | — | false | Pipeline provenance. |

**CDE count:** 11 of 15 (4 provenance fields excluded).
**PII count:** 0 of 15 — confirmed against `governance/pii-reports/raw-bls-oews-pii-report.md`.

---

## Decisions — `base.bls_oews` (12 fields)

Silver carries the same field-level CDE/PII decisions forward, with two structural differences:
- adds `record_id` (grain hash, not a CDE — pipeline infrastructure);
- renames `load_date` → `source_load_date`;
- drops `wage_hourly_median`, `source_url`, and `source_method` (not surfaced through Silver per spec §Silver Schema).

| Field | is_cde | cde_tier | is_pii | Rationale (one-line) |
|-------|--------|----------|--------|----------------------|
| `record_id` | false | — | false | Pipeline infrastructure. |
| `soc_code` | true | P0 | false | Validated XX-XXXX; primary join key into Gold. |
| `occupation_title` | true | P1 | false | Display label. |
| `total_employment` | true | P1 | false | Sanity / weighting input. |
| `wage_annual_p10` | true | P0 | false | Lower-tail signal; Future Enhancements §1/§4. |
| `wage_annual_p25` | true | P0 | false | User-facing lower bound. |
| `wage_annual_median` | true | P0 | false | Canonical headline salary. |
| `wage_annual_p75` | true | P0 | false | User-facing upper bound; PDF ceiling. |
| `wage_annual_p90` | true | P0 | false | Upside potential framing. |
| `wage_annual_mean` | true | P0 | false | Complementary single-figure salary. |
| `wage_capped` | true | P0 | false | Top-code interpretation flag. |
| `source_load_date` | false | — | false | Pipeline provenance. |
| `ingested_at` | false | — | false | Pipeline provenance (Silver promotion timestamp). |

**CDE count:** 10 of 13.
**PII count:** 0 of 13.

---

## Decisions — `consumable.occupation_profiles` 1.1.0 (4 new fields)

| Field | is_cde | cde_tier | is_pii | Rationale (one-line) |
|-------|--------|----------|--------|----------------------|
| `wage_p10` | true | P0 | false | Per spec §"CDE / PII Classification (Gold)" — decision-relevant earnings distribution; ERN v2 candidate. |
| `wage_p25` | true | P0 | false | Per spec — lower bound of the user-facing "typical range." |
| `wage_p75` | true | P0 | false | Per spec — upper bound of the user-facing "typical range"; existing PDF ceiling proxy. |
| `wage_p90` | true | P0 | false | Per spec — upside potential / Fight AI boss framing. |

Version bump: **1.0.0 → 1.1.0** (additive, MINOR per `breaking_changes.policy`).
Lineage updated: `lineage.source_tables` now lists `base.bls_ooh` and `base.bls_oews`.

---

## Decisions — `consumable.program_career_paths` 1.2.0 (4 new fields)

| Field | is_cde | cde_tier | is_pii | Rationale (one-line) |
|-------|--------|----------|--------|----------------------|
| `wage_p10` | true | P0 | false | Threaded from `consumable.occupation_profiles.wage_p10`. |
| `wage_p25` | true | P0 | false | Threaded; surfaces through API as `CareerOutcome.wage_p25`. |
| `wage_p75` | true | P0 | false | Threaded; surfaces through API as `CareerOutcome.wage_p75`. |
| `wage_p90` | true | P0 | false | Threaded; supports upside framing in MCP/frontend. |

Version bump: **1.1.0 → 1.2.0** (additive, MINOR per `breaking_changes.policy`).

---

## Verification

- All four contract version bumps match the spec's §Governance Artifacts → Data Contracts checklist (lines 499–503 of the spec): `consumable-occupation-profiles` 1.0.0→1.1.0, `consumable-program-career-paths` 1.1.0→1.2.0, plus the new Silver contract for `base.bls_oews`.
- All four new Gold columns carry `is_cde: true`, `is_pii: false`, `cde_tier: P0` per the spec's pre-declared decisions in §Zone 3 → "CDE / PII Classification (Gold — occupation_profiles)".
- All Bronze and Silver columns carry `is_pii: false` consistent with the NO_PII verdict in `governance/pii-reports/raw-bls-oews-pii-report.md`.
- No backward-propagation of CDE flags across zones — each zone's flags were evaluated independently per @cde-tagger scope rules.

The dq-engineer will validate column presence and constraint satisfaction when the Silver/Gold transformers run.
