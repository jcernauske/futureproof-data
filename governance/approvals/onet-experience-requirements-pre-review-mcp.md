# Governance Review: onet-experience-requirements — Zone 4 (MCP + Service Layer)

**Review Type:** Pre-Implementation (MCP / Service Layer zone)
**Reviewer:** @governance-reviewer (bs:governance-reviewer)
**Date:** 2026-04-16
**Verdict:** APPROVED (MCP implementation may begin)

---

## Scope

Final zone of the cross-zone O*NET experience-requirements spec. Bronze, Silver, and Gold have all been APPROVED (pre + post + staff). The 4 additive columns on `consumable.career_branches` are live in Iceberg and DQ-validated:

| Column | Type | Null rate (Gold post-review) |
|--------|------|------------------------------|
| `related_experience_years` | DOUBLE | 5.47% |
| `related_experience_tier` | STRING | 5.47% |
| `source_experience_years` | DOUBLE | 3.88% |
| `experience_delta_years` | DOUBLE | 9.09% (NULL-propagating union) |

This zone wires the already-written columns through the MCP tool and into the backend service layer. No new data, no new DQ rules, no schema changes beyond what Gold already committed. CAB already APPROVED WITH CONDITIONS C1–C3 that map exactly to the four code edits below.

---

## Current State Verification (file-level)

| # | Artifact | Path | Current State | Required Change |
|---|----------|------|---------------|-----------------|
| 1 | MCP response allowlist | `src/mcp_server/futureproof_server.py` lines 380–409 (`CAREER_BRANCHES_RESPONSE_FIELDS`) | 28 fields, no experience fields present (grep confirms zero hits on `experience_*` tokens in the whole file) | Append the 4 new column names to the list |
| 2 | Backend model | `backend/app/models/career.py` lines 198–208 (`CareerBranch` class) | 9 fields: `from_soc`, `to_soc`, `to_title`, `delta_ern`, `delta_roi`, `delta_res`, `delta_grw`, `delta_hmn`, `unlock`, `relatedness` — no experience fields (grep confirms) | Add 3 optional fields: `experience_years: float \| None = None`, `experience_tier: str \| None = None`, `experience_delta: float \| None = None` |
| 3 | Branch tree service | `backend/app/services/branch_tree.py` lines 93–106 (row-to-model mapping in `get_branches`) | Constructs `CareerBranch(...)` with 9 kwargs; no experience passthroughs | Add 3 `row.get(...)` passthroughs: `experience_years=row.get("related_experience_years")`, `experience_tier=row.get("related_experience_tier")`, `experience_delta=row.get("experience_delta_years")` |
| 4 | Career tree service — signature | `backend/app/services/career_tree.py` lines 130–134 (`build_tree()` signature) | `def build_tree(build: Build, *, max_depth: int = 3) -> tuple[TreeNode, TreeStats]:` | Add `max_experience_years: float \| None = None` kwarg |
| 5 | Career tree service — filter | `backend/app/services/career_tree.py` lines 174–183 (expansion loop in `expand()`) | No experience filtering | Insert guard: if `max_experience_years is not None` and `row.get("related_experience_years") > max_experience_years`, `continue` |
| 6 | TreeNode dataclass | `backend/app/services/career_tree.py` lines 29–51 (`TreeNode` dataclass) | 15 fields covering stats, wage, boss, education, children — no experience fields | Add 2 optional fields: `experience_years: float \| None = None`, `experience_tier: str \| None = None` |
| 7 | TreeNode population | `backend/app/services/career_tree.py` lines 185–202 (child `TreeNode(...)` construction) | Already passes `education=row.get("related_education_level")` | Also pass `experience_years=row.get("related_experience_years")` and `experience_tier=row.get("related_experience_tier")` |

All seven required edits are additive. None mutate existing call signatures in a breaking way (all new kwargs are optional with `None` defaults).

---

## Pre-Implementation Checklist (Zone 4)

| # | Item | Status | Note |
|---|------|--------|------|
| 1 | Spec §Zone 4 and §Zone 5 specify exact code shape | PASS | Lines 254–351 of the spec give code snippets for all 7 edits, including exact parameter names and types. |
| 2 | Upstream data exists | PASS | Gold post-review verified all 4 columns populated in `consumable.career_branches` with expected null rates. |
| 3 | Upstream DQ green | PASS | Gold addendum rules executed — GLD-CB-EXP-001 (null rate <15%), GLD-CB-EXP-002 (delta −12..12), GLD-CB-EXP-003 (senior ⇒ years ≥ 8) all PASS. |
| 4 | CAB decision captured | PASS | CAB APPROVED WITH CONDITIONS C1–C3 = exactly the MCP + service edits in this zone. |
| 5 | Primary implementation agent | PASS | `bs:primary-agent` (same agent that shipped Bronze/Silver/Gold). |
| 6 | No new DQ rules needed | PASS | This zone is contract-carrying code only — no new Iceberg tables, no new DQ rules needed. Existing Gold rules cover the data. |
| 7 | No new CDE / lineage artifacts needed | PASS | CDE flags already applied to `consumable-career-branches.yaml` in Zone 3. No new lineage events — MCP is a query layer, not a transformation job. Column lineage for the 4 Gold columns was emitted with the Gold OpenLineage event. |
| 8 | No new data models needed | PASS | MCP + service layer is not a Base/Gold zone transformation. Data model gate N/A. |
| 9 | No breaking changes to MCP public contract | PASS | The 28 existing `CAREER_BRANCHES_RESPONSE_FIELDS` entries remain; new fields are appended. Additive schema change per JSON-Schema semver rules. |
| 10 | No breaking changes to backend model public contract | PASS | 3 new fields on `CareerBranch` are all `Optional[...] = None` — default-None means any existing caller that constructs `CareerBranch(...)` without these kwargs keeps working. |
| 11 | Testing approach defined | PASS | Spec §Test Matrix covers weighted-median edge cases at Silver. Zone 4 needs three integration-level tests: (a) MCP tool returns 32 fields not 28; (b) `branch_tree.get_branches()` populates the 3 new model fields when MCP returns them; (c) `career_tree.build_tree(max_experience_years=5.0)` prunes high-experience branches. These are standard for `@test-writer`. |
| 12 | Frontend integration scope | PASS | Spec §Open Decisions item #4 explicitly DEFERS frontend filter-vs-dim to a downstream frontend spec. Not blocking this pipeline zone. |

---

## Data Model Gate

**N/A.** The MCP + Service Layer zone is not a Base or Gold transformation. The Base-zone greenfield gate was already satisfied in Phase 1 (Silver models approved 2026-04-16); the Gold physical-model addendum was satisfied in Phase 4.

---

## Cross-Zone Consistency Checks

| Check | Result |
|-------|--------|
| MCP field names match Gold column names | PASS — spec §Zone 4 lists exactly `related_experience_years`, `related_experience_tier`, `source_experience_years`, `experience_delta_years`. Gold post-review confirms these are the physical column names. |
| Model field names (intentional rename) | PASS — backend renames `related_experience_years` → `experience_years`, `related_experience_tier` → `experience_tier`, `experience_delta_years` → `experience_delta` on `CareerBranch`. This is a deliberate de-prefix because the model represents a single branch (caller-side, "related" prefix is redundant). `source_experience_years` is intentionally NOT plumbed to the model — spec §Zone 5 does not include it (delta is the user-facing metric). |
| TreeNode field names | PASS — spec §Zone 5 shows `experience_years` and `experience_tier` on `TreeNode`, which matches the `CareerBranch` model naming. `experience_delta` is NOT plumbed to `TreeNode` because tree-level filtering uses absolute `experience_years` against a threshold, not a delta. |
| Filter semantics (`max_experience_years`) | PASS — filter is `> max_experience_years` (strict greater-than per spec line 338), so `max_experience_years=5.0` admits branches at exactly 5.0 years. Matches the spec's "≤ 5 years" default-view guidance at line 572. |

---

## Issues Found

None. No blockers, no changes requested, no advisories. The spec is unusually concrete for this zone — every edit is spelled out at code-snippet fidelity.

---

## Decision Rationale

This is the simplest zone of the five. All data is in place, all DQ has passed, all contracts are bumped, CAB has signed off, and the spec gives exact code shapes. The four files that need editing are all read-verified in this review:

- `src/mcp_server/futureproof_server.py`:380–409 — 28 fields today, will be 32 after
- `backend/app/models/career.py`:198–208 — 9 fields today, will be 12 after
- `backend/app/services/branch_tree.py`:93–106 — 9 kwargs today, will be 12 after
- `backend/app/services/career_tree.py`:29–51, 130–134, 174–202 — adds 1 parameter, 2 TreeNode fields, 3-line filter guard, 2 TreeNode kwargs

All additions are append-only and default-None, so backward compatibility is structurally guaranteed — no deprecations, no migrations, no callers to update.

Post-implementation governance review (step 31 of the pipeline) will verify:
- MCP tool response includes the 4 new fields for a known SOC (e.g., `15-1252` Software Developers)
- `get_branches("15-1252")` returns `CareerBranch` objects with `experience_years`, `experience_tier`, `experience_delta` populated
- `build_tree(build, max_experience_years=5.0)` produces a strictly smaller tree than `build_tree(build)` when at least one branch has `experience_years > 5.0`
- Full test suite passes (pipeline pytest + backend pytest + ruff + mypy)

**Verdict: APPROVED (MCP implementation may begin)**

The implementing agent (`bs:primary-agent`) may proceed to steps 29 and 30 of the agent workflow.
