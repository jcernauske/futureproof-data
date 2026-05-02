"""v1.4 §5 verification — base.ipeds_finance invariant checks.

Asserts:
  - BSE-IPF-001 conservation: row count == bronze row count == 2,675.
  - BSE-IPF-018 preview: every row's endowment_value_flag matches bronze
    on UNITID (passthrough fidelity).
  - BSE-IPF-020 preview: A↔NULL coupling holds at base.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import brightsmith.config  # noqa: E402

brightsmith.config.configure(
    project_root=PROJECT_ROOT,
    require_human_approval=False,
)

from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb  # noqa: E402


def main() -> int:
    bronze_warehouse = PROJECT_ROOT / "data" / "bronze" / "iceberg_warehouse"
    base_warehouse = PROJECT_ROOT / "data" / "silver" / "iceberg_warehouse"

    bronze_catalog = get_catalog(bronze_warehouse, brightsmith.config.CATALOG_PATH)
    base_catalog = get_catalog(base_warehouse, brightsmith.config.CATALOG_PATH)

    bronze_rows = read_with_duckdb(bronze_catalog.load_table("bronze.ipeds_finance"))
    base_rows = read_with_duckdb(base_catalog.load_table("base.ipeds_finance"))

    print(f"bronze row count: {len(bronze_rows)}")
    print(f"base   row count: {len(base_rows)}")

    # BSE-IPF-001 conservation
    assert len(bronze_rows) == len(base_rows), "row count mismatch"
    assert len(base_rows) == 2_675, f"expected 2,675, got {len(base_rows)}"
    print("PASS: BSE-IPF-001 conservation (row count == bronze == 2,675)")

    # BSE-IPF-018 preview: passthrough fidelity
    bronze_by_unitid = {r["unitid"]: r["endowment_value_flag"] for r in bronze_rows}
    base_by_unitid = {r["unitid"]: r["endowment_value_flag"] for r in base_rows}
    mismatches = [
        (u, bronze_by_unitid[u], base_by_unitid.get(u))
        for u in bronze_by_unitid
        if base_by_unitid.get(u) != bronze_by_unitid[u]
    ]
    assert not mismatches, f"BSE-IPF-018 mismatches: {mismatches[:5]}"
    print(f"PASS: BSE-IPF-018 passthrough fidelity (0 mismatches across {len(bronze_by_unitid)} UNITIDs)")

    # BSE-IPF-020 preview: A↔NULL coupling
    # (1) every flag = 'A' row has endowment_value IS NULL.
    a_with_value = [
        r for r in base_rows
        if r["endowment_value_flag"] == "A" and r["endowment_value"] is not None
    ]
    assert not a_with_value, f"A-flagged rows with non-null endowment: {len(a_with_value)}"

    # (2) every F1A/F2 row with endowment_value IS NULL has flag = 'A'.
    f1a_f2_null_no_a = [
        r for r in base_rows
        if r["report_form"] in ("F1A", "F2")
        and r["endowment_value"] is None
        and r["endowment_value_flag"] != "A"
    ]
    assert not f1a_f2_null_no_a, (
        f"F1A/F2 NULL-value rows lacking A flag: {len(f1a_f2_null_no_a)} "
        f"(sample: {f1a_f2_null_no_a[:3]})"
    )
    print("PASS: BSE-IPF-020 A↔NULL coupling (both directions hold)")

    # Form-form-by-flag breakdown (sanity)
    from collections import Counter
    breakdown: dict[tuple[str, object], int] = Counter()
    for r in base_rows:
        breakdown[(r["report_form"], r["endowment_value_flag"])] += 1
    print("Form × flag breakdown:")
    for k, v in sorted(breakdown.items(), key=lambda x: (x[0][0], str(x[0][1]))):
        print(f"  {k}: {v}")

    # Spot-check Stanford
    stanford = next(r for r in base_rows if r["unitid"] == 243744)
    print(f"Stanford UNITID=243744: flag={stanford['endowment_value_flag']!r} "
          f"value={stanford['endowment_value']}")
    assert stanford["endowment_value_flag"] == "R"
    assert stanford["endowment_value"] is not None
    print("PASS: Stanford spot check (flag='R', value populated)")

    print("\nALL v1.4 BASE INVARIANT CHECKS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
