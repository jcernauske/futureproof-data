#!/usr/bin/env python3
"""Head-to-head: gemma4:e2b vs gemma4:e4b on the SOC-expansion tool-calling task.

Runs the same 6-variant harness used in the original e4b baseline against each
model, then writes a side-by-side comparison file.

Usage:
    uv run python scripts/spike_e2b_vs_e4b_tool_calling.py --repeats 3
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.services.soc_expansion import EXPAND_SOCS_TOOL, SYSTEM_PROMPT  # noqa: E402


OLLAMA_NATIVE_URL = os.environ.get("OLLAMA_NATIVE_URL", "http://127.0.0.1:11434")

MODELS_TO_TEST = ["gemma4:e2b", "gemma4:e4b"]

BASE_SOCS = [
    "11-9121", "19-1029", "19-1042", "19-1099", "19-4012",
    "19-4013", "19-4021", "19-4092", "25-1042", "25-2031",
]

CANDIDATES_26 = [
    ("11-9111", "Medical and health services managers", "Management", "Bachelor's degree"),
    ("17-2031", "Bioengineers and biomedical engineers", "Architecture and Engineering", "Bachelor's degree"),
    ("29-1022", "Oral and maxillofacial surgeons", "Healthcare Practitioners and Technical", "Doctoral or professional degree"),
    ("29-1071", "Physician assistants", "Healthcare Practitioners and Technical", "Master's degree"),
    ("29-1214", "Emergency medicine physicians", "Healthcare Practitioners and Technical", "Doctoral or professional degree"),
    ("29-1215", "Family medicine physicians", "Healthcare Practitioners and Technical", "Doctoral or professional degree"),
    ("29-1216", "General internal medicine physicians", "Healthcare Practitioners and Technical", "Doctoral or professional degree"),
    ("29-1222", "Physicians, pathologists", "Healthcare Practitioners and Technical", "Doctoral or professional degree"),
    ("29-1229", "Physicians, all other", "Healthcare Practitioners and Technical", "Doctoral or professional degree"),
    ("29-1242", "Orthopedic surgeons, except pediatric", "Healthcare Practitioners and Technical", "Doctoral or professional degree"),
    ("29-1243", "Pediatric surgeons", "Healthcare Practitioners and Technical", "Doctoral or professional degree"),
    ("29-1249", "Surgeons, all other", "Healthcare Practitioners and Technical", "Doctoral or professional degree"),
    ("29-2032", "Diagnostic medical sonographers", "Healthcare Practitioners and Technical", "Associate's degree"),
    ("29-2036", "Medical dosimetrists", "Healthcare Practitioners and Technical", "Bachelor's degree"),
    ("29-2042", "Emergency medical technicians", "Healthcare Practitioners and Technical", "Postsecondary nondegree award"),
    ("29-2057", "Ophthalmic medical technicians", "Healthcare Practitioners and Technical", "Postsecondary nondegree award"),
    ("29-2072", "Medical records specialists", "Healthcare Practitioners and Technical", "Postsecondary nondegree award"),
    ("29-9021", "Health information technologists and medical registrars", "Healthcare Practitioners and Technical", "Associate's degree"),
    ("31-9092", "Medical assistants", "Healthcare Support", "Postsecondary nondegree award"),
    ("31-9093", "Medical equipment preparers", "Healthcare Support", "High school diploma or equivalent"),
    ("31-9094", "Medical transcriptionists", "Healthcare Support", "Postsecondary nondegree award"),
    ("43-6013", "Medical secretaries and administrative assistants", "Office and Administrative Support", "High school diploma or equivalent"),
    ("43-6014", "Secretaries and administrative assistants, except legal, medical, and executive", "Office and Administrative Support", "High school diploma or equivalent"),
    ("49-9062", "Medical equipment repairers", "Installation, Maintenance, and Repair", "Associate's degree"),
    ("51-9082", "Medical appliance technicians", "Production", "High school diploma or equivalent"),
    ("53-3011", "Ambulance drivers and attendants, except emergency medical technicians", "Transportation and Material Moving", "High school diploma or equivalent"),
]

CANDIDATES_8 = [CANDIDATES_26[i] for i in [2, 3, 4, 5, 6, 7, 8, 12]]
CANDIDATES_3 = [CANDIDATES_26[i] for i in [4, 5, 8]]

SHORT_SYSTEM = """\
Select SOC codes for a student who typed "doctor".

Use the expand_socs tool. Pick up to 5 SOC codes from the candidate pool
that directly represent physician or surgeon careers. Do not pick jobs that
are medical support, records, administration, or technician roles.
"""

JSON_SYSTEM = """\
Select SOC codes for a student who typed "doctor".

Return only JSON:
{"soc_codes":["XX-XXXX"],"rationale":"one sentence"}

Rules:
- Pick up to 5 SOC codes from the candidate pool.
- Pick physician or surgeon careers.
- Do not pick support, records, administration, or technician roles.
- Use only candidate SOC codes.
"""


def candidate_text(candidates: list[tuple[str, str, str, str]]) -> str:
    return "\n".join(
        f"{soc} | {title} | {group} | {education}"
        for soc, title, group, education in candidates
    )


def user_message(candidates: list[tuple[str, str, str, str]]) -> str:
    return (
        "Student intent keywords: doctor\n\n"
        "Already in the student's list (do not pick these):\n"
        f"{', '.join(BASE_SOCS)}\n\n"
        "Candidate pool (pick from these only):\n"
        f"{candidate_text(candidates)}"
    )


def post_ollama(payload: dict[str, Any], timeout_s: float) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_NATIVE_URL}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_tool_args(response: dict[str, Any]) -> dict[str, Any] | None:
    message = response.get("message") or {}
    tool_calls = message.get("tool_calls") or []
    if not tool_calls:
        return None
    function = (tool_calls[0] or {}).get("function") or {}
    args = function.get("arguments")
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        try:
            parsed = json.loads(args)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def extract_json_args(response: dict[str, Any]) -> dict[str, Any] | None:
    content = ((response.get("message") or {}).get("content") or "").strip()
    if not content:
        return None
    start = content.find("{")
    end = content.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        parsed = json.loads(content[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def validate(args: dict[str, Any] | None, candidates: list[tuple[str, str, str, str]]) -> tuple[bool, list[str]]:
    if not isinstance(args, dict):
        return False, []
    codes = args.get("soc_codes")
    if not isinstance(codes, list):
        return False, []
    candidate_codes = {c[0] for c in candidates}
    selected = [c for c in codes if isinstance(c, str)]
    valid = bool(selected) and all(c in candidate_codes for c in selected)
    return valid, selected


def run_case(
    *,
    model: str,
    label: str,
    mode: str,
    system: str,
    candidates: list[tuple[str, str, str, str]],
    timeout_s: float,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message(candidates)},
        ],
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "num_predict": 600},
    }
    if mode == "tool":
        payload["tools"] = [EXPAND_SOCS_TOOL]
    else:
        payload["format"] = "json"

    started = time.perf_counter()
    try:
        response = post_ollama(payload, timeout_s)
        duration_ms = int((time.perf_counter() - started) * 1000)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {
            "model": model,
            "label": label,
            "mode": mode,
            "candidate_count": len(candidates),
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "selected": [],
            "has_native_tool_call": False,
        }

    args = extract_tool_args(response) if mode == "tool" else extract_json_args(response)
    ok, selected = validate(args, candidates)
    return {
        "model": model,
        "label": label,
        "mode": mode,
        "candidate_count": len(candidates),
        "duration_ms": duration_ms,
        "ok": ok,
        "selected": selected,
        "raw_args": args,
        "content_preview": ((response.get("message") or {}).get("content") or "")[:200],
        "has_native_tool_call": bool(extract_tool_args(response)),
    }


def summarize(results: list[dict[str, Any]], model: str) -> list[dict[str, Any]]:
    rows = []
    model_results = [r for r in results if r["model"] == model]
    labels = list(dict.fromkeys(r["label"] for r in model_results))
    for label in labels:
        group = [r for r in model_results if r["label"] == label]
        durations = [r["duration_ms"] for r in group]
        oks = [r for r in group if r["ok"]]
        tool_calls = [r for r in group if r.get("has_native_tool_call")]
        rows.append({
            "model": model,
            "label": label,
            "runs": len(group),
            "successes": len(oks),
            "success_rate": len(oks) / len(group) if group else 0.0,
            "native_tool_calls": len(tool_calls),
            "p50_ms": int(statistics.median(durations)) if durations else 0,
            "avg_ms": int(sum(durations) / len(durations)) if durations else 0,
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--timeout-s", type=float, default=60.0)
    parser.add_argument(
        "--models",
        type=str,
        default=",".join(MODELS_TO_TEST),
        help="Comma-separated list of Ollama model tags to test",
    )
    args = parser.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    variants = [
        ("tool_current_26", "tool", SYSTEM_PROMPT, CANDIDATES_26),
        ("tool_short_26", "tool", SHORT_SYSTEM, CANDIDATES_26),
        ("tool_short_8", "tool", SHORT_SYSTEM, CANDIDATES_8),
        ("tool_short_3", "tool", SHORT_SYSTEM, CANDIDATES_3),
        ("json_short_26", "json", JSON_SYSTEM, CANDIDATES_26),
        ("json_short_8", "json", JSON_SYSTEM, CANDIDATES_8),
    ]

    results: list[dict[str, Any]] = []
    print(f"Ollama: {OLLAMA_NATIVE_URL}")
    print(f"Models: {models}")
    print(f"Repeats: {args.repeats}, Timeout: {args.timeout_s}s")

    for model in models:
        print(f"\n=== Model: {model} ===")
        for i in range(args.repeats):
            print(f"  Repeat {i + 1}/{args.repeats}")
            for label, mode, system, candidates in variants:
                result = run_case(
                    model=model,
                    label=label,
                    mode=mode,
                    system=system,
                    candidates=candidates,
                    timeout_s=args.timeout_s,
                )
                results.append(result)
                status = "ok" if result["ok"] else "FAIL"
                tool = "tool" if result.get("has_native_tool_call") else "no-tool"
                err = f"  err: {result.get('error')}" if "error" in result else ""
                print(
                    f"    {label:18} {status:4} {tool:7} "
                    f"{result['duration_ms']:5}ms{err}"
                )

    summary_by_model = {m: summarize(results, m) for m in models}

    out = {
        "ollama_native_url": OLLAMA_NATIVE_URL,
        "repeats": args.repeats,
        "models": models,
        "results": results,
        "summary_by_model": summary_by_model,
    }
    out_path = PROJECT_ROOT / "reports" / "spike_e2b_vs_e4b_tool_calling_results.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("\n\n=== HEAD-TO-HEAD SUMMARY ===\n")
    labels = [v[0] for v in variants]
    header = "| Variant | " + " | ".join(f"{m} success" for m in models) + " | " + " | ".join(f"{m} p50" for m in models) + " |"
    sep = "|---|" + "---:|" * (2 * len(models))
    print(header)
    print(sep)
    for label in labels:
        row_cells = [f" {label} "]
        for model in models:
            rows = summary_by_model[model]
            mrow = next((r for r in rows if r["label"] == label), None)
            if mrow:
                row_cells.append(f" {mrow['successes']}/{mrow['runs']} ({mrow['success_rate']:.0%}) ")
            else:
                row_cells.append(" - ")
        for model in models:
            rows = summary_by_model[model]
            mrow = next((r for r in rows if r["label"] == label), None)
            if mrow:
                row_cells.append(f" {mrow['p50_ms']}ms ")
            else:
                row_cells.append(" - ")
        print("|" + "|".join(row_cells) + "|")

    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
