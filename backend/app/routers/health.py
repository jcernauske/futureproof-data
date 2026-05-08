from fastapi import APIRouter

from app import __version__
from app.models.health import HealthResponse
from app.services.gemma_client import health_info

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    backend, model = health_info()
    return HealthResponse(
        status="ok",
        project="futureproof",
        version=__version__,
        inference_backend=backend,
        inference_model=model,
    )
