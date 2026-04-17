"""One-off runner: promote bronze.college_scorecard_institution to
base.college_scorecard_institution (Silver zone).

Reads 3,039 rows from the Bronze College Scorecard Institution table and
writes them to the Silver base table via the idempotent ``promote`` pattern.
Re-running the script produces 0 new rows.

NOTE: This script intentionally does NOT override ``project_name``. The
Brightsmith framework's ``get_catalog()`` binds the SqlCatalog to the
module-level ``PROJECT_NAME``. If this script set ``project_name`` to
anything other than the framework default ('brightsmith'), it would write
Iceberg rows under a separate ``catalog_name`` that ``dq_runner`` (and every
other reader that does not call ``configure()``) cannot see --
reproducing the catalog-registration drift remediated per
``governance/adversarial-audits/raw-ingest-bea-rpp.md`` HIGH-1.

Usage:
    uv run python scripts/promote_college_scorecard_institution_silver.py
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

from silver.college_scorecard_institution_transformer import transform

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
)
logger = logging.getLogger("promote_college_scorecard_institution_silver")

EXPECTED_ROWS = 3039
ROW_TOLERANCE = 5  # +/- drift budget matches Silver DQ rule SLV-CSI-001


def main() -> int:
    results = transform(project_dir=PROJECT_ROOT)
    logger.info("Promote results: %s", results)

    # Verify row count via DuckDB against the persistent Silver warehouse.
    from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

    silver_warehouse = PROJECT_ROOT / "data" / "silver" / "iceberg_warehouse"
    catalog = get_catalog(silver_warehouse, brightsmith.config.CATALOG_PATH)
    table = catalog.load_table("base.college_scorecard_institution")
    rows = read_with_duckdb(table)
    logger.info("base.college_scorecard_institution row count: %d", len(rows))

    control_dist: dict[str, int] = {}
    for r in rows:
        label = r.get("institution_control")
        if label is not None:
            control_dist[label] = control_dist.get(label, 0) + 1
    logger.info("institution_control distribution: %s", control_dist)

    diff = abs(len(rows) - EXPECTED_ROWS)
    if diff > ROW_TOLERANCE:
        logger.error(
            "Silver row count %d deviates from expected %d by more than tolerance %d",
            len(rows),
            EXPECTED_ROWS,
            ROW_TOLERANCE,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
