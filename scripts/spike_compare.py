#!/usr/bin/env python
"""Throwaway head-to-head: Illinois State Marketing vs IU-Bloomington Marketing.

Product simulation — shows exactly what the MCP tool surface returns for a
two-school, single-major comparison. No editorializing, no Gemma-style
narration; just the raw data side-by-side.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mcp_server.futureproof_server import FutureProofMCPServer  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

STAT_FIELDS = ("stat_ern", "stat_roi", "stat_res", "stat_grw", "stat_hmn")
BOSS_FIELDS = (
    "boss_ai_score",
    "boss_loans_score",
    "boss_market_score",
    "boss_burnout_score",
    "boss_ceiling_score",
)


def banner(label: str, char: str = "=") -> None:
    bar = char * 78
    print(f"\n{bar}\n{label}\n{bar}")


def fmt(v, width: int = 10) -> str:
    if v is None:
        return "—".rjust(width)
    if isinstance(v, float):
        if abs(v) >= 1000:
            return f"{v:,.0f}".rjust(width)
        return f"{v:.2f}".rjust(width)
    if isinstance(v, int):
        return f"{v:,}".rjust(width)
    return str(v).rjust(width)


def find_marketing_program(programs: list[dict]) -> tuple[dict | None, str]:
    """Pick the Marketing program.

    Returns (program, match_quality) where match_quality is one of:
      - "exact"  — CIP 52.14xx (Marketing cluster)
      - "name"   — program_name contains "marketing" (non-52.14 CIP)
      - "fallback_business" — no marketing; using 52.01 Business/Commerce
      - "none"   — no business-family program at all
    """
    for p in programs:
        cip = str(p.get("cipcode") or "")
        if cip.startswith("52.14"):
            return p, "exact"
    for p in programs:
        name = (p.get("program_name") or "").lower()
        if "marketing" in name:
            return p, "name"
    # Fallback: closest available match in the Business cluster (52.01).
    for p in programs:
        cip = str(p.get("cipcode") or "")
        if cip.startswith("52.01"):
            return p, "fallback_business"
    return None, "none"


def program_summary(p: dict) -> None:
    print(f"  unitid:            {p.get('unitid')}")
    print(f"  institution_name:  {p.get('institution_name')}")
    print(f"  cipcode:           {p.get('cipcode')}")
    print(f"  program_name:      {p.get('program_name')}")
    print(f"  earnings_1yr_med:  {fmt(p.get('earnings_1yr_median'))}")
    print(f"  earnings_1yr_p25:  {fmt(p.get('earnings_1yr_p25'))}")
    print(f"  earnings_1yr_p75:  {fmt(p.get('earnings_1yr_p75'))}")
    print(f"  debt_median:       {fmt(p.get('debt_median'))}")
    print(f"  debt_to_earnings:  {fmt(p.get('debt_to_earnings_annual'))}")
    print(f"  confidence_tier:   {p.get('confidence_tier')}")
    print(f"  program_value_idx: {fmt(p.get('program_value_index'))}")


def career_paths_table(label: str, paths: list[dict]) -> None:
    print(f"\n{label}  ({len(paths)} paths)")
    header = (
        f"  {'soc':>8}  {'title':<42}  "
        + "  ".join(f"{f[5:]:>4}" for f in STAT_FIELDS)
        + "  |  "
        + "  ".join(f"{f.replace('boss_','').replace('_score','')[:6]:>6}" for f in BOSS_FIELDS)
    )
    print(header)
    print("  " + "-" * (len(header) - 2))
    for p in paths:
        title = (p.get("occupation_title") or "")[:42]
        soc = p.get("soc_code") or ""
        stats = "  ".join(fmt(p.get(f), 4) for f in STAT_FIELDS)
        bosses = "  ".join(fmt(p.get(f), 6) for f in BOSS_FIELDS)
        print(f"  {soc:>8}  {title:<42}  {stats}  |  {bosses}")


def pick_overlap(
    paths_a: list[dict], paths_b: list[dict]
) -> tuple[set[str], str | None]:
    socs_a = {p.get("soc_code") for p in paths_a if p.get("soc_code")}
    socs_b = {p.get("soc_code") for p in paths_b if p.get("soc_code")}
    overlap = socs_a & socs_b
    # Prefer Marketing Manager (11-2021) if present
    if "11-2021" in overlap:
        return overlap, "11-2021"
    # Otherwise pick whichever overlapping SOC has the highest stat_ern in A
    by_soc_a = {p.get("soc_code"): p for p in paths_a}
    best_soc = None
    best_ern = -1
    for soc in overlap:
        ern = by_soc_a[soc].get("stat_ern")
        if isinstance(ern, (int, float)) and ern > best_ern:
            best_ern = ern
            best_soc = soc
    return overlap, best_soc


def side_by_side_stats(
    label_a: str,
    path_a: dict | None,
    label_b: str,
    path_b: dict | None,
) -> None:
    print(f"\n{'field':<24}  {label_a:>14}  {label_b:>14}  {'winner':>10}")
    print("  " + "-" * 68)
    rows = list(STAT_FIELDS) + list(BOSS_FIELDS)
    for field in rows:
        va = path_a.get(field) if path_a else None
        vb = path_b.get(field) if path_b else None
        winner = "—"
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            if va > vb:
                winner = label_a
            elif vb > va:
                winner = label_b
            else:
                winner = "tie"
        print(f"{field:<24}  {fmt(va, 14)}  {fmt(vb, 14)}  {winner:>10}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run() -> int:
    server = FutureProofMCPServer(
        warehouse_path=str(PROJECT_ROOT / "data" / "warehouse"),
        catalog_path=str(PROJECT_ROOT / "data" / "catalog" / "catalog.db"),
        server_name="futureproof",
    )

    schools = [
        ("A", "Illinois State", "IL"),
        ("B", "Indiana University-Bloomington", "IN"),
    ]

    banner("PROGRAM LOOKUP")
    picked: dict[str, dict] = {}
    match_quality: dict[str, str] = {}
    for tag, name, _state in schools:
        resp = server._handle_get_school_programs({"school_name": name})
        programs = resp.get("data") or []
        print(f"\n[{tag}] {name} — {len(programs)} programs returned")
        prog, quality = find_marketing_program(programs)
        if prog is None:
            print(f"  NO MARKETING OR BUSINESS PROGRAM FOUND — giving up")
            return 1
        if quality == "exact":
            print("  match: EXACT (CIP 52.14 Marketing)")
        elif quality == "name":
            print(f"  match: NAME (program name contains 'marketing')")
        elif quality == "fallback_business":
            print(
                "  match: FALLBACK — no standalone Marketing program in "
                "College Scorecard for this school; using closest available "
                "match (CIP 52.01 Business/Commerce, General). Comparison is "
                "NOT strictly apples-to-apples."
            )
        picked[tag] = prog
        match_quality[tag] = quality
        program_summary(prog)

    banner("CAREER PATHS")
    paths: dict[str, list[dict]] = {}
    for tag, name, _state in schools:
        prog = picked[tag]
        resp = server._handle_get_career_paths(
            {"unitid": prog["unitid"], "cipcode": prog["cipcode"]}
        )
        rows = resp.get("data") or []
        paths[tag] = rows
        label = f"[{tag}] {name} — {prog.get('program_name')}"
        career_paths_table(label, rows)

    banner("OVERLAP ANALYSIS")
    overlap, chosen_soc = pick_overlap(paths["A"], paths["B"])
    print(f"Shared SOC codes: {sorted(overlap)}")
    if chosen_soc is None:
        print("NO OVERLAPPING CAREER PATHS — cannot continue SOC-keyed probes")
        return 1
    print(f"Chosen SOC for deep dive: {chosen_soc}")

    path_a = next((p for p in paths["A"] if p.get("soc_code") == chosen_soc), None)
    path_b = next((p for p in paths["B"] if p.get("soc_code") == chosen_soc), None)
    title = (path_a or path_b or {}).get("occupation_title", "")
    print(f"Occupation: {title}")

    banner(f"HEAD-TO-HEAD: {title} ({chosen_soc})")
    side_by_side_stats("ISU", path_a, "IU-B", path_b)

    banner(f"OCCUPATION DATA — {chosen_soc}")
    od = server._handle_get_occupation_data({"soc_code": chosen_soc}).get("data") or {}
    print(f"  occupation_title:   {od.get('occupation_title')}")
    print(f"  soc_major_group:    {od.get('soc_major_group_name')}")
    print(f"  median_annual_wage: {fmt(od.get('median_annual_wage'))}")
    print(f"  wage_tier:          {od.get('wage_tier')}")
    print(f"  growth_category:    {od.get('growth_category')}")
    print(f"  employment_current: {fmt(od.get('employment_current'))}")
    print(f"  employment_proj:    {fmt(od.get('employment_projected'))}")
    print(f"  employment_chg_pct: {fmt(od.get('employment_change_pct'))}")
    print(f"  openings_annual:    {fmt(od.get('openings_annual_avg'))}")
    print(f"  education_level:    {od.get('education_level_name')}")

    banner(f"TASK BREAKDOWN — {chosen_soc}")
    tb = server._handle_get_task_breakdown({"soc_code": chosen_soc}).get("data") or {}
    print(f"  primary_title:         {tb.get('primary_title')}")
    print(f"  hmn_score:             {fmt(tb.get('hmn_score'))}   (human edge, 1-10)")
    print(f"  burnout_score:         {fmt(tb.get('burnout_score'))}")
    print(f"  activity_importance_μ: {fmt(tb.get('activity_importance_mean'))}")
    print(f"  time_pressure:         {fmt(tb.get('time_pressure'))}")
    print(f"  consequence_of_error:  {fmt(tb.get('consequence_of_error'))}")

    print("\n  Top 5 activities (all):")
    for a in tb.get("top_5_activities") or []:
        print(f"    - {a.get('activity'):<60}  importance={a.get('importance')}")
    print("\n  Top human-edge activities:")
    for a in tb.get("top_human_activities") or []:
        print(f"    - {a.get('activity'):<60}  importance={a.get('importance')}")
    print("\n  Burnout drivers:")
    for d in tb.get("burnout_drivers") or []:
        print(f"    - {d.get('element'):<60}  value={d.get('value')}")

    banner(f"AI EXPOSURE — {chosen_soc}")
    ae = server._handle_get_ai_exposure({"soc_code": chosen_soc}).get("data") or {}
    print(f"  exposure_score:  {ae.get('exposure_score')}  (0-10; higher = more exposed)")
    print(f"  stat_res:        {ae.get('stat_res')}  (1-10; higher = more resilient)")
    print(f"  boss_ai_score:   {ae.get('boss_ai_score')}  (1-10 boss difficulty)")
    print(f"  category:        {ae.get('category')}")
    rationale = ae.get("rationale") or ""
    print(f"\n  rationale:\n    {rationale}")

    banner(f"CAREER BRANCHES FROM {chosen_soc}")
    cb = server._handle_get_career_branches({"soc_code": chosen_soc}).get("data") or []
    print(f"  {len(cb)} branches returned\n")
    header = (
        f"  {'related_soc':>11}  {'title':<40}  "
        f"{'rel_tier':>9}  {'wage':>9}  "
        f"{'grw_Δ':>6}  {'hmn_Δ':>6}  {'wage_Δ':>9}  {'res_Δ':>6}  {'ai_Δ':>6}"
    )
    print(header)
    print("  " + "-" * (len(header) - 2))
    for b in cb:
        print(
            f"  {b.get('related_soc_code') or '':>11}  "
            f"{(b.get('related_title') or '')[:40]:<40}  "
            f"{(b.get('relatedness_tier') or '')[:9]:>9}  "
            f"{fmt(b.get('related_wage'), 9)}  "
            f"{fmt(b.get('grw_delta'), 6)}  "
            f"{fmt(b.get('hmn_delta'), 6)}  "
            f"{fmt(b.get('wage_delta'), 9)}  "
            f"{fmt(b.get('res_delta'), 6)}  "
            f"{fmt(b.get('ai_boss_delta'), 6)}"
        )

    banner("PURCHASING POWER — IL vs IN")
    wage = od.get("median_annual_wage")
    if not isinstance(wage, (int, float)):
        print(f"  median_annual_wage unavailable ({wage!r}); skipping")
        return 0
    cpp = server._handle_compare_purchasing_power(
        {"salary": float(wage), "state_a": "IL", "state_b": "IN"}
    ).get("data") or {}
    sa = cpp.get("state_a") or {}
    sb = cpp.get("state_b") or {}
    print(f"  base salary: {fmt(cpp.get('salary'))}")
    print(f"\n  {'field':<24}  {'IL':>14}  {'IN':>14}")
    print("  " + "-" * 58)
    for field in (
        "state_name",
        "adjusted_salary",
        "cost_tier",
        "purchasing_power_multiplier",
        "data_source",
    ):
        va = sa.get(field)
        vb = sb.get(field)
        print(f"  {field:<24}  {fmt(va, 14)}  {fmt(vb, 14)}")

    print("\n=== COMPARISON COMPLETE ===")
    return 0


if __name__ == "__main__":
    import traceback

    try:
        sys.exit(run())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
