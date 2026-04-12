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

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

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
    global _ENV_LOADED, _LOG_PATH_CACHED
    _ENV_LOADED = False
    _LOG_PATH_CACHED = None


# ---------------------------------------------------------------------------
# JSONL call log
# ---------------------------------------------------------------------------
#
# Every Gemma call appends one JSON record to ``logs/gemma.jsonl`` at the
# project root so prompts, responses, finish reasons, token usage, and
# latency are inspectable after the fact. Set ``GEMMA_LOG_DISABLED=1`` to
# skip logging (tests, CI).

_LOG_PATH_CACHED: Path | None = None


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
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("gemma jsonl log write failed: %s", exc)


def generate(
    *,
    system: str,
    user: str,
    max_tokens: int = 500,
    temperature: float = 0.7,
    model: str | None = None,
) -> str:
    """Run a single chat completion and return the assistant text.

    Returns an empty string on failure — narratives are best-effort and
    must never crash the CLI. Callers log the error and fall back to a
    static placeholder.
    """
    return generate_chat(
        system=system,
        messages=[{"role": "user", "content": user}],
        max_tokens=max_tokens,
        temperature=temperature,
        model=model,
    )


def generate_chat(
    *,
    system: str,
    messages: list[dict],
    max_tokens: int = 500,
    temperature: float = 0.7,
    model: str | None = None,
) -> str:
    """Multi-turn variant for conversational flows.

    ``messages`` is an OpenAI-format list of ``{"role", "content"}`` dicts
    (without the system message — that's passed separately). Returns an
    empty string on failure, same failure contract as ``generate()``.
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
        "messages": full_messages,
    }
    started = time.perf_counter()

    try:
        response = client.chat.completions.create(
            model=resolved_model,
            messages=full_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
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
