"""Deterministic CIP lookup from data/reference/major_to_cip.yaml.

Used by the intent service to short-circuit Gemma when the student's
input is an exact (or alias) match for a known major. Pure Python,
no LLM, no external calls.

Path resolution is cwd-independent: we walk upward from this module
file looking for the YAML. Backend pytest runs from ``backend/``, root
pytest runs from the repo root, and ``uvicorn app.main:app`` is started
from either — all three must resolve the same YAML or the
short-circuit silently no-ops in some contexts (which is exactly how
Bug B leaked into prod before this spec).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import TypedDict, cast

import yaml  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


class MajorEntry(TypedDict):
    major: str
    cip4: str
    cip_family: str
    aliases: list[str]


_REL_YAML_PATH = Path("data/reference/major_to_cip.yaml")


@lru_cache(maxsize=1)
def _yaml_path() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / _REL_YAML_PATH
        if candidate.is_file():
            return candidate
    return None


@lru_cache(maxsize=1)
def _load() -> tuple[MajorEntry, ...]:
    """Load and cache the YAML lookup table.

    Two caches layer here: ``_yaml_path`` caches the discovered file
    location, ``_load`` caches the parsed entries. Tests that mutate
    ``data/reference/major_to_cip.yaml`` or monkeypatch ``_yaml_path``
    must call BOTH ``_yaml_path.cache_clear()`` and
    ``_load.cache_clear()`` to see the change.
    """
    path = _yaml_path()
    if path is None:
        # Graceful degradation: silent-fail makes every student's
        # intent query fall through to Gemma. Log once so ops can
        # see the config issue — this is the exact failure mode
        # (Bug B) the spec was written to fix.
        logger.warning(
            "major_lookup: %s not found in any parent of %s; "
            "deterministic short-circuit disabled",
            _REL_YAML_PATH,
            Path(__file__).resolve().parent,
        )
        return ()
    with path.open() as f:
        raw = yaml.safe_load(f) or []
    if not isinstance(raw, list):
        return ()
    entries = tuple(e for e in raw if isinstance(e, dict))
    return cast("tuple[MajorEntry, ...]", entries)


def lookup_major(text: str) -> MajorEntry | None:
    """Return the matching YAML entry or None.

    Matches case-insensitively against ``major`` and every ``alias``.
    Returns ``None`` for empty input, no match, or load failure.
    """
    if not text:
        return None
    needle = text.strip().lower()
    if not needle:
        return None
    for entry in _load():
        if needle == str(entry.get("major", "")).lower():
            return entry
        for alias in entry.get("aliases") or []:
            if needle == str(alias).lower():
                return entry
    return None
