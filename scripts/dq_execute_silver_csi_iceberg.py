"""Execute Silver DQ rules for silver-base-college-scorecard-institution against
the real Iceberg table (not an in-memory transformation of the CSV).

This is the Iceberg-backed sibling of scripts/dq_execute_silver_csi.py.
Instead of re-downloading/transforming, it reads the persisted
base.college_scorecard_institution Iceberg table via
``read_with_duckdb(table)`` and materializes it into an in-memory DuckDB
view whose fully qualified name (``base.college_scorecard_institution``)
matches what the DQ rule SQL expects. All 23 rules defined in
``governance/dq-rules/silver-base-college-scorecard-institution.json`` are
executed unchanged; the status field (proposed/approved) is ignored here
because the goal is to prove parity against the real Silver Iceberg table
and close Silver post-review advisory A3.

Usage:
    uv run python scripts/dq_execute_silver_csi_iceberg.py
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

SILVER_WAREHOUSE = PROJECT_ROOT / "data" / "silver" / "iceberg_warehouse"


def load_rules() -> list[dict]:
    path = (
        PROJECT_ROOT
        / "governance"
        / "dq-rules"
        / "silver-base-college-scorecard-institution.json"
    )
    return json.loads(path.read_text())["rules"]


def _materialize_duckdb(rows: list[dict]) -> duckdb.DuckDBPyConnection:
    """Load Silver rows into in-memory DuckDB as base.college_scorecard_institution."""
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA base")
    con.execute(
        """
        CREATE TABLE base.college_scorecard_institution (
            record_id VARCHAR NOT NULL,
            unitid BIGINT NOT NULL,
            institution_name VARCHAR NOT NULL,
            state_abbr VARCHAR NOT NULL,
            institution_control VARCHAR NOT NULL,
            cost_of_attendance_annual DOUBLE,
            cost_of_attendance_4yr DOUBLE,
            net_price_annual DOUBLE,
            net_price_4yr DOUBLE,
            net_price_q1 DOUBLE,
            net_price_q2 DOUBLE,
            net_price_q3 DOUBLE,
            net_price_q4 DOUBLE,
            net_price_q5 DOUBLE,
            tuition_in_state DOUBLE,
            tuition_out_of_state DOUBLE,
            room_board_on_campus DOUBLE,
            room_board_off_campus DOUBLE,
            books_supplies DOUBLE,
            costt4_a_raw DOUBLE,
            costt4_p_raw DOUBLE,
            npt4_pub_raw DOUBLE,
            npt4_priv_raw DOUBLE,
            npt41_pub_raw DOUBLE,
            npt42_pub_raw DOUBLE,
            npt43_pub_raw DOUBLE,
            npt44_pub_raw DOUBLE,
            npt45_pub_raw DOUBLE,
            npt41_priv_raw DOUBLE,
            npt42_priv_raw DOUBLE,
            npt43_priv_raw DOUBLE,
            npt44_priv_raw DOUBLE,
            npt45_priv_raw DOUBLE,
            source_load_date DATE NOT NULL,
            ingested_at TIMESTAMP NOT NULL
        )
        """
    )
    cols = [
        "record_id", "unitid", "institution_name", "state_abbr",
        "institution_control",
        "cost_of_attendance_annual", "cost_of_attendance_4yr",
        "net_price_annual", "net_price_4yr",
        "net_price_q1", "net_price_q2", "net_price_q3", "net_price_q4", "net_price_q5",
        "tuition_in_state", "tuition_out_of_state",
        "room_board_on_campus", "room_board_off_campus", "books_supplies",
        "costt4_a_raw", "costt4_p_raw",
        "npt4_pub_raw", "npt4_priv_raw",
        "npt41_pub_raw", "npt42_pub_raw", "npt43_pub_raw",
        "npt44_pub_raw", "npt45_pub_raw",
        "npt41_priv_raw", "npt42_priv_raw", "npt43_priv_raw",
        "npt44_priv_raw", "npt45_priv_raw",
        "source_load_date", "ingested_at",
    ]
    placeholders = ", ".join(["?"] * len(cols))
    insert_sql = (
        f"INSERT INTO base.college_scorecard_institution ({', '.join(cols)}) "
        f"VALUES ({placeholders})"
    )
    for r in rows:
        vals = [r.get(c) for c in cols]
        con.execute(insert_sql, vals)
    return con


def _threshold_passes(threshold: str, actual: int) -> bool:
    t = threshold.replace(" ", "")
    if t == "result=0":
        return actual == 0
    if t == "result_count=0":
        return actual == 0
    if t.startswith("result_count<="):
        return actual <= int(t.split("<=", 1)[1])
    if t.startswith("result<="):
        return actual <= int(t.split("<=", 1)[1])
    raise ValueError(f"Unsupported threshold: {threshold}")


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
        threshold = rule["threshold"]

        try:
            res = con.execute(sql).fetchall()
            t_norm = threshold.replace(" ", "")
            if t_norm.startswith("result=") or t_norm.startswith("result<="):
                actual = int(res[0][0]) if res else 0
            else:
                actual = len(res)
            passed = _threshold_passes(threshold, actual)
            status = "PASS" if passed else "FAIL"
            results.append(
                {
                    "rule_id": rid,
                    "name": name,
                    "priority": priority,
                    "status": status,
                    "actual_value": actual,
                    "threshold": threshold,
                    "details": None if passed else f"Violation: actual={actual}",
                }
            )
            if not passed and priority == "P0":
                p0_failures.append(rid)
            print(
                f"  [{priority}] {rid:>12s}  {status}  actual={actual}  "
                f"thr='{threshold}'  — {name}",
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
                    "threshold": threshold,
                    "details": f"SQL error: {exc}",
                }
            )
            print(f"  [{priority}] {rid}  ERROR  {exc}", flush=True)
    return results, p0_failures


def gather_stats(con: duckdb.DuckDBPyConnection) -> dict:
    stats: dict = {}
    stats["total_rows"] = con.execute(
        "SELECT COUNT(*) FROM base.college_scorecard_institution"
    ).fetchone()[0]
    stats["distinct_unitids"] = con.execute(
        "SELECT COUNT(DISTINCT unitid) FROM base.college_scorecard_institution"
    ).fetchone()[0]
    stats["distinct_record_ids"] = con.execute(
        "SELECT COUNT(DISTINCT record_id) FROM base.college_scorecard_institution"
    ).fetchone()[0]
    ctl = con.execute(
        "SELECT institution_control, COUNT(*) AS n "
        "FROM base.college_scorecard_institution "
        "GROUP BY institution_control ORDER BY institution_control"
    ).fetchall()
    stats["control_distribution"] = [{"label": c, "count": n} for c, n in ctl]
    row = con.execute(
        "SELECT SUM(CASE WHEN net_price_annual IS NOT NULL THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN cost_of_attendance_annual IS NOT NULL THEN 1 ELSE 0 END), "
        "COUNT(*) FROM base.college_scorecard_institution"
    ).fetchone()
    stats["net_price_annual_coverage_pct"] = round(100.0 * row[0] / row[2], 2)
    stats["cost_of_attendance_annual_coverage_pct"] = round(100.0 * row[1] / row[2], 2)
    stats["q1_gt_q5_total"] = con.execute(
        "SELECT COUNT(*) FROM base.college_scorecard_institution "
        "WHERE net_price_q1 IS NOT NULL AND net_price_q5 IS NOT NULL "
        "AND net_price_q1 > net_price_q5"
    ).fetchone()[0]
    return stats


def main() -> int:
    print(
        "=== Silver DQ execution (Iceberg): silver-base-college-scorecard-institution ===",
        flush=True,
    )
    catalog = get_catalog(
        SILVER_WAREHOUSE,
        brightsmith.config.CATALOG_PATH,
    )
    table = catalog.load_table("base.college_scorecard_institution")
    rows = read_with_duckdb(table)
    print(f"Read {len(rows)} rows from Iceberg table", flush=True)

    con = _materialize_duckdb(rows)
    total = con.execute(
        "SELECT COUNT(*) FROM base.college_scorecard_institution"
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
        f"silver-csi-iceberg-{ts.isoformat()}".encode()
    ).hexdigest()[:8]
    stamp = ts.strftime("%Y%m%dT%H%M%SZ")

    out = {
        "run_id": run_id,
        "spec": "silver-base-college-scorecard-institution",
        "zone": "silver",
        "table": "base.college_scorecard_institution",
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
        f"silver-base-college-scorecard-institution-iceberg-{stamp}.json"
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
