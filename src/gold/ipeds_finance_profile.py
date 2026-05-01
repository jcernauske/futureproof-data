"""Gold zone transformer for ``consumable.ipeds_finance_profile``.

Reads ``base.ipeds_finance`` from the Silver/base zone and produces the
institution-level finance profile consumed downstream (notably by
``raw-ingest-eada.md`` for composite ratio fusion). This is a
shaping-only base→consumable promote: no cross-source joins, no new
arithmetic beyond the ``data_completeness_tier`` synthesis.

Per spec ``docs/specs/full-pipeline-ipeds-finance.md`` v1.3 §6:

  - **Base passthrough:** ``unitid``, ``institution_name``,
    ``report_form``, ``fiscal_year``, ``total_fte_enrollment``,
    ``instruction_expenses``, ``institutional_support_expenses``,
    ``endowment_value``, ``institutional_support_per_fte``,
    ``instruction_per_fte``, ``endowment_per_fte``, ``marketing_ratio``.
    The three raw dollar passthroughs (added v1.2) are exposed at
    consumable so downstream specs can compute composite ratios without
    back-joining to base.
  - **data_completeness_tier:** synthesized from the count of non-null
    *independent raw inputs* (not derived signals).  Per the v1.2 patch,
    counts ``instruction_expenses``, ``institutional_support_expenses``,
    ``endowment_value``, and ``total_fte_enrollment`` (positive).
    Counting independent raw inputs (vs. the v1.0 formula which mixed
    in derived ``marketing_ratio``) prevents double-counting expense
    fields and makes ``total_fte_enrollment`` a first-class signal.
  - **Provenance:** ``promoted_at`` timestamp.
  - **Grain / record_id:** ``compute_grain_id(row, ['unitid'],
    prefix='ifp')``.  The ``ifp`` prefix is distinct from base's
    ``ipf`` so record_ids cannot collide across zones.
  - **Promote:** idempotent — re-running with the same base snapshot
    produces 0 new rows.

The 277-ish F3 rows have ``endowment_value = NULL`` 100% of the time
(genuine N/A for for-profits), which means F3 rows with the other 3
raw inputs present land at tier ``medium``, not ``high``.  This is the
intended behavior per the v1.2 reviewer rework — counting derived
signals would have misleadingly classified these rows as ``high``.
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import Any

from pyiceberg.schema import Schema
from pyiceberg.types import (
    DoubleType,
    IntegerType,
    LongType,
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

GRAIN_FIELDS: list[str] = ["unitid"]
GRAIN_PREFIX = "ifp"
SPEC_NAME = "consumable-ipeds-finance-profile"
BASE_TABLE_FQN = "base.ipeds_finance"
CONSUMABLE_NAMESPACE = "consumable"
CONSUMABLE_TABLE_NAME = "ipeds_finance_profile"

# Base columns carried forward verbatim to consumable.
BASE_PASSTHROUGH_FIELDS: tuple[str, ...] = (
    "unitid",
    "institution_name",
    "report_form",
    "fiscal_year",
    "total_fte_enrollment",
    "instruction_expenses",
    "institutional_support_expenses",
    "endowment_value",
    "institutional_support_per_fte",
    "instruction_per_fte",
    "endowment_per_fte",
    "marketing_ratio",
)

# Independent raw inputs counted by the data_completeness_tier formula.
# Per spec §6.2 (v1.2): four independent raw inputs, not derived signals.
TIER_RAW_INPUTS: tuple[str, ...] = (
    "instruction_expenses",
    "institutional_support_expenses",
    "endowment_value",
    "total_fte_enrollment",
)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def get_consumable_schema() -> Schema:
    """Iceberg schema for ``consumable.ipeds_finance_profile`` (15 columns).

    Field IDs are dense and stable.  Column order matches the spec §6
    Consumable Schema table.  Required-vs-nullable mirrors the spec:

      - ``record_id``, identity passthroughs, ``data_completeness_tier``,
        and ``promoted_at`` are required.
      - The four raw / FTE passthroughs and four derived per-FTE / ratio
        passthroughs are nullable (the F3-endowment and zero-FTE
        realities make any required-not-null rule false on real data).
    """
    return Schema(
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "unitid", LongType(), required=True),
        NestedField(3, "institution_name", StringType(), required=True),
        NestedField(4, "report_form", StringType(), required=True),
        NestedField(5, "fiscal_year", IntegerType(), required=True),
        NestedField(6, "total_fte_enrollment", DoubleType(), required=False),
        NestedField(7, "instruction_expenses", DoubleType(), required=False),
        NestedField(
            8, "institutional_support_expenses", DoubleType(), required=False
        ),
        NestedField(9, "endowment_value", DoubleType(), required=False),
        NestedField(
            10, "institutional_support_per_fte", DoubleType(), required=False
        ),
        NestedField(11, "instruction_per_fte", DoubleType(), required=False),
        NestedField(12, "endowment_per_fte", DoubleType(), required=False),
        NestedField(13, "marketing_ratio", DoubleType(), required=False),
        NestedField(14, "data_completeness_tier", StringType(), required=True),
        NestedField(15, "promoted_at", TimestampType(), required=True),
    )


# ---------------------------------------------------------------------------
# Derivation helpers
# ---------------------------------------------------------------------------


def classify_data_completeness_tier(row: dict) -> str:
    """Classify a base row's data_completeness_tier (v1.2 formula).

    Counts the number of non-null *independent raw inputs* per spec §6.2:

      - ``instruction_expenses``
      - ``institutional_support_expenses``
      - ``endowment_value``
      - ``total_fte_enrollment`` (must be present AND > 0 — a zero or
        negative FTE makes all three per-FTE values NULL and the row
        unusable for per-student comparison)

    Tier mapping:

      - 4/4 → ``high``
      - 2-3/4 → ``medium``
      - 1/4 → ``low``
      - 0/4 → ``insufficient``

    F3 (private for-profit) rows have ``endowment_value = NULL`` 100% of
    the time, so an F3 row with the other 3 inputs present lands at
    ``medium`` (3/4), not ``high``.  This is by design — the v1.2 patch
    reworked this from the v1.0 derived-fields count specifically to
    prevent misleading-``high`` classification of F3 rows.
    """
    non_null_signals = 0
    for field in TIER_RAW_INPUTS:
        value = row.get(field)
        if value is None:
            continue
        if field == "total_fte_enrollment" and not (value > 0):
            # FTE = 0 or negative makes per-FTE values NULL — not a usable signal.
            continue
        non_null_signals += 1

    if non_null_signals == 4:
        return "high"
    if non_null_signals >= 2:
        return "medium"
    if non_null_signals == 1:
        return "low"
    return "insufficient"


# ---------------------------------------------------------------------------
# Row transform
# ---------------------------------------------------------------------------


def transform_row(
    base_row: dict,
    promoted_at: datetime.datetime,
) -> dict:
    """Transform one base row into a consumable ``ipeds_finance_profile`` row.

    Pure shaping: passes the 12 base fields through verbatim, synthesizes
    ``data_completeness_tier``, and stamps ``record_id`` + ``promoted_at``.
    No cross-source joins.  No new arithmetic on the per-FTE / ratio
    fields — those remain whatever the base transformer computed (CON-IFP-007
    arithmetic invariant is upstream of this transformer).
    """
    record: dict[str, Any] = {field: base_row.get(field) for field in BASE_PASSTHROUGH_FIELDS}
    record["data_completeness_tier"] = classify_data_completeness_tier(base_row)
    record["promoted_at"] = promoted_at
    record["record_id"] = compute_grain_id(record, GRAIN_FIELDS, prefix=GRAIN_PREFIX)
    return record


def transform_rows(
    base_rows: list[dict],
    promoted_at: datetime.datetime | None = None,
) -> list[dict]:
    """Transform every base row into a consumable row.

    Enforces UNITID uniqueness up front so a duplicate-grain base
    snapshot fails loud here rather than silently dedup-skipping at
    promote time (CON-IFP-003 uniqueness invariant).
    """
    if promoted_at is None:
        promoted_at = datetime.datetime.now(tz=datetime.timezone.utc)

    consumable_rows = [transform_row(row, promoted_at) for row in base_rows]

    seen: set[int] = set()
    for row in consumable_rows:
        if row["unitid"] in seen:
            raise ValueError(f"Duplicate unitid in consumable rows: {row['unitid']}")
        seen.add(row["unitid"])

    return consumable_rows


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------


def transform(
    project_dir: str | Path | None = None,
    base_warehouse: str | Path | None = None,
    consumable_warehouse: str | Path | None = None,
    catalog_path: str | Path | None = None,
    promoted_at: datetime.datetime | None = None,
) -> dict:
    """Run the gold transformation for ``consumable.ipeds_finance_profile``.

    Reads ``base.ipeds_finance`` from the silver/base zone, applies the
    consumable shape (pass through 12 base fields + synthesize
    ``data_completeness_tier``), and promotes to
    ``consumable.ipeds_finance_profile`` via the idempotent promote
    pattern.  Re-running with the same base snapshot produces 0 new rows.

    Args:
        project_dir: Project root.  Defaults to the current working
            directory.  Only used when warehouse / catalog paths are
            left as None.
        base_warehouse: Override for the silver/base Iceberg warehouse
            path.
        consumable_warehouse: Override for the gold/consumable Iceberg
            warehouse path.
        catalog_path: Override for the shared SQLite catalog DB path.
        promoted_at: Override for the promotion timestamp (tests pass a
            fixed value for determinism).

    Returns:
        Dict with run metrics: ``rows_read``, ``rows_transformed``,
        ``promoted``, ``skipped_dedup``, ``snapshot_id``,
        ``tier_counts``.
    """
    project_dir = Path(project_dir or ".").resolve()

    base_warehouse = Path(
        base_warehouse or project_dir / "data" / "silver" / "iceberg_warehouse"
    )
    consumable_warehouse = Path(
        consumable_warehouse or project_dir / "data" / "gold" / "iceberg_warehouse"
    )
    catalog_path = Path(
        catalog_path or project_dir / "data" / "catalog" / "catalog.db"
    )

    # Read base.
    logger.info("Reading from %s...", BASE_TABLE_FQN)
    base_catalog = get_catalog(base_warehouse, catalog_path)
    base_table = base_catalog.load_table(BASE_TABLE_FQN)
    base_rows = read_with_duckdb(base_table)
    logger.info("Read %d rows from %s", len(base_rows), BASE_TABLE_FQN)

    # Transform.
    logger.info("Transforming to %s.%s...", CONSUMABLE_NAMESPACE, CONSUMABLE_TABLE_NAME)
    consumable_rows = transform_rows(base_rows, promoted_at=promoted_at)
    logger.info("Transformed %d rows", len(consumable_rows))

    # Tier-distribution log (for the CON-IFP-005/006/009 invariants).
    tier_counts: dict[str, int] = {}
    for row in consumable_rows:
        tier_counts[row["data_completeness_tier"]] = (
            tier_counts.get(row["data_completeness_tier"], 0) + 1
        )
    logger.info("data_completeness_tier distribution: %s", sorted(tier_counts.items()))

    # Promote.
    logger.info("Promoting to %s.%s...", CONSUMABLE_NAMESPACE, CONSUMABLE_TABLE_NAME)
    consumable_catalog = get_catalog(consumable_warehouse, catalog_path)
    consumable_table = get_or_create_table(
        consumable_catalog,
        CONSUMABLE_NAMESPACE,
        CONSUMABLE_TABLE_NAME,
        get_consumable_schema(),
    )
    result = promote(
        consumable_table,
        consumable_rows,
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
        "rows_read": len(base_rows),
        "rows_transformed": len(consumable_rows),
        "promoted": result["promoted"],
        "skipped_dedup": result["skipped"],
        "snapshot_id": result.get("snapshot_id"),
        "tier_counts": tier_counts,
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
    )
    result = transform()
    print(f"Gold transform complete: {result}")
