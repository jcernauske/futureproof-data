"""Data review spike for three-signal composite (S4).

Loads base.anthropic_observed_exposure + consumable.ai_exposure and
simulates the composite formula from the spec to understand:
 - Coverage: fraction three_signal / gemma_only / karpathy_only
 - stat_res delta distribution vs current stat_res
 - Weight sanity check (40/35/25)
 - Velocity label clustering
 - Edge cases (theoretical=0, observed>theoretical*10, NaN handling)
"""

from __future__ import annotations

import math
from pathlib import Path

import duckdb
from pyiceberg.catalog.sql import SqlCatalog

PROJECT_DIR = Path("/Users/jcernauske/code/bright/futureproof-data")
CATALOG_PATH = PROJECT_DIR / "data" / "catalog" / "catalog.db"
WAREHOUSE = PROJECT_DIR / "data" / "silver" / "iceberg_warehouse"


def compute_composite(
    gemma_score: float | None,
    karpathy_score: float | None,
    observed_pct: float | None,
) -> tuple[int | None, float | None, str | None, str]:
    theoretical = gemma_score if gemma_score is not None else karpathy_score
    if theoretical is None:
        return (None, None, None, "no_data")

    observed_normalized = (observed_pct / 10.0) if observed_pct is not None else None

    velocity_ratio = None
    velocity_label = None
    velocity_normalized = None

    if observed_normalized is not None and theoretical > 0:
        velocity_ratio = observed_normalized / theoretical
        velocity_normalized = min(velocity_ratio * 10, 10)
        if velocity_ratio > 0.5:
            velocity_label = "rapid"
        elif velocity_ratio > 0.25:
            velocity_label = "moderate"
        elif velocity_ratio > 0.1:
            velocity_label = "slow"
        else:
            velocity_label = "nascent"

    if observed_normalized is not None and velocity_normalized is not None:
        composite = (
            0.40 * theoretical
            + 0.35 * observed_normalized
            + 0.25 * velocity_normalized
        )
        method = "three_signal"
    else:
        composite = theoretical
        method = "gemma_only" if gemma_score is not None else "karpathy_only"

    return (
        round(max(0, min(10, composite))),
        velocity_ratio,
        velocity_label,
        method,
    )


def main() -> None:
    cat = SqlCatalog(
        "brightsmith",
        **{
            "uri": f"sqlite:///{CATALOG_PATH}",
            "warehouse": f"file://{WAREHOUSE}",
        },
    )
    print("=== Inspecting base.anthropic_observed_exposure ===")
    anth = cat.load_table("base.anthropic_observed_exposure")
    anth_df = anth.scan().to_arrow().to_pandas()
    print(f"Rows: {len(anth_df)}")
    print(f"Columns: {list(anth_df.columns)}")
    print(anth_df.head(5).to_string())
    print()
    print("observed_exposure_pct describe:")
    print(anth_df["observed_exposure_pct"].describe())
    print()
    print("Null counts:")
    print(anth_df.isnull().sum())
    print()

    # Load consumable.ai_exposure from Gold catalog
    gold_catalog_path = PROJECT_DIR / "data" / "catalog" / "catalog.db"
    gold_warehouse = PROJECT_DIR / "data" / "gold" / "iceberg_warehouse"
    gold_cat = SqlCatalog(
        "brightsmith_gold",
        **{
            "uri": f"sqlite:///{gold_catalog_path}",
            "warehouse": f"file://{gold_warehouse}",
        },
    )
    print("=== Inspecting consumable.ai_exposure ===")
    try:
        ai = gold_cat.load_table("consumable.ai_exposure")
    except Exception:
        # Fallback — try the silver catalog (same db, different path root)
        ai = cat.load_table("consumable.ai_exposure")
    ai_df = ai.scan().to_arrow().to_pandas()
    print(f"Rows: {len(ai_df)}")
    print(f"Columns: {list(ai_df.columns)}")
    print()
    print("scoring_model counts:")
    print(ai_df["scoring_model"].value_counts())
    print()
    print("observed_exposure_pct null? ",
          ai_df["observed_exposure_pct"].isnull().sum(), "/", len(ai_df))
    print("karpathy_score null? ",
          ai_df["karpathy_score"].isnull().sum(), "/", len(ai_df))
    print("exposure_score describe:")
    print(ai_df["exposure_score"].describe())
    print()

    # Simulate composite for every row
    rows = []
    for _, r in ai_df.iterrows():
        gemma = r["exposure_score"] if r["scoring_model"] == "gemma-4" else None
        karp = r["karpathy_score"] if not _is_nan(r["karpathy_score"]) else None
        # If scoring_model is gemini-flash, exposure_score IS karpathy-derived.
        if r["scoring_model"] == "gemini-flash":
            gemma = None
            karp = r["exposure_score"]
        obs = r["observed_exposure_pct"]
        if _is_nan(obs):
            obs = None

        comp, vel_r, vel_lbl, method = compute_composite(
            gemma if gemma is not None else None,
            karp if karp is not None else None,
            obs,
        )
        new_stat_res = None
        if comp is not None:
            new_stat_res = min(11 - comp, 10)
        rows.append(
            {
                "soc_code": r["soc_code"],
                "title": r["occupation_title"],
                "current_exposure": r["exposure_score"],
                "current_stat_res": r["stat_res"],
                "scoring_model": r["scoring_model"],
                "observed_pct": obs,
                "composite": comp,
                "new_stat_res": new_stat_res,
                "velocity_ratio": vel_r,
                "velocity_label": vel_lbl,
                "method": method,
            }
        )

    import pandas as pd

    sim = pd.DataFrame(rows)
    print("=== Simulated composite output ===")
    print("method counts:")
    print(sim["method"].value_counts(dropna=False))
    print()
    print("velocity_label counts (three_signal only):")
    print(sim[sim["method"] == "three_signal"]["velocity_label"].value_counts(dropna=False))
    print()
    print("velocity_ratio describe (three_signal):")
    print(sim[sim["method"] == "three_signal"]["velocity_ratio"].describe())
    print()
    print("velocity_ratio > 1.0 count:",
          (sim["velocity_ratio"] > 1.0).sum())
    print()

    # Compare current vs new stat_res
    deltas = sim[sim["method"] == "three_signal"].copy()
    deltas["stat_res_delta"] = deltas["new_stat_res"] - deltas["current_stat_res"]
    print("stat_res delta (three_signal):")
    print(deltas["stat_res_delta"].describe())
    print("delta distribution:")
    print(deltas["stat_res_delta"].value_counts().sort_index())
    print()

    print("=== Biggest stat_res INCREASES (more resilient — composite went lower) ===")
    print(
        deltas.nlargest(10, "stat_res_delta")[
            ["soc_code", "title", "current_exposure", "observed_pct",
             "composite", "current_stat_res", "new_stat_res",
             "velocity_label", "stat_res_delta"]
        ].to_string(index=False)
    )
    print()

    print("=== Biggest stat_res DROPS (less resilient — composite went higher) ===")
    print(
        deltas.nsmallest(10, "stat_res_delta")[
            ["soc_code", "title", "current_exposure", "observed_pct",
             "composite", "current_stat_res", "new_stat_res",
             "velocity_label", "stat_res_delta"]
        ].to_string(index=False)
    )
    print()

    # Edge case 1: theoretical=0 with observed_pct>0
    edge1 = sim[(sim["current_exposure"] == 0) & (sim["observed_pct"].notna())]
    print(f"=== Edge case: theoretical=0 with observed data ({len(edge1)} rows) ===")
    if len(edge1) > 0:
        print(edge1.head(10).to_string(index=False))
    print()

    # Edge case 2: velocity_ratio > 1
    over1 = sim[sim["velocity_ratio"] > 1.0]
    print(f"=== Edge case: velocity_ratio > 1.0 ({len(over1)} rows) ===")
    if len(over1) > 0:
        print(over1[["soc_code", "title", "current_exposure", "observed_pct",
                     "velocity_ratio", "velocity_label", "composite"]]
              .head(10).to_string(index=False))
    print()

    # Popular majors / popular careers — sanity check
    # Grab a sample of well-known SOCs
    popular_socs = [
        "15-1252",  # Software Developers
        "13-2051",  # Financial Analysts
        "11-1021",  # General & Operations Managers
        "29-1141",  # Registered Nurses
        "13-1111",  # Management Analysts
        "25-2021",  # Elementary School Teachers
        "47-2111",  # Electricians
        "47-2152",  # Plumbers
        "11-9021",  # Construction Managers
        "15-1299",  # CS Misc
        "23-1011",  # Lawyers
        "29-1221",  # Pediatricians
        "27-3023",  # News Analysts / Reporters
        "43-9021",  # Data Entry Keyers
        "13-2011",  # Accountants and Auditors
    ]
    print("=== Popular-SOC sanity check ===")
    popular = sim[sim["soc_code"].isin(popular_socs)].sort_values("soc_code")
    print(popular[["soc_code", "title", "current_exposure", "observed_pct",
                   "composite", "current_stat_res", "new_stat_res",
                   "velocity_label", "method"]].to_string(index=False))
    print()

    # Weight sensitivity — if we shift the weights, how much does it move?
    print("=== Weight sensitivity (40/35/25 vs 50/30/20 vs 33/33/33) ===")

    def comp_with_weights(theo, obs_pct, w_t, w_o, w_v):
        if theo is None or obs_pct is None or theo == 0:
            return None
        on = obs_pct / 10.0
        vr = on / theo
        vn = min(vr * 10, 10)
        c = w_t * theo + w_o * on + w_v * vn
        return round(max(0, min(10, c)))

    sample = deltas.head(500)
    for label, (wt, wo, wv) in [
        ("40/35/25", (0.40, 0.35, 0.25)),
        ("50/30/20", (0.50, 0.30, 0.20)),
        ("33/33/33", (0.3333, 0.3334, 0.3333)),
        ("60/40/00", (0.60, 0.40, 0.0)),
    ]:
        vals = sample.apply(
            lambda r, wt=wt, wo=wo, wv=wv: comp_with_weights(
                r["current_exposure"], r["observed_pct"], wt, wo, wv
            ),
            axis=1,
        )
        print(f"  {label}: mean={vals.mean():.2f}  median={vals.median():.2f}  "
              f"std={vals.std():.2f}")

    print()

    # Check monotonicity assumption: for fixed theoretical, higher observed
    # should mean HIGHER composite (more exposure).
    print("=== Monotonicity sanity ===")
    test_theo = 6
    for obs in [0, 10, 25, 40, 55, 70, 85]:
        c, vr, vl, _ = compute_composite(test_theo, None, obs)
        print(f"  theo={test_theo}, obs={obs}% -> composite={c}, "
              f"velocity={vr:.3f}, label={vl}")
    print()

    # Tier snapshot — grouped by major category (SOC prefix)
    print("=== stat_res delta by SOC major group ===")
    deltas["major"] = deltas["soc_code"].str.slice(0, 2)
    grp = deltas.groupby("major")["stat_res_delta"].agg(["mean", "count"])
    print(grp.sort_values("mean").to_string())


def _is_nan(x):
    if x is None:
        return True
    try:
        return math.isnan(x)
    except (TypeError, ValueError):
        return False


if __name__ == "__main__":
    main()
