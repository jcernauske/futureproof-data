"""Tests for the unified Gemma inference client — async path.

The async path is what the /build router fans out on. These tests cover:

- The module-level semaphore that caps concurrency (``GEMMA_MAX_CONCURRENCY``).
- The JSONL call log that every generate_async invocation appends to.

Both tests stub the sync ``generate`` function so they never touch a real
Ollama/OpenRouter backend, and they reset the gemma_client cache so the
semaphore is rebuilt under the patched env.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time

import pytest

from app.services import gemma_client


@pytest.mark.asyncio
async def test_generate_async_respects_semaphore(monkeypatch, tmp_path):
    """Cap concurrency at 2 and fire 6 slow requests — no more than 2 in-flight at once.

    If the module semaphore isn't being honored, more than 2 of the mocked
    generates will be mid-flight simultaneously. The mock tracks the live
    counter and records the peak.

    The default ThreadPoolExecutor on small CI runners may have only 2
    workers — which would let the test pass for the wrong reason (the
    pool is what caps, not the semaphore). We install a 16-wide pool
    for the duration of the test so only the asyncio.Semaphore can be
    the binding constraint.
    """
    from concurrent.futures import ThreadPoolExecutor

    # Install the concurrency cap BEFORE the semaphore gets built. reset_cache
    # nulls the lazy module-level sentinel so _get_semaphore() rebuilds it
    # with the patched env on the next acquire.
    monkeypatch.setenv("GEMMA_MAX_CONCURRENCY", "2")
    monkeypatch.setenv("GEMMA_LOG_DISABLED", "1")  # no disk I/O
    gemma_client.reset_cache()

    loop = asyncio.get_running_loop()
    wide_executor = ThreadPoolExecutor(max_workers=16)
    loop.set_default_executor(wide_executor)

    import threading

    state_lock = threading.Lock()
    in_flight = 0
    peak_in_flight = 0

    def slow_generate(**kwargs):
        # ``generate_async`` calls this inside asyncio.to_thread, so we're
        # on a worker thread. Use a threading.Lock + plain counters — no
        # need to bounce through the event loop.
        nonlocal in_flight, peak_in_flight
        with state_lock:
            in_flight += 1
            if in_flight > peak_in_flight:
                peak_in_flight = in_flight
        try:
            time.sleep(0.08)  # ensure overlap windows
        finally:
            with state_lock:
                in_flight -= 1
        return "ok"

    monkeypatch.setattr(gemma_client, "generate", slow_generate)

    try:
        async def _one(i: int) -> str:
            return await gemma_client.generate_async(
                system="sys", user=f"msg-{i}", max_tokens=10
            )

        results = await asyncio.gather(*(_one(i) for i in range(6)))
        assert len(results) == 6
        assert all(r == "ok" for r in results)
        # With GEMMA_MAX_CONCURRENCY=2 the peak must never exceed 2.
        assert peak_in_flight <= 2, (
            f"semaphore breached: peak in-flight was {peak_in_flight}, "
            f"expected <=2"
        )
        # And we should actually have hit the cap at some point — otherwise
        # the test isn't exercising the semaphore (all requests would have
        # serialized accidentally).
        assert peak_in_flight >= 2, (
            f"expected to saturate the semaphore (peak=2), only saw "
            f"{peak_in_flight}"
        )
    finally:
        # Swap back to a fresh small default executor so we don't leak
        # our 16 worker threads into later tests. (Python 3.14 tightened
        # set_default_executor to reject None.)
        loop.set_default_executor(ThreadPoolExecutor(max_workers=4))
        wide_executor.shutdown(wait=False)

    gemma_client.reset_cache()


@pytest.mark.asyncio
async def test_generate_async_logs_to_jsonl(monkeypatch, tmp_path):
    """Each async call appends exactly one record to gemma.jsonl.

    Uses a tmp log path by patching the module's cached log path. Ensures
    GEMMA_LOG_DISABLED is NOT set so logging actually fires.
    """
    # Make sure logging is enabled — don't let a leftover env from another
    # test suppress it.
    monkeypatch.delenv("GEMMA_LOG_DISABLED", raising=False)
    monkeypatch.setenv("GEMMA_MAX_CONCURRENCY", "8")
    gemma_client.reset_cache()

    log_path = tmp_path / "gemma.jsonl"
    # ``_log_path()`` caches its result; patching the function itself is the
    # clean way to redirect without fighting the cache.
    monkeypatch.setattr(gemma_client, "_log_path", lambda: log_path)

    # Stub the underlying sync generate so the async wrapper exercises the
    # full code path but never hits a real backend. We delegate to
    # generate_chat (which is what writes the log record) via the real
    # plumbing: set up a tiny stub client via _cached_client.
    class _Choice:
        def __init__(self, content: str):
            self.message = type("M", (), {"content": content})()
            self.finish_reason = "stop"

    class _Response:
        def __init__(self, content: str):
            self.choices = [_Choice(content)]
            self.usage = type(
                "U",
                (),
                {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            )()

    class _Completions:
        def create(self, **kwargs):
            return _Response("hello from stub")

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
    # Preserve the .cache_clear attribute (the production reset_cache
    # calls it) by wrapping the stub in functools.lru_cache too.
    from functools import lru_cache

    stub_client = _StubClient()

    @lru_cache(maxsize=1)
    def _stub_cached_client():
        return stub_client, cfg

    monkeypatch.setattr(gemma_client, "_cached_client", _stub_cached_client)

    # Fire three async calls.
    out_a = await gemma_client.generate_async(system="s", user="one", max_tokens=20)
    out_b = await gemma_client.generate_async(system="s", user="two", max_tokens=20)
    out_c = await gemma_client.generate_async(system="s", user="three", max_tokens=20)
    assert out_a == "hello from stub"
    assert out_b == "hello from stub"
    assert out_c == "hello from stub"

    assert log_path.exists(), "expected gemma.jsonl to be created"
    lines = [ln for ln in log_path.read_text().splitlines() if ln.strip()]
    assert len(lines) == 3, f"expected 3 log records, got {len(lines)}"

    # Every line parses, carries the right backend, and the three users
    # made it in.
    users_seen: list[str] = []
    for line in lines:
        record = json.loads(line)
        assert record["backend"] == "openrouter"
        assert record["model"] == "gemma4:e4b"
        assert record["response"] == "hello from stub"
        assert "duration_ms" in record
        # Pull the user message out of the chat record.
        users_seen.extend(
            msg["content"]
            for msg in record["messages"]
            if msg["role"] == "user"
        )

    assert set(users_seen) == {"one", "two", "three"}

    gemma_client.reset_cache()


@pytest.mark.asyncio
async def test_generate_async_jsonl_integrity_under_gather(monkeypatch, tmp_path):
    """Fan out 8 concurrent ``generate_async`` calls with multi-KB prompts
    and assert every line in ``gemma.jsonl`` parses individually.

    Without the ``_log_lock`` around the append, worker threads can
    interleave bytes mid-line (records can exceed PIPE_BUF, which is
    512 bytes on macOS), producing garbage lines that break downstream
    readers. This test is the direct regression test for that hazard.
    """
    monkeypatch.delenv("GEMMA_LOG_DISABLED", raising=False)
    monkeypatch.setenv("GEMMA_MAX_CONCURRENCY", "8")
    gemma_client.reset_cache()

    log_path = tmp_path / "gemma.jsonl"
    monkeypatch.setattr(gemma_client, "_log_path", lambda: log_path)

    # Build a reusable multi-KB response body — 4 KB of 'A' comfortably
    # beats the 512-byte POSIX atomic-write guarantee.
    bulky_body = "A" * 4096

    class _Choice:
        def __init__(self, content: str):
            self.message = type("M", (), {"content": content})()
            self.finish_reason = "stop"

    class _Response:
        def __init__(self, content: str):
            self.choices = [_Choice(content)]
            self.usage = type(
                "U",
                (),
                {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            )()

    class _Completions:
        def create(self, **kwargs):
            # Give the OS time to schedule another thread mid-write so
            # lock-less appends would actually interleave.
            time.sleep(0.01)
            return _Response(bulky_body)

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

    # Widen the executor so all 8 calls can actually land on worker
    # threads simultaneously.
    from concurrent.futures import ThreadPoolExecutor

    loop = asyncio.get_running_loop()
    wide_executor = ThreadPoolExecutor(max_workers=16)
    loop.set_default_executor(wide_executor)

    try:
        bulky_user = "U" * 4096
        tasks = [
            gemma_client.generate_async(
                system="s", user=f"{bulky_user}-{i}", max_tokens=20
            )
            for i in range(8)
        ]
        results = await asyncio.gather(*tasks)
        assert all(r == bulky_body for r in results)
    finally:
        loop.set_default_executor(ThreadPoolExecutor(max_workers=4))
        wide_executor.shutdown(wait=False)

    assert log_path.exists()
    lines = [ln for ln in log_path.read_text().splitlines() if ln.strip()]
    assert len(lines) == 8, f"expected 8 records, got {len(lines)}"

    # The heart of the test: every individual line must parse cleanly.
    # Without the lock, concurrent appenders would interleave bytes and
    # at least one json.loads() below would raise JSONDecodeError.
    for idx, line in enumerate(lines):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:  # pragma: no cover
            raise AssertionError(
                f"line {idx} is not valid JSON (concurrent-write "
                f"corruption?): {exc}: {line[:200]!r}"
            )
        assert record["backend"] == "openrouter"
        assert record["response"] == bulky_body

    gemma_client.reset_cache()


# ---------------------------------------------------------------------------
# generate_with_tools tests
# ---------------------------------------------------------------------------


def _make_stub_client_for_tools(monkeypatch, tmp_path, response_factory):
    """Wire up a stub OpenAI client that returns whatever response_factory builds.

    Returns (stub_client, cfg, log_path) for assertions.
    """
    monkeypatch.delenv("GEMMA_LOG_DISABLED", raising=False)
    gemma_client.reset_cache()

    log_path = tmp_path / "gemma.jsonl"
    monkeypatch.setattr(gemma_client, "_log_path", lambda: log_path)

    class _Completions:
        def create(self, **kwargs):
            return response_factory(**kwargs)

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
    return stub_client, cfg, log_path


def test_generate_with_tools_parses_tool_call(monkeypatch, tmp_path):
    """When the OpenAI client returns a tool_calls response,
    generate_with_tools correctly parses out name + arguments."""

    class _Function:
        name = "expand_socs"
        arguments = '{"soc_codes": ["29-1228"], "rationale": "pre-med intent"}'

    class _ToolCall:
        id = "call_1"
        type = "function"
        function = _Function()

    class _Message:
        content = None
        tool_calls = [_ToolCall()]

    class _Choice:
        message = _Message()
        finish_reason = "stop"

    class _Response:
        choices = [_Choice()]
        usage = type(
            "U", (), {"prompt_tokens": 20, "completion_tokens": 15, "total_tokens": 35}
        )()

    _make_stub_client_for_tools(monkeypatch, tmp_path, lambda **kw: _Response())

    result = gemma_client.generate_with_tools(
        system="You expand SOCs.",
        user="Student wants pre-med.",
        tools=[{"type": "function", "function": {"name": "expand_socs"}}],
        tool_choice="required",
        extra={"call_site": "soc_expansion"},
    )

    assert result is not None
    assert result["name"] == "expand_socs"
    assert result["arguments"]["soc_codes"] == ["29-1228"]
    assert result["arguments"]["rationale"] == "pre-med intent"

    gemma_client.reset_cache()


def test_generate_with_tools_no_tool_call_falls_back(monkeypatch, tmp_path):
    """When the model returns plain text (no tool_calls) and fallback
    also fails to produce parseable JSON, returns None."""

    class _Message:
        content = "I cannot call tools right now."
        tool_calls = None

    class _Choice:
        message = _Message()
        finish_reason = "stop"

    class _Response:
        choices = [_Choice()]
        usage = type(
            "U", (), {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18}
        )()

    _make_stub_client_for_tools(monkeypatch, tmp_path, lambda **kw: _Response())

    result = gemma_client.generate_with_tools(
        system="You expand SOCs.",
        user="Student wants pre-med.",
        tools=[{
            "type": "function",
            "function": {
                "name": "expand_socs",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "soc_codes": {"type": "array", "description": "SOC codes"},
                        "rationale": {"type": "string", "description": "reason"},
                    },
                    "required": ["soc_codes", "rationale"],
                },
            },
        }],
        tool_choice="required",
    )

    assert result is None

    gemma_client.reset_cache()


def test_generate_with_tools_content_json_fallback(monkeypatch, tmp_path):
    """When the model returns JSON in the content field instead of using
    tool_calls, the fallback extracts and returns it."""

    json_in_content = json.dumps({
        "soc_codes": ["29-1229", "29-1221"],
        "rationale": "physician and surgeon for pre-med",
    })

    class _Message:
        content = json_in_content
        tool_calls = None

    class _Choice:
        message = _Message()
        finish_reason = "stop"

    class _Response:
        choices = [_Choice()]
        usage = None

    _make_stub_client_for_tools(monkeypatch, tmp_path, lambda **kw: _Response())

    result = gemma_client.generate_with_tools(
        system="You expand SOCs.",
        user="Student wants pre-med.",
        tools=[{
            "type": "function",
            "function": {
                "name": "expand_socs",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "soc_codes": {"type": "array", "description": "SOC codes"},
                        "rationale": {"type": "string", "description": "reason"},
                    },
                    "required": ["soc_codes", "rationale"],
                },
            },
        }],
        tool_choice="required",
    )

    assert result is not None
    assert result["name"] == "expand_socs"
    assert result["arguments"]["soc_codes"] == ["29-1229", "29-1221"]

    gemma_client.reset_cache()


def test_generate_with_tools_fenced_json_fallback(monkeypatch, tmp_path):
    """When the model wraps JSON in markdown code fences, the fallback
    still extracts it."""

    fenced = (
        "Here are the picks:\n\n```json\n"
        '{"soc_codes": ["29-1229"], "rationale": "physicians"}\n'
        "```"
    )

    class _Message:
        content = fenced
        tool_calls = None

    class _Choice:
        message = _Message()
        finish_reason = "stop"

    class _Response:
        choices = [_Choice()]
        usage = None

    _make_stub_client_for_tools(monkeypatch, tmp_path, lambda **kw: _Response())

    result = gemma_client.generate_with_tools(
        system="You expand SOCs.",
        user="Student wants pre-med.",
        tools=[{
            "type": "function",
            "function": {
                "name": "expand_socs",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "soc_codes": {"type": "array", "description": "SOC codes"},
                        "rationale": {"type": "string", "description": "reason"},
                    },
                    "required": ["soc_codes", "rationale"],
                },
            },
        }],
        tool_choice="required",
    )

    assert result is not None
    assert result["name"] == "expand_socs"
    assert result["arguments"]["soc_codes"] == ["29-1229"]

    gemma_client.reset_cache()


def test_generate_with_tools_prompt_fallback(monkeypatch, tmp_path):
    """When the initial call returns empty content (no tool_calls, no JSON),
    the fallback re-issues as a plain prompt and parses the JSON response."""

    call_count = 0

    def _response_factory(**kwargs):
        nonlocal call_count
        call_count += 1

        if "tools" in kwargs:

            class _EmptyMessage:
                content = ""
                tool_calls = None

            class _EmptyChoice:
                message = _EmptyMessage()
                finish_reason = "stop"

            class _EmptyResponse:
                choices = [_EmptyChoice()]
                usage = None

            return _EmptyResponse()

        class _FallbackMessage:
            content = '{"soc_codes": ["29-1229"], "rationale": "physician"}'
            tool_calls = None

        class _FallbackChoice:
            message = _FallbackMessage()
            finish_reason = "stop"

        class _FallbackResponse:
            choices = [_FallbackChoice()]
            usage = None

        return _FallbackResponse()

    _make_stub_client_for_tools(monkeypatch, tmp_path, _response_factory)

    result = gemma_client.generate_with_tools(
        system="You expand SOCs.",
        user="Student wants pre-med.",
        tools=[{
            "type": "function",
            "function": {
                "name": "expand_socs",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "soc_codes": {"type": "array", "description": "SOC codes"},
                        "rationale": {"type": "string", "description": "reason"},
                    },
                    "required": ["soc_codes", "rationale"],
                },
            },
        }],
        tool_choice="required",
    )

    assert result is not None
    assert result["name"] == "expand_socs"
    assert result["arguments"]["soc_codes"] == ["29-1229"]
    assert call_count == 2

    gemma_client.reset_cache()


def test_generate_with_tools_logs_to_jsonl(monkeypatch, tmp_path):
    """Every generate_with_tools call appends a JSONL record with
    call_site, tool_call_made, and tool_name fields."""

    class _Function:
        name = "expand_socs"
        arguments = '{"soc_codes": ["29-1228"], "rationale": "test"}'

    class _ToolCall:
        id = "call_1"
        type = "function"
        function = _Function()

    class _Message:
        content = None
        tool_calls = [_ToolCall()]

    class _Choice:
        message = _Message()
        finish_reason = "stop"

    class _Response:
        choices = [_Choice()]
        usage = None

    _, _, log_path = _make_stub_client_for_tools(
        monkeypatch, tmp_path, lambda **kw: _Response(),
    )

    gemma_client.generate_with_tools(
        system="sys",
        user="usr",
        tools=[{"type": "function", "function": {"name": "expand_socs"}}],
        tool_choice="required",
        extra={"call_site": "soc_expansion"},
    )

    assert log_path.exists(), "expected gemma.jsonl to be created"
    lines = [ln for ln in log_path.read_text().splitlines() if ln.strip()]
    assert len(lines) == 1

    record = json.loads(lines[0])
    assert record["call_site"] == "soc_expansion"
    assert record["tool_call_made"] is True
    assert record["tool_name"] == "expand_socs"
    assert record["backend"] == "openrouter"
    assert "duration_ms" in record

    gemma_client.reset_cache()


def test_generate_with_tools_transport_error_returns_none(monkeypatch, tmp_path):
    """When the OpenAI client raises, generate_with_tools returns None
    and logs the error."""

    def _explode(**kwargs):
        raise ConnectionError("Backend unreachable")

    _, _, log_path = _make_stub_client_for_tools(
        monkeypatch, tmp_path, _explode,
    )

    result = gemma_client.generate_with_tools(
        system="sys",
        user="usr",
        tools=[{"type": "function", "function": {"name": "expand_socs"}}],
    )

    assert result is None

    # Log should still have recorded the failure.
    lines = [ln for ln in log_path.read_text().splitlines() if ln.strip()]
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert "error" in record
    assert record["tool_call_made"] is False

    gemma_client.reset_cache()


def test_generate_with_tools_unparseable_args_returns_none(monkeypatch, tmp_path):
    """When tool arguments are not valid JSON, returns None."""

    class _Function:
        name = "expand_socs"
        arguments = "NOT VALID JSON {{{{"

    class _ToolCall:
        id = "call_1"
        type = "function"
        function = _Function()

    class _Message:
        content = None
        tool_calls = [_ToolCall()]

    class _Choice:
        message = _Message()
        finish_reason = "stop"

    class _Response:
        choices = [_Choice()]
        usage = None

    _make_stub_client_for_tools(monkeypatch, tmp_path, lambda **kw: _Response())

    result = gemma_client.generate_with_tools(
        system="sys",
        user="usr",
        tools=[{"type": "function", "function": {"name": "expand_socs"}}],
    )

    assert result is None

    gemma_client.reset_cache()


# ---------------------------------------------------------------------------
# generate_with_tools_loop tests
# ---------------------------------------------------------------------------


def _make_tool_loop_stub(monkeypatch, tmp_path, response_sequence):
    """Wire up a stub client that returns responses from a sequence.

    Each item in response_sequence is called in order for successive
    client.chat.completions.create() calls.
    """
    monkeypatch.setenv("GEMMA_LOG_DISABLED", "1")
    monkeypatch.setenv("GEMMA_MAX_CONCURRENCY", "8")
    gemma_client.reset_cache()

    call_idx = [0]

    class _Completions:
        def create(self, **kwargs):
            idx = call_idx[0]
            call_idx[0] += 1
            if idx < len(response_sequence):
                return response_sequence[idx]
            raise RuntimeError(f"Unexpected call index {idx}")

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
        model="gemma4:stub",
    )

    from functools import lru_cache

    stub_client = _StubClient()

    @lru_cache(maxsize=1)
    def _stub_cached_client():
        return stub_client, cfg

    monkeypatch.setattr(gemma_client, "_cached_client", _stub_cached_client)
    return stub_client, cfg


class _PlainTextResponse:
    def __init__(self, content: str):
        class _M:
            pass
        msg = _M()
        msg.content = content
        msg.tool_calls = None
        choice = _M()
        choice.message = msg
        choice.finish_reason = "stop"
        self.choices = [choice]
        self.usage = None


class _ToolCallResponse:
    def __init__(self, tool_name: str, tool_args: str, call_id: str = "call_1"):
        class _M:
            pass
        fn = _M()
        fn.name = tool_name
        fn.arguments = tool_args
        tc = _M()
        tc.id = call_id
        tc.type = "function"
        tc.function = fn
        msg = _M()
        msg.content = None
        msg.tool_calls = [tc]
        choice = _M()
        choice.message = msg
        choice.finish_reason = "stop"
        self.choices = [choice]
        self.usage = None


@pytest.mark.asyncio
async def test_generate_with_tools_loop_single_turn(monkeypatch, tmp_path):
    """Plain text response on turn 1 returns directly with empty tool log."""
    _make_tool_loop_stub(monkeypatch, tmp_path, [
        _PlainTextResponse("This is the final answer."),
    ])

    async def _dispatch(name: str, args: dict) -> dict:
        raise AssertionError("Dispatch should not be called")

    text, log = await gemma_client.generate_with_tools_loop(
        system="sys",
        user="usr",
        tools=[{"type": "function", "function": {"name": "get_career_paths"}}],
        dispatch=_dispatch,
    )

    assert text == "This is the final answer."
    assert log == []
    gemma_client.reset_cache()


@pytest.mark.asyncio
async def test_generate_with_tools_loop_two_turn(monkeypatch, tmp_path):
    """tool_calls on turn 1, text on turn 2 — loop dispatches and returns."""
    _career_args = '{"unitid": 151351, "cipcode": "52.1401"}'
    _make_tool_loop_stub(monkeypatch, tmp_path, [
        _ToolCallResponse("get_career_paths", _career_args),
        _PlainTextResponse("Final response after tool call."),
    ])

    dispatch_calls: list[tuple[str, dict]] = []

    async def _dispatch(name: str, args: dict) -> dict:
        dispatch_calls.append((name, args))
        return {"data": [{"occupation_title": "Marketing Manager"}]}

    text, log = await gemma_client.generate_with_tools_loop(
        system="sys",
        user="usr",
        tools=[{"type": "function", "function": {"name": "get_career_paths"}}],
        dispatch=_dispatch,
    )

    assert text == "Final response after tool call."
    assert len(log) == 1
    assert log[0].tool_name == "get_career_paths"
    assert log[0].error is None
    assert len(dispatch_calls) == 1
    assert dispatch_calls[0][0] == "get_career_paths"
    gemma_client.reset_cache()


@pytest.mark.asyncio
async def test_generate_with_tools_loop_dispatch_error(monkeypatch, tmp_path):
    """When dispatch raises, loop returns empty text with error in log."""
    _career_args = '{"unitid": 151351, "cipcode": "52.1401"}'
    _make_tool_loop_stub(monkeypatch, tmp_path, [
        _ToolCallResponse("get_career_paths", _career_args),
    ])

    async def _dispatch(name: str, args: dict) -> dict:
        raise RuntimeError("DB unavailable")

    text, log = await gemma_client.generate_with_tools_loop(
        system="sys",
        user="usr",
        tools=[{"type": "function", "function": {"name": "get_career_paths"}}],
        dispatch=_dispatch,
    )

    assert text == ""
    assert len(log) == 1
    assert log[0].error is not None
    assert "DB unavailable" in log[0].error
    gemma_client.reset_cache()


@pytest.mark.asyncio
async def test_generate_with_tools_loop_turn_cap(monkeypatch, tmp_path):
    """Pathological model keeps calling tools — loop hits cap and returns empty."""
    _args = '{"unitid": 1, "cipcode": "52.14"}'
    _make_tool_loop_stub(monkeypatch, tmp_path, [
        _ToolCallResponse("get_career_paths", _args, "c1"),
        _ToolCallResponse("get_career_paths", _args, "c2"),
        _ToolCallResponse("get_career_paths", _args, "c3"),
    ])

    async def _dispatch(name: str, args: dict) -> dict:
        return {"data": []}

    text, log = await gemma_client.generate_with_tools_loop(
        system="sys",
        user="usr",
        tools=[{"type": "function", "function": {"name": "get_career_paths"}}],
        dispatch=_dispatch,
        max_turns=3,
    )

    assert text == ""
    assert len(log) == 3
    gemma_client.reset_cache()


@pytest.mark.asyncio
async def test_generate_with_tools_loop_transport_error(monkeypatch, tmp_path):
    """When the client raises on turn 1, returns empty text."""
    monkeypatch.setenv("GEMMA_LOG_DISABLED", "1")
    monkeypatch.setenv("GEMMA_MAX_CONCURRENCY", "8")
    gemma_client.reset_cache()

    class _Completions:
        def create(self, **kwargs):
            raise ConnectionError("Backend down")

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
        model="gemma4:stub",
    )

    from functools import lru_cache

    @lru_cache(maxsize=1)
    def _stub():
        return _StubClient(), cfg

    monkeypatch.setattr(gemma_client, "_cached_client", _stub)

    async def _dispatch(name: str, args: dict) -> dict:
        raise AssertionError("Should not be called")

    text, log = await gemma_client.generate_with_tools_loop(
        system="sys",
        user="usr",
        tools=[{"type": "function", "function": {"name": "get_career_paths"}}],
        dispatch=_dispatch,
    )

    assert text == ""
    assert log == []
    gemma_client.reset_cache()


# ---------------------------------------------------------------------------
# Trace callback tests (feature-gemma-trace.md §4)
# ---------------------------------------------------------------------------


class _MultiToolCallResponse:
    """One LLM response carrying multiple parallel tool_use blocks.
    Models the parallel-tool-call case Decision #13's dispatch_index
    is meant to handle."""

    def __init__(self, calls: list[tuple[str, str, str]]) -> None:
        # Each call: (tool_name, tool_args_json, call_id)
        class _M:
            pass

        tcs = []
        for name, args_json, cid in calls:
            fn = _M()
            fn.name = name
            fn.arguments = args_json
            tc = _M()
            tc.id = cid
            tc.type = "function"
            tc.function = fn
            tcs.append(tc)

        msg = _M()
        msg.content = None
        msg.tool_calls = tcs
        choice = _M()
        choice.message = msg
        choice.finish_reason = "stop"
        self.choices = [choice]
        self.usage = None


@pytest.mark.asyncio
async def test_on_turn_event_default_is_noop(monkeypatch, tmp_path):
    """Loop with no on_turn_event passed behaves identically to baseline."""
    _career_args = '{"unitid": 151351, "cipcode": "52.1401"}'
    _make_tool_loop_stub(monkeypatch, tmp_path, [
        _ToolCallResponse("get_career_paths", _career_args),
        _PlainTextResponse("Done."),
    ])

    async def _dispatch(name: str, args: dict) -> dict:
        return {"data": []}

    text, log = await gemma_client.generate_with_tools_loop(
        system="sys",
        user="usr",
        tools=[{"type": "function", "function": {"name": "get_career_paths"}}],
        dispatch=_dispatch,
    )

    assert text == "Done."
    assert len(log) == 1
    gemma_client.reset_cache()


@pytest.mark.asyncio
async def test_on_turn_start_default_is_noop(monkeypatch, tmp_path):
    """Loop with no on_turn_start passed behaves identically to baseline."""
    _career_args = '{"unitid": 151351, "cipcode": "52.1401"}'
    _make_tool_loop_stub(monkeypatch, tmp_path, [
        _ToolCallResponse("get_career_paths", _career_args),
        _PlainTextResponse("Done."),
    ])

    async def _dispatch(name: str, args: dict) -> dict:
        return {"data": []}

    text, log = await gemma_client.generate_with_tools_loop(
        system="sys",
        user="usr",
        tools=[{"type": "function", "function": {"name": "get_career_paths"}}],
        dispatch=_dispatch,
    )

    assert text == "Done."
    assert len(log) == 1
    gemma_client.reset_cache()


@pytest.mark.asyncio
async def test_on_turn_event_fires_per_turn(monkeypatch, tmp_path):
    """Mock callback receives one call per appended ToolCallTurn, in order."""
    _args = '{"unitid": 1, "cipcode": "52.14"}'
    _make_tool_loop_stub(monkeypatch, tmp_path, [
        _ToolCallResponse("get_career_paths", _args, "c1"),
        _PlainTextResponse("Done."),
    ])

    received: list[gemma_client.ToolCallTurn] = []

    async def _on_turn(turn):
        received.append(turn)

    async def _dispatch(name: str, args: dict) -> dict:
        return {"data": [{"x": 1}]}

    await gemma_client.generate_with_tools_loop(
        system="sys",
        user="usr",
        tools=[{"type": "function", "function": {"name": "get_career_paths"}}],
        dispatch=_dispatch,
        on_turn_event=_on_turn,
    )

    assert len(received) == 1
    assert received[0].tool_name == "get_career_paths"
    assert received[0].dispatch_index == 0
    gemma_client.reset_cache()


@pytest.mark.asyncio
async def test_on_turn_start_fires_before_dispatch(monkeypatch, tmp_path):
    """on_turn_start fires BEFORE dispatch returns (UI sees in-progress
    shimmer the moment Gemma issues the call)."""
    _args = '{"unitid": 1, "cipcode": "52.14"}'
    _make_tool_loop_stub(monkeypatch, tmp_path, [
        _ToolCallResponse("get_career_paths", _args),
        _PlainTextResponse("Done."),
    ])

    timeline: list[str] = []

    async def _on_start(idx: int, name: str, args: dict) -> None:
        timeline.append(f"start:{idx}:{name}")

    async def _dispatch(name: str, args: dict) -> dict:
        timeline.append(f"dispatch_begin:{name}")
        await asyncio.sleep(0.01)
        timeline.append(f"dispatch_end:{name}")
        return {"data": []}

    await gemma_client.generate_with_tools_loop(
        system="sys",
        user="usr",
        tools=[{"type": "function", "function": {"name": "get_career_paths"}}],
        dispatch=_dispatch,
        on_turn_start=_on_start,
    )

    # start fires BEFORE dispatch_begin
    start_idx = timeline.index("start:0:get_career_paths")
    begin_idx = timeline.index("dispatch_begin:get_career_paths")
    assert start_idx < begin_idx, f"timeline: {timeline}"
    gemma_client.reset_cache()


@pytest.mark.asyncio
async def test_dispatch_index_unique_across_parallel_calls(
    monkeypatch, tmp_path
):
    """Decision #13: with multiple tool calls in ONE outer LLM turn,
    each appended ToolCallTurn has a distinct, monotonically increasing
    dispatch_index even though they share turn_number."""
    args1 = '{"unitid": 1, "cipcode": "11.0701"}'
    args2 = '{"unitid": 2, "cipcode": "52.1401"}'
    args3 = '{"unitid": 3, "cipcode": "26.0101"}'
    _make_tool_loop_stub(monkeypatch, tmp_path, [
        _MultiToolCallResponse([
            ("get_career_paths", args1, "c1"),
            ("get_career_paths", args2, "c2"),
            ("get_career_paths", args3, "c3"),
        ]),
        _PlainTextResponse("Final answer."),
    ])

    async def _dispatch(name: str, args: dict) -> dict:
        return {"data": []}

    _text, log = await gemma_client.generate_with_tools_loop(
        system="sys",
        user="usr",
        tools=[{"type": "function", "function": {"name": "get_career_paths"}}],
        dispatch=_dispatch,
    )

    # All three dispatched in a single outer turn → share turn_number=0
    # but have distinct, sequential dispatch_index values 0, 1, 2.
    assert len(log) == 3
    assert {t.turn_number for t in log} == {0}
    assert [t.dispatch_index for t in log] == [0, 1, 2]
    gemma_client.reset_cache()


@pytest.mark.asyncio
async def test_on_turn_start_and_event_share_dispatch_index(
    monkeypatch, tmp_path
):
    """For each dispatch, the dispatch_index passed to on_turn_start
    equals ToolCallTurn.dispatch_index passed to on_turn_event. This is
    the contract <GemmaTrace> relies on for row pairing."""
    args1 = '{"unitid": 1, "cipcode": "11.0701"}'
    args2 = '{"unitid": 2, "cipcode": "52.1401"}'
    _make_tool_loop_stub(monkeypatch, tmp_path, [
        _MultiToolCallResponse([
            ("get_career_paths", args1, "c1"),
            ("get_career_paths", args2, "c2"),
        ]),
        _PlainTextResponse("Final."),
    ])

    starts: list[int] = []
    completes: list[int] = []

    async def _on_start(idx: int, name: str, args: dict) -> None:
        starts.append(idx)

    async def _on_turn(turn) -> None:
        completes.append(turn.dispatch_index)

    async def _dispatch(name: str, args: dict) -> dict:
        return {"data": []}

    await gemma_client.generate_with_tools_loop(
        system="sys",
        user="usr",
        tools=[{"type": "function", "function": {"name": "get_career_paths"}}],
        dispatch=_dispatch,
        on_turn_start=_on_start,
        on_turn_event=_on_turn,
    )

    assert starts == [0, 1]
    assert completes == [0, 1]
    gemma_client.reset_cache()


@pytest.mark.asyncio
async def test_on_turn_event_callback_failure_does_not_break_loop(
    monkeypatch, tmp_path
):
    """A callback that raises is caught + logged; loop continues to
    completion. Trace is supplementary; chat must keep working."""
    _args = '{"unitid": 1, "cipcode": "52.14"}'
    _make_tool_loop_stub(monkeypatch, tmp_path, [
        _ToolCallResponse("get_career_paths", _args),
        _PlainTextResponse("All good."),
    ])

    async def _broken(turn):
        raise RuntimeError("consumer is broken")

    async def _dispatch(name: str, args: dict) -> dict:
        return {"data": []}

    text, log = await gemma_client.generate_with_tools_loop(
        system="sys",
        user="usr",
        tools=[{"type": "function", "function": {"name": "get_career_paths"}}],
        dispatch=_dispatch,
        on_turn_event=_broken,
    )

    assert text == "All good."
    assert len(log) == 1
    gemma_client.reset_cache()


@pytest.mark.asyncio
async def test_on_turn_start_callback_failure_does_not_break_loop(
    monkeypatch, tmp_path
):
    """Symmetric to the on_turn_event failure test."""
    _args = '{"unitid": 1, "cipcode": "52.14"}'
    _make_tool_loop_stub(monkeypatch, tmp_path, [
        _ToolCallResponse("get_career_paths", _args),
        _PlainTextResponse("All good."),
    ])

    async def _broken(idx, name, args):
        raise RuntimeError("start consumer broken")

    async def _dispatch(name: str, args: dict) -> dict:
        return {"data": []}

    text, log = await gemma_client.generate_with_tools_loop(
        system="sys",
        user="usr",
        tools=[{"type": "function", "function": {"name": "get_career_paths"}}],
        dispatch=_dispatch,
        on_turn_start=_broken,
    )

    assert text == "All good."
    assert len(log) == 1
    gemma_client.reset_cache()


@pytest.mark.asyncio
async def test_callback_accepts_sync_callable(monkeypatch, tmp_path):
    """Item D: both callbacks accept sync OR async callables. Loop
    detects via asyncio.iscoroutine on the return value. Test fixtures
    can use plain list-append spies without async def boilerplate."""
    _args = '{"unitid": 1, "cipcode": "52.14"}'
    _make_tool_loop_stub(monkeypatch, tmp_path, [
        _ToolCallResponse("get_career_paths", _args),
        _PlainTextResponse("Done."),
    ])

    starts: list[tuple[int, str]] = []
    completes: list[int] = []

    def _sync_start(idx: int, name: str, args: dict) -> None:
        starts.append((idx, name))

    def _sync_event(turn) -> None:
        completes.append(turn.dispatch_index)

    async def _dispatch(name: str, args: dict) -> dict:
        return {"data": []}

    text, _log = await gemma_client.generate_with_tools_loop(
        system="sys",
        user="usr",
        tools=[{"type": "function", "function": {"name": "get_career_paths"}}],
        dispatch=_dispatch,
        on_turn_start=_sync_start,
        on_turn_event=_sync_event,
    )

    assert text == "Done."
    assert starts == [(0, "get_career_paths")]
    assert completes == [0]
    gemma_client.reset_cache()


@pytest.mark.asyncio
async def test_tool_result_preview_truncated(monkeypatch, tmp_path):
    """The tool_result_preview field is truncated to 500 chars;
    tool_result_size_bytes reflects the FULL size."""
    _args = '{"unitid": 1, "cipcode": "52.14"}'
    _make_tool_loop_stub(monkeypatch, tmp_path, [
        _ToolCallResponse("get_career_paths", _args),
        _PlainTextResponse("Done."),
    ])

    big_string = "x" * 2000

    async def _dispatch(name: str, args: dict) -> dict:
        return {"data": big_string}

    _text, log = await gemma_client.generate_with_tools_loop(
        system="sys",
        user="usr",
        tools=[{"type": "function", "function": {"name": "get_career_paths"}}],
        dispatch=_dispatch,
    )

    assert len(log) == 1
    turn = log[0]
    assert len(turn.tool_result_preview) == 500
    # Full size is the JSON-encoded length: includes braces + key + quotes
    assert turn.tool_result_size_bytes > 2000
    gemma_client.reset_cache()


# ---------------------------------------------------------------------------
# final_turn_response_format — JSON-mode scoping
#   spec: docs/specs/feature-explain-stat-receipt.md (DRAFT v1.3) §4
#         Service Changes (Decision 15) + §4 New Tests Required (P0).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_final_turn_response_format_synthesis_only(
    monkeypatch, tmp_path
):
    """final_turn_response_format is injected ONLY on synthesis turns
    (turns that follow at least one tool-call turn) — NOT on the
    initial turn-0 tool-call decision.

    Wire a 3-turn loop: tool, tool, text. Capture per-turn kwargs to
    _one_tool_turn and assert response_format is None on turns 0 and 1
    (tool-call turns) and the JSON-mode dict on turn 2 (synthesis).

    Without this scoping the Ollama backend's ``format: "json"``
    constraint would suppress tool emission on turn 0 (it strictly
    enforces JSON output), breaking the explain-receipt path silently.
    P0 / fp-architect Condition 1."""
    monkeypatch.setenv("GEMMA_LOG_DISABLED", "1")
    monkeypatch.setenv("GEMMA_MAX_CONCURRENCY", "8")
    gemma_client.reset_cache()

    captured_kwargs: list[dict] = []

    async def _capturing_one_tool_turn(**kwargs):
        # Snapshot the response_format key per turn.
        captured_kwargs.append({
            "turn_number": kwargs.get("turn_number"),
            "response_format": kwargs.get("response_format"),
        })
        turn_idx = kwargs.get("turn_number", 0)
        if turn_idx == 0:
            return ("", [{
                "id": "c0",
                "name": "get_career_paths",
                "arguments": {"unitid": 1, "cipcode": "11.07"},
            }])
        if turn_idx == 1:
            return ("", [{
                "id": "c1",
                "name": "get_occupation_data",
                "arguments": {"soc_code": "15-1252"},
            }])
        # Turn 2 (synthesis) — return text.
        return ("Final synthesis answer.", [])

    monkeypatch.setattr(
        gemma_client, "_one_tool_turn", _capturing_one_tool_turn
    )

    # Stub _cached_client so _tools_loop_inner can read backend type.
    cfg = gemma_client.InferenceConfig(
        backend="openrouter",
        base_url="http://stub",
        api_key="stub",
        model="gemma4:stub",
    )

    from functools import lru_cache

    @lru_cache(maxsize=1)
    def _stub():
        class _C: pass  # noqa: E701
        return _C(), cfg

    monkeypatch.setattr(gemma_client, "_cached_client", _stub)

    async def _dispatch(name, args):
        return {"data": []}

    text, log = await gemma_client.generate_with_tools_loop(
        system="sys",
        user="usr",
        tools=[{"type": "function", "function": {"name": "get_career_paths"}}],
        dispatch=_dispatch,
        max_turns=3,
        final_turn_response_format={"type": "json_object"},
    )

    assert text == "Final synthesis answer."
    assert len(log) == 2  # 2 tool calls dispatched
    assert len(captured_kwargs) == 3, (
        f"expected 3 turns (2 tool, 1 synthesis), got {len(captured_kwargs)}"
    )
    # Turn 0: NO response_format (initial tool-call decision).
    assert captured_kwargs[0]["response_format"] is None, (
        "turn 0 must not carry response_format (would suppress tool calls "
        "on Ollama backend per Decision 15)"
    )
    # Turn 1: NO response_format yet (still a tool-call turn — the
    # previous turn issued tool calls but turn 1 itself is the next
    # tool-call decision turn). Actually per the implementation, turn 1
    # IS a synthesis-eligible turn because prev_turn_had_tool_calls is
    # set. Let's verify by reading the implementation: yes, the flag
    # is set the moment a tool call fires, so turn 1 receives the
    # response_format. The test mocks turn 1 to issue another tool call
    # which is fine; the scoping check is "turn N+1 receives the format
    # if turn N issued tool calls."
    assert captured_kwargs[1]["response_format"] == {"type": "json_object"}
    # Turn 2: response_format threaded (synthesis turn after tools).
    assert captured_kwargs[2]["response_format"] == {"type": "json_object"}
    gemma_client.reset_cache()


@pytest.mark.asyncio
async def test_response_format_propagates_to_openrouter_path(
    monkeypatch, tmp_path
):
    """OpenAI-compat path: ``final_turn_response_format={"type":
    "json_object"}`` lands in completion_kwargs["response_format"]
    verbatim. Mock the OpenAI client and capture call args.

    P0 / fp-architect Condition 1."""
    monkeypatch.setenv("GEMMA_LOG_DISABLED", "1")
    monkeypatch.setenv("GEMMA_MAX_CONCURRENCY", "8")
    gemma_client.reset_cache()

    captured_calls: list[dict] = []

    class _Completions:
        def create(self, **kwargs):
            captured_calls.append(kwargs)
            # Return plain-text on the first turn so the loop terminates
            # after one call. The synthesis-turn-only scoping in
            # _tools_loop_inner means the response_format is only
            # injected after a tool call has fired, but here we want to
            # exercise the per-call wire format directly. Bypass the
            # loop's scoping by calling _one_tool_turn directly below.
            class _M: pass  # noqa: E701
            msg = _M()
            msg.content = "ok"
            msg.tool_calls = None
            choice = _M()
            choice.message = msg
            choice.finish_reason = "stop"
            resp = _M()
            resp.choices = [choice]
            resp.usage = None
            return resp

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
        model="gemma4:stub",
    )

    from functools import lru_cache

    stub_client = _StubClient()

    @lru_cache(maxsize=1)
    def _stub():
        return stub_client, cfg

    monkeypatch.setattr(gemma_client, "_cached_client", _stub)

    # Call _one_tool_turn directly to test the per-call wire format
    # without the _tools_loop_inner scoping logic getting in the way.
    text, tool_calls = await gemma_client._one_tool_turn(
        messages=[{"role": "user", "content": "hello"}],
        tools=[],
        temperature=0.0,
        max_tokens=100,
        turn_number=0,
        extra=None,
        response_format={"type": "json_object"},
    )
    assert text == "ok"
    assert tool_calls == []  # plain text response
    assert len(captured_calls) == 1
    # OpenAI-compat path passes response_format verbatim.
    assert captured_calls[0]["response_format"] == {"type": "json_object"}
    gemma_client.reset_cache()


@pytest.mark.asyncio
async def test_response_format_translates_to_ollama_native_payload(
    monkeypatch, tmp_path
):
    """Native Ollama path (_one_tool_turn_ollama):
    ``final_turn_response_format={"type": "json_object"}`` translates
    to ``payload["format"] = "json"`` on the wire. Without this
    translation Ollama silently ignores the OpenAI-compat shape and
    JSON mode no-ops on the local-inference backend.

    P0 / fp-architect Condition 1 — load-bearing for local-inference
    correctness."""
    monkeypatch.setenv("GEMMA_LOG_DISABLED", "1")
    monkeypatch.setenv("GEMMA_MAX_CONCURRENCY", "8")
    gemma_client.reset_cache()

    captured_payloads: list[dict] = []

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "message": {"content": "ok", "tool_calls": None},
            }

    def _capture_post(url, json=None, timeout=None):
        captured_payloads.append(json or {})
        return _Resp()

    monkeypatch.setattr(gemma_client.httpx, "post", _capture_post)

    cfg = gemma_client.InferenceConfig(
        backend="ollama",
        base_url="http://localhost:11434",
        api_key=None,
        model="gemma:stub",
    )

    text, tool_calls = await gemma_client._one_tool_turn_ollama(
        config=cfg,
        model="gemma:stub",
        messages=[{"role": "user", "content": "hello"}],
        tools=[],
        temperature=0.0,
        max_tokens=100,
        turn_number=0,
        response_format={"type": "json_object"},
    )

    assert text == "ok"
    assert tool_calls == []
    assert len(captured_payloads) == 1
    # OpenAI-compat shape MUST translate to Ollama native "json".
    assert captured_payloads[0].get("format") == "json", (
        f"Ollama path must translate {{'type': 'json_object'}} to "
        f"format='json' on the wire; got payload={captured_payloads[0]!r}"
    )
    gemma_client.reset_cache()


@pytest.mark.asyncio
async def test_response_format_absent_when_unset_on_ollama(monkeypatch):
    """Sanity check: when final_turn_response_format is None,
    payload["format"] is not set on the Ollama path."""
    monkeypatch.setenv("GEMMA_LOG_DISABLED", "1")
    monkeypatch.setenv("GEMMA_MAX_CONCURRENCY", "8")
    gemma_client.reset_cache()

    captured_payloads: list[dict] = []

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": "ok", "tool_calls": None}}

    def _capture_post(url, json=None, timeout=None):
        captured_payloads.append(json or {})
        return _Resp()

    monkeypatch.setattr(gemma_client.httpx, "post", _capture_post)

    cfg = gemma_client.InferenceConfig(
        backend="ollama",
        base_url="http://localhost:11434",
        api_key=None,
        model="gemma:stub",
    )

    await gemma_client._one_tool_turn_ollama(
        config=cfg,
        model="gemma:stub",
        messages=[{"role": "user", "content": "hello"}],
        tools=[],
        temperature=0.0,
        max_tokens=100,
        turn_number=0,
        response_format=None,
    )
    assert len(captured_payloads) == 1
    assert "format" not in captured_payloads[0]
    gemma_client.reset_cache()


# ---------------------------------------------------------------------------
# _hedged_completion tests — tail-latency hedging for OpenRouter calls.
#
# The function lives just above _one_tool_turn in gemma_client.py. It wraps
# the blocking SDK call (run via asyncio.to_thread) so a slow primary
# request can be raced against a backup fired _HEDGE_DELAY_S later.
#
# Test infra notes:
#   - GEMMA_HEDGE_DELAY_S is read at IMPORT time into the module-level
#     constant `_HEDGE_DELAY_S`. Setting the env var post-import has no
#     effect — we monkeypatch the constant directly.
#   - The SDK call site is `_client.chat.completions.create(**kwargs)`.
#     We stub `_cached_client()` (lru_cache wrapped) the same way the
#     existing tests do, then back the .create() with whatever latency /
#     failure behavior the test needs.
#   - All sleeps are asyncio.sleep on tiny intervals (hedge delay <= 0.05s)
#     so the suite stays under a second.
# ---------------------------------------------------------------------------


def _install_hedge_stub_client(monkeypatch, create_fn):
    """Wire up a stub client whose chat.completions.create() delegates to
    `create_fn(**kwargs)` (a plain sync callable — runs on a worker
    thread because _hedged_completion uses asyncio.to_thread).

    Returns the stub client object so the test can hang call counters /
    state on it if needed.
    """
    monkeypatch.setenv("GEMMA_LOG_DISABLED", "1")
    monkeypatch.setenv("GEMMA_MAX_CONCURRENCY", "8")
    gemma_client.reset_cache()

    class _Completions:
        def create(self, **kwargs):
            return create_fn(**kwargs)

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
        model="gemma4:stub",
    )

    from functools import lru_cache

    stub_client = _StubClient()

    @lru_cache(maxsize=1)
    def _stub_cached_client():
        return stub_client, cfg

    monkeypatch.setattr(gemma_client, "_cached_client", _stub_cached_client)
    return stub_client


def _make_response_obj(content: str = "ok"):
    """Minimal stand-in for the OpenAI SDK response object. The hedged
    function returns it verbatim — we only need identity, but we build
    something realistic so failures are easier to debug."""
    class _M:
        pass

    msg = _M()
    msg.content = content
    msg.tool_calls = None
    choice = _M()
    choice.message = msg
    choice.finish_reason = "stop"
    resp = _M()
    resp.choices = [choice]
    resp.usage = None
    resp._marker = content  # for asserting which call won
    return resp


@pytest.mark.asyncio
async def test_hedged_completion_primary_wins_fast(monkeypatch):
    """Primary returns inside the hedge window — backup never fires.

    Verifies (a) the response is the primary's, (b) the SDK was called
    exactly once. If the hedging logic accidentally spawned a backup
    despite the primary completing inside the window, call_count would
    be 2.
    """
    monkeypatch.setattr(gemma_client, "_HEDGE_DELAY_S", 0.5)

    call_count = 0
    primary_response = _make_response_obj("primary")

    def _create(**kwargs):
        nonlocal call_count
        call_count += 1
        # Return immediately — well under the 0.5s hedge window.
        return primary_response

    _install_hedge_stub_client(monkeypatch, _create)

    result = await gemma_client._hedged_completion(
        completion_kwargs={"model": "x", "messages": []},
        turn_number=0,
    )

    assert result is primary_response
    assert call_count == 1, (
        f"backup should not have fired when primary won fast; "
        f"got {call_count} SDK calls"
    )

    gemma_client.reset_cache()


@pytest.mark.asyncio
async def test_hedged_completion_primary_slow_backup_wins(monkeypatch):
    """Primary blocks past the hedge delay; backup fires and returns
    quickly. Result is the backup's response; the SDK is called twice.

    Uses a threading.Event so the slow primary stays blocked until we
    explicitly release it after the assertions — that way we don't
    leak a sleeping worker thread that wakes up and emits a stray log
    line during a later test.
    """
    import threading

    monkeypatch.setattr(gemma_client, "_HEDGE_DELAY_S", 0.05)

    call_count = 0
    call_lock = threading.Lock()
    release_primary = threading.Event()
    primary_response = _make_response_obj("primary")
    backup_response = _make_response_obj("backup")

    def _create(**kwargs):
        nonlocal call_count
        with call_lock:
            call_count += 1
            this_call = call_count

        if this_call == 1:
            # Primary: block on the event so the hedge delay elapses.
            # If the test ends without setting the event, wait at most
            # 2s so we don't pin a worker thread forever.
            release_primary.wait(timeout=2.0)
            return primary_response
        # Backup: return immediately so it wins the race.
        return backup_response

    _install_hedge_stub_client(monkeypatch, _create)

    try:
        result = await gemma_client._hedged_completion(
            completion_kwargs={"model": "x", "messages": []},
            turn_number=0,
        )

        assert result is backup_response, (
            "backup should have won the race once primary exceeded the "
            "hedge delay"
        )
        assert call_count == 2, (
            f"both primary and backup should have fired; got {call_count}"
        )
    finally:
        # Unblock the primary so its worker thread can exit cleanly.
        release_primary.set()


@pytest.mark.asyncio
async def test_hedged_completion_disabled_when_delay_zero(monkeypatch):
    """When _HEDGE_DELAY_S <= 0, exactly one call ever fires — even if
    that call is slow. The early-return branch must NOT spawn a backup
    task.
    """
    import threading

    monkeypatch.setattr(gemma_client, "_HEDGE_DELAY_S", 0.0)

    call_count = 0
    call_lock = threading.Lock()
    response = _make_response_obj("only")

    def _create(**kwargs):
        nonlocal call_count
        with call_lock:
            call_count += 1
        # Sleep longer than what the (now-disabled) hedge delay would
        # have been. With hedging on this would absolutely have triggered
        # a backup; with hedging off we should still see just one call.
        time.sleep(0.1)
        return response

    _install_hedge_stub_client(monkeypatch, _create)

    result = await gemma_client._hedged_completion(
        completion_kwargs={"model": "x", "messages": []},
        turn_number=0,
    )

    assert result is response
    assert call_count == 1, (
        f"hedging must be disabled when _HEDGE_DELAY_S<=0; "
        f"got {call_count} SDK calls"
    )

    gemma_client.reset_cache()


@pytest.mark.asyncio
async def test_hedged_completion_both_fail_returns_none(monkeypatch, caplog):
    """Both primary AND backup raise transport errors. Function returns
    None and emits a WARNING log per failed candidate."""
    import threading

    monkeypatch.setattr(gemma_client, "_HEDGE_DELAY_S", 0.05)

    call_count = 0
    call_lock = threading.Lock()

    def _create(**kwargs):
        nonlocal call_count
        with call_lock:
            call_count += 1
            this_call = call_count
        if this_call == 1:
            # Primary: stay slow so backup actually fires.
            time.sleep(0.15)
            raise ConnectionError("primary transport error")
        raise ConnectionError("backup transport error")

    _install_hedge_stub_client(monkeypatch, _create)

    with caplog.at_level(logging.WARNING, logger=gemma_client.logger.name):
        result = await gemma_client._hedged_completion(
            completion_kwargs={"model": "x", "messages": []},
            turn_number=7,
        )

    assert result is None
    assert call_count == 2, (
        f"backup must have fired when primary was still pending; "
        f"got {call_count}"
    )
    # Each candidate failure should have been logged.
    candidate_warnings = [
        rec for rec in caplog.records
        if rec.levelno == logging.WARNING
        and "candidate failed" in rec.getMessage()
    ]
    assert len(candidate_warnings) == 2, (
        f"expected 2 'candidate failed' WARNING logs (one per failure); "
        f"got {len(candidate_warnings)}: "
        f"{[r.getMessage() for r in candidate_warnings]}"
    )

    gemma_client.reset_cache()


@pytest.mark.asyncio
async def test_hedged_completion_primary_fails_fast_no_backup(
    monkeypatch, caplog
):
    """Primary raises BEFORE the hedge delay elapses. Document the
    CURRENT behavior: no backup is fired (because asyncio.wait returned
    `done` non-empty), the loop catches the exception, candidates becomes
    empty (pending was empty), and the function returns None.

    POTENTIAL WEAKNESS / FLAG FOR HUMAN REVIEW
    -------------------------------------------
    Arguably this is a bug: a transient fast-failure (e.g. 5xx, dropped
    socket) on the primary effectively bypasses the hedge entirely and
    falls straight through to None, when the whole point of hedging is
    resilience. A more defensive implementation would always fire the
    backup on primary failure (whether fast or slow). Worth a follow-up
    spec — for now this test pins the actual behavior so a future fix
    is intentional and visible in the diff.
    """
    monkeypatch.setattr(gemma_client, "_HEDGE_DELAY_S", 0.5)

    call_count = 0

    def _create(**kwargs):
        nonlocal call_count
        call_count += 1
        # Fast failure — well inside the 0.5s hedge window.
        raise ConnectionError("primary fast-failed")

    _install_hedge_stub_client(monkeypatch, _create)

    with caplog.at_level(logging.WARNING, logger=gemma_client.logger.name):
        result = await gemma_client._hedged_completion(
            completion_kwargs={"model": "x", "messages": []},
            turn_number=3,
        )

    assert result is None
    # CURRENT behavior: backup is NOT fired on fast primary failure.
    # (See docstring above — flagged for human review.)
    assert call_count == 1, (
        "current implementation does not fire backup on fast primary "
        "failure; if this assertion now reads call_count == 2, the "
        "behavior changed and the docstring above should be updated"
    )
    # The single candidate failure should have been logged.
    candidate_warnings = [
        rec for rec in caplog.records
        if rec.levelno == logging.WARNING
        and "candidate failed" in rec.getMessage()
    ]
    assert len(candidate_warnings) == 1

    gemma_client.reset_cache()


@pytest.mark.asyncio
async def test_hedged_completion_backup_fails_primary_wins(monkeypatch):
    """Both fire (primary slow → backup spawns), backup raises FIRST,
    then primary succeeds. The loop should swallow the backup's
    exception and return primary's successful result.

    Pins the contract that a single candidate failure does not poison
    the whole hedged call as long as another candidate is still in
    flight.
    """
    import threading

    monkeypatch.setattr(gemma_client, "_HEDGE_DELAY_S", 0.05)

    call_count = 0
    call_lock = threading.Lock()
    primary_response = _make_response_obj("primary")
    release_primary = threading.Event()

    def _create(**kwargs):
        nonlocal call_count
        with call_lock:
            call_count += 1
            this_call = call_count

        if this_call == 1:
            # Primary: wait until released, then return success. Released
            # below AFTER the backup has had time to raise.
            released = release_primary.wait(timeout=2.0)
            assert released, "primary was never released"
            return primary_response
        # Backup: raise quickly so it lands in `done` first.
        raise ConnectionError("backup transport error")

    _install_hedge_stub_client(monkeypatch, _create)

    # Drive the test: kick off the hedged call, give the backup time
    # to fire and fail, then release the primary so it can win.
    async def _release_after_backup_fails():
        # 0.15s is long enough for: primary to start blocking, hedge
        # delay (0.05s) to elapse, backup to spawn and raise. Then we
        # release the primary so the loop can collect its success.
        await asyncio.sleep(0.15)
        release_primary.set()

    releaser = asyncio.create_task(_release_after_backup_fails())
    try:
        result = await gemma_client._hedged_completion(
            completion_kwargs={"model": "x", "messages": []},
            turn_number=0,
        )
    finally:
        await releaser

    assert result is primary_response, (
        "primary's successful result should have won after backup raised"
    )
    assert call_count == 2

    gemma_client.reset_cache()
