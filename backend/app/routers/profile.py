from fastapi import APIRouter

from app.models.api import ProfileLookupRequest, ProfileRerollRequest
from app.services import profile

router = APIRouter()


@router.post("/")
async def create_profile():
    return profile.generate_name()


@router.post("/reroll")
async def reroll_profile(request: ProfileRerollRequest):
    return profile.reroll(request.current_name)


@router.post("/lookup")
async def lookup_profile(request: ProfileLookupRequest):
    return profile.lookup(request.name_query)
