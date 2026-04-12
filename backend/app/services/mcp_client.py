"""Thin singleton wrapper around FutureProofMCPServer.

The CLI and routers both need a single configured MCP server instance
that knows where the Iceberg catalog lives. Instantiating the server is
cheap but it caches parsed contracts and the major->CIP lookup table,
so sharing one instance across the process avoids redundant disk reads.

The ``src/`` directory is added to ``sys.path`` on import so
``mcp_server.futureproof_server`` is always resolvable regardless of the
working directory the CLI is launched from.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SRC_PATH = _PROJECT_ROOT / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

# isort: off
from mcp_server.futureproof_server import FutureProofMCPServer  # type: ignore[import-not-found]  # noqa: E402
# isort: on

_server: FutureProofMCPServer | None = None


def project_root() -> Path:
    return _PROJECT_ROOT


def get_server() -> FutureProofMCPServer:
    """Return the shared MCP server instance, constructing it on first call.

    ``warehouse_path`` is kept for framework compatibility but reads are
    satisfied by the Iceberg catalog which carries absolute metadata
    paths, so an empty ``data/warehouse`` directory is fine.
    """
    global _server
    if _server is None:
        catalog_path = os.environ.get(
            "FUTUREPROOF_CATALOG_PATH",
            str(_PROJECT_ROOT / "data" / "catalog" / "catalog.db"),
        )
        warehouse_path = os.environ.get(
            "FUTUREPROOF_WAREHOUSE_PATH",
            str(_PROJECT_ROOT / "data" / "warehouse"),
        )
        _server = FutureProofMCPServer(
            warehouse_path=warehouse_path,
            catalog_path=catalog_path,
            server_name="futureproof-cli",
        )
    return _server


def reset_server() -> None:
    """Drop the cached server instance. Used by tests."""
    global _server
    _server = None


def call(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    """Invoke a named MCP handler by its public tool name.

    Each tool has a ``_handle_<name>`` method on the server. This
    function exists so call sites read like tool invocations rather than
    private attribute access.
    """
    server = get_server()
    handler_name = f"_handle_{tool}"
    handler = getattr(server, handler_name, None)
    if handler is None:
        raise AttributeError(f"MCP server has no handler for tool {tool!r}")
    result: dict[str, Any] = handler(args)
    return result
