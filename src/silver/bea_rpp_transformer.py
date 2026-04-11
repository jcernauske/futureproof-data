"""Silver zone transformer for BEA Regional Price Parities base table.

Reads bronze.bea_rpp (51 rows: 50 states + DC) from the Bronze zone and
produces base.bea_rpp with:

  - state_fips / state_name passthrough (renamed from geo_fips / geo_name)
  - state_abbr derivation (static FIPS-to-USPS lookup)
  - census_region derivation (static FIPS-to-region lookup, DC -> South)
  - rpp_all_items passthrough
  - purchasing_power_multiplier = 100.0 / rpp_all_items
  - verification_status derivation (8 BEA-verified FIPS -> bea_official,
    the other 43 -> estimate)
  - data_year passthrough (expected constant 2024)
  - source_load_date passthrough + ingested_at timestamp
  - Deterministic record_id via compute_grain_id(..., prefix='rpp')
  - Idempotent promotion via the Brightsmith promote pattern
"""

from __future__ import annotations

import datetime
import logging
import re
from pathlib import Path
from typing import Any

from pyiceberg.schema import Schema
from pyiceberg.types import (
    DateType,
    DoubleType,
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

from silver._us_state_reference import (
    BEA_VERIFIED_FIPS,
    FIPS_TO_CENSUS_REGION,
    FIPS_TO_USPS,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GRAIN_FIELDS: list[str] = ["state_fips"]
GRAIN_PREFIX = "rpp"
SPEC_NAME = "silver-base-bea-rpp"
EXPECTED_ROW_COUNT = 51
DEFAULT_DATA_YEAR = 2024

_FIPS_PATTERN = re.compile(r"^\d{2}$")


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def get_silver_schema() -> Schema:
    """Iceberg schema for base.bea_rpp (11 columns, all required)."""
    return Schema(
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "state_fips", StringType(), required=True),
        NestedField(3, "state_name", StringType(), required=True),
        NestedField(4, "state_abbr", StringType(), required=True),
        NestedField(5, "census_region", StringType(), required=True),
        NestedField(6, "rpp_all_items", DoubleType(), required=True),
        NestedField(7, "purchasing_power_multiplier", DoubleType(), required=True),
        NestedField(8, "verification_status", StringType(), required=True),
        NestedField(9, "data_year", IntegerType(), required=True),
        NestedField(10, "source_load_date", DateType(), required=True),
        NestedField(11, "ingested_at", TimestampType(), required=True),
    )


# ---------------------------------------------------------------------------
# Derivation helpers
# ---------------------------------------------------------------------------


def derive_state_abbr(state_fips: str) -> str:
    """Return the USPS two-letter abbreviation for a state FIPS code.

    Raises ValueError if the code is not in the 51-entry lookup.
    """
    try:
        return FIPS_TO_USPS[state_fips]
    except KeyError as exc:
        raise ValueError(
            f"Unknown state_fips '{state_fips}' — not in FIPS_TO_USPS lookup"
        ) from exc


def derive_census_region(state_fips: str) -> str:
    """Return the U.S. Census Bureau region for a state FIPS code.

    DC (FIPS '11') maps to 'South' per Census convention.  Raises
    ValueError if the code is not in the 51-entry lookup.
    """
    try:
        return FIPS_TO_CENSUS_REGION[state_fips]
    except KeyError as exc:
        raise ValueError(
            f"Unknown state_fips '{state_fips}' — not in FIPS_TO_CENSUS_REGION lookup"
        ) from exc


def derive_purchasing_power_multiplier(rpp_all_items: float) -> float:
    """Compute the pre-computed salary scaling factor ``100.0 / rpp_all_items``.

    Single source of truth for salary adjustment across the pipeline.
    Raises ValueError for zero or non-finite input.
    """
    if rpp_all_items is None:
        raise ValueError("rpp_all_items is None — cannot compute multiplier")
    rpp = float(rpp_all_items)
    if rpp == 0.0:
        raise ValueError("rpp_all_items is 0 — division by zero")
    if rpp != rpp:  # NaN check
        raise ValueError("rpp_all_items is NaN")
    return 100.0 / rpp


def derive_verification_status(state_fips: str) -> str:
    """Return 'bea_official' for BEA-verified FIPS codes, else 'estimate'."""
    return "bea_official" if state_fips in BEA_VERIFIED_FIPS else "estimate"


def _validate_state_fips(raw_value: Any) -> str:
    """Normalize and validate a state FIPS value from a Bronze row."""
    if raw_value is None:
        raise ValueError("Missing state_fips (bronze geo_fips) in row")
    value = str(raw_value).strip()
    if not _FIPS_PATTERN.match(value):
        raise ValueError(
            f"Invalid state_fips format: '{value}' (expected 2-digit zero-padded)"
        )
    if value not in FIPS_TO_USPS:
        raise ValueError(
            f"state_fips '{value}' is not a known U.S. state or DC FIPS code"
        )
    return value


# ---------------------------------------------------------------------------
# Row transform
# ---------------------------------------------------------------------------


def transform_row(
    raw: dict,
    ingested_at: datetime.datetime | None = None,
) -> dict:
    """Transform a single Bronze row into a Silver base.bea_rpp row.

    Args:
        raw: A row dict read from bronze.bea_rpp.  Expected keys include
             ``geo_fips``, ``geo_name``, ``rpp_all_items``, ``data_year``,
             and ``load_date``.
        ingested_at: Override for the promotion timestamp.  Defaults to
             ``datetime.datetime.now(tz=datetime.timezone.utc)``.

    Returns:
        An ordered dict with the 11 Silver columns plus a deterministic
        ``record_id``.
    """
    if ingested_at is None:
        ingested_at = datetime.datetime.now(tz=datetime.timezone.utc)

    state_fips = _validate_state_fips(raw.get("geo_fips"))

    state_name = raw.get("geo_name")
    if state_name is None or not str(state_name).strip():
        raise ValueError(f"Missing geo_name for state_fips '{state_fips}'")
    state_name = str(state_name).strip()

    rpp_all_items = raw.get("rpp_all_items")
    if rpp_all_items is None:
        raise ValueError(f"Missing rpp_all_items for state_fips '{state_fips}'")
    rpp_all_items = float(rpp_all_items)

    data_year = raw.get("data_year")
    if data_year is None:
        data_year = DEFAULT_DATA_YEAR
    data_year = int(data_year)

    source_load_date = raw.get("load_date")
    if source_load_date is None:
        raise ValueError(f"Missing load_date for state_fips '{state_fips}'")

    record = {
        "state_fips": state_fips,
        "state_name": state_name,
        "state_abbr": derive_state_abbr(state_fips),
        "census_region": derive_census_region(state_fips),
        "rpp_all_items": rpp_all_items,
        "purchasing_power_multiplier": derive_purchasing_power_multiplier(rpp_all_items),
        "verification_status": derive_verification_status(state_fips),
        "data_year": data_year,
        "source_load_date": source_load_date,
        "ingested_at": ingested_at,
    }
    record["record_id"] = compute_grain_id(record, GRAIN_FIELDS, prefix=GRAIN_PREFIX)
    return record


def transform_rows(
    bronze_rows: list[dict],
    ingested_at: datetime.datetime | None = None,
) -> list[dict]:
    """Transform every Bronze row into a Silver row, preserving ordering.

    Enforces the 51-row expectation up front so downstream invariants
    catch a short or over-long Bronze snapshot immediately.
    """
    if ingested_at is None:
        ingested_at = datetime.datetime.now(tz=datetime.timezone.utc)

    if len(bronze_rows) != EXPECTED_ROW_COUNT:
        logger.warning(
            "Bronze row count is %d, expected %d (closed set of 50 states + DC)",
            len(bronze_rows),
            EXPECTED_ROW_COUNT,
        )

    silver_rows = [transform_row(row, ingested_at=ingested_at) for row in bronze_rows]

    # Uniqueness guard — the promote pattern also dedups, but failing
    # here gives a clearer error than a silent dedup skip.
    seen: set[str] = set()
    for row in silver_rows:
        if row["state_fips"] in seen:
            raise ValueError(f"Duplicate state_fips in Silver rows: {row['state_fips']}")
        seen.add(row["state_fips"])

    return silver_rows


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------


def promote_bea_rpp(
    project_dir: str | Path | None = None,
    bronze_warehouse: str | Path | None = None,
    silver_warehouse: str | Path | None = None,
    catalog_path: str | Path | None = None,
    ingested_at: datetime.datetime | None = None,
) -> dict:
    """Run the Silver zone transformation for base.bea_rpp.

    Reads bronze.bea_rpp from the Bronze zone, transforms 51 rows, and
    promotes to base.bea_rpp via the idempotent promote pattern.

    Args:
        project_dir: Project root.  Defaults to current working directory.
             Only used when the warehouse/catalog paths are left as None.
        bronze_warehouse: Override for the Bronze Iceberg warehouse path.
        silver_warehouse: Override for the Silver Iceberg warehouse path.
        catalog_path: Override for the shared SQLite catalog DB path.
        ingested_at: Override for the promotion timestamp.  Tests pass
             a fixed timestamp for determinism.

    Returns:
        Dict with run metrics: ``rows_read``, ``rows_transformed``,
        ``promoted``, ``skipped_dedup``, ``snapshot_id``.
    """
    project_dir = Path(project_dir or ".").resolve()

    bronze_warehouse = Path(
        bronze_warehouse or project_dir / "data" / "bronze" / "iceberg_warehouse"
    )
    silver_warehouse = Path(
        silver_warehouse or project_dir / "data" / "silver" / "iceberg_warehouse"
    )
    catalog_path = Path(
        catalog_path or project_dir / "data" / "catalog" / "catalog.db"
    )

    # Read Bronze
    logger.info("Reading from bronze.bea_rpp...")
    bronze_catalog = get_catalog(bronze_warehouse, catalog_path)
    bronze_table = bronze_catalog.load_table("bronze.bea_rpp")
    bronze_rows = read_with_duckdb(bronze_table)
    logger.info("Read %d rows from bronze.bea_rpp", len(bronze_rows))

    # Transform
    logger.info("Transforming to Silver base table...")
    silver_rows = transform_rows(bronze_rows, ingested_at=ingested_at)
    logger.info("Transformed %d rows", len(silver_rows))

    # Verification status counts (log for parity with run-report expectations).
    verification_counts: dict[str, int] = {}
    for row in silver_rows:
        v = row["verification_status"]
        verification_counts[v] = verification_counts.get(v, 0) + 1
    logger.info("verification_status distribution: %s", verification_counts)

    # Promote to Silver
    logger.info("Promoting to base.bea_rpp...")
    silver_catalog = get_catalog(silver_warehouse, catalog_path)
    silver_table = get_or_create_table(
        silver_catalog, "base", "bea_rpp", get_silver_schema()
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
        result["promoted"],
        result["skipped"],
    )

    return {
        "rows_read": len(bronze_rows),
        "rows_transformed": len(silver_rows),
        "promoted": result["promoted"],
        "skipped_dedup": result["skipped"],
        "snapshot_id": result.get("snapshot_id"),
        "verification_counts": verification_counts,
    }


def transform(project_dir: str | Path | None = None) -> dict:
    """Manifest entry point — thin wrapper around ``promote_bea_rpp``."""
    return promote_bea_rpp(project_dir=project_dir)
