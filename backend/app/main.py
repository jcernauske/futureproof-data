from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.routers import (
    branches,
    builds,
    builds_collection,
    career_pick,
    gauntlet,
    guidance_router,
    health,
    intent,
    profile,
    reports,
    schools,
    sessions,
    set_your_course,
    skills,
    wrapped,
)


def create_app() -> FastAPI:
    application = FastAPI(
        title="FutureProof API",
        version=__version__,
        description="RPG-style college decision engine",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health.router)
    application.include_router(profile.router, prefix="/profile", tags=["Profile"])
    application.include_router(schools.router, prefix="/schools", tags=["Schools"])
    application.include_router(intent.router, prefix="/intent", tags=["Intent"])
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
    application.include_router(career_pick.router)
    application.include_router(skills.router, prefix="/build", tags=["Skills"])
    application.include_router(wrapped.router, prefix="/build", tags=["Wrapped"])
    application.include_router(
        sessions.router, prefix="/session", tags=["Session"]
    )
    application.include_router(reports.router, tags=["Reports"])

    @application.on_event("startup")
    async def startup():
        import logging

        from app.services.mcp_client import get_server
        from app.services.profile import _load_existing_profiles

        log = logging.getLogger("startup")
        _load_existing_profiles()

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

    return application


app = create_app()
