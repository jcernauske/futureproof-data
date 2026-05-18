"""Tests for app.services.prefetch — speculative build prefetching."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.career import CareerBranch, CareerDescription, CareerOutcome
from app.services import prefetch, stat_engine


@pytest.fixture(autouse=True)
def _clean_cache():
    """Clear the prefetch cache before and after each test."""
    prefetch.clear_all()
    yield
    prefetch.clear_all()


def _fake_career() -> CareerOutcome:
    return MagicMock(spec=CareerOutcome, soc_code="13-1161")


def _fake_branch() -> CareerBranch:
    return MagicMock(spec=CareerBranch)


def _fake_description() -> CareerDescription:
    return MagicMock(spec=CareerDescription)


BASE_PARAMS = dict(
    unitid=151351,
    cipcode="52.1401",
    soc_code="13-1161",
    effort="balanced",
    loan_pct=0.5,
    student_major="Marketing",
    student_cip=None,
    home_state=None,
)


class TestMakeKey:
    def test_deterministic(self):
        k1 = prefetch.make_key(**BASE_PARAMS)
        k2 = prefetch.make_key(**BASE_PARAMS)
        assert k1 == k2

    def test_different_effort_different_key(self):
        k1 = prefetch.make_key(**BASE_PARAMS)
        k2 = prefetch.make_key(**{**BASE_PARAMS, "effort": "high"})
        assert k1 != k2

    def test_different_loan_pct_different_key(self):
        k1 = prefetch.make_key(**BASE_PARAMS)
        k2 = prefetch.make_key(**{**BASE_PARAMS, "loan_pct": 1.0})
        assert k1 != k2

    def test_different_soc_different_key(self):
        k1 = prefetch.make_key(**BASE_PARAMS)
        k2 = prefetch.make_key(**{**BASE_PARAMS, "soc_code": "11-2011"})
        assert k1 != k2


class TestStartAndConsume:
    @pytest.mark.asyncio
    async def test_consume_returns_prefetched_career(self):
        career = _fake_career()
        branches = [_fake_branch()]
        desc = _fake_description()

        with (
            patch(
                "app.services.prefetch.stat_engine.compute_one",
                return_value=career,
            ),
            patch(
                "app.services.prefetch.branch_tree.get_branches",
                return_value=branches,
            ),
            patch(
                "app.services.prefetch.career_description.get_or_generate",
                new_callable=AsyncMock,
                return_value=desc,
            ),
        ):
            key = prefetch.start(
                **BASE_PARAMS,
                occupation_title="Market research analysts",
            )
            result = await prefetch.consume(key)

        assert result is not None
        assert result.career is career
        assert result.branches == branches
        assert result.career_description is desc

    @pytest.mark.asyncio
    async def test_consume_removes_from_cache(self):
        with (
            patch(
                "app.services.prefetch.stat_engine.compute_one",
                return_value=_fake_career(),
            ),
            patch(
                "app.services.prefetch.branch_tree.get_branches",
                return_value=[],
            ),
        ):
            key = prefetch.start(**BASE_PARAMS)
            result1 = await prefetch.consume(key)
            result2 = await prefetch.consume(key)

        assert result1 is not None
        assert result2 is None

    @pytest.mark.asyncio
    async def test_consume_returns_none_when_no_entry(self):
        key = prefetch.make_key(**BASE_PARAMS)
        result = await prefetch.consume(key)
        assert result is None

    @pytest.mark.asyncio
    async def test_consume_returns_none_when_career_failed(self):
        with (
            patch(
                "app.services.prefetch.stat_engine.compute_one",
                side_effect=ValueError("no data"),
            ),
            patch(
                "app.services.prefetch.branch_tree.get_branches",
                return_value=[],
            ),
        ):
            key = prefetch.start(**BASE_PARAMS)
            result = await prefetch.consume(key)

        assert result is None

    @pytest.mark.asyncio
    async def test_mismatched_key_returns_none(self):
        with (
            patch(
                "app.services.prefetch.stat_engine.compute_one",
                return_value=_fake_career(),
            ),
            patch(
                "app.services.prefetch.branch_tree.get_branches",
                return_value=[],
            ),
        ):
            prefetch.start(**BASE_PARAMS)
            wrong_key = prefetch.make_key(
                **{**BASE_PARAMS, "effort": "high"},
            )
            result = await prefetch.consume(wrong_key)

        assert result is None


class TestInvalidate:
    @pytest.mark.asyncio
    async def test_invalidate_cancels_and_removes(self):
        async def _slow_compute(**kw):
            await asyncio.sleep(100)
            return _fake_career()

        with (
            patch(
                "app.services.prefetch.stat_engine.compute_one",
                side_effect=_slow_compute,
            ),
            patch(
                "app.services.prefetch.branch_tree.get_branches",
                return_value=[],
            ),
        ):
            key = prefetch.start(**BASE_PARAMS)
            removed = prefetch.invalidate(key)
            assert removed is True

            result = await prefetch.consume(key)
            assert result is None

    def test_invalidate_nonexistent_returns_false(self):
        key = prefetch.make_key(**BASE_PARAMS)
        assert prefetch.invalidate(key) is False


class TestDeduplication:
    @pytest.mark.asyncio
    async def test_start_deduplicates_inflight(self):
        call_count = 0

        def _counting_compute(**kw):
            nonlocal call_count
            call_count += 1
            return _fake_career()

        with (
            patch(
                "app.services.prefetch.stat_engine.compute_one",
                side_effect=_counting_compute,
            ),
            patch(
                "app.services.prefetch.branch_tree.get_branches",
                return_value=[],
            ),
        ):
            prefetch.start(**BASE_PARAMS)
            prefetch.start(**BASE_PARAMS)
            key = prefetch.start(**BASE_PARAMS)
            result = await prefetch.consume(key)

        assert result is not None
        assert call_count == 1


class TestExpiry:
    @pytest.mark.asyncio
    async def test_expired_entry_returns_none(self):
        with (
            patch(
                "app.services.prefetch.stat_engine.compute_one",
                return_value=_fake_career(),
            ),
            patch(
                "app.services.prefetch.branch_tree.get_branches",
                return_value=[],
            ),
        ):
            key = prefetch.start(**BASE_PARAMS)
            # Wait for task to complete
            await prefetch._cache[key].task

        # Simulate expiry
        prefetch._cache[key].created_at -= prefetch.TTL_SECONDS + 1

        result = await prefetch.consume(key)
        assert result is None


class TestClearAll:
    @pytest.mark.asyncio
    async def test_clear_all(self):
        with (
            patch(
                "app.services.prefetch.stat_engine.compute_one",
                return_value=_fake_career(),
            ),
            patch(
                "app.services.prefetch.branch_tree.get_branches",
                return_value=[],
            ),
        ):
            prefetch.start(**BASE_PARAMS)
            count = prefetch.clear_all()
            assert count == 1

            key = prefetch.make_key(**BASE_PARAMS)
            result = await prefetch.consume(key)
            assert result is None


# ---------------------------------------------------------------------------
# Bundle 6a: LookupError caught separately and logged at INFO
# (post-100-build-test-fixes-bundle §4)
#
# When stat_engine.compute_one raises LookupError because the
# (unitid, cipcode, soc) triple isn't in gold (e.g., a branch campus
# without the requested SOC in its catalog), prefetch must catch the
# exception and degrade gracefully. The build stream computes from
# scratch — prefetch is best-effort, not a hard dependency. Critically,
# the exception is logged at INFO level (not WARNING) with structured
# context — "soc_not_in_gold" is a known, benign cache-miss state, not
# a bug that should page the on-call.
# ---------------------------------------------------------------------------


class TestComputeOneLookupErrorCaught:
    """Verify LookupError in compute_one is caught and routed cleanly."""

    @pytest.mark.asyncio
    async def test_compute_one_lookup_error_caught(self):
        """compute_one raises LookupError → the prefetch task completes
        successfully (no exception propagates). result.error carries the
        exception string; result.career remains None.

        This proves the architect's A2 fix: LookupError is a *separate*
        except clause that doesn't escape and doesn't crash the gather.
        """
        with (
            patch(
                "app.services.prefetch.stat_engine.compute_one",
                side_effect=stat_engine.SOCNotInGold(
                    "(151351, 11.0701, 15-1252) not in gold"
                ),
            ),
            patch(
                "app.services.prefetch.branch_tree.get_branches",
                return_value=[],
            ),
        ):
            key = prefetch.start(**BASE_PARAMS)
            # If LookupError leaked past the except clause, awaiting the
            # underlying task here would re-raise. The whole point of
            # Bundle 6a is that this is silent.
            entry = prefetch._cache[key]
            result = await entry.task

        # The task completed (no exception). career is None because
        # compute_one raised; error is populated with the LookupError msg.
        assert result.career is None, (
            "career must be None when compute_one raises LookupError"
        )
        assert result.error is not None, (
            "result.error must carry the LookupError message so the "
            "caller can distinguish cache-miss from cache-hit"
        )
        assert "not in gold" in result.error

    @pytest.mark.asyncio
    async def test_compute_one_lookup_error_logged_at_info_not_warning(
        self, caplog
    ):
        """LookupError from compute_one must log at INFO with structured
        extra context. Logging at WARNING would cry wolf — soc_not_in_gold
        is a known benign state, not a bug."""
        import logging

        caplog.set_level(logging.DEBUG, logger="app.services.prefetch")

        with (
            patch(
                "app.services.prefetch.stat_engine.compute_one",
                side_effect=stat_engine.SOCNotInGold("benign cache miss"),
            ),
            patch(
                "app.services.prefetch.branch_tree.get_branches",
                return_value=[],
            ),
        ):
            key = prefetch.start(**BASE_PARAMS)
            await prefetch._cache[key].task

        # Find the prefetch_compute_one record.
        relevant = [
            r for r in caplog.records
            if r.name == "app.services.prefetch"
        ]
        info_records = [r for r in relevant if r.levelno == logging.INFO]
        warning_records = [
            r for r in relevant if r.levelno == logging.WARNING
        ]

        assert len(info_records) >= 1, (
            f"Expected at least one INFO log; got records "
            f"{[(r.levelname, r.message) for r in relevant]}"
        )
        # The structured extra carries call_site='prefetch_compute_one'.
        cache_miss_records = [
            r for r in info_records
            if getattr(r, "call_site", None) == "prefetch_compute_one"
        ]
        assert len(cache_miss_records) == 1, (
            "Expected exactly one INFO record tagged "
            "call_site='prefetch_compute_one'"
        )
        rec = cache_miss_records[0]
        # Structured context required for auditability.
        assert getattr(rec, "unitid", None) == BASE_PARAMS["unitid"]
        assert getattr(rec, "cipcode", None) == BASE_PARAMS["cipcode"]
        assert getattr(rec, "soc_code", None) == BASE_PARAMS["soc_code"]
        assert getattr(rec, "reason", None) == "soc_not_in_gold"

        # And — critically — NO warning was emitted for the LookupError.
        # (Branch-fetch logs WARNING on its own errors, but here we stubbed
        # branch_tree.get_branches to succeed, so any WARNING means the
        # LookupError leaked into the generic Exception clause.)
        lookup_warnings = [
            r for r in warning_records
            if "benign cache miss" in r.getMessage()
            or "compute_one" in r.getMessage()
        ]
        assert lookup_warnings == [], (
            f"LookupError must log at INFO, not WARNING. Got warning "
            f"records: {[r.getMessage() for r in lookup_warnings]}"
        )

    @pytest.mark.asyncio
    async def test_bare_lookup_error_still_logs_at_warning(self, caplog):
        """Code review F3 guard: a bare LookupError (e.g. a KeyError from
        a malformed gold row, since KeyError IS a LookupError subclass)
        must still log at WARNING, not get swallowed as a benign cache
        miss. Only SOCNotInGold — the explicit sentinel raised by
        stat_engine.compute_one when the (unitid, cipcode, soc) triple
        isn't in gold — is treated as benign.
        """
        import logging

        caplog.set_level(logging.DEBUG, logger="app.services.prefetch")

        with (
            patch(
                "app.services.prefetch.stat_engine.compute_one",
                side_effect=KeyError("malformed gold row missing 'unitid'"),
            ),
            patch(
                "app.services.prefetch.branch_tree.get_branches",
                return_value=[],
            ),
        ):
            key = prefetch.start(**BASE_PARAMS)
            await prefetch._cache[key].task

        prefetch_logs = [
            r for r in caplog.records
            if r.name == "app.services.prefetch"
        ]
        warning_records = [
            r for r in prefetch_logs if r.levelno == logging.WARNING
        ]
        # A bare KeyError (LookupError subclass) must surface as WARNING.
        # If a future refactor broadens the SOCNotInGold catch back to
        # bare LookupError, this assertion catches the regression.
        assert any(
            "compute_one failed" in r.getMessage() for r in warning_records
        ), (
            f"KeyError from a malformed gold row must log at WARNING, not "
            f"be swallowed as soc_not_in_gold. Got prefetch records: "
            f"{[(r.levelname, r.message) for r in prefetch_logs]}"
        )
