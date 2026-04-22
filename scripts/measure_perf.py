"""Measure wall-clock latency of _handle_get_career_paths on canonical requests.

Runs each request 10 times back-to-back from a fresh process. Reports
median + p95 + query-count per path. Feeds the §9 "Performance
Verification" table in the spec.
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
for p in (str(_PROJECT_ROOT / "backend"), str(_PROJECT_ROOT / "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.services.mcp_client import get_server  # noqa: E402

CASES: list[tuple[str, dict]] = [
    (
        "substituted (UIUC+26.01→Biology)",
        {"unitid": 145637, "cipcode": "26.01", "student_major": "Biology"},
    ),
    (
        "substituted (IU+52.01→Marketing)",
        {"unitid": 151351, "cipcode": "52.01", "student_major": "Marketing"},
    ),
    ("standard (IU+52.14)", {"unitid": 151351, "cipcode": "52.14"}),
]


def _time_one(server, inputs: dict) -> float:
    t0 = time.perf_counter()
    server._handle_get_career_paths(inputs)
    return (time.perf_counter() - t0) * 1000


def main() -> None:
    server = get_server()
    for name, inputs in CASES:
        # Warm-up to isolate steady-state latency (first call pays the
        # QueryEngine init + view registration cost).
        _time_one(server, inputs)
        samples = [_time_one(server, inputs) for _ in range(10)]
        median = statistics.median(samples)
        p95 = sorted(samples)[int(len(samples) * 0.95) - 1]
        print(
            f"{name:<40}  median={median:7.1f}ms  p95={p95:7.1f}ms  "
            f"min={min(samples):6.1f}ms  max={max(samples):6.1f}ms"
        )


if __name__ == "__main__":
    main()
