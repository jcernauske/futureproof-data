"""One-off runner: ingest Anthropic Economic Index into the persistent bronze warehouse.

Reads the local git-lfs clone at ``data/raw/anthropic_economic_index/``
(preferred release per ``AnthropicEconomicIndexIngestor.RELEASE_PREFERENCE``)
and materializes ``raw.anthropic_economic_index`` into the shared Brightsmith
Iceberg catalog under ``data/bronze/iceberg_warehouse/raw/anthropic_economic_index/``.

Expected row count after the many-to-many (task, soc) fan-out is ~4,082 rows
per the dq-engineer execution log in
``governance/audit-trail/dq-engineer-aei-*.json``.

NOTE: This script intentionally does NOT override ``project_name``. The
Brightsmith framework's ``get_catalog()`` binds the SqlCatalog to the
module-level ``PROJECT_NAME``. If this script set ``project_name`` to
anything other than the framework default ('brightsmith'), it would write
Iceberg rows under a separate ``catalog_name`` that ``dq_runner`` (and every
other reader that does not call ``configure()``) cannot see --
reproducing the catalog-registration drift remediated per
``governance/adversarial-audits/raw-ingest-bea-rpp.md`` HIGH-1.

Usage:
    uv run python scripts/ingest_anthropic_economic_index.py
"""

from __future__ import annotations

import logging
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
from raw.anthropic_economic_index_ingestor import (
    AnthropicEconomicIndexIngestor,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
)
logger = logging.getLogger("ingest_anthropic_economic_index")

# Expected rowcount per the DQ baseline in the dq-engineer audit trail.
EXPECTED_ROWS = 4082
ROW_TOLERANCE = 50  # permit small drift across release ordering


def main() -> int:
    # SourceConfig: Namespace is ``raw`` to match:
    #   - DQ rules at governance/dq-rules/raw-anthropic-economic-index.json
    #     ("table": "raw.anthropic_economic_index")
    #   - Silver transformer which reads ``bronze_catalog.load_table(
    #     "raw.anthropic_economic_index")`` at
    #     src/silver/anthropic_observed_exposure_transformer.py:411
    #   - Peer O*NET and CIP-SOC raw tables, which also live in the
    #     ``raw`` namespace (e.g. raw.onet_task_statements).
    source = SourceConfig(
        name="anthropic_economic_index",
        namespace="raw",
        table="anthropic_economic_index",
        fetch={"hf_git_clone": {}},
        entities={
            "anthropic": (
                "Anthropic Economic Index — observed AI exposure "
                "(task_pct_v2, automation_vs_augmentation_by_task, "
                "O*NET task statements bridge)"
            )
        },
        # Composite grain — task_id alone is not unique because task-to-SOC
        # is many-to-many (up to 34-way fan-out in the 2025-03-27 release).
        dedup_grain=["task_id", "soc_code"],
        cache_dir=PROJECT_ROOT / "data" / "raw" / "anthropic_economic_index_cache",
    )
    manifest = DomainManifest(
        name="futureproof-data",
        version="0.1",
        description="ingest runner",
        sources=[],
        hints=DomainHints(),
        pipeline={},
    )

    ingestor = AnthropicEconomicIndexIngestor(source, manifest)
    results = ingestor.ingest(method="hf_git_clone")
    logger.info("Ingest results: %s", results)

    # Verify row count via DuckDB against the persistent warehouse.
    from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

    catalog = get_catalog(
        brightsmith.config.WAREHOUSE_PATH,
        brightsmith.config.CATALOG_PATH,
    )
    table = catalog.load_table("raw.anthropic_economic_index")
    rows = read_with_duckdb(table)
    logger.info("raw.anthropic_economic_index row count: %d", len(rows))

    diff = abs(len(rows) - EXPECTED_ROWS)
    if diff > ROW_TOLERANCE:
        logger.error(
            "Row count %d deviates from expected %d by more than tolerance %d",
            len(rows),
            EXPECTED_ROWS,
            ROW_TOLERANCE,
        )
        return 1

    # Structural sanity: soc_code composition mirrors dq-engineer baselines.
    null_soc = sum(1 for r in rows if r.get("soc_code") in (None, ""))
    soc_matched = len(rows) - null_soc
    logger.info(
        "Bronze composition: soc_match=%d null_soc=%d",
        soc_matched,
        null_soc,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
