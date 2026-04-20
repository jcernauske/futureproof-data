"""Tests for the Set Your Course FastAPI router.

Three endpoints, wired under ``/intent``:
- ``POST /intent/stream`` — SSE stream. Test that the router forwards
  service events as SSE frames to the client.
- ``POST /intent/chip`` — chip dispatch. Test that a valid request
  round-trips through the response model; test that a ``not_expected``
  request with null clarifier returns 422 at the Pydantic validator
  (no handler invocation).

Gemma + MCP are fully mocked — no network, no DuckDB reads.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.services import gemma_client, set_your_course


@pytest.fixture(autouse=True)
def _disable_gemma_jsonl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMMA_LOG_DISABLED", "1")


@pytest.fixture(autouse=True)
def _reset_gemma_client() -> None:
    """Keep the module-level client/semaphore deterministic between
    tests; mirrors the services conftest autouse fixture."""
    gemma_client.reset_cache()
    yield
    gemma_client.reset_cache()


def _current_resolution_dict() -> dict[str, Any]:
    return {
        "matched_cip": "52.1401",
        "matched_title": "Marketing",
        "confidence": "high",
        "reasoning": "Marketing maps to 52.1401.",
        "careers_preview": ["Marketing Manager"],
        "audit_flag": None,
        "audit_message": None,
        "needs_clarification": False,
        "alternatives": [],
        "parent_cip": "",
        "confirmed_focus": None,
    }


class TestStream:
    def test_streams_to_client(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The router's ``StreamingResponse`` forwards whatever the
        service yields as SSE frames. We replace the service generator
        with a deterministic one and verify the frames land on the
        wire in order."""

        async def _fake_events(**kwargs: Any):
            yield {"event": "delta", "data": {"text": "Hello "}}
            yield {"event": "delta", "data": {"text": "world."}}
            yield {
                "event": "structured",
                "data": {
                    **_current_resolution_dict(),
                    "matched_title": "Marketing",
                },
            }
            yield {"event": "suggestions", "data": []}
            yield {"event": "done", "data": {}}

        monkeypatch.setattr(
            set_your_course, "stream_initial_resolution", _fake_events
        )

        response = client.post(
            "/intent/stream",
            json={
                "major_text": "marketing",
                "school_name": "Indiana University",
                "unitid": 151351,
                "programs": [],
            },
        )
        assert response.status_code == 200
        body = response.text

        # Each SSE frame carries an ``event:`` line, a ``data:`` line,
        # and ends with a blank line. Assert the sequence and payload.
        assert "event: delta" in body
        assert 'data: {"text": "Hello "}' in body
        assert 'data: {"text": "world."}' in body
        assert "event: structured" in body
        assert "event: suggestions" in body
        assert "event: done" in body
        # Ordering check — structured must appear before done.
        assert body.index("event: structured") < body.index("event: done")


class TestChip:
    def test_returns_chip_response(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The router delegates to ``handle_chip_dispatch`` and
        serializes the returned ``ChipResponse`` as JSON."""
        from app.models.api import ChipResponse

        async def _fake_dispatch(request: Any) -> ChipResponse:
            return ChipResponse(
                debug_trace="Trace text",
                updated_resolution=None,
                cta_link=None,
                bucket="no_issue_found",
                confirmed_focus=None,
            )

        monkeypatch.setattr(
            set_your_course, "handle_chip_dispatch", _fake_dispatch
        )

        response = client.post(
            "/intent/chip",
            json={
                "chip_id": "not_expected",
                "clarifier": "I wanted something else.",
                "current_resolution": _current_resolution_dict(),
                "initial_resolution": _current_resolution_dict(),
                "school_name": "Indiana University",
                "unitid": 151351,
                "programs": [],
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["debug_trace"] == "Trace text"
        assert body["bucket"] == "no_issue_found"
        assert body["updated_resolution"] is None
        assert body["confirmed_focus"] is None

    def test_not_expected_without_clarifier_returns_422(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """ChipRequest's @model_validator rejects ``not_expected`` with
        an empty/null clarifier. The handler MUST NOT be called."""
        handler_calls: list[Any] = []

        async def _fail_if_called(*args: Any, **kwargs: Any) -> Any:
            handler_calls.append((args, kwargs))
            raise AssertionError(
                "handler must not be reached when validator rejects"
            )

        monkeypatch.setattr(
            set_your_course, "handle_chip_dispatch", _fail_if_called
        )

        response = client.post(
            "/intent/chip",
            json={
                "chip_id": "not_expected",
                "clarifier": None,
                "current_resolution": _current_resolution_dict(),
                "initial_resolution": _current_resolution_dict(),
                "school_name": "Indiana University",
                "unitid": 151351,
                "programs": [],
            },
        )
        # Only assert on status — FastAPI's error body format is not
        # the contract under test.
        assert response.status_code == 422
        assert handler_calls == []
