"""One-off runner: ingest IPEDS Finance into the persistent bronze warehouse.

Reads from the staged FY2023 source zips at
``data/raw/ipeds_finance_cache/`` (F2223_F1A.zip, F2223_F2.zip,
F2223_F3.zip, EFIA2023.zip, HD2023.zip) — no NCES network calls
required.  After this runs, ``bronze.ipeds_finance`` exists in the
shared Brightsmith Iceberg catalog (catalog_name='brightsmith') with
~2,675 rows after the HD 4-year-bachelor's-or-above filter.

Cycle-year choice: FY2023 (academic year 2022-23) is the most-recent
fully-published IPEDS Finance cycle as of 2026-04-30.  The pre-staged
FY24 zips in the cache directory are 1.2KB 404-error HTML pages —
NCES has not yet released that cycle.  The full EDA at
``governance/eda/full-pipeline-ipeds-finance-raw-eda.md`` confirmed
all column codes against FY23 dictionaries at byte level.
``fiscal_year=`` is a constructor arg, so promoting to FY24 once
published is a parameter change, not a code change.

NOTE: This script intentionally does NOT override ``project_name``.
The Brightsmith framework's ``get_catalog()`` binds the SqlCatalog to
the module-level ``PROJECT_NAME``.  If this script set
``project_name`` to anything other than the framework default
('brightsmith'), it would write Iceberg table rows under a separate
``catalog_name`` that ``dq_runner`` (and every other reader that does
not call ``configure()``) cannot see — see the BEA RPP precedent at
``governance/adversarial-audits/raw-ingest-bea-rpp.md`` HIGH-1.

This is a re-ingest of the FY22 table.  Because the existing snapshot
holds FY22 data and we're landing FY23, the existing table is dropped
and re-created — single-vintage scope (§2 Decision #6) means the
fiscal_year column is invariant within a snapshot.  The drop is
consistent with the EADA re-ingest precedent at
``scripts/ingest_eada.py``.

Usage:
    uv run python scripts/ingest_ipeds_finance.py
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
from raw.ipeds_finance_ingestor import IpedsFinanceIngestor  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
)
logger = logging.getLogger("ingest_ipeds_finance")

FISCAL_YEAR = 2023


def main() -> int:
    cache_dir = PROJECT_ROOT / "data" / "raw" / "ipeds_finance_cache"
    if not cache_dir.exists():
        logger.error("IPEDS finance cache directory missing: %s", cache_dir)
        return 1

    # Verify the five FY23 source files are present (the EDA confirmed
    # all five at 200 OK from NCES).
    required = [
        "F2223_F1A.zip",
        "F2223_F2.zip",
        "F2223_F3.zip",
        "EFIA2023.zip",
        "HD2023.csv",  # HD2023.zip also present; either path works
    ]
    for name in required:
        zip_alt = cache_dir / name.replace(".csv", ".zip")
        csv_alt = cache_dir / name
        if not (zip_alt.exists() or csv_alt.exists()):
            logger.error("FY23 cache missing: %s (or .zip equivalent)", csv_alt)
            return 1

    # Build SourceConfig in-line (mirrors scripts/ingest_bea_rpp.py).
    source = SourceConfig(
        name="ipeds_finance",
        namespace="bronze",
        table="ipeds_finance",
        fetch={
            "ipeds_finance": {
                "fallback_path": str(cache_dir),
                "fiscal_year": FISCAL_YEAR,
            }
        },
        entities={
            "ipeds_finance": (
                "IPEDS Finance Survey — F1A + F2 + F3 + EFIA + HD, "
                f"FY{FISCAL_YEAR}"
            )
        },
        dedup_grain=["unitid"],
        cache_dir=cache_dir,
    )
    manifest = DomainManifest(
        name="futureproof-data",
        version="0.1",
        description="ingest runner",
        sources=[],
        hints=DomainHints(),
        pipeline={},
    )

    # Drop the existing FY22 table (if present) so the FY23 snapshot
    # writes cleanly.  Single-vintage scope (§2 Decision #6) means we
    # do not retain prior-vintage rows; the prior snapshot's metadata
    # files remain on disk under
    # ``data/bronze/iceberg_warehouse/bronze/ipeds_finance/metadata/``
    # for any audit trail.
    catalog = get_catalog(
        brightsmith.config.WAREHOUSE_PATH,
        brightsmith.config.CATALOG_PATH,
    )
    try:
        catalog.drop_table("bronze.ipeds_finance")
        logger.info("Dropped existing bronze.ipeds_finance table")
    except Exception as exc:
        logger.info("No existing bronze.ipeds_finance to drop: %s", exc)

    ingestor = IpedsFinanceIngestor(
        source,
        manifest,
        fiscal_year=FISCAL_YEAR,
    )

    # force_fallback=True so we never silently fall through to the bulk
    # download URLs (FY23 zips are pre-staged in the cache directory).
    results = ingestor.ingest(
        cache_dir=cache_dir,
        force_fallback=True,
    )
    logger.info("Ingest results: %s", results)

    # Verify row count + form mix via DuckDB against the persistent warehouse.
    from brightsmith.infra.iceberg_setup import read_with_duckdb

    table = catalog.load_table("bronze.ipeds_finance")
    snap_id = table.current_snapshot().snapshot_id
    logger.info("Snapshot ID: %d", snap_id)

    rows = read_with_duckdb(table)
    logger.info("bronze.ipeds_finance row count: %d", len(rows))

    form_counts: dict[str, int] = {}
    for r in rows:
        form_counts[r["report_form"]] = form_counts.get(r["report_form"], 0) + 1
    logger.info("Form mix: %s", sorted(form_counts.items()))

    # Sanity: EDA expects ~2,675 rows (F1A=819 / F2=1,579 / F3=277).
    return 0 if 2_400 <= len(rows) <= 3_000 else 1


if __name__ == "__main__":
    raise SystemExit(main())
