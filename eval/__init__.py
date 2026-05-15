"""FutureProof Gemma eval harness.

Adds ``backend/`` to sys.path on import so adapters can ``from app.services.X
import …`` regardless of how the runner is invoked. Backend is also pip-
installable (``cd backend && pip install -e .``); the path insert is a
belt-and-suspenders convenience for fresh checkouts.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BACKEND = _REPO_ROOT / "backend"
if _BACKEND.exists():
    backend_str = str(_BACKEND)
    if backend_str not in sys.path:
        sys.path.insert(0, backend_str)
