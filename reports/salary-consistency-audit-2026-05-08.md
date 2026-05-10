# Salary Consistency Audit — FutureProof Web App

**Date:** 2026-05-08
**Auditor:** Claude (Opus 4.7) via Playwright harness
**Harness:** `scripts/audit_salary_consistency.py`
**Build under test:** branch `grad-school-suggestion`, backend on `:8000`, frontend on `:5173`, inference backend `openrouter` / `google/gemma-4-26b-a4b-it`
**Schools driven:** Indiana University-Bloomington (Marketing → Fundraisers), Harvard University (CS → Computer network support specialists), Miami Dade College (Nursing → Registered nurses), California Institute of Technology (Mechanical Engineering → Aerospace engineers).

> **Note on test set.** The original audit plan called for Ivy Tech Community College as the 2-year/vocational pick. Ivy Tech is not in the IPEDS subset shipped in the demo dataset (zero results for `Ivy Tech*` across five query variants). Substituted with Miami Dade College — same shape (public 2-year), in-state Florida residency.

## Executive summary

**Three salary-rendering inconsistencies found across the audited surfaces:**

1. **🔴 CRITICAL: PDF "Year-1 median earnings" is mathematically inconsistent with the year-one range shown to the same student on /my-build.** For 3 of the 4 builds the PDF prints a median that exceeds the 75th-percentile shown on the Finances card. For one build (IU/Marketing/Fundraisers) the PDF even contradicts itself internally — it states "Year-1 median earnings $63,371" on page 1 and "Year-1 75th-percentile wage is $49,674" on page 1's Career Risk Profile. A median cannot exceed its own 75th percentile. Likely root cause: `earnings_1yr_median` and `earnings_1yr_p25/p75` are sourced from different College Scorecard aggregations (career-blended vs program-level) but rendered together as if from the same row.

2. **🟡 Same field, different label, different surface.** The fields `earnings_1yr_p25` / `earnings_1yr_p75` are labeled "Year-one from {school}" on the Finances card (implying program-specific) but "Peer 25th–75th" on the Comparison view (implying peer-wide across all schools in this CIP). Either the data is the same and one label is wrong, or the data is different and the field name is being overloaded. Source: `FinancesCard.tsx:202-204` vs `MoneySection.tsx`.

3. **🟡 Compare-view fallback diverges from comparison-PDF behavior** when `earnings_1yr_median` is null. Compare UI silently substitutes `median_annual_wage` ($134,830 → "$135K") and adds a footnote "career wage reference because program median earnings are unavailable." Compare PDF, given the same null, prints "—" with no fallback. Same data → two different stories on two surfaces of the same comparison.

**Otherwise, salary numbers are consistent across surfaces.** Mid-career salary (`median_annual_wage`), OEWS career percentiles (`wage_p10`/`p25`/`p75`), 4-year cost (`published_cost_4yr`), modeled debt (`modeled_total_debt`), and debt-to-earnings all match exactly between SetYourCourse → Finances → Single PDF → Comparison PDF for every build that has the underlying data.

## What was driven

For each of the 4 schools, the harness:

1. Onboarded a fresh profile (`/profile` → home state → continue).
2. Picked the school via the SchoolSearch combobox on `/set-your-course`.
3. Typed the major; waited for Gemma to stream a CIP resolution + load careers.
4. Captured the SetYourCourse career card text (full screenshot + DOM scrape).
5. Clicked the first career returned, then committed the build via `btn-spec-build-bottom` to land on `/my-build`.
6. Captured the Finances card text (full screenshot + DOM scrape).
7. Opened the ERN stat popover, screenshot, closed; same for ROI.
8. Saved the build via `btn-save-build-bar`.
9. Clicked Export PDF, captured the PDF download, extracted text via `pypdf`.

After all 4 builds, navigated via the `header-compare` button (SPA navigation, preserves the saved-build list across the in-memory profile reset that occurs each onboarding) to `/builds?select=1`, selected the 4 most-recent build cards, clicked Compare, screenshotted the comparison view, exported the comparison PDF, and extracted its text.

All artifacts are in `reports/salary-audit/`:
- `screenshots/` — 22 full-page PNGs
- `pdfs/` — 4 single-build PDFs + 1 comparison PDF, plus `.txt` extractions
- `raw/` — per-build JSON dumps + a combined `_summary.json`

## Per-build salary matrix

Each row is a salary concept; each column is a surface. ✓ = displayed and matches the underlying field; ✗ = not shown on this surface; **bold dollar** = the value the surface displayed; ⚠ marks an inconsistency.

### Build 1 — Indiana University-Bloomington · Marketing · Fundraisers (SOC 13-1131)

| Field | SetYourCourse card | Finances card | Stat popovers | Single PDF | Compare PDF | Compare Money |
|---|---|---|---|---|---|---|
| `median_annual_wage` (mid-career) | ✓ **$66,490** | ✓ **$66,490** | ✗ static text only | ✗ | ✗ | ✗ |
| `wage_p10`–`wage_p25` (OEWS starting) | ✓ **$43,200 – $52,590** | ✓ **$43,200 – $52,590** | ✗ | ✗ | ✗ | ✗ |
| `earnings_1yr_p25`–`p75` (year-one program range) | ✗ (OEWS preempts) | ✓ **$38,515 – $49,674** ("Year-one from IU") | ✗ | ✗ | ✗ | ✓ **$39K / $50K** ("Peer 25th"/"75th") |
| `earnings_1yr_median` (year-one program median) | ✗ | ✗ (range preempts) | ✗ | ⚠ **$63,371** ("Year-1 median earnings") | ⚠ **$63,371** ("Year-1 earnings") | ⚠ **$63K** ("This program median") |
| `published_cost_4yr` | ✗ | ✓ **$109,444** | ✗ | ✓ **$109,444** | ✓ **$109,444** | ✗ |
| `modeled_total_debt` | ✗ | ✓ **$54,722** | ✗ | ✓ **$54,722** | ✓ **$54,722** | ✗ |
| `debt_to_earnings_annual` | ✗ | ✓ ROI label only | ✗ | ✓ **173%** | ✓ **173%** | ✗ |

**Inconsistency in this row:** the Finances card tells the student their year-one earnings will be $38,515–$49,674. The PDF prints **$63,371** as the year-1 median for the same selection. $63,371 > $49,674, so the PDF's median is *outside* the range the same product just showed for the same field. The PDF Career Risk Profile then states "Year-1 75th-percentile wage is $49,674 — meaningful upside above the median" (line 71 of the extracted PDF text), implying p75 < median, which is impossible.

Screenshots: [01-iu-set-your-course.png](salary-audit/screenshots/01-iu-set-your-course.png) · [01-iu-finances.png](salary-audit/screenshots/01-iu-finances.png) · [01-iu-ern-popover.png](salary-audit/screenshots/01-iu-ern-popover.png) · [01-iu-roi-popover.png](salary-audit/screenshots/01-iu-roi-popover.png)
PDF: [01-iu.pdf](salary-audit/pdfs/01-iu.pdf) · [01-iu.txt](salary-audit/pdfs/01-iu.txt)

### Build 2 — Harvard University · Computer Science · Computer network support specialists (SOC 15-1231)

| Field | SetYourCourse card | Finances card | Single PDF | Compare PDF | Compare Money |
|---|---|---|---|---|---|
| `median_annual_wage` | ✓ **$73,340** | ✓ **$73,340** | ✗ | ✗ | ✗ |
| `wage_p10`–`wage_p25` (OEWS) | ✓ **$46,010 – $56,720** | ✓ **$46,010 – $56,720** | ✗ | ✗ | ✗ |
| `earnings_1yr_p25`–`p75` | ✗ | ✓ **$46,984 – $65,661** | ✗ | ✗ | ✓ **$47K / $66K** |
| `earnings_1yr_median` | ✗ | ✗ | ⚠ **$140,072** | ⚠ **$140,072** | ⚠ **$140K** |
| `published_cost_4yr` | ✗ | ✓ **$331,368** | ✓ **$331,368** | ✓ **$331,368** | ✗ |
| `modeled_total_debt` | ✗ | ✓ **$165,684** | ✓ **$165,684** | ✓ **$165,684** | ✗ |

**Same inconsistency, larger gap:** Finances year-one is $46,984–$65,661; PDF prints $140,072. The PDF claims the year-1 median is more than 2× the displayed 75th percentile.

### Build 3 — Miami Dade College · Nursing · Registered nurses (SOC 29-1141)

| Field | SetYourCourse card | Finances card | Single PDF | Compare PDF | Compare Money |
|---|---|---|---|---|---|
| `median_annual_wage` | ✓ **$93,600** | ✓ **$93,600** | ✗ | ✗ | ✗ |
| `wage_p10`–`wage_p25` (OEWS) | ✓ **$66,030 – $78,610** | ✓ **$66,030 – $78,610** | ✗ | ✗ | ✗ |
| `earnings_1yr_p25`–`p75` | ✗ | ✓ **$32,935 – $62,573** | ✗ | ✗ | ✓ **$33K / $63K** |
| `earnings_1yr_median` | ✗ | ✗ | ⚠ **$73,541** | ⚠ **$73,541** | ⚠ **$74K** |
| `published_cost_4yr` | ✗ | ✓ **$50,140** | ✓ **$50,140** | ✓ **$50,140** | ✗ |
| `modeled_total_debt` | ✗ | ✓ **$25,070** | ✓ **$25,070** | ✓ **$25,070** | ✗ |

**Same shape:** Finances range $32,935–$62,573 vs PDF median $73,541. Median is $11K above the displayed p75. RN data is unusually noisy to begin with (RN can be a 2-year ADN or a 4-year BSN program; Scorecard mixes them at different aggregations) — but the product surfaces the resulting incoherence to the student instead of reconciling it.

### Build 4 — California Institute of Technology · Mechanical Engineering · Aerospace engineers (SOC 17-2011)

| Field | SetYourCourse card | Finances card | Single PDF | Compare PDF | Compare Money |
|---|---|---|---|---|---|
| `median_annual_wage` | ✓ **$134,830** | ✓ **$134,830** | ✗ | ✗ | ⚠ **$135K** (used as fallback) |
| `wage_p10`–`wage_p25` (OEWS) | ✓ **$85,350 – $104,740** | ✓ **$85,350 – $104,740** | ✗ | ✗ | ✗ |
| `earnings_1yr_p25`–`p75` | ✗ | ✓ **$60,121 – $69,541** | ✗ | ✗ | ✗ (suppressed when median null?) |
| `earnings_1yr_median` | ✗ | ✗ (median field null) | ⚠ **"—"** (null) | ⚠ **"—"** (null) | ⚠ falls back to mid-career |
| `published_cost_4yr` | ✗ | ✓ **$334,392** | ✓ **$334,392** | ✓ **$334,392** | ✗ |
| `modeled_total_debt` | ✗ | ✓ **$167,196** | ✓ **$167,196** | ✓ **$167,196** | ✗ |

**Two issues for Caltech:**
- `earnings_1yr_median` is null (College Scorecard suppresses it for small completer cohorts), but `earnings_1yr_p25` and `p75` are populated. The fact that the median is missing while the percentile range is present is itself evidence that these fields come from different aggregations.
- The PDF prints "—" for year-1 earnings; the Compare Money section, given the same null, falls back to `median_annual_wage` ($134,830 → "$135K") and explains itself with a footnote. **Same null, two different rendering policies.** The student looking at the Compare table sees a $135K bar for Caltech; the student opening the comparison PDF sees a blank cell.

## Cross-build consistency findings

### ✓ Mid-career salary is consistent everywhere it's shown

`median_annual_wage` matches exactly between the SetYourCourse career card and the Finances card on /my-build for all 4 builds. It is not surfaced in the single-build PDF or the comparison PDF (a deliberate omission — those PDFs lead with year-1 earnings). The Compare Money section uses it as a documented fallback for null program-medians.

### ✓ OEWS national career percentiles are consistent

`wage_p10` and `wage_p25` displayed as "Career starting range" on the Finances card match the "starting range" shown on the SetYourCourse card byte-for-byte across all 4 builds. All 4 careers fell into the entry-accessible OEWS branch (`work_experience_code` ∈ {2, 3, null}) — none of the picks exercised the long-term `wage_p25–wage_p75` "typical range" branch. **Coverage gap noted:** the audit didn't naturally hit that branch.

### ✓ Cost and debt fields are consistent

`published_cost_4yr`, `modeled_total_debt`, and `debt_to_earnings_annual` (where rendered) match exactly between Finances card, single PDF, and comparison PDF for all 4 builds. No discrepancies.

### 🔴 Year-1 program earnings are NOT consistent

This is the headline finding. To restate the math:

| Build | Finances year-1 range (p25 – p75) | PDF year-1 median | Median in range? |
|---|---|---|---|
| IU/Marketing | $38,515 – $49,674 | $63,371 | **NO — median > p75 by $13,697** |
| Harvard/CS | $46,984 – $65,661 | $140,072 | **NO — median > p75 by $74,411** |
| Miami Dade/Nursing | $32,935 – $62,573 | $73,541 | **NO — median > p75 by $10,968** |
| Caltech/ME | $60,121 – $69,541 | null ("—") | not testable |

In a single coherent dataset the median MUST sit between p25 and p75. The fact that it doesn't, in 3 of 3 testable cases, means `earnings_1yr_median` and `earnings_1yr_p25/p75` are not coming from the same row of the same Scorecard aggregation. The product currently renders them as if they were. **A counselor reading the PDF would conclude this product cannot do basic statistics.**

Likely sources of the divergence:
- College Scorecard publishes *Field-of-Study* earnings at the program level (recent grads, narrow cohort) and *Institution-level* earnings (all grads of the school across programs). The percentiles and the median may be coming from different tables.
- Or: percentiles are at one cohort year (say, 1-yr post-graduation) and the median at another (say, the broader Field-of-Study median which may include later cohorts).
- Or: one is the IPEDS Scorecard FieldOfStudy CSV and the other is the Scorecard MERGED institution-level CSV.

This is a **data-pipeline audit problem**, not a UI bug — the UI is faithfully displaying what the backend hands it. But the student sees the contradiction.

### 🟡 Same field, different label

The same `earnings_1yr_p25` / `earnings_1yr_p75` values render under two labels:

- **Finances card** (`FinancesCard.tsx:202-204`): label `"Year-one from {school}"` (e.g. "Year-one from Indiana University-Bloomington")
- **Compare Money section** (`MoneySection.tsx`): label `"Peer 25th"` and `"Peer 75th"`, with the explainer "Band shows the middle 50% of peer programs in this field."

If the field is school-specific (as the Finances label asserts), the Compare label is wrong. If the field is peer-wide (as Compare asserts), the Finances label is wrong. Both surfaces are reading the same field on the same `CareerOutcome` model — they cannot both be right.

This is the same root cause as #1: the data layer is conflating two different aggregations under one field name, and different surfaces interpret it differently.

### 🟡 Null-handling diverges between Compare UI and Comparison PDF

For Caltech (`earnings_1yr_median` is null):

- **Compare Money section** renders **$135K** for Caltech with a footnote "Pill is a career wage reference because program median earnings are unavailable" — silently substituting `median_annual_wage`.
- **Comparison PDF Year-1 earnings row** renders **"—"** for Caltech — no fallback, just a blank.

A student who sees the comparison on screen, then exports the same comparison to PDF, gets two different stories about the same school's year-1 earnings. The on-screen $135K is also misleading: a "career wage reference" is the typical mid-career incumbent's salary, not what a 22-year-old graduate makes year one. The PDF's "—" is more honest, but the inconsistency between the two surfaces is the bigger issue.

### 📝 Display precision differs (informational)

Same value, different rounding across surfaces:

| Surface | Renders $63,371 as |
|---|---|
| Single PDF | `$63,371` |
| Comparison PDF | `$63,371` |
| Compare Money pill | `$63K` |

Probably intentional (Compare Money uses `$K` shorthand for dense bars), but worth listing for completeness — the audit found this everywhere there's a numeric pill in MoneySection.

### 📝 Stat popovers do not surface live numbers

Both ERN and ROI popovers opened cleanly on all 4 builds (`open_stat_popover` reported `opened: true` for every run). Their content is **purely the static definition** from `bossData.ts:90-100` plus a "Source: …" line — they cite no live computed numbers from the build. Live numbers only appear in the chat that opens after clicking "Explain this to me," which calls Gemma and is out of scope for this consistency audit.

This means **the popover layer does not introduce or replicate any salary numbers**, so the popovers cannot drift from the Finances card. Listed here so future audits don't waste time on it.

## Recommendations

In rough priority order:

1. **Fix the year-1 median/percentile pairing in the Gold zone.** Decide whether `earnings_1yr_median` and `earnings_1yr_p25/p75` should be (a) from the same Scorecard FieldOfStudy row, in which case the percentiles will be different from what's shown today, or (b) explicitly different aggregations, in which case the UI must label them as such ("Field median: $X · This program peer-band: $A–$B"). Either way, never render a median outside its own range without explanation.

2. **Reconcile FinancesCard "Year-one from {school}" vs Compare "Peer 25th–75th".** Pick one semantic for `earnings_1yr_p25/p75` and label it the same way everywhere. If you need both program-specific and peer-wide ranges, ship them as different fields.

3. **Make the Compare-UI null-fallback match the Comparison-PDF behavior.** Either both surfaces fall back to `median_annual_wage` (with a label change) or both surfaces print "—". Two-stories-from-one-dataset is a credibility hit.

4. **Add an internal data-quality check** that fails the build (or at minimum logs a warning) when `earnings_1yr_median > earnings_1yr_p75` or `< earnings_1yr_p25`. This would have caught all 3 of these failures before they shipped.

5. **Once the data layer is sane, consider adding the year-1 median to the Finances card** — currently it's hidden when the range is available (`FinancesCard.tsx:131-135`), which is the only reason the inconsistency hides until the user exports the PDF. Showing the median next to its range would either expose the data bug to product (forcing a fix) or give the student the same number on both surfaces.

## How to re-run the audit

```bash
# Bring servers up.
cd backend && python -m uvicorn app.main:app --port 8000 &
cd frontend && npm run dev &

# Run the harness (uses backend venv for playwright + pypdf).
/Users/jcernauske/code/bright/futureproof-data/backend/.venv/bin/python \
  scripts/audit_salary_consistency.py
```

Output lands under `reports/salary-audit/` (cleared on each run). Total runtime is ~6–8 minutes against `openrouter` inference; the slow path is Gemma streaming the CIP resolution for each major.

## Verification I did on this report

- Spot-checked screenshot `01-iu-finances.png` — the rendered dollars match what `01-iu.json` says was scraped.
- Read `01-iu.txt` lines 43–71 directly to confirm the PDF really does state both "Year-1 median earnings $63,371" and "Year-1 75th-percentile wage is $49,674" for the same build.
- Read `compare.txt` to confirm the comparison PDF prints the same per-school year-1 medians as the single PDFs ($63,371 IU / $140,072 Harvard / $73,541 Miami / "—" Caltech) and "—" for Caltech specifically.
- Read `compare.json` `money_section_text` to confirm the Compare Money section surfaces $135K for Caltech with the explanatory footnote.
- Confirmed the harness picked the correct 4 builds for the comparison (the 4 most-recent saved builds, which are exactly the ones this run created — `compare.json` `builds_in_view[:4]` matches the 4 builds we just saved).

What I did **not** verify, by design:
- Whether Gemma-resolved CIPs match what a human counselor would expect for each major. The audit follows whatever Gemma resolves to.
- The accuracy of the underlying College Scorecard / BLS / O*NET data itself. The audit only checks that the same data is rendered the same way across surfaces.
