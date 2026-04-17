"""Simulate the Gold LEFT JOIN for CSI enrichment before materialization.

Reads:
  - Silver base.college_scorecard_institution  (3,039 institutions)
  - Gold   consumable.career_outcomes          (pre-enrichment)

Produces the stats needed to calibrate GLD-CSI-005/006/007/008 thresholds.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from brightsmith.infra.iceberg_setup import get_catalog


PROJECT_DIR = Path("/Users/jcernauske/code/bright/futureproof-data")
SILVER_WH = PROJECT_DIR / "data" / "silver" / "iceberg_warehouse"
GOLD_WH = PROJECT_DIR / "data" / "gold" / "iceberg_warehouse"
CATALOG_DB = PROJECT_DIR / "data" / "catalog" / "catalog.db"


def main() -> None:
    silver_catalog = get_catalog(SILVER_WH, CATALOG_DB)
    gold_catalog = get_catalog(GOLD_WH, CATALOG_DB)

    csi_tbl = silver_catalog.load_table("base.college_scorecard_institution")
    co_tbl = gold_catalog.load_table("consumable.career_outcomes")

    csi_arrow = csi_tbl.scan().to_arrow()
    co_arrow = co_tbl.scan().to_arrow()

    print(f"Silver base.college_scorecard_institution rows: {csi_arrow.num_rows}")
    print(f"Gold consumable.career_outcomes rows: {co_arrow.num_rows}")
    print(f"Silver columns: {csi_arrow.column_names}")
    print(f"Gold columns: {co_arrow.column_names[:10]}...")

    con = duckdb.connect()
    con.register("csi", csi_arrow)
    con.register("co", co_arrow)

    out: dict = {}

    # 1. Row count of career_outcomes
    out["co_row_count"] = con.execute("SELECT COUNT(*) FROM co").fetchone()[0]
    # 2. Distinct UNITIDs
    out["co_distinct_unitids"] = con.execute("SELECT COUNT(DISTINCT unitid) FROM co").fetchone()[0]
    out["csi_distinct_unitids"] = con.execute("SELECT COUNT(DISTINCT unitid) FROM csi").fetchone()[0]
    out["csi_row_count"] = con.execute("SELECT COUNT(*) FROM csi").fetchone()[0]

    # Duplicate check on left side
    out["co_unitid_is_unique_to_grain"] = con.execute(
        "SELECT COUNT(*) - COUNT(DISTINCT (unitid, cipcode, credential_level)) FROM co"
    ).fetchone()[0]

    # 3. Overlap
    out["overlap_unitids"] = con.execute("""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT unitid FROM co
        ) c INNER JOIN (SELECT DISTINCT unitid FROM csi) i USING (unitid)
    """).fetchone()[0]

    # 4. Unmatched UNITIDs
    out["unmatched_distinct_unitids"] = con.execute("""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT unitid FROM co
            EXCEPT
            SELECT DISTINCT unitid FROM csi
        )
    """).fetchone()[0]

    # Reverse: CSI unitids NOT in CO (not needed for DQ, but context)
    out["csi_unitids_not_in_co"] = con.execute("""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT unitid FROM csi
            EXCEPT
            SELECT DISTINCT unitid FROM co
        )
    """).fetchone()[0]

    # Sample unmatched INSTNMs
    sample_unmatched = con.execute("""
        SELECT DISTINCT unitid, institution_name
        FROM co
        WHERE unitid NOT IN (SELECT DISTINCT unitid FROM csi)
        ORDER BY institution_name
        LIMIT 10
    """).fetchall()
    out["sample_unmatched_institutions"] = [{"unitid": r[0], "institution_name": r[1]} for r in sample_unmatched]

    # Row-impact of unmatched unitids
    out["rows_with_unmatched_unitid"] = con.execute("""
        SELECT COUNT(*) FROM co
        WHERE unitid NOT IN (SELECT DISTINCT unitid FROM csi)
    """).fetchone()[0]

    # 5. Simulate the LEFT JOIN and compute null rates post-join
    con.execute("""
        CREATE TEMP VIEW joined AS
        SELECT
            co.unitid,
            co.cipcode,
            co.credential_level,
            co.institution_name AS co_inst,
            csi.net_price_annual,
            csi.cost_of_attendance_annual,
            csi.net_price_4yr,
            csi.institution_control,
            csi.tuition_in_state,
            csi.tuition_out_of_state,
            csi.room_board_on_campus
        FROM co
        LEFT JOIN csi ON co.unitid = csi.unitid
    """)

    out["joined_row_count"] = con.execute("SELECT COUNT(*) FROM joined").fetchone()[0]

    null_fields = [
        "net_price_annual",
        "cost_of_attendance_annual",
        "net_price_4yr",
        "institution_control",
        "tuition_in_state",
        "tuition_out_of_state",
        "room_board_on_campus",
    ]
    null_rates = {}
    for f in null_fields:
        result = con.execute(f"""
            SELECT
                SUM(CASE WHEN {f} IS NULL THEN 1 ELSE 0 END) AS nulls,
                COUNT(*) AS total
            FROM joined
        """).fetchone()
        null_rates[f] = {
            "nulls": result[0],
            "total": result[1],
            "non_null": result[1] - result[0],
            "null_pct": result[0] / result[1] * 100.0 if result[1] else None,
            "non_null_pct": (result[1] - result[0]) / result[1] * 100.0 if result[1] else None,
        }
    out["post_join_null_rates"] = null_rates

    # 6. Distribution of institution_control post-join
    control_dist = con.execute("""
        SELECT
            COALESCE(institution_control, '(null)') AS control_label,
            COUNT(*) AS rows,
            ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM joined), 2) AS pct
        FROM joined
        GROUP BY 1
        ORDER BY rows DESC
    """).fetchall()
    out["post_join_institution_control_distribution"] = [
        {"control": r[0], "rows": r[1], "pct": r[2]} for r in control_dist
    ]

    # 7. Spot check: pick a few known high-profile institutions by keyword
    spot_checks = con.execute("""
        SELECT
            co.unitid,
            co.institution_name,
            MAX(csi.institution_control) AS control,
            MAX(csi.cost_of_attendance_annual) AS coa,
            MAX(csi.net_price_annual) AS np,
            MAX(csi.tuition_out_of_state) AS tuition_oos,
            COUNT(DISTINCT co.cipcode) AS program_count
        FROM co
        LEFT JOIN csi ON co.unitid = csi.unitid
        WHERE co.institution_name ILIKE '%Harvard%'
           OR co.institution_name ILIKE '%Stanford%'
           OR co.institution_name ILIKE '%Massachusetts Institute of Technology%'
           OR co.institution_name ILIKE '%Princeton%'
           OR co.institution_name ILIKE '%Yale University%'
        GROUP BY co.unitid, co.institution_name
        ORDER BY co.institution_name
        LIMIT 20
    """).fetchall()
    out["spot_check_elite"] = [
        {
            "unitid": r[0],
            "institution_name": r[1],
            "institution_control": r[2],
            "cost_of_attendance_annual": r[3],
            "net_price_annual": r[4],
            "tuition_oos": r[5],
            "program_count": r[6],
        }
        for r in spot_checks
    ]

    # Unmatched by control-share (what types of institutions are in CO but not CSI?)
    # Since CSI is the only source for institution_control, unmatched rows have no control signal.
    # Check the program-count distribution of unmatched unitids.
    unmatched_program_dist = con.execute("""
        WITH per_unmatched AS (
            SELECT co.unitid, COUNT(*) AS row_count
            FROM co
            WHERE co.unitid NOT IN (SELECT DISTINCT unitid FROM csi)
            GROUP BY co.unitid
        )
        SELECT
            COUNT(*) AS unmatched_unitids,
            SUM(row_count) AS total_unmatched_rows,
            MIN(row_count) AS min_rows_per_unitid,
            AVG(row_count) AS avg_rows_per_unitid,
            MEDIAN(row_count) AS median_rows_per_unitid,
            MAX(row_count) AS max_rows_per_unitid
        FROM per_unmatched
    """).fetchone()
    out["unmatched_program_distribution"] = {
        "unmatched_unitids": unmatched_program_dist[0],
        "total_unmatched_rows": unmatched_program_dist[1],
        "min_rows_per_unitid": unmatched_program_dist[2],
        "avg_rows_per_unitid": float(unmatched_program_dist[3]) if unmatched_program_dist[3] else None,
        "median_rows_per_unitid": float(unmatched_program_dist[4]) if unmatched_program_dist[4] else None,
        "max_rows_per_unitid": unmatched_program_dist[5],
    }

    # Coverage stratified by CSI-matched status (sanity check on null rates)
    matched_coverage = con.execute("""
        SELECT
            COUNT(*) AS total_rows,
            SUM(CASE WHEN csi.unitid IS NOT NULL THEN 1 ELSE 0 END) AS rows_matched_to_csi,
            SUM(CASE WHEN csi.net_price_annual IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_np,
            SUM(CASE WHEN csi.cost_of_attendance_annual IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_coa,
            SUM(CASE WHEN csi.institution_control IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_control
        FROM co
        LEFT JOIN csi ON co.unitid = csi.unitid
    """).fetchone()
    out["post_join_coverage_stratified"] = {
        "total_rows": matched_coverage[0],
        "rows_matched_to_csi": matched_coverage[1],
        "rows_with_np": matched_coverage[2],
        "rows_with_coa": matched_coverage[3],
        "rows_with_control": matched_coverage[4],
    }

    # Unmatched UNITIDs verified: how many distinct UNITIDs have net_price_annual IS NULL after join?
    out["distinct_unitids_with_null_np_post_join"] = con.execute("""
        SELECT COUNT(DISTINCT co.unitid)
        FROM co
        LEFT JOIN csi ON co.unitid = csi.unitid
        WHERE csi.net_price_annual IS NULL
    """).fetchone()[0]

    # Distribution of institution_control by unique-unitid (not rows)
    control_unitid_dist = con.execute("""
        SELECT
            COALESCE(csi.institution_control, '(null - unmatched)') AS control,
            COUNT(DISTINCT co.unitid) AS unitids
        FROM co
        LEFT JOIN csi ON co.unitid = csi.unitid
        GROUP BY 1
        ORDER BY unitids DESC
    """).fetchall()
    out["institution_control_distinct_unitids"] = [
        {"control": r[0], "unitids": r[1]} for r in control_unitid_dist
    ]

    # Row-identical co-null check: how often is NP null but COA not, or vice versa, post-join?
    conull_check = con.execute("""
        SELECT
            SUM(CASE WHEN net_price_annual IS NULL AND cost_of_attendance_annual IS NULL THEN 1 ELSE 0 END) AS both_null,
            SUM(CASE WHEN net_price_annual IS NULL AND cost_of_attendance_annual IS NOT NULL THEN 1 ELSE 0 END) AS np_only_null,
            SUM(CASE WHEN net_price_annual IS NOT NULL AND cost_of_attendance_annual IS NULL THEN 1 ELSE 0 END) AS coa_only_null,
            SUM(CASE WHEN net_price_annual IS NOT NULL AND cost_of_attendance_annual IS NOT NULL THEN 1 ELSE 0 END) AS both_pop
        FROM joined
    """).fetchone()
    out["np_vs_coa_conull_matrix"] = {
        "both_null": conull_check[0],
        "np_only_null": conull_check[1],
        "coa_only_null": conull_check[2],
        "both_populated": conull_check[3],
    }

    # ---- OUTPUT ----
    out_path = PROJECT_DIR / "docs" / "sessions" / "eda-gold-csi-join-stats.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nWrote: {out_path}")
    print("\n===== KEY RESULTS =====")
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
