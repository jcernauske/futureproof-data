# Entity Resolution Assessment: base.eada

**Date:** 2026-04-30
**Agent:** @entity-resolver
**Spec:** `docs/specs/full-pipeline-eada.md` §5
**Verdict:** NOT APPLICABLE — exact-key join, no resolution required

## Entity Model

| Property | Value |
|----------|-------|
| Entity type | Postsecondary institution |
| Canonical key | `unitid` (IPEDS UNITID, integer) |
| Resolution strategy | Exact-match on `unitid` (ID-based) |
| Aliasing required | No |
| Fuzzy matching required | No |
| Lifecycle handling at silver | None — handled (if at all) at gold |

`base.eada` is a Silver-zone normalization of `bronze.eada` that joins one upstream source (`base.ipeds_finance`) using IPEDS UNITID. Both datasets are keyed on UNITID and inherit it from authoritative federal sources — no name normalization, no fuzzy match, no aliasing pass is performed or needed at this layer.

## Cross-Source Join Behavior

Construction (per spec §5):

```
base.eada =
  bronze.eada
  LEFT JOIN base.ipeds_finance USING (unitid)
```

Option-C COALESCE rule for FTE (the only field sourced cross-table):

```
fte_total      = COALESCE(ipeds_finance.fte_total, eada_fte_headcount)
fte_source     = CASE
                   WHEN ipeds_finance.fte_total IS NOT NULL THEN 'ipeds_finance'
                   WHEN eada_fte_headcount   IS NOT NULL THEN 'eada_in_file'
                   ELSE 'none'
                 END
```

The LEFT JOIN preserves every EADA row unconditionally. IPEDS-Finance is the preferred FTE source because it is the authoritative IPEDS measure; EADA's own headcount column is the in-file fallback.

## Observed Coverage

| `fte_source` | Rows | % of EADA |
|--------------|------|-----------|
| `ipeds_finance` | 1,492 | 73.14% |
| `eada_in_file`  | 548   | 26.86% |
| `none`          | 0     | 0.00% |
| **Total**       | 2,040 | 100.00% |

Every institution in EADA resolves to a known FTE source. There are zero rows requiring human review for entity identity, and zero rows where the institution exists but FTE is unknown from any source.

The 26.86% IPEDS-Finance miss rate is a **coverage** observation, not an entity-resolution observation — those institutions are correctly identified by UNITID; their finance row simply does not exist in `base.ipeds_finance` (typically community-college reporting gaps). Resolution is unaffected.

## Confidence

All 2,040 rows resolve at confidence 1.0 (exact ID match). No fuzzy matches, no flagged-for-review cases, no lifecycle events to log at this layer.

## Forward-Looking Note: Gold Zone

Entity resolution work — if any is ever required for institution identity in this pipeline — surfaces at **gold**, not silver. The downstream `consumable.institution_aura` table is built via a FULL OUTER JOIN across all institution-keyed silver bases (College Scorecard, IPEDS-Finance, EADA, plus future sources). That gold join is also UNITID-keyed and exact-match, but FULL OUTER means non-overlapping institutions on either side become first-class rows. If a future source introduces non-UNITID identifiers (e.g., OPEID-only, or name-only), entity resolution becomes load-bearing at that point and a dedicated assessment will be filed against the relevant gold spec.

For `base.eada` itself: no entity-resolution logic, no entity-registry entry, no audit decisions to record beyond this assessment.

## Scope Boundary Confirmation

- No write to `governance/entity-registry.json` (no canonical IDs minted; UNITID is already canonical upstream).
- No `entity-resolution-decisions.md` audit entries (no decisions made — exact-key joins are deterministic).
- This file documents the **non-applicability finding** so downstream reviewers and future spec authors can confirm entity resolution was considered and dismissed with cause.
