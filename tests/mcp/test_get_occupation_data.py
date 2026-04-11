"""Tests for the get_occupation_data MCP tool."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from mcp_server.futureproof_server import (
    OCCUPATION_DATA_RESPONSE_FIELDS,
    OCCUPATION_DATA_TABLE,
    FutureProofMCPServer,
)


SAMPLE_ROW = {
    "soc_code": "13-2051",
    "occupation_title": "Financial Analysts",
    "soc_major_group": "13-0000",
    "soc_major_group_name": "Business and Financial Operations",
    "median_annual_wage": 98580.0,
    "wage_percentile_overall": 0.86,
    "wage_percentile_education_tier": 0.72,
    "wage_tier": "high",
    "employment_current": 376950,
    "employment_projected": 404900,
    "employment_change_pct": 7.4,
    "openings_annual_avg": 29000,
    "growth_category": "Faster than average",
    "grw_score": 7,
    "grw_score_rounded": 7,
    "market_score": 6,
    "market_score_rounded": 6,
    "education_code": 5,
    "education_level_name": "Bachelor's degree",
    "work_experience_code": 0,
    "training_code": 0,
    "broad_occupation_flag": False,
    "catchall_flag": False,
}


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
        assert "get_occupation_data" in names

    def test_requires_soc_code(self):
        server = _make_server()
        tool = [t for t in server.get_tools() if t.name == "get_occupation_data"][0]
        assert "soc_code" in tool.input_schema["required"]


class TestValidLookup:
    def test_returns_single_row(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[SAMPLE_ROW]):
            result = server._handle_get_occupation_data({"soc_code": "13-2051"})
        assert result["row_count"] == 1
        assert result["data"]["soc_code"] == "13-2051"

    def test_response_contains_all_fields(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[SAMPLE_ROW]):
            result = server._handle_get_occupation_data({"soc_code": "13-2051"})
        for field in OCCUPATION_DATA_RESPONSE_FIELDS:
            assert field in result["data"], f"Missing field: {field}"

    def test_delegates_with_correct_filter(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[SAMPLE_ROW]) as mq:
            server._handle_get_occupation_data({"soc_code": "13-2051"})
        mq.assert_called_once_with(
            OCCUPATION_DATA_TABLE,
            filters={"soc_code": "13-2051"},
            columns=OCCUPATION_DATA_RESPONSE_FIELDS,
            limit=1,
        )


class TestValidation:
    def test_missing_soc_returns_required(self):
        server = _make_server()
        result = server._handle_get_occupation_data({})
        assert result["data"] is None
        assert "required" in result["message"].lower()

    def test_empty_soc_returns_required(self):
        server = _make_server()
        result = server._handle_get_occupation_data({"soc_code": ""})
        assert result["data"] is None

    def test_malformed_soc_rejected(self):
        server = _make_server()
        result = server._handle_get_occupation_data({"soc_code": "13_2051"})
        assert result["data"] is None
        assert "XX-XXXX" in result["message"]

    def test_whitespace_stripped(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[SAMPLE_ROW]) as mq:
            server._handle_get_occupation_data({"soc_code": "  13-2051  "})
        assert mq.call_args.kwargs["filters"]["soc_code"] == "13-2051"


class TestNullCases:
    def test_not_found_returns_null(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[]):
            result = server._handle_get_occupation_data({"soc_code": "99-9999"})
        assert result["data"] is None
        assert "99-9999" in result["message"]

    def test_query_error_returns_null(self):
        server = _make_server()
        err = [{"error": "Cannot query consumable.occupation_profiles"}]
        with patch.object(server, "query_iceberg_simple", return_value=err):
            result = server._handle_get_occupation_data({"soc_code": "13-2051"})
        assert result["data"] is None


class TestGovernance:
    def test_governance_attached_on_success(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[SAMPLE_ROW]):
            result = server._handle_get_occupation_data({"soc_code": "13-2051"})
        assert result["governance"]["table"] == OCCUPATION_DATA_TABLE

    def test_governance_attached_on_null(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[]):
            result = server._handle_get_occupation_data({"soc_code": "99-9999"})
        assert result["governance"]["table"] == OCCUPATION_DATA_TABLE
