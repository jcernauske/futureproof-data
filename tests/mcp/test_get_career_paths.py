"""Tests for the get_career_paths MCP tool.

Covers tool registration, valid unitid+cipcode lookup, sort order by
stats_available_count DESC, unitid and cipcode validation, zero-result
handling, query error propagation, and governance metadata attachment.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from mcp_server.futureproof_server import (
    CAREER_PATHS_RESPONSE_FIELDS,
    CAREER_PATHS_TABLE,
    FutureProofMCPServer,
)


def _make_row(
    unitid: int,
    cipcode: str,
    soc_code: str,
    occupation_title: str,
    stats_available_count: int,
    **overrides,
) -> dict:
    row = {
        "unitid": unitid,
        "institution_name": "Indiana State University",
        "cipcode": cipcode,
        "program_name": "Business Administration",
        "cip_family_name": "Business, Management, Marketing",
        "soc_code": soc_code,
        "occupation_title": occupation_title,
        "soc_major_group_name": "Business and Financial Operations",
        "stat_ern": 6,
        "stat_roi": 5,
        "stat_res": 3,
        "stat_grw": 7,
        "stat_hmn": 5,
        "boss_ai_score": 8,
        "boss_loans_score": 5,
        "boss_market_score": 4,
        "boss_burnout_score": 6,
        "boss_ceiling_score": 3,
        "earnings_1yr_median": 55000.0,
        "earnings_1yr_p25": 42000.0,
        "earnings_1yr_p75": 72000.0,
        "debt_median": 25000.0,
        "debt_to_earnings_annual": 0.45,
        "confidence_tier_program": "high",
        "median_annual_wage": 98580.0,
        "growth_category": "Faster than average",
        "employment_current": 376950,
        "education_level_name": "Bachelor's degree",
        "top_5_activities": "[]",
        "top_human_activities": "[]",
        "burnout_drivers": "[]",
        "match_quality": "high",
        "stats_available_count": stats_available_count,
        "bosses_available_count": 5,
        "overall_confidence": "high",
    }
    row.update(overrides)
    return row


BIZ_ROWS = [
    _make_row(151801, "52.02", "13-2051", "Financial Analyst", 5),
    _make_row(151801, "52.02", "11-1021", "General and Operations Manager", 4),
    _make_row(151801, "52.02", "13-1161", "Market Research Analyst", 3),
]


def _make_server():
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


class TestToolRegistration:
    def test_tool_is_registered(self):
        server = _make_server()
        names = [t.name for t in server.get_tools()]
        assert "get_career_paths" in names

    def test_requires_unitid_and_cipcode(self):
        server = _make_server()
        tool = [t for t in server.get_tools() if t.name == "get_career_paths"][0]
        assert set(tool.input_schema["required"]) == {"unitid", "cipcode"}


class TestValidLookup:
    def test_returns_all_career_rows(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=BIZ_ROWS):
            result = server._handle_get_career_paths(
                {"unitid": 151801, "cipcode": "52.02"}
            )
        assert result["row_count"] == 3

    def test_sorted_by_stats_count_desc(self):
        server = _make_server()
        shuffled = [BIZ_ROWS[2], BIZ_ROWS[0], BIZ_ROWS[1]]
        with patch.object(server, "query_iceberg_simple", return_value=shuffled):
            result = server._handle_get_career_paths(
                {"unitid": 151801, "cipcode": "52.02"}
            )
        counts = [r["stats_available_count"] for r in result["data"]]
        assert counts == [5, 4, 3]

    def test_query_uses_composite_filter(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=BIZ_ROWS) as mq:
            server._handle_get_career_paths(
                {"unitid": 151801, "cipcode": "52.02"}
            )
        _, kwargs = mq.call_args
        assert kwargs.get("filters") == {"unitid": 151801, "cipcode": "52.02"}

    def test_response_contains_all_fields(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=BIZ_ROWS):
            result = server._handle_get_career_paths(
                {"unitid": 151801, "cipcode": "52.02"}
            )
        for field in CAREER_PATHS_RESPONSE_FIELDS:
            assert field in result["data"][0], f"Missing field: {field}"


class TestValidation:
    def test_missing_unitid_returns_null(self):
        server = _make_server()
        result = server._handle_get_career_paths({"cipcode": "52.02"})
        assert result["data"] is None
        assert "unitid" in result["message"]

    def test_zero_unitid_rejected(self):
        server = _make_server()
        result = server._handle_get_career_paths({"unitid": 0, "cipcode": "52.02"})
        assert result["data"] is None
        assert "unitid" in result["message"]

    def test_negative_unitid_rejected(self):
        server = _make_server()
        result = server._handle_get_career_paths({"unitid": -1, "cipcode": "52.02"})
        assert result["data"] is None

    def test_boolean_unitid_rejected(self):
        """bool is an int subclass; reject to avoid True -> unitid=1."""
        server = _make_server()
        result = server._handle_get_career_paths({"unitid": True, "cipcode": "52.02"})
        assert result["data"] is None

    def test_string_digits_unitid_accepted(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=BIZ_ROWS) as mq:
            server._handle_get_career_paths(
                {"unitid": "151801", "cipcode": "52.02"}
            )
        _, kwargs = mq.call_args
        assert kwargs["filters"]["unitid"] == 151801

    def test_missing_cipcode_returns_null(self):
        server = _make_server()
        result = server._handle_get_career_paths({"unitid": 151801})
        assert result["data"] is None
        assert "cipcode" in result["message"]

    def test_malformed_cipcode_rejected(self):
        server = _make_server()
        result = server._handle_get_career_paths(
            {"unitid": 151801, "cipcode": "52"}
        )
        assert result["data"] is None
        assert "cipcode" in result["message"]

    def test_full_cipcode_accepted(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=BIZ_ROWS):
            result = server._handle_get_career_paths(
                {"unitid": 151801, "cipcode": "52.0201"}
            )
        assert result["row_count"] == 3


class TestNullCases:
    def test_no_results_returns_null_with_message(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[]):
            result = server._handle_get_career_paths(
                {"unitid": 151801, "cipcode": "99.99"}
            )
        assert result["data"] is None
        assert "99.99" in result["message"]
        assert "151801" in result["message"]

    def test_query_error_returns_null(self):
        server = _make_server()
        err = [{"error": "Cannot query consumable.program_career_paths"}]
        with patch.object(server, "query_iceberg_simple", return_value=err):
            result = server._handle_get_career_paths(
                {"unitid": 151801, "cipcode": "52.02"}
            )
        assert result["data"] is None


class TestGovernance:
    def test_governance_attached_on_success(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=BIZ_ROWS):
            result = server._handle_get_career_paths(
                {"unitid": 151801, "cipcode": "52.02"}
            )
        assert result["governance"]["table"] == CAREER_PATHS_TABLE

    def test_governance_attached_on_null(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[]):
            result = server._handle_get_career_paths(
                {"unitid": 151801, "cipcode": "99.99"}
            )
        assert result["governance"]["table"] == CAREER_PATHS_TABLE
