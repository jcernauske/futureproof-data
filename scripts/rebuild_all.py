"""Rebuild the entire FutureProof data pipeline from scratch.

Downloads all source data from public URLs, runs raw ingest into Bronze,
transforms through Silver, and builds Gold consumable tables.

Usage:
    uv run python scripts/rebuild_all.py
"""

import importlib
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Ensure project root is on the path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Configure brightsmith to use this project
import brightsmith.config

brightsmith.config.configure(
    project_root=PROJECT_ROOT,
    project_name="futureproof-data",
    require_human_approval=False,
)

from brightsmith.domain_loader import SourceConfig, DomainManifest, load_manifest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("rebuild_all")


@dataclass
class StepResult:
    name: str
    zone: str
    elapsed: float
    detail: str
    ok: bool


def _run_step(name: str, zone: str, fn, *args, **kwargs) -> StepResult:
    """Run a pipeline step with timing and error handling."""
    logger.info("=" * 60)
    logger.info("STEP: %s (%s)", name, zone)
    logger.info("=" * 60)
    t0 = time.time()
    try:
        result = fn(*args, **kwargs)
        elapsed = time.time() - t0
        return StepResult(name, zone, elapsed, str(result), ok=True)
    except Exception as exc:
        elapsed = time.time() - t0
        logger.error("FAILED: %s — %s", name, exc, exc_info=True)
        return StepResult(name, zone, elapsed, str(exc), ok=False)


# ---------------------------------------------------------------------------
# Raw ingest helpers
# ---------------------------------------------------------------------------

def _make_source_config(name: str, namespace: str, table: str,
                        fetch: dict, entities: dict,
                        dedup_grain: list[str]) -> SourceConfig:
    """Build a minimal SourceConfig for an ingestor."""
    return SourceConfig(
        name=name,
        namespace=namespace,
        table=table,
        fetch=fetch,
        entities=entities,
        dedup_grain=dedup_grain,
        cache_dir=PROJECT_ROOT / "data" / "raw",
    )


def _make_manifest() -> DomainManifest:
    """Load the project manifest."""
    return load_manifest(PROJECT_ROOT / "domain" / "manifest.yaml")


def ingest_college_scorecard(manifest: DomainManifest) -> dict:
    """Ingest College Scorecard data."""
    from raw.college_scorecard_ingestor import CollegeScorecardIngestor

    source = _make_source_config(
        "college_scorecard", "bronze", "college_scorecard",
        fetch={"bulk_csv_download": {}},
        entities={"scorecard": "College Scorecard Field of Study (Bachelor's)"},
        dedup_grain=["unitid", "cipcode", "credlev"],
    )
    ingestor = CollegeScorecardIngestor(source, manifest)
    return ingestor.ingest(method="bulk_csv_download")


def ingest_bls_ooh(manifest: DomainManifest) -> dict:
    """Ingest BLS OOH data."""
    from raw.bls_ooh_ingestor import BlsOohIngestor

    source = _make_source_config(
        "bls_ooh", "bronze", "bls_ooh",
        fetch={"xlsx_download": {}},
        entities={"ooh": "BLS Employment Projections — All Detailed Occupations"},
        dedup_grain=["soc_code"],
    )
    ingestor = BlsOohIngestor(source, manifest)
    return ingestor.ingest(method="xlsx_download")


def ingest_cip_soc_crosswalk(manifest: DomainManifest) -> dict:
    """Ingest CIP-SOC crosswalk."""
    from raw.cip_soc_crosswalk_ingestor import CipSocCrosswalkIngestor

    source = _make_source_config(
        "cip_soc_crosswalk", "raw", "cip_soc_crosswalk",
        fetch={"xlsx_download": {}},
        entities={"crosswalk": "NCES CIP 2020 to SOC 2018 Crosswalk"},
        dedup_grain=["cipcode", "soc_code"],
    )
    ingestor = CipSocCrosswalkIngestor(source, manifest)
    return ingestor.ingest(method="xlsx_download")


def ingest_onet(manifest: DomainManifest) -> dict:
    """Ingest all O*NET tables (5 ingestors sharing one ZIP download)."""
    from raw.onet_ingestor import (
        OnetOccupationsIngestor,
        OnetTaskStatementsIngestor,
        OnetWorkActivitiesIngestor,
        OnetWorkContextIngestor,
        OnetRelatedOccupationsIngestor,
    )

    onet_tables = [
        ("onet_occupations", OnetOccupationsIngestor, ["onet_soc_code"]),
        ("onet_task_statements", OnetTaskStatementsIngestor, ["onet_soc_code", "task_id"]),
        ("onet_work_activities", OnetWorkActivitiesIngestor, ["onet_soc_code", "element_id", "scale_id"]),
        ("onet_work_context", OnetWorkContextIngestor, ["onet_soc_code", "element_id", "scale_id", "category"]),
        ("onet_related_occupations", OnetRelatedOccupationsIngestor, ["onet_soc_code", "related_onet_soc_code"]),
    ]

    results = {}
    for table_name, ingestor_cls, grain in onet_tables:
        source = _make_source_config(
            table_name, "bronze", table_name,
            fetch={"bulk_zip_download": {}},
            entities={"onet": f"O*NET — {table_name}"},
            dedup_grain=grain,
        )
        ingestor = ingestor_cls(source, manifest)
        results[table_name] = ingestor.ingest(method="bulk_zip_download")

    return results


# ---------------------------------------------------------------------------
# Silver transform helpers
# ---------------------------------------------------------------------------

def transform_silver_college_scorecard() -> dict:
    from silver.college_scorecard_transformer import transform
    return transform(project_dir=PROJECT_ROOT)


def transform_silver_bls_ooh() -> dict:
    from silver.bls_ooh_transformer import transform
    return transform(project_dir=PROJECT_ROOT)


def transform_silver_onet() -> dict:
    from silver.onet_transformer import transform
    return transform(project_dir=PROJECT_ROOT)


def transform_silver_cip_soc_crosswalk() -> dict:
    """CIP-SOC crosswalk depends on Silver scorecard, BLS, and O*NET tables."""
    from silver.cip_soc_crosswalk_transformer import transform
    return transform(project_dir=PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Gold transform helpers
# ---------------------------------------------------------------------------

def transform_gold_career_outcomes() -> dict:
    from gold.college_scorecard_career_outcomes import transform
    return transform()


def transform_gold_occupation_profiles() -> dict:
    from gold.bls_ooh_occupation_profiles import transform
    return transform()


def transform_gold_onet_work_profiles() -> dict:
    from gold.onet_work_profiles import transform
    return transform()


def transform_gold_career_transitions() -> dict:
    from gold.onet_career_transitions import transform
    return transform()


def transform_gold_futureproof_engine() -> dict:
    from gold.futureproof_engine import transform
    return transform()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    total_start = time.time()
    manifest = _make_manifest()
    results: list[StepResult] = []

    # Phase 1: Raw ingest (Bronze zone)
    logger.info("=" * 60)
    logger.info("PHASE 1: RAW INGEST (Bronze)")
    logger.info("=" * 60)

    results.append(_run_step("College Scorecard", "raw", ingest_college_scorecard, manifest))
    results.append(_run_step("BLS OOH", "raw", ingest_bls_ooh, manifest))
    results.append(_run_step("O*NET (5 tables)", "raw", ingest_onet, manifest))
    results.append(_run_step("CIP-SOC Crosswalk", "raw", ingest_cip_soc_crosswalk, manifest))

    # Check raw phase before continuing
    raw_ok = all(r.ok for r in results)
    if not raw_ok:
        logger.error("Raw ingest had failures — Silver transforms may fail.")

    # Phase 2: Silver transforms
    logger.info("=" * 60)
    logger.info("PHASE 2: SILVER TRANSFORMS")
    logger.info("=" * 60)

    # College Scorecard, BLS, O*NET can run independently
    results.append(_run_step("Silver College Scorecard", "silver", transform_silver_college_scorecard))
    results.append(_run_step("Silver BLS OOH", "silver", transform_silver_bls_ooh))
    results.append(_run_step("Silver O*NET", "silver", transform_silver_onet))
    # CIP-SOC crosswalk depends on the above three
    results.append(_run_step("Silver CIP-SOC Crosswalk", "silver", transform_silver_cip_soc_crosswalk))

    silver_ok = all(r.ok for r in results if r.zone == "silver")
    if not silver_ok:
        logger.error("Silver transforms had failures — Gold transforms may fail.")

    # Phase 3: Gold transforms
    logger.info("=" * 60)
    logger.info("PHASE 3: GOLD TRANSFORMS")
    logger.info("=" * 60)

    # Career outcomes and occupation profiles can run independently
    results.append(_run_step("Gold Career Outcomes", "gold", transform_gold_career_outcomes))
    results.append(_run_step("Gold Occupation Profiles", "gold", transform_gold_occupation_profiles))
    results.append(_run_step("Gold O*NET Work Profiles", "gold", transform_gold_onet_work_profiles))
    # Career transitions depends on work profiles
    results.append(_run_step("Gold Career Transitions", "gold", transform_gold_career_transitions))
    # FutureProof engine depends on all of the above
    results.append(_run_step("Gold FutureProof Engine", "gold", transform_gold_futureproof_engine))

    # Summary
    total_elapsed = time.time() - total_start
    logger.info("")
    logger.info("=" * 60)
    logger.info("REBUILD COMPLETE")
    logger.info("=" * 60)

    passed = sum(1 for r in results if r.ok)
    failed = sum(1 for r in results if not r.ok)

    for r in results:
        status = "OK" if r.ok else "FAIL"
        logger.info("  [%s] %-35s %6.1fs  %s", status, r.name, r.elapsed, r.zone)

    logger.info("")
    logger.info("  %d/%d steps passed in %.1fs", passed, len(results), total_elapsed)

    if failed:
        logger.error("  %d steps FAILED — check logs above", failed)
        sys.exit(1)
    else:
        logger.info("  All steps passed.")


if __name__ == "__main__":
    main()
