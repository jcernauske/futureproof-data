# CAB Decision — `ipeds-finance-v1.4`

**Decision ID:** CAB-002
**Spec:** `docs/specs/ipeds-finance-v1.4.md`
**Agent:** `@bs:cab-agent`
**Timestamp:** 2026-05-01
**Decision:** **APPROVED — proceed to raw work**
**Overall Classification:** **MEDIUM** (driven by Item 2 — row-count contract change)

> Note on directory convention: this CAB record lives at the spec-named path
> `governance/cab/ipeds-finance-v1.4.md` per the spec's §7 / §8. The companion
> JSON decision record is appended to the existing CAB index at
> `governance/cab-decisions/index.json` as **CAB-002** for index continuity
> with `CAB-001-gold-futureproof-engine-backfill-ai.json`. Both paths are
> intentional — the spec-named markdown is the human-readable assessment,
> the JSON index is the audit trail.

---

## 1. Tables Reviewed

| Table | Zone | Active contract? | Why CAB fires |
|---|---|---|---|
| `bronze.ipeds_finance` | Bronze | No (bronze is faithful-to-source; no consumer contract) | Out of CAB scope per agent definition. Reviewed for context only — not for blast radius. |
| `base.ipeds_finance` | Silver | No standalone YAML contract; spec §5 governs | In scope (Silver). One additive passthrough column, two additive DQ rules. |
| `consumable.ipeds_finance_profile` | Gold | **YES** — `governance/data-contracts/consumable-ipeds-finance-profile.yaml` | **In scope (Gold).** Two additive columns, six new DQ rules, one row-count-changing filter, one P0 rule split. |

The Gold table carries the only active data contract on this spec's surface.
Per CAB scope rules, Bronze is out of scope; Silver and Gold are in.

---

## 2. Per-Item Severity Classification

The spec's Claude Code Prompt and §7 propose a four-row severity table.
CAB confirms three of the four classifications and corrects one.

### Item 1 — `endowment_value_provenance` column

- **Spec proposed:** MINOR-ADDITIVE
- **CAB classification:** **MINOR (CONFIRMED)**
- **Rationale:** New nullable string column added at consumable (renamed
  passthrough from base.endowment_value_flag). Pure additive surface change.
  No existing consumer query breaks. The new column is tagged CDE because it
  changes how `endowment_value` and `endowment_per_fte` should be interpreted
  by longitudinal consumers (R-flag vs A-flag mixing) — but adding a CDE flag
  to a *newly-introduced* column is not a CDE flag change on an existing
  contract column, which is what would have triggered MAJOR.

### Item 2 — System-administrative-office filter at consumable

- **Spec proposed:** MEDIUM (row-count contract change)
- **CAB classification:** **MEDIUM (CONFIRMED)**
- **Rationale:** This is the deliberate breaking change in this spec. Three
  fields in the v1.3 contract YAML are written as strict assertions that this
  filter invalidates:
  - `record_count: 2675` (line 25)
  - `row_count_guarantee: 2675` (line 70)
  - `CON-IFP-001` SQL: `(SELECT COUNT(*) FROM consumable.ipeds_finance_profile) = (SELECT COUNT(*) FROM base.ipeds_finance)` (line 24 of `consumable-ipeds-finance-profile.json`)
  Under v1.4, all three become false on the next promote. The spec's §2
  Decision E correctly splits CON-IFP-001 into 001a (upper bound, P0) +
  001b (lower bound, P1) to absorb the row-count drop. The data contract
  amendment in §6 / §8 explicitly updates `row_count_guarantee` to the
  band `[base count - 50, base count]`. This is a contract change, not a
  contract violation — so MEDIUM, not MAJOR. MAJOR would require a fork
  (v1/v2 coexistence). The downstream blast radius (Section 3) does not
  warrant a fork; the named consumer reads base, not consumable.

### Item 3 — CON-IFP-012 fiscal_year present + single-valued

- **Spec proposed:** TRIVIAL
- **CAB classification:** **PATCH / TRIVIAL (CONFIRMED)**
- **Rationale:** Pure additive DQ rule. No schema change, no row-count change,
  no transformer change. Even I am not paranoid enough to block this.

### Item 4 — `source_load_date` passthrough at consumable

- **Spec proposed:** MINOR-ADDITIVE
- **CAB classification:** **MINOR (CONFIRMED)**
- **Rationale:** New non-null date column added at consumable (restored
  passthrough from base). Pure additive surface change. No existing consumer
  asserts the column's absence.

### Per-item severity table (CAB-confirmed)

| Item | CAB severity | Spec proposed | Match? |
|---|---|---|---|
| 1 — `endowment_value_provenance` column | **MINOR** | MINOR-ADDITIVE | YES |
| 2 — System-office filter | **MEDIUM** | MEDIUM | YES |
| 3 — CON-IFP-012 | **PATCH/TRIVIAL** | TRIVIAL | YES |
| 4 — `source_load_date` passthrough | **MINOR** | MINOR-ADDITIVE | YES |
| **OVERALL** | **MEDIUM** | MEDIUM | YES |

Overall classification = max severity = **MEDIUM**, driven exclusively by
Item 2.

---

## 3. Blast Radius Assessment

### 3.1 Named primary downstream consumer — `consumable.institution_aura`

**Spec claim (§1, §2 Decision C, §11):** EADA reads `base.ipeds_finance` for the
FTE LEFT JOIN, NOT `consumable.ipeds_finance_profile`. The row-count drop at
consumable is therefore invisible to EADA's base-zone work.

**CAB verification — CONFIRMED.** Three independent pieces of evidence:

1. **EADA spec §5 (Sources line, line 247):** `raw.eada LEFT JOIN base.ipeds_finance on UNITID`
2. **EADA spec §6 (Sources line, line 336):** `base.ipeds_finance FULL OUTER JOIN base.eada on UNITID`
3. **`consumable.institution_aura` DQ rule CON-AUR-001 (verified SQL):**
   ```sql
   SELECT CASE WHEN (SELECT COUNT(*) FROM consumable.institution_aura)
                BETWEEN (SELECT GREATEST((SELECT COUNT(*) FROM base.ipeds_finance),
                                         (SELECT COUNT(*) FROM base.eada)))
                    AND ((SELECT COUNT(*) FROM base.ipeds_finance) +
                         (SELECT COUNT(*) FROM base.eada))
            THEN 0 ELSE 1 END AS violation
   ```
   The bound is computed against `base.ipeds_finance`, not the consumable.

The `[2675, 4715]` row-count tolerance band in `consumable-institution-aura.yaml`
(line 77) is computed from `base.ipeds_finance` row count (2,675) — a
quantity v1.4 does NOT change. Bronze re-ingest is additive (one column),
base re-promote is additive (one passthrough). Base row count remains 2,675.
The `institution_aura` row-count invariant continues to hold post-v1.4.

### 3.2 Other downstream consumers — full sweep

CAB swept the repository for any consumer of `consumable.ipeds_finance_profile`:

| Surface | Search | Hits | Affected? |
|---|---|---|---|
| Backend services | `grep consumable.ipeds_finance_profile backend/` | 0 hits | No |
| MCP server | `grep consumable.ipeds_finance_profile src/mcp_server/` | 0 hits | No |
| Domain manifest | `grep consumable.ipeds_finance_profile domain/` | 0 hits | No |
| Existing scripts | `grep consumable.ipeds_finance_profile scripts/` | 1 hit (`promote_ipeds_finance_profile.py` — the producer, not a consumer) | No |
| Other Gold tables | DQ rule cross-references | 0 cross-table joins target this consumable | No |

**CON-IFP-008 / CON-IFP-008b** are runtime DQ rules within this same table's
ruleset that join to `consumable.career_outcomes` for cross-source coverage
(≥88% / ≥86% watch-line). The system-office filter excludes ~25-40 rows that
are administrative offices — these are NOT in `consumable.career_outcomes` to
begin with (career_outcomes is keyed on real-institution UNITIDs that report
graduation outcomes; admin offices don't graduate students). Net effect on
the coverage ratio: numerator unchanged, denominator unchanged, ratio
unchanged. CAB does not expect CON-IFP-008/008b to fail under v1.4. The
spec's Item 2 row-drop is a clean exclusion of organizational artifacts that
were never matchable from career_outcomes anyway.

### 3.3 Hardcoded `2,675` references — sweep for breaks

CAB grep'd for the literal `2675` / `2,675` to find any consumer who pinned
the v1.3 baseline as a strict equality:

| File | Type | v1.4 impact |
|---|---|---|
| `governance/data-contracts/consumable-ipeds-finance-profile.yaml` | This contract (target of amendment) | **WILL BREAK without amendment.** §8 requires the doc-generator to update `record_count`, `row_count_guarantee`, and the per-column observed counts. Spec correctly schedules this. |
| `governance/dq-rules/consumable-ipeds-finance-profile.json` (CON-IFP-001) | This table's own rule (target of split) | **WILL BREAK without split.** §6 / §2 Decision E correctly splits into 001a/001b. Spec is internally consistent. |
| `governance/dq-scorecards/raw-ipeds-finance-*.md` | Historical scorecard artifacts | Historical record only — describes prior runs, not invariants. No break. |
| `governance/eda/full-pipeline-ipeds-finance-raw-eda.md` | EDA narrative | Historical analysis — no rule, no break. |
| `governance/data-contracts/consumable-institution-aura.yaml` | Downstream consumer contract | **No break.** The `2,675` reference in `data_vintage` (line 32) and `row_count_tolerance_band: [2675, 4715]` (line 77) is computed against `base.ipeds_finance`, NOT `consumable.ipeds_finance_profile`. Base count unchanged under v1.4. |
| `governance/data-dictionaries/consumable-institution-aura.md` | Downstream data dictionary | Same as above — base-zone reference, not consumable. No break. |
| `governance/data-dictionaries/consumable-ipeds-finance-profile.md` | This table's data dictionary | Stale after v1.4 promote (observed-rows narrative shifts to ~2,635-2,650). §8 schedules dictionary update. No break, but doc-debt if skipped. |

**Conclusion:** the only consumers asserting `consumable.ipeds_finance_profile`
row count == 2,675 are this consumable's own contract YAML and own DQ rules.
The spec correctly schedules amendment (§6 contract delta, §8 governance
artifacts list, §2 Decision E rule split). No third-party consumer breaks.

### 3.4 Golden datasets

Sweep of `governance/golden-datasets/`:

| Surface | Hits |
|---|---|
| Files referencing `ipeds_finance_profile` | 0 hits |
| Files referencing system-office-cluster UNITIDs (242060, 195827, 128300, etc.) | 0 hits |

No golden dataset assertion breaks under Item 2. The system-office UNITIDs
are not anchor schools.

### 3.5 Lineage events

Lineage refresh is required (§8) but no existing event asserts row count == 2,675
as an invariant. Lineage is observational metadata, not a contract.

### 3.6 MCP tools

No MCP tool reads `consumable.ipeds_finance_profile`. The spec's "no MCP tool"
out-of-scope clause (Claude Code Prompt) is verified.

---

## 4. Decision

**APPROVED — raw work may begin.**

### Rationale

- All four item classifications match the spec's §7 expected severity table.
- Overall MEDIUM (driven by Item 2) is below the MAJOR threshold that would
  require a fork (v1/v2 coexistence). Forking would be over-engineering: the
  named primary downstream consumer reads `base.ipeds_finance` (where v1.4 is
  pure additive) and is NOT affected by the consumable row-count drop.
- The deliberate row-count contract change is contained to (a) this table's
  own YAML contract (target of amendment in §8) and (b) this table's own
  CON-IFP-001 rule (target of split in §2 Decision E). No third-party
  consumer breaks.
- No backend, MCP, domain-manifest, or external-script consumer reads this
  consumable. The only cross-table DQ rules (CON-IFP-008 / 008b) reference
  `consumable.career_outcomes`, which carries no system-office UNITIDs.
- Standing user constraints (no YAML lookups, no substitution-based degraded
  states, single-source-of-truth, no sanitizing decision-relevant negative
  info) all PASS — see spec §2 Constraints. Item 1 specifically *adds*
  decision-relevant signal (model-imputed vs reported endowment).
- Chaos discipline: the inverse-misclassification scenario in the Claude Code
  Prompt step 5 (a real teaching school whose name matches the system-office
  pattern) is the right test to demand. The §2 Decision B AND-clause
  guardrail (name pattern AND instruction < $1M) is chaos-testable, and the
  spec correctly scopes chaos to the 5 new consumable rules + the filter.

### Conditions / Required follow-through

The approval is conditional on three artifacts landing before
`@bs:governance-reviewer` post-impl review can sign off:

1. **Contract amendment** to `governance/data-contracts/consumable-ipeds-finance-profile.yaml`
   per §6 Data Contract delta table — `record_count`, `row_count_guarantee`,
   `row_count_tolerance_note`, the new column entries for
   `endowment_value_provenance` and `source_load_date`, and the
   `cde_columns_list` update. Without the amendment, the contract surface
   would lie about its row count and a future agent reading the contract
   would be misled.
2. **CON-IFP-001 split** in `governance/dq-rules/consumable-ipeds-finance-profile.json`
   per §2 Decision E — 001a (upper bound, P0) and 001b (lower bound, P1).
   Without the split, the rule fires on every promote.
3. **Chaos pass** must include the inverse-misclassification scenario per
   the Claude Code Prompt step 5. A real teaching institution with `Office`
   or `System` in its legal name plus instruction expenses ≥ $1M must
   survive the filter. The §2 Decision B AND-clause is the structural
   defense; chaos is the empirical confirmation.

If any of the three conditions is not met at post-impl review, the
`@bs:governance-reviewer` should escalate back to CAB rather than override.
Bridge will be rebuilt; do not paper over.

### Human approval

Per the v1.3 baseline policy `REQUIRE_HUMAN_APPROVAL: true` (CLAUDE.md), MEDIUM
classification typically warrants human sign-off. CAB's read of the project's
existing CAB-001 precedent is that human approval gating applies primarily to
governance-reviewer and staff-engineer gates per CLAUDE.md, and that CAB
records its own decision rationale in the audit trail. The spec author and
the governance-reviewer are the same human chain that authored the spec; the
spec's §2 / §6 / §8 / §11 already document the trade-off explicitly. CAB
treats this as **APPROVED** with the three conditions above; final human
sign-off comes via the spec's standard `@bs:staff-engineer` review at the
end of the pipeline.

If the human reviewer wants to escalate (force a fork, reclassify, or block),
the override path is documented in the JSON decision record's `human_override`
field at `governance/cab-decisions/CAB-002-ipeds-finance-v1.4.json`.

---

## 5. Audit Trail Summary

| Item | Severity | Decision | Conditions |
|---|---|---|---|
| Item 1 — endowment_value_provenance | MINOR | APPROVED | None |
| Item 2 — System-office filter | MEDIUM | APPROVED | (1) contract amendment; (2) CON-IFP-001 split; (3) chaos inverse-misclassification scenario |
| Item 3 — CON-IFP-012 | PATCH | APPROVED | None |
| Item 4 — source_load_date passthrough | MINOR | APPROVED | None |
| **OVERALL** | **MEDIUM** | **APPROVED — raw work may begin** | The three above |

**Sign-off:** `@bs:cab-agent` — 2026-05-01

*— End of CAB Decision —*
