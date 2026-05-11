"""PDF Report Exports — FastAPI router.

Two endpoints (see docs/specs/feature-pdf-report-exports.md §4):
- POST /build/{build_id}/pdf       → 2-page My Build PDF
- POST /builds/compare/pdf         → 1-page Comparison PDF

Bytes stream back via ``Response(content=bytes, media_type="application/pdf")``
— precedent: ``backend/app/routers/wrapped.py:152``. Never streams; bytes
are fully materialized in memory before send (PDFs are tens of KB).

Render failures bubble out of pdf_export as exceptions and are caught
here, re-raised as ``HTTPException(500)`` so they flow through
``CORSMiddleware`` (precedent: ``wrapped.py:92-103``).
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Response

from app import state
from app.models.api import (
    ExportBuildPdfRequest,
    ExportComparisonPdfRequest,
)
from app.models.career import Build
from app.services import builds as builds_service
from app.services import career_description, pdf_export, pdf_questions
from app.services.career_description import CareerDescriptionUnavailable

logger = logging.getLogger(__name__)

# Empty prefix matches builds_collection.router precedent. Tag is "PDF"
# capitalized per genai-architect / fp-architect §5 R1.
router = APIRouter(prefix="", tags=["PDF"])


def _load_build_or_404(build_id: str) -> Build:
    """Resolve a build_id to an in-memory Build, raising 404 if missing.

    Mirrors wrapped.py's _load_build_or_404 pattern: try the in-process
    state cache first, fall back to disk-backed builds_service.
    """
    build = state.get_build(build_id)
    if build is not None:
        return build
    try:
        build = builds_service.load_build(build_id)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Build {build_id} not found",
        ) from exc
    state.store_build(build)
    return build


_FILENAME_SAFE = re.compile(r"[^a-z0-9]+")


def _slug(s: str) -> str:
    return _FILENAME_SAFE.sub("-", s.lower()).strip("-") or "x"


def _build_filename(build: Build) -> str:
    school = _slug(build.school_name)[:32]
    major = _slug(build.career.program_name or build.major_text)[:32]
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"futureproof-{school}-{major}-{today}.pdf"


def _comparison_filename(builds: list[Build]) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    major = _slug(builds[0].career.program_name or builds[0].major_text)[:32]
    return f"futureproof-compare-{major}-{len(builds)}schools-{today}.pdf"


@router.post("/build/{build_id}/pdf")
async def export_build_pdf(
    build_id: str,
    body: ExportBuildPdfRequest,
) -> Response:
    """Render the 2-page My Build PDF and return application/pdf bytes."""
    build = _load_build_or_404(build_id)

    # Lazy fallback: if the eager spawn-time generation didn't populate
    # career_description (older serialized build, or eager fetch failed),
    # try once more here within a 12s budget. Persist back via the
    # canonical state.update_build path so a subsequent export skips
    # this call entirely. Failure is non-fatal — PDF still renders, the
    # "About this career" section is silently omitted.
    if build.career_description is None:
        try:
            desc = await asyncio.wait_for(
                career_description.get_or_generate(
                    build.career.soc_code, build.career.occupation_title,
                ),
                timeout=12.0,
            )
            build.career_description = desc
            state.update_build(build.build_id, build)
        except (CareerDescriptionUnavailable, asyncio.TimeoutError) as exc:
            logger.info(
                "lazy career_description fetch failed for build=%s soc=%s: %s",
                build_id, build.career.soc_code, exc,
            )
        except Exception as exc:
            logger.warning(
                "lazy career_description unexpected error for build=%s: %r",
                build_id, exc,
            )

    # Resolve audience questions BEFORE rendering. The PDF service stays
    # pure-sync; Gemma calls happen here so the router's async context
    # holds them. generate_audience_questions never raises — it returns
    # a non-empty AudienceQuestions on every code path.
    audience_questions = await pdf_questions.generate_audience_questions(build)

    try:
        # ReportLab rendering is CPU-bound and synchronous. Run it in a
        # worker thread so it doesn't block the FastAPI event loop while
        # other requests are in flight (staff-engineer P1 fix).
        pdf_bytes = await asyncio.to_thread(
            pdf_export.generate_build_pdf,
            build,
            student_name=body.student_name,
            audience_questions=audience_questions,
        )
    except Exception as exc:
        logger.exception("PDF render failed for build %s", build_id)
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation failed: {type(exc).__name__}",
        ) from exc

    filename = _build_filename(build)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/builds/compare/pdf")
async def export_comparison_pdf(
    body: ExportComparisonPdfRequest,
) -> Response:
    """Render the multi-page Comparison PDF and return application/pdf bytes.

    Validation order:
    1. Pydantic enforces 2 ≤ len(build_ids) ≤ 4.
    2. Each build_id must resolve (404 on first missing).

    Cross-major comparisons are SUPPORTED — the in-app CompareView shows
    them, the PDF matches that contract. The PDF title falls back to
    "Career comparison" when majors differ.
    """
    builds: list[Build] = [_load_build_or_404(bid) for bid in body.build_ids]

    try:
        pdf_bytes = await asyncio.to_thread(
            pdf_export.generate_comparison_pdf, builds,
        )
    except ValueError as exc:
        # Should be unreachable given the validation above, but kept as a
        # safety net so downstream contract violations surface as 400, not 500.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Comparison PDF render failed for ids=%s", body.build_ids)
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation failed: {type(exc).__name__}",
        ) from exc

    filename = _comparison_filename(builds)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
