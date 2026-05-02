# Physical Model: consumable-institution-aura

**Status:** PROPOSED
**Mode:** Greenfield (cross-source fusion)
**Zone:** Gold (Consumable)
**Spec:** [docs/specs/full-pipeline-eada.md](../../docs/specs/full-pipeline-eada.md) §6
**Logical model:** [consumable-institution-aura-logical.md](consumable-institution-aura-logical.md)
**Conceptual model:** [consumable-institution-aura-conceptual.md](consumable-institution-aura-conceptual.md)
**Author:** @doc-generator
**Date:** 2026-04-30
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)

---

## Iceberg Table

- **Logical name:** `consumable.institution_aura`
- **Physical Iceberg namespace:** `consumable.institution_aura` (matches the catalog convention used by sibling Gold/Consumable tables — `consumable.ipeds_finance_profile`, `consumable.regional_price_parities`, `consumable.career_outcomes`, `consumable.occupation_profiles`)
- **Format:** Apache Iceberg over Parquet (v2)
- **Catalog:** Brightsmith Gold SQL catalog (`data/gold/iceberg_warehouse/`); registered in `data/catalog/catalog.db`
- **Partition spec:** none (single-snapshot view; matches Base layer)
- **Sort spec:** none
- **Storage location:** `data/gold/iceberg_warehouse/consumable/institution_aura/`
- **Created by:** [`src/gold/institution_aura.py`](../../src/gold/institution_aura.py) (640 lines) — `transform()` / `promote_institution_aura()`
- **Current snapshot:** `5887248523326294782` (3,223 rows; FY2023 Finance × 2022 EADA)
- **Idempotent promote:** `brightsmith.infra.promote.promote(..., dedup_on=['unitid'])` — re-running with the same source snapshots produces 0 new rows

---

## Iceberg Schema

The schema is defined in code at `src/gold/institution_aura.py` and materialized via `brightsmith.infra.promote.promote()`. Field IDs are stable; never reassign on schema evolution.

| Field ID | Field | Iceberg Type | Required | Source | Physical Notes |
|---:|-------|--------------|:--------:|--------|----------------|
| 1 | `record_id` | `StringType` | yes | `compute_grain_id(row, ['unitid'], prefix='aur')` | Format: `aur-<16 hex>`. Distinct from Base prefixes `ipf`/`ead` and from sibling consumable prefix `ifp`. |
| 2 | `unitid` | `LongType` | yes | `COALESCE(f.unitid, e.unitid)` | Natural key; coalesced from FULL OUTER. |
| 3 | `institution_name` | `StringType` | yes | `COALESCE(f.institution_name, e.institution_name)` | Display-only. |
| 4 | `endowment_per_fte` | `DoubleType` | no | `base.ipeds_finance.endowment_per_fte` (passthrough) | Aura input — feeds `rp_endowment`. |
| 5 | `institutional_support_per_fte` | `DoubleType` | no | `base.ipeds_finance.institutional_support_per_fte` (passthrough) | NOT an aura input directly; CON-AUR-007 cross-checks the marketing-ratio arithmetic identity. |
| 6 | `instruction_per_fte` | `DoubleType` | no | `base.ipeds_finance.instruction_per_fte` (passthrough) | NOT an aura input directly; CON-AUR-007. |
| 7 | `marketing_ratio` | `DoubleType` | no | `base.ipeds_finance.marketing_ratio` (passthrough) | Aura input — feeds `rp_marketing`. |
| 8 | `athletic_spend_per_fte` | `DoubleType` | no | `base.eada.athletic_spend_per_fte` (passthrough) | Aura input — feeds `rp_athletic`. FTE denominator provenance in `athletic_fte_source` (col 11). |
| 9 | `athletic_revenue_per_fte` | `DoubleType` | no | `base.eada.athletic_revenue_per_fte` (passthrough) | Context column only. |
| 10 | `athletic_subsidy_ratio` | `DoubleType` | no | `base.eada.athletic_subsidy_ratio` (passthrough) | **Context column only — NOT an aura input** (spec §2 Decision 11). |
| 11 | `athletic_fte_source` | `StringType` | no | `base.eada.fte_source` (passthrough, renamed) | Enum-valued: `ipeds_finance` / `eada_fte_headcount` / `none`. Methodological-provenance CDE. NULL on `coverage_tier='finance_only'` rows. |
| 12 | `aura_score` | `IntegerType` | no | derived (v1 composite) | Integer 1–10. NULL ⇔ `aura_score_basis IS NULL` (CON-AUR-034 P0). |
| 13 | `aura_score_continuous` | `DoubleType` | no | derived (v1 composite) | Pre-rounding continuous value in [1.0, 10.0] (CON-AUR-014 P0). |
| 14 | `aura_score_version` | `StringType` | yes | constant `"v1"` | CON-AUR-012 P0 enforces the stamp. |
| 15 | `aura_score_basis` | `StringType` | no | derived (5-value enum) | `three_term` / `two_term_finance_only` / `two_term_no_endowment` / `one_term_marketing_only` / NULL. CON-AUR-033 P0 enforces the closed enum. |
| 16 | `has_ipeds_finance` | `BooleanType` | yes | `f.unitid IS NOT NULL` | TRUE on 2,675 rows (live). |
| 17 | `has_eada` | `BooleanType` | yes | `e.unitid IS NOT NULL` | TRUE on 2,040 rows (live). |
| 18 | `coverage_tier` | `StringType` | yes | derived (CASE) | `both` / `finance_only` / `athletics_only`. CON-AUR-005 P0 enforces the closed enum. |
| 19 | `promoted_at` | `TimestampType` | yes | `datetime.now()` at promote time | Identical across all rows in a single consumable promote. |

**Total fields:** 19 (3 identity + 4 finance signals + 3 athletics signals + 1 FTE-source provenance + 4 aura columns + 3 coverage flags + 1 provenance).

### Field-ID Stability

Field IDs 1–19 are pinned. Future schema evolution (e.g., adding a v2 score column, surfacing additional EADA fields like `direct_institutional_support`, or adding sport-specific aura facets) must allocate IDs ≥ 20 and **never** rebind 1–19 to other columns. Standard Iceberg-evolution discipline.

### Verified-Landed Schema

Verified via Iceberg metadata for snapshot `5887248523326294782` — all 19 fields present in the order documented above, all field IDs 1–19, all types as documented, all nullability as documented. **Landed schema matches spec §6 Consumable Schema exactly** (modulo the column ordering inherited from the transformer, which groups identity → finance → athletics → fte-source → aura → coverage → provenance per spec §6's logical reading order).

---

## PyIceberg Schema Definition

Verbatim from `src/gold/institution_aura.py:158-176`:

```python
from pyiceberg.schema import Schema
from pyiceberg.types import (
    BooleanType,
    DoubleType,
    IntegerType,
    LongType,
    NestedField,
    StringType,
    TimestampType,
)

SCHEMA = Schema(
    NestedField(1,  "record_id",                      StringType(),    required=True),
    NestedField(2,  "unitid",                         LongType(),      required=True),
    NestedField(3,  "institution_name",               StringType(),    required=True),
    NestedField(4,  "endowment_per_fte",              DoubleType(),    required=False),
    NestedField(5,  "institutional_support_per_fte",  DoubleType(),    required=False),
    NestedField(6,  "instruction_per_fte",            DoubleType(),    required=False),
    NestedField(7,  "marketing_ratio",                DoubleType(),    required=False),
    NestedField(8,  "athletic_spend_per_fte",         DoubleType(),    required=False),
    NestedField(9,  "athletic_revenue_per_fte",       DoubleType(),    required=False),
    NestedField(10, "athletic_subsidy_ratio",         DoubleType(),    required=False),
    NestedField(11, "athletic_fte_source",            StringType(),    required=False),
    NestedField(12, "aura_score",                     IntegerType(),   required=False),
    NestedField(13, "aura_score_continuous",          DoubleType(),    required=False),
    NestedField(14, "aura_score_version",             StringType(),    required=True),
    NestedField(15, "aura_score_basis",               StringType(),    required=False),
    NestedField(16, "has_ipeds_finance",              BooleanType(),   required=True),
    NestedField(17, "has_eada",                       BooleanType(),   required=True),
    NestedField(18, "coverage_tier",                  StringType(),    required=True),
    NestedField(19, "promoted_at",                    TimestampType(), required=True),
)
```

---

## Promote Pattern

Per spec §6:

- **Grain:** `unitid`
- **Dedup grain:** `[unitid]`
- **Promote pattern:** `compute_grain_id(row, ['unitid'], prefix='aur')`
- **Idempotent:** Yes
- **Sources:** `base.ipeds_finance` FULL OUTER JOIN `base.eada` on UNITID
- **Expected rows:** Bounded by `[max(N_finance, N_eada), N_finance + N_eada] = [2,675, 4,715]`; observed 3,223

```python
from brightsmith.infra.grain import compute_grain_id
from brightsmith.infra.promote import promote
from datetime import datetime
import pandas as pd

AURA_SCORE_VERSION = "v1"
WEIGHT_MAX = 0.65
WEIGHT_MEAN = 0.35
RAW_SCORE_P5 = 0.1413
RAW_SCORE_P95 = 0.9400


def compute_rp(series: pd.Series) -> pd.Series:
    """Population-level percent rank, NULL-skipping (NULL inputs stay NULL in output)."""
    non_null = series.dropna()
    ranks = non_null.rank(method="average", pct=True) if len(non_null) > 1 else pd.Series([0.5] * len(non_null), index=non_null.index)
    out = pd.Series([None] * len(series), index=series.index, dtype="float64")
    out.loc[non_null.index] = ranks
    return out


def assign_basis(rp_marketing, rp_endowment, rp_athletic) -> str | None:
    """Per-row basis assignment for the 5-value enum."""
    if rp_marketing is None:
        return None  # athletics_only OR zero-instruction edge case
    has_endow = rp_endowment is not None
    has_ath   = rp_athletic  is not None
    if has_endow and has_ath:
        return "three_term"
    if has_endow and not has_ath:
        return "two_term_finance_only"
    if has_ath and not has_endow:
        return "two_term_no_endowment"
    return "one_term_marketing_only"  # only marketing


def compute_aura(rp_marketing, rp_endowment, rp_athletic, basis):
    if basis is None:
        return None, None
    available = [r for r in (rp_marketing, rp_endowment, rp_athletic) if r is not None]
    raw_score = WEIGHT_MAX * max(available) + WEIGHT_MEAN * (sum(available) / len(available))
    t = (raw_score - RAW_SCORE_P5) / (RAW_SCORE_P95 - RAW_SCORE_P5)
    t_clipped = max(0.0, min(1.0, t))
    cont = 1.0 + 9.0 * t_clipped
    return cont, round(cont)


def promote_institution_aura(*, project_dir):
    f = read_base_ipeds_finance(project_dir)
    e = read_base_eada(project_dir)

    # 1. FULL OUTER JOIN on unitid
    df = f.merge(e, how="outer", on="unitid", suffixes=("_f", "_e"))

    # 2. Coalesce identity columns
    df["institution_name"] = df["institution_name_f"].combine_first(df["institution_name_e"])

    # 3. Coverage flags
    df["has_ipeds_finance"] = df["unitid"].isin(f["unitid"])
    df["has_eada"]          = df["unitid"].isin(e["unitid"])
    df["coverage_tier"] = df.apply(
        lambda r: "both" if r["has_ipeds_finance"] and r["has_eada"]
                  else ("finance_only" if r["has_ipeds_finance"] else "athletics_only"),
        axis=1,
    )

    # 4. Population-level percent ranks (computed across rows where signal non-null)
    rp_mkt   = compute_rp(df["marketing_ratio"])
    rp_endow = compute_rp(df["endowment_per_fte"])
    rp_ath   = compute_rp(df["athletic_spend_per_fte"])

    # 5. Per-row basis + score
    df["aura_score_basis"] = [assign_basis(m, e_, a) for m, e_, a in zip(rp_mkt, rp_endow, rp_ath)]
    cont_scores = [compute_aura(m, e_, a, b)
                   for m, e_, a, b in zip(rp_mkt, rp_endow, rp_ath, df["aura_score_basis"])]
    df["aura_score_continuous"] = [c[0] for c in cont_scores]
    df["aura_score"]            = [c[1] for c in cont_scores]
    df["aura_score_version"]    = AURA_SCORE_VERSION

    # 6. Provenance
    df["promoted_at"] = datetime.utcnow()

    # 7. Deterministic record_id (note 'aur' prefix)
    df["record_id"] = df.apply(
        lambda row: compute_grain_id(row, ["unitid"], prefix="aur"), axis=1,
    )

    # 8. Column order matches SCHEMA (19 columns, fields 1–19)
    df = df[[
        "record_id", "unitid", "institution_name",
        "endowment_per_fte", "institutional_support_per_fte", "instruction_per_fte", "marketing_ratio",
        "athletic_spend_per_fte", "athletic_revenue_per_fte", "athletic_subsidy_ratio",
        "athletic_fte_source",
        "aura_score", "aura_score_continuous", "aura_score_version", "aura_score_basis",
        "has_ipeds_finance", "has_eada", "coverage_tier",
        "promoted_at",
    ]]

    promote(df, table="consumable.institution_aura", schema=SCHEMA, dedup_on=["unitid"])
```

> The reference code above is illustrative; the production transformer at `src/gold/institution_aura.py` is the authoritative implementation (640 lines, includes additional input-validation, logging, and constant-pinning around the v1 P5/P95 bounds).

Idempotency guarantees:
- **Determinism:** `record_id` is a pure function of `unitid` with constant prefix `aur`. Re-running with the same source snapshots yields identical hashes.
- **Dedup grain:** `[unitid]` ensures a re-run with identical Base inputs produces zero new rows.
- **Conservation:** Row count ∈ [max(N_finance, N_eada), N_finance + N_eada] = [2,675, 4,715] (CON-AUR-001 P0). Observed 3,223 lands within.
- **Basis determinism:** `assign_basis()` is a pure function of three rp_* values; the same row always classifies to the same basis (CON-AUR-033 P0 enforces enum domain; CON-AUR-034 P0 enforces the iff-NULL invariant against `aura_score`).
- **Round-correctness:** `aura_score == ROUND(aura_score_continuous)` for every row where both non-null (CON-AUR-013 P0).

---

## v1 Aura Score — Reference Algorithm

The exact computation that the consumable transformer materializes and that CON-AUR-010..014/030..034 verify on read:

### Step 1 — Population-Level Rank-Percentile Transform

For each input signal `s ∈ {marketing_ratio, endowment_per_fte, athletic_spend_per_fte}`, compute:

```sql
rp_s = PERCENT_RANK() OVER (ORDER BY s) -- where s IS NOT NULL
```

Rows with NULL `s` get NULL `rp_s` (no imputation). This matches the Brightsmith HMN convention of computing percentile transforms across the population of non-null observations.

### Step 2 — Per-Row Basis Assignment (5-value enum)

```python
if rp_marketing is None:
    basis = None  # athletics_only OR zero-instruction edge case → no aura
elif rp_endowment is not None and rp_athletic is not None:
    basis = "three_term"
elif rp_endowment is not None:
    basis = "two_term_finance_only"
elif rp_athletic is not None:
    basis = "two_term_no_endowment"
else:
    basis = "one_term_marketing_only"
```

### Step 3 — MAX + MEAN Composite

For rows with non-NULL basis:

```python
available = [r for r in (rp_marketing, rp_endowment, rp_athletic) if r is not None]
raw_score = 0.65 * max(available) + 0.35 * (sum(available) / len(available))
```

### Step 4 — P5/P95 Percentile Rescale to [1, 10]

```python
t = (raw_score - 0.1413) / (0.9400 - 0.1413)
t_clipped = max(0.0, min(1.0, t))
aura_score_continuous = 1.0 + 9.0 * t_clipped   # in [1.0, 10.0]
aura_score = round(aura_score_continuous)        # in [1, 10]
```

The P5/P95 bounds (`0.1413` / `0.9400`) are population-level percentiles of `raw_score` across the production population, EDA-pinned 2026-04-30 and recomputed on each annual refresh.

### Step 5 — Stamp Provenance

```python
aura_score_version = "v1"
```

By construction:
- Athletics-only rows (548) have NULL `marketing_ratio` → NULL basis → NULL aura_score and NULL aura_score_continuous.
- Zero-instruction-expense edge cases (31) have NULL `marketing_ratio` (because instruction is 0 ⇒ marketing_ratio is NULL) → NULL aura, even though `has_ipeds_finance = TRUE`. This is why CON-AUR-011/034 enforce the basis-tagged invariant rather than the spec-as-written `iff has_ipeds_finance = FALSE` shorthand.
- 14 anchor schools (UNITIDs Harvard 166027, Princeton 186131, Stanford 243744, MIT 166683, Yale 130794, Duke 198419, Cornell 190415, Northwestern 147767, Alabama 100751, Phoenix 484613, Ohio State 204796, Michigan 170976, Grand Canyon 104717, Liberty 232557) produce the EDA-validated v1 scores documented in CON-AUR-032.

---

## DDL (Reference)

This DDL is for documentation. The actual table is created via `brightsmith.infra.promote.promote()` which handles Iceberg table creation and idempotent writes.

```sql
-- Reference DDL for consumable.institution_aura
-- Engine: DuckDB + Iceberg v2
-- Do not execute directly -- use promote() pattern

CREATE TABLE IF NOT EXISTS consumable.institution_aura (
    record_id                       VARCHAR     NOT NULL,
    unitid                          BIGINT      NOT NULL,
    institution_name                VARCHAR     NOT NULL,
    endowment_per_fte               DOUBLE,
    institutional_support_per_fte   DOUBLE,
    instruction_per_fte             DOUBLE,
    marketing_ratio                 DOUBLE,
    athletic_spend_per_fte          DOUBLE,
    athletic_revenue_per_fte        DOUBLE,
    athletic_subsidy_ratio          DOUBLE,
    athletic_fte_source             VARCHAR,
    aura_score                      INTEGER,
    aura_score_continuous           DOUBLE,
    aura_score_version              VARCHAR     NOT NULL,
    aura_score_basis                VARCHAR,
    has_ipeds_finance               BOOLEAN     NOT NULL,
    has_eada                        BOOLEAN     NOT NULL,
    coverage_tier                   VARCHAR     NOT NULL,
    promoted_at                     TIMESTAMP   NOT NULL,

    PRIMARY KEY (record_id),
    UNIQUE (unitid),

    CHECK (aura_score IS NULL OR (aura_score BETWEEN 1 AND 10)),
    CHECK (aura_score_continuous IS NULL OR (aura_score_continuous BETWEEN 1.0 AND 10.0)),
    CHECK (aura_score_version = 'v1'),
    CHECK (aura_score_basis IS NULL OR aura_score_basis IN ('three_term','two_term_finance_only','two_term_no_endowment','one_term_marketing_only')),
    CHECK (athletic_fte_source IS NULL OR athletic_fte_source IN ('ipeds_finance','eada_fte_headcount','none')),
    CHECK (coverage_tier IN ('both','finance_only','athletics_only')),
    CHECK ((aura_score IS NULL) = (aura_score_basis IS NULL))   -- CON-AUR-034 invariant
);
```

---

## Source-to-Target Mapping

| Physical Column | DuckDB Type | Source Table | Source Field | Transformation |
|-----------------|-------------|--------------|--------------|----------------|
| record_id | VARCHAR | -- | derived | `compute_grain_id(row, ['unitid'], prefix='aur')` |
| unitid | BIGINT | base.ipeds_finance + base.eada | unitid | `COALESCE(f.unitid, e.unitid)` |
| institution_name | VARCHAR | base.ipeds_finance + base.eada | institution_name | `COALESCE(f.institution_name, e.institution_name)` |
| endowment_per_fte | DOUBLE | base.ipeds_finance | endowment_per_fte | Direct passthrough |
| institutional_support_per_fte | DOUBLE | base.ipeds_finance | institutional_support_per_fte | Direct passthrough |
| instruction_per_fte | DOUBLE | base.ipeds_finance | instruction_per_fte | Direct passthrough |
| marketing_ratio | DOUBLE | base.ipeds_finance | marketing_ratio | Direct passthrough |
| athletic_spend_per_fte | DOUBLE | base.eada | athletic_spend_per_fte | Direct passthrough |
| athletic_revenue_per_fte | DOUBLE | base.eada | athletic_revenue_per_fte | Direct passthrough |
| athletic_subsidy_ratio | DOUBLE | base.eada | athletic_subsidy_ratio | Direct passthrough (CONTEXT only — NOT an aura input) |
| athletic_fte_source | VARCHAR | base.eada | fte_source | Renamed passthrough |
| aura_score | INTEGER | -- | derived | `ROUND(aura_score_continuous)` per the v1 algorithm above |
| aura_score_continuous | DOUBLE | -- | derived | v1 MAX+MEAN composite + P5/P95 rescale (see "v1 Aura Score — Reference Algorithm" above) |
| aura_score_version | VARCHAR | -- | constant | `"v1"` |
| aura_score_basis | VARCHAR | -- | derived | 5-value enum per Step 2 above |
| has_ipeds_finance | BOOLEAN | base.ipeds_finance | unitid | `f.unitid IS NOT NULL` |
| has_eada | BOOLEAN | base.eada | unitid | `e.unitid IS NOT NULL` |
| coverage_tier | VARCHAR | -- | derived | `CASE WHEN both → 'both' WHEN finance → 'finance_only' WHEN athletics → 'athletics_only' END` |
| promoted_at | TIMESTAMP | -- | generated | `datetime.utcnow()` at promote time |

---

## Load Statistics (snapshot 5887248523326294782, 2026-05-01)

| Metric | Value |
|--------|------:|
| Rows | 3,223 |
| Distinct `unitid` | 3,223 (100% unique — CON-AUR-003) |
| `record_id` non-null + unique | 3,223 / 3,223 (CON-AUR-004) |
| Conservation (CON-AUR-001) | 3,223 ∈ [max(2,675, 2,040)=2,675, 2,675+2,040=4,715] ✓ |
| `coverage_tier` distribution | `both` 1,492 (46.3%) / `finance_only` 1,183 (36.7%) / `athletics_only` 548 (17.0%) |
| `has_ipeds_finance` TRUE | 2,675 |
| `has_eada` TRUE | 2,040 |
| `marketing_ratio` non-null | 2,644 / 3,223 (82.0%); 31 zero-instruction edge cases NULL |
| `endowment_per_fte` non-null | 1,998 / 3,223 (62.0%); structural NULL on F3 + small F2 |
| `athletic_spend_per_fte` non-null | 2,040 / 3,223 (63.3%) |
| `athletic_subsidy_ratio` non-null | 2,040 / 3,223; 1,284 of 2,040 are exactly 0 (silver-zone clipping artifact) |
| `athletic_fte_source = 'ipeds_finance'` | 1,492 (all `coverage_tier='both'`) |
| `athletic_fte_source = 'eada_fte_headcount'` | 548 (all `coverage_tier='athletics_only'`) |
| `athletic_fte_source` NULL | 1,183 (all `coverage_tier='finance_only'`) |
| `aura_score` non-null | 2,644 |
| `aura_score` NULL | 579 (548 athletics_only + 31 zero-instruction edge cases) |
| `aura_score_basis` distribution | `three_term` 1,417 / `two_term_finance_only` 579 / `two_term_no_endowment` 75 / `one_term_marketing_only` 573 / NULL 579 |
| `aura_score` band distribution | [1,3] 17.4% / [4,6] 25.7% / [7,10] 56.9% |
| `aura_score` median | 7 (CON-AUR-031 [4,7] band ✓) |
| `aura_score_version = 'v1'` | 3,223 / 3,223 (CON-AUR-012) |
| 14 anchor schools match v1 expected | 14 / 14 (CON-AUR-032 PASS) |
| UNITID overlap with `consumable.career_outcomes` | 89.68% (CON-AUR-021 floor: 90%; 0.32 pp drift, P1 warning) |
| DQ scorecard | 14/14 P0 PASS, 4/5 P1 PASS — `governance/dq-scorecards/consumable-institution-aura-20260501T235038Z.md` |
| Chaos coverage | 10/10 caught — `governance/chaos-reports/consumable-institution-aura-chaos.md` |

Source: `src/gold/institution_aura.py` run + ad-hoc DuckDB queries against the landed Iceberg snapshot.

---

## Cross-References

| Artifact | Path |
|----------|------|
| Spec | `docs/specs/full-pipeline-eada.md` (§6) |
| Transformer | `src/gold/institution_aura.py` (640 lines) |
| Conceptual model | `governance/models/consumable-institution-aura-conceptual.md` |
| Logical model | `governance/models/consumable-institution-aura-logical.md` |
| Base models | `governance/models/base-eada-{conceptual,logical,physical}.md` and `governance/models/base-ipeds-finance-{conceptual,logical,physical}.md` |
| DQ rules | `governance/dq-rules/consumable-institution-aura.json` (19 rules: 14 P0 + 5 P1) |
| DQ scorecard | `governance/dq-scorecards/consumable-institution-aura-20260501T235038Z.md` (14/14 P0 PASS, 4/5 P1 PASS) |
| Data dictionary | `governance/data-dictionaries/consumable-institution-aura.md` |
| Data contract | `governance/data-contracts/consumable-institution-aura.yaml` |
| EDA report | `governance/eda/consumable-institution-aura-eda.md` |
| Chaos report | `governance/chaos-reports/consumable-institution-aura-chaos.md` (10/10 caught) |
| Entity-resolution assessment | `governance/entity-resolution/consumable-institution-aura-er-assessment.md` (N/A — institution-level, no ER required) |
| PII scan | `governance/pii-scans/consumable-institution-aura-pii-scan.md` (N/A — no PII) |
| Temporal assessment | `governance/temporal-models/consumable-institution-aura-temporal-assessment.md` (N/A — single-snapshot) |
| CDE tagging | `governance/cde-tagging/consumable-institution-aura.md` (companion artifact) |
| Lineage | `governance/lineage/full-pipeline-eada-gold-{timestamp}.json` |
| Audit trail | `governance/audit-trail/consumable-institution-aura-dq-execution-20260501T235038Z.md` |

---

## Modeling Decisions (Physical Layer)

1. **`consumable.institution_aura` namespace.** Matches the catalog convention for every Gold/Consumable table.

2. **`DoubleType` for all monetary, per-FTE, ratio, and continuous-score fields.** Matches Base; preserves the BSE-IPF-008/009/010 arithmetic invariants through the consumable layer. CON-AUR-007 (`institutional_support_per_fte / instruction_per_fte ≈ marketing_ratio` within 0.001) is computable in DOUBLE precision (live observation: differences within 1e-6 across the 2,620-row population where all three are non-null).

3. **`IntegerType` for `aura_score`** but `DoubleType` for `aura_score_continuous`. The integer is the consumer-facing score; the continuous value is retained for downstream auditability and for the CON-AUR-013 round-correctness invariant.

4. **`BooleanType` for the two coverage flags.** Native boolean rather than `0`/`1` integer or `'Y'`/`'N'` text — Iceberg supports the type natively, and downstream DuckDB / pandas / pyarrow consumers all handle BooleanType cleanly.

5. **`StringType` (not enum) for the four enum-valued columns** (`athletic_fte_source`, `aura_score_version`, `aura_score_basis`, `coverage_tier`). Iceberg does not have a first-class enum type; the closed domain is enforced by the DQ rules CON-AUR-005/012/033 (P0).

6. **`required=True` on `aura_score_version`** even though `aura_score` itself is NULLABLE. The version stamp is for the *formula*, not for the score-existence — every row carries the version regardless of whether the formula produced a non-NULL score on that row.

7. **`required=False` on the four aura columns** that NULL together (`aura_score`, `aura_score_continuous`, `aura_score_basis`, plus the legacy `aura_score IS NULL ⇔ aura_score_basis IS NULL` invariant per CON-AUR-034 P0).

8. **Column order: identity → finance → athletics → fte-source → aura → coverage → provenance.** Per spec §6 logical reading order. Groups related fields together: the four finance signals, the three athletics signals (with subsidy_ratio adjacent to its peers but tagged "context only"), the FTE-source provenance immediately after the athletics signals it qualifies, then the aura columns as a contiguous block, then the three coverage flags, then the timestamp.

9. **`record_id` prefix `aur` — distinct from upstream Base prefixes (`ipf`, `ead`) and the sibling consumable prefix (`ifp`).** Per spec §6 promote pattern: `compute_grain_id(row, ['unitid'], prefix='aur')`. The `aur` mnemonic is "**a**ura". Cross-zone hash collisions impossible by construction.

10. **No partition spec.** Single-snapshot view; fits trivially in unpartitioned storage. Future multi-snapshot SCD2 extension (out of scope for v1) would partition by snapshot date or version.

11. **No sort spec.** Read patterns are dominated by individual-UNITID lookups (downstream MCP, frontend) and full-table scans (downstream analytics). Neither benefits significantly from a sort key on a 3,223-row table.

12. **`promoted_at` is the only consumable-zone provenance.** The Base load_dates are recoverable via join to `base.ipeds_finance` / `base.eada` if needed; downstream consumers don't typically need them.

13. **v1 P5/P95 bounds (0.1413 / 0.9400) pinned as constants in the transformer.** EDA-finalized 2026-04-30 against the production population. Recomputed on each annual refresh; a drift in the bounds (e.g., P95 bumping above 1.0) would trigger a v2 score with a new `aura_score_version` stamp rather than an in-place rebound.

14. **No imputation flag column.** Consistent with the standing user constraint "no substitution-based degraded states." The `aura_score_basis` column is the *summary* of which inputs were missing, not a substitute for them.

15. **The transformer at `src/gold/institution_aura.py` is 640 lines** — substantially larger than the `consumable.ipeds_finance_profile` transformer (which is a 1:1 shaping promote). The size reflects the v1 composite computation, the FULL OUTER JOIN handling, and the per-row basis assignment with the 5-value enum. The exact reference algorithm and constant pinning (P5/P95 bounds, weight constants, basis enum values) live in the production code; this physical model documents the contract.
