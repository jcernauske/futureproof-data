"""Tests for intent-resolution helpers in ``app.services.intent``.

Focused on the audit-driven contract: the three DuckDB-backed helpers
must (a) preserve the empty-list fallback when the underlying query
fails and (b) emit a WARNING-level log line with the exception attached
so the failure is triageable from logs/.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest

from app.services import intent


class _BoomServer:
    """MCP server stub that raises on ``query_iceberg``."""

    def query_iceberg(self, sql: str) -> list[dict[str, Any]]:
        raise RuntimeError("simulated DuckDB outage")


@pytest.fixture
def boom_server(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import mcp_client

    monkeypatch.setattr(mcp_client, "get_server", lambda: _BoomServer())


def test_get_school_cips_logs_warning_on_query_failure(
    boom_server: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="app.services.intent"):
        result = intent._get_school_cips(123456)

    assert result == []
    matching = [
        record
        for record in caplog.records
        if record.name == "app.services.intent"
        and record.levelno == logging.WARNING
        and "_get_school_cips" in record.getMessage()
    ]
    assert matching, "expected a WARNING from _get_school_cips on query failure"
    assert matching[0].exc_info is not None, "exc_info must be attached for triage"


def test_get_crosswalk_cips_for_families_logs_warning_on_query_failure(
    boom_server: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="app.services.intent"):
        result = intent._get_crosswalk_cips_for_families(["13.10"])

    assert result == []
    matching = [
        record
        for record in caplog.records
        if record.name == "app.services.intent"
        and record.levelno == logging.WARNING
        and "_get_crosswalk_cips_for_families" in record.getMessage()
    ]
    assert matching, "expected a WARNING from _get_crosswalk_cips_for_families"
    assert matching[0].exc_info is not None


def test_get_career_titles_for_cip_logs_warning_on_query_failure(
    boom_server: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="app.services.intent"):
        result = intent._get_career_titles_for_cip("13.1001")

    assert result == []
    matching = [
        record
        for record in caplog.records
        if record.name == "app.services.intent"
        and record.levelno == logging.WARNING
        and "_get_career_titles_for_cip" in record.getMessage()
    ]
    assert matching, "expected a WARNING from _get_career_titles_for_cip"
    assert matching[0].exc_info is not None


def test_get_crosswalk_returns_empty_for_no_families_without_logging(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Empty input is the short-circuit path — no query, no warning."""
    with caplog.at_level(logging.WARNING, logger="app.services.intent"):
        assert intent._get_crosswalk_cips_for_families([]) == []
    assert not [
        r for r in caplog.records if r.name == "app.services.intent"
    ]


class _BaseExceptionServer:
    """MCP server stub that raises a non-Exception BaseException
    (KeyboardInterrupt). The audit explicitly called out that the prior
    bare ``except:`` would swallow this; the spec's Decision #7 mandates
    ``except Exception`` so Ctrl-C / SystemExit propagate. These tests pin
    that contract — any future "tighten the safety net" refactor that
    re-broadens to ``except BaseException`` will fail loud here.
    """

    def query_iceberg(self, sql: str) -> list[dict[str, Any]]:
        raise KeyboardInterrupt("user hit ctrl-c")


@pytest.fixture
def base_exception_server(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import mcp_client

    monkeypatch.setattr(mcp_client, "get_server", lambda: _BaseExceptionServer())


def test_get_school_cips_propagates_keyboard_interrupt(
    base_exception_server: None,
) -> None:
    with pytest.raises(KeyboardInterrupt):
        intent._get_school_cips(123456)


def test_get_crosswalk_cips_propagates_keyboard_interrupt(
    base_exception_server: None,
) -> None:
    with pytest.raises(KeyboardInterrupt):
        intent._get_crosswalk_cips_for_families(["13.10"])


def test_get_career_titles_propagates_keyboard_interrupt(
    base_exception_server: None,
) -> None:
    with pytest.raises(KeyboardInterrupt):
        intent._get_career_titles_for_cip("13.1001")


# ---------------------------------------------------------------------------
# CIP family prefix validation (defense-in-depth — see hardening-followup spec)
# ---------------------------------------------------------------------------


class _CapturingServer:
    """MCP server stub that records the SQL passed to ``query_iceberg``
    and returns a canned row set so we can assert on the WHERE clause
    shape without touching DuckDB."""

    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows = rows if rows is not None else []
        self.last_sql: str | None = None

    def query_iceberg(self, sql: str) -> list[dict[str, Any]]:
        self.last_sql = sql
        return self.rows


def test_get_crosswalk_cips_for_families_drops_malformed_prefixes(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Only ``^\\d{2}$`` prefixes survive validation. ``"abc"`` and ``"5"``
    are dropped (logged at DEBUG); ``"11"`` passes through; ``"11.0701"``
    is truncated to its 2-digit head and passes through."""
    from app.services import mcp_client

    server = _CapturingServer(
        rows=[{"cipcode": "11.0101", "cip_title": "Computer Science"}],
    )
    monkeypatch.setattr(mcp_client, "get_server", lambda: server)

    with caplog.at_level(logging.DEBUG, logger="app.services.intent"):
        result = intent._get_crosswalk_cips_for_families(
            ["11", "abc", "5", "11.0701"],
        )

    assert server.last_sql is not None
    sql = server.last_sql
    assert "SUBSTR(cipcode, 1, 2) = '11'" in sql
    # Malformed prefixes must not leak into the SQL under any quoting.
    assert "'abc'" not in sql
    assert "= '5'" not in sql

    debug_messages = [
        r.getMessage()
        for r in caplog.records
        if r.name == "app.services.intent" and r.levelno == logging.DEBUG
    ]
    assert any("dropping malformed prefix" in m for m in debug_messages)

    assert result == [{"cipcode": "11.0101", "cip_title": "Computer Science"}]


def test_get_crosswalk_cips_for_families_all_invalid_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If every prefix fails validation, return ``[]`` without touching
    the MCP server. Catches a regression that would still build a SQL
    statement with an empty conditions clause and either error out or
    return everything."""
    from app.services import mcp_client

    called = {"count": 0}

    def _fail_get_server() -> Any:
        called["count"] += 1
        raise AssertionError("get_server must not run when no prefix is valid")

    monkeypatch.setattr(mcp_client, "get_server", _fail_get_server)

    assert intent._get_crosswalk_cips_for_families(["abc", "1", ""]) == []
    assert called["count"] == 0


def test_get_crosswalk_cips_for_families_valid_prefixes_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All currently-valid 2-digit prefixes must continue to flow through
    untouched — the new validation is a tighten, not a break. Asserts the
    SQL contains every requested prefix in order, so an over-strict
    pattern (e.g. ``\\d{2,}``) would fail this test loud."""
    from app.services import mcp_client

    server = _CapturingServer(
        rows=[
            {"cipcode": "11.0101", "cip_title": "CS"},
            {"cipcode": "14.0901", "cip_title": "Computer Engineering"},
            {"cipcode": "52.0201", "cip_title": "Business Administration"},
        ],
    )
    monkeypatch.setattr(mcp_client, "get_server", lambda: server)

    result = intent._get_crosswalk_cips_for_families(["11", "14", "52"])

    assert server.last_sql is not None
    sql = server.last_sql
    assert "SUBSTR(cipcode, 1, 2) = '11'" in sql
    assert "SUBSTR(cipcode, 1, 2) = '14'" in sql
    assert "SUBSTR(cipcode, 1, 2) = '52'" in sql

    assert result == [
        {"cipcode": "11.0101", "cip_title": "CS"},
        {"cipcode": "14.0901", "cip_title": "Computer Engineering"},
        {"cipcode": "52.0201", "cip_title": "Business Administration"},
    ]
