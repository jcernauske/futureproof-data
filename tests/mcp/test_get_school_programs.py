"""Tests for the get_school_programs MCP tool.

Covers tool registration, fuzzy substring match, numeric unitid exact
lookup, min_confidence filtering, row limit, program_name sort order,
empty/missing input handling, query error propagation, and governance
metadata attachment.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from mcp_server.futureproof_server import (
    SCHOOL_PROGRAMS_MAX_ROWS,
    SCHOOL_PROGRAMS_RESPONSE_FIELDS,
    SCHOOL_PROGRAMS_TABLE,
    FutureProofMCPServer,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_row(
    unitid: int,
    institution: str,
    cipcode: str,
    program_name: str,
    confidence_tier: str = "high",
    **overrides,
) -> dict:
    row = {
        "unitid": unitid,
        "institution_name": institution,
        "institution_control": "Public",
        "cipcode": cipcode,
        "program_name": program_name,
        "cip_family_name": "Business, Management, Marketing",
        "earnings_1yr_median": 45000.0,
        "earnings_1yr_p25": 35000.0,
        "earnings_1yr_p75": 60000.0,
        "debt_median": 22000.0,
        "debt_to_earnings_annual": 0.49,
        "debt_to_earnings_tier": "Low",
        "program_value_index": 2.05,
        "confidence_tier": confidence_tier,
        "has_earnings": True,
        "has_debt": True,
        "outcome_completeness": 1.0,
    }
    row.update(overrides)
    return row


ISU_ROWS = [
    _make_row(151801, "Indiana State University", "52.02", "Business Administration"),
    _make_row(151801, "Indiana State University", "45.11", "Sociology", confidence_tier="medium"),
    _make_row(151801, "Indiana State University", "11.01", "Computer Science", confidence_tier="low"),
    _make_row(151801, "Indiana State University", "99.99", "Suppressed", confidence_tier="insufficient"),
]

MULTI_CAMPUS_ROWS = [
    _make_row(170976, "University of Michigan-Ann Arbor", "52.02", "Business"),
    _make_row(171137, "University of Michigan-Dearborn", "52.02", "Business"),
    _make_row(170082, "University of Michigan-Flint", "52.02", "Business"),
    _make_row(151801, "Indiana State University", "52.02", "Business Administration"),
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


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


class TestToolRegistration:
    def test_tool_is_registered(self):
        server = _make_server()
        names = [t.name for t in server.get_tools()]
        assert "get_school_programs" in names

    def test_tool_requires_school_name(self):
        server = _make_server()
        tool = [t for t in server.get_tools() if t.name == "get_school_programs"][0]
        assert "school_name" in tool.input_schema["required"]

    def test_min_confidence_has_default(self):
        server = _make_server()
        tool = [t for t in server.get_tools() if t.name == "get_school_programs"][0]
        assert tool.input_schema["properties"]["min_confidence"]["default"] == "insufficient"


# ---------------------------------------------------------------------------
# Fuzzy name lookup
# ---------------------------------------------------------------------------


class TestFuzzyLookup:
    def test_substring_match_returns_matching_rows(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=MULTI_CAMPUS_ROWS):
            result = server._handle_get_school_programs({"school_name": "Indiana State"})
        assert result["data"] is not None
        assert result["row_count"] == 1
        assert result["data"][0]["institution_name"] == "Indiana State University"

    def test_case_insensitive_match(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=MULTI_CAMPUS_ROWS):
            result = server._handle_get_school_programs({"school_name": "indiana STATE"})
        assert result["row_count"] == 1

    def test_multi_campus_returns_all_matches(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=MULTI_CAMPUS_ROWS):
            result = server._handle_get_school_programs({"school_name": "Michigan"})
        assert result["row_count"] == 3
        names = {r["institution_name"] for r in result["data"]}
        assert names == {
            "University of Michigan-Ann Arbor",
            "University of Michigan-Dearborn",
            "University of Michigan-Flint",
        }

    def test_sorted_by_program_name(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=ISU_ROWS):
            result = server._handle_get_school_programs({"school_name": "Indiana"})
        names = [r["program_name"] for r in result["data"]]
        assert names == sorted(names)

    def test_fuzzy_query_uses_no_filters(self):
        """Fuzzy path passes filters=None so ILIKE happens in Python."""
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=ISU_ROWS) as mq:
            server._handle_get_school_programs({"school_name": "Indiana"})
        _, kwargs = mq.call_args
        assert kwargs.get("filters") is None


# ---------------------------------------------------------------------------
# Numeric unitid exact lookup
# ---------------------------------------------------------------------------


class TestNumericLookup:
    def test_digits_trigger_unitid_filter(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=ISU_ROWS) as mq:
            server._handle_get_school_programs({"school_name": "151801"})
        _, kwargs = mq.call_args
        assert kwargs.get("filters") == {"unitid": 151801}

    def test_numeric_lookup_returns_all_programs(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=ISU_ROWS):
            result = server._handle_get_school_programs({"school_name": "151801"})
        assert result["row_count"] == 4


# ---------------------------------------------------------------------------
# min_confidence filter
# ---------------------------------------------------------------------------


class TestMinConfidence:
    def test_default_returns_all_tiers(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=ISU_ROWS):
            result = server._handle_get_school_programs({"school_name": "Indiana"})
        assert result["row_count"] == 4

    def test_medium_filters_out_low_and_insufficient(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=ISU_ROWS):
            result = server._handle_get_school_programs(
                {"school_name": "Indiana", "min_confidence": "medium"}
            )
        tiers = {r["confidence_tier"] for r in result["data"]}
        assert tiers == {"high", "medium"}

    def test_high_filters_out_everything_else(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=ISU_ROWS):
            result = server._handle_get_school_programs(
                {"school_name": "Indiana", "min_confidence": "high"}
            )
        assert result["row_count"] == 1
        assert result["data"][0]["confidence_tier"] == "high"

    def test_invalid_min_confidence_returns_null(self):
        server = _make_server()
        result = server._handle_get_school_programs(
            {"school_name": "Indiana", "min_confidence": "bogus"}
        )
        assert result["data"] is None
        assert "min_confidence" in result["message"]

    def test_all_suppressed_with_high_returns_null(self):
        server = _make_server()
        suppressed = [
            _make_row(99999, "Nowhere U", "11.01", "CS", confidence_tier="insufficient"),
        ]
        with patch.object(server, "query_iceberg_simple", return_value=suppressed):
            result = server._handle_get_school_programs(
                {"school_name": "Nowhere", "min_confidence": "high"}
            )
        assert result["data"] is None


# ---------------------------------------------------------------------------
# Row cap
# ---------------------------------------------------------------------------


class TestRowCap:
    def test_caps_at_500_rows(self):
        server = _make_server()
        rows = [
            _make_row(1, "Test School", "11.01", f"Program {i:03d}")
            for i in range(600)
        ]
        with patch.object(server, "query_iceberg_simple", return_value=rows):
            result = server._handle_get_school_programs({"school_name": "Test"})
        assert result["row_count"] == SCHOOL_PROGRAMS_MAX_ROWS


# ---------------------------------------------------------------------------
# Null / missing / empty input
# ---------------------------------------------------------------------------


class TestNullInput:
    def test_missing_key_returns_required(self):
        server = _make_server()
        result = server._handle_get_school_programs({})
        assert result["data"] is None
        assert "required" in result["message"].lower()

    def test_empty_string_returns_required(self):
        server = _make_server()
        result = server._handle_get_school_programs({"school_name": ""})
        assert result["data"] is None
        assert "required" in result["message"].lower()

    def test_whitespace_only_returns_required(self):
        server = _make_server()
        result = server._handle_get_school_programs({"school_name": "   "})
        assert result["data"] is None
        assert "required" in result["message"].lower()

    def test_no_match_returns_null_with_message(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=ISU_ROWS):
            result = server._handle_get_school_programs({"school_name": "Nonexistent"})
        assert result["data"] is None
        assert "Nonexistent" in result["message"]


# ---------------------------------------------------------------------------
# Query errors
# ---------------------------------------------------------------------------


class TestQueryErrors:
    def test_query_error_returns_null(self):
        server = _make_server()
        err = [{"error": "Cannot query consumable.career_outcomes: table missing"}]
        with patch.object(server, "query_iceberg_simple", return_value=err):
            result = server._handle_get_school_programs({"school_name": "Indiana"})
        assert result["data"] is None
        assert "Cannot query" in result["message"]


# ---------------------------------------------------------------------------
# Governance
# ---------------------------------------------------------------------------


class TestGovernance:
    def test_governance_metadata_attached_on_success(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=ISU_ROWS):
            result = server._handle_get_school_programs({"school_name": "Indiana"})
        assert result["governance"]["table"] == SCHOOL_PROGRAMS_TABLE

    def test_governance_metadata_attached_on_null(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[]):
            result = server._handle_get_school_programs({"school_name": "Nonexistent"})
        assert result["governance"]["table"] == SCHOOL_PROGRAMS_TABLE


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------


class TestResponseShape:
    def test_response_contains_all_expected_fields(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=ISU_ROWS):
            result = server._handle_get_school_programs({"school_name": "Indiana"})
        for field in SCHOOL_PROGRAMS_RESPONSE_FIELDS:
            assert field in result["data"][0], f"Missing field: {field}"
