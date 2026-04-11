"""One-off runner: promote bronze.bea_rpp to base.bea_rpp (Silver zone).

Reads 51 rows from the Bronze BEA RPP table and writes them to the
Silver base table via the idempotent promote pattern.  Re-running the
script produces 0 new rows.

NOTE: This script intentionally does NOT override ``project_name``. The
Brightsmith framework's ``get_catalog()`` binds the SqlCatalog to the
module-level ``PROJECT_NAME``. If this script set ``project_name`` to
anything other than the framework default ('brightsmith'), it would
write Iceberg table rows under a separate ``catalog_name`` that
``dq_runner`` (and every other reader that does not call
``configure()``) cannot see — reproducing the catalog-registration
drift remediated per ``governance/adversarial-audits/raw-ingest-bea-rpp.md``
HIGH-1.

Usage:
    uv run python scripts/promote_bea_rpp_silver.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import brightsmith.config

# Configure project paths but keep the framework default project_name
# ('brightsmith') so writers and readers resolve the same catalog_name.
brightsmith.config.configure(
    project_root=PROJECT_ROOT,
    require_human_approval=False,
)

from silver.bea_rpp_transformer import promote_bea_rpp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
)
logger = logging.getLogger("promote_bea_rpp_silver")


def main() -> int:
    results = promote_bea_rpp(project_dir=PROJECT_ROOT)
    logger.info("Promote results: %s", results)

    # Verify row count via DuckDB against the persistent warehouse.
    from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

    silver_warehouse = PROJECT_ROOT / "data" / "silver" / "iceberg_warehouse"
    catalog = get_catalog(silver_warehouse, brightsmith.config.CATALOG_PATH)
    table = catalog.load_table("base.bea_rpp")
    rows = read_with_duckdb(table)
    logger.info("base.bea_rpp row count: %d", len(rows))

    verif = {"bea_official": 0, "estimate": 0}
    for r in rows:
        v = r.get("verification_status")
        if v in verif:
            verif[v] += 1
    logger.info("verification_status distribution: %s", verif)

    return 0 if len(rows) == 51 and verif == {"bea_official": 8, "estimate": 43} else 1


if __name__ == "__main__":
    raise SystemExit(main())
