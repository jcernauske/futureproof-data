import asyncio
import logging
import os
import time
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

    # Warm the QueryEngine so the first /build request doesn't pay
    # cold-start cost: duckdb.connect() + install/load iceberg extension
    # + CREATE VIEW for every registered table. catalog.load_table()
    # alone only touches metadata.json — it does NOT trigger the
    # extension load or view registration, both of which run lazily
    # on first query through _query_engine._ensure_initialized.
    #
    # One small query forces all of that. After this returns, every
    # subsequent request hits a hot engine. Doubles as a fail-fast:
    # if the catalog is empty or unreachable, the error surfaces here
    # at boot, not silently on every user request.
    try:
        server = get_server()
        started = time.perf_counter()
        rows = await asyncio.to_thread(
            server.query_iceberg_simple,
            "consumable.occupation_profiles",
            limit=1,
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if rows and isinstance(rows[0], dict) and "error" in rows[0]:
            log.error(
                "MCP warmup query returned error in %d ms — catalog or "
                "view registration may be broken: %s",
                elapsed_ms, rows[0]["error"],
            )
        else:
            view_count = len(getattr(server._get_query_engine(), "_views", {}))
            log.info(
                "MCP warmup OK in %d ms (%d iceberg views registered)",
                elapsed_ms, view_count,
            )
    except Exception as exc:
        log.warning("MCP server warmup failed: %s", exc, exc_info=True)

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
    application.include_router(pdf_export.router)
    application.include_router(
        sessions.router, prefix="/session", tags=["Session"]
    )
    application.include_router(ask_gemma_router.router, tags=["AskGemma"])

    return application


app = create_app()
