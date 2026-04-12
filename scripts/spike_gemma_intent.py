#!/usr/bin/env python
"""Spike E — Gemma intent resolution: ambiguous major → 4-digit CIP.

Builds a menu of all 4-digit CIP prefixes present in ``base.cip_soc_crosswalk``
(with titles), then asks a local Gemma model (``gemma4:e4b`` via Ollama) to
pick the best CIP for each of 20 test student majors. Records accuracy,
latency, and JSON-output conformance, and writes the results into the
Findings section of ``docs/specs/spike-gemma-intent-resolution.md``.

Throwaway. Read-only against the warehouse; does not touch production code
or data.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mcp_server.futureproof_server import FutureProofMCPServer  # noqa: E402

SPEC_PATH = PROJECT_ROOT / "docs" / "specs" / "spike-gemma-intent-resolution.md"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma4:e4b"
REQUEST_TIMEOUT = 120  # seconds

VIEW = "base_cip_soc_crosswalk"

SQL_CIP4_MENU = f"""
SELECT
    SUBSTR(cipcode, 1, 5) AS cip4,
    ANY_VALUE(cip_title) AS title
FROM {VIEW}
GROUP BY SUBSTR(cipcode, 1, 5)
ORDER BY cip4
"""


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

# Each entry: (id, bucket, input, expected_set, note)
# expected_set is a set of acceptable 4-digit CIP codes. The primary_cip
# returned by Gemma is "correct" if any acceptable code appears in either
# primary or alternatives.

TESTS: list[dict] = [
    # easy
    {"id": 1, "bucket": "easy", "input": "Marketing",
     "expected": {"52.14"}, "note": "direct match"},
    {"id": 2, "bucket": "easy", "input": "Accounting",
     "expected": {"52.03"}, "note": "direct match"},
    {"id": 3, "bucket": "easy", "input": "Computer Science",
     "expected": {"11.01", "11.07"}, "note": "11.07 is CS, 11.01 is CIS"},
    {"id": 4, "bucket": "easy", "input": "Nursing",
     "expected": {"51.38", "51.39"}, "note": "51.38 RN, 51.39 practical"},
    {"id": 5, "bucket": "easy", "input": "Mechanical Engineering",
     "expected": {"14.19"}, "note": "direct match"},
    # ambiguous
    {"id": 6, "bucket": "ambiguous", "input": "Sports Marketing",
     "expected": {"52.14", "31.05"}, "note": "marketing or rec/sports mgmt"},
    {"id": 7, "bucket": "ambiguous", "input": "Business Analytics",
     "expected": {"52.13", "52.12", "30.71", "30.70"},
     "note": "mgmt sci / MIS / data analytics"},
    {"id": 8, "bucket": "ambiguous", "input": "Pre-Med",
     "expected": {"26.01", "26.02", "51.11", "51.12", "51.38"},
     "note": "biology or health sciences prep"},
    {"id": 9, "bucket": "ambiguous", "input": "Data Science",
     "expected": {"11.04", "11.07", "27.05", "30.70", "30.71", "30.80"},
     "note": "CS / stats / data analytics"},
    {"id": 10, "bucket": "ambiguous", "input": "Communications",
     "expected": {"09.01", "09.04", "09.07", "09.09", "09.10"},
     "note": "communications family"},
    # fuzzy / misspelled
    {"id": 11, "bucket": "fuzzy", "input": "Mktg",
     "expected": {"52.14"}, "note": "abbreviation"},
    {"id": 12, "bucket": "fuzzy", "input": "Comp Sci",
     "expected": {"11.01", "11.07"}, "note": "abbreviation"},
    {"id": 13, "bucket": "fuzzy", "input": "Biz Admin",
     "expected": {"52.02"}, "note": "abbreviation"},
    {"id": 14, "bucket": "fuzzy", "input": "Psych",
     "expected": {"42.01", "42.27", "42.28"}, "note": "abbreviation"},
    # unusual
    {"id": 15, "bucket": "unusual", "input": "Underwater Basket Weaving",
     "expected": set(),
     "note": "no reasonable match; graceful degradation expected"},
    {"id": 16, "bucket": "unusual", "input": "AI and Machine Learning",
     "expected": {"11.01", "11.02", "11.04", "11.07", "14.09", "14.10",
                  "14.42", "27.05", "30.70"},
     "note": "CS / CE / stats"},
    {"id": 17, "bucket": "unusual", "input": "Sustainability Studies",
     "expected": {"03.01", "03.02", "03.03", "03.06", "30.33", "30.34",
                  "30.22"},
     "note": "natural resources / env / interdisciplinary"},
    {"id": 18, "bucket": "unusual", "input": "Game Design",
     "expected": {"50.04", "11.08", "11.09"},
     "note": "design / interactive / multimedia"},
    {"id": 19, "bucket": "unusual", "input": "Health Informatics",
     "expected": {"51.07", "51.27", "52.12", "11.04"},
     "note": "health admin / HIT / MIS"},
    {"id": 20, "bucket": "unusual", "input": "Sports Management",
     "expected": {"31.05", "52.09"},
     "note": "parks/rec/sports or hospitality mgmt"},
]


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------


def ollama_generate(prompt: str) -> tuple[str, float]:
    """Call Ollama and return (response_text, latency_seconds)."""
    body = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0, "num_ctx": 8192},
    }).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    dt = time.perf_counter() - t0
    return payload.get("response", ""), dt


# ---------------------------------------------------------------------------
# Prompting
# ---------------------------------------------------------------------------


def build_menu(rows: list[dict]) -> str:
    lines = []
    for r in rows:
        cip4 = r.get("cip4") or ""
        title = (r.get("title") or "").strip().rstrip(".")
        if not cip4:
            continue
        lines.append(f"{cip4}\t{title}")
    return "\n".join(lines)


PROMPT_TEMPLATE = """Given this list of academic program codes and descriptions (format: CIP4 TAB description):

{menu}

A student says their major is: "{test_input}"

Which CIP code best matches their stated major? If the major spans multiple programs, list up to 3 in order of relevance. Codes must be chosen from the list above and use the dotted 4-digit form (e.g. 52.14).

Respond with ONLY a JSON object on a single line, with no other text, no code fences, no commentary:
{{"primary_cip": "XX.XX", "reasoning": "one sentence", "alternatives": ["XX.XX", ...]}}
"""


JSON_RE = re.compile(r"\{.*\}", re.DOTALL)
CIP_RE = re.compile(r"\b(\d{2}\.\d{2})\b")


def parse_gemma_response(raw: str) -> dict:
    """Best-effort JSON parse; falls back to regex extraction."""
    text = raw.strip()
    # strip code fences if any
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    # try direct parse
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return _normalise(obj, raw, structured=True)
    except Exception:
        pass
    # try to locate first {...} block
    m = JSON_RE.search(text)
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict):
                return _normalise(obj, raw, structured=True)
        except Exception:
            pass
    # fall back — grab any CIP-looking tokens in order
    found = CIP_RE.findall(raw)
    primary = found[0] if found else ""
    return {
        "primary_cip": primary,
        "reasoning": "",
        "alternatives": found[1:4],
        "structured": False,
        "raw": raw,
    }


def _normalise(obj: dict, raw: str, *, structured: bool) -> dict:
    primary = str(obj.get("primary_cip") or "").strip()
    reasoning = str(obj.get("reasoning") or "").strip()
    alts_raw = obj.get("alternatives") or []
    if isinstance(alts_raw, str):
        alts_raw = [alts_raw]
    alts = [str(a).strip() for a in alts_raw if str(a).strip()]
    return {
        "primary_cip": primary,
        "reasoning": reasoning,
        "alternatives": alts,
        "structured": structured,
        "raw": raw,
    }


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def evaluate(test: dict, parsed: dict) -> dict:
    expected: set[str] = test["expected"]
    primary = parsed["primary_cip"]
    alts = parsed["alternatives"]
    candidates = [primary] + list(alts)

    if not expected:
        # "no match" test: correct iff primary is empty OR Gemma picks
        # something but flags uncertainty. We score generously: any
        # behaviour is acceptable, but we flag the call.
        correct = True
        primary_correct = True
        any_correct = True
    else:
        primary_correct = primary in expected
        any_correct = any(c in expected for c in candidates if c)
        correct = primary_correct or any_correct

    return {
        "primary_correct": primary_correct,
        "any_correct": any_correct,
        "correct": correct,
    }


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def render_detail_table(results: list[dict]) -> str:
    header = (
        "| # | Bucket | Input | Expected | Primary | Alternatives | "
        "Correct? | JSON? | Latency (s) |\n"
        "|---:|---|---|---|---|---|---|---|---:|"
    )
    lines = [header]
    for r in results:
        expected = ", ".join(sorted(r["test"]["expected"])) or "—"
        alts = ", ".join(r["parsed"]["alternatives"]) or "—"
        primary = r["parsed"]["primary_cip"] or "—"
        correct_sym = "✅" if r["eval"]["correct"] else "❌"
        if not r["test"]["expected"]:
            correct_sym = "➖"  # N/A bucket
        json_sym = "✅" if r["parsed"]["structured"] else "❌"
        title = r["test"]["input"].replace("|", "/")
        lines.append(
            f"| {r['test']['id']} | {r['test']['bucket']} | {title} "
            f"| {expected} | {primary} | {alts} | {correct_sym} "
            f"| {json_sym} | {r['latency']:.2f} |"
        )
    return "\n".join(lines)


def render_reasoning_block(results: list[dict]) -> str:
    lines = []
    for r in results:
        reasoning = r["parsed"]["reasoning"] or "_(none)_"
        lines.append(
            f"- **#{r['test']['id']} {r['test']['input']}** → "
            f"`{r['parsed']['primary_cip'] or '—'}`: {reasoning}"
        )
    return "\n".join(lines)


def bucket_accuracy(results: list[dict], bucket: str) -> tuple[int, int, float]:
    rows = [r for r in results if r["test"]["bucket"] == bucket]
    if not rows:
        return 0, 0, 0.0
    # skip the "no-match" unusual case from the denominator
    scored = [r for r in rows if r["test"]["expected"]]
    if not scored:
        return 0, 0, 0.0
    correct = sum(1 for r in scored if r["eval"]["correct"])
    return correct, len(scored), correct / len(scored) * 100


# ---------------------------------------------------------------------------
# Spec-file update
# ---------------------------------------------------------------------------


def update_findings(markdown_block: str) -> None:
    text = SPEC_PATH.read_text()
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


def run() -> int:
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

    # quick reachability ping
    print("Pinging Ollama …", file=sys.stderr)
    try:
        _, ping_dt = ollama_generate("Say 'ready' in one word.")
        print(f"  OK ({ping_dt:.2f}s)", file=sys.stderr)
    except urllib.error.URLError as exc:
        print(f"Ollama unreachable: {exc}", file=sys.stderr)
        return 2

    results: list[dict] = []
    for test in TESTS:
        prompt = PROMPT_TEMPLATE.format(menu=menu, test_input=test["input"])
        print(
            f"[{test['id']:>2}] {test['bucket']:<9} {test['input']!r} …",
            file=sys.stderr,
        )
        try:
            raw, dt = ollama_generate(prompt)
        except Exception as exc:
            print(f"    ERROR: {exc}", file=sys.stderr)
            results.append({
                "test": test,
                "parsed": {
                    "primary_cip": "",
                    "reasoning": f"ERROR: {exc}",
                    "alternatives": [],
                    "structured": False,
                    "raw": "",
                },
                "eval": {"primary_correct": False, "any_correct": False,
                         "correct": False},
                "latency": 0.0,
            })
            continue

        parsed = parse_gemma_response(raw)
        ev = evaluate(test, parsed)
        correct_mark = "OK " if ev["correct"] else "MISS"
        json_mark = "json" if parsed["structured"] else "nojson"
        print(
            f"    {correct_mark} {json_mark}  primary={parsed['primary_cip'] or '—':<6}"
            f" alts={parsed['alternatives']} ({dt:.2f}s)",
            file=sys.stderr,
        )
        results.append({
            "test": test,
            "parsed": parsed,
            "eval": ev,
            "latency": dt,
        })

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

    # ------------------------------------------------------------------
    # Markdown
    # ------------------------------------------------------------------
    blocks: list[str] = []
    blocks.append(
        "_Generated by `scripts/spike_gemma_intent.py` against local "
        f"Ollama `{MODEL}` and `base.cip_soc_crosswalk`._\n"
    )
    blocks.append("### 1. Setup\n")
    blocks.append(
        f"- **Model:** `{MODEL}` via Ollama at `{OLLAMA_URL}`\n"
        f"- **Menu:** {len(menu_rows)} 4-digit CIP prefixes "
        f"(≈{len(menu)} chars of prompt context)\n"
        f"- **Test cases:** {len(TESTS)} "
        f"(5 easy, 5 ambiguous, 4 fuzzy, 6 unusual)\n"
        f"- **Decoding:** temperature 0, JSON-only response contract\n"
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

    blocks.append("### 5. Latency & Output Conformance\n")
    blocks.append(
        f"- **Average latency:** {avg_latency:.2f}s per call\n"
        f"- **Min / max:** {min_latency:.2f}s / {max_latency:.2f}s\n"
        f"- **JSON-valid responses:** {n_json_ok}/{len(results)}\n"
    )

    blocks.append("### 6. Assessment\n")

    verdict_lines: list[str] = []
    if easy_pct >= 90:
        verdict_lines.append(
            f"- **Easy cases ({easy_pct:.0f}%):** reliable — direct name "
            "matches are solved by the model without trouble."
        )
    elif easy_pct >= 70:
        verdict_lines.append(
            f"- **Easy cases ({easy_pct:.0f}%):** mostly reliable, with "
            "occasional slips even on unambiguous inputs. Not safe as a "
            "drop-in replacement for the curated YAML."
        )
    else:
        verdict_lines.append(
            f"- **Easy cases ({easy_pct:.0f}%):** unreliable. If the "
            "model cannot nail direct matches it is not a candidate for "
            "production intent resolution."
        )

    if amb_pct >= 80:
        verdict_lines.append(
            f"- **Ambiguous cases ({amb_pct:.0f}%):** strong reasoning; "
            "the model makes sensible cross-family calls."
        )
    elif amb_pct >= 50:
        verdict_lines.append(
            f"- **Ambiguous cases ({amb_pct:.0f}%):** partial; acceptable "
            "as a suggestion surface but needs a human-in-the-loop "
            "confirmation step for borderline majors."
        )
    else:
        verdict_lines.append(
            f"- **Ambiguous cases ({amb_pct:.0f}%):** weak. The model "
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
            f"- **Unusual/long-tail ({unu_pct:.0f}%):** the model offers "
            "real value on the inputs a static table can never cover."
        )
    else:
        verdict_lines.append(
            f"- **Unusual/long-tail ({unu_pct:.0f}%):** the model's "
            "long-tail coverage is limited; async review is required."
        )

    if avg_latency < 1.5:
        verdict_lines.append(
            f"- **Latency ({avg_latency:.2f}s avg):** acceptable for "
            "query-time fallback."
        )
    elif avg_latency < 5.0:
        verdict_lines.append(
            f"- **Latency ({avg_latency:.2f}s avg):** borderline for "
            "query-time — usable as an opt-in, but async resolution is "
            "safer for the default path."
        )
    else:
        verdict_lines.append(
            f"- **Latency ({avg_latency:.2f}s avg):** too slow for "
            "synchronous query-time use; unmatched majors should be "
            "queued for async resolution."
        )

    if n_json_ok == len(results):
        verdict_lines.append(
            "- **Structured output:** every call returned valid JSON; the "
            "contract holds."
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
            "constrained decoding (grammar / response_format)."
        )

    blocks.extend(verdict_lines)
    blocks.append("")

    blocks.append("#### Verdict\n")
    blocks.append(
        "The YAML lookup remains the primary path for head-of-distribution "
        f"majors. Gemma (`{MODEL}`) is "
        + (
            "a viable fallback for the long tail"
            if total_pct >= 60
            else "not yet reliable enough to stand in as a fallback"
        )
        + f" (overall accuracy {total_pct:.0f}%, avg latency "
        f"{avg_latency:.2f}s). "
        + (
            "Latency is acceptable for query-time use when the YAML misses."
            if avg_latency < 1.5
            else (
                "At this latency, unmatched majors should be queued for "
                "async resolution rather than blocked on a synchronous call."
            )
        )
    )
    blocks.append("")

    markdown = "\n".join(blocks)
    update_findings(markdown)
    print(f"\nWrote findings to {SPEC_PATH}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    import traceback

    try:
        sys.exit(run())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
