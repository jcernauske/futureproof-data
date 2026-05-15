"""Surface adapter protocol.

An adapter takes a GoldenCase's `inputs` dict and runs the production code
path that owns one Gemma surface. It returns whatever the surface produces
(structured dict, narrative string, tool-call list) plus latency from the
in-process timer. The runner combines that output with golden expectations
to score.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class AdapterResult:
    """One production run of one surface against one input set."""

    actual_output: Any
    """Surface-specific output. May be:
    - dict (structured surfaces — JSON parsed)
    - str (narrative surfaces — raw text)
    - tuple[str, list[dict]] (tool-using surfaces — text + tool_call_log)
    None on adapter failure (logged in error)."""

    latency_ms: int
    """Wall-clock latency for the underlying call. From perf_counter wrapping
    the adapter's invocation — independent of the production JSONL log."""

    error: str | None = None
    """Adapter-level failure. Production-side failures (Gemma 500s, parse
    errors) should land here, not crash the eval."""

    raw: dict[str, Any] = field(default_factory=dict)
    """Surface-specific raw payload — extra fields like tool_call_log,
    confidence, finish_reason, etc. Not used for scoring directly but available
    for results inspection."""


class SurfaceAdapter(Protocol):
    surface_name: str
    """Canonical surface name. Must match a key in
    eval.instrumentation.call_site_map.SURFACE_TO_CALL_SITES."""

    tier: str
    """P0 | P1 | P2 — drives which `make eval-*` target picks this up."""

    def run(self, inputs: dict[str, Any]) -> AdapterResult:
        """Run the production code path for this surface with golden inputs.

        Adapters MUST catch their own exceptions and return them via
        AdapterResult.error. The runner does not retry on failure — one
        case, one outcome.
        """
        ...


def time_call(fn, *args, **kwargs) -> tuple[Any, int]:
    """Helper: invoke `fn(*args, **kwargs)`, return (result, latency_ms).

    Used inside adapters to wrap the production call site. The production
    code is already instrumented for JSONL logging — this timer is the
    eval-side measurement that does not depend on the JSONL log being
    readable (CI environments without the file, etc.).
    """
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return result, elapsed_ms
