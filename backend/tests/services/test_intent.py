"""Tests for the tiered Gemma intent resolution service.

Covers the three confidence tiers (high / medium / low), the post-parse
alternatives sanitizer (clamp, malformed CIPs, dedup), and audit-flag
propagation. These are the first service-level tests for
``app.services.intent`` — prior coverage was only via the CLI harness.

Every test monkeypatches both ``gemma_client.generate`` (so no Ollama /
OpenRouter HTTP goes out) and ``mcp_client.get_server`` (so no DuckDB /
Iceberg reads happen). The ``generate`` mock returns two sequenced JSON
strings per ``resolve_intent`` call: the intent response first, the
audit response second.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.services import intent

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_FIXTURES_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "intent_responses.json"
)


@pytest.fixture
def intent_fixtures() -> dict[str, dict[str, Any]]:
    """Load the tier payloads that stand in for Gemma responses."""
    return json.loads(_FIXTURES_PATH.read_text())


@pytest.fixture(autouse=True)
def _clear_intent_cache() -> None:
    """Ensure each test starts with an empty intent cache.

    ``resolve_intent`` memoizes by ``(normalized_input, unitid)``. Bleed
    across tests (even when inputs differ) would mask real regressions
    because a cache hit short-circuits Gemma entirely.
    """
    intent._intent_cache.clear()
    yield
    intent._intent_cache.clear()


def _make_generate_mock(
    intent_payload: dict[str, Any] | str,
    audit_payload: dict[str, Any] | str | None = None,
):
    """Return a callable standing in for ``gemma_client.generate``.

    First call returns the intent JSON; second call returns the audit
    JSON (default: valid+clean). Third-plus calls return the audit too,
    so nothing blows up if the service ever stops making exactly two
    calls. Accepts raw strings so tests can exercise the parser's
    trailing-prose stripping.
    """
    intent_str = (
        intent_payload
        if isinstance(intent_payload, str)
        else json.dumps(intent_payload)
    )
    audit_obj = audit_payload if audit_payload is not None else {
        "valid": True,
        "tone": "clean",
        "message": "ok",
    }
    audit_str = (
        audit_obj if isinstance(audit_obj, str) else json.dumps(audit_obj)
    )
    call_log: list[tuple[str, str]] = []

    def _generate(*, system: str, user: str, max_tokens: int = 500,
                  temperature: float = 0.7, model: str | None = None) -> str:
        call_log.append((system, user))
        # First call: intent. Anything after that: audit. Both the intent
        # prompt and the audit prompt have distinctive lead-ins, so we
        # route by call index rather than by inspecting the system text.
        return intent_str if len(call_log) == 1 else audit_str

    _generate.call_log = call_log  # type: ignore[attr-defined]
    return _generate


class _StubServer:
    """Minimal stand-in for FutureProofMCPServer used by the intent service.

    The intent service calls ``server.query_iceberg(sql)`` three times:
    once for school CIPs, once for crosswalk CIPs, once for career
    titles. Returning empty lists is sufficient — we're not testing the
    Gemma prompt assembly here, only the response pipeline.
    """

    def __init__(self) -> None:
        self.sql_log: list[str] = []

    def query_iceberg(self, sql: str) -> list[dict[str, Any]]:
        self.sql_log.append(sql)
        return []


@pytest.fixture
def stub_server(monkeypatch: pytest.MonkeyPatch) -> _StubServer:
    server = _StubServer()
    monkeypatch.setattr(intent.mcp_client, "get_server", lambda: server)
    return server


@pytest.fixture
def stub_gemma_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent ``current_config()`` from touching .env or cached client.

    ``_call_gemma_intent`` reads the config for its stats dict. Without
    this patch it will try to load ``.env`` and may flake based on the
    developer's local ``INFERENCE_BACKEND`` setting.
    """
    class _Cfg:
        model = "stub-model"
        backend = "stub"

    monkeypatch.setattr(intent.gemma_client, "current_config", lambda: _Cfg())


def _programs_arg() -> list[dict[str, Any]]:
    """The `programs` kwarg is threaded through but not used in the response
    pipeline we're testing. An empty list keeps the signature honest."""
    return []


# ---------------------------------------------------------------------------
# P0: tier-driven behavior
# ---------------------------------------------------------------------------


def test_resolve_intent_high_confidence_returns_empty_alternatives(
    monkeypatch: pytest.MonkeyPatch,
    intent_fixtures: dict[str, dict[str, Any]],
    stub_server: _StubServer,
    stub_gemma_config: None,
) -> None:
    """High confidence → confidence='high', alternatives=[], no clarify."""
    fake_generate = _make_generate_mock(intent_fixtures["high"])
    monkeypatch.setattr(intent.gemma_client, "generate", fake_generate)

    result = intent.resolve_intent(
        major_text="pre-PT",
        school_name="University of Central Anywhere",
        unitid=123456,
        programs=_programs_arg(),
    )

    assert result.confidence == "high"
    assert result.matched_cip == "51.2308"
    assert result.needs_clarification is False
    # A high-tier result must not pollute the card with alternatives.
    # The sanitizer normalizes an empty list to [] (not None) when the
    # input was a valid list — this is the contract with the frontend's
    # `alternatives?.length > 0` check.
    assert result.alternatives == []


def test_resolve_intent_medium_confidence_returns_2_to_4_alternatives(
    monkeypatch: pytest.MonkeyPatch,
    intent_fixtures: dict[str, dict[str, Any]],
    stub_server: _StubServer,
    stub_gemma_config: None,
) -> None:
    """Medium confidence → 2–4 alternatives, all well-formed, no clarify."""
    fake_generate = _make_generate_mock(intent_fixtures["medium"])
    monkeypatch.setattr(intent.gemma_client, "generate", fake_generate)

    result = intent.resolve_intent(
        major_text="business",
        school_name="Anywhere State",
        unitid=42,
        programs=_programs_arg(),
    )

    assert result.confidence == "medium"
    assert result.matched_cip == "52.0201"
    assert result.needs_clarification is False
    assert result.alternatives is not None
    assert 2 <= len(result.alternatives) <= 4, (
        "medium-tier contract: 2–4 alternatives"
    )
    for alt in result.alternatives:
        assert alt["cip"] and alt["title"], (
            "every alternative carries non-empty cip/title"
        )
        assert alt["cip"] != result.matched_cip, (
            "sanitizer must drop echoes of the primary CIP"
        )


def test_resolve_intent_low_confidence_sets_needs_clarification(
    monkeypatch: pytest.MonkeyPatch,
    intent_fixtures: dict[str, dict[str, Any]],
    stub_server: _StubServer,
    stub_gemma_config: None,
) -> None:
    """Low confidence → needs_clarification=True; up to 10 alternatives.

    The frontend reads ``needs_clarification`` to route low-tier inputs
    into the picker rather than the match card. This is the contract.
    """
    fake_generate = _make_generate_mock(intent_fixtures["low"])
    monkeypatch.setattr(intent.gemma_client, "generate", fake_generate)

    result = intent.resolve_intent(
        major_text="helping people",
        school_name="Anywhere State",
        unitid=42,
        programs=_programs_arg(),
    )

    assert result.confidence == "low"
    assert result.needs_clarification is True
    assert result.alternatives is not None
    assert len(result.alternatives) <= 10, (
        "low-tier ceiling — sanitizer clamps at 10"
    )
    # The fixture carries 5 distinct alts; all should survive the
    # sanitizer since they're well-formed and don't dupe the primary.
    assert len(result.alternatives) == 5


def test_resolve_intent_clamps_excess_alternatives_to_10(
    monkeypatch: pytest.MonkeyPatch,
    stub_server: _StubServer,
    stub_gemma_config: None,
) -> None:
    """Gemma misbehaves and returns 15 alternatives → sanitizer clamps to 10.

    Without the clamp, a low-confidence response with a verbose Gemma
    could blow up the picker layout. This test injects 15 well-formed
    alternatives and asserts exactly 10 survive in the same input order.
    """
    oversized = {
        "matched_cip": "14.0901",
        "matched_title": "Computer Engineering, General",
        "confidence": "low",
        "reasoning": "ambiguous",
        "parent_cip": "",
        "alternatives": [
            {
                "cip": f"{family:02d}.{serial:04d}",
                "title": f"Program {family}-{serial}",
                "why": f"reason {family}-{serial}",
            }
            # 15 distinct CIPs, all in valid XX.XXXX format and none
            # equal to the primary 14.0901.
            for family, serial in [
                (11, 101), (11, 102), (11, 103), (14, 902),
                (14, 903), (14, 904), (15, 1301), (15, 1302),
                (26, 1), (26, 2), (27, 1), (27, 2),
                (30, 701), (30, 702), (30, 703),
            ]
        ],
    }
    fake_generate = _make_generate_mock(oversized)
    monkeypatch.setattr(intent.gemma_client, "generate", fake_generate)

    result = intent.resolve_intent(
        major_text="something with computers",
        school_name="Anywhere State",
        unitid=42,
        programs=_programs_arg(),
    )

    assert result.alternatives is not None
    assert len(result.alternatives) == 10, (
        "sanitizer must clamp at 10 even when Gemma returns more"
    )
    # Order must be preserved — the first 10 input entries survive, not
    # the last 10 and not a random subset.
    assert [a["cip"] for a in result.alternatives] == [
        "11.0101", "11.0102", "11.0103", "14.0902", "14.0903",
        "14.0904", "15.1301", "15.1302", "26.0001", "26.0002",
    ]


def test_resolve_intent_handles_null_alternatives(
    monkeypatch: pytest.MonkeyPatch,
    stub_server: _StubServer,
    stub_gemma_config: None,
) -> None:
    """Gemma returns "alternatives": null → service returns alternatives=None,
    does not crash, downstream IntentResult is still valid."""
    payload = {
        "matched_cip": "14.0901",
        "matched_title": "Computer Engineering, General",
        "confidence": "high",
        "reasoning": "unambiguous",
        "parent_cip": "",
        "alternatives": None,
    }
    fake_generate = _make_generate_mock(payload)
    monkeypatch.setattr(intent.gemma_client, "generate", fake_generate)

    result = intent.resolve_intent(
        major_text="computer engineering",
        school_name="Anywhere State",
        unitid=42,
        programs=_programs_arg(),
    )

    # The sanitizer returns None (not []) when the raw field is not a
    # list. The frontend treats null and [] identically for rendering;
    # we pin the exact shape so any accidental coercion is caught.
    assert result.alternatives is None
    assert result.confidence == "high"


# ---------------------------------------------------------------------------
# P1: cross-tier invariants
# ---------------------------------------------------------------------------


def test_resolve_intent_preserves_audit_flag_across_tiers(
    monkeypatch: pytest.MonkeyPatch,
    intent_fixtures: dict[str, dict[str, Any]],
    stub_server: _StubServer,
    stub_gemma_config: None,
) -> None:
    """Playful-warning and hard-reject audits pass through regardless of tier.

    The audit pass is a second Gemma call that annotates the match with
    a tone. The intent service must surface these on every tier — the
    UI decides whether to render them. Playful warnings on a medium-
    tier match render inline; hard rejects replace the card entirely.
    """
    # Medium-tier match + playful warning.
    fake_playful = _make_generate_mock(
        intent_fixtures["medium"],
        audit_payload={
            "valid": True,
            "tone": "playful_warning",
            "message": "Business is broad — sure you don't mean Finance?",
        },
    )
    monkeypatch.setattr(intent.gemma_client, "generate", fake_playful)

    medium_result = intent.resolve_intent(
        major_text="business",
        school_name="Anywhere State",
        unitid=42,
        programs=_programs_arg(),
    )
    assert medium_result.audit_flag == "playful_warning"
    assert medium_result.audit_message == (
        "Business is broad — sure you don't mean Finance?"
    )

    # High-tier match + hard reject (adversarial/nonsense input that
    # Gemma's intent pass charitably mapped to something).
    intent._intent_cache.clear()
    fake_reject = _make_generate_mock(
        intent_fixtures["high"],
        audit_payload={
            "valid": False,
            "tone": "hard_reject",
            "message": "That doesn't look like a real major.",
        },
    )
    monkeypatch.setattr(intent.gemma_client, "generate", fake_reject)

    high_result = intent.resolve_intent(
        major_text="asdfghjkl",
        school_name="Anywhere State",
        unitid=42,
        programs=_programs_arg(),
    )
    assert high_result.audit_flag == "hard_reject"
    assert high_result.audit_message == "That doesn't look like a real major."
    # Hard-reject tone must not silently flip needs_clarification. The
    # tier is still "high" so the frontend routes to match then the
    # audit_flag gate swaps in the reject card.
    assert high_result.confidence == "high"


# ---------------------------------------------------------------------------
# Bonus: direct sanitizer coverage (not in §4 but low-cost + high-value)
# ---------------------------------------------------------------------------


def test_sanitize_drops_malformed_cip_codes() -> None:
    """Mix of valid (XX.XXXX) and invalid CIPs → only well-formed survive.

    Gemma hallucinates CIP codes regularly — two-digit prefixes, bare
    integers, obvious garbage. The sanitizer defends the frontend
    contract (the `CIP XX.XXXX` label in the match card and the
    confirm-endpoint payload both assume the canonical format).
    """
    raw = [
        {"cip": "52.0201", "title": "Valid Biz Admin", "why": "ok"},
        {"cip": "52.999", "title": "Malformed — 3 digits after dot", "why": ""},
        {"cip": "abc", "title": "Not numeric at all", "why": ""},
        {"cip": "52.02", "title": "Only 2 digits after dot", "why": ""},
        {"cip": "", "title": "Empty CIP", "why": ""},
        {"cip": "52.0801", "title": "Valid Finance", "why": "ok"},
    ]

    cleaned = intent._sanitize_alternatives(raw, primary_cip="99.9999")

    assert cleaned is not None
    assert [a["cip"] for a in cleaned] == ["52.0201", "52.0801"], (
        "exactly the two well-formed CIPs survive, in input order"
    )


def test_sanitize_drops_primary_cip_echoed_in_alternatives() -> None:
    """Gemma echoes the primary CIP as an alternative → sanitizer drops it.

    This is a real failure mode: when Gemma is uncertain, it sometimes
    restates its primary as an 'alternative' before listing the actual
    alternatives. Leaving it in means the student would see the same
    program twice in the card — once as primary, once as an option.
    """
    raw = [
        # Gemma's echo of the primary match.
        {"cip": "52.0201", "title": "Business Administration", "why": "same"},
        {"cip": "52.0801", "title": "Finance", "why": "core markets"},
        {"cip": "52.1401", "title": "Marketing", "why": "customer base"},
    ]

    cleaned = intent._sanitize_alternatives(raw, primary_cip="52.0201")

    assert cleaned is not None
    assert len(cleaned) == 2
    # The echoed primary is gone; the genuine alternatives survive in
    # input order with the echo filtered out rather than shifting
    # positions.
    assert [a["cip"] for a in cleaned] == ["52.0801", "52.1401"]


def test_sanitize_drops_non_string_title_and_cip() -> None:
    """Non-string title/cip values are dropped before str() coercion.

    Gemma very rarely returns nested dicts or numeric literals where a
    string is expected. Without the isinstance guard, str() would turn
    those into Python reprs like "{'primary': 'Finance'}" that render
    verbatim in the match card — a UX defect disguised as data. The
    sanitizer drops these entries before the coercion step.
    """
    raw = [
        # Valid control — survives.
        {"cip": "52.0801", "title": "Finance", "why": "ok"},
        # Dict-valued title: previously became "{'primary': 'Finance'}".
        {"cip": "52.1401", "title": {"primary": "Marketing"}, "why": "no"},
        # Int CIP: coerced to "52" which would fail the regex anyway, but
        # the isinstance guard short-circuits before we touch it.
        {"cip": 52, "title": "Integer CIP", "why": "no"},
        # None title: would have become "None".
        {"cip": "52.0701", "title": None, "why": "no"},
    ]

    cleaned = intent._sanitize_alternatives(raw, primary_cip="52.0201")

    assert cleaned is not None
    assert [a["cip"] for a in cleaned] == ["52.0801"]


# ---------------------------------------------------------------------------
# Primary-CIP validation (S1 from §8 Code Review)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_cip",
    [
        "52",         # missing dot + last four
        "52.02",      # only two digits after dot
        "52.0201X",   # trailing junk
        "",           # empty
        "abc.defg",   # non-numeric
        "052.0201",   # three-digit family (regex anchors at ^\d{2}\.)
        "52.02011",   # five-digit subcode
    ],
)
def test_resolve_intent_rejects_malformed_primary_cip(
    bad_cip: str,
    monkeypatch: pytest.MonkeyPatch,
    stub_server: _StubServer,
    stub_gemma_config: None,
) -> None:
    """Malformed Gemma primary CIP → ValueError (→ frontend fallback phase).

    The sanitizer regex-gates every alternative but the primary
    ``matched_cip`` is what gets persisted to ``_intent_cache`` and
    shipped to downstream MCP queries. A malformed primary must never
    reach either. The router translates the raised ``ValueError`` into
    the phase="fallback" path on the frontend.
    """
    payload = {
        "matched_cip": bad_cip,
        "matched_title": "Whatever",
        "confidence": "high",
        "reasoning": "n/a",
        "parent_cip": "",
        "alternatives": [],
    }
    fake_generate = _make_generate_mock(payload)
    monkeypatch.setattr(intent.gemma_client, "generate", fake_generate)

    with pytest.raises(ValueError, match="malformed primary CIP"):
        intent.resolve_intent(
            major_text="something",
            school_name="Anywhere State",
            unitid=42,
            programs=_programs_arg(),
        )


def test_resolve_intent_rejects_null_primary_cip(
    monkeypatch: pytest.MonkeyPatch,
    stub_server: _StubServer,
    stub_gemma_config: None,
) -> None:
    """Null/missing primary CIP → ValueError. Covered separately from the
    parametrized test because JSON ``null`` arrives as Python ``None``
    after parsing, which would make the parametrize list awkward."""
    payload = {
        "matched_cip": None,
        "matched_title": "Whatever",
        "confidence": "high",
        "reasoning": "n/a",
        "parent_cip": "",
        "alternatives": [],
    }
    fake_generate = _make_generate_mock(payload)
    monkeypatch.setattr(intent.gemma_client, "generate", fake_generate)

    with pytest.raises(ValueError, match="malformed primary CIP"):
        intent.resolve_intent(
            major_text="something",
            school_name="Anywhere State",
            unitid=42,
            programs=_programs_arg(),
        )
