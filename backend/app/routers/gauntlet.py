from fastapi import APIRouter, HTTPException

from app import state
from app.models.api import RerollRequest, WrapupRequest
from app.services import boss_fights, skill_pool

router = APIRouter()


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
            locale=build.locale,
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
        locale=build.locale,
    )
    return {"narrative": narrative}
