# Approval Required: Business Glossary Terms (Silver/Gold — O*NET Experience)
**Spec:** onet-experience-requirements
**Produced by:** @data-steward
**Date:** 2026-04-16
**Artifact:** governance/business-glossary.json

## What You Are Approving

The @data-steward agent reviewed `docs/specs/onet-experience-requirements.md` — a spec that adds O*NET Education/Training/Experience data to the FutureProof pipeline — and identified 2 new business terms that describe the concepts introduced by this work. Of those 2 terms:

- **1 was auto-approved** (BT-117: Related Work Experience) because it is rooted in the O*NET Data Collection Program (element 3.A.1, scale RW), a recognized external standard for occupational taxonomy and measurement. Our aggregation (weighted-median over category midpoints) is a FutureProof-specific transformation, but the underlying concept, the 11 duration categories, and the incumbent-survey methodology are all authoritative O*NET content.
- **1 requires your approval** (BT-118: Experience Tier) because the four-bucket classification (entry / early / mid / senior) and its numeric thresholds are FutureProof design choices. The thresholds themselves were previously resolved in `governance/approvals/onet-experience-requirements-open-decisions.md` on 2026-04-16; this approval ratifies the term entry that encodes those thresholds in the business glossary.

Additionally confirmed during this pass:

- **BT-116** is the current max assigned term_id prior to this change; no collision.
- **BT-108** and **BT-109** are absent from the glossary (gap between BT-107 and BT-110). Disposition: unassigned / skipped. No action taken — these IDs remain reserved/unused for historical continuity; we do not backfill gaps.

## Terms Requiring Approval

### 1. BT-118: Experience Tier (Category: Classification)

**Proposed Definition:**
"FutureProof-derived classification of occupations by typical experience requirement, based on the `experience_years_typical` scalar derived from O*NET Related Work Experience (BT-117). Four-valued enumeration: `entry` (0 ≤ years ≤ 1), `early` (1 < years ≤ 4), `mid` (4 < years ≤ 8), `senior` (years > 8). Drives default filtering and 'decade bucketing' in the career evolution tree (Stage 3 branching graph), allowing users to see which downstream careers are reachable now vs. after several years of experience. Thresholds were human-approved 2026-04-16; see `governance/approvals/onet-experience-requirements-open-decisions.md`."

**Why this is project-specific:** The concept of bucketing occupations by required experience is a product framing invented by FutureProof to power the career evolution tree and decade-bucketing UX. O*NET itself publishes only the raw distribution (BT-117); it does not define `entry`/`early`/`mid`/`senior` tiers, nor does it specify threshold values at 1, 4, and 8 years. Both the label set and the cut points are project design decisions. The source_reference on this term points back to the spec and the prior human-approval record for the thresholds.

**What to look for:**
- Do the tier names (`entry`, `early`, `mid`, `senior`) read naturally for the intended audience (students choosing a major/career)? Or would something like `now`, `soon`, `later`, `much-later` better match the "when can I reach this career" framing of the branching tree?
- Are the threshold cut points at exactly 1 / 4 / 8 years still correct as encoded here? These mirror what was approved in `onet-experience-requirements-open-decisions.md` — please confirm that the glossary entry matches your prior decision and that no drift has been introduced.
- Are the bucket boundaries — `entry` as `years ≤ 1` and `early` as `years > 1` — the correct inclusivity? (The spec uses `≤` on the upper bound of each tier and strict `>` on the lower bound of the next, so there are no gaps or overlaps at the exact boundary values 1.0, 4.0, and 8.0.)
- Is the linkage from BT-118 back to the prior approval doc (`governance/approvals/onet-experience-requirements-open-decisions.md`) sufficient, or should the glossary entry also inline the approval date and rationale?

---

## Summary Table

| Term ID | Term Name | Category | Source | Key Question for Reviewer |
|---------|-----------|----------|--------|--------------------------|
| BT-117 | Related Work Experience | measure | external-standard | AUTO-APPROVED (O*NET element 3.A.1, scale RW) |
| BT-118 | Experience Tier | classification | project-specific | Do tier names + thresholds (1/4/8 yrs) match the prior approval? |

## Auto-Approved Term (No Action Needed)

**BT-117 (Related Work Experience)** was auto-approved because the underlying concept, the 11-category duration distribution, and the survey methodology are all defined by the O*NET Data Collection Program — a recognized external standard for occupational data in the United States. Specifically:

- The measure is element `3.A.1` with scale code `RW` in the O*NET content model.
- The 11 duration categories (None → Over 10 years) are published by O*NET and are stable across O*NET database releases.
- The incumbent-survey methodology is documented in the O*NET Center's public methodology docs.

The FutureProof-specific pieces — the midpoint values used for weighted-median aggregation and the resulting `experience_years_typical` scalar — are noted in the definition but do not change the authority of the underlying concept. Those specific midpoints and the weighted-median approach were already separately human-approved on 2026-04-16 and are recorded in `governance/approvals/onet-experience-requirements-open-decisions.md`; this glossary entry cites that file as part of its `source_reference`.

## Existing Terms Updated (No Action Needed)

No existing terms had their definitions or `used_in_models` arrays modified in this pass. Downstream specs (`raw-ingest-onet-experience`, `silver-base-onet-experience-profiles`, `gold-career-branches`, `mcp-futureproof-core`) are referenced directly in the `used_in_models` arrays of the two new terms.

## Impact If Rejected

If BT-118 is rejected:

- The term remains in `proposed` status and cannot be referenced by downstream governance artifacts (data contract for `base.onet_experience_profiles`, Gold-zone updates to `consumable.career_branches`, MCP tool docstrings).
- The @data-steward agent will revise the definition — typically the tier names, thresholds, or category-inclusivity convention — based on your feedback and resubmit.
- This does **not** block implementation of the ingestor or Silver transformer code in the Bronze/Silver zones, but it **does** block @doc-generator from producing the final data dictionary entries that describe the `experience_tier` column on the Silver and Gold outputs.
- The governance completeness checklist for the O*NET Experience Requirements spec cannot be marked complete until BT-118 is approved.

If BT-117 is later contested (it is currently auto-approved and does not need your sign-off): raise it here and the @data-steward will re-open the source attribution, likely downgrading it to `project-specific` only if our aggregation choices materially change the meaning of the underlying O*NET measure.

## Decision

**BT-118 Experience Tier: APPROVED**
- Approved By: Jeff Cernauske
- Approved Date: 2026-04-16
- Conditions: none
- BT-118 moved from `proposed` → `approved` in `governance/business-glossary.json`.

## How to Respond

- **Approve BT-118:** "Approved" — BT-118 moves from `proposed` to `approved` status in `governance/business-glossary.json`.
- **Approve with revisions:** Specify which aspect (name, tier labels, threshold values, inclusivity convention, source_reference wording) to revise.
- **Reject:** Provide feedback on what needs to change. Note: rejecting BT-118 while leaving the threshold-approval doc untouched will create an inconsistency that the @data-steward will flag back for resolution.

For any revision request, please indicate whether the issue is with the **name**, the **definition**, the **thresholds**, or the **source_reference**, so the @data-steward can make a targeted edit without re-litigating settled decisions from `onet-experience-requirements-open-decisions.md`.
