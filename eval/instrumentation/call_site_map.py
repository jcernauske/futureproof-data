"""Map production ``call_site`` strings to canonical eval surfaces.

Production tags every Gemma call with ``extra["call_site"]`` and logs to
``logs/gemma.jsonl``. The eval harness reads those logs to compute latency
distributions. Some surfaces have multiple call_site values (ask_gemma_chat
streams through ~10 distinct branch handlers); this module collapses them
to one canonical surface name.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any


# Canonical surface → all production call_site values that count as that surface.
# Surfaces are listed in the order they appear in docs/specs/gemma-eval-harness.md §1.
SURFACE_TO_CALL_SITES: dict[str, set[str]] = {
    # --- P0 ---
    "ask_gemma_chat": {
        "ask_gemma_branch_opener",
        "ask_gemma_branch",
        "ask_gemma_stat",
        "ask_gemma_boss",
        "ask_gemma_compare",
        "ask_gemma_career",
        "ask_gemma_build",
        "ask_gemma_stream_branch_opener",
        "ask_gemma_stream_branch",
        "ask_gemma_stream_build",
        "ask_gemma_stream_stat",
        "ask_gemma_stream_compare",
        "ask_gemma_stream_career",
        "ask_gemma_stream_skill",
        "ask_gemma_stream_boss",
    },
    "career_intent": {
        "intent_resolve",
        "intent_audit",
    },
    "chip": {
        "chip_dispatch_tool_call",
    },
    "explain_ern": {
        "explain_ern_receipt",
        "explain_ern_missing_receipt",
        "explain_ern_receipt_deterministic",
        "explain_stat_short_circuit",
    },
    "explain_roi": {
        "explain_roi_receipt",
        "explain_roi_receipt_deterministic",
    },
    "explain_res": {
        "explain_res_receipt",
        "explain_res_receipt_deterministic",
    },
    "explain_grw": {
        "explain_grw_receipt",
        "explain_grw_receipt_deterministic",
    },
    "explain_aura": {
        "explain_aura_receipt",
        "explain_aura_receipt_deterministic",
    },
    # --- P1 ---
    "boss_narrative": {"boss_narrative"},
    "career_tiering": {"career_tiering"},
    "career_description": {"career_description"},
    "next_steps": {"next_steps"},
    "guidance": {"guidance"},
    # --- P2 ---
    "skill_pool": {"skill_pool"},
    "skill_recs": {"skill_recs"},
    "reroll_commentary": {"reroll_commentary"},
    "career_pick_qna": {"career_pick.ask"},
    "initial_major_resolution": {
        "set_your_course_resolve",
        "set_your_course_fallback_resolve",
    },
    "pdf_questions": {"pdf_questions"},
    "soc_expansion": {"soc_expansion"},
    "compare": {
        "compare_summary",
        "compare_pros_cons",
        "compare_money_insight",
    },
}


# Inverted map for fast lookup. Built at module load.
CALL_SITE_TO_SURFACE: dict[str, str] = {
    call_site: surface
    for surface, call_sites in SURFACE_TO_CALL_SITES.items()
    for call_site in call_sites
}


def canonical_surface(call_site: str) -> str | None:
    """Return the canonical surface name for a production call_site, or None
    if the call_site is unrecognized (e.g., ``warmup`` or untagged calls)."""
    return CALL_SITE_TO_SURFACE.get(call_site)


def iter_log_records(log_path: Path) -> Iterator[dict[str, Any]]:
    """Stream JSONL records from logs/gemma.jsonl. Skips blank lines and
    malformed records — production has both."""
    with log_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def latency_for_surface(
    log_path: Path,
    surface: str,
    since_iso: str | None = None,
) -> list[int]:
    """Return all duration_ms values for a given surface from the log.

    Skips synthetic records (``synthetic: true``) — those are written by
    ``log_synthetic_event`` for non-call observability (parse-success flags,
    fallback markers) and have no latency. Counting them in a latency
    distribution would silently include zero / null values, undercounting
    real latency.

    ``since_iso`` filters to records with ``ts >= since_iso`` so callers can
    isolate one eval run's records from the full production history.
    """
    call_sites = SURFACE_TO_CALL_SITES.get(surface, set())
    if not call_sites:
        return []
    out: list[int] = []
    for rec in iter_log_records(log_path):
        if rec.get("call_site") not in call_sites:
            continue
        if rec.get("synthetic") is True:
            continue
        if since_iso is not None and rec.get("ts", "") < since_iso:
            continue
        duration = rec.get("duration_ms")
        if isinstance(duration, int):
            out.append(duration)
    return out
