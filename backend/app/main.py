from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.routers import (
    branches,
    builds,
    gauntlet,
    guidance_router,
    health,
    intent,
    profile,
    reports,
    schools,
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
    application.include_router(builds.router, prefix="/build", tags=["Builds"])
    application.include_router(gauntlet.router, prefix="/build", tags=["Gauntlet"])
    application.include_router(
        guidance_router.router, prefix="/build", tags=["Guidance"]
    )
    application.include_router(branches.router, tags=["Branches"])
    application.include_router(skills.router, prefix="/build", tags=["Skills"])
    application.include_router(wrapped.router, prefix="/build", tags=["Wrapped"])
    application.include_router(reports.router, tags=["Reports"])

    @application.on_event("startup")
    async def startup():
        from app.services.profile import _load_existing_profiles
        _load_existing_profiles()

    return application


app = create_app()
