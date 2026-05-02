# Physical Model: consumable-ipeds-finance-profile

**Status:** PROPOSED
**Mode:** Greenfield
**Zone:** Gold (Consumable)
**Spec:** [docs/specs/full-pipeline-ipeds-finance.md](../../docs/specs/full-pipeline-ipeds-finance.md) §6
**Logical model:** [consumable-ipeds-finance-profile-logical.md](consumable-ipeds-finance-profile-logical.md)
**Conceptual model:** [consumable-ipeds-finance-profile-conceptual.md](consumable-ipeds-finance-profile-conceptual.md)
**Author:** @doc-generator
**Date:** 2026-04-30
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)

---

## Iceberg Table

- **Logical name:** `consumable.ipeds_finance_profile`
- **Physical Iceberg namespace:** `consumable.ipeds_finance_profile` (matches the catalog convention used by sibling Gold/Consumable tables — `consumable.regional_price_parities`, `consumable.career_outcomes`, `consumable.occupation_profiles`)
- **Format:** Apache Iceberg over Parquet (v2)
- **Catalog:** Brightsmith Gold SQL catalog (`data/gold/iceberg_warehouse/`); registered in `data/catalog/catalog.db`
- **Partition spec:** none (single-cycle snapshot; matches Base)
- **Sort spec:** none
- **Storage location:** `data/gold/iceberg_warehouse/consumable/ipeds_finance_profile/`
- **Created by:** [`src/gold/ipeds_finance_profile.py`](../../src/gold/ipeds_finance_profile.py) — `transform()` / `promote_ipeds_finance_profile()`
- **Runner:** [`scripts/promote_ipeds_finance_profile.py`](../../scripts/promote_ipeds_finance_profile.py)
- **Current snapshot:** `950547093607535235` (2,630 rows, FY2023, v1.4 with system-office filter applied + `endowment_value_provenance` + `source_load_date`); v1.3 historical snapshot `6649279885162971471` (2,675 rows, no filter)
- **Idempotent promote:** `brightsmith.infra.promote.promote(..., dedup_on=['unitid'])` — re-running yields `0 new rows (all 2675 already exist)`

---

## Iceberg Schema

The schema is defined in code at `src/gold/ipeds_finance_profile.py` and materialized via `brightsmith.infra.promote.promote()`. Field IDs are stable; never reassign on schema evolution.

| Field ID | Field | Iceberg Type | Required | Source | Physical Notes |
|---:|-------|--------------|:--------:|--------|----------------|
| 1 | `record_id` | `StringType` | yes | `compute_grain_id(row, ['unitid'], prefix='ifp')` | Format: `ifp-<16 hex>`. Distinct from Base's `ipf-` prefix. |
| 2 | `unitid` | `LongType` | yes | `base.ipeds_finance.unitid` (passthrough) | Natural key. |
| 3 | `institution_name` | `StringType` | yes | `base.ipeds_finance.institution_name` (passthrough) | |
| 4 | `report_form` | `StringType` | yes | `base.ipeds_finance.report_form` (passthrough) | Enum-valued: `F1A` / `F2` / `F3`. |
| 5 | `fiscal_year` | `IntegerType` | yes | `base.ipeds_finance.fiscal_year` (passthrough) | Constant across batch. |
| 6 | `total_fte_enrollment` | `DoubleType` | no | `base.ipeds_finance.total_fte_enrollment` (passthrough) | EFIA-sourced 12-month FTE. |
| 7 | `instruction_expenses` | `DoubleType` | no | `base.ipeds_finance.instruction_expenses` (passthrough) | **Raw passthrough USD. Exposed at consumable for downstream EADA composite ratios.** |
| 8 | `institutional_support_expenses` | `DoubleType` | no | `base.ipeds_finance.institutional_support_expenses` (passthrough) | **Raw passthrough USD. Exposed at consumable for downstream EADA composite ratios.** |
| 9 | `endowment_value` | `DoubleType` | no | `base.ipeds_finance.endowment_value` (passthrough) | **Raw passthrough USD. Exposed at consumable for downstream EADA composite ratios.** F3 structural NULL. |
| 10 | `institutional_support_per_fte` | `DoubleType` | no | `base.ipeds_finance.institutional_support_per_fte` (passthrough) | Per-student admin spending. |
| 11 | `instruction_per_fte` | `DoubleType` | no | `base.ipeds_finance.instruction_per_fte` (passthrough) | Per-student instructional spending. |
| 12 | `endowment_per_fte` | `DoubleType` | no | `base.ipeds_finance.endowment_per_fte` (passthrough) | Per-student endowment value. F3 always NULL. |
| 13 | `marketing_ratio` | `DoubleType` | no | `base.ipeds_finance.marketing_ratio` (passthrough) | Institutional support / instruction. |
| 14 | `data_completeness_tier` | `StringType` | yes | derived | `high`/`medium`/`low`/`insufficient`. CASE expression over the 4 independent raw inputs. |
| 15 | `promoted_at` | `TimestampType` | yes | `datetime.now()` at promote time | Identical across all rows in a single consumable promote. |
| 16 | `endowment_value_provenance` (v1.4) | `StringType` | no | `base.ipeds_finance.endowment_value_flag` (renamed passthrough) | **NEW v1.4** — Renamed passthrough from base; **CDE** per spec §6 Data Contract delta — interpretation-changing for `endowment_value` and `endowment_per_fte`. Domain `{R, A, P, Z, N}` OR NULL. **Authoritative semantics (corrected v1.2):** `R` = Reported by institution; `A` = **Not applicable** (no endowment fund — exact `A`↔NULL coupling on `endowment_value`, invariant per BSE-IPF-020); `N` = **Imputed using Nearest Neighbor procedure**; `P` = Imputed prior year; `Z` = Imputed zero. NULL on F3 by structure. Validated by CON-IFP-013 (P0 rename-fidelity). |
| 17 | `source_load_date` (v1.4) | `DateType` | yes | `base.ipeds_finance.source_load_date` (passthrough) | **NEW v1.4** — Restored vintage-observability passthrough from base per spec §2 Decision G (v1.3 dropped this column; v1.4 restores it). **Explicitly NOT CDE** per spec §6 Data Contract delta — metadata-only. Validated by CON-IFP-015 (P0 NOT NULL) and CON-IFP-016 (P1 within 400 days of `promoted_at`). |

**Total fields:** 17 (5 identity + 1 FTE + 3 raw expense passthroughs + 3 per-FTE derivations + 1 marketing-ratio + 1 tier + 1 promote stamp + **1 imputation provenance, v1.4** + **1 vintage-observability passthrough, v1.4**).

### Field-ID Stability

Field IDs 1–17 are pinned. Field IDs 1–15 are unchanged from v1.0–v1.3; field IDs 16 (`endowment_value_provenance`) and 17 (`source_load_date`) were added in v1.4 — strictly additive at the tail. Future schema evolution must allocate IDs ≥ 18 and **never** rebind 1–17 to other columns. Standard Iceberg-evolution discipline.

### Verified-Landed Schema

Verified via Iceberg metadata at `data/gold/iceberg_warehouse/consumable/ipeds_finance_profile/metadata/00001-f4e93ae5-0895-4f0e-b162-733ce80e413b.metadata.json` — all 15 fields present, all field IDs 1–15 in the order documented above, all types as documented, all nullability as documented. **Landed schema matches spec §6 Consumable Schema exactly.**

---

## PyIceberg Schema Definition

```python
from pyiceberg.schema import Schema
from pyiceberg.types import (
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
    NestedField(6,  "total_fte_enrollment",          DoubleType(),    required=False),
    NestedField(7,  "instruction_expenses",          DoubleType(),    required=False),
    NestedField(8,  "institutional_support_expenses", DoubleType(),   required=False),
    NestedField(9,  "endowment_value",               DoubleType(),    required=False),
    NestedField(10, "institutional_support_per_fte", DoubleType(),    required=False),
    NestedField(11, "instruction_per_fte",           DoubleType(),    required=False),
    NestedField(12, "endowment_per_fte",             DoubleType(),    required=False),
    NestedField(13, "marketing_ratio",               DoubleType(),    required=False),
    NestedField(14, "data_completeness_tier",        StringType(),    required=True),
    NestedField(15, "promoted_at",                   TimestampType(), required=True),
    NestedField(16, "endowment_value_provenance",    StringType(),    required=False),  # v1.4 — renamed CDE passthrough from base.ipeds_finance.endowment_value_flag
    NestedField(17, "source_load_date",              DateType(),      required=True),   # v1.4 — restored NOT-CDE vintage-observability passthrough from base
)

# v1.4 also imports DateType from pyiceberg.types
```

---

## Promote Pattern

Per spec §6:

- **Grain:** `unitid`
- **Dedup grain:** `[unitid]`
- **Promote pattern:** `compute_grain_id(row, ['unitid'], prefix='ifp')`
- **Idempotent:** Yes
- **Source:** `base.ipeds_finance`
- **Expected rows (v1.4):** between (Base row count - 50) and Base row count, exclusive of the system-administrative-office cluster excluded by the v1.4 row-filter (8-pattern AND 4-clause-numeric-proxy). FY2023 measured: 2,630 rows (45 excluded against 2,675-row base).
- **Expected rows (v1.3 historical):** matched Base row count exactly (CON-IFP-001 strict equality; replaced in v1.4 by CON-IFP-001a/001b band).

```python
from brightsmith.infra.grain import compute_grain_id
from brightsmith.infra.promote import promote
from datetime import datetime

TIER_HIGH = "high"
TIER_MEDIUM = "medium"
TIER_LOW = "low"
TIER_INSUFFICIENT = "insufficient"

def classify_tier(row) -> str:
    """Count non-null independent raw inputs and classify completeness."""
    n = 0
    if row.get('instruction_expenses') is not None:
        n += 1
    if row.get('institutional_support_expenses') is not None:
        n += 1
    if row.get('endowment_value') is not None:
        n += 1
    fte = row.get('total_fte_enrollment')
    if fte is not None and fte > 0:
        n += 1

    if n == 4:
        return TIER_HIGH
    elif n >= 2:
        return TIER_MEDIUM
    elif n == 1:
        return TIER_LOW
    return TIER_INSUFFICIENT


def promote_ipeds_finance_profile(*, project_dir):
    base_df = read_base_ipeds_finance(project_dir)

    # 1. Passthroughs from Base (12 fields)
    df = base_df[[
        'unitid', 'institution_name', 'report_form', 'fiscal_year',
        'total_fte_enrollment',
        'instruction_expenses', 'institutional_support_expenses', 'endowment_value',
        'institutional_support_per_fte', 'instruction_per_fte',
        'endowment_per_fte', 'marketing_ratio',
    ]].copy()

    # 2. Synthesize data_completeness_tier (4 independent raw inputs)
    df['data_completeness_tier'] = df.apply(classify_tier, axis=1)

    # 3. Provenance
    df['promoted_at'] = datetime.utcnow()

    # 4. Deterministic record_id (note 'ifp' prefix, distinct from Base's 'ipf')
    df['record_id'] = df.apply(
        lambda row: compute_grain_id(row, ['unitid'], prefix='ifp'), axis=1
    )

    # 5. Column order matches SCHEMA
    df = df[[
        'record_id', 'unitid', 'institution_name', 'report_form', 'fiscal_year',
        'total_fte_enrollment',
        'instruction_expenses', 'institutional_support_expenses', 'endowment_value',
        'institutional_support_per_fte', 'instruction_per_fte', 'endowment_per_fte', 'marketing_ratio',
        'data_completeness_tier', 'promoted_at',
    ]]

    promote(df, table='consumable.ipeds_finance_profile', schema=SCHEMA, dedup_on=['unitid'])
```

Idempotency guarantees:
- **Determinism:** `record_id` is a pure function of `unitid` with constant prefix `ifp`. Re-running yields identical hashes (verified: Stanford UNITID 243744 → `ifp-267f20f48b4b772f` across multiple promotes).
- **Dedup grain:** `[unitid]` ensures a re-run with identical Base input produces zero new rows.
- **Conservation:** Every Base row promotes to exactly one consumable row (CON-IFP-001 P0).
- **Tier determinism:** `classify_tier()` is a pure function of four input values; the same row always classifies to the same tier (CON-IFP-006 enforces this by re-computing on read).

---

## Tier Classification — Reference Implementation

The exact CASE expression that the consumable transformer materializes and that CON-IFP-006 re-checks:

```sql
CASE
  WHEN (
    (instruction_expenses IS NOT NULL)::int +
    (institutional_support_expenses IS NOT NULL)::int +
    (endowment_value IS NOT NULL)::int +
    (total_fte_enrollment IS NOT NULL AND total_fte_enrollment > 0)::int
  ) = 4 THEN 'high'
  WHEN (
    (instruction_expenses IS NOT NULL)::int +
    (institutional_support_expenses IS NOT NULL)::int +
    (endowment_value IS NOT NULL)::int +
    (total_fte_enrollment IS NOT NULL AND total_fte_enrollment > 0)::int
  ) >= 2 THEN 'medium'
  WHEN (
    (instruction_expenses IS NOT NULL)::int +
    (institutional_support_expenses IS NOT NULL)::int +
    (endowment_value IS NOT NULL)::int +
    (total_fte_enrollment IS NOT NULL AND total_fte_enrollment > 0)::int
  ) = 1 THEN 'low'
  ELSE 'insufficient'
END
```

The four input clauses are deliberately independent raw inputs (NOT derived signals). This is the v1.1 reformulation that prevents the v1.0 inflation effect where a present `marketing_ratio` re-counted the two expense fields it was derived from.

By construction:
- F3 rows always cap at `medium` because `endowment_value` is structurally NULL on F3 (no `F3H` family). Verified: F3 = `medium:277, high:0`.
- Rows with NULL `total_fte_enrollment` cap at `medium` because all three per-FTE values would NULL-cascade and the row is unusable for per-student comparison.

---

## DDL (Reference)

This DDL is for documentation. The actual table is created via `brightsmith.infra.promote.promote()` which handles Iceberg table creation and idempotent writes.

```sql
-- Reference DDL for consumable.ipeds_finance_profile
-- Engine: DuckDB + Iceberg v2
-- Do not execute directly -- use promote() pattern

CREATE TABLE IF NOT EXISTS consumable.ipeds_finance_profile (
    record_id                       VARCHAR     NOT NULL,
    unitid                          BIGINT      NOT NULL,
    institution_name                VARCHAR     NOT NULL,
    report_form                     VARCHAR     NOT NULL,
    fiscal_year                     INTEGER     NOT NULL,
    total_fte_enrollment            DOUBLE,
    instruction_expenses            DOUBLE,
    institutional_support_expenses  DOUBLE,
    endowment_value                 DOUBLE,
    institutional_support_per_fte   DOUBLE,
    instruction_per_fte             DOUBLE,
    endowment_per_fte               DOUBLE,
    marketing_ratio                 DOUBLE,
    data_completeness_tier          VARCHAR     NOT NULL,
    promoted_at                     TIMESTAMP   NOT NULL,

    PRIMARY KEY (record_id),
    UNIQUE (unitid),

    CHECK (report_form IN ('F1A','F2','F3')),
    CHECK (data_completeness_tier IN ('high','medium','low','insufficient'))
);
```

---

## Source-to-Target Mapping

| Physical Column | DuckDB Type | Source Table | Source Field | Transformation |
|-----------------|-------------|--------------|--------------|----------------|
| record_id | VARCHAR | -- | derived | `compute_grain_id(row, ['unitid'], prefix='ifp')` |
| unitid | BIGINT | base.ipeds_finance | unitid | Direct passthrough |
| institution_name | VARCHAR | base.ipeds_finance | institution_name | Direct passthrough |
| report_form | VARCHAR | base.ipeds_finance | report_form | Direct passthrough |
| fiscal_year | INTEGER | base.ipeds_finance | fiscal_year | Direct passthrough |
| total_fte_enrollment | DOUBLE | base.ipeds_finance | total_fte_enrollment | Direct passthrough |
| instruction_expenses | DOUBLE | base.ipeds_finance | instruction_expenses | Direct passthrough (raw expense exposed at consumable per spec §6) |
| institutional_support_expenses | DOUBLE | base.ipeds_finance | institutional_support_expenses | Direct passthrough (raw expense exposed at consumable per spec §6) |
| endowment_value | DOUBLE | base.ipeds_finance | endowment_value | Direct passthrough (raw expense exposed at consumable per spec §6) |
| institutional_support_per_fte | DOUBLE | base.ipeds_finance | institutional_support_per_fte | Direct passthrough |
| instruction_per_fte | DOUBLE | base.ipeds_finance | instruction_per_fte | Direct passthrough |
| endowment_per_fte | DOUBLE | base.ipeds_finance | endowment_per_fte | Direct passthrough |
| marketing_ratio | DOUBLE | base.ipeds_finance | marketing_ratio | Direct passthrough |
| data_completeness_tier | VARCHAR | -- | derived | CASE expression over 4 independent raw inputs (see "Tier Classification" above) |
| promoted_at | TIMESTAMP | -- | generated | `datetime.utcnow()` at promote time |

---

## Load Statistics (FY2023, snapshot 6649279885162971471)

| Metric | Value |
|--------|------:|
| Rows | 2,675 |
| Distinct `unitid` | 2,675 (100% unique) |
| `record_id` non-null | 2,675 / 2,675 |
| `record_id` unique | 2,675 / 2,675 |
| `report_form` distinct values | 3 — F1A 819 (30.6%) / F2 1,579 (59.0%) / F3 277 (10.4%) |
| `institution_name` non-null | 100.00% |
| `instruction_expenses` non-null | 100.00% |
| `institutional_support_expenses` non-null | 100.00% |
| `endowment_value` non-null | 76.00% (F3 structural + small F2 institutions) |
| `total_fte_enrollment` non-null | 97.94% |
| `institutional_support_per_fte` non-null | 97.94% |
| `instruction_per_fte` non-null | 97.94% |
| `endowment_per_fte` non-null | 74.69% |
| `marketing_ratio` non-null | 98.84% |
| `data_completeness_tier` non-null | 100.00% |
| `data_completeness_tier=high` count | 1,998 (74.7%) |
| `data_completeness_tier=medium` count | 677 (25.3%) |
| `data_completeness_tier=low` count | 0 |
| `data_completeness_tier=insufficient` count | 0 |
| Per-form tier (FY23) | F1A `high:706, medium:113`; F2 `high:1,292, medium:287`; F3 `high:0, medium:277` |
| Stanford spot check (UNITID 243744) | `tier=high`, `marketing_ratio=0.30193`, `record_id=ifp-267f20f48b4b772f` |
| F3 spot check (UNITID 101116, South University-Montgomery) | `tier=medium`, `endowment_value=NULL`, 3/4 raw inputs present |
| Conservation invariant (CON-IFP-001) | 2,675 == 2,675 (Base) ✓ |
| UNITID overlap with `consumable.career_outcomes` | 88.71% (CON-IFP-008 floor: 88%) |

Source: scripts/promote_ipeds_finance_profile.py output + ad-hoc DuckDB queries against the landed Parquet files.

---

## Cross-References

| Artifact | Path |
|----------|------|
| Spec | `docs/specs/full-pipeline-ipeds-finance.md` (§6) |
| Transformer | `src/gold/ipeds_finance_profile.py` |
| Runner | `scripts/promote_ipeds_finance_profile.py` |
| Conceptual model | `governance/models/consumable-ipeds-finance-profile-conceptual.md` |
| Logical model | `governance/models/consumable-ipeds-finance-profile-logical.md` |
| Base model | `governance/models/base-ipeds-finance-{conceptual,logical,physical}.md` |
| DQ rules | `governance/dq-rules/consumable-ipeds-finance-profile.json` (11 rules: 8 P0 + 2 P1 + 1 P2) |
| DQ scorecard | `governance/dq-scorecards/full-pipeline-ipeds-finance-scorecard.md` |
| Data dictionary | `governance/data-dictionaries/consumable-ipeds-finance-profile.md` |
| Data contract | `governance/data-contracts/consumable-ipeds-finance-profile.yaml` |
| Domain context | `governance/domain-context.md` § IPEDS Finance Survey |
| EDA report | `governance/eda/raw-ingest-ipeds-finance-eda.md` |
| Adversarial audit | `governance/adversarial-audits/consumable-ipeds-finance-profile.md` (companion artifact) |
| CDE tagging | `governance/cde-tagging/consumable-ipeds-finance-profile.md` (companion artifact) |
| Lineage | `governance/lineage/full-pipeline-ipeds-finance-{timestamp}.json` |

---

## Modeling Decisions (Physical Layer)

1. **`consumable.ipeds_finance_profile` namespace.** Matches the catalog convention for every Gold/Consumable table (`consumable.regional_price_parities`, `consumable.career_outcomes`, `consumable.occupation_profiles`).

2. **`DoubleType` for all monetary, per-FTE, and ratio fields.** Matches Base; preserves the BSE-IPF-008/009/010 arithmetic invariants through the consumable layer. CON-IFP-007 (`institutional_support_per_fte / instruction_per_fte ≈ marketing_ratio` within 0.001) is computable in DOUBLE precision.

3. **`required=True` on `data_completeness_tier`.** Every row gets a tier — the `insufficient` enum value covers the all-NULL-inputs degenerate case. CON-IFP-005 P0 enforces the closed enum domain.

4. **`required=False` on the four monetary inputs, the FTE denominator, the three per-FTE derivations, and the marketing-ratio.** Honest NULL propagation; standing user constraint "no substitution-based degraded states."

5. **Three raw expense passthroughs (`instruction_expenses`, `institutional_support_expenses`, `endowment_value`) at consumable.** Narrow exception to the standard "consumable is shaped, not raw-pass-through" Brightsmith convention, justified by the named downstream consumer `raw-ingest-eada.md`. Documented inline in the schema notes ("Raw passthrough USD. Exposed at consumable for downstream EADA composite ratios.") and in §6 of the spec.

6. **Column order: identity → enrollment → raw expenses → per-FTE derivations → marketing-ratio → tier → provenance.** Per spec §6 Consumable Schema. Groups related fields together: the four monetary inputs sit alongside each other, the three per-FTE derivations sit alongside each other, and the marketing-ratio sits between the per-FTE rates and the tier (matching the analytical reading order: raw → per-student → cross-field-ratio → completeness summary).

7. **`record_id` prefix `ifp` — distinct from Base's `ipf`.** Per spec §6 promote pattern. Cross-zone hash collisions impossible by construction. The `ifp` mnemonic is "**i**peds-**f**inance-**p**rofile" (consumable); the `ipf` mnemonic is "**i**peds-**f**inance" without the profile suffix (Base).

8. **No partition spec.** Single-cycle snapshot; fits trivially in unpartitioned storage. Future multi-cycle backfill should add `PARTITION BY fiscal_year`.

9. **No sort spec.** Read patterns are dominated by individual-UNITID lookups (downstream EADA fusion) and full-table scans (downstream analytics). Neither benefits significantly from a sort key on a 2,675-row table.

10. **`promoted_at` is the only consumable-zone provenance.** Base carries `source_load_date` + `ingested_at`; the consumable carries only `promoted_at`. The Bronze load_date is recoverable via join to `base.ipeds_finance` if needed; downstream consumers don't typically need it.

11. **Tier classification implementation: pure-Python `classify_tier()` function, not SQL CASE.** The reference SQL above is for documentation and DQ-rule re-checking (CON-IFP-006). The transformer uses pure-Python because Pandas-style row-wise access is the natural shape for the Bronze-→Base-→Consumable data flow.

12. **No imputation flag column.** Consistent with Base/Bronze; future v1.4 `endowment_value_provenance` column would be a Bronze schema change first, then a Base/Consumable passthrough.
