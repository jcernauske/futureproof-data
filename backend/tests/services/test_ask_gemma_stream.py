"""Tests for ``ask_gemma.chat_ask_stream`` — the SSE-stream variant of
the Ask Gemma chat handler.

Backs ``feature-gemma-trace.md`` §4 Service Changes. Verifies:

- Event ordering — turn_start, turn_complete, final_text, done.
- No-tool path — only final_text + done emit.
- Tool error — turn_complete carries error, final_text continues.
- Transport failure — chat_unavailable fallback then done; never raises.
- Loop exception — try/except boundary returns chat_unavailable + done.
- Client disconnect — loop_task cancellation via try/finally.
- Bounded queue under realistic load — no blocking, no event loss.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.models.api import (
    AskScope,
    TraceDone,
    TraceFinalText,
    TraceTurnComplete,
    TraceTurnStart,
)
from app.models.career import (
    BossScores,
    Build,
    CareerOutcome,
    GauntletResult,
    PentagonStats,
)
from app.services import ask_gemma, gemma_client

_FULL_PROFILE = gemma_client.ModelRuntimeProfile(
    tier="full",
    rich_intent_streaming=True,
    intent_fallback_max_tokens=200,
    build_gemma_timeout_s=None,
    build_narrative_max_tokens=800,
    build_recs_max_tokens=800,
    build_pool_max_tokens=2000,
    build_guidance_max_tokens=1200,
    eager_career_description=True,
    sequential_build_stream=False,
    ask_tool_wall_time_s=45.0,
    ask_max_tokens=1200,
    ask_skip_tool_calling=False,
)


@pytest.fixture(autouse=True)
def _force_full_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force full-tier profile so E4B local config doesn't route through
    the no-tools generate_async path."""
    monkeypatch.setattr(
        gemma_client, "runtime_profile", lambda config=None: _FULL_PROFILE,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_build() -> Build:
    """Minimal in-memory Build fixture. Direct constructor (no DB
    write) so the test stays purely unit-level and doesn't fight for
    the shared DuckDB lock."""
    return Build(
        build_id="bid-test",
        created_at="2026-05-01T00:00:00Z",
        school_name="Test University",
        unitid=110635,
        major_text="Computer Science",
        cipcode="11.0701",
        program_name="Computer Science",
        effort="balanced",
        loan_pct=1.0,
        career=CareerOutcome(
            unitid=110635,
            institution_name="Test University",
            cipcode="11.0701",
            program_name="Computer Science",
            soc_code="13-2052",
            occupation_title="Financial Analyst",
            stats=PentagonStats(ern=7, roi=6, res=5, grw=8, aura=4),
            bosses=BossScores(
                ai=10, loans=10, market=10, burnout=10, ceiling=10
            ),
            modeled_total_debt=20000,
            net_price_annual=15000,
            loan_pct=1.0,
            earnings_1yr_median=60000,
            median_annual_wage=80000,
        ),
        gauntlet=GauntletResult(
            fights=[],
            wins=0,
            losses=0,
            draws=0,
            unknown=0,
            verdict="OK",
        ),
        branches=[],
        skill_recs=[],
        guidance="",
        skills_crafted=[],
        skill_pool=[],
        profile_name="Test Profile",
    )


async def _collect(gen) -> list:
    """Drain an async generator into a list."""
    out = []
    async for ev in gen:
        out.append(ev)
    return out


# ---------------------------------------------------------------------------
# Happy path — one tool call resolves cleanly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_emits_turn_start_then_complete(monkeypatch) -> None:
    """One tool call → events in order: turn_start, turn_complete,
    final_text, done. Both events carry turn=dispatch_index=0."""
    build = _make_build()

    async def _fake_loop(**kwargs: Any) -> tuple[str, list]:
        on_start = kwargs.get("on_turn_start")
        on_event = kwargs.get("on_turn_event")
        await on_start(0, "get_career_paths", {"unitid": 110635})
        turn = gemma_client.ToolCallTurn(
            turn_number=0,
            tool_name="get_career_paths",
            tool_args={"unitid": 110635},
            tool_result_size_bytes=42,
            duration_ms=87,
            error=None,
            tool_result_preview='{"data": "ok"}',
            dispatch_index=0,
        )
        await on_event(turn)
        return ("Final answer.", [turn])

    monkeypatch.setattr(
        gemma_client, "generate_with_tools_loop", _fake_loop
    )

    events = await _collect(
        ask_gemma.chat_ask_stream(
            scope=AskScope(kind="build", build_ids=[build.build_id]),
            builds=[build],
            message="What about Marketing at IU?",
            history=[],
            locale="en",
        )
    )

    # turn_start, turn_complete, final_text, done
    assert len(events) == 4
    assert isinstance(events[0], TraceTurnStart)
    assert events[0].turn == 0
    assert events[0].tool == "get_career_paths"
    assert isinstance(events[1], TraceTurnComplete)
    assert events[1].turn == 0
    assert events[1].duration_ms == 87
    assert events[1].error is None
    assert isinstance(events[2], TraceFinalText)
    assert events[2].response == "Final answer."
    assert isinstance(events[3], TraceDone)


# ---------------------------------------------------------------------------
# No-tool path — Gemma answers from context
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_no_tools_called_emits_only_final_and_done(
    monkeypatch,
) -> None:
    """Gemma answers from context (no tool calls) → events: final_text,
    done. No turn_start, no turn_complete."""
    build = _make_build()

    async def _fake_loop(**kwargs: Any) -> tuple[str, list]:
        return ("Direct answer from context.", [])

    monkeypatch.setattr(
        gemma_client, "generate_with_tools_loop", _fake_loop
    )

    events = await _collect(
        ask_gemma.chat_ask_stream(
            scope=AskScope(kind="build", build_ids=[build.build_id]),
            builds=[build],
            message="Tell me about my build.",
            history=[],
            locale="en",
        )
    )

    assert len(events) == 2
    assert isinstance(events[0], TraceFinalText)
    assert events[0].response == "Direct answer from context."
    assert isinstance(events[1], TraceDone)


# ---------------------------------------------------------------------------
# Tool dispatch error — error pill, chat continues
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_tool_error_emits_complete_with_error(
    monkeypatch,
) -> None:
    """Tool dispatch errors → turn_complete carries `error` field,
    final_text + done still emit."""
    build = _make_build()

    async def _fake_loop(**kwargs: Any) -> tuple[str, list]:
        on_start = kwargs.get("on_turn_start")
        on_event = kwargs.get("on_turn_event")
        await on_start(0, "get_career_paths", {})
        turn = gemma_client.ToolCallTurn(
            turn_number=0,
            tool_name="get_career_paths",
            tool_args={},
            tool_result_size_bytes=0,
            duration_ms=12,
            error="RuntimeError: DB unavailable",
            tool_result_preview='{"error": "DB unavailable"}',
            dispatch_index=0,
        )
        await on_event(turn)
        return ("I tried to look that up but couldn't.", [turn])

    monkeypatch.setattr(
        gemma_client, "generate_with_tools_loop", _fake_loop
    )

    events = await _collect(
        ask_gemma.chat_ask_stream(
            scope=AskScope(kind="build", build_ids=[build.build_id]),
            builds=[build],
            message="What about a different school?",
            history=[],
            locale="en",
        )
    )

    completes = [e for e in events if isinstance(e, TraceTurnComplete)]
    assert len(completes) == 1
    assert completes[0].error == "RuntimeError: DB unavailable"

    # final_text still emits — chat continues to render an answer.
    finals = [e for e in events if isinstance(e, TraceFinalText)]
    assert len(finals) == 1
    assert finals[0].response == "I tried to look that up but couldn't."


# ---------------------------------------------------------------------------
# Transport failure — chat_unavailable fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_transport_failure_emits_fallback_final_text(
    monkeypatch,
) -> None:
    """Gemma loop returns ('', []) (transport failure) → final_text is
    chat_unavailable localized string, done emitted."""
    build = _make_build()

    async def _fake_loop(**kwargs: Any) -> tuple[str, list]:
        return ("", [])

    monkeypatch.setattr(
        gemma_client, "generate_with_tools_loop", _fake_loop
    )

    events = await _collect(
        ask_gemma.chat_ask_stream(
            scope=AskScope(kind="build", build_ids=[build.build_id]),
            builds=[build],
            message="Anything",
            history=[],
            locale="en",
        )
    )

    assert isinstance(events[-2], TraceFinalText)
    assert isinstance(events[-1], TraceDone)
    # Some non-empty fallback string (the localized one)
    assert events[-2].response != ""


# ---------------------------------------------------------------------------
# C3 — loop_task exception caught at the boundary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_loop_exception_falls_back_to_chat_unavailable(
    monkeypatch,
) -> None:
    """If the loop raises mid-flight, the generator wraps the exception
    in a fallback final_text + done. Never raises past the boundary."""
    build = _make_build()

    async def _fake_loop(**kwargs: Any) -> tuple[str, list]:
        raise RuntimeError("loop blew up")

    monkeypatch.setattr(
        gemma_client, "generate_with_tools_loop", _fake_loop
    )

    events = await _collect(
        ask_gemma.chat_ask_stream(
            scope=AskScope(kind="build", build_ids=[build.build_id]),
            builds=[build],
            message="Anything",
            history=[],
            locale="en",
        )
    )

    # Even with a raising loop, we get final_text + done back, no
    # exception propagation.
    assert isinstance(events[-2], TraceFinalText)
    assert events[-2].response != ""
    assert isinstance(events[-1], TraceDone)


# ---------------------------------------------------------------------------
# Queue draining — events emitted before EOF
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_queue_drained_after_loop_completes(
    monkeypatch,
) -> None:
    """If the loop completes while events are still in the queue, the
    drain loop yields them all before falling through to final_text."""
    build = _make_build()

    async def _fake_loop(**kwargs: Any) -> tuple[str, list]:
        on_start = kwargs.get("on_turn_start")
        on_event = kwargs.get("on_turn_event")
        log = []
        for i in range(3):
            await on_start(i, "get_career_paths", {"i": i})
            t = gemma_client.ToolCallTurn(
                turn_number=0,
                tool_name="get_career_paths",
                tool_args={"i": i},
                tool_result_size_bytes=10,
                duration_ms=5,
                error=None,
                tool_result_preview="ok",
                dispatch_index=i,
            )
            log.append(t)
            await on_event(t)
        return ("Final.", log)

    monkeypatch.setattr(
        gemma_client, "generate_with_tools_loop", _fake_loop
    )

    events = await _collect(
        ask_gemma.chat_ask_stream(
            scope=AskScope(kind="build", build_ids=[build.build_id]),
            builds=[build],
            message="anything",
            history=[],
            locale="en",
        )
    )

    starts = [e for e in events if isinstance(e, TraceTurnStart)]
    completes = [e for e in events if isinstance(e, TraceTurnComplete)]
    assert [e.turn for e in starts] == [0, 1, 2]
    assert [e.turn for e in completes] == [0, 1, 2]
    assert isinstance(events[-2], TraceFinalText)
    assert isinstance(events[-1], TraceDone)


# ---------------------------------------------------------------------------
# C4 — client disconnect cancels loop_task
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_cancelled_when_client_disconnects(monkeypatch) -> None:
    """Promoted from P1 to P0 per C4. Simulate client disconnect by
    calling aclose() on the generator while the loop is in-flight.

    Asserts: the loop_task is cancelled within ~100ms (not after the
    30s wall-time cap), and asyncio.gather on it does not hang.
    """
    build = _make_build()

    loop_task_holder: dict[str, asyncio.Task | None] = {"task": None}
    loop_started = asyncio.Event()
    loop_finished = asyncio.Event()

    async def _slow_loop(**kwargs: Any) -> tuple[str, list]:
        # Keep the current task in the holder so the test can inspect
        # it after disconnect.
        loop_task_holder["task"] = asyncio.current_task()
        loop_started.set()
        try:
            await asyncio.sleep(30.0)  # full wall-time cap
            return ("never", [])
        finally:
            loop_finished.set()

    monkeypatch.setattr(
        gemma_client, "generate_with_tools_loop", _slow_loop
    )

    gen = ask_gemma.chat_ask_stream(
        scope=AskScope(kind="build", build_ids=[build.build_id]),
        builds=[build],
        message="anything",
        history=[],
        locale="en",
    )

    # Pump the generator until the loop is in-flight (one yield is
    # enough — even an empty queue causes the drain loop to spin).
    pump_task = asyncio.create_task(gen.__anext__())
    await loop_started.wait()
    # Wait briefly so the drain loop is actually running.
    await asyncio.sleep(0.05)

    # Now simulate disconnect: cancel the pumping task and aclose the
    # generator. This should cancel loop_task in the finally block.
    pump_task.cancel()
    try:
        await pump_task
    except (asyncio.CancelledError, StopAsyncIteration):
        pass
    await gen.aclose()

    # Within ~100ms, loop_task is settled (cancelled) and finished is
    # set (because asyncio.sleep raises CancelledError, which the
    # try/finally in _slow_loop catches and propagates after setting
    # the event).
    await asyncio.wait_for(loop_finished.wait(), timeout=0.5)
    task = loop_task_holder["task"]
    assert task is not None
    assert task.done()


# ---------------------------------------------------------------------------
# C5 / Decision #14 — bounded queue under realistic load
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_back_pressure_under_bounded_queue(monkeypatch) -> None:
    """Push 32 events through a single chat turn (4x typical load).
    The queue's maxsize=256 never blocks and no events are lost.

    Validates Decision #14's documented bound: max_turns(3) ×
    max_tools_per_turn(~5) × event_pairs(2) = ~30 worst case; 32 is
    above the realistic cap and still well below the 256-cap.
    """
    build = _make_build()

    async def _fake_loop(**kwargs: Any) -> tuple[str, list]:
        on_start = kwargs.get("on_turn_start")
        on_event = kwargs.get("on_turn_event")
        log = []
        for i in range(16):
            await on_start(i, "get_career_paths", {"i": i})
            t = gemma_client.ToolCallTurn(
                turn_number=0,
                tool_name="get_career_paths",
                tool_args={"i": i},
                tool_result_size_bytes=10,
                duration_ms=1,
                error=None,
                tool_result_preview="ok",
                dispatch_index=i,
            )
            log.append(t)
            await on_event(t)
        return ("Done.", log)

    monkeypatch.setattr(
        gemma_client, "generate_with_tools_loop", _fake_loop
    )

    events = await _collect(
        ask_gemma.chat_ask_stream(
            scope=AskScope(kind="build", build_ids=[build.build_id]),
            builds=[build],
            message="anything",
            history=[],
            locale="en",
        )
    )

    starts = [e for e in events if isinstance(e, TraceTurnStart)]
    completes = [e for e in events if isinstance(e, TraceTurnComplete)]
    assert len(starts) == 16
    assert len(completes) == 16
    # All 32 events delivered in order (no drops, no blocks).
    assert [e.turn for e in starts] == list(range(16))
    assert [e.turn for e in completes] == list(range(16))
