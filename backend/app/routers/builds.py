from fastapi import APIRouter, HTTPException

from app import state
from app.models.api import BuildRequest, OutcomesRequest, TierRequest
from app.models.career import CareerOutcome
from app.services import (
    boss_fights,
    branch_tree,
    builds,
    career_tiering,
    guidance,
    skill_pool,
    skill_recs,
    stat_engine,
)

router = APIRouter()


@router.post("/outcomes")
async def compute_outcomes(request: OutcomesRequest):
    try:
        return stat_engine.compute_pentagon(
            unitid=request.unitid,
            cipcode=request.cipcode,
            student_major=request.student_major,
            effort=request.effort,
            loan_pct=request.loan_pct,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/tier")
async def tier_outcomes(request: TierRequest):
    outcomes = [CareerOutcome.model_validate(o) for o in request.outcomes]
    tiers = career_tiering.tier_careers(
        outcomes,
        school_name=request.school_name,
        program_name=request.program_name,
        cipcode=request.cipcode,
    )
    return {
        label: [o.model_dump(mode="json") for o in careers]
        for label, careers in tiers.items()
    }


@router.post("")
async def create_build(request: BuildRequest):
    try:
        outcomes = stat_engine.compute_pentagon(
            unitid=request.unitid,
            cipcode=request.cipcode,
            student_major=request.student_major,
            effort=request.effort,
            loan_pct=request.loan_pct,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    career = next(
        (o for o in outcomes if o.soc_code == request.selected_soc),
        None,
    )
    if career is None:
        raise HTTPException(
            status_code=404,
            detail=f"SOC {request.selected_soc} not found in outcomes",
        )

    gauntlet = boss_fights.run_gauntlet(career)
    branches = branch_tree.get_branches(career.soc_code)
    recs = skill_recs.generate_recs(career, gauntlet)
    pool = skill_pool.generate_pool(career, gauntlet)
    narrative = guidance.generate_guidance(career, gauntlet, branches)

    build = builds.build_from_parts(
        school_name=request.school_name,
        unitid=request.unitid,
        major_text=request.major_text,
        cipcode=request.cipcode,
        program_name=request.cip_title,
        effort=request.effort,
        loan_pct=request.loan_pct,
        career=career,
        gauntlet=gauntlet,
        branches=branches,
        skill_recs=recs,
        guidance=narrative,
        skill_pool=pool,
        profile_name=request.profile_name,
    )
    state.store_build(build)
    builds.save_build(build)
    return build


@router.post("/{build_id}/save")
async def save_build(build_id: str):
    build = state.get_build(build_id)
    if build is None:
        try:
            build = builds.load_build(build_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Build {build_id} not found")
    builds.save_build(build)
    return {"build_id": build.build_id}


@router.get("/{build_id}")
async def get_build(build_id: str):
    build = state.get_build(build_id)
    if build is not None:
        return build
    try:
        build = builds.load_build(build_id)
        state.store_build(build)
        return build
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")


# Compare endpoint moved to `routers/builds_collection.py` so it lives
# at the clean `POST /builds/compare` path instead of `POST /build/s/compare`.
