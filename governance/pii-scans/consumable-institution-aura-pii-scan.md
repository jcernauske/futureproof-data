# PII Scan — `consumable.institution_aura`

**Snapshot:** `5887248523326294782`
**Date:** 2026-05-01
**Scanner:** `bs:pii-scanner`
**Verdict:** **NO PII DETECTED**

## Scope

- 19 columns, 3,223 institution-level rows
- Single string non-key column: `institution_name` (public institution names from IPEDS HD / EADA InstLevel)
- Other string columns are bounded enums: `aura_score_version` (`"v1"`), `aura_score_basis` (5-value enum), `coverage_tier` (3-value enum), `athletic_fte_source` (3-value enum)

## Pattern Coverage

- Email regex — 0 matches
- SSN-shaped numbers — 0 matches
- Phone-number patterns — 0 matches
- Credit card patterns — 0 matches
- Address patterns — 0 matches
- Person-name NER — 0 matches (institution names only)

## Upstream Lineage

Inherits PII profile from `base.ipeds_finance` (no PII per `governance/pii-scans/raw-ipeds-finance-pii-scan.md`) and `base.eada` (no PII per `governance/pii-scans/base-eada-pii-scan.md`). The FULL OUTER JOIN at gold introduces no new string surfaces.

## Sensitivity Classification

**Level 1 — Public.** Federally mandated institution-level disclosure (IPEDS Finance via NCES, EADA via Office of Postsecondary Education). No regulatory restrictions.

## Recommendations

- No row-level security required
- No column masking
- Standard public-data handling for downstream consumers
- @bs:policy-engineer: classify as `public` access tier
