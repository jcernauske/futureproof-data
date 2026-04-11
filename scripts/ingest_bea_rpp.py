"""One-off runner: ingest BEA RPP into the persistent bronze warehouse.

Uses the CSV fallback at data/raw/bea_cache/bea_rpp_2024.csv — no BEA API
key required.  After this runs, bronze.bea_rpp exists in the shared
Brightsmith Iceberg catalog (catalog_name='brightsmith') with 51 rows.

NOTE: This script intentionally does NOT override ``project_name``. The
Brightsmith framework's ``get_catalog()`` binds the SqlCatalog to the
module-level ``PROJECT_NAME``. If this script set ``project_name`` to
anything other than the framework default ('brightsmith'), it would write
Iceberg table rows under a separate ``catalog_name`` that ``dq_runner``
(and every other reader that does not call ``configure()``) cannot see —
producing the catalog-registration drift remediated per
``governance/adversarial-audits/raw-ingest-bea-rpp.md`` HIGH-1.

Usage:
    uv run python scripts/ingest_bea_rpp.py
"""

import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import brightsmith.config

# Configure project paths but keep the framework default project_name
# ('brightsmith') so that writers and readers resolve the same catalog_name.
brightsmith.config.configure(
    project_root=PROJECT_ROOT,
    require_human_approval=False,
)

from brightsmith.domain_loader import DomainHints, DomainManifest, SourceConfig
from raw.bea_rpp_ingestor import BeaRppIngestor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
)
logger = logging.getLogger("ingest_bea_rpp")


def main() -> int:
    source = SourceConfig(
        name="bea_rpp",
        namespace="bronze",
        table="bea_rpp",
        fetch={"bea_api": {"fallback_path": "data/raw/bea_cache/bea_rpp_2024.csv"}},
        entities={"rpp": "BEA Regional Price Parities — All States + DC, All Items 2024"},
        dedup_grain=["geo_fips"],
        cache_dir=PROJECT_ROOT / "data" / "raw" / "bea_cache",
    )
    manifest = DomainManifest(
        name="futureproof-data",
        version="0.1",
        description="ingest runner",
        sources=[],
        hints=DomainHints(),
        pipeline={},
    )

    # Force the CSV cache path (no API key required for this run).
    os.environ.pop("BEA_API_KEY", None)

    ingestor = BeaRppIngestor(source, manifest)
    results = ingestor.ingest(force_fallback=True)
    logger.info("Ingest results: %s", results)

    # Verify row count via DuckDB against the persistent warehouse.
    from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

    catalog = get_catalog(
        brightsmith.config.WAREHOUSE_PATH,
        brightsmith.config.CATALOG_PATH,
    )
    table = catalog.load_table("bronze.bea_rpp")
    rows = read_with_duckdb(table)
    logger.info("bronze.bea_rpp row count: %d", len(rows))
    return 0 if len(rows) == 51 else 1


if __name__ == "__main__":
    raise SystemExit(main())
