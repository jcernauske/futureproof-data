"""Silver zone transformer for CIP-SOC crosswalk base table.

Reads raw.cip_soc_crosswalk from the Bronze zone and produces
base.cip_soc_crosswalk with validated codes, derived classification
fields, cross-table match flags, and match quality classification.

This is the bridge table that connects College Scorecard programs (CIP)
to BLS OOH and O*NET occupations (SOC).
"""

import datetime
import logging
import re
from pathlib import Path

from pyiceberg.schema import Schema
from pyiceberg.types import (
    BooleanType,
    DateType,
    NestedField,
    StringType,
    TimestampType,
)

from brightsmith.infra.grain import compute_grain_id
from brightsmith.infra.iceberg_setup import get_catalog, get_or_create_table, read_with_duckdb
from brightsmith.infra.promote import promote

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SPEC_NAME = "crosswalk-cip-soc"
GRAIN_FIELDS = ["cipcode", "soc_code"]

_CIP_PATTERN = re.compile(r"^\d{2}\.\d{4}$")
_SOC_PATTERN = re.compile(r"^\d{2}-\d{4}$")

VALID_SOC_MAJOR_GROUPS: frozenset[str] = frozenset({
    "11", "13", "15", "17", "19", "21", "23", "25", "27", "29",
    "31", "33", "35", "37", "39", "41", "43", "45", "47", "49",
    "51", "53", "55",
})

VALID_MATCH_QUALITIES: frozenset[str] = frozenset({
    "full", "partial_no_onet", "partial_no_bls", "scorecard_only", "no_scorecard",
})


def get_silver_schema() -> Schema:
    """Iceberg schema for base.cip_soc_crosswalk."""
    return Schema(
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "cipcode", StringType(), required=True),
        NestedField(3, "cip_title", StringType(), required=True),
        NestedField(4, "cip_family", StringType(), required=True),
        NestedField(5, "soc_code", StringType(), required=True),
        NestedField(6, "soc_title", StringType(), required=True),
        NestedField(7, "soc_major_group", StringType(), required=True),
        NestedField(8, "has_scorecard_match", BooleanType(), required=True),
        NestedField(9, "has_bls_match", BooleanType(), required=True),
        NestedField(10, "has_onet_match", BooleanType(), required=True),
        NestedField(11, "match_quality", StringType(), required=True),
        NestedField(12, "source_load_date", DateType(), required=True),
        NestedField(13, "ingested_at", TimestampType(), required=True),
    )


def derive_match_quality(
    has_scorecard: bool,
    has_bls: bool,
    has_onet: bool,
) -> str:
    """Derive match_quality from the three cross-table match flags.

    Implements the exhaustive 5-tier CASE expression from the spec.
    """
    if not has_scorecard:
        return "no_scorecard"
    if has_scorecard and has_bls and has_onet:
        return "full"
    if has_scorecard and has_bls and not has_onet:
        return "partial_no_onet"
    if has_scorecard and not has_bls and has_onet:
        return "partial_no_bls"
    # has_scorecard and not has_bls and not has_onet
    return "scorecard_only"


def transform_row(
    raw: dict,
    scorecard_cips: set[str],
    bls_socs: set[str],
    onet_socs: set[str],
) -> dict | None:
    """Transform a single Bronze crosswalk row into a Silver base row.

    Returns None if the row should be filtered (soc_code = '99-9999')
    or fails validation.

    Args:
        raw: A row from raw.cip_soc_crosswalk.
        scorecard_cips: Set of distinct cipcode values from base.college_scorecard.
        bls_socs: Set of distinct soc_code values from base.bls_ooh.
        onet_socs: Set of distinct bls_soc_code values from base.onet_occupations.

    Returns:
        Transformed dict or None if filtered/invalid.
    """
    cipcode = raw.get("cipcode")
    soc_code = raw.get("soc_code")

    if cipcode is None or soc_code is None:
        return None

    cipcode = str(cipcode).strip()
    soc_code = str(soc_code).strip()

    # Filter out "no match" sentinel rows
    if soc_code == "99-9999":
        return None

    # Validate CIP format
    if not _CIP_PATTERN.match(cipcode):
        logger.warning("Invalid CIP format: '%s' -- skipping", cipcode)
        return None

    # Validate SOC format
    if not _SOC_PATTERN.match(soc_code):
        logger.warning("Invalid SOC format: '%s' -- skipping", soc_code)
        return None

    # Derive classification fields
    cip_family = cipcode[:2]
    soc_major_group = soc_code[:2]

    # Validate SOC major group
    if soc_major_group not in VALID_SOC_MAJOR_GROUPS:
        logger.warning(
            "Invalid SOC major group '%s' from code '%s' -- skipping",
            soc_major_group, soc_code,
        )
        return None

    # Cross-table match flags
    has_scorecard_match = cipcode in scorecard_cips
    has_bls_match = soc_code in bls_socs
    has_onet_match = soc_code in onet_socs

    # Derive match quality
    match_quality = derive_match_quality(
        has_scorecard_match, has_bls_match, has_onet_match
    )

    record = {
        "cipcode": cipcode,
        "cip_title": raw.get("cip_title", ""),
        "cip_family": cip_family,
        "soc_code": soc_code,
        "soc_title": raw.get("soc_title", ""),
        "soc_major_group": soc_major_group,
        "has_scorecard_match": has_scorecard_match,
        "has_bls_match": has_bls_match,
        "has_onet_match": has_onet_match,
        "match_quality": match_quality,
        "source_load_date": raw.get("load_date"),
        "ingested_at": datetime.datetime.now(tz=datetime.timezone.utc),
    }
    record["record_id"] = compute_grain_id(record, GRAIN_FIELDS, prefix="xw")
    return record


def _load_scorecard_cips(catalog) -> set[str]:
    """Load distinct cipcode values from base.college_scorecard.

    Returns an empty set if the table does not exist.
    """
    try:
        table = catalog.load_table("base.college_scorecard")
        rows = read_with_duckdb(table)
        return {r["cipcode"] for r in rows if r.get("cipcode")}
    except Exception:
        logger.warning("Could not load base.college_scorecard -- has_scorecard_match will be False")
        return set()


def _load_bls_socs(catalog) -> set[str]:
    """Load distinct soc_code values from base.bls_ooh.

    Returns an empty set if the table does not exist.
    """
    try:
        table = catalog.load_table("base.bls_ooh")
        rows = read_with_duckdb(table)
        return {r["soc_code"] for r in rows if r.get("soc_code")}
    except Exception:
        logger.warning("Could not load base.bls_ooh -- has_bls_match will be False")
        return set()


def _load_onet_socs(catalog) -> set[str]:
    """Load distinct bls_soc_code values from base.onet_occupations.

    Returns an empty set if the table does not exist.
    """
    try:
        table = catalog.load_table("base.onet_occupations")
        rows = read_with_duckdb(table)
        return {r["bls_soc_code"] for r in rows if r.get("bls_soc_code")}
    except Exception:
        logger.warning("Could not load base.onet_occupations -- has_onet_match will be False")
        return set()


def transform(
    project_dir: str | Path | None = None,
) -> dict:
    """Run the Silver zone transformation for CIP-SOC crosswalk.

    Reads raw.cip_soc_crosswalk from Bronze, filters, validates, enriches
    with cross-table match flags, and promotes to base.cip_soc_crosswalk
    via the idempotent promote pattern.

    Returns:
        {"rows_read": N, "rows_transformed": M, "promoted": P, ...}
    """
    project_dir = Path(project_dir or ".").resolve()

    bronze_warehouse = project_dir / "data" / "bronze" / "iceberg_warehouse"
    bronze_catalog_path = project_dir / "data" / "catalog" / "catalog.db"
    silver_warehouse = project_dir / "data" / "silver" / "iceberg_warehouse"
    silver_catalog_path = project_dir / "data" / "catalog" / "catalog.db"

    # Read from Bronze
    logger.info("Reading from raw.cip_soc_crosswalk...")
    bronze_catalog = get_catalog(bronze_warehouse, bronze_catalog_path)
    bronze_table = bronze_catalog.load_table("raw.cip_soc_crosswalk")
    raw_rows = read_with_duckdb(bronze_table)
    logger.info("Read %d rows from Bronze", len(raw_rows))

    # Load cross-table lookup sets from Silver
    silver_catalog = get_catalog(silver_warehouse, silver_catalog_path)
    scorecard_cips = _load_scorecard_cips(silver_catalog)
    bls_socs = _load_bls_socs(silver_catalog)
    onet_socs = _load_onet_socs(silver_catalog)
    logger.info(
        "Loaded lookup sets: %d scorecard CIPs, %d BLS SOCs, %d O*NET SOCs",
        len(scorecard_cips), len(bls_socs), len(onet_socs),
    )

    # Transform
    logger.info("Transforming to Silver base table...")
    silver_rows = []
    filtered = 0
    for raw in raw_rows:
        record = transform_row(raw, scorecard_cips, bls_socs, onet_socs)
        if record is None:
            filtered += 1
            continue
        silver_rows.append(record)

    logger.info(
        "Transformed %d rows (%d filtered/invalid)",
        len(silver_rows), filtered,
    )

    # Promote to Silver
    logger.info("Promoting to base.cip_soc_crosswalk...")
    silver_table = get_or_create_table(
        silver_catalog, "base", "cip_soc_crosswalk", get_silver_schema()
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
        "rows_filtered": filtered,
        "promoted": result["promoted"],
        "skipped_dedup": result["skipped"],
        "snapshot_id": result.get("snapshot_id"),
    }
