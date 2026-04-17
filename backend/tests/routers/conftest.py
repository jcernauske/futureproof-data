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

    Everything the wrapped router touches (state._builds, builds._conns)
    is cleared before and after the test.
    """
    from app import state
    from app.services import builds

    target = tmp_path / "builds.duckdb"
    monkeypatch.setattr(builds, "_db_path", lambda: target)
    builds._conns.clear()
    state._builds.clear()
    yield target
    builds._conns.clear()
    state._builds.clear()
