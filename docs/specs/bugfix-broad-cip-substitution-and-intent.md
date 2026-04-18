# Bugfix: Broad-CIP Substitution & Intent Prompt Bias

## Claude Code Prompt

```
Read the spec at docs/specs/bugfix-broad-cip-substitution-and-intent.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review §1–§4 for substitution data-flow correctness across all CIP granularities (4-digit "52.01", padded 6-digit "52.0100", specific 6-digit "52.0101"/"52.1401") and the proposed deterministic short-circuit in the intent service.
   - Writes findings to §5. If APPROVED → step 2. If CHANGES REQUESTED or REJECTED → STOP, alert human.

2. IMPLEMENTATION
   - Implement §4 exactly. Touch only the files listed in the File Changes table.
   - BEFORE coding: read §4 Testing Impact Analysis. Note which tests are Confirmed Safe — if any of those fail, STOP and escalate.
   - Log all work to §6. Run backend (ruff + mypy + pytest) and pipeline (ruff + pytest at repo root) to verify the build is green when you finish.
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts). After 3 failed attempts, escalate to human via §10 and set status BLOCKED.

3. PROMPT REWRITE
   - Invoke @fp-copywriter to rewrite the `_INTENT_SYSTEM_PROMPT` body in `backend/app/services/intent.py`. The brief: bias Gemma toward the most specific CIP that matches the student's intent, even when that CIP isn't in the school's reported list. The earnings-blending caveat is the backend's job, not Gemma's. Voice must stay consistent with `docs/reference/voice-guide.md`.
   - @fp-copywriter logs the before/after prompt diff and reasoning to §10.

4. TESTING
   - Invoke @test-writer to add the cases in §4 "New Tests Required". P0 first.
   - Run the full pytest suite (`uv run pytest` at repo root, `cd backend && pytest`). Every failure must be acknowledged in §7. Never silently skip.

5. CODE REVIEW
   - Invoke @faang-staff-engineer for security/performance/error-handling review of the substitution helpers and the intent short-circuit. Writes verdict to §8.

6. VERIFICATION
   - Invoke @fp-builder to run the full pipeline: ruff, mypy, pytest (root + backend), TypeScript, vitest. Logs to §9.

7. COMPLETION
   - Update Status to COMPLETE. Tick every Success Criterion in §1. Move spec to `docs/specs/completed/`. Write report to `reports/bugfix-broad-cip-substitution-and-intent-2026-04-18.md`.
```

---

## Status: DRAFT

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-18 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-04-18 |
| Blocked By | — |
| Related Specs | `docs/specs/completed/cip-intent-substitution.md`, `docs/specs/completed/spike-intent-substitution.md`, `docs/specs/completed/career-path-fallback.md`, `docs/specs/concept-gemma-intent-cache.md`, `docs/specs/feature-gemma-tiered-matching.md` |

---

## §1 Feature Description

### Overview

Two compounding bugs cause a student picking a specific major (e.g. "Marketing") at a broad-CIP school (e.g. Indiana University, which reports all Kelley grads under `52.01 Business/Commerce, General`) to see a hard error instead of marketing-specific careers. This spec fixes the substitution lookup to be CIP-granularity-agnostic, and rewrites the intent prompt so Gemma stops dodging the substitution flow.

### Problem Statement

**Reproduction (verified locally on `main` 2026-04-18):**

1. User enters Indiana University-Bloomington + "Marketing".
2. Frontend `POST /intent/` → backend `intent.resolve_intent` → Gemma returns:
   - `matched_cip="52.0100"`, `matched_title="Business/Commerce, General"`, `confidence="medium"`, `parent_cip="52.01"`.
   - Gemma picked the school's reported program (zero-padded to 6 digits) instead of the cousin `52.14 Marketing` from `data/reference/major_to_cip.yaml`.
3. Frontend `POST /build/outcomes` with `cipcode="52.0100"`, `student_major="Marketing"`.
4. MCP `_handle_get_career_paths` (`src/mcp_server/futureproof_server.py:2031-2076`) correctly fires substitution because `_is_broad_cip("52.0100")` is `True` (regex `^\d{2}\.01(00)?$` accepts the padded form) and `_find_major_intent("Marketing")` returns the entry with `cip4="52.14"`.
5. Inside `_build_substituted_rows` (`src/mcp_server/futureproof_server.py:1538-1551`) it queries `consumable.career_outcomes` with exact filter `cipcode="52.0100"`. But `career_outcomes` only stores 4-digit CIPs — IU's row is `cipcode="52.01"`. Zero rows → returns:
   `No career_outcomes row for unitid=151351, cipcode='52.0100'; cannot substitute.`
6. `compute_pentagon` raises `ValueError(message)`. FastAPI returns 422. User sees the message on `/career-pick` and reads it as "missing crosswalk data".

**Bug A** (substitution lookup): exact-equals match against `career_outcomes.cipcode` is fragile — only the bare 4-digit form happens to work. Fix: normalize the lookup to `cipcode[:5]`.

**Bug B** (intent prompt): the prompt at `backend/app/services/intent.py:22-55` lists school-reported CIPs first under "these have earnings data" and crosswalk CIPs second under "these have career path data even if the school doesn't report them separately." For broad-CIP schools, Gemma reads the first signal as dominant and picks the broad school CIP even when the student's intent maps cleanly to a specific cousin. The substitution flow exists *exactly* to handle "specific major from broad-CIP school" — Gemma should be told to pick the most specific CIP and let the backend blend earnings.

Verified: with `cipcode="52.01"` the same handler call returns 9 marketing-specific careers led by *Advertising and Promotions Managers*. The bug is purely the granularity mismatch.

### Success Criteria

- [ ] `_handle_get_career_paths(unitid=151351, cipcode="52.0100", student_major="Marketing")` returns 9 substituted Marketing rows with `substituted_cipcode="52.14"` and a `blended_substitution` caveat — same shape as the `cipcode="52.01"` call today.
- [ ] `_handle_get_career_paths(unitid=151351, cipcode="52.0101", student_major="Marketing")` returns the same 9 substituted Marketing rows (specific 6-digit form of the broad CIP also works).
- [ ] No regression on `_handle_get_career_paths(unitid=151351, cipcode="52.01", student_major="Marketing")` — still returns 9 substituted Marketing rows.
- [ ] No regression on the standard path: `_handle_get_career_paths(unitid=151351, cipcode="52.10")` (Human Resources, the only other 52.x program IU reports) still returns the school's HR career paths from `program_career_paths`.
- [ ] `intent.resolve_intent("Marketing", "Indiana University-Bloomington", 151351, [...])` returns `matched_cip="52.14"` (or `52.1401`), NOT `52.01` / `52.0100` / `52.0101`. Confidence is `high` because it's a deterministic YAML hit.
- [ ] `intent.resolve_intent("Accounting", ...)` and `intent.resolve_intent("Finance", ...)` at IU also return their YAML `cip4` directly — pick any school in `consumable.career_outcomes` that reports `52.01`, behavior must be the same.
- [ ] `intent.resolve_intent("Underwater basket weaving", ...)` still falls through to Gemma — the short-circuit fires only on exact YAML hits.
- [ ] Existing `tests/mcp/test_cip_substitution.py` and `tests/mcp/test_cip_substitution_integration.py` suites still pass without modification (they pin the bare-4-digit happy path and must keep passing).
- [ ] New tests cover all three input CIP forms (`52.01`, `52.0100`, `52.0101`) and the deterministic intent short-circuit.
- [ ] Full build green: `ruff`, `mypy`, `pytest` (root + backend), TypeScript, `vitest`, Vite production build.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Normalize `reported_cipcode` to its 4-digit prefix (`cipcode[:5]`) inside `_build_substituted_rows` before the `career_outcomes` lookup. | `consumable.career_outcomes` is canonically 4-digit (BT-086, see `governance/models/gold-futureproof-engine-logical.md`). The 6-digit-padded form is just Gemma's choice, not data we can change. Normalizing at the lookup site is the smallest correct fix and keeps the rest of the substitution payload intact (the substituted rows still set `cipcode = substituted_cipcode` per existing behavior). | (a) Strip "00" padding upstream in `compute_pentagon` — rejected, leaks granularity awareness into the backend service that has no business knowing it. (b) Loosen `_BROAD_CIP_PATTERN` to accept `52.0101` etc. — rejected, that regex correctly identifies the family-general CIP and shouldn't drift. (c) Have Gemma always return 4-digit — rejected, we can't reliably constrain Gemma's output across two backends and the substitution YAML itself uses both 4- and 6-digit entries. |
| 2 | Audit and apply the same `cipcode[:5]` normalization to every `cipcode=` filter on `consumable.career_outcomes` and `consumable.program_career_paths` in `futureproof_server.py`. | Both tables are 4-digit. Any exact-match filter using a caller-supplied cipcode has the same latent bug — today it's masked by the broaden-fallback for some paths but bites for substitution. Fix once, fix all. | Patch only `_build_substituted_rows` — rejected, leaves a class of latent bugs that will surface the next time anyone wires a new code path. |
| 3 | When the student's free-text input is an exact match (or exact alias match) to a `major_to_cip.yaml` entry, short-circuit Gemma in `intent.resolve_intent` and return the YAML's `cip4` with confidence `high`, reasoning `"Deterministic match from major_to_cip.yaml"`. Only invoke Gemma on YAML misses. | We have a deterministic answer for "Marketing" — calling Gemma is rolling dice on a settled question. The audit step (`_audit_intent_mapping`) still runs after the short-circuit so we keep the safety net. Cuts one Gemma call per known major (cheaper, faster, and removes the prompt-bias failure mode entirely for the cases the YAML covers). | (a) Only fix the prompt — rejected, the prompt rewrite is also needed for unknown-major cases, but we shouldn't pay the latency / nondeterminism cost when YAML already answers. (b) Short-circuit AND skip the audit — rejected, audit catches genuinely adversarial inputs ("pre-med" → audit on the 51-family, etc.) and stays cheap. |
| 4 | Rewrite `_INTENT_SYSTEM_PROMPT` to (i) drop the "earnings data" vs "career path data" framing that currently biases Gemma toward school-reported CIPs, and (ii) explicitly instruct Gemma to pick the most specific CIP that matches the student's intent, telling it the backend handles earnings blending automatically. | The current prompt accidentally teaches Gemma to dodge the substitution flow. The substitution flow is the entire point of the intent feature for broad-CIP schools. Prompt copy must reflect the system's actual contract. | Add chain-of-thought / few-shot examples — rejected as out of scope for a bugfix; if the rewrite isn't enough we'll open a separate spec for richer prompt engineering. |
| 5 | Keep the substitution caveat shape unchanged (`type: "blended_substitution"`, `reported_cipcode`, `substituted_cipcode`, `substituted_program`, etc.). | The frontend types reference `data_caveat` even though no UI consumes it today. Changing the shape now risks breaking the future UI work tracked separately. The fix is to populate the caveat with the *4-digit* `reported_cipcode` so when the UI is wired, it surfaces the canonical CIP. | Rename fields for clarity — rejected, scope creep. |

### Constraints

- `consumable.career_outcomes` schema is fixed (4-digit `cipcode`). No pipeline / Iceberg changes in this spec.
- `consumable.program_career_paths` schema is fixed (4-digit `cipcode`). No pipeline changes.
- `data/reference/major_to_cip.yaml` is read-only in this spec — entries are correct, the lookup is the bug.
- Gemma may be running on Ollama (local dev) or OpenRouter (cloud demo). The fix must work identically on both — no new prompt patterns, no new tools, no model-specific assumptions.
- All `gemma_client.generate` call sites must keep their existing deterministic fallback. The intent short-circuit is *additional* determinism, not a replacement for the audit step.

### Out of Scope

- **Frontend display of `data_caveat`.** The substitution path sets a caveat; no React component consumes it. That's a UX gap, but bundling it here grows blast radius. Track separately.
- **Deeper Gemma intent caching / eval harness.** `docs/specs/concept-gemma-intent-cache.md` and `docs/specs/feature-gemma-tiered-matching.md` cover this. Coordinate, do not duplicate.
- **Adding new entries to `major_to_cip.yaml`.** Coverage gaps (especially Education family 6-digit entries documented in `docs/Background_for_CIP_Disambig_Fix.md`) are a separate problem. This spec only fixes the lookup mechanics.
- **Reworking `_audit_intent_mapping`.** Stays as-is. Still runs after both the short-circuit and the Gemma path.
- **Changing `_BROAD_CIP_PATTERN`.** It's correct.
- **Deprecating `_fallback_broaden_cip` or `_fallback_gemma_soc_resolution`.** They stay as the safety net for cases the substitution path can't handle.

---

## §3 UI/UX Design

**SKIPPED (backend-only spec).** No frontend file changes. The user-visible improvement is "Marketing at IU returns marketing careers instead of an error" — the screens that render the result are unchanged.

---

## §4 Technical Specification

### Architecture Overview

Two services touched, one orchestration call site:

1. **MCP server** (`src/mcp_server/futureproof_server.py`): the substitution and standard query helpers inside `FutureProofMCPServer` need to normalize caller-supplied cipcodes to 4-digit before filtering `career_outcomes` / `program_career_paths`. Single helper method (`_canonical_cip4`) keeps the rule in one place.

2. **Intent service** (`backend/app/services/intent.py`): `resolve_intent` checks the YAML lookup first via the same matching logic the MCP server already uses (`_find_major_intent` semantics) and short-circuits Gemma when there's an exact / alias hit. The system prompt is rewritten for the cases that still go to Gemma.

No Iceberg schema changes. No new endpoints. No frontend changes. No new dependencies.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `/Users/jcernauske/code/bright/futureproof-data/src/mcp_server/futureproof_server.py` | Modify | Add `_canonical_cip4(cipcode: str) -> str` helper. Apply it inside `_build_substituted_rows` (line 1541) and at the standard-path / fallback-broaden / Gemma-SOC-fallback `cipcode=` filter sites (lines 1860, 2139, 2181). Update the substituted-row caveat to set `reported_cipcode` to the 4-digit form so consumers see the canonical CIP. |
| `/Users/jcernauske/code/bright/futureproof-data/backend/app/services/intent.py` | Modify | Add deterministic YAML short-circuit at the top of `resolve_intent` (after cache check, before `_call_gemma_intent`). Rewrite `_INTENT_SYSTEM_PROMPT` body via @fp-copywriter. Reuse `_find_major_intent` semantics by reading `data/reference/major_to_cip.yaml` directly (helper module to avoid circular import with `mcp_server`). |
| `/Users/jcernauske/code/bright/futureproof-data/backend/app/services/major_lookup.py` | Create | New small module. Single public function `lookup_major(text: str) -> dict | None` that loads `data/reference/major_to_cip.yaml` (cached) and returns the matching entry by `major` or `aliases` (case-insensitive). Pure-Python, no deps beyond `pyyaml`. Used by both `intent.py` (new) and optionally referenced from MCP server (existing `_find_major_intent` behavior stays — module is the deterministic backbone the intent short-circuit uses). |
| `/Users/jcernauske/code/bright/futureproof-data/backend/tests/services/test_intent.py` | Create | New test file. Covers deterministic YAML short-circuit, Gemma fallback for unknown majors, audit behavior unchanged. |
| `/Users/jcernauske/code/bright/futureproof-data/backend/tests/services/test_major_lookup.py` | Create | New test file for `major_lookup.lookup_major`. |
| `/Users/jcernauske/code/bright/futureproof-data/tests/mcp/test_cip_substitution.py` | Modify | Add cases for `52.0100` and `52.0101` reported_cipcode forms. Add cases for `_canonical_cip4` helper. Existing tests stay untouched (Confirmed Safe). |
| `/Users/jcernauske/code/bright/futureproof-data/tests/mcp/test_cip_substitution_integration.py` | Modify | Add an end-to-end variant of `TestIUBMarketing52_14` that sends `cipcode="52.0100"` and asserts the same substituted-Marketing payload comes back. |

### Data Model Changes

**None.** No Iceberg schema changes, no DuckDB schema changes, no new Pydantic models. The existing `IntentResult` (`backend/app/models/career.py`) and the existing substitution caveat shape are unchanged.

### Service Changes

**New module — `backend/app/services/major_lookup.py`:**

```python
"""Deterministic CIP lookup from data/reference/major_to_cip.yaml.

Used by the intent service to short-circuit Gemma when the student's
input is an exact (or alias) match for a known major. Pure Python,
no LLM, no external calls.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

import yaml


class MajorEntry(TypedDict):
    major: str
    cip4: str
    cip_family: str
    aliases: list[str]


_LOOKUP_CACHE: list[MajorEntry] | None = None
_LOOKUP_PATH = Path("data/reference/major_to_cip.yaml")


def _load() -> list[MajorEntry]:
    global _LOOKUP_CACHE
    if _LOOKUP_CACHE is not None:
        return _LOOKUP_CACHE
    # Resolve relative to the project root regardless of cwd.
    try:
        from brightsmith.config import PROJECT_ROOT  # type: ignore
        root = Path(PROJECT_ROOT)
    except Exception:
        root = Path.cwd()
    path = root / _LOOKUP_PATH
    if not path.exists():
        _LOOKUP_CACHE = []
        return _LOOKUP_CACHE
    with path.open() as f:
        raw = yaml.safe_load(f) or []
    if not isinstance(raw, list):
        _LOOKUP_CACHE = []
        return _LOOKUP_CACHE
    _LOOKUP_CACHE = [e for e in raw if isinstance(e, dict)]
    return _LOOKUP_CACHE


def lookup_major(text: str) -> MajorEntry | None:
    """Return the matching YAML entry or None.

    Matches case-insensitively against `major` and every `alias`.
    Returns None for empty input, no match, or load failure.
    """
    if not text:
        return None
    needle = text.strip().lower()
    if not needle:
        return None
    for entry in _load():
        if needle == str(entry.get("major", "")).lower():
            return entry
        for alias in entry.get("aliases") or []:
            if needle == str(alias).lower():
                return entry
    return None
```

**MCP server — new helper inside `FutureProofMCPServer`:**

```python
@staticmethod
def _canonical_cip4(cipcode: str) -> str:
    """Normalize an arbitrary CIP code to the 4-digit XX.YY form.

    `consumable.career_outcomes` and `consumable.program_career_paths`
    are both stored at 4-digit granularity. Callers (Gemma, frontend,
    YAML) may hand in 6-digit forms ("52.0100", "52.0101", "52.1401")
    that exact-equals queries against either table will miss.
    Normalize to the 4-digit prefix at every filter site.
    """
    if not cipcode:
        return cipcode
    return cipcode[:5] if len(cipcode) >= 5 else cipcode
```

**MCP server — `_build_substituted_rows` patch:** at line 1541, replace `"cipcode": reported_cipcode` with `"cipcode": self._canonical_cip4(reported_cipcode)`. Also update the error message at line 1549 to surface the canonical form (`f"cipcode='{self._canonical_cip4(reported_cipcode)}'; cannot substitute."`) so logs reflect the actual lookup. The substituted-row caveat (built downstream) sets `reported_cipcode` to the canonical 4-digit form too — single source of truth.

**MCP server — `_handle_get_career_paths` patch:** at line 2139 and line 2181, replace `"cipcode": cipcode` with `"cipcode": self._canonical_cip4(cipcode)`. The `cipcode` variable used downstream (substituted-rows, caveats) is otherwise unchanged so the responses still echo the caller's input verbatim where appropriate.

**MCP server — `_fallback_gemma_soc_resolution` patch:** at line 1860, replace `str(r.get("cipcode", "")) == cipcode` with `str(r.get("cipcode", "")) == self._canonical_cip4(cipcode)`.

**Intent service — `resolve_intent` short-circuit:** insert after the cache check (line 250-259), before `_get_school_cips`:

```python
deterministic = major_lookup.lookup_major(major_text)
if deterministic is not None:
    cip4 = str(deterministic.get("cip4", ""))
    title = str(deterministic.get("major", ""))
    careers = _get_career_titles_for_cip(cip4)
    audit = _audit_intent_mapping(major_text, cip4, title, careers)
    audit_flag = None
    audit_message = None
    if audit:
        tone = str(audit.get("tone", "clean"))
        message = str(audit.get("message", ""))
        if not bool(audit.get("valid", True)):
            audit_flag = "hard_reject"
            audit_message = message
        elif tone == "playful_warning":
            audit_flag = "playful_warning"
            audit_message = message
    return IntentResult(
        matched_cip=cip4,
        matched_title=title,
        confidence="high",
        reasoning="Deterministic match from major_to_cip.yaml.",
        careers_preview=careers,
        audit_flag=audit_flag,
        audit_message=audit_message,
        needs_clarification=False,
        alternatives=None,
        parent_cip="",
    )
```

**Intent service — `_INTENT_SYSTEM_PROMPT` rewrite:** authored by @fp-copywriter in step 3 of the workflow. Brief recorded in §10. The function signature of `_call_gemma_intent` does not change — just the prompt body.

### Testing Impact Analysis

> Searched `tests/mcp/`, `backend/tests/`, and `tests/` for tests touching `_build_substituted_rows`, `_handle_get_career_paths`, `_INTENT_SYSTEM_PROMPT`, and `resolve_intent`. Findings below.

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `tests/mcp/test_cip_substitution.py` | `TestIntegrationLikePath::test_iub_marketing_substitution_fires` | Low | Passes `cipcode="52.01"` (bare 4-digit). `_canonical_cip4("52.01") == "52.01"` so behavior is identical. |
| `tests/mcp/test_cip_substitution.py` | `TestIntegrationLikePath::test_no_substitution_when_specific_cip` | Low | Passes `cipcode="52.14"`. `_canonical_cip4("52.14") == "52.14"`. Identical. |
| `tests/mcp/test_cip_substitution.py` | `TestStatComputation::test_ern_and_roi_match_engine_formula` | Low | Same — bare 4-digit input. |
| `tests/mcp/test_cip_substitution.py` | `TestSchoolRowMissing::test_missing_school_row_returns_null` | Med | Test stubs `query_iceberg_simple` to return `[]` — should still surface the "No career_outcomes row" error path with the new canonical form in the message. May need to update the asserted message string if it pins the exact text. |
| `tests/mcp/test_cip_substitution.py` | `TestEmptyCrosswalk::test_empty_crosswalk_returns_null` | Low | Stubs the crosswalk fetch — unaffected by the lookup change. |
| `tests/mcp/test_cip_substitution_integration.py` | `TestIUBMarketing52_14::*` (5 tests) | Low | All pass `cipcode="52.01"`. Identical behavior. |
| `tests/mcp/test_cip_substitution_integration.py` | `TestOtherBusinessMajors::test_accounting_soc_set` / `test_finance_soc_set` | Low | Bare 4-digit. Identical. |
| `tests/mcp/test_cip_substitution_integration.py` | `TestSpecificCIPDirect::test_isu_52_14_direct_path` | Low | Bare 4-digit. Identical. |
| `tests/mcp/test_cip_substitution_integration.py` | All others | Low | Same. |
| `backend/tests/services/test_stat_engine.py` | All | Low | Stat engine doesn't touch the lookup; calls MCP via fixture. |
| `backend/tests/services/test_school_lookup.py` | All | Low | Lookup-table tests, unchanged. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `tests/mcp/test_cip_substitution.py::TestSchoolRowMissing::test_missing_school_row_returns_null` | Update the asserted error message string if it pins the now-canonicalized `cipcode='...'` substring. | The error message change is intentional — it now reports the canonical form so logs are accurate. |

#### Confirmed Safe

Every other existing test in `tests/mcp/`, `backend/tests/`, and `tests/`. None of them exercise the 6-digit-padded input form, and none assert on the prompt body text. **If any of these fail, STOP and escalate via §10.**

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `tests/mcp/test_cip_substitution.py` | `TestCanonicalCip4::test_strips_padding` | `_canonical_cip4("52.0100") == "52.01"`, `_canonical_cip4("52.0101") == "52.01"`, `_canonical_cip4("52.14") == "52.14"`, `_canonical_cip4("52.1401") == "52.14"`, `_canonical_cip4("52.01") == "52.01"`, `_canonical_cip4("") == ""`. |
| P0 | `tests/mcp/test_cip_substitution.py` | `TestIntegrationLikePath::test_padded_broad_cip_still_substitutes` | Calls `_handle_get_career_paths(unitid=151351, cipcode="52.0100", student_major="Marketing")` against the same fixture set as `test_iub_marketing_substitution_fires`. Asserts `substitution_applied=True`, `reported_cipcode="52.01"` (canonicalized), `substituted_cipcode="52.14"`, and same row count. |
| P0 | `tests/mcp/test_cip_substitution.py` | `TestIntegrationLikePath::test_specific_six_digit_broad_cip_still_substitutes` | Same as above but with `cipcode="52.0101"` (the specific 6-digit form of Business/Commerce, General). Same expectations. |
| P0 | `tests/mcp/test_cip_substitution_integration.py` | `TestIUBMarketing52_14_PaddedInput::test_substitution_fires_with_52_0100` | End-to-end against the real Iceberg tables: `cipcode="52.0100"`, `student_major="Marketing"`, asserts substituted Marketing rows + `_blended_substitution` caveat. Mirrors the existing `TestIUBMarketing52_14::test_substitution_fires` shape. |
| P0 | `backend/tests/services/test_intent.py` | `TestDeterministicShortCircuit::test_marketing_skips_gemma` | Patch `gemma_client.generate` to raise on call. `resolve_intent("Marketing", "Indiana University-Bloomington", 151351, [...])` returns `matched_cip="52.14"`, `confidence="high"`, `reasoning` mentions YAML. Audit may still call Gemma — patch that separately or stub it to no-op. |
| P0 | `backend/tests/services/test_intent.py` | `TestDeterministicShortCircuit::test_alias_match_skips_gemma` | `resolve_intent("mktg", ...)` (an alias for Marketing) hits the short-circuit too. |
| P0 | `backend/tests/services/test_intent.py` | `TestDeterministicShortCircuit::test_unknown_major_falls_through_to_gemma` | `resolve_intent("Underwater basket weaving", ...)` skips the short-circuit. Assert `gemma_client.generate` is called. |
| P0 | `backend/tests/services/test_major_lookup.py` | `TestLookupMajor::test_exact_major_match` / `test_alias_match` / `test_case_insensitive` / `test_empty_input_returns_none` / `test_unknown_returns_none` | Standard coverage of `lookup_major`. |
| P1 | `backend/tests/services/test_intent.py` | `TestDeterministicShortCircuit::test_short_circuit_runs_audit` | Confirm the audit call still fires after the short-circuit (so `audit_flag` and `audit_message` propagate). |
| P1 | `tests/mcp/test_cip_substitution.py` | `TestStandardPath::test_padded_specific_cip_normalizes` | `_handle_get_career_paths(unitid=151351, cipcode="52.1000", student_major=None)` (HR padded to 6 digits) returns IU's HR rows from `program_career_paths`. Validates the standard-path normalization. |
| P2 | `backend/tests/services/test_intent.py` | `TestPromptCopy::test_prompt_does_not_bias_toward_school_cips` | After @fp-copywriter rewrites the prompt, snapshot-test the system-prompt body to flag accidental regressions toward the old "earnings data" framing. Lightweight string assertion. |

#### Test Data Requirements

- **MCP unit tests** reuse the existing in-test stubs in `tests/mcp/test_cip_substitution.py` (mock `query_iceberg_simple` returning the fixed IU 52.01 row + 52.14 crosswalk SOCs). No new fixtures needed.
- **MCP integration tests** depend on `data/futureproof.duckdb` / Iceberg warehouse being populated for `unitid=151351`. Existing `tests/mcp/test_cip_substitution_integration.py` already documents this (see top-of-file fixtures).
- **Intent service tests** need `gemma_client.generate` patched at the module level. Use `monkeypatch.setattr("backend.app.services.intent.gemma_client.generate", ...)`. The audit step also calls `gemma_client.generate` — patch it to return `None` (drops audit silently per existing fallback at line 229).
- **`major_lookup` tests** need `data/reference/major_to_cip.yaml` reachable from `Path.cwd()`. Either run from repo root (consistent with existing test conventions) or use `monkeypatch.chdir(repo_root)` in a fixture.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** PENDING
#### Findings
[Filled in by @fp-architect — focus on data-flow correctness across all CIP granularities and the short-circuit's interaction with the audit step]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

### @fp-data-reviewer Review
**Status:** SKIPPED (no pipeline / stat-formula / crosswalk changes — only lookup mechanics on existing tables)

---

## §6 Implementation Log

**Status:** PENDING

### Files Modified
| File | Change Summary |
|------|---------------|

### Deviations from Spec
[Any divergence from §4 and why]

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|

---

## §7 Test Coverage

**Status:** PENDING

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest (root) | | | | |
| pytest (backend) | | | | |
| vitest | | | | |

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@fp-design-auditor)
**Status:** SKIPPED (backend-only spec)

### Code Review (@faang-staff-engineer)
**Status:** PENDING
#### Findings
[Filled in by reviewer — focus on the substitution helpers and the intent short-circuit. Watch for: silent-fail in `lookup_major` (file missing → empty list → all majors fall through to Gemma — is that the right failure mode?), audit-call duplication on the short-circuit path, log noise, error-message string drift breaking downstream tooling.]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

---

## §9 Verification

**Status:** PENDING

### Backend (@fp-builder)
| Check | Result |
|-------|--------|
| Lint (ruff) — backend | |
| Lint (ruff) — pipeline | |
| Type check (mypy) — backend | |
| Tests (pytest) — backend | |
| Tests (pytest) — pipeline | |

### Frontend (@fp-builder)
| Check | Result |
|-------|--------|
| TypeScript | |
| Tests (vitest) | |
| Production build (Vite) | |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|

---

## §10 Discussion

```
[2026-04-18 spec-author → @fp-copywriter]
Brief for the prompt rewrite (step 3 of the workflow):

Current prompt (backend/app/services/intent.py:22-55) lists the school's
reported CIPs first under "Programs this school reports (these have
earnings data)" and the crosswalk CIPs second under "these have career
path data even if the school doesn't report them separately." For
broad-CIP schools (e.g. IU/Kelley reports all of Business under 52.01),
Gemma reads the first signal as dominant and picks the broad school CIP
even when the student's intent maps cleanly to a specific cousin
(e.g. 52.14 Marketing). That kills the substitution flow before the
backend ever sees it.

Required shift:
- Tell Gemma to pick the most specific CIP that matches the student's
  intent, full stop.
- Make explicit that the backend handles earnings blending — Gemma does
  NOT need to favor school-reported CIPs to "preserve earnings data."
- Drop the "these have earnings data" / "these have career path data"
  framing entirely. Both lists are equally valid match candidates.
- Keep the JSON output schema unchanged (`matched_cip`, `matched_title`,
  `confidence`, `reasoning`, `parent_cip`, `alternatives`).

Voice: stay consistent with docs/reference/voice-guide.md. The prompt
isn't user-facing but the reasoning Gemma generates IS shown in the UI,
so coach Gemma toward concise, confident match rationale.

Log the before/after diff and reasoning here.
```

---

## §11 Final Notes

**Human Review:** PENDING

[Final thoughts, lessons learned, follow-up items.]
