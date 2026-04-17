"""Silver zone transformer for Anthropic observed exposure.

Reads ``raw.anthropic_economic_index`` (one row per O*NET task,
~3,500 rows) and produces ``base.anthropic_observed_exposure``
(one row per SOC code, ~700-900 rows) with:

  - SOC normalization to ``XX-XXXX`` format
  - Broad SOC code (``XX-XXX0``) expansion via the BLS prefix map
  - Task-level aggregation to SOC grain via weighted averages
  - ``soc_match`` flag cross-checked against ``base.bls_ooh``
  - Deterministic ``record_id`` via
    ``compute_grain_id(row, ['soc_code'], prefix='aoe')``
  - Idempotent promotion via the Brightsmith promote pattern

Aggregation contract
--------------------
Anthropic's ``pct`` column (``task_pct_v2.csv``) is a **global share
in 0-100 percent units** — the full source table sums to 100.0 across
all tasks. Bronze emits one row per (task, SOC) pair and splits each
task's raw pct by the number of SOCs it maps to, so the invariant
``SUM(task_pct)`` across all Bronze rows = ~100 is preserved across
the many-to-many fan-out.

Under the global-share interpretation:

  observed_exposure_pct(SOC) = SUM(task_pct) for (task, SOC) rows in Bronze

Summing across all SOCs reconstructs ~100 - 1.78 (the ``task_name='none'``
placeholder is excluded here) = ~98.22 of total Claude usage.

Placeholder row (``task_name='none'``) handling:
  Bronze keeps the ``none`` row with ``soc_code=NULL`` for audit
  trail. Silver drops rows with null/unusable SOC before aggregation,
  so this row is excluded from every SOC total and from the final
  Silver output.

Automation & augmentation ratios are weighted averages of the per-
task ratios (already in 0-100 percent units from Bronze's v2 split:
automation = directive + feedback_loop; augmentation = task_iteration
+ validation + learning), weighted by ``task_pct`` (so that tasks
with more observed usage dominate the blend).
"""

from __future__ import annotations

import datetime
import logging
import re
from pathlib import Path
from typing import Any

from pyiceberg.schema import Schema
from pyiceberg.types import (
    BooleanType,
    DoubleType,
    IntegerType,
    NestedField,
    StringType,
    TimestampType,
)

from brightsmith.infra.grain import compute_grain_id
from brightsmith.infra.iceberg_setup import (
    get_catalog,
    get_or_create_table,
    read_with_duckdb,
)
from brightsmith.infra.promote import promote

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GRAIN_FIELDS: list[str] = ["soc_code"]
GRAIN_PREFIX = "aoe"
SPEC_NAME = "silver-base-anthropic-observed-exposure"

_SOC_PATTERN = re.compile(r"^\d{2}-\d{4}$")
_BROAD_SOC_PATTERN = re.compile(r"^\d{2}-\d{3}0$")


def get_silver_schema() -> Schema:
    """Iceberg schema for base.anthropic_observed_exposure."""
    return Schema(
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "soc_code", StringType(), required=True),
        NestedField(3, "soc_title", StringType(), required=False),
        NestedField(4, "observed_exposure_pct", DoubleType(), required=True),
        NestedField(5, "automation_pct", DoubleType(), required=False),
        NestedField(6, "augmentation_pct", DoubleType(), required=False),
        NestedField(7, "task_count", IntegerType(), required=True),
        NestedField(8, "soc_match", BooleanType(), required=True),
        NestedField(9, "source_release", StringType(), required=True),
        NestedField(10, "promoted_at", TimestampType(), required=True),
    )


# ---------------------------------------------------------------------------
# SOC helpers (mirrors karpathy_ai_exposure_transformer conventions)
# ---------------------------------------------------------------------------


def _is_valid_soc(soc_code: str) -> bool:
    """True when soc_code matches XX-XXXX format."""
    return bool(_SOC_PATTERN.match(soc_code))


def _is_broad_soc(soc_code: str) -> bool:
    """True for XX-XXX0 broad codes."""
    return bool(_BROAD_SOC_PATTERN.match(soc_code))


def _normalize_soc_code(soc_code: str | None) -> str | None:
    """Strip whitespace and drop O*NET overlay suffix.

    Handles:
      - "11-1011.00"  -> "11-1011" (O*NET overlay code)
      - "  11-1011 "  -> "11-1011"
      - None / ""     -> None
    """
    if soc_code is None:
        return None
    s = str(soc_code).strip()
    if not s:
        return None
    if "." in s:
        s = s.split(".", 1)[0]
    if not _is_valid_soc(s):
        return None
    return s


def build_bls_soc_set(bls_rows: list[dict]) -> set[str]:
    """Build a set of SOC codes present in base.bls_ooh."""
    return {
        row["soc_code"]
        for row in bls_rows
        if row.get("soc_code")
    }


def build_bls_prefix_map(bls_soc_set: set[str]) -> dict[str, list[str]]:
    """Map 6-char SOC prefix to detailed codes for broad expansion."""
    prefix_map: dict[str, list[str]] = {}
    for soc in bls_soc_set:
        if _is_valid_soc(soc) and not _is_broad_soc(soc):
            prefix = soc[:6]
            prefix_map.setdefault(prefix, []).append(soc)
    for prefix in prefix_map:
        prefix_map[prefix].sort()
    return prefix_map


def _expand_broad_soc(
    soc_code: str,
    bls_soc_set: set[str],
    bls_prefix_map: dict[str, list[str]],
) -> list[str]:
    """Return the list of SOC codes a broad code should fan out to.

    - If the broad code itself is in BLS, keep it as-is.
    - Otherwise expand to all detailed codes sharing its 6-char prefix.
    - If no detailed codes exist, keep the broad code (unmatched).
    """
    if soc_code in bls_soc_set:
        return [soc_code]
    detailed = bls_prefix_map.get(soc_code[:6], [])
    return detailed if detailed else [soc_code]


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _weighted_average(
    values: list[float | None],
    weights: list[float | None],
) -> float | None:
    """Weighted average, skipping rows where value OR weight is None.

    Returns None when there are no valid (value, weight) pairs OR when
    total weight is zero. Falls back to a simple mean when all weights
    are zero/null but at least one value is present (so tasks with
    zero observed usage still contribute something).
    """
    paired = [
        (v, w)
        for v, w in zip(values, weights)
        if v is not None and w is not None
    ]
    if not paired:
        # Try simple mean across non-None values
        non_null = [v for v in values if v is not None]
        if not non_null:
            return None
        return sum(non_null) / len(non_null)

    total_weight = sum(w for _, w in paired)
    if total_weight == 0:
        non_null = [v for v, _ in paired]
        return sum(non_null) / len(non_null)

    return sum(v * w for v, w in paired) / total_weight


def _aggregate_observed_exposure(task_pcts: list[float | None]) -> float:
    """Aggregate per-task pct values into a single SOC-level score.

    See module docstring for the global-share interpretation. Under
    that model, the SOC-level exposure is the SUM of its tasks'
    global shares — i.e. the fraction of all Claude usage attributable
    to that occupation.

    Returns 0.0 (not None) when every task value is null, because the
    spec declares ``observed_exposure_pct`` required.
    """
    values = [v for v in task_pcts if v is not None]
    if not values:
        return 0.0
    total = sum(values)
    # Clamp to [0, 100] to absorb any rounding drift above 100%.
    return max(0.0, min(100.0, total))


# ---------------------------------------------------------------------------
# Core transform
# ---------------------------------------------------------------------------


def transform_rows(
    bronze_rows: list[dict],
    bls_rows: list[dict],
    promoted_at: datetime.datetime | None = None,
) -> list[dict]:
    """Transform Bronze rows into Silver base rows.

    Steps:
      1. Normalize SOC codes; drop tasks with no usable SOC.
      2. Expand broad SOC codes (XX-XXX0) into detailed codes where
         the BLS crosswalk has them.
      3. Group tasks by detailed SOC and aggregate.
      4. Mark soc_match=true when the SOC is present in base.bls_ooh.
      5. Compute record_id via compute_grain_id.

    Args:
        bronze_rows: Rows from raw.anthropic_economic_index.
        bls_rows: Rows from base.bls_ooh (for match flag + expansion).
        promoted_at: Optional UTC timestamp stamped on every row. When
            None, uses ``datetime.now(tz=utc)``.

    Returns:
        List of Silver base rows ready for ``promote()``.
    """
    if promoted_at is None:
        promoted_at = datetime.datetime.now(tz=datetime.timezone.utc)

    bls_soc_set = build_bls_soc_set(bls_rows)
    bls_prefix_map = build_bls_prefix_map(bls_soc_set)

    # Group tasks by detailed SOC, distributing broad-code tasks across
    # all detailed descendants (split-weight: each detailed code gets
    # an equal share of the task's pct).
    tasks_by_soc: dict[str, list[dict]] = {}
    source_releases: set[str] = set()
    soc_titles: dict[str, str] = {}
    skipped_no_soc = 0

    for row in bronze_rows:
        soc_code = _normalize_soc_code(row.get("soc_code"))
        if soc_code is None:
            skipped_no_soc += 1
            continue

        source_releases.add(row.get("source_release") or "")
        title = row.get("soc_title")
        if title and soc_code not in soc_titles:
            soc_titles[soc_code] = title

        task_pct = row.get("task_pct")
        automation_pct = row.get("automation_pct")
        augmentation_pct = row.get("augmentation_pct")

        if _is_broad_soc(soc_code):
            targets = _expand_broad_soc(soc_code, bls_soc_set, bls_prefix_map)
            if len(targets) > 1:
                # Split task_pct equally across detailed descendants so
                # the global sum is preserved post-expansion. Automation
                # ratios are not split — they apply identically to each
                # descendant.
                share = task_pct / len(targets) if task_pct is not None else None
                for tgt in targets:
                    tasks_by_soc.setdefault(tgt, []).append({
                        "task_pct": share,
                        "automation_pct": automation_pct,
                        "augmentation_pct": augmentation_pct,
                    })
                    if title and tgt not in soc_titles:
                        soc_titles[tgt] = title
                continue
            # Single target (either broad code found in BLS as-is or
            # no expansion available) — keep original values
            soc_code = targets[0]

        tasks_by_soc.setdefault(soc_code, []).append({
            "task_pct": task_pct,
            "automation_pct": automation_pct,
            "augmentation_pct": augmentation_pct,
        })

    if skipped_no_soc:
        logger.warning(
            "Skipped %d Bronze tasks with null/invalid SOC code", skipped_no_soc,
        )

    # Pick a canonical source_release (should be one anyway)
    if len(source_releases) == 1:
        canonical_release = next(iter(source_releases))
    else:
        canonical_release = sorted(source_releases)[-1] if source_releases else ""

    silver_rows: list[dict] = []

    for soc_code, tasks in tasks_by_soc.items():
        task_pcts = [t["task_pct"] for t in tasks]
        automation_pcts = [t["automation_pct"] for t in tasks]
        augmentation_pcts = [t["augmentation_pct"] for t in tasks]

        observed_exposure = _aggregate_observed_exposure(task_pcts)
        automation = _weighted_average(automation_pcts, task_pcts)
        augmentation = _weighted_average(augmentation_pcts, task_pcts)

        row = {
            "soc_code": soc_code,
            "soc_title": soc_titles.get(soc_code),
            "observed_exposure_pct": observed_exposure,
            "automation_pct": automation,
            "augmentation_pct": augmentation,
            "task_count": len(tasks),
            "soc_match": soc_code in bls_soc_set,
            "source_release": canonical_release,
            "promoted_at": promoted_at,
        }
        row["record_id"] = compute_grain_id(row, GRAIN_FIELDS, prefix=GRAIN_PREFIX)
        silver_rows.append(row)

    # Stable ordering (aids debugging and deterministic tests)
    silver_rows.sort(key=lambda r: r["soc_code"])

    soc_match_count = sum(1 for r in silver_rows if r["soc_match"])
    logger.info(
        "Transformed %d SOC rows (soc_match=true: %d / %.1f%%)",
        len(silver_rows),
        soc_match_count,
        100 * soc_match_count / len(silver_rows) if silver_rows else 0.0,
    )
    return silver_rows


# ---------------------------------------------------------------------------
# Orchestration wrapper (mirrors the pattern used by peer transformers)
# ---------------------------------------------------------------------------


class AnthropicObservedExposureTransformer:
    """Silver transformer for base.anthropic_observed_exposure.

    Thin OO wrapper so tests and the bs:smelt runner can instantiate
    the transformer alongside its peers. The heavy lifting stays in
    ``transform_rows`` (pure) and ``transform`` (IO wrapper).
    """

    def __init__(self, project_dir: str | Path | None = None) -> None:
        self.project_dir = Path(project_dir or ".").resolve()

    def get_schema(self) -> Schema:
        return get_silver_schema()

    def transform_rows(
        self,
        bronze_rows: list[dict],
        bls_rows: list[dict],
        promoted_at: datetime.datetime | None = None,
    ) -> list[dict]:
        """Public wrapper around the module-level ``transform_rows``."""
        return transform_rows(bronze_rows, bls_rows, promoted_at)

    def transform(self) -> dict[str, Any]:
        """Run the full Silver transform (read Bronze, transform, promote)."""
        return transform(self.project_dir)


def transform(project_dir: str | Path | None = None) -> dict[str, Any]:
    """Read Bronze, transform, promote to base.anthropic_observed_exposure.

    Returns a summary dict compatible with the pattern used by peer
    Silver transformers (karpathy_ai_exposure_transformer.transform).
    """
    project_dir = Path(project_dir or ".").resolve()

    bronze_warehouse = project_dir / "data" / "bronze" / "iceberg_warehouse"
    silver_warehouse = project_dir / "data" / "silver" / "iceberg_warehouse"
    catalog_path = project_dir / "data" / "catalog" / "catalog.db"

    # Read Bronze
    logger.info("Reading from raw.anthropic_economic_index...")
    bronze_catalog = get_catalog(bronze_warehouse, catalog_path)
    bronze_table = bronze_catalog.load_table("raw.anthropic_economic_index")
    bronze_rows = read_with_duckdb(bronze_table)
    logger.info("Read %d rows from Bronze", len(bronze_rows))

    # Read BLS OOH for SOC match + broad expansion
    logger.info("Reading from base.bls_ooh for SOC cross-validation...")
    silver_catalog = get_catalog(silver_warehouse, catalog_path)
    bls_table = silver_catalog.load_table("base.bls_ooh")
    bls_rows = read_with_duckdb(bls_table)
    logger.info("Read %d rows from base.bls_ooh", len(bls_rows))

    # Transform
    promoted_at = datetime.datetime.now(tz=datetime.timezone.utc)
    silver_rows = transform_rows(bronze_rows, bls_rows, promoted_at)

    # Promote
    logger.info("Promoting to base.anthropic_observed_exposure...")
    silver_table = get_or_create_table(
        silver_catalog,
        "base",
        "anthropic_observed_exposure",
        get_silver_schema(),
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
        "soc_match_count": sum(1 for r in silver_rows if r["soc_match"]),
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(message)s",
    )
    summary = transform()
    print(f"Silver transform complete: {summary}")
