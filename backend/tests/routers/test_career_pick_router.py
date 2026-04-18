"""Tests for the /career-pick HTTP router.

Covers:
  - GET /career-pick/chips with pre-med elevation.
  - POST /career-pick/ask happy path (Gemma mocked).
  - POST /career-pick/ask with unknown chip_id → 422.
  - POST /career-pick/ask with malformed body → 422 from Pydantic.

Uses the shared ``client`` fixture from ``backend/tests/conftest.py``.
Gemma transport is mocked via ``monkeypatch.setattr`` on
``gemma_client.generate_async`` — both sync and async endpoints work
with an ``async`` stub because ``career_pick_qna.ask`` awaits the call.

The autouse ``_reset_gemma_client`` fixture below makes the module-level
semaphore + cache deterministic across tests (the routers/conftest.py
ships the isolated_builds_db fixture but not the Gemma reset — we add
it here so env changes in one test don't leak into the next).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.services import gemma_client


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_gemma_client() -> None:
    """Reset the module-level Gemma client + semaphore before each test.

    The service-layer conftest.py already autouses this behavior for tests
    under tests/services/; mirror it here so router tests that monkeypatch
    ``generate_async`` don't leak the patch into the next test via the
    cached semaphore.
    """
    gemma_client.reset_cache()
    yield
    gemma_client.reset_cache()


@pytest.fixture(autouse=True)
def _disable_gemma_jsonl(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default: skip JSONL writes. Individual tests can unset this."""
    monkeypatch.setenv("GEMMA_LOG_DISABLED", "1")


# ---------------------------------------------------------------------------
# GET /career-pick/chips
# ---------------------------------------------------------------------------


def test_get_chips_returns_elevated_chip_for_pre_med(client: TestClient) -> None:
    """pre-med + SOC list lacking physician → elevated 'why_no_doctor' chip
    first with terminal_title='doctor'."""
    response = client.get(
        "/career-pick/chips",
        params={
            "cipcode": "26.0101",
            "major_text": "pre-med",
            "soc_codes": ["19-1029"],
        },
    )
    assert response.status_code == 200, response.text
    chips = response.json()
    assert isinstance(chips, list)
    assert len(chips) >= 1
    first = chips[0]
    assert first["id"] == "why_no_doctor"
    assert first["elevated"] is True
    assert first["terminal_title"] == "doctor"

    # Base-catalog chips follow (non-graduate-intent chips).
    base_ids = [chip["id"] for chip in chips[1:]]
    assert "what_does_this_do" in base_ids
    assert "right_school_for_this" in base_ids
    assert "why_these_tiers" in base_ids


def test_get_chips_returns_base_catalog_for_generic_major(
    client: TestClient,
) -> None:
    """marketing → no elevation, base catalog only, no terminal_title set."""
    response = client.get(
        "/career-pick/chips",
        params={
            "cipcode": "52.1401",
            "major_text": "marketing",
            "soc_codes": ["13-1161"],
        },
    )
    assert response.status_code == 200, response.text
    chips = response.json()
    assert [chip["id"] for chip in chips] == [
        "what_does_this_do",
        "right_school_for_this",
        "why_these_tiers",
    ]
    assert all(chip["elevated"] is False for chip in chips)


# ---------------------------------------------------------------------------
# POST /career-pick/ask
# ---------------------------------------------------------------------------


def test_post_ask_returns_gemma_response(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST /career-pick/ask with a valid chip_id + mocked Gemma returns the
    canned text in the response body shape ``AskCareerPickResponse``."""

    async def _fake_generate_async(**_kwargs: object) -> str:
        return "Biology is the standard pre-med path."

    monkeypatch.setattr(gemma_client, "generate_async", _fake_generate_async)

    response = client.post(
        "/career-pick/ask",
        json={
            "chip_id": "why_no_doctor",
            "cipcode": "26.0101",
            "major_text": "pre-med",
            "soc_codes": ["19-1029", "13-1071"],
            "selected_soc": None,
            "terminal_title": "doctor",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["chip_id"] == "why_no_doctor"
    assert body["answer"] == "Biology is the standard pre-med path."
    assert body["fallback_fired"] is False


def test_post_ask_falls_back_when_gemma_returns_empty(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty Gemma response → 200 with fallback_fired=True and a non-empty
    answer (the canned fallback copy)."""

    async def _empty(**_kwargs: object) -> str:
        return ""

    monkeypatch.setattr(gemma_client, "generate_async", _empty)

    response = client.post(
        "/career-pick/ask",
        json={
            "chip_id": "why_no_doctor",
            "cipcode": "26.0101",
            "major_text": "pre-med",
            "soc_codes": ["19-1029"],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["fallback_fired"] is True
    assert body["answer"].strip() != ""


def test_post_ask_unknown_chip_id_returns_422(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unknown chip_id → 422 (service raises ValueError, router maps to 422)."""

    async def _unused(**_kwargs: object) -> str:  # pragma: no cover
        return "never called"

    monkeypatch.setattr(gemma_client, "generate_async", _unused)

    response = client.post(
        "/career-pick/ask",
        json={
            "chip_id": "this_chip_does_not_exist",
            "cipcode": "26.0101",
            "major_text": "pre-med",
            "soc_codes": [],
        },
    )
    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    # Message surfaces the unknown chip id so the client can tell the user.
    assert "this_chip_does_not_exist" in detail


def test_post_ask_malformed_body_returns_422(client: TestClient) -> None:
    """Missing required fields → 422 from Pydantic validation."""
    response = client.post(
        "/career-pick/ask",
        json={
            # chip_id missing
            "cipcode": "26.0101",
            # major_text missing
        },
    )
    assert response.status_code == 422, response.text
    # Pydantic's 422 detail is a list of validation errors — pick out the
    # missing-field reports without being too brittle about shape.
    detail = response.json()["detail"]
    missing_locs = {
        tuple(item.get("loc", [])) for item in detail if isinstance(item, dict)
    }
    # Both chip_id and major_text should surface as missing.
    missing_fields = {loc[-1] for loc in missing_locs if loc}
    assert "chip_id" in missing_fields
    assert "major_text" in missing_fields
