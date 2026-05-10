"""Tests for app.services.prefetch — speculative build prefetching."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.career import CareerBranch, CareerDescription, CareerOutcome
from app.services import prefetch


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
