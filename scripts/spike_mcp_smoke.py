#!/usr/bin/env python
"""Throwaway MCP smoke test — verifies all 8 domain handlers return real data.

Read-only diagnostic. Do not commit to long-term scripts.
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

# Mirror conftest / serve_mcp bootstrap
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mcp_server.futureproof_server import FutureProofMCPServer  # noqa: E402


def banner(label: str) -> None:
    print(f"\n=== {label} ===")


def dump(obj, max_chars: int = 800) -> None:
    s = json.dumps(obj, indent=2, default=str)
    if len(s) > max_chars:
        s = s[:max_chars] + "\n  …(truncated)"
    print(s)


def run() -> int:
    server = FutureProofMCPServer(
        warehouse_path=str(PROJECT_ROOT / "data" / "warehouse"),
        catalog_path=str(PROJECT_ROOT / "data" / "catalog" / "catalog.db"),
        server_name="futureproof",
    )

    # --- get_school_programs ---
    banner("get_school_programs(school_name='Indiana State')")
    sp = server._handle_get_school_programs({"school_name": "Indiana State"})
    programs = sp.get("programs") or sp.get("data") or []
    print(f"programs returned: {len(programs)}")
    for p in programs[:3]:
        name = p.get("program_name") or p.get("cip_title") or p.get("name")
        earnings = p.get("earnings_1yr_median")
        print(f"  - {name} | earnings_1yr_median={earnings}")
    has_earnings_any = any(p.get("earnings_1yr_median") is not None for p in programs)
    print(f"earnings data present anywhere: {has_earnings_any}")
    if not programs:
        print("STOP: no programs returned — cannot continue chained probes")
        dump(sp)
        return 1

    first = programs[0]
    unitid = first.get("unitid")
    cipcode = first.get("cipcode")
    print(f"first program unitid={unitid} cipcode={cipcode}")

    # --- get_career_paths ---
    banner(f"get_career_paths(unitid={unitid}, cipcode={cipcode})")
    cp = server._handle_get_career_paths({"unitid": unitid, "cipcode": cipcode})
    paths = cp.get("career_paths") or cp.get("paths") or cp.get("data") or []
    print(f"career paths returned: {len(paths)}")
    for p in paths[:3]:
        title = p.get("occupation_title") or p.get("title") or p.get("soc_title")
        print(f"  - {title}")
    if paths:
        first_path = paths[0]
        non_null_keys = [k for k, v in first_path.items() if v is not None]
        stat_keys = [k for k in non_null_keys if any(tok in k.lower() for tok in ("wage", "earning", "growth", "employ", "median", "stat"))]
        boss_keys = [k for k in non_null_keys if "boss" in k.lower() or "score" in k.lower() or "exposure" in k.lower()]
        print(f"non-null stat-ish fields: {stat_keys}")
        print(f"non-null boss/score fields: {boss_keys}")
    else:
        print("STOP: no career paths — skipping SOC-keyed probes")
        dump(cp)
        return 1

    soc_code = paths[0].get("soc_code") or paths[0].get("soc")
    print(f"first career path soc_code={soc_code}")

    # --- get_occupation_data ---
    banner(f"get_occupation_data(soc_code={soc_code})")
    od = server._handle_get_occupation_data({"soc_code": soc_code})
    print(f"top-level keys: {list(od.keys())}")
    data = od.get("data") if isinstance(od.get("data"), dict) else od
    wage = (
        data.get("median_annual_wage")
        or data.get("median_wage")
        or data.get("wage")
    )
    growth = (
        data.get("growth_category")
        or data.get("growth_outlook")
        or data.get("growth")
    )
    print(f"wage={wage} growth={growth}")
    if wage is None and growth is None:
        dump(od, max_chars=600)

    # --- get_task_breakdown ---
    banner(f"get_task_breakdown(soc_code={soc_code})")
    tb = server._handle_get_task_breakdown({"soc_code": soc_code})
    print(f"top-level keys: {list(tb.keys())}")
    tb_data = tb.get("data") if isinstance(tb.get("data"), dict) else tb
    activities = (
        tb_data.get("activities")
        or tb_data.get("tasks")
        or tb_data.get("work_activities")
        or tb_data.get("top_activities")
        or tb_data.get("top_tasks")
        or []
    )
    if isinstance(activities, dict):
        # sometimes a mapping — take items
        activities = [{"name": k, **(v if isinstance(v, dict) else {"value": v})} for k, v in activities.items()]
    print(f"activities returned: {len(activities) if hasattr(activities, '__len__') else 'n/a'}")
    if isinstance(activities, list):
        for a in activities[:2]:
            if isinstance(a, dict):
                label = a.get("activity") or a.get("task") or a.get("name") or a.get("title") or a.get("statement")
                importance = a.get("importance") or a.get("score") or a.get("relevance")
                print(f"  - {label} (importance={importance})")
            else:
                print(f"  - {a}")
    else:
        dump(tb, max_chars=600)

    # --- get_ai_exposure ---
    banner(f"get_ai_exposure(soc_code={soc_code})")
    ae = server._handle_get_ai_exposure({"soc_code": soc_code})
    print(f"exposure_score={ae.get('exposure_score')}")
    rationale = ae.get("rationale")
    if rationale and len(str(rationale)) > 200:
        rationale = str(rationale)[:200] + "…"
    print(f"rationale={rationale}")

    # --- get_career_branches ---
    banner(f"get_career_branches(soc_code={soc_code})")
    cb = server._handle_get_career_branches({"soc_code": soc_code})
    branches = cb.get("branches") or cb.get("career_branches") or cb.get("data") or []
    print(f"branches returned: {len(branches)}")
    for b in branches[:2]:
        if isinstance(b, dict):
            title = b.get("occupation_title") or b.get("title") or b.get("related_title")
            print(f"  - {title}")
        else:
            print(f"  - {b}")

    # --- get_regional_price_parity ---
    banner("get_regional_price_parity(state='IN')")
    rpp = server._handle_get_regional_price_parity({"state": "IN"})
    print(f"rpp_all_items={rpp.get('rpp_all_items')}")
    print(f"adjusted_50k={rpp.get('adjusted_50k')}")

    # --- compare_purchasing_power ---
    banner("compare_purchasing_power(salary=48000, IN vs CA)")
    cpp = server._handle_compare_purchasing_power(
        {"salary": 48000, "state_a": "IN", "state_b": "CA"}
    )
    print(f"IN adjusted: {cpp.get('state_a_adjusted') or cpp.get('adjusted_a')}")
    print(f"CA adjusted: {cpp.get('state_b_adjusted') or cpp.get('adjusted_b')}")
    dump(cpp, max_chars=400)

    print("\n=== ALL PROBES COMPLETED ===")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(run())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
