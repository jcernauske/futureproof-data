# Entity Resolution Assessment: raw-ingest-college-scorecard
**Date:** 2026-04-05
**Agent:** @entity-resolver
**Entity Type:** Postsecondary Institution (UNITID)
**Resolution Strategy:** Not required — authoritative federal identifier present

---

## Finding: No Entity Resolution Needed

UNITID is an authoritative identifier assigned by the Integrated Postsecondary Education Data System (IPEDS) and managed by the National Center for Education Statistics (NCES). It is the standard federal identifier for U.S. postsecondary institutions and is stable across years.

**No entity resolution, fuzzy matching, or deduplication is required for this dataset.**

---

## Verification Results

### Identifier Statistics
| Metric | Value |
|--------|-------|
| Total rows | 69,947 |
| Distinct UNITIDs | 2,559 |
| Distinct institution names (INSTNM) | 2,534 |

### UNITID-to-Name Mapping: Clean
- **Same UNITID with different names:** 0 cases
- Every UNITID maps to exactly one INSTNM in this snapshot. No data quality issues.

### Name-to-UNITID Mapping: Expected Multi-Campus Cases
- **Same name with different UNITIDs:** 15 cases (25 extra UNITIDs, explaining the 2,559 vs 2,534 gap)
- These are distinct institutions that share a name, not duplicates. Examples:

| Institution Name | UNITID Count | Explanation |
|-----------------|-------------|-------------|
| Stevens-Henager College | 6 | Multi-campus for-profit system, each campus has its own UNITID |
| Bethel University | 3 | Unrelated institutions in different states (IN, MN, TN) |
| Lincoln University | 3 | Unrelated institutions in different states (PA, MO, CA) |
| Anderson University | 2 | Unrelated institutions (SC, IN) |
| St. John's College | 2 | Separate campuses (MD, NM) |

These are **not** entity resolution issues. UNITID correctly distinguishes separate campuses and unrelated institutions that happen to share names.

---

## Recommendations for Silver Zone

1. **Use UNITID as the primary foreign key** for all institution-level joins and lookups. It is stable, unique, and authoritative.
2. **Do not attempt name-based matching** for institution identity. INSTNM is a display label, not an identifier.
3. **Track UNITID-to-INSTNM mapping across data refreshes** to detect institution name changes over time (none observed in this single snapshot).
4. **CIP codes (CIPCODE)** are also standardized federal codes and need no resolution, though the Silver zone should normalize the format by inserting the dot separator (e.g., "5202" to "52.02") for crosswalk compatibility.

---

## Resolution Status: PASS — No Action Required
