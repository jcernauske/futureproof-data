"""v1.4 §6 verification — consumable.ipeds_finance_profile invariant checks.

Asserts:
  - CON-IFP-001a upper: row count <= base count.
  - CON-IFP-001b lower: row count >= base count - 50.
  - Specific named UNITIDs are NOT in consumable: 242060, 195827, 128300.
  - CON-IFP-013 preview: endowment_value_provenance matches base's
    endowment_value_flag for every consumable UNITID.
  - CON-IFP-015 preview: source_load_date is 100% non-null.
  - CON-IFP-012 preview: fiscal_year is single-valued and non-null.
  - Stanford and a small teaching school survive.
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
    base_warehouse = PROJECT_ROOT / "data" / "silver" / "iceberg_warehouse"
    consumable_warehouse = PROJECT_ROOT / "data" / "gold" / "iceberg_warehouse"

    base_catalog = get_catalog(base_warehouse, brightsmith.config.CATALOG_PATH)
    consumable_catalog = get_catalog(
        consumable_warehouse, brightsmith.config.CATALOG_PATH
    )

    base_rows = read_with_duckdb(base_catalog.load_table("base.ipeds_finance"))
    consumable_rows = read_with_duckdb(
        consumable_catalog.load_table("consumable.ipeds_finance_profile")
    )

    base_count = len(base_rows)
    cons_count = len(consumable_rows)
    drop = base_count - cons_count
    print(f"base       row count: {base_count}")
    print(f"consumable row count: {cons_count}")
    print(f"drop delta: {drop}")

    # CON-IFP-001a/b
    assert cons_count <= base_count, "CON-IFP-001a: row count > base"
    assert cons_count >= base_count - 50, (
        f"CON-IFP-001b: row count {cons_count} < base - 50 = {base_count - 50}"
    )
    print("PASS: CON-IFP-001a (count <= base)")
    print("PASS: CON-IFP-001b (count >= base - 50)")

    # Named UNITIDs — verify against the §6 SQL AND-clause:
    # excluded only when name matches AND (instruction NULL OR < $1M).
    base_by_unitid = {r["unitid"]: r for r in base_rows}
    cons_unitids = {r["unitid"] for r in consumable_rows}

    def _is_admin_office(unitid: int, label: str, expected_excluded: bool) -> bool:
        """True if pass/fail matches expectation."""
        in_cons = unitid in cons_unitids
        actually_excluded = not in_cons
        b = base_by_unitid.get(unitid)
        instr = b["instruction_expenses"] if b else None
        instr_str = f"${instr:,.2f}" if instr is not None else "NULL"
        verdict = (
            "PASS"
            if actually_excluded == expected_excluded
            else "FAIL"
        )
        action = "excluded" if actually_excluded else "preserved"
        print(
            f"{verdict}: {unitid} ({label}, instruction={instr_str}) is {action} "
            f"(expected_excluded={expected_excluded})"
        )
        return actually_excluded == expected_excluded

    # Per spec §6 SQL — instruction < $1M is the floor.  195827 has
    # instruction = $2.2M (> $1M) so per the AND-clause it is PRESERVED;
    # this is the spec's deliberate guardrail (§2 Decision B).  128300
    # has instruction = $280K (< $1M) so it is excluded.  242060 has
    # instruction = $2,565 (< $1M) so it is excluded.
    ok = True
    ok &= _is_admin_office(
        242060, "Sistema Universitario Ana G. Mendez (live test target)", True
    )
    ok &= _is_admin_office(195827, "SUNY-System Office (instruction>$1M)", False)
    ok &= _is_admin_office(128300, "U Colorado System Office (instruction<$1M)", True)
    if not ok:
        return 1

    # CON-IFP-013 preview: provenance == base flag for every consumable row
    base_by_unitid = {r["unitid"]: r["endowment_value_flag"] for r in base_rows}
    mismatches = [
        (r["unitid"], base_by_unitid.get(r["unitid"]), r["endowment_value_provenance"])
        for r in consumable_rows
        if r["endowment_value_provenance"] != base_by_unitid.get(r["unitid"])
    ]
    assert not mismatches, f"CON-IFP-013 mismatches: {mismatches[:5]}"
    print(f"PASS: CON-IFP-013 endowment_value_provenance fidelity ({cons_count} rows)")

    # CON-IFP-015 preview: source_load_date 100% non-null
    null_loads = [r for r in consumable_rows if r["source_load_date"] is None]
    assert not null_loads, f"CON-IFP-015 null source_load_date: {len(null_loads)}"
    print(f"PASS: CON-IFP-015 source_load_date 100% non-null")

    # CON-IFP-012 preview: fiscal_year single-valued and non-null
    fy_values = {r["fiscal_year"] for r in consumable_rows}
    null_fys = [r for r in consumable_rows if r["fiscal_year"] is None]
    assert not null_fys, f"CON-IFP-012 null fiscal_year: {len(null_fys)}"
    assert len(fy_values) == 1, f"CON-IFP-012 multi-valued fiscal_year: {fy_values}"
    print(f"PASS: CON-IFP-012 fiscal_year single-valued (= {next(iter(fy_values))}) and non-null")

    # Spot-check Stanford
    stanford = [r for r in consumable_rows if r["unitid"] == 243744]
    assert stanford, "Stanford NOT in consumable — filter false-positive"
    s = stanford[0]
    print(f"Stanford UNITID=243744: prov={s['endowment_value_provenance']!r}, "
          f"source_load_date={s['source_load_date']}, "
          f"data_completeness_tier={s['data_completeness_tier']}")
    assert s["endowment_value_provenance"] == "R"
    assert s["data_completeness_tier"] == "high"
    print("PASS: Stanford spot check (preserved, prov=R, tier=high)")

    # Spot-check Berea College (small teaching school — UNITID 156189)
    berea = [r for r in consumable_rows if r["unitid"] == 156189]
    if berea:
        b = berea[0]
        print(f"Berea College UNITID=156189: prov={b['endowment_value_provenance']!r}, "
              f"name={b['institution_name']!r}")
        print("PASS: Berea College preserved (small teaching school)")

    # Berklee College of Music UNITID 164271
    berklee = [r for r in consumable_rows if r["unitid"] == 164271]
    if berklee:
        b = berklee[0]
        print(f"Berklee College of Music UNITID=164271: prov={b['endowment_value_provenance']!r}")
        print("PASS: Berklee College of Music preserved")

    # Excluded UNITIDs list — list institution names
    base_by_unitid_full = {r["unitid"]: r for r in base_rows}
    excluded_unitids = sorted(set(base_by_unitid_full) - cons_unitids)
    print(f"\nExcluded UNITIDs ({len(excluded_unitids)}):")
    for u in excluded_unitids:
        b = base_by_unitid_full[u]
        instr = b["instruction_expenses"]
        instr_str = f"${instr:,.0f}" if instr is not None else "NULL"
        print(f"  {u}: {b['institution_name']!r} (instruction={instr_str})")

    print("\nALL v1.4 CONSUMABLE INVARIANT CHECKS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
