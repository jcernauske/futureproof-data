"""Wrapped story frame endpoints (Screen 9).

Three endpoints:
- POST /build/{id}/wrapped/render  — trigger Playwright rendering
- GET  /build/{id}/wrapped          — list frame URLs (metadata)
- GET  /build/{id}/wrapped/{idx}    — serve a single frame PNG

Caching: rendered PNGs persist as BLOBs in the `wrapped_frames` DuckDB
table. Re-rendering is skipped when cached frames exist and are at
least as fresh as the build itself.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Response

from app import state
from app.models.career import (
    Build,
    RenderResponse,
    WrappedFrameInfo,
    WrappedResponse,
)
from app.services import builds as builds_service
from app.services import profile as profile_service
from app.services import wrapped_renderer

logger = logging.getLogger(__name__)

router = APIRouter()

# Per-build render serialization. Prevents two concurrent /render calls
# for the same build_id from both launching Chromium and interleaving
# their save_wrapped_frames writes. The guard lock serializes dict
# mutation so concurrent first-time lookups don't create duplicate locks.
_render_locks: dict[str, asyncio.Lock] = {}
_render_locks_guard = asyncio.Lock()


async def _render_lock_for(build_id: str) -> asyncio.Lock:
    async with _render_locks_guard:
        return _render_locks.setdefault(build_id, asyncio.Lock())


def _load_build_or_404(build_id: str) -> Build:
    build = state.get_build(build_id)
    if build is not None:
        return build
    try:
        build = builds_service.load_build(build_id)
        state.store_build(build)
        return build
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")


def _animal_emoji_for(profile_name: str) -> str:
    if not profile_name:
        return ""
    return profile_service._find_emoji(profile_service._normalize(profile_name))


@router.post("/{build_id}/wrapped/render", response_model=RenderResponse)
async def render_wrapped(build_id: str) -> RenderResponse:
    build = _load_build_or_404(build_id)

    # Cheap pre-check — if cache is fresh, skip acquiring the render lock.
    # This is a hint, not a guarantee. The definitive check runs inside
    # the lock to avoid the double-render race.
    if _cache_fresh(build_id, build.created_at):
        return RenderResponse(status="cached", frame_count=6)

    lock = await _render_lock_for(build_id)
    async with lock:
        # Re-check under the lock (double-checked locking): another
        # request that was ahead of us in the queue may have just
        # finished rendering. If so, return cached without launching
        # a second Chromium instance.
        if _cache_fresh(build_id, build.created_at):
            return RenderResponse(status="cached", frame_count=6)

        emoji = _animal_emoji_for(build.profile_name)
        try:
            frames = await wrapped_renderer.render_frames(
                build=build,
                profile_name=build.profile_name,
                animal_emoji=emoji,
            )
        except RuntimeError as exc:
            logger.exception("Wrapped render failed for build %s", build_id)
            raise HTTPException(status_code=500, detail=str(exc))

        builds_service.save_wrapped_frames(build_id, frames)
        return RenderResponse(status="ok", frame_count=len(frames))


def _cache_fresh(build_id: str, build_created_at: str) -> bool:
    existing = builds_service.list_wrapped_frames(build_id)
    rendered_at = builds_service.wrapped_frames_rendered_at(build_id)
    return (
        len(existing) == 6
        and rendered_at is not None
        and rendered_at >= build_created_at
    )


@router.get("/{build_id}/wrapped", response_model=WrappedResponse)
async def get_wrapped(build_id: str) -> WrappedResponse:
    _load_build_or_404(build_id)

    indices = builds_service.list_wrapped_frames(build_id)
    if not indices:
        raise HTTPException(
            status_code=409,
            detail=f"No wrapped frames rendered for build {build_id}. "
                   f"Call POST /build/{build_id}/wrapped/render first.",
        )
    frames = [
        WrappedFrameInfo(index=i, url=f"/build/{build_id}/wrapped/{i}")
        for i in indices
    ]
    return WrappedResponse(frames=frames)


@router.get("/{build_id}/wrapped/{frame_index}")
async def get_wrapped_frame(build_id: str, frame_index: int) -> Response:
    if frame_index < 0 or frame_index > 5:
        raise HTTPException(
            status_code=404,
            detail=f"Frame index {frame_index} out of range",
        )
    try:
        png = builds_service.load_wrapped_frame(build_id, frame_index)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Frame {frame_index} not rendered for build {build_id}",
        )
    filename = f"futureproof-{build_id}-frame-{frame_index}.png"
    return Response(
        content=png,
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "public, max-age=3600",
        },
    )
