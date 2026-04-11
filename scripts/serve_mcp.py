#!/usr/bin/env python
"""Hackathon MCP server launcher — bypasses /bs:serve manifest loader.

The framework's ``/bs:serve`` entrypoint currently cannot start against
this project because of two Brightsmith bugs tracked in the
``mcp-futureproof-core`` spec (see the KNOWN BLOCKER section):

1. ``domain_loader.py`` hard-requires singular ``table:`` in
   ``domain/sources/*.yaml``, but ``onet.yaml`` uses ``tables:`` for its
   multi-table source.
2. ``_load_zone_registry()`` expects a flat ``pipeline.silver.module``
   shape, but this project's ``domain/manifest.yaml`` uses the nested
   list-of-steps shape that multi-source domains produce naturally.

This script sidesteps both issues by instantiating
``FutureProofMCPServer`` directly. The MCP tool handlers query Gold
Iceberg tables via ``query_iceberg_simple()`` and do not depend on the
manifest loader or zone registry, so the full 8-tool surface works
exactly as it would under ``/bs:serve``.

Usage::

    uv run python scripts/serve_mcp.py

Environment variables:

    BRIGHTSMITH_PROJECT_ROOT
        Optional. When unset, the script assumes the project root is
        the directory containing this file's parent (i.e., run from the
        repo root). Set it explicitly if you need to launch the server
        from a different working directory.

    FUTUREPROOF_WAREHOUSE
        Optional. Path to the Iceberg warehouse. Defaults to
        ``data/warehouse`` under the project root.

    FUTUREPROOF_CATALOG
        Optional. Path to the SQLite catalog. Defaults to
        ``data/catalog.db`` under the project root.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path


def main() -> None:
    # Resolve the project root. This file lives at
    # ``<project_root>/scripts/serve_mcp.py``.
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent

    # Let Brightsmith's config module pick up the project root before
    # any brightsmith imports happen.
    os.environ.setdefault("BRIGHTSMITH_PROJECT_ROOT", str(project_root))

    # Ensure the domain ``src`` directory is importable. ``conftest.py``
    # handles this for pytest; we mirror the same trick here for
    # runtime launches.
    src_dir = project_root / "src"
    if src_dir.is_dir() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    logging.basicConfig(
        level=os.environ.get("FUTUREPROOF_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger("futureproof.serve_mcp")

    warehouse_path = Path(
        os.environ.get("FUTUREPROOF_WAREHOUSE", project_root / "data" / "warehouse")
    )
    catalog_path = Path(
        os.environ.get("FUTUREPROOF_CATALOG", project_root / "data" / "catalog.db")
    )

    # Import after sys.path / env vars are in place.
    from mcp_server.futureproof_server import FutureProofMCPServer

    server = FutureProofMCPServer(
        warehouse_path=warehouse_path,
        catalog_path=catalog_path,
        server_name="futureproof",
    )

    tool_names = [t.name for t in server._all_tools()]
    logger.info(
        "FutureProof MCP server starting with %d tools: %s",
        len(tool_names),
        ", ".join(tool_names),
    )
    logger.info("Warehouse: %s", warehouse_path)
    logger.info("Catalog:   %s", catalog_path)

    # BaseMCPServer.serve() is an async stdio entrypoint.
    asyncio.run(server.serve())


if __name__ == "__main__":
    main()
