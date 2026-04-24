from fastapi import APIRouter, HTTPException

from app.models.api import CheckpointRequest
from app.services import sessions

router = APIRouter()


@router.get("")
async def get_session():
    result = sessions.load_session()
    if result is None:
        raise HTTPException(status_code=404, detail="No active session")
    return result


@router.post("/checkpoint")
async def save_checkpoint(request: CheckpointRequest):
    sessions.save_checkpoint(request)
    return {"status": "ok"}


@router.delete("")
async def delete_session():
    sessions.clear_session()
    return {"status": "ok"}
