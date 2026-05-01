"""Tests for the FastAPI app factory and middleware configuration."""

import warnings

import pytest
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

    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_lifespan_runs_without_raising() -> None:
    """The lifespan context manager must boot cleanly and emit no on_event
    DeprecationWarning. Catches a regression to the legacy startup hook.
    """
    from fastapi.testclient import TestClient

    application = create_app()
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        with TestClient(application) as client:
            response = client.get("/health")
            assert response.status_code == 200

    deprecation_messages = [
        str(w.message)
        for w in captured
        if issubclass(w.category, DeprecationWarning)
    ]
    assert not any(
        "on_event" in msg for msg in deprecation_messages
    ), f"on_event DeprecationWarning leaked: {deprecation_messages}"


def test_cors_disallows_unlisted_origin() -> None:
    """A preflight from an origin NOT in the allowlist must not receive a
    permissive access-control-allow-origin header. Catches a regression
    to allow_origins=["*"] which would silently echo any origin under
    allow_credentials=True.
    """
    from fastapi.testclient import TestClient

    application = create_app()
    client = TestClient(application)

    response = client.options(
        "/health",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    allow_origin = response.headers.get("access-control-allow-origin")
    assert allow_origin != "https://evil.example.com"
    assert allow_origin != "*"


def test_cors_origins_env_var_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Setting CORS_ALLOWED_ORIGINS replaces the dev defaults. Catches
    accidental hardcoding of localhost in the production deploy path.
    """
    from fastapi.testclient import TestClient

    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com")
    application = create_app()
    client = TestClient(application)

    allowed = client.options(
        "/health",
        headers={
            "Origin": "https://app.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert (
        allowed.headers.get("access-control-allow-origin")
        == "https://app.example.com"
    )

    blocked = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert blocked.headers.get("access-control-allow-origin") != "http://localhost:5173"


def test_parse_cors_origins_empty_env_falls_back_to_dev_defaults(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """CORS_ALLOWED_ORIGINS="" (or whitespace-only / comma-only) MUST NOT
    silently deny every preflight — that's the same demo-killer shape the
    audit was trying to fix. Empty values fall back to DEFAULT_DEV_ORIGINS
    so a stray ``CORS_ALLOWED_ORIGINS=`` in a Railway env doesn't break
    local dev. The all-stripped path additionally emits a WARNING so
    misconfiguration is visible in logs/.
    """
    import logging

    from app.main import DEFAULT_DEV_ORIGINS, _parse_cors_origins

    expected = [
        origin.strip()
        for origin in DEFAULT_DEV_ORIGINS.split(",")
        if origin.strip()
    ]

    # Empty string → falls back, no warning required (env was simply blank)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "")
    assert _parse_cors_origins() == expected

    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "   ")
    assert _parse_cors_origins() == expected

    # Non-empty but all-stripped → falls back AND emits a startup WARNING
    with caplog.at_level(logging.WARNING, logger="startup"):
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "   ,  , ")
        assert _parse_cors_origins() == expected
    assert any(
        "CORS_ALLOWED_ORIGINS" in r.getMessage() and r.levelno == logging.WARNING
        for r in caplog.records
    ), "expected a WARN log from the empty-after-strip fallback"


def test_lifespan_tolerates_profile_preload_failure(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """If ``_load_existing_profiles`` raises during startup, the app must
    still boot. ``lifespan``'s startup-exception semantics in FastAPI
    0.115+ refuse to serve traffic on any unhandled raise — so a
    profiles-table read failure during cold start would otherwise prevent
    the app from coming up. The defensive try/except logs a WARNING and
    moves on. Catches a regression to the bare ``_load_existing_profiles()``
    call that was preserved as parity with the legacy ``on_event`` hook.
    """
    import logging

    from fastapi.testclient import TestClient

    from app.services import profile

    def _boom() -> None:
        raise RuntimeError("simulated profiles read failure")

    monkeypatch.setattr(profile, "_load_existing_profiles", _boom)

    application = create_app()
    with caplog.at_level(logging.WARNING, logger="startup"):
        with TestClient(application) as client:
            response = client.get("/health")
            assert response.status_code == 200

    assert any(
        "profile preload failed" in r.getMessage()
        and r.levelno == logging.WARNING
        and r.name == "startup"
        for r in caplog.records
    ), "expected a WARNING log from the lifespan profile-preload guard"


def test_parse_cors_origins_strips_and_drops_whitespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Comma-separated parsing must strip whitespace around each entry and
    drop empty fragments — guards against `CORS_ALLOWED_ORIGINS="a, ,b,"`
    being misparsed into ["a", " ", "b", ""], which CORSMiddleware would
    silently treat as "allow the empty-string origin" (i.e. nothing useful).
    """
    from app.main import _parse_cors_origins

    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        " https://a.example.com , ,https://b.example.com,",
    )
    assert _parse_cors_origins() == [
        "https://a.example.com",
        "https://b.example.com",
    ]
