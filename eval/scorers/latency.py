"""Latency aggregation. Reads duration_ms values, returns p50/p95/p99."""

from __future__ import annotations

from statistics import median
from typing import TypedDict


class LatencyStats(TypedDict):
    n: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float
    min_ms: int
    max_ms: int


def _percentile(sorted_values: list[int], pct: float) -> float:
    """Linear-interpolation percentile. Matches numpy default."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = rank - lo
    return sorted_values[lo] + frac * (sorted_values[hi] - sorted_values[lo])


def latency_percentiles(durations_ms: list[int]) -> LatencyStats:
    """Compute p50/p95/p99 plus summary stats. Empty input returns zeros."""
    if not durations_ms:
        return LatencyStats(
            n=0, p50_ms=0.0, p95_ms=0.0, p99_ms=0.0, mean_ms=0.0, min_ms=0, max_ms=0
        )
    sorted_values = sorted(durations_ms)
    return LatencyStats(
        n=len(sorted_values),
        p50_ms=float(median(sorted_values)),
        p95_ms=_percentile(sorted_values, 95.0),
        p99_ms=_percentile(sorted_values, 99.0),
        mean_ms=sum(sorted_values) / len(sorted_values),
        min_ms=sorted_values[0],
        max_ms=sorted_values[-1],
    )
