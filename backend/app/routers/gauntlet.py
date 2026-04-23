from fastapi import APIRouter, HTTPException

from app import state
from app.models.api import RerollRequest, RescoreRequest, WrapupRequest
from app.services import boss_fights, skill_pool, stat_engine

router = APIRouter()


@router.post("/{build_id}/gauntlet")
async def run_gauntlet(build_id: str):
    build = state.get_build(build_id)
    if build is None:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")
    gauntlet = boss_fights.run_gauntlet(build.career)
    build.gauntlet = gauntlet
    state.update_build(build_id, build)
    return gauntlet


@router.post("/{build_id}/rescore")
async def rescore_build(build_id: str, request: RescoreRequest):
    build = state.get_build(build_id)
    if build is None:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")

    updated_career = stat_engine.recompute_for_sliders(
        career=build.career,
        original_effort=build.effort,
        new_effort=request.effort,
        new_loan_pct=request.loan_pct,
    )
    gauntlet = boss_fights.score_gauntlet(updated_career)

    return {
        "stats": updated_career.stats.model_dump(),
        "bosses": updated_career.bosses.model_dump(),
        "loan_pct": updated_career.loan_pct,
        "modeled_total_debt": updated_career.modeled_total_debt,
        "financed_dte": updated_career.financed_dte,
        "gauntlet": gauntlet.model_dump(),
    }


@router.post("/{build_id}/reroll")
async def reroll_fight(build_id: str, request: RerollRequest):
    build = state.get_build(build_id)
    if build is None:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")

    picks = [s for s in build.skill_pool if s.id in request.skill_ids]
    if not picks:
        raise HTTPException(status_code=400, detail="No valid skills selected")

    mutated_career = skill_pool.apply_skills(build.career, picks)
    new_fight = boss_fights.rescore_fight(mutated_career, request.boss_id)

    original_fight = next(
        (f for f in build.gauntlet.fights if f.boss == request.boss_id),
        None,
    )
    if original_fight:
        new_fight.rerolled = True
        new_fight.reroll_count = original_fight.reroll_count + 1
        new_fight.original_result = (
            original_fight.original_result or original_fight.result
        )
        new_fight.original_raw_score = (
            original_fight.original_raw_score or original_fight.raw_score
        )

        original_result = original_fight.original_result or original_fight.result
        original_narrative = original_fight.narrative or ""
        skill_titles = [s.title for s in picks]

        updated_narrative = await boss_fights.generate_reroll_commentary_async(
            mutated_career,
            new_fight,
            original_result,
            original_narrative,
            skill_titles,
        )
        new_fight.narrative = updated_narrative or original_narrative
        new_fight.applied_skill_titles = skill_titles

        build.gauntlet.fights = [
            new_fight if f.boss == request.boss_id else f
            for f in build.gauntlet.fights
        ]
        boss_fights.recompute_totals(build.gauntlet)

    build.career = mutated_career
    build.skills_crafted.extend(picks)
    state.update_build(build_id, build)

    return new_fight


@router.post("/{build_id}/wrapup")
async def fight_wrapup(build_id: str, request: WrapupRequest):
    build = state.get_build(build_id)
    if build is None:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")

    fight = next(
        (f for f in build.gauntlet.fights if f.boss == request.boss_id),
        None,
    )
    if fight is None:
        raise HTTPException(
            status_code=404, detail=f"Fight {request.boss_id} not found"
        )

    original_result = fight.original_result or fight.result
    narrative = await boss_fights.generate_wrapup_async(
        build.career,
        fight,
        original_result,
        request.all_skill_titles,
        request.all_narratives,
    )
    return {"narrative": narrative}
