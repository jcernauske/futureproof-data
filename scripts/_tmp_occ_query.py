"""Temporary query script for data review."""
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

# 1. Row count
rows = qe.query_sql("SELECT COUNT(*) as cnt FROM consumable_occupation_profiles")
print("ROW_COUNT:", rows[0]["cnt"])

# 2. Column names
sample = qe.query_sql("SELECT * FROM consumable_occupation_profiles LIMIT 1")
if sample:
    cols = list(sample[0])
    print("COLUMNS:", cols)
    for k in cols:
        print(f"  {k} = {sample[0][k]}")

# 3. SOC format check - any that don't match XX-XXXX
bad_format = qe.query_sql(
    "SELECT soc_code FROM consumable_occupation_profiles "
    "WHERE NOT regexp_matches(soc_code, '^[0-9][0-9]-[0-9][0-9][0-9][0-9]$')"
)
print("BAD_FORMAT_SOCS:", len(bad_format), bad_format[:5] if bad_format else [])

# 4. Check for 99-9999
residual = qe.query_sql(
    "SELECT soc_code, occupation_title FROM consumable_occupation_profiles "
    "WHERE soc_code = '99-9999'"
)
print("RESIDUAL_99_9999:", residual)

# 5. Null checks
nulls = qe.query_sql(
    "SELECT COUNT(*) as cnt FROM consumable_occupation_profiles "
    "WHERE soc_code IS NULL OR occupation_title IS NULL"
)
print("NULL_SOC_OR_TITLE:", nulls[0]["cnt"])

# 6. Pre-med test: physician/surgeon/doctor
premed = qe.query_sql(
    "SELECT soc_code, occupation_title, soc_major_group_name "
    "FROM consumable_occupation_profiles "
    "WHERE LOWER(occupation_title) LIKE '%physician%' "
    "   OR LOWER(occupation_title) LIKE '%surgeon%' "
    "   OR LOWER(occupation_title) LIKE '%doctor%' "
    "ORDER BY soc_code"
)
print("PREMED_MATCHES:")
for r in premed:
    print(f"  {r['soc_code']} | {r['occupation_title']} | {r.get('soc_major_group_name', 'N/A')}")

# 7. Specific physician SOCs
specific = qe.query_sql(
    "SELECT soc_code, occupation_title FROM consumable_occupation_profiles "
    "WHERE soc_code IN ('29-1228', '29-1241')"
)
print("SPECIFIC_PHYSICIAN_SOCS:", specific)

# 8. Deaf ed / special ed test
deafed = qe.query_sql(
    "SELECT soc_code, occupation_title, soc_major_group_name "
    "FROM consumable_occupation_profiles "
    "WHERE LOWER(occupation_title) LIKE '%special education%' "
    "   OR LOWER(occupation_title) LIKE '%deaf%' "
    "ORDER BY soc_code"
)
print("DEAF_ED_MATCHES:")
for r in deafed:
    print(f"  {r['soc_code']} | {r['occupation_title']} | {r.get('soc_major_group_name', 'N/A')}")

# 9. Specific special ed SOCs
sped = qe.query_sql(
    "SELECT soc_code, occupation_title FROM consumable_occupation_profiles "
    "WHERE soc_code IN ('25-2052', '25-2053', '25-2054', '25-2058')"
)
print("SPECIFIC_SPED_SOCS:", sped)

# 10. Check for 'All Other' residual SOCs
all_other = qe.query_sql(
    "SELECT COUNT(*) as cnt FROM consumable_occupation_profiles "
    "WHERE occupation_title LIKE '%All Other%'"
)
print("ALL_OTHER_COUNT:", all_other[0]["cnt"])

# 11. Major group name coverage
mg = qe.query_sql(
    "SELECT COUNT(*) as cnt FROM consumable_occupation_profiles "
    "WHERE soc_major_group_name IS NULL OR soc_major_group_name = ''"
)
print("MISSING_MAJOR_GROUP:", mg[0]["cnt"])

# 12. Pre-med keyword: what matches 'med' in title or major group?
premed_kw = qe.query_sql(
    "SELECT soc_code, occupation_title, soc_major_group_name FROM consumable_occupation_profiles "
    "WHERE LOWER(occupation_title) LIKE '%med%' "
    "   OR LOWER(soc_major_group_name) LIKE '%med%' "
    "ORDER BY soc_code LIMIT 35"
)
print("MED_KEYWORD_MATCHES:", len(premed_kw))
for r in premed_kw:
    print(f"  {r['soc_code']} | {r['occupation_title']} | {r.get('soc_major_group_name', 'N/A')}")

# 13. Teacher/education keyword matches
teacher_kw = qe.query_sql(
    "SELECT soc_code, occupation_title, soc_major_group_name FROM consumable_occupation_profiles "
    "WHERE LOWER(occupation_title) LIKE '%teacher%' "
    "   OR LOWER(soc_major_group_name) LIKE '%education%' "
    "ORDER BY soc_code LIMIT 50"
)
print("TEACHER_EDUCATION_MATCHES:", len(teacher_kw))
for r in teacher_kw:
    print(f"  {r['soc_code']} | {r['occupation_title']} | {r.get('soc_major_group_name', 'N/A')}")

# 14. 'doctor' keyword specifically
doctor_kw = qe.query_sql(
    "SELECT soc_code, occupation_title FROM consumable_occupation_profiles "
    "WHERE LOWER(occupation_title) LIKE '%doctor%' "
    "ORDER BY soc_code"
)
print("DOCTOR_KEYWORD_MATCHES:", doctor_kw)

# 15. Check for duplicate SOC codes
dupes = qe.query_sql(
    "SELECT soc_code, COUNT(*) as cnt FROM consumable_occupation_profiles "
    "GROUP BY soc_code HAVING COUNT(*) > 1"
)
print("DUPLICATE_SOCS:", dupes)

# 16. What does 'pre-med' match?
premed_exact = qe.query_sql(
    "SELECT soc_code, occupation_title FROM consumable_occupation_profiles "
    "WHERE LOWER(occupation_title) LIKE '%pre-med%' OR LOWER(occupation_title) LIKE '%premed%' "
    "ORDER BY soc_code"
)
print("PREMED_EXACT_MATCHES:", premed_exact)

# 17. 'deaf' keyword
deaf_kw = qe.query_sql(
    "SELECT soc_code, occupation_title FROM consumable_occupation_profiles "
    "WHERE LOWER(occupation_title) LIKE '%deaf%' "
    "ORDER BY soc_code"
)
print("DEAF_KEYWORD_MATCHES:", deaf_kw)

# 18. Education level column check
try:
    edu = qe.query_sql(
        "SELECT soc_code, entry_level_education FROM consumable_occupation_profiles "
        "WHERE entry_level_education IS NOT NULL LIMIT 5"
    )
    print("EDUCATION_LEVEL_SAMPLE:", edu)
except Exception as e:
    print("EDUCATION_LEVEL_ERROR:", e)
