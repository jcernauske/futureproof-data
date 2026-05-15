"""Tests for the rank_states_by_purchasing_power MCP tool.

Covers:
    * Tool registration and schema (only `salary` is required)
    * Sort order: cheapest_first (default) ranks by purchasing power desc
    * top_n truncation
    * order='expensive_first' inverts
    * verified_only filters out estimate rows
    * Salary validation: negative, zero, non-numeric, NaN/inf, bool, None
    * top_n validation: zero / negative / bool / non-int rejection
    * order validation: rejects unknown values
    * Empty data → structured null
    * Governance metadata attached
"""

from __future__ import annotations

from unittest.mock import patch

from mcp_server.futureproof_server import RPP_TABLE_NAME

from tests.mcp.test_get_regional_price_parity import (
    ESTIMATE_TX_ROW,
    VERIFIED_ROWS,
    _make_server,
)


def _patch_rows(server, rows):
    return patch.object(server, "query_iceberg_simple", return_value=rows)


class TestToolRegistration:
    def test_tool_is_registered(self):
        server = _make_server()
        names = [t.name for t in server.get_tools()]
        assert "rank_states_by_purchasing_power" in names

    def test_only_salary_is_required(self):
        server = _make_server()
        tool = next(
            t for t in server.get_tools()
            if t.name == "rank_states_by_purchasing_power"
        )
        required = tool.input_schema["required"]
        assert required == ["salary"]


class TestRanking:
    def test_default_order_is_cheapest_first(self):
        server = _make_server()
        rows = [VERIFIED_ROWS["CA"], VERIFIED_ROWS["AR"], VERIFIED_ROWS["DC"]]
        with _patch_rows(server, rows):
            result = server._handle_rank_states_by_purchasing_power({"salary": 65000})
        data = result["data"]
        states = data["states"]
        # AR has highest purchasing_power_multiplier → appears first.
        assert states[0]["state_abbr"] == "AR"
        # Each row has the cheapest-first invariant.
        for a, b in zip(states, states[1:]):
            assert a["purchasing_power_multiplier"] >= b["purchasing_power_multiplier"]

    def test_expensive_first_inverts(self):
        server = _make_server()
        rows = [VERIFIED_ROWS["CA"], VERIFIED_ROWS["AR"], VERIFIED_ROWS["DC"]]
        with _patch_rows(server, rows):
            result = server._handle_rank_states_by_purchasing_power(
                {"salary": 65000, "order": "expensive_first"}
            )
        states = result["data"]["states"]
        assert states[0]["state_abbr"] == "CA"  # lowest PPM, highest cost
        for a, b in zip(states, states[1:]):
            assert a["purchasing_power_multiplier"] <= b["purchasing_power_multiplier"]

    def test_top_n_truncates(self):
        server = _make_server()
        rows = list(VERIFIED_ROWS.values())
        with _patch_rows(server, rows):
            result = server._handle_rank_states_by_purchasing_power(
                {"salary": 50000, "top_n": 2}
            )
        assert len(result["data"]["states"]) == 2
        assert result["row_count"] == 2

    def test_top_n_null_returns_all(self):
        server = _make_server()
        rows = list(VERIFIED_ROWS.values())
        with _patch_rows(server, rows):
            result = server._handle_rank_states_by_purchasing_power(
                {"salary": 50000, "top_n": None}
            )
        assert len(result["data"]["states"]) == len(rows)

    def test_adjusted_salary_is_full_precision_rounded_to_cents(self):
        server = _make_server()
        with _patch_rows(server, [VERIFIED_ROWS["CA"]]):
            result = server._handle_rank_states_by_purchasing_power({"salary": 65000})
        ca = result["data"]["states"][0]
        # 65000 * 0.9033423667570009 = 58717.25 (rounded to 2dp)
        assert ca["adjusted_salary"] == 58717.25

    def test_response_carries_salary_and_order_in_payload(self):
        server = _make_server()
        with _patch_rows(server, [VERIFIED_ROWS["CA"]]):
            result = server._handle_rank_states_by_purchasing_power(
                {"salary": 50000, "order": "expensive_first"}
            )
        assert result["data"]["salary"] == 50000
        assert result["data"]["order"] == "expensive_first"


class TestVerifiedOnly:
    def test_verified_only_drops_estimate_rows(self):
        server = _make_server()
        rows = [VERIFIED_ROWS["CA"], ESTIMATE_TX_ROW, VERIFIED_ROWS["AR"]]
        with _patch_rows(server, rows):
            result = server._handle_rank_states_by_purchasing_power(
                {"salary": 65000, "verified_only": True}
            )
        states = result["data"]["states"]
        assert all(s["data_source"] == "bea_official" for s in states)
        assert all(s["state_abbr"] != "TX" for s in states)

    def test_verified_only_all_estimates_returns_null(self):
        server = _make_server()
        rows = [ESTIMATE_TX_ROW]
        with _patch_rows(server, rows):
            result = server._handle_rank_states_by_purchasing_power(
                {"salary": 65000, "verified_only": True}
            )
        assert result["data"] is None
        assert "estimate" in result["message"]


class TestSalaryValidation:
    def test_zero_salary_rejected(self):
        server = _make_server()
        result = server._handle_rank_states_by_purchasing_power({"salary": 0})
        assert result["data"] is None

    def test_negative_salary_rejected(self):
        server = _make_server()
        result = server._handle_rank_states_by_purchasing_power({"salary": -1000})
        assert result["data"] is None

    def test_huge_salary_rejected(self):
        server = _make_server()
        result = server._handle_rank_states_by_purchasing_power(
            {"salary": 99_999_999}
        )
        assert result["data"] is None

    def test_string_salary_rejected(self):
        server = _make_server()
        result = server._handle_rank_states_by_purchasing_power(
            {"salary": "65000"}
        )
        assert result["data"] is None

    def test_bool_salary_rejected(self):
        server = _make_server()
        result = server._handle_rank_states_by_purchasing_power({"salary": True})
        assert result["data"] is None


class TestTopNValidation:
    def test_zero_top_n_rejected(self):
        server = _make_server()
        result = server._handle_rank_states_by_purchasing_power(
            {"salary": 50000, "top_n": 0}
        )
        assert result["data"] is None

    def test_negative_top_n_rejected(self):
        server = _make_server()
        result = server._handle_rank_states_by_purchasing_power(
            {"salary": 50000, "top_n": -3}
        )
        assert result["data"] is None

    def test_bool_top_n_rejected(self):
        server = _make_server()
        result = server._handle_rank_states_by_purchasing_power(
            {"salary": 50000, "top_n": True}
        )
        assert result["data"] is None

    def test_float_top_n_rejected(self):
        server = _make_server()
        result = server._handle_rank_states_by_purchasing_power(
            {"salary": 50000, "top_n": 3.5}
        )
        assert result["data"] is None


class TestOrderValidation:
    def test_unknown_order_rejected(self):
        server = _make_server()
        result = server._handle_rank_states_by_purchasing_power(
            {"salary": 50000, "order": "alphabetical"}
        )
        assert result["data"] is None


class TestEmptyAndGovernance:
    def test_no_rows_returns_structured_null(self):
        server = _make_server()
        with _patch_rows(server, []):
            result = server._handle_rank_states_by_purchasing_power(
                {"salary": 50000}
            )
        assert result["data"] is None
        assert "available" in result["message"].lower()

    def test_query_error_returns_structured_null(self):
        server = _make_server()
        with _patch_rows(server, [{"error": "boom"}]):
            result = server._handle_rank_states_by_purchasing_power(
                {"salary": 50000}
            )
        assert result["data"] is None

    def test_governance_metadata_attached_on_success(self):
        server = _make_server()
        with _patch_rows(server, [VERIFIED_ROWS["CA"]]):
            result = server._handle_rank_states_by_purchasing_power(
                {"salary": 50000}
            )
        # enrich_response adds source_table; attach_governance adds it too.
        assert "source_table" in result or RPP_TABLE_NAME in str(result)
