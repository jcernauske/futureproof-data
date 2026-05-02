"""Silver/base zone transformer for the EADA institution-athletics profile.

Reads ``bronze.eada`` (~2,040 rows, one row per institution per
reporting year) and produces ``base.eada`` with the four raw EADA
measures passed through, the §5 Option-C COALESCE'd FTE source, three
per-FTE derivations, the athletic subsidy ratio, and standard
provenance columns.

Per spec ``docs/specs/full-pipeline-eada.md`` v1.x §5 (Option-C
amendment, 2026-04-30):

  - **Passthrough from raw:** ``unitid``, ``institution_name``,
    ``reporting_year``, ``total_athletic_expenses``,
    ``total_athletic_revenue``, ``recruiting_expenses``,
    ``eada_fte_headcount``.
  - **Hybrid FTE source (Option C):** LEFT JOIN ``base.ipeds_finance``
    on UNITID to fetch ``total_fte_enrollment`` (annualized FTE),
    COALESCE with ``bronze.eada.eada_fte_headcount`` (12-month
    headcount fallback), stamp ``fte_source`` provenance.  No
    imputation.
  - **Per-FTE derivations:** plain double arithmetic.  NULL when
    either operand is NULL or ``total_fte_enrollment <= 0``.  Each
    derivation inherits the ``fte_source`` of its denominator.
  - **Athletic subsidy ratio:** ``(expenses - revenue) /
    NULLIF(expenses, 0)``.  Independent of FTE source.
  - **Provenance:** ``source_load_date`` (raw ``load_date``
    passthrough), ``ingested_at`` (base promotion timestamp), plus the
    ``fte_source`` / ``has_ipeds_finance_fte`` / ``has_eada_fte``
    columns.
  - **Grain / record_id:** ``compute_grain_id(row, ['unitid'],
    prefix='ead')``.
  - **Promote:** idempotent — re-running with the same bronze and
    base.ipeds_finance snapshots produces 0 new rows.

The two FTE definitions are NOT identical — ``total_fte_enrollment`` is
annualized, ``EFTotalCount`` is 12-month headcount — so the
``fte_source`` column makes the methodological mix explicit for
downstream consumers who want to filter or stratify.
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import Any

from pyiceberg.schema import Schema
from pyiceberg.types import (
    BooleanType,
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
GRAIN_PREFIX = "ead"
SPEC_NAME = "base-eada"
BRONZE_TABLE_FQN = "bronze.eada"
IPEDS_FINANCE_TABLE_FQN = "base.ipeds_finance"
BASE_NAMESPACE = "base"
BASE_TABLE_NAME = "eada"

FTE_SOURCE_IPEDS = "ipeds_finance"
FTE_SOURCE_EADA = "eada_fte_headcount"
FTE_SOURCE_NONE = "none"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def get_base_schema() -> Schema:
    """Iceberg schema for ``base.eada`` (19 columns).

    Field IDs are dense and stable.  Required-vs-nullable mirrors the
    spec §5 base schema table:

      - ``record_id``, identity passthroughs, FTE provenance flags, and
        provenance timestamps are required.
      - The four raw EADA dollar / FTE passthroughs, the COALESCE'd
        ``total_fte_enrollment``, and the four derivations are
        nullable (per the §5 Option-C residual-NULL allowance and
        per-FTE arithmetic NULL semantics).
    """
    return Schema(
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "unitid", LongType(), required=True),
        NestedField(3, "institution_name", StringType(), required=True),
        NestedField(4, "reporting_year", IntegerType(), required=True),
        NestedField(5, "total_athletic_expenses", DoubleType(), required=False),
        NestedField(6, "total_athletic_revenue", DoubleType(), required=False),
        NestedField(7, "recruiting_expenses", DoubleType(), required=False),
        NestedField(8, "eada_fte_headcount", DoubleType(), required=False),
        NestedField(9, "total_fte_enrollment", DoubleType(), required=False),
        NestedField(10, "fte_source", StringType(), required=True),
        NestedField(11, "has_ipeds_finance_fte", BooleanType(), required=True),
        NestedField(12, "has_eada_fte", BooleanType(), required=True),
        NestedField(13, "athletic_spend_per_fte", DoubleType(), required=False),
        NestedField(14, "athletic_revenue_per_fte", DoubleType(), required=False),
        NestedField(15, "recruiting_per_fte", DoubleType(), required=False),
        NestedField(16, "athletic_subsidy_ratio", DoubleType(), required=False),
        NestedField(17, "source_load_date", DateType(), required=True),
        NestedField(18, "ingested_at", TimestampType(), required=True),
    )


# ---------------------------------------------------------------------------
# Derivation helpers
# ---------------------------------------------------------------------------


def _to_optional_float(value: Any) -> float | None:
    """Coerce a bronze numeric value to ``float`` or ``None``.

    Bronze landed sentinel-cleaned values — ``None`` for missing,
    ``float`` for present — but defensively reject NaN here so
    downstream arithmetic invariants hold.
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
    ``fte <= 0``.  The arithmetic invariants in BSE-EAD-008 require
    that ``derive_per_fte(num, fte) * fte ≈ num`` within $1 when all
    three are non-null — this is satisfied by plain double division.
    Do not switch to Decimal: the spec requires plain double
    arithmetic.
    """
    if numerator is None or fte is None or fte <= 0:
        return None
    return numerator / fte


def derive_subsidy_ratio(
    expenses: float | None,
    revenue: float | None,
) -> float | None:
    """Compute ``(expenses - revenue) / NULLIF(expenses, 0)`` or None.

    Mirrors SQL ``NULLIF(total_athletic_expenses, 0)``: returns
    ``None`` when either operand is None or when expenses is 0.
    Positive = subsidized (revenue < expenses).  Near 0 =
    self-sustaining.  Negative = profitable (revenue > expenses).
    Independent of FTE source.
    """
    if expenses is None or revenue is None or expenses == 0:
        return None
    return (expenses - revenue) / expenses


def resolve_fte(
    ipeds_finance_fte: float | None,
    eada_fte_headcount: float | None,
) -> tuple[float | None, str]:
    """Apply the §5 Option-C COALESCE hybrid for the FTE source.

    Prefers ``base.ipeds_finance.total_fte_enrollment`` when non-null
    (preferred annualized FTE); falls back to
    ``bronze.eada.eada_fte_headcount`` (12-month headcount) when the
    IPEDS Finance value is missing.  Stamps the explicit provenance
    string for the chosen source.

    Returns:
        ``(total_fte_enrollment, fte_source)``.  When both inputs are
        None, returns ``(None, 'none')`` — the residual-NULL case
        bounded by BSE-EAD-009 (≤ 1%).
    """
    if ipeds_finance_fte is not None:
        return ipeds_finance_fte, FTE_SOURCE_IPEDS
    if eada_fte_headcount is not None:
        return eada_fte_headcount, FTE_SOURCE_EADA
    return None, FTE_SOURCE_NONE


# ---------------------------------------------------------------------------
# Row transform
# ---------------------------------------------------------------------------


def transform_row(
    raw: dict,
    ipeds_finance_fte: float | None,
    ingested_at: datetime.datetime | None = None,
) -> dict:
    """Transform one bronze row into a base ``eada`` row.

    Args:
        raw: A row dict read from ``bronze.eada``.  Required keys:
            ``unitid``, ``institution_name``, ``reporting_year``,
            ``load_date``.  Numeric measures may be None.
        ipeds_finance_fte: The ``total_fte_enrollment`` value from
            ``base.ipeds_finance`` for this UNITID, or ``None`` when
            the LEFT JOIN had no match or the IPEDS row had a NULL
            value.  Drives the §5 Option-C COALESCE.
        ingested_at: Override for the base promotion timestamp.
            Defaults to ``datetime.datetime.now(tz=datetime.timezone.utc)``.

    Returns:
        A dict containing the 18 columns of the base schema.  The 19th
        ``record_id`` is a deterministic ``ead-<16hex>`` hash of
        ``unitid``.
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

    reporting_year_raw = raw.get("reporting_year")
    if reporting_year_raw is None:
        raise ValueError(f"bronze row missing 'reporting_year' (unitid={unitid})")
    reporting_year = int(reporting_year_raw)

    source_load_date = raw.get("load_date")
    if source_load_date is None:
        raise ValueError(f"bronze row missing 'load_date' (unitid={unitid})")

    total_athletic_expenses = _to_optional_float(raw.get("total_athletic_expenses"))
    total_athletic_revenue = _to_optional_float(raw.get("total_athletic_revenue"))
    recruiting_expenses = _to_optional_float(raw.get("recruiting_expenses"))
    eada_fte_headcount = _to_optional_float(raw.get("eada_fte_headcount"))
    ipeds_fte_clean = _to_optional_float(ipeds_finance_fte)

    total_fte_enrollment, fte_source = resolve_fte(ipeds_fte_clean, eada_fte_headcount)
    has_ipeds_finance_fte = ipeds_fte_clean is not None
    has_eada_fte = eada_fte_headcount is not None

    athletic_spend_per_fte = derive_per_fte(total_athletic_expenses, total_fte_enrollment)
    athletic_revenue_per_fte = derive_per_fte(total_athletic_revenue, total_fte_enrollment)
    recruiting_per_fte = derive_per_fte(recruiting_expenses, total_fte_enrollment)
    athletic_subsidy_ratio = derive_subsidy_ratio(
        total_athletic_expenses, total_athletic_revenue
    )

    record: dict[str, Any] = {
        "unitid": unitid,
        "institution_name": institution_name,
        "reporting_year": reporting_year,
        "total_athletic_expenses": total_athletic_expenses,
        "total_athletic_revenue": total_athletic_revenue,
        "recruiting_expenses": recruiting_expenses,
        "eada_fte_headcount": eada_fte_headcount,
        "total_fte_enrollment": total_fte_enrollment,
        "fte_source": fte_source,
        "has_ipeds_finance_fte": has_ipeds_finance_fte,
        "has_eada_fte": has_eada_fte,
        "athletic_spend_per_fte": athletic_spend_per_fte,
        "athletic_revenue_per_fte": athletic_revenue_per_fte,
        "recruiting_per_fte": recruiting_per_fte,
        "athletic_subsidy_ratio": athletic_subsidy_ratio,
        "source_load_date": source_load_date,
        "ingested_at": ingested_at,
    }
    record["record_id"] = compute_grain_id(record, GRAIN_FIELDS, prefix=GRAIN_PREFIX)
    return record


def transform_rows(
    bronze_rows: list[dict],
    ipeds_fte_by_unitid: dict[int, float | None],
    ingested_at: datetime.datetime | None = None,
) -> list[dict]:
    """Transform every bronze row into a base row.

    Performs the LEFT JOIN against ``base.ipeds_finance`` via the
    ``ipeds_fte_by_unitid`` lookup (UNITID → total_fte_enrollment).
    UNITIDs present in EADA but absent from IPEDS Finance fall through
    to ``eada_fte_headcount`` per §5 Option-C.

    Enforces UNITID uniqueness up front so a duplicate-grain bronze
    snapshot fails loud here rather than silently dedup-skipping at
    promote time.
    """
    if ingested_at is None:
        ingested_at = datetime.datetime.now(tz=datetime.timezone.utc)

    base_rows = [
        transform_row(
            row,
            ipeds_finance_fte=ipeds_fte_by_unitid.get(int(row["unitid"])),
            ingested_at=ingested_at,
        )
        for row in bronze_rows
    ]

    seen: set[int] = set()
    for row in base_rows:
        if row["unitid"] in seen:
            raise ValueError(f"Duplicate unitid in base rows: {row['unitid']}")
        seen.add(row["unitid"])

    return base_rows


def build_ipeds_fte_lookup(ipeds_rows: list[dict]) -> dict[int, float | None]:
    """Build the UNITID → total_fte_enrollment lookup for the LEFT JOIN.

    Reads ``base.ipeds_finance`` rows and returns a dict keyed by
    integer UNITID.  Rows where IPEDS-Finance has a NULL FTE produce a
    ``None`` value in the lookup, which then falls through to the
    EADA fallback during ``resolve_fte``.

    Duplicate UNITIDs in the IPEDS Finance feed should not happen (its
    grain is UNITID), but if they do this raises rather than silently
    last-write-wins.
    """
    lookup: dict[int, float | None] = {}
    for row in ipeds_rows:
        unitid_raw = row.get("unitid")
        if unitid_raw is None:
            continue
        unitid = int(unitid_raw)
        if unitid in lookup:
            raise ValueError(
                f"Duplicate unitid in base.ipeds_finance lookup: {unitid}"
            )
        lookup[unitid] = _to_optional_float(row.get("total_fte_enrollment"))
    return lookup


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------


def promote_eada_base(
    project_dir: str | Path | None = None,
    bronze_warehouse: str | Path | None = None,
    base_warehouse: str | Path | None = None,
    catalog_path: str | Path | None = None,
    ingested_at: datetime.datetime | None = None,
) -> dict:
    """Run the silver/base transformation for ``base.eada``.

    Reads ``bronze.eada`` from the bronze zone, LEFT JOINs
    ``base.ipeds_finance`` on UNITID to fetch the preferred FTE
    source, applies §5 Option-C COALESCE / provenance stamping,
    transforms the rows, and promotes to ``base.eada`` via the
    idempotent promote pattern.  Re-running with the same source
    snapshots produces 0 new rows.

    Args:
        project_dir: Project root.  Defaults to the current working
            directory.  Only used when warehouse / catalog paths are
            left as None.
        bronze_warehouse: Override for the bronze Iceberg warehouse
            path.
        base_warehouse: Override for the silver/base Iceberg warehouse
            path (also where ``base.ipeds_finance`` is read from —
            both share the same SQLite catalog).
        catalog_path: Override for the shared SQLite catalog DB path.
        ingested_at: Override for the promotion timestamp (tests pass
            a fixed value for determinism).

    Returns:
        Dict with run metrics: ``rows_read``, ``ipeds_lookup_rows``,
        ``rows_transformed``, ``promoted``, ``skipped_dedup``,
        ``snapshot_id``, ``fte_source_counts``.
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

    # Read bronze.eada (~2,040 rows — read in one shot, no chunking).
    logger.info("Reading from %s...", BRONZE_TABLE_FQN)
    bronze_catalog = get_catalog(bronze_warehouse, catalog_path)
    bronze_table = bronze_catalog.load_table(BRONZE_TABLE_FQN)
    bronze_rows = read_with_duckdb(bronze_table)
    logger.info("Read %d rows from %s", len(bronze_rows), BRONZE_TABLE_FQN)

    # Read base.ipeds_finance (~2,683 rows) for the LEFT-JOIN lookup.
    logger.info("Reading from %s for FTE LEFT JOIN...", IPEDS_FINANCE_TABLE_FQN)
    base_catalog = get_catalog(base_warehouse, catalog_path)
    ipeds_table = base_catalog.load_table(IPEDS_FINANCE_TABLE_FQN)
    ipeds_rows = read_with_duckdb(ipeds_table)
    ipeds_fte_by_unitid = build_ipeds_fte_lookup(ipeds_rows)
    logger.info(
        "Built IPEDS-Finance FTE lookup: %d UNITIDs (%d with non-null FTE)",
        len(ipeds_fte_by_unitid),
        sum(1 for v in ipeds_fte_by_unitid.values() if v is not None),
    )

    # Transform — Option-C COALESCE applied per row.
    logger.info("Transforming to base.eada...")
    base_rows = transform_rows(
        bronze_rows,
        ipeds_fte_by_unitid=ipeds_fte_by_unitid,
        ingested_at=ingested_at,
    )
    logger.info("Transformed %d rows", len(base_rows))

    # FTE-source mix log for parity with EDA expectations.
    fte_source_counts: dict[str, int] = {}
    for row in base_rows:
        fte_source_counts[row["fte_source"]] = (
            fte_source_counts.get(row["fte_source"], 0) + 1
        )
    logger.info("FTE-source mix: %s", sorted(fte_source_counts.items()))

    # Promote.
    logger.info("Promoting to %s.%s...", BASE_NAMESPACE, BASE_TABLE_NAME)
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
        "ipeds_lookup_rows": len(ipeds_fte_by_unitid),
        "rows_transformed": len(base_rows),
        "promoted": result["promoted"],
        "skipped_dedup": result["skipped"],
        "snapshot_id": result.get("snapshot_id"),
        "fte_source_counts": fte_source_counts,
    }


def transform(project_dir: str | Path | None = None) -> dict:
    """Manifest-style entry point — thin wrapper around ``promote_eada_base``."""
    return promote_eada_base(project_dir=project_dir)
