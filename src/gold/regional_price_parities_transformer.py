"""Gold zone transformer for consumable.regional_price_parities.

Reads base.bea_rpp from the Silver zone, derives cost_tier from
rpp_all_items via the frozen 5-bucket CASE, pre-computes the four
display-ready adjusted salary columns, carries forward the Silver
columns plus verification_status (per Bronze Condition 7), stamps
promoted_at, and writes to consumable.regional_price_parities via the
Brightsmith idempotent promote pattern.

Grain: state_fips
Record ID: compute_grain_id(row, ['state_fips'], prefix='rpc')

NOTE: The record_id prefix is 'rpc' (regional-price-consumable), NOT
Silver's 'rpp'. Gold keeps a separate hash namespace from Silver per
the physical model so record_ids cannot collide across zones.
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path

import duckdb
from pyiceberg.schema import Schema
from pyiceberg.types import (
    DoubleType,
    IntegerType,
    NestedField,
    StringType,
    TimestampType,
)

from brightsmith.infra.grain import compute_grain_id
from brightsmith.infra.iceberg_setup import get_catalog, get_or_create_table
from brightsmith.infra.promote import promote

from gold._cost_tier import classify_cost_tier

logger = logging.getLogger(__name__)

SPEC_NAME = "gold-regional-price-parities"
GRAIN_FIELDS = ["state_fips"]
GRAIN_PREFIX = "rpc"

# Salary anchor levels (USD) for the pre-computed adjusted columns.
# Frozen by the spec. A future spec adding e.g. adjusted_150k must
# append to this list and also append a column to the Gold schema.
SALARY_ANCHORS: tuple[tuple[int, str], ...] = (
    (30000, "adjusted_30k"),
    (50000, "adjusted_50k"),
    (75000, "adjusted_75k"),
    (100000, "adjusted_100k"),
)

# Silver columns carried forward verbatim to Gold.
SILVER_PASSTHROUGH_FIELDS: tuple[str, ...] = (
    "state_fips",
    "state_name",
    "state_abbr",
    "census_region",
    "rpp_all_items",
    "purchasing_power_multiplier",
    "verification_status",
    "data_year",
)


def get_gold_schema() -> Schema:
    """Iceberg schema for consumable.regional_price_parities (15 columns).

    Column order matches the physical model exactly.
    """
    return Schema(
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "state_fips", StringType(), required=True),
        NestedField(3, "state_name", StringType(), required=True),
        NestedField(4, "state_abbr", StringType(), required=True),
        NestedField(5, "census_region", StringType(), required=True),
        NestedField(6, "rpp_all_items", DoubleType(), required=True),
        NestedField(7, "purchasing_power_multiplier", DoubleType(), required=True),
        NestedField(8, "cost_tier", StringType(), required=True),
        NestedField(9, "adjusted_30k", DoubleType(), required=True),
        NestedField(10, "adjusted_50k", DoubleType(), required=True),
        NestedField(11, "adjusted_75k", DoubleType(), required=True),
        NestedField(12, "adjusted_100k", DoubleType(), required=True),
        NestedField(13, "verification_status", StringType(), required=True),
        NestedField(14, "data_year", IntegerType(), required=True),
        NestedField(15, "promoted_at", TimestampType(), required=True),
    )


def compute_adjusted_salary(national_salary: float, multiplier: float) -> float:
    """Pre-compute a salary figure adjusted for regional purchasing power.

    Uses Python's built-in round() which implements banker's rounding
    (IEEE 754 round-half-to-even), matching DuckDB's default ROUND().
    Consistency across the transformer, DQ engine, and database is
    required so the invariant
    `abs(adjusted_Nk - round(N*1000*multiplier, 2)) <= 0.01` holds on
    both sides.
    """
    return round(national_salary * multiplier, 2)


def derive_gold_rows(silver_rows: list[dict]) -> list[dict]:
    """Derive Gold rows from Silver rows.

    For each Silver row:
      - Carry forward the 8 passthrough columns verbatim.
      - Derive cost_tier from rpp_all_items via the frozen CASE.
      - Compute the four adjusted_Nk columns as
        round(N * 1000 * purchasing_power_multiplier, 2).

    Does NOT assign record_id or promoted_at; those are added by
    add_record_ids() so tests can exercise the two steps independently.
    """
    gold_rows: list[dict] = []
    for row in silver_rows:
        gold_row: dict = {field: row[field] for field in SILVER_PASSTHROUGH_FIELDS}
        gold_row["cost_tier"] = classify_cost_tier(row["rpp_all_items"])

        multiplier = row["purchasing_power_multiplier"]
        for anchor, column in SALARY_ANCHORS:
            gold_row[column] = compute_adjusted_salary(float(anchor), multiplier)

        gold_rows.append(gold_row)
    return gold_rows


def add_record_ids(
    gold_rows: list[dict],
    promoted_at: datetime.datetime,
) -> list[dict]:
    """Add record_id and promoted_at to each Gold row.

    The grain hash uses ['state_fips'] per the spec with prefix 'rpc'.
    """
    for row in gold_rows:
        row["record_id"] = compute_grain_id(row, GRAIN_FIELDS, prefix=GRAIN_PREFIX)
        row["promoted_at"] = promoted_at
    return gold_rows


def transform(
    project_dir: str | Path | None = None,
) -> dict:
    """Run the Gold zone transformation for consumable.regional_price_parities.

    Reads base.bea_rpp from Silver, applies the 5 Gold derivations,
    and promotes to consumable.regional_price_parities via the
    idempotent promote pattern.

    Returns:
        {
            "rows_read": N,
            "rows_derived": N,
            "promoted": N,
            "skipped_dedup": N,
            "snapshot_id": X | None,
        }
    """
    project_dir = Path(project_dir or ".").resolve()

    silver_warehouse = project_dir / "data" / "silver" / "iceberg_warehouse"
    catalog_path = project_dir / "data" / "catalog" / "catalog.db"
    gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"

    # Read from Silver.
    logger.info("Reading from base.bea_rpp...")
    silver_catalog = get_catalog(silver_warehouse, catalog_path)
    silver_table = silver_catalog.load_table("base.bea_rpp")

    arrow_table = silver_table.scan().to_arrow()
    con = duckdb.connect()
    result = con.sql("SELECT * FROM arrow_table").fetchall()
    columns = [field.name for field in silver_table.schema().fields]
    silver_rows = [dict(zip(columns, row)) for row in result]
    con.close()
    logger.info("Read %d rows from Silver", len(silver_rows))

    # Derive Gold fields.
    logger.info("Computing Gold derivations (cost_tier + adjusted_Nk)...")
    gold_rows = derive_gold_rows(silver_rows)
    logger.info("Derived %d Gold rows", len(gold_rows))

    # Stamp record_id and promoted_at.
    promoted_at = datetime.datetime.now(tz=datetime.timezone.utc)
    add_record_ids(gold_rows, promoted_at)

    # Promote to Gold.
    logger.info("Promoting to consumable.regional_price_parities...")
    gold_catalog = get_catalog(gold_warehouse, catalog_path)
    gold_table = get_or_create_table(
        gold_catalog,
        "consumable",
        "regional_price_parities",
        get_gold_schema(),
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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(message)s",
    )
    result = transform()
    print(f"Gold transform complete: {result}")
