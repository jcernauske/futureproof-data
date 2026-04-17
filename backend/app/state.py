"""In-memory build store with disk fallback.

Module-level dict for fast access. On cache miss, attempts to load
from the on-disk builds directory so builds survive server reloads
(uvicorn --reload wipes the dict on every file change).
"""

from __future__ import annotations

import logging

from app.models.career import Build

logger = logging.getLogger(__name__)

_builds: dict[str, Build] = {}


def store_build(build: Build) -> str:
    _builds[build.build_id] = build
    return build.build_id


def get_build(build_id: str) -> Build | None:
    build = _builds.get(build_id)
    if build is not None:
        return build

    # Disk fallback — survives uvicorn --reload
    try:
        from app.services.builds import load_build
        build = load_build(build_id)
        _builds[build_id] = build
        logger.info("Recovered build %s from disk", build_id)
        return build
    except FileNotFoundError:
        return None


def update_build(build_id: str, build: Build) -> None:
    _builds[build_id] = build

    # Persist to disk so mutations survive reloads. If save_build
    # fails (disk full, DB locked, schema mismatch), we let the
    # exception propagate — silently dropping a mutation leaves the
    # in-memory state and the DB out of sync, which is worse than a
    # visible 5xx.
    from app.services.builds import save_build
    save_build(build)
