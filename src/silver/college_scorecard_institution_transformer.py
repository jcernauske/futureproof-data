"""Silver zone transformer for College Scorecard institution-level data.

Reads raw.college_scorecard_institution from the Bronze zone and produces
base.college_scorecard_institution with unified cost-of-attendance, unified
net price (with control-based public/private routing), unified net price by
income quintile, 4-year total derivations, and raw field pass-through for
provenance. Idempotent promotion via the Brightsmith promote pattern.

Per governance/models/silver-base-college-scorecard-institution-physical.md.
"""

import datetime
import logging
from pathlib import Path
from typing import Any

from pyiceberg.schema import Schema
from pyiceberg.types import (
    DateType,
    DoubleType,
    LongType,
    NestedField,
    StringType,
    TimestampType,
)

from brightsmith.infra.grain import compute_grain_id
from brightsmith.infra.iceberg_setup import get_catalog, get_or_create_table, read_with_duckdb
from brightsmith.infra.promote import promote

logger = logging.getLogger(__name__)

# Institution control integer -> human-readable label. Bronze DQ constrains
# control to {1, 2, 3}; anything else is unexpected and yields None.
CONTROL_LABELS: dict[int, str] = {
    1: "Public",
    2: "Private nonprofit",
    3: "Private for-profit",
}

# Grain: institution (UNITID). One row per institution.
GRAIN_FIELDS: list[str] = ["unitid"]
GRAIN_PREFIX: str = "csi"
SPEC_NAME: str = "silver-base-college-scorecard-institution"


def get_silver_schema() -> Schema:
    """Iceberg schema for base.college_scorecard_institution.

    Field IDs match governance/models/silver-base-college-scorecard-institution-physical.md
    and must not be reassigned even across schema evolution.
    """
    return Schema(
        # Core identity
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "unitid", LongType(), required=True),
        NestedField(3, "institution_name", StringType(), required=True),
        NestedField(4, "state_abbr", StringType(), required=True),
        NestedField(5, "institution_control", StringType(), required=True),
        # Unified cost of attendance
        NestedField(6, "cost_of_attendance_annual", DoubleType(), required=False),
        NestedField(7, "cost_of_attendance_4yr", DoubleType(), required=False),
        # Unified net price
        NestedField(8, "net_price_annual", DoubleType(), required=False),
        NestedField(9, "net_price_4yr", DoubleType(), required=False),
        # Unified net price by income quintile
        NestedField(10, "net_price_q1", DoubleType(), required=False),
        NestedField(11, "net_price_q2", DoubleType(), required=False),
        NestedField(12, "net_price_q3", DoubleType(), required=False),
        NestedField(13, "net_price_q4", DoubleType(), required=False),
        NestedField(14, "net_price_q5", DoubleType(), required=False),
        # Tuition structure
        NestedField(15, "tuition_in_state", DoubleType(), required=False),
        NestedField(16, "tuition_out_of_state", DoubleType(), required=False),
        # Living cost estimate
        NestedField(17, "room_board_on_campus", DoubleType(), required=False),
        NestedField(18, "room_board_off_campus", DoubleType(), required=False),
        NestedField(19, "books_supplies", DoubleType(), required=False),
        # Raw COA pass-through (provenance)
        NestedField(20, "costt4_a_raw", DoubleType(), required=False),
        NestedField(21, "costt4_p_raw", DoubleType(), required=False),
        # Raw average net price pass-through (provenance)
        NestedField(22, "npt4_pub_raw", DoubleType(), required=False),
        NestedField(23, "npt4_priv_raw", DoubleType(), required=False),
        # Raw public quintile pass-through (provenance)
        NestedField(24, "npt41_pub_raw", DoubleType(), required=False),
        NestedField(25, "npt42_pub_raw", DoubleType(), required=False),
        NestedField(26, "npt43_pub_raw", DoubleType(), required=False),
        NestedField(27, "npt44_pub_raw", DoubleType(), required=False),
        NestedField(28, "npt45_pub_raw", DoubleType(), required=False),
        # Raw private quintile pass-through (provenance)
        NestedField(29, "npt41_priv_raw", DoubleType(), required=False),
        NestedField(30, "npt42_priv_raw", DoubleType(), required=False),
        NestedField(31, "npt43_priv_raw", DoubleType(), required=False),
        NestedField(32, "npt44_priv_raw", DoubleType(), required=False),
        NestedField(33, "npt45_priv_raw", DoubleType(), required=False),
        # Pipeline metadata
        NestedField(34, "source_load_date", DateType(), required=True),
        NestedField(35, "ingested_at", TimestampType(), required=True),
    )


def map_control_label(control: Any) -> str | None:
    """Map integer institution control to human-readable label.

    Per physical model: 1 -> 'Public', 2 -> 'Private nonprofit',
    3 -> 'Private for-profit'. Returns None for null or unexpected values
    so downstream DQ rules can flag them rather than crashing the transform.
    """
    if control is None:
        return None
    try:
        key = int(control)
    except (ValueError, TypeError):
        return None
    return CONTROL_LABELS.get(key)


def pick_by_control(control: Any, pub_val: float | None, priv_val: float | None) -> float | None:
    """Route a measure to the pub vs. priv variant based on institution control.

    control == 1 -> public value; control in {2, 3} -> private value.
    Returns None if control is null or unexpected (so missing control does
    not silently collapse to the private branch).
    """
    if control is None:
        return None
    try:
        key = int(control)
    except (ValueError, TypeError):
        return None
    if key == 1:
        return pub_val
    if key in (2, 3):
        return priv_val
    return None


def multiply_or_none(value: float | None, factor: float) -> float | None:
    """Null-propagating multiplication used for the 4-year derivations."""
    if value is None:
        return None
    return value * factor


def transform_row(raw: dict) -> dict | None:
    """Transform a single raw row into a Silver base row.

    Returns None if the row fails validation (missing required grain/identity
    fields or an unmappable control value). Callers should count skips and
    log them for operator visibility.
    """
    unitid = raw.get("unitid")
    if unitid is None:
        return None

    instnm = raw.get("instnm")
    stabbr = raw.get("stabbr")
    if not instnm or not stabbr:
        return None

    control_raw = raw.get("control")
    institution_control = map_control_label(control_raw)
    if institution_control is None:
        # Required field per physical model. Skip rows we cannot classify so
        # the table-level NOT NULL + domain constraint always holds.
        return None

    costt4_a = raw.get("costt4_a")
    costt4_p = raw.get("costt4_p")
    npt4_pub = raw.get("npt4_pub")
    npt4_priv = raw.get("npt4_priv")

    # Unified COA: prefer academic-year, fall back to program-year.
    cost_of_attendance_annual = costt4_a if costt4_a is not None else costt4_p
    cost_of_attendance_4yr = multiply_or_none(cost_of_attendance_annual, 4)

    # Unified net price: control-based routing.
    net_price_annual = pick_by_control(control_raw, npt4_pub, npt4_priv)
    net_price_4yr = multiply_or_none(net_price_annual, 4)

    # Unified quintile net price: same routing, per quintile.
    net_price_q1 = pick_by_control(control_raw, raw.get("npt41_pub"), raw.get("npt41_priv"))
    net_price_q2 = pick_by_control(control_raw, raw.get("npt42_pub"), raw.get("npt42_priv"))
    net_price_q3 = pick_by_control(control_raw, raw.get("npt43_pub"), raw.get("npt43_priv"))
    net_price_q4 = pick_by_control(control_raw, raw.get("npt44_pub"), raw.get("npt44_priv"))
    net_price_q5 = pick_by_control(control_raw, raw.get("npt45_pub"), raw.get("npt45_priv"))

    record: dict = {
        # Core identity
        "unitid": unitid,
        "institution_name": instnm,
        "state_abbr": stabbr,
        "institution_control": institution_control,
        # Unified COA
        "cost_of_attendance_annual": cost_of_attendance_annual,
        "cost_of_attendance_4yr": cost_of_attendance_4yr,
        # Unified net price
        "net_price_annual": net_price_annual,
        "net_price_4yr": net_price_4yr,
        # Unified quintiles
        "net_price_q1": net_price_q1,
        "net_price_q2": net_price_q2,
        "net_price_q3": net_price_q3,
        "net_price_q4": net_price_q4,
        "net_price_q5": net_price_q5,
        # Tuition structure
        "tuition_in_state": raw.get("tuitionfee_in"),
        "tuition_out_of_state": raw.get("tuitionfee_out"),
        # Living cost estimate
        "room_board_on_campus": raw.get("roomboard_on"),
        "room_board_off_campus": raw.get("roomboard_off"),
        "books_supplies": raw.get("booksupply"),
        # Raw COA pass-through
        "costt4_a_raw": costt4_a,
        "costt4_p_raw": costt4_p,
        # Raw average net price pass-through
        "npt4_pub_raw": npt4_pub,
        "npt4_priv_raw": npt4_priv,
        # Raw public quintile pass-through
        "npt41_pub_raw": raw.get("npt41_pub"),
        "npt42_pub_raw": raw.get("npt42_pub"),
        "npt43_pub_raw": raw.get("npt43_pub"),
        "npt44_pub_raw": raw.get("npt44_pub"),
        "npt45_pub_raw": raw.get("npt45_pub"),
        # Raw private quintile pass-through
        "npt41_priv_raw": raw.get("npt41_priv"),
        "npt42_priv_raw": raw.get("npt42_priv"),
        "npt43_priv_raw": raw.get("npt43_priv"),
        "npt44_priv_raw": raw.get("npt44_priv"),
        "npt45_priv_raw": raw.get("npt45_priv"),
        # Pipeline metadata
        "source_load_date": raw.get("load_date"),
        "ingested_at": datetime.datetime.now(tz=datetime.timezone.utc),
    }
    record["record_id"] = compute_grain_id(record, GRAIN_FIELDS, prefix=GRAIN_PREFIX)
    return record


def transform(
    project_dir: str | Path | None = None,
) -> dict:
    """Run the Silver zone transformation.

    Reads raw.college_scorecard_institution from Bronze, transforms, and
    promotes to base.college_scorecard_institution via the idempotent
    promote pattern.

    Returns:
        {
            "rows_read": N,
            "rows_transformed": T,
            "rows_skipped_transform": S,
            "promoted": P,
            "skipped_dedup": D,
            "snapshot_id": ...,
        }
    """
    project_dir = Path(project_dir or ".").resolve()

    bronze_warehouse = project_dir / "data" / "bronze" / "iceberg_warehouse"
    bronze_catalog_path = project_dir / "data" / "catalog" / "catalog.db"
    silver_warehouse = project_dir / "data" / "silver" / "iceberg_warehouse"
    silver_catalog_path = project_dir / "data" / "catalog" / "catalog.db"

    # Read from Bronze
    logger.info("Reading from bronze.college_scorecard_institution...")
    bronze_catalog = get_catalog(bronze_warehouse, bronze_catalog_path)
    bronze_table = bronze_catalog.load_table("bronze.college_scorecard_institution")
    raw_rows = read_with_duckdb(bronze_table)
    logger.info("Read %d rows from Bronze", len(raw_rows))

    # Transform
    logger.info("Transforming to Silver base table...")
    silver_rows: list[dict] = []
    skipped = 0
    for raw in raw_rows:
        record = transform_row(raw)
        if record is None:
            skipped += 1
            continue
        silver_rows.append(record)

    if skipped:
        logger.warning("Skipped %d rows with null/invalid required fields", skipped)
    logger.info("Transformed %d rows", len(silver_rows))

    # Promote to Silver
    logger.info("Promoting to base.college_scorecard_institution...")
    silver_catalog = get_catalog(silver_warehouse, silver_catalog_path)
    silver_table = get_or_create_table(
        silver_catalog,
        "base",
        "college_scorecard_institution",
        get_silver_schema(),
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
        "rows_read": len(raw_rows),
        "rows_transformed": len(silver_rows),
        "rows_skipped_transform": skipped,
        "promoted": result["promoted"],
        "skipped_dedup": result["skipped"],
        "snapshot_id": result.get("snapshot_id"),
    }
