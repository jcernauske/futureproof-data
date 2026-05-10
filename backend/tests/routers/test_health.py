"""Tests for /health and /health/warmup endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import create_app


def _client() -> TestClient:
    return TestClient(create_app())


class TestHealthCheck:
    def test_health_returns_ok(self):
        resp = _client().get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["project"] == "futureproof"


class TestWarmup:
    def test_warmup_returns_202(self):
        with patch(
            "app.routers.health.gemma_client.generate_async",
            new_callable=AsyncMock,
            return_value="hi",
        ):
            resp = _client().post("/health/warmup")
        assert resp.status_code == 202
        assert resp.json()["status"] == "warming"

    def test_warmup_does_not_crash_on_failure(self):
        with patch(
            "app.routers.health.gemma_client.generate_async",
            new_callable=AsyncMock,
            side_effect=RuntimeError("model not loaded"),
        ):
            resp = _client().post("/health/warmup")
        assert resp.status_code == 202
