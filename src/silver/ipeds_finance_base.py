"""Silver/base zone transformer for the IPEDS Finance institution profile.

Reads ``bronze.ipeds_finance`` (~2,683 rows for FY2022 — F1A public GASB,
F2 private nonprofit FASB, F3 private for-profit) and produces
``base.ipeds_finance`` with the four raw dollar fields passed through,
three per-FTE derivations, the cross-field marketing ratio, and standard
provenance columns.

Per spec ``docs/specs/full-pipeline-ipeds-finance.md`` v1.3 §5:

  - **Passthrough:** ``unitid``, ``institution_name``, ``report_form``,
    ``fiscal_year``, ``institutional_support_expenses``,
    ``instruction_expenses``, ``endowment_value``,
    ``total_fte_enrollment``.
  - **Per-FTE derivations:** plain double arithmetic.  NULL when either
    operand is NULL or ``total_fte_enrollment <= 0``.  No imputation.
  - **Marketing ratio:** ``institutional_support_expenses /
    NULLIF(instruction_expenses, 0)``.  NULL when either operand is NULL
    or instruction is 0.
  - **Provenance:** ``source_load_date`` (raw ``load_date`` passthrough),
    ``ingested_at`` (base promotion timestamp).
  - **Grain / record_id:** ``compute_grain_id(row, ['unitid'],
    prefix='ipf')``.
  - **Promote:** idempotent — re-running with the same bronze snapshot
    produces 0 new rows.

Per-form differentiation (F1A vs. F2 vs. F3) is a bronze-zone concern;
``report_form`` is just a passthrough column here.  The 287-ish F3 rows
have ``endowment_value = NULL`` 100% of the time (genuine N/A for
for-profits), which propagates to a NULL ``endowment_per_fte`` for those
rows by design (per BSE-IPF-013, the ≥55% endowment-per-fte non-null
budget is met by F1A + F2 alone).  The handful of zero-instruction rows
(system administrative offices) produce NULL ``marketing_ratio`` per the
NULLIF semantics — that is the correct behavior, not a bug.
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import Any

from pyiceberg.schema import Schema
from pyiceberg.types import (
    DateType,
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
GRAIN_PREFIX = "ipf"
SPEC_NAME = "base-ipeds-finance"
BRONZE_TABLE_FQN = "bronze.ipeds_finance"
BASE_NAMESPACE = "base"
BASE_TABLE_NAME = "ipeds_finance"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def get_base_schema() -> Schema:
    """Iceberg schema for ``base.ipeds_finance`` (15 columns).

    Field IDs are dense and stable.  Required-vs-nullable mirrors the
    spec §5 base schema table:

      - ``record_id``, identity passthroughs, and provenance are required.
      - The four raw dollar / FTE passthroughs and four derivations are
        nullable (the F3-endowment and zero-FTE realities make any
        required-not-null rule false on real data).
    """
    return Schema(
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "unitid", LongType(), required=True),
        NestedField(3, "institution_name", StringType(), required=True),
        NestedField(4, "report_form", StringType(), required=True),
        NestedField(5, "fiscal_year", IntegerType(), required=True),
        NestedField(6, "institutional_support_expenses", DoubleType(), required=False),
        NestedField(7, "instruction_expenses", DoubleType(), required=False),
        NestedField(8, "endowment_value", DoubleType(), required=False),
        NestedField(9, "total_fte_enrollment", DoubleType(), required=False),
        NestedField(10, "institutional_support_per_fte", DoubleType(), required=False),
        NestedField(11, "instruction_per_fte", DoubleType(), required=False),
        NestedField(12, "endowment_per_fte", DoubleType(), required=False),
        NestedField(13, "marketing_ratio", DoubleType(), required=False),
        NestedField(14, "source_load_date", DateType(), required=True),
        NestedField(15, "ingested_at", TimestampType(), required=True),
    )


# ---------------------------------------------------------------------------
# Derivation helpers
# ---------------------------------------------------------------------------


def _to_optional_float(value: Any) -> float | None:
    """Coerce a bronze numeric value to ``float`` or ``None``.

    Bronze landed sentinel-cleaned values — ``None`` for missing,
    ``float`` for present — but defensively reject NaN here so downstream
    arithmetic invariants hold.
    """
    if value is None:
        return None
    f = float(value)
    if f != f:  # NaN check
        return None
    return f


def derive_per_fte(numerator: float | None, fte: float | None) -> float | None:
    """Compute a per-FTE value or return None.

    Returns ``None`` when ``numerator`` is None, ``fte`` is None, or
    ``fte <= 0``.  The arithmetic invariants in BSE-IPF-008/009 require
    that ``derive_per_fte(num, fte) * fte ≈ num`` within $1 when all
    three are non-null — this is satisfied by plain double division.
    Do not switch to Decimal: the spec requires plain double arithmetic.
    """
    if numerator is None or fte is None or fte <= 0:
        return None
    return numerator / fte


def derive_marketing_ratio(
    institutional_support: float | None,
    instruction: float | None,
) -> float | None:
    """Compute ``institutional_support / instruction`` or return None.

    Mirrors SQL ``NULLIF(instruction, 0)``: returns ``None`` when either
    operand is None or when instruction is 0.  The 34 system-admin-office
    F1A rows with zero instruction expense produce ``None`` here by
    design — that is the correct outcome per spec §5 footnote.
    """
    if institutional_support is None or instruction is None or instruction == 0:
        return None
    return institutional_support / instruction


# ---------------------------------------------------------------------------
# Row transform
# ---------------------------------------------------------------------------


def transform_row(
    raw: dict,
    ingested_at: datetime.datetime | None = None,
) -> dict:
    """Transform one bronze row into a base ``ipeds_finance`` row.

    Args:
        raw: A row dict read from ``bronze.ipeds_finance``.  Required
            keys: ``unitid``, ``institution_name``, ``report_form``,
            ``fiscal_year``, ``load_date``.  Numeric measures may be
            None.
        ingested_at: Override for the base promotion timestamp.  Defaults
            to ``datetime.datetime.now(tz=datetime.timezone.utc)``.

    Returns:
        A dict containing the 15 columns of the base schema.  ``record_id``
        is a deterministic ``ipf-<16hex>`` hash of ``unitid``.
    """
    if ingested_at is None:
        ingested_at = datetime.datetime.now(tz=datetime.timezone.utc)

    unitid_raw = raw.get("unitid")
    if unitid_raw is None:
        raise ValueError("bronze row missing required 'unitid'")
    unitid = int(unitid_raw)

    institution_name = raw.get("institution_name")
    if institution_name is None:
        raise ValueError(f"bronze row missing 'institution_name' (unitid={unitid})")
    institution_name = str(institution_name)

    report_form = raw.get("report_form")
    if report_form is None:
        raise ValueError(f"bronze row missing 'report_form' (unitid={unitid})")
    report_form = str(report_form)

    fiscal_year_raw = raw.get("fiscal_year")
    if fiscal_year_raw is None:
        raise ValueError(f"bronze row missing 'fiscal_year' (unitid={unitid})")
    fiscal_year = int(fiscal_year_raw)

    source_load_date = raw.get("load_date")
    if source_load_date is None:
        raise ValueError(f"bronze row missing 'load_date' (unitid={unitid})")

    institutional_support = _to_optional_float(raw.get("institutional_support_expenses"))
    instruction = _to_optional_float(raw.get("instruction_expenses"))
    endowment = _to_optional_float(raw.get("endowment_value"))
    total_fte = _to_optional_float(raw.get("total_fte_enrollment"))

    institutional_support_per_fte = derive_per_fte(institutional_support, total_fte)
    instruction_per_fte = derive_per_fte(instruction, total_fte)
    endowment_per_fte = derive_per_fte(endowment, total_fte)
    marketing_ratio = derive_marketing_ratio(institutional_support, instruction)

    record: dict[str, Any] = {
        "unitid": unitid,
        "institution_name": institution_name,
        "report_form": report_form,
        "fiscal_year": fiscal_year,
        "institutional_support_expenses": institutional_support,
        "instruction_expenses": instruction,
        "endowment_value": endowment,
        "total_fte_enrollment": total_fte,
        "institutional_support_per_fte": institutional_support_per_fte,
        "instruction_per_fte": instruction_per_fte,
        "endowment_per_fte": endowment_per_fte,
        "marketing_ratio": marketing_ratio,
        "source_load_date": source_load_date,
        "ingested_at": ingested_at,
    }
    record["record_id"] = compute_grain_id(record, GRAIN_FIELDS, prefix=GRAIN_PREFIX)
    return record


def transform_rows(
    bronze_rows: list[dict],
    ingested_at: datetime.datetime | None = None,
) -> list[dict]:
    """Transform every bronze row into a base row.

    Enforces UNITID uniqueness up front so a duplicate-grain bronze
    snapshot fails loud here rather than silently dedup-skipping at
    promote time.
    """
    if ingested_at is None:
        ingested_at = datetime.datetime.now(tz=datetime.timezone.utc)

    base_rows = [transform_row(row, ingested_at=ingested_at) for row in bronze_rows]

    seen: set[int] = set()
    for row in base_rows:
        if row["unitid"] in seen:
            raise ValueError(f"Duplicate unitid in base rows: {row['unitid']}")
        seen.add(row["unitid"])

    return base_rows


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------


def promote_ipeds_finance_base(
    project_dir: str | Path | None = None,
    bronze_warehouse: str | Path | None = None,
    base_warehouse: str | Path | None = None,
    catalog_path: str | Path | None = None,
    ingested_at: datetime.datetime | None = None,
) -> dict:
    """Run the silver/base transformation for ``base.ipeds_finance``.

    Reads ``bronze.ipeds_finance`` from the bronze zone, transforms the
    rows, and promotes to ``base.ipeds_finance`` via the idempotent
    promote pattern.  Re-running with the same bronze snapshot produces
    0 new rows.

    Args:
        project_dir: Project root.  Defaults to the current working
            directory.  Only used when warehouse / catalog paths are
            left as None.
        bronze_warehouse: Override for the bronze Iceberg warehouse path.
        base_warehouse: Override for the silver/base Iceberg warehouse
            path.
        catalog_path: Override for the shared SQLite catalog DB path.
        ingested_at: Override for the promotion timestamp (tests pass a
            fixed value for determinism).

    Returns:
        Dict with run metrics: ``rows_read``, ``rows_transformed``,
        ``promoted``, ``skipped_dedup``, ``snapshot_id``,
        ``form_counts``.
    """
    project_dir = Path(project_dir or ".").resolve()

    bronze_warehouse = Path(
        bronze_warehouse or project_dir / "data" / "bronze" / "iceberg_warehouse"
    )
    base_warehouse = Path(
        base_warehouse or project_dir / "data" / "silver" / "iceberg_warehouse"
    )
    catalog_path = Path(
        catalog_path or project_dir / "data" / "catalog" / "catalog.db"
    )

    # Read bronze (only ~2,683 rows — read in one shot, no chunking).
    logger.info("Reading from %s...", BRONZE_TABLE_FQN)
    bronze_catalog = get_catalog(bronze_warehouse, catalog_path)
    bronze_table = bronze_catalog.load_table(BRONZE_TABLE_FQN)
    bronze_rows = read_with_duckdb(bronze_table)
    logger.info("Read %d rows from %s", len(bronze_rows), BRONZE_TABLE_FQN)

    # Transform.
    logger.info("Transforming to base.ipeds_finance...")
    base_rows = transform_rows(bronze_rows, ingested_at=ingested_at)
    logger.info("Transformed %d rows", len(base_rows))

    # Form-mix log for parity with bronze (BSE-IPF-001 conservation
    # invariant downstream-DQ will enforce row count == bronze).
    form_counts: dict[str, int] = {}
    for row in base_rows:
        form_counts[row["report_form"]] = form_counts.get(row["report_form"], 0) + 1
    logger.info("Form-mix: %s", sorted(form_counts.items()))

    # Promote.
    logger.info("Promoting to %s.%s...", BASE_NAMESPACE, BASE_TABLE_NAME)
    base_catalog = get_catalog(base_warehouse, catalog_path)
    base_table = get_or_create_table(
        base_catalog, BASE_NAMESPACE, BASE_TABLE_NAME, get_base_schema()
    )
    result = promote(
        base_table,
        base_rows,
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
        "rows_transformed": len(base_rows),
        "promoted": result["promoted"],
        "skipped_dedup": result["skipped"],
        "snapshot_id": result.get("snapshot_id"),
        "form_counts": form_counts,
    }


def transform(project_dir: str | Path | None = None) -> dict:
    """Manifest-style entry point — thin wrapper around ``promote_ipeds_finance_base``."""
    return promote_ipeds_finance_base(project_dir=project_dir)
