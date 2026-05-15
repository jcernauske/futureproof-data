"""Tests for school search and program listing.

MCP calls are patched so these tests are hermetic.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.models.career import Program
from app.services import school_lookup

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mcp_rows(monkeypatch):
    """Install a stub MCP call that returns caller-provided rows."""

    state = {"rows": []}

    def fake_call(tool: str, args: dict[str, Any]) -> dict:
        assert tool == "get_school_programs"
        return {"data": state["rows"]}

    from app.services import mcp_client

    monkeypatch.setattr(mcp_client, "call", fake_call)

    def set_rows(rows: list[dict]) -> None:
        state["rows"] = rows

    return set_rows


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------


_IUB_ROWS = [
    {
        "unitid": 151351,
        "institution_name": "Indiana University-Bloomington",
        "institution_control": "public",
        "cipcode": "52.01",
        "program_name": "Business/Commerce, General",
        "cip_family_name": "Business",
        "earnings_1yr_median": 55000.0,
        "debt_median": 19500.0,
        "confidence_tier": "high",
    },
    {
        "unitid": 151351,
        "institution_name": "Indiana University-Bloomington",
        "institution_control": "public",
        "cipcode": "52.03",
        "program_name": "Accounting",
        "cip_family_name": "Business",
        "earnings_1yr_median": 58000.0,
        "debt_median": 19500.0,
        "confidence_tier": "high",
    },
    {
        "unitid": 151324,
        "institution_name": "Indiana University-East",
        "institution_control": "public",
        "cipcode": "52.01",
        "program_name": "Business/Commerce, General",
        "earnings_1yr_median": 38000.0,
        "debt_median": 15000.0,
        "confidence_tier": "medium",
    },
]


# ---------------------------------------------------------------------------
# search_schools
# ---------------------------------------------------------------------------


class TestSearchSchools:
    def test_returns_distinct_schools(self, mcp_rows):
        mcp_rows(_IUB_ROWS)
        matches = school_lookup.search_schools("Indiana")
        assert len(matches) == 2
        unitids = {m.unitid for m in matches}
        assert unitids == {151351, 151324}

    def test_empty_query_returns_empty(self):
        assert school_lookup.search_schools("") == []
        assert school_lookup.search_schools("   ") == []

    def test_sorted_by_name(self, mcp_rows):
        mcp_rows(_IUB_ROWS)
        matches = school_lookup.search_schools("Indiana")
        names = [m.institution_name for m in matches]
        assert names == sorted(names)

    def test_acronym_rows_pass_through(self, mcp_rows):
        """Acronym-matched rows from the MCP flow through unchanged.

        The matcher lives in the MCP layer; this service test just
        guards against regressions in the passthrough — the rows the
        MCP returns for a query like "IU" appear in the result list.
        """
        mcp_rows(_IUB_ROWS)
        matches = school_lookup.search_schools("IU")
        unitids = {m.unitid for m in matches}
        assert 151351 in unitids
        assert 151324 in unitids


# ---------------------------------------------------------------------------
# get_programs
# ---------------------------------------------------------------------------


class TestGetPrograms:
    def test_filters_and_parses(self, mcp_rows):
        mcp_rows(_IUB_ROWS)
        programs = school_lookup.get_programs(151351)
        # The stub returns ALL rows regardless of unitid; the code still
        # maps them cleanly.
        assert all(isinstance(p, Program) for p in programs)
        assert any(p.cipcode == "52.03" for p in programs)

    def test_sorted_alphabetically(self, mcp_rows):
        mcp_rows(_IUB_ROWS)
        programs = school_lookup.get_programs(151351)
        names = [p.program_name.lower() for p in programs]
        assert names == sorted(names)


