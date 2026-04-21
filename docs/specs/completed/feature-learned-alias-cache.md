# Feature: Learned Alias Cache

## Claude Code Prompt

```
Read the spec at docs/specs/feature-learned-alias-cache.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review §1–§4 for: resolution-path ordering
     (YAML -> cache -> Gemma), idempotence of the append-only JSONL writer,
     crash safety, the request_id -> acceptance correlation, and the
     read/rebuild strategy on startup.
   - Invoke @fp-data-reviewer to review: threshold gating math, input
     normalization rules, cross-CIP consistency when the same input text
     has been resolved to >1 CIP over time, privacy posture on logged
     inputs.
   - Invoke @genai-architect (ad-hoc) to review: how cache hits interact
     with the Gemma intent prompt's confidence tiers, whether cached
     "medium"-confidence resolutions need to carry their alternatives,
     and whether the cache poisons the Gemma fallback path when it misses.
   - All three write findings to §5.
   - If APPROVED: proceed to step 2.
   - If CHANGES REQUESTED (Significant): STOP, alert human.
   - If REJECTED (Blocker): STOP, alert human.

2. DESIGN VISION — SKIPPED (no net-new UI surface; acceptance signal
   piggybacks on the existing /intent/confirm endpoint).

3. IMPLEMENTATION
   - Implement §4 exactly. Touch only the files listed in the File Changes
     table. Reuse existing gemma_client / major_lookup plumbing.
   - BEFORE coding: read §4 Testing Impact Analysis. Note which tests are
     Confirmed Safe — if any of those fail, STOP and escalate.
   - Log all work to §6. Run backend (ruff + mypy + pytest), pipeline
     (ruff + pytest at repo root), and frontend (tsc + vitest) to verify
     the build is green when you finish.
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts).
     After 3 failed attempts, escalate to human via §10 and set status BLOCKED.

4. TESTING
   - Invoke @test-writer to add the cases in §4 "New Tests Required". P0 first.
   - Run the full test suite. Every failure must be acknowledged in §7.
     Never silently skip.

5. DESIGN AUDIT — SKIPPED (no design tokens touched).

6. CODE REVIEW
   - Invoke @faang-staff-engineer for security/performance/error-handling
     review of the cache service, the JSONL writer, and the resolution-path
     integration. Writes verdict to §8.

7. VERIFICATION
   - Invoke @fp-builder to run ruff + mypy + pytest (root + backend) +
     TypeScript + vitest + Vite build. Logs results to §9.

8. COMPLETION
   - Update Status to COMPLETE. Tick every Success Criterion in §1.
   - Move spec to docs/specs/completed/.
   - Write report to reports/feature-learned-alias-cache-YYYY-MM-DD.md.
   - Move docs/specs/feature-gemma-alias-curation.md to
     docs/specs/completed/ with a SUPERSEDED banner at the top pointing
     to this spec.
```

---

## Status: DEFERRED (post-hackathon) — SUPERSEDED BY REINFORCEMENT LOOP DESIGN

> **Deferred 2026-04-19** after product review. The cache is the right feature for real production traffic, but it's the wrong feature for the Gemma-sponsored Kaggle submission on May 18, 2026. Building infrastructure whose explicit purpose is to reduce Gemma calls works against the submission narrative; the judges reward ambitious Gemma use, not efficient avoidance. The cache also solves problems we don't have on a controlled-demo timeline (latency is fine, determinism is solved by `temperature=0` + a fixed seed in the intent call, cost is zero on local Ollama). Revisit once the product sees real student traffic, or if a post-hackathon scale event makes Gemma call volume a real constraint.
>
> **SUPERSEDED 2026-04-19 (same session).** The core idea — "students teach the system by accepting matches" — evolved into the visible community-suggestions surface in `docs/specs/feature-set-your-course.md` §4 (Community Suggestions Surface) and the correction log schema + aggregation. Key differences: that design keeps Gemma on the hot path (additive signal, not replacement), surfaces crowd data transparently (never silent), and ships as part of the flagship rather than as optimization. **If you're reaching for a learned-cache design, read `feature-set-your-course.md` + `feature-receipts.md` first — the student-visible community suggestions already do most of what this spec proposed, without the Gemma-avoidance framing that got this version parked.**
>
> Product review reasoning captured in conversation on 2026-04-19 (`docs/convos/2026-04-19-gemma-core-pivot.md` Topic 4 + Topic 13). The YAML/cache toggle decisions (§2 Decision #12) remain useful for any future revival of this work.


## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-19 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-04-19 |
| Blocked By | — |
| Supersedes | `docs/specs/feature-gemma-alias-curation.md` (on COMPLETE) |
| Related Specs | `docs/specs/completed/bugfix-broad-cip-substitution-and-intent.md`, `docs/specs/completed/feature-gemma-tiered-matching.md`, `docs/specs/completed/spike-gemma-intent-resolution.md`, `docs/specs/concept-gemma-intent-cache.md` |
| Proposal | `reports/proposal-learned-alias-cache-2026-04-19.md` |

---

## §1 Feature Description

### Overview

Insert a learned-alias cache between the YAML short-circuit (`backend/app/services/major_lookup.py`) and the Gemma intent resolver (`backend/app/services/intent.py`). The cache is built from actual student behavior: every resolved intent is appended to a JSONL log, and when the student confirms the match by moving past the Career Pick screen, the resolution is marked accepted. Inputs that cross a simple acceptance threshold get served from the cache instead of calling Gemma. Three layers in order of preference: YAML → learned cache → Gemma.

### Problem Statement

Today the YAML has 56 hand-curated entries and 342 auto-generated entries with empty aliases. Most student-typed strings miss the YAML and fall through to Gemma (`intent._call_gemma_intent`). Every fall-through is a 500ms–2s latency hit, a token cost, and a point of non-determinism. The previous spec (`docs/specs/feature-gemma-alias-curation.md`) tried to pre-populate aliases by having Gemma *guess* what students would type — pure speculation, generating hundreds of plausible-but-wrong tokens.

Student behavior is the better signal. If 3+ students typed `"CS"` and confirmed that `26.0101 Computer Science` was what they meant, we know that mapping is right — no LLM call required. The cache captures that signal and reuses it.

Constraints that shape the design:

- The cache must be **append-only and crash-safe**. A Ctrl-C mid-write must not corrupt earlier entries.
- The cache must be **reproducible from its log**. Rebuilding in-memory state from the JSONL must be deterministic; nothing derived lives in memory that can't be regenerated from disk.
- **Acceptance ≠ resolution.** A cache entry that records "Gemma returned 52.02 for 'marketing'" is a *seen* event, not an *accepted* one. Only after the student confirms does the entry become usable for future lookups.
- The Gemma intent prompt returns **confidence tiers** (high / medium / low) and for medium/low returns **alternatives**. The cache must decide whether to replay just the primary CIP or the full alternatives envelope.
- The cache must **degrade gracefully**: a missing/corrupted JSONL file means zero cache hits, never a crash. Same discipline as `major_lookup._load()` today.
- Privacy: we log raw student input strings. Acceptable for the hackathon with no real students; flagged as a boundary for real deployment.

### Success Criteria

- [ ] Resolution path calls YAML → learned cache → Gemma, in that exact order, in `intent.resolve_intent()`.
- [ ] YAML short-circuit is toggleable via `INTENT_YAML_ENABLED` env var (default `true`). When `false`, every resolution skips the YAML and goes directly to the learned cache → Gemma fallback chain. Enables A/B testing of Gemma behavior without the YAML's curated coverage. Cache behavior is independently toggleable via `INTENT_CACHE_ENABLED` (default `true`).
- [ ] Cache hits return a response shape identical to a YAML short-circuit (`source: "cache"` instead of `"yaml"`; otherwise byte-for-byte compatible with the existing `IntentResult` contract).
- [ ] Every resolution — from any source — appends one line to `data/reference/learned_aliases.jsonl`.
- [ ] When the frontend confirms a match via `POST /intent/confirm`, an `acceptance` record is appended to the same JSONL.
- [ ] Cache promotion threshold: `accepted_count >= CACHE_MIN_ACCEPTED` (default 3) AND `accepted_count / seen_count >= CACHE_MIN_ACCEPT_RATE` (default 0.6). Both configurable via env vars.
- [ ] Input normalization matches the YAML path: `.strip().lower()` with collapsed internal whitespace (single spaces).
- [ ] If the same `input_normalized` has been accepted against >1 distinct CIP over time, the cache picks the majority-accepted CIP. Ties resolve by most-recent-acceptance.
- [ ] Graceful degradation: missing JSONL → empty cache, never an error. Malformed line → skip that line, log once, continue.
- [ ] Startup cost: loading the JSONL and building the in-memory aggregate completes in under 200ms for a file of 10k entries. Measured and asserted in tests.
- [ ] Frontend gets a `resolution_id` (UUID) in every `IntentResult`. The Career Pick commit path echoes that id to `POST /intent/confirm`, which triggers the acceptance write.
- [ ] Full test suite passes: `uv run pytest`, `cd backend && pytest`, `cd frontend && npx vitest run`. Ruff + mypy clean. TypeScript clean.
- [ ] `logs/gemma.jsonl` still captures every Gemma call (unchanged). Cache hits do NOT generate a `logs/gemma.jsonl` entry — they didn't call Gemma.
- [ ] `docs/specs/feature-gemma-alias-curation.md` moved to `docs/specs/completed/` with a SUPERSEDED banner pointing here.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | **Layer the cache BETWEEN YAML and Gemma**, not alongside either. | (a) The YAML is hand-curated truth — the cache can never override it; collisions would be a footgun. (b) Gemma is the creative fallback; the cache exists precisely to reduce Gemma calls. The order YAML → cache → Gemma reflects that hierarchy exactly. (c) Identical placement to `docs/specs/concept-gemma-intent-cache.md` discussed previously. | (a) Cache parallel to YAML, first-match-wins — rejected, YAML authority is load-bearing. (b) Cache after Gemma as post-hoc memoization — rejected, saves no Gemma calls on repeat input. |
| 2 | **Append-only JSONL on disk**, one record per line, no compaction. | (a) Append-only is crash-safe: the last partial line is dropped on parse with `try/except json.JSONDecodeError`, earlier lines are intact. (b) Every state change is auditable with `git log` and `tail`. (c) Compaction (rewriting the file to dedupe) re-introduces every crash-safety concern the alias-curation spec fought — no atomic-write ceremony required if we never rewrite. | (a) DuckDB table inside `data/futureproof.duckdb` — rejected, overkill for 10k entries and forces a schema migration. (b) SQLite — rejected, same overkill. (c) In-memory only, rebuilt by replaying `logs/gemma.jsonl` — rejected, couples the cache to Gemma logging and has no acceptance signal. |
| 3 | **Acceptance is piggy-backed on the existing `POST /intent/confirm` endpoint.** The frontend already calls it when the Career Pick screen commits. | (a) The endpoint and the UX flow already exist — see `backend/app/routers/intent.py::confirm_intent` and the Career Pick commit path touched in commit `7a22317`. (b) Zero new UI. The "student reached Career Pick and committed" signal is both implicit (no extra tap) and reliable (they saw the match and said yes). (c) The request body already carries the matched CIP and input text — we just need to stamp a `resolution_id` into the resolve response and echo it on confirm. | (a) Explicit "Is this right?" confirmation UI — rejected, adds friction for near-zero signal lift. (b) Treat ANY screen-past-Career-Pick as acceptance — rejected, too indirect; next-screen loads would have to carry provenance. (c) Treat boss-fight completion as the signal — rejected, too deep in the funnel; we'd under-count good matches from students who bailed early for unrelated reasons. |
| 4 | **`resolution_id` is a new field on `IntentResult`.** Frontend stores it, echoes it on confirm. Backend correlates confirm → resolution via this id. | (a) Correlating on `(input_text, cip4, session)` is flaky — the student can re-type and get a new resolution for the same cip. An explicit id is unambiguous. (b) UUID4 is cheap and collision-free. (c) The field is additive — existing frontend code ignoring it still works. | (a) Correlate on session id alone — rejected, one session can resolve multiple majors. (b) No correlation, just trust the confirm payload fields — rejected, confirm has no way to distinguish "the resolution we just served" from "a resolution from 20 minutes ago." |
| 5 | **Cache serves only the primary CIP, not the full Gemma alternatives envelope.** A cache hit has `confidence: "high"` and `alternatives: []` by construction. | (a) If a cached entry has crossed the acceptance threshold, the student population has effectively voted "this is the primary." Reopening alternatives would re-introduce ambiguity the cache exists to remove. (b) Replaying full alternatives forces us to cache Gemma's entire output shape, which gets stale if the prompt evolves. (c) The YAML short-circuit already behaves exactly this way (`confidence: "high"`, no alternatives). The cache inherits that contract. | (a) Cache full alternatives — rejected, stale + undermines the acceptance signal. (b) Cache alternatives but lower confidence to "medium" — rejected, sends a confused signal; if we're confident enough to skip Gemma we're confident enough to say "high". |
| 6 | **Threshold: accepted>=3 AND accepted/seen>=0.6.** Both env-configurable (`CACHE_MIN_ACCEPTED`, `CACHE_MIN_ACCEPT_RATE`). | (a) The `3` floor blocks a single enthusiastic test session from training the cache. (b) The `0.6` ratio blocks entries where students frequently *see* the match but *don't* accept (meaning Gemma resolved to the wrong CIP). (c) Env-configurable so we can tune without a redeploy. | (a) Hard-coded — rejected, no tuning knob. (b) Time-weighted decay — rejected, over-engineered for hackathon; `CIP` mappings don't rot over months. (c) Per-input Bayesian scoring — rejected, same over-engineering. |
| 7 | **On conflict (same input → multiple CIPs over time), pick majority-accepted, tiebreak by most-recent acceptance.** | (a) "CS" resolving to both `26.0101` and `11.0101` can happen if Gemma drifts. Majority vote is the cleanest rule; most-recent tiebreak follows recent prompt improvements. (b) Deterministic under replay — rebuilding the in-memory aggregate from the JSONL yields the same decision. | (a) Always latest — rejected, a single weird recent match beats 10 old correct ones. (b) Never serve when conflicts exist — rejected, kills the cache for exactly the inputs that benefit most. |
| 8 | **No frontend UI change beyond storing/echoing `resolution_id`.** No admin panel. No "learned from N students" UI. | (a) The cache is observability-inside; the student experience is "Gemma got faster." Showing cache provenance in the UI invites questions ("why is this learned?") we don't have answers for. (b) Hackathon scope — the demo story is in the data file, not the UI. | (a) Badge on the resolution ("learned from 12 students") — rejected, UX clutter, confusing for first-time users where the count is 0. (b) Admin inspection UI — rejected, use `git log` and `jq`. |
| 9 | **No auto-promotion to `major_to_cip.yaml`.** The YAML stays hand-curated. | (a) Auto-writing to YAML re-introduces the exact risk the alias-curation spec failed on: a confused Gemma + confused student pair can promote garbage into a file that's in the app's hot path. (b) Manual promotion is a cheap quarterly chore: `jq` the JSONL, inspect top hits, paste into YAML by hand. (c) The cache already serves hits — promotion is pure consolidation, not a correctness need. | (a) Auto-promote on `accepted>=10` — rejected, concentrates the risk without a human gate. (b) Auto-generate a PR with proposed additions — rejected, out of scope; if we build it later, the JSONL is the source of truth. |
| 10 | **JSONL file committed to git**, same discipline as the (abandoned) alias-curation sidecar. | (a) Reproducibility artifact: "why did the cache serve X?" answered by one `git log`. (b) Shared across environments — the file seeded by hackathon demo traffic is what ships. (c) File grows slowly enough (one line per resolution, one per acceptance) that git LFS is unnecessary for a year+. | Gitignore — rejected, loses the reproducibility trail. |
| 11 | **No per-school specialization.** The cache keys on `input_normalized` alone; `school_id` is logged for forensics but never branches the lookup. | (a) "Marketing" means the same thing at every school — the per-school variation is the substitution layer's job (which CIP the school offers). (b) Per-school fragmentation would need 20× more traffic to reach thresholds. (c) If we ever do need per-school, it's a second cache in front of this one, not a structural change here. | Per-school primary key — rejected, fragments learning. |
| 12 | **Every resolution layer is independently toggleable via env var.** `INTENT_YAML_ENABLED` (default `true`), `INTENT_CACHE_ENABLED` (default `true`). Gemma is always on — it's the final fallback and can't be disabled. | (a) Enables A/B testing: "how does Gemma perform without the YAML crutch?" is a real question that informs whether the YAML is load-bearing or just latency optimization. (b) Testing the cache's learning curve in isolation requires being able to disable the YAML so Gemma traffic is maximized, the cache fills faster, and we can watch the hit-rate climb. (c) Debugging: when a student gets a weird resolution, flipping one layer off is a one-line diagnostic. (d) Demo flexibility: we may want to show "Gemma alone" in the Kaggle video to emphasize the model's capability, not the shortcuts around it. | (a) No toggle — rejected, hurts testability and demo narrative control. (b) Single `INTENT_LAYERS=yaml,cache,gemma` env var — rejected, harder to script/reason about in tests than boolean flags. (c) Runtime API to flip layers — rejected, over-engineered for hackathon; env vars are fine. |

### Constraints

- `data/reference/major_to_cip.yaml` and `backend/app/services/major_lookup.py` — UNCHANGED.
- `src/mcp_server/futureproof_server.py::_load_major_to_cip_lookup` — UNCHANGED. The MCP server's YAML loader stays as-is; the cache is backend-only, not a pipeline artifact.
- `backend/app/services/gemma_client.py` — UNCHANGED. The cache intercepts before Gemma is called; no changes to the transport.
- `backend/app/services/intent.py::_INTENT_SYSTEM_PROMPT` — UNCHANGED. Cached results don't re-run the prompt.
- `logs/gemma.jsonl` — unchanged format; cache hits do NOT generate an entry there (nothing was sent to Gemma).
- Cache file grows at roughly `2 * (daily resolutions)` lines/day (one `seen`, one `acceptance`). At 10k student sessions this is 20k lines — trivial.
- In-memory aggregate size: O(distinct input strings). Bounded by real-world student vocabulary; projected under 5k distinct entries for years.

### Out of Scope

- **Replacing the YAML.** The YAML is faster than the cache (no file I/O on startup, precompiled) and serves the hand-curated hot path.
- **Replacing Gemma.** The cache is a memoization layer; Gemma is still the fallback for every cache miss. Improving Gemma's prompt is a different spec.
- **Career augmentation on substitution.** The "marketing at IU → Business/Commerce" experience problem is a separate proposal. That's about what we *show* after resolution, not how we resolve.
- **Admin UI.** Inspect the JSONL with `jq`.
- **Auto-promotion to YAML.** §2 Decision #9.
- **Per-school specialization.** §2 Decision #11.
- **Decay / TTL.** §2 Decision #6 alternative (c).
- **Multi-node consistency.** Single FastAPI process today. If we ever deploy multi-node, move the cache to `data/futureproof.duckdb`.
- **Privacy controls on student input strings.** Flagged for real deployment; out of scope for hackathon demo.
- **Exporting the cache as a Kaggle artifact.** Tempting but cut.
- **Changes to the Gemma intent prompt.** Lives in `backend/app/services/intent.py::_INTENT_SYSTEM_PROMPT`; cache doesn't know or care what the prompt says.

---

## §3 UI/UX Design

**SKIPPED (no net-new UI).** The only frontend change is additive: the Career Pick commit payload echoes a `resolution_id` the backend already supplied in the intent response. No visible change for the student. The visible improvement is "Gemma got faster for the inputs other students have already confirmed."

---

## §4 Technical Specification

### Architecture Overview

One new backend service (`learned_alias_cache`), one new data file (`data/reference/learned_aliases.jsonl`), two touch-points in existing code (`intent.resolve_intent` and `intent.confirm_intent`), one additive field in the `IntentResult` Pydantic model, one additive field the frontend echoes to `POST /intent/confirm`.

**Resolution path (new):**

```
resolve_intent(major_text, unitid, programs)
    │
    ▼
1. YAML short-circuit (major_lookup.lookup_major) -------------- hit? return, source="yaml"
    │ miss OR INTENT_YAML_ENABLED=false (skipped entirely)
    ▼
2. learned_alias_cache.lookup(input_normalized) --------------- hit? return, source="cache"
    │ miss OR INTENT_CACHE_ENABLED=false (skipped entirely)
    ▼
3. Gemma intent call ---------------------------------------- return, source="gemma"
    │
    ▼
4. learned_alias_cache.record_resolution(input, cip, source, resolution_id)
       (always runs — we record resolutions even when the cache lookup is
        disabled, so turning the cache back on doesn't start from zero)
    │
    ▼
Response to frontend includes resolution_id
```

**Layer toggles:** Two env vars control which resolution layers are consulted. Defaults keep today's + new behavior.

| Env var | Default | Effect when `false` |
|---------|---------|--------------------|
| `INTENT_YAML_ENABLED` | `true` | YAML lookup is skipped — every input goes straight to cache → Gemma. Useful for A/B testing Gemma's standalone performance and for stress-testing the cache. |
| `INTENT_CACHE_ENABLED` | `true` | Cache lookup is skipped; resolutions are still *recorded* so the cache keeps learning. Re-enabling serves everything learned during the off period. |

Gemma is always the final fallback and has no toggle — it's the only layer that can resolve novel input.

**Acceptance path (new):**

```
POST /intent/confirm { resolution_id, matched_cip, ... }
    │
    ▼
intent.confirm_intent(...)
    │
    ▼
learned_alias_cache.record_acceptance(resolution_id)
    │
    ▼
{"cached": true}
```

**Cache internals:**

```
learned_alias_cache singleton
├─ _path: Path to learned_aliases.jsonl
├─ _aggregate: dict[input_normalized, AggregateEntry]
│      AggregateEntry {
│        seen_total: int
│        by_cip: dict[cip4, CipTally]
│                  CipTally {
│                    seen: int
│                    accepted: int
│                    last_accepted_at: str | None
│                  }
│      }
├─ _pending: dict[resolution_id, PendingResolution]
│      (in-memory only; resolution_id -> (input_normalized, cip4))
└─ methods: lookup, record_resolution, record_acceptance, _rebuild
```

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `/Users/jcernauske/code/bright/futureproof-data/backend/app/services/learned_alias_cache.py` | Create | Cache service. Loads JSONL on first access, rebuilds in-memory aggregate, exposes `lookup`, `record_resolution`, `record_acceptance`. Append-only writer with `try/except json.JSONDecodeError` on read. Thread-safe via a simple `threading.Lock` around the writer (FastAPI is single-process; the lock defends against concurrent requests in the same process, which DO happen with async). |
| `/Users/jcernauske/code/bright/futureproof-data/backend/app/services/intent.py` | Modify | Insert cache check between YAML lookup and Gemma call in `resolve_intent`. Generate `resolution_id` (UUID4) for every resolution regardless of source. Call `record_resolution` at the end of every path. |
| `/Users/jcernauske/code/bright/futureproof-data/backend/app/services/intent.py::confirm_intent` | Modify | After the existing cache write, call `learned_alias_cache.record_acceptance(resolution_id)`. |
| `/Users/jcernauske/code/bright/futureproof-data/backend/app/models/career.py` | Modify | Add `resolution_id: str` to `IntentResult` Pydantic model. Required field, populated by the service layer. |
| `/Users/jcernauske/code/bright/futureproof-data/backend/app/models/api.py` | Modify | Add `resolution_id: str \| None` to `IntentConfirmRequest`. Optional (null means "frontend didn't echo it back, skip the acceptance write"). |
| `/Users/jcernauske/code/bright/futureproof-data/data/reference/learned_aliases.jsonl` | Create | Empty file. Committed to git so the path exists on fresh checkout. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/types/build.ts` OR similar intent type module | Modify | Add `resolution_id: string` to the frontend `IntentResult` type. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/screens/CareerPickScreen.tsx` | Modify | Thread `resolution_id` from the intent response into the commit call payload. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/lib/api.ts` OR wherever `POST /intent/confirm` is called | Modify | Add `resolution_id` to the confirm request body. |
| `/Users/jcernauske/code/bright/futureproof-data/backend/tests/services/test_learned_alias_cache.py` | Create | Unit tests for the cache service. Mocks file I/O via `tmp_path`. |
| `/Users/jcernauske/code/bright/futureproof-data/backend/tests/services/test_intent_cache_integration.py` | Create | Integration tests for `resolve_intent` + `confirm_intent` with the cache wired in. Mocks Gemma; uses real cache service against `tmp_path` JSONL. |

### Data Model Changes

**Pydantic — `backend/app/models/career.py`:**

```python
class IntentResult(BaseModel):
    # ...existing fields unchanged...
    resolution_id: str  # NEW — UUID4, generated in resolve_intent
```

**Pydantic — `backend/app/models/api.py`:**

```python
class IntentConfirmRequest(BaseModel):
    # ...existing fields unchanged...
    resolution_id: str | None = None  # NEW — echoed by frontend
```

**JSONL record schemas** (two record types, distinguished by `kind`):

```python
# Resolution record — written by resolve_intent
class ResolutionLogRecord(TypedDict):
    kind: Literal["resolution"]
    resolution_id: str                 # UUID4
    timestamp: str                     # ISO8601 UTC
    input_text: str                    # raw student input
    input_normalized: str              # .strip().lower() with whitespace collapse
    cip4: str                          # resolved CIP
    source: Literal["yaml", "cache", "gemma"]
    unitid: int | None                 # school id for forensics
    school_id: str | None              # ISU, IU, etc., if known
    session_id: str | None             # if available from request context

# Acceptance record — written by confirm_intent
class AcceptanceLogRecord(TypedDict):
    kind: Literal["acceptance"]
    resolution_id: str                 # must match a prior resolution record
    timestamp: str                     # ISO8601 UTC
```

**In-memory aggregate** (rebuilt from JSONL on first lookup):

```python
class CipTally(TypedDict):
    seen: int
    accepted: int
    last_accepted_at: str | None

class AggregateEntry(TypedDict):
    seen_total: int
    by_cip: dict[str, CipTally]  # cip4 -> tally
```

### Service Changes

**New module — `backend/app/services/learned_alias_cache.py`:**

```python
"""Learned alias cache — student-behavior-driven intent resolution.

Sits between major_lookup (YAML) and intent._call_gemma_intent. On every
resolution we append a 'resolution' record to the JSONL. On every
confirm from the Career Pick screen we append an 'acceptance' record.
Lookups serve cached matches only when the (accepted, seen) tallies
cross a configured threshold.

Append-only JSONL is the source of truth. In-memory aggregate is a
rebuildable derivative.

See docs/specs/feature-learned-alias-cache.md.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Literal, TypedDict

logger = logging.getLogger(__name__)

_REL_JSONL_PATH = Path("data/reference/learned_aliases.jsonl")

# Tuned per §2 Decision #6. Env-configurable so ops can tune without
# a redeploy. Read once at module load; tests patch via monkeypatch.
_MIN_ACCEPTED = int(os.environ.get("CACHE_MIN_ACCEPTED", "3"))
_MIN_ACCEPT_RATE = float(os.environ.get("CACHE_MIN_ACCEPT_RATE", "0.6"))

_write_lock = threading.Lock()


class CipTally(TypedDict):
    seen: int
    accepted: int
    last_accepted_at: str | None


class AggregateEntry(TypedDict):
    seen_total: int
    by_cip: dict[str, CipTally]


class CacheMatch(TypedDict):
    cip4: str
    accepted_count: int
    seen_count: int


@lru_cache(maxsize=1)
def _jsonl_path() -> Path | None:
    """Walk upward from this module to find the JSONL. Identical discipline
    to major_lookup._yaml_path (see that module's docstring for why)."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / _REL_JSONL_PATH
        if candidate.is_file():
            return candidate
    return None


@lru_cache(maxsize=1)
def _aggregate() -> dict[str, AggregateEntry]:
    """Rebuild the aggregate from JSONL. Cached for the process lifetime;
    cache_clear() in tests after monkeypatching the path."""
    path = _jsonl_path()
    if path is None:
        return {}
    return _build_aggregate(path)


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _build_aggregate(path: Path) -> dict[str, AggregateEntry]:
    agg: dict[str, AggregateEntry] = {}
    # First pass: resolutions.
    resolutions: dict[str, tuple[str, str]] = {}  # resolution_id -> (input_norm, cip4)
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("skipping malformed JSONL line")
                continue
            kind = record.get("kind")
            if kind == "resolution":
                input_norm = record["input_normalized"]
                cip4 = record["cip4"]
                rid = record["resolution_id"]
                resolutions[rid] = (input_norm, cip4)
                entry = agg.setdefault(input_norm, {"seen_total": 0, "by_cip": {}})
                entry["seen_total"] += 1
                tally = entry["by_cip"].setdefault(
                    cip4, {"seen": 0, "accepted": 0, "last_accepted_at": None}
                )
                tally["seen"] += 1
            elif kind == "acceptance":
                rid = record["resolution_id"]
                pair = resolutions.get(rid)
                if pair is None:
                    continue
                input_norm, cip4 = pair
                entry = agg.get(input_norm)
                if entry is None:
                    continue
                tally = entry["by_cip"].get(cip4)
                if tally is None:
                    continue
                tally["accepted"] += 1
                tally["last_accepted_at"] = record["timestamp"]
    return agg


def lookup(input_text: str) -> CacheMatch | None:
    """Return a cache hit for the normalized input, or None."""
    normalized = _normalize(input_text)
    if not normalized:
        return None
    entry = _aggregate().get(normalized)
    if entry is None:
        return None
    # Pick the best CIP per §2 Decision #7 (majority-accepted, tiebreak
    # most-recent-acceptance). Entries below threshold are filtered first.
    eligible = [
        (cip4, tally)
        for cip4, tally in entry["by_cip"].items()
        if tally["accepted"] >= _MIN_ACCEPTED
        and tally["accepted"] / tally["seen"] >= _MIN_ACCEPT_RATE
    ]
    if not eligible:
        return None
    eligible.sort(
        key=lambda pair: (
            -pair[1]["accepted"],
            -(pair[1]["last_accepted_at"] or ""),
        )
    )
    # Note: lexicographic sort on ISO timestamps is correct-ordering.
    cip4, tally = eligible[0]
    return {
        "cip4": cip4,
        "accepted_count": tally["accepted"],
        "seen_count": tally["seen"],
    }


def new_resolution_id() -> str:
    return str(uuid.uuid4())


def record_resolution(
    *,
    resolution_id: str,
    input_text: str,
    cip4: str,
    source: Literal["yaml", "cache", "gemma"],
    unitid: int | None = None,
    school_id: str | None = None,
    session_id: str | None = None,
) -> None:
    """Append one 'resolution' record. Crash-safe: single write() call."""
    record = {
        "kind": "resolution",
        "resolution_id": resolution_id,
        "timestamp": _now_iso(),
        "input_text": input_text,
        "input_normalized": _normalize(input_text),
        "cip4": cip4,
        "source": source,
        "unitid": unitid,
        "school_id": school_id,
        "session_id": session_id,
    }
    _append(record)
    # Update in-memory aggregate to reflect the write.
    _apply_resolution_to_aggregate(record)


def record_acceptance(*, resolution_id: str) -> None:
    """Append one 'acceptance' record. No-op if resolution_id is unknown
    (which only happens if the JSONL was truncated — we log once)."""
    record = {
        "kind": "acceptance",
        "resolution_id": resolution_id,
        "timestamp": _now_iso(),
    }
    _append(record)
    _apply_acceptance_to_aggregate(resolution_id, record["timestamp"])


def _append(record: dict) -> None:
    path = _jsonl_path()
    if path is None:
        logger.warning(
            "learned_alias_cache JSONL not found; skipping write "
            "(this should only happen in a broken deployment)"
        )
        return
    line = json.dumps(record, separators=(",", ":")) + "\n"
    with _write_lock:
        with path.open("a") as f:
            f.write(line)


def _apply_resolution_to_aggregate(record: dict) -> None:
    # Mutate _aggregate's cached value in place; the lru_cache decorator
    # returns the same dict instance across calls.
    agg = _aggregate()
    input_norm = record["input_normalized"]
    cip4 = record["cip4"]
    entry = agg.setdefault(input_norm, {"seen_total": 0, "by_cip": {}})
    entry["seen_total"] += 1
    tally = entry["by_cip"].setdefault(
        cip4, {"seen": 0, "accepted": 0, "last_accepted_at": None}
    )
    tally["seen"] += 1
    # Track the pending resolution so we can apply a future acceptance.
    _pending_resolutions()[record["resolution_id"]] = (input_norm, cip4)


def _apply_acceptance_to_aggregate(resolution_id: str, timestamp: str) -> None:
    pair = _pending_resolutions().get(resolution_id)
    if pair is None:
        return
    input_norm, cip4 = pair
    agg = _aggregate()
    entry = agg.get(input_norm)
    if entry is None:
        return
    tally = entry["by_cip"].get(cip4)
    if tally is None:
        return
    tally["accepted"] += 1
    tally["last_accepted_at"] = timestamp


@lru_cache(maxsize=1)
def _pending_resolutions() -> dict[str, tuple[str, str]]:
    """resolution_id -> (input_normalized, cip4). Rebuilt on first call
    by replaying the JSONL — same data the aggregate builder uses."""
    path = _jsonl_path()
    if path is None:
        return {}
    pending: dict[str, tuple[str, str]] = {}
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("kind") == "resolution":
                pending[record["resolution_id"]] = (
                    record["input_normalized"],
                    record["cip4"],
                )
    return pending


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
```

**Modified — `backend/app/services/intent.py`:**

```python
# At top with other imports:
from app.services import gemma_client, major_lookup, mcp_client, learned_alias_cache

# Inside resolve_intent (pseudo-diff; exact lines determined at implementation):
def resolve_intent(*, major_text, school_name, unitid, programs):
    resolution_id = learned_alias_cache.new_resolution_id()
    # 1. YAML short-circuit (existing code, unchanged).
    yaml_hit = major_lookup.lookup_major(major_text)
    if yaml_hit is not None:
        result = _build_yaml_result(yaml_hit, major_text, programs, unitid)
        result.resolution_id = resolution_id
        learned_alias_cache.record_resolution(
            resolution_id=resolution_id,
            input_text=major_text,
            cip4=result.matched_cip,
            source="yaml",
            unitid=unitid,
        )
        return result

    # 2. Learned cache (NEW).
    cache_hit = learned_alias_cache.lookup(major_text)
    if cache_hit is not None:
        result = _build_cache_result(cache_hit, major_text, programs, unitid)
        result.resolution_id = resolution_id
        learned_alias_cache.record_resolution(
            resolution_id=resolution_id,
            input_text=major_text,
            cip4=cache_hit["cip4"],
            source="cache",
            unitid=unitid,
        )
        return result

    # 3. Gemma fallback (existing code, unchanged).
    gemma_result = _call_gemma_intent(...)
    gemma_result.resolution_id = resolution_id
    learned_alias_cache.record_resolution(
        resolution_id=resolution_id,
        input_text=major_text,
        cip4=gemma_result.matched_cip,
        source="gemma",
        unitid=unitid,
    )
    return gemma_result


# Inside confirm_intent (pseudo-diff):
def confirm_intent(*, matched_cip, matched_title, major_text, unitid, parent_cip, resolution_id=None):
    # ...existing cache write unchanged...
    if resolution_id:
        learned_alias_cache.record_acceptance(resolution_id=resolution_id)
```

**New helper `_build_cache_result`** constructs an `IntentResult` from a cache hit. Its shape mirrors `_build_yaml_result` (which the spec implementor will factor out if it isn't already), with `source="cache"` and `confidence="high"` and `alternatives=[]` per §2 Decision #5.

### Gemma Prompt Design

No prompt changes. `_INTENT_SYSTEM_PROMPT` stays exactly as it is today.

### Frontend Changes

Minimal — two touch-points:

1. **Type definition**: `frontend/src/types/build.ts` or wherever `IntentResult` is typed. Add `resolution_id: string`.
2. **Commit payload**: the Career Pick screen's commit handler pulls `resolution_id` off the resolve response and includes it in the `POST /intent/confirm` body.

No UI changes. No new tests in vitest — the type addition is exercised by existing tests via the build flow; the commit payload is exercised by the existing commit test (`frontend/src/screens/CareerPickScreen.test.tsx`).

### Pipeline Integration

None. The cache is backend runtime state, not a pipeline artifact. No Brightsmith zone changes. No DuckDB table. No crosswalk changes.

### Testing Impact Analysis

> **IMPORTANT:** Before finalizing this section, search the test directories for tests related to files being modified.

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `backend/tests/services/test_intent.py` | `TestDeterministicShortCircuit::*` | Low | YAML path unchanged. Cache sits *after* YAML — YAML hits still return before the cache is consulted. Tests must still pass byte-for-byte. |
| `backend/tests/services/test_intent.py` | `TestGemmaIntent::*` | Med | Gemma path unchanged in logic, but now wrapped by a cache read. Tests that patch `_call_gemma_intent` still work; tests that assert on the full `IntentResult` shape must be updated for the new `resolution_id` field. Mitigation: assert with `model_dump(exclude={"resolution_id"})` or update fixtures. |
| `backend/tests/services/test_intent.py` | Tests asserting `IntentResult` shape | Med | Same reason — new required field. |
| `frontend/src/screens/CareerPickScreen.test.tsx` | Commit-flow tests | Low | Existing tests commit with a mock intent response; adding `resolution_id` to the mock is a one-line fixture update. |
| `tests/mcp/test_cip_substitution.py::*` | All tests | Low | MCP server YAML loader untouched. |
| `tests/mcp/test_cip_substitution_integration.py::*` | All tests | Low | Same — MCP server path is not changed. |
| `backend/tests/services/test_builds.py::*` | Build flow tests | Low | Build flow consumes `matched_cip` from intent resolution; `resolution_id` is additive and ignored by the build path. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `backend/tests/services/test_intent.py` fixtures | Add `resolution_id: <uuid>` to every `IntentResult` fixture constructor. | New required field on the Pydantic model — constructors that omit it would raise ValidationError. |
| `frontend/src/screens/CareerPickScreen.test.tsx` | Add `resolution_id: "fixture-uuid"` to mocked intent responses. | Same — shape change. |

#### Confirmed Safe

Tests that must NOT break. If any fail, STOP and escalate:

- `backend/tests/services/test_intent.py::TestDeterministicShortCircuit::test_short_circuit_resolves_via_yaml` — core YAML path.
- `tests/mcp/test_cip_substitution_integration.py::TestIUBMarketing` — end-to-end substitution flow.
- `tests/mcp/test_cip_substitution_integration.py::TestIUBAccounting` / `TestIUBFinance`.
- `backend/tests/services/test_gemma_voice_contract.py` — Gemma voice contract tests (new-ish, must not regress).
- All frontend vitest cases for build flow (`BuildScreen`, `RevealScreen`, etc.) — they consume intent results but don't branch on `resolution_id`.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/services/test_learned_alias_cache.py` | `TestLookup::test_miss_when_no_jsonl` | Missing JSONL file → `lookup()` returns None, no error. |
| P0 | `backend/tests/services/test_learned_alias_cache.py` | `TestLookup::test_miss_when_below_threshold` | Input with `accepted=2` (below default 3) returns None. |
| P0 | `backend/tests/services/test_learned_alias_cache.py` | `TestLookup::test_hit_when_above_threshold` | Input with `accepted=3`, `seen=4` returns the cip. |
| P0 | `backend/tests/services/test_learned_alias_cache.py` | `TestLookup::test_miss_when_accept_rate_too_low` | Input with `accepted=3`, `seen=10` (ratio 0.3) returns None. |
| P0 | `backend/tests/services/test_learned_alias_cache.py` | `TestLookup::test_normalization_case_insensitive` | "CS" and "cs" map to the same aggregate bucket. |
| P0 | `backend/tests/services/test_learned_alias_cache.py` | `TestLookup::test_normalization_whitespace_collapse` | "  computer   science " maps to "computer science". |
| P0 | `backend/tests/services/test_learned_alias_cache.py` | `TestLookup::test_conflict_picks_majority_accepted` | Same input has `cip4=A` (accepted=5) and `cip4=B` (accepted=3) → returns A. |
| P0 | `backend/tests/services/test_learned_alias_cache.py` | `TestLookup::test_conflict_tiebreak_most_recent` | Both cips have equal accepted counts → returns the one with the later `last_accepted_at`. |
| P0 | `backend/tests/services/test_learned_alias_cache.py` | `TestRecord::test_resolution_appends_one_line` | `record_resolution` writes exactly one line with expected shape. |
| P0 | `backend/tests/services/test_learned_alias_cache.py` | `TestRecord::test_acceptance_appends_one_line` | `record_acceptance` writes exactly one line with expected shape. |
| P0 | `backend/tests/services/test_learned_alias_cache.py` | `TestRecord::test_acceptance_increments_aggregate` | After `record_resolution` then `record_acceptance`, the aggregate reflects the increment. |
| P0 | `backend/tests/services/test_learned_alias_cache.py` | `TestCrashSafety::test_malformed_line_is_skipped` | A truncated/partial line in the JSONL is skipped without raising. |
| P0 | `backend/tests/services/test_learned_alias_cache.py` | `TestCrashSafety::test_unknown_acceptance_resolution_id_is_noop` | Acceptance referencing a resolution_id that doesn't exist is silently dropped. |
| P0 | `backend/tests/services/test_learned_alias_cache.py` | `TestIntegrityRebuild::test_rebuild_from_jsonl_is_deterministic` | Building the aggregate twice from the same JSONL produces identical dicts. |
| P0 | `backend/tests/services/test_intent_cache_integration.py` | `TestResolveIntent::test_yaml_hit_skips_cache_and_gemma` | YAML hit → no cache or Gemma interaction. Verified via mock. |
| P0 | `backend/tests/services/test_intent_cache_integration.py` | `TestResolveIntent::test_cache_hit_skips_gemma` | Cache hit above threshold → no Gemma call. Verified via mock. |
| P0 | `backend/tests/services/test_intent_cache_integration.py` | `TestResolveIntent::test_cache_miss_falls_through_to_gemma` | Cache miss → Gemma called. |
| P0 | `backend/tests/services/test_intent_cache_integration.py` | `TestResolveIntent::test_every_path_appends_resolution_record` | YAML, cache, and Gemma paths all append exactly one resolution record. |
| P0 | `backend/tests/services/test_intent_cache_integration.py` | `TestResolveIntent::test_resolution_id_is_uuid4` | Response carries a UUID4 `resolution_id`. |
| P0 | `backend/tests/services/test_intent_cache_integration.py` | `TestConfirmIntent::test_appends_acceptance_record` | Confirm with `resolution_id` appends acceptance line. |
| P0 | `backend/tests/services/test_intent_cache_integration.py` | `TestConfirmIntent::test_missing_resolution_id_is_silent_noop` | Confirm without `resolution_id` (old client) does not raise. |
| P0 | `backend/tests/services/test_intent_cache_integration.py` | `TestCacheHitShape::test_cache_hit_has_high_confidence_no_alternatives` | Cache hits match YAML shape per §2 Decision #5. |
| P1 | `backend/tests/services/test_learned_alias_cache.py` | `TestEnvConfig::test_threshold_env_vars_override_defaults` | `CACHE_MIN_ACCEPTED=5` + `CACHE_MIN_ACCEPT_RATE=0.8` raise the bar. |
| P1 | `backend/tests/services/test_learned_alias_cache.py` | `TestStartupCost::test_10k_line_jsonl_loads_under_200ms` | Bulk-generated fixture validates the perf claim. |
| P1 | `backend/tests/services/test_learned_alias_cache.py` | `TestConcurrency::test_parallel_writes_do_not_corrupt_file` | Two threads calling `record_resolution` concurrently produce two complete lines with no interleaving. |
| P2 | `backend/tests/services/test_intent_cache_integration.py` | `TestObservability::test_cache_hit_does_not_log_to_gemma_jsonl` | Cache hits skip `logs/gemma.jsonl` per §1 success criteria. |

#### Test Data Requirements

- **Fixture JSONL** at `backend/tests/services/fixtures/mini_learned_aliases.jsonl` — ~20 entries covering: threshold hit, below-threshold, majority conflict, tiebreak conflict, malformed line.
- **Large fixture** for perf test — 10k lines generated in-test via a helper, not committed.
- **Mocked Gemma** — `unittest.mock.patch("app.services.intent._call_gemma_intent")`. No live Gemma in CI.
- **Environment** — tests patch the JSONL path via `monkeypatch` on `_jsonl_path` and clear `_aggregate` / `_pending_resolutions` LRU caches.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** PENDING
#### Findings
[Filled in by @fp-architect — resolution-path ordering, JSONL writer idempotence, crash safety, resolution_id correlation, startup rebuild strategy.]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

### @fp-data-reviewer Review
**Status:** PENDING
#### Findings
[Filled in by @fp-data-reviewer — threshold math, normalization rules, cross-CIP conflict resolution, privacy posture on logged inputs.]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

### @genai-architect Review (ad-hoc)
**Status:** PENDING
#### Findings
[Filled in by @genai-architect — cache/confidence-tier interaction, whether medium-confidence alternatives must be cached, poisoning risk on Gemma fallback.]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
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

### Design Audit (@fp-design-auditor)
**Status:** SKIPPED (no design tokens touched)

### Code Review (@faang-staff-engineer)
**Status:** PENDING
#### Findings
[Filled in by reviewer — cache service correctness, writer atomicity, resolve/confirm integration, concurrency.]
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

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|

---

## §10 Discussion

```
[2026-04-19] Initial draft, derived from reports/proposal-learned-alias-cache-2026-04-19.md.
Key open questions for architecture review:
- Is the resolution_id round-trip (backend -> frontend -> backend on confirm)
  the right correlation mechanism, or should the backend stash it in a
  short-lived server-side map keyed by session? (§2 Decision #4.)
- Is append-only with in-memory replay the right tradeoff vs a compacted
  store? (§2 Decision #2.)
- Cache serves primary-only, no alternatives — is that too reductive
  for medium-confidence inputs? (§2 Decision #5.)
- Threshold defaults 3/0.6 are vibes — do data-reviewers want different
  numbers based on expected demo traffic volume? (§2 Decision #6.)
```

---

## §11 Final Notes

**Human Review:** PENDING

[Final thoughts, lessons learned, follow-up items populated at COMPLETE.]
