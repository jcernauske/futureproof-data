"""Tests for the Gold zone O*NET work profiles transformer.

Covers HMN score rescaling, burnout score computation, JSON array generation,
null handling for partial-data occupations, confidence tier logic, and
static fields. Minimum 15 tests required across both test files.
"""

import datetime
import json

import pytest

from gold.onet_work_profiles import (
    GRAIN_FIELDS,
    GRAIN_PREFIX,
    HUMAN_INTENSIVE_ELEMENT_IDS,
    _normalize_context_value,
    _round_half_up,
    add_record_ids,
    derive_gold_rows,
    get_gold_schema,
)
from brightsmith.infra.grain import compute_grain_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# All 41 activity element IDs from O*NET Generalized Work Activities
ALL_ACTIVITY_IDS = [
    "4.A.1.a.1", "4.A.1.a.2", "4.A.1.a.3", "4.A.1.b.1", "4.A.1.b.2",
    "4.A.1.b.3", "4.A.1.b.4", "4.A.1.b.5", "4.A.2.a.1", "4.A.2.a.2",
    "4.A.2.a.3", "4.A.2.a.4", "4.A.2.b.1", "4.A.2.b.2", "4.A.2.b.3",
    "4.A.2.b.4", "4.A.2.b.5", "4.A.2.b.6", "4.A.3.a.1", "4.A.3.a.2",
    "4.A.3.a.3", "4.A.3.a.4", "4.A.3.b.1", "4.A.3.b.2", "4.A.3.b.4",
    "4.A.3.b.5", "4.A.3.b.6", "4.A.4.a.1", "4.A.4.a.2", "4.A.4.a.3",
    "4.A.4.a.4", "4.A.4.a.5", "4.A.4.a.6", "4.A.4.a.7", "4.A.4.a.8",
    "4.A.4.b.1", "4.A.4.b.2", "4.A.4.b.3", "4.A.4.b.4", "4.A.4.b.5",
    "4.A.4.c.2",
]

# Activity names for the 41 elements (simplified for testing)
ACTIVITY_NAMES = {eid: f"Activity_{eid}" for eid in ALL_ACTIVITY_IDS}
ACTIVITY_NAMES["4.A.2.b.1"] = "Making Decisions and Solving Problems"
ACTIVITY_NAMES["4.A.2.b.2"] = "Thinking Creatively"
ACTIVITY_NAMES["4.A.4.a.4"] = "Establishing and Maintaining Interpersonal Relationships"
ACTIVITY_NAMES["4.A.4.b.1"] = "Coordinating the Work and Activities of Others"
ACTIVITY_NAMES["4.A.4.b.3"] = "Training and Teaching Others"
ACTIVITY_NAMES["4.A.1.a.1"] = "Getting Information"


def _make_occupation(
    bls_soc_code="15-1252",
    primary_title="Software Developers",
    description="Develop software applications.",
    multi_detail_flag=False,
    data_completeness_tier="full",
    source_load_date=datetime.date(2026, 4, 8),
):
    return {
        "bls_soc_code": bls_soc_code,
        "primary_title": primary_title,
        "description": description,
        "multi_detail_flag": multi_detail_flag,
        "data_completeness_tier": data_completeness_tier,
        "source_load_date": source_load_date,
    }


def _make_activities(bls_soc_code="15-1252", base_importance=3.0, human_boost=1.0):
    """Create 41 activity rows for a SOC with configurable importance."""
    human_set = set(HUMAN_INTENSIVE_ELEMENT_IDS)
    rows = []
    for eid in ALL_ACTIVITY_IDS:
        imp = base_importance + human_boost if eid in human_set else base_importance
        rows.append({
            "bls_soc_code": bls_soc_code,
            "element_id": eid,
            "element_name": ACTIVITY_NAMES.get(eid, f"Activity_{eid}"),
            "importance": imp,
            "suppress_flag": False,
            "is_high_importance": imp >= 3.5,
        })
    return rows


def _make_context_rows(bls_soc_code="15-1252", burnout_value=3.5, non_burnout_value=2.5):
    """Create context rows with 9 burnout elements and some non-burnout."""
    burnout_elements = [
        ("4.C.3.d.1", "Time Pressure", "CX"),
        ("4.C.3.d.8", "Duration of Typical Work Week", "CT"),
        ("4.C.3.a.1", "Consequence of Error", "CX"),
        ("4.C.3.d.3", "Pace Determined by Speed of Equipment", "CX"),
        ("4.C.3.a.2.b", "Frequency of Decision Making", "CX"),
        ("4.C.3.b.4", "Importance of Being Exact or Accurate", "CX"),
        ("4.C.3.b.7", "Importance of Repeating Same Tasks", "CX"),
        ("4.C.3.d.4", "Work Schedules", "CT"),
        ("4.C.3.a.2.a", "Impact of Decisions on Co-workers", "CX"),
    ]
    rows = []
    for eid, name, scale in burnout_elements:
        val = burnout_value if scale == "CX" else min(burnout_value, 3.0)
        rows.append({
            "bls_soc_code": bls_soc_code,
            "element_id": eid,
            "element_name": name,
            "scale_id": scale,
            "context_value": val,
            "is_burnout_element": True,
            "suppress_flag": False,
        })
    # Add a few non-burnout context rows
    for i in range(5):
        rows.append({
            "bls_soc_code": bls_soc_code,
            "element_id": f"4.C.1.a.{i+1}",
            "element_name": f"NonBurnout_{i}",
            "scale_id": "CX",
            "context_value": non_burnout_value,
            "is_burnout_element": False,
            "suppress_flag": False,
        })
    return rows


# ---------------------------------------------------------------------------
# Tests: HMN Score Rescaling
# ---------------------------------------------------------------------------


class TestHMNScore:
    """Tests for HMN score computation with min/max rescaling."""

    def test_hmn_rescale_min_gets_1(self):
        """Occupation with lowest human_ratio gets HMN score 1.0."""
        # SOC1: low human-intensive importance, SOC2: high
        occs = [
            _make_occupation(bls_soc_code="10-0001", primary_title="Low HMN"),
            _make_occupation(bls_soc_code="10-0002", primary_title="High HMN"),
        ]
        # Low: human activities = 1.0, non-human = 4.0
        acts1 = _make_activities("10-0001", base_importance=4.0, human_boost=-3.0)
        # High: human activities = 5.0, non-human = 1.0
        acts2 = _make_activities("10-0002", base_importance=1.0, human_boost=4.0)
        ctxs = _make_context_rows("10-0001") + _make_context_rows("10-0002")

        result = derive_gold_rows(occs, acts1 + acts2, ctxs)
        low_occ = next(r for r in result if r["bls_soc_code"] == "10-0001")
        high_occ = next(r for r in result if r["bls_soc_code"] == "10-0002")

        assert low_occ["hmn_score"] == pytest.approx(1.0)
        assert high_occ["hmn_score"] == pytest.approx(10.0)

    def test_hmn_rescale_max_gets_10(self):
        """Occupation with highest human_ratio gets HMN score 10.0."""
        occs = [
            _make_occupation(bls_soc_code="10-0001"),
            _make_occupation(bls_soc_code="10-0002"),
        ]
        acts1 = _make_activities("10-0001", base_importance=3.0, human_boost=0.0)
        acts2 = _make_activities("10-0002", base_importance=3.0, human_boost=2.0)
        ctxs = _make_context_rows("10-0001") + _make_context_rows("10-0002")

        result = derive_gold_rows(occs, acts1 + acts2, ctxs)
        high = next(r for r in result if r["bls_soc_code"] == "10-0002")
        assert high["hmn_score"] == pytest.approx(10.0)

    def test_hmn_clamped_to_range(self):
        """HMN scores are clamped to [1.0, 10.0]."""
        occs = [
            _make_occupation(bls_soc_code="10-0001"),
            _make_occupation(bls_soc_code="10-0002"),
        ]
        acts1 = _make_activities("10-0001", base_importance=3.0, human_boost=0.0)
        acts2 = _make_activities("10-0002", base_importance=3.0, human_boost=1.0)
        ctxs = _make_context_rows("10-0001") + _make_context_rows("10-0002")

        result = derive_gold_rows(occs, acts1 + acts2, ctxs)
        for r in result:
            if r["hmn_score"] is not None:
                assert 1.0 <= r["hmn_score"] <= 10.0

    def test_hmn_null_for_partial_data(self):
        """Partial-data occupations (no activities) get null HMN score."""
        occs = [
            _make_occupation(bls_soc_code="10-0001"),
            _make_occupation(bls_soc_code="99-9999", data_completeness_tier="partial"),
        ]
        acts = _make_activities("10-0001")
        ctxs = _make_context_rows("10-0001")

        result = derive_gold_rows(occs, acts, ctxs)
        partial = next(r for r in result if r["bls_soc_code"] == "99-9999")
        assert partial["hmn_score"] is None
        assert partial["hmn_score_rounded"] is None

    def test_hmn_rounded_consistency(self):
        """hmn_score_rounded matches round-half-up of hmn_score."""
        occs = [
            _make_occupation(bls_soc_code="10-0001"),
            _make_occupation(bls_soc_code="10-0002"),
            _make_occupation(bls_soc_code="10-0003"),
        ]
        acts = (
            _make_activities("10-0001", base_importance=3.0, human_boost=0.0)
            + _make_activities("10-0002", base_importance=3.0, human_boost=0.5)
            + _make_activities("10-0003", base_importance=3.0, human_boost=1.0)
        )
        ctxs = (
            _make_context_rows("10-0001")
            + _make_context_rows("10-0002")
            + _make_context_rows("10-0003")
        )

        result = derive_gold_rows(occs, acts, ctxs)
        for r in result:
            if r["hmn_score"] is not None:
                assert r["hmn_score_rounded"] == _round_half_up(r["hmn_score"])

    def test_hmn_two_phase_required(self):
        """HMN score computation requires all ratios before rescaling.

        With 3 occupations at different human ratios, the middle one should
        get a score strictly between 1 and 10.
        """
        occs = [
            _make_occupation(bls_soc_code="10-0001"),
            _make_occupation(bls_soc_code="10-0002"),
            _make_occupation(bls_soc_code="10-0003"),
        ]
        acts = (
            _make_activities("10-0001", base_importance=3.0, human_boost=0.0)
            + _make_activities("10-0002", base_importance=3.0, human_boost=0.5)
            + _make_activities("10-0003", base_importance=3.0, human_boost=1.0)
        )
        ctxs = (
            _make_context_rows("10-0001")
            + _make_context_rows("10-0002")
            + _make_context_rows("10-0003")
        )

        result = derive_gold_rows(occs, acts, ctxs)
        mid = next(r for r in result if r["bls_soc_code"] == "10-0002")
        assert 1.0 < mid["hmn_score"] < 10.0


# ---------------------------------------------------------------------------
# Tests: Burnout Score
# ---------------------------------------------------------------------------


class TestBurnoutScore:
    """Tests for burnout score computation."""

    def test_burnout_score_range(self):
        """Burnout score should be between 1.0 and 10.0."""
        occs = [_make_occupation()]
        acts = _make_activities()
        ctxs = _make_context_rows(burnout_value=3.5)

        result = derive_gold_rows(occs, acts, ctxs)
        assert 1.0 <= result[0]["burnout_score"] <= 10.0

    def test_burnout_score_formula(self):
        """burnout_score = 1.0 + 9.0 * avg(normalized values)."""
        # CX value 3.5 -> normalized (3.5-1)/4 = 0.625
        # CT value 3.0 -> normalized (3.0-1)/2 = 1.0
        # 7 CX elements + 2 CT elements
        # avg = (7 * 0.625 + 2 * 1.0) / 9 = (4.375 + 2.0) / 9 = 6.375 / 9 = 0.708333
        # burnout = 1 + 9 * 0.708333 = 7.375
        occs = [_make_occupation()]
        acts = _make_activities()
        ctxs = _make_context_rows(burnout_value=3.5)

        result = derive_gold_rows(occs, acts, ctxs)
        assert result[0]["burnout_score"] == pytest.approx(7.375, abs=0.01)

    def test_burnout_null_for_partial_data(self):
        """Partial occupations with no context data get null burnout."""
        occs = [
            _make_occupation(bls_soc_code="10-0001"),
            _make_occupation(bls_soc_code="99-9999", data_completeness_tier="partial"),
        ]
        acts = _make_activities("10-0001")
        ctxs = _make_context_rows("10-0001")

        result = derive_gold_rows(occs, acts, ctxs)
        partial = next(r for r in result if r["bls_soc_code"] == "99-9999")
        assert partial["burnout_score"] is None
        assert partial["burnout_score_rounded"] is None
        assert partial["burnout_drivers"] is None

    def test_burnout_rounded_consistency(self):
        """burnout_score_rounded matches round-half-up of burnout_score."""
        occs = [_make_occupation()]
        acts = _make_activities()
        ctxs = _make_context_rows(burnout_value=3.0)

        result = derive_gold_rows(occs, acts, ctxs)
        bs = result[0]["burnout_score"]
        assert result[0]["burnout_score_rounded"] == _round_half_up(bs)

    def test_burnout_low_values(self):
        """Low burnout context values produce low burnout score."""
        occs = [_make_occupation()]
        acts = _make_activities()
        # CX min is 1.0, CT min is 1.0 -> all normalized to 0.0
        ctxs = _make_context_rows(burnout_value=1.0)

        result = derive_gold_rows(occs, acts, ctxs)
        assert result[0]["burnout_score"] == pytest.approx(1.0, abs=0.01)


# ---------------------------------------------------------------------------
# Tests: JSON Arrays
# ---------------------------------------------------------------------------


class TestJSONArrays:
    """Tests for JSON array field generation."""

    def test_top_5_activities_is_valid_json(self):
        """top_5_activities should be a valid JSON array of 5 items."""
        occs = [_make_occupation()]
        acts = _make_activities()
        ctxs = _make_context_rows()

        result = derive_gold_rows(occs, acts, ctxs)
        parsed = json.loads(result[0]["top_5_activities"])
        assert len(parsed) == 5
        assert all("activity" in item and "importance" in item for item in parsed)

    def test_top_human_activities_is_valid_json(self):
        """top_human_activities should be valid JSON with up to 5 items."""
        occs = [_make_occupation()]
        acts = _make_activities()
        ctxs = _make_context_rows()

        result = derive_gold_rows(occs, acts, ctxs)
        parsed = json.loads(result[0]["top_human_activities"])
        assert len(parsed) == 5
        assert all("activity" in item and "importance" in item for item in parsed)

    def test_burnout_drivers_is_valid_json(self):
        """burnout_drivers should be valid JSON with 3 items."""
        occs = [_make_occupation()]
        acts = _make_activities()
        ctxs = _make_context_rows()

        result = derive_gold_rows(occs, acts, ctxs)
        parsed = json.loads(result[0]["burnout_drivers"])
        assert len(parsed) == 3
        assert all("element" in item and "value" in item for item in parsed)

    def test_json_null_for_partial_data(self):
        """JSON arrays should be null for partial-data occupations."""
        occs = [
            _make_occupation(bls_soc_code="10-0001"),
            _make_occupation(bls_soc_code="99-9999", data_completeness_tier="partial"),
        ]
        acts = _make_activities("10-0001")
        ctxs = _make_context_rows("10-0001")

        result = derive_gold_rows(occs, acts, ctxs)
        partial = next(r for r in result if r["bls_soc_code"] == "99-9999")
        assert partial["top_5_activities"] is None
        assert partial["top_human_activities"] is None
        assert partial["burnout_drivers"] is None


# ---------------------------------------------------------------------------
# Tests: Individual Element Extraction
# ---------------------------------------------------------------------------


class TestIndividualElements:
    """Tests for individual burnout element extraction."""

    def test_time_pressure_extracted(self):
        """time_pressure should be the context value for 4.C.3.d.1."""
        occs = [_make_occupation()]
        acts = _make_activities()
        ctxs = _make_context_rows(burnout_value=4.0)

        result = derive_gold_rows(occs, acts, ctxs)
        assert result[0]["time_pressure"] == 4.0

    def test_work_hours_extracted(self):
        """work_hours should be the context value for 4.C.3.d.8 (CT scale, capped at 3)."""
        occs = [_make_occupation()]
        acts = _make_activities()
        ctxs = _make_context_rows(burnout_value=3.5)

        result = derive_gold_rows(occs, acts, ctxs)
        assert result[0]["work_hours"] == 3.0  # CT capped at 3.0 in _make_context_rows

    def test_consequence_of_error_extracted(self):
        """consequence_of_error should be the context value for 4.C.3.a.1."""
        occs = [_make_occupation()]
        acts = _make_activities()
        ctxs = _make_context_rows(burnout_value=2.5)

        result = derive_gold_rows(occs, acts, ctxs)
        assert result[0]["consequence_of_error"] == 2.5

    def test_individual_elements_null_for_partial(self):
        """Individual burnout elements should be null for partial occupations."""
        occs = [
            _make_occupation(bls_soc_code="10-0001"),
            _make_occupation(bls_soc_code="99-9999", data_completeness_tier="partial"),
        ]
        acts = _make_activities("10-0001")
        ctxs = _make_context_rows("10-0001")

        result = derive_gold_rows(occs, acts, ctxs)
        partial = next(r for r in result if r["bls_soc_code"] == "99-9999")
        assert partial["time_pressure"] is None
        assert partial["work_hours"] is None
        assert partial["consequence_of_error"] is None


# ---------------------------------------------------------------------------
# Tests: Confidence Tier & Suppression
# ---------------------------------------------------------------------------


class TestConfidenceTier:
    """Tests for confidence tier derivation."""

    def test_high_confidence_full_data(self):
        """Full data with low suppression -> high confidence."""
        occs = [_make_occupation()]
        acts = _make_activities()
        ctxs = _make_context_rows()

        result = derive_gold_rows(occs, acts, ctxs)
        assert result[0]["confidence_tier"] == "high"

    def test_low_confidence_partial_data(self):
        """Partial data occupations -> low confidence."""
        occs = [
            _make_occupation(bls_soc_code="10-0001"),
            _make_occupation(bls_soc_code="99-9999", data_completeness_tier="partial"),
        ]
        acts = _make_activities("10-0001")
        ctxs = _make_context_rows("10-0001")

        result = derive_gold_rows(occs, acts, ctxs)
        partial = next(r for r in result if r["bls_soc_code"] == "99-9999")
        assert partial["confidence_tier"] == "low"

    def test_medium_confidence_high_suppression(self):
        """Full data with >= 5% context suppression -> medium confidence."""
        occs = [_make_occupation(bls_soc_code="29-1241")]
        acts = _make_activities("29-1241")

        # Create context rows with high suppression rate (>= 5%)
        ctxs = _make_context_rows("29-1241")
        # Suppress enough context rows to exceed 5%
        total = len(ctxs)
        suppress_count = max(1, int(total * 0.06))  # 6%
        for i in range(suppress_count):
            ctxs[i]["suppress_flag"] = True

        result = derive_gold_rows(occs, acts, ctxs)
        assert result[0]["confidence_tier"] == "medium"


# ---------------------------------------------------------------------------
# Tests: Static Fields & Schema
# ---------------------------------------------------------------------------


class TestStaticFields:
    """Tests for static fields and schema conformity."""

    def test_backs_stats_always_hmn(self):
        """backs_stats should always be 'HMN'."""
        occs = [_make_occupation()]
        acts = _make_activities()
        ctxs = _make_context_rows()

        result = derive_gold_rows(occs, acts, ctxs)
        assert result[0]["backs_stats"] == "HMN"

    def test_backs_bosses_always_ai_burnout(self):
        """backs_bosses should always be 'AI,Burnout'."""
        occs = [_make_occupation()]
        acts = _make_activities()
        ctxs = _make_context_rows()

        result = derive_gold_rows(occs, acts, ctxs)
        assert result[0]["backs_bosses"] == "AI,Burnout"

    def test_record_id_deterministic(self):
        """record_id should be deterministic for same bls_soc_code."""
        occs = [_make_occupation()]
        acts = _make_activities()
        ctxs = _make_context_rows()

        result = derive_gold_rows(occs, acts, ctxs)
        promoted_at = datetime.datetime(2026, 4, 8, 12, 0, 0, tzinfo=datetime.timezone.utc)
        add_record_ids(result, promoted_at)

        expected_id = compute_grain_id(
            {"bls_soc_code": "15-1252"}, GRAIN_FIELDS, prefix=GRAIN_PREFIX
        )
        assert result[0]["record_id"] == expected_id
        assert result[0]["record_id"].startswith("wp-")

    def test_schema_column_count(self):
        """Schema should have exactly 27 columns."""
        schema = get_gold_schema()
        assert len(schema.fields) == 27

    def test_empty_input_returns_empty(self):
        """Empty occupation list returns empty result."""
        result = derive_gold_rows([], [], [])
        assert result == []


# ---------------------------------------------------------------------------
# Tests: Normalization helper
# ---------------------------------------------------------------------------


class TestNormalizeContextValue:
    """Tests for CX and CT normalization."""

    def test_cx_normalization(self):
        """CX: (value - 1) / 4. 1->0, 5->1."""
        assert _normalize_context_value(1.0, "CX") == pytest.approx(0.0)
        assert _normalize_context_value(5.0, "CX") == pytest.approx(1.0)
        assert _normalize_context_value(3.0, "CX") == pytest.approx(0.5)

    def test_ct_normalization(self):
        """CT: (value - 1) / 2. 1->0, 3->1."""
        assert _normalize_context_value(1.0, "CT") == pytest.approx(0.0)
        assert _normalize_context_value(3.0, "CT") == pytest.approx(1.0)
        assert _normalize_context_value(2.0, "CT") == pytest.approx(0.5)

    def test_unknown_scale_raises(self):
        """Unknown scale_id should raise ValueError."""
        with pytest.raises(ValueError):
            _normalize_context_value(3.0, "XX")
