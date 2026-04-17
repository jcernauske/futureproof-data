"""Rebuild the entire FutureProof data pipeline from scratch.

Downloads all source data from public URLs, runs raw ingest into Bronze,
transforms through Silver, and builds Gold consumable tables.

Usage:
    uv run python scripts/rebuild_all.py
"""

import importlib
import logging
import subprocess
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

from brightsmith.domain_loader import (
    DomainHints,
    DomainManifest,
    SourceConfig,
    load_manifest,
)

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
    """Build a lightweight manifest stub.

    rebuild_all supplies explicit per-ingestor SourceConfigs via
    _make_source_config() — the ingestors do not actually read the manifest's
    sources list, they only need a DomainManifest object for constructor
    signatures. load_manifest() cannot parse the multi-table onet.yaml
    (missing 'table' key) and resolves source paths inconsistently across
    call sites, so we skip it entirely and return a stub.
    """
    return DomainManifest(
        name="futureproof-data",
        version="0.1",
        description="rebuild_all runner stub",
        sources=[],
        hints=DomainHints(),
        pipeline={},
    )


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


def ingest_karpathy_ai_exposure(manifest: DomainManifest) -> dict:
    """Ingest Karpathy AI exposure scores."""
    from raw.karpathy_ai_exposure_ingestor import KarpathyAiExposureIngestor

    source = _make_source_config(
        "karpathy_ai_exposure", "bronze", "karpathy_ai_exposure",
        fetch={"github_download": {}},
        entities={"karpathy": "Karpathy AI Exposure Scores — All Scored Occupations"},
        dedup_grain=["slug"],
    )
    ingestor = KarpathyAiExposureIngestor(source, manifest)
    return ingestor.ingest(method="github_download")


def ingest_bea_rpp(manifest: DomainManifest) -> dict:
    """Ingest BEA Regional Price Parities (Bronze zone).

    Runs as a subprocess so the script retains the framework-default
    project_name ('brightsmith') required by the Bronze HIGH-1 fix
    (governance/adversarial-audits/raw-ingest-bea-rpp.md). This rebuild
    script sets project_name='futureproof-data' module-wide, which would
    otherwise bind the Iceberg catalog_name to a value the dq_runner and
    downstream readers cannot resolve.
    """
    script = PROJECT_ROOT / "scripts" / "ingest_bea_rpp.py"
    proc = subprocess.run(
        ["uv", "run", "python", str(script)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.stdout:
        for line in proc.stdout.splitlines():
            logger.info("[ingest_bea_rpp] %s", line)
    if proc.stderr:
        for line in proc.stderr.splitlines():
            logger.info("[ingest_bea_rpp] %s", line)
    if proc.returncode != 0:
        raise RuntimeError(f"ingest_bea_rpp.py failed with returncode={proc.returncode}")
    return {"script": str(script), "returncode": proc.returncode}


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
    """Ingest all O*NET tables (6 ingestors sharing one ZIP download)."""
    from raw.onet_ingestor import (
        OnetExperienceIngestor,
        OnetOccupationsIngestor,
        OnetRelatedOccupationsIngestor,
        OnetTaskStatementsIngestor,
        OnetWorkActivitiesIngestor,
        OnetWorkContextIngestor,
    )

    onet_tables = [
        ("onet_occupations", OnetOccupationsIngestor, ["onet_soc_code"]),
        ("onet_task_statements", OnetTaskStatementsIngestor, ["onet_soc_code", "task_id"]),
        ("onet_work_activities", OnetWorkActivitiesIngestor, ["onet_soc_code", "element_id", "scale_id"]),
        ("onet_work_context", OnetWorkContextIngestor, ["onet_soc_code", "element_id", "scale_id", "category"]),
        ("onet_related_occupations", OnetRelatedOccupationsIngestor, ["onet_soc_code", "related_onet_soc_code"]),
        ("onet_experience", OnetExperienceIngestor, ["onet_soc_code", "element_id", "scale_id", "category"]),
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


def transform_silver_onet_experience() -> dict:
    """Silver base.onet_experience_profiles (depends on base.onet_occupations)."""
    from silver.onet_experience_transformer import transform
    return transform(project_dir=PROJECT_ROOT)


def transform_silver_cip_soc_crosswalk() -> dict:
    """CIP-SOC crosswalk depends on Silver scorecard, BLS, and O*NET tables."""
    from silver.cip_soc_crosswalk_transformer import transform
    return transform(project_dir=PROJECT_ROOT)


def transform_silver_karpathy_ai_exposure() -> dict:
    """Karpathy AI exposure depends on Silver base.bls_ooh for SOC resolution."""
    from silver.karpathy_ai_exposure_transformer import transform
    return transform(project_dir=PROJECT_ROOT)


def transform_silver_bea_rpp() -> dict:
    """Promote bronze.bea_rpp to base.bea_rpp (Silver zone).

    Runs as a subprocess for the same Bronze HIGH-1 reason documented on
    ``ingest_bea_rpp`` — the dedicated runner keeps the framework default
    project_name so writer and reader resolve the same catalog_name.
    """
    script = PROJECT_ROOT / "scripts" / "promote_bea_rpp_silver.py"
    proc = subprocess.run(
        ["uv", "run", "python", str(script)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.stdout:
        for line in proc.stdout.splitlines():
            logger.info("[promote_bea_rpp_silver] %s", line)
    if proc.stderr:
        for line in proc.stderr.splitlines():
            logger.info("[promote_bea_rpp_silver] %s", line)
    if proc.returncode != 0:
        raise RuntimeError(f"promote_bea_rpp_silver.py failed with returncode={proc.returncode}")
    return {"script": str(script), "returncode": proc.returncode}


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


def transform_gold_ai_exposure() -> dict:
    from gold.ai_exposure_transformer import transform
    return transform(project_dir=PROJECT_ROOT)


def transform_gold_futureproof_engine() -> dict:
    from gold.futureproof_engine import transform
    return transform()


def transform_gold_regional_price_parities() -> dict:
    """Promote base.bea_rpp to consumable.regional_price_parities (Gold).

    Runs as a subprocess for the same Bronze HIGH-1 reason documented on
    ``ingest_bea_rpp`` and ``transform_silver_bea_rpp`` — the dedicated
    runner keeps the framework default project_name so writer and reader
    resolve the same catalog_name, bypassing the rebuild_all module-level
    ``project_name='futureproof-data'`` override.
    """
    script = PROJECT_ROOT / "scripts" / "promote_regional_price_parities.py"
    proc = subprocess.run(
        ["uv", "run", "python", str(script)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.stdout:
        for line in proc.stdout.splitlines():
            logger.info("[promote_regional_price_parities] %s", line)
    if proc.stderr:
        for line in proc.stderr.splitlines():
            logger.info("[promote_regional_price_parities] %s", line)
    if proc.returncode != 0:
        raise RuntimeError(
            f"promote_regional_price_parities.py failed with returncode={proc.returncode}"
        )
    return {"script": str(script), "returncode": proc.returncode}


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
    results.append(_run_step("Karpathy AI Exposure", "raw", ingest_karpathy_ai_exposure, manifest))
    results.append(_run_step("BEA RPP", "raw", ingest_bea_rpp, manifest))

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
    # O*NET experience profiles depends on base.onet_occupations (same zone)
    results.append(_run_step(
        "Silver O*NET Experience", "silver", transform_silver_onet_experience
    ))
    # CIP-SOC crosswalk depends on the above three
    results.append(_run_step("Silver CIP-SOC Crosswalk", "silver", transform_silver_cip_soc_crosswalk))
    # Karpathy AI exposure depends on Silver BLS OOH
    results.append(_run_step("Silver Karpathy AI Exposure", "silver", transform_silver_karpathy_ai_exposure))
    # BEA RPP is a standalone Silver promote (no cross-source joins)
    results.append(_run_step("Silver BEA RPP", "silver", transform_silver_bea_rpp))

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
    # AI exposure depends only on Silver karpathy_ai_exposure
    results.append(_run_step("Gold AI Exposure", "gold", transform_gold_ai_exposure))
    # Regional price parities is standalone (no cross-source joins)
    results.append(_run_step(
        "Gold Regional Price Parities", "gold", transform_gold_regional_price_parities
    ))
    # FutureProof engine depends on all of the above (reads consumable.ai_exposure)
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
