## Entity Resolution Assessment: gold-futureproof-engine
**Date:** 2026-04-09
**Agent:** @entity-resolver
**Spec:** docs/specs/gold-futureproof-engine.md
**Decision:** SKIP -- entity resolution not required

### Assessment

This spec joins four Gold tables and one Silver crosswalk to produce two consumable tables (`consumable.program_career_paths` and `consumable.career_branches`). All joins use deterministic keys:

| Join | Left Key | Right Key | Method |
|------|----------|-----------|--------|
| career_outcomes to cip_soc_crosswalk | `cipcode` (XX.XX) | `LEFT(cipcode, 5)` (XX.XXXX truncated) | Deterministic string prefix match |
| crosswalk to occupation_profiles | `soc_code` | `soc_code` | Exact match |
| crosswalk to onet_work_profiles | `soc_code` | `bls_soc_code` | Exact match |
| career_transitions to occupation_profiles | `soc_code` / `related_soc_code` | `soc_code` | Exact match |
| career_transitions to onet_work_profiles | `soc_code` / `related_soc_code` | `bls_soc_code` | Exact match |

### Why Entity Resolution Is Not Needed

1. **No fuzzy matching.** Every join is on exact key equality or deterministic string truncation (`LEFT(cipcode, 5)`). The CIP prefix match is a deliberate design choice to handle the 4-digit vs. 6-digit granularity mismatch -- it is not ambiguous or probabilistic.

2. **Standardized taxonomies throughout.** CIP codes and SOC codes are government-maintained classification systems with stable, well-defined identifiers. There are no name-based lookups, no free-text entity matching, and no cross-system identifier reconciliation beyond the CIP-SOC crosswalk (which is itself a government-published deterministic mapping).

3. **UNITID is a stable IPEDS identifier.** Institution matching uses UNITID (a federal integer ID), not institution names.

4. **No entity lifecycle events.** This spec consumes point-in-time snapshots. There are no mergers, name changes, or ID migrations to track.

5. **Upstream resolution already handled.** The Silver zone crosswalk (`base.cip_soc_crosswalk`) already provides the canonical CIP-to-SOC mapping. The Gold spec simply consumes it.

### Entities Present (No Resolution Needed)

| Entity Type | Identifier | Source | Resolution Status |
|-------------|-----------|--------|-------------------|
| Institution | UNITID (integer) | College Scorecard | Deterministic -- no resolution needed |
| Program | CIPCODE (XX.XX) | College Scorecard | Deterministic -- prefix match is a design choice, not ambiguity |
| Occupation | SOC code (XX-XXXX) | BLS/O*NET/Crosswalk | Deterministic -- exact match |

### Confidence

Resolution confidence scoring is not applicable. All joins are either exact matches (confidence 1.0 by definition) or intentional prefix matches that are documented design decisions rather than fuzzy resolution.

### Recommendation

No entity registry entries needed. No resolution mappings to produce. The spec's own "Conditionally Skippable Agents" section correctly identifies @entity-resolver as SKIP.
