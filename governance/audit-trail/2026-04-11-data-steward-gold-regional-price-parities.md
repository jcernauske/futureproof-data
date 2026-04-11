# Data Steward Audit Trail — gold-regional-price-parities

**Date:** 2026-04-11
**Agent:** @data-steward
**Mode:** Greenfield (Gold zone term definition)
**Spec:** docs/specs/gold-regional-price-parities.md
**Glossary:** governance/business-glossary.json
**Domain:** Education / Career Guidance (BEA Regional Price Parities sub-domain)

## Summary

Added two new business glossary terms — BT-106 (Cost Tier) and BT-107 (Adjusted Salary) — required by the `gold-regional-price-parities` Gold zone spec. Both terms are project-specific derivations that build on the already-approved BEA RPP terms BT-098 and BT-099.

## New Terms Proposed

| Term ID | Term | Source | Category | Approval Status |
|---------|------|--------|----------|------------------|
| BT-106 | Cost Tier | project-specific | classification | proposed |
| BT-107 | Adjusted Salary | project-specific | derived | proposed |

Both terms are marked `proposed` (not `auto-approved`) because their source is `project-specific`. Per the data-steward approval rules, project-specific terms always require human review regardless of the `REQUIRE_HUMAN_APPROVAL` toggle. The FutureProof project has `REQUIRE_HUMAN_APPROVAL = true`, which reinforces this gate.

### BT-106 Cost Tier

- **Source:** project-specific — the five-bucket scheme is a FutureProof editorial classification, not a BEA-published category system.
- **Category:** `classification` — the term is an enumerated bucketing of a continuous metric.
- **Related terms:** BT-098 (Regional Price Parity) — the underlying input.
- **Enumeration completeness:** YES. All five buckets are fully documented in the definition:
  1. `very_high` — RPP >= 108 (CA 110.7, HI 110.0, DC 109.9, NJ 108.8)
  2. `high` — 103 <= RPP < 108
  3. `average` — 97 <= RPP < 103
  4. `low` — 91 <= RPP < 97
  5. `very_low` — RPP < 91 (AR 86.9, MS 87.0, IA 87.8, OK 87.8)
- **Breakpoint semantics:** left-closed (inclusive on lower bound, exclusive on upper bound). Explicitly documented.
- **Downstream consumers documented:** frontend color coding, Fight Location Lock boss-difficulty selection, Gemma regional narrative prompts.
- **Editorial caveat:** definition explicitly warns that breakpoint changes are breaking changes for downstream consumers.
- **used_in_models:** `gold-regional-price-parities`, and any MCP spec consuming `cost_tier` (forward-looking, placeholder `mcp-regional-price-parities`).

### BT-107 Adjusted Salary

- **Source:** project-specific — a derivation from BEA RPP, not itself a BEA publication.
- **Category:** `derived` — pure mathematical function of two other glossary terms.
- **Related terms:** BT-098 (Regional Price Parity) and BT-099 (Purchasing Power Multiplier) — both formula inputs.
- **Formula captured in definition:** `adjusted_salary = national_salary * (100 / state_RPP) = national_salary * purchasing_power_multiplier`.
- **Worked examples:** included in definition ($50K national -> ~$45,167 CA; ~$57,537 AR).
- **Pre-computed benchmarks:** `adjusted_30k`, `adjusted_50k`, `adjusted_75k`, `adjusted_100k` all listed as synonyms so frontend/Gemma references resolve to this term.
- **Precision rule:** stored as double rounded to 2 decimal places (cents). Sub-cent precision explicitly disallowed as false precision for a state-level aggregate index.
- **Vintage inheritance:** the definition notes that adjusted salary inherits `data_year` (BT-102) and state grain from its inputs.
- **used_in_models:** `gold-regional-price-parities`, and any MCP spec consuming adjusted salary (forward-looking).

## Schema Conformance

Both new terms use the exact same JSON schema as BT-098..BT-105 with all required fields populated:

- `term_id`, `name`, `definition`, `source`, `source_reference`, `synonyms`, `related_terms`, `category`, `owner`, `used_in_models`, `approval_status`.

JSON loads cleanly. Post-add term count = 107 (was 105). Last four IDs: BT-104, BT-105, BT-106, BT-107.

## Cross-Reference Integrity

- BT-106 -> BT-098 (one-way link from tier to the underlying RPP metric).
- BT-107 -> BT-098, BT-099 (both formula inputs linked).
- BT-098 and BT-099 do not currently back-link to BT-106/BT-107 in their `related_terms` arrays. This is consistent with how BT-098 was originally authored (it only back-links to BT-099), so no retroactive edit is being proposed here. Back-linking can be revisited as a glossary hygiene pass if and when the governance reviewer requests it.

## Conflicts / Ambiguities

- **No ID collisions.** BT-106 and BT-107 were confirmed absent from the pre-edit glossary (grep for `BT-10[67]` returned no matches).
- **No name collisions.** Neither "Cost Tier" nor "Adjusted Salary" appeared as an existing term or synonym.
- **No definition conflicts.** The spec's usage of these concepts is consistent with the definitions captured here.
- **Pre-existing validator warnings (NOT caused by this change):** `python -m brightsmith.infra.glossary_validator validate` reports 9 category issues on BT-094, BT-095, BT-098, BT-100, BT-101, BT-102, BT-103, BT-104, BT-105 (categories `metric`, `descriptive`, `identifier`, `provenance`, `taxonomy` are not in the validator's allowed set `{regulatory, classification, temporal, entity, derived, measurement}`). These are pre-existing drift between the glossary and the validator's enum and are out of scope for this task. The new BT-106 (`classification`) and BT-107 (`derived`) both use validator-allowed categories and therefore pass the schema check cleanly — they do not add to the warning count.

## Human Approval Required

Both new terms are marked `approval_status: proposed` and must be reviewed by a human governance reviewer before they are promoted to `approved`. The reviewer should confirm:

1. The five cost-tier breakpoints are editorially acceptable for the frontend color scheme and the Fight Location Lock gameplay mapping.
2. The four pre-computed salary benchmarks ($30K / $50K / $75K / $100K) match the spec and the frontend's display contract.
3. The 2-decimal-place rounding rule on adjusted salary is acceptable for all downstream consumers.

## Artifacts

- Updated: `governance/business-glossary.json` (BT-106, BT-107 appended)
- Written: `governance/audit-trail/2026-04-11-data-steward-gold-regional-price-parities.md` (this file)
