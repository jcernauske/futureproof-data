"""Isolated probes to map each requested scenario to a single rule id.

Runs each scenario ALONE (not bundled) and reports which rule(s) fire.
This is the source-of-truth for the per-scenario caught/missed matrix
in the chaos report.
"""

import copy
import sys
from pathlib import Path

PROJECT_ROOT = Path("/Users/jcernauske/code/bright/futureproof-data")
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, "/Users/jcernauske/code/bright/brightsmith/src")

from brightsmith.config import configure  # noqa: E402
configure(project_root=str(PROJECT_ROOT), project_name="brightsmith")

sys.path.insert(0, str(PROJECT_ROOT / "governance/chaos-manifests"))
from bea_rpp_chaos_runner import (  # noqa: E402
    load_source_rows,
    rows_to_arrow,
    write_shadow_parquet,
    register_shadow,
    run_dq_rules_shadow,
    cleanup_shadow,
    safety_check,
)


def _run(label, mutate):
    rows, schema = load_source_rows()
    mutate(rows)
    arrow = rows_to_arrow(rows, schema)
    pq = write_shadow_parquet(arrow, 900)
    register_shadow(pq)
    res = run_dq_rules_shadow()
    fired = [r["rule_id"] for r in res.get("results", []) if not r.get("passed")]
    print(f"  [{label}] fired={fired}  rows={len(rows)}")
    cleanup_shadow()
    return fired


def main():
    safety_check()
    results = {}

    # S1a: drop WY (row count 50, WY missing)
    def drop_wy(rows):
        idx = next(i for i, r in enumerate(rows) if r["geo_fips"] == "56")
        rows.pop(idx)
    results["S1a_drop_wyoming_only"] = _run("S1a drop WY only", drop_wy)

    # S1b: duplicate TX only (row count 52)
    def dup_tx(rows):
        tx = next(r for r in rows if r["geo_fips"] == "48")
        rows.append(copy.deepcopy(tx))
    results["S1b_duplicate_texas_only"] = _run("S1b duplicate TX only", dup_tx)

    # S2a: CA = 200
    def ca_high(rows):
        idx = next(i for i, r in enumerate(rows) if r["geo_fips"] == "06")
        rows[idx]["rpp_all_items"] = 200.0
    results["S2a_ca_200"] = _run("S2a CA=200", ca_high)

    # S2b: CA = -10
    def ca_neg(rows):
        idx = next(i for i, r in enumerate(rows) if r["geo_fips"] == "06")
        rows[idx]["rpp_all_items"] = -10.0
    results["S2b_ca_neg10"] = _run("S2b CA=-10", ca_neg)

    # S3: null rpp NV
    def null_nv(rows):
        idx = next(i for i, r in enumerate(rows) if r["geo_fips"] == "32")
        rows[idx]["rpp_all_items"] = None
    results["S3_null_rpp_nv"] = _run("S3 null rpp NV", null_nv)

    # S4: inject duplicate FIPS OR (geo_fips=41 appears twice, row count 52)
    def dup_or(rows):
        src = next(r for r in rows if r["geo_fips"] == "41")
        dup = copy.deepcopy(src)
        dup["geo_name"] = "Oregon (duplicate)"
        dup["rpp_all_items"] = 99.9
        rows.append(dup)
    results["S4_duplicate_fips_or"] = _run("S4 duplicate fips OR", dup_or)

    # S4b: duplicate fips with row count preserved (drop WY, add duplicate OR)
    def dup_fips_same_count(rows):
        idx = next(i for i, r in enumerate(rows) if r["geo_fips"] == "56")
        rows.pop(idx)
        src = next(r for r in rows if r["geo_fips"] == "41")
        dup = copy.deepcopy(src)
        dup["geo_name"] = "Oregon (duplicate)"
        dup["rpp_all_items"] = 99.9
        rows.append(dup)
    results["S4b_duplicate_fips_row_count_51"] = _run("S4b dup fips, count preserved", dup_fips_same_count)

    # S5: stale data_year
    def stale_year(rows):
        idx = next(i for i, r in enumerate(rows) if r["geo_fips"] == "30")
        rows[idx]["data_year"] = 2023
    results["S5_stale_year_2023"] = _run("S5 stale year 2023", stale_year)

    # S6: CA stale value (95.0 plausible but wrong)
    def ca_stale(rows):
        idx = next(i for i, r in enumerate(rows) if r["geo_fips"] == "06")
        rows[idx]["rpp_all_items"] = 95.0
    results["S6_ca_stale_95"] = _run("S6 CA=95", ca_stale)

    # S7: AR stale value (100.0)
    def ar_stale(rows):
        idx = next(i for i, r in enumerate(rows) if r["geo_fips"] == "05")
        rows[idx]["rpp_all_items"] = 100.0
    results["S7_ar_stale_100"] = _run("S7 AR=100", ar_stale)

    # S8: drop WY (= S1a)
    # S9: drop DC
    def drop_dc(rows):
        idx = next(i for i, r in enumerate(rows) if r["geo_fips"] == "11")
        rows.pop(idx)
    results["S9_drop_dc"] = _run("S9 drop DC", drop_dc)

    # S10: bad source_method
    def bad_method(rows):
        idx = next(i for i, r in enumerate(rows) if r["geo_fips"] == "48")
        rows[idx]["source_method"] = "unknown"
    results["S10_bad_source_method"] = _run("S10 bad source_method", bad_method)

    # S11: unit error x10
    def unit_x10(rows):
        for r in rows:
            if r.get("rpp_all_items") is not None:
                r["rpp_all_items"] = r["rpp_all_items"] * 10.0
    results["S11_unit_error_x10"] = _run("S11 x10 unit error", unit_x10)

    # S12: negative control — IA/OK name swap
    def swap_ia_ok(rows):
        ia = next(i for i, r in enumerate(rows) if r["geo_fips"] == "19")
        ok = next(i for i, r in enumerate(rows) if r["geo_fips"] == "40")
        rows[ia]["geo_name"], rows[ok]["geo_name"] = rows[ok]["geo_name"], rows[ia]["geo_name"]
    results["S12_neg_control_swap_ia_ok"] = _run("S12 neg ctrl swap IA/OK", swap_ia_ok)

    print("\n====== PROBE SUMMARY ======")
    for k, v in results.items():
        print(f"{k:45s} -> {v}")


if __name__ == "__main__":
    main()
