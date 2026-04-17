"""Execute Bronze DQ rules for raw-ingest-onet-experience against the real
Iceberg-backed parquet.

The PyIceberg catalog entry for ``bronze.onet_experience`` currently fails
to resolve via ``catalog.load_table`` (NoSuchTableError reported by
bs:data-analyst), but the parquet file on disk is readable and the warehouse
layout is intact. This script reads the parquet directly via DuckDB and
materializes it as ``raw.onet_experience`` so the DQ rule SQL (which
references the fully-qualified name) executes unchanged.

Usage:
    uv run python scripts/dq_execute_onet_experience.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RULES_PATH = (
    PROJECT_ROOT / "governance" / "dq-rules" / "raw-onet-experience.json"
)

# The Iceberg table has a single parquet data file as of the current snapshot.
# We glob the data/ dir so a future compaction or append still works.
PARQUET_GLOB = (
    PROJECT_ROOT
    / "data"
    / "bronze"
    / "iceberg_warehouse"
    / "bronze"
    / "onet_experience"
    / "data"
    / "*.parquet"
)


def load_rules() -> list[dict]:
    return json.loads(RULES_PATH.read_text())["rules"]


def _materialize_duckdb() -> duckdb.DuckDBPyConnection:
    """Load the Bronze Iceberg parquet into in-memory DuckDB as raw.onet_experience."""
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA raw")
    con.execute(
        f"""
        CREATE TABLE raw.onet_experience AS
        SELECT * FROM read_parquet('{PARQUET_GLOB}')
        """
    )
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
            # For rules whose SQL returns a scalar 'violation' flag (0/1),
            # threshold is "result = 0". For set-returning rules that list
            # offending rows, threshold is "result_count = 0".
            if threshold == "result=0":
                actual = int(res[0][0]) if res else 0
                passed = actual == 0
            elif threshold == "result_count=0":
                actual = len(res)
                passed = actual == 0
            elif threshold.startswith("result_count<="):
                actual = len(res)
                passed = actual <= int(threshold.split("<=", 1)[1])
            elif threshold.startswith("result<="):
                actual = int(res[0][0]) if res else 0
                passed = actual <= int(threshold.split("<=", 1)[1])
            else:
                actual = len(res)
                passed = False

            status = "PASS" if passed else "FAIL"
            sample = None
            if not passed and res:
                # Capture up to 5 sample violation rows for the results file
                sample = [list(map(_jsonable, r)) for r in res[:5]]

            results.append(
                {
                    "rule_id": rid,
                    "name": name,
                    "priority": priority,
                    "status": status,
                    "actual_value": actual,
                    "threshold": rule["threshold"],
                    "details": None if passed else f"Violation: actual={actual}",
                    "sample_violations": sample,
                }
            )
            if not passed and priority == "P0":
                p0_failures.append(rid)
            print(
                f"  [{priority}] {rid:>18s}  {status}  actual={actual}  "
                f"thr='{rule['threshold']}'  -- {name}",
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
                    "sample_violations": None,
                }
            )
            print(f"  [{priority}] {rid}  ERROR  {exc}", flush=True)

    return results, p0_failures


def _jsonable(v: object) -> object:
    # DuckDB returns datetime/date/Decimal etc; coerce for JSON.
    if v is None:
        return None
    if isinstance(v, (int, float, str, bool)):
        return v
    return str(v)


def gather_stats(con: duckdb.DuckDBPyConnection) -> dict:
    stats: dict = {}
    stats["total_rows"] = con.execute(
        "SELECT COUNT(*) FROM raw.onet_experience"
    ).fetchone()[0]
    stats["distinct_onet_soc_codes"] = con.execute(
        "SELECT COUNT(DISTINCT onet_soc_code) FROM raw.onet_experience"
    ).fetchone()[0]
    stats["scale_distribution"] = [
        {"scale_id": r[0], "rows": r[1]}
        for r in con.execute(
            "SELECT scale_id, COUNT(*) FROM raw.onet_experience "
            "GROUP BY scale_id ORDER BY scale_id"
        ).fetchall()
    ]
    stats["category_counts_per_scale"] = [
        {"scale_id": r[0], "distinct_categories": r[1]}
        for r in con.execute(
            "SELECT scale_id, COUNT(DISTINCT category) FROM raw.onet_experience "
            "GROUP BY scale_id ORDER BY scale_id"
        ).fetchall()
    ]
    stats["element_id_values"] = [
        {"element_id": r[0], "rows": r[1]}
        for r in con.execute(
            "SELECT element_id, COUNT(*) FROM raw.onet_experience "
            "GROUP BY element_id ORDER BY element_id"
        ).fetchall()
    ]
    stats["data_value_range"] = {
        "min": con.execute(
            "SELECT MIN(data_value) FROM raw.onet_experience"
        ).fetchone()[0],
        "max": con.execute(
            "SELECT MAX(data_value) FROM raw.onet_experience"
        ).fetchone()[0],
    }
    stats["per_group_sum_stats"] = {
        "group_count": con.execute(
            "SELECT COUNT(*) FROM ("
            "SELECT onet_soc_code, scale_id FROM raw.onet_experience "
            "GROUP BY onet_soc_code, scale_id)"
        ).fetchone()[0],
        "max_abs_deviation_from_100": con.execute(
            "SELECT MAX(ABS(s - 100.0)) FROM ("
            "SELECT SUM(data_value) AS s FROM raw.onet_experience "
            "GROUP BY onet_soc_code, scale_id)"
        ).fetchone()[0],
    }
    stats["null_counts"] = {
        col: con.execute(
            f"SELECT COUNT(*) FROM raw.onet_experience WHERE {col} IS NULL"
        ).fetchone()[0]
        for col in ("onet_soc_code", "element_id", "scale_id", "category", "data_value")
    }
    return stats


def main() -> int:
    print("=== Bronze DQ execution: raw-onet-experience ===", flush=True)
    con = _materialize_duckdb()
    total = con.execute("SELECT COUNT(*) FROM raw.onet_experience").fetchone()[0]
    print(f"Materialized {total} rows into DuckDB as raw.onet_experience", flush=True)

    rules = load_rules()
    print(f"Executing {len(rules)} rules...", flush=True)
    results, p0_failures = execute_rules(con, rules)

    stats = gather_stats(con)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errored = sum(1 for r in results if r["status"] == "ERROR")

    ts = datetime.now(timezone.utc)
    run_id = hashlib.sha256(
        f"bronze-onet-exp-{ts.isoformat()}".encode()
    ).hexdigest()[:8]
    # Use the requested filename convention YYYYMMDD-HHMMSS
    stamp = ts.strftime("%Y%m%d-%H%M%S")

    out = {
        "run_id": run_id,
        "spec": "onet-experience-requirements",
        "zone": "bronze",
        "table": "bronze.onet_experience",
        "source": "iceberg_parquet",
        "source_path": str(PARQUET_GLOB),
        "executed_at": ts.isoformat(),
        "rules_total": len(results),
        "rules_passed": passed,
        "rules_failed": failed,
        "rules_errored": errored,
        "p0_passed": len(p0_failures) == 0,
        "p0_failures": p0_failures,
        "results": results,
        "supplementary_stats": stats,
    }

    out_dir = PROJECT_ROOT / "governance" / "dq-results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"raw-onet-experience-{stamp}.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nWrote results to {out_path}")

    print("\n=== Summary ===")
    print(f"Total:  {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Errored: {errored}")
    print(
        f"P0 gate: {'PASS' if len(p0_failures) == 0 else 'FAIL -- ' + ', '.join(p0_failures)}"
    )

    return 0 if failed == 0 and errored == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
