"""Tests for the get_task_breakdown MCP tool."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from mcp_server.futureproof_server import (
    TASK_BREAKDOWN_RESPONSE_FIELDS,
    TASK_BREAKDOWN_TABLE,
    FutureProofMCPServer,
)


SAMPLE_ROW = {
    "bls_soc_code": "13-2051",
    "primary_title": "Financial Analysts",
    "description": "Conduct quantitative analyses of investment information.",
    "hmn_score": 5,
    "hmn_score_rounded": 5,
    "burnout_score": 6,
    "burnout_score_rounded": 6,
    "top_5_activities": '[{"activity": "Analyzing data", "importance": 4.8}]',
    "top_human_activities": '[{"activity": "Client meetings", "importance": 4.3}]',
    "burnout_drivers": '[{"driver": "time_pressure", "value": 4.2}]',
    "time_pressure": 4.2,
    "work_hours": 45,
    "consequence_of_error": 4.1,
    "activity_importance_mean": 3.9,
    "human_activity_count": 7,
    "multi_detail_flag": False,
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
        assert "get_task_breakdown" in names

    def test_requires_soc_code(self):
        server = _make_server()
        tool = [t for t in server.get_tools() if t.name == "get_task_breakdown"][0]
        assert "soc_code" in tool.input_schema["required"]


class TestValidLookup:
    def test_returns_single_row(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[SAMPLE_ROW]):
            result = server._handle_get_task_breakdown({"soc_code": "13-2051"})
        assert result["row_count"] == 1
        assert result["data"]["bls_soc_code"] == "13-2051"

    def test_response_contains_all_fields(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[SAMPLE_ROW]):
            result = server._handle_get_task_breakdown({"soc_code": "13-2051"})
        for field in TASK_BREAKDOWN_RESPONSE_FIELDS:
            assert field in result["data"], f"Missing field: {field}"

    def test_filter_uses_bls_soc_code(self):
        """O*NET Gold table keys off bls_soc_code, not soc_code."""
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[SAMPLE_ROW]) as mq:
            server._handle_get_task_breakdown({"soc_code": "13-2051"})
        mq.assert_called_once_with(
            TASK_BREAKDOWN_TABLE,
            filters={"bls_soc_code": "13-2051"},
            columns=TASK_BREAKDOWN_RESPONSE_FIELDS,
            limit=1,
        )


class TestValidation:
    def test_missing_soc_returns_required(self):
        server = _make_server()
        result = server._handle_get_task_breakdown({})
        assert result["data"] is None
        assert "required" in result["message"].lower()

    def test_malformed_soc_rejected(self):
        server = _make_server()
        result = server._handle_get_task_breakdown({"soc_code": "132051"})
        assert result["data"] is None
        assert "XX-XXXX" in result["message"]

    def test_whitespace_stripped(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[SAMPLE_ROW]) as mq:
            server._handle_get_task_breakdown({"soc_code": " 13-2051 "})
        assert mq.call_args.kwargs["filters"]["bls_soc_code"] == "13-2051"


class TestNullCases:
    def test_not_found_returns_null(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[]):
            result = server._handle_get_task_breakdown({"soc_code": "99-9999"})
        assert result["data"] is None
        assert "99-9999" in result["message"]

    def test_query_error_returns_null(self):
        server = _make_server()
        err = [{"error": "Cannot query consumable.onet_work_profiles"}]
        with patch.object(server, "query_iceberg_simple", return_value=err):
            result = server._handle_get_task_breakdown({"soc_code": "13-2051"})
        assert result["data"] is None


class TestGovernance:
    def test_governance_attached_on_success(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[SAMPLE_ROW]):
            result = server._handle_get_task_breakdown({"soc_code": "13-2051"})
        assert result["governance"]["table"] == TASK_BREAKDOWN_TABLE

    def test_governance_attached_on_null(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[]):
            result = server._handle_get_task_breakdown({"soc_code": "99-9999"})
        assert result["governance"]["table"] == TASK_BREAKDOWN_TABLE
