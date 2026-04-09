"""Gold zone transformer for consumable.career_transitions.

Reads base.onet_career_transitions and base.onet_occupations from
Silver, plus consumable.onet_work_profiles from Gold. Enriches
transitions with titles and work profile availability flags.
Promotes to consumable.career_transitions.

Grain: bls_soc_code x related_bls_soc_code
Record ID: compute_grain_id(row, ['bls_soc_code', 'related_bls_soc_code'], prefix='tr')
"""

import datetime
import logging
from pathlib import Path

import duckdb
from pyiceberg.schema import Schema
from pyiceberg.types import (
    BooleanType,
    DateType,
    IntegerType,
    NestedField,
    StringType,
    TimestampType,
)

from brightsmith.infra.grain import compute_grain_id
from brightsmith.infra.iceberg_setup import get_catalog, get_or_create_table
from brightsmith.infra.promote import promote

logger = logging.getLogger(__name__)

SPEC_NAME = "gold-onet-profiles"
GRAIN_FIELDS = ["bls_soc_code", "related_bls_soc_code"]
GRAIN_PREFIX = "tr"


def get_gold_schema() -> Schema:
    """Iceberg schema for consumable.career_transitions (14 columns)."""
    return Schema(
        # Career Transition Identity (Carried + Enriched)
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "bls_soc_code", StringType(), required=True),
        NestedField(3, "source_title", StringType(), required=True),
        NestedField(4, "related_bls_soc_code", StringType(), required=True),
        NestedField(5, "related_title", StringType(), required=True),
        # Similarity Classification (Carried from Silver)
        NestedField(6, "best_index", IntegerType(), required=True),
        NestedField(7, "relatedness_tier", StringType(), required=True),
        NestedField(8, "is_primary", BooleanType(), required=True),
        NestedField(9, "relationship_type", StringType(), required=True),
        # Work Profile Availability (Derived)
        NestedField(10, "source_has_work_profile", BooleanType(), required=True),
        NestedField(11, "related_has_work_profile", BooleanType(), required=True),
        # FutureProof Stat Mapping (Static)
        NestedField(12, "backs_feature", StringType(), required=True),
        # Pipeline Metadata
        NestedField(13, "source_load_date", DateType(), required=True),
        NestedField(14, "promoted_at", TimestampType(), required=True),
    )


def derive_gold_rows(
    transition_rows: list[dict],
    occupation_rows: list[dict],
    work_profile_rows: list[dict],
) -> list[dict]:
    """Enrich career transitions with titles and work profile flags.

    Args:
        transition_rows: Rows from base.onet_career_transitions.
        occupation_rows: Rows from base.onet_occupations (for title lookup).
        work_profile_rows: Rows from consumable.onet_work_profiles (for
            activity_profile_available flag).

    Returns:
        List of dicts ready for grain-id computation and promotion.
    """
    if not transition_rows:
        return []

    # Build title lookup
    title_lookup: dict[str, str] = {
        r["bls_soc_code"]: r["primary_title"] for r in occupation_rows
    }

    # Build work profile availability lookup
    wp_lookup: dict[str, bool] = {
        r["bls_soc_code"]: r.get("activity_profile_available", False)
        for r in work_profile_rows
    }

    gold_rows: list[dict] = []
    for tr in transition_rows:
        soc = tr["bls_soc_code"]
        related_soc = tr["related_bls_soc_code"]

        row = {
            "bls_soc_code": soc,
            "source_title": title_lookup.get(soc, "Unknown"),
            "related_bls_soc_code": related_soc,
            "related_title": title_lookup.get(related_soc, "Unknown"),
            "best_index": tr["best_index"],
            "relatedness_tier": tr["relatedness_tier"],
            "is_primary": tr["is_primary"],
            "relationship_type": tr["relationship_type"],
            "source_has_work_profile": wp_lookup.get(soc, False),
            "related_has_work_profile": wp_lookup.get(related_soc, False),
            "backs_feature": "Stage3Branching",
            "source_load_date": tr["source_load_date"],
        }
        gold_rows.append(row)

    return gold_rows


def add_record_ids(gold_rows: list[dict], promoted_at: datetime.datetime) -> list[dict]:
    """Add record_id and promoted_at to each Gold row."""
    for row in gold_rows:
        row["record_id"] = compute_grain_id(row, GRAIN_FIELDS, prefix=GRAIN_PREFIX)
        row["promoted_at"] = promoted_at
    return gold_rows


def transform(
    project_dir: str | Path | None = None,
) -> dict:
    """Run the Gold zone transformation for consumable.career_transitions.

    Reads base.onet_career_transitions and base.onet_occupations from
    Silver, plus consumable.onet_work_profiles from Gold. Enriches
    transitions with titles and work profile availability flags.
    Promotes to consumable.career_transitions.

    Returns:
        {"rows_read": N, "rows_derived": N, "promoted": N, "skipped": N}
    """
    project_dir = Path(project_dir or ".").resolve()

    silver_warehouse = project_dir / "data" / "silver" / "iceberg_warehouse"
    catalog_path = project_dir / "data" / "catalog" / "catalog.db"
    gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"

    def _read_table(catalog, table_name: str) -> list[dict]:
        tbl = catalog.load_table(table_name)
        arrow = tbl.scan().to_arrow()
        con = duckdb.connect()
        rows_raw = con.sql("SELECT * FROM arrow").fetchall()
        cols = [field.name for field in tbl.schema().fields]
        con.close()
        return [dict(zip(cols, r)) for r in rows_raw]

    # Read Silver tables
    logger.info("Reading Silver tables...")
    silver_catalog = get_catalog(silver_warehouse, catalog_path)
    transition_rows = _read_table(silver_catalog, "base.onet_career_transitions")
    occupation_rows = _read_table(silver_catalog, "base.onet_occupations")
    logger.info(
        "Read %d transitions, %d occupations from Silver",
        len(transition_rows), len(occupation_rows),
    )

    # Read Gold work profiles (must exist from Table 1 transform)
    logger.info("Reading consumable.onet_work_profiles from Gold...")
    gold_catalog = get_catalog(gold_warehouse, catalog_path)
    work_profile_rows = _read_table(gold_catalog, "consumable.onet_work_profiles")
    logger.info("Read %d work profiles from Gold", len(work_profile_rows))

    # Derive Gold fields
    logger.info("Computing Gold derivations...")
    gold_rows = derive_gold_rows(transition_rows, occupation_rows, work_profile_rows)
    logger.info("Derived %d Gold rows", len(gold_rows))

    # Add record_id and promoted_at
    promoted_at = datetime.datetime.now(tz=datetime.timezone.utc)
    add_record_ids(gold_rows, promoted_at)

    # Promote to Gold
    logger.info("Promoting to consumable.career_transitions...")
    gold_table = get_or_create_table(
        gold_catalog, "consumable", "career_transitions", get_gold_schema()
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
        "rows_read": len(transition_rows) + len(occupation_rows) + len(work_profile_rows),
        "rows_derived": len(gold_rows),
        "promoted": result["promoted"],
        "skipped_dedup": result["skipped"],
        "snapshot_id": result.get("snapshot_id"),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    result = transform()
    print(f"Gold transform complete: {result}")
