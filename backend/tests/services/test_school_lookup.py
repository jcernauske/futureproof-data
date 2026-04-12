"""Tests for school lookup + major resolution flow.

MCP calls are patched so these tests are hermetic. The Gemma fallback
is also patched to avoid live model calls.
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


@pytest.fixture
def stub_yaml_lookup(monkeypatch):
    """Stub the shared MCP server's _find_major_intent method."""
    from app.services import mcp_client

    class _Stub:
        def __init__(self):
            self.table: dict[str, dict] = {}

        def _find_major_intent(self, major_text: str) -> dict | None:
            return self.table.get(major_text.lower().strip())

    stub = _Stub()
    monkeypatch.setattr(mcp_client, "get_server", lambda: stub)
    return stub


@pytest.fixture
def stub_gemma(monkeypatch):
    from app.services import gemma_client

    state = {"response": ""}

    def fake_generate(**kwargs):
        return state["response"]

    monkeypatch.setattr(gemma_client, "generate", fake_generate)
    return state


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
# resolve_major
# ---------------------------------------------------------------------------


def _programs_sample() -> list[Program]:
    return [
        Program(
            unitid=151351,
            institution_name="IU-B",
            cipcode="52.01",
            program_name="Business/Commerce, General",
        ),
        Program(
            unitid=151351,
            institution_name="IU-B",
            cipcode="52.03",
            program_name="Accounting",
        ),
        Program(
            unitid=151351,
            institution_name="IU-B",
            cipcode="26.01",
            program_name="Biology/Biological Sciences, General",
        ),
    ]


class TestResolveMajor:
    def test_exact_match(self, stub_yaml_lookup, stub_gemma):
        match = school_lookup.resolve_major("Accounting", _programs_sample())
        assert match.method == "exact"
        assert match.cipcode == "52.03"

    def test_case_insensitive_exact(self, stub_yaml_lookup, stub_gemma):
        match = school_lookup.resolve_major("accounting", _programs_sample())
        assert match.method == "exact"

    def test_substring_match_biology(self, stub_yaml_lookup, stub_gemma):
        match = school_lookup.resolve_major("Biology", _programs_sample())
        assert match.method == "substring"
        assert match.cipcode == "26.01"

    def test_yaml_lookup_fires_substitution(
        self, stub_yaml_lookup, stub_gemma
    ):
        stub_yaml_lookup.table["marketing"] = {
            "major": "Marketing",
            "cip4": "52.14",
            "cip_family": "52",
        }
        match = school_lookup.resolve_major("Marketing", _programs_sample())
        assert match.method == "yaml"
        assert match.cipcode == "52.14"
        assert match.substitution_applied is True
        assert match.reported_cipcode == "52.01"

    def test_yaml_lookup_no_substitution_when_no_broad_cip(
        self, stub_yaml_lookup, stub_gemma
    ):
        # No 52.01 in the program list — yaml match is informational.
        programs = [
            Program(
                unitid=1,
                institution_name="X",
                cipcode="11.07",
                program_name="Computer Science",
            )
        ]
        stub_yaml_lookup.table["accountancy"] = {
            "major": "Accounting",
            "cip4": "52.03",
            "cip_family": "52",
        }
        match = school_lookup.resolve_major("Accountancy", programs)
        assert match.method == "yaml"
        assert match.substitution_applied is False

    def test_gemma_fallback_returns_matching_cipcode(
        self, stub_yaml_lookup, stub_gemma
    ):
        stub_gemma["response"] = "26.01"
        match = school_lookup.resolve_major(
            "Some Obscure Thing", _programs_sample()
        )
        assert match.method == "gemma"
        assert match.cipcode == "26.01"

    def test_gemma_returns_none_marks_unmatched(
        self, stub_yaml_lookup, stub_gemma
    ):
        stub_gemma["response"] = "NONE"
        match = school_lookup.resolve_major("Zzz", _programs_sample())
        assert match.method == "unmatched"

    def test_empty_major_is_unmatched(self, stub_yaml_lookup, stub_gemma):
        match = school_lookup.resolve_major("", _programs_sample())
        assert match.method == "unmatched"
        match2 = school_lookup.resolve_major("   ", _programs_sample())
        assert match2.method == "unmatched"

    def test_pure_digit_input_rejected_without_calling_gemma(
        self, stub_yaml_lookup, stub_gemma, monkeypatch
    ):
        """Menu index leakage: a raw '2' must never reach the Gemma
        CIP mapper — earlier bug had 'Student major: 2' in the log.
        """
        from app.services import gemma_client

        call_count = {"n": 0}

        def fail_on_call(**kwargs):
            call_count["n"] += 1
            return ""

        monkeypatch.setattr(gemma_client, "generate", fail_on_call)

        match = school_lookup.resolve_major("2", _programs_sample())
        assert match.method == "unmatched"
        assert "menu number" in (match.note or "").lower()
        assert call_count["n"] == 0

    def test_multi_digit_input_also_rejected(
        self, stub_yaml_lookup, stub_gemma, monkeypatch
    ):
        from app.services import gemma_client

        call_count = {"n": 0}
        monkeypatch.setattr(
            gemma_client,
            "generate",
            lambda **kw: (call_count.__setitem__("n", call_count["n"] + 1), "")[1],
        )
        match = school_lookup.resolve_major("42", _programs_sample())
        assert match.method == "unmatched"
        assert call_count["n"] == 0

    def test_non_digit_text_still_resolves_normally(
        self, stub_yaml_lookup, stub_gemma
    ):
        """Only pure digits are rejected; normal major text resolves
        through exact / substring as before."""
        match = school_lookup.resolve_major("Accounting", _programs_sample())
        assert match.method in ("exact", "substring")
        assert match.cipcode == "52.03"
