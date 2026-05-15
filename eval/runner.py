"""Eval runner. Loads golden cases for one or more surfaces, runs them
through the registered adapter, scores each case, and writes timestamped
results.

Usage:
    python -m eval.runner --tier P0 --out eval/results
    python -m eval.runner --surface career_intent --out eval/results
    python -m eval.runner --latency-only  # skip surface runs; just aggregate JSONL log

Results land in eval/results/<timestamp>/ with:
    summary.json          aggregate per-surface metrics
    summary.md            human-readable table
    <surface>.jsonl       per-case results
    latency.jsonl         latency rows from logs/gemma.jsonl filtered by surface
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval.adapters.registry import get_adapter, known_surfaces, surfaces_in_tier
from eval.instrumentation import (
    SURFACE_TO_CALL_SITES,
    latency_for_surface,
)
from eval.scorers import (
    GoldenCase,
    ScoreResult,
    latency_percentiles,
    score_directional_content,
    score_exact_match,
    score_length_range,
    score_schema_validity,
    score_skill_pool,
    score_tolerant_match,
    score_tool_call,
)
from eval.scorers.rubric import score_rubric


REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = REPO_ROOT / "eval" / "golden"
RESULTS_DIR = REPO_ROOT / "eval" / "results"
LOG_PATH = REPO_ROOT / "logs" / "gemma.jsonl"


def _load_cases(surface: str) -> list[GoldenCase]:
    path = GOLDEN_DIR / surface / "cases.jsonl"
    if not path.exists():
        return []
    cases: list[GoldenCase] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            payload = json.loads(line)
            cases.append(GoldenCase.model_validate(payload))
    return cases


def _score_one(
    *,
    case: GoldenCase,
    actual: Any,
    raw: dict[str, Any],
    surface: str,
) -> list[ScoreResult]:
    """Apply every scorer the case asks for. Scorers are declared in
    case.expected with these keys:

      schema: {"module": "...", "class": "..."}  → resolved to Pydantic class
      exact_match: {"field": ..., "value": ...}
      exact_matches: [{...}, ...]
      tolerant_match: {"field": ..., "value": ..., "tolerance": ...}
      tool_call: {"expected_tool": ..., "expected_args": {...}}
      rubric: {"surface_description": ..., "char_budget": ..., "input_context": ...}
    """
    results: list[ScoreResult] = []
    expected = case.expected

    if "schema" in expected:
        spec = expected["schema"]
        try:
            mod = __import__(spec["module"], fromlist=[spec["class"]])
            schema_cls = getattr(mod, spec["class"])
            results.append(
                score_schema_validity(case=case, actual=actual, surface=surface, schema=schema_cls)
            )
        except (ImportError, AttributeError) as exc:
            results.append(
                ScoreResult(
                    case_id=case.case_id,
                    surface=surface,
                    metric="schema_valid",
                    score=0.0,
                    passed=False,
                    error=f"schema_resolve_error: {exc}",
                )
            )

    for em in expected.get("exact_matches", []):
        results.append(
            score_exact_match(
                case=case,
                actual=actual,
                surface=surface,
                field=em["field"],
                expected_value=em["value"],
            )
        )

    if "exact_match" in expected:
        em = expected["exact_match"]
        results.append(
            score_exact_match(
                case=case,
                actual=actual,
                surface=surface,
                field=em["field"],
                expected_value=em["value"],
            )
        )

    if "tolerant_match" in expected:
        tm = expected["tolerant_match"]
        results.append(
            score_tolerant_match(
                case=case,
                actual=actual,
                surface=surface,
                field=tm["field"],
                expected_value=tm.get("value"),
                numeric_tolerance=tm.get("tolerance", 0.0),
                string_similarity_threshold=tm.get("similarity_threshold", 1.0),
                accepted_set=set(tm["accepted_set"]) if "accepted_set" in tm else None,
            )
        )

    for dc in expected.get("directional_content", []):
        results.append(
            score_directional_content(
                case=case,
                actual=actual,
                surface=surface,
                field=dc["field"],
                expected_directional=dc["any_of"],
                require_all=dc.get("require_all", False),
            )
        )

    for lr in expected.get("length_ranges", []):
        results.append(
            score_length_range(
                case=case,
                actual=actual,
                surface=surface,
                field=lr["field"],
                min_chars=lr.get("min", 1),
                max_chars=lr.get("max", 1000),
            )
        )

    if "tool_call" in expected:
        tc = expected["tool_call"]
        results.append(
            score_tool_call(
                case=case,
                actual_tool_calls=raw.get("tool_call_log", []),
                surface=surface,
                expected_tool=tc["expected_tool"],
                expected_args=tc.get("expected_args"),
                require_value_match=tc.get("require_value_match", False),
            )
        )

    if "skill_pool" in expected:
        sp = expected["skill_pool"]
        text_output = actual if isinstance(actual, str) else raw.get("text", "")
        results.extend(
            score_skill_pool(
                case=case,
                raw_text=text_output,
                surface=surface,
                school_name=sp["school_name"],
            )
        )

    if "rubric" in expected:
        rb = expected["rubric"]
        text_output = actual if isinstance(actual, str) else raw.get("text", "")
        if text_output:
            results.append(
                score_rubric(
                    case=case,
                    actual_output=text_output,
                    surface=surface,
                    surface_description=rb["surface_description"],
                    char_budget=rb["char_budget"],
                    input_context=rb["input_context"],
                )
            )

    return results


def _run_surface(
    surface: str,
    *,
    eval_start_iso: str,
    enable_rubric: bool = True,
) -> dict[str, Any]:
    """Run all golden cases for one surface and return aggregate metrics."""
    cases = _load_cases(surface)
    if not cases:
        return {"surface": surface, "n_cases": 0, "note": "no golden cases"}

    adapter = get_adapter(surface)
    case_results: list[dict[str, Any]] = []
    score_counts: dict[str, dict[str, int]] = {}

    for case in cases:
        if not enable_rubric and "rubric" in case.expected:
            case.expected = {k: v for k, v in case.expected.items() if k != "rubric"}

        adapter_result = adapter.run(case.inputs)

        scores: list[ScoreResult] = []
        if adapter_result.error:
            scores.append(
                ScoreResult(
                    case_id=case.case_id,
                    surface=surface,
                    metric="adapter",
                    score=0.0,
                    passed=False,
                    error=adapter_result.error,
                    latency_ms=adapter_result.latency_ms,
                )
            )
        else:
            scores = _score_one(
                case=case,
                actual=adapter_result.actual_output,
                raw=adapter_result.raw,
                surface=surface,
            )

        for s in scores:
            bucket = score_counts.setdefault(s.metric, {"pass": 0, "fail": 0, "n": 0})
            bucket["n"] += 1
            bucket["pass" if s.passed else "fail"] += 1

        case_results.append(
            {
                "case_id": case.case_id,
                "tags": case.tags,
                "latency_ms": adapter_result.latency_ms,
                "adapter_error": adapter_result.error,
                "scores": [s.model_dump() for s in scores],
            }
        )

    durations = [r["latency_ms"] for r in case_results if r["latency_ms"]]
    log_durations = (
        latency_for_surface(LOG_PATH, surface, since_iso=eval_start_iso)
        if LOG_PATH.exists()
        else []
    )
    durations.extend(log_durations)

    return {
        "surface": surface,
        "n_cases": len(cases),
        "score_counts": score_counts,
        "latency": latency_percentiles(durations) if durations else None,
        "cases": case_results,
    }


def _aggregate_latency_only(eval_start_iso: str | None = None) -> dict[str, Any]:
    """Pull latency from logs/gemma.jsonl for every known surface, no
    adapter runs. Used by `make eval-latency` and as the always-on row in
    every eval report."""
    out: dict[str, Any] = {}
    if not LOG_PATH.exists():
        return {"error": f"no log file at {LOG_PATH}"}

    for surface in SURFACE_TO_CALL_SITES:
        durations = latency_for_surface(LOG_PATH, surface, since_iso=eval_start_iso)
        if durations:
            out[surface] = latency_percentiles(durations)
    return out


def _write_results(results_dir: Path, summary: dict[str, Any]) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    (results_dir / "summary.md").write_text(_render_markdown(summary))


def _render_markdown(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# Eval Results — {summary.get('timestamp', 'unknown')}\n")
    lines.append(f"Backend: `{summary.get('backend', 'unknown')}`")
    lines.append(f"Run mode: `{summary.get('mode', 'unknown')}`\n")

    surface_summaries = summary.get("surfaces", {})
    if surface_summaries:
        lines.append("## Per-surface scores\n")
        lines.append("| Surface | N cases | Metrics |")
        lines.append("|---------|--------:|---------|")
        for name, s in surface_summaries.items():
            n = s.get("n_cases", 0)
            metrics = s.get("score_counts", {})
            cells = [
                f"{m}: {b['pass']}/{b['n']}" for m, b in metrics.items()
            ]
            lines.append(f"| {name} | {n} | {'<br>'.join(cells) if cells else '—'} |")
        lines.append("")

    latency = summary.get("latency", {})
    if latency:
        lines.append("## Latency (all 20 surfaces, from logs/gemma.jsonl)\n")
        lines.append("| Surface | n | p50 ms | p95 ms | p99 ms |")
        lines.append("|---------|--:|------:|------:|------:|")
        for name in sorted(latency):
            stats = latency[name]
            lines.append(
                f"| {name} | {stats['n']} | "
                f"{stats['p50_ms']:.0f} | {stats['p95_ms']:.0f} | {stats['p99_ms']:.0f} |"
            )
        lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FutureProof Gemma eval runner")
    parser.add_argument("--tier", choices=("P0", "P1", "P2"), help="Run all surfaces in this tier")
    parser.add_argument("--surface", action="append", help="Specific surface(s); repeatable")
    parser.add_argument("--latency-only", action="store_true", help="Just aggregate latency log")
    parser.add_argument("--no-rubric", action="store_true", help="Skip rubric scoring (no API key)")
    parser.add_argument("--out", type=Path, default=RESULTS_DIR, help="Results parent dir")
    args = parser.parse_args(argv)

    eval_start_iso = datetime.now(timezone.utc).isoformat()
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    run_dir = args.out / timestamp

    summary: dict[str, Any] = {
        "timestamp": timestamp,
        "backend": __import__("os").environ.get("INFERENCE_BACKEND", "ollama"),
        "mode": "latency-only" if args.latency_only else "full",
        "surfaces": {},
    }

    if args.latency_only:
        # No `since_iso` filter — we want the full historical log when running
        # latency-only. Use --tier / --surface for a fresh slice.
        summary["latency"] = _aggregate_latency_only(eval_start_iso=None)
        _write_results(run_dir, summary)
        print(f"Wrote latency-only results to {run_dir}")
        return 0

    if args.surface:
        surfaces = args.surface
    elif args.tier:
        surfaces = surfaces_in_tier(args.tier)
    else:
        print("must pass --tier, --surface, or --latency-only", file=sys.stderr)
        return 2

    unknown = set(surfaces) - set(known_surfaces())
    if unknown:
        print(f"unknown surfaces: {sorted(unknown)}", file=sys.stderr)
        return 2

    for surface in surfaces:
        print(f"running {surface}...", flush=True)
        result = _run_surface(
            surface,
            eval_start_iso=eval_start_iso,
            enable_rubric=not args.no_rubric,
        )
        (run_dir / f"{surface}.json").parent.mkdir(parents=True, exist_ok=True)
        summary["surfaces"][surface] = result

    summary["latency"] = _aggregate_latency_only(eval_start_iso=eval_start_iso)
    _write_results(run_dir, summary)
    print(f"Wrote results to {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
