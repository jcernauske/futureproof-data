#!/usr/bin/env python3
"""Test gemma4:e2b on Spanish and Arabic prompts.

Pulls real prompts from logs/gemma.jsonl that previously ran on e4b/26b,
replays them through e2b, and writes a side-by-side comparison.

Usage:
    uv run python scripts/spike_e2b_multilingual.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = PROJECT_ROOT / "logs" / "gemma.jsonl"
_safe_tag = os.environ.get("TEST_MODEL", "gemma4:e2b").replace(":", "-").replace("/", "-")
OUT_PATH = PROJECT_ROOT / "reports" / f"spike_multilingual_{_safe_tag}_results.json"

OLLAMA_URL = os.environ.get("OLLAMA_NATIVE_URL", "http://127.0.0.1:11434")
E2B_MODEL = os.environ.get("TEST_MODEL", "gemma4:e2b")

# Surfaces we care about for student-facing prose quality
TARGET_SITES = {
    "boss_narrative",
    "career_description",
    "guidance",
    "set_your_course_resolve",
    "skill_pool",
    "skill_recs",
}

SAMPLES_PER_LANG = 3  # 3 Spanish + 3 Arabic = 6 e2b calls


def detect_language(blob: str) -> str | None:
    if re.search(r"[؀-ۿ]", blob):
        return "ar"
    if re.search(r"[¿¡ñáéíóú]", blob) and re.search(
        r"\b(que|para|tu|tus|carrera|estudios|trabajo|salario|cómo|hacia)\b",
        blob,
        re.I,
    ):
        return "es"
    return None


def text_blob(record: dict[str, Any]) -> str:
    blob = record.get("response") or ""
    msgs = record.get("messages") or []
    if isinstance(msgs, list):
        for m in msgs:
            if isinstance(m, dict):
                c = m.get("content", "")
                if isinstance(c, str):
                    blob += "\n" + c
    return blob


def collect_samples() -> dict[str, list[dict[str, Any]]]:
    by_lang_site: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            site = d.get("call_site") or ""
            if site not in TARGET_SITES:
                continue
            msgs = d.get("messages") or []
            if not msgs:
                continue
            lang = detect_language(text_blob(d))
            if lang is None:
                continue
            by_lang_site[(lang, site)].append(d)

    sampled: dict[str, list[dict[str, Any]]] = {"es": [], "ar": []}
    for lang in ("es", "ar"):
        site_records = [(s, by_lang_site.get((lang, s), [])) for s in TARGET_SITES]
        site_records = [(s, recs) for s, recs in site_records if recs]
        # Prefer diversity of sites
        for site, recs in site_records:
            if len(sampled[lang]) >= SAMPLES_PER_LANG:
                break
            sampled[lang].append(recs[0])
    return sampled


def post_ollama(payload: dict[str, Any], timeout_s: float = 120.0) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def replay(record: dict[str, Any]) -> dict[str, Any]:
    msgs = record.get("messages") or []
    options = {
        "temperature": record.get("temperature", 0.7),
        "num_predict": record.get("max_tokens", 600),
    }
    payload: dict[str, Any] = {
        "model": E2B_MODEL,
        "messages": msgs,
        "stream": False,
        "think": False,
        "options": options,
    }
    started = time.perf_counter()
    try:
        response = post_ollama(payload)
        duration_ms = int((time.perf_counter() - started) * 1000)
        text = (response.get("message") or {}).get("content") or ""
        return {"ok": True, "duration_ms": duration_ms, "response": text}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "error": f"{type(exc).__name__}: {exc}",
            "response": "",
        }


def voice_violations(text: str) -> list[str]:
    v = []
    if re.search(r"\b(ERN|ROI|RES|GRW|AURA)\b", text):
        v.append("stat_code")
    if re.search(r"\b(boss fight|gauntlet|HP|XP|level up)\b", text, re.I):
        v.append("en_game_framing")
    if re.search(r"[٠-٩۰-۹]", text):
        v.append("non_western_numerals")
    return v


def lang_purity(text: str, target: str) -> float:
    if target == "ar":
        arabic = len(re.findall(r"[؀-ۿ]", text))
        latin = len(re.findall(r"[a-zA-Z]", text))
        total = arabic + latin
        return (arabic / total) if total else 0.0
    if target == "es":
        # crude: presence of Spanish accents/punct + Spanish stopwords
        es_markers = len(re.findall(r"[¿¡ñáéíóú]", text))
        # also count spanish stopwords
        es_words = len(
            re.findall(
                r"\b(que|para|tu|tus|carrera|estudios|trabajo|salario|cómo|hacia|el|la|los|las|de|en|con|por)\b",
                text,
                re.I,
            )
        )
        # rough proxy: if any spanish markers found AND words present, return 1.0
        return 1.0 if (es_markers > 0 and es_words > 3) else 0.0
    return 0.0


def main() -> int:
    if not LOG_PATH.exists():
        print(f"No log at {LOG_PATH}", file=sys.stderr)
        return 1

    samples = collect_samples()
    print(f"Sampled {len(samples['es'])} Spanish + {len(samples['ar'])} Arabic prompts")

    results: list[dict[str, Any]] = []
    for lang, records in samples.items():
        for record in records:
            site = record.get("call_site") or "?"
            original_model = record.get("model") or "?"
            original_backend = record.get("backend") or "?"
            original_response = record.get("response") or ""
            print(f"\n[{lang}] site={site}  original={original_backend}/{original_model}")
            e2b = replay(record)
            print(f"    e2b status={'ok' if e2b['ok'] else 'FAIL'} duration={e2b['duration_ms']}ms")
            if not e2b["ok"]:
                print(f"    error: {e2b.get('error')}")

            e2b_resp = e2b.get("response", "")
            purity = lang_purity(e2b_resp, lang)
            violations = voice_violations(e2b_resp)

            print(f"    lang_purity={purity:.2f}  voice_violations={violations}")
            print(f"    e2b excerpt: {e2b_resp[:160]!r}")
            print(f"    orig excerpt: {original_response[:160]!r}")

            results.append({
                "lang": lang,
                "call_site": site,
                "original_backend": original_backend,
                "original_model": original_model,
                "original_response": original_response,
                "e2b_ok": e2b["ok"],
                "e2b_duration_ms": e2b["duration_ms"],
                "e2b_response": e2b_resp,
                "e2b_error": e2b.get("error"),
                "e2b_lang_purity": purity,
                "e2b_voice_violations": violations,
                "e2b_response_length": len(e2b_resp),
                "original_response_length": len(original_response),
            })

    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {OUT_PATH}")

    print("\n=== Summary ===")
    for lang in ("es", "ar"):
        lang_results = [r for r in results if r["lang"] == lang]
        if not lang_results:
            continue
        ok = sum(1 for r in lang_results if r["e2b_ok"])
        purity_avg = sum(r["e2b_lang_purity"] for r in lang_results) / len(lang_results)
        violations_total = sum(len(r["e2b_voice_violations"]) for r in lang_results)
        avg_len = sum(r["e2b_response_length"] for r in lang_results) / len(lang_results)
        avg_dur = sum(r["e2b_duration_ms"] for r in lang_results) / len(lang_results)
        print(
            f"{lang}: {ok}/{len(lang_results)} ok  "
            f"avg purity={purity_avg:.2f}  "
            f"violations={violations_total}  "
            f"avg len={avg_len:.0f} chars  "
            f"avg dur={avg_dur:.0f}ms"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
