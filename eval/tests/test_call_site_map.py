"""Verify the call_site → surface map is complete and consistent."""

from __future__ import annotations

import json
from pathlib import Path

from eval.instrumentation.call_site_map import (
    CALL_SITE_TO_SURFACE,
    SURFACE_TO_CALL_SITES,
    canonical_surface,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = REPO_ROOT / "logs" / "gemma.jsonl"


def test_no_duplicate_call_sites() -> None:
    """A given call_site string maps to exactly one surface."""
    seen: dict[str, str] = {}
    for surface, sites in SURFACE_TO_CALL_SITES.items():
        for site in sites:
            assert site not in seen, (
                f"call_site {site!r} maps to both {seen[site]!r} and {surface!r}"
            )
            seen[site] = surface


def test_canonical_surface_lookup() -> None:
    assert canonical_surface("explain_ern_receipt") == "explain_ern"
    assert canonical_surface("ask_gemma_branch_opener") == "ask_gemma_chat"
    assert canonical_surface("nonsense_call_site") is None


def test_inverted_map_matches_forward_map() -> None:
    for surface, sites in SURFACE_TO_CALL_SITES.items():
        for site in sites:
            assert CALL_SITE_TO_SURFACE[site] == surface


def test_known_production_call_sites_covered() -> None:
    """If logs/gemma.jsonl exists, every call_site in it that we expect to
    be covered IS covered. We only check known production-tagged sites —
    not 'UNTAGGED' / 'warmup' rows."""
    if not LOG_PATH.exists():
        return  # skip when log isn't available

    seen_call_sites: set[str] = set()
    with LOG_PATH.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            site = rec.get("call_site")
            if site:
                seen_call_sites.add(site)

    expected_covered = {
        "explain_ern_receipt",
        "explain_roi_receipt",
        "explain_res_receipt",
        "explain_grw_receipt",
        "explain_aura_receipt",
        "set_your_course_resolve",
        "chip_dispatch_tool_call",
        "ask_gemma_branch_opener",
        "boss_narrative",
        "career_description",
        "soc_expansion",
    }
    missing_from_map = expected_covered - set(CALL_SITE_TO_SURFACE)
    assert not missing_from_map, (
        f"Production call_sites not in the surface map: {missing_from_map}"
    )
