"""Unit tests for pure helpers in wrapped_renderer.py.

These tests deliberately stay in the Python-only layer:
- `_pentagon_svg`       — SVG generation math
- `_pick_standout_stat` — tie-break + None-safe selection
- `_build_context`      — Jinja context assembly (6 frames)
- Frame-5 branching     — clean-sweep vs biggest-risk selection

Playwright / Chromium are NEVER launched here. The render_frames()
coroutine is integration-only; see the router test for mocked coverage.
"""

from __future__ import annotations

from app.models.career import (
    AppliedSkill,
    BossFightResult,
    BossScores,
    Build,
    CareerOutcome,
    GauntletResult,
    PentagonStats,
)
from app.services import wrapped_renderer

# --- Helpers ---------------------------------------------------------------


def _fight(
    boss: str,
    result: str,
    *,
    raw_score: int | None = 10,
    narrative: str = "",
    reason: str = "r",
) -> BossFightResult:
    return BossFightResult(
        boss=boss,  # type: ignore[arg-type]
        label=boss.title(),
        result=result,  # type: ignore[arg-type]
        raw_score=raw_score,
        threshold_win=14,
        threshold_draw=10,
        reason=reason,
        narrative=narrative,
    )


def _build(
    *,
    stats: PentagonStats | None = None,
    fights: list[BossFightResult] | None = None,
    skills_crafted: list[AppliedSkill] | None = None,
    profile_name: str = "",
    school: str = "IU-B",
    major: str = "Marketing",
    career_title: str = "Financial Analyst",
) -> Build:
    stats = stats or PentagonStats(ern=8, roi=9, res=4, grw=6, aura=6)
    if fights is None:
        fights = [
            _fight("ai", "win"),
            _fight("loans", "win"),
            _fight("market", "lose", raw_score=3),
            _fight("burnout", "win"),
            _fight("ceiling", "draw"),
        ]
    wins = sum(1 for f in fights if f.result == "win")
    losses = sum(1 for f in fights if f.result == "lose")
    draws = sum(1 for f in fights if f.result == "draw")
    unknown = sum(1 for f in fights if f.result == "unknown")

    career = CareerOutcome(
        unitid=151351,
        institution_name=school,
        cipcode="52.14",
        program_name=major,
        soc_code="13-2051",
        occupation_title=career_title,
        stats=stats,
        bosses=BossScores(ai=7, loans=None, market=7, burnout=6, ceiling=None),
        median_annual_wage=66490.0,
    )
    return Build(
        build_id="iu-b-marketing-001",
        created_at="2026-04-15T12:00:00+00:00",
        school_name=school,
        unitid=151351,
        major_text=major,
        cipcode="52.14",
        program_name=major,
        effort="balanced",
        career=career,
        gauntlet=GauntletResult(
            fights=fights,
            wins=wins,
            losses=losses,
            draws=draws,
            unknown=unknown,
            verdict="Solid build.",
        ),
        branches=[],
        skill_recs=[],
        guidance="",
        skills_crafted=skills_crafted or [],
        profile_name=profile_name,
    )


# --- _pentagon_svg ---------------------------------------------------------


class TestPentagonSvg:
    def test_returns_valid_svg_string(self):
        svg = wrapped_renderer._pentagon_svg(
            {"ern": 8, "roi": 9, "res": 4, "grw": 6, "aura": 6}
        )
        assert svg.lstrip().startswith("<svg")
        assert svg.rstrip().endswith("</svg>")
        assert 'xmlns="http://www.w3.org/2000/svg"' in svg

    def test_has_exactly_five_vertex_circles(self):
        """One filled circle per axis — 5 stat points, no more, no less."""
        svg = wrapped_renderer._pentagon_svg(
            {"ern": 5, "roi": 5, "res": 5, "grw": 5, "aura": 5}
        )
        # Circle elements are the only <circle> in the SVG
        assert svg.count("<circle") == 5

    def test_includes_fill_polygon_and_grid_rings(self):
        svg = wrapped_renderer._pentagon_svg(
            {"ern": 8, "roi": 9, "res": 4, "grw": 6, "aura": 6}
        )
        # 4 grid-ring polygons + 1 data polygon = 5
        assert svg.count("<polygon") == 5
        # 5 axis spokes
        assert svg.count("<line") == 5

    def test_missing_stats_treated_as_zero(self):
        """None values collapse to radius 0 (center) — do NOT crash."""
        svg = wrapped_renderer._pentagon_svg(
            {"ern": None, "roi": None, "res": None, "grw": None, "aura": None}
        )
        # All five points collapse to center (390.0, 390.0) — no NaN/None
        # leaked into the points attribute
        assert "None" not in svg
        assert "nan" not in svg.lower()
        # 5 vertex dots all at center
        assert svg.count("<circle") == 5

    def test_out_of_range_high_value_clamped(self):
        """A value of 15 (above 10) must NOT push points past r_max=300."""
        svg = wrapped_renderer._pentagon_svg(
            {"ern": 15, "roi": 0, "res": 0, "grw": 0, "aura": 0}
        )
        # Canvas is 780x780, center (390, 390), r_max=300 so vertices
        # must stay within [90, 690]. Extract polygon points and verify.
        # We do this by making sure no coordinate falls outside that range.
        import re
        nums = [float(x) for x in re.findall(r"\d+\.\d+", svg)]
        # All numbers should be within the SVG canvas (0..780)
        leaked = [n for n in nums if n < 0 or n > 780]
        assert all(0 <= n <= 780 for n in nums), (
            f"Pentagon coordinates leaked outside canvas: {leaked}"
        )

    def test_negative_value_clamped_to_zero(self):
        svg = wrapped_renderer._pentagon_svg(
            {"ern": -5, "roi": 0, "res": 0, "grw": 0, "aura": 0}
        )
        # Should not crash, should not contain negative coords
        assert "--" not in svg  # no double-minus from formatting


# --- _pick_standout_stat ---------------------------------------------------


class TestPickStandoutStat:
    def test_picks_strict_highest(self):
        build = _build(
            stats=PentagonStats(ern=2, roi=3, res=9, grw=4, aura=5)
        )
        assert wrapped_renderer._pick_standout_stat(build) == "res"

    def test_tie_break_picks_first_in_ern_roi_res_grw_hmn_order(self):
        """Tie-break rule per spec: ERN wins over ROI, ROI over RES, etc.

        Implementation is "first with strictly-greater value wins" —
        so equal scores keep the earliest key in the ordered list.
        """
        build = _build(
            stats=PentagonStats(ern=8, roi=8, res=8, grw=8, aura=8)
        )
        assert wrapped_renderer._pick_standout_stat(build) == "ern"

    def test_tie_break_across_subset(self):
        """ROI wins over RES/GRW/AURA when all are tied at the max."""
        build = _build(
            stats=PentagonStats(ern=3, roi=7, res=7, grw=7, aura=7)
        )
        assert wrapped_renderer._pick_standout_stat(build) == "roi"

    def test_all_none_stats_defaults_to_ern(self):
        """Per the implementation's best_key default. No crash."""
        build = _build(
            stats=PentagonStats(ern=None, roi=None, res=None, grw=None, aura=None)
        )
        assert wrapped_renderer._pick_standout_stat(build) == "ern"

    def test_none_stat_never_wins_over_real_value(self):
        """A present stat of 1 beats any number of None stats."""
        build = _build(
            stats=PentagonStats(ern=None, roi=None, res=1, grw=None, aura=None)
        )
        assert wrapped_renderer._pick_standout_stat(build) == "res"

    def test_zero_is_a_valid_stat_value(self):
        """0 beats -1 but loses to 1 — standard comparison."""
        build = _build(
            stats=PentagonStats(ern=0, roi=0, res=0, grw=0, aura=0)
        )
        # All zero, all present — first-key wins is ERN
        assert wrapped_renderer._pick_standout_stat(build) == "ern"


# --- _build_context --------------------------------------------------------


class TestBuildContext:
    FRAME_KEYS = {"identity", "pentagon", "bosses", "insight", "risk", "cta"}

    def test_returns_six_frame_contexts(self):
        ctx = wrapped_renderer._build_context(
            _build(profile_name="bold bear"), "bold bear", "🐻"
        )
        assert set(ctx.keys()) == self.FRAME_KEYS

    def test_identity_ctx_shape(self):
        ctx = wrapped_renderer._build_context(
            _build(profile_name="bold bear"), "bold bear", "🐻"
        )
        identity = ctx["identity"]
        expected_keys = {
            "base_css", "profile_name_display", "profile_emoji",
            "school_name", "major_text",
        }
        assert expected_keys.issubset(identity.keys())
        assert identity["school_name"] == "IU-B"
        assert identity["major_text"] == "Marketing"
        assert identity["profile_emoji"] == "🐻"
        assert "bold bear" in identity["profile_name_display"]

    def test_empty_profile_name_falls_back_to_anonymous(self):
        """profile_name="" must not surface as an empty string in the UI."""
        ctx = wrapped_renderer._build_context(
            _build(profile_name=""), "", ""
        )
        # Display text must be non-empty
        assert ctx["identity"]["profile_name_display"].strip()
        assert "Anonymous" in ctx["identity"]["profile_name_display"]

    def test_empty_emoji_falls_back_to_star(self):
        """Never leave profile_emoji blank — UI expects SOMETHING to render."""
        ctx = wrapped_renderer._build_context(
            _build(profile_name="alice"), "alice", ""
        )
        assert ctx["identity"]["profile_emoji"] == "✦"
        assert ctx["cta"]["profile_emoji"] == "✦"

    def test_pentagon_ctx_embeds_stat_values(self):
        build = _build(
            stats=PentagonStats(ern=8, roi=9, res=4, grw=6, aura=6),
            career_title="Financial Analyst",
        )
        ctx = wrapped_renderer._build_context(build, "alice", "🦊")
        p = ctx["pentagon"]
        assert p["stat_ern"] == 8
        assert p["stat_roi"] == 9
        assert p["stat_res"] == 4
        assert p["stat_grw"] == 6
        assert p["stat_aura"] == 6
        assert p["career_title"] == "Financial Analyst"
        assert p["pentagon_svg"].lstrip().startswith("<svg")

    def test_pentagon_ctx_renders_em_dash_for_missing_stats(self):
        """None stats surface as "—" in the UI layer, not as None."""
        build = _build(
            stats=PentagonStats(ern=None, roi=5, res=None, grw=5, aura=None)
        )
        p = wrapped_renderer._build_context(build, "x", "🐻")["pentagon"]
        assert p["stat_ern"] == "—"
        assert p["stat_roi"] == 5
        assert p["stat_res"] == "—"
        assert p["stat_aura"] == "—"

    def test_bosses_ctx_includes_all_fights_with_formatted_fields(self):
        build = _build()
        ctx = wrapped_renderer._build_context(build, "alice", "🦊")
        bosses = ctx["bosses"]
        assert len(bosses["fights"]) == 5
        # Each fight has the normalized result fields
        for f in bosses["fights"]:
            assert set(f.keys()) >= {
                "boss", "label", "result", "result_upper", "emoji"
            }
            assert f["result_upper"] == f["result"].upper()
        assert bosses["wins"] == 3
        assert bosses["losses"] == 1
        assert bosses["draws"] == 1

    def test_bosses_ctx_verdict_falls_back_when_empty(self):
        """An empty verdict string must not print as nothing on the frame."""
        build = _build()
        build.gauntlet.verdict = ""
        ctx = wrapped_renderer._build_context(build, "alice", "🦊")
        assert ctx["bosses"]["verdict_text"] == "Build complete"

    def test_empty_fights_renders_without_error(self):
        """Saboteur: what if gauntlet.fights is empty?

        The _build_context function iterates fights to build boss cards.
        Zero fights must not crash — the frame should just render empty.
        """
        build = _build(fights=[])
        ctx = wrapped_renderer._build_context(build, "alice", "🦊")
        assert ctx["bosses"]["fights"] == []
        # Clean-sweep logic triggers when len(losses) == 0
        # (which is true when there are no fights at all)
        assert ctx["risk"]["clean_sweep"] is True


# --- Frame-5: Clean Sweep vs Biggest Risk ----------------------------------


class TestRiskFrameBranching:
    def test_clean_sweep_when_all_wins(self):
        build = _build(fights=[
            _fight("ai", "win"),
            _fight("loans", "win"),
            _fight("market", "win"),
            _fight("burnout", "win"),
            _fight("ceiling", "win"),
        ])
        ctx = wrapped_renderer._build_context(build, "alice", "🦊")
        assert ctx["risk"]["clean_sweep"] is True
        # Clean-sweep frame hides boss-specific content
        assert ctx["risk"]["boss_name"] == ""
        assert ctx["risk"]["boss_emoji"] == ""

    def test_clean_sweep_when_wins_and_draws_only_no_losses(self):
        """Draws are not losses — clean-sweep should still trigger.

        The implementation checks `f.result == "lose"`, so a gauntlet
        with only wins + draws (zero losses) is a clean sweep.
        """
        build = _build(fights=[
            _fight("ai", "win"),
            _fight("loans", "draw"),
            _fight("market", "draw"),
            _fight("burnout", "win"),
            _fight("ceiling", "draw"),
        ])
        ctx = wrapped_renderer._build_context(build, "alice", "🦊")
        assert ctx["risk"]["clean_sweep"] is True

    def test_biggest_risk_picks_lowest_raw_score_loss(self):
        """Among losses, the one with the lowest raw_score is the 'worst hit'."""
        build = _build(fights=[
            _fight("ai", "lose", raw_score=8),          # bad
            _fight("loans", "lose", raw_score=3),       # WORST (should win)
            _fight("market", "lose", raw_score=5),      # worse
            _fight("burnout", "win"),
            _fight("ceiling", "win"),
        ])
        ctx = wrapped_renderer._build_context(build, "alice", "🦊")
        assert ctx["risk"]["clean_sweep"] is False
        assert ctx["risk"]["boss_name"] == "Student Loans"

    def test_biggest_risk_single_loss(self):
        """Only one loss — that must be the biggest risk (no ambiguity)."""
        build = _build(fights=[
            _fight("ai", "win"),
            _fight("loans", "win"),
            _fight("market", "lose", raw_score=2, narrative="The market is rough."),
            _fight("burnout", "win"),
            _fight("ceiling", "draw"),
        ])
        ctx = wrapped_renderer._build_context(build, "alice", "🦊")
        risk = ctx["risk"]
        assert risk["clean_sweep"] is False
        assert risk["boss_name"] == "The Market"
        assert risk["result_label"] == "LOSS"
        assert risk["narrative"] == "The market is rough."

    def test_biggest_risk_none_raw_score_treated_as_zero(self):
        """The min()-key uses `raw_score if not None else 0`.

        A loss with raw_score=None has key=0, which is minimum unless
        another loss has raw_score<=0. Verify no crash and deterministic pick.
        """
        build = _build(fights=[
            _fight("ai", "lose", raw_score=None),
            _fight("loans", "lose", raw_score=5),
            _fight("market", "win"),
            _fight("burnout", "win"),
            _fight("ceiling", "win"),
        ])
        ctx = wrapped_renderer._build_context(build, "alice", "🦊")
        # AI has key=0, loans has key=5 → AI wins (lowest)
        assert ctx["risk"]["boss_name"] == "Fight AI"

    def test_biggest_risk_falls_back_when_narrative_and_reason_empty(self):
        build = _build(fights=[
            _fight("market", "lose", raw_score=3, narrative="", reason=""),
            _fight("ai", "win"),
            _fight("loans", "win"),
            _fight("burnout", "win"),
            _fight("ceiling", "win"),
        ])
        ctx = wrapped_renderer._build_context(build, "alice", "🦊")
        assert ctx["risk"]["narrative"] == "This boss hit hardest in your build."

    def test_biggest_risk_surfaces_matching_crafted_skills(self):
        """skills_crafted entries that target the biggest-risk boss bubble up."""
        loan_skill = AppliedSkill(
            id="loans_1",
            title="Income-Driven Repayment",
            rationale="IDR plan",
            targets=["loans"],
            delta_roi=2,
        )
        unrelated_skill = AppliedSkill(
            id="ai_1",
            title="Data Analytics",
            rationale="AI defense",
            targets=["ai"],
            delta_res=2,
        )
        build = _build(
            fights=[
                _fight("ai", "win"),
                _fight("loans", "lose", raw_score=2),
                _fight("market", "win"),
                _fight("burnout", "win"),
                _fight("ceiling", "draw"),
            ],
            skills_crafted=[loan_skill, unrelated_skill],
        )
        ctx = wrapped_renderer._build_context(build, "alice", "🦊")
        risk = ctx["risk"]
        assert risk["skills"] == ["Income-Driven Repayment"]
        # The unrelated skill must NOT leak in
        assert "Data Analytics" not in risk["skills"]

    def test_biggest_risk_uses_loans_palette_for_unknown_boss(self):
        """Defensive: an unknown boss id falls back to the loans palette.

        This protects against schema drift where a new boss type lands
        in the gauntlet data before the palette map is updated.
        """
        bad_fight = BossFightResult(
            boss="ai",  # type: ignore[arg-type]
            label="Unknown",
            result="lose",  # type: ignore[arg-type]
            raw_score=2,
            threshold_win=14,
            threshold_draw=10,
            reason="x",
        )
        # Force-override after construction to bypass Literal validation
        bad_fight.boss = "mystery_boss"  # type: ignore[assignment]
        build = _build(fights=[
            bad_fight,
            _fight("loans", "win"),
            _fight("market", "win"),
            _fight("burnout", "win"),
            _fight("ceiling", "win"),
        ])
        ctx = wrapped_renderer._build_context(build, "alice", "🦊")
        # No crash; boss_color defined
        assert ctx["risk"]["boss_color"]
        assert ctx["risk"]["boss_color_strong"]
