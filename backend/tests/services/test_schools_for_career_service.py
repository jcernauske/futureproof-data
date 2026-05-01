"""Tests for the schools_for_career service.

Per spec ``docs/specs/feature-compare-schools-for-career.md`` §4 New
Tests Required (P0). The service is a thin shaper around
``mcp_client.call("get_schools_for_career", ...)``: every test below
mocks ``mcp_client.call`` and asserts on (a) the dispatched args and
(b) the response validation. ``test_service_does_not_open_duckdb``
locks architect C1 by reading the module source and confirming no
direct DuckDB import.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.models.career import (
    AnchorBuild,
    SchoolsForCareerResponse,
)
from app.services import mcp_client, schools_for_career


def _good_response_dict(
    *,
    mode: str = "by_soc",
    cipcode: str | None = None,
    program_name: str | None = None,
) -> dict:
    """Minimal valid raw response payload (matches SchoolsForCareerResponse)."""
    return {
        "mode": mode,
        "soc_code": "15-1252",
        "occupation_title": "Software Developers",
        "cipcode": cipcode,
        "program_name": program_name,
        "rows": [
            {
                "rank": 1,
                "unitid": 110001,
                "institution_name": "Top Tech",
                "institution_control": "Public",
                "state_abbr": "CA",
                "cipcode": cipcode or "11.0701",
                "program_name": program_name or "Computer Science",
                "soc_code": "15-1252",
                "occupation_title": "Software Developers",
                "stat_ern": 9,
                "stat_roi": 9,
                "earnings_1yr_median": 120000.0,
                "net_price_annual": 20000.0,
                "cost_of_attendance_annual": 30000.0,
                "tuition_in_state": 9000.0,
                "tuition_out_of_state": 21000.0,
                "overall_confidence": "high",
                "confidence_tier_program": "high",
                "match_quality": "full",
                "is_anchor": False,
            }
        ],
        "anchor_in_top_n": False,
        "total_qualifying_programs": 11,
        "confidence_filter_applied": "medium",
        "state_filter_applied": None,
        "min_program_confidence_applied": "low",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ===========================================================================
# P0 — composite formula dispatch + response validation
# ===========================================================================


class TestCompositeScoreDispatch:
    def test_composite_score_formula_via_mcp_dispatch(self, monkeypatch):
        """Service passes the documented args + validates into the model.

        Validates: (a) the service calls ``mcp_client.call`` with
        ``"get_schools_for_career"``, (b) the args dict carries every
        knob the user passed (mode, soc_code, limit, min_confidence,
        min_program_confidence, state_abbr, build_unitid, build_cipcode),
        and (c) the raw response is parsed into ``SchoolsForCareerResponse``.
        """
        captured: dict = {}

        def fake_call(tool: str, args: dict) -> dict:
            captured["tool"] = tool
            captured["args"] = dict(args)
            return _good_response_dict()

        monkeypatch.setattr(mcp_client, "call", fake_call)

        result = schools_for_career.rank_schools_for_career(
            mode="by_soc",
            soc_code="15-1252",
            limit=10,
            min_confidence="medium",
            min_program_confidence="medium",
            state_abbr="CA",
            anchor=AnchorBuild(unitid=110001, cipcode="11.0701"),
        )

        assert isinstance(result, SchoolsForCareerResponse)
        assert result.mode == "by_soc"
        assert result.rows[0].unitid == 110001
        assert result.total_qualifying_programs == 11

        # Dispatch contract.
        assert captured["tool"] == "get_schools_for_career"
        args = captured["args"]
        assert args["mode"] == "by_soc"
        assert args["soc_code"] == "15-1252"
        assert args["limit"] == 10
        assert args["min_confidence"] == "medium"
        assert args["min_program_confidence"] == "medium"
        assert args["state_abbr"] == "CA"
        assert args["build_unitid"] == 110001
        assert args["build_cipcode"] == "11.0701"

    def test_error_field_raises_value_error(self, monkeypatch):
        """An MCP-side error response surfaces as ValueError."""
        def fake_call(tool: str, args: dict) -> dict:
            return {"error": "soc_code must be in XX-XXXX format"}

        monkeypatch.setattr(mcp_client, "call", fake_call)

        with pytest.raises(ValueError, match="XX-XXXX"):
            schools_for_career.rank_schools_for_career(
                mode="by_soc", soc_code="bogus"
            )


# ===========================================================================
# P0 — mode dispatches correct args
# ===========================================================================


class TestModeDispatchesCorrectArgs:
    def test_mode_dispatches_correct_args(self, monkeypatch):
        """by_soc and by_cip_and_soc differ only in mode and cipcode."""
        captures: list[dict] = []

        def fake_call(tool: str, args: dict) -> dict:
            captures.append(dict(args))
            mode = args.get("mode", "by_soc")
            cip = args.get("cipcode")
            return _good_response_dict(
                mode=mode,
                cipcode=cip if mode == "by_cip_and_soc" else None,
                program_name="Computer Science"
                if mode == "by_cip_and_soc"
                else None,
            )

        monkeypatch.setattr(mcp_client, "call", fake_call)

        # by_soc — no cipcode dispatched
        schools_for_career.rank_schools_for_career(
            mode="by_soc",
            soc_code="15-1252",
            limit=5,
        )
        assert captures[0]["mode"] == "by_soc"
        assert "cipcode" not in captures[0]

        # by_cip_and_soc — cipcode dispatched
        schools_for_career.rank_schools_for_career(
            mode="by_cip_and_soc",
            soc_code="15-1252",
            cipcode="11.0701",
            limit=5,
        )
        assert captures[1]["mode"] == "by_cip_and_soc"
        assert captures[1]["cipcode"] == "11.0701"

        # Same other knobs — confirm they round-tripped identically.
        assert captures[0]["soc_code"] == captures[1]["soc_code"]
        assert captures[0]["limit"] == captures[1]["limit"]

    def test_by_cip_and_soc_without_cipcode_raises(self, monkeypatch):
        """Service rejects by_cip_and_soc with no cipcode before dispatch."""
        called = {"value": False}

        def fake_call(tool, args):
            called["value"] = True
            return _good_response_dict()

        monkeypatch.setattr(mcp_client, "call", fake_call)

        with pytest.raises(ValueError, match="cipcode is required"):
            schools_for_career.rank_schools_for_career(
                mode="by_cip_and_soc",
                soc_code="15-1252",
            )
        assert called["value"] is False


# ===========================================================================
# P0 — service must not open DuckDB (architect C1)
# ===========================================================================


class TestAnchorEstimatedRankDispatch:
    def test_anchor_stats_threaded_through_to_mcp(self, monkeypatch):
        """anchor_stat_ern + anchor_stat_roi land in the MCP args dict."""
        captured: dict = {}

        def fake_call(tool: str, args: dict) -> dict:
            captured["args"] = dict(args)
            payload = _good_response_dict()
            payload["anchor_estimated_rank"] = 31
            return payload

        monkeypatch.setattr(mcp_client, "call", fake_call)

        result = schools_for_career.rank_schools_for_career(
            mode="by_soc",
            soc_code="13-1161",
            anchor=AnchorBuild(unitid=151351, cipcode="52.01"),
            anchor_stat_ern=8,
            anchor_stat_roi=7,
        )

        assert captured["args"]["anchor_stat_ern"] == 8
        assert captured["args"]["anchor_stat_roi"] == 7
        assert result.anchor_estimated_rank == 31

    def test_anchor_stats_omitted_when_not_provided(self, monkeypatch):
        """No anchor_stat_* keys in the args dict when caller omits them."""
        captured: dict = {}

        def fake_call(tool: str, args: dict) -> dict:
            captured["args"] = dict(args)
            return _good_response_dict()

        monkeypatch.setattr(mcp_client, "call", fake_call)

        schools_for_career.rank_schools_for_career(
            mode="by_soc",
            soc_code="15-1252",
        )
        assert "anchor_stat_ern" not in captured["args"]
        assert "anchor_stat_roi" not in captured["args"]


class TestServiceDoesNotOpenDuckDB:
    def test_service_module_does_not_import_duckdb(self):
        """The service file must not import duckdb at module level."""
        spec = importlib.util.find_spec("app.services.schools_for_career")
        assert spec is not None and spec.origin is not None
        source = Path(spec.origin).read_text()
        # No duckdb import — neither `import duckdb` nor `from duckdb`.
        assert "import duckdb" not in source
        assert "from duckdb" not in source

    def test_service_does_not_call_mcp_get_server(self, monkeypatch):
        """rank_schools_for_career must not reach into mcp_client.get_server.

        The MCP boundary is the canonical reader; the service must
        round-trip through ``mcp_client.call`` only. Patching
        ``get_server`` to raise verifies the service never touches it.
        """
        def explode():
            raise AssertionError(
                "service called mcp_client.get_server — architect C1 violated"
            )

        monkeypatch.setattr(mcp_client, "get_server", explode)
        # Patch call so the test doesn't try to actually reach DuckDB.
        monkeypatch.setattr(
            mcp_client, "call", lambda tool, args: _good_response_dict()
        )

        result = schools_for_career.rank_schools_for_career(
            mode="by_soc",
            soc_code="15-1252",
            limit=5,
        )
        assert isinstance(result, SchoolsForCareerResponse)
