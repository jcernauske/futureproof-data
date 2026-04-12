#!/usr/bin/env python
"""Spike F — Gemma intent resolution via OpenRouter (cloud inference).

Runs the same 20 CIP intent-resolution test cases as Spike E, but against
``google/gemma-4-26b-a4b-it`` on OpenRouter instead of the local
``gemma4:e4b`` model on Ollama. Records accuracy, latency, token usage, and
JSON-output conformance, and writes the results into the Findings section of
``docs/specs/spike-gemma-intent-openrouter.md``.

Throwaway. Read-only against the warehouse; does not touch production code or
data. Run with::

    uv run --with openai --with python-dotenv scripts/spike_gemma_intent_openrouter.py
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "src"
SCRIPTS = PROJECT_ROOT / "scripts"
for p in (SRC, SCRIPTS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from dotenv import load_dotenv  # noqa: E402

# Load the shared .env before the openai client is constructed.
ENV_PATH = Path.home() / "code" / "future_proof" / ".env"
load_dotenv(ENV_PATH)

from openai import OpenAI  # noqa: E402
from openai import APIError, APIStatusError, RateLimitError  # noqa: E402

from mcp_server.futureproof_server import FutureProofMCPServer  # noqa: E402

# Reuse everything we can from Spike E.
from spike_gemma_intent import (  # noqa: E402
    PROMPT_TEMPLATE,
    SQL_CIP4_MENU,
    TESTS,
    bucket_accuracy,
    build_menu,
    evaluate,
    parse_gemma_response,
    render_detail_table,
    render_reasoning_block,
)

SPEC_PATH = PROJECT_ROOT / "docs" / "specs" / "spike-gemma-intent-openrouter.md"

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
PAID_MODEL = "google/gemma-4-26b-a4b-it"
FREE_MODEL = "google/gemma-4-26b-a4b-it:free"

# OpenRouter published pricing for the paid model (per 1M tokens).
PRICE_PER_M_INPUT_USD = 0.12
PRICE_PER_M_OUTPUT_USD = 0.40

MAX_TOKENS = 256
REQUEST_TIMEOUT = 120.0


# ---------------------------------------------------------------------------
# OpenRouter call
# ---------------------------------------------------------------------------


def openrouter_generate(
    client: OpenAI,
    prompt: str,
) -> tuple[str, float, str, int, int]:
    """Call OpenRouter and return (text, latency, model_used, prompt_tok, completion_tok).

    Tries the paid model first and retries once on the free tier if the paid
    model returns a rate-limit or billing error.
    """
    errors: list[str] = []
    for model in (PAID_MODEL, FREE_MODEL):
        t0 = time.perf_counter()
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=MAX_TOKENS,
                timeout=REQUEST_TIMEOUT,
            )
        except (RateLimitError, APIStatusError) as exc:
            errors.append(f"{model}: {exc}")
            # Fall through and retry on the next model.
            continue
        except APIError as exc:
            errors.append(f"{model}: {exc}")
            continue
        dt = time.perf_counter() - t0
        msg = resp.choices[0].message
        text = msg.content or ""
        usage = getattr(resp, "usage", None)
        prompt_tok = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tok = int(getattr(usage, "completion_tokens", 0) or 0)
        return text, dt, model, prompt_tok, completion_tok

    raise RuntimeError(
        "Both paid and free OpenRouter models failed: " + " | ".join(errors)
    )


# ---------------------------------------------------------------------------
# Spec-file update (scoped to this spec, not Spike E's)
# ---------------------------------------------------------------------------


def update_findings(markdown_block: str) -> None:
    import re

    text = SPEC_PATH.read_text()
    # Replace everything between "## Findings" and the first "---" divider.
    pattern = re.compile(r"(## Findings\s*\n).*?(\n---\n)", re.DOTALL)
    replacement = r"\1\n" + markdown_block + r"\n\2"
    new_text, n = pattern.subn(replacement, text, count=1)
    if n == 0:
        raise RuntimeError(
            "Could not locate Findings section followed by '---' divider in "
            f"{SPEC_PATH}; refusing to write."
        )
    SPEC_PATH.write_text(new_text)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


# Spike E baseline (from its committed Findings section) for side-by-side.
SPIKE_E_TOTAL_ACCURACY_PCT = 100.0
SPIKE_E_AVG_LATENCY_S = 45.9
SPIKE_E_JSON_RATE = "20/20"
SPIKE_E_MODEL = "gemma4:e4b (Ollama)"


def run() -> int:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print(
            "OPENROUTER_API_KEY not set. Expected in "
            f"{ENV_PATH} or the shell environment.",
            file=sys.stderr,
        )
        return 2

    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)

    server = FutureProofMCPServer(
        warehouse_path=str(PROJECT_ROOT / "data" / "warehouse"),
        catalog_path=str(PROJECT_ROOT / "data" / "catalog" / "catalog.db"),
        server_name="futureproof-spike",
    )
    print("Loading CIP4 menu from base.cip_soc_crosswalk …", file=sys.stderr)
    menu_rows = server.query_iceberg(SQL_CIP4_MENU)
    menu = build_menu(menu_rows)
    print(
        f"  {len(menu_rows)} prefixes, {len(menu)} chars of menu",
        file=sys.stderr,
    )

    # Quick reachability ping.
    print(f"Pinging OpenRouter ({PAID_MODEL}) …", file=sys.stderr)
    try:
        _, ping_dt, ping_model, _, _ = openrouter_generate(
            client, "Say 'ready' in one word."
        )
        print(f"  OK ({ping_dt:.2f}s via {ping_model})", file=sys.stderr)
    except Exception as exc:
        print(f"OpenRouter unreachable: {exc}", file=sys.stderr)
        return 2

    results: list[dict] = []
    for test in TESTS:
        prompt = PROMPT_TEMPLATE.format(menu=menu, test_input=test["input"])
        print(
            f"[{test['id']:>2}] {test['bucket']:<9} {test['input']!r} …",
            file=sys.stderr,
        )
        try:
            raw, dt, model_used, prompt_tok, completion_tok = openrouter_generate(
                client, prompt
            )
        except Exception as exc:
            print(f"    ERROR: {exc}", file=sys.stderr)
            results.append(
                {
                    "test": test,
                    "parsed": {
                        "primary_cip": "",
                        "reasoning": f"ERROR: {exc}",
                        "alternatives": [],
                        "structured": False,
                        "raw": "",
                    },
                    "eval": {
                        "primary_correct": False,
                        "any_correct": False,
                        "correct": False,
                    },
                    "latency": 0.0,
                    "model": "error",
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                }
            )
            continue

        parsed = parse_gemma_response(raw)
        ev = evaluate(test, parsed)
        correct_mark = "OK " if ev["correct"] else "MISS"
        json_mark = "json" if parsed["structured"] else "nojson"
        print(
            f"    {correct_mark} {json_mark}  primary={parsed['primary_cip'] or '—':<6}"
            f" alts={parsed['alternatives']} ({dt:.2f}s"
            f" p={prompt_tok} c={completion_tok} via {model_used})",
            file=sys.stderr,
        )
        results.append(
            {
                "test": test,
                "parsed": parsed,
                "eval": ev,
                "latency": dt,
                "model": model_used,
                "prompt_tokens": prompt_tok,
                "completion_tokens": completion_tok,
            }
        )

    # ------------------------------------------------------------------
    # Aggregate
    # ------------------------------------------------------------------
    latencies = [r["latency"] for r in results if r["latency"] > 0]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    max_latency = max(latencies) if latencies else 0.0
    min_latency = min(latencies) if latencies else 0.0
    n_json_ok = sum(1 for r in results if r["parsed"]["structured"])

    easy_c, easy_n, easy_pct = bucket_accuracy(results, "easy")
    amb_c, amb_n, amb_pct = bucket_accuracy(results, "ambiguous")
    fuz_c, fuz_n, fuz_pct = bucket_accuracy(results, "fuzzy")
    unu_c, unu_n, unu_pct = bucket_accuracy(results, "unusual")
    total_scored = easy_n + amb_n + fuz_n + unu_n
    total_correct = easy_c + amb_c + fuz_c + unu_c
    total_pct = (total_correct / total_scored * 100) if total_scored else 0.0

    total_prompt_tok = sum(r["prompt_tokens"] for r in results)
    total_completion_tok = sum(r["completion_tokens"] for r in results)
    est_cost_usd = (
        total_prompt_tok / 1_000_000 * PRICE_PER_M_INPUT_USD
        + total_completion_tok / 1_000_000 * PRICE_PER_M_OUTPUT_USD
    )

    paid_calls = sum(1 for r in results if r.get("model") == PAID_MODEL)
    free_calls = sum(1 for r in results if r.get("model") == FREE_MODEL)
    err_calls = len(results) - paid_calls - free_calls

    # ------------------------------------------------------------------
    # Markdown
    # ------------------------------------------------------------------
    blocks: list[str] = []
    blocks.append(
        "_Generated by `scripts/spike_gemma_intent_openrouter.py` against "
        f"`{PAID_MODEL}` via OpenRouter and `base.cip_soc_crosswalk`._\n"
    )
    blocks.append("### 1. Setup\n")
    blocks.append(
        f"- **Model:** `{PAID_MODEL}` via OpenRouter "
        f"(`{OPENROUTER_BASE_URL}`)\n"
        f"- **Fallback model:** `{FREE_MODEL}` on rate limit / billing error\n"
        f"- **Menu:** {len(menu_rows)} 4-digit CIP prefixes "
        f"(≈{len(menu)} chars of prompt context)\n"
        f"- **Test cases:** {len(TESTS)} "
        "(5 easy, 5 ambiguous, 4 fuzzy, 6 unusual) — identical to Spike E\n"
        f"- **Decoding:** temperature 0, max_tokens={MAX_TOKENS}, JSON-only "
        "response contract\n"
        f"- **Model routing:** {paid_calls} paid, {free_calls} free, "
        f"{err_calls} errors\n"
    )
    blocks.append("### 2. Per-test Results\n")
    blocks.append(render_detail_table(results))
    blocks.append("")

    blocks.append("### 3. Gemma's Reasoning (verbatim)\n")
    blocks.append(render_reasoning_block(results))
    blocks.append("")

    blocks.append("### 4. Aggregate Scorecard\n")
    blocks.append(
        "| Bucket | Correct | Total | Accuracy |\n"
        "|---|---:|---:|---:|\n"
        f"| easy (direct match) | {easy_c} | {easy_n} | {easy_pct:.0f}% |\n"
        f"| ambiguous (reasoning) | {amb_c} | {amb_n} | {amb_pct:.0f}% |\n"
        f"| fuzzy (abbr/typo) | {fuz_c} | {fuz_n} | {fuz_pct:.0f}% |\n"
        f"| unusual (long tail) | {unu_c} | {unu_n} | {unu_pct:.0f}% |\n"
        f"| **overall** | **{total_correct}** | **{total_scored}** "
        f"| **{total_pct:.0f}%** |\n"
    )

    blocks.append("### 5. Latency, Tokens & Cost\n")
    blocks.append(
        f"- **Average latency:** {avg_latency:.2f}s per call\n"
        f"- **Min / max latency:** {min_latency:.2f}s / {max_latency:.2f}s\n"
        f"- **JSON-valid responses:** {n_json_ok}/{len(results)}\n"
        f"- **Total prompt tokens:** {total_prompt_tok:,}\n"
        f"- **Total completion tokens:** {total_completion_tok:,}\n"
        f"- **Estimated cost (paid tier "
        f"${PRICE_PER_M_INPUT_USD}/M input + "
        f"${PRICE_PER_M_OUTPUT_USD}/M output):** "
        f"${est_cost_usd:.4f} for {len(results)} calls\n"
    )

    blocks.append("### 6. Side-by-side: OpenRouter 26B MoE vs. Ollama E4B\n")
    speedup = (
        f"{SPIKE_E_AVG_LATENCY_S / avg_latency:.1f}×"
        if avg_latency > 0
        else "n/a"
    )
    blocks.append(
        "| Metric | OpenRouter `google/gemma-4-26b-a4b-it` | "
        f"Ollama `{SPIKE_E_MODEL}` |\n"
        "|---|---|---|\n"
        f"| Overall accuracy | {total_pct:.0f}% "
        f"({total_correct}/{total_scored}) | "
        f"{SPIKE_E_TOTAL_ACCURACY_PCT:.0f}% (19/19) |\n"
        f"| Avg latency | {avg_latency:.2f}s | "
        f"{SPIKE_E_AVG_LATENCY_S:.1f}s |\n"
        f"| Latency speedup | **{speedup}** | 1× (baseline) |\n"
        f"| JSON conformance | {n_json_ok}/{len(results)} | "
        f"{SPIKE_E_JSON_RATE} |\n"
        f"| Hardware | OpenRouter cloud GPU | Local consumer hardware |\n"
        f"| Per-call cost | ~${est_cost_usd / max(len(results), 1):.4f} | $0 |\n"
    )

    blocks.append("### 7. Assessment\n")

    verdict_lines: list[str] = []
    if easy_pct >= 90:
        verdict_lines.append(
            f"- **Easy cases ({easy_pct:.0f}%):** reliable — the 26B MoE "
            "nails direct-name matches just like the E4B did."
        )
    elif easy_pct >= 70:
        verdict_lines.append(
            f"- **Easy cases ({easy_pct:.0f}%):** mostly reliable; slips "
            "even on unambiguous inputs are concerning for a larger model."
        )
    else:
        verdict_lines.append(
            f"- **Easy cases ({easy_pct:.0f}%):** unreliable — the 26B MoE "
            "underperforms the E4B on direct matches, which would be a "
            "regression."
        )

    if amb_pct >= 80:
        verdict_lines.append(
            f"- **Ambiguous cases ({amb_pct:.0f}%):** strong reasoning on "
            "cross-family calls."
        )
    elif amb_pct >= 50:
        verdict_lines.append(
            f"- **Ambiguous cases ({amb_pct:.0f}%):** partial; borderline "
            "majors still need human-in-the-loop confirmation."
        )
    else:
        verdict_lines.append(
            f"- **Ambiguous cases ({amb_pct:.0f}%):** weak; the model "
            "cannot be trusted to break ties between adjacent CIP families."
        )

    if fuz_pct >= 75:
        verdict_lines.append(
            f"- **Fuzzy/abbreviations ({fuz_pct:.0f}%):** robust to the "
            "kinds of inputs that break a pure lookup table."
        )
    else:
        verdict_lines.append(
            f"- **Fuzzy/abbreviations ({fuz_pct:.0f}%):** brittle; the "
            "YAML lookup with alias expansion is still the right first line."
        )

    if unu_pct >= 50:
        verdict_lines.append(
            f"- **Unusual/long-tail ({unu_pct:.0f}%):** real value on the "
            "inputs a static table can never cover."
        )
    else:
        verdict_lines.append(
            f"- **Unusual/long-tail ({unu_pct:.0f}%):** long-tail coverage "
            "is limited; async review is required."
        )

    if avg_latency < 1.5:
        verdict_lines.append(
            f"- **Latency ({avg_latency:.2f}s avg):** well within "
            "query-time budget; safe for synchronous use at demo time."
        )
    elif avg_latency < 5.0:
        verdict_lines.append(
            f"- **Latency ({avg_latency:.2f}s avg):** borderline for "
            "query-time — usable as an opt-in surface, async for the "
            "default path."
        )
    else:
        verdict_lines.append(
            f"- **Latency ({avg_latency:.2f}s avg):** still too slow for "
            "synchronous query-time use even on cloud GPUs."
        )

    if n_json_ok == len(results):
        verdict_lines.append(
            "- **Structured output:** every call returned valid JSON — the "
            "same function-calling contract the production agent will use "
            "holds on the cloud backend."
        )
    elif n_json_ok >= len(results) * 0.8:
        verdict_lines.append(
            f"- **Structured output:** {n_json_ok}/{len(results)} valid "
            "JSON; a regex fallback is required to recover the rest."
        )
    else:
        verdict_lines.append(
            f"- **Structured output:** only {n_json_ok}/{len(results)} "
            "valid JSON — the prompt contract is not reliable; consider "
            "constrained decoding."
        )

    # Cost commentary.
    verdict_lines.append(
        f"- **Cost:** ${est_cost_usd:.4f} for {len(results)} calls "
        f"(~${est_cost_usd / max(len(results), 1):.4f}/call, "
        f"{total_prompt_tok:,} prompt + {total_completion_tok:,} completion "
        "tokens). At this rate, a live demo of a few hundred queries costs "
        "pennies."
    )

    blocks.extend(verdict_lines)
    blocks.append("")

    blocks.append("#### Verdict\n")
    baseline_delta = total_pct - SPIKE_E_TOTAL_ACCURACY_PCT
    if baseline_delta >= -5 and avg_latency < SPIKE_E_AVG_LATENCY_S / 2:
        verdict = (
            "OpenRouter `google/gemma-4-26b-a4b-it` is a **viable cloud "
            "backend** for the live demo. Accuracy matches (or is within "
            "tolerance of) the local E4B baseline and latency is materially "
            f"faster ({avg_latency:.2f}s vs {SPIKE_E_AVG_LATENCY_S:.1f}s, "
            f"{speedup}). The JSON contract held, so the production "
            "function-calling path works unchanged against the cloud "
            "endpoint."
        )
    elif baseline_delta >= -10:
        verdict = (
            "OpenRouter `google/gemma-4-26b-a4b-it` is **usable with "
            "reservations** as a cloud backend. Accuracy is close to the "
            f"E4B baseline ({total_pct:.0f}% vs "
            f"{SPIKE_E_TOTAL_ACCURACY_PCT:.0f}%) and latency is "
            f"{avg_latency:.2f}s vs {SPIKE_E_AVG_LATENCY_S:.1f}s "
            f"({speedup}); verify the missed buckets before committing to "
            "it for the demo."
        )
    else:
        verdict = (
            "OpenRouter `google/gemma-4-26b-a4b-it` **regresses** on "
            f"accuracy vs. the local E4B ({total_pct:.0f}% vs "
            f"{SPIKE_E_TOTAL_ACCURACY_PCT:.0f}%) despite the larger model. "
            "Do not substitute it for the local backend without "
            "investigating which cases regressed and why."
        )
    blocks.append(verdict)
    blocks.append("")

    markdown = "\n".join(blocks)
    update_findings(markdown)
    print(f"\nWrote findings to {SPEC_PATH}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(run())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
