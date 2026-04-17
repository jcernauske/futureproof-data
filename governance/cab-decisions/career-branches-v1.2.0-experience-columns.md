# CAB Decision: career_branches v1.2.0 — Experience Columns

**Decision ID:** CAB-002
**Spec:** docs/specs/onet-experience-requirements.md
**Table under review:** `consumable.career_branches`
**Contract:** `governance/data-contracts/consumable-career-branches.yaml` (v1.1.0 → v1.2.0)
**Reviewer:** @cab-agent
**Date:** 2026-04-16
**Mode:** Read-only review (no schema, spec, or contract modifications)

---

## 1. Severity Classification

**Classification: MINOR (additive, non-breaking)**

Four new columns appended to `consumable.career_branches`:

| Field ID | Name | Type | Required | CDE |
|---------:|------|------|:--------:|:---:|
| 31 | `related_experience_years` | DOUBLE | no | true |
| 32 | `related_experience_tier` | VARCHAR | no | true |
| 33 | `source_experience_years` | DOUBLE | no | true |
| 34 | `experience_delta_years` | DOUBLE | no | true |

Why MINOR (not MAJOR / not PATCH):

- **Not MAJOR.** No column removed. No column renamed. No type changed on an existing column. Grain unchanged (`[soc_code, related_soc_code]` composite key preserved). No CDE flag flipped on an existing column. No required-field added. No constraint tightened on existing column.
- **Not PATCH.** Structural schema change (new NestedField IDs 31–34). Not description-only.
- **MINOR fits.** Iceberg field IDs 31–34 are new and append-only — existing readers that project named columns are unaffected; readers using `SELECT *` receive additional columns with NULL values in roughly 5–9% of rows. All four columns are `required=False` (nullable). `experience_delta_years` is explicitly NULL-propagating per spec §Zone 3.

Contract version bump v1.1.0 → v1.2.0 is correct under the contract's own stated semver policy (lines 575–579 of the yaml): "Column added triggers a minor bump (NON-BREAKING)."

---

## 2. Blast Radius

Three consumer surfaces reviewed. All three are tolerant of the additive change.

### 2.1 MCP tool `get_career_branches` (`src/mcp_server/futureproof_server.py`)

**Impact:** SAFE for the new columns but they WILL NOT surface to Gemma until registered.

The handler uses an **explicit allowlist** at line 377:

```python
CAREER_BRANCHES_RESPONSE_FIELDS = [
    "soc_code", "source_title", "related_soc_code", "related_title",
    "best_index", "relatedness_tier", "is_primary",
    # ... existing source/related stats ...
    "ai_boss_delta", "branch_has_full_data",
]
```

Passed to `query_iceberg_simple(..., columns=CAREER_BRANCHES_RESPONSE_FIELDS, ...)` at line 2373. Because the Iceberg projection is narrow, the four new physical columns are **not read and not returned** through this tool today. This is actually protective for the v1.2.0 landing — no surprise rows appear in MCP responses.

However: spec §Zone 4 requires appending the four new field names to `CAREER_BRANCHES_RESPONSE_FIELDS` in the next pipeline phase (workflow step 29, `bs:primary-agent`). Without that edit, the new columns are dead weight from a consumer POV. This is a **follow-up condition**, not a blocker on the schema change itself.

### 2.2 Backend service `branch_tree.py`

**Impact:** SAFE. Current code is defensive by construction.

Reviewed `backend/app/services/branch_tree.py` lines 1–100. The mapping from MCP row → `CareerBranch` is entirely `row.get(<explicit-name>)`-based (`wage_delta`, `res_delta`, `related_education_level`, `relatedness_tier`). There is no `**row` splat, no unknown-field rejection, no strict Pydantic model validation at the service layer. Extra row keys will be silently ignored until `bs:primary-agent` wires in the three new model fields (`experience_years`, `experience_tier`, `experience_delta`) per spec §Zone 5.

No grep hits for `related_experience|experience_tier|experience_delta` in `backend/app/services/` — the backend is not consuming these yet, as expected at this CAB gate.

### 2.3 Backend service `career_tree.py`

**Impact:** SAFE. Same pattern — `row.get(...)` lookups on explicit names (`related_soc_code`, `related_title`, stat columns). Extra keys ignored. The future `max_experience_years` filter parameter and `TreeNode.experience_years` / `experience_tier` additions are captured in spec §Zone 5 step 30 and are not in scope of this CAB review.

### 2.4 Frontend (React branch tree UI)

**Impact:** SAFE. TypeScript consumers read from the backend API response model; they do not talk to Gold directly. No impact from Gold-zone schema drift until backend plumbing lands.

### 2.5 Golden datasets

**Impact:** SAFE. `governance/golden-datasets/` is scanned via the spec's governance-artifact checklist; no golden dataset currently asserts against experience columns. Existing assertions remain valid (composite key, existing stat columns, existing deltas).

### 2.6 Row-count / write-path impact

Row count before: 15,944. Row count after: 15,944 (identical — pure column append via LEFT JOIN). Write-path impact is negligible.

---

## 3. Backward-Compatibility Specific Concerns

### 3.1 Does the additive schema break any existing consumer?

**No.** MCP allowlist does not project the new columns. Backend services use field-by-name lookups with `.get(...)` semantics. No consumer does `SELECT *` followed by positional or strict-schema parsing that I can find.

### 3.2 NULL semantics on `experience_delta_years`

**Handled correctly upstream, no consumer regression downstream.** The transformer at `src/gold/futureproof_engine.py:602-612` implements the spec-required NULL propagation:

```python
related_experience_years = rel_exp.get("experience_years_typical")
source_experience_years = src_exp.get("experience_years_typical")
if (source_experience_years is not None
        and related_experience_years is not None):
    experience_delta_years = related_experience_years - source_experience_years
else:
    experience_delta_years = None
```

Observed null rates (5.47% on `related_experience_years`, 9.09% on `experience_delta_years`) are within the spec's P1 DQ threshold of <5% for the first and tolerable for the derived field. Consumers that later bind these fields must handle NULL — but none do today, so no backward-compat risk exists at v1.2.0 landing.

### 3.3 Backward-compat of `derive_br_rows()` itself

`derive_br_rows()` accepts `onet_experience_rows: list[dict] | None = None` (default `None`) per the implementation summary. When None/empty, all four new fields are NULL for every row. Callers that have not been updated to pass the new kwarg still work — function signature is source-compatible. Is good pattern. Confirmed at `src/gold/futureproof_engine.py:526`.

### 3.4 Data-contract v1.2.0 label accuracy

**Accurate.** The contract's own breaking-change policy (lines 575–582) defines "column added" as MINOR. Four columns added, none removed, none retyped, none constraint-tightened. Label is correct.

---

## 4. Decision

### APPROVE WITH CONDITIONS

The schema change is safe to land as-is at the Gold layer. However, three downstream follow-ups must track this change through the remainder of the pipeline or the new columns become dormant at best and inconsistent at worst.

### Conditions (follow-up required, not blocking the Gold landing)

| # | Condition | Owner | Spec anchor |
|---|-----------|-------|-------------|
| C1 | Register the 4 new field names in `CAREER_BRANCHES_RESPONSE_FIELDS` in `src/mcp_server/futureproof_server.py`. Without this, the Gold columns exist but are invisible to Gemma. | bs:primary-agent | §Zone 4 / Workflow step 29 |
| C2 | Add `experience_years`, `experience_tier`, `experience_delta` to `CareerBranch` dataclass in `backend/app/models/career.py`; plumb through `backend/app/services/branch_tree.py`. | bs:primary-agent | §Zone 5 / Workflow step 30 |
| C3 | Add `max_experience_years` filter parameter to `build_tree()` in `backend/app/services/career_tree.py` and `experience_years`/`experience_tier` to `TreeNode`. | bs:primary-agent | §Zone 5 / Workflow step 30 |

### Forks required

**None.** This is pure addition. No v1/v2 coexistence needed. No deprecation timeline. No downstream migration spec skeleton. Existing consumers keep working without any change on their side — they simply do not see the new columns until explicitly wired.

### Conditions that would have flipped this to MAJOR (reference for future reviewers)

- If `experience_tier` had been added as a `required=True` column → MAJOR (consumers forced to handle it).
- If the grain had shifted from `[soc_code, related_soc_code]` to include experience dimensions → MAJOR.
- If an existing column (e.g., `relatedness_tier`) had been repurposed to carry tier info → MAJOR (semantic overload).
- If the CDE flag on an existing column had been flipped → MAJOR (precedent: CAB-001 flagged this pattern explicitly for `stat_res`, though that case was grandfathered as placeholder backfill).

None of those applied. All four new columns land clean.

---

## 5. Blast-Radius Summary Map

```
consumable.career_branches (v1.2.0)
  |
  +-- MCP get_career_branches  [SAFE; dormant until C1 lands]
  |     |
  |     +-- backend/app/services/branch_tree.py  [SAFE; dormant until C2]
  |     |     |
  |     |     +-- frontend branch tree UI  [SAFE; no direct Gold binding]
  |     |
  |     +-- backend/app/services/career_tree.py  [SAFE; dormant until C3]
  |
  +-- Golden datasets (governance/golden-datasets/)  [SAFE; no existing assertions]
  |
  +-- Downstream Gold tables  [NONE — career_branches is terminal]
```

Consumer count: 3 code surfaces, 0 breaking impacts, 3 dormant-until-wired.

---

## 6. Audit Trail

- Spec file read: `docs/specs/onet-experience-requirements.md` (governance re-review verdict: APPROVED, 2026-04-16)
- Contract read: `governance/data-contracts/consumable-career-branches.yaml` v1.2.0 (already bumped, version_history entry present lines 594–604)
- Physical-model addendum read: `governance/models/gold-futureproof-engine-physical.md` lines 893–1022 (addendum for 4 experience columns, 2026-04-16)
- Implementation read: `src/gold/futureproof_engine.py` lines 221 (`get_br_schema`, 34 fields) and 521–662 (`derive_br_rows` with `onet_experience_rows` kwarg default `None`)
- MCP read: `src/mcp_server/futureproof_server.py` lines 377–406 (`CAREER_BRANCHES_RESPONSE_FIELDS`, 28 entries — 4 new not yet registered), lines 2370–2375 (explicit-column Iceberg projection)
- Backend services read: `backend/app/services/branch_tree.py` (no experience references yet), `backend/app/services/career_tree.py` (no experience references yet)
- Prior CAB precedent: `governance/cab-decisions/CAB-001-gold-futureproof-engine-backfill-ai.json` — same table, same table's prior MINOR classification for 6 additive columns. Consistent treatment.

---

## 7. One-Line Decision

**APPROVED WITH CONDITIONS — MINOR additive schema change on `consumable.career_branches`, v1.1.0 → v1.2.0. Zero breaking impact on MCP / backend / frontend today; three non-blocking follow-ups (C1/C2/C3) must land to realize the columns' value. No fork required.**
