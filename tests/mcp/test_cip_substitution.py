"""Unit tests for CIP intent substitution in get_career_paths.

Covers the product decisions described in
``docs/specs/cip-intent-substitution.md``:

  * Substitution fires only when all four gates pass (student_major
    provided, reported cipcode is broad, major matches, family matches)
  * Lookup is case- and alias-insensitive
  * Family-mismatch and unrecognized-major fall back to the standard
    path with a ``substitution_note``
  * Blended ERN/ROI use the Gold engine formula
  * ``data_caveat`` metadata is attached to every substituted row set
    and absent on non-substituted results
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from mcp_server.futureproof_server import (
    CAREER_OUTCOMES_TABLE,
    FutureProofMCPServer,
)


# Sample lookup that mirrors the shape of major_to_cip.yaml.
FAKE_LOOKUP = [
    {
        "major": "Marketing",
        "cip4": "52.14",
        "cip_family": "52",
        "aliases": ["marketing management", "mktg", "digital marketing"],
    },
    {
        "major": "Accounting",
        "cip4": "52.03",
        "cip_family": "52",
        "aliases": ["accountancy", "acct"],
    },
    {
        "major": "Finance",
        "cip4": "52.08",
        "cip_family": "52",
        "aliases": ["financial management"],
    },
    {
        "major": "Nursing",
        "cip4": "51.38",
        "cip_family": "51",
        "aliases": ["registered nurse", "RN"],
    },
]


# IU-B broad-CIP row used as the substitution earnings basis.
IUB_CO_ROW = {
    "unitid": 151351,
    "institution_name": "Indiana University-Bloomington",
    "cipcode": "52.01",
    "program_name": "Business/Commerce, General.",
    "cip_family_name": "Business, Management, Marketing",
    "earnings_1yr_median": 63371.0,
    "earnings_1yr_p25": 38515.0,
    "earnings_1yr_p75": 49674.0,
    "debt_median": 19500.0,
    "debt_to_earnings_annual": 0.3077,
    "cip_family_earnings_rank": 0.9558,
    "confidence_tier": "high",
}


def _make_server() -> FutureProofMCPServer:
    server = FutureProofMCPServer.__new__(FutureProofMCPServer)
    server.warehouse_path = "/tmp/fake"
    server.catalog_path = "/tmp/fake.db"
    server.grounding_docs_path = None
    server.server_name = "test"
    server.formatter = None
    server.anomaly_checker = None
    server.system_prompt = None
    server._catalog = MagicMock()
    # Pre-populate the lookup cache so we don't hit the filesystem.
    server._major_to_cip_cache = FAKE_LOOKUP
    return server


def _fake_query_simple(table_name, filters=None, columns=None, limit=None):
    """Mock dispatch for query_iceberg_simple across the 4 tables used.

    Returns (table, filters) → rows. The marketing SOCs 11-2021 and
    13-1161 get representative occupation/onet/ai rows; others return
    empty lists so the handler produces a sparse pentagon for them.
    """
    filters = filters or {}
    if table_name == CAREER_OUTCOMES_TABLE:
        if filters.get("unitid") == 151351 and filters.get("cipcode") == "52.01":
            return [IUB_CO_ROW]
        return []
    if table_name == "consumable.occupation_profiles":
        soc = filters.get("soc_code")
        if soc == "11-2021":
            return [
                {
                    "soc_code": "11-2021",
                    "occupation_title": "Marketing Managers",
                    "soc_major_group_name": "Management",
                    "median_annual_wage": 161030.0,
                    "wage_percentile_overall": 0.95,
                    "grw_score_rounded": 7,
                    "market_score_rounded": 8,
                    "growth_category": "Faster than average",
                    "employment_current": 400000,
                    "education_level_name": "Bachelor's degree",
                }
            ]
        if soc == "13-1161":
            return [
                {
                    "soc_code": "13-1161",
                    "occupation_title": "Market Research Analysts",
                    "soc_major_group_name": "Business and Financial Operations",
                    "median_annual_wage": 76950.0,
                    "wage_percentile_overall": 0.72,
                    "grw_score_rounded": 7,
                    "market_score_rounded": 8,
                    "growth_category": "Faster than average",
                    "employment_current": 900000,
                    "education_level_name": "Bachelor's degree",
                }
            ]
        return []
    if table_name == "consumable.onet_work_profiles":
        soc = filters.get("bls_soc_code")
        if soc == "11-2021":
            return [
                {
                    "bls_soc_code": "11-2021",
                    "primary_title": "Marketing Managers",
                    "hmn_score_rounded": 6,
                    "burnout_score_rounded": 6,
                    "top_5_activities": "[]",
                    "top_human_activities": "[]",
                    "burnout_drivers": "[]",
                }
            ]
        if soc == "13-1161":
            return [
                {
                    "bls_soc_code": "13-1161",
                    "primary_title": "Market Research Analysts",
                    "hmn_score_rounded": 3,
                    "burnout_score_rounded": 5,
                    "top_5_activities": "[]",
                    "top_human_activities": "[]",
                    "burnout_drivers": "[]",
                }
            ]
        return []
    if table_name == "consumable.ai_exposure":
        soc = filters.get("soc_code")
        if soc == "11-2021":
            return [
                {
                    "soc_code": "11-2021",
                    "stat_res": 3,
                    "boss_ai_score": 8,
                }
            ]
        if soc == "13-1161":
            return [
                {
                    "soc_code": "13-1161",
                    "stat_res": 2,
                    "boss_ai_score": 9,
                }
            ]
        return []
    return []


def _patch_substitution(server, cip4_socs: list[str]):
    """Patch the crosswalk + query_iceberg_simple for a substitution flow."""
    return (
        patch.object(
            server,
            "_fetch_crosswalk_socs",
            return_value=cip4_socs,
        ),
        patch.object(
            server,
            "query_iceberg_simple",
            side_effect=_fake_query_simple,
        ),
    )


class TestSubstitutionFires:
    """Substitution happens for a broad-CIP school + matched major."""

    def test_iub_marketing_substitution_fires(self):
        server = _make_server()
        xw_patch, q_patch = _patch_substitution(
            server, ["11-2021", "13-1161"]
        )
        with xw_patch, q_patch:
            result = server._handle_get_career_paths(
                {
                    "unitid": 151351,
                    "cipcode": "52.01",
                    "student_major": "Marketing",
                }
            )
        assert result["substitution_applied"] is True
        assert result["reported_cipcode"] == "52.01"
        assert result["substituted_cipcode"] == "52.14"
        assert result["row_count"] == 2
        socs = [r["soc_code"] for r in result["data"]]
        assert set(socs) == {"11-2021", "13-1161"}
        # All substituted rows use the substituted cipcode and the
        # school's broad-program earnings.
        for row in result["data"]:
            assert row["cipcode"] == "52.14"
            assert row["unitid"] == 151351
            assert row["earnings_1yr_median"] == 63371.0
            assert row["debt_to_earnings_annual"] == 0.3077
            assert row["match_quality"] == "substituted_cip"

    def test_no_substitution_when_major_omitted(self):
        """No student_major → standard path, no substitution."""
        server = _make_server()
        with patch.object(
            server,
            "query_iceberg_simple",
            return_value=[
                {
                    f: None
                    for f in (
                        "unitid",
                        "cipcode",
                        "soc_code",
                        "occupation_title",
                        "stats_available_count",
                    )
                }
                | {"stats_available_count": 5, "soc_code": "11-9021"}
            ],
        ):
            result = server._handle_get_career_paths(
                {"unitid": 151351, "cipcode": "52.01"}
            )
        assert result["substitution_applied"] is False
        assert "data_caveat" not in result

    def test_no_substitution_when_specific_cip(self):
        """ISU reports 52.14 directly → student_major is ignored."""
        server = _make_server()
        with patch.object(
            server,
            "query_iceberg_simple",
            return_value=[{"stats_available_count": 5, "soc_code": "11-2021"}],
        ):
            result = server._handle_get_career_paths(
                {
                    "unitid": 145813,
                    "cipcode": "52.14",
                    "student_major": "Marketing",
                }
            )
        assert result["substitution_applied"] is False
        assert "substitution_note" in result
        assert "specific" in result["substitution_note"]


class TestAliasMatching:
    """Case-insensitive alias matching against major names + aliases."""

    def test_uppercase_marketing(self):
        server = _make_server()
        entry = server._find_major_intent("MARKETING")
        assert entry is not None
        assert entry["cip4"] == "52.14"

    def test_alias_mktg(self):
        server = _make_server()
        entry = server._find_major_intent("mktg")
        assert entry is not None
        assert entry["cip4"] == "52.14"

    def test_alias_phrase_marketing_management(self):
        server = _make_server()
        entry = server._find_major_intent("marketing management")
        assert entry is not None
        assert entry["cip4"] == "52.14"

    def test_unknown_major_returns_none(self):
        server = _make_server()
        assert server._find_major_intent("Underwater Basket Weaving") is None

    def test_empty_major_returns_none(self):
        server = _make_server()
        assert server._find_major_intent("") is None
        assert server._find_major_intent("   ") is None


class TestFamilyMismatchAndUnknown:
    """Invalid substitutions fall back to the standard path."""

    def test_family_mismatch_falls_back(self):
        """Student says 'Nursing' (51.xx) at a 52.01 school → standard path."""
        server = _make_server()
        standard_rows = [
            {"stats_available_count": 5, "soc_code": "11-9021"}
        ]
        with patch.object(
            server, "query_iceberg_simple", return_value=standard_rows
        ):
            result = server._handle_get_career_paths(
                {
                    "unitid": 151351,
                    "cipcode": "52.01",
                    "student_major": "Nursing",
                }
            )
        assert result["substitution_applied"] is False
        assert "substitution_note" in result
        assert "family" in result["substitution_note"]
        assert "data_caveat" not in result

    def test_unrecognized_major_falls_back(self):
        server = _make_server()
        standard_rows = [
            {"stats_available_count": 5, "soc_code": "11-9021"}
        ]
        with patch.object(
            server, "query_iceberg_simple", return_value=standard_rows
        ):
            result = server._handle_get_career_paths(
                {
                    "unitid": 151351,
                    "cipcode": "52.01",
                    "student_major": "Underwater Basket Weaving",
                }
            )
        assert result["substitution_applied"] is False
        assert "substitution_note" in result
        assert "Could not map" in result["substitution_note"]
        assert "data_caveat" not in result


class TestBroadCipDetection:
    def test_broad_cip_detection(self):
        assert FutureProofMCPServer._is_broad_cip("52.01") is True
        assert FutureProofMCPServer._is_broad_cip("52.0100") is True
        assert FutureProofMCPServer._is_broad_cip("13.01") is True
        assert FutureProofMCPServer._is_broad_cip("52.14") is False
        assert FutureProofMCPServer._is_broad_cip("52.0101") is False
        assert FutureProofMCPServer._is_broad_cip("52.02") is False

    def test_cip_family_extraction(self):
        assert FutureProofMCPServer._cip_family("52.01") == "52"
        assert FutureProofMCPServer._cip_family("51.38") == "51"
        assert FutureProofMCPServer._cip_family("52.1401") == "52"


class TestBlendedStats:
    """ERN and ROI match the Gold engine formula."""

    def test_ern_and_roi_match_engine_formula(self):
        """Blended ERN = round(1 + 9*(0.6*rank + 0.4*wpo)).

        With IU-B rank = 0.9558 and 13-1161 wpo = 0.72:
            raw = 0.6*0.9558 + 0.4*0.72 = 0.85348
            1 + 9*0.85348 = 8.68
            round half-up → 9
        ROI with dte = 0.3077 → piecewise linear from Gold engine.
        We just assert the values match the engine, not a specific int,
        to avoid duplicating the breakpoint table here.
        """
        from gold.futureproof_engine import compute_stat_ern, compute_stat_roi

        expected_ern = compute_stat_ern(0.9558, 0.72)
        expected_roi = compute_stat_roi(0.3077)

        server = _make_server()
        xw_patch, q_patch = _patch_substitution(server, ["13-1161"])
        with xw_patch, q_patch:
            result = server._handle_get_career_paths(
                {
                    "unitid": 151351,
                    "cipcode": "52.01",
                    "student_major": "Marketing",
                }
            )
        row = result["data"][0]
        assert row["stat_ern"] == expected_ern
        assert row["stat_roi"] == expected_roi

    def test_same_school_same_ern_roi_across_substitutions(self):
        """ERN/ROI depend only on school-level inputs + SOC wpo.

        Across two different student majors at the same school, the ROI
        for any given SOC remains identical (since ROI depends only on
        the school's debt-to-earnings ratio, not the SOC).
        """
        server = _make_server()

        def _all_missing(*a, **kw):
            # Return empty op/onet/ai but the IU-B CO row.
            return _fake_query_simple(*a, **kw)

        xw_patch, q_patch = _patch_substitution(server, ["13-1161"])
        with xw_patch, q_patch:
            r1 = server._handle_get_career_paths(
                {
                    "unitid": 151351,
                    "cipcode": "52.01",
                    "student_major": "Marketing",
                }
            )
        xw_patch2, q_patch2 = _patch_substitution(server, ["13-1161"])
        with xw_patch2, q_patch2:
            r2 = server._handle_get_career_paths(
                {
                    "unitid": 151351,
                    "cipcode": "52.01",
                    "student_major": "Accounting",
                }
            )
        assert r1["data"][0]["stat_roi"] == r2["data"][0]["stat_roi"]


class TestCaveatMetadata:
    def test_data_caveat_present_on_substituted(self):
        server = _make_server()
        xw_patch, q_patch = _patch_substitution(server, ["11-2021"])
        with xw_patch, q_patch:
            result = server._handle_get_career_paths(
                {
                    "unitid": 151351,
                    "cipcode": "52.01",
                    "student_major": "Marketing",
                }
            )
        caveat = result["data_caveat"]
        assert caveat["type"] == "blended_substitution"
        assert caveat["reported_cipcode"] == "52.01"
        assert caveat["substituted_cipcode"] == "52.14"
        assert caveat["substituted_program"] == "Marketing"
        assert caveat["earnings_specificity"] == "school_broad"
        assert caveat["career_path_specificity"] == "national_major_specific"
        assert "Marketing" in caveat["message"]

    def test_data_caveat_absent_on_standard(self):
        server = _make_server()
        with patch.object(
            server,
            "query_iceberg_simple",
            return_value=[{"stats_available_count": 5, "soc_code": "11-9021"}],
        ):
            result = server._handle_get_career_paths(
                {"unitid": 151351, "cipcode": "52.01"}
            )
        assert "data_caveat" not in result


class TestErrorHandling:
    def test_missing_school_row_returns_null(self):
        """If the school's broad-CIP row is missing, substitution fails."""
        server = _make_server()
        empty_query = patch.object(
            server, "query_iceberg_simple", return_value=[]
        )
        xw_patch = patch.object(
            server, "_fetch_crosswalk_socs", return_value=["11-2021"]
        )
        with xw_patch, empty_query:
            result = server._handle_get_career_paths(
                {
                    "unitid": 999999,
                    "cipcode": "52.01",
                    "student_major": "Marketing",
                }
            )
        assert result["data"] is None
        assert "cannot substitute" in result["message"]

    def test_empty_crosswalk_returns_null(self):
        server = _make_server()
        xw_patch = patch.object(
            server, "_fetch_crosswalk_socs", return_value=[]
        )
        q_patch = patch.object(
            server, "query_iceberg_simple", side_effect=_fake_query_simple
        )
        with xw_patch, q_patch:
            result = server._handle_get_career_paths(
                {
                    "unitid": 151351,
                    "cipcode": "52.01",
                    "student_major": "Marketing",
                }
            )
        assert result["data"] is None
        assert "crosswalk" in result["message"].lower()
