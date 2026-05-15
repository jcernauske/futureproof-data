import asyncio
import logging

import httpx
from fastapi import APIRouter

from app import __version__
from app.models.health import HealthResponse
from app.services import gemma_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])


async def _probe_model(backend: str) -> bool:
    try:
        config = gemma_client.current_config()
        base = config.base_url.rstrip("/v1").rstrip("/")
        if backend == "ollama":
            # /api/ps returns only models currently loaded in memory.
            # Badge is green only when a model is actually warm and ready.
            url = f"{base}/api/ps"
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return False
                return bool(resp.json().get("models"))
        else:
            url = f"{config.base_url}/models"
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {config.api_key}"},
                )
                return resp.status_code == 200
    except Exception:
        return False


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    backend, model = gemma_client.health_info()
    reachable = await _probe_model(backend)
    return HealthResponse(
        status="ok",
        project="futureproof",
        version=__version__,
        inference_backend=backend,
        inference_model=model,
        model_reachable=reachable,
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
