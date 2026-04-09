"""Tests for the Silver zone O*NET transformers.

Tests all 4 transformation functions: occupations, activity profiles,
context profiles, and career transitions. Minimum 15 tests per
staff-engineer requirement.
"""

import datetime
import json

import pytest

from silver.onet_transformer import (
    BURNOUT_ELEMENT_IDS,
    SPEC_NAME,
    derive_relatedness_tier,
    get_activity_profiles_schema,
    get_career_transitions_schema,
    get_context_profiles_schema,
    get_occupations_schema,
    transform_activity_profiles,
    transform_career_transitions,
    transform_context_profiles,
    transform_occupations,
    truncate_to_bls_soc,
)

NOW = datetime.datetime(2026, 4, 8, 12, 0, 0, tzinfo=datetime.timezone.utc)
LOAD_DATE = datetime.date(2026, 4, 8)


# ---------------------------------------------------------------------------
# Fixtures: raw Bronze row factories
# ---------------------------------------------------------------------------

def make_occ_row(onet_soc: str, title: str = "Test Occ", desc: str = "Desc"):
    return {
        "onet_soc_code": onet_soc,
        "title": title,
        "description": desc,
        "load_date": LOAD_DATE,
    }


def make_wa_row(
    onet_soc: str,
    element_id: str = "4.A.1.a.1",
    element_name: str = "Getting Information",
    scale_id: str = "IM",
    data_value: float = 3.5,
    recommend_suppress: str = "N",
):
    return {
        "onet_soc_code": onet_soc,
        "element_id": element_id,
        "element_name": element_name,
        "scale_id": scale_id,
        "data_value": data_value,
        "recommend_suppress": recommend_suppress,
        "load_date": LOAD_DATE,
    }


def make_wc_row(
    onet_soc: str,
    element_id: str = "4.C.3.d.1",
    element_name: str = "Time Pressure",
    scale_id: str = "CX",
    data_value: float = 3.0,
    recommend_suppress: str = "N",
):
    return {
        "onet_soc_code": onet_soc,
        "element_id": element_id,
        "element_name": element_name,
        "scale_id": scale_id,
        "data_value": data_value,
        "recommend_suppress": recommend_suppress,
        "load_date": LOAD_DATE,
    }


def make_ro_row(onet_soc: str, related_soc: str, index: int = 1):
    return {
        "onet_soc_code": onet_soc,
        "related_onet_soc_code": related_soc,
        "related_index": index,
        "load_date": LOAD_DATE,
    }


def make_ts_row(onet_soc: str):
    return {"onet_soc_code": onet_soc, "load_date": LOAD_DATE}


# ---------------------------------------------------------------------------
# Test: truncate_to_bls_soc
# ---------------------------------------------------------------------------

class TestTruncateToBLSSOC:

    def test_base_code(self):
        assert truncate_to_bls_soc("15-1252.00") == "15-1252"

    def test_detail_code(self):
        assert truncate_to_bls_soc("29-1229.01") == "29-1229"

    def test_already_truncated_no_dot(self):
        """Edge case: code without dot should return as-is."""
        assert truncate_to_bls_soc("15-1252") == "15-1252"


# ---------------------------------------------------------------------------
# Test: derive_relatedness_tier
# ---------------------------------------------------------------------------

class TestDeriveRelatednessTier:

    def test_primary_short_1(self):
        assert derive_relatedness_tier(1) == "Primary-Short"

    def test_primary_short_5(self):
        assert derive_relatedness_tier(5) == "Primary-Short"

    def test_primary_long_6(self):
        assert derive_relatedness_tier(6) == "Primary-Long"

    def test_primary_long_10(self):
        assert derive_relatedness_tier(10) == "Primary-Long"

    def test_supplemental_11(self):
        assert derive_relatedness_tier(11) == "Supplemental"

    def test_supplemental_20(self):
        assert derive_relatedness_tier(20) == "Supplemental"


# ---------------------------------------------------------------------------
# Test: transform_occupations
# ---------------------------------------------------------------------------

class TestTransformOccupations:

    def test_single_base_code(self):
        occ = [make_occ_row("15-1252.00", "Software Devs")]
        child = {"wa": {"15-1252"}, "wc": {"15-1252"}, "ts": {"15-1252"}, "ro": {"15-1252"}}
        result = transform_occupations(occ, child, NOW)
        assert len(result) == 1
        assert result[0]["bls_soc_code"] == "15-1252"
        assert result[0]["primary_title"] == "Software Devs"

    def test_multi_detail_aggregation(self):
        occ = [
            make_occ_row("29-1229.00", "Physicians, All Other"),
            make_occ_row("29-1229.01", "Allergists"),
            make_occ_row("29-1229.02", "Dermatologists"),
        ]
        child = {"wa": {"29-1229"}, "wc": {"29-1229"}, "ts": {"29-1229"}, "ro": {"29-1229"}}
        result = transform_occupations(occ, child, NOW)
        assert len(result) == 1
        rec = result[0]
        assert rec["bls_soc_code"] == "29-1229"
        assert rec["onet_detail_count"] == 3
        assert rec["multi_detail_flag"] is True
        codes = json.loads(rec["onet_detail_codes"])
        assert len(codes) == 3

    def test_prefers_base_00_for_title(self):
        occ = [
            make_occ_row("29-1229.01", "Allergists"),
            make_occ_row("29-1229.00", "Physicians, All Other"),
        ]
        child = {"wa": {"29-1229"}, "wc": {"29-1229"}, "ts": {"29-1229"}, "ro": {"29-1229"}}
        result = transform_occupations(occ, child, NOW)
        assert result[0]["primary_title"] == "Physicians, All Other"

    def test_no_base_code_uses_first_detail(self):
        occ = [
            make_occ_row("29-1229.02", "Dermatologists"),
            make_occ_row("29-1229.01", "Allergists"),
        ]
        child = {"wa": {"29-1229"}, "wc": {"29-1229"}, "ts": {"29-1229"}, "ro": {"29-1229"}}
        result = transform_occupations(occ, child, NOW)
        # Sorted by SOC, first is .01
        assert result[0]["primary_title"] == "Allergists"

    def test_excludes_structurally_empty(self):
        occ = [
            make_occ_row("99-9999.00", "All Other, Nothing"),
            make_occ_row("15-1252.00", "Software Devs"),
        ]
        child = {"wa": {"15-1252"}, "wc": {"15-1252"}, "ts": {"15-1252"}, "ro": {"15-1252"}}
        result = transform_occupations(occ, child, NOW)
        assert len(result) == 1
        assert result[0]["bls_soc_code"] == "15-1252"

    def test_full_completeness_tier(self):
        occ = [make_occ_row("15-1252.00")]
        child = {"wa": {"15-1252"}, "wc": {"15-1252"}, "ts": {"15-1252"}, "ro": {"15-1252"}}
        result = transform_occupations(occ, child, NOW)
        assert result[0]["data_completeness_tier"] == "full"
        assert result[0]["has_work_activities"] is True
        assert result[0]["has_work_context"] is True
        assert result[0]["has_tasks"] is True
        assert result[0]["has_related"] is True

    def test_partial_completeness_tier(self):
        occ = [make_occ_row("11-9199.00")]
        child = {"wa": set(), "wc": set(), "ts": {"11-9199"}, "ro": {"11-9199"}}
        result = transform_occupations(occ, child, NOW)
        assert result[0]["data_completeness_tier"] == "partial"
        assert result[0]["has_work_activities"] is False
        assert result[0]["has_tasks"] is True

    def test_record_id_prefix_on(self):
        occ = [make_occ_row("15-1252.00")]
        child = {"wa": {"15-1252"}, "wc": {"15-1252"}, "ts": {"15-1252"}, "ro": {"15-1252"}}
        result = transform_occupations(occ, child, NOW)
        assert result[0]["record_id"].startswith("on-")

    def test_record_id_deterministic(self):
        occ = [make_occ_row("15-1252.00")]
        child = {"wa": {"15-1252"}, "wc": {"15-1252"}, "ts": {"15-1252"}, "ro": {"15-1252"}}
        r1 = transform_occupations(occ, child, NOW)
        r2 = transform_occupations(occ, child, NOW)
        assert r1[0]["record_id"] == r2[0]["record_id"]

    def test_onet_detail_codes_is_json_array(self):
        occ = [make_occ_row("15-1252.00")]
        child = {"wa": {"15-1252"}, "wc": {"15-1252"}, "ts": {"15-1252"}, "ro": {"15-1252"}}
        result = transform_occupations(occ, child, NOW)
        codes = json.loads(result[0]["onet_detail_codes"])
        assert isinstance(codes, list)
        assert codes == ["15-1252.00"]

    def test_single_detail_not_multi(self):
        occ = [make_occ_row("15-1252.00")]
        child = {"wa": {"15-1252"}, "wc": {"15-1252"}, "ts": {"15-1252"}, "ro": {"15-1252"}}
        result = transform_occupations(occ, child, NOW)
        assert result[0]["multi_detail_flag"] is False
        assert result[0]["onet_detail_count"] == 1

    def test_source_load_date(self):
        occ = [make_occ_row("15-1252.00")]
        child = {"wa": {"15-1252"}, "wc": {"15-1252"}, "ts": {"15-1252"}, "ro": {"15-1252"}}
        result = transform_occupations(occ, child, NOW)
        assert result[0]["source_load_date"] == LOAD_DATE

    def test_ingested_at(self):
        occ = [make_occ_row("15-1252.00")]
        child = {"wa": {"15-1252"}, "wc": {"15-1252"}, "ts": {"15-1252"}, "ro": {"15-1252"}}
        result = transform_occupations(occ, child, NOW)
        assert result[0]["ingested_at"] == NOW

    def test_empty_input(self):
        result = transform_occupations([], {"wa": set(), "wc": set(), "ts": set(), "ro": set()}, NOW)
        assert result == []


# ---------------------------------------------------------------------------
# Test: transform_activity_profiles
# ---------------------------------------------------------------------------

class TestTransformActivityProfiles:

    def test_basic_im_row(self):
        wa = [make_wa_row("15-1252.00", data_value=4.0)]
        result = transform_activity_profiles(wa, {"15-1252"}, NOW)
        assert len(result) == 1
        assert result[0]["importance"] == 4.0
        assert result[0]["bls_soc_code"] == "15-1252"

    def test_filters_lv_scale(self):
        wa = [
            make_wa_row("15-1252.00", scale_id="IM", data_value=4.0),
            make_wa_row("15-1252.00", scale_id="LV", data_value=5.0),
        ]
        result = transform_activity_profiles(wa, {"15-1252"}, NOW)
        assert len(result) == 1

    def test_multi_detail_averaging(self):
        wa = [
            make_wa_row("29-1229.01", data_value=4.0),
            make_wa_row("29-1229.02", data_value=3.0),
        ]
        result = transform_activity_profiles(wa, {"29-1229"}, NOW)
        assert len(result) == 1
        assert result[0]["importance"] == 3.5
        assert result[0]["onet_details_averaged"] == 2

    def test_importance_rank(self):
        wa = [
            make_wa_row("15-1252.00", element_id="4.A.1.a.1", element_name="Getting Info", data_value=4.0),
            make_wa_row("15-1252.00", element_id="4.A.1.a.2", element_name="Monitoring", data_value=3.0),
            make_wa_row("15-1252.00", element_id="4.A.1.a.3", element_name="Analyzing", data_value=5.0),
        ]
        result = transform_activity_profiles(wa, {"15-1252"}, NOW)
        assert len(result) == 3
        by_element = {r["element_id"]: r for r in result}
        assert by_element["4.A.1.a.3"]["importance_rank"] == 1  # highest
        assert by_element["4.A.1.a.1"]["importance_rank"] == 2
        assert by_element["4.A.1.a.2"]["importance_rank"] == 3  # lowest

    def test_is_high_importance_true(self):
        wa = [make_wa_row("15-1252.00", data_value=3.5)]
        result = transform_activity_profiles(wa, {"15-1252"}, NOW)
        assert result[0]["is_high_importance"] is True

    def test_is_high_importance_false(self):
        wa = [make_wa_row("15-1252.00", data_value=3.49)]
        result = transform_activity_profiles(wa, {"15-1252"}, NOW)
        assert result[0]["is_high_importance"] is False

    def test_suppress_flag_propagates(self):
        wa = [
            make_wa_row("29-1229.01", recommend_suppress="N"),
            make_wa_row("29-1229.02", recommend_suppress="Y"),
        ]
        result = transform_activity_profiles(wa, {"29-1229"}, NOW)
        assert result[0]["suppress_flag"] is True

    def test_excludes_invalid_bls_soc(self):
        wa = [make_wa_row("99-9999.00")]
        result = transform_activity_profiles(wa, {"15-1252"}, NOW)
        assert len(result) == 0

    def test_record_id_prefix_wa(self):
        wa = [make_wa_row("15-1252.00")]
        result = transform_activity_profiles(wa, {"15-1252"}, NOW)
        assert result[0]["record_id"].startswith("wa-")

    def test_record_id_deterministic(self):
        wa = [make_wa_row("15-1252.00")]
        r1 = transform_activity_profiles(wa, {"15-1252"}, NOW)
        r2 = transform_activity_profiles(wa, {"15-1252"}, NOW)
        assert r1[0]["record_id"] == r2[0]["record_id"]

    def test_element_name_passthrough(self):
        wa = [make_wa_row("15-1252.00", element_name="Getting Information")]
        result = transform_activity_profiles(wa, {"15-1252"}, NOW)
        assert result[0]["element_name"] == "Getting Information"

    def test_single_detail_averaged_count_1(self):
        wa = [make_wa_row("15-1252.00")]
        result = transform_activity_profiles(wa, {"15-1252"}, NOW)
        assert result[0]["onet_details_averaged"] == 1


# ---------------------------------------------------------------------------
# Test: transform_context_profiles
# ---------------------------------------------------------------------------

class TestTransformContextProfiles:

    def test_basic_cx_row(self):
        wc = [make_wc_row("15-1252.00", scale_id="CX", data_value=3.5)]
        result = transform_context_profiles(wc, {"15-1252"}, NOW)
        assert len(result) == 1
        assert result[0]["context_value"] == 3.5
        assert result[0]["scale_id"] == "CX"

    def test_basic_ct_row(self):
        wc = [make_wc_row("15-1252.00", element_id="4.C.3.d.8", scale_id="CT", data_value=2.3)]
        result = transform_context_profiles(wc, {"15-1252"}, NOW)
        assert len(result) == 1
        assert result[0]["scale_id"] == "CT"

    def test_filters_cxp_ctp(self):
        wc = [
            make_wc_row("15-1252.00", scale_id="CX"),
            make_wc_row("15-1252.00", element_id="4.C.1.a.2.c", scale_id="CXP", data_value=0.3),
            make_wc_row("15-1252.00", element_id="4.C.1.a.2.d", scale_id="CTP", data_value=0.5),
        ]
        result = transform_context_profiles(wc, {"15-1252"}, NOW)
        assert len(result) == 1
        assert result[0]["scale_id"] == "CX"

    def test_burnout_element_correct_ids(self):
        """All 9 EDA-corrected burnout element IDs must be in the set."""
        expected = {
            "4.C.3.d.1", "4.C.3.d.8", "4.C.3.a.1", "4.C.3.d.3",
            "4.C.3.a.2.b", "4.C.3.b.4", "4.C.3.b.7", "4.C.3.d.4",
            "4.C.3.a.2.a",
        }
        assert BURNOUT_ELEMENT_IDS == expected
        assert len(BURNOUT_ELEMENT_IDS) == 9

    def test_is_burnout_true_for_time_pressure(self):
        wc = [make_wc_row("15-1252.00", element_id="4.C.3.d.1")]
        result = transform_context_profiles(wc, {"15-1252"}, NOW)
        assert result[0]["is_burnout_element"] is True

    def test_is_burnout_false_for_non_burnout(self):
        wc = [make_wc_row("15-1252.00", element_id="4.C.1.a.2.c", element_name="Public Speaking")]
        result = transform_context_profiles(wc, {"15-1252"}, NOW)
        assert result[0]["is_burnout_element"] is False

    def test_multi_detail_averaging(self):
        wc = [
            make_wc_row("29-1229.01", data_value=4.0),
            make_wc_row("29-1229.02", data_value=2.0),
        ]
        result = transform_context_profiles(wc, {"29-1229"}, NOW)
        assert len(result) == 1
        assert result[0]["context_value"] == 3.0
        assert result[0]["onet_details_averaged"] == 2

    def test_suppress_flag_propagates(self):
        wc = [
            make_wc_row("29-1229.01", recommend_suppress="N"),
            make_wc_row("29-1229.02", recommend_suppress="Y"),
        ]
        result = transform_context_profiles(wc, {"29-1229"}, NOW)
        assert result[0]["suppress_flag"] is True

    def test_record_id_prefix_wc(self):
        wc = [make_wc_row("15-1252.00")]
        result = transform_context_profiles(wc, {"15-1252"}, NOW)
        assert result[0]["record_id"].startswith("wc-")

    def test_excludes_invalid_bls_soc(self):
        wc = [make_wc_row("99-9999.00")]
        result = transform_context_profiles(wc, {"15-1252"}, NOW)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Test: transform_career_transitions
# ---------------------------------------------------------------------------

class TestTransformCareerTransitions:

    def test_basic_pair(self):
        ro = [make_ro_row("15-1252.00", "15-1253.00", index=1)]
        valid = {"15-1252", "15-1253"}
        result = transform_career_transitions(ro, valid, NOW)
        assert len(result) == 1
        assert result[0]["bls_soc_code"] == "15-1252"
        assert result[0]["related_bls_soc_code"] == "15-1253"
        assert result[0]["best_index"] == 1

    def test_removes_self_references(self):
        """Two O*NET details of same BLS SOC relating to each other."""
        ro = [make_ro_row("29-1229.01", "29-1229.02", index=3)]
        valid = {"29-1229"}
        result = transform_career_transitions(ro, valid, NOW)
        assert len(result) == 0

    def test_dedup_keeps_best_index(self):
        ro = [
            make_ro_row("29-1229.01", "15-1252.00", index=8),
            make_ro_row("29-1229.02", "15-1252.00", index=3),
            make_ro_row("29-1229.03", "15-1252.00", index=12),
        ]
        valid = {"29-1229", "15-1252"}
        result = transform_career_transitions(ro, valid, NOW)
        assert len(result) == 1
        assert result[0]["best_index"] == 3

    def test_relatedness_tier_primary_short(self):
        ro = [make_ro_row("15-1252.00", "15-1253.00", index=3)]
        valid = {"15-1252", "15-1253"}
        result = transform_career_transitions(ro, valid, NOW)
        assert result[0]["relatedness_tier"] == "Primary-Short"
        assert result[0]["is_primary"] is True

    def test_relatedness_tier_primary_long(self):
        ro = [make_ro_row("15-1252.00", "15-1253.00", index=7)]
        valid = {"15-1252", "15-1253"}
        result = transform_career_transitions(ro, valid, NOW)
        assert result[0]["relatedness_tier"] == "Primary-Long"
        assert result[0]["is_primary"] is True

    def test_relatedness_tier_supplemental(self):
        ro = [make_ro_row("15-1252.00", "15-1253.00", index=15)]
        valid = {"15-1252", "15-1253"}
        result = transform_career_transitions(ro, valid, NOW)
        assert result[0]["relatedness_tier"] == "Supplemental"
        assert result[0]["is_primary"] is False

    def test_relationship_type_always_similarity(self):
        ro = [make_ro_row("15-1252.00", "15-1253.00")]
        valid = {"15-1252", "15-1253"}
        result = transform_career_transitions(ro, valid, NOW)
        assert result[0]["relationship_type"] == "similarity"

    def test_excludes_invalid_source_soc(self):
        ro = [make_ro_row("99-9999.00", "15-1252.00")]
        valid = {"15-1252"}
        result = transform_career_transitions(ro, valid, NOW)
        assert len(result) == 0

    def test_excludes_invalid_target_soc(self):
        ro = [make_ro_row("15-1252.00", "99-9999.00")]
        valid = {"15-1252"}
        result = transform_career_transitions(ro, valid, NOW)
        assert len(result) == 0

    def test_record_id_prefix_ct(self):
        ro = [make_ro_row("15-1252.00", "15-1253.00")]
        valid = {"15-1252", "15-1253"}
        result = transform_career_transitions(ro, valid, NOW)
        assert result[0]["record_id"].startswith("ct-")

    def test_record_id_deterministic(self):
        ro = [make_ro_row("15-1252.00", "15-1253.00")]
        valid = {"15-1252", "15-1253"}
        r1 = transform_career_transitions(ro, valid, NOW)
        r2 = transform_career_transitions(ro, valid, NOW)
        assert r1[0]["record_id"] == r2[0]["record_id"]

    def test_directional_pairs_both_preserved(self):
        """A->B and B->A are distinct pairs."""
        ro = [
            make_ro_row("15-1252.00", "15-1253.00", index=1),
            make_ro_row("15-1253.00", "15-1252.00", index=2),
        ]
        valid = {"15-1252", "15-1253"}
        result = transform_career_transitions(ro, valid, NOW)
        assert len(result) == 2
        pairs = {(r["bls_soc_code"], r["related_bls_soc_code"]) for r in result}
        assert ("15-1252", "15-1253") in pairs
        assert ("15-1253", "15-1252") in pairs


# ---------------------------------------------------------------------------
# Test: Schema field counts
# ---------------------------------------------------------------------------

class TestSchemas:

    def test_occupations_schema_field_count(self):
        schema = get_occupations_schema()
        assert len(schema.fields) == 14

    def test_activity_profiles_schema_field_count(self):
        schema = get_activity_profiles_schema()
        assert len(schema.fields) == 11

    def test_context_profiles_schema_field_count(self):
        schema = get_context_profiles_schema()
        assert len(schema.fields) == 11

    def test_career_transitions_schema_field_count(self):
        schema = get_career_transitions_schema()
        assert len(schema.fields) == 9

    def test_all_schemas_all_fields_required(self):
        """Physical model says all columns are NOT NULL."""
        for schema_fn in [
            get_occupations_schema,
            get_activity_profiles_schema,
            get_context_profiles_schema,
            get_career_transitions_schema,
        ]:
            schema = schema_fn()
            for field in schema.fields:
                assert field.required, f"{field.name} should be required"


# ---------------------------------------------------------------------------
# Test: spec name constant
# ---------------------------------------------------------------------------

class TestConstants:

    def test_spec_name(self):
        assert SPEC_NAME == "silver-base-onet"

    def test_burnout_element_count(self):
        assert len(BURNOUT_ELEMENT_IDS) == 9

    def test_no_spec_incorrect_burnout_ids(self):
        """Verify the incorrect spec IDs are NOT in our set."""
        wrong_ids = {"4.C.3.d.5", "4.C.3.d.7", "4.C.3.b.2", "4.C.3.d.4_wrong"}
        # 4.C.3.d.5 and 4.C.3.d.7 do not exist in data
        assert "4.C.3.d.5" not in BURNOUT_ELEMENT_IDS
        assert "4.C.3.d.7" not in BURNOUT_ELEMENT_IDS
        # 4.C.3.b.2 is "Degree of Automation" (wrong), we use 4.C.3.a.2.b
        assert "4.C.3.a.2.b" in BURNOUT_ELEMENT_IDS
