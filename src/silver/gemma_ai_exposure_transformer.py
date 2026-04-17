"""Silver zone transformer for Gemma AI Exposure base table.

Reads bronze.raw_gemma_ai_exposure from the Bronze zone (~798 rows) and
produces base.gemma_ai_exposure with:
  - SOC normalization to XX-XXXX format
  - Drop of ``error != NULL`` rows (failed scorer outputs stay in Bronze)
  - Referential-integrity check against consumable.onet_work_profiles
  - record_id via compute_grain_id with prefix 'gae'
  - Idempotent promotion via the Brightsmith promote pattern
"""

from __future__ import annotations

import datetime
import logging
import re
from pathlib import Path

from pyiceberg.schema import Schema
from pyiceberg.types import (
    BooleanType,
    IntegerType,
    NestedField,
    StringType,
    TimestampType,
)

from brightsmith.infra.grain import compute_grain_id
from brightsmith.infra.iceberg_setup import (
    get_catalog,
    get_or_create_table,
    read_with_duckdb,
)
from brightsmith.infra.promote import promote

logger = logging.getLogger(__name__)

SPEC_NAME = "silver-base-gemma-ai-exposure"
GRAIN_FIELDS = ["soc_code_normalized"]
GRAIN_PREFIX = "gae"

_SOC_PATTERN = re.compile(r"^\d{2}-\d{4}$")


def get_silver_schema() -> Schema:
    """Iceberg schema for base.gemma_ai_exposure."""
    return Schema(
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "soc_code", StringType(), required=True),
        NestedField(3, "soc_code_normalized", StringType(), required=True),
        NestedField(4, "primary_title", StringType(), required=False),
        NestedField(5, "exposure_score", IntegerType(), required=True),
        NestedField(6, "rationale", StringType(), required=True),
        NestedField(7, "task_breakdown_automatable", StringType(), required=False),
        NestedField(8, "task_breakdown_human", StringType(), required=False),
        NestedField(9, "scoring_model", StringType(), required=True),
        NestedField(10, "model_tag", StringType(), required=False),
        NestedField(11, "scored_at", TimestampType(), required=False),
        NestedField(12, "join_valid", BooleanType(), required=True),
        NestedField(13, "ingested_at", TimestampType(), required=True),
    )


def normalize_soc(soc_code: str | None) -> str | None:
    """Normalize SOC code to XX-XXXX format.

    Strips whitespace; if the input is already XX-XXXX, returns it
    unchanged. If it's 6 digits without a hyphen, inserts one. Returns
    None for anything that cannot be coerced.
    """
    if soc_code is None:
        return None
    s = str(soc_code).strip()
    if not s:
        return None
    if _SOC_PATTERN.match(s):
        return s
    digits = re.sub(r"\D", "", s)
    if len(digits) == 6:
        return f"{digits[:2]}-{digits[2:]}"
    return None


def transform_rows(
    bronze_rows: list[dict],
    onet_soc_set: set[str],
) -> list[dict]:
    """Transform Bronze rows into Silver base rows.

    * Drops ``error != NULL`` rows — they stay in Bronze for audit but
      do not propagate downstream.
    * Normalizes ``bls_soc_code`` → ``soc_code_normalized``.
    * Dedups by normalized SOC (first-seen wins; the scorer already
      produces one row per occupation so collisions would indicate a
      re-run artifact).
    * Computes ``join_valid = soc_code_normalized in onet_soc_set``.
    * Stamps ``record_id`` and ``ingested_at``.
    """
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    seen: set[str] = set()
    silver_rows: list[dict] = []
    dropped_errors = 0
    dropped_unnormalizable = 0
    dropped_duplicates = 0

    for row in bronze_rows:
        if row.get("error"):
            dropped_errors += 1
            continue

        raw_soc = row.get("bls_soc_code")
        normalized = normalize_soc(raw_soc)
        if normalized is None:
            dropped_unnormalizable += 1
            logger.warning(
                "Dropping Gemma row with unnormalizable SOC %r", raw_soc
            )
            continue

        if normalized in seen:
            dropped_duplicates += 1
            continue
        seen.add(normalized)

        exposure = row.get("exposure_score")
        rationale = row.get("rationale")
        if exposure is None or rationale is None:
            # Missing required fields — treat as if it were an error row.
            dropped_errors += 1
            logger.warning(
                "Dropping Gemma row with missing exposure_score/rationale "
                "(soc=%s)", normalized,
            )
            continue

        silver_rows.append({
            "soc_code": str(raw_soc),
            "soc_code_normalized": normalized,
            "primary_title": row.get("primary_title"),
            "exposure_score": int(exposure),
            "rationale": str(rationale),
            "task_breakdown_automatable": row.get("task_breakdown_automatable"),
            "task_breakdown_human": row.get("task_breakdown_human"),
            "scoring_model": row.get("scoring_model") or "gemma-4",
            "model_tag": row.get("model_tag"),
            "scored_at": row.get("scored_at"),
            "join_valid": normalized in onet_soc_set,
            "ingested_at": now,
        })

    # Stamp record_ids.
    for row in silver_rows:
        row["record_id"] = compute_grain_id(
            row, GRAIN_FIELDS, prefix=GRAIN_PREFIX
        )

    logger.info(
        "Silver transform: %d Bronze → %d Silver "
        "(%d error rows dropped, %d unnormalizable dropped, %d duplicates dropped)",
        len(bronze_rows), len(silver_rows),
        dropped_errors, dropped_unnormalizable, dropped_duplicates,
    )
    return silver_rows


def _load_onet_soc_set(
    silver_catalog_path: Path,
    silver_warehouse: Path,
) -> set[str]:
    """Load the set of SOC codes present in consumable.onet_work_profiles.

    Returns an empty set if the O*NET Gold table is not yet built —
    downstream rows simply get ``join_valid=False`` and the Silver DQ
    rule for referential integrity fails loudly.
    """
    gold_warehouse = silver_warehouse.parent.parent / "gold" / "iceberg_warehouse"
    try:
        gold_catalog = get_catalog(gold_warehouse, silver_catalog_path)
        onet_table = gold_catalog.load_table("consumable.onet_work_profiles")
    except Exception as exc:
        logger.warning(
            "consumable.onet_work_profiles not loadable (%s); "
            "join_valid will be False for every row",
            exc,
        )
        return set()

    onet_rows = read_with_duckdb(onet_table)
    return {
        str(r["bls_soc_code"])
        for r in onet_rows
        if r.get("bls_soc_code")
    }


def transform(project_dir: str | Path | None = None) -> dict:
    """Run the Silver zone transformation for base.gemma_ai_exposure."""
    project_dir = Path(project_dir or ".").resolve()

    bronze_warehouse = project_dir / "data" / "bronze" / "iceberg_warehouse"
    silver_warehouse = project_dir / "data" / "silver" / "iceberg_warehouse"
    catalog_path = project_dir / "data" / "catalog" / "catalog.db"

    logger.info("Reading from bronze.raw_gemma_ai_exposure...")
    bronze_catalog = get_catalog(bronze_warehouse, catalog_path)
    bronze_table = bronze_catalog.load_table("bronze.raw_gemma_ai_exposure")
    bronze_rows = read_with_duckdb(bronze_table)
    logger.info("Read %d rows from Bronze", len(bronze_rows))

    onet_soc_set = _load_onet_soc_set(catalog_path, silver_warehouse)
    logger.info("Loaded %d O*NET SOC codes for join validation", len(onet_soc_set))

    silver_rows = transform_rows(bronze_rows, onet_soc_set)
    join_valid_count = sum(1 for r in silver_rows if r["join_valid"])
    logger.info(
        "Silver rows: %d (join_valid=true: %d, false: %d)",
        len(silver_rows), join_valid_count,
        len(silver_rows) - join_valid_count,
    )

    silver_catalog = get_catalog(silver_warehouse, catalog_path)
    silver_table = get_or_create_table(
        silver_catalog, "base", "gemma_ai_exposure", get_silver_schema()
    )
    result = promote(
        silver_table,
        silver_rows,
        id_field="record_id",
        spec_name=SPEC_NAME,
        agent_name="@primary-agent",
    )

    logger.info(
        "Promote complete: %d promoted, %d skipped",
        result["promoted"], result["skipped"],
    )

    return {
        "rows_read": len(bronze_rows),
        "rows_transformed": len(silver_rows),
        "join_valid_count": join_valid_count,
        "promoted": result["promoted"],
        "skipped_dedup": result["skipped"],
        "snapshot_id": result.get("snapshot_id"),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    print(transform())
