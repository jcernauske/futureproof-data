"""Persistent DuckDB connection with cached Iceberg views.

The brightsmith base helpers (``query_iceberg_simple`` and
``query_iceberg``) rebuild the DuckDB world on every call — installing
and loading the Iceberg extension, walking the whole catalog, and
creating a view per table. That setup cost dominates the MCP request
budget. This module owns a process-lifetime connection that pays
those costs exactly once, exposes a predicate-pushdown helper that
turns Python filters into SQL WHERE clauses, and exposes a thin SQL
pass-through for JOINs against the registered views.

Thread-safety: ``query_filtered`` and ``query_sql`` acquire
``self._lock`` (a ``threading.RLock``) for the entirety of the
``execute`` / ``fetchall`` / ``con.description`` read. DuckDB's Python
connection serializes independent statements internally, but
``con.description`` is NOT atomic relative to a concurrent ``execute``
from another thread. Under parallel ``asyncio.to_thread`` handlers
(FastAPI's default) the result is silent column-name corruption.
The lock cost is negligible at hackathon request rates; an ``RLock``
is used so ``_ensure_initialized`` can recurse safely if future
registration logic is factored that way.
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass
from typing import Any

import duckdb

from mcp_server._telemetry import timed

logger = logging.getLogger(__name__)

# Max clamp for query_filtered limit. Callers typically pass much less;
# this is a defensive belt-and-suspenders against accidental
# unbounded scans.
_MAX_LIMIT = 1_000_000

# Column / table identifiers are validated against this strict pattern
# before being interpolated into SQL. We never interpolate VALUES — only
# identifiers — and identifiers must be known-safe.
_IDENT_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass
class _ViewRegistration:
    """One Iceberg table registered as a DuckDB view."""

    namespace: str
    table: str
    view_name: str  # f"{namespace}_{table}"
    metadata_location: str  # absolute path to current metadata.json


def _namespace_view_name(namespace: str, table: str) -> str:
    return f"{namespace}_{table}"


class QueryEngine:
    """Persistent DuckDB connection with cached Iceberg views.

    Lazy-initialized on first query. Process-lifetime; closed only via
    explicit ``shutdown()`` (used by tests and ``mcp_client.reset_server``).
    """

    def __init__(self, catalog: Any) -> None:
        self._catalog = catalog
        self._con: duckdb.DuckDBPyConnection | None = None
        self._views: dict[str, _ViewRegistration] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _ensure_initialized(self) -> duckdb.DuckDBPyConnection:
        """Open the DuckDB connection and register Iceberg views once."""
        with self._lock:
            if self._con is not None:
                return self._con
            con = duckdb.connect()
            con.install_extension("iceberg")
            con.load_extension("iceberg")
            for ns_tuple in self._catalog.list_namespaces():
                ns = ns_tuple[0] if isinstance(ns_tuple, tuple) else ns_tuple
                try:
                    tables = self._catalog.list_tables(ns)
                except Exception:
                    continue
                for table_id in tables:
                    tbl_name = table_id[1] if isinstance(table_id, tuple) else table_id
                    view_name = _namespace_view_name(ns, tbl_name)
                    full_id = f"{ns}.{tbl_name}"
                    try:
                        iceberg_table = self._catalog.load_table(full_id)
                        metadata_path = iceberg_table.metadata_location
                        con.execute(
                            f"CREATE VIEW IF NOT EXISTS {view_name} AS "
                            f"SELECT * FROM iceberg_scan("
                            f"'{metadata_path}')"
                        )
                        self._views[view_name] = _ViewRegistration(
                            namespace=ns,
                            table=tbl_name,
                            view_name=view_name,
                            metadata_location=metadata_path,
                        )
                    except Exception as exc:
                        logger.warning(
                            "skipping %s during view registration: %s",
                            full_id,
                            exc,
                            exc_info=True,
                        )
            self._con = con
            return con

    def shutdown(self) -> None:
        """Close the DuckDB connection. Idempotent."""
        with self._lock:
            if self._con is None:
                return
            try:
                self._con.close()
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("DuckDB close failed: %s", exc)
            self._con = None
            self._views.clear()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @timed(
        "query_filtered",
        extract=lambda result, self, table_name, *a, **kw: {
            "table": table_name,
            "row_count": len(result) if isinstance(result, list) else 0,
        },
    )
    def query_filtered(
        self,
        table_name: str,
        filters: dict[str, Any] | None = None,
        columns: list[str] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Predicate-pushdown query against a registered Iceberg view.

        ``table_name`` is the full ``namespace.table`` identifier (e.g.
        ``"consumable.career_outcomes"``); it is mapped to the
        ``{namespace}_{table}`` view registered at init.
        ``filters`` become a parameterized SQL ``WHERE`` clause pushed
        into DuckDB. ``columns`` is Python-side projection only:
        callers may request columns that don't exist on the table
        (brightsmith's base helper tolerates that via ``row.get(k)``)
        and missing keys surface as ``None``. Returns at most ``limit``
        rows.
        """
        view_name = self._view_name_for(table_name)
        limit = max(0, min(int(limit), _MAX_LIMIT))

        if columns:
            for c in columns:
                if not _IDENT_PATTERN.match(c):
                    raise ValueError(f"invalid column identifier: {c!r}")

        where_parts: list[str] = []
        params: dict[str, Any] = {}
        if filters:
            for i, (col, val) in enumerate(filters.items()):
                if not _IDENT_PATTERN.match(col):
                    raise ValueError(f"invalid filter column: {col!r}")
                param_name = f"p{i}"
                where_parts.append(f"{col} = ${param_name}")
                params[param_name] = val
        where_clause = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""

        sql = f"SELECT * FROM {view_name}{where_clause} LIMIT {limit}"

        # Hold the lock continuously from init through execute so a
        # concurrent shutdown() cannot close ``con`` between the two
        # windows. Safe nested acquire: ``self._lock`` is an RLock.
        with self._lock:
            con = self._ensure_initialized()
            cur = con.execute(sql, params) if params else con.execute(sql)
            rows = cur.fetchall()
            col_names = [d[0] for d in con.description]
        dicts = [dict(zip(col_names, r)) for r in rows]
        if columns:
            # Project in Python. Missing columns become None — matches
            # brightsmith's base helper contract of ``row.get(col)``.
            return [{k: r.get(k) for k in columns} for r in dicts]
        return dicts

    @timed(
        "query_sql",
        extract=lambda result, *a, **kw: {
            "row_count": len(result) if isinstance(result, list) else 0,
        },
    )
    def query_sql(
        self,
        sql: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Run parameterized SQL against the registered Iceberg views.

        ``params`` keys are referenced as ``$name`` in the SQL.
        """
        # Hold the lock continuously from init through execute so a
        # concurrent shutdown() cannot close ``con`` mid-query. RLock
        # makes the nested acquire in ``_ensure_initialized`` safe.
        with self._lock:
            con = self._ensure_initialized()
            if params:
                cur = con.execute(sql, params)
            else:
                cur = con.execute(sql)
            rows = cur.fetchall()
            col_names = [d[0] for d in con.description]
        return [dict(zip(col_names, r)) for r in rows]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _view_name_for(self, table_name: str) -> str:
        """Translate ``namespace.table`` → ``namespace_table`` view name."""
        if "." not in table_name:
            # Already a view name; trust it but validate.
            if not _IDENT_PATTERN.match(table_name):
                raise ValueError(f"invalid table name: {table_name!r}")
            return table_name
        ns, tbl = table_name.split(".", 1)
        if not (_IDENT_PATTERN.match(ns) and _IDENT_PATTERN.match(tbl)):
            raise ValueError(f"invalid table name: {table_name!r}")
        return _namespace_view_name(ns, tbl)
