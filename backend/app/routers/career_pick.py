"""FastAPI router for the /career-pick Ask-Gemma chip surface.

Two endpoints, both async:

- ``GET /career-pick/chips`` — deliver the chip set with the
  intent-mismatch heuristic already applied so the frontend is a dumb
  renderer.
- ``POST /career-pick/ask`` — resolve the canned prompt + call Gemma.
  Always 200 unless the chip_id is unknown (422) or the request body is
  malformed (422 from Pydantic). Gemma transport failures are swallowed
  into the deterministic fallback string.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.career_pick import (
    AskCareerPickRequest,
    AskCareerPickResponse,
    CareerPickChip,
)
from app.services import career_pick_qna

router = APIRouter(prefix="/career-pick", tags=["Career Pick"])


@router.get("/chips", response_model=list[CareerPickChip])
async def get_chips(
    cipcode: str = Query(..., description="CIP code, string format (e.g. '26.0101')"),
    major_text: str = Query(..., description="Raw major text the student typed"),
    soc_codes: list[str] = Query(
        default_factory=list,
        description="SOC codes currently rendered in tier cards",
    ),
) -> list[CareerPickChip]:
    return career_pick_qna.build_chip_list(
        cipcode=cipcode,
        major_text=major_text,
        soc_codes=soc_codes,
    )


@router.post("/ask", response_model=AskCareerPickResponse)
async def post_ask(request: AskCareerPickRequest) -> AskCareerPickResponse:
    try:
        return await career_pick_qna.ask(request=request, locale=request.locale)
    except ValueError as exc:
        # Unknown chip_id — Pydantic can't catch this since the id is a
        # free-form string in the request schema.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
