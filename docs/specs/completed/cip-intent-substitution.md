# Spec: cip-intent-substitution

**Status:** COMPLETE
**Layer:** MCP / Product Logic
**Primary Agent:** @primary-agent
**Created:** 2026-04-11
**Priority:** P0 — Hackathon Critical

---

## Problem Statement

When a student selects a school that reports under a broad CIP code (e.g., IU-Bloomington reports all Kelley business graduates under CIP 52.01 "Business/Commerce, General"), the career paths returned are generic management roles — Construction Managers, Industrial Production Managers, Facilities Managers — that don't match the student's actual major. An IU Marketing student should see Marketing Managers, Market Research Analysts, and Advertising Managers, not Construction Managers.

Four spikes validated the solution: **student-intent CIP substitution.** A lookup table maps the student's stated major to a specific CIP code. When the school reports only a broad CIP, the system substitutes the specific CIP's crosswalk SOC mappings while keeping the school's broad-CIP earnings data for ERN and ROI.

### Spike Evidence

| Spike | Finding | File |
|---|---|---|
| Broad CIP Prevalence | 23.5% of all rows are broad XX.01 CIPs. Systemic. | `spike-broad-cip-prevalence.md` |
| Override Table (A) | Only 26 Business schools are broad-only. IU isn't one — it reports both. Too narrow. | `spike-cip-override-table.md` |
| Gemma Filtering (B) | Marketing SOCs don't exist in 52.01's candidate set. Can't filter for what's not there. | `spike-gemma-query-filter.md` |
| Hierarchy Fallback (C) | 22% SOC overlap between 52.01 and 52.14. SOC sets are complementary, not nested. Unsafe. | `spike-cip-hierarchy-fallback.md` |
| Intent Substitution (D) | Substituting 52.14 SOCs + IU 52.01 earnings produces correct Marketing career paths with 5-stat pentagons. Validated. | `spike-intent-substitution.md` |

---

## What Ships

### 1. Major-to-CIP Intent Lookup Table

A YAML reference file mapping common major names to specific 4-digit CIP codes.

**Location:** `data/reference/major_to_cip.yaml`

**Format:**
```yaml
# Major-to-CIP Intent Lookup
# Used when a school reports only a broad XX.01 CIP and the student
# specifies a more specific major. Maps the student's stated intent
# to the specific CIP whose crosswalk SOC mappings best represent
# that major's career paths.
#
# Structure: list of entries, each with:
#   - major: common name(s) students would type
#   - cip4: the 4-digit CIP prefix to substitute
#   - cip_family: the 2-digit family this belongs to
#   - aliases: alternate names, abbreviations, misspellings

- major: "Marketing"
  cip4: "52.14"
  cip_family: "52"
  aliases: ["marketing management", "mktg", "digital marketing"]

- major: "Accounting"
  cip4: "52.03"
  cip_family: "52"
  aliases: ["accountancy", "acct"]

- major: "Finance"
  cip4: "52.08"
  cip_family: "52"
  aliases: ["financial management", "corporate finance"]

- major: "Human Resources"
  cip4: "52.10"
  cip_family: "52"
  aliases: ["HR", "human resource management", "personnel management"]

- major: "Management Information Systems"
  cip4: "52.12"
  cip_family: "52"
  aliases: ["MIS", "business information systems", "IT management"]

- major: "Hospitality Management"
  cip4: "52.09"
  cip_family: "52"
  aliases: ["hotel management", "hospitality", "tourism management"]

- major: "Entrepreneurship"
  cip4: "52.07"
  cip_family: "52"
  aliases: ["small business", "startup"]

- major: "International Business"
  cip4: "52.11"
  cip_family: "52"
  aliases: ["global business", "intl business"]

- major: "Business Administration"
  cip4: "52.02"
  cip_family: "52"
  aliases: ["business admin", "BBA", "business management", "general management"]

# ... extend to cover all CIP families
```

**Scope for hackathon:** CIP family 52 (Business) is the highest priority — 18 entries covering the majors students actually type. Extend to families 13 (Education), 26 (Biology), 42 (Psychology), 23 (English), 09 (Communications), 11 (Computer Science), 14 (Engineering) as time allows. Target ~150-250 entries total.

**Curation approach:** Seed from the crosswalk's 4-digit CIP descriptions (Spike C produced the full list for family 52). Add aliases from common student language. Gemma can draft the initial table; human reviews and corrects.

### 2. Substitution Logic in `get_career_paths`

Update the `_handle_get_career_paths` handler in `src/mcp_server/futureproof_server.py` to implement the substitution flow.

**New parameter:**
```json
{
  "student_major": {
    "type": "string",
    "description": "The student's stated major (e.g., 'Marketing'). Optional. When provided and the school's reported CIP is a broad XX.01 code, the system substitutes the specific CIP's crosswalk SOC mappings. When omitted, returns the school's reported CIP career paths as-is."
  }
}
```

**Flow:**

```
1. Receive (unitid, cipcode, student_major)

2. If student_major is null or empty:
   → Standard path. Query program_career_paths as today. Return results.

3. If student_major is provided:
   a. Check if cipcode is a broad code (ends in ".01" pattern)
      - If NOT broad → standard path, ignore student_major
        (school already reports the specific CIP)
   
   b. Look up student_major in major_to_cip.yaml
      - Match against major name and aliases (case-insensitive)
      - If no match found → standard path + message:
        "Could not map '{student_major}' to a specific program.
         Showing results for the school's reported program."
   
   c. Verify the matched cip4 is in the same family as the reported cipcode
      - "Marketing" → 52.14, school reports 52.01 → same family (52) ✓
      - If different family → standard path + warning
        (student's major doesn't match the school's program family)
   
   d. SUBSTITUTION:
      - Get school's program-level data from career_outcomes using
        the ORIGINAL cipcode (52.01) → earnings, debt, ROI, p25/p75
      - Get career paths (SOC codes) from the crosswalk using the
        SUBSTITUTED cip4 (52.14) → marketing-specific SOCs
      - For each SOC: pull occupation_profiles, onet_work_profiles,
        ai_exposure → GRW, HMN, RES, boss scores
      - Compute ERN and ROI using school's program-level earnings
        + occupation-level wage percentile (same formula as Gold engine)
      - Assemble blended result rows
   
   e. Flag every result row:
      - substitution_applied: true
      - reported_cipcode: "52.01"
      - substituted_cipcode: "52.14"
      - earnings_source: "school_broad_program"
      - career_paths_source: "substituted_specific_cip"
```

### 3. Substitution Bypass Logic

The substitution ONLY fires when ALL of these are true:
- `student_major` is provided
- The school's `cipcode` is a broad code (XX.01)
- `student_major` matches an entry in `major_to_cip.yaml`
- The matched CIP is in the same family as the reported CIP

If the school already reports the specific CIP (e.g., ISU reports 52.14 directly), the standard path runs and no substitution is needed. This handles the 604 schools that report 52.14 directly vs. the 217 that report only 52.01.

### 4. Product Caveat in Response

Every substituted result includes metadata the frontend uses to show an honest caveat:

```json
{
  "data_caveat": {
    "type": "blended_substitution",
    "message": "Earnings and debt reflect all business graduates at this school. Career paths reflect typical Marketing outcomes nationally. This school does not report Marketing-specific outcome data.",
    "reported_program": "Business/Commerce, General.",
    "substituted_program": "Marketing/Marketing Management, General.",
    "earnings_specificity": "school_broad",
    "career_path_specificity": "national_major_specific"
  }
}
```

### 5. Gemma Prompt Update

When Gemma receives substituted results, its guidance generation prompt should incorporate the caveat naturally:

"IU-Bloomington doesn't break out Marketing-specific earnings — their data covers all Kelley business graduates together. So the salary and debt numbers here are for the broader business program. But the career paths, AI exposure, and skill requirements are specifically for Marketing majors based on national data."

This is prompt engineering in the Gemma agent layer, not MCP code. Include a sample prompt fragment in this spec for the agent integration spec to reference.

---

## What Does NOT Ship

- No new Brightsmith pipeline zones (Bronze/Silver/Gold)
- No new Iceberg tables
- No changes to existing Gold tables
- No changes to the crosswalk
- The lookup table is a static YAML file, not a governed data product
- Gemma is NOT involved in the substitution decision — it's deterministic logic based on the lookup table

---

## Testing

### Unit Tests

- `tests/mcp/test_cip_substitution.py`
  - Substitution fires for IU-B (unitid=151351) + cipcode=52.01 + student_major="Marketing" → returns 52.14 SOCs
  - Substitution does NOT fire for ISU (unitid=145813) + cipcode=52.14 + student_major="Marketing" → returns 52.14 SOCs via standard path
  - Substitution does NOT fire when student_major is omitted → returns 52.01 SOCs as today
  - Alias matching: "mktg", "MARKETING", "marketing management" all resolve to 52.14
  - Family mismatch rejection: student says "Nursing" (CIP 51.xx) at a school with cipcode=52.01 → standard path + warning
  - Unrecognized major: student says "Underwater Basket Weaving" → standard path + message
  - Blended ERN/ROI computation matches Gold engine formula
  - Caveat metadata present on every substituted row
  - Caveat metadata absent on non-substituted rows

### Integration Tests

- `tests/mcp/test_cip_substitution_integration.py`
  - End-to-end: IU-B Marketing → 9 career paths including Marketing Managers (11-2021), Market Research Analysts (13-1161)
  - End-to-end: IU-B Accounting → 15 career paths including Accountants and Auditors (13-2011)
  - End-to-end: IU-B Finance → 21 career paths including Financial Managers (11-3031)
  - Verify 5-stat pentagon completeness on substituted results (expect ~67% full pentagon based on spike)
  - Verify boss scores populated on substituted results
  - Compare substituted IU-B Marketing results to ISU Marketing (52.14 direct) — SOC lists should match, ERN/ROI should differ (different school earnings)

### Eval Cases

- `data/ai_ready/eval/mcp-cip-substitution-eval.jsonl`
  - Mechanically verifiable: known inputs → known SOC lists, known stat values

---

## Lookup Table Curation Plan

### Phase 1 (Hackathon — ships): CIP Family 52 (Business)

18 entries covering the majors Kelley/Wharton/Ross students actually study. Manually curated from Spike C crosswalk data + school bulletin verification.

### Phase 2 (Hackathon — stretch): Top 8 CIP Families

Extend to families 13, 26, 42, 23, 09, 11, 14, 51 (Education, Biology, Psychology, English, Communications, CS, Engineering, Health). Gemma drafts initial entries from crosswalk descriptions; human reviews. ~100-150 additional entries.

### Phase 3 (Post-hackathon): Full Coverage

All CIP families with broad-reporting schools. ~150-250 total entries. Community contributions welcome.

---

## Agent Workflow

1. @primary-agent — Create `data/reference/major_to_cip.yaml` (Phase 1: family 52)
2. @primary-agent — Implement substitution logic in `_handle_get_career_paths`
3. @primary-agent — Write unit + integration tests
4. @primary-agent — Write eval cases
5. @primary-agent — Verify IU-B Marketing / Accounting / Finance produce correct results
6. @staff-engineer — Review

---

## Estimated Effort

| Step | Estimate |
|------|----------|
| YAML lookup table (family 52) | 1 hour |
| Substitution logic in MCP handler | 2-3 hours |
| Tests + eval cases | 2-3 hours |
| Phase 2 lookup expansion (stretch) | 2-3 hours |
| **Total** | **~5-9 hours** |

---

## After This Spec

With CIP substitution live, the core product loop handles the broad-CIP problem for the majority of cases. The Student Career Path Override spec (P0 #2) handles the remaining edge cases where the lookup table doesn't have the student's major or where the student wants a career path not in the substituted set.

---

*— End of Spec —*
