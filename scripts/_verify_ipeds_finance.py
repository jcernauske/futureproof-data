"""Verification helper — read bronze.ipeds_finance + sanity checks.

Throwaway helper used after running scripts/ingest_ipeds_finance.py to
confirm the landed Iceberg table matches the smoke-run baseline.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import brightsmith.config

brightsmith.config.configure(
    project_root=PROJECT_ROOT,
    require_human_approval=False,
)

from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb


def main() -> int:
    catalog = get_catalog(
        brightsmith.config.WAREHOUSE_PATH,
        brightsmith.config.CATALOG_PATH,
    )
    table = catalog.load_table("bronze.ipeds_finance")
    rows = read_with_duckdb(table)
    print(f"TOTAL ROWS: {len(rows)}")

    form_counts: dict[str, int] = {}
    for r in rows:
        form_counts[r["report_form"]] = form_counts.get(r["report_form"], 0) + 1
    print(f"FORM MIX: {sorted(form_counts.items())}")

    print(f"COLUMNS: {sorted(rows[0].keys())}")

    # Stanford UNITID 243744 spot check — should be F2, FTE=18,219,
    # instruction=$2,380,695,000, institutional_support=$684,507,000,
    # endowment=$36,338,794,000 per pre-flight.
    stanford = [r for r in rows if r["unitid"] == 243744]
    if stanford:
        s = stanford[0]
        print("STANFORD UNITID=243744:")
        for k in (
            "unitid",
            "institution_name",
            "report_form",
            "fiscal_year",
            "instruction_expenses",
            "institutional_support_expenses",
            "endowment_value",
            "total_fte_enrollment",
            "source_method",
        ):
            print(f"  {k}: {s.get(k)}")

    # Berkeley spot check — F1A, FTE=45,872 per pre-flight.
    berkeley = [r for r in rows if r["unitid"] == 110635]
    if berkeley:
        b = berkeley[0]
        print(f"BERKELEY UNITID=110635: form={b['report_form']} FTE={b['total_fte_enrollment']}")

    # F3 endowment NULL check — every F3 row should have NULL endowment.
    f3 = [r for r in rows if r["report_form"] == "F3"]
    f3_endowment_nonnull = sum(1 for r in f3 if r["endowment_value"] is not None)
    print(f"F3 ENDOWMENT NON-NULL: {f3_endowment_nonnull}/{len(f3)}")

    # UNITID uniqueness (RAW-IPF-003 invariant)
    unique_unitids = {r["unitid"] for r in rows}
    print(f"UNIQUE UNITIDS: {len(unique_unitids)} (== row count: {len(unique_unitids) == len(rows)})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
