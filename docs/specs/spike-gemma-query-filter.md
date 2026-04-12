# Spike B: Gemma Query-Time Filtering — Feasibility

**Status:** SPIKE (diagnostic only)
**Created:** 2026-04-11

## Findings

**Diagnostic run:** 2026-04-11
**Script:** `scripts/spike_gemma_filter.py`
**Query:** `get_career_paths(unitid=151351, cipcode="52.01")` — Indiana University-Bloomington, Business/Commerce, General
**Result:** 17 career paths returned.

### 1. Full candidate set (17 rows)

| SOC | Occupation | SOC Major Group |
|---|---|---|
| 11-1011 | Chief executives | Management |
| 11-1021 | General and operations managers | Management |
| 11-2022 | Sales managers | Management |
| 11-3012 | Administrative services managers | Management |
| 11-3013 | Facilities managers | Management |
| 11-3051 | Industrial production managers | Management |
| 11-3071 | Transportation, storage, and distribution managers | Management |
| 11-9021 | Construction managers | Management |
| 11-9072 | Entertainment and recreation managers, except gambling | Management |
| 11-9151 | Social and community service managers | Management |
| 11-9179 | Personal service managers, all other | Management |
| 11-9199 | Managers, all other | Management |
| 13-1051 | Cost estimators | Business and Financial Operations |
| 13-1082 | Project management specialists | Business and Financial Operations |
| 13-1111 | Management analysts | Business and Financial Operations |
| 13-2022 | Appraisers of Personal and Business Property | *(null)* |
| 25-1011 | Business teachers, postsecondary | Educational Instruction and Library |

**Immediate observation:** this is a generic "business manager everyman" slate. It does NOT contain Marketing Managers (11-2021), Financial Managers (11-3031), Human Resources Managers (11-3121), Market Research Analysts (13-1161), Financial Analysts (13-2051), or HR Specialists (13-1071). The CIP 52.01 → SOC crosswalk is explicitly broad by design: the "General" program maps to generic business leadership roles, not to specializations.

### 2. "Marketing" filter

Heuristic: SOC title / major-group name contains any of `marketing, advertising, sales, public relations, market research, promotion, brand`; or SOC matches prefix in `{11-2021, 11-2022, 11-2032, 13-1161, 27-3031, 41-}`.

**Kept: 1 / 17**

| SOC | Occupation | Why |
|---|---|---|
| 11-2022 | Sales managers | keyword: `sales` |

**Dropped: 16 / 17** (all 16 rows not shown above).

The only survivor is Sales managers, and only because "sales" was one of the keywords. A purist might argue Sales Managers is NOT marketing-relevant — it's the *post-marketing* revenue motion — which makes even this single survivor a borderline false positive.

### 3. "Finance" filter

Heuristic: title / group contains `financial, finance, treasur, budget, credit, investment, loan, accountant, accounting, auditor, actuarial`; or SOC prefix in `{11-3031, 13-2}`.

**Kept: 4 / 17**

| SOC | Occupation | SOC Major Group | Why |
|---|---|---|---|
| 13-1051 | Cost estimators | Business and Financial Operations | kw:`financial` (via group name) |
| 13-1111 | Management analysts | Business and Financial Operations | kw:`financial` (via group name) |
| 13-1082 | Project management specialists | Business and Financial Operations | kw:`financial` (via group name) |
| 13-2022 | Appraisers of Personal and Business Property | *(null)* | soc prefix `13-2` |

**Verdict:** 3 of the 4 survivors are **false positives** driven by the string "Financial" appearing in the SOC major-group name "Business and Financial Operations". Cost estimators, management analysts, and project management specialists are not finance careers — they just happen to sit in a major group whose title mentions the word. Only the Appraiser role (caught via prefix 13-2) is arguably finance-adjacent, and even that is a stretch.

### 4. "HR" filter

Heuristic: title / group contains `human resources, personnel, training and development, compensation, benefits, labor relations, recruit`; or SOC prefix in `{11-3111, 11-3121, 11-3131, 13-1071, 13-1075, 13-1141, 13-1151}`.

**Kept: 0 / 17.**

Not a single row survives. Every HR-relevant SOC (11-3121 HR Managers, 13-1071 HR Specialists, 13-1141 Comp/Benefits Analysts, 13-1151 Training/Development Specialists) is simply absent from the 17 candidates. The filter is doing its job — there is nothing HR-shaped in the input.

### 5. Summary counts

| Intent | Kept | Dropped | Usable for product? |
|---|---|---|---|
| marketing | 1 | 16 | No — too narrow; sole survivor is arguable |
| finance | 4 | 13 | No — 3 of 4 are false positives |
| hr | 0 | 17 | No — zero coverage |

### 6. False-positive / false-negative analysis

**False positives (heuristic keeps things that shouldn't be kept):**
- `kw:financial` matching the group name "Business and Financial Operations" pollutes the finance filter with every 13-1xxx generalist. Group-name matching is the main attack surface.
- `kw:sales` catching Sales Managers for the marketing filter is debatable; Sales and Marketing are distinct functions, even though recruiters lump them.
- A richer CIP (not 52.01) with SOC 11-9199 "Managers, all other" would pass literally any keyword filter that hit that row's generic description.

**False negatives (heuristic drops things that should be kept):**
- Management analysts (13-1111) and Project management specialists (13-1082) contain legitimate marketing/finance/HR subspecialties in practice but get dropped (for marketing and HR) because their titles and group names are intent-neutral.
- Business teachers, postsecondary (25-1011) arguably teach marketing/finance/HR — pedagogical path dropped by every filter.
- For a richer CIP, an HR Specialist (13-1071) sits in "Business and Financial Operations" — a keyword filter on group name would mis-file them as finance, and a marketing filter on title alone would miss "Compensation & Benefits Analyst" unless the keyword list is tuned precisely.

---

## Assessment

### The keyword heuristic is not the real problem.

The spike was framed as "heuristic vs. Gemma", but the diagnostic reveals the actual bottleneck sits one layer lower. **The CIP 52.01 → SOC crosswalk returns a generic business-manager slate that does not contain the specialization the student asked for.** Marketing Managers (11-2021), Financial Managers (11-3031), and HR Managers (11-3121) are *not in the candidate set at all*. No filter — heuristic, LLM, or oracle — can recover a row that was never passed in.

This means **query-time filtering on the output of `get_career_paths(unitid, "52.01")` cannot satisfy the "I want marketing" intent**, regardless of filter sophistication.

### What the filter numbers say

- **marketing:** 1 kept, and it's borderline (Sales Managers).
- **finance:** 4 kept, 3 of them false positives from group-name matching.
- **hr:** 0 kept.

All three results are outside the usable band (spec target: 3–15 survivors that a student would recognize as relevant to their stated intent). Only the finance filter hits the count band, and only because of contamination.

### Would Gemma do better than the heuristic?

**On this input: marginally, and not enough to matter.**
- Gemma would correctly drop the three false-positive finance hits (cost estimators, management analysts, project management specialists are not finance careers and an LLM knows that).
- Gemma would correctly flag Sales Managers as "sales, not marketing" for a student who specifically asked for marketing.
- Gemma could rewrite the presentation ("you asked for marketing; the closest match in this school's general business program is Sales Management, because College Scorecard does not report a dedicated marketing program outcome for IU-B").

What Gemma **cannot** do is invent 11-2021 Marketing Managers, 11-3031 Financial Managers, or 11-3121 HR Managers as career paths for this program. The crosswalk simply doesn't emit them.

### Recommendation

**Query-time filtering — whether heuristic or LLM — is the wrong layer to solve the intent-specialization problem.** Two fixable layers sit upstream:

1. **Crosswalk coverage for broad CIPs (Silver zone).** The CIP 52.01 → SOC mapping should either (a) fan out to include the full specialization slate (11-2021, 11-3031, 11-3121, 13-1161, 13-2051, etc.) that a Business General graduate could plausibly pursue, *or* (b) the product should not let a student drill into "I want marketing" while holding a "Business General" program pointer — route them instead to the school's marketing program if one exists.
2. **Program selection (MCP / product layer).** When the student says "marketing", the program-picker in `find_marketing_program()` already has a `fallback_business` tier for schools without a standalone marketing program. The query-time filter idea is trying to do the same job after the fact — better to strengthen the upstream selection.

**On the filter itself:** if we ever do want intent filtering over a richer candidate set, the heuristic should (a) **only match title, not SOC major-group name** (group-name matching is the main false-positive source), (b) maintain an explicit SOC allow-list per intent (the prefix list in this script), and (c) fall back to Gemma only when the allow-list yields <3 survivors. But again — that's polish on a layer that is not the root problem.

**Verdict: do not ship Gemma query-time filtering as a solution to this problem.** Fix crosswalk fan-out and program selection instead. See sibling spikes `spike-broad-cip-prevalence.md`, `spike-cip-hierarchy-fallback.md`, and `spike-cip-override-table.md` for the upstream fixes.

---

## Instructions

Write a throwaway script `scripts/spike_gemma_filter.py` that answers the questions below, then populate the Findings section of this spec file (`docs/specs/spike-gemma-query-filter.md`) with the results in markdown tables. Do NOT change any production code or data.

### Queries

1. Call `get_career_paths(151351, "52.01")` — the IU-B Business/Commerce General results (17 career paths).

2. For each returned SOC code, look up the SOC major group name. Classify each career path as "marketing-relevant" or "not marketing-relevant" using a simple heuristic: SOC title or major group contains "marketing", "advertising", "sales", "public relations", "market research", or the SOC is in major group 11-20xx (advertising/marketing/PR managers) or 13-11xx (business operations specialists in marketing).

3. Show the filtered list — which careers survive the "marketing" filter vs. which get dropped?

4. Now do the same for a student who said "Finance" — filter for finance-relevant SOCs. And "HR" — filter for HR-relevant SOCs. Does the heuristic hold across different majors within the same broad CIP?

5. What's the false-positive and false-negative risk? Are there legitimate marketing careers that the heuristic would drop? Non-marketing careers it would keep?

### Assessment

After running the filters, assess:
- Is a keyword heuristic robust enough to ship, or does this need Gemma's LLM judgment?
- How many SOCs survive each filter? Is the filtered set too small (< 3) or too large (> 15)?
- Would Gemma do better than the heuristic? If so, what would the prompt look like?

### Output

Update the Findings section of THIS file (`docs/specs/spike-gemma-query-filter.md`) with the results as markdown tables and the assessment. Leave the script at `scripts/spike_gemma_filter.py` for reproducibility.
