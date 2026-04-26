"""Tests for guidance prompt assembly + fallback."""

from __future__ import annotations

from app.models.career import (
    BossFightResult,
    BossScores,
    CareerBranch,
    CareerOutcome,
    GauntletResult,
    PentagonStats,
    SkillRec,
)
from app.services import guidance


def _career() -> CareerOutcome:
    return CareerOutcome(
        unitid=1,
        institution_name="IU-B",
        cipcode="52.14",
        program_name="Marketing",
        soc_code="11-2021",
        occupation_title="Marketing Managers",
        stats=PentagonStats(ern=8, roi=9, res=3, grw=6, hmn=7),
        bosses=BossScores(ai=7, loans=2, market=6, burnout=5, ceiling=8),
        median_annual_wage=157620.0,
        education_level_name="Bachelor's degree",
    )


def _gauntlet() -> GauntletResult:
    return GauntletResult(
        fights=[
            BossFightResult(
                boss="ai",  # type: ignore[arg-type]
                label="Fight AI",
                result="lose",  # type: ignore[arg-type]
                raw_score=10,
                threshold_win=14,
                threshold_draw=10,
                reason="RES 3 + HMN 7 = 10",
            )
        ],
        wins=0,
        losses=1,
        draws=0,
        unknown=0,
        verdict="SOLID BUILD with a single gap.",
    )


class TestGenerateGuidance:
    def test_returns_gemma_output_verbatim(self, monkeypatch):
        from app.services import gemma_client

        stub_text = (
            "IU-B Marketing is strong on ROI but weak on AI resilience."
        )
        monkeypatch.setattr(
            gemma_client, "generate", lambda **kwargs: stub_text
        )
        text = guidance.generate_guidance(_career(), _gauntlet(), [])
        assert "IU-B" in text

    def test_fallback_speaks_in_gemmas_voice(self, monkeypatch):
        """When Gemma is unreachable, the fallback must still hit the
        voice contract: name the school/major/career in plain words,
        point at the weak spot in plain language, and never leak stat
        codes, outcome labels, or game framing.
        """
        from app.services import gemma_client

        monkeypatch.setattr(gemma_client, "generate", lambda **kwargs: "")
        text = guidance.generate_guidance(_career(), _gauntlet(), [])

        # The fallback still grounds the student in their real context.
        assert "Marketing" in text
        assert "IU-B" in text
        # The AI-exposure weak spot is named in plain words, not as
        # "Fight AI" or "LOSE".
        assert "computer" in text.lower()

        # Voice contract — these tokens must never leak into the copy
        # the student actually reads.
        for forbidden in (
            "SOLID BUILD",
            "Fight AI",
            "boss",
            "gauntlet",
            "WIN",
            "LOSE",
            "DRAW",
            "ERN",
            "ROI",
            "RES",
            "GRW",
            "HMN",
            "/10",
        ):
            assert forbidden not in text, (
                f"guidance fallback leaked {forbidden!r}: {text!r}"
            )

    def test_prompt_includes_boss_results(self):
        prompt = guidance._prompt(_career(), _gauntlet(), [])
        assert "Fight AI" in prompt
        assert "LOSE" in prompt
        assert "RES 3" in prompt


class TestChatWithContext:
    def test_system_prompt_carries_build_context(self, monkeypatch):
        from app.services import gemma_client

        captured: dict[str, object] = {}

        def fake_chat(**kwargs):
            captured.update(kwargs)
            return "stub answer"

        monkeypatch.setattr(gemma_client, "generate_chat", fake_chat)
        answer = guidance.chat_with_context(
            career=_career(),
            gauntlet=_gauntlet(),
            branches=[],
            skill_recs=[],
            conversation_history=[],
            user_question="What if I add a CS minor?",
        )

        assert answer == "stub answer"
        system = captured["system"]
        assert isinstance(system, str)
        assert "IU-B" in system
        assert "Marketing" in system
        assert "RES 3" in system
        assert "Fight AI=LOSE" in system

        messages = captured["messages"]
        assert isinstance(messages, list)
        assert messages == [
            {"role": "user", "content": "What if I add a CS minor?"},
        ]

    def test_history_is_prepended_before_new_question(self, monkeypatch):
        from app.services import gemma_client

        captured: dict[str, object] = {}
        monkeypatch.setattr(
            gemma_client,
            "generate_chat",
            lambda **kw: (captured.update(kw), "ok")[1],
        )

        history = [
            {"role": "user", "content": "prior q"},
            {"role": "assistant", "content": "prior a"},
        ]
        guidance.chat_with_context(
            career=_career(),
            gauntlet=_gauntlet(),
            branches=[],
            skill_recs=[],
            conversation_history=history,
            user_question="follow up",
        )

        messages = captured["messages"]
        assert messages == [
            {"role": "user", "content": "prior q"},
            {"role": "assistant", "content": "prior a"},
            {"role": "user", "content": "follow up"},
        ]

    def test_context_block_includes_branches_and_recs(self, monkeypatch):
        from app.services import gemma_client

        captured: dict[str, object] = {}
        monkeypatch.setattr(
            gemma_client,
            "generate_chat",
            lambda **kw: (captured.update(kw), "ok")[1],
        )

        branches = [
            CareerBranch(
                from_soc="11-2021",
                to_soc="11-2022",
                to_title="Sales Managers",
                delta_ern=1,
                unlock="3 years experience",
            )
        ]
        recs = [
            SkillRec(
                title="Python for marketers",
                stat_impact="RES +2",
                rationale="Automate campaign analysis.",
            )
        ]
        guidance.chat_with_context(
            career=_career(),
            gauntlet=_gauntlet(),
            branches=branches,
            skill_recs=recs,
            conversation_history=[],
            user_question="hi",
        )

        system = captured["system"]
        assert "Sales Managers" in system
        assert "Python for marketers" in system

    def test_fallback_when_chat_returns_empty(self, monkeypatch):
        from app.services import gemma_client

        monkeypatch.setattr(gemma_client, "generate_chat", lambda **kw: "")
        answer = guidance.chat_with_context(
            career=_career(),
            gauntlet=_gauntlet(),
            branches=[],
            skill_recs=[],
            conversation_history=[],
            user_question="hi",
        )
        assert "trouble" in answer or "unavailable" in answer


# ---------------------------------------------------------------------------
# Locale threading — Spanish instruction injection
# ---------------------------------------------------------------------------


class TestGuidanceLocale:
    def test_generate_guidance_passes_spanish_instruction(self, monkeypatch):
        """When locale='es', the system prompt sent to Gemma must contain
        the full Spanish instruction block — glossary, prose directive,
        JSON key preservation rules.
        """
        from app.services import gemma_client

        captured: dict[str, object] = {}

        def fake_generate(**kwargs):
            captured.update(kwargs)
            return "stub guidance"

        monkeypatch.setattr(gemma_client, "generate", fake_generate)
        guidance.generate_guidance(
            _career(), _gauntlet(), [], locale="es"
        )

        system = captured["system"]
        assert isinstance(system, str)
        assert "Write all student-facing prose in Spanish" in system
        assert "deuda estudiantil" in system
        assert "JSON keys" in system
        assert "enum values in English" in system

    def test_generate_guidance_english_locale(self, monkeypatch):
        """locale='en' should produce English instruction, not Spanish."""
        from app.services import gemma_client

        captured: dict[str, object] = {}
        monkeypatch.setattr(
            gemma_client,
            "generate",
            lambda **kw: (captured.update(kw), "ok")[1],
        )
        guidance.generate_guidance(
            _career(), _gauntlet(), [], locale="en"
        )

        system = captured["system"]
        assert "Write student-facing prose in English" in system
        assert "Spanish" not in system
        assert "Glossary" not in system

    def test_generate_guidance_async_passes_spanish_instruction(
        self, monkeypatch
    ):
        """Async variant must thread locale the same way."""
        import asyncio

        from app.services import gemma_client

        captured: dict[str, object] = {}

        async def fake_generate_async(**kwargs):
            captured.update(kwargs)
            return "stub async"

        monkeypatch.setattr(
            gemma_client, "generate_async", fake_generate_async
        )
        asyncio.run(
            guidance.generate_guidance_async(
                _career(), _gauntlet(), [], locale="es"
            )
        )

        system = captured["system"]
        assert isinstance(system, str)
        assert "Write all student-facing prose in Spanish" in system
        assert "deuda estudiantil" in system

    def test_chat_with_context_passes_spanish_instruction(self, monkeypatch):
        """chat_with_context must thread locale into the system prompt."""
        from app.services import gemma_client

        captured: dict[str, object] = {}
        monkeypatch.setattr(
            gemma_client,
            "generate_chat",
            lambda **kw: (captured.update(kw), "ok")[1],
        )
        guidance.chat_with_context(
            career=_career(),
            gauntlet=_gauntlet(),
            branches=[],
            skill_recs=[],
            conversation_history=[],
            user_question="hi",
            locale="es",
        )

        system = captured["system"]
        assert "Write all student-facing prose in Spanish" in system
        assert "deuda estudiantil" in system

    def test_chat_with_context_default_locale_is_english(self, monkeypatch):
        """Omitting locale should produce English instruction."""
        from app.services import gemma_client

        captured: dict[str, object] = {}
        monkeypatch.setattr(
            gemma_client,
            "generate_chat",
            lambda **kw: (captured.update(kw), "ok")[1],
        )
        guidance.chat_with_context(
            career=_career(),
            gauntlet=_gauntlet(),
            branches=[],
            skill_recs=[],
            conversation_history=[],
            user_question="hi",
        )

        system = captured["system"]
        assert "Write student-facing prose in English" in system
        assert "Spanish" not in system
