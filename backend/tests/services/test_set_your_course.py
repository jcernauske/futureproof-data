"""Tests for ``app.services.set_your_course``.

Covers:
- ``stream_initial_resolution`` happy path + transport failure.
- ``handle_chip_dispatch`` for all three chip ids:
  - ``not_expected`` — the Gemma-heavy path.
  - ``show_less_common`` + ``change_major`` — no Gemma, no log.
- Tail parsing (``---UPDATED_RESOLUTION---``, ``---BUCKET---``,
  ``---CONFIRMED_FOCUS---``) including the three service-side invariants
  that strip ``confirmed_focus`` when:
  1. The bucket is ``semantic_drift`` or ``intent_divergence``.
  2. No tool call was made (pre-fetch returned empty).
  3. Numeric-code parentheticals leak into the confirmed focus.
- Observability: every Gemma call records ``call_site`` on the JSONL log.

Mocks:
- ``gemma_client.generate_chat_async`` for the chip path.
- ``gemma_client.generate_stream_async`` for the initial-resolution path.
- ``mcp_client.call`` for the MCP pre-fetch.
- Stubs for ``intent._get_school_cips``,
  ``intent._get_crosswalk_cips_for_families``,
  ``intent._get_career_titles_for_cip``,
  ``community_suggestions.get_suggestions``.

The autouse ``_reset_gemma_client_state`` fixture in services/conftest.py
resets the Gemma semaphore/cache between tests.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence
from typing import Any

import pytest

from app.models.api import ChipRequest
from app.models.career import IntentResult
from app.services import (
    community_suggestions,
    gemma_client,
    intent,
    mcp_client,
    set_your_course,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _disable_gemma_jsonl(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default: skip JSONL writes. Individual tests unset this to assert
    on the logged records."""
    monkeypatch.setenv("GEMMA_LOG_DISABLED", "1")


@pytest.fixture(autouse=True)
def _stub_gemma_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent ``current_config()`` from loading the user's ``.env``.

    The commit path calls ``gemma_client.current_config()`` for the
    ``backend`` + ``model`` fields on the correction record.
    """

    class _Cfg:
        model = "stub-model"
        backend = "stub"

    monkeypatch.setattr(
        set_your_course.gemma_client, "current_config", lambda: _Cfg()
    )


@pytest.fixture(autouse=True)
def _reset_community_aggregate() -> None:
    """Empty the in-memory aggregate between tests so suggestion lookups
    don't bleed state."""
    community_suggestions.reset_for_tests()
    yield
    community_suggestions.reset_for_tests()


@pytest.fixture
def stub_intent_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the DuckDB-backed helpers that
    ``stream_initial_resolution`` and
    ``_build_intent_result_from_tail`` call.

    The stream tests only care about the prose-vs-tail state machine
    and the suggestion plumbing. DB calls would either hang or 404 in
    CI so we short-circuit them with empty lists.
    """
    monkeypatch.setattr(intent, "_get_school_cips", lambda unitid: [])
    monkeypatch.setattr(
        intent, "_get_crosswalk_cips_for_families", lambda fams: []
    )
    monkeypatch.setattr(intent, "_get_career_titles_for_cip", lambda cip: [])
    monkeypatch.setattr(intent, "_derive_parent_cip", lambda cip4, progs: "")
    monkeypatch.setattr(
        community_suggestions,
        "get_suggestions",
        lambda unitid, input_normalized, top_k=3: [],
    )


def _make_current_resolution(**overrides: Any) -> IntentResult:
    """Return an IntentResult shaped like a resolved state."""
    defaults: dict[str, Any] = {
        "matched_cip": "52.1401",
        "matched_title": "Marketing",
        "confidence": "high",
        "reasoning": "Marketing maps to 52.1401.",
        "careers_preview": ["Marketing Manager", "Marketing Specialist"],
        "audit_flag": None,
        "audit_message": None,
        "needs_clarification": False,
        "alternatives": [],
        "parent_cip": "",
        "confirmed_focus": None,
    }
    defaults.update(overrides)
    return IntentResult(**defaults)


def _make_chip_request(
    *,
    chip_id: str = "not_expected",
    clarifier: str | None = "I want marketing-manager jobs.",
    current: IntentResult | None = None,
    initial: IntentResult | None = None,
) -> ChipRequest:
    return ChipRequest(
        chip_id=chip_id,  # type: ignore[arg-type]
        clarifier=clarifier,
        current_resolution=current or _make_current_resolution(),
        initial_resolution=initial or _make_current_resolution(),
        school_name="Indiana University",
        unitid=151351,
        programs=[],
    )


# Helper that satisfies the ``AsyncIterator[str]`` contract of
# ``generate_stream_async`` — yields chunks then returns.
def _stream_from(chunks: Sequence[str]):
    async def _gen(**_kwargs: Any) -> AsyncIterator[str]:
        for chunk in chunks:
            yield chunk

    return _gen


def _stream_raises(exc: Exception):
    async def _gen(**_kwargs: Any) -> AsyncIterator[str]:
        # Must be a proper async generator that raises inside, so the
        # service's ``async for`` hits the exception path. Yield once
        # first so the try/except wraps the real exception during the
        # iteration, matching real transport failures.
        if False:  # pragma: no cover — satisfies the generator protocol
            yield ""
        raise exc

    return _gen


# ---------------------------------------------------------------------------
# stream_initial_resolution
# ---------------------------------------------------------------------------


class TestStreamInitial:
    @pytest.mark.asyncio
    async def test_happy_path_streams_content(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_intent_helpers: None,
    ) -> None:
        """Streamed prose chunks are forwarded, delimiter + tail produce
        a structured IntentResult, suggestions + done close the stream."""
        prose = 'Marketing maps to the Marketing program.'
        tail = (
            '\n---INTENT_JSON---\n'
            '{"matched_cip": "52.1401", "matched_title": "Marketing", '
            '"confidence": "high", "parent_cip": "52.14", "alternatives": []}'
        )
        chunks = [prose[:10], prose[10:], tail]
        monkeypatch.setattr(
            gemma_client, "generate_stream_async", _stream_from(chunks)
        )

        events: list[dict[str, Any]] = []
        async for event in set_your_course.stream_initial_resolution(
            major_text="marketing",
            school_name="Indiana University",
            unitid=151351,
            programs=[],
        ):
            events.append(event)

        # Expect: some "delta" events, exactly one "structured", one
        # "suggestions", one "done" — in that order.
        event_names = [e["event"] for e in events]
        assert event_names.count("structured") == 1
        assert event_names.count("suggestions") == 1
        assert event_names.count("done") == 1
        assert event_names[-1] == "done"
        assert event_names[-2] == "suggestions"
        assert event_names[-3] == "structured"

        deltas = [e for e in events if e["event"] == "delta"]
        assert len(deltas) >= 1
        # The prose — and ONLY the prose — was emitted as deltas. The
        # delimiter and JSON tail must never reach the client.
        emitted = "".join(d["data"]["text"] for d in deltas)
        assert "---INTENT_JSON---" not in emitted
        assert "matched_cip" not in emitted
        assert emitted.strip().startswith("Marketing maps to")

        structured = next(e for e in events if e["event"] == "structured")
        assert structured["data"]["matched_cip"] == "52.1401"
        assert structured["data"]["matched_title"] == "Marketing"
        assert structured["data"]["confidence"] == "high"

    @pytest.mark.asyncio
    async def test_transport_failure_returns_empty(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_intent_helpers: None,
    ) -> None:
        """Gemma raising mid-stream yields a structured+done pair (no
        crash). The IntentResult is a low-confidence placeholder."""
        monkeypatch.setattr(
            gemma_client,
            "generate_stream_async",
            _stream_raises(RuntimeError("boom")),
        )

        events: list[dict[str, Any]] = []
        async for event in set_your_course.stream_initial_resolution(
            major_text="marketing",
            school_name="Indiana University",
            unitid=151351,
            programs=[],
        ):
            events.append(event)

        # Even on transport failure we MUST deliver the trailing
        # structured/suggestions/done events — the frontend is
        # awaiting them.
        names = [e["event"] for e in events]
        assert "structured" in names
        assert "done" in names
        structured = next(e for e in events if e["event"] == "structured")
        # Placeholder payload per ``_build_intent_result_from_tail``.
        assert structured["data"]["confidence"] == "low"
        assert structured["data"]["needs_clarification"] is True
        # No deltas were emitted — transport never produced a chunk.
        assert all(e["event"] != "delta" for e in events)


# ---------------------------------------------------------------------------
# handle_chip_dispatch
# ---------------------------------------------------------------------------


class _GemmaRecorder:
    """Captures ``generate_chat_async`` kwargs so tests can assert the
    prompt carried the clarifier / tool context / etc."""

    def __init__(self, response: str = "") -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    async def __call__(self, **kwargs: Any) -> str:
        self.calls.append(kwargs)
        return self.response


class TestChipDispatch:
    @pytest.mark.asyncio
    async def test_not_expected_runs_gemma_with_clarifier(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The clarifier is interpolated into the system prompt and the
        pre-fetch is called before Gemma."""
        mcp_calls: list[tuple[str, dict[str, Any]]] = []

        def _mock_mcp_call(tool: str, args: dict[str, Any]) -> dict[str, Any]:
            mcp_calls.append((tool, args))
            return {
                "data": [
                    {
                        "occupation_title": "Marketing Manager",
                        "soc_code": "11-2021",
                    }
                ]
            }

        monkeypatch.setattr(mcp_client, "call", _mock_mcp_call)
        recorder = _GemmaRecorder(
            response='Trace.\n---BUCKET---\n{"bucket": "no_issue_found"}'
        )
        monkeypatch.setattr(
            gemma_client, "generate_chat_async", recorder
        )

        request = _make_chip_request(
            clarifier="I wanted marketing-manager jobs, not general business."
        )
        response = await set_your_course.handle_chip_dispatch(request)

        # Pre-fetch happened exactly once against get_career_paths.
        # The new flow passes student_cip = matched_cip so the MCP
        # handler's YAML-backed _find_major_intent is bypassed.
        assert len(mcp_calls) == 1
        tool_name, tool_args = mcp_calls[0]
        assert tool_name == "get_career_paths"
        assert tool_args == {
            "unitid": 151351,
            "cipcode": "52.1401",
            "student_cip": "52.1401",
        }

        # Gemma was called with the clarifier text in the system prompt.
        assert len(recorder.calls) == 1
        call = recorder.calls[0]
        system = call["system"]
        assert "I wanted marketing-manager jobs" in system
        assert "Indiana University" in system
        # And the user message carried the tool context block.
        user = call["messages"][0]["content"]
        assert "Marketing Manager" in user or "11-2021" in user

        assert response.bucket == "no_issue_found"

    @pytest.mark.asyncio
    async def test_not_expected_without_clarifier_422(self) -> None:
        """Pydantic's ``@model_validator`` on ChipRequest rejects a
        ``not_expected`` request with an empty/null clarifier. This is
        the service's first line of defense — FastAPI returns 422 from
        the router level without ever reaching the handler."""
        with pytest.raises(Exception) as excinfo:
            ChipRequest(
                chip_id="not_expected",
                clarifier=None,
                current_resolution=_make_current_resolution(),
                initial_resolution=_make_current_resolution(),
                school_name="IU",
                unitid=1,
                programs=[],
            )
        assert "clarifier is required" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            ChipRequest(
                chip_id="not_expected",
                clarifier="   ",  # whitespace-only is rejected
                current_resolution=_make_current_resolution(),
                initial_resolution=_make_current_resolution(),
                school_name="IU",
                unitid=1,
                programs=[],
            )
        assert "clarifier is required" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_show_less_common_skips_gemma(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The ``show_less_common`` chip is purely a frontend toggle —
        backend must NOT call Gemma, NOT call MCP, and MUST return an
        empty response."""
        recorder = _GemmaRecorder()

        def _fail_mcp(*a: Any, **kw: Any) -> Any:
            raise AssertionError("MCP must not be called for show_less_common")

        monkeypatch.setattr(gemma_client, "generate_chat_async", recorder)
        monkeypatch.setattr(mcp_client, "call", _fail_mcp)

        request = _make_chip_request(chip_id="show_less_common", clarifier=None)
        response = await set_your_course.handle_chip_dispatch(request)

        assert recorder.calls == []
        assert response.debug_trace == ""
        assert response.bucket is None
        assert response.updated_resolution is None
        assert response.confirmed_focus is None

    @pytest.mark.asyncio
    async def test_change_major_skips_gemma(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The ``change_major`` chip is also local-only. Same invariant
        as ``show_less_common``."""
        recorder = _GemmaRecorder()

        def _fail_mcp(*a: Any, **kw: Any) -> Any:
            raise AssertionError("MCP must not be called for change_major")

        monkeypatch.setattr(gemma_client, "generate_chat_async", recorder)
        monkeypatch.setattr(mcp_client, "call", _fail_mcp)

        request = _make_chip_request(chip_id="change_major", clarifier=None)
        response = await set_your_course.handle_chip_dispatch(request)

        assert recorder.calls == []
        assert response.debug_trace == ""
        assert response.bucket is None
        assert response.updated_resolution is None
        assert response.confirmed_focus is None

    @pytest.mark.asyncio
    async def test_bucket_tail_parsed_into_response(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A valid ``---BUCKET---`` body is parsed onto the response."""
        monkeypatch.setattr(
            mcp_client, "call", lambda *a, **kw: {"data": []}
        )
        raw = (
            "Prose narration.\n"
            '---BUCKET---\n{"bucket": "crosswalk_mismatch"}'
        )
        monkeypatch.setattr(
            gemma_client, "generate_chat_async", _GemmaRecorder(response=raw)
        )

        response = await set_your_course.handle_chip_dispatch(
            _make_chip_request()
        )
        assert response.bucket == "crosswalk_mismatch"
        assert response.updated_resolution is None

    @pytest.mark.asyncio
    async def test_resolution_tail_parsed_when_present(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An ``---UPDATED_RESOLUTION---`` tail with a valid CIP produces
        an ``IntentResult`` on the response."""
        monkeypatch.setattr(
            mcp_client,
            "call",
            lambda *a, **kw: {"data": [{"occupation_title": "Nurse"}]},
        )
        monkeypatch.setattr(intent, "_derive_parent_cip", lambda cip4, progs: "")
        monkeypatch.setattr(intent, "_get_career_titles_for_cip", lambda cip: [])

        reasoning = "The clarifier mentions a nursing goal."
        raw = (
            "Re-resolving to Nursing.\n"
            '---UPDATED_RESOLUTION---\n'
            '{"matched_cip": "51.3801", "matched_title": "Nursing", '
            f'"confidence": "high", "reasoning": "{reasoning}"'
            "}\n---BUCKET---\n"
            '{"bucket": "semantic_drift"}'
        )
        monkeypatch.setattr(
            gemma_client, "generate_chat_async", _GemmaRecorder(response=raw)
        )

        response = await set_your_course.handle_chip_dispatch(
            _make_chip_request()
        )
        assert response.updated_resolution is not None
        assert response.updated_resolution.matched_cip == "51.3801"
        assert response.updated_resolution.matched_title == "Nursing"
        assert response.bucket == "semantic_drift"

    @pytest.mark.asyncio
    async def test_no_resolution_tail_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without ``---UPDATED_RESOLUTION---`` the field stays None."""
        monkeypatch.setattr(
            mcp_client, "call", lambda *a, **kw: {"data": []}
        )
        raw = (
            "Can't classify.\n"
            '---BUCKET---\n{"bucket": "no_issue_found"}'
        )
        monkeypatch.setattr(
            gemma_client, "generate_chat_async", _GemmaRecorder(response=raw)
        )

        response = await set_your_course.handle_chip_dispatch(
            _make_chip_request()
        )
        assert response.updated_resolution is None
        assert response.bucket == "no_issue_found"

    @pytest.mark.asyncio
    async def test_tool_call_results_get_merged_into_prompt(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The MCP pre-fetch data lands in the user message so Gemma
        grounds on it."""
        monkeypatch.setattr(
            mcp_client,
            "call",
            lambda tool, args: {
                "data": [
                    {
                        "occupation_title": "Speech-Language Pathologist",
                        "soc_code": "29-1127",
                    },
                    {
                        "occupation_title": "Audiologist",
                        "soc_code": "29-1181",
                    },
                ]
            },
        )
        recorder = _GemmaRecorder(
            response='Trace.\n---BUCKET---\n{"bucket": "no_issue_found"}'
        )
        monkeypatch.setattr(
            gemma_client, "generate_chat_async", recorder
        )

        await set_your_course.handle_chip_dispatch(_make_chip_request())

        assert len(recorder.calls) == 1
        user = recorder.calls[0]["messages"][0]["content"]
        assert "Speech-Language Pathologist" in user
        assert "Audiologist" in user
        assert "29-1127" in user

    @pytest.mark.asyncio
    async def test_malformed_tails_are_ignored_no_crash(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Half-written JSON after a tail marker must not crash the
        handler. The tail body is dropped; the prose still lands on
        ``debug_trace``."""
        monkeypatch.setattr(
            mcp_client, "call", lambda *a, **kw: {"data": []}
        )
        raw = (
            "Prose narration.\n"
            "---UPDATED_RESOLUTION---\n"
            '{"matched_cip": "NOT-A-CIP"\n'  # malformed — no closing brace
            "---BUCKET---\n"
            "{not json at all\n"
            "---CONFIRMED_FOCUS---\n"
            '{"confirmed_focus":'  # truncated
        )
        monkeypatch.setattr(
            gemma_client, "generate_chat_async", _GemmaRecorder(response=raw)
        )

        response = await set_your_course.handle_chip_dispatch(
            _make_chip_request()
        )
        assert response.updated_resolution is None
        assert response.bucket is None
        assert response.confirmed_focus is None
        # Prose is retained — we never fail the request on parse errors.
        assert "Prose narration" in response.debug_trace


# ---------------------------------------------------------------------------
# Confirmed Focus invariants
# ---------------------------------------------------------------------------


class TestConfirmedFocus:
    @pytest.mark.asyncio
    async def test_confirmed_focus_tail_parsed_into_response(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A ``---CONFIRMED_FOCUS---`` tail populates the field IF a
        tool call happened AND the bucket allows it."""
        monkeypatch.setattr(
            mcp_client,
            "call",
            lambda *a, **kw: {"data": [{"occupation_title": "Teacher"}]},
        )
        raw = (
            "Confirmed deaf education.\n"
            '---BUCKET---\n{"bucket": "crosswalk_mismatch"}\n'
            '---CONFIRMED_FOCUS---\n{"confirmed_focus": "Deaf Education"}'
        )
        monkeypatch.setattr(
            gemma_client, "generate_chat_async", _GemmaRecorder(response=raw)
        )

        response = await set_your_course.handle_chip_dispatch(
            _make_chip_request()
        )
        assert response.confirmed_focus == "Deaf Education"
        assert response.bucket == "crosswalk_mismatch"

    @pytest.mark.asyncio
    async def test_no_confirmed_focus_tail_leaves_field_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Absence of the tail → confirmed_focus stays None."""
        monkeypatch.setattr(
            mcp_client, "call", lambda *a, **kw: {"data": [{"occupation_title": "X"}]}
        )
        raw = (
            "Trace.\n"
            '---BUCKET---\n{"bucket": "no_issue_found"}'
        )
        monkeypatch.setattr(
            gemma_client, "generate_chat_async", _GemmaRecorder(response=raw)
        )
        response = await set_your_course.handle_chip_dispatch(
            _make_chip_request()
        )
        assert response.confirmed_focus is None

    @pytest.mark.asyncio
    async def test_initial_stream_never_sets_confirmed_focus(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_intent_helpers: None,
    ) -> None:
        """Even if the streamed tail hallucinates a ``confirmed_focus``
        field, ``stream_initial_resolution`` must always emit
        ``confirmed_focus=None`` — the chip flow owns sub-focus."""
        tail = (
            '\n---INTENT_JSON---\n'
            '{"matched_cip": "13.1001", "matched_title": "Special Education", '
            '"confidence": "high", "parent_cip": "13.10", '
            '"confirmed_focus": "Deaf Education", "alternatives": []}'
        )
        chunks = ["Special Ed maps to 13.10.", tail]
        monkeypatch.setattr(
            gemma_client, "generate_stream_async", _stream_from(chunks)
        )

        events: list[dict[str, Any]] = []
        async for event in set_your_course.stream_initial_resolution(
            major_text="deaf ed",
            school_name="IU",
            unitid=151351,
            programs=[],
        ):
            events.append(event)

        structured = next(e for e in events if e["event"] == "structured")
        assert structured["data"]["confirmed_focus"] is None

    @pytest.mark.asyncio
    async def test_confirmed_focus_dropped_when_bucket_is_semantic_drift(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """semantic_drift means the 4-digit resolution CHANGED. A sub-
        focus doesn't carry across that boundary — the service must
        strip it."""
        monkeypatch.setattr(
            mcp_client,
            "call",
            lambda *a, **kw: {"data": [{"occupation_title": "UX Designer"}]},
        )
        monkeypatch.setattr(intent, "_derive_parent_cip", lambda cip4, progs: "")
        monkeypatch.setattr(intent, "_get_career_titles_for_cip", lambda cip: [])
        raw = (
            "Different program.\n"
            "---UPDATED_RESOLUTION---\n"
            '{"matched_cip": "11.0801", "matched_title": "Web Design", '
            '"confidence": "medium"}\n'
            "---BUCKET---\n"
            '{"bucket": "semantic_drift"}\n'
            "---CONFIRMED_FOCUS---\n"
            '{"confirmed_focus": "UX Design"}'
        )
        monkeypatch.setattr(
            gemma_client, "generate_chat_async", _GemmaRecorder(response=raw)
        )

        response = await set_your_course.handle_chip_dispatch(
            _make_chip_request()
        )
        assert response.confirmed_focus is None
        # And the updated_resolution must not carry it either, even
        # though it was parsed from the same response.
        assert response.updated_resolution is not None
        assert response.updated_resolution.confirmed_focus is None

    @pytest.mark.asyncio
    async def test_confirmed_focus_dropped_when_bucket_is_intent_divergence(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Same invariant as semantic_drift — a changing 4-digit scope
        voids any sub-focus."""
        monkeypatch.setattr(
            mcp_client,
            "call",
            lambda *a, **kw: {"data": [{"occupation_title": "Doctor"}]},
        )
        raw = (
            "Major mismatch.\n"
            "---BUCKET---\n"
            '{"bucket": "intent_divergence"}\n'
            "---CONFIRMED_FOCUS---\n"
            '{"confirmed_focus": "Pre-Med"}'
        )
        monkeypatch.setattr(
            gemma_client, "generate_chat_async", _GemmaRecorder(response=raw)
        )

        response = await set_your_course.handle_chip_dispatch(
            _make_chip_request()
        )
        assert response.confirmed_focus is None
        assert response.bucket == "intent_divergence"

    @pytest.mark.asyncio
    async def test_confirmed_focus_requires_tool_call_evidence(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the MCP pre-fetch returned nothing (tool_call_made=False)
        the service MUST strip any confirmed_focus Gemma claims.

        This is the anti-fabrication guard — sub-focus is legitimate
        only when a verification call actually grounded it."""

        # Pre-fetch returns a falsy result — no tool call evidence.
        monkeypatch.setattr(
            mcp_client, "call", lambda *a, **kw: None
        )
        raw = (
            "I think this is deaf ed.\n"
            "---BUCKET---\n"
            '{"bucket": "crosswalk_mismatch"}\n'
            "---CONFIRMED_FOCUS---\n"
            '{"confirmed_focus": "Deaf Education"}'
        )
        monkeypatch.setattr(
            gemma_client, "generate_chat_async", _GemmaRecorder(response=raw)
        )

        response = await set_your_course.handle_chip_dispatch(
            _make_chip_request()
        )
        assert response.confirmed_focus is None
        # Bucket still gets through — only confirmed_focus is guarded.
        assert response.bucket == "crosswalk_mismatch"

    @pytest.mark.asyncio
    async def test_confirmed_focus_strips_numeric_codes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """P1 defense-in-depth: if Gemma leaks a parenthetical CIP code
        into the confirmed_focus value, the service strips it before
        returning. Spec §2 Decision #12 forbids internal codes in
        student-facing prose."""
        monkeypatch.setattr(
            mcp_client,
            "call",
            lambda *a, **kw: {"data": [{"occupation_title": "Teacher"}]},
        )
        raw = (
            "Confirmed.\n"
            "---BUCKET---\n"
            '{"bucket": "crosswalk_mismatch"}\n'
            "---CONFIRMED_FOCUS---\n"
            '{"confirmed_focus": "Deaf Education (13.1003)"}'
        )
        monkeypatch.setattr(
            gemma_client, "generate_chat_async", _GemmaRecorder(response=raw)
        )

        response = await set_your_course.handle_chip_dispatch(
            _make_chip_request()
        )
        assert response.confirmed_focus == "Deaf Education"


# ---------------------------------------------------------------------------
# Observability
# ---------------------------------------------------------------------------


class TestObservability:
    @pytest.mark.asyncio
    async def test_gemma_jsonl_has_call_site_tag(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
        stub_intent_helpers: None,
    ) -> None:
        """Every Gemma call from this service stamps ``call_site``
        onto its JSONL record — either ``set_your_course_resolve`` (for
        the stream path) or ``set_your_course_chip`` + ``chip_id`` (for
        the chip path).

        We replace the sync ``generate_chat`` with a shim that writes
        a JSONL record directly to a tmp file mirroring the real
        log path, so we can assert on the record's shape without
        depending on the OpenAI client."""

        # Re-enable logging and point the log path at tmp.
        monkeypatch.delenv("GEMMA_LOG_DISABLED", raising=False)
        log_path = tmp_path / "gemma.jsonl"
        monkeypatch.setattr(gemma_client, "_log_path", lambda: log_path)
        gemma_client._LOG_PATH_CACHED = None

        # Replace generate_chat_async with a shim that records the
        # extra dict onto the log file the same way the real client
        # would, but without hitting any network.
        async def _fake_chat_async(**kwargs: Any) -> str:
            record = {"response": "trace"}
            if kwargs.get("extra"):
                record.update(kwargs["extra"])
            gemma_client._log_exchange(record)
            return 'Trace.\n---BUCKET---\n{"bucket": "no_issue_found"}'

        monkeypatch.setattr(
            gemma_client, "generate_chat_async", _fake_chat_async
        )
        monkeypatch.setattr(
            mcp_client, "call", lambda *a, **kw: {"data": []}
        )

        await set_your_course.handle_chip_dispatch(_make_chip_request())

        contents = log_path.read_text()
        lines = [
            json.loads(line) for line in contents.splitlines() if line.strip()
        ]
        assert any(
            r.get("call_site") == "set_your_course_chip"
            and r.get("chip_id") == "not_expected"
            for r in lines
        ), f"expected a chip call_site record, got: {lines!r}"
