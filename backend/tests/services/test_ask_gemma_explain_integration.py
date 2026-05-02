"""Integration tests for the ERN explain-receipt path through
``ask_gemma.chat_ask`` and ``ask_gemma.chat_ask_stream``.

Spec: docs/specs/feature-explain-stat-receipt.md (DRAFT v1.3) §4
Testing Impact Analysis. The post-processor itself is unit-tested in
``test_ask_gemma_explain_receipt.py``; this file exercises the wired
branches in chat_ask / chat_ask_stream that route into the receipt
path, the markdown-fallback retry, and the cached-tool-log injection.

Mocks:
  - ``gemma_client.generate_with_tools_loop`` — replaced via monkeypatch
    so no real Gemma call is issued.
  - ``ask_gemma._dispatch`` — counted via wrapper so the test can
    assert the cached-tool-log path doesn't re-dispatch MCP tools.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.models.api import (
    AskScope,
    ExplainStatReceipt,
    TraceFinalText,
)
from app.models.career import (
    BossScores,
    Build,
    CareerOutcome,
    GauntletResult,
    PentagonStats,
)
from app.services import ask_gemma, gemma_client

_IU_UNITID = 151351
_IU_CIPCODE = "11.0701"
_IU_SOC = "15-1252"
_OPENER = "[explain-this:ERN]"


def _make_build(*, ern: int | None = 7, effort: str = "balanced") -> Build:
    """Direct-construct a Build matching the IU CS happy-path build."""
    return Build(
        build_id="iu-cs-test-001",
        created_at="2026-05-02T00:00:00Z",
        school_name="Indiana University-Bloomington",
        unitid=_IU_UNITID,
        major_text="Computer Science",
        cipcode=_IU_CIPCODE,
        program_name="Computer Science",
        effort=effort,  # type: ignore[arg-type]
        loan_pct=1.0,
        career=CareerOutcome(
            unitid=_IU_UNITID,
            institution_name="Indiana University-Bloomington",
            cipcode=_IU_CIPCODE,
            program_name="Computer Science",
            soc_code=_IU_SOC,
            occupation_title="Software Developer",
            stats=PentagonStats(ern=ern, roi=6, res=5, grw=8, aura=4),
            bosses=BossScores(
                ai=10, loans=10, market=10, burnout=10, ceiling=10
            ),
            median_annual_wage=132270.0,
            earnings_1yr_median=94200.0,
        ),
        gauntlet=GauntletResult(
            fights=[], wins=0, losses=0, draws=0, unknown=0, verdict="OK"
        ),
        branches=[],
        skill_recs=[],
        guidance="",
        skills_crafted=[],
        skill_pool=[],
        profile_name="Test Profile",
    )


def _make_tool_log() -> list[gemma_client.ToolCallTurn]:
    """Cached tool_call_log with both ERN tools resolved."""
    return [
        gemma_client.ToolCallTurn(
            turn_number=0,
            tool_name="get_career_paths",
            tool_args={"unitid": _IU_UNITID, "cipcode": _IU_CIPCODE},
            tool_result_size_bytes=200,
            duration_ms=12,
            error=None,
            tool_result_preview=json.dumps({
                "results": [
                    {
                        "soc_code": _IU_SOC,
                        "cip_family_earnings_rank": 0.87,
                        "earnings_1yr_median": 94_200,
                    }
                ]
            }),
            dispatch_index=0,
        ),
        gemma_client.ToolCallTurn(
            turn_number=0,
            tool_name="get_occupation_data",
            tool_args={"soc_code": _IU_SOC},
            tool_result_size_bytes=200,
            duration_ms=15,
            error=None,
            tool_result_preview=json.dumps({
                "wage_percentile_overall": 0.92,
                "median_annual_wage": 132_270,
            }),
            dispatch_index=1,
        ),
    ]


def _good_receipt_payload() -> dict[str, Any]:
    return {
        "kind": "receipt",
        "stat_code": "ERN",
        "stat_name": "Earning Power",
        "score": 7,
        "score_max": 10,
        "one_liner": (
            "Earning Power tells you how much your degree usually pays "
            "right after graduation."
        ),
        "components": [
            {
                "weight_pct": 60,
                "label": "your school's program rank",
                "explainer": (
                    "IU Bloomington's Computer Science grads earn a "
                    "median of $94,200 — that lands at the 87th "
                    "percentile (out of 100 programs, this one ranks "
                    "higher than about 86) of all CS programs."
                ),
                "value_pct": 87,
                "anchor_text": "Indiana University Computer Science grads",
                "anchor_dollars": 94_200,
                "missing_reason": None,
            },
            {
                "weight_pct": 40,
                "label": "this career's pay rank",
                "explainer": (
                    "Software Developer median pay is $132,270, which "
                    "sits at the 92nd percentile."
                ),
                "value_pct": 92,
                "anchor_text": "Software Developer",
                "anchor_dollars": 132_270,
                "missing_reason": None,
            },
        ],
        "math_line": "0.6 × 0.87 + 0.4 × 0.92 → score 9/10",
        "sources": [
            {
                "label": "Graduate earnings",
                "name": "College Scorecard (U.S. Department of Education)",
            },
            {
                "label": "Occupation wages",
                "name": (
                    "Occupational Outlook Handbook, published by the "
                    "Bureau of Labor Statistics (BLS)"
                ),
            },
        ],
        "why_mix_paragraph": (
            "Picture two students. One in a top-ranked CS program at "
            "a regional school, one in a mid-tier Philosophy program "
            "at a flagship. School rank alone would mislead you. "
            "Mixing in occupation pay grounds the score in real "
            "salaries — that's why we blend both."
        ),
    }


# ---------------------------------------------------------------------------
# chat_ask happy path → receipt response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_ask_ern_explain_returns_receipt_on_success(
    monkeypatch,
) -> None:
    """End-to-end: opener triggers JSON-mode loop → post-processor
    succeeds → AskResponse.response is an ExplainStatReceipt object."""
    build = _make_build()

    async def _fake_loop(**kwargs: Any) -> tuple[str, list]:
        # Assert the JSON-mode response_format kwarg is threaded.
        assert kwargs.get("final_turn_response_format") == {
            "type": "json_object"
        }, (
            "explain-ern path must thread response_format=json_object "
            "into generate_with_tools_loop"
        )
        return (json.dumps(_good_receipt_payload()), _make_tool_log())

    monkeypatch.setattr(
        gemma_client, "generate_with_tools_loop", _fake_loop
    )

    response = await ask_gemma.chat_ask(
        scope=AskScope(kind="stat", build_ids=[build.build_id], target_id="ERN"),
        builds=[build],
        message=_OPENER,
        history=[],
        locale="en",
    )

    assert isinstance(response.response, ExplainStatReceipt)
    assert response.response.stat_code == "ERN"
    assert response.response.score == 7  # build's score
    # Tool calls surface on the response so <GemmaTrace> can render.
    assert len(response.tool_calls) == 2


# ---------------------------------------------------------------------------
# chat_ask fallback path → markdown spike string
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_ask_ern_explain_falls_back_on_parse_failure(
    monkeypatch,
) -> None:
    """When _postprocess_ern_explain_receipt returns None, the response
    is the markdown-spike fallback string — NOT a ValidationError, NOT
    None, NOT an empty AskResponse (P0)."""
    build = _make_build()

    call_count = {"n": 0}

    async def _fake_loop(**kwargs: Any) -> tuple[str, list]:
        call_count["n"] += 1
        if call_count["n"] == 1:
            # First call: garbage JSON, will fail postprocess.
            return ("not even close to JSON {{{ broken", _make_tool_log())
        # Second call (fallback): markdown response.
        return (
            "### Earning Power — 7/10\n\n**The one-liner.** Markdown "
            "fallback rendered.",
            [],
        )

    monkeypatch.setattr(
        gemma_client, "generate_with_tools_loop", _fake_loop
    )

    response = await ask_gemma.chat_ask(
        scope=AskScope(kind="stat", build_ids=[build.build_id], target_id="ERN"),
        builds=[build],
        message=_OPENER,
        history=[],
        locale="en",
    )

    # The response is now a string (the markdown fallback), NOT a receipt.
    assert isinstance(response.response, str)
    assert "Earning Power" in response.response
    assert "Markdown fallback rendered" in response.response
    assert call_count["n"] == 2  # initial + fallback retry


@pytest.mark.asyncio
async def test_chat_ask_ern_explain_fallback_uses_cached_tool_log(
    monkeypatch,
) -> None:
    """When fallback fires, get_career_paths and get_occupation_data
    MCP tools are NOT re-called — the cached tool_call_log percentile
    values are injected into the markdown appendix's user message
    instead. Decision 6 v1.2 (P0).

    Mock the dispatch and assert call count == 0 (we never run dispatch
    in this test because the fake loop fires the on_turn_event callbacks
    itself; what matters is that the fallback path's tools=[] argument
    means there are no tools offered to Gemma at all)."""
    build = _make_build()

    call_count = {"n": 0}
    fallback_kwargs: dict[str, Any] = {}

    async def _fake_loop(**kwargs: Any) -> tuple[str, list]:
        call_count["n"] += 1
        if call_count["n"] == 1:
            # Initial JSON-mode loop: garbage to force fallback.
            return ("garbage", _make_tool_log())
        # Fallback retry: capture kwargs to verify tools=[] and the
        # cached values are in the user message.
        fallback_kwargs.update(kwargs)
        return ("### Earning Power — 7/10\n\nFallback rendered.", [])

    monkeypatch.setattr(
        gemma_client, "generate_with_tools_loop", _fake_loop
    )

    # Wrap _dispatch with a counter to prove no MCP tools fire here.
    dispatch_calls: list[tuple[str, dict]] = []
    original_dispatch = ask_gemma._dispatch

    async def _counting_dispatch(name: str, args: dict) -> dict:
        dispatch_calls.append((name, args))
        return await original_dispatch(name, args)

    monkeypatch.setattr(ask_gemma, "_dispatch", _counting_dispatch)

    await ask_gemma.chat_ask(
        scope=AskScope(kind="stat", build_ids=[build.build_id], target_id="ERN"),
        builds=[build],
        message=_OPENER,
        history=[],
        locale="en",
    )

    # Fallback retry MUST pass tools=[] so Gemma can't re-call MCP.
    assert fallback_kwargs.get("tools") == [], (
        f"fallback retry must offer no tools (cached values in message); "
        f"got tools={fallback_kwargs.get('tools')!r}"
    )
    # The user message MUST carry the cached percentile values so the
    # fallback Gemma can read them without re-dispatching.
    user_msg = fallback_kwargs.get("user", "")
    assert "cip_family_earnings_rank = 0.87" in user_msg
    assert "wage_percentile_overall = 0.92" in user_msg
    # No MCP dispatch fired — the fake loop never invoked it because
    # tools=[] was passed.
    assert dispatch_calls == []


@pytest.mark.asyncio
async def test_chat_ask_ern_explain_returns_string_when_build_score_null(
    monkeypatch,
) -> None:
    """Build with stats.ern=None → postprocess returns None (score_null
    failure_reason) → fallback fires (P0)."""
    build = _make_build(ern=None)

    call_count = {"n": 0}

    async def _fake_loop(**kwargs: Any) -> tuple[str, list]:
        call_count["n"] += 1
        if call_count["n"] == 1:
            # Even valid JSON fails postprocess because ern is None.
            return (json.dumps(_good_receipt_payload()), _make_tool_log())
        return ("Markdown fallback after score_null.", [])

    monkeypatch.setattr(
        gemma_client, "generate_with_tools_loop", _fake_loop
    )

    response = await ask_gemma.chat_ask(
        scope=AskScope(kind="stat", build_ids=[build.build_id], target_id="ERN"),
        builds=[build],
        message=_OPENER,
        history=[],
        locale="en",
    )

    assert isinstance(response.response, str)
    assert "fallback" in response.response.lower()


# ---------------------------------------------------------------------------
# chat_ask_stream — receipt rides in the final_text frame
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_ask_stream_ern_explain_emits_receipt_in_final_text(
    monkeypatch,
) -> None:
    """TraceFinalText.response carries an ExplainStatReceipt object
    (with kind='receipt'), not a string, when the JSON path
    succeeds (P0)."""
    build = _make_build()

    async def _fake_loop(**kwargs: Any) -> tuple[str, list]:
        return (json.dumps(_good_receipt_payload()), _make_tool_log())

    monkeypatch.setattr(
        gemma_client, "generate_with_tools_loop", _fake_loop
    )

    events = []
    async for ev in ask_gemma.chat_ask_stream(
        scope=AskScope(kind="stat", build_ids=[build.build_id], target_id="ERN"),
        builds=[build],
        message=_OPENER,
        history=[],
        locale="en",
    ):
        events.append(ev)

    # Exactly one final_text event; payload is a typed receipt.
    finals = [e for e in events if isinstance(e, TraceFinalText)]
    assert len(finals) == 1
    payload = finals[0].response
    assert isinstance(payload, ExplainStatReceipt), (
        f"final_text.response must be an ExplainStatReceipt object, "
        f"got {type(payload).__name__}"
    )
    assert payload.kind == "receipt"
    assert payload.stat_code == "ERN"
    assert payload.score == 7


# ---------------------------------------------------------------------------
# Non-explain stat-scope path — control test (must NOT route via JSON mode)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_ask_non_explain_stat_scope_does_not_set_response_format(
    monkeypatch,
) -> None:
    """Free-form stat-scope question (NOT the opener) → JSON-mode
    response_format is NOT injected. Defends against an explain-mode
    leak into the prose path."""
    build = _make_build()

    captured: dict[str, Any] = {}

    async def _fake_loop(**kwargs: Any) -> tuple[str, list]:
        captured.update(kwargs)
        return ("Plain prose answer.", [])

    monkeypatch.setattr(
        gemma_client, "generate_with_tools_loop", _fake_loop
    )

    await ask_gemma.chat_ask(
        scope=AskScope(kind="stat", build_ids=[build.build_id], target_id="ERN"),
        builds=[build],
        message="why is my earning power so low?",  # not the opener
        history=[],
        locale="en",
    )

    # response_format MUST be None or absent for free-form prose.
    assert captured.get("final_turn_response_format") is None
