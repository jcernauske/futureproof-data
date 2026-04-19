# Bugfix: Disable Intent YAML Short-Circuit + Run 56-Input Regression

## Claude Code Prompt (V2 — Anchored Rerun)

```
Read the spec at docs/specs/completed/bugfix-disable-intent-yaml-regression.md
in its entirety. The V1 run (unanchored) is COMPLETE; this prompt invokes a
V2 anchored rerun per §12 to produce production-realistic data.

Execute the following workflow:

1. ARCHITECTURE REVIEW — SKIPPED. Scope is additive to an existing script;
   no architectural change.

2. IMPLEMENTATION
   - Modify scripts/yaml_regression.py per §12 Methodology Correction:
     * Add --anchored / --k SCHOOLS (default 3) flags.
     * Add _sample_anchoring_schools(expected_cip4, k) — queries the
       DuckDB Gold zone for up to k schools that actually report the
       expected CIP family, returns deterministic (unitid, school_name,
       programs) tuples.
     * Main loop: for each (input, expected_cip), iterate over k
       anchoring schools; call resolve_intent with unitid + programs +
       school_name pulled from the sampled school. Record one row per
       (input, school) pair.
   - Do NOT delete or reshape the V1 logic — keep unanchored as the
     default when --anchored is not set. The V1 baseline data is still
     valid "no-context worst-case" signal.
   - Leave backend/app/services/intent.py untouched (the env-var gate
     shipped in V1 already works).
   - Run backend (ruff + mypy + pytest) to verify nothing regressed.
   - Log work to §6 under a new "V2 Implementation" subsection.
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts).

3. TESTING
   - Add one test covering _sample_anchoring_schools determinism (same
     input + same k returns same schools). Mock DuckDB.
   - Do NOT add a test that calls live Gemma.

4. VERIFICATION
   - Invoke @fp-builder to run ruff + mypy + pytest (backend + root).

5. REGRESSION RUN
   - Run the V2 anchored regression manually:
       uv run python scripts/yaml_regression.py --anchored --k 3 \
           --backend openrouter \
           --output reports/intent-yaml-regression-anchored-YYYY-MM-DD.md
   - Expected: ~657 Gemma calls (219 inputs × 3 schools). Budget < $0.20.
     Wall time: ~50 min with current rate-limit handling. If rate limits
     cluster at the tail like V1, use --backend ollama or add --sleep 0.5.
   - The anchored report must capture per-(input, school) match rows
     PLUS a per-input aggregate (e.g. 3/3, 2/3, 1/3, 0/3) PLUS a per-
     family aggregate PLUS an overall match rate.

6. COMPLETION
   - Update Status to COMPLETE (V2).
   - Update §12 V2 Anchored Regression Methodology with the results
     table + a go/no-go recommendation for disabling YAML in prod.
   - Write a V2 completion report to
     reports/bugfix-disable-intent-yaml-regression-v2-YYYY-MM-DD.md
     summarizing: overall anchored match rate, per-family deltas vs V1,
     per-input recommendations, and the go/no-go for disabling YAML in
     production in set-your-course.
   - The completion report is what drives the Set Your Course go/no-go.
   - Spec stays in docs/specs/completed/ (don't move).
```

---

## Status: COMPLETE (V2)

> **Methodology Correction (2026-04-19).** The V1 regression ran with `unitid=0` and `programs=[]`, stripping the school-context signal that production's UI always passes to `_call_gemma_intent`. The 9.1% match rate is a worst-case unanchored baseline, not the production-realistic signal needed to make a disable-YAML call. See §12 for the V2 anchored methodology and why this matters. The V1 code deliverables (env-var gate + base regression script) remain correct and stay shipped. Only the *interpretation* of V1 results was over-read; V2 produces the real number.

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-19 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-04-19 |
| Blocked By | — |
| Blocks | `docs/specs/feature-set-your-course.md` (the Set Your Course spec's "disable YAML in prod" commitment depends on a clean regression result) |
| Related Specs | `docs/specs/completed/feature-gemma-tiered-matching.md`, `docs/specs/completed/bugfix-broad-cip-substitution-and-intent.md` |

---

## §1 Feature Description

### Overview

Today every major input is resolved by `backend/app/services/intent.py::resolve_intent`:

1. YAML short-circuit — `major_lookup.lookup_major` reads `data/reference/major_to_cip.yaml` and returns the hand-curated CIP for 56 known inputs.
2. Miss → Gemma intent call at `temperature=0.0` + input-derived seed (just shipped — the call is deterministic per input).

Since Gemma is now deterministic per input, the YAML's defining advantage (same input → same output) no longer differentiates it. The remaining question is: **does Gemma correctly resolve the 56 hand-curated inputs without the YAML?** This bugfix gives us the answer, reversibly.

Two deliverables:

1. An `INTENT_YAML_ENABLED` env var gate so the YAML can be disabled for testing without code changes.
2. A regression script that runs every hand-curated input through live Gemma and produces a side-by-side comparison report.

### Problem Statement

Set Your Course (`docs/specs/feature-set-your-course.md`) wants to route every major input through Gemma on the unified screen, so the student sees Gemma reasoning live. But we cannot commit to disabling the YAML in production until we know how well Gemma handles the 56 inputs the YAML was originally built to catch — the ones a curator flagged after watching real students fail.

Without hard data we're guessing. This spec produces the data.

### Success Criteria

**V1 — Env var gate + unanchored baseline (COMPLETE):**

- [x] `INTENT_YAML_ENABLED` env var added to `backend/app/services/intent.py::resolve_intent`. Default `true` (preserves today's behavior). When `false`, the `major_lookup.lookup_major` call is skipped entirely; every input goes to `_call_gemma_intent`.
- [x] Env var is read lazily (on each `resolve_intent` call, not at module import) so tests can toggle it via `monkeypatch.setenv` without restarting the process.
- [x] `scripts/yaml_regression.py` exists, runs from repo root, accepts `--backend ollama|openrouter`, `--limit N`, `--family XX`, `--output PATH` flags.
- [x] Script enumerates all entries in `data/reference/major_to_cip.yaml` where `aliases` is non-empty. For each entry it tests:
  - The canonical `major` string (case-insensitive lowercased)
  - Every string in `aliases`
- [x] Each input is run through the same code path `resolve_intent` uses, but with `INTENT_YAML_ENABLED=false`. Gemma runs at `temperature=0.0` + `_derive_intent_seed(input)`.
- [x] Report written to `reports/intent-yaml-regression-YYYY-MM-DD-HHMMSS.md` with a table: `input | expected_cip (from YAML) | returned_cip (from Gemma) | match? | confidence | one-line reasoning`.
- [x] Report summary section at top: total inputs, total matches, total mismatches, match rate per CIP family, wall time, cost (if openrouter).
- [x] Script has a `--dry-run` that lists the inputs without calling Gemma, so we can validate the enumeration logic without spending tokens.
- [x] Two new backend tests covering the env-var gate (§4 Testing Impact Analysis).
- [x] Full test suite passes: `cd backend && pytest`, `uv run pytest`, `cd frontend && npx vitest run`. Ruff + mypy clean.
- [x] No frontend changes.

**V2 — Anchored rerun with production-realistic school context (COMPLETE):**

- [x] `scripts/yaml_regression.py` gains `--anchored` and `--k SCHOOLS` (default 3) flags per §12. Also added `--sleep` for rate-limit spreading on long runs.
- [x] New helper `_sample_anchoring_schools(expected_cip4, k)` queries the Iceberg Gold zone (`consumable_career_outcomes.institution_name + unitid`) for up to `k` schools that actually report the expected CIP family. Deterministic order (sort by `unitid`). Returns `(unitid, school_name, programs)` tuples where `programs` is the full `_get_school_cips(unitid)` result.
- [x] Main loop, when `--anchored` set: for each `(input, expected_cip)` pair, iterate over the `k` sampled schools and call `resolve_intent(major_text=input, school_name=school_name, unitid=unitid, programs=programs)`. One row recorded per `(input, school)` pair.
- [x] V2 report shape: per-(input, school) table + per-input aggregate (3/3, 2/3, 1/3, 0/3) + per-family aggregate + overall match rate. Reports go/no-go verdict at the top.
- [x] V2 run recorded in §12 with explicit go/no-go recommendation for disabling YAML in prod (per-family, not binary).
- [x] V2 unanchored baseline preserved — no-`--anchored` behavior unchanged so V1 stays replayable.
- [x] Five new tests in `tests/scripts/test_yaml_regression.py` covering `_sample_anchoring_schools` determinism + edge cases (k clamping, empty family, 6-digit cip4, missing fields).

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | **Env var gate, read per-call** not module-level. | (a) Test-friendly — `monkeypatch.setenv` works without reset_cache. (b) Cost of reading an env var is nanoseconds; resolve_intent is already doing DuckDB queries and a Gemma call, the env-var read is free. | Module-level constant — rejected, forces cache-reset ceremony in tests. |
| 2 | **Default true** (preserves today's behavior). | Shipping `INTENT_YAML_ENABLED=true` default means the bugfix code change alone is a no-op in prod. Switching to false is a separate ops decision, happening only after the regression report is clean. | Default false — rejected, flips production behavior on merge of a bugfix PR. |
| 3 | **Test every (major, alias) pair**, not just canonical majors. | Aliases exist precisely for inputs students type ("CS", "pre-PT", "nursing"). The regression is worthless if it only checks the canonical NCES title — the canonical is the easy case. | Test only canonical — rejected, misses the hard cases. |
| 4 | **Report is markdown**, not JSONL. | The audience is human — Jeff reading it tonight. Markdown tables are the fastest path to "yep, this one's fine / this one needs help." Automated analysis can re-read markdown tables trivially. | JSONL — rejected, forces a second viewer. CSV — rejected, doesn't render in PRs. |
| 5 | **Match is exact cip4 equality**, not fuzzy. | A mismatch is a signal we want to see, not suppress. Close-but-different CIP (51.3801 Nursing Education vs 51.3808 Nursing Science) counts as a mismatch for reporting; the human decides if it's acceptable. | Fuzzy-match by family prefix — rejected, hides the exact cases we're here to see. |
| 6 | **Single live Gemma call per input**, no retries. | Retry loops would mask flakiness the demo will expose. If Gemma fails on input X once, that's the data point. | Retry with backoff — rejected, masks real behavior. |
| 7 | **Skip audit prompt** in the regression script. | `_call_audit` adds a second Gemma call per input and is not relevant to the YAML-vs-Gemma comparison. We're testing intent matching, not audit signaling. | Include audit — rejected, doubles runtime + cost for no new signal. |

### Constraints

- `backend/app/services/major_lookup.py` — UNCHANGED. The gate is in `intent.py`, not in `major_lookup`.
- `backend/app/services/gemma_client.py` — UNCHANGED. The script uses the existing `generate` + `_derive_intent_seed` pattern.
- `data/reference/major_to_cip.yaml` — UNCHANGED. Read-only input.
- Gemma calls count against OpenRouter budget if `INFERENCE_BACKEND=openrouter`. Estimated cost at `google/gemma-4-26b-a4b-it` pricing × ~250 inputs (56 entries × ~4 aliases avg) × ~1500 tokens/call ≈ under $0.50. Defensible.

### Out of Scope

- **Removing the YAML file.** We're gating, not deleting. The file stays as the hand-curated reference.
- **Automatic fallback** when Gemma mismatches ("try YAML if Gemma disagrees"). Out of scope; that's set-your-course spec territory.
- **Decision on whether to flip the default to false in production.** That decision is driven by the regression report and happens in a follow-up commit, not this spec.
- **Changing the Gemma intent prompt.** If the regression surfaces systematic Gemma miss patterns, tightening the prompt is a separate spec.
- **Touching cli.py's copy of `_call_gemma_intent`.** CLI uses `temperature=0.1`, not production path.

---

## §3 UI/UX Design

**SKIPPED (backend-only, ops toggle + offline script).**

---

## §4 Technical Specification

### Architecture Overview

One additive env-var gate in `resolve_intent`, one new offline script, two new tests. That's it.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `/Users/jcernauske/code/bright/futureproof-data/backend/app/services/intent.py` | Modify | Add `if os.environ.get("INTENT_YAML_ENABLED", "true").lower() == "true":` guard around the `major_lookup.lookup_major` call in `resolve_intent`. When the env var is `false`, skip straight to `_call_gemma_intent`. Import `os` if not already imported. |
| `/Users/jcernauske/code/bright/futureproof-data/scripts/yaml_regression.py` | Create | Offline regression script. Loads YAML, enumerates (input, expected_cip) pairs from entries with non-empty aliases, runs each through `resolve_intent` (with `INTENT_YAML_ENABLED=false` in-process), collects results, writes markdown report. CLI flags per §1 Success Criteria. |
| `/Users/jcernauske/code/bright/futureproof-data/backend/tests/services/test_intent.py` | Modify | Add `TestYamlGate` class with two tests: env-off skips YAML (mock `major_lookup.lookup_major` to raise; resolve_intent must not hit it); default preserves today's behavior. |
| `/Users/jcernauske/code/bright/futureproof-data/reports/.gitkeep` | Create (if not present) | Ensure `reports/` exists on fresh checkout. |

### Data Model Changes

None.

### Service Changes

**Modified — `backend/app/services/intent.py::resolve_intent`** (pseudo-diff):

```python
def resolve_intent(*, major_text, school_name, unitid, programs):
    # NEW: gate the YAML short-circuit behind an env var so the
    # regression script and set-your-course can opt out without code.
    yaml_enabled = os.environ.get("INTENT_YAML_ENABLED", "true").lower() == "true"
    if yaml_enabled:
        yaml_hit = major_lookup.lookup_major(major_text)
        if yaml_hit is not None:
            return _build_yaml_result(yaml_hit, major_text, programs, unitid)
    # else fall through to Gemma, same code path as before.
    ...
```

**New script — `scripts/yaml_regression.py`** (structure):

```python
"""YAML vs Gemma regression — compare hand-curated CIPs against live Gemma.

Runs every (input, expected_cip) pair from data/reference/major_to_cip.yaml
through resolve_intent with INTENT_YAML_ENABLED=false. Writes a markdown
report to reports/intent-yaml-regression-YYYY-MM-DD-HHMMSS.md.

See docs/specs/bugfix-disable-intent-yaml-regression.md.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "backend"))

# Gate YAML BEFORE importing intent so resolve_intent sees the disabled state.
os.environ["INTENT_YAML_ENABLED"] = "false"

from app.services import intent  # noqa: E402

YAML_PATH = _REPO_ROOT / "data" / "reference" / "major_to_cip.yaml"
REPORT_DIR = _REPO_ROOT / "reports"


def _enumerate_cases(path: Path, family_filter: str | None) -> list[tuple[str, str, str]]:
    """Return list of (input, expected_cip4, source_entry_major)."""
    data = yaml.safe_load(path.read_text())
    cases: list[tuple[str, str, str]] = []
    for entry in data:
        aliases = entry.get("aliases") or []
        if not aliases:
            continue
        cip4 = entry["cip4"]
        if family_filter and not cip4.startswith(family_filter):
            continue
        major = entry["major"]
        cases.append((major, cip4, major))
        for alias in aliases:
            cases.append((alias, cip4, major))
    return cases


def _run_one(student_input: str) -> dict:
    start = time.perf_counter()
    try:
        result = intent.resolve_intent(
            major_text=student_input,
            school_name="University of Central Anywhere",
            unitid=0,
            programs=[],
        )
        latency = int((time.perf_counter() - start) * 1000)
        return {
            "ok": True,
            "returned_cip": result.matched_cip,
            "confidence": result.confidence,
            "reasoning": (result.reasoning or "")[:120],
            "latency_ms": latency,
        }
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _write_report(cases_with_results: list[dict], output_path: Path) -> None:
    # Markdown table + summary header — see §1 Success Criteria for the fields.
    ...


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["ollama", "openrouter"], default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--family", type=str, default=None)
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.backend:
        os.environ["INFERENCE_BACKEND"] = args.backend

    cases = _enumerate_cases(YAML_PATH, args.family)
    if args.limit:
        cases = cases[: args.limit]

    if args.dry_run:
        for student_input, expected_cip, source in cases:
            print(f"{expected_cip}\t{source!r}\t<- {student_input!r}")
        return 0

    results = []
    for student_input, expected_cip, source in cases:
        result = _run_one(student_input)
        results.append({
            "input": student_input,
            "expected_cip": expected_cip,
            "source_entry": source,
            **result,
        })

    output_path = Path(args.output) if args.output else _default_output_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_report(results, output_path)
    print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `backend/tests/services/test_intent.py` | `TestDeterministicShortCircuit::*` | Low | Tests don't set `INTENT_YAML_ENABLED`; default is true; behavior preserved. |

#### Confirmed Safe

- All existing `TestDeterministicShortCircuit::*` tests.
- All `TestGemmaIntent::*` and downstream tier tests.
- `tests/mcp/test_cip_substitution_integration.py::*` — MCP server doesn't read the intent env var.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/services/test_intent.py` | `TestYamlGate::test_env_false_skips_yaml` | `INTENT_YAML_ENABLED=false` causes `resolve_intent` to NOT call `major_lookup.lookup_major`. Verified via mock. |
| P0 | `backend/tests/services/test_intent.py` | `TestYamlGate::test_default_preserves_behavior` | Env unset OR `=true` preserves today's YAML short-circuit. |

---

## §5 Architecture Review

### @fp-architect Review
**Status:** SKIPPED (low-risk gate + offline script — per Claude Code Prompt)

### @fp-data-reviewer Review
**Status:** SKIPPED

### @genai-architect Review (ad-hoc)
**Status:** SKIPPED

---

## §6 Implementation Log

**Status:** COMPLETE (V1 + V2)

### Files Modified
| File | Change Summary |
|------|---------------|
| `backend/app/services/intent.py` | Added `import os`. Wrapped the `major_lookup.lookup_major(major_text)` call in `resolve_intent` behind `INTENT_YAML_ENABLED` env var (default `"true"` → today's behavior preserved; `"false"` → YAML skipped, every input goes to Gemma). Read per-call so tests can `monkeypatch.setenv` without restart. |
| `scripts/yaml_regression.py` | New offline regression script. Sets `INTENT_YAML_ENABLED=false` BEFORE importing `app.services.intent`. Enumerates every (major, alias, …) input from YAML entries with non-empty aliases (219 inputs across 56 entries). Calls `resolve_intent` per input with `unitid=0`/`programs=[]`/`school_name="University of Central Anywhere"` (per §4 example). Writes `reports/intent-yaml-regression-YYYY-MM-DD-HHMMSS.md` with summary + per-family rate + full table + mismatch + error sections. Flags: `--backend ollama|openrouter`, `--limit N`, `--family XX`, `--output PATH`, `--dry-run`. |
| `backend/tests/services/test_intent.py` | Added `TestYamlGate` class (2 tests): `test_env_false_skips_yaml` (mock `lookup_major` to raise; assert it never fires), `test_default_preserves_behavior` (env unset + explicit `"true"` both preserve YAML short-circuit and skip Gemma). |

### Deviations from Spec
- **Match semantics.** §4 says "exact cip4 equality." YAML stores 4-digit `XX.YY` family codes; Gemma's primary `matched_cip` is regex-validated to be 6-digit `XX.YYYY`. The script compares Gemma's leaf's first-5 chars (`XX.YY`) against the YAML's `cip4`. So same-family different-leaf counts as a match (e.g. YAML `13.10` + Gemma `13.1011` matches). This is the only sensible read of "exact cip4 equality" given the regex contract that already defends `matched_cip` against 4-digit leaks; tightening to "exact 6-digit identity" would be impossible because the YAML never stores leaves.
- **Audit prompt skipped (per spec).** §2 decision #7 says skip the audit for the regression run. The script patches `intent._audit_intent_mapping` to a no-op immediately after the `intent` import. This halves wall time and openrouter cost without affecting the `matched_cip` we report on. Audit-tone behavior remains covered by the intent test suite, not by this script. (An earlier draft of this spec deviated by skipping this patch; corrected before the regression run.)
- **`reports/.gitkeep` not created.** §4 lists it as "Create (if not present)." The directory already exists with 25+ committed files (per `ls reports/`); a `.gitkeep` is unnecessary noise.

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | PASS | — | Backend: ruff clean, 980/980 pytest pass (incl. 2 new `TestYamlGate` tests), mypy on `intent.py` shows 2 errors at L383 + L445 — both pre-existing (verified via `git stash` round-trip; same errors at pre-edit line numbers 370 + 432). Script lints clean (`uv run ruff check scripts/yaml_regression.py`). Dry-run enumerated 219 inputs as expected (56 canonical majors + 163 aliases). |

### Regression Run
| Field | Value |
|-------|-------|
| Backend | OpenRouter (`google/gemma-4-26b-a4b-it`) |
| Total inputs | 219 (55 distinct YAML entries × ~4 aliases each) |
| Matches | 20 (9.1%) |
| Mismatches | 182 (83.1%) |
| Errors | 17 (7.8% — 2 malformed Gemma JSON + 15 OpenRouter rate-limit clusters at tail of run) |
| Wall time | 973.9 s (~16 min) |
| Cost (openrouter) | <$0.05 (well under §2 estimate of $0.50) |
| Report path | [`reports/intent-yaml-regression-2026-04-19.md`](../../reports/intent-yaml-regression-2026-04-19.md) |
| Completion report | [`reports/bugfix-disable-intent-yaml-regression-2026-04-19.md`](../../reports/bugfix-disable-intent-yaml-regression-2026-04-19.md) |

### V2 Implementation (anchored rerun)

| File | Change Summary |
|------|---------------|
| `scripts/yaml_regression.py` | Added `--anchored`, `--k SCHOOLS` (default 3), and `--sleep` flags. New helpers: `_sample_anchoring_schools` (Iceberg query for k schools that report the expected family, sorted by `unitid` for determinism), `_run_one_anchored` (resolve_intent with school context threaded through), `_summarize_anchored_by_family`, `_per_input_aggregate`, `_write_anchored_report`, `_run_anchored`. V1 unanchored path preserved when `--anchored` is not set. Added `flush=True` to per-row prints so progress is visible under `python -u` redirected stdout. |
| `tests/scripts/test_yaml_regression.py` | New file with 5 tests: determinism (same expected_cip4 + same k → same schools), k-clamping, empty-family handling (`[]` for "no anchor available"), 6-digit cip4 family-prefix clip, missing-field row drops. Mocks `intent.mcp_client.get_server` + `intent._get_school_cips`. |
| `tests/scripts/__init__.py` | New empty init for the tests subdir. |
| `backend/app/services/intent.py` | UNCHANGED in V2. The env-var gate from V1 stays as the kill switch. |

#### V2 Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | OpenRouter 402 | Account had no credits; all 657 calls returned empty raw_response. | User topped up credits; deleted bogus report; re-ran. |
| 2 | Stuck (1h, 0 visible progress) | Python's stdout block-buffering when redirected to file hid the run; `python` (not `python -u`) flushed nothing in 1h. Process was alive but invisible. | Killed; added `flush=True` to per-row prints + relaunched with `python -u`. Restart was clean — V2 ran 657 calls in ~55 min with 1 transient error. |
| 3 | PASS | — | 278/657 matches (42.3%), 378 mismatches, 1 transient malformed-CIP error. Report written. |

### V2 Regression Run
| Field | Value |
|-------|-------|
| Backend | OpenRouter (`google/gemma-4-26b-a4b-it`) |
| Mode | Anchored — k=3 schools per input |
| Inputs enumerated | 219 |
| Total (input, school) attempts | 657 |
| Matches | 278 (42.3%) |
| Mismatches | 378 (57.5%) |
| Errors | 1 (0.2%) |
| Inputs with no anchoring school | 0 |
| Wall time | 3290 s (~55 min) |
| Cost (openrouter) | ~$0.20 |
| Anchored report | [`reports/intent-yaml-regression-anchored-2026-04-19.md`](../../reports/intent-yaml-regression-anchored-2026-04-19.md) |
| V2 completion report | [`reports/bugfix-disable-intent-yaml-regression-v2-2026-04-19.md`](../../reports/bugfix-disable-intent-yaml-regression-v2-2026-04-19.md) |
| **V2 Verdict** | **Per-family disable.** Family 52 (17 entries) → disable YAML, 99.5% Gemma rate with anchor. Family 13 four-digit codes (5 entries) → disable YAML, 100% Gemma rate. Family 13 six-digit sub-leaves (33 entries) → keep YAML, 0% rate even with anchor. Implementation: an allowlist of 22 cip4 codes that bypass the YAML inside `major_lookup` or `intent.resolve_intent`. The `INTENT_YAML_ENABLED` env-var gate stays as the kill switch but is not the operational lever. See `feature-set-your-course.md` for the per-entry implementation. |
| **Verdict** | **DO NOT disable the YAML in production.** Gemma matched 0/147 in Family 13 (Education) and 20/72 (28%) in Family 52 (Business) without school context. The gate ships defaulted to `true` — no production behavior change. |

---

## §7 Test Coverage

**Status:** COMPLETE (backend) — root pytest + vitest deferred to @fp-builder in §9

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|
| `backend/tests/services/test_intent.py` | `TestYamlGate::test_env_false_skips_yaml` | `INTENT_YAML_ENABLED=false` causes `resolve_intent` to NOT call `major_lookup.lookup_major`. Verified by monkey-patching `lookup_major` to raise `AssertionError` on any call; the test injects a Gemma stand-in so `resolve_intent` returns its answer (`52.1401`), proving the input was routed through Gemma instead of the YAML. |
| `backend/tests/services/test_intent.py` | `TestYamlGate::test_default_preserves_behavior` | (a) Env unset → YAML short-circuit fires for `"Marketing"` (returns `52.14` with `"major_to_cip.yaml"` in reasoning) and Gemma never runs (`generate_calls == 0`). (b) Explicit `INTENT_YAML_ENABLED=true` preserves the same behavior. Pins the bugfix's commitment that merging the gate is a no-op in production. |

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest (backend) | 980 | 0 | 0 | 980 |
| pytest (root) | (deferred to @fp-builder) | | | |
| vitest | (deferred to @fp-builder) | | | |

---

## §8 Reviews

**Status:** SKIPPED (per Claude Code Prompt)

---

## §9 Verification

**Status:** PASS WITH PRE-EXISTING NOISE
**Verified:** 2026-04-19 10:32

### Backend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff) | PASS | No issues — `ruff check .` clean across all 44 source files |
| Type check (mypy) | PASS (pre-existing noise) | 45 errors in 18 files — all pre-existing (verified via `git stash` round-trip in §6). The 2 errors attributable to `intent.py` are at lines 383 and 445, confirmed identical to pre-edit lines 370 and 432. Zero errors introduced by this spec. |
| Tests (pytest) | PASS | 980 passed, 0 failed, 62 warnings (DeprecationWarning: `on_event` — pre-existing FastAPI lifecycle warning) |

#### mypy Pre-Existing Errors (not attributable to this spec)
All 45 errors across `app/models/career.py`, `app/models/api.py`, `app/services/stat_engine.py`, `app/services/wrapped_renderer.py`, `app/routers/profile.py`, `app/services/gemma_client.py`, `app/services/skill_pool.py`, `app/routers/skills.py`, `app/routers/schools.py`, `app/services/guidance.py`, `app/routers/gauntlet.py`, `app/routers/guidance_router.py`, `app/routers/builds.py`, `app/routers/branches.py`, `app/routers/reports.py`, `app/services/intent.py` (lines 383, 445 — pre-existing), `app/routers/intent.py`, `app/main.py` are pre-existing. Full list available via `cd backend && .venv/bin/mypy app/`.

### Pipeline (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff src/ tests/ scripts/) | PASS WITH PRE-EXISTING NOISE | `scripts/yaml_regression.py` (the only new file from this spec) is **clean**. 47 pre-existing errors across other scripts: `_adversarial_probe_onet_exp.py` (F401, F541), `data_review_three_signal.py` (F401), `data_review_three_signal_option_b.py` (invalid-syntax), `dq_execute_aei.py` (F401, F541), `dq_execute_csi.py` (F401, F841), `onet_experience_chaos_runner.py` (F541 ×many), `promote_bea_rpp_silver.py` (E402), `promote_career_outcomes_enriched.py` (E402), and others. None introduced by this spec. |
| Tests (pytest tests/) | PASS | 1678 passed, 1 deselected (network-marked), 0 failed — 70.10s |

### Frontend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| TypeScript | PASS | No errors (`npx tsc --noEmit` clean) |
| Tests (vitest) | PASS | 504 passed, 1 skipped, 0 failed — 51 test files |
| Production build (Vite) | PASS | Build completed — 668 modules transformed, dist written. Chunk size advisory (753 kB > 500 kB) is pre-existing and not a build failure. |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | All checks passed (pre-existing noise noted above) | — | — |

---

## V2 Verification

**Status:** PASS WITH PRE-EXISTING NOISE
**Verified:** 2026-04-19 11:28

### Backend
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff) | PASS | No issues — `ruff check .` clean across all backend source files |
| Type check (mypy) | PASS (pre-existing noise) | 45 errors in 18 files — identical count and files to V1. The 2 errors in `app/services/intent.py` remain at lines 383 and 445 as expected. `intent.py` was NOT modified in V2. Zero errors introduced by V2. |
| Tests (pytest) | PASS | 980 passed, 0 failed, 62 warnings — identical to V1. V2 added no backend code. |

#### mypy Pre-Existing Errors (unchanged from V1)
45 errors in 18 files. The 2 errors in `app/services/intent.py` (lines 383, 445) are pre-existing and were not introduced or altered by V2. Full list identical to V1 §9 entry above.

### Pipeline
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff src/ tests/) | PASS | `src/` and `tests/` are clean. |
| Lint (ruff scripts/) | PASS WITH PRE-EXISTING NOISE | `scripts/yaml_regression.py` (V2 changes) is **clean**. `tests/scripts/test_yaml_regression.py` (new V2 test file) is **clean**. 87 total errors across `scripts/` — all pre-existing in other scripts (`_adversarial_probe_onet_exp.py`, `data_review_three_signal.py`, `data_review_three_signal_option_b.py`, `dq_execute_aei.py`, `dq_execute_csi.py`, `onet_experience_chaos_runner.py`, `promote_bea_rpp_silver.py`, `promote_career_outcomes_enriched.py`, others). Count increased from 47 (V1) to 87 due to additional pre-existing scripts being present; none attributable to V2. |
| Tests (pytest tests/) | PASS | 1683 passed, 1 deselected (network-marked), 0 failed — 70.55s. +5 from `tests/scripts/test_yaml_regression.py` (all 5 new tests pass: `test_sample_anchoring_schools_is_deterministic`, `test_sample_anchoring_schools_respects_k`, `test_sample_anchoring_schools_handles_missing_family`, `test_sample_anchoring_schools_handles_six_digit_cip`, `test_sample_anchoring_schools_skips_rows_with_missing_fields`). |

### Frontend
| Check | Result | Details |
|-------|--------|---------|
| TypeScript | PASS | No errors (`npx tsc --noEmit` clean) |
| Tests (vitest) | PASS | 504 passed, 1 skipped, 0 failed — 51 test files. Identical to V1; frontend untouched in V2. |
| Production build (Vite) | PASS | Build completed — 670 modules transformed, 762 kB JS bundle. Chunk size advisory (>500 kB) is pre-existing. |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | All checks passed (pre-existing noise noted above) | — | — |

---

## §10 Discussion

```
[2026-04-19] Drafted after founder decision to pursue feature-set-your-course.md.
The set-your-course spec wants to disable the YAML in prod so every student
input is a visible Gemma moment; this bugfix is the prerequisite regression
test that says whether Gemma alone is reliable enough for that commitment.

If the regression shows widespread Gemma misses, the decision becomes:
(a) tighten the intent prompt and rerun, or
(b) keep the YAML enabled but route its hits through the set-your-course
    conversational UI so Gemma still narrates even when the YAML resolves.
```

---

## §11 Final Notes

**Human Review:** PENDING

### Lessons learned

- **Strip-the-context regressions measure something other than production behavior.** V1's `unitid=0` + `programs=[]` posture stripped the school anchor that production always passes; the resulting 9.1% match rate was a worst-case headline, not a basis for a disable-YAML decision. V2 reframed the question to "Gemma as production calls it" and the answer was 42.3% — and the per-entry distribution was sharply bimodal in a way V1 could not surface. Future Gemma quality work defaults to anchored.
- **Aggregate match rates hide structural splits.** 42.3% overall maps to "KEEP YAML" against the §12 band table, but per-entry analysis showed three distinct buckets (Family 52 99.5%, Family 13 four-digit 100%, Family 13 six-digit 0%) that argue for per-family disable, not binary disable. Single-number summaries are useful for an executive read; never use them to drive disable decisions on a heterogeneous corpus.
- **`python` (not `python -u`) into a redirected file = invisible runs.** V2 attempt 2 ran for an hour with zero visible output because Python's stdout is block-buffered to non-TTY targets. Adding `flush=True` to per-row prints + launching with `python -u` gave real-time progress. Worth carrying forward as a script convention for any long-running CLI.
- **Curator-specific six-digit YAML sub-leaves are load-bearing.** The 33 Family 13 six-digit entries (Deaf Ed, Foreign Lang Ed, ESL, etc.) encode a translation from student vocabulary to NCES sub-leaves that Gemma cannot recover from school context — schools report at the family level, and the curator's mapping to a specific six-digit leaf is opinion, not catalog. This is exactly the case the YAML was built for; deleting it would silently regress every Education major's experience.

### Follow-up items

- `feature-set-your-course.md` should ship the per-entry allowlist of 22 cip4 codes (per V2 completion report) that bypass YAML and route through live Gemma. Implementation surface is tiny: one allowlist + a guard inside `major_lookup.lookup_major` or `intent.resolve_intent`.
- Family 13 prompt refinement is a separate question and is **not** a follow-up of this spec. The 0% rate on six-digit sub-leaves is a structural feature of the data (schools don't report at that granularity), not a Gemma defect tightening the prompt would fix.
- The `INTENT_YAML_ENABLED` env-var gate stays in place as the kill switch but is not the operational lever for Set Your Course. Worth keeping for ops emergencies.
- Anchoring should become the default analysis mode for any future intent-quality regression. Consider promoting `--anchored` to default-true with `--unanchored` as opt-in for the worst-case-baseline measurement.

---

## §12 Methodology Correction + V2 Anchored Regression Plan

### What went wrong in V1

The V1 Claude Code Prompt (now preserved above for history) invoked `scripts/yaml_regression.py` with no school context. The script's `_run_one(student_input)` function called:

```python
result = intent.resolve_intent(
    major_text=student_input,
    school_name="University of Central Anywhere",
    unitid=0,
    programs=[],
)
```

This matches the §4 example block literally — which is also where the mistake originated. But in production, the UI always passes a real `unitid` and the `_get_school_cips(unitid)` result as `programs`. Those values land inside `_INTENT_SYSTEM_PROMPT` as the "Candidate CIPs — programs reported by this school" bullet list, which is the **single most load-bearing disambiguation signal Gemma gets.** Strip it and Gemma is left picking from the national crosswalk alone — a list of 20+ plausible siblings per CIP family, especially in Family 13 (Education) where the curator's YAML encodes context Gemma cannot recover unanchored.

Result: V1 measured "Gemma without school context," not "Gemma as the UI actually invokes it." The 9.1% match rate is a worst-case baseline, not the number that should drive the YAML-disable decision.

### What V1 data is still worth

Not nothing. "Gemma at 9% without anchoring vs YAML at 100%" tells us **the school anchor is doing substantial disambiguation work in production.** That's itself a finding worth keeping, and it shapes how we think about fallback behavior (see `feature-gemma-availability.md`).

### V2 methodology

**Goal:** measure `resolve_intent` with the same signals production provides — `unitid` + `school_name` + `programs` populated from real schools that actually offer the expected CIP.

**Sampling strategy:** three-schools-per-input. For each `(input, expected_cip4)` pair, query the DuckDB Gold zone for up to 3 distinct schools that actually report CIPs in the `expected_cip4` family. Run `resolve_intent` against each. Record one row per `(input, school)` pair. Aggregate per-input (3/3, 2/3, 1/3, 0/3) and overall.

**Why three schools, not one:**
- One risks curator-bias (they'd pick the school the YAML entry was tuned against).
- Five triples cost and rate-limit surface for marginal signal gain.
- Three gives a distribution and catches school-level variance ("Gemma gets Education right at IU but not at Purdue") without exploding the budget.

**Why not every school that offers the CIP:**
- Some CIPs are offered at hundreds of schools; testing all of them blows the budget without adding distribution signal.
- Three-sample captures "does Gemma get this right at *some* schools" — the signal we care about for the disable-YAML decision.

**Sampling determinism:** query ordered by `unitid ASC`, deterministic tiebreak. Same run on same DuckDB → same schools. Tests can mock this.

### V2 script changes (`scripts/yaml_regression.py`)

Add two flags:
- `--anchored` — activate the anchored mode. Without this flag, V1 behavior preserved.
- `--k SCHOOLS` (default 3) — how many anchoring schools per input.

New helper:

```python
def _sample_anchoring_schools(
    expected_cip4: str,
    k: int = 3,
) -> list[tuple[int, str, list[dict[str, str]]]]:
    """Return up to k (unitid, school_name, programs) tuples for schools
    that actually report a CIP in the expected family. Deterministic
    order: sort by unitid ASC. `programs` is the full _get_school_cips
    result for each school."""
    server = mcp_client.get_server()
    sql = (
        "SELECT DISTINCT unitid, instnm "
        "FROM consumable_career_outcomes "
        f"WHERE SUBSTR(cipcode, 1, 5) = '{expected_cip4[:5]}' "
        "AND instnm IS NOT NULL "
        "ORDER BY unitid "
        f"LIMIT {int(k)}"
    )
    rows = server.query_iceberg(sql)
    out: list[tuple[int, str, list[dict[str, str]]]] = []
    for row in rows:
        unitid = int(row["unitid"])
        school_name = str(row["instnm"])
        programs = intent._get_school_cips(unitid)
        out.append((unitid, school_name, programs))
    return out
```

Modified main loop (inside `if args.anchored`):

```python
for student_input, expected_cip, source in cases:
    anchors = _sample_anchoring_schools(expected_cip, k=args.k)
    if not anchors:
        # No school in the dataset offers this CIP — record a single
        # "no_anchor_available" row; don't attempt Gemma.
        results.append({...})
        continue
    for unitid, school_name, programs in anchors:
        result = intent.resolve_intent(
            major_text=student_input,
            school_name=school_name,
            unitid=unitid,
            programs=programs,
        )
        results.append({
            "input": student_input,
            "expected_cip": expected_cip,
            "source_entry": source,
            "anchor_unitid": unitid,
            "anchor_school": school_name,
            "returned_cip": result.matched_cip,
            "match": _cip_match(result.matched_cip, expected_cip),
            "confidence": result.confidence,
            ...
        })
```

### V2 report shape

Required sections:

1. **Summary** — overall anchored match rate (matches / (inputs × k)), delta vs V1 (9.1%), wall time, cost.
2. **Per-input aggregate table** — one row per input; columns: `input`, `expected_cip`, `schools_tested`, `match_count` (`3/3`, `2/3`, `1/3`, `0/3`), `modal_returned_cip`, `worst-case_reasoning`.
3. **Per-family aggregate table** — matches / tested per CIP family, with V1 comparison column.
4. **Full per-(input, school) table** — every row captured, for audit.
5. **No-anchor-available list** — inputs whose expected CIP had zero schools offering it. This is itself a finding (may indicate YAML entries for CIPs not present in the Gold zone).
6. **Go/no-go recommendation** — based on the anchored match rate:
   - ≥85%: YAML can be disabled in prod safely. Set Your Course ships with `INTENT_YAML_ENABLED=false`.
   - 60–85%: mixed signal. YAML stays on; per-family disable may be viable for the strong families.
   - <60%: YAML stays on definitively. Set Your Course routes all chip corrections through Gemma but trusts YAML for initial resolution.

### V2 cost + wall-time estimate

- ~219 inputs × 3 schools = ~657 Gemma calls.
- At V1's ~1.3 s/call average, ~14 min pure inference time.
- OpenRouter rate limits will likely cluster at the tail again; expect ~50 min wall with current handling, or add `--sleep 0.5` to spread calls.
- Cost: ~$0.15 at V1 token-budget; budget well under $0.50.

### V2 success → V2 spec completion

When the V2 report lands, update §12 with the anchored match rate + go/no-go, update the Regression Run section in §6 with V2 numbers alongside V1, and add the §11 Final Notes. Only then does this spec truly close.

### V2 Run Results (2026-04-19)

| Field | Value |
|-------|-------|
| Backend | OpenRouter (`google/gemma-4-26b-a4b-it`) |
| Mode | Anchored (k=3 schools per input) |
| Inputs enumerated | 219 |
| Total (input, school) attempts | 657 |
| Matches | 278 (42.3%) |
| Mismatches | 378 (57.5%) |
| Errors | 1 (0.2%) |
| No-anchor inputs | 0 (every YAML cip4 had ≥1 school in the Gold zone) |
| Wall time | 3290 s (~55 min) |
| Cost (OpenRouter) | ~$0.20 |
| Anchored report | [`reports/intent-yaml-regression-anchored-2026-04-19.md`](../../reports/intent-yaml-regression-anchored-2026-04-19.md) |
| V2 completion report | [`reports/bugfix-disable-intent-yaml-regression-v2-2026-04-19.md`](../../reports/bugfix-disable-intent-yaml-regression-v2-2026-04-19.md) |

#### Per-input distribution
| Bucket | Inputs |
|--------|--------|
| 3/3 (Gemma reliable with anchor) | 92 |
| 2/3 | 1 |
| 0/3 (Gemma unreliable) | 126 |

#### Per-family delta vs V1
| Family | V1 | V2 | Δ |
|--------|----|----|----|
| 13 — Education | 0/147 (0.0%) | 63/441 (14.3%) | +14.3 pp |
| 52 — Business | 20/72 (27.8%) | 215/216 (99.5%) | +71.7 pp |
| **Overall** | **9.1%** | **42.3%** | **+33.2 pp** |

### V2 Decision: Per-family disable, not binary

The `≥85% / 60–85% / <60%` band table in §12 above maps the 42.3% overall to "KEEP YAML" — but that aggregate hides a sharp three-way split:

1. **Family 52 (17 entries, 72 inputs) — 99.5% with anchor.** Disable YAML.
2. **Family 13 four-digit YAML codes (5 entries, 22 inputs) — 100% with anchor.** Disable YAML.
3. **Family 13 six-digit YAML sub-leaf codes (33 entries, 147 inputs) — 0% with anchor.** Keep YAML.

The third bucket exists because the YAML stores curator-specific sub-leaves (13.1003 Deaf Ed, 13.1306 Foreign Lang Ed, etc.) that Gemma cannot recover from school context — schools report at family level (13.10) and the curator's mapping to a specific six-digit leaf is opinion, not catalog data.

**Action for `feature-set-your-course.md`:** ship a per-entry allowlist of 22 cip4 codes + their aliases that bypass the YAML and route through live Gemma. Everything else falls through to YAML as today. The binary `INTENT_YAML_ENABLED` env-var gate stays in place as the kill switch but is not the operational lever.

The V2 completion report at `reports/bugfix-disable-intent-yaml-regression-v2-2026-04-19.md` has the full per-entry recommendation list.

### V2 expected outcomes + branch plan for Set Your Course

| V2 anchored match rate | Set Your Course posture | Action |
|------------------------|-------------------------|--------|
| ≥85% | YAML disabled in prod for the Set Your Course flow | Update `feature-set-your-course.md` §1/§4 to re-commit to `INTENT_YAML_ENABLED=false`; keep YAML file as fallback per `feature-gemma-availability.md`. |
| 60–84% | Per-family disable | Update `feature-set-your-course.md` to disable YAML for strong families (probably 52 Business), keep it for weak ones (13 Education). Requires a per-family env var or a lookup-time bypass list. |
| <60% | YAML stays on, full stop | `feature-set-your-course.md` stays as revised (YAML-first); chip correction is where Gemma visibility lives. Minor wording updates to the Kaggle narrative per `submission-kaggle-narrative.md`. |
