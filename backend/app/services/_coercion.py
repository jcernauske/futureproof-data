"""Shared numeric coercion helpers for MCP row values.

DuckDB/Iceberg round-trips can produce either int or float for numeric
columns; these helpers normalize to the Python type the model expects
while preserving NULL semantics.
"""

from __future__ import annotations

from typing import Any


def as_float(value: Any) -> float | None:
    """Coerce numeric MCP values (int or float) to float; pass through None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def as_int(value: Any) -> int | None:
    """Coerce numeric MCP values to int; pass through None. Rounds floats."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(round(value))
    return None
