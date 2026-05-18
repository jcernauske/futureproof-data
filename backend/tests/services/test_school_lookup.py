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


# ---------------------------------------------------------------------------
# Bundle 3: Relevance-ranked sort (post-100-build-test-fixes-bundle §4)
#
# search_schools used to sort alphabetically. That surfaced "Indiana
# University-East" (branch campus) before "Indiana University-Bloomington"
# (flagship), and "Baptist University of Florida" before "University of
# Florida" for the query "University of Florida". Bundle 3 replaces the
# alpha sort with a relevance rank: exact name > prefix > anything else,
# then by program count desc (flagship over branch), then name length asc,
# then alpha.
# ---------------------------------------------------------------------------


def _ranked_school_rows(rows_with_counts: list[tuple[dict, int]]) -> list[dict]:
    """Helper: yield the row list while installing the program-count cache.

    Each tuple is (row, program_count_for_unitid). We clear the lru_cache,
    install a stub for _program_counts_by_unitid, then return the rows.
    """
    return [row for row, _ in rows_with_counts]


def _install_program_counts(monkeypatch, counts: dict[int, int]) -> None:
    """Patch _program_counts_by_unitid to return the given mapping.

    The function is @lru_cache(maxsize=1) so we monkeypatch the bound
    function itself rather than poke at the cache. This keeps the rank
    test hermetic regardless of whether the real DuckDB-backed query
    fires.
    """
    monkeypatch.setattr(
        school_lookup, "_program_counts_by_unitid", lambda: counts
    )


class TestRelevanceSort:
    """Verify the Bundle 3 sort rank prioritizes flagship over branch."""

    def test_school_search_ranks_main_above_branch(
        self, mcp_rows, monkeypatch
    ):
        """Ohio State: Main Campus (204796, ~140 programs) must rank
        ABOVE Lima Campus (204671, ~8 programs) when the query is
        'Ohio State'."""
        rows = [
            {
                "unitid": 204796,
                "institution_name": "Ohio State University-Main Campus",
                "institution_control": "public",
                "cipcode": "52.01",
                "program_name": "Business",
                "confidence_tier": "high",
            },
            {
                "unitid": 204671,
                "institution_name": "Ohio State University-Lima Campus",
                "institution_control": "public",
                "cipcode": "52.01",
                "program_name": "Business",
                "confidence_tier": "high",
            },
        ]
        mcp_rows(rows)
        # Main campus reports 140 distinct programs; Lima reports 8.
        _install_program_counts(monkeypatch, {204796: 140, 204671: 8})

        matches = school_lookup.search_schools("Ohio State")

        # Both surface; main campus is FIRST.
        assert len(matches) == 2
        assert matches[0].unitid == 204796, (
            f"Main campus must rank first; got order "
            f"{[m.unitid for m in matches]}"
        )
        assert matches[1].unitid == 204671

    def test_school_search_university_of_florida_ranks_flagship_first(
        self, mcp_rows, monkeypatch
    ):
        """University of Florida (134130, flagship) must rank ABOVE
        Baptist University of Florida (132408, small private)."""
        rows = [
            # Note: alpha sort would put Baptist first. Relevance rank
            # uses startswith ("university of florida" → matches the
            # flagship's name lower-prefix; doesn't match Baptist
            # because its name starts with "baptist").
            {
                "unitid": 132408,
                "institution_name": "The Baptist University of Florida",
                "institution_control": "private",
                "cipcode": "39.0601",
                "program_name": "Theology",
                "confidence_tier": "high",
            },
            {
                "unitid": 134130,
                "institution_name": "University of Florida",
                "institution_control": "public",
                "cipcode": "11.0101",
                "program_name": "Computer Science",
                "confidence_tier": "high",
            },
        ]
        mcp_rows(rows)
        _install_program_counts(
            monkeypatch, {134130: 250, 132408: 5}
        )

        matches = school_lookup.search_schools("University of Florida")

        # The flagship lands first because:
        #   - bucket 0: exact-name match for "University of Florida".
        #   - Baptist falls into bucket 2 (not prefix, not exact).
        assert matches[0].unitid == 134130, (
            f"University of Florida (flagship) must rank first; got "
            f"{[m.institution_name for m in matches]}"
        )

    def test_returns_distinct_schools_after_sort_change_still_dedupes(
        self, mcp_rows, monkeypatch
    ):
        """Regression check: Bundle 3's new sort still de-duplicates by
        unitid (same school across rows with different cipcodes collapses
        to one SchoolMatch)."""
        _install_program_counts(
            monkeypatch, {151351: 100, 151324: 20}
        )
        mcp_rows(_IUB_ROWS)
        matches = school_lookup.search_schools("Indiana")
        unitids = [m.unitid for m in matches]
        assert sorted(unitids) == sorted({151351, 151324})


# ---------------------------------------------------------------------------
# Bundle 3: Alias + token-overlap matching (MCP layer)
#
# The alias and token-overlap matchers live in the MCP handler
# `_handle_get_school_programs` — service-layer search_schools just
# forwards. Per spec §4, these tests live in test_school_lookup.py to
# keep one place for "what happens when a user types <query>".
#
# Pattern mirrors tests/mcp/test_get_school_programs.py — instantiate
# the bare server, stub query_iceberg_simple to return seeded rows,
# then call the handler directly.
# ---------------------------------------------------------------------------


def _make_mcp_server():
    """Build a bare MCP server for handler tests.

    Same shape as tests/mcp/test_get_school_programs.py:_make_server.
    Side-steps the heavy __init__ (catalog connection, formatter, ...)
    so the test is hermetic.
    """
    from unittest.mock import MagicMock

    from mcp_server.futureproof_server import FutureProofMCPServer

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


def _bare_row(unitid: int, name: str, *, confidence_tier: str = "high") -> dict:
    """Minimal row shape that satisfies the SCHOOL_PROGRAMS response."""
    return {
        "unitid": unitid,
        "institution_name": name,
        "institution_control": "Public",
        "cipcode": "52.01",
        "program_name": "Business",
        "cip_family_name": "Business",
        "earnings_1yr_median": 50_000.0,
        "earnings_1yr_p25": 40_000.0,
        "earnings_1yr_p75": 65_000.0,
        "debt_median": 22_000.0,
        "debt_p25": 15_000.0,
        "debt_p75": 28_000.0,
        "debt_to_earnings_annual": 0.44,
        "debt_to_earnings_tier": "Low",
        "program_value_index": 2.0,
        "confidence_tier": confidence_tier,
        "has_earnings": True,
        "has_debt": True,
        "outcome_completeness": 1.0,
        "net_price_annual": 14_200.0,
        "cost_of_attendance_annual": 22_800.0,
        "net_price_4yr": 56_800.0,
        "tuition_in_state": 9_800.0,
        "tuition_out_of_state": 21_400.0,
        "room_board_on_campus": 11_500.0,
        "state_abbr": "XX",
    }


class TestSchoolAliasMatch:
    """The alias matcher in `_handle_get_school_programs` maps colloquial
    school names to canonical IPEDS unitids that the substring + acronym
    matchers miss."""

    def test_school_search_alias_match(self):
        """'Penn State' is in data/reference/school_aliases.yaml mapping
        to canonical_unitid 495767. The handler must surface that row
        even though 'Penn State' is NOT a substring of the canonical
        name 'The Pennsylvania State University'."""
        from unittest.mock import patch

        from mcp_server.futureproof_server import _load_school_aliases

        # Force a fresh YAML load so the test sees the real curated file.
        _load_school_aliases.cache_clear()
        try:
            server = _make_mcp_server()
            # Seed rows: the canonical Penn State row + an unrelated row
            # that should NOT match.
            rows = [
                _bare_row(495767, "The Pennsylvania State University"),
                _bare_row(151351, "Indiana University-Bloomington"),
            ]
            with patch.object(
                server, "query_iceberg_simple", return_value=rows
            ):
                result = server._handle_get_school_programs(
                    {"school_name": "Penn State"}
                )

            assert result["data"] is not None, (
                f"Alias match for 'Penn State' must return data; got {result}"
            )
            unitids = {r["unitid"] for r in result["data"]}
            assert 495767 in unitids, (
                f"Alias-mapped unitid 495767 must surface for 'Penn State'; "
                f"got {unitids}"
            )
            # The unrelated Indiana row must NOT appear — it doesn't match
            # via alias, substring, acronym, or token-overlap for "Penn State".
            assert 151351 not in unitids
        finally:
            _load_school_aliases.cache_clear()


class TestSchoolTokenOverlap:
    """The token-overlap matcher fires when ALL 3+ char tokens in the
    query appear (as substring or prefix) in the candidate's name."""

    def test_school_search_token_overlap(self):
        """'UC Berkeley' has two tokens after normalization. Token-overlap
        must surface 'University of California-Berkeley' even though the
        literal string 'uc berkeley' isn't a substring of the canonical
        name. (The 'UC Berkeley' alias in the YAML ALSO matches this row,
        so either matcher path satisfies the test — what matters is that
        the row surfaces.)"""
        from unittest.mock import patch

        from mcp_server.futureproof_server import _load_school_aliases

        _load_school_aliases.cache_clear()
        try:
            server = _make_mcp_server()
            rows = [
                _bare_row(110635, "University of California-Berkeley"),
                _bare_row(110644, "University of California-Davis"),
                _bare_row(123456, "Berkeley Community College"),
            ]
            with patch.object(
                server, "query_iceberg_simple", return_value=rows
            ):
                result = server._handle_get_school_programs(
                    {"school_name": "UC Berkeley"}
                )

            assert result["data"] is not None
            unitids = {r["unitid"] for r in result["data"]}
            assert 110635 in unitids, (
                f"University of California-Berkeley (unitid 110635) must "
                f"surface for 'UC Berkeley'; got {unitids}"
            )
        finally:
            _load_school_aliases.cache_clear()

