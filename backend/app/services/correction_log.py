"""Append-only correction log.

Lives at ``data/reference/student_corrections.jsonl``, committed to git.
Every committed build writes one JSONL line when the student's final
resolution differs from Gemma's initial one — this log is the raw input
to the community-suggestions surface.

See docs/specs/feature-set-your-course.md §2 Decision #4 + §4 Data Model.

The write path is ``record_correction``. Logging MUST NOT crash the
commit path — every exception is swallowed to ``logger.warning``, same
discipline as ``gemma_client._log_exchange``.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, TypedDict

from app.services.mcp_client import project_root

logger = logging.getLogger(__name__)


_REL_LOG_PATH = Path("data/reference/student_corrections.jsonl")
_write_lock = threading.Lock()
_SCHEMA_VERSION = "1.0"


class CorrectionLogRecord(TypedDict, total=False):
    """One JSONL line in ``student_corrections.jsonl``.

    Fields mirror §4 Data Model Changes of feature-set-your-course.md.
    ``total=False`` because ``schema_version`` and ``timestamp`` are
    filled in by the writer when absent.
    """

    schema_version: str
    kind: Literal["correction"]
    timestamp: str
    school_unitid: int
    school_name: str
    input_normalized: str
    initial_major_text: str
    initial_cip4: str
    final_cip4: str
    clicked_soc: str | None
    clicked_career_title: str | None
    feasibility_mode: str | None
    chips_tapped: list[str]
    clarifier: str | None
    bucket: str | None
    backend: str
    model: str


def _log_path() -> Path:
    """Absolute path to the JSONL file. Parent dir is created if missing."""
    path = project_root() / _REL_LOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _ensure_timestamp(record: CorrectionLogRecord) -> CorrectionLogRecord:
    """Fill in an ISO8601 UTC timestamp when the caller didn't set one.

    Isolated for testability — the writer owns the clock so callers can
    build deterministic records without reaching for datetime.
    """
    if not record.get("timestamp"):
        record["timestamp"] = datetime.now(timezone.utc).isoformat()
    if not record.get("schema_version"):
        record["schema_version"] = _SCHEMA_VERSION
    return record


def record_correction(record: CorrectionLogRecord) -> None:
    """Append one JSONL line and refresh the in-memory aggregate.

    Single write() call under a threading.Lock so concurrent commits
    don't interleave partial JSON lines. Never raises — logging must
    not crash the commit path.
    """
    try:
        record = _ensure_timestamp(record)
        line = json.dumps(record, ensure_ascii=False, default=str)
        path = _log_path()
        with _write_lock, path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("correction_log write failed: %s", exc)
        return

    # Refresh after write so the in-memory aggregate stays fresh without
    # a full rebuild on read.
    try:
        from app.services import community_suggestions

        community_suggestions.refresh_on_write(record)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "community_suggestions.refresh_on_write failed: %s", exc
        )


def _coerce_record(raw: dict[str, Any]) -> CorrectionLogRecord | None:
    """Best-effort coercion of a decoded JSONL line into a log record.

    Returns ``None`` when the line is missing load-bearing fields. Used by
    ``community_suggestions.rebuild`` to tolerate corrupt lines without
    crashing the startup path.
    """
    try:
        unitid_raw = raw.get("school_unitid")
        if unitid_raw is None:
            return None
        unitid = int(unitid_raw)
        input_normalized = str(raw.get("input_normalized") or "")
        if not input_normalized:
            return None
    except (TypeError, ValueError):
        return None

    coerced: CorrectionLogRecord = {
        "schema_version": str(raw.get("schema_version", _SCHEMA_VERSION)),
        "kind": "correction",
        "timestamp": str(raw.get("timestamp") or ""),
        "school_unitid": unitid,
        "school_name": str(raw.get("school_name") or ""),
        "input_normalized": input_normalized,
        "initial_major_text": str(raw.get("initial_major_text") or ""),
        "initial_cip4": str(raw.get("initial_cip4") or ""),
        "final_cip4": str(raw.get("final_cip4") or ""),
        "clicked_soc": (
            str(raw["clicked_soc"]) if raw.get("clicked_soc") else None
        ),
        "clicked_career_title": (
            str(raw["clicked_career_title"])
            if raw.get("clicked_career_title")
            else None
        ),
        "feasibility_mode": (
            str(raw["feasibility_mode"])
            if raw.get("feasibility_mode")
            else None
        ),
        "chips_tapped": [
            str(c) for c in (raw.get("chips_tapped") or [])
        ],
        "clarifier": (
            str(raw["clarifier"]) if raw.get("clarifier") else None
        ),
        "bucket": (str(raw["bucket"]) if raw.get("bucket") else None),
        "backend": str(raw.get("backend") or ""),
        "model": str(raw.get("model") or ""),
    }
    return coerced
