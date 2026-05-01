"""One-off runner: promote bronze.ipeds_finance to base.ipeds_finance.

Reads the ~2,683-row bronze IPEDS Finance snapshot (FY2022 — F1A public
GASB, F2 private nonprofit FASB, F3 private for-profit) and writes the
matching rows to ``base.ipeds_finance`` via the idempotent promote
pattern.  Re-running the script produces 0 new rows.

NOTE: This script intentionally does NOT override ``project_name``.  The
Brightsmith framework's ``get_catalog()`` binds the SqlCatalog to the
module-level ``PROJECT_NAME``.  If this script set ``project_name`` to
anything other than the framework default ('brightsmith'), it would
write Iceberg table rows under a separate ``catalog_name`` that
``dq_runner`` (and every other reader that does not call
``configure()``) cannot see — see the BEA RPP precedent at
``governance/adversarial-audits/raw-ingest-bea-rpp.md`` HIGH-1.

Usage:
    uv run python scripts/promote_ipeds_finance_base.py
"""

from __future__ import annotations

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

from silver.ipeds_finance_base import promote_ipeds_finance_base  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
)
logger = logging.getLogger("promote_ipeds_finance_base")


def main() -> int:
    results = promote_ipeds_finance_base(project_dir=PROJECT_ROOT)
    logger.info("Promote results: %s", results)

    # Verify row count + spot-check Stanford against the persistent
    # warehouse via a fresh read.
    from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

    base_warehouse = PROJECT_ROOT / "data" / "silver" / "iceberg_warehouse"
    catalog = get_catalog(base_warehouse, brightsmith.config.CATALOG_PATH)
    table = catalog.load_table("base.ipeds_finance")
    rows = read_with_duckdb(table)
    logger.info("base.ipeds_finance row count: %d", len(rows))

    # Stanford UNITID 243744 spot check (per-FTE values from the spec).
    stanford = [r for r in rows if r["unitid"] == 243744]
    if stanford:
        s = stanford[0]
        logger.info("Stanford UNITID=243744 derivations:")
        logger.info("  instruction_per_fte:           %s", s.get("instruction_per_fte"))
        logger.info("  institutional_support_per_fte: %s", s.get("institutional_support_per_fte"))
        logger.info("  endowment_per_fte:             %s", s.get("endowment_per_fte"))
        logger.info("  marketing_ratio:               %s", s.get("marketing_ratio"))
        logger.info("  record_id:                     %s", s.get("record_id"))

    # record_id non-null + unique check (BSE-IPF-002, BSE-IPF-003).
    record_ids = [r.get("record_id") for r in rows]
    nulls = sum(1 for rid in record_ids if rid is None)
    unique_ids = set(record_ids)
    logger.info(
        "record_id: %d non-null, %d unique (== row count: %s)",
        len(record_ids) - nulls,
        len(unique_ids),
        len(unique_ids) == len(record_ids),
    )

    # Form mix.
    form_counts: dict[str, int] = {}
    for r in rows:
        form_counts[r["report_form"]] = form_counts.get(r["report_form"], 0) + 1
    logger.info("Form mix: %s", sorted(form_counts.items()))

    return 0 if (
        nulls == 0
        and len(unique_ids) == len(record_ids)
        and len(rows) >= 2_400
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
