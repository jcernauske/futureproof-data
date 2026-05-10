import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app import state
from app.models.api import (
    BuildRequest,
    OutcomesRequest,
    PrefetchRequest,
    RebuildRequest,
    TierRequest,
)
from app.models.career import (
    AppliedSkill,
    CareerBranch,
    CareerDescription,
    CareerOutcome,
    EffortLevel,
    GauntletResult,
    SkillRec,
)
from app.services import (
    boss_fights,
    branch_tree,
    builds,
    career_description,
    career_tiering,
    gemma_client,
    guidance,
    prefetch,
    skill_pool,
    skill_recs,
    stat_engine,
)
from app.services._sse import sse_event
from app.services.locale import AppLocale

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/prefetch", status_code=202)
async def start_prefetch(request: PrefetchRequest):
    """Speculatively start stat engine + branches + career description.

    Called from /set-your-course when the student clicks a career card.
    The build stream consumes the result if it's ready by the time
    ``POST /build/stream`` fires.
    """
    key = prefetch.start(
        unitid=request.unitid,
        cipcode=request.cipcode,
        soc_code=request.soc_code,
        effort=request.effort,
        loan_pct=request.loan_pct,
        student_major=request.student_major,
        student_cip=request.student_cip,
        intent_keywords=request.intent_keywords or None,
        home_state=request.home_state,
        occupation_title=request.occupation_title,
    )
    return {"status": "started", "key": list(key)}



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
            home_state=request.home_state,
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
) -> tuple[list[SkillRec], list[AppliedSkill], str, CareerDescription | None]:
    """Fan out Gemma-bound calls (narratives + recs + pool + guidance +
    career description).

    Shared by ``create_build`` and ``rebuild_with_sliders``. The career
    description shares the fanout's effective wait budget so we don't
    layer a separate timeout on top — failure is non-fatal.

    Returns (recs, pool, guidance_narrative, career_description_or_None).
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
    desc_task = career_description.get_or_generate(
        career.soc_code, career.occupation_title,
    )

    results = await asyncio.gather(
        *narrative_tasks,
        recs_task,
        pool_task,
        guidance_task,
        desc_task,
        return_exceptions=True,
    )

    fight_count = len(gauntlet.fights)
    narrative_results = results[:fight_count]
    recs_result, pool_result, guidance_result, desc_result = results[fight_count:]

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

    desc: CareerDescription | None
    if isinstance(desc_result, BaseException):
        if not isinstance(
            desc_result, career_description.CareerDescriptionUnavailable,
        ):
            logger.warning(
                "career_description raised for %s: %r",
                career.soc_code,
                desc_result,
            )
        desc = None
    else:
        desc = cast("CareerDescription | None", desc_result)

    return recs, pool, narrative, desc


@router.post("")
async def create_build(request: BuildRequest):
    try:
        career_task = asyncio.to_thread(
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
        branches_task = asyncio.to_thread(
            branch_tree.get_branches, request.selected_soc,
        )
        career, branches_list = await asyncio.gather(
            career_task, branches_task,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except LookupError as exc:
        logger.warning("Career lookup failed: %s", exc)
        raise HTTPException(
            status_code=404,
            detail=(
                "We don't have enough data for that career at this school."
                " Try a different career or school."
            ),
        )

    if not career.program_name and request.cip_title:
        career.program_name = request.cip_title
    career = stat_engine.apply_published_cost_override(
        career,
        request.published_cost_4yr,
        loan_pct=request.loan_pct,
    )

    if (
        request.home_state
        and request.school_state
        and request.home_state != request.school_state
        and career.institution_control
        and career.institution_control.startswith("Public")
    ):
        career.is_out_of_state = True

    gauntlet = boss_fights.score_gauntlet(career)

    recs, pool, narrative, desc = await _gemma_fanout(
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
    if desc is not None:
        build.career_description = desc
    state.store_build(build)
    builds.save_build(build)
    return build


@router.post("/stream")
async def create_build_stream(request: BuildRequest) -> StreamingResponse:
    return StreamingResponse(
        _build_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _build_stream(request: BuildRequest) -> AsyncIterator[str]:
    # Try to consume a prefetch result from /set-your-course.
    pf_key = prefetch.make_key(
        request.unitid, request.cipcode, request.selected_soc,
        request.effort, request.loan_pct, request.student_major,
        request.student_cip, request.home_state,
    )
    pf_result = await prefetch.consume(pf_key)

    if pf_result and pf_result.career:
        logger.info(
            "build_stream using prefetched result for soc=%s",
            request.selected_soc,
        )
        career: CareerOutcome = pf_result.career
        branches_list: list[CareerBranch] = pf_result.branches
    else:
        career_task = asyncio.to_thread(
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
        branches_task = asyncio.to_thread(
            branch_tree.get_branches, request.selected_soc,
        )

        try:
            career, branches_list = await asyncio.gather(
                career_task, branches_task,
            )
        except ValueError as exc:
            yield sse_event("error", {"detail": str(exc)})
            return
        except LookupError:
            yield sse_event(
                "error",
                {"detail": "We don't have enough data for that career at this school."},
            )
            return

    if not career.program_name and request.cip_title:
        career.program_name = request.cip_title
    career = stat_engine.apply_published_cost_override(
        career,
        request.published_cost_4yr,
        loan_pct=request.loan_pct,
    )
    if (
        request.home_state
        and request.school_state
        and request.home_state != request.school_state
        and career.institution_control
        and career.institution_control.startswith("Public")
    ):
        career.is_out_of_state = True

    gauntlet = boss_fights.score_gauntlet(career)

    skeleton = builds.build_from_parts(
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
        skill_recs=[],
        guidance="",
        skill_pool=[],
        profile_name=request.profile_name,
        home_state=request.home_state,
        animal_emoji=request.animal_emoji,
        locale=request.locale,
    )

    # The frontend renders /my-build as soon as this skeleton event
    # arrives. Persist it before yielding so immediate Ask Gemma actions
    # can resolve the build_id while the slower Gemma fanout continues.
    state.store_build(skeleton)
    await asyncio.to_thread(builds.save_build, skeleton)

    yield sse_event("skeleton", skeleton.model_dump(mode="json"))

    locale = request.locale or "en"

    async def _narrate(fight: Any) -> tuple[str, dict[str, str]]:
        try:
            text = await boss_fights.narrate_one(career, fight, locale=locale)
            fight.narrative = text or boss_fights._fallback_narrative(fight)
        except Exception:
            fight.narrative = boss_fights._fallback_narrative(fight)
        return ("boss_narrative", {"boss_id": fight.boss, "narrative": fight.narrative})

    async def _recs() -> tuple[str, list[dict[str, Any]]]:
        try:
            r = await skill_recs.generate_recs_async(career, gauntlet, locale=locale)
        except Exception:
            r = skill_recs._fallback_recs(career)
        return ("skill_recs", [rec.model_dump(mode="json") for rec in r])

    async def _pool() -> tuple[str, list[dict[str, Any]]]:
        try:
            p = await skill_pool.generate_pool_async(career, gauntlet, locale=locale)
        except Exception:
            p = []
        return ("skill_pool", [s.model_dump(mode="json") for s in p])

    async def _guide() -> tuple[str, dict[str, str]]:
        try:
            g = await guidance.generate_guidance_async(
                career, gauntlet, branches_list, locale=locale,
            )
        except Exception:
            g = guidance._fallback_narrative(career, gauntlet)
        return ("guidance", {"narrative": g})

    async def _desc() -> tuple[str, dict[str, Any] | None]:
        # Eager career description. Failure → None; the lazy PDF
        # fallback path still runs server-side on export. We do NOT
        # yield this as its own SSE event (out of scope per §4); the
        # final-build commit picks it up via the captured result below.
        if not gemma_client.runtime_profile().eager_career_description:
            return ("_career_description", None)
        try:
            d = await career_description.get_or_generate(
                career.soc_code, career.occupation_title,
            )
        except career_description.CareerDescriptionUnavailable:
            return ("_career_description", None)
        except Exception as exc:
            logger.warning(
                "stream career_description raised for %s: %r",
                career.soc_code, exc,
            )
            return ("_career_description", None)
        return ("_career_description", d.model_dump(mode="json"))

    profile = gemma_client.runtime_profile()

    recs_result: list[SkillRec] = []
    pool_result: list[AppliedSkill] = []
    guidance_result = ""
    desc_result: CareerDescription | None = None

    try:
        if profile.sequential_build_stream:
            # Local compact Ollama models serialize most short prose calls,
            # but the skill pool is the long pole and students need those
            # skills. Run it in its own lane while visible notes continue
            # sequentially in the other lane. Full/26B keeps the richer
            # as_completed fanout below.
            pool_task = asyncio.create_task(_pool())
            pool_emitted = False

            async def _drain_pool_if_ready() -> str | None:
                nonlocal pool_emitted, pool_result
                if pool_emitted or not pool_task.done():
                    return None
                event_name, event_data = await pool_task
                assert event_name == "skill_pool"
                assert event_data is not None
                pool_result = [
                    AppliedSkill.model_validate(s) for s in event_data
                ]
                pool_emitted = True
                return sse_event(event_name, event_data)

            steps = [
                *[(lambda fight=f: _narrate(fight)) for f in gauntlet.fights],
                _recs,
                _guide,
                _desc,
            ]
            for step in steps:
                event_name, event_data = await step()

                if event_name == "_career_description":
                    if event_data is not None:
                        desc_result = CareerDescription.model_validate(event_data)
                    continue

                assert event_data is not None
                yield sse_event(event_name, event_data)

                if event_name == "skill_recs":
                    recs_result = [SkillRec.model_validate(r) for r in event_data]
                elif event_name == "skill_pool":
                    pool_result = [
                        AppliedSkill.model_validate(s) for s in event_data
                    ]
                elif event_name == "guidance":
                    guidance_result = cast("dict[str, str]", event_data)["narrative"]

                pool_event = await _drain_pool_if_ready()
                if pool_event is not None:
                    yield pool_event

            if not pool_emitted:
                event_name, event_data = await pool_task
                assert event_name == "skill_pool"
                assert event_data is not None
                yield sse_event(event_name, event_data)
                pool_result = [
                    AppliedSkill.model_validate(s) for s in event_data
                ]
        else:
            tasks = [
                *[asyncio.create_task(_narrate(f)) for f in gauntlet.fights],
                asyncio.create_task(_recs()),
                asyncio.create_task(_pool()),
                asyncio.create_task(_guide()),
                asyncio.create_task(_desc()),
            ]
            for coro in asyncio.as_completed(tasks):
                event_name, event_data = await coro

                if event_name == "_career_description":
                    # Internal-only: never yielded as SSE in this round.
                    if event_data is not None:
                        desc_result = CareerDescription.model_validate(event_data)
                    continue

                # event_data is non-None for every other branch by construction
                # of the corresponding _narrate / _recs / _pool / _guide helpers.
                assert event_data is not None
                yield sse_event(event_name, event_data)

                if event_name == "skill_recs":
                    recs_result = [SkillRec.model_validate(r) for r in event_data]
                elif event_name == "skill_pool":
                    pool_result = [
                        AppliedSkill.model_validate(s) for s in event_data
                    ]
                elif event_name == "guidance":
                    guidance_result = cast("dict[str, str]", event_data)["narrative"]
    except (asyncio.CancelledError, GeneratorExit):
        if "pool_task" in locals() and not pool_task.done():
            pool_task.cancel()
        if "tasks" in locals():
            for t in tasks:
                t.cancel()
        return

    final_build = skeleton.model_copy(update={
        "skill_recs": recs_result,
        "skill_pool": pool_result,
        "guidance": guidance_result,
        "career_description": desc_result,
    })
    state.store_build(final_build)
    builds.save_build(final_build)

    yield sse_event("done", {"build_id": final_build.build_id})


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


@router.delete("/{build_id}")
async def delete_build(build_id: str):
    builds.delete_build(build_id)
    state.remove_build(build_id)
    return {"deleted": build_id}


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

    recs, pool, narrative, desc = await _gemma_fanout(
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
    # Reuse the parent's description if the rebuild's eager fetch failed —
    # SOC is identical between original and rebuild, so the description
    # is interchangeable. Keeps PDF exports of slider-rebuilds populated.
    build.career_description = desc or original.career_description
    state.store_build(build)
    builds.save_build(build)
    return build


# Compare endpoint moved to `routers/builds_collection.py` so it lives
# at the clean `POST /builds/compare` path instead of `POST /build/s/compare`.
