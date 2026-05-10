import asyncio
import logging

from fastapi import APIRouter

from app import __version__
from app.models.health import HealthResponse
from app.services import gemma_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    backend, model = gemma_client.health_info()
    return HealthResponse(
        status="ok",
        project="futureproof",
        version=__version__,
        inference_backend=backend,
        inference_model=model,
    )


@router.post("/health/warmup", status_code=202)
async def warmup() -> dict[str, str]:
    """Fire a minimal Gemma generation to pre-load model weights.

    Called from the profile screen so Ollama loads the model into GPU
    memory before the student reaches /set-your-course. Fire-and-forget
    on the frontend — the response is irrelevant.
    """
    asyncio.create_task(_warmup_task())
    return {"status": "warming"}


async def _warmup_task() -> None:
    try:
        await gemma_client.generate_async(
            system="Reply with one word.",
            user="Hi",
            max_tokens=4,
            temperature=0,
            extra={"call_site": "warmup"},
        )
    except Exception as exc:
        logger.debug("warmup call failed (non-fatal): %r", exc)
