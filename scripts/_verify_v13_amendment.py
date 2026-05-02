"""v1.3 amendment verification — local one-shot."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import brightsmith.config  # noqa: E402

brightsmith.config.configure(project_root=PROJECT_ROOT, require_human_approval=False)

from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb  # noqa: E402


def main() -> int:
    cw = PROJECT_ROOT / "data" / "gold" / "iceberg_warehouse"
    catalog = get_catalog(cw, brightsmith.config.CATALOG_PATH)
    table = catalog.load_table("consumable.ipeds_finance_profile")
    rows = read_with_duckdb(table)
    print(f"consumable rows: {len(rows)}")

    spot_ids = {
        243744: "Stanford",
        166027: "Harvard",
        166683: "MIT",
        132903: "Berea (small teaching)",
        217615: "Brown",
    }
    by_uid = {r["unitid"]: r for r in rows}
    for uid, name in spot_ids.items():
        if uid in by_uid:
            r = by_uid[uid]
            print(
                f"  {name} (UNITID {uid}): SURVIVES — "
                f"instr={r.get('instruction_expenses')}, "
                f"fte={r.get('total_fte_enrollment')}, "
                f"prov={r.get('endowment_value_provenance')}, "
                f"src_load={r.get('source_load_date')}"
            )
        else:
            print(f"  {name} (UNITID {uid}): NOT in consumable")

    v13_leaks = [117681, 195827, 438665, 222497, 242671, 166665, 454218, 428453, 144777]
    print("\nv1.3 named-leak exclusion check:")
    for uid in v13_leaks:
        excluded = uid not in by_uid
        status = "EXCLUDED" if excluded else "STILL PRESENT (FAIL)"
        print(f"  UNITID {uid}: {status}")

    print(
        f"  UNITID 242060 (Sistema Universitario): "
        f"{'EXCLUDED' if 242060 not in by_uid else 'STILL PRESENT (FAIL)'}"
    )

    sample = rows[0]
    print(f"\nSample row keys: {sorted(sample.keys())}")
    print(f"  endowment_value_provenance present: {'endowment_value_provenance' in sample}")
    print(f"  source_load_date present: {'source_load_date' in sample}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
