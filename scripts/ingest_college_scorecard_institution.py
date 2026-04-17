"""One-off runner: ingest College Scorecard Institution into the persistent bronze warehouse.

Downloads the ~170MB Most-Recent-Cohorts-Institution CSV (with ZIP fallback)
and filters/flattens it via CollegeScorecardInstitutionIngestor to produce the
bronze.college_scorecard_institution Iceberg table in the shared Brightsmith
catalog (catalog_name='brightsmith'). Expected row count after the
PREDDEG=3 OR ICLEVEL=1 filter and UNITID dedup is 3,039 (per the Bronze EDA
at docs/sessions/eda-college-scorecard-institution.md).

NOTE: This script intentionally does NOT override ``project_name``. The
Brightsmith framework's ``get_catalog()`` binds the SqlCatalog to the
module-level ``PROJECT_NAME``. If this script set ``project_name`` to
anything other than the framework default ('brightsmith'), it would write
Iceberg rows under a separate ``catalog_name`` that ``dq_runner`` (and every
other reader that does not call ``configure()``) cannot see --
reproducing the catalog-registration drift remediated per
``governance/adversarial-audits/raw-ingest-bea-rpp.md`` HIGH-1.

The ingestor's fetch() accepts a local ``csv_path`` kwarg (used for tests).
If a cached CSV exists at /tmp/Most-Recent-Cohorts-Institution.csv or inside
data/raw/scorecard_cache/, this runner passes it to fetch() to avoid the
170MB re-download. Otherwise fetch() downloads from the primary URL (or
ZIP fallback) automatically.

Usage:
    uv run python scripts/ingest_college_scorecard_institution.py
"""

from __future__ import annotations

import io
import logging
import sys
import zipfile
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
from raw.college_scorecard_institution_ingestor import (
    CollegeScorecardInstitutionIngestor,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
)
logger = logging.getLogger("ingest_college_scorecard_institution")

EXPECTED_ROWS = 3039
ROW_TOLERANCE = 5  # +/- drift budget per Bronze DQ rule RAW-CSI-001

CACHE_CANDIDATES: tuple[Path, ...] = (
    Path("/tmp/Most-Recent-Cohorts-Institution.csv"),
    PROJECT_ROOT / "data" / "raw" / "scorecard_cache" / "Most-Recent-Cohorts-Institution.csv",
)

ZIP_CACHE_CANDIDATES: tuple[Path, ...] = (
    Path("/tmp/Most-Recent-Cohorts-Institution.zip"),
    PROJECT_ROOT
    / "data"
    / "raw"
    / "scorecard_cache"
    / "Most-Recent-Cohorts-Institution_04172025.zip",
)


def _resolve_csv_path() -> Path | None:
    """Return the first existing cached CSV path, or extract one from a cached ZIP."""
    for candidate in CACHE_CANDIDATES:
        if candidate.exists():
            logger.info("Using cached CSV at %s", candidate)
            return candidate
    for zip_candidate in ZIP_CACHE_CANDIDATES:
        if not zip_candidate.exists():
            continue
        logger.info("Extracting cached CSV from %s", zip_candidate)
        extracted = PROJECT_ROOT / "data" / "raw" / "scorecard_cache"
        extracted.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_candidate) as zf:
            csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not csv_names:
                continue
            out_path = extracted / "Most-Recent-Cohorts-Institution.csv"
            out_path.write_bytes(zf.read(csv_names[0]))
            logger.info("Extracted cached CSV to %s", out_path)
            return out_path
    return None


def main() -> int:
    source = SourceConfig(
        name="college_scorecard_institution",
        namespace="bronze",
        table="college_scorecard_institution",
        fetch={"bulk_csv_download": {}},
        entities={
            "institutions": (
                "College Scorecard institution-level cost of attendance, net price, "
                "tuition, and living cost (4-year + bachelor's-predominant)"
            )
        },
        dedup_grain=["unitid"],
        cache_dir=PROJECT_ROOT / "data" / "raw" / "scorecard_cache",
    )
    manifest = DomainManifest(
        name="futureproof-data",
        version="0.1",
        description="ingest runner",
        sources=[],
        hints=DomainHints(),
        pipeline={},
    )

    ingestor = CollegeScorecardInstitutionIngestor(source, manifest)

    csv_path = _resolve_csv_path()
    fetch_kwargs: dict = {}
    if csv_path is not None:
        fetch_kwargs["csv_path"] = str(csv_path)

    results = ingestor.ingest(method="bulk_csv_download", **fetch_kwargs)
    logger.info("Ingest results: %s", results)

    # Verify row count via DuckDB against the persistent warehouse.
    from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

    catalog = get_catalog(
        brightsmith.config.WAREHOUSE_PATH,
        brightsmith.config.CATALOG_PATH,
    )
    table = catalog.load_table("bronze.college_scorecard_institution")
    rows = read_with_duckdb(table)
    logger.info("bronze.college_scorecard_institution row count: %d", len(rows))

    diff = abs(len(rows) - EXPECTED_ROWS)
    if diff > ROW_TOLERANCE:
        logger.error(
            "Row count %d deviates from expected %d by more than tolerance %d",
            len(rows),
            EXPECTED_ROWS,
            ROW_TOLERANCE,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
