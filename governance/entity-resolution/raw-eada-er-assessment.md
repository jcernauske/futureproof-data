# Entity Resolution Review: raw-eada (Bronze zone)

**Spec:** `docs/specs/full-pipeline-eada.md` (Zone 1 — `raw.eada`, sourced from EADA 2022–2023 `InstLevel.xlsx`)
**Date:** 2026-04-30
**Agent:** @entity-resolver
**Verdict:** **NOT APPLICABLE / NO RESOLUTION REQUIRED.** The Bronze zone for EADA carries a single authoritative entity (postsecondary institution) keyed by a single stable identifier (`unitid`, the IPEDS UNITID) sourced from a single file. There is no aliasing, fuzzy matching, lifecycle reconciliation, or cross-source ID arbitration to perform at this zone.

---

## 1. Entity Model

| Property | Value |
|----------|-------|
| Entity type | Postsecondary institution |
| Grain | One row per `unitid` (institution-level totals) |
| Canonical identifier | `unitid` (long, IPEDS UNITID) |
| Identifier authority | NCES / IPEDS — federal, stable, externally governed |
| Resolution strategy | **ID-based, exact match** (per `governance/domain-context.md` §Entity Types) |
| Source file | `InstLevel.xlsx` from EADA 2022–2023 datafile zip — institution totals only; `Schools.xlsx` (per-team grain) is not ingested |
| In-pipeline filter | None (institution totals are physically separated by file, not by row marker) |

The domain-context.md `Entity Types` table is explicit: "ID-based resolution. UNITID is stable and authoritative. No resolution needed — use UNITID as-is." That guidance applies verbatim here. `institution_name` rides along for human-readability and is **not** used as a join key, anywhere, ever — it carries the documented multi-campus collision pattern (10 INSTNM strings map to multiple UNITIDs in College Scorecard) and is unsuitable as an identity.

---

## 2. UNITID Overlap Statistics

Cross-source UNITID overlap calibrations from `governance/domain-context.md` (EADA section, finalized 2026-04-30) and `governance/eda/full-pipeline-eada-raw-eda.md`:

| Cross-source pair | Overlap | Calibration target |
|-------------------|--------:|---------------------|
| `bronze.eada` ∩ `bronze.college_scorecard_institution` (UNITID) | **74.5% (1,519 / 2,040)** | Calibrates **BSE-EAD-009** (`fte_source_available ≥ 95%`) — threshold marked EDA-promoted; current observation is **lower** than the spec's a-priori 95%, meaning either (a) the threshold drops to ~75%, or (b) the per-FTE derivation switches to EADA's in-file `EFTotalCount`. **Open architectural question** flagged in domain-context.md (2026-04-30). |
| `bronze.eada` ∩ `raw.ipeds_finance` (UNITID) | **DEFERRED** — `raw.ipeds_finance` not yet built (`docs/specs/raw-ingest-ipeds-finance.md` is upstream). | Will be measured at the Silver `base.eada` LEFT JOIN step (Zone 2.2 of the full-pipeline spec). |
| `bronze.eada` ∩ `consumable.career_outcomes` (UNITID) | **DEFERRED** — `consumable.career_outcomes` is the FULL OUTER JOIN sink (Zone 3 / Aura). | Will be measured by **CON-AUR-020** (every aura UNITID exists in `career_outcomes.unitid` or is documented drift) and **CON-AUR-021** (≥90% reverse coverage). Both are EDA-calibrated, not entity-resolution gates. |

### What the 521-row gap is, and what it isn't

The 521 EADA institutions absent from `bronze.college_scorecard_institution` are **predominantly 2-year colleges**. EADA reports any Title IV institution that sponsors an athletic program, including community colleges; College Scorecard's bachelor's-program file (`bronze.college_scorecard_institution` / Field of Study) excludes institutions that do not award bachelor's degrees. The 25.5% gap is therefore **a coverage characteristic of the two source populations**, not a UNITID-resolution failure.

Consequence for this review: there is **nothing to resolve**. UNITID is the same stable IPEDS-issued identifier across both files for every institution that exists in both populations; for institutions in only one population, no resolution would conjure a row that does not exist on the other side. Resolution is the wrong tool — coverage logging at Silver/Gold is the right tool.

---

## 3. Lifecycle Events

| Event | Detectability in raw.eada | Handling |
|-------|---------------------------|----------|
| Institution closure | Not detectable in a single annual snapshot. Tracked only across refreshes. | Out of scope for Bronze. Future cross-vintage diff. |
| Institution name change | `institution_name` may drift across years for the same `unitid`. | UNITID is the canonical key — name drift is harmless. |
| UNITID merger / re-issue | Rare (IPEDS does not re-issue retired UNITIDs). | Not observed; no handling needed today. |
| Athletic program discontinuation | UNITID disappears from a future EADA snapshot. | Tracked at refresh time, not at resolution time. |

No lifecycle events are processed at this zone.

---

## 4. Confidence

Match confidence is binary and trivially 1.0 for every row: the source ships UNITID as a typed integer that is the canonical IPEDS-issued ID. There are no fuzzy matches, no flagged-for-review rows, no <0.7 confidence cases. Resolution statistics are degenerate:

| Metric | Value |
|--------|------:|
| Total entities (UNITIDs) processed | 2,040 |
| Exact-ID matches (confidence 1.0) | 2,040 (100%) |
| Fuzzy / corroborated matches | 0 |
| Flagged for review | 0 |
| Lifecycle events handled | 0 |

---

## 5. Is an entity registry warranted?

**No.** Same reasoning as the Anthropic Economic Index ER review (2026-04-16):

1. UNITID is already a federally governed canonical ID — there is no second-source ID to reconcile against at the Bronze zone.
2. The cross-source pattern is `bronze.eada.unitid = bronze.college_scorecard_institution.unitid = raw.ipeds_finance.unitid = consumable.career_outcomes.unitid` — a deterministic equi-join, not an alias resolution problem.
3. Confidence scoring would write `1.0` for every row.
4. No lifecycle events to track in a single snapshot.
5. The CDE registry / data contracts already cover UNITID as a shared cross-source CDE (institution identifier). That is the correct locus for institution-identity governance, not a per-source registry.

`governance/entity-registry.json` is not modified by this review.

---

## 6. Forward-Looking Notes for Silver / Gold

The full-pipeline-eada spec carries the institution identity through three downstream joins. All three are deterministic equi-joins on `unitid`. **None of them invoke fuzzy matching, name resolution, or alias reconciliation, and none of them should.**

| Zone | Join | Notes for downstream agents |
|------|------|-----------------------------|
| Silver — `base.eada` | `raw.eada` LEFT JOIN `base.ipeds_finance` ON `unitid` (to attach `total_fte_enrollment`) | Spec §Zone 2.2.2. Schools without an IPEDS Finance row get `NULL` FTE and `NULL` per-FTE derivations; flagged via `fte_source_available BOOLEAN`. **This is correct behavior.** No name-fallback, no fuzzy retry. The 521-school 2-year-college gap surfaces here; chaos manifest must include a forced UNITID type-mismatch test against BSE-EAD-009 (spec §Zone 2.4 already requires this). |
| Gold — `consumable.institution_aura` | `base.ipeds_finance` **FULL OUTER JOIN** `base.eada` ON `unitid`, with `COALESCE(f.unitid, e.unitid) AS unitid` | Spec §Zone 3. **Critical:** the join condition is UNITID and only UNITID. The `has_ipeds_finance` and `has_eada` boolean flags are computed from the join result (`f.unitid IS NOT NULL` / `e.unitid IS NOT NULL`); they explicitly model the asymmetric-coverage case rather than papering over it with a name-similarity fallback. **Do not introduce a name-based fallback.** It would invent rows that should not exist (multi-campus systems share `institution_name` but represent distinct UNITIDs — see domain-context.md §Entity Types: 10 INSTNM-to-multiple-UNITID cases in College Scorecard alone). |
| Gold — coverage assertions | `consumable.institution_aura.unitid` ↔ `consumable.career_outcomes.unitid` | Enforced by CON-AUR-020 / CON-AUR-021. These are **coverage** checks against an EDA-calibrated threshold, not **resolution** checks. Failures should be triaged as data-coverage gaps (e.g., new community-college cohort), never as ER bugs. |

### One-line guarantee

> Across `bronze.eada → base.eada → consumable.institution_aura → consumable.career_outcomes`, the institution-identity contract is **exact-match on UNITID, with no aliasing**. Any future agent (Silver, Gold, or DQ) that proposes a name-similarity fallback should be rejected on the grounds that UNITID is already authoritative and `institution_name` is documented as ambiguous (multi-campus collisions).

---

## 7. Recommendations

| # | Recommendation | Priority | Owner |
|---|----------------|---------:|:------|
| 1 | **Do not build a per-source entity registry for EADA.** UNITID is federally canonical. | — | @entity-resolver (closed) |
| 2 | At Silver `base.eada` build, log the actual `fte_source_available` rate against BSE-EAD-009's 95% threshold. If the observed rate is closer to 74.5% than 95%, escalate the open architectural question (LEFT JOIN to IPEDS Finance vs. in-file `EFTotalCount`) before base ships. | P1 | @silver-transformer |
| 3 | At Gold `consumable.institution_aura` build, ensure `COALESCE(f.unitid, e.unitid)` is the only identity expression in play and there is no name-similarity fallback anywhere in the join graph. | P1 | @gold-transformer |
| 4 | At each annual EADA refresh, log adds/drops to the UNITID set vs. the previous vintage to surface institution closures and program discontinuations. No registry needed; a refresh-time diff suffices. | P2 / operational | @data-analyst at next vintage |

---

## 8. Audit Trail

- **Files read:**
  - `docs/specs/full-pipeline-eada.md` (§§4, Zone 1, Zone 2, Zone 3, DQ rules)
  - `governance/domain-context.md` (EADA section finalized 2026-04-30; Entity Types; Canonical Concept Map)
  - `governance/entity-resolution/raw-anthropic-economic-index-entity-resolution.md` (precedent for "no registry warranted")
- **Empirical claims sourced from:**
  - 74.5% UNITID overlap (1,519 / 2,040): `governance/domain-context.md` EADA section + `governance/eda/full-pipeline-eada-raw-eda.md`
  - 521-row gap predominantly 2-year colleges: `governance/domain-context.md` EADA section
  - Multi-campus INSTNM collision pattern (10 cases): `governance/domain-context.md` Entity Types table
- **Decisions logged:** Verdict NOT APPLICABLE. No registry created. No lifecycle events tracked. Forward-looking notes pinned for @silver-transformer and @gold-transformer.
- **Timestamp:** 2026-04-30
