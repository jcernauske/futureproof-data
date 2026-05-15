"""Scorer unit tests. No live LLM calls. These are the eval's ground truth —
if a scorer is wrong, every reported metric is wrong, so we test them hard."""

from __future__ import annotations

from pydantic import BaseModel

from eval.scorers import (
    GoldenCase,
    latency_percentiles,
    score_exact_match,
    score_schema_validity,
    score_tolerant_match,
    score_tool_call,
)


def _case(case_id: str = "test-001") -> GoldenCase:
    return GoldenCase(case_id=case_id, inputs={}, expected={})


# --- Schema scorer ---

class SimpleSchema(BaseModel):
    cipcode: str
    confidence: float
    title: str


def test_schema_valid_passes() -> None:
    actual = {"cipcode": "13.1011", "confidence": 0.85, "title": "Special Ed"}
    result = score_schema_validity(case=_case(), actual=actual, surface="x", schema=SimpleSchema)
    assert result.passed is True
    assert result.score == 1.0


def test_schema_missing_required_field_fails() -> None:
    actual = {"cipcode": "13.1011", "title": "Special Ed"}  # missing confidence
    result = score_schema_validity(case=_case(), actual=actual, surface="x", schema=SimpleSchema)
    assert result.passed is False
    assert result.score == 0.0
    assert result.error is not None and "confidence" in result.error


def test_schema_wrong_type_fails() -> None:
    actual = {"cipcode": "13.1011", "confidence": "high", "title": "Special Ed"}
    result = score_schema_validity(case=_case(), actual=actual, surface="x", schema=SimpleSchema)
    assert result.passed is False


def test_schema_none_input_fails() -> None:
    result = score_schema_validity(case=_case(), actual=None, surface="x", schema=SimpleSchema)
    assert result.passed is False
    assert result.error == "actual is None"


# --- Exact match scorer ---

def test_exact_match_cip_pass() -> None:
    result = score_exact_match(
        case=_case(),
        actual={"cipcode": "13.1011"},
        surface="x",
        field="cipcode",
        expected_value="13.1011",
    )
    assert result.passed is True
    assert result.score == 1.0


def test_exact_match_cip_fail() -> None:
    result = score_exact_match(
        case=_case(),
        actual={"cipcode": "13.1099"},
        surface="x",
        field="cipcode",
        expected_value="13.1011",
    )
    assert result.passed is False
    assert result.details["actual"] == "13.1099"


def test_exact_match_nested_field() -> None:
    actual = {"alternatives": [{"cipcode": "13.1101"}, {"cipcode": "13.1102"}]}
    result = score_exact_match(
        case=_case(),
        actual=actual,
        surface="x",
        field="alternatives.0.cipcode",
        expected_value="13.1101",
    )
    assert result.passed is True


def test_exact_match_missing_field() -> None:
    result = score_exact_match(
        case=_case(),
        actual={},
        surface="x",
        field="cipcode",
        expected_value="13.1011",
    )
    assert result.passed is False
    assert result.details["actual"] is None


# --- Tolerant match scorer ---

def test_tolerant_numeric_within_band() -> None:
    result = score_tolerant_match(
        case=_case(),
        actual={"confidence": 4.2},
        surface="x",
        field="confidence",
        expected_value=4.0,
        numeric_tolerance=0.5,
    )
    assert result.passed is True


def test_tolerant_numeric_outside_band() -> None:
    result = score_tolerant_match(
        case=_case(),
        actual={"confidence": 4.8},
        surface="x",
        field="confidence",
        expected_value=4.0,
        numeric_tolerance=0.5,
    )
    assert result.passed is False


def test_tolerant_accepted_set() -> None:
    result = score_tolerant_match(
        case=_case(),
        actual={"bucket": "data_analytics"},
        surface="x",
        field="bucket",
        expected_value=None,
        accepted_set={"data_science", "data_analytics", "stats"},
    )
    assert result.passed is True


def test_tolerant_string_similarity() -> None:
    result = score_tolerant_match(
        case=_case(),
        actual={"title": "registered nurse"},
        surface="x",
        field="title",
        expected_value="Registered Nurses",
        string_similarity_threshold=0.85,
    )
    assert result.passed is True


# --- Tool call scorer ---

def test_tool_call_correct_tool_and_args() -> None:
    actual = [
        {"name": "get_career_paths", "arguments": {"cipcode": "13.1011", "unitid": 151111}}
    ]
    result = score_tool_call(
        case=_case(),
        actual_tool_calls=actual,
        surface="ask_gemma",
        expected_tool="get_career_paths",
        expected_args={"cipcode": "13.1011"},
    )
    assert result.passed is True
    assert result.details["tool_name_match"] is True
    assert result.details["args_present_match"] is True


def test_tool_call_wrong_tool() -> None:
    actual = [{"name": "get_occupation_data", "arguments": {}}]
    result = score_tool_call(
        case=_case(),
        actual_tool_calls=actual,
        surface="ask_gemma",
        expected_tool="get_career_paths",
    )
    assert result.passed is False
    assert result.details["tool_name_match"] is False


def test_tool_call_no_call_made() -> None:
    result = score_tool_call(
        case=_case(),
        actual_tool_calls=[],
        surface="ask_gemma",
        expected_tool="get_career_paths",
    )
    assert result.passed is False
    assert result.error == "no tool calls made"


def test_tool_call_args_as_json_string() -> None:
    """OpenAI-style: arguments arrive as JSON string, not dict."""
    actual = [
        {
            "function": {
                "name": "get_career_paths",
                "arguments": '{"cipcode": "13.1011"}',
            }
        }
    ]
    result = score_tool_call(
        case=_case(),
        actual_tool_calls=actual,
        surface="ask_gemma",
        expected_tool="get_career_paths",
        expected_args={"cipcode": "13.1011"},
    )
    assert result.passed is True


def test_tool_call_value_mismatch_informational_by_default() -> None:
    actual = [{"name": "get_career_paths", "arguments": {"cipcode": "13.9999"}}]
    result = score_tool_call(
        case=_case(),
        actual_tool_calls=actual,
        surface="ask_gemma",
        expected_tool="get_career_paths",
        expected_args={"cipcode": "13.1011"},
        require_value_match=False,
    )
    assert result.passed is True  # informational only when not required
    assert result.details["value_match_score"] == 0.0


def test_tool_call_value_match_required_fails() -> None:
    actual = [{"name": "get_career_paths", "arguments": {"cipcode": "13.9999"}}]
    result = score_tool_call(
        case=_case(),
        actual_tool_calls=actual,
        surface="ask_gemma",
        expected_tool="get_career_paths",
        expected_args={"cipcode": "13.1011"},
        require_value_match=True,
    )
    assert result.passed is False


# --- Latency percentiles ---

def test_latency_empty() -> None:
    stats = latency_percentiles([])
    assert stats["n"] == 0
    assert stats["p50_ms"] == 0.0


def test_latency_single_sample() -> None:
    stats = latency_percentiles([1000])
    assert stats["n"] == 1
    assert stats["p50_ms"] == 1000.0
    assert stats["p95_ms"] == 1000.0


def test_latency_p95_on_100_samples() -> None:
    # 100 samples 1..100; p95 should be 95.05 with linear interpolation
    stats = latency_percentiles(list(range(1, 101)))
    assert stats["n"] == 100
    assert stats["p50_ms"] == 50.5
    assert 94.0 <= stats["p95_ms"] <= 96.0
    assert 98.0 <= stats["p99_ms"] <= 100.0


def test_latency_handles_unsorted_input() -> None:
    stats = latency_percentiles([300, 100, 200, 50])
    assert stats["min_ms"] == 50
    assert stats["max_ms"] == 300
    assert stats["p50_ms"] == 150.0  # median of [50, 100, 200, 300]
