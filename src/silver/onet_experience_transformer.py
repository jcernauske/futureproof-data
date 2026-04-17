"""Silver zone transformer for base.onet_experience_profiles.

Reads from bronze.onet_experience (Bronze, ~35,998 rows across 4 scales) and
produces base.onet_experience_profiles (~765 rows, one per BLS SOC).

Transformation (per spec docs/specs/onet-experience-requirements.md §Zone 2):

1. Filter to ``scale_id == 'RW'`` AND ``element_id == '3.A.1'`` (Related Work
   Experience; the other three scales RL/PT/OJ are dropped).
2. Per O*NET-SOC code compute the weighted-median RW category using
   ``data_value`` as the weight. Cumulative frequency walk; first category
   whose running total reaches or crosses 50% is the median. When cumulative
   frequency lands exactly on a boundary (== 50.0) the LOWER (more
   conservative) category wins — human-approved in
   ``governance/approvals/onet-experience-requirements-open-decisions.md``
   Decision 1.
3. Map median category → midpoint years using the human-approved lookup
   (Decision 2; category 11 → 12.0). Same approval file.
4. Derive four-tier classifier from ``experience_years_typical`` using the
   approved thresholds: 0–1 entry, 1–4 early, 4–8 mid, 8+ senior (right-open
   on all but the final bucket — see ``derive_experience_tier``).
5. Aggregate O*NET-SOC (XX-XXXX.XX) to BLS SOC (XX-XXXX) by unweighted
   averaging of ``experience_years_typical`` across O*NET details
   (Decision 3). Tier is re-derived from the averaged years; distribution
   is merged (unweighted average per category across contributing details).
6. Store the per-category distribution as a JSON string for downstream
   diagnostics.

Every output field is NOT NULL. Occupations with no RW rows (or zero total
weight) are skipped rather than producing a null-laden row — see spec
§Test Matrix case 1.
"""

from __future__ import annotations

import datetime
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from pyiceberg.schema import Schema
from pyiceberg.types import (
    BooleanType,
    DateType,
    DoubleType,
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
# Constants (human-approved 2026-04-16; see approvals file in module docstring)
# ---------------------------------------------------------------------------

SPEC_NAME = "silver-base-onet-experience"

# Filters applied to bronze.onet_experience rows before any derivation.
RW_SCALE_ID = "RW"
RW_ELEMENT_ID = "3.A.1"

# Human-approved midpoint years for each of the 11 RW categories.
# Decision 2 in governance/approvals/onet-experience-requirements-open-decisions.md.
# Category 11 ("Over 10 years") resolves to 12.0 years.
CATEGORY_MIDPOINT_YEARS: dict[int, float] = {
    1: 0.0,
    2: 0.0,
    3: 0.17,
    4: 0.38,
    5: 0.75,
    6: 1.5,
    7: 3.0,
    8: 5.0,
    9: 7.0,
    10: 9.0,
    11: 12.0,
}

# Allowed RW category range (used for validation + distribution emission).
MIN_RW_CATEGORY = 1
MAX_RW_CATEGORY = 11

# Tie tolerance for float-compared cumulative frequency at the 50% boundary.
# Per EDA, per-(occupation × scale) frequency sums are within ±0.03 of 100,
# so a cumulative frequency of 50.0 ± 1e-9 is the realistic precision band.
_TIE_EPS = 1e-9


# ---------------------------------------------------------------------------
# Pure helpers (unit-testable without Iceberg)
# ---------------------------------------------------------------------------

def truncate_to_bls_soc(onet_soc_code: str) -> str:
    """Truncate O*NET-SOC (XX-XXXX.XX) to BLS SOC (XX-XXXX).

    Mirrors ``silver.onet_transformer.truncate_to_bls_soc``. Kept local for
    encapsulation — these two transformers deliberately don't cross-import.
    """
    return onet_soc_code.split(".")[0]


def weighted_median_category(
    distribution: dict[int, float],
) -> int | None:
    """Compute the weighted median RW category via cumulative-frequency walk.

    Args:
        distribution: category (1–11) → percent frequency. Categories with
            weight 0 are allowed; categories absent from the dict are treated
            as weight 0.

    Returns:
        The smallest category index whose cumulative frequency reaches or
        crosses 50% of the total weight. Ties at exactly 50% resolve to the
        LOWER-numbered category (human-approved Decision 1, §Tie-breaking).
        Returns ``None`` if the total weight is zero (no usable rows).
    """
    total = sum(w for w in distribution.values() if w is not None)
    if total <= 0.0:
        return None

    half = total / 2.0
    cumulative = 0.0
    for cat in range(MIN_RW_CATEGORY, MAX_RW_CATEGORY + 1):
        weight = distribution.get(cat, 0.0) or 0.0
        cumulative += weight
        # `>= half - _TIE_EPS` captures both the strict-crossing case and the
        # exact-50% tie case. Because we iterate categories in ascending order
        # the FIRST category to satisfy the condition is returned — this is
        # the lower-numbered category in a tie. Approved tie-break rule.
        if cumulative >= half - _TIE_EPS:
            return cat
    # Numerical fallback — shouldn't happen when total > 0 and we hit every cat
    return MAX_RW_CATEGORY


def derive_experience_tier(years: float) -> str:
    """Bucket ``experience_years_typical`` into the four approved tiers.

    Thresholds (right-inclusive except the open-ended senior bucket):

    * 0 ≤ years ≤ 1        → ``"entry"``
    * 1 < years ≤ 4        → ``"early"``
    * 4 < years ≤ 8        → ``"mid"``
    * 8 < years            → ``"senior"``

    Human-approved Decision 1. Exact boundaries go to the LOWER tier
    (entry/early/mid) so 1.0, 4.0, and 8.0 resolve deterministically to
    entry, early, and mid respectively.
    """
    if years <= 1.0:
        return "entry"
    if years <= 4.0:
        return "early"
    if years <= 8.0:
        return "mid"
    return "senior"


def _median_from_category_or_none(cat: int | None) -> float | None:
    """Map a median category to its approved midpoint years, or None."""
    if cat is None:
        return None
    return CATEGORY_MIDPOINT_YEARS[cat]


def _argmax_category(distribution: dict[int, float]) -> int:
    """Mode of the distribution; ties broken by lower-numbered category.

    Only called when the distribution has at least one nonzero weight (the
    caller skips zero-total rows before aggregation).
    """
    best_cat = MIN_RW_CATEGORY
    best_weight = -1.0
    for cat in range(MIN_RW_CATEGORY, MAX_RW_CATEGORY + 1):
        weight = distribution.get(cat, 0.0) or 0.0
        if weight > best_weight:
            best_weight = weight
            best_cat = cat
    return best_cat


def _normalize_distribution(distribution: dict[int, float]) -> dict[str, float]:
    """Emit the JSON-ready {category-as-string: weight} representation.

    Rounds to 4 decimal places for compact output (source percentages are
    published to 2 decimals by O*NET; 4 dp preserves any averaging residual
    for multi-detail rows). Categories with zero weight ARE included so the
    JSON is self-describing across all 11 categories.
    """
    return {
        str(cat): round(distribution.get(cat, 0.0) or 0.0, 4)
        for cat in range(MIN_RW_CATEGORY, MAX_RW_CATEGORY + 1)
    }


# ---------------------------------------------------------------------------
# Iceberg schema (matches governance/models/silver-base-onet-experience-physical.md)
# ---------------------------------------------------------------------------

def get_experience_profiles_schema() -> Schema:
    """Iceberg schema for base.onet_experience_profiles (11 fields)."""
    return Schema(
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "bls_soc_code", StringType(), required=True),
        NestedField(3, "experience_category_median", IntegerType(), required=True),
        NestedField(4, "experience_years_typical", DoubleType(), required=True),
        NestedField(5, "experience_tier", StringType(), required=True),
        NestedField(6, "experience_category_mode", IntegerType(), required=True),
        NestedField(7, "experience_distribution", StringType(), required=True),
        NestedField(8, "onet_details_averaged", IntegerType(), required=True),
        NestedField(9, "suppress_flag", BooleanType(), required=True),
        NestedField(10, "source_load_date", DateType(), required=True),
        NestedField(11, "ingested_at", TimestampType(), required=True),
    )


# ---------------------------------------------------------------------------
# Transformation logic
# ---------------------------------------------------------------------------

def _group_rw_rows_by_onet_soc(
    rows: Iterable[dict],
) -> dict[str, dict[str, object]]:
    """Group Bronze rows down to {onet_soc_code: {distribution, suppress, load_date}}.

    Only rows passing the RW/element filter are accepted. Rows without
    ``data_value`` (None) are treated as weight 0. ``recommend_suppress``
    is OR-reduced across all contributing rows — "Y" on any row flips
    ``suppress`` to True. The earliest ``load_date`` seen is retained; this
    is a provenance marker only and the precise choice does not affect Silver
    semantics (all rows for a given occupation share the same load_date
    in practice).
    """
    grouped: dict[str, dict[str, object]] = {}
    for row in rows:
        if row.get("scale_id") != RW_SCALE_ID:
            continue
        if row.get("element_id") != RW_ELEMENT_ID:
            continue
        onet_soc = row.get("onet_soc_code")
        if not isinstance(onet_soc, str) or not onet_soc:
            continue
        category = row.get("category")
        if category is None:
            continue
        try:
            cat_int = int(category)
        except (TypeError, ValueError):
            continue
        if cat_int < MIN_RW_CATEGORY or cat_int > MAX_RW_CATEGORY:
            continue

        weight_raw = row.get("data_value")
        if weight_raw is None:
            weight = 0.0
        else:
            try:
                weight = float(weight_raw)
            except (TypeError, ValueError):
                weight = 0.0

        bucket = grouped.get(onet_soc)
        if bucket is None:
            bucket = {
                "distribution": {
                    c: 0.0 for c in range(MIN_RW_CATEGORY, MAX_RW_CATEGORY + 1)
                },
                "suppress": False,
                "load_date": row.get("load_date"),
            }
            grouped[onet_soc] = bucket
        dist: dict[int, float] = bucket["distribution"]  # type: ignore[assignment]
        dist[cat_int] = dist.get(cat_int, 0.0) + weight
        if row.get("recommend_suppress") == "Y":
            bucket["suppress"] = True
        if bucket.get("load_date") is None:
            bucket["load_date"] = row.get("load_date")

    return grouped


def _derive_onet_detail(
    distribution: dict[int, float],
    suppress: bool,
    load_date: datetime.date | None,
) -> dict | None:
    """Derive a single-O*NET-SOC detail record, or None if no usable data.

    Returns the per-detail fields that the BLS-level aggregator will merge:
    median category, years, tier, mode, distribution, suppress flag, load date.
    """
    median_cat = weighted_median_category(distribution)
    if median_cat is None:
        return None
    years = _median_from_category_or_none(median_cat)
    if years is None:
        return None
    mode_cat = _argmax_category(distribution)
    return {
        "distribution": distribution,
        "median_category": median_cat,
        "years": years,
        "tier": derive_experience_tier(years),
        "mode_category": mode_cat,
        "suppress": suppress,
        "load_date": load_date,
    }


def _aggregate_to_bls(
    details: dict[str, dict],
    valid_bls_socs: set[str] | None,
    now: datetime.datetime,
) -> list[dict]:
    """Aggregate per-O*NET-SOC details up to BLS SOC grain.

    Multi-detail aggregation rules (human-approved Decision 3):
      * ``experience_years_typical``: unweighted mean of per-detail years.
      * ``experience_category_median``: re-derived from the merged
        (unweighted-mean) per-category distribution, not averaged from
        per-detail medians. This is consistent with what a single analyst
        looking at the combined distribution would compute.
      * ``experience_tier``: re-derived from the averaged years (NOT from
        per-detail tiers) so the bucket boundaries apply at the BLS grain.
      * ``experience_category_mode``: argmax of the merged distribution.
      * ``experience_distribution``: per-category unweighted mean across
        contributing details (so the JSON still sums to ~100).
      * ``suppress_flag``: OR across details.
      * ``onet_details_averaged``: count of contributing details.

    If ``valid_bls_socs`` is not None, only BLS SOC codes in that set are
    emitted. Missing-from-set rows are silently skipped; we LEFT-JOIN against
    the occupations table rather than error (per spec §Implementation).
    """
    # Group details by BLS SOC
    by_bls: dict[str, list[dict]] = defaultdict(list)
    for onet_soc, detail in details.items():
        bls_soc = truncate_to_bls_soc(onet_soc)
        by_bls[bls_soc].append(detail)

    records: list[dict] = []
    for bls_soc, group in sorted(by_bls.items()):
        if valid_bls_socs is not None and bls_soc not in valid_bls_socs:
            # Referential-integrity-style filter: skip BLS SOCs that are not
            # present in base.onet_occupations. Matches the spec's LEFT JOIN
            # intent — don't error, just drop.
            logger.debug(
                "Skipping %s: not found in base.onet_occupations", bls_soc
            )
            continue

        # Merge per-category distributions by unweighted mean across details
        n_details = len(group)
        merged_distribution: dict[int, float] = {}
        for cat in range(MIN_RW_CATEGORY, MAX_RW_CATEGORY + 1):
            total = sum(d["distribution"].get(cat, 0.0) for d in group)
            merged_distribution[cat] = total / n_details

        # Unweighted mean of years across details (human-approved)
        years = sum(d["years"] for d in group) / n_details

        # Re-derive median from the merged distribution
        merged_median = weighted_median_category(merged_distribution)
        if merged_median is None:
            # Defensive: should not happen — each detail contributed non-zero
            # weight by construction in _derive_onet_detail.
            logger.warning(
                "Merged distribution for %s had zero total weight; skipping",
                bls_soc,
            )
            continue

        merged_mode = _argmax_category(merged_distribution)
        tier = derive_experience_tier(years)
        suppress = any(d["suppress"] for d in group)

        # Pick the earliest non-null load_date for determinism
        load_dates = [d["load_date"] for d in group if d["load_date"] is not None]
        load_date = min(load_dates) if load_dates else None
        if load_date is None:
            # Bronze should always carry load_date; skip if genuinely missing
            # because the Silver schema marks source_load_date NOT NULL.
            logger.warning(
                "No load_date for %s — skipping", bls_soc
            )
            continue

        record = {
            "bls_soc_code": bls_soc,
            "experience_category_median": merged_median,
            "experience_years_typical": round(years, 4),
            "experience_tier": tier,
            "experience_category_mode": merged_mode,
            "experience_distribution": json.dumps(
                _normalize_distribution(merged_distribution),
                sort_keys=True,
            ),
            "onet_details_averaged": n_details,
            "suppress_flag": suppress,
            "source_load_date": load_date,
            "ingested_at": now,
        }
        record["record_id"] = compute_grain_id(
            record, ["bls_soc_code"], prefix="exp"
        )
        records.append(record)

    return records


def transform_experience_profiles(
    bronze_rows: Iterable[dict],
    valid_bls_socs: set[str] | None,
    now: datetime.datetime,
) -> list[dict]:
    """Pure transformation: Bronze rows → Silver records.

    Exposed separately from ``transform()`` for unit testing without Iceberg
    I/O. ``valid_bls_socs`` may be None to disable the referential-integrity
    filter (used in some unit tests); in production it is the BLS SOC set
    from ``base.onet_occupations``.
    """
    grouped = _group_rw_rows_by_onet_soc(bronze_rows)

    per_detail: dict[str, dict] = {}
    for onet_soc, bucket in grouped.items():
        detail = _derive_onet_detail(
            bucket["distribution"],  # type: ignore[arg-type]
            bool(bucket["suppress"]),
            bucket.get("load_date"),  # type: ignore[arg-type]
        )
        if detail is None:
            # Empty / zero-total distribution: skip this O*NET-SOC entirely
            logger.debug(
                "Skipping %s: empty or zero-weight RW distribution", onet_soc
            )
            continue
        per_detail[onet_soc] = detail

    return _aggregate_to_bls(per_detail, valid_bls_socs, now)


# ---------------------------------------------------------------------------
# Iceberg I/O
# ---------------------------------------------------------------------------

def _read_bronze_experience(project_dir: Path) -> list[dict]:
    """Read bronze.onet_experience into a list of dicts."""
    warehouse = project_dir / "data" / "bronze" / "iceberg_warehouse"
    catalog_path = project_dir / "data" / "catalog" / "catalog.db"
    catalog = get_catalog(warehouse, catalog_path)
    tbl = catalog.load_table("bronze.onet_experience")
    rows = read_with_duckdb(tbl)
    logger.info("Read %d rows from bronze.onet_experience", len(rows))
    return rows


def _read_valid_bls_socs(project_dir: Path) -> set[str] | None:
    """Read bls_soc_code set from base.onet_occupations for a LEFT JOIN filter.

    Returns None if the Silver occupations table does not yet exist — in that
    case the transformer falls through without the referential-integrity
    filter (spec: "don't error on missing"). In production this table is
    always present before this transformer runs (see scripts/rebuild_all.py
    ordering).
    """
    warehouse = project_dir / "data" / "silver" / "iceberg_warehouse"
    catalog_path = project_dir / "data" / "catalog" / "catalog.db"
    try:
        catalog = get_catalog(warehouse, catalog_path)
        tbl = catalog.load_table("base.onet_occupations")
    except Exception as exc:
        logger.warning(
            "base.onet_occupations not available for FK filter (%s); "
            "proceeding without referential-integrity filter.",
            exc,
        )
        return None
    rows = read_with_duckdb(tbl)
    return {r["bls_soc_code"] for r in rows if r.get("bls_soc_code")}


def _get_silver_catalog(project_dir: Path):
    """Get the Silver zone catalog."""
    warehouse = project_dir / "data" / "silver" / "iceberg_warehouse"
    catalog_path = project_dir / "data" / "catalog" / "catalog.db"
    return get_catalog(warehouse, catalog_path)


def transform(project_dir: str | Path | None = None) -> dict:
    """Run the Silver base.onet_experience_profiles transformation.

    Returns a summary dict shaped like ``silver.onet_transformer.transform``:

        {
            "rows_transformed": int,
            "promoted": int,
            "skipped_dedup": int,
            "snapshot_id": int | None,
            "rows": int,         # alias for rows_transformed
            "skipped": int,      # alias for skipped_dedup
        }
    """
    project_dir = Path(project_dir or ".").resolve()
    now = datetime.datetime.now(tz=datetime.timezone.utc)

    logger.info("Reading Bronze bronze.onet_experience...")
    bronze = _read_bronze_experience(project_dir)

    logger.info("Reading base.onet_occupations for FK filter...")
    valid_bls_socs = _read_valid_bls_socs(project_dir)
    if valid_bls_socs is not None:
        logger.info(
            "Applying referential-integrity filter against %d BLS SOC codes",
            len(valid_bls_socs),
        )

    logger.info("Transforming to base.onet_experience_profiles...")
    records = transform_experience_profiles(bronze, valid_bls_socs, now)
    logger.info("Produced %d experience profile records", len(records))

    catalog = _get_silver_catalog(project_dir)
    table = get_or_create_table(
        catalog, "base", "onet_experience_profiles", get_experience_profiles_schema()
    )
    result = promote(
        table,
        records,
        id_field="record_id",
        spec_name=SPEC_NAME,
        agent_name="bs:primary-agent",
    )
    logger.info(
        "base.onet_experience_profiles: %d promoted, %d skipped",
        result["promoted"],
        result["skipped"],
    )

    return {
        "rows_transformed": len(records),
        "promoted": result["promoted"],
        "skipped_dedup": result["skipped"],
        "snapshot_id": result.get("snapshot_id"),
        # Aliased names some callers expect
        "rows": len(records),
        "skipped": result["skipped"],
    }
