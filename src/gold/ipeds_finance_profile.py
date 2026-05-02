"""Gold zone transformer for ``consumable.ipeds_finance_profile``.

Reads ``base.ipeds_finance`` from the Silver/base zone and produces the
institution-level finance profile consumed downstream (notably by
``raw-ingest-eada.md`` for composite ratio fusion). This is a
shaping-only base→consumable promote: no cross-source joins, no new
arithmetic beyond the ``data_completeness_tier`` synthesis.

v1.4 (`docs/specs/ipeds-finance-v1.4.md`) §6 deltas:

  - **Passthrough (renamed):** ``endowment_value_flag`` from base →
    exposed at consumable as ``endowment_value_provenance``
    (§2 Decision A — consumer clarity).
  - **Passthrough (restored):** ``source_load_date`` from base, NOT
    NULL (§2 Decision G — preserves base's NOT NULL guarantee).
  - **System-administrative-office filter:** ~33 rows are dropped
    BEFORE the promote write per the spec §6 SQL ``WHERE NOT (...)``
    clause.  A row is excluded only when (a) ``institution_name``
    matches one of 8 LIKE patterns AND (b) at least one of four
    organizational-shell signals: ``instruction_expenses IS NULL``,
    ``instruction_expenses < $1,000,000``, ``total_fte_enrollment IS
    NULL``, or ``total_fte_enrollment < 50``.  The AND-clause is the
    deliberate guardrail against false-positives on real teaching
    institutions whose names happen to match a pattern (§2 Decision B);
    real teaching institutions have positive FTE.  v1.3 amendment
    (chaos-monkey R1) extended the v1.0–v1.2 2-disjunct numeric proxy
    to 4 disjuncts after the v1.4 chaos pass found 9 administrative
    entities surviving the 2-clause proxy with `instruction_expenses`
    between $1.73M and $6.83M AND `total_fte_enrollment IS NULL`
    (e.g., LA CCD District Office, SUNY-System Office, UMass-Central
    Office, DeVry-Administrative Office).  CON-IFP-001 splits into
    CON-IFP-001a (upper bound, P0) + CON-IFP-001b (lower bound, P1).

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

# v1.4 §6 system-administrative-office filter pattern.  The eight LIKE
# patterns are evaluated against ``LOWER(institution_name)``; a row is
# excluded only when (a) the institution_name matches at least one
# pattern AND (b) at least one of four organizational-shell signals
# fires: ``instruction_expenses IS NULL`` OR
# ``instruction_expenses < $1,000,000`` OR
# ``total_fte_enrollment IS NULL`` OR ``total_fte_enrollment < 50``.
# v1.3 (chaos-monkey R1) extended the original v1.0–v1.2 2-disjunct
# numeric proxy with two FTE disjuncts after the v1.4 chaos pass found
# 9 administrative entities with FTE NULL and instruction in the
# $1.73M–$6.83M band that survived the 2-clause version.  The AND-clause
# is the structural guardrail against false-positives on real teaching
# institutions whose names happen to match a pattern (per §2 Decision B);
# real teaching institutions have positive FTE >= 50.
SYSTEM_OFFICE_NAME_PATTERNS: tuple[str, ...] = (
    "% office",
    "% system",
    "% system %",
    "%chancellor%",
    "%central office%",
    "%system office%",
    "%district office%",
    "%sistema universitario%",  # v1.1: catches UNITID 242060
)

# Numeric-proxy threshold for the system-office filter — a real
# teaching institution cannot operate on under $1M of instruction.
SYSTEM_OFFICE_INSTRUCTION_THRESHOLD: float = 1_000_000.0

# v1.3 amendment: FTE numeric-proxy threshold (strict less-than).  Real
# teaching institutions have FTE well above 50; the v1.4 chaos pass
# documented 9 admin entities with FTE NULL surviving the v1.0–v1.2
# 2-clause numeric proxy.  Threshold of 50 is well below any real
# teaching institution and comfortably catches the FTE-NULL admin
# cluster while preserving small-school edge cases.
SYSTEM_OFFICE_FTE_THRESHOLD: float = 50.0

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
    """Iceberg schema for ``consumable.ipeds_finance_profile`` (17 columns — v1.4 §6).

    Field IDs are dense and stable.  Column order matches the spec §6
    Consumable Schema table.  Required-vs-nullable mirrors the spec:

      - ``record_id``, identity passthroughs, ``data_completeness_tier``,
        ``source_load_date`` (v1.4 §2 Decision G — NOT NULL preserves
        base's NOT NULL guarantee), and ``promoted_at`` are required.
      - The four raw / FTE passthroughs and four derived per-FTE / ratio
        passthroughs are nullable (the F3-endowment and zero-FTE
        realities make any required-not-null rule false on real data).
      - ``endowment_value_provenance`` (v1.4 §2 Decision A — renamed
        passthrough from ``base.ipeds_finance.endowment_value_flag``)
        is nullable.  NULL on F3 (structural).  On F1A/F2 the observed
        FY2023 domain is ``{R, A, P, Z, N}``.  Authoritative semantics:
        ``R`` = Reported; ``A`` = Not applicable (institution has no
        endowment fund — exact ``A``↔NULL coupling); ``N``/``P``/``Z``
        = NCES-imputed values.
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
        NestedField(16, "endowment_value_provenance", StringType(), required=False),
        NestedField(17, "source_load_date", DateType(), required=True),
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
# System-administrative-office filter (v1.4 §6 Item 2)
# ---------------------------------------------------------------------------


def _name_matches_system_office_pattern(institution_name: str | None) -> bool:
    """True if ``LOWER(institution_name)`` matches one of the 8 SQL LIKE patterns.

    Pure-Python translation of the SQL LIKE-clauses in spec §6.  ``%`` is
    "any sequence" (including the empty sequence) and pattern boundaries
    matter.  Patterns:

      - ``"% office"``        — name ends with " office"
      - ``"% system"``        — name ends with " system"
      - ``"% system %"``      — " system " appears with whitespace flanks
      - ``"%chancellor%"``    — substring "chancellor"
      - ``"%central office%"`` — substring "central office"
      - ``"%system office%"``  — substring "system office"
      - ``"%district office%"`` — substring "district office"
      - ``"%sistema universitario%"`` — substring "sistema universitario"
        (v1.1 — Spanish-language Puerto Rico system-office convention,
        catches UNITID 242060 "Sistema Universitario Ana G. Mendez")

    The check is case-insensitive (matches SQL ``LOWER(...)``).
    """
    if institution_name is None:
        return False
    name = institution_name.lower()
    # Endswith patterns ("% office", "% system").
    if name.endswith(" office") or name.endswith(" system"):
        return True
    # " system " bordered by whitespace.
    if " system " in name:
        return True
    # Substring patterns.
    for substring in (
        "chancellor",
        "central office",
        "system office",
        "district office",
        "sistema universitario",
    ):
        if substring in name:
            return True
    return False


def is_system_office_row(base_row: dict) -> bool:
    """True if the base row should be excluded by the v1.4 §6 system-office filter.

    Implements the spec §6 SQL ``WHERE NOT (...)``-clause's exclusion
    predicate.  A row is excluded only when **both** halves of the AND
    are satisfied:

      (a) ``institution_name`` matches one of the 8 LIKE patterns
          (``_name_matches_system_office_pattern``).
      (b) ``instruction_expenses`` is NULL OR < $1,000,000 OR
          ``total_fte_enrollment`` is NULL OR < 50.

    v1.3 amendment (chaos-monkey R1): the numeric proxy was extended
    from 2 disjuncts (instruction-NULL OR < $1M) to 4 disjuncts after
    the v1.4 chaos pass surfaced 9 admin entities with `instruction
    >= $1M` AND `total_fte_enrollment IS NULL` (LA CCD District Office,
    SUNY-System Office, Rancho Santiago CCD Office, Alamo CCD Central
    Office, Inter American U Puerto Rico-Central Office, UMass-Central
    Office, Chamberlain U-Administrative Office, Minnesota State System
    Office, DeVry-Administrative Office).  All 9 had instruction in the
    $1.73M–$6.83M band — above the $1M floor but with FTE NULL — and
    leaked past the original 2-clause proxy.

    The AND-clause is the deliberate guardrail (§2 Decision B): a real
    teaching institution whose name contains "Office" or "System" but
    that reports >= $1M of instruction AND >= 50 FTE is preserved.  A
    small teaching institution whose name does not match any pattern is
    also preserved.  Only the intersection — admin-pattern name AND
    organizational-shell signal — is dropped.

    The ``< 50`` and ``< 1_000_000.0`` are strict less-thans; a row
    with FTE exactly 50 OR instruction exactly $1M does not satisfy the
    numeric-proxy disjunct on its own.
    """
    if not _name_matches_system_office_pattern(base_row.get("institution_name")):
        return False
    instruction = base_row.get("instruction_expenses")
    if instruction is None:
        return True
    if instruction < SYSTEM_OFFICE_INSTRUCTION_THRESHOLD:
        return True
    fte = base_row.get("total_fte_enrollment")
    if fte is None:
        return True
    return fte < SYSTEM_OFFICE_FTE_THRESHOLD


# ---------------------------------------------------------------------------
# Row transform
# ---------------------------------------------------------------------------


def transform_row(
    base_row: dict,
    promoted_at: datetime.datetime,
) -> dict:
    """Transform one base row into a consumable ``ipeds_finance_profile`` row.

    Pure shaping: passes the 12 base fields through verbatim, synthesizes
    ``data_completeness_tier``, renames ``endowment_value_flag`` →
    ``endowment_value_provenance`` per v1.4 §2 Decision A, restores the
    ``source_load_date`` passthrough per v1.4 §2 Decision G, and stamps
    ``record_id`` + ``promoted_at``.  No cross-source joins.  No new
    arithmetic on the per-FTE / ratio fields — those remain whatever the
    base transformer computed (CON-IFP-007 arithmetic invariant is
    upstream of this transformer).
    """
    record: dict[str, Any] = {field: base_row.get(field) for field in BASE_PASSTHROUGH_FIELDS}
    record["data_completeness_tier"] = classify_data_completeness_tier(base_row)
    record["promoted_at"] = promoted_at
    # v1.4 §2 Decision A: rename base.endowment_value_flag →
    # consumable.endowment_value_provenance.  Pure passthrough, no
    # transformation.  CON-IFP-013 asserts passthrough fidelity.
    flag_value = base_row.get("endowment_value_flag")
    record["endowment_value_provenance"] = (
        str(flag_value) if flag_value is not None else None
    )
    # v1.4 §2 Decision G: restored passthrough.  Base guarantees NOT NULL,
    # so consumable carries the same NOT NULL constraint.  CON-IFP-015
    # asserts 100% non-null at consumable.
    record["source_load_date"] = base_row.get("source_load_date")
    record["record_id"] = compute_grain_id(record, GRAIN_FIELDS, prefix=GRAIN_PREFIX)
    return record


def transform_rows(
    base_rows: list[dict],
    promoted_at: datetime.datetime | None = None,
) -> list[dict]:
    """Transform every base row into a consumable row.

    v1.4 §6 Item 2: the system-administrative-office filter is applied
    BEFORE the per-row transformation so the dropped rows never appear
    in the consumable output.  Per §2 Decision B the filter is
    name-pattern-AND-numeric-proxy — both halves must match for
    exclusion (see ``is_system_office_row``).  Expected drop on the
    FY2023-landed snapshot: ~33 rows under the v1.3 4-clause numeric
    proxy (24 caught by the v1.0–v1.2 2-clause version + 9 caught by
    the v1.3 FTE disjuncts).  CON-IFP-001a (upper bound, P0) +
    CON-IFP-001b (lower bound, P1) replace v1.3's strict equality.

    Enforces UNITID uniqueness up front (post-filter) so a
    duplicate-grain base snapshot fails loud here rather than silently
    dedup-skipping at promote time (CON-IFP-003 uniqueness invariant).
    """
    if promoted_at is None:
        promoted_at = datetime.datetime.now(tz=datetime.timezone.utc)

    # v1.4 §6: drop system-administrative-office rows BEFORE the promote
    # write.  is_system_office_row() implements the spec §6 SQL
    # WHERE NOT (...)-clause's exclusion predicate verbatim.
    filtered_base_rows = [row for row in base_rows if not is_system_office_row(row)]

    consumable_rows = [transform_row(row, promoted_at) for row in filtered_base_rows]

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
    consumable shape (pass through 12 base fields + the v1.4
    ``endowment_value_provenance`` rename + the v1.4 ``source_load_date``
    restoration + synthesize ``data_completeness_tier``), drops
    system-administrative-office rows per the v1.4 §6 filter, and
    promotes to ``consumable.ipeds_finance_profile`` via the idempotent
    promote pattern.  Re-running with the same base snapshot produces
    0 new rows.

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

    # v1.4 §6: log the system-office filter drop count for the
    # implementation log (the dropped UNITIDs are recorded in §9).
    excluded_rows = [row for row in base_rows if is_system_office_row(row)]
    excluded_unitids = sorted(int(row["unitid"]) for row in excluded_rows)
    logger.info(
        "v1.4 system-office filter: %d rows excluded (UNITIDs: %s)",
        len(excluded_rows),
        excluded_unitids,
    )

    # Transform (system-office filter is applied inside transform_rows).
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
        "rows_excluded_system_office": len(excluded_rows),
        "excluded_unitids": excluded_unitids,
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
