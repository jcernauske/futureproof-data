"""Gold zone transformer for consumable.ai_exposure.

Reads base.karpathy_ai_exposure from the Silver zone, filters to rows
where bls_match = true, derives stat_res (AI Resilience) and
boss_ai_score (Fight AI boss strength), and promotes to
consumable.ai_exposure via the Brightsmith idempotent promote pattern.

Grain: soc_code
Record ID: compute_grain_id(row, ['soc_code'], prefix='aie')
"""

import datetime
import logging
from pathlib import Path

import duckdb
from pyiceberg.schema import Schema
from pyiceberg.types import (
    IntegerType,
    NestedField,
    StringType,
    TimestampType,
)

from brightsmith.infra.grain import compute_grain_id
from brightsmith.infra.iceberg_setup import get_catalog, get_or_create_table
from brightsmith.infra.promote import promote

logger = logging.getLogger(__name__)

SPEC_NAME = "gold-ai-exposure"
GRAIN_FIELDS = ["soc_code"]
GRAIN_PREFIX = "aie"


def get_gold_schema() -> Schema:
    """Iceberg schema for consumable.ai_exposure (9 columns)."""
    return Schema(
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "soc_code", StringType(), required=True),
        NestedField(3, "occupation_title", StringType(), required=True),
        NestedField(4, "exposure_score", IntegerType(), required=True),
        NestedField(5, "stat_res", IntegerType(), required=True),
        NestedField(6, "boss_ai_score", IntegerType(), required=True),
        NestedField(7, "rationale", StringType(), required=True),
        NestedField(8, "category", StringType(), required=True),
        NestedField(9, "promoted_at", TimestampType(), required=True),
    )


def compute_stat_res(exposure_score: int) -> int:
    """Derive AI Resilience stat (1-10) from exposure score (0-10).

    Higher exposure = lower resilience.
    Formula: MIN(11 - exposure_score, 10)

    Edge case: exposure_score=0 -> 11, capped at 10.
    """
    return min(11 - exposure_score, 10)


def compute_boss_ai_score(exposure_score: int) -> int:
    """Derive Fight AI boss strength (1-10) from exposure score (0-10).

    Higher exposure = harder fight. Floor at 1.
    Formula: MAX(exposure_score, 1)
    """
    return max(exposure_score, 1)


def derive_gold_rows(silver_rows: list[dict]) -> list[dict]:
    """Filter Silver rows to bls_match=true and derive Gold fields.

    Filters out rows where bls_match is not true, then computes:
    - stat_res from exposure_score
    - boss_ai_score from exposure_score
    - Carries forward: soc_code, occupation_title, exposure_score, rationale, category

    Returns a list of dicts ready for grain-id computation and promotion.
    """
    gold_rows = []

    for row in silver_rows:
        if not row.get("bls_match"):
            continue

        soc_code = row.get("soc_code")
        if soc_code is None:
            continue

        exposure_score = row["exposure_score"]

        gold_row = {
            "soc_code": soc_code,
            "occupation_title": row["occupation_title"],
            "exposure_score": exposure_score,
            "stat_res": compute_stat_res(exposure_score),
            "boss_ai_score": compute_boss_ai_score(exposure_score),
            "rationale": row["rationale"],
            "category": row["category"],
        }

        gold_rows.append(gold_row)

    return gold_rows


def add_record_ids(gold_rows: list[dict], promoted_at: datetime.datetime) -> list[dict]:
    """Add record_id and promoted_at to each Gold row.

    The grain hash uses ['soc_code'] per spec with prefix 'aie'.
    """
    for row in gold_rows:
        row["record_id"] = compute_grain_id(row, GRAIN_FIELDS, prefix=GRAIN_PREFIX)
        row["promoted_at"] = promoted_at
    return gold_rows


def transform(
    project_dir: str | Path | None = None,
) -> dict:
    """Run the Gold zone transformation for consumable.ai_exposure.

    Reads base.karpathy_ai_exposure from Silver, filters to bls_match=true,
    derives stat_res and boss_ai_score, and promotes to
    consumable.ai_exposure via idempotent promote pattern.

    Returns:
        {"rows_read": N, "rows_filtered": N, "rows_derived": N,
         "promoted": N, "skipped_dedup": N, "snapshot_id": X | None}
    """
    project_dir = Path(project_dir or ".").resolve()

    silver_warehouse = project_dir / "data" / "silver" / "iceberg_warehouse"
    catalog_path = project_dir / "data" / "catalog" / "catalog.db"
    gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"

    # Read from Silver
    logger.info("Reading from base.karpathy_ai_exposure...")
    silver_catalog = get_catalog(silver_warehouse, catalog_path)
    silver_table = silver_catalog.load_table("base.karpathy_ai_exposure")

    arrow_table = silver_table.scan().to_arrow()
    con = duckdb.connect()
    result = con.sql("SELECT * FROM arrow_table").fetchall()
    columns = [field.name for field in silver_table.schema().fields]
    silver_rows = [dict(zip(columns, row)) for row in result]
    con.close()
    logger.info("Read %d rows from Silver", len(silver_rows))

    # Derive Gold fields (includes bls_match filter)
    logger.info("Computing Gold derivations (filtering to bls_match=true)...")
    gold_rows = derive_gold_rows(silver_rows)
    rows_filtered = len(silver_rows) - len(gold_rows)
    logger.info(
        "Derived %d Gold rows (%d filtered out by bls_match)",
        len(gold_rows), rows_filtered,
    )

    # Add record_id and promoted_at
    promoted_at = datetime.datetime.now(tz=datetime.timezone.utc)
    add_record_ids(gold_rows, promoted_at)

    # Promote to Gold
    logger.info("Promoting to consumable.ai_exposure...")
    gold_catalog = get_catalog(gold_warehouse, catalog_path)
    gold_table = get_or_create_table(
        gold_catalog, "consumable", "ai_exposure", get_gold_schema()
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
        "rows_filtered": rows_filtered,
        "rows_derived": len(gold_rows),
        "promoted": result["promoted"],
        "skipped_dedup": result["skipped"],
        "snapshot_id": result.get("snapshot_id"),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    result = transform()
    print(f"Gold transform complete: {result}")
