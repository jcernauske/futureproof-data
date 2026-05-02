"""Tests for ``app.routers.branches``.

Covers the SOC-shape validator on /branches/{soc} and the upper-bound
cap on /tree/{build_id}?max_depth=. Both are unauthenticated endpoints
that flow user input into DuckDB lookups; the validators close the
DoS-amplifier surfaces flagged in the 2026-05-01 staff engineer audit
followup-2 (P1.1, P1.2).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(isolated_builds_db) -> TestClient:
    return TestClient(create_app())


# ---------------------------------------------------------------------------
# /branches/{soc} — SOC-shape validator
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "soc, expected_status",
    [
        # Well-formed SOC → through to the handler (may 200 or 404 from
        # the service layer, but NOT 422 from the validator).
        ("11-3021", 200),
        ("15-1252", 200),
        # Malformed → 422 from FastAPI's path validator.
        ("not-a-soc", 422),
        ("11-3021; DROP TABLE careers;", 422),
        ("113021", 422),  # Missing hyphen.
        ("1-3021", 422),  # Three-char prefix wrong.
        ("11-30210", 422),  # Five-digit suffix.
        # Trailing newline — closed at the path-validator level by
        # FastAPI's regex anchoring. Mirrors the AskScope fullmatch
        # case in test_ask_gemma_router.py so the contract is pinned
        # on both surfaces.
        ("11-3021%0A", 422),
    ],
    ids=[
        "valid_management",
        "valid_developer",
        "freeform_string",
        "injection_shape",
        "no_hyphen",
        "short_prefix",
        "long_suffix",
        "trailing_newline_url_encoded",
    ],
)
def test_get_branches_soc_validation(
    client: TestClient,
    soc: str,
    expected_status: int,
) -> None:
    """SOC path parameter rejects anything outside ``\\d{2}-\\d{4}``
    before the handler runs. Mirrors the AskScope validator added in
    the 2026-05-01 audit so the unauthenticated /branches surface
    can't be used to feed arbitrary strings into a DuckDB lookup."""
    resp = client.get(f"/branches/{soc}")
    assert resp.status_code == expected_status, (
        f"Expected {expected_status} for soc={soc!r}, got {resp.status_code}: "
        f"{resp.text}"
    )


# ---------------------------------------------------------------------------
# /tree/{build_id}?max_depth=… — upper-bound cap
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "max_depth, expected_status",
    [
        # Valid range: 1..4. Handler returns 404 because the build_id
        # doesn't exist, but the validator passes.
        (1, 404),
        (3, 404),
        (4, 404),
        # Below floor → 422.
        (0, 422),
        (-1, 422),
        # Above cap → 422. Without the cap a caller could request
        # max_depth=999 and force career_tree.build_tree to fan out
        # through the full SOC graph on an unauthenticated endpoint.
        (5, 422),
        (50, 422),
        (999, 422),
    ],
    ids=[
        "min_valid",
        "default_valid",
        "max_valid",
        "floor_zero",
        "floor_negative",
        "above_cap_5",
        "above_cap_50",
        "above_cap_999",
    ],
)
def test_get_tree_max_depth_bounds(
    client: TestClient,
    max_depth: int,
    expected_status: int,
) -> None:
    """``max_depth`` must satisfy 1 <= max_depth <= 4. The validator
    fires before the handler so unbounded fan-out can't be triggered
    on an unauthenticated endpoint."""
    resp = client.get(f"/tree/nonexistent-build?max_depth={max_depth}")
    assert resp.status_code == expected_status, (
        f"Expected {expected_status} for max_depth={max_depth}, got "
        f"{resp.status_code}: {resp.text}"
    )
