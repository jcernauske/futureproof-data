"""Tests for the get_occupation_education_requirements MCP tool.

Covers:
- Known grad-school SOC (29-1123 Physical Therapist) returns
  education_code=1, requires_grad_school=True.
- Known undergrad SOC (15-1252 Software Developer) returns
  education_code in 3-8, requires_grad_school=False.
- Invalid SOC format ("11_2021") returns an error message.
- Unknown SOC (real format but not in DB) returns error message.
- Missing soc_code returns error.
- Whitespace-padded soc_code is stripped.
- Query error propagation.

Follows the same pattern as ``test_get_occupation_data.py``: uses a
``_make_server()`` helper and ``patch.object`` on ``query_iceberg_simple``
to avoid DuckDB dependency.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from mcp_server.futureproof_server import (
    OCCUPATION_DATA_TABLE,
    FutureProofMCPServer,
)


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

SAMPLE_DPT_ROW = {
    "soc_code": "29-1123",
    "occupation_title": "Physical Therapists",
    "education_code": 1,
    "education_level_name": "Doctoral or professional degree",
}

SAMPLE_SW_DEV_ROW = {
    "soc_code": "15-1252",
    "occupation_title": "Software Developers",
    "education_code": 5,
    "education_level_name": "Bachelor's degree",
}

SAMPLE_MASTERS_ROW = {
    "soc_code": "21-1021",
    "occupation_title": "Child, Family, and School Social Workers",
    "education_code": 2,
    "education_level_name": "Master's degree",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_server() -> FutureProofMCPServer:
    """Construct a bare FutureProofMCPServer without a real catalog."""
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
# Tool Registration
# ---------------------------------------------------------------------------


class TestToolRegistration:
    def test_tool_is_registered(self) -> None:
        server = _make_server()
        names = [t.name for t in server.get_tools()]
        assert "get_occupation_education_requirements" in names

    def test_requires_soc_code(self) -> None:
        server = _make_server()
        tool = [
            t
            for t in server.get_tools()
            if t.name == "get_occupation_education_requirements"
        ][0]
        assert "soc_code" in tool.input_schema["required"]


# ---------------------------------------------------------------------------
# Known Grad-School SOC
# ---------------------------------------------------------------------------


class TestGradSchoolSoc:
    def test_returns_education_for_known_soc_dpt(self) -> None:
        """Physical Therapist (29-1123) should be education_code=1,
        requires_grad_school=True."""
        server = _make_server()
        with patch.object(
            server, "query_iceberg_simple", return_value=[SAMPLE_DPT_ROW]
        ):
            result = server._handle_get_occupation_education_requirements(
                {"soc_code": "29-1123"}
            )
        data = result["data"]
        assert data is not None
        assert data["soc_code"] == "29-1123"
        assert data["education_code"] == 1
        assert data["requires_grad_school"] is True
        assert data["education_level_name"] == "Doctoral or professional degree"
        assert data["occupation_title"] == "Physical Therapists"

    def test_masters_degree_also_requires_grad_school(self) -> None:
        """Master's-required SOCs (education_code=2) should also return
        requires_grad_school=True."""
        server = _make_server()
        with patch.object(
            server, "query_iceberg_simple", return_value=[SAMPLE_MASTERS_ROW]
        ):
            result = server._handle_get_occupation_education_requirements(
                {"soc_code": "21-1021"}
            )
        data = result["data"]
        assert data is not None
        assert data["education_code"] == 2
        assert data["requires_grad_school"] is True


# ---------------------------------------------------------------------------
# Known Undergrad SOC
# ---------------------------------------------------------------------------


class TestUndergradSoc:
    def test_returns_education_for_undergrad_soc(self) -> None:
        """Software Developer (15-1252) should be education_code=5,
        requires_grad_school=False."""
        server = _make_server()
        with patch.object(
            server, "query_iceberg_simple", return_value=[SAMPLE_SW_DEV_ROW]
        ):
            result = server._handle_get_occupation_education_requirements(
                {"soc_code": "15-1252"}
            )
        data = result["data"]
        assert data is not None
        assert data["soc_code"] == "15-1252"
        assert data["education_code"] == 5
        assert data["requires_grad_school"] is False
        assert data["education_level_name"] == "Bachelor's degree"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_invalid_soc_format_returns_error(self) -> None:
        """'11_2021' (underscore instead of hyphen) should be rejected."""
        server = _make_server()
        result = server._handle_get_occupation_education_requirements(
            {"soc_code": "11_2021"}
        )
        assert result["data"] is None
        assert "XX-XXXX" in result["message"]

    def test_missing_soc_returns_error(self) -> None:
        """Missing soc_code should return a 'required' error."""
        server = _make_server()
        result = server._handle_get_occupation_education_requirements({})
        assert result["data"] is None
        assert "required" in result["message"].lower()

    def test_empty_soc_returns_error(self) -> None:
        """Empty string soc_code should return a 'required' error."""
        server = _make_server()
        result = server._handle_get_occupation_education_requirements(
            {"soc_code": ""}
        )
        assert result["data"] is None

    def test_whitespace_stripped(self) -> None:
        """Leading/trailing whitespace should be stripped before lookup."""
        server = _make_server()
        with patch.object(
            server, "query_iceberg_simple", return_value=[SAMPLE_DPT_ROW]
        ) as mq:
            server._handle_get_occupation_education_requirements(
                {"soc_code": "  29-1123  "}
            )
        assert mq.call_args.kwargs["filters"]["soc_code"] == "29-1123"

    def test_numeric_soc_code_coerced_to_string(self) -> None:
        """An integer soc_code (edge case from JSON parsing) should be
        coerced to string. Still rejected since it won't match XX-XXXX."""
        server = _make_server()
        result = server._handle_get_occupation_education_requirements(
            {"soc_code": 291123}
        )
        assert result["data"] is None


# ---------------------------------------------------------------------------
# Not Found / Error Cases
# ---------------------------------------------------------------------------


class TestNotFound:
    def test_unknown_soc_returns_not_found(self) -> None:
        """A valid-format SOC that doesn't exist in the DB should return
        a descriptive error."""
        server = _make_server()
        with patch.object(
            server, "query_iceberg_simple", return_value=[]
        ):
            result = server._handle_get_occupation_education_requirements(
                {"soc_code": "99-9999"}
            )
        assert result["data"] is None
        assert "99-9999" in result["message"]

    def test_query_error_returns_error(self) -> None:
        """A DuckDB query error should propagate as a clean error response."""
        server = _make_server()
        err = [{"error": "Cannot query consumable.occupation_profiles"}]
        with patch.object(
            server, "query_iceberg_simple", return_value=err
        ):
            result = server._handle_get_occupation_education_requirements(
                {"soc_code": "29-1123"}
            )
        assert result["data"] is None


# ---------------------------------------------------------------------------
# Query Contract
# ---------------------------------------------------------------------------


class TestQueryContract:
    def test_delegates_with_correct_filter_and_columns(self) -> None:
        """The handler should query the correct table with the expected
        columns and filter."""
        server = _make_server()
        with patch.object(
            server, "query_iceberg_simple", return_value=[SAMPLE_DPT_ROW]
        ) as mq:
            server._handle_get_occupation_education_requirements(
                {"soc_code": "29-1123"}
            )
        mq.assert_called_once_with(
            OCCUPATION_DATA_TABLE,
            filters={"soc_code": "29-1123"},
            columns=[
                "soc_code",
                "occupation_title",
                "education_code",
                "education_level_name",
            ],
            limit=1,
        )

    def test_row_count_is_1_on_success(self) -> None:
        """Successful lookup should report row_count=1."""
        server = _make_server()
        with patch.object(
            server, "query_iceberg_simple", return_value=[SAMPLE_DPT_ROW]
        ):
            result = server._handle_get_occupation_education_requirements(
                {"soc_code": "29-1123"}
            )
        assert result["row_count"] == 1


# ---------------------------------------------------------------------------
# Edge Cases for requires_grad_school Logic
# ---------------------------------------------------------------------------


class TestRequiresGradSchoolLogic:
    """Pin the exact boundary: education_code in (1, 2) = True, else False."""

    @staticmethod
    def _make_row(education_code: int) -> dict:
        return {
            "soc_code": "00-0000",
            "occupation_title": "Test Occupation",
            "education_code": education_code,
            "education_level_name": f"Code {education_code}",
        }

    def test_education_code_1_is_grad(self) -> None:
        server = _make_server()
        with patch.object(
            server, "query_iceberg_simple",
            return_value=[self._make_row(1)],
        ):
            result = server._handle_get_occupation_education_requirements(
                {"soc_code": "00-0000"}
            )
        assert result["data"]["requires_grad_school"] is True

    def test_education_code_2_is_grad(self) -> None:
        server = _make_server()
        with patch.object(
            server, "query_iceberg_simple",
            return_value=[self._make_row(2)],
        ):
            result = server._handle_get_occupation_education_requirements(
                {"soc_code": "00-0000"}
            )
        assert result["data"]["requires_grad_school"] is True

    def test_education_code_3_is_not_grad(self) -> None:
        """education_code=3 (Bachelor's + higher experience) is NOT grad."""
        server = _make_server()
        with patch.object(
            server, "query_iceberg_simple",
            return_value=[self._make_row(3)],
        ):
            result = server._handle_get_occupation_education_requirements(
                {"soc_code": "00-0000"}
            )
        assert result["data"]["requires_grad_school"] is False

    def test_education_code_5_is_not_grad(self) -> None:
        server = _make_server()
        with patch.object(
            server, "query_iceberg_simple",
            return_value=[self._make_row(5)],
        ):
            result = server._handle_get_occupation_education_requirements(
                {"soc_code": "00-0000"}
            )
        assert result["data"]["requires_grad_school"] is False

    def test_education_code_8_is_not_grad(self) -> None:
        server = _make_server()
        with patch.object(
            server, "query_iceberg_simple",
            return_value=[self._make_row(8)],
        ):
            result = server._handle_get_occupation_education_requirements(
                {"soc_code": "00-0000"}
            )
        assert result["data"]["requires_grad_school"] is False

    def test_education_code_none_is_not_grad(self) -> None:
        """When education_code is missing (None), requires_grad_school
        should be False — don't accidentally match None in (1, 2)."""
        server = _make_server()
        row = self._make_row(0)
        row["education_code"] = None
        with patch.object(
            server, "query_iceberg_simple", return_value=[row],
        ):
            result = server._handle_get_occupation_education_requirements(
                {"soc_code": "00-0000"}
            )
        assert result["data"]["requires_grad_school"] is False
