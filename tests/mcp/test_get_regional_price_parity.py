"""Tests for the get_regional_price_parity MCP tool.

Covers:
    * State input normalization (FIPS / USPS / full name, case insensitive,
      whitespace, unknown, non-string)
    * Success path for all 8 BEA-verified states using exact Gold values
      from the 2026-04-11 signed-off gold-regional-price-parities spec
    * Sample estimated states returning data_source='estimate'
    * Strict mode: verified_only=true succeeds for bea_official rows
    * Strict mode: verified_only=true refuses estimate rows with a
      structured null response
    * Response shape: adjusted_examples struct, verification_status
      renamed to data_source, full-precision
      purchasing_power_multiplier (pre-review Advisory #1)
    * Governance metadata attached to every response
    * Tool registration (mirrors test_get_ai_exposure pattern)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from mcp_server._state_input import normalize_state_input
from mcp_server.futureproof_server import (
    RPP_QUERY_FIELDS,
    RPP_TABLE_NAME,
    FutureProofMCPServer,
)


# ---------------------------------------------------------------------------
# Fixtures — exact Gold rows for the 8 BEA-verified states
# ---------------------------------------------------------------------------

# Each row matches the shape returned by query_iceberg_simple: the full
# set of RPP_QUERY_FIELDS with full-precision purchasing_power_multiplier.
VERIFIED_ROWS: dict[str, dict] = {
    "AR": {
        "state_name": "Arkansas",
        "state_abbr": "AR",
        "state_fips": "05",
        "census_region": "South",
        "rpp_all_items": 86.9,
        "purchasing_power_multiplier": 1.1507479861910241,
        "cost_tier": "very_low",
        "adjusted_30k": 34522.44,
        "adjusted_50k": 57537.4,
        "adjusted_75k": 86306.1,
        "adjusted_100k": 115074.8,
        "verification_status": "bea_official",
        "data_year": 2024,
    },
    "CA": {
        "state_name": "California",
        "state_abbr": "CA",
        "state_fips": "06",
        "census_region": "West",
        "rpp_all_items": 110.7,
        "purchasing_power_multiplier": 0.9033423667570009,
        "cost_tier": "very_high",
        "adjusted_30k": 27100.27,
        "adjusted_50k": 45167.12,
        "adjusted_75k": 67750.68,
        "adjusted_100k": 90334.24,
        "verification_status": "bea_official",
        "data_year": 2024,
    },
    "DC": {
        "state_name": "District of Columbia",
        "state_abbr": "DC",
        "state_fips": "11",
        "census_region": "South",
        "rpp_all_items": 109.9,
        "purchasing_power_multiplier": 0.9099181073703366,
        "cost_tier": "very_high",
        "adjusted_30k": 27297.54,
        "adjusted_50k": 45495.91,
        "adjusted_75k": 68243.86,
        "adjusted_100k": 90991.81,
        "verification_status": "bea_official",
        "data_year": 2024,
    },
    "HI": {
        "state_name": "Hawaii",
        "state_abbr": "HI",
        "state_fips": "15",
        "census_region": "West",
        "rpp_all_items": 110.0,
        "purchasing_power_multiplier": 0.9090909090909091,
        "cost_tier": "very_high",
        "adjusted_30k": 27272.73,
        "adjusted_50k": 45454.55,
        "adjusted_75k": 68181.82,
        "adjusted_100k": 90909.09,
        "verification_status": "bea_official",
        "data_year": 2024,
    },
    "IA": {
        "state_name": "Iowa",
        "state_abbr": "IA",
        "state_fips": "19",
        "census_region": "Midwest",
        "rpp_all_items": 87.8,
        "purchasing_power_multiplier": 1.1389521640091116,
        "cost_tier": "very_low",
        "adjusted_30k": 34168.56,
        "adjusted_50k": 56947.61,
        "adjusted_75k": 85421.41,
        "adjusted_100k": 113895.22,
        "verification_status": "bea_official",
        "data_year": 2024,
    },
    "MS": {
        "state_name": "Mississippi",
        "state_abbr": "MS",
        "state_fips": "28",
        "census_region": "South",
        "rpp_all_items": 87.0,
        "purchasing_power_multiplier": 1.1494252873563218,
        "cost_tier": "very_low",
        "adjusted_30k": 34482.76,
        "adjusted_50k": 57471.26,
        "adjusted_75k": 86206.9,
        "adjusted_100k": 114942.53,
        "verification_status": "bea_official",
        "data_year": 2024,
    },
    "NJ": {
        "state_name": "New Jersey",
        "state_abbr": "NJ",
        "state_fips": "34",
        "census_region": "Northeast",
        "rpp_all_items": 108.8,
        "purchasing_power_multiplier": 0.9191176470588236,
        "cost_tier": "very_high",
        "adjusted_30k": 27573.53,
        "adjusted_50k": 45955.88,
        "adjusted_75k": 68933.82,
        "adjusted_100k": 91911.76,
        "verification_status": "bea_official",
        "data_year": 2024,
    },
    "OK": {
        "state_name": "Oklahoma",
        "state_abbr": "OK",
        "state_fips": "40",
        "census_region": "South",
        "rpp_all_items": 87.8,
        "purchasing_power_multiplier": 1.1389521640091116,
        "cost_tier": "very_low",
        "adjusted_30k": 34168.56,
        "adjusted_50k": 56947.61,
        "adjusted_75k": 85421.41,
        "adjusted_100k": 113895.22,
        "verification_status": "bea_official",
        "data_year": 2024,
    },
}

ESTIMATE_TX_ROW = {
    "state_name": "Texas",
    "state_abbr": "TX",
    "state_fips": "48",
    "census_region": "South",
    "rpp_all_items": 97.4,
    "purchasing_power_multiplier": 1.0266940451745379,
    "cost_tier": "average",
    "adjusted_30k": 30800.82,
    "adjusted_50k": 51334.70,
    "adjusted_75k": 77002.05,
    "adjusted_100k": 102669.40,
    "verification_status": "estimate",
    "data_year": 2024,
}


def _make_server():
    """Create a FutureProofMCPServer with mocked catalog (no real Iceberg)."""
    server = FutureProofMCPServer.__new__(FutureProofMCPServer)
    server.warehouse_path = "/tmp/fake"
    server.catalog_path = "/tmp/fake.db"
    server.grounding_docs_path = None
    server.server_name = "test"
    server.formatter = None
    server.anomaly_checker = None
    server.system_prompt = None
    server._catalog = MagicMock()
    return server


def _patch_rows(server, *rows):
    """Patch query_iceberg_simple to return the supplied rows."""
    return patch.object(
        server,
        "query_iceberg_simple",
        return_value=list(rows),
    )


# ---------------------------------------------------------------------------
# State input normalizer (pure function tests)
# ---------------------------------------------------------------------------


class TestStateInputNormalizer:
    """Unit tests for the pure normalize_state_input function."""

    def test_fips_passthrough(self):
        assert normalize_state_input("06") == "06"

    def test_fips_single_digit_rejected(self):
        # "6" is not a valid FIPS code — FIPS codes are always 2 digits.
        assert normalize_state_input("6") is None

    def test_usps_uppercase(self):
        assert normalize_state_input("CA") == "06"

    def test_usps_lowercase(self):
        assert normalize_state_input("ca") == "06"

    def test_usps_mixed_case(self):
        assert normalize_state_input("Ca") == "06"

    def test_full_name_exact(self):
        assert normalize_state_input("California") == "06"

    def test_full_name_lowercase(self):
        assert normalize_state_input("california") == "06"

    def test_full_name_uppercase(self):
        assert normalize_state_input("CALIFORNIA") == "06"

    def test_full_name_mixed_whitespace(self):
        assert normalize_state_input("  California  ") == "06"

    def test_district_of_columbia_fips(self):
        assert normalize_state_input("11") == "11"

    def test_district_of_columbia_usps(self):
        assert normalize_state_input("DC") == "11"

    def test_district_of_columbia_name(self):
        assert normalize_state_input("District of Columbia") == "11"
        assert normalize_state_input("district of columbia") == "11"

    def test_unknown_state(self):
        assert normalize_state_input("Xanadu") is None

    def test_puerto_rico_not_in_51_set(self):
        assert normalize_state_input("PR") is None
        assert normalize_state_input("Puerto Rico") is None

    def test_empty_string(self):
        assert normalize_state_input("") is None

    def test_whitespace_only(self):
        assert normalize_state_input("   ") is None

    def test_none_input(self):
        assert normalize_state_input(None) is None

    def test_non_string_input(self):
        assert normalize_state_input(6) is None
        assert normalize_state_input(["CA"]) is None

    def test_all_51_fips_codes_roundtrip(self):
        """Every FIPS code in FIPS_TO_USPS normalizes to itself."""
        from silver._us_state_reference import FIPS_TO_USPS

        for fips in FIPS_TO_USPS:
            assert normalize_state_input(fips) == fips

    def test_all_51_usps_codes_roundtrip(self):
        """Every USPS code normalizes to the correct FIPS."""
        from silver._us_state_reference import FIPS_TO_USPS

        for fips, usps in FIPS_TO_USPS.items():
            assert normalize_state_input(usps) == fips
            assert normalize_state_input(usps.lower()) == fips


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


class TestToolRegistration:
    def test_tool_is_registered(self):
        server = _make_server()
        names = [t.name for t in server.get_tools()]
        assert "get_regional_price_parity" in names

    def test_tool_requires_state(self):
        server = _make_server()
        tool = next(
            t for t in server.get_tools() if t.name == "get_regional_price_parity"
        )
        assert "state" in tool.input_schema["required"]

    def test_verified_only_defaults_to_false(self):
        server = _make_server()
        tool = next(
            t for t in server.get_tools() if t.name == "get_regional_price_parity"
        )
        props = tool.input_schema["properties"]
        assert props["verified_only"]["default"] is False


# ---------------------------------------------------------------------------
# All 8 BEA-verified states — exact cost_tier and adjusted_50k from Gold
# ---------------------------------------------------------------------------


class TestAllBeaVerifiedStates:
    """Every BEA-verified state returns correct cost_tier + adjusted_50k."""

    @pytest.mark.parametrize(
        "usps,expected_cost_tier,expected_adj_50k",
        [
            ("AR", "very_low", 57537.4),
            ("CA", "very_high", 45167.12),
            ("DC", "very_high", 45495.91),
            ("HI", "very_high", 45454.55),
            ("IA", "very_low", 56947.61),
            ("MS", "very_low", 57471.26),
            ("NJ", "very_high", 45955.88),
            ("OK", "very_low", 56947.61),
        ],
    )
    def test_verified_state_payload(
        self, usps, expected_cost_tier, expected_adj_50k
    ):
        server = _make_server()
        with _patch_rows(server, VERIFIED_ROWS[usps]):
            result = server._handle_get_regional_price_parity({"state": usps})
        assert result["data"] is not None
        assert result["data"]["cost_tier"] == expected_cost_tier
        assert result["data"]["adjusted_examples"]["50k"] == expected_adj_50k
        assert result["data"]["data_source"] == "bea_official"


# ---------------------------------------------------------------------------
# Response shape and full precision
# ---------------------------------------------------------------------------


class TestResponseShape:
    def test_adjusted_examples_struct(self):
        server = _make_server()
        with _patch_rows(server, VERIFIED_ROWS["CA"]):
            result = server._handle_get_regional_price_parity({"state": "CA"})
        data = result["data"]
        assert "adjusted_examples" in data
        assert set(data["adjusted_examples"].keys()) == {"30k", "50k", "75k", "100k"}
        assert data["adjusted_examples"]["30k"] == 27100.27
        assert data["adjusted_examples"]["100k"] == 90334.24

    def test_verification_status_renamed_to_data_source(self):
        server = _make_server()
        with _patch_rows(server, VERIFIED_ROWS["CA"]):
            result = server._handle_get_regional_price_parity({"state": "CA"})
        assert "verification_status" not in result["data"]
        assert result["data"]["data_source"] == "bea_official"

    def test_full_precision_purchasing_power_multiplier(self):
        """Advisory #1: response must preserve full precision, not rounded."""
        server = _make_server()
        with _patch_rows(server, VERIFIED_ROWS["CA"]):
            result = server._handle_get_regional_price_parity({"state": "CA"})
        assert result["data"]["purchasing_power_multiplier"] == 0.9033423667570009

    def test_governance_metadata_attached(self):
        server = _make_server()
        with _patch_rows(server, VERIFIED_ROWS["CA"]):
            result = server._handle_get_regional_price_parity({"state": "CA"})
        assert "governance" in result
        assert result["governance"]["table"] == RPP_TABLE_NAME

    def test_governance_quality_tier_partial_verification(self):
        """MCP-BEA-002: every success response carries quality_tier."""
        server = _make_server()
        with _patch_rows(server, VERIFIED_ROWS["CA"]):
            result = server._handle_get_regional_price_parity({"state": "CA"})
        assert result["governance"]["quality_tier"] == "partial_verification"

    def test_governance_owner_attached(self):
        """Spec example governance payload requires an owner field."""
        server = _make_server()
        with _patch_rows(server, VERIFIED_ROWS["CA"]):
            result = server._handle_get_regional_price_parity({"state": "CA"})
        assert "owner" in result["governance"]
        assert result["governance"]["owner"]

    def test_governance_quality_tier_on_estimate_row(self):
        """Estimate rows also carry quality_tier=partial_verification."""
        server = _make_server()
        with _patch_rows(server, ESTIMATE_TX_ROW):
            result = server._handle_get_regional_price_parity({"state": "TX"})
        assert result["governance"]["quality_tier"] == "partial_verification"

    def test_governance_quality_tier_on_strict_mode_refusal(self):
        """Even null/refusal responses attach the tier."""
        server = _make_server()
        with _patch_rows(server, ESTIMATE_TX_ROW):
            result = server._handle_get_regional_price_parity(
                {"state": "TX", "verified_only": True}
            )
        assert result["governance"]["quality_tier"] == "partial_verification"

    def test_row_count_is_one(self):
        server = _make_server()
        with _patch_rows(server, VERIFIED_ROWS["CA"]):
            result = server._handle_get_regional_price_parity({"state": "CA"})
        assert result["row_count"] == 1


# ---------------------------------------------------------------------------
# Estimated states
# ---------------------------------------------------------------------------


class TestEstimatedStates:
    def test_estimate_row_returned_by_default(self):
        server = _make_server()
        with _patch_rows(server, ESTIMATE_TX_ROW):
            result = server._handle_get_regional_price_parity({"state": "TX"})
        assert result["data"]["data_source"] == "estimate"
        assert result["data"]["state_name"] == "Texas"


# ---------------------------------------------------------------------------
# Strict mode (verified_only)
# ---------------------------------------------------------------------------


class TestStrictMode:
    def test_strict_mode_returns_verified_state(self):
        server = _make_server()
        with _patch_rows(server, VERIFIED_ROWS["CA"]):
            result = server._handle_get_regional_price_parity(
                {"state": "CA", "verified_only": True}
            )
        assert result["data"] is not None
        assert result["data"]["data_source"] == "bea_official"

    def test_strict_mode_refuses_estimate(self):
        server = _make_server()
        with _patch_rows(server, ESTIMATE_TX_ROW):
            result = server._handle_get_regional_price_parity(
                {"state": "TX", "verified_only": True}
            )
        assert result["data"] is None
        assert "estimate" in result["message"]
        assert "strict mode" in result["message"].lower()
        assert "Texas" in result["message"]

    def test_strict_mode_refusal_has_governance(self):
        server = _make_server()
        with _patch_rows(server, ESTIMATE_TX_ROW):
            result = server._handle_get_regional_price_parity(
                {"state": "TX", "verified_only": True}
            )
        assert "governance" in result

    def test_strict_mode_all_8_verified_states_succeed(self):
        """All 8 BEA-verified states return data in strict mode."""
        for usps, row in VERIFIED_ROWS.items():
            server = _make_server()
            with _patch_rows(server, row):
                result = server._handle_get_regional_price_parity(
                    {"state": usps, "verified_only": True}
                )
            assert result["data"] is not None, f"{usps} should succeed"
            assert result["data"]["data_source"] == "bea_official"


# ---------------------------------------------------------------------------
# Null cases (unknown / missing / empty input)
# ---------------------------------------------------------------------------


class TestNullCases:
    def test_unknown_state_returns_null(self):
        server = _make_server()
        result = server._handle_get_regional_price_parity({"state": "Xanadu"})
        assert result["data"] is None
        assert "Unknown state" in result["message"]
        assert "Xanadu" in result["message"]

    def test_empty_state_returns_null(self):
        server = _make_server()
        result = server._handle_get_regional_price_parity({"state": ""})
        assert result["data"] is None
        assert "Unknown state" in result["message"]

    def test_missing_state_key_returns_null(self):
        server = _make_server()
        result = server._handle_get_regional_price_parity({})
        assert result["data"] is None
        assert "Unknown state" in result["message"]

    def test_puerto_rico_rejected(self):
        server = _make_server()
        result = server._handle_get_regional_price_parity({"state": "Puerto Rico"})
        assert result["data"] is None
        assert "Unknown state" in result["message"]

    def test_non_string_state_rejected(self):
        server = _make_server()
        result = server._handle_get_regional_price_parity({"state": 6})
        assert result["data"] is None

    def test_no_data_row_returned(self):
        server = _make_server()
        # Simulate a valid FIPS lookup that returns zero rows from Gold
        with _patch_rows(server):  # no rows
            result = server._handle_get_regional_price_parity({"state": "CA"})
        assert result["data"] is None
        assert "No regional price parity data" in result["message"]


# ---------------------------------------------------------------------------
# Query delegation
# ---------------------------------------------------------------------------


class TestQueryDelegation:
    def test_queries_correct_table(self):
        server = _make_server()
        with patch.object(
            server, "query_iceberg_simple", return_value=[VERIFIED_ROWS["CA"]]
        ) as mock_q:
            server._handle_get_regional_price_parity({"state": "CA"})
        mock_q.assert_called_once_with(
            RPP_TABLE_NAME,
            filters={"state_fips": "06"},
            columns=RPP_QUERY_FIELDS,
            limit=1,
        )

    def test_all_three_input_forms_same_query(self):
        """FIPS, USPS, and full name all produce the same Gold query."""
        for state_input in ("06", "CA", "California", "california", "ca"):
            server = _make_server()
            with patch.object(
                server,
                "query_iceberg_simple",
                return_value=[VERIFIED_ROWS["CA"]],
            ) as mock_q:
                server._handle_get_regional_price_parity({"state": state_input})
            args, kwargs = mock_q.call_args
            assert kwargs["filters"] == {"state_fips": "06"}
