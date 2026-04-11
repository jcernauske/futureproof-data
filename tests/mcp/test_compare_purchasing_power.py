"""Tests for the compare_purchasing_power MCP tool.

Covers:
    * Arithmetic matches the spec canonical values for CA vs IA at $65K
      (58717.25 vs 74031.89, diff 15314.64, diff_pct 26.08)
    * All common salary levels ($30K, $50K, $75K, $100K)
    * Salary validation: negative, zero, > 10M, non-numeric, None, bool,
      NaN, inf
    * Same-state-twice rejection (after normalization)
    * Strict mode positive cases and mixed-provenance refusal
    * Unknown state_a / state_b rejection
    * Full-precision purchasing_power_multiplier in both sides of the
      response (pre-review Advisory #1)
    * Governance metadata attached
    * Tool registration
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from mcp_server.futureproof_server import RPP_TABLE_NAME

from tests.mcp.test_get_regional_price_parity import (
    ESTIMATE_TX_ROW,
    VERIFIED_ROWS,
    _make_server,
)


def _patch_fetch(server, row_a, row_b):
    """Patch _fetch_rpp_row to return row_a then row_b."""
    return patch.object(
        server, "_fetch_rpp_row", side_effect=[row_a, row_b]
    )


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


class TestToolRegistration:
    def test_tool_is_registered(self):
        server = _make_server()
        names = [t.name for t in server.get_tools()]
        assert "compare_purchasing_power" in names

    def test_requires_salary_state_a_state_b(self):
        server = _make_server()
        tool = next(
            t for t in server.get_tools() if t.name == "compare_purchasing_power"
        )
        required = tool.input_schema["required"]
        assert "salary" in required
        assert "state_a" in required
        assert "state_b" in required


# ---------------------------------------------------------------------------
# Canonical spec arithmetic: CA vs IA at $65K
# ---------------------------------------------------------------------------


class TestCanonicalCaVsIa:
    def test_ca_vs_ia_65k_spec_canonical(self):
        server = _make_server()
        with _patch_fetch(server, VERIFIED_ROWS["CA"], VERIFIED_ROWS["IA"]):
            result = server._handle_compare_purchasing_power(
                {"salary": 65000, "state_a": "CA", "state_b": "IA"}
            )
        data = result["data"]
        assert data["state_a"]["adjusted_salary"] == 58717.25
        assert data["state_b"]["adjusted_salary"] == 74031.89
        assert data["difference"] == 15314.64
        assert data["difference_pct"] == 26.08

    def test_ca_vs_ia_65k_float_input(self):
        server = _make_server()
        with _patch_fetch(server, VERIFIED_ROWS["CA"], VERIFIED_ROWS["IA"]):
            result = server._handle_compare_purchasing_power(
                {"salary": 65000.0, "state_a": "CA", "state_b": "IA"}
            )
        assert result["data"]["state_a"]["adjusted_salary"] == 58717.25

    def test_state_names_accepted(self):
        server = _make_server()
        with _patch_fetch(server, VERIFIED_ROWS["CA"], VERIFIED_ROWS["IA"]):
            result = server._handle_compare_purchasing_power(
                {
                    "salary": 65000,
                    "state_a": "California",
                    "state_b": "Iowa",
                }
            )
        assert result["data"]["state_a"]["state_name"] == "California"

    def test_fips_accepted(self):
        server = _make_server()
        with _patch_fetch(server, VERIFIED_ROWS["CA"], VERIFIED_ROWS["IA"]):
            result = server._handle_compare_purchasing_power(
                {"salary": 65000, "state_a": "06", "state_b": "19"}
            )
        assert result["data"]["state_a"]["state_name"] == "California"


# ---------------------------------------------------------------------------
# Common salary levels
# ---------------------------------------------------------------------------


class TestCommonSalaries:
    @pytest.mark.parametrize("salary", [30000, 50000, 75000, 100000, 65000])
    def test_ca_vs_ia_various_salaries(self, salary):
        server = _make_server()
        with _patch_fetch(server, VERIFIED_ROWS["CA"], VERIFIED_ROWS["IA"]):
            result = server._handle_compare_purchasing_power(
                {"salary": salary, "state_a": "CA", "state_b": "IA"}
            )
        data = result["data"]
        # Arithmetic consistency: adjusted_a matches round(salary*ppm, 2)
        expected_a = round(salary * VERIFIED_ROWS["CA"]["purchasing_power_multiplier"], 2)
        expected_b = round(salary * VERIFIED_ROWS["IA"]["purchasing_power_multiplier"], 2)
        assert data["state_a"]["adjusted_salary"] == expected_a
        assert data["state_b"]["adjusted_salary"] == expected_b
        assert data["difference"] == round(expected_b - expected_a, 2)


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------


class TestResponseShape:
    def test_row_count_is_two(self):
        server = _make_server()
        with _patch_fetch(server, VERIFIED_ROWS["CA"], VERIFIED_ROWS["IA"]):
            result = server._handle_compare_purchasing_power(
                {"salary": 65000, "state_a": "CA", "state_b": "IA"}
            )
        assert result["row_count"] == 2

    def test_full_precision_multiplier_preserved(self):
        """Advisory #1: both sides carry full-precision ppm, not rounded."""
        server = _make_server()
        with _patch_fetch(server, VERIFIED_ROWS["CA"], VERIFIED_ROWS["IA"]):
            result = server._handle_compare_purchasing_power(
                {"salary": 65000, "state_a": "CA", "state_b": "IA"}
            )
        assert (
            result["data"]["state_a"]["purchasing_power_multiplier"]
            == 0.9033423667570009
        )
        assert (
            result["data"]["state_b"]["purchasing_power_multiplier"]
            == 1.1389521640091116
        )

    def test_data_source_on_both_sides(self):
        server = _make_server()
        with _patch_fetch(server, VERIFIED_ROWS["CA"], VERIFIED_ROWS["IA"]):
            result = server._handle_compare_purchasing_power(
                {"salary": 65000, "state_a": "CA", "state_b": "IA"}
            )
        assert result["data"]["state_a"]["data_source"] == "bea_official"
        assert result["data"]["state_b"]["data_source"] == "bea_official"

    def test_governance_metadata_attached(self):
        server = _make_server()
        with _patch_fetch(server, VERIFIED_ROWS["CA"], VERIFIED_ROWS["IA"]):
            result = server._handle_compare_purchasing_power(
                {"salary": 65000, "state_a": "CA", "state_b": "IA"}
            )
        assert result["governance"]["table"] == RPP_TABLE_NAME

    def test_governance_quality_tier_partial_verification(self):
        """MCP-BEA-002: every success response carries quality_tier."""
        server = _make_server()
        with _patch_fetch(server, VERIFIED_ROWS["CA"], VERIFIED_ROWS["IA"]):
            result = server._handle_compare_purchasing_power(
                {"salary": 65000, "state_a": "CA", "state_b": "IA"}
            )
        assert result["governance"]["quality_tier"] == "partial_verification"

    def test_governance_owner_attached(self):
        """Spec example governance payload requires an owner field."""
        server = _make_server()
        with _patch_fetch(server, VERIFIED_ROWS["CA"], VERIFIED_ROWS["IA"]):
            result = server._handle_compare_purchasing_power(
                {"salary": 65000, "state_a": "CA", "state_b": "IA"}
            )
        assert "owner" in result["governance"]
        assert result["governance"]["owner"]

    def test_salary_echoed_in_response(self):
        server = _make_server()
        with _patch_fetch(server, VERIFIED_ROWS["CA"], VERIFIED_ROWS["IA"]):
            result = server._handle_compare_purchasing_power(
                {"salary": 65000, "state_a": "CA", "state_b": "IA"}
            )
        assert result["data"]["salary"] == 65000.0


# ---------------------------------------------------------------------------
# Salary validation
# ---------------------------------------------------------------------------


class TestSalaryValidation:
    @pytest.mark.parametrize(
        "bad",
        [-5, 0, -100, -1.5, 10_000_000, 10_000_001, 20_000_000],
    )
    def test_invalid_numeric_salary(self, bad):
        server = _make_server()
        result = server._handle_compare_purchasing_power(
            {"salary": bad, "state_a": "CA", "state_b": "IA"}
        )
        assert result["data"] is None
        assert "salary must be a positive number" in result["message"]

    @pytest.mark.parametrize("bad", ["65000", "abc", None, [], {}, True, False])
    def test_non_numeric_salary(self, bad):
        server = _make_server()
        result = server._handle_compare_purchasing_power(
            {"salary": bad, "state_a": "CA", "state_b": "IA"}
        )
        assert result["data"] is None
        assert "salary must be a positive number" in result["message"]

    def test_nan_salary(self):
        server = _make_server()
        result = server._handle_compare_purchasing_power(
            {"salary": float("nan"), "state_a": "CA", "state_b": "IA"}
        )
        assert result["data"] is None

    def test_inf_salary(self):
        server = _make_server()
        result = server._handle_compare_purchasing_power(
            {"salary": float("inf"), "state_a": "CA", "state_b": "IA"}
        )
        assert result["data"] is None


# ---------------------------------------------------------------------------
# Same state twice
# ---------------------------------------------------------------------------


class TestSameStateRejection:
    def test_same_usps_twice(self):
        server = _make_server()
        result = server._handle_compare_purchasing_power(
            {"salary": 65000, "state_a": "CA", "state_b": "CA"}
        )
        assert result["data"] is None
        assert "different states" in result["message"]

    def test_same_state_different_forms(self):
        """USPS vs full name vs FIPS normalize to same FIPS -> reject."""
        server = _make_server()
        result = server._handle_compare_purchasing_power(
            {"salary": 65000, "state_a": "CA", "state_b": "California"}
        )
        assert result["data"] is None
        assert "different states" in result["message"]

    def test_same_state_fips_and_name(self):
        server = _make_server()
        result = server._handle_compare_purchasing_power(
            {"salary": 65000, "state_a": "06", "state_b": "California"}
        )
        assert result["data"] is None
        assert "different states" in result["message"]


# ---------------------------------------------------------------------------
# Unknown state rejection
# ---------------------------------------------------------------------------


class TestUnknownStateRejection:
    def test_unknown_state_a(self):
        server = _make_server()
        result = server._handle_compare_purchasing_power(
            {"salary": 65000, "state_a": "Xanadu", "state_b": "IA"}
        )
        assert result["data"] is None
        assert "Unknown state" in result["message"]

    def test_unknown_state_b(self):
        server = _make_server()
        result = server._handle_compare_purchasing_power(
            {"salary": 65000, "state_a": "CA", "state_b": "Atlantis"}
        )
        assert result["data"] is None
        assert "Unknown state" in result["message"]

    def test_missing_state_a(self):
        server = _make_server()
        result = server._handle_compare_purchasing_power(
            {"salary": 65000, "state_b": "IA"}
        )
        assert result["data"] is None
        assert "Unknown state" in result["message"]


# ---------------------------------------------------------------------------
# Strict mode
# ---------------------------------------------------------------------------


class TestStrictMode:
    def test_strict_mode_two_verified_states_succeeds(self):
        server = _make_server()
        with _patch_fetch(server, VERIFIED_ROWS["CA"], VERIFIED_ROWS["IA"]):
            result = server._handle_compare_purchasing_power(
                {
                    "salary": 65000,
                    "state_a": "CA",
                    "state_b": "IA",
                    "verified_only": True,
                }
            )
        assert result["data"] is not None
        assert result["data"]["state_a"]["data_source"] == "bea_official"

    def test_strict_mode_mixed_provenance_refused(self):
        server = _make_server()
        with _patch_fetch(server, VERIFIED_ROWS["CA"], ESTIMATE_TX_ROW):
            result = server._handle_compare_purchasing_power(
                {
                    "salary": 65000,
                    "state_a": "CA",
                    "state_b": "TX",
                    "verified_only": True,
                }
            )
        assert result["data"] is None
        assert "Strict mode" in result["message"]
        assert "Texas" in result["message"]

    def test_strict_mode_estimate_in_state_a(self):
        server = _make_server()
        with _patch_fetch(server, ESTIMATE_TX_ROW, VERIFIED_ROWS["CA"]):
            result = server._handle_compare_purchasing_power(
                {
                    "salary": 65000,
                    "state_a": "TX",
                    "state_b": "CA",
                    "verified_only": True,
                }
            )
        assert result["data"] is None
        assert "Texas" in result["message"]

    def test_strict_mode_refusal_has_governance(self):
        server = _make_server()
        with _patch_fetch(server, VERIFIED_ROWS["CA"], ESTIMATE_TX_ROW):
            result = server._handle_compare_purchasing_power(
                {
                    "salary": 65000,
                    "state_a": "CA",
                    "state_b": "TX",
                    "verified_only": True,
                }
            )
        assert "governance" in result


# ---------------------------------------------------------------------------
# No-data guard
# ---------------------------------------------------------------------------


class TestNoDataGuard:
    def test_state_a_not_in_gold(self):
        server = _make_server()
        with patch.object(server, "_fetch_rpp_row", side_effect=[None, VERIFIED_ROWS["IA"]]):
            result = server._handle_compare_purchasing_power(
                {"salary": 65000, "state_a": "CA", "state_b": "IA"}
            )
        assert result["data"] is None
        assert "No regional price parity data" in result["message"]

    def test_state_b_not_in_gold(self):
        server = _make_server()
        with patch.object(server, "_fetch_rpp_row", side_effect=[VERIFIED_ROWS["CA"], None]):
            result = server._handle_compare_purchasing_power(
                {"salary": 65000, "state_a": "CA", "state_b": "IA"}
            )
        assert result["data"] is None
        assert "No regional price parity data" in result["message"]
