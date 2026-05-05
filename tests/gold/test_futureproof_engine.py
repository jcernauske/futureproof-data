"""Tests for the Gold zone FutureProof Engine transformer.

Covers both Table 1 (consumable.program_career_paths) and Table 2
(consumable.career_branches). Tests stat derivations, join logic,
dedup, match quality, confidence tiers, and edge cases.

Minimum 15 tests required for Consumable zone.
"""

import datetime

import pytest

from gold.futureproof_engine import (
    BR_GRAIN_FIELDS,
    BR_GRAIN_PREFIX,
    PCP_GRAIN_FIELDS,
    PCP_GRAIN_PREFIX,
    ROI_MULTIPLIER_THRESHOLDS,
    add_br_record_ids,
    add_pcp_record_ids,
    compute_boss_ceiling,
    compute_stat_ern,
    compute_stat_roi,
    compute_stat_roi_from_multiplier,
    derive_br_rows,
    derive_match_quality,
    derive_overall_confidence,
    derive_pcp_rows,
    get_br_schema,
    get_pcp_schema,
)
from brightsmith.infra.grain import compute_grain_id


# ---------------------------------------------------------------------------
# Helpers: Table 1
# ---------------------------------------------------------------------------


def _make_career_outcome(
    unitid=151801,
    institution_name="Indiana State University",
    cipcode="52.02",
    program_name="Business Administration",
    cip_family="52",
    cip_family_name="Business, Management, Marketing",
    earnings_1yr_median=42000.0,
    earnings_1yr_p25=35000.0,
    earnings_1yr_p75=55000.0,
    debt_median=27000.0,
    debt_to_earnings_annual=0.643,
    confidence_tier="medium",
    cip_family_earnings_rank=0.45,
    roi_cost_basis="debt_median",
    net_price_annual=None,
    cost_of_attendance_annual=None,
    institution_control=None,
    net_price_4yr=None,
    tuition_in_state=None,
    tuition_out_of_state=None,
    room_board_on_campus=None,
    state_abbr="IN",
    lifetime_earnings_15yr=None,
    roi_raw_multiplier=None,
    roi_multiplier_basis="none",
):
    # ROI Net Lifetime Value (spec roi-net-lifetime-value, 2026-05-04):
    # When the caller doesn't specify the new columns, derive them from
    # earnings + cost basis so PCP_SQL's SELECT picks up real values.
    if lifetime_earnings_15yr is None and earnings_1yr_median is not None:
        lifetime_earnings_15yr = round(earnings_1yr_median * 18.5989, 2)
    if roi_raw_multiplier is None and lifetime_earnings_15yr is not None:
        cost_basis: float | None
        if cost_of_attendance_annual and cost_of_attendance_annual > 0:
            cost_basis = cost_of_attendance_annual * 4.0
            roi_multiplier_basis = "sticker_4yr"
        elif net_price_4yr and net_price_4yr > 0:
            cost_basis = net_price_4yr
            roi_multiplier_basis = "net_price_4yr"
        else:
            cost_basis = None
        if cost_basis:
            roi_raw_multiplier = round(lifetime_earnings_15yr / cost_basis, 4)
    return {
        "unitid": unitid,
        "institution_name": institution_name,
        "cipcode": cipcode,
        "program_name": program_name,
        "cip_family": cip_family,
        "cip_family_name": cip_family_name,
        "earnings_1yr_median": earnings_1yr_median,
        "earnings_1yr_p25": earnings_1yr_p25,
        "earnings_1yr_p75": earnings_1yr_p75,
        "debt_median": debt_median,
        "debt_to_earnings_annual": debt_to_earnings_annual,
        "confidence_tier": confidence_tier,
        "cip_family_earnings_rank": cip_family_earnings_rank,
        # Cost-based ROI provenance + institution cost fields (added by
        # plan ~/.claude/plans/why-are-we-still-jaunty-curry.md). All
        # optional — fixtures that don't exercise these paths pass the
        # defaults (debt_median basis, no institution cost columns).
        "roi_cost_basis": roi_cost_basis,
        "net_price_annual": net_price_annual,
        "cost_of_attendance_annual": cost_of_attendance_annual,
        "institution_control": institution_control,
        "net_price_4yr": net_price_4yr,
        "tuition_in_state": tuition_in_state,
        "tuition_out_of_state": tuition_out_of_state,
        "room_board_on_campus": room_board_on_campus,
        "state_abbr": state_abbr,
        # ROI Net Lifetime Value (spec roi-net-lifetime-value).
        "lifetime_earnings_15yr": lifetime_earnings_15yr,
        "roi_raw_multiplier": roi_raw_multiplier,
        "roi_multiplier_basis": roi_multiplier_basis,
    }


def _make_crosswalk(cipcode="52.0201", soc_code="13-2051", soc_title="Financial Analysts"):
    return {
        "cipcode": cipcode,
        "soc_code": soc_code,
        "soc_title": soc_title,
    }


def _make_occupation_profile(
    soc_code="13-2051",
    occupation_title="Financial and Investment Analysts",
    soc_major_group_name="Business and Financial Operations",
    median_annual_wage=95080.0,
    wage_percentile_overall=0.75,
    wage_percentile_education_tier=0.60,
    growth_category="growing",
    employment_current=328600,
    education_level_name="Bachelor's degree",
    grw_score_rounded=6,
    market_score_rounded=5,
):
    return {
        "soc_code": soc_code,
        "occupation_title": occupation_title,
        "soc_major_group_name": soc_major_group_name,
        "median_annual_wage": median_annual_wage,
        "wage_percentile_overall": wage_percentile_overall,
        "wage_percentile_education_tier": wage_percentile_education_tier,
        "growth_category": growth_category,
        "employment_current": employment_current,
        "education_level_name": education_level_name,
        "grw_score_rounded": grw_score_rounded,
        "market_score_rounded": market_score_rounded,
    }


def _make_onet_profile(
    bls_soc_code="13-2051",
    primary_title="Financial Analysts",
    hmn_score_rounded=4,
    burnout_score_rounded=6,
    top_5_activities='[{"activity":"Analyzing","importance":4.5}]',
    top_human_activities='[{"activity":"Deciding","importance":4.2}]',
    burnout_drivers='[{"element":"Time Pressure","value":0.75}]',
    time_pressure=3.5,
    work_hours=2.1,
):
    return {
        "bls_soc_code": bls_soc_code,
        "primary_title": primary_title,
        "hmn_score_rounded": hmn_score_rounded,
        "burnout_score_rounded": burnout_score_rounded,
        "top_5_activities": top_5_activities,
        "top_human_activities": top_human_activities,
        "burnout_drivers": burnout_drivers,
        "time_pressure": time_pressure,
        "work_hours": work_hours,
    }


def _simple_pcp_derive(**co_overrides):
    """Shorthand: derive one program_career_paths row with defaults."""
    co = _make_career_outcome(**co_overrides)
    xw = [_make_crosswalk()]
    op = [_make_occupation_profile()]
    onet = [_make_onet_profile()]
    return derive_pcp_rows([co], xw, op, onet)


# ---------------------------------------------------------------------------
# Helpers: Table 2
# ---------------------------------------------------------------------------


def _make_transition(
    bls_soc_code="15-1252",
    related_bls_soc_code="15-1256",
    source_title="Software Developers",
    related_title="Software Quality Assurance Analysts",
    best_index=1,
    relatedness_tier="Primary-Short",
    is_primary=True,
):
    return {
        "bls_soc_code": bls_soc_code,
        "related_bls_soc_code": related_bls_soc_code,
        "source_title": source_title,
        "related_title": related_title,
        "best_index": best_index,
        "relatedness_tier": relatedness_tier,
        "is_primary": is_primary,
    }


# =========================================================================
# Table 1 Tests: stat_ern derivation
# =========================================================================


class TestStatErn:
    """Tests for Earning Power stat derivation."""

    def test_ern_basic_computation(self):
        """stat_ern = ROUND(1 + 9 * (0.6 * rank + 0.4 * percentile))."""
        result = compute_stat_ern(0.45, 0.75)
        # raw = 0.6*0.45 + 0.4*0.75 = 0.27 + 0.30 = 0.57
        # ern = ROUND(1 + 9*0.57) = ROUND(6.13) = 6
        assert result == 6

    def test_ern_max_inputs(self):
        """Both inputs at 1.0 should produce 10."""
        assert compute_stat_ern(1.0, 1.0) == 10

    def test_ern_min_inputs(self):
        """Both inputs at 0.0 should produce 1."""
        assert compute_stat_ern(0.0, 0.0) == 1

    def test_ern_null_when_earnings_rank_null(self):
        """stat_ern is null when cip_family_earnings_rank is null."""
        assert compute_stat_ern(None, 0.75) is None

    def test_ern_null_when_wage_percentile_null(self):
        """stat_ern is null when wage_percentile_overall is null."""
        assert compute_stat_ern(0.45, None) is None


# =========================================================================
# Table 1 Tests: stat_roi derivation
# =========================================================================


class TestStatRoi:
    """Tests for Return on Investment stat derivation.

    Breakpoints (tightened to punish DTE >= 1.0):
        DTE <= 0.25       -> 10
        0.25 -> 0.50      -> 10 -> 9
        0.50 -> 0.75      ->  9 -> 7
        0.75 -> 1.00      ->  7 -> 5
        1.00 -> 1.50      ->  5 -> 3
        1.50 -> 2.50      ->  3 -> 1
        DTE >= 2.50       -> 1
    """

    def test_roi_excellent(self):
        """DTE <= 0.25 should produce ROI = 10."""
        assert compute_stat_roi(0.10) == 10
        assert compute_stat_roi(0.25) == 10

    def test_roi_catastrophic(self):
        """DTE >= 2.5 should produce ROI = 1."""
        assert compute_stat_roi(2.5) == 1
        assert compute_stat_roi(3.0) == 1
        assert compute_stat_roi(5.0) == 1

    def test_roi_good_band(self):
        """DTE 0.50 -> 0.75 interpolates 9 -> 7."""
        # midpoint DTE 0.625: fraction=0.5, roi = 9 - 0.5*2 = 8
        assert compute_stat_roi(0.625) == 8
        assert compute_stat_roi(0.50) == 9
        assert compute_stat_roi(0.75) == 7

    def test_roi_mediocre_band(self):
        """DTE 0.75 -> 1.00 interpolates 7 -> 5."""
        # midpoint DTE 0.875: fraction=0.5, roi = 7 - 0.5*2 = 6
        assert compute_stat_roi(0.875) == 6

    def test_roi_bad_band_dte_one(self):
        """DTE >= 1.0 must cap at ROI <= 5 (spec: debt exceeds earnings)."""
        assert compute_stat_roi(1.00) == 5
        # DTE 1.244 (Millikin Drama): fraction=(1.244-1.0)/0.5=0.488
        # roi = 5 - 0.488*2 = 4.024 -> 4
        assert compute_stat_roi(1.244) == 4
        # DTE 1.25: fraction=0.5, roi = 5 - 1 = 4
        assert compute_stat_roi(1.25) == 4
        # DTE 1.5 boundary: lands at 3 via next band start
        assert compute_stat_roi(1.5) == 3

    def test_roi_terrible_band(self):
        """DTE 1.5 -> 2.5 interpolates 3 -> 1."""
        # midpoint DTE 2.0: fraction=0.5, roi = 3 - 0.5*2 = 2
        assert compute_stat_roi(2.0) == 2

    def test_roi_null_when_dte_null(self):
        """stat_roi is null when debt_to_earnings_annual is null."""
        assert compute_stat_roi(None) is None


# =========================================================================
# Table 1 Tests: boss scores
# =========================================================================


class TestBossScores:
    """Tests for boss fight score derivations."""

    def test_boss_loans_inverse_of_roi(self):
        """Gold-precomputed boss_loans_score = 11 - stat_roi (placeholder
        only; the backend recomputes financing-aware via _derive_loans_boss
        per spec roi-net-lifetime-value Decision #5)."""
        # Cheap public + high earnings → multiplier saturates at 10 → boss 1.
        rows = _simple_pcp_derive(
            earnings_1yr_median=80_000.0,
            cost_of_attendance_annual=10_000.0,  # sticker_4yr = 40_000
        )
        assert rows[0]["stat_roi"] == 10
        assert rows[0]["boss_loans_score"] == 1

    def test_boss_loans_null_when_roi_null(self):
        """boss_loans_score is null when stat_roi is null (no roi_raw_multiplier)."""
        rows = _simple_pcp_derive(
            earnings_1yr_median=None,
            cost_of_attendance_annual=None,
            net_price_4yr=None,
        )
        assert rows[0]["stat_roi"] is None
        assert rows[0]["boss_loans_score"] is None

    def test_boss_ceiling_basic(self):
        """boss_ceiling = ROUND(10 - 9 * wage_pct_edu_tier)."""
        # wage_percentile_education_tier = 0.60
        # ceiling = ROUND(10 - 9*0.60) = ROUND(4.6) = 5
        result = compute_boss_ceiling(0.60)
        assert result == 5

    def test_boss_ceiling_null_when_no_percentile(self):
        """boss_ceiling is null when wage_percentile_education_tier is null."""
        assert compute_boss_ceiling(None) is None

    def test_boss_ai_null_without_ai_exposure(self):
        """boss_ai_score is null when no AI exposure data provided."""
        rows = _simple_pcp_derive()
        assert rows[0]["boss_ai_score"] is None

    def test_stat_res_null_without_ai_exposure(self):
        """stat_res is null when no AI exposure data provided."""
        rows = _simple_pcp_derive()
        assert rows[0]["stat_res"] is None


# =========================================================================
# Table 1 Tests: match quality and confidence
# =========================================================================


class TestMatchQualityAndConfidence:
    """Tests for match_quality and overall_confidence derivation."""

    def test_full_match_quality(self):
        """Both BLS and O*NET joined -> 'full'."""
        assert derive_match_quality(True, True) == "full"

    def test_partial_no_onet(self):
        """BLS joined, O*NET missing -> 'partial_no_onet'."""
        assert derive_match_quality(True, False) == "partial_no_onet"

    def test_partial_no_bls(self):
        """O*NET joined, BLS missing -> 'partial_no_bls'."""
        assert derive_match_quality(False, True) == "partial_no_bls"

    def test_scorecard_only(self):
        """Neither BLS nor O*NET -> 'scorecard_only'."""
        assert derive_match_quality(False, False) == "scorecard_only"

    def test_confidence_high(self):
        """stats >= 4 AND match = 'full' -> 'high'."""
        assert derive_overall_confidence(4, "full") == "high"

    def test_confidence_medium(self):
        """stats >= 2 AND match contains 'partial' -> 'medium'."""
        assert derive_overall_confidence(3, "partial_no_onet") == "medium"
        assert derive_overall_confidence(2, "partial_no_bls") == "medium"

    def test_confidence_low_insufficient_stats(self):
        """stats < 2 -> 'low' regardless of match."""
        assert derive_overall_confidence(1, "full") == "low"

    def test_confidence_low_scorecard_only(self):
        """scorecard_only -> 'low' regardless of stats."""
        assert derive_overall_confidence(4, "scorecard_only") == "low"


# =========================================================================
# Table 1 Tests: CIP prefix join and dedup
# =========================================================================


class TestCipPrefixJoinAndDedup:
    """Tests for the CIP prefix matching join and dedup logic."""

    def test_cip_prefix_join_matches(self):
        """Scorecard CIP 52.02 should match crosswalk CIP 52.0201."""
        rows = _simple_pcp_derive()
        assert len(rows) == 1
        assert rows[0]["cipcode"] == "52.02"
        assert rows[0]["soc_code"] == "13-2051"

    def test_cip_prefix_fan_out(self):
        """One Scorecard CIP matching multiple crosswalk entries produces multiple rows."""
        co = [_make_career_outcome()]
        xw = [
            _make_crosswalk("52.0201", "13-2051", "Financial Analysts"),
            _make_crosswalk("52.0203", "11-1021", "General Managers"),
        ]
        op = [
            _make_occupation_profile("13-2051"),
            _make_occupation_profile("11-1021", occupation_title="General and Operations Managers"),
        ]
        onet = [
            _make_onet_profile("13-2051"),
            _make_onet_profile("11-1021", primary_title="General Managers"),
        ]
        rows = derive_pcp_rows(co, xw, op, onet)
        assert len(rows) == 2
        soc_codes = {r["soc_code"] for r in rows}
        assert soc_codes == {"13-2051", "11-1021"}

    def test_dedup_same_soc_via_multiple_cips(self):
        """Same SOC from multiple 6-digit CIPs should be deduped to one row."""
        co = [_make_career_outcome()]
        # Both 52.0201 and 52.0202 map to the same SOC 13-2051
        xw = [
            _make_crosswalk("52.0201", "13-2051", "Financial Analysts"),
            _make_crosswalk("52.0202", "13-2051", "Financial Analysts"),
        ]
        op = [_make_occupation_profile("13-2051")]
        onet = [_make_onet_profile("13-2051")]
        rows = derive_pcp_rows(co, xw, op, onet)
        assert len(rows) == 1

    def test_no_match_excluded(self):
        """Scorecard CIP with no crosswalk match produces no rows."""
        co = [_make_career_outcome(cipcode="99.99")]
        xw = [_make_crosswalk("52.0201", "13-2051")]
        op = [_make_occupation_profile()]
        onet = [_make_onet_profile()]
        rows = derive_pcp_rows(co, xw, op, onet)
        assert len(rows) == 0


# =========================================================================
# Table 1 Tests: occupation title fallback
# =========================================================================


class TestOccupationTitleFallback:
    """Tests for occupation_title sourcing with fallback chain."""

    def test_title_from_bls_preferred(self):
        """BLS occupation_title is preferred source."""
        rows = _simple_pcp_derive()
        assert rows[0]["occupation_title"] == "Financial and Investment Analysts"

    def test_title_fallback_to_onet(self):
        """When BLS not available, falls back to O*NET primary_title."""
        co = [_make_career_outcome()]
        xw = [_make_crosswalk()]
        op = []  # no BLS data
        onet = [_make_onet_profile()]
        rows = derive_pcp_rows(co, xw, op, onet)
        assert rows[0]["occupation_title"] == "Financial Analysts"

    def test_title_fallback_to_crosswalk(self):
        """When neither BLS nor O*NET, falls back to crosswalk soc_title."""
        co = [_make_career_outcome()]
        xw = [_make_crosswalk(soc_title="Financial Analysts (XW)")]
        op = []
        onet = []
        rows = derive_pcp_rows(co, xw, op, onet)
        assert rows[0]["occupation_title"] == "Financial Analysts (XW)"

    def test_title_fallback_to_unknown(self):
        """When no title source, defaults to 'Unknown'."""
        co = [_make_career_outcome()]
        xw = [_make_crosswalk(soc_title=None)]
        op = []
        onet = []
        rows = derive_pcp_rows(co, xw, op, onet)
        assert rows[0]["occupation_title"] == "Unknown"


# =========================================================================
# Table 1 Tests: schema and record IDs
# =========================================================================


class TestPcpSchemaAndRecordIds:
    """Tests for Table 1 schema and record ID generation."""

    def test_schema_has_57_columns(self):
        """PCP physical model has 57 columns. Fields 55-57 are the
        ROI Net Lifetime Value triplet (lifetime_earnings_15yr,
        roi_raw_multiplier, roi_multiplier_basis) added by spec
        roi-net-lifetime-value (2026-05-04).
        """
        schema = get_pcp_schema()
        assert len(schema.fields) == 57

    def test_record_id_deterministic(self):
        """record_id is deterministic for same grain."""
        rows = _simple_pcp_derive()
        promoted_at = datetime.datetime(2026, 4, 9, 12, 0, tzinfo=datetime.timezone.utc)
        add_pcp_record_ids(rows, promoted_at)

        expected = compute_grain_id(
            {"unitid": 151801, "cipcode": "52.02", "soc_code": "13-2051"},
            PCP_GRAIN_FIELDS,
            prefix=PCP_GRAIN_PREFIX,
        )
        assert rows[0]["record_id"] == expected
        assert rows[0]["record_id"].startswith("pcp-")

    def test_stats_available_count(self):
        """stats_available_count counts non-null pentagon stats."""
        # Provide cost basis so the new payback-multiplier ROI is non-null
        # (spec roi-net-lifetime-value).
        rows = _simple_pcp_derive(cost_of_attendance_annual=20_000.0)
        # With full data: stat_ern, stat_roi, stat_grw, stat_hmn are non-null; stat_res is null
        assert rows[0]["stats_available_count"] == 4

    def test_bosses_available_count(self):
        """bosses_available_count counts non-null boss scores."""
        rows = _simple_pcp_derive(cost_of_attendance_annual=20_000.0)
        # boss_loans, boss_market, boss_burnout, boss_ceiling non-null; boss_ai null
        assert rows[0]["bosses_available_count"] == 4


# =========================================================================
# Table 1 Tests: null propagation and edge cases
# =========================================================================


class TestPcpEdgeCases:
    """Edge cases for program_career_paths."""

    def test_empty_career_outcomes_returns_empty(self):
        """Empty career_outcomes produces no rows."""
        rows = derive_pcp_rows([], [_make_crosswalk()], [], [])
        assert rows == []

    def test_null_earnings_propagates(self):
        """Null earnings fields propagate through to null stats."""
        rows = _simple_pcp_derive(
            earnings_1yr_median=None,
            debt_median=None,
            debt_to_earnings_annual=None,
            cip_family_earnings_rank=None,
        )
        assert rows[0]["stat_ern"] is None
        assert rows[0]["stat_roi"] is None
        assert rows[0]["boss_loans_score"] is None

    def test_no_bls_data_produces_null_grw_and_market(self):
        """When BLS join fails, stat_grw and boss_market are null."""
        co = [_make_career_outcome()]
        xw = [_make_crosswalk()]
        op = []  # no BLS
        onet = [_make_onet_profile()]
        rows = derive_pcp_rows(co, xw, op, onet)
        assert rows[0]["stat_grw"] is None
        assert rows[0]["boss_market_score"] is None
        assert rows[0]["match_quality"] == "partial_no_bls"

    def test_no_onet_data_produces_null_hmn_and_burnout(self):
        """When O*NET join fails, stat_hmn and boss_burnout are null."""
        co = [_make_career_outcome()]
        xw = [_make_crosswalk()]
        op = [_make_occupation_profile()]
        onet = []  # no O*NET
        rows = derive_pcp_rows(co, xw, op, onet)
        assert rows[0]["stat_hmn"] is None
        assert rows[0]["boss_burnout_score"] is None
        assert rows[0]["match_quality"] == "partial_no_onet"

    def test_scorecard_only_match(self):
        """No BLS or O*NET data produces scorecard_only match."""
        co = [_make_career_outcome()]
        xw = [_make_crosswalk()]
        op = []
        onet = []
        rows = derive_pcp_rows(co, xw, op, onet)
        assert rows[0]["match_quality"] == "scorecard_only"
        assert rows[0]["overall_confidence"] == "low"


# =========================================================================
# Table 2 Tests: career_branches
# =========================================================================


class TestCareerBranches:
    """Tests for career_branches derivation."""

    def test_basic_branch_enrichment(self):
        """Basic branch should carry source and target stats."""
        transitions = [_make_transition()]
        op = [
            _make_occupation_profile("15-1252", grw_score_rounded=8, median_annual_wage=133080.0),
            _make_occupation_profile("15-1256", grw_score_rounded=5, median_annual_wage=98000.0,
                                    growth_category="growing", education_level_name="Bachelor's degree"),
        ]
        onet = [
            _make_onet_profile("15-1252", hmn_score_rounded=5, burnout_score_rounded=4),
            _make_onet_profile("15-1256", hmn_score_rounded=3, burnout_score_rounded=7),
        ]
        rows = derive_br_rows(transitions, op, onet)
        assert len(rows) == 1
        r = rows[0]
        assert r["source_grw"] == 8
        assert r["related_grw"] == 5
        assert r["source_hmn"] == 5
        assert r["related_hmn"] == 3

    def test_grw_delta(self):
        """grw_delta = related_grw - source_grw."""
        transitions = [_make_transition()]
        op = [
            _make_occupation_profile("15-1252", grw_score_rounded=8),
            _make_occupation_profile("15-1256", grw_score_rounded=5),
        ]
        onet = [
            _make_onet_profile("15-1252", hmn_score_rounded=5),
            _make_onet_profile("15-1256", hmn_score_rounded=3),
        ]
        rows = derive_br_rows(transitions, op, onet)
        assert rows[0]["grw_delta"] == -3  # 5 - 8

    def test_wage_delta(self):
        """wage_delta = related_wage - source_wage."""
        transitions = [_make_transition()]
        op = [
            _make_occupation_profile("15-1252", median_annual_wage=133080.0),
            _make_occupation_profile("15-1256", median_annual_wage=98000.0),
        ]
        onet = [_make_onet_profile("15-1252"), _make_onet_profile("15-1256")]
        rows = derive_br_rows(transitions, op, onet)
        assert rows[0]["wage_delta"] == pytest.approx(-35080.0)

    def test_deltas_null_when_source_missing(self):
        """Deltas are null when source stats are missing."""
        transitions = [_make_transition()]
        op = [_make_occupation_profile("15-1256", grw_score_rounded=5)]
        onet = [_make_onet_profile("15-1256", hmn_score_rounded=3)]
        rows = derive_br_rows(transitions, op, onet)
        assert rows[0]["grw_delta"] is None
        assert rows[0]["hmn_delta"] is None

    def test_branch_has_full_data_true(self):
        """branch_has_full_data is True when related has both BLS and O*NET."""
        transitions = [_make_transition()]
        op = [
            _make_occupation_profile("15-1252"),
            _make_occupation_profile("15-1256"),
        ]
        onet = [
            _make_onet_profile("15-1252"),
            _make_onet_profile("15-1256"),
        ]
        rows = derive_br_rows(transitions, op, onet)
        assert rows[0]["branch_has_full_data"] is True

    def test_branch_has_full_data_false_no_onet(self):
        """branch_has_full_data is False when related has no O*NET."""
        transitions = [_make_transition()]
        op = [
            _make_occupation_profile("15-1252"),
            _make_occupation_profile("15-1256"),
        ]
        onet = [_make_onet_profile("15-1252")]  # no O*NET for related
        rows = derive_br_rows(transitions, op, onet)
        assert rows[0]["branch_has_full_data"] is False

    def test_empty_transitions_returns_empty(self):
        """Empty transitions list returns empty result."""
        rows = derive_br_rows([], [], [])
        assert rows == []


# =========================================================================
# Table 2 Tests: schema and record IDs
# =========================================================================


class TestBrSchemaAndRecordIds:
    """Tests for Table 2 schema and record ID generation."""

    def test_schema_has_34_columns(self):
        """Physical model specifies 34 columns (24 original + 6 AI backfill +
        4 experience columns added by the onet-experience-requirements spec).
        """
        schema = get_br_schema()
        assert len(schema.fields) == 34

    def test_record_id_deterministic(self):
        """record_id is deterministic for same grain."""
        transitions = [_make_transition()]
        op = [_make_occupation_profile("15-1252"), _make_occupation_profile("15-1256")]
        onet = [_make_onet_profile("15-1252"), _make_onet_profile("15-1256")]
        rows = derive_br_rows(transitions, op, onet)

        promoted_at = datetime.datetime(2026, 4, 9, 12, 0, tzinfo=datetime.timezone.utc)
        add_br_record_ids(rows, promoted_at)

        expected = compute_grain_id(
            {"soc_code": "15-1252", "related_soc_code": "15-1256"},
            BR_GRAIN_FIELDS,
            prefix=BR_GRAIN_PREFIX,
        )
        assert rows[0]["record_id"] == expected
        assert rows[0]["record_id"].startswith("br-")

    def test_carried_fields_preserved(self):
        """Carried fields from career_transitions should be preserved."""
        transitions = [_make_transition(
            best_index=3,
            relatedness_tier="Primary-Long",
            is_primary=True,
        )]
        op = [_make_occupation_profile("15-1252"), _make_occupation_profile("15-1256")]
        onet = [_make_onet_profile("15-1252"), _make_onet_profile("15-1256")]
        rows = derive_br_rows(transitions, op, onet)
        assert rows[0]["best_index"] == 3
        assert rows[0]["relatedness_tier"] == "Primary-Long"
        assert rows[0]["is_primary"] is True

    def test_related_growth_category_and_education(self):
        """Related occupation context fields should be carried."""
        transitions = [_make_transition()]
        op = [
            _make_occupation_profile("15-1252"),
            _make_occupation_profile(
                "15-1256",
                growth_category="growing_fast",
                education_level_name="Master's degree",
            ),
        ]
        onet = [_make_onet_profile("15-1252"), _make_onet_profile("15-1256")]
        rows = derive_br_rows(transitions, op, onet)
        assert rows[0]["related_growth_category"] == "growing_fast"
        assert rows[0]["related_education_level"] == "Master's degree"


# =========================================================================
# AI Exposure Backfill Tests
# =========================================================================


def _make_ai_exposure(soc_code="13-2051", stat_res=3, boss_ai_score=8):
    """Create a minimal ai_exposure row for testing."""
    return {
        "soc_code": soc_code,
        "stat_res": stat_res,
        "boss_ai_score": boss_ai_score,
    }


class TestPcpAiExposureBackfill:
    """Tests for AI exposure backfill into program_career_paths."""

    def test_stat_res_populated_from_ai_exposure(self):
        """stat_res is populated when ai_exposure has a matching SOC code."""
        co = [_make_career_outcome()]
        xw = [_make_crosswalk()]
        op = [_make_occupation_profile()]
        onet = [_make_onet_profile()]
        ai = [_make_ai_exposure("13-2051", stat_res=3, boss_ai_score=8)]
        rows = derive_pcp_rows(co, xw, op, onet, ai_exposure_rows=ai)
        assert rows[0]["stat_res"] == 3

    def test_boss_ai_score_populated_from_ai_exposure(self):
        """boss_ai_score is populated when ai_exposure has a matching SOC code."""
        co = [_make_career_outcome()]
        xw = [_make_crosswalk()]
        op = [_make_occupation_profile()]
        onet = [_make_onet_profile()]
        ai = [_make_ai_exposure("13-2051", stat_res=3, boss_ai_score=8)]
        rows = derive_pcp_rows(co, xw, op, onet, ai_exposure_rows=ai)
        assert rows[0]["boss_ai_score"] == 8

    def test_stat_res_null_when_soc_not_in_ai_exposure(self):
        """stat_res stays null when SOC code is not in ai_exposure."""
        co = [_make_career_outcome()]
        xw = [_make_crosswalk()]
        op = [_make_occupation_profile()]
        onet = [_make_onet_profile()]
        ai = [_make_ai_exposure("99-9999", stat_res=5, boss_ai_score=6)]
        rows = derive_pcp_rows(co, xw, op, onet, ai_exposure_rows=ai)
        assert rows[0]["stat_res"] is None
        assert rows[0]["boss_ai_score"] is None

    def test_stats_available_count_increments_with_ai(self):
        """stats_available_count increases by 1 when stat_res is populated."""
        # Provide cost basis so the new payback-multiplier ROI is non-null
        # (spec roi-net-lifetime-value).
        co = [_make_career_outcome(cost_of_attendance_annual=20_000.0)]
        xw = [_make_crosswalk()]
        op = [_make_occupation_profile()]
        onet = [_make_onet_profile()]

        # Without AI: 4 stats (ern, roi, grw, hmn)
        rows_no_ai = derive_pcp_rows(co, xw, op, onet)
        assert rows_no_ai[0]["stats_available_count"] == 4

        # With AI: 5 stats (ern, roi, res, grw, hmn)
        ai = [_make_ai_exposure("13-2051", stat_res=3, boss_ai_score=8)]
        rows_with_ai = derive_pcp_rows(co, xw, op, onet, ai_exposure_rows=ai)
        assert rows_with_ai[0]["stats_available_count"] == 5

    def test_bosses_available_count_increments_with_ai(self):
        """bosses_available_count increases by 1 when boss_ai_score is populated."""
        co = [_make_career_outcome(cost_of_attendance_annual=20_000.0)]
        xw = [_make_crosswalk()]
        op = [_make_occupation_profile()]
        onet = [_make_onet_profile()]

        # Without AI: 4 bosses (loans, market, burnout, ceiling)
        rows_no_ai = derive_pcp_rows(co, xw, op, onet)
        assert rows_no_ai[0]["bosses_available_count"] == 4

        # With AI: 5 bosses
        ai = [_make_ai_exposure("13-2051", stat_res=3, boss_ai_score=8)]
        rows_with_ai = derive_pcp_rows(co, xw, op, onet, ai_exposure_rows=ai)
        assert rows_with_ai[0]["bosses_available_count"] == 5

    def test_overall_confidence_may_upgrade_with_ai(self):
        """overall_confidence may upgrade when stats_available increases."""
        co = [_make_career_outcome()]
        xw = [_make_crosswalk()]
        op = [_make_occupation_profile()]
        onet = [_make_onet_profile()]
        ai = [_make_ai_exposure("13-2051", stat_res=3, boss_ai_score=8)]
        rows = derive_pcp_rows(co, xw, op, onet, ai_exposure_rows=ai)
        # With 5 stats and full match, should be "high"
        assert rows[0]["overall_confidence"] == "high"

    def test_empty_ai_exposure_list_same_as_none(self):
        """Passing empty ai_exposure_rows is the same as no AI data."""
        co = [_make_career_outcome()]
        xw = [_make_crosswalk()]
        op = [_make_occupation_profile()]
        onet = [_make_onet_profile()]
        rows = derive_pcp_rows(co, xw, op, onet, ai_exposure_rows=[])
        assert rows[0]["stat_res"] is None
        assert rows[0]["boss_ai_score"] is None


class TestBrAiExposureBackfill:
    """Tests for AI exposure backfill into career_branches."""

    def _br_with_ai(self, ai_rows):
        """Helper: derive career_branches with AI exposure data."""
        transitions = [_make_transition()]
        op = [
            _make_occupation_profile("15-1252", grw_score_rounded=8),
            _make_occupation_profile("15-1256", grw_score_rounded=5),
        ]
        onet = [
            _make_onet_profile("15-1252", hmn_score_rounded=5),
            _make_onet_profile("15-1256", hmn_score_rounded=3),
        ]
        return derive_br_rows(transitions, op, onet, ai_exposure_rows=ai_rows)

    def test_source_res_populated(self):
        """source_res is populated from ai_exposure for source SOC."""
        ai = [
            _make_ai_exposure("15-1252", stat_res=4, boss_ai_score=7),
            _make_ai_exposure("15-1256", stat_res=6, boss_ai_score=5),
        ]
        rows = self._br_with_ai(ai)
        assert rows[0]["source_res"] == 4
        assert rows[0]["source_ai_boss"] == 7

    def test_related_res_populated(self):
        """related_res is populated from ai_exposure for target SOC."""
        ai = [
            _make_ai_exposure("15-1252", stat_res=4, boss_ai_score=7),
            _make_ai_exposure("15-1256", stat_res=6, boss_ai_score=5),
        ]
        rows = self._br_with_ai(ai)
        assert rows[0]["related_res"] == 6
        assert rows[0]["related_ai_boss"] == 5

    def test_res_delta_computed(self):
        """res_delta = related_res - source_res."""
        ai = [
            _make_ai_exposure("15-1252", stat_res=4, boss_ai_score=7),
            _make_ai_exposure("15-1256", stat_res=6, boss_ai_score=5),
        ]
        rows = self._br_with_ai(ai)
        assert rows[0]["res_delta"] == 2  # 6 - 4

    def test_ai_boss_delta_computed(self):
        """ai_boss_delta = related_ai_boss - source_ai_boss."""
        ai = [
            _make_ai_exposure("15-1252", stat_res=4, boss_ai_score=7),
            _make_ai_exposure("15-1256", stat_res=6, boss_ai_score=5),
        ]
        rows = self._br_with_ai(ai)
        assert rows[0]["ai_boss_delta"] == -2  # 5 - 7

    def test_deltas_null_when_source_missing(self):
        """Deltas are null when source SOC not in ai_exposure."""
        ai = [_make_ai_exposure("15-1256", stat_res=6, boss_ai_score=5)]
        rows = self._br_with_ai(ai)
        assert rows[0]["source_res"] is None
        assert rows[0]["res_delta"] is None
        assert rows[0]["ai_boss_delta"] is None

    def test_deltas_null_when_target_missing(self):
        """Deltas are null when target SOC not in ai_exposure."""
        ai = [_make_ai_exposure("15-1252", stat_res=4, boss_ai_score=7)]
        rows = self._br_with_ai(ai)
        assert rows[0]["related_res"] is None
        assert rows[0]["res_delta"] is None
        assert rows[0]["ai_boss_delta"] is None

    def test_all_ai_fields_null_without_ai_data(self):
        """All AI fields are null when no ai_exposure data provided."""
        rows = self._br_with_ai([])
        assert rows[0]["source_res"] is None
        assert rows[0]["source_ai_boss"] is None
        assert rows[0]["related_res"] is None
        assert rows[0]["related_ai_boss"] is None
        assert rows[0]["res_delta"] is None
        assert rows[0]["ai_boss_delta"] is None

    def test_br_schema_has_ai_fields(self):
        """career_branches schema includes the 6 new AI fields."""
        schema = get_br_schema()
        field_names = [f.name for f in schema.fields]
        assert "source_res" in field_names
        assert "source_ai_boss" in field_names
        assert "related_res" in field_names
        assert "related_ai_boss" in field_names
        assert "res_delta" in field_names
        assert "ai_boss_delta" in field_names


# ---------------------------------------------------------------------------
# ROI multiplier-based scoring (spec roi-net-lifetime-value, 2026-05-04)
# ---------------------------------------------------------------------------


class TestComputeStatRoiFromMultiplier:
    """Threshold-ladder mapping from 15-year payback multiplier to 1-10.

    Spec: docs/specs/roi-net-lifetime-value.md §4 New Tests Required.

    The ladder is non-linear by design (Decision #4): a 1.5x multiplier
    is genuinely "underwater over 15 yrs" and a 16x multiplier is
    "elite" — equal-spaced bands would compress most real-world programs
    into the 5-7 band and lose discrimination at the extremes.

    These tests pin the boundary mapping so any future band recalibration
    is intentional.
    """

    def test_compute_stat_roi_threshold_boundaries(self):
        """Every threshold boundary maps to the correct integer score.

        ROI_MULTIPLIER_THRESHOLDS (upper-exclusive bounds):
          < 1.5  → 1     1.5 ≤ x < 2.5  → 2     2.5 ≤ x < 3.5  → 3
          3.5 ≤ x < 4.5  → 4     4.5 ≤ x < 5.5  → 5     5.5 ≤ x < 7.0  → 6
          7.0 ≤ x < 9.0  → 7     9.0 ≤ x < 12.0 → 8     12.0 ≤ x < 16.0 → 9
          ≥ 16.0  → 10
        """
        # Just-below each boundary stays in the lower band.
        assert compute_stat_roi_from_multiplier(1.49) == 1
        assert compute_stat_roi_from_multiplier(2.49) == 2
        assert compute_stat_roi_from_multiplier(3.49) == 3
        assert compute_stat_roi_from_multiplier(4.49) == 4
        assert compute_stat_roi_from_multiplier(5.49) == 5
        assert compute_stat_roi_from_multiplier(6.99) == 6
        assert compute_stat_roi_from_multiplier(8.99) == 7
        assert compute_stat_roi_from_multiplier(11.99) == 8
        assert compute_stat_roi_from_multiplier(15.99) == 9

        # Exactly-at each boundary jumps to the higher band (upper-exclusive).
        assert compute_stat_roi_from_multiplier(1.5) == 2
        assert compute_stat_roi_from_multiplier(2.5) == 3
        assert compute_stat_roi_from_multiplier(3.5) == 4
        assert compute_stat_roi_from_multiplier(4.5) == 5
        assert compute_stat_roi_from_multiplier(5.5) == 6
        assert compute_stat_roi_from_multiplier(7.0) == 7
        assert compute_stat_roi_from_multiplier(9.0) == 8
        assert compute_stat_roi_from_multiplier(12.0) == 9
        assert compute_stat_roi_from_multiplier(16.0) == 10

        # Above the top band stays at 10 (no overflow).
        assert compute_stat_roi_from_multiplier(20.0) == 10
        assert compute_stat_roi_from_multiplier(100.0) == 10

        # Below-zero / zero clamps to 1 (sanity floor — should not occur
        # in practice given Gold-pipeline guards).
        assert compute_stat_roi_from_multiplier(0.0) == 1
        assert compute_stat_roi_from_multiplier(-1.0) == 1
        assert compute_stat_roi_from_multiplier(-100.0) == 1

    def test_compute_stat_roi_none_input(self):
        """Returns None when input is None (cost or earnings missing)."""
        assert compute_stat_roi_from_multiplier(None) is None

    def test_thresholds_are_strictly_monotonic(self):
        """Sanity: the threshold table itself is strictly increasing.

        If anyone accidentally re-orders the table, every other test on
        this stat falls apart silently. Lock the invariant in.
        """
        bounds = [b for b, _score in ROI_MULTIPLIER_THRESHOLDS]
        scores = [s for _b, s in ROI_MULTIPLIER_THRESHOLDS]
        assert bounds == sorted(bounds)
        assert len(set(bounds)) == len(bounds)  # no duplicates
        assert scores == sorted(scores)
        assert len(set(scores)) == len(scores)
        # Score 10 is implicit (>= last bound), so the table itself
        # should cap at 9.
        assert scores[-1] == 9
