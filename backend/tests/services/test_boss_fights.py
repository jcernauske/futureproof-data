"""Tests for the boss fight gauntlet — threshold logic + verdict composition."""

from __future__ import annotations

from app.models.career import BossScores, CareerOutcome, PentagonStats
from app.services import boss_fights


def _career(
    *,
    ern=None,
    roi=None,
    res=None,
    grw=None,
    hmn=None,
    burnout=None,
    ceiling=None,
    net_price_annual=None,
    cost_of_attendance_annual=None,
    modeled_total_debt=None,
    debt_median_reference=None,
    debt_median=None,
    earnings_1yr_median=None,
    institution_control=None,
    roi_cost_basis=None,
    financed_dte=None,
    tuition_in_state=None,
    tuition_out_of_state=None,
    loan_pct=1.0,
) -> CareerOutcome:
    return CareerOutcome(
        unitid=1,
        institution_name="Test School",
        cipcode="00.00",
        program_name="Test",
        soc_code="11-1021",
        occupation_title="Test Career",
        net_price_annual=net_price_annual,
        cost_of_attendance_annual=cost_of_attendance_annual,
        modeled_total_debt=modeled_total_debt,
        debt_median_reference=debt_median_reference,
        debt_median=debt_median,
        earnings_1yr_median=earnings_1yr_median,
        institution_control=institution_control,
        roi_cost_basis=roi_cost_basis,
        financed_dte=financed_dte,
        tuition_in_state=tuition_in_state,
        tuition_out_of_state=tuition_out_of_state,
        loan_pct=loan_pct,
        stats=PentagonStats(ern=ern, roi=roi, res=res, grw=grw, hmn=hmn),
        bosses=BossScores(
            ai=None, loans=None, market=None, burnout=burnout, ceiling=ceiling
        ),
    )


class TestFightAI:
    def test_win_when_res_plus_hmn_high(self):
        career = _career(res=8, hmn=8)
        fight = _run_one(career, "ai")
        assert fight.result == "win"
        assert fight.raw_score == 16

    def test_draw_in_middle_band(self):
        career = _career(res=5, hmn=5)
        fight = _run_one(career, "ai")
        assert fight.result == "draw"

    def test_lose_when_low(self):
        career = _career(res=2, hmn=3)
        fight = _run_one(career, "ai")
        assert fight.result == "lose"

    def test_unknown_when_stats_missing(self):
        career = _career(res=None, hmn=None)
        fight = _run_one(career, "ai")
        assert fight.result == "unknown"
        assert fight.raw_score is None


class TestFightLoans:
    def test_win_above_threshold(self):
        fight = _run_one(_career(roi=8), "loans")
        assert fight.result == "win"

    def test_draw_at_5(self):
        fight = _run_one(_career(roi=5), "loans")
        assert fight.result == "draw"

    def test_lose_below_5(self):
        fight = _run_one(_career(roi=3), "loans")
        assert fight.result == "lose"


class TestFightMarket:
    def test_win_at_grw_6(self):
        fight = _run_one(_career(grw=6), "market")
        assert fight.result == "win"

    def test_draw_at_grw_4(self):
        fight = _run_one(_career(grw=4), "market")
        assert fight.result == "draw"


class TestFightBurnout:
    def test_low_burnout_risk_wins(self):
        fight = _run_one(_career(burnout=3), "burnout")
        # readiness = 11 - 3 = 8 → win
        assert fight.result == "win"
        assert fight.raw_score == 8

    def test_high_burnout_risk_loses(self):
        fight = _run_one(_career(burnout=9), "burnout")
        # readiness = 2 → lose
        assert fight.result == "lose"

    def test_middling_draw(self):
        fight = _run_one(_career(burnout=6), "burnout")
        # readiness = 5 → draw
        assert fight.result == "draw"


class TestFightCeiling:
    def test_uses_boss_score_when_present(self):
        fight = _run_one(_career(ceiling=8, ern=3), "ceiling")
        assert fight.result == "win"
        assert fight.raw_score == 8

    def test_falls_back_to_ern(self):
        fight = _run_one(_career(ceiling=None, ern=8), "ceiling")
        assert fight.result == "win"
        assert fight.raw_score == 8
        assert "fallback" in fight.reason

    def test_unknown_when_both_missing(self):
        fight = _run_one(_career(ceiling=None, ern=None), "ceiling")
        assert fight.result == "unknown"


class TestGauntletVerdict:
    def test_dominant_when_no_losses_and_three_wins(self, monkeypatch):
        _disable_narrative(monkeypatch)
        gauntlet = boss_fights.run_gauntlet(
            _career(res=8, hmn=8, roi=9, grw=7, burnout=3, ceiling=8),
            with_narratives=False,
        )
        assert gauntlet.losses == 0
        assert gauntlet.wins >= 3
        assert "DOMINANT" in gauntlet.verdict

    def test_vulnerable_when_losses_outweigh_wins(self, monkeypatch):
        _disable_narrative(monkeypatch)
        gauntlet = boss_fights.run_gauntlet(
            _career(res=2, hmn=2, roi=3, grw=2, burnout=9, ceiling=2),
            with_narratives=False,
        )
        assert gauntlet.losses > gauntlet.wins
        assert "VULNERABLE" in gauntlet.verdict

    def test_insufficient_when_all_unknown(self, monkeypatch):
        _disable_narrative(monkeypatch)
        gauntlet = boss_fights.run_gauntlet(_career(), with_narratives=False)
        assert gauntlet.unknown == 5
        assert "Insufficient" in gauntlet.verdict

    def test_mixed_when_wins_equal_losses(self, monkeypatch):
        _disable_narrative(monkeypatch)
        # 2 wins + 2 losses + 1 draw
        gauntlet = boss_fights.run_gauntlet(
            _career(res=8, hmn=8, roi=2, grw=2, burnout=3, ceiling=5),
            with_narratives=False,
        )
        # ai=16 win, loans=2 lose, market=2 lose, burnout=8 win, ceiling=5 draw
        assert gauntlet.wins == gauntlet.losses
        assert "MIXED" in gauntlet.verdict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _disable_narrative(monkeypatch):
    from app.services import gemma_client

    monkeypatch.setattr(gemma_client, "generate", lambda **kwargs: "")


def _run_one(career: CareerOutcome, boss_id: str):
    """Run the full gauntlet with narratives off and pluck one fight."""
    gauntlet = boss_fights.run_gauntlet(career, with_narratives=False)
    return next(f for f in gauntlet.fights if f.boss == boss_id)


class TestScoreAndNarrateSplit:
    """The /build async path splits run_gauntlet into a pure scorer
    (``score_gauntlet``) + a per-fight async narrator (``narrate_one``)
    so the narrative calls can fan out alongside recs/pool/guidance.

    These tests lock the split in: pure scoring is deterministic and
    leaves narratives empty, ``narrate_one`` hits Gemma once per fight,
    and the sync ``run_gauntlet`` facade still populates narratives for
    the CLI / scripts.
    """

    def test_score_gauntlet_produces_empty_narratives(self):
        career = _career(res=8, hmn=8, roi=7, grw=6, burnout=3, ceiling=7, ern=6)
        gauntlet = boss_fights.score_gauntlet(career)
        # Every fight got scored — no unknowns with full stats.
        assert len(gauntlet.fights) == 5
        assert all(f.narrative == "" for f in gauntlet.fights), (
            "score_gauntlet must leave every narrative empty — the async "
            "router owns the Gemma call via narrate_one"
        )
        # Verdict totals still compose normally.
        assert (
            gauntlet.wins + gauntlet.losses + gauntlet.draws + gauntlet.unknown
            == 5
        )

    def test_score_gauntlet_never_calls_gemma(self, monkeypatch):
        """If score_gauntlet ever reaches into gemma_client, the router's
        parallel fan-out model breaks — assert the boundary."""
        from app.services import gemma_client

        called = {"n": 0}

        def _explode(**kwargs):
            called["n"] += 1
            raise AssertionError("score_gauntlet must not call gemma.generate")

        async def _explode_async(**kwargs):
            called["n"] += 1
            raise AssertionError("score_gauntlet must not call gemma.generate_async")

        monkeypatch.setattr(gemma_client, "generate", _explode)
        monkeypatch.setattr(gemma_client, "generate_async", _explode_async)

        boss_fights.score_gauntlet(
            _career(res=8, hmn=8, roi=7, grw=6, burnout=3, ceiling=7)
        )
        assert called["n"] == 0

    def test_run_gauntlet_still_populates_narratives(self, monkeypatch):
        """The sync facade (still used by the CLI) must keep populating
        narratives so nothing downstream sees empty strings."""
        from app.services import gemma_client

        captured: list[dict] = []

        def fake_generate(**kwargs):
            captured.append(kwargs)
            return "Sync coach note."

        monkeypatch.setattr(gemma_client, "generate", fake_generate)

        gauntlet = boss_fights.run_gauntlet(
            _career(res=8, hmn=8, roi=7, grw=6, burnout=3, ceiling=7, ern=6),
            with_narratives=True,
        )
        # One generate call per fight.
        assert len(captured) == len(gauntlet.fights)
        # Every fight carries the narrative Gemma returned (falls back if
        # blank, but here we returned a real string for all).
        assert all(f.narrative == "Sync coach note." for f in gauntlet.fights)

    def test_run_gauntlet_skips_gemma_for_unknown_fights(self, monkeypatch):
        """Same UNKNOWN short-circuit as narrate_one, on the sync path.

        Mirrors the async guard: when a fight's result is ``unknown``
        the prompt has no register to narrate against, so we must use
        the deterministic fallback and NEVER spend a Gemma call on it.
        """
        from app.services import gemma_client

        captured: list[dict] = []

        def fake_generate(**kwargs):
            captured.append(kwargs)
            return "Sync coach note."

        monkeypatch.setattr(gemma_client, "generate", fake_generate)

        # ern missing → ceiling fight is UNKNOWN; other stats present
        # so their fights classify normally.
        gauntlet = boss_fights.run_gauntlet(
            _career(res=8, hmn=8, roi=7, grw=6, burnout=3, ceiling=None, ern=None),
            with_narratives=True,
        )

        ceiling = next(f for f in gauntlet.fights if f.boss == "ceiling")
        assert ceiling.result == "unknown"
        assert ceiling.narrative == boss_fights._fallback_narrative(ceiling)

        # One Gemma call per non-unknown fight, none for the ceiling.
        scored = [f for f in gauntlet.fights if f.result != "unknown"]
        assert len(captured) == len(scored)
        assert all(f.narrative == "Sync coach note." for f in scored)


class TestNarrateOne:
    """Async ``narrate_one`` returns a coach string, falls back cleanly
    when Gemma throws or returns empty, and never raises."""

    def test_narrate_one_returns_gemma_text(self, monkeypatch):
        from app.models.career import BossFightResult
        from app.services import gemma_client

        async def fake_async(**kwargs):
            return "  coach narrative for the ai boss  "

        monkeypatch.setattr(gemma_client, "generate_async", fake_async)

        fight = BossFightResult(
            boss="ai",  # type: ignore[arg-type]
            label="Fight AI",
            result="win",  # type: ignore[arg-type]
            raw_score=16,
            threshold_win=14,
            threshold_draw=10,
            reason="RES 8 + HMN 8 = 16",
        )
        import asyncio

        text = asyncio.run(
            boss_fights.narrate_one(_career(res=8, hmn=8), fight)
        )
        # narrate_one returns whatever Gemma returned; leading/trailing
        # whitespace is intentionally preserved (stripping is the sync
        # generate's job, and the mock bypasses that).
        assert "coach narrative" in text

    def test_narrate_one_falls_back_on_empty(self, monkeypatch):
        """When Gemma returns empty for a scored fight, the degraded
        fallback kicks in. Voice contract: no stat codes, no outcome
        labels (WIN/LOSE/DRAW), no game framing (fight/boss/gauntlet),
        no internal boss label — the student gets a short, honest,
        tone-matched placeholder.
        """
        from app.models.career import BossFightResult
        from app.services import gemma_client

        async def fake_async(**kwargs):
            return ""

        monkeypatch.setattr(gemma_client, "generate_async", fake_async)

        fight = BossFightResult(
            boss="loans",  # type: ignore[arg-type]
            label="Fight Student Loans",
            result="lose",  # type: ignore[arg-type]
            raw_score=3,
            threshold_win=7,
            threshold_draw=5,
            reason="ROI 3",
        )
        import asyncio

        text = asyncio.run(
            boss_fights.narrate_one(_career(roi=3), fight)
        )
        assert text  # non-empty
        # Voice contract — these strings MUST NOT appear in the
        # fallback the student actually sees.
        forbidden = [
            "Fight Student Loans",
            "LOSE",
            "WIN",
            "DRAW",
            "boss",
            "gauntlet",
            "battle",
            "ROI",
            "ERN",
        ]
        for word in forbidden:
            assert word not in text, (
                f"degraded fallback leaked forbidden token {word!r}: {text!r}"
            )

    def test_unknown_ceiling_fallback_has_correct_voice(self):
        """Reproduces the Illinois State Special Ed screenshot bug.

        When the Ceiling has no data, the student must see an honest
        'not enough data' line — in Gemma's voice, never a prompt-echo
        and never a stat/game/outcome leak.
        """
        from app.models.career import BossFightResult

        fight = BossFightResult(
            boss="ceiling",  # type: ignore[arg-type]
            label="Fight the Ceiling",
            result="unknown",  # type: ignore[arg-type]
            raw_score=None,
            threshold_win=7,
            threshold_draw=5,
            reason="ceiling score unavailable",
        )
        text = boss_fights._fallback_narrative(fight)

        # The line must communicate the no-data state in plain words.
        assert "enough" in text.lower() or "not enough" in text.lower()

        # Voice contract — never leak these.
        forbidden = [
            "Fight the Ceiling",
            "boss",
            "gauntlet",
            "battle",
            "WIN",
            "LOSE",
            "DRAW",
            "ERN",
            "ROI",
            "RES",
            "GRW",
            "HMN",
            "flagged for review",
            "/10",
        ]
        for word in forbidden:
            assert word not in text, (
                f"unknown-ceiling fallback leaked forbidden token "
                f"{word!r}: {text!r}"
            )

    def test_narrate_one_skips_gemma_when_result_unknown(self, monkeypatch):
        """No-data bosses must NOT hit Gemma.

        Gemma's narrative prompt only defines WIN / DRAW / LOSE
        registers, so asking it to narrate an UNKNOWN result gets us a
        prompt echo ("Please provide the WIN, DRAW, or LOSE result...")
        which leaks straight into the UI. Short-circuit to the
        deterministic no-data fallback instead.
        """
        from app.models.career import BossFightResult
        from app.services import gemma_client

        async def boom(**kwargs):
            raise AssertionError(
                "narrate_one must not call Gemma for unknown results"
            )

        monkeypatch.setattr(gemma_client, "generate_async", boom)

        fight = BossFightResult(
            boss="ceiling",  # type: ignore[arg-type]
            label="Fight the Ceiling",
            result="unknown",  # type: ignore[arg-type]
            raw_score=None,
            threshold_win=7,
            threshold_draw=5,
            reason="ceiling score unavailable",
        )
        import asyncio

        text = asyncio.run(
            boss_fights.narrate_one(_career(ceiling=None, ern=None), fight)
        )
        assert text == boss_fights._fallback_narrative(fight)

    def test_narrate_one_propagates_unexpected_exception(self, monkeypatch):
        """Unexpected bugs must bubble up — the router's
        ``return_exceptions=True`` is the single fallback gate. If this
        layer silently swallowed them, an attribute error on a
        malformed CareerOutcome would masquerade as a normal Gemma
        outage and we'd never see the real signal.
        """
        from app.models.career import BossFightResult
        from app.services import gemma_client

        async def boom(**kwargs):
            raise RuntimeError("OpenRouter 503")

        monkeypatch.setattr(gemma_client, "generate_async", boom)

        fight = BossFightResult(
            boss="ai",  # type: ignore[arg-type]
            label="Fight AI",
            result="draw",  # type: ignore[arg-type]
            raw_score=12,
            threshold_win=14,
            threshold_draw=10,
            reason="RES 6 + HMN 6",
        )
        import asyncio

        import pytest

        with pytest.raises(RuntimeError, match="OpenRouter 503"):
            asyncio.run(
                boss_fights.narrate_one(_career(res=6, hmn=6), fight)
            )


class TestRerollCommentary:
    def test_generates_commentary_on_flip(self, monkeypatch):
        from app.models.career import BossFightResult
        from app.services import gemma_client

        captured: dict = {}

        def fake_generate(**kwargs):
            captured.update(kwargs)
            return "Equipping the analytics minor moved your RES from 3 to 5."

        monkeypatch.setattr(gemma_client, "generate", fake_generate)

        fight = BossFightResult(
            boss="ai",  # type: ignore[arg-type]
            label="Fight AI",
            result="win",  # type: ignore[arg-type]
            raw_score=14,
            threshold_win=14,
            threshold_draw=10,
            reason="RES 5 + HMN 9 = 14",
        )
        text = boss_fights.generate_reroll_commentary(
            career=_career(res=5, hmn=9),
            fight=fight,
            original_result="lose",
            original_narrative="The original coach note.",
            crafted_skill_titles=["Data Analytics Minor", "Design Thinking"],
        )
        assert "analytics minor" in text.lower()
        assert "LOSE" in captured["user"]
        assert "WIN" in captured["user"]
        assert "Data Analytics Minor" in captured["user"]
        assert "Design Thinking" in captured["user"]

    def test_returns_empty_on_gemma_failure(self, monkeypatch):
        from app.models.career import BossFightResult
        from app.services import gemma_client

        monkeypatch.setattr(gemma_client, "generate", lambda **kw: "")
        fight = BossFightResult(
            boss="ai",  # type: ignore[arg-type]
            label="Fight AI",
            result="win",  # type: ignore[arg-type]
            raw_score=14,
            threshold_win=14,
            threshold_draw=10,
            reason="test",
        )
        text = boss_fights.generate_reroll_commentary(
            career=_career(res=8, hmn=8),
            fight=fight,
            original_result="lose",
            original_narrative="",
            crafted_skill_titles=["Some Skill"],
        )
        assert text == ""

    def test_returns_empty_on_exception(self, monkeypatch):
        from app.models.career import BossFightResult
        from app.services import gemma_client

        def boom(**kwargs):
            raise RuntimeError("connection failed")

        monkeypatch.setattr(gemma_client, "generate", boom)
        fight = BossFightResult(
            boss="ai",  # type: ignore[arg-type]
            label="Fight AI",
            result="draw",  # type: ignore[arg-type]
            raw_score=12,
            threshold_win=14,
            threshold_draw=10,
            reason="test",
        )
        text = boss_fights.generate_reroll_commentary(
            career=_career(res=6, hmn=6),
            fight=fight,
            original_result="lose",
            original_narrative="",
            crafted_skill_titles=["Some Skill"],
        )
        assert text == ""


class TestFightLoansWithCostOfAttendance:
    """Fight Student Loans must score across both ROI input paths.

    Spec: docs/specs/roi-formula-cost-of-attendance.md §F (P0). The
    fight's score-of function reads ``career.stats.roi`` directly, so it
    is agnostic to whether ROI was derived from net_price_annual or
    debt_median — but we exercise both paths end-to-end to guarantee the
    fight still resolves win/draw/lose under either input.
    """

    def test_loans_fight_with_cost_of_attendance_inputs(self):
        """Net-price path produced ROI = 8 → loans fight WIN."""
        career = _career(
            roi=8,
            net_price_annual=14_200.0,
            modeled_total_debt=14_200.0 * 4.0,
            debt_median_reference=19_500.0,
            debt_median=19_500.0,
            earnings_1yr_median=63_371.0,
        )
        fight = _run_one(career, "loans")
        assert fight.result == "win"
        assert fight.raw_score == 8

    def test_loans_fight_fallback_path_still_scores(self):
        """Legacy ROI input (no cost fields set) — fight still resolves."""
        career = _career(roi=4)
        fight = _run_one(career, "loans")
        assert fight.result == "lose"
        assert fight.raw_score == 4

    def test_loans_fight_unknown_when_roi_missing(self):
        career = _career(
            roi=None,
            net_price_annual=14_200.0,
            modeled_total_debt=56_800.0,
        )
        fight = _run_one(career, "loans")
        assert fight.result == "unknown"


class TestNarrativePromptIncludesCostContext:
    """The Fight Student Loans narrative prompt must include cost context.

    Spec: docs/specs/roi-formula-cost-of-attendance.md §4 / §F (P1).
    When net_price_annual is available the prompt should carry the
    school net price, modeled 4-year debt, and the median-debt reference
    so Gemma can name the gap between modeled and median.
    """

    def test_prompt_carries_net_price_and_modeled_debt(self):
        from app.models.career import BossFightResult
        from app.services import boss_fights as bf

        career = _career(
            roi=4,
            net_price_annual=14_200.0,
            cost_of_attendance_annual=22_800.0,
            tuition_in_state=18_000.0,
            modeled_total_debt=14_200.0 * 4.0 * 0.75,
            debt_median_reference=19_500.0,
            debt_median=19_500.0,
            earnings_1yr_median=63_371.0,
            institution_control="Public",
            loan_pct=0.75,
        )
        fight = BossFightResult(
            boss="loans",  # type: ignore[arg-type]
            label="Fight Student Loans",
            result="lose",  # type: ignore[arg-type]
            raw_score=4,
            threshold_win=7,
            threshold_draw=5,
            reason="ROI 4",
        )
        prompt = bf._narrative_prompt(career, fight)
        assert "$72,000" in prompt  # sticker tuition 18000*4
        assert "75%" in prompt  # loan coverage
        assert "$54,000" in prompt  # sticker debt 72000*0.75
        assert "$56,800" in prompt  # net price avg 14200*4
        assert "average" in prompt.lower()  # net price labeled as average
        # modeled_total_debt suppressed when sticker available
        assert "$42,600" not in prompt
        assert "$19,500" in prompt  # debt_median_reference
        assert "Fight Student Loans" in prompt
        assert "LOSE" in prompt

    def test_prompt_falls_back_when_no_net_price(self):
        from app.models.career import BossFightResult
        from app.services import boss_fights as bf

        career = _career(
            roi=4,
            debt_median=19_500.0,
            earnings_1yr_median=63_371.0,
        )
        fight = BossFightResult(
            boss="loans",  # type: ignore[arg-type]
            label="Fight Student Loans",
            result="lose",  # type: ignore[arg-type]
            raw_score=4,
            threshold_win=7,
            threshold_draw=5,
            reason="ROI 4",
        )
        prompt = bf._narrative_prompt(career, fight)
        # Fallback path: legacy median-debt context still present.
        assert "$19,500" in prompt
        assert "Fight Student Loans" in prompt


class TestRescoreFight:
    def test_rescores_with_updated_stats(self):
        original = _career(res=2, hmn=3)
        lost = _run_one(original, "ai")
        assert lost.result == "lose"

        buffed = _career(res=8, hmn=8)
        rescored = boss_fights.rescore_fight(buffed, "ai")
        assert rescored.result == "win"
        assert rescored.raw_score == 16
        assert rescored.boss == "ai"
        assert rescored.label == "Fight AI"

    def test_unknown_when_inputs_missing(self):
        career = _career()  # all None
        rescored = boss_fights.rescore_fight(career, "ai")
        assert rescored.result == "unknown"

    def test_unknown_boss_raises(self):
        import pytest

        with pytest.raises(ValueError, match="Unknown boss id"):
            boss_fights.rescore_fight(_career(res=5, hmn=5), "nonsense")

    def test_narrative_is_empty_on_rescore(self):
        rescored = boss_fights.rescore_fight(_career(res=8, hmn=8), "ai")
        assert rescored.narrative == ""


class TestRecomputeTotals:
    def test_recount_after_flip(self, monkeypatch):
        from app.services import gemma_client

        monkeypatch.setattr(gemma_client, "generate", lambda **kwargs: "")
        career = _career(res=2, hmn=3, roi=2, grw=2, burnout=10, ceiling=2, ern=2)
        gauntlet = boss_fights.run_gauntlet(career, with_narratives=False)
        original_losses = gauntlet.losses
        assert original_losses >= 1

        # Flip one loss to a win manually, then recompute.
        lost_fight = next(f for f in gauntlet.fights if f.result == "lose")
        lost_fight.result = "win"
        boss_fights.recompute_totals(gauntlet)

        assert gauntlet.losses == original_losses - 1
        assert gauntlet.wins >= 1
        # Verdict recomposes from the new totals.
        assert gauntlet.verdict

    def test_all_wins_produce_dominant_verdict(self, monkeypatch):
        from app.services import gemma_client

        monkeypatch.setattr(gemma_client, "generate", lambda **kwargs: "")
        career = _career(res=9, hmn=9, roi=9, grw=9, burnout=1, ceiling=9, ern=9)
        gauntlet = boss_fights.run_gauntlet(career, with_narratives=False)
        boss_fights.recompute_totals(gauntlet)
        assert gauntlet.losses == 0
        assert "DOMINANT" in gauntlet.verdict or "SOLID" in gauntlet.verdict


class TestStatExplainerRoiNarrative:
    """stat_explainer ROI narrative is cost-based, loan_pct-agnostic.

    Plan: ~/.claude/plans/why-are-we-still-jaunty-curry.md. The ROI
    explanation talks about the 4-year cost of the program vs. the
    starting salary. Financing-specific wording (modeled debt, loan
    coverage %) belongs to the Student Loans Boss narrative, not here.
    """

    def test_cost_of_attendance_narrative_cites_4yr_cost(self):
        career = _career(
            roi=5,
            net_price_annual=14_200.0,
            earnings_1yr_median=50_000.0,
            roi_cost_basis="cost_of_attendance",
        )
        result = boss_fights.stat_explainer(career)

        # 4-year average net price = 14_200 × 4 = 56_800
        assert "$56,800" in result
        assert "average net price" in result.lower()
        assert "$50,000" in result

    def test_debt_median_fallback_narrative(self):
        career = _career(
            roi=5,
            debt_median=19_500.0,
            earnings_1yr_median=50_000.0,
            roi_cost_basis="debt_median",
        )
        result = boss_fights.stat_explainer(career)

        assert "$19,500" in result
        assert "median graduate debt" in result.lower()
        assert "program-level estimate" in result.lower()

    def test_roi_narrative_independent_of_loan_pct(self):
        """The ROI narrative wording must not change with loan_pct."""
        base = dict(
            roi=5,
            net_price_annual=14_200.0,
            earnings_1yr_median=50_000.0,
            roi_cost_basis="cost_of_attendance",
        )
        c0 = _career(**base)
        c0.loan_pct = 0.0
        c1 = _career(**base)
        c1.loan_pct = 1.0
        assert boss_fights.stat_explainer(c0) == boss_fights.stat_explainer(c1)

    def test_roi_narrative_has_no_debt_figures_when_inputs_null(self):
        career = _career(
            roi=5,
            modeled_total_debt=None,
            debt_median=None,
            net_price_annual=None,
            earnings_1yr_median=50_000.0,
        )
        result = boss_fights.stat_explainer(career)

        assert "ROI" in result
        # No cost/debt dollar amounts should appear in the ROI explanation.
        assert "$19,500" not in result
        assert "$56,800" not in result
        assert "projected debt" not in result.lower()
        assert "median graduate debt" not in result.lower()


# ---------------------------------------------------------------------------
# Locale threading — narrate_one + generate_reroll_commentary
# ---------------------------------------------------------------------------


class TestBossFightsLocale:
    def test_narrate_one_passes_spanish_instruction(self, monkeypatch):
        """narrate_one with locale='es' must thread the Spanish instruction
        block into the Gemma system prompt."""
        import asyncio

        from app.services import gemma_client

        captured: dict[str, object] = {}

        async def fake_generate_async(**kwargs):
            captured.update(kwargs)
            return "stub narrative"

        monkeypatch.setattr(
            gemma_client, "generate_async", fake_generate_async
        )

        career = _career(res=3, hmn=7)
        gauntlet = boss_fights.score_gauntlet(career)
        # Pick a fight that is NOT unknown so narrate_one calls Gemma.
        fight = next(f for f in gauntlet.fights if f.result != "unknown")

        result = asyncio.run(
            boss_fights.narrate_one(career, fight, locale="es")
        )

        assert result == "stub narrative"
        system = captured["system"]
        assert isinstance(system, str)
        assert "Write all student-facing prose in Spanish" in system
        assert "deuda estudiantil" in system

    def test_narrate_one_default_locale_is_english(self, monkeypatch):
        import asyncio

        from app.services import gemma_client

        captured: dict[str, object] = {}

        async def fake_generate_async(**kwargs):
            captured.update(kwargs)
            return "stub"

        monkeypatch.setattr(
            gemma_client, "generate_async", fake_generate_async
        )

        career = _career(res=3, hmn=7)
        gauntlet = boss_fights.score_gauntlet(career)
        fight = next(f for f in gauntlet.fights if f.result != "unknown")

        asyncio.run(boss_fights.narrate_one(career, fight))

        system = captured["system"]
        assert "Write student-facing prose in English" in system
        assert "Spanish" not in system

    def test_narrate_one_unknown_fight_skips_gemma(self, monkeypatch):
        """When fight.result == 'unknown', narrate_one returns the
        deterministic fallback without calling Gemma at all."""
        import asyncio

        from app.services import gemma_client

        called = False

        async def fake_generate_async(**kwargs):
            nonlocal called
            called = True
            return "should not be called"

        monkeypatch.setattr(
            gemma_client, "generate_async", fake_generate_async
        )

        career = _career(res=None, hmn=None)
        gauntlet = boss_fights.score_gauntlet(career)
        fight = next(f for f in gauntlet.fights if f.boss == "ai")
        assert fight.result == "unknown"

        result = asyncio.run(
            boss_fights.narrate_one(career, fight, locale="es")
        )

        assert not called, "Gemma should not be called for unknown fights"
        assert result  # Should still return the fallback text

    def test_generate_reroll_commentary_passes_spanish(self, monkeypatch):
        from app.models.career import BossFightResult
        from app.services import gemma_client

        captured: dict[str, object] = {}

        def fake_generate(**kwargs):
            captured.update(kwargs)
            return "reroll commentary"

        monkeypatch.setattr(gemma_client, "generate", fake_generate)

        career = _career(res=5, hmn=7)
        fight = BossFightResult(
            boss="ai",
            label="Fight AI",
            result="draw",
            raw_score=12,
            threshold_win=14,
            threshold_draw=10,
            reason="test",
        )
        boss_fights.generate_reroll_commentary(
            career, fight, "lose", "original narrative",
            ["Data Analytics Minor"],
            locale="es",
        )

        system = captured["system"]
        assert "Write all student-facing prose in Spanish" in system
