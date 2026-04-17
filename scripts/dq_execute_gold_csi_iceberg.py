"""Execute Gold DQ rules for gold-career-outcomes-college-scorecard against the
real Iceberg table after CSI enrichment re-promote.

Runs all rules defined in
``governance/dq-rules/gold-career-outcomes-college-scorecard.json`` — both
the new GLD-CSI-001..009 enrichment rules (status=proposed) and the existing
GLD-CO-* regression suite (status=active) — against the freshly promoted
``consumable.career_outcomes`` Iceberg table. The rule status field is
ignored; the goal is to prove that the 7 new columns pass all GLD-CSI-*
invariants while the GLD-CO-* rules remain green (no regression).

Usage:
    uv run python scripts/dq_execute_gold_csi_iceberg.py
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

GOLD_WAREHOUSE = PROJECT_ROOT / "data" / "gold" / "iceberg_warehouse"


def load_rules() -> list[dict]:
    path = (
        PROJECT_ROOT
        / "governance"
        / "dq-rules"
        / "gold-career-outcomes-college-scorecard.json"
    )
    return json.loads(path.read_text())["rules"]


def _materialize_duckdb(
    con: duckdb.DuckDBPyConnection, rows: list[dict]
) -> None:
    """Register Iceberg rows into DuckDB as consumable.career_outcomes.

    We discover the schema from the first row's keys so this remains robust
    to evolution (7 new CSI columns + whatever the transformer emits).
    """
    if not rows:
        raise RuntimeError("Iceberg table produced 0 rows")

    con.execute("CREATE SCHEMA consumable")

    # Use DuckDB's VALUES-based inference via an Arrow-free path: build a
    # temp view from a Pandas DataFrame if available, else a sequence of
    # INSERTs. We use DuckDB's auto-typing on Python dicts via executemany.
    import pyarrow as pa  # provided transitively via pyiceberg / duckdb
    # Normalize into an Arrow table to preserve types through DuckDB.
    arrow_tbl = pa.Table.from_pylist(rows)
    con.register("_ingest_co", arrow_tbl)
    con.execute(
        "CREATE TABLE consumable.career_outcomes AS SELECT * FROM _ingest_co"
    )
    con.unregister("_ingest_co")


def _threshold_passes(threshold: str, actual: int) -> bool:
    t = threshold.replace(" ", "")
    if t == "result=0":
        return actual == 0
    if t == "result_count=0":
        return actual == 0
    if t.startswith("result_count<="):
        return actual <= int(t.split("<=", 1)[1])
    if t.startswith("result<="):
        # Floating threshold like "result <= 100.0"
        rhs = t.split("<=", 1)[1]
        try:
            return float(actual) <= float(rhs)
        except ValueError:
            return actual <= int(rhs)
    raise ValueError(f"Unsupported threshold: {threshold}")


def execute_rules(
    con: duckdb.DuckDBPyConnection, rules: list[dict]
) -> tuple[list[dict], list[str], list[str]]:
    results: list[dict] = []
    p0_failures: list[str] = []
    p1_failures: list[str] = []
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
                if res and res[0] and res[0][0] is not None:
                    actual_raw = res[0][0]
                else:
                    actual_raw = 0
                # Preserve floats where applicable (e.g. null_pct)
                actual = (
                    actual_raw
                    if isinstance(actual_raw, float)
                    else int(actual_raw)
                )
            else:
                actual = len(res)
            passed = _threshold_passes(threshold, actual)
            status = "PASS" if passed else "FAIL"
            results.append(
                {
                    "rule_id": rid,
                    "name": name,
                    "priority": priority,
                    "status_rule": rule.get("status"),
                    "status": status,
                    "actual_value": actual,
                    "threshold": threshold,
                    "details": None if passed else f"Violation: actual={actual}",
                }
            )
            if not passed:
                if priority == "P0":
                    p0_failures.append(rid)
                elif priority == "P1":
                    p1_failures.append(rid)
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
                    "status_rule": rule.get("status"),
                    "status": "ERROR",
                    "actual_value": None,
                    "threshold": threshold,
                    "details": f"SQL error: {exc}",
                }
            )
            print(f"  [{priority}] {rid}  ERROR  {exc}", flush=True)
    return results, p0_failures, p1_failures


def gather_stats(con: duckdb.DuckDBPyConnection) -> dict:
    stats: dict = {}
    stats["total_rows"] = con.execute(
        "SELECT COUNT(*) FROM consumable.career_outcomes"
    ).fetchone()[0]
    stats["distinct_unitids"] = con.execute(
        "SELECT COUNT(DISTINCT unitid) FROM consumable.career_outcomes"
    ).fetchone()[0]
    stats["distinct_record_ids"] = con.execute(
        "SELECT COUNT(DISTINCT record_id) FROM consumable.career_outcomes"
    ).fetchone()[0]

    row = con.execute(
        """
        SELECT
            ROUND(100.0 * SUM(CASE WHEN net_price_annual IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS np_coverage,
            ROUND(100.0 * SUM(CASE WHEN cost_of_attendance_annual IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS coa_coverage,
            ROUND(100.0 * SUM(CASE WHEN net_price_4yr IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS np4yr_coverage,
            ROUND(100.0 * SUM(CASE WHEN institution_control IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS control_coverage
        FROM consumable.career_outcomes
        """
    ).fetchone()
    stats["net_price_annual_coverage_pct"] = row[0]
    stats["cost_of_attendance_annual_coverage_pct"] = row[1]
    stats["net_price_4yr_coverage_pct"] = row[2]
    stats["institution_control_coverage_pct"] = row[3]

    stats["unmatched_distinct_unitids"] = con.execute(
        """
        SELECT COUNT(DISTINCT unitid) FROM consumable.career_outcomes
        WHERE institution_control IS NULL
          AND net_price_annual IS NULL
          AND cost_of_attendance_annual IS NULL
        """
    ).fetchone()[0]

    ctl = con.execute(
        """
        SELECT institution_control, COUNT(*) AS n
        FROM consumable.career_outcomes
        GROUP BY institution_control
        ORDER BY n DESC
        """
    ).fetchall()
    stats["institution_control_distribution"] = [
        {"label": c if c is not None else "(null)", "count": n} for c, n in ctl
    ]

    return stats


def main() -> int:
    print(
        "=== Gold DQ execution (Iceberg): gold-career-outcomes-college-scorecard ===",
        flush=True,
    )
    catalog = get_catalog(
        GOLD_WAREHOUSE,
        brightsmith.config.CATALOG_PATH,
    )
    table = catalog.load_table("consumable.career_outcomes")
    rows = read_with_duckdb(table)
    print(f"Read {len(rows)} rows from Iceberg table", flush=True)

    con = duckdb.connect(":memory:")
    _materialize_duckdb(con, rows)
    total = con.execute(
        "SELECT COUNT(*) FROM consumable.career_outcomes"
    ).fetchone()[0]
    print(f"Materialized {total} rows into DuckDB", flush=True)

    # Column introspection (to record schema evidence in results)
    col_info = con.execute(
        "DESCRIBE consumable.career_outcomes"
    ).fetchall()
    columns = [{"name": r[0], "type": r[1]} for r in col_info]
    print(f"Table has {len(columns)} columns", flush=True)

    rules = load_rules()
    gld_csi = [r for r in rules if r["rule_id"].startswith("GLD-CSI-")]
    gld_co = [r for r in rules if r["rule_id"].startswith("GLD-CO-")]
    print(
        f"Rules loaded: {len(rules)} total "
        f"({len(gld_csi)} GLD-CSI-* new, {len(gld_co)} GLD-CO-* regression)",
        flush=True,
    )

    print("\n--- GLD-CSI-* (new enrichment rules) ---", flush=True)
    csi_results, csi_p0, csi_p1 = execute_rules(con, gld_csi)
    print("\n--- GLD-CO-* (regression) ---", flush=True)
    co_results, co_p0, co_p1 = execute_rules(con, gld_co)

    results = csi_results + co_results
    p0_failures = csi_p0 + co_p0
    p1_failures = csi_p1 + co_p1

    stats = gather_stats(con)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errored = sum(1 for r in results if r["status"] == "ERROR")

    # Breakdown per sub-group for scorecard
    def _count(subset: list[dict], status: str) -> int:
        return sum(1 for r in subset if r["status"] == status)

    csi_summary = {
        "total": len(csi_results),
        "passed": _count(csi_results, "PASS"),
        "failed": _count(csi_results, "FAIL"),
        "errored": _count(csi_results, "ERROR"),
        "p0_failed": [r["rule_id"] for r in csi_results if r["priority"] == "P0" and r["status"] != "PASS"],
        "p1_failed": [r["rule_id"] for r in csi_results if r["priority"] == "P1" and r["status"] != "PASS"],
        "p2_failed": [r["rule_id"] for r in csi_results if r["priority"] == "P2" and r["status"] != "PASS"],
    }
    co_summary = {
        "total": len(co_results),
        "passed": _count(co_results, "PASS"),
        "failed": _count(co_results, "FAIL"),
        "errored": _count(co_results, "ERROR"),
        "p0_failed": [r["rule_id"] for r in co_results if r["priority"] == "P0" and r["status"] != "PASS"],
        "p1_failed": [r["rule_id"] for r in co_results if r["priority"] == "P1" and r["status"] != "PASS"],
        "p2_failed": [r["rule_id"] for r in co_results if r["priority"] == "P2" and r["status"] != "PASS"],
    }

    ts = datetime.now(timezone.utc)
    stamp = ts.strftime("%Y%m%dT%H%M%SZ")
    run_id = hashlib.sha256(
        f"gold-csi-iceberg-{ts.isoformat()}".encode()
    ).hexdigest()[:8]

    # Evidence hash: stable over rule_id + actual_value pairs so the scorecard
    # pins the exact observed state without depending on timestamps.
    evidence_payload = json.dumps(
        [
            {"rule_id": r["rule_id"], "actual": r["actual_value"], "status": r["status"]}
            for r in results
        ],
        sort_keys=True,
    )
    evidence_hash = hashlib.sha256(evidence_payload.encode()).hexdigest()[:16]

    out = {
        "run_id": run_id,
        "evidence_hash": evidence_hash,
        "spec": "gold-career-outcomes-college-scorecard",
        "zone": "gold",
        "table": "consumable.career_outcomes",
        "source": "iceberg",
        "warehouse": str(GOLD_WAREHOUSE),
        "executed_at": ts.isoformat(),
        "schema_columns": columns,
        "rules_total": len(results),
        "rules_passed": passed,
        "rules_failed": failed,
        "rules_errored": errored,
        "p0_passed": len(p0_failures) == 0,
        "p0_failures": p0_failures,
        "p1_failures": p1_failures,
        "gld_csi_summary": csi_summary,
        "gld_co_summary": co_summary,
        "results": results,
        "supplementary_stats": stats,
    }

    out_dir = PROJECT_ROOT / "governance" / "dq-results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (
        f"gold-career-outcomes-college-scorecard-csi-enrichment-{stamp}.json"
    )
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nWrote results to {out_path}")

    print("\n=== Summary ===")
    print(f"Total:   {len(results)}")
    print(f"Passed:  {passed}")
    print(f"Failed:  {failed}")
    print(f"Errored: {errored}")
    print(
        f"P0 gate: {'PASS' if len(p0_failures) == 0 else 'FAIL — ' + ', '.join(p0_failures)}"
    )
    print(
        f"P1 gate: {'PASS' if len(p1_failures) == 0 else 'FAIL — ' + ', '.join(p1_failures)}"
    )
    print(f"Evidence hash: {evidence_hash}")
    print(f"GLD-CSI: {csi_summary['passed']}/{csi_summary['total']} passed")
    print(f"GLD-CO : {co_summary['passed']}/{co_summary['total']} passed")

    return 0 if failed == 0 and errored == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
