"""Tests for backend/app/routers/pdf_export.py — HTTP boundary.

Covers:
- POST /build/{id}/pdf returns Content-Type: application/pdf.
- POST /builds/compare/pdf 400 on cross-major.
- Pydantic-level validation of len(build_ids) ∈ [2, 3].
- 500 on ReportLab render failure (with CORS-friendly headers).
- 404 when build_id is unknown.

See docs/specs/feature-pdf-report-exports.md §4 New Tests Required.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app import state
from app.main import create_app
from app.routers import pdf_export as pdf_export_router
from app.services import pdf_export, pdf_questions
from app.services.career_description import CareerDescriptionUnavailable

# Pull in the canonical fixture builder from the services conftest.
_SERVICES_TESTS = Path(__file__).resolve().parent.parent / "services"
if str(_SERVICES_TESTS) not in sys.path:
    sys.path.insert(0, str(_SERVICES_TESTS))

# Imported AFTER sys.path adjustment to resolve to the services conftest.
from conftest import make_fixture_build  # type: ignore[import-not-found] # noqa: E402

# ---------------------------------------------------------------------------
# Test client + fixture loading.
# ---------------------------------------------------------------------------


@pytest.fixture
def client(isolated_builds_db) -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def stub_audience_questions(monkeypatch):
    """Stub pdf_questions.generate_audience_questions so router tests don't
    fan out to Gemma. Returns the static fallback assembly directly.
    """
    from app.models.api import AudienceQuestion, AudienceQuestions

    aq = AudienceQuestions(
        ask_the_college=[
            AudienceQuestion(text="College Q1", is_static_mandatory=True),
            AudienceQuestion(text="College Q2", is_static_mandatory=True),
        ],
        ask_your_parents=[AudienceQuestion(text="Parents Q1")],
        ask_yourself=[AudienceQuestion(text="Will I Q1?")],
        gemma_path="fallback_disabled",
    )
    monkeypatch.setattr(
        pdf_questions,
        "generate_audience_questions",
        AsyncMock(return_value=aq),
    )
    return aq


@pytest.fixture
def stamped_build(isolated_builds_db):
    """Stamp a fully-populated Build into the in-memory state cache.

    Returns the Build so tests have access to its build_id.
    """
    build = make_fixture_build()
    state.store_build(build)
    return build


@pytest.fixture
def stamped_three_same_major_builds(isolated_builds_db):
    """Three builds in the 14.19 CIP family stamped into state."""
    builds = [
        make_fixture_build(
            school_name="Purdue University",
            cipcode="14.1901",
            unitid=243780,
            profile_name="brave fox",
        ),
        make_fixture_build(
            school_name="Indiana University",
            cipcode="14.1902",
            unitid=151351,
            profile_name="bold otter",
        ),
        make_fixture_build(
            school_name="Rose-Hulman Institute of Technology",
            cipcode="14.1903",
            unitid=152426,
            profile_name="kind raven",
        ),
    ]
    for b in builds:
        state.store_build(b)
    return builds


@pytest.fixture
def stamped_cross_major_builds(isolated_builds_db):
    """Two builds in different 4-digit CIP families for cross-major tests."""
    builds = [
        make_fixture_build(cipcode="14.1901", school_name="Purdue", unitid=243780),
        make_fixture_build(cipcode="11.0701", school_name="UC Berkeley", unitid=110635),
    ]
    for b in builds:
        state.store_build(b)
    return builds


# ---------------------------------------------------------------------------
# P0: Single-build PDF — Content-Type, 200, bytes.
# ---------------------------------------------------------------------------


class TestPostBuildPdf:
    def test_post_build_pdf_returns_application_pdf_content_type(
        self, client, stamped_build, stub_audience_questions,
    ):
        resp = client.post(
            f"/build/{stamped_build.build_id}/pdf",
            json={"student_name": None},
        )
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"] == "application/pdf"
        # Response is real PDF bytes.
        assert resp.content[:4] == b"%PDF"

    def test_post_build_pdf_includes_attachment_disposition(
        self, client, stamped_build, stub_audience_questions,
    ):
        resp = client.post(
            f"/build/{stamped_build.build_id}/pdf",
            json={"student_name": "Rowan"},
        )
        assert resp.status_code == 200
        disposition = resp.headers.get("content-disposition", "")
        assert "attachment" in disposition
        assert "futureproof-" in disposition
        assert ".pdf" in disposition

    def test_post_build_pdf_404_when_build_missing(
        self, client, isolated_builds_db,
    ):
        resp = client.post(
            "/build/does-not-exist-9999/pdf",
            json={"student_name": None},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert "not found" in body["detail"].lower()

    def test_post_build_pdf_500_when_reportlab_raises(
        self, client, stamped_build, stub_audience_questions, monkeypatch,
    ):
        """Patch generate_build_pdf to raise; assert 500 with the error
        message format that flows through CORSMiddleware (architect A3).
        """
        monkeypatch.setattr(
            pdf_export,
            "generate_build_pdf",
            lambda *a, **k: (_ for _ in ()).throw(
                RuntimeError("simulated reportlab failure")
            ),
        )

        resp = client.post(
            f"/build/{stamped_build.build_id}/pdf",
            json={"student_name": None},
        )
        assert resp.status_code == 500
        body = resp.json()
        assert "detail" in body
        # Error surfaces via HTTPException so CORS headers attach correctly
        # (vs an unhandled 5xx that bypasses middleware).
        detail = body["detail"]
        assert "PDF generation failed" in detail or "RuntimeError" in detail

    def test_post_build_pdf_accepts_optional_student_name(
        self, client, stamped_build, stub_audience_questions,
    ):
        # Send no student_name field at all.
        resp = client.post(f"/build/{stamped_build.build_id}/pdf", json={})
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"

    def test_post_build_pdf_rejects_overlong_student_name(
        self, client, stamped_build, stub_audience_questions,
    ):
        """Pydantic max_length=80 — 81+ chars rejected at validation."""
        resp = client.post(
            f"/build/{stamped_build.build_id}/pdf",
            json={"student_name": "X" * 200},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# P0: Comparison PDF — 400 on cross-major, 422 on bad len.
# ---------------------------------------------------------------------------


class TestPostComparePdf:
    def test_post_compare_pdf_returns_application_pdf_content_type(
        self, client, stamped_three_same_major_builds, stub_audience_questions,
    ):
        ids = [b.build_id for b in stamped_three_same_major_builds]
        resp = client.post("/builds/compare/pdf", json={"build_ids": ids})
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"

    def test_post_compare_pdf_accepts_cross_major(
        self, client, stamped_cross_major_builds, stub_audience_questions,
    ):
        """Cross-major comparisons are SUPPORTED — the in-app CompareView
        shows them, the PDF matches that contract. Title falls back to
        "Career comparison" in the rendered PDF when majors differ."""
        ids = [b.build_id for b in stamped_cross_major_builds]
        resp = client.post("/builds/compare/pdf", json={"build_ids": ids})
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"

    def test_post_compare_pdf_validation_rejects_one_build(
        self, client, isolated_builds_db,
    ):
        """Pydantic min_length=2 rejects length 1 → 422."""
        resp = client.post("/builds/compare/pdf", json={"build_ids": ["b1"]})
        assert resp.status_code == 422

    def test_post_compare_pdf_validation_rejects_four_builds(
        self, client, isolated_builds_db,
    ):
        """Pydantic max_length=3 rejects length 4 → 422."""
        resp = client.post(
            "/builds/compare/pdf",
            json={"build_ids": ["b1", "b2", "b3", "b4"]},
        )
        assert resp.status_code == 422

    def test_post_compare_pdf_404_when_first_build_missing(
        self, client, isolated_builds_db,
    ):
        """Unknown build_id in the list → 404."""
        resp = client.post(
            "/builds/compare/pdf",
            json={"build_ids": ["does-not-exist-1", "does-not-exist-2"]},
        )
        assert resp.status_code == 404

    def test_post_compare_pdf_404_when_one_id_missing(
        self, client, stamped_three_same_major_builds, stub_audience_questions,
    ):
        """If any one build is missing, 404 (the loop short-circuits)."""
        valid = stamped_three_same_major_builds[0].build_id
        resp = client.post(
            "/builds/compare/pdf",
            json={"build_ids": [valid, "does-not-exist-9999"]},
        )
        assert resp.status_code == 404

    def test_post_compare_pdf_accepts_2_or_3_same_major_builds(
        self, client, stamped_three_same_major_builds, stub_audience_questions,
    ):
        """Both 2 and 3 same-major build sets render successfully."""
        ids2 = [b.build_id for b in stamped_three_same_major_builds[:2]]
        resp = client.post("/builds/compare/pdf", json={"build_ids": ids2})
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"

        ids3 = [b.build_id for b in stamped_three_same_major_builds]
        resp = client.post("/builds/compare/pdf", json={"build_ids": ids3})
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"


# ---------------------------------------------------------------------------
# P0: career_description lazy-fetch fallback on the PDF export path.
# (feature-career-description-on-pdf.md §4 New Tests Required)
# ---------------------------------------------------------------------------


def _make_career_description():
    """Helper: build a valid CareerDescription instance for assertions."""
    from app.models.career import CareerDescription

    return CareerDescription(
        soc_code="17-2141",
        summary=(
            "Mechanical engineers design machines that move parts of "
            "the world. They sketch, simulate, and prototype systems."
        ),
        tasks=[
            "Sketch concept designs for parts and systems",
            "Simulate stresses and tolerances digitally",
            "Prototype machines and test them physically",
            "Coordinate with manufacturing on tolerances",
        ],
        anchor_tier="activities",
        generated_at="2026-05-07T00:00:00+00:00",
        model="gemma-4-26b-a4b-it",
    )


class TestPdfExportLazyCareerDescription:
    def test_pdf_export_lazy_fetch_persists(
        self, client, stamped_build, stub_audience_questions, monkeypatch,
    ):
        """Build with career_description=None at the in-memory state →
        endpoint calls the service, persists the result via
        state.update_build, and the persisted Build now carries the
        description.
        """
        # Confirm the fixture build starts unpopulated.
        assert stamped_build.career_description is None

        desc = _make_career_description()
        call_count = {"value": 0}

        async def fake_get_or_generate(soc_code: str, occupation_title: str):
            call_count["value"] += 1
            return desc

        monkeypatch.setattr(
            pdf_export_router.career_description,
            "get_or_generate",
            fake_get_or_generate,
        )

        resp = client.post(
            f"/build/{stamped_build.build_id}/pdf",
            json={"student_name": None},
        )
        assert resp.status_code == 200, resp.text
        assert resp.content[:4] == b"%PDF"
        assert call_count["value"] == 1

        # Persisted: state's view of the build now carries the description.
        persisted = state.get_build(stamped_build.build_id)
        assert persisted is not None
        assert persisted.career_description is not None
        assert persisted.career_description.summary == desc.summary
        assert persisted.career_description.tasks == desc.tasks

    def test_pdf_export_lazy_fetch_failure_renders_without_section(
        self, client, stamped_build, stub_audience_questions, monkeypatch,
    ):
        """Service raises CareerDescriptionUnavailable → endpoint still
        returns 200 PDF; the build's career_description stays None.
        """
        assert stamped_build.career_description is None

        async def raising(soc_code: str, occupation_title: str):
            raise CareerDescriptionUnavailable("simulated upstream failure")

        monkeypatch.setattr(
            pdf_export_router.career_description,
            "get_or_generate",
            raising,
        )

        resp = client.post(
            f"/build/{stamped_build.build_id}/pdf",
            json={"student_name": None},
        )
        assert resp.status_code == 200, resp.text
        assert resp.content[:4] == b"%PDF"

        # The "About this career" section was silently omitted.
        persisted = state.get_build(stamped_build.build_id)
        assert persisted is not None
        assert persisted.career_description is None

    def test_pdf_export_lazy_fetch_uses_state_update_build(
        self, client, stamped_build, stub_audience_questions, monkeypatch,
    ):
        """Lazy persist routes through ``state.update_build`` (not
        builds_service.save_build directly). Per architect §5 condition 4
        / Decision 14, this is the canonical single-write path that keeps
        the in-memory cache and DuckDB in sync.
        """
        assert stamped_build.career_description is None

        desc = _make_career_description()

        async def fake_get_or_generate(soc_code: str, occupation_title: str):
            return desc

        monkeypatch.setattr(
            pdf_export_router.career_description,
            "get_or_generate",
            fake_get_or_generate,
        )

        update_calls: list[tuple[str, str]] = []
        original_update = state.update_build

        def spy_update_build(build_id, build):
            # Tuple of (build_id, summary text) so we can assert the
            # call shape without a heavyweight equality check.
            update_calls.append(
                (build_id, build.career_description.summary if build.career_description else None),
            )
            original_update(build_id, build)

        monkeypatch.setattr(state, "update_build", spy_update_build)
        # The router imports `state` directly; patching the module-level
        # attribute makes the spy observable from inside the endpoint.
        monkeypatch.setattr(pdf_export_router.state, "update_build", spy_update_build)

        resp = client.post(
            f"/build/{stamped_build.build_id}/pdf",
            json={"student_name": None},
        )
        assert resp.status_code == 200, resp.text

        # Exactly one update_build call, and the persisted summary matches.
        assert len(update_calls) == 1
        build_id, summary = update_calls[0]
        assert build_id == stamped_build.build_id
        assert summary == desc.summary

        # Subsequent _load_build_or_404 returns the persisted description.
        persisted = state.get_build(stamped_build.build_id)
        assert persisted is not None
        assert persisted.career_description is not None
        assert persisted.career_description.summary == desc.summary
