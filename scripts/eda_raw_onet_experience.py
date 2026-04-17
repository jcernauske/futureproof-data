"""EDA for raw.onet_experience (Bronze zone) per spec onet-experience-requirements.md.

Produces stats the EDA report (`governance/eda/raw-onet-experience-eda.md`) and
downstream DQ-rule writer need. Output is JSON on stdout + a file.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb

PROJECT_DIR = Path("/Users/jcernauske/code/bright/futureproof-data")
BRONZE_WH = PROJECT_DIR / "data" / "bronze" / "iceberg_warehouse"
CATALOG_DB = PROJECT_DIR / "data" / "catalog" / "catalog.db"
OUT_JSON = PROJECT_DIR / "docs" / "sessions" / "eda-raw-onet-experience-stats.json"


def main() -> None:
    sys.path.insert(0, str(PROJECT_DIR / "src"))

    # The table was written by the ingestor to
    # data/bronze/iceberg_warehouse/bronze/onet_experience. The namespace
    # wasn't registered in the SQL catalog at ingest time; we read the
    # parquet data file(s) the ingestor produced directly.
    data_dir = BRONZE_WH / "bronze" / "onet_experience" / "data"
    parquet_files = sorted(data_dir.glob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"No parquet files under {data_dir}")

    con = duckdb.connect()
    files_literal = ", ".join(f"'{p}'" for p in parquet_files)
    con.execute(f"CREATE VIEW ex AS SELECT * FROM read_parquet([{files_literal}])")
    arrow_cols = [c[0] for c in con.execute("SELECT * FROM ex LIMIT 0").description]
    print(f"columns: {arrow_cols}")

    # Minimal shim so the rest of this script can still read `arrow.column_names`
    # and `arrow.num_rows` without a real Arrow object.
    class _ArrowLike:
        column_names = arrow_cols
        num_rows = con.execute("SELECT COUNT(*) FROM ex").fetchone()[0]

    arrow = _ArrowLike()
    print(f"rows: {arrow.num_rows}")

    out: dict = {}
    out["row_count"] = con.execute("SELECT COUNT(*) FROM ex").fetchone()[0]
    out["field_count"] = len(arrow.column_names)
    out["columns"] = arrow.column_names

    # 1. Rows by scale
    out["scale_distribution"] = [
        {"scale_id": r[0], "rows": r[1]}
        for r in con.execute(
            "SELECT scale_id, COUNT(*) FROM ex GROUP BY 1 ORDER BY 2 DESC"
        ).fetchall()
    ]

    # 2. Occupation coverage
    out["distinct_onet_soc_codes"] = con.execute(
        "SELECT COUNT(DISTINCT onet_soc_code) FROM ex"
    ).fetchone()[0]
    out["distinct_bls_soc_codes"] = con.execute(
        "SELECT COUNT(DISTINCT SUBSTR(onet_soc_code, 1, 7)) FROM ex"
    ).fetchone()[0]

    coverage_per_scale = con.execute(
        """
        SELECT scale_id, COUNT(DISTINCT onet_soc_code) AS occ_count
        FROM ex
        GROUP BY 1 ORDER BY 1
        """
    ).fetchall()
    out["distinct_occupations_per_scale"] = [
        {"scale_id": r[0], "occupations": r[1]} for r in coverage_per_scale
    ]

    # Occupations missing one or more scales
    coverage_matrix = con.execute(
        """
        WITH per_occ_scale AS (
            SELECT onet_soc_code, scale_id
            FROM ex GROUP BY 1,2
        ),
        per_occ AS (
            SELECT onet_soc_code, COUNT(DISTINCT scale_id) AS scale_count
            FROM per_occ_scale GROUP BY 1
        )
        SELECT scale_count, COUNT(*) FROM per_occ GROUP BY 1 ORDER BY 1
        """
    ).fetchall()
    out["occupations_by_scale_count"] = [
        {"scale_count": r[0], "occupations": r[1]} for r in coverage_matrix
    ]

    # 3. Category distribution per scale (distinct count)
    cat_distinct_per_scale = con.execute(
        """
        SELECT scale_id, COUNT(DISTINCT category) AS cat_count,
               MIN(category) AS min_cat, MAX(category) AS max_cat
        FROM ex GROUP BY 1 ORDER BY 1
        """
    ).fetchall()
    out["distinct_categories_per_scale"] = [
        {"scale_id": r[0], "category_count": r[1], "min_cat": r[2], "max_cat": r[3]}
        for r in cat_distinct_per_scale
    ]

    # Also: do all occupations for each scale have the expected category count?
    per_occ_cat = con.execute(
        """
        WITH c AS (
          SELECT scale_id, onet_soc_code, COUNT(DISTINCT category) AS cat_n
          FROM ex GROUP BY 1,2
        )
        SELECT scale_id, cat_n, COUNT(*) AS occupations
        FROM c GROUP BY 1,2 ORDER BY 1, 2
        """
    ).fetchall()
    out["category_count_distribution_per_scale"] = [
        {"scale_id": r[0], "category_count": r[1], "occupations": r[2]}
        for r in per_occ_cat
    ]

    # Element id/name per scale (sanity check - RW should only see 3.A.1)
    element_per_scale = con.execute(
        """
        SELECT scale_id, element_id, element_name, COUNT(*) AS rows
        FROM ex GROUP BY 1,2,3 ORDER BY 1,4 DESC
        """
    ).fetchall()
    out["element_per_scale"] = [
        {"scale_id": r[0], "element_id": r[1], "element_name": r[2], "rows": r[3]}
        for r in element_per_scale
    ]

    # 4. data_value sanity: min/max overall and by scale
    out["data_value_overall"] = list(
        con.execute(
            "SELECT MIN(data_value), MAX(data_value), AVG(data_value) FROM ex"
        ).fetchone()
    )
    out["data_value_out_of_range"] = con.execute(
        "SELECT COUNT(*) FROM ex WHERE data_value < 0.0 OR data_value > 100.0"
    ).fetchone()[0]
    out["data_value_per_scale"] = [
        {
            "scale_id": r[0],
            "min": r[1],
            "max": r[2],
            "avg": r[3],
            "stddev": r[4],
        }
        for r in con.execute(
            """
            SELECT scale_id, MIN(data_value), MAX(data_value),
                   AVG(data_value), STDDEV_POP(data_value)
            FROM ex GROUP BY 1 ORDER BY 1
            """
        ).fetchall()
    ]

    # Per (occ, scale) sum of data_value — should be near 100
    sum_stats = con.execute(
        """
        WITH s AS (
            SELECT onet_soc_code, scale_id, SUM(data_value) AS total
            FROM ex GROUP BY 1,2
        )
        SELECT scale_id,
               COUNT(*) AS groups,
               AVG(total) AS mean_sum,
               STDDEV_POP(total) AS std_sum,
               MIN(total) AS min_sum,
               MAX(total) AS max_sum,
               QUANTILE_CONT(total, 0.05) AS p05,
               QUANTILE_CONT(total, 0.5) AS median,
               QUANTILE_CONT(total, 0.95) AS p95
        FROM s GROUP BY 1 ORDER BY 1
        """
    ).fetchall()
    out["sum_per_occ_scale"] = [
        {
            "scale_id": r[0],
            "groups": r[1],
            "mean_sum": r[2],
            "std_sum": r[3],
            "min_sum": r[4],
            "max_sum": r[5],
            "p05": r[6],
            "median": r[7],
            "p95": r[8],
        }
        for r in sum_stats
    ]

    # Outlier groups where sum deviates from 100 by >1
    sum_outliers = con.execute(
        """
        WITH s AS (
            SELECT onet_soc_code, scale_id, SUM(data_value) AS total
            FROM ex GROUP BY 1,2
        )
        SELECT scale_id,
               SUM(CASE WHEN ABS(total - 100.0) > 1 THEN 1 ELSE 0 END) AS gt1,
               SUM(CASE WHEN ABS(total - 100.0) > 5 THEN 1 ELSE 0 END) AS gt5,
               SUM(CASE WHEN ABS(total - 100.0) > 10 THEN 1 ELSE 0 END) AS gt10,
               SUM(CASE WHEN total = 0 THEN 1 ELSE 0 END) AS zero_sum
        FROM s GROUP BY 1 ORDER BY 1
        """
    ).fetchall()
    out["sum_outlier_counts"] = [
        {"scale_id": r[0], "off_by_gt_1": r[1], "off_by_gt_5": r[2], "off_by_gt_10": r[3], "zero_sum": r[4]}
        for r in sum_outliers
    ]

    # 5. Suppression rate
    supp_overall = con.execute(
        """
        SELECT COALESCE(recommend_suppress, '(null)') AS val, COUNT(*) AS rows
        FROM ex GROUP BY 1 ORDER BY 2 DESC
        """
    ).fetchall()
    out["recommend_suppress_distribution_overall"] = [
        {"value": r[0], "rows": r[1]} for r in supp_overall
    ]
    supp_per_scale = con.execute(
        """
        SELECT scale_id, COALESCE(recommend_suppress, '(null)') AS val, COUNT(*) AS rows
        FROM ex GROUP BY 1,2 ORDER BY 1, 3 DESC
        """
    ).fetchall()
    out["recommend_suppress_per_scale"] = [
        {"scale_id": r[0], "value": r[1], "rows": r[2]} for r in supp_per_scale
    ]

    # 6. Spot checks (RW)
    def rw_dist(soc: str) -> list[dict]:
        rows = con.execute(
            """
            SELECT category, data_value, recommend_suppress
            FROM ex
            WHERE onet_soc_code = ? AND scale_id = 'RW'
            ORDER BY category
            """,
            [soc],
        ).fetchall()
        return [
            {"category": r[0], "data_value": r[1], "recommend_suppress": r[2]}
            for r in rows
        ]

    out["spot_check_11_1011_00_rw"] = rw_dist("11-1011.00")
    out["spot_check_41_2031_00_rw"] = rw_dist("41-2031.00")
    out["spot_check_15_1252_00_rw"] = rw_dist("15-1252.00")

    # Mode (most common category) per occupation for RW — used in Silver
    spot_mode = con.execute(
        """
        WITH r AS (
            SELECT onet_soc_code, category, data_value,
                   ROW_NUMBER() OVER (PARTITION BY onet_soc_code ORDER BY data_value DESC, category ASC) AS rn
            FROM ex WHERE scale_id = 'RW'
        )
        SELECT onet_soc_code, category, data_value
        FROM r WHERE rn = 1 AND onet_soc_code IN ('11-1011.00','41-2031.00','15-1252.00')
        ORDER BY onet_soc_code
        """
    ).fetchall()
    out["spot_check_mode_categories"] = [
        {"onet_soc_code": r[0], "mode_category": r[1], "mode_data_value": r[2]}
        for r in spot_mode
    ]

    # 7. Multi-detail aggregation preview
    multi = con.execute(
        """
        WITH per_bls AS (
            SELECT SUBSTR(onet_soc_code, 1, 7) AS bls_soc,
                   COUNT(DISTINCT onet_soc_code) AS detail_count
            FROM ex WHERE scale_id = 'RW'
            GROUP BY 1
        )
        SELECT detail_count, COUNT(*) AS bls_socs
        FROM per_bls GROUP BY 1 ORDER BY 1
        """
    ).fetchall()
    out["rw_multi_detail_distribution"] = [
        {"onet_details_averaged": r[0], "bls_socs": r[1]} for r in multi
    ]
    out["rw_distinct_bls_socs"] = con.execute(
        "SELECT COUNT(DISTINCT SUBSTR(onet_soc_code,1,7)) FROM ex WHERE scale_id='RW'"
    ).fetchone()[0]

    # 8. Null analysis per column
    null_rates = {}
    for col in arrow.column_names:
        r = con.execute(
            f"SELECT SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END), COUNT(*) FROM ex"
        ).fetchone()
        null_rates[col] = {"nulls": r[0], "total": r[1], "null_pct": r[0] / r[1] * 100.0}
    out["null_rates"] = null_rates

    # 9. n, SE, CI
    out["n_stats"] = list(
        con.execute(
            """
            SELECT
                COUNT(n), MIN(n), MAX(n), AVG(n),
                QUANTILE_CONT(n, 0.5), QUANTILE_CONT(n, 0.05), QUANTILE_CONT(n, 0.95)
            FROM ex WHERE n IS NOT NULL
            """
        ).fetchone()
    )
    out["standard_error_stats"] = list(
        con.execute(
            """
            SELECT
                COUNT(standard_error), MIN(standard_error), MAX(standard_error),
                AVG(standard_error), QUANTILE_CONT(standard_error, 0.5)
            FROM ex WHERE standard_error IS NOT NULL
            """
        ).fetchone()
    )
    out["lower_upper_ci_null_rates"] = {
        "lower_ci_null": con.execute(
            "SELECT SUM(CASE WHEN lower_ci_bound IS NULL THEN 1 ELSE 0 END) FROM ex"
        ).fetchone()[0],
        "upper_ci_null": con.execute(
            "SELECT SUM(CASE WHEN upper_ci_bound IS NULL THEN 1 ELSE 0 END) FROM ex"
        ).fetchone()[0],
        "both_populated": con.execute(
            "SELECT SUM(CASE WHEN lower_ci_bound IS NOT NULL AND upper_ci_bound IS NOT NULL THEN 1 ELSE 0 END) FROM ex"
        ).fetchone()[0],
    }

    # 10. Weighted-median edge cases in RW scale
    # a) Any occupation where ALL RW rows are suppressed?
    all_supp = con.execute(
        """
        WITH per_occ AS (
            SELECT onet_soc_code,
                   COUNT(*) AS rows,
                   SUM(CASE WHEN recommend_suppress = 'Y' THEN 1 ELSE 0 END) AS y_count
            FROM ex WHERE scale_id = 'RW'
            GROUP BY 1
        )
        SELECT COUNT(*)
        FROM per_occ
        WHERE rows = y_count
        """
    ).fetchone()[0]
    out["rw_all_suppressed_occupations"] = all_supp

    # Sample occupations with all suppressed (up to 10)
    all_supp_sample = con.execute(
        """
        WITH per_occ AS (
            SELECT onet_soc_code,
                   COUNT(*) AS rows,
                   SUM(CASE WHEN recommend_suppress = 'Y' THEN 1 ELSE 0 END) AS y_count
            FROM ex WHERE scale_id = 'RW'
            GROUP BY 1
        )
        SELECT onet_soc_code, rows, y_count
        FROM per_occ WHERE rows = y_count
        LIMIT 10
        """
    ).fetchall()
    out["rw_all_suppressed_sample"] = [
        {"onet_soc_code": r[0], "rows": r[1], "suppressed_rows": r[2]}
        for r in all_supp_sample
    ]

    # b) Occupations with < 11 categories in RW (partial coverage)
    partial = con.execute(
        """
        WITH per_occ AS (
            SELECT onet_soc_code, COUNT(DISTINCT category) AS cat_n
            FROM ex WHERE scale_id = 'RW'
            GROUP BY 1
        )
        SELECT cat_n, COUNT(*) FROM per_occ GROUP BY 1 ORDER BY 1
        """
    ).fetchall()
    out["rw_category_coverage"] = [
        {"category_count": r[0], "occupations": r[1]} for r in partial
    ]

    # c) Occupations where a single category is 100%
    single_cat_100 = con.execute(
        """
        SELECT onet_soc_code, category, data_value
        FROM ex WHERE scale_id = 'RW' AND data_value = 100.0
        ORDER BY onet_soc_code
        LIMIT 20
        """
    ).fetchall()
    out["rw_single_category_100pct_sample"] = [
        {"onet_soc_code": r[0], "category": r[1], "data_value": r[2]} for r in single_cat_100
    ]
    out["rw_single_category_100pct_count"] = con.execute(
        """
        SELECT COUNT(*) FROM ex
        WHERE scale_id = 'RW' AND data_value = 100.0
        """
    ).fetchone()[0]

    # d) Occupations where no category > 50 (no obvious mode - weighted median must walk cumulative)
    no_mode_above_50 = con.execute(
        """
        WITH per_occ AS (
            SELECT onet_soc_code, MAX(data_value) AS max_dv
            FROM ex WHERE scale_id = 'RW'
            GROUP BY 1
        )
        SELECT COUNT(*) FROM per_occ WHERE max_dv < 50.0
        """
    ).fetchone()[0]
    out["rw_no_single_category_above_50pct"] = no_mode_above_50

    # domain_source distribution
    dom_src = con.execute(
        """
        SELECT COALESCE(domain_source, '(null)') AS src, COUNT(*)
        FROM ex GROUP BY 1 ORDER BY 2 DESC
        """
    ).fetchall()
    out["domain_source_distribution"] = [{"source": r[0], "rows": r[1]} for r in dom_src]

    # date distribution
    date_dist = con.execute(
        """
        SELECT COALESCE(date, '(null)') AS d, COUNT(*)
        FROM ex GROUP BY 1 ORDER BY 2 DESC LIMIT 15
        """
    ).fetchall()
    out["date_distribution_top15"] = [{"date": r[0], "rows": r[1]} for r in date_dist]

    # onet_soc_code format validation
    fmt_check = con.execute(
        """
        SELECT COUNT(*) FROM ex
        WHERE NOT REGEXP_MATCHES(onet_soc_code, '^\\d{2}-\\d{4}\\.\\d{2}$')
        """
    ).fetchone()[0]
    out["onet_soc_format_violations"] = fmt_check

    # scale_id values
    out["scale_id_values"] = [
        r[0]
        for r in con.execute(
            "SELECT DISTINCT scale_id FROM ex ORDER BY 1"
        ).fetchall()
    ]

    # RW-specific: rows, occupations
    out["rw_rows"] = con.execute(
        "SELECT COUNT(*) FROM ex WHERE scale_id='RW'"
    ).fetchone()[0]
    out["rw_distinct_occupations"] = con.execute(
        "SELECT COUNT(DISTINCT onet_soc_code) FROM ex WHERE scale_id='RW'"
    ).fetchone()[0]

    # Element_id breakdown (spec says RW must be 3.A.1)
    out["rw_element_ids"] = [
        {"element_id": r[0], "element_name": r[1], "rows": r[2]}
        for r in con.execute(
            """
            SELECT element_id, element_name, COUNT(*)
            FROM ex WHERE scale_id='RW'
            GROUP BY 1,2 ORDER BY 3 DESC
            """
        ).fetchall()
    ]

    # Compute weighted-median for a handful of occupations (sanity check for Silver)
    # Walk cumulative; first category where cumulative >= 50 is the weighted median.
    def weighted_median_rw(soc: str) -> dict:
        rows = con.execute(
            """
            SELECT category, data_value
            FROM ex WHERE onet_soc_code = ? AND scale_id = 'RW'
            ORDER BY category
            """,
            [soc],
        ).fetchall()
        cum = 0.0
        median_cat = None
        for c, v in rows:
            cum += v or 0.0
            if median_cat is None and cum >= 50.0:
                median_cat = c
        return {
            "onet_soc_code": soc,
            "rows": len(rows),
            "sum": round(cum, 2),
            "weighted_median_category": median_cat,
            "distribution": [{"category": c, "data_value": v} for c, v in rows],
        }

    out["spot_check_weighted_medians"] = [
        weighted_median_rw("11-1011.00"),
        weighted_median_rw("41-2031.00"),
        weighted_median_rw("15-1252.00"),
    ]

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nWrote: {OUT_JSON}")
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
