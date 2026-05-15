"""Tests for the careers router (peer-school leaderboard endpoints).

Per spec ``docs/specs/feature-compare-schools-for-career.md`` §4 New
Tests Required (P0/P1). Mocks the service layer so the routes are
tested in isolation: regex validation, anchor normalization, and the
empty-SOC fallback.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models.career import (
    AnchorBuild,
    CareerDescription,
    SchoolForCareerRow,
    SchoolsForCareerResponse,
)
from app.routers import careers as careers_router
from app.services.career_description import CareerDescriptionUnavailable

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _row(**overrides) -> SchoolForCareerRow:
    base: dict = {
        "rank": 1,
        "unitid": 110001,
        "institution_name": "Top Tech",
        "institution_control": "Public",
        "state_abbr": "CA",
        "cipcode": "11.0701",
        "program_name": "Computer Science",
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
    base.update(overrides)
    return SchoolForCareerRow(**base)


def _response(
    *,
    mode: str,
    cipcode: str | None,
    program_name: str | None,
    rows: list[SchoolForCareerRow],
    total: int,
) -> SchoolsForCareerResponse:
    return SchoolsForCareerResponse(
        mode=mode,  # type: ignore[arg-type]
        soc_code="15-1252",
        occupation_title="Software Developers",
        cipcode=cipcode,
        program_name=program_name,
        rows=rows,
        anchor_in_top_n=False,
        total_qualifying_programs=total,
        confidence_filter_applied="medium",
        state_filter_applied=None,
        min_program_confidence_applied="low",
        generated_at=datetime.now(timezone.utc),
    )


# ===========================================================================
# P0 — by_soc happy path
# ===========================================================================


class TestBySocEndpointHappyPath:
    def test_by_soc_endpoint_happy_path(self, client, monkeypatch):
        captured: dict = {}

        def fake_rank(**kwargs):
            captured.update(kwargs)
            return _response(
                mode="by_soc",
                cipcode=None,
                program_name=None,
                rows=[_row()],
                total=11,
            )

        monkeypatch.setattr(careers_router, "rank_schools_for_career", fake_rank)

        resp = client.get(
            "/careers/15-1252/schools",
            params={
                "build_unitid": 110001,
                "build_cipcode": "11.0701",
                "limit": 5,
            },
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["mode"] == "by_soc"
        assert body["soc_code"] == "15-1252"
        assert body["occupation_title"] == "Software Developers"
        assert body["cipcode"] is None
        assert body["program_name"] is None
        assert isinstance(body["rows"], list)
        assert len(body["rows"]) == 1
        assert body["rows"][0]["unitid"] == 110001
        assert body["total_qualifying_programs"] == 11

        # Service was dispatched with the right contract.
        assert captured["mode"] == "by_soc"
        assert captured["soc_code"] == "15-1252"
        assert captured["limit"] == 5
        assert isinstance(captured["anchor"], AnchorBuild)
        assert captured["anchor"].unitid == 110001
        assert captured["anchor"].cipcode == "11.0701"


# ===========================================================================
# P0 — by_cip_and_soc happy path
# ===========================================================================


class TestByCipAndSocEndpointHappyPath:
    def test_by_cip_and_soc_endpoint_happy_path(self, client, monkeypatch):
        captured: dict = {}

        def fake_rank(**kwargs):
            captured.update(kwargs)
            return _response(
                mode="by_cip_and_soc",
                cipcode="51.38",
                program_name="Registered Nursing",
                rows=[_row(cipcode="51.38",
                          soc_code="29-1141",
                          occupation_title="Registered Nurses",
                          program_name="Registered Nursing",
                          unitid=200001,
                          institution_name="Nursing College A")],
                total=2,
            )

        monkeypatch.setattr(careers_router, "rank_schools_for_career", fake_rank)

        resp = client.get(
            "/majors/51.38/schools/for-career/29-1141",
            params={"build_unitid": 200001},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["mode"] == "by_cip_and_soc"
        assert body["cipcode"] == "51.38"
        assert body["program_name"] == "Registered Nursing"

        assert captured["mode"] == "by_cip_and_soc"
        assert captured["cipcode"] == "51.38"
        assert captured["soc_code"] == "29-1141"
        # build_unitid alone (no build_cipcode) → no anchor.
        assert captured["anchor"] is None


# ===========================================================================
# P0 — invalid cipcode rejected by FastAPI Path regex
# ===========================================================================


class TestInvalidCipcodeFormat:
    def test_invalid_cipcode_format_rejected(self, client, monkeypatch):
        # Service should never be reached.
        called = {"value": False}

        def trap(**kwargs):
            called["value"] = True
            raise AssertionError("service called despite 422")

        monkeypatch.setattr(careers_router, "rank_schools_for_career", trap)

        resp = client.get("/majors/11/schools/for-career/15-1252")
        assert resp.status_code == 422
        assert called["value"] is False

    def test_short_cipcode_three_digits_rejected(self, client, monkeypatch):
        """Two-character cipcode ``11.0`` slips no further than the
        Path regex either."""
        monkeypatch.setattr(
            careers_router,
            "rank_schools_for_career",
            lambda **kw: pytest.fail("service must not be called"),
        )
        resp = client.get("/majors/11.0/schools/for-career/15-1252")
        assert resp.status_code == 422


# ===========================================================================
# P0 — unknown SOC returns 200 with empty rows
# ===========================================================================


class TestUnknownSocEmpty:
    def test_unknown_soc_returns_empty(self, client, monkeypatch):
        def fake_rank(**kwargs):
            return _response(
                mode="by_soc",
                cipcode=None,
                program_name=None,
                rows=[],
                total=0,
            )

        monkeypatch.setattr(careers_router, "rank_schools_for_career", fake_rank)

        resp = client.get("/careers/99-9999/schools")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["rows"] == []
        assert body["total_qualifying_programs"] == 0
        assert body["anchor_in_top_n"] is False


# ===========================================================================
# P1 — partial anchor params
# ===========================================================================


class TestAnchorPartiallyProvided:
    def test_anchor_only_partially_provided(self, client, monkeypatch):
        """build_unitid only (no build_cipcode) must not 422.

        With the current router signature, ``build_unitid`` and
        ``build_cipcode`` are independent query params. Partial-anchor
        is normalized inside ``_maybe_anchor`` to ``None`` and the
        request still resolves to 200.
        """
        captured: dict = {}

        def fake_rank(**kwargs):
            captured.update(kwargs)
            return _response(
                mode="by_soc",
                cipcode=None,
                program_name=None,
                rows=[_row()],
                total=11,
            )

        monkeypatch.setattr(careers_router, "rank_schools_for_career", fake_rank)

        # unitid present, cipcode absent.
        resp = client.get(
            "/careers/15-1252/schools",
            params={"build_unitid": 110001},
        )
        assert resp.status_code == 200, resp.text
        assert captured["anchor"] is None

        # cipcode present, unitid absent.
        captured.clear()
        resp = client.get(
            "/careers/15-1252/schools",
            params={"build_cipcode": "11.0701"},
        )
        assert resp.status_code == 200, resp.text
        assert captured["anchor"] is None


# ===========================================================================
# P1 — anchor stat query params (Option A: per-request anchor estimator)
# ===========================================================================


class TestAnchorStatsQueryParams:
    def test_anchor_stats_dispatched_to_service(self, client, monkeypatch):
        """anchor_stat_ern + anchor_stat_roi reach the service kwargs."""
        captured: dict = {}

        def fake_rank(**kwargs):
            captured.update(kwargs)
            payload = _response(
                mode="by_soc",
                cipcode=None,
                program_name=None,
                rows=[_row()],
                total=962,
            )
            payload.anchor_estimated_rank = 31
            return payload

        monkeypatch.setattr(careers_router, "rank_schools_for_career", fake_rank)

        resp = client.get(
            "/careers/13-1161/schools",
            params={
                "build_unitid": 151351,
                "build_cipcode": "52.01",
                "anchor_stat_ern": 8,
                "anchor_stat_roi": 7,
            },
        )

        assert resp.status_code == 200, resp.text
        assert captured["anchor_stat_ern"] == 8
        assert captured["anchor_stat_roi"] == 7
        assert resp.json()["anchor_estimated_rank"] == 31

    def test_anchor_stat_out_of_range_rejected(self, client, monkeypatch):
        """Stats outside 0-10 are rejected by FastAPI Query before dispatch."""
        monkeypatch.setattr(
            careers_router,
            "rank_schools_for_career",
            lambda **kw: pytest.fail("service must not be called"),
        )

        resp = client.get(
            "/careers/13-1161/schools",
            params={"anchor_stat_ern": 99, "anchor_stat_roi": 5},
        )
        assert resp.status_code == 422

        resp = client.get(
            "/careers/13-1161/schools",
            params={"anchor_stat_ern": -1, "anchor_stat_roi": 5},
        )
        assert resp.status_code == 422

    def test_anchor_stats_omitted_when_query_absent(self, client, monkeypatch):
        """Service kwargs default to None when query params aren't present."""
        captured: dict = {}

        def fake_rank(**kwargs):
            captured.update(kwargs)
            return _response(
                mode="by_soc",
                cipcode=None,
                program_name=None,
                rows=[_row()],
                total=11,
            )

        monkeypatch.setattr(careers_router, "rank_schools_for_career", fake_rank)

        resp = client.get("/careers/15-1252/schools")
        assert resp.status_code == 200
        assert captured["anchor_stat_ern"] is None
        assert captured["anchor_stat_roi"] is None


# ===========================================================================
# P0 — GET /careers/{soc_code}/description
# (feature-career-description-on-pdf.md §4 New Tests Required)
# ===========================================================================


def _career_description(
    *,
    soc: str = "13-2051",
    anchor_tier: str = "activities",
) -> CareerDescription:
    return CareerDescription(
        soc_code=soc,
        summary=(
            "Financial analysts study filings and market data to guide "
            "investment decisions. They assemble models and brief managers."
        ),
        tasks=[
            "Analyze company filings",
            "Assemble valuation models",
            "Brief portfolio managers",
            "Read industry reports",
            "Track positions after recommendations",
        ],
        anchor_tier=anchor_tier,  # type: ignore[arg-type]
        generated_at="2026-05-07T00:00:00+00:00",
        model="gemma-4-26b-a4b-it",
    )


class TestCareerDescriptionEndpoint:
    def test_get_career_description_endpoint_happy(self, client, monkeypatch):
        """Happy path: service returns a valid CareerDescription → 200 +
        the JSON-serialized payload.
        """
        captured: dict = {}

        async def fake_service(soc_code: str, occupation_title: str, locale=None):
            captured["soc"] = soc_code
            captured["title"] = occupation_title
            return _career_description(soc=soc_code)

        monkeypatch.setattr(
            careers_router.career_description_service,
            "get_or_generate",
            fake_service,
        )

        resp = client.get(
            "/careers/13-2051/description",
            params={"occupation_title": "Financial and Investment Analysts"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["soc_code"] == "13-2051"
        assert body["anchor_tier"] == "activities"
        assert isinstance(body["tasks"], list)
        assert 4 <= len(body["tasks"]) <= 6
        assert body["summary"]
        # Service was dispatched with the path SOC + query title.
        assert captured["soc"] == "13-2051"
        assert captured["title"] == "Financial and Investment Analysts"

    def test_get_career_description_endpoint_unavailable(
        self, client, monkeypatch,
    ):
        """Service raises CareerDescriptionUnavailable → endpoint maps to 502."""

        async def raising_service(soc_code: str, occupation_title: str, locale=None):
            raise CareerDescriptionUnavailable(
                "two consecutive Gemma failures",
            )

        monkeypatch.setattr(
            careers_router.career_description_service,
            "get_or_generate",
            raising_service,
        )

        resp = client.get(
            "/careers/13-2051/description",
            params={"occupation_title": "Financial and Investment Analysts"},
        )
        assert resp.status_code == 502, resp.text
        body = resp.json()
        assert body["detail"] == "career_description_unavailable"

    def test_get_career_description_endpoint_invalid_soc(
        self, client, monkeypatch,
    ):
        """Malformed SOC fails the FastAPI Path regex → 422 BEFORE the
        service is invoked.
        """
        called = {"value": False}

        async def trap(soc_code: str, occupation_title: str, locale=None):
            called["value"] = True
            raise AssertionError("service called despite 422")

        monkeypatch.setattr(
            careers_router.career_description_service,
            "get_or_generate",
            trap,
        )

        resp = client.get(
            "/careers/13205/description",  # missing the dash + 4-digit suffix
            params={"occupation_title": "Anything"},
        )
        assert resp.status_code == 422
        assert called["value"] is False

    def test_get_career_description_endpoint_missing_query_param(
        self, client, monkeypatch,
    ):
        """occupation_title is required (Tier C fallback needs it). FastAPI
        returns 422 when it's absent.
        """
        async def trap(soc_code: str, occupation_title: str, locale=None):
            raise AssertionError("service called despite 422")

        monkeypatch.setattr(
            careers_router.career_description_service,
            "get_or_generate",
            trap,
        )

        resp = client.get("/careers/13-2051/description")
        assert resp.status_code == 422
