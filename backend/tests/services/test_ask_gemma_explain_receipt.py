"""Unit tests for the ERN explain-this-stat receipt path.

Spec: docs/specs/feature-explain-stat-receipt.md (DRAFT v1.3) §4 Service
Changes + §4 Testing Impact Analysis (P0 / P1 rows). Phase 3 implementation
landed in commit 098fb20 — these tests bind the actual contract.

Coverage scope (per §4 New Tests Required, P0/P1 rows):

- ``_postprocess_ern_explain_receipt``: happy path, all four percentile-
  null permutations, JSON-decode failure, Pydantic-extra-field rejection,
  Pydantic-missing-required-field rejection, sentinel-passthrough across
  every prose field × every sentinel pattern, stat_code mismatch,
  truncated why_mix_paragraph, math_line unconditional overwrite,
  label normalization (canonical match + label-swap recovery),
  ``_extract_json_objects`` integration (markdown-fenced + trailing-prose
  recovery), structured-record logging on every parse-success and
  parse-failure path.
- ``_render_math_line``: balanced effort (no second line), focused
  effort (lifts), chill effort (brings), Unicode arrow.

All tests use module-level fixtures and direct constructors — no
DuckDB, no MCP, no Gemma client. Production code (Pydantic models,
post-processor, math renderer, label normalizer, log writer) is the
real implementation; only Gemma's input string is fabricated per case.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest

from app.models.api import (
    ExplainStatReceipt,
    ReceiptSource,
)
from app.models.career import (
    BossScores,
    Build,
    CareerOutcome,
    GauntletResult,
    PentagonStats,
)
from app.services import ask_gemma, gemma_client
from app.services.ask_gemma import (
    _ERN_LABEL_ALLOWLIST,
    _normalize_label,
    _postprocess_ern_explain_receipt,
    _render_math_line,
)

# ---------------------------------------------------------------------------
# Build / tool-log fixtures
# ---------------------------------------------------------------------------

# Indiana University-Bloomington → CS → Software Developer (the happy
# path build mentioned in the spec's Test Data Requirements). Direct-
# constructor; never persisted to DuckDB.
_IU_UNITID = 151351
_IU_CIPCODE = "11.0701"
_IU_SOC = "15-1252"


def _make_build(
    *,
    ern: int | None = 7,
    effort: str = "balanced",
    school: str = "Indiana University-Bloomington",
    program: str = "Computer Science",
    occupation: str = "Software Developer",
    soc: str = _IU_SOC,
    cipcode: str = _IU_CIPCODE,
    unitid: int = _IU_UNITID,
) -> Build:
    """Direct-constructor Build — no MCP, no DuckDB. Default stats fit
    the happy-path build; override `ern` to None for the score-null
    guard test."""
    return Build(
        build_id="iu-cs-test-001",
        created_at="2026-05-02T00:00:00Z",
        school_name=school,
        unitid=unitid,
        major_text=program,
        cipcode=cipcode,
        program_name=program,
        effort=effort,  # type: ignore[arg-type]
        loan_pct=1.0,
        career=CareerOutcome(
            unitid=unitid,
            institution_name=school,
            cipcode=cipcode,
            program_name=program,
            soc_code=soc,
            occupation_title=occupation,
            stats=PentagonStats(ern=ern, roi=6, res=5, grw=8, aura=4),
            bosses=BossScores(ai=10, loans=10, market=10, burnout=10, ceiling=10),
            median_annual_wage=132270.0,
            earnings_1yr_median=94200.0,
        ),
        gauntlet=GauntletResult(
            fights=[], wins=0, losses=0, draws=0, unknown=0, verdict="OK"
        ),
        branches=[],
        skill_recs=[],
        guidance="",
        skills_crafted=[],
        skill_pool=[],
        profile_name="Test Profile",
    )


def _make_tool_log(
    *,
    cip_rank: float | None = 0.87,
    earnings: int | None = 94_200,
    wage_pct: float | None = 0.92,
    wage: int | None = 132_270,
    soc: str = _IU_SOC,
    unitid: int = _IU_UNITID,
    cipcode: str = _IU_CIPCODE,
) -> list[gemma_client.ToolCallTurn]:
    """Build the cached tool_call_log shape that ``_extract_tool_results``
    pulls percentiles + dollars out of. Mirrors the on-the-wire JSON that
    the MCP server serializes for the two ERN tools. Setting any value
    to None reproduces the corresponding null-percentile permutation."""
    career_payload: dict[str, Any] = {
        "results": [
            {
                "soc_code": soc,
                "cip_family_earnings_rank": cip_rank,
                "earnings_1yr_median": earnings,
            }
        ]
    }
    occupation_payload: dict[str, Any] = {
        "wage_percentile_overall": wage_pct,
        "median_annual_wage": wage,
    }

    return [
        gemma_client.ToolCallTurn(
            turn_number=0,
            tool_name="get_career_paths",
            tool_args={"unitid": unitid, "cipcode": cipcode},
            tool_result_size_bytes=200,
            duration_ms=12,
            error=None,
            tool_result_preview=json.dumps(career_payload),
            dispatch_index=0,
        ),
        gemma_client.ToolCallTurn(
            turn_number=0,
            tool_name="get_occupation_data",
            tool_args={"soc_code": soc},
            tool_result_size_bytes=200,
            duration_ms=15,
            error=None,
            tool_result_preview=json.dumps(occupation_payload),
            dispatch_index=1,
        ),
    ]


def _good_receipt_json(
    *,
    stat_code: str = "ERN",
    score: int = 7,
    extra: dict[str, Any] | None = None,
    drop: str | None = None,
    override: dict[str, Any] | None = None,
    component_overrides: list[dict[str, Any]] | None = None,
) -> str:
    """Build a Gemma-shaped JSON string for the receipt. Toggle individual
    fields (``override``), add an unsanctioned key (``extra``), drop a
    required key (``drop``), or override per-component fields
    (``component_overrides``: a list of partial dicts applied to
    ``components[i]`` in order)."""
    payload: dict[str, Any] = {
        "kind": "receipt",
        "stat_code": stat_code,
        "stat_name": "Earning Power",
        "score": score,
        "score_max": 10,
        "one_liner": (
            "Earning Power tells you how much your degree usually pays "
            "right after graduation."
        ),
        "components": [
            {
                "weight_pct": 60,
                "label": "your school's program rank",
                "explainer": (
                    "IU Bloomington's Computer Science grads earn a "
                    "median of $94,200 — that lands at the 87th "
                    "percentile (out of 100 programs, this one ranks "
                    "higher than about 86) of all CS programs."
                ),
                "value_pct": 87,
                "anchor_text": "Indiana University Computer Science grads",
                "anchor_dollars": 94_200,
                "missing_reason": None,
            },
            {
                "weight_pct": 40,
                "label": "this career's pay rank",
                "explainer": (
                    "Software Developer median pay is $132,270, which "
                    "sits at the 92nd percentile."
                ),
                "value_pct": 92,
                "anchor_text": "Software Developer",
                "anchor_dollars": 132_270,
                "missing_reason": None,
            },
        ],
        "math_line": "0.6 × 0.87 + 0.4 × 0.92 → score 9/10",
        "sources": [
            {
                "label": "Graduate earnings",
                "name": "College Scorecard (U.S. Department of Education)",
            },
            {
                "label": "Occupation wages",
                "name": (
                    "Occupational Outlook Handbook, published by the "
                    "Bureau of Labor Statistics (BLS)"
                ),
            },
        ],
        "why_mix_paragraph": (
            "Picture two students. One in a top-ranked CS program at "
            "a regional school, one in a mid-tier Philosophy program "
            "at a flagship. School rank alone would mislead you. "
            "Mixing in occupation pay grounds the score in real "
            "salaries — that's why we blend both."
        ),
    }
    if override:
        payload.update(override)
    if extra:
        payload.update(extra)
    if drop:
        payload.pop(drop, None)
    if component_overrides:
        for idx, patch in enumerate(component_overrides):
            payload["components"][idx].update(patch)
    return json.dumps(payload)


# ---------------------------------------------------------------------------
# _postprocess_ern_explain_receipt — happy + score override
# ---------------------------------------------------------------------------


def test_postprocess_happy_path() -> None:
    """Valid Gemma JSON → parsed ExplainStatReceipt with all fields
    populated; both percentiles present (P0)."""
    build = _make_build()
    log = _make_tool_log()
    receipt = _postprocess_ern_explain_receipt(
        raw=_good_receipt_json(),
        build=build,
        tool_call_log=log,
        backend="ollama",
    )

    assert receipt is not None
    assert isinstance(receipt, ExplainStatReceipt)
    assert receipt.stat_code == "ERN"
    assert receipt.kind == "receipt"
    assert receipt.score == 7  # build.career.stats.ern
    assert receipt.score_max == 10
    assert len(receipt.components) == 2

    # Components are server-stamped from tool_call_log percentiles.
    by_weight = {c.weight_pct: c for c in receipt.components}
    assert by_weight[60].value_pct == 87
    assert by_weight[60].anchor_dollars == 94_200
    assert by_weight[60].missing_reason is None
    assert by_weight[40].value_pct == 92
    assert by_weight[40].anchor_dollars == 132_270
    assert by_weight[40].missing_reason is None

    # Sources are server-stamped from the canonical _ERN_RECEIPT_SOURCES.
    assert len(receipt.sources) == 2
    assert all(isinstance(s, ReceiptSource) for s in receipt.sources)

    # Math line is server-rendered. cip=0.87 wage=0.92 → raw=0.89 →
    # unshifted=9/10; on balanced effort the math_line shows the
    # unshifted derivation (the post-processor still server-stamps the
    # receipt.score field separately to the build's authoritative 7).
    assert "0.6 × 0.87 + 0.4 × 0.92" in receipt.math_line
    assert "score 9/10" in receipt.math_line  # unshifted derivation


def test_postprocess_overrides_score_from_build() -> None:
    """Gemma emits score 99; server stamps build.career.stats.ern (7)."""
    build = _make_build(ern=7)
    log = _make_tool_log()
    raw = _good_receipt_json(score=99)

    receipt = _postprocess_ern_explain_receipt(
        raw=raw, build=build, tool_call_log=log, backend="ollama"
    )

    # Pydantic ge=1/le=10 would reject score=99, so the test verifies the
    # server stamp behaviour by setting Gemma's score to a valid-but-wrong
    # number. Re-run the assertion with score=2.
    raw_valid_wrong = _good_receipt_json(score=2)
    receipt = _postprocess_ern_explain_receipt(
        raw=raw_valid_wrong, build=build, tool_call_log=log, backend="ollama"
    )
    assert receipt is not None
    assert receipt.score == 7  # build's score, not Gemma's 2


# ---------------------------------------------------------------------------
# _postprocess_ern_explain_receipt — null-percentile permutations
# ---------------------------------------------------------------------------


def test_postprocess_school_rank_null() -> None:
    """cip_family_earnings_rank null → 60% component value_pct null,
    missing_reason set, math_line shows n/a for the 60% piece (P0)."""
    build = _make_build()
    log = _make_tool_log(cip_rank=None, earnings=None)
    receipt = _postprocess_ern_explain_receipt(
        raw=_good_receipt_json(),
        build=build,
        tool_call_log=log,
        backend="ollama",
    )

    assert receipt is not None
    by_weight = {c.weight_pct: c for c in receipt.components}
    assert by_weight[60].value_pct is None
    assert by_weight[60].anchor_dollars is None
    assert by_weight[60].missing_reason is not None
    # 40% piece still has data.
    assert by_weight[40].value_pct == 92
    assert by_weight[40].missing_reason is None
    # Math line shows n/a for the 60% piece, real value for the 40% piece.
    assert "0.6 × n/a" in receipt.math_line
    assert "0.4 × 0.92" in receipt.math_line


def test_postprocess_occupation_pct_null() -> None:
    """wage_percentile_overall null → 40% component value_pct null,
    missing_reason set, math_line shows n/a for the 40% piece (P0)."""
    build = _make_build()
    log = _make_tool_log(wage_pct=None, wage=None)
    receipt = _postprocess_ern_explain_receipt(
        raw=_good_receipt_json(),
        build=build,
        tool_call_log=log,
        backend="ollama",
    )

    assert receipt is not None
    by_weight = {c.weight_pct: c for c in receipt.components}
    assert by_weight[40].value_pct is None
    assert by_weight[40].anchor_dollars is None
    assert by_weight[40].missing_reason is not None
    assert by_weight[60].value_pct == 87
    assert by_weight[60].missing_reason is None
    assert "0.6 × 0.87" in receipt.math_line
    assert "0.4 × n/a" in receipt.math_line


def test_postprocess_both_null() -> None:
    """Both percentiles null → receipt parses; math_line shows n/a for
    both pieces (P0)."""
    build = _make_build()
    log = _make_tool_log(
        cip_rank=None, earnings=None, wage_pct=None, wage=None
    )
    receipt = _postprocess_ern_explain_receipt(
        raw=_good_receipt_json(),
        build=build,
        tool_call_log=log,
        backend="ollama",
    )

    assert receipt is not None
    assert all(c.value_pct is None for c in receipt.components)
    assert all(c.anchor_dollars is None for c in receipt.components)
    assert all(c.missing_reason is not None for c in receipt.components)
    assert "0.6 × n/a" in receipt.math_line
    assert "0.4 × n/a" in receipt.math_line


# ---------------------------------------------------------------------------
# _postprocess_ern_explain_receipt — failure modes
# ---------------------------------------------------------------------------


def test_postprocess_invalid_json_returns_none() -> None:
    """Unparseable string → returns None (P0)."""
    build = _make_build()
    log = _make_tool_log()
    receipt = _postprocess_ern_explain_receipt(
        raw="this is not even close to JSON {{{{ broken",
        build=build,
        tool_call_log=log,
        backend="ollama",
    )
    assert receipt is None


def test_postprocess_extra_field_rejected() -> None:
    """Gemma adds confidence: 0.8 → Pydantic extra='forbid' rejects → None."""
    build = _make_build()
    log = _make_tool_log()
    raw = _good_receipt_json(extra={"confidence": 0.8})
    receipt = _postprocess_ern_explain_receipt(
        raw=raw, build=build, tool_call_log=log, backend="ollama"
    )
    assert receipt is None


def test_postprocess_missing_required_field() -> None:
    """Gemma omits why_mix_paragraph → Pydantic rejects → None (P0)."""
    build = _make_build()
    log = _make_tool_log()
    raw = _good_receipt_json(drop="why_mix_paragraph")
    receipt = _postprocess_ern_explain_receipt(
        raw=raw, build=build, tool_call_log=log, backend="ollama"
    )
    assert receipt is None


def test_postprocess_rejects_wrong_stat_code() -> None:
    """Gemma emits stat_code='ROI' for an ERN explain → None (P0).

    Pydantic accepts ROI (it's in the Literal); the post-processor's
    Step 4 stat_code assertion rejects the cross-stat drift."""
    build = _make_build()
    log = _make_tool_log()
    raw = _good_receipt_json(stat_code="ROI")
    receipt = _postprocess_ern_explain_receipt(
        raw=raw, build=build, tool_call_log=log, backend="ollama"
    )
    assert receipt is None


def test_postprocess_rejects_truncated_why_mix_paragraph() -> None:
    """Gemma emits why_mix_paragraph longer than 800 chars → Pydantic
    max_length rejects → None → fallback fires (P0)."""
    build = _make_build()
    log = _make_tool_log()
    long_paragraph = "x" * 801
    raw = _good_receipt_json(override={"why_mix_paragraph": long_paragraph})
    receipt = _postprocess_ern_explain_receipt(
        raw=raw, build=build, tool_call_log=log, backend="ollama"
    )
    assert receipt is None


def test_postprocess_returns_none_when_build_score_null() -> None:
    """build.career.stats.ern is None → score_null → returns None (P0)."""
    build = _make_build(ern=None)
    log = _make_tool_log()
    receipt = _postprocess_ern_explain_receipt(
        raw=_good_receipt_json(),
        build=build,
        tool_call_log=log,
        backend="ollama",
    )
    assert receipt is None


# ---------------------------------------------------------------------------
# _postprocess_ern_explain_receipt — extraction (markdown fence + prose)
# ---------------------------------------------------------------------------


def test_postprocess_uses_extract_json_objects_first() -> None:
    """Markdown-fenced ```json{...}``` payload parses (P0).

    Plain json.loads would fail on the fence; _extract_json_objects
    strips it before parsing."""
    build = _make_build()
    log = _make_tool_log()
    inner = _good_receipt_json()
    fenced = f"```json\n{inner}\n```"
    receipt = _postprocess_ern_explain_receipt(
        raw=fenced, build=build, tool_call_log=log, backend="ollama"
    )
    assert receipt is not None
    assert receipt.stat_code == "ERN"


def test_postprocess_extract_handles_trailing_prose() -> None:
    """`Here is the receipt: {valid JSON}` parses via brace-depth
    extraction (P0)."""
    build = _make_build()
    log = _make_tool_log()
    inner = _good_receipt_json()
    wrapped = f"Here is the receipt: {inner}"
    receipt = _postprocess_ern_explain_receipt(
        raw=wrapped, build=build, tool_call_log=log, backend="ollama"
    )
    assert receipt is not None
    assert receipt.stat_code == "ERN"


# ---------------------------------------------------------------------------
# _postprocess_ern_explain_receipt — math_line unconditional overwrite
# ---------------------------------------------------------------------------


def test_postprocess_overwrites_math_line_unconditionally() -> None:
    """Gemma writes 'I made this up'; server overwrites with the actual
    _render_math_line output. The Gemma-supplied string NEVER appears
    in the receipt (P0)."""
    build = _make_build()
    log = _make_tool_log()
    raw = _good_receipt_json(override={"math_line": "I made this up"})
    receipt = _postprocess_ern_explain_receipt(
        raw=raw, build=build, tool_call_log=log, backend="ollama"
    )
    assert receipt is not None
    # Gemma's bogus string MUST not survive.
    assert "I made this up" not in receipt.math_line
    # The server-built derivation MUST be present.
    assert "0.6 × 0.87" in receipt.math_line
    assert "0.4 × 0.92" in receipt.math_line


# ---------------------------------------------------------------------------
# _postprocess_ern_explain_receipt — sentinel passthrough rejection
# ---------------------------------------------------------------------------

# Each sentinel pattern × every prose field. The validator MUST reject
# every combination (Gemma echoing the appendix's __FILL_IN__ markers
# verbatim is a silent correctness failure mode without this guard).
_SENTINEL_VALUES: tuple[str, ...] = (
    "__FILL_IN__",
    "[FILL_IN]",
    "<FILL_IN>",
    # Tightened per @faang-staff-engineer M1 finding — naked
    # "placeholder" can appear in legitimate prose, so the sentinel
    # form requires the underscored / bracketed wrapper.
    "__PLACEHOLDER__",
    "ONE-SENTENCE DEFINITION HERE",
)


@pytest.mark.parametrize("sentinel", _SENTINEL_VALUES)
@pytest.mark.parametrize(
    "field",
    [
        "one_liner",
        "why_mix_paragraph",
        "components.0.explainer",
        "components.0.anchor_text",
    ],
)
def test_postprocess_rejects_sentinel_passthrough(
    sentinel: str, field: str
) -> None:
    """Gemma echoes the appendix sentinel verbatim → field_validator
    raises → None → fallback fires. Covers all 5 sentinel patterns ×
    4 prose fields (P0). genai-architect v1.2 re-review concern."""
    build = _make_build()
    log = _make_tool_log()
    if field.startswith("components."):
        _, idx_str, sub = field.split(".")
        idx = int(idx_str)
        component_overrides: list[dict[str, Any]] = [{}] * 2
        component_overrides[idx] = {sub: sentinel}
        raw = _good_receipt_json(component_overrides=component_overrides)
    else:
        raw = _good_receipt_json(override={field: sentinel})

    receipt = _postprocess_ern_explain_receipt(
        raw=raw, build=build, tool_call_log=log, backend="ollama"
    )
    assert receipt is None, (
        f"sentinel {sentinel!r} in field {field!r} should have triggered "
        f"the validator and returned None"
    )


# ---------------------------------------------------------------------------
# _postprocess_ern_explain_receipt — label normalization
# ---------------------------------------------------------------------------


def test_postprocess_label_normalization_match_by_weight() -> None:
    """Gemma emits weight=60 + label='program rank' (off-script) →
    _normalize_label matches by weight_pct=60 → replaces with the
    canonical 'your school's program rank'. Decision 14 (P0)."""
    build = _make_build()
    log = _make_tool_log()
    raw = _good_receipt_json(
        component_overrides=[
            {"label": "program rank"},  # off-script — should normalize
            {},  # 40% piece untouched
        ]
    )
    receipt = _postprocess_ern_explain_receipt(
        raw=raw, build=build, tool_call_log=log, backend="ollama"
    )
    assert receipt is not None
    by_weight = {c.weight_pct: c for c in receipt.components}
    # Server replaced Gemma's "program rank" with the canonical label.
    assert by_weight[60].label == "your school's program rank"
    # 40% piece left as-is (already canonical).
    assert by_weight[40].label == "this career's pay rank"


def test_postprocess_label_normalization_handles_swap() -> None:
    """Gemma swaps the labels (60% carries the 40% canonical, vice
    versa) → match-by-weight catches the swap → both labels normalized
    to their per-weight canonical forms (P0)."""
    build = _make_build()
    log = _make_tool_log()
    raw = _good_receipt_json(
        component_overrides=[
            {"label": "this career's pay rank"},  # canonical-but-wrong-weight
            {"label": "your school's program rank"},
        ]
    )
    receipt = _postprocess_ern_explain_receipt(
        raw=raw, build=build, tool_call_log=log, backend="ollama"
    )
    assert receipt is not None
    by_weight = {c.weight_pct: c for c in receipt.components}
    assert by_weight[60].label == "your school's program rank"
    assert by_weight[40].label == "this career's pay rank"


# ---------------------------------------------------------------------------
# _log_receipt_parse — structured logging on success + every failure
# ---------------------------------------------------------------------------


def test_postprocess_logs_structured_record_on_success(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """After a successful parse, _log_receipt_parse writes one INFO-
    level structured record carrying call_site=explain_ern_receipt,
    parse_success=True, plus build_id, backend, json_prefix (P0)."""
    build = _make_build()
    log = _make_tool_log()
    with caplog.at_level(logging.INFO, logger=ask_gemma.logger.name):
        receipt = _postprocess_ern_explain_receipt(
            raw=_good_receipt_json(),
            build=build,
            tool_call_log=log,
            backend="ollama",
        )

    assert receipt is not None
    success_records = [
        r for r in caplog.records if "ern_explain_receipt parsed" in r.message
    ]
    assert len(success_records) == 1
    rec_text = success_records[0].getMessage()
    assert "'parse_success': True" in rec_text
    assert "'failure_reason': None" in rec_text
    assert "'call_site': 'explain_ern_receipt'" in rec_text
    assert build.build_id in rec_text
    assert "'backend': 'ollama'" in rec_text


@pytest.mark.parametrize(
    "raw_factory_label,raw_factory,expected_reason",
    [
        (
            "json_decode",
            lambda: "this is { broken json",
            "json_decode",
        ),
        (
            "pydantic_validation",
            lambda: _good_receipt_json(extra={"confidence": 0.8}),
            "pydantic_validation",
        ),
        (
            "stat_code_mismatch",
            lambda: _good_receipt_json(stat_code="ROI"),
            "stat_code_mismatch",
        ),
    ],
)
def test_postprocess_logs_structured_record_on_failure(
    caplog: pytest.LogCaptureFixture,
    raw_factory_label: str,
    raw_factory,
    expected_reason: str,
) -> None:
    """After a parse failure, _log_receipt_parse writes one WARNING
    record with the matching failure_reason. Covers json_decode,
    pydantic_validation, stat_code_mismatch (P0). The score_null
    branch is covered by its own test below (different build state
    needed)."""
    build = _make_build()
    log = _make_tool_log()
    with caplog.at_level(logging.WARNING, logger=ask_gemma.logger.name):
        receipt = _postprocess_ern_explain_receipt(
            raw=raw_factory(),
            build=build,
            tool_call_log=log,
            backend="ollama",
        )

    assert receipt is None
    failure_records = [
        r for r in caplog.records
        if "ern_explain_receipt parse failed" in r.message
    ]
    assert len(failure_records) == 1, (
        f"{raw_factory_label}: expected exactly 1 failure log record, "
        f"got {[r.getMessage() for r in failure_records]}"
    )
    rec_text = failure_records[0].getMessage()
    assert "'parse_success': False" in rec_text
    assert f"'failure_reason': '{expected_reason}'" in rec_text


def test_postprocess_logs_score_null_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The fourth failure_reason — score_null — fires when
    build.career.stats.ern is None (P0)."""
    build = _make_build(ern=None)
    log = _make_tool_log()
    with caplog.at_level(logging.WARNING, logger=ask_gemma.logger.name):
        receipt = _postprocess_ern_explain_receipt(
            raw=_good_receipt_json(),
            build=build,
            tool_call_log=log,
            backend="ollama",
        )
    assert receipt is None
    failure_records = [
        r for r in caplog.records
        if "ern_explain_receipt parse failed" in r.message
    ]
    assert len(failure_records) == 1
    assert "'failure_reason': 'score_null'" in failure_records[0].getMessage()


# ---------------------------------------------------------------------------
# _render_math_line — effort branching (Decision 13)
# ---------------------------------------------------------------------------


def test_render_math_line_balanced_effort() -> None:
    """effort='balanced' → simple form, no effort line (P0)."""
    line = _render_math_line(
        cip_rank=0.87,
        wage_pct=0.92,
        build_score=9,
        score_max=10,
        effort="balanced",
    )
    assert line == "0.6 × 0.87 + 0.4 × 0.92 → score 9/10"
    assert "\n" not in line  # no second line


def test_render_math_line_focused_effort() -> None:
    """effort='focused' → unshifted derivation + 'lifts' effort line.

    cip=0.70, wage=0.80 → raw=0.74 → unshifted = int(1+9*0.74+0.5) = 8/10.
    Build score is 9 after the focused-effort lift; the effort line
    names the bump. The first line MUST show the unshifted derivation,
    not the build's score (P0). Decision 13."""
    line = _render_math_line(
        cip_rank=0.70,
        wage_pct=0.80,
        build_score=9,
        score_max=10,
        effort="focused",
    )
    # First line shows unshifted derivation.
    parts = line.split("\n")
    assert len(parts) == 2, f"expected 2-line output, got: {line!r}"
    assert parts[0] == "0.6 × 0.70 + 0.4 × 0.80 → score 8/10"
    # Second line names the focused-effort lift.
    assert "**Focused**" in parts[1]
    assert "lifts" in parts[1]
    assert "9/10" in parts[1]


def test_render_math_line_working_hard_effort() -> None:
    """effort='working_hard' → 'brings' effort line (score drops).
    cip=0.70, wage=0.80 → unshifted=8/10. Build score is 6 after a
    working-hard effort drop; the effort line uses 'brings' (not
    'lifts') because the build score went DOWN. Decision 13. Uses
    the friendly label 'Working Hard' (B2 fix — effort.capitalize()
    would have rendered 'Working_hard')."""
    line = _render_math_line(
        cip_rank=0.70,
        wage_pct=0.80,
        build_score=6,
        score_max=10,
        effort="working_hard",
    )
    parts = line.split("\n")
    assert len(parts) == 2, f"expected 2-line output, got: {line!r}"
    assert parts[0] == "0.6 × 0.70 + 0.4 × 0.80 → score 8/10"
    assert "**Working Hard**" in parts[1]
    assert "brings" in parts[1]
    assert "6/10" in parts[1]


def test_render_math_line_all_in_effort() -> None:
    """effort='all_in' → 'lifts' effort line. cip=0.70, wage=0.80 →
    unshifted=8/10. Build score is 10 after an all-in lift. Verifies
    the friendly label 'All-In' is used (B2 fix — effort.capitalize()
    would have rendered 'All_in')."""
    line = _render_math_line(
        cip_rank=0.70,
        wage_pct=0.80,
        build_score=10,
        score_max=10,
        effort="all_in",
    )
    parts = line.split("\n")
    assert len(parts) == 2, f"expected 2-line output, got: {line!r}"
    assert parts[0] == "0.6 × 0.70 + 0.4 × 0.80 → score 8/10"
    assert "**All-In**" in parts[1]
    assert "lifts" in parts[1]
    assert "10/10" in parts[1]


def test_render_math_line_unknown_effort_no_line() -> None:
    """Unknown effort string → defensive: no effort line, just the
    base math (B2 fix — protects against EffortLevel literal drift)."""
    line = _render_math_line(
        cip_rank=0.70,
        wage_pct=0.80,
        build_score=6,
        score_max=10,
        effort="some_future_value",
    )
    # No newline → no effort line.
    assert "\n" not in line
    assert line == "0.6 × 0.70 + 0.4 × 0.80 → score 8/10"


def test_render_math_line_halfway_case_with_effort() -> None:
    """One percentile None + non-balanced effort → math line shows
    build_score with n/a in the missing slot, AND emits an effort
    line that doesn't claim a from-N-to-M delta (S2 fix). Without
    this, the halfway case silently suppressed the effort signal —
    a Decision-13 trust regression."""
    line = _render_math_line(
        cip_rank=None,
        wage_pct=0.80,
        build_score=7,
        score_max=10,
        effort="focused",
    )
    parts = line.split("\n")
    assert len(parts) == 2, f"expected 2-line output, got: {line!r}"
    assert parts[0] == "0.6 × n/a + 0.4 × 0.80 → score 7/10"
    assert "**Focused**" in parts[1]
    assert "is reflected in this score" in parts[1]
    # The effort line must NOT claim a from-N-to-M delta.
    assert "lifts" not in parts[1]
    assert "brings" not in parts[1]


def test_render_math_line_halfway_case_balanced_no_effort_line() -> None:
    """One percentile None + balanced effort → no effort line.
    Sanity check that the S2 fix doesn't accidentally emit an effort
    sentence when effort is balanced."""
    line = _render_math_line(
        cip_rank=None,
        wage_pct=0.80,
        build_score=2,
        score_max=10,
        effort="balanced",
    )
    assert "\n" not in line
    assert line == "0.6 × n/a + 0.4 × 0.80 → score 2/10"


def test_math_line_format_unicode_arrow() -> None:
    """math_line uses → (U+2192) for product-copy consistency (P1)."""
    line = _render_math_line(
        cip_rank=0.87,
        wage_pct=0.92,
        build_score=9,
        score_max=10,
        effort="balanced",
    )
    assert "→" in line
    assert "->" not in line
    # Sanity-check the codepoint, not just the glyph appearance.
    assert "→" in line


# ---------------------------------------------------------------------------
# _normalize_label — independent unit-test for the helper itself
# ---------------------------------------------------------------------------


def test_normalize_label_canonical_match_no_change() -> None:
    """Already-canonical label → returned unchanged, was_normalized=False."""
    canonical, was = _normalize_label(
        60, "your school's program rank", _ERN_LABEL_ALLOWLIST
    )
    assert canonical == "your school's program rank"
    assert was is False


def test_normalize_label_off_script_replaced() -> None:
    """Off-script label at a known weight → replaced, was_normalized=True."""
    canonical, was = _normalize_label(
        60, "program rank", _ERN_LABEL_ALLOWLIST
    )
    assert canonical == "your school's program rank"
    assert was is True


def test_normalize_label_unknown_weight_passthrough() -> None:
    """Weight not in the allowlist → Gemma's label kept verbatim."""
    canonical, was = _normalize_label(
        25, "something custom", _ERN_LABEL_ALLOWLIST
    )
    assert canonical == "something custom"
    assert was is False
