import pytest
from fastapi.testclient import TestClient

from app.models.health import HealthResponse


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["project"] == "futureproof"
    assert data["version"] == "0.1.0"


def test_health_response_model(client: TestClient) -> None:
    response = client.get("/health")
    model = HealthResponse(**response.json())
    assert model.status == "ok"
    assert model.project == "futureproof"
    assert model.version == "0.1.0"


def test_health_returns_json_content_type(client: TestClient) -> None:
    """Response must be application/json so frontend fetch() parses correctly."""
    response = client.get("/health")
    assert "application/json" in response.headers["content-type"]


def test_health_post_not_allowed(client: TestClient) -> None:
    """POST /health should be rejected -- only GET is defined."""
    response = client.post("/health")
    assert response.status_code == 405


def test_health_response_contract_fields(client: TestClient) -> None:
    """Catch accidental field additions that would change the API contract."""
    data = client.get("/health").json()
    assert set(data.keys()) == {
        "status",
        "project",
        "version",
        "inference_backend",
        "inference_model",
        "model_reachable",
    }


def test_health_reports_ollama_when_env_unset(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default INFERENCE_BACKEND is ollama. The badge should reflect that."""
    monkeypatch.delenv("INFERENCE_BACKEND", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    data = client.get("/health").json()
    assert data["inference_backend"] == "ollama"
    assert data["inference_model"]  # non-empty default


def test_health_reports_openrouter_when_set(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Health endpoint must not raise even when openrouter env is misconfigured.

    A missing ``OPENROUTER_API_KEY`` would make ``current_config()`` raise,
    so the helper falls back to env-derived values.
    """
    monkeypatch.setenv("INFERENCE_BACKEND", "openrouter")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_MODEL", "google/gemma-test")
    data = client.get("/health").json()
    assert data["inference_backend"] == "openrouter"
    assert data["inference_model"] == "google/gemma-test"
