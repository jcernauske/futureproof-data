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

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SRC_PATH = _PROJECT_ROOT / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

# isort: off
from mcp_server.futureproof_server import FutureProofMCPServer  # type: ignore[import-not-found]  # noqa: E402
# isort: on

_server: FutureProofMCPServer | None = None

# Tool schema cache — populated lazily from the MCP server's get_tools().
_tool_schemas: dict[str, dict[str, Any]] | None = None


class McpArgumentError(Exception):
    """Raised when tool arguments fail schema validation."""


def project_root() -> Path:
    return _PROJECT_ROOT


def get_server() -> FutureProofMCPServer:
    """Return the shared MCP server instance, constructing it on first call.

    Iceberg metadata stores manifest/data-file references as repo-root-
    relative paths (e.g. ``data/bronze/iceberg_warehouse/...``), so both
    pyiceberg's catalog loader and DuckDB's ``iceberg_scan`` resolve them
    against the process CWD. We pin CWD to the project root here so the
    backend reads the catalog correctly regardless of how it was launched
    (``uvicorn`` from ``backend/``, ``uv run`` from the repo root, Docker
    with whatever WORKDIR, etc.). ``warehouse_path`` is kept for framework
    compatibility; an empty ``data/warehouse`` directory is fine.
    """
    global _server
    if _server is None:
        if Path.cwd() != _PROJECT_ROOT:
            logger.info(
                "pinning CWD to project root for Iceberg path resolution: %s",
                _PROJECT_ROOT,
            )
            os.chdir(_PROJECT_ROOT)
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
    """Drop the cached server instance. Used by tests.

    Calls ``server.shutdown()`` first so the persistent ``QueryEngine``
    closes its DuckDB connection and per-engine caches flush. Idempotent
    — safe to call on a server that never issued a query.
    """
    global _server, _tool_schemas
    if _server is not None:
        try:
            _server.shutdown()
        except Exception:  # pragma: no cover - defensive
            pass
    _server = None
    _tool_schemas = None


def _get_tool_schemas() -> dict[str, dict[str, Any]]:
    """Lazily build a {tool_name: input_schema} map from the MCP server."""
    global _tool_schemas
    if _tool_schemas is None:
        server = get_server()
        _tool_schemas = {
            t.name: t.input_schema for t in server.get_tools()
        }
    return _tool_schemas


def get_tool_openai_schema(tool_name: str) -> dict[str, Any] | None:
    """Return the OpenAI-compatible tool definition for a named MCP tool."""
    schemas = _get_tool_schemas()
    schema = schemas.get(tool_name)
    if schema is None:
        return None
    server = get_server()
    tool_def = next((t for t in server.get_tools() if t.name == tool_name), None)
    if tool_def is None:
        return None
    return {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": tool_def.description,
            "parameters": schema,
        },
    }


def _validate_args(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    """Validate and coerce tool arguments against the published schema.

    Coerces int-strings to int and float-strings to float where the
    schema expects those types. Unknown keys pass through because
    multiple callers inject internal keys (student_cip, loan_pct,
    student_major, intent_keywords) not in the published schema.
    """
    schemas = _get_tool_schemas()
    schema = schemas.get(tool)
    if schema is None:
        return args

    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    validated: dict[str, Any] = {}

    for key, value in args.items():
        prop_schema = properties.get(key)
        if prop_schema is None:
            validated[key] = value
            continue
        expected_type = prop_schema.get("type")

        if expected_type == "integer" and isinstance(value, str):
            stripped = value.strip()
            is_int = stripped.isdigit() or (
                stripped.startswith("-") and stripped[1:].isdigit()
            )
            if is_int:
                validated[key] = int(stripped)
                continue
            raise McpArgumentError(
                f"Argument {key!r} for tool {tool!r}: expected integer, "
                f"got non-numeric string {value!r}"
            )
        if expected_type == "number" and isinstance(value, str):
            try:
                validated[key] = float(value.strip())
                continue
            except ValueError:
                raise McpArgumentError(
                    f"Argument {key!r} for tool {tool!r}: expected number, "
                    f"got {value!r}"
                )
        validated[key] = value

    for req_key in required:
        if req_key not in validated:
            raise McpArgumentError(
                f"Missing required argument {req_key!r} for tool {tool!r}"
            )

    return validated


def call(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    """Invoke a named MCP handler by its public tool name.

    Validates arguments against the tool's published schema before
    dispatch. Each tool has a ``_handle_<name>`` method on the server.
    """
    validated = _validate_args(tool, args)
    server = get_server()
    handler_name = f"_handle_{tool}"
    handler = getattr(server, handler_name, None)
    if handler is None:
        raise AttributeError(f"MCP server has no handler for tool {tool!r}")
    result: dict[str, Any] = handler(validated)
    return result


async def call_async(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    """Async variant for use inside generate_with_tools_loop."""
    return await asyncio.to_thread(call, tool, args)
