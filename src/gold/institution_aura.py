"""Gold zone transformer for ``consumable.institution_aura``.

Reads ``base.ipeds_finance`` and ``base.eada`` from the silver/base zone,
FULL OUTER JOINs them on UNITID, computes the v1 ``aura_score``
(EDA-finalized 2026-04-30 — see
``governance/eda/consumable-institution-aura-eda.md`` for the full
anchor-validation evidence chain), and promotes to
``consumable.institution_aura`` via the Brightsmith idempotent promote
pattern.

Per spec ``docs/specs/full-pipeline-eada.md`` §6 (post-aura-EDA v1
amendment, 2026-04-30):

  - **Sources:** FULL OUTER JOIN ``base.ipeds_finance`` (~2,675 rows)
    against ``base.eada`` (~2,040 rows) on UNITID.
  - **Identity:** ``unitid`` and ``institution_name`` are
    ``COALESCE(f, e)``.
  - **Passthrough analytical columns:** four IPEDS-Finance per-FTE / ratio
    fields plus three EADA per-FTE / ratio fields.
    ``athletic_subsidy_ratio`` is carried as a context column ONLY — it
    is NOT an aura input (per §2 Decision 11).
  - **Coverage flags:** ``has_ipeds_finance``, ``has_eada``,
    ``coverage_tier`` ∈ {``both``, ``finance_only``,
    ``athletics_only``}.
  - **v1 aura_score algorithm:** for each of the three signals
    (``marketing_ratio``, ``endowment_per_fte``,
    ``athletic_spend_per_fte``), compute the population-level percent
    rank across rows where the signal is non-null.  Per-row, take ONLY
    the rp_* values that are non-null for that row (NULL inputs are
    EXCLUDED, not imputed).  Compute
    ``raw_score = 0.65 * MAX(available_rp) + 0.35 * MEAN(available_rp)``,
    rescale via P5/P95 percentile bounds (EDA-pinned: 0.1413 / 0.9400),
    clamp to [0, 1], stretch to [1, 10], and round.
  - **aura_score_basis (5-value enum):** ``three_term``,
    ``two_term_finance_only``, ``two_term_no_endowment``,
    ``one_term_marketing_only``, or NULL when ``aura_score`` itself is
    NULL.
  - **aura_score_version:** stamped ``"v1"`` for every row.
  - **Grain / record_id:** ``compute_grain_id(row, ['unitid'],
    prefix='aur')``.
  - **Promote:** idempotent — re-running with the same source snapshots
    produces 0 new rows.

The 548 ``athletics_only`` rows have ``has_ipeds_finance = FALSE`` and
no ``marketing_ratio`` / ``endowment_per_fte`` signal; their
``aura_score`` is NULL by construction (the ``aura_score_basis`` cases
all require ``marketing_ratio`` to be non-null per the EDA-finalized
formula).  The athletic-only rp_athletic value is computed across all
rows where ``athletic_spend_per_fte`` is non-null (covering both EADA
strata) so the population statistics are stable across runs.
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import Any

from pyiceberg.schema import Schema
from pyiceberg.types import (
    BooleanType,
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
GRAIN_PREFIX = "aur"
SPEC_NAME = "consumable-institution-aura"
IPEDS_FINANCE_TABLE_FQN = "base.ipeds_finance"
EADA_TABLE_FQN = "base.eada"
CONSUMABLE_NAMESPACE = "consumable"
CONSUMABLE_TABLE_NAME = "institution_aura"

AURA_SCORE_VERSION = "v1"

# v1 composite weights (MAX + MEAN over available rp_* signals).
# EDA-finalized 2026-04-30 — selected from 4 candidates via §6 item 2
# anchor validation; passes 13/13 anchors.  Do NOT change without a new
# EDA + version bump.
WEIGHT_MAX = 0.65
WEIGHT_MEAN = 0.35

# v1 P5/P95 percentile rescale bounds (population-level percentiles of
# raw_score across the production population).  EDA-pinned constants;
# recomputed on each annual refresh.  See
# ``governance/eda/consumable-institution-aura-eda.md`` Item 5.
RAW_SCORE_P5 = 0.1413
RAW_SCORE_P95 = 0.9400

# aura_score_basis enum values (5-value, EDA-expanded 2026-04-30 from
# 3 → 5).  See spec §6 Consumable Transformations rule 4.
BASIS_THREE_TERM = "three_term"
BASIS_TWO_TERM_FINANCE_ONLY = "two_term_finance_only"
BASIS_TWO_TERM_NO_ENDOWMENT = "two_term_no_endowment"
BASIS_ONE_TERM_MARKETING_ONLY = "one_term_marketing_only"

COVERAGE_BOTH = "both"
COVERAGE_FINANCE_ONLY = "finance_only"
COVERAGE_ATHLETICS_ONLY = "athletics_only"

# Column lists for the FULL OUTER MERGE.
FINANCE_COLUMNS: tuple[str, ...] = (
    "unitid",
    "institution_name",
    "endowment_per_fte",
    "institutional_support_per_fte",
    "instruction_per_fte",
    "marketing_ratio",
)
EADA_COLUMNS: tuple[str, ...] = (
    "unitid",
    "institution_name",
    "athletic_spend_per_fte",
    "athletic_revenue_per_fte",
    "athletic_subsidy_ratio",
    "fte_source",
)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def get_consumable_schema() -> Schema:
    """Iceberg schema for ``consumable.institution_aura`` (19 columns).

    Field IDs are dense and stable.  Required-vs-nullable mirrors the
    spec §6 Consumable Schema table:

      - ``record_id``, identity passthroughs, ``aura_score_version``,
        coverage flags, ``coverage_tier``, and ``promoted_at`` are
        required.
      - The seven analytical passthroughs, ``athletic_fte_source``,
        ``aura_score`` / ``aura_score_continuous``, and
        ``aura_score_basis`` are nullable per spec.
    """
    return Schema(
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "unitid", LongType(), required=True),
        NestedField(3, "institution_name", StringType(), required=True),
        NestedField(4, "endowment_per_fte", DoubleType(), required=False),
        NestedField(5, "institutional_support_per_fte", DoubleType(), required=False),
        NestedField(6, "instruction_per_fte", DoubleType(), required=False),
        NestedField(7, "marketing_ratio", DoubleType(), required=False),
        NestedField(8, "athletic_spend_per_fte", DoubleType(), required=False),
        NestedField(9, "athletic_revenue_per_fte", DoubleType(), required=False),
        NestedField(10, "athletic_subsidy_ratio", DoubleType(), required=False),
        NestedField(11, "athletic_fte_source", StringType(), required=False),
        NestedField(12, "aura_score", IntegerType(), required=False),
        NestedField(13, "aura_score_continuous", DoubleType(), required=False),
        NestedField(14, "aura_score_version", StringType(), required=True),
        NestedField(15, "aura_score_basis", StringType(), required=False),
        NestedField(16, "has_ipeds_finance", BooleanType(), required=True),
        NestedField(17, "has_eada", BooleanType(), required=True),
        NestedField(18, "coverage_tier", StringType(), required=True),
        NestedField(19, "promoted_at", TimestampType(), required=True),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_optional_float(value: Any) -> float | None:
    """Coerce a base numeric value to ``float`` or ``None`` (NaN-safe)."""
    if value is None:
        return None
    f = float(value)
    if f != f:  # NaN check
        return None
    return f


def compute_rank_pct(values: list[float | None]) -> list[float | None]:
    """Compute population-level percent rank across non-null values.

    Mirrors SQL ``PERCENT_RANK() OVER (ORDER BY x)`` restricted to rows
    where ``x IS NOT NULL``: a value's rank-pct is
    ``(rank - 1) / (n - 1)`` where ``rank`` is its 1-based ordinal in
    the sorted-ascending non-null subset and ``n`` is the size of that
    subset.  Ties share the lowest rank (consistent with SQL semantics).

    Returns a list aligned to ``values``: NULL inputs map to NULL
    outputs (NOT imputed).  When ``n == 1`` the lone non-null value
    maps to ``0.0``; when ``n == 0`` everything stays NULL.
    """
    non_null_pairs: list[tuple[float, int]] = [
        (float(v), idx) for idx, v in enumerate(values) if v is not None
    ]
    n = len(non_null_pairs)
    out: list[float | None] = [None] * len(values)
    if n == 0:
        return out
    if n == 1:
        out[non_null_pairs[0][1]] = 0.0
        return out

    # Sort ascending by value, then determine each unique value's rank
    # (ties share lowest rank, matching SQL PERCENT_RANK).
    non_null_pairs.sort(key=lambda p: p[0])
    rank_by_idx: dict[int, int] = {}
    i = 0
    while i < n:
        j = i
        # All entries from i..j-1 with equal value get the same rank (i+1).
        while j < n and non_null_pairs[j][0] == non_null_pairs[i][0]:
            rank_by_idx[non_null_pairs[j][1]] = i + 1
            j += 1
        i = j

    denom = float(n - 1)
    for idx, rank in rank_by_idx.items():
        out[idx] = (rank - 1) / denom
    return out


def determine_basis(
    rp_marketing: float | None,
    rp_endowment: float | None,
    rp_athletic: float | None,
) -> str | None:
    """Return the v1 ``aura_score_basis`` enum value, or NULL.

    Mirrors spec §6 rule 4 / EDA Item 4:
      - all three non-null  → ``three_term``
      - mkt + endow only    → ``two_term_finance_only``
      - mkt + ath only      → ``two_term_no_endowment``
      - mkt only            → ``one_term_marketing_only``
      - everything else (incl. no marketing) → NULL aura.

    The 548 ``coverage_tier='athletics_only'`` rows have no
    ``marketing_ratio`` signal (and no ``endowment_per_fte`` signal)
    because ``base.ipeds_finance`` did not match.  They produce NULL
    basis → NULL aura, per the EDA-confirmed semantic that aura is
    a brand-gravity signal anchored on marketing_ratio whenever it
    can be computed.
    """
    has_mkt = rp_marketing is not None
    has_end = rp_endowment is not None
    has_ath = rp_athletic is not None
    if has_mkt and has_end and has_ath:
        return BASIS_THREE_TERM
    if has_mkt and has_end:
        return BASIS_TWO_TERM_FINANCE_ONLY
    if has_mkt and has_ath:
        return BASIS_TWO_TERM_NO_ENDOWMENT
    if has_mkt:
        return BASIS_ONE_TERM_MARKETING_ONLY
    return None


def compute_raw_score(
    rp_marketing: float | None,
    rp_endowment: float | None,
    rp_athletic: float | None,
) -> float | None:
    """Compute v1 raw_score = 0.65*MAX(rp_*) + 0.35*MEAN(rp_*).

    The MAX and MEAN are taken ONLY over the AVAILABLE (non-null)
    rp_* values for this row — NULL inputs are excluded, NOT imputed.
    Returns None when no rp_* signal is available.
    """
    available = [v for v in (rp_marketing, rp_endowment, rp_athletic) if v is not None]
    if not available:
        return None
    return WEIGHT_MAX * max(available) + WEIGHT_MEAN * (sum(available) / len(available))


def rescale_aura(raw_score: float | None) -> tuple[float | None, int | None]:
    """Apply EDA-pinned P5/P95 rescale → (continuous, integer) tuple.

    Per EDA Item 5: linear stretch [P5=0.1413, P95=0.9400] → [1, 10],
    clamp to [0, 1] before stretching, then ``round`` the continuous
    value (Python's banker's rounding matches DuckDB's default ROUND).
    Both outputs are NULL when ``raw_score`` is None.
    """
    if raw_score is None:
        return None, None
    span = RAW_SCORE_P95 - RAW_SCORE_P5
    t = (raw_score - RAW_SCORE_P5) / span
    t_clipped = max(0.0, min(1.0, t))
    aura_continuous = 1.0 + 9.0 * t_clipped
    return aura_continuous, int(round(aura_continuous))


def derive_coverage_tier(has_finance: bool, has_eada: bool) -> str:
    """Map the (has_finance, has_eada) pair to the coverage_tier enum."""
    if has_finance and has_eada:
        return COVERAGE_BOTH
    if has_finance:
        return COVERAGE_FINANCE_ONLY
    return COVERAGE_ATHLETICS_ONLY


# ---------------------------------------------------------------------------
# Merge + transform
# ---------------------------------------------------------------------------


def _normalize_finance_row(row: dict) -> dict:
    """Coerce the IPEDS-Finance subset of fields to a stable types dict."""
    return {
        "unitid": int(row["unitid"]),
        "institution_name": str(row["institution_name"]),
        "endowment_per_fte": _to_optional_float(row.get("endowment_per_fte")),
        "institutional_support_per_fte": _to_optional_float(
            row.get("institutional_support_per_fte")
        ),
        "instruction_per_fte": _to_optional_float(row.get("instruction_per_fte")),
        "marketing_ratio": _to_optional_float(row.get("marketing_ratio")),
    }


def _normalize_eada_row(row: dict) -> dict:
    """Coerce the EADA subset of fields to a stable types dict."""
    return {
        "unitid": int(row["unitid"]),
        "institution_name": str(row["institution_name"]),
        "athletic_spend_per_fte": _to_optional_float(row.get("athletic_spend_per_fte")),
        "athletic_revenue_per_fte": _to_optional_float(
            row.get("athletic_revenue_per_fte")
        ),
        "athletic_subsidy_ratio": _to_optional_float(row.get("athletic_subsidy_ratio")),
        "fte_source": (
            str(row["fte_source"]) if row.get("fte_source") is not None else None
        ),
    }


def full_outer_merge(
    finance_rows: list[dict],
    eada_rows: list[dict],
) -> list[dict]:
    """FULL OUTER JOIN base.ipeds_finance × base.eada on UNITID.

    Returns one merged dict per UNITID with the COALESCE'd identity
    columns, the seven analytical passthroughs, the
    ``athletic_fte_source`` provenance pass-through, and the three
    coverage flags.  rp_* / aura_* fields are NOT computed here — that
    happens in ``compute_aura_columns`` after we have the full row set
    so population percent ranks are stable.

    Enforces UNITID uniqueness on each side (base tables already have
    UNITID grain; this fails loud rather than silently last-write-wins).
    """
    finance_by_unitid: dict[int, dict] = {}
    for row in finance_rows:
        norm = _normalize_finance_row(row)
        if norm["unitid"] in finance_by_unitid:
            raise ValueError(
                f"Duplicate unitid in base.ipeds_finance: {norm['unitid']}"
            )
        finance_by_unitid[norm["unitid"]] = norm

    eada_by_unitid: dict[int, dict] = {}
    for row in eada_rows:
        norm = _normalize_eada_row(row)
        if norm["unitid"] in eada_by_unitid:
            raise ValueError(f"Duplicate unitid in base.eada: {norm['unitid']}")
        eada_by_unitid[norm["unitid"]] = norm

    all_unitids = sorted(set(finance_by_unitid) | set(eada_by_unitid))
    merged: list[dict] = []
    for unitid in all_unitids:
        f = finance_by_unitid.get(unitid)
        e = eada_by_unitid.get(unitid)

        has_finance = f is not None
        has_eada_flag = e is not None

        # COALESCE identity columns.
        institution_name = (f or e or {})["institution_name"]  # type: ignore[index]

        merged.append(
            {
                "unitid": unitid,
                "institution_name": institution_name,
                "endowment_per_fte": f["endowment_per_fte"] if f else None,
                "institutional_support_per_fte": (
                    f["institutional_support_per_fte"] if f else None
                ),
                "instruction_per_fte": f["instruction_per_fte"] if f else None,
                "marketing_ratio": f["marketing_ratio"] if f else None,
                "athletic_spend_per_fte": (
                    e["athletic_spend_per_fte"] if e else None
                ),
                "athletic_revenue_per_fte": (
                    e["athletic_revenue_per_fte"] if e else None
                ),
                "athletic_subsidy_ratio": (
                    e["athletic_subsidy_ratio"] if e else None
                ),
                "athletic_fte_source": e["fte_source"] if e else None,
                "has_ipeds_finance": has_finance,
                "has_eada": has_eada_flag,
                "coverage_tier": derive_coverage_tier(has_finance, has_eada_flag),
            }
        )
    return merged


def compute_aura_columns(merged_rows: list[dict]) -> list[dict]:
    """Stamp rp_*, raw_score, aura_score, aura_score_continuous, basis.

    Computes population percent ranks for the three signals across the
    merged row set, then per-row applies the v1 algorithm:

      1. Determine ``aura_score_basis`` from which rp_* are non-null.
      2. ``raw_score = 0.65 * MAX(available) + 0.35 * MEAN(available)``.
      3. Linear-rescale via P5/P95 → [1, 10], clamp + round.

    Mutates ``merged_rows`` in place AND returns it (caller convenience).
    The intermediate rp_* values are NOT written to the consumable
    schema — they are an implementation detail of the score derivation.
    """
    rp_marketing = compute_rank_pct(
        [row["marketing_ratio"] for row in merged_rows]
    )
    rp_endowment = compute_rank_pct(
        [row["endowment_per_fte"] for row in merged_rows]
    )
    rp_athletic = compute_rank_pct(
        [row["athletic_spend_per_fte"] for row in merged_rows]
    )

    for idx, row in enumerate(merged_rows):
        rp_m = rp_marketing[idx]
        rp_e = rp_endowment[idx]
        rp_a = rp_athletic[idx]

        basis = determine_basis(rp_m, rp_e, rp_a)
        if basis is None:
            # Per spec §6 rule 4: aura_score is NULL whenever basis is NULL.
            # The 5-value basis enum requires marketing_ratio; rows without
            # it (548 athletics_only + 31 zero-instruction system shells)
            # produce NULL aura regardless of whether other rp_* signals
            # exist, because no v1 case fires without marketing.
            aura_continuous: float | None = None
            aura_int: int | None = None
        else:
            raw_score = compute_raw_score(rp_m, rp_e, rp_a)
            aura_continuous, aura_int = rescale_aura(raw_score)

        row["aura_score"] = aura_int
        row["aura_score_continuous"] = aura_continuous
        row["aura_score_version"] = AURA_SCORE_VERSION
        row["aura_score_basis"] = basis

    return merged_rows


def stamp_record_ids(rows: list[dict], promoted_at: datetime.datetime) -> list[dict]:
    """Stamp deterministic record_id + promoted_at on every row."""
    for row in rows:
        row["promoted_at"] = promoted_at
        row["record_id"] = compute_grain_id(row, GRAIN_FIELDS, prefix=GRAIN_PREFIX)
    return rows


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
    """Run the gold transformation for ``consumable.institution_aura``.

    Reads ``base.ipeds_finance`` (~2,675 rows) and ``base.eada``
    (~2,040 rows) from the silver/base zone, FULL OUTER JOINs on UNITID
    to produce ~3,223 rows, computes the v1 aura score, and promotes
    via the idempotent promote pattern.  Re-running with the same
    source snapshots produces 0 new rows.

    Args:
        project_dir: Project root.  Defaults to the current working
            directory.  Only used when warehouse / catalog paths are
            left as None.
        base_warehouse: Override for the silver/base Iceberg warehouse
            path.
        consumable_warehouse: Override for the gold/consumable Iceberg
            warehouse path.
        catalog_path: Override for the shared SQLite catalog DB path.
        promoted_at: Override for the promotion timestamp (tests pass
            a fixed value for determinism).

    Returns:
        Dict with run metrics: ``rows_finance``, ``rows_eada``,
        ``rows_merged``, ``coverage_tier_counts``,
        ``aura_score_basis_counts``, ``aura_score_bucket_counts``,
        ``promoted``, ``skipped_dedup``, ``snapshot_id``.
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

    if promoted_at is None:
        promoted_at = datetime.datetime.now(tz=datetime.timezone.utc)

    # Read base.ipeds_finance + base.eada from the silver catalog.
    logger.info("Reading from %s and %s...", IPEDS_FINANCE_TABLE_FQN, EADA_TABLE_FQN)
    base_catalog = get_catalog(base_warehouse, catalog_path)

    finance_table = base_catalog.load_table(IPEDS_FINANCE_TABLE_FQN)
    finance_rows = read_with_duckdb(finance_table)
    logger.info(
        "Read %d rows from %s (snap %s)",
        len(finance_rows),
        IPEDS_FINANCE_TABLE_FQN,
        finance_table.metadata.current_snapshot_id,
    )

    eada_table = base_catalog.load_table(EADA_TABLE_FQN)
    eada_rows = read_with_duckdb(eada_table)
    logger.info(
        "Read %d rows from %s (snap %s)",
        len(eada_rows),
        EADA_TABLE_FQN,
        eada_table.metadata.current_snapshot_id,
    )

    # FULL OUTER JOIN on UNITID.
    logger.info("FULL OUTER JOIN base.ipeds_finance × base.eada on UNITID...")
    merged_rows = full_outer_merge(finance_rows, eada_rows)
    logger.info("Merged %d rows", len(merged_rows))

    # Compute v1 aura columns (rp_*, raw_score, aura_score, basis).
    logger.info("Computing v1 aura_score (MAX+MEAN, P5/P95 rescale)...")
    compute_aura_columns(merged_rows)

    # Stamp record_id + promoted_at.
    stamp_record_ids(merged_rows, promoted_at)

    # Distribution logs for spot-check parity with the EDA report.
    coverage_counts: dict[str, int] = {}
    basis_counts: dict[str | None, int] = {}
    bucket_counts: dict[str, int] = {"[1-3]": 0, "[4-6]": 0, "[7-10]": 0, "NULL": 0}
    for row in merged_rows:
        coverage_counts[row["coverage_tier"]] = (
            coverage_counts.get(row["coverage_tier"], 0) + 1
        )
        basis_counts[row["aura_score_basis"]] = (
            basis_counts.get(row["aura_score_basis"], 0) + 1
        )
        score = row["aura_score"]
        if score is None:
            bucket_counts["NULL"] += 1
        elif score <= 3:
            bucket_counts["[1-3]"] += 1
        elif score <= 6:
            bucket_counts["[4-6]"] += 1
        else:
            bucket_counts["[7-10]"] += 1

    logger.info("coverage_tier distribution: %s", sorted(coverage_counts.items()))
    logger.info(
        "aura_score_basis distribution: %s",
        sorted(basis_counts.items(), key=lambda p: (p[0] is None, p[0] or "")),
    )
    logger.info("aura_score bucket distribution: %s", bucket_counts)

    # Promote to consumable.institution_aura.
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
        merged_rows,
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
        "rows_finance": len(finance_rows),
        "rows_eada": len(eada_rows),
        "rows_merged": len(merged_rows),
        "coverage_tier_counts": coverage_counts,
        "aura_score_basis_counts": {
            (k if k is not None else "NULL"): v for k, v in basis_counts.items()
        },
        "aura_score_bucket_counts": bucket_counts,
        "promoted": result["promoted"],
        "skipped_dedup": result["skipped"],
        "snapshot_id": result.get("snapshot_id"),
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
    )
    result = transform()
    print(f"Gold transform complete: {result}")
