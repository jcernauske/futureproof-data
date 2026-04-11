"""One-off runner: promote base.bea_rpp (Silver) to consumable.regional_price_parities (Gold).

Reads 51 rows from the Silver BEA RPP table, derives cost_tier and the
four adjusted_Nk columns, stamps promoted_at, and writes to the Gold
consumable zone via the idempotent promote pattern. Re-running the
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
    uv run python scripts/promote_regional_price_parities.py
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

from gold.regional_price_parities_transformer import transform

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
)
logger = logging.getLogger("promote_regional_price_parities")


def main() -> int:
    results = transform(project_dir=PROJECT_ROOT)
    logger.info("Promote results: %s", results)

    # Verify row count and distributions against the persistent warehouse.
    from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

    gold_warehouse = PROJECT_ROOT / "data" / "gold" / "iceberg_warehouse"
    catalog = get_catalog(gold_warehouse, brightsmith.config.CATALOG_PATH)
    table = catalog.load_table("consumable.regional_price_parities")
    rows = read_with_duckdb(table)
    logger.info("consumable.regional_price_parities row count: %d", len(rows))

    verif: dict[str, int] = {"bea_official": 0, "estimate": 0}
    for r in rows:
        v = r.get("verification_status")
        if v in verif:
            verif[v] += 1
    logger.info("verification_status distribution: %s", verif)

    tier_counts: dict[str, int] = {}
    for r in rows:
        t = r.get("cost_tier")
        tier_counts[t] = tier_counts.get(t, 0) + 1
    logger.info("cost_tier distribution: %s", tier_counts)

    ok = (
        len(rows) == 51
        and verif == {"bea_official": 8, "estimate": 43}
        and set(tier_counts.keys()) <= {
            "very_high", "high", "average", "low", "very_low",
        }
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
