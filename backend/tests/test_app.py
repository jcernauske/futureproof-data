"""Tests for the FastAPI app factory and middleware configuration."""

from starlette.middleware.cors import CORSMiddleware

from app.main import create_app


def test_create_app_includes_health_route() -> None:
    """The app factory must wire the health router so /health is reachable."""
    application = create_app()
    route_paths = [route.path for route in application.routes]
    assert "/health" in route_paths


def test_create_app_has_cors_middleware() -> None:
    """CORS middleware must be present so the frontend dev server can reach the API."""
    application = create_app()
    middleware_classes = [m.cls for m in application.user_middleware]
    assert CORSMiddleware in middleware_classes


def test_create_app_cors_allows_vite_dev_origin() -> None:
    """The Vite dev server origin must be in the CORS allow list."""
    from fastapi.testclient import TestClient

    application = create_app()
    client = TestClient(application)

    # Simulate a CORS preflight from the Vite dev server
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
