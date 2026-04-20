"""In-memory aggregate of the append-only correction log.

Rebuilt from ``data/reference/student_corrections.jsonl`` on first read
and refreshed incrementally on every new write. Exposes
``get_suggestions`` for the /intent/stream endpoint to surface the
"Other students searching ... ended up here:" surface.

Cacheable feasibility modes only: ``direct_hit``, ``crosswalk_quirk``,
``adjacent_reachable``. The two "not reachable" modes log for audit but
never surface as suggestions — that is the design guardrail keeping the
reinforcement loop from learning noise.

See docs/specs/feature-set-your-course.md §4 Community Suggestions
Surface.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from app.services import correction_log
from app.services.correction_log import CorrectionLogRecord
from app.services.mcp_client import project_root

logger = logging.getLogger(__name__)


# Cacheable modes — only these contribute to community suggestions.
_CACHEABLE_MODES = frozenset(
    {"direct_hit", "crosswalk_quirk", "adjacent_reachable"}
)


class Suggestion(TypedDict):
    clicked_soc: str
    clicked_career_title: str
    canonical_cip4: str
    count: int


@dataclass
class _Bucket:
    count: int = 0
    last_canonical_cip4: str = ""


# Aggregate shape:
# { (unitid, input_normalized): { (soc, title): _Bucket } }
_aggregate: dict[
    tuple[int, str], dict[tuple[str, str], _Bucket]
] = {}
_lock = threading.RLock()
_initialized = False


def normalize_input(raw: str) -> str:
    """THE single pinned normalization function.

    Rule: strip, lowercase, collapse whitespace. Every code path that
    writes a correction record OR reads suggestions MUST call this
    function so the cache key stays consistent across writers and
    readers. Diverging normalization is the single biggest cause of a
    cold-looking suggestion surface next to a populated log file.
    """
    if raw is None:
        return ""
    return " ".join(str(raw).strip().lower().split())


def _log_path() -> Path:
    return project_root() / "data/reference/student_corrections.jsonl"


def _apply_record(record: CorrectionLogRecord) -> None:
    """Merge one record into the in-memory aggregate. Caller holds the lock."""
    mode = record.get("feasibility_mode")
    if mode not in _CACHEABLE_MODES:
        return
    soc = record.get("clicked_soc")
    title = record.get("clicked_career_title")
    if not soc or not title:
        return
    unitid = record.get("school_unitid")
    input_normalized = record.get("input_normalized")
    if unitid is None or not input_normalized:
        return

    outer_key = (int(unitid), str(input_normalized))
    inner_key = (str(soc), str(title))
    inner = _aggregate.setdefault(outer_key, {})
    bucket = inner.setdefault(inner_key, _Bucket())
    bucket.count += 1
    canonical = str(record.get("final_cip4") or record.get("initial_cip4") or "")
    if canonical:
        bucket.last_canonical_cip4 = canonical


def rebuild() -> None:
    """Re-read the whole JSONL file and rebuild the aggregate from scratch.

    Tolerates corrupt lines (logs a warning and skips). Filters to
    cacheable feasibility modes only and records with a non-null
    ``clicked_soc``.
    """
    global _initialized
    path = _log_path()
    with _lock:
        _aggregate.clear()
        _initialized = True
        if not path.exists():
            return
        try:
            with path.open("r", encoding="utf-8") as fh:
                for line_no, raw_line in enumerate(fh, start=1):
                    stripped = raw_line.strip()
                    if not stripped:
                        continue
                    try:
                        raw = json.loads(stripped)
                    except json.JSONDecodeError as exc:
                        logger.warning(
                            "corrupt correction log line %d: %s",
                            line_no,
                            exc,
                        )
                        continue
                    if not isinstance(raw, dict):
                        continue
                    coerced = correction_log._coerce_record(raw)
                    if coerced is None:
                        continue
                    _apply_record(coerced)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("correction log rebuild failed: %s", exc)


def refresh_on_write(record: CorrectionLogRecord) -> None:
    """Incremental update for one just-written record.

    Cheaper than a full rebuild() per write. Called from
    ``correction_log.record_correction`` after a successful append.
    """
    with _lock:
        if not _initialized:
            # Cold — build from disk once, which already includes this
            # record (since the append happened before this call). Avoids
            # double-counting.
            rebuild()
            return
        _apply_record(record)


def _ensure_initialized() -> None:
    if _initialized:
        return
    rebuild()


def _min_count() -> int:
    """Threshold for surfacing a suggestion. Default 1 during hackathon."""
    try:
        return max(1, int(os.environ.get("COMMUNITY_MIN_COUNT", "1")))
    except (TypeError, ValueError):
        return 1


def get_suggestions(
    unitid: int,
    input_normalized: str,
    top_k: int = 3,
) -> list[Suggestion]:
    """Return up to ``top_k`` suggestions ranked by count descending.

    ``input_normalized`` must be produced by :func:`normalize_input` —
    we do NOT re-normalize here so callers can't drift.
    """
    _ensure_initialized()
    key = (int(unitid), str(input_normalized))
    threshold = _min_count()
    with _lock:
        inner = _aggregate.get(key, {})
        if not inner:
            return []
        ranked = sorted(
            (
                Suggestion(
                    clicked_soc=soc,
                    clicked_career_title=title,
                    canonical_cip4=bucket.last_canonical_cip4,
                    count=bucket.count,
                )
                for (soc, title), bucket in inner.items()
                if bucket.count >= threshold
            ),
            key=lambda s: (-s["count"], s["clicked_career_title"]),
        )
    return ranked[: max(0, int(top_k))]


def reset_for_tests() -> None:
    """Drop the in-memory aggregate. Tests that mutate the JSONL file
    call this to force a rebuild on the next read."""
    global _initialized
    with _lock:
        _aggregate.clear()
        _initialized = False
