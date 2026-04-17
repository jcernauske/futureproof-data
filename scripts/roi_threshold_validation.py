"""Threshold validation for the new cost-of-attendance ROI formula.

Compares old vs new Fight Student Loans outcomes across 20 representative
school+major combos. Writes results to
``docs/sessions/roi-formula-threshold-validation.md``.

Run with: ``uv run python scripts/roi_threshold_validation.py``
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Make sure catalog env is set the same way the backend does so the MCP
# server points at the real warehouse.
os.environ.setdefault(
    "FUTUREPROOF_CATALOG_PATH",
    str(PROJECT_ROOT / "data" / "catalog" / "catalog.db"),
)
os.environ.setdefault(
    "FUTUREPROOF_WAREHOUSE_PATH",
    str(PROJECT_ROOT / "data" / "warehouse"),
)

from app.services import mcp_client  # noqa: E402
from app.services.boss_fights import BOSS_SPECS  # noqa: E402
from gold.futureproof_engine import compute_stat_roi  # noqa: E402  # type: ignore

LOAN_PCT = 0.75  # representative default per the task prompt


# ---------------------------------------------------------------------------
# 20 representative combos — (tier_label, school_query, cip_prefix, major_hint)
# cip_prefix is matched against the CIP 2-digit group (the first two chars of
# CIPCODE, e.g. "11" for Computer/Information Sciences). The first row whose
# CIP starts with that prefix is used.
# ---------------------------------------------------------------------------

COMBOS: list[dict[str, str]] = [
    # --- High-earning public ---
    {"bucket": "high_public", "school_query": "University of California-Berkeley", "cip_prefix": "11", "major": "Computer Science"},
    {"bucket": "high_public", "school_query": "Georgia Institute of Technology-Main Campus", "cip_prefix": "14", "major": "Engineering"},
    {"bucket": "high_public", "school_query": "University of North Carolina at Chapel Hill", "cip_prefix": "51.38", "major": "Nursing"},
    {"bucket": "high_public", "school_query": "The University of Texas at Austin", "cip_prefix": "52", "major": "Business"},
    {"bucket": "high_public", "school_query": "Purdue University-Main Campus", "cip_prefix": "14", "major": "Engineering"},
    # --- High-earning private ---
    {"bucket": "high_private", "school_query": "Massachusetts Institute of Technology", "cip_prefix": "11", "major": "Computer Science"},
    {"bucket": "high_private", "school_query": "Stanford University", "cip_prefix": "11", "major": "Computer Science"},
    {"bucket": "high_private", "school_query": "Harvard University", "cip_prefix": "45.06", "major": "Economics"},
    {"bucket": "high_private", "school_query": "University of Pennsylvania", "cip_prefix": "52.08", "major": "Finance"},
    {"bucket": "high_private", "school_query": "Carnegie Mellon University", "cip_prefix": "11", "major": "Computer Science"},
    # --- Moderate-earning public ---
    {"bucket": "mid_public", "school_query": "Indiana State University", "cip_prefix": "52", "major": "Business"},
    {"bucket": "mid_public", "school_query": "Arizona State University", "cip_prefix": "42", "major": "Psychology"},
    {"bucket": "mid_public", "school_query": "University of Florida", "cip_prefix": "09", "major": "Communications"},
    {"bucket": "mid_public", "school_query": "University of Georgia", "cip_prefix": "26", "major": "Biology"},
    {"bucket": "mid_public", "school_query": "Ohio State University-Main Campus", "cip_prefix": "54", "major": "History"},
    # --- Moderate-earning private/mixed ---
    {"bucket": "mid_private", "school_query": "New York University", "cip_prefix": "50.06", "major": "Film"},
    {"bucket": "mid_private", "school_query": "Boston University", "cip_prefix": "09", "major": "Communications"},
    {"bucket": "mid_private", "school_query": "Fordham University", "cip_prefix": "52", "major": "Business"},
    {"bucket": "mid_private", "school_query": "Syracuse University", "cip_prefix": "09", "major": "Communications"},
    {"bucket": "mid_private", "school_query": "DePaul University", "cip_prefix": "52.03", "major": "Accounting"},
]


def _fetch_school_rows(school_name: str) -> list[dict[str, Any]]:
    """Return all career_outcomes rows matching a fuzzy school name query."""
    try:
        result = mcp_client.call(
            "get_school_programs",
            {"school_name": school_name},
        )
    except Exception as exc:  # pragma: no cover
        print(f"  ! get_school_programs failed for {school_name!r}: {exc}")
        return []
    rows = result.get("data") or []
    return [r for r in rows if isinstance(r, dict)]


def _pick_school_row(rows: list[dict[str, Any]], cip_prefix: str,
                     school_name_hint: str) -> dict[str, Any] | None:
    """Given all rows that match a fuzzy school query, pick the single
    row best matching (exact-ish school name, cip prefix, cost fields present).

    Prefers an exact case-insensitive institution-name match to the hint
    when possible so queries like "Indiana State University" don't pull in
    other "Indiana University" matches.
    """
    hint_lower = school_name_hint.lower().strip()

    def _inst_matches(r: dict[str, Any]) -> bool:
        name = str(r.get("institution_name") or "").lower()
        # Exact match wins; otherwise fall back to substring.
        return name == hint_lower or hint_lower in name

    # First restrict to rows matching the institution hint.
    same_school = [r for r in rows if _inst_matches(r)]
    if not same_school:
        same_school = rows  # fallback: all fuzzy matches

    candidates = [
        r
        for r in same_school
        if str(r.get("cipcode", "")).startswith(cip_prefix)
        and r.get("debt_median") is not None
        and r.get("net_price_annual") is not None
        and r.get("earnings_1yr_median") is not None
    ]
    if not candidates:
        return None
    # Among valid candidates, prefer the one whose institution name has the
    # smallest edit-distance-ish heuristic to the hint — we just rank by
    # (exact match first, then longest common prefix length) and break
    # ties by earnings so bachelor's programs win over certificates.
    def _rank(r: dict[str, Any]) -> tuple[int, int, float]:
        name = str(r.get("institution_name") or "").lower()
        exact = 1 if name == hint_lower else 0
        # longest common prefix length
        lcp = 0
        for a, b in zip(name, hint_lower):
            if a != b:
                break
            lcp += 1
        return (exact, lcp, float(r.get("earnings_1yr_median") or 0))

    candidates.sort(key=_rank, reverse=True)
    return candidates[0]


def _score_loans(roi: int | None) -> str:
    spec = BOSS_SPECS["loans"]
    if roi is None:
        return "unknown"
    if roi >= spec.win_at_or_above:
        return "win"
    if roi >= spec.draw_at_or_above:
        return "draw"
    return "lose"


def _compute_old_roi(
    *,
    debt_median: float,
    earnings: float,
    loan_pct: float,
) -> int | None:
    """Old formula: modeled_debt = debt_median * loan_pct; then DTE -> ROI."""
    modeled_debt = float(debt_median) * float(loan_pct)
    try:
        dte = modeled_debt / float(earnings)
    except ZeroDivisionError:
        return None
    return compute_stat_roi(dte)


def _compute_new_roi(
    *,
    net_price: float,
    earnings: float,
    loan_pct: float,
) -> int | None:
    """New formula: modeled_debt = net_price * 4 * loan_pct; then DTE -> ROI."""
    modeled_debt = float(net_price) * 4.0 * float(loan_pct)
    try:
        dte = modeled_debt / float(earnings)
    except ZeroDivisionError:
        return None
    return compute_stat_roi(dte)


def main() -> int:
    results: list[dict[str, Any]] = []

    print(f"Resolving {len(COMBOS)} combos against MCP at loan_pct={LOAN_PCT}")
    print("=" * 80)

    for i, combo in enumerate(COMBOS, start=1):
        print(f"[{i:02d}/{len(COMBOS)}] {combo['school_query']} "
              f"[{combo['major']}]")
        rows = _fetch_school_rows(combo["school_query"])
        if not rows:
            print("    ! no rows from get_school_programs")
            results.append({**combo, "status": "no_unitid"})
            continue

        row = _pick_school_row(rows, combo["cip_prefix"], combo["school_query"])
        if row is None:
            print(f"    ! no program row for prefix={combo['cip_prefix']} "
                  f"with net_price/debt_median/earnings all populated")
            # Fall back: pick a program at the intended school with cost
            # fields populated, regardless of CIP prefix, so we still have
            # a data point for this school.
            fallback = _pick_school_row(rows, "", combo["school_query"])
            if fallback is None:
                results.append({
                    **combo,
                    "unitid": rows[0].get("unitid"),
                    "institution_name": rows[0].get("institution_name"),
                    "status": "no_program_row",
                })
                continue
            row = fallback

        debt_median = float(row["debt_median"])
        net_price = float(row["net_price_annual"])
        earnings = float(row["earnings_1yr_median"])
        cipcode = str(row["cipcode"])
        program_name = str(row.get("program_name") or "")
        unitid = int(row["unitid"])
        inst_name = str(row.get("institution_name") or combo["school_query"])

        old_roi = _compute_old_roi(
            debt_median=debt_median,
            earnings=earnings,
            loan_pct=LOAN_PCT,
        )
        new_roi = _compute_new_roi(
            net_price=net_price,
            earnings=earnings,
            loan_pct=LOAN_PCT,
        )
        old_fight = _score_loans(old_roi)
        new_fight = _score_loans(new_roi)

        # Modeled debts under each formula
        old_modeled_debt = debt_median * LOAN_PCT
        new_modeled_debt = net_price * 4.0 * LOAN_PCT
        old_dte = old_modeled_debt / earnings
        new_dte = new_modeled_debt / earnings

        results.append({
            **combo,
            "unitid": unitid,
            "institution_name": inst_name,
            "status": "ok",
            "cipcode": cipcode,
            "program_name": program_name,
            "earnings": earnings,
            "debt_median": debt_median,
            "net_price_annual": net_price,
            "old_modeled_debt": old_modeled_debt,
            "new_modeled_debt": new_modeled_debt,
            "old_dte": old_dte,
            "new_dte": new_dte,
            "old_roi": old_roi,
            "new_roi": new_roi,
            "old_fight": old_fight,
            "new_fight": new_fight,
        })
        print(
            f"    {inst_name} [{cipcode} {program_name[:30]}] "
            f"earn=${earnings:,.0f} debt_med=${debt_median:,.0f} "
            f"net_price=${net_price:,.0f}  "
            f"OLD ROI={old_roi} ({old_fight}) | NEW ROI={new_roi} ({new_fight})"
        )

    # ---------------------------------------------------------------
    # Distribution analysis
    # ---------------------------------------------------------------
    ok_rows = [r for r in results if r.get("status") == "ok"]

    def _count(key: str, val: str) -> int:
        return sum(1 for r in ok_rows if r[key] == val)

    old_wins = _count("old_fight", "win")
    old_draws = _count("old_fight", "draw")
    old_losses = _count("old_fight", "lose")
    new_wins = _count("new_fight", "win")
    new_draws = _count("new_fight", "draw")
    new_losses = _count("new_fight", "lose")

    transitions: dict[tuple[str, str], int] = {}
    for r in ok_rows:
        key = (r["old_fight"], r["new_fight"])
        transitions[key] = transitions.get(key, 0) + 1

    won_now_lose = sum(n for (o, n_), n in transitions.items() if o == "win" and n_ == "lose")
    lost_now_win = sum(n for (o, n_), n in transitions.items() if o == "lose" and n_ == "win")
    won_now_draw = sum(n for (o, n_), n in transitions.items() if o == "win" and n_ == "draw")
    lost_now_draw = sum(n for (o, n_), n in transitions.items() if o == "lose" and n_ == "draw")
    draw_now_win = sum(n for (o, n_), n in transitions.items() if o == "draw" and n_ == "win")
    draw_now_lose = sum(n for (o, n_), n in transitions.items() if o == "draw" and n_ == "lose")
    same = sum(n for (o, n_), n in transitions.items() if o == n_)

    # ---------------------------------------------------------------
    # Write the session log
    # ---------------------------------------------------------------
    out_path = PROJECT_ROOT / "docs" / "sessions" / "roi-formula-threshold-validation.md"
    lines: list[str] = []
    lines.append("# ROI Formula Threshold Validation — Fight Student Loans")
    lines.append("")
    lines.append("**Spec:** `docs/specs/roi-formula-cost-of-attendance.md` §2")
    lines.append("**Loan pct:** 0.75 (representative default)")
    lines.append("**Current thresholds:** `win ≥ 7`, `draw ≥ 5`")
    lines.append("")
    lines.append(
        "Compares old ROI formula (`debt_median × loan_pct`) vs new formula "
        "(`net_price_annual × 4 × loan_pct`) across 20 representative "
        "school+major combos spanning high/moderate earnings at public and "
        "private schools. Only combos with `net_price_annual` populated are "
        "evaluated — we are validating the new-formula path."
    )
    lines.append("")
    lines.append("## Per-combo table")
    lines.append("")
    lines.append(
        "| # | Bucket | School | CIP | Program | Earn | Debt med | Net price | "
        "Old debt@75% | New debt@75% | Old DTE | New DTE | Old ROI | New ROI | "
        "Old fight | New fight |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(results, start=1):
        if r.get("status") != "ok":
            lines.append(
                f"| {i} | {r['bucket']} | {r['school_query']} | — | — | — | "
                f"— | — | — | — | — | — | — | — | — | "
                f"({r.get('status', 'skipped')}) |"
            )
            continue
        lines.append(
            f"| {i} | {r['bucket']} | {r['institution_name']} | "
            f"{r['cipcode']} | {r['program_name'][:30]} | "
            f"${r['earnings']:,.0f} | ${r['debt_median']:,.0f} | "
            f"${r['net_price_annual']:,.0f} | "
            f"${r['old_modeled_debt']:,.0f} | ${r['new_modeled_debt']:,.0f} | "
            f"{r['old_dte']:.2f} | {r['new_dte']:.2f} | "
            f"{r['old_roi']} | {r['new_roi']} | "
            f"{r['old_fight']} | {r['new_fight']} |"
        )
    lines.append("")

    lines.append("## Distribution summary")
    lines.append("")
    n = len(ok_rows)
    lines.append(f"- Combos evaluated: **{n}** (of {len(COMBOS)} requested; "
                 f"skipped: {len(results) - n})")
    lines.append("")
    lines.append("**Outcome counts:**")
    lines.append("")
    lines.append("| Outcome | Old formula | New formula | Delta |")
    lines.append("|---|---|---|---|")
    lines.append(f"| win | {old_wins} | {new_wins} | {new_wins - old_wins:+d} |")
    lines.append(f"| draw | {old_draws} | {new_draws} | {new_draws - old_draws:+d} |")
    lines.append(f"| lose | {old_losses} | {new_losses} | {new_losses - old_losses:+d} |")
    lines.append("")
    lines.append("**Transition matrix (old → new):**")
    lines.append("")
    for (old, new), count in sorted(transitions.items()):
        flag = " ← same" if old == new else ""
        lines.append(f"- {old} → {new}: {count}{flag}")
    lines.append("")
    lines.append(f"- Unchanged: **{same}** / {n}")
    lines.append(
        f"- Students who used to WIN now LOSE: **{won_now_lose}**"
    )
    lines.append(
        f"- Students who used to WIN now DRAW: **{won_now_draw}**"
    )
    lines.append(
        f"- Students who used to LOSE now WIN: **{lost_now_win}**"
    )
    lines.append(
        f"- Students who used to LOSE now DRAW: **{lost_now_draw}**"
    )
    lines.append(
        f"- Students who used to DRAW now WIN: **{draw_now_win}**"
    )
    lines.append(
        f"- Students who used to DRAW now LOSE: **{draw_now_lose}**"
    )
    lines.append("")

    lines.append("## ROI score distribution comparison")
    lines.append("")
    lines.append("| ROI score | Old count | New count |")
    lines.append("|---|---|---|")
    for s in range(1, 11):
        old_c = sum(1 for r in ok_rows if r["old_roi"] == s)
        new_c = sum(1 for r in ok_rows if r["new_roi"] == s)
        lines.append(f"| {s} | {old_c} | {new_c} |")
    old_mean = (
        sum(r["old_roi"] for r in ok_rows if r["old_roi"] is not None) / n
        if n else 0.0
    )
    new_mean = (
        sum(r["new_roi"] for r in ok_rows if r["new_roi"] is not None) / n
        if n else 0.0
    )
    lines.append("")
    lines.append(f"- Mean old ROI: **{old_mean:.2f}**")
    lines.append(f"- Mean new ROI: **{new_mean:.2f}**")
    lines.append(f"- Mean shift: **{new_mean - old_mean:+.2f}**")
    lines.append("")

    # ---------------------------------------------------------------
    # Recommendation logic
    # ---------------------------------------------------------------
    lines.append("## Threshold recommendation")
    lines.append("")

    uniformly_worse = won_now_lose + won_now_draw > (n * 0.6) and lost_now_win == 0
    uniformly_better = lost_now_win + lost_now_draw > (n * 0.6) and won_now_lose == 0
    spread_out = (won_now_lose + lost_now_win) > 0 or (
        won_now_draw > 0 and draw_now_win > 0
    )

    if uniformly_worse:
        recommendation = (
            "**Adjust thresholds DOWN.** The distribution shifted uniformly "
            "worse under the new formula — most winners now draw or lose. "
            "Lowering the cutoffs preserves the original win/draw/lose mix "
            "without re-tuning the fight's narrative feel."
        )
    elif uniformly_better:
        recommendation = (
            "**Adjust thresholds UP.** The distribution shifted uniformly "
            "better — most losers now draw or win. Raising cutoffs keeps the "
            "fight meaningful."
        )
    elif spread_out:
        recommendation = (
            "**KEEP thresholds at win ≥ 7, draw ≥ 5.** The distribution is "
            "*spread out* rather than uniformly shifted: some combos improve, "
            "others worsen. That's the expected and desired behavior under "
            "cost-of-attendance — well-aided students at expensive schools "
            "see better ROI, students paying full net-price at pricey schools "
            "see worse ROI. Thresholds remain calibrated."
        )
    else:
        recommendation = (
            "**KEEP thresholds at win ≥ 7, draw ≥ 5.** Outcome distribution "
            "is essentially unchanged (most fights resolve to the same result "
            "under both formulas). No adjustment warranted."
        )

    lines.append(recommendation)
    lines.append("")
    lines.append("### Decision criteria")
    lines.append("")
    lines.append(
        "- **Keep** if distribution is spread out (some better / some worse) "
        "or essentially unchanged."
    )
    lines.append(
        "- **Adjust down** (e.g. win ≥ 6, draw ≥ 4) if >60% of wins become "
        "losses or draws AND no losses become wins."
    )
    lines.append(
        "- **Adjust up** (e.g. win ≥ 8, draw ≥ 6) if >60% of losses become "
        "wins or draws AND no wins become losses."
    )
    lines.append("")

    lines.append("### Raw signals")
    lines.append("")
    lines.append(f"- `uniformly_worse` heuristic: **{uniformly_worse}**")
    lines.append(f"- `uniformly_better` heuristic: **{uniformly_better}**")
    lines.append(f"- `spread_out` heuristic: **{spread_out}**")
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nSession log written: {out_path}")

    # Short stdout summary for the caller
    print()
    print("DISTRIBUTION SUMMARY")
    print(f"  old  w/d/l = {old_wins}/{old_draws}/{old_losses}")
    print(f"  new  w/d/l = {new_wins}/{new_draws}/{new_losses}")
    print(f"  unchanged: {same}/{n}")
    print(f"  won-now-lose: {won_now_lose}  lost-now-win: {lost_now_win}")
    print(f"  mean old ROI: {old_mean:.2f}  mean new ROI: {new_mean:.2f}")
    print(f"  uniformly_worse={uniformly_worse} uniformly_better={uniformly_better} spread_out={spread_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
