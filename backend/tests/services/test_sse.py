"""Unit tests for the shared SSE wire-format helper.

Backs feature-gemma-trace.md §4 — the helper is the single source of
truth for the ``event:`` / ``data:`` framing across three router modules
(``builds``, ``set_your_course``, ``ask_gemma_router``).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from app.services._sse import sse_event


def test_sse_event_format() -> None:
    """The output is exactly ``event: <name>\\ndata: <json>\\n\\n``.

    Two-newline trailer is the SSE spec's frame separator; consumers
    that split on ``"\\n\\n"`` rely on it.
    """
    out = sse_event("turn_start", {"turn": 0, "tool": "x"})
    assert out == 'event: turn_start\ndata: {"turn": 0, "tool": "x"}\n\n'


def test_sse_event_default_str_encoder() -> None:
    """``default=str`` lets datetime / UUID values serialize without
    raising. The trace stream carries plain dicts but the helper is
    shared with build creation which can serialize timestamps."""
    when = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)
    uid = uuid.UUID("12345678-1234-5678-1234-567812345678")
    out = sse_event("test", {"when": when, "id": uid})
    # Both values appear stringified in the JSON payload.
    assert "2026-05-01" in out
    assert "12345678-1234-5678-1234-567812345678" in out
    # The frame still parses as valid SSE.
    assert out.startswith("event: test\ndata: ")
    assert out.endswith("\n\n")


def test_sse_event_preserves_non_ascii() -> None:
    """``ensure_ascii=False`` keeps non-ASCII characters readable on the
    wire. Important for localized chat answers and school names like
    ``Université de Montréal``."""
    out = sse_event("final_text", {"response": "Université"})
    assert "Université" in out


def test_sse_event_data_is_valid_json() -> None:
    """The ``data:`` line is parseable JSON for any consumer."""
    payload = {"k": "v", "n": 42, "b": True, "z": None, "lst": [1, 2, 3]}
    out = sse_event("evt", payload)
    # Strip the SSE wrapper to extract the JSON payload.
    data_line = out.split("\n")[1]
    assert data_line.startswith("data: ")
    parsed = json.loads(data_line[len("data: "):])
    assert parsed == payload
