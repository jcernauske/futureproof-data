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
    """Iceberg schema for consumable.occupation_profiles (35 columns).

    OEWS wage-distribution columns (IDs 32-35) added by spec
    ingest-bls-oews-wage-percentiles, sourced from base.bls_oews via a
    LEFT JOIN on soc_code. Existing schema unchanged.
    """
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
        # OEWS Wage Distribution (LEFT JOIN base.bls_oews on soc_code)
        # Spec: docs/specs/ingest-bls-oews-wage-percentiles.md §Zone 3.
        # All four columns are CDE-P0 (drives CareerCard "typical range" and
        # FinancesCard salary row) but nullable — a small number of OEWS-
        # suppressed SOCs and the lone OOH-only SOC (45-3031) yield nulls.
        NestedField(32, "wage_p10", DoubleType(), required=False),
        NestedField(33, "wage_p25", DoubleType(), required=False),
        NestedField(34, "wage_p75", DoubleType(), required=False),
        NestedField(35, "wage_p90", DoubleType(), required=False),
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
-- Step 1: Select and carry forward Silver fields (dropping fields not needed in Gold).
-- LEFT JOIN base.bls_oews on soc_code to surface OEWS wage percentiles
-- (spec ingest-bls-oews-wage-percentiles §Zone 3). The OEWS table is
-- registered in DuckDB as ``silver_oews`` (see derive_gold_rows()).
-- All four wage_p* columns NULL-propagate when the SOC has no OEWS row
-- (e.g., OOH-only 45-3031 Fishing/Hunting Workers, or fully-suppressed
-- entertainment occupations).
base AS (
    SELECT
        s.soc_code,
        s.occupation_title,
        s.soc_major_group,
        s.soc_major_group_name,
        s.broad_occupation_flag,
        s.catchall_flag,
        s.employment_current,
        s.employment_projected,
        s.employment_change_pct,
        s.openings_annual_avg,
        s.growth_category,
        s.median_annual_wage,
        s.wage_available,
        s.education_code,
        s.education_level_name,
        s.work_experience_code,
        s.training_code,
        s.source_load_date,
        -- OEWS wage percentiles (LEFT JOIN; null when SOC has no OEWS row)
        oews.wage_annual_p10 AS wage_p10,
        oews.wage_annual_p25 AS wage_p25,
        oews.wage_annual_p75 AS wage_p75,
        oews.wage_annual_p90 AS wage_p90
    FROM silver s
    LEFT JOIN silver_oews oews ON s.soc_code = oews.soc_code
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
    j.source_load_date,
    -- OEWS wage distribution (carried through the joined CTE from base).
    j.wage_p10,
    j.wage_p25,
    j.wage_p75,
    j.wage_p90
FROM joined j
ORDER BY j.soc_code ASC
"""


def derive_gold_rows(
    silver_rows: list[dict],
    oews_rows: list[dict] | None = None,
) -> list[dict]:
    """Run Gold derivations over Silver rows using DuckDB.

    Computes wage percentiles (null-safe), wage tier, confidence tier,
    data completeness, and openings_score via SQL. Then computes
    GRW score and market score in Python for the piecewise function.

    Args:
        silver_rows: Rows from base.bls_ooh (the BLS OOH Silver table).
        oews_rows: Optional rows from base.bls_oews (BLS OEWS Silver, spec
            ingest-bls-oews-wage-percentiles). When None or empty, the four
            wage_p* columns are emitted as null for every row (graceful
            degradation when the OEWS dispatch hasn't run yet). Required
            keys when supplied: soc_code, wage_annual_p10/p25/p75/p90.

    Returns a list of dicts ready for grain-id computation and promotion.
    """
    import pyarrow as pa

    if not silver_rows:
        return []

    # Build Arrow table from Silver rows for DuckDB
    arrow_table = pa.Table.from_pylist(silver_rows)

    # Build OEWS Arrow table. If no rows supplied (or empty list), register
    # an empty table with the expected schema so the LEFT JOIN matches zero
    # rows and emits null for all four wage_p* columns.
    if oews_rows:
        oews_arrow = pa.Table.from_pylist([
            {
                "soc_code": r["soc_code"],
                "wage_annual_p10": r.get("wage_annual_p10"),
                "wage_annual_p25": r.get("wage_annual_p25"),
                "wage_annual_p75": r.get("wage_annual_p75"),
                "wage_annual_p90": r.get("wage_annual_p90"),
            }
            for r in oews_rows
        ])
    else:
        oews_arrow = pa.table({
            "soc_code": pa.array([], type=pa.string()),
            "wage_annual_p10": pa.array([], type=pa.float64()),
            "wage_annual_p25": pa.array([], type=pa.float64()),
            "wage_annual_p75": pa.array([], type=pa.float64()),
            "wage_annual_p90": pa.array([], type=pa.float64()),
        })

    con = duckdb.connect()
    con.register("silver", arrow_table)
    con.register("silver_oews", oews_arrow)
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


def _overwrite_occupation_profiles(table, records: list[dict]) -> int:
    """Overwrite consumable.occupation_profiles with new data.

    Used for backfills where the grain is unchanged but column values
    change — specifically the OEWS-enrichment dispatch (spec
    ingest-bls-oews-wage-percentiles) that adds wage_p10/25/75/90 to
    existing soc_code rows. Mirrors the helper in futureproof_engine.
    """
    import pyarrow as pa
    from pyiceberg.io.pyarrow import schema_to_pyarrow
    from pyiceberg.types import DateType

    iceberg_schema = table.schema()
    date_fields = {
        f.name for f in iceberg_schema.fields if isinstance(f.field_type, DateType)
    }
    columns: dict = {}
    for field in iceberg_schema.fields:
        values = [r.get(field.name) for r in records]
        if field.name in date_fields:
            values = [
                datetime.date.fromisoformat(v) if isinstance(v, str) else v
                for v in values
            ]
        columns[field.name] = values

    arrow_schema = schema_to_pyarrow(iceberg_schema)
    arrow_table = pa.table(columns, schema=arrow_schema)
    table.overwrite(arrow_table)
    table.refresh()
    return list(table.snapshots())[-1].snapshot_id


def transform(
    project_dir: str | Path | None = None,
    overwrite: bool = False,
) -> dict:
    """Run the Gold zone transformation.

    Reads base.bls_ooh from Silver, computes all Gold derivations,
    and promotes to consumable.occupation_profiles.

    Args:
        project_dir: Root project directory.
        overwrite: If True, overwrite existing data instead of dedup-append.
            Use for backfills where column values change but the grain is
            the same — e.g., the OEWS-enrichment dispatch (spec
            ingest-bls-oews-wage-percentiles) that adds wage_p10/25/75/90
            to existing soc_code rows.

    Returns:
        {"rows_read": N, "promoted": M, "skipped_dedup": S, ...}
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

    # Read OEWS Silver (optional — graceful degradation when the OEWS
    # dispatch hasn't been promoted yet). Spec:
    # docs/specs/ingest-bls-oews-wage-percentiles.md §Zone 3.
    oews_rows: list[dict] = []
    try:
        oews_table = silver_catalog.load_table("base.bls_oews")
        oews_arrow = oews_table.scan().to_arrow()  # noqa: F841
        con = duckdb.connect()
        oews_result = con.sql("SELECT * FROM oews_arrow").fetchall()
        oews_columns = [field.name for field in oews_table.schema().fields]
        oews_rows = [dict(zip(oews_columns, row)) for row in oews_result]
        con.close()
        logger.info("Read %d rows from base.bls_oews", len(oews_rows))
    except Exception as exc:
        logger.info(
            "base.bls_oews not available (%s) — wage_p* columns will be null",
            exc,
        )

    # Derive Gold fields
    logger.info("Computing Gold derivations...")
    gold_rows = derive_gold_rows(silver_rows, oews_rows=oews_rows)
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

    # Schema evolution: add new OEWS wage_p* columns if the table was
    # created before the spec ingest-bls-oews-wage-percentiles dispatch.
    # Mirrors the futureproof_engine pattern. Idempotent — no-op when the
    # new fields already exist.
    existing_field_names = {f.name for f in gold_table.schema().fields}
    target_schema = get_gold_schema()
    new_fields = [
        f for f in target_schema.fields if f.name not in existing_field_names
    ]
    if new_fields:
        with gold_table.update_schema() as update:
            for field in new_fields:
                update.add_column(
                    field.name, field.field_type, doc=None, required=field.required
                )
        logger.info(
            "Evolved occupation_profiles schema: added %d fields (%s)",
            len(new_fields),
            [f.name for f in new_fields],
        )
        gold_table.refresh()

    if overwrite:
        logger.info("Overwrite mode: replacing all data in occupation_profiles")
        snapshot_id = _overwrite_occupation_profiles(gold_table, gold_rows)
        result = {"promoted": len(gold_rows), "skipped": 0, "snapshot_id": snapshot_id}
    else:
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
