"""Execute Bronze DQ rules for raw-ingest-college-scorecard-institution against
the real Iceberg table (not in-memory CSV).

This is the Iceberg-backed sibling of scripts/dq_execute_csi.py. Instead of
re-downloading and re-parsing the 170MB CSV, it reads the persisted
bronze.college_scorecard_institution Iceberg table via
``read_with_duckdb(table)`` and materializes it into an in-memory DuckDB
view whose fully qualified name (``raw.college_scorecard_institution``)
matches what the DQ rule SQL expects. All 13 rules defined in
``governance/dq-rules/raw-ingest-college-scorecard-institution.json`` are
executed unchanged; their status field (approved/proposed) is ignored here
because the DQ rules were already locked at 23/23 in-memory earlier in the
spec lifecycle and this run only proves parity against the materialized
Iceberg table (closes Silver post-review advisory A3 for Bronze).

Usage:
    uv run python scripts/dq_execute_csi_iceberg.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import brightsmith.config

brightsmith.config.configure(
    project_root=PROJECT_ROOT,
    require_human_approval=False,
)

from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb


def load_rules() -> list[dict]:
    path = (
        PROJECT_ROOT
        / "governance"
        / "dq-rules"
        / "raw-ingest-college-scorecard-institution.json"
    )
    return json.loads(path.read_text())["rules"]


def _materialize_duckdb(rows: list[dict]) -> duckdb.DuckDBPyConnection:
    """Load Bronze rows into in-memory DuckDB as raw.college_scorecard_institution.

    The Bronze Iceberg table contains the framework metadata columns
    (ingested_at, source_url, source_method, load_date). We preserve them
    so that any DQ rule that references them (e.g. ingested_at >= ...)
    evaluates against real values.
    """
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA raw")

    col_defs = [
        "unitid BIGINT",
        "instnm VARCHAR",
        "stabbr VARCHAR",
        "control INTEGER",
        "preddeg INTEGER",
        "costt4_a DOUBLE",
        "costt4_p DOUBLE",
        "npt4_pub DOUBLE",
        "npt4_priv DOUBLE",
        "npt41_pub DOUBLE",
        "npt42_pub DOUBLE",
        "npt43_pub DOUBLE",
        "npt44_pub DOUBLE",
        "npt45_pub DOUBLE",
        "npt41_priv DOUBLE",
        "npt42_priv DOUBLE",
        "npt43_priv DOUBLE",
        "npt44_priv DOUBLE",
        "npt45_priv DOUBLE",
        "tuitionfee_in DOUBLE",
        "tuitionfee_out DOUBLE",
        "roomboard_on DOUBLE",
        "roomboard_off DOUBLE",
        "booksupply DOUBLE",
        "ingested_at TIMESTAMP",
        "source_url VARCHAR",
        "source_method VARCHAR",
        "load_date DATE",
    ]
    con.execute(
        f"CREATE TABLE raw.college_scorecard_institution ({', '.join(col_defs)})"
    )
    col_names = [c.split()[0] for c in col_defs]
    placeholders = ", ".join(["?"] * len(col_names))
    insert_sql = (
        f"INSERT INTO raw.college_scorecard_institution "
        f"({', '.join(col_names)}) VALUES ({placeholders})"
    )
    for r in rows:
        vals = [r.get(c) for c in col_names]
        con.execute(insert_sql, vals)
    return con


def execute_rules(
    con: duckdb.DuckDBPyConnection, rules: list[dict]
) -> tuple[list[dict], list[str]]:
    results: list[dict] = []
    p0_failures: list[str] = []
    for rule in rules:
        rid = rule["rule_id"]
        name = rule["name"]
        priority = rule["priority"]
        sql = rule["sql"]
        threshold = rule["threshold"].replace(" ", "")

        try:
            res = con.execute(sql).fetchall()
            if threshold.startswith("result=") or threshold.startswith("result<="):
                actual = int(res[0][0]) if res else 0
            else:
                actual = len(res)

            if threshold == "result=0":
                passed = actual == 0
            elif threshold == "result_count=0":
                passed = actual == 0
            elif threshold.startswith("result_count<="):
                passed = actual <= int(threshold.split("<=", 1)[1])
            elif threshold.startswith("result<="):
                passed = actual <= int(threshold.split("<=", 1)[1])
            else:
                passed = False

            status = "PASS" if passed else "FAIL"
            results.append(
                {
                    "rule_id": rid,
                    "name": name,
                    "priority": priority,
                    "status": status,
                    "actual_value": actual,
                    "threshold": rule["threshold"],
                    "details": None
                    if passed
                    else f"Violation: actual={actual}",
                }
            )
            if not passed and priority == "P0":
                p0_failures.append(rid)
            print(
                f"  [{priority}] {rid:>12s}  {status}  actual={actual}  "
                f"thr='{rule['threshold']}'  — {name}",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "rule_id": rid,
                    "name": name,
                    "priority": priority,
                    "status": "ERROR",
                    "actual_value": None,
                    "threshold": rule["threshold"],
                    "details": f"SQL error: {exc}",
                }
            )
            print(f"  [{priority}] {rid}  ERROR  {exc}", flush=True)

    return results, p0_failures


def gather_stats(con: duckdb.DuckDBPyConnection) -> dict:
    stats: dict = {}
    stats["total_rows"] = con.execute(
        "SELECT COUNT(*) FROM raw.college_scorecard_institution"
    ).fetchone()[0]
    stats["distinct_unitids"] = con.execute(
        "SELECT COUNT(DISTINCT unitid) FROM raw.college_scorecard_institution"
    ).fetchone()[0]
    stats["control_dist"] = [
        {"control": r[0], "count": r[1]}
        for r in con.execute(
            "SELECT control, COUNT(*) FROM raw.college_scorecard_institution "
            "GROUP BY control ORDER BY control"
        ).fetchall()
    ]
    stats["coa_coverage_pct"] = con.execute(
        "SELECT ROUND(100.0 * SUM(CASE WHEN costt4_a IS NOT NULL "
        "OR costt4_p IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) "
        "FROM raw.college_scorecard_institution"
    ).fetchone()[0]
    stats["pub_npt4_coverage_pct"] = con.execute(
        "SELECT ROUND(100.0 * SUM(CASE WHEN control=1 AND npt4_pub IS NOT NULL "
        "THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN control=1 THEN 1 ELSE 0 END), 0), 1) "
        "FROM raw.college_scorecard_institution"
    ).fetchone()[0]
    stats["priv_npt4_coverage_pct"] = con.execute(
        "SELECT ROUND(100.0 * SUM(CASE WHEN control=2 AND npt4_priv IS NOT NULL "
        "THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN control=2 THEN 1 ELSE 0 END), 0), 1) "
        "FROM raw.college_scorecard_institution"
    ).fetchone()[0]
    stats["q1_gt_q5_pub"] = con.execute(
        "SELECT COUNT(*) FROM raw.college_scorecard_institution WHERE control = 1 "
        "AND npt41_pub IS NOT NULL AND npt45_pub IS NOT NULL AND npt41_pub > npt45_pub"
    ).fetchone()[0]
    stats["q1_gt_q5_priv"] = con.execute(
        "SELECT COUNT(*) FROM raw.college_scorecard_institution WHERE control IN (2, 3) "
        "AND npt41_priv IS NOT NULL AND npt45_priv IS NOT NULL AND npt41_priv > npt45_priv"
    ).fetchone()[0]
    return stats


def main() -> int:
    print(
        "=== Bronze DQ execution (Iceberg): raw-ingest-college-scorecard-institution ===",
        flush=True,
    )
    catalog = get_catalog(
        brightsmith.config.WAREHOUSE_PATH,
        brightsmith.config.CATALOG_PATH,
    )
    table = catalog.load_table("bronze.college_scorecard_institution")
    rows = read_with_duckdb(table)
    print(f"Read {len(rows)} rows from Iceberg table", flush=True)

    con = _materialize_duckdb(rows)
    total = con.execute(
        "SELECT COUNT(*) FROM raw.college_scorecard_institution"
    ).fetchone()[0]
    print(f"Materialized {total} rows into DuckDB", flush=True)

    rules = load_rules()
    print(f"Executing {len(rules)} rules...", flush=True)
    results, p0_failures = execute_rules(con, rules)

    stats = gather_stats(con)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errored = sum(1 for r in results if r["status"] == "ERROR")

    ts = datetime.now(timezone.utc)
    run_id = hashlib.sha256(
        f"bronze-csi-iceberg-{ts.isoformat()}".encode()
    ).hexdigest()[:8]
    stamp = ts.strftime("%Y%m%dT%H%M%SZ")

    out = {
        "run_id": run_id,
        "spec": "raw-ingest-college-scorecard-institution",
        "zone": "bronze",
        "table": "bronze.college_scorecard_institution",
        "source": "iceberg",
        "executed_at": ts.isoformat(),
        "rules_total": len(results),
        "rules_passed": passed,
        "rules_failed": failed,
        "rules_errored": errored,
        "p0_passed": len(p0_failures) == 0,
        "results": results,
        "supplementary_stats": stats,
    }

    out_dir = PROJECT_ROOT / "governance" / "dq-results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (
        f"raw-ingest-college-scorecard-institution-iceberg-{stamp}.json"
    )
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nWrote results to {out_path}")

    print("\n=== Summary ===")
    print(f"Total:  {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Errored: {errored}")
    print(
        f"P0 gate: {'PASS' if len(p0_failures) == 0 else 'FAIL — ' + ', '.join(p0_failures)}"
    )

    return 0 if failed == 0 and errored == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
