"""Silver zone transformer for College Scorecard base table.

Reads raw.college_scorecard from the Bronze zone and produces base.college_scorecard
with normalized CIP codes, business-meaningful column names, derived fields, and
idempotent promotion via the Brightsmith promote pattern.
"""

import datetime
import logging
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

# CIP 2-digit family descriptions (CIP 2020 taxonomy)
CIP_FAMILIES: dict[str, str] = {
    "01": "Agriculture, Agriculture Operations, and Related Sciences",
    "03": "Natural Resources and Conservation",
    "04": "Architecture and Related Services",
    "05": "Area, Ethnic, Cultural, Gender, and Group Studies",
    "09": "Communication, Journalism, and Related Programs",
    "10": "Communications Technologies/Technicians and Support Services",
    "11": "Computer and Information Sciences and Support Services",
    "12": "Personal and Culinary Services",
    "13": "Education",
    "14": "Engineering",
    "15": "Engineering Technologies and Engineering-Related Fields",
    "16": "Foreign Languages, Literatures, and Linguistics",
    "19": "Family and Consumer Sciences/Human Sciences",
    "22": "Legal Professions and Studies",
    "23": "English Language and Literature/Letters",
    "24": "Liberal Arts and Sciences, General Studies and Humanities",
    "25": "Library Science",
    "26": "Biological and Biomedical Sciences",
    "27": "Mathematics and Statistics",
    "28": "Military Science, Leadership and Operational Art",
    "29": "Military Technologies and Applied Sciences",
    "30": "Multi/Interdisciplinary Studies",
    "31": "Parks, Recreation, Leisure, and Fitness Studies",
    "32": "Basic Skills and Developmental/Remedial Education",
    "33": "Citizenship Activities",
    "34": "Health-Related Knowledge and Skills",
    "35": "Interpersonal and Social Skills",
    "36": "Leisure and Recreational Activities",
    "38": "Philosophy and Religious Studies",
    "39": "Theology and Religious Vocations",
    "40": "Physical Sciences",
    "41": "Science Technologies/Technicians",
    "42": "Psychology",
    "43": "Homeland Security, Law Enforcement, Firefighting and Related Protective Services",
    "44": "Public Administration and Social Service Professions",
    "45": "Social Sciences",
    "46": "Construction Trades",
    "47": "Mechanic and Repair Technologies/Technicians",
    "48": "Precision Production",
    "49": "Transportation and Materials Moving",
    "50": "Visual and Performing Arts",
    "51": "Health Professions and Related Programs",
    "52": "Business, Management, Marketing, and Related Support Services",
    "53": "High School/Secondary Diplomas and Certificates",
    "54": "History",
}

# Institution control type mapping
CONTROL_MAP: dict[str, str] = {
    "1": "Public",
    "2": "Private nonprofit",
    "3": "Private for-profit",
    "Public": "Public",
    "Private nonprofit": "Private nonprofit",
    "Private not-for-profit": "Private nonprofit",
    "Private for-profit": "Private for-profit",
}

GRAIN_FIELDS = ["unitid", "cipcode", "credential_level"]
SPEC_NAME = "silver-base-college-scorecard"


def get_silver_schema() -> Schema:
    """Iceberg schema for base.college_scorecard."""
    return Schema(
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "unitid", LongType(), required=True),
        NestedField(3, "institution_name", StringType(), required=True),
        NestedField(4, "institution_control", StringType(), required=False),
        NestedField(5, "cipcode", StringType(), required=True),
        NestedField(6, "program_name", StringType(), required=True),
        NestedField(7, "cip_family", StringType(), required=True),
        NestedField(8, "cip_family_name", StringType(), required=True),
        NestedField(9, "credential_level", IntegerType(), required=True),
        NestedField(10, "credential_description", StringType(), required=True),
        NestedField(11, "earnings_1yr_median", DoubleType(), required=False),
        NestedField(12, "earnings_2yr_median", DoubleType(), required=False),
        NestedField(13, "debt_median", DoubleType(), required=False),
        NestedField(14, "completions_count_1", LongType(), required=False),
        NestedField(15, "completions_count_2", LongType(), required=False),
        NestedField(16, "small_cohort_flag", BooleanType(), required=True),
        NestedField(17, "source_load_date", DateType(), required=True),
        NestedField(18, "ingested_at", TimestampType(), required=True),
    )


def normalize_cipcode(raw_code: str) -> str:
    """Insert dot at position 2 to normalize 4-digit CIP to XX.XXXX format.

    Handles both 4-digit ("5202" -> "52.02") and already-normalized
    ("52.02" -> "52.02") inputs.
    """
    if "." in raw_code:
        return raw_code
    if len(raw_code) == 4:
        return f"{raw_code[:2]}.{raw_code[2:]}"
    return raw_code


def transform_row(raw: dict) -> dict | None:
    """Transform a single raw row into a Silver base row.

    Returns None if the row fails validation (missing grain fields).
    """
    unitid = raw.get("unitid")
    cipcode_raw = raw.get("cipcode")
    credlev = raw.get("credlev")

    if unitid is None or cipcode_raw is None or credlev is None:
        return None

    cipcode = normalize_cipcode(str(cipcode_raw))
    cip_family = cipcode[:2]
    cip_family_name = CIP_FAMILIES.get(cip_family, f"Unknown CIP Family ({cip_family})")

    control_raw = raw.get("control")
    institution_control = None
    if control_raw is not None:
        institution_control = CONTROL_MAP.get(str(control_raw).strip())

    completions_1 = raw.get("ipedscount1")
    small_cohort = completions_1 is None or completions_1 < 30

    record = {
        "unitid": unitid,
        "institution_name": raw.get("instnm", ""),
        "institution_control": institution_control,
        "cipcode": cipcode,
        "program_name": raw.get("cipdesc", ""),
        "cip_family": cip_family,
        "cip_family_name": cip_family_name,
        "credential_level": credlev,
        "credential_description": raw.get("creddesc", ""),
        "earnings_1yr_median": raw.get("earn_mdn_hi_1yr"),
        "earnings_2yr_median": raw.get("earn_mdn_hi_2yr"),
        "debt_median": raw.get("debt_all_stgp_eval_mdn"),
        "completions_count_1": completions_1,
        "completions_count_2": raw.get("ipedscount2"),
        "small_cohort_flag": small_cohort,
        "source_load_date": raw.get("load_date"),
        "ingested_at": datetime.datetime.now(tz=datetime.timezone.utc),
    }
    record["record_id"] = compute_grain_id(record, GRAIN_FIELDS, prefix="cs")
    return record


def transform(
    project_dir: str | Path | None = None,
) -> dict:
    """Run the Silver zone transformation.

    Reads raw.college_scorecard from Bronze, transforms, and promotes to
    base.college_scorecard via idempotent promote pattern.

    Returns:
        {"rows_read": N, "promoted": M, "skipped": S}
    """
    project_dir = Path(project_dir or ".").resolve()

    bronze_warehouse = project_dir / "data" / "bronze" / "iceberg_warehouse"
    bronze_catalog_path = project_dir / "data" / "catalog" / "catalog.db"
    silver_warehouse = project_dir / "data" / "silver" / "iceberg_warehouse"
    silver_catalog_path = project_dir / "data" / "catalog" / "catalog.db"

    # Read from Bronze
    logger.info("Reading from bronze.college_scorecard...")
    bronze_catalog = get_catalog(bronze_warehouse, bronze_catalog_path)
    bronze_table = bronze_catalog.load_table("bronze.college_scorecard")
    raw_rows = read_with_duckdb(bronze_table)
    logger.info("Read %d rows from Bronze", len(raw_rows))

    # Transform
    logger.info("Transforming to Silver base table...")
    silver_rows = []
    skipped = 0
    for raw in raw_rows:
        record = transform_row(raw)
        if record is None:
            skipped += 1
            continue
        silver_rows.append(record)

    if skipped:
        logger.warning("Skipped %d rows with null grain fields", skipped)
    logger.info("Transformed %d rows", len(silver_rows))

    # Promote to Silver
    logger.info("Promoting to base.college_scorecard...")
    silver_catalog = get_catalog(silver_warehouse, silver_catalog_path)
    silver_table = get_or_create_table(
        silver_catalog, "base", "college_scorecard", get_silver_schema()
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
