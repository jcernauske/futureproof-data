"""In-memory build store.

Module-level dict sufficient for hackathon (single server process).
Builds persist across requests but not across server restarts.
"""

from __future__ import annotations

from app.models.career import Build

_builds: dict[str, Build] = {}


def store_build(build: Build) -> str:
    _builds[build.build_id] = build
    return build.build_id


def get_build(build_id: str) -> Build | None:
    return _builds.get(build_id)


def update_build(build_id: str, build: Build) -> None:
    _builds[build_id] = build
