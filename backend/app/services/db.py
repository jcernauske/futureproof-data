"""Shared DuckDB connection for application-layer persistence.

Both ``builds.py`` and ``sessions.py`` write to the same DuckDB file
(``backend/data/futureproof.duckdb``). DuckDB allows only one write
connection per file — this module owns that connection and lock so
concurrent writes from different service modules don't collide.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import duckdb

from app.services.mcp_client import project_root

_conns: dict[Path, duckdb.DuckDBPyConnection] = {}
_conn_lock = threading.RLock()
_schema_initializers: list[Any] = []


def _db_path() -> Path:
    root = project_root() / "backend" / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root / "futureproof.duckdb"


def register_schema_initializer(fn: Any) -> None:
    _schema_initializers.append(fn)


def conn() -> duckdb.DuckDBPyConnection:
    with _conn_lock:
        path = _db_path()
        if path not in _conns:
            connection = duckdb.connect(str(path))
            for init_fn in _schema_initializers:
                init_fn(connection)
            _conns[path] = connection
        return _conns[path]


def execute(sql: str, params: list[Any] | None = None) -> list[tuple[Any, ...]]:
    with _conn_lock:
        return conn().execute(sql, params or []).fetchall()


def execute_one(sql: str, params: list[Any] | None = None) -> tuple[Any, ...] | None:
    with _conn_lock:
        return conn().execute(sql, params or []).fetchone()


def execute_write(sql: str, params: list[Any] | None = None) -> None:
    with _conn_lock:
        conn().execute(sql, params or [])


def get_lock() -> threading.RLock:
    return _conn_lock
