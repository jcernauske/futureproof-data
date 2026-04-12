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


@pytest.fixture
def isolated_builds_dir(tmp_path, monkeypatch):
    """Redirect the builds directory to a tmp path for the test."""
    from app.services import builds

    target = tmp_path / "builds"
    monkeypatch.setattr(builds, "_builds_dir", lambda: target)
    target.mkdir(parents=True, exist_ok=True)
    return target
