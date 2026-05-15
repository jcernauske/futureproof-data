"""Tests for the collection-level builds router (no-prefix).

Covers:
  GET  /builds?profile_name=X  → filters list_builds by profile, returns
                                 {builds: [BuildSummary, ...]} JSON.
  POST /builds/compare         → 200 with {builds, stats, bosses} on hit;
                                 404 when any build_id is unknown.

A fresh FastAPI app per test backed by an isolated DuckDB via the
`isolated_builds_db` fixture.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models.career import (
    BossFightResult,
    BossScores,
    Build,
    CareerOutcome,
    GauntletResult,
    PentagonStats,
)
from app.services import builds as builds_service

# --- Helpers ---------------------------------------------------------------


def _make_build(
    *,
    profile_name: str,
    school_name: str,
    major_text: str,
    soc: str = "13-2051",
    title: str = "Financial Analyst",
) -> Build:
    """Construct + persist a build, return the Build instance.

    Uses the builds service's own builder so the build_id is generated
    consistently (matches the slug rules the production code relies on).
    """
    career = CareerOutcome(
        unitid=151351,
        institution_name=school_name,
        cipcode="52.14",
        program_name=major_text,
        soc_code=soc,
        occupation_title=title,
        stats=PentagonStats(ern=8, roi=9, res=4, grw=6, aura=6),
        bosses=BossScores(ai=7, loans=None, market=7, burnout=6, ceiling=None),
        median_annual_wage=66490.0,
    )
    gauntlet = GauntletResult(
        fights=[
            BossFightResult(
                boss="ai",  # type: ignore[arg-type]
                label="Fight AI",
                result="win",  # type: ignore[arg-type]
                raw_score=16,
                threshold_win=14,
                threshold_draw=10,
                reason="r",
            ),
            BossFightResult(
                boss="loans",  # type: ignore[arg-type]
                label="Pay your loans",
                result="lose",  # type: ignore[arg-type]
                raw_score=4,
                threshold_win=14,
                threshold_draw=10,
                reason="r",
            ),
        ],
        wins=1,
        losses=1,
        draws=0,
        unknown=0,
        verdict="MIXED",
    )
    build = builds_service.build_from_parts(
        school_name=school_name,
        unitid=151351,
        major_text=major_text,
        cipcode="52.14",
        program_name=major_text,
        effort="balanced",
        career=career,
        gauntlet=gauntlet,
        branches=[],
        skill_recs=[],
        guidance="",
        profile_name=profile_name,
    )
    builds_service.save_build(build)
    return build


@pytest.fixture
def client(isolated_builds_db) -> TestClient:
    """Fresh FastAPI app + TestClient against the isolated DuckDB."""
    return TestClient(create_app())


# --- GET /builds -----------------------------------------------------------


class TestListBuildsRouter:
    def test_returns_empty_list_when_no_builds(self, client):
        resp = client.get("/builds")
        assert resp.status_code == 200
        assert resp.json() == {"builds": []}

    def test_returns_all_builds_when_no_profile_filter(self, client):
        _make_build(profile_name="bold bear", school_name="IU", major_text="Marketing")
        _make_build(profile_name="wandering otter", school_name="UCB", major_text="CS")

        resp = client.get("/builds")
        assert resp.status_code == 200
        body = resp.json()
        assert "builds" in body
        assert len(body["builds"]) == 2

    def test_profile_name_filter_passes_through_to_service(self, client):
        """The query param must reach `builds.list_builds(profile_name=...)`
        unchanged — same-named profiles only, no casing normalization."""
        _make_build(
            profile_name="bold bear", school_name="IU", major_text="Marketing"
        )
        _make_build(
            profile_name="wandering otter", school_name="UCB", major_text="CS"
        )

        resp = client.get("/builds?profile_name=bold%20bear")
        assert resp.status_code == 200
        builds = resp.json()["builds"]
        assert len(builds) == 1
        assert builds[0]["profile_name"] == "bold bear"
        assert builds[0]["school_name"] == "IU"

    def test_profile_name_filter_with_no_matches_returns_empty(self, client):
        _make_build(
            profile_name="bold bear", school_name="IU", major_text="Marketing"
        )

        resp = client.get("/builds?profile_name=nobody")
        assert resp.status_code == 200
        assert resp.json() == {"builds": []}

    def test_each_build_dict_has_summary_fields(self, client):
        """Saboteur: schema drift in BuildSummary breaks the frontend.

        Lock down the keys the MenuScreen expects (the contract surface).
        """
        _make_build(
            profile_name="bold bear", school_name="IU", major_text="Marketing"
        )
        body = client.get("/builds").json()
        first = body["builds"][0]
        for key in (
            "build_id",
            "profile_name",
            "created_at",
            "school_name",
            "major_text",
            "career_title",
            "ern",
            "roi",
            "res",
            "grw",
            "aura",
            "wins",
            "losses",
            "draws",
            "parent_build_id",
            "effort",
            "loan_pct",
        ):
            assert key in first, f"BuildSummary missing required field {key!r}"


# --- POST /builds/compare --------------------------------------------------


class TestCompareBuildsRouter:
    def test_returns_compare_payload_for_two_builds(self, client):
        b1 = _make_build(
            profile_name="bold bear", school_name="IU", major_text="Marketing"
        )
        b2 = _make_build(
            profile_name="bold bear",
            school_name="UCB",
            major_text="CS",
            soc="15-1252",
            title="Software Developers",
        )

        resp = client.post(
            "/builds/compare",
            json={"build_ids": [b1.build_id, b2.build_id]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "builds" in body
        assert "stats" in body
        assert "bosses" in body
        assert len(body["builds"]) == 2
        # Stats must contain all 5 axes; each row must hold one value per build.
        labels = {row["label"] for row in body["stats"]}
        assert labels == {"ERN", "ROI", "RES", "GRW", "AURA"}
        for row in body["stats"]:
            assert len(row["values"]) == 2
        # Bosses must include the canonical 5; per-build values present.
        boss_labels = {row["label"] for row in body["bosses"]}
        assert boss_labels == {"AI", "Loans", "Market", "Burnout", "Ceiling"}

    def test_returns_404_when_any_build_id_is_unknown(self, client):
        """Saboteur: a stale build_id from the frontend must not 500.

        The router catches FileNotFoundError from `load_build` and
        translates to 404 with a message — the frontend treats this as
        a recoverable state.
        """
        b1 = _make_build(
            profile_name="bold bear", school_name="IU", major_text="Marketing"
        )

        resp = client.post(
            "/builds/compare",
            json={"build_ids": [b1.build_id, "ghost-build-999"]},
        )
        assert resp.status_code == 404
        # The detail must mention the missing id so the frontend can log it.
        assert "ghost-build-999" in resp.json()["detail"]

    def test_returns_422_when_request_body_missing_build_ids(self, client):
        """Pydantic validation on `CompareRequest` must reject an empty body."""
        resp = client.post("/builds/compare", json={})
        assert resp.status_code == 422

    def test_compare_with_empty_build_ids_returns_422(self, client):
        """Empty list rejected by Pydantic min_length=2 validation."""
        resp = client.post("/builds/compare", json={"build_ids": []})
        assert resp.status_code == 422

    def test_compare_with_single_build_id_returns_422(self, client):
        """Single build rejected — need at least 2 to compare."""
        b1 = _make_build(
            profile_name="bold bear", school_name="IU", major_text="Marketing"
        )
        resp = client.post(
            "/builds/compare", json={"build_ids": [b1.build_id]}
        )
        assert resp.status_code == 422
