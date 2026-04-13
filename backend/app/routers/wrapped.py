from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/{build_id}/wrapped")
async def get_wrapped(build_id: str):
    raise HTTPException(
        status_code=501,
        detail="Wrapped rendering not yet implemented. Ships with F6.",
    )
