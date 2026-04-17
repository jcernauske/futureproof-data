"""One-off runner: re-promote consumable.career_outcomes with CSI enrichment.

Reads ``base.college_scorecard`` (field-of-study silver) and
``base.college_scorecard_institution`` (institution silver), derives the Gold
career outcomes rows with the 2026-04-16 CSI enrichment applied (spec
``raw-ingest-college-scorecard-institution`` §Zone 3), evolves the Gold Iceberg
schema additively to add the 6 new columns (IDs 32-37), and overwrites the
target table so existing records get the new column values populated.

This is an overwrite-mode promote because the record_ids are stable across
runs and a dedup-append promote would skip every row (leaving the new columns
null). The grain is unchanged; only the column set expands.

NOTE: This script intentionally does NOT override ``project_name``. See
``scripts/promote_regional_price_parities.py`` for the full rationale —
overriding project_name breaks catalog resolution for downstream readers.

Usage:
    uv run python scripts/promote_career_outcomes_enriched.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import brightsmith.config

brightsmith.config.configure(
    project_root=PROJECT_ROOT,
    require_human_approval=False,
)

from gold.college_scorecard_career_outcomes import (
    CSI_ENRICHMENT_COLUMNS,
    transform,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
)
logger = logging.getLogger("promote_career_outcomes_enriched")


EXPECTED_ROW_COUNT = 69_947


def main() -> int:
    # Pre-promote row count (for the row-count-preserved invariant GLD-CSI-001).
    from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

    gold_warehouse = PROJECT_ROOT / "data" / "gold" / "iceberg_warehouse"
    catalog = get_catalog(gold_warehouse, brightsmith.config.CATALOG_PATH)
    try:
        table = catalog.load_table("consumable.career_outcomes")
        pre_rows = read_with_duckdb(table)
        pre_count = len(pre_rows)
        logger.info("Pre-promote row count: %d", pre_count)
    except Exception:
        pre_count = None
        logger.info("No existing consumable.career_outcomes (fresh create)")

    results = transform(project_dir=PROJECT_ROOT, overwrite=True)
    logger.info("Promote results: %s", results)

    # Post-promote verification.
    table = catalog.load_table("consumable.career_outcomes")
    post_rows = read_with_duckdb(table)
    post_count = len(post_rows)
    logger.info("Post-promote row count: %d", post_count)

    # 1) Row-count-preserved invariant (GLD-CSI-001).
    if pre_count is not None and post_count != pre_count:
        logger.error(
            "Row count changed: pre=%d post=%d (must match)",
            pre_count, post_count,
        )
        return 1
    if post_count != EXPECTED_ROW_COUNT:
        logger.warning(
            "Post row count %d != expected %d (spec invariant)",
            post_count, EXPECTED_ROW_COUNT,
        )

    # 2) CSI enrichment columns are present on the schema.
    schema_names = {f.name for f in table.schema().fields}
    for col in (*CSI_ENRICHMENT_COLUMNS, "institution_control"):
        if col not in schema_names:
            logger.error("Missing enrichment column in Gold schema: %s", col)
            return 1
    logger.info("All 7 enrichment columns present in schema.")

    # 3) Non-null coverage spot-check per field (matches EDA projection).
    coverage: dict[str, dict[str, float]] = {}
    for col in (*CSI_ENRICHMENT_COLUMNS, "institution_control"):
        non_null = sum(1 for r in post_rows if r.get(col) is not None)
        pct = 100.0 * non_null / post_count if post_count else 0.0
        coverage[col] = {"non_null": non_null, "pct": round(pct, 2)}
    logger.info("Post-enrichment coverage: %s", coverage)

    # 4) Sample a few rows to show the columns land with correct types.
    sample = [r for r in post_rows if r.get("net_price_annual") is not None][:3]
    for r in sample:
        logger.info(
            "sample: unitid=%s cipcode=%s control=%s NP=%.2f COA=%.2f 4yr=%.2f",
            r["unitid"], r["cipcode"], r["institution_control"],
            r["net_price_annual"], r["cost_of_attendance_annual"],
            r["net_price_4yr"],
        )

    # 5) Invariant: net_price_4yr ≈ net_price_annual × 4 on sampled rows.
    for r in sample:
        expected_4yr = r["net_price_annual"] * 4
        delta = abs(r["net_price_4yr"] - expected_4yr)
        if delta > 1.0:
            logger.error(
                "Invariant violated for unitid=%s: |4yr - annual*4|=%.2f > $1",
                r["unitid"], delta,
            )
            return 1

    logger.info("All invariants passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
