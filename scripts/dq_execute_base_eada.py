"""Execute the 13 DQ rules for base.eada against the live Iceberg snapshot.

Loads base.eada and base.ipeds_finance from the silver warehouse and bronze.eada
from the bronze warehouse via SqlCatalog at data/catalog/catalog.db, materializes
each into DuckDB at the schema-qualified name used by rule SQL, then runs each
rule's SQL verbatim.

Writes a JSON+MD scorecard pair to governance/dq-scorecards/.
Mirrors the bronze.ipeds_finance DQ execution pattern (scripts/dq_execute_ipeds_finance.py).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
from brightsmith.infra.iceberg_setup import get_catalog

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RULES_FILE = PROJECT_ROOT / "governance" / "dq-rules" / "base-eada.json"
SCORECARD_DIR = PROJECT_ROOT / "governance" / "dq-scorecards"
RESULTS_DIR = PROJECT_ROOT / "governance" / "dq-results"
SCORECARD_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

SILVER_WAREHOUSE = PROJECT_ROOT / "data" / "silver" / "iceberg_warehouse"
BRONZE_WAREHOUSE = PROJECT_ROOT / "data" / "bronze" / "iceberg_warehouse"
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"


def main() -> int:
    rules_doc = json.loads(RULES_FILE.read_text())
    rules = rules_doc["rules"]
    primary_table = rules_doc["table"]  # "base.eada"

    # Load base.eada from silver warehouse.
    print(f"Loading {primary_table} from silver Iceberg warehouse...")
    silver_catalog = get_catalog(SILVER_WAREHOUSE, CATALOG_PATH)
    base_eada_table = silver_catalog.load_table("base.eada")
    snap = base_eada_table.current_snapshot()
    snapshot_id = snap.snapshot_id if snap else None
    print(f"base.eada snapshot id: {snapshot_id}")

    base_eada_arrow = base_eada_table.scan().to_arrow()
    base_eada_row_count = base_eada_arrow.num_rows
    base_eada_columns = [f.name for f in base_eada_arrow.schema]
    print(f"base.eada loaded: {base_eada_row_count} rows, {len(base_eada_columns)} cols")

    # Load base.ipeds_finance from silver warehouse (for BSE-EAD-013 cross-source check).
    print("Loading base.ipeds_finance from silver Iceberg warehouse...")
    base_ipf_table = silver_catalog.load_table("base.ipeds_finance")
    base_ipf_arrow = base_ipf_table.scan().to_arrow()
    print(f"base.ipeds_finance loaded: {base_ipf_arrow.num_rows} rows")

    # Load bronze.eada from bronze warehouse (for BSE-EAD-001 row count conservation).
    print("Loading bronze.eada from bronze Iceberg warehouse...")
    bronze_catalog = get_catalog(BRONZE_WAREHOUSE, CATALOG_PATH)
    bronze_eada_table = bronze_catalog.load_table("bronze.eada")
    bronze_eada_arrow = bronze_eada_table.scan().to_arrow()
    print(f"bronze.eada loaded: {bronze_eada_arrow.num_rows} rows")

    # Materialize all three into DuckDB at the schema-qualified names rules use.
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA IF NOT EXISTS base")
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")

    con.register("__arrow_base_eada", base_eada_arrow)
    con.execute("CREATE TABLE base.eada AS SELECT * FROM __arrow_base_eada")
    con.unregister("__arrow_base_eada")

    con.register("__arrow_base_ipf", base_ipf_arrow)
    con.execute("CREATE TABLE base.ipeds_finance AS SELECT * FROM __arrow_base_ipf")
    con.unregister("__arrow_base_ipf")

    con.register("__arrow_bronze_eada", bronze_eada_arrow)
    con.execute("CREATE TABLE bronze.eada AS SELECT * FROM __arrow_bronze_eada")
    con.unregister("__arrow_bronze_eada")

    results = []
    p0_total = p0_pass = p1_total = p1_pass = p2_total = p2_pass = 0
    overall_pass = True
    p0_failed = False  # P0 fail STOPS

    for rule in rules:
        rid = rule["rule_id"]
        prio = rule["priority"]
        sql = rule["sql"]
        threshold = rule["threshold"]
        print(f"\n>>> {rid} [{prio}] {rule['name']}")
        print(f"    SQL: {sql[:120]}...")
        try:
            cur = con.execute(sql)
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchall()
        except Exception as exc:
            print(f"    ERROR: {exc}")
            results.append({
                "rule_id": rid,
                "name": rule["name"],
                "priority": prio,
                "dimension": rule["dimension"],
                "threshold": threshold,
                "actual": None,
                "passed": False,
                "error": str(exc),
            })
            overall_pass = False
            if prio == "P0":
                p0_total += 1
                p0_failed = True
            elif prio == "P1":
                p1_total += 1
            else:
                p2_total += 1
            continue

        passed = False
        actual: object = None
        if threshold == "result = 0":
            if rows and len(rows) == 1:
                actual = rows[0][0]
                passed = actual == 0
        elif threshold == "result_count = 0":
            actual = len(rows)
            passed = actual == 0
        else:
            actual = len(rows)
            passed = actual == 0

        sample = [list(r) for r in rows[:5]]
        results.append({
            "rule_id": rid,
            "name": rule["name"],
            "priority": prio,
            "dimension": rule["dimension"],
            "threshold": threshold,
            "actual": actual,
            "passed": bool(passed),
            "result_columns": cols,
            "row_count_returned": len(rows),
            "sample_rows": sample,
        })
        print(f"    -> actual={actual}, passed={passed}")

        if prio == "P0":
            p0_total += 1
            if passed:
                p0_pass += 1
            else:
                overall_pass = False
                p0_failed = True
        elif prio == "P1":
            p1_total += 1
            if passed:
                p1_pass += 1
            else:
                overall_pass = False
        else:
            p2_total += 1
            if passed:
                p2_pass += 1
            else:
                overall_pass = False

        # P0 fail STOPS — but we continue executing remaining rules
        # so the human can see the full diagnostic picture in the scorecard.
        # The gate decision uses p0_failed.
        if p0_failed and prio == "P0" and not passed:
            print(f"    !!! P0 GATE FAILURE: {rid} did not pass; continuing to collect full diagnostic.")

    ts = datetime.now(timezone.utc)
    iso = ts.strftime("%Y%m%dT%H%M%SZ")
    iso_full = ts.isoformat()

    summary = {
        "overall_pass": overall_pass,
        "p0_total": p0_total,
        "p0_pass": p0_pass,
        "p0_fail": p0_total - p0_pass,
        "p1_total": p1_total,
        "p1_pass": p1_pass,
        "p1_fail": p1_total - p1_pass,
        "p2_total": p2_total,
        "p2_pass": p2_pass,
        "p2_fail": p2_total - p2_pass,
        "p0_gate_blocking": (p0_total - p0_pass) > 0,
    }

    payload = {
        "spec": rules_doc["spec"],
        "table": primary_table,
        "snapshot_id": str(snapshot_id),
        "row_count": base_eada_row_count,
        "rules_file": "governance/dq-rules/base-eada.json",
        "executed_at": iso_full,
        "executed_by": "@dq-engineer",
        "rule_count": len(rules),
        "summary": summary,
        "results": results,
    }

    json_path = SCORECARD_DIR / f"base-eada-{iso}.json"
    md_path = SCORECARD_DIR / f"base-eada-{iso}.md"
    results_json_path = RESULTS_DIR / f"base-eada-{iso}.json"

    json_path.write_text(json.dumps(payload, indent=2, default=str))
    results_json_path.write_text(json.dumps(payload, indent=2, default=str))

    md_lines = [
        "# DQ Scorecard - base-eada",
        "",
        f"- **Spec:** `{rules_doc['spec']}`",
        f"- **Table:** `{primary_table}`",
        f"- **Snapshot:** `{snapshot_id}`",
        f"- **Rules file:** `governance/dq-rules/base-eada.json`",
        f"- **Executed at:** {iso_full}",
        f"- **Executed by:** @dq-engineer",
        f"- **Row count:** {base_eada_row_count}",
        "",
        "## Summary",
        "",
        f"- **Overall pass:** {summary['overall_pass']}",
        f"- **P0 gate:** {'PASS' if summary['p0_pass'] == summary['p0_total'] else 'FAIL'} "
        f"({summary['p0_pass']}/{summary['p0_total']} passed)",
        f"- **P1:** {summary['p1_pass']}/{summary['p1_total']} passed",
        "",
        "## Results",
        "",
        "| rule_id | priority | dimension | status | expected | actual | notes |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        actual_str = (
            f"{r['actual']} rows" if r["threshold"] == "result_count = 0" else str(r["actual"])
        )
        md_lines.append(
            f"| {r['rule_id']} | {r['priority']} | {r['dimension']} | {status} | "
            f"{r['threshold']} | {actual_str} | {r['name']} |"
        )
    md_lines.append("")
    md_lines.append("## Gate Decision")
    md_lines.append("")
    if summary["p0_gate_blocking"]:
        md_lines.append(
            f"**base.eada is BLOCKED.** {summary['p0_fail']} P0 rule(s) failed. "
            "Escalate to @governance-reviewer; chaos-monkey is GATED."
        )
    else:
        md_lines.append(
            "**base.eada is CLEARED for chaos-monkey hardening.** "
            f"All {len(rules)} rules pass; no P0 violations."
        )
    md_path.write_text("\n".join(md_lines) + "\n")

    print(f"\nScorecard JSON: {json_path}")
    print(f"Scorecard MD:   {md_path}")
    print(f"Results JSON:   {results_json_path}")
    print(f"\nSummary: {json.dumps(summary, indent=2)}")

    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
