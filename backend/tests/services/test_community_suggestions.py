"""Tests for ``app.services.community_suggestions``.

Covers the invariants that keep the reinforcement loop honest:
- ``normalize_input`` is THE pinned normalization function. Every writer
  and reader shares it. Diverging normalization was the single biggest
  cause of a cold-looking suggestion surface next to a populated log.
- ``rebuild`` tolerates corrupt JSONL lines without crashing startup.
- ``rebuild`` / ``_apply_record`` filter to cacheable feasibility modes
  only. The two "not reachable" modes (``school_gap``,
  ``genuinely_impossible``) MUST NOT contribute to suggestions —
  surfacing them would learn noise.
- ``get_suggestions`` honors ``COMMUNITY_MIN_COUNT``.
- ``get_suggestions`` ranks by count descending, breaks ties by title.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.services import community_suggestions, correction_log


@pytest.fixture
def tmp_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Redirect project_root() to tmp_path and reset the aggregate."""
    monkeypatch.setattr(community_suggestions, "project_root", lambda: tmp_path)
    monkeypatch.setattr(correction_log, "project_root", lambda: tmp_path)
    from app.services import mcp_client

    monkeypatch.setattr(mcp_client, "project_root", lambda: tmp_path)
    community_suggestions.reset_for_tests()
    yield tmp_path
    community_suggestions.reset_for_tests()


def _write_lines(tmp_project: Path, records: list[dict[str, Any]]) -> Path:
    """Seed the log file under the tmp project root."""
    log = tmp_project / "data" / "reference" / "student_corrections.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    return log


def _record(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_version": "1.0",
        "kind": "correction",
        "timestamp": "2026-04-01T12:00:00+00:00",
        "school_unitid": 151351,
        "school_name": "IU",
        "input_normalized": "marketing",
        "initial_major_text": "marketing",
        "initial_cip4": "52.01",
        "final_cip4": "52.14",
        "clicked_soc": "11-2021",
        "clicked_career_title": "Marketing Manager",
        "feasibility_mode": "direct_hit",
        "chips_tapped": [],
        "clarifier": None,
        "bucket": None,
        "backend": "stub",
        "model": "stub",
    }
    base.update(overrides)
    return base


class TestNormalizeInput:
    def test_strips_trailing_and_leading_whitespace(self) -> None:
        assert community_suggestions.normalize_input("  marketing  ") == "marketing"

    def test_lowercases(self) -> None:
        assert community_suggestions.normalize_input("Marketing") == "marketing"
        assert community_suggestions.normalize_input("MARKETING") == "marketing"

    def test_collapses_internal_whitespace(self) -> None:
        assert (
            community_suggestions.normalize_input("deaf    education")
            == "deaf education"
        )
        assert (
            community_suggestions.normalize_input("deaf\teducation")
            == "deaf education"
        )
        assert (
            community_suggestions.normalize_input("deaf\neducation")
            == "deaf education"
        )

    def test_none_returns_empty(self) -> None:
        assert community_suggestions.normalize_input(None) == ""  # type: ignore[arg-type]

    def test_empty_string_returns_empty(self) -> None:
        assert community_suggestions.normalize_input("") == ""
        assert community_suggestions.normalize_input("   ") == ""


class TestRebuild:
    def test_empty_when_file_missing(self, tmp_project: Path) -> None:
        community_suggestions.rebuild()
        assert (
            community_suggestions.get_suggestions(
                unitid=1, input_normalized="anything"
            )
            == []
        )

    def test_tolerates_corrupt_lines(self, tmp_project: Path) -> None:
        """A corrupt line logs a warning and is skipped — downstream
        callers never see it. This is the contract for a log that is
        committed to git and may have been hand-edited."""
        log = tmp_project / "data" / "reference" / "student_corrections.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("w", encoding="utf-8") as fh:
            fh.write(json.dumps(_record()) + "\n")
            fh.write("{ this is not valid json }\n")
            fh.write("\n")  # blank line
            fh.write(json.dumps(_record(clicked_career_title="Brand Manager")) + "\n")
            fh.write("[]\n")  # wrong type — not a dict
            fh.write(json.dumps(_record(school_unitid=None)) + "\n")  # coercion fails

        community_suggestions.rebuild()
        suggestions = community_suggestions.get_suggestions(
            unitid=151351, input_normalized="marketing"
        )
        # Only the two clean records should have landed.
        titles = sorted(s["clicked_career_title"] for s in suggestions)
        assert titles == ["Brand Manager", "Marketing Manager"]

    def test_filters_non_cacheable_feasibility_modes(
        self, tmp_project: Path
    ) -> None:
        """school_gap + genuinely_impossible must NEVER surface as
        suggestions. Logging them is fine for audit, but the
        reinforcement loop must not learn noise."""
        _write_lines(
            tmp_project,
            [
                _record(feasibility_mode="direct_hit"),
                _record(
                    feasibility_mode="crosswalk_quirk",
                    clicked_career_title="Brand Strategist",
                ),
                _record(
                    feasibility_mode="adjacent_reachable",
                    clicked_career_title="Product Marketing",
                ),
                _record(
                    feasibility_mode="school_gap",
                    clicked_career_title="Nurse Practitioner",
                ),
                _record(
                    feasibility_mode="genuinely_impossible",
                    clicked_career_title="Rocket Surgeon",
                ),
                _record(
                    feasibility_mode=None,
                    clicked_career_title="Unknown Job",
                ),
            ],
        )
        community_suggestions.rebuild()
        suggestions = community_suggestions.get_suggestions(
            unitid=151351, input_normalized="marketing", top_k=10
        )
        titles = {s["clicked_career_title"] for s in suggestions}
        # Only the three cacheable modes surface.
        assert titles == {
            "Marketing Manager",
            "Brand Strategist",
            "Product Marketing",
        }
        # Explicitly: the blocked modes must be absent.
        assert "Nurse Practitioner" not in titles
        assert "Rocket Surgeon" not in titles
        assert "Unknown Job" not in titles


class TestGetSuggestions:
    def test_respects_community_min_count(
        self, tmp_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A suggestion below threshold must NOT surface. The default
        threshold is 1 (hackathon mode); setting it to 2 means a
        single-count entry disappears."""
        _write_lines(
            tmp_project,
            [
                # Marketing Manager — count 2 (surfaces at threshold 2).
                _record(),
                _record(),
                # Brand Strategist — count 1 (filtered at threshold 2).
                _record(clicked_career_title="Brand Strategist"),
            ],
        )
        monkeypatch.setenv("COMMUNITY_MIN_COUNT", "2")
        community_suggestions.rebuild()
        suggestions = community_suggestions.get_suggestions(
            unitid=151351, input_normalized="marketing"
        )
        titles = [s["clicked_career_title"] for s in suggestions]
        assert titles == ["Marketing Manager"]
        assert all(s["count"] >= 2 for s in suggestions)

    def test_ranked_by_count_descending(self, tmp_project: Path) -> None:
        """Higher-count entries land first."""
        _write_lines(
            tmp_project,
            [
                _record(clicked_soc="A", clicked_career_title="Alpha"),
                _record(clicked_soc="A", clicked_career_title="Alpha"),
                _record(clicked_soc="A", clicked_career_title="Alpha"),
                _record(clicked_soc="B", clicked_career_title="Beta"),
            ],
        )
        community_suggestions.rebuild()
        suggestions = community_suggestions.get_suggestions(
            unitid=151351, input_normalized="marketing"
        )
        assert [s["clicked_career_title"] for s in suggestions] == ["Alpha", "Beta"]
        assert suggestions[0]["count"] == 3
        assert suggestions[1]["count"] == 1

    def test_top_k_clamps_result_length(self, tmp_project: Path) -> None:
        _write_lines(
            tmp_project,
            [
                _record(clicked_soc="A", clicked_career_title="A"),
                _record(clicked_soc="B", clicked_career_title="B"),
                _record(clicked_soc="C", clicked_career_title="C"),
                _record(clicked_soc="D", clicked_career_title="D"),
            ],
        )
        community_suggestions.rebuild()
        suggestions = community_suggestions.get_suggestions(
            unitid=151351, input_normalized="marketing", top_k=2
        )
        assert len(suggestions) == 2

    def test_tie_break_on_title_alpha(self, tmp_project: Path) -> None:
        """Two entries with the same count break the tie alphabetically
        by title so ordering is deterministic for the frontend."""
        _write_lines(
            tmp_project,
            [
                _record(clicked_soc="A", clicked_career_title="Zeta"),
                _record(clicked_soc="B", clicked_career_title="Alpha"),
            ],
        )
        community_suggestions.rebuild()
        suggestions = community_suggestions.get_suggestions(
            unitid=151351, input_normalized="marketing"
        )
        assert [s["clicked_career_title"] for s in suggestions] == ["Alpha", "Zeta"]

    def test_different_unitids_do_not_cross_contaminate(
        self, tmp_project: Path
    ) -> None:
        _write_lines(
            tmp_project,
            [
                _record(school_unitid=1, clicked_career_title="ForSchool1"),
                _record(school_unitid=2, clicked_career_title="ForSchool2"),
            ],
        )
        community_suggestions.rebuild()

        s1 = community_suggestions.get_suggestions(
            unitid=1, input_normalized="marketing"
        )
        s2 = community_suggestions.get_suggestions(
            unitid=2, input_normalized="marketing"
        )
        assert [x["clicked_career_title"] for x in s1] == ["ForSchool1"]
        assert [x["clicked_career_title"] for x in s2] == ["ForSchool2"]
