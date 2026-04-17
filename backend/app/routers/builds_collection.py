"""Collection-level builds endpoints (no `/build` prefix).

Hosts routes that target the *collection* of builds rather than a
specific build_id: list and compare. Lives outside `routers/builds.py`
because that router is mounted under `/build` (singular) and we need
clean `/builds/...` paths for these collection operations.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.models.api import CompareRequest
from app.services import builds

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
