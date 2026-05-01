"""One-off runner: re-ingest EADA into the persistent bronze warehouse.

Uses the CSV cache at data/raw/eada_cache/eada_2022.csv — no network
fetch required.  After this runs, bronze.eada exists in the shared
Brightsmith Iceberg catalog (catalog_name='brightsmith') with 2,040 rows
across an 11-column schema (post-2026-04-30 Option-C amendment;
includes ``eada_fte_headcount`` from EADA's ``EFTotalCount`` column).

This is a re-ingest of an existing table.  Because the schema changed
(field 7 was added at ``eada_fte_headcount`` and metadata fields shifted
from IDs 7-10 → 8-11), the existing 10-column table is dropped and
re-created — pyiceberg's ``_get_or_create_table`` does not auto-evolve
schema.  The drop is consistent with the spec §4 amendment line 188
("the re-ingest is idempotent ... and overwrites the existing
snapshot"); the prior snapshot's metadata files remain on disk under
``data/bronze/iceberg_warehouse/bronze/eada/metadata/`` for any audit
trail that needs the previous-snapshot reference.

Usage:
    uv run python scripts/ingest_eada.py
"""

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import brightsmith.config  # noqa: E402

# Configure project paths but keep the framework default project_name
# ('brightsmith') so that writers and readers resolve the same catalog_name.
brightsmith.config.configure(
    project_root=PROJECT_ROOT,
    require_human_approval=False,
)

from brightsmith.domain_loader import DomainHints, DomainManifest, SourceConfig  # noqa: E402
from brightsmith.infra.iceberg_setup import get_catalog  # noqa: E402
from raw.eada_ingestor import EadaIngestor  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
)
logger = logging.getLogger("ingest_eada")


def main() -> int:
    source = SourceConfig(
        name="eada",
        namespace="bronze",
        table="eada",
        fetch={
            "eada": {
                "fallback_path": "data/raw/eada_cache",
            }
        },
        entities={
            "eada": (
                "EADA Athletics Disclosure Survey — "
                "Institution-Level totals, 2022-2023 cycle"
            )
        },
        dedup_grain=["unitid"],
        cache_dir=PROJECT_ROOT / "data" / "raw" / "eada_cache",
    )
    manifest = DomainManifest(
        name="futureproof-data",
        version="0.1",
        description="EADA re-ingest runner (Option-C amendment, 2026-04-30)",
        sources=[],
        hints=DomainHints(),
        pipeline={},
    )

    # Drop the existing 10-column table (if present) so the new
    # 11-column schema is created cleanly.  Schema evolution at
    # raw is not used here — the spec amendment treats the re-ingest
    # as a snapshot-overwrite, not a schema-evolution.
    catalog = get_catalog(
        brightsmith.config.WAREHOUSE_PATH,
        brightsmith.config.CATALOG_PATH,
    )
    try:
        catalog.drop_table("bronze.eada")
        logger.info("Dropped existing bronze.eada table (10-col schema)")
    except Exception as exc:
        logger.info("No existing bronze.eada to drop: %s", exc)

    ingestor = EadaIngestor(source, manifest)
    results = ingestor.ingest(force_fallback=True)
    logger.info("Ingest results: %s", results)

    # Verify the new table.
    table = catalog.load_table("bronze.eada")
    schema = table.schema()
    logger.info("New schema field count: %d", len(schema.fields))
    for f in schema.fields:
        logger.info(
            "  field %d: %s %s%s",
            f.field_id,
            f.name,
            f.field_type,
            " (required)" if f.required else " (optional)",
        )
    snap_id = table.current_snapshot().snapshot_id
    logger.info("New snapshot ID: %d", snap_id)
    df = table.scan().to_pandas()
    logger.info("Row count: %d", len(df))
    if "eada_fte_headcount" in df.columns:
        logger.info(
            "eada_fte_headcount distribution: %s",
            df["eada_fte_headcount"].describe().to_dict(),
        )
    return 0 if len(df) == 2040 and len(schema.fields) == 11 else 1


if __name__ == "__main__":
    raise SystemExit(main())
