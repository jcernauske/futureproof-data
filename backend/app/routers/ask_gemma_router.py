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

from fastapi import APIRouter, HTTPException

from app.models.api import AskRequest, AskResponse
from app.services import ask_gemma, builds

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat/ask")
async def chat_ask(request: AskRequest) -> AskResponse:
    """Scope-aware chat. The Pydantic ``AskScope.model_validator``
    already enforces cardinality and target_id constraints, so a 422
    from FastAPI fires before this handler runs on bad payloads."""
    try:
        # load_build is sync DuckDB; run it on a worker thread (and fan
        # out across compare-scope's 2-4 build_ids in parallel) so the
        # FastAPI event loop isn't blocked while the lookups serialize.
        loaded = await asyncio.gather(
            *(
                asyncio.to_thread(builds.load_build, bid)
                for bid in request.scope.build_ids
            )
        )
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
