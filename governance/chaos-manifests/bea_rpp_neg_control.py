"""Isolated negative-control check: swap IA and OK geo_name ONLY.

Expected: zero DQ rules fire (swap doesn't change any value other than
geo_name, and two states with the same rpp_all_items should not be
considered a uniqueness violation).
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path("/Users/jcernauske/code/bright/futureproof-data")
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, "/Users/jcernauske/code/bright/brightsmith/src")

from brightsmith.config import configure  # noqa: E402
configure(project_root=str(PROJECT_ROOT), project_name="brightsmith")

# Re-use helpers from the cycle runner
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


def main():
    safety_check()
    rows, schema = load_source_rows()

    ia = next(i for i, r in enumerate(rows) if r["geo_fips"] == "19")
    ok = next(i for i, r in enumerate(rows) if r["geo_fips"] == "40")
    rows[ia]["geo_name"], rows[ok]["geo_name"] = rows[ok]["geo_name"], rows[ia]["geo_name"]

    arrow = rows_to_arrow(rows, schema)
    pq = write_shadow_parquet(arrow, 99)
    register_shadow(pq)
    res = run_dq_rules_shadow()
    print(
        f"run={res.get('run_id')} total={res.get('rules_total')} "
        f"passed={res.get('rules_passed')} failed={res.get('rules_failed')}"
    )
    for r in res.get("results", []):
        if not r.get("passed"):
            print(f"  FIRED: {r.get('rule_id')} value={r.get('raw_value')}")
    cleanup_shadow()
    return res.get("rules_failed", -1)


if __name__ == "__main__":
    failures = main()
    if failures == 0:
        print("NEGATIVE CONTROL PASSED: zero rules fired (as expected)")
    else:
        print(f"NEGATIVE CONTROL FAILED: {failures} rules fired (expected 0)")
