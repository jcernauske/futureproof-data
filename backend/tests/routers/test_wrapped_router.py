"""Tests for the Wrapped router endpoints.

Playwright is mocked out — these tests exercise the HTTP boundary,
caching, and error paths using FastAPI's TestClient. Chromium is never
launched.

Endpoints covered:
  POST /build/{id}/wrapped/render  → {"status": "ok"|"cached", frame_count}
  GET  /build/{id}/wrapped          → {"frames": [...]}  or 409 if unrendered
  GET  /build/{id}/wrapped/{idx}    → image/png binary   or 404
"""

from __future__ import annotations

from unittest.mock import AsyncMock

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


def _make_build() -> Build:
    career = CareerOutcome(
        unitid=151351,
        institution_name="IU-B",
        cipcode="52.14",
        program_name="Marketing",
        soc_code="13-2051",
        occupation_title="Financial Analyst",
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
            )
        ],
        wins=1,
        losses=0,
        draws=0,
        unknown=0,
        verdict="SOLID",
    )
    return builds_service.build_from_parts(
        school_name="IU-B",
        unitid=151351,
        major_text="Marketing",
        cipcode="52.14",
        program_name="Marketing",
        effort="balanced",
        career=career,
        gauntlet=gauntlet,
        branches=[],
        skill_recs=[],
        guidance="",
        profile_name="bold bear",
    )


def _png_bytes(marker: bytes) -> bytes:
    """Minimal PNG-ish bytes for BLOB round-trip tests."""
    return b"\x89PNG\r\n\x1a\n" + marker


@pytest.fixture
def client(isolated_builds_db) -> TestClient:
    """A fresh FastAPI app + TestClient per test, using the isolated DB."""
    return TestClient(create_app())


@pytest.fixture
def saved_build(isolated_builds_db) -> Build:
    """A build persisted in the isolated DuckDB."""
    build = _make_build()
    builds_service.save_build(build)
    return build


# --- 404 / build lookup ----------------------------------------------------


class TestBuildNotFound:
    def test_render_returns_404_for_unknown_build(self, client):
        resp = client.post("/build/does-not-exist-999/wrapped/render")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_get_wrapped_returns_404_for_unknown_build(self, client):
        resp = client.get("/build/does-not-exist-999/wrapped")
        assert resp.status_code == 404

    def test_get_frame_returns_404_for_unknown_build_in_valid_range(
        self, client
    ):
        """Frame endpoint skips the build-existence check and goes straight
        to the frame lookup — if there's no frame, it's a 404 regardless."""
        resp = client.get("/build/does-not-exist-999/wrapped/0")
        assert resp.status_code == 404


# --- GET /wrapped — 409 when not yet rendered -------------------------------


class TestGetWrappedBeforeRender:
    def test_returns_409_when_frames_not_rendered(self, client, saved_build):
        resp = client.get(f"/build/{saved_build.build_id}/wrapped")
        assert resp.status_code == 409
        body = resp.json()
        assert "render" in body["detail"].lower(), (
            "409 detail should hint that /render must be called first"
        )

    def test_409_references_render_endpoint_in_hint(self, client, saved_build):
        """Guide the frontend: the error body points at the fix."""
        resp = client.get(f"/build/{saved_build.build_id}/wrapped")
        assert resp.status_code == 409
        assert "/wrapped/render" in resp.json()["detail"]


# --- POST /render — success & cache ----------------------------------------


class TestRenderSuccessAndCache:
    def test_render_returns_ok_status_and_frame_count(
        self, client, saved_build, monkeypatch
    ):
        """Mock render_frames so Playwright is never launched."""
        from app.services import wrapped_renderer

        mock_render = AsyncMock(
            return_value=[(i, _png_bytes(bytes([i]))) for i in range(6)]
        )
        monkeypatch.setattr(wrapped_renderer, "render_frames", mock_render)

        resp = client.post(f"/build/{saved_build.build_id}/wrapped/render")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "frame_count": 6}
        mock_render.assert_awaited_once()

    def test_render_persists_frames_to_duckdb(
        self, client, saved_build, monkeypatch
    ):
        from app.services import wrapped_renderer

        monkeypatch.setattr(
            wrapped_renderer,
            "render_frames",
            AsyncMock(return_value=[(i, _png_bytes(bytes([i]))) for i in range(6)]),
        )
        client.post(f"/build/{saved_build.build_id}/wrapped/render")

        assert builds_service.list_wrapped_frames(saved_build.build_id) == [
            0, 1, 2, 3, 4, 5
        ]

    def test_second_render_returns_cached_status(
        self, client, saved_build, monkeypatch
    ):
        """Idempotent: calling /render twice doesn't re-run Playwright."""
        from app.services import wrapped_renderer

        mock_render = AsyncMock(
            return_value=[(i, _png_bytes(bytes([i]))) for i in range(6)]
        )
        monkeypatch.setattr(wrapped_renderer, "render_frames", mock_render)

        r1 = client.post(f"/build/{saved_build.build_id}/wrapped/render")
        assert r1.json()["status"] == "ok"
        assert mock_render.await_count == 1

        r2 = client.post(f"/build/{saved_build.build_id}/wrapped/render")
        assert r2.status_code == 200
        assert r2.json() == {"status": "cached", "frame_count": 6}
        # Second call must NOT re-invoke the renderer
        assert mock_render.await_count == 1

    def test_partial_render_not_treated_as_cached(
        self, client, saved_build, monkeypatch
    ):
        """If only 3 frames exist, a re-render must re-run (not skip).

        Cache freshness is defined as `len(existing) == 6`. A partial
        render (e.g., crashed halfway) must NOT short-circuit.
        """
        from app.services import wrapped_renderer

        # Seed 3 frames manually with an OLD timestamp, then trigger /render
        builds_service._conn().execute(
            "INSERT INTO wrapped_frames "
            "(build_id, frame_index, png_data, rendered_at) "
            "VALUES (?, ?, ?, ?)",
            [saved_build.build_id, 0, b"stale", "2020-01-01T00:00:00+00:00"],
        )
        builds_service._conn().execute(
            "INSERT INTO wrapped_frames "
            "(build_id, frame_index, png_data, rendered_at) "
            "VALUES (?, ?, ?, ?)",
            [saved_build.build_id, 1, b"stale", "2020-01-01T00:00:00+00:00"],
        )

        mock_render = AsyncMock(
            return_value=[(i, _png_bytes(bytes([i]))) for i in range(6)]
        )
        monkeypatch.setattr(wrapped_renderer, "render_frames", mock_render)

        resp = client.post(f"/build/{saved_build.build_id}/wrapped/render")
        assert resp.json()["status"] == "ok"  # NOT "cached"
        mock_render.assert_awaited_once()

    def test_render_surfaces_runtime_error_as_500(
        self, client, saved_build, monkeypatch
    ):
        """RuntimeError from render_frames (e.g. Playwright missing) → 500."""
        from app.services import wrapped_renderer

        monkeypatch.setattr(
            wrapped_renderer,
            "render_frames",
            AsyncMock(side_effect=RuntimeError("playwright is not installed")),
        )
        resp = client.post(f"/build/{saved_build.build_id}/wrapped/render")
        assert resp.status_code == 500
        assert "playwright" in resp.json()["detail"].lower()


# --- GET /wrapped — after render --------------------------------------------


class TestGetWrappedAfterRender:
    def test_returns_six_frames_with_correct_shape(
        self, client, saved_build, monkeypatch
    ):
        from app.services import wrapped_renderer

        monkeypatch.setattr(
            wrapped_renderer,
            "render_frames",
            AsyncMock(return_value=[(i, _png_bytes(bytes([i]))) for i in range(6)]),
        )
        client.post(f"/build/{saved_build.build_id}/wrapped/render")

        resp = client.get(f"/build/{saved_build.build_id}/wrapped")
        assert resp.status_code == 200
        body = resp.json()
        assert "frames" in body
        assert len(body["frames"]) == 6
        for i, frame in enumerate(body["frames"]):
            assert frame["index"] == i
            assert frame["url"] == f"/build/{saved_build.build_id}/wrapped/{i}"


# --- GET /wrapped/{idx} — frame PNG serving --------------------------------


class TestGetSingleFrame:
    def test_returns_png_bytes_with_correct_content_type(
        self, client, saved_build, monkeypatch
    ):
        from app.services import wrapped_renderer

        payload = _png_bytes(b"frame-3-unique-marker")
        frames = [(i, _png_bytes(bytes([i]))) for i in range(6)]
        frames[3] = (3, payload)
        monkeypatch.setattr(
            wrapped_renderer, "render_frames", AsyncMock(return_value=frames)
        )
        client.post(f"/build/{saved_build.build_id}/wrapped/render")

        resp = client.get(f"/build/{saved_build.build_id}/wrapped/3")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        assert resp.content == payload

    def test_response_has_attachment_content_disposition(
        self, client, saved_build, monkeypatch
    ):
        """Content-Disposition: attachment makes browsers download the file."""
        from app.services import wrapped_renderer

        monkeypatch.setattr(
            wrapped_renderer,
            "render_frames",
            AsyncMock(return_value=[(i, _png_bytes(bytes([i]))) for i in range(6)]),
        )
        client.post(f"/build/{saved_build.build_id}/wrapped/render")

        resp = client.get(f"/build/{saved_build.build_id}/wrapped/2")
        disposition = resp.headers.get("content-disposition", "")
        assert "attachment" in disposition
        # Filename includes build id and 0-indexed frame number
        assert f"futureproof-{saved_build.build_id}-frame-2.png" in disposition

    def test_has_cache_control_header(
        self, client, saved_build, monkeypatch
    ):
        from app.services import wrapped_renderer

        monkeypatch.setattr(
            wrapped_renderer,
            "render_frames",
            AsyncMock(return_value=[(i, _png_bytes(bytes([i]))) for i in range(6)]),
        )
        client.post(f"/build/{saved_build.build_id}/wrapped/render")

        resp = client.get(f"/build/{saved_build.build_id}/wrapped/0")
        assert "max-age" in resp.headers.get("cache-control", "").lower()

    def test_returns_404_for_frame_index_above_five(self, client, saved_build):
        """frame_index > 5 is out of the 6-frame contract."""
        resp = client.get(f"/build/{saved_build.build_id}/wrapped/6")
        assert resp.status_code == 404
        assert "out of range" in resp.json()["detail"].lower()

    def test_returns_404_for_negative_frame_index(self, client, saved_build):
        resp = client.get(f"/build/{saved_build.build_id}/wrapped/-1")
        assert resp.status_code == 404

    def test_returns_404_when_frame_index_valid_but_not_rendered(
        self, client, saved_build
    ):
        """Frame 2 is in the [0,5] range, but no render has happened."""
        resp = client.get(f"/build/{saved_build.build_id}/wrapped/2")
        assert resp.status_code == 404
        detail = resp.json()["detail"].lower()
        assert "not rendered" in detail or "no frame" in detail

    def test_returns_404_for_partially_rendered_missing_index(
        self, client, saved_build, monkeypatch
    ):
        """Seed only frames 0,1,2 — index 3 is 404.

        This matches the crash-mid-render scenario.
        """
        from app.services import wrapped_renderer

        monkeypatch.setattr(
            wrapped_renderer,
            "render_frames",
            AsyncMock(return_value=[(i, _png_bytes(bytes([i]))) for i in range(3)]),
        )
        client.post(f"/build/{saved_build.build_id}/wrapped/render")

        # Indices 0..2 exist; 3 does not
        assert client.get(
            f"/build/{saved_build.build_id}/wrapped/2"
        ).status_code == 200
        assert client.get(
            f"/build/{saved_build.build_id}/wrapped/3"
        ).status_code == 404
