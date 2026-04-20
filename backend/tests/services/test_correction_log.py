"""Tests for ``app.services.correction_log``.

Covers the append-only JSONL write path:
- One ``record_correction`` call → exactly one valid JSON line.
- The parent directory is created on first use (no pre-existing dir).
- Concurrent writes from two threads produce two complete lines
  (no interleaving) — the module's ``threading.Lock`` is the load-
  bearing invariant.

Every test uses ``tmp_path`` as the project root so we never touch
``data/reference/student_corrections.jsonl`` in the repo.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import pytest

from app.services import correction_log


@pytest.fixture
def tmp_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Redirect ``mcp_client.project_root()`` to ``tmp_path`` so the
    correction log writes under the tmp dir. Both ``correction_log``
    and ``community_suggestions`` import ``project_root`` — patch
    both module-level bindings."""
    monkeypatch.setattr(correction_log, "project_root", lambda: tmp_path)
    from app.services import community_suggestions, mcp_client

    monkeypatch.setattr(community_suggestions, "project_root", lambda: tmp_path)
    monkeypatch.setattr(mcp_client, "project_root", lambda: tmp_path)
    community_suggestions.reset_for_tests()
    return tmp_path


def _make_record(**overrides: Any) -> correction_log.CorrectionLogRecord:
    base: correction_log.CorrectionLogRecord = {
        "schema_version": "1.0",
        "kind": "correction",
        "timestamp": "",  # filled by _ensure_timestamp
        "school_unitid": 151351,
        "school_name": "Indiana University",
        "input_normalized": "marketing",
        "initial_major_text": "marketing",
        "initial_cip4": "52.14",
        "final_cip4": "52.14",
        "clicked_soc": "11-2021",
        "clicked_career_title": "Marketing Manager",
        "feasibility_mode": "direct_hit",
        "chips_tapped": [],
        "clarifier": None,
        "bucket": None,
        "backend": "stub",
        "model": "stub-model",
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


class TestAppend:
    def test_writes_one_line(self, tmp_project: Path) -> None:
        """One record_correction call appends exactly one valid JSON
        line, with schema_version + timestamp filled in."""
        correction_log.record_correction(_make_record())

        log_file = tmp_project / "data/reference/student_corrections.jsonl"
        assert log_file.exists()
        contents = log_file.read_text()
        lines = [
            line for line in contents.splitlines() if line.strip()
        ]
        assert len(lines) == 1

        parsed = json.loads(lines[0])
        assert parsed["school_unitid"] == 151351
        assert parsed["input_normalized"] == "marketing"
        # Schema + timestamp defaulted in by _ensure_timestamp.
        assert parsed["schema_version"] == "1.0"
        assert parsed["timestamp"]  # non-empty
        # ISO-8601 UTC — contains T and Z/offset.
        assert "T" in parsed["timestamp"]

    def test_missing_dir_creates_it(self, tmp_project: Path) -> None:
        """First-run must create ``data/reference/`` under the project
        root — the repo's data dir is gitignored so a fresh clone has
        no parent dir."""
        parent = tmp_project / "data" / "reference"
        assert not parent.exists()

        correction_log.record_correction(_make_record())

        assert parent.exists()
        assert (parent / "student_corrections.jsonl").exists()

    def test_concurrent_writes_do_not_interleave(
        self, tmp_project: Path
    ) -> None:
        """Two threads hammering ``record_correction`` in parallel
        must produce N complete, parseable JSON lines — no corruption.

        The module's ``_write_lock`` is what guarantees this. If it
        ever regresses to an unlocked write, bytes from the two
        threads will interleave mid-line and ``json.loads`` will
        fail on at least one of them."""
        N = 40  # per thread
        results: list[Exception | None] = [None, None]

        def _writer(idx: int, value: str) -> None:
            try:
                for i in range(N):
                    correction_log.record_correction(
                        _make_record(
                            input_normalized=f"{value}-{i}",
                            school_unitid=idx,
                        )
                    )
            except Exception as exc:  # pragma: no cover — defensive
                results[idx] = exc

        t1 = threading.Thread(target=_writer, args=(0, "alpha"))
        t2 = threading.Thread(target=_writer, args=(1, "beta"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert results[0] is None
        assert results[1] is None

        log_file = tmp_project / "data/reference/student_corrections.jsonl"
        contents = log_file.read_text()
        lines = [line for line in contents.splitlines() if line.strip()]
        assert len(lines) == 2 * N, (
            f"expected {2 * N} lines, got {len(lines)}"
        )
        # Every line must parse cleanly — no interleave corruption.
        parsed = [json.loads(line) for line in lines]
        # And every record must be one of the two threads' outputs.
        inputs = {p["input_normalized"] for p in parsed}
        expected = {f"alpha-{i}" for i in range(N)} | {
            f"beta-{i}" for i in range(N)
        }
        assert inputs == expected


class TestEnsureTimestamp:
    def test_fills_in_timestamp_when_missing(self) -> None:
        """An empty timestamp field is replaced with now() ISO-8601."""
        record = _make_record(timestamp="")
        out = correction_log._ensure_timestamp(record)
        assert out["timestamp"]
        assert "T" in out["timestamp"]

    def test_preserves_caller_timestamp(self) -> None:
        """A caller that pre-sets a timestamp keeps it (used by
        replay/backfill paths)."""
        fixed = "2026-04-01T12:00:00+00:00"
        record = _make_record(timestamp=fixed)
        out = correction_log._ensure_timestamp(record)
        assert out["timestamp"] == fixed
