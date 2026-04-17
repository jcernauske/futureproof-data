"""Gold zone transformer for consumable.program_career_paths and consumable.career_branches.

Reads consumable.career_outcomes, consumable.occupation_profiles,
consumable.onet_work_profiles, consumable.career_transitions (Gold),
and base.cip_soc_crosswalk (Silver). Joins them via CIP prefix matching,
computes pentagon stats (ERN, ROI, GRW, HMN; RES placeholder),
boss fight scores, match quality, and confidence tiers.

Table 1 Grain: unitid x cipcode x soc_code
Table 2 Grain: soc_code x related_soc_code

Record IDs:
  Table 1: compute_grain_id(row, ['unitid', 'cipcode', 'soc_code'], prefix='pcp')
  Table 2: compute_grain_id(row, ['soc_code', 'related_soc_code'], prefix='br')
"""

import datetime
import logging
import math
from pathlib import Path

import duckdb
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
from brightsmith.infra.iceberg_setup import get_catalog, get_or_create_table
from brightsmith.infra.promote import promote

logger = logging.getLogger(__name__)

SPEC_NAME = "gold-futureproof-engine"

# Table 1 constants
PCP_GRAIN_FIELDS = ["unitid", "cipcode", "soc_code"]
PCP_GRAIN_PREFIX = "pcp"

# Table 2 constants
BR_GRAIN_FIELDS = ["soc_code", "related_soc_code"]
BR_GRAIN_PREFIX = "br"

# ---------------------------------------------------------------------------
# ROI piecewise breakpoints: (dte_lower, dte_upper, roi_lower, roi_upper)
# ---------------------------------------------------------------------------

ROI_BREAKPOINTS: list[tuple[float, float, float, float]] = [
    # DTE <= 0.25              -> ROI 10  (excellent, handled as floor below)
    (0.25, 0.50, 10.0, 9.0),  # excellent
    (0.50, 0.75, 9.0, 7.0),   # good
    (0.75, 1.00, 7.0, 5.0),   # mediocre
    (1.00, 1.50, 5.0, 3.0),   # bad — debt exceeds annual earnings
    (1.50, 2.50, 3.0, 1.0),   # terrible
    # DTE >= 2.5               -> ROI 1   (catastrophic, handled as cap below)
]


def _round_half_up(x: float) -> int:
    """Round to nearest integer using round-half-up (standard) rounding.

    Python's built-in round() uses banker's rounding (round half to even),
    which differs from DuckDB's ROUND(). This function matches DuckDB:
      round_half_up(2.5) = 3  (Python round(2.5) = 2)
      round_half_up(6.5) = 7  (Python round(6.5) = 6)
    """
    return int(math.floor(x + 0.5))


def compute_stat_ern(
    cip_family_earnings_rank: float | None,
    wage_percentile_overall: float | None,
) -> int | None:
    """Compute Earning Power stat (1-10).

    Blends 60% program-level earnings rank with 40% occupation-level wage
    percentile. Returns None if either input is None.
    """
    if cip_family_earnings_rank is None or wage_percentile_overall is None:
        return None
    raw = 0.6 * cip_family_earnings_rank + 0.4 * wage_percentile_overall
    return _round_half_up(1.0 + 9.0 * raw)


def compute_stat_roi(debt_to_earnings_annual: float | None) -> int | None:
    """Compute Return on Investment stat (1-10).

    Piecewise linear mapping from debt-to-earnings ratio.
    Lower DTE = better ROI = higher score.
    Returns None if input is None.
    """
    if debt_to_earnings_annual is None:
        return None

    dte = debt_to_earnings_annual

    # Floor: excellent ROI
    if dte <= 0.25:
        return 10

    # Piecewise linear interpolation
    for dte_lo, dte_hi, roi_lo, roi_hi in ROI_BREAKPOINTS:
        if dte <= dte_hi:
            fraction = (dte - dte_lo) / (dte_hi - dte_lo)
            return _round_half_up(roi_lo + fraction * (roi_hi - roi_lo))

    # Cap: very poor ROI
    return 1


def compute_boss_ceiling(
    wage_percentile_education_tier: float | None,
) -> int | None:
    """Compute Ceiling Boss score (1-10).

    Low earner within education tier = strong boss (ceiling is real).
    High earner = weak boss (already pushed past it).
    Returns None if input is None.
    """
    if wage_percentile_education_tier is None:
        return None
    return _round_half_up(10.0 - 9.0 * wage_percentile_education_tier)


def derive_match_quality(has_bls: bool, has_onet: bool) -> str:
    """Derive match quality from join success flags."""
    if has_bls and has_onet:
        return "full"
    elif has_bls and not has_onet:
        return "partial_no_onet"
    elif not has_bls and has_onet:
        return "partial_no_bls"
    else:
        return "scorecard_only"


def derive_overall_confidence(
    stats_available_count: int, match_quality: str
) -> str:
    """Derive overall confidence tier from stats count and match quality."""
    if stats_available_count >= 4 and match_quality == "full":
        return "high"
    elif stats_available_count >= 2 and "partial" in match_quality:
        return "medium"
    else:
        return "low"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


def get_pcp_schema() -> Schema:
    """Iceberg schema for consumable.program_career_paths (40 columns)."""
    return Schema(
        # Core Identity
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "unitid", LongType(), required=True),
        NestedField(3, "institution_name", StringType(), required=True),
        NestedField(4, "cipcode", StringType(), required=True),
        NestedField(5, "program_name", StringType(), required=True),
        NestedField(6, "cip_family", StringType(), required=True),
        NestedField(7, "cip_family_name", StringType(), required=True),
        NestedField(8, "soc_code", StringType(), required=True),
        NestedField(9, "occupation_title", StringType(), required=True),
        NestedField(10, "soc_major_group_name", StringType(), required=False),
        # Pentagon Stats
        NestedField(11, "stat_ern", IntegerType(), required=False),
        NestedField(12, "stat_roi", IntegerType(), required=False),
        NestedField(13, "stat_res", IntegerType(), required=False),
        NestedField(14, "stat_grw", IntegerType(), required=False),
        NestedField(15, "stat_hmn", IntegerType(), required=False),
        # Boss Fight Profile
        NestedField(16, "boss_ai_score", IntegerType(), required=False),
        NestedField(17, "boss_loans_score", IntegerType(), required=False),
        NestedField(18, "boss_market_score", IntegerType(), required=False),
        NestedField(19, "boss_burnout_score", IntegerType(), required=False),
        NestedField(20, "boss_ceiling_score", IntegerType(), required=False),
        # Program Context
        NestedField(21, "earnings_1yr_median", DoubleType(), required=False),
        NestedField(22, "earnings_1yr_p25", DoubleType(), required=False),
        NestedField(23, "earnings_1yr_p75", DoubleType(), required=False),
        NestedField(24, "debt_median", DoubleType(), required=False),
        NestedField(25, "debt_to_earnings_annual", DoubleType(), required=False),
        NestedField(26, "confidence_tier_program", StringType(), required=False),
        # Occupation Context
        NestedField(27, "median_annual_wage", DoubleType(), required=False),
        NestedField(28, "growth_category", StringType(), required=False),
        NestedField(29, "employment_current", LongType(), required=False),
        NestedField(30, "education_level_name", StringType(), required=False),
        NestedField(31, "top_5_activities", StringType(), required=False),
        NestedField(32, "top_human_activities", StringType(), required=False),
        NestedField(33, "burnout_drivers", StringType(), required=False),
        NestedField(34, "time_pressure", DoubleType(), required=False),
        NestedField(35, "work_hours", DoubleType(), required=False),
        # Data Quality
        NestedField(36, "match_quality", StringType(), required=True),
        NestedField(37, "stats_available_count", IntegerType(), required=True),
        NestedField(38, "bosses_available_count", IntegerType(), required=True),
        NestedField(39, "overall_confidence", StringType(), required=True),
        # Metadata
        NestedField(40, "promoted_at", TimestampType(), required=True),
        # Option B composite provenance (S4 v4 — three-signal-ai-exposure-composite).
        # Threaded through from consumable.ai_exposure so receipts and the
        # Fight AI narrative prompt can reference the composite method and
        # velocity label without re-joining at query time.
        NestedField(41, "ai_adoption_share", DoubleType(), required=False),
        NestedField(42, "velocity_label", StringType(), required=False),
        NestedField(43, "composite_method", StringType(), required=False),
        NestedField(44, "adoption_percentile", DoubleType(), required=False),
        # Cost-based ROI + institution cost enrichment — threaded through from
        # consumable.career_outcomes so the backend stat_engine can drive the
        # cost-based ROI + financing-aware Loans Boss without falling back to
        # the debt_median legacy path. Plan:
        # ~/.claude/plans/why-are-we-still-jaunty-curry.md
        NestedField(45, "roi_cost_basis", StringType(), required=False),
        NestedField(46, "net_price_annual", DoubleType(), required=False),
        NestedField(47, "cost_of_attendance_annual", DoubleType(), required=False),
        NestedField(48, "institution_control", StringType(), required=False),
        NestedField(49, "net_price_4yr", DoubleType(), required=False),
        NestedField(50, "tuition_in_state", DoubleType(), required=False),
        NestedField(51, "tuition_out_of_state", DoubleType(), required=False),
        NestedField(52, "room_board_on_campus", DoubleType(), required=False),
    )


def get_br_schema() -> Schema:
    """Iceberg schema for consumable.career_branches (34 columns).

    30 baseline columns (24 originals + 6 AI Exposure backfill) plus 4
    additive experience columns (IDs 31-34) introduced by the
    ``onet-experience-requirements`` spec (§Zone 3, 2026-04-16). All four
    experience columns are ``required=False`` — they NULL-propagate when
    the source or target BLS SOC has no row in
    ``base.onet_experience_profiles``.
    """
    return Schema(
        # Core Identity
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "soc_code", StringType(), required=True),
        NestedField(3, "source_title", StringType(), required=True),
        NestedField(4, "related_soc_code", StringType(), required=True),
        NestedField(5, "related_title", StringType(), required=True),
        NestedField(6, "best_index", IntegerType(), required=True),
        NestedField(7, "relatedness_tier", StringType(), required=True),
        NestedField(8, "is_primary", BooleanType(), required=True),
        # Source Stats
        NestedField(9, "source_grw", IntegerType(), required=False),
        NestedField(10, "source_hmn", IntegerType(), required=False),
        NestedField(11, "source_burnout", IntegerType(), required=False),
        NestedField(12, "source_wage", DoubleType(), required=False),
        # Related Stats
        NestedField(13, "related_grw", IntegerType(), required=False),
        NestedField(14, "related_hmn", IntegerType(), required=False),
        NestedField(15, "related_burnout", IntegerType(), required=False),
        NestedField(16, "related_wage", DoubleType(), required=False),
        NestedField(17, "related_growth_category", StringType(), required=False),
        NestedField(18, "related_education_level", StringType(), required=False),
        # Stat Deltas
        NestedField(19, "grw_delta", IntegerType(), required=False),
        NestedField(20, "hmn_delta", IntegerType(), required=False),
        NestedField(21, "burnout_delta", IntegerType(), required=False),
        NestedField(22, "wage_delta", DoubleType(), required=False),
        NestedField(23, "branch_has_full_data", BooleanType(), required=True),
        # Metadata
        NestedField(24, "promoted_at", TimestampType(), required=True),
        # AI Exposure Stats (backfill)
        NestedField(25, "source_res", IntegerType(), required=False),
        NestedField(26, "source_ai_boss", IntegerType(), required=False),
        NestedField(27, "related_res", IntegerType(), required=False),
        NestedField(28, "related_ai_boss", IntegerType(), required=False),
        NestedField(29, "res_delta", IntegerType(), required=False),
        NestedField(30, "ai_boss_delta", IntegerType(), required=False),
        # Experience (spec: onet-experience-requirements §Zone 3, 2026-04-16)
        NestedField(31, "related_experience_years", DoubleType(), required=False),
        NestedField(32, "related_experience_tier", StringType(), required=False),
        NestedField(33, "source_experience_years", DoubleType(), required=False),
        NestedField(34, "experience_delta_years", DoubleType(), required=False),
    )


# ---------------------------------------------------------------------------
# Table 1: program_career_paths derivation
# ---------------------------------------------------------------------------

# SQL: Join career_outcomes to crosswalk via CIP prefix match, then LEFT JOIN
# to occupation_profiles and onet_work_profiles. Dedup on grain.
PCP_SQL = """
WITH
-- Step 1: Join career_outcomes to crosswalk via 4-digit CIP prefix
-- INNER JOIN: programs without crosswalk match are excluded
joined AS (
    SELECT
        co.unitid,
        co.institution_name,
        co.cipcode,
        co.program_name,
        co.cip_family,
        co.cip_family_name,
        xw.soc_code,
        -- Occupation title: prefer BLS, fallback to O*NET, then crosswalk, then 'Unknown'
        COALESCE(op.occupation_title, onet.primary_title, xw.soc_title, 'Unknown')
            AS occupation_title,
        op.soc_major_group_name,
        -- Program context (from career_outcomes)
        co.earnings_1yr_median,
        co.earnings_1yr_p25,
        co.earnings_1yr_p75,
        co.debt_median,
        co.debt_to_earnings_annual,
        co.confidence_tier AS confidence_tier_program,
        co.cip_family_earnings_rank,
        -- Cost-based ROI provenance + institution-level cost fields.
        -- These carry through from consumable.career_outcomes so the
        -- backend can drive cost-based stat_roi + financing-aware
        -- boss_loans_score without refetching from raw Silver.
        co.roi_cost_basis,
        co.net_price_annual,
        co.cost_of_attendance_annual,
        co.institution_control,
        co.net_price_4yr,
        co.tuition_in_state,
        co.tuition_out_of_state,
        co.room_board_on_campus,
        -- Occupation context (from occupation_profiles)
        op.median_annual_wage,
        op.wage_percentile_overall,
        op.wage_percentile_education_tier,
        op.growth_category,
        op.employment_current,
        op.education_level_name,
        op.grw_score_rounded,
        op.market_score_rounded,
        -- O*NET context
        onet.hmn_score_rounded,
        onet.burnout_score_rounded,
        onet.top_5_activities,
        onet.top_human_activities,
        onet.burnout_drivers,
        onet.time_pressure,
        onet.work_hours,
        -- Join flags for match_quality derivation
        CASE WHEN op.soc_code IS NOT NULL THEN TRUE ELSE FALSE END AS has_bls,
        CASE WHEN onet.bls_soc_code IS NOT NULL THEN TRUE ELSE FALSE END AS has_onet,
        -- Count non-null stats for dedup preference (more non-nulls = better row)
        (CASE WHEN op.grw_score_rounded IS NOT NULL THEN 1 ELSE 0 END
         + CASE WHEN onet.hmn_score_rounded IS NOT NULL THEN 1 ELSE 0 END
         + CASE WHEN op.median_annual_wage IS NOT NULL THEN 1 ELSE 0 END
         + CASE WHEN onet.burnout_score_rounded IS NOT NULL THEN 1 ELSE 0 END
         + CASE WHEN op.market_score_rounded IS NOT NULL THEN 1 ELSE 0 END
        ) AS stat_richness
    FROM career_outcomes co
    INNER JOIN crosswalk xw
        ON co.cipcode = LEFT(xw.cipcode, 5)
    LEFT JOIN occupation_profiles op
        ON xw.soc_code = op.soc_code
    LEFT JOIN onet_work_profiles onet
        ON xw.soc_code = onet.bls_soc_code
),

-- Step 2: Dedup on grain (unitid, cipcode, soc_code)
-- Keep row with most non-null stat values
ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY unitid, cipcode, soc_code
            ORDER BY stat_richness DESC
        ) AS rn
    FROM joined
)

SELECT * EXCLUDE (rn, stat_richness)
FROM ranked
WHERE rn = 1
ORDER BY cip_family ASC, unitid ASC, cipcode ASC, soc_code ASC
"""


def derive_pcp_rows(
    career_outcomes_rows: list[dict],
    crosswalk_rows: list[dict],
    occupation_profiles_rows: list[dict],
    onet_work_profiles_rows: list[dict],
    ai_exposure_rows: list[dict] | None = None,
) -> list[dict]:
    """Join and derive program_career_paths rows using DuckDB.

    Returns a list of dicts ready for stat computation, grain-id, and promotion.
    """
    import pyarrow as pa

    if not career_outcomes_rows:
        return []

    # Register all tables in DuckDB
    co_table = pa.Table.from_pylist(career_outcomes_rows)
    xw_table = pa.Table.from_pylist(crosswalk_rows)

    # Handle empty occupation/onet tables gracefully
    if occupation_profiles_rows:
        op_table = pa.Table.from_pylist(occupation_profiles_rows)
    else:
        op_table = pa.table({
            "soc_code": pa.array([], type=pa.string()),
            "occupation_title": pa.array([], type=pa.string()),
            "soc_major_group_name": pa.array([], type=pa.string()),
            "median_annual_wage": pa.array([], type=pa.float64()),
            "wage_percentile_overall": pa.array([], type=pa.float64()),
            "wage_percentile_education_tier": pa.array([], type=pa.float64()),
            "growth_category": pa.array([], type=pa.string()),
            "employment_current": pa.array([], type=pa.int64()),
            "education_level_name": pa.array([], type=pa.string()),
            "grw_score_rounded": pa.array([], type=pa.int32()),
            "market_score_rounded": pa.array([], type=pa.int32()),
        })

    if onet_work_profiles_rows:
        onet_table = pa.Table.from_pylist(onet_work_profiles_rows)
    else:
        onet_table = pa.table({
            "bls_soc_code": pa.array([], type=pa.string()),
            "primary_title": pa.array([], type=pa.string()),
            "hmn_score_rounded": pa.array([], type=pa.int32()),
            "burnout_score_rounded": pa.array([], type=pa.int32()),
            "top_5_activities": pa.array([], type=pa.string()),
            "top_human_activities": pa.array([], type=pa.string()),
            "burnout_drivers": pa.array([], type=pa.string()),
            "time_pressure": pa.array([], type=pa.float64()),
            "work_hours": pa.array([], type=pa.float64()),
        })

    con = duckdb.connect()
    con.register("career_outcomes", co_table)
    con.register("crosswalk", xw_table)
    con.register("occupation_profiles", op_table)
    con.register("onet_work_profiles", onet_table)

    rel = con.sql(PCP_SQL)
    col_names = [desc[0] for desc in rel.description]
    rows = rel.fetchall()
    con.close()

    # Build AI exposure lookup keyed by soc_code
    ai_by_soc: dict[str, dict] = {}
    if ai_exposure_rows:
        ai_by_soc = {r["soc_code"]: r for r in ai_exposure_rows if r.get("soc_code")}

    # Post-process: compute stats and quality fields in Python
    gold_rows = []
    for row_tuple in rows:
        row = dict(zip(col_names, row_tuple))

        # AI exposure lookup for this row's SOC code
        ai_data = ai_by_soc.get(row.get("soc_code"), {})

        # Pentagon stats
        stat_ern = compute_stat_ern(
            row.pop("cip_family_earnings_rank", None),
            row.pop("wage_percentile_overall", None),
        )
        stat_roi = compute_stat_roi(row.get("debt_to_earnings_annual"))
        stat_grw = row.get("grw_score_rounded")
        stat_hmn = row.get("hmn_score_rounded")
        stat_res = ai_data.get("stat_res")  # From ai_exposure lookup, None if no match

        row["stat_ern"] = stat_ern
        row["stat_roi"] = stat_roi
        row["stat_res"] = stat_res
        row["stat_grw"] = stat_grw
        row["stat_hmn"] = stat_hmn

        # Boss scores
        row["boss_ai_score"] = ai_data.get("boss_ai_score")  # From ai_exposure lookup
        # Option B composite provenance threaded through to program_career_paths
        # so the backend receives velocity_label / composite_method / adoption
        # share without a second ai_exposure lookup per row.
        row["ai_adoption_share"] = ai_data.get("ai_adoption_share")
        row["velocity_label"] = ai_data.get("velocity_label")
        row["composite_method"] = ai_data.get("composite_method")
        row["adoption_percentile"] = ai_data.get("adoption_percentile")
        row["boss_loans_score"] = (11 - stat_roi) if stat_roi is not None else None
        row["boss_market_score"] = row.pop("market_score_rounded", None)
        row["boss_burnout_score"] = row.get("burnout_score_rounded")
        row["boss_ceiling_score"] = compute_boss_ceiling(
            row.pop("wage_percentile_education_tier", None)
        )

        # Remove carried fields not in output schema
        row.pop("grw_score_rounded", None)
        row.pop("burnout_score_rounded", None)

        # Match quality (derived from join flags)
        has_bls = row.pop("has_bls", False)
        has_onet = row.pop("has_onet", False)
        match_quality = derive_match_quality(has_bls, has_onet)
        row["match_quality"] = match_quality

        # Stats available count
        stats = [stat_ern, stat_roi, stat_res, stat_grw, stat_hmn]
        stats_available = sum(1 for s in stats if s is not None)
        row["stats_available_count"] = stats_available

        # Bosses available count
        bosses = [
            row["boss_ai_score"],
            row["boss_loans_score"],
            row["boss_market_score"],
            row["boss_burnout_score"],
            row["boss_ceiling_score"],
        ]
        bosses_available = sum(1 for b in bosses if b is not None)
        row["bosses_available_count"] = bosses_available

        # Overall confidence
        row["overall_confidence"] = derive_overall_confidence(
            stats_available, match_quality
        )

        gold_rows.append(row)

    return gold_rows


def add_pcp_record_ids(
    gold_rows: list[dict], promoted_at: datetime.datetime
) -> list[dict]:
    """Add record_id and promoted_at to program_career_paths rows."""
    for row in gold_rows:
        row["record_id"] = compute_grain_id(row, PCP_GRAIN_FIELDS, prefix=PCP_GRAIN_PREFIX)
        row["promoted_at"] = promoted_at
    return gold_rows


# ---------------------------------------------------------------------------
# Table 2: career_branches derivation
# ---------------------------------------------------------------------------


def derive_br_rows(
    transition_rows: list[dict],
    occupation_profiles_rows: list[dict],
    onet_work_profiles_rows: list[dict],
    ai_exposure_rows: list[dict] | None = None,
    onet_experience_rows: list[dict] | None = None,
) -> list[dict]:
    """Enrich career transitions with source/target stats and compute deltas.

    When ``onet_experience_rows`` (from ``base.onet_experience_profiles``) is
    supplied, the 4 additive experience columns (spec:
    ``onet-experience-requirements`` §Zone 3, 2026-04-16) are populated on
    each branch via a LEFT-JOIN-style lookup on ``bls_soc_code``. The delta
    NULL-propagates when either side is NULL — we do NOT coalesce to 0.

    When ``onet_experience_rows`` is None or empty (backward-compat), all 4
    experience columns come out None.

    Returns a list of dicts ready for grain-id computation and promotion.
    """
    if not transition_rows:
        return []

    # Build lookup dicts for BLS and O*NET
    op_by_soc: dict[str, dict] = {
        r["soc_code"]: r for r in occupation_profiles_rows
    }
    onet_by_soc: dict[str, dict] = {
        r["bls_soc_code"]: r for r in onet_work_profiles_rows
    }

    # Build AI exposure lookup keyed by soc_code
    ai_by_soc: dict[str, dict] = {}
    if ai_exposure_rows:
        ai_by_soc = {r["soc_code"]: r for r in ai_exposure_rows if r.get("soc_code")}

    # Build experience lookup keyed by bls_soc_code (Silver grain).
    # Silver table is base.onet_experience_profiles (~765 rows).
    exp_by_soc: dict[str, dict] = {}
    if onet_experience_rows:
        exp_by_soc = {
            r["bls_soc_code"]: r
            for r in onet_experience_rows
            if r.get("bls_soc_code")
        }

    gold_rows: list[dict] = []
    for tr in transition_rows:
        soc = tr["bls_soc_code"]
        related_soc = tr["related_bls_soc_code"]

        # Source stats
        src_op = op_by_soc.get(soc, {})
        src_onet = onet_by_soc.get(soc, {})
        source_grw = src_op.get("grw_score_rounded")
        source_hmn = src_onet.get("hmn_score_rounded")
        source_burnout = src_onet.get("burnout_score_rounded")
        source_wage = src_op.get("median_annual_wage")

        # Related stats
        rel_op = op_by_soc.get(related_soc, {})
        rel_onet = onet_by_soc.get(related_soc, {})
        related_grw = rel_op.get("grw_score_rounded")
        related_hmn = rel_onet.get("hmn_score_rounded")
        related_burnout = rel_onet.get("burnout_score_rounded")
        related_wage = rel_op.get("median_annual_wage")

        # AI exposure stats (source and related)
        src_ai = ai_by_soc.get(soc, {})
        rel_ai = ai_by_soc.get(related_soc, {})
        source_res = src_ai.get("stat_res")
        source_ai_boss = src_ai.get("boss_ai_score")
        related_res = rel_ai.get("stat_res")
        related_ai_boss = rel_ai.get("boss_ai_score")

        # Experience stats (source and related) — spec §Zone 3.
        # LEFT JOIN on bls_soc_code; missing rows yield all-None fields,
        # which propagates into experience_delta_years as NULL.
        src_exp = exp_by_soc.get(soc, {})
        rel_exp = exp_by_soc.get(related_soc, {})
        source_experience_years = src_exp.get("experience_years_typical")
        related_experience_years = rel_exp.get("experience_years_typical")
        related_experience_tier = rel_exp.get("experience_tier")
        if (
            source_experience_years is not None
            and related_experience_years is not None
        ):
            experience_delta_years: float | None = (
                related_experience_years - source_experience_years
            )
        else:
            experience_delta_years = None

        # Deltas (null if either side null)
        grw_delta = (related_grw - source_grw) if (related_grw is not None and source_grw is not None) else None
        hmn_delta = (related_hmn - source_hmn) if (related_hmn is not None and source_hmn is not None) else None
        burnout_delta = (related_burnout - source_burnout) if (related_burnout is not None and source_burnout is not None) else None
        wage_delta = (related_wage - source_wage) if (related_wage is not None and source_wage is not None) else None
        res_delta = (related_res - source_res) if (related_res is not None and source_res is not None) else None
        ai_boss_delta = (related_ai_boss - source_ai_boss) if (related_ai_boss is not None and source_ai_boss is not None) else None

        # branch_has_full_data: True if related has both BLS and O*NET data
        branch_has_full_data = (related_grw is not None and related_hmn is not None)

        row = {
            "soc_code": soc,
            "source_title": tr["source_title"],
            "related_soc_code": related_soc,
            "related_title": tr["related_title"],
            "best_index": tr["best_index"],
            "relatedness_tier": tr["relatedness_tier"],
            "is_primary": tr["is_primary"],
            "source_grw": source_grw,
            "source_hmn": source_hmn,
            "source_burnout": source_burnout,
            "source_wage": source_wage,
            "related_grw": related_grw,
            "related_hmn": related_hmn,
            "related_burnout": related_burnout,
            "related_wage": related_wage,
            "related_growth_category": rel_op.get("growth_category"),
            "related_education_level": rel_op.get("education_level_name"),
            "grw_delta": grw_delta,
            "hmn_delta": hmn_delta,
            "burnout_delta": burnout_delta,
            "wage_delta": wage_delta,
            "branch_has_full_data": branch_has_full_data,
            "source_res": source_res,
            "source_ai_boss": source_ai_boss,
            "related_res": related_res,
            "related_ai_boss": related_ai_boss,
            "res_delta": res_delta,
            "ai_boss_delta": ai_boss_delta,
            "related_experience_years": related_experience_years,
            "related_experience_tier": related_experience_tier,
            "source_experience_years": source_experience_years,
            "experience_delta_years": experience_delta_years,
        }
        gold_rows.append(row)

    return gold_rows


def add_br_record_ids(
    gold_rows: list[dict], promoted_at: datetime.datetime
) -> list[dict]:
    """Add record_id and promoted_at to career_branches rows."""
    for row in gold_rows:
        row["record_id"] = compute_grain_id(row, BR_GRAIN_FIELDS, prefix=BR_GRAIN_PREFIX)
        row["promoted_at"] = promoted_at
    return gold_rows


# ---------------------------------------------------------------------------
# Helpers for reading Iceberg tables
# ---------------------------------------------------------------------------


def _read_table(catalog, table_name: str) -> list[dict]:
    """Read an Iceberg table into a list of dicts."""
    tbl = catalog.load_table(table_name)
    arrow = tbl.scan().to_arrow()
    con = duckdb.connect()
    rows_raw = con.sql("SELECT * FROM arrow").fetchall()
    cols = [field.name for field in tbl.schema().fields]
    con.close()
    return [dict(zip(cols, r)) for r in rows_raw]


# ---------------------------------------------------------------------------
# Main transform
# ---------------------------------------------------------------------------


def _overwrite_table(table: Table, records: list[dict]) -> int:
    """Overwrite an Iceberg table with new data. Returns the new snapshot ID.

    Used for backfills where the grain is unchanged but column values are updated.
    PyIceberg's overwrite() replaces all data in the table.
    """
    import pyarrow as pa
    from pyiceberg.io.pyarrow import schema_to_pyarrow
    from pyiceberg.types import DateType

    iceberg_schema = table.schema()
    date_fields = {f.name for f in iceberg_schema.fields if isinstance(f.field_type, DateType)}
    columns = {}
    for field in iceberg_schema.fields:
        values = [r.get(field.name) for r in records]
        if field.name in date_fields:
            values = [datetime.date.fromisoformat(v) if isinstance(v, str) else v for v in values]
        columns[field.name] = values

    arrow_schema = schema_to_pyarrow(iceberg_schema)
    arrow_table = pa.table(columns, schema=arrow_schema)
    table.overwrite(arrow_table)
    table.refresh()
    return list(table.snapshots())[-1].snapshot_id


def transform(
    project_dir: str | Path | None = None,
    overwrite: bool = False,
) -> dict:
    """Run the Gold zone transformation for both FutureProof Engine tables.

    Table 1: consumable.program_career_paths (cross-source join)
    Table 2: consumable.career_branches (transition enrichment)

    Args:
        project_dir: Root project directory.
        overwrite: If True, overwrite existing data instead of dedup-append.
            Use for backfills where column values change but the grain is the same.

    Returns summary dict with row counts for both tables.
    """
    project_dir = Path(project_dir or ".").resolve()

    silver_warehouse = project_dir / "data" / "silver" / "iceberg_warehouse"
    catalog_path = project_dir / "data" / "catalog" / "catalog.db"
    gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"

    # -----------------------------------------------------------------------
    # Read source tables
    # -----------------------------------------------------------------------
    logger.info("Reading source tables...")
    silver_catalog = get_catalog(silver_warehouse, catalog_path)
    gold_catalog = get_catalog(gold_warehouse, catalog_path)

    crosswalk_rows = _read_table(silver_catalog, "base.cip_soc_crosswalk")
    career_outcomes_rows = _read_table(gold_catalog, "consumable.career_outcomes")
    occupation_profiles_rows = _read_table(gold_catalog, "consumable.occupation_profiles")
    onet_work_profiles_rows = _read_table(gold_catalog, "consumable.onet_work_profiles")
    career_transitions_rows = _read_table(gold_catalog, "consumable.career_transitions")

    # AI exposure data (optional — graceful degradation if not yet promoted)
    try:
        ai_exposure_rows = _read_table(gold_catalog, "consumable.ai_exposure")
        logger.info("Read %d ai_exposure rows", len(ai_exposure_rows))
    except Exception:
        ai_exposure_rows = []
        logger.info("consumable.ai_exposure not available — AI stats will be null")

    # O*NET experience profiles (optional — graceful degradation if the Silver
    # table from the onet-experience-requirements spec has not yet been
    # materialized). Powers the 4 additive experience columns on
    # consumable.career_branches per §Zone 3.
    try:
        onet_experience_rows = _read_table(
            silver_catalog, "base.onet_experience_profiles"
        )
        logger.info(
            "Read %d onet_experience_profiles rows", len(onet_experience_rows)
        )
    except Exception:
        onet_experience_rows = []
        logger.info(
            "base.onet_experience_profiles not available — "
            "experience columns will be null"
        )

    logger.info(
        "Read: %d career_outcomes, %d crosswalk, %d occupation_profiles, "
        "%d onet_work_profiles, %d career_transitions, %d ai_exposure, "
        "%d onet_experience_profiles",
        len(career_outcomes_rows),
        len(crosswalk_rows),
        len(occupation_profiles_rows),
        len(onet_work_profiles_rows),
        len(career_transitions_rows),
        len(ai_exposure_rows),
        len(onet_experience_rows),
    )

    # -----------------------------------------------------------------------
    # Table 1: program_career_paths
    # -----------------------------------------------------------------------
    logger.info("Deriving program_career_paths...")
    pcp_rows = derive_pcp_rows(
        career_outcomes_rows,
        crosswalk_rows,
        occupation_profiles_rows,
        onet_work_profiles_rows,
        ai_exposure_rows=ai_exposure_rows,
    )
    logger.info("Derived %d program_career_paths rows", len(pcp_rows))

    promoted_at = datetime.datetime.now(tz=datetime.timezone.utc)
    add_pcp_record_ids(pcp_rows, promoted_at)

    logger.info("Promoting to consumable.program_career_paths...")
    pcp_table = get_or_create_table(
        gold_catalog, "consumable", "program_career_paths", get_pcp_schema()
    )
    # Schema evolution: append Option B composite provenance fields (S4 v4)
    # if the table was created pre-v4. Mirrors the career_branches pattern
    # below. Idempotent — no-op when the new fields already exist.
    existing_pcp_fields = {f.name for f in pcp_table.schema().fields}
    target_pcp_schema = get_pcp_schema()
    new_pcp_fields = [
        f for f in target_pcp_schema.fields if f.name not in existing_pcp_fields
    ]
    if new_pcp_fields:
        with pcp_table.update_schema() as update:
            for field in new_pcp_fields:
                update.add_column(
                    field.name, field.field_type, doc=None, required=field.required
                )
        logger.info(
            "Evolved program_career_paths schema: added %d fields (%s)",
            len(new_pcp_fields),
            [f.name for f in new_pcp_fields],
        )
    if overwrite:
        logger.info("Overwrite mode: replacing all data in program_career_paths")
        snapshot_id = _overwrite_table(pcp_table, pcp_rows)
        pcp_result = {"promoted": len(pcp_rows), "skipped": 0, "snapshot_id": snapshot_id}
    else:
        pcp_result = promote(
            pcp_table,
            pcp_rows,
            id_field="record_id",
            spec_name=SPEC_NAME,
            agent_name="@primary-agent",
        )
    logger.info(
        "Table 1 promote: %d promoted, %d skipped",
        pcp_result["promoted"],
        pcp_result["skipped"],
    )

    # -----------------------------------------------------------------------
    # Table 2: career_branches
    # -----------------------------------------------------------------------
    logger.info("Deriving career_branches...")
    br_rows = derive_br_rows(
        career_transitions_rows,
        occupation_profiles_rows,
        onet_work_profiles_rows,
        ai_exposure_rows=ai_exposure_rows,
        onet_experience_rows=onet_experience_rows,
    )
    logger.info("Derived %d career_branches rows", len(br_rows))

    add_br_record_ids(br_rows, promoted_at)

    logger.info("Promoting to consumable.career_branches...")
    br_table = get_or_create_table(
        gold_catalog, "consumable", "career_branches", get_br_schema()
    )
    # Schema evolution: add new AI columns if they don't exist yet
    existing_field_names = {f.name for f in br_table.schema().fields}
    target_schema = get_br_schema()
    new_fields = [f for f in target_schema.fields if f.name not in existing_field_names]
    if new_fields:
        with br_table.update_schema() as update:
            for field in new_fields:
                update.add_column(field.name, field.field_type, doc=None, required=field.required)
        logger.info("Evolved career_branches schema: added %d fields (%s)",
                     len(new_fields), [f.name for f in new_fields])

    if overwrite:
        logger.info("Overwrite mode: replacing all data in career_branches")
        snapshot_id = _overwrite_table(br_table, br_rows)
        br_result = {"promoted": len(br_rows), "skipped": 0, "snapshot_id": snapshot_id}
    else:
        br_result = promote(
            br_table,
            br_rows,
            id_field="record_id",
            spec_name=SPEC_NAME,
            agent_name="@primary-agent",
        )
    logger.info(
        "Table 2 promote: %d promoted, %d skipped",
        br_result["promoted"],
        br_result["skipped"],
    )

    return {
        "table_1": {
            "name": "consumable.program_career_paths",
            "rows_derived": len(pcp_rows),
            "promoted": pcp_result["promoted"],
            "skipped_dedup": pcp_result["skipped"],
            "snapshot_id": pcp_result.get("snapshot_id"),
        },
        "table_2": {
            "name": "consumable.career_branches",
            "rows_derived": len(br_rows),
            "promoted": br_result["promoted"],
            "skipped_dedup": br_result["skipped"],
            "snapshot_id": br_result.get("snapshot_id"),
        },
    }


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    do_overwrite = "--overwrite" in sys.argv
    result = transform(overwrite=do_overwrite)
    print(f"FutureProof Engine transform complete:")
    print(f"  Table 1: {result['table_1']}")
    print(f"  Table 2: {result['table_2']}")
