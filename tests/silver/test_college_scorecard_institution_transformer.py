"""Tests for the Silver zone College Scorecard institution transformer."""

import datetime

import pytest

from silver.college_scorecard_institution_transformer import (
    CONTROL_LABELS,
    GRAIN_FIELDS,
    GRAIN_PREFIX,
    get_silver_schema,
    map_control_label,
    multiply_or_none,
    pick_by_control,
    transform_row,
)


@pytest.fixture
def raw_row_public():
    """A fully populated raw row representing a public institution (control=1)."""
    return {
        "unitid": 110635,
        "instnm": "University of California-Berkeley",
        "stabbr": "CA",
        "control": 1,
        "preddeg": 3,
        "costt4_a": 40000.0,
        "costt4_p": None,
        "npt4_pub": 18000.0,
        "npt4_priv": None,
        "npt41_pub": 10000.0,
        "npt42_pub": 13000.0,
        "npt43_pub": 16000.0,
        "npt44_pub": 22000.0,
        "npt45_pub": 28000.0,
        "npt41_priv": None,
        "npt42_priv": None,
        "npt43_priv": None,
        "npt44_priv": None,
        "npt45_priv": None,
        "tuitionfee_in": 14000.0,
        "tuitionfee_out": 44000.0,
        "roomboard_on": 16000.0,
        "roomboard_off": 15000.0,
        "booksupply": 1200.0,
        "load_date": datetime.date(2026, 4, 6),
    }


@pytest.fixture
def raw_row_private_nonprofit():
    """A fully populated raw row representing a private nonprofit (control=2)."""
    return {
        "unitid": 243744,
        "instnm": "Stanford University",
        "stabbr": "CA",
        "control": 2,
        "preddeg": 3,
        "costt4_a": 82000.0,
        "costt4_p": None,
        "npt4_pub": None,
        "npt4_priv": 20000.0,
        "npt41_pub": None,
        "npt42_pub": None,
        "npt43_pub": None,
        "npt44_pub": None,
        "npt45_pub": None,
        "npt41_priv": 3000.0,
        "npt42_priv": 8000.0,
        "npt43_priv": 14000.0,
        "npt44_priv": 28000.0,
        "npt45_priv": 52000.0,
        "tuitionfee_in": 60000.0,
        "tuitionfee_out": 60000.0,
        "roomboard_on": 19000.0,
        "roomboard_off": 18000.0,
        "booksupply": 1400.0,
        "load_date": datetime.date(2026, 4, 6),
    }


@pytest.fixture
def raw_row_private_for_profit():
    """A fully populated raw row representing a private for-profit (control=3)."""
    return {
        "unitid": 999001,
        "instnm": "Example For-Profit University",
        "stabbr": "AZ",
        "control": 3,
        "preddeg": 3,
        "costt4_a": 30000.0,
        "costt4_p": None,
        "npt4_pub": None,
        "npt4_priv": 25000.0,
        "npt41_pub": None,
        "npt42_pub": None,
        "npt43_pub": None,
        "npt44_pub": None,
        "npt45_pub": None,
        "npt41_priv": 22000.0,
        "npt42_priv": 23000.0,
        "npt43_priv": 24000.0,
        "npt44_priv": 25500.0,
        "npt45_priv": 27000.0,
        "tuitionfee_in": 20000.0,
        "tuitionfee_out": 20000.0,
        "roomboard_on": None,
        "roomboard_off": 12000.0,
        "booksupply": 1800.0,
        "load_date": datetime.date(2026, 4, 6),
    }


class TestMapControlLabel:
    """Tests for numeric control -> label mapping."""

    def test_public(self):
        assert map_control_label(1) == "Public"

    def test_private_nonprofit(self):
        assert map_control_label(2) == "Private nonprofit"

    def test_private_for_profit(self):
        assert map_control_label(3) == "Private for-profit"

    def test_none_returns_none(self):
        assert map_control_label(None) is None

    def test_unexpected_integer_returns_none(self):
        # Bronze DQ should prevent this, but the transformer must not crash.
        assert map_control_label(99) is None

    def test_string_digit_coerces(self):
        # Guards against Bronze ever emitting string-typed controls.
        assert map_control_label("1") == "Public"

    def test_non_numeric_string_returns_none(self):
        assert map_control_label("public") is None


class TestPickByControl:
    """Tests for public/private routing of unified measures."""

    def test_control_1_picks_pub(self):
        assert pick_by_control(1, 100.0, 200.0) == 100.0

    def test_control_2_picks_priv(self):
        assert pick_by_control(2, 100.0, 200.0) == 200.0

    def test_control_3_picks_priv(self):
        assert pick_by_control(3, 100.0, 200.0) == 200.0

    def test_control_none_returns_none(self):
        assert pick_by_control(None, 100.0, 200.0) is None

    def test_control_unexpected_returns_none(self):
        assert pick_by_control(99, 100.0, 200.0) is None

    def test_routed_value_is_none(self):
        # Public school with missing npt4_pub -> net_price_annual is None.
        assert pick_by_control(1, None, 200.0) is None
        # Private school with missing npt4_priv -> None.
        assert pick_by_control(2, 100.0, None) is None

    def test_string_digit_coerces(self):
        assert pick_by_control("1", 100.0, 200.0) == 100.0
        assert pick_by_control("2", 100.0, 200.0) == 200.0


class TestMultiplyOrNone:
    """Tests for null-propagating multiplication used by the 4-year derivations."""

    def test_multiplies_non_null(self):
        assert multiply_or_none(1000.0, 4) == 4000.0

    def test_zero_multiplies_to_zero(self):
        assert multiply_or_none(0.0, 4) == 0.0

    def test_none_propagates(self):
        assert multiply_or_none(None, 4) is None


class TestTransformRow:
    """Tests for single-row transformation logic."""

    def test_returns_dict(self, raw_row_public):
        result = transform_row(raw_row_public)
        assert isinstance(result, dict)

    def test_public_control_label(self, raw_row_public):
        result = transform_row(raw_row_public)
        assert result["institution_control"] == "Public"

    def test_private_nonprofit_control_label(self, raw_row_private_nonprofit):
        result = transform_row(raw_row_private_nonprofit)
        assert result["institution_control"] == "Private nonprofit"

    def test_private_for_profit_control_label(self, raw_row_private_for_profit):
        result = transform_row(raw_row_private_for_profit)
        assert result["institution_control"] == "Private for-profit"

    def test_identity_fields_passed_through(self, raw_row_public):
        result = transform_row(raw_row_public)
        assert result["unitid"] == 110635
        assert result["institution_name"] == "University of California-Berkeley"
        assert result["state_abbr"] == "CA"

    # --- Net price routing (control-based) ---

    def test_public_net_price_routes_to_pub(self, raw_row_public):
        result = transform_row(raw_row_public)
        assert result["net_price_annual"] == 18000.0

    def test_private_nonprofit_net_price_routes_to_priv(self, raw_row_private_nonprofit):
        result = transform_row(raw_row_private_nonprofit)
        assert result["net_price_annual"] == 20000.0

    def test_private_for_profit_net_price_routes_to_priv(self, raw_row_private_for_profit):
        result = transform_row(raw_row_private_for_profit)
        assert result["net_price_annual"] == 25000.0

    def test_net_price_null_when_routed_field_null(self, raw_row_public):
        raw_row_public["npt4_pub"] = None
        result = transform_row(raw_row_public)
        assert result["net_price_annual"] is None

    # --- Cost of attendance coalesce ---

    def test_coa_prefers_costt4_a(self, raw_row_public):
        raw_row_public["costt4_a"] = 40000.0
        raw_row_public["costt4_p"] = 50000.0
        result = transform_row(raw_row_public)
        assert result["cost_of_attendance_annual"] == 40000.0

    def test_coa_falls_back_to_costt4_p(self, raw_row_public):
        raw_row_public["costt4_a"] = None
        raw_row_public["costt4_p"] = 35000.0
        result = transform_row(raw_row_public)
        assert result["cost_of_attendance_annual"] == 35000.0

    def test_coa_null_when_both_null(self, raw_row_public):
        raw_row_public["costt4_a"] = None
        raw_row_public["costt4_p"] = None
        result = transform_row(raw_row_public)
        assert result["cost_of_attendance_annual"] is None
        assert result["cost_of_attendance_4yr"] is None

    # --- 4-year derivations ---

    def test_net_price_4yr_is_annual_times_four(self, raw_row_public):
        result = transform_row(raw_row_public)
        assert result["net_price_4yr"] == 72000.0

    def test_coa_4yr_is_annual_times_four(self, raw_row_public):
        result = transform_row(raw_row_public)
        assert result["cost_of_attendance_4yr"] == 160000.0

    def test_net_price_4yr_null_when_annual_null(self, raw_row_public):
        raw_row_public["npt4_pub"] = None
        result = transform_row(raw_row_public)
        assert result["net_price_4yr"] is None

    # --- Quintile routing (all 5 x pub/priv) ---

    @pytest.mark.parametrize(
        "field,expected",
        [
            ("net_price_q1", 10000.0),
            ("net_price_q2", 13000.0),
            ("net_price_q3", 16000.0),
            ("net_price_q4", 22000.0),
            ("net_price_q5", 28000.0),
        ],
    )
    def test_public_quintiles_route_to_pub(self, raw_row_public, field, expected):
        result = transform_row(raw_row_public)
        assert result[field] == expected

    @pytest.mark.parametrize(
        "field,expected",
        [
            ("net_price_q1", 3000.0),
            ("net_price_q2", 8000.0),
            ("net_price_q3", 14000.0),
            ("net_price_q4", 28000.0),
            ("net_price_q5", 52000.0),
        ],
    )
    def test_private_quintiles_route_to_priv(self, raw_row_private_nonprofit, field, expected):
        result = transform_row(raw_row_private_nonprofit)
        assert result[field] == expected

    @pytest.mark.parametrize(
        "field,expected",
        [
            ("net_price_q1", 22000.0),
            ("net_price_q2", 23000.0),
            ("net_price_q3", 24000.0),
            ("net_price_q4", 25500.0),
            ("net_price_q5", 27000.0),
        ],
    )
    def test_for_profit_quintiles_route_to_priv(
        self, raw_row_private_for_profit, field, expected
    ):
        result = transform_row(raw_row_private_for_profit)
        assert result[field] == expected

    def test_missing_quintile_preserved_as_null(self, raw_row_public):
        raw_row_public["npt43_pub"] = None
        result = transform_row(raw_row_public)
        assert result["net_price_q3"] is None
        # Other quintiles are still populated from the pub branch.
        assert result["net_price_q1"] == 10000.0

    # --- Raw pass-through fields (provenance) ---

    def test_raw_coa_passthrough(self, raw_row_public):
        result = transform_row(raw_row_public)
        assert result["costt4_a_raw"] == 40000.0
        assert result["costt4_p_raw"] is None

    def test_raw_avg_net_price_passthrough(self, raw_row_private_nonprofit):
        result = transform_row(raw_row_private_nonprofit)
        # Both raw values are carried regardless of which one was routed.
        assert result["npt4_pub_raw"] is None
        assert result["npt4_priv_raw"] == 20000.0

    def test_raw_pub_quintile_passthrough(self, raw_row_public):
        result = transform_row(raw_row_public)
        assert result["npt41_pub_raw"] == 10000.0
        assert result["npt45_pub_raw"] == 28000.0
        # Private raws are carried even on a public row.
        assert result["npt41_priv_raw"] is None

    def test_raw_priv_quintile_passthrough(self, raw_row_private_nonprofit):
        result = transform_row(raw_row_private_nonprofit)
        assert result["npt41_priv_raw"] == 3000.0
        assert result["npt45_priv_raw"] == 52000.0
        assert result["npt41_pub_raw"] is None

    # --- Tuition / room+board / books pass-through ---

    def test_tuition_fields_passthrough(self, raw_row_public):
        result = transform_row(raw_row_public)
        assert result["tuition_in_state"] == 14000.0
        assert result["tuition_out_of_state"] == 44000.0

    def test_room_board_passthrough(self, raw_row_public):
        result = transform_row(raw_row_public)
        assert result["room_board_on_campus"] == 16000.0
        assert result["room_board_off_campus"] == 15000.0

    def test_books_supplies_passthrough(self, raw_row_public):
        result = transform_row(raw_row_public)
        assert result["books_supplies"] == 1200.0

    def test_null_tuition_preserved(self, raw_row_public):
        raw_row_public["tuitionfee_in"] = None
        result = transform_row(raw_row_public)
        assert result["tuition_in_state"] is None

    # --- Pipeline metadata ---

    def test_source_load_date_preserved(self, raw_row_public):
        result = transform_row(raw_row_public)
        assert result["source_load_date"] == datetime.date(2026, 4, 6)

    def test_ingested_at_is_timestamp(self, raw_row_public):
        result = transform_row(raw_row_public)
        assert isinstance(result["ingested_at"], datetime.datetime)

    # --- record_id ---

    def test_record_id_has_csi_prefix(self, raw_row_public):
        result = transform_row(raw_row_public)
        assert result["record_id"].startswith("csi-")

    def test_record_id_deterministic(self, raw_row_public):
        r1 = transform_row(raw_row_public)
        r2 = transform_row(dict(raw_row_public))
        assert r1["record_id"] == r2["record_id"]

    def test_record_id_changes_with_unitid(self, raw_row_public):
        r1 = transform_row(raw_row_public)
        raw_row_public["unitid"] = 999999
        r2 = transform_row(raw_row_public)
        assert r1["record_id"] != r2["record_id"]

    def test_record_id_stable_across_measure_changes(self, raw_row_public):
        # Only unitid participates in the grain hash per the physical model.
        r1 = transform_row(raw_row_public)
        raw_row_public["costt4_a"] = 99999.0
        raw_row_public["npt4_pub"] = 12345.0
        r2 = transform_row(raw_row_public)
        assert r1["record_id"] == r2["record_id"]

    # --- Row-level validation / skip conditions ---

    def test_null_unitid_returns_none(self, raw_row_public):
        raw_row_public["unitid"] = None
        assert transform_row(raw_row_public) is None

    def test_null_instnm_returns_none(self, raw_row_public):
        raw_row_public["instnm"] = None
        assert transform_row(raw_row_public) is None

    def test_null_stabbr_returns_none(self, raw_row_public):
        raw_row_public["stabbr"] = None
        assert transform_row(raw_row_public) is None

    def test_null_control_returns_none(self, raw_row_public):
        # institution_control is NOT NULL per physical model, so rows without
        # a mappable control must be skipped rather than written with null.
        raw_row_public["control"] = None
        assert transform_row(raw_row_public) is None

    def test_unexpected_control_returns_none(self, raw_row_public):
        raw_row_public["control"] = 99
        assert transform_row(raw_row_public) is None


class TestRecordCountPreservation:
    """Silver should emit one row per valid Bronze row."""

    def test_all_valid_rows_preserved(
        self, raw_row_public, raw_row_private_nonprofit, raw_row_private_for_profit
    ):
        raws = [raw_row_public, raw_row_private_nonprofit, raw_row_private_for_profit]
        out = [transform_row(r) for r in raws]
        assert len(out) == len(raws)
        assert all(r is not None for r in out)

    def test_unique_record_ids_per_unitid(
        self, raw_row_public, raw_row_private_nonprofit, raw_row_private_for_profit
    ):
        out = [
            transform_row(raw_row_public),
            transform_row(raw_row_private_nonprofit),
            transform_row(raw_row_private_for_profit),
        ]
        ids = {r["record_id"] for r in out}
        assert len(ids) == 3


class TestControlLabelsConstant:
    """The CONTROL_LABELS mapping is the source of truth for the label domain."""

    def test_all_three_controls_present(self):
        assert CONTROL_LABELS[1] == "Public"
        assert CONTROL_LABELS[2] == "Private nonprofit"
        assert CONTROL_LABELS[3] == "Private for-profit"

    def test_exactly_three_entries(self):
        assert len(CONTROL_LABELS) == 3


class TestGrainConfig:
    """Grain fields and prefix match the physical model."""

    def test_grain_fields(self):
        assert GRAIN_FIELDS == ["unitid"]

    def test_grain_prefix(self):
        assert GRAIN_PREFIX == "csi"


class TestSilverSchema:
    """Tests for the Silver Iceberg schema structure."""

    def test_schema_field_count(self):
        # 34 business columns + ingested_at = 35 per physical model.
        schema = get_silver_schema()
        assert len(schema.fields) == 35

    def test_required_fields(self):
        schema = get_silver_schema()
        required = {f.name for f in schema.fields if f.required}
        assert required == {
            "record_id",
            "unitid",
            "institution_name",
            "state_abbr",
            "institution_control",
            "source_load_date",
            "ingested_at",
        }

    def test_unified_measures_nullable(self):
        schema = get_silver_schema()
        nullable = {f.name for f in schema.fields if not f.required}
        for name in [
            "cost_of_attendance_annual",
            "cost_of_attendance_4yr",
            "net_price_annual",
            "net_price_4yr",
            "net_price_q1",
            "net_price_q2",
            "net_price_q3",
            "net_price_q4",
            "net_price_q5",
        ]:
            assert name in nullable

    def test_raw_passthrough_fields_present(self):
        schema = get_silver_schema()
        names = {f.name for f in schema.fields}
        for name in [
            "costt4_a_raw",
            "costt4_p_raw",
            "npt4_pub_raw",
            "npt4_priv_raw",
            "npt41_pub_raw",
            "npt42_pub_raw",
            "npt43_pub_raw",
            "npt44_pub_raw",
            "npt45_pub_raw",
            "npt41_priv_raw",
            "npt42_priv_raw",
            "npt43_priv_raw",
            "npt44_priv_raw",
            "npt45_priv_raw",
        ]:
            assert name in names

    def test_field_ids_stable(self):
        """Field IDs must match the physical model spec exactly."""
        schema = get_silver_schema()
        ids_by_name = {f.name: f.field_id for f in schema.fields}
        assert ids_by_name["record_id"] == 1
        assert ids_by_name["unitid"] == 2
        assert ids_by_name["institution_name"] == 3
        assert ids_by_name["state_abbr"] == 4
        assert ids_by_name["institution_control"] == 5
        assert ids_by_name["cost_of_attendance_annual"] == 6
        assert ids_by_name["cost_of_attendance_4yr"] == 7
        assert ids_by_name["net_price_annual"] == 8
        assert ids_by_name["net_price_4yr"] == 9
        assert ids_by_name["net_price_q1"] == 10
        assert ids_by_name["net_price_q5"] == 14
        assert ids_by_name["source_load_date"] == 34
        assert ids_by_name["ingested_at"] == 35
