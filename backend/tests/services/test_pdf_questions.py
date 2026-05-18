"""Tests for app.services.pdf_questions — Gemma-call wiring + fallback paths.

Every code path emits exactly one ``logs/gemma.jsonl`` record (architect's
G3 contract). The 5 ``GemmaPath`` literals are:

    live, fallback_timeout, fallback_empty, fallback_malformed, fallback_disabled

Each test patches ``gemma_client.generate_chat_async`` to drive a specific
code path and asserts the gemma_path stamp on the returned AudienceQuestions
plus the number/shape of jsonl records emitted.

NEVER calls live Ollama or OpenRouter from these tests.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from app.services import gemma_client, pdf_questions

# ---------------------------------------------------------------------------
# Helpers — build a valid Gemma JSON response, capture jsonl records, etc.
# ---------------------------------------------------------------------------


def _valid_gemma_json() -> str:
    """A well-formed JSON response that exercises the 'live' path."""
    return json.dumps({
        "ask_the_college": [
            "Does Indiana University publish placement rates for "
            "Mechanical Engineering grads one year out?",
            "Can the department connect me with a co-op coordinator who "
            "places students into manufacturing roles?",
        ],
        "ask_your_parents": [
            "If we model debt at 50%, can our family carry the monthly "
            "payment alongside everything else after I graduate?",
        ],
        "ask_yourself": [
            "Will I still want to be doing this work in 10 years?",
        ],
    })


@pytest.fixture
def patched_jsonl(monkeypatch, tmp_path):
    """Redirect the Gemma jsonl writer to a tmp file. Returns a callable
    that reads back all records as a list of dicts.

    Patches ``_log_path`` (the cached resolver) AND clears
    ``GEMMA_LOG_DISABLED`` so synthetic events actually fire.
    """
    monkeypatch.delenv("GEMMA_LOG_DISABLED", raising=False)
    log_file = tmp_path / "gemma.jsonl"
    monkeypatch.setattr(gemma_client, "_log_path", lambda: log_file)

    def _read_records() -> list[dict]:
        if not log_file.exists():
            return []
        out = []
        for line in log_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
        return out

    return _read_records


# ---------------------------------------------------------------------------
# P0: static_fallback_when_gemma_times_out
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_static_fallback_when_gemma_times_out(
    monkeypatch, fixture_build, patched_jsonl,
):
    """``asyncio.TimeoutError`` from generate_chat_async → fallback_timeout.

    Mandatory college questions present at indices [0, 1].
    All three audiences floor at >= 1 question.
    """
    async def _raises_timeout(**kwargs):
        raise asyncio.TimeoutError("Gemma timed out for testing")

    monkeypatch.setattr(
        gemma_client, "generate_chat_async", _raises_timeout
    )

    result = await pdf_questions.generate_audience_questions(fixture_build)

    assert result.gemma_path == "fallback_timeout"
    # Two mandatory college questions at the head of ask_the_college.
    assert result.ask_the_college[0].is_static_mandatory is True
    assert result.ask_the_college[1].is_static_mandatory is True
    # Every audience has at least one question.
    assert len(result.ask_the_college) >= 1
    assert len(result.ask_your_parents) >= 1
    assert len(result.ask_yourself) >= 1

    records = patched_jsonl()
    assert len(records) == 1, f"expected exactly one jsonl record, got {records}"
    assert records[0]["event"] == "fallback_timeout"
    assert records[0]["call_site"] == "pdf_questions"
    assert records[0]["synthetic"] is True


# ---------------------------------------------------------------------------
# P0: static_fallback_when_gemma_returns_malformed_json
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_static_fallback_when_gemma_returns_malformed_json(
    monkeypatch, fixture_build, patched_jsonl,
):
    """Non-JSON response → fallback_malformed."""
    monkeypatch.setattr(
        gemma_client,
        "generate_chat_async",
        AsyncMock(return_value="this is not valid JSON at all"),
    )

    result = await pdf_questions.generate_audience_questions(fixture_build)

    assert result.gemma_path == "fallback_malformed"
    assert len(result.ask_the_college) >= 1
    records = patched_jsonl()
    assert len(records) == 1
    assert records[0]["event"] == "fallback_malformed"


@pytest.mark.asyncio
async def test_static_fallback_when_gemma_returns_wrong_schema(
    monkeypatch, fixture_build, patched_jsonl,
):
    """Valid JSON but missing required keys → fallback_malformed."""
    monkeypatch.setattr(
        gemma_client,
        "generate_chat_async",
        AsyncMock(return_value=json.dumps({"unrelated": [1, 2, 3]})),
    )

    result = await pdf_questions.generate_audience_questions(fixture_build)
    assert result.gemma_path == "fallback_malformed"


# ---------------------------------------------------------------------------
# P0: static_fallback_when_gemma_returns_empty
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_static_fallback_when_gemma_returns_empty(
    monkeypatch, fixture_build, patched_jsonl,
):
    """Empty string from gemma_client → fallback_empty."""
    monkeypatch.setattr(
        gemma_client, "generate_chat_async", AsyncMock(return_value="")
    )

    result = await pdf_questions.generate_audience_questions(fixture_build)
    assert result.gemma_path == "fallback_empty"
    records = patched_jsonl()
    assert len(records) == 1
    assert records[0]["event"] == "fallback_empty"


# ---------------------------------------------------------------------------
# P0: two_static_college_questions_always_present (even on Gemma success)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_two_static_college_questions_always_present(
    monkeypatch, fixture_build,
):
    """Indices [0, 1] of ask_the_college are the static-mandatory pair —
    even when Gemma succeeds. Gemma's contributions follow.
    """
    monkeypatch.setattr(
        gemma_client,
        "generate_chat_async",
        AsyncMock(return_value=_valid_gemma_json()),
    )

    result = await pdf_questions.generate_audience_questions(fixture_build)

    assert result.gemma_path == "live"
    assert len(result.ask_the_college) >= 2
    # Indices [0, 1] are the static-mandatory pair.
    assert result.ask_the_college[0].is_static_mandatory is True
    assert result.ask_the_college[1].is_static_mandatory is True
    # Mandatory[0] interpolates the school name.
    assert "Indiana University" in result.ask_the_college[0].text
    # Gemma's contributions follow at index 2+ and are not flagged mandatory.
    if len(result.ask_the_college) >= 3:
        assert result.ask_the_college[2].is_static_mandatory is False


# ---------------------------------------------------------------------------
# Missing-earnings 3rd-mandatory question — mirrors InsufficientDataBanner.
# When build.career.stats.ern and stats.roi are both None, the static
# college questions get a 3rd mandatory entry pointing the student at the
# missing data with the program name interpolated.
# ---------------------------------------------------------------------------


def test_missing_earnings_question_appended_when_both_stats_null():
    """Build with null ERN+ROI: 3rd mandatory question appears with the
    program name interpolated.
    """
    from tests.services.conftest import make_fixture_build

    build = make_fixture_build(
        program_name="Finance",
        stats_override={"ern": None, "roi": None},
    )

    questions = pdf_questions._static_college_questions(build, locale="en")

    # 2 original mandatory + 1 missing-earnings mandatory + 1 fallback.
    assert len(questions) == 4
    assert questions[0].is_static_mandatory is True
    assert questions[1].is_static_mandatory is True
    assert questions[2].is_static_mandatory is True
    assert questions[3].is_static_mandatory is False

    # The new mandatory entry mentions the missing data and interpolates
    # the program name so the student walks into the conversation knowing
    # exactly what they're asking about.
    missing_q = questions[2].text
    assert "Federal earnings data isn't published" in missing_q
    assert "Finance" in missing_q
    assert "federal loans" in missing_q


def test_missing_earnings_question_omitted_when_stats_populated(fixture_build):
    """Build with non-null stats: only the original 2 mandatory + 1
    fallback. No 3rd mandatory question.
    """
    questions = pdf_questions._static_college_questions(fixture_build, locale="en")
    assert len(questions) == 3
    assert questions[0].is_static_mandatory is True
    assert questions[1].is_static_mandatory is True
    assert questions[2].is_static_mandatory is False


def test_missing_earnings_question_omitted_when_only_ern_is_null():
    """Predicate is AND, not OR — matches the screen-level banner gate."""
    from tests.services.conftest import make_fixture_build

    build = make_fixture_build(stats_override={"ern": None})  # roi stays 7
    questions = pdf_questions._static_college_questions(build, locale="en")
    assert len(questions) == 3  # no 3rd mandatory entry


@pytest.mark.asyncio
async def test_missing_earnings_question_survives_live_gemma_path(
    monkeypatch, patched_jsonl,
):
    """Regression guard against the _live_assemble [:2] slice bug.

    When ERN+ROI are both null AND Gemma returns valid JSON, the live
    path used to drop the 3rd mandatory question because the slice took
    only the first 2 entries. The fix preserves every mandatory entry.
    """
    from tests.services.conftest import make_fixture_build

    build = make_fixture_build(
        program_name="Finance",
        stats_override={"ern": None, "roi": None},
    )
    monkeypatch.setattr(
        gemma_client,
        "generate_chat_async",
        AsyncMock(return_value=_valid_gemma_json()),
    )

    result = await pdf_questions.generate_audience_questions(build)

    assert result.gemma_path == "live"
    mandatory_qs = [
        q for q in result.ask_the_college if q.is_static_mandatory
    ]
    assert len(mandatory_qs) == 3, (
        "live Gemma path dropped the missing-earnings mandatory question — "
        "the _live_assemble [:2] slice regressed"
    )
    # The new mandatory carries the missing-earnings copy + program name.
    missing_q_text = mandatory_qs[2].text
    assert "Federal earnings data isn't published" in missing_q_text
    assert "Finance" in missing_q_text


def test_missing_earnings_question_truncates_long_program_across_locales():
    """50-char CIP names (real example: Harvard's matched program for
    'Finance' resolves to 'Business Administration, Management and
    Operations') must not blow the AudienceQuestion 240-char cap in any
    locale — Spanish has the tightest budget.
    """
    from tests.services.conftest import make_fixture_build

    long_program = "Business Administration, Management and Operations"
    assert len(long_program) > 40  # sanity: actually long
    build = make_fixture_build(
        program_name=long_program,
        stats_override={"ern": None, "roi": None},
    )
    for locale in ("en", "es", "ar"):
        questions = pdf_questions._static_college_questions(build, locale=locale)
        assert len(questions) == 4
        missing = questions[2]
        # Pydantic enforces max_length=240 on construction — if this
        # line builds without ValidationError, the cap was respected.
        assert len(missing.text) <= 240, (
            f"locale={locale!r} produced {len(missing.text)} chars (>240)"
        )
        assert missing.is_static_mandatory is True


def test_fit_program_to_template_truncates_with_ellipsis():
    """Direct unit test on the helper — short names pass through,
    long names get truncated + ellipsis, all within budget.
    """
    template = "Federal earnings data isn't published for your {program}."
    # Short — pass through unchanged.
    assert pdf_questions._fit_program_to_template(template, "Nursing") == "Nursing"
    # Long — truncated with ellipsis suffix.
    long_name = "x" * 500
    fitted = pdf_questions._fit_program_to_template(template, long_name)
    formatted = template.format(program=fitted)
    assert len(formatted) <= 240
    assert fitted.endswith("…")


# ---------------------------------------------------------------------------
# P0: audience_caps_enforced — Gemma 4-5 accepted; 6+ clipped or rejected.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audience_caps_enforced_4_per_audience_accepted(
    monkeypatch, fixture_build,
):
    """4 Gemma questions per audience: accept (Pydantic max_length=5)."""
    payload = json.dumps({
        "ask_the_college": [f"College Q {i}?" for i in range(4)],
        "ask_your_parents": [f"Parents Q {i}?" for i in range(4)],
        "ask_yourself": [f"Will I Q {i}?" for i in range(4)],
    })
    monkeypatch.setattr(
        gemma_client,
        "generate_chat_async",
        AsyncMock(return_value=payload),
    )

    result = await pdf_questions.generate_audience_questions(fixture_build)

    assert result.gemma_path == "live"
    # College has 2 mandatory + 3 from Gemma (capped at 3 per _live_assemble).
    assert 2 <= len(result.ask_the_college) <= 5
    # Parents/yourself max at 4 (Gemma returned 4).
    assert 1 <= len(result.ask_your_parents) <= 5
    assert 1 <= len(result.ask_yourself) <= 5


@pytest.mark.asyncio
async def test_audience_caps_enforced_6_clips_or_falls_back(
    monkeypatch, fixture_build,
):
    """6+ questions per audience: implementation clips at 5 OR falls back.

    Read pdf_questions.py: _assemble does `[:5]` (a hard slice), so 6
    Gemma questions are accepted and clipped to 5 — NOT a fallback.
    Per spec, assert what it actually does.
    """
    payload = json.dumps({
        "ask_the_college": [f"College Q {i}?" for i in range(6)],
        "ask_your_parents": [f"Parents Q {i}?" for i in range(6)],
        "ask_yourself": [f"Will I Q {i}?" for i in range(6)],
    })
    monkeypatch.setattr(
        gemma_client,
        "generate_chat_async",
        AsyncMock(return_value=payload),
    )

    result = await pdf_questions.generate_audience_questions(fixture_build)

    # The implementation clips at 5 in _assemble — accept the live path.
    assert result.gemma_path == "live"
    # ALL audiences capped at <= 5.
    assert len(result.ask_the_college) <= 5
    assert len(result.ask_your_parents) <= 5
    assert len(result.ask_yourself) <= 5


# ---------------------------------------------------------------------------
# P0: every_gemma_path_emits_one_jsonl_record (G3 contract)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_every_gemma_path_emits_one_jsonl_record(
    monkeypatch, fixture_build, patched_jsonl, tmp_path,
):
    """All 5 GemmaPath values must each emit exactly one jsonl record.

    Architect's G3 contract — observability has zero blind spots.

    For 'live' we need to drive the real generate_chat_async path. We stub
    the OpenAI client at _cached_client level so the real generate_chat
    code (which calls _log_exchange) fires. For each fallback path we
    override the async wrapper directly.
    """

    # ------------------------------------------------------------------
    # Path 1: live — real generate_chat_async with a stubbed OpenAI client.
    # ------------------------------------------------------------------
    log_file = tmp_path / "gemma_live.jsonl"
    monkeypatch.setattr(gemma_client, "_log_path", lambda: log_file)
    monkeypatch.delenv("GEMMA_LOG_DISABLED", raising=False)
    monkeypatch.setenv("GEMMA_MAX_CONCURRENCY", "8")
    gemma_client.reset_cache()

    valid_json = _valid_gemma_json()

    class _Choice:
        def __init__(self, content: str):
            self.message = type("M", (), {"content": content})()
            self.finish_reason = "stop"

    class _Response:
        def __init__(self, content: str):
            self.choices = [_Choice(content)]
            self.usage = type(
                "U", (), {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            )()

    class _Completions:
        def create(self, **kwargs):
            return _Response(valid_json)

    class _Chat:
        def __init__(self):
            self.completions = _Completions()

    class _StubClient:
        def __init__(self):
            self.chat = _Chat()

    cfg = gemma_client.InferenceConfig(
        backend="openrouter",
        base_url="http://stub",
        api_key="stub",
        model="gemma4:e4b",
    )
    from functools import lru_cache

    stub_client = _StubClient()

    @lru_cache(maxsize=1)
    def _stub_cached_client():
        return stub_client, cfg

    monkeypatch.setattr(gemma_client, "_cached_client", _stub_cached_client)

    result = await pdf_questions.generate_audience_questions(fixture_build)
    assert result.gemma_path == "live"

    live_records = [
        json.loads(ln)
        for ln in log_file.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    # Live path emits exactly ONE transport-level record (not synthetic).
    assert len(live_records) == 1, (
        f"live path should emit 1 jsonl record, got {len(live_records)}"
    )
    # Live record is NOT marked synthetic.
    assert live_records[0].get("synthetic") is not True
    # Confirm it's the transport-level record (carries response field).
    assert "response" in live_records[0]

    gemma_client.reset_cache()

    # ------------------------------------------------------------------
    # Paths 2-4: fallback_timeout, fallback_empty, fallback_malformed.
    # Each gets a fresh tmp jsonl file so we can count records cleanly.
    # ------------------------------------------------------------------

    for path_name, mock_setup in [
        (
            "fallback_timeout",
            lambda: AsyncMock(side_effect=asyncio.TimeoutError("forced")),
        ),
        (
            "fallback_empty",
            lambda: AsyncMock(return_value=""),
        ),
        (
            "fallback_malformed",
            lambda: AsyncMock(return_value="not valid json"),
        ),
    ]:
        log_path = tmp_path / f"gemma_{path_name}.jsonl"
        monkeypatch.setattr(gemma_client, "_log_path", lambda p=log_path: p)
        monkeypatch.setattr(
            gemma_client, "generate_chat_async", mock_setup()
        )

        r = await pdf_questions.generate_audience_questions(fixture_build)
        assert r.gemma_path == path_name, (
            f"expected {path_name}, got {r.gemma_path}"
        )

        records = [
            json.loads(ln)
            for ln in log_path.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        assert len(records) == 1, (
            f"{path_name} should emit exactly 1 jsonl record, got "
            f"{len(records)}"
        )
        assert records[0]["event"] == path_name
        assert records[0]["synthetic"] is True
        assert records[0]["call_site"] == "pdf_questions"

    # ------------------------------------------------------------------
    # Path 5: fallback_disabled — generate_chat_async raises a non-Timeout
    # exception (e.g. cold env, missing OPENROUTER_API_KEY).
    # ------------------------------------------------------------------
    log_path = tmp_path / "gemma_disabled.jsonl"
    monkeypatch.setattr(gemma_client, "_log_path", lambda p=log_path: p)

    async def _raises_runtime(**kwargs):
        raise RuntimeError("OPENROUTER_API_KEY not set in test env")

    monkeypatch.setattr(gemma_client, "generate_chat_async", _raises_runtime)

    r = await pdf_questions.generate_audience_questions(fixture_build)
    assert r.gemma_path == "fallback_disabled"

    records = [
        json.loads(ln)
        for ln in log_path.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    assert len(records) == 1
    assert records[0]["event"] == "fallback_disabled"
    assert records[0]["synthetic"] is True


# ---------------------------------------------------------------------------
# P0: gemma_client_called_with_timeout_and_json_mode (G1 contract)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gemma_client_called_with_timeout_and_json_mode(
    monkeypatch, fixture_build, patched_jsonl,
):
    """The call into gemma_client must include timeout_s=6.0 and
    response_format='json'. Architect's G1 contract.
    """
    captured_kwargs: dict = {}

    async def _capturing_call(**kwargs):
        captured_kwargs.update(kwargs)
        return _valid_gemma_json()

    monkeypatch.setattr(
        gemma_client, "generate_chat_async", _capturing_call
    )

    result = await pdf_questions.generate_audience_questions(fixture_build)
    assert result.gemma_path == "live"

    assert "timeout_s" in captured_kwargs, (
        "pdf_questions must pass timeout_s into generate_chat_async"
    )
    assert captured_kwargs["timeout_s"] == 6.0, (
        f"timeout_s must be 6.0 per spec G1; got "
        f"{captured_kwargs['timeout_s']!r}"
    )

    assert "response_format" in captured_kwargs, (
        "pdf_questions must pass response_format into generate_chat_async"
    )
    rf = captured_kwargs["response_format"]
    # Either the string shorthand "json" or the OpenAI-compat dict shape.
    assert rf == "json" or (
        isinstance(rf, dict) and rf.get("type") == "json_object"
    ), (
        f"response_format must be 'json' or {{'type': 'json_object'}}; "
        f"got {rf!r}"
    )


# ---------------------------------------------------------------------------
# P0: code_fence_wrapped_json_is_parsed (A3)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_code_fence_wrapped_json_is_parsed(
    monkeypatch, fixture_build, patched_jsonl,
):
    """OpenRouter sometimes wraps JSON in ```json…``` fences despite
    response_format. pdf_questions must strip the fence before parsing,
    landing on gemma_path='live' (NOT fallback_malformed).
    """
    body = _valid_gemma_json()
    fenced = f"```json\n{body}\n```"

    monkeypatch.setattr(
        gemma_client,
        "generate_chat_async",
        AsyncMock(return_value=fenced),
    )

    result = await pdf_questions.generate_audience_questions(fixture_build)

    assert result.gemma_path == "live", (
        f"expected 'live' after fence stripping; got {result.gemma_path!r}"
    )


@pytest.mark.asyncio
async def test_code_fence_without_json_marker_is_also_parsed(
    monkeypatch, fixture_build, patched_jsonl,
):
    """The fence stripper handles bare ``` (no 'json' marker) too."""
    body = _valid_gemma_json()
    fenced = f"```\n{body}\n```"

    monkeypatch.setattr(
        gemma_client,
        "generate_chat_async",
        AsyncMock(return_value=fenced),
    )

    result = await pdf_questions.generate_audience_questions(fixture_build)
    assert result.gemma_path == "live"


# ---------------------------------------------------------------------------
# Forbidden vocabulary — Gemma output containing RPG terms triggers fallback.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forbidden_term_in_gemma_output_triggers_fallback(
    monkeypatch, fixture_build, patched_jsonl,
):
    """Gemma output containing 'boss' or 'ROI' (or any forbidden term)
    must trigger fallback_malformed — the post-filter is the last line
    of defense before printed pages reach a counselor's desk.
    """
    payload = json.dumps({
        "ask_the_college": [
            "Does Indiana University publish boss-fight outcomes for ME grads?"
        ],
        "ask_your_parents": ["Can our family carry the monthly payment?"],
        "ask_yourself": ["Will I want this in 10 years?"],
    })
    monkeypatch.setattr(
        gemma_client,
        "generate_chat_async",
        AsyncMock(return_value=payload),
    )

    result = await pdf_questions.generate_audience_questions(fixture_build)

    assert result.gemma_path == "fallback_malformed", (
        f"forbidden 'boss' in Gemma output must trigger fallback; got "
        f"{result.gemma_path!r}"
    )


@pytest.mark.asyncio
async def test_forbidden_stat_abbreviation_triggers_fallback(
    monkeypatch, fixture_build, patched_jsonl,
):
    """Stat abbreviations (ERN/ROI/RES/GRW/AURA) are in
    FORBIDDEN_IN_GEMMA_OUTPUT but NOT in RPG_TERMS_FORBIDDEN_IN_PDF.
    Gemma using one of them in a question must trigger fallback.
    """
    payload = json.dumps({
        "ask_the_college": [
            "Does the ROI on this program justify the cost over 4 years?"
        ],
        "ask_your_parents": ["Can our family carry the monthly payment?"],
        "ask_yourself": ["Will I want this in 10 years?"],
    })
    monkeypatch.setattr(
        gemma_client,
        "generate_chat_async",
        AsyncMock(return_value=payload),
    )

    result = await pdf_questions.generate_audience_questions(fixture_build)
    assert result.gemma_path == "fallback_malformed"


# ---------------------------------------------------------------------------
# P1: voice rules — audience-first vs student-first prefix.
# Per-spec these are system-prompt assertions; we exercise the parser's
# tolerance for valid voice patterns rather than trying to grade Gemma.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_voice_audience_first_for_college_and_parents_passes(
    monkeypatch, fixture_build,
):
    """Audience-first questions ('Does …', 'Can our family …') flow through."""
    payload = json.dumps({
        "ask_the_college": [
            "Does Indiana University publish placement rates for ME grads?",
        ],
        "ask_your_parents": [
            "Can our family carry the monthly payment after I graduate?",
        ],
        "ask_yourself": [
            "Will I still want to be doing this work in 10 years?",
        ],
    })
    monkeypatch.setattr(
        gemma_client,
        "generate_chat_async",
        AsyncMock(return_value=payload),
    )
    result = await pdf_questions.generate_audience_questions(fixture_build)
    assert result.gemma_path == "live"
    # Verify mandatories at [0, 1] in college; Gemma's audience-first
    # additions follow.
    college_texts = [q.text for q in result.ask_the_college[2:]]
    for q in college_texts:
        # Audience-first: should NOT begin with "Will I" or "Am I" markers.
        assert not q.startswith("Will I"), q
        assert not q.startswith("Am I"), q


@pytest.mark.asyncio
async def test_voice_student_first_for_ask_yourself_passes(
    monkeypatch, fixture_build,
):
    """Student-first 'Will I' / 'Am I' patterns are accepted for self."""
    payload = json.dumps({
        "ask_the_college": ["Does the school publish outcomes data?"],
        "ask_your_parents": ["Can our family handle the loan payments?"],
        "ask_yourself": [
            "Will I be content with this career in 10 years?",
            "Am I picking this because it interests me?",
        ],
    })
    monkeypatch.setattr(
        gemma_client,
        "generate_chat_async",
        AsyncMock(return_value=payload),
    )
    result = await pdf_questions.generate_audience_questions(fixture_build)
    assert result.gemma_path == "live"
    yourself_texts = [q.text for q in result.ask_yourself]
    assert any(
        t.startswith("Will I") or t.startswith("Am I") for t in yourself_texts
    )


# ---------------------------------------------------------------------------
# Strength/risk framing — past failures here produced contradictory
# questions like "Will I be satisfied with a low earnings ceiling?" when
# the student had actually cleared the Ceiling fight. The user prompt
# now strips the raw "Low"/"High" labels from boss names and uses
# "cleared" / "needs attention" phrasing that cannot be parsed as a
# noun-modifier. The system prompt also forbids framing cleared
# outcomes as problems.
# ---------------------------------------------------------------------------


def test_user_prompt_uses_cleared_phrasing_for_strengths(fixture_build):
    """Strengths render as ``<label> — cleared`` so a positive-direction
    noun like 'Earnings ceiling' can't be misread as 'low earnings
    ceiling'. Raw risk-level labels must not appear next to boss names.
    """
    prompt = pdf_questions._user_prompt(fixture_build)
    assert "cleared" in prompt.lower()
    # The label-as-adjective inversions we saw in production:
    assert "Earnings ceiling: Low" not in prompt
    assert "Earnings ceiling: High" not in prompt
    assert "Job market outlook: Low" not in prompt
    assert "Job market outlook: High" not in prompt


def test_user_prompt_uses_needs_attention_for_risks(fixture_build):
    """Risks render with descriptive phrasing rather than a raw level
    label so the prompt is unambiguous in both directions."""
    prompt = pdf_questions._user_prompt(fixture_build)
    assert "needs attention" in prompt.lower() or "(none ranked)" in prompt


def test_system_prompt_forbids_framing_strengths_as_problems():
    """The system prompt must explicitly tell Gemma that cleared
    outcomes are CONFIRMED GOOD and must never be described as
    problems — this is the safety net behind the user-prompt rewrite.
    """
    assert "CLEARED" in pdf_questions._SYSTEM
    assert "low earnings ceiling" in pdf_questions._SYSTEM.lower()
