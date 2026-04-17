"""Option B simulation for three-signal composite (S4 v4).

Rebuilds the v3 spike around the new formula:

    adoption_percentile = percent_rank(ai_adoption_share) * 100
    confidence          = clamp(0.3 + 0.7 * adoption_percentile / 100, 0.3, 1.0)
    composite_exposure  = confidence * theoretical + (1 - confidence) * baseline

Velocity labels bucket adoption_percentile into saturating / accelerating /
emerging / nascent (>=90 / >=70 / >=40 / else). Fallback rules per the
v4 spec: no Anthropic → confidence=0.5, velocity="unknown"; no Gemma →
composite=baseline, method="karpathy_only"; Gemma=0 with adoption>0 →
composite=baseline*confidence, method="observed_override"; both None →
no_data.

Run: `uv run python scripts/data_review_three_signal_option_b.py`.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

PROJECT_DIR = Path(__file__).resolve().parents[1]
CATALOG_PATH = PROJECT_DIR / "data" / "catalog" / "catalog.db"
SILVER_WAREHOUSE = PROJECT_DIR / "data" / "silver" / "iceberg_warehouse"
GOLD_WAREHOUSE = PROJECT_DIR / "data" / "gold" / "iceberg_warehouse"


def percent_rank(values: list[float | None]) -> list[float | None]:
    """Return percent_rank * 100 (0-100), preserving None slots."""
    ranked = [(i, v) for i, v in enumerate(values) if v is not None]
    ranked.sort(key=lambda iv: iv[1])
    n = len(ranked)
    out: list[float | None] = [None] * len(values)
    if n == 0:
        return out
    if n == 1:
        out[ranked[0][0]] = 100.0
        return out
    for rank, (idx, _) in enumerate(ranked):
        out[idx] = 100.0 * rank / (n - 1)
    return out


def velocity_from_percentile(pct: float | None) -> str:
    if pct is None:
        return "unknown"
    if pct >= 90:
        return "saturating"
    if pct >= 70:
        return "accelerating"
    if pct >= 40:
        return "emerging"
    return "nascent"


def compute_composite_ob(
    gemma: int | None,
    karpathy: int | None,
    share: float | None,
    percentile: float | None,
) -> tuple[int | None, float | None, str, str, float | None]:
    """Return (composite_int, confidence, velocity, method, percentile)."""
    theoretical = gemma
    baseline = karpathy

    if percentile is not None:
        confidence = max(0.3, min(1.0, 0.3 + 0.7 * percentile / 100))
        velocity = velocity_from_percentile(percentile)
    else:
        confidence = 0.5
        velocity = "unknown"

    if theoretical is None and baseline is None:
        return None, None, velocity, "no_data", percentile
    if theoretical is None:
        return (
            max(0, min(10, round(float(baseline)))),
            confidence,
            velocity,
            "karpathy_only",
            percentile,
        )
    if baseline is None:
        method = "gemma_only" if share is None else "gemma_plus_anthropic"
        return (
            max(0, min(10, round(float(theoretical)))),
            confidence,
            velocity,
            method,
            percentile,
        )
    if theoretical == 0 and share is not None and share > 0:
        return (
            max(0, min(10, round(baseline * confidence))),
            confidence,
            velocity,
            "observed_override",
            percentile,
        )

    composite = confidence * theoretical + (1 - confidence) * baseline
    method = "three_signal" if share is not None else "two_signal_no_anthropic"
    return (
        max(0, min(10, round(composite))),
        confidence,
        velocity,
        method,
        percentile,
    )


def derive_stat_res(composite: int | None) -> int | None:
    if composite is None:
        return None
    return min(11 - composite, 10)


def main() -> None:
    silver = get_catalog(SILVER_WAREHOUSE, CATALOG_PATH)
    gold = get_catalog(GOLD_WAREHOUSE, CATALOG_PATH)

    anthropic = read_with_duckdb(silver.load_table("base.anthropic_observed_exposure"))
    exposure = read_with_duckdb(gold.load_table("consumable.ai_exposure"))

    share_by_soc = {r["soc_code"]: r.get("observed_exposure_pct") for r in anthropic}

    # Compute percentile across all SOCs that appear in ai_exposure (full set),
    # using their share (None if absent).
    rows = []
    for r in exposure:
        soc = r["soc_code"]
        share = share_by_soc.get(soc)
        rows.append({
            "soc_code": soc,
            "title": r.get("occupation_title"),
            "gemma": r.get("exposure_score") if r.get("scoring_model") == "gemma-4" else None,
            "karpathy": r.get("karpathy_score") if r.get("karpathy_score") is not None else (
                r.get("exposure_score") if r.get("scoring_model") == "gemini-flash" else None
            ),
            "share": share,
            "current_stat_res": r.get("stat_res"),
        })

    percentiles = percent_rank([row["share"] for row in rows])
    for row, pct in zip(rows, percentiles):
        comp, conf, vel, method, p = compute_composite_ob(
            row["gemma"], row["karpathy"], row["share"], pct
        )
        row["composite"] = comp
        row["confidence"] = conf
        row["velocity"] = vel
        row["method"] = method
        row["percentile"] = p
        row["new_stat_res"] = derive_stat_res(comp)

    total = len(rows)
    method_counts = Counter(r["method"] for r in rows)
    velocity_counts = Counter(r["velocity"] for r in rows)
    print(f"Total rows: {total}")
    print("Method distribution:")
    for k, v in method_counts.most_common():
        print(f"  {k:25s} {v:5d} ({100*v/total:5.1f}%)")
    print("Velocity distribution:")
    for k, v in velocity_counts.most_common():
        print(f"  {k:15s} {v:5d} ({100*v/total:5.1f}%)")

    # stat_res delta distribution
    deltas: list[int] = []
    for r in rows:
        if r["new_stat_res"] is not None and r["current_stat_res"] is not None:
            deltas.append(r["new_stat_res"] - r["current_stat_res"])
    if deltas:
        import statistics
        print()
        print(f"stat_res delta (new vs current): n={len(deltas)} "
              f"min={min(deltas)} max={max(deltas)} "
              f"mean={statistics.mean(deltas):+.2f} "
              f"median={statistics.median(deltas)}")
        delta_hist = Counter(deltas)
        for d in sorted(delta_hist):
            print(f"  delta {d:+d}: {delta_hist[d]}")

    # Spot check: popular blue-collar + high-exposure clerical roles
    spot = {
        "47-2031": "Carpenters",
        "47-2111": "Electricians",
        "47-2152": "Plumbers",
        "11-9021": "Construction Managers",
        "25-2021": "Elementary School Teachers",
        "29-1141": "Registered Nurses",
        "15-1252": "Software Developers",
        "15-1131": "Computer Programmers",
        "13-2051": "Financial Analysts",
        "43-9021": "Data Entry Keyers",
        "31-9094": "Medical Transcriptionists",
        "43-4051": "Customer Service Representatives",
        "43-3051": "Payroll and Timekeeping Clerks",
        "25-2011": "Preschool Teachers",
        "35-3023": "Fast Food and Counter Workers",
    }
    print()
    print("Spot checks (old stat_res → new stat_res, method, velocity):")
    by_soc = {r["soc_code"]: r for r in rows}
    for soc, label in spot.items():
        r = by_soc.get(soc)
        if r is None:
            print(f"  {soc} {label}: MISSING from ai_exposure")
            continue
        print(
            f"  {soc} {label[:35]:<35s} "
            f"g={r['gemma']!s:>4} k={r['karpathy']!s:>4} "
            f"share={(f'{r['share']:.4f}' if r['share'] is not None else '  —  '):>7} "
            f"pct={(f'{r['percentile']:5.1f}' if r['percentile'] is not None else ' —  '):>5} "
            f"conf={(f'{r['confidence']:.2f}' if r['confidence'] is not None else ' — '):>4} "
            f"old_res={r['current_stat_res']!s:>3} new_res={r['new_stat_res']!s:>3} "
            f"{r['method']:<22s} {r['velocity']}"
        )

    # Saturation check: how many blue-collar SOCs end up at stat_res=10?
    blue_collar_prefixes = ("47-", "49-", "51-", "53-", "45-", "31-", "37-", "39-")
    saturated = [
        r for r in rows
        if r["new_stat_res"] == 10 and r["soc_code"].startswith(blue_collar_prefixes)
    ]
    blue_total = sum(1 for r in rows if r["soc_code"].startswith(blue_collar_prefixes))
    print()
    print(f"Blue-collar saturation at stat_res=10: {len(saturated)}/{blue_total} "
          f"({100*len(saturated)/blue_total if blue_total else 0:.1f}%)")


if __name__ == "__main__":
    main()
