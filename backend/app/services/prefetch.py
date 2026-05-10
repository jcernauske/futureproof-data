"""Speculative prefetch for build-stream prerequisites.

When the student picks a career on /set-your-course, the frontend fires
``POST /build/prefetch`` with the current slider values. This module runs
``stat_engine.compute_one``, ``branch_tree.get_branches``, and
``career_description.get_or_generate`` concurrently in the background and
caches the results. When ``/build/stream`` starts, it consumes the cached
result instead of recomputing — shaving the stat-engine wall-clock off the
build transition.

If the student adjusts a slider, the frontend fires ``DELETE /build/prefetch``
(invalidating the stale result) then a new ``POST /build/prefetch`` with
updated values.

The cache is intentionally small (one entry per key, keyed by the full
param tuple) and short-lived (entries expire after 5 minutes). No
persistence — prefetch results live only in-process memory.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import cast

from app.models.career import (
    CareerBranch,
    CareerDescription,
    CareerOutcome,
    EffortLevel,
)
from app.services import branch_tree, career_description, stat_engine

logger = logging.getLogger(__name__)

TTL_SECONDS = 300

PrefetchKey = tuple[int, str, str, str, float, str | None, str | None, str | None]


def make_key(
    unitid: int,
    cipcode: str,
    soc_code: str,
    effort: str,
    loan_pct: float,
    student_major: str | None = None,
    student_cip: str | None = None,
    home_state: str | None = None,
) -> PrefetchKey:
    return (
        unitid, cipcode, soc_code, effort, loan_pct,
        student_major, student_cip, home_state,
    )


@dataclass
class PrefetchResult:
    career: CareerOutcome | None = None
    branches: list[CareerBranch] = field(default_factory=list)
    career_description: CareerDescription | None = None
    created_at: float = field(default_factory=time.monotonic)
    error: str | None = None


@dataclass
class _PrefetchEntry:
    task: asyncio.Task[PrefetchResult]
    created_at: float = field(default_factory=time.monotonic)


_cache: dict[PrefetchKey, _PrefetchEntry] = {}


async def _run_prefetch(
    unitid: int,
    cipcode: str,
    soc_code: str,
    effort: str,
    loan_pct: float,
    student_major: str | None,
    student_cip: str | None,
    intent_keywords: list[str] | None,
    home_state: str | None,
    occupation_title: str | None,
) -> PrefetchResult:
    result = PrefetchResult()

    async def _compute_career() -> None:
        try:
            result.career = await asyncio.to_thread(
                stat_engine.compute_one,
                unitid=unitid,
                cipcode=cipcode,
                soc_code=soc_code,
                effort=cast(EffortLevel, effort or "balanced"),
                loan_pct=loan_pct,
                student_major=student_major,
                student_cip=student_cip,
                intent_keywords=intent_keywords,
                home_state=home_state,
            )
        except Exception as exc:
            logger.warning("prefetch compute_one failed: %r", exc)
            result.error = str(exc)

    async def _fetch_branches() -> None:
        try:
            result.branches = await asyncio.to_thread(
                branch_tree.get_branches, soc_code,
            )
        except Exception as exc:
            logger.warning("prefetch get_branches failed: %r", exc)

    async def _fetch_description() -> None:
        if not occupation_title:
            return
        try:
            result.career_description = await career_description.get_or_generate(
                soc_code, occupation_title,
            )
        except Exception as exc:
            logger.warning("prefetch career_description failed: %r", exc)

    await asyncio.gather(_compute_career(), _fetch_branches(), _fetch_description())
    return result


def start(
    unitid: int,
    cipcode: str,
    soc_code: str,
    effort: str,
    loan_pct: float,
    student_major: str | None = None,
    student_cip: str | None = None,
    intent_keywords: list[str] | None = None,
    home_state: str | None = None,
    occupation_title: str | None = None,
) -> PrefetchKey:
    """Start a background prefetch. Returns the cache key."""
    key = make_key(
        unitid, cipcode, soc_code, effort, loan_pct,
        student_major, student_cip, home_state,
    )

    _evict_expired()

    existing = _cache.get(key)
    if existing and not existing.task.done():
        return key
    if existing and existing.task.done():
        elapsed = time.monotonic() - existing.created_at
        if elapsed < TTL_SECONDS:
            return key

    task = asyncio.create_task(
        _run_prefetch(
            unitid, cipcode, soc_code, effort, loan_pct,
            student_major, student_cip, intent_keywords,
            home_state, occupation_title,
        )
    )
    _cache[key] = _PrefetchEntry(task=task)
    logger.info("prefetch started for soc=%s unitid=%d", soc_code, unitid)
    return key


def invalidate(key: PrefetchKey) -> bool:
    """Cancel and remove a prefetch entry. Returns True if something was removed."""
    entry = _cache.pop(key, None)
    if entry is None:
        return False
    if not entry.task.done():
        entry.task.cancel()
    logger.info("prefetch invalidated key=%s", key)
    return True


async def consume(key: PrefetchKey) -> PrefetchResult | None:
    """Await and return a prefetch result, removing it from the cache.

    Returns None if no entry exists, the entry expired, or the prefetch
    errored on the career compute (the critical path).
    """
    entry = _cache.pop(key, None)
    if entry is None:
        return None

    elapsed = time.monotonic() - entry.created_at
    if elapsed > TTL_SECONDS:
        if not entry.task.done():
            entry.task.cancel()
        logger.info("prefetch expired key=%s (%.1fs)", key, elapsed)
        return None

    try:
        result = await entry.task
    except asyncio.CancelledError:
        return None
    except Exception as exc:
        logger.warning("prefetch task raised: %r", exc)
        return None

    if result.career is None:
        return None

    logger.info(
        "prefetch consumed for soc=%s (waited %.1fs)",
        key[2], elapsed,
    )
    return result


def _evict_expired() -> None:
    now = time.monotonic()
    expired = [k for k, v in _cache.items() if now - v.created_at > TTL_SECONDS]
    for k in expired:
        entry = _cache.pop(k, None)
        if entry and not entry.task.done():
            entry.task.cancel()


def clear_all() -> int:
    """Cancel all entries and clear the cache. Returns the number removed."""
    count = len(_cache)
    for entry in _cache.values():
        if not entry.task.done():
            entry.task.cancel()
    _cache.clear()
    return count
