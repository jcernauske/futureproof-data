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
                "data": [
                    {
                        "soc_code": _IU_SOC,
                        "cip_family_earnings_rank": 0.87,
                        "earnings_1yr_median": 94_200,
                    }
                ],
                "row_count": 1,
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
                "data": {
                    "wage_percentile_overall": 0.92,
                    "median_annual_wage": 132_270,
                },
                "row_count": 1,
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
    monkeypatch.setattr(gemma_client, "runtime_profile", lambda *a, **kw: _FULL_PROFILE)
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
    monkeypatch.setattr(gemma_client, "runtime_profile", lambda *a, **kw: _FULL_PROFILE)
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
    monkeypatch.setattr(gemma_client, "runtime_profile", lambda *a, **kw: _FULL_PROFILE)
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


# ---------------------------------------------------------------------------
# Score-null receipt path (server-built, no Gemma call)
# Spec: docs/specs/bugfix-explain-stat-trigger-null-score-guard.md
# ---------------------------------------------------------------------------


def _occupation_payload(
    *, wage_pct: float | None = 0.92, wage: int | None = 132_270
) -> dict[str, Any]:
    return {
        "data": {
            "wage_percentile_overall": wage_pct,
            "median_annual_wage": wage,
        },
        "row_count": 1,
    }


def _career_paths_payload(
    *, cip_rank: float | None = 0.87, earnings: int | None = 94_200
) -> dict[str, Any]:
    return {
        "data": [
            {
                "soc_code": _IU_SOC,
                "cip_family_earnings_rank": cip_rank,
                "earnings_1yr_median": earnings,
            }
        ],
        "row_count": 1,
    }


def _patch_dispatch(
    monkeypatch,
    *,
    career_paths: dict[str, Any],
    occupation: dict[str, Any],
) -> dict[str, list]:
    """Patch ask_gemma._dispatch to return canned MCP responses without
    hitting the real MCP server. Returns a dict tracking call counts so
    tests can assert each tool was called exactly once."""
    calls: dict[str, list[dict[str, Any]]] = {
        "get_career_paths": [],
        "get_occupation_data": [],
    }

    async def _fake_dispatch(name: str, args: dict[str, Any]) -> dict[str, Any]:
        calls.setdefault(name, []).append(args)
        if name == "get_career_paths":
            return career_paths
        if name == "get_occupation_data":
            return occupation
        raise AssertionError(f"unexpected dispatch: {name}")

    monkeypatch.setattr(ask_gemma, "_dispatch", _fake_dispatch)
    return calls


@pytest.mark.asyncio
async def test_chat_ask_ern_explain_returns_missing_receipt_when_score_null(
    monkeypatch,
) -> None:
    """Build with stats.ern=None + sentinel opener → response is an
    ExplainStatReceipt with score=None, the universal one-liner /
    sources / why-mix paragraph, and per-input missing_reason lines.
    NO Gemma call (fake loop asserts call_count == 0)."""
    build = _make_build(ern=None)

    loop_calls = {"n": 0}

    async def _fake_loop(**kwargs: Any) -> tuple[str, list]:
        loop_calls["n"] += 1
        return ("should not be reached", [])

    monkeypatch.setattr(gemma_client, "generate_with_tools_loop", _fake_loop)
    # Earnings missing (the Millikin-class case): cip_rank null, BLS
    # values present.
    dispatch_calls = _patch_dispatch(
        monkeypatch,
        career_paths=_career_paths_payload(cip_rank=None, earnings=None),
        occupation=_occupation_payload(),
    )

    response = await ask_gemma.chat_ask(
        scope=AskScope(kind="stat", build_ids=[build.build_id], target_id="ERN"),
        builds=[build],
        message=_OPENER,
        history=[],
        locale="en",
    )

    assert loop_calls["n"] == 0, "score-null path must NOT call Gemma"
    assert len(dispatch_calls["get_career_paths"]) == 1
    assert len(dispatch_calls["get_occupation_data"]) == 1

    assert isinstance(response.response, ExplainStatReceipt)
    receipt = response.response
    assert receipt.kind == "receipt"
    assert receipt.stat_code == "ERN"
    assert receipt.score is None
    assert receipt.score_max == 10
    # Universal prose (always rendered, regardless of which input is null).
    assert "Earning Power" in receipt.stat_name
    assert receipt.one_liner
    assert receipt.why_mix_paragraph
    assert len(receipt.sources) == 2

    # Per-component fields. 60% bullet → school+earnings missing.
    school_comp = next(c for c in receipt.components if c.weight_pct == 60)
    assert school_comp.value_pct is None
    assert school_comp.anchor_dollars is None
    assert school_comp.missing_reason is not None
    assert "College Scorecard" in school_comp.missing_reason
    assert build.career.institution_name in school_comp.missing_reason

    # 40% bullet → present, has values.
    career_comp = next(c for c in receipt.components if c.weight_pct == 40)
    assert career_comp.value_pct == 92
    assert career_comp.anchor_dollars == 132_270
    assert career_comp.missing_reason is None

    # math_line shows the missing input as 'n/a'.
    assert "n/a" in receipt.math_line
    assert "no score available" in receipt.math_line

    # Tool calls surface so the trace rail can render them.
    assert len(response.tool_calls) == 2
    tool_names = sorted(tc.tool for tc in response.tool_calls)
    assert tool_names == ["get_career_paths", "get_occupation_data"]


@pytest.mark.asyncio
async def test_chat_ask_ern_explain_missing_receipt_handles_both_inputs_null(
    monkeypatch,
) -> None:
    """Both inputs null → both component bullets carry missing_reason
    lines naming their respective data sources."""
    build = _make_build(ern=None)

    async def _fake_loop(**kwargs: Any) -> tuple[str, list]:
        raise AssertionError("must not call Gemma on score-null path")

    monkeypatch.setattr(gemma_client, "generate_with_tools_loop", _fake_loop)
    _patch_dispatch(
        monkeypatch,
        career_paths=_career_paths_payload(cip_rank=None, earnings=None),
        occupation=_occupation_payload(wage_pct=None, wage=None),
    )

    response = await ask_gemma.chat_ask(
        scope=AskScope(kind="stat", build_ids=[build.build_id], target_id="ERN"),
        builds=[build],
        message=_OPENER,
        history=[],
        locale="en",
    )

    assert isinstance(response.response, ExplainStatReceipt)
    receipt = response.response
    assert receipt.score is None
    school = next(c for c in receipt.components if c.weight_pct == 60)
    career = next(c for c in receipt.components if c.weight_pct == 40)
    assert school.missing_reason and "College Scorecard" in school.missing_reason
    assert career.missing_reason and "BLS" in career.missing_reason
    # Math line: both placeholders.
    assert receipt.math_line.count("n/a") == 2


@pytest.mark.asyncio
async def test_chat_ask_stream_ern_explain_emits_missing_receipt(
    monkeypatch,
) -> None:
    """Stream variant: emits two trace turn pairs (one per MCP fetch)
    + one TraceFinalText carrying the receipt + one TraceDone."""
    from app.models.api import TraceDone, TraceTurnComplete, TraceTurnStart

    build = _make_build(ern=None)

    async def _fake_loop(**kwargs: Any) -> tuple[str, list]:
        raise AssertionError("must not call Gemma on score-null path")

    monkeypatch.setattr(gemma_client, "generate_with_tools_loop", _fake_loop)
    _patch_dispatch(
        monkeypatch,
        career_paths=_career_paths_payload(cip_rank=None, earnings=None),
        occupation=_occupation_payload(),
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

    finals = [e for e in events if isinstance(e, TraceFinalText)]
    dones = [e for e in events if isinstance(e, TraceDone)]
    starts = [e for e in events if isinstance(e, TraceTurnStart)]
    completes = [e for e in events if isinstance(e, TraceTurnComplete)]

    assert len(finals) == 1
    assert len(dones) == 1
    assert len(starts) == 2
    assert len(completes) == 2
    payload = finals[0].response
    assert isinstance(payload, ExplainStatReceipt)
    assert payload.score is None


@pytest.mark.asyncio
async def test_score_null_path_logs_structured_record(monkeypatch) -> None:
    """Score-null path appends one record to gemma.jsonl with
    call_site='explain_ern_missing_receipt' and the input-null state."""
    monkeypatch.setattr(gemma_client, "runtime_profile", lambda *a, **kw: _FULL_PROFILE)
    build = _make_build(ern=None)

    captured: list[dict[str, Any]] = []

    def _fake_log_exchange(record: dict[str, Any]) -> None:
        captured.append(record)

    monkeypatch.setattr(gemma_client, "_log_exchange", _fake_log_exchange)

    async def _fake_loop(**kwargs: Any) -> tuple[str, list]:
        raise AssertionError("must not call Gemma on score-null path")

    monkeypatch.setattr(gemma_client, "generate_with_tools_loop", _fake_loop)
    _patch_dispatch(
        monkeypatch,
        career_paths=_career_paths_payload(cip_rank=None, earnings=None),
        occupation=_occupation_payload(),
    )

    await ask_gemma.chat_ask(
        scope=AskScope(kind="stat", build_ids=[build.build_id], target_id="ERN"),
        builds=[build],
        message=_OPENER,
        history=[],
        locale="en",
    )

    matches = [
        r for r in captured
        if r.get("call_site") == "explain_ern_missing_receipt"
    ]
    assert len(matches) == 1
    rec = matches[0]
    assert rec["build_id"] == build.build_id
    assert rec["reason"] == "build_score_null"
    assert rec["cip_rank"] is None
    assert rec["wage_pct"] == 0.92


@pytest.mark.asyncio
async def test_score_present_path_unchanged(monkeypatch) -> None:
    """Build with non-null stats.ern → the JSON path runs normally; the
    score-null branch is not entered."""
    monkeypatch.setattr(gemma_client, "runtime_profile", lambda *a, **kw: _FULL_PROFILE)
    build = _make_build(ern=7)

    async def _fake_loop(**kwargs: Any) -> tuple[str, list]:
        return (json.dumps(_good_receipt_payload()), _make_tool_log())

    monkeypatch.setattr(gemma_client, "generate_with_tools_loop", _fake_loop)

    # Patch dispatch with a sentinel that fails if the score-null branch
    # tries to use it (the score-present path goes through Gemma's tool
    # loop, not the direct dispatch).
    async def _fail_dispatch(name: str, args: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError(
            f"score-present path must not direct-dispatch {name}"
        )

    monkeypatch.setattr(ask_gemma, "_dispatch", _fail_dispatch)

    response = await ask_gemma.chat_ask(
        scope=AskScope(kind="stat", build_ids=[build.build_id], target_id="ERN"),
        builds=[build],
        message=_OPENER,
        history=[],
        locale="en",
    )

    assert isinstance(response.response, ExplainStatReceipt)
    assert response.response.score == 7


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
    monkeypatch.setattr(gemma_client, "runtime_profile", lambda *a, **kw: _FULL_PROFILE)
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
