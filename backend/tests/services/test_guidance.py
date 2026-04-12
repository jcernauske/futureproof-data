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

    def test_fallback_includes_verdict(self, monkeypatch):
        from app.services import gemma_client

        monkeypatch.setattr(gemma_client, "generate", lambda **kwargs: "")
        text = guidance.generate_guidance(_career(), _gauntlet(), [])
        assert "SOLID BUILD" in text
        assert "Marketing" in text

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
        assert "IU-B" in answer
        assert "Marketing" in answer
