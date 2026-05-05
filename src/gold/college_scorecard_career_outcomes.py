"""Gold zone transformer for consumable.career_outcomes.

Reads base.college_scorecard from the Silver zone, computes all derived fields
(percentile bands, debt-to-earnings, earnings growth, confidence tiers, etc.),
and promotes to consumable.career_outcomes via the Brightsmith idempotent
promote pattern.

As of 2026-04-16 (spec raw-ingest-college-scorecard-institution §Zone 3) the
transformer also LEFT JOINs `base.college_scorecard_institution` on ``unitid``
to enrich each row with 6 net-new institution-level cost columns
(net_price_annual, cost_of_attendance_annual, net_price_4yr, tuition_in_state,
tuition_out_of_state, room_board_on_campus) and re-sources ``institution_control``
(id=4) from the institution file (replaces the prior 100%-null carry-forward
from the field-of-study file). Row count is preserved exactly.

Grain: unitid x cipcode x credential_level
Record ID: compute_grain_id(row, ['unitid', 'cipcode', 'credlev'], prefix='co')
"""

import datetime
import logging
from pathlib import Path

import duckdb
import pyarrow as pa
from pyiceberg.io.pyarrow import schema_to_pyarrow
from pyiceberg.schema import Schema
from pyiceberg.table import Table
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

# Columns added by the 2026-04-16 CSI enrichment (spec
# raw-ingest-college-scorecard-institution §Zone 3). Exposed as a module-level
# constant so tests and the promote runner can assert presence + types without
# re-hardcoding the list.
CSI_ENRICHMENT_COLUMNS: tuple[str, ...] = (
    "net_price_annual",
    "cost_of_attendance_annual",
    "net_price_4yr",
    "tuition_in_state",
    "tuition_out_of_state",
    "room_board_on_campus",
)


def get_gold_schema() -> Schema:
    """Iceberg schema for consumable.career_outcomes.

    Columns 1–31 are the original career-outcomes physical model. Columns 32–37
    are the 2026-04-16 CSI enrichment (spec raw-ingest-college-scorecard-
    institution §Zone 3). Field ID 4 (``institution_control``) is kept in place
    but is re-sourced from the institution file; nullability is unchanged.
    """
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
        # CSI Enrichment (added 2026-04-16; all nullable; sourced via LEFT JOIN
        # on unitid against base.college_scorecard_institution)
        NestedField(32, "net_price_annual", DoubleType(), required=False),
        NestedField(33, "cost_of_attendance_annual", DoubleType(), required=False),
        NestedField(34, "net_price_4yr", DoubleType(), required=False),
        NestedField(35, "tuition_in_state", DoubleType(), required=False),
        NestedField(36, "tuition_out_of_state", DoubleType(), required=False),
        NestedField(37, "room_board_on_campus", DoubleType(), required=False),
        # Cost-based ROI provenance (spec why-are-we-still-jaunty-curry).
        # roi_cost_basis records which numerator was used to compute
        # debt_to_earnings_annual on this row:
        #   'cost_of_attendance' — net_price_annual × 4 (preferred; ~95% of rows)
        #   'debt_median'        — debt_median fallback when net_price is null
        #   'none'               — neither input available (DTE is null)
        NestedField(38, "roi_cost_basis", StringType(), required=False),
        NestedField(39, "state_abbr", StringType(), required=False),
        # ROI Net Lifetime Value (spec roi-net-lifetime-value, 2026-05-04).
        # 15-year cumulative earnings + payback multiplier + provenance.
        # Formula: lifetime_earnings_15yr = earnings_1yr_median × 18.5989
        #          roi_raw_multiplier = lifetime_earnings_15yr
        #                               / COALESCE(coa × 4, net_price_4yr)
        # Per Decision #11, the multiplier is the in-state baseline; the
        # backend's stat_engine._derive_roi applies the residency-aware
        # override at runtime.
        NestedField(40, "lifetime_earnings_15yr", DoubleType(), required=False),
        NestedField(41, "roi_raw_multiplier", DoubleType(), required=False),
        NestedField(42, "roi_multiplier_basis", StringType(), required=False),
    )


# ---------------------------------------------------------------------------
# SQL for all Gold derivations.  Executed in DuckDB over the Silver Arrow
# table registered as ``silver``.
# ---------------------------------------------------------------------------

GOLD_SQL = """
WITH
-- Step 1: Carry forward Silver fields, rename completions_count_1 -> completions_count.
-- ``institution_control`` is NOT carried forward here because it is re-sourced
-- from the institution file via the ``institution`` CTE below (spec
-- raw-ingest-college-scorecard-institution §Zone 3). Pre-enrichment, this
-- field was 100% null in the field-of-study silver source.
base AS (
    SELECT
        unitid,
        institution_name,
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

-- Step 3b: Institution-level cost enrichment (spec raw-ingest-college-
-- scorecard-institution §Zone 3). One row per UNITID. The final LEFT JOIN on
-- this CTE does not drop rows in ``base``; unmatched UNITIDs get NULL for all
-- 7 enrichment columns. institution_control here REPLACES the prior field-of-
-- study value (which was 100% null).
institution AS (
    SELECT
        unitid,
        state_abbr,
        net_price_annual,
        cost_of_attendance_annual,
        net_price_4yr,
        institution_control,
        tuition_in_state,
        tuition_out_of_state,
        room_board_on_campus
    FROM institution_silver
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
        -- CSI enrichment (LEFT JOIN on unitid; columns carried forward).
        i.institution_control,
        i.state_abbr,
        i.net_price_annual,
        i.cost_of_attendance_annual,
        i.net_price_4yr,
        i.tuition_in_state,
        i.tuition_out_of_state,
        i.room_board_on_campus,
        cb.earnings_1yr_p25,
        cb.earnings_1yr_p75,
        cb.earnings_2yr_p25,
        cb.earnings_2yr_p75,
        cb.debt_p25,
        cb.debt_p75,
        -- Cost-based DTE: numerator is 4-year net price of attendance when
        -- institution-level data is available, else falls back to
        -- debt_median (the pre-2026-04 behaviour). This decouples stat_roi
        -- from financing: ROI now reflects program economic value, not how
        -- much was borrowed. The Student Loans Boss is the place where
        -- loan_pct still matters; that math lives in the backend stat_engine
        -- so the per-request knob can vary without re-promoting Gold.
        -- Spec: docs/specs (in progress) + plan at
        -- ~/.claude/plans/why-are-we-still-jaunty-curry.md
        CASE
            WHEN b.earnings_1yr_median IS NULL THEN NULL
            WHEN i.net_price_annual IS NOT NULL
                THEN (i.net_price_annual * 4.0) / b.earnings_1yr_median
            WHEN b.debt_median IS NOT NULL
                THEN b.debt_median / b.earnings_1yr_median
            ELSE NULL
        END AS debt_to_earnings_annual,
        CASE
            WHEN b.earnings_1yr_median IS NULL THEN 'none'
            WHEN i.net_price_annual IS NOT NULL THEN 'cost_of_attendance'
            WHEN b.debt_median IS NOT NULL THEN 'debt_median'
            ELSE 'none'
        END AS roi_cost_basis,
        -- 15-year cumulative earnings at flat 3% nominal growth.
        -- Closed-form geometric series: earnings × ((1.03^15 - 1) / 0.03)
        --                             = earnings × 18.5989
        -- Spec: docs/specs/roi-net-lifetime-value.md §2 Decision #10.
        CASE
            WHEN b.earnings_1yr_median IS NOT NULL
                THEN ROUND(b.earnings_1yr_median * 18.5989, 2)
            ELSE NULL
        END AS lifetime_earnings_15yr,
        -- Cost-basis provenance for the new payback-multiplier ROI.
        -- 'sticker_4yr'   = cost_of_attendance_annual × 4 (preferred; in-state baseline)
        -- 'net_price_4yr' = net_price_4yr fallback when COA missing
        -- 'none'          = neither cost input available (multiplier is NULL)
        CASE
            WHEN i.cost_of_attendance_annual IS NOT NULL
                 AND i.cost_of_attendance_annual > 0 THEN 'sticker_4yr'
            WHEN i.net_price_4yr IS NOT NULL AND i.net_price_4yr > 0
                 THEN 'net_price_4yr'
            ELSE 'none'
        END AS roi_multiplier_basis,
        -- Payback multiplier (in-state baseline). Backend overrides residency-
        -- aware at runtime via stat_engine._derive_roi. See spec Decision #11.
        -- NULLIF on cost_of_attendance_annual prevents COALESCE(0 * 4.0,
        -- net_price_4yr) returning 0 — zero is not NULL, so the fallback
        -- wouldn't fire and we'd divide by zero. Belt + suspenders with
        -- the > 0 guards above (M1 from @faang-staff-engineer review).
        CASE
            WHEN b.earnings_1yr_median IS NOT NULL
                 AND b.earnings_1yr_median > 0
                 AND (
                     (i.cost_of_attendance_annual IS NOT NULL
                      AND i.cost_of_attendance_annual > 0)
                     OR (i.net_price_4yr IS NOT NULL AND i.net_price_4yr > 0)
                 )
                THEN ROUND(
                    (b.earnings_1yr_median * 18.5989)
                    / COALESCE(NULLIF(i.cost_of_attendance_annual, 0) * 4.0,
                               NULLIF(i.net_price_4yr, 0)),
                    4
                )
            ELSE NULL
        END AS roi_raw_multiplier,
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
    -- Institution-level cost enrichment (spec raw-ingest-college-scorecard-
    -- institution §Zone 3). LEFT JOIN preserves every row in ``base``; unmatched
    -- UNITIDs (~207 per 2026-04-16 EDA) get NULL for the 7 new columns.
    LEFT JOIN institution i ON i.unitid = b.unitid
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


def derive_gold_rows(
    silver_rows: list[dict],
    institution_rows: list[dict] | None = None,
) -> list[dict]:
    """Run Gold derivations over Silver rows using DuckDB.

    Args:
        silver_rows: Field-of-study Silver rows (``base.college_scorecard``).
        institution_rows: Institution-level Silver rows (``base.college_scorecard_
            institution``). Optional — when None, the LEFT JOIN produces an
            empty right side and the 7 CSI enrichment columns will all be NULL
            for every output row. This preserves backward-compatible behaviour
            for existing unit tests that do not supply institution data.

    Returns a list of dicts ready for grain-id computation and promotion.
    """
    if not silver_rows:
        return []

    # Build Arrow table from Silver rows for DuckDB
    arrow_table = pa.Table.from_pylist(silver_rows)

    # Institution silver source — register even when empty so the CTE resolves.
    # We always hand DuckDB an Arrow table with the right schema so the LEFT
    # JOIN produces NULLs correctly for unmatched unitids.
    institution_arrow = _build_institution_arrow(institution_rows or [])

    con = duckdb.connect()
    con.register("silver", arrow_table)
    con.register("institution_silver", institution_arrow)
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


# ---------------------------------------------------------------------------
# Institution silver helper + schema evolution
# ---------------------------------------------------------------------------

# Columns (and Arrow types) that the ``institution`` CTE selects. The silver
# source has many more columns; we only need these for the enrichment.
_INSTITUTION_ARROW_SCHEMA = pa.schema([
    pa.field("unitid", pa.int64()),
    pa.field("state_abbr", pa.string()),
    pa.field("net_price_annual", pa.float64()),
    pa.field("cost_of_attendance_annual", pa.float64()),
    pa.field("net_price_4yr", pa.float64()),
    pa.field("institution_control", pa.string()),
    pa.field("tuition_in_state", pa.float64()),
    pa.field("tuition_out_of_state", pa.float64()),
    pa.field("room_board_on_campus", pa.float64()),
])


def _build_institution_arrow(institution_rows: list[dict]) -> pa.Table:
    """Build a typed Arrow table for the institution CTE.

    Always emits the same schema, even when ``institution_rows`` is empty, so
    DuckDB can resolve column references in the LEFT JOIN.
    """
    names = [f.name for f in _INSTITUTION_ARROW_SCHEMA]
    columns: dict[str, list] = {name: [] for name in names}
    for row in institution_rows:
        for name in names:
            columns[name].append(row.get(name))
    return pa.table(columns, schema=_INSTITUTION_ARROW_SCHEMA)


def _evolve_schema_if_needed(table: Table, target_schema: Schema) -> list[str]:
    """Add any columns present in ``target_schema`` but missing from ``table``.

    Additive-only evolution. Existing field IDs and types are never modified.
    Returns the list of added field names (empty if schema already matches).
    """
    existing = {f.name for f in table.schema().fields}
    new_fields = [f for f in target_schema.fields if f.name not in existing]
    if not new_fields:
        return []
    with table.update_schema() as update:
        for field in new_fields:
            update.add_column(
                field.name, field.field_type, doc=None, required=field.required
            )
    table.refresh()
    return [f.name for f in new_fields]


def _overwrite_table(table: Table, records: list[dict]) -> int:
    """Overwrite an Iceberg table with new data. Returns the new snapshot ID.

    Used for idempotent re-promote where the grain is unchanged but column
    values change (e.g. adding CSI enrichment columns to existing records).
    Mirrors the helper in ``src/gold/futureproof_engine.py`` so both gold
    transformers share the same overwrite shape.
    """
    iceberg_schema = table.schema()
    date_fields = {
        f.name for f in iceberg_schema.fields if isinstance(f.field_type, DateType)
    }
    columns: dict[str, list] = {}
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
    overwrite: bool = False,
) -> dict:
    """Run the Gold zone transformation.

    Reads base.college_scorecard AND base.college_scorecard_institution from
    Silver, computes all Gold derivations (including the 7-column CSI
    enrichment), and promotes to consumable.career_outcomes.

    Args:
        project_dir: Project root. Defaults to cwd.
        overwrite: When True, replace all data in the Gold table (required for
            the 2026-04-16 CSI enrichment re-promote since record_ids already
            exist; without overwrite the dedup-append promote skips them and
            the new columns stay null). When False, uses the standard
            idempotent dedup-append promote.

    Returns:
        {"rows_read": N, "rows_institution": I, "promoted": M, "skipped": S,
         "schema_evolved": [list of added column names], ...}
    """
    project_dir = Path(project_dir or ".").resolve()

    silver_warehouse = project_dir / "data" / "silver" / "iceberg_warehouse"
    catalog_path = project_dir / "data" / "catalog" / "catalog.db"
    gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"

    # Read from Silver (field-of-study)
    logger.info("Reading from base.college_scorecard...")
    silver_catalog = get_catalog(silver_warehouse, catalog_path)
    silver_table = silver_catalog.load_table("base.college_scorecard")

    # Read via PyIceberg scan -> Arrow (same pattern as Silver transformer)
    arrow_table = silver_table.scan().to_arrow()  # noqa: F841  (DuckDB auto-registers by local name)
    con = duckdb.connect()
    result = con.sql("SELECT * FROM arrow_table").fetchall()
    columns = [field.name for field in silver_table.schema().fields]
    silver_rows = [dict(zip(columns, row)) for row in result]
    con.close()
    logger.info("Read %d rows from Silver (field-of-study)", len(silver_rows))

    # Read from Silver (institution) — spec raw-ingest-college-scorecard-
    # institution §Zone 3 enrichment. Read only the columns needed by the CTE.
    logger.info("Reading from base.college_scorecard_institution...")
    institution_table = silver_catalog.load_table(
        "base.college_scorecard_institution"
    )
    institution_cols = [f.name for f in _INSTITUTION_ARROW_SCHEMA]
    institution_arrow = institution_table.scan(
        selected_fields=tuple(institution_cols)
    ).to_arrow()
    institution_rows = institution_arrow.to_pylist()
    logger.info(
        "Read %d rows from Silver (institution)", len(institution_rows)
    )

    # Derive Gold fields
    logger.info("Computing Gold derivations...")
    gold_rows = derive_gold_rows(silver_rows, institution_rows)
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

    # Iceberg schema evolution — additive only. If the target table predates the
    # 2026-04-16 CSI enrichment, add the 6 new physical columns (IDs 32–37)
    # in-place. Existing field IDs and types are never touched.
    evolved = _evolve_schema_if_needed(gold_table, get_gold_schema())
    if evolved:
        logger.info(
            "Evolved consumable.career_outcomes schema: added %d fields (%s)",
            len(evolved), evolved,
        )

    if overwrite:
        logger.info(
            "Overwrite mode: replacing all data in consumable.career_outcomes"
        )
        snapshot_id = _overwrite_table(gold_table, gold_rows)
        result_dict = {
            "promoted": len(gold_rows),
            "skipped": 0,
            "snapshot_id": snapshot_id,
        }
    else:
        result_dict = promote(
            gold_table,
            gold_rows,
            id_field="record_id",
            spec_name=SPEC_NAME,
            agent_name="@primary-agent",
        )

    logger.info(
        "Promote complete: %d promoted, %d skipped",
        result_dict["promoted"],
        result_dict["skipped"],
    )

    return {
        "rows_read": len(silver_rows),
        "rows_institution": len(institution_rows),
        "rows_derived": len(gold_rows),
        "promoted": result_dict["promoted"],
        "skipped_dedup": result_dict["skipped"],
        "schema_evolved": evolved,
        "snapshot_id": result_dict.get("snapshot_id"),
    }


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    do_overwrite = "--overwrite" in sys.argv
    result = transform(overwrite=do_overwrite)
    print(f"Gold transform complete: {result}")
