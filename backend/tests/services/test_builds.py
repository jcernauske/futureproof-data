"""Tests for build save/load/list/compare round-trip.

Uses the ``isolated_builds_dir`` fixture so the real builds directory
is never touched.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from app.models.api import BuildRequest
from app.models.career import (
    AppliedSkill,
    BossFightResult,
    BossScores,
    Build,
    CareerBranch,
    CareerOutcome,
    GauntletResult,
    PentagonStats,
    SkillRec,
)
from app.routers import builds as builds_router
from app.services import (
    boss_fights,
    branch_tree,
    builds,
    guidance,
    skill_pool,
    skill_recs,
    stat_engine,
)


def _career(title: str = "Fundraisers", ern: int = 8) -> CareerOutcome:
    return CareerOutcome(
        unitid=151351,
        institution_name="Indiana University-Bloomington",
        cipcode="52.14",
        program_name="Marketing",
        soc_code="13-1131",
        occupation_title=title,
        stats=PentagonStats(ern=ern, roi=9, res=4, grw=6, hmn=6),
        bosses=BossScores(ai=7, loans=None, market=7, burnout=6, ceiling=None),
        median_annual_wage=66490.0,
    )


def _gauntlet(wins: int = 3, losses: int = 1) -> GauntletResult:
    fights = [
        BossFightResult(
            boss="ai",  # type: ignore[arg-type]
            label="Fight AI",
            result="lose" if losses > 0 else "win",  # type: ignore[arg-type]
            raw_score=5,
            threshold_win=14,
            threshold_draw=10,
            reason="test",
        ),
        BossFightResult(
            boss="loans",  # type: ignore[arg-type]
            label="Fight Loans",
            result="win",  # type: ignore[arg-type]
            raw_score=9,
            threshold_win=7,
            threshold_draw=5,
            reason="test",
        ),
    ]
    return GauntletResult(
        fights=fights,
        wins=wins,
        losses=losses,
        draws=0,
        unknown=0,
        verdict="TEST BUILD",
    )


def _make_build(*, school: str = "IU-B", major: str = "Marketing") -> Build:
    return builds.build_from_parts(
        school_name=school,
        unitid=151351,
        major_text=major,
        cipcode="52.14",
        program_name="Marketing",
        effort="balanced",
        career=_career(),
        gauntlet=_gauntlet(),
        branches=[
            CareerBranch(
                from_soc="13-1131",
                to_soc="11-2011",
                to_title="Advertising Managers",
                delta_ern=2,
            )
        ],
        skill_recs=[
            SkillRec(
                title="Data Analytics", stat_impact="RES+1", rationale="Test"
            )
        ],
        guidance="test guidance",
    )


class TestBuildCrud:
    def test_save_and_load_round_trip(self, isolated_builds_dir):
        original = _make_build()
        builds.save_build(original)

        loaded = builds.load_build(original.build_id)
        assert loaded.build_id == original.build_id
        assert loaded.career.occupation_title == "Fundraisers"
        assert loaded.gauntlet.verdict == "TEST BUILD"
        assert loaded.guidance == "test guidance"

    def test_missing_build_raises_file_not_found(self, isolated_builds_dir):
        with pytest.raises(FileNotFoundError):
            builds.load_build("nonexistent-001")

    def test_build_id_increments(self, isolated_builds_dir):
        a = _make_build()
        builds.save_build(a)
        b = _make_build()
        builds.save_build(b)
        assert a.build_id.endswith("001")
        assert b.build_id.endswith("002")

    def test_skills_crafted_round_trip(self, isolated_builds_dir):
        """Skills crafted during a reroll must persist through save/load."""
        build = builds.build_from_parts(
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
            guidance="",
            skills_crafted=[
                AppliedSkill(
                    id="data_analytics_minor",
                    title="Data Analytics Minor",
                    rationale="Helps direct AI tools.",
                    targets=["ai", "market"],
                    delta_res=2,
                ),
                AppliedSkill(
                    id="cc_transfer_first_year",
                    title="Community College Transfer (Year 1)",
                    rationale="Cut first-year debt.",
                    targets=["loans"],
                    delta_roi=2,
                ),
            ],
        )
        assert len(build.skills_crafted) == 2
        builds.save_build(build)
        loaded = builds.load_build(build.build_id)
        assert len(loaded.skills_crafted) == 2
        assert loaded.skills_crafted[0].id == "data_analytics_minor"
        assert loaded.skills_crafted[0].delta_res == 2
        assert loaded.skills_crafted[1].delta_roi == 2

    def test_skills_crafted_defaults_to_empty(self, isolated_builds_dir):
        """Builds without rerolls should still round-trip cleanly."""
        build = _make_build()
        assert build.skills_crafted == []
        assert build.skill_pool == []
        builds.save_build(build)
        loaded = builds.load_build(build.build_id)
        assert loaded.skills_crafted == []
        assert loaded.skill_pool == []

    def test_skill_pool_round_trip(self, isolated_builds_dir):
        """Pre-computed personalized skill pool persists through save/load."""
        pool = [
            AppliedSkill(
                id="ai_kelley_analytics_minor",
                title="Kelley Business Analytics minor",
                rationale="Direct AI tools at Kelley.",
                targets=["ai"],
                delta_res=2,
                delta_hmn=1,
            ),
            AppliedSkill(
                id="loans_instate_residency",
                title="In-state residency lock",
                rationale="Cut Kelley sticker price in half.",
                targets=["loans"],
                delta_roi=2,
            ),
        ]
        build = builds.build_from_parts(
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
            guidance="",
            skill_pool=pool,
        )
        assert len(build.skill_pool) == 2
        builds.save_build(build)
        loaded = builds.load_build(build.build_id)
        assert len(loaded.skill_pool) == 2
        assert loaded.skill_pool[0].title == "Kelley Business Analytics minor"
        assert loaded.skill_pool[0].delta_res == 2
        assert loaded.skill_pool[0].delta_hmn == 1
        assert loaded.skill_pool[1].delta_roi == 2

    def test_reroll_bookkeeping_round_trips(self, isolated_builds_dir):
        """BossFightResult's rerolled/original_result fields must persist."""
        build = _make_build()
        # Simulate a reroll having flipped the AI fight from lose to win.
        fight = next(
            f for f in build.gauntlet.fights if f.boss == "ai"
        )
        fight.original_result = "lose"
        fight.original_raw_score = 5
        fight.result = "win"
        fight.raw_score = 16
        fight.rerolled = True
        fight.reroll_count = 1
        builds.save_build(build)

        loaded = builds.load_build(build.build_id)
        loaded_fight = next(
            f for f in loaded.gauntlet.fights if f.boss == "ai"
        )
        assert loaded_fight.rerolled is True
        assert loaded_fight.reroll_count == 1
        assert loaded_fight.original_result == "lose"
        assert loaded_fight.result == "win"

    def test_list_builds_sorted_by_created_at_desc(
        self, isolated_builds_dir
    ):
        first = _make_build(school="IU-B", major="Marketing")
        builds.save_build(first)
        second = _make_build(school="Purdue", major="Engineering")
        builds.save_build(second)

        listing = builds.list_builds()
        assert len(listing) == 2
        assert listing[0].created_at >= listing[1].created_at

    def test_compare_builds_returns_stat_and_boss_rows(
        self, isolated_builds_dir
    ):
        a = _make_build(school="IU-B", major="Marketing")
        builds.save_build(a)
        b = _make_build(school="Purdue", major="Engineering")
        builds.save_build(b)

        comparison = builds.compare_builds([a.build_id, b.build_id])
        assert len(comparison["builds"]) == 2
        assert len(comparison["stats"]) == 5
        assert len(comparison["bosses"]) == 5
        ern_row = next(r for r in comparison["stats"] if r["label"] == "ERN")
        assert ern_row["values"] == [8, 8]


# ---------------------------------------------------------------------------
# /build async fan-out tests (spec: docs/specs/perf-reveal-loading-screen.md)
# ---------------------------------------------------------------------------


def _build_request(**overrides) -> BuildRequest:
    base = dict(
        profile_name="dancing happy bear",
        school_name="Indiana University-Bloomington",
        unitid=151351,
        cipcode="52.14",
        cip_title="Marketing",
        major_text="Marketing",
        effort="balanced",
        loan_pct=0.5,
        selected_soc="13-1131",
        selected_title="Fundraisers",
        student_major="Marketing",
    )
    base.update(overrides)
    return BuildRequest(**base)


class _FanoutHarness:
    """Collects per-call start timestamps for every Gemma-bound coroutine
    the /build router fans out.

    Each mock awaits an artificial sleep so the wall-clock budget stays
    bounded, and ``started_at`` captures the perf_counter() reading at
    entry. After ``asyncio.gather`` completes, the spread between the
    earliest and latest start indicates whether the gather actually ran
    in parallel.
    """

    def __init__(self, *, per_call_sleep_s: float = 0.1):
        self.per_call_sleep_s = per_call_sleep_s
        self.started_at: list[tuple[str, float]] = []
        # narrate_one is called once per fight, in BOSS_SPECS order. We
        # return the boss label so the router's post-gather reassembly
        # can be validated.
        self.narrate_call_order: list[str] = []

    async def narrate_one(self, career, fight, locale="en"):
        self.started_at.append((f"narrate:{fight.boss}", time.perf_counter()))
        self.narrate_call_order.append(fight.boss)
        await asyncio.sleep(self.per_call_sleep_s)
        return f"narrative-for-{fight.boss}"

    async def generate_recs_async(self, career, gauntlet, locale="en"):
        self.started_at.append(("recs", time.perf_counter()))
        await asyncio.sleep(self.per_call_sleep_s)
        return [
            SkillRec(
                title="Data Analytics Minor",
                stat_impact="RES+2",
                rationale="async rec",
            )
        ]

    async def generate_pool_async(self, career, gauntlet, locale="en"):
        self.started_at.append(("pool", time.perf_counter()))
        await asyncio.sleep(self.per_call_sleep_s)
        return []  # empty pool is a valid response

    async def generate_guidance_async(self, career, gauntlet, branches, locale="en"):
        self.started_at.append(("guidance", time.perf_counter()))
        await asyncio.sleep(self.per_call_sleep_s)
        return "async guidance"


def _install_fanout_harness(
    monkeypatch,
    *,
    career_factory=None,
    harness: _FanoutHarness | None = None,
) -> _FanoutHarness:
    """Patch everything the /build router hits outside the Gemma layer.

    Returns the harness instance so the test can inspect timings + order.
    """
    h = harness or _FanoutHarness()
    career = (career_factory or _career)()

    def fake_compute_one(**kwargs):
        return career

    def fake_get_branches(soc_code):
        return []  # empty branches — guidance still renders

    # compute_one and branch_tree.get_branches are called via
    # asyncio.to_thread in the router, so sync functions are fine here.
    monkeypatch.setattr(stat_engine, "compute_one", fake_compute_one)
    monkeypatch.setattr(branch_tree, "get_branches", fake_get_branches)

    # The router dispatches through the module objects it imported at the
    # top of builds.py, so patch THOSE attributes (not the service modules
    # directly) so the async gather actually picks them up.
    monkeypatch.setattr(boss_fights, "narrate_one", h.narrate_one)
    monkeypatch.setattr(skill_recs, "generate_recs_async", h.generate_recs_async)
    monkeypatch.setattr(skill_pool, "generate_pool_async", h.generate_pool_async)
    monkeypatch.setattr(
        guidance, "generate_guidance_async", h.generate_guidance_async
    )

    return h


class TestBuildLocalePersistence:
    """Locale field must survive build_from_parts → save → load round-trip."""

    def test_create_build_with_spanish_locale(self, isolated_builds_dir):
        build = builds.build_from_parts(
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
            locale="es",
        )
        assert build.locale == "es"

        builds.save_build(build)
        loaded = builds.load_build(build.build_id)
        assert loaded.locale == "es"

    def test_create_build_default_locale_is_english(self, isolated_builds_dir):
        build = _make_build()
        assert build.locale == "en"

        builds.save_build(build)
        loaded = builds.load_build(build.build_id)
        assert loaded.locale == "en"

    def test_locale_survives_json_round_trip(self, isolated_builds_dir):
        """Pydantic model_dump_json → model_validate_json must preserve locale."""
        build = builds.build_from_parts(
            school_name="Purdue",
            unitid=99999,
            major_text="Engineering",
            cipcode="14.01",
            program_name="Engineering",
            effort="all_in",
            career=_career(),
            gauntlet=_gauntlet(),
            branches=[],
            skill_recs=[],
            guidance="",
            locale="es",
        )
        json_str = build.model_dump_json()
        restored = Build.model_validate_json(json_str)
        assert restored.locale == "es"


class TestCreateBuildParallelFanout:
    """The /build router must fan out all 8 Gemma-bound coroutines via
    asyncio.gather — not await them serially.

    With 5 boss narratives + recs + pool + guidance, sequential
    execution at 100 ms each would cost ~800 ms wall clock. Parallel
    gather should complete in ~100 ms regardless of count.
    """

    def test_create_build_parallel_fanout(
        self, isolated_builds_dir, monkeypatch
    ):
        h = _install_fanout_harness(monkeypatch)

        wall_started = time.perf_counter()
        build = asyncio.run(
            builds_router.create_build(_build_request())
        )
        wall_elapsed = time.perf_counter() - wall_started

        # Every coroutine recorded one start. 5 narratives + 3 sibling
        # calls = 8 total.
        assert len(h.started_at) == 8, (
            f"expected 8 fan-out coroutines, saw {len(h.started_at)}: "
            f"{[name for name, _ in h.started_at]}"
        )

        # All 8 start within 100ms of each other — the gather fired them
        # concurrently instead of awaiting each in sequence.
        earliest = min(ts for _, ts in h.started_at)
        latest = max(ts for _, ts in h.started_at)
        spread_ms = (latest - earliest) * 1000
        assert spread_ms < 100, (
            f"fan-out start spread was {spread_ms:.1f}ms — gather isn't "
            f"running in parallel. Timings: "
            f"{[(n, round((t - earliest) * 1000, 1)) for n, t in h.started_at]}"
        )

        # Wall clock must be closer to a single sleep (~100 ms) than the
        # serial budget (~800 ms). Generous guard at 500 ms lets CI
        # wobble without false positives while still catching a
        # regression to serial awaits.
        assert wall_elapsed < 0.5, (
            f"wall clock was {wall_elapsed * 1000:.0f}ms — gather isn't "
            f"running in parallel (serial budget would be ~800ms)"
        )

        # Final build is well-formed.
        assert isinstance(build, Build)
        assert build.guidance == "async guidance"
        assert len(build.gauntlet.fights) == 5
        assert build.skill_recs[0].title == "Data Analytics Minor"


class TestCreateBuildPartialFailureFallback:
    """``return_exceptions=True`` in the gather means one Gemma call
    raising must NOT poison the response. The failing site falls back
    to its deterministic string; the other 7 produce real content."""

    def test_one_narrate_raises_others_succeed(
        self, isolated_builds_dir, monkeypatch
    ):
        class _PartialHarness(_FanoutHarness):
            async def narrate_one(self, career, fight, locale="en"):
                self.started_at.append(
                    (f"narrate:{fight.boss}", time.perf_counter())
                )
                self.narrate_call_order.append(fight.boss)
                await asyncio.sleep(self.per_call_sleep_s)
                # Market narrative is the one Gemma ghosted.
                if fight.boss == "market":
                    raise RuntimeError("OpenRouter 503 for market narrative")
                return f"narrative-for-{fight.boss}"

        _install_fanout_harness(
            monkeypatch, harness=_PartialHarness(per_call_sleep_s=0.05)
        )

        build = asyncio.run(
            builds_router.create_build(_build_request())
        )

        # The 7 non-failing calls produced real content.
        for fight in build.gauntlet.fights:
            if fight.boss == "market":
                continue
            assert fight.narrative == f"narrative-for-{fight.boss}", (
                f"{fight.boss} narrative got clobbered: {fight.narrative!r}"
            )

        # The failing site fell back to the deterministic string. The
        # fallback must carry Gemma's voice: non-empty, but never leaks
        # the internal boss label, outcome pill, stat codes, or game
        # framing (see _NARRATIVE_SYSTEM rules in boss_fights.py).
        market_fight = next(
            f for f in build.gauntlet.fights if f.boss == "market"
        )
        assert market_fight.narrative != ""
        for forbidden in (
            "Fight the Market",
            "boss",
            "gauntlet",
            market_fight.result.upper(),
            "GRW",
        ):
            assert forbidden not in market_fight.narrative, (
                f"market degraded fallback leaked {forbidden!r}: "
                f"{market_fight.narrative!r}"
            )

        # Recs/pool/guidance still succeeded.
        assert build.guidance == "async guidance"
        assert build.skill_recs[0].title == "Data Analytics Minor"

        # The build is persisted to the isolated DuckDB — loading it back
        # proves it's well-formed.
        reloaded = builds.load_build(build.build_id)
        assert reloaded.build_id == build.build_id
        assert reloaded.guidance == "async guidance"

    def test_recs_raises_falls_back_to_deterministic(
        self, isolated_builds_dir, monkeypatch
    ):
        """If generate_recs_async crashes, the router must substitute
        the canonical fallback set instead of losing the section."""

        class _RecsFailHarness(_FanoutHarness):
            async def generate_recs_async(self, career, gauntlet, locale="en"):
                self.started_at.append(("recs", time.perf_counter()))
                await asyncio.sleep(self.per_call_sleep_s)
                raise RuntimeError("boom")

        _install_fanout_harness(
            monkeypatch, harness=_RecsFailHarness(per_call_sleep_s=0.05)
        )

        build = asyncio.run(
            builds_router.create_build(_build_request())
        )

        # Deterministic fallback carries exactly three canonical recs.
        assert len(build.skill_recs) == 3
        titles = [r.title for r in build.skill_recs]
        assert "Data Analytics coursework" in titles
        # Other sections still succeeded.
        assert build.guidance == "async guidance"

    def test_guidance_raises_falls_back_to_template(
        self, isolated_builds_dir, monkeypatch
    ):
        """guidance failure must substitute the deterministic template
        string, NOT leave the build with an empty narrative."""

        class _GuidanceFailHarness(_FanoutHarness):
            async def generate_guidance_async(
                self, career, gauntlet, branches, locale="en"
            ):
                self.started_at.append(("guidance", time.perf_counter()))
                await asyncio.sleep(self.per_call_sleep_s)
                raise RuntimeError("OpenRouter outage")

        _install_fanout_harness(
            monkeypatch, harness=_GuidanceFailHarness(per_call_sleep_s=0.05)
        )

        build = asyncio.run(
            builds_router.create_build(_build_request())
        )

        assert build.guidance != ""
        # Fallback template references the school and program.
        assert "Indiana University-Bloomington" in build.guidance
        assert "Marketing" in build.guidance


class TestCreateBuildPreservesFightOrder:
    """Fights must stay in BOSS_SPECS iteration order after the gather —
    regardless of which Gemma narrative finishes first."""

    def test_fights_stay_in_boss_specs_order(
        self, isolated_builds_dir, monkeypatch
    ):
        # Vary per-call sleep by boss so narratives complete in reverse
        # order relative to how they were scheduled. If the router
        # reassembles by completion order instead of spec order, the
        # narratives will land on the wrong fights.
        sleep_by_boss = {
            "ai": 0.15,
            "loans": 0.12,
            "market": 0.09,
            "burnout": 0.06,
            "ceiling": 0.03,
        }

        class _OutOfOrderHarness(_FanoutHarness):
            async def narrate_one(self, career, fight, locale="en"):
                self.started_at.append(
                    (f"narrate:{fight.boss}", time.perf_counter())
                )
                self.narrate_call_order.append(fight.boss)
                await asyncio.sleep(sleep_by_boss.get(fight.boss, 0.05))
                return f"narrative-for-{fight.boss}"

        h = _install_fanout_harness(
            monkeypatch, harness=_OutOfOrderHarness(per_call_sleep_s=0.05)
        )

        build = asyncio.run(
            builds_router.create_build(_build_request())
        )

        # Fights are in BOSS_SPECS iteration order (ai, loans, market,
        # burnout, ceiling).
        expected_order = list(boss_fights.BOSS_SPECS.keys())
        actual_order = [f.boss for f in build.gauntlet.fights]
        assert actual_order == expected_order, (
            f"fight order drifted: expected {expected_order}, "
            f"got {actual_order}"
        )

        # Every fight carries the narrative that matches its boss id —
        # not the narrative of whichever call happened to finish first.
        for fight in build.gauntlet.fights:
            assert fight.narrative == f"narrative-for-{fight.boss}", (
                f"{fight.boss} got wrong narrative: {fight.narrative!r}"
            )

        # Also verify narrate_one was actually invoked in schedule order
        # (the scheduling side is separate from the reassembly side).
        assert h.narrate_call_order == expected_order
