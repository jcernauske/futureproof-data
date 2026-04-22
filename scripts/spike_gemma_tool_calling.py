#!/usr/bin/env python3
"""Pre-flight spike: test Gemma tool-calling reliability on both backends.

Runs 20 chip-dispatch-shaped prompts with tools=[get_career_paths] against
both gemma4:e4b (Ollama) and google/gemma-4-26b-a4b-it (OpenRouter).

Records: tool-call success rate, argument validity, latency per call.
Writes findings to §5 of feature-chip-dispatch-mcp-tool-calling.md.

Usage:
    python scripts/spike_gemma_tool_calling.py [--backend ollama|openrouter|both]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Add project paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(PROJECT_ROOT / ".env", override=False)

GET_CAREER_PATHS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_career_paths",
        "description": (
            "Core product query. Given a school (unitid) and major (cipcode), "
            "returns every career outcome the program leads to, with stats, "
            "boss-fight scores, earnings, and task summaries."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "unitid": {
                    "type": "integer",
                    "description": "IPEDS 6-digit institution identifier (e.g., 151351 for Indiana University).",
                },
                "cipcode": {
                    "type": "string",
                    "description": "CIP program code in XX.XX or XX.XXXX format (e.g., '52.1401' for Marketing).",
                },
                "student_major": {
                    "type": "string",
                    "description": "Optional. The student's stated major for CIP substitution.",
                },
            },
            "required": ["unitid", "cipcode"],
        },
    },
}

SCENARIOS = [
    {
        "label": "marketing-manager-at-iu",
        "system_snippet": "School: Indiana University (unitid 151351), Current: 52.1401 Marketing",
        "clarifier": "I wanted marketing-manager jobs, not general business.",
    },
    {
        "label": "deaf-ed-at-iu",
        "system_snippet": "School: Indiana University (unitid 151351), Current: 13.1001 Special Education",
        "clarifier": "I want to teach deaf students specifically.",
    },
    {
        "label": "premed-biology",
        "system_snippet": "School: Indiana University (unitid 151351), Current: 26.0101 Biology",
        "clarifier": "I'm pre-med, I want to see physician careers.",
    },
    {
        "label": "cs-game-design",
        "system_snippet": "School: Purdue University (unitid 243780), Current: 11.0101 Computer Science",
        "clarifier": "I want to design video games, not just code.",
    },
    {
        "label": "nursing-at-liberal-arts",
        "system_snippet": "School: DePauw University (unitid 150400), Current: 24.0101 Liberal Arts",
        "clarifier": "I want to be a nurse.",
    },
    {
        "label": "accounting-specific",
        "system_snippet": "School: Indiana University (unitid 151351), Current: 52.0201 Business/Commerce",
        "clarifier": "I want accounting jobs specifically.",
    },
    {
        "label": "physical-therapy",
        "system_snippet": "School: Ball State University (unitid 150136), Current: 51.0001 Health Professions",
        "clarifier": "I want to be a physical therapist.",
    },
    {
        "label": "ux-design",
        "system_snippet": "School: Indiana University (unitid 151351), Current: 50.0401 Design and Visual Comms",
        "clarifier": "I want UX design, not graphic design.",
    },
    {
        "label": "data-science",
        "system_snippet": "School: Purdue University (unitid 243780), Current: 27.0101 Mathematics",
        "clarifier": "I'm interested in data science careers.",
    },
    {
        "label": "environmental-science",
        "system_snippet": "School: Indiana University (unitid 151351), Current: 03.0104 Environmental Science",
        "clarifier": "I want to work in environmental policy.",
    },
    {
        "label": "social-work",
        "system_snippet": "School: Ball State University (unitid 150136), Current: 44.0701 Social Work",
        "clarifier": "I want clinical social work, not just any social work.",
    },
    {
        "label": "mechanical-engineering",
        "system_snippet": "School: Purdue University (unitid 243780), Current: 14.1901 Mechanical Engineering",
        "clarifier": "I want aerospace jobs.",
    },
    {
        "label": "journalism",
        "system_snippet": "School: Indiana University (unitid 151351), Current: 09.0401 Journalism",
        "clarifier": "What about sports journalism specifically?",
    },
    {
        "label": "psychology-clinical",
        "system_snippet": "School: Indiana University (unitid 151351), Current: 42.0101 Psychology",
        "clarifier": "I want to be a clinical psychologist.",
    },
    {
        "label": "broad-input-business",
        "system_snippet": "School: Indiana University (unitid 151351), Current: 52.0201 Business/Commerce",
        "clarifier": "I just don't like these jobs.",
    },
    {
        "label": "music-education",
        "system_snippet": "School: Ball State University (unitid 150136), Current: 13.1312 Music Education",
        "clarifier": "I want to perform, not teach.",
    },
    {
        "label": "criminal-justice",
        "system_snippet": "School: Indiana University (unitid 151351), Current: 43.0104 Criminal Justice",
        "clarifier": "I want to be an FBI agent.",
    },
    {
        "label": "finance-quant",
        "system_snippet": "School: Purdue University (unitid 243780), Current: 52.0801 Finance",
        "clarifier": "I'm interested in quantitative finance, algorithmic trading.",
    },
    {
        "label": "art-therapy",
        "system_snippet": "School: Indiana University (unitid 151351), Current: 50.0701 Fine/Studio Art",
        "clarifier": "I want to use art for therapy.",
    },
    {
        "label": "supply-chain",
        "system_snippet": "School: Purdue University (unitid 243780), Current: 52.0201 Business/Commerce",
        "clarifier": "I want supply chain management roles.",
    },
]

SYSTEM_TEMPLATE = """\
You are FutureProof's career-planning assistant. A student tapped "Not what I expected."

{system_snippet}

You have access to one tool: get_career_paths. Call it when you need to look up
career outcomes for a school + program combination to answer the student's question.

After your tool call returns (if any), provide a brief 2-3 sentence response.
"""


def run_one(
    client: OpenAI,
    model: str,
    scenario: dict,
    backend_name: str,
) -> dict:
    system = SYSTEM_TEMPLATE.format(system_snippet=scenario["system_snippet"])
    user = f'Student clarifier: "{scenario["clarifier"]}"'

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    started = time.perf_counter()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=[GET_CAREER_PATHS_TOOL],
            tool_choice="auto",
            max_tokens=600,
            temperature=0.0,
        )
    except Exception as exc:
        elapsed = int((time.perf_counter() - started) * 1000)
        return {
            "label": scenario["label"],
            "backend": backend_name,
            "tool_call": False,
            "args_valid": False,
            "error": str(exc),
            "latency_ms": elapsed,
        }

    elapsed = int((time.perf_counter() - started) * 1000)
    choices = getattr(response, "choices", [])
    if not choices:
        return {
            "label": scenario["label"],
            "backend": backend_name,
            "tool_call": False,
            "args_valid": False,
            "error": "no_choices",
            "latency_ms": elapsed,
        }

    choice = choices[0]
    message = getattr(choice, "message", None)
    tool_calls = getattr(message, "tool_calls", None) if message else None

    if not tool_calls:
        content = getattr(message, "content", "") or ""
        return {
            "label": scenario["label"],
            "backend": backend_name,
            "tool_call": False,
            "args_valid": False,
            "content_preview": content[:200],
            "latency_ms": elapsed,
        }

    tc = tool_calls[0]
    fn = getattr(tc, "function", None)
    fn_name = getattr(fn, "name", "") if fn else ""
    fn_args_raw = getattr(fn, "arguments", "") if fn else ""

    args_valid = False
    parsed_args = None
    try:
        parsed_args = json.loads(fn_args_raw) if isinstance(fn_args_raw, str) else fn_args_raw
        if isinstance(parsed_args, dict):
            has_unitid = "unitid" in parsed_args
            has_cipcode = "cipcode" in parsed_args
            unitid_ok = isinstance(parsed_args.get("unitid"), (int, str))
            cipcode_ok = isinstance(parsed_args.get("cipcode"), str)
            args_valid = has_unitid and has_cipcode and unitid_ok and cipcode_ok
    except (json.JSONDecodeError, TypeError):
        pass

    return {
        "label": scenario["label"],
        "backend": backend_name,
        "tool_call": True,
        "tool_name": fn_name,
        "args_valid": args_valid,
        "parsed_args": parsed_args,
        "latency_ms": elapsed,
    }


def run_backend(backend: str) -> list[dict]:
    if backend == "ollama":
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        api_key = os.environ.get("OLLAMA_API_KEY", "ollama")
        model = os.environ.get("OLLAMA_MODEL", "gemma4:e4b")
    else:
        base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        model = os.environ.get("OPENROUTER_MODEL", "google/gemma-4-26b-a4b-it")
        if not api_key:
            print(f"  SKIP {backend}: OPENROUTER_API_KEY not set")
            return []

    client = OpenAI(base_url=base_url, api_key=api_key)
    results = []
    for i, scenario in enumerate(SCENARIOS):
        print(f"  [{backend}] {i+1}/{len(SCENARIOS)}: {scenario['label']}...", end=" ", flush=True)
        result = run_one(client, model, scenario, backend)
        tc = "TOOL" if result["tool_call"] else "TEXT"
        av = "VALID" if result.get("args_valid") else "INVALID"
        print(f"{tc} {av} {result['latency_ms']}ms")
        results.append(result)
    return results


def summarize(results: list[dict], backend: str) -> dict:
    if not results:
        return {"backend": backend, "count": 0}
    total = len(results)
    tool_calls = sum(1 for r in results if r["tool_call"])
    valid_args = sum(1 for r in results if r.get("args_valid"))
    latencies = [r["latency_ms"] for r in results]
    avg_latency = sum(latencies) // total
    p50 = sorted(latencies)[total // 2]
    return {
        "backend": backend,
        "count": total,
        "tool_call_rate": f"{tool_calls}/{total} ({100*tool_calls//total}%)",
        "valid_args_rate": f"{valid_args}/{total} ({100*valid_args//total}%)",
        "avg_latency_ms": avg_latency,
        "p50_latency_ms": p50,
        "success_rate_pct": 100 * valid_args // total,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["ollama", "openrouter", "both"], default="both")
    args = parser.parse_args()

    backends = ["ollama", "openrouter"] if args.backend == "both" else [args.backend]
    all_results = {}

    for backend in backends:
        print(f"\n=== {backend.upper()} ===")
        results = run_backend(backend)
        if results:
            summary = summarize(results, backend)
            all_results[backend] = {"results": results, "summary": summary}
            print(f"\n  Summary: {json.dumps(summary, indent=2)}")

    # Write raw results
    out_path = PROJECT_ROOT / "scripts" / "spike_gemma_tool_calling_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nRaw results: {out_path}")

    # Print markdown table
    print("\n### Spike Results\n")
    print("| Backend | Scenarios | Tool-Call Rate | Valid Args | Avg Latency | P50 Latency |")
    print("|---------|-----------|---------------|------------|-------------|-------------|")
    for backend, data in all_results.items():
        s = data["summary"]
        print(f"| {s['backend']} | {s['count']} | {s['tool_call_rate']} | {s['valid_args_rate']} | {s['avg_latency_ms']}ms | {s['p50_latency_ms']}ms |")

    # Decision
    for backend, data in all_results.items():
        rate = data["summary"]["success_rate_pct"]
        if rate >= 80:
            print(f"\n{backend}: SUCCESS RATE {rate}% >= 80% — real tools=[...] path")
        else:
            print(f"\n{backend}: SUCCESS RATE {rate}% < 80% — FALLBACK to prompt-then-parse")


if __name__ == "__main__":
    main()
