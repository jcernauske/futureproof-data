"""Tests for the chip dispatch tool-calling loop.

Covers the new generate_with_tools_loop integration in handle_chip_dispatch:
- Loop dispatches a tool call and returns final text
- No tool call returns directly
- Loop cap returns failure chip
- Malformed tool call returns failure chip
- Dispatch error returns failure chip
- confirmed_focus only when tool_call_made
- show_less_common/change_major short-circuit
"""

from __future__ import annotations

from typing import Any

import pytest

from app.models.api import ChipRequest
from app.models.career import IntentResult
from app.services import gemma_client, mcp_client, set_your_course
from app.services.gemma_client import ToolCallTurn


@pytest.fixture(autouse=True)
def _disable_gemma_jsonl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMMA_LOG_DISABLED", "1")


@pytest.fixture(autouse=True)
def _stub_gemma_config(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Cfg:
        model = "stub-model"
        backend = "stub"

    monkeypatch.setattr(
        set_your_course.gemma_client, "current_config", lambda: _Cfg()
    )


_FAKE_TOOL_SCHEMAS: dict[str, dict] = {
    "get_career_paths": {
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
    "get_occupation_education_requirements": {
        "type": "function",
        "function": {
            "name": "get_occupation_education_requirements",
            "description": "Returns education requirements.",
            "parameters": {
                "type": "object",
                "properties": {
                    "soc_code": {"type": "string"},
                },
                "required": ["soc_code"],
            },
        },
    },
}


def _stub_tool_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        mcp_client,
        "get_tool_openai_schema",
        lambda name: _FAKE_TOOL_SCHEMAS.get(name),
    )


def _make_resolution(**overrides: Any) -> IntentResult:
    defaults: dict[str, Any] = {
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
    defaults.update(overrides)
    return IntentResult(**defaults)


def _make_request(
    *,
    chip_id: str = "not_expected",
    clarifier: str | None = "I want marketing-manager jobs.",
    current: IntentResult | None = None,
) -> ChipRequest:
    return ChipRequest(
        chip_id=chip_id,
        clarifier=clarifier,
        current_resolution=current or _make_resolution(),
        initial_resolution=_make_resolution(),
        school_name="Indiana University",
        unitid=151351,
        programs=[],
    )


def _make_turn(
    *,
    turn: int = 0,
    error: str | None = None,
) -> ToolCallTurn:
    return ToolCallTurn(
        turn_number=turn,
        tool_name="get_career_paths",
        tool_args={"unitid": 151351, "cipcode": "52.1401"},
        tool_result_size_bytes=500,
        duration_ms=100,
        error=error,
    )


class TestChipDispatchToolLoop:
    @pytest.mark.asyncio
    async def test_chip_dispatch_calls_gemma_with_tools(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """handle_chip_dispatch invokes generate_with_tools_loop with
        the get_career_paths schema in the tool catalog."""
        _stub_tool_schema(monkeypatch)
        captured: list[dict[str, Any]] = []

        async def _fake_loop(**kwargs: Any) -> tuple[str, list[ToolCallTurn]]:
            captured.append(kwargs)
            return 'Trace.\n---BUCKET---\n{"bucket": "no_issue_found"}', [_make_turn()]

        monkeypatch.setattr(gemma_client, "generate_with_tools_loop", _fake_loop)

        await set_your_course.handle_chip_dispatch(_make_request())

        assert len(captured) == 1
        assert len(captured[0]["tools"]) == 2
        tool_names = {t["function"]["name"] for t in captured[0]["tools"]}
        assert "get_career_paths" in tool_names
        assert "get_occupation_education_requirements" in tool_names
        assert captured[0]["max_turns"] == 3
        assert captured[0]["max_wall_time_s"] == 30.0

    @pytest.mark.asyncio
    async def test_chip_dispatch_loops_on_tool_call(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the loop dispatches a tool and returns final text, the
        response is parsed correctly with tool_call_made=True."""
        _stub_tool_schema(monkeypatch)
        raw = (
            "Confirmed deaf education.\n"
            '---BUCKET---\n{"bucket": "crosswalk_mismatch"}\n'
            '---CONFIRMED_FOCUS---\n{"confirmed_focus": "Deaf Education"}'
        )

        async def _fake_loop(**kwargs: Any) -> tuple[str, list[ToolCallTurn]]:
            return raw, [_make_turn()]

        monkeypatch.setattr(gemma_client, "generate_with_tools_loop", _fake_loop)
        response = await set_your_course.handle_chip_dispatch(_make_request())

        assert response.bucket == "crosswalk_mismatch"
        assert response.confirmed_focus == "Deaf Education"

    @pytest.mark.asyncio
    async def test_chip_dispatch_no_tool_call_returns_directly(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When Gemma returns plain text on turn 1 (no tool call),
        tool_call_made is False."""
        _stub_tool_schema(monkeypatch)
        raw = (
            "No data lookup needed.\n"
            '---BUCKET---\n{"bucket": "no_issue_found"}\n'
            '---CONFIRMED_FOCUS---\n{"confirmed_focus": "Deaf Education"}'
        )

        async def _fake_loop(**kwargs: Any) -> tuple[str, list[ToolCallTurn]]:
            return raw, []  # empty log = no tool call

        monkeypatch.setattr(gemma_client, "generate_with_tools_loop", _fake_loop)
        response = await set_your_course.handle_chip_dispatch(_make_request())

        assert response.bucket == "no_issue_found"
        # confirmed_focus stripped because no tool call evidence
        assert response.confirmed_focus is None

    @pytest.mark.asyncio
    async def test_chip_dispatch_loop_cap_returns_failure_chip(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the loop hits the turn cap and returns empty text,
        the failure chip is returned."""
        _stub_tool_schema(monkeypatch)

        async def _fake_loop(**kwargs: Any) -> tuple[str, list[ToolCallTurn]]:
            # Simulate cap hit — empty text, multiple turns
            return "", [_make_turn(turn=0), _make_turn(turn=1), _make_turn(turn=2)]

        monkeypatch.setattr(gemma_client, "generate_with_tools_loop", _fake_loop)
        response = await set_your_course.handle_chip_dispatch(_make_request())

        assert response.debug_trace == set_your_course._TRANSPORT_FAILURE_MESSAGE
        assert response.bucket is None
        assert response.updated_resolution is None

    @pytest.mark.asyncio
    async def test_chip_dispatch_wall_time_cap(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Wall time cap hit returns failure chip."""
        _stub_tool_schema(monkeypatch)

        async def _fake_loop(**kwargs: Any) -> tuple[str, list[ToolCallTurn]]:
            return "", [_make_turn(turn=0)]

        monkeypatch.setattr(gemma_client, "generate_with_tools_loop", _fake_loop)
        response = await set_your_course.handle_chip_dispatch(_make_request())

        assert response.debug_trace == set_your_course._TRANSPORT_FAILURE_MESSAGE

    @pytest.mark.asyncio
    async def test_chip_dispatch_malformed_tool_call_returns_failure_chip(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When a tool call has an error, the failure chip is returned."""
        _stub_tool_schema(monkeypatch)

        async def _fake_loop(**kwargs: Any) -> tuple[str, list[ToolCallTurn]]:
            return "", [_make_turn(error="McpArgumentError: invalid args")]

        monkeypatch.setattr(gemma_client, "generate_with_tools_loop", _fake_loop)
        response = await set_your_course.handle_chip_dispatch(_make_request())

        assert response.debug_trace == set_your_course._TRANSPORT_FAILURE_MESSAGE

    @pytest.mark.asyncio
    async def test_chip_dispatch_dispatch_error_returns_failure_chip(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When dispatch raises, the loop returns empty text → failure chip."""
        _stub_tool_schema(monkeypatch)

        async def _fake_loop(**kwargs: Any) -> tuple[str, list[ToolCallTurn]]:
            return "", [_make_turn(error="RuntimeError: DB unavailable")]

        monkeypatch.setattr(gemma_client, "generate_with_tools_loop", _fake_loop)
        response = await set_your_course.handle_chip_dispatch(_make_request())

        assert response.debug_trace == set_your_course._TRANSPORT_FAILURE_MESSAGE

    @pytest.mark.asyncio
    async def test_chip_dispatch_confirmed_focus_only_when_tool_call_made(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """confirmed_focus is None when no tool call happened."""
        _stub_tool_schema(monkeypatch)
        raw = (
            "Guessing deaf ed.\n"
            '---BUCKET---\n{"bucket": "crosswalk_mismatch"}\n'
            '---CONFIRMED_FOCUS---\n{"confirmed_focus": "Deaf Education"}'
        )

        async def _fake_loop(**kwargs: Any) -> tuple[str, list[ToolCallTurn]]:
            return raw, []

        monkeypatch.setattr(gemma_client, "generate_with_tools_loop", _fake_loop)
        response = await set_your_course.handle_chip_dispatch(_make_request())

        assert response.confirmed_focus is None
        assert response.bucket == "crosswalk_mismatch"

    @pytest.mark.asyncio
    async def test_chip_dispatch_show_less_common_short_circuits(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """show_less_common and change_major return empty without Gemma."""
        for chip_id in ("show_less_common", "change_major"):
            request = _make_request(chip_id=chip_id, clarifier=None)
            response = await set_your_course.handle_chip_dispatch(request)
            assert response.debug_trace == ""
            assert response.bucket is None
            assert response.updated_resolution is None
            assert response.confirmed_focus is None
