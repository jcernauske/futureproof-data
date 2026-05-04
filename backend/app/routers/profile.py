from fastapi import APIRouter

from app.models.api import ProfileRerollRequest
from app.services import profile

router = APIRouter()


@router.post("/")
async def create_profile():
    return profile.generate_name()


@router.post("/reroll")
async def reroll_profile(request: ProfileRerollRequest):
    return profile.reroll(request.current_name)
