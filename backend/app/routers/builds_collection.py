"""Collection-level builds endpoints (no `/build` prefix).

Hosts routes that target the *collection* of builds rather than a
specific build_id: list and compare. Lives outside `routers/builds.py`
because that router is mounted under `/build` (singular) and we need
clean `/builds/...` paths for these collection operations.
"""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.models.api import CompareRequest
from app.services import builds
from app.services.guidance import (
    generate_compare_pivotal_async,
    generate_compare_pros_cons_async,
    generate_compare_summary_async,
    generate_money_insight_async,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/builds")
async def list_builds(
    profile_name: str | None = Query(default=None, max_length=200),
) -> dict[str, list[dict[str, Any]]]:
    summaries = builds.list_builds(profile_name=profile_name)
    return {"builds": [s.model_dump(mode="json") for s in summaries]}


@router.post("/builds/compare")
async def compare_builds(request: CompareRequest) -> dict[str, Any]:
    try:
        return builds.compare_builds(request.build_ids)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/builds/compare-insights")
async def compare_insights(request: CompareRequest) -> dict[str, Any]:
    """Generate Gemma insights for the Party Select comparison screen.

    Fires both Gemma calls in parallel. Either can fail independently —
    the frontend renders whatever arrives.
    """
    try:
        loaded = [builds.load_build(bid) for bid in request.build_ids]
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    results = await asyncio.gather(
        generate_money_insight_async(loaded),
        generate_compare_summary_async(loaded),
        generate_compare_pros_cons_async(loaded),
        generate_compare_pivotal_async(loaded),
        return_exceptions=True,
    )

    for i, r in enumerate(results):
        if isinstance(r, BaseException):
            logger.error("compare-insights task %d failed: %s", i, r, exc_info=r)

    money_insight = results[0] if not isinstance(results[0], BaseException) else None
    compare_summary = results[1] if not isinstance(results[1], BaseException) else None
    pros_cons = results[2] if not isinstance(results[2], BaseException) else None
    pivotal = results[3] if not isinstance(results[3], BaseException) else None

    return {
        "money_insight": money_insight,
        "compare_summary": compare_summary,
        "pros_cons": pros_cons,
        "pivotal": pivotal,
    }
