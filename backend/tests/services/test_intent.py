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

    def _generate(**kwargs: Any) -> str:
        call_log.append((kwargs.get("system", ""), kwargs.get("user", "")))
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


# ---------------------------------------------------------------------------
# Regression: 4-digit umbrella CIPs promoted to leaf before strict regex.
# Bug was: Gemma returning "13.10" (umbrella) tripped _CIP_PATTERN and the
# frontend saw "Gemma couldn't match that" for "deaf ed" at Illinois State.
# ---------------------------------------------------------------------------


class _SchoolCatalogStubServer:
    """Stub that returns a realistic school CIP catalog for the first query
    (``_get_school_cips``) and empty for the rest. Lets us exercise the
    salvage path that reads from the school's reported CIPs.
    """

    def __init__(self, school_cips: list[dict[str, str]]) -> None:
        self._school_cips = school_cips
        self.sql_log: list[str] = []

    def query_iceberg(self, sql: str) -> list[dict[str, Any]]:
        self.sql_log.append(sql)
        if "consumable_career_outcomes" in sql:
            return list(self._school_cips)
        return []


def _install_school_catalog(
    monkeypatch: pytest.MonkeyPatch,
    school_cips: list[dict[str, str]],
) -> _SchoolCatalogStubServer:
    server = _SchoolCatalogStubServer(school_cips)
    monkeypatch.setattr(intent.mcp_client, "get_server", lambda: server)
    return server


def test_resolve_intent_promotes_parent_cip_when_primary_is_4_digit(
    monkeypatch: pytest.MonkeyPatch,
    stub_gemma_config: None,
) -> None:
    """Gemma swaps the fields → salvage by promoting parent_cip to primary."""
    payload = {
        "matched_cip": "13.10",             # umbrella, invalid as primary
        "matched_title": "Special Education and Teaching",
        "confidence": "medium",
        "reasoning": "Deaf ed is a subset of special education.",
        "parent_cip": "13.1001",            # the real 6-digit leaf
        "alternatives": [],
    }
    fake_generate = _make_generate_mock(payload)
    monkeypatch.setattr(intent.gemma_client, "generate", fake_generate)
    _install_school_catalog(monkeypatch, school_cips=[])

    result = intent.resolve_intent(
        major_text="deaf ed",
        school_name="Illinois State University",
        unitid=149772,
        programs=_programs_arg(),
    )
    assert result.matched_cip == "13.1001"
    assert result.matched_title == "Special Education and Teaching"


def test_resolve_intent_falls_back_to_school_catalog_descendant(
    monkeypatch: pytest.MonkeyPatch,
    stub_gemma_config: None,
) -> None:
    """Gemma returns a 4-digit family with no usable parent_cip → pick the
    lexicographically first descendant from the school's reported CIPs."""
    payload = {
        "matched_cip": "13.10",
        "matched_title": "Special Education and Teaching",
        "confidence": "medium",
        "reasoning": "Umbrella match.",
        "parent_cip": "13.10",              # also 4-digit — no help
        "alternatives": [],
    }
    fake_generate = _make_generate_mock(payload)
    monkeypatch.setattr(intent.gemma_client, "generate", fake_generate)
    _install_school_catalog(
        monkeypatch,
        school_cips=[
            {"cipcode": "13.1001", "program_name": "Education, General"},
            {"cipcode": "13.1011", "program_name": "Special Ed Admin"},
            {"cipcode": "13.1099", "program_name": "Special Ed, Other"},
            {"cipcode": "52.0201", "program_name": "Business Admin"},
        ],
    )

    result = intent.resolve_intent(
        major_text="special ed",
        school_name="Illinois State University",
        unitid=149772,
        programs=_programs_arg(),
    )
    # 13.1001 is lexicographically first among the 13.10 family; chosen
    # deterministically over the other two valid candidates.
    assert result.matched_cip == "13.1001"


def test_resolve_intent_raises_when_4_digit_has_no_parent_and_no_school_match(
    monkeypatch: pytest.MonkeyPatch,
    stub_gemma_config: None,
) -> None:
    """Last-resort fallback — no parent_cip, no school descendants → raise.

    This is the original behavior for malformed primaries; the salvage
    path only kicks in when we can produce a valid 6-digit leaf.
    """
    payload = {
        "matched_cip": "99.99",             # fictional umbrella
        "matched_title": "Made-Up Umbrella",
        "confidence": "medium",
        "reasoning": "n/a",
        "parent_cip": "99.99",
        "alternatives": [],
    }
    fake_generate = _make_generate_mock(payload)
    monkeypatch.setattr(intent.gemma_client, "generate", fake_generate)
    _install_school_catalog(
        monkeypatch,
        school_cips=[
            {"cipcode": "13.1001", "program_name": "Education, General"},
        ],
    )

    with pytest.raises(ValueError, match="malformed primary CIP"):
        intent.resolve_intent(
            major_text="nonsense",
            school_name="Anywhere State",
            unitid=42,
            programs=_programs_arg(),
        )


def test_promote_to_leaf_cip_is_identity_on_valid_6_digit() -> None:
    """Sanity: the salvage helper never perturbs an already-valid CIP."""
    assert (
        intent._promote_to_leaf_cip("13.1001", "13.10", school_cips=[])
        == "13.1001"
    )


# ---------------------------------------------------------------------------
# TestDeterministicShortCircuit — P0/P1 cases from §4 of
# bugfix-broad-cip-substitution-and-intent.md.
#
# These tests pin the invariants of the YAML short-circuit that was added
# in §6. Specifically:
#
#   - Known majors skip the Gemma intent call entirely (but the audit
#     step may still fire, per the existing contract).
#   - The returned IntentResult's parent_cip is derived from the school's
#     reported programs, NOT hardcoded to "". This is load-bearing for
#     the frontend's substitution affordance gate (MajorInput.tsx:102).
#   - Cache writes are owned by confirm_intent; the short-circuit does
#     not populate _intent_cache.
#   - Unknown majors fall through to Gemma unchanged.
# ---------------------------------------------------------------------------


def _iu_programs() -> list[dict[str, Any]]:
    """IU-Bloomington reports 52.01 (broad business) + 52.10 (HR).

    This mirrors the real IU program list used in
    ``tests/mcp/test_cip_substitution.py`` fixtures. Marketing/52.14 is
    NOT in this list — that is exactly the scenario the substitution
    flow was built for, and the scenario ``parent_cip`` must reflect.
    """
    return [
        {"cipcode": "52.01", "program_name": "Business/Commerce, General"},
        {"cipcode": "52.10", "program_name": "Human Resources"},
    ]


def _patch_gemma_and_audit_quiet(
    monkeypatch: pytest.MonkeyPatch,
    *,
    forbid_intent_generate: bool = False,
) -> dict[str, int]:
    """Install stubs that let the short-circuit run undisturbed.

    - ``gemma_client.generate`` is patched to either raise (when
      ``forbid_intent_generate`` is True — any call would be a bug because
      the short-circuit should skip Gemma entirely for known majors) or
      increment a call counter so the test can assert it was NOT called.
    - ``_audit_intent_mapping`` is patched to return None (the "audit
      quiets silently" fallback that the service already uses when the
      audit Gemma call fails).
    - ``mcp_client.get_server`` returns a stub whose ``query_iceberg``
      yields an empty list — so ``_get_school_cips`` (and any other
      Iceberg query the short-circuit triggers) returns []. That matches
      the Gemma path's behavior when there's no catalog on disk and keeps
      the short-circuit from hitting the real warehouse.
    """
    counters = {"generate_calls": 0}

    def _generate(**kwargs: Any) -> str:
        counters["generate_calls"] += 1
        if forbid_intent_generate:
            raise AssertionError(
                "gemma_client.generate must not be called on the "
                "deterministic short-circuit path."
            )
        return "{}"

    monkeypatch.setattr(intent.gemma_client, "generate", _generate)
    monkeypatch.setattr(intent, "_audit_intent_mapping", lambda *a, **kw: None)

    class _EmptyServer:
        def query_iceberg(self, sql: str) -> list[dict[str, Any]]:
            return []

    monkeypatch.setattr(intent.mcp_client, "get_server", lambda: _EmptyServer())
    return counters


class TestDeterministicShortCircuit:
    """The YAML-match short-circuit that Bug B's prompt rewrite stopped
    depending on Gemma's judgment for known majors."""

    def test_marketing_skips_gemma(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_gemma_config: None,
    ) -> None:
        """Exact "Marketing" input → YAML hit, Gemma is never called."""
        counters = _patch_gemma_and_audit_quiet(
            monkeypatch, forbid_intent_generate=True
        )

        result = intent.resolve_intent(
            major_text="Marketing",
            school_name="Indiana University-Bloomington",
            unitid=151351,
            programs=_iu_programs(),
        )

        assert result.matched_cip == "52.14"
        assert result.matched_title == "Marketing"
        assert result.confidence == "high"
        assert "major_to_cip.yaml" in result.reasoning.lower(), (
            "Reasoning must advertise the deterministic source so "
            "downstream UI / logs can distinguish this path from Gemma's"
        )
        # The short-circuit is the whole point — generate MUST NOT fire.
        assert counters["generate_calls"] == 0

    def test_parent_cip_set_when_school_reports_broad_family(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_gemma_config: None,
    ) -> None:
        """Marketing-at-IU: parent_cip = 52.01 (frontend substitution signal).

        This is the bug fix's core UX contract — if parent_cip is empty
        here, ``MajorInput.tsx:102`` renders "no substitution" on the
        confirm card while ``/build/outcomes`` silently substitutes.
        Confirm card lies → user confusion.
        """
        _patch_gemma_and_audit_quiet(monkeypatch)

        result = intent.resolve_intent(
            major_text="Marketing",
            school_name="Indiana University-Bloomington",
            unitid=151351,
            programs=_iu_programs(),
        )

        assert result.parent_cip == "52.01", (
            "IU reports the broad 52.01; parent_cip must surface it so "
            "the frontend substitution affordance lights up"
        )

    def test_parent_cip_empty_when_school_reports_specific_cip(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_gemma_config: None,
    ) -> None:
        """When the school reports 52.14 directly, no substitution is
        needed and parent_cip must be empty — anything else would cause
        the frontend to draw the substitution affordance for a school
        that doesn't need substitution."""
        _patch_gemma_and_audit_quiet(monkeypatch)

        result = intent.resolve_intent(
            major_text="Marketing",
            school_name="A School That Reports 52.14",
            unitid=999999,
            programs=[
                {"cipcode": "52.14", "program_name": "Marketing"},
                {"cipcode": "52.10", "program_name": "Human Resources"},
            ],
        )

        assert result.matched_cip == "52.14"
        assert result.parent_cip == "", (
            "Exact school-report of the cip4 → no substitution will "
            "apply; parent_cip must be empty"
        )

    def test_parent_cip_empty_when_no_same_family_broad(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_gemma_config: None,
    ) -> None:
        """Different-family programs: no same-family broad CIP exists,
        so no substitution parent to surface. Outcomes path will handle
        the miss via its broadening fallback; confirm card correctly
        shows no substitution affordance."""
        _patch_gemma_and_audit_quiet(monkeypatch)

        result = intent.resolve_intent(
            major_text="Marketing",
            school_name="Some Non-Business School",
            unitid=888888,
            programs=[
                {"cipcode": "11.07", "program_name": "Computer Science"},
                {"cipcode": "14.01", "program_name": "Engineering, General"},
            ],
        )

        assert result.matched_cip == "52.14"
        assert result.parent_cip == "", (
            "No same-family broad CIP in programs → parent_cip is empty"
        )

    def test_alias_match_skips_gemma(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_gemma_config: None,
    ) -> None:
        """Alias hits (e.g. 'mktg' for Marketing) take the short-circuit.

        Without alias support, users who type shorthand would fall
        through to Gemma and re-open the prompt-bias failure mode.
        """
        counters = _patch_gemma_and_audit_quiet(
            monkeypatch, forbid_intent_generate=True
        )

        result = intent.resolve_intent(
            major_text="mktg",
            school_name="Indiana University-Bloomington",
            unitid=151351,
            programs=_iu_programs(),
        )

        assert result.matched_cip == "52.14"
        assert result.matched_title == "Marketing"
        assert result.confidence == "high"
        assert counters["generate_calls"] == 0

    def test_unknown_major_falls_through_to_gemma(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_gemma_config: None,
    ) -> None:
        """Unknown-major inputs skip the short-circuit and call Gemma.

        The short-circuit is only for YAML-covered majors. Coverage gaps
        (Education 6-digit, entire Nursing family, etc. — tracked
        separately) must still reach Gemma or we'd regress those.
        """
        payload = {
            "matched_cip": "99.9999",
            "matched_title": "Truly Nonsense",
            "confidence": "low",
            "reasoning": "Guessing.",
            "parent_cip": "",
            "alternatives": [],
        }
        fake_generate = _make_generate_mock(payload)
        monkeypatch.setattr(intent.gemma_client, "generate", fake_generate)
        # Install the empty stub server so ``_get_school_cips`` / crosswalk
        # queries don't hit the real warehouse.
        _install_school_catalog(monkeypatch, school_cips=[])

        # "Underwater basket weaving" is explicitly called out in §1 of the
        # spec as the sentinel for "not in YAML → falls through to Gemma".
        # Gemma's response is structurally valid (99.9999 passes _CIP_PATTERN)
        # so resolve_intent returns normally rather than raising.
        result = intent.resolve_intent(
            major_text="Underwater basket weaving",
            school_name="Anywhere State",
            unitid=42,
            programs=_iu_programs(),
        )

        # At least one call to gemma_client.generate for the intent step.
        # (Audit would make it two, but that fires regardless.) What we
        # care about is that the call_log is non-empty — the
        # short-circuit did NOT skip Gemma.
        assert len(fake_generate.call_log) >= 1, (
            "Unknown-major input must still reach Gemma"
        )
        assert result.matched_cip == "99.9999"

    def test_short_circuit_does_not_write_cache(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_gemma_config: None,
    ) -> None:
        """After a YAML short-circuit hit, _intent_cache must be empty.

        Cache writes are owned by ``confirm_intent`` (the student clicks
        "yes, this is my major" → persisted). The short-circuit is part
        of resolve_intent and must not pre-populate the cache, or the
        student's subsequent clarifications would be silently ignored.
        """
        _patch_gemma_and_audit_quiet(monkeypatch)

        assert not intent._intent_cache, "Precondition: cache starts empty"

        intent.resolve_intent(
            major_text="Marketing",
            school_name="Indiana University-Bloomington",
            unitid=151351,
            programs=_iu_programs(),
        )

        # The cache key would be ("marketing", 151351) — a Gemma-path
        # resolve_intent does NOT write the cache either (only
        # confirm_intent does), so the short-circuit path must match.
        assert ("marketing", 151351) not in intent._intent_cache
        # Defensive: the entire cache must be empty since no other test
        # in this module mutates it (the autouse fixture clears it).
        assert intent._intent_cache == {}

    def test_short_circuit_runs_audit(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_gemma_config: None,
    ) -> None:
        """The audit step fires on the short-circuit path so audit_flag
        and audit_message propagate identically to the Gemma path.

        Rationale: the short-circuit trades Gemma's judgment for the
        YAML's known answer, but the audit is an *independent* safety
        net that catches adversarial inputs the YAML never considered.
        Short-circuiting the audit would silently drop that safety net.
        """
        audit_calls: list[tuple[str, str, str, list[str]]] = []

        def _fake_audit(
            student_input: str,
            matched_cip: str,
            matched_title: str,
            career_titles: list[str],
        ) -> dict[str, Any]:
            audit_calls.append(
                (student_input, matched_cip, matched_title, career_titles)
            )
            return {
                "valid": True,
                "tone": "playful_warning",
                "message": "Marketing is a real major. Proceed.",
            }

        # Same plumbing as _patch_gemma_and_audit_quiet, but we override
        # the audit patch with a real capturer.
        def _generate(**kwargs: Any) -> str:
            return "{}"

        monkeypatch.setattr(intent.gemma_client, "generate", _generate)
        monkeypatch.setattr(intent, "_audit_intent_mapping", _fake_audit)

        class _EmptyServer:
            def query_iceberg(self, sql: str) -> list[dict[str, Any]]:
                return []

        monkeypatch.setattr(
            intent.mcp_client, "get_server", lambda: _EmptyServer()
        )

        result = intent.resolve_intent(
            major_text="Marketing",
            school_name="Indiana University-Bloomington",
            unitid=151351,
            programs=_iu_programs(),
        )

        # Audit MUST have fired.
        assert len(audit_calls) == 1
        student_input, matched_cip, matched_title, _careers = audit_calls[0]
        assert student_input == "Marketing"
        assert matched_cip == "52.14"
        assert matched_title == "Marketing"
        # The audit's tone must propagate onto the result.
        assert result.audit_flag == "playful_warning"
        assert result.audit_message == "Marketing is a real major. Proceed."


# ---------------------------------------------------------------------------
# TestPromptCopy — P2 snapshot of the prompt body (post-rewrite).
#
# Guards against accidental regressions toward the pre-rewrite framing
# that caused Bug B: the old prompt's "these have earnings data" / "these
# have career path data" split biased Gemma toward school-reported CIPs.
# The rewrite (@fp-copywriter §10) explicitly tells Gemma the backend
# blends earnings and both CIP lists are equal match candidates.
# ---------------------------------------------------------------------------


class TestPromptCopy:
    """Lightweight snapshot of the _INTENT_SYSTEM_PROMPT body."""

    def test_prompt_does_not_bias_toward_school_cips(self) -> None:
        """The rewritten prompt must:

        - Kill the asymmetric labels that caused Bug B.
        - Explicitly direct Gemma to pick the most specific CIP.
        - Surface the "backend blends earnings" invariant so Gemma
          stops dodging the substitution flow to 'preserve' earnings.
        - Treat both CIP lists as equal candidates.
        """
        prompt = intent._INTENT_SYSTEM_PROMPT

        # The three exact strings the old prompt used to bias Gemma:
        # "(these have earnings data)" on the school list and "these
        # have career path data" on the crosswalk list. Either phrase
        # returning is a regression to Bug B.
        assert "these have earnings data" not in prompt, (
            "Old earnings-data bias phrase is back — this is the exact "
            "copy that caused Bug B"
        )
        assert "these have career path data" not in prompt, (
            "Old career-path-data framing is back — same bug"
        )

        # Positive assertions — the rewrite's load-bearing signals must
        # be present. Keep these loose (substring, case-insensitive) so
        # minor wording tweaks don't break the test, but the contract
        # itself does.
        lowered = prompt.lower()
        assert "most specific cip" in lowered, (
            "Prompt must instruct Gemma to pick the most specific CIP"
        )
        assert "blends earnings" in lowered or "blend earnings" in lowered, (
            "Prompt must tell Gemma the backend handles earnings blending"
        )
        # Format keys that _call_gemma_intent needs — if these drift the
        # .format() call will KeyError at runtime. Fail fast here.
        for key in ("{student_input}", "{school_name}",
                    "{school_cip_list}", "{crosswalk_cip_list}"):
            assert key in prompt, (
                f"Prompt is missing required format key {key!r}"
            )


class TestDeterministicIntentCall:
    """Intent Gemma calls must be reproducible for a given input.

    The Kaggle demo runs Gemma live — the same student typing the same
    major twice must not land on two different CIPs. Guaranteed by
    temperature=0 plus an input-derived seed; this test pins both.
    """

    def test_seed_is_deterministic_per_input(self) -> None:
        assert intent._derive_intent_seed("CS") == intent._derive_intent_seed("CS")
        assert intent._derive_intent_seed("CS") == intent._derive_intent_seed("cs")
        assert intent._derive_intent_seed("CS") == intent._derive_intent_seed("  CS  ")

    def test_seed_differs_across_inputs(self) -> None:
        assert intent._derive_intent_seed("CS") != intent._derive_intent_seed("nursing")

    def test_seed_is_openai_compatible_32bit_uint(self) -> None:
        seed = intent._derive_intent_seed("pre-PT")
        assert 0 <= seed < 2**32

    def test_gemma_call_uses_temperature_zero_and_seed(
        self,
        monkeypatch: pytest.MonkeyPatch,
        intent_fixtures: dict[str, dict[str, Any]],
        stub_server: _StubServer,
        stub_gemma_config: None,
    ) -> None:
        captured: dict[str, Any] = {}

        def _generate(**kwargs: Any) -> str:
            if not captured:
                captured.update(kwargs)
            return json.dumps(intent_fixtures["high"])

        monkeypatch.setattr(intent.gemma_client, "generate", _generate)

        intent.resolve_intent(
            major_text="pre-PT",
            school_name="University of Central Anywhere",
            unitid=123456,
            programs=_programs_arg(),
        )

        assert captured["temperature"] == 0.0, (
            "Intent calls must run at temperature=0 for demo reproducibility"
        )
        assert captured["seed"] == intent._derive_intent_seed("pre-PT"), (
            "Intent calls must pass an input-derived seed for demo reproducibility"
        )


# ---------------------------------------------------------------------------
# TestYamlGate — INTENT_YAML_ENABLED env-var contract.
#
# Spec: docs/specs/bugfix-disable-intent-yaml-regression.md.
#
# The gate's contract: env-var read per `resolve_intent` call (NOT at module
# import). The default (unset) preserves today's YAML short-circuit. Setting
# INTENT_YAML_ENABLED=false skips `major_lookup.lookup_major` entirely so
# every input is routed through Gemma — what the regression script needs.
# ---------------------------------------------------------------------------


class TestYamlGate:
    """Env-var gate that lets the regression script disable the YAML."""

    def test_env_false_skips_yaml(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_gemma_config: None,
    ) -> None:
        """INTENT_YAML_ENABLED=false → major_lookup.lookup_major is NOT called.

        The regression script needs every input to hit Gemma so we can
        compare Gemma's answer against the YAML's curated answer. If
        the gate leaks (lookup_major still fires), the comparison is
        contaminated by YAML hits.
        """
        # Marketing is a known YAML hit — same fixture as the
        # short-circuit tests above. With the gate off, the YAML must
        # be skipped and Gemma must run instead.
        monkeypatch.setenv("INTENT_YAML_ENABLED", "false")

        def _explode(_text: str) -> Any:
            raise AssertionError(
                "major_lookup.lookup_major must not be called when "
                "INTENT_YAML_ENABLED=false"
            )

        monkeypatch.setattr(intent.major_lookup, "lookup_major", _explode)

        # Gemma stand-in: a structurally valid response so resolve_intent
        # returns normally. We're testing the gate, not the Gemma path.
        payload = {
            "matched_cip": "52.1401",
            "matched_title": "Marketing",
            "confidence": "high",
            "reasoning": "Direct match.",
            "parent_cip": "52.14",
            "alternatives": [],
        }
        fake_generate = _make_generate_mock(payload)
        monkeypatch.setattr(intent.gemma_client, "generate", fake_generate)
        _install_school_catalog(monkeypatch, school_cips=[])

        result = intent.resolve_intent(
            major_text="Marketing",
            school_name="Indiana University-Bloomington",
            unitid=151351,
            programs=[],
        )

        # Gemma's answer wins because the YAML was skipped.
        assert result.matched_cip == "52.1401"
        assert len(fake_generate.call_log) >= 1, (
            "Gate-off path must reach Gemma instead of the YAML"
        )

    def test_default_preserves_behavior(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_gemma_config: None,
    ) -> None:
        """Env unset (or =true) → YAML short-circuit fires, Gemma is skipped.

        The bugfix ships the gate defaulting to "true" so merging it is
        a no-op in production. This test pins that default by using the
        same "Marketing → 52.14, no Gemma" expectation as the existing
        short-circuit tests.
        """
        monkeypatch.delenv("INTENT_YAML_ENABLED", raising=False)
        counters = _patch_gemma_and_audit_quiet(
            monkeypatch, forbid_intent_generate=True
        )

        result = intent.resolve_intent(
            major_text="Marketing",
            school_name="Indiana University-Bloomington",
            unitid=151351,
            programs=_iu_programs(),
        )

        assert result.matched_cip == "52.14"
        assert result.confidence == "high"
        assert "major_to_cip.yaml" in result.reasoning.lower()
        assert counters["generate_calls"] == 0, (
            "Default (env unset) must preserve the YAML short-circuit "
            "and skip Gemma entirely"
        )

        # Explicit "true" must also preserve the short-circuit.
        intent._intent_cache.clear()
        monkeypatch.setenv("INTENT_YAML_ENABLED", "true")
        result = intent.resolve_intent(
            major_text="Marketing",
            school_name="Indiana University-Bloomington",
            unitid=151351,
            programs=_iu_programs(),
        )
        assert result.matched_cip == "52.14"
        assert counters["generate_calls"] == 0, (
            "Explicit INTENT_YAML_ENABLED=true must preserve the "
            "YAML short-circuit"
        )


# ---------------------------------------------------------------------------
# Multi-CIP: _sanitize_alternatives respects max_alts and parent_cip
# ---------------------------------------------------------------------------


def test_sanitize_alternatives_respects_max_alts() -> None:
    """When max_alts=2, only the first 2 valid alternatives survive
    even if more are present."""
    raw = [
        {"cip": "52.0801", "title": "Finance", "why": "ok"},
        {"cip": "52.1401", "title": "Marketing", "why": "ok"},
        {"cip": "52.0701", "title": "Entrepreneurship", "why": "ok"},
    ]
    cleaned = intent._sanitize_alternatives(raw, primary_cip="52.0201", max_alts=2)
    assert cleaned is not None
    assert len(cleaned) == 2
    assert [a["cip"] for a in cleaned] == ["52.0801", "52.1401"]


def test_sanitize_alternatives_preserves_parent_cip() -> None:
    """When an alternative carries a parent_cip field, _sanitize_alternatives
    preserves it on the output dict."""
    raw = [
        {
            "cip": "14.1001",
            "title": "Electrical Engineering",
            "why": "Circuits",
            "parent_cip": "14.10",
        },
        {
            "cip": "14.1901",
            "title": "Mechanical Engineering",
            "why": "Physical systems",
            # No parent_cip — should be absent from output.
        },
    ]
    cleaned = intent._sanitize_alternatives(raw, primary_cip="14.0901")
    assert cleaned is not None
    assert len(cleaned) == 2
    assert cleaned[0]["parent_cip"] == "14.10"
    assert "parent_cip" not in cleaned[1]


def test_promote_to_leaf_called_for_each_alternative() -> None:
    """Each alternative CIP goes through _promote_to_leaf_cip inside
    _sanitize_alternatives (indirectly, via the streaming path in
    set_your_course._build_intent_result_from_tail).

    We test the contract at the _sanitize_alternatives boundary: 4-digit
    alternative CIPs that would fail the _CIP_PATTERN regex are dropped.
    The streaming path calls _promote_to_leaf_cip BEFORE passing to
    _sanitize_alternatives. So if promotion fails, the 4-digit CIP
    reaches the sanitizer and gets dropped — which is the correct
    behavior. We verify both: a valid 6-digit survives, a 4-digit
    that cannot be promoted is dropped.
    """
    raw = [
        # Valid 6-digit: passes regex, survives.
        {"cip": "14.1001", "title": "Electrical Engineering", "why": "ok"},
        # 4-digit (umbrella): fails the strict XX.XXXX regex, dropped.
        {"cip": "14.19", "title": "Mechanical Umbrella", "why": "too broad"},
        # Another valid 6-digit.
        {"cip": "14.1901", "title": "Mechanical Engineering", "why": "ok"},
    ]
    cleaned = intent._sanitize_alternatives(raw, primary_cip="14.0901")
    assert cleaned is not None
    assert len(cleaned) == 2
    assert [a["cip"] for a in cleaned] == ["14.1001", "14.1901"]
    # The 4-digit "14.19" was dropped — it would need to go through
    # _promote_to_leaf_cip in the streaming path before reaching here.
