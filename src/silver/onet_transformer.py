"""Silver zone transformers for O*NET base tables.

Reads from raw.onet_* Bronze tables and produces four Silver base tables:
  1. base.onet_occupations      -- master occupation reference at BLS SOC level
  2. base.onet_activity_profiles -- work activity importance ratings (IM scale)
  3. base.onet_context_profiles  -- work context point estimates (CX/CT scales)
  4. base.onet_career_transitions -- career similarity graph

All tables use bls_soc_code (XX-XXXX) as the primary identifier, derived by
truncating O*NET-SOC codes (XX-XXXX.XX -> XX-XXXX). Multi-detail O*NET codes
are aggregated to BLS level via averaging (activities/context) or best-index
selection (transitions).
"""

import datetime
import json
import logging
from collections import defaultdict
from pathlib import Path

from pyiceberg.schema import Schema
from pyiceberg.types import (
    BooleanType,
    DateType,
    DoubleType,
    IntegerType,
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

SPEC_NAME = "silver-base-onet"

# EDA-corrected burnout element IDs (from governance/eda/silver-onet-eda.md)
BURNOUT_ELEMENT_IDS: frozenset[str] = frozenset({
    "4.C.3.d.1",    # Time Pressure (CX)
    "4.C.3.d.8",    # Duration of Typical Work Week (CT)
    "4.C.3.a.1",    # Consequence of Error (CX)
    "4.C.3.d.3",    # Pace Determined by Speed of Equipment (CX)
    "4.C.3.a.2.b",  # Frequency of Decision Making (CX)
    "4.C.3.b.4",    # Importance of Being Exact or Accurate (CX)
    "4.C.3.b.7",    # Importance of Repeating Same Tasks (CX)
    "4.C.3.d.4",    # Work Schedules (CT)
    "4.C.3.a.2.a",  # Impact of Decisions on Co-workers or Company Results (CX)
})


def truncate_to_bls_soc(onet_soc_code: str) -> str:
    """Truncate O*NET-SOC code (XX-XXXX.XX) to BLS SOC (XX-XXXX).

    Examples:
        "15-1252.00" -> "15-1252"
        "29-1229.01" -> "29-1229"
    """
    return onet_soc_code.split(".")[0]


def derive_relatedness_tier(index: int) -> str:
    """Derive relatedness tier from a best_index value (1-20)."""
    if index <= 5:
        return "Primary-Short"
    if index <= 10:
        return "Primary-Long"
    return "Supplemental"


# ---------------------------------------------------------------------------
# Iceberg Schemas
# ---------------------------------------------------------------------------

def get_occupations_schema() -> Schema:
    """Iceberg schema for base.onet_occupations (14 fields)."""
    return Schema(
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "bls_soc_code", StringType(), required=True),
        NestedField(3, "primary_title", StringType(), required=True),
        NestedField(4, "description", StringType(), required=True),
        NestedField(5, "onet_detail_codes", StringType(), required=True),
        NestedField(6, "onet_detail_count", IntegerType(), required=True),
        NestedField(7, "multi_detail_flag", BooleanType(), required=True),
        NestedField(8, "has_work_activities", BooleanType(), required=True),
        NestedField(9, "has_work_context", BooleanType(), required=True),
        NestedField(10, "has_tasks", BooleanType(), required=True),
        NestedField(11, "has_related", BooleanType(), required=True),
        NestedField(12, "data_completeness_tier", StringType(), required=True),
        NestedField(13, "source_load_date", DateType(), required=True),
        NestedField(14, "ingested_at", TimestampType(), required=True),
    )


def get_activity_profiles_schema() -> Schema:
    """Iceberg schema for base.onet_activity_profiles (11 fields)."""
    return Schema(
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "bls_soc_code", StringType(), required=True),
        NestedField(3, "element_id", StringType(), required=True),
        NestedField(4, "element_name", StringType(), required=True),
        NestedField(5, "importance", DoubleType(), required=True),
        NestedField(6, "importance_rank", IntegerType(), required=True),
        NestedField(7, "is_high_importance", BooleanType(), required=True),
        NestedField(8, "onet_details_averaged", IntegerType(), required=True),
        NestedField(9, "suppress_flag", BooleanType(), required=True),
        NestedField(10, "source_load_date", DateType(), required=True),
        NestedField(11, "ingested_at", TimestampType(), required=True),
    )


def get_context_profiles_schema() -> Schema:
    """Iceberg schema for base.onet_context_profiles (11 fields)."""
    return Schema(
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "bls_soc_code", StringType(), required=True),
        NestedField(3, "element_id", StringType(), required=True),
        NestedField(4, "element_name", StringType(), required=True),
        NestedField(5, "scale_id", StringType(), required=True),
        NestedField(6, "context_value", DoubleType(), required=True),
        NestedField(7, "is_burnout_element", BooleanType(), required=True),
        NestedField(8, "onet_details_averaged", IntegerType(), required=True),
        NestedField(9, "suppress_flag", BooleanType(), required=True),
        NestedField(10, "source_load_date", DateType(), required=True),
        NestedField(11, "ingested_at", TimestampType(), required=True),
    )


def get_career_transitions_schema() -> Schema:
    """Iceberg schema for base.onet_career_transitions (9 fields)."""
    return Schema(
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "bls_soc_code", StringType(), required=True),
        NestedField(3, "related_bls_soc_code", StringType(), required=True),
        NestedField(4, "best_index", IntegerType(), required=True),
        NestedField(5, "relatedness_tier", StringType(), required=True),
        NestedField(6, "is_primary", BooleanType(), required=True),
        NestedField(7, "relationship_type", StringType(), required=True),
        NestedField(8, "source_load_date", DateType(), required=True),
        NestedField(9, "ingested_at", TimestampType(), required=True),
    )


# ---------------------------------------------------------------------------
# Transformation logic
# ---------------------------------------------------------------------------

def _build_child_data_sets(
    wa_rows: list[dict],
    wc_rows: list[dict],
    ts_rows: list[dict],
    ro_rows: list[dict],
) -> dict[str, set[str]]:
    """Build lookup of which BLS SOCs have data in each child table.

    Returns dict with keys 'wa', 'wc', 'ts', 'ro', each mapping to a
    set of BLS SOC codes that have at least one row in that table.
    """
    result: dict[str, set[str]] = {"wa": set(), "wc": set(), "ts": set(), "ro": set()}
    for row in wa_rows:
        result["wa"].add(truncate_to_bls_soc(row["onet_soc_code"]))
    for row in wc_rows:
        result["wc"].add(truncate_to_bls_soc(row["onet_soc_code"]))
    for row in ts_rows:
        result["ts"].add(truncate_to_bls_soc(row["onet_soc_code"]))
    for row in ro_rows:
        result["ro"].add(truncate_to_bls_soc(row["onet_soc_code"]))
    return result


def transform_occupations(
    occ_rows: list[dict],
    child_data: dict[str, set[str]],
    now: datetime.datetime,
) -> list[dict]:
    """Transform raw.onet_occupations into base.onet_occupations records.

    Groups by BLS SOC, aggregates multi-detail codes, computes data
    completeness flags, and excludes structurally empty BLS SOCs.
    """
    # Group O*NET occupations by BLS SOC
    bls_groups: dict[str, list[dict]] = defaultdict(list)
    for row in occ_rows:
        bls_soc = truncate_to_bls_soc(row["onet_soc_code"])
        bls_groups[bls_soc].append(row)

    records = []
    for bls_soc, group in sorted(bls_groups.items()):
        # Sort detail codes for deterministic output
        group.sort(key=lambda r: r["onet_soc_code"])
        detail_codes = [r["onet_soc_code"] for r in group]

        # Pick primary title/description: prefer the .00 code, else first detail
        base_row = None
        for r in group:
            if r["onet_soc_code"].endswith(".00"):
                base_row = r
                break
        if base_row is None:
            base_row = group[0]

        # Data completeness flags
        has_wa = bls_soc in child_data["wa"]
        has_wc = bls_soc in child_data["wc"]
        has_ts = bls_soc in child_data["ts"]
        has_ro = bls_soc in child_data["ro"]

        all_flags = [has_wa, has_wc, has_ts, has_ro]
        if not any(all_flags):
            # Structurally empty -- exclude from Silver
            continue

        if all(all_flags):
            tier = "full"
        else:
            tier = "partial"

        record = {
            "bls_soc_code": bls_soc,
            "primary_title": base_row["title"],
            "description": base_row["description"],
            "onet_detail_codes": json.dumps(detail_codes),
            "onet_detail_count": len(detail_codes),
            "multi_detail_flag": len(detail_codes) > 1,
            "has_work_activities": has_wa,
            "has_work_context": has_wc,
            "has_tasks": has_ts,
            "has_related": has_ro,
            "data_completeness_tier": tier,
            "source_load_date": base_row["load_date"],
            "ingested_at": now,
        }
        record["record_id"] = compute_grain_id(
            record, ["bls_soc_code"], prefix="on"
        )
        records.append(record)

    return records


def transform_activity_profiles(
    wa_rows: list[dict],
    valid_bls_socs: set[str],
    now: datetime.datetime,
) -> list[dict]:
    """Transform raw.onet_work_activities into base.onet_activity_profiles.

    Filters to IM scale, aggregates to BLS SOC level by averaging
    importance across O*NET details, ranks within occupation, and flags
    high-importance activities.
    """
    # Filter to IM scale only and valid BLS SOCs
    # Group by (bls_soc, element_id)
    agg: dict[tuple[str, str], dict] = {}

    for row in wa_rows:
        if row["scale_id"] != "IM":
            continue
        bls_soc = truncate_to_bls_soc(row["onet_soc_code"])
        if bls_soc not in valid_bls_socs:
            continue

        key = (bls_soc, row["element_id"])
        if key not in agg:
            agg[key] = {
                "element_name": row["element_name"],
                "values": [],
                "suppress": False,
                "load_date": row["load_date"],
            }
        agg[key]["values"].append(row["data_value"])
        if row.get("recommend_suppress") == "Y":
            agg[key]["suppress"] = True

    # Build records with averaged importance
    # Group by bls_soc for ranking
    by_soc: dict[str, list[dict]] = defaultdict(list)

    for (bls_soc, element_id), data in agg.items():
        importance = sum(data["values"]) / len(data["values"])
        rec = {
            "bls_soc_code": bls_soc,
            "element_id": element_id,
            "element_name": data["element_name"],
            "importance": round(importance, 2),
            "onet_details_averaged": len(data["values"]),
            "suppress_flag": data["suppress"],
            "source_load_date": data["load_date"],
            "ingested_at": now,
        }
        by_soc[bls_soc].append(rec)

    # Rank within each occupation (1 = most important)
    records = []
    for bls_soc in sorted(by_soc):
        activities = by_soc[bls_soc]
        # Sort by importance descending, then element_id for determinism
        activities.sort(key=lambda r: (-r["importance"], r["element_id"]))
        for rank, rec in enumerate(activities, start=1):
            rec["importance_rank"] = rank
            rec["is_high_importance"] = rec["importance"] >= 3.5
            rec["record_id"] = compute_grain_id(
                rec, ["bls_soc_code", "element_id"], prefix="wa"
            )
            records.append(rec)

    return records


def transform_context_profiles(
    wc_rows: list[dict],
    valid_bls_socs: set[str],
    now: datetime.datetime,
) -> list[dict]:
    """Transform raw.onet_work_context into base.onet_context_profiles.

    Filters to CX and CT scales only, aggregates to BLS SOC level by
    averaging context_value across O*NET details, and flags burnout
    elements using the EDA-corrected element IDs.
    """
    # Filter to CX/CT scales and valid BLS SOCs
    agg: dict[tuple[str, str], dict] = {}

    for row in wc_rows:
        if row["scale_id"] not in ("CX", "CT"):
            continue
        bls_soc = truncate_to_bls_soc(row["onet_soc_code"])
        if bls_soc not in valid_bls_socs:
            continue

        key = (bls_soc, row["element_id"])
        if key not in agg:
            agg[key] = {
                "element_name": row["element_name"],
                "scale_id": row["scale_id"],
                "values": [],
                "suppress": False,
                "load_date": row["load_date"],
            }
        agg[key]["values"].append(row["data_value"])
        if row.get("recommend_suppress") == "Y":
            agg[key]["suppress"] = True

    records = []
    for (bls_soc, element_id), data in sorted(agg.items()):
        context_value = sum(data["values"]) / len(data["values"])
        rec = {
            "bls_soc_code": bls_soc,
            "element_id": element_id,
            "element_name": data["element_name"],
            "scale_id": data["scale_id"],
            "context_value": round(context_value, 2),
            "is_burnout_element": element_id in BURNOUT_ELEMENT_IDS,
            "onet_details_averaged": len(data["values"]),
            "suppress_flag": data["suppress"],
            "source_load_date": data["load_date"],
            "ingested_at": now,
        }
        rec["record_id"] = compute_grain_id(
            rec, ["bls_soc_code", "element_id"], prefix="wc"
        )
        records.append(rec)

    return records


def transform_career_transitions(
    ro_rows: list[dict],
    valid_bls_socs: set[str],
    now: datetime.datetime,
) -> list[dict]:
    """Transform raw.onet_related_occupations into base.onet_career_transitions.

    Truncates both SOC codes to BLS level, removes self-references,
    deduplicates by keeping the best (lowest) index per BLS pair,
    and derives relatedness_tier/is_primary.
    """
    # Aggregate: for each (source_bls, target_bls), keep lowest index
    best: dict[tuple[str, str], dict] = {}

    for row in ro_rows:
        src = truncate_to_bls_soc(row["onet_soc_code"])
        tgt = truncate_to_bls_soc(row["related_onet_soc_code"])

        # Exclude self-references
        if src == tgt:
            continue
        # Exclude pairs where either SOC not in valid set
        if src not in valid_bls_socs or tgt not in valid_bls_socs:
            continue

        key = (src, tgt)
        idx = row["related_index"]
        if key not in best or idx < best[key]["index"]:
            best[key] = {
                "index": idx,
                "load_date": row["load_date"],
            }

    records = []
    for (src, tgt), data in sorted(best.items()):
        idx = data["index"]
        tier = derive_relatedness_tier(idx)
        rec = {
            "bls_soc_code": src,
            "related_bls_soc_code": tgt,
            "best_index": idx,
            "relatedness_tier": tier,
            "is_primary": tier in ("Primary-Short", "Primary-Long"),
            "relationship_type": "similarity",
            "source_load_date": data["load_date"],
            "ingested_at": now,
        }
        rec["record_id"] = compute_grain_id(
            rec, ["bls_soc_code", "related_bls_soc_code"], prefix="ct"
        )
        records.append(rec)

    return records


# ---------------------------------------------------------------------------
# Pipeline entry points
# ---------------------------------------------------------------------------

def _read_bronze(project_dir: Path) -> dict[str, list[dict]]:
    """Read all required Bronze tables and return as a dict of row lists."""
    warehouse = project_dir / "data" / "bronze" / "iceberg_warehouse"
    catalog_path = project_dir / "data" / "catalog" / "catalog.db"
    catalog = get_catalog(warehouse, catalog_path)

    tables = {
        "occupations": "raw.onet_occupations",
        "work_activities": "raw.onet_work_activities",
        "work_context": "raw.onet_work_context",
        "task_statements": "raw.onet_task_statements",
        "related_occupations": "raw.onet_related_occupations",
    }

    result = {}
    for key, table_name in tables.items():
        tbl = catalog.load_table(table_name)
        rows = read_with_duckdb(tbl)
        logger.info("Read %d rows from %s", len(rows), table_name)
        result[key] = rows

    return result


def _get_silver_catalog(project_dir: Path):
    """Get the Silver zone catalog."""
    warehouse = project_dir / "data" / "silver" / "iceberg_warehouse"
    catalog_path = project_dir / "data" / "catalog" / "catalog.db"
    return get_catalog(warehouse, catalog_path)


def transform(project_dir: str | Path | None = None) -> dict:
    """Run all 4 Silver O*NET transformations.

    Reads from Bronze, transforms, and promotes to Silver base tables
    via the idempotent promote pattern.

    Returns summary dict with row counts for all 4 tables.
    """
    project_dir = Path(project_dir or ".").resolve()
    now = datetime.datetime.now(tz=datetime.timezone.utc)

    # Read all Bronze tables
    logger.info("Reading Bronze O*NET tables...")
    bronze = _read_bronze(project_dir)

    # Build child data presence sets
    child_data = _build_child_data_sets(
        bronze["work_activities"],
        bronze["work_context"],
        bronze["task_statements"],
        bronze["related_occupations"],
    )

    # Table 1: Occupations
    logger.info("Transforming base.onet_occupations...")
    occ_records = transform_occupations(bronze["occupations"], child_data, now)
    valid_bls_socs = {r["bls_soc_code"] for r in occ_records}
    logger.info("Produced %d occupation records", len(occ_records))

    # Table 2: Activity Profiles
    logger.info("Transforming base.onet_activity_profiles...")
    ap_records = transform_activity_profiles(
        bronze["work_activities"], valid_bls_socs, now
    )
    logger.info("Produced %d activity profile records", len(ap_records))

    # Table 3: Context Profiles
    logger.info("Transforming base.onet_context_profiles...")
    cp_records = transform_context_profiles(
        bronze["work_context"], valid_bls_socs, now
    )
    logger.info("Produced %d context profile records", len(cp_records))

    # Table 4: Career Transitions
    logger.info("Transforming base.onet_career_transitions...")
    ct_records = transform_career_transitions(
        bronze["related_occupations"], valid_bls_socs, now
    )
    logger.info("Produced %d career transition records", len(ct_records))

    # Promote all 4 tables
    catalog = _get_silver_catalog(project_dir)
    results = {}

    for name, records, schema_fn, table_name in [
        ("occupations", occ_records, get_occupations_schema, "onet_occupations"),
        ("activity_profiles", ap_records, get_activity_profiles_schema, "onet_activity_profiles"),
        ("context_profiles", cp_records, get_context_profiles_schema, "onet_context_profiles"),
        ("career_transitions", ct_records, get_career_transitions_schema, "onet_career_transitions"),
    ]:
        logger.info("Promoting to base.%s...", table_name)
        table = get_or_create_table(catalog, "base", table_name, schema_fn())
        result = promote(
            table,
            records,
            id_field="record_id",
            spec_name=SPEC_NAME,
            agent_name="@primary-agent",
        )
        results[name] = {
            "rows_transformed": len(records),
            "promoted": result["promoted"],
            "skipped_dedup": result["skipped"],
            "snapshot_id": result.get("snapshot_id"),
        }
        logger.info(
            "  %s: %d promoted, %d skipped",
            table_name,
            result["promoted"],
            result["skipped"],
        )

    return results
