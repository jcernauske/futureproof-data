# Audit Trail: doc-generator — raw.eada (full-pipeline-eada)

**Agent:** @doc-generator
**Date:** 2026-04-30
**Spec:** [docs/specs/full-pipeline-eada.md](../../docs/specs/full-pipeline-eada.md)
**Scope:** Bronze-zone only — data dictionary, conceptual / logical / physical models, glossary update for the EADA-sourced term.

---

## Artifacts Produced

| Artifact | Path |
|----------|------|
| Conceptual model | `governance/models/raw-eada-conceptual.md` |
| Logical model | `governance/models/raw-eada-logical.md` |
| Physical model | `governance/models/raw-eada-physical.md` |
| Data dictionary | `governance/data-dictionaries/raw-eada.md` |
| Business glossary update | `governance/business-glossary.json` (added 1 proposed term: `BT-EAD-ATHLETIC-SUBSIDY-RATIO`) |
| Audit trail (this file) | `governance/audit-trail/2026-04-30-doc-generator-raw-eada.md` |

## Artifacts Deferred (out of scope per task brief)

- Silver / Gold models (`base-eada-*`, `consumable-institution-aura-*`).
- Consumable data contract (`governance/data-contracts/consumable-institution-aura.yaml`) — Gold-only per spec §8.
- Glossary terms `BT-AUR-AURA-SCORE` and `BT-AUR-COVERAGE-TIER` — deferred to gold-zone work (per task brief).
- Bronze-zone data contract — not produced. Sibling convention (`governance/data-contracts/`) has no `raw-*.yaml` or `bronze-*.yaml` files; the spec only mandates the Gold contract at §8.

---

## Decisions and Rationale

### 1. Iceberg namespace `bronze.eada` vs. logical name `raw.eada`

The spec declares `raw.eada` as the logical name (§4 heading). The DQ rules file (`governance/dq-rules/raw-eada.json`) writes SQL against `bronze.eada` directly, matching the catalog convention used by `bronze.college_scorecard_institution`, `bronze.bls_ooh`, etc. **Decision:** call out both names in the data dictionary header and physical model — they refer to the same physical table. Downstream readers should use `bronze.eada` in SQL.

### 2. Data dictionary file location

Sibling convention is `governance/data-dictionaries/<table>.md` (e.g., `raw-college-scorecard-institution.md`, `silver-base-college-scorecard-institution.md`). **Decision:** use `governance/data-dictionaries/raw-eada.md`, matching the §8 amendment that drops the verb "ingest" from spec-renamed artifacts.

### 3. CDE flagging at Bronze

The spec §6 Data Contract names CDE candidates at the Gold zone (`aura_score`, `marketing_ratio`, `endowment_per_fte`, `athletic_subsidy_ratio`, plus `athletic_spend_per_fte` per the governance-reviewer's CHANGES REQUESTED issue #2). Bronze does not have a contract, so I propagated the flag upstream to the columns that **feed** those Gold CDEs:
- `unitid` — flagged CDE (universal join key into every IPEDS-keyed downstream table; same convention as `bronze.college_scorecard_institution.unitid`).
- `total_athletic_expenses` — flagged CDE (drives `athletic_spend_per_fte`, the EADA-side aura input, and is one of two inputs to `athletic_subsidy_ratio`).
- `total_athletic_revenue` — flagged CDE (the other input to `athletic_subsidy_ratio`).
- `recruiting_expenses` — flagged CDE (drives `recruiting_per_fte`; carried through Silver as a context column).

The other 6 columns (`institution_name`, `reporting_year`, 4 provenance fields) are **not** flagged CDE — they are display, vintage, or provenance metadata, none of which feed the downstream score.

This is a tagging proposal; final CDE designation is @bs:cde-tagger's call.

### 4. Glossary term ID for the proposed `BT-EAD-ATHLETIC-SUBSIDY-RATIO`

The spec §6 proposes alphabetic IDs (`BT-EAD-*`, `BT-AUR-*`). The existing `governance/business-glossary.json` uses **numeric** IDs (`BT-001`..`BT-118`). **Decision:** insert the term using the spec-proposed alphabetic form (`BT-EAD-ATHLETIC-SUBSIDY-RATIO`) with `approval_status: "proposed"` and a `steward_notes` field flagging the convention mismatch. The steward may re-key to `BT-119` if they prefer numeric. This avoids pre-empting the steward's call while still landing the term so downstream models can reference it.

Per the task brief: only the EADA-sourced term (`BT-EAD-ATHLETIC-SUBSIDY-RATIO`) is added. `BT-AUR-AURA-SCORE` and `BT-AUR-COVERAGE-TIER` are deferred to gold-zone work.

### 5. Forward-pointer for the Bronze lineage event

The task brief stated "lineage-tracker just produced a freshly-written file under `governance/lineage/full-pipeline-eada-{timestamp}.json`." At the time of this run, no such file is on disk (most recent lineage entries are dated 2026-04-17 or earlier). **Decision:** cite the path `governance/lineage/full-pipeline-eada-{timestamp}.json` as a forward pointer in the data dictionary and physical model. When the lineage event lands, the `{timestamp}` placeholder will resolve. If the lineage-tracker output ended up at a different path, the data dictionary's "Lineage" line is the only edit needed to retarget.

### 6. Bronze data contract decision

The task brief asked whether to produce a Bronze-zone contract. **Decision:** no Bronze contract. Sibling convention in `governance/data-contracts/` has no `raw-*.yaml` or `bronze-*.yaml` files — every existing contract is for Silver (`base-*.yaml`), Gold (`consumable-*.yaml`), or MCP (`mcp-*.yaml`). The spec §8 only mandates `governance/data-contracts/consumable-institution-aura.yaml`. Producing a Bronze contract would invent a convention not present elsewhere in the project.

### 7. Plain-English definitions — domain caveats

EDA observations were embedded directly into definitions where they materially affect consumer behavior — e.g., the `recruiting_expenses` definition explicitly calls out the 17.8% real-zero rate so a future reviewer doesn't add a "> 0" rule, and the `total_athletic_revenue` definition flags the revenue ≈ expense identity so the Silver `athletic_subsidy_ratio` does not surprise a consumer expecting non-trivial values. The "Caveats for Consumers" section consolidates all eight non-obvious behaviors in one place.

---

## Cross-References Verified

All linked governance artifacts exist on disk as of 2026-04-30:

- ✅ `docs/specs/full-pipeline-eada.md`
- ✅ `src/raw/eada_ingestor.py`
- ✅ `governance/eda/full-pipeline-eada-raw-eda.md`
- ✅ `governance/dq-rules/raw-eada.json` (12 rules)
- ✅ `governance/dq-scorecards/raw-eada-20260501T040238Z.{json,md}` (12/12 PASS)
- ✅ `governance/chaos-reports/raw-eada-chaos.md`
- ✅ `governance/adversarial-audits/raw-eada-bronze-audit.md`
- ✅ `governance/pii-scans/raw-eada-pii-scan.md`
- ✅ `governance/entity-resolution/raw-eada-er-assessment.md`
- ✅ `governance/temporal-models/raw-eada-temporal-assessment.md`
- ✅ `governance/domain-context.md` (EADA Athletics Disclosure section)
- ⏳ `governance/lineage/full-pipeline-eada-{timestamp}.json` (forward pointer; produced by lineage-tracker)
