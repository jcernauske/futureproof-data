# Feature: Resolution Cache (Gemma Response Caching)

## Claude Code Prompt

```
[TO BE WRITTEN — this spec is DEFERRED until post-hackathon]
```

---

## Status: DEPRECATED 2026-05-03

> **Deprecated.** Was already DEFERRED post-hackathon. Caching Gemma responses is a production-stage optimization, not a hackathon concern. If response latency becomes a real problem in deployment, write fresh against measured bottlenecks.

> **Deferred rationale:** Caching Gemma responses bypasses Gemma for cache-hit students, which undermines the Gemma 4 Good hackathon demo. Every student should experience Gemma resolving their major in real time. This spec will be detailed and executed post-hackathon when scale matters more than demo impact.

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-23 |
| Author | Jeff + Claude Code |
| Spec Version | 0.1 (skeleton) |
| Last Updated | 2026-05-03 (DEPRECATED — production-stage optimization, not a hackathon concern) |
| Blocked By | Hackathon deadline (2026-05-18) — execute after |
| Related Specs | `feature-save-build.md` |

---

## §1 Feature Description

### Overview

Add a persistent DuckDB cache layer keyed by school + major text that stores Gemma's intent resolution, career outcomes from MCP, and Gemma's career tiering. When a second student enters the same school and field of study, they get cached results immediately — skipping Gemma inference and MCP scans.

### Problem Statement

Every student who enters the same school + major combination triggers:
1. A Gemma intent resolution call (~2-5s)
2. An MCP scan of Iceberg tables (~1-3s)
3. A Gemma tiering call (~2-5s)

For popular school+major combos (e.g., "IU" + "business"), these identical calls waste inference budget and add latency. A cache keyed by `(unitid, normalized_major_text)` would serve repeat combos instantly.

### Success Criteria

- [ ] New `resolution_cache` DuckDB table with TTL-based expiry
- [ ] Cache key: `{unitid}:{normalized_major_text}`
- [ ] Cached artifacts: IntentResult, career outcomes, tiered careers
- [ ] Cache is checked before Gemma calls in intent resolution flow
- [ ] Cache is populated after successful Gemma resolution
- [ ] TTL default 7 days, configurable via env var
- [ ] Cache stores pre-slider baseline data (effort=balanced, loan_pct=1.0)
- [ ] Expired entries are evicted on server startup
- [ ] Admin endpoint to clear cache manually
- [ ] Hit counter for analytics

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Cache pre-slider data only | Effort/loans are student-specific; base career outcomes are shared | Cache per effort+loans combo (25 combos per school+major — wasteful) |
| 2 | DuckDB table, not Redis/memcached | Same DB, same connection pattern, no new infrastructure | Redis (adds operational complexity for a hackathon project) |
| 3 | TTL-based expiry, not version-based | Simple; data pipeline runs are infrequent enough that 7-day TTL is safe | Iceberg snapshot versioning (over-engineered) |
| 4 | Three-tier lookup: in-memory → DuckDB → Gemma | In-memory for hot path, DuckDB for warm restarts, Gemma as fallback | DuckDB only (slower for repeat requests in same session) |

### Constraints

- [TO BE DETAILED post-hackathon]

---

## §3 UI/UX Design

> SKIPPED — backend-only spec. No UI changes. Cache is transparent to the frontend.

---

## §4 Technical Specification

### Architecture Overview

[TO BE DETAILED — skeleton below]

**New DuckDB table:** `resolution_cache`

```sql
CREATE TABLE IF NOT EXISTS resolution_cache (
    cache_key VARCHAR PRIMARY KEY,        -- "{unitid}:{normalized_major_text}"
    unitid INTEGER NOT NULL,
    major_text_normalized VARCHAR NOT NULL,
    school_name VARCHAR NOT NULL,
    intent_result VARCHAR NOT NULL,       -- JSON: full IntentResult
    career_outcomes VARCHAR,              -- JSON: list[CareerOutcome] (baseline effort/loans)
    tiered_careers VARCHAR,               -- JSON: tiered career grouping
    gemma_model VARCHAR,
    gemma_backend VARCHAR,
    created_at VARCHAR NOT NULL,
    expires_at VARCHAR NOT NULL,
    hit_count INTEGER DEFAULT 0
)
```

**New service:** `backend/app/services/resolution_cache_db.py`

**Modified service:** `backend/app/services/intent.py` — add DuckDB cache as tier-2 lookup

**Integration points:**
- `resolve_intent()` checks DuckDB before calling Gemma
- `confirm_intent()` writes to DuckDB after successful resolution
- `/build/outcomes` response is cached after first fetch
- `/build/tier` response is cached after first Gemma tiering

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/services/resolution_cache_db.py` | Create | Cache service with get/put/evict functions |
| `backend/app/services/intent.py` | Modify | Add DuckDB cache as tier-2 lookup before Gemma |
| `backend/app/routers/builds.py` | Modify | Cache outcomes and tiering results after computation |
| `backend/app/main.py` | Modify | Add cache eviction to startup event |

### Data Model Changes

[TO BE DETAILED]

### Service Changes

[TO BE DETAILED]

### Testing Impact Analysis

[TO BE DETAILED]

---

## §5–§11

[PENDING — to be filled when spec is activated post-hackathon]
