# Feature: Gemma Alias Curation for major_to_cip.yaml

## Claude Code Prompt

```
Read the spec at docs/specs/feature-gemma-alias-curation.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review §1–§4 for: data-flow correctness across the
     Gemma call boundary, idempotence guarantees, pipeline placement, and the
     read/write boundary between curator edits and automated edits to
     data/reference/major_to_cip.yaml.
   - Invoke @fp-data-reviewer to review: alias validation rules, collision
     detection across families, coverage-floor (soc_n cutoff), and impact on
     the intent substitution path at backend/app/services/intent.py +
     src/mcp_server/futureproof_server.py.
   - Invoke @genai-architect (ad-hoc) to review §4 Gemma Prompt Design — the
     prompt body, JSON schema, fallback, and rate-limit posture under both
     Ollama and OpenRouter.
   - All three write findings to §5.
   - If APPROVED: proceed to step 2.
   - If CHANGES REQUESTED (Significant): STOP, alert human.
   - If REJECTED (Blocker): STOP, alert human.

2. DESIGN VISION — SKIPPED (backend-only spec, no UI surface).

3. IMPLEMENTATION
   - Implement §4 exactly. Touch only the files listed in the File Changes
     table. Use the existing gemma_client.generate API; do not refactor it.
   - BEFORE coding: read §4 Testing Impact Analysis. Note which tests are
     Confirmed Safe — if any of those fail, STOP and escalate.
   - Log all work to §6. Run backend (ruff + mypy + pytest) and pipeline
     (ruff + pytest at repo root) to verify the build is green when you finish.
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts).
     After 3 failed attempts, escalate to human via §10 and set status BLOCKED.

4. TESTING
   - Invoke @test-writer to add the cases in §4 "New Tests Required". P0 first.
   - Run the full pytest suite (cd backend && pytest, uv run pytest at repo
     root). Every failure must be acknowledged in §7. Never silently skip.

5. DESIGN AUDIT — SKIPPED (backend-only spec).

6. CODE REVIEW
   - Invoke @faang-staff-engineer for security/performance/error-handling
     review of the alias generator, the validator, and the YAML merger.
     Writes verdict to §8.

7. VERIFICATION
   - Invoke @fp-builder to run ruff + mypy + pytest (root + backend) +
     TypeScript + vitest + Vite build.
   - YAML schema unchanged → no frontend regression expected, but the build
     gate still runs. Logs results to §9.

8. COMPLETION
   - Update Status to COMPLETE. Tick every Success Criterion in §1.
   - Move spec to docs/specs/completed/.
   - Write report to reports/feature-gemma-alias-curation-YYYY-MM-DD.md.
   - Run scripts/alias_major_entries.py once in implementation mode against the
     current YAML and commit the resulting aliases in a SEPARATE commit with
     message "data(aliases): first pass over auto-generated entries" so the
     diff is reviewable standalone.
```

---

## Status: SUPERSEDED (2026-04-19) — do not execute

> **This spec is architecturally dead.** Captured here for history. Superseded by `docs/specs/feature-set-your-course.md` (flagship) + `docs/specs/feature-receipts.md` (data provenance) + the reinforcement-loop design. The YAML file it proposed enriching is being retired from the resolution path entirely; pre-generating aliases is explicitly the wrong direction (reduces visible Gemma use — the opposite of what the Kaggle submission should showcase, per PM review on 2026-04-19).
>
> Original spec received CHANGES REQUESTED from `@fp-architect`, `@fp-data-reviewer`, and `@genai-architect`; findings recorded in §5. Those critiques are a useful reference for anyone trying to do pipeline-time Gemma generation responsibly, but this specific feature does not ship.
>
> **If you're here looking for alias curation:** the student-visible community-suggestions surface in Set Your Course §4 does the same job through user behavior rather than pipeline-time guessing. See also `docs/convos/2026-04-19-gemma-core-pivot.md` Topic 4 (PM's cache pushback) and Topic 13 (reinforcement-loop design) for the full arc.

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-19 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-04-19 |
| Blocked By | — |
| Related Specs | `docs/specs/completed/bugfix-broad-cip-substitution-and-intent.md`, `docs/specs/completed/spike-gemma-intent-openrouter.md`, `docs/specs/completed/spike-gemma-intent-resolution.md`, `docs/specs/completed/feature-gemma-tiered-matching.md`, `docs/specs/concept-gemma-intent-cache.md` |

---

## §1 Feature Description

### Overview

Use Gemma to propose student-friendly aliases for every auto-generated entry in `data/reference/major_to_cip.yaml`, preserving hand-curated entries verbatim. Ship the generator as a standalone re-runnable script (`scripts/alias_major_entries.py`) that integrates cleanly with `scripts/regenerate_major_to_cip_yaml.py` so alias curation becomes a repeatable pipeline step — not a one-time hackathon chore.

### Problem Statement

The auto-generation spec just added 342 new entries to `major_to_cip.yaml` (398 total, 39 families). Each auto-entry has `aliases: []` and a bureaucratic NCES `major` title like `"Registered Nursing/Registered Nurse"` or `"Computer and Information Sciences, General"`. `backend/app/services/major_lookup.py::lookup_major` does case-insensitive **exact** match against `major` + every `alias`. A student typing `"nursing"` or `"CS"` hits zero of those auto-entries. They fall through to Gemma's intent resolver — the exact non-determinism the YAML short-circuit was designed to eliminate.

Hand-writing 342 × (3–8) aliases is hours of grunt work that decays when NCES ships a new CIP edition (2020 added family 30; 2025 will add more). An automated pipeline step that re-runs on data refresh is the right shape.

Constraints that shape the design:

- Hand-curated entries (56 today) are **load-bearing**. Their aliases were chosen against real failure modes. The generator MUST NOT overwrite them.
- Gemma is already integrated via `gemma_client.generate` — dual-backend (Ollama / OpenRouter) via `.env INFERENCE_BACKEND`. Don't reinvent the transport.
- Aliases must be **exact-match-ready** (the lookup doesn't fuzzy-match), which constrains what counts as a valid alias (short, deduplicated, no cross-entry collisions).
- The pipeline MUST be re-runnable safely. Partial failure (Gemma rate-limits mid-run) must leave the YAML in a consistent state and be recoverable.

### Success Criteria

- [ ] `scripts/alias_major_entries.py` exists, runs from repo root, accepts `--dry-run`, `--force`, `--limit N`, `--family XX`, `--backend ollama|openrouter` flags.
- [ ] Running the script against the current YAML produces 2–8 aliases per targeted entry, all passing the validator, committed atomically (success OR rollback on validator error).
- [ ] Hand-curated entries (any entry whose `aliases` is already non-empty at run start) are preserved byte-for-byte — including ordering within aliases.
- [ ] Idempotence: re-running without `--force` skips entries already processed by a prior run (tracked via sidecar log `data/reference/aliases_log.jsonl`). `--force` regenerates but still preserves non-empty human aliases unless `--force-overwrite-human` is set (default off, dangerous).
- [ ] Validator rejects: empty aliases, aliases >40 chars, aliases <2 chars, aliases equal to any entry's `major` (case-insensitive), aliases that appear in >1 entry (cross-entry collision), aliases failing `^[a-zA-Z0-9 ./&'-]+$` (no weird unicode, no newlines).
- [ ] `regenerate_major_to_cip_yaml.py --with-aliases` invokes the alias generator as a post-step for new entries only; without the flag the regenerator behaves exactly as today.
- [ ] Observability: per-run JSONL report at `reports/alias_curation_YYYY-MM-DD-HHMMSS.jsonl` captures per-entry `{cip4, major, proposed, accepted, rejected_with_reason, latency_ms, tokens_used, backend, model}`. Stdout summary prints accepted/rejected totals and total cost estimate.
- [ ] Cost under `$1.00` for a full 342-entry pass on OpenRouter at current `google/gemma-4-26b-a4b-it` pricing. Local Ollama runs are free but slower (bounded at 2 req/s as today).
- [ ] Full test suite (`uv run pytest`, `cd backend && pytest`, `cd frontend && npx vitest run`) passes unchanged. Ruff + mypy clean. No frontend tests added (no frontend change).
- [ ] `logs/gemma.jsonl` captures every `gemma_client.generate` call made by the script — same observability discipline as every other Gemma caller.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Pass **every auto-generated entry with `soc_n >= 3`**, not top-N by IPEDS enrollment. | (a) Full-YAML cost is under $1 — top-N optimization buys cents for hours of extra work. (b) IPEDS Completions data isn't in the pipeline today; adding it for prioritization only would create a new data dep for no real gain. (c) `soc_n < 3` entries have no meaningful career mapping regardless — aliasing them wastes tokens and invites false-positive matches to programs with no career signal. Cutoff belongs on the crosswalk side, not curator time. | (a) Top-100 by IPEDS enrollment — rejected, introduces new data dep; cost savings are trivial. (b) Every entry including `soc_n < 3` — rejected, wastes budget on programs the student can't meaningfully explore. (c) Aliasing on demand per-student-miss — rejected, defeats idempotence; can't be pre-computed, adds latency to every miss. |
| 2 | Track processed entries in a **JSONL sidecar log** at `data/reference/aliases_log.jsonl`, not in the YAML itself (no `aliases_source` field). | (a) Keeping the YAML shape unchanged avoids breaking every reader that consumes it (both backend `major_lookup.py` and MCP server `_load_major_to_cip_lookup`) — we don't need a migration. (b) The log is a processing artifact, not content — separating it respects the "YAML is source of truth for lookup, log is bookkeeping" split. (c) Git-tracked log means PR diffs show exactly what was processed when. | (a) Add `aliases_source: human\|gemma-v1` field to every entry — rejected, forces a YAML shape change that every reader must opt into; silently breaks any third-party script. (b) In-file comments marking auto-generated entries — rejected, PyYAML doesn't round-trip comments without ruamel, and we'd be parsing comments for state. (c) Separate YAML-of-processed-entries — rejected, JSONL is append-only-safe and partial-write-safe in a way YAML isn't. |
| 3 | The script is **standalone AND invoked as a `--with-aliases` post-step** from `regenerate_major_to_cip_yaml.py`. | (a) Standalone is needed for re-aliasing without regenerating the YAML skeleton (e.g. improving the prompt and re-running). (b) Regenerator post-step is needed because after a crosswalk refresh adds new entries, those new entries need aliases before the next session. (c) Default-off (`--with-aliases` opt-in) keeps the cheap fast path for people who just want to refresh the skeleton without burning tokens. | (a) Only as a post-step — rejected, can't iterate on prompt without regenerating everything. (b) Only standalone — rejected, new entries from crosswalk refresh would ship without aliases until someone remembered to run the aliaser separately. |
| 4 | Use `gemma_client.generate` via the existing OpenAI-compatible API; do NOT add a new transport. Prompt body lives in `scripts/alias_major_entries.py::_ALIAS_SYSTEM_PROMPT` and is duplicated with a DUPLICATE banner if ever copied elsewhere, per the intent-prompt discipline. | Every Gemma call site shares the same transport, retry policy, logging, and backend switch. Duplicating that plumbing is a bug factory. The intent prompt already has DUPLICATE discipline (backend/app/services/intent.py:67) — mirror it. | Separate Gemma client just for alias generation — rejected, three call sites means three bug surfaces. |
| 5 | **One entry per Gemma call** (not batched), with bounded parallelism (asyncio semaphore, max 4 in flight for OpenRouter / 1 for Ollama). | (a) Batch prompts get truncated by Gemma at scale — students have seen this in the intent path. (b) Per-entry calls are observability-friendly: each `logs/gemma.jsonl` entry maps to exactly one `(cip4, major)` pair. (c) Failure isolation: one bad response doesn't poison 40 entries. (d) Parallelism ceiling matches `gemma_client`'s existing semaphore posture — don't pick a fight with rate limits. | (a) Batch 10 entries per call with JSON-per-entry output — rejected, higher failure surface, harder to log/debug, marginal cost savings (~20 %). (b) One-call per family (15–40 entries) — rejected, the Gemma JSON mode can't reliably emit nested JSON at that size. |
| 6 | Validator rejects aliases matching `^[a-zA-Z0-9 ./&'-]+$`, length 2–40, no cross-entry collisions, no collision with any `major` anywhere in the YAML. | Aliases get `.lower().strip()` then exact-match against typed text. Unicode or punctuation students don't type is a dead-weight alias that costs file space and scans against every input. 40-char cap is generous (`"Mechanical Engineering Technology"` is 32). Cross-entry collision would let two different cip4s match the same typed text non-deterministically (first one wins in YAML order — worse than Gemma). | (a) No length limit — rejected, Gemma occasionally emits entire sentences. (b) Unicode-permissive regex — rejected, unnecessarily widens the attack surface. (c) Permit same alias across entries — rejected, breaks first-match-wins semantics. |
| 7 | **No automatic commit of generated aliases.** The script writes the YAML + the log, but the human runs `git diff` and commits when they're satisfied. | The YAML is the source of truth for the live app. Silent commits would make it trivial for a broken prompt to ship garbage into the lookup. The cost of a manual `git commit` is seconds. | Auto-commit with sign-off from a second Gemma pass — rejected, two models voting on student-visible content is a compounding failure mode. |
| 8 | **No CI scheduling** of alias generation. Manual / on-demand only, documented in the script's `--help`. | CI runs would spend real money non-deterministically, create merge-conflict churn on the YAML, and surface Gemma provider outages as red builds. Data refresh is a deliberate human act; aliasing belongs in the same flow. | Cron-schedule a nightly run — rejected. GitHub Actions run on every push triggering re-aliasing — rejected. |
| 9 | **Preserve hand-curated aliases verbatim.** If an entry has `aliases: [...]` non-empty at run start, skip it (don't call Gemma). `--force-overwrite-human` exists but prints a red warning and requires interactive confirmation. | The curated aliases are chosen by someone who watched students fail. Nothing Gemma produces is worth clobbering that. The interactive gate is the "if this fires, you definitely meant it" tripwire. | Merge Gemma aliases into human-curated lists — rejected, makes it ambiguous which aliases are which and which ones can be safely removed. |
| 10 | The JSONL sidecar log is **committed to git** (not gitignored). | The log is a reproducibility artifact: "why did this entry have these aliases?" is answered by one `git log` on the sidecar. Committing it also means PRs show exactly which entries were processed when alias coverage changes. | Gitignore the log — rejected, loses the reproducibility trail. Store in `reports/` instead — rejected, `reports/` is per-run ephemera, the log is cumulative state. |

### Constraints

- `data/reference/major_to_cip.yaml` schema is **unchanged** by this spec. No new fields on entries.
- `backend/app/services/major_lookup.py` and `src/mcp_server/futureproof_server.py::_load_major_to_cip_lookup` are **not touched**. Alias lookup semantics (case-insensitive exact match, first-match-wins) stay exactly as today.
- `gemma_client.generate` is not touched. Prompt + parsing logic lives in the new script.
- The regenerator script (`scripts/regenerate_major_to_cip_yaml.py`) gains ONE new optional flag (`--with-aliases`). Default behavior unchanged.
- OpenRouter budget: <$1 per full-YAML pass.
- Ollama: must run end-to-end in under 30 minutes on an M-series Mac at default concurrency.
- All `gemma_client.generate` call sites keep their existing deterministic fallback. The alias generator's fallback is "skip this entry, log the failure, continue" — NOT "guess aliases from the title."
- `logs/gemma.jsonl` captures every call (per global invariant).

### Out of Scope

- **Changing `lookup_major` / `_find_major_intent` semantics.** Aliases stay exact-match. Fuzzy matching is a separate spec.
- **Refactoring `gemma_client`.** Concurrency semaphore, retry policy, and logging stay exactly as today.
- **Changing the intent Gemma prompt.** That's `backend/app/services/intent.py::_INTENT_SYSTEM_PROMPT` and belongs to a different spec.
- **Adding IPEDS Completions data to the pipeline.** The top-N prioritization alternative (§2 Decision #1) is rejected; this spec doesn't touch Brightsmith ingestion.
- **Cross-family substitution.** Substitution still fires only when `matched_cip` family == `cipcode` family. Aliases make more student-typed strings match a specific cip; they don't widen the substitution window.
- **Aliasing the `major` field itself** (e.g. Gemma suggesting "Nursing" as the canonical name for the NCES "Registered Nursing/Registered Nurse" entry). Canonical names stay NCES; aliases are the student-typed layer.
- **UI surface in the student-facing app.** No React / vitest change.
- **Frontend `MajorSelection.cipCode` / `parentCip` contract.** That's the IU+Marketing fix territory, not alias curation.

---

## §3 UI/UX Design

**SKIPPED (backend-only spec).** The user-visible improvement is "more student-typed major strings deterministically match the YAML short-circuit instead of falling through to Gemma's intent resolver." The screens that render the result are unchanged.

---

## §4 Technical Specification

### Architecture Overview

One new standalone script (`scripts/alias_major_entries.py`) plus a small change to the existing regenerator (`scripts/regenerate_major_to_cip_yaml.py`) that adds an optional `--with-aliases` post-step. The script:

1. Loads the current YAML.
2. Loads the sidecar log (`data/reference/aliases_log.jsonl`) to identify entries already processed.
3. For each entry that needs aliasing (auto-generated, not previously processed, or forced), calls `gemma_client.generate` with a system prompt that returns JSON of candidate aliases.
4. Runs candidates through the validator (length, regex, cross-entry collision, major-collision).
5. Merges accepted aliases into the YAML entry (preserving existing aliases; dedupe case-insensitively).
6. Atomically writes the updated YAML and appends one line per processed entry to the sidecar log.
7. Writes a per-run report at `reports/alias_curation_YYYY-MM-DD-HHMMSS.jsonl` and a stdout summary.

Dependencies stay minimal: `pyyaml` (already vendored), `httpx` via `gemma_client` (already vendored), stdlib otherwise. No new packages.

Failure modes and containment:

- **Gemma transport failure (timeout, 5xx, empty response):** log `rejected_reason: "gemma_error"`, continue to next entry. The log captures the error string. Re-running without `--force` picks up exactly where it left off.
- **JSON parse failure:** log `rejected_reason: "bad_json"`, continue.
- **All proposed aliases rejected by validator:** entry gets `aliases: []` unchanged but IS logged as processed (so re-runs skip it). Log captures all rejection reasons. Curator can inspect and re-run with an improved prompt via `--force`.
- **Rate limit hit (429):** the existing `gemma_client` retry policy handles transient 429s. If it gives up, treat as `gemma_error` and continue — don't abort the whole run.
- **User aborts mid-run (Ctrl-C):** every entry written to the YAML has already been written to the log. Re-running picks up cleanly.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `/Users/jcernauske/code/bright/futureproof-data/scripts/alias_major_entries.py` | Create | The alias generator. Loads YAML + log, iterates targetable entries, calls Gemma one entry at a time (bounded async concurrency), validates, merges, writes YAML + appends log line per entry, writes per-run report. CLI flags: `--dry-run`, `--force`, `--force-overwrite-human`, `--limit N`, `--family XX`, `--backend ollama\|openrouter`, `--verbose`. Entry point under `if __name__ == "__main__"`. |
| `/Users/jcernauske/code/bright/futureproof-data/scripts/regenerate_major_to_cip_yaml.py` | Modify | Add optional `--with-aliases` flag. When set, after writing the YAML, invoke `alias_major_entries.main([...])` with the same backend config and a `--limit` scoped to only NEW cip4s added in this run. Default behavior (no flag) unchanged byte-for-byte. |
| `/Users/jcernauske/code/bright/futureproof-data/data/reference/aliases_log.jsonl` | Create | Sidecar log. One JSON object per line, schema defined below. Committed to git. New file starts empty; first run appends 342-ish lines. |
| `/Users/jcernauske/code/bright/futureproof-data/data/reference/major_to_cip.yaml` | Modify | Output target — aliases merged into auto-generated entries. Hand-curated entries untouched. This is the *artifact* of running the script, not a code change — committed separately from the script code. |
| `/Users/jcernauske/code/bright/futureproof-data/tests/scripts/test_alias_major_entries.py` | Create | Unit tests for parser, validator, merger, sidecar-log reader, CLI arg parsing. All tests mock `gemma_client.generate` — no live Gemma in CI. |
| `/Users/jcernauske/code/bright/futureproof-data/tests/scripts/__init__.py` | Create | Empty file — pytest namespace marker. |
| `/Users/jcernauske/code/bright/futureproof-data/reports/.gitkeep` | Create (if not present) | Keep `reports/` tracked so per-run report writes don't fail on a fresh checkout. |

### Data Model Changes

No Iceberg schema changes. No new Pydantic models that cross module boundaries.

**New: sidecar log schema** (`data/reference/aliases_log.jsonl`, one JSON object per line):

```python
# Captured in scripts/alias_major_entries.py; internal TypedDict for type hints.
class AliasLogEntry(TypedDict):
    cip4: str                          # "52.14"
    major: str                         # canonical name at processing time
    run_id: str                        # ISO timestamp, e.g. "2026-04-19T14:32:08Z"
    backend: Literal["ollama", "openrouter"]
    model: str                         # e.g. "google/gemma-4-26b-a4b-it"
    proposed: list[str]                # raw Gemma output after JSON parse
    accepted: list[str]                # passed validator, merged into YAML
    rejected: list[dict[str, str]]     # [{"alias": "...", "reason": "..."}]
    latency_ms: int
    tokens_in: int | None              # if backend reports it
    tokens_out: int | None
    status: Literal["ok", "gemma_error", "bad_json", "all_rejected"]
    error: str | None                  # populated when status != "ok"
```

**New: per-run report schema** (`reports/alias_curation_YYYY-MM-DD-HHMMSS.jsonl`): same schema as sidecar log, but scoped to one run only. Sidecar is cumulative; report is ephemeral.

### Service Changes

No changes to `backend/app/services/` or `src/mcp_server/`. The alias generator is a pipeline-time script, not runtime code.

**New module — `scripts/alias_major_entries.py`:**

```python
"""Use Gemma to propose student-friendly aliases for major_to_cip.yaml.

Idempotent, re-runnable, and observable. See docs/specs/feature-gemma-
alias-curation.md for the full contract.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, TypedDict

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "backend"))
sys.path.insert(0, str(_REPO_ROOT / "src"))

from app.services import gemma_client  # noqa: E402

YAML_PATH = _REPO_ROOT / "data" / "reference" / "major_to_cip.yaml"
LOG_PATH = _REPO_ROOT / "data" / "reference" / "aliases_log.jsonl"
REPORT_DIR = _REPO_ROOT / "reports"

# Validator constants — justified in §2 Decision #6.
_ALIAS_RE = re.compile(r"^[a-zA-Z0-9 ./&'\-]+$")
_ALIAS_MIN_LEN = 2
_ALIAS_MAX_LEN = 40
_ALIAS_MIN_COUNT = 2
_ALIAS_MAX_COUNT = 8

# Concurrency posture. Mirrors gemma_client's semaphore — see §2 Decision #5.
_OPENROUTER_CONCURRENCY = 4
_OLLAMA_CONCURRENCY = 1

# Coverage floor. See §2 Decision #1.
# NB: we don't re-query the crosswalk here — the YAML is the source of truth
# of what entries exist. Entries with no usable career data would never have
# been emitted by the regenerator.
_MIN_SOC_COUNT = 3  # enforced upstream by regenerator; this is documentation.


class AliasLogEntry(TypedDict):
    cip4: str
    major: str
    run_id: str
    backend: Literal["ollama", "openrouter"]
    model: str
    proposed: list[str]
    accepted: list[str]
    rejected: list[dict[str, str]]
    latency_ms: int
    tokens_in: int | None
    tokens_out: int | None
    status: Literal["ok", "gemma_error", "bad_json", "all_rejected"]
    error: str | None


# DUPLICATE: this prompt body is the sole Gemma prompt for alias generation.
# If it is ever copied or referenced from another file, add a DUPLICATE banner
# to the other copy pointing here — mirror the discipline in
# backend/app/services/intent.py:67.
_ALIAS_SYSTEM_PROMPT = """\
You generate student-typed aliases for a college major entry.

The canonical major is: "{major}"
The CIP code is: {cip4} (family {family})
This entry lives in the lookup table that turns student free-text input \
into a CIP code. Your aliases are what gets matched against. They must \
be exact, literal tokens that a real student, counselor, or parent would \
type into a college planning tool.

Think: shorthand (CS, RN, ME, CompSci), common phrasings (nursing, \
engineering), misspellings (buiness, psycology), and regional variants \
(mech eng, chem eng).

Hard rules:
- Return 2-8 aliases. Never zero. Never more than eight.
- Each alias is 2-40 characters. Lowercase or mixed-case — we lowercase on lookup.
- Alphabetic characters, digits, spaces, dots, slashes, ampersands, \
apostrophes, hyphens only. No unicode. No newlines.
- Never return the canonical major text ("{major}") — that is already the \
primary match.
- Never return a single word that could plausibly match a different major. \
"Engineering" alone is not a valid alias for Mechanical Engineering — \
that collides with every other engineering major. Prefer "mech eng", \
"mechanical", "ME" instead.
- Every alias must be a string a student actually types. "Mechanical \
Engineer Who Builds Bridges" is a description, not an alias — reject it.

Respond in JSON only, no preamble, no markdown:
{{"aliases": ["alias1", "alias2", ...]}}\
"""


def _clean_alias(raw: str) -> str:
    return " ".join(raw.strip().split())


def _validate_alias(
    alias: str,
    *,
    canonical_major: str,
    canonical_major_lower: str,
    all_majors_lower: set[str],
    reserved_aliases_lower: set[str],
    entry_aliases_lower: set[str],
) -> tuple[bool, str]:
    """Return (ok, rejection_reason). See §2 Decision #6 for the ruleset."""
    if not isinstance(alias, str):
        return False, "not_a_string"
    cleaned = _clean_alias(alias)
    if not cleaned:
        return False, "empty"
    if len(cleaned) < _ALIAS_MIN_LEN:
        return False, "too_short"
    if len(cleaned) > _ALIAS_MAX_LEN:
        return False, "too_long"
    if not _ALIAS_RE.match(cleaned):
        return False, "invalid_chars"
    lower = cleaned.lower()
    if lower == canonical_major_lower:
        return False, "equals_canonical"
    if lower in entry_aliases_lower:
        return False, "duplicate_in_entry"
    if lower in all_majors_lower:
        return False, "collides_with_other_major"
    if lower in reserved_aliases_lower:
        return False, "collides_with_other_alias"
    return True, ""


async def _request_aliases_for_entry(
    entry: dict[str, Any],
    *,
    semaphore: asyncio.Semaphore,
) -> tuple[list[str], dict[str, Any]]:
    """Return (proposed_aliases, stats)."""
    ...  # see implementation notes below


def _merge_aliases_into_entry(
    entry: dict[str, Any], accepted: list[str]
) -> None:
    """Mutate entry in-place, appending accepted aliases (dedupe preserving
    original order). Preserves existing aliases verbatim — see §2 Decision #9."""
    existing = [str(a) for a in (entry.get("aliases") or [])]
    existing_lower = {a.lower() for a in existing}
    for new_alias in accepted:
        if new_alias.lower() in existing_lower:
            continue
        existing.append(new_alias)
        existing_lower.add(new_alias.lower())
    entry["aliases"] = existing


def _load_processed_cip4s(force: bool) -> set[str]:
    """Return set of cip4s already processed per the sidecar log. Empty set
    when force=True."""
    if force or not LOG_PATH.is_file():
        return set()
    out: set[str] = set()
    with LOG_PATH.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            cip4 = record.get("cip4")
            if cip4:
                out.add(str(cip4))
    return out


async def main_async(args: argparse.Namespace) -> int:
    ...  # orchestration: load YAML, filter, gather with semaphore, validate,
         # merge, write YAML, append log, emit report.


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate student-friendly aliases for major_to_cip.yaml entries "
            "via Gemma. See docs/specs/feature-gemma-alias-curation.md."
        )
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true",
                        help="Ignore sidecar log; re-process every entry.")
    parser.add_argument("--force-overwrite-human", action="store_true",
                        help="DANGER: overwrite hand-curated aliases. "
                             "Requires interactive confirmation.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--family", type=str, default=None,
                        help="Only process entries in this 2-digit family.")
    parser.add_argument("--backend", choices=["ollama", "openrouter"],
                        default=None,
                        help="Override INFERENCE_BACKEND env for this run.")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
```

**Modified module — `scripts/regenerate_major_to_cip_yaml.py`** (diff, not rewrite):

```python
# Add import at top:
from alias_major_entries import main as _run_aliaser

# Add CLI arg to main():
parser.add_argument("--with-aliases", action="store_true",
                    help="After regenerating, run the alias generator on "
                         "entries new to this run. See "
                         "docs/specs/feature-gemma-alias-curation.md.")

# After YAML_PATH.write_text(output), before the print() block:
if args.with_aliases:
    # Scope to NEW cip4s added in this run. Pass as --limit via the family
    # filter — the aliaser skips entries already in the log, so new ones
    # get aliased and existing ones don't re-run without --force.
    new_cip4s = [row["cip4"] for row in crosswalk if row["cip4"] not in existing_cip4s]
    if new_cip4s:
        _run_aliaser([])  # picks up new entries via the sidecar log gate
```

### Gemma Prompt Design

Reviewed by `@genai-architect` as part of §5.

**System prompt** (full text in `_ALIAS_SYSTEM_PROMPT` above). Design intent:

- **One entry per call** — not batched. §2 Decision #5.
- **Explicit count bounds** (2–8) stated twice in the prompt — Gemma tends to drift on count ranges when they're mentioned once.
- **Explicit format hard rules** stated before the example JSON. Gemma respects format rules better when they're upstream of the output schema.
- **Collision guidance in-prompt** — the validator enforces it, but asking Gemma to avoid "Engineering alone → Mechanical Engineering" aliases improves first-pass acceptance rate from empirically ~60 % to ~85 %.
- **JSON-only response** — identical to the intent prompt pattern, same parsing logic (`re.sub` strip markdown fences, `json.loads`).

**User message:** static. The system prompt interpolates `{major}`, `{cip4}`, `{family}` into the system body; the user message is the constant string `"Propose aliases for this major."`. Keeps the observability identical across entries (only the system prompt varies).

**Generation config:**
- `max_tokens=200` — aliases are short, 8 × 40 chars + JSON overhead fits easily under 200 tokens.
- `temperature=0.2` — mild creativity for surface variants, not high enough to invent plausible-looking-but-wrong tokens.
- Model: whatever `gemma_client.current_config().model` returns (controlled by `INFERENCE_BACKEND`).

**Fallback behavior:** on transport failure, JSON parse failure, or `all_rejected` validator result, the entry is logged with the appropriate `status` and `aliases: []` unchanged. The script continues to the next entry. This is the "deterministic fallback" required by the global Gemma-caller discipline — no silent guess-based aliases.

### Pipeline Integration

**Operating modes:**

1. **Standalone invocation** — `uv run python scripts/alias_major_entries.py`. Processes every eligible entry not in the sidecar log. Typical use: re-running after the Gemma prompt improves.

2. **Regenerator post-step** — `uv run python scripts/regenerate_major_to_cip_yaml.py --with-aliases`. Typical use: after a source-data refresh that added new entries.

3. **Scoped re-runs** — `--family 51 --force` re-aliases all Health entries (e.g. after noticing the 51.38 Nursing alias list is weak).

**Run frequency:** manual / on-demand. See §2 Decision #8. Documented in the script's `--help`.

**What runs in CI:** the pytest suite (mocked Gemma). The live script does NOT run in CI.

### Testing Impact Analysis

> **IMPORTANT:** Before finalizing this section, search the test directories for tests related to files being modified.

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `backend/tests/services/test_major_lookup.py` | `TestCrossModuleConsistency::test_matches_find_major_intent_for_every_yaml_entry` | Med | Parameterized over every YAML entry + alias. Adding ~1,500 new alias combinations across 342 entries will significantly expand test parametrization; test may hit collection-time timeout if the generator produces unexpected shapes. Mitigation: run the aliaser once before the test suite so the parametrization stabilizes, and confirm no Gemma-proposed alias collides with `_find_major_intent` semantics. |
| `backend/tests/services/test_major_lookup.py` | `TestLookup::*` | Low | Lookup semantics unchanged. Only the YAML content changes. If a Gemma alias collides with some other entry's canonical major (caught by validator), this test would still pass; validator catches the bug upstream. |
| `tests/mcp/test_cip_substitution.py` | `TestMajorIntentLookup::*` | Low | `_find_major_intent` iterates YAML entries; more aliases = more match surface. Every test's `student_major` fixture is still exact-match so no false positives expected. |
| `tests/mcp/test_cip_substitution_integration.py` | `TestIUBMarketing::*` | Low | The `"Marketing"` exact match is already in the hand-curated entry — Gemma never touches it (§2 Decision #9). Substitution path behavior unchanged. |
| `backend/tests/services/test_intent.py` | `TestDeterministicShortCircuit::*` | Low | Same reasoning. Hand-curated entries untouched. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `backend/tests/services/test_major_lookup.py::TestCrossModuleConsistency::test_matches_find_major_intent_for_every_yaml_entry` | If the parametrization becomes too expensive, switch to a sampled-subset variant (random sample of 50 entries per run, fixed seed). Document the change in §6. | Parametrization cost is a known scaling pain point and the test's contract is "pick any entry, lookup_major and _find_major_intent agree" — a sampled subset preserves that contract. |

#### Confirmed Safe

Tests that must NOT break. If any fail, STOP and escalate:

- `tests/mcp/test_cip_substitution_integration.py::TestIUBMarketing` (end-to-end Marketing-at-IU substitution)
- `tests/mcp/test_cip_substitution_integration.py::TestIUBAccounting`
- `tests/mcp/test_cip_substitution_integration.py::TestIUBFinance`
- `tests/mcp/test_cip_substitution.py::TestMajorToCipLookupPathResolution::test_loader_resolves_yaml_from_non_repo_cwd`
- `backend/tests/services/test_intent.py::TestDeterministicShortCircuit::test_short_circuit_resolves_via_yaml`
- All 500+ frontend vitest cases. They don't touch the YAML; they should pass unmodified.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `tests/scripts/test_alias_major_entries.py` | `TestValidator::test_rejects_too_short` | Alias of length 1 rejected with reason `"too_short"`. |
| P0 | `tests/scripts/test_alias_major_entries.py` | `TestValidator::test_rejects_too_long` | Alias of length 41 rejected with reason `"too_long"`. |
| P0 | `tests/scripts/test_alias_major_entries.py` | `TestValidator::test_rejects_empty_after_strip` | `"   "` rejected with reason `"empty"`. |
| P0 | `tests/scripts/test_alias_major_entries.py` | `TestValidator::test_rejects_invalid_chars` | `"nursing\n"` / `"nursing™"` rejected with reason `"invalid_chars"`. |
| P0 | `tests/scripts/test_alias_major_entries.py` | `TestValidator::test_rejects_equals_canonical` | Alias equal to the entry's own `major` rejected. |
| P0 | `tests/scripts/test_alias_major_entries.py` | `TestValidator::test_rejects_collides_with_other_major` | Alias equal to a different entry's `major` rejected. |
| P0 | `tests/scripts/test_alias_major_entries.py` | `TestValidator::test_rejects_collides_with_other_alias` | Alias equal to an alias already used in a different entry rejected. |
| P0 | `tests/scripts/test_alias_major_entries.py` | `TestMerger::test_preserves_existing_aliases_order` | Hand-curated aliases remain first, in original order. |
| P0 | `tests/scripts/test_alias_major_entries.py` | `TestMerger::test_dedupes_case_insensitively` | Adding `"Nursing"` when `"nursing"` exists is a no-op. |
| P0 | `tests/scripts/test_alias_major_entries.py` | `TestIdempotence::test_cip4s_in_sidecar_log_are_skipped` | Entries already in `aliases_log.jsonl` are not re-processed unless `--force`. |
| P0 | `tests/scripts/test_alias_major_entries.py` | `TestMockedGemma::test_happy_path_end_to_end` | With a mocked `gemma_client.generate` returning valid JSON for 3 entries, script produces expected YAML and log. |
| P0 | `tests/scripts/test_alias_major_entries.py` | `TestMockedGemma::test_gemma_error_continues` | Mocked `gemma_client.generate` raises for entry 2 of 3; entries 1 and 3 still process; entry 2 logged with `status: "gemma_error"`. |
| P1 | `tests/scripts/test_alias_major_entries.py` | `TestMockedGemma::test_bad_json_continues` | Mocked response is `"not json"`; entry logged with `status: "bad_json"`. |
| P1 | `tests/scripts/test_alias_major_entries.py` | `TestMockedGemma::test_all_rejected_marks_entry` | Every proposed alias fails validator; entry gets `aliases: []` in YAML and `status: "all_rejected"` in log. |
| P1 | `tests/scripts/test_alias_major_entries.py` | `TestCLI::test_family_filter` | `--family 52` processes only family 52 entries. |
| P1 | `tests/scripts/test_alias_major_entries.py` | `TestCLI::test_limit_caps_entries` | `--limit 5` processes at most 5 entries. |
| P1 | `tests/scripts/test_alias_major_entries.py` | `TestCLI::test_dry_run_writes_nothing` | `--dry-run` writes neither YAML nor log; prints report summary only. |
| P1 | `tests/scripts/test_alias_major_entries.py` | `TestCLI::test_force_reprocesses_logged_entries` | `--force` ignores sidecar log. |
| P1 | `tests/scripts/test_alias_major_entries.py` | `TestCurated::test_preserves_hand_curated_entries` | Entries with non-empty `aliases` at run start are skipped (no Gemma call, no log entry). Verified via mock call count. |
| P1 | `tests/scripts/test_alias_major_entries.py` | `TestAtomicWrite::test_partial_failure_leaves_yaml_consistent` | Simulate Ctrl-C between two entries; YAML written so far includes every successfully processed entry; log reflects the same set. |
| P2 | `tests/scripts/test_alias_major_entries.py` | `TestRegeneratorIntegration::test_with_aliases_flag_invokes_generator` | `regenerate_major_to_cip_yaml.py --with-aliases` calls `alias_major_entries.main`. Verified via mock. |

#### Test Data Requirements

- **Tiny YAML fixture** at `tests/scripts/fixtures/mini_major_to_cip.yaml` — 5 entries across 2 families: 2 hand-curated (non-empty aliases) and 3 auto-generated (empty aliases). Used by every test that exercises the end-to-end flow.
- **Mocked Gemma** — `unittest.mock.patch("app.services.gemma_client.generate")` that returns pre-canned JSON per entry. No live Gemma calls in CI.
- **Tmp sidecar log** via `tmp_path` fixture — every test gets a clean sidecar path to avoid state leakage.
- **Environment** — tests do NOT set `INFERENCE_BACKEND`; they mock the transport one level below.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** COMPLETE
**Reviewed:** 2026-04-19

#### System Context

This spec sits **outside the Bronze -> Silver -> Gold -> MCP zone flow**. `data/reference/major_to_cip.yaml` is a curator-maintained reference file consumed by two runtime readers (`backend/app/services/major_lookup.py::_load` and `src/mcp_server/futureproof_server.py::_load_major_to_cip_lookup`) to short-circuit Gemma intent resolution on deterministic matches. The spec adds an offline, human-triggered pipeline step that uses Gemma itself to enrich that curated file — Gemma calls crossing into curated state is the unusual seam. The script is standalone plus a post-step hook into `scripts/regenerate_major_to_cip_yaml.py`, which itself produces the YAML skeleton from `base.cip_soc_crosswalk` (Gold-ish base-zone data).

The Gemma call boundary is `gemma_client.generate_async` (async variant — see concern below). The global invariant "every Gemma call site logs to `logs/gemma.jsonl`" is satisfied automatically by the shared transport, *provided* the script uses the existing client without reimplementing the POST. Failure isolation is spec'd correctly (per-entry `status` with `gemma_error` / `bad_json` / `all_rejected`), and the sidecar log at `data/reference/aliases_log.jsonl` is the right shape for a reproducibility trail.

#### Data Flow Analysis

Source-to-destination trace, with every boundary crossing called out:

1. **Read:** `major_to_cip.yaml` -> in-memory `list[dict]` via `yaml.safe_load`. Fine.
2. **Read:** `aliases_log.jsonl` -> `set[str]` of processed cip4s. Fine.
3. **Filter -> Gemma call:** `(cip4, major, family)` -> `gemma_client.generate_async` -> JSON string. This is the only network boundary. Falls through to transport-layer retry/logging on failure. Fine, **if** the script uses `generate_async` (§4 `_request_aliases_for_entry` is `async def` but body is unspecified — see Concerns).
4. **Parse + validate:** JSON -> `list[str]` -> per-alias validator. The validator needs to see a `reserved_aliases_lower` set that is **mutated live across the run** so entry B's proposal "CS" is rejected if entry A just accepted it. §4 signature takes `reserved_aliases_lower: set[str]` as input but `main_async` orchestration is elided, so the live-update discipline isn't spec'd. See Concerns.
5. **Merge:** `_merge_aliases_into_entry` mutates the in-memory YAML entry. Correct.
6. **Persist:** YAML write + log append. This is where the atomicity story is under-specified. See Concerns.
7. **Downstream read-back:** `major_lookup._load` and MCP `_load_major_to_cip_lookup` cache at process boundary. Offline nature of the script means live servers won't see new aliases until restart — acceptable, but worth stating.

#### Contract Review

- `AliasLogEntry` TypedDict (§4 lines 209-223): well-typed, uses `Literal[...]` for `backend`/`status`, nullable `tokens_*`. Good.
- No new Pydantic models cross module boundaries. Good — keeps the YAML schema contract frozen, which matches §2 Constraint and respects `major_lookup.MajorEntry` verbatim.
- Validator return shape `tuple[bool, str]` is fine for an internal function. Not crossing a module boundary.
- Gemma call: should reuse `gemma_client.generate_async` — the correct async entrypoint. The module-level `_get_semaphore()` (default 8 concurrent) sits above the script's own semaphore (§2 Decision #5 proposes 4 / 1). That's an extra layer of guard, which is fine, but the script's local semaphore is actually the effective ceiling.
- Prompt body lives in `_ALIAS_SYSTEM_PROMPT` with the DUPLICATE-banner discipline mirroring `backend/app/services/intent.py:67`. Correct pattern.

#### Findings

##### Sound

- **Pipeline placement.** Standalone script + `--with-aliases` opt-in flag on the regenerator (§2 Decision #3) is the right seam. The regenerator's existing logic (preserve curated entries verbatim, skip excluded families 60/61/99, name-collision guard) is already the YAML's state machine; layering the aliaser as a post-step keeps both steps independently re-runnable and doesn't create a new coupling between the crosswalk refresh path and Gemma.
- **Read/write boundary between curator and automation (§2 Decision #9).** Enforced at the correct layer: pre-filter at script start (`entry.get("aliases")` non-empty -> skip, no Gemma call, no log entry). This respects the invariant "curated aliases are load-bearing" and keeps the gate outside the validator — which is right, because the validator is pure and should not know about provenance. `--force-overwrite-human` requiring interactive confirmation is the correct dead-man's switch.
- **Sidecar log at `data/reference/aliases_log.jsonl` instead of a new YAML field (§2 Decision #2).** Keeps `major_lookup.MajorEntry` TypedDict and `_load_major_to_cip_lookup` untouched — no migration for downstream readers. JSONL is append-safe in a way YAML isn't. Committing it to git (§2 Decision #10) is the right call for reproducibility.
- **No CI scheduling (§2 Decision #8).** Correct. Data-refresh is a deliberate human act and Gemma outages shouldn't produce red builds.
- **Validator ruleset (§2 Decision #6).** Rejects empty / too-short / too-long / invalid chars / equals-canonical / duplicate-in-entry / collides-with-other-major / collides-with-other-alias. Mirrors the discipline the regenerator already uses for name collisions (`reserved_names` set at `scripts/regenerate_major_to_cip_yaml.py:215-223`). First-match-wins semantics in `lookup_major` / `_find_major_intent` are preserved because cross-entry collisions are rejected upstream.
- **Failure isolation.** `gemma_error` / `bad_json` / `all_rejected` statuses are the right partitioning. Each entry is observable from the sidecar log after the fact.
- **No changes to `major_lookup.py`, `futureproof_server._load_major_to_cip_lookup`, `intent.py` substitution path.** Correct — the spec's contract is "more alias strings deterministically match; lookup semantics unchanged." The `lru_cache` on `major_lookup._load` means a live `uvicorn` won't see new aliases until restart, which is fine for an offline curator workflow (noted, not a blocker).

##### Concerns

- **Atomic YAML write is under-specified.** §1 (line 106) and §4 step 6 (line 176) both claim "atomically written" / "committed atomically" but §4 doesn't spell out the mechanism. The standard correct pattern is `tempfile.NamedTemporaryFile(dir=YAML_PATH.parent, delete=False)` -> `os.replace()`. Without this, a Ctrl-C or crash mid-write leaves `major_to_cip.yaml` truncated and breaks every reader on next process start (both `major_lookup._load` and `_load_major_to_cip_lookup` will log a warning and return an empty list, silently disabling the short-circuit). **Impact:** partial-write corruption of the primary reference file; silent lookup failure across backend + MCP. **Recommendation:** add to §4 Architecture Overview step 6: "Write YAML via `tempfile.NamedTemporaryFile(dir=YAML_PATH.parent, delete=False, mode='w')` + `os.replace(tmp, YAML_PATH)` so the swap is atomic at the filesystem layer. Append to `aliases_log.jsonl` via `open('a')` + `fh.flush()` + `os.fsync(fh.fileno())` per-entry so partial runs leave a durable log." One paragraph; no design change needed.

- **Sidecar log vs. YAML write ordering under partial failure is ambiguous.** §4 step 6 says "Atomically writes the updated YAML and appends one line per processed entry to the sidecar log" — but with concurrency=4, is the YAML re-written after every entry (342 atomic replaces) or once at the end? The test `TestAtomicWrite::test_partial_failure_leaves_yaml_consistent` (line 561) says "YAML written so far includes every successfully processed entry; log reflects the same set" — that implies per-entry persistence. But the write ordering between log-append and YAML-swap is never committed. Without an explicit rule, idempotence on re-run is racy: log entries for YAML writes that didn't happen -> re-run skips incorrectly; or YAML entries without log -> re-run re-processes (safe because the aliaser's curator-gate checks non-empty `aliases` per §2 Decision #9, but pays tokens). **Impact:** idempotence claim in §1 line 108 is conditional on a rule that isn't stated. **Recommendation:** pick one and add a sentence to §4 step 6: "Log line is appended + fsynced BEFORE the YAML tempfile swap for that entry. On re-run, the sidecar log is the authoritative 'processed' set regardless of YAML state. A crash between log-write and YAML-swap loses only the YAML persistence of that entry; the re-run will skip the logged cip4 unless `--force`." This makes the idempotence guarantee concrete.

- **Regenerator integration is misleading (§4 lines 452-470).** The snippet computes `new_cip4s = [row["cip4"] for row in crosswalk if row["cip4"] not in existing_cip4s]` but then calls `_run_aliaser([])` — passing no args. `new_cip4s` is computed and discarded. The comment on line 469 claims "picks up new entries via the sidecar-log gate," which is partly true: the aliaser will correctly skip any cip4 in `aliases_log.jsonl`, so on first `--with-aliases` invocation it'll alias every auto-generated entry (not just the newly added ones from this crosswalk refresh). **This is not a race condition** — `existing_cip4s` is captured at `scripts/regenerate_major_to_cip_yaml.py:209` before the regenerator writes the updated YAML, but the aliaser reads from disk post-write and uses the sidecar log (not `existing_cip4s`) for its gate. The gate works. But the snippet is misleading: `new_cip4s` is dead code and the comment doesn't match the actual behavior. **Impact:** on the very first `--with-aliases` invocation against a YAML that has never been aliased, it processes all 342 entries, not just the "new to this run" subset the spec text implies. That's fine for the first pass (see §1 Prompt step 8) but costs ~$1 of tokens every time someone runs `--with-aliases` on a fresh log. **Recommendation:** either (a) remove `new_cip4s` computation from the snippet and update the comment to say "the aliaser picks up every unlogged entry; the sidecar log is the gate," OR (b) add a `--cip4-allowlist` CLI flag to the aliaser and pass `new_cip4s` through it so the regenerator's post-step only touches truly new entries. Option (a) is simpler and aligns with the sidecar-log-as-gate design.

- **Cross-entry collision validation under bounded parallelism.** The validator takes `reserved_aliases_lower: set[str]` as input (§4 line 346). With concurrency=4, four entries are in flight at once. If the `reserved_aliases_lower` set is snapshotted at run start and never updated, two in-flight entries could both accept "CS" and both merge it into their own aliases list, creating exactly the cross-entry collision §2 Decision #6 forbids. §4 `main_async` orchestration is elided (line 417) so the live-update pattern is not spec'd. **Impact:** under parallelism, a latent cross-entry collision can slip past the validator and break first-match-wins semantics in `lookup_major` / `_find_major_intent`. **Recommendation:** spell out in §4 Architecture Overview that proposals are gathered in parallel via `asyncio.gather` with the semaphore but **validation + merge + log-append run serially after fan-out completes, in deterministic cip4 order**. Four concurrent Gemma calls, one sequential commit loop. Simpler than `asyncio.Lock` on a shared set, and deterministic for re-runs.

- **Sync vs async transport.** The spec's `_request_aliases_for_entry` is declared `async def` (§4 line 372) with body elided. It MUST call `gemma_client.generate_async` (not the sync `generate`) to keep the event loop free. If it calls sync `generate`, the script's `asyncio.Semaphore` is cosmetic — the single OS thread serializes all calls regardless. `generate_async` already wraps the sync `generate` in `asyncio.to_thread` (`backend/app/services/gemma_client.py:295-323`), so the transport posture is correct for both Ollama and OpenRouter. **Impact:** if an implementer picks the sync variant, the 4-wide OpenRouter concurrency claim is false and a full-YAML run takes 4x as long. **Recommendation:** add one line to §4 Gemma Prompt Design or Architecture Overview: "`_request_aliases_for_entry` calls `gemma_client.generate_async` (not `generate`) and passes `extra={'call_site': 'alias_curation', 'cip4': cip4, 'run_id': run_id}` so each `logs/gemma.jsonl` record is traceable back to its entry."

- **`logs/gemma.jsonl` `extra` correlation.** §1 Success Criteria (line 114) says "`logs/gemma.jsonl` captures every `gemma_client.generate` call made by the script." That's satisfied for free by the transport. But without passing `extra={'call_site': 'alias_curation', ...}` into `generate_async`, the audit is unattributable — every alias call looks like every other Gemma call in the log. `backend/app/services/intent.py` and the /build fan-out both set `call_site` via `extra`. **Impact:** minor observability regression compared to existing call sites. **Recommendation:** state explicitly in §4 that every `generate_async` call passes `extra={'call_site': 'alias_curation', 'cip4': cip4, 'run_id': run_id}`. Folds in with the fix above.

- **`sys.path` hack for importing `gemma_client` (§4 lines 254-258).** `sys.path.insert(0, str(_REPO_ROOT / "backend"))` then `from app.services import gemma_client`. Works from the repo root but brittle: if anyone runs the script from a different cwd that already has an `app` package on `sys.path` (e.g. a venv with `app/` installed), they'll import the wrong module silently. The regenerator script uses the same pattern (`sys.path.insert(0, str(_REPO_ROOT / "src"))` at `scripts/regenerate_major_to_cip_yaml.py:33`) so the precedent exists. **Impact:** minor; same failure mode as every other repo-root script. **Recommendation:** add a one-line comment explaining the dual `sys.path.insert`, mirroring the regenerator's comment at line 30-32.

##### Blockers

None. The architecture is fundamentally sound — the concerns are all "spell this out in §4 before coding" items, not "redesign required."

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

#### Conditions (if CHANGES REQUESTED)

1. **Spell out the atomic write mechanism in §4.** Add: "YAML is written via `tempfile.NamedTemporaryFile(dir=YAML_PATH.parent, delete=False, mode='w')` + `os.replace(tmp, YAML_PATH)`. Sidecar log append via `open('a')` + `fh.flush()` + `os.fsync()` per entry."
2. **Commit to a log/YAML write ordering rule.** Add one sentence to §4 Architecture Overview step 6 stating log line is appended + fsynced BEFORE the YAML tempfile swap for that entry, and that the sidecar log is the authoritative "processed" set on re-run.
3. **Clarify the regenerator `--with-aliases` snippet (§4 lines 462-470).** Either (a) remove the dead `new_cip4s` computation and update the comment to match the sidecar-log gate semantics, OR (b) thread `new_cip4s` through a new `--cip4-allowlist` CLI flag on the aliaser. Pick (a) for simplicity.
4. **Define the cross-entry collision discipline under parallelism.** Add to §4: "proposals gathered in parallel via `asyncio.gather` + semaphore; validation + merge + log-append run serially after fan-out in deterministic cip4 order." This avoids needing a lock on `reserved_aliases_lower` and keeps re-runs deterministic.
5. **State explicitly that `_request_aliases_for_entry` calls `gemma_client.generate_async` (not `generate`) and passes `extra={'call_site': 'alias_curation', 'cip4': cip4, 'run_id': run_id}` for `logs/gemma.jsonl` correlation.**
6. **(Minor)** Add a one-line comment explaining the dual `sys.path.insert` in §4 code sketch, matching `scripts/regenerate_major_to_cip_yaml.py:30-32`.

Once §4 is updated with the six items above, implementation can proceed. None of these require redesign — they close spec gaps that would otherwise be resolved by the implementer inconsistently.

### @fp-data-reviewer Review
**Status:** COMPLETE
**Reviewed:** 2026-04-19

#### Data Sources Affected
- `data/reference/major_to_cip.yaml` (authoritative CIP lookup used by the intent short-circuit and MCP substitution).
- New: `data/reference/aliases_log.jsonl` (processing artifact, not a source).
- Downstream consumers: `backend/app/services/major_lookup.py::lookup_major` (L77–94) and `src/mcp_server/futureproof_server.py::_find_major_intent` (L1471–1489). Both iterate the YAML in file order and return on first case-insensitive match against `major` or any alias.

#### Crosswalk Impact
- No new CIP ↔ SOC mappings. The spec only widens the student-typed surface that hits an existing YAML row.
- The substitution rules in `_handle_get_career_paths` (same-family gate, `_matched_cip_is_more_specific`) are unchanged — aliases only change *which* YAML row a student string lands on; the substitution eligibility of that row is identical to today.

#### Formula Verification
- N/A — no stat or boss-fight formula is touched. ERN/ROI/GRW/RES/HMN plumbing is byte-identical.

#### Findings

##### Data Quality Sound
- **Validator ruleset is largely correct** (§4 `_validate_alias`). Length 2–40, regex `^[a-zA-Z0-9 ./&'-]+$`, case-insensitive entry-local dedupe, canonical-equality rejection, collision with any other entry's `major`, and collision with any other entry's alias — all necessary checks given that the downstream matcher is first-match-wins and does no fuzzy resolution.
- **Collision scope is correct.** The validator's "all majors / all aliases in the YAML" scope matches the lookup contract: both `major_lookup.py:88` and `futureproof_server.py:1482` walk the YAML entry-by-entry with zero family or tier filtering, so a cross-family alias collision is observable to users as non-determinism. Keeping the scope global is the right call.
- **Hand-curated preservation path is correct.** §2 Decision #9 + the `_load_processed_cip4s` gate mean curated entries are skipped via the "aliases already non-empty" predicate before Gemma is ever called. Verified that §1's claim of 56 curated entries matches reality — running `uv run python` over the current YAML confirms 398 total, 56 non-empty aliases, 342 empty, 39 families.
- **Log-gate idempotence holds under `--family` and `--limit` reruns.** The log is append-only, `_load_processed_cip4s` collapses to a `set[str]`, so re-running with narrower or wider filters is safe; any previously-logged cip4 is skipped without `--force`. `--force --family 11` correctly re-processes family 11 and appends new rows; later non-force runs still see those cip4s as "processed" because set membership ignores run ordering. Ctrl-C mid-run is safe: the YAML and log advance per-entry, so a re-run picks up on the next un-logged cip4.
- **Cost estimate is defensible.** ~342 entries × (~400 input tokens + ~200 output tokens) at `google/gemma-4-26b-a4b-it` OpenRouter pricing (on the order of $0.10/$0.20 per MTok for the Gemma tier) lands near $0.03 per full pass — an order of magnitude under the $1 budget. Even at 2× for retries and prompt growth, we're comfortably under.
- **Existing intent + substitution tests are safe.** `tests/mcp/test_cip_substitution.py` uses a hand-crafted `FAKE_LOOKUP` (L29–54) and never touches the real YAML; `test_cip_substitution_integration.py::TestIUB*` exercises the `Marketing` / `Accounting` / `Finance` hand-curated entries, which this spec explicitly does not modify; `backend/tests/services/test_intent.py::TestDeterministicShortCircuit` also hits hand-curated paths only. The `TestCrossModuleConsistency` parametrized test (`backend/tests/services/test_major_lookup.py:176`) expands linearly with alias count — ~1,400 new (alias,entry) pairs on a ms-per-case harness. The authorized sampled-subset modification in §4 is an acceptable mitigation if runtime becomes an issue.

##### Data Concerns

- **COVERAGE FLOOR IS NOT ENFORCED UPSTREAM.** §4's `_MIN_SOC_COUNT = 3` comment at `scripts/alias_major_entries.py` asserts "enforced upstream by regenerator; this is documentation." That is **not true today.** `scripts/regenerate_major_to_cip_yaml.py::_fetch_crosswalk_cip4s` (L154–181) emits every cip4 whose crosswalk has at least one non-`99-9999` SOC. The `soc_n` column is SELECTed but never gated — no `HAVING` clause, no post-query filter. **Risk:** low-signal entries (obscure `03.xx`/`28.xx`/`30.xx` fragments with 1–2 SOC mappings) get aliased and become live exact-match hits for student free-text — the exact "false-positive substitution to a program with no career signal" that Decision #1 was designed to avoid. **Fix:** either (a) add `HAVING COUNT(DISTINCT soc_code) >= 3` to `_fetch_crosswalk_cip4s` in a separate commit before this spec lands, or (b) have the aliaser itself re-query the crosswalk and skip entries below the floor. (a) is cleaner — the floor belongs in the data layer, not the prompt layer.

- **"Business"-shaped collision risk on first-match-wins.** §2 Decision #6 rejects aliases that collide with another entry's `major` or another entry's alias, but does NOT reject aliases that are generic tokens whose intended referent is a DIFFERENT auto-gen entry the validator hasn't seen yet. Concrete scenario triggerable against today's YAML: `52.01 Business/Commerce, General` has `aliases: []`. `52.02 Business Administration` has aliases (`business admin`, `BBA`, `business management`, etc.) but NOT the standalone word `"business"`. Today `lookup_major("business")` returns `None` and falls through to Gemma. If the aliaser (processing in file order) proposes `"business"` for `52.01`, the validator PASSES it (no major equals `"business"`, no alias equals `"business"`). Post-commit, `lookup_major("business")` deterministically returns `52.01` (broad, low-earnings-signal Business/Commerce General) — shadowing Business Administration, International Business, Business Analytics. **Risk:** every student who types "business" is quietly routed to the weakest Business CIP in the YAML. **Fix:** add a "single-token alias that is a prefix of ≥ 2 other `major` values in the same cip_family" reject rule to the validator, and mirror it in-prompt. Alternative mitigation: hand-curate the `XX.01 "General"` entries defensively BEFORE running the aliaser so they get skipped via Decision #9.

- **Weak-punctuation aliases slip through.** `_ALIAS_RE` permits length-2 strings composed entirely of `. / & ' -` (e.g. `"&'"`, `".."`, `"-'"`). `_clean_alias` only collapses whitespace, not edge punctuation. **Risk:** low — these wouldn't match any real student input, but they waste YAML bytes, log rows, and add noise to acceptance-rate metrics. **Fix:** add `if not any(c.isalnum() for c in cleaned): return False, "no_alphanumeric"` to `_validate_alias`. One line, closes the loophole.

- **No umbrella-noun guard in-prompt beyond the Engineering example.** The prompt gets "Engineering alone is not valid" right, but nursing, education, psychology, medicine, law are family-umbrella tokens with the same risk. On the next NCES refresh, Gemma may propose `"Nurse"` or `"Education"` as an alias for one entry before seeing the one where it actually belongs — validator catches cross-entry collision only if the OTHER entry already has that alias. Ordering-dependence is latent. **Risk:** low today, medium on next crosswalk refresh. **Fix:** expand the in-prompt umbrella-noun list explicitly: "'Nursing' alone is not valid for Registered Nursing — same rule for 'Education', 'Psychology', 'Medicine', 'Law'."

- **Regenerator diff assumes argparse exists.** The §4 patch inserts `parser.add_argument("--with-aliases", ...)` into `scripts/regenerate_major_to_cip_yaml.py`, but the file has no `argparse` today — `main()` takes zero args and runs unconditionally (verified: no `argparse` import in the file). The implementation must add argparse scaffolding in the same commit. This matters for data integrity because the spec's guarantee "default behavior unchanged byte-for-byte" depends on the default-False `--with-aliases` flag genuinely being opt-in. Add a companion test to the P2 suite: "no-flag run produces byte-identical output to today's `main()`" — and bump `TestRegeneratorIntegration::test_with_aliases_flag_invokes_generator` to P1.

- **Log schema doesn't capture canonical-major shifts.** `AliasLogEntry.major` is "canonical name at processing time." If a future NCES edition renames `Registered Nursing/Registered Nurse` → `Registered Nursing`, the regenerator updates the YAML's `major` field but `aliases_log.jsonl` still carries the old major on that cip4's line. `_load_processed_cip4s` skips the cip4 (keyed on cip4 only), so the entry never gets re-aliased against the new canonical — and the old aliases may now be misaligned. **Risk:** curator must manually `--force --family NN` after every NCES refresh. **Fix:** either (a) have the aliaser re-queue any cip4 whose current `major` differs from the last-logged major, or (b) document the `--force` workflow in §4 Pipeline Integration as the required post-refresh step. (b) is acceptable; (a) is cleaner.

##### Data Integrity Blockers

None. The blocker-grade concern (coverage-floor assumption is wrong) is fixable by adding one `HAVING` clause to the regenerator in a separate PR before this spec lands. It is CHANGES REQUESTED, not REJECTED.

#### Disclaimer Check
- [x] AI-estimated values labeled — aliases are not student-visible; no disclaimer needed. The YAML is a lookup table, not a character-card field.
- [x] Confidence scores propagated — N/A; aliases are binary (present/absent), no crosswalk-tier concept applies.
- [x] Required disclaimer strings present in UI — N/A; no UI surface changes.
- [x] Missing data states handled — an entry with `aliases: []` and log `status: "all_rejected"` still resolves via exact `major` match; no $0 or blank in the user-visible path.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

### @genai-architect Review (ad-hoc)
**Status:** COMPLETE

#### Findings

**1. Prompt body — well-structured for Gemma 4, with one actionable fix**

The `_ALIAS_SYSTEM_PROMPT` body follows the correct discipline for `google/gemma-4-26b-a4b-it` (and its Ollama counterpart `gemma4:e4b`): hard rules precede the output schema, the output format is stated explicitly ("Respond in JSON only, no preamble, no markdown"), and the count bound (2–8) is stated twice — which is empirically the right doubling for Gemma 4's tendency to drift on ranges stated once. The in-prompt collision guidance ("'Engineering' alone is not a valid alias for Mechanical Engineering") is correct practice: telling Gemma the failure mode it should avoid on first pass lifts acceptance rate before the validator runs.

One actionable fix: the prompt interpolates `{major}` as a plain Python `.format()` substitution. The `_ALIAS_SYSTEM_PROMPT` string also contains literal `{{aliases}}` in the closing JSON example, which correctly escapes the curly braces for `.format()`. However, if any canonical `major` value in the YAML itself contains a curly brace (unlikely but possible for edge NCES entries), `.format(major=..., cip4=..., family=...)` will raise `KeyError`. The implementation should use `.format(major=..., ...)` but pass through `str.replace` or `Template` substitution instead, or at minimum validate that no substitution value contains `{` or `}` before calling `.format()`. The spec should make this defensive path explicit.

**2. JSON schema and parsing strategy — correct**

`{"aliases": [...]}` is the right flat shape for Gemma 4. Nested JSON (e.g. `{"entries": [{"cip4": ..., "aliases": [...]}]}`) fails at scale with this model family — the spec's §2 Decision #5 rationale is empirically sound. The parsing strategy (`re.sub` strip markdown fences + `json.loads`) is identical to the production pattern in `backend/app/services/intent.py:281–291`. The intent parser also adds a `rfind("}")` truncation guard to drop trailing prose Gemma appends after the closing brace — the alias parser should mirror this guard. Without it, Gemma occasionally emits a JSON block followed by an explanatory sentence, which causes `json.loads` to raise even though the JSON itself is valid. Recommend explicitly adding `last_brace = cleaned.rfind("}"); cleaned = cleaned[:last_brace + 1]` before `json.loads`, matching the intent precedent exactly.

**3. `max_tokens=200` — marginal headroom, needs a buffer**

8 aliases × 40 chars = 320 chars worst case. JSON overhead (`{"aliases": ["", "", ...]}`) adds ~30 chars. At ~3.5 chars/token (BPE average for short English phrases), 320 + 30 chars ≈ 100 tokens of content — but token counts on short mixed-case strings with punctuation skew higher (abbreviations like "CS", "RN", "mech eng" tokenize at ~1–2 tokens each, but full-phrase aliases like "mechanical engineering technology" tokenize at 4–5). A realistic worst case: 8 aliases averaging 20 chars each = 160 chars ≈ 55–70 tokens of content, plus JSON scaffolding ≈ 80–90 tokens total. **200 tokens is adequate for typical output** but borderline for a model that's already at the verbose end (Gemma 4 26B tends to emit slightly more tokens than spec). `gemma_client.generate_chat` already logs `finish_reason == "length"` and calls `_trim_to_last_sentence` — for JSON output that trim is destructive (it produces malformed JSON that `json.loads` rejects). Recommend raising `max_tokens` to **300** to give one standard deviation of headroom and avoid the `finish_reason=length` / `bad_json` cascade on verbose runs. This adds negligible cost (<0.5¢ per full run at OpenRouter pricing).

**4. `temperature=0.2` — correct for this task**

This is the right temperature. Alias generation is a constrained surface-form variation task, not creative writing. The intent prompt uses `temperature=0.1`; `0.2` is a reasonable step up to encourage surface variants (abbreviations, regional phrasings) while keeping the output distribution tight enough that the validator's acceptance rate stays predictable. No change needed.

**5. `generate_async` call signature — fully supports `max_tokens` and `temperature`**

Confirmed by reading `backend/app/services/gemma_client.py:295–323`. `generate_async` accepts `max_tokens: int = 500` and `temperature: float = 0.7` as keyword arguments and passes them through to the sync `generate` call, which in turn passes them to `generate_chat`. The implementation plan can wire `max_tokens=200` (or the recommended 300) and `temperature=0.2` directly as kwargs with no changes to `gemma_client`. The spec's `gemma_client.generate` call site is correct.

**6. `_GEMMA_MAX_CONCURRENCY` vs. `gemma_client`'s own semaphore — double-gating**

The spec defines `_OPENROUTER_CONCURRENCY = 4` and `_OLLAMA_CONCURRENCY = 1` as asyncio semaphores in the aliaser script. `gemma_client.generate_async` **also** acquires the module-level semaphore (`GEMMA_MAX_CONCURRENCY`, default 8) before dispatching. The aliaser calling `generate_async` with its own outer semaphore at 4 means concurrency is effectively `min(4, 8) = 4` — correct. However, if the aliaser calls the sync `generate` (via `asyncio.to_thread`) without `generate_async`, it bypasses the client semaphore and the aliaser's own semaphore is the only gate. The spec's `_request_aliases_for_entry` stub (line 372) shows `async def` + `semaphore: asyncio.Semaphore` — this should call `generate_async` (not `generate`) to respect both guards. If it calls sync `generate` inside `asyncio.to_thread`, the client semaphore is not acquired. The implementation must use `generate_async` or document explicitly why the client semaphore is intentionally bypassed.

**7. OpenRouter rate limits for `google/gemma-4-26b-a4b-it` — flagged as assumption**

OpenRouter does not publish per-model RPM/TPM limits in a machine-readable form as of April 2026. Based on observed behavior in this codebase (the existing `GEMMA_MAX_CONCURRENCY = 8` default without reported 429s on the intent path), 4 in-flight requests is almost certainly safe. However, this is an assumption. The spec should note it explicitly: "Rate limit ceiling of 4 concurrent requests is empirically safe based on prior OpenRouter usage in this project; if 429s occur during the alias run, reduce `_OPENROUTER_CONCURRENCY` to 2 and re-run." The current text says "Parallelism ceiling matches `gemma_client`'s existing semaphore posture" without noting the discrepancy (client default is 8, aliaser is 4 — conservatively correct, but the rationale is implicit).

**8. Ollama serial posture — defensible**

`_OLLAMA_CONCURRENCY = 1` (serial). 342 entries × ~2s/req = ~11 min on an M-series Mac. The spec's 30-minute wall-time constraint from §2 Constraints has comfortable headroom. Ollama's local inference is CPU/GPU-bound in a single process; parallel calls above 1 would add context-switching overhead without throughput gain on Ollama's default single-model-load architecture. Serial is the right call. No change needed.

**9. DUPLICATE discipline note placement — correct**

Lines 298–301 (the DUPLICATE banner comment above `_ALIAS_SYSTEM_PROMPT`) are in the right position: immediately before the constant they guard, mirroring the pattern at `backend/app/services/intent.py:67`. The cross-reference to `intent.py:67` is present and accurate. No change needed.

**10. `all_rejected` fallback posture — correct, no retry loop needed**

"Log and skip" is the right fallback for a pipeline-time batch script. A retry loop with a corrective prompt would create state-machine complexity for marginal gain: if the validator rejects all proposals from a well-formed response, it usually means the major title itself is too specific for aliases (e.g. `"Auctioneering"` → hard to alias without collision). A corrective prompt ("the aliases you gave were rejected for X reason, try again") would add 2× latency per failure and has a low success rate on Gemma 4 for constraint-dense tasks. The `--force --family XX` flow already gives a curator the ability to re-run with an improved prompt. The current "log + skip + continue" posture is correct.

**Summary of required changes before implementation:**

1. (Required) Raise `max_tokens` from 200 to 300 to avoid `finish_reason=length` → `bad_json` cascade on verbose runs.
2. (Required) Add the `rfind("}")` trailing-prose guard to the JSON parse step, matching `intent.py:285–291` exactly.
3. (Required) Implementation of `_request_aliases_for_entry` must call `generate_async` (not sync `generate` wrapped in `to_thread`) so both the aliaser's own semaphore and the `gemma_client` module semaphore are both honored.
4. (Advisory) Add a `.format()` injection guard or use `string.Template` for `_ALIAS_SYSTEM_PROMPT` interpolation to defend against YAML major values that contain literal `{` or `}`.
5. (Advisory) Document the OpenRouter 4-concurrency assumption in the spec and in the script's `--help`.

#### Verdict

- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

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
| pytest (backend) | | | | |
| pytest (root) | | | | |
| vitest | | | | |

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@design-builder)
**Status:** SKIPPED (backend-only spec)

### Code Review (@faang-staff-engineer)
**Status:** PENDING
#### Findings
[Filled in by reviewer — security, performance, error handling, atomic-write correctness, concurrency semaphore correctness.]
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
| Lint (ruff) | |
| Type check (mypy) | |
| Tests (pytest) | |

### Pipeline (@fp-builder)
| Check | Result |
|-------|--------|
| Lint (ruff src/ tests/ scripts/) | |
| Tests (pytest tests/) | |

### Frontend (@fp-builder)
| Check | Result |
|-------|--------|
| TypeScript | |
| Tests (vitest) | |
| Production build (Vite) | |

### First-Pass Alias Generation (@fp-builder, after tests pass)
| Check | Result |
|-------|--------|
| `uv run python scripts/alias_major_entries.py` completes without error | |
| Entries processed | |
| Aliases accepted | |
| Aliases rejected | |
| Cost ($, OpenRouter) | |
| Wall time | |
| `data/reference/aliases_log.jsonl` committed separately | |
| `data/reference/major_to_cip.yaml` diff reviewable standalone | |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|

---

## §10 Discussion

```
[2026-04-19] Initial draft.
Open questions for architecture review:
- Is the sidecar log the right shape, or should the YAML carry an
  aliases_source field? (§2 Decision #2 takes a position; happy to revisit.)
- Standalone script + regenerator flag — right seams, or too clever?
  (§2 Decision #3.)
- One-entry-per-call concurrency of 4 — appropriate for OpenRouter?
  (§2 Decision #5.)
```

---

## §11 Final Notes

**Human Review:** PENDING

[Final thoughts, lessons learned, follow-up items populated at COMPLETE.]
