# Entity Resolution Review — Gold Enrichment: `consumable.career_outcomes`

**Spec:** `docs/specs/raw-ingest-college-scorecard-institution.md` (Zone 3)
**Zone:** Gold (enrichment, not new entity)
**Table:** `consumable.career_outcomes`
**Reviewer:** @entity-resolver
**Date:** 2026-04-16
**Verdict:** APPROVED

---

## Summary (≤80 words)

Gold enrichment is entity-resolution-safe. UNITID (IPEDS-canonical, resolved at Silver) remains the institution key; the LEFT JOIN introduces no new entities, just 7 nullable attributes on the existing `CareerOutcome` entity. Empirical verification: row count preserved at 69,947; 2,352 of 2,559 distinct UNITIDs matched (207 unmatched, per EDA); `institution_control` values limited to the 3 permitted categoricals; Harvard/MIT/Stanford/Yale resolve correctly with sensible COA and net-price figures. APPROVED.

---

## 1. Scope of Review

No new canonical entity is introduced at Gold. This is an **attribute enrichment** of an existing entity (`CareerOutcome`, already keyed on UNITID + CIPCODE + CREDLEV). The join key UNITID is:

- The **IPEDS-canonical institution identifier**, reused federally across education data.
- Already entity-resolved at Silver via `base.college_scorecard_institution` (see silver pre/post/staff reviews for that spec — a dedicated `silver-...-entity-resolution.md` file is not present under that exact name, but the identity semantics are documented inline in `governance/reviews/silver-base-college-scorecard-institution-{pre,post,staff}-review.md` and in `docs/sessions/eda-college-scorecard-institution.md`).
- The same UNITID used by the field-of-study file that already populates `consumable.career_outcomes`, so no cross-system reconciliation is needed.

Therefore the entity-resolver concern at Gold is narrow: **does the LEFT JOIN preserve the existing UNITID canonicalization, and does the re-sourced `institution_control` create identity drift?**

---

## 2. Checks Performed

### 2.1 UNITID canonicality post-join

Verified against the materialized Iceberg table at `data/gold/iceberg_warehouse/consumable/career_outcomes`:

| Metric | Expected (spec/EDA) | Observed | OK? |
|---|---|---|---|
| Row count | 69,947 | 69,947 | yes |
| Distinct UNITIDs (total) | — | 2,559 | yes |
| Distinct UNITIDs matched (institution_control non-null) | 2,352 | 2,352 | yes (exact) |
| Distinct UNITIDs unmatched | 207 | 207 | yes (exact) |

No row duplication, no UNITID fan-out from the LEFT JOIN. The institution-side grain is one row per UNITID, which is enforced at Silver (dedup grain `[unitid]`), so a left join on UNITID is guaranteed to be 1:N (career-outcomes side) → 1 — i.e., row-preserving.

**No collisions observed.** UNITID remains the sole canonical institution key.

### 2.2 `institution_control` re-sourcing — identity drift check

`institution_control` was previously 100% null on the field-of-study-derived `career_outcomes` (the upstream FOS file does not carry a usable control label). The enrichment now sources it from the institution file. This is a **true re-sourcing** (null → real value) rather than an overwrite of a previously-populated attribute, so there is no risk of silently changing identity-bearing data. The recommendation in the 2026-04-06 insight report is satisfied.

Distinct observed values (row-level):

- `Private nonprofit` — 37,211 rows
- `Public` — 29,374 rows
- `Private for-profit` — 1,558 rows
- `NULL` (unmatched UNITID) — 1,804 rows

All non-null values are in the permitted categorical set `{Public, Private nonprofit, Private for-profit}` (GLD-CSI-009 intent — confirmed). No rogue values, no taxonomy drift.

### 2.3 Sanity-spot-check — named elite institutions

| UNITID | institution_name (Silver) | institution_control | cost_of_attendance_annual | net_price_annual | Sensible? |
|---|---|---|---|---|---|
| 166027 | Harvard University | Private nonprofit | $82,842 | $16,816 | yes |
| 166683 | Massachusetts Institute of Technology | Private nonprofit | $79,850 | $19,813 | yes |
| 243744 | Stanford University | Private nonprofit | $82,162 | $12,136 | yes |
| 130794 | Yale University | Private nonprofit | $85,120 | $27,818 | yes |
| 165015 | Brandeis University | Private nonprofit | $82,123 | $33,885 | yes |

All four requested elite UNITIDs resolve to the correct named institution and the expected `Private nonprofit` control. COA in the high-$70K–mid-$80K range and net price well below sticker (reflecting high institutional aid) — behavior consistent with BT-111 and with the silver invariant `net_price_annual ≤ cost_of_attendance_annual`.

**Note on the request body:** UNITID 165015 is **Brandeis**, not Harvard. Harvard is UNITID **166027**. Checked both — both resolve cleanly, so this is a transcription nit in the request, not a data defect.

### 2.4 Unmatched UNITIDs (207 institutions)

207 UNITIDs in `career_outcomes` have no row in `base.college_scorecard_institution` and therefore get NULLs for all 7 enrichment columns. This is the expected asymmetric-coverage behavior of the two Scorecard files (institution file filters to `PREDDEG=3` / `ICLEVEL=1`; the field-of-study file has broader admission criteria). These UNITIDs are **still canonically resolved** — they simply have no attributes to merge. Entity identity is unaffected.

---

## 3. Lifecycle Events

None discovered or relevant. No mergers, splits, IPEDS renumberings, or name changes triggered by this enrichment — the join is purely additive attribute propagation on an already-resolved identifier.

---

## 4. Confidence Scoring

| Resolution Method | Confidence | Rows |
|---|---|---|
| Exact UNITID match (both files agree on integer key) | 1.0 | 68,143 rows across 2,352 UNITIDs |
| Unmatched (UNITID exists in FOS but not in institution file) | N/A (not a resolution failure — attribute gap only) | 1,804 rows across 207 UNITIDs |

No fuzzy matching was required or performed. No rows require human review.

---

## 5. Scope Boundaries Honored

- Did NOT normalize taxonomies (that was @cde-tagger at Silver).
- Did NOT rewrite the UNITID canonical registry (already maintained at Silver).
- Did NOT auto-resolve anything below 1.0 confidence — there were no such cases.

---

## 6. Verdict

**APPROVED.**

The Gold enrichment preserves UNITID canonicalization, introduces no new entities, and the `institution_control` re-sourcing is a null-fill with no identity drift. Proceed to remaining Gold-zone gates (adversarial-auditor, lineage/CDE/doc-generator, governance-reviewer-post, staff-engineer).
