"""Tests for the get_schools_for_career MCP tool.

Per spec ``docs/specs/feature-compare-schools-for-career.md`` §4 New
Tests Required (P0/P1/P2). Hits the real handler with a real DuckDB
in-memory connection seeded with a synthesized PCP fixture so the
windowed RANK() query, anchor in-place / append / absent paths, and
implicit NULL-stat drop are all exercised end-to-end against actual
SQL — no SQL string-matching, no over-mocking.

The MCP server's ``_get_query_engine()`` is patched to return a shim
whose ``query_sql(sql, params)`` runs against an in-memory DuckDB with
the synthesized fixture registered as ``consumable_program_career_paths``.
That mirrors the exact view name the brightsmith QueryEngine registers
in production (namespace + table name joined by underscore).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import duckdb

from mcp_server.futureproof_server import (
    SCHOOLS_FOR_CAREER_RESPONSE_FIELDS_HTTP,
    FutureProofMCPServer,
)


# ---------------------------------------------------------------------------
# Fixture rows
# ---------------------------------------------------------------------------
#
# Schema mirrors consumable.program_career_paths just deeply enough to
# satisfy the SELECT list inside _handle_get_schools_for_career. We
# fabricate three SOCs:
#
#   15-1252  — Software Developers, 12 rows spanning two CIPs
#              (11.0701 + 11.07 broad), three confidence tiers, three
#              states (CA, IN, WA). Drives the bulk of the suite.
#   29-1141  — Registered Nurses, single CIP 51.38, three rows.
#              Drives the by_cip_and_soc smoke test.
#   17-2199  — Engineers (the only-low-confidence SOC).
#              Drives the empty-after-filter test.

_PCP_COLUMNS = [
    "unitid",
    "institution_name",
    "institution_control",
    "state_abbr",
    "cipcode",
    "program_name",
    "soc_code",
    "occupation_title",
    "stat_ern",
    "stat_roi",
    "earnings_1yr_median",
    "net_price_annual",
    "cost_of_attendance_annual",
    "tuition_in_state",
    "tuition_out_of_state",
    # Spec: roi-net-lifetime-value followup ("apples-to-apples
    # leaderboard"). The handler SELECTs lifetime_earnings_15yr so the
    # residency adjustment can recompute roi_raw_multiplier and
    # stat_roi when home_state is provided.
    "lifetime_earnings_15yr",
    "overall_confidence",
    "confidence_tier_program",
    "match_quality",
]


def _row(**overrides) -> dict:
    earnings = overrides.get("earnings_1yr_median", 60000.0)
    base = {
        "unitid": 100000,
        "institution_name": "Test University",
        "institution_control": "Public",
        "state_abbr": "CA",
        "cipcode": "11.0701",
        "program_name": "Computer Science",
        "soc_code": "15-1252",
        "occupation_title": "Software Developers",
        "stat_ern": 7,
        "stat_roi": 7,
        "earnings_1yr_median": 60000.0,
        "net_price_annual": 18000.0,
        "cost_of_attendance_annual": 28000.0,
        "tuition_in_state": 9000.0,
        "tuition_out_of_state": 21000.0,
        # Auto-derive lifetime_earnings_15yr from earnings (matches the
        # Gold pipeline's closed-form constant 18.5989). Override
        # explicitly to test edge cases.
        "lifetime_earnings_15yr": (
            round(earnings * 18.5989, 2) if earnings is not None else None
        ),
        "overall_confidence": "high",
        "confidence_tier_program": "high",
        "match_quality": "full",
    }
    base.update(overrides)
    return base


# 12 rows for SOC 15-1252 with deterministic composite scores so
# ranking ordering is asserted exactly. Composite = (ern+roi)/2.
# Ranked by composite DESC, earnings DESC NULLS LAST, net_price ASC NULLS LAST.
_SOFTWARE_DEV_ROWS = [
    # composite 9.5 — top row
    _row(unitid=110001, institution_name="Top Tech",
         stat_ern=10, stat_roi=9, earnings_1yr_median=120000.0,
         net_price_annual=20000.0, state_abbr="CA",
         cipcode="11.0701", program_name="CS"),
    # composite 9.0 — second
    _row(unitid=110002, institution_name="Second Tech",
         stat_ern=9, stat_roi=9, earnings_1yr_median=110000.0,
         net_price_annual=22000.0, state_abbr="WA",
         cipcode="11.0701", program_name="CS"),
    # composite 8.5
    _row(unitid=110003, institution_name="Third Tech",
         stat_ern=9, stat_roi=8, earnings_1yr_median=95000.0,
         net_price_annual=18000.0, state_abbr="IN",
         cipcode="11.0701", program_name="CS"),
    # composite 8.0
    _row(unitid=110004, institution_name="Fourth Tech",
         stat_ern=8, stat_roi=8, earnings_1yr_median=85000.0,
         net_price_annual=15000.0, state_abbr="CA",
         cipcode="11.0701", program_name="CS"),
    # composite 7.5
    _row(unitid=110005, institution_name="Fifth Tech",
         stat_ern=8, stat_roi=7, earnings_1yr_median=78000.0,
         net_price_annual=14000.0, state_abbr="IN",
         cipcode="11.0701", program_name="CS"),
    # composite 7.0
    _row(unitid=110006, institution_name="Sixth Tech",
         stat_ern=7, stat_roi=7, earnings_1yr_median=70000.0,
         net_price_annual=12000.0, state_abbr="CA",
         cipcode="11.0701", program_name="CS"),
    # composite 6.5
    _row(unitid=110007, institution_name="Seventh Tech",
         stat_ern=7, stat_roi=6, earnings_1yr_median=65000.0,
         net_price_annual=11000.0, state_abbr="IN",
         cipcode="11.0701", program_name="CS"),
    # composite 6.0
    _row(unitid=110008, institution_name="Eighth Tech",
         stat_ern=6, stat_roi=6, earnings_1yr_median=60000.0,
         net_price_annual=10000.0, state_abbr="WA",
         cipcode="11.07", program_name="Computer & Info Sciences"),
    # composite 5.5
    _row(unitid=110009, institution_name="Ninth Tech",
         stat_ern=6, stat_roi=5, earnings_1yr_median=55000.0,
         net_price_annual=10000.0, state_abbr="CA",
         cipcode="11.0701", program_name="CS",
         overall_confidence="medium"),
    # composite 5.0
    _row(unitid=110010, institution_name="Tenth Tech",
         stat_ern=5, stat_roi=5, earnings_1yr_median=52000.0,
         net_price_annual=10000.0, state_abbr="IN",
         cipcode="11.0701", program_name="CS",
         overall_confidence="medium"),
    # composite 4.5
    _row(unitid=110011, institution_name="Eleventh Tech",
         stat_ern=5, stat_roi=4, earnings_1yr_median=48000.0,
         net_price_annual=10000.0, state_abbr="WA",
         cipcode="11.0701", program_name="CS",
         overall_confidence="medium",
         confidence_tier_program="low"),
    # composite 4.0 — low overall_confidence; filtered by default.
    _row(unitid=110012, institution_name="Twelfth Tech",
         stat_ern=4, stat_roi=4, earnings_1yr_median=44000.0,
         net_price_annual=10000.0, state_abbr="CA",
         cipcode="11.0701", program_name="CS",
         overall_confidence="low",
         confidence_tier_program="insufficient"),
    # partial_no_bls + medium overall_confidence + NULL stat_ern.
    # Implicit-drop test: should NEVER appear in rankings (NULL stat
    # excludes the row from the windowed query).
    _row(unitid=110013, institution_name="Implicit Drop Tech",
         stat_ern=None, stat_roi=8, earnings_1yr_median=None,
         net_price_annual=12000.0, state_abbr="CA",
         cipcode="11.0701", program_name="CS",
         overall_confidence="medium",
         match_quality="partial_no_bls"),
]

# 3 rows for SOC 29-1141 nursing — by_cip_and_soc test.
_NURSING_ROWS = [
    _row(unitid=200001, institution_name="Nursing College A",
         soc_code="29-1141", occupation_title="Registered Nurses",
         cipcode="51.38", program_name="Registered Nursing",
         stat_ern=8, stat_roi=8, earnings_1yr_median=72000.0,
         net_price_annual=15000.0),
    _row(unitid=200002, institution_name="Nursing College B",
         soc_code="29-1141", occupation_title="Registered Nurses",
         cipcode="51.38", program_name="Registered Nursing",
         stat_ern=7, stat_roi=7, earnings_1yr_median=68000.0,
         net_price_annual=14000.0),
    # Different CIP — should NOT appear when by_cip_and_soc filters to 51.38.
    _row(unitid=200003, institution_name="Nursing College C",
         soc_code="29-1141", occupation_title="Registered Nurses",
         cipcode="51.39", program_name="Practical Nursing",
         stat_ern=6, stat_roi=6, earnings_1yr_median=58000.0,
         net_price_annual=12000.0),
]

# 2 rows for SOC 17-2199 — both overall_confidence='low'.
# Drives test_empty_after_filter_with_drop_confidence_escape.
_ALL_LOW_ROWS = [
    _row(unitid=300001, institution_name="LowConf Eng A",
         soc_code="17-2199", occupation_title="Engineers, All Other",
         cipcode="14.0101", program_name="Engineering",
         stat_ern=4, stat_roi=4, overall_confidence="low",
         confidence_tier_program="low"),
    _row(unitid=300002, institution_name="LowConf Eng B",
         soc_code="17-2199", occupation_title="Engineers, All Other",
         cipcode="14.0101", program_name="Engineering",
         stat_ern=3, stat_roi=3, overall_confidence="low",
         confidence_tier_program="insufficient"),
]


_ALL_ROWS = _SOFTWARE_DEV_ROWS + _NURSING_ROWS + _ALL_LOW_ROWS


# ---------------------------------------------------------------------------
# DuckDB shim — real SQL execution, no Iceberg
# ---------------------------------------------------------------------------


class _DuckDBEngineShim:
    """Stand-in for QueryEngine.query_sql backed by an in-memory DuckDB.

    Registers the seed rows under the same view name the production
    QueryEngine would create for ``consumable.program_career_paths``
    (i.e. ``consumable_program_career_paths``), so the handler's SQL
    runs verbatim.
    """

    def __init__(self, rows: list[dict]) -> None:
        self._con = duckdb.connect(":memory:")
        # Build a typed table so NULL stat_ern stays NULL.
        cols_sql = ", ".join(
            [
                "unitid INTEGER",
                "institution_name VARCHAR",
                "institution_control VARCHAR",
                "state_abbr VARCHAR",
                "cipcode VARCHAR",
                "program_name VARCHAR",
                "soc_code VARCHAR",
                "occupation_title VARCHAR",
                "stat_ern INTEGER",
                "stat_roi INTEGER",
                "earnings_1yr_median DOUBLE",
                "net_price_annual DOUBLE",
                "cost_of_attendance_annual DOUBLE",
                "tuition_in_state DOUBLE",
                "tuition_out_of_state DOUBLE",
                "lifetime_earnings_15yr DOUBLE",
                "overall_confidence VARCHAR",
                "confidence_tier_program VARCHAR",
                "match_quality VARCHAR",
            ]
        )
        self._con.execute(
            f"CREATE TABLE consumable_program_career_paths ({cols_sql})"
        )
        if rows:
            placeholders = ", ".join(["?"] * len(_PCP_COLUMNS))
            insert_sql = (
                f"INSERT INTO consumable_program_career_paths "
                f"({', '.join(_PCP_COLUMNS)}) VALUES ({placeholders})"
            )
            for r in rows:
                self._con.execute(
                    insert_sql, [r.get(c) for c in _PCP_COLUMNS]
                )

    def query_sql(self, sql: str, params: dict | None = None) -> list[dict]:
        cur = self._con.execute(sql, params or {})
        rows = cur.fetchall()
        col_names = [d[0] for d in cur.description]
        return [dict(zip(col_names, r)) for r in rows]


def _make_server(rows: list[dict] | None = None) -> FutureProofMCPServer:
    """Construct a server with a fake QueryEngine seeded with rows."""
    server = FutureProofMCPServer.__new__(FutureProofMCPServer)
    server.warehouse_path = "/tmp/fake"
    server.catalog_path = "/tmp/fake.db"
    server.grounding_docs_path = None
    server.server_name = "test"
    server.formatter = None
    server.anomaly_checker = None
    server.system_prompt = None
    server._catalog = MagicMock()
    server._query_engine = _DuckDBEngineShim(
        rows if rows is not None else _ALL_ROWS
    )
    return server


# ===========================================================================
# P0 — by_soc happy path
# ===========================================================================


class TestBySocReturnsTopN:
    def test_by_soc_returns_top_n(self):
        """SOC with ≥10 high-confidence rows returns 10 ranked rows."""
        server = _make_server()
        result = server._handle_get_schools_for_career(
            {"mode": "by_soc", "soc_code": "15-1252", "limit": 10}
        )
        assert "error" not in result, result
        assert result["mode"] == "by_soc"
        assert result["soc_code"] == "15-1252"
        assert result["occupation_title"] == "Software Developers"
        assert len(result["rows"]) == 10
        # Strict descending composite — assert the rank monotonicity.
        ranks = [r["rank"] for r in result["rows"]]
        assert ranks == sorted(ranks)
        # Top row is unitid=110001 by composite 9.5.
        assert result["rows"][0]["unitid"] == 110001
        assert result["rows"][0]["rank"] == 1
        # No is_anchor rows since no anchor was supplied.
        assert all(not r["is_anchor"] for r in result["rows"])
        # total_qualifying_programs counts ALL post-filter rows in the
        # ranked universe (not just top-N). Rows 110001..110011 all pass
        # the default medium-confidence floor; 110012 (low) and 110013
        # (NULL stat_ern) are excluded.
        assert result["total_qualifying_programs"] == 11


# ===========================================================================
# P0 — by_cip_and_soc filtering
# ===========================================================================


class TestByCipAndSoc:
    def test_by_cip_and_soc_filters_to_anchor_program(self):
        """Only rows matching BOTH cipcode='51.38' AND soc='29-1141'."""
        server = _make_server()
        result = server._handle_get_schools_for_career(
            {
                "mode": "by_cip_and_soc",
                "cipcode": "51.38",
                "soc_code": "29-1141",
                "limit": 10,
            }
        )
        assert "error" not in result, result
        assert result["mode"] == "by_cip_and_soc"
        assert result["cipcode"] == "51.38"
        assert len(result["rows"]) == 2
        for row in result["rows"]:
            assert row["cipcode"] == "51.38"
            assert row["soc_code"] == "29-1141"
        # 51.39 (Practical Nursing) MUST NOT leak through.
        assert all(r["unitid"] != 200003 for r in result["rows"])
        assert result["program_name"] == "Registered Nursing"

    def test_by_cip_and_soc_requires_cipcode(self):
        """mode='by_cip_and_soc' without cipcode yields a structured error."""
        server = _make_server()
        result = server._handle_get_schools_for_career(
            {"mode": "by_cip_and_soc", "soc_code": "15-1252"}
        )
        assert "error" in result
        assert "cipcode" in result["error"].lower()


# ===========================================================================
# P0 — anchor handling
# ===========================================================================


class TestAnchorHandling:
    def test_anchor_appended_when_not_in_top_n(self):
        """Anchor below top-N is appended as N+1th row with absolute rank."""
        server = _make_server()
        # unitid 110007 is rank 7 (composite 6.5). With limit=3 it lands
        # below top-N.
        result = server._handle_get_schools_for_career(
            {
                "mode": "by_soc",
                "soc_code": "15-1252",
                "limit": 3,
                "build_unitid": 110007,
                "build_cipcode": "11.0701",
            }
        )
        assert "error" not in result, result
        assert len(result["rows"]) == 4  # 3 + appended anchor
        assert result["anchor_in_top_n"] is False
        # Top 3 are unitid 110001, 110002, 110003.
        assert [r["unitid"] for r in result["rows"][:3]] == [
            110001,
            110002,
            110003,
        ]
        anchor = result["rows"][-1]
        assert anchor["is_anchor"] is True
        assert anchor["unitid"] == 110007
        assert anchor["cipcode"] == "11.0701"
        # Absolute rank 7 — appended at the end with its real position.
        assert anchor["rank"] == 7
        # No false-positive anchors above the appended row.
        assert all(not r["is_anchor"] for r in result["rows"][:3])

    def test_anchor_in_place_when_in_top_n(self):
        """Anchor in top-N: exactly one is_anchor row, no duplicate appended."""
        server = _make_server()
        # unitid 110002 is rank 2. With limit=10 it lands inside top-N.
        result = server._handle_get_schools_for_career(
            {
                "mode": "by_soc",
                "soc_code": "15-1252",
                "limit": 10,
                "build_unitid": 110002,
                "build_cipcode": "11.0701",
            }
        )
        assert "error" not in result, result
        assert result["anchor_in_top_n"] is True
        anchor_rows = [r for r in result["rows"] if r["is_anchor"]]
        assert len(anchor_rows) == 1
        assert anchor_rows[0]["unitid"] == 110002
        assert anchor_rows[0]["rank"] == 2
        # No appended duplicate — total rows == limit.
        assert len(result["rows"]) == 10
        unitid_seen = [r["unitid"] for r in result["rows"]]
        assert unitid_seen.count(110002) == 1

    def test_no_anchor_renders_clean(self):
        """No build_* params → no anchor rows, no error."""
        server = _make_server()
        result = server._handle_get_schools_for_career(
            {"mode": "by_soc", "soc_code": "15-1252", "limit": 5}
        )
        assert "error" not in result, result
        assert result["anchor_in_top_n"] is False
        assert all(not r["is_anchor"] for r in result["rows"])


# ===========================================================================
# P0 — anchor estimated rank (Option A: per-request anchor estimator)
# ===========================================================================


class TestAnchorEstimatedRank:
    """When the anchor (unitid, cipcode) is absent from the filtered
    universe but the caller passed anchor_stat_ern + anchor_stat_roi,
    the handler counts higher-composite rows in `materialized` and
    returns the rank as `anchor_estimated_rank`.

    The seeded SOC 15-1252 universe under default min_confidence=medium
    contains composites: 9.5, 9.0, 8.5, 8.0, 7.5, 7.0, 6.5, 6.0, 5.5,
    5.0, 4.5 — 11 rows (the 4.0 'low' row + the NULL-stat row are
    filtered out).
    """

    def test_estimated_rank_for_unknown_anchor(self):
        server = _make_server()
        # Unknown unitid; stats 8/8 → composite 8.0. Higher composites:
        # 9.5, 9.0, 8.5 → 3 rows above. Estimated rank = 4.
        result = server._handle_get_schools_for_career(
            {
                "mode": "by_soc",
                "soc_code": "15-1252",
                "limit": 5,
                "build_unitid": 999999,
                "build_cipcode": "11.0701",
                "anchor_stat_ern": 8,
                "anchor_stat_roi": 8,
            }
        )
        assert "error" not in result, result
        assert result["anchor_estimated_rank"] == 4
        # No is_anchor row in payload — synthetic row is built client-side.
        assert all(not r["is_anchor"] for r in result["rows"])
        # Top-N untouched.
        assert len(result["rows"]) == 5
        assert result["rows"][0]["unitid"] == 110001

    def test_estimated_rank_skipped_when_anchor_in_universe(self):
        """When the (unitid, cipcode) IS in PCP, anchor_estimated_rank
        stays None — the existing append-anchor path handles it."""
        server = _make_server()
        result = server._handle_get_schools_for_career(
            {
                "mode": "by_soc",
                "soc_code": "15-1252",
                "limit": 3,
                "build_unitid": 110007,  # composite 6.5, in universe
                "build_cipcode": "11.0701",
                "anchor_stat_ern": 7,
                "anchor_stat_roi": 6,
            }
        )
        assert result["anchor_estimated_rank"] is None
        assert any(r["is_anchor"] for r in result["rows"])

    def test_estimated_rank_skipped_without_stats(self):
        """Anchor lookup misses + no stats provided → no estimate."""
        server = _make_server()
        result = server._handle_get_schools_for_career(
            {
                "mode": "by_soc",
                "soc_code": "15-1252",
                "limit": 5,
                "build_unitid": 999999,
                "build_cipcode": "11.0701",
            }
        )
        assert result["anchor_estimated_rank"] is None

    def test_estimated_rank_top_position_when_stats_dominant(self):
        """Stats 10/10 → composite 10.0, no rows higher → rank 1."""
        server = _make_server()
        result = server._handle_get_schools_for_career(
            {
                "mode": "by_soc",
                "soc_code": "15-1252",
                "limit": 5,
                "build_unitid": 999999,
                "build_cipcode": "11.0701",
                "anchor_stat_ern": 10,
                "anchor_stat_roi": 10,
            }
        )
        assert result["anchor_estimated_rank"] == 1

    def test_estimated_rank_bottom_position_when_stats_weak(self):
        """Stats 0/0 → no row beats it from below → rank = total + 1."""
        server = _make_server()
        result = server._handle_get_schools_for_career(
            {
                "mode": "by_soc",
                "soc_code": "15-1252",
                "limit": 5,
                "build_unitid": 999999,
                "build_cipcode": "11.0701",
                "anchor_stat_ern": 0,
                "anchor_stat_roi": 0,
            }
        )
        total = result["total_qualifying_programs"]
        assert result["anchor_estimated_rank"] == total + 1

    def test_estimated_rank_rejects_out_of_range_stats(self):
        """Out-of-range stats silently drop — no estimate, no error."""
        server = _make_server()
        result = server._handle_get_schools_for_career(
            {
                "mode": "by_soc",
                "soc_code": "15-1252",
                "limit": 5,
                "build_unitid": 999999,
                "build_cipcode": "11.0701",
                "anchor_stat_ern": 99,
                "anchor_stat_roi": 5,
            }
        )
        assert result["anchor_estimated_rank"] is None

    def test_estimated_rank_against_user_filtered_universe(self):
        """The rank counts against the same min_confidence-filtered
        universe, not the full table. Lowering the floor changes the
        denominator AND can change the rank (more rows to outrank)."""
        server = _make_server()
        # min_confidence='low' adds the composite=4.0 row, but it ranks
        # below 8.0 so the rank stays 4. Total grows from 11 to 12.
        result = server._handle_get_schools_for_career(
            {
                "mode": "by_soc",
                "soc_code": "15-1252",
                "limit": 5,
                "min_confidence": "low",
                "build_unitid": 999999,
                "build_cipcode": "11.0701",
                "anchor_stat_ern": 8,
                "anchor_stat_roi": 8,
            }
        )
        assert result["total_qualifying_programs"] == 12
        assert result["anchor_estimated_rank"] == 4


# ===========================================================================
# P0 — confidence filter + storage-only match_quality
# ===========================================================================


class TestConfidenceFilter:
    def test_low_confidence_rows_excluded_by_default(self):
        """Default min_confidence='medium' filters out 'low' rows."""
        server = _make_server()
        result = server._handle_get_schools_for_career(
            {"mode": "by_soc", "soc_code": "15-1252", "limit": 25}
        )
        assert "error" not in result, result
        # Row 110012 has overall_confidence='low' — must NOT appear.
        assert all(r["unitid"] != 110012 for r in result["rows"])
        for row in result["rows"]:
            assert row["overall_confidence"] in ("high", "medium")

    def test_returned_match_quality_values_are_storage_layer_only(self):
        """Returned match_quality is from the stored enum only.

        Replaces test_broad_cip_fallback_excluded_by_default per
        data-reviewer item 4 — broad-CIP substitution is a runtime
        property of get_career_paths, not a stored row attribute.
        """
        valid = {"full", "partial_no_onet", "partial_no_bls", "scorecard_only"}
        server = _make_server()
        result = server._handle_get_schools_for_career(
            {"mode": "by_soc", "soc_code": "15-1252", "limit": 25}
        )
        for row in result["rows"]:
            assert row["match_quality"] in valid, (
                f"unexpected match_quality {row['match_quality']!r} — "
                f"runtime substitution rows must not leak into PCP"
            )

    def test_partial_no_bls_dropped_by_implicit_stat_filter(self):
        """partial_no_bls + NULL stat_ern excluded by NULL-handling.

        Per data-reviewer item 5: even though the row passes the
        confidence floor, the WHERE stat_ern IS NOT NULL clause keeps
        it out of the windowed CTE.
        """
        server = _make_server()
        result = server._handle_get_schools_for_career(
            {"mode": "by_soc", "soc_code": "15-1252", "limit": 25}
        )
        # unitid 110013 is the partial_no_bls + NULL stat_ern row.
        assert all(r["unitid"] != 110013 for r in result["rows"])

    def test_empty_after_filter_with_drop_confidence_escape(self):
        """SOC with all-low rows: empty under default, populated under low."""
        server = _make_server()
        # Default medium filter: 17-2199 has only 'low' rows.
        empty = server._handle_get_schools_for_career(
            {"mode": "by_soc", "soc_code": "17-2199", "limit": 10}
        )
        assert "error" not in empty
        assert empty["rows"] == []
        assert empty["total_qualifying_programs"] == 0

        # Drop the floor — escape hatch.
        full = server._handle_get_schools_for_career(
            {
                "mode": "by_soc",
                "soc_code": "17-2199",
                "limit": 10,
                "min_confidence": "low",
            }
        )
        assert "error" not in full
        assert len(full["rows"]) == 2
        assert full["total_qualifying_programs"] == 2


# ===========================================================================
# P1 — additional filters
# ===========================================================================


class TestAdditionalFilters:
    def test_state_filter_applied(self):
        """state_abbr='IN' returns only IN rows (both modes)."""
        server = _make_server()
        result = server._handle_get_schools_for_career(
            {
                "mode": "by_soc",
                "soc_code": "15-1252",
                "limit": 25,
                "state_abbr": "IN",
            }
        )
        assert "error" not in result, result
        assert len(result["rows"]) > 0
        for row in result["rows"]:
            assert row["state_abbr"] == "IN"
        assert result["state_filter_applied"] == "IN"

    def test_limit_param_clamped(self):
        """limit=999 clamps to ≤25."""
        server = _make_server()
        result = server._handle_get_schools_for_career(
            {"mode": "by_soc", "soc_code": "15-1252", "limit": 999}
        )
        assert "error" not in result, result
        assert len(result["rows"]) <= 25

    def test_min_confidence_low_includes_all(self):
        """min_confidence='low' surfaces rows the default filter hides."""
        server = _make_server()
        default = server._handle_get_schools_for_career(
            {"mode": "by_soc", "soc_code": "15-1252", "limit": 25}
        )
        permissive = server._handle_get_schools_for_career(
            {
                "mode": "by_soc",
                "soc_code": "15-1252",
                "limit": 25,
                "min_confidence": "low",
            }
        )
        assert len(permissive["rows"]) > len(default["rows"])
        # The 'low' overall_confidence row IS in the permissive result.
        assert any(r["unitid"] == 110012 for r in permissive["rows"])

    def test_min_program_confidence_optional_filter(self):
        """min_program_confidence='medium' drops low/insufficient program tier.

        Per data-reviewer item 4: the second knob is independent of
        overall_confidence and threads through confidence_tier_program.
        """
        server = _make_server()
        # Use min_confidence=low so we see ALL rows that aren't filtered
        # by overall_confidence; then layer the program filter on top.
        result = server._handle_get_schools_for_career(
            {
                "mode": "by_soc",
                "soc_code": "15-1252",
                "limit": 25,
                "min_confidence": "low",
                "min_program_confidence": "medium",
            }
        )
        assert "error" not in result, result
        # unitid 110011 has confidence_tier_program='low' — should be dropped.
        assert all(r["unitid"] != 110011 for r in result["rows"])
        # unitid 110012 has confidence_tier_program='insufficient' — dropped.
        assert all(r["unitid"] != 110012 for r in result["rows"])
        # Returned rows have program tier in {high, medium}.
        for row in result["rows"]:
            assert row["confidence_tier_program"] in ("high", "medium")


# ===========================================================================
# P2 — wire-shape whitelist
# ===========================================================================


class TestResponseFieldWhitelist:
    def test_response_field_whitelist_no_pii_leak(self):
        """Returned rows contain only documented fields — no composite_score."""
        server = _make_server()
        result = server._handle_get_schools_for_career(
            {"mode": "by_soc", "soc_code": "15-1252", "limit": 5}
        )
        allowed = set(SCHOOLS_FOR_CAREER_RESPONSE_FIELDS_HTTP)
        for row in result["rows"]:
            extra = set(row.keys()) - allowed
            assert not extra, f"extraneous wire fields: {extra}"
            # composite_score is computed but MUST NOT cross the wire
            # (locks architect C3).
            assert "composite_score" not in row
            assert "abs_rank" not in row
