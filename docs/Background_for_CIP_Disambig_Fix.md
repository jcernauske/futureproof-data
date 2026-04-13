# Background: CIP Disaggregation Coverage Gap Analysis

**Date:** 2026-04-12
**Context:** Spike analysis to scope the CIP Disaggregation Fix spec
**Trigger:** Deaf Education substitution (13.1003) resolves correctly but fails downstream lookup — no row for specific CIP in career_outcomes

---

## The Core Problem

Career_outcomes and the CIP-SOC crosswalk operate at fundamentally different CIP granularities:

| Data Source | CIP Format | Example | Distinct CIPs |
|-------------|-----------|---------|---------------|
| `consumable.career_outcomes` (Gold) | 4-digit (XX.YY) | `13.10` | 390 |
| `base.cip_soc_crosswalk` (Silver) | 6-digit (XX.YYYY) | `13.1003` | 1,949 |

**Overlap between the two: 0.** They share zero CIP codes because they use different granularity levels. This is not a data quality issue — it's a structural mismatch between College Scorecard (which reports at 4-digit) and the BLS/NCES crosswalk (which maps at 6-digit).

The substitution feature in `major_to_cip.yaml` can point to either granularity. Entries targeting 4-digit CIPs work. Entries targeting 6-digit CIPs break silently — the crosswalk resolves SOCs correctly, but the earnings/debt lookup in career_outcomes finds no rows.

---

## Impact on Current YAML Entries

Of 56 entries in `data/reference/major_to_cip.yaml`:

| Status | Count | Description |
|--------|-------|-------------|
| OK | 23 | 4-digit CIP, direct match in career_outcomes |
| BROKEN | 33 | 6-digit CIP, no match in career_outcomes |

### Working Entries (23)

All Business family entries and 5 broad Education entries that use 4-digit CIPs:

| Major | CIP | Family |
|-------|-----|--------|
| Business Administration | 52.02 | 52 |
| Accounting | 52.03 | 52 |
| Entrepreneurship | 52.07 | 52 |
| Finance | 52.08 | 52 |
| Hospitality Management | 52.09 | 52 |
| Human Resources | 52.10 | 52 |
| International Business | 52.11 | 52 |
| Management Information Systems | 52.12 | 52 |
| Business Analytics | 52.13 | 52 |
| Marketing | 52.14 | 52 |
| Real Estate | 52.15 | 52 |
| Taxation | 52.16 | 52 |
| Insurance | 52.17 | 52 |
| General Sales | 52.18 | 52 |
| Specialized Sales | 52.19 | 52 |
| Construction Management | 52.20 | 52 |
| Telecommunications Management | 52.21 | 52 |
| Supply Chain Management | 52.02 | 52 |
| Special Education | 13.10 | 13 |
| Bilingual Education | 13.02 | 13 |
| Curriculum and Instruction | 13.03 | 13 |
| Educational Leadership | 13.04 | 13 |
| Instructional Technology | 13.05 | 13 |

### Broken Entries (33)

All 33 are Education family (13) entries using 6-digit CIPs. Every one exists in the crosswalk (so SOC resolution works) but not in career_outcomes (so earnings lookup fails). **Every broken entry's parent 4-digit CIP exists in career_outcomes.**

| Major | CIP (6-digit) | Parent (4-digit) | Parent in CO? |
|-------|--------------|-----------------|---------------|
| Deaf Education | 13.1003 | 13.10 | YES |
| Education of the Emotionally Disturbed | 13.1005 | 13.10 | YES |
| Intellectual Disabilities Education | 13.1006 | 13.10 | YES |
| Education of the Visually Impaired | 13.1009 | 13.10 | YES |
| Learning Disabilities Education | 13.1011 | 13.10 | YES |
| Speech-Language Impairments Education | 13.1012 | 13.10 | YES |
| Autism Education | 13.1013 | 13.10 | YES |
| Early Childhood Special Education | 13.1015 | 13.10 | YES |
| Elementary Education | 13.1202 | 13.12 | YES |
| Middle School Education | 13.1203 | 13.12 | YES |
| Secondary Education | 13.1205 | 13.12 | YES |
| Early Childhood Education | 13.1210 | 13.12 | YES |
| Kindergarten Education | 13.1209 | 13.12 | YES |
| Adult Education | 13.1201 | 13.12 | YES |
| Math Education | 13.1311 | 13.13 | YES |
| English Education | 13.1305 | 13.13 | YES |
| Science Education | 13.1316 | 13.13 | YES |
| Social Studies Education | 13.1318 | 13.13 | YES |
| History Education | 13.1328 | 13.13 | YES |
| Biology Education | 13.1322 | 13.13 | YES |
| Chemistry Education | 13.1323 | 13.13 | YES |
| Physics Education | 13.1329 | 13.13 | YES |
| Music Education | 13.1312 | 13.13 | YES |
| Art Education | 13.1302 | 13.13 | YES |
| Physical Education | 13.1314 | 13.13 | YES |
| Health Education | 13.1307 | 13.13 | YES |
| Foreign Language Education | 13.1306 | 13.13 | YES |
| Drama Education | 13.1324 | 13.13 | YES |
| Agricultural Education | 13.1301 | 13.13 | YES |
| Business Education | 13.1303 | 13.13 | YES |
| Reading Education | 13.1315 | 13.13 | YES |
| School Counseling | 13.1101 | 13.11 | YES |
| ESL Education | 13.1401 | 13.14 | YES |

---

## Broader Gap: Crosswalk vs Career Outcomes by CIP Family

This is not an Education-only problem. The crosswalk-to-career_outcomes granularity mismatch affects every CIP family.

| Family | Crosswalk (6-digit) | Career Outcomes (4-digit) | Overlap | Coverage | Gap |
|--------|--------------------:|-------------------------:|--------:|---------:|----:|
| 01 Agriculture | 84 | 19 | 0 | 0.0% | 84 |
| 03 Natural Resources | 22 | 6 | 0 | 0.0% | 22 |
| 04 Architecture | 18 | 9 | 0 | 0.0% | 18 |
| 05 Area/Ethnic Studies | 50 | 3 | 0 | 0.0% | 50 |
| 09 Communication | 24 | 6 | 0 | 0.0% | 24 |
| 10 Communications Tech | 15 | 4 | 0 | 0.0% | 15 |
| 11 Computer Science | 30 | 10 | 0 | 0.0% | 30 |
| 12 Culinary/Personal Services | 31 | 4 | 0 | 0.0% | 31 |
| **13 Education** | **106** | **15** | **0** | **0.0%** | **106** |
| 14 Engineering | 59 | 41 | 0 | 0.0% | 59 |
| 15 Engineering Tech | 73 | 19 | 0 | 0.0% | 73 |
| 16 Foreign Languages | 84 | 17 | 0 | 0.0% | 84 |
| 19 Family/Consumer Sciences | 33 | 9 | 0 | 0.0% | 33 |
| 22 Legal Professions | 32 | 5 | 0 | 0.0% | 32 |
| 23 English Language/Literature | 13 | 5 | 0 | 0.0% | 13 |
| 24 Liberal Arts | 3 | 1 | 0 | 0.0% | 3 |
| 25 Library Science | 5 | 1 | 0 | 0.0% | 5 |
| 26 Biological Sciences | 92 | 14 | 0 | 0.0% | 92 |
| 27 Mathematics/Statistics | 18 | 5 | 0 | 0.0% | 18 |
| 28 Military Science | 9 | 4 | 0 | 0.0% | 9 |
| 29 Military Technologies | 20 | 5 | 0 | 0.0% | 20 |
| 30 Interdisciplinary Studies | 62 | 43 | 0 | 0.0% | 62 |
| 31 Parks/Recreation | 10 | 5 | 0 | 0.0% | 10 |
| 38 Philosophy/Religious Studies | 16 | 4 | 0 | 0.0% | 16 |
| 39 Theology | 22 | 8 | 0 | 0.0% | 22 |
| 40 Physical Sciences | 45 | 9 | 0 | 0.0% | 45 |
| 41 Science Technologies | 9 | 5 | 0 | 0.0% | 9 |
| 42 Psychology | 31 | 6 | 0 | 0.0% | 31 |
| 43 Homeland Security/Law Enforcement | 37 | 5 | 0 | 0.0% | 37 |
| 44 Public Administration | 14 | 6 | 0 | 0.0% | 14 |
| 45 Social Sciences | 40 | 13 | 0 | 0.0% | 40 |
| 46 Construction Trades | 24 | 4 | 0 | 0.0% | 24 |
| 47 Mechanic/Repair | 41 | 5 | 0 | 0.0% | 41 |
| 48 Precision Production | 17 | 2 | 0 | 0.0% | 17 |
| 49 Transportation | 16 | 3 | 0 | 0.0% | 16 |
| 50 Visual/Performing Arts | 68 | 11 | 0 | 0.0% | 68 |
| **51 Health Professions** | **237** | **29** | **0** | **0.0%** | **237** |
| **52 Business** | **100** | **22** | **0** | **0.0%** | **100** |
| 54 History | 9 | 1 | 0 | 0.0% | 9 |
| 60 Residency Programs | 138 | 0 | 0 | — | 138 |
| 61 Residency Programs | 191 | 0 | 0 | — | 191 |
| **TOTAL** | **1,949** | **390** | **0** | **0.0%** | **1,949** |

**Key takeaway:** The coverage percentage is 0% across the board because the two systems use different granularity levels. This is a universal structural gap, not a data incompleteness issue.

---

## Fallback Viability

The parent-CIP fallback strategy is viable for all 33 broken YAML entries and is likely viable system-wide:

- **Every 6-digit CIP in the crosswalk** can be truncated to its 4-digit parent (first 5 characters)
- Career_outcomes has 390 4-digit CIPs covering all major families
- The strategy: resolve to 6-digit CIP for SOC crosswalk lookups (more specific career mapping), but use the 4-digit parent for earnings/debt data from career_outcomes

### What the fix does NOT solve

The earnings data at the parent CIP level is an aggregate across all specializations within that family. A Deaf Education major (13.1003) would get the same earnings as any other Special Education specialization (13.10). This is a College Scorecard data limitation — they don't report earnings at 6-digit CIP granularity.

---

## Design Decision for the Spec

Two implementation approaches:

| Approach | Where | Pros | Cons |
|----------|-------|------|------|
| **Runtime fallback in MCP server** | `get_career_paths` tool | No pipeline changes, ships fast | Logic scattered, harder to test |
| **Precomputed Gold table** | New or modified Gold zone table | Clean joins, testable, DQ rules apply | Pipeline work, schema change needs spec |

---

## Totals

- **390** distinct 4-digit CIPs in career_outcomes
- **1,949** distinct 6-digit CIPs in crosswalk
- **0** direct overlap
- **33 / 56** YAML substitution entries currently broken
- **100%** of broken entries recoverable via parent-CIP fallback
