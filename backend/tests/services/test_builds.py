"""Tests for build save/load/list/compare round-trip.

Uses the ``isolated_builds_dir`` fixture so the real builds directory
is never touched.
"""

from __future__ import annotations

import pytest

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
from app.services import builds


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
        path = builds.save_build(original)
        assert path.exists()

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
