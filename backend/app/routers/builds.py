import asyncio
import logging
from typing import cast

from fastapi import APIRouter, HTTPException, Request

from app import state
from app.models.api import BuildRequest, OutcomesRequest, TierRequest
from app.models.career import AppliedSkill, CareerOutcome, EffortLevel, SkillRec
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

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/outcomes")
async def compute_outcomes(request: OutcomesRequest):
    # PyIceberg metadata + scan is sync and can block the event loop for
    # seconds on a cold call. Offload to a thread so /health stays
    # responsive — otherwise Railway's liveness probe times out and
    # SIGKILLs the container mid-request.
    try:
        return await asyncio.to_thread(
            stat_engine.compute_pentagon,
            unitid=request.unitid,
            cipcode=request.cipcode,
            student_major=request.student_major,
            student_cip=request.student_cip,
            effort=request.effort,
            loan_pct=request.loan_pct,
            intent_keywords=request.intent_keywords or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/tier")
async def tier_outcomes(request: TierRequest, raw_request: Request):
    if await raw_request.is_disconnected():
        raise HTTPException(status_code=499, detail="client_disconnected")
    outcomes = [CareerOutcome.model_validate(o) for o in request.outcomes]
    tiers = career_tiering.tier_careers(
        outcomes,
        school_name=request.school_name,
        program_name=request.program_name,
        cipcode=request.cipcode,
        student_major_text=request.student_major_text or "",
        intent_keywords=request.intent_keywords,
    )
    return {
        label: [o.model_dump(mode="json") for o in careers]
        for label, careers in tiers.items()
    }


@router.post("")
async def create_build(request: BuildRequest):
    # Pull the selected career first. PyIceberg metadata + scan is sync
    # and can block the event loop for seconds on a cold call — offload
    # to a thread so /health stays responsive.
    try:
        career = await asyncio.to_thread(
            stat_engine.compute_one,
            unitid=request.unitid,
            cipcode=request.cipcode,
            soc_code=request.selected_soc,
            student_major=request.student_major,
            student_cip=request.student_cip,
            effort=cast(EffortLevel, request.effort),
            loan_pct=request.loan_pct,
            intent_keywords=request.intent_keywords or None,
            home_state=request.home_state,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if not career.program_name and request.cip_title:
        career.program_name = request.cip_title

    if (
        request.home_state
        and request.school_state
        and request.home_state != request.school_state
        and career.institution_control
        and career.institution_control.startswith("Public")
    ):
        career.is_out_of_state = True

    # Scoring is deterministic and cheap — stays on the event loop.
    gauntlet = boss_fights.score_gauntlet(career)
    branches = await asyncio.to_thread(branch_tree.get_branches, career.soc_code)

    # Fan out the eight Gemma-bound calls in a single gather. Each
    # coroutine owns its own semaphore acquisition via
    # ``gemma_client.generate_async``; ``return_exceptions=True`` keeps
    # one backend hiccup from taking down the whole build response.
    narrative_tasks = [
        boss_fights.narrate_one(career, fight) for fight in gauntlet.fights
    ]
    recs_task = skill_recs.generate_recs_async(career, gauntlet)
    pool_task = skill_pool.generate_pool_async(career, gauntlet)
    guidance_task = guidance.generate_guidance_async(
        career, gauntlet, branches
    )

    results = await asyncio.gather(
        *narrative_tasks,
        recs_task,
        pool_task,
        guidance_task,
        return_exceptions=True,
    )

    fight_count = len(gauntlet.fights)
    narrative_results = results[:fight_count]
    recs_result, pool_result, guidance_result = results[fight_count:]

    for fight, narrative_text in zip(gauntlet.fights, narrative_results):
        if isinstance(narrative_text, BaseException):
            logger.warning(
                "narrate_one raised for boss=%s: %s",
                fight.boss,
                narrative_text,
            )
            fight.narrative = boss_fights._fallback_narrative(fight)
        else:
            text = cast(str, narrative_text)
            fight.narrative = text or boss_fights._fallback_narrative(fight)

    recs: list[SkillRec]
    if isinstance(recs_result, BaseException):
        logger.warning("skill_recs raised: %s", recs_result)
        recs = skill_recs._fallback_recs(career)
    else:
        recs = cast("list[SkillRec]", recs_result)

    pool: list[AppliedSkill]
    if isinstance(pool_result, BaseException):
        logger.warning("skill_pool raised: %s", pool_result)
        pool = []
    else:
        pool = cast("list[AppliedSkill]", pool_result)

    narrative: str
    if isinstance(guidance_result, BaseException):
        logger.warning("guidance raised: %s", guidance_result)
        narrative = guidance._fallback_narrative(career, gauntlet)
    else:
        narrative = cast(str, guidance_result)

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
