"""Instrumentation glue: maps production call_site strings to eval surfaces and
reads logs/gemma.jsonl for latency aggregation."""

from eval.instrumentation.call_site_map import (
    SURFACE_TO_CALL_SITES,
    canonical_surface,
    iter_log_records,
    latency_for_surface,
)

__all__ = [
    "SURFACE_TO_CALL_SITES",
    "canonical_surface",
    "iter_log_records",
    "latency_for_surface",
]
