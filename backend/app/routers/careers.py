"""Career-anchored HTTP endpoints.

Two thin endpoints over ``app.services.schools_for_career``. Spec B will
later add ``POST /careers/search-from-intent`` to this router (see
``docs/specs/feature-career-search.md``).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import ValidationError

from app.models.career import (
    AnchorBuild,
    CareerDescription,
    ConfidenceTier,
    SchoolsForCareerResponse,
)
from app.services import career_description as career_description_service
from app.services.career_description import CareerDescriptionUnavailable
from app.services.locale import AppLocale, normalize_locale
from app.services.schools_for_career import rank_schools_for_career

logger = logging.getLogger(__name__)

router = APIRouter()

_CIP_PATTERN = r"^\d{2}\.\d{2,4}$"
_SOC_PATTERN = r"^\d{2}-\d{4}$"

# Opaque error codes the MCP handler returns. Mapped to user-friendly
# 502 detail strings here so DuckDB / contract internals don't leak.
_OPAQUE_UPSTREAM_CODES: frozenset[str] = frozenset({"leaderboard_query_failed"})


def _maybe_anchor(unitid: int | None, cipcode: str | None) -> AnchorBuild | None:
    if unitid is None or cipcode is None:
        return None
    return AnchorBuild(unitid=unitid, cipcode=cipcode)


def _dispatch(**kwargs: object) -> SchoolsForCareerResponse:
    """Call the service with explicit failure mapping.

    - `ValidationError` (Pydantic v2 inherits from `ValueError` today, but
      that may change in v3) → 502 with opaque detail.
    - Opaque upstream codes (e.g. ``leaderboard_query_failed``) → 502.
    - Other ``ValueError`` (validation messages) → 422 with the raw message.
    """
    try:
        return rank_schools_for_career(**kwargs)  # type: ignore[arg-type]
    except ValidationError as exc:
        logger.exception("schools_for_career response failed validation: %s", exc)
        raise HTTPException(
            status_code=502, detail="upstream_contract_violation"
        ) from exc
    except ValueError as exc:
        message = str(exc)
        if message in _OPAQUE_UPSTREAM_CODES:
            raise HTTPException(status_code=502, detail=message) from exc
        raise HTTPException(status_code=422, detail=message) from exc


@router.get(
    "/careers/{soc_code}/schools",
    response_model=SchoolsForCareerResponse,
)
def get_schools_for_career_by_soc(
    soc_code: str = Path(..., pattern=_SOC_PATTERN),
    limit: int = Query(10, ge=1, le=25),
    min_confidence: ConfidenceTier = Query("medium"),
    min_program_confidence: ConfidenceTier = Query("low"),
    state_abbr: str | None = Query(None, min_length=2, max_length=2),
    home_state: str | None = Query(None, min_length=2, max_length=2),
    build_unitid: int | None = Query(None),
    build_cipcode: str | None = Query(None, pattern=_CIP_PATTERN),
    anchor_stat_ern: int | None = Query(None, ge=0, le=10),
    anchor_stat_roi: int | None = Query(None, ge=0, le=10),
) -> SchoolsForCareerResponse:
    """`by_soc` mode: all programs producing this SOC, ranked nationally."""
    anchor = _maybe_anchor(build_unitid, build_cipcode)
    return _dispatch(
        mode="by_soc",
        soc_code=soc_code,
        limit=limit,
        min_confidence=min_confidence,
        min_program_confidence=min_program_confidence,
        state_abbr=state_abbr,
        home_state=home_state,
        anchor=anchor,
        anchor_stat_ern=anchor_stat_ern,
        anchor_stat_roi=anchor_stat_roi,
    )


@router.get(
    "/careers/{soc_code}/description",
    response_model=CareerDescription,
)
async def get_career_description(
    soc_code: str = Path(..., pattern=_SOC_PATTERN),
    occupation_title: str = Query(
        ...,
        min_length=1,
        max_length=200,
        description="Display title for the occupation; required for the Tier C "
        "fallback prompt when O*NET coverage is missing.",
    ),
    locale: str | None = Query(
        default=None,
        description="Two-letter app locale (en / es / ar). Selects the Gemma "
        "output language and participates in the cache key so a new language "
        "fetches fresh copy.",
    ),
) -> CareerDescription:
    """Return a plain-English career description for a SOC code.

    On cold cache: pre-fetch O*NET activity / BLS description data via
    ``get_task_breakdown``, pick the appropriate anchor tier (A/B/C),
    call Gemma once, validate against the PDF voice rules, and cache.

    On warm cache: return immediately.

    Maps service errors:
        ``CareerDescriptionUnavailable`` → 502 ``career_description_unavailable``
        Path regex failure (malformed SOC) → 422 (FastAPI built-in)
    """
    resolved: AppLocale = normalize_locale(locale)
    try:
        return await career_description_service.get_or_generate(
            soc_code, occupation_title, locale=resolved,
        )
    except CareerDescriptionUnavailable as exc:
        logger.info(
            "career_description unavailable for soc=%s: %s", soc_code, exc,
        )
        raise HTTPException(
            status_code=502, detail="career_description_unavailable",
        ) from exc


@router.get(
    "/majors/{cipcode}/schools/for-career/{soc_code}",
    response_model=SchoolsForCareerResponse,
)
def get_schools_by_cip_and_soc(
    cipcode: str = Path(..., pattern=_CIP_PATTERN),
    soc_code: str = Path(..., pattern=_SOC_PATTERN),
    limit: int = Query(10, ge=1, le=25),
    min_confidence: ConfidenceTier = Query("medium"),
    min_program_confidence: ConfidenceTier = Query("low"),
    state_abbr: str | None = Query(None, min_length=2, max_length=2),
    home_state: str | None = Query(None, min_length=2, max_length=2),
    build_unitid: int | None = Query(None),
    build_cipcode: str | None = Query(None, pattern=_CIP_PATTERN),
    anchor_stat_ern: int | None = Query(None, ge=0, le=10),
    anchor_stat_roi: int | None = Query(None, ge=0, le=10),
) -> SchoolsForCareerResponse:
    """`by_cip_and_soc` mode: programs at this CIP that produce this SOC."""
    anchor = _maybe_anchor(build_unitid, build_cipcode)
    return _dispatch(
        mode="by_cip_and_soc",
        soc_code=soc_code,
        cipcode=cipcode,
        limit=limit,
        min_confidence=min_confidence,
        min_program_confidence=min_program_confidence,
        state_abbr=state_abbr,
        home_state=home_state,
        anchor=anchor,
        anchor_stat_ern=anchor_stat_ern,
        anchor_stat_roi=anchor_stat_roi,
    )
