"""Shared SSE wire-format helper.

Used by build creation (``routers/builds.py``), set-your-course intent
streaming (``routers/set_your_course.py``), and the Ask Gemma trace
stream (``routers/ask_gemma_router.py``). Single source of truth for
``event:`` / ``data:`` framing.

See ``docs/specs/feature-gemma-trace.md`` Decision #11 (SSE wire format)
and the spec's File Changes table.
"""

from __future__ import annotations

import json
from typing import Any


def sse_event(event: str, data: Any) -> str:
    """Format a single SSE frame.

    JSON-encodes ``data`` with ``default=str`` for datetime / UUID
    safety and ``ensure_ascii=False`` so non-ASCII content survives.
    Always terminates with a blank line per the SSE spec so consumers
    that split on ``\\n\\n`` parse each frame as one event.
    """
    payload = json.dumps(data, default=str, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"
