from fastapi import APIRouter, HTTPException, Query

from app import state
from app.services import builds, report_gen

router = APIRouter()


@router.get("/build/{build_id}/report")
async def get_report(build_id: str):
    build = state.get_build(build_id)
    if build is None:
        try:
            build = builds.load_build(build_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Build {build_id} not found")
    path = report_gen.generate_build_report(build)
    return {"markdown": path.read_text(encoding="utf-8")}


@router.get("/builds/compare/report")
async def get_comparison_report(build_ids: list[str] = Query(...)):
    try:
        comparison = builds.compare_builds(build_ids)
        full_builds = [builds.load_build(bid) for bid in build_ids]
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    path = report_gen.generate_comparison_report(comparison, full_builds)
    return {"markdown": path.read_text(encoding="utf-8")}
