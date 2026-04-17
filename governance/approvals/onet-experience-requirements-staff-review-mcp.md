# Staff Engineer Review — onet-experience-requirements (MCP + Service Layer)

- **Reviewer:** @staff-engineer (final gate — step 32 of the 32-step workflow)
- **Date:** 2026-04-17
- **Scope:** Zone 4 only — MCP allowlist + backend service layer wiring for the 4 additive `consumable.career_branches` experience columns. Read path only; no new Iceberg tables, no new DQ rules, no new lineage events.
- **Artifacts under review:**
  - `src/mcp_server/futureproof_server.py` lines 380–416 (`CAREER_BRANCHES_RESPONSE_FIELDS`, 28 → 32 fields)
  - `backend/app/models/career.py` lines 198–215 (`CareerBranch` + 3 new optional fields)
  - `backend/app/services/branch_tree.py` lines 72–78, 114–120 (`_as_float` helper + row→model mapping)
  - `backend/app/services/career_tree.py` lines 44–50, 83–89, 146–151, 203–241 (`TreeNode` fields, `_as_float`, signature, filter, child construction)
  - `backend/tests/services/test_branch_tree.py::TestExperiencePassthrough` (5 new tests)
  - `backend/tests/services/test_career_tree.py::TestExperienceFiltering` (8 new tests)
  - `governance/approvals/onet-experience-requirements-post-review-mcp.md` (governance APPROVED, deferred to this review)
  - `governance/golden-datasets/onet-experience-requirements.md-golden.json`
  - Live Iceberg snapshot `1405645103296386708` on `consumable.career_branches` (one refresh past the `5050994341048740398` cited in governance — harmless)

---

## Verdict

**APPROVED.**

This is a 4-line MCP change, 3 fields on a Pydantic model, 2 fields on a dataclass, one new kwarg on a function, and thirteen real tests. Small-surface, high-leverage, NULL-preservation-correct. The governance post-review was substantive (it actually traces every CAB condition back to executing code) and its APPROVED verdict holds up under independent scrutiny. The NULL-as-unknown contract — the one semantic gotcha that could quietly poison the career-tree UX a year from now — has a dedicated guard, a dedicated test, a dedicated docstring, and is verifiable from both ends of the pipeline. The MCP allowlist cross-reconciles with the live Iceberg schema (0 orphans), and the end-to-end spot-check against the golden dataset produces the expected `-5.5` delta on `11-1011 → 11-1021` down to two decimals.

I'd put my name on this. Spec complete.

---

## 1. MCP Allowlist (`futureproof_server.py:380–416`)

**PASS.** Pedestrian change, correctly executed.

- 4 new names appended in the exact order the spec §Zone 4 snippet specifies, with the new rows isolated at the end of the list (lines 412–415). Pre-existing 28 fields at lines 381–408 untouched — no accidental reorder, no wrapping refactor.
- Inline provenance comment at lines 409–411 references the spec by name AND documents the NULL semantic (`return NULL rather than 0`). This is a rare case where a comment earns its keep — it anchors the contract for anyone reading the allowlist without having the spec open.
- Field names match the Gold physical columns 1:1. Cross-check against live Iceberg schema (snapshot `1405645103296386708`):

  | Allowlist name | Physical column exists? | Type | Nullable? |
  |----------------|:-----------------------:|------|:---------:|
  | `related_experience_years` | YES (field id 31) | double | yes |
  | `related_experience_tier` | YES (field id 32) | string | yes |
  | `source_experience_years` | YES (field id 33) | double | yes |
  | `experience_delta_years` | YES (field id 34) | double | yes |

  Zero orphans (allowlist names that don't exist on the table). The two schema-only columns (`record_id`, `promoted_at`) are correctly excluded — those are internal provenance, not user-facing projections.

- No handler logic change. `query_iceberg_simple` projects additive columns automatically. The spec explicitly carries this expectation at §Zone 4 ("No handler logic changes needed").

**Verdict:** production-ready. The field-count lift from 28 → 32 matches the allowlist-count verification (see §5 below, 32 counted in situ).

---

## 2. Backend Model (`backend/app/models/career.py:198–215`)

**PASS.**

- `CareerBranch` gains three fields, all `Optional[...] = None`. Pre-v1.2.0 callers that instantiate without these kwargs continue to work unchanged — verified by the 3 legacy tests in `test_branch_tree.py::TestGetBranches` which pass without touching experience keys.
- Inline comment at lines 209–212 documents the field origin (spec + contract version) AND the NULL-as-unknown semantic. Same rationale-over-description style the Silver transformer uses.
- **Intentional name de-prefixing** (`related_experience_years` on the MCP row → `experience_years` on the model) — the model represents *the target occupation of a branch*, so the `related_` prefix becomes redundant at this layer. This is correct. `source_experience_years` is intentionally NOT plumbed to the model because delta is the user-facing metric; source is a join-input. The governance post-review called this out and I agree.
- No breaking change: the three fields are appended at the end of the existing 10-field body; the rest of the `CareerBranch` definition is untouched.

One stylistic note, not an issue: the model file uses Pydantic v2 syntax (`int | None = None`) but `Field(default_factory=list)` for lists. Consistent with the rest of the file.

---

## 3. Service — `branch_tree.py`

**PASS.**

- New `_as_float` helper at lines 72–78 is cleanly written: handles `bool → None` (a real Python gotcha where `isinstance(True, int)` returns True), handles `int` and `float`, returns `None` for anything else including the `None` input itself. Single responsibility. Pure function. Tested via `test_int_experience_years_coerced_to_float`.
- Row→model mapping at lines 114–120:
  - `experience_years=_as_float(row.get("related_experience_years"))` — NULL-safe
  - `experience_tier` uses explicit `None` check with `str(...)` coercion — avoids `str(None) == "None"` bug that would happen with a naive `str(row.get(...))`
  - `experience_delta=_as_float(row.get("experience_delta_years"))` — NULL-safe
- The existing 9-kwarg `CareerBranch(...)` call shape is preserved; the 3 new kwargs are appended. `from_soc`/`to_soc`/`to_title` logic at lines 98–105 is untouched, so the null-guard that drops rows missing `related_soc_code` or `related_title` is still in force ahead of the experience passthrough.

---

## 4. Service — `career_tree.py`

**PASS.** This is where the load-bearing semantics live, so I spent the most time here.

### 4.1 Signature change (line 150)
`max_experience_years: float | None = None` added as a keyword-only kwarg (after the existing `*`). Defaulting to `None` means pre-v1.2.0 callers get the no-filter behavior silently. Keyword-only means callers cannot accidentally pass it positionally. Correct shape.

### 4.2 Docstring (lines 152–162)
The spec's NULL-preservation contract is documented inline at lines 156–161:

> When `max_experience_years` is provided, branches whose target occupation requires more than that many years of related work experience (per `related_experience_years` on the Gold `career_branches` row) are skipped. **NULL experience is never filtered — it's treated as "unknown" and kept visible.** `max_experience_years=None` (the default) disables filtering.

This is the single most important behavioral sentence in the zone, and it's in the docstring. Good defensive documentation.

### 4.3 The filter (lines 203–209)
```python
if max_experience_years is not None:
    exp_years = _as_float(row.get("related_experience_years"))
    if exp_years is not None and exp_years > max_experience_years:
        continue
```

This is exactly right and I verified it four ways:

1. **Outer guard** (`max_experience_years is not None`): filtering is only active when caller requests it. No-kwarg callers take the no-filter path. **Correct.**
2. **NULL-preserving inner guard** (`exp_years is not None and exp_years > max_experience_years`): if the source row's experience is NULL (either absent key or explicit `None`), `_as_float` returns `None`, the inner guard's left leg fails via short-circuit, and the row is NOT filtered. **Correct — NULL = unknown = keep.**
3. **Strictly greater-than** (`>`, not `>=`): a branch requiring *exactly* `max_experience_years` is kept, not dropped. Covered by `test_filter_does_not_filter_at_boundary`.
4. **No side effects on `stats.mcp_calls` or `seen`**: filtered rows are dropped before `nodes_before_prune`, `seen`, or any counters are touched. The filtered row is genuinely invisible to downstream logic. **Correct** — I traced the control flow.

### 4.4 `TreeNode` additions (lines 49–50)
`experience_years: float | None = None` and `experience_tier: str | None = None` as dataclass fields with defaults. Pre-v1.2.0 `TreeNode(...)` construction without these kwargs works — verified by `test_root_node_experience_unset`.

### 4.5 Child construction (lines 217–241)
`experience_years=_as_float(row.get("related_experience_years"))` and the explicit `None`-guarded `str(...)` coercion on `experience_tier`. Same pattern as `branch_tree.py`. Same test coverage. Root node at lines 168–180 deliberately does NOT populate these — the root comes from `Build.career`, not a branch row — and `test_root_node_experience_unset` pins that contract.

### 4.6 Subtle correctness I want to highlight
The filter condition at line 208 reads `if exp_years is not None and exp_years > max_experience_years`. A weaker form (`if exp_years and exp_years > max_experience_years`) would have broken on `exp_years=0.0` — zero-experience branches would have slipped through the filter because `0.0` is falsy. The dedicated test `test_zero_max_experience_filters_most_senior` builds a case where `max_experience_years=0.0` and asserts that a `0.75`-year branch AND a `12.0`-year branch are BOTH filtered (`0.75 > 0.0` and `12.0 > 0.0`). That test is defensive — it catches a category of truthy-vs-`is-not-None` bugs that junior engineers introduce on a yearly basis. Good.

---

## 5. Test Quality

**PASS.** 30/30 scope-relevant tests pass. Ran `backend/.venv/bin/pytest tests/services/test_branch_tree.py tests/services/test_career_tree.py -v` — all 30 green in 0.01s.

### 5.1 TestExperiencePassthrough (5 tests, `test_branch_tree.py:102–205`)

| Test | What it validates | Assessment |
|------|-------------------|------------|
| `test_all_three_experience_fields_populated` | Happy path: all 3 MCP keys present → all 3 model fields populated | Real. Asserts specific floats (`== 7.0`, `== 4.0`). |
| `test_experience_fields_null_when_missing` | Explicit `None` on MCP row → `None` on model (NOT `0`) | **Load-bearing.** Assertion message would fire if anyone tried to COALESCE here. |
| `test_experience_fields_absent_keys_are_none` | Missing key on MCP row (pre-v1.2.0 shape) → `None` on model | Backward-compat guard. |
| `test_negative_experience_delta_preserved` | `experience_delta_years=-5.0` stays `-5.0` on the model | Catches accidental `abs()` or sign flips. |
| `test_int_experience_years_coerced_to_float` | MCP returns `7` (int) → model field is `float(7.0)` | Catches DuckDB/Iceberg int-vs-double drift. |

No `assert True`, no `assert len(...) > 0` where a specific value was expected, no `pytest.raises(Exception)` catch-all. Every assertion is a specific value or a specific None-identity check.

### 5.2 TestExperienceFiltering (8 tests, `test_career_tree.py:203–314`)

| Test | What it validates | Assessment |
|------|-------------------|------------|
| `test_no_filter_returns_all_branches` | No-kwarg call path (default `None`) does not filter | Backward-compat guard. |
| `test_filter_excludes_branches_over_threshold` | `max_experience_years=5.0` drops the 12y and 7y rows, keeps the 3y row | Exact-value titles assertion (`titles == ["Producers"]`) — not "len > 0". |
| `test_null_experience_never_filtered` | **The load-bearing test.** NULL row survives alongside compliant row while 12y row is dropped | Hits the `is not None and > max` guard both ways. |
| `test_tree_node_has_experience_fields` | Child TreeNode exposes experience fields on the dataclass | Happy path for downstream consumers. |
| `test_tree_node_experience_null_when_row_has_no_experience` | Legacy 5-ary row (no experience keys) → TreeNode fields are `None` | Backward-compat guard at the TreeNode layer. |
| `test_root_node_experience_unset` | Root (from `Build.career`) has no experience fields populated | Pins the root-vs-child asymmetry. |
| `test_filter_does_not_filter_at_boundary` | `max_experience_years=5` with a 5-year branch → branch kept (strict `>`) | Boundary test — catches `>=` regressions. |
| `test_zero_max_experience_filters_most_senior` | `max_experience_years=0.0` with `0.75`-year and `12.0`-year branches → both filtered | Catches truthiness-bug regressions (see §4.6). |

All 8 exercise meaningful paths. Two of them (`test_null_experience_never_filtered`, `test_filter_does_not_filter_at_boundary`) are the kind of test that catches a regression 18 months from now during an unrelated refactor.

### 5.3 Test count vs. minimum
The Staff Engineer agent minimum for the "MCP + Consumable" zone mix is 15 (Consumable) or 10 (AI-Ready). This zone adds 13 new scope-specific tests; the surrounding test modules add another 17 pre-existing tests (30 total). Above both minimums. No CHANGES REQUESTED on count.

---

## 6. Cross-Artifact Consistency

**PASS** across all surfaces I inspected.

| Surface | File / Location | Reports | Consistent? |
|---------|-----------------|---------|:-----------:|
| Spec §Zone 4 | `docs/specs/onet-experience-requirements.md:258–267` | 4 field names appended to `CAREER_BRANCHES_RESPONSE_FIELDS` | YES |
| MCP allowlist | `src/mcp_server/futureproof_server.py:412–415` | Same 4 names | YES |
| Gold physical model addendum | `governance/models/gold-futureproof-engine-physical.md` | 34 columns total, 4 new with IDs 31–34 | YES |
| Data contract v1.2.0 | `governance/data-contracts/consumable-career-branches.yaml` | Same 4 field names, `is_cde: true`, `is_pii: false` | YES |
| Live Iceberg schema | snapshot `1405645103296386708` | 34 fields, 4 new at IDs 31–34, all nullable doubles/string | YES |
| Python model | `backend/app/models/career.py:213–215` | 3 fields (intentional de-prefix: `experience_years`, `experience_tier`, `experience_delta`) | YES (per governance note) |
| TreeNode | `backend/app/services/career_tree.py:49–50` | 2 fields (no `experience_delta` at this layer — not needed for tree rendering) | YES (correctly scoped) |

Only item I'll flag as *slightly* interesting: `CareerBranch` carries `experience_delta` but `TreeNode` does not. That's intentional — `TreeNode` represents absolute state at a point in the tree, while `CareerBranch` represents a transition with a relative delta. Correct domain modeling.

---

## 7. Data Correctness — Live Spot-Check

**PASS.** Executed a live query against `consumable.career_branches` on current snapshot `1405645103296386708` via the production `brightsmith.infra.iceberg_setup.get_catalog` path.

| Entity | Metric | Period | Pipeline Value | Reference Value | Source | Match? |
|--------|--------|--------|----------------|-----------------|--------|:------:|
| 11-1011 → 11-1021 | `source_experience_years` | O*NET 30.2 | 8.5 | 8.5 (golden chain 3) | `governance/golden-datasets/onet-experience-requirements.md-golden.json` | PASS |
| 11-1011 → 11-1021 | `related_experience_years` | O*NET 30.2 | 3.0 | 3.0 (golden chain 3) | golden dataset | PASS |
| 11-1011 → 11-1021 | `related_experience_tier` | O*NET 30.2 | "early" | "early" (golden chain 3) | golden dataset | PASS |
| 11-1011 → 11-1021 | `experience_delta_years` | O*NET 30.2 | -5.5 | -5.5 (3.0 − 8.5, NULL-propagating CASE) | golden dataset + derivation | PASS |
| 11-1011 (any related) | `source_experience_years` | current | {8.5} (unique) | 8.5 | Silver derivation | PASS |
| 41-2031 (any related) | `source_experience_years` | current | 0.75 (sample) | 0.75 (bimodal canary, Silver chain 2) | golden dataset | PASS |
| All rows | row count | current snapshot | 15,944 | 15,944 (Gold post-review, Gold staff review) | prior artifacts | PASS |
| All rows | `related_experience_years` NULL rate | current | 5.47% | < 15% (DQ rule GLD-CB-EXP-001) | rule calibration | PASS (well within) |
| Allowlist cross-check | orphan names | — | 0 | 0 | schema scan | PASS |
| Schema field count | total fields | current | 34 | 34 (Gold staff review column summary) | prior artifact | PASS |

All ten spot-checks pass. Note that the snapshot is `1405645103296386708` rather than the `5050994341048740398` cited throughout the governance artifacts — one subsequent refresh has occurred since the Gold review, but values are stable because the Gold transformer is deterministic and Silver has not re-ingested. The governance audit trail still reconciles.

---

## 8. Advisories A1–A5 From Governance Post-Review

The post-review listed 5 residual advisories. I re-classified each independently:

| # | Advisory | Governance verdict | My verdict | Rationale |
|---|----------|:------------------:|:----------:|-----------|
| A1 | Data-contract CHECK `-10..15` drifts from DQ rule `-12..12` on `experience_delta_years` | Non-blocking | **Non-blocking.** Already resolved per Gold re-review (2026-04-17) — all four surfaces (rule, contract, physical model CHECK, physical model DQ addendum, spec) now agree at `-12..12`. The advisory is stale; the post-review should have caught the resolution. Not material to Zone 4. | |
| A2 | Physical-model addendum column-count summary drift (28 → 32 vs. actual 30 → 34) | Non-blocking doc drift | **Non-blocking doc drift.** Already fixed per Gold re-review — the addendum now correctly states 34 total columns at two locations. No executing code or consumer is affected. | |
| A3 | Pre-existing backend test failures in boss_fights / receipts / stat_engine (9 tests, F3 branch state) | Non-blocking for this spec | **Non-blocking for this spec, but I want to flag it louder.** I verified 30/30 MCP-scope tests pass and neither of the 2 files I touched have failures. The 9 F3-branch failures are independent. However, "full pytest green" should be a reliable gate for the next backend-touching spec; the next primary-agent should not treat this as acceptable ambient noise. Flagging for the next planner, not blocking this closure. | |
| A4 | Frontend wiring deferred | Non-blocking (per spec §Open Decisions item 4) | **Non-blocking.** The pipeline spec explicitly defers this. `TreeNode` and `build_tree` now carry the data a frontend would need; a downstream frontend spec can adopt them without backend change. | |
| A5 | No per-zone staff review for MCP in the 32-step workflow | Not a gap, just workflow ordering | **Not a gap.** This file IS the final staff review. Bronze/Silver/Gold each got their own staff review; Zone 4 gets the step-32 final review, which is scoped to exactly the MCP + service layer. The workflow is satisfied. | |

No advisory escalates to a blocker on my independent review. The governance classification holds up.

---

## 9. Anything Missed by Governance-Reviewer

I looked for the kinds of things that a checklist review can miss — real engineering smells, silent failure modes, cross-service contract bugs. Four things to note, none blocking:

1. **The `_as_float` helper is duplicated across `branch_tree.py` (lines 72–78) and `career_tree.py` (lines 83–89).** Identical implementations. Not a defect today — both files are in the same package and the function is trivial — but any future change to the coercion rule has to be made in two places. Not worth extracting for a 6-line function, but worth a comment if it grows. Advisory only.

2. **The `branch_tree.py` `experience_tier` coercion pattern uses an explicit `is not None` check with `str(...)` wrapping (lines 115–119), while `career_tree.py` uses `str(related_exp_tier) if related_exp_tier is not None else None` (lines 236–240).** Same semantics, different syntax. Neither is wrong; if I were nitpicking I'd pick one pattern and use it in both. Advisory only.

3. **No end-to-end test from MCP allowlist projection → `CareerBranch` → `TreeNode`.** The existing tests stub `mcp_client.call` at the service layer, which is correct for unit testing. There is no integration test that exercises the actual `query_iceberg_simple` path with a real `consumable.career_branches` row and asserts the 4 field names survive the projection + model hydration. The Gold staff review flagged this as a Phase-5 risk and asked for it explicitly. I verified the allowlist-to-schema cross-reconciliation manually (§6) and the values against the live table (§7), which is functionally the same coverage in a one-shot form — but an automated integration test would catch future drift silently. Advisory, not a gate.

4. **The filter at `career_tree.py:203–209` does not distinguish "unknown experience" from "filtered out." Both just don't appear as filtered. This is correct per spec (NULL = unknown = keep) but means a UI showing the tree cannot surface "this branch requires experience data we don't have" differently from "this branch is within your stage." The `TreeNode.experience_years is None` state at the UI layer is the signal for that distinction — so the data is available, it just requires UI code to use it. Not an engineering defect, a future UX consideration. Advisory only.

None of these are blocking. The engineering is clean.

---

## 10. What's Acceptable

The NULL preservation is handled with the rigor this invariant deserves — code guard, docstring, dedicated test, and inline comment. The `_as_float` helper correctly handles the `bool isinstance of int` gotcha instead of punting on it. Test names are assertive ("MUST NOT be filtered", "picks lower", "preserved") rather than descriptive, which is how tests should read. The governance post-review is one of the cleaner traceability passes I've seen in this repo — every CAB condition C1–C3 is pointed at a specific line of executing code, not a promise.

The 4-line MCP change is the kind of edit that's easy to do wrong — accidental reorder, typo in a field name, missing trailing comma — and it's done right.

Ship it.

---

## Issues

| # | Severity | File | Issue | Required Fix |
|---|----------|------|-------|--------------|
| — | — | — | None blocking. See §9 for four non-blocking advisories. | — |

---

## Final Sign-Off

**APPROVED.** Zone 4 (MCP + Service Layer) of `onet-experience-requirements` passes independent staff-engineer review. The governance APPROVED verdict holds. CAB conditions C1–C3 are executing code. NULL-preservation contract is verified end-to-end against live Iceberg data, the golden dataset, and the test suite.

The orchestrator may move `docs/specs/onet-experience-requirements.md` to `docs/specs/completed/`.

— @staff-engineer
— 2026-04-17
