from fastapi import APIRouter, Query

from app.services import school_lookup

router = APIRouter()


@router.get("/")
async def search_schools(q: str = Query(..., min_length=1)):
    return school_lookup.search_schools(q)


@router.get("/{unitid}/programs")
async def get_programs(unitid: int):
    return school_lookup.get_programs(unitid)
