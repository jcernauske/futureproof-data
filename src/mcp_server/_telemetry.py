"""Structured timing logs for the MCP data-access layer.

Mirrors ``backend/app/services/gemma_client._log_exchange``: one JSON
line per event appended to ``logs/mcp.jsonl`` at the project root,
guarded by a module-level ``threading.Lock`` because MCP records
routinely exceed POSIX ``PIPE_BUF`` (4096 bytes on macOS) and
concurrent appends would interleave under ``asyncio.to_thread``
fan-out.

The ``@timed`` decorator wraps sync callables, records
``time.perf_counter()`` deltas, and emits one JSON line on both
success and exception paths. Callers pass an ``extract`` callable
that pulls per-call context (e.g. ``path``, ``unitid``, ``cipcode``,
``row_count``, ``cache_hit``) out of the function's args and return
value.

Logging policy: ``extra`` is bounded-cardinality only. Enums, numeric
IDs, row counts, category labels, booleans — never free-text user
input (e.g. raw ``student_major`` strings, intent transcripts).
``unitid`` and ``cipcode`` at the top level are IPEDS / CIP public
identifiers and are intentionally included for grep-ability.
"""

from __future__ import annotations

import functools
import json
import logging
import os
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# logs/ lives at the repo root. __file__ is
# src/mcp_server/_telemetry.py, so parents[2] = repo root.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOG_PATH_CACHED: Path | None = None

# POSIX append atomicity only holds up to PIPE_BUF. A timing record
# carrying an ``extra`` payload can easily exceed that, so two threads
# appending under the substitution fan-out would interleave bytes and
# corrupt the JSONL. Serialize behind a lock — cost is negligible at
# hackathon request rates.
_log_lock = threading.Lock()


def _log_path() -> Path:
    global _LOG_PATH_CACHED
    if _LOG_PATH_CACHED is None:
        logs_dir = _PROJECT_ROOT / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        _LOG_PATH_CACHED = logs_dir / "mcp.jsonl"
    return _LOG_PATH_CACHED


def emit(record: dict[str, Any]) -> None:
    """Append a single JSONL record. Never raises — telemetry must not
    crash callers. Set ``MCP_LOG_DISABLED=1`` to skip (tests, CI)."""
    if os.environ.get("MCP_LOG_DISABLED"):
        return
    try:
        path = _log_path()
        line = json.dumps(record, ensure_ascii=False, default=str)
        with _log_lock, path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("mcp jsonl log write failed: %s", exc)


ExtractFn = Callable[..., dict[str, Any]]


def timed(
    event: str,
    *,
    extract: ExtractFn | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator factory: wrap a sync callable with timing + logging.

    ``extract`` is invoked with ``(result, *args, **kwargs)`` after the
    wrapped callable returns and should return a dict merged into the
    log record. Keep it bounded-cardinality (see module docstring).
    On exception the wrapped function's exception propagates after the
    record is emitted with ``error`` set to the exception message and
    ``duration_ms`` measured up to the failure point.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            started = time.perf_counter()
            ts = datetime.now(timezone.utc).isoformat()
            result: Any = None
            err: BaseException | None = None
            try:
                result = fn(*args, **kwargs)
                return result
            except BaseException as exc:
                err = exc
                raise
            finally:
                duration_ms = int((time.perf_counter() - started) * 1000)
                record: dict[str, Any] = {
                    "ts": ts,
                    "event": event,
                    "duration_ms": duration_ms,
                }
                if extract is not None and err is None:
                    try:
                        record.update(extract(result, *args, **kwargs))
                    except Exception as exc:  # pragma: no cover - defensive
                        logger.debug("telemetry extract failed for %s: %s", event, exc)
                if err is not None:
                    record["error"] = f"{type(err).__name__}: {err}"
                emit(record)

        return wrapper

    return decorator
