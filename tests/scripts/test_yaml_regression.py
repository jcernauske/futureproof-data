"""Tests for scripts/yaml_regression.py — anchoring helper.

Spec: docs/specs/completed/bugfix-disable-intent-yaml-regression.md §12.

Importing the script has side effects (sets `INTENT_YAML_ENABLED=false`
in the process env, patches `intent._audit_intent_mapping` to a no-op).
Both are intentional for the script's primary use case (the regression
run) but live within this single pytest process — root pytest does not
share process state with the backend pytest suite, so this is safe.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
sys.path.insert(0, str(_REPO_ROOT / "backend"))

import yaml_regression  # type: ignore[import-not-found]  # noqa: E402
from app.services import intent  # noqa: E402


class _StubServer:
    """Stand-in for FutureProofMCPServer.query_iceberg.

    Logs every SQL string the helper issues and returns a fixed
    deterministic row set keyed by 5-char family prefix. Same prefix +
    same fixture → same rows in the same order.
    """

    def __init__(
        self,
        rows_by_family: dict[str, list[dict[str, Any]]],
    ) -> None:
        self._rows = rows_by_family
        self.sql_log: list[str] = []

    def query_iceberg(self, sql: str) -> list[dict[str, Any]]:
        self.sql_log.append(sql)
        # Pluck the family prefix out of the SQL so the stub doesn't
        # have to parse it. The helper always issues
        # "SUBSTR(cipcode, 1, 5) = '<prefix>'".
        for prefix, rows in self._rows.items():
            if f"= '{prefix}'" in sql:
                limit = _extract_limit(sql)
                return list(rows[:limit])
        return []


def _extract_limit(sql: str) -> int:
    """Pull the ``LIMIT N`` value out of the helper's SQL.

    The helper's SQL ends in ``LIMIT {int(k)}``; pulling the value out
    lets the stub respect the ``k`` argument so we can write a test that
    exercises the truncation behavior (k=2 must drop the third row).
    """
    tail = sql.rsplit("LIMIT", 1)[-1].strip()
    return int(tail)


@pytest.fixture
def install_stub_server(monkeypatch: pytest.MonkeyPatch):
    """Install a stub MCP server and a deterministic _get_school_cips.

    `_sample_anchoring_schools` calls `intent.mcp_client.get_server()`
    once for the unitid query and `intent._get_school_cips(unitid)` per
    sampled school. We patch both so neither touches the real Iceberg
    catalog.
    """

    def _factory(rows_by_family: dict[str, list[dict[str, Any]]]) -> _StubServer:
        server = _StubServer(rows_by_family)
        monkeypatch.setattr(intent.mcp_client, "get_server", lambda: server)
        # Each unitid maps to a stub program list. The exact contents
        # don't matter for determinism — what matters is that the same
        # unitid returns the same list across calls.
        monkeypatch.setattr(
            intent,
            "_get_school_cips",
            lambda unitid: [
                {"cipcode": "13.0201", "program_name": f"Stub Bilingual {unitid}"}
            ],
        )
        return server

    return _factory


def test_sample_anchoring_schools_is_deterministic(install_stub_server) -> None:
    """Same expected_cip4 + same k + same DuckDB → same schools each call.

    This is the load-bearing invariant for the V2 regression report:
    re-running `--anchored` against the same Gold zone must produce the
    same per-(input, school) rows so the report is reproducible. We pin
    it by issuing two back-to-back calls with the same arguments and
    asserting the returned tuples are equal.
    """
    install_stub_server({
        "13.02": [
            {"unitid": 105297, "institution_name": "Dine College"},
            {"unitid": 110097, "institution_name": "Biola University"},
            {"unitid": 127918, "institution_name": "Regis University"},
        ],
    })

    a = yaml_regression._sample_anchoring_schools("13.02", k=3)
    b = yaml_regression._sample_anchoring_schools("13.02", k=3)

    # Strip the (mutable) programs list — those come from the stub
    # _get_school_cips and are equal-by-value but not identity-equal.
    keys_a = [(uid, name) for uid, name, _ in a]
    keys_b = [(uid, name) for uid, name, _ in b]
    assert keys_a == keys_b
    assert keys_a == [
        (105297, "Dine College"),
        (110097, "Biola University"),
        (127918, "Regis University"),
    ]


def test_sample_anchoring_schools_respects_k(install_stub_server) -> None:
    """k=2 must clamp the result to 2 rows, not return all available.

    Determinism only matters if the caller can size the sample. The
    helper hands ``k`` straight into the SQL ``LIMIT`` clause; the stub
    extracts it and clips its return value to match.
    """
    install_stub_server({
        "13.02": [
            {"unitid": 105297, "institution_name": "Dine College"},
            {"unitid": 110097, "institution_name": "Biola University"},
            {"unitid": 127918, "institution_name": "Regis University"},
        ],
    })

    result = yaml_regression._sample_anchoring_schools("13.02", k=2)
    assert [uid for uid, _, _ in result] == [105297, 110097]


def test_sample_anchoring_schools_handles_missing_family(
    install_stub_server,
) -> None:
    """No school in the Gold zone offers this family → empty list.

    The caller treats `[]` as "no_anchor_available" and records the
    input separately in the report. Returning anything else (raise,
    None, partial result) would corrupt that bucket.
    """
    install_stub_server({"99.99": []})

    assert yaml_regression._sample_anchoring_schools("99.99", k=3) == []


def test_sample_anchoring_schools_handles_six_digit_cip(
    install_stub_server,
) -> None:
    """A 6-digit YAML cip4 (e.g. 13.1003) anchors against its 5-char family.

    Several YAML entries store sub-leaf codes (Deaf Education = 13.1003,
    Autism Education = 13.1013). The helper must clip to the first 5
    chars so it samples schools in the broader 13.10 family — the
    family Gemma's leaf would land in if it gets the answer right.
    """
    install_stub_server({
        "13.10": [
            {"unitid": 100001, "institution_name": "Stub State University"},
        ],
    })

    result = yaml_regression._sample_anchoring_schools("13.1003", k=3)
    assert [uid for uid, _, _ in result] == [100001]


def test_sample_anchoring_schools_skips_rows_with_missing_fields(
    install_stub_server,
) -> None:
    """Defensive: a row missing institution_name or unitid is dropped.

    The Gold zone has a small tail of records where institution_name is
    null. The helper's SQL filters those, but the in-Python check is
    cheap insurance for the case where the upstream contract drifts.
    """
    install_stub_server({
        "13.02": [
            {"unitid": 105297, "institution_name": "Dine College"},
            {"unitid": 110097, "institution_name": None},   # dropped
            {"unitid": None, "institution_name": "Nameless"},  # dropped
            {"unitid": 127918, "institution_name": "Regis University"},
        ],
    })

    result = yaml_regression._sample_anchoring_schools("13.02", k=4)
    assert [uid for uid, _, _ in result] == [105297, 127918]
