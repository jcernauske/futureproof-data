"""Tool-call correctness scorer.

For function-calling surfaces (ask_gemma_chat, chip, explain_*, soc_expansion),
the question isn't 'did Gemma write good prose' — it's 'did Gemma pick the
right tool with reasonable arguments?'

Three sub-scores combined to a 0–1 score:
  1. Tool name match (1.0 or 0.0)
  2. Required-args present (1.0 if all expected_args keys exist, else 0.0)
  3. Required-args value match (mean of per-key exact match)

The overall pass requires (1) and (2); (3) is informational.
"""

from __future__ import annotations

from typing import Any

from eval.scorers.base import GoldenCase, ScoreResult


def score_tool_call(
    *,
    case: GoldenCase,
    actual_tool_calls: list[dict[str, Any]],
    surface: str,
    expected_tool: str,
    expected_args: dict[str, Any] | None = None,
    require_value_match: bool = False,
) -> ScoreResult:
    """Score one tool call.

    ``actual_tool_calls`` is the log of tool invocations Gemma made during
    a single turn. We score the FIRST call against the expectation; chained
    calls beyond the first are not penalized but not credited either.

    ``expected_args``: keys that must exist on the tool call. Values are
    checked only if ``require_value_match=True``; otherwise value mismatch
    is informational and doesn't fail the case.
    """
    if not actual_tool_calls:
        return ScoreResult(
            case_id=case.case_id,
            surface=surface,
            metric="tool_call",
            score=0.0,
            passed=False,
            details={"expected_tool": expected_tool, "actual_tool_calls": []},
            error="no tool calls made",
        )

    first = actual_tool_calls[0]
    actual_tool = first.get("name") or first.get("tool") or first.get("function", {}).get("name")
    actual_args = first.get("arguments") or first.get("args") or first.get("function", {}).get(
        "arguments"
    ) or {}

    if isinstance(actual_args, str):
        import json
        try:
            actual_args = json.loads(actual_args)
        except json.JSONDecodeError:
            actual_args = {}

    tool_name_ok = actual_tool == expected_tool
    expected_args = expected_args or {}
    args_present_ok = all(k in actual_args for k in expected_args)

    value_match_score: float | None = None
    value_mismatches: dict[str, dict[str, Any]] = {}
    if expected_args:
        matches = 0
        for k, v in expected_args.items():
            if actual_args.get(k) == v:
                matches += 1
            else:
                value_mismatches[k] = {"expected": v, "actual": actual_args.get(k)}
        value_match_score = matches / len(expected_args)

    if require_value_match and expected_args:
        passed = bool(tool_name_ok and args_present_ok and value_match_score == 1.0)
    else:
        passed = bool(tool_name_ok and args_present_ok)

    score = (
        (1.0 if tool_name_ok else 0.0) * 0.5
        + (1.0 if args_present_ok else 0.0) * 0.3
        + (value_match_score if value_match_score is not None else 1.0) * 0.2
    )

    return ScoreResult(
        case_id=case.case_id,
        surface=surface,
        metric="tool_call",
        score=score,
        passed=passed,
        details={
            "expected_tool": expected_tool,
            "actual_tool": actual_tool,
            "tool_name_match": tool_name_ok,
            "expected_args": expected_args,
            "actual_args": actual_args,
            "args_present_match": args_present_ok,
            "value_match_score": value_match_score,
            "value_mismatches": value_mismatches,
            "n_tool_calls": len(actual_tool_calls),
        },
    )
