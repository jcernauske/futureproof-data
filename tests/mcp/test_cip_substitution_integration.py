"""Integration tests for CIP intent substitution.

Exercises the full substitution pipeline against the real Iceberg
warehouse. Skipped automatically when the warehouse or catalog is not
present locally (CI / fresh checkouts). Validates the exact cases
called out in ``docs/specs/cip-intent-substitution.md``:

  * IU-B Marketing → Marketing-family SOCs
  * IU-B Accounting → Accounting-family SOCs
  * IU-B Finance → Finance-family SOCs
  * Substitution results for IU-B 52.14 match ISU 52.14 SOC sets
    (same crosswalk; different school earnings)
"""

from __future__ import annotations

from pathlib import Path

import pytest


from mcp_server.futureproof_server import FutureProofMCPServer


# IU-B only reports 52.01 (the broad business CIP) for business
# graduates, so it is the canonical case for substitution.
IUB_UNITID = 151351

# ISU (Indiana State) reports 52.14 directly, which provides a ground
# truth for comparing substituted SOC lists.
ISU_UNITID = 151801


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WAREHOUSE_PATH = PROJECT_ROOT / "data" / "warehouse"
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"


def _warehouse_available() -> bool:
    return WAREHOUSE_PATH.exists() and CATALOG_PATH.exists()


pytestmark = pytest.mark.skipif(
    not _warehouse_available(),
    reason="Iceberg warehouse not present; skipping integration tests",
)


@pytest.fixture(scope="module")
def server() -> FutureProofMCPServer:
    return FutureProofMCPServer(
        warehouse_path=str(WAREHOUSE_PATH),
        catalog_path=str(CATALOG_PATH),
        server_name="integration-test",
    )


def _call(server: FutureProofMCPServer, **kwargs) -> dict:
    return server._handle_get_career_paths(kwargs)


def _socs(result: dict) -> set[str]:
    return {r["soc_code"] for r in (result.get("data") or [])}


class TestIUBMarketing:
    """IU-B + cipcode 52.01 + 'Marketing' → 52.14 SOC set."""

    def test_substitution_fires(self, server):
        result = _call(
            server,
            unitid=IUB_UNITID,
            cipcode="52.01",
            student_major="Marketing",
        )
        assert result["substitution_applied"] is True
        assert result["reported_cipcode"] == "52.01"
        assert result["substituted_cipcode"] == "52.14"
        assert result["row_count"] > 0

    def test_marketing_soc_set(self, server):
        result = _call(
            server,
            unitid=IUB_UNITID,
            cipcode="52.01",
            student_major="Marketing",
        )
        socs = _socs(result)
        # Core Marketing-family SOCs from spike-intent-substitution.md.
        assert "11-2021" in socs  # Marketing Managers
        assert "13-1161" in socs  # Market Research Analysts
        # Generic management SOCs that appear under the BROKEN 52.01
        # path must NOT be in the substituted result.
        assert "11-9021" not in socs  # Construction Managers
        assert "11-3051" not in socs  # Industrial Production Managers
        assert "11-3013" not in socs  # Facilities Managers

    def test_blended_earnings_are_iub_broad(self, server):
        """Substituted rows carry IU-B's 52.01 earnings, not national."""
        result = _call(
            server,
            unitid=IUB_UNITID,
            cipcode="52.01",
            student_major="Marketing",
        )
        rows = result["data"]
        assert rows
        for row in rows:
            # Every substituted row shares the same school-level
            # earnings basis.
            assert row["earnings_1yr_median"] == rows[0]["earnings_1yr_median"]
            assert (
                row["debt_to_earnings_annual"]
                == rows[0]["debt_to_earnings_annual"]
            )
        # IU-B 52.01 earnings from the spike findings.
        assert abs(rows[0]["earnings_1yr_median"] - 63371.0) < 1.0

    def test_data_caveat_present(self, server):
        result = _call(
            server,
            unitid=IUB_UNITID,
            cipcode="52.01",
            student_major="Marketing",
        )
        caveat = result["data_caveat"]
        assert caveat["type"] == "blended_substitution"
        assert caveat["reported_cipcode"] == "52.01"
        assert caveat["substituted_cipcode"] == "52.14"

    def test_pentagon_completeness(self, server):
        """Most substituted rows should land a full 5-stat pentagon."""
        result = _call(
            server,
            unitid=IUB_UNITID,
            cipcode="52.01",
            student_major="Marketing",
        )
        rows = result["data"]
        full = sum(
            1
            for r in rows
            if all(
                r.get(k) is not None
                for k in ("stat_ern", "stat_roi", "stat_res", "stat_grw", "stat_hmn")
            )
        )
        # Spike measured 6/9 full pentagons → ~67%. Require at least
        # half.
        assert full >= len(rows) // 2


class TestIUBAccounting:
    def test_accounting_soc_set(self, server):
        result = _call(
            server,
            unitid=IUB_UNITID,
            cipcode="52.01",
            student_major="Accounting",
        )
        assert result["substitution_applied"] is True
        assert result["substituted_cipcode"] == "52.03"
        socs = _socs(result)
        # 13-2011 Accountants and Auditors is the defining Accounting
        # SOC.
        assert "13-2011" in socs


class TestIUBFinance:
    def test_finance_soc_set(self, server):
        result = _call(
            server,
            unitid=IUB_UNITID,
            cipcode="52.01",
            student_major="Finance",
        )
        assert result["substitution_applied"] is True
        assert result["substituted_cipcode"] == "52.08"
        socs = _socs(result)
        # 11-3031 Financial Managers is the defining Finance SOC.
        assert "11-3031" in socs


class TestIUBMarketing52_14_PaddedInput:
    """End-to-end against real Iceberg: the padded 6-digit broad CIP
    form ('52.0100') must produce the same substituted Marketing
    payload as the bare 4-digit form.

    This is the integration-level expression of Bug A: the backend
    would see padded input from Gemma/frontend and mis-filter
    career_outcomes (stored at 4-digit granularity) down to zero
    rows — user sees "missing crosswalk data" instead of Marketing
    careers. Mirrors TestIUBMarketing::test_substitution_fires with
    the padded input form.
    """

    def test_substitution_fires_with_52_0100(self, server):
        result = _call(
            server,
            unitid=IUB_UNITID,
            cipcode="52.0100",  # padded broad — Bug A target
            student_major="Marketing",
        )
        # Same invariants as the bare-4-digit case.
        assert result["substitution_applied"] is True
        # Response canonicalizes the reported cipcode to 4-digit, so
        # this is "52.01" even though we passed "52.0100".
        assert result["reported_cipcode"] == "52.01"
        assert result["substituted_cipcode"] == "52.14"
        assert result["row_count"] > 0
        # Caveat must carry the canonical reported cipcode too — dual
        # location (caveat + root) is §4 Decision #3.
        caveat = result["data_caveat"]
        assert caveat["type"] == "blended_substitution"
        assert caveat["reported_cipcode"] == "52.01"
        assert caveat["substituted_cipcode"] == "52.14"
        # Blended earnings must match what the bare-4-digit case gets —
        # same 52.01 row on IU's side.
        rows = result["data"]
        assert abs(rows[0]["earnings_1yr_median"] - 63371.0) < 1.0


class TestSpecificCipBypass:
    """A school that reports 52.14 directly should not be substituted."""

    def test_isu_52_14_direct_path(self, server):
        """ISU reports 52.14 directly; student_major is ignored."""
        result = _call(
            server,
            unitid=ISU_UNITID,
            cipcode="52.14",
            student_major="Marketing",
        )
        # Standard path should have run and ignored student_major.
        assert result.get("substitution_applied") is False
        # Either there are ISU 52.14 rows or the standard path returns
        # null — both are "no substitution" outcomes.
        if result.get("data"):
            # Standard rows use the reported cipcode as-is.
            for row in result["data"]:
                assert row["cipcode"] == "52.14"


class TestIUBMarketing52_14_BrokenContract:
    """Pins the backend behavior the *frontend* used to rely on and no
    longer does.

    Before the frontend fix, CareerPickScreen sent
    ``cipcode = intent.matched_cip = "52.14"`` to ``/build/outcomes`` for
    IU-B Marketing. The MCP handler saw a non-broad, non-prefix-child CIP
    and skipped substitution. The standard-path query found no IU 52.14
    rows, ``_fallback_broaden_cip`` dropped to the family prefix, and the
    response shipped every 52.* IU program — so the student saw
    accounting / finance / management careers instead of marketing.

    The frontend now sends ``parentCip = "52.01"`` for this flow
    (covered by TestIUBMarketing above). This test intentionally calls
    the handler with the *old* shape to document the backend's
    broaden-fallback behavior: if a future frontend refactor accidentally
    reverts to sending the matched leaf, we want a test that surfaces
    exactly what the user would see, so the regression is caught before
    a release rather than after.
    """

    def test_52_14_at_iub_falls_to_broaden_fallback(self, server):
        result = _call(
            server,
            unitid=IUB_UNITID,
            cipcode="52.14",
            student_major="Marketing",
        )
        # The fallback still reports substitution_applied (it's a kind
        # of substitution — broadening the caller's cip) but the caveat
        # shape is the broadening one, NOT the blended-major one.
        caveat = result.get("data_caveat") or {}
        assert caveat.get("type") == "cip_broadened", (
            "If this assertion flips to 'blended_substitution', the "
            "backend gained a self-healing path and the frontend no "
            "longer needs to route parentCip. Reconsider the fix."
        )
        # The row set is the family-broadened result — not the Marketing
        # crosswalk SOC set. 11-2021 (Marketing Managers) would be here
        # only if substitution had fired.
        socs = _socs(result)
        assert "11-2021" not in socs, (
            "Broaden-fallback surfaced a Marketing SOC; check whether "
            "IU now reports 52.14 directly or substitution changed."
        )
