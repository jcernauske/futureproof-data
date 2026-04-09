## Audit Trail: Temporal Assessment for gold-career-outcomes-college-scorecard
**Timestamp:** 2026-04-06
**Agent:** @temporal-modeler
**Spec:** docs/specs/gold-career-outcomes-college-scorecard.md
**Zone:** Gold (consumable)

### Action
Assessed temporal modeling needs for the `consumable.career_outcomes` Gold table.

### Decision
No bitemporal modeling required. Snapshot-only approach with Iceberg time travel is sufficient.

### Inputs Reviewed
- Gold spec: `docs/specs/gold-career-outcomes-college-scorecard.md`
- Silver spec: `docs/specs/silver-base-college-scorecard.md`
- Domain context: `governance/domain-context.md` (Temporal Patterns and Amendment/Correction Patterns sections)
- Silver temporal assessment: `governance/reviews/silver-base-college-scorecard-temporal-assessment.md`

### Key Rationale
1. Single-vintage snapshot data -- no valid time range exists in source or derived fields
2. Full table replace strategy confirmed by user for data refresh
3. All Gold derivations (percentile bands, ratios, tiers) are deterministic transformations of snapshot data
4. DOE does not publish corrections with supersession metadata
5. Earnings measurement windows are cross-sectional, not longitudinal

### Future Triggers for Re-Assessment
- Multi-year data retention requirement (year-over-year tracking)
- BLS/O*NET cross-source integration (temporal vintage alignment)
- User request for historical percentile band comparison

### Artifacts Produced
- `governance/reviews/gold-career-outcomes-college-scorecard-temporal-assessment.md`

### Trade-offs Considered
- Adding a `data_vintage` column now for future-proofing vs. keeping schema minimal: chose minimal schema since full table replace makes vintage tracking unnecessary in MVP, and adding the column later is non-breaking.
- Retaining multiple annual snapshots in the Gold table vs. full replace: chose full replace per user confirmation, with Iceberg time travel providing version recovery if needed.
