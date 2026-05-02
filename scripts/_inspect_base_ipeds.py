"""Inspect the current base.ipeds_finance table for v1.4 promote planning."""

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
    catalog = get_catalog(base_warehouse, brightsmith.config.CATALOG_PATH)
    table = catalog.load_table("base.ipeds_finance")
    print("Schema fields:")
    for f in table.schema().fields:
        print(f"  field_id={f.field_id} name={f.name} type={f.field_type} required={f.required}")
    rows = read_with_duckdb(table)
    print("Row count:", len(rows))
    print("First row keys:", sorted(rows[0].keys()))
    print("endowment_value_flag in row 0?:", "endowment_value_flag" in rows[0])
    if "endowment_value_flag" in rows[0]:
        flag_counts: dict[object, int] = {}
        for r in rows:
            v = r.get("endowment_value_flag")
            flag_counts[v] = flag_counts.get(v, 0) + 1
        print("flag_counts:", sorted(flag_counts.items(), key=lambda x: str(x[0])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
