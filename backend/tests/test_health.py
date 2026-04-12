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


def test_health_response_has_exactly_three_fields(client: TestClient) -> None:
    """Catch accidental field additions that would change the API contract."""
    data = client.get("/health").json()
    assert set(data.keys()) == {"status", "project", "version"}
