from fastapi import APIRouter, HTTPException

from app import state
from app.models.api import ChatRequest
from app.services import guidance, next_steps

router = APIRouter()


@router.post("/{build_id}/guidance")
async def generate_guidance(build_id: str):
    build = state.get_build(build_id)
    if build is None:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")
    narrative = guidance.generate_guidance(
        build.career, build.gauntlet, build.branches, locale=build.locale,
    )
    return {"narrative": narrative}


@router.post("/{build_id}/chat")
async def chat_with_context(build_id: str, request: ChatRequest):
    build = state.get_build(build_id)
    if build is None:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")
    effective_locale = request.locale or build.locale
    response = guidance.chat_with_context(
        career=build.career,
        gauntlet=build.gauntlet,
        branches=build.branches,
        skill_recs=build.skill_recs,
        conversation_history=request.history,
        user_question=request.message,
        locale=effective_locale,
    )
    return {"response": response}


@router.post("/{build_id}/next-steps")
async def generate_next_steps(build_id: str):
    build = state.get_build(build_id)
    if build is None:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")
    checklist = next_steps.generate_next_steps(build)
    return {"checklist": checklist}
