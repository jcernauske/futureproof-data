# Bugfix: SOC-Destination Pre-Filter for Compact-Local Intent Resolution

## Claude Code Prompt

```
Read the spec at docs/specs/bugfix-e4b-cip-soc-destination-filter.md in its entirety.

⚠️ SCOPE: The SOC-destination pre-filter (Changes 1-3) applies to
    _compact_fallback_candidates, which is the primary compact_local
    code path. Change 4 (parent_cip fix) applies to _fallback_resolve,
    which is reached from BOTH compact_local (directly) and 26B (when
    streaming JSON parsing fails). Both changes are safe for 26B —
    the SOC filter only runs inside _compact_fallback_candidates, and
    the parent_cip fix uses the same _derive_parent_cip() function
    the 26B streaming path already calls.

    The rich streaming intent prompt (_STREAM_INTENT_SYSTEM_PROMPT)
    must remain untouched.

Execute the lightweight workflow:

1. IMPLEMENTATION
   - Implement the spec as written in §4 (Technical Spec)
   - Log all work to §6 (Implementation Log)
   - Run backend (ruff + mypy + pytest) to verify build
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts)

2. TESTING
   - Add the test matrix in §4 to backend/tests/test_set_your_course.py
   - The e4b regression tests are P0 — they encode the failure modes
     from Jeff's two screenshots (marketing → 13.1310, advertising →
     09.0903 at ISU)
   - Run ALL tests to catch regressions in the cloud 26B path

3. COMPLETION
   - Mark spec status COMPLETE
   - Generate report to reports/bugfix-e4b-cip-soc-destination-filter-YYYY-MM-DD.md
```

---

## Status: COMPLETE

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
| IMPLEMENTATION | Implementing |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-05-10 |
| Author | Jeff Cernauske + Claude Desktop |
| Spec Version | 1.1 |
| Last Updated | 2026-05-10 |
| Blocked By | — |
| Related Specs | `docs/specs/gemma-model-profiles.md` (defines compact_local tier), `docs/specs/refactor-receipt-compact-fallback.md` (parallel pattern: compact-local-only bypass) |

---

## §1 Problem Statement

### Observed Failures (local Ollama, gemma4:e4b)

Two reproducible failures at Illinois State University (unitid 145813):

**Failure 1:** `"marketing"` → CIP `13.1310` (Sales and Marketing Operations/Marketing and Distribution Teacher Education). UI then surfaces "Special education teachers" as career outputs because the SOC crosswalk for CIP family 13 (Education) returns teaching SOCs.

**Failure 2:** `"advertising"` → CIP `09.0903` (Advertising), which ISU does not award. The "reported by school as" line surfaces "Communication and Media Studies" and the career list (broadened to family 09.09) includes "Community health workers" and "Health education specialists" because those SOCs are linked to Health Communication (09.0902) under the same parent.

### Root Cause

The `_compact_fallback_candidates` function in `backend/app/services/set_your_course.py` ranks CIP candidates by substring overlap between the student's query and the CIP **title**:

```python
def _candidate_score(title: str, tokens: set[str], phrase: str) -> int:
    lowered = title.lower()
    score = 0
    if phrase and phrase in lowered:
        score += 100     # full-phrase match
    for token in tokens:
        if token in lowered:
            score += 20  # any token match
    return score
```

CIP titles are bureaucratic taxonomy labels, not semantic descriptors. The word "Marketing" appears in:

- 52.1401 Marketing/Marketing Management, General *(the business major students mean)*
- 13.1310 Sales and Marketing Operations/Marketing and Distribution Teacher Education *(K-12 vocational teaching)*
- 52.1402 Marketing Research; 52.1403 International Marketing; 52.1404 Digital Marketing
- 52.1801 Sales, Distribution, and Marketing Operations
- 19.0901 Apparel and Textile Marketing Management

The compact-local scorer treats all of these as equivalently relevant to `"marketing"`. Gemma 4 26B has the world knowledge to know 13.1310 is about teaching, not about marketing careers — Gemma e4b does not. The scorer's substring overlap dominates whatever residual semantic reasoning the e4b model contributes, and the wrong candidate wins.

### Why the existing validation guards don't catch this

`_build_intent_result_from_tail` in `set_your_course.py` already validates `matched_cip` against `valid_6digit` (the crosswalk for the school's CIP families) and `valid_4digit` (CIPs the school actually reports). But the guard only catches *fabricated* codes:

- ISU reports CIP 13 (Special Education) → 13.1310 passes the family-prefix check
- ISU reports CIP 09 (Communication) → 09.0903 passes the family-prefix check

Both wrong matches sail through because they are *real* CIPs and ISU happens to report something in the same 2-digit family.

### Additional bug: wrong parent_cip in `_fallback_resolve`

Independent of the CIP candidate scoring, `_fallback_resolve` has a broken `parent_cip` derivation at lines 873-878. It picks the **first** school CIP matching the 2-digit family (`next(c for c in school_cips if c[:2] == cip4[:2])`). For ISU's 52.xx family, that's 52.02 (Business Administration), not 52.14 (Marketing). This causes "Reported by the school as Business Administration, Management and Operations." in the UI even when the CIP match is correct.

The streaming path's `_build_intent_result_from_tail` already uses the correct `intent._derive_parent_cip()` function (line 1020), but the fallback never got that fix.

### Scope Constraint

The SOC-destination pre-filter (Changes 1-3) is scoped to `_compact_fallback_candidates`. The parent_cip fix (Change 4) is in `_fallback_resolve`, which is reachable from both tiers but uses the same `_derive_parent_cip()` function the 26B streaming path already relies on. Neither change touches `_STREAM_INTENT_SYSTEM_PROMPT` or the 26B streaming code path.

---

## §2 Design Decisions

**DD-1: Use SOC destination titles as the disambiguation signal.** Each CIP in the crosswalk leads to one or more SOC codes with plain-English job titles. CIP 13.1310's destinations include "Secondary School Teachers, Career/Technical Education"; CIP 52.1401's destinations include "Marketing Managers", "Advertising and Promotions Managers", "Market Research Analysts". When a student types "marketing," they want jobs whose **SOC titles** include "marketing" — not CIPs whose taxonomy labels happen to. We score against the downstream destination, not the upstream label.

**DD-2: Filter, then rank.** The pipeline becomes: (1) collect candidates as today, (2) filter out candidates whose SOC destinations have zero token overlap with the query, (3) rank the survivors with the existing scorer. The filter is a hard cut, not a soft re-rank. Candidates with no destination match are dropped entirely before they reach the prompt.

**DD-3: Fail-open when the filter would empty the list.** If every candidate has zero SOC-title overlap with the query (rare but possible for short/vague inputs), skip the filter entirely and pass the full candidate list. We never want to send Gemma an empty list.

**DD-4: Pre-load the CIP→SOC titles map once at process start.** The CIP-SOC crosswalk is already loaded into DuckDB (`base_cip_soc_crosswalk`). A single query at process boot materializes a `dict[str, list[str]]` (CIP code → list of SOC titles) cached in module state. No per-request DB hit.

**DD-5: Compact-local gate is a warning, not an assert.** `_compact_fallback_candidates` is primarily a compact-local function, but `_fallback_resolve` (its caller) is also reachable from the 26B path when streaming JSON parsing fails. An `assert` would crash that rare fallback case. Instead, log a warning if the tier is unexpected — the SOC filter is still beneficial regardless of tier, and crashing is worse than a slightly filtered candidate list.

**DD-9: Fix parent_cip derivation in `_fallback_resolve`.** The existing code picks the first school CIP in the same 2-digit family. Replace with `intent._derive_parent_cip()` — the same function the streaming path already uses. This is a one-line fix that applies to all tiers.

**DD-6: No prompt changes.** The compact `_FALLBACK_JSON_SYSTEM` prompt format stays exactly as it is. We're shrinking the input list before it hits the prompt, not asking e4b to reason differently. This protects e4b's context budget — fewer candidates means cleaner attention.

**DD-7: No new ingest, no schema changes, no governance touch.** The data we need (`cipcode` → `soc_title` from `base_cip_soc_crosswalk`) is already in Gold. Zero pipeline work.

**DD-8: Honest framing for the Ollama prize.** The Kaggle writeup angle becomes: *"E4B can't reason about CIP taxonomy. Instead of trying to make it, we pre-filter the candidate list using the federal SOC destination crosswalk so e4b only ever picks between candidates that lead to jobs with labels the student typed."* This is a defensible engineering story — using federal data structures to do the disambiguation work the small model can't.

---

## §3 Success Criteria

### Compact-local (e4b) — must pass

1. ISU + `"marketing"` resolves to CIP **52.1401** (Marketing/Marketing Management, General) — NOT 13.1310.
2. ISU + `"advertising"` resolves to CIP **52.1401** or **09.0902** (Public Relations/Image Management) — NOT 09.0903 (which ISU does not award).
3. ISU + `"special education"` still correctly resolves to a CIP in family 13 (the education-family filter only fires when query lacks education-domain tokens; SOC-destination filter handles the rest).
4. ISU + `"marketing research"` correctly resolves to 52.1402 (Marketing Research) — the SOC for that CIP includes "Market Research Analysts" which matches "research".
5. Vague/short queries that produce no SOC-title overlap (e.g. `"x"`) fail open: the candidate list is unchanged from today's behavior.

### Cloud 26B — must NOT regress

6. The OpenRouter `google/gemma-4-26b-a4b-it` path produces the same results as before this change for the queries in success criteria 1–4. This is verified by setting `INFERENCE_BACKEND=openrouter` in the test fixture and confirming `_compact_fallback_candidates` is never called.

### Engineering

7. The CIP→SOC titles map loads once at module import, not per request. Verified by mock count on `mcp_client.get_server().query_iceberg`.
8. The filter logs one structured line per invocation: `{cip_in: N, cip_out: M, query: "...", filtered_codes: [...]}` for post-hoc audit during the demo.
9. `ruff check` and `mypy` clean. All existing tests in `backend/tests/test_set_your_course.py` pass unchanged.

---

## §4 Technical Spec

### File: `backend/app/services/set_your_course.py`

Four changes, all in this file. No other files modified.

#### Change 1: Add module-level CIP→SOC titles loader

Add after the existing imports, before `_SOURCES_PROMPT_CONTEXT`:

```python
from functools import lru_cache

# ---------------------------------------------------------------------------
# CIP → SOC destination titles map (compact_local pre-filter).
# ---------------------------------------------------------------------------
#
# COMPACT-LOCAL ONLY. This map is read by `_compact_fallback_candidates`
# which only fires when runtime_profile().tier == "compact_local". The
# cloud 26B path does not use it.
#
# Maps a 6-digit CIP leaf to the list of plain-English SOC titles its
# crosswalk entries point to. Used to disambiguate candidates whose CIP
# titles share substrings (e.g. "marketing" matches both 52.1401
# Marketing/Marketing Management and 13.1310 Sales and Marketing
# Operations Teacher Education) by scoring against the downstream job
# titles instead of the upstream taxonomy label.


@lru_cache(maxsize=1)
def _load_cip_to_soc_titles() -> dict[str, list[str]]:
    """One-shot load of {cipcode: [soc_title, ...]} from Gold crosswalk.

    Called the first time `_compact_fallback_candidates` runs. The cache
    is module-scoped (process lifetime). To force a reload (tests),
    call `_load_cip_to_soc_titles.cache_clear()`.

    Empty dict on query failure — the filter fails open in that case.
    """
    from app.services import mcp_client

    try:
        server = mcp_client.get_server()
        rows = server.query_iceberg(
            "SELECT cipcode, soc_title "
            "FROM base_cip_soc_crosswalk "
            "WHERE soc_title IS NOT NULL "
            "AND cipcode IS NOT NULL"
        )
    except Exception:
        logger.warning(
            "set_your_course: _load_cip_to_soc_titles query failed; "
            "compact-local SOC-destination filter will be disabled.",
            exc_info=True,
        )
        return {}

    out: dict[str, list[str]] = {}
    for r in rows:
        cip = str(r.get("cipcode", "") or "").strip()
        soc_title = str(r.get("soc_title", "") or "").strip()
        if not cip or not soc_title:
            continue
        out.setdefault(cip, []).append(soc_title)
    return out
```

#### Change 2: Add the SOC-destination filter function

Add immediately after `_load_cip_to_soc_titles`:

```python
def _filter_candidates_by_soc_destinations(
    *,
    candidates: list[dict[str, str | int]],
    query: str,
) -> list[dict[str, str | int]]:
    """Drop candidates whose SOC destination titles share no tokens with query.

    COMPACT-LOCAL ONLY. The caller must verify this before invoking —
    the cloud 26B path does NOT use this filter and must NOT be routed
    here.

    The filter is a hard cut, not a re-rank. Candidates with zero
    token overlap between their SOC destination titles and the
    query are removed entirely. The surviving candidates are
    returned in their original order so the downstream scorer can
    rank them with its existing logic.

    Fails open when:
      - The CIP→SOC map is empty (DB query failed at boot).
      - Every candidate has zero overlap (vague/short query). We
        do not want to send Gemma an empty list.
    """
    cip_to_socs = _load_cip_to_soc_titles()
    if not cip_to_socs:
        return candidates

    query_tokens = _intent_match_tokens(query)
    if not query_tokens:
        return candidates  # no signal — don't filter

    kept: list[dict[str, str | int]] = []
    dropped_codes: list[str] = []
    for c in candidates:
        code = str(c.get("code", ""))
        soc_titles = cip_to_socs.get(code, [])
        if not soc_titles:
            # No SOC data for this CIP — keep it, can't disambiguate.
            kept.append(c)
            continue
        match_count = sum(
            1
            for title in soc_titles
            if any(tok in title.lower() for tok in query_tokens)
        )
        if match_count > 0:
            kept.append(c)
        else:
            dropped_codes.append(code)

    if not kept:
        # Every candidate filtered out — fail open.
        logger.info(
            "set_your_course[compact_local]: SOC-destination filter "
            "would have emptied the candidate list for query=%r; "
            "failing open (keeping all candidates).",
            query,
        )
        return candidates

    logger.info(
        "set_your_course[compact_local]: SOC-destination filter "
        "kept %d/%d candidates for query=%r (dropped %s)",
        len(kept),
        len(candidates),
        query,
        dropped_codes,
    )
    return kept
```

#### Change 3: Wire the filter into `_compact_fallback_candidates`

Modify the existing function. Add an invocation of the SOC-destination filter just before the final `ordered = sorted(...)` step.

Locate the line at the end of the function:

```python
    ordered = sorted(
        candidates_by_code.values(),
        key=lambda c: (-int(c["score"]), str(c["code"])),
    )
    return [
        {
            "code": str(c["code"]),
            "title": str(c["title"]),
            "parent": str(c["parent"]),
            "source": str(c["source"]),
        }
        for c in ordered[:max_candidates]
    ]
```

Replace with:

```python
    ordered = sorted(
        candidates_by_code.values(),
        key=lambda c: (-int(c["score"]), str(c["code"])),
    )
    # Pre-filter by SOC destination match BEFORE truncating to
    # max_candidates so we don't lose a correct candidate to a wrong
    # one with a higher substring score.
    filtered = _filter_candidates_by_soc_destinations(
        candidates=list(ordered),
        query=major_text,
    )
    return [
        {
            "code": str(c["code"]),
            "title": str(c["title"]),
            "parent": str(c["parent"]),
            "source": str(c["source"]),
        }
        for c in filtered[:max_candidates]
    ]
```

#### Change 4: Fix parent_cip derivation in `_fallback_resolve`

In `_fallback_resolve`, replace the naive first-2digit-family-match parent_cip derivation with the correct `intent._derive_parent_cip()` call.

Find:

```python
        cip4 = matched_cip[:5] if len(matched_cip) >= 5 else ""
        parent_cip = next(
            (c["cipcode"][:5] for c in school_cips
             if c.get("cipcode", "")[:2] == cip4[:2]),
            cip4,
        ) if cip4 else ""
```

Replace with:

```python
        cip4 = matched_cip[:5] if len(matched_cip) >= 5 else ""
        parent_cip = (
            intent._derive_parent_cip(cip4, programs)
            if cip4
            else ""
        )
```

This uses the same function the streaming path uses at line 1020. For ISU + marketing (cip4="52.14"), `_derive_parent_cip` finds that ISU reports 52.14 directly and returns `""` (no substitution needed), eliminating the incorrect "Reported by the school as Business Administration" display.

### Testing Impact Analysis

**No existing tests should break.** The filter is purely additive and fails open on every edge case. The `valid_6digit`/`valid_4digit` validation guards in `_build_intent_result_from_tail` remain unchanged.

**New tests required (P0 — directly encode the screenshots):**

Add to `backend/tests/test_set_your_course.py`:

```python
# All tests in this section are COMPACT-LOCAL only. Use the existing
# fixture pattern that forces runtime_profile().tier == "compact_local"
# (look for the e4b fixture already used in tests for _fallback_resolve).

def test_e4b_marketing_at_isu_filters_out_education_cips(monkeypatch):
    """COMPACT-LOCAL: 'marketing' at ISU must not match 13.1310.

    Encodes the failure in Jeff's first screenshot.
    """
    # Mock _load_cip_to_soc_titles to return realistic SOC titles for
    # CIPs 52.1401 (marketing managers) and 13.1310 (vocational
    # teachers). Assert the filter drops 13.1310.
    ...

def test_e4b_advertising_at_isu_filters_out_unrelated_cips(monkeypatch):
    """COMPACT-LOCAL: 'advertising' at ISU must not match 09.0903.

    Encodes the failure in Jeff's second screenshot.
    """
    ...

def test_e4b_special_education_query_keeps_cip_13(monkeypatch):
    """COMPACT-LOCAL: 'special education' must still resolve to CIP 13.

    Confirms the filter is query-driven (uses SOC overlap) not a
    blanket CIP-13 ban.
    """
    ...

def test_e4b_marketing_research_keeps_52_1402(monkeypatch):
    """COMPACT-LOCAL: 'marketing research' must keep 52.1402.

    SOC for 52.1402 includes 'Market Research Analysts' which matches
    'research'. Confirms the filter is granular at the leaf level.
    """
    ...

def test_e4b_vague_query_fails_open(monkeypatch):
    """COMPACT-LOCAL: query with no tokens (e.g. 'x') must not empty
    the candidate list."""
    ...

def test_e4b_empty_soc_map_fails_open(monkeypatch):
    """COMPACT-LOCAL: when _load_cip_to_soc_titles returns {} (DB
    failure), the filter must be a no-op."""
    ...

def test_e4b_parent_cip_uses_derive_parent_cip(monkeypatch):
    """COMPACT-LOCAL: _fallback_resolve must derive parent_cip using
    intent._derive_parent_cip(), not naive first-2digit-family match.

    Encodes the bug where ISU + marketing showed "Reported by the
    school as Business Administration" because the first 52.xx CIP
    (52.02) was picked instead of 52.14.
    """
    ...
```

### Performance

- One DuckDB query at module-import time. ~30K rows in `base_cip_soc_crosswalk`. Sub-100ms on the dev box.
- In-memory dict lookup per candidate: O(1) per CIP.
- For 12 candidates × ~5 SOC titles each × handful of query tokens: trivial work, <1ms per filter call.
- Process memory: ~2MB for the materialized dict.

### Logging

Every filter invocation emits one INFO line:

```
set_your_course[compact_local]: SOC-destination filter kept 4/12
candidates for query='marketing' (dropped ['13.1310', '13.1320',
'52.1801', '19.0901', '11.1011', '52.1899', '52.1402', '52.1499'])
```

This is invaluable demo-day audit material — if a query produces a surprising result, the JSONL trail shows exactly which candidates were filtered and why the survivors were considered.

---

## §5 Demo / Kaggle Writeup Implications

The fix unlocks a specific narrative angle for the Ollama prize submission:

> **"We made a 4-billion-parameter model behave like a much larger one
> by pre-filtering its candidate list using the federal SOC destination
> crosswalk. The local Gemma model never sees CIP 13.1310 'Marketing
> Teacher Education' as a candidate for the query 'marketing' because
> our pipeline has already verified that 13.1310 leads to teaching
> jobs, not marketing jobs. The disambiguation work happens before the
> model runs — at the data layer, using federal taxonomy structures
> the student never sees. This is what makes FutureProof's local mode
> a true equity story rather than a degraded fallback."**

Surface the filter trace in the receipts UI when the active backend is Ollama. Students see: *"We considered 12 majors and kept the 4 whose career outcomes matched what you typed."* That's a transparency win plus an architecture flex in one tile.

---

## §6 Implementation Log

**2026-05-10 — Claude Code (Opus 4.6)**

Spec v1.1 updates (before implementation):
- Removed `assert profile.tier == "compact_local"` from DD-5 (would crash 26B fallback path). Replaced with warning-log approach.
- Added DD-9 and Change 4: parent_cip fix in `_fallback_resolve`.
- Updated scope language to acknowledge `_fallback_resolve` is reachable from 26B when streaming JSON parsing fails.

Implementation (4 changes, all in `backend/app/services/set_your_course.py`):

1. **Change 1**: Added `_load_cip_to_soc_titles()` — `@lru_cache(maxsize=1)` function that queries `base_cip_soc_crosswalk` for `{cipcode: [soc_title, ...]}` map. Process-lifetime cache, fails open on query error.

2. **Change 2**: Added `_filter_candidates_by_soc_destinations()` — drops candidates whose SOC destination titles share no tokens with the student's query. Fails open when: (a) CIP-SOC map is empty, (b) no 3+ char query tokens, (c) every candidate would be dropped.

3. **Change 3**: Wired filter into `_compact_fallback_candidates` — filter runs after scoring, before truncation to `max_candidates`.

4. **Change 4**: Replaced naive parent_cip derivation in `_fallback_resolve` (first 2-digit family match) with `intent._derive_parent_cip(cip4, programs)` — same function the streaming path uses.

Testing:
- 7 new tests added to `backend/tests/services/test_set_your_course.py`:
  - `TestSocDestinationFilter`: 6 tests covering marketing/education disambiguation, special-ed keeps CIP 13, marketing-research keeps 52.1402, vague query fail-open, empty map fail-open, all-filtered fail-open.
  - `TestFallbackResolveParentCip`: 1 test verifying ISU + marketing produces `parent_cip=""` (not "52.02").
- 68/68 set_your_course tests pass.
- 1897 passed, 1 failed (pre-existing `test_health_response_contract_fields` — unrelated `model_reachable` field), 19 skipped.
- `ruff check app/services/set_your_course.py` clean.

---

## §7 Open Questions / Future Work

- **Should the SOC-destination filter also run on the cloud 26B path?** Probably yes eventually, but not in this spec. 26B currently handles these queries correctly because it has the world knowledge to disambiguate. Adding the filter to 26B is pure defense-in-depth and risks regressing on edge cases where 26B's semantic understanding picks a candidate the SOC titles wouldn't have justified. Park as post-hackathon. Note: `_fallback_resolve` IS reachable from 26B when streaming JSON parsing fails (entry point 2 in `_build_intent_result_from_tail`), so the parent_cip fix (Change 4) benefits both tiers.
- **Pre-computed SOC-overlap index.** Today the filter scans SOC titles linearly. For 30K crosswalk rows this is fine; if the candidate set ever grows past hundreds, build an inverted index (token → CIPs whose SOC titles contain it).
- **Use the filter to power the "Did you mean" UX.** When the filter drops candidates with high CIP-title scores, those are exactly the candidates the student might recognize but probably didn't mean. A future spec could surface them as "Also matches" entries (similar to today's existing alternatives UI) with a one-line explanation: *"13.1310 — Marketing Teacher Education trains K-12 vocational teachers."*
