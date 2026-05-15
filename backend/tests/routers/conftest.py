"""Shared fixtures for backend router tests.

Ensures `backend/` is on sys.path and isolates DuckDB/state so tests
don't stomp on each other or the real app DB.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


@pytest.fixture
def isolated_builds_db(tmp_path, monkeypatch):
    """Point the builds DuckDB + in-memory state at a tmp file/dict.

    Clears state._builds and builds._conns before and after the test.
    """
    from app import state
    from app.services import db

    target = tmp_path / "builds.duckdb"
    monkeypatch.setattr(db, "_db_path", lambda: target)
    db._conns.clear()
    state._builds.clear()
    yield target
    db._conns.clear()
    state._builds.clear()


