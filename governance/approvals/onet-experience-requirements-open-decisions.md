# Human Approval: Open Decisions — onet-experience-requirements

**Spec:** `docs/specs/onet-experience-requirements.md`
**Approved by:** Jeff Cernauske
**Approval date:** 2026-04-16
**Recorded by:** Claude Code (via `/bs:run` after `@governance-reviewer` CHANGES REQUESTED verdict)

---

## Context

The pre-implementation `@governance-reviewer` pass flagged three "Open Decisions" items in the spec as governance blockers because they were already baked into DQ rules and transformer logic but lacked human sign-off. Per `REQUIRE_HUMAN_APPROVAL: true` in CLAUDE.md, these required explicit approval before Silver implementation could begin.

Jeff reviewed each proposal and approved the defaults. This document captures that decision in a durable location so downstream agents (`bs:semantic-modeler`, `bs:dq-rule-writer`, `bs:primary-agent` Silver implementer) have a single source of truth to reference.

---

## Decision 1 — Experience Tier Thresholds

**Approved mapping:**

| Tier | Range (years) |
|------|---------------|
| `entry`  | 0 ≤ years ≤ 1  |
| `early`  | 1 < years ≤ 4  |
| `mid`    | 4 < years ≤ 8  |
| `senior` | years > 8      |

**Where this shows up:**

- Silver transformer (`src/silver/onet_experience_transformer.py`) — `experience_tier` derivation from `experience_years_typical`.
- Silver DQ rules (`governance/dq-rules/silver-onet-experience.json`) — `experience_tier IN ('entry','early','mid','senior')` (P0); spot checks `11-1011 (Chief Executives) = senior` (P0) and `41-2031 (Retail Salespersons) = entry` (P0).
- Gold `consumable.career_branches` — the `related_experience_tier` column carries this classification to the MCP tool and frontend.
- Business Glossary BT-118 (Experience Tier) — definition cites these thresholds.

**Why this mapping is defensible:**

- `0–1` `entry` — matches "no prior experience required" and very brief training windows typical of Retail Salespersons, food-service roles, warehouse labor.
- `1–4` `early` — typical individual-contributor career onset; matches O*NET RW categories 6 and 7 (1–2 and 2–4 year buckets).
- `4–8` `mid` — senior IC / lead / first-line manager zone; matches O*NET RW categories 8 and 9.
- `8+` `senior` — executive / deep specialist; matches O*NET RW categories 10 and 11 and empirically aligns with chief-executive titles in the sample spot checks.

---

## Decision 2 — "Over 10 years" Midpoint

**Approved value:** 12 years.

**Where this shows up:**

- Silver midpoint mapping table in the spec (Zone 2 / Related Work Experience Categories).
- Gold DQ rule: `experience_delta_years range: -10 ≤ delta ≤ 15` (P1) — the upper bound of `15` allows headroom above 12 in case both source and target sit at category 11 with different O*NET details averaging to a higher number.
- `experience_years_typical` for any occupation whose weighted-median category resolves to `11`.

**Why 12 and not 15:**

- 12 years is a conservative midpoint — far enough above 10 to preserve the "Over 10 years" ordering over the 10-year category, but not so high that it inflates senior-tier estimates. Pinning at 15 would double-count the open-ended tail and artificially widen `experience_delta_years` for senior-to-senior transitions.
- Keeping the value as a categorical string (`"10+"`) instead of a numeric was rejected because downstream math (the `experience_delta_years` subtraction, the `max_experience_years` filter in `career_tree.py`) requires a scalar.

---

## Decision 3 — Multi-Detail Aggregation

**Approved method:** Unweighted average of `experience_years_typical` across O*NET detail codes when collapsing O*NET-SOC (`XX-XXXX.XX`) to BLS SOC (`XX-XXXX`).

**Where this shows up:**

- Silver transformer aggregation step: for SOC codes with multiple O*NET details (e.g., `15-1252.00` Software Developers and `15-1252.01` Software Developers, Applications), produce a single Silver row with `experience_years_typical = mean(details)` and `onet_details_averaged = count(details)`.
- Silver schema — `onet_details_averaged` column exposes the count for provenance.

**Why unweighted and not incumbent-weighted:**

- Matches existing O*NET Silver precedent in `silver-base-onet` (`base.onet_work_profiles`, `base.onet_occupation_tasks`, `base.onet_work_activities`) — cross-source consistency matters more than theoretical superiority of incumbent-weighting.
- Incumbent counts are not published at detail grain by O*NET's free bulk data, so a weighted average would require an additional data source and bespoke plumbing for marginal accuracy gain.
- The `experience_distribution` JSON field preserves the full per-category frequencies from every contributing detail so downstream analysts can recompute a weighted median later if ever needed.

---

## Decision 4 (Advisory Only — Not Blocking) — Filter vs. Dim Branches

**Disposition:** Deferred to a future frontend spec.

This pipeline spec commits to `hide` semantics via `max_experience_years` in `backend/app/services/career_tree.py` — branches above the threshold are dropped from the tree. Whether the UI surfaces filtered branches as dimmed "locked" cards with an "Unlocks at 8+ years" badge, or simply removes them, is a UX decision owned by the frontend team. The pipeline does not need to emit locked-branch metadata to support either choice — the same `experience_years` and `experience_tier` columns serve both rendering modes.

---

## Downstream Propagation

- `bs:dq-rule-writer` — cite this file in the `rationale` field for tier-enum and spot-check rules.
- `bs:semantic-modeler` — conceptual and logical models should cite this file when documenting `experience_tier` attribute semantics.
- `bs:data-steward` — BT-118 Experience Tier glossary entry must cite this file as source-of-approval.
- `bs:doc-generator` — data dictionary entries for `experience_tier` and `experience_years_typical` should cross-link to this file.
