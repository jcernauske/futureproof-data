"""FastAPI router for the Set Your Course screen.

Three endpoints, all mounted under ``/intent`` so they coexist with the
existing ``intent.router``:

- ``POST /intent/stream`` — server-sent events stream for the initial
  major-resolution, carrying prose deltas, the final IntentResult, and
  community suggestions.
- ``POST /intent/chip`` — stateless chip dispatch.
- ``POST /intent/commit`` — writes a correction log record on commit.

See docs/specs/feature-set-your-course.md §4.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.api import (
    ChipRequest,
    ChipResponse,
    CommitRequest,
    IntentStreamRequest,
)
from app.services import set_your_course
from app.services._sse import sse_event

logger = logging.getLogger(__name__)

router = APIRouter()


async def _stream_events(
    request: IntentStreamRequest,
) -> AsyncIterator[str]:
    try:
        async for event in set_your_course.stream_initial_resolution(
            major_text=request.major_text,
            school_name=request.school_name,
            unitid=request.unitid,
            programs=request.programs,
            locale=request.locale,
        ):
            name = event.get("event", "delta")
            data = event.get("data", {})
            yield sse_event(name, data)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("set_your_course stream failed: %s", exc)
        yield sse_event(
            "error",
            {"message": "stream failed — try again."},
        )
        yield sse_event("done", {})


@router.post("/stream")
async def stream(request: IntentStreamRequest) -> StreamingResponse:
    """Stream the initial resolution as server-sent events."""
    return StreamingResponse(
        _stream_events(request),
        media_type="text/event-stream",
        headers={
            # Disable intermediate buffering so the student sees prose
            # as it arrives, not after a full flush.
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chip", response_model=ChipResponse)
async def chip(request: ChipRequest) -> ChipResponse:
    """Dispatch one chip tap and return the chip response.

    The Pydantic model validator on ``ChipRequest`` rejects a
    ``not_expected`` request with a missing clarifier, so FastAPI
    returns 422 automatically for that case — no explicit handling
    here.
    """
    try:
        return await set_your_course.handle_chip_dispatch(request)
    except Exception as exc:
        logger.exception("set_your_course chip dispatch failed: %s", exc)
        raise HTTPException(
            status_code=500, detail="chip dispatch failed"
        ) from exc


@router.post("/commit")
async def commit(request: CommitRequest) -> dict[str, bool]:
    """Write one correction log record on commit.

    Returns ``{"committed": True, "logged": <bool>}``. ``logged`` is
    ``False`` when the initial and current CIPs are identical (nothing
    to learn from).
    """
    logged = set_your_course.record_commit(request)
    return {"committed": True, "logged": logged}
