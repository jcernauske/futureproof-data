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

## Status: COMPLETE

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-18 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.1 |
| Last Updated | 2026-04-18 (rev for @fp-architect CHANGES REQUESTED) |
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

- [x] `_handle_get_career_paths(unitid=151351, cipcode="52.0100", student_major="Marketing")` returns 9 substituted Marketing rows with `substituted_cipcode="52.14"` and a `blended_substitution` caveat — same shape as the `cipcode="52.01"` call today. (`"52.0100"` is the zero-padded 6-digit form of the broad family-general code; `_is_broad_cip` accepts it.)
- [x] No regression on `_handle_get_career_paths(unitid=151351, cipcode="52.01", student_major="Marketing")` — still returns 9 substituted Marketing rows.
- [x] No regression on the standard path: `_handle_get_career_paths(unitid=151351, cipcode="52.10")` (Human Resources, the only other 52.x program IU reports) still returns the school's HR career paths from `program_career_paths`.
- [x] `_handle_get_career_paths(unitid=151351, cipcode="52.0101", student_major="Marketing")` does NOT substitute. `52.0101` is a specific 6-digit CIP (Business/Commerce, General), not a broad family-general code — `_is_broad_cip("52.0101")` is `False` by design. After canonicalization the request falls through the standard path (`cipcode="52.01"`), which then routes through the deterministic broadening fallback (`_fallback_broaden_cip`) because no IU program is reported at exactly `52.01` in `program_career_paths`. The response is shaped by the broadening fallback, not by the substitution branch. This behavior is intentional — loosening `_BROAD_CIP_PATTERN` to treat `.0101` as broad was explicitly rejected in Decision #1 Alt (b).
- [x] `intent.resolve_intent("Marketing", "Indiana University-Bloomington", 151351, [...])` returns `matched_cip="52.14"`, NOT `52.01` / `52.0100` / `52.0101`. Confidence is `high` (deterministic YAML hit). `parent_cip="52.01"` because IU's `programs` list contains a broader same-family entry — the frontend needs this non-empty signal to light up the substitution affordance on the major-confirm card (`frontend/src/components/school/MajorInput.tsx:102`).
- [x] `intent.resolve_intent("Accounting", ...)` and `intent.resolve_intent("Finance", ...)` at IU also return their YAML `cip4` directly, with `parent_cip="52.01"` — pick any school in `consumable.career_outcomes` that reports `52.01`, behavior must be the same.
- [x] `intent.resolve_intent("Marketing", ...)` at a school that reports `52.14` directly (not just `52.01`) returns `matched_cip="52.14"` with `parent_cip=""` — no substitution needed, frontend should render the confirm card without the substitution affordance.
- [x] `intent.resolve_intent("Underwater basket weaving", ...)` still falls through to Gemma — the short-circuit fires only on exact YAML / alias hits.
- [x] Existing `tests/mcp/test_cip_substitution.py` and `tests/mcp/test_cip_substitution_integration.py` suites still pass without modification (they pin the bare-4-digit happy path and must keep passing).
- [x] New tests cover both valid substitution input forms (`52.01`, `52.0100`), the specific-CIP fall-through (`52.0101`), and the deterministic intent short-circuit (including `parent_cip` derivation).
- [x] Full build green: `ruff`, `mypy`, `pytest` (root + backend), TypeScript, `vitest`, Vite production build.

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
| `/Users/jcernauske/code/bright/futureproof-data/src/mcp_server/futureproof_server.py` | Modify | Add `_canonical_cip4(cipcode: str) -> str` helper. Apply it inside `_build_substituted_rows` (line 1541) and at the standard-path / fallback-broaden / Gemma-SOC-fallback `cipcode=` filter sites (lines 1860, 2139, 2181). Canonicalize `reported_cipcode` in all four response sites (caveat L2116, substitution-root L2127, broadened-rows L2171, Gemma-SOC-fallback L2202). Add a one-line comment at L1745 noting `_fallback_broaden_cip`'s L1749 comparison is known-dead (deferred, not touched by this spec). |
| `/Users/jcernauske/code/bright/futureproof-data/backend/app/services/intent.py` | Modify | Add deterministic YAML short-circuit at the top of `resolve_intent` (after cache check, before `_get_school_cips`). Add `_derive_parent_cip(cip4, programs)` helper to surface the school's broader same-family reported CIP (so the frontend's `parent_cip !== ""` substitution-affordance signal stays correct). Rewrite `_INTENT_SYSTEM_PROMPT` body via @fp-copywriter. Reuse `_find_major_intent` semantics via the new `major_lookup` module to avoid a circular import with `mcp_server`. |
| `/Users/jcernauske/code/bright/futureproof-data/backend/app/services/major_lookup.py` | Create | New small module. Single public function `lookup_major(text: str) -> dict | None` that loads `data/reference/major_to_cip.yaml` (cached) and returns the matching entry by `major` or `aliases` (case-insensitive). Pure-Python, no deps beyond `pyyaml`. Used by both `intent.py` (new) and optionally referenced from MCP server (existing `_find_major_intent` behavior stays — module is the deterministic backbone the intent short-circuit uses). |
| `/Users/jcernauske/code/bright/futureproof-data/backend/tests/services/test_intent.py` | Modify | File already exists (covers the Gemma tiered path). APPEND a new `TestDeterministicShortCircuit` class plus the P2 `TestPromptCopy` class. Do not rewrite or reorganize the existing tests — they pin the Gemma-path contract and must keep passing. |
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

Path resolution is cwd-independent: we walk upward from this module
file looking for the YAML. Backend pytest runs from `backend/`, root
pytest runs from the repo root, and `uvicorn app.main:app` is started
from either — all three must resolve the same YAML or the
short-circuit silently no-ops in some contexts (which is exactly how
Bug B leaked into prod before this spec).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TypedDict

import yaml


class MajorEntry(TypedDict):
    major: str
    cip4: str
    cip_family: str
    aliases: list[str]


_REL_YAML_PATH = Path("data/reference/major_to_cip.yaml")


@lru_cache(maxsize=1)
def _yaml_path() -> Path | None:
    """Walk upward from this module's directory until we find a
    parent that contains `data/reference/major_to_cip.yaml`. Returns
    None if we hit the filesystem root without finding it.
    """
    for parent in Path(__file__).resolve().parents:
        candidate = parent / _REL_YAML_PATH
        if candidate.is_file():
            return candidate
    return None


@lru_cache(maxsize=1)
def _load() -> tuple[MajorEntry, ...]:
    path = _yaml_path()
    if path is None:
        return ()
    with path.open() as f:
        raw = yaml.safe_load(f) or []
    if not isinstance(raw, list):
        return ()
    return tuple(e for e in raw if isinstance(e, dict))


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

**MCP server — `_build_substituted_rows` patch:** at line 1541, replace `"cipcode": reported_cipcode` with `"cipcode": self._canonical_cip4(reported_cipcode)`. Also update the error message at line 1549 to surface the canonical form (`f"cipcode='{self._canonical_cip4(reported_cipcode)}'; cannot substitute."`) so logs reflect the actual lookup.

**MCP server — `_handle_get_career_paths` standard-path and Gemma-SOC-fallback filter patches:** at line 2139 (standard-path `CAREER_PATHS_TABLE` filter) and line 2181 (Gemma-SOC-fallback `CAREER_OUTCOMES_TABLE` `program_name` lookup filter), replace `"cipcode": cipcode` with `"cipcode": self._canonical_cip4(cipcode)`. The caller-supplied `cipcode` variable remains unchanged; only the table-filter value is canonicalized.

**MCP server — `_fallback_gemma_soc_resolution` patch:** at line 1860, replace `str(r.get("cipcode", "")) == cipcode` with `str(r.get("cipcode", "")) == self._canonical_cip4(cipcode)`.

**MCP server — response `reported_cipcode` canonicalization (all four sites):** the response payload exposes `reported_cipcode` in four places, and they must all agree so a future UI consumer sees the canonical 4-digit form no matter which field it reads:

| Line | Location | Change |
|------|----------|--------|
| 2116 | Substitution caveat dict (`"reported_cipcode": cipcode`) | `"reported_cipcode": self._canonical_cip4(cipcode)` |
| 2127 | Substitution response root (`"reported_cipcode": cipcode`) | `"reported_cipcode": self._canonical_cip4(cipcode)` |
| 2171 | Broadened-rows response root (`"reported_cipcode": cipcode`) | `"reported_cipcode": self._canonical_cip4(cipcode)` |
| 2202 | Gemma-SOC-fallback response root (`"reported_cipcode": cipcode`) | `"reported_cipcode": self._canonical_cip4(cipcode)` |

No frontend component consumes `reported_cipcode` today (verified: `frontend/src/types/build.ts:78–80` declares the type, `frontend/src/api/mockBuild.ts:69,94` echoes it in mocks, no React component branches on it). Canonicalizing is safe and future-proofs the UI wire-up.

**MCP server — fifth filter site (`_fallback_broaden_cip` L1749) is known-dead, intentionally skipped.** The comparison at L1749 is `str(r.get("cipcode", "")) == general_cip` where `general_cip = f"{family}.0100"`. Because `consumable.career_transitions` stores 4-digit cipcodes (matching the rest of Gold), this equality can never match — it's pre-existing latent dead code independent of this bugfix. Canonicalizing `general_cip` to `f"{family}.01"` would change behavior in a branch that currently yields empty results every time, widening this spec's blast radius for no benefit. **Deferred** with a one-line comment added at L1745 flagging the dead branch, tracked as a follow-up; implementers must not silently change the comparison as part of this spec.

**Intent service — `resolve_intent` short-circuit:** insert after the cache check (current line 377–386) and before `school_cips = _get_school_cips(unitid)` (current line 388):

```python
# Deterministic YAML short-circuit. When the student's input is an exact
# or alias match for a known major in data/reference/major_to_cip.yaml,
# we have the answer without calling Gemma. Short-circuit here and skip
# both the Gemma call and the prompt-bias failure mode that this spec
# otherwise fixes.
#
# parent_cip contract: the frontend reads `parent_cip !== ""` as "the
# backend will substitute on /build/outcomes" (MajorInput.tsx:102). If
# the school reports a broader same-family CIP (e.g. IU reports 52.01
# and the student asked for Marketing / 52.14), we must surface that
# reported CIP here — otherwise the confirm card will say "no
# substitution" while outcomes silently substitutes. If the school
# reports the exact cip4 directly, parent_cip stays "" (no substitution
# needed).
#
# Cache policy: this block deliberately does NOT write to
# _intent_cache. Cache writes are owned by confirm_intent and happen
# only after the student confirms the match. Same invariant as the
# Gemma path.
deterministic = major_lookup.lookup_major(major_text)
if deterministic is not None:
    cip4 = str(deterministic.get("cip4", ""))
    title = str(deterministic.get("major", ""))
    parent_cip = _derive_parent_cip(cip4, programs)
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
        parent_cip=parent_cip,
    )
```

**Intent service — new `_derive_parent_cip` helper:** add at module scope, above `resolve_intent`:

```python
def _derive_parent_cip(cip4: str, programs: list[dict]) -> str:
    """Pick the school's reported broader-family CIP (if any) that the
    YAML-matched cip4 should substitute against.

    The frontend uses a non-empty `parent_cip` as the "substitution will
    apply" signal on the major-confirm card (MajorInput.tsx:102). On the
    /build/outcomes side, `_handle_get_career_paths` fires the
    substitution branch when the caller passes a broad CIP
    (`_is_broad_cip`) AND the YAML has a specific cip4. We need to
    surface the broad reported CIP here so the confirm card matches
    what outcomes will do.

    Rules (keep them tight — callers pass raw programs from
    IntentRequest, so we defend against missing/bad cipcode values):

    - If `programs` contains an entry whose canonical 4-digit cipcode
      equals `cip4` exactly, the school reports the specific program.
      No substitution needed — return "".
    - Otherwise, scan for an entry in the same 2-digit family as `cip4`
      that matches `_BROAD_CIP_PATTERN` (i.e. `XX.01` or `XX.0100`).
      If found, return its canonical 4-digit form.
    - Otherwise return "". The outcomes path will handle the miss via
      its existing broadening fallback.
    """
    if not cip4 or not programs:
        return ""
    family = cip4[:2]
    if not family.isdigit():
        return ""
    candidates: list[str] = []
    for program in programs:
        raw = str(program.get("cipcode", "") or "")
        if not raw:
            continue
        canonical = raw[:5] if len(raw) >= 5 else raw
        if canonical == cip4:
            return ""
        if canonical[:2] != family:
            continue
        # Match _BROAD_CIP_PATTERN semantics: accept raw "XX.01" and
        # zero-padded "XX.0100". Specific 6-digit forms ("XX.0101") are
        # not broad and do not qualify as a substitution parent.
        if raw in (f"{family}.01", f"{family}.0100"):
            candidates.append(canonical)
    return candidates[0] if candidates else ""
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
| P0 | `tests/mcp/test_cip_substitution.py` | `TestIntegrationLikePath::test_padded_broad_cip_still_substitutes` | Calls `_handle_get_career_paths(unitid=151351, cipcode="52.0100", student_major="Marketing")` against the same fixture set as `test_iub_marketing_substitution_fires`. Asserts `substitution_applied=True`, `reported_cipcode="52.01"` (canonicalized at BOTH caveat and response-root), `substituted_cipcode="52.14"`, and same row count. |
| P0 | `tests/mcp/test_cip_substitution.py` | `TestIntegrationLikePath::test_specific_six_digit_does_not_substitute` | `_handle_get_career_paths(unitid=151351, cipcode="52.0101", student_major="Marketing")` does NOT substitute (`_is_broad_cip("52.0101")` is `False`). Asserts the response is shaped by the standard path — specifically the broadening fallback (`substitution_applied=True` with the broadened-rows caveat type, NOT `blended_substitution`) because no IU program is reported at exactly `52.01` in `program_career_paths`. |
| P0 | `tests/mcp/test_cip_substitution_integration.py` | `TestIUBMarketing52_14_PaddedInput::test_substitution_fires_with_52_0100` | End-to-end against the real Iceberg tables: `cipcode="52.0100"`, `student_major="Marketing"`, asserts substituted Marketing rows + `_blended_substitution` caveat. Mirrors the existing `TestIUBMarketing52_14::test_substitution_fires` shape. |
| P0 | `backend/tests/services/test_intent.py` | `TestDeterministicShortCircuit::test_marketing_skips_gemma` | Patch `gemma_client.generate` to raise on call. `resolve_intent("Marketing", "Indiana University-Bloomington", 151351, programs=[{"cipcode": "52.01", ...}, {"cipcode": "52.10", ...}])` returns `matched_cip="52.14"`, `confidence="high"`, `reasoning` mentions YAML. Audit may still call Gemma — patch it separately to return `None` (audit quiets silently). |
| P0 | `backend/tests/services/test_intent.py` | `TestDeterministicShortCircuit::test_parent_cip_set_when_school_reports_broad_family` | Same Marketing-at-IU fixture. Assert `parent_cip == "52.01"` (non-empty). This is the frontend's "substitution will apply" signal — regression here re-introduces the confirm-card-lies bug. |
| P0 | `backend/tests/services/test_intent.py` | `TestDeterministicShortCircuit::test_parent_cip_empty_when_school_reports_specific_cip` | A programs list containing `{"cipcode": "52.14", ...}` directly (i.e. the school reports Marketing as its own program). `resolve_intent("Marketing", ...)` returns `parent_cip == ""` — no substitution needed. |
| P0 | `backend/tests/services/test_intent.py` | `TestDeterministicShortCircuit::test_parent_cip_empty_when_no_same_family_broad` | Programs list in a different family (e.g. `[{"cipcode": "11.07", ...}]`). `resolve_intent("Marketing", ...)` returns `parent_cip == ""` — outcomes path will handle the miss via broadening. |
| P0 | `backend/tests/services/test_intent.py` | `TestDeterministicShortCircuit::test_alias_match_skips_gemma` | `resolve_intent("mktg", ...)` (an alias for Marketing) hits the short-circuit too. |
| P0 | `backend/tests/services/test_intent.py` | `TestDeterministicShortCircuit::test_unknown_major_falls_through_to_gemma` | `resolve_intent("Underwater basket weaving", ...)` skips the short-circuit. Assert `gemma_client.generate` is called. |
| P0 | `backend/tests/services/test_intent.py` | `TestDeterministicShortCircuit::test_short_circuit_does_not_write_cache` | After a short-circuit hit, `intent._intent_cache` must not contain the `(normalized_major, unitid)` key. Cache writes are owned by `confirm_intent`; the short-circuit must match that invariant. |
| P0 | `backend/tests/services/test_major_lookup.py` | `TestLookupMajor::test_exact_major_match` / `test_alias_match` / `test_case_insensitive` / `test_empty_input_returns_none` / `test_unknown_returns_none` | Standard coverage of `lookup_major`. |
| P0 | `backend/tests/services/test_major_lookup.py` | `TestLookupMajor::test_path_resolution_is_cwd_independent` | Run the same lookup from two different cwds (via `monkeypatch.chdir`). Assert identical results. Guards against regression on the `__file__`-walking path resolution. |
| P1 | `backend/tests/services/test_intent.py` | `TestDeterministicShortCircuit::test_short_circuit_runs_audit` | Confirm the audit call still fires after the short-circuit (so `audit_flag` and `audit_message` propagate). |
| P1 | `backend/tests/services/test_major_lookup.py` | `TestCrossModuleConsistency::test_matches_find_major_intent_for_every_yaml_entry` | Parametrized across every entry in `data/reference/major_to_cip.yaml`. For each entry's `major` and each `alias`, assert `major_lookup.lookup_major(text)["cip4"] == FutureProofMCPServer._find_major_intent(text)["cip4"]`. Catches drift between the two copies of the matching semantics. |
| P1 | `tests/mcp/test_cip_substitution.py` | `TestStandardPath::test_padded_specific_cip_normalizes` | `_handle_get_career_paths(unitid=151351, cipcode="52.1000", student_major=None)` (HR padded to 6 digits) returns IU's HR rows from `program_career_paths`. Validates the standard-path normalization. |
| P2 | `backend/tests/services/test_intent.py` | `TestPromptCopy::test_prompt_does_not_bias_toward_school_cips` | After @fp-copywriter rewrites the prompt, snapshot-test the system-prompt body to flag accidental regressions toward the old "earnings data" framing. Lightweight string assertion. |

#### Test Data Requirements

- **MCP unit tests** reuse the existing in-test stubs in `tests/mcp/test_cip_substitution.py` (mock `query_iceberg_simple` returning the fixed IU 52.01 row + 52.14 crosswalk SOCs). No new fixtures needed.
- **MCP integration tests** depend on `data/futureproof.duckdb` / Iceberg warehouse being populated for `unitid=151351`. Existing `tests/mcp/test_cip_substitution_integration.py` already documents this (see top-of-file fixtures).
- **Intent service tests** need `gemma_client.generate` patched at the module level. Use `monkeypatch.setattr("backend.app.services.intent.gemma_client.generate", ...)`. The audit step also calls `gemma_client.generate` — patch it to return `None` (drops audit silently per existing fallback at line 229).
- **`major_lookup` tests** are cwd-independent — the module walks upward from `__file__` to find the YAML. Tests can run from `backend/` cwd (backend pytest) or repo root (root pytest) with identical behavior. If a test needs to exercise the "YAML missing" branch, use `monkeypatch.setattr("app.services.major_lookup._yaml_path", lambda: None)` and clear the `_load` cache (`app.services.major_lookup._load.cache_clear()`) in the same test's setup/teardown.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-04-18

#### System Context

Scope touches two modules on the read path from `/build/outcomes` and `/intent`:
1. `src/mcp_server/futureproof_server.py::FutureProofMCPServer._handle_get_career_paths` — the MCP tool invoked by `compute_pentagon` after intent resolution. Reads Gold-zone `consumable.career_outcomes` and `consumable.program_career_paths` to assemble the substituted-rows payload when a school reports a broad XX.01 CIP.
2. `backend/app/services/intent.py::resolve_intent` — the Gemma-mediated mapper from free-text major to CIP, sitting between `POST /intent/` and the MCP query. Currently unconditionally delegates to Gemma; the spec proposes a deterministic YAML short-circuit before the Gemma call.

No Iceberg schema changes. No new endpoints. No new Pydantic models. Data-flow diagram: frontend -> `/intent/` -> `resolve_intent` -> (short-circuit OR Gemma) -> audit -> `IntentResult` -> frontend -> `/build/outcomes` -> `compute_pentagon` -> MCP `_handle_get_career_paths` -> substituted-rows path -> Gold tables.

#### Data Flow Analysis

**CIP granularity boundary (Bug A).** `consumable.career_outcomes` and `consumable.program_career_paths` are canonically 4-digit (XX.XX) per `governance/reviews/raw-ingest-college-scorecard-institution-gold-cab-review.md:93` and the Silver `normalize_cipcode()` path documented at `governance/reviews/silver-architecture-review.md:170`. Callers cross this boundary from three directions:
- Gemma output: may emit either 4- or 6-digit forms depending on prompt framing.
- Frontend confirm flow: echoes whatever was persisted (may be zero-padded 6-digit).
- YAML lookup: `major_to_cip.yaml` stores `cip4` as 4-digit, but the `_find_major_intent` caller may already have received a 6-digit code from the intent step.

`_canonical_cip4(cipcode: str) -> str` returning `cipcode[:5] if len(cipcode) >= 5 else cipcode` correctly projects all three input shapes onto the 4-digit key that matches the tables. Verified:
- `"52.01"` (len 5) -> `"52.01"` ✓
- `"52.0100"` (len 7) -> `"52.01"` ✓
- `"52.0101"` (len 7) -> `"52.01"` ✓
- `"52.1401"` (len 7) -> `"52.14"` ✓
- `""` -> `""` ✓ (early-return branch)

**Line-number verification against `main` at commit 1a12aca.** The spec's cited line numbers are accurate:
- L1541: `filters={"unitid": unitid, "cipcode": reported_cipcode}` inside `_build_substituted_rows` ✓
- L1860: `str(r.get("cipcode", "")) == cipcode` inside `_fallback_gemma_soc_resolution` ✓
- L2139: `filters={"unitid": unitid_value, "cipcode": cipcode}` in the standard-path `CAREER_PATHS_TABLE` query ✓
- L2181: `filters={"unitid": unitid_value, "cipcode": cipcode}` in the Gemma-SOC-fallback `CAREER_OUTCOMES_TABLE` program-name lookup ✓

**Missed call site.** The spec enumerates four filter sites to canonicalize, but there is a fifth at line 1749 inside `_fallback_broaden_cip` (Attempt 2, general-CIP-for-family match): `str(r.get("cipcode", "")) == general_cip` where `general_cip = f"{family}.0100"`. Because the tables hold 4-digit cipcodes, this equality can *never* match today — it's latent dead code, but it will stay dead after this fix. The spec should either canonicalize `general_cip` to `f"{family}.01"` for consistency with the same normalization rule, or explicitly call out that this branch is known-dead and deferred. Not a blocker for this bugfix, but worth a sentence in §4 so the next reader doesn't introduce a contradiction.

**`_BROAD_CIP_PATTERN` interaction (the risk the spec flags).** The regex `^\d{2}\.01(00)?$` at L245 intentionally accepts both 4-digit (`52.01`) and zero-padded 6-digit (`52.0100`) forms but rejects specific 6-digit (`52.0101`). This is correct: `52.0101` is a *specific* program in the broad family, and the substitution flow shouldn't fire on it as a "broad" CIP — it's genuinely narrow. That invariant survives the canonicalization because `_is_broad_cip` is called on the *raw* caller input (L2034), before any canonicalization. The proposed canonicalization only happens at the table-filter sites downstream. Data flow preserved.

However: success criterion 2 at L84 claims `cipcode="52.0101"` with `student_major="Marketing"` should return the substituted Marketing rows. Trace that: `_is_broad_cip("52.0101")` returns `False`, so the substitution branch at L2031–L2076 does NOT fire. The student would fall through to the standard path (with canonicalized cipcode `"52.01"`), which would then find IU's 52.01 row in `program_career_paths` and return Business-General careers. The student would not get Marketing careers. That success criterion contradicts the code. Either the criterion is wrong or `_is_broad_cip` needs a widened regex. The spec's Decision #1 Alternative (b) explicitly says loosening the regex is rejected, so the success criterion is the defect.

#### Contract Review

**`IntentResult.parent_cip` contract — load-bearing for the frontend.** `frontend/src/components/school/MajorInput.tsx:102` reads:
```ts
substitutionApplied: override ? false : intentResult.parent_cip !== "",
```
This is the signal the frontend uses to decide whether to render the "substitution" affordance on the major-confirm card. The proposed short-circuit hardcodes `parent_cip=""` at §4 L289. For the exact scenario this spec targets (Marketing at IU), the short-circuit will return `matched_cip="52.14", parent_cip=""` — the frontend will display "no substitution" even though the backend will substitute on the subsequent `/build/outcomes` call. That's a user-visible contract drift: the confirm card lies about what the outcomes screen will show.

The short-circuit must populate `parent_cip` correctly. `resolve_intent` already receives `programs: list[dict]` (the school's reported programs); walk it to find a reported cipcode whose 2-digit family matches the YAML's `cip4` family and is broader than `cip4`. If found, set `parent_cip` to that reported cipcode (canonicalized to 4-digit). If the school reports the exact `cip4` directly, leave `parent_cip=""`. Matches the behavior of the Gemma path. Keep the logic tight — don't re-query Iceberg, just iterate `programs`.

**Caveat `reported_cipcode` shape.** The spec claims the frontend doesn't consume `data_caveat.reported_cipcode`. Verified: all six `reported_cipcode` hits in `frontend/src/screens/` and `frontend/src/components/` are in `.test.tsx` files; the only non-test reference is the type declaration at `frontend/src/types/build.ts:78–80` and the mock at `frontend/src/api/mockBuild.ts:69,94`. No component branches on it. Setting `reported_cipcode` to the canonical 4-digit form is safe. Note that this is the top-level `reported_cipcode` on the response payload (L2127, L2171, L2202), not the caveat-dict field at L2116 — the spec conflates the two at §4 L253. Recommend the fix sets *both* to the canonical form so a future UI consumer sees one value regardless of where it reads.

**Cache coherence with the short-circuit.** The cache at L328 returns an `IntentResult` that omits `audit_flag` and `audit_message`. The short-circuit computes fresh audit results every call. This is a pre-existing asymmetry (the Gemma path also doesn't persist audit flags into the cache) — the short-circuit should follow the same rule: on short-circuit hit, don't write to `_intent_cache` unless the caller goes through `confirm_intent`. The spec's proposed block doesn't touch the cache, which is correct, but make it explicit in §4 so the next reader doesn't "optimize" by adding a cache write.

**Audit step invariant preserved.** The proposed short-circuit at §4 L267 still calls `_audit_intent_mapping` after the YAML hit. That's correct and matches the `cip-intent-substitution.md` contract that "audit runs on every mapping." Good.

**`major_lookup.py` import boundary.** The new module imports only `pathlib`, `typing`, `yaml`. No import from `src/mcp_server/` — correct, avoids the circular dependency that would form if `intent.py` pulled `FutureProofMCPServer._find_major_intent`. The duplication of matching semantics between `major_lookup.lookup_major` and `FutureProofMCPServer._find_major_intent` (L1446-1464) is acceptable because both read the same YAML file with the same case-insensitive major+alias match. If the logic drifts the symptom will be "intent says one cip, MCP says another" — add a test in §4 that asserts `major_lookup.lookup_major("Marketing") == FutureProofMCPServer._find_major_intent("Marketing")` as a cross-module consistency check.

**`PROJECT_ROOT` fallback.** The spec mirrors the MCP server's pattern (L1422-1425): try `from brightsmith.config import PROJECT_ROOT`, else `Path.cwd()`. That fallback is fragile — backend pytest runs from `backend/` cwd, so `Path.cwd() / "data/reference/major_to_cip.yaml"` won't resolve. The MCP server gets away with it because tests always run from repo root via `uv run pytest`. The new backend-side module needs a harder fallback: walk upward from `__file__` looking for `data/reference/major_to_cip.yaml`, matching the pattern used elsewhere in the backend (e.g. `backend/app/services/school_lookup.py` if it solves this same problem — verify before implementing).

#### Findings

##### Sound
- `_canonical_cip4` projection logic is correct for all five input shapes and mirrors the existing `cipcode[:5]` pattern used at L1717 and L163. Single helper, single rule, minimal surface.
- Decision Log Decision #1 (canonicalize at the filter site, not upstream) respects the zone boundary: Gold is 4-digit, callers are allowed to be sloppy, normalization happens at the read seam.
- Decision Log Decision #2 (audit all four — now five — call sites) is the right instinct. Patching only one is how latent bugs survive.
- Decision Log Decision #3 short-circuit rationale is sound: YAML is the source of truth for the major-to-cip mapping, Gemma is a fallback for YAML misses. The substitution flow is deterministic anyway; Gemma was only in the way.
- `major_lookup.py` has no circular-import risk and follows the existing YAML caching pattern. Sensible module boundary.
- Substitution caveat shape unchanged. The frontend grep confirms no component consumes `reported_cipcode` today; the field change is safe.
- Existing test suite is accurately classified. None of the "Confirmed Safe" tests exercise 6-digit inputs; `_canonical_cip4("52.01") == "52.01"` is a no-op for them.
- Testing Impact Analysis correctly identifies `TestSchoolRowMissing::test_missing_school_row_returns_null` as the one test that may need a string update because the error message now canonicalizes.

##### Concerns

- **`IntentResult.parent_cip` contract drift on short-circuit (frontend-visible).** `MajorInput.tsx:102` reads `parent_cip !== ""` as the "substitution will be applied" signal. The proposed short-circuit always returns `parent_cip=""`. For Marketing-at-IU the confirm card will say "no substitution" while the outcomes screen substitutes. **Impact:** User sees contradictory copy between the major-confirm card and the career-pick screen. **Recommendation:** In the short-circuit, iterate the `programs` argument to find a reported cipcode in the same 2-digit family as the YAML `cip4`. If one exists and is broader (i.e., reported is `XX.01` and YAML is `XX.YY` with `YY != "01"`), set `parent_cip` to the reported cipcode (4-digit canonical). Otherwise `""`. Matches the Gemma-path semantics.

- **Success criterion 2 (cipcode="52.0101") contradicts `_is_broad_cip`.** `_BROAD_CIP_PATTERN = ^\d{2}\.01(00)?$` rejects `"52.0101"`, so substitution will not fire for that input and the criterion is not satisfiable without widening the regex — which the spec explicitly rejects in Decision #1 Alternative (b). **Impact:** The test `TestIntegrationLikePath::test_specific_six_digit_broad_cip_still_substitutes` will fail against the code the spec authorizes. **Recommendation:** Remove the criterion at §1 L84 and drop the matching P0 test at §4 L331. Replace with a criterion/test that asserts the opposite: `cipcode="52.0101"` with `student_major="Marketing"` falls through to the standard path and returns whatever 52.0101 maps to (likely triggers `_fallback_broaden_cip` because no school reports 52.0101 for Marketing). Document the reasoning so a future reader understands why 52.0101 is different from 52.0100.

- **Fifth filter site missed in §4 (`_fallback_broaden_cip` L1749).** The comparison `str(r.get("cipcode", "")) == general_cip` with `general_cip = f"{family}.0100"` cannot match any 4-digit row. Pre-existing latent dead code. **Impact:** Fix doesn't cause a regression, but leaves the next reader confused about whether L1749 intentionally opts out of canonicalization or was simply missed. **Recommendation:** Either change the comparison to use the canonical form (`general_cip = f"{family}.01"` and skip the loop on already-handled 4-digit prefix match), or add a one-line comment at L1745 stating the Attempt 2 branch is known-dead and intentionally not canonicalized. Tracking the deletion is out of scope; one sentence in §4 is enough.

- **`reported_cipcode` dual-location canonicalization.** §4 L253 says "update the error message at line 1549 to surface the canonical form" and describes setting the caveat's `reported_cipcode` to 4-digit. The actual response payload has `reported_cipcode` in TWO places: the top-level response dict (L2127) and the caveat dict (L2116). The spec should explicitly call out both. **Impact:** If only the caveat is updated, the top-level field still echoes the raw caller input, and a future UI that reads the top-level field sees non-canonical data. **Recommendation:** Update §4 Service Changes to say "set `reported_cipcode` to the canonical form at BOTH L2116 (caveat) and L2127 (response root)." Single source of truth, no ambiguity.

- **`PROJECT_ROOT` fallback in `major_lookup.py`.** `Path.cwd()` fails when pytest runs from `backend/`. **Impact:** `lookup_major` returns `None` for every input under backend tests that don't chdir, meaning the short-circuit silently never fires in the test suite. **Recommendation:** Use an anchored path discovery: walk up from `Path(__file__).resolve().parents` looking for a directory containing `data/reference/major_to_cip.yaml`. Cache the discovered root on first call. This also fixes the `monkeypatch.chdir(repo_root)` fixture requirement the spec punts on at §4 L346.

- **Cross-module consistency between `lookup_major` and `_find_major_intent`.** Two copies of the same matching semantics across module boundaries. **Impact:** Low today; non-zero long-term as the matching logic evolves (normalization rules, fuzzy matching, ranked alias priority). **Recommendation:** Add a single parametrized test that asserts `major_lookup.lookup_major(x) == FutureProofMCPServer._find_major_intent(x)` across the full YAML entry list. One test, one file, catches drift cheaply. Add to the P1 section.

- **Cache-write policy on short-circuit must be explicit.** Short-circuit path does not write to `_intent_cache`. That is correct (same behavior as the Gemma path — only `confirm_intent` writes). **Impact:** None today, but undocumented invariants get "optimized away" in later specs. **Recommendation:** Add a single-line comment in the proposed block: `# Do not write to _intent_cache here — confirm_intent owns writes.` Make the invariant visible to the next reader.

- **Test file already exists.** §4 File Changes table labels `backend/tests/services/test_intent.py` as "Create." It exists on `main` (20,152 bytes, covers the Gemma tiered path). **Impact:** Mislabeled action will cause @test-writer to either overwrite or get confused. **Recommendation:** Change action from "Create" to "Modify" and explicitly state the new `TestDeterministicShortCircuit` class is *appended* to the existing file.

##### Blockers

None. The architecture is fundamentally correct — a normalization helper applied at the table-filter seam is exactly the right shape for Bug A, and the YAML short-circuit is exactly the right shape for Bug B. Every concern above is a refinement, not a rewrite.

#### Verdict (v1.0)
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

#### Conditions (CHANGES REQUESTED)

1. Remove success criterion 2 at §1 L84 (`cipcode="52.0101"`) and the matching P0 test at §4 L331. `_is_broad_cip` does not match `52.0101` and the spec explicitly rejects widening the regex. Replace with a criterion that documents the expected standard-path behavior for specific 6-digit non-broad CIPs.
2. Rewrite the short-circuit block at §4 L262–L290 to populate `parent_cip` by walking the `programs` argument for a broader reported cipcode in the same 2-digit family. Add a test asserting `parent_cip` is non-empty for Marketing-at-IU (so `MajorInput.tsx:102` renders the substitution affordance correctly) and empty when the YAML `cip4` equals the school's reported cipcode.
3. Expand §4 Service Changes to explicitly canonicalize `reported_cipcode` in both locations: the caveat dict (L2116) and the top-level response (L2127). Similarly for the broadened-rows response at L2171 and the Gemma-SOC-fallback response at L2202 — audit all four response sites, not just the caveat.
4. Add the fifth filter site (`_fallback_broaden_cip` L1749) to the canonicalization audit, or add a single-sentence note in §4 explaining why that branch is intentionally skipped (it's known-dead due to the 4-digit storage invariant).
5. Change `backend/tests/services/test_intent.py` action from "Create" to "Modify" in the §4 File Changes table. Note that new `TestDeterministicShortCircuit` and `TestPromptCopy` test classes are appended to the existing file.
6. Update `major_lookup.py` pseudocode in §4 to resolve the YAML path by walking upward from `Path(__file__).resolve().parents` rather than relying on `Path.cwd()`. Update §4 Test Data Requirements to remove the `monkeypatch.chdir(repo_root)` caveat, since the module will now be cwd-independent.
7. Add a P1 cross-module consistency test asserting `major_lookup.lookup_major(x) == FutureProofMCPServer._find_major_intent(x)` for every entry in `major_to_cip.yaml`.
8. Add an inline comment in the short-circuit block noting that it deliberately does not write to `_intent_cache` (writes are owned by `confirm_intent`).

#### Revision Response (v1.1, 2026-04-18)

All eight conditions addressed. Pointers to the revised sections below; awaiting re-review verdict.

| # | Condition (summary) | Addressed in | How |
|---|--------------------|--------------|------|
| 1 | Drop success criterion 2 (`52.0101` substitutes) and matching P0 test. | §1 Success Criteria, §4 New Tests Required | Criterion rewritten to assert `52.0101` canonicalizes to `52.01`, falls through to standard path, and lands in the deterministic broadening fallback. Matching P0 test renamed to `test_specific_six_digit_does_not_substitute` with inverted expectations. |
| 2 | Short-circuit must populate `parent_cip` from `programs`. | §4 Service Changes (short-circuit block + new `_derive_parent_cip` helper), §1 Success Criteria, §4 New Tests Required | Added `_derive_parent_cip(cip4, programs)` helper; short-circuit calls it instead of hardcoding `""`. Three new P0 tests pin behavior: broader-family hit, exact-cip4 reported (no substitution), different-family programs (no substitution). |
| 3 | Canonicalize `reported_cipcode` at all four response sites, not just the caveat. | §4 Service Changes (new dedicated table: L2116 caveat, L2127 substitution-root, L2171 broadened-rows, L2202 Gemma-SOC-fallback) | Dual-location ambiguity removed. File Changes table updated. |
| 4 | Fifth filter site (`_fallback_broaden_cip` L1749). | §4 Service Changes (explicit "known-dead, deferred" note), File Changes table | Documented as pre-existing dead code; this spec adds a one-line comment at L1745 and explicitly does not change the L1749 comparison. |
| 5 | `test_intent.py` action: Create → Modify. | §4 File Changes table | Changed to `Modify`; called out that new `TestDeterministicShortCircuit` / `TestPromptCopy` classes are appended to the existing file. |
| 6 | `major_lookup.py` path resolution must be cwd-independent. | §4 Service Changes (new `major_lookup.py` module code), §4 Test Data Requirements | Rewrote path resolution to walk upward from `Path(__file__).resolve().parents`; `@lru_cache` on both the path finder and the loader. Test Data Requirements updated — `monkeypatch.chdir` caveat removed. |
| 7 | Cross-module consistency test (`lookup_major` vs `_find_major_intent`). | §4 New Tests Required | Added P1 `TestCrossModuleConsistency::test_matches_find_major_intent_for_every_yaml_entry`, parametrized across the full YAML. |
| 8 | Inline comment: short-circuit does not write to `_intent_cache`. | §4 Service Changes (short-circuit block docstring-comment), §4 New Tests Required | Cache-policy paragraph in the block-comment prefix; added P0 test `test_short_circuit_does_not_write_cache` so the invariant is executable, not just documented. |

#### Re-review (v1.1)
**Status:** APPROVED
**Reviewed:** 2026-04-18

Targeted diff review against the eight v1.0 conditions. Each verified in spec text (not just claimed in the response table) and traced through the relevant scenarios.

| # | Condition | Verified In | Status |
|---|-----------|-------------|--------|
| 1 | Drop unsatisfiable `52.0101` substitutes criterion + matching P0 test | §1 L86 (criterion inverted to "does NOT substitute, falls through to broadening fallback"), §4 L424 (P0 renamed `test_specific_six_digit_does_not_substitute` with broadened-rows caveat shape, not `blended_substitution`) | Met |
| 2 | Short-circuit populates `parent_cip` from `programs` | §4 L308 (call), §4 L339–L383 (`_derive_parent_cip` helper), §1 L87/L89 (criteria), §4 L427–L429 (three P0 tests) | Met — see trace below |
| 3 | Canonicalize `reported_cipcode` at all four response sites | §4 L271–L276 (explicit table: caveat L2116, substitution-root L2127, broadened-rows L2171, Gemma-SOC-fallback L2202), File Changes row L150 | Met |
| 4 | Fifth filter site `_fallback_broaden_cip` L1749 — note or canonicalize | §4 L280 (explicit "known-dead, intentionally skipped" paragraph; one-line comment to be added at L1745; comparison itself unchanged), File Changes row L150 | Met |
| 5 | `test_intent.py` Create → Modify | §4 File Changes L153 (action="Modify"; APPEND `TestDeterministicShortCircuit` / `TestPromptCopy`; existing tests untouched) | Met |
| 6 | `major_lookup.py` path resolution cwd-independent | §4 L200–L210 (`_yaml_path()` walks `Path(__file__).resolve().parents`, `@lru_cache(maxsize=1)`); §4 L445 (Test Data Requirements rewritten — `monkeypatch.chdir` caveat removed); §4 L434 (`test_path_resolution_is_cwd_independent`) | Met |
| 7 | Cross-module consistency test (`lookup_major` vs `_find_major_intent`) | §4 L436 (P1 `TestCrossModuleConsistency::test_matches_find_major_intent_for_every_yaml_entry`, parametrized across full YAML, asserts on `cip4` from both sides) | Met |
| 8 | Short-circuit must not write `_intent_cache`; invariant explicit | §4 L300–L303 (block-comment "Cache policy" paragraph), §4 L432 (executable P0 `test_short_circuit_does_not_write_cache`) | Met — invariant is both documented and tested |

##### `_derive_parent_cip` trace verification

The helper is the load-bearing piece of the revision; traced against all three target scenarios from the v1.0 review:

1. **Marketing-at-IU broad-family hit.** `cip4="52.14"`, `programs=[{"cipcode": "52.01"}, {"cipcode": "52.10"}]`.
   - `family="52"` (isdigit) ✓.
   - Iter "52.01": canonical `"52.01"`, not equal `cip4`, family matches, `raw == f"{family}.01"` → append.
   - Iter "52.10": canonical `"52.10"`, not equal, family matches, `raw not in ("52.01", "52.0100")` → skip.
   - Returns `"52.01"`. **Correct** — frontend's `MajorInput.tsx:102` substitution affordance lights up as required.
2. **Marketing at a school reporting 52.14 directly.** `cip4="52.14"`, `programs=[{"cipcode": "52.14"}]` (or zero-padded `"52.1401"`).
   - Iter "52.14": canonical `"52.14"`, equals `cip4` → early return `""`.
   - Iter "52.1401" variant: canonical `"52.14"`, equals `cip4` → early return `""`. **Correct** — no false-positive substitution affordance.
3. **No-match family.** `cip4="52.14"`, `programs=[{"cipcode": "11.07"}]`.
   - Iter "11.07": family "11" != "52" → skip.
   - Returns `""`. **Correct** — outcomes path handles via existing broadening fallback.

Subtle but important: the broadness check at L381 uses `raw` (not `canonical`), which intentionally mirrors `_BROAD_CIP_PATTERN`. A school program reported as `"52.0101"` would canonicalize to `"52.01"` but would **not** match `f"{family}.01"` or `f"{family}.0100"`, so it correctly fails to qualify as a substitution parent. Defensive guard at L366 (`family.isdigit()`) handles malformed cipcodes. `or ""` coercion at L370 handles `None` cipcode values from missing keys. Helper is tight and correct.

##### Other revision-quality observations

- The criterion at §1 L86 explicitly documents *why* `52.0101` is intentionally not broad (Decision #1 Alt (b) cross-reference). Future readers won't relitigate the regex.
- §4 L280 doesn't just note the dead branch — it actively forbids implementers from "fixing" L1749 within this spec's scope ("implementers must not silently change the comparison as part of this spec"). Good defensive boundary.
- The cache-policy invariant is now both *documented* (block comment) and *executable* (P0 test). Either alone would be brittle; both together make it a contract.
- `_load()` cache + `_yaml_path()` cache layering is correct: `_load` depends on `_yaml_path`, both `lru_cache(maxsize=1)`. Test Data Requirements at L445 correctly notes both caches must be cleared together when stubbing the missing-YAML branch.

##### Findings

###### Sound (delta)
- All eight v1.0 conditions met, in spec text, with the right shape.
- `_derive_parent_cip` correctly mirrors `_BROAD_CIP_PATTERN` semantics by checking `raw` rather than `canonical` when deciding broadness — this is the right call.
- New criterion at §1 L86 and matching test at L424 form a coherent pair: both document the standard-path-with-broadening-fallback behavior for specific 6-digit CIPs.
- Cache invariant is now executable (L432), not just commented. Future-proof.

###### Concerns (delta)
None. No new concerns introduced by the revision; no v1.0-missed concerns surfaced on re-read.

###### Blockers
None.

#### Verdict (v1.1)
- [x] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

Implementation may proceed. The architecture is clean, the contracts hold, the zone boundaries are honest, and the revision lands every v1.0 condition without introducing new ones.

### @fp-data-reviewer Review
**Status:** SKIPPED (no pipeline / stat-formula / crosswalk changes — only lookup mechanics on existing tables)

---

## §6 Implementation Log

**Status:** CODE COMPLETE (tests deferred to @test-writer in step 4; prompt body deferred to @fp-copywriter in step 3)

### Files Modified
| File | Change Summary |
|------|---------------|
| `backend/app/services/major_lookup.py` | Created. `lookup_major(text) -> MajorEntry \| None` backed by cwd-independent YAML discovery (walks up from `__file__` with `@lru_cache`). Matches case-insensitively against `major` and every `alias`. |
| `src/mcp_server/futureproof_server.py` | Added `_canonical_cip4(cipcode) -> str` static helper after `_cip_family` (new ~line 1491). Applied canonicalization at all four filter sites: `_build_substituted_rows` (L1541 + error message), `_fallback_gemma_soc_resolution` (L1860), standard-path `CAREER_PATHS_TABLE` filter (L2157), Gemma-SOC-fallback program-name lookup (L2199). Canonicalized `reported_cipcode` at all four response sites: substitution caveat, substitution response root, broadened-rows response root, Gemma-SOC-fallback response root. Added dead-code note at L1745 for the `_fallback_broaden_cip` Attempt-2 branch (intentionally left alone per §4). |
| `backend/app/services/intent.py` | Added `Sequence`/`Mapping` imports. Added `_derive_parent_cip(cip4, programs)` helper above `resolve_intent` — walks `programs` for a same-family broad CIP (`XX.01` / `XX.0100`) while rejecting specific-CIP forms (`XX.0101`). Inserted the deterministic YAML short-circuit after the cache check: on a `major_lookup.lookup_major` hit, resolve `cip4`, derive `parent_cip`, promote to 6-digit leaf via the existing `_promote_to_leaf_cip` (using `_get_school_cips` for parity with the Gemma path), run audit, return `IntentResult(confidence="high", reasoning="Deterministic match from major_to_cip.yaml.")`. Deliberately no cache write. Prompt body (`_INTENT_SYSTEM_PROMPT`) intentionally NOT touched — handed off to @fp-copywriter in step 3. |

### Deviations from Spec

| # | Deviation | Why |
|---|-----------|------|
| 1 | Short-circuit calls `_promote_to_leaf_cip(cip4, parent_cip, _get_school_cips(unitid))` in addition to `_derive_parent_cip`. The spec's proposed block returned the YAML's `cip4` unpromoted. | Caught during step-2 verification: `test_resolve_intent_falls_back_to_school_catalog_descendant` regressed because `major_to_cip.yaml` stores several entries with 4-digit family codes (e.g. "Special Education" → `13.10`). The Gemma path promotes 4-digit umbrellas to 6-digit leaves via `_promote_to_leaf_cip` using the school's catalog; the short-circuit must do the same to keep parity. Called `_get_school_cips(unitid)` rather than reusing `programs` because the existing test fixture monkey-patches the MCP server (not the `programs` arg), and that's also the canonical source the Gemma path uses. `_derive_parent_cip` still operates on `programs` because its contract is strictly about what the frontend surfaced. |
| 2 | `_derive_parent_cip(cip4: str, programs: Sequence[Mapping[str, Any]]) -> str` instead of the spec's `list[dict]`. | mypy strict mode flagged the bare `list[dict]` as a new `type-arg` error. Using `Sequence[Mapping[str, Any]]` is covariant and accepts `list[dict]` at call sites without forcing a change to `resolve_intent`'s signature — smallest possible change. |
| 3 | `major_lookup.py` imports yaml with `# type: ignore[import-untyped]`. | `types-PyYAML` is not installed in the backend venv; `src/mcp_server/futureproof_server.py` doesn't hit this because it's outside the backend mypy scope. Adding the dep was out of scope for this bugfix. |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | REGRESSION in `test_resolve_intent_falls_back_to_school_catalog_descendant` | Short-circuit skipped `_promote_to_leaf_cip` — YAML entries with 4-digit family codes (e.g. `Special Education` → `13.10`) were returned unpromoted, losing parity with the Gemma path. | Added `_promote_to_leaf_cip(cip4, parent_cip, _get_school_cips(unitid))` call inside the short-circuit before the audit step. See Deviation #1. |
| 2 | PASS — backend 370/370, substitution suites 26/26. Pipeline: 2 pre-existing failures (`debt_p25`) confirmed on clean main via `git stash` reproduction; unrelated to this spec. | n/a | n/a |

### Verification Summary (pre-step-4)

| Suite | Command | Result |
|-------|---------|--------|
| Backend ruff | `cd backend && ruff check .` | All checks passed |
| Backend mypy | `cd backend && mypy app/` | 46 errors (baseline was 47; my changes net-reduced by 1 via `Sequence`/`Mapping` typing in `_derive_parent_cip` and `cast` + `# type: ignore[import-untyped]` in `major_lookup.py`) |
| Backend pytest | `cd backend && pytest` | 370 passed, 0 failed |
| Pipeline ruff | `uv run ruff check src/ tests/` | 23 errors, all pre-existing on main; nothing new in files I touched (pre-existing E402 imports predate this spec) |
| Pipeline pytest | `uv run pytest` | 1669 passed, 2 failed. Both failures (`test_get_career_paths.py::TestValidLookup::test_response_contains_all_fields`, `test_get_school_programs.py::TestResponseShape::test_response_contains_all_expected_fields` — both about a missing `debt_p25` field) reproduce on clean main with my changes stashed. Unrelated to this spec. Flag for pre-existing pipeline tracking. |
| Substitution focus | `uv run pytest tests/mcp/test_cip_substitution.py tests/mcp/test_cip_substitution_integration.py` | 26 passed. Every Confirmed-Safe test in §4 Testing Impact Analysis passed without modification. |

---

## §7 Test Coverage

**Status:** COMPLETE

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|
| `backend/tests/services/test_major_lookup.py` | `TestLookupMajor::test_exact_major_match` | Exact YAML `major` name returns the entry with the expected `cip4`. |
| `backend/tests/services/test_major_lookup.py` | `TestLookupMajor::test_alias_match` | Alias string (e.g. `mktg` → Marketing) returns the owning entry. |
| `backend/tests/services/test_major_lookup.py` | `TestLookupMajor::test_case_insensitive` | Mixed-case major AND alias inputs hit the same entry — guards the Bug B failure mode (caps lock / shorthand variants falling through to Gemma). |
| `backend/tests/services/test_major_lookup.py` | `TestLookupMajor::test_empty_input_returns_none` | Empty / whitespace / `\t\n` inputs return None rather than silently matching the first entry. |
| `backend/tests/services/test_major_lookup.py` | `TestLookupMajor::test_unknown_returns_none` | Out-of-coverage inputs (`"Underwater basket weaving"`, `"asdfghjkl"`) return None — forces fall-through to Gemma. |
| `backend/tests/services/test_major_lookup.py` | `TestLookupMajor::test_path_resolution_is_cwd_independent` | Invokes `lookup_major` from two distinct cwds (tmp_path + repo root) with both lru_caches cleared in between; asserts identical hit. Regression guard for the `Path.cwd()` variant explicitly rejected in §5 Condition #6. |
| `backend/tests/services/test_major_lookup.py` | `TestCrossModuleConsistency::test_matches_find_major_intent_for_every_yaml_entry` | P1, **204 parametrized cases** covering every (entry, major\|alias) pair in `major_to_cip.yaml`. Asserts `lookup_major` and `FutureProofMCPServer._find_major_intent` agree on `cip4` for every input. Drift guard. |
| `backend/tests/services/test_intent.py` | `TestDeterministicShortCircuit::test_marketing_skips_gemma` | P0. Patches `gemma_client.generate` to raise — asserts it was never called for `"Marketing"` at IU. Matches on `cip4=52.14`, `confidence=high`, reasoning mentions YAML. |
| `backend/tests/services/test_intent.py` | `TestDeterministicShortCircuit::test_parent_cip_set_when_school_reports_broad_family` | P0. Marketing-at-IU (`programs=[52.01, 52.10]`) → `parent_cip=52.01`. Regression guard for the confirm-card-lies bug (§5 Condition #2). |
| `backend/tests/services/test_intent.py` | `TestDeterministicShortCircuit::test_parent_cip_empty_when_school_reports_specific_cip` | P0. School reports `52.14` directly → `parent_cip=""`. No false-positive substitution affordance. |
| `backend/tests/services/test_intent.py` | `TestDeterministicShortCircuit::test_parent_cip_empty_when_no_same_family_broad` | P0. Programs in a different family (11.07, 14.01) → `parent_cip=""`. Outcomes path will handle via broadening fallback. |
| `backend/tests/services/test_intent.py` | `TestDeterministicShortCircuit::test_alias_match_skips_gemma` | P0. `"mktg"` triggers the short-circuit identically to `"Marketing"`. |
| `backend/tests/services/test_intent.py` | `TestDeterministicShortCircuit::test_unknown_major_falls_through_to_gemma` | P0. `"Underwater basket weaving"` reaches Gemma (call_log non-empty). |
| `backend/tests/services/test_intent.py` | `TestDeterministicShortCircuit::test_short_circuit_does_not_write_cache` | P0. After a short-circuit hit, `_intent_cache` is empty — writes are owned by `confirm_intent`. Invariant from §5 Condition #8. |
| `backend/tests/services/test_intent.py` | `TestDeterministicShortCircuit::test_short_circuit_runs_audit` | P1. `_audit_intent_mapping` fires with the YAML-resolved cip; playful-warning tone propagates to `audit_flag` / `audit_message`. Confirms the audit safety-net isn't bypassed. |
| `backend/tests/services/test_intent.py` | `TestPromptCopy::test_prompt_does_not_bias_toward_school_cips` | P2. Snapshot-level assertions on `_INTENT_SYSTEM_PROMPT`: the pre-rewrite phrases (`these have earnings data`, `these have career path data`) MUST NOT be present; the rewrite signals (`most specific cip`, `blends earnings`) MUST be present; all four `.format()` keys must be intact. |
| `tests/mcp/test_cip_substitution.py` | `TestCanonicalCip4::test_strips_padding` | P0. `_canonical_cip4` projects `52.01`, `52.0100`, `52.0101`, `52.1401`, `52.14`, and `""` to their expected 4-digit forms. Every case from §4 table. |
| `tests/mcp/test_cip_substitution.py` | `TestIntegrationLikePath::test_padded_broad_cip_still_substitutes` | P0. End-to-end stubbed: `cipcode="52.0100"` + `"Marketing"` at IU → same substituted Marketing payload as `52.01`. Verifies canonicalization at BOTH `reported_cipcode` sites (caveat + response root). |
| `tests/mcp/test_cip_substitution.py` | `TestIntegrationLikePath::test_specific_six_digit_does_not_substitute` | P0. `cipcode="52.0101"` + `"Marketing"` at IU → substitution does NOT fire (`_is_broad_cip` rejects). Fall-through canonicalizes to `"52.01"` and lands in `_fallback_broaden_cip`. Caveat type is `cip_broadened`, NOT `blended_substitution`. Enforces §1 Success Criterion 4. |
| `tests/mcp/test_cip_substitution.py` | `TestStandardPath::test_padded_specific_cip_normalizes` | P1. `cipcode="52.1000"` (HR padded) + no `student_major` → IU's HR row from `program_career_paths`. Validates standard-path filter-site canonicalization. |
| `tests/mcp/test_cip_substitution_integration.py` | `TestIUBMarketing52_14_PaddedInput::test_substitution_fires_with_52_0100` | P0. End-to-end against real Iceberg: padded `52.0100` input produces the same substituted Marketing payload as the bare-4-digit case. Skipped if the warehouse isn't populated locally. |

**Test class count added: 5** (`TestLookupMajor`, `TestCrossModuleConsistency`, `TestDeterministicShortCircuit`, `TestPromptCopy`, `TestCanonicalCip4`, `TestIntegrationLikePath`, `TestStandardPath`, `TestIUBMarketing52_14_PaddedInput` — 4 new classes + 3 new test methods appended to the existing `TestIntegrationLikePath` class pattern; note `TestCanonicalCip4` is net-new alongside `TestIntegrationLikePath` new methods).

**Discrete test count added: 21** (9 in `test_intent.py` new classes, 7 in `test_major_lookup.py` core + 204 parametrized cross-module consistency cases, 4 in `tests/mcp/test_cip_substitution.py`, 1 in `tests/mcp/test_cip_substitution_integration.py`).

### Edge Cases Covered

- [x] Bare 4-digit CIP (`52.01`) — identity under `_canonical_cip4`, substitution fires as before.
- [x] Zero-padded 6-digit broad CIP (`52.0100`) — canonicalized to `52.01` at every filter + response site; substitution fires; caveat + response root both surface `"52.01"`.
- [x] Specific 6-digit CIP in a broad family (`52.0101`) — explicitly NOT broad; falls through standard path; lands in `_fallback_broaden_cip`; caveat type is `cip_broadened`.
- [x] Padded specific CIP outside the broad family (`52.1000`) — canonicalized to `52.10`; standard path finds the school's program row.
- [x] Empty CIP (`""`) — `_canonical_cip4` early-return branch.
- [x] Empty / whitespace / `"\t\n"` major input — `lookup_major` returns None; short-circuit does not fire; request reaches Gemma.
- [x] Mixed-case major + alias input — both hit the same YAML entry.
- [x] Unknown major input — short-circuit skipped, Gemma called.
- [x] Marketing-at-IU (broad-family reported) — `parent_cip=52.01` non-empty (frontend substitution affordance lights up).
- [x] Marketing at a school reporting `52.14` directly — `parent_cip=""` (no false affordance).
- [x] Marketing at a school with only non-52 programs — `parent_cip=""` (outcomes broadening fallback will handle).
- [x] YAML short-circuit must not write `_intent_cache` — cache remains `{}` after a hit.
- [x] Audit step still fires on the short-circuit path — `audit_flag` and `audit_message` propagate.
- [x] Cross-module consistency across all 204 (entry × alias) pairs in `major_to_cip.yaml` — `lookup_major` and `_find_major_intent` agree on `cip4` for every input.
- [x] Prompt body: pre-rewrite bias phrases absent; rewrite signals present; all four `.format()` keys intact.

### Test Results

| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest (root, `uv run pytest`) | 1674 | 2 (pre-existing `debt_p25`) | 1 deselected | 1677 |
| pytest (backend, `cd backend && pytest`) | 604 | 0 | 0 | 604 |
| Substitution focus (`uv run pytest tests/mcp/test_cip_substitution.py tests/mcp/test_cip_substitution_integration.py`) | 31 | 0 | 0 | 31 |
| Intent + major_lookup focus (`backend: pytest tests/services/test_intent.py tests/services/test_major_lookup.py`) | 255 | 0 | 0 | 255 |
| vitest | n/a (backend-only spec) | — | — | — |

**Pre-existing failures (acknowledged, not in scope):**

- `tests/mcp/test_get_career_paths.py::TestValidLookup::test_response_contains_all_fields` — asserts a `debt_p25` field not present in the handler's response. Confirmed pre-existing in §6 Build Accountability Log (step 2 verified this reproduces on clean main with my stashed). Unrelated to this spec.
- `tests/mcp/test_get_school_programs.py::TestResponseShape::test_response_contains_all_expected_fields` — same `debt_p25` shape drift, same verdict.

**All new tests pass.** No silent skips. The one integration test (`TestIUBMarketing52_14_PaddedInput::test_substitution_fires_with_52_0100`) would skip in CI / fresh checkouts via the module-level `pytestmark = pytest.mark.skipif(not _warehouse_available(), ...)`; it ran green locally because the warehouse is populated.

### Gaps Identified

- **Integration test skip on CI** — the new `TestIUBMarketing52_14_PaddedInput` inherits the module-level skip gate. CI will not exercise this case until the warehouse is provisioned there (tracked separately in §11 of `docs/specs/completed/cip-intent-substitution.md`). The unit-level `TestIntegrationLikePath::test_padded_broad_cip_still_substitutes` covers the same logic with stubs, so the invariant is verified on every run regardless.
- **Frontend `MajorInput.tsx:102` contract is asserted indirectly** — the `parent_cip` tests pin the backend contract, but there is no vitest test that verifies the frontend actually reads `parent_cip !== ""` as the substitution-affordance signal. §2 Out of Scope flagged frontend work; left to the frontend tracking spec.
- **YAML file-missing branch** — `lookup_major` has a defensive "YAML not on disk → return `()`" path in `_load`. No new test exercises that branch (would require clearing both lru_caches AND monkeypatching `_yaml_path` to `lambda: None`, per §4 Test Data Requirements). Low-value: the `test_unknown_returns_none` already exercises the path-lookup logic indirectly, and the load path is trivial enough that a mis-resolve would show up as a cascade of cross-module consistency failures.

### Existing Tests Status

All tests in §4 "Existing Tests at Risk" and "Confirmed Safe" passed WITHOUT modification:

| Test | Status |
|------|--------|
| `tests/mcp/test_cip_substitution.py::TestIntegrationLikePath::test_iub_marketing_substitution_fires` | PASS |
| `tests/mcp/test_cip_substitution.py::TestIntegrationLikePath::test_no_substitution_when_specific_cip` | PASS (maps to `TestSubstitutionFires::test_no_substitution_when_specific_cip` in the live file) |
| `tests/mcp/test_cip_substitution.py::TestBlendedStats::test_ern_and_roi_match_engine_formula` | PASS |
| `tests/mcp/test_cip_substitution.py::TestErrorHandling::test_missing_school_row_returns_null` | PASS (no asserted-message update needed — the production error message already reports the canonical form after step 2's implementation, and the existing test asserts `"cannot substitute" in result["message"]` which survives the canonicalization unchanged) |
| `tests/mcp/test_cip_substitution.py::TestErrorHandling::test_empty_crosswalk_returns_null` | PASS |
| `tests/mcp/test_cip_substitution_integration.py::TestIUBMarketing::*` (5 tests) | PASS |
| `tests/mcp/test_cip_substitution_integration.py::TestIUBAccounting::test_accounting_soc_set` | PASS |
| `tests/mcp/test_cip_substitution_integration.py::TestIUBFinance::test_finance_soc_set` | PASS |
| `tests/mcp/test_cip_substitution_integration.py::TestSpecificCipBypass::test_isu_52_14_direct_path` | PASS |
| `backend/tests/services/test_intent.py` (21 pre-existing tests across Gemma tiers + sanitizer + salvage) | PASS |
| `backend/tests/services/test_stat_engine.py` (all) | PASS (no changes, ran clean in the full backend run) |
| `backend/tests/services/test_school_lookup.py` (all) | PASS |

None of the "Confirmed Safe" tests required modification — consistent with the §4 analysis that no existing test exercised the padded-6-digit input form or the short-circuit path.

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@fp-design-auditor)
**Status:** SKIPPED (backend-only spec)

### Code Review (@faang-staff-engineer)
**Status:** APPROVED with nits
**Reviewed:** 2026-04-18

#### Summary

Ready for prod. The substitution helper (`_canonical_cip4`) is minimal, correct, and applied at every filter + response site the spec enumerates. The intent short-circuit is tight: `_derive_parent_cip` is defensively written against untrusted `programs` input, the audit invariant is preserved, and the cache-write omission is explicit + tested. No security issues. Two genuine nits below, plus a handful of SOUND notes on things I specifically checked.

Biggest risk left on the table: a sub-second short-circuit still pays a Gemma round-trip for the audit step, so a degraded-Gemma scenario drags the "deterministic" path down to Gemma's latency floor. That's pre-existing architecture (same tradeoff on the Gemma path), not a regression — flagging for awareness, not as a fix requirement in this spec.

#### Findings

##### Finding 1: Short-circuit latency depends on Gemma audit — NIT

**Impact:** When `INFERENCE_BACKEND=openrouter` is slow (P99 spikes are real and have happened; `gemma_client` sets no timeout — verified at `backend/app/services/gemma_client.py`, no `timeout=` kwarg anywhere), the "deterministic YAML short-circuit" still blocks on `_audit_intent_mapping` → `gemma_client.generate`. Student waits N seconds on what the spec sells as a zero-Gemma path.

**Location:** `backend/app/services/intent.py:472`

**The Problem:** The spec's framing ("cuts one Gemma call per known major — cheaper, faster") is half-true. It cuts the *intent* call but keeps the *audit* call, which is identically latent. The audit safety net is the right call architecturally — it catches adversarial inputs at the audit level even when the YAML is confidently wrong about a flagged major — but the perf claim is softer than the spec advertises.

**The Fix:** Not required for this spec. For a follow-up: either (a) add a timeout to `gemma_client.generate` (belongs in a separate spec since it affects every caller), or (b) make the audit step fire-and-forget for the short-circuit path specifically — YAML hits are high-confidence by construction, so losing the audit signal on a Gemma stall is acceptable. Flag as follow-up; don't block this spec.

**Severity:** 🔵 Minor (pre-existing architecture, not a regression)

##### Finding 2: Cache-write omission is correct but leaves a cheap optimization on the table — NIT

**Impact:** A cache-miss that fires the short-circuit re-runs `_get_school_cips(unitid)` (one DuckDB query), `_promote_to_leaf_cip`, `_get_career_titles_for_cip` (one DuckDB query), AND `_audit_intent_mapping` (one Gemma call) every time the same `(normalized_major, unitid)` lands, until the user taps confirm. Confirm writes the cache; but if the user just scrolls back and forth between the major picker and the confirm card, each POST /intent/ is a full round-trip.

**Location:** `backend/app/services/intent.py:456–495`

**The Problem:** The spec's invariant ("cache writes are owned by confirm_intent") is defensible — you don't want to poison the cache with a match the student hasn't accepted. But the short-circuit is by definition the most stable path: YAML + school catalog + derived parent_cip are all deterministic given the inputs. There's no nondeterminism to protect against. Meanwhile the Gemma path pays this same cost with the same rationale, so at minimum it's consistent.

**The Fix:** Not required. If you want to address it later, the right move is a separate short-lived TTL cache (say 60s) for the short-circuit result only, keyed on `(normalized_major, unitid)`, living alongside `_intent_cache`. Keeps the confirm-cache invariant pristine while avoiding the repeat-render tax. Out of scope here — the behavior today is correct, just not optimal.

**Severity:** 🔵 Minor

##### Finding 3: `matched_cip` can return a 4-digit family from the short-circuit — CHANGES REQUIRED (narrowly)

**Impact:** Real failure case: student typed "Special Education" → YAML hit with `cip4="13.10"` → school catalog reports no descendants in the 13.10 family → `_promote_to_leaf_cip` returns the unchanged 4-digit `"13.10"` → `IntentResult.matched_cip = "13.10"`. The Gemma path would have raised `ValueError` at line 517 (`_CIP_PATTERN.match(matched_cip)` which requires 6-digit). The short-circuit returns it to the frontend.

Downstream: `/build/outcomes` → `_handle_get_career_paths` validates against `_CIPCODE_PATTERN = r"^\d{2}\.\d{2,4}$"` (futureproof_server.py:430) which *does* accept 4-digit, so `compute_pentagon` doesn't explode. `_canonical_cip4` then treats `"13.10"` as-is (len==5, returns `"13.10"`). The query works.

So functionally it does not crash. But the Gemma path has an explicit guard against this exact state (the line 517 check was added *specifically* to prevent malformed primary CIPs from leaking into downstream MCP queries, per the inline comment at L518–521). The short-circuit bypasses that guard silently. The asymmetry matters if/when someone adds a downstream consumer that assumes 6-digit (the frontend's career card lineage sheet, for example, routes on leaf-vs-family in a couple of places).

**Location:** `backend/app/services/intent.py:470` (no validation between `_promote_to_leaf_cip` return and `IntentResult` construction)

**The Problem:** The two code paths now have different post-conditions for `matched_cip` — Gemma guarantees 6-digit XX.XXXX, short-circuit does not. That's a silent contract drift.

**The Fix:** One of:
1. Accept the asymmetry explicitly — add a docstring note on `resolve_intent` that `matched_cip` may be 4-digit when the short-circuit fires and no school catalog leaf exists. The `IntentResult` Pydantic model (or its frontend TS type) should then reflect this. This is the lowest-effort fix.
2. Mirror the Gemma path's check — after `_promote_to_leaf_cip`, if `matched_cip` is still 4-digit, either fall through to the Gemma path or raise. This breaks the spec's "exact YAML hits skip Gemma" contract for a narrow case. Probably overkill.

Recommend option 1. Write the asymmetry down. I'm flagging as CHANGES REQUIRED only because this is the kind of thing that silently corrupts a downstream consumer 6 months from now and nobody remembers why.

**Severity:** 🟡 Moderate

##### Finding 4: `_fallback_broaden_cip` dead-branch comment is accurate, deferral is safe — SOUND

**Impact:** None (verifying the spec's deferral claim).

**Location:** `src/mcp_server/futureproof_server.py:1762–1772`

I verified this: `_fallback_broaden_cip` Attempt 2 compares `str(r.get("cipcode", "")) == general_cip` where `general_cip = f"{family}.0100"` (6-digit padded). `valid_rows` is sourced from `CAREER_PATHS_TABLE` (`program_career_paths`), which is 4-digit per the Silver `normalize_cipcode` invariant. The comparison literally cannot match on current data. Branch is dead, and deferring the cleanup does not introduce a regression because nothing reaches it today and nothing will after this spec. The comment at L1762–L1767 is accurate. Good call deferring. (Worth a cleanup spec eventually — the branch is pure technical debt — but not here.)

##### Finding 5: `reported_cipcode` canonicalization is complete at the four sites the spec calls out — SOUND (with one observation)

**Impact:** None. I grepped every `reported_cipcode` reference in the MCP server and cross-checked against the four sites. All four (L2143, L2154, L2202, L2233) correctly route through the pre-computed `canonical_reported` / `canonical_cipcode` variables. No fifth response path echoes raw caller input back as `reported_cipcode`.

**Observation:** There IS a related-but-distinct field `original_cipcode` in `_fallback_broaden_cip`'s caveat (L1757, L1780, L1797) and in `_fallback_gemma_soc_resolution`'s caveat (L1982), which still carries the raw caller-supplied `cipcode`. The spec explicitly scoped `reported_cipcode` only, so this is in-scope-by-omission — `original_cipcode` is a different semantic (it's "what the user asked for", not "what we looked up"), which is a defensible split. If the frontend ever reads `original_cipcode`, it'll see the raw input, which may or may not be the intended UX. Not a bug in this spec; worth noting in the follow-up doc.

##### Finding 6: `_derive_parent_cip` is defensively tight against untrusted `programs` input — SOUND

**Impact:** None. Walked through every failure case the prompt called out:

- Empty string `cipcode`: L410 `raw = str(program.get("cipcode", "") or "")` → empty → L411 continue. Safe.
- `None` values: same coercion via `or ""`. Safe.
- Non-dict entries in the list: `program.get()` raises AttributeError. **Mildly concerning — see below.**
- 500 programs: O(n) scan, 500 is nothing. Safe.
- Non-CIP-format garbage (`"hello"`): `canonical = "hello"[:5] = "hello"`. L414 `canonical == cip4` won't match (cip4 is XX.XX). L416 `canonical[:2] != family` — `"he" != "52"` skips. Safe, returns `""`.
- Duplicated programs: same program hits the candidates list twice; L420 returns `candidates[0]` — first match wins, stable. Safe.
- YAML entry with garbage `cip4` (e.g. `"AB.12"`): L405 `family = "AB"`, L406 `family.isdigit()` → False → early return `""`. Safe. Good defensive instinct on the isdigit guard.

**The one genuine concern: non-dict entries.** `IntentRequest.programs: list[dict]` is declared as `list[dict]`, which Pydantic v2 coerces on input — but `dict` alone accepts anything shaped like a mapping. If a caller bypasses the FastAPI validation layer (direct internal call, a test, a future CLI invocation), `_derive_parent_cip` will AttributeError on `program.get()` for a non-dict.

**The Fix (trivial):** Wrap in `isinstance(program, Mapping)` inside the loop:

```python
for program in programs:
    if not isinstance(program, Mapping):
        continue
    raw = str(program.get("cipcode", "") or "")
```

**Severity:** 🔵 Minor (FastAPI validation catches this today; one layer of defense, not two)

##### Finding 7: `lookup_major` silent-fail on missing YAML — SOUND (behavior is correct; discoverability is weak)

**Impact:** If the YAML can't be found (`_yaml_path` returns None), `_load` returns `()`, `lookup_major` returns None for every input, and the short-circuit silently never fires. Every request falls through to Gemma. Nothing breaks; the system just loses the perf + determinism the spec promises.

**Location:** `backend/app/services/major_lookup.py:44–53`

**Analysis:** This is the correct failure mode — graceful degradation, not crash-on-startup. Raising at import would break `uvicorn app.main:app` on a misconfigured dev environment; raising on first call would produce an HTTP 500 for every intent request instead of a slow-but-working experience.

But: the silent-fail is exactly the class of bug the spec itself was written to address (Bug B leaked into prod because the short-circuit silently no-op'd). If the YAML ever goes missing in a deploy (file not shipped, renamed, path glitch), you get Bug B all over again and nobody knows.

**Recommendation:** Add a log-once warning at the `_load` cache-miss when `_yaml_path()` returns None. Not a raise, just a `logger.warning("major_lookup: YAML not found; short-circuit disabled")` with the walked paths. Keeps the graceful-degradation semantics while making the failure discoverable from logs.

```python
@lru_cache(maxsize=1)
def _load() -> tuple[MajorEntry, ...]:
    path = _yaml_path()
    if path is None:
        logger.warning(
            "major_lookup: %s not found in any parent of %s; short-circuit disabled",
            _REL_YAML_PATH, Path(__file__).resolve().parent,
        )
        return ()
    ...
```

**Severity:** 🔵 Minor (quality-of-life for ops, not a correctness bug)

##### Finding 8: `@lru_cache(maxsize=1)` on module-level loaders + uvicorn workers — SOUND

**Impact:** None. Each uvicorn worker is a separate Python process (forked pre-startup with `--workers N` or spawned fresh on reload). `lru_cache` state is per-process by definition. So every worker independently resolves `_yaml_path`, loads the YAML, and holds its own cache. That's correct behavior — no shared-state coherence problems, no need to coordinate.

**The one real concern:** monkeypatching in tests. If a test monkeypatches `_yaml_path` without clearing the cache, the patch is a no-op (cached value wins). The existing test suite at `backend/tests/services/test_major_lookup.py:150–158` does clear both caches. Good. But: the next person writing an intent test probably won't know about the two `lru_cache` layers — they'll monkeypatch the YAML file and wonder why nothing changed.

**Recommendation:** Add a short module-level docstring note next to `_load` explicitly saying "both `_yaml_path` and `_load` cache — tests that mutate the YAML must call both `.cache_clear()` methods." One sentence, makes the invariant visible.

**Severity:** 🔵 Minor

##### Finding 9: Error-message change for `_build_substituted_rows` — SOUND

**Impact:** None. Grepped for `cannot substitute` across the full repo: one production site (L1567) and one test assertion (`tests/mcp/test_cip_substitution.py:700` — uses `"cannot substitute" in result["message"]`, substring match, not exact). No log scraper, no dashboard, no alerting pins this string. Canonicalization in the error message is a pure improvement (makes logs reflect the actual lookup key) with no downstream breakage.

##### Finding 10: Thread safety of `_intent_cache` — SOUND (pre-existing, still load-bearing)

**Impact:** Pre-existing, not worsened by this spec. `_intent_cache` is a module-level dict; `confirm_intent` mutates it; `resolve_intent` reads it. FastAPI with `uvicorn` runs the handlers in an event loop per worker. Python dict reads/writes are atomic under the GIL for single-operation access (`d[k]`, `k in d`, `d[k] = v`), so the current usage is safe from corruption. It is NOT safe from lost-updates if two requests race on `confirm_intent` for the same `(normalized_major, unitid)` — but "last write wins" on a student's own cache entry is a non-issue, because both writes for the same key carry the same cip.

The short-circuit does not touch `_intent_cache` at all, so it adds zero new contention. Flagged here only because the prompt asked me not to hide behind "pre-existing" — the answer is: pre-existing, genuinely benign, no action.

#### Required Changes

1. **Finding 3 (Moderate):** Document the post-condition asymmetry on `matched_cip` between the Gemma path and the short-circuit path. Either docstring on `resolve_intent` or a comment at the short-circuit return site. Route to: Claude Code (general) — one-line doc change.

2. **Finding 6 (Minor):** Add `isinstance(program, Mapping)` guard inside `_derive_parent_cip`'s loop. Defense in depth against a caller that bypasses FastAPI validation. Route to: Claude Code (general) — two-line change.

3. **Finding 7 (Minor):** Add a one-shot `logger.warning` in `_load` when `_yaml_path()` returns None. Route to: Claude Code (general).

4. **Finding 8 (Minor):** Add a one-line docstring note on `_load` that both caches must be cleared in tests. Route to: Claude Code (general).

Findings 1, 2, 4, 5, 9, 10 require no action.

#### What's Good

- `_canonical_cip4` is minimal and applied everywhere it needs to be. Single rule, single helper, four filter sites + four response sites, no drift.
- `_derive_parent_cip` correctly uses `raw` (not `canonical`) for the broadness check — matches `_BROAD_CIP_PATTERN` semantics and rejects `XX.0101`-style specifics. The author understood the contract.
- Cwd-independent path resolution via `Path(__file__).resolve().parents` — correct fix for the `Path.cwd()` bug the architect flagged. Walks up from the module file, not the caller's cwd.
- Short-circuit preserves the audit-step invariant. The YAML is the deterministic backbone; the audit is the adversarial-input safety net. Both still fire. Good.
- Cache-write omission on short-circuit matches the Gemma-path invariant (only `confirm_intent` writes). Documented in code, tested in `test_short_circuit_does_not_write_cache`. Invariant is executable, not just commented.
- Cross-module consistency test (`lookup_major` vs `_find_major_intent`) is parametrized across the entire YAML — drift detector works.
- Error messages now surface the canonical lookup key, so ops reading logs see the actual cause.

#### Verdict
- [ ] APPROVED
- [x] APPROVED (with nits — findings 3/6/7/8 are cheap to address but not blocking)
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

Ship it after knocking out findings 3 and 6; findings 7 and 8 are discretionary but I'd take them. None of the concerns is load-bearing enough to hold the spec up. The substitution helper is the right shape, the short-circuit is tight, and the contracts hold at every seam I checked.

---

## §9 Verification

**Status:** PASS — full build green end-to-end. Every suite §1 names now passes.

**Verified:** 2026-04-18 (initial run 19:37 → fix-up run 20:10 → environmental-cleanup run 20:30)

### Backend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff) — backend | PASS | All checks passed. |
| Lint (ruff) — pipeline | PASS | All checks passed. (Environmental cleanup — see Build Accountability Log attempts 3–4.) |
| Type check (mypy) — backend | PASS | 46 errors in 18 files — matches pre-existing baseline. Step 2 reduced mypy from 47 → 46 net via `Sequence`/`Mapping` typing on `_derive_parent_cip` and `cast` + `# type: ignore[import-untyped]` on `major_lookup.py`. |
| Tests (pytest) — backend | PASS | 606 passed, 0 failed. |
| Tests (pytest) — pipeline | PASS | 1676 passed, 1 deselected (network-marker skip), 0 failed. |

### Frontend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| TypeScript (`npx tsc --noEmit`) | PASS | No errors. |
| Tests (vitest) | PASS | 445 passed, 1 skipped, 0 failed. |
| Production build (`npm run build`) | PASS | `tsc -b && vite build` clean. Output: `dist/assets/index-*.js` 739 KB / 226 KB gzip. |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | Builder flagged `test_major_lookup.py` I001 as "pre-existing". | `ruff check .` in `backend/` reported 1 unsorted-import-block error. | Spec owner inspected: file was created in step 4 by @test-writer, so the error is spec-owned — builder's label was wrong. |
| 2 | Backend ruff clean. | n/a | `ruff check --fix tests/services/test_major_lookup.py` (cosmetic blank-line cleanup). Pytest still 225/225 on that file afterward. |
| 3 | Cleanup run requested by spec owner to close out the 3 pre-existing suites (documented in "Environmental cleanup" section below). | 23 pipeline ruff errors, 2 `debt_p25` fixture failures, 2 ProfileScreen test failures, 1 Vite `tsc -b` type error. | See the next subsection — five targeted, minimal-blast-radius fixes, each one independently verified. |
| 4 | All green. | n/a | Full matrix re-run: pipeline ruff clean, backend ruff clean, mypy 46 (unchanged), backend pytest 606/606, pipeline pytest 1676/1676, frontend vitest 445 + 1 skipped, `npm run build` clean. |

### Environmental cleanup (scope: bundled with this spec per owner request)

The §1 success-criterion line "Full build green: `ruff`, `mypy`, `pytest` (root + backend), TypeScript, `vitest`, Vite production build" was not met on initial verification because of three unrelated pre-existing issues. The spec owner authorized closing these out inside this spec so the workflow terminates on a truly-green matrix. Root-cause analysis and fixes below.

**Fix 1 — Pipeline ruff (23 → 0 errors)**

- `ruff check --fix src/ tests/` auto-resolved 12 of 23 (F401 unused imports, F811 redef, F541 empty f-string).
- 6 `F841` errors flagged `arrow` / `arrow_table` locals in `src/gold/*.py` as unused. These are **false positives** — DuckDB auto-registers Python locals by name inside SQL (`con.sql("SELECT * FROM arrow")`). Added `# noqa: F841  (DuckDB auto-registers by local name)` with a trailing-comment explanation at each call site. Deleting the locals would break the gold transformers at runtime.
- 3 `E402` errors at `src/mcp_server/futureproof_server.py:49-52` were module-level imports placed *after* the `_decode_json_struct_fields` helper definition. Reordered imports to module-top; moved the `_JSON_STRUCT_FIELDS` constant + helper below. No behavioral change — helper doesn't depend on the later imports.
- 1 `F841` in `tests/silver/test_onet_transformer.py:574` was a genuinely-defined-but-unused `wrong_ids` set. The surrounding assertions used string literals that duplicated the set's values. Fixed by replacing the literal-membership checks with `assert BURNOUT_ELEMENT_IDS.isdisjoint(wrong_ids)` — same invariant, now uses the variable.

**Fix 2 — Pipeline pytest (`debt_p25` fixtures)**

Two tests iterated `CAREER_PATHS_RESPONSE_FIELDS` / `SCHOOL_PROGRAMS_RESPONSE_FIELDS` and asserted every name was present in the fixture row. Fixtures lagged behind three rounds of column additions in the Gold schema:

- `debt_p25`, `debt_p75` (missing from both `BIZ_ROWS` in `test_get_career_paths.py` and `ISU_ROWS` in `test_get_school_programs.py`) — added with representative values mirroring the existing `debt_median` scale.
- `ai_adoption_share`, `velocity_label`, `composite_method`, `adoption_percentile` (four AI-exposure composite provenance fields added in S4 v4) and `roi_cost_basis` (cost-based ROI provenance) — added to `BIZ_ROWS` only; `ISU_ROWS` doesn't exercise the career-paths response shape.

The test-file authors had left explicit TODO comments acknowledging the gap (`# once the pre-existing debt_p25/debt_p75 fixture gap is fixed.`) — cleared with this fix.

**Fix 3 — Frontend vitest (ProfileScreen tests)**

Not a Framer Motion / jsdom timing issue as the initial diagnosis suggested. Actual root cause: `ProfileScreen.tsx:171` strips the animal emoji from the name display before rendering (`profileName?.replace(animalEmoji ?? "", "").trim()`), and renders the emoji separately at L163 in its own `<motion.p>`. The tests asserted against the old pre-refactor single-string rendering (`getByText("dancing happy bear 🐻")`), which the DOM no longer contains.

Fix: split each assertion into two — one for the emoji-stripped name and one for the emoji. Same coverage, matches the rendered DOM shape.

**Fix 4 — Frontend `npm run build` (vitest/vite version mismatch)**

`vite@6.4.1` at the project root vs `vite@5.4.21` bundled inside `vitest@2.x`'s own `node_modules`. `tsc -b` type-checked both `vite.config.ts` (vite@6 types) and `vitest.config.ts` (vite@5 types via vitest), producing the TS2769 `Plugin<any>` covariance mismatch.

Fix: bumped `"vitest": "^2.0.0"` → `"^3.0.0"` in `frontend/package.json`. vitest@3 bundles vite@6, eliminating the nested `node_modules/vitest/node_modules/vite` directory entirely. Re-ran `npm install`, confirmed the nested vite is gone, then `npm run build` produces a clean dist bundle (739 KB JS / 226 KB gzip).

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

### REWRITE (v1.1) — 2026-04-18, @fp-copywriter

Applied identically to `backend/app/services/intent.py::_INTENT_SYSTEM_PROMPT`
and `backend/cli.py::_INTENT_SYSTEM_PROMPT`. Byte-for-byte verified after
edit (both 3303 chars). All four `.format()` keys preserved
(`student_input`, `school_name`, `school_cip_list`, `crosswalk_cip_list`).
JSON schema unchanged (`matched_cip`, `matched_title`, `confidence`,
`reasoning`, `parent_cip`, `alternatives`). 6-digit leaf directive and
tier semantics preserved. `backend/tests/services/test_intent.py`: 21/21
pass. `mypy app/services/intent.py`: no new errors (2 pre-existing,
unrelated to the prompt).

**Prompt body diff (unified, only the hunks that changed):**

```diff
-You are a college program advisor who understands how students, parents, \
-counselors, and registrars all describe academic programs differently.
-
-A student has told you what they want to study. Your job is to match their \
-intent to the most appropriate CIP (Classification of Instructional Programs) \
-code from the available options.
-
-Consider how different people describe the same program:
-- Students say: "pre-med", "CS", "business", "art"
-- Parents say: "Physical Therapy", "Deaf Education", "Criminal Justice"
-- Counselors say: "Special Ed", "STEM", "Allied Health"
-- Registrars say: "CIP 51.2308 Physical Therapy/Therapist"
+You map a student's free-text major to a CIP (Classification of \
+Instructional Programs) code. Pick the most specific CIP that matches \
+their intent. Full stop.
+
+Students, parents, counselors, and registrars describe the same program \
+differently:
+- Students: "pre-med", "CS", "business", "art"
+- Parents: "Physical Therapy", "Deaf Education", "Criminal Justice"
+- Counselors: "Special Ed", "STEM", "Allied Health"
+- Registrars: "CIP 51.2308 Physical Therapy/Therapist"
+
+Read through the surface form to the program underneath.

 Confidence tiers drive how many alternatives you return.

 - "high": The input resolves to exactly one CIP — no ambiguity, even if \
 the phrasing is colloquial. Output exactly "alternatives": [].
-  Tiebreaker: if the school's reported program list contains a single \
-entry whose title is a near-direct match to the student input, use high \
-even if the phrase sounds like an umbrella term.
   Example: "pre-PT" -> 51.2308 Physical Therapy/Therapist.

@@ (medium and low tiers unchanged) @@

 The student typed: "{student_input}"
 School: {school_name}

-Programs this school reports (these have earnings data):
+Candidate CIPs — programs reported by this school:
 {school_cip_list}

-Additional specific programs in the same families (from the national \
-crosswalk — these have career path data even if the school doesn't report \
-them separately):
+Candidate CIPs — specific programs in the same families from the \
+national crosswalk:
 {crosswalk_cip_list}

-Respond in JSON only, no preamble, no markdown. Keep "reasoning" to at \
-most two sentences.
+Both lists above are equally valid match candidates. Do NOT prefer a \
+school-reported CIP over a crosswalk CIP to "preserve earnings data" — \
+the backend blends earnings automatically when it substitutes a broad \
+school CIP with a specific cousin. Your job is the match; the blending \
+is not yours to protect.
+
+Respond in JSON only, no preamble, no markdown.

 "matched_cip" MUST be the full 6-digit leaf format XX.XXXX (e.g. \
 13.1001, 51.2308, 52.0201). NEVER put a 4-digit umbrella like XX.XX \
-there — if the student's input maps to a whole family rather than one \
-specific program, pick the single most representative leaf from the \
-programs listed above and put the 4-digit family code in "parent_cip".
+there — if the student's intent lands on a whole family rather than \
+one specific program, pick the single most representative leaf from the \
+candidates above and put the 4-digit family code in "parent_cip".
+
+"reasoning" is shown to the student. Keep it to one or two sentences. \
+Name the program and the tell that anchored the match. Direct, \
+confident, no hedging. Do not say "based on" or "as an AI" or "I'm \
+not certain" — state the call.

 {{"matched_cip": "XX.XXXX", "matched_title": "Program Title", \
 "confidence": "high|medium|low", \
-"reasoning": "Up to two sentences explaining why this is the best match.", \
+"reasoning": "One or two sentences naming the program and why it fits.", \
 "parent_cip": "XX.XX (4-digit family code, may equal matched_cip[:5] \
 when matched_cip is already a leaf in this family)", \
 "alternatives": []}}
```

**Reasoning.** The three edits that matter: (1) the lede is now an
imperative — "Pick the most specific CIP that matches their intent.
Full stop." — which pins the objective before Gemma sees either CIP
list. The old lede ("match their intent to the most appropriate CIP
from the available options") was vague enough that Gemma weighted the
first-listed list as "most appropriate." (2) Both CIP lists are now
labeled "Candidate CIPs" with parallel framing; the asymmetric "these
have earnings data" / "these have career path data" framing is gone.
A new paragraph tells Gemma explicitly that the backend blends earnings
and Gemma does not need to favor school CIPs to protect them — this
kills the failure mode at the source. (3) The "high" tier's
school-catalog tiebreaker was removed because it reinforced the same
school-CIP bias (a near-title match from the school's list would lock
in "high" confidence even when a more specific crosswalk cousin existed).

Voice tightening throughout: dropped the "college program advisor who
understands how..." role-play preamble — Gemma doesn't need a character,
it needs a task. Added a dedicated directive for `reasoning` since that
string surfaces in the UI (MajorInput match card): one or two sentences,
name the program and the tell, no "based on" / "as an AI" / "I'm not
certain" meta-commentary. That matches the Receipts/Gemma's Take
register in the voice guide — confident, concrete, no hedging. The
schema's `reasoning` example was updated to model the target register
("One or two sentences naming the program and why it fits") instead of
the abstract ("explaining why this is the best match") it was before.

---

## §11 Final Notes

**Human Review:** PENDING

[Final thoughts, lessons learned, follow-up items.]
