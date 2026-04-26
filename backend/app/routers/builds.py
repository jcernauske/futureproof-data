import asyncio
import logging
from typing import cast

from fastapi import APIRouter, HTTPException, Request

from app import state
from app.models.api import (
    BuildRequest,
    OutcomesRequest,
    RebuildRequest,
    TierRequest,
)
from app.models.career import (
    AppliedSkill,
    CareerBranch,
    CareerOutcome,
    EffortLevel,
    GauntletResult,
    SkillRec,
)
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
from app.services.locale import AppLocale

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


async def _gemma_fanout(
    career: CareerOutcome,
    gauntlet: GauntletResult,
    branches: list[CareerBranch],
    locale: AppLocale = "en",
) -> tuple[list[SkillRec], list[AppliedSkill], str]:
    """Fan out Gemma-bound calls (narratives + recs + pool + guidance).

    Shared by ``create_build`` and ``rebuild_with_sliders``.
    Returns (recs, pool, guidance_narrative).
    """
    narrative_tasks = [
        boss_fights.narrate_one(career, fight, locale=locale)
        for fight in gauntlet.fights
    ]
    recs_task = skill_recs.generate_recs_async(career, gauntlet, locale=locale)
    pool_task = skill_pool.generate_pool_async(career, gauntlet, locale=locale)
    guidance_task = guidance.generate_guidance_async(
        career, gauntlet, branches, locale=locale,
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

    return recs, pool, narrative


@router.post("")
async def create_build(request: BuildRequest):
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
        logger.warning("Career lookup failed: %s", exc)
        raise HTTPException(
            status_code=404,
            detail="We don't have enough data for that career at this school. Try a different career or school.",
        )

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

    gauntlet = boss_fights.score_gauntlet(career)
    branches_list = await asyncio.to_thread(
        branch_tree.get_branches, career.soc_code
    )

    recs, pool, narrative = await _gemma_fanout(
        career, gauntlet, branches_list, locale=request.locale,
    )

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
        branches=branches_list,
        skill_recs=recs,
        guidance=narrative,
        skill_pool=pool,
        profile_name=request.profile_name,
        home_state=request.home_state,
        animal_emoji=request.animal_emoji,
        locale=request.locale,
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


@router.post("/{build_id}/rebuild")
async def rebuild_with_sliders(build_id: str, request: RebuildRequest):
    original = state.get_build(build_id)
    if original is None:
        raise HTTPException(
            status_code=404, detail=f"Build {build_id} not found"
        )

    career = stat_engine.recompute_for_sliders(
        career=original.career,
        original_effort=original.effort,
        new_effort=cast(EffortLevel, request.effort),
        new_loan_pct=request.loan_pct,
    )
    gauntlet = boss_fights.score_gauntlet(career)

    recs, pool, narrative = await _gemma_fanout(
        career, gauntlet, original.branches, locale=original.locale,
    )

    build = builds.build_from_parts(
        school_name=original.school_name,
        unitid=original.unitid,
        major_text=original.major_text,
        cipcode=original.cipcode,
        program_name=original.program_name,
        effort=request.effort,
        loan_pct=request.loan_pct,
        career=career,
        gauntlet=gauntlet,
        branches=original.branches,
        skill_recs=recs,
        guidance=narrative,
        skill_pool=pool,
        profile_name=original.profile_name,
        parent_build_id=original.build_id,
        home_state=original.home_state,
        animal_emoji=original.animal_emoji,
        locale=original.locale,
    )
    state.store_build(build)
    builds.save_build(build)
    return build


# Compare endpoint moved to `routers/builds_collection.py` so it lives
# at the clean `POST /builds/compare` path instead of `POST /build/s/compare`.
