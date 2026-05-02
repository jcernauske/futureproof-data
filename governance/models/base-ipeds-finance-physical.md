# Physical Model: base-ipeds-finance

**Status:** PROPOSED
**Mode:** Greenfield
**Zone:** Silver (Base)
**Spec:** [docs/specs/full-pipeline-ipeds-finance.md](../../docs/specs/full-pipeline-ipeds-finance.md) §5
**Logical model:** [base-ipeds-finance-logical.md](base-ipeds-finance-logical.md)
**Conceptual model:** [base-ipeds-finance-conceptual.md](base-ipeds-finance-conceptual.md)
**Author:** @doc-generator
**Date:** 2026-04-30
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)

---

## Iceberg Table

- **Logical name:** `base.ipeds_finance`
- **Physical Iceberg namespace:** `base.ipeds_finance` (matches the catalog convention used by sibling Silver/Base tables — `base.bea_rpp`, `base.bls_ooh`, `base.college_scorecard_institution`)
- **Format:** Apache Iceberg over Parquet (v2)
- **Catalog:** Brightsmith Silver SQL catalog (`data/silver/iceberg_warehouse/`); registered in `data/catalog/catalog.db`
- **Partition spec:** none (single-cycle snapshot in current load; future amendment may partition on `fiscal_year`)
- **Sort spec:** none (current snapshot)
- **Storage location:** `data/silver/iceberg_warehouse/base/ipeds_finance/`
- **Created by:** [`src/silver/ipeds_finance_base.py`](../../src/silver/ipeds_finance_base.py) — `promote_ipeds_finance_base()`
- **Runner:** [`scripts/promote_ipeds_finance_base.py`](../../scripts/promote_ipeds_finance_base.py)
- **Current snapshot:** `1277941459950591173` (2,675 rows, FY2023)
- **Idempotent promote:** `brightsmith.infra.promote.promote(..., dedup_on=['unitid'])` — re-running yields `0 new rows (all 2675 already exist)`

---

## Iceberg Schema

The schema is defined in code at `src/silver/ipeds_finance_base.py` and materialized via `brightsmith.infra.promote.promote()`. Field IDs are stable; never reassign on schema evolution.

| Field ID | Field | Iceberg Type | Required | Source | Physical Notes |
|---:|-------|--------------|:--------:|--------|----------------|
| 1 | `record_id` | `StringType` | yes | `compute_grain_id(row, ['unitid'], prefix='ipf')` | Format: `ipf-<16 hex>`. Deterministic across re-runs. |
| 2 | `unitid` | `LongType` | yes | `bronze.ipeds_finance.unitid` (passthrough) | Natural key. |
| 3 | `institution_name` | `StringType` | yes | `bronze.ipeds_finance.institution_name` (passthrough) | HD `INSTNM`-derived display name. |
| 4 | `report_form` | `StringType` | yes | `bronze.ipeds_finance.report_form` (passthrough) | Enum-valued: `F1A` / `F2` / `F3`. |
| 5 | `fiscal_year` | `IntegerType` | yes | `bronze.ipeds_finance.fiscal_year` (passthrough) | Constant across batch (single-vintage invariant). |
| 6 | `institutional_support_expenses` | `DoubleType` | no | `bronze.ipeds_finance.institutional_support_expenses` (passthrough) | Raw passthrough USD. F1A `F1C071` / F2 `F2E061` / F3 `F3E03C1`. |
| 7 | `instruction_expenses` | `DoubleType` | no | `bronze.ipeds_finance.instruction_expenses` (passthrough) | Raw passthrough USD. F1A `F1C011` / F2 `F2E011` / F3 `F3E011`. |
| 8 | `endowment_value` | `DoubleType` | no | `bronze.ipeds_finance.endowment_value` (passthrough) | Raw passthrough USD. F1A `F1H02` / F2 `F2H02` / F3 N/A (structural NULL). |
| 9 | `total_fte_enrollment` | `DoubleType` | no | `bronze.ipeds_finance.total_fte_enrollment` (passthrough) | EFIA-sourced 12-month FTE; NULL when EFIA had no row for the UNITID. |
| 10 | `institutional_support_per_fte` | `DoubleType` | no | derived | `institutional_support_expenses / total_fte_enrollment`. NULL when either operand is NULL or `total_fte_enrollment ≤ 0`. |
| 11 | `instruction_per_fte` | `DoubleType` | no | derived | `instruction_expenses / total_fte_enrollment`. Same NULL rule. |
| 12 | `endowment_per_fte` | `DoubleType` | no | derived | `endowment_value / total_fte_enrollment`. Same NULL rule. F3 always NULL. |
| 13 | `marketing_ratio` | `DoubleType` | no | derived | `institutional_support_expenses / NULLIF(instruction_expenses, 0)`. NULL when either operand is NULL or instruction is 0. |
| 14 | `source_load_date` | `DateType` | yes | `bronze.ipeds_finance.load_date` (passthrough, cast to DATE) | Identical across all rows in a batch. |
| 15 | `ingested_at` | `TimestampType` | yes | `datetime.now()` at promote time | Identical across all rows in a single Base promote run. |

**Total fields:** 15 (5 identity + 4 monetary inputs + 4 derivations + 2 provenance).

### Field-ID Stability

Field IDs 1–15 are pinned. Future schema evolution (e.g., adding raw expense passthroughs that do not yet exist in Bronze, or a per-form data-quality flag) must allocate IDs ≥ 16 and **never** rebind 1–15 to other columns. Standard Iceberg-evolution discipline used across the project.

### Verified-Landed Schema

Verified via Iceberg metadata at `data/silver/iceberg_warehouse/base/ipeds_finance/metadata/00001-4b79be88-21c1-4a59-ad00-c2299e64f36b.metadata.json` — all 15 fields present, all field IDs 1–15 in the order documented above, all types as documented, all nullability as documented. **Landed schema matches spec §5 Base Schema exactly.**

---

## PyIceberg Schema Definition

```python
from pyiceberg.schema import Schema
from pyiceberg.types import (
    DateType,
    DoubleType,
    IntegerType,
    LongType,
    NestedField,
    StringType,
    TimestampType,
)

SCHEMA = Schema(
    NestedField(1,  "record_id",                     StringType(),    required=True),
    NestedField(2,  "unitid",                        LongType(),      required=True),
    NestedField(3,  "institution_name",              StringType(),    required=True),
    NestedField(4,  "report_form",                   StringType(),    required=True),
    NestedField(5,  "fiscal_year",                   IntegerType(),   required=True),
    NestedField(6,  "institutional_support_expenses", DoubleType(),   required=False),
    NestedField(7,  "instruction_expenses",          DoubleType(),    required=False),
    NestedField(8,  "endowment_value",               DoubleType(),    required=False),
    NestedField(9,  "total_fte_enrollment",          DoubleType(),    required=False),
    NestedField(10, "institutional_support_per_fte", DoubleType(),    required=False),
    NestedField(11, "instruction_per_fte",           DoubleType(),    required=False),
    NestedField(12, "endowment_per_fte",             DoubleType(),    required=False),
    NestedField(13, "marketing_ratio",               DoubleType(),    required=False),
    NestedField(14, "source_load_date",              DateType(),      required=True),
    NestedField(15, "ingested_at",                   TimestampType(), required=True),
)
```

---

## Promote Pattern

Per spec §5:

- **Grain:** `unitid`
- **Dedup grain:** `[unitid]`
- **Promote pattern:** `compute_grain_id(row, ['unitid'], prefix='ipf')`
- **Idempotent:** Yes
- **Source:** `bronze.ipeds_finance`

```python
from brightsmith.infra.grain import compute_grain_id
from brightsmith.infra.promote import promote
from datetime import datetime

def promote_ipeds_finance_base(*, project_dir):
    bronze_df = read_bronze_ipeds_finance(project_dir)

    # 1. Passthroughs (no rescaling, no rounding)
    df = bronze_df[[
        'unitid', 'institution_name', 'report_form', 'fiscal_year',
        'institutional_support_expenses', 'instruction_expenses',
        'endowment_value', 'total_fte_enrollment',
    ]].copy()

    # 2. Per-FTE derivations — NULL-safe via guarded division
    fte = df['total_fte_enrollment']
    valid_fte = fte.notna() & (fte > 0)
    df['institutional_support_per_fte'] = df['institutional_support_expenses'].where(valid_fte) / fte.where(valid_fte)
    df['instruction_per_fte']           = df['instruction_expenses'].where(valid_fte)           / fte.where(valid_fte)
    df['endowment_per_fte']             = df['endowment_value'].where(valid_fte)                / fte.where(valid_fte)

    # 3. Marketing ratio — NULLIF semantics on the denominator
    instr = df['instruction_expenses']
    valid_instr = instr.notna() & (instr != 0)
    df['marketing_ratio'] = df['institutional_support_expenses'].where(valid_instr) / instr.where(valid_instr)

    # 4. Provenance
    df['source_load_date'] = pd.to_datetime(bronze_df['load_date']).dt.date
    df['ingested_at'] = datetime.utcnow()

    # 5. Deterministic record_id
    df['record_id'] = df.apply(
        lambda row: compute_grain_id(row, ['unitid'], prefix='ipf'), axis=1
    )

    # 6. Column order matches SCHEMA
    df = df[[
        'record_id', 'unitid', 'institution_name', 'report_form', 'fiscal_year',
        'institutional_support_expenses', 'instruction_expenses', 'endowment_value', 'total_fte_enrollment',
        'institutional_support_per_fte', 'instruction_per_fte', 'endowment_per_fte', 'marketing_ratio',
        'source_load_date', 'ingested_at',
    ]]

    promote(df, table='base.ipeds_finance', schema=SCHEMA, dedup_on=['unitid'])
```

Idempotency guarantees:
- **Determinism:** `record_id` is a pure function of `unitid` with constant prefix `ipf`. Re-running yields identical hashes (verified: Stanford UNITID 243744 → `ipf-267f20f48b4b772f` across multiple promotes).
- **Dedup grain:** `[unitid]` ensures a re-run with identical Bronze input produces zero new rows.
- **Conservation:** Every Bronze row promotes to exactly one Base row (BSE-IPF-001 P0).

---

## DDL (Reference)

This DDL is for documentation. The actual table is created via `brightsmith.infra.promote.promote()` which handles Iceberg table creation and idempotent writes.

```sql
-- Reference DDL for base.ipeds_finance
-- Engine: DuckDB + Iceberg v2
-- Do not execute directly -- use promote() pattern

CREATE TABLE IF NOT EXISTS base.ipeds_finance (
    record_id                       VARCHAR     NOT NULL,
    unitid                          BIGINT      NOT NULL,
    institution_name                VARCHAR     NOT NULL,
    report_form                     VARCHAR     NOT NULL,
    fiscal_year                     INTEGER     NOT NULL,
    institutional_support_expenses  DOUBLE,
    instruction_expenses            DOUBLE,
    endowment_value                 DOUBLE,
    total_fte_enrollment            DOUBLE,
    institutional_support_per_fte   DOUBLE,
    instruction_per_fte             DOUBLE,
    endowment_per_fte               DOUBLE,
    marketing_ratio                 DOUBLE,
    source_load_date                DATE        NOT NULL,
    ingested_at                     TIMESTAMP   NOT NULL,

    PRIMARY KEY (record_id),
    UNIQUE (unitid),

    CHECK (report_form IN ('F1A','F2','F3')),
    CHECK (institutional_support_expenses IS NULL OR institutional_support_expenses >= 0),
    CHECK (instruction_expenses           IS NULL OR instruction_expenses           >= 0),
    CHECK (endowment_value                IS NULL OR endowment_value                >= 0),
    CHECK (total_fte_enrollment           IS NULL OR total_fte_enrollment           >  0),
    CHECK (institutional_support_per_fte  IS NULL OR institutional_support_per_fte  >= 0),
    CHECK (instruction_per_fte            IS NULL OR instruction_per_fte            >= 0),
    CHECK (endowment_per_fte              IS NULL OR endowment_per_fte              >= 0),
    CHECK (marketing_ratio                IS NULL OR marketing_ratio                >= 0)
);
```

---

## Source-to-Target Mapping

| Physical Column | DuckDB Type | Source Table | Source Field | Transformation |
|-----------------|-------------|--------------|--------------|----------------|
| record_id | VARCHAR | -- | derived | `compute_grain_id(row, ['unitid'], prefix='ipf')` |
| unitid | BIGINT | bronze.ipeds_finance | unitid | Direct passthrough |
| institution_name | VARCHAR | bronze.ipeds_finance | institution_name | Direct passthrough |
| report_form | VARCHAR | bronze.ipeds_finance | report_form | Direct passthrough |
| fiscal_year | INTEGER | bronze.ipeds_finance | fiscal_year | Direct passthrough |
| institutional_support_expenses | DOUBLE | bronze.ipeds_finance | institutional_support_expenses | Direct passthrough |
| instruction_expenses | DOUBLE | bronze.ipeds_finance | instruction_expenses | Direct passthrough |
| endowment_value | DOUBLE | bronze.ipeds_finance | endowment_value | Direct passthrough |
| total_fte_enrollment | DOUBLE | bronze.ipeds_finance | total_fte_enrollment | Direct passthrough |
| institutional_support_per_fte | DOUBLE | -- | derived | `institutional_support_expenses / total_fte_enrollment` (NULL-safe) |
| instruction_per_fte | DOUBLE | -- | derived | `instruction_expenses / total_fte_enrollment` (NULL-safe) |
| endowment_per_fte | DOUBLE | -- | derived | `endowment_value / total_fte_enrollment` (NULL-safe) |
| marketing_ratio | DOUBLE | -- | derived | `institutional_support_expenses / NULLIF(instruction_expenses, 0)` |
| source_load_date | DATE | bronze.ipeds_finance | load_date | Cast to DATE; passthrough |
| ingested_at | TIMESTAMP | -- | generated | `datetime.utcnow()` at promote time |

---

## Load Statistics (FY2023, snapshot 1277941459950591173)

| Metric | Value |
|--------|------:|
| Rows | 2,675 |
| Distinct `unitid` | 2,675 (100% unique) |
| `record_id` non-null | 2,675 / 2,675 |
| `record_id` unique | 2,675 / 2,675 |
| `report_form` distinct values | 3 — F1A 819 (30.6%) / F2 1,579 (59.0%) / F3 277 (10.4%) |
| `institution_name` non-null | 100.00% |
| `institutional_support_expenses` non-null | 100.00% |
| `instruction_expenses` non-null | 100.00% |
| `endowment_value` non-null | 76.00% (1,033 NULL — F3 structural + small F2 institutions w/o endowment) |
| `total_fte_enrollment` non-null | 97.94% (55 NULL — newly-opened or late EFIA filers) |
| `institutional_support_per_fte` non-null | 97.94% (NULL-cascades from FTE) |
| `instruction_per_fte` non-null | 97.94% |
| `endowment_per_fte` non-null | 74.69% (NULL-cascades from both endowment NULL and FTE NULL) |
| `marketing_ratio` non-null | 98.84% (31 NULL — zero-instruction system-office UNITIDs) |
| Stanford spot check (UNITID 243744) | `instruction_per_fte=140,522.42`, `institutional_support_per_fte=42,427.78`, `endowment_per_fte=1,911,327.80`, `marketing_ratio=0.30193`, `record_id=ipf-267f20f48b4b772f` |
| `marketing_ratio` per-form P99 | F1A 14.15 / F2 6.35 / F3 8.75 |
| Conservation invariant (BSE-IPF-001) | 2,675 == 2,675 (Bronze) ✓ |

Source: scripts/promote_ipeds_finance_base.py output + ad-hoc DuckDB queries against the landed Parquet files.

---

## Cross-References

| Artifact | Path |
|----------|------|
| Spec | `docs/specs/full-pipeline-ipeds-finance.md` (§5) |
| Transformer | `src/silver/ipeds_finance_base.py` |
| Runner | `scripts/promote_ipeds_finance_base.py` |
| Bronze model | `governance/models/raw-ipeds-finance-{conceptual,logical,physical}.md` |
| Conceptual model | `governance/models/base-ipeds-finance-conceptual.md` |
| Logical model | `governance/models/base-ipeds-finance-logical.md` |
| DQ rules | `governance/dq-rules/base-ipeds-finance.json` (19 rules: 13 P0 + 6 P1) |
| DQ scorecard | `governance/dq-scorecards/full-pipeline-ipeds-finance-scorecard.md` |
| Data dictionary | `governance/data-dictionaries/base-ipeds-finance.md` |
| Domain context | `governance/domain-context.md` § IPEDS Finance Survey |
| EDA report | `governance/eda/raw-ingest-ipeds-finance-eda.md` |
| Lineage | `governance/lineage/full-pipeline-ipeds-finance-{timestamp}.json` |

---

## Modeling Decisions (Physical Layer)

1. **`base.ipeds_finance` namespace.** Matches the catalog convention for every Silver/Base table (`base.bea_rpp`, `base.bls_ooh`, `base.college_scorecard_institution`). The Python transformer module lives under `src/silver/` per the project's long-standing zone-naming convention; the Iceberg namespace uses the spec-specified `base` name.

2. **`DoubleType` for all monetary and per-FTE fields, not `DecimalType(p, s)`.** Matches Bronze (DoubleType for the four monetary inputs) and matches the BEA RPP precedent. Per-FTE rates and the marketing-ratio are continuous measures, not currency that requires fixed-precision arithmetic. The BSE-IPF-008/009/010 tolerance is $1 — DOUBLE precision is more than sufficient.

3. **`required=False` on the four monetary inputs and the four derivations.** NULLs are part of the data: F3 endowment is structurally NULL, FTE is NULL on 55 institutions, per-FTE values NULL-cascade, and marketing-ratio is NULL on zero-instruction system offices. Locking these to `required=True` would make the schema reject legitimate Bronze data. The completeness DQ rules (BSE-IPF-011..014) enforce the *expected* non-null rates instead.

4. **`required=True` on identity + provenance.** Every row must carry a complete identity (`unitid`, `institution_name`, `report_form`, `fiscal_year`) and a complete provenance stamp (`source_load_date`, `ingested_at`, `record_id`). NULL on any of these would mean the row bypassed the promote machinery — a governance violation.

5. **`unitid` as `LongType`, not `StringType`.** Bronze stores UNITID as `LongType`; Base preserves the same physical type. UNITID is a 6-digit integer (no leading zeros), so the FIPS-style "must be string to preserve zero-padding" concern does not apply. Matches every other UNITID-keyed table in the project (`bronze.college_scorecard_institution`, `bronze.eada`, `consumable.career_outcomes`).

6. **No partition spec.** The Base table is single-cycle today and `fiscal_year` is constant across rows. Adding a partition spec when there's only one partition value would only add metadata overhead. Future multi-cycle backfill should add `PARTITION BY fiscal_year` as a schema-evolution step.

7. **No sort spec.** Read patterns are dominated by full-table scans (downstream consumable promote) and individual-UNITID lookups (downstream EADA fusion). Neither benefits significantly from a sort key on a 2,675-row table.

8. **`record_id` prefix `ipf` — distinct from consumable's `ifp`.** Per spec §5, `compute_grain_id(row, ['unitid'], prefix='ipf')`. The downstream consumable uses prefix `ifp` so that hash namespaces between zones cannot collide by construction. Verified: Stanford UNITID 243744 yields `ipf-267f20f48b4b772f` at Base and `ifp-267f20f48b4b772f` at Consumable.

9. **No SCD2.** Same as Bronze; latest-snapshot-only.

10. **No imputation flag column.** Per spec §2 Decision #8 and the EDA Req 7 finding (≤1.22% imputation prevalence on instruction/inst-support, 25-31% on endowment), the `XF1H02` / `XF2H02` flag columns are not landed at Bronze and therefore are not promoted to Base. Field IDs ≥ 16 are reserved for a future `endowment_value_provenance` column if the v1.4 EDA recommendation is accepted.
