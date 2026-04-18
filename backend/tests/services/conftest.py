"""Pytest fixtures for CLI service tests.

Ensures ``backend/`` is on ``sys.path`` so ``app.services.*`` imports
resolve without pytest being told to use ``rootdir=backend``. Isolates
the build directory so ``test_builds`` never writes to the real
``backend/data/builds`` store.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


@pytest.fixture(autouse=True)
def _reset_gemma_client_state():
    """Null the module-level Gemma client + semaphore before every test.

    The /build fan-out introduced a lazy module-level
    ``_semaphore`` sized from ``GEMMA_MAX_CONCURRENCY``. If a prior test
    fails after monkeypatching that env var but before its trailing
    ``reset_cache()``, later tests would inherit a size-2 (or whatever)
    semaphore and silently run under a different concurrency budget.
    This autouse fixture makes the budget deterministic test-to-test.
    """
    from app.services import gemma_client

    gemma_client.reset_cache()
    yield
    gemma_client.reset_cache()


@pytest.fixture
def isolated_builds_dir(tmp_path, monkeypatch):
    """Redirect the builds DuckDB to a tmp file for the test.

    Named ``isolated_builds_dir`` for historical compatibility; the
    backing store is a DuckDB file, not a directory. The connection
    cache is reset before and after the test so each run gets a fresh
    schema.
    """
    from app.services import builds

    target = tmp_path / "builds.duckdb"
    monkeypatch.setattr(builds, "_db_path", lambda: target)
    builds._conns.clear()
    yield target
    builds._conns.clear()
