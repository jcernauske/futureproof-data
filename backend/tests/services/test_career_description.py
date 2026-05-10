"""Tests for ``app.services.career_description``.

See ``docs/specs/feature-career-description-on-pdf.md`` §4 New Tests
Required (P0). Every test mocks ``gemma_client.generate_async`` and
``mcp_client.call_async``; the module never reaches a real backend.

Conventions:
    - ``career_description.clear_cache()`` runs before/after every test
      via the autouse ``_reset_career_description_cache`` fixture.
    - ``gemma_client.generate_async`` is replaced with an async stub
      that returns a string (matches the empty-string-on-failure
      contract — exceptions are not the path).
    - ``mcp_client.call_async`` is replaced with an async stub returning
      ``{"data": {...}}`` (mirrors the production wrapper).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.models.career import CareerDescription
from app.services import career_description, gemma_client, mcp_client
from app.services.career_description import CareerDescriptionUnavailable

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_career_description_cache():
    """Drop the per-process single-flight cache between tests."""
    career_description.clear_cache()
    yield
    career_description.clear_cache()


def _activities_payload(n: int = 5) -> list[dict[str, Any]]:
    """Return a list of n O*NET activity dicts in the shape MCP returns."""
    bases = [
        ("Analyze financial filings and reports", 4.8),
        ("Build models that project earnings and risk", 4.5),
        ("Brief portfolio managers on findings", 4.2),
        ("Read industry reports", 4.0),
        ("Track positions after recommendations", 3.8),
        ("Mentor junior analysts", 3.6),
    ]
    return [
        {"activity": a, "importance": imp}
        for a, imp in bases[:n]
    ]


def _valid_gemma_json() -> str:
    """A well-formed Gemma JSON response with a 5-task list. Avoids every
    term in ``RPG_TERMS_FORBIDDEN_IN_PDF`` (notably 'build', 'win', 'draw')
    so voice validation passes deterministically.
    """
    return json.dumps({
        "summary": (
            "Financial analysts study filings and market data to guide "
            "investment decisions. They assemble models, brief managers, "
            "and track positions after recommendations."
        ),
        "tasks": [
            "Analyze company filings and earnings calls",
            "Assemble valuation and scenario models",
            "Brief portfolio managers on positions",
            "Read industry reports and competitor data",
            "Track recommendations and feed lessons back",
        ],
    })


@pytest.fixture
def patched_gemma(monkeypatch):
    """Replace gemma_client.generate_async with an AsyncMock returning
    valid JSON by default. Returns the mock so individual tests can
    set ``side_effect``/``return_value`` to drive different paths.
    """
    mock = AsyncMock(return_value=_valid_gemma_json())
    monkeypatch.setattr(gemma_client, "generate_async", mock)
    return mock


@pytest.fixture
def patched_mcp_activities(monkeypatch):
    """Default MCP stub: ``get_task_breakdown`` returns 5 activities
    (Tier A path).
    """
    async def fake_call(tool: str, args: dict[str, Any]) -> dict[str, Any]:
        if tool == "get_task_breakdown":
            return {
                "data": {
                    "top_5_activities": _activities_payload(5),
                    "top_human_activities": [],
                    "description": (
                        "Conduct quantitative analyses of financial markets "
                        "and information."
                    ),
                    "multi_detail_flag": False,
                },
            }
        return {"data": {}}

    monkeypatch.setattr(mcp_client, "call_async", fake_call)


@pytest.fixture
def patched_mcp_description_only(monkeypatch):
    """MCP stub for Tier B: no activities, but BLS description present."""
    async def fake_call(tool: str, args: dict[str, Any]) -> dict[str, Any]:
        if tool == "get_task_breakdown":
            return {
                "data": {
                    "top_5_activities": None,
                    "top_human_activities": None,
                    "description": (
                        "Emergency medical technicians and paramedics "
                        "respond to emergency calls, perform medical "
                        "services, and transport patients to medical "
                        "facilities."
                    ),
                    "multi_detail_flag": False,
                },
            }
        return {"data": {}}

    monkeypatch.setattr(mcp_client, "call_async", fake_call)


@pytest.fixture
def patched_mcp_title_only(monkeypatch):
    """MCP stub for Tier C: empty payload (no activities, no description)."""
    async def fake_call(tool: str, args: dict[str, Any]) -> dict[str, Any]:
        return {"data": {}}

    monkeypatch.setattr(mcp_client, "call_async", fake_call)


# ---------------------------------------------------------------------------
# 1. Happy path (Tier A)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_or_generate_happy_path(
    patched_gemma, patched_mcp_activities,
):
    """Pre-fetch returns activities → Gemma returns valid JSON → service
    returns a CareerDescription with anchor_tier='activities' and
    4-6 task bullets.
    """
    desc = await career_description.get_or_generate(
        "13-2051", "Financial and Investment Analysts",
    )

    assert isinstance(desc, CareerDescription)
    assert desc.soc_code == "13-2051"
    assert desc.anchor_tier == "activities"
    assert 4 <= len(desc.tasks) <= 6
    assert desc.summary
    assert len(desc.summary) <= 500
    # Each task ≤ 90 chars (after strip + dedup of trailing periods).
    for task in desc.tasks:
        assert len(task) <= 90
    # Gemma was called exactly once.
    assert patched_gemma.await_count == 1


# ---------------------------------------------------------------------------
# 2. Cache hit skips Gemma
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_hit_skips_gemma(
    patched_gemma, patched_mcp_activities,
):
    """Two sequential calls for the same SOC → exactly one Gemma call."""
    soc = "13-2051"
    title = "Financial and Investment Analysts"

    first = await career_description.get_or_generate(soc, title)
    second = await career_description.get_or_generate(soc, title)

    # Pydantic equality on the whole model — same generated_at timestamp
    # because second call was a cache hit, not a regeneration.
    assert first == second
    assert patched_gemma.await_count == 1, (
        f"Expected exactly 1 Gemma call across two get_or_generate calls; "
        f"got {patched_gemma.await_count}"
    )


# ---------------------------------------------------------------------------
# 3. Parse failure → retries → raises
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parse_failure_first_then_valid_returns(
    monkeypatch, patched_mcp_activities,
):
    """First Gemma response is malformed JSON; second is valid. Service
    returns the valid CareerDescription on the second attempt.
    """
    responses = ["this is not JSON at all", _valid_gemma_json()]
    mock = AsyncMock(side_effect=responses)
    monkeypatch.setattr(gemma_client, "generate_async", mock)

    desc = await career_description.get_or_generate(
        "13-2051", "Financial and Investment Analysts",
    )
    assert desc.anchor_tier == "activities"
    assert mock.await_count == 2


@pytest.mark.asyncio
async def test_parse_failure_both_attempts_raises(
    monkeypatch, patched_mcp_activities,
):
    """Both Gemma responses are malformed JSON → CareerDescriptionUnavailable."""
    mock = AsyncMock(side_effect=["nope", "still nope"])
    monkeypatch.setattr(gemma_client, "generate_async", mock)

    with pytest.raises(CareerDescriptionUnavailable):
        await career_description.get_or_generate(
            "13-2051", "Financial and Investment Analysts",
        )
    assert mock.await_count == 2


# ---------------------------------------------------------------------------
# 4. Voice validation rejects RPG terms
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_voice_validation_rejects_rpg_terms(
    monkeypatch, patched_mcp_activities,
):
    """Gemma response contains a forbidden 'boss' RPG term → retry.
    Persistent voice violation → CareerDescriptionUnavailable. Assert the
    second prompt to Gemma includes a 'do not use' reminder.
    """
    bad_json = json.dumps({
        "summary": (
            "Financial analysts win the boss fight against bad earnings. "
            "They study filings and brief their managers."
        ),
        "tasks": [
            "Analyze company filings",
            "Build valuation models",
            "Brief portfolio managers",
            "Track recommendations after a boss fight",
        ],
    })

    captured_systems: list[str] = []

    async def capturing_gemma(*, system: str, user: str, **kwargs):
        captured_systems.append(system)
        return bad_json

    monkeypatch.setattr(gemma_client, "generate_async", capturing_gemma)

    with pytest.raises(CareerDescriptionUnavailable):
        await career_description.get_or_generate(
            "13-2051", "Financial and Investment Analysts",
        )

    # Two attempts should have been made.
    assert len(captured_systems) == 2
    # The second prompt must include the "Do not use" reminder. The retry
    # surfaces the offending term back to Gemma.
    assert "Do not use" in captured_systems[1]
    assert "boss" in captured_systems[1].lower()
    # First prompt must NOT have the strengthened suffix.
    assert "Do not use the words" not in captured_systems[0]


# ---------------------------------------------------------------------------
# 5. Length caps enforced (summary > 500 or task > 90)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_length_caps_summary_too_long(
    monkeypatch, patched_mcp_activities,
):
    """Summary > 500 chars → parse failure → retry → if both bad → raise."""
    long_summary = "x" * 501
    bad = json.dumps({
        "summary": long_summary,
        "tasks": ["a one", "a two", "a three", "a four"],
    })
    mock = AsyncMock(side_effect=[bad, bad])
    monkeypatch.setattr(gemma_client, "generate_async", mock)

    with pytest.raises(CareerDescriptionUnavailable):
        await career_description.get_or_generate(
            "13-2051", "Financial and Investment Analysts",
        )
    assert mock.await_count == 2


@pytest.mark.asyncio
async def test_length_caps_task_too_long(
    monkeypatch, patched_mcp_activities,
):
    """A single task > 90 chars → parse failure path."""
    long_task = "x" * 91
    bad = json.dumps({
        "summary": "Reasonable summary.",
        "tasks": [long_task, "two", "three", "four"],
    })
    good = _valid_gemma_json()
    mock = AsyncMock(side_effect=[bad, good])
    monkeypatch.setattr(gemma_client, "generate_async", mock)

    desc = await career_description.get_or_generate(
        "13-2051", "Financial and Investment Analysts",
    )
    assert desc.anchor_tier == "activities"
    assert mock.await_count == 2


# ---------------------------------------------------------------------------
# 6. Task count bounds (< 4 or > 6)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_task_count_too_few(
    monkeypatch, patched_mcp_activities,
):
    """Only 3 tasks → parse failure → retry."""
    too_few = json.dumps({
        "summary": "Summary.",
        "tasks": ["a", "b", "c"],
    })
    good = _valid_gemma_json()
    mock = AsyncMock(side_effect=[too_few, good])
    monkeypatch.setattr(gemma_client, "generate_async", mock)

    desc = await career_description.get_or_generate(
        "13-2051", "Financial and Investment Analysts",
    )
    assert 4 <= len(desc.tasks) <= 6
    assert mock.await_count == 2


@pytest.mark.asyncio
async def test_task_count_too_many(
    monkeypatch, patched_mcp_activities,
):
    """7 tasks → parse failure → if both responses 7 → raise."""
    too_many = json.dumps({
        "summary": "Summary.",
        "tasks": [f"task {i}" for i in range(7)],
    })
    mock = AsyncMock(side_effect=[too_many, too_many])
    monkeypatch.setattr(gemma_client, "generate_async", mock)

    with pytest.raises(CareerDescriptionUnavailable):
        await career_description.get_or_generate(
            "13-2051", "Financial and Investment Analysts",
        )
    assert mock.await_count == 2


# ---------------------------------------------------------------------------
# 7. Anchor tier A — full activities
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_anchor_tier_a_full_activities(
    monkeypatch, patched_gemma,
):
    """Pre-fetch returns 5 parsed activities → Tier A prompt selected;
    result anchor_tier='activities'.
    """
    captured_systems: list[str] = []

    async def fake_call(tool: str, args: dict[str, Any]) -> dict[str, Any]:
        return {
            "data": {
                "top_5_activities": _activities_payload(5),
                "description": "BLS description",
                "multi_detail_flag": False,
            },
        }

    async def capturing_gemma(*, system: str, user: str, **kwargs):
        captured_systems.append(system)
        return _valid_gemma_json()

    monkeypatch.setattr(mcp_client, "call_async", fake_call)
    monkeypatch.setattr(gemma_client, "generate_async", capturing_gemma)

    desc = await career_description.get_or_generate(
        "13-2051", "Financial and Investment Analysts",
    )
    assert desc.anchor_tier == "activities"
    # Tier A prompt cites importance scores.
    assert len(captured_systems) == 1
    assert "importance" in captured_systems[0]


# ---------------------------------------------------------------------------
# 8. Anchor tier B — description only
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_anchor_tier_b_description_only(
    monkeypatch, patched_gemma, patched_mcp_description_only,
):
    """top_5_activities=None but BLS description populated → Tier B."""
    desc = await career_description.get_or_generate(
        "29-2042", "Emergency Medical Technicians",
    )
    assert desc.anchor_tier == "description_only"


@pytest.mark.asyncio
async def test_tier_b_falls_through_on_malformed_activities_json(
    monkeypatch, patched_gemma,
):
    """Malformed JSON in top_5_activities does NOT raise — it falls
    through to Tier B (description-only).
    """
    async def fake_call(tool: str, args: dict[str, Any]) -> dict[str, Any]:
        return {
            "data": {
                # Bogus stringified JSON — the parser should fail and
                # treat the activity list as empty.
                "top_5_activities": "{not valid json",
                "top_human_activities": None,
                "description": (
                    "Cardiologists diagnose and treat diseases of the heart."
                ),
            },
        }

    monkeypatch.setattr(mcp_client, "call_async", fake_call)

    desc = await career_description.get_or_generate(
        "29-1212", "Cardiologists",
    )
    # Falls through to Tier B because description is populated.
    assert desc.anchor_tier == "description_only"


# ---------------------------------------------------------------------------
# 9. Anchor tier C — title only
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_anchor_tier_c_title_only(
    monkeypatch, patched_gemma, patched_mcp_title_only,
):
    """Both activities + description missing → Tier C with title only."""
    desc = await career_description.get_or_generate(
        "13-1199", "Business Operations Specialists, All Other",
    )
    assert desc.anchor_tier == "title_only"


# ---------------------------------------------------------------------------
# 10. Tier D — malformed SOC raises before invoking Gemma
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tier_d_malformed_soc_raises_without_gemma(monkeypatch):
    """SOC fails ^\\d{2}-\\d{4}$ → CareerDescriptionUnavailable raised
    BEFORE any Gemma invocation.
    """
    gemma_mock = AsyncMock(return_value=_valid_gemma_json())
    monkeypatch.setattr(gemma_client, "generate_async", gemma_mock)
    mcp_mock = AsyncMock(return_value={"data": {}})
    monkeypatch.setattr(mcp_client, "call_async", mcp_mock)

    with pytest.raises(CareerDescriptionUnavailable):
        await career_description.get_or_generate(
            "bad-soc", "Mystery Career",
        )

    assert gemma_mock.await_count == 0, (
        "Tier D must reject malformed SOC before any Gemma call"
    )
    assert mcp_mock.await_count == 0, (
        "Tier D must reject malformed SOC before any MCP call"
    )


# ---------------------------------------------------------------------------
# 11. Single-flight: concurrent misses fan out only one Gemma call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_flight_concurrent_misses(
    monkeypatch, patched_mcp_activities,
):
    """Two concurrent get_or_generate calls for the same SOC while Gemma
    is in-flight → only one Gemma invocation; both calls receive the same
    CareerDescription.
    """
    call_count = 0
    in_flight = asyncio.Event()
    release = asyncio.Event()

    async def slow_gemma(*, system: str, user: str, **kwargs):
        nonlocal call_count
        call_count += 1
        in_flight.set()
        # Block until the second caller has had a chance to enter the
        # cache lookup.
        await release.wait()
        return _valid_gemma_json()

    monkeypatch.setattr(gemma_client, "generate_async", slow_gemma)

    async def caller():
        return await career_description.get_or_generate(
            "13-2051", "Financial and Investment Analysts",
        )

    task_a = asyncio.create_task(caller())
    # Wait for the first caller to be inside Gemma so we know the cache
    # entry exists for the second caller to join.
    await in_flight.wait()
    task_b = asyncio.create_task(caller())
    # Yield once so task_b enters get_or_generate and joins the same future.
    await asyncio.sleep(0)
    release.set()

    res_a, res_b = await asyncio.gather(task_a, task_b)

    assert call_count == 1, (
        f"Expected single-flight to dedupe Gemma; got {call_count} calls"
    )
    assert res_a == res_b


# ---------------------------------------------------------------------------
# 12. Empty string treated as transport failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_string_then_valid_returns(
    monkeypatch, patched_mcp_activities,
):
    """First Gemma call returns "" (transport failure), second returns
    valid JSON → returns CareerDescription on the second attempt.
    """
    mock = AsyncMock(side_effect=["", _valid_gemma_json()])
    monkeypatch.setattr(gemma_client, "generate_async", mock)

    desc = await career_description.get_or_generate(
        "13-2051", "Financial and Investment Analysts",
    )
    assert desc.anchor_tier == "activities"
    assert mock.await_count == 2


@pytest.mark.asyncio
async def test_empty_string_both_attempts_raises(
    monkeypatch, patched_mcp_activities,
):
    """Both Gemma calls return "" → CareerDescriptionUnavailable."""
    mock = AsyncMock(side_effect=["", ""])
    monkeypatch.setattr(gemma_client, "generate_async", mock)

    with pytest.raises(CareerDescriptionUnavailable):
        await career_description.get_or_generate(
            "13-2051", "Financial and Investment Analysts",
        )
    assert mock.await_count == 2


# ---------------------------------------------------------------------------
# 13. Voice retry uses strengthened prompt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_voice_retry_includes_offending_term_in_prompt(
    monkeypatch, patched_mcp_activities,
):
    """First response contains 'boss'; assert the second prompt sent to
    Gemma includes a 'do not use' reminder with the offending term.
    """
    bad_json = json.dumps({
        "summary": "Analysts join the boss fight to win the day.",
        "tasks": [
            "Analyze filings",
            "Build models",
            "Brief portfolio managers",
            "Win the boss fight",
        ],
    })
    good = _valid_gemma_json()

    captured: list[str] = []

    async def capturing_gemma(*, system: str, user: str, **kwargs):
        captured.append(system)
        return bad_json if len(captured) == 1 else good

    monkeypatch.setattr(gemma_client, "generate_async", capturing_gemma)

    desc = await career_description.get_or_generate(
        "13-2051", "Financial and Investment Analysts",
    )
    assert desc.anchor_tier == "activities"
    assert len(captured) == 2
    # Strengthened second prompt names the offending term back to Gemma.
    assert "Do not use" in captured[1]
    assert "boss" in captured[1].lower()


# ---------------------------------------------------------------------------
# 14. Parse retry uses strengthened prompt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parse_retry_uses_strengthened_prompt(
    monkeypatch, patched_mcp_activities,
):
    """First response is malformed JSON; assert second prompt includes
    'Output ONLY valid JSON matching the schema.'
    """
    captured: list[str] = []

    async def capturing_gemma(*, system: str, user: str, **kwargs):
        captured.append(system)
        if len(captured) == 1:
            return "this is definitely not JSON"
        return _valid_gemma_json()

    monkeypatch.setattr(gemma_client, "generate_async", capturing_gemma)

    desc = await career_description.get_or_generate(
        "13-2051", "Financial and Investment Analysts",
    )
    assert desc.anchor_tier == "activities"
    assert len(captured) == 2
    assert "Output ONLY valid JSON matching the schema" in captured[1]


# ---------------------------------------------------------------------------
# Markdown-leak regression: small Ollama models put **bold** inside the
# JSON summary/task strings. We strip those before returning.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_markdown_in_summary_and_tasks_is_stripped(
    monkeypatch, patched_mcp_activities,
):
    response = json.dumps({
        "summary": (
            "**Financial analysts** study filings and market data to guide "
            "*investment* decisions. They assemble models, brief managers."
        ),
        "tasks": [
            "Analyze **company filings** and earnings calls",
            "Assemble *valuation* and scenario models",
            "Brief portfolio managers on positions",
            "Read industry reports and competitor data",
        ],
    })
    monkeypatch.setattr(
        gemma_client, "generate_async", AsyncMock(return_value=response)
    )

    desc = await career_description.get_or_generate(
        "13-2051", "Financial and Investment Analysts",
    )
    assert "**" not in desc.summary
    assert "*investment*" not in desc.summary
    # Content survives stripping.
    assert "Financial analysts" in desc.summary
    for task in desc.tasks:
        assert "**" not in task
        assert "*valuation*" not in task
