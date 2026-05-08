"""EDA for bronze.bls_oews — BLS OEWS National Wage Percentiles, May 2024.

Profiles the freshly-landed Bronze table for spec
``docs/specs/ingest-bls-oews-wage-percentiles.md``. Cross-references with
``bronze.bls_ooh`` and ``consumable.onet_work_profiles`` to lock the Gold
coverage threshold for downstream DQ rules.
"""
from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path

import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pyiceberg.catalog.sql import SqlCatalog


_CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"


def _catalog(warehouse_subpath: str) -> SqlCatalog:
    """All zones share data/catalog/catalog.db; warehouse path is per-zone.

    Catalog name must be ``brightsmith`` to match how the ingestor wrote the
    rows (see ``brightsmith.config.PROJECT_NAME``).
    """
    return SqlCatalog(
        "brightsmith",
        uri=f"sqlite:///{_CATALOG_PATH}",
        warehouse=str(PROJECT_ROOT / warehouse_subpath),
    )


def get_bronze_catalog() -> SqlCatalog:
    return _catalog("data/bronze/iceberg_warehouse")


def get_silver_catalog() -> SqlCatalog:
    return _catalog("data/silver/iceberg_warehouse")


def get_gold_catalog() -> SqlCatalog:
    return _catalog("data/gold/iceberg_warehouse")


def load_table_rows(catalog: SqlCatalog, identifier: str) -> list[dict]:
    table = catalog.load_table(identifier)
    arrow = table.scan().to_arrow()
    return arrow.to_pylist()


def percentile(sorted_vals: list[float], p: float) -> float | None:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return float(sorted_vals[f])
    return float(sorted_vals[f]) + (k - f) * (float(sorted_vals[c]) - float(sorted_vals[f]))


def main() -> None:
    bronze_catalog = get_bronze_catalog()
    silver_catalog = get_silver_catalog()
    gold_catalog = get_gold_catalog()

    # Load OEWS bronze
    oews = load_table_rows(bronze_catalog, "bronze.bls_oews")
    ooh_bronze = load_table_rows(bronze_catalog, "bronze.bls_ooh")
    ooh_silver = load_table_rows(silver_catalog, "base.bls_ooh")
    onet_work = load_table_rows(gold_catalog, "consumable.onet_work_profiles")

    out: dict = {}

    # 1. Row count + schema
    out["row_count"] = len(oews)
    out["columns"] = list(oews[0].keys()) if oews else []

    # SOC code overlap with bls_ooh and onet_work_profiles
    oews_socs = {r["soc_code"] for r in oews if r.get("soc_code")}
    ooh_socs_bronze = {r["soc_code"] for r in ooh_bronze if r.get("soc_code")}
    ooh_socs_silver = {r["soc_code"] for r in ooh_silver if r.get("soc_code")}
    # consumable.onet_work_profiles uses ``bls_soc_code`` instead of ``soc_code``.
    onet_socs = {
        r.get("bls_soc_code") or r.get("soc_code")
        for r in onet_work
        if r.get("bls_soc_code") or r.get("soc_code")
    }

    out["overlap"] = {
        "oews_count": len(oews_socs),
        "bls_ooh_bronze_count": len(ooh_socs_bronze),
        "bls_ooh_silver_count": len(ooh_socs_silver),
        "onet_work_profiles_count": len(onet_socs),
        "oews_AND_ooh_bronze": len(oews_socs & ooh_socs_bronze),
        "oews_AND_ooh_silver": len(oews_socs & ooh_socs_silver),
        "ooh_silver_minus_oews": len(ooh_socs_silver - oews_socs),
        "oews_minus_ooh_silver": len(oews_socs - ooh_socs_silver),
        "oews_AND_onet": len(oews_socs & onet_socs),
        "onet_minus_oews": len(onet_socs - oews_socs),
    }
    # Examples of OEWS-only and OOH-only SOCs
    oews_titles = {r["soc_code"]: r.get("occupation_title") for r in oews}
    ooh_titles = {r["soc_code"]: r.get("occupation_title") for r in ooh_silver}
    only_in_ooh = sorted(ooh_socs_silver - oews_socs)
    only_in_oews = sorted(oews_socs - ooh_socs_silver)
    out["overlap"]["only_in_ooh_examples"] = [
        (s, ooh_titles.get(s)) for s in only_in_ooh[:15]
    ]
    out["overlap"]["only_in_oews_examples"] = [
        (s, oews_titles.get(s)) for s in only_in_oews[:15]
    ]

    # 2. Wage distribution shape — wage_annual_median
    medians = sorted(
        r["wage_annual_median"] for r in oews if r.get("wage_annual_median") is not None
    )
    if medians:
        out["wage_annual_median_distribution"] = {
            "n_non_null": len(medians),
            "min": medians[0],
            "p10": percentile(medians, 10),
            "p25": percentile(medians, 25),
            "median": percentile(medians, 50),
            "mean": round(statistics.fmean(medians), 2),
            "p75": percentile(medians, 75),
            "p90": percentile(medians, 90),
            "max": medians[-1],
            "stdev": round(statistics.pstdev(medians), 2),
        }
        # Histogram buckets (10K width up to 240K)
        hist = Counter()
        for v in medians:
            bucket = min(int(v // 10_000), 24)  # cap at 24 = 240K+
            hist[bucket] += 1
        out["wage_annual_median_histogram_10k"] = {
            f"${b * 10}K-${(b + 1) * 10}K": hist[b] for b in sorted(hist)
        }

    # 3. Suppression rate per percentile column
    pct_cols = [
        "wage_annual_p10",
        "wage_annual_p25",
        "wage_annual_median",
        "wage_annual_p75",
        "wage_annual_p90",
        "wage_annual_mean",
        "wage_hourly_median",
        "total_employment",
    ]
    suppression = {}
    for col in pct_cols:
        non_null = sum(1 for r in oews if r.get(col) is not None)
        suppression[col] = {
            "non_null": non_null,
            "null": len(oews) - non_null,
            "non_null_rate": round(100.0 * non_null / max(len(oews), 1), 3),
        }
    out["suppression_rates_pct"] = suppression

    # 4. Top-coding — wage_capped True count + which percentiles top-coded
    capped = [r for r in oews if r.get("wage_capped")]
    out["top_coded"] = {
        "rows_capped": len(capped),
        "rows_capped_rate": round(100.0 * len(capped) / max(len(oews), 1), 3),
    }
    # Per-percentile equal-to-239200 count (the floor)
    TOP_CODED_VALUE = 239_200.0
    per_pct_capped = {}
    for col in [
        "wage_annual_p10",
        "wage_annual_p25",
        "wage_annual_median",
        "wage_annual_p75",
        "wage_annual_p90",
        "wage_annual_mean",
    ]:
        n = sum(1 for r in oews if r.get(col) == TOP_CODED_VALUE)
        per_pct_capped[col] = n
    out["top_coded_per_percentile"] = per_pct_capped

    # Top-coded SOC titles
    capped_titles = sorted(
        [(r["soc_code"], r.get("occupation_title")) for r in capped],
        key=lambda t: t[0],
    )
    out["top_coded_socs"] = capped_titles

    # 5. Monotonicity p10 ≤ p25 ≤ median ≤ p75 ≤ p90 (where all non-null)
    full_data = [
        r
        for r in oews
        if all(
            r.get(k) is not None
            for k in (
                "wage_annual_p10",
                "wage_annual_p25",
                "wage_annual_median",
                "wage_annual_p75",
                "wage_annual_p90",
            )
        )
    ]
    violations = []
    for r in full_data:
        seq = [
            r["wage_annual_p10"],
            r["wage_annual_p25"],
            r["wage_annual_median"],
            r["wage_annual_p75"],
            r["wage_annual_p90"],
        ]
        for i in range(len(seq) - 1):
            if seq[i] > seq[i + 1]:
                violations.append(
                    {
                        "soc_code": r["soc_code"],
                        "title": r.get("occupation_title"),
                        "values": seq,
                        "violated_pair": (
                            ["p10", "p25", "median", "p75", "p90"][i],
                            ["p10", "p25", "median", "p75", "p90"][i + 1],
                        ),
                    }
                )
                break
    out["monotonicity"] = {
        "rows_with_full_data": len(full_data),
        "violations_count": len(violations),
        "violation_rate_pct": round(
            100.0 * len(violations) / max(len(full_data), 1), 4
        ),
        "violations_examples": violations[:10],
    }

    # 6. Spread (p75 - p25) — widest and narrowest careers
    spreads = []
    for r in oews:
        p25 = r.get("wage_annual_p25")
        p75 = r.get("wage_annual_p75")
        if p25 is not None and p75 is not None:
            spreads.append(
                {
                    "soc_code": r["soc_code"],
                    "title": r.get("occupation_title"),
                    "p25": p25,
                    "p75": p75,
                    "spread": p75 - p25,
                    "wage_capped": bool(r.get("wage_capped")),
                }
            )
    spreads.sort(key=lambda x: x["spread"], reverse=True)
    out["spread_p75_minus_p25"] = {
        "n_rows": len(spreads),
        "widest_top10": spreads[:10],
        "narrowest_bottom10": spreads[-10:],
        "median_spread": percentile(
            sorted(s["spread"] for s in spreads), 50
        ),
        "p10_spread": percentile(sorted(s["spread"] for s in spreads), 10),
        "p90_spread": percentile(sorted(s["spread"] for s in spreads), 90),
    }

    # 7. Spec spot-checks
    spec_checks = [
        ("29-1141", "Registered Nurses", "median ~$86K"),
        ("15-1252", "Software Developers", "median ~$130K"),
        ("29-1171", "Nurse Practitioners", "median ~$126K"),
        ("11-1011", "Chief Executives", "p90 top-coded"),
    ]
    spot = []
    by_soc = {r["soc_code"]: r for r in oews}
    for soc, expected_title, note in spec_checks:
        r = by_soc.get(soc)
        if not r:
            spot.append({"soc": soc, "expected": expected_title, "note": note, "status": "MISSING"})
            continue
        spot.append(
            {
                "soc": soc,
                "expected_title": expected_title,
                "actual_title": r.get("occupation_title"),
                "p10": r.get("wage_annual_p10"),
                "p25": r.get("wage_annual_p25"),
                "median": r.get("wage_annual_median"),
                "p75": r.get("wage_annual_p75"),
                "p90": r.get("wage_annual_p90"),
                "mean": r.get("wage_annual_mean"),
                "wage_capped": bool(r.get("wage_capped")),
                "total_employment": r.get("total_employment"),
                "note": note,
            }
        )
    out["spec_spot_checks"] = spot

    # 8. Outliers / anomalies
    anomalies: list[dict] = []
    # Negative wages
    for r in oews:
        for col in [
            "wage_annual_p10",
            "wage_annual_p25",
            "wage_annual_median",
            "wage_annual_p75",
            "wage_annual_p90",
            "wage_annual_mean",
        ]:
            v = r.get(col)
            if v is not None and v < 0:
                anomalies.append(
                    {
                        "type": "negative_wage",
                        "soc": r["soc_code"],
                        "title": r.get("occupation_title"),
                        "col": col,
                        "value": v,
                    }
                )
    # SOC code format
    import re

    soc_re = re.compile(r"^\d{2}-\d{4}$")
    bad_soc = [
        (r["soc_code"], r.get("occupation_title"))
        for r in oews
        if not r.get("soc_code") or not soc_re.match(r["soc_code"])
    ]
    out["soc_code_format_violations"] = {
        "count": len(bad_soc),
        "examples": bad_soc[:10],
    }

    # SOC code uniqueness
    soc_counts = Counter(r["soc_code"] for r in oews)
    duplicates = [(s, c) for s, c in soc_counts.items() if c > 1]
    out["soc_code_duplicates"] = {
        "count": len(duplicates),
        "examples": duplicates[:10],
    }

    # Title null
    null_titles = sum(1 for r in oews if not r.get("occupation_title"))
    out["null_occupation_title"] = null_titles

    # wage_capped True but no field equal to 239200
    bad_cap = []
    for r in oews:
        if r.get("wage_capped"):
            if not any(
                r.get(c) == TOP_CODED_VALUE
                for c in [
                    "wage_annual_p10",
                    "wage_annual_p25",
                    "wage_annual_median",
                    "wage_annual_p75",
                    "wage_annual_p90",
                    "wage_annual_mean",
                ]
            ):
                bad_cap.append((r["soc_code"], r.get("occupation_title")))
    out["wage_capped_without_floor_value"] = {
        "count": len(bad_cap),
        "examples": bad_cap[:10],
    }

    # mean vs median sanity (mean > p90 = suspicious)
    suspicious_mean = []
    for r in oews:
        m = r.get("wage_annual_mean")
        p90 = r.get("wage_annual_p90")
        if m is not None and p90 is not None and m > p90:
            suspicious_mean.append(
                {"soc": r["soc_code"], "title": r.get("occupation_title"), "mean": m, "p90": p90}
            )
    out["mean_above_p90"] = {
        "count": len(suspicious_mean),
        "examples": suspicious_mean[:10],
    }

    # 9. Cross-source overlap quality — silver.bls_ooh SOCs with OEWS p25 non-null
    ooh_silver_socs_with_oews_p25 = 0
    ooh_silver_socs_with_oews = 0
    for s in ooh_socs_silver:
        r = by_soc.get(s)
        if r is None:
            continue
        ooh_silver_socs_with_oews += 1
        if r.get("wage_annual_p25") is not None:
            ooh_silver_socs_with_oews_p25 += 1
    out["join_coverage_ooh_x_oews"] = {
        "ooh_silver_total": len(ooh_socs_silver),
        "ooh_silver_intersect_oews": ooh_silver_socs_with_oews,
        "ooh_silver_intersect_oews_with_p25": ooh_silver_socs_with_oews_p25,
        "p25_coverage_after_join_pct": round(
            100.0 * ooh_silver_socs_with_oews_p25 / max(len(ooh_socs_silver), 1), 3
        ),
    }

    # ALL annual percentile coverage when joined
    coverage_per_pct = {}
    for col in [
        "wage_annual_p10",
        "wage_annual_p25",
        "wage_annual_median",
        "wage_annual_p75",
        "wage_annual_p90",
    ]:
        n = 0
        for s in ooh_socs_silver:
            r = by_soc.get(s)
            if r and r.get(col) is not None:
                n += 1
        coverage_per_pct[col] = {
            "non_null_after_join": n,
            "rate_pct": round(100.0 * n / max(len(ooh_socs_silver), 1), 3),
        }
    out["join_coverage_per_percentile"] = coverage_per_pct

    # 10. Threshold lock-in — recommend ≥ N SOCs with non-null wage_p25
    out["threshold_recommendation"] = {
        "spec_proposed_floor": 750,
        "actual_p25_coverage_in_ooh_intersect": ooh_silver_socs_with_oews_p25,
        "headroom": ooh_silver_socs_with_oews_p25 - 750,
    }

    # Detailed null patterns — rows that have median=null
    null_median_rows = [
        {
            "soc": r["soc_code"],
            "title": r.get("occupation_title"),
            "tot_emp": r.get("total_employment"),
            "p10": r.get("wage_annual_p10"),
            "p25": r.get("wage_annual_p25"),
            "p75": r.get("wage_annual_p75"),
            "p90": r.get("wage_annual_p90"),
        }
        for r in oews
        if r.get("wage_annual_median") is None
    ]
    out["null_median_rows"] = {
        "count": len(null_median_rows),
        "rows": null_median_rows[:20],
    }

    # All rows with wage_capped — title list
    out["capped_socs_full"] = capped_titles

    # Print as JSON for ingestion into the markdown report
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
