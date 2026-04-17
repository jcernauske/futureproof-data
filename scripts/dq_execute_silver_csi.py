"""Execute Silver DQ rules for silver-base-college-scorecard-institution.

This script:
1. Reads the cached College Scorecard Institution CSV (or downloads from
   the fallback URL if not cached).
2. Applies the Bronze ingestor filter (PREDDEG=3 OR ICLEVEL=1) + dedup on UNITID
   + sentinel-to-null coercion.
3. Applies the Silver transformer's ``transform_row`` to produce derived fields.
4. Loads the 3,039 rows into in-memory DuckDB as ``base.college_scorecard_institution``.
5. Executes all 17 SLV-CSI-* rules.
6. Writes a timestamped JSON results file to governance/dq-results/.
7. Prints a summary suitable for scorecard generation.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.silver.college_scorecard_institution_transformer import transform_row  # noqa: E402

CACHED_CSV = Path("/tmp/Most-Recent-Cohorts-Institution.csv")
CACHED_ZIP = Path("/tmp/Most-Recent-Cohorts-Institution.zip")
FALLBACK_URL = (
    "https://ed-public-download.scorecard.network/downloads/"
    "Most-Recent-Cohorts-Institution_04172025.zip"
)
USER_AGENT = "FutureProof/0.1 (jeff@hyenastudios.com)"

COLUMN_MAP: dict[str, str] = {
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
STRING_FIELDS = frozenset({"instnm", "stabbr"})
LONG_FIELDS = frozenset({"unitid"})
INT_FIELDS = frozenset({"control", "preddeg"})


def _coerce(field_name: str, value: str | None) -> Any:
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


def load_csv_text() -> str:
    """Read cached CSV or fall back to ZIP / remote download."""
    if CACHED_CSV.exists():
        print(f"Using cached CSV at {CACHED_CSV}", flush=True)
        text = CACHED_CSV.read_text(encoding="utf-8-sig")
        return text
    if CACHED_ZIP.exists():
        print(f"Using cached ZIP at {CACHED_ZIP}", flush=True)
        content = CACHED_ZIP.read_bytes()
    else:
        print(f"Downloading from {FALLBACK_URL}...", flush=True)
        import requests

        resp = requests.get(FALLBACK_URL, headers={"User-Agent": USER_AGENT}, timeout=600)
        resp.raise_for_status()
        content = resp.content
    zf = zipfile.ZipFile(io.BytesIO(content))
    csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    csv_bytes = zf.read(csv_names[0])
    if csv_bytes.startswith(b"\xef\xbb\xbf"):
        csv_bytes = csv_bytes[3:]
    return csv_bytes.decode("utf-8")


def parse_and_filter(text: str) -> list[dict]:
    """Apply PREDDEG=3 OR ICLEVEL=1 filter + dedup on UNITID (Bronze parity)."""
    reader = csv.DictReader(io.StringIO(text))
    available = set(reader.fieldnames or [])
    target = set(COLUMN_MAP.keys()) & available

    seen: set[str] = set()
    rows: list[dict] = []
    for row in reader:
        try:
            pred_match = int(row.get("PREDDEG", "")) == 3
        except (ValueError, TypeError):
            pred_match = False
        try:
            icl_match = int(row.get("ICLEVEL", "")) == 1
        except (ValueError, TypeError):
            icl_match = False
        if not (pred_match or icl_match):
            continue
        unitid = row.get("UNITID", "")
        if unitid in seen:
            continue
        seen.add(unitid)
        rows.append({col: row[col] for col in target})
    return rows


def bronze_flatten(raw_rows: list[dict]) -> list[dict]:
    """Mimic the Bronze ingestor flatten() — sentinel→null + type coercion."""
    flat: list[dict] = []
    skipped = 0
    for raw_row in raw_rows:
        record: dict = {}
        for csv_col, iceberg_col in COLUMN_MAP.items():
            record[iceberg_col] = _coerce(iceberg_col, raw_row.get(csv_col))
        if record.get("unitid") is None:
            skipped += 1
            continue
        # Bronze metadata the Silver transformer expects on each row.
        record["load_date"] = datetime(2025, 4, 17).date()
        flat.append(record)
    if skipped:
        print(f"Bronze flatten skipped {skipped} rows with null UNITID", flush=True)
    return flat


def run_silver_transform(bronze_rows: list[dict]) -> list[dict]:
    silver: list[dict] = []
    skipped = 0
    for br in bronze_rows:
        rec = transform_row(br)
        if rec is None:
            skipped += 1
            continue
        silver.append(rec)
    if skipped:
        print(f"Silver transform skipped {skipped} rows", flush=True)
    return silver


def load_duckdb(silver_rows: list[dict]) -> duckdb.DuckDBPyConnection:
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
        "record_id", "unitid", "institution_name", "state_abbr", "institution_control",
        "cost_of_attendance_annual", "cost_of_attendance_4yr",
        "net_price_annual", "net_price_4yr",
        "net_price_q1", "net_price_q2", "net_price_q3", "net_price_q4", "net_price_q5",
        "tuition_in_state", "tuition_out_of_state",
        "room_board_on_campus", "room_board_off_campus", "books_supplies",
        "costt4_a_raw", "costt4_p_raw",
        "npt4_pub_raw", "npt4_priv_raw",
        "npt41_pub_raw", "npt42_pub_raw", "npt43_pub_raw", "npt44_pub_raw", "npt45_pub_raw",
        "npt41_priv_raw", "npt42_priv_raw", "npt43_priv_raw", "npt44_priv_raw", "npt45_priv_raw",
        "source_load_date", "ingested_at",
    ]
    placeholders = ", ".join(["?"] * len(cols))
    insert_sql = f"INSERT INTO base.college_scorecard_institution ({', '.join(cols)}) VALUES ({placeholders})"
    rows_tuples = [tuple(row.get(c) for c in cols) for row in silver_rows]
    con.executemany(insert_sql, rows_tuples)
    return con


# ---------------------------------------------------------------------------
# Rule execution
# ---------------------------------------------------------------------------


def load_rules() -> list[dict]:
    path = BASE_DIR / "governance" / "dq-rules" / "silver-base-college-scorecard-institution.json"
    return json.loads(path.read_text())["rules"]


def _threshold_passes(rule: dict, actual: int) -> bool:
    t = rule["threshold"].replace(" ", "")
    if t == "result=0":
        return actual == 0
    if t == "result_count=0":
        return actual == 0
    if t.startswith("result_count<="):
        return actual <= int(t.split("<=", 1)[1])
    if t.startswith("result<="):
        return actual <= int(t.split("<=", 1)[1])
    raise ValueError(f"Unsupported threshold: {rule['threshold']}")


def execute_rule(con: duckdb.DuckDBPyConnection, rule: dict) -> dict:
    """Execute a single rule and return a result dict."""
    sql = rule["sql"]
    # The rule SQL returns either:
    #  - a scalar violation flag (0/1)   — "result = 0" or "result <= N"
    #  - a set of violating rows          — "result_count = 0" or "result_count <= N"
    # For the 'scalar' variant the first column of the first row is the flag.
    try:
        res = con.execute(sql).fetchall()
    except Exception as exc:  # noqa: BLE001
        return {
            "rule_id": rule["rule_id"],
            "name": rule["name"],
            "priority": rule["priority"],
            "status": "ERROR",
            "actual_value": None,
            "threshold": rule["threshold"],
            "details": f"SQL error: {exc}",
        }

    threshold = rule["threshold"].replace(" ", "")
    if threshold.startswith("result=") or threshold.startswith("result<="):
        actual = int(res[0][0]) if res else 0
    else:
        actual = len(res)

    passed = _threshold_passes(rule, actual)
    return {
        "rule_id": rule["rule_id"],
        "name": rule["name"],
        "priority": rule["priority"],
        "status": "PASS" if passed else "FAIL",
        "actual_value": actual,
        "threshold": rule["threshold"],
        "details": None,
    }


def collect_supplementary_stats(con: duckdb.DuckDBPyConnection) -> dict:
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
        """
        SELECT institution_control, COUNT(*) AS n
        FROM base.college_scorecard_institution
        GROUP BY institution_control ORDER BY institution_control
        """
    ).fetchall()
    stats["control_distribution"] = [{"label": c, "count": n} for c, n in ctl]

    # Coverage
    row = con.execute(
        """
        SELECT
            SUM(CASE WHEN net_price_annual IS NOT NULL THEN 1 ELSE 0 END) AS np_nn,
            SUM(CASE WHEN cost_of_attendance_annual IS NOT NULL THEN 1 ELSE 0 END) AS coa_nn,
            COUNT(*) AS total
        FROM base.college_scorecard_institution
        """
    ).fetchone()
    stats["net_price_annual_coverage_pct"] = round(100.0 * row[0] / row[2], 2)
    stats["cost_of_attendance_annual_coverage_pct"] = round(100.0 * row[1] / row[2], 2)

    # Coverage by control
    per_ctl = con.execute(
        """
        SELECT institution_control,
               COUNT(*) AS total,
               SUM(CASE WHEN net_price_annual IS NOT NULL THEN 1 ELSE 0 END) AS np_nn
        FROM base.college_scorecard_institution
        GROUP BY institution_control ORDER BY institution_control
        """
    ).fetchall()
    stats["coverage_by_control"] = [
        {"control": c, "total": t, "np_nonnull": n, "np_pct": round(100.0 * n / t, 2)}
        for c, t, n in per_ctl
    ]

    # Derived field profiles
    for col in ("net_price_annual", "net_price_4yr", "cost_of_attendance_annual", "cost_of_attendance_4yr"):
        row = con.execute(
            f"SELECT MIN({col}), MAX({col}), MEDIAN({col}), COUNT({col}) "
            f"FROM base.college_scorecard_institution"
        ).fetchone()
        stats[f"{col}_profile"] = {
            "min": row[0],
            "max": row[1],
            "median": row[2],
            "nonnull": row[3],
        }

    # Invariants
    stats["np_le_coa_violations"] = con.execute(
        """
        SELECT COUNT(*) FROM base.college_scorecard_institution
        WHERE net_price_annual IS NOT NULL
          AND cost_of_attendance_annual IS NOT NULL
          AND net_price_annual > cost_of_attendance_annual
        """
    ).fetchone()[0]
    stats["np4yr_tautology_violations"] = con.execute(
        """
        SELECT COUNT(*) FROM base.college_scorecard_institution
        WHERE net_price_annual IS NOT NULL
          AND (net_price_4yr IS NULL OR ABS(net_price_4yr - (net_price_annual * 4)) > 0.01)
        """
    ).fetchone()[0]
    stats["coa4yr_tautology_violations"] = con.execute(
        """
        SELECT COUNT(*) FROM base.college_scorecard_institution
        WHERE cost_of_attendance_annual IS NOT NULL
          AND (cost_of_attendance_4yr IS NULL
               OR ABS(cost_of_attendance_4yr - (cost_of_attendance_annual * 4)) > 0.01)
        """
    ).fetchone()[0]
    stats["q1_gt_q5_total"] = con.execute(
        """
        SELECT COUNT(*) FROM base.college_scorecard_institution
        WHERE net_price_q1 IS NOT NULL AND net_price_q5 IS NOT NULL
          AND net_price_q1 > net_price_q5
        """
    ).fetchone()[0]

    per_ctl_q = con.execute(
        """
        SELECT institution_control, COUNT(*) AS viol
        FROM base.college_scorecard_institution
        WHERE net_price_q1 IS NOT NULL AND net_price_q5 IS NOT NULL
          AND net_price_q1 > net_price_q5
        GROUP BY institution_control ORDER BY institution_control
        """
    ).fetchall()
    stats["q1_gt_q5_by_control"] = [{"control": c, "violations": v} for c, v in per_ctl_q]

    return stats


def main() -> int:
    print("=== Silver DQ execution: silver-base-college-scorecard-institution ===", flush=True)
    text = load_csv_text()
    raw_rows = parse_and_filter(text)
    print(f"Parsed {len(raw_rows)} rows after Bronze filter", flush=True)
    bronze_rows = bronze_flatten(raw_rows)
    print(f"Bronze-flatten produced {len(bronze_rows)} rows", flush=True)
    silver_rows = run_silver_transform(bronze_rows)
    print(f"Silver transform produced {len(silver_rows)} rows", flush=True)

    con = load_duckdb(silver_rows)
    total = con.execute("SELECT COUNT(*) FROM base.college_scorecard_institution").fetchone()[0]
    print(f"Loaded {total} rows into DuckDB base.college_scorecard_institution", flush=True)

    rules = load_rules()
    print(f"Executing {len(rules)} rules...", flush=True)
    results = [execute_rule(con, r) for r in rules]

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errored = sum(1 for r in results if r["status"] == "ERROR")
    p0_passed = all(r["status"] == "PASS" for r in results if r["priority"] == "P0")

    stats = collect_supplementary_stats(con)

    ts = datetime.now(timezone.utc)
    run_id = hashlib.sha256(
        f"silver-csi-{ts.isoformat()}".encode()
    ).hexdigest()[:8]

    out = {
        "run_id": run_id,
        "spec": "silver-base-college-scorecard-institution",
        "zone": "silver",
        "table": "base.college_scorecard_institution",
        "executed_at": ts.isoformat(),
        "rules_total": len(results),
        "rules_passed": passed,
        "rules_failed": failed,
        "rules_errored": errored,
        "p0_passed": p0_passed,
        "results": results,
        "supplementary_stats": stats,
    }

    out_dir = BASE_DIR / "governance" / "dq-results"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = ts.strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"silver-base-college-scorecard-institution-{stamp}.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"Wrote results to {out_path}", flush=True)

    print(f"\nTotals: pass={passed} fail={failed} error={errored}  P0 gate: {'PASS' if p0_passed else 'FAIL'}")
    for r in results:
        print(f"  [{r['priority']}] {r['rule_id']}  {r['status']}  actual={r['actual_value']}  thr='{r['threshold']}'")

    return 0 if (failed == 0 and errored == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
