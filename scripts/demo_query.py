"""Query gold zone parquet data for demo scenario school matches."""
import duckdb
import textwrap

con = duckdb.connect()
PCP = "data/gold/iceberg_warehouse/consumable/program_career_paths/data/*.parquet"

def find_schools(label, cip_pattern, target_occupation_keyword, order_by="debt DESC", limit=8):
    """Find schools matching a cip + target occupation, deduplicated by school+program."""
    print(f"\n{'='*70}")
    print(f"{label}")
    print(f"{'='*70}")
    sql = f"""
    WITH ranked AS (
        SELECT *,
               ROW_NUMBER() OVER (
                   PARTITION BY unitid, cipcode
                   ORDER BY CASE WHEN LOWER(occupation_title) LIKE '%{target_occupation_keyword.lower()}%' THEN 0 ELSE 1 END,
                            earnings_1yr_median DESC NULLS LAST
               ) as rn
        FROM read_parquet('{PCP}')
        WHERE cipcode LIKE '{cip_pattern}'
          AND earnings_1yr_median IS NOT NULL
          AND debt_median IS NOT NULL
          AND confidence_tier_program IN ('high', 'medium', 'low')
    )
    SELECT
        institution_name,
        program_name,
        occupation_title,
        ROUND(earnings_1yr_median) AS earnings_1yr,
        ROUND(debt_median) AS debt,
        ROUND(debt_to_earnings_annual, 2) AS dte,
        stat_ern, stat_roi, stat_res, stat_grw, stat_hmn,
        boss_ai_score, boss_loans_score, boss_market_score, boss_burnout_score, boss_ceiling_score,
        confidence_tier_program AS confidence,
        employment_current
    FROM ranked
    WHERE rn = 1
    ORDER BY {order_by}
    LIMIT {limit}
    """
    df = con.execute(sql).fetchdf()
    for _, row in df.iterrows():
        print(f"\n  SCHOOL:      {row['institution_name']}")
        print(f"  PROGRAM:     {row['program_name']}")
        print(f"  CAREER:      {row['occupation_title']}")
        print(f"  EARNINGS 1yr: ${row['earnings_1yr']:,.0f}   DEBT: ${row['debt']:,.0f}   DTE: {row['dte']}")
        print(f"  STATS:       ERN={row['stat_ern']} ROI={row['stat_roi']} RES={row['stat_res']} GRW={row['stat_grw']} HMN={row['stat_hmn']}")
        print(f"  BOSSES:      AI={row['boss_ai_score']} Loans={row['boss_loans_score']} Market={row['boss_market_score']} Burnout={row['boss_burnout_score']} Ceiling={row['boss_ceiling_score']}")
        import pandas as pd
        emp = row['employment_current']
        emp_str = f"{emp:,.0f}" if pd.notna(emp) else "N/A"
        print(f"  Confidence: {row['confidence']}  |  Employment: {emp_str}")


# ── 1. DEAF EDUCATION ──────────────────────────────────────────────────────────
find_schools(
    "DEAF ED — EXPENSIVE (bad path)",
    cip_pattern="13.10%",
    target_occupation_keyword="special education",
    order_by="debt DESC",
    limit=8
)
find_schools(
    "DEAF ED — AFFORDABLE (good path)",
    cip_pattern="13.10%",
    target_occupation_keyword="special education",
    order_by="debt ASC",
    limit=8
)

# ── 2. NURSING ─────────────────────────────────────────────────────────────────
find_schools(
    "NURSING — EXPENSIVE PRIVATE (bad path)",
    cip_pattern="51.38%",
    target_occupation_keyword="registered nurse",
    order_by="debt DESC",
    limit=8
)
find_schools(
    "NURSING — AFFORDABLE (good path)",
    cip_pattern="51.38%",
    target_occupation_keyword="registered nurse",
    order_by="debt ASC",
    limit=8
)

# ── 3. PSYCHOLOGY ──────────────────────────────────────────────────────────────
find_schools(
    "PSYCHOLOGY — EXPENSIVE PRIVATE (bad path)",
    cip_pattern="42.01%",
    target_occupation_keyword="psychologist",
    order_by="debt DESC",
    limit=8
)
find_schools(
    "PSYCHOLOGY — AFFORDABLE (good path)",
    cip_pattern="42.01%",
    target_occupation_keyword="psychologist",
    order_by="debt ASC",
    limit=8
)

# ── 4. FILM / MEDIA ────────────────────────────────────────────────────────────
find_schools(
    "FILM/MEDIA — EXPENSIVE PRIVATE (bad path)",
    cip_pattern="50.06%",
    target_occupation_keyword="film",
    order_by="debt DESC",
    limit=8
)
find_schools(
    "FILM/MEDIA — AFFORDABLE (good path)",
    cip_pattern="50.06%",
    target_occupation_keyword="film",
    order_by="debt ASC",
    limit=8
)

# ── 5. COMPUTER SCIENCE ────────────────────────────────────────────────────────
find_schools(
    "CS — EXPENSIVE PRIVATE, GENERIC (bad path)",
    cip_pattern="11.01%",
    target_occupation_keyword="software",
    order_by="debt DESC",
    limit=8
)
find_schools(
    "CS — AFFORDABLE STATE, GOOD EARNINGS (good path)",
    cip_pattern="11.01%",
    target_occupation_keyword="software",
    order_by="earnings_1yr DESC",
    limit=8
)
