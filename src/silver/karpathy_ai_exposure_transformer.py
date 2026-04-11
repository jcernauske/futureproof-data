"""Silver zone transformer for Karpathy AI Exposure base table.

Reads bronze.karpathy_ai_exposure from the Bronze zone (342 rows) and produces
base.karpathy_ai_exposure with:
  - SOC code normalization (XX-XXXX format, whitespace stripped)
  - Null SOC resolution via title matching against base.bls_ooh
  - Broad SOC code expansion (XX-XXX0 -> all detailed codes in BLS OOH)
  - Broad-to-broad exact match detection (4 codes match BLS as broad codes)
  - Post-expansion deduplication by soc_code (highest num_jobs_2024 wins)
  - bls_match flag and soc_resolved_method classification
  - Idempotent promotion via the Brightsmith promote pattern

Expected output: ~400-500 rows (342 Bronze + ~70 from broad expansion
+ ~28 from title matching - duplicates).
"""

import datetime
import logging
import re
from pathlib import Path

from pyiceberg.schema import Schema
from pyiceberg.types import (
    BooleanType,
    DateType,
    IntegerType,
    NestedField,
    StringType,
    TimestampType,
)

from brightsmith.infra.grain import compute_grain_id
from brightsmith.infra.iceberg_setup import get_catalog, get_or_create_table, read_with_duckdb
from brightsmith.infra.promote import promote

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GRAIN_FIELDS = ["soc_code"]
SLUG_GRAIN_FIELDS = ["slug"]
SPEC_NAME = "silver-base-karpathy-ai-exposure"

_SOC_PATTERN = re.compile(r"^\d{2}-\d{4}$")
_BROAD_SOC_PATTERN = re.compile(r"^\d{2}-\d{3}0$")


def get_silver_schema() -> Schema:
    """Iceberg schema for base.karpathy_ai_exposure."""
    return Schema(
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "soc_code", StringType(), required=False),
        NestedField(3, "slug", StringType(), required=True),
        NestedField(4, "occupation_title", StringType(), required=True),
        NestedField(5, "category", StringType(), required=True),
        NestedField(6, "exposure_score", IntegerType(), required=True),
        NestedField(7, "rationale", StringType(), required=True),
        NestedField(8, "bls_match", BooleanType(), required=True),
        NestedField(9, "soc_resolved_method", StringType(), required=True),
        NestedField(10, "source_load_date", DateType(), required=True),
        NestedField(11, "ingested_at", TimestampType(), required=True),
    )


def _normalize_soc_code(soc_code: str | None) -> str | None:
    """Strip whitespace from SOC code, return None if empty/null."""
    if soc_code is None:
        return None
    soc_code = soc_code.strip()
    if not soc_code:
        return None
    return soc_code


def _is_broad_soc(soc_code: str) -> bool:
    """Check if a SOC code is a broad code (XX-XXX0 pattern)."""
    return bool(_BROAD_SOC_PATTERN.match(soc_code))


def _is_valid_soc(soc_code: str) -> bool:
    """Check if a SOC code matches XX-XXXX format."""
    return bool(_SOC_PATTERN.match(soc_code))


def build_bls_soc_lookup(bls_rows: list[dict]) -> dict[str, str]:
    """Build a set of BLS SOC codes and a title -> soc_code lookup.

    Returns a dict mapping lowercase occupation_title -> soc_code for
    title-based resolution.
    """
    return {
        row["occupation_title"].lower().strip(): row["soc_code"]
        for row in bls_rows
        if row.get("soc_code") and row.get("occupation_title")
    }


def build_bls_soc_set(bls_rows: list[dict]) -> set[str]:
    """Build a set of all SOC codes in BLS OOH."""
    return {
        row["soc_code"]
        for row in bls_rows
        if row.get("soc_code")
    }


def build_bls_prefix_map(bls_soc_set: set[str]) -> dict[str, list[str]]:
    """Build a map from 6-char prefix (e.g. '15-123') to list of detailed codes.

    Only includes non-broad codes (last digit != 0) as expansion targets.
    """
    prefix_map: dict[str, list[str]] = {}
    for soc in bls_soc_set:
        if _is_valid_soc(soc) and not _is_broad_soc(soc):
            prefix = soc[:6]
            prefix_map.setdefault(prefix, []).append(soc)
    # Sort each list for deterministic output
    for prefix in prefix_map:
        prefix_map[prefix].sort()
    return prefix_map


def title_match(
    occupation_title: str,
    bls_title_lookup: dict[str, str],
) -> list[str]:
    """Attempt to resolve a SOC code from occupation title.

    Strategy:
    1. Exact case-insensitive match
    2. Substring match: BLS title contained in Karpathy title
    3. Substring match: Karpathy title contained in BLS title

    Returns list of matched SOC codes (may be empty or multiple).
    """
    title_lower = occupation_title.lower().strip()

    # 1. Exact match
    if title_lower in bls_title_lookup:
        return [bls_title_lookup[title_lower]]

    # 2. BLS title is a substring of Karpathy title (e.g. "Marketing managers"
    #    is contained in "Advertising, promotions, and marketing managers")
    matches = []
    for bls_title, soc in bls_title_lookup.items():
        if bls_title in title_lower or title_lower in bls_title:
            matches.append(soc)

    return sorted(set(matches))


def transform_rows(
    bronze_rows: list[dict],
    bls_rows: list[dict],
) -> list[dict]:
    """Transform Bronze rows into Silver base rows.

    Performs:
    1. SOC code normalization
    2. Null SOC resolution via title matching
    3. Broad SOC expansion
    4. Post-expansion deduplication
    5. record_id computation
    6. bls_match and soc_resolved_method derivation

    Args:
        bronze_rows: Rows from bronze.karpathy_ai_exposure.
        bls_rows: Rows from base.bls_ooh (for SOC cross-validation).

    Returns:
        List of Silver base rows ready for promotion.
    """
    bls_soc_set = build_bls_soc_set(bls_rows)
    bls_title_lookup = build_bls_soc_lookup(bls_rows)
    bls_prefix_map = build_bls_prefix_map(bls_soc_set)
    now = datetime.datetime.now(tz=datetime.timezone.utc)

    silver_rows: list[dict] = []

    for raw in bronze_rows:
        soc_code = _normalize_soc_code(raw.get("soc_code"))
        slug = raw["slug"]
        occupation_title = raw["occupation_title"]
        category = raw["category"]
        exposure_score = int(raw["exposure_score"])
        rationale = raw["rationale"]
        source_load_date = raw.get("load_date")
        num_jobs_2024 = raw.get("num_jobs_2024")

        base_fields = {
            "slug": slug,
            "occupation_title": occupation_title,
            "category": category,
            "exposure_score": exposure_score,
            "rationale": rationale,
            "source_load_date": source_load_date,
            "ingested_at": now,
            "_num_jobs_2024": num_jobs_2024,  # temp field for dedup, removed later
        }

        if soc_code is None:
            # Attempt title-based resolution
            matched_socs = title_match(occupation_title, bls_title_lookup)
            if matched_socs:
                # Create a row for each matched SOC
                for matched_soc in matched_socs:
                    row = {**base_fields}
                    row["soc_code"] = matched_soc
                    row["bls_match"] = matched_soc in bls_soc_set
                    row["soc_resolved_method"] = "title_match"
                    silver_rows.append(row)
            else:
                # Unresolved
                row = {**base_fields}
                row["soc_code"] = None
                row["bls_match"] = False
                row["soc_resolved_method"] = "unresolved"
                silver_rows.append(row)

        elif _is_valid_soc(soc_code) and _is_broad_soc(soc_code):
            # Broad code: check for exact match in BLS first
            if soc_code in bls_soc_set:
                # Broad-to-broad exact match -- treat as direct
                row = {**base_fields}
                row["soc_code"] = soc_code
                row["bls_match"] = True
                row["soc_resolved_method"] = "direct"
                silver_rows.append(row)
            else:
                # Try to expand to detailed codes
                prefix = soc_code[:6]
                detailed_codes = bls_prefix_map.get(prefix, [])
                if detailed_codes:
                    for detailed_soc in detailed_codes:
                        row = {**base_fields}
                        row["soc_code"] = detailed_soc
                        row["bls_match"] = True  # by definition, found in BLS
                        row["soc_resolved_method"] = "broad_expansion"
                        silver_rows.append(row)
                else:
                    # No detailed codes found, keep broad code as unresolved
                    row = {**base_fields}
                    row["soc_code"] = soc_code
                    row["bls_match"] = False
                    row["soc_resolved_method"] = "unresolved"
                    silver_rows.append(row)

        elif _is_valid_soc(soc_code):
            # Detailed code, direct match
            row = {**base_fields}
            row["soc_code"] = soc_code
            row["bls_match"] = soc_code in bls_soc_set
            row["soc_resolved_method"] = "direct"
            silver_rows.append(row)

        else:
            # Invalid SOC code format -- treat as unresolved
            logger.warning(
                "Invalid SOC code format '%s' for slug '%s', marking unresolved",
                soc_code, slug,
            )
            row = {**base_fields}
            row["soc_code"] = None
            row["bls_match"] = False
            row["soc_resolved_method"] = "unresolved"
            silver_rows.append(row)

    # Post-expansion deduplication by soc_code (non-null only)
    silver_rows = _dedup_by_soc_code(silver_rows)

    # Compute record_id and remove temp fields
    for row in silver_rows:
        if row["soc_code"] is not None:
            row["record_id"] = compute_grain_id(row, GRAIN_FIELDS, prefix="kai")
        else:
            row["record_id"] = compute_grain_id(row, SLUG_GRAIN_FIELDS, prefix="kai")
        # Remove temp dedup field
        row.pop("_num_jobs_2024", None)

    return silver_rows


def _dedup_by_soc_code(rows: list[dict]) -> list[dict]:
    """Deduplicate rows by soc_code, keeping highest num_jobs_2024.

    For null soc_code rows, no dedup is applied (they are kept as-is).
    Ties in num_jobs_2024 are broken by slug alphabetical order.
    """
    null_soc_rows = [r for r in rows if r["soc_code"] is None]
    non_null_rows = [r for r in rows if r["soc_code"] is not None]

    # Group by soc_code
    groups: dict[str, list[dict]] = {}
    for row in non_null_rows:
        groups.setdefault(row["soc_code"], []).append(row)

    deduped = []
    for soc_code, group in groups.items():
        if len(group) == 1:
            deduped.append(group[0])
        else:
            # Sort: highest num_jobs_2024 first, then alphabetical slug
            group.sort(
                key=lambda r: (
                    -(r.get("_num_jobs_2024") or 0),
                    r.get("slug", ""),
                )
            )
            deduped.append(group[0])
            logger.info(
                "Dedup soc_code %s: kept slug '%s' (num_jobs=%s), dropped %d",
                soc_code, group[0]["slug"],
                group[0].get("_num_jobs_2024"), len(group) - 1,
            )

    return deduped + null_soc_rows


def transform(
    project_dir: str | Path | None = None,
) -> dict:
    """Run the Silver zone transformation.

    Reads bronze.karpathy_ai_exposure from Bronze and base.bls_ooh from Silver,
    transforms, and promotes to base.karpathy_ai_exposure via idempotent
    promote pattern.

    Returns:
        {"rows_read": N, "rows_transformed": M, "promoted": P, ...}
    """
    project_dir = Path(project_dir or ".").resolve()

    bronze_warehouse = project_dir / "data" / "bronze" / "iceberg_warehouse"
    bronze_catalog_path = project_dir / "data" / "catalog" / "catalog.db"
    silver_warehouse = project_dir / "data" / "silver" / "iceberg_warehouse"
    silver_catalog_path = project_dir / "data" / "catalog" / "catalog.db"

    # Read from Bronze
    logger.info("Reading from bronze.karpathy_ai_exposure...")
    bronze_catalog = get_catalog(bronze_warehouse, bronze_catalog_path)
    bronze_table = bronze_catalog.load_table("bronze.karpathy_ai_exposure")
    bronze_rows = read_with_duckdb(bronze_table)
    logger.info("Read %d rows from Bronze", len(bronze_rows))

    # Read BLS OOH for SOC cross-validation and expansion
    logger.info("Reading from base.bls_ooh for SOC resolution...")
    silver_catalog = get_catalog(silver_warehouse, silver_catalog_path)
    bls_table = silver_catalog.load_table("base.bls_ooh")
    bls_rows = read_with_duckdb(bls_table)
    logger.info("Read %d rows from base.bls_ooh", len(bls_rows))

    # Transform
    logger.info("Transforming to Silver base table...")
    silver_rows = transform_rows(bronze_rows, bls_rows)
    logger.info("Transformed %d rows (from %d Bronze)", len(silver_rows), len(bronze_rows))

    # Log method distribution
    method_counts: dict[str, int] = {}
    for row in silver_rows:
        method = row["soc_resolved_method"]
        method_counts[method] = method_counts.get(method, 0) + 1
    logger.info("SOC resolution method distribution: %s", method_counts)

    bls_match_count = sum(1 for r in silver_rows if r["bls_match"])
    logger.info(
        "BLS match rate: %d/%d (%.1f%%)",
        bls_match_count, len(silver_rows),
        100 * bls_match_count / len(silver_rows) if silver_rows else 0,
    )

    # Promote to Silver
    logger.info("Promoting to base.karpathy_ai_exposure...")
    silver_table = get_or_create_table(
        silver_catalog, "base", "karpathy_ai_exposure", get_silver_schema()
    )
    result = promote(
        silver_table,
        silver_rows,
        id_field="record_id",
        spec_name=SPEC_NAME,
        agent_name="@primary-agent",
    )

    logger.info(
        "Promote complete: %d promoted, %d skipped",
        result["promoted"],
        result["skipped"],
    )

    return {
        "rows_read": len(bronze_rows),
        "rows_transformed": len(silver_rows),
        "promoted": result["promoted"],
        "skipped_dedup": result["skipped"],
        "snapshot_id": result.get("snapshot_id"),
        "method_distribution": method_counts,
    }
