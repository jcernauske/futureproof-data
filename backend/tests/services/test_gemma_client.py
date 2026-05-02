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
