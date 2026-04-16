"""Execute DQ rules for raw-ingest-college-scorecard-institution against live data.

This script:
1. Downloads the College Scorecard Institution CSV
2. Applies the same filter/coerce logic as the ingestor
3. Loads into in-memory DuckDB
4. Executes all 13 DQ rules
5. Writes results JSON and outputs stats for scorecard generation
"""

import csv
import io
import json
import hashlib
import zipfile
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
import duckdb

BASE_DIR = Path(__file__).resolve().parent.parent


def download_csv():
    """Download and parse the College Scorecard Institution CSV."""
    url = (
        "https://ed-public-download.scorecard.network/downloads/"
        "Most-Recent-Cohorts-Institution_04172025.zip"
    )
    print(f"Downloading from {url}...", flush=True)
    resp = requests.get(
        url,
        headers={"User-Agent": "FutureProof/0.1 (jeff@hyenastudios.com)"},
        timeout=600,
    )
    resp.raise_for_status()
    print(f"Downloaded {len(resp.content)} bytes", flush=True)

    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    print(f"ZIP contents: {zf.namelist()}", flush=True)
    csv_bytes = zf.read(csv_names[0])
    if csv_bytes.startswith(b"\xef\xbb\xbf"):
        csv_bytes = csv_bytes[3:]
    return csv_bytes.decode("utf-8")


COLUMN_MAP = {
    "UNITID": "unitid",
    "INSTNM": "instnm",
    "STABBR": "stabbr",
    "CONTROL": "control",
    "PREDDEG": "preddeg",
    "COSTT4_A": "costt4_a",
    "COSTT4_P": "costt4_p",
    "NPT4_PUB": "npt4_pub",
    "NPT4_PRIV": "npt4_priv",
    "NPT41_PUB": "npt41_pub",
    "NPT42_PUB": "npt42_pub",
    "NPT43_PUB": "npt43_pub",
    "NPT44_PUB": "npt44_pub",
    "NPT45_PUB": "npt45_pub",
    "NPT41_PRIV": "npt41_priv",
    "NPT42_PRIV": "npt42_priv",
    "NPT43_PRIV": "npt43_priv",
    "NPT44_PRIV": "npt44_priv",
    "NPT45_PRIV": "npt45_priv",
    "TUITIONFEE_IN": "tuitionfee_in",
    "TUITIONFEE_OUT": "tuitionfee_out",
    "ROOMBOARD_ON": "roomboard_on",
    "ROOMBOARD_OFF": "roomboard_off",
    "BOOKSUPPLY": "booksupply",
}

SENTINEL_VALUES = {"PrivacySuppressed", "PS", "NA", "NULL", ""}
STRING_FIELDS = {"instnm", "stabbr"}
LONG_FIELDS = {"unitid"}
INT_FIELDS = {"control", "preddeg"}


def coerce(field_name, value):
    """Coerce a raw string value to the appropriate Python type."""
    if value is None or value.strip() in SENTINEL_VALUES:
        return None
    value = value.strip()
    if field_name in STRING_FIELDS:
        return value
    if field_name in LONG_FIELDS:
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    if field_name in INT_FIELDS:
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def parse_and_filter(text):
    """Parse CSV text, filter to PREDDEG=3 or ICLEVEL=1, dedup on UNITID."""
    reader = csv.DictReader(io.StringIO(text))
    available = set(reader.fieldnames or [])
    target = set(COLUMN_MAP) & available

    seen = set()
    rows = []
    for row in reader:
        preddeg_raw = row.get("PREDDEG", "")
        iclevel_raw = row.get("ICLEVEL", "")
        try:
            preddeg_match = int(preddeg_raw) == 3
        except (ValueError, TypeError):
            preddeg_match = False
        try:
            iclevel_match = int(iclevel_raw) == 1
        except (ValueError, TypeError):
            iclevel_match = False

        if not (preddeg_match or iclevel_match):
            continue

        unitid = row.get("UNITID", "")
        if unitid in seen:
            continue
        seen.add(unitid)

        record = {}
        for csv_col, ice_col in COLUMN_MAP.items():
            record[ice_col] = coerce(ice_col, row.get(csv_col))
        if record.get("unitid") is None:
            continue
        rows.append(record)

    print(f"Filtered to {len(rows)} rows after PREDDEG=3/ICLEVEL=1 + dedup", flush=True)
    return rows


def load_duckdb(rows):
    """Load rows into in-memory DuckDB."""
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA raw")

    cols = list(COLUMN_MAP.values())
    col_defs = []
    for c in cols:
        if c in STRING_FIELDS:
            col_defs.append(f"{c} VARCHAR")
        elif c in LONG_FIELDS:
            col_defs.append(f"{c} BIGINT")
        elif c in INT_FIELDS:
            col_defs.append(f"{c} INTEGER")
        else:
            col_defs.append(f"{c} DOUBLE")

    create_sql = f"CREATE TABLE raw.college_scorecard_institution ({', '.join(col_defs)})"
    con.execute(create_sql)

    if rows:
        placeholders = ", ".join(["?" for _ in cols])
        insert_sql = f"INSERT INTO raw.college_scorecard_institution ({', '.join(cols)}) VALUES ({placeholders})"
        for r in rows:
            vals = [r.get(c) for c in cols]
            con.execute(insert_sql, vals)

    cnt = con.execute("SELECT COUNT(*) FROM raw.college_scorecard_institution").fetchone()[0]
    print(f"Loaded {cnt} rows into DuckDB", flush=True)
    return con


def execute_rules(con):
    """Execute all 13 DQ rules and return results."""
    rules_path = BASE_DIR / "governance" / "dq-rules" / "raw-ingest-college-scorecard-institution.json"
    with open(rules_path) as f:
        rule_defs = json.load(f)

    results = []
    p0_failures = []

    for rule in rule_defs["rules"]:
        rid = rule["rule_id"]
        name = rule["name"]
        priority = rule["priority"]
        sql = rule["sql"]
        threshold = rule["threshold"]

        try:
            result = con.execute(sql).fetchall()

            passed = False
            actual_value = None

            if threshold == "result = 0":
                val = result[0][0] if result else None
                actual_value = val
                passed = val == 0
            elif threshold == "result_count = 0":
                actual_value = len(result)
                passed = len(result) == 0
            elif threshold.startswith("result_count <="):
                max_val = int(threshold.split("<=")[1].strip())
                actual_value = len(result)
                passed = len(result) <= max_val
            else:
                actual_value = f"Unknown threshold: {threshold}"
                passed = False

            status = "PASS" if passed else "FAIL"
            results.append({
                "rule_id": rid,
                "name": name,
                "priority": priority,
                "status": status,
                "actual_value": actual_value,
                "threshold": threshold,
                "details": None if passed else f"Violation: actual={actual_value}",
            })

            if not passed and priority == "P0":
                p0_failures.append(rid)

            print(f"  {rid} [{priority}] {name}: {status} (actual={actual_value})", flush=True)

        except Exception as e:
            results.append({
                "rule_id": rid,
                "name": name,
                "priority": priority,
                "status": "ERROR",
                "actual_value": None,
                "threshold": threshold,
                "details": str(e),
            })
            print(f"  {rid} [{priority}] {name}: ERROR ({e})", flush=True)

    return results, p0_failures


def gather_stats(con):
    """Gather supplementary stats for the scorecard."""
    stats = {}
    stats["total_rows"] = con.execute(
        "SELECT COUNT(*) FROM raw.college_scorecard_institution"
    ).fetchone()[0]
    stats["distinct_unitids"] = con.execute(
        "SELECT COUNT(DISTINCT unitid) FROM raw.college_scorecard_institution"
    ).fetchone()[0]
    stats["control_dist"] = [
        {"control": r[0], "count": r[1]}
        for r in con.execute(
            "SELECT control, COUNT(*) FROM raw.college_scorecard_institution GROUP BY control ORDER BY control"
        ).fetchall()
    ]
    stats["costt4_a_nonnull"], stats["costt4_a_min"], stats["costt4_a_max"], stats["costt4_a_median"] = con.execute(
        "SELECT COUNT(*), MIN(costt4_a), MAX(costt4_a), ROUND(MEDIAN(costt4_a), 0) "
        "FROM raw.college_scorecard_institution WHERE costt4_a IS NOT NULL"
    ).fetchone()
    stats["npt4_pub_nonnull"], stats["npt4_pub_min"], stats["npt4_pub_max"] = con.execute(
        "SELECT COUNT(*), MIN(npt4_pub), MAX(npt4_pub) "
        "FROM raw.college_scorecard_institution WHERE npt4_pub IS NOT NULL"
    ).fetchone()
    stats["npt4_priv_nonnull"], stats["npt4_priv_min"], stats["npt4_priv_max"] = con.execute(
        "SELECT COUNT(*), MIN(npt4_priv), MAX(npt4_priv) "
        "FROM raw.college_scorecard_institution WHERE npt4_priv IS NOT NULL"
    ).fetchone()
    stats["tuitionfee_in_nonnull"], stats["tuitionfee_in_min"], stats["tuitionfee_in_max"] = con.execute(
        "SELECT COUNT(*), MIN(tuitionfee_in), MAX(tuitionfee_in) "
        "FROM raw.college_scorecard_institution WHERE tuitionfee_in IS NOT NULL"
    ).fetchone()
    stats["roomboard_on_nonnull"], stats["roomboard_on_min"], stats["roomboard_on_max"] = con.execute(
        "SELECT COUNT(*), MIN(roomboard_on), MAX(roomboard_on) "
        "FROM raw.college_scorecard_institution WHERE roomboard_on IS NOT NULL"
    ).fetchone()
    stats["coa_coverage_pct"] = con.execute(
        "SELECT ROUND(100.0 * SUM(CASE WHEN costt4_a IS NOT NULL OR costt4_p IS NOT NULL THEN 1 ELSE 0 END) "
        "/ COUNT(*), 1) FROM raw.college_scorecard_institution"
    ).fetchone()[0]
    stats["pub_npt4_coverage_pct"] = con.execute(
        "SELECT ROUND(100.0 * SUM(CASE WHEN control=1 AND npt4_pub IS NOT NULL THEN 1 ELSE 0 END) "
        "/ NULLIF(SUM(CASE WHEN control=1 THEN 1 ELSE 0 END), 0), 1) "
        "FROM raw.college_scorecard_institution"
    ).fetchone()[0]
    stats["priv_npt4_coverage_pct"] = con.execute(
        "SELECT ROUND(100.0 * SUM(CASE WHEN control=2 AND npt4_priv IS NOT NULL THEN 1 ELSE 0 END) "
        "/ NULLIF(SUM(CASE WHEN control=2 THEN 1 ELSE 0 END), 0), 1) "
        "FROM raw.college_scorecard_institution"
    ).fetchone()[0]
    stats["q1_gt_q5_pub"] = con.execute(
        "SELECT COUNT(*) FROM raw.college_scorecard_institution "
        "WHERE control = 1 AND npt41_pub IS NOT NULL AND npt45_pub IS NOT NULL AND npt41_pub > npt45_pub"
    ).fetchone()[0]
    stats["q1_gt_q5_priv"] = con.execute(
        "SELECT COUNT(*) FROM raw.college_scorecard_institution "
        "WHERE control IN (2, 3) AND npt41_priv IS NOT NULL AND npt45_priv IS NOT NULL AND npt41_priv > npt45_priv"
    ).fetchone()[0]
    return stats


def main():
    text = download_csv()
    rows = parse_and_filter(text)
    con = load_duckdb(rows)

    print("\nExecuting DQ rules...", flush=True)
    results, p0_failures = execute_rules(con)
    stats = gather_stats(con)

    # Write results JSON
    ts = datetime.now(timezone.utc).isoformat()
    run_id = hashlib.sha256(ts.encode()).hexdigest()[:8]
    ts_slug = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    passed_count = sum(1 for r in results if r["status"] == "PASS")
    failed_count = sum(1 for r in results if r["status"] == "FAIL")
    errored_count = sum(1 for r in results if r["status"] == "ERROR")

    result_json = {
        "run_id": run_id,
        "spec": "raw-ingest-college-scorecard-institution",
        "executed_at": ts,
        "rules_total": len(results),
        "rules_passed": passed_count,
        "rules_failed": failed_count,
        "rules_errored": errored_count,
        "p0_passed": len(p0_failures) == 0,
        "results": results,
        "supplementary_stats": {k: v for k, v in stats.items()},
    }

    result_path = BASE_DIR / "governance" / "dq-results" / f"raw-ingest-college-scorecard-institution-{ts_slug}.json"
    with open(result_path, "w") as f:
        json.dump(result_json, f, indent=2, default=str)

    evidence_hash = hashlib.sha256(
        json.dumps(result_json, indent=2, default=str).encode()
    ).hexdigest()[:16]

    print(f"\n{'='*60}")
    print("DQ EXECUTION SUMMARY")
    print(f"{'='*60}")
    print(f"Spec:     raw-ingest-college-scorecard-institution")
    print(f"Run ID:   {run_id}")
    print(f"Time:     {ts}")
    print(f"Evidence: {evidence_hash}")
    print(f"Results:  {result_path}")
    print(f"Total:    {len(results)} rules")
    print(f"Passed:   {passed_count}")
    print(f"Failed:   {failed_count}")
    print(f"Errored:  {errored_count}")
    print(f"P0 gate:  {'PASS' if len(p0_failures) == 0 else 'FAIL - ' + ', '.join(p0_failures)}")
    print(f"\nSupplementary Stats:")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # Save for scorecard generation
    output = {
        "results": results,
        "stats": stats,
        "run_id": run_id,
        "ts": ts,
        "evidence_hash": evidence_hash,
        "result_path": str(result_path),
        "passed_count": passed_count,
        "failed_count": failed_count,
        "errored_count": errored_count,
        "p0_failures": p0_failures,
    }
    with open("/tmp/dq_csi_output.json", "w") as f:
        json.dump(output, f, indent=2, default=str)


if __name__ == "__main__":
    main()
