"""Tests for ``POST /chat/ask``.

Covers:
- All 5 scope kinds round-trip end-to-end with a mocked Gemma.
- Pydantic validation rejects malformed scopes (422).
- Unknown ``build_id`` returns 404.
- Empty Gemma response routes to the localized fallback string (200).
- Tool dispatch fires when Gemma calls a tool (P1).
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models.career import (
    AppliedSkill,
    BossFightResult,
    BossScores,
    Build,
    CareerBranch,
    CareerOutcome,
    GauntletResult,
    PentagonStats,
)
from app.services import builds as builds_service
from app.services import gemma_client
from app.services.gemma_client import ToolCallTurn

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_build(
    *,
    profile_name: str = "bold bear",
    school_name: str = "UC Berkeley",
    major_text: str = "Computer Science",
    soc: str = "15-1252",
    title: str = "Software Developers",
    with_branches: bool = False,
) -> Build:
    """Persist + return one build with applied skill, populated stats,
    and the canonical 5 fights — enough for every scope kind."""
    career = CareerOutcome(
        unitid=110635,
        institution_name=school_name,
        cipcode="11.0701",
        program_name=major_text,
        soc_code=soc,
        occupation_title=title,
        stats=PentagonStats(ern=8, roi=6, res=4, grw=9, hmn=5),
        bosses=BossScores(ai=11, loans=8, market=10, burnout=6, ceiling=7),
        median_annual_wage=127_260.0,
        earnings_1yr_median=82_500.0,
        earnings_1yr_p75=110_000.0,
        net_price_annual=18_400.0,
        modeled_total_debt=36_800.0,
        debt_to_earnings_annual=0.32,
        education_level_name="Bachelor's degree",
        growth_category="growing_fast",
        composite_method="three_signal",
        roi_cost_basis="cost_of_attendance",
        loan_pct=0.5,
    )
    gauntlet = GauntletResult(
        fights=[
            BossFightResult(
                boss=b,  # type: ignore[arg-type]
                label=f"Fight {b}",
                result="lose" if b == "ai" else "win",  # type: ignore[arg-type]
                raw_score=9,
                threshold_win=14,
                threshold_draw=10,
                reason="ok",
                narrative=f"{b} narrative",
            )
            for b in ("ai", "loans", "market", "burnout", "ceiling")
        ],
        wins=4,
        losses=1,
        draws=0,
        unknown=0,
        verdict="OK",
    )
    skill = AppliedSkill(
        id="ai_minor",
        title="AI/ML elective track",
        rationale="Direct AI tools rather than be replaced.",
        targets=["ai"],
        delta_res=2,
    )
    branches: list[CareerBranch] = []
    if with_branches:
        branches = [
            CareerBranch(
                from_soc=soc,
                to_soc="11-3021",
                to_title="Computer and Information Systems Managers",
                delta_ern=3,
                delta_grw=-1,
                relatedness=0.84,
                related_education_level="Master's degree",
            ),
            CareerBranch(
                from_soc=soc,
                to_soc="15-1299",
                to_title="Computer Occupations, All Other",
                delta_ern=1,
                delta_grw=2,
                relatedness=0.72,
            ),
        ]
    build = builds_service.build_from_parts(
        school_name=school_name,
        unitid=110635,
        major_text=major_text,
        cipcode="11.0701",
        program_name=major_text,
        effort="balanced",
        career=career,
        gauntlet=gauntlet,
        branches=branches,
        skill_recs=[],
        guidance="",
        profile_name=profile_name,
        skills_crafted=[skill],
    )
    builds_service.save_build(build)
    return build


@pytest.fixture
def client(isolated_builds_db) -> TestClient:
    """Fresh FastAPI app + TestClient against the isolated DuckDB."""
    return TestClient(create_app())


@pytest.fixture
def stub_clean_gemma(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Patch ``generate_with_tools_loop`` to return a canned clean
    response and capture the call args. Useful for shape tests where
    we don't care WHAT Gemma said, only that the pipeline routes
    correctly."""
    captured: dict[str, Any] = {"calls": []}

    async def fake_loop(**kwargs: Any) -> tuple[str, list[ToolCallTurn]]:
        captured["calls"].append(kwargs)
        return "Berkeley CS keeps your earnings in line with $82k+ start.", []

    monkeypatch.setattr(gemma_client, "generate_with_tools_loop", fake_loop)
    return captured


# ---------------------------------------------------------------------------
# 1. Each scope kind round-trips through the router.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "scope_payload",
    [
        # stat
        {"kind": "stat", "build_ids": ["__bid__"], "target_id": "ERN"},
        # boss
        {"kind": "boss", "build_ids": ["__bid__"], "target_id": "ai"},
        # skill
        {"kind": "skill", "build_ids": ["__bid__"], "target_id": "ai_minor"},
        # build
        {"kind": "build", "build_ids": ["__bid__"]},
    ],
    ids=["stat", "boss", "skill", "build"],
)
def test_post_chat_ask_each_scope_kind(
    client: TestClient,
    stub_clean_gemma: dict[str, Any],
    scope_payload: dict[str, Any],
) -> None:
    """All four single-build scope kinds: payload validates, build
    loads, Gemma is called, ``{response, tool_calls}`` returns 200."""
    build = _make_build()
    payload = dict(scope_payload)
    payload["build_ids"] = [build.build_id]

    resp = client.post(
        "/chat/ask",
        json={
            "scope": payload,
            "message": "How does this look?",
            "history": [],
            "locale": "en",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "response" in body
    assert "tool_calls" in body
    assert isinstance(body["response"], str)
    assert body["response"].startswith("Berkeley CS")
    # Pipeline called Gemma exactly once, with our scope kind threaded
    # into the call_site extras.
    assert len(stub_clean_gemma["calls"]) == 1
    call = stub_clean_gemma["calls"][0]
    assert call["extra"]["call_site"] == f"ask_gemma_{payload['kind']}"


def test_post_chat_ask_compare_scope(
    client: TestClient,
    stub_clean_gemma: dict[str, Any],
) -> None:
    """Compare scope is the 5th and the only one with N>1 build_ids."""
    b1 = _make_build(profile_name="a", school_name="UCB", major_text="CS")
    b2 = _make_build(
        profile_name="a",
        school_name="IU",
        major_text="Marketing",
        soc="11-2021",
        title="Marketing Managers",
    )

    resp = client.post(
        "/chat/ask",
        json={
            "scope": {
                "kind": "compare",
                "build_ids": [b1.build_id, b2.build_id],
            },
            "message": "Which one wins on cost?",
            "history": [],
            "locale": "en",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "response" in body
    assert stub_clean_gemma["calls"][0]["extra"]["call_site"] == "ask_gemma_compare"
    assert stub_clean_gemma["calls"][0]["extra"]["scope_build_count"] == 2


# ---------------------------------------------------------------------------
# 2. Pydantic validation — every malformed payload returns 422.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "scope, expectation",
    [
        # Compare with 1 build.
        (
            {"kind": "compare", "build_ids": ["x"]},
            "compare scope requires 2-4 build_ids",
        ),
        # Compare with 5 builds.
        (
            {"kind": "compare", "build_ids": ["a", "b", "c", "d", "e"]},
            None,  # min/max length error from Field(max_length=4)
        ),
        # Compare with target_id set.
        (
            {
                "kind": "compare",
                "build_ids": ["a", "b"],
                "target_id": "ERN",
            },
            "compare scope must not set target_id",
        ),
        # Stat with no target_id.
        (
            {"kind": "stat", "build_ids": ["x"]},
            "stat scope requires target_id",
        ),
        # Stat with bad target_id.
        (
            {"kind": "stat", "build_ids": ["x"], "target_id": "FOO"},
            "stat target_id must be one of",
        ),
        # Boss with no target_id.
        (
            {"kind": "boss", "build_ids": ["x"]},
            "boss scope requires target_id",
        ),
        # Boss with bad target_id.
        (
            {"kind": "boss", "build_ids": ["x"], "target_id": "FOO"},
            "boss target_id must be one of",
        ),
        # Build with target_id set — the validator enforces "stat/boss/skill
        # require target_id" but does not explicitly forbid build from
        # having one. Acceptable per the model — only compare bans it.
        # Skip this one — see test_build_with_target_id below for the
        # actual contract.
        # Stat with too many build_ids (only allowed 1).
        (
            {
                "kind": "stat",
                "build_ids": ["a", "b"],
                "target_id": "ERN",
            },
            "stat scope requires exactly 1 build_id",
        ),
    ],
    ids=[
        "compare_one_build",
        "compare_five_builds",
        "compare_with_target",
        "stat_no_target",
        "stat_bad_target",
        "boss_no_target",
        "boss_bad_target",
        "stat_two_builds",
    ],
)
def test_scope_validation_rejects_bad_payloads(
    client: TestClient,
    scope: dict[str, Any],
    expectation: str | None,
) -> None:
    resp = client.post(
        "/chat/ask",
        json={
            "scope": scope,
            "message": "anything",
            "history": [],
            "locale": "en",
        },
    )
    assert resp.status_code == 422, resp.text
    if expectation is not None:
        body_text = resp.text
        assert expectation in body_text, (
            f"Expected {expectation!r} in 422 body; got: {body_text}"
        )


# ---------------------------------------------------------------------------
# 3. Unknown build_id returns 404.
# ---------------------------------------------------------------------------


def test_404_when_build_id_missing(
    client: TestClient,
    stub_clean_gemma: dict[str, Any],
) -> None:
    resp = client.post(
        "/chat/ask",
        json={
            "scope": {
                "kind": "build",
                "build_ids": ["nonexistent-9999"],
            },
            "message": "tell me about my build",
            "history": [],
            "locale": "en",
        },
    )
    assert resp.status_code == 404, resp.text
    # Gemma should NOT have been called when the build can't be loaded.
    assert stub_clean_gemma["calls"] == []


def test_404_when_skill_id_missing(
    client: TestClient,
    stub_clean_gemma: dict[str, Any],
) -> None:
    """skill scope with an unknown skill_id raises SkillNotFoundError
    in the service layer; the router translates that to 404."""
    build = _make_build()
    resp = client.post(
        "/chat/ask",
        json={
            "scope": {
                "kind": "skill",
                "build_ids": [build.build_id],
                "target_id": "no-such-skill",
            },
            "message": "what's this?",
            "history": [],
            "locale": "en",
        },
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 4. Empty Gemma → fallback string, status 200.
# ---------------------------------------------------------------------------


def test_gemma_unavailable_returns_fallback_string(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ``generate_with_tools_loop`` returns ``("", [])`` (the
    uniform empty-string failure signal — see spec §4 line 967), the
    router returns the localized ``chat_unavailable`` string with
    status 200, never a 5xx."""
    build = _make_build()

    async def fake_loop(**kwargs: Any) -> tuple[str, list[ToolCallTurn]]:
        return "", []

    monkeypatch.setattr(gemma_client, "generate_with_tools_loop", fake_loop)

    resp = client.post(
        "/chat/ask",
        json={
            "scope": {"kind": "build", "build_ids": [build.build_id]},
            "message": "How does this look?",
            "history": [],
            "locale": "en",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    # The exact English fallback per locale.py:_FALLBACKS["chat_unavailable"]["en"]
    assert body["response"] == (
        "I'm having trouble reaching Gemma right now. "
        "Try the question again in a moment."
    )
    # tool_calls is the empty list — there were no tool turns.
    assert body["tool_calls"] == []


def test_gemma_unavailable_es_locale_returns_spanish_fallback(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Locale-aware fallback. Spanish locale gets the Spanish string."""
    build = _make_build()

    async def fake_loop(**kwargs: Any) -> tuple[str, list[ToolCallTurn]]:
        return "", []

    monkeypatch.setattr(gemma_client, "generate_with_tools_loop", fake_loop)

    resp = client.post(
        "/chat/ask",
        json={
            "scope": {"kind": "build", "build_ids": [build.build_id]},
            "message": "How does this look?",
            "history": [],
            "locale": "es",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["response"] == (
        "Tengo problemas para conectar con Gemma ahora. "
        "Intenta la pregunta de nuevo en un momento."
    )


# ---------------------------------------------------------------------------
# 5. Tool-loop dispatch fires when Gemma calls a tool (P1).
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 6. Branch scope (feature-tree-as-map.md §4)
# ---------------------------------------------------------------------------


@pytest.fixture
def stub_clean_gemma_async(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Patch BOTH ``generate_with_tools_loop`` (tool-loop path) AND
    ``generate_async`` (branch opener path). The branch opener
    short-circuits to ``generate_async`` when ``history`` is empty."""
    captured: dict[str, Any] = {"calls": [], "async_calls": []}

    async def fake_loop(**kwargs: Any) -> tuple[str, list[ToolCallTurn]]:
        captured["calls"].append(kwargs)
        return "Branch summary placeholder.", []

    async def fake_async(**kwargs: Any) -> str:
        captured["async_calls"].append(kwargs)
        return (
            "From the root career, the \"Computer and Information Systems "
            "Managers\" path moves you upstream of the day-to-day work. "
            "What would you like to dig into?"
        )

    monkeypatch.setattr(gemma_client, "generate_with_tools_loop", fake_loop)
    monkeypatch.setattr(gemma_client, "generate_async", fake_async)
    return captured


def test_post_chat_ask_kind_branch(
    client: TestClient,
    stub_clean_gemma_async: dict[str, Any],
) -> None:
    """E2E POST /chat/ask with kind=branch + target_id=branch.to_soc.
    Resolves to the matched-branch context-builder path. Empty history
    routes through ``generate_async`` (opener path, tools disabled).
    The call_site logs as ``ask_gemma_branch_opener``."""
    build = _make_build(with_branches=True)

    resp = client.post(
        "/chat/ask",
        json={
            "scope": {
                "kind": "branch",
                "build_ids": [build.build_id],
                "target_id": "11-3021",
            },
            "message": "What's the upside here?",
            "history": [],
            "locale": "en",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "response" in body
    assert "tool_calls" in body
    assert isinstance(body["response"], str)

    # Empty-history opener went through generate_async, NOT the
    # tool-loop. Tool calls list is therefore empty.
    assert body["tool_calls"] == []
    assert len(stub_clean_gemma_async["async_calls"]) == 1
    assert len(stub_clean_gemma_async["calls"]) == 0
    call = stub_clean_gemma_async["async_calls"][0]
    extra = call["extra"]
    assert extra["call_site"] == "ask_gemma_branch_opener"
    assert extra["scope_target_id"] == "11-3021"


def test_post_chat_ask_kind_branch_root_anchor(
    client: TestClient,
    stub_clean_gemma_async: dict[str, Any],
) -> None:
    """target_id == build's root soc_code → anchor-at-root opener path."""
    build = _make_build(with_branches=True)
    resp = client.post(
        "/chat/ask",
        json={
            "scope": {
                "kind": "branch",
                "build_ids": [build.build_id],
                "target_id": "15-1252",  # The build's root soc_code.
            },
            "message": "Where could this take me?",
            "history": [],
            "locale": "en",
        },
    )
    assert resp.status_code == 200, resp.text
    assert len(stub_clean_gemma_async["async_calls"]) == 1
    extra = stub_clean_gemma_async["async_calls"][0]["extra"]
    assert extra["call_site"] == "ask_gemma_branch_opener"


def test_post_chat_ask_kind_branch_with_history_uses_tool_loop(
    client: TestClient,
    stub_clean_gemma_async: dict[str, Any],
) -> None:
    """Non-empty history forces the standard tool-loop path. The
    call_site changes from ``ask_gemma_branch_opener`` to
    ``ask_gemma_branch``."""
    build = _make_build(with_branches=True)
    resp = client.post(
        "/chat/ask",
        json={
            "scope": {
                "kind": "branch",
                "build_ids": [build.build_id],
                "target_id": "11-3021",
            },
            "message": "Tell me more about the salary.",
            "history": [
                {"role": "user", "content": "First question"},
                {"role": "assistant", "content": "First answer"},
            ],
            "locale": "en",
        },
    )
    assert resp.status_code == 200, resp.text
    # Tool-loop path: generate_with_tools_loop fired, not generate_async.
    assert len(stub_clean_gemma_async["calls"]) == 1
    assert len(stub_clean_gemma_async["async_calls"]) == 0
    extra = stub_clean_gemma_async["calls"][0]["extra"]
    assert extra["call_site"] == "ask_gemma_branch"
    assert extra["scope_target_id"] == "11-3021"


@pytest.mark.parametrize(
    "scope, expected_substring",
    [
        # No target_id at all → 422 from Pydantic.
        (
            {"kind": "branch", "build_ids": ["x"]},
            "branch scope requires target_id",
        ),
        # Empty-string target_id → 422.
        (
            {"kind": "branch", "build_ids": ["x"], "target_id": ""},
            "branch scope requires target_id",
        ),
        # >1 build_ids → 422.
        (
            {
                "kind": "branch",
                "build_ids": ["a", "b"],
                "target_id": "11-3021",
            },
            "branch scope requires exactly 1 build_id",
        ),
    ],
    ids=["branch_no_target", "branch_empty_target", "branch_two_builds"],
)
def test_branch_scope_validation(
    client: TestClient,
    scope: dict[str, Any],
    expected_substring: str,
) -> None:
    """Pydantic ``AskScope.model_validator`` rejects malformed branch
    payloads with 422 before the handler runs."""
    resp = client.post(
        "/chat/ask",
        json={
            "scope": scope,
            "message": "anything",
            "history": [],
            "locale": "en",
        },
    )
    assert resp.status_code == 422, resp.text
    assert expected_substring in resp.text, (
        f"Expected {expected_substring!r} in 422 body; got {resp.text}"
    )


def test_branch_tool_loop_dispatches_get_career_branches(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the user asks 'what if I went into <X>' (an off-tree
    branch), Gemma can call ``get_career_branches`` via the tool loop.
    Asserts: (a) the new MCP tool fires, (b) tool_calls is populated,
    (c) call_site is ``ask_gemma_branch``."""
    build = _make_build(with_branches=True)

    # Mock the tool-loop to simulate a successful get_career_branches
    # call in the loop's tool-call log.
    captured: dict[str, Any] = {"loop_kwargs": []}

    async def fake_loop(**kwargs: Any) -> tuple[str, list[ToolCallTurn]]:
        captured["loop_kwargs"].append(kwargs)
        log = [
            ToolCallTurn(
                turn_number=0,
                tool_name="get_career_branches",
                tool_args={"soc_code": "13-2052", "primary_only": True},
                tool_result_size_bytes=2048,
                duration_ms=124,
                error=None,
            ),
        ]
        return (
            "Pivoting into financial analysis would mean a different "
            "wage profile. The destination role's median wage and "
            "education requirements are different.",
            log,
        )

    monkeypatch.setattr(gemma_client, "generate_with_tools_loop", fake_loop)

    # Use a non-empty history so we hit the tool-loop path (not the
    # opener short-circuit).
    resp = client.post(
        "/chat/ask",
        json={
            "scope": {
                "kind": "branch",
                "build_ids": [build.build_id],
                "target_id": "11-3021",
            },
            "message": "What if I went into financial analysis instead?",
            "history": [
                {"role": "user", "content": "first turn"},
                {"role": "assistant", "content": "first answer"},
            ],
            "locale": "en",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # The tool call surfaced on AskResponse.tool_calls.
    assert len(body["tool_calls"]) == 1
    tc = body["tool_calls"][0]
    assert tc["tool"] == "get_career_branches"
    assert tc["ok"] is True
    assert tc["duration_ms"] == 124

    # call_site stamped correctly on the loop kwargs (visible in
    # logs/gemma.jsonl when a real Gemma call fires).
    assert len(captured["loop_kwargs"]) == 1
    extra = captured["loop_kwargs"][0]["extra"]
    assert extra["call_site"] == "ask_gemma_branch"

    # The tool schema for ``get_career_branches`` was published into the
    # tools list passed to generate_with_tools_loop. (The tool schemas
    # come from mcp_client.get_tool_openai_schema; if it returns None
    # the tool is silently skipped, so we assert presence by name.)
    tools = captured["loop_kwargs"][0].get("tools", [])
    tool_names = {
        t.get("function", {}).get("name") for t in tools if isinstance(t, dict)
    }
    assert "get_career_branches" in tool_names, (
        f"get_career_branches missing from tool list; got {tool_names}"
    )


def test_tool_loop_dispatches_to_mcp(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mock ``generate_with_tools_loop`` to simulate a successful tool
    call. Assert the response carries the tool-call telemetry on
    ``tool_calls`` so the routing/E2E test (and the UI's debug view)
    can see it. Per the service contract, ``tool_calls`` is shaped
    ``[{"tool": str, "ok": bool, "duration_ms": int}, ...]``.
    """
    build = _make_build()

    async def fake_loop(**kwargs: Any) -> tuple[str, list[ToolCallTurn]]:
        # Simulate one successful tool call followed by a clean answer.
        log = [
            ToolCallTurn(
                turn_number=0,
                tool_name="get_career_paths",
                tool_args={"unitid": 110635, "cipcode": "11.0701"},
                tool_result_size_bytes=1234,
                duration_ms=87,
                error=None,
            ),
        ]
        return (
            "Switching majors generally requires running it as a new pick.",
            log,
        )

    monkeypatch.setattr(gemma_client, "generate_with_tools_loop", fake_loop)

    resp = client.post(
        "/chat/ask",
        json={
            "scope": {"kind": "build", "build_ids": [build.build_id]},
            "message": "What if I picked Mechanical Engineering?",
            "history": [],
            "locale": "en",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["response"].startswith("Switching majors")
    # tool_calls is populated. The summary shape from ask_gemma.chat_ask.
    assert len(body["tool_calls"]) == 1
    tc = body["tool_calls"][0]
    assert tc["tool"] == "get_career_paths"
    assert tc["ok"] is True
    assert tc["duration_ms"] == 87
