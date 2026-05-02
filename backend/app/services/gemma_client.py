"""Unified Gemma inference client.

Reads ``INFERENCE_BACKEND`` from the environment (or ``.env`` via
``python-dotenv``) and returns an OpenAI-compatible ``OpenAI`` client
pointed at either a local Ollama instance or OpenRouter. Both backends
expose the OpenAI chat completions API, so switching is a config
change, not a code change.

Same code path the cloud-gemma-deployment spec defines — the CLI uses
it for narrative generation (boss explanations, skill recs, guidance).

Usage:

    from app.services.gemma_client import generate

    text = generate(
        system="You are a career coach...",
        user="Write 4 sentences about...",
        max_tokens=400,
    )
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from openai import OpenAI

from app.services.mcp_client import project_root

logger = logging.getLogger(__name__)

# Default model identifiers per backend. OpenRouter expects the fully
# qualified slug; Ollama expects the local tag pulled via ``ollama pull``.
DEFAULT_OPENROUTER_MODEL = "google/gemma-4-26b-a4b-it"
DEFAULT_OLLAMA_MODEL = "gemma4:e4b"

_ENV_LOADED = False


def _ensure_env_loaded() -> None:
    """Load ``.env`` from project root once per process."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    env_path = project_root() / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
    _ENV_LOADED = True


@dataclass(frozen=True)
class InferenceConfig:
    backend: str
    base_url: str
    api_key: str
    model: str


def _resolve_config() -> InferenceConfig:
    _ensure_env_loaded()
    backend = os.environ.get("INFERENCE_BACKEND", "ollama").strip().lower()
    if backend not in {"ollama", "openrouter"}:
        raise ValueError(
            f"INFERENCE_BACKEND must be 'ollama' or 'openrouter'; got {backend!r}"
        )

    if backend == "ollama":
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        model = os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        api_key = os.environ.get("OLLAMA_API_KEY", "ollama")
        return InferenceConfig(backend, base_url, api_key, model)

    base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    model = os.environ.get("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is required when INFERENCE_BACKEND=openrouter"
        )
    return InferenceConfig(backend, base_url, api_key, model)


@lru_cache(maxsize=1)
def _cached_client() -> tuple[OpenAI, InferenceConfig]:
    config = _resolve_config()
    client = OpenAI(base_url=config.base_url, api_key=config.api_key)
    logger.debug("gemma_client ready backend=%s model=%s", config.backend, config.model)
    return client, config


def current_config() -> InferenceConfig:
    return _cached_client()[1]


def reset_cache() -> None:
    """Clear the cached client. Used by tests that patch env vars."""
    _cached_client.cache_clear()
    global _ENV_LOADED, _LOG_PATH_CACHED, _semaphore
    _ENV_LOADED = False
    _LOG_PATH_CACHED = None
    _semaphore = None


# ---------------------------------------------------------------------------
# Concurrency guard
# ---------------------------------------------------------------------------
#
# The /build router fans out up to eight Gemma calls via asyncio.gather.
# OpenRouter enforces per-key RPM limits and a spike of eight simultaneous
# 26B-MoE calls from one demo machine can trip them. A module-level
# semaphore guarantees every async call site shares the budget and the
# guard cannot be forgotten at a new call site.
#
# The semaphore is lazy-constructed so GEMMA_MAX_CONCURRENCY can be set
# in tests before the first acquire, and so reset_cache() can rebuild it.

_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        max_concurrency = int(os.environ.get("GEMMA_MAX_CONCURRENCY", "8"))
        _semaphore = asyncio.Semaphore(max_concurrency)
    return _semaphore


# ---------------------------------------------------------------------------
# Native Ollama API helpers (think: false)
# ---------------------------------------------------------------------------
#
# Ollama's OpenAI-compatible /v1/chat/completions ignores ``think: false``
# even via ``extra_body``. Gemma 4 models default to extended thinking
# which consumes all output tokens with reasoning, leaving ``content``
# empty. The native /api/chat endpoint honors ``think: false``, so we
# use httpx for Ollama non-streaming and SSE for streaming.


def _ollama_native_url(config: InferenceConfig) -> str:
    """Derive the native Ollama API base from the OpenAI-compat base_url."""
    # base_url is like "http://localhost:11434/v1"
    return config.base_url.replace("/v1", "")


def _ollama_chat_sync(
    config: InferenceConfig,
    model: str,
    messages: list[dict[str, Any]],
    max_tokens: int,
    temperature: float,
    seed: int | None = None,
) -> dict[str, Any]:
    """Call Ollama native /api/chat with think=false. Returns parsed JSON."""
    url = f"{_ollama_native_url(config)}/api/chat"
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "think": False,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
        },
    }
    if seed is not None:
        payload["options"]["seed"] = seed
    resp = httpx.post(url, json=payload, timeout=180.0)
    resp.raise_for_status()
    return resp.json()


def _ollama_chat_stream(
    config: InferenceConfig,
    model: str,
    messages: list[dict[str, Any]],
    max_tokens: int,
    temperature: float,
    seed: int | None = None,
) -> Iterator[str]:
    """Stream Ollama native /api/chat with think=false. Yields content chunks."""
    url = f"{_ollama_native_url(config)}/api/chat"
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "think": False,
        "stream": True,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
        },
    }
    if seed is not None:
        payload["options"]["seed"] = seed
    with httpx.stream("POST", url, json=payload, timeout=180.0) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line.strip():
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue
            content = chunk.get("message", {}).get("content", "")
            if content:
                yield content


# ---------------------------------------------------------------------------
# JSONL call log
# ---------------------------------------------------------------------------
#
# Every Gemma call appends one JSON record to ``logs/gemma.jsonl`` at the
# project root so prompts, responses, finish reasons, token usage, and
# latency are inspectable after the fact. Set ``GEMMA_LOG_DISABLED=1`` to
# skip logging (tests, CI).

_LOG_PATH_CACHED: Path | None = None

# POSIX write atomicity only holds up to PIPE_BUF (512 bytes on macOS).
# A full Gemma record with system + user prompt + response can reach 10-20 KB,
# so two threads writing at once under the /build fan-out will interleave
# bytes and corrupt the JSONL. Serializing the append behind a lock costs
# nothing (8-wide worst case, network-dominated) and makes every line safe
# to parse downstream.
_log_lock = threading.Lock()


def _log_path() -> Path:
    global _LOG_PATH_CACHED
    if _LOG_PATH_CACHED is None:
        logs_dir = project_root() / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        _LOG_PATH_CACHED = logs_dir / "gemma.jsonl"
    return _LOG_PATH_CACHED


def _log_exchange(record: dict[str, Any]) -> None:
    """Append a single JSONL record. Never raises — logging must not crash callers."""
    if os.environ.get("GEMMA_LOG_DISABLED"):
        return
    try:
        path = _log_path()
        line = json.dumps(record, ensure_ascii=False, default=str)
        with _log_lock, path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("gemma jsonl log write failed: %s", exc)


def generate(
    *,
    system: str,
    user: str,
    max_tokens: int = 500,
    temperature: float = 0.7,
    seed: int | None = None,
    model: str | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    """Run a single chat completion and return the assistant text.

    Returns an empty string on failure — narratives are best-effort and
    must never crash the CLI. Callers log the error and fall back to a
    static placeholder.

    ``seed`` forwards to the OpenAI-compatible ``seed`` parameter when
    set. Both OpenRouter and Ollama accept it; with ``temperature=0`` it
    makes output reproducible for a given (prompt, model, seed) tuple,
    which is what demo determinism depends on.

    ``extra`` is merged into the JSONL log record — use it to stamp
    ``call_site`` and any other call-specific correlation fields so
    each call lands exactly one JSONL record tagged for audit.
    """
    return generate_chat(
        system=system,
        messages=[{"role": "user", "content": user}],
        max_tokens=max_tokens,
        temperature=temperature,
        seed=seed,
        model=model,
        extra=extra,
    )


def generate_chat(
    *,
    system: str,
    messages: list[dict[str, Any]],
    max_tokens: int = 500,
    temperature: float = 0.7,
    seed: int | None = None,
    model: str | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    """Multi-turn variant for conversational flows.

    ``messages`` is an OpenAI-format list of ``{"role", "content"}`` dicts
    (without the system message — that's passed separately). Returns an
    empty string on failure, same failure contract as ``generate()``.

    ``seed`` forwards to the OpenAI-compatible ``seed`` parameter when set.

    ``extra`` is merged into the JSONL log record.
    """
    client, config = _cached_client()
    resolved_model = model or config.model
    full_messages = [{"role": "system", "content": system}, *messages]
    record: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "backend": config.backend,
        "model": resolved_model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "seed": seed,
        "messages": full_messages,
    }
    if extra:
        # Extra fields first so our standard fields take precedence on any
        # collision (a caller passing ``response`` wouldn't override the
        # real Gemma output).
        record = {**extra, **record}
    started = time.perf_counter()

    # Ollama native API: the only path that reliably disables thinking.
    if config.backend == "ollama":
        try:
            data = _ollama_chat_sync(
                config, resolved_model, full_messages,
                max_tokens, temperature, seed,
            )
        except Exception as exc:
            record["duration_ms"] = int((time.perf_counter() - started) * 1000)
            record["error"] = f"{type(exc).__name__}: {exc}"
            _log_exchange(record)
            logger.warning("gemma generate failed backend=%s: %s", config.backend, exc)
            return ""

        record["duration_ms"] = int((time.perf_counter() - started) * 1000)
        content = data.get("message", {}).get("content", "").strip()
        finish_reason = data.get("done_reason", "stop")
        truncated = finish_reason == "length"
        if truncated:
            logger.warning(
                "gemma response truncated at max_tokens=%d (backend=%s). "
                "Trimming to last complete sentence.",
                max_tokens, config.backend,
            )
            content = _trim_to_last_sentence(content)
        record["finish_reason"] = finish_reason
        record["truncated"] = truncated
        record["response"] = content
        prompt_tokens = data.get("prompt_eval_count")
        eval_tokens = data.get("eval_count")
        if prompt_tokens is not None:
            record["usage"] = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": eval_tokens,
                "total_tokens": (prompt_tokens or 0) + (eval_tokens or 0),
            }
        _log_exchange(record)
        return content

    # OpenRouter / other OpenAI-compatible backends.
    completion_kwargs: dict[str, Any] = {
        "model": resolved_model,
        "messages": full_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if seed is not None:
        completion_kwargs["seed"] = seed

    try:
        response = client.chat.completions.create(**completion_kwargs)
    except Exception as exc:
        record["duration_ms"] = int((time.perf_counter() - started) * 1000)
        record["error"] = f"{type(exc).__name__}: {exc}"
        _log_exchange(record)
        logger.warning("gemma generate failed backend=%s: %s", config.backend, exc)
        return ""

    record["duration_ms"] = int((time.perf_counter() - started) * 1000)

    choices = getattr(response, "choices", None) or []
    if not choices:
        record["error"] = "no_choices"
        _log_exchange(record)
        return ""
    choice = choices[0]
    finish_reason = getattr(choice, "finish_reason", None)
    content = getattr(choice.message, "content", None) or ""
    content = content.strip()
    truncated = finish_reason == "length"
    if truncated:
        logger.warning(
            "gemma response truncated at max_tokens=%d (backend=%s). "
            "Trimming to last complete sentence.",
            max_tokens,
            config.backend,
        )
        content = _trim_to_last_sentence(content)

    usage = getattr(response, "usage", None)
    record["finish_reason"] = finish_reason
    record["truncated"] = truncated
    record["response"] = content
    if usage is not None:
        record["usage"] = {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }
    _log_exchange(record)
    return content


async def generate_async(
    *,
    system: str,
    user: str,
    max_tokens: int = 500,
    temperature: float = 0.7,
    seed: int | None = None,
    model: str | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    """Async variant of :func:`generate`.

    Acquires the module semaphore, then runs the sync ``generate`` inside
    a worker thread via :func:`asyncio.to_thread`. Preserves the
    empty-string-on-failure contract so callers never see exceptions
    from the transport layer.

    ``extra`` is merged into the JSONL log record.
    """
    sem = _get_semaphore()
    async with sem:
        return await asyncio.to_thread(
            generate,
            system=system,
            user=user,
            max_tokens=max_tokens,
            temperature=temperature,
            seed=seed,
            model=model,
            extra=extra,
        )


async def generate_chat_async(
    *,
    system: str,
    messages: list[dict[str, Any]],
    max_tokens: int = 500,
    temperature: float = 0.7,
    seed: int | None = None,
    model: str | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    """Async variant of :func:`generate_chat` — same semaphore discipline.

    ``extra`` is merged into the JSONL log record — matches
    :func:`generate_async` so call sites (e.g. set-your-course chip
    dispatcher) can stamp ``call_site`` and correlation fields.
    """
    sem = _get_semaphore()
    async with sem:
        return await asyncio.to_thread(
            generate_chat,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            seed=seed,
            model=model,
            extra=extra,
        )


async def generate_stream_async(
    *,
    system: str,
    messages: list[dict[str, Any]],
    max_tokens: int = 500,
    temperature: float = 0.7,
    seed: int | None = None,
    model: str | None = None,
    extra: dict[str, Any] | None = None,
) -> AsyncIterator[str]:
    """Streaming variant — yields content-delta chunks as they arrive.

    Uses OpenAI-compatible ``stream=True``. The sync iterator from the
    OpenAI client is drained in a worker thread and bridged to the async
    generator via a queue so the caller can ``async for`` over deltas
    without blocking the event loop.

    On transport failure the generator yields nothing (no exception
    raised) — matches the empty-string-on-failure contract of the other
    generate helpers. One JSONL record per call is appended under
    ``_log_lock`` with the fully assembled response, ``duration_ms``, and
    any ``extra`` fields the caller passed (e.g. ``call_site``).

    The semaphore is held for the entire streaming lifetime so the global
    concurrency budget stays honest.
    """
    import queue as _queue

    sem = _get_semaphore()
    async with sem:
        client, config = _cached_client()
        resolved_model = model or config.model
        full_messages = [{"role": "system", "content": system}, *messages]
        record: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "backend": config.backend,
            "model": resolved_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "seed": seed,
            "messages": full_messages,
            "streamed": True,
        }
        if extra:
            record = {**extra, **record}

        # Ollama native: use /api/chat with think=false + stream=true.
        use_native_ollama = config.backend == "ollama"

        # Sentinel types for the bridge queue.
        _DONE = object()
        q: "_queue.Queue[Any]" = _queue.Queue(maxsize=256)
        stream_holder: list[Any] = []

        def _drain_sync() -> None:
            try:
                if use_native_ollama:
                    for chunk in _ollama_chat_stream(
                        config, resolved_model, full_messages,
                        max_tokens, temperature, seed,
                    ):
                        q.put(chunk)
                else:
                    completion_kwargs: dict[str, Any] = {
                        "model": resolved_model,
                        "messages": full_messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "stream": True,
                    }
                    if seed is not None:
                        completion_kwargs["seed"] = seed
                    stream = client.chat.completions.create(**completion_kwargs)
                    stream_holder.append(stream)
                    for chunk in stream:
                        choices = getattr(chunk, "choices", None) or []
                        if not choices:
                            continue
                        delta = getattr(choices[0], "delta", None)
                        content = getattr(delta, "content", None) if delta else None
                        if content:
                            q.put(content)
            except Exception as exc:  # pragma: no cover - defensive
                q.put(("__error__", f"{type(exc).__name__}: {exc}"))
            finally:
                q.put(_DONE)

        started = time.perf_counter()
        loop = asyncio.get_running_loop()
        task = loop.run_in_executor(None, _drain_sync)

        assembled: list[str] = []
        error: str | None = None
        try:
            while True:
                item = await asyncio.to_thread(q.get)
                if item is _DONE:
                    break
                if isinstance(item, tuple) and item and item[0] == "__error__":
                    error = str(item[1])
                    break
                if isinstance(item, str):
                    assembled.append(item)
                    yield item
        finally:
            # On cancel / abort / GeneratorExit: close the OpenAI stream
            # so the drain thread's `for chunk in stream:` loop exits
            # promptly. Then drain any pending queue items so the thread's
            # final q.put(_DONE) can complete even if the queue is full.
            if stream_holder:
                try:
                    stream_holder[0].close()
                except Exception:  # pragma: no cover - defensive
                    pass
            while not task.done():
                try:
                    await asyncio.wait_for(
                        asyncio.to_thread(q.get), timeout=0.1
                    )
                except asyncio.TimeoutError:
                    continue
                except Exception:  # pragma: no cover - defensive
                    break
            try:
                await task
            except Exception:  # pragma: no cover - defensive
                pass

            record["duration_ms"] = int((time.perf_counter() - started) * 1000)
            record["response"] = "".join(assembled)
            if error is not None:
                record["error"] = error
            _log_exchange(record)
            if error is not None:
                logger.warning(
                    "gemma stream failed backend=%s: %s", config.backend, error
                )


def generate_with_tools(
    *,
    system: str,
    user: str,
    tools: list[dict[str, Any]],
    tool_choice: str | dict[str, Any] = "required",
    max_tokens: int = 600,
    temperature: float = 0.0,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Issue a chat completion with OpenAI-compatible function-calling.

    Returns ``{"name": <fn_name>, "arguments": <dict>}`` for the first
    tool call in the response, or ``None`` if the model returned a
    plain message instead of calling a tool, or on transport error.

    Works with both INFERENCE_BACKEND=ollama and openrouter.
    Logs to logs/gemma.jsonl with extra["call_site"] for traceability.
    """
    client, config = _cached_client()
    resolved_model = config.model
    full_messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    record: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "backend": config.backend,
        "model": resolved_model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "tool_calling": True,
        "messages": full_messages,
    }
    if extra:
        record = {**extra, **record}
    started = time.perf_counter()

    completion_kwargs: dict[str, Any] = {
        "model": resolved_model,
        "messages": full_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "tools": tools,
        "tool_choice": tool_choice,
    }

    try:
        response = client.chat.completions.create(**completion_kwargs)
    except Exception as exc:
        record["duration_ms"] = int((time.perf_counter() - started) * 1000)
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["tool_call_made"] = False
        _log_exchange(record)
        logger.warning(
            "gemma generate_with_tools failed backend=%s: %s",
            config.backend, exc,
        )
        return None

    record["duration_ms"] = int((time.perf_counter() - started) * 1000)

    choices = getattr(response, "choices", None) or []
    if not choices:
        record["error"] = "no_choices"
        record["tool_call_made"] = False
        _log_exchange(record)
        return None

    choice = choices[0]
    message = getattr(choice, "message", None)
    tool_calls = getattr(message, "tool_calls", None) if message else None

    if not tool_calls:
        content = getattr(message, "content", None) or ""
        content = content.strip()
        record["tool_call_made"] = False
        record["tool_choice_honored"] = False
        record["response"] = content

        parsed = _try_parse_json_from_content(content, tools)
        if parsed is not None:
            record["tool_call_made"] = True
            record["tool_choice_honored"] = False
            record["fallback"] = "content_json_parse"
            record["tool_name"] = parsed["name"]
            record["tool_arguments"] = parsed["arguments"]
            _log_exchange(record)
            logger.info(
                "gemma generate_with_tools: extracted tool call "
                "from content (backend=%s)",
                config.backend,
            )
            return parsed

        logger.info(
            "gemma generate_with_tools: no tool_calls, "
            "retrying as plain JSON prompt (backend=%s)",
            config.backend,
        )
        _log_exchange(record)

        return _fallback_prompt_for_json(
            system=system,
            user=user,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
            extra=extra,
        )

    tc = tool_calls[0]
    fn = getattr(tc, "function", None)
    if fn is None:
        record["tool_call_made"] = False
        _log_exchange(record)
        return None

    fn_name = getattr(fn, "name", "") or ""
    fn_args_raw = getattr(fn, "arguments", "") or ""

    try:
        fn_args = (
            json.loads(fn_args_raw)
            if isinstance(fn_args_raw, str)
            else fn_args_raw
        )
    except json.JSONDecodeError:
        record["tool_call_made"] = True
        record["error"] = f"unparseable_arguments: {fn_args_raw[:200]}"
        _log_exchange(record)
        logger.warning(
            "gemma generate_with_tools: unparseable tool args: %s",
            fn_args_raw[:200],
        )
        return None

    record["tool_call_made"] = True
    record["tool_choice_honored"] = True
    record["tool_name"] = fn_name
    record["tool_arguments"] = fn_args
    _log_exchange(record)

    return {"name": fn_name, "arguments": fn_args}


def _try_parse_json_from_content(
    content: str,
    tools: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Try to extract a tool call from the model's plain-text content.

    Some models return the tool-call JSON inside the content field
    instead of using the tool_calls mechanism. Looks for a JSON object
    containing keys that match the first tool's parameter schema.
    """
    if not content:
        return None

    fn_name = ""
    expected_keys: set[str] = set()
    for tool in tools:
        func = tool.get("function", {})
        fn_name = func.get("name", "")
        props = func.get("parameters", {}).get("properties", {})
        expected_keys = set(props.keys())
        break

    if not expected_keys:
        return None

    candidates = _extract_json_objects(content)
    for obj in candidates:
        if not isinstance(obj, dict):
            continue
        if expected_keys & set(obj.keys()):
            return {"name": fn_name, "arguments": obj}

    return None


def _extract_json_objects(text: str) -> list[Any]:
    """Extract JSON objects from text, handling markdown code fences."""
    import re as _re

    results: list[Any] = []

    fenced = _re.findall(r"```(?:json)?\s*\n?(.*?)\n?```", text, _re.DOTALL)
    for block in fenced:
        try:
            results.append(json.loads(block.strip()))
        except json.JSONDecodeError:
            pass

    if not results:
        brace_start = text.find("{")
        if brace_start >= 0:
            depth = 0
            for i in range(brace_start, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            results.append(
                                json.loads(text[brace_start : i + 1])
                            )
                        except json.JSONDecodeError:
                            pass
                        break

    return results


def _fallback_prompt_for_json(
    *,
    system: str,
    user: str,
    tools: list[dict[str, Any]],
    max_tokens: int,
    temperature: float,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Re-issue the request as a plain prompt asking for JSON output.

    Used when the model doesn't support the tools=[] parameter.
    Converts the tool schema into explicit JSON instructions in the
    prompt, calls generate(), and parses the JSON from the response.
    """
    fn_name = ""
    fn_params: dict[str, Any] = {}
    for tool in tools:
        func = tool.get("function", {})
        fn_name = func.get("name", "")
        fn_params = func.get("parameters", {})
        break

    if not fn_name:
        return None

    props = fn_params.get("properties", {})
    required = fn_params.get("required", [])
    schema_lines = []
    for key, spec in props.items():
        req_marker = " (required)" if key in required else ""
        desc = spec.get("description", "")
        schema_lines.append(f'  "{key}": {desc}{req_marker}')
    schema_text = "{\n" + ",\n".join(schema_lines) + "\n}"

    json_system = (
        f"{system}\n\n"
        f"CRITICAL INSTRUCTION: Your entire response must be a "
        f"single JSON object and nothing else. No thinking, no "
        f"explanation, no markdown fences, no preamble. Start "
        f"your response with {{ and end with }}.\n\n"
        f"Schema:\n{schema_text}"
    )

    fallback_extra = dict(extra) if extra else {}
    fallback_extra["fallback"] = "prompt_for_json"
    fallback_extra["original_tool"] = fn_name

    fallback_max_tokens = max(max_tokens, 1024)

    raw = generate(
        system=json_system,
        user=user,
        max_tokens=fallback_max_tokens,
        temperature=temperature,
        extra=fallback_extra,
    )

    if not raw:
        return None

    candidates = _extract_json_objects(raw)
    expected_keys = set(props.keys())
    for obj in candidates:
        if not isinstance(obj, dict):
            continue
        if expected_keys & set(obj.keys()):
            return {"name": fn_name, "arguments": obj}

    try:
        parsed = json.loads(raw.strip())
        if isinstance(parsed, dict) and expected_keys & set(parsed.keys()):
            return {"name": fn_name, "arguments": parsed}
    except json.JSONDecodeError:
        pass

    logger.warning(
        "gemma fallback JSON parse failed for tool=%s, raw=%s",
        fn_name, raw[:300],
    )
    return None


@dataclass(frozen=True)
class ToolCallTurn:
    turn_number: int
    tool_name: str
    tool_args: dict[str, Any]
    tool_result_size_bytes: int
    duration_ms: int
    error: str | None
    tool_result_preview: str = ""
    dispatch_index: int = 0


# Maximum length of the truncated tool result preview surfaced via the
# trace stream and AskResponse.tool_calls. 500 chars keeps log records
# lean while still giving the engineering view a meaningful sample.
_TOOL_RESULT_PREVIEW_MAX = 500


# Callback aliases for the trace stream. Both accept sync OR async
# returns — the loop's invocation shim awaits when it sees a coroutine.
TurnStartCallback = Callable[[int, str, dict[str, Any]], Any]
TurnEventCallback = Callable[["ToolCallTurn"], Any]


async def _invoke_callback(callback: Callable[..., Any] | None, *args: Any) -> None:
    """Invoke an opt-in trace callback. Handles sync OR async callables.
    Swallows + logs any exception so a broken consumer never breaks the
    Gemma loop. Trace is supplementary — chat must keep working.
    """
    if callback is None:
        return
    try:
        result = callback(*args)
        if asyncio.iscoroutine(result):
            await result
    except Exception as exc:  # noqa: BLE001 — callback isolation is the point
        logger.warning("trace callback raised: %s", exc)


async def generate_with_tools_loop(
    *,
    system: str,
    user: str,
    tools: list[dict[str, Any]],
    dispatch: Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]],
    max_turns: int = 3,
    max_wall_time_s: float = 30.0,
    temperature: float = 0.0,
    max_tokens: int = 600,
    extra: dict[str, Any] | None = None,
    on_turn_start: TurnStartCallback | None = None,
    on_turn_event: TurnEventCallback | None = None,
) -> tuple[str, list[ToolCallTurn]]:
    """Multi-turn Gemma tool-calling loop.

    Returns ``(final_text, tool_call_log)``. On transport failure or
    cap hit, returns ``("", [...])``.

    ``on_turn_start`` and ``on_turn_event`` are opt-in trace callbacks
    (see docs/specs/feature-gemma-trace.md, Decisions #12–#13). When set:

    - ``on_turn_start(dispatch_index, tool_name, tool_args)`` fires
      immediately before each ``await dispatch(...)``. ``dispatch_index``
      is monotonically unique across the entire chat turn (including
      parallel tool calls in one outer LLM turn).
    - ``on_turn_event(tool_call_turn)`` fires immediately after each
      ``ToolCallTurn`` is appended to ``tool_call_log``.

    Both callbacks are fired-and-forgotten: exceptions are caught and
    logged at WARNING; the loop continues. Sync or async callables are
    both supported. Both default to ``None`` (no-op) to preserve
    backward compatibility with all existing callers.
    """
    sem = _get_semaphore()
    async with sem:
        return await _tools_loop_inner(
            system=system,
            user=user,
            tools=tools,
            dispatch=dispatch,
            max_turns=max_turns,
            max_wall_time_s=max_wall_time_s,
            temperature=temperature,
            max_tokens=max_tokens,
            extra=extra,
            on_turn_start=on_turn_start,
            on_turn_event=on_turn_event,
        )


async def _tools_loop_inner(
    *,
    system: str,
    user: str,
    tools: list[dict[str, Any]],
    dispatch: Callable,  # type: ignore[type-arg]
    max_turns: int,
    max_wall_time_s: float,
    temperature: float,
    max_tokens: int,
    extra: dict[str, Any] | None,
    on_turn_start: TurnStartCallback | None = None,
    on_turn_event: TurnEventCallback | None = None,
) -> tuple[str, list[ToolCallTurn]]:
    """Core loop logic, runs inside the semaphore."""
    _client, config = _cached_client()
    is_ollama = config.backend == "ollama"

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    tool_call_log: list[ToolCallTurn] = []
    wall_start = time.perf_counter()

    for turn in range(max_turns):
        remaining = max_wall_time_s - (time.perf_counter() - wall_start)
        if remaining <= 0:
            logger.warning(
                "generate_with_tools_loop: wall time cap hit at turn %d",
                turn,
            )
            break

        turn_start = time.perf_counter()
        # Tools are offered on every turn up to ``max_turns``. Pre-trace
        # the loop dropped tools after the first dispatch (anti-runaway
        # guard); now that the trace IS the value (feature-gemma-trace.md)
        # and the system prompt biases toward tool use, we let Gemma
        # chain across turns. ``max_turns`` and ``max_wall_time_s``
        # remain the load-bearing bounds.
        turn_tools = tools
        try:
            response_text, response_tool_calls = await asyncio.wait_for(
                _one_tool_turn(
                    messages=messages,
                    tools=turn_tools,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    turn_number=turn,
                    extra=extra,
                ),
                timeout=remaining,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "generate_with_tools_loop: wall time cap during turn %d",
                turn,
            )
            break

        if response_tool_calls is None:
            # Transport error
            _log_tool_turn(
                turn_number=turn,
                tools_offered=[_tool_name(t) for t in tools],
                tool_called=None,
                tool_result_size=0,
                duration_ms=int((time.perf_counter() - turn_start) * 1000),
                error="transport_error",
                extra=extra,
            )
            return "", tool_call_log

        if not response_tool_calls:
            # Plain text response — done
            _log_tool_turn(
                turn_number=turn,
                tools_offered=[_tool_name(t) for t in tools],
                tool_called=None,
                tool_result_size=0,
                duration_ms=int((time.perf_counter() - turn_start) * 1000),
                error=None,
                extra=extra,
            )
            return response_text, tool_call_log

        # Process each tool call
        for tc in response_tool_calls:
            fn_name = tc.get("name", "")
            fn_args = tc.get("arguments", {})
            tc_id = tc.get("id", f"call_{turn}")

            # dispatch_index is the per-dispatch monotonic key shared
            # by on_turn_start and on_turn_event for the SSE trace
            # (Decision #13). Captured BEFORE dispatch so turn_start
            # carries the same key the appended ToolCallTurn will hold.
            dispatch_index = len(tool_call_log)
            await _invoke_callback(on_turn_start, dispatch_index, fn_name, fn_args)

            dispatch_start = time.perf_counter()
            dispatch_error: str | None = None
            result_str = ""
            dispatch_remaining = max_wall_time_s - (
                time.perf_counter() - wall_start
            )
            try:
                result = await asyncio.wait_for(
                    dispatch(fn_name, fn_args),
                    timeout=max(dispatch_remaining, 0.1),
                )
                result_str = json.dumps(result, default=str)
            except asyncio.TimeoutError:
                dispatch_error = "TimeoutError: wall time cap during dispatch"
                result_str = json.dumps({"error": dispatch_error})
                logger.warning(
                    "generate_with_tools_loop: dispatch %s timed out",
                    fn_name,
                )
            except Exception as exc:
                dispatch_error = f"{type(exc).__name__}: {exc}"
                result_str = json.dumps({"error": str(exc)})
                logger.warning(
                    "generate_with_tools_loop: dispatch %s failed: %s",
                    fn_name, exc,
                )

            dispatch_ms = int((time.perf_counter() - dispatch_start) * 1000)
            turn_obj = ToolCallTurn(
                turn_number=turn,
                tool_name=fn_name,
                tool_args=fn_args,
                tool_result_size_bytes=len(result_str.encode()),
                duration_ms=dispatch_ms,
                error=dispatch_error,
                tool_result_preview=result_str[:_TOOL_RESULT_PREVIEW_MAX],
                dispatch_index=dispatch_index,
            )
            tool_call_log.append(turn_obj)
            await _invoke_callback(on_turn_event, turn_obj)

            _log_tool_turn(
                turn_number=turn,
                tools_offered=[_tool_name(t) for t in tools],
                tool_called=fn_name,
                tool_result_size=len(result_str.encode()),
                duration_ms=int((time.perf_counter() - turn_start) * 1000),
                error=dispatch_error,
                extra=extra,
            )

            if dispatch_error:
                return "", tool_call_log

            # Append assistant tool-call + tool result to history so the
            # next turn can either read the result and produce text, or
            # decide it needs another tool call.
            # Ollama native API uses a different message shape.
            if is_ollama:
                messages.append({
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{
                        "function": {
                            "name": fn_name,
                            "arguments": fn_args,
                        },
                    }],
                })
                messages.append({
                    "role": "tool",
                    "content": result_str,
                })
            else:
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": tc_id,
                        "type": "function",
                        "function": {
                            "name": fn_name,
                            "arguments": json.dumps(fn_args),
                        },
                    }],
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": result_str,
                })

    # If we exhausted turns without a plain-text response, return empty
    final_text = ""
    if tool_call_log:
        logger.warning(
            "generate_with_tools_loop: turn cap reached (%d turns)", max_turns
        )
    return final_text, tool_call_log


async def _one_tool_turn(
    *,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    temperature: float,
    max_tokens: int,
    turn_number: int,
    extra: dict[str, Any] | None,
) -> tuple[str, list[dict[str, Any]] | None]:
    """Issue one Gemma call. Returns (text, tool_calls_list | None on error).

    An empty tool_calls list means plain text response.

    Routes Ollama through the native ``/api/chat`` endpoint with
    ``tools`` + ``think: false`` to avoid the OpenAI-compat endpoint's
    thinking-mode token drain.
    """
    _client, config = _cached_client()
    resolved_model = config.model

    if config.backend == "ollama":
        return await _one_tool_turn_ollama(
            config=config,
            model=resolved_model,
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            turn_number=turn_number,
        )

    # OpenRouter / other OpenAI-compatible backends.
    completion_kwargs: dict[str, Any] = {
        "model": resolved_model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if tools:
        completion_kwargs["tools"] = tools
        completion_kwargs["tool_choice"] = "auto"

    def _call() -> Any:
        return _client.chat.completions.create(**completion_kwargs)

    try:
        response = await asyncio.to_thread(_call)
    except Exception as exc:
        logger.warning(
            "generate_with_tools_loop turn %d failed: %s", turn_number, exc
        )
        return "", None

    choices = getattr(response, "choices", None) or []
    if not choices:
        return "", None

    choice = choices[0]
    message = getattr(choice, "message", None)
    tool_calls_raw = getattr(message, "tool_calls", None) if message else None

    if not tool_calls_raw:
        content = getattr(message, "content", None) or ""
        return content.strip(), []

    parsed_calls: list[dict[str, Any]] = []
    for tc in tool_calls_raw:
        fn = getattr(tc, "function", None)
        if fn is None:
            continue
        fn_name = getattr(fn, "name", "") or ""
        fn_args_raw = getattr(fn, "arguments", "") or ""
        try:
            fn_args = (
                json.loads(fn_args_raw)
                if isinstance(fn_args_raw, str)
                else fn_args_raw
            )
        except json.JSONDecodeError:
            fn_args = {}
        parsed_calls.append({
            "id": getattr(tc, "id", f"call_{turn_number}"),
            "name": fn_name,
            "arguments": fn_args if isinstance(fn_args, dict) else {},
        })

    return "", parsed_calls


async def _one_tool_turn_ollama(
    *,
    config: InferenceConfig,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    temperature: float,
    max_tokens: int,
    turn_number: int,
) -> tuple[str, list[dict[str, Any]] | None]:
    """Ollama native /api/chat with tools + think=false."""
    url = f"{_ollama_native_url(config)}/api/chat"
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "think": False,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
        },
    }
    if tools:
        payload["tools"] = tools

    def _call() -> dict[str, Any]:
        resp = httpx.post(url, json=payload, timeout=180.0)
        resp.raise_for_status()
        return resp.json()

    try:
        data = await asyncio.to_thread(_call)
    except Exception as exc:
        logger.warning(
            "generate_with_tools_loop turn %d failed (ollama): %s",
            turn_number, exc,
        )
        return "", None

    message = data.get("message", {})
    tool_calls_raw = message.get("tool_calls")

    if not tool_calls_raw:
        content = message.get("content", "").strip()
        return content, []

    parsed_calls: list[dict[str, Any]] = []
    for tc in tool_calls_raw:
        fn = tc.get("function", {})
        fn_name = fn.get("name", "")
        fn_args = fn.get("arguments", {})
        if not isinstance(fn_args, dict):
            try:
                fn_args = json.loads(fn_args) if isinstance(fn_args, str) else {}
            except json.JSONDecodeError:
                fn_args = {}
        parsed_calls.append({
            "id": tc.get("id", f"call_{turn_number}"),
            "name": fn_name,
            "arguments": fn_args,
        })

    return "", parsed_calls


def _tool_name(tool: dict[str, Any]) -> str:
    func: dict[str, Any] = tool.get("function") or {}
    return str(func.get("name", "unknown"))


def _log_tool_turn(
    *,
    turn_number: int,
    tools_offered: list[str],
    tool_called: str | None,
    tool_result_size: int,
    duration_ms: int,
    error: str | None,
    extra: dict[str, Any] | None,
) -> None:
    record: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "call_site": (extra or {}).get("call_site", "unknown"),
        "turn_number": turn_number,
        "tools_offered": tools_offered,
        "tool_called": tool_called,
        "tool_result_size": tool_result_size,
        "duration_ms": duration_ms,
    }
    if error:
        record["error"] = error
    if extra:
        for k, v in extra.items():
            if k not in record:
                record[k] = v
    _log_exchange(record)


def _trim_to_last_sentence(text: str) -> str:
    """Cut text at the last sentence terminator so it doesn't hang."""
    if not text:
        return text
    for terminator in (". ", "! ", "? ", ".\n", "!\n", "?\n"):
        idx = text.rfind(terminator)
        if idx >= 0:
            return text[: idx + 1].rstrip()
    # No terminator found — just return the last full line.
    last_newline = text.rfind("\n")
    if last_newline >= 0:
        return text[:last_newline].rstrip()
    return text.rstrip()


def dotenv_path() -> Path:
    return project_root() / ".env"
