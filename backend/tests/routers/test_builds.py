"""Tests for the streaming build endpoint POST /build/stream.

Covers:
  P0: skeleton-first emission, done-last emission, concurrent data queries
  P1: Gemma failure fallback, save-after-done ordering
  P2: error event on invalid SOC

All services below the router (stat_engine, branch_tree, boss_fights,
skill_recs, skill_pool, guidance, builds, state) are fully mocked.
No network, no DuckDB, no Gemma.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app import state
from app.main import create_app
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
from app.services import (
    boss_fights,
    branch_tree,
    builds,
    guidance,
    skill_pool,
    skill_recs,
    stat_engine,
)

# ---------------------------------------------------------------------------
# Fixtures — deterministic career / gauntlet / branches
# ---------------------------------------------------------------------------


def _career() -> CareerOutcome:
    return CareerOutcome(
        unitid=151351,
        institution_name="Indiana University-Bloomington",
        cipcode="52.14",
        program_name="Marketing",
        soc_code="13-1161",
        occupation_title="Market Research Analysts",
        stats=PentagonStats(ern=7, roi=8, res=5, grw=6, aura=7),
        bosses=BossScores(ai=6, loans=8, market=7, burnout=5, ceiling=4),
        median_annual_wage=68230.0,
    )


def _gauntlet() -> GauntletResult:
    return GauntletResult(
        fights=[
            BossFightResult(
                boss="ai",
                label="Fight AI",
                result="win",
                raw_score=16,
                threshold_win=14,
                threshold_draw=10,
                reason="Strong AI resilience",
            ),
            BossFightResult(
                boss="loans",
                label="Pay Your Loans",
                result="draw",
                raw_score=11,
                threshold_win=14,
                threshold_draw=10,
                reason="Moderate debt load",
            ),
            BossFightResult(
                boss="market",
                label="Beat the Market",
                result="win",
                raw_score=15,
                threshold_win=14,
                threshold_draw=10,
                reason="Strong growth",
            ),
            BossFightResult(
                boss="burnout",
                label="Avoid Burnout",
                result="lose",
                raw_score=5,
                threshold_win=14,
                threshold_draw=10,
                reason="High burnout risk",
            ),
            BossFightResult(
                boss="ceiling",
                label="Break the Ceiling",
                result="win",
                raw_score=16,
                threshold_win=14,
                threshold_draw=10,
                reason="High ceiling",
            ),
        ],
        wins=3,
        losses=1,
        draws=1,
        unknown=0,
        verdict="SOLID",
    )


def _branches() -> list[CareerBranch]:
    return [
        CareerBranch(
            from_soc="13-1161",
            to_soc="11-2021",
            to_title="Marketing Managers",
            delta_ern=2,
            delta_grw=1,
        ),
    ]


def _build_request_body() -> dict[str, Any]:
    return {
        "profile_name": "bold bear",
        "school_name": "Indiana University-Bloomington",
        "unitid": 151351,
        "cipcode": "52.14",
        "cip_title": "Marketing",
        "major_text": "Marketing",
        "effort": "balanced",
        "loan_pct": 1.0,
        "selected_soc": "13-1161",
        "selected_title": "Market Research Analysts",
        "student_major": None,
        "student_cip": None,
        "home_state": None,
        "school_state": None,
        "animal_emoji": "\U0001f43b",
        "locale": "en",
    }


# ---------------------------------------------------------------------------
# Helpers — parse SSE frames from response body text
# ---------------------------------------------------------------------------


def _parse_sse_events(body: str) -> list[tuple[str, Any]]:
    """Parse SSE frames from raw response text.

    Returns a list of (event_type, parsed_json_data) tuples.
    """
    events = []
    for frame in body.strip().split("\n\n"):
        frame = frame.strip()
        if not frame:
            continue
        event_match = re.search(r"^event:\s*(.+)$", frame, re.MULTILINE)
        data_match = re.search(r"^data:\s*(.+)$", frame, re.MULTILINE)
        if event_match and data_match:
            event_type = event_match.group(1).strip()
            data = json.loads(data_match.group(1))
            events.append((event_type, data))
    return events


# ---------------------------------------------------------------------------
# Shared mock wiring
# ---------------------------------------------------------------------------


@pytest.fixture
def stream_client(isolated_builds_db, monkeypatch):
    """TestClient with all services mocked for the streaming endpoint.

    Mocks:
    - stat_engine.compute_one -> returns _career()
    - branch_tree.get_branches -> returns _branches()
    - boss_fights.score_gauntlet -> returns _gauntlet()
    - boss_fights.narrate_one -> returns per-boss narrative
    - skill_recs.generate_recs_async -> returns one SkillRec
    - skill_pool.generate_pool_async -> returns one AppliedSkill
    - guidance.generate_guidance_async -> returns guidance text
    - state.store_build -> no-op (captured by spy)
    - builds.save_build -> no-op (captured by spy)
    """
    career = _career()
    gauntlet = _gauntlet()

    monkeypatch.setattr(stat_engine, "compute_one", lambda **kw: career)
    monkeypatch.setattr(branch_tree, "get_branches", lambda *a, **kw: _branches())
    monkeypatch.setattr(boss_fights, "score_gauntlet", lambda c: gauntlet)

    async def _mock_narrate(career_obj, fight, locale="en"):
        return f"Narrative for {fight.boss}."

    monkeypatch.setattr(boss_fights, "narrate_one", _mock_narrate)
    monkeypatch.setattr(
        boss_fights,
        "_fallback_narrative",
        lambda fight, locale="en": f"Fallback for {fight.boss}.",
    )

    async def _mock_recs(career_obj, gauntlet_obj, locale="en"):
        return [
            SkillRec(
                title="Data Analytics Minor",
                stat_impact="RES+2",
                rationale="Learn to direct AI tools.",
            ),
        ]

    monkeypatch.setattr(skill_recs, "generate_recs_async", _mock_recs)
    monkeypatch.setattr(
        skill_recs,
        "_fallback_recs",
        lambda c: [
            SkillRec(
                title="Fallback Rec",
                stat_impact="ERN+1",
                rationale="Fallback.",
            ),
        ],
    )

    async def _mock_pool(career_obj, gauntlet_obj, locale="en"):
        return [
            AppliedSkill(
                id="test_skill_1",
                title="Test Skill",
                rationale="A test.",
                targets=["ai"],
                delta_res=1,
            ),
        ]

    monkeypatch.setattr(skill_pool, "generate_pool_async", _mock_pool)

    async def _mock_guidance(career_obj, gauntlet_obj, branches_list, locale="en"):
        return "Your guidance narrative here."

    monkeypatch.setattr(guidance, "generate_guidance_async", _mock_guidance)
    monkeypatch.setattr(
        guidance,
        "_fallback_narrative",
        lambda c, g, locale="en": "Fallback guidance.",
    )

    store_spy = MagicMock(side_effect=state.store_build)
    monkeypatch.setattr(state, "store_build", store_spy)

    save_spy = MagicMock()
    monkeypatch.setattr(builds, "save_build", save_spy)

    client = TestClient(create_app())
    client._store_spy = store_spy  # type: ignore[attr-defined]
    client._save_spy = save_spy  # type: ignore[attr-defined]
    return client


# ===========================================================================
# P0: test_stream_build_emits_skeleton_first
# ===========================================================================


class TestStreamBuildEmitsSkeletonFirst:
    """SSE stream starts with a 'skeleton' event containing valid Build JSON
    with empty Gemma fields (skill_recs=[], skill_pool=[], guidance='',
    and fight narratives all empty strings)."""

    def test_first_event_is_skeleton(self, stream_client):
        response = stream_client.post(
            "/build/stream",
            json=_build_request_body(),
        )
        assert response.status_code == 200
        events = _parse_sse_events(response.text)
        assert len(events) >= 2, f"Expected at least 2 events, got {len(events)}"

        first_event_type, first_data = events[0]
        assert first_event_type == "skeleton"

    def test_skeleton_contains_valid_build_json(self, stream_client):
        response = stream_client.post(
            "/build/stream",
            json=_build_request_body(),
        )
        events = _parse_sse_events(response.text)
        _, skeleton_data = events[0]

        # Must be a valid Build shape
        build = Build.model_validate(skeleton_data)
        assert build.school_name == "Indiana University-Bloomington"
        assert build.career.soc_code == "13-1161"
        assert build.career.occupation_title == "Market Research Analysts"

    def test_skeleton_has_empty_gemma_fields(self, stream_client):
        response = stream_client.post(
            "/build/stream",
            json=_build_request_body(),
        )
        events = _parse_sse_events(response.text)
        _, skeleton_data = events[0]
        build = Build.model_validate(skeleton_data)

        # Gemma fields must be empty in the skeleton
        assert build.skill_recs == []
        assert build.skill_pool == []
        assert build.guidance == ""
        for fight in build.gauntlet.fights:
            assert fight.narrative == "", (
                f"Fight {fight.boss} narrative should be empty in skeleton, "
                f"got: {fight.narrative!r}"
            )

    def test_skeleton_has_populated_non_gemma_fields(self, stream_client):
        """The skeleton carries stats, gauntlet scores, and branches even
        though Gemma fields are empty. This is the data the frontend renders
        immediately in Phase 1."""
        response = stream_client.post(
            "/build/stream",
            json=_build_request_body(),
        )
        events = _parse_sse_events(response.text)
        _, skeleton_data = events[0]
        build = Build.model_validate(skeleton_data)

        # Pentagon stats must be populated
        assert build.career.stats.ern is not None
        assert build.career.stats.roi is not None

        # Gauntlet fights must have scores (not narratives)
        assert len(build.gauntlet.fights) == 5
        for fight in build.gauntlet.fights:
            assert fight.result in ("win", "lose", "draw", "unknown")
            assert fight.raw_score is not None

        # Branches must be populated
        assert len(build.branches) >= 1


# ===========================================================================
# P0: test_stream_build_emits_done_last
# ===========================================================================


class TestStreamBuildEmitsDoneLast:
    """'done' event fires after all other events and contains 'build_id'."""

    def test_done_is_last_event(self, stream_client):
        response = stream_client.post(
            "/build/stream",
            json=_build_request_body(),
        )
        events = _parse_sse_events(response.text)
        assert len(events) >= 2

        last_event_type, last_data = events[-1]
        assert last_event_type == "done"

    def test_done_contains_build_id(self, stream_client):
        response = stream_client.post(
            "/build/stream",
            json=_build_request_body(),
        )
        events = _parse_sse_events(response.text)
        _, done_data = events[-1]

        assert "build_id" in done_data
        assert isinstance(done_data["build_id"], str)
        assert len(done_data["build_id"]) > 0

    def test_skeleton_before_done(self, stream_client):
        """Skeleton must appear before done. This covers the ordering
        contract that the frontend depends on for navigation."""
        response = stream_client.post(
            "/build/stream",
            json=_build_request_body(),
        )
        events = _parse_sse_events(response.text)
        event_types = [e[0] for e in events]

        assert event_types[0] == "skeleton"
        assert event_types[-1] == "done"

    def test_all_expected_event_types_present(self, stream_client):
        """The full stream must include skeleton, boss narratives,
        skill_recs, skill_pool, guidance, and done."""
        response = stream_client.post(
            "/build/stream",
            json=_build_request_body(),
        )
        events = _parse_sse_events(response.text)
        event_types = [e[0] for e in events]

        assert "skeleton" in event_types
        assert "done" in event_types
        assert "boss_narrative" in event_types
        assert "skill_recs" in event_types
        assert "skill_pool" in event_types
        assert "guidance" in event_types

    def test_five_boss_narrative_events(self, stream_client):
        """One boss_narrative event per fight in the gauntlet (5 total)."""
        response = stream_client.post(
            "/build/stream",
            json=_build_request_body(),
        )
        events = _parse_sse_events(response.text)
        boss_events = [e for e in events if e[0] == "boss_narrative"]
        assert len(boss_events) == 5

        emitted_bosses = {e[1]["boss_id"] for e in boss_events}
        assert emitted_bosses == {"ai", "loans", "market", "burnout", "ceiling"}


# ===========================================================================
# P0: test_stream_build_parallel_data_queries
# ===========================================================================


class TestStreamBuildParallelDataQueries:
    """compute_one and get_branches are called concurrently via
    asyncio.gather, not sequentially."""

    def test_concurrent_execution(self, isolated_builds_db, monkeypatch):
        """If compute_one and get_branches run sequentially, total time
        is >= 2 * delay. If concurrent, total time is ~1 * delay.

        We add a 0.3s sleep to each mock and assert the total wall time
        is well under 2 * 0.3s = 0.6s.
        """
        delay = 0.3
        call_log: list[tuple[str, float]] = []

        def _slow_compute_one(**kw):
            call_log.append(("compute_one", time.monotonic()))
            time.sleep(delay)
            return _career()

        def _slow_get_branches(*a, **kw):
            call_log.append(("get_branches", time.monotonic()))
            time.sleep(delay)
            return _branches()

        monkeypatch.setattr(stat_engine, "compute_one", _slow_compute_one)
        monkeypatch.setattr(branch_tree, "get_branches", _slow_get_branches)
        monkeypatch.setattr(boss_fights, "score_gauntlet", lambda c: _gauntlet())

        async def _mock_narrate(career_obj, fight, locale="en"):
            return f"Narrative for {fight.boss}."

        monkeypatch.setattr(boss_fights, "narrate_one", _mock_narrate)
        monkeypatch.setattr(
            boss_fights, "_fallback_narrative",
            lambda fight, locale="en": f"Fallback for {fight.boss}.",
        )

        async def _mock_recs(c, g, locale="en"):
            return []

        monkeypatch.setattr(skill_recs, "generate_recs_async", _mock_recs)
        monkeypatch.setattr(skill_recs, "_fallback_recs", lambda c: [])

        async def _mock_pool(c, g, locale="en"):
            return []

        monkeypatch.setattr(skill_pool, "generate_pool_async", _mock_pool)

        async def _mock_guidance(c, g, b, locale="en"):
            return ""

        monkeypatch.setattr(guidance, "generate_guidance_async", _mock_guidance)
        monkeypatch.setattr(
            guidance, "_fallback_narrative", lambda c, g, locale="en": "",
        )
        monkeypatch.setattr(state, "store_build", lambda b: b.build_id)
        monkeypatch.setattr(builds, "save_build", lambda b: None)

        client = TestClient(create_app())

        start = time.monotonic()
        response = client.post("/build/stream", json=_build_request_body())
        elapsed = time.monotonic() - start

        assert response.status_code == 200

        # Both must have been called
        called_fns = [name for name, _ in call_log]
        assert "compute_one" in called_fns
        assert "get_branches" in called_fns

        # If run concurrently, elapsed should be ~0.3s (plus overhead),
        # not ~0.6s+. Allow generous headroom but reject sequential timing.
        assert elapsed < delay * 1.8, (
            f"Expected concurrent execution (~{delay}s), "
            f"but took {elapsed:.2f}s (sequential would be ~{delay * 2}s)"
        )


# ===========================================================================
# P1: test_stream_build_gemma_failure_fallback
# ===========================================================================


class TestStreamBuildGemmaFailureFallback:
    """When a Gemma call raises, fallback text is emitted — not an error
    event. The stream must complete with a 'done' event."""

    def test_narrate_one_failure_emits_fallback_narrative(
        self, isolated_builds_db, monkeypatch,
    ):
        """If narrate_one raises for all 5 bosses, each boss_narrative
        event should contain the fallback text, and no error event
        should appear."""
        monkeypatch.setattr(stat_engine, "compute_one", lambda **kw: _career())
        monkeypatch.setattr(branch_tree, "get_branches", lambda *a, **kw: _branches())
        monkeypatch.setattr(boss_fights, "score_gauntlet", lambda c: _gauntlet())

        async def _failing_narrate(career_obj, fight, locale="en"):
            raise RuntimeError("Gemma is down")

        monkeypatch.setattr(boss_fights, "narrate_one", _failing_narrate)
        # The fallback must produce non-empty text
        monkeypatch.setattr(
            boss_fights, "_fallback_narrative",
            lambda fight, locale="en": f"Fallback for {fight.boss}.",
        )

        async def _mock_recs(c, g, locale="en"):
            return [
                SkillRec(title="R", stat_impact="ERN+1", rationale="R"),
            ]

        monkeypatch.setattr(skill_recs, "generate_recs_async", _mock_recs)
        monkeypatch.setattr(
            skill_recs, "_fallback_recs",
            lambda c: [SkillRec(title="FR", stat_impact="ERN+1", rationale="FR")],
        )

        async def _mock_pool(c, g, locale="en"):
            return []

        monkeypatch.setattr(skill_pool, "generate_pool_async", _mock_pool)

        async def _mock_guidance(c, g, b, locale="en"):
            return "Guidance."

        monkeypatch.setattr(guidance, "generate_guidance_async", _mock_guidance)
        monkeypatch.setattr(
            guidance, "_fallback_narrative", lambda c, g, locale="en": "FG",
        )
        monkeypatch.setattr(state, "store_build", lambda b: b.build_id)
        monkeypatch.setattr(builds, "save_build", lambda b: None)

        client = TestClient(create_app())
        response = client.post("/build/stream", json=_build_request_body())
        assert response.status_code == 200

        events = _parse_sse_events(response.text)
        event_types = [e[0] for e in events]

        # No error events
        assert "error" not in event_types, (
            "Gemma failure must NOT produce an error event — fallback should be used"
        )

        # Done must still fire
        assert event_types[-1] == "done"

        # Each boss narrative must be the fallback text
        boss_events = [e for e in events if e[0] == "boss_narrative"]
        assert len(boss_events) == 5
        for _, data in boss_events:
            assert data["narrative"].startswith("Fallback for "), (
                f"Expected fallback narrative, got: {data['narrative']!r}"
            )

    def test_all_gemma_calls_fail_still_completes(
        self, isolated_builds_db, monkeypatch,
    ):
        """Even when ALL Gemma-dependent calls fail (narrate_one,
        generate_recs_async, generate_pool_async, generate_guidance_async),
        the stream completes with fallbacks and a done event."""
        monkeypatch.setattr(stat_engine, "compute_one", lambda **kw: _career())
        monkeypatch.setattr(branch_tree, "get_branches", lambda *a, **kw: _branches())
        monkeypatch.setattr(boss_fights, "score_gauntlet", lambda c: _gauntlet())

        async def _fail(*, msg="down"):
            raise RuntimeError(msg)

        async def _failing_narrate(c, fight, locale="en"):
            raise RuntimeError("narrate down")

        async def _failing_recs(c, g, locale="en"):
            raise RuntimeError("recs down")

        async def _failing_pool(c, g, locale="en"):
            raise RuntimeError("pool down")

        async def _failing_guidance(c, g, b, locale="en"):
            raise RuntimeError("guidance down")

        monkeypatch.setattr(boss_fights, "narrate_one", _failing_narrate)
        monkeypatch.setattr(
            boss_fights, "_fallback_narrative",
            lambda fight, locale="en": "FB narrative",
        )
        monkeypatch.setattr(skill_recs, "generate_recs_async", _failing_recs)
        monkeypatch.setattr(
            skill_recs, "_fallback_recs",
            lambda c: [SkillRec(title="FR", stat_impact="ERN+1", rationale="FR")],
        )
        monkeypatch.setattr(skill_pool, "generate_pool_async", _failing_pool)
        monkeypatch.setattr(guidance, "generate_guidance_async", _failing_guidance)
        monkeypatch.setattr(
            guidance, "_fallback_narrative",
            lambda c, g, locale="en": "FB guidance",
        )
        monkeypatch.setattr(state, "store_build", lambda b: b.build_id)
        monkeypatch.setattr(builds, "save_build", lambda b: None)

        client = TestClient(create_app())
        response = client.post("/build/stream", json=_build_request_body())
        assert response.status_code == 200

        events = _parse_sse_events(response.text)
        event_types = [e[0] for e in events]

        assert "error" not in event_types
        assert event_types[0] == "skeleton"
        assert event_types[-1] == "done"

        # Guidance fallback should be emitted
        guidance_events = [e for e in events if e[0] == "guidance"]
        assert len(guidance_events) == 1
        assert guidance_events[0][1]["narrative"] == "FB guidance"

        # skill_recs fallback: the _recs() inner function catches the exception
        # and uses _fallback_recs, so skill_recs event should carry fallback data
        recs_events = [e for e in events if e[0] == "skill_recs"]
        assert len(recs_events) == 1

        # skill_pool fallback: empty list when pool generation fails
        pool_events = [e for e in events if e[0] == "skill_pool"]
        assert len(pool_events) == 1
        assert pool_events[0][1] == []


# ===========================================================================
# P1: test_stream_build_saves_after_done
# ===========================================================================


class TestStreamBuildSavesAfterDone:
    """Build is persisted to disk (state.store_build + builds.save_build)
    only after all events complete — i.e. the save happens before the done
    event is yielded but after all Gemma results are collected."""

    def test_save_called_once(self, stream_client):
        response = stream_client.post(
            "/build/stream",
            json=_build_request_body(),
        )
        assert response.status_code == 200

        save_spy = stream_client._save_spy  # type: ignore[attr-defined]
        store_spy = stream_client._store_spy  # type: ignore[attr-defined]

        # Both must be called exactly once
        assert save_spy.call_count == 1, (
            "builds.save_build should be called once, "
            f"was called {save_spy.call_count} times"
        )
        assert store_spy.call_count == 1, (
            "state.store_build should be called once, "
            f"was called {store_spy.call_count} times"
        )

    def test_saved_build_contains_gemma_results(self, stream_client):
        """The build passed to save_build must have Gemma results patched in,
        not the empty skeleton."""
        response = stream_client.post(
            "/build/stream",
            json=_build_request_body(),
        )
        assert response.status_code == 200

        save_spy = stream_client._save_spy  # type: ignore[attr-defined]
        saved_build: Build = save_spy.call_args[0][0]

        # skill_recs should not be empty (mock returns 1)
        assert len(saved_build.skill_recs) >= 1
        assert saved_build.skill_recs[0].title == "Data Analytics Minor"

        # skill_pool should not be empty (mock returns 1)
        assert len(saved_build.skill_pool) >= 1
        assert saved_build.skill_pool[0].id == "test_skill_1"

        # guidance should not be empty
        assert saved_build.guidance == "Your guidance narrative here."

    def test_saved_build_id_matches_done_event(self, stream_client):
        """The build_id in the done event must match the build_id that was
        saved. This is the contract that allows the frontend to look up the
        persisted build after streaming completes."""
        response = stream_client.post(
            "/build/stream",
            json=_build_request_body(),
        )
        assert response.status_code == 200

        events = _parse_sse_events(response.text)
        done_data = next(d for t, d in events if t == "done")
        done_build_id = done_data["build_id"]

        save_spy = stream_client._save_spy  # type: ignore[attr-defined]
        saved_build: Build = save_spy.call_args[0][0]

        assert saved_build.build_id == done_build_id, (
            f"Done event build_id {done_build_id!r} does not match "
            f"saved build_id {saved_build.build_id!r}"
        )

    def test_skeleton_build_id_matches_done_event(self, stream_client):
        """Architect review identified a potential double-ID bug. The
        implementation uses model_copy, so skeleton and done should share
        the same build_id."""
        response = stream_client.post(
            "/build/stream",
            json=_build_request_body(),
        )
        assert response.status_code == 200

        events = _parse_sse_events(response.text)
        skeleton_data = next(d for t, d in events if t == "skeleton")
        done_data = next(d for t, d in events if t == "done")

        assert skeleton_data["build_id"] == done_data["build_id"], (
            f"Skeleton build_id {skeleton_data['build_id']!r} does not match "
            f"done build_id {done_data['build_id']!r} — possible double-ID bug"
        )


# ===========================================================================
# P2: test_stream_build_error_on_invalid_soc
# ===========================================================================


class TestStreamBuildErrorOnInvalidSoc:
    """When compute_one raises for a bad SOC code, the stream emits an
    'error' event (not an HTTP 422) and terminates."""

    def test_value_error_emits_error_event(
        self, isolated_builds_db, monkeypatch,
    ):
        """ValueError from compute_one (no data for this school/program)
        produces an error SSE event."""

        def _raise_value_error(**kw):
            raise ValueError("No outcomes found for unitid=999999 cipcode=99.99")

        monkeypatch.setattr(stat_engine, "compute_one", _raise_value_error)
        monkeypatch.setattr(branch_tree, "get_branches", lambda *a, **kw: [])
        monkeypatch.setattr(state, "store_build", lambda b: b.build_id)
        monkeypatch.setattr(builds, "save_build", lambda b: None)

        client = TestClient(create_app())
        body = _build_request_body()
        body["selected_soc"] = "99-9999"

        response = client.post("/build/stream", json=body)
        # SSE endpoint returns 200 for the stream, error is in-band
        assert response.status_code == 200

        events = _parse_sse_events(response.text)
        assert len(events) >= 1

        event_type, data = events[0]
        assert event_type == "error"
        assert "detail" in data
        assert "No outcomes found" in data["detail"]

        # No done event — stream terminates after error
        event_types = [e[0] for e in events]
        assert "done" not in event_types
        assert "skeleton" not in event_types

    def test_lookup_error_emits_error_event(
        self, isolated_builds_db, monkeypatch,
    ):
        """LookupError from compute_one (SOC not among results)
        produces an error SSE event with user-friendly message."""

        def _raise_lookup(**kw):
            raise LookupError("SOC 99-9999 not found")

        monkeypatch.setattr(stat_engine, "compute_one", _raise_lookup)
        monkeypatch.setattr(branch_tree, "get_branches", lambda *a, **kw: [])
        monkeypatch.setattr(state, "store_build", lambda b: b.build_id)
        monkeypatch.setattr(builds, "save_build", lambda b: None)

        client = TestClient(create_app())
        body = _build_request_body()
        body["selected_soc"] = "99-9999"

        response = client.post("/build/stream", json=body)
        assert response.status_code == 200

        events = _parse_sse_events(response.text)
        assert len(events) >= 1

        event_type, data = events[0]
        assert event_type == "error"
        assert "detail" in data
        # Should be the user-friendly message, not the raw exception
        assert "enough data" in data["detail"].lower()

        # No done or skeleton events
        event_types = [e[0] for e in events]
        assert "done" not in event_types


# ===========================================================================
# P0 bonus: existing POST /build endpoint still works (no regression)
# ===========================================================================


class TestExistingBuildEndpointNotBroken:
    """The non-streaming POST /build endpoint must continue to work after
    the streaming endpoint was added."""

    def test_blocking_build_still_works(self, stream_client):
        response = stream_client.post(
            "/build",
            json=_build_request_body(),
        )
        assert response.status_code == 200
        body = response.json()
        assert "build_id" in body
        assert body["school_name"] == "Indiana University-Bloomington"
        assert body["career"]["soc_code"] == "13-1161"
