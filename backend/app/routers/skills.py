from fastapi import APIRouter, HTTPException

from app import state
from app.services import skill_pool, skill_recs

router = APIRouter()


@router.get("/{build_id}/skill-recs")
async def get_skill_recs(build_id: str):
    build = state.get_build(build_id)
    if build is None:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")
    return skill_recs.generate_recs(build.career, build.gauntlet)


@router.get("/{build_id}/skill-pool")
async def get_skill_pool(build_id: str):
    build = state.get_build(build_id)
    if build is None:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")
    return skill_pool.generate_pool(build.career, build.gauntlet)
