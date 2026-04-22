"""Additional queries for data review."""
import sys
sys.path.insert(0, "src")
from pyiceberg.catalog.sql import SqlCatalog
from mcp_server._query_engine import QueryEngine

catalog = SqlCatalog(
    "brightsmith",
    uri="sqlite:///data/catalog/catalog.db",
    warehouse="data/gold/iceberg_warehouse",
)
qe = QueryEngine(catalog)

# 1. Find SOC 29-1228 specifically
r = qe.query_sql(
    "SELECT soc_code, occupation_title FROM consumable_occupation_profiles "
    "WHERE soc_code = '29-1228'"
)
print("SOC_29_1228:", r)

# 2. All 29-12XX SOCs
r = qe.query_sql(
    "SELECT soc_code, occupation_title FROM consumable_occupation_profiles "
    "WHERE soc_code LIKE '29-12%' ORDER BY soc_code"
)
print("ALL_29_12XX:")
for row in r:
    print(f"  {row['soc_code']} | {row['occupation_title']}")

# 3. Check if 25-2053 and 25-2054 exist (spec mentions these)
r = qe.query_sql(
    "SELECT soc_code, occupation_title FROM consumable_occupation_profiles "
    "WHERE soc_code IN ('25-2053', '25-2054')"
)
print("SOC_25_2053_25_2054:", r)

# 4. What does the crosswalk table look like?
try:
    r = qe.query_sql(
        "SELECT * FROM base_cip_soc_crosswalk LIMIT 3"
    )
    print("CROSSWALK_SAMPLE:")
    if r:
        print("  COLS:", list(r[0]))
        for row in r:
            print(f"  {row}")
except Exception as e:
    print("CROSSWALK_ERROR:", e)

# 5. Confidence tier distribution
r = qe.query_sql(
    "SELECT confidence_tier, COUNT(*) as cnt FROM consumable_occupation_profiles "
    "GROUP BY confidence_tier ORDER BY confidence_tier"
)
print("CONFIDENCE_TIER_DISTRIBUTION:")
for row in r:
    print(f"  {row['confidence_tier']}: {row['cnt']}")

# 6. backs_stats distribution
r = qe.query_sql(
    "SELECT backs_stats, COUNT(*) as cnt FROM consumable_occupation_profiles "
    "GROUP BY backs_stats ORDER BY cnt DESC LIMIT 10"
)
print("BACKS_STATS_DISTRIBUTION:")
for row in r:
    print(f"  {row['backs_stats']}: {row['cnt']}")

# 7. data_completeness distribution
r = qe.query_sql(
    "SELECT data_completeness, COUNT(*) as cnt FROM consumable_occupation_profiles "
    "GROUP BY data_completeness ORDER BY data_completeness"
)
print("DATA_COMPLETENESS_DIST:")
for row in r:
    print(f"  {row['data_completeness']}: {row['cnt']}")

# 8. broad_occupation_flag and catchall_flag counts
r = qe.query_sql(
    "SELECT broad_occupation_flag, catchall_flag, COUNT(*) as cnt "
    "FROM consumable_occupation_profiles "
    "GROUP BY broad_occupation_flag, catchall_flag "
    "ORDER BY broad_occupation_flag, catchall_flag"
)
print("FLAG_DISTRIBUTION:")
for row in r:
    print(f"  broad={row['broad_occupation_flag']}, catchall={row['catchall_flag']}: {row['cnt']}")

# 9. Education column name
r = qe.query_sql(
    "SELECT soc_code, education_code, education_level_name FROM consumable_occupation_profiles "
    "LIMIT 5"
)
print("EDUCATION_SAMPLE:")
for row in r:
    print(f"  {row['soc_code']} | ed_code={row['education_code']} | {row['education_level_name']}")
