"""Tests for the curated skill pool used by the boss-reroll flow."""

from __future__ import annotations

from app.models.career import (
    AppliedSkill,
    BossScores,
    CareerOutcome,
    PentagonStats,
)
from app.services import skill_pool


def _career(
    ern: int | None = 5,
    roi: int | None = 5,
    res: int | None = 5,
    grw: int | None = 5,
    aura: int | None = 5,
    burnout: int | None = 5,
    ceiling: int | None = 5,
) -> CareerOutcome:
    return CareerOutcome(
        unitid=1,
        institution_name="Test U",
        cipcode="52.14",
        program_name="Marketing",
        soc_code="11-2021",
        occupation_title="Marketing Managers",
        stats=PentagonStats(ern=ern, roi=roi, res=res, grw=grw, aura=aura),
        bosses=BossScores(
            ai=5, loans=5, market=5, burnout=burnout, ceiling=ceiling
        ),
    )


class TestFallbackPoolIntegrity:
    """The fallback pool is the safety net when Gemma generation fails.

    If any of these invariants break, a loss-screen reroll could crash
    or offer zero eligible skills — both unacceptable failure modes.
    """

    def test_pool_is_non_empty(self):
        assert len(skill_pool.FALLBACK_POOL) > 0

    def test_ids_are_unique(self):
        ids = [s.id for s in skill_pool.FALLBACK_POOL]
        assert len(ids) == len(set(ids)), "duplicate skill ids in pool"

    def test_every_skill_has_at_least_one_target(self):
        for skill in skill_pool.FALLBACK_POOL:
            assert skill.targets, f"{skill.id} has no targets"

    def test_every_skill_has_at_least_one_nonzero_delta(self):
        # delta_hmn was removed in pentagon-stat-reshape v1.2 (RES absorbed
        # the human-essential signal). delta_aura is intentionally absent
        # from AppliedSkill — AURA is institution-level.
        for skill in skill_pool.FALLBACK_POOL:
            deltas = [
                skill.delta_ern,
                skill.delta_roi,
                skill.delta_res,
                skill.delta_grw,
                skill.delta_burnout_raw,
                skill.delta_ceiling_raw,
            ]
            assert any(deltas), f"{skill.id} has no stat impact"

    def test_every_boss_has_at_least_three_fallback_skills(self):
        """Padding relies on fallback having >= 3 per boss so Gemma's
        under-production can always be topped up."""
        for boss_id in ("ai", "loans", "market", "burnout", "ceiling"):
            results = skill_pool.get_skills_for_boss(boss_id)  # type: ignore[arg-type]
            assert len(results) >= 3, (
                f"fallback pool has only {len(results)} skill(s) for "
                f"boss {boss_id!r}; generate_pool padding needs >= 3"
            )


class TestGetSkillsForBoss:
    def test_returns_only_matching_targets(self):
        skills = skill_pool.get_skills_for_boss("loans")
        assert skills
        for skill in skills:
            assert "loans" in skill.targets

    def test_exclude_ids_filters_out_crafted(self):
        all_loans = skill_pool.get_skills_for_boss("loans")
        assert len(all_loans) >= 2
        first_id = all_loans[0].id
        filtered = skill_pool.get_skills_for_boss(
            "loans", exclude_ids={first_id}
        )
        assert first_id not in {s.id for s in filtered}
        assert len(filtered) == len(all_loans) - 1

    def test_exhaustion_returns_empty_list(self):
        all_ai = skill_pool.get_skills_for_boss("ai")
        crafted = {s.id for s in all_ai}
        result = skill_pool.get_skills_for_boss("ai", exclude_ids=crafted)
        assert result == []


class TestApplySkills:
    def test_empty_skill_list_is_identity(self):
        career = _career()
        result = skill_pool.apply_skills(career, [])
        assert result is career  # no-op short-circuit

    def test_stat_deltas_stack_and_clamp(self):
        # Pentagon-stat-reshape: AURA is institution-level — skills can't
        # shift it (no delta_aura on AppliedSkill). Verify aura passes
        # through unchanged from the original CareerOutcome.
        career = _career(res=3, aura=3)
        skills = [
            AppliedSkill(
                id="a",
                title="A",
                rationale="",
                targets=["ai"],
                delta_res=5,
            ),
            AppliedSkill(
                id="b",
                title="B",
                rationale="",
                targets=["ai"],
                delta_res=5,  # would push to 13 → clamp to 10
            ),
        ]
        new_career = skill_pool.apply_skills(career, skills)
        assert new_career.stats.res == 10  # clamped
        assert new_career.stats.aura == 3  # unchanged — institution-level
        # Original untouched.
        assert career.stats.res == 3
        assert career.stats.aura == 3

    def test_none_stats_stay_none(self):
        career = _career(res=None)
        skills = [
            AppliedSkill(
                id="a",
                title="A",
                rationale="",
                targets=["ai"],
                delta_res=3,
            )
        ]
        new_career = skill_pool.apply_skills(career, skills)
        assert new_career.stats.res is None

    def test_burnout_delta_reduces_raw_score(self):
        career = _career(burnout=7)
        skill = AppliedSkill(
            id="c",
            title="C",
            rationale="",
            targets=["burnout"],
            delta_burnout_raw=-2,
        )
        new_career = skill_pool.apply_skills(career, [skill])
        assert new_career.bosses.burnout == 5

    def test_burnout_delta_clamps_to_floor(self):
        career = _career(burnout=2)
        skill = AppliedSkill(
            id="c",
            title="C",
            rationale="",
            targets=["burnout"],
            delta_burnout_raw=-5,
        )
        new_career = skill_pool.apply_skills(career, [skill])
        assert new_career.bosses.burnout == 1

    def test_ceiling_delta_raises_raw_score(self):
        career = _career(ceiling=5)
        skill = AppliedSkill(
            id="d",
            title="D",
            rationale="",
            targets=["ceiling"],
            delta_ceiling_raw=3,
        )
        new_career = skill_pool.apply_skills(career, [skill])
        assert new_career.bosses.ceiling == 8

    def test_ceiling_delta_clamps_to_ten(self):
        career = _career(ceiling=9)
        skill = AppliedSkill(
            id="d",
            title="D",
            rationale="",
            targets=["ceiling"],
            delta_ceiling_raw=5,
        )
        new_career = skill_pool.apply_skills(career, [skill])
        assert new_career.bosses.ceiling == 10


class TestFormatImpact:
    def test_single_stat(self):
        skill = AppliedSkill(
            id="x",
            title="X",
            rationale="",
            targets=["ai"],
            delta_res=2,
        )
        assert skill_pool.format_impact(skill) == "RES+2"

    def test_multiple_stats(self):
        # delta_hmn / AURA dropped from AppliedSkill in pentagon-stat-reshape.
        # Verify multi-stat delta formatting still emits each non-zero stat.
        skill = AppliedSkill(
            id="x",
            title="X",
            rationale="",
            targets=["ai", "market"],
            delta_res=2,
            delta_grw=1,
            delta_ern=-1,
        )
        impact = skill_pool.format_impact(skill)
        assert "RES+2" in impact
        assert "GRW+1" in impact
        assert "ERN-1" in impact

    def test_burnout_raw_shows_signed(self):
        skill = AppliedSkill(
            id="x",
            title="X",
            rationale="",
            targets=["burnout"],
            delta_burnout_raw=-2,
        )
        assert "burnout-2" in skill_pool.format_impact(skill)

    def test_empty_skill_returns_dash(self):
        skill = AppliedSkill(
            id="x", title="X", rationale="", targets=["ai"]
        )
        assert skill_pool.format_impact(skill) == "—"


# ---------------------------------------------------------------------------
# Personalized pool generation — Gemma + parser + padding
# ---------------------------------------------------------------------------


def _lose_ai_gauntlet():
    from app.models.career import BossFightResult, GauntletResult

    return GauntletResult(
        fights=[
            BossFightResult(
                boss="ai",  # type: ignore[arg-type]
                label="Fight AI",
                result="lose",  # type: ignore[arg-type]
                raw_score=6,
                threshold_win=14,
                threshold_draw=10,
                reason="RES 3 + AURA 3 = 6",
            )
        ],
        wins=0,
        losses=1,
        draws=0,
        unknown=0,
        verdict="TEST",
    )


def _lose_ai_and_loans_gauntlet():
    from app.models.career import BossFightResult, GauntletResult

    return GauntletResult(
        fights=[
            BossFightResult(
                boss="ai",  # type: ignore[arg-type]
                label="Fight AI",
                result="lose",  # type: ignore[arg-type]
                raw_score=6,
                threshold_win=14,
                threshold_draw=10,
                reason="RES 3 + AURA 3 = 6",
            ),
            BossFightResult(
                boss="loans",  # type: ignore[arg-type]
                label="Fight Student Loans",
                result="lose",  # type: ignore[arg-type]
                raw_score=3,
                threshold_win=7,
                threshold_draw=5,
                reason="ROI 3",
            ),
        ],
        wins=0,
        losses=2,
        draws=0,
        unknown=0,
        verdict="TEST",
    )


def _draw_ai_gauntlet():
    from app.models.career import BossFightResult, GauntletResult

    return GauntletResult(
        fights=[
            BossFightResult(
                boss="ai",  # type: ignore[arg-type]
                label="Fight AI",
                result="draw",  # type: ignore[arg-type]
                raw_score=10,
                threshold_win=14,
                threshold_draw=10,
                reason="RES 5 + AURA 5 = 10",
            )
        ],
        wins=0,
        losses=0,
        draws=1,
        unknown=0,
        verdict="TEST",
    )


def _mixed_loss_draw_win_gauntlet():
    from app.models.career import BossFightResult, GauntletResult

    return GauntletResult(
        fights=[
            BossFightResult(
                boss="ai",  # type: ignore[arg-type]
                label="Fight AI",
                result="draw",  # type: ignore[arg-type]
                raw_score=10,
                threshold_win=14,
                threshold_draw=10,
                reason="RES 5 + AURA 5 = 10",
            ),
            BossFightResult(
                boss="loans",  # type: ignore[arg-type]
                label="Fight Student Loans",
                result="lose",  # type: ignore[arg-type]
                raw_score=3,
                threshold_win=7,
                threshold_draw=5,
                reason="ROI 3",
            ),
            BossFightResult(
                boss="market",  # type: ignore[arg-type]
                label="Fight the Market",
                result="win",  # type: ignore[arg-type]
                raw_score=8,
                threshold_win=6,
                threshold_draw=4,
                reason="GRW 8",
            ),
        ],
        wins=1,
        losses=1,
        draws=1,
        unknown=0,
        verdict="TEST",
    )


def _win_everything_gauntlet():
    from app.models.career import GauntletResult

    return GauntletResult(
        fights=[], wins=5, losses=0, draws=0, unknown=0, verdict="WIN"
    )


class TestParsePool:
    def test_parses_valid_line(self):
        # Pentagon-stat-reshape: legacy HMN tokens fold into RES on parse
        # (RES absorbs the human-essential signal). RES+2,HMN+1 → delta_res=3.
        text = (
            "ai|Kelley Business Analytics minor|RES+2,HMN+1|"
            "The Kelley analytics minor teaches marketers to direct AI tools."
        )
        skills = skill_pool._parse_pool(text, ["ai"])
        assert len(skills) == 1
        skill = skills[0]
        assert skill.title == "Kelley Business Analytics minor"
        assert skill.delta_res == 3  # 2 (raw RES) + 1 (folded HMN)
        assert skill.targets == ["ai"]
        assert "Kelley" in skill.rationale

    def test_parses_multiple_lines(self):
        text = (
            "ai|Revit BIM coursework|RES+2|Architecture students who direct BIM.\n"
            "ai|Portfolio-building studio|HMN+2,RES+1|Builds judgment AI can't.\n"
            "loans|In-state residency lock|ROI+2|Cut sticker price.\n"
        )
        skills = skill_pool._parse_pool(text, ["ai", "loans"])
        assert len(skills) == 3
        ai_skills = [s for s in skills if "ai" in s.targets]
        loans_skills = [s for s in skills if "loans" in s.targets]
        assert len(ai_skills) == 2
        assert len(loans_skills) == 1

    def test_ignores_malformed_lines(self):
        text = (
            "not a valid line\n"
            "ai|Good skill|RES+2|Real rationale.\n"
            "ai||RES+2|missing title\n"
            "ai|Missing deltas||no deltas at all\n"
            "ai|No rationale|RES+2|\n"
        )
        skills = skill_pool._parse_pool(text, ["ai"])
        titles = [s.title for s in skills]
        assert "Good skill" in titles
        assert "" not in titles

    def test_drops_skills_for_non_losing_bosses(self):
        """If Gemma hallucinates a skill for a boss the student won,
        it must be dropped — the pool is losing-only by design."""
        text = (
            "ai|Targeted AI skill|RES+2|Hits a losing fight.\n"
            "market|Wrong target|GRW+2|Student didn't lose this one.\n"
        )
        skills = skill_pool._parse_pool(text, ["ai"])
        assert len(skills) == 1
        assert skills[0].title == "Targeted AI skill"

    def test_parses_burnout_raw(self):
        text = "burnout|Campus counseling|burnout-2|Free support on campus."
        skills = skill_pool._parse_pool(text, ["burnout"])
        assert len(skills) == 1
        assert skills[0].delta_burnout_raw == -2

    def test_parses_ceiling_raw(self):
        text = "ceiling|Grad school track|ceiling+2|Raises long-term earnings."
        skills = skill_pool._parse_pool(text, ["ceiling"])
        assert len(skills) == 1
        assert skills[0].delta_ceiling_raw == 2

    def test_dedupes_by_derived_id(self):
        text = (
            "ai|Repeat Skill|RES+1|First rationale.\n"
            "ai|Repeat Skill|RES+2|Different rationale same title.\n"
        )
        skills = skill_pool._parse_pool(text, ["ai"])
        assert len(skills) == 1

    def test_boss_tag_is_case_insensitive(self):
        text = "AI|Mixed case boss|RES+1|rationale."
        skills = skill_pool._parse_pool(text, ["ai"])
        assert len(skills) == 1


class TestGeneratePool:
    def test_no_losses_returns_empty_without_calling_gemma(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            skill_pool.gemma_client,
            "generate",
            lambda **kw: (calls.append(kw), "")[1],
        )
        result = skill_pool.generate_pool(_career(), _win_everything_gauntlet())
        assert result == []
        assert calls == []  # never called

    def test_uses_gemma_output_when_parseable(self, monkeypatch):
        fake = (
            "ai|Kelley Business Analytics minor|RES+2,HMN+1|"
            "Direct AI tools at Kelley.\n"
            "ai|Media School studio|HMN+2|Uniquely human work.\n"
            "ai|AI ethics elective|RES+1,HMN+1|Positions you as AI judge.\n"
        )
        monkeypatch.setattr(
            skill_pool.gemma_client, "generate", lambda **kw: fake
        )
        pool = skill_pool.generate_pool(_career(), _lose_ai_gauntlet())
        ai_skills = [s for s in pool if "ai" in s.targets]
        assert len(ai_skills) >= 3
        # Personalized (Gemma) skills come first, before fallback.
        assert ai_skills[0].title == "Kelley Business Analytics minor"

    def test_pads_under_production_from_fallback(self, monkeypatch):
        # Gemma returns only ONE ai-skill. generate_pool should pad to >= 3.
        monkeypatch.setattr(
            skill_pool.gemma_client,
            "generate",
            lambda **kw: "ai|Only one skill|RES+2|Rationale.\n",
        )
        pool = skill_pool.generate_pool(_career(), _lose_ai_gauntlet())
        ai_skills = [s for s in pool if "ai" in s.targets]
        assert len(ai_skills) >= 3
        assert ai_skills[0].title == "Only one skill"  # Gemma first
        # Remaining came from the fallback
        fallback_ids = {s.id for s in skill_pool.FALLBACK_POOL}
        assert any(s.id in fallback_ids for s in ai_skills[1:])

    def test_empty_gemma_output_falls_back_entirely(self, monkeypatch):
        monkeypatch.setattr(
            skill_pool.gemma_client, "generate", lambda **kw: ""
        )
        pool = skill_pool.generate_pool(_career(), _lose_ai_gauntlet())
        ai_skills = [s for s in pool if "ai" in s.targets]
        assert len(ai_skills) >= 3
        fallback_ids = {s.id for s in skill_pool.FALLBACK_POOL}
        assert all(s.id in fallback_ids for s in ai_skills)

    def test_multi_boss_losses_pad_independently(self, monkeypatch):
        # Gemma returns 4 ai-skills and 0 loans-skills.
        fake = (
            "ai|AI Skill A|RES+1|a\n"
            "ai|AI Skill B|RES+1|b\n"
            "ai|AI Skill C|HMN+1|c\n"
            "ai|AI Skill D|HMN+1|d\n"
        )
        monkeypatch.setattr(
            skill_pool.gemma_client, "generate", lambda **kw: fake
        )
        pool = skill_pool.generate_pool(
            _career(), _lose_ai_and_loans_gauntlet()
        )
        ai_count = sum(1 for s in pool if "ai" in s.targets)
        loans_count = sum(1 for s in pool if "loans" in s.targets)
        assert ai_count == 4  # Gemma covered AI, no padding needed
        assert loans_count >= 3  # Fully padded from fallback

    def test_prompt_lists_non_win_bosses_only(self, monkeypatch):
        """Prompt must list LOSE and DRAW bosses — not WINs."""
        captured: dict = {}

        def capture(**kw):
            captured.update(kw)
            return ""

        monkeypatch.setattr(skill_pool.gemma_client, "generate", capture)
        skill_pool.generate_pool(
            _career(), _mixed_loss_draw_win_gauntlet()
        )
        user_prompt = captured["user"]
        assert "Fight AI" in user_prompt
        assert "DRAW" in user_prompt
        assert "Fight Student Loans" in user_prompt
        assert "LOSE" in user_prompt
        # Won boss should NOT appear.
        assert "Fight the Market" not in user_prompt

    def test_draw_only_gauntlet_generates_pool(self, monkeypatch):
        """A gauntlet with draws but no losses must still generate a pool."""
        fake = (
            "ai|AI Literacy Course|RES+1|AI exposure for theatre.\n"
            "ai|Portfolio Project|HMN+2|Builds human-work evidence.\n"
            "ai|Public Speaking|HMN+1,RES+1|Rehearsal for real jobs.\n"
        )
        monkeypatch.setattr(
            skill_pool.gemma_client, "generate", lambda **kw: fake
        )
        pool = skill_pool.generate_pool(_career(), _draw_ai_gauntlet())
        ai_skills = [s for s in pool if "ai" in s.targets]
        assert len(ai_skills) >= 3

    def test_mixed_loss_draw_generates_skills_for_both(self, monkeypatch):
        """Both the LOSE (loans) and DRAW (ai) bosses get skills."""
        fake = (
            "ai|AI Skill|RES+2|a\n"
            "ai|AI Skill 2|HMN+1|b\n"
            "ai|AI Skill 3|RES+1|c\n"
            "loans|Loan Skill|ROI+2|d\n"
            "loans|Loan Skill 2|ROI+1|e\n"
            "loans|Loan Skill 3|ROI+1|f\n"
        )
        monkeypatch.setattr(
            skill_pool.gemma_client, "generate", lambda **kw: fake
        )
        pool = skill_pool.generate_pool(
            _career(), _mixed_loss_draw_win_gauntlet()
        )
        ai_count = sum(1 for s in pool if "ai" in s.targets)
        loans_count = sum(1 for s in pool if "loans" in s.targets)
        assert ai_count >= 3
        assert loans_count >= 3
        # Won boss (market) should have zero skills.
        market_count = sum(1 for s in pool if "market" in s.targets)
        assert market_count == 0


class TestGetSkillsForBossWithExplicitPool:
    def test_custom_pool_overrides_fallback(self):
        custom = [
            AppliedSkill(
                id="custom_1",
                title="Custom skill",
                rationale="r",
                targets=["ai"],
                delta_res=2,
            )
        ]
        results = skill_pool.get_skills_for_boss("ai", custom)
        assert len(results) == 1
        assert results[0].id == "custom_1"

    def test_none_pool_uses_fallback(self):
        results = skill_pool.get_skills_for_boss("ai", None)
        assert results  # non-empty
        fallback_ids = {s.id for s in skill_pool.FALLBACK_POOL}
        assert all(s.id in fallback_ids for s in results)

    def test_exclude_ids_with_custom_pool(self):
        custom = [
            AppliedSkill(
                id="a", title="A", rationale="r", targets=["ai"], delta_res=1
            ),
            AppliedSkill(
                id="b", title="B", rationale="r", targets=["ai"], delta_res=1
            ),
        ]
        results = skill_pool.get_skills_for_boss(
            "ai", custom, exclude_ids={"a"}
        )
        assert len(results) == 1
        assert results[0].id == "b"
