import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.routers import (
    ask_gemma_router,
    branches,
    builds,
    builds_collection,
    career_pick,
    careers,
    gauntlet,
    guidance_router,
    health,
    pdf_export,
    profile,
    schools,
    sessions,
    set_your_course,
    skills,
    wrapped,
)

DEFAULT_DEV_ORIGINS = "http://localhost:5173,http://localhost:4173"


def _parse_cors_origins() -> list[str]:
    """Parse the CORS allowlist env var. Empty/whitespace-only values fall
    back to the dev defaults so a stray ``CORS_ALLOWED_ORIGINS=`` in a
    Railway env doesn't silently deny every preflight (audit-flagged
    demo-killer shape — see spec §2 Decision #3).
    """
    raw = os.environ.get("CORS_ALLOWED_ORIGINS", DEFAULT_DEV_ORIGINS).strip()
    if not raw:
        raw = DEFAULT_DEV_ORIGINS
    parsed = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if not parsed:
        # raw was non-empty but every entry stripped to empty (e.g. ",,")
        # — log and fall back so the app still talks to local dev.
        logging.getLogger("startup").warning(
            "CORS_ALLOWED_ORIGINS parsed to empty list; falling back to dev defaults"
        )
        parsed = [
            origin.strip()
            for origin in DEFAULT_DEV_ORIGINS.split(",")
            if origin.strip()
        ]
    return parsed


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.services.mcp_client import get_server
    from app.services.profile import _load_existing_profiles

    log = logging.getLogger("startup")
    try:
        _load_existing_profiles()
    except Exception as exc:
        log.warning("profile preload failed: %s", exc, exc_info=True)

    # Warm the Iceberg catalog so the first /build/outcomes request
    # doesn't pay metadata-load latency that can exceed Railway's
    # liveness window. Each load_table() reads only metadata.json,
    # not data files — cheap.
    warm_tables = [
        "consumable.program_career_paths",
        "consumable.career_outcomes",
        "consumable.occupation_profiles",
        "consumable.onet_work_profiles",
        "consumable.ai_exposure",
        "consumable.career_branches",
        "consumable.regional_price_parities",
    ]
    try:
        server = get_server()
        for table_name in warm_tables:
            try:
                server.catalog.load_table(table_name)
                log.info("warmed iceberg metadata: %s", table_name)
            except Exception as exc:
                log.warning("warmup skipped %s: %s", table_name, exc)
    except Exception as exc:
        log.warning("MCP server warmup failed: %s", exc)

    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="FutureProof API",
        version=__version__,
        description="RPG-style college decision engine",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=_parse_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health.router)
    application.include_router(profile.router, prefix="/profile", tags=["Profile"])
    application.include_router(schools.router, prefix="/schools", tags=["Schools"])
    application.include_router(
        set_your_course.router, prefix="/intent", tags=["SetYourCourse"]
    )
    application.include_router(builds.router, prefix="/build", tags=["Builds"])
    application.include_router(builds_collection.router, tags=["Builds"])
    application.include_router(gauntlet.router, prefix="/build", tags=["Gauntlet"])
    application.include_router(
        guidance_router.router, prefix="/build", tags=["Guidance"]
    )
    application.include_router(branches.router, tags=["Branches"])
    application.include_router(careers.router, tags=["Careers"])
    application.include_router(career_pick.router)
    application.include_router(skills.router, prefix="/build", tags=["Skills"])
    application.include_router(wrapped.router, prefix="/build", tags=["Wrapped"])
    application.include_router(pdf_export.router)
    application.include_router(
        sessions.router, prefix="/session", tags=["Session"]
    )
    application.include_router(ask_gemma_router.router, tags=["AskGemma"])

    return application


app = create_app()
