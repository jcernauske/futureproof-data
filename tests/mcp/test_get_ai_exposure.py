"""Tests for the get_ai_exposure MCP tool.

Tests cover: valid lookups, null/missing SOC handling, empty input,
whitespace stripping, response shape, governance metadata attachment,
field completeness, and integration with the Iceberg query layer.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from mcp_server.futureproof_server import (
    AI_EXPOSURE_RESPONSE_FIELDS,
    TABLE_NAME,
    FutureProofMCPServer,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_ROW = {
    "soc_code": "13-2051",
    "occupation_title": "Financial analysts",
    "exposure_score": 8,
    "stat_res": 3,
    "boss_ai_score": 8,
    "rationale": (
        "Financial analysts work almost entirely on computers, processing "
        "data, building models, and generating reports."
    ),
    "category": "business-and-financial",
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


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

class TestToolRegistration:
    """Verify get_ai_exposure is registered correctly."""

    def test_tool_is_registered(self):
        server = _make_server()
        tools = server.get_tools()
        names = [t.name for t in tools]
        assert "get_ai_exposure" in names

    def test_tool_requires_soc_code(self):
        server = _make_server()
        tool = [t for t in server.get_tools() if t.name == "get_ai_exposure"][0]
        assert "soc_code" in tool.input_schema["required"]

    def test_tool_included_in_all_tools(self):
        """get_ai_exposure appears alongside framework tools."""
        server = _make_server()
        all_names = [t.name for t in server._all_tools()]
        assert "get_ai_exposure" in all_names
        assert "query_table" in all_names  # framework tool


# ---------------------------------------------------------------------------
# Valid lookups
# ---------------------------------------------------------------------------

class TestValidLookup:
    """Tests for successful SOC code lookups."""

    def test_returns_matching_row(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[SAMPLE_ROW]):
            result = server._handle_get_ai_exposure({"soc_code": "13-2051"})
        assert result["data"]["soc_code"] == "13-2051"
        assert result["data"]["exposure_score"] == 8
        assert result["row_count"] == 1

    def test_response_contains_all_fields(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[SAMPLE_ROW]):
            result = server._handle_get_ai_exposure({"soc_code": "13-2051"})
        for field in AI_EXPOSURE_RESPONSE_FIELDS:
            assert field in result["data"], f"Missing field: {field}"

    def test_governance_metadata_attached(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[SAMPLE_ROW]):
            result = server._handle_get_ai_exposure({"soc_code": "13-2051"})
        assert "governance" in result
        assert result["governance"]["table"] == TABLE_NAME


# ---------------------------------------------------------------------------
# Null / missing SOC handling
# ---------------------------------------------------------------------------

class TestNullCases:
    """Tests for missing, empty, or not-found SOC codes."""

    def test_soc_not_found_returns_null_with_message(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[]):
            result = server._handle_get_ai_exposure({"soc_code": "99-9999"})
        assert result["data"] is None
        assert "No AI exposure data available" in result["message"]

    def test_empty_soc_returns_required_message(self):
        server = _make_server()
        result = server._handle_get_ai_exposure({"soc_code": ""})
        assert result["data"] is None
        assert "required" in result["message"].lower()

    def test_missing_soc_key_returns_required_message(self):
        server = _make_server()
        result = server._handle_get_ai_exposure({})
        assert result["data"] is None
        assert "required" in result["message"].lower()

    def test_whitespace_soc_stripped(self):
        """Leading/trailing whitespace is stripped before query."""
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[SAMPLE_ROW]) as mock_q:
            server._handle_get_ai_exposure({"soc_code": "  13-2051  "})
        call_filters = mock_q.call_args[1].get("filters") or mock_q.call_args[0][1]
        assert call_filters["soc_code"] == "13-2051"


# ---------------------------------------------------------------------------
# Query error handling
# ---------------------------------------------------------------------------

class TestQueryErrors:
    """Tests for Iceberg query failures."""

    def test_query_error_returns_null(self):
        server = _make_server()
        with patch.object(
            server, "query_iceberg_simple",
            return_value=[{"error": "Cannot query consumable.ai_exposure: table not found"}],
        ):
            result = server._handle_get_ai_exposure({"soc_code": "13-2051"})
        assert result["data"] is None
        assert "error" in result["message"].lower() or "Cannot query" in result["message"]


# ---------------------------------------------------------------------------
# Query delegation
# ---------------------------------------------------------------------------

class TestQueryDelegation:
    """Verify the tool delegates correctly to query_iceberg_simple."""

    def test_queries_correct_table(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[]) as mock_q:
            server._handle_get_ai_exposure({"soc_code": "13-2051"})
        mock_q.assert_called_once_with(
            TABLE_NAME,
            filters={"soc_code": "13-2051"},
            columns=AI_EXPOSURE_RESPONSE_FIELDS,
            limit=1,
        )

    def test_limits_to_one_row(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[]) as mock_q:
            server._handle_get_ai_exposure({"soc_code": "13-2051"})
        _, kwargs = mock_q.call_args
        assert kwargs.get("limit") == 1 or mock_q.call_args[0][3] == 1
