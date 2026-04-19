# Proposal: Learned Alias Cache

**Date:** 2026-04-19
**Author:** Jeff Cernauske + Claude Code
**Status:** DEFERRED (post-hackathon) — see `docs/specs/feature-learned-alias-cache.md` for the parked spec and rationale
**Supersedes (if adopted):** `docs/specs/feature-gemma-alias-curation.md`

> **Deferred 2026-04-19** after product review. The cache is the right feature for real production traffic but wrong for a Gemma-sponsored Kaggle submission — "the system learns to call Gemma less" undercuts the narrative judges are looking for. Demo-level determinism is solved with a 2-line `temperature=0` + fixed seed change in the intent call. Revisit post-hackathon if Gemma call volume becomes a real constraint.


---

## The problem

Students type things like `"marketing"`, `"CS"`, `"nursing"` into the major field. We need to turn that into a CIP code. Today that happens in two steps:

1. **YAML lookup** at `data/reference/major_to_cip.yaml` — case-insensitive exact match against `major` + `aliases`. Fast, deterministic, but small: 56 hand-curated entries + 342 auto-generated entries with empty alias lists.
2. **Gemma intent resolver** at `backend/app/services/intent.py` — when the YAML misses, Gemma figures out what the student meant. Slow (500ms–2s), non-deterministic, costs tokens.

Most student input falls through to Gemma. Every fall-through is a latency hit, a token cost, and a point of non-determinism.

The shelved alias-curation spec tried to solve this by using Gemma once (at pipeline time) to *pre-populate* aliases for every auto-generated entry. That's guessing what students will type. This proposal replaces the guessing with a learning loop that observes what students actually type and accept.

## The shape

Three layers, in order of preference:

```
student input
    │
    ▼
┌─────────────────────┐
│ YAML (curated)      │ ← deterministic, hand-chosen
└─────────────────────┘
    │ miss
    ▼
┌─────────────────────┐
│ Learned cache       │ ← built from student behavior
└─────────────────────┘
    │ miss or low-confidence
    ▼
┌─────────────────────┐
│ Gemma intent        │ ← creative fallback
└─────────────────────┘
    │
    ▼
Log the resolution (input, school, cip, source, timestamp)
    │
    ▼
If student accepts, increment acceptance count
```

### The learned cache

- Physical form: `data/reference/learned_aliases.jsonl`. Append-only. Committed to git (same discipline as the sidecar log in the alias spec — it's a reproducibility artifact).
- Schema per line:
  ```
  {
    "input_text": "marketing",
    "input_normalized": "marketing",
    "resolved_cip4": "52.14",
    "source": "gemma" | "yaml" | "cache",
    "school_id": "ISU" | null,
    "accepted": true | false | null,
    "run_id": "2026-04-19T14:32:08Z",
    "session_id": "...",
    "model": "google/gemma-4-26b-a4b-it"
  }
  ```
- Read path: in-memory aggregate on startup. Group by `input_normalized`. An entry is a "cache hit" when `accepted_count >= N` AND `accepted_count / seen_count >= P`.
- Write path: every resolution appends one line. Every acceptance appends a second line (or updates in place; TBD — see open questions).

## Design decisions

### 1. What counts as "acceptance"?

Three options, ascending cost/clarity:

| Signal | How it's captured | Noise level | UX cost |
|--------|------------------|-------------|---------|
| **Implicit — proceeded past Career Pick** | Existing screen transition | Medium (curious clicks) | Zero |
| **Explicit — "Is this what you meant?" confirm** | New UI element post-resolution | Low | One tap |
| **Strong — completed boss / saved wrapped** | Existing high-value actions | Very low | Zero |

**Recommendation:** start with implicit (proceeded past Career Pick). Add strong signals as a tiebreaker (boss completion = 2 points, proceed = 1 point). Skip explicit for hackathon — the friction isn't worth the clarity.

### 2. Global or per-school?

"Marketing" means the same thing at ISU and Wharton. The per-school variation is handled by the substitution layer (which CIP gets shown at this school), not the resolution layer (what did the student mean).

**Recommendation:** global. `input_normalized → resolved_cip4` regardless of school. We still log `school_id` for forensics but don't branch on it.

### 3. Auto-promote learned entries to YAML?

Two options:

- **Auto-promote** — when cache entry crosses threshold, append to YAML `aliases` automatically. Pro: YAML grows. Con: one bad Gemma + one confused student pattern pollutes the file forever.
- **Read from cache directly** — the cache is just another lookup tier. Humans promote to YAML manually when they feel like cleaning up.

**Recommendation:** read from cache directly. Never auto-write to YAML. Manual promotion is a quarterly chore with `git diff`, not an automated risk.

### 4. Confidence threshold

A cache entry is promoted to "use this instead of Gemma" when:
- `accepted_count >= 3` AND
- `accepted_count / seen_count >= 0.6`

Numbers are picked from vibes. Tunable later. The 3-count floor protects against a single enthusiastic student training the system.

### 5. Decay / stale entries

Out of scope for now. A `"marketing"` match from 2026 is probably still good in 2028. If CIP taxonomy changes materially (NCES ships a new edition), we do a one-off cleanup pass.

## What this replaces / leaves alone

| Concern | Status |
|---------|--------|
| `docs/specs/feature-gemma-alias-curation.md` | **Supersede.** The alias spec was trying to front-load what this learns organically. |
| `backend/app/services/major_lookup.py` (YAML lookup) | **Unchanged.** New layer sits between it and Gemma. |
| `backend/app/services/intent.py` (Gemma resolver) | **Unchanged.** Still the fallback. |
| `src/mcp_server/futureproof_server.py` | **Unchanged.** The MCP server's YAML loader stays as-is. |
| Career substitution layer (CIP family fallback) | **Separate spec.** The "marketing → Business/Commerce at IU" experience problem is a different fix: Gemma augments substituted careers with ones the student probably wanted. That's the next proposal. |

## Hackathon scope (by May 18, 2026 — 29 days)

**In scope:**
- New service: `backend/app/services/learned_alias_cache.py`. Loads JSONL on startup, offers `lookup(input) -> CipMatch | None`, appends to log on every resolution.
- Wire into the resolution path: YAML → learned cache → Gemma. One call site, in the existing intent path.
- Implicit acceptance signal via Career Pick transition. One hook in the existing screen flow.
- Append-only JSONL write with atomic file ops (the architecture lesson from the alias-curation review).
- Tests: mock Gemma, verify cache population, verify threshold gating, verify graceful degradation when the JSONL is missing or malformed.
- Observability: every cache read/write logs to `logs/gemma.jsonl` equivalent or a dedicated `logs/alias_cache.jsonl`.

**Out of scope for hackathon:**
- Auto-promotion to `major_to_cip.yaml`.
- Explicit thumbs-up UI.
- Per-school specialization.
- Decay / TTL on stale entries.
- Admin UI to inspect / prune the cache.
- Exporting the cache as a Kaggle artifact (tempting but cut).

## What the Kaggle narrative becomes

Before: "We used Gemma to pre-generate aliases for a lookup table."
After: "The system learns from every student. Each resolved match feeds the next student's lookup. Gemma is the last resort, and it's needed less every day."

That's a materially better demo story. It's also honest — we can show the cache file growing during the video.

## Open questions for review

1. **Acceptance signal: implicit only, or implicit + strong?** Boss completion is ~5 minutes in; a student who abandons early but accepted the match still gave us a valid signal.
2. **JSONL append-only vs compact updates?** Append-only is simpler and robust. Compact format (one row per `input_normalized`, updated in place) is smaller but requires atomic rewrites. Proposing append-only.
3. **Should the cache carry `source` granularity finer than just "gemma"?** e.g. `"gemma-intent-v1"`, `"gemma-intent-v2"` — helps us invalidate on prompt changes.
4. **Where does the cache live in production?** Fine on disk for a single-node FastAPI. If we ever deploy multi-node, this becomes a DuckDB table in `data/futureproof.duckdb`. Worth mentioning in the spec so future-us doesn't wedge around the JSONL.
5. **Privacy:** we're logging student input strings. For the hackathon demo with no real students, fine. For real deployment, the school's data steward wants a say. Out of scope for this proposal but flag it.
6. **The career-augmentation spec** (from the prior conversation — "Gemma fills the gap when substitution lands on the wrong CIP") — that's a sibling, not a dependency. Can ship independently.

---

## Next step

Full §1–§11 spec lives at **[`docs/specs/feature-learned-alias-cache.md`](../docs/specs/feature-learned-alias-cache.md)** — ready for the standard agent pipeline (architect + data-reviewer + genai-architect before implementation). On COMPLETE, the alias-curation spec moves to `docs/specs/completed/` with a SUPERSEDED banner pointing to this work.
