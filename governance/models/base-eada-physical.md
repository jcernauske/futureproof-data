# Physical Model: base-eada

**Status:** PROPOSED
**Mode:** Greenfield
**Zone:** Silver (Base)
**Spec:** [docs/specs/full-pipeline-eada.md](../../docs/specs/full-pipeline-eada.md) §5 (Option-C amendment, 2026-04-30)
**Logical model:** [base-eada-logical.md](base-eada-logical.md)
**Conceptual model:** [base-eada-conceptual.md](base-eada-conceptual.md)
**Author:** @doc-generator
**Date:** 2026-04-30
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)

---

## Iceberg Table

- **Logical name:** `base.eada`
- **Physical Iceberg namespace:** `base.eada` (matches the catalog convention used by sibling Silver/Base tables — `base.ipeds_finance`, `base.bea_rpp`, `base.bls_ooh`, `base.college_scorecard_institution`)
- **Format:** Apache Iceberg over Parquet (v2)
- **Catalog:** Brightsmith Silver SQL catalog (`data/silver/iceberg_warehouse/`); registered in `data/catalog/catalog.db`
- **Partition spec:** none (single-cycle snapshot in current load; future amendment may partition on `reporting_year`)
- **Sort spec:** none
- **Storage location:** `data/silver/iceberg_warehouse/base/eada/`
- **Created by:** [`src/silver/eada_base.py`](../../src/silver/eada_base.py) — `promote_eada_base()`
- **Current snapshot:** `973879610917339278` (2,040 rows, academic year 2022–23 cycle)
- **Idempotent promote:** `brightsmith.infra.promote.promote(..., id_field='record_id')` — re-running with the same Bronze and `base.ipeds_finance` snapshots produces 0 new rows

---

## Iceberg Schema

The schema is defined in code at [`src/silver/eada_base.py::get_base_schema()`](../../src/silver/eada_base.py) (~L92). Field IDs are dense and stable; never reassign on schema evolution.

| Field ID | Field | Iceberg Type | Required | Source | Physical Notes |
|---:|-------|--------------|:--------:|--------|----------------|
| 1 | `record_id` | `StringType` | yes | `compute_grain_id(row, ['unitid'], prefix='ead')` | Format: `ead-<16 hex>`. Deterministic across re-runs. |
| 2 | `unitid` | `LongType` | yes | `bronze.eada.unitid` (passthrough) | Natural key. Coerced via `_to_optional_float` only for derivation arithmetic; written to Iceberg as long. |
| 3 | `institution_name` | `StringType` | yes | `bronze.eada.institution_name` (passthrough) | Display name. |
| 4 | `reporting_year` | `IntegerType` | yes | `bronze.eada.reporting_year` (passthrough) | Constant across batch (single-vintage invariant). |
| 5 | `total_athletic_expenses` | `DoubleType` | no | `bronze.eada.total_athletic_expenses` (passthrough) | Raw passthrough USD. EADA `GRND_TOTAL_EXPENSE`. NaN guarded by `_to_optional_float`. |
| 6 | `total_athletic_revenue` | `DoubleType` | no | `bronze.eada.total_athletic_revenue` (passthrough) | Raw passthrough USD. EADA `GRND_TOTAL_REVENUE`. |
| 7 | `recruiting_expenses` | `DoubleType` | no | `bronze.eada.recruiting_expenses` (passthrough) | Raw passthrough USD. EADA `RECRUITEXP_TOTAL`. ~17.8% of rows are real `0.0` (valid). |
| 8 | `eada_fte_headcount` | `DoubleType` | no | `bronze.eada.eada_fte_headcount` (passthrough) | EADA's `EFTotalCount` — 12-month enrollment headcount. ~100% non-null. The Option-C fallback denominator. |
| 9 | `total_fte_enrollment` | `DoubleType` | no | derived | COALESCE result: `base.ipeds_finance.total_fte_enrollment` if non-null, else `bronze.eada.eada_fte_headcount`. NULL only when both are missing. |
| 10 | `fte_source` | `StringType` | yes | derived | Enum: `'ipeds_finance'` / `'eada_fte_headcount'` / `'none'`. Stamped per-row by `resolve_fte()`. |
| 11 | `has_ipeds_finance_fte` | `BooleanType` | yes | derived | True iff IPEDS-Finance contributed a non-null FTE for this UNITID. |
| 12 | `has_eada_fte` | `BooleanType` | yes | derived | True iff EADA's `eada_fte_headcount` was non-null for this UNITID. Expected ~100% true. |
| 13 | `athletic_spend_per_fte` | `DoubleType` | no | derived | `total_athletic_expenses / total_fte_enrollment`. NULL when either operand is NULL or `total_fte_enrollment ≤ 0`. |
| 14 | `athletic_revenue_per_fte` | `DoubleType` | no | derived | `total_athletic_revenue / total_fte_enrollment`. Same NULL rule. |
| 15 | `recruiting_per_fte` | `DoubleType` | no | derived | `recruiting_expenses / total_fte_enrollment`. Same NULL rule. |
| 16 | `athletic_subsidy_ratio` | `DoubleType` | no | derived | `(total_athletic_expenses − total_athletic_revenue) / NULLIF(total_athletic_expenses, 0)`. Independent of FTE. |
| 17 | `source_load_date` | `DateType` | yes | `bronze.eada.load_date` (passthrough) | Identical across all rows in a batch. |
| 18 | `ingested_at` | `TimestampType` | yes | `datetime.now(tz=UTC)` at promote time | Identical across all rows in a single Base promote run. |

**Total fields:** 18 (5 identity + 3 monetary inputs + 1 EADA headcount passthrough + 1 hybrid FTE + 3 FTE-source provenance + 4 derivations + 2 provenance = 18 columns).

### Field-ID Stability

Field IDs 1–18 are pinned. Future schema evolution (e.g., adding a Knight-Commission classification flag, an in-zone subsidy-ratio confidence score, or a per-row aura-input audit trail) must allocate IDs ≥ 19 and **never** rebind 1–18 to other columns. Standard Iceberg-evolution discipline used across the project (compare `base.ipeds_finance` field IDs 1–15, `base.college_scorecard_institution` field IDs 1–N).

### Verified-Landed Schema

Verified via Iceberg metadata at `data/silver/iceberg_warehouse/base/eada/metadata/00001-6c5472be-6284-4d7e-a288-ba51b6cce7b7.metadata.json` — all 18 fields present, all field IDs 1–18 in the order documented above, all types as documented, all nullability as documented. Snapshot `973879610917339278`. **Landed schema matches spec §5 Base Schema exactly.**

---

## PyIceberg Schema Definition

Reproduced from `src/silver/eada_base.py::get_base_schema()`:

```python
from pyiceberg.schema import Schema
from pyiceberg.types import (
    BooleanType,
    DateType,
    DoubleType,
    IntegerType,
    LongType,
    NestedField,
    StringType,
    TimestampType,
)

SCHEMA = Schema(
    NestedField(1,  "record_id",                StringType(),    required=True),
    NestedField(2,  "unitid",                   LongType(),      required=True),
    NestedField(3,  "institution_name",         StringType(),    required=True),
    NestedField(4,  "reporting_year",           IntegerType(),   required=True),
    NestedField(5,  "total_athletic_expenses",  DoubleType(),    required=False),
    NestedField(6,  "total_athletic_revenue",   DoubleType(),    required=False),
    NestedField(7,  "recruiting_expenses",      DoubleType(),    required=False),
    NestedField(8,  "eada_fte_headcount",       DoubleType(),    required=False),
    NestedField(9,  "total_fte_enrollment",     DoubleType(),    required=False),
    NestedField(10, "fte_source",               StringType(),    required=True),
    NestedField(11, "has_ipeds_finance_fte",    BooleanType(),   required=True),
    NestedField(12, "has_eada_fte",             BooleanType(),   required=True),
    NestedField(13, "athletic_spend_per_fte",   DoubleType(),    required=False),
    NestedField(14, "athletic_revenue_per_fte", DoubleType(),    required=False),
    NestedField(15, "recruiting_per_fte",       DoubleType(),    required=False),
    NestedField(16, "athletic_subsidy_ratio",   DoubleType(),    required=False),
    NestedField(17, "source_load_date",         DateType(),      required=True),
    NestedField(18, "ingested_at",              TimestampType(), required=True),
)
```

---

## Promote Pattern

Per spec §5:

- **Grain:** `unitid`
- **Dedup grain:** `[unitid]`
- **Promote pattern:** `compute_grain_id(row, ['unitid'], prefix='ead')`
- **Idempotent:** Yes
- **Sources:** `bronze.eada` (~2,040 rows, primary) LEFT JOIN `base.ipeds_finance` (~2,675 rows, FTE source)

The promote is implemented in `src/silver/eada_base.py::promote_eada_base()`. Cross-source enrichment is performed in-process via a UNITID-keyed dict lookup built from `base.ipeds_finance`, **not** via a SQL join — the row-counts (2,040 × 2,675) fit comfortably in memory and the dict-lookup keeps the transformer pure-Python and unit-testable.

```python
# In src/silver/eada_base.py — abbreviated
def promote_eada_base(...):
    # 1. Read bronze.eada (~2,040 rows)
    bronze_rows = read_with_duckdb(bronze_eada_table)

    # 2. Build UNITID → total_fte_enrollment lookup from base.ipeds_finance
    ipeds_rows = read_with_duckdb(ipeds_finance_table)
    ipeds_fte_by_unitid = build_ipeds_fte_lookup(ipeds_rows)

    # 3. Per-row transform — Option-C COALESCE applied here
    base_rows = transform_rows(bronze_rows, ipeds_fte_by_unitid, ingested_at)

    # 4. Promote (idempotent dedup on record_id)
    promote(base_table, base_rows, id_field='record_id', spec_name='base-eada', ...)
```

The per-row transform applies in this order:
1. Coerce Bronze numerics to `float | None` (NaN guard via `_to_optional_float`).
2. `resolve_fte(ipeds_fte, eada_fte)` → `(total_fte_enrollment, fte_source)`.
3. `derive_per_fte(numerator, total_fte_enrollment)` × 3 (returns NULL when either operand is NULL or `fte ≤ 0`).
4. `derive_subsidy_ratio(expenses, revenue)` (returns NULL when either operand is NULL or `expenses == 0`).
5. Stamp `record_id` via `compute_grain_id(row, ['unitid'], prefix='ead')`.

Idempotency guarantees:
- **Determinism:** `record_id` is a pure function of `unitid` with constant prefix `ead`. Re-running yields identical hashes.
- **Dedup grain:** `[unitid]` — the promote's `id_field='record_id'` ensures a re-run with identical Bronze + IPEDS-Finance snapshots produces zero new rows.
- **Conservation:** Every Bronze row promotes to exactly one Base row (BSE-EAD-001 P0 `result == 0`).
- **Cross-source determinism:** The dict-based LEFT JOIN is deterministic given a fixed `base.ipeds_finance` snapshot. `build_ipeds_fte_lookup()` raises on duplicate UNITIDs in the IPEDS feed rather than silently last-write-wins.

---

## DDL (Reference)

This DDL is for documentation. The actual table is created via `brightsmith.infra.iceberg_setup.get_or_create_table()` plus `brightsmith.infra.promote.promote()`.

```sql
-- Reference DDL for base.eada
-- Engine: DuckDB + Iceberg v2
-- Do not execute directly -- use the promote() pattern.

CREATE TABLE IF NOT EXISTS base.eada (
    record_id                  VARCHAR     NOT NULL,
    unitid                     BIGINT      NOT NULL,
    institution_name           VARCHAR     NOT NULL,
    reporting_year             INTEGER     NOT NULL,
    total_athletic_expenses    DOUBLE,
    total_athletic_revenue     DOUBLE,
    recruiting_expenses        DOUBLE,
    eada_fte_headcount         DOUBLE,
    total_fte_enrollment       DOUBLE,
    fte_source                 VARCHAR     NOT NULL,
    has_ipeds_finance_fte      BOOLEAN     NOT NULL,
    has_eada_fte               BOOLEAN     NOT NULL,
    athletic_spend_per_fte     DOUBLE,
    athletic_revenue_per_fte   DOUBLE,
    recruiting_per_fte         DOUBLE,
    athletic_subsidy_ratio     DOUBLE,
    source_load_date           DATE        NOT NULL,
    ingested_at                TIMESTAMP   NOT NULL,

    PRIMARY KEY (record_id),
    UNIQUE (unitid),

    CHECK (fte_source IN ('ipeds_finance','eada_fte_headcount','none')),
    CHECK (total_athletic_expenses    IS NULL OR total_athletic_expenses    >= 0),
    CHECK (total_athletic_revenue     IS NULL OR total_athletic_revenue     >= 0),
    CHECK (recruiting_expenses        IS NULL OR recruiting_expenses        >= 0),
    CHECK (eada_fte_headcount         IS NULL OR eada_fte_headcount         >  0),
    CHECK (total_fte_enrollment       IS NULL OR total_fte_enrollment       >  0),
    CHECK (athletic_spend_per_fte     IS NULL OR athletic_spend_per_fte     >= 0),
    CHECK (athletic_revenue_per_fte   IS NULL OR athletic_revenue_per_fte   >= 0),
    CHECK (recruiting_per_fte         IS NULL OR recruiting_per_fte         >= 0),
    CHECK (athletic_subsidy_ratio     IS NULL OR athletic_subsidy_ratio     BETWEEN -3.0 AND 1.0),
    -- Tautology between FTE and source enforced by BSE-EAD-012:
    CHECK ((total_fte_enrollment IS NULL) = (fte_source = 'none'))
);
```

---

## Source-to-Target Mapping

| Physical Column | DuckDB Type | Source Table | Source Field | Transformation |
|-----------------|-------------|--------------|--------------|----------------|
| record_id | VARCHAR | -- | derived | `compute_grain_id(row, ['unitid'], prefix='ead')` |
| unitid | BIGINT | bronze.eada | unitid | Direct passthrough |
| institution_name | VARCHAR | bronze.eada | institution_name | Direct passthrough |
| reporting_year | INTEGER | bronze.eada | reporting_year | Direct passthrough |
| total_athletic_expenses | DOUBLE | bronze.eada | total_athletic_expenses | Direct passthrough (NaN-guarded) |
| total_athletic_revenue | DOUBLE | bronze.eada | total_athletic_revenue | Direct passthrough (NaN-guarded) |
| recruiting_expenses | DOUBLE | bronze.eada | recruiting_expenses | Direct passthrough (NaN-guarded) |
| eada_fte_headcount | DOUBLE | bronze.eada | eada_fte_headcount | Direct passthrough (NaN-guarded) |
| total_fte_enrollment | DOUBLE | base.ipeds_finance + bronze.eada | total_fte_enrollment + eada_fte_headcount | `COALESCE(ipeds_finance, eada_fte_headcount)` |
| fte_source | VARCHAR | -- | derived | `'ipeds_finance'` / `'eada_fte_headcount'` / `'none'` based on COALESCE selection |
| has_ipeds_finance_fte | BOOLEAN | base.ipeds_finance | total_fte_enrollment IS NOT NULL | `(ipeds_finance.total_fte_enrollment IS NOT NULL)` |
| has_eada_fte | BOOLEAN | bronze.eada | eada_fte_headcount IS NOT NULL | `(bronze.eada.eada_fte_headcount IS NOT NULL)` |
| athletic_spend_per_fte | DOUBLE | -- | derived | `total_athletic_expenses / total_fte_enrollment` (NULL-safe; FTE > 0 gate) |
| athletic_revenue_per_fte | DOUBLE | -- | derived | `total_athletic_revenue / total_fte_enrollment` (NULL-safe) |
| recruiting_per_fte | DOUBLE | -- | derived | `recruiting_expenses / total_fte_enrollment` (NULL-safe) |
| athletic_subsidy_ratio | DOUBLE | -- | derived | `(total_athletic_expenses − total_athletic_revenue) / NULLIF(total_athletic_expenses, 0)` |
| source_load_date | DATE | bronze.eada | load_date | Direct passthrough |
| ingested_at | TIMESTAMP | -- | generated | `datetime.now(tz=UTC)` at promote time |

---

## Load Statistics (academic year 2022–23, snapshot 973879610917339278)

| Metric | Value |
|--------|------:|
| Rows | 2,040 |
| Distinct `unitid` | 2,040 (100% unique) |
| `record_id` non-null | 2,040 / 2,040 |
| `record_id` unique | 2,040 / 2,040 |
| `total_athletic_expenses` non-null | 100.00% |
| `total_athletic_revenue` non-null | 100.00% |
| `recruiting_expenses` non-null | 100.00% (17.8% are real `0.0`) |
| `eada_fte_headcount` non-null | ~100.00% |
| `total_fte_enrollment` non-null | > 99.0% (BSE-EAD-009 P0: `'none'` rate ≤ 1%) |
| `fte_source = 'ipeds_finance'` rate | ~74.5% (BSE-EAD-011 P1, ±5pp) |
| `fte_source = 'eada_fte_headcount'` rate | ~25.5% |
| `fte_source = 'none'` rate | < 1% |
| `has_ipeds_finance_fte = TRUE` rate | ~74.5% |
| `has_eada_fte = TRUE` rate | ~100% |
| `athletic_spend_per_fte` non-null | > 99.0% |
| `athletic_revenue_per_fte` non-null | > 99.0% |
| `recruiting_per_fte` non-null | > 99.0% |
| `athletic_subsidy_ratio` non-null | 100.00% (independent of FTE) |
| `athletic_subsidy_ratio` distribution | P5 = −0.157 / P50 = 0.0 / P95 = 0.0 / min = −2.92 / max = 0.0 |
| Conservation invariant (BSE-EAD-001) | 2,040 == 2,040 (Bronze) ✓ |
| IPEDS-preference invariant (BSE-EAD-013) | 0 violations ✓ |
| Tautology invariant (BSE-EAD-012) | 0 violations ✓ |
| Arithmetic invariant (BSE-EAD-008) | 0 rows where `|spend_per_fte × fte − expenses| > $1` ✓ |

Source: `governance/dq-scorecards/base-eada-20260501T210828Z.{json,md}` (13/13 PASS) plus the `fte_source_counts` returned by `promote_eada_base()`.

---

## Cross-References

| Artifact | Path |
|----------|------|
| Spec | `docs/specs/full-pipeline-eada.md` (§5, Option-C amendment 2026-04-30) |
| Transformer | `src/silver/eada_base.py` |
| Bronze model | `governance/models/raw-eada-{conceptual,logical,physical}.md` |
| Cross-source dependency model | `governance/models/base-ipeds-finance-{conceptual,logical,physical}.md` |
| Conceptual model | `governance/models/base-eada-conceptual.md` |
| Logical model | `governance/models/base-eada-logical.md` |
| DQ rules | `governance/dq-rules/base-eada.json` (13 rules: 11 P0 + 2 P1) |
| DQ scorecard | `governance/dq-scorecards/base-eada-20260501T210828Z.{json,md}` (13/13 PASS) |
| Chaos report | `governance/chaos-reports/base-eada-chaos.md` (7/7 caught) |
| Entity resolution | `governance/entity-resolution/base-eada-er-assessment.md` (N/A — single grain, no merge) |
| PII scan | `governance/pii-scans/base-eada-pii-scan.md` (NONE) |
| Temporal model | `governance/temporal-models/base-eada-temporal-assessment.md` (N/A — single-cycle snapshot) |
| CDE/PII tagging | `governance/cde-tagging/raw-eada.md` (Bronze; Base CDE flags follow the same upstream-feeder + analytical lens documented in this Physical model) |
| Lineage | `governance/lineage/full-pipeline-eada-silver-*.json` (silver run; produced by lineage-tracker) |
| Domain context | `governance/domain-context.md` § EADA Athletics Disclosure |
| Data dictionary | `governance/data-dictionaries/base-eada.md` |

---

## Modeling Decisions (Physical Layer)

1. **`base.eada` namespace.** Matches the catalog convention for every Silver/Base table. The Python transformer module lives under `src/silver/` per the project's long-standing zone-naming convention; the Iceberg namespace uses the spec-specified `base` name.

2. **`DoubleType` for all monetary, FTE, per-FTE, and ratio fields, not `DecimalType(p, s)`.** Matches Bronze (DoubleType for the four numeric passthroughs) and matches the `base.ipeds_finance` precedent. Per-FTE rates and the subsidy ratio are continuous measures, not currency that requires fixed-precision arithmetic. The BSE-EAD-008 tolerance is $1 — DOUBLE precision is more than sufficient.

3. **`required=True` on `fte_source` (and the two boolean coverage flags), even though the FTE *value* itself is `required=False`.** The provenance columns must always carry a value — `'none'` is a real enum value that handles the double-NULL case rather than NULLing the column. This makes BSE-EAD-012 (`total_fte_enrollment IS NULL ⟺ fte_source = 'none'`) a clean tautology check rather than a tri-state-NULL relationship.

4. **`required=False` on the four monetary inputs and the four derivations.** NULLs are part of the data contract: future cycles may suppress small-program totals, the per-FTE values NULL-cascade when the COALESCE'd FTE is missing, and the subsidy ratio NULL-cascades when either monetary operand is missing or expenses is 0. Locking these to `required=True` would make the schema reject legitimate Bronze data. The completeness DQ rules (BSE-EAD-009/011/012) enforce the *expected* non-null rates and source distribution instead.

5. **`required=True` on identity + provenance.** Every row must carry a complete identity (`record_id`, `unitid`, `institution_name`, `reporting_year`) and a complete provenance stamp (`source_load_date`, `ingested_at`, `fte_source`, `has_ipeds_finance_fte`, `has_eada_fte`). NULL on any of these would mean the row bypassed the promote machinery — a governance violation.

6. **`unitid` as `LongType`, not `StringType`.** Bronze stores UNITID as `LongType`; Base preserves the same physical type. UNITID is a 6-digit integer (no leading zeros), so the FIPS-style "must be string to preserve zero-padding" concern does not apply. Matches every other UNITID-keyed table in the project (`bronze.college_scorecard_institution`, `bronze.eada`, `base.ipeds_finance`, `consumable.career_outcomes`).

7. **No partition spec.** The Base table is single-cycle today and `reporting_year` is constant across rows. Adding a partition spec when there's only one partition value would only add metadata overhead. Future multi-cycle backfill should add `PARTITION BY reporting_year` as a schema-evolution step.

8. **No sort spec.** Read patterns are dominated by the downstream consumable promote (full-table scan via FULL OUTER JOIN against `base.ipeds_finance`) and individual-UNITID lookups. Neither benefits significantly from a sort key on a 2,040-row table.

9. **`record_id` prefix `ead` — distinct from consumable's `aur`.** Per spec §5, `compute_grain_id(row, ['unitid'], prefix='ead')`. The downstream consumable uses prefix `aur` so that hash namespaces between zones cannot collide by construction. Same pattern as `base.ipeds_finance` (`ipf`) → `consumable.ipeds_finance_profile` (`ifp`).

10. **Cross-source LEFT JOIN implemented as in-process dict lookup, not SQL.** Both source tables fit in memory (2,040 + 2,675 rows) and pure-Python keeps the transformer unit-testable with synthetic dicts. The dict builder (`build_ipeds_fte_lookup`) raises on duplicate UNITIDs in `base.ipeds_finance` rather than silently last-write-wins — a defensive choice that surfaces feed corruption at promote time.

11. **No SCD2.** Same as Bronze; latest-snapshot-only.

12. **No imputation flag column.** Per spec §2 Decision #8 and the standing user constraint, the Option-C COALESCE is *source selection between two equally-real measurements*, not imputation. The `fte_source` enum carries the choice; there is no boolean `is_fte_imputed` column because no FTE value is imputed. Field IDs ≥ 19 are reserved for any future schema-evolution that surfaces the imputation flag at a finer grain (e.g., per-derivation confidence) — but nothing imputed needs landing today.
