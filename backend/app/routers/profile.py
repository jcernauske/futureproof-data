from fastapi import APIRouter

from app.models.api import ProfileCreateRequest, ProfileRerollRequest
from app.services import profile

router = APIRouter()


@router.post("")
async def create_profile(request: ProfileCreateRequest | None = None):
    # Body is optional — pre-locale clients still POST an empty payload.
    locale = request.locale if request else None
    return profile.generate_name(locale=locale)


@router.post("/reroll")
async def reroll_profile(request: ProfileRerollRequest):
    return profile.reroll(request.current_name, locale=request.locale)
