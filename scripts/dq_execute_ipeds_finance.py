"""Execute the 14 DQ rules for bronze.ipeds_finance against the live Iceberg snapshot.

Loads the table via Brightsmith's get_catalog() (SqlCatalog at
data/bronze/iceberg_warehouse/catalog.db), materializes the entire snapshot
into DuckDB as bronze.ipeds_finance, then runs each rule's SQL verbatim.

Writes a JSON+MD scorecard pair to governance/dq-scorecards/.
Mirrors the bronze.eada DQ execution pattern.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import brightsmith.config
from brightsmith.infra.iceberg_setup import get_catalog

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RULES_FILE = PROJECT_ROOT / "governance" / "dq-rules" / "raw-ipeds-finance.json"
SCORECARD_DIR = PROJECT_ROOT / "governance" / "dq-scorecards"
RESULTS_DIR = PROJECT_ROOT / "governance" / "dq-results"
SCORECARD_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def main() -> int:
    rules_doc = json.loads(RULES_FILE.read_text())
    rules = rules_doc["rules"]
    table_name = rules_doc["table"]  # "bronze.ipeds_finance"

    print(f"Loading {table_name} from Iceberg...")
    catalog = get_catalog(
        brightsmith.config.WAREHOUSE_PATH,
        brightsmith.config.CATALOG_PATH,
    )
    iceberg_table = catalog.load_table(table_name)
    snap = iceberg_table.current_snapshot()
    snapshot_id = snap.snapshot_id if snap else None
    print(f"Snapshot id: {snapshot_id}")

    arrow_table = iceberg_table.scan().to_arrow()
    row_count = arrow_table.num_rows
    columns = [f.name for f in arrow_table.schema]
    print(f"Loaded {row_count} rows, columns: {columns}")

    # Materialize into DuckDB at the schema-qualified name used by rule SQL.
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    con.register("__arrow_ipf", arrow_table)
    con.execute("CREATE TABLE bronze.ipeds_finance AS SELECT * FROM __arrow_ipf")
    con.unregister("__arrow_ipf")

    results = []
    p0_total = p0_pass = p1_total = p1_pass = 0
    overall_pass = True

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
            elif prio == "P1":
                p1_total += 1
            continue

        # Two threshold flavors: 'result = 0' (single-value) or 'result_count = 0' (rowset).
        passed = False
        actual: object = None
        if threshold == "result = 0":
            # Expect exactly 1 row with one column whose value should be 0
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
        elif prio == "P1":
            p1_total += 1
            if passed:
                p1_pass += 1
            else:
                overall_pass = False

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
        "p0_gate_blocking": (p0_total - p0_pass) > 0,
    }

    payload = {
        "spec": rules_doc["spec"],
        "table": table_name,
        "snapshot_id": str(snapshot_id),
        "row_count": row_count,
        "rules_file": "governance/dq-rules/raw-ipeds-finance.json",
        "executed_at": iso_full,
        "executed_by": "@dq-engineer",
        "rule_count": len(rules),
        "summary": summary,
        "results": results,
    }

    json_path = SCORECARD_DIR / f"raw-ipeds-finance-{iso}.json"
    md_path = SCORECARD_DIR / f"raw-ipeds-finance-{iso}.md"
    results_json_path = RESULTS_DIR / f"raw-ipeds-finance-{iso}.json"

    json_path.write_text(json.dumps(payload, indent=2, default=str))
    results_json_path.write_text(json.dumps(payload, indent=2, default=str))

    md_lines = [
        f"# DQ Scorecard - raw-ipeds-finance",
        "",
        f"- **Spec:** `{rules_doc['spec']}`",
        f"- **Table:** `{table_name}`",
        f"- **Snapshot:** `{snapshot_id}`",
        f"- **Rules file:** `governance/dq-rules/raw-ipeds-finance.json`",
        f"- **Executed at:** {iso_full}",
        f"- **Executed by:** @dq-engineer",
        f"- **Row count:** {row_count}",
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
            f"**bronze.ipeds_finance is BLOCKED.** {summary['p0_fail']} P0 rule(s) failed. "
            "Escalate to @governance-reviewer; chaos-monkey is GATED."
        )
    else:
        md_lines.append(
            "**bronze.ipeds_finance is CLEARED for chaos-monkey hardening.** "
            f"All {len(rules)} rules pass; no P0 violations."
        )
    md_path.write_text("\n".join(md_lines))

    print(f"\nScorecard JSON: {json_path}")
    print(f"Scorecard MD:   {md_path}")
    print(f"Results JSON:   {results_json_path}")
    print(f"\nSummary: {json.dumps(summary, indent=2)}")

    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
