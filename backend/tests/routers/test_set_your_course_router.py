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

from app.services import career_tiering, gemma_client, set_your_course


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


class TestStreamMajorTextValidation:
    """Bundle 6b: IntentStreamRequest.major_text has Field(max_length=200).

    Defense against tokenization explosion + pathologically long inputs
    (sometimes pasted accidentally, sometimes adversarial). Pydantic
    catches the violation at the model layer so the handler never runs.
    """

    def test_intent_stream_rejects_oversize_major_text(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """major_text >200 chars → 422 at the validator. Handler is NOT
        called; no Gemma traffic happens."""
        handler_calls: list[Any] = []

        async def _fail_if_called(*args: Any, **kwargs: Any) -> Any:
            handler_calls.append((args, kwargs))
            raise AssertionError(
                "stream_initial_resolution must NOT be called when "
                "Pydantic rejects an oversize major_text"
            )
            yield {}  # pragma: no cover — async-gen protocol

        monkeypatch.setattr(
            set_your_course, "stream_initial_resolution", _fail_if_called
        )

        # 201 chars — one over the cap.
        oversize = "a" * 201
        response = client.post(
            "/intent/stream",
            json={
                "major_text": oversize,
                "school_name": "Indiana University",
                "unitid": 151351,
                "programs": [],
            },
        )

        assert response.status_code == 422, (
            f"oversize major_text must be rejected at validation; "
            f"got {response.status_code} with body {response.text!r}"
        )
        assert handler_calls == [], (
            "Handler must not be reached when the Pydantic validator "
            "rejects the request"
        )
        # Best-effort assertion that the error body mentions the field.
        body = response.json()
        body_str = str(body).lower()
        assert "major_text" in body_str, (
            f"Expected 422 body to mention 'major_text'; got {body!r}"
        )

    def test_intent_stream_accepts_exactly_200_chars(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """200 chars (the boundary) is accepted — confirms the cap is
        inclusive, not off-by-one."""

        async def _fake_events(**_kwargs: Any):
            yield {"event": "structured", "data": {
                "matched_cip": "",
                "matched_title": "",
                "confidence": "low",
                "reasoning": "",
                "careers_preview": [],
                "audit_flag": None,
                "audit_message": None,
                "needs_clarification": True,
                "alternatives": None,
                "parent_cip": "",
                "confirmed_focus": None,
            }}
            yield {"event": "done", "data": {}}

        monkeypatch.setattr(
            set_your_course, "stream_initial_resolution", _fake_events
        )

        at_cap = "a" * 200
        response = client.post(
            "/intent/stream",
            json={
                "major_text": at_cap,
                "school_name": "Indiana University",
                "unitid": 151351,
                "programs": [],
            },
        )

        assert response.status_code == 200, (
            f"200-char major_text should pass validation; got "
            f"{response.status_code}: {response.text!r}"
        )


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


# ---------------------------------------------------------------------------
# POST /build/tier — intent fields forwarding (P1)
# ---------------------------------------------------------------------------


class TestTierEndpointIntentFields:
    """Verify the /build/tier endpoint forwards student_major_text and
    intent_keywords to the ``career_tiering.tier_careers`` service."""

    def test_tier_endpoint_forwards_intent_fields(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """POST /build/tier with student_major_text + intent_keywords
        forwards them to tier_careers."""
        captured: dict[str, Any] = {}

        async def _capture_tier_careers(outcomes, **kwargs):
            captured.update(kwargs)
            from collections import OrderedDict

            return OrderedDict({"All career paths": list(outcomes)})

        monkeypatch.setattr(
            career_tiering, "tier_careers_async", _capture_tier_careers
        )

        response = client.post(
            "/build/tier",
            json={
                "outcomes": [],
                "school_name": "Indiana University",
                "program_name": "Biology",
                "cipcode": "26.0101",
                "student_major_text": "biology pre-med",
                "intent_keywords": ["pre-med", "doctor"],
            },
        )
        assert response.status_code == 200
        assert captured["student_major_text"] == "biology pre-med"
        assert captured["intent_keywords"] == ["pre-med", "doctor"]

    def test_tier_endpoint_omitted_intent_fields_default_empty(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """POST /build/tier WITHOUT intent fields uses defaults (empty
        string and empty list) for backward compat."""
        captured: dict[str, Any] = {}

        async def _capture_tier_careers(outcomes, **kwargs):
            captured.update(kwargs)
            from collections import OrderedDict

            return OrderedDict({"All career paths": list(outcomes)})

        monkeypatch.setattr(
            career_tiering, "tier_careers_async", _capture_tier_careers
        )

        response = client.post(
            "/build/tier",
            json={
                "outcomes": [],
                "school_name": "Test U",
                "program_name": "Marketing",
                "cipcode": "52.14",
            },
        )
        assert response.status_code == 200
        # When student_major_text is None (not in JSON), the router
        # passes "" via `or ""`; intent_keywords defaults to [].
        assert captured["student_major_text"] == ""
        assert captured["intent_keywords"] == []


# ---------------------------------------------------------------------------
# Chip flow: intent fields round-trip (P1)
# ---------------------------------------------------------------------------


class TestChipFlowIntentFieldsRouter:
    """Verify that intent fields on the current_resolution survive the
    chip dispatch round-trip at the router level."""

    def test_chip_flow_preserves_intent_fields(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """IntentResult round-trips through chip dispatch with
        intent_keywords + student_major_text intact on the updated
        resolution."""
        from app.models.api import ChipResponse
        from app.models.career import IntentResult

        async def _fake_dispatch(request: Any) -> ChipResponse:
            # Verify the request carries the intent fields
            cr = request.current_resolution
            assert cr.student_major_text == "deaf ed"
            assert cr.intent_keywords == ["deaf education", "teacher"]

            updated = IntentResult(
                matched_cip="13.1001",
                matched_title="Special Education",
                confidence="high",
                reasoning="Updated.",
                careers_preview=[],
                parent_cip="",
                confirmed_focus="Deaf Education",
                student_major_text=cr.student_major_text,
                intent_keywords=[*cr.intent_keywords, "deaf education"],
            )
            return ChipResponse(
                debug_trace="Trace",
                updated_resolution=updated,
                bucket="crosswalk_mismatch",
                confirmed_focus="Deaf Education",
            )

        monkeypatch.setattr(
            set_your_course, "handle_chip_dispatch", _fake_dispatch
        )

        resolution_dict = {
            **_current_resolution_dict(),
            "student_major_text": "deaf ed",
            "intent_keywords": ["deaf education", "teacher"],
        }
        response = client.post(
            "/intent/chip",
            json={
                "chip_id": "not_expected",
                "clarifier": "I want deaf ed.",
                "current_resolution": resolution_dict,
                "initial_resolution": _current_resolution_dict(),
                "school_name": "Indiana University",
                "unitid": 151351,
                "programs": [],
            },
        )
        assert response.status_code == 200
        body = response.json()
        updated = body["updated_resolution"]
        assert updated is not None
        assert updated["student_major_text"] == "deaf ed"
        assert "deaf education" in updated["intent_keywords"]
