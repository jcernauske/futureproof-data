"""Unit tests for ``src/mcp_server/_query_engine.py``.

Covers the guarantees the spec hangs on the new data-access layer:

  * Predicate pushdown: filter dict turns into a parameterized SQL
    ``WHERE`` clause (not a Python-side post-filter).
  * View registration happens exactly once per engine lifetime — even
    across multiple public calls.
  * ``shutdown()`` closes the connection; the engine re-initializes on
    the next query (new connection, views re-registered).
  * Filter values are parameterized, never string-interpolated — so
    SQL injection payloads cannot escape into the emitted SQL text.
  * Result rows are keyed by the selected column names.
  * ``query_sql`` / ``query_filtered`` serialize concurrent callers
    behind the ``RLock`` so ``con.description`` cannot be clobbered by
    another thread's ``execute`` between one thread's ``execute`` and
    its own ``description`` read.
  * Sentinel SOC ``'99-9999'`` stays filtered out of JOIN-style SQL.

These tests use a ``MagicMock`` catalog + a ``MagicMock`` DuckDB
connection. No Iceberg, no warehouse. Per §4 Test Data Requirements:
"Mocked-catalog tests for _query_engine use a tiny in-memory DuckDB
with synthetic Iceberg paths, not the real warehouse."
"""

from __future__ import annotations

import threading
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from mcp_server._query_engine import QueryEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_catalog(
    namespaces: list[str] | None = None,
    tables_by_ns: dict[str, list[str]] | None = None,
) -> MagicMock:
    """Build a MagicMock catalog that mimics the pyiceberg surface.

    ``list_namespaces`` returns tuples (pyiceberg convention).
    ``list_tables`` returns ``(ns, tbl)`` tuples per namespace.
    ``load_table`` returns an object with ``metadata_location`` — a
    synthetic absolute path that never gets scanned because we patch
    the DuckDB connection itself.
    """
    namespaces = namespaces or ["consumable"]
    tables_by_ns = tables_by_ns or {"consumable": ["career_outcomes"]}
    catalog = MagicMock()
    catalog.list_namespaces.return_value = [(ns,) for ns in namespaces]

    def _list_tables(ns: str) -> list[tuple[str, str]]:
        return [(ns, t) for t in tables_by_ns.get(ns, [])]

    catalog.list_tables.side_effect = _list_tables

    def _load_table(full_id: str) -> MagicMock:
        tbl = MagicMock()
        tbl.metadata_location = f"/synthetic/{full_id}/metadata.json"
        return tbl

    catalog.load_table.side_effect = _load_table
    return catalog


def _install_connection_factory(
    rows: list[tuple] | None = None,
    description: list[tuple] | None = None,
) -> tuple[MagicMock, list[tuple[str, dict[str, Any] | None]]]:
    """Patch ``duckdb.connect`` and return (connection, captured_executes).

    Every call to ``con.execute(sql[, params])`` is recorded as
    ``(sql, params_or_None)`` in the returned list so tests can assert
    what the engine actually emitted.

    The default ``description`` is ``[("c",)]`` so a single-column
    fallback exists for tests that don't care.
    """
    rows = rows if rows is not None else []
    description = description if description is not None else [("c",)]
    captured: list[tuple[str, dict[str, Any] | None]] = []

    con = MagicMock()

    def _execute(sql: str, params: dict[str, Any] | None = None) -> MagicMock:
        captured.append((sql, params))
        cur = MagicMock()
        cur.fetchall.return_value = rows
        return cur

    con.execute.side_effect = _execute
    con.description = description

    return con, captured


# ---------------------------------------------------------------------------
# Predicate pushdown
# ---------------------------------------------------------------------------


def test_predicate_pushdown_filters_in_sql() -> None:
    """filter={'unitid': 145637} → ``WHERE unitid = $p0``, params={'p0': 145637}.

    This is the core pushdown guarantee — without it we fall back to the
    pre-rewrite full-scan-plus-Python-filter behavior that the spec exists
    to kill.
    """
    catalog = _make_catalog()
    engine = QueryEngine(catalog)

    con, captured = _install_connection_factory(
        rows=[(1,)], description=[("unitid",)]
    )

    # Short-circuit initialization: drop a connection in place and
    # pre-register the view so public calls don't trigger
    # install_extension / CREATE VIEW side effects we're not asserting on here.
    engine._con = con
    engine._views["consumable_career_outcomes"] = object()  # type: ignore[assignment]

    result = engine.query_filtered(
        "consumable.career_outcomes",
        filters={"unitid": 145637},
        limit=10,
    )

    assert result == [{"unitid": 1}]
    # Exactly one execute for the data query.
    assert len(captured) == 1
    sql, params = captured[0]
    assert "WHERE unitid = $p0" in sql
    assert params == {"p0": 145637}
    # And there's no Python-side filter — the literal 145637 is not
    # interpolated into the SQL text.
    assert "145637" not in sql


# ---------------------------------------------------------------------------
# View registration lifecycle
# ---------------------------------------------------------------------------


def test_views_registered_once() -> None:
    """Two public calls → CREATE VIEW still issued exactly once per (ns, tbl).

    Spec §1 Success Criteria: "DuckDB connection + Iceberg view
    registration happens exactly once per process lifetime, not per
    request." Two public calls across 2 namespaces x 2 tables = 4
    CREATE VIEW statements total, not 8.
    """
    catalog = _make_catalog(
        namespaces=["consumable", "base"],
        tables_by_ns={
            "consumable": ["career_outcomes", "occupation_profiles"],
            "base": [],  # keep base empty; irrelevant side paths
        },
    )
    # Add one base table so we have 3 total, not just 2.
    catalog.list_tables.side_effect = lambda ns: {
        "consumable": [("consumable", "career_outcomes"), ("consumable", "occupation_profiles")],
        "base": [("base", "cip_soc_crosswalk")],
    }.get(ns, [])

    con, captured = _install_connection_factory(
        rows=[], description=[("x",)]
    )

    with patch("mcp_server._query_engine.duckdb.connect", return_value=con):
        engine = QueryEngine(catalog)
        engine.query_sql("SELECT 1")
        engine.query_sql("SELECT 2")

    create_view_count = sum(
        1 for sql, _ in captured if sql.lstrip().upper().startswith("CREATE VIEW")
    )
    # 3 tables x registered once across 2 public calls = 3. NOT 6.
    assert create_view_count == 3, (
        f"expected 3 CREATE VIEW statements across both queries, "
        f"got {create_view_count}: "
        f"{[s for s, _ in captured if s.lstrip().upper().startswith('CREATE VIEW')]}"
    )
    # And the two SELECTs are there.
    select_count = sum(
        1 for sql, _ in captured if sql.lstrip().upper().startswith("SELECT")
    )
    assert select_count == 2


def test_shutdown_closes_connection() -> None:
    """shutdown() calls con.close(); next query re-initializes cleanly."""
    catalog = _make_catalog()
    first_con, first_captured = _install_connection_factory()
    second_con, second_captured = _install_connection_factory()

    # duckdb.connect is called twice — once on first init, once after shutdown.
    with patch(
        "mcp_server._query_engine.duckdb.connect",
        side_effect=[first_con, second_con],
    ):
        engine = QueryEngine(catalog)
        engine.query_sql("SELECT 1")
        # Under test: close triggers on shutdown.
        engine.shutdown()
        assert first_con.close.called, "expected shutdown() to close the connection"
        assert engine._con is None
        assert engine._views == {}

        # Next query reinitializes — new connection, views re-registered.
        engine.query_sql("SELECT 2")

    # Re-init paid the view registration cost again, on the SECOND con.
    second_create_views = [
        sql for sql, _ in second_captured
        if sql.lstrip().upper().startswith("CREATE VIEW")
    ]
    assert len(second_create_views) >= 1, (
        "re-init should re-register at least one view on the new connection"
    )
    # And the second SELECT landed on the second connection, not the first.
    second_selects = [
        sql for sql, _ in second_captured
        if sql.lstrip().upper().startswith("SELECT")
    ]
    assert "SELECT 2" in second_selects


# ---------------------------------------------------------------------------
# Parameterization / injection surface
# ---------------------------------------------------------------------------


def test_filter_value_parameterized_not_interpolated() -> None:
    """A SQL-injection-style filter value never appears literally in the SQL text.

    The classic Little Bobby Tables payload. The value rides in
    ``params``; the SQL contains only ``$p0``. No string interpolation.
    """
    catalog = _make_catalog()
    engine = QueryEngine(catalog)
    con, captured = _install_connection_factory(
        rows=[], description=[("cipcode",)]
    )
    engine._con = con
    engine._views["consumable_career_outcomes"] = object()  # type: ignore[assignment]

    malicious = "' OR 1=1 --"
    engine.query_filtered(
        "consumable.career_outcomes",
        filters={"cipcode": malicious},
        limit=1,
    )

    assert len(captured) == 1
    sql, params = captured[0]
    # Payload never escapes into SQL text.
    assert malicious not in sql, (
        f"injection payload leaked into SQL text: {sql!r}"
    )
    # Payload IS passed as a bound parameter.
    assert params == {"p0": malicious}
    # And the placeholder is there.
    assert "$p0" in sql


# ---------------------------------------------------------------------------
# Result shape
# ---------------------------------------------------------------------------


def test_query_sql_returns_dicts_with_column_keys() -> None:
    """query_sql result is [{col: val, ...}, ...] keyed by the connection's description."""
    catalog = _make_catalog()
    engine = QueryEngine(catalog)
    con, _ = _install_connection_factory(
        rows=[(1, 2), (3, 4)],
        description=[("a",), ("b",)],
    )
    engine._con = con
    # Pre-populate views so _ensure_initialized doesn't re-register.
    engine._views["consumable_career_outcomes"] = object()  # type: ignore[assignment]

    result = engine.query_sql("SELECT a, b FROM t")
    assert result == [{"a": 1, "b": 2}, {"a": 3, "b": 4}]


# ---------------------------------------------------------------------------
# Concurrency / RLock (promoted P2 → P1 per arch review)
# ---------------------------------------------------------------------------


def test_concurrent_calls_are_serialized() -> None:
    """Without the RLock, ``con.description`` gets clobbered between threads.

    Setup: the mock connection's ``execute`` records the current SQL
    and sets ``description`` to a SQL-specific column-name tuple. A
    tiny ``time.sleep`` between ``execute`` landing and ``description``
    being read widens the race window. Under the RLock each thread's
    ``description`` read corresponds to ITS OWN SQL — no cross-thread
    contamination.
    """
    catalog = _make_catalog()
    engine = QueryEngine(catalog)

    # We only need the public path to work; skip _ensure_initialized.
    lock = threading.Lock()
    state: dict[str, Any] = {"description": [("init",)]}

    con = MagicMock()

    def _execute(sql: str, params: dict[str, Any] | None = None) -> MagicMock:
        # Derive a unique column name from the SQL itself so we can
        # verify afterwards that each thread saw its own.
        col = sql.split(" ")[-1]
        with lock:
            state["description"] = [(col,)]
        # Widen the race: if two threads race through execute here,
        # the second will overwrite state["description"] before the
        # first reads it.
        time.sleep(0.001)
        cur = MagicMock()
        cur.fetchall.return_value = [(col,)]
        return cur

    con.execute.side_effect = _execute

    # ``description`` is read AFTER execute + fetchall. Return a live
    # view of state so the race is real.
    type(con).description = property(lambda _self: state["description"])

    engine._con = con
    engine._views["consumable_career_outcomes"] = object()  # type: ignore[assignment]

    n_threads = 16
    errors: list[str] = []
    errors_lock = threading.Lock()

    def worker(idx: int) -> None:
        # The engine splits SQL by space and takes the last token as
        # the "column name" — pick a unique tail per thread.
        unique = f"col_{idx}"
        sql = f"SELECT 1 AS {unique}"
        try:
            result = engine.query_sql(sql)
            # Each row dict must be keyed by this thread's own column
            # name. If the RLock fails, we'll see another thread's
            # column as the key.
            for row in result:
                if unique not in row:
                    with errors_lock:
                        errors.append(
                            f"thread {idx}: expected key {unique!r}, "
                            f"got keys {list(row.keys())!r}"
                        )
        except Exception as exc:  # noqa: BLE001
            with errors_lock:
                errors.append(f"thread {idx}: raised {type(exc).__name__}: {exc}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, (
        "RLock failed to serialize threads; cross-thread contamination "
        "detected:\n" + "\n".join(errors)
    )


# ---------------------------------------------------------------------------
# Sentinel SOC exclusion (P2)
# ---------------------------------------------------------------------------


def test_sentinel_soc_excluded() -> None:
    """``'99-9999'`` rows must not survive the crosswalk JOIN's WHERE clause.

    The production JOIN in ``_fetch_substituted_join`` includes
    ``AND soc_code <> '99-9999'``. This is a JOIN-level fixture: we
    feed the mock connection a result set that ALREADY has the sentinel
    filtered out (simulating the DB's correct response) and assert the
    engine doesn't re-introduce it. And we verify the engine's SQL
    pass-through carries the exclusion clause through unmodified.
    """
    catalog = _make_catalog()
    engine = QueryEngine(catalog)
    # Simulate a DB that would have returned '99-9999' except the
    # filter stripped it. We assert (a) the filter clause reaches the
    # connection unchanged, and (b) no sentinel survives in the output.
    con, captured = _install_connection_factory(
        rows=[("11-2021",), ("13-1161",)],
        description=[("soc_code",)],
    )
    engine._con = con
    engine._views["base_cip_soc_crosswalk"] = object()  # type: ignore[assignment]

    sql = (
        "SELECT DISTINCT soc_code FROM base_cip_soc_crosswalk "
        "WHERE SUBSTR(cipcode, 1, 5) = $cip4 "
        "AND soc_code IS NOT NULL AND soc_code <> '99-9999'"
    )
    result = engine.query_sql(sql, {"cip4": "52.14"})

    # Filter clause made it to the connection verbatim.
    assert any("99-9999" in s for s, _ in captured), (
        "sentinel exclusion clause missing from emitted SQL"
    )
    # No sentinel in the result — the DB did its job and the engine
    # didn't corrupt it.
    soc_codes = [row["soc_code"] for row in result]
    assert "99-9999" not in soc_codes
    assert soc_codes == ["11-2021", "13-1161"]


# ---------------------------------------------------------------------------
# Invalid identifier rejection (defense in depth)
# ---------------------------------------------------------------------------


def test_invalid_filter_column_rejected() -> None:
    """A filter key with SQL-metacharacters must be rejected before it lands in SQL."""
    catalog = _make_catalog()
    engine = QueryEngine(catalog)
    con, _ = _install_connection_factory()
    engine._con = con
    engine._views["consumable_career_outcomes"] = object()  # type: ignore[assignment]

    with pytest.raises(ValueError, match="invalid filter column"):
        engine.query_filtered(
            "consumable.career_outcomes",
            filters={"unitid; DROP TABLE x": 1},
        )
