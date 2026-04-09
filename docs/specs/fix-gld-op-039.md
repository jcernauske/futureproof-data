# Fix: GLD-OP-039 Market Score DQ Rule SQL

## Problem

DQ rule GLD-OP-039 fails with 828 violations. The data is correct — the SQL is structurally broken. It tries to use `PERCENT_RANK()` inside a correlated scalar subquery, which doesn't work in DuckDB (or most SQL engines).

The broken SQL:
```sql
SELECT COUNT(*) AS violations FROM consumable.occupation_profiles AS op 
WHERE market_score IS NOT NULL 
AND ABS(market_score - (0.6 * grw_score + 0.4 * (1.0 + 9.0 * (
  SELECT PERCENT_RANK() OVER (ORDER BY o2.openings_annual_avg) 
  FROM consumable.occupation_profiles o2 
  WHERE o2.soc_code = op.soc_code
)))) > 0.01
```

## How Market Score Is Actually Computed

From `src/gold/bls_ooh_occupation_profiles.py`:

1. SQL CTE `openings_ranked` computes: `1.0 + 9.0 * PERCENT_RANK() OVER (ORDER BY openings_annual_avg)` — excluding null openings
2. Python then computes: `market_score = 0.6 * grw_score + 0.4 * openings_score`

## Fix

Replace the SQL in GLD-OP-039 in `governance/dq-rules/gold-occupation-profiles-bls-ooh.json` with:

```sql
WITH openings_ranked AS (
    SELECT
        soc_code,
        1.0 + 9.0 * PERCENT_RANK() OVER (ORDER BY openings_annual_avg) AS openings_score
    FROM consumable.occupation_profiles
    WHERE openings_annual_avg IS NOT NULL
)
SELECT COUNT(*) AS violations
FROM consumable.occupation_profiles op
LEFT JOIN openings_ranked o ON op.soc_code = o.soc_code
WHERE op.market_score IS NOT NULL
  AND o.openings_score IS NOT NULL
  AND op.grw_score IS NOT NULL
  AND ABS(op.market_score - (0.6 * op.grw_score + 0.4 * o.openings_score)) > 0.01
```

This mirrors the actual implementation: compute `openings_score` via a CTE with `PERCENT_RANK()` over the full table, then join back and validate the formula.

## After Fixing

1. Update the `sql` field for rule `GLD-OP-039` in `governance/dq-rules/gold-occupation-profiles-bls-ooh.json`
2. Re-run the DQ rule against `consumable.occupation_profiles`
3. Confirm violations = 0
4. Update `governance/dq-scorecards/gold-occupation-profiles-bls-ooh-scorecard.md` — GLD-OP-039 should flip from FAIL to PASS
5. Run full test suite to confirm nothing else broke
