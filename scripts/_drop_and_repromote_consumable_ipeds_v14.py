"""v1.4 §6: drop and re-create consumable.ipeds_finance_profile with the
new endowment_value_provenance and source_load_date columns plus the
system-administrative-office filter.

Idempotent.  Re-running is a no-op if the table already has 17 fields.
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

from brightsmith.infra.iceberg_setup import get_catalog  # noqa: E402
from gold.ipeds_finance_profile import (  # noqa: E402
    CONSUMABLE_NAMESPACE,
    CONSUMABLE_TABLE_NAME,
    transform,
)


def main() -> int:
    consumable_warehouse = PROJECT_ROOT / "data" / "gold" / "iceberg_warehouse"
    catalog = get_catalog(consumable_warehouse, brightsmith.config.CATALOG_PATH)
    fqn = f"{CONSUMABLE_NAMESPACE}.{CONSUMABLE_TABLE_NAME}"

    table = catalog.load_table(fqn)
    field_count = len(table.schema().fields)
    print(f"Current {fqn} schema field count: {field_count}")

    if field_count < 17:
        print(f"v1.3 schema detected — dropping {fqn} and re-creating with v1.4 schema.")
        catalog.drop_table(fqn)
        print(f"Dropped {fqn}.  Re-running promote with v1.4 schema...")
        result = transform(project_dir=PROJECT_ROOT)
        print(f"Promote result: {result}")

        table = catalog.load_table(fqn)
        snapshots = list(table.metadata.snapshots)
        if snapshots:
            print(f"NEW consumable snapshot id: {snapshots[-1].snapshot_id}")
        print(f"NEW consumable schema field count: {len(table.schema().fields)}")
    else:
        print("Schema already has 17+ fields; nothing to do.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
