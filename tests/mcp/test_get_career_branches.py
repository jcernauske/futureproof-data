"""Tests for the get_career_branches MCP tool."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from mcp_server.futureproof_server import (
    CAREER_BRANCHES_MAX_ROWS,
    CAREER_BRANCHES_RESPONSE_FIELDS,
    CAREER_BRANCHES_TABLE,
    FutureProofMCPServer,
)


def _make_row(
    related_soc: str,
    best_index: float,
    is_primary: bool = True,
    **overrides,
) -> dict:
    row = {
        "soc_code": "13-2051",
        "source_title": "Financial Analysts",
        "related_soc_code": related_soc,
        "related_title": f"Title {related_soc}",
        "best_index": best_index,
        "relatedness_tier": "primary" if is_primary else "secondary",
        "is_primary": is_primary,
        "source_grw": 7,
        "source_hmn": 5,
        "source_burnout": 6,
        "source_wage": 98580.0,
        "source_res": 3,
        "source_ai_boss": 8,
        "related_grw": 8,
        "related_hmn": 6,
        "related_burnout": 5,
        "related_wage": 110000.0,
        "related_growth_category": "Much faster than average",
        "related_education_level": "Bachelor's degree",
        "related_res": 4,
        "related_ai_boss": 7,
        "grw_delta": 1,
        "hmn_delta": 1,
        "burnout_delta": -1,
        "wage_delta": 11420.0,
        "res_delta": 1,
        "ai_boss_delta": -1,
        "branch_has_full_data": True,
        # v1.2.0 (onet-experience-requirements): O*NET ETE fields
        "related_experience_years": 7.0,
        "related_experience_tier": "mid",
        "source_experience_years": 3.0,
        "experience_delta_years": 4.0,
    }
    row.update(overrides)
    return row


PRIMARY_ROWS = [
    _make_row("13-2054", 0.92),
    _make_row("13-1161", 0.85),
    _make_row("11-3031", 0.78),
]

MIXED_ROWS = PRIMARY_ROWS + [
    _make_row("15-2051", 0.55, is_primary=False),
    _make_row("13-2071", 0.40, is_primary=False),
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
        assert "get_career_branches" in names

    def test_requires_soc_code(self):
        server = _make_server()
        tool = [t for t in server.get_tools() if t.name == "get_career_branches"][0]
        assert "soc_code" in tool.input_schema["required"]

    def test_primary_only_default_true(self):
        server = _make_server()
        tool = [t for t in server.get_tools() if t.name == "get_career_branches"][0]
        assert tool.input_schema["properties"]["primary_only"]["default"] is True


class TestValidLookup:
    def test_default_returns_primary_only(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=MIXED_ROWS):
            result = server._handle_get_career_branches({"soc_code": "13-2051"})
        assert result["row_count"] == 3
        assert all(r["is_primary"] for r in result["data"])

    def test_primary_only_false_returns_all(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=MIXED_ROWS):
            result = server._handle_get_career_branches(
                {"soc_code": "13-2051", "primary_only": False}
            )
        assert result["row_count"] == 5

    def test_sorted_by_best_index_asc(self):
        server = _make_server()
        shuffled = [PRIMARY_ROWS[2], PRIMARY_ROWS[0], PRIMARY_ROWS[1]]
        with patch.object(server, "query_iceberg_simple", return_value=shuffled):
            result = server._handle_get_career_branches({"soc_code": "13-2051"})
        indices = [r["best_index"] for r in result["data"]]
        assert indices == sorted(indices)

    def test_caps_at_20_rows(self):
        server = _make_server()
        many = [_make_row(f"99-{i:04d}", 0.1 * i) for i in range(30)]
        with patch.object(server, "query_iceberg_simple", return_value=many):
            result = server._handle_get_career_branches({"soc_code": "13-2051"})
        assert result["row_count"] == CAREER_BRANCHES_MAX_ROWS

    def test_response_contains_all_fields(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=PRIMARY_ROWS):
            result = server._handle_get_career_branches({"soc_code": "13-2051"})
        for field in CAREER_BRANCHES_RESPONSE_FIELDS:
            assert field in result["data"][0], f"Missing field: {field}"

    def test_filter_passed_to_query(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=PRIMARY_ROWS) as mq:
            server._handle_get_career_branches({"soc_code": "13-2051"})
        _, kwargs = mq.call_args
        assert kwargs["filters"] == {"soc_code": "13-2051"}


class TestValidation:
    def test_missing_soc_returns_required(self):
        server = _make_server()
        result = server._handle_get_career_branches({})
        assert result["data"] is None
        assert "required" in result["message"].lower()

    def test_malformed_soc_rejected(self):
        server = _make_server()
        result = server._handle_get_career_branches({"soc_code": "bad"})
        assert result["data"] is None
        assert "XX-XXXX" in result["message"]


class TestNullCases:
    def test_no_results_returns_null(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[]):
            result = server._handle_get_career_branches({"soc_code": "99-9999"})
        assert result["data"] is None
        assert "99-9999" in result["message"]

    def test_all_non_primary_with_default_returns_null(self):
        """Rows exist but none are primary → default filter yields empty."""
        server = _make_server()
        rows = [
            _make_row("15-2051", 0.55, is_primary=False),
            _make_row("13-2071", 0.40, is_primary=False),
        ]
        with patch.object(server, "query_iceberg_simple", return_value=rows):
            result = server._handle_get_career_branches({"soc_code": "13-2051"})
        assert result["data"] is None

    def test_query_error_returns_null(self):
        server = _make_server()
        err = [{"error": "Cannot query consumable.career_branches"}]
        with patch.object(server, "query_iceberg_simple", return_value=err):
            result = server._handle_get_career_branches({"soc_code": "13-2051"})
        assert result["data"] is None


class TestExperienceFields:
    """onet-experience-requirements spec §Zone 4: the 4 new experience
    fields are projected in CAREER_BRANCHES_RESPONSE_FIELDS and flow
    through to the MCP tool response."""

    EXPERIENCE_FIELDS = (
        "related_experience_years",
        "related_experience_tier",
        "source_experience_years",
        "experience_delta_years",
    )

    def test_experience_fields_registered_in_response_fields(self):
        for field in self.EXPERIENCE_FIELDS:
            assert field in CAREER_BRANCHES_RESPONSE_FIELDS

    def test_experience_fields_surfaced_in_tool_output(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=PRIMARY_ROWS):
            result = server._handle_get_career_branches({"soc_code": "13-2051"})
        first = result["data"][0]
        for field in self.EXPERIENCE_FIELDS:
            assert field in first, f"Missing field: {field}"
        assert first["related_experience_years"] == 7.0
        assert first["related_experience_tier"] == "mid"
        assert first["source_experience_years"] == 3.0
        assert first["experience_delta_years"] == 4.0

    def test_null_experience_fields_pass_through(self):
        """When Gold has NULL experience (no O*NET ETE coverage), the
        MCP tool surfaces None — never coerced to 0."""
        server = _make_server()
        null_row = _make_row(
            "15-2051",
            0.8,
            related_experience_years=None,
            related_experience_tier=None,
            source_experience_years=None,
            experience_delta_years=None,
        )
        with patch.object(server, "query_iceberg_simple", return_value=[null_row]):
            result = server._handle_get_career_branches({"soc_code": "13-2051"})
        first = result["data"][0]
        assert first["related_experience_years"] is None
        assert first["related_experience_tier"] is None
        assert first["source_experience_years"] is None
        assert first["experience_delta_years"] is None


class TestGovernance:
    def test_governance_attached_on_success(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=PRIMARY_ROWS):
            result = server._handle_get_career_branches({"soc_code": "13-2051"})
        assert result["governance"]["table"] == CAREER_BRANCHES_TABLE

    def test_governance_attached_on_null(self):
        server = _make_server()
        with patch.object(server, "query_iceberg_simple", return_value=[]):
            result = server._handle_get_career_branches({"soc_code": "99-9999"})
        assert result["governance"]["table"] == CAREER_BRANCHES_TABLE
