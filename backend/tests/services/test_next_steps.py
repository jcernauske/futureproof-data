"""Tests for next_steps locale threading.

The core behavior: generate_next_steps reads build.locale when no explicit
locale is passed, and threads the correct language instruction into the
Gemma system prompt.
"""

from __future__ import annotations

from app.models.career import (
    BossFightResult,
    BossScores,
    Build,
    CareerOutcome,
    GauntletResult,
    PentagonStats,
)
from app.services import builds, next_steps


def _career() -> CareerOutcome:
    return CareerOutcome(
        unitid=151351,
        institution_name="Indiana University-Bloomington",
        cipcode="52.14",
        program_name="Marketing",
        soc_code="13-1131",
        occupation_title="Fundraisers",
        stats=PentagonStats(ern=8, roi=9, res=4, grw=6, aura=6),
        bosses=BossScores(ai=7, loans=None, market=7, burnout=6, ceiling=None),
        median_annual_wage=66490.0,
    )


def _gauntlet() -> GauntletResult:
    return GauntletResult(
        fights=[
            BossFightResult(
                boss="ai",  # type: ignore[arg-type]
                label="Fight AI",
                result="lose",  # type: ignore[arg-type]
                raw_score=5,
                threshold_win=14,
                threshold_draw=10,
                reason="test",
            ),
        ],
        wins=0,
        losses=1,
        draws=0,
        unknown=0,
        verdict="TEST",
    )


def _make_build(locale: str = "en") -> Build:
    return builds.build_from_parts(
        school_name="IU-B",
        unitid=151351,
        major_text="Marketing",
        cipcode="52.14",
        program_name="Marketing",
        effort="balanced",
        career=_career(),
        gauntlet=_gauntlet(),
        branches=[],
        skill_recs=[],
        guidance="test",
        locale=locale,
    )


class TestNextStepsLocale:
    def test_uses_build_locale_when_no_explicit_locale(
        self, monkeypatch, isolated_builds_dir
    ):
        """When locale is not passed, generate_next_steps should read
        build.locale and thread it into the Gemma system prompt."""
        from app.services import gemma_client

        captured: dict[str, object] = {}

        def fake_generate(**kwargs):
            captured.update(kwargs)
            return "## Questions to Ask\n1. Stub"

        monkeypatch.setattr(gemma_client, "generate", fake_generate)

        build = _make_build(locale="es")
        next_steps.generate_next_steps(build)

        system = captured["system"]
        assert isinstance(system, str)
        assert "Write all student-facing prose in Spanish" in system
        assert "deuda estudiantil" in system

    def test_explicit_locale_overrides_build_locale(
        self, monkeypatch, isolated_builds_dir
    ):
        """An explicit locale kwarg should override whatever build.locale is."""
        from app.services import gemma_client

        captured: dict[str, object] = {}
        monkeypatch.setattr(
            gemma_client,
            "generate",
            lambda **kw: (captured.update(kw), "stub")[1],
        )

        build = _make_build(locale="es")
        next_steps.generate_next_steps(build, locale="en")

        system = captured["system"]
        assert "Write student-facing prose in English" in system
        assert "Spanish" not in system

    def test_default_build_locale_is_english(
        self, monkeypatch, isolated_builds_dir
    ):
        """A build created without explicit locale defaults to 'en'."""
        from app.services import gemma_client

        captured: dict[str, object] = {}
        monkeypatch.setattr(
            gemma_client,
            "generate",
            lambda **kw: (captured.update(kw), "stub")[1],
        )

        build = _make_build()  # default locale="en"
        assert build.locale == "en"
        next_steps.generate_next_steps(build)

        system = captured["system"]
        assert "Write student-facing prose in English" in system

    def test_inline_markdown_stripped_h2_and_numbered_list_preserved(
        self, monkeypatch, isolated_builds_dir
    ):
        """The frontend NextSteps parser splits on ``## `` headers and
        renders numbered ``1.`` items, so those must survive. Inline
        markdown inside an item (bold/italic) must be stripped before
        the response is returned."""
        from app.services import gemma_client

        markdown_response = (
            "## Questions to Ask Your Counselor\n"
            "1. Ask about **scholarship** programs.\n"
            "2. Ask about *internships* in marketing.\n\n"
            "## Things to Verify\n"
            "1. Verify the program is **accredited**.\n"
        )
        monkeypatch.setattr(
            gemma_client, "generate", lambda **kw: markdown_response
        )
        build = _make_build()
        text = next_steps.generate_next_steps(build)

        # Section headers and numbered items survive.
        assert "## Questions to Ask Your Counselor" in text
        assert "## Things to Verify" in text
        assert "1. Ask about scholarship programs." in text
        assert "2. Ask about internships in marketing." in text
        assert "1. Verify the program is accredited." in text
        # Inline markdown is gone.
        assert "**" not in text
        assert "*internships*" not in text
        assert "*scholarship*" not in text
