"""Isolated probe: duplicate geo_fips while preserving row count = 51.

Inject: drop Wyoming (56), then duplicate Texas (48). Net row count = 51.
Goal: confirm whether a pure uniqueness violation (two rows with fips=48)
is detected when volume is unchanged.
"""

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
import copy


def main():
    safety_check()
    rows, schema = load_source_rows()

    # Drop Wyoming
    rows = [r for r in rows if r["geo_fips"] != "56"]
    # Duplicate Texas
    tx = next(r for r in rows if r["geo_fips"] == "48")
    rows.append(copy.deepcopy(tx))
    print(f"row count = {len(rows)}")

    arrow = rows_to_arrow(rows, schema)
    pq = write_shadow_parquet(arrow, 101)
    register_shadow(pq)
    res = run_dq_rules_shadow()
    print(
        f"total={res.get('rules_total')} "
        f"passed={res.get('rules_passed')} "
        f"failed={res.get('rules_failed')}"
    )
    for r in res.get("results", []):
        if not r.get("passed"):
            print(f"  FIRED: {r.get('rule_id')} value={r.get('raw_value')}")
    cleanup_shadow()


if __name__ == "__main__":
    main()
