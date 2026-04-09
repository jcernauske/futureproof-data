"""Gold zone transformer for consumable.career_outcomes.

Reads base.college_scorecard from the Silver zone, computes all derived fields
(percentile bands, debt-to-earnings, earnings growth, confidence tiers, etc.),
and promotes to consumable.career_outcomes via the Brightsmith idempotent
promote pattern.

Grain: unitid x cipcode x credential_level
Record ID: compute_grain_id(row, ['unitid', 'cipcode', 'credlev'], prefix='co')
"""

import datetime
import logging
from pathlib import Path

import duckdb
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

from brightsmith.infra.grain import compute_grain_id
from brightsmith.infra.iceberg_setup import get_catalog, get_or_create_table
from brightsmith.infra.promote import promote

logger = logging.getLogger(__name__)

SPEC_NAME = "gold-career-outcomes-college-scorecard"
GRAIN_FIELDS = ["unitid", "cipcode", "credlev"]
GRAIN_PREFIX = "co"


def get_gold_schema() -> Schema:
    """Iceberg schema for consumable.career_outcomes (30 columns)."""
    return Schema(
        # Core Identity
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "unitid", LongType(), required=True),
        NestedField(3, "institution_name", StringType(), required=True),
        NestedField(4, "institution_control", StringType(), required=False),
        NestedField(5, "cipcode", StringType(), required=True),
        NestedField(6, "program_name", StringType(), required=True),
        NestedField(7, "cip_family", StringType(), required=True),
        NestedField(8, "cip_family_name", StringType(), required=True),
        NestedField(9, "credential_level", IntegerType(), required=True),
        # Core Outcome Fields
        NestedField(10, "earnings_1yr_median", DoubleType(), required=False),
        NestedField(11, "earnings_2yr_median", DoubleType(), required=False),
        NestedField(12, "debt_median", DoubleType(), required=False),
        NestedField(13, "completions_count", LongType(), required=False),
        NestedField(14, "small_cohort_flag", BooleanType(), required=True),
        # Percentile Bands
        NestedField(15, "earnings_1yr_p25", DoubleType(), required=False),
        NestedField(16, "earnings_1yr_p75", DoubleType(), required=False),
        NestedField(17, "earnings_2yr_p25", DoubleType(), required=False),
        NestedField(18, "earnings_2yr_p75", DoubleType(), required=False),
        NestedField(19, "debt_p25", DoubleType(), required=False),
        NestedField(20, "debt_p75", DoubleType(), required=False),
        # Financial Assessment
        NestedField(21, "debt_to_earnings_annual", DoubleType(), required=False),
        NestedField(22, "debt_to_earnings_tier", StringType(), required=False),
        NestedField(23, "earnings_growth_rate", DoubleType(), required=False),
        NestedField(24, "cip_family_earnings_rank", DoubleType(), required=False),
        NestedField(25, "program_value_index", DoubleType(), required=False),
        # Data Confidence
        NestedField(26, "confidence_tier", StringType(), required=True),
        NestedField(27, "has_earnings", BooleanType(), required=True),
        NestedField(28, "has_debt", BooleanType(), required=True),
        NestedField(29, "outcome_completeness", DoubleType(), required=True),
        # Metadata
        NestedField(30, "source_load_date", DateType(), required=True),
        NestedField(31, "promoted_at", TimestampType(), required=True),
    )


# ---------------------------------------------------------------------------
# SQL for all Gold derivations.  Executed in DuckDB over the Silver Arrow
# table registered as ``silver``.
# ---------------------------------------------------------------------------

GOLD_SQL = """
WITH
-- Step 1: Carry forward Silver fields, rename completions_count_1 -> completions_count
base AS (
    SELECT
        unitid,
        institution_name,
        institution_control,
        cipcode,
        program_name,
        cip_family,
        cip_family_name,
        credential_level,
        earnings_1yr_median,
        earnings_2yr_median,
        debt_median,
        completions_count_1 AS completions_count,
        small_cohort_flag,
        source_load_date
    FROM silver
),

-- Step 2: Count non-null values per CIP family for minimum-sample guard
cip_counts AS (
    SELECT
        cip_family,
        COUNT(earnings_1yr_median) AS nn_1yr,
        COUNT(earnings_2yr_median) AS nn_2yr,
        COUNT(debt_median)         AS nn_debt
    FROM base
    GROUP BY cip_family
),

-- Step 3: Compute percentile bands per CIP family (only for families with >= 3 values)
cip_bands AS (
    SELECT
        cip_family,
        CASE WHEN nn_1yr >= 3
            THEN PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY earnings_1yr_median)
            ELSE NULL END AS earnings_1yr_p25,
        CASE WHEN nn_1yr >= 3
            THEN PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY earnings_1yr_median)
            ELSE NULL END AS earnings_1yr_p75,
        CASE WHEN nn_2yr >= 3
            THEN PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY earnings_2yr_median)
            ELSE NULL END AS earnings_2yr_p25,
        CASE WHEN nn_2yr >= 3
            THEN PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY earnings_2yr_median)
            ELSE NULL END AS earnings_2yr_p75,
        CASE WHEN nn_debt >= 3
            THEN PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY debt_median)
            ELSE NULL END AS debt_p25,
        CASE WHEN nn_debt >= 3
            THEN PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY debt_median)
            ELSE NULL END AS debt_p75
    FROM base
    JOIN cip_counts USING (cip_family)
    GROUP BY cip_family, nn_1yr, nn_2yr, nn_debt
),

-- Step 4: Compute PERCENT_RANK for earnings within CIP family
-- Only rows with non-null earnings_1yr_median participate in ranking
ranked AS (
    SELECT
        unitid, cipcode, credential_level,
        PERCENT_RANK() OVER (
            PARTITION BY cip_family
            ORDER BY earnings_1yr_median
        ) AS cip_family_earnings_rank
    FROM base
    WHERE earnings_1yr_median IS NOT NULL
),

-- Step 5: Join everything together and compute remaining derived fields
joined AS (
    SELECT
        b.*,
        cb.earnings_1yr_p25,
        cb.earnings_1yr_p75,
        cb.earnings_2yr_p25,
        cb.earnings_2yr_p75,
        cb.debt_p25,
        cb.debt_p75,
        -- Debt-to-earnings ratio (null-safe)
        CASE WHEN b.debt_median IS NOT NULL AND b.earnings_1yr_median IS NOT NULL
            THEN b.debt_median / b.earnings_1yr_median
            ELSE NULL END AS debt_to_earnings_annual,
        -- Earnings growth rate (null-safe)
        CASE WHEN b.earnings_1yr_median IS NOT NULL AND b.earnings_2yr_median IS NOT NULL
            THEN (b.earnings_2yr_median - b.earnings_1yr_median) / b.earnings_1yr_median
            ELSE NULL END AS earnings_growth_rate,
        -- CIP family earnings rank (null for rows without earnings)
        r.cip_family_earnings_rank,
        -- Program value index (null-safe)
        CASE WHEN b.earnings_1yr_median IS NOT NULL AND b.debt_median IS NOT NULL
            THEN b.earnings_1yr_median / b.debt_median
            ELSE NULL END AS program_value_index,
        -- Convenience flags
        (b.earnings_1yr_median IS NOT NULL OR b.earnings_2yr_median IS NOT NULL) AS has_earnings,
        (b.debt_median IS NOT NULL) AS has_debt,
        -- Outcome completeness
        ROUND(
            (CASE WHEN b.earnings_1yr_median IS NOT NULL THEN 1 ELSE 0 END
           + CASE WHEN b.earnings_2yr_median IS NOT NULL THEN 1 ELSE 0 END
           + CASE WHEN b.debt_median IS NOT NULL THEN 1 ELSE 0 END)
           / 3.0,
            2
        ) AS outcome_completeness
    FROM base b
    LEFT JOIN cip_bands cb ON b.cip_family = cb.cip_family
    LEFT JOIN ranked r
        ON b.unitid = r.unitid
        AND b.cipcode = r.cipcode
        AND b.credential_level = r.credential_level
)

SELECT
    j.*,
    -- Debt-to-earnings tier
    CASE
        WHEN j.debt_to_earnings_annual IS NULL THEN NULL
        WHEN j.debt_to_earnings_annual < 0.75 THEN 'Low'
        WHEN j.debt_to_earnings_annual < 1.5 THEN 'Moderate'
        WHEN j.debt_to_earnings_annual < 2.5 THEN 'High'
        ELSE 'Very High'
    END AS debt_to_earnings_tier,
    -- Confidence tier
    CASE
        WHEN j.small_cohort_flag = FALSE AND j.has_earnings = TRUE AND j.has_debt = TRUE
            THEN 'high'
        WHEN j.small_cohort_flag = FALSE AND (j.has_earnings = TRUE OR j.has_debt = TRUE)
            THEN 'medium'
        WHEN j.small_cohort_flag = TRUE AND (j.has_earnings = TRUE OR j.has_debt = TRUE)
            THEN 'low'
        ELSE 'insufficient'
    END AS confidence_tier
FROM joined j
ORDER BY j.cip_family ASC, j.unitid ASC, j.cipcode ASC, j.credential_level ASC
"""


def _snap_outcome_completeness(val: float) -> float:
    """Snap outcome_completeness to the exact value set {0.0, 0.33, 0.67, 1.0}.

    ROUND(n/3, 2) in DuckDB produces 0.0, 0.33, 0.67, 1.0 but floating-point
    rounding across engines can drift.  This snaps to the nearest valid value.
    """
    valid = [0.0, 0.33, 0.67, 1.0]
    return min(valid, key=lambda v: abs(v - val))


def derive_gold_rows(silver_rows: list[dict]) -> list[dict]:
    """Run Gold derivations over Silver rows using DuckDB.

    Returns a list of dicts ready for grain-id computation and promotion.
    """
    import pyarrow as pa

    if not silver_rows:
        return []

    # Build Arrow table from Silver rows for DuckDB
    arrow_table = pa.Table.from_pylist(silver_rows)

    con = duckdb.connect()
    con.register("silver", arrow_table)
    rel = con.sql(GOLD_SQL)
    col_names = [desc[0] for desc in rel.description]
    rows = rel.fetchall()
    con.close()

    gold_rows = []
    for row_tuple in rows:
        row = dict(zip(col_names, row_tuple))
        # Snap outcome_completeness to exact value set
        row["outcome_completeness"] = _snap_outcome_completeness(
            row["outcome_completeness"]
        )
        gold_rows.append(row)

    return gold_rows


def add_record_ids(gold_rows: list[dict], promoted_at: datetime.datetime) -> list[dict]:
    """Add record_id and promoted_at to each Gold row.

    The grain hash uses ['unitid', 'cipcode', 'credlev'] per spec.
    The row dict has 'credential_level', so we build a grain dict with 'credlev'.
    """
    for row in gold_rows:
        # Build grain dict with spec-defined key names
        grain_row = {
            "unitid": row["unitid"],
            "cipcode": row["cipcode"],
            "credlev": row["credential_level"],
        }
        row["record_id"] = compute_grain_id(grain_row, GRAIN_FIELDS, prefix=GRAIN_PREFIX)
        row["promoted_at"] = promoted_at
    return gold_rows


def transform(
    project_dir: str | Path | None = None,
) -> dict:
    """Run the Gold zone transformation.

    Reads base.college_scorecard from Silver, computes all Gold derivations,
    and promotes to consumable.career_outcomes via idempotent promote pattern.

    Returns:
        {"rows_read": N, "promoted": M, "skipped": S, ...}
    """
    project_dir = Path(project_dir or ".").resolve()

    silver_warehouse = project_dir / "data" / "silver" / "iceberg_warehouse"
    catalog_path = project_dir / "data" / "catalog" / "catalog.db"
    gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"

    # Read from Silver
    logger.info("Reading from base.college_scorecard...")
    silver_catalog = get_catalog(silver_warehouse, catalog_path)
    silver_table = silver_catalog.load_table("base.college_scorecard")

    # Read via PyIceberg scan -> Arrow (same pattern as Silver transformer)
    arrow_table = silver_table.scan().to_arrow()
    con = duckdb.connect()
    result = con.sql("SELECT * FROM arrow_table").fetchall()
    columns = [field.name for field in silver_table.schema().fields]
    silver_rows = [dict(zip(columns, row)) for row in result]
    con.close()
    logger.info("Read %d rows from Silver", len(silver_rows))

    # Derive Gold fields
    logger.info("Computing Gold derivations...")
    gold_rows = derive_gold_rows(silver_rows)
    logger.info("Derived %d Gold rows", len(gold_rows))

    # Add record_id and promoted_at
    promoted_at = datetime.datetime.now(tz=datetime.timezone.utc)
    add_record_ids(gold_rows, promoted_at)

    # Promote to Gold
    logger.info("Promoting to consumable.career_outcomes...")
    gold_catalog = get_catalog(gold_warehouse, catalog_path)
    gold_table = get_or_create_table(
        gold_catalog, "consumable", "career_outcomes", get_gold_schema()
    )
    result = promote(
        gold_table,
        gold_rows,
        id_field="record_id",
        spec_name=SPEC_NAME,
        agent_name="@primary-agent",
    )

    logger.info(
        "Promote complete: %d promoted, %d skipped",
        result["promoted"],
        result["skipped"],
    )

    return {
        "rows_read": len(silver_rows),
        "rows_derived": len(gold_rows),
        "promoted": result["promoted"],
        "skipped_dedup": result["skipped"],
        "snapshot_id": result.get("snapshot_id"),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    result = transform()
    print(f"Gold transform complete: {result}")
