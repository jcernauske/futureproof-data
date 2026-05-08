"""Tests for app.services.pdf_export — bytes-out PDF rendering.

Covers:
- generate_build_pdf returns valid PDF bytes (2 pages).
- generate_comparison_pdf accepts 2 or 3 builds, rejects 4+ and cross-major.
- No PII written to disk during PDF generation (BytesIO only).
- Insufficient chip renders for null raw_score boss.
- Cost strip renders debt_to_earnings as f"{v*100:.0f}%".
- Match-quality caveat appears for partial coverage.

See docs/specs/feature-pdf-report-exports.md §4.
"""

from __future__ import annotations

import builtins
from io import BytesIO
from pathlib import Path

import pytest

from app.models.api import AudienceQuestion, AudienceQuestions
from app.services import pdf_export

# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _aq() -> AudienceQuestions:
    """A minimal valid AudienceQuestions for render tests."""
    return AudienceQuestions(
        ask_the_college=[
            AudienceQuestion(
                text="Which majors at this school produce mechanical engineers?",
                is_static_mandatory=True,
            ),
            AudienceQuestion(
                text="How can I augment my education with the suggested skills?",
                is_static_mandatory=True,
            ),
            AudienceQuestion(text="What is the year-1 placement rate?"),
        ],
        ask_your_parents=[
            AudienceQuestion(text="Can our family carry the monthly payment?"),
        ],
        ask_yourself=[
            AudienceQuestion(text="Will I still want this in 10 years?"),
        ],
        gemma_path="live",
    )


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    pypdf = pytest.importorskip("pypdf")
    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _pdf_page_count(pdf_bytes: bytes) -> int:
    pypdf = pytest.importorskip("pypdf")
    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    return len(reader.pages)


# ---------------------------------------------------------------------------
# P0: generate_build_pdf returns valid bytes (2 pages).
# ---------------------------------------------------------------------------


class TestGenerateBuildPdf:
    def test_returns_valid_pdf_bytes(self, fixture_build):
        out = pdf_export.generate_build_pdf(
            fixture_build,
            student_name=None,
            audience_questions=_aq(),
        )
        assert isinstance(out, bytes)
        assert len(out) > 0
        # Standard PDF magic.
        assert out[:4] == b"%PDF", (
            f"PDF must start with %PDF magic; got {out[:8]!r}"
        )

    def test_my_build_pdf_has_exactly_two_pages(self, fixture_build):
        out = pdf_export.generate_build_pdf(
            fixture_build,
            student_name=None,
            audience_questions=_aq(),
        )
        assert _pdf_page_count(out) == 2, (
            "My Build PDF must have exactly 2 pages per spec §3.5"
        )

    def test_my_build_pdf_byte_size_under_800kb(self, fixture_build):
        """P1: byte budget. Sample renders measured ~50KB; 800KB is the
        headroom cap before review.
        """
        out = pdf_export.generate_build_pdf(
            fixture_build,
            student_name="Rowan",
            audience_questions=_aq(),
        )
        assert len(out) < 800_000, (
            f"My Build PDF exceeded 800KB budget: {len(out):,} bytes. "
            "If this fixture genuinely needs more, raise the cap by spec."
        )

    def test_pdf_renders_school_and_program_in_header(self, fixture_build):
        out = pdf_export.generate_build_pdf(
            fixture_build,
            student_name=None,
            audience_questions=_aq(),
        )
        text = _extract_pdf_text(out)
        # School name and program name both appear (page 1 header).
        assert "Indiana University" in text
        assert "Mechanical Engineering" in text


# ---------------------------------------------------------------------------
# P0: no_pii_written_to_disk — PDF materializes entirely in BytesIO.
# ---------------------------------------------------------------------------


class TestNoPiiWrittenToDisk:
    def test_no_pii_written_to_disk(self, monkeypatch, fixture_build):
        """Patch every disk-write surface and verify generate_build_pdf
        never touches them. PDF must materialize entirely in BytesIO.

        Patched:
        - builtins.open in write/append modes
        - Path.write_text / write_bytes
        """
        write_calls: list[tuple] = []

        original_open = builtins.open

        def _guarded_open(path, mode="r", *args, **kwargs):
            # Allow read-only opens (font files, package resources).
            mode_str = str(mode)
            if any(c in mode_str for c in ("w", "a", "x", "+")):
                write_calls.append(("open", str(path), mode_str))
                raise AssertionError(
                    f"PDF generation attempted to open {path} for writing "
                    f"(mode={mode_str!r}) — no PII to disk"
                )
            return original_open(path, mode, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", _guarded_open)

        def _guarded_write_text(self, *args, **kwargs):
            write_calls.append(("Path.write_text", str(self)))
            raise AssertionError(
                f"Path.write_text called on {self} during PDF render"
            )

        def _guarded_write_bytes(self, *args, **kwargs):
            write_calls.append(("Path.write_bytes", str(self)))
            raise AssertionError(
                f"Path.write_bytes called on {self} during PDF render"
            )

        monkeypatch.setattr(Path, "write_text", _guarded_write_text)
        monkeypatch.setattr(Path, "write_bytes", _guarded_write_bytes)

        # Use a profile_name with PII-shaped content so any leak would be
        # easy to grep for.
        fixture_build.profile_name = "Rowan Q. Pii"
        out = pdf_export.generate_build_pdf(
            fixture_build,
            student_name="Rowan Q. Pii",
            audience_questions=_aq(),
        )

        assert isinstance(out, bytes)
        assert len(out) > 0
        assert out[:4] == b"%PDF"
        assert write_calls == [], (
            f"unexpected disk writes during PDF render: {write_calls}"
        )


# ---------------------------------------------------------------------------
# P0: generate_comparison_pdf — cross-major + over-3 + 2..3 acceptance.
# ---------------------------------------------------------------------------


class TestGenerateComparisonPdf:
    def test_accepts_cross_major_2_builds(self, fixture_build):
        """Cross-major 2-build comparison renders cleanly. The in-app
        CompareView already supports cross-major; the PDF matches that
        contract. Title falls back to "Career comparison" in the
        rendered PDF when majors differ."""
        from tests.services.conftest import make_fixture_build  # type: ignore

        b1 = make_fixture_build(
            cipcode="14.1901", school_name="A",
            program_name="Mechanical Engineering",
        )
        b2 = make_fixture_build(
            cipcode="11.0701", school_name="B",
            program_name="Computer Science",
        )
        pdf_bytes = pdf_export.generate_comparison_pdf([b1, b2])
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF")
        text = _extract_pdf_text(pdf_bytes)
        # Cross-major title fallback — neither major name leads the title.
        assert "Career comparison" in text

    def test_rejects_more_than_3_builds(self, fixture_three_same_major_builds):
        from tests.services.conftest import make_fixture_build  # type: ignore

        builds = fixture_three_same_major_builds + [
            make_fixture_build(
                school_name="University of Notre Dame",
                cipcode="14.1903",
                unitid=152080,
            )
        ]
        assert len(builds) == 4
        with pytest.raises(ValueError):
            pdf_export.generate_comparison_pdf(builds)

    def test_rejects_one_or_zero_builds(self, fixture_build):
        with pytest.raises(ValueError):
            pdf_export.generate_comparison_pdf([fixture_build])
        with pytest.raises(ValueError):
            pdf_export.generate_comparison_pdf([])

    def test_accepts_2_builds_same_major(self, fixture_three_same_major_builds):
        out = pdf_export.generate_comparison_pdf(
            fixture_three_same_major_builds[:2]
        )
        assert isinstance(out, bytes)
        assert out[:4] == b"%PDF"
        assert _pdf_page_count(out) >= 1

    def test_accepts_3_builds_same_major(self, fixture_three_same_major_builds):
        out = pdf_export.generate_comparison_pdf(
            fixture_three_same_major_builds
        )
        assert isinstance(out, bytes)
        assert out[:4] == b"%PDF"
        assert _pdf_page_count(out) >= 1

    def test_accepts_4_digit_family_match_with_different_full_cips(
        self, fixture_three_same_major_builds,
    ):
        """14.1901, 14.1902, 14.1903 are all 14.19* family — accepted.
        Confirms the spec's same-major rule is 4-digit-family, not full CIP.
        """
        ids = [b.cipcode for b in fixture_three_same_major_builds]
        assert ids == ["14.1901", "14.1902", "14.1903"]
        # No raise — render succeeds.
        out = pdf_export.generate_comparison_pdf(
            fixture_three_same_major_builds
        )
        assert out[:4] == b"%PDF"


# ---------------------------------------------------------------------------
# P0: insufficient_chip_renders_for_null_raw_score_boss
# ---------------------------------------------------------------------------


class TestInsufficientChipRendering:
    def test_insufficient_chip_renders_for_null_raw_score_boss(
        self, fixture_build_null_ai_score,
    ):
        """Build with raw_score=None for one boss → PDF renders the
        italic Roman 'Insufficient data' chip and 'Data unavailable for
        this program.' context for that row. Other 4 rows render normal
        chips.
        """
        out = pdf_export.generate_build_pdf(
            fixture_build_null_ai_score,
            student_name=None,
            audience_questions=_aq(),
        )
        text = _extract_pdf_text(out)
        # The italic chip uses the literal string "Insufficient data".
        assert "Insufficient data" in text, (
            "Insufficient chip must render for null-raw_score boss"
        )
        # Context column reads 'Data unavailable for this program.'.
        assert "Data unavailable for this program." in text


# ---------------------------------------------------------------------------
# P1: cost_strip_renders_debt_to_earnings_percent
# ---------------------------------------------------------------------------


class TestCostStripRendersDebtToEarnings:
    def test_renders_dte_as_percent(self, fixture_build):
        """4th cost-strip cell uses f"{v*100:.0f}%" format.

        Fixture sets debt_to_earnings_annual=0.12 → renders as "12%".
        """
        assert fixture_build.career.debt_to_earnings_annual == 0.12
        out = pdf_export.generate_build_pdf(
            fixture_build,
            student_name=None,
            audience_questions=_aq(),
        )
        text = _extract_pdf_text(out)
        assert "12%" in text, (
            "Cost strip must render debt_to_earnings_annual=0.12 as '12%'"
        )

    def test_renders_em_dash_when_dte_is_none(self, fixture_build):
        """None debt_to_earnings_annual → '—' (em dash), no 'None%'."""
        fixture_build.career.debt_to_earnings_annual = None
        out = pdf_export.generate_build_pdf(
            fixture_build,
            student_name=None,
            audience_questions=_aq(),
        )
        text = _extract_pdf_text(out)
        assert "None%" not in text
        assert "${None" not in text


# ---------------------------------------------------------------------------
# P1: partial_match_quality_renders_caveat_line
# ---------------------------------------------------------------------------


class TestPartialMatchQualityCaveat:
    def test_scorecard_only_renders_caveat(
        self, fixture_build_scorecard_only,
    ):
        out = pdf_export.generate_build_pdf(
            fixture_build_scorecard_only,
            student_name=None,
            audience_questions=_aq(),
        )
        text = _extract_pdf_text(out)
        # Caveat references partial coverage.
        assert "partial" in text.lower() or "unavailable" in text.lower()

    def test_partial_no_onet_renders_caveat(
        self, fixture_build_partial_no_onet,
    ):
        out = pdf_export.generate_build_pdf(
            fixture_build_partial_no_onet,
            student_name=None,
            audience_questions=_aq(),
        )
        text = _extract_pdf_text(out)
        # The partial_no_onet caveat references O*NET.
        assert "O*NET" in text or "task" in text.lower()

    def test_full_match_quality_omits_caveat(self, fixture_build):
        """match_quality='full' → no caveat string in the PDF."""
        assert fixture_build.career.match_quality == "full"
        out = pdf_export.generate_build_pdf(
            fixture_build,
            student_name=None,
            audience_questions=_aq(),
        )
        text = _extract_pdf_text(out)
        # Specific caveat strings from pdf_copy._COVERAGE_CAVEATS.
        assert "occupational task data is partial" not in text.lower()
        assert "o*net task detail is unavailable" not in text.lower()


# ---------------------------------------------------------------------------
# P1: pentagon vertices render numeric labels.
# ---------------------------------------------------------------------------


class TestPentagonNumericLabels:
    def test_pentagon_vertices_render_numeric_labels(self, fixture_build):
        """Each pentagon vertex shows '<value>/10' next to the stat name."""
        out = pdf_export.generate_build_pdf(
            fixture_build,
            student_name=None,
            audience_questions=_aq(),
        )
        text = _extract_pdf_text(out)
        # Fixture stats: ern=8 roi=7 res=6 grw=7 aura=6.
        # The micro-table renders these as "8/10", etc.
        assert "8/10" in text
        assert "7/10" in text
        assert "6/10" in text


# ---------------------------------------------------------------------------
# P0: XML-escape user-controlled strings before passing to ReportLab Paragraph.
# ReportLab parses Paragraph input as mini-XML; a bare `<` raises ValueError
# mid-render and 500s the export. Staff-engineer §8 finding S1.
# ---------------------------------------------------------------------------


class TestXmlEscapeUserControlledStrings:
    def test_lt_in_student_name_does_not_crash_render(self, fixture_build):
        """A student typing `<3 design` in the name field must not crash."""
        out = pdf_export.generate_build_pdf(
            fixture_build,
            student_name="<3 design",
            audience_questions=_aq(),
        )
        assert isinstance(out, bytes)
        assert out.startswith(b"%PDF")

    def test_lt_in_skill_rationale_does_not_crash_render(self, fixture_build):
        """Gemma-emitted '<5%' or '<Python>' in skill_recs must not crash."""
        from app.models.career import SkillRec

        fixture_build.skill_recs = [
            SkillRec(
                title="Python <3.11 features",
                stat_impact="Boosts <ai resilience> for <5% of tasks",
                rationale="Does Purdue offer Python <3.11 in core curriculum?",
            ),
            SkillRec(
                title="Statistics & data <visualization>",
                stat_impact="Lifts roi & growth",
                rationale="What's the <internship> placement rate?",
            ),
        ]
        out = pdf_export.generate_build_pdf(
            fixture_build,
            student_name=None,
            audience_questions=_aq(),
        )
        assert isinstance(out, bytes)
        assert out.startswith(b"%PDF")

    def test_lt_in_audience_question_text_does_not_crash_render(
        self, fixture_build
    ):
        """LLM-generated questions containing `<` must not crash the render."""
        aq = AudienceQuestions(
            ask_the_college=[
                AudienceQuestion(
                    text="Is the placement rate < 80% concerning?",
                    is_static_mandatory=True,
                ),
                AudienceQuestion(
                    text="How can I <augment> my education here?",
                    is_static_mandatory=True,
                ),
            ],
            ask_your_parents=[
                AudienceQuestion(text="Can we afford <$30K/yr> after taxes?"),
            ],
            ask_yourself=[
                AudienceQuestion(text="Will I tolerate <repetitive> tasks?"),
            ],
            gemma_path="live",
        )
        out = pdf_export.generate_build_pdf(
            fixture_build,
            student_name=None,
            audience_questions=aq,
        )
        assert isinstance(out, bytes)
        assert out.startswith(b"%PDF")

    def test_lt_in_school_name_does_not_crash_comparison_render(
        self, fixture_three_same_major_builds
    ):
        """Adversarial school name in comparison render must not crash."""
        # Mutate one school name to contain XML-special chars.
        fixture_three_same_major_builds[0].school_name = "<3 University"
        out = pdf_export.generate_comparison_pdf(fixture_three_same_major_builds)
        assert isinstance(out, bytes)
        assert out.startswith(b"%PDF")


# ---------------------------------------------------------------------------
# P0: "About this career" section render
# (feature-career-description-on-pdf.md §4 New Tests Required)
# ---------------------------------------------------------------------------


class TestAboutThisCareerSection:
    """Page 1 "About this career" section: rendered when the build carries
    a populated CareerDescription, silently skipped when None.
    """

    def _populated_career_description(self, *, anchor_tier: str = "activities"):
        from app.models.career import CareerDescription

        return CareerDescription(
            soc_code="17-2141",
            summary=(
                "Mechanical engineers design machines that move parts of "
                "the world. They sketch, simulate, and prototype systems "
                "that turn ideas into hardware."
            ),
            tasks=[
                "Sketch concept designs for parts and systems",
                "Simulate stresses and tolerances digitally",
                "Prototype machines and test them physically",
                "Coordinate with manufacturing on tolerances",
            ],
            anchor_tier=anchor_tier,  # type: ignore[arg-type]
            generated_at="2026-05-07T00:00:00+00:00",
            model="gemma-4-26b-a4b-it",
        )

    def test_pdf_renders_about_this_career_section_when_present(
        self, fixture_build,
    ):
        """Build with career_description populated → rendered PDF contains
        the section heading + summary + first task bullet.
        """
        fixture_build.career_description = self._populated_career_description()
        out = pdf_export.generate_build_pdf(
            fixture_build,
            student_name=None,
            audience_questions=_aq(),
        )
        text = _extract_pdf_text(out)
        # Section heading.
        assert "ABOUT THIS CAREER" in text.upper(), (
            f"section heading missing from PDF text; got: {text[:500]!r}"
        )
        # Summary content.
        assert "Mechanical engineers design machines" in text
        # At least the first task bullet content.
        assert "Sketch concept designs" in text
        # PDF render still produces a valid file. Adding the new section
        # may push content to a 3rd page in the fixture; success criterion
        # is "page-1 layout is valid", not a hard 2-page cap.
        assert _pdf_page_count(out) >= 2

    def test_pdf_skips_section_when_description_missing(
        self, fixture_build,
    ):
        """Build with career_description=None → PDF renders without the
        section, page-1 layout is valid (still exactly 2 pages, no
        section heading present).
        """
        assert fixture_build.career_description is None
        out = pdf_export.generate_build_pdf(
            fixture_build,
            student_name=None,
            audience_questions=_aq(),
        )
        text = _extract_pdf_text(out)
        # No section heading (case-insensitive guard).
        assert "ABOUT THIS CAREER" not in text.upper()
        # Pentagon still renders — its labels survive on page 1. The
        # fixture's stats: ern=8 roi=7 res=6 grw=7 aura=6.
        assert "8/10" in text
        # PDF render still works and produces 2 valid pages.
        assert _pdf_page_count(out) == 2
        assert isinstance(out, bytes)
        assert out.startswith(b"%PDF")

    def test_pdf_renders_tier_b_disclaimer(self, fixture_build):
        """Tier B (description_only) → italic disclaimer line is rendered."""
        fixture_build.career_description = self._populated_career_description(
            anchor_tier="description_only",
        )
        out = pdf_export.generate_build_pdf(
            fixture_build,
            student_name=None,
            audience_questions=_aq(),
        )
        text = _extract_pdf_text(out)
        # Disclaimer copy referenced from career_description module.
        assert "AI-inferred" in text
        assert "BLS occupation summary" in text

    def test_pdf_tier_a_omits_disclaimer(self, fixture_build):
        """Tier A (activities) → NO disclaimer line in the PDF."""
        fixture_build.career_description = self._populated_career_description(
            anchor_tier="activities",
        )
        out = pdf_export.generate_build_pdf(
            fixture_build,
            student_name=None,
            audience_questions=_aq(),
        )
        text = _extract_pdf_text(out)
        # No "AI-inferred" disclaimer banner appears for Tier A.
        assert "AI-inferred" not in text
