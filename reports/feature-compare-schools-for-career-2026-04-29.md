# Report: Peer-School Leaderboard (Dual Mode — by Career, by Major)

**Spec:** `docs/specs/feature-compare-schools-for-career.md`
**Status:** COMPLETE
**Date:** 2026-04-29
**Author:** Jeff Cernauske + Claude Code

---

## What shipped

A dual-mode peer-school leaderboard that ranks programs by composite ERN+ROI:

- **`by_soc` mode** — "Compare schools for this career" trigger on `CareerDetail` (RevealScreen). Right-edge slide-in sheet. Used as the click-through destination from Spec B's career-search page.
- **`by_cip_and_soc` mode** — "See it at other schools" inline disclosure panel on `BuildResultsScreen`, between Path+Institution and Build Stats. Tightest apples-to-apples comparison: same major, different schools.

One React component (`CompareSchoolsPanel`), one shared service (`schools_for_career`), one MCP tool (`get_schools_for_career` with `mode` discriminator), two FastAPI endpoints, one new LRU cache.

## Architecture at a glance

```
[Gold zone: consumable.program_career_paths]
          │
          │ Iceberg view via QueryEngine.query_sql (RANK() OVER windowed)
          ▼
[MCP tool: _handle_get_schools_for_career(mode, soc_code, cipcode?, ...)]
          │
          │ mcp_client.call (canonical Gold-zone reader)
          ▼
[FastAPI:  GET /careers/{soc}/schools]   [GET /majors/{cip}/schools/for-career/{soc}]
          │                              │
          ▼                              ▼
[React: CompareSchoolsPanel — sheet (by_soc) / inline (by_cip_and_soc)]
          │
          ▼
[Anchor highlighted in-place if in top-N, appended at index N otherwise,
 or absent when no build context (Spec B click-through)]
```

No Iceberg schema changes. No pipeline rerun. Pure additive read scope.

## Files added or modified

**Backend (Python):**
- `src/mcp_server/futureproof_server.py` — handler, tool registration, two response-field whitelists (HTTP + MCP), LRU cache + sweep registration, `@timed` instrumentation
- `backend/app/models/career.py` — `LeaderboardMode`, `ConfidenceTier`, `LeaderboardMatchQuality`, `AnchorBuild`, `SchoolForCareerRow`, `SchoolsForCareerResponse`
- `backend/app/services/schools_for_career.py` (NEW) — thin MCP shaper
- `backend/app/routers/careers.py` (NEW) — two endpoints + `_dispatch` helper for typed error mapping
- `backend/app/main.py` — router registration

**Frontend (TypeScript / React):**
- `frontend/src/types/build.ts` — TS mirrors of the new Pydantic models
- `frontend/src/api/careers.ts` (NEW) — `fetchSchoolsBySoc`, `fetchSchoolsByCipAndSoc`
- `frontend/src/lib/format.ts` (NEW) — extracted `fmtMoney`, added `roiColorClass`, `statRoiColorClass`
- `frontend/src/components/CompareSchoolsPanel.tsx` (NEW) — sheet + inline + table + states + motion + a11y
- `frontend/src/components/CareerDetail.tsx` — `by_soc` trigger + sheet mount; `fmtMoney` import refactor
- `frontend/src/screens/BuildResultsScreen.tsx` — `by_cip_and_soc` inline panel insertion
- `frontend/src/i18n/strings.ts` — 32 `compareSchools.*` strings (en); empty `ar:` block to satisfy `Record<AppLocale, ...>`

**Tests (4 new files, 36 new tests):**
- `tests/mcp/test_get_schools_for_career.py` — 15 passed (P0/P1/P2 coverage of windowed query, anchor cases, confidence filters, partial_no_bls drop, response whitelist)
- `backend/tests/routers/test_careers_router.py` — 6 passed (happy paths, regex rejection, unknown SOC, partial anchor)
- `backend/tests/services/test_schools_for_career_service.py` — 6 passed (mocked dispatch, mode args, no-DuckDB lock)
- `frontend/src/components/CompareSchoolsPanel.test.tsx` — 9 passed + 1 P2 skipped (mode chip, anchor states, empty escape, pentagon-free contract)
- `frontend/src/components/CareerDetail.test.tsx` — added 1 trigger test (P0)
- `frontend/src/screens/BuildResultsScreen.test.tsx` — added 1 inline trigger test (P0)

## Agent pipeline summary

| Step | Agent | Verdict | Notes |
|------|-------|---------|-------|
| Architecture | @fp-architect | CHANGES REQUESTED → folded in | 7 conditions C1–C7 (service must call mcp_client; drop match_quality predicate; drop composite_score from wire; single windowed RANK; cache wiring; router validator dedup; tighten confidence_tier_program typing) |
| Data review | @fp-data-reviewer | CHANGES REQUESTED → folded in | Verified against 626,406 PCP rows; broad-CIP fallback predicate doesn't exist on stored rows (no-op); recommended optional `min_program_confidence` knob from existing `confidence_tier_program` proxy; precise definition of `total_qualifying_programs` |
| Design vision | @fp-design-visionary | COMPLETE | §3 expanded from ~85 to ~770 lines; asymmetric containers, durable mode chip, anchor row treatment with no-shame contract, motion choreography, ASCII wireframes, full string list |
| GenAI review | @genai-architect | CHANGES REQUESTED → folded in | 5 spec edits (anchor pair must be both/neither; lower default limit to 5 for chat; MCP-only response whitelist; rewrite tool description to disambiguate from get_career_paths; state_abbr documentation) + 2 implementation notes (ISO 8601 generated_at, @timed decorator) |
| Implementation | Claude Code | COMPLETE | All edits applied; smoke tests on real PCP data; backend + frontend builds clean |
| Testing | @test-writer | COMPLETE | 36 new tests across 4 files; in-memory DuckDB seeded for handler tests; mocked `mcp_client.call` for service tests; mocked API client for component tests |
| Design audit | @fp-design-auditor | CHANGES REQUIRED → fixed in post-pass | 15 token violations (notably phantom `bg-surface-elev1/2` rendered transparent; broken anchor border on `display:contents`; wrong ROI thresholds; raw Tailwind classes vs Brightpath tokens). All fixed. |
| Code review | @faang-staff-engineer | CHANGES REQUIRED → 4 🟠 fixed; 4 🟡 deferred to v1.1 | Frontend race in load (generation counter); raw exception leak via `str(exc)` (now opaque code + logger.exception); Pydantic ValidationError handling (now caught separately, future-proofed against v3); inline panel re-fetch on disclosure toggle (state lifted to parent). Plus: focus on close button on sheet mount. |
| Verification | @fp-builder | APPROVED WITH NOTES | Backend ruff/mypy/pytest clean; root pytest 1713 passed; frontend tsc/build clean; vitest 11 pre-existing failures in unrelated `menu/CompareView.test.tsx` and `menu/PentagonOverlay.test.tsx` (flagged in §6) |

## Key data findings

- `consumable.program_career_paths` carries 626,406 rows. Default `min_confidence=medium` filter yields 257,080 rankable rows (have `stat_ern` + `stat_roi`) across 520 SOC codes.
- The proposed `match_quality NOT IN ('broad_cip_substituted', 'broad_cip_unblended')` predicate from the original draft was a no-op against actual stored data. Stored values: `{full, partial_no_onet, partial_no_bls, scorecard_only}`. Substitution-related values are runtime-stamped only inside `_handle_get_career_paths` and never reach Iceberg.
- `partial_no_bls` rows passing `medium` confidence have NULL `stat_ern` → dropped naturally by the composite formula's NULL-in-either-drops behavior. Verified via dedicated P0 test.
- Composite formula `(stat_ern + stat_roi) / 2.0` produces intuitive top-N (Stanford, Princeton, UW Bothell on SOC 15-1252 = Software Developers).

## v1.1 follow-ups (deferred, flagged in §10)

- Drop `limit` from cache key; slice in Python (memory efficiency, not correctness).
- Anchor cipcode canonicalization helper (latent — works on today's `VARCHAR` schema).
- Scan-limit warning log + DQ guard (won't fire today; largest SOC has ~2,000 rows vs 5,000 cap).
- Full focus-trap implementation in SheetEnclosure (current minimum: focus close button on mount).
- MCP-only whitelist actually trimming — currently the handler always emits the HTTP whitelist; the MCP whitelist is documented for future use.
- Live Gemma chat verification (`Ask Gemma` calling the new tool end-to-end on representative queries) — covered by GenAI review walkthroughs but not exercised in CI.
- Spec B (`feature-career-search.md`) implementation — sibling spec exists as a redraft skeleton; needs human spec-write before implementation.

## File-recovery note

This spec was reconstructed mid-session after the original on-disk file vanished from disk during the architecture-review pass (cause undetermined; investigation notes in §11). Reconstruction sources: full conversation context including verbatim §5 review content. The sibling spec `feature-career-search.md` was also lost in the same incident and re-created as a redraft skeleton (its original content was never read into context, so that file requires human spec-writing before workflow execution).

## Verification snapshot

| Check | Result |
|-------|--------|
| Backend ruff (all touched files) | ✓ Clean |
| Backend mypy (new files) | ✓ Clean |
| Backend pytest | ✓ 1252 passed |
| Pipeline pytest (root + MCP) | ✓ 1713 passed |
| Frontend tsc | ✓ Clean |
| Frontend vitest (touched files) | ✓ 56 passed, 1 skipped |
| Frontend vite build | ✓ Clean (798 KB JS / 232 KB gzip) |

## Demo-day note

The visionary called the headline beat: open BuildResults → see the chip rail with the preview pill → click → panel grows in place → top-N stagger lands → 200ms beat → anchor row slides in below the dashed divider with the ◆ marker. **That beat is the moment.** Hackathon deadline May 18, 2026.
