# Entity Resolution Review: raw-ipeds-finance (Bronze zone)

**Spec:** `docs/specs/full-pipeline-ipeds-finance.md` v1.3 (Zone 1 — `bronze.ipeds_finance`, sourced from IPEDS Finance F1A/F2/F3 + EFIA + HD; FY23 promote target)
**EDA:** `governance/eda/full-pipeline-ipeds-finance-raw-eda.md` (2026-04-30)
**Date:** 2026-04-30
**Agent:** @entity-resolver
**Verdict:** **NOT APPLICABLE / NO RESOLUTION REQUIRED.** The Bronze zone for IPEDS Finance carries a single authoritative entity (postsecondary institution) keyed by a single stable identifier (`unitid`, the IPEDS UNITID), assembled from a `UNION` of three forms that are physically partitioned by `report_form` with zero cross-form UNITID overlap. There is no aliasing, fuzzy matching, lifecycle reconciliation, or cross-source ID arbitration to perform at this zone.

---

## 1. Entity Model

| Property | Value |
|----------|-------|
| Entity type | Postsecondary institution |
| Grain | One row per `unitid` per `fiscal_year` (institution-level totals) |
| Canonical identifier | `unitid` (long, IPEDS UNITID) |
| Identifier authority | NCES / IPEDS — federal, stable, externally governed |
| Resolution strategy | **ID-based, exact match** (per `governance/domain-context.md` §Entity Types) |
| Source files | `F2223_F1A.csv`, `F2223_F2.csv`, `F2223_F3.csv` (vertical UNION); `EFIA2023.csv` (FTE LEFT JOIN); `HD2023.csv` (filter LEFT JOIN) |
| In-pipeline filter | `HD.ICLEVEL=1 AND HD.HLOFFER>=5` applied via LEFT JOIN to HD; pre-filter UNITIDs = 6,163, post-filter rows = 2,675 |

The domain-context.md `Entity Types` table is explicit: "ID-based resolution. UNITID is stable and authoritative. No resolution needed — use UNITID as-is." That guidance applies verbatim here. `INSTNM` is not carried by `bronze.ipeds_finance` at all (it lives on `bronze.college_scorecard_institution` and is joined in at Silver). Even at Silver, `institution_name` is ride-along context, never a join key — it carries the documented multi-campus collision pattern (10 INSTNM strings map to multiple UNITIDs in College Scorecard).

---

## 2. Cross-Form UNION Cleanly Partitions UNITIDs by `report_form`

The Zone 1 ingestor concatenates three IPEDS Finance forms into one Bronze table, tagging each row with `report_form ∈ {F1A, F2, F3}`. IPEDS assigns each institution to exactly one finance form per cycle, governed by accounting basis:

| Form | Sector | Accounting | FY23 row count | Pct |
|------|--------|------------|---------------:|----:|
| F1A | Public 4-year+ | GASB | 819 | 30.62% |
| F2 | Private nonprofit 4-year+ | FASB | 1,579 | 59.03% |
| F3 | For-profit 4-year+ | FASB / Form-990-style | 277 | 10.36% |
| **Total** | | | **2,675** | **100.00%** |

**Cross-form duplicate UNITIDs: 0** (verified by @bs:data-analyst — `governance/eda/full-pipeline-ipeds-finance-raw-eda.md` §10 audit trail confirms the UNION introduces no duplicates because IPEDS classifies each UNITID into exactly one form per cycle).

Consequence for entity resolution: the UNION is a **disjoint partition**, not an entity-collision surface. There is no UNITID that appears on two forms in the same cycle requiring arbitration — the `report_form` column is purely descriptive metadata of the source schedule, not a competing identity claim. A `GROUP BY unitid` over `bronze.ipeds_finance` yields exactly 2,675 groups of size 1; no de-duplication is needed at any downstream zone for the form-mix dimension.

This is a structural guarantee from IPEDS itself, not an empirical accident. If a future cycle ever produced a UNITID-on-two-forms collision, it would be an upstream IPEDS reporting bug, not a resolution problem; **RAW-IPF-016** (suggested in the EDA, §12) — which bands per-form row counts — would surface the form-mix shift before it became a downstream issue.

---

## 3. UNITID Overlap with Sibling Bronze Tables

Cross-source UNITID overlap calibrations sourced from `governance/eda/full-pipeline-ipeds-finance-raw-eda.md` §6:

| Cross-source pair | Direction | Overlap | Pct | Notes |
|-------------------|-----------|--------:|----:|-------|
| `bronze.ipeds_finance` ∩ `bronze.college_scorecard_institution` | finance→scorecard | 2,621 / 2,675 | **98.0%** | Excellent — the silver-zone join surface is essentially complete |
| `bronze.ipeds_finance` ∩ `bronze.college_scorecard_institution` | scorecard→finance | 2,621 / 3,039 | **86.2%** | The 418 scorecard-only UNITIDs are predominantly 2-year and certificate-granting institutions (correctly excluded by IPEDS Finance HD-filter `ICLEVEL=1 AND HLOFFER>=5`) |
| `bronze.ipeds_finance` ∩ `bronze.eada` | finance↔eada | (will be measured at Silver) | DEFERRED | EADA EDA reports 1,519 / 2,040 (74.5%) overlap with `bronze.college_scorecard_institution`; finance↔eada will be measured at Silver `base.eada` LEFT JOIN per the full-pipeline-eada spec §Zone 2.2 |
| `bronze.ipeds_finance` ∩ `consumable.career_outcomes` | finance→aura | DEFERRED | Will be enforced by **CON-AUR-020** / **CON-AUR-021** at the FULL OUTER JOIN sink in `consumable.institution_aura` |

### What the gaps are, and what they aren't

- **54 finance-only UNITIDs** (2.0% of finance, missing from scorecard): mostly small religious or specialty institutions that opted out of Title IV reporting or have suppressed scorecard rows. Coverage characteristic, not resolution failure.
- **418 scorecard-only UNITIDs** (13.8% of scorecard, missing from finance): 2-year and certificate-granting institutions that fail the `ICLEVEL=1 AND HLOFFER>=5` filter. Coverage characteristic by intentional design — finance is bachelor's-and-up only.

For institutions in both populations, UNITID is a deterministic equi-join key. For institutions in only one population, no resolution would conjure a row that does not exist on the other side. Resolution is the wrong tool — coverage logging at Silver/Gold is the right tool. This calibrates **silver-zone DQ rule for cross-source UNITID coverage to ≥97%** (matching the EDA recommendation, §6).

---

## 4. Lifecycle Events

| Event | Detectability in `bronze.ipeds_finance` | Handling |
|-------|----------------------------------------|----------|
| Institution closure | Not detectable in a single annual snapshot. Tracked only across refreshes (e.g., `fiscal_year=2023` vs `fiscal_year=2024`). | Out of scope for Bronze. Cross-vintage diff at refresh time. |
| Institution name change | `INSTNM` is not carried by `bronze.ipeds_finance`. Drift on the joined-in `bronze.college_scorecard_institution.INSTNM` is harmless — UNITID is the canonical key. | No handling needed. |
| UNITID merger / re-issue | Rare (IPEDS does not re-issue retired UNITIDs). Not observed in FY23. | No handling needed today. |
| Form reclassification (e.g., GASB → FASB) | Possible if an institution's accounting basis changes (rare). Surfaced as a `report_form` change across cycles for the same UNITID. | Out of scope for Bronze. Cross-vintage diff would surface; **RAW-IPF-016** (suggested per-form row-count band) would catch a population-level shift. |
| F3 schedule revision | The post-2014-15 F3 schedule populated `F3E03C1` (institutional support); pre-2014-15 cycles did not. | Already handled via spec v1.3 column-code lock-down (§2 of EDA, RESOLVED). Not a per-row resolution event. |

No lifecycle events are processed at this zone.

---

## 5. Confidence

Match confidence is binary and trivially 1.0 for every row: the source ships UNITID as a typed integer that is the canonical IPEDS-issued ID, and the cross-form UNION introduces zero duplicates. There are no fuzzy matches, no flagged-for-review rows, no <0.7 confidence cases. Resolution statistics are degenerate:

| Metric | Value |
|--------|------:|
| Total entities (UNITIDs) processed | 2,675 |
| Exact-ID matches (confidence 1.0) | 2,675 (100%) |
| Cross-form duplicate UNITIDs | 0 |
| Fuzzy / corroborated matches | 0 |
| Flagged for review | 0 |
| Lifecycle events handled | 0 |

---

## 6. Is an entity registry warranted?

**No.** Same reasoning as the EADA ER review (2026-04-30) and the Anthropic Economic Index ER review (2026-04-16):

1. UNITID is already a federally governed canonical ID — there is no second-source ID to reconcile against at the Bronze zone.
2. The cross-form UNION is a disjoint partition by `report_form`; there is no within-table identity collision.
3. The cross-source pattern is `bronze.ipeds_finance.unitid = bronze.eada.unitid = bronze.college_scorecard_institution.unitid = consumable.career_outcomes.unitid` — a deterministic equi-join, not an alias resolution problem.
4. Confidence scoring would write `1.0` for every row.
5. No lifecycle events to track in a single snapshot.
6. The CDE registry / data contracts already cover UNITID as a shared cross-source CDE (institution identifier). That is the correct locus for institution-identity governance, not a per-source registry.

`governance/entity-registry.json` is not modified by this review.

---

## 7. Forward-Looking Notes for Silver / Gold

The full-pipeline-ipeds-finance spec carries institution identity through downstream joins. All are deterministic equi-joins on `unitid`. **None invoke fuzzy matching, name resolution, or alias reconciliation, and none should.**

| Zone | Join | Notes for downstream agents |
|------|------|-----------------------------|
| Silver — `base.ipeds_finance` | Identity-preserving cleanse over `bronze.ipeds_finance`. Rows preserve `unitid`, `fiscal_year`, `report_form` exactly. The four analytical fields (`instruction_expenses`, `institutional_support_expenses`, `endowment_value`, `total_fte_enrollment`) carry forward unchanged; `data_completeness_tier` (high/medium based on F3's structural endowment NULL) is computed at Silver. **No fuzzy matching.** F3's 100% endowment NULL is a structural NULL (the field does not exist on the F3 schedule) and must remain NULL — never coalesce to 0, never impute from F2/F1A. |
| Silver — `base.eada` (LEFT JOIN to `base.ipeds_finance`) | `raw.eada LEFT JOIN base.ipeds_finance ON unitid` to attach `total_fte_enrollment` for per-FTE derivations. Spec §Zone 2.2.2 of full-pipeline-eada. EADA institutions without an IPEDS Finance row (the 521-row 2-year-college gap, plus the 54 finance-only delta from the inverse direction) get `NULL` FTE; flagged via `fte_source_available BOOLEAN`. **This is correct behavior.** No name-fallback. The 74.5% / 95% threshold question for **BSE-EAD-009** is open per the EADA ER review and is **not** an entity-resolution problem. |
| Silver — `base.college_scorecard_institution` ↔ `base.ipeds_finance` | Cross-source LEFT JOIN on `unitid` (calibrated ≥97% coverage). Used to attach finance-derived per-FTE metrics to scorecard programs at Gold. The 54 finance-only UNITIDs and 418 scorecard-only UNITIDs surface here as `NULL`s on one side; both are coverage characteristics, not resolution failures. |
| Gold — `consumable.institution_aura` | `base.ipeds_finance` **FULL OUTER JOIN** `base.eada` ON `unitid`, with `COALESCE(f.unitid, e.unitid) AS unitid`. Spec §Zone 3 of full-pipeline-eada. **Critical:** the join condition is UNITID and only UNITID. The `has_ipeds_finance` and `has_eada` boolean flags are computed from the join result (`f.unitid IS NOT NULL` / `e.unitid IS NOT NULL`); they explicitly model the asymmetric-coverage case. **Do not introduce a name-based fallback.** It would invent rows that should not exist (multi-campus systems share `INSTNM` but represent distinct UNITIDs). |
| Gold — `consumable.career_outcomes` | `unitid` ↔ `consumable.institution_aura.unitid`. Enforced by **CON-AUR-020** (every aura UNITID exists in `career_outcomes.unitid` or is documented drift) and **CON-AUR-021** (≥90% reverse coverage). Coverage checks against an EDA-calibrated threshold, **not** resolution checks. |

### One-line guarantee

> Across `bronze.ipeds_finance → base.ipeds_finance → consumable.institution_aura → consumable.career_outcomes`, the institution-identity contract is **exact-match on UNITID, with no aliasing and no within-table form-collision**. The cross-form UNION is a disjoint partition. Any future agent (Silver, Gold, or DQ) that proposes a name-similarity fallback or a form-priority arbitration should be rejected on the grounds that UNITID is already authoritative and the form partition is structurally disjoint.

---

## 8. Recommendations

| # | Recommendation | Priority | Owner |
|---|----------------|---------:|:------|
| 1 | **Do not build a per-source entity registry for IPEDS Finance.** UNITID is federally canonical; the cross-form UNION is structurally disjoint. | — | @entity-resolver (closed) |
| 2 | At Silver `base.ipeds_finance` build, preserve F3 `endowment_value` as NULL (structural absence). Codify with **RAW-IPF-015** (suggested in EDA §12): F3 endowment_value = NULL for 100% of F3 rows. | P1 | @silver-transformer + @bs:dq-rule-writer |
| 3 | Add **RAW-IPF-016** (suggested in EDA §12) per-form row-count bands (F1A 700–900, F2 1,400–1,750, F3 200–350) to surface form-mix shifts at refresh time. This is the closest thing to a "lifecycle event" detector this Bronze table needs. | P1 | @bs:dq-rule-writer |
| 4 | At Silver cross-source join (`base.ipeds_finance` ↔ `base.college_scorecard_institution`), log the actual UNITID coverage rate against the ≥97% threshold (calibrated from the 98.0% / 86.2% finance↔scorecard observation). Coverage logging, **not** resolution. | P1 | @silver-transformer |
| 5 | At Gold `consumable.institution_aura` build, ensure `COALESCE(f.unitid, e.unitid)` is the only identity expression in play and there is no name-similarity fallback in the join graph. | P1 | @gold-transformer |
| 6 | At each annual IPEDS Finance refresh (FY24 expected Sep 2026), log adds/drops to the UNITID set vs. the previous vintage and the form-mix delta. No registry needed; a refresh-time diff suffices. | P2 / operational | @data-analyst at next vintage |

---

## 9. Audit Trail

- **Files read:**
  - `docs/specs/full-pipeline-ipeds-finance.md` (v1.3, §4 Zone 1, EDA Requirements)
  - `governance/eda/full-pipeline-ipeds-finance-raw-eda.md` (full FY23 EDA, §§1–13)
  - `governance/entity-resolution/raw-eada-er-assessment.md` (precedent for "no registry warranted" + sibling cross-source overlap framing)
- **Empirical claims sourced from:**
  - 98.0% / 86.2% UNITID overlap with `bronze.college_scorecard_institution`: EDA §6
  - 0 cross-form duplicate UNITIDs: EDA §13 audit trail
  - Form mix (F1A 30.62% / F2 59.03% / F3 10.36%; n=2,675): EDA §7
  - Pre-filter 6,163 / post-filter 2,675: EDA §6
  - Multi-campus INSTNM collision pattern (10 cases): `governance/domain-context.md` Entity Types (cited via the EADA ER review)
- **Decisions logged:** Verdict NOT APPLICABLE. No registry created. No lifecycle events tracked. Forward-looking notes pinned for @silver-transformer, @gold-transformer, @bs:dq-rule-writer.
- **Timestamp:** 2026-04-30
