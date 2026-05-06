"""Ask Gemma router — POST /chat/ask.

Single endpoint for the scope-aware chat surface on /my-build (per-
element entry points + sticky FAB) and the build compare screen
(entry point under "Gemma's Take").

The discriminated ``scope`` payload determines which build(s) to
load and which context-builder runs. ``ask_gemma.chat_ask`` returns
the localized ``chat_unavailable`` fallback string with status 200
when Gemma is unreachable — never a 5xx. See
docs/specs/feature-ask-gemma.md.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.api import AskRequest, AskResponse
from app.services import ask_gemma, builds
from app.services._sse import sse_event
from app.services.builds import Build

logger = logging.getLogger(__name__)

router = APIRouter()


async def _load_builds(scope_kind: str, build_ids: list[str]) -> list[Build]:
    """Load builds, skipping missing ones for compare scope."""
    if scope_kind == "compare":
        results = await asyncio.gather(
            *(asyncio.to_thread(builds.load_build, bid) for bid in build_ids),
            return_exceptions=True,
        )
        loaded = [r for r in results if isinstance(r, Build)]
        if len(loaded) < 2:
            raise FileNotFoundError("Not enough builds could be loaded for comparison")
        return loaded

    loaded = await asyncio.gather(
        *(asyncio.to_thread(builds.load_build, bid) for bid in build_ids)
    )
    return list(loaded)


@router.post("/chat/ask")
async def chat_ask(request: AskRequest) -> AskResponse:
    """Scope-aware chat. The Pydantic ``AskScope.model_validator``
    already enforces cardinality and target_id constraints, so a 422
    from FastAPI fires before this handler runs on bad payloads."""
    try:
        loaded = await _load_builds(request.scope.kind, request.scope.build_ids)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        return await ask_gemma.chat_ask(
            scope=request.scope,
            builds=loaded,
            message=request.message,
            history=request.history,
            locale=request.locale,
        )
    except ask_gemma.SkillNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/chat/ask/stream")
async def chat_ask_stream(request: AskRequest) -> StreamingResponse:
    """SSE variant of /chat/ask. Streams ``TraceEvent`` frames as Gemma
    works through its tool-call loop, finishing with ``final_text``
    then ``done``.

    The frontend tries this endpoint first; on connection failure (HTTP
    error or thrown exception in the read loop), it falls back to the
    non-streaming ``/chat/ask`` endpoint and synthesizes trace events
    from ``AskResponse.tool_calls`` (feature-gemma-trace.md §4 Service
    Changes — frontend askGemmaStream).
    """
    try:
        loaded = await _load_builds(request.scope.kind, request.scope.build_ids)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def _stream() -> AsyncIterator[str]:
        try:
            async for ev in ask_gemma.chat_ask_stream(
                scope=request.scope,
                builds=loaded,
                message=request.message,
                history=request.history,
                locale=request.locale,
            ):
                yield sse_event(ev.type, ev.model_dump(mode="json"))
        except ask_gemma.SkillNotFoundError as exc:
            # SkillNotFoundError is a logical 404 from the service.
            # In a streaming response we surface it as a final error
            # event then close, since the response headers were
            # already sent.
            yield sse_event("error", {"detail": str(exc)})
            yield sse_event("done", {})

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
