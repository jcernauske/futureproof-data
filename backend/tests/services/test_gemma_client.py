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
        backend="ollama",
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
        assert record["backend"] == "ollama"
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
        backend="ollama",
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
        assert record["backend"] == "ollama"
        assert record["response"] == bulky_body

    gemma_client.reset_cache()
