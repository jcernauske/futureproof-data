"""v1.4 §5: drop and re-create base.ipeds_finance with the new
endowment_value_flag column.

The append-only promote pattern has no schema-evolution hook — re-running
``promote_ipeds_finance_base`` against the v1.3-shaped table produces 0
rows (all 2,675 record_ids already exist).  v1.4 adds an additive nullable
column at field-id 16; the cleanest path is drop + re-create with the new
schema.

Idempotent.  Re-running is a no-op if the table already has 16 fields.
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
from silver.ipeds_finance_base import (  # noqa: E402
    BASE_NAMESPACE,
    BASE_TABLE_NAME,
    promote_ipeds_finance_base,
)


def main() -> int:
    base_warehouse = PROJECT_ROOT / "data" / "silver" / "iceberg_warehouse"
    catalog = get_catalog(base_warehouse, brightsmith.config.CATALOG_PATH)
    fqn = f"{BASE_NAMESPACE}.{BASE_TABLE_NAME}"

    # Check current schema.
    table = catalog.load_table(fqn)
    field_count = len(table.schema().fields)
    print(f"Current {fqn} schema field count: {field_count}")

    if field_count < 16:
        print(f"v1.3 schema detected — dropping {fqn} and re-creating with v1.4 schema.")
        catalog.drop_table(fqn)
        print(f"Dropped {fqn}.  Re-running promote with v1.4 schema...")
        result = promote_ipeds_finance_base(project_dir=PROJECT_ROOT)
        print(f"Promote result: {result}")

        # Re-read for the new snapshot id.
        table = catalog.load_table(fqn)
        snapshots = list(table.metadata.snapshots)
        if snapshots:
            print(f"NEW base snapshot id: {snapshots[-1].snapshot_id}")
        print(f"NEW base schema field count: {len(table.schema().fields)}")
    else:
        print("Schema already has 16+ fields; nothing to do.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
