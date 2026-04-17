"""Execute Gold DQ rules for onet-experience-requirements against the real
Iceberg-backed ``consumable.career_branches`` table.

Runs the 3 addendum rules defined in
``governance/dq-rules/gold-career-branches-experience.json``
(GLD-CB-EXP-001, 002, 003) against the freshly re-promoted Gold table so the
proposed rules can be advanced to ``active`` with real-data backing.

Usage:
    uv run python scripts/dq_execute_gold_career_branches_experience.py
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

RULES_PATH = (
    PROJECT_ROOT
    / "governance"
    / "dq-rules"
    / "gold-career-branches-experience.json"
)


def load_rules() -> list[dict]:
    return json.loads(RULES_PATH.read_text())["rules"]


def _materialize_duckdb(
    con: duckdb.DuckDBPyConnection, rows: list[dict]
) -> None:
    """Register Iceberg rows into DuckDB as consumable.career_branches."""
    if not rows:
        raise RuntimeError("Iceberg table produced 0 rows")

    con.execute("CREATE SCHEMA consumable")

    import pyarrow as pa
    arrow_tbl = pa.Table.from_pylist(rows)
    con.register("_ingest_cb", arrow_tbl)
    con.execute(
        "CREATE TABLE consumable.career_branches AS SELECT * FROM _ingest_cb"
    )
    con.unregister("_ingest_cb")


def _jsonable(v: object) -> object:
    if v is None:
        return None
    if isinstance(v, (int, float, str, bool)):
        return v
    return str(v)


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
        threshold = rule["threshold"].replace(" ", "")

        try:
            res = con.execute(sql).fetchall()
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
                sample = [list(map(_jsonable, r)) for r in res[:5]]

            results.append(
                {
                    "rule_id": rid,
                    "name": name,
                    "priority": priority,
                    "dimension": rule.get("dimension"),
                    "status_rule": rule.get("status"),
                    "status": status,
                    "actual_value": actual,
                    "threshold": rule["threshold"],
                    "details": None if passed else f"Violation: actual={actual}",
                    "sample_violations": sample,
                }
            )
            if not passed:
                if priority == "P0":
                    p0_failures.append(rid)
                elif priority == "P1":
                    p1_failures.append(rid)
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
                    "dimension": rule.get("dimension"),
                    "status_rule": rule.get("status"),
                    "status": "ERROR",
                    "actual_value": None,
                    "threshold": rule["threshold"],
                    "details": f"SQL error: {exc}",
                    "sample_violations": None,
                }
            )
            if priority == "P0":
                p0_failures.append(rid)
            elif priority == "P1":
                p1_failures.append(rid)
            print(f"  [{priority}] {rid}  ERROR  {exc}", flush=True)

    return results, p0_failures, p1_failures


def gather_stats(con: duckdb.DuckDBPyConnection) -> dict:
    stats: dict = {}
    stats["total_rows"] = con.execute(
        "SELECT COUNT(*) FROM consumable.career_branches"
    ).fetchone()[0]

    # Null rate and coverage for related_experience_years
    row = con.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN related_experience_years IS NULL THEN 1 ELSE 0 END) AS rey_null,
            SUM(CASE WHEN source_experience_years IS NULL THEN 1 ELSE 0 END) AS sey_null,
            SUM(CASE WHEN experience_delta_years IS NULL THEN 1 ELSE 0 END) AS delta_null,
            SUM(CASE WHEN related_experience_tier IS NULL THEN 1 ELSE 0 END) AS tier_null
        FROM consumable.career_branches
        """
    ).fetchone()
    total = row[0] or 0
    stats["null_counts"] = {
        "related_experience_years": row[1],
        "source_experience_years": row[2],
        "experience_delta_years": row[3],
        "related_experience_tier": row[4],
    }
    stats["null_rates_pct"] = {
        "related_experience_years": round((row[1] or 0) * 100.0 / total, 4) if total else None,
        "source_experience_years": round((row[2] or 0) * 100.0 / total, 4) if total else None,
        "experience_delta_years": round((row[3] or 0) * 100.0 / total, 4) if total else None,
        "related_experience_tier": round((row[4] or 0) * 100.0 / total, 4) if total else None,
    }

    # Tier distribution
    stats["related_experience_tier_distribution"] = [
        {"tier": r[0] if r[0] is not None else "(null)", "rows": r[1]}
        for r in con.execute(
            "SELECT related_experience_tier, COUNT(*) FROM consumable.career_branches "
            "GROUP BY related_experience_tier ORDER BY 2 DESC"
        ).fetchall()
    ]

    # Delta range stats (where both populated)
    drow = con.execute(
        """
        SELECT
            COUNT(*) AS n,
            MIN(experience_delta_years) AS min_d,
            MAX(experience_delta_years) AS max_d,
            AVG(experience_delta_years) AS avg_d
        FROM consumable.career_branches
        WHERE related_experience_years IS NOT NULL
          AND source_experience_years IS NOT NULL
          AND experience_delta_years IS NOT NULL
        """
    ).fetchone()
    stats["experience_delta_years_where_both_nonnull"] = {
        "rows": drow[0],
        "min": float(drow[1]) if drow[1] is not None else None,
        "max": float(drow[2]) if drow[2] is not None else None,
        "avg": float(drow[3]) if drow[3] is not None else None,
    }

    # Senior consistency spot check
    senior_row = con.execute(
        """
        SELECT
            COUNT(*) AS senior_rows,
            MIN(related_experience_years) AS min_y,
            MAX(related_experience_years) AS max_y
        FROM consumable.career_branches
        WHERE related_experience_tier = 'senior'
        """
    ).fetchone()
    stats["senior_tier_check"] = {
        "rows": senior_row[0],
        "min_related_experience_years": float(senior_row[1]) if senior_row[1] is not None else None,
        "max_related_experience_years": float(senior_row[2]) if senior_row[2] is not None else None,
    }

    return stats


def write_scorecard(
    scorecard_path: Path,
    results: list[dict],
    stats: dict,
    ts: datetime,
    run_id: str,
    snapshot_id: str,
) -> None:
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errored = sum(1 for r in results if r["status"] == "ERROR")
    p0_fails = [r for r in results if r["status"] in ("FAIL", "ERROR") and r["priority"] == "P0"]
    p1_fails = [r for r in results if r["status"] in ("FAIL", "ERROR") and r["priority"] == "P1"]

    pass_rate = (passed / total * 100.0) if total else 0.0

    lines: list[str] = []
    lines.append("# DQ Scorecard: gold-career-branches-experience")
    lines.append("")
    lines.append("- **Spec**: `docs/specs/onet-experience-requirements.md`")
    lines.append("- **Zone**: Gold")
    lines.append("- **Table**: `consumable.career_branches`")
    lines.append(f"- **Iceberg snapshot**: `{snapshot_id}`")
    lines.append(f"- **Run ID**: `{run_id}`")
    lines.append(f"- **Executed at (UTC)**: {ts.isoformat()}")
    lines.append("- **Rules file**: `governance/dq-rules/gold-career-branches-experience.json`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Total rules | {total} |")
    lines.append(f"| Passed | {passed} |")
    lines.append(f"| Failed | {failed} |")
    lines.append(f"| Errored | {errored} |")
    lines.append(f"| Pass rate | {pass_rate:.1f}% |")
    lines.append(f"| **P0 gate** | **{'PASS' if not p0_fails else 'FAIL'}** |")
    lines.append(f"| P1 warnings | {len(p1_fails)} |")
    lines.append("")

    lines.append("## Table stats (observed)")
    lines.append("")
    lines.append(f"- **Total rows**: {stats['total_rows']}")
    nr = stats["null_rates_pct"]
    lines.append(
        f"- **Null rates (%)**: "
        f"related_experience_years={nr['related_experience_years']}, "
        f"source_experience_years={nr['source_experience_years']}, "
        f"experience_delta_years={nr['experience_delta_years']}, "
        f"related_experience_tier={nr['related_experience_tier']}"
    )
    dd = stats["experience_delta_years_where_both_nonnull"]
    lines.append(
        f"- **experience_delta_years (both-sides non-null)**: "
        f"rows={dd['rows']}, min={dd['min']}, max={dd['max']}, "
        f"avg={dd['avg']:.3f}" if dd['avg'] is not None else
        f"- **experience_delta_years (both-sides non-null)**: rows={dd['rows']}"
    )
    sc = stats["senior_tier_check"]
    lines.append(
        f"- **Senior tier rows**: {sc['rows']} "
        f"(min years={sc['min_related_experience_years']}, "
        f"max years={sc['max_related_experience_years']})"
    )
    lines.append("")

    lines.append("### related_experience_tier distribution")
    lines.append("")
    lines.append("| Tier | Rows |")
    lines.append("|---|---|")
    for row in stats["related_experience_tier_distribution"]:
        lines.append(f"| {row['tier']} | {row['rows']} |")
    lines.append("")

    lines.append("## Rule results")
    lines.append("")
    lines.append("| Rule ID | Priority | Dimension | Status | Actual | Threshold | Name |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in results:
        lines.append(
            f"| `{r['rule_id']}` | {r['priority']} | "
            f"{r.get('dimension') or '-'} | "
            f"**{r['status']}** | {r['actual_value']} | "
            f"`{r['threshold']}` | {r['name']} |"
        )
    lines.append("")

    if p0_fails or p1_fails or errored:
        lines.append("## Failures / errors")
        lines.append("")
        for r in p0_fails + p1_fails:
            lines.append(
                f"- **{r['rule_id']}** [{r['priority']}] {r['status']}: {r['details']}"
            )
            if r.get("sample_violations"):
                lines.append(f"  - Sample violations (up to 5): `{r['sample_violations']}`")
        lines.append("")
    else:
        lines.append("## Failures / errors")
        lines.append("")
        lines.append("_None. All rules passed._")
        lines.append("")

    lines.append("## Gate decision")
    lines.append("")
    if not p0_fails and not errored:
        lines.append(
            "**P0 gate: PASS.** Gold addendum DQ for `onet-experience-requirements` "
            "is cleared. Rule status advanced from `proposed` to `active`."
        )
    else:
        lines.append(
            "**P0 gate: FAIL.** Spec cannot be marked complete. "
            "Escalate to `@governance-reviewer`."
        )
    lines.append("")

    scorecard_path.write_text("\n".join(lines))


def write_audit_entry(
    audit_path: Path,
    run_id: str,
    ts: datetime,
    results: list[dict],
    stats: dict,
    p0_failures: list[str],
    p1_failures: list[str],
    results_path: Path,
    scorecard_path: Path,
    snapshot_id: str,
) -> None:
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errored = sum(1 for r in results if r["status"] == "ERROR")

    lines: list[str] = []
    lines.append(f"# DQ execution: gold-career-branches-experience ({run_id})")
    lines.append("")
    lines.append(f"- **Timestamp (UTC)**: {ts.isoformat()}")
    lines.append("- **Spec**: `docs/specs/onet-experience-requirements.md`")
    lines.append("- **Zone**: Gold")
    lines.append("- **Table**: `consumable.career_branches`")
    lines.append(f"- **Iceberg snapshot**: `{snapshot_id}`")
    lines.append("- **Rules executed**: 3 (GLD-CB-EXP-001, 002, 003)")
    lines.append("- **Rules file**: `governance/dq-rules/gold-career-branches-experience.json`")
    lines.append("")
    lines.append("## Result summary")
    lines.append("")
    lines.append(f"- Passed: {passed} / {total}")
    lines.append(f"- Failed: {failed}")
    lines.append(f"- Errored: {errored}")
    lines.append(
        f"- **P0 gate**: {'PASS' if not p0_failures else 'FAIL (' + ', '.join(p0_failures) + ')'}"
    )
    lines.append(
        f"- **P1 warnings**: {len(p1_failures)}"
        + (f" ({', '.join(p1_failures)})" if p1_failures else "")
    )
    lines.append("")
    lines.append("## Observed table stats")
    lines.append("")
    lines.append(f"- total_rows = {stats['total_rows']}")
    lines.append(f"- null_rates_pct = {stats['null_rates_pct']}")
    lines.append(
        f"- experience_delta_years_where_both_nonnull = {stats['experience_delta_years_where_both_nonnull']}"
    )
    lines.append(f"- senior_tier_check = {stats['senior_tier_check']}")
    lines.append(
        f"- related_experience_tier_distribution = {stats['related_experience_tier_distribution']}"
    )
    lines.append("")
    lines.append("## Rule status transition")
    lines.append("")
    if not p0_failures and errored == 0:
        lines.append(
            "All 3 rules passed against real Gold data (snapshot "
            f"`{snapshot_id}`). Rule status in "
            "`governance/dq-rules/gold-career-branches-experience.json` "
            "updated from `proposed` to `active` for GLD-CB-EXP-001, "
            "GLD-CB-EXP-002, GLD-CB-EXP-003."
        )
    else:
        lines.append(
            "Rule status NOT advanced -- gate did not pass. "
            "Rules remain `proposed` pending remediation."
        )
    lines.append("")
    lines.append("## Regression comparison")
    lines.append("")
    lines.append(
        "_First Gold DQ execution for the experience-addendum rules on "
        "`consumable.career_branches`; no prior run to compare._"
    )
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    lines.append(f"- Results JSON: `{results_path.relative_to(PROJECT_ROOT)}`")
    lines.append(f"- Scorecard: `{scorecard_path.relative_to(PROJECT_ROOT)}`")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    if not p0_failures and errored == 0:
        lines.append(
            "P0 gate cleared. Gold addendum DQ is green for "
            "`onet-experience-requirements`. Proceed to Zone 4 work."
        )
    else:
        lines.append(
            "P0 gate failed. Spec cannot be marked complete until "
            "`@governance-reviewer` acknowledges."
        )
    lines.append("")

    audit_path.write_text("\n".join(lines))


def advance_rule_status(results: list[dict], snapshot_id: str, ts: datetime) -> list[str]:
    """Advance rules from `proposed` to `active` where they passed.

    Only updates status fields -- never SQL or thresholds.
    """
    doc = json.loads(RULES_PATH.read_text())
    updated: list[str] = []
    results_by_id = {r["rule_id"]: r for r in results}
    for rule in doc["rules"]:
        rid = rule["rule_id"]
        res = results_by_id.get(rid)
        if res is None:
            continue
        if res["status"] == "PASS" and rule.get("status") == "proposed":
            rule["status"] = "active"
            rule["activated_at"] = ts.isoformat()
            rule["activated_by"] = "@dq-engineer"
            rule["activation_evidence"] = {
                "iceberg_snapshot_id": snapshot_id,
                "actual_value": res["actual_value"],
                "threshold": res["threshold"],
            }
            updated.append(rid)
    RULES_PATH.write_text(json.dumps(doc, indent=2) + "\n")
    return updated


def main() -> int:
    print(
        "=== Gold DQ execution (Iceberg): gold-career-branches-experience ===",
        flush=True,
    )
    catalog = get_catalog(
        GOLD_WAREHOUSE,
        brightsmith.config.CATALOG_PATH,
    )
    table = catalog.load_table("consumable.career_branches")
    snap = table.current_snapshot()
    snapshot_id = str(snap.snapshot_id) if snap else "UNKNOWN"
    print(f"Iceberg current snapshot: {snapshot_id}", flush=True)

    rows = read_with_duckdb(table)
    print(f"Read {len(rows)} rows from Iceberg table", flush=True)

    con = duckdb.connect(":memory:")
    _materialize_duckdb(con, rows)
    total = con.execute(
        "SELECT COUNT(*) FROM consumable.career_branches"
    ).fetchone()[0]
    print(f"Materialized {total} rows into DuckDB", flush=True)

    col_info = con.execute("DESCRIBE consumable.career_branches").fetchall()
    print(f"Table has {len(col_info)} columns", flush=True)

    rules = load_rules()
    print(f"Executing {len(rules)} rules...", flush=True)
    results, p0_failures, p1_failures = execute_rules(con, rules)

    stats = gather_stats(con)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errored = sum(1 for r in results if r["status"] == "ERROR")

    ts = datetime.now(timezone.utc)
    run_id = hashlib.sha256(
        f"gold-cb-exp-{ts.isoformat()}".encode()
    ).hexdigest()[:8]
    stamp = ts.strftime("%Y%m%d-%H%M%S")

    out = {
        "run_id": run_id,
        "spec": "onet-experience-requirements",
        "zone": "gold",
        "table": "consumable.career_branches",
        "iceberg_snapshot_id": snapshot_id,
        "source": "iceberg_parquet_via_pyiceberg",
        "source_warehouse": str(GOLD_WAREHOUSE),
        "executed_at": ts.isoformat(),
        "rules_file": "governance/dq-rules/gold-career-branches-experience.json",
        "rules_total": len(results),
        "rules_passed": passed,
        "rules_failed": failed,
        "rules_errored": errored,
        "p0_passed": len(p0_failures) == 0,
        "p0_failures": p0_failures,
        "p1_failures": p1_failures,
        "results": results,
        "supplementary_stats": stats,
    }

    results_dir = PROJECT_ROOT / "governance" / "dq-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    results_path = results_dir / f"gold-career-branches-experience-{stamp}.json"
    results_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nWrote results to {results_path}")

    scorecard_dir = PROJECT_ROOT / "governance" / "dq-scorecards"
    scorecard_dir.mkdir(parents=True, exist_ok=True)
    scorecard_path = scorecard_dir / "gold-career-branches-experience.md"
    write_scorecard(scorecard_path, results, stats, ts, run_id, snapshot_id)
    print(f"Wrote scorecard to {scorecard_path}")

    audit_dir = PROJECT_ROOT / "governance" / "audit-trail"
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / f"gold-career-branches-experience-{stamp}.md"
    write_audit_entry(
        audit_path, run_id, ts, results, stats, p0_failures, p1_failures,
        results_path, scorecard_path, snapshot_id,
    )
    print(f"Wrote audit trail to {audit_path}")

    # Advance rule status from proposed -> active for rules that passed.
    if failed == 0 and errored == 0:
        updated = advance_rule_status(results, snapshot_id, ts)
        if updated:
            print(
                f"Advanced {len(updated)} rule(s) from proposed to active: "
                f"{', '.join(updated)}"
            )
        else:
            print("No rule status changes required (already active or not passing).")
    else:
        print("Skipping rule-status advancement due to failures/errors.")

    print("\n=== Summary ===")
    print(f"Total:   {len(results)}")
    print(f"Passed:  {passed}")
    print(f"Failed:  {failed}")
    print(f"Errored: {errored}")
    print(
        f"P0 gate: {'PASS' if len(p0_failures) == 0 else 'FAIL -- ' + ', '.join(p0_failures)}"
    )

    return 0 if failed == 0 and errored == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
