## Temporal Assessment: gold-futureproof-engine
**Date:** 2026-04-09
**Agent:** @temporal-modeler
**Spec:** docs/specs/gold-futureproof-engine.md
**Domain:** Education / Career Guidance

### Decision: SKIP Temporal Modeling

Temporal modeling is **not applicable** to this spec. No bitemporal schema, snapshot strategy, or correction-handling logic is required.

### Rationale

1. **No valid time dimension.** The two Gold tables (`consumable.program_career_paths` and `consumable.career_branches`) are derived join products, not fact tables with real-world validity periods. There are no date ranges, effective periods, or slowly changing dimensions. The only timestamp is `promoted_at`, which is pipeline metadata (when the table was built), not a temporal fact about the data.

2. **Full table replace pattern.** The spec explicitly uses idempotent full-table promotion. Each pipeline run overwrites the entire table. There is no incremental append, no amendment mechanism, and no need to preserve prior versions within the table itself. Iceberg snapshot-level time travel is sufficient if rollback is ever needed.

3. **Upstream sources lack temporal grain.** All four upstream sources follow the same single-snapshot, full-replace pattern:
   - College Scorecard: annual "Most Recent Cohorts" release, full table replace (domain-context.md, Question 6 assumption)
   - BLS OOH: biennial projection cycle, full table replace
   - O*NET: quarterly release, full database replacement
   - CIP-SOC Crosswalk: periodic release, full replace

   None of these sources carry valid-time ranges that would propagate into the Gold join product.

4. **Spec explicitly marks temporal modeling as skippable.** The "Conditionally Skippable Agents" table states: "@temporal-modeler | SKIP | Single-snapshot pipeline. Full table replace."

5. **Consistent with prior temporal assessments.** The upstream specs (gold-career-outcomes-college-scorecard, gold-occupation-profiles-bls-ooh, gold-onet-profiles) all received the same "SKIP" determination for the same reasons.

### Future Considerations

If the pipeline evolves to support year-over-year comparison (e.g., tracking how a program's ERN score changes across annual Scorecard releases), temporal modeling would become relevant. At that point:
- Add a `release_year` or `data_vintage` column to establish valid time
- Consider SCD Type 2 on the (unitid, cipcode, soc_code) grain
- Use Iceberg snapshots for transaction time as designed

This is not needed for the current MVP/hackathon scope.

### Artifacts Produced

None. No schema changes, no temporal columns, no snapshot strategy document.
