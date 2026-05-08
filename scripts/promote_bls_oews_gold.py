"""One-off runner: re-promote consumable.occupation_profiles and
consumable.program_career_paths with the OEWS wage_p10/p25/p75/p90
enrichment landed (spec ingest-bls-oews-wage-percentiles §Zone 3).

Runs the two Gold transformers in dependency order:
  1. gold.bls_ooh_occupation_profiles — produces occupation_profiles
     with the LEFT JOIN of base.bls_oews on soc_code.
  2. gold.futureproof_engine — re-derives program_career_paths and
     career_branches, threading the four wage_p* columns through.

Usage:
    uv run python scripts/promote_bls_oews_gold.py
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
)
logger = logging.getLogger("promote_bls_oews_gold")


def main() -> int:
    # Step 1: occupation_profiles (LEFT JOIN bls_ooh + bls_oews on soc_code).
    from gold.bls_ooh_occupation_profiles import transform as transform_op

    logger.info("Running gold.bls_ooh_occupation_profiles (with OEWS LEFT JOIN)...")
    # overwrite=True: existing rows have the same grain (soc_code) but
    # need new wage_p* column values landed.
    op_result = transform_op(project_dir=PROJECT_ROOT, overwrite=True)
    logger.info("occupation_profiles result: %s", op_result)

    # Step 2: futureproof_engine (threads wage_p* through to PCP).
    from gold.futureproof_engine import transform as transform_engine

    logger.info("Running gold.futureproof_engine (threading wage_p* to PCP)...")
    # overwrite=True because we're rewriting existing rows with new
    # wage_p* values for an unchanged grain.
    engine_result = transform_engine(project_dir=PROJECT_ROOT, overwrite=True)
    logger.info("futureproof_engine result: %s", engine_result)

    # Verify wage_p* coverage in the persistent warehouse.
    from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

    gold_warehouse = PROJECT_ROOT / "data" / "gold" / "iceberg_warehouse"
    gold_cat = get_catalog(gold_warehouse, brightsmith.config.CATALOG_PATH)

    op_rows = read_with_duckdb(gold_cat.load_table("consumable.occupation_profiles"))
    op_with_p25 = sum(1 for r in op_rows if r.get("wage_p25") is not None)
    logger.info(
        "occupation_profiles: %d rows total, %d with wage_p25 non-null",
        len(op_rows),
        op_with_p25,
    )

    pcp_rows = read_with_duckdb(gold_cat.load_table("consumable.program_career_paths"))
    pcp_with_p25 = sum(1 for r in pcp_rows if r.get("wage_p25") is not None)
    logger.info(
        "program_career_paths: %d rows total, %d with wage_p25 non-null",
        len(pcp_rows),
        pcp_with_p25,
    )

    # Spot-check: Software Developers should have OEWS percentiles.
    sd = next((r for r in op_rows if r["soc_code"] == "15-1252"), None)
    if sd:
        logger.info(
            "Spot check (15-1252 Software Developers): "
            "wage_p10=%s, wage_p25=%s, wage_p75=%s, wage_p90=%s, median=%s",
            sd.get("wage_p10"),
            sd.get("wage_p25"),
            sd.get("wage_p75"),
            sd.get("wage_p90"),
            sd.get("median_annual_wage"),
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
