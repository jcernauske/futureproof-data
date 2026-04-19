"""Gold zone transformer for consumable.occupation_profiles.

Reads base.bls_ooh from the Silver zone, computes all derived fields
(GRW score, wage percentiles, market score, confidence tier, etc.),
and promotes to consumable.occupation_profiles via the Brightsmith
idempotent promote pattern.

Grain: soc_code
Record ID: compute_grain_id(row, ['soc_code'], prefix='op')
"""

import datetime
import logging
import math
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

SPEC_NAME = "gold-occupation-profiles-bls-ooh"
GRAIN_FIELDS = ["soc_code"]
GRAIN_PREFIX = "op"

# ---------------------------------------------------------------------------
# GRW score piecewise breakpoints.
# Each tuple is (pct_lower, pct_upper, score_lower, score_upper).
# ---------------------------------------------------------------------------

GRW_BREAKPOINTS: list[tuple[float, float, float, float]] = [
    (-20.0, -10.0, 1.0, 2.5),
    (-10.0, -1.0, 2.5, 4.0),
    (-1.0, 1.0, 4.0, 5.0),
    (1.0, 5.0, 5.0, 6.5),
    (5.0, 10.0, 6.5, 7.5),
    (10.0, 20.0, 7.5, 9.0),
    (20.0, 50.0, 9.0, 10.0),
]


def _round_half_up(x: float) -> int:
    """Round to nearest integer using round-half-up (standard) rounding.

    Python's built-in round() uses banker's rounding (round half to even),
    which differs from DuckDB's ROUND(). This function matches DuckDB:
      round_half_up(2.5) = 3  (Python round(2.5) = 2)
      round_half_up(6.5) = 7  (Python round(6.5) = 6)
    """
    return int(math.floor(x + 0.5))


def compute_grw_score(pct: float | None) -> float | None:
    """Compute GRW score from employment_change_pct using piecewise linear function.

    Maps employment_change_pct to a 1.0-10.0 scale using 8 segments:
      <= -20.0  -> 1.0 (floor)
      -20 to -10 -> 1.0 to 2.5
      -10 to -1  -> 2.5 to 4.0
      -1 to 1    -> 4.0 to 5.0
      1 to 5     -> 5.0 to 6.5
      5 to 10    -> 6.5 to 7.5
      10 to 20   -> 7.5 to 9.0
      >= 20      -> 9.0 to 10.0 (capped at 10.0)

    Returns None if pct is None.
    """
    if pct is None:
        return None

    # Floor: severe decline
    if pct <= -20.0:
        return 1.0

    # Piecewise linear interpolation through the breakpoints
    for pct_lo, pct_hi, score_lo, score_hi in GRW_BREAKPOINTS:
        if pct <= pct_hi:
            fraction = (pct - pct_lo) / (pct_hi - pct_lo)
            return score_lo + fraction * (score_hi - score_lo)

    # Cap: exceptional growth beyond 50%
    return 10.0


def get_gold_schema() -> Schema:
    """Iceberg schema for consumable.occupation_profiles (31 columns)."""
    return Schema(
        # Occupation Profile (Core Identity + Classification)
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "soc_code", StringType(), required=True),
        NestedField(3, "occupation_title", StringType(), required=True),
        NestedField(4, "soc_major_group", StringType(), required=True),
        NestedField(5, "soc_major_group_name", StringType(), required=True),
        NestedField(6, "broad_occupation_flag", BooleanType(), required=True),
        NestedField(7, "catchall_flag", BooleanType(), required=True),
        # Growth Assessment (Carried + Derived)
        NestedField(8, "employment_current", LongType(), required=False),
        NestedField(9, "employment_projected", LongType(), required=False),
        NestedField(10, "employment_change_pct", DoubleType(), required=False),
        NestedField(11, "openings_annual_avg", LongType(), required=False),
        NestedField(12, "growth_category", StringType(), required=True),
        NestedField(13, "grw_score", DoubleType(), required=False),
        NestedField(14, "grw_score_rounded", IntegerType(), required=False),
        # Wage Position (Carried + Derived)
        NestedField(15, "median_annual_wage", DoubleType(), required=False),
        NestedField(16, "wage_available", BooleanType(), required=True),
        NestedField(17, "wage_percentile_overall", DoubleType(), required=False),
        NestedField(18, "wage_percentile_education_tier", DoubleType(), required=False),
        NestedField(19, "wage_tier", StringType(), required=False),
        # Entry Requirements (Carried)
        NestedField(20, "education_code", IntegerType(), required=False),
        NestedField(21, "education_level_name", StringType(), required=False),
        NestedField(22, "work_experience_code", IntegerType(), required=False),
        NestedField(23, "training_code", IntegerType(), required=False),
        # Market Opportunity (Derived)
        NestedField(24, "market_score", DoubleType(), required=False),
        NestedField(25, "market_score_rounded", IntegerType(), required=False),
        # Data Quality Context (Derived)
        NestedField(26, "confidence_tier", StringType(), required=True),
        NestedField(27, "data_completeness", DoubleType(), required=True),
        # FutureProof Stat Mapping (Static)
        NestedField(28, "backs_stats", StringType(), required=True),
        NestedField(29, "backs_bosses", StringType(), required=True),
        # Pipeline Metadata
        NestedField(30, "source_load_date", DateType(), required=True),
        NestedField(31, "promoted_at", TimestampType(), required=True),
    )


# ---------------------------------------------------------------------------
# SQL for all Gold derivations.  Executed in DuckDB over the Silver Arrow
# table registered as ``silver``.
#
# CRITICAL: Wage percentiles are computed on a filtered subset that EXCLUDES
# null wages, then LEFT JOINed back.  If nulls participate in PERCENT_RANK,
# DuckDB places them at ~0.185, corrupting all positions.
# ---------------------------------------------------------------------------

GOLD_SQL = """
WITH
-- Step 1: Select and carry forward Silver fields (dropping fields not needed in Gold)
base AS (
    SELECT
        soc_code,
        occupation_title,
        soc_major_group,
        soc_major_group_name,
        broad_occupation_flag,
        catchall_flag,
        employment_current,
        employment_projected,
        employment_change_pct,
        openings_annual_avg,
        growth_category,
        median_annual_wage,
        wage_available,
        education_code,
        education_level_name,
        work_experience_code,
        training_code,
        source_load_date
    FROM silver
),

-- Step 2: Compute wage percentile overall (exclude nulls from ranking)
wage_ranked_overall AS (
    SELECT
        soc_code,
        PERCENT_RANK() OVER (ORDER BY median_annual_wage) AS wage_percentile_overall
    FROM base
    WHERE median_annual_wage IS NOT NULL
),

-- Step 3: Compute wage percentile within education tier (exclude nulls from ranking)
wage_ranked_edu AS (
    SELECT
        soc_code,
        PERCENT_RANK() OVER (
            PARTITION BY education_code
            ORDER BY median_annual_wage
        ) AS wage_percentile_education_tier
    FROM base
    WHERE median_annual_wage IS NOT NULL
),

-- Step 4: Compute openings_score via PERCENT_RANK mapped to 1-10
-- CRITICAL: Exclude null openings from ranking (same pattern as wage percentiles).
-- If nulls participate, DuckDB sorts them last, inflating their score to ~10.0.
openings_ranked AS (
    SELECT
        soc_code,
        1.0 + 9.0 * PERCENT_RANK() OVER (ORDER BY openings_annual_avg) AS openings_score
    FROM base
    WHERE openings_annual_avg IS NOT NULL
),

-- Step 5: Join everything together
joined AS (
    SELECT
        b.*,
        wro.wage_percentile_overall,
        wre.wage_percentile_education_tier,
        o.openings_score
    FROM base b
    LEFT JOIN wage_ranked_overall wro ON b.soc_code = wro.soc_code
    LEFT JOIN wage_ranked_edu wre ON b.soc_code = wre.soc_code
    LEFT JOIN openings_ranked o ON b.soc_code = o.soc_code
)

SELECT
    j.soc_code,
    j.occupation_title,
    j.soc_major_group,
    j.soc_major_group_name,
    j.broad_occupation_flag,
    j.catchall_flag,
    j.employment_current,
    j.employment_projected,
    j.employment_change_pct,
    j.openings_annual_avg,
    j.growth_category,
    j.median_annual_wage,
    j.wage_available,
    j.wage_percentile_overall,
    j.wage_percentile_education_tier,
    -- Wage tier: bucket wage_percentile_overall into 5 tiers
    CASE
        WHEN j.wage_percentile_overall IS NULL THEN NULL
        WHEN j.wage_percentile_overall < 0.25 THEN 'low'
        WHEN j.wage_percentile_overall < 0.50 THEN 'below_average'
        WHEN j.wage_percentile_overall < 0.75 THEN 'above_average'
        WHEN j.wage_percentile_overall < 0.90 THEN 'high'
        ELSE 'very_high'
    END AS wage_tier,
    j.education_code,
    j.education_level_name,
    j.work_experience_code,
    j.training_code,
    j.openings_score,
    -- Confidence tier: wage_available check FIRST (priority over broad/catchall)
    CASE
        WHEN j.wage_available = FALSE THEN 'low'
        WHEN j.broad_occupation_flag = TRUE OR j.catchall_flag = TRUE THEN 'medium'
        ELSE 'high'
    END AS confidence_tier,
    -- Data completeness: count of non-null core fields / 4
    (
        CASE WHEN j.median_annual_wage IS NOT NULL THEN 1 ELSE 0 END
      + CASE WHEN j.employment_current IS NOT NULL THEN 1 ELSE 0 END
      + CASE WHEN j.employment_change_pct IS NOT NULL THEN 1 ELSE 0 END
      + CASE WHEN j.openings_annual_avg IS NOT NULL THEN 1 ELSE 0 END
    ) / 4.0 AS data_completeness,
    j.source_load_date
FROM joined j
ORDER BY j.soc_code ASC
"""


def derive_gold_rows(silver_rows: list[dict]) -> list[dict]:
    """Run Gold derivations over Silver rows using DuckDB.

    Computes wage percentiles (null-safe), wage tier, confidence tier,
    data completeness, and openings_score via SQL.  Then computes
    GRW score and market score in Python for the piecewise function.

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

        # Compute GRW score via piecewise linear function (Python, not SQL)
        grw = compute_grw_score(row.get("employment_change_pct"))
        row["grw_score"] = grw
        row["grw_score_rounded"] = _round_half_up(grw) if grw is not None else None

        # Compute market score: 0.6 * grw_score + 0.4 * openings_score
        # Guard on raw openings_annual_avg (not openings_score, which may be
        # non-null even when the underlying data is null in edge cases).
        openings_score = row.pop("openings_score", None)
        has_openings = row.get("openings_annual_avg") is not None
        if grw is not None and has_openings and openings_score is not None:
            market = 0.6 * grw + 0.4 * openings_score
            row["market_score"] = market
            row["market_score_rounded"] = _round_half_up(market)
        else:
            row["market_score"] = None
            row["market_score_rounded"] = None

        # Static FutureProof stat mapping fields
        row["backs_stats"] = "ERN,GRW"
        row["backs_bosses"] = "Market,Ceiling"

        gold_rows.append(row)

    return gold_rows


def add_record_ids(gold_rows: list[dict], promoted_at: datetime.datetime) -> list[dict]:
    """Add record_id and promoted_at to each Gold row.

    The grain hash uses ['soc_code'] per spec with prefix 'op'.
    """
    for row in gold_rows:
        row["record_id"] = compute_grain_id(row, GRAIN_FIELDS, prefix=GRAIN_PREFIX)
        row["promoted_at"] = promoted_at
    return gold_rows


def transform(
    project_dir: str | Path | None = None,
) -> dict:
    """Run the Gold zone transformation.

    Reads base.bls_ooh from Silver, computes all Gold derivations,
    and promotes to consumable.occupation_profiles via idempotent
    promote pattern.

    Returns:
        {"rows_read": N, "promoted": M, "skipped": S, ...}
    """
    project_dir = Path(project_dir or ".").resolve()

    silver_warehouse = project_dir / "data" / "silver" / "iceberg_warehouse"
    catalog_path = project_dir / "data" / "catalog" / "catalog.db"
    gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"

    # Read from Silver
    logger.info("Reading from base.bls_ooh...")
    silver_catalog = get_catalog(silver_warehouse, catalog_path)
    silver_table = silver_catalog.load_table("base.bls_ooh")

    arrow_table = silver_table.scan().to_arrow()  # noqa: F841  (DuckDB auto-registers by local name)
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
    logger.info("Promoting to consumable.occupation_profiles...")
    gold_catalog = get_catalog(gold_warehouse, catalog_path)
    gold_table = get_or_create_table(
        gold_catalog, "consumable", "occupation_profiles", get_gold_schema()
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
