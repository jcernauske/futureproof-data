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


class _ToolLoopRecorder:
    """Captures ``generate_with_tools_loop`` kwargs and returns a
    configured (text, tool_call_log) tuple."""

    def __init__(
        self,
        response: str = "",
        tool_call_log: list[Any] | None = None,
    ) -> None:
        self.response = response
        self.tool_call_log = tool_call_log or []
        self.calls: list[dict[str, Any]] = []

    async def __call__(self, **kwargs: Any) -> tuple[str, list[Any]]:
        self.calls.append(kwargs)
        return self.response, self.tool_call_log


def _stub_tool_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub mcp_client.get_tool_openai_schema to return a valid schema."""
    monkeypatch.setattr(
        mcp_client,
        "get_tool_openai_schema",
        lambda name: {
            "type": "function",
            "function": {
                "name": "get_career_paths",
                "description": "Returns career outcomes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "unitid": {"type": "integer"},
                        "cipcode": {"type": "string"},
                    },
                    "required": ["unitid", "cipcode"],
                },
            },
        },
    )


def _make_tool_call_turn(
    *,
    turn_number: int = 0,
    tool_name: str = "get_career_paths",
    error: str | None = None,
) -> Any:
    from app.services.gemma_client import ToolCallTurn
    return ToolCallTurn(
        turn_number=turn_number,
        tool_name=tool_name,
        tool_args={"unitid": 151351, "cipcode": "52.1401"},
        tool_result_size_bytes=500,
        duration_ms=100,
        error=error,
    )


class TestChipDispatch:
    @pytest.mark.asyncio
    async def test_not_expected_runs_gemma_with_tools(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """handle_chip_dispatch invokes generate_with_tools_loop with the
        get_career_paths schema in the tool catalog."""
        _stub_tool_schema(monkeypatch)
        recorder = _ToolLoopRecorder(
            response='Trace.\n---BUCKET---\n{"bucket": "no_issue_found"}',
            tool_call_log=[_make_tool_call_turn()],
        )
        monkeypatch.setattr(
            gemma_client, "generate_with_tools_loop", recorder
        )

        request = _make_chip_request(
            clarifier="I wanted marketing-manager jobs, not general business."
        )
        response = await set_your_course.handle_chip_dispatch(request)

        assert len(recorder.calls) == 1
        call = recorder.calls[0]
        assert "I wanted marketing-manager jobs" in call["system"]
        assert "Indiana University" in call["system"]
        assert len(call["tools"]) == 1
        assert call["tools"][0]["function"]["name"] == "get_career_paths"
        assert response.bucket == "no_issue_found"

    @pytest.mark.asyncio
    async def test_not_expected_without_clarifier_422(self) -> None:
        """Pydantic's ``@model_validator`` on ChipRequest rejects a
        ``not_expected`` request with an empty/null clarifier."""
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
                clarifier="   ",
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
        """The ``show_less_common`` chip is purely a frontend toggle."""
        recorder = _ToolLoopRecorder()
        monkeypatch.setattr(gemma_client, "generate_with_tools_loop", recorder)

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
        """The ``change_major`` chip is also local-only."""
        recorder = _ToolLoopRecorder()
        monkeypatch.setattr(gemma_client, "generate_with_tools_loop", recorder)

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
        _stub_tool_schema(monkeypatch)
        raw = (
            "Prose narration.\n"
            '---BUCKET---\n{"bucket": "crosswalk_mismatch"}'
        )
        monkeypatch.setattr(
            gemma_client,
            "generate_with_tools_loop",
            _ToolLoopRecorder(response=raw, tool_call_log=[_make_tool_call_turn()]),
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
        _stub_tool_schema(monkeypatch)
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
            gemma_client,
            "generate_with_tools_loop",
            _ToolLoopRecorder(response=raw, tool_call_log=[_make_tool_call_turn()]),
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
        _stub_tool_schema(monkeypatch)
        raw = (
            "Can't classify.\n"
            '---BUCKET---\n{"bucket": "no_issue_found"}'
        )
        monkeypatch.setattr(
            gemma_client,
            "generate_with_tools_loop",
            _ToolLoopRecorder(response=raw),
        )

        response = await set_your_course.handle_chip_dispatch(
            _make_chip_request()
        )
        assert response.updated_resolution is None
        assert response.bucket == "no_issue_found"

    @pytest.mark.asyncio
    async def test_tool_call_made_true_when_loop_dispatched(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """tool_call_made is True when the loop dispatched a tool."""
        _stub_tool_schema(monkeypatch)
        raw = (
            "Confirmed deaf education.\n"
            '---BUCKET---\n{"bucket": "crosswalk_mismatch"}\n'
            '---CONFIRMED_FOCUS---\n{"confirmed_focus": "Deaf Education"}'
        )
        monkeypatch.setattr(
            gemma_client,
            "generate_with_tools_loop",
            _ToolLoopRecorder(
                response=raw,
                tool_call_log=[_make_tool_call_turn()],
            ),
        )
        response = await set_your_course.handle_chip_dispatch(
            _make_chip_request()
        )
        assert response.confirmed_focus == "Deaf Education"

    @pytest.mark.asyncio
    async def test_malformed_tails_are_ignored_no_crash(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Half-written JSON after a tail marker must not crash."""
        _stub_tool_schema(monkeypatch)
        raw = (
            "Prose narration.\n"
            "---UPDATED_RESOLUTION---\n"
            '{"matched_cip": "NOT-A-CIP"\n'
            "---BUCKET---\n"
            "{not json at all\n"
            "---CONFIRMED_FOCUS---\n"
            '{"confirmed_focus":'
        )
        monkeypatch.setattr(
            gemma_client,
            "generate_with_tools_loop",
            _ToolLoopRecorder(response=raw),
        )

        response = await set_your_course.handle_chip_dispatch(
            _make_chip_request()
        )
        assert response.updated_resolution is None
        assert response.bucket is None
        assert response.confirmed_focus is None
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
        _stub_tool_schema(monkeypatch)
        raw = (
            "Confirmed deaf education.\n"
            '---BUCKET---\n{"bucket": "crosswalk_mismatch"}\n'
            '---CONFIRMED_FOCUS---\n{"confirmed_focus": "Deaf Education"}'
        )
        monkeypatch.setattr(
            gemma_client,
            "generate_with_tools_loop",
            _ToolLoopRecorder(
                response=raw,
                tool_call_log=[_make_tool_call_turn()],
            ),
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
        _stub_tool_schema(monkeypatch)
        raw = (
            "Trace.\n"
            '---BUCKET---\n{"bucket": "no_issue_found"}'
        )
        monkeypatch.setattr(
            gemma_client,
            "generate_with_tools_loop",
            _ToolLoopRecorder(
                response=raw,
                tool_call_log=[_make_tool_call_turn()],
            ),
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
        """semantic_drift means the resolution CHANGED. Sub-focus
        doesn't carry across that boundary."""
        _stub_tool_schema(monkeypatch)
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
            gemma_client,
            "generate_with_tools_loop",
            _ToolLoopRecorder(
                response=raw,
                tool_call_log=[_make_tool_call_turn()],
            ),
        )

        response = await set_your_course.handle_chip_dispatch(
            _make_chip_request()
        )
        assert response.confirmed_focus is None
        assert response.updated_resolution is not None
        assert response.updated_resolution.confirmed_focus is None

    @pytest.mark.asyncio
    async def test_confirmed_focus_dropped_when_bucket_is_intent_divergence(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Same invariant as semantic_drift."""
        _stub_tool_schema(monkeypatch)
        raw = (
            "Major mismatch.\n"
            "---BUCKET---\n"
            '{"bucket": "intent_divergence"}\n'
            "---CONFIRMED_FOCUS---\n"
            '{"confirmed_focus": "Pre-Med"}'
        )
        monkeypatch.setattr(
            gemma_client,
            "generate_with_tools_loop",
            _ToolLoopRecorder(
                response=raw,
                tool_call_log=[_make_tool_call_turn()],
            ),
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
        """When no tool call was dispatched (tool_call_log empty),
        the service MUST strip any confirmed_focus Gemma claims."""
        _stub_tool_schema(monkeypatch)
        raw = (
            "I think this is deaf ed.\n"
            "---BUCKET---\n"
            '{"bucket": "crosswalk_mismatch"}\n'
            "---CONFIRMED_FOCUS---\n"
            '{"confirmed_focus": "Deaf Education"}'
        )
        # Empty tool_call_log = no tool call evidence
        monkeypatch.setattr(
            gemma_client,
            "generate_with_tools_loop",
            _ToolLoopRecorder(response=raw, tool_call_log=[]),
        )

        response = await set_your_course.handle_chip_dispatch(
            _make_chip_request()
        )
        assert response.confirmed_focus is None
        assert response.bucket == "crosswalk_mismatch"

    @pytest.mark.asyncio
    async def test_confirmed_focus_strips_numeric_codes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Gemma leaking a CIP code into confirmed_focus gets stripped."""
        _stub_tool_schema(monkeypatch)
        raw = (
            "Confirmed.\n"
            "---BUCKET---\n"
            '{"bucket": "crosswalk_mismatch"}\n'
            "---CONFIRMED_FOCUS---\n"
            '{"confirmed_focus": "Deaf Education (13.1003)"}'
        )
        monkeypatch.setattr(
            gemma_client,
            "generate_with_tools_loop",
            _ToolLoopRecorder(
                response=raw,
                tool_call_log=[_make_tool_call_turn()],
            ),
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
        """The chip dispatch passes call_site to generate_with_tools_loop
        via the extra dict."""
        _stub_tool_schema(monkeypatch)

        captured_extra: list[dict[str, Any]] = []

        async def _fake_loop(**kwargs: Any) -> tuple[str, list[Any]]:
            if kwargs.get("extra"):
                captured_extra.append(kwargs["extra"])
            return 'Trace.\n---BUCKET---\n{"bucket": "no_issue_found"}', []

        monkeypatch.setattr(
            gemma_client, "generate_with_tools_loop", _fake_loop
        )

        await set_your_course.handle_chip_dispatch(_make_chip_request())

        assert len(captured_extra) == 1
        assert captured_extra[0]["call_site"] == "chip_dispatch_tool_call"
        assert captured_extra[0]["chip_id"] == "not_expected"


# ---------------------------------------------------------------------------
# Intent-aware fields: _parse_intent_keywords + _merge_confirmed_focus
# ---------------------------------------------------------------------------


class TestParseIntentKeywords:
    """Direct tests on the pure ``_parse_intent_keywords`` function.

    This function sanitizes the raw JSON value Gemma returns for
    ``intent_keywords``. It must handle: list of strings (happy),
    string (malformed), null/None, list with non-string elements,
    and empty list.
    """

    def test_valid_list_of_strings(self):
        result = set_your_course._parse_intent_keywords(
            ["pre-med", "doctor", "physician"]
        )
        assert result == ["pre-med", "doctor", "physician"]

    def test_lowercases_and_strips(self):
        result = set_your_course._parse_intent_keywords(
            ["  Pre-Med ", "DOCTOR"]
        )
        assert result == ["pre-med", "doctor"]

    def test_string_instead_of_list_returns_empty(self):
        """Gemma sometimes emits a bare string instead of a list."""
        result = set_your_course._parse_intent_keywords("pre-med")
        assert result == []

    def test_null_returns_empty(self):
        result = set_your_course._parse_intent_keywords(None)
        assert result == []

    def test_integer_returns_empty(self):
        result = set_your_course._parse_intent_keywords(42)
        assert result == []

    def test_list_with_non_string_elements_filters_them(self):
        """Non-string items in the list are silently dropped."""
        result = set_your_course._parse_intent_keywords(
            ["pre-med", 42, None, "doctor", True, ""]
        )
        # 42, None, True are not str; "" is str but empty after strip
        assert result == ["pre-med", "doctor"]

    def test_empty_list_returns_empty(self):
        result = set_your_course._parse_intent_keywords([])
        assert result == []

    def test_whitespace_only_strings_dropped(self):
        result = set_your_course._parse_intent_keywords(["  ", "\t", "valid"])
        assert result == ["valid"]


class TestMergeConfirmedFocusIntoKeywords:
    """Direct tests on ``_merge_confirmed_focus_into_keywords``.

    This function appends lowercased confirmed_focus to intent_keywords
    when it's not already present. It must handle: None confirmed_focus,
    empty string, already-present token, and normal append.
    """

    def test_no_confirmed_focus_returns_unchanged(self):
        ir = IntentResult(
            matched_cip="13.1001",
            matched_title="Special Ed",
            confidence="high",
            intent_keywords=["teacher"],
        )
        result = set_your_course._merge_confirmed_focus_into_keywords(ir)
        assert result.intent_keywords == ["teacher"]

    def test_confirmed_focus_appended_lowercased(self):
        ir = IntentResult(
            matched_cip="13.1001",
            matched_title="Special Ed",
            confidence="high",
            intent_keywords=["teacher"],
            confirmed_focus="Deaf Education",
        )
        result = set_your_course._merge_confirmed_focus_into_keywords(ir)
        assert result.intent_keywords == ["teacher", "deaf education"]

    def test_confirmed_focus_deduped(self):
        """If the token is already in intent_keywords, don't add it again."""
        ir = IntentResult(
            matched_cip="13.1001",
            matched_title="Special Ed",
            confidence="high",
            intent_keywords=["deaf education", "teacher"],
            confirmed_focus="Deaf Education",
        )
        result = set_your_course._merge_confirmed_focus_into_keywords(ir)
        assert result.intent_keywords == ["deaf education", "teacher"]
        assert result.intent_keywords.count("deaf education") == 1

    def test_empty_confirmed_focus_returns_unchanged(self):
        ir = IntentResult(
            matched_cip="13.1001",
            matched_title="Special Ed",
            confidence="high",
            intent_keywords=["teacher"],
            confirmed_focus="",
        )
        result = set_your_course._merge_confirmed_focus_into_keywords(ir)
        assert result.intent_keywords == ["teacher"]

    def test_whitespace_only_confirmed_focus_returns_unchanged(self):
        ir = IntentResult(
            matched_cip="13.1001",
            matched_title="Special Ed",
            confidence="high",
            intent_keywords=[],
            confirmed_focus="   ",
        )
        result = set_your_course._merge_confirmed_focus_into_keywords(ir)
        assert result.intent_keywords == []

    def test_original_intent_result_not_mutated(self):
        """_merge returns a new IntentResult via model_copy; the
        original must remain untouched."""
        ir = IntentResult(
            matched_cip="13.1001",
            matched_title="Special Ed",
            confidence="high",
            intent_keywords=["teacher"],
            confirmed_focus="Deaf Education",
        )
        result = set_your_course._merge_confirmed_focus_into_keywords(ir)
        assert ir.intent_keywords == ["teacher"]  # original unchanged
        assert result.intent_keywords == ["teacher", "deaf education"]


# ---------------------------------------------------------------------------
# Intent-aware resolver tail parsing (P0)
# ---------------------------------------------------------------------------


class TestResolverIntentKeywords:
    """Verify that ``_build_intent_result_from_tail`` correctly parses
    ``intent_keywords`` and ``student_major_text`` from the Gemma JSON
    tail — and handles all the malformed / missing variations."""

    def test_resolver_emits_intent_keywords_when_present(self):
        """Happy path: Gemma JSON tail includes intent_keywords list."""
        parsed = {
            "matched_cip": "26.0101",
            "matched_title": "Biology",
            "confidence": "high",
            "parent_cip": "26.01",
            "alternatives": [],
            "intent_keywords": ["pre-med", "doctor", "physician"],
        }
        result = set_your_course._build_intent_result_from_tail(
            major_text="biology pre-med",
            prose="Biology program.",
            parsed=parsed,
            school_cips=[{"cipcode": "26.0101", "program_name": "Biology"}],
            programs=[],
        )
        assert result.intent_keywords == ["pre-med", "doctor", "physician"]
        assert result.student_major_text == "biology pre-med"

    def test_resolver_back_compat_missing_intent_keywords(self):
        """Gemma response WITHOUT intent_keywords key falls back to []."""
        parsed = {
            "matched_cip": "52.1401",
            "matched_title": "Marketing",
            "confidence": "high",
            "parent_cip": "52.14",
            "alternatives": [],
            # No intent_keywords key at all
        }
        result = set_your_course._build_intent_result_from_tail(
            major_text="marketing",
            prose="Marketing.",
            parsed=parsed,
            school_cips=[{"cipcode": "52.1401", "program_name": "Marketing"}],
            programs=[],
        )
        assert result.intent_keywords == []
        assert result.student_major_text == "marketing"

    def test_resolver_intent_keywords_string_falls_back_to_empty(self):
        """Gemma returns a string instead of a list → []."""
        parsed = {
            "matched_cip": "26.0101",
            "matched_title": "Biology",
            "confidence": "high",
            "parent_cip": "26.01",
            "alternatives": [],
            "intent_keywords": "pre-med",  # string, not list
        }
        result = set_your_course._build_intent_result_from_tail(
            major_text="biology pre-med",
            prose="Biology.",
            parsed=parsed,
            school_cips=[{"cipcode": "26.0101", "program_name": "Biology"}],
            programs=[],
        )
        assert result.intent_keywords == []

    def test_resolver_intent_keywords_null_falls_back_to_empty(self):
        """Gemma returns null for intent_keywords → []."""
        parsed = {
            "matched_cip": "26.0101",
            "matched_title": "Biology",
            "confidence": "high",
            "parent_cip": "26.01",
            "alternatives": [],
            "intent_keywords": None,
        }
        result = set_your_course._build_intent_result_from_tail(
            major_text="biology pre-med",
            prose="Biology.",
            parsed=parsed,
            school_cips=[{"cipcode": "26.0101", "program_name": "Biology"}],
            programs=[],
        )
        assert result.intent_keywords == []

    def test_resolver_extracts_intent_for_deaf_ed(self):
        """The deaf-ed scenario: Gemma emits sub-specialty keywords for
        a specific niche inside a broader CIP."""
        parsed = {
            "matched_cip": "13.1001",
            "matched_title": "Special Education and Teaching, General",
            "confidence": "high",
            "parent_cip": "13.10",
            "alternatives": [],
            "intent_keywords": ["deaf education", "special education", "teacher"],
        }
        result = set_your_course._build_intent_result_from_tail(
            major_text="deaf ed",
            prose="Special Education.",
            parsed=parsed,
            school_cips=[
                {"cipcode": "13.1001", "program_name": "Special Education"}
            ],
            programs=[],
        )
        assert result.intent_keywords == [
            "deaf education",
            "special education",
            "teacher",
        ]
        assert result.student_major_text == "deaf ed"

    def test_student_major_text_set_on_fallback_path(self):
        """When parsed is None (unparseable tail), student_major_text
        should still be set on the fallback IntentResult."""
        result = set_your_course._build_intent_result_from_tail(
            major_text="deaf ed",
            prose="",
            parsed=None,
            school_cips=[],
            programs=[],
        )
        assert result.student_major_text == "deaf ed"
        assert result.intent_keywords == []
        assert result.confidence == "low"

    def test_student_major_text_set_on_malformed_cip_path(self):
        """When matched_cip is malformed, the low-confidence degraded
        result should still carry student_major_text and intent_keywords."""
        parsed = {
            "matched_cip": "NOTACIP",
            "matched_title": "Biology",
            "confidence": "high",
            "parent_cip": "26.01",
            "alternatives": [],
            "intent_keywords": ["pre-med"],
        }
        result = set_your_course._build_intent_result_from_tail(
            major_text="biology pre-med",
            prose="Biology.",
            parsed=parsed,
            school_cips=[],
            programs=[],
        )
        assert result.student_major_text == "biology pre-med"
        assert result.intent_keywords == ["pre-med"]
        assert result.confidence == "low"


# ---------------------------------------------------------------------------
# Chip flow: confirmed_focus → intent_keywords merge (P0)
# ---------------------------------------------------------------------------


class TestChipFlowIntentKeywords:
    @pytest.mark.asyncio
    async def test_confirmed_focus_populates_intent_keywords(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the chip flow confirms a sub-specialty,
        ``_merge_confirmed_focus_into_keywords`` appends the lowercased
        token to intent_keywords."""
        _stub_tool_schema(monkeypatch)
        monkeypatch.setattr(intent, "_derive_parent_cip", lambda cip4, progs: "")
        monkeypatch.setattr(intent, "_get_career_titles_for_cip", lambda cip: [])

        raw = (
            "Confirmed deaf education path.\n"
            "---UPDATED_RESOLUTION---\n"
            '{"matched_cip": "13.1001", "matched_title": "Special Education", '
            '"confidence": "high", "reasoning": "Confirmed sub-focus."}\n'
            "---BUCKET---\n"
            '{"bucket": "crosswalk_mismatch"}\n'
            "---CONFIRMED_FOCUS---\n"
            '{"confirmed_focus": "Deaf Education"}'
        )
        monkeypatch.setattr(
            gemma_client,
            "generate_with_tools_loop",
            _ToolLoopRecorder(
                response=raw,
                tool_call_log=[_make_tool_call_turn()],
            ),
        )

        current = _make_current_resolution(
            matched_cip="13.1001",
            matched_title="Special Education",
            student_major_text="deaf ed",
            intent_keywords=["special education", "teacher"],
        )
        request = _make_chip_request(
            clarifier="I want deaf education specifically.",
            current=current,
        )
        response = await set_your_course.handle_chip_dispatch(request)

        assert response.confirmed_focus == "Deaf Education"
        assert response.updated_resolution is not None
        assert response.updated_resolution.confirmed_focus == "Deaf Education"
        assert "deaf education" in response.updated_resolution.intent_keywords

    @pytest.mark.asyncio
    async def test_chip_flow_carries_forward_intent_fields(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``_parse_updated_resolution`` copies student_major_text and
        intent_keywords from the request's current_resolution."""
        _stub_tool_schema(monkeypatch)
        monkeypatch.setattr(intent, "_derive_parent_cip", lambda cip4, progs: "")
        monkeypatch.setattr(intent, "_get_career_titles_for_cip", lambda cip: [])

        raw = (
            "Re-resolving.\n"
            "---UPDATED_RESOLUTION---\n"
            '{"matched_cip": "52.1401", "matched_title": "Marketing", '
            '"confidence": "high", "reasoning": "Narrowed."}\n'
            "---BUCKET---\n"
            '{"bucket": "crosswalk_mismatch"}'
        )
        monkeypatch.setattr(
            gemma_client,
            "generate_with_tools_loop",
            _ToolLoopRecorder(
                response=raw,
                tool_call_log=[_make_tool_call_turn()],
            ),
        )

        current = _make_current_resolution(
            student_major_text="marketing analytics",
            intent_keywords=["analytics", "data"],
        )
        request = _make_chip_request(
            clarifier="I want marketing analytics roles.",
            current=current,
        )
        response = await set_your_course.handle_chip_dispatch(request)

        assert response.updated_resolution is not None
        assert response.updated_resolution.student_major_text == "marketing analytics"
        assert response.updated_resolution.intent_keywords == ["analytics", "data"]


# ---------------------------------------------------------------------------
# Multi-CIP resolution (feature-multi-cip-resolution §4)
# ---------------------------------------------------------------------------


class TestMultiCipResolution:
    """Tests for the multi-CIP resolution feature.

    The streaming prompt now asks Gemma for up to 3 ranked CIP matches.
    ``_build_intent_result_from_tail`` parses the ``alternatives`` array,
    ``remaining_count``, and ``narrowing_hint`` from the JSON tail.
    ``_fallback_resolve`` also supports multi-CIP.
    """

    def test_stream_multi_cip_parses_3_ranked_options(
        self,
        stub_intent_helpers: None,
    ) -> None:
        """Mocked Gemma response with 3 CIPs -> IntentResult has primary
        + 2 alternatives with correct fields (cip, title, why, parent_cip)."""
        parsed = {
            "matched_cip": "14.0901",
            "matched_title": "Computer Engineering, General",
            "confidence": "high",
            "parent_cip": "14.09",
            "alternatives": [
                {
                    "cip": "14.1001",
                    "title": "Electrical Engineering",
                    "why": "Also covers circuits",
                    "parent_cip": "14.10",
                },
                {
                    "cip": "14.1901",
                    "title": "Mechanical Engineering",
                    "why": "Physical systems",
                    "parent_cip": "14.19",
                },
            ],
            "remaining_count": 11,
            "narrowing_hint": "Try 'civil engineering'",
            "intent_keywords": ["engineering"],
        }
        result = set_your_course._build_intent_result_from_tail(
            major_text="engineering",
            prose="Engineering program.",
            parsed=parsed,
            school_cips=[
                {"cipcode": "14.0901", "program_name": "Computer Engineering"},
            ],
            programs=[],
        )
        assert result.matched_cip == "14.0901"
        assert result.matched_title == "Computer Engineering, General"
        assert result.alternatives is not None
        assert len(result.alternatives) == 2
        assert result.alternatives[0]["cip"] == "14.1001"
        assert result.alternatives[0]["title"] == "Electrical Engineering"
        assert result.alternatives[0]["why"] == "Also covers circuits"
        assert result.alternatives[0]["parent_cip"] == "14.10"
        assert result.alternatives[1]["cip"] == "14.1901"
        assert result.alternatives[1]["title"] == "Mechanical Engineering"

    def test_stream_single_cip_no_alternatives(
        self,
        stub_intent_helpers: None,
    ) -> None:
        """Mocked Gemma response with 1 CIP -> alternatives is empty/None,
        remaining_count is 0."""
        parsed = {
            "matched_cip": "51.3801",
            "matched_title": "Registered Nursing",
            "confidence": "high",
            "parent_cip": "51.38",
            "alternatives": [],
            "remaining_count": 0,
            "narrowing_hint": "",
            "intent_keywords": ["nursing"],
        }
        result = set_your_course._build_intent_result_from_tail(
            major_text="nursing",
            prose="Nursing program.",
            parsed=parsed,
            school_cips=[{"cipcode": "51.3801", "program_name": "Nursing"}],
            programs=[],
        )
        assert result.matched_cip == "51.3801"
        # Empty list after sanitization — the sanitizer returns [] (not None)
        # when the input was a valid but empty list.
        assert result.alternatives == []
        assert result.remaining_count == 0
        assert result.narrowing_hint == ""

    def test_stream_multi_cip_validates_all_against_crosswalk(
        self,
        stub_intent_helpers: None,
    ) -> None:
        """Gemma returns 3 CIPs, one invalid -> only valid alternatives survive.

        The sanitizer inside _build_intent_result_from_tail runs
        _sanitize_alternatives which regex-gates every alternative CIP.
        An invalid CIP code (e.g., "INVALID") must be silently dropped.
        """
        parsed = {
            "matched_cip": "14.0901",
            "matched_title": "Computer Engineering",
            "confidence": "high",
            "parent_cip": "14.09",
            "alternatives": [
                {
                    "cip": "14.1001",
                    "title": "Electrical Engineering",
                    "why": "Circuits",
                    "parent_cip": "14.10",
                },
                {
                    "cip": "INVALID",
                    "title": "Fake Program",
                    "why": "Dropped",
                    "parent_cip": "99.99",
                },
            ],
            "remaining_count": 5,
            "narrowing_hint": "Try mechanical",
            "intent_keywords": ["engineering"],
        }
        result = set_your_course._build_intent_result_from_tail(
            major_text="engineering",
            prose="Engineering.",
            parsed=parsed,
            school_cips=[
                {"cipcode": "14.0901", "program_name": "Computer Engineering"},
            ],
            programs=[],
        )
        assert result.alternatives is not None
        assert len(result.alternatives) == 1
        assert result.alternatives[0]["cip"] == "14.1001"
        # The invalid "INVALID" CIP was dropped entirely.

    @pytest.mark.asyncio
    async def test_fallback_multi_cip(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_intent_helpers: None,
    ) -> None:
        """_fallback_resolve with multi-CIP response -> same validation
        and population of alternatives/remaining_count/narrowing_hint."""
        fallback_response = (
            '{"matched_cip": "14.0901", "matched_title": "Computer Engineering", '
            '"confidence": "high", "parent_cip": "14.09", '
            '"alternatives": ['
            '{"cip": "14.1001", "title": "Electrical Engineering", '
            '"why": "Circuits", "parent_cip": "14.10"}, '
            '{"cip": "14.1901", "title": "Mechanical Engineering", '
            '"why": "Physical systems", "parent_cip": "14.19"}'
            '], "remaining_count": 8, '
            '"narrowing_hint": "Try civil engineering", '
            '"intent_keywords": ["engineering"]}'
        )
        monkeypatch.setattr(
            gemma_client,
            "generate",
            lambda **kwargs: fallback_response,
        )
        school_cips = [
            {"cipcode": "14.0901", "program_name": "Computer Engineering"},
        ]
        result = set_your_course._fallback_resolve(
            "engineering", school_cips, programs=[]
        )
        assert result is not None
        assert result.matched_cip == "14.0901"
        assert result.alternatives is not None
        assert len(result.alternatives) == 2
        assert result.alternatives[0]["cip"] == "14.1001"
        assert result.alternatives[1]["cip"] == "14.1901"
        assert result.remaining_count == 8
        assert result.narrowing_hint == "Try civil engineering"

    def test_stream_multi_cip_remaining_count_and_hint(
        self,
        stub_intent_helpers: None,
    ) -> None:
        """remaining_count and narrowing_hint are correctly extracted from
        the Gemma response and populated on IntentResult."""
        parsed = {
            "matched_cip": "14.0901",
            "matched_title": "Computer Engineering",
            "confidence": "high",
            "parent_cip": "14.09",
            "alternatives": [
                {
                    "cip": "14.1001",
                    "title": "Electrical Engineering",
                    "why": "Circuits",
                    "parent_cip": "14.10",
                },
            ],
            "remaining_count": 11,
            "narrowing_hint": "Try 'civil engineering' or 'aerospace'",
            "intent_keywords": ["engineering"],
        }
        result = set_your_course._build_intent_result_from_tail(
            major_text="engineering",
            prose="Engineering.",
            parsed=parsed,
            school_cips=[
                {"cipcode": "14.0901", "program_name": "Computer Engineering"},
            ],
            programs=[],
        )
        assert result.remaining_count == 11
        assert result.narrowing_hint == "Try 'civil engineering' or 'aerospace'"

    def test_stream_multi_cip_deduplicates_primary(
        self,
        stub_intent_helpers: None,
    ) -> None:
        """If Gemma echoes the primary CIP in alternatives, the sanitizer
        drops it — student must not see the same program twice."""
        parsed = {
            "matched_cip": "14.0901",
            "matched_title": "Computer Engineering",
            "confidence": "high",
            "parent_cip": "14.09",
            "alternatives": [
                {
                    "cip": "14.0901",
                    "title": "Computer Engineering (echo)",
                    "why": "Same as primary",
                    "parent_cip": "14.09",
                },
                {
                    "cip": "14.1001",
                    "title": "Electrical Engineering",
                    "why": "Circuits",
                    "parent_cip": "14.10",
                },
            ],
            "remaining_count": 0,
            "narrowing_hint": "",
            "intent_keywords": ["engineering"],
        }
        result = set_your_course._build_intent_result_from_tail(
            major_text="engineering",
            prose="Engineering.",
            parsed=parsed,
            school_cips=[
                {"cipcode": "14.0901", "program_name": "Computer Engineering"},
            ],
            programs=[],
        )
        assert result.alternatives is not None
        assert len(result.alternatives) == 1
        assert result.alternatives[0]["cip"] == "14.1001"
