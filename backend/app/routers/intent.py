from fastapi import APIRouter, HTTPException

from app.models.api import IntentConfirmRequest, IntentRequest
from app.services import intent

router = APIRouter()


@router.post("/")
async def resolve_intent(request: IntentRequest):
    try:
        return intent.resolve_intent(
            major_text=request.major_text,
            school_name=request.school_name,
            unitid=request.unitid,
            programs=request.programs,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/confirm")
async def confirm_intent(request: IntentConfirmRequest):
    intent.confirm_intent(
        matched_cip=request.matched_cip,
        matched_title=request.matched_title,
        major_text=request.major_text,
        unitid=request.unitid,
    )
    return {"cached": True}
