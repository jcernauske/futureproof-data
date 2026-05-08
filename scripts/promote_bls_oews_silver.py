"""One-off runner: promote bronze.bls_oews to base.bls_oews (Silver zone).

Reads ~831 rows from the Bronze BLS OEWS table and writes them to the
Silver base table via the idempotent promote pattern. Re-running the
script produces 0 new rows.

Usage:
    uv run python scripts/promote_bls_oews_silver.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import brightsmith.config

# Use framework default project_name ('brightsmith') so writers and
# readers resolve the same catalog_name. See promote_bea_rpp_silver.py
# for the rationale and the prior adversarial-audit reference.
brightsmith.config.configure(
    project_root=PROJECT_ROOT,
    require_human_approval=False,
)

from silver.bls_oews_transformer import promote_bls_oews

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
)
logger = logging.getLogger("promote_bls_oews_silver")


def main() -> int:
    results = promote_bls_oews(project_dir=PROJECT_ROOT)
    logger.info("Promote results: %s", results)

    # Verify row count via DuckDB against the persistent warehouse.
    from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

    silver_warehouse = PROJECT_ROOT / "data" / "silver" / "iceberg_warehouse"
    catalog = get_catalog(silver_warehouse, brightsmith.config.CATALOG_PATH)
    table = catalog.load_table("base.bls_oews")
    rows = read_with_duckdb(table)
    logger.info("base.bls_oews row count: %d", len(rows))

    capped = sum(1 for r in rows if r.get("wage_capped"))
    logger.info("base.bls_oews wage_capped: %d", capped)

    return 0


if __name__ == "__main__":
    sys.exit(main())
