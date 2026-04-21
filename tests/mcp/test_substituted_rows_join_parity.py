"""P0 parity test: post-rewrite JOIN produces byte-identical payload vs. captured fan-out fixtures.

Per spec §4 Decision #7, the data-access-layer rewrite must preserve
``_handle_get_career_paths`` response shape byte-for-byte against
fixtures captured from the pre-rewrite fan-out implementation.

Fixtures live in ``tests/mcp/fixtures/career_paths_responses/``:
    a — UIUC + 26.01 substituted to Biology-specific CIP (canonical)
    b — IU + 52.01 substituted to Marketing 52.14
    c — small-program substituted
    e — missing school earnings (school-CTE zero-row short-circuit)
    f — partial coverage: SOC in occupation_profiles but missing onet/ai
    g — partial coverage: SOC in onet_work_profiles but missing op
    h — standard-path exact match (no substitution)

Fixture (d) — the "substitution falls back to 'no rows'" case — was
intentionally dropped: that path routes through the non-deterministic
LLM fallback (``_fallback_gemma_soc_resolution``), so byte-equality
cannot be enforced without mocking the Gemma client. That path is
covered indirectly by the other fixtures and by the existing
``test_cip_substitution_integration.py`` suite.

The ``governance`` key is stripped from both sides before comparison:
it carries per-request timestamps that flap across runs and is not
part of the data-access-layer contract under test here.

These tests hit the real Iceberg warehouse via ``mcp_client.get_server``
and will skip automatically if the warehouse is not provisioned.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


FIXTURE_DIR = (
    Path(__file__).resolve().parent / "fixtures" / "career_paths_responses"
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_WAREHOUSE_PATH = _PROJECT_ROOT / "data" / "warehouse"
_CATALOG_PATH = _PROJECT_ROOT / "data" / "catalog" / "catalog.db"


def _warehouse_available() -> bool:
    return _WAREHOUSE_PATH.exists() and _CATALOG_PATH.exists()


pytestmark = pytest.mark.skipif(
    not _warehouse_available(),
    reason="Iceberg warehouse not present; skipping JOIN parity tests",
)


def _fixture_ids() -> list[str]:
    return sorted(p.stem for p in FIXTURE_DIR.glob("*.json"))


def _load_fixture(stem: str) -> dict:
    path = FIXTURE_DIR / f"{stem}.json"
    with path.open() as fh:
        return json.load(fh)


def _strip_volatile(response: dict) -> dict:
    """Drop per-request flapping keys before comparison.

    ``governance`` is attached by ``attach_governance`` / ``enrich_response``
    on every tool response and includes ``generated_at`` timestamps that
    change on every call. It is not part of the data-access-layer
    contract the parity test is guarding.
    """
    if not isinstance(response, dict):
        return response
    return {k: v for k, v in response.items() if k != "governance"}


def _canonical(payload: dict) -> str:
    """Deterministic serialization: sort keys, coerce non-JSON types via ``default=str``."""
    return json.dumps(payload, sort_keys=True, default=str)


@pytest.fixture(scope="module")
def server():
    """Construct a real FutureProofMCPServer bound to the local Iceberg warehouse.

    Mirrors ``scripts/verify_parity.py``: we build the server directly
    rather than going through ``mcp_client.get_server()`` to avoid
    dragging the FastAPI ``backend/app`` tree onto the import path.
    """
    from mcp_server.futureproof_server import FutureProofMCPServer

    return FutureProofMCPServer(
        warehouse_path=str(_WAREHOUSE_PATH),
        catalog_path=str(_CATALOG_PATH),
        server_name="parity-test",
    )


@pytest.mark.parametrize("fixture_id", _fixture_ids())
def test_join_payload_matches_fanout_fixture(server, fixture_id: str) -> None:
    """Captured pre-rewrite response vs. live post-rewrite response: byte-identical.

    Parametrized over every JSON fixture in the directory. Failure here
    means the JOIN produces different data than the 3xN fan-out for
    the same input — a parity regression that MUST block the spec.
    """
    fixture = _load_fixture(fixture_id)
    expected = fixture["response"]
    actual = _strip_volatile(server._handle_get_career_paths(fixture["input"]))

    # sort_keys + default=str gives us a stable canonical form. We compare
    # the serialized strings rather than dicts so pytest's error output
    # surfaces the first diverging character directly.
    assert _canonical(actual) == _canonical(expected), (
        f"parity drift for {fixture_id}: JOIN response differs from captured fan-out fixture"
    )
