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
        stats=PentagonStats(ern=ern, roi=9, res=4, grw=6, aura=6),
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
        # delta_hmn was removed in pentagon-stat-reshape v1.2 (AppliedSkill
        # no longer carries it; RES absorbs the human-essential signal).
        assert not hasattr(loaded.skill_pool[0], "delta_hmn")
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

    # --- P2: Party Select expanded fields (spec: feature-party-select) ---

    def test_compare_builds_returns_expanded_build_fields(
        self, isolated_builds_dir
    ):
        """compare_builds must return soc_code, profile_name, animal_emoji,
        school_name, major_text, effort, loan_pct, and financial fields
        per build — the Party Select character card depends on these."""
        a = _make_build(school="IU-B", major="Marketing")
        builds.save_build(a)
        b = _make_build(school="Purdue", major="Engineering")
        builds.save_build(b)

        comparison = builds.compare_builds([a.build_id, b.build_id])
        build_a = comparison["builds"][0]

        # Identity fields.
        assert build_a["soc_code"] == "13-1131"
        assert build_a["school_name"] == "IU-B"
        assert build_a["major_text"] == "Marketing"
        assert build_a["label"] == "IU-B — Marketing"
        assert build_a["career"] == "Fundraisers"
        assert build_a["effort"] == "balanced"
        assert build_a["loan_pct"] == 1.0

        # Financial fields (median_annual_wage comes from _career fixture).
        assert build_a["median_annual_wage"] == 66490.0
        # _career does not set net_price_annual or modeled_total_debt.
        assert build_a["net_price_annual"] is None
        assert build_a["modeled_total_debt"] is None

        # profile_name and animal_emoji.
        assert "profile_name" in build_a
        assert "animal_emoji" in build_a

    def test_compare_builds_returns_boss_skill_counts_and_original_values(
        self, isolated_builds_dir
    ):
        """Boss rows must include skill_counts and original_values for the
        Party Select skill badge UI."""
        a = _make_build(school="IU-B", major="Marketing")
        # Simulate a reroll on the AI fight: flipped from lose to win.
        ai_fight = next(
            f for f in a.gauntlet.fights if f.boss == "ai"
        )
        ai_fight.original_result = "lose"
        ai_fight.result = "win"
        ai_fight.rerolled = True
        ai_fight.reroll_count = 2
        builds.save_build(a)

        b = _make_build(school="Purdue", major="Engineering")
        builds.save_build(b)

        comparison = builds.compare_builds([a.build_id, b.build_id])
        ai_boss = next(
            r for r in comparison["bosses"] if r["boss_id"] == "ai"
        )

        # Build A had a reroll; Build B did not.
        assert ai_boss["skill_counts"] == [2, 0]
        assert ai_boss["original_values"] == ["LOSE", "LOSE"]
        assert ai_boss["values"] == ["WIN", "LOSE"]

    def test_compare_builds_returns_branch_data(self, isolated_builds_dir):
        """branches key must include top-3 destinations per build."""
        a = _make_build(school="IU-B", major="Marketing")
        builds.save_build(a)
        b = _make_build(school="Purdue", major="Engineering")
        builds.save_build(b)

        comparison = builds.compare_builds([a.build_id, b.build_id])
        assert "branches" in comparison
        assert len(comparison["branches"]) == 2

        branch_a = comparison["branches"][0]
        assert branch_a["build_id"] == a.build_id
        assert branch_a["career"] == "Fundraisers"
        assert len(branch_a["destinations"]) == 1
        assert branch_a["destinations"][0]["to_title"] == "Advertising Managers"
        assert branch_a["destinations"][0]["to_soc"] == "11-2011"
        assert branch_a["destinations"][0]["delta_ern"] == 2

    def test_compare_builds_handles_four_builds(self, isolated_builds_dir):
        """4-build comparison must not error — Party Select supports 2-4."""
        a = _make_build(school="IU-B", major="Marketing")
        builds.save_build(a)
        b = _make_build(school="Purdue", major="Engineering")
        builds.save_build(b)
        c = _make_build(school="UC Berkeley", major="Finance")
        builds.save_build(c)
        d = _make_build(school="Ohio State", major="Accounting")
        builds.save_build(d)

        comparison = builds.compare_builds(
            [a.build_id, b.build_id, c.build_id, d.build_id]
        )
        assert len(comparison["builds"]) == 4
        assert all(len(r["values"]) == 4 for r in comparison["stats"])
        assert all(len(r["values"]) == 4 for r in comparison["bosses"])
        assert all(
            len(r["skill_counts"]) == 4 for r in comparison["bosses"]
        )
        assert len(comparison["branches"]) == 4

    def test_compare_builds_branches_limited_to_three(
        self, isolated_builds_dir
    ):
        """Branch destinations must be capped at 3 per build even when
        the build has more."""
        five_branches = [
            CareerBranch(
                from_soc="13-1131", to_soc=f"11-{i:04d}", to_title=f"Branch {i}"
            )
            for i in range(5)
        ]
        a = builds.build_from_parts(
            school_name="IU-B",
            unitid=151351,
            major_text="Marketing",
            cipcode="52.14",
            program_name="Marketing",
            effort="balanced",
            career=_career(),
            gauntlet=_gauntlet(),
            branches=five_branches,
            skill_recs=[],
            guidance="test",
        )
        builds.save_build(a)
        b = _make_build(school="Purdue", major="Engineering")
        builds.save_build(b)

        comparison = builds.compare_builds([a.build_id, b.build_id])
        branch_a = comparison["branches"][0]
        assert len(branch_a["destinations"]) == 3

    def test_compare_builds_missing_fight_shows_dash_and_zero_skills(
        self, isolated_builds_dir
    ):
        """When a build has no fight for a boss_id (e.g. the gauntlet
        fixture only has ai + loans), the comparison row must show '—'
        for the value, 0 for skill_counts, and '—' for original_values."""
        a = _make_build(school="IU-B", major="Marketing")
        builds.save_build(a)
        b = _make_build(school="Purdue", major="Engineering")
        builds.save_build(b)

        comparison = builds.compare_builds([a.build_id, b.build_id])
        # Our gauntlet only has "ai" and "loans" fights, so "market",
        # "burnout", and "ceiling" are missing.
        market_boss = next(
            r for r in comparison["bosses"] if r["boss_id"] == "market"
        )
        assert market_boss["values"] == ["—", "—"]
        assert market_boss["skill_counts"] == [0, 0]
        assert market_boss["original_values"] == ["—", "—"]

    # --- P0: Cost detail fields (spec: feature-compare-screen-redesign) ---

    def test_compare_builds_returns_cost_detail_fields(
        self, isolated_builds_dir, monkeypatch
    ):
        """compare_builds must return new cost detail + earnings range
        fields from CareerOutcome for the Cost Breakdown accordion."""
        # Patch out _fetch_institution_profiles so we don't need MCP.
        monkeypatch.setattr(
            builds,
            "_fetch_institution_profiles",
            lambda _builds: {},
        )
        a = _make_build(school="IU-B", major="Marketing")
        builds.save_build(a)
        b = _make_build(school="Purdue", major="Engineering")
        builds.save_build(b)

        comparison = builds.compare_builds([a.build_id, b.build_id])
        build_a = comparison["builds"][0]

        # All 10 new CareerOutcome-derived fields must be present as keys.
        cost_fields = [
            "cost_of_attendance_annual",
            "published_cost_4yr",
            "room_board_on_campus",
            "tuition_in_state",
            "tuition_out_of_state",
            "earnings_1yr_median",
            "earnings_1yr_p25",
            "earnings_1yr_p75",
            "state_abbr",
            "aura_score_basis",
        ]
        for field in cost_fields:
            assert field in build_a, (
                f"compare response missing cost detail field: {field}"
            )

        # The _career() fixture doesn't set these fields, so they
        # should all be None — verifying the pipeline handles absence.
        assert build_a["cost_of_attendance_annual"] is None
        assert build_a["published_cost_4yr"] is None
        assert build_a["room_board_on_campus"] is None
        assert build_a["tuition_in_state"] is None
        assert build_a["tuition_out_of_state"] is None
        assert build_a["earnings_1yr_p25"] is None
        assert build_a["earnings_1yr_p75"] is None
        assert build_a["state_abbr"] is None

    # --- P0: Institution profile fields ---

    def test_compare_builds_returns_institution_profile_fields(
        self, isolated_builds_dir, monkeypatch
    ):
        """compare_builds must return institution profile fields derived
        from the MCP get_institution_aura call and Iceberg FTE query."""
        # Mock MCP call: get_institution_aura returns realistic data.
        mock_aura_response = {
            "data": {
                "endowment_per_fte": 45000.0,
                "marketing_ratio": 0.12,
                "athletic_spend_per_fte": 2100.0,
                "athletic_revenue_per_fte": 3500.0,
                "athletic_subsidy_ratio": 0.15,
                "coverage_tier": "full",
            },
            "row_count": 1,
        }

        def mock_mcp_call(tool: str, args: dict):
            if tool == "get_institution_aura":
                return mock_aura_response
            raise ValueError(f"Unexpected MCP tool call: {tool}")

        # Mock the Iceberg query for FTE enrollment.
        class FakeServer:
            def query_iceberg_simple(self, table, *, filters, columns, limit):
                if table == "consumable.ipeds_finance_profile":
                    return [{"total_fte_enrollment": 35000}]
                return []

        monkeypatch.setattr(
            "app.services.mcp_client.call", mock_mcp_call
        )
        monkeypatch.setattr(
            "app.services.mcp_client.get_server", lambda: FakeServer()
        )

        a = _make_build(school="IU-B", major="Marketing")
        builds.save_build(a)
        b = _make_build(school="Purdue", major="Engineering")
        builds.save_build(b)

        comparison = builds.compare_builds([a.build_id, b.build_id])
        build_a = comparison["builds"][0]

        # Institution profile fields must be populated from mock data.
        assert build_a["endowment_per_fte"] == 45000.0
        assert build_a["marketing_ratio"] == 0.12
        assert build_a["athletic_spend_per_fte"] == 2100.0
        assert build_a["athletic_revenue_per_fte"] == 3500.0
        assert build_a["athletic_subsidy_ratio"] == 0.15
        assert build_a["coverage_tier"] == "full"
        assert build_a["fte_enrollment"] == 35000

    # --- P1: Institution profile caching by unitid ---

    def test_compare_builds_caches_institution_profile_by_unitid(
        self, isolated_builds_dir, monkeypatch
    ):
        """Two builds at the same school (same unitid) should trigger
        only one MCP call for institution_aura, not two."""
        call_count = {"aura": 0, "fte": 0}

        def mock_mcp_call(tool: str, args: dict):
            if tool == "get_institution_aura":
                call_count["aura"] += 1
                return {"data": {"endowment_per_fte": 10000.0}}
            raise ValueError(f"Unexpected MCP tool call: {tool}")

        class FakeServer:
            def query_iceberg_simple(self, table, *, filters, columns, limit):
                if table == "consumable.ipeds_finance_profile":
                    call_count["fte"] += 1
                    return [{"total_fte_enrollment": 20000}]
                return []

        monkeypatch.setattr(
            "app.services.mcp_client.call", mock_mcp_call
        )
        monkeypatch.setattr(
            "app.services.mcp_client.get_server", lambda: FakeServer()
        )

        # Both builds share unitid 151351 (from _make_build / _career).
        a = _make_build(school="IU-B", major="Marketing")
        builds.save_build(a)
        b = _make_build(school="IU-B", major="Finance")
        builds.save_build(b)

        comparison = builds.compare_builds([a.build_id, b.build_id])

        # Only ONE aura call and ONE FTE query despite two builds.
        assert call_count["aura"] == 1, (
            f"Expected 1 MCP call for same unitid, got {call_count['aura']}"
        )
        assert call_count["fte"] == 1, (
            f"Expected 1 FTE query for same unitid, got {call_count['fte']}"
        )

        # Both builds should still have the institution data.
        assert comparison["builds"][0]["endowment_per_fte"] == 10000.0
        assert comparison["builds"][1]["endowment_per_fte"] == 10000.0

    # --- P2: Missing institution AURA data ---

    def test_compare_builds_handles_missing_institution_aura(
        self, isolated_builds_dir, monkeypatch
    ):
        """When the MCP call and Iceberg query both fail, institution
        profile fields should be absent (merged from empty dict)."""

        def mock_mcp_call(tool: str, args: dict):
            raise RuntimeError("MCP server unavailable")

        class FakeServer:
            def query_iceberg_simple(self, table, *, filters, columns, limit):
                raise RuntimeError("Iceberg unavailable")

        monkeypatch.setattr(
            "app.services.mcp_client.call", mock_mcp_call
        )
        monkeypatch.setattr(
            "app.services.mcp_client.get_server", lambda: FakeServer()
        )

        a = _make_build(school="IU-B", major="Marketing")
        builds.save_build(a)
        b = _make_build(school="Purdue", major="Engineering")
        builds.save_build(b)

        comparison = builds.compare_builds([a.build_id, b.build_id])
        build_a = comparison["builds"][0]

        # Institution profile fields should be null or absent.
        # _fetch_institution_profiles returns {} for each unitid on
        # exception, so the ** merge adds no keys. These keys won't
        # exist in build_a.
        assert build_a.get("endowment_per_fte") is None
        assert build_a.get("marketing_ratio") is None
        assert build_a.get("athletic_spend_per_fte") is None
        assert build_a.get("fte_enrollment") is None
        assert build_a.get("coverage_tier") is None


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

    async def get_or_generate(self, soc_code: str, occupation_title: str, locale=None):
        # Eager career-description fetch joins _gemma_fanout's gather
        # (feature-career-description-on-pdf.md). Tests that rely on the
        # fan-out harness now see a 9th coroutine in started_at; raising
        # CareerDescriptionUnavailable keeps the build path otherwise
        # unchanged (career_description=None on the Build).
        from app.services.career_description import CareerDescriptionUnavailable
        self.started_at.append(("career_description", time.perf_counter()))
        await asyncio.sleep(self.per_call_sleep_s)
        raise CareerDescriptionUnavailable("test harness — no anchor")


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
    # Stub the eager career_description fetch to keep tests deterministic.
    # Patches the symbol the router uses, not the service module directly.
    from app.services import career_description as _cd_module
    monkeypatch.setattr(_cd_module, "get_or_generate", h.get_or_generate)
    # Reset the per-process cache so a prior test's success doesn't
    # short-circuit this one's stub.
    _cd_module.clear_cache()

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
        # calls + 1 career-description = 9 total.
        assert len(h.started_at) == 9, (
            f"expected 9 fan-out coroutines, saw {len(h.started_at)}: "
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


class TestSpawnEagerCareerDescription:
    """Eager career_description fetch joins _gemma_fanout's gather. The
    build pipeline must (1) attach a populated CareerDescription on
    success, (2) tolerate CareerDescriptionUnavailable without blocking
    the build, and (3) tolerate timeouts (modeled here as the same
    branch — gather with return_exceptions=True swallows both).
    """

    @staticmethod
    def _attaching_harness():
        from app.models.career import CareerDescription

        class _AttachingHarness(_FanoutHarness):
            async def get_or_generate(self, soc_code, occupation_title, locale=None):
                self.started_at.append(
                    ("career_description", time.perf_counter()),
                )
                await asyncio.sleep(self.per_call_sleep_s)
                return CareerDescription(
                    soc_code=soc_code,
                    summary="Plain-English summary of the work.",
                    tasks=[
                        "Review filings",
                        "Build models",
                        "Brief the team",
                        "Track positions",
                    ],
                    anchor_tier="activities",
                    generated_at="2026-05-07T00:00:00Z",
                    model="gemma-test",
                )

        return _AttachingHarness()

    def test_spawn_eager_career_description_attaches(
        self, isolated_builds_dir, monkeypatch,
    ):
        """Service returns a CareerDescription → Build.career_description
        is populated on the response."""
        _install_fanout_harness(monkeypatch, harness=self._attaching_harness())

        build = asyncio.run(builds_router.create_build(_build_request()))

        assert build.career_description is not None
        assert build.career_description.anchor_tier == "activities"
        assert build.career_description.summary.startswith("Plain-English")
        assert len(build.career_description.tasks) == 4

    def test_spawn_eager_failure_does_not_block_build(
        self, isolated_builds_dir, monkeypatch,
    ):
        """Service raises CareerDescriptionUnavailable → spawn still
        succeeds with career_description=None. (Default _FanoutHarness
        already raises; this is the canonical happy-failure path.)"""
        _install_fanout_harness(monkeypatch)

        build = asyncio.run(builds_router.create_build(_build_request()))

        assert isinstance(build, Build)
        assert build.career_description is None
        # The 8 non-description coroutines still produced real content.
        assert build.guidance == "async guidance"
        assert len(build.gauntlet.fights) == 5

    def test_spawn_eager_unexpected_exception_does_not_block_build(
        self, isolated_builds_dir, monkeypatch,
    ):
        """An unexpected exception (not CareerDescriptionUnavailable)
        from the service is logged but does not block the build."""

        class _ExplodingHarness(_FanoutHarness):
            async def get_or_generate(self, soc_code, occupation_title, locale=None):
                self.started_at.append(
                    ("career_description", time.perf_counter()),
                )
                await asyncio.sleep(self.per_call_sleep_s)
                raise RuntimeError("upstream went sideways")

        _install_fanout_harness(monkeypatch, harness=_ExplodingHarness())

        build = asyncio.run(builds_router.create_build(_build_request()))

        assert isinstance(build, Build)
        assert build.career_description is None


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
