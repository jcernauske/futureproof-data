# Temporal Modeling Disposition: onet-experience-requirements

**Spec:** `docs/specs/onet-experience-requirements.md`
**Agent:** bs:temporal-modeler
**Date:** 2026-04-16
**Verdict:** NO TEMPORAL MODELING REQUIRED — treat as static annual snapshot
**Spec cross-reference:** §Agent Workflow Phase 2 step 12 (`bs:temporal-modeler` — SKIP justified)

---

## Rationale

The O*NET 30.2 "Education, Training, and Experience" file is an annual snapshot publication. Every row in `raw.onet_experience` describes the occupation-aggregate percent-frequency distribution as of a single data-collection wave — there is no intra-wave evolution to track. Nothing in the source data carries bitemporal semantics: `onet_soc_code`, `element_id`, `scale_id`, `category`, `data_value`, and sample-size / CI fields are all static attributes of a survey snapshot, and the lone `date` column records the publication/data-collection date (a provenance stamp), not a `valid_from` boundary for a versioned fact. The Silver aggregate `base.onet_experience_profiles` collapses these to BLS-SOC grain for a single point-in-time view; the Gold join onto `consumable.career_branches` adds four additive, non-versioned columns (`related_experience_years`, `related_experience_tier`, `source_experience_years`, `experience_delta_years`) that inherit the same snapshot semantics. There is no amendment/correction mechanism (O*NET ships a new version; it does not emit restatements of prior versions), no downstream requirement to answer "what did we believe about occupation X on date Y?", and no SCD behavior (tier changes, if any, manifest as Type-1 overwrites on version refresh, which is the explicit and approved behavior per the sibling O*NET spec pattern).

---

## Recommendation

**NO TEMPORAL MODELING REQUIRED — treat as static annual snapshot.**

Do not add `valid_from` / `valid_to` columns, do not maintain SCD Type-2 history, do not retain per-wave snapshots as long-lived Iceberg history. The Iceberg snapshot of the current active version is sufficient for any "what does the pipeline currently believe" query; older O*NET versions, if ever needed, are available as the original vendor ZIP archives (`data/raw/onet_cache/`), not as a live governance concern.

---

## Annual Refresh Strategy

When a new O*NET version ships (approx. annually):

1. **Bronze re-ingest** — `OnetExperienceIngestor` (8th subclass in `src/raw/onet_ingestor.py`) re-reads the new `db_XX_X_text.zip`, extracts `Education, Training, and Experience.txt`, and writes a fresh snapshot to `raw.onet_experience` via full-table replace (existing `OnetBaseIngestor` promote pattern).
2. **Silver re-promote** — `src/silver/onet_experience_transformer.py` re-computes weighted median, tier, and BLS-SOC aggregation against the new Bronze state; writes a fresh `base.onet_experience_profiles` via full-table replace.
3. **Gold re-join** — the `consumable.career_branches` Gold transformer re-executes the `LEFT JOIN` against the refreshed Silver profile; the additive experience columns update in place.
4. **No SCD / no bitemporal history retained** — prior version values are overwritten. Prior Iceberg snapshots exist for operational rollback but are not a governance-surfaced historical dimension. DQ rules and data-contract schema versions do not change on a data refresh (additive schema changes would require a separate spec).

This is identical to the refresh behavior already approved for every other O*NET Silver and Gold table in the pipeline.

---

## Cross-Reference: Sibling O*NET Table Treatment (Same Pattern)

Every existing O*NET spec applies the identical disposition, confirming this is the project-wide pattern for O*NET data:

| Sibling spec | Table(s) | Temporal-modeler disposition |
|--------------|----------|------------------------------|
| `docs/specs/silver-base-onet.md` | `base.onet_occupations`, `base.onet_work_profiles`, `base.onet_task_statements`, `base.onet_work_context` | SKIP — "Single-snapshot. Full table replace on O*NET release updates." (line 269) |
| `docs/specs/gold-onet-profiles.md` | `consumable.occupation_profiles`, `consumable.onet_work_profiles`, `consumable.career_transitions`, `consumable.career_branches` | SKIP — "Single-snapshot. Full table replace." (line 292) |
| `docs/specs/onet-experience-requirements.md` | `raw.onet_experience`, `base.onet_experience_profiles`, `consumable.career_branches` (+4 additive cols) | SKIP (this disposition) — "static annual snapshot, no temporal dimension" |

---

## Answers to the Three Posed Questions

1. **Does any field in `raw.onet_experience` track change-over-time for an occupation?** NO. The `date` column is a data-collection/publication provenance stamp on the snapshot, not a bitemporal `valid_from`. No field carries versioned-fact semantics.
2. **Should `base.onet_experience_profiles` be bitemporal to support annual O*NET version refreshes?** NO. Annual refresh is handled via full-table replace, consistent with every sibling O*NET Silver table. Retaining cross-version history would impose real governance cost (SCD Type-2 management, versioned DQ rules, consumer-facing "which version?" queries) against zero product-side demand — the career-branching UX reasons about current occupational reality, not the longitudinal drift of O*NET category distributions.
3. **Is there any SCD behavior needed at Gold?** NO. The four additive columns on `consumable.career_branches` (`related_experience_years`, `related_experience_tier`, `source_experience_years`, `experience_delta_years`) are Type-1 overwrite-on-refresh, inherited from the Silver snapshot semantics they join from.

---

## Trade-offs Considered

- **Retaining SCD Type-2 history on `base.onet_experience_profiles`**: rejected — no product demand, adds governance burden (versioned DQ rules, contract bumps, consumer disambiguation), inconsistent with sibling O*NET tables. Prior-version ZIP archives remain available if historical comparison is ever needed as a one-off analysis.
- **Tracking O*NET version as a non-bitemporal dimension column** (e.g., `onet_version = "30.2"` on every Silver row): deferred. Not in spec scope. Could be added later via a separate minor spec if version-provenance ever becomes a surfaced concern; does not require bitemporal machinery.
- **Adding `ingested_at` / `source_load_date` as pseudo-temporal columns**: already present in the Silver schema (`source_load_date`, `ingested_at` per §Silver Schema) as audit/provenance stamps. These satisfy any "when did the pipeline last refresh?" need without a bitemporal model.

---

## Audit Trail

- 2026-04-16 — Disposition authored by `bs:temporal-modeler` per spec §Agent Workflow Phase 2 step 12.
- Cross-verified against `docs/specs/silver-base-onet.md` line 269 and `docs/specs/gold-onet-profiles.md` line 292 — same NO-temporal disposition applied project-wide for O*NET.
- Cross-verified against spec §Source Data (annual snapshot publication) and §Silver Schema (no `valid_from`/`valid_to` columns requested).

— End of disposition —
