"""Perf + telemetry tests for ``_handle_get_career_paths``.

Covers the spec §1 Success Criteria that are observable in-process:

  * Permanent timing logs land in ``logs/mcp.jsonl`` with the contracted
    schema (``event``, ``duration_ms``, ``path``, ``unitid``, ``cipcode``).
  * ``_fetch_crosswalk_socs`` is LRU-cached; a repeat call is a hit.
  * A single substituted handler call does NOT exceed 4 Iceberg scans.
  * The standard-path outcomes cache is OFF by default and ON only with
    ``FUTUREPROOF_OUTCOMES_CACHE=1``.

All tests mock the data-access layer (``query_iceberg_simple``,
``_fetch_crosswalk_socs``, ``_fetch_substituted_join``) — they do NOT
hit the real Iceberg warehouse. The handler under test is exercised
by its real code path, not mocked.

Telemetry test uses ``monkeypatch`` to redirect ``_log_path()`` to a
tmp file so the assertion is isolated from the real repo-root
``logs/mcp.jsonl`` and from other running tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server import _telemetry
from mcp_server.futureproof_server import (
    CAREER_OUTCOMES_TABLE,
    FutureProofMCPServer,
    _career_paths_cache,
    _crosswalk_cache,
)


# ---------------------------------------------------------------------------
# Server + mock helpers (bypass BaseMCPServer.__init__, mirror test_cip_substitution.py)
# ---------------------------------------------------------------------------


_FAKE_LOOKUP = [
    {
        "major": "Marketing",
        "cip4": "52.14",
        "cip_family": "52",
        "aliases": ["marketing management", "mktg"],
    },
    {
        "major": "Biology",
        "cip4": "26.02",
        "cip_family": "26",
        "aliases": ["bio"],
    },
]


_IUB_CO_ROW = {
    "unitid": 151351,
    "institution_name": "Indiana University-Bloomington",
    "cipcode": "52.01",
    "program_name": "Business/Commerce, General.",
    "cip_family_name": "Business, Management, Marketing",
    "earnings_1yr_median": 63371.0,
    "earnings_1yr_p25": 38515.0,
    "earnings_1yr_p75": 49674.0,
    "debt_median": 19500.0,
    "debt_to_earnings_annual": 0.3077,
    "cip_family_earnings_rank": 0.9558,
    "confidence_tier": "high",
}


_JOIN_ROW = {
    "soc_code": "11-2021",
    "occupation_title": "Marketing Managers",
    "soc_major_group_name": "Management",
    "median_annual_wage": 161030.0,
    "wage_percentile_overall": 0.95,
    "grw_score_rounded": 7,
    "market_score_rounded": 8,
    "growth_category": "Faster than average",
    "employment_current": 400000,
    "education_level_name": "Bachelor's degree",
    "primary_title": "Marketing Managers",
    "hmn_score_rounded": 6,
    "burnout_score_rounded": 6,
    "top_5_activities": "[]",
    "top_human_activities": "[]",
    "burnout_drivers": "[]",
    "stat_res": 3,
    "boss_ai_score": 8,
}


def _make_server() -> FutureProofMCPServer:
    server = FutureProofMCPServer.__new__(FutureProofMCPServer)
    server.warehouse_path = "/tmp/fake"
    server.catalog_path = "/tmp/fake.db"
    server.grounding_docs_path = None
    server.server_name = "perf-test"
    server.formatter = None
    server.anomaly_checker = None
    server.system_prompt = None
    server._catalog = MagicMock()
    server._major_to_cip_cache = _FAKE_LOOKUP
    return server


def _fake_query_simple(table_name, filters=None, columns=None, limit=None):
    """Mirror ``test_cip_substitution._fake_query_simple`` for the school lookup."""
    filters = filters or {}
    if table_name == CAREER_OUTCOMES_TABLE:
        if filters.get("unitid") == 151351 and filters.get("cipcode") == "52.01":
            return [_IUB_CO_ROW]
    return []


def _clear_module_caches() -> None:
    """Drop all entries from the module-level LRUs.

    These caches are module-scoped so two tests can poison each other's
    hit/miss expectations if we don't clear between cases. Each test
    that reasons about cache state calls this at the top.
    """
    _crosswalk_cache.clear()
    _career_paths_cache.clear()


# ---------------------------------------------------------------------------
# Telemetry: timing log emission
# ---------------------------------------------------------------------------


def test_handler_emits_timing_log_with_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A substituted handler call writes one ``career_paths_handler`` line.

    Enforces the schema: ``event``, ``duration_ms`` (non-negative int),
    ``path`` (``"substituted"`` for this case), ``unitid``/``cipcode``
    echoing the input. Without these fields the telemetry contract in
    §4 is broken and regressions go undetected.
    """
    _clear_module_caches()
    log_file = tmp_path / "mcp.jsonl"

    # Two things must happen for the log to land in tmp_path:
    # 1. MCP_LOG_DISABLED must be UNSET (CI often sets it globally).
    # 2. _log_path() must resolve to our tmp path, not the repo root.
    monkeypatch.delenv("MCP_LOG_DISABLED", raising=False)
    monkeypatch.setattr(_telemetry, "_LOG_PATH_CACHED", log_file)

    server = _make_server()

    with patch.object(server, "_fetch_crosswalk_socs", return_value=["11-2021"]), \
         patch.object(server, "query_iceberg_simple", side_effect=_fake_query_simple), \
         patch.object(server, "_fetch_substituted_join", return_value=[_JOIN_ROW]):
        result = server._handle_get_career_paths(
            {
                "unitid": 151351,
                "cipcode": "52.01",
                "student_major": "Marketing",
            }
        )

    # Sanity: substituted path fired.
    assert result.get("substitution_applied") is True

    # Telemetry file was written.
    assert log_file.exists(), "telemetry log file was not created"
    lines = [json.loads(line) for line in log_file.read_text().splitlines() if line.strip()]
    handler_lines = [
        ln for ln in lines if ln.get("event") == "career_paths_handler"
    ]
    assert handler_lines, (
        f"no career_paths_handler line found; got events: "
        f"{[ln.get('event') for ln in lines]}"
    )

    # Contract fields — pick the most recent matching line.
    line = handler_lines[-1]
    assert line["path"] == "substituted", (
        f"expected path=substituted, got {line.get('path')!r}"
    )
    assert isinstance(line["duration_ms"], int), (
        f"duration_ms must be int, got {type(line['duration_ms']).__name__}"
    )
    assert line["duration_ms"] >= 0
    assert line["unitid"] == 151351
    assert line["cipcode"] == "52.01"


# ---------------------------------------------------------------------------
# LRU caching: crosswalk
# ---------------------------------------------------------------------------


def test_crosswalk_socs_lru_hit_on_repeat() -> None:
    """Second call to _fetch_crosswalk_socs("26.01") is an LRU hit.

    Asserted via the server's ``_last_crosswalk_cache_hit`` attribute,
    which the production helper sets on every call (hit or miss).
    """
    _clear_module_caches()
    server = _make_server()

    # Patch the engine's query_sql so we don't hit the real warehouse.
    # First call returns synthetic crosswalk rows; subsequent calls
    # should never reach the engine because the LRU short-circuits.
    fake_engine = MagicMock()
    fake_engine.query_sql.return_value = [
        {"soc_code": "19-1020"},
        {"soc_code": "19-1022"},
    ]

    with patch.object(server, "_get_query_engine", return_value=fake_engine):
        # First call — miss.
        first = server._fetch_crosswalk_socs("26.01")
        assert first == ["19-1020", "19-1022"]
        assert server._last_crosswalk_cache_hit is False
        first_call_count = fake_engine.query_sql.call_count
        assert first_call_count == 1

        # Second call — hit.
        second = server._fetch_crosswalk_socs("26.01")
        assert second == ["19-1020", "19-1022"]
        assert server._last_crosswalk_cache_hit is True
        # Engine was NOT hit a second time.
        assert fake_engine.query_sql.call_count == first_call_count, (
            "LRU hit should have short-circuited before reaching query_sql"
        )


# ---------------------------------------------------------------------------
# Scan-count budget: one substituted call should not exceed 4 underlying scans
# ---------------------------------------------------------------------------


def test_handler_does_not_exceed_4_iceberg_scans_substituted() -> None:
    """A single substituted handler call stays within the spec's ≤ 4 scan budget.

    Budget (per spec §1 Success Criteria): crosswalk (1) + school (1) +
    JOIN (1) + at most 1 more for edge paths. We spy on
    ``QueryEngine.query_filtered`` and ``QueryEngine.query_sql`` — the
    two entry points for every underlying Iceberg scan.
    """
    _clear_module_caches()
    server = _make_server()

    # Counter wrapping the two engine entry points. The real handler
    # uses the server's overrides (query_iceberg_simple delegates to
    # query_filtered; query_iceberg delegates to query_sql), so we
    # intercept at those overrides.
    scan_count = {"value": 0}

    def _count_simple(table_name, filters=None, columns=None, limit=None):
        scan_count["value"] += 1
        return _fake_query_simple(table_name, filters, columns, limit)

    def _count_join(cip4: str) -> list[dict]:
        scan_count["value"] += 1
        return [_JOIN_ROW]

    def _count_crosswalk(cip4: str) -> list[str]:
        scan_count["value"] += 1
        server._last_crosswalk_cache_hit = False
        return ["11-2021"]

    with patch.object(server, "query_iceberg_simple", side_effect=_count_simple), \
         patch.object(server, "_fetch_substituted_join", side_effect=_count_join), \
         patch.object(server, "_fetch_crosswalk_socs", side_effect=_count_crosswalk):
        result = server._handle_get_career_paths(
            {
                "unitid": 151351,
                "cipcode": "52.01",
                "student_major": "Marketing",
            }
        )

    assert result.get("substitution_applied") is True, (
        "test must exercise substituted path"
    )
    assert scan_count["value"] <= 4, (
        f"handler issued {scan_count['value']} underlying scans; spec budget is ≤ 4"
    )


# ---------------------------------------------------------------------------
# Standard-path outcomes cache — off by default, on with env flag
# ---------------------------------------------------------------------------


def test_outcomes_cache_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without ``FUTUREPROOF_OUTCOMES_CACHE`` set, repeat calls both miss the engine.

    The cache in ``_standard_path_rows`` is gated on the env flag. With
    the flag unset, every call must reach ``query_iceberg_simple`` —
    otherwise the env gate is broken (caching by default is a
    correctness hazard the spec deliberately avoids).
    """
    _clear_module_caches()
    monkeypatch.delenv("FUTUREPROOF_OUTCOMES_CACHE", raising=False)

    server = _make_server()
    # Pre-initialize the query engine so _standard_path_rows has a
    # stable engine id for the cache key (irrelevant with cache off,
    # but keeps the test setup consistent with the 'on' variant).
    server._query_engine = MagicMock()

    # Two identical calls; both should reach query_iceberg_simple.
    synthetic_row = {
        "soc_code": "11-2021",
        "occupation_title": "Marketing Managers",
        "stats_available_count": 5,
        "bosses_available_count": 4,
        "overall_confidence": 8,
    }

    call_count = {"value": 0}

    def _stub(table_name, filters=None, columns=None, limit=None):
        call_count["value"] += 1
        return [synthetic_row]

    with patch.object(server, "query_iceberg_simple", side_effect=_stub):
        server._standard_path_rows(151351, "52.14")
        server._standard_path_rows(151351, "52.14")

    assert call_count["value"] == 2, (
        f"cache was off but only {call_count['value']} scan(s) reached the engine; "
        f"default must be uncached"
    )
    assert server._last_career_paths_cache_hit is False


def test_outcomes_cache_on_with_env_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """With ``FUTUREPROOF_OUTCOMES_CACHE=1``, second call is a cache hit."""
    _clear_module_caches()
    monkeypatch.setenv("FUTUREPROOF_OUTCOMES_CACHE", "1")

    server = _make_server()
    # Fixed engine instance → stable id → stable cache key.
    server._query_engine = MagicMock()

    synthetic_row = {
        "soc_code": "11-2021",
        "occupation_title": "Marketing Managers",
        "stats_available_count": 5,
        "bosses_available_count": 4,
        "overall_confidence": 8,
    }

    call_count = {"value": 0}

    def _stub(table_name, filters=None, columns=None, limit=None):
        call_count["value"] += 1
        return [synthetic_row]

    with patch.object(server, "query_iceberg_simple", side_effect=_stub):
        first = server._standard_path_rows(151351, "52.14")
        assert server._last_career_paths_cache_hit is False
        assert call_count["value"] == 1

        second = server._standard_path_rows(151351, "52.14")
        assert server._last_career_paths_cache_hit is True, (
            "second identical call should have been a cache hit"
        )
        # Engine was NOT hit a second time.
        assert call_count["value"] == 1, (
            f"cache should have short-circuited; got {call_count['value']} total scans"
        )

    # Result shape preserved across cache layer.
    assert first[0]["soc_code"] == second[0]["soc_code"]
