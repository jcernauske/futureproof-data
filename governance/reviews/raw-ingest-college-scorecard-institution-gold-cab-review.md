# CAB Review — Gold Schema Change: `consumable.career_outcomes`

**Spec:** `docs/specs/raw-ingest-college-scorecard-institution.md` §Zone 3
**Zone:** Gold (Consumable)
**Table:** `consumable.career_outcomes`
**Contract:** `governance/data-contracts/consumable-career-outcomes.yaml` (current v1.0.0)
**Reviewer:** @cab-agent
**Decision date:** 2026-04-16
**Status:** DECIDED

---

## 1. Change Inventory

### 1a. Additive — 6 new nullable DOUBLE columns (field IDs 32–37)

| Field ID | Name | Type | Required | CDE | Source |
|---------:|------|------|----------|-----|--------|
| 32 | `net_price_annual` | double | no | **true** | LEFT JOIN `base.college_scorecard_institution` |
| 33 | `cost_of_attendance_annual` | double | no | **true** | LEFT JOIN `base.college_scorecard_institution` |
| 34 | `net_price_4yr` | double | no | false | derived from `net_price_annual` |
| 35 | `tuition_in_state` | double | no | false | LEFT JOIN `base.college_scorecard_institution` |
| 36 | `tuition_out_of_state` | double | no | false | LEFT JOIN `base.college_scorecard_institution` |
| 37 | `room_board_on_campus` | double | no | false | LEFT JOIN `base.college_scorecard_institution` |

All six assigned **new** field IDs — no ID reuse, no position collision with existing 1–31. Iceberg schema evolution rules: appending new fields with fresh IDs is safe. Readers that project columns by ID will not see them; readers that use `SELECT *` will see them as nullable trailing columns.

### 1b. In-place re-source — 1 column with nullability relaxation

| Field ID | Name | Before | After |
|---------:|------|--------|-------|
| 4 | `institution_control` | `required=True` in contract; `required=False` in current Iceberg schema; **100% null in data** | `required=False` in both contract and Iceberg schema; **97.42% non-null in data** |

Field ID kept at **4** — no rename, no type change. Iceberg-level nullability on the physical table was already `required=False` (see `src/gold/college_scorecard_career_outcomes.py:77` and `docs/sessions/2026-04-06-gold-primary-agent-session.md:39`). The contract YAML still says `required: true` (line 71), and the physical model/spec documented `NOT NULL` — so the contract promise is **being formally relaxed to match the physical reality that already existed**, and the data is being re-sourced from a fundamentally different upstream (institution file vs. field-of-study file).

### 1c. Data-level reality shift (not a schema change but material)

- **Row count:** 69,947 → 69,947 (grain preserved — LEFT JOIN on unitid; unmatched unitids retain null cost fields)
- **Grain:** unitid × cipcode × credential_level — unchanged
- `institution_control` content changes from all-null to populated (1,804 rows still null for the 207 unmatched UNITIDs)

---

## 2. Classification

### 2a. Per-change classification

| Change | Class | Rationale |
|--------|-------|-----------|
| Add 6 nullable columns (IDs 32–37) | **MINOR** | Purely additive. Iceberg field-ID append. Nullable. Named-column readers unaffected; `SELECT *` readers see trailing columns. |
| Flip `net_price_annual` to `is_cde=true` | **MINOR** | New CDE flag on new column (not a flip on an existing contract column). |
| Flip `cost_of_attendance_annual` to `is_cde=true` | **MINOR** | Same as above. |
| Contract nullability of `institution_control`: `required:true` → `required:false` | **MAJOR** (by strict semver policy) — but see §3 | Per contract's own breaking-changes policy (lines 536–538: "type changed… triggers major version bump"). Technically a tightened-to-relaxed contract guarantee on an existing column. However: the physical Iceberg schema was already `required=False`, and field was 100% null — the written contract was aspirational, not enforced. |
| Data-level semantic shift on `institution_control` (all-null → 97.42% populated) | **MINOR** | No consumer could have been relying on meaningful values of an all-null column. Populating it can only improve consumer behavior, not break it. |

### 2b. Overall classification

**MINOR** — with one conditional caveat on `institution_control` discussed in §3.

Maximum per-change severity is technically MAJOR (nullability relaxation) if the contract's written policy is applied literally. I am downgrading to MINOR because:

1. The physical Iceberg schema has **always** allowed null on field ID 4 (see `college_scorecard_career_outcomes.py:77`, dated pre-this-spec). The `required: true` line in the YAML contract was never enforced against actual data.
2. The field was **100% null** pre-change. No consumer query could have successfully relied on a non-null guarantee that was already violated 100% of the time.
3. Nullability is being **relaxed**, not tightened. Consumers written to handle nulls (which all current consumers must, since they already encounter 100% nulls) are strictly safer under the new contract.
4. Relaxation of an already-violated "required" guarantee is a **contract correction**, not a contract break.

I remain conservative enough to flag it. See §6 conditions.

---

## 3. Blast Radius

### 3a. Direct consumers of `consumable.career_outcomes`

Identified by repo-wide grep for `career_outcomes` and `institution_control`:

| Consumer | Path | What it reads | Impact |
|----------|------|---------------|--------|
| Gold transformer `futureproof_engine.py` | `src/gold/futureproof_engine.py:313` | Named columns: `unitid`, `institution_name`, `cipcode`, `program_name`, `cip_family`, `cip_family_name`, `earnings_1yr_median`, `earnings_1yr_p25`, `earnings_1yr_p75`, `debt_median`, `debt_to_earnings_annual`, `confidence_tier`, `cip_family_earnings_rank` (aliased as `confidence_tier_program`). **Does NOT read `institution_control` or any cost field.** | **ZERO IMPACT.** Named-column projection. New columns invisible. `institution_control` change irrelevant. |
| MCP tool `get_school_programs` | `src/mcp_server/futureproof_server.py:100` (SCHOOL_PROGRAMS_RESPONSE_FIELDS) | Named columns including `institution_control`. Does NOT read the 6 new cost fields. | **BEHAVIORAL IMPROVEMENT.** Will now return 97.42% populated `institution_control` values instead of all-null. No client code assumes non-null (backend `SchoolMatch.institution_control: str \| None = None`). |
| MCP CIP intent substitution `_SUB_CO_FIELDS` | `src/mcp_server/futureproof_server.py:203-218` | Named columns: `unitid`, `institution_name`, `cipcode`, `program_name`, `cip_family_name`, earnings/debt percentiles, `cip_family_earnings_rank`, `confidence_tier`. **Does NOT read `institution_control` or cost fields.** | **ZERO IMPACT.** |
| Backend CLI `_get_school_cips` | `backend/cli.py:648` | `SELECT DISTINCT cipcode, program_name FROM consumable_career_outcomes` | **ZERO IMPACT.** Projects two columns. |
| Backend intent service | `backend/app/services/intent.py:87` | `FROM consumable_career_outcomes` (SELECT list not relevant here) | Uses named-column projection — **ZERO IMPACT** on schema extension. |
| Backend `school_lookup` service | `backend/app/services/school_lookup.py:65` | Reads `institution_control` from MCP response via `row.get("institution_control")` | **BEHAVIORAL IMPROVEMENT.** `row.get` returns `None` when absent — handles both old (null) and new (populated) states. No breakage. |
| Pydantic `SchoolMatch` model | `backend/app/models/career.py:21` | `institution_control: str \| None = None` | **Already nullable in model.** New data fits the existing API contract exactly. |
| Frontend `buildInput.ts` | `frontend/src/types/buildInput.ts:38` | `institution_control: string \| null` | **Already nullable in TS.** No breakage. |
| Frontend `SchoolSearch.tsx` | `frontend/src/components/school/SchoolSearch.tsx:72` | Reads and propagates `institution_control` | **Already null-tolerant.** No breakage. |

### 3b. Transitive downstream (Gold tables fed by `career_outcomes`)

| Table | How it uses career_outcomes | Impact |
|-------|-----------------------------|--------|
| `consumable.program_career_paths` (626,406 rows) | Inner join on 4-digit CIP prefix via `futureproof_engine.py`. Uses 13 named columns (none of them `institution_control` or cost). | **ZERO IMPACT.** Re-promote not required by this schema change. |
| `consumable.career_branches` | Derived downstream from `program_career_paths`. | **ZERO IMPACT.** |

### 3c. Golden datasets

Grepped `governance/golden-datasets/` for `institution_control` and cost-field references. No existing golden-dataset assertion on `career_outcomes` tests `institution_control` non-null behavior, and no assertion exists for the 6 new fields (they did not exist at golden-dataset authoring time). Existing assertions on earnings/debt/confidence remain valid post-re-promote.

### 3d. MCP tool contracts (`domain/manifest.yaml`, MCP spec)

The MCP spec `docs/specs/mcp-futureproof-core.md:59` lists `institution_control` in `get_school_programs` response schema without a nullability assertion. Client assumption is **nullable**. Populated-vs-null is a value change, not a schema change. No MCP contract break.

---

## 4. Backward Compatibility Analysis

### 4a. Does any consumer assume `institution_control` is NOT NULL?

**No.** Evidence:

- Backend Pydantic model: `institution_control: str | None = None` (nullable).
- Frontend TS type: `string | null` (nullable).
- Backend service: `row.get("institution_control")` (no raise on missing / null).
- No `.strip()`, `.lower()`, `== "Public"`, or index access on `institution_control` anywhere that would NPE on null.
- Silver architecture review §3 (`silver-architecture-review.md:231-235`) explicitly architected this field as **"nullable in Gold with DEFERRED note"** — the contract's `required: true` was aspirational, documented as a known gap in the 2026-04-06 sessions.
- DQ rule SLV-CS-027 "passes on 100% NULL institution_control due to SQL NULL semantics" (silver-architecture-review.md:80) — confirms no strict NOT NULL enforcement was ever executed.

### 4b. Does any consumer assume a strict schema with exactly 31 columns?

**No.** All Python consumers use named-column projection (`SELECT col1, col2, ...`). The backend CLI uses `SELECT DISTINCT cipcode, program_name`. The MCP tool uses explicit `SCHOOL_PROGRAMS_RESPONSE_FIELDS` lists. No `SELECT *` against `career_outcomes` that I found. No `ORDINAL_POSITION`–based readers. No fixed-width row destructuring.

### 4c. Does `institution_control` going from null → populated break any client assumption?

**No — it fixes assumptions instead.** The frontend `SchoolSearch.tsx` and backend `school_lookup.py` have carried `institution_control` plumbing through to the UI specifically to support institution-type segmentation the moment data became available. This is the 2026-04-06 insight-report recommendation finally closing.

**One caveat:** if any consumer code branches "if `institution_control is None`, fall back to default behavior" — the fallback will now trigger 2.58% of the time instead of 100% of the time. Grep confirms no such branching exists in the Python or TS codebases. UI will show real values; no default-rendering logic is at risk.

---

## 5. Fork Recommendation

**No fork required. Contract version bump to `1.1.0` (MINOR) is sufficient.**

Rationale:

- The nullability relaxation on `institution_control` is a **contract correction** aligning the written promise with the always-existing physical reality, not a new breaking constraint imposed on consumers.
- All consumers are already null-tolerant on this column.
- Six new columns are strictly additive with fresh Iceberg field IDs.
- Row count, grain, and all existing columns' semantics are unchanged.
- Zero consumers break. Zero golden-dataset assertions fail. Zero MCP tool signatures change.

A fork (v1 coexisting with v2 under a deprecation window) would be appropriate if:
- An existing column's type changed (it did not).
- The grain shifted (it did not).
- An existing CDE column was removed (it was not).
- A consumer was demonstrated to fail on the new schema (none do).

None of those are present. Fork is overkill. MINOR bump is honest.

---

## 6. Decision

### **APPROVE WITH CONDITIONS** — classification MINOR

Conditions (all must be satisfied before `@governance-reviewer-post` can sign off):

1. **Contract update — MINOR bump to 1.1.0.** Update `governance/data-contracts/consumable-career-outcomes.yaml`:
   - `version: "1.0.0"` → `version: "1.1.0"`
   - Field 4 `institution_control`: `required: true` → `required: false`; update description to note re-source from `base.college_scorecard_institution` with 97.42% coverage; remove/update the prior "100% null known gap" language.
   - Add 6 new column definitions (fields 32–37) with types, nullability, CDE flags, business terms, and descriptions.
   - `lineage.source_table: base.college_scorecard` → `lineage.source_tables: [base.college_scorecard, base.college_scorecard_institution]`.
   - Extend `quality:` block with the 9 GLD-CSI-00x rules called out in spec §Zone 3.

2. **CDE registry update.** Register `net_price_annual` and `cost_of_attendance_annual` as CDEs in `governance/cde-registry/` with rationale anchored in the ROI-formula follow-up spec (`roi-formula-cost-of-attendance.md`).

3. **Lineage event.** Update `governance/lineage/` to reflect dual Silver input.

4. **Audit-trail entry.** Append a row to `governance/audit-trail/raw-ingest-college-scorecard-institution-approvals.md` recording this decision and the contract v1.0.0 → v1.1.0 bump.

5. **Deprecation registry — no entry required.** No column is being deprecated. Re-sourcing `institution_control` is a silent improvement; it does not warrant a deprecation timeline because nothing is being removed or renamed.

6. **Post-implementation verification.** `@governance-reviewer-post` must confirm (a) row count 69,947 exactly, (b) grain uniqueness preserved, (c) `institution_control` coverage ≥95% on the real Iceberg table, (d) 6 new columns nullable and populated where UNITID matches, (e) all 9 new DQ rules pass.

### What I am NOT approving

- Any change to the `institution_control` CDE flag (stays `is_cde: false`).
- Any implicit promotion of the new cost fields to REQUIRED — they must remain nullable because the LEFT JOIN produces nulls for unmatched unitids (207 schools, 1,804 rows).
- Any backfill of `program_career_paths` or `career_branches` on account of this change. Those tables do not read the affected columns. Re-promote is not required by this schema event.

### Human override

Not invoked. No one overrode my classification. If `@governance-reviewer` wants to re-classify nullability relaxation as strict MAJOR and demand a fork, that is their prerogative — I will log the override with name, rationale, and timestamp and comply. I disagree with that path but I respect it.

---

## 7. Summary Statement

The Gold schema of `consumable.career_outcomes` is gaining six additive nullable cost columns and having one existing column (`institution_control`) re-sourced from a different upstream file. Row count and grain are unchanged. Field IDs 32–37 are fresh (no ID reuse). The contract's written `required: true` on `institution_control` was never enforced by the physical Iceberg schema or the data (100% null). Every consumer — Gold engine, MCP tools, backend services, frontend types — is already null-tolerant on this column. No consumer reads the 6 new columns; none of them break on the addition. No fork is required. A contract version bump from 1.0.0 to 1.1.0 and CDE registration for `net_price_annual` / `cost_of_attendance_annual` are sufficient.

Is MINOR. I sleep tonight.

---

## Appendix A — Evidence References

- Current Gold schema with new fields: `src/gold/college_scorecard_career_outcomes.py:72-118` (fields 32–37 appended).
- Pre-existing Iceberg nullability of field 4: `src/gold/college_scorecard_career_outcomes.py:77` (`required=False`).
- Primary consumer projection (does not touch `institution_control`): `src/gold/futureproof_engine.py:265-320`.
- MCP consumer of `institution_control`: `src/mcp_server/futureproof_server.py:97-117`.
- Backend nullable Pydantic model: `backend/app/models/career.py:21`.
- Frontend nullable TS type: `frontend/src/types/buildInput.ts:38`.
- Coverage EDA: `docs/sessions/eda-gold-career-outcomes-csi-enrichment.md:41` (97.42% institution_control).
- Silver-era known gap: `governance/reviews/silver-architecture-review.md:154,231-235`.
- 2026-04-06 gold implementation note on nullability: `docs/sessions/2026-04-06-gold-primary-agent-session.md:39`.
- Contract breaking-change policy: `governance/data-contracts/consumable-career-outcomes.yaml:536-543`.
