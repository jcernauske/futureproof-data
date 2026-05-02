"""Tests for the get_institution_aura MCP tool.

Tests cover: valid lookups, missing-row handling, NULL aura_score row
(returned intact for caller-side rendering), unitid validation,
governance metadata attachment.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from mcp_server.futureproof_server import (
    INSTITUTION_AURA_RESPONSE_FIELDS,
    INSTITUTION_AURA_TABLE,
    FutureProofMCPServer,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_ROW = {
    "unitid": 145813,
    "institution_name": "Illinois State University",
    "endowment_per_fte": 12500.0,
    "marketing_ratio": 0.034,
    "athletic_spend_per_fte": 2100.0,
    "athletic_revenue_per_fte": 1850.0,
    "athletic_subsidy_ratio": 0.88,
    "athletic_fte_source": "eada",
    "aura_score": 5,
    "aura_score_continuous": 5.32,
    "aura_score_version": "v1",
    "aura_score_basis": "three_term",
    "has_ipeds_finance": True,
    "has_eada": True,
    "coverage_tier": "both",
}


# Athletics-only school with no marketing_ratio → NULL aura_score
NULL_AURA_ROW = {
    "unitid": 100654,
    "institution_name": "Athletics-Only Tech College",
    "endowment_per_fte": None,
    "marketing_ratio": None,
    "athletic_spend_per_fte": 1200.0,
    "athletic_revenue_per_fte": 0.0,
    "athletic_subsidy_ratio": 1.0,
    "athletic_fte_source": "eada",
    "aura_score": None,
    "aura_score_continuous": None,
    "aura_score_version": "v1",
    "aura_score_basis": None,
    "has_ipeds_finance": False,
    "has_eada": True,
    "coverage_tier": "athletics_only",
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
    """Verify get_institution_aura is registered correctly."""

    def test_tool_is_registered(self):
        server = _make_server()
        tools = server.get_tools()
        names = [t.name for t in tools]
        assert "get_institution_aura" in names

    def test_tool_requires_unitid(self):
        server = _make_server()
        tool = [
            t for t in server.get_tools() if t.name == "get_institution_aura"
        ][0]
        assert "unitid" in tool.input_schema["required"]
        # unitid must be typed as integer per schema
        assert tool.input_schema["properties"]["unitid"]["type"] == "integer"

    def test_response_fields_documented(self):
        """The 15 fields in INSTITUTION_AURA_RESPONSE_FIELDS map the
        complete shape returned to Gemma — basis + version are critical
        for receipt provenance, so the tool description should call them
        out explicitly."""
        server = _make_server()
        tool = [
            t for t in server.get_tools() if t.name == "get_institution_aura"
        ][0]
        assert "aura_score_basis" in tool.description
        assert "aura_score_version" in tool.description
        # NULL aura_score handling must be in the description so Gemma
        # knows it's normal for institutions without coverage.
        assert "NULL" in tool.description


# ---------------------------------------------------------------------------
# Handler behavior
# ---------------------------------------------------------------------------

class TestHandler:
    """Verify _handle_get_institution_aura behavior across input shapes."""

    def test_returns_row_for_known_unitid(self):
        server = _make_server()
        server.query_iceberg_simple = MagicMock(return_value=[SAMPLE_ROW])
        server.attach_governance = lambda r, _t: r
        server.enrich_response = lambda r, _t: {**r, "governance": {}}

        result = server._handle_get_institution_aura({"unitid": 145813})

        assert result["data"] == SAMPLE_ROW
        assert result["row_count"] == 1
        server.query_iceberg_simple.assert_called_once_with(
            INSTITUTION_AURA_TABLE,
            filters={"unitid": 145813},
            columns=INSTITUTION_AURA_RESPONSE_FIELDS,
            limit=1,
        )

    def test_returns_null_for_unknown_unitid(self):
        """Missing-row response is structured (data=None + message)
        with governance metadata attached so the caller can still cite
        the table contract."""
        server = _make_server()
        server.query_iceberg_simple = MagicMock(return_value=[])
        captured = {}

        def fake_attach(payload, table):
            captured["table"] = table
            return {**payload, "governance": {"table": table}}

        server.attach_governance = fake_attach

        result = server._handle_get_institution_aura({"unitid": 999999})

        assert result["data"] is None
        assert "No institution_aura row" in result["message"]
        assert captured["table"] == INSTITUTION_AURA_TABLE

    def test_handles_null_aura_score_row(self):
        """A row with aura_score IS NULL is returned INTACT — the caller
        (stat_engine) decides whether to render the AURA stat as '—'.
        The MCP tool does not impute or filter."""
        server = _make_server()
        server.query_iceberg_simple = MagicMock(return_value=[NULL_AURA_ROW])
        server.attach_governance = lambda r, _t: r
        server.enrich_response = lambda r, _t: {**r, "governance": {}}

        result = server._handle_get_institution_aura({"unitid": 100654})

        assert result["data"] == NULL_AURA_ROW
        assert result["data"]["aura_score"] is None
        assert result["data"]["aura_score_basis"] is None

    def test_rejects_missing_unitid(self):
        server = _make_server()
        result = server._handle_get_institution_aura({})
        assert result["data"] is None
        assert "unitid is required" in result["message"]

    def test_rejects_string_unitid(self):
        """unitid must be an integer (matches Iceberg schema). Strings
        are rejected with a structured-null response."""
        server = _make_server()
        result = server._handle_get_institution_aura({"unitid": "145813"})
        assert result["data"] is None
        assert "integer" in result["message"]

    def test_rejects_bool_unitid(self):
        """bool is a subclass of int in Python, so isinstance(True, int)
        returns True. The handler must reject bools explicitly to keep
        the contract honest."""
        server = _make_server()
        result = server._handle_get_institution_aura({"unitid": True})
        assert result["data"] is None
        assert "integer" in result["message"]

    def test_propagates_query_error(self):
        """When the query layer returns an error envelope, the handler
        surfaces it as a structured-null with the error message and
        attaches governance metadata."""
        server = _make_server()
        server.query_iceberg_simple = MagicMock(
            return_value=[{"error": "table read failed"}]
        )
        server.attach_governance = lambda r, _t: r

        result = server._handle_get_institution_aura({"unitid": 145813})

        assert result["data"] is None
        assert result["message"] == "table read failed"
