"""Silver zone transformer for BLS Occupational Outlook Handbook base table.

Reads bronze.bls_ooh from the Bronze zone and produces base.bls_ooh
with SOC major group classification, broad occupation and catchall flags,
growth category bucketing, and idempotent promotion via the Brightsmith
promote pattern.
"""

import datetime
import logging
import re
from pathlib import Path

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
from brightsmith.infra.iceberg_setup import get_catalog, get_or_create_table, read_with_duckdb
from brightsmith.infra.promote import promote

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

SOC_MAJOR_GROUP_LOOKUP: dict[str, str] = {
    "11": "Management",
    "13": "Business and Financial Operations",
    "15": "Computer and Mathematical",
    "17": "Architecture and Engineering",
    "19": "Life, Physical, and Social Science",
    "21": "Community and Social Service",
    "23": "Legal",
    "25": "Educational Instruction and Library",
    "27": "Arts, Design, Entertainment, Sports, and Media",
    "29": "Healthcare Practitioners and Technical",
    "31": "Healthcare Support",
    "33": "Protective Service",
    "35": "Food Preparation and Serving Related",
    "37": "Building and Grounds Cleaning and Maintenance",
    "39": "Personal Care and Service",
    "41": "Sales and Related",
    "43": "Office and Administrative Support",
    "45": "Farming, Fishing, and Forestry",
    "47": "Construction and Extraction",
    "49": "Installation, Maintenance, and Repair",
    "51": "Production",
    "53": "Transportation and Material Moving",
}

EDUCATION_LEVEL_LOOKUP: dict[int, str] = {
    1: "Doctoral or professional degree",
    2: "Master's degree",
    3: "Bachelor's degree",
    4: "Associate's degree",
    5: "Postsecondary nondegree award",
    6: "Some college, no degree",
    7: "High school diploma or equivalent",
    8: "No formal educational credential",
}

# Hardcoded list of 7 rolled-up/broad occupation SOC codes from Bronze SOC audit.
# Do NOT pattern-match; see spec for rationale.
BROAD_OCCUPATION_CODES: frozenset[str] = frozenset({
    "13-1020",
    "13-2020",
    "29-2010",
    "31-1120",
    "39-7010",
    "47-4090",
    "51-2090",
})

GRAIN_FIELDS = ["soc_code"]
SPEC_NAME = "silver-base-bls-ooh"

_SOC_PATTERN = re.compile(r"^\d{2}-\d{4}$")


def get_silver_schema() -> Schema:
    """Iceberg schema for base.bls_ooh."""
    return Schema(
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "soc_code", StringType(), required=True),
        NestedField(3, "occupation_title", StringType(), required=True),
        NestedField(4, "soc_major_group", StringType(), required=True),
        NestedField(5, "soc_major_group_name", StringType(), required=True),
        NestedField(6, "broad_occupation_flag", BooleanType(), required=True),
        NestedField(7, "catchall_flag", BooleanType(), required=True),
        NestedField(8, "employment_current", LongType(), required=False),
        NestedField(9, "employment_projected", LongType(), required=False),
        NestedField(10, "employment_change", LongType(), required=False),
        NestedField(11, "employment_change_pct", DoubleType(), required=False),
        NestedField(12, "openings_annual_avg", LongType(), required=False),
        NestedField(13, "growth_category", StringType(), required=False),
        NestedField(14, "median_annual_wage", DoubleType(), required=False),
        NestedField(15, "median_wage_capped", BooleanType(), required=True),
        NestedField(16, "wage_available", BooleanType(), required=True),
        NestedField(17, "education_typical", StringType(), required=False),
        NestedField(18, "education_code", IntegerType(), required=False),
        NestedField(19, "education_level_name", StringType(), required=False),
        NestedField(20, "work_experience", StringType(), required=False),
        NestedField(21, "work_experience_code", IntegerType(), required=False),
        NestedField(22, "training_typical", StringType(), required=False),
        NestedField(23, "training_code", IntegerType(), required=False),
        NestedField(24, "source_load_date", DateType(), required=True),
        NestedField(25, "ingested_at", TimestampType(), required=True),
    )


def derive_growth_category(pct: float | None) -> str | None:
    """Bucket employment_change_pct into a growth category.

    Uses half-open intervals per the spec:
      < -10  => declining_fast
      < -1   => declining
      < 1    => stable
      < 10   => growing
      < 20   => growing_fast
      >= 20  => booming
      None   => None
    """
    if pct is None:
        return None
    if pct < -10.0:
        return "declining_fast"
    if pct < -1.0:
        return "declining"
    if pct < 1.0:
        return "stable"
    if pct < 10.0:
        return "growing"
    if pct < 20.0:
        return "growing_fast"
    return "booming"


def transform_row(raw: dict) -> dict:
    """Transform a single Bronze row into a Silver base row.

    Raises ValueError if the SOC code is missing or invalid.
    All Bronze rows are expected to be valid; this function does not
    silently skip bad data.
    """
    soc_code = raw.get("soc_code")
    if soc_code is None or not isinstance(soc_code, str) or not soc_code.strip():
        raise ValueError(f"Missing soc_code in row: {raw}")

    soc_code = soc_code.strip()
    if not _SOC_PATTERN.match(soc_code):
        raise ValueError(f"Invalid SOC code format: '{soc_code}' (expected XX-XXXX)")

    occupation_title = raw.get("occupation_title", "")
    if occupation_title is None:
        occupation_title = ""

    soc_major_group = soc_code[:2]
    soc_major_group_name = SOC_MAJOR_GROUP_LOOKUP.get(soc_major_group)
    if soc_major_group_name is None:
        raise ValueError(
            f"Unknown SOC major group '{soc_major_group}' from code '{soc_code}'"
        )

    broad_occupation_flag = soc_code in BROAD_OCCUPATION_CODES
    catchall_flag = "all other" in occupation_title.lower()

    employment_change_pct = raw.get("employment_change_pct")
    growth_category = derive_growth_category(employment_change_pct)

    median_annual_wage = raw.get("median_annual_wage")
    wage_available = median_annual_wage is not None

    education_code = raw.get("education_code")
    education_level_name = EDUCATION_LEVEL_LOOKUP.get(education_code) if education_code is not None else None

    record = {
        "soc_code": soc_code,
        "occupation_title": occupation_title,
        "soc_major_group": soc_major_group,
        "soc_major_group_name": soc_major_group_name,
        "broad_occupation_flag": broad_occupation_flag,
        "catchall_flag": catchall_flag,
        "employment_current": raw.get("employment_current"),
        "employment_projected": raw.get("employment_projected"),
        "employment_change": raw.get("employment_change"),
        "employment_change_pct": employment_change_pct,
        "openings_annual_avg": raw.get("openings_annual_avg"),
        "growth_category": growth_category,
        "median_annual_wage": median_annual_wage,
        "median_wage_capped": raw.get("median_wage_capped", False),
        "wage_available": wage_available,
        "education_typical": raw.get("education_typical"),
        "education_code": education_code,
        "education_level_name": education_level_name,
        "work_experience": raw.get("work_experience"),
        "work_experience_code": raw.get("work_experience_code"),
        "training_typical": raw.get("training_typical"),
        "training_code": raw.get("training_code"),
        "source_load_date": raw.get("load_date"),
        "ingested_at": datetime.datetime.now(tz=datetime.timezone.utc),
    }
    record["record_id"] = compute_grain_id(record, GRAIN_FIELDS, prefix="ooh")
    return record


def transform(
    project_dir: str | Path | None = None,
) -> dict:
    """Run the Silver zone transformation.

    Reads bronze.bls_ooh from Bronze, transforms, and promotes to
    base.bls_ooh via idempotent promote pattern.

    Returns:
        {"rows_read": N, "rows_transformed": M, "promoted": P, ...}
    """
    project_dir = Path(project_dir or ".").resolve()

    bronze_warehouse = project_dir / "data" / "bronze" / "iceberg_warehouse"
    bronze_catalog_path = project_dir / "data" / "catalog" / "catalog.db"
    silver_warehouse = project_dir / "data" / "silver" / "iceberg_warehouse"
    silver_catalog_path = project_dir / "data" / "catalog" / "catalog.db"

    # Read from Bronze
    logger.info("Reading from bronze.bls_ooh...")
    bronze_catalog = get_catalog(bronze_warehouse, bronze_catalog_path)
    bronze_table = bronze_catalog.load_table("bronze.bls_ooh")
    raw_rows = read_with_duckdb(bronze_table)
    logger.info("Read %d rows from Bronze", len(raw_rows))

    # Transform
    logger.info("Transforming to Silver base table...")
    silver_rows = []
    for raw in raw_rows:
        record = transform_row(raw)
        silver_rows.append(record)

    logger.info("Transformed %d rows", len(silver_rows))

    # Promote to Silver
    logger.info("Promoting to base.bls_ooh...")
    silver_catalog = get_catalog(silver_warehouse, silver_catalog_path)
    silver_table = get_or_create_table(
        silver_catalog, "base", "bls_ooh", get_silver_schema()
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
        "promoted": result["promoted"],
        "skipped_dedup": result["skipped"],
        "snapshot_id": result.get("snapshot_id"),
    }
