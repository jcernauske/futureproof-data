"""Tests for app.services.pdf_copy — RPG-language enforcement, risk-level
mapping, anchor templates, data-coverage caveat, verdict line.

See docs/specs/feature-pdf-report-exports.md §4 New Tests Required (P0/P2
rows targeting test_pdf_copy.py).
"""

from __future__ import annotations

import re

import pytest

from app.models.api import AudienceQuestion, AudienceQuestions
from app.services import pdf_export
from app.services.pdf_copy import (
    FORBIDDEN_IN_GEMMA_OUTPUT,
    RPG_TERMS_FORBIDDEN_IN_PDF,
    data_coverage_caveat,
    risk_level_for_boss,
    risk_one_liner,
    verdict_line,
    where_each_pulls_ahead,
)

# ---------------------------------------------------------------------------
# Shared helpers — extract text from a generated PDF and run regex checks.
# ---------------------------------------------------------------------------


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Use pypdf to pull text out of a rendered PDF.

    pypdf is the project's accepted test-time PDF inspector — see the
    spec's §4 Test Data Requirements.
    """
    pypdf = pytest.importorskip("pypdf")
    from io import BytesIO

    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _make_audience_questions() -> AudienceQuestions:
    return AudienceQuestions(
        ask_the_college=[
            AudienceQuestion(
                text=(
                    "Which majors at Indiana University Bloomington most "
                    "often lead graduates into Mechanical Engineers?"
                ),
                is_static_mandatory=True,
            ),
            AudienceQuestion(
                text=(
                    "How can I augment this major with the suggested skills "
                    "above — through coursework, clubs, or internships?"
                ),
                is_static_mandatory=True,
            ),
            AudienceQuestion(
                text=(
                    "What outcomes data do you publish for this program — "
                    "median earnings, employment rate, debt at graduation?"
                ),
            ),
        ],
        ask_your_parents=[
            AudienceQuestion(
                text=(
                    "If the loan numbers on page 1 are accurate, can our "
                    "family carry that monthly payment after I graduate?"
                ),
            ),
        ],
        ask_yourself=[
            AudienceQuestion(
                text=(
                    "Will I still want to be doing this work in 10 years if "
                    "the day-to-day looks like the task profile on page 1?"
                ),
            ),
        ],
        gemma_path="live",
    )


# ---------------------------------------------------------------------------
# P0: RPG vocabulary must not appear anywhere in the rendered PDF text.
# ---------------------------------------------------------------------------


class TestNoRpgTerms:
    def test_no_rpg_terms_in_rendered_text(self, fixture_build):
        """Render a real PDF and assert no RPG_TERMS_FORBIDDEN_IN_PDF leak.

        Decision #4 enforcement — the non-negotiable test. Asserted
        against RPG_TERMS_FORBIDDEN_IN_PDF (NOT the FORBIDDEN_IN_GEMMA_OUTPUT
        superset) because the PDF chrome deliberately renders the stat
        abbreviations (ERN/ROI/RES/GRW/AURA) in the pentagon, micro-table,
        and glossary.
        """
        pdf_bytes = pdf_export.generate_build_pdf(
            fixture_build,
            student_name=None,
            audience_questions=_make_audience_questions(),
        )
        text = _extract_pdf_text(pdf_bytes).lower()

        # Word-boundary regex per spec: hyphenated forms ("level-up", "boss
        # fight") are checked verbatim against the lower-cased corpus.
        for term in RPG_TERMS_FORBIDDEN_IN_PDF:
            # ``re.escape`` so embedded spaces/hyphens stay literal.
            # Anchor with \b on both sides so 'win' doesn't match 'winning';
            # the forbidden set also includes 'winning'-shaped variants
            # explicitly when they're meant to fail.
            pattern = re.compile(
                r"\b" + re.escape(term.lower()) + r"\b",
            )
            match = pattern.search(text)
            assert match is None, (
                f"RPG term {term!r} leaked into rendered PDF text: "
                f"...{text[max(0, match.start() - 30):match.end() + 30]}..."
                if match
                else ""
            )

    def test_full_pdf_text_includes_stat_abbreviations(self, fixture_build):
        """Sanity-check: ERN/ROI/RES/GRW/AURA SHOULD appear in the chrome.

        This guards against an over-eager future patch that adds the stat
        abbreviations to RPG_TERMS_FORBIDDEN_IN_PDF — the PDF would still
        render them in the pentagon, micro-table, and glossary, and the
        no-RPG-terms test would fire incorrectly. Belt-and-suspenders.
        """
        pdf_bytes = pdf_export.generate_build_pdf(
            fixture_build,
            student_name=None,
            audience_questions=_make_audience_questions(),
        )
        text = _extract_pdf_text(pdf_bytes)
        # The micro-table renders the abbreviations as-is.
        assert "ERN" in text
        assert "ROI" in text


# ---------------------------------------------------------------------------
# P0: risk_level_for_boss — deterministic per-boss thresholds + None handling.
# ---------------------------------------------------------------------------


class TestRiskLevelMapping:
    """For each (boss_id, raw_score) pair, assert risk_level_for_boss
    returns the expected RiskLevel. Includes raw_score=None for every
    boss returning 'Insufficient' — the missing-data-is-not-zero rule.
    """

    # Threshold table per app.services.boss_fights.BOSS_SPECS:
    #   ai      win=14  draw=10  → Elevated band starts at floor(10/2)=5
    #   loans   win=7   draw=5   → Elevated band starts at floor(5/2)=2
    #   market  win=6   draw=4   → Elevated band starts at floor(4/2)=2
    #   burnout win=7   draw=5   → Elevated band starts at floor(5/2)=2
    #   ceiling win=7   draw=5   → Elevated band starts at floor(5/2)=2

    @pytest.mark.parametrize(
        "boss_id, raw_score, expected_level",
        [
            # AI boss
            ("ai", 20, "Low"),
            ("ai", 14, "Low"),
            ("ai", 13, "Moderate"),
            ("ai", 10, "Moderate"),
            ("ai", 9, "Elevated"),
            ("ai", 5, "Elevated"),
            ("ai", 4, "High"),
            ("ai", 0, "High"),
            # Loans boss
            ("loans", 9, "Low"),
            ("loans", 7, "Low"),
            ("loans", 6, "Moderate"),
            ("loans", 5, "Moderate"),
            ("loans", 4, "Elevated"),
            ("loans", 2, "Elevated"),
            ("loans", 1, "High"),
            ("loans", 0, "High"),
            # Market boss
            ("market", 8, "Low"),
            ("market", 6, "Low"),
            ("market", 5, "Moderate"),
            ("market", 4, "Moderate"),
            ("market", 3, "Elevated"),
            ("market", 2, "Elevated"),
            ("market", 1, "High"),
            ("market", 0, "High"),
            # Burnout boss
            ("burnout", 9, "Low"),
            ("burnout", 7, "Low"),
            ("burnout", 6, "Moderate"),
            ("burnout", 5, "Moderate"),
            ("burnout", 4, "Elevated"),
            ("burnout", 2, "Elevated"),
            ("burnout", 1, "High"),
            ("burnout", 0, "High"),
            # Ceiling boss
            ("ceiling", 9, "Low"),
            ("ceiling", 7, "Low"),
            ("ceiling", 6, "Moderate"),
            ("ceiling", 5, "Moderate"),
            ("ceiling", 4, "Elevated"),
            ("ceiling", 2, "Elevated"),
            ("ceiling", 1, "High"),
            ("ceiling", 0, "High"),
        ],
    )
    def test_risk_level_per_boss_thresholds_match_data_reviewer_table(
        self, boss_id, raw_score, expected_level
    ):
        """All 5 bosses × all 4 thresholds: deterministic mapping holds."""
        assert risk_level_for_boss(boss_id, raw_score) == expected_level

    @pytest.mark.parametrize("boss_id", ["ai", "loans", "market", "burnout", "ceiling"])
    def test_none_raw_score_returns_insufficient_not_high(self, boss_id):
        """The missing-data-is-not-zero rule. NEVER returns 'High'.

        Per @fp-data-reviewer §5 round-1 ruling, re-confirmed round 2.
        This is the load-bearing assertion of the whole risk-chip path.
        """
        result = risk_level_for_boss(boss_id, None)
        assert result == "Insufficient"
        assert result != "High"


# ---------------------------------------------------------------------------
# P0: data_coverage_caveat — None for full, strings for partial.
# ---------------------------------------------------------------------------


class TestDataCoverageCaveat:
    def test_returns_none_for_full_match_quality(self, fixture_build):
        """Full coverage → no caveat line rendered."""
        assert fixture_build.career.match_quality == "full"
        assert data_coverage_caveat(fixture_build) is None

    def test_returns_caveat_for_scorecard_only(self, fixture_build_scorecard_only):
        result = data_coverage_caveat(fixture_build_scorecard_only)
        assert result is not None
        assert isinstance(result, str)
        # Caveat must explicitly reference the partial coverage.
        assert "partial" in result.lower() or "unavailable" in result.lower()
        # Must NOT use RPG vocab in the caveat itself (defense in depth).
        for term in ("boss", "fight", "gauntlet", "win", "lose"):
            assert term not in result.lower()

    def test_returns_caveat_for_partial_no_onet(self, fixture_build_partial_no_onet):
        result = data_coverage_caveat(fixture_build_partial_no_onet)
        assert result is not None
        assert isinstance(result, str)
        # The partial_no_onet caveat references O*NET task data.
        assert "O*NET" in result or "task" in result.lower()

    def test_returns_none_for_missing_match_quality(self, fixture_build):
        """An unset/None match_quality → no caveat (treated as 'unknown')."""
        fixture_build.career.match_quality = None
        assert data_coverage_caveat(fixture_build) is None

    def test_returns_none_for_unknown_match_quality_value(self, fixture_build):
        """Defensive: an unrecognized value returns None, doesn't crash."""
        fixture_build.career.match_quality = "some_unknown_value"
        assert data_coverage_caveat(fixture_build) is None


# ---------------------------------------------------------------------------
# P0: risk_one_liner — null anchor falls back, never produces "None%".
# ---------------------------------------------------------------------------


class TestRiskOneLinerHandlesNullAnchor:
    def test_ai_no_adoption_percentile_falls_back(self, fixture_build):
        """When career.adoption_percentile is None, we render the level-only
        sentence — NOT a string with 'None%' or '${None}' in it.
        """
        fixture_build.career.adoption_percentile = None
        result = risk_one_liner("ai", "Elevated", fixture_build)
        assert "None" not in result
        assert "{p" not in result
        # Level-only fallback contains the level descriptor.
        assert "elevated" in result.lower() or "AI" in result

    def test_loans_no_dte_falls_back(self, fixture_build):
        fixture_build.career.debt_to_earnings_annual = None
        result = risk_one_liner("loans", "High", fixture_build)
        assert "None" not in result
        assert "%" not in result or not re.search(r"None\s*%", result)

    def test_market_no_growth_category_falls_back(self, fixture_build):
        fixture_build.career.growth_category = None
        result = risk_one_liner("market", "Moderate", fixture_build)
        assert "None" not in result
        assert "{label" not in result

    def test_burnout_no_drivers_falls_back(self, fixture_build):
        fixture_build.career.burnout_drivers = []
        result = risk_one_liner("burnout", "Elevated", fixture_build)
        assert "None" not in result
        assert "{driver" not in result

    def test_ceiling_no_p75_falls_back(self, fixture_build):
        fixture_build.career.earnings_1yr_p75 = None
        result = risk_one_liner("ceiling", "Low", fixture_build)
        assert "None" not in result
        assert "${None" not in result
        assert "{v" not in result

    @pytest.mark.parametrize(
        "boss_id", ["ai", "loans", "market", "burnout", "ceiling"]
    )
    def test_insufficient_level_always_returns_data_unavailable(
        self, boss_id, fixture_build
    ):
        """Insufficient level → 'Data unavailable for this program.' for
        every boss. Counselor-scanning aid (§3.11.2)."""
        out = risk_one_liner(boss_id, "Insufficient", fixture_build)
        assert "unavailable" in out.lower()
        assert "None" not in out

    def test_with_anchor_data_includes_numeric_value(self, fixture_build):
        """Sanity check: when anchor data IS present, the template format
        substitution actually fires (otherwise the fallback test above
        wouldn't be load-bearing)."""
        fixture_build.career.adoption_percentile = 0.42  # 42nd percentile
        result = risk_one_liner("ai", "Moderate", fixture_build)
        # The template renders {p:.0f} → 42 (no decimal).
        assert "42" in result
        assert "None" not in result


# ---------------------------------------------------------------------------
# P2: verdict line length budget.
# ---------------------------------------------------------------------------


class TestVerdictLineBudget:
    def test_verdict_line_within_200_chars(self, fixture_build):
        """Verdict line ≤ 200 chars — single-line at display 24pt (§3.5)."""
        out = verdict_line(fixture_build)
        assert len(out) <= 200, (
            f"verdict line exceeds 200 char budget: len={len(out)}, "
            f"text={out!r}"
        )

    def test_verdict_line_within_budget_for_long_school_name(self):
        """Long school + program names still fit the budget."""
        from tests.services.conftest import make_fixture_build  # type: ignore

        b = make_fixture_build(
            school_name="University of California Riverside Bourns College",
            program_name="Mechanical and Aerospace Systems Engineering",
            major_text="Mechanical and Aerospace Systems Engineering",
        )
        out = verdict_line(b)
        assert len(out) <= 200, (
            f"verdict line exceeds 200 char budget: len={len(out)}, "
            f"text={out!r}"
        )

    def test_verdict_line_no_rpg_terms(self, fixture_build):
        """Verdict line never leaks RPG language."""
        out = verdict_line(fixture_build).lower()
        for term in ("boss", "gauntlet", "fight", "won", "lost", "draw"):
            assert (
                re.search(r"\b" + re.escape(term) + r"\b", out) is None
            ), f"verdict line contains forbidden term {term!r}: {out!r}"


# ---------------------------------------------------------------------------
# Forbidden-set hygiene. Belt-and-suspenders: superset must contain RPG.
# ---------------------------------------------------------------------------


class TestForbiddenSetsConsistency:
    def test_gemma_forbidden_is_strict_superset_of_pdf_forbidden(self):
        """FORBIDDEN_IN_GEMMA_OUTPUT must include every term in the PDF
        forbidden set, plus the stat abbreviations.

        The two-frozenset distinction is load-bearing — the PDF chrome
        renders ERN/ROI/RES/GRW/AURA legitimately, so the PDF-text test
        cannot use the superset. But Gemma must never output those
        abbreviations because the PDF text post-filters them.
        """
        assert RPG_TERMS_FORBIDDEN_IN_PDF.issubset(FORBIDDEN_IN_GEMMA_OUTPUT)
        # Stat abbreviations must be in the Gemma-only filter.
        for abbr in ("ern", "roi", "res", "grw", "aura"):
            assert abbr in FORBIDDEN_IN_GEMMA_OUTPUT, (
                f"stat abbreviation {abbr!r} missing from "
                "FORBIDDEN_IN_GEMMA_OUTPUT — Gemma post-filter loses teeth"
            )

    def test_pdf_forbidden_omits_stat_abbreviations(self):
        """The PDF-text filter MUST NOT include stat abbreviations — the
        chrome renders them. Including them would make the no-RPG test
        fail incorrectly on every PDF."""
        for abbr in ("ern", "roi", "res", "grw", "aura"):
            assert abbr not in RPG_TERMS_FORBIDDEN_IN_PDF, (
                f"{abbr!r} must NOT be in RPG_TERMS_FORBIDDEN_IN_PDF — "
                "the pentagon/micro-table/glossary render it legitimately"
            )


# ---------------------------------------------------------------------------
# P0: where_each_pulls_ahead does NOT claim leadership when all peers are None.
# Staff-engineer §8 finding A4 — walrus short-circuit incorrectly returned
# True when comparing N values to all-None peers.
# ---------------------------------------------------------------------------


class TestWhereEachPullsAheadAllNonePeers:
    def test_no_leadership_claimed_when_all_peer_values_none(self):
        """A build with `ERN=5` should NOT lead Earnings when both peers
        have `ERN=None` — there's nothing to compare against. Should
        render the "no clear leader" copy, not "leads on Earnings"."""
        from tests.services.conftest import make_fixture_build  # type: ignore

        my = make_fixture_build(
            cipcode="14.1901",
            school_name="My U",
            stats_override={"ern": 5, "roi": 5, "res": 5, "grw": 5, "aura": 5},
        )
        # Two peers with the same major but ALL stats None.
        peer1 = make_fixture_build(
            cipcode="14.1902",
            school_name="Peer A",
            stats_override={
                "ern": None, "roi": None, "res": None, "grw": None, "aura": None,
            },
        )
        peer2 = make_fixture_build(
            cipcode="14.1903",
            school_name="Peer B",
            stats_override={
                "ern": None, "roi": None, "res": None, "grw": None, "aura": None,
            },
        )
        lines = where_each_pulls_ahead([my, peer1, peer2])
        assert len(lines) == 3
        # My U should land on the "no clear leader" template, NOT a
        # leadership claim against absent data.
        assert "no clear leader" in lines[0], (
            f"expected 'no clear leader' in {lines[0]!r}; "
            "build with all peers None must not claim leadership"
        )
        assert "leads on" not in lines[0]

    def test_leadership_claimed_when_at_least_one_peer_has_value(self):
        """Sanity check the inverse: when ANY peer has a value, a higher
        value DOES claim leadership (the ordinary path)."""
        from tests.services.conftest import make_fixture_build  # type: ignore

        my = make_fixture_build(
            cipcode="14.1901",
            school_name="My U",
            stats_override={"ern": 8, "roi": 5, "res": 5, "grw": 5, "aura": 5},
        )
        peer1 = make_fixture_build(
            cipcode="14.1902",
            school_name="Peer A",
            stats_override={
                "ern": 4, "roi": None, "res": None, "grw": None, "aura": None,
            },
        )
        peer2 = make_fixture_build(
            cipcode="14.1903",
            school_name="Peer B",
            stats_override={
                "ern": None, "roi": None, "res": None, "grw": None, "aura": None,
            },
        )
        lines = where_each_pulls_ahead([my, peer1, peer2])
        # My U has ERN=8 vs peer1's ERN=4 (peer2 None). My should lead.
        assert "Earnings" in lines[0], (
            f"expected leadership in {lines[0]!r}"
        )
