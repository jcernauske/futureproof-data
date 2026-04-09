# Audit Trail: Physical Model Generation

**Spec:** silver-base-college-scorecard
**Stage:** Stage 3 (Physical Model)
**Date:** 2026-04-06
**Agent:** @semantic-modeler
**Mode:** Greenfield

---

## Stage Progression

| Stage | Status | Date | Notes |
|-------|--------|------|-------|
| Conceptual (Stage 1) | APPROVED | 2026-04-06 | Rev 2 incorporated human feedback on earnings split and institution_control |
| Logical (Stage 2) | APPROVED | 2026-04-06 | Human feedback on credential_level typing, NULL completions, institution_control BT |
| Physical (Stage 3) | APPROVED | 2026-04-06 | Generated from approved logical. No separate approval gate (per spec workflow step 5). |

---

## Human Feedback Incorporated

The following feedback from logical model approval was incorporated into the physical model:

1. **credential_level typed as INTEGER** -- Logical model had type domain "numeric" which could map to DOUBLE. Human clarified it is a categorical code (not aggregatable). Physical model uses INTEGER with explicit documentation that SUM/AVG are semantically invalid.

2. **NULL completions produce small_cohort_flag = True** -- Conservative default approved. Physical derivation rule: `completions_count_1 IS NULL OR completions_count_1 < 30`. This protects downstream consumers from interpreting potentially suppressed data as reliable.

3. **institution_control needs BT-018** -- Acknowledged as non-blocking. Physical model uses `*pending BT-018*` placeholder. @data-steward to propose the term.

4. **CONTROL field via raw ingestor update (option a)** -- Source-to-target mapping references `raw.college_scorecard.control` as the source field. Raw ingestor must be updated before Silver transformer can execute.

---

## Design Decisions

### Type Mappings

| Decision | Rationale |
|----------|-----------|
| unitid as BIGINT (not VARCHAR) | 6-digit numeric ID. BIGINT supports efficient numeric comparisons and joins. No leading zeros to preserve. |
| cipcode as VARCHAR (not numeric) | Contains dot separator (XX.XXXX format). Must be string. |
| cip_family as VARCHAR (not INTEGER) | 2-digit codes may have leading zeros (e.g., "01" for Agriculture). VARCHAR preserves formatting. |
| credential_level as INTEGER (not DOUBLE) | Human feedback: categorical code. INTEGER prevents accidental aggregation and saves storage vs DOUBLE. |
| earnings/debt as DOUBLE (not DECIMAL) | DuckDB DOUBLE provides sufficient precision for monetary aggregates at this grain. No sub-cent precision needed. |
| completions as BIGINT (not INTEGER) | BIGINT for consistency with other count fields and future-proofing, though values fit in INTEGER. |

### Partition Strategy

No partitioning. The dataset is 69,947 rows (MVP) -- small enough for a single Iceberg data file. Partitioning would add metadata overhead without query performance benefit. This should be revisited if the dataset grows beyond ~1M rows or if temporal snapshots are added.

### Sort Order

`unitid ASC, cipcode ASC, credential_level ASC` -- matches the natural key and the most common access pattern (filter by institution, then by program). Supports predicate pushdown for institution-level queries.

### CHECK Constraints

Range constraints on earnings ($1,000-$250,000) and debt ($1,000-$100,000) match DQ rule thresholds from the spec. These are documented as reference constraints -- Iceberg does not enforce CHECK constraints natively. Enforcement happens at transform time and via DQ rules.

---

## Alternatives Considered

| Alternative | Decision | Reason |
|-------------|----------|--------|
| DECIMAL(10,2) for monetary fields | Rejected in favor of DOUBLE | No sub-cent precision required. DOUBLE is simpler in DuckDB and sufficient for cohort-level aggregates. |
| Partition by cip_family | Rejected | Would create 47 partitions for < 70K rows. Overhead exceeds benefit. |
| Partition by credential_level | Rejected | MVP has single value (3). Would be single-partition. Revisit when multiple credential levels are loaded. |
| VARCHAR for credential_level | Rejected | Human explicitly requested INTEGER. Categorical nature documented via constraints and description. |
| Separate lookup tables for cip_family_name, credential_description | Rejected | Silver Base pattern calls for denormalized wide tables. Lookups happen at transform time, not query time. |

---

## Artifacts Produced

- `/Users/jcernauske/code/bright/futureproof-data/governance/models/silver-base-college-scorecard-physical.md`
- `/Users/jcernauske/code/bright/futureproof-data/governance/audit-trail/silver-base-college-scorecard-physical-model.md` (this file)
