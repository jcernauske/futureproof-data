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
    _RES_LABEL_ALLOWLIST,
    _STAT_EXPLAIN_REGISTRY,
    _extract_tool_results,
    _normalize_label,
    _normalize_label_by_position,
    _postprocess_ern_explain_receipt,
    _postprocess_grw_explain_receipt,
    _postprocess_res_explain_receipt,
    _postprocess_roi_explain_receipt,
    _render_math_line,
    _render_math_line_grw,
    _render_math_line_res,
    _render_math_line_roi,
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
    # Mirror the on-the-wire MCP envelope: both tools wrap their payload
    # under "data". get_career_paths returns a list, get_occupation_data
    # returns a single row dict.
    career_payload: dict[str, Any] = {
        "data": [
            {
                "soc_code": soc,
                "cip_family_earnings_rank": cip_rank,
                "earnings_1yr_median": earnings,
            }
        ],
        "row_count": 1,
    }
    occupation_payload: dict[str, Any] = {
        "data": {
            "wage_percentile_overall": wage_pct,
            "median_annual_wage": wage,
        },
        "row_count": 1,
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
    log = _make_tool_log(cip_rank=None, earnings=None, wage_pct=None, wage=None)
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
def test_postprocess_rejects_sentinel_passthrough(sentinel: str, field: str) -> None:
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
        r for r in caplog.records if "ern_explain_receipt parse failed" in r.message
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
        r for r in caplog.records if "ern_explain_receipt parse failed" in r.message
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
    canonical, was = _normalize_label(60, "program rank", _ERN_LABEL_ALLOWLIST)
    assert canonical == "your school's program rank"
    assert was is True


def test_normalize_label_unknown_weight_passthrough() -> None:
    """Weight not in the allowlist → Gemma's label kept verbatim."""
    canonical, was = _normalize_label(25, "something custom", _ERN_LABEL_ALLOWLIST)
    assert canonical == "something custom"
    assert was is False


# ---------------------------------------------------------------------------
# _extract_tool_results — CIP-level field extraction must not require
# soc_code match.
# Spec: docs/specs/bugfix-explain-stat-trigger-null-score-guard.md
# ---------------------------------------------------------------------------


def _career_paths_log(rows: list[dict[str, Any]]) -> gemma_client.ToolCallTurn:
    payload = {"data": rows, "row_count": len(rows)}
    body = json.dumps(payload)
    return gemma_client.ToolCallTurn(
        turn_number=0,
        tool_name="get_career_paths",
        tool_args={"unitid": _IU_UNITID, "cipcode": _IU_CIPCODE},
        tool_result_size_bytes=len(body),
        duration_ms=10,
        error=None,
        tool_result_preview=body[:500],
        tool_result_full=body,
        dispatch_index=0,
    )


def _occupation_log(
    *, wage_pct: float | None = 0.92, wage: int | None = 132_270
) -> gemma_client.ToolCallTurn:
    payload = {
        "data": {
            "wage_percentile_overall": wage_pct,
            "median_annual_wage": wage,
        },
        "row_count": 1,
    }
    body = json.dumps(payload)
    return gemma_client.ToolCallTurn(
        turn_number=0,
        tool_name="get_occupation_data",
        tool_args={"soc_code": _IU_SOC},
        tool_result_size_bytes=len(body),
        duration_ms=10,
        error=None,
        tool_result_preview=body[:500],
        tool_result_full=body,
        dispatch_index=1,
    )


def test_extract_tool_results_reads_cip_fields_when_soc_code_in_first_row() -> None:
    """Standard happy path — cip_family_earnings_rank lives on the row
    whose soc_code matches the build's career."""
    log = [
        _career_paths_log(
            [
                {
                    "soc_code": _IU_SOC,
                    "cip_family_earnings_rank": 0.87,
                    "earnings_1yr_median": 94_200,
                }
            ]
        ),
        _occupation_log(),
    ]
    cip_rank, earnings, wage_pct, wage = _extract_tool_results(log)
    assert cip_rank == 0.87
    assert earnings == 94_200
    assert wage_pct == 0.92
    assert wage == 132_270


def test_extract_tool_results_reads_cip_fields_from_any_row() -> None:
    """REGRESSION: cip_family_earnings_rank and earnings_1yr_median are
    (school, CIP)-level — same across every soc_code fanout row. The
    extractor must read them from any row, even when the row whose
    soc_code matches the build's career happens to have null values
    or doesn't appear in the response (CIP substitution / SOC drift)."""
    log = [
        _career_paths_log(
            [
                # Different SOC (e.g. another career in the same program's
                # fanout) — has the values we want.
                {
                    "soc_code": "11-2021",
                    "cip_family_earnings_rank": 0.87,
                    "earnings_1yr_median": 94_200,
                },
                # The build's SOC is here but missing the CIP-level fields.
                {
                    "soc_code": _IU_SOC,
                    "cip_family_earnings_rank": None,
                    "earnings_1yr_median": None,
                },
            ]
        ),
        _occupation_log(),
    ]
    cip_rank, earnings, _wage_pct, _wage = _extract_tool_results(log)
    assert cip_rank == 0.87
    assert earnings == 94_200


def test_extract_tool_results_when_build_soc_absent_from_response() -> None:
    """REGRESSION (the user-visible bug): get_career_paths returns rows
    for the program but the build's career.soc_code is NOT among them.
    Old extractor returned (None, None, ...) and Gemma's prose then
    claimed values the server couldn't surface (◦ — vs prose mismatch).
    The fix: read CIP-level fields from any row in the response."""
    log = [
        _career_paths_log(
            [
                {
                    "soc_code": "13-1199",  # different SOC, same program
                    "cip_family_earnings_rank": 0.90,
                    "earnings_1yr_median": 63_371,
                },
                {
                    "soc_code": "11-2021",
                    "cip_family_earnings_rank": 0.90,
                    "earnings_1yr_median": 63_371,
                },
            ]
        ),
        _occupation_log(wage_pct=0.72, wage=76_950),
    ]
    cip_rank, earnings, wage_pct, wage = _extract_tool_results(log)
    assert cip_rank == 0.90
    assert earnings == 63_371
    assert wage_pct == 0.72
    assert wage == 76_950


def test_extract_tool_results_genuine_null_when_no_rows_have_value() -> None:
    """When every row has null cip_family_earnings_rank, the extractor
    correctly returns None — driving the score-null receipt path."""
    log = [
        _career_paths_log(
            [
                {
                    "soc_code": _IU_SOC,
                    "cip_family_earnings_rank": None,
                    "earnings_1yr_median": None,
                }
            ]
        ),
        _occupation_log(wage_pct=None, wage=None),
    ]
    cip_rank, earnings, wage_pct, wage = _extract_tool_results(log)
    assert cip_rank is None
    assert earnings is None
    assert wage_pct is None
    assert wage is None


# ===========================================================================
# ROI / RES / GRW explain-receipt tests
#
# Spec: docs/specs/feature-explain-stat-receipt-roi-res-grw.md
# These tests bind the postprocessor contract for the three new stats
# added in the ROI/RES/GRW explain-receipt extension. They follow the
# same pattern as the ERN suite above: direct-constructor builds, no
# DuckDB, no Gemma client — only the real postprocessor logic.
# ===========================================================================


# ---------------------------------------------------------------------------
# Fixture helpers for ROI / RES / GRW
# ---------------------------------------------------------------------------


def _make_roi_build(
    *,
    roi: int | None = 4,
    published_cost_4yr: float | None = 112_400.0,
    earnings_1yr_median: float | None = 78_400.0,
) -> Build:
    """Build fixture for ROI tests."""
    return Build(
        build_id="iu-cs-roi-001",
        created_at="2026-05-02T00:00:00Z",
        school_name="Indiana University-Bloomington",
        unitid=_IU_UNITID,
        major_text="Computer Science",
        cipcode=_IU_CIPCODE,
        program_name="Computer Science",
        effort="balanced",
        loan_pct=1.0,
        career=CareerOutcome(
            unitid=_IU_UNITID,
            institution_name="Indiana University-Bloomington",
            cipcode=_IU_CIPCODE,
            program_name="Computer Science",
            soc_code=_IU_SOC,
            occupation_title="Software Developer",
            stats=PentagonStats(ern=7, roi=roi, res=5, grw=8, aura=4),
            bosses=BossScores(ai=10, loans=10, market=10, burnout=10, ceiling=10),
            median_annual_wage=132_270.0,
            earnings_1yr_median=earnings_1yr_median,
            published_cost_4yr=published_cost_4yr,
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


def _make_res_build(
    *,
    res: int | None = 8,
    raw_stat_res: int | None = 8,
    raw_stat_hmn: int | None = 7,
    task_breakdown_automatable: list[str] | None = None,
    task_breakdown_human: list[str] | None = None,
) -> Build:
    """Build fixture for RES tests."""
    return Build(
        build_id="iu-cs-res-001",
        created_at="2026-05-02T00:00:00Z",
        school_name="Indiana University-Bloomington",
        unitid=_IU_UNITID,
        major_text="Computer Science",
        cipcode=_IU_CIPCODE,
        program_name="Computer Science",
        effort="balanced",
        loan_pct=1.0,
        career=CareerOutcome(
            unitid=_IU_UNITID,
            institution_name="Indiana University-Bloomington",
            cipcode=_IU_CIPCODE,
            program_name="Computer Science",
            soc_code=_IU_SOC,
            occupation_title="Software Developer",
            stats=PentagonStats(ern=7, roi=6, res=res, grw=8, aura=4),
            bosses=BossScores(ai=10, loans=10, market=10, burnout=10, ceiling=10),
            median_annual_wage=132_270.0,
            earnings_1yr_median=94_200.0,
            raw_stat_res=raw_stat_res,
            raw_stat_hmn=raw_stat_hmn,
            task_breakdown_automatable=(
                task_breakdown_automatable
                if task_breakdown_automatable is not None
                else [
                    "Generate code from a clear specification",
                    "Find patterns in logs and test failures",
                ]
            ),
            task_breakdown_human=(
                task_breakdown_human
                if task_breakdown_human is not None
                else [
                    "Choose the right product tradeoff",
                    "Coordinate with teammates and users",
                ]
            ),
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


def _make_grw_build(
    *,
    grw: int | None = 8,
) -> Build:
    """Build fixture for GRW tests."""
    return Build(
        build_id="iu-cs-grw-001",
        created_at="2026-05-02T00:00:00Z",
        school_name="Indiana University-Bloomington",
        unitid=_IU_UNITID,
        major_text="Computer Science",
        cipcode=_IU_CIPCODE,
        program_name="Computer Science",
        effort="balanced",
        loan_pct=1.0,
        career=CareerOutcome(
            unitid=_IU_UNITID,
            institution_name="Indiana University-Bloomington",
            cipcode=_IU_CIPCODE,
            program_name="Computer Science",
            soc_code=_IU_SOC,
            occupation_title="Software Developer",
            stats=PentagonStats(ern=7, roi=6, res=5, grw=grw, aura=4),
            bosses=BossScores(ai=10, loans=10, market=10, burnout=10, ceiling=10),
            median_annual_wage=132_270.0,
            earnings_1yr_median=94_200.0,
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


def _make_grw_tool_log(
    *,
    employment_change_pct: float | None = 15.2,
    growth_category: str | None = "Much faster than average",
) -> list[gemma_client.ToolCallTurn]:
    """Tool-call log for GRW (get_occupation_data with employment_change_pct)."""
    payload: dict[str, Any] = {
        "data": {
            "employment_change_pct": employment_change_pct,
            "growth_category": growth_category,
            "median_annual_wage": 132_270,
        },
        "row_count": 1,
    }
    body = json.dumps(payload)
    return [
        gemma_client.ToolCallTurn(
            turn_number=0,
            tool_name="get_occupation_data",
            tool_args={"soc_code": _IU_SOC},
            tool_result_size_bytes=len(body),
            duration_ms=15,
            error=None,
            tool_result_preview=body[:500],
            tool_result_full=body,
            dispatch_index=0,
        ),
    ]


def _make_res_tool_log(
    *,
    stat_res: int | None = 8,
    stat_hmn: int | None = 7,
) -> list[gemma_client.ToolCallTurn]:
    """Tool-call log for RES (get_career_paths with stat_res/stat_hmn)."""
    payload: dict[str, Any] = {
        "data": [
            {
                "soc_code": _IU_SOC,
                "stat_res": stat_res,
                "stat_hmn": stat_hmn,
                "earnings_1yr_median": 94_200,
            }
        ],
        "row_count": 1,
    }
    body = json.dumps(payload)
    return [
        gemma_client.ToolCallTurn(
            turn_number=0,
            tool_name="get_career_paths",
            tool_args={"unitid": _IU_UNITID, "cipcode": _IU_CIPCODE},
            tool_result_size_bytes=len(body),
            duration_ms=12,
            error=None,
            tool_result_preview=body[:500],
            tool_result_full=body,
            dispatch_index=0,
        ),
    ]


def _roi_receipt_json(
    *,
    stat_code: str = "ROI",
    score: int = 4,
    override: dict[str, Any] | None = None,
    component_overrides: list[dict[str, Any]] | None = None,
) -> str:
    """Build a Gemma-shaped JSON string for the ROI receipt."""
    payload: dict[str, Any] = {
        "kind": "receipt",
        "stat_code": stat_code,
        "stat_name": "Return on Investment",
        "score": score,
        "score_max": 10,
        "one_liner": (
            "Return on Investment divides your school's full published cost "
            "by what you're likely to earn in your first year after graduation."
        ),
        "components": [
            {
                "weight_pct": 100,
                "label": "your debt-to-earnings ratio",
                "explainer": (
                    "IU Bloomington's Computer Science 4-year published cost "
                    "is $112,400. Graduates earn a median of $78,400 one year "
                    "out. That puts the ratio at 1.43."
                ),
                "value_pct": None,
                "anchor_text": (
                    "Indiana University Computer Science"
                    " 4-year published cost"
                ),
                "anchor_dollars": 112_400,
                "missing_reason": None,
            },
        ],
        "math_line": "$112,400 / $78,400 = 1.43 → ROI score 4/10",
        "sources": [
            {
                "label": "Published cost",
                "name": "College Scorecard (U.S. Department of Education)",
            },
            {
                "label": "Graduate earnings",
                "name": "College Scorecard (U.S. Department of Education)",
            },
        ],
        "why_mix_paragraph": (
            "Picture two students. One pays $40,000 total but earns $35,000 "
            "— their cost is barely more than a year's salary. Another pays "
            "$200,000 and earns $50,000 — four years of salary spent before "
            "they start. The ratio turns both into one number you can compare "
            "across any school and career."
        ),
    }
    if override:
        payload.update(override)
    if component_overrides:
        for idx, patch in enumerate(component_overrides):
            payload["components"][idx].update(patch)
    return json.dumps(payload)


def _res_receipt_json(
    *,
    stat_code: str = "RES",
    score: int = 8,
    override: dict[str, Any] | None = None,
    component_overrides: list[dict[str, Any]] | None = None,
) -> str:
    """Build a Gemma-shaped JSON string for the RES receipt."""
    payload: dict[str, Any] = {
        "kind": "receipt",
        "stat_code": stat_code,
        "stat_name": "AI Resilience",
        "score": score,
        "score_max": 10,
        "one_liner": (
            "AI Resilience blends how automatable a career's tasks are with "
            "how much the work depends on human judgment and social awareness."
        ),
        "components": [
            {
                "weight_pct": 50,
                "label": "AI exposure",
                "explainer": (
                    "Software Developer tasks score 8 out of 10 on the AI-exposure "
                    "composite from Karpathy, Anthropic, and Gemma."
                ),
                "value_pct": 80,
                "anchor_text": "AI-exposure rating: 8/10",
                "anchor_dollars": None,
                "missing_reason": None,
            },
            {
                "weight_pct": 50,
                "label": "human-essential skills",
                "explainer": (
                    "Software Developer work depends heavily on judgment and "
                    "social awareness — O*NET rates it 7 out of 10."
                ),
                "value_pct": 70,
                "anchor_text": "Human-essential rating: 7/10",
                "anchor_dollars": None,
                "missing_reason": None,
            },
        ],
        "math_line": "0.5 × 8 + 0.5 × 7 → score 8/10",
        "sources": [
            {
                "label": "AI exposure composite",
                "name": "Karpathy AI Exposure Index + Anthropic Economic Index",
            },
            {
                "label": "Human-essential skills",
                "name": (
                    "O*NET (Occupational Information Network,"
                    " U.S. Department of Labor)"
                ),
            },
        ],
        "why_mix_paragraph": (
            "Two signals are mixed 50/50: AI exposure scores how automatable "
            "the work is, and human-essential rates how much it depends on "
            "judgment, social awareness, or physical presence. The blend "
            "hedges against either signal being too pessimistic or too "
            "generous on its own."
        ),
    }
    if override:
        payload.update(override)
    if component_overrides:
        for idx, patch in enumerate(component_overrides):
            payload["components"][idx].update(patch)
    return json.dumps(payload)


def _grw_receipt_json(
    *,
    stat_code: str = "GRW",
    score: int = 8,
    override: dict[str, Any] | None = None,
    component_overrides: list[dict[str, Any]] | None = None,
) -> str:
    """Build a Gemma-shaped JSON string for the GRW receipt."""
    payload: dict[str, Any] = {
        "kind": "receipt",
        "stat_code": stat_code,
        "stat_name": "Growth Outlook",
        "score": score,
        "score_max": 10,
        "one_liner": (
            "Growth Outlook reads the federal 10-year projection of how many "
            "more or fewer people will work in this career a decade from now."
        ),
        "components": [
            {
                "weight_pct": 100,
                "label": "this career's projected employment change",
                "explainer": (
                    "Software Developer employment is projected to grow 15.2% "
                    "over the next decade — the BLS calls this 'Much faster "
                    "than average'."
                ),
                "value_pct": None,
                "anchor_text": "+15.2% projected change over 10 years",
                "anchor_dollars": None,
                "missing_reason": None,
            },
        ],
        "math_line": "+15.2% employment change → GRW score 8/10",
        "sources": [
            {
                "label": "Employment projections",
                "name": (
                    "Occupational Outlook Handbook, published by the Bureau "
                    "of Labor Statistics (BLS)"
                ),
            },
        ],
        "why_mix_paragraph": (
            "This score reads BLS's 10-year employment-change projection. "
            "We use a projection because for a college decision you care "
            "about the world you'll enter, not the world you'd have entered "
            "in 2018."
        ),
    }
    if override:
        payload.update(override)
    if component_overrides:
        for idx, patch in enumerate(component_overrides):
            payload["components"][idx].update(patch)
    return json.dumps(payload)


# ===========================================================================
# ROI postprocessor tests
# ===========================================================================


class TestROIPostprocess:
    """Tests for _postprocess_roi_explain_receipt."""

    def test_roi_postprocess_happy_path(self) -> None:
        """Valid Gemma JSON → parsed ExplainStatReceipt with stat_code=ROI,
        single 100% component, math_line shape '$X / $Y = Z.ZZ → ROI score N/10'."""
        build = _make_roi_build()
        log = _make_tool_log()  # ROI doesn't use tool log for extraction
        receipt = _postprocess_roi_explain_receipt(
            raw=_roi_receipt_json(),
            build=build,
            tool_call_log=log,
            backend="ollama",
        )

        assert receipt is not None
        assert isinstance(receipt, ExplainStatReceipt)
        assert receipt.stat_code == "ROI"
        assert receipt.kind == "receipt"
        assert receipt.score == 4  # build.career.stats.roi
        assert receipt.score_max == 10
        assert len(receipt.components) == 1

        comp = receipt.components[0]
        assert comp.weight_pct == 100
        assert comp.label == "your debt-to-earnings ratio"
        # anchor_dollars = published_cost_4yr
        assert comp.anchor_dollars == 112_400
        # value_pct is always None for ROI (ratio, not percentile)
        assert comp.value_pct is None
        assert comp.missing_reason is None

        # Math line format: '$112,400 / $78,400 = 1.43 → ROI score 4/10'
        assert "$112,400" in receipt.math_line
        assert "$78,400" in receipt.math_line
        assert "1.43" in receipt.math_line
        assert "ROI score 4/10" in receipt.math_line
        assert "→" in receipt.math_line

        # Sources are server-stamped
        assert len(receipt.sources) == 2

    def test_roi_postprocess_score_from_build(self) -> None:
        """Gemma emits score 2 → overwritten with build.career.stats.roi (4)."""
        build = _make_roi_build(roi=4)
        log = _make_tool_log()
        raw = _roi_receipt_json(score=2)  # Wrong score from Gemma

        receipt = _postprocess_roi_explain_receipt(
            raw=raw, build=build, tool_call_log=log, backend="ollama"
        )
        assert receipt is not None
        assert receipt.score == 4  # build's ROI score, not Gemma's 2

    def test_roi_postprocess_anchor_uses_build_published_cost_4yr(self) -> None:
        """anchor_dollars stamped from build.career.published_cost_4yr,
        not from whatever Gemma put in the JSON."""
        build = _make_roi_build(published_cost_4yr=95_000.0)
        log = _make_tool_log()
        # Gemma writes anchor_dollars=112400, but server should stamp 95000
        raw = _roi_receipt_json(component_overrides=[{"anchor_dollars": 999_999}])

        receipt = _postprocess_roi_explain_receipt(
            raw=raw, build=build, tool_call_log=log, backend="ollama"
        )
        assert receipt is not None
        assert receipt.components[0].anchor_dollars == 95_000

    def test_roi_postprocess_published_cost_null(self) -> None:
        """build.career.published_cost_4yr is None → missing_reason set,
        math_line shows n/a."""
        build = _make_roi_build(published_cost_4yr=None)
        log = _make_tool_log()

        receipt = _postprocess_roi_explain_receipt(
            raw=_roi_receipt_json(),
            build=build,
            tool_call_log=log,
            backend="ollama",
        )
        assert receipt is not None
        comp = receipt.components[0]
        assert comp.anchor_dollars is None
        assert comp.missing_reason is not None
        assert "published cost" in comp.missing_reason.lower()
        assert "n/a" in receipt.math_line

    def test_roi_postprocess_earnings_null(self) -> None:
        """earnings_1yr_median is None → missing_reason set, math_line n/a."""
        build = _make_roi_build(earnings_1yr_median=None)
        log = _make_tool_log()

        receipt = _postprocess_roi_explain_receipt(
            raw=_roi_receipt_json(),
            build=build,
            tool_call_log=log,
            backend="ollama",
        )
        assert receipt is not None
        comp = receipt.components[0]
        # anchor_dollars is published_cost_4yr (still present)
        assert comp.anchor_dollars == 112_400
        assert comp.missing_reason is not None
        assert "earnings" in comp.missing_reason.lower()
        assert "n/a" in receipt.math_line

    def test_roi_postprocess_both_null(self) -> None:
        """Both published_cost_4yr and earnings None → n/a / n/a."""
        build = _make_roi_build(published_cost_4yr=None, earnings_1yr_median=None)
        log = _make_tool_log()

        receipt = _postprocess_roi_explain_receipt(
            raw=_roi_receipt_json(),
            build=build,
            tool_call_log=log,
            backend="ollama",
        )
        assert receipt is not None
        assert "n/a / n/a = n/a" in receipt.math_line

    def test_roi_postprocess_label_normalization(self) -> None:
        """Off-script label at weight=100 → replaced with canonical."""
        build = _make_roi_build()
        log = _make_tool_log()
        raw = _roi_receipt_json(component_overrides=[{"label": "debt ratio"}])

        receipt = _postprocess_roi_explain_receipt(
            raw=raw, build=build, tool_call_log=log, backend="ollama"
        )
        assert receipt is not None
        assert receipt.components[0].label == "your debt-to-earnings ratio"

    def test_roi_postprocess_rejects_wrong_stat_code(self) -> None:
        """stat_code='ERN' in ROI dispatch → None."""
        build = _make_roi_build()
        log = _make_tool_log()
        raw = _roi_receipt_json(stat_code="ERN")

        receipt = _postprocess_roi_explain_receipt(
            raw=raw, build=build, tool_call_log=log, backend="ollama"
        )
        assert receipt is None

    def test_roi_postprocess_rejects_sentinel_passthrough(self) -> None:
        """one_liner containing '__FILL_IN__' → Pydantic rejects → None."""
        build = _make_roi_build()
        log = _make_tool_log()
        raw = _roi_receipt_json(override={"one_liner": "__FILL_IN__"})

        receipt = _postprocess_roi_explain_receipt(
            raw=raw, build=build, tool_call_log=log, backend="ollama"
        )
        assert receipt is None

    def test_roi_postprocess_invalid_json_returns_none(self) -> None:
        """Unparseable string → None."""
        build = _make_roi_build()
        log = _make_tool_log()

        receipt = _postprocess_roi_explain_receipt(
            raw="this is completely broken JSON {{{",
            build=build,
            tool_call_log=log,
            backend="ollama",
        )
        assert receipt is None

    def test_roi_postprocess_build_score_null_returns_none(self) -> None:
        """build.career.stats.roi is None → returns None."""
        build = _make_roi_build(roi=None)
        log = _make_tool_log()

        receipt = _postprocess_roi_explain_receipt(
            raw=_roi_receipt_json(),
            build=build,
            tool_call_log=log,
            backend="ollama",
        )
        assert receipt is None


# ===========================================================================
# RES postprocessor tests
# ===========================================================================


class TestRESPostprocess:
    """Tests for _postprocess_res_explain_receipt."""

    def test_res_postprocess_happy_path(self) -> None:
        """Valid JSON → 2-component receipt, value_pct=stat_res*10 and
        stat_hmn*10, labels normalized."""
        build = _make_res_build(res=8, raw_stat_res=8, raw_stat_hmn=7)
        log = _make_res_tool_log()

        receipt = _postprocess_res_explain_receipt(
            raw=_res_receipt_json(),
            build=build,
            tool_call_log=log,
            backend="ollama",
        )

        assert receipt is not None
        assert isinstance(receipt, ExplainStatReceipt)
        assert receipt.stat_code == "RES"
        assert receipt.score == 8
        assert receipt.score_max == 10
        assert len(receipt.components) == 2

        # Position 0 = AI exposure
        assert receipt.components[0].label == "AI exposure"
        assert receipt.components[0].value_pct == 80  # 8 * 10
        assert receipt.components[0].anchor_dollars is None
        assert receipt.components[0].missing_reason is None

        # Position 1 = human-essential
        assert receipt.components[1].label == "human-essential skills"
        assert receipt.components[1].value_pct == 70  # 7 * 10
        assert receipt.components[1].anchor_dollars is None
        assert receipt.components[1].missing_reason is None

        # Math line
        assert "0.5 × 8 + 0.5 × 7" in receipt.math_line
        assert "score 8/10" in receipt.math_line

        # Sources
        assert len(receipt.sources) == 2

    def test_res_postprocess_label_normalization_position_based(self) -> None:
        """Off-script label at position 0 → replaced with canonical
        'AI exposure', position 1 → 'human-essential skills'."""
        build = _make_res_build()
        log = _make_res_tool_log()
        raw = _res_receipt_json(
            component_overrides=[
                {"label": "ai vulnerability"},  # off-script at pos 0
                {"label": "human skills"},  # off-script at pos 1
            ]
        )

        receipt = _postprocess_res_explain_receipt(
            raw=raw, build=build, tool_call_log=log, backend="ollama"
        )
        assert receipt is not None
        assert receipt.components[0].label == "AI exposure"
        assert receipt.components[1].label == "human-essential skills"

    def test_res_postprocess_value_pct_conversion(self) -> None:
        """stat_res=6 → value_pct=60, stat_hmn=9 → value_pct=90."""
        build = _make_res_build(res=8, raw_stat_res=6, raw_stat_hmn=9)
        log = _make_res_tool_log(stat_res=6, stat_hmn=9)

        receipt = _postprocess_res_explain_receipt(
            raw=_res_receipt_json(),
            build=build,
            tool_call_log=log,
            backend="ollama",
        )
        assert receipt is not None
        assert receipt.components[0].value_pct == 60  # 6 * 10
        assert receipt.components[1].value_pct == 90  # 9 * 10

    def test_res_postprocess_partial_null_stat_res(self) -> None:
        """stat_res None → value_pct None + missing_reason on comp[0]."""
        build = _make_res_build(raw_stat_res=None, raw_stat_hmn=7)
        log = _make_res_tool_log(stat_res=None, stat_hmn=7)

        receipt = _postprocess_res_explain_receipt(
            raw=_res_receipt_json(),
            build=build,
            tool_call_log=log,
            backend="ollama",
        )
        assert receipt is not None
        assert receipt.components[0].value_pct is None
        assert receipt.components[0].missing_reason is not None
        assert "ai" in receipt.components[0].missing_reason.lower()
        # Position 1 still populated
        assert receipt.components[1].value_pct == 70  # 7 * 10
        assert receipt.components[1].missing_reason is None

    def test_res_postprocess_partial_null_stat_hmn(self) -> None:
        """stat_hmn None → value_pct None + missing_reason on comp[1]."""
        build = _make_res_build(raw_stat_res=8, raw_stat_hmn=None)
        log = _make_res_tool_log(stat_res=8, stat_hmn=None)

        receipt = _postprocess_res_explain_receipt(
            raw=_res_receipt_json(),
            build=build,
            tool_call_log=log,
            backend="ollama",
        )
        assert receipt is not None
        assert receipt.components[0].value_pct == 80  # 8 * 10
        assert receipt.components[0].missing_reason is None
        assert receipt.components[1].value_pct is None
        assert receipt.components[1].missing_reason is not None
        assert "human" in receipt.components[1].missing_reason.lower()

    def test_res_postprocess_both_null(self) -> None:
        """Both stat_res and stat_hmn None → both missing."""
        build = _make_res_build(raw_stat_res=None, raw_stat_hmn=None)
        log = _make_res_tool_log(stat_res=None, stat_hmn=None)

        receipt = _postprocess_res_explain_receipt(
            raw=_res_receipt_json(),
            build=build,
            tool_call_log=log,
            backend="ollama",
        )
        assert receipt is not None
        assert receipt.components[0].value_pct is None
        assert receipt.components[1].value_pct is None
        assert "n/a" in receipt.math_line

    def test_res_postprocess_score_from_build(self) -> None:
        """Gemma emits score=2 → overwritten with build.career.stats.res."""
        build = _make_res_build(res=8)
        log = _make_res_tool_log()
        raw = _res_receipt_json(score=2)

        receipt = _postprocess_res_explain_receipt(
            raw=raw, build=build, tool_call_log=log, backend="ollama"
        )
        assert receipt is not None
        assert receipt.score == 8

    def test_res_postprocess_wrong_stat_code_builds_server_receipt(self) -> None:
        """stat_code='ERN' in RES dispatch → server-built RES receipt."""
        build = _make_res_build()
        log = _make_res_tool_log()
        raw = _res_receipt_json(stat_code="ERN")

        receipt = _postprocess_res_explain_receipt(
            raw=raw, build=build, tool_call_log=log, backend="ollama"
        )
        assert receipt is not None
        assert receipt.stat_code == "RES"
        assert receipt.score == 8
        assert receipt.components[0].evidence_bullets is not None

    def test_res_postprocess_sentinel_passthrough_builds_server_receipt(self) -> None:
        """Sentinel in one_liner → server-built RES receipt."""
        build = _make_res_build()
        log = _make_res_tool_log()
        raw = _res_receipt_json(override={"one_liner": "[FILL_IN]"})

        receipt = _postprocess_res_explain_receipt(
            raw=raw, build=build, tool_call_log=log, backend="ollama"
        )
        assert receipt is not None
        assert receipt.stat_code == "RES"
        assert receipt.one_liner != "[FILL_IN]"

    def test_res_postprocess_build_score_null_returns_none(self) -> None:
        """build.career.stats.res is None → returns None."""
        build = _make_res_build(res=None)
        log = _make_res_tool_log()

        receipt = _postprocess_res_explain_receipt(
            raw=_res_receipt_json(),
            build=build,
            tool_call_log=log,
            backend="ollama",
        )
        assert receipt is None

    def test_res_postprocess_wrong_component_count_builds_server_receipt(self) -> None:
        """RES expects 2 components; malformed count → server-built receipt."""
        build = _make_res_build()
        log = _make_res_tool_log()
        # Build a receipt with only 1 component
        payload = json.loads(_res_receipt_json())
        payload["components"] = [payload["components"][0]]
        raw = json.dumps(payload)

        receipt = _postprocess_res_explain_receipt(
            raw=raw, build=build, tool_call_log=log, backend="ollama"
        )
        assert receipt is not None
        assert len(receipt.components) == 2
        assert receipt.components[0].label == "AI exposure"
        assert receipt.components[1].label == "human-essential skills"

    def test_res_postprocess_fallback_to_tool_log(self) -> None:
        """When build has raw_stat_res=None, falls back to tool_call_log."""
        build = _make_res_build(raw_stat_res=None, raw_stat_hmn=None)
        # Tool log provides the values
        log = _make_res_tool_log(stat_res=6, stat_hmn=9)

        receipt = _postprocess_res_explain_receipt(
            raw=_res_receipt_json(),
            build=build,
            tool_call_log=log,
            backend="ollama",
        )
        assert receipt is not None
        # Fell back to tool log values
        assert receipt.components[0].value_pct == 60  # 6 * 10
        assert receipt.components[1].value_pct == 90  # 9 * 10
        assert "0.5 × 6 + 0.5 × 9" in receipt.math_line

    def test_res_postprocess_json_decode_builds_server_receipt(self) -> None:
        """Non-JSON Gemma output → structured server-built RES receipt."""
        build = _make_res_build(res=4, raw_stat_res=4, raw_stat_hmn=3)

        receipt = _postprocess_res_explain_receipt(
            raw="AI Resilience — markdown fallback should not render",
            build=build,
            tool_call_log=_make_res_tool_log(stat_res=4, stat_hmn=3),
            backend="ollama",
        )

        assert receipt is not None
        assert receipt.kind == "receipt"
        assert receipt.stat_code == "RES"
        assert receipt.score == 4
        assert receipt.components[0].value_pct == 40
        assert receipt.components[1].value_pct == 30
        assert "0.5 × 4 + 0.5 × 3" in receipt.math_line
        assert "score 4/10" in receipt.math_line
        assert receipt.components[0].evidence_bullets is not None

    def test_res_postprocess_tool_score_fallback_matches_build_soc(self) -> None:
        """Multi-row get_career_paths must use the selected career's SOC row."""
        payload = {
            "data": [
                {
                    "soc_code": "11-3012",
                    "stat_res": 7,
                    "stat_hmn": 5,
                },
                {
                    "soc_code": _IU_SOC,
                    "stat_res": 4,
                    "stat_hmn": 3,
                },
            ],
            "row_count": 2,
        }
        body = json.dumps(payload)
        log = [
            gemma_client.ToolCallTurn(
                turn_number=0,
                tool_name="get_career_paths",
                tool_args={"unitid": _IU_UNITID, "cipcode": _IU_CIPCODE},
                tool_result_size_bytes=len(body),
                duration_ms=12,
                error=None,
                tool_result_preview=body[:500],
                tool_result_full=body,
                dispatch_index=0,
            ),
        ]
        build = _make_res_build(res=4, raw_stat_res=None, raw_stat_hmn=None)

        receipt = _postprocess_res_explain_receipt(
            raw=_res_receipt_json(),
            build=build,
            tool_call_log=log,
            backend="ollama",
        )

        assert receipt is not None
        assert receipt.score == 4
        assert receipt.components[0].value_pct == 40
        assert receipt.components[1].value_pct == 30
        assert "0.5 × 4 + 0.5 × 3" in receipt.math_line

    def test_res_postprocess_stamps_task_evidence_from_build(self) -> None:
        """Task evidence from CareerOutcome is stamped into component slots."""
        build = _make_res_build(
            task_breakdown_automatable=[
                "Generate code from a clear specification",
                "Find patterns in logs and test failures",
            ],
            task_breakdown_human=[
                "Choose the right product tradeoff",
                "Coordinate with teammates and users",
            ],
        )

        receipt = _postprocess_res_explain_receipt(
            raw=_res_receipt_json(),
            build=build,
            tool_call_log=_make_res_tool_log(),
            backend="ollama",
        )

        assert receipt is not None
        assert receipt.components[0].evidence_bullets == [
            "Generate code from a clear specification",
            "Find patterns in logs and test failures",
        ]
        assert receipt.components[1].evidence_bullets == [
            "Choose the right product tradeoff",
            "Coordinate with teammates and users",
        ]

    def test_res_postprocess_fetches_task_evidence_when_build_lacks_it(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Missing build evidence falls back to deterministic get_task_breakdown."""

        def fake_call(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
            assert tool_name == "get_task_breakdown"
            assert args == {"soc_code": _IU_SOC}
            return {
                "data": {
                    "top_5_activities": [
                        "Analyze user needs and software requirements",
                        "Modify existing software to correct errors",
                    ],
                    "top_human_activities": [
                        "Collaborate with users about software design",
                        "Make architecture decisions under tradeoffs",
                    ],
                },
                "row_count": 1,
            }

        monkeypatch.setattr(ask_gemma.mcp_client, "call", fake_call)

        receipt = _postprocess_res_explain_receipt(
            raw=_res_receipt_json(),
            build=_make_res_build(
                task_breakdown_automatable=[],
                task_breakdown_human=[],
            ),
            tool_call_log=_make_res_tool_log(),
            backend="ollama",
        )

        assert receipt is not None
        assert receipt.components[0].evidence_bullets == [
            "Analyze user needs and software requirements",
            "Modify existing software to correct errors",
        ]
        assert receipt.components[1].evidence_bullets == [
            "Collaborate with users about software design",
            "Make architecture decisions under tradeoffs",
        ]


# ===========================================================================
# GRW postprocessor tests
# ===========================================================================


class TestGRWPostprocess:
    """Tests for _postprocess_grw_explain_receipt."""

    def test_grw_postprocess_happy_path(self) -> None:
        """Valid JSON → single 100% component, anchor_text shows projection."""
        build = _make_grw_build(grw=8)
        log = _make_grw_tool_log(employment_change_pct=15.2)

        receipt = _postprocess_grw_explain_receipt(
            raw=_grw_receipt_json(),
            build=build,
            tool_call_log=log,
            backend="ollama",
        )

        assert receipt is not None
        assert isinstance(receipt, ExplainStatReceipt)
        assert receipt.stat_code == "GRW"
        assert receipt.score == 8
        assert receipt.score_max == 10
        assert len(receipt.components) == 1

        comp = receipt.components[0]
        assert comp.weight_pct == 100
        assert comp.label == "this career's projected employment change"
        assert comp.value_pct is None
        assert comp.anchor_dollars is None
        assert comp.missing_reason is None
        assert "+15.2%" in comp.anchor_text
        assert "projected change over 10 years" in comp.anchor_text

        # Math line format
        assert "+15.2% employment change" in receipt.math_line
        assert "GRW score 8/10" in receipt.math_line
        assert "→" in receipt.math_line

        # Sources
        assert len(receipt.sources) == 1
        assert "BLS" in receipt.sources[0].name or "Bureau" in receipt.sources[0].name

    def test_grw_postprocess_employment_change_null(self) -> None:
        """employment_change_pct None → missing_reason set, math n/a."""
        build = _make_grw_build(grw=8)
        log = _make_grw_tool_log(employment_change_pct=None)

        receipt = _postprocess_grw_explain_receipt(
            raw=_grw_receipt_json(),
            build=build,
            tool_call_log=log,
            backend="ollama",
        )
        assert receipt is not None
        comp = receipt.components[0]
        assert comp.missing_reason is not None
        assert "projection" in comp.missing_reason.lower()
        assert "n/a employment change" in receipt.math_line

    def test_grw_postprocess_negative_change_format(self) -> None:
        """-3.4% → math line '-3.4% employment change → GRW score 3/10'."""
        build = _make_grw_build(grw=3)
        log = _make_grw_tool_log(employment_change_pct=-3.4)

        receipt = _postprocess_grw_explain_receipt(
            raw=_grw_receipt_json(),
            build=build,
            tool_call_log=log,
            backend="ollama",
        )
        assert receipt is not None
        assert "-3.4% employment change" in receipt.math_line
        assert "GRW score 3/10" in receipt.math_line
        # Anchor text also reflects negative
        comp = receipt.components[0]
        assert "-3.4%" in comp.anchor_text

    def test_grw_postprocess_zero_change_format(self) -> None:
        """0.0% employment change formats without sign prefix."""
        build = _make_grw_build(grw=5)
        log = _make_grw_tool_log(employment_change_pct=0.0)

        receipt = _postprocess_grw_explain_receipt(
            raw=_grw_receipt_json(),
            build=build,
            tool_call_log=log,
            backend="ollama",
        )
        assert receipt is not None
        assert "0.0% employment change" in receipt.math_line
        assert "GRW score 5/10" in receipt.math_line

    def test_grw_postprocess_score_from_build(self) -> None:
        """Gemma emits score=2 → overwritten with build.career.stats.grw."""
        build = _make_grw_build(grw=8)
        log = _make_grw_tool_log()
        raw = _grw_receipt_json(score=2)

        receipt = _postprocess_grw_explain_receipt(
            raw=raw, build=build, tool_call_log=log, backend="ollama"
        )
        assert receipt is not None
        assert receipt.score == 8

    def test_grw_postprocess_label_normalization(self) -> None:
        """Off-script label at weight=100 → replaced with canonical."""
        build = _make_grw_build()
        log = _make_grw_tool_log()
        raw = _grw_receipt_json(
            component_overrides=[{"label": "employment growth projection"}]
        )

        receipt = _postprocess_grw_explain_receipt(
            raw=raw, build=build, tool_call_log=log, backend="ollama"
        )
        assert receipt is not None
        assert (
            receipt.components[0].label == "this career's projected employment change"
        )

    def test_grw_postprocess_rejects_wrong_stat_code(self) -> None:
        """stat_code='ROI' in GRW dispatch → None."""
        build = _make_grw_build()
        log = _make_grw_tool_log()
        raw = _grw_receipt_json(stat_code="ROI")

        receipt = _postprocess_grw_explain_receipt(
            raw=raw, build=build, tool_call_log=log, backend="ollama"
        )
        assert receipt is None

    def test_grw_postprocess_rejects_sentinel_passthrough(self) -> None:
        """Sentinel in why_mix_paragraph → None."""
        build = _make_grw_build()
        log = _make_grw_tool_log()
        raw = _grw_receipt_json(override={"why_mix_paragraph": "<FILL_IN>"})

        receipt = _postprocess_grw_explain_receipt(
            raw=raw, build=build, tool_call_log=log, backend="ollama"
        )
        assert receipt is None

    def test_grw_postprocess_build_score_null_returns_none(self) -> None:
        """build.career.stats.grw is None → returns None."""
        build = _make_grw_build(grw=None)
        log = _make_grw_tool_log()

        receipt = _postprocess_grw_explain_receipt(
            raw=_grw_receipt_json(),
            build=build,
            tool_call_log=log,
            backend="ollama",
        )
        assert receipt is None

    def test_grw_postprocess_invalid_json_returns_none(self) -> None:
        """Unparseable string → None."""
        build = _make_grw_build()
        log = _make_grw_tool_log()

        receipt = _postprocess_grw_explain_receipt(
            raw="not json at all }{{{",
            build=build,
            tool_call_log=log,
            backend="ollama",
        )
        assert receipt is None


# ===========================================================================
# Math-line renderer tests
# ===========================================================================


class TestRenderMathLineROI:
    """Tests for _render_math_line_roi."""

    def test_render_math_line_roi_happy(self) -> None:
        """Normal case: both values present."""
        line = _render_math_line_roi(
            published_cost_4yr=112_400.0,
            earnings_1yr_median=78_400.0,
            build_score=4,
            score_max=10,
        )
        assert line == "$112,400 / $78,400 = 1.43 → ROI score 4/10"

    def test_render_math_line_roi_cost_null(self) -> None:
        """published_cost_4yr None → n/a / $X."""
        line = _render_math_line_roi(
            published_cost_4yr=None,
            earnings_1yr_median=78_400.0,
            build_score=4,
            score_max=10,
        )
        assert line == "n/a / $78,400 = n/a → score 4/10"

    def test_render_math_line_roi_earnings_null(self) -> None:
        """earnings None → $X / n/a."""
        line = _render_math_line_roi(
            published_cost_4yr=112_400.0,
            earnings_1yr_median=None,
            build_score=4,
            score_max=10,
        )
        assert line == "$112,400 / n/a = n/a → score 4/10"

    def test_render_math_line_roi_both_null(self) -> None:
        """Both None → n/a / n/a."""
        line = _render_math_line_roi(
            published_cost_4yr=None,
            earnings_1yr_median=None,
            build_score=4,
            score_max=10,
        )
        assert line == "n/a / n/a = n/a → score 4/10"

    def test_render_math_line_roi_ratio_precision(self) -> None:
        """Ratio uses exactly 2 decimal places."""
        line = _render_math_line_roi(
            published_cost_4yr=100_000.0,
            earnings_1yr_median=33_333.0,
            build_score=2,
            score_max=10,
        )
        # 100000 / 33333 = 3.00003... → "3.00"
        assert "= 3.00" in line
        assert "ROI score 2/10" in line

    def test_render_math_line_roi_large_values(self) -> None:
        """Comma formatting on large dollar amounts."""
        line = _render_math_line_roi(
            published_cost_4yr=250_000.0,
            earnings_1yr_median=45_000.0,
            build_score=1,
            score_max=10,
        )
        assert "$250,000" in line
        assert "$45,000" in line

    def test_render_math_line_roi_earnings_zero(self) -> None:
        """Zero earnings treated as n/a to prevent division by zero."""
        line = _render_math_line_roi(
            published_cost_4yr=112_400.0,
            earnings_1yr_median=0,
            build_score=4,
            score_max=10,
        )
        assert "n/a" in line
        assert "score 4/10" in line


class TestRenderMathLineRES:
    """Tests for _render_math_line_res."""

    def test_render_math_line_res_happy(self) -> None:
        """Normal case: both values present."""
        line = _render_math_line_res(
            stat_res_raw=8,
            stat_hmn_raw=7,
            build_score=8,
            score_max=10,
        )
        assert line == "0.5 × 8 + 0.5 × 7 → score 8/10"

    def test_render_math_line_res_res_null(self) -> None:
        """stat_res None → n/a in first position."""
        line = _render_math_line_res(
            stat_res_raw=None,
            stat_hmn_raw=7,
            build_score=7,
            score_max=10,
        )
        assert line == "0.5 × n/a + 0.5 × 7 → score 7/10"

    def test_render_math_line_res_hmn_null(self) -> None:
        """stat_hmn None → n/a in second position."""
        line = _render_math_line_res(
            stat_res_raw=8,
            stat_hmn_raw=None,
            build_score=8,
            score_max=10,
        )
        assert line == "0.5 × 8 + 0.5 × n/a → score 8/10"

    def test_render_math_line_res_both_null(self) -> None:
        """Both None → n/a everywhere."""
        line = _render_math_line_res(
            stat_res_raw=None,
            stat_hmn_raw=None,
            build_score=5,
            score_max=10,
        )
        assert line == "0.5 × n/a + 0.5 × n/a → score 5/10"

    def test_render_math_line_res_unicode_multiply_arrow(self) -> None:
        """Uses x-multiply (U+00D7) and arrow (U+2192)."""
        line = _render_math_line_res(
            stat_res_raw=8,
            stat_hmn_raw=7,
            build_score=8,
            score_max=10,
        )
        assert "×" in line  # multiplication sign
        assert "→" in line  # rightwards arrow


class TestRenderMathLineGRW:
    """Tests for _render_math_line_grw."""

    def test_render_math_line_grw_positive(self) -> None:
        """Positive value → '+' prefix."""
        line = _render_math_line_grw(
            employment_change_pct=15.2,
            build_score=8,
            score_max=10,
        )
        assert line == "+15.2% employment change → GRW score 8/10"

    def test_render_math_line_grw_negative(self) -> None:
        """Negative value → '-' prefix (no '+')."""
        line = _render_math_line_grw(
            employment_change_pct=-3.4,
            build_score=3,
            score_max=10,
        )
        assert line == "-3.4% employment change → GRW score 3/10"

    def test_render_math_line_grw_zero(self) -> None:
        """Zero → '0.0%' with no sign prefix."""
        line = _render_math_line_grw(
            employment_change_pct=0.0,
            build_score=5,
            score_max=10,
        )
        assert line == "0.0% employment change → GRW score 5/10"

    def test_render_math_line_grw_null(self) -> None:
        """None → 'n/a employment change'."""
        line = _render_math_line_grw(
            employment_change_pct=None,
            build_score=5,
            score_max=10,
        )
        assert line == "n/a employment change → score 5/10"

    def test_render_math_line_grw_large_positive(self) -> None:
        """Large positive value renders correctly."""
        line = _render_math_line_grw(
            employment_change_pct=42.7,
            build_score=10,
            score_max=10,
        )
        assert "+42.7%" in line
        assert "GRW score 10/10" in line

    def test_render_math_line_grw_small_negative(self) -> None:
        """Small negative value renders one decimal."""
        line = _render_math_line_grw(
            employment_change_pct=-0.3,
            build_score=4,
            score_max=10,
        )
        assert "-0.3%" in line


# ===========================================================================
# Registry tests
# ===========================================================================


class TestStatExplainRegistry:
    """Tests for _STAT_EXPLAIN_REGISTRY dispatch table."""

    def test_registry_dispatch_completeness(self) -> None:
        """ERN, ROI, RES, GRW all registered; AURA is not."""
        assert "ERN" in _STAT_EXPLAIN_REGISTRY
        assert "ROI" in _STAT_EXPLAIN_REGISTRY
        assert "RES" in _STAT_EXPLAIN_REGISTRY
        assert "GRW" in _STAT_EXPLAIN_REGISTRY
        assert "AURA" not in _STAT_EXPLAIN_REGISTRY

    def test_registry_stat_codes_match_keys(self) -> None:
        """Each registry entry's stat_code matches its dict key."""
        for key, config in _STAT_EXPLAIN_REGISTRY.items():
            assert config.stat_code == key, (
                f"Registry key '{key}' does not match config.stat_code "
                f"'{config.stat_code}'"
            )

    def test_registry_postprocessors_are_callable(self) -> None:
        """All registered postprocessors are callable."""
        for key, config in _STAT_EXPLAIN_REGISTRY.items():
            assert callable(config.postprocessor), (
                f"{key} postprocessor is not callable"
            )

    def test_registry_roi_config_has_correct_allowlist(self) -> None:
        """ROI config's label_allowlist has exactly the expected entry."""
        config = _STAT_EXPLAIN_REGISTRY["ROI"]
        assert config.label_allowlist == {100: "your debt-to-earnings ratio"}

    def test_registry_res_config_has_correct_allowlist(self) -> None:
        """RES config's label_allowlist is the position-based list."""
        config = _STAT_EXPLAIN_REGISTRY["RES"]
        assert config.label_allowlist == [
            (50, "AI exposure"),
            (50, "human-essential skills"),
        ]

    def test_registry_grw_config_has_correct_allowlist(self) -> None:
        """GRW config's label_allowlist has the employment change entry."""
        config = _STAT_EXPLAIN_REGISTRY["GRW"]
        assert config.label_allowlist == {
            100: "this career's projected employment change"
        }


# ===========================================================================
# _normalize_label_by_position tests
# ===========================================================================


class TestNormalizeLabelByPosition:
    """Tests for the position-based label normalizer."""

    def test_normalize_label_by_position_match_exact(self) -> None:
        """Exact canonical match → returned unchanged, was_normalized=False."""
        canonical, was = _normalize_label_by_position(
            0, "AI exposure", _RES_LABEL_ALLOWLIST
        )
        assert canonical == "AI exposure"
        assert was is False

    def test_normalize_label_by_position_match_case_insensitive(self) -> None:
        """Case-insensitive match → canonical returned, was_normalized=False."""
        canonical, was = _normalize_label_by_position(
            0, "ai Exposure", _RES_LABEL_ALLOWLIST
        )
        assert canonical == "AI exposure"
        assert was is False

    def test_normalize_label_by_position_match_with_whitespace(self) -> None:
        """Leading/trailing whitespace stripped before comparison."""
        canonical, was = _normalize_label_by_position(
            1, "  human-essential skills  ", _RES_LABEL_ALLOWLIST
        )
        assert canonical == "human-essential skills"
        assert was is False

    def test_normalize_label_by_position_off_script_replaced(self) -> None:
        """Off-script label at known position → replaced, was_normalized=True."""
        canonical, was = _normalize_label_by_position(
            0, "AI vulnerability score", _RES_LABEL_ALLOWLIST
        )
        assert canonical == "AI exposure"
        assert was is True

    def test_normalize_label_by_position_second_position(self) -> None:
        """Position 1 off-script → replaced with 'human-essential skills'."""
        canonical, was = _normalize_label_by_position(
            1, "human skills rating", _RES_LABEL_ALLOWLIST
        )
        assert canonical == "human-essential skills"
        assert was is True

    def test_normalize_label_by_position_out_of_bounds(self) -> None:
        """Index beyond allowlist length → Gemma's label kept, not normalized."""
        canonical, was = _normalize_label_by_position(
            5, "something unknown", _RES_LABEL_ALLOWLIST
        )
        assert canonical == "something unknown"
        assert was is False

    def test_normalize_label_by_position_empty_allowlist(self) -> None:
        """Empty allowlist → any index is out of bounds → passthrough."""
        canonical, was = _normalize_label_by_position(0, "anything", [])
        assert canonical == "anything"
        assert was is False
