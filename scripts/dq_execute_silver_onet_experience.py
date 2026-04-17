"""Execute Silver DQ rules for onet-experience-requirements against the real
Iceberg-backed parquet for ``base.onet_experience_profiles``.

Per project convention the Iceberg namespace is ``base`` (not ``silver``).
Rather than relying on PyIceberg catalog resolution, we read the parquet
data file directly via DuckDB and materialize it as ``base.onet_experience_profiles``
so the DQ rule SQL (which references the fully-qualified name) executes unchanged.

Usage:
    uv run python scripts/dq_execute_silver_onet_experience.py
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
    PROJECT_ROOT / "governance" / "dq-rules" / "silver-onet-experience.json"
)

PARQUET_GLOB = (
    PROJECT_ROOT
    / "data"
    / "silver"
    / "iceberg_warehouse"
    / "base"
    / "onet_experience_profiles"
    / "data"
    / "*.parquet"
)

SNAPSHOT_ID = "5745163851101673330"


def load_rules() -> list[dict]:
    return json.loads(RULES_PATH.read_text())["rules"]


def _materialize_duckdb() -> duckdb.DuckDBPyConnection:
    """Load the Silver Iceberg parquet into in-memory DuckDB as base.onet_experience_profiles."""
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA base")
    con.execute(
        f"""
        CREATE TABLE base.onet_experience_profiles AS
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
            if priority == "P0":
                p0_failures.append(rid)
            print(f"  [{priority}] {rid}  ERROR  {exc}", flush=True)

    return results, p0_failures


def _jsonable(v: object) -> object:
    if v is None:
        return None
    if isinstance(v, (int, float, str, bool)):
        return v
    return str(v)


def gather_stats(con: duckdb.DuckDBPyConnection) -> dict:
    stats: dict = {}
    stats["total_rows"] = con.execute(
        "SELECT COUNT(*) FROM base.onet_experience_profiles"
    ).fetchone()[0]
    stats["distinct_bls_soc_codes"] = con.execute(
        "SELECT COUNT(DISTINCT bls_soc_code) FROM base.onet_experience_profiles"
    ).fetchone()[0]
    stats["tier_distribution"] = [
        {"tier": r[0], "rows": r[1]}
        for r in con.execute(
            "SELECT experience_tier, COUNT(*) FROM base.onet_experience_profiles "
            "GROUP BY experience_tier ORDER BY 2 DESC"
        ).fetchall()
    ]
    stats["experience_years_typical"] = {
        "min": con.execute(
            "SELECT MIN(experience_years_typical) FROM base.onet_experience_profiles"
        ).fetchone()[0],
        "max": con.execute(
            "SELECT MAX(experience_years_typical) FROM base.onet_experience_profiles"
        ).fetchone()[0],
        "avg": con.execute(
            "SELECT AVG(experience_years_typical) FROM base.onet_experience_profiles"
        ).fetchone()[0],
    }
    stats["experience_category_median"] = {
        "min": con.execute(
            "SELECT MIN(experience_category_median) FROM base.onet_experience_profiles"
        ).fetchone()[0],
        "max": con.execute(
            "SELECT MAX(experience_category_median) FROM base.onet_experience_profiles"
        ).fetchone()[0],
    }
    stats["spot_checks"] = [
        {
            "bls_soc_code": r[0],
            "experience_tier": r[1],
            "experience_category_median": r[2],
            "experience_years_typical": float(r[3]) if r[3] is not None else None,
        }
        for r in con.execute(
            "SELECT bls_soc_code, experience_tier, experience_category_median, "
            "experience_years_typical FROM base.onet_experience_profiles "
            "WHERE bls_soc_code IN ('11-1011', '15-1252', '41-2031') "
            "ORDER BY bls_soc_code"
        ).fetchall()
    ]
    stats["null_counts"] = {
        col: con.execute(
            f"SELECT COUNT(*) FROM base.onet_experience_profiles WHERE {col} IS NULL"
        ).fetchone()[0]
        for col in (
            "bls_soc_code",
            "experience_category_median",
            "experience_years_typical",
            "experience_tier",
        )
    }
    return stats


def write_scorecard(
    scorecard_path: Path,
    results: list[dict],
    stats: dict,
    ts: datetime,
    run_id: str,
) -> None:
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errored = sum(1 for r in results if r["status"] == "ERROR")
    p0_fails = [r for r in results if r["status"] in ("FAIL", "ERROR") and r["priority"] == "P0"]
    p1_fails = [r for r in results if r["status"] in ("FAIL", "ERROR") and r["priority"] == "P1"]

    pass_rate = (passed / total * 100.0) if total else 0.0

    lines: list[str] = []
    lines.append("# DQ Scorecard: silver-onet-experience")
    lines.append("")
    lines.append(f"- **Spec**: `docs/specs/onet-experience-requirements.md`")
    lines.append(f"- **Zone**: Silver")
    lines.append(f"- **Table**: `base.onet_experience_profiles`")
    lines.append(f"- **Iceberg snapshot**: `{SNAPSHOT_ID}`")
    lines.append(f"- **Run ID**: `{run_id}`")
    lines.append(f"- **Executed at (UTC)**: {ts.isoformat()}")
    lines.append(f"- **Rules file**: `governance/dq-rules/silver-onet-experience.json`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| Total rules | {total} |")
    lines.append(f"| Passed | {passed} |")
    lines.append(f"| Failed | {failed} |")
    lines.append(f"| Errored | {errored} |")
    lines.append(f"| Pass rate | {pass_rate:.1f}% |")
    lines.append(
        f"| **P0 gate** | **{'PASS' if not p0_fails else 'FAIL'}** |"
    )
    lines.append(f"| P1 warnings | {len(p1_fails)} |")
    lines.append("")

    lines.append("## Table stats (observed)")
    lines.append("")
    lines.append(f"- **Total rows**: {stats['total_rows']}")
    lines.append(f"- **Distinct bls_soc_code**: {stats['distinct_bls_soc_codes']}")
    eyt = stats["experience_years_typical"]
    lines.append(
        f"- **experience_years_typical**: min={eyt['min']}, max={eyt['max']}, "
        f"avg={float(eyt['avg']):.3f}"
    )
    ecm = stats["experience_category_median"]
    lines.append(
        f"- **experience_category_median**: min={ecm['min']}, max={ecm['max']}"
    )
    lines.append("")
    lines.append("### Tier distribution")
    lines.append("")
    lines.append("| Tier | Rows |")
    lines.append("|---|---|")
    for row in stats["tier_distribution"]:
        lines.append(f"| {row['tier']} | {row['rows']} |")
    lines.append("")

    lines.append("### Spot checks")
    lines.append("")
    lines.append("| BLS SOC | Tier | Category median | Years typical |")
    lines.append("|---|---|---|---|")
    for sc in stats["spot_checks"]:
        lines.append(
            f"| {sc['bls_soc_code']} | {sc['experience_tier']} | "
            f"{sc['experience_category_median']} | {sc['experience_years_typical']} |"
        )
    lines.append("")

    lines.append("## Rule results")
    lines.append("")
    lines.append("| Rule ID | Priority | Dimension | Status | Actual | Threshold | Name |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in results:
        lines.append(
            f"| `{r['rule_id']}` | {r['priority']} | "
            f"{_dimension_for(r['rule_id'])} | "
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
            "**P0 gate: PASS.** Silver zone of `onet-experience-requirements` "
            "is cleared from the DQ perspective."
        )
    else:
        lines.append(
            "**P0 gate: FAIL.** Spec cannot be marked complete. "
            "Escalate to `@governance-reviewer`."
        )
    lines.append("")

    scorecard_path.write_text("\n".join(lines))


def _dimension_for(rule_id: str) -> str:
    """Fallback dimension lookup to keep scorecard table concise.

    We intentionally re-derive from the rules JSON rather than pass through,
    so the scorecard layout is self-contained.
    """
    mapping = {
        "SLV-ONET-EXP-001": "Volume",
        "SLV-ONET-EXP-002": "Validity",
        "SLV-ONET-EXP-003": "Uniqueness",
        "SLV-ONET-EXP-004": "Validity",
        "SLV-ONET-EXP-005": "Validity",
        "SLV-ONET-EXP-006": "Validity",
        "SLV-ONET-EXP-007": "Coverage",
        "SLV-ONET-EXP-008": "Consistency",
        "SLV-ONET-EXP-009": "Consistency",
        "SLV-ONET-EXP-010": "Consistency",
    }
    return mapping.get(rule_id, "-")


def write_audit_entry(
    audit_path: Path,
    run_id: str,
    ts: datetime,
    results: list[dict],
    stats: dict,
    p0_failures: list[str],
    results_path: Path,
    scorecard_path: Path,
) -> None:
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errored = sum(1 for r in results if r["status"] == "ERROR")

    lines: list[str] = []
    lines.append(f"# DQ execution: silver-onet-experience ({run_id})")
    lines.append("")
    lines.append(f"- **Timestamp (UTC)**: {ts.isoformat()}")
    lines.append(f"- **Spec**: `docs/specs/onet-experience-requirements.md`")
    lines.append(f"- **Zone**: Silver")
    lines.append(f"- **Table**: `base.onet_experience_profiles`")
    lines.append(f"- **Iceberg snapshot**: `{SNAPSHOT_ID}`")
    lines.append(f"- **Rules executed**: 10 (SLV-ONET-EXP-001 through 010)")
    lines.append(f"- **Rules file**: `governance/dq-rules/silver-onet-experience.json`")
    lines.append("")
    lines.append("## Result summary")
    lines.append("")
    lines.append(f"- Passed: {passed} / {total}")
    lines.append(f"- Failed: {failed}")
    lines.append(f"- Errored: {errored}")
    lines.append(
        f"- **P0 gate**: {'PASS' if not p0_failures else 'FAIL (' + ', '.join(p0_failures) + ')'}"
    )
    lines.append("")
    lines.append("## Observed table stats")
    lines.append("")
    lines.append(f"- total_rows = {stats['total_rows']}")
    lines.append(f"- distinct bls_soc_code = {stats['distinct_bls_soc_codes']}")
    lines.append(
        f"- tier distribution = {stats['tier_distribution']}"
    )
    lines.append(
        "- spot checks (11-1011 senior / 15-1252 mid / 41-2031 entry): "
        f"{stats['spot_checks']}"
    )
    lines.append("")
    lines.append("## Regression comparison")
    lines.append("")
    lines.append(
        "_First Silver DQ execution for `base.onet_experience_profiles`; no prior run to compare._"
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
            "P0 gate cleared. Silver DQ is green for `onet-experience-requirements`. "
            "Proceed to Zone 3 (Gold) work."
        )
    else:
        lines.append(
            "P0 gate failed. Spec cannot be marked complete until "
            "`@governance-reviewer` acknowledges."
        )
    lines.append("")

    audit_path.write_text("\n".join(lines))


def main() -> int:
    print("=== Silver DQ execution: silver-onet-experience ===", flush=True)
    con = _materialize_duckdb()
    total = con.execute(
        "SELECT COUNT(*) FROM base.onet_experience_profiles"
    ).fetchone()[0]
    print(
        f"Materialized {total} rows into DuckDB as base.onet_experience_profiles",
        flush=True,
    )

    rules = load_rules()
    print(f"Executing {len(rules)} rules...", flush=True)
    results, p0_failures = execute_rules(con, rules)

    stats = gather_stats(con)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errored = sum(1 for r in results if r["status"] == "ERROR")

    ts = datetime.now(timezone.utc)
    run_id = hashlib.sha256(
        f"silver-onet-exp-{ts.isoformat()}".encode()
    ).hexdigest()[:8]
    stamp = ts.strftime("%Y%m%d-%H%M%S")

    out = {
        "run_id": run_id,
        "spec": "onet-experience-requirements",
        "zone": "silver",
        "table": "base.onet_experience_profiles",
        "iceberg_snapshot_id": SNAPSHOT_ID,
        "source": "iceberg_parquet",
        "source_path": str(PARQUET_GLOB),
        "executed_at": ts.isoformat(),
        "rules_file": "governance/dq-rules/silver-onet-experience.json",
        "rules_total": len(results),
        "rules_passed": passed,
        "rules_failed": failed,
        "rules_errored": errored,
        "p0_passed": len(p0_failures) == 0,
        "p0_failures": p0_failures,
        "results": results,
        "supplementary_stats": stats,
    }

    results_dir = PROJECT_ROOT / "governance" / "dq-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    results_path = results_dir / f"silver-onet-experience-{stamp}.json"
    results_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nWrote results to {results_path}")

    scorecard_dir = PROJECT_ROOT / "governance" / "dq-scorecards"
    scorecard_dir.mkdir(parents=True, exist_ok=True)
    scorecard_path = scorecard_dir / "silver-onet-experience.md"
    write_scorecard(scorecard_path, results, stats, ts, run_id)
    print(f"Wrote scorecard to {scorecard_path}")

    audit_dir = PROJECT_ROOT / "governance" / "audit-trail"
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / f"silver-onet-experience-{stamp}.md"
    write_audit_entry(
        audit_path, run_id, ts, results, stats, p0_failures, results_path, scorecard_path
    )
    print(f"Wrote audit trail to {audit_path}")

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
