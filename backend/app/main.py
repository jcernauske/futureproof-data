from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.routers import health


def create_app() -> FastAPI:
    application = FastAPI(
        title="FutureProof API",
        version=__version__,
        description="AI Career Impact Tool — Backend API",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:4173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health.router)

    return application


app = create_app()
