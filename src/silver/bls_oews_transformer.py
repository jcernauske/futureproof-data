"""Silver zone transformer for BLS Occupational Employment & Wage Statistics base table.

Reads ``bronze.bls_oews`` from the Bronze zone and produces ``base.bls_oews`` via
the idempotent promote pattern. Validates SOC code format, enforces the wage
percentile monotonicity invariant (logging violations), normalizes top-coded
values to the spec-mandated $239,200 floor, and computes a deterministic
``record_id`` via ``compute_grain_id`` with prefix ``oews``.

Pattern mirrors ``src/silver/bls_ooh_transformer.py`` (same SOC keying) and
``src/silver/bea_rpp_transformer.py`` (single-source 1:1 promote pattern).
"""

from __future__ import annotations

import datetime
import logging
import re
from pathlib import Path
from typing import Any

from pyiceberg.schema import Schema
from pyiceberg.types import (
    BooleanType,
    DateType,
    DoubleType,
    LongType,
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


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GRAIN_FIELDS: list[str] = ["soc_code"]
GRAIN_PREFIX = "oews"
SPEC_NAME = "silver-base-bls-oews"

# BLS top-code floor — when wage_capped is True, capped percentiles must
# equal exactly this number (per spec §Silver Transformations §3).
TOP_CODED_VALUE: float = 239_200.0

# The five annual wage percentile fields, in monotonicity-check order.
_PERCENTILE_FIELDS: tuple[str, ...] = (
    "wage_annual_p10",
    "wage_annual_p25",
    "wage_annual_median",
    "wage_annual_p75",
    "wage_annual_p90",
)

_SOC_PATTERN = re.compile(r"^\d{2}-\d{4}$")


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def get_silver_schema() -> Schema:
    """Iceberg schema for ``base.bls_oews`` (13 columns)."""
    return Schema(
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "soc_code", StringType(), required=True),
        NestedField(3, "occupation_title", StringType(), required=True),
        NestedField(4, "total_employment", LongType(), required=False),
        NestedField(5, "wage_annual_p10", DoubleType(), required=False),
        NestedField(6, "wage_annual_p25", DoubleType(), required=False),
        NestedField(7, "wage_annual_median", DoubleType(), required=False),
        NestedField(8, "wage_annual_p75", DoubleType(), required=False),
        NestedField(9, "wage_annual_p90", DoubleType(), required=False),
        NestedField(10, "wage_annual_mean", DoubleType(), required=False),
        NestedField(11, "wage_capped", BooleanType(), required=True),
        NestedField(12, "source_load_date", DateType(), required=True),
        NestedField(13, "ingested_at", TimestampType(), required=True),
    )


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_soc_code(raw_value: Any) -> str:
    """Normalize and validate the SOC code from a Bronze row.

    Raises ValueError on missing or malformed values so callers can log and
    skip per spec §"Reject malformed SOC codes (log, skip)".
    """
    if raw_value is None:
        raise ValueError("Missing soc_code")
    value = str(raw_value).strip()
    if not value:
        raise ValueError("Empty soc_code")
    if not _SOC_PATTERN.match(value):
        raise ValueError(f"Invalid SOC code format: '{value}' (expected XX-XXXX)")
    return value


def check_monotonicity(record: dict) -> list[str]:
    """Return a list of monotonicity-violation messages for a row.

    Verifies p10 <= p25 <= median <= p75 <= p90 across non-null values only.
    Per spec, violations are logged but rows are NOT skipped — the Silver DQ
    rule (SLV-OEWS-005) catches anything that slips through.

    Returns an empty list when the row is monotone (or all five values are
    null).
    """
    violations: list[str] = []
    prev_name: str | None = None
    prev_value: float | None = None
    for name in _PERCENTILE_FIELDS:
        value = record.get(name)
        if value is None:
            continue
        if prev_value is not None and prev_name is not None and value < prev_value:
            violations.append(
                f"{prev_name}={prev_value} > {name}={value}"
            )
        prev_name = name
        prev_value = value
    return violations


def normalize_top_code(record: dict) -> dict:
    """Normalize top-coded percentile values to exactly $239,200.

    Per spec §Silver Transformations §3: "Where wage_capped = True, ensure the
    capped percentile(s) are exactly 239200." The Bronze ingestor already
    writes 239200.0 for any percentile parsed from the ``#`` sentinel, but
    floating-point drift in re-parses or backfills could produce values such
    as 239199.99 — this guard snaps any non-null percentile within $1 of the
    top-code floor (when the row is flagged capped) to exactly 239200.0.

    Mutates and returns the same dict for fluent chaining.
    """
    if not record.get("wage_capped"):
        return record
    for name in _PERCENTILE_FIELDS:
        value = record.get(name)
        if value is None:
            continue
        if abs(float(value) - TOP_CODED_VALUE) <= 1.0 and float(value) != TOP_CODED_VALUE:
            record[name] = TOP_CODED_VALUE
    return record


# ---------------------------------------------------------------------------
# Row transform
# ---------------------------------------------------------------------------


def transform_row(
    raw: dict,
    ingested_at: datetime.datetime | None = None,
) -> dict:
    """Transform a single Bronze row into a Silver ``base.bls_oews`` row.

    Args:
        raw: A row dict read from ``bronze.bls_oews``.
        ingested_at: Override for the promotion timestamp. Defaults to
            ``datetime.datetime.now(tz=datetime.timezone.utc)``.

    Returns:
        A dict with the 13 Silver columns plus a deterministic ``record_id``.

    Raises:
        ValueError: When ``soc_code`` is missing or malformed (caller should
            log and skip per spec §Silver Transformations §1).
    """
    if ingested_at is None:
        ingested_at = datetime.datetime.now(tz=datetime.timezone.utc)

    soc_code = _validate_soc_code(raw.get("soc_code"))

    occupation_title = raw.get("occupation_title")
    if occupation_title is None or not str(occupation_title).strip():
        raise ValueError(f"Missing occupation_title for soc_code '{soc_code}'")
    occupation_title = str(occupation_title).strip()

    source_load_date = raw.get("load_date")
    if source_load_date is None:
        raise ValueError(f"Missing load_date for soc_code '{soc_code}'")

    wage_capped = raw.get("wage_capped")
    if wage_capped is None:
        wage_capped = False
    wage_capped = bool(wage_capped)

    record: dict = {
        "soc_code": soc_code,
        "occupation_title": occupation_title,
        "total_employment": raw.get("total_employment"),
        "wage_annual_p10": raw.get("wage_annual_p10"),
        "wage_annual_p25": raw.get("wage_annual_p25"),
        "wage_annual_median": raw.get("wage_annual_median"),
        "wage_annual_p75": raw.get("wage_annual_p75"),
        "wage_annual_p90": raw.get("wage_annual_p90"),
        "wage_annual_mean": raw.get("wage_annual_mean"),
        "wage_capped": wage_capped,
        "source_load_date": source_load_date,
        "ingested_at": ingested_at,
    }

    # Normalize top-coded percentiles to exactly 239200 (floating-point guard).
    normalize_top_code(record)

    # Monotonicity check (log only; do NOT skip — spec leaves this to the
    # Silver DQ rule SLV-OEWS-005).
    violations = check_monotonicity(record)
    if violations:
        logger.warning(
            "Monotonicity violation for soc_code=%s: %s",
            soc_code,
            "; ".join(violations),
        )

    record["record_id"] = compute_grain_id(record, GRAIN_FIELDS, prefix=GRAIN_PREFIX)
    return record


def transform_rows(
    bronze_rows: list[dict],
    ingested_at: datetime.datetime | None = None,
) -> list[dict]:
    """Transform every Bronze row into a Silver row.

    Rows with malformed or missing required fields (soc_code, occupation_title,
    load_date) are logged and skipped per spec §Silver Transformations §1.
    Rows with monotonicity issues are NOT skipped — the violation is logged
    and the row is still promoted, so the Silver DQ rule has a chance to fail
    loudly.
    """
    if ingested_at is None:
        ingested_at = datetime.datetime.now(tz=datetime.timezone.utc)

    silver_rows: list[dict] = []
    rows_skipped = 0
    for raw in bronze_rows:
        try:
            silver_rows.append(transform_row(raw, ingested_at=ingested_at))
        except ValueError as exc:
            rows_skipped += 1
            logger.warning(
                "Skipping malformed Bronze row (soc_code=%r): %s",
                raw.get("soc_code"),
                exc,
            )

    if rows_skipped:
        logger.warning("Skipped %d malformed Bronze rows", rows_skipped)

    # Uniqueness guard — promote also dedups, but failing here gives a
    # clearer error than a silent dedup skip.
    seen: set[str] = set()
    for row in silver_rows:
        if row["soc_code"] in seen:
            raise ValueError(f"Duplicate soc_code in Silver rows: {row['soc_code']}")
        seen.add(row["soc_code"])

    return silver_rows


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------


def promote_bls_oews(
    project_dir: str | Path | None = None,
    bronze_warehouse: str | Path | None = None,
    silver_warehouse: str | Path | None = None,
    catalog_path: str | Path | None = None,
    ingested_at: datetime.datetime | None = None,
) -> dict:
    """Run the Silver zone transformation for ``base.bls_oews``.

    Reads ``bronze.bls_oews`` from the Bronze zone, transforms ~831 rows, and
    promotes to ``base.bls_oews`` via the idempotent promote pattern.

    Args:
        project_dir: Project root.  Defaults to current working directory.
        bronze_warehouse: Override for the Bronze Iceberg warehouse path.
        silver_warehouse: Override for the Silver Iceberg warehouse path.
        catalog_path: Override for the shared SQLite catalog DB path.
        ingested_at: Override for the promotion timestamp.

    Returns:
        Run-metric dict: ``rows_read``, ``rows_transformed``,
        ``rows_skipped_transform``, ``promoted``, ``skipped_dedup``,
        ``snapshot_id``.
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

    if ingested_at is None:
        ingested_at = datetime.datetime.now(tz=datetime.timezone.utc)

    # Read Bronze
    logger.info("Reading from bronze.bls_oews...")
    bronze_catalog = get_catalog(bronze_warehouse, catalog_path)
    bronze_table = bronze_catalog.load_table("bronze.bls_oews")
    bronze_rows = read_with_duckdb(bronze_table)
    logger.info("Read %d rows from bronze.bls_oews", len(bronze_rows))

    # Transform
    logger.info("Transforming to Silver base table...")
    silver_rows = transform_rows(bronze_rows, ingested_at=ingested_at)
    rows_skipped_transform = len(bronze_rows) - len(silver_rows)
    logger.info(
        "Transformed %d rows (%d skipped malformed)",
        len(silver_rows),
        rows_skipped_transform,
    )

    # Capped distribution (informational log — DQ rules cover invariants).
    capped_count = sum(1 for r in silver_rows if r.get("wage_capped"))
    logger.info("wage_capped distribution: %d capped, %d uncapped",
                capped_count, len(silver_rows) - capped_count)

    # Promote to Silver
    logger.info("Promoting to base.bls_oews...")
    silver_catalog = get_catalog(silver_warehouse, catalog_path)
    silver_table = get_or_create_table(
        silver_catalog, "base", "bls_oews", get_silver_schema()
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
        "rows_skipped_transform": rows_skipped_transform,
        "promoted": result["promoted"],
        "skipped_dedup": result["skipped"],
        "snapshot_id": result.get("snapshot_id"),
        "wage_capped_count": capped_count,
    }


def transform(project_dir: str | Path | None = None) -> dict:
    """Manifest entry point — thin wrapper around ``promote_bls_oews``."""
    return promote_bls_oews(project_dir=project_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    result = transform()
    print(f"Silver transform complete: {result}")
