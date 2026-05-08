"""Pytest fixtures for CLI service tests.

Ensures ``backend/`` is on ``sys.path`` so ``app.services.*`` imports
resolve without pytest being told to use ``rootdir=backend``. Isolates
the build directory so ``test_builds`` never writes to the real
``backend/data/builds`` store.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


@pytest.fixture(autouse=True)
def _reset_gemma_client_state():
    """Null the module-level Gemma client + semaphore before every test.

    The /build fan-out introduced a lazy module-level
    ``_semaphore`` sized from ``GEMMA_MAX_CONCURRENCY``. If a prior test
    fails after monkeypatching that env var but before its trailing
    ``reset_cache()``, later tests would inherit a size-2 (or whatever)
    semaphore and silently run under a different concurrency budget.
    This autouse fixture makes the budget deterministic test-to-test.
    """
    from app.services import gemma_client

    gemma_client.reset_cache()
    yield
    gemma_client.reset_cache()


@pytest.fixture
def isolated_builds_dir(tmp_path, monkeypatch):
    """Redirect the builds DuckDB to a tmp file for the test.

    Named ``isolated_builds_dir`` for historical compatibility; the
    backing store is a DuckDB file, not a directory. The connection
    cache is reset before and after the test so each run gets a fresh
    schema.
    """
    from app.services import db

    target = tmp_path / "builds.duckdb"
    monkeypatch.setattr(db, "_db_path", lambda: target)
    db._conns.clear()
    yield target
    db._conns.clear()


# ---------------------------------------------------------------------------
# PDF-export fixtures (feature-pdf-report-exports.md §4 Test Data Requirements)
# ---------------------------------------------------------------------------
#
# A fully-populated Build with all 5 stats, all 5 boss fights resolved
# (raw_score non-null), 6 skill_recs, and a non-empty next_steps. Plus
# sibling builders for the match-quality, null-anchor, and 3-school
# comparison fixture cases the PDF tests need.


def make_fixture_build(
    *,
    school_name: str = "Indiana University Bloomington",
    program_name: str = "Mechanical Engineering",
    major_text: str = "Mechanical Engineering",
    cipcode: str = "14.1901",
    unitid: int = 151351,
    profile_name: str = "bold otter",
    occupation_title: str = "Mechanical Engineers",
    soc_code: str = "17-2141",
    match_quality: str | None = "full",
    null_boss_id: str | None = None,
    stats_override: dict | None = None,
    earnings_1yr_p75: float | None = 92_000.0,
    debt_to_earnings_annual: float | None = 0.12,
    published_cost_4yr: float | None = 88_000.0,
    modeled_total_debt: float | None = 26_000.0,
    earnings_1yr_median: float | None = 70_000.0,
    growth_category: str | None = "Faster than average",
    burnout_drivers: list | None = None,
    adoption_percentile: float | None = 0.42,
    home_state: str = "IN",
):
    """Construct a fully-populated Build for PDF tests.

    See backend/tests/services/conftest.py docstring above for the contract.
    """
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

    stats_kwargs = {"ern": 8, "roi": 7, "res": 6, "grw": 7, "aura": 6}
    if stats_override:
        stats_kwargs.update(stats_override)

    if burnout_drivers is None:
        burnout_drivers = [
            {"label": "long irregular hours during product launch cycles"},
            {"label": "shifting deadlines"},
        ]

    career = CareerOutcome(
        unitid=unitid,
        institution_name=school_name,
        cipcode=cipcode,
        program_name=program_name,
        soc_code=soc_code,
        occupation_title=occupation_title,
        soc_major_group_name="Architecture and Engineering Occupations",
        median_annual_wage=82_000.0,
        earnings_1yr_median=earnings_1yr_median,
        earnings_1yr_p25=58_000.0,
        earnings_1yr_p75=earnings_1yr_p75,
        debt_median=24_000.0,
        debt_to_earnings_annual=debt_to_earnings_annual,
        education_level_name="Bachelor's degree",
        growth_category=growth_category,
        net_price_annual=14_000.0,
        cost_of_attendance_annual=22_000.0,
        published_cost_4yr=published_cost_4yr,
        modeled_total_debt=modeled_total_debt,
        institution_control="Public",
        roi_cost_basis="cost_of_attendance",
        financed_dte=0.10,
        is_out_of_state=False,
        stats=PentagonStats(**stats_kwargs),
        bosses=BossScores(ai=12, loans=7, market=6, burnout=7, ceiling=7),
        raw_stat_res=6,
        raw_stat_hmn=6,
        adoption_percentile=adoption_percentile,
        burnout_drivers=burnout_drivers,
        match_quality=match_quality,
    )

    # Build deterministic gauntlet — all 5 bosses with raw_scores above the
    # win threshold by default; null_boss_id flips one to raw_score=None
    # for the Insufficient-chip path.
    fight_specs = [
        ("ai", "AI displacement", 16, 14, 10),
        ("loans", "Debt burden", 8, 7, 5),
        ("market", "Job market", 7, 6, 4),
        ("burnout", "Burnout", 8, 7, 5),
        ("ceiling", "Earnings ceiling", 8, 7, 5),
    ]
    fights = []
    for boss, label, score, win, draw in fight_specs:
        raw = None if boss == null_boss_id else score
        result = "win" if raw is not None and raw >= win else "unknown"
        fights.append(BossFightResult(
            boss=boss,  # type: ignore[arg-type]
            label=label,
            result=result,  # type: ignore[arg-type]
            raw_score=raw,
            threshold_win=win,
            threshold_draw=draw,
            reason="fixture",
        ))
    wins = sum(1 for f in fights if f.result == "win")
    unknowns = sum(1 for f in fights if f.result == "unknown")
    gauntlet = GauntletResult(
        fights=fights,
        wins=wins,
        losses=0,
        draws=0,
        unknown=unknowns,
        verdict="SOLID" if wins >= 4 else "OK",
    )

    branches = [
        CareerBranch(
            from_soc=soc_code,
            to_soc="17-2199",
            to_title="Mechanical Engineering Technologist",
            delta_ern=1,
            delta_roi=0,
            delta_res=0,
            delta_grw=0,
        )
    ]

    skill_recs = [
        SkillRec(
            title=f"Skill {i}",
            stat_impact="Boosts ERN",
            rationale=f"Counselor question {i}?",
        )
        for i in range(6)
    ]

    skill_pool = [
        AppliedSkill(id=f"sk_{i}", title=f"Skill {i}", rationale="r")
        for i in range(3)
    ]

    return Build(
        build_id=f"fp-fixture-{cipcode.replace('.', '')}-{unitid}",
        created_at="2026-05-06T00:00:00+00:00",
        school_name=school_name,
        unitid=unitid,
        major_text=major_text,
        cipcode=cipcode,
        program_name=program_name,
        effort="balanced",
        loan_pct=0.5,
        career=career,
        gauntlet=gauntlet,
        branches=branches,
        skill_recs=skill_recs,
        skills_crafted=[],
        skill_pool=skill_pool,
        guidance="",
        next_steps="Talk to your counselor about a co-op slot.",
        profile_name=profile_name,
        animal_emoji="🦦",
        home_state=home_state,
    )


@pytest.fixture
def fixture_build():
    """Default fully-populated Build for PDF tests."""
    return make_fixture_build()


@pytest.fixture
def fixture_build_scorecard_only():
    """Build whose CareerOutcome.match_quality == 'scorecard_only'."""
    return make_fixture_build(match_quality="scorecard_only")


@pytest.fixture
def fixture_build_partial_no_onet():
    """Build whose CareerOutcome.match_quality == 'partial_no_onet'."""
    return make_fixture_build(match_quality="partial_no_onet")


@pytest.fixture
def fixture_build_null_ai_score():
    """Build with raw_score=None for the AI boss — exercises the
    'Insufficient' chip path in the page-1 risk profile (§3.4).
    """
    return make_fixture_build(null_boss_id="ai")


@pytest.fixture
def fixture_three_same_major_builds():
    """Three builds in the 14.19 CIP family (different sub-CIPs, same
    4-digit family). Used by the comparison PDF same-major-positive case.
    """
    return [
        make_fixture_build(
            school_name="Purdue University",
            cipcode="14.1901",
            unitid=243780,
            profile_name="brave fox",
        ),
        make_fixture_build(
            school_name="Indiana University",
            cipcode="14.1902",
            unitid=151351,
            profile_name="bold otter",
        ),
        make_fixture_build(
            school_name="Rose-Hulman Institute of Technology",
            cipcode="14.1903",
            unitid=152426,
            profile_name="kind raven",
        ),
    ]
