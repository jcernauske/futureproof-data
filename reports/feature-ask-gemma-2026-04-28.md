# Feature: Ask Gemma — Scope-Aware Build Q&A

**Spec:** `docs/specs/feature-ask-gemma.md`
**Status:** COMPLETE
**Date:** 2026-04-28
**Author:** Jeff Cernauske + Claude Code

---

## Summary

Wired a scope-aware "Ask Gemma" chat surface across `/my-build` (per-element entry points + sticky FAB) and the build compare screen (entry point under "Gemma's Take"). The student can now click a stat's "?" popover, a boss band's "Ask why" pill, an applied-skill chip's ✦ icon, the bottom-right FAB, or the compare-screen button — and the chat opens with the right scope pre-loaded.

The new `POST /chat/ask` endpoint takes a discriminated `scope` (stat, boss, skill, build, compare) and routes through one of five context-builders that ground Gemma in the actual numeric drivers behind every claim — composite AI exposure, Karpathy score, Anthropic adoption, BLS growth category, O*NET task breakdowns, financed debt-to-earnings, modeled total debt, raw boss scores with thresholds. The four-tool MCP allowlist (`get_career_paths`, `get_occupation_data`, `get_regional_price_parity`, `compare_purchasing_power`) lets Gemma fetch "what if" answers (different school, different state, different career).

The voice contract is preserved end-to-end: every stat code, outcome label, and game-framing word in the rendered context is wrapped in `[helper: ...]` brackets that Gemma is instructed never to echo. Static and dynamic voice tests block ship if any forbidden token leaks.

## What Changed

### Backend
- `backend/app/services/ask_gemma.py` (NEW, 789 lines) — 5 context-builders, `_SYSTEM_BASE`, four-tool allowlist, `chat_ask` entry point, trivial `_dispatch` (no `student_cip` injection), `_helper()` wrapper, alias maps, `_fold_history`, `SkillNotFoundError`.
- `backend/app/routers/ask_gemma_router.py` (NEW, 47 lines) — `POST /chat/ask`. 404 on unknown build_id / unknown skill_id. 422 from Pydantic model validator on bad scope payloads. 200 with `chat_unavailable` localized fallback on Gemma transport / tool-dispatch / turn-cap / wall-time exhaustion.
- `backend/app/models/api.py` — `AskScopeKind`, `AskScope` (with cardinality + target_id model validator), `AskRequest`, `AskResponse`.
- `backend/app/services/guidance.py` — extracted `_SHARED_VOICE_RULES` constant from `_CHAT_SYSTEM`. Voice rules now have one source of truth; `_CHAT_SYSTEM` reconstructed byte-equivalent (voice-contract tests still 25/25 passing).
- `backend/app/main.py` — registered the router.

### Frontend
- `frontend/src/components/menu/AskGemmaFab.tsx` (NEW) — 56pt circle, breathing glow via `animate-gemma-fab-breathe`, `springs.smooth` AnimatePresence, hover tooltip (desktop only), safe-area inset, reduced-motion fallback.
- `frontend/src/api/menu.ts` — `AskScope` discriminated union type, `askGemma()` client.
- `frontend/src/components/menu/GemmaChat.tsx` — accepts `scope` and `chipText` props. Header chip renders `data-testid="chip-chat-scope"` when scope is set; legacy `contextLine` chip preserved for backwards compat.
- `frontend/src/components/build-results/StatInfoPopover.tsx` — added `onAsk` and `chatOpen` props. Inline "✦ Ask Gemma about this" CTA with hairline divider.
- `frontend/src/components/build-results/BossBand.tsx` — per-boss "Ask why" pill (result-aware tint at 8% alpha) and per-skill ask icon-button (24×24 with `-m-2` hit-area expander). Skill card refactored from `<button>` to `<div role="button" tabIndex={0}>` with explicit Enter/Space keyboard handlers.
- `frontend/src/components/menu/CompareView.tsx` — `btn-ask-compare` thrive-green CTA beneath the "Gemma's Take" card; only renders when `compare_summary` is non-null.
- `frontend/src/screens/BuildResultsScreen.tsx` — chat state lifted; per-element handlers wired; `<AskGemmaFab>` and `<GemmaChat>` mounted.
- `frontend/src/index.css` — `gemma-fab-breathe` keyframe + `.animate-gemma-fab-breathe` utility + reduced-motion override.
- `frontend/src/i18n/strings.ts` — 8 new keys × 2 locales; all voice-contract clean.

## Architecture Review

**Reviewer:** @fp-architect + @genai-architect (parallel)
**Verdict:** CHANGES REQUESTED (1st pass) → APPROVED (2nd pass after spec revisions)

Key conditions on first pass and how they were resolved before implementation:

| # | Condition | Resolution |
|---|-----------|------------|
| Architect-1 | Manifest table referenced fields not on `CareerOutcome` (`composite_exposure`, `wage_percentile_*`, `bls_employment_*`, `boss_loans_score`, `anthropic_adoption_share`) | Rewrote §4 manifest with actual API field names (`composite_method`, `karpathy_score`, `ai_adoption_share`, `growth_category`, `BossFightResult.raw_score`/`threshold_win`/`threshold_draw`). |
| Architect-2 | `_CHAT_SYSTEM` extraction shape unspecified | Made explicit: `_CHAT_SYSTEM = f"...{_SHARED_VOICE_RULES}..."`. |
| Architect-3 | Compare builder dollar-format drift risk | Bound to `boss_fights.fmt_dollars`. |
| Architect-4 | `_dispatch` over-copy risk (`student_cip` injection) | Documented: trivial passthrough, no injection. |
| Architect-5 | Empty-string fallback contract not uniform | Enumerated: 4 failure modes (transport, dispatch, turn-cap, wall-time) all route to `chat_unavailable`. |
| GenAI-F1 | `_SYSTEM_BASE` would fail voice-contract tests on day one | Registered in `test_gemma_voice_contract.py:SYSTEM_PROMPTS`; passes via `_SHARED_VOICE_RULES` inheritance. |
| GenAI-F2 | `tool_choice="auto"` at temp 0.7 too permissive | Lowered to `_TEMPERATURE = 0.4`; context block prefixed with `[CONTEXT — already loaded, no tool call needed for this data]`. |
| GenAI-F3 | Context field labels would embed forbidden tokens | Added `[helper: ...]` bracket convention with system-prompt rule "never reproduce them verbatim or paraphrase their notation in your reply". |
| GenAI-F7 | Hallucinated-CIP risk on hypothetical-major tool calls | Added explicit guard sentence to `_SYSTEM_BASE`: "tell them to start a new build with that major rather than guessing". |

## Design Vision

**Designer:** @fp-design-visionary (570-line §3 deliverable)

Visual language: every entry point uses the existing Gemma sparkle `✦`. Resting accent `text-accent-insight`; hover wash `bg-state-loading`; press `transitions.press`; focus ring `ring-focus-ring`. The five entry points are five sizes of the same chord: text-link (stat popover) → ghost button (boss pill) → icon button (skill ✦) → FAB (whole build) → hero button (compare).

The FAB is the only breathing element on `/my-build` apart from the stat-pentagon vertex glow. Voice-contract clean throughout: `aria-label`s use risk-category language ("Ask Gemma why this risk passed") instead of game framing.

## Design Audit

**Auditor:** @fp-design-auditor
**Verdict:** CHANGES REQUIRED → resolved

| File | Fix Applied |
|---|---|
| `BossBand.tsx:418` | Added `hover:border-border` to boss pill. |
| `AskGemmaFab.tsx:65` | Added `hover:shadow-glow-insight` to FAB. |

All other surfaces audited PASS — Brightpath token compliance verified across 6 surfaces (FAB, keyframe, stat CTA, boss pill, skill icon, scope chip, compare button).

## Code Review

**Reviewer:** @faang-staff-engineer
**Verdict:** APPROVED

Six concerns logged (none blocking):
- C1: minor FAB flicker risk on chat exit (polish, deferred)
- C2: `assert` statements in handler (harmless today; would be stripped under `python -O`)
- C3: mock fallback in prod builds (pre-existing pattern, ops hygiene)
- C4: `_fold_history` voice-contract injection surface from prior turns (low realistic impact, future test concern)
- C5: unbounded `history` field (pre-existing on legacy `ChatRequest` too)
- C6: `compareScope` memo dep on array reference (no current impact)

All four spec-mandated focus areas verified: scope discriminator validation, tool-loop latency budget, empty-string fallback contract uniformity, no PII in `logs/gemma.jsonl`, `_dispatch` correctness.

## Tests

**Test author:** @test-writer
**New:** 84 tests across 4 new files + 3 modified files. All pass.

| File | Count | What It Tests |
|---|---|---|
| `backend/tests/services/test_ask_gemma.py` (NEW) | 17 | Context-builders. Includes the **HARD GATE** `test_context_blocks_never_leak_forbidden_tokens` — walks every scope kind, asserts no leak outside `[helper: ...]` spans. |
| `backend/tests/services/test_ask_gemma_voice.py` (NEW) | 26 | 18-prompt jailbreak battery + jailbreak-held + 7-case negative test that confirms the assertion would catch a leak. |
| `backend/tests/routers/test_ask_gemma_router.py` (NEW) | 18 | All 5 scope kinds, 8 validator-rejected payloads, both 404 paths, English + Spanish fallback locales, tool-loop dispatch telemetry. |
| `backend/tests/services/test_gemma_voice_contract.py` (extended) | +3 | Registered `ask_gemma._SYSTEM_BASE` in `SYSTEM_PROMPTS`; passes via `_SHARED_VOICE_RULES` inheritance. |
| `frontend/src/components/menu/AskGemmaFab.test.tsx` (NEW) | 3 | Visibility logic, label, aria-label. |
| `frontend/src/components/menu/GemmaChat.test.tsx` (extended) | +8 | Scope routing, chip rendering, legacy backwards-compat. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` (extended) | +4 | Per-stat / per-boss / per-skill / FAB scope dispatch. |
| `frontend/src/components/menu/CompareView.test.tsx` (extended) | +2 | Compare button + scope chip. |

**Production-code fix discovered by tests:** The `test_context_blocks_never_leak_forbidden_tokens` hard gate caught one leak — `BossFightResult.reason` is a scorer summary string (e.g. `"RES 4 + HMN 5 = 9"`) that bypassed the helper-bracket convention. Fix: wrap `fight.reason` in `_helper(...)` in `_context_for_boss`. Voice contract intact.

## Build Verification

**Verifier:** @fp-builder
**Verdict:** PASSED (after one iteration)

| Check | Result |
|---|---|
| Backend ruff | ✓ PASS |
| Backend mypy (this spec's files) | ✓ PASS — 0 errors on `ask_gemma.py`, `ask_gemma_router.py`, `models/api.py` (after `list[dict[str, Any]]` fix), `guidance.py`. 71 pre-existing errors in unrelated files documented as not introduced. |
| Backend pytest | ✓ PASS — 1211 passed, 0 failed |
| Frontend tsc | ✓ PASS |
| Frontend vitest | ✓ PASS — 663 passed (11 pre-existing failures in `CompareView.test.tsx` and `PentagonOverlay.test.tsx` documented as not introduced; verified by stash diff against `main`) |
| Frontend Vite build | ✓ PASS — 915 kB bundle |

## Key Design Decisions

1. **Single discriminated route over 5 endpoints.** New scopes can be added via Literal extension + new context-builder, no router work.
2. **New service module rather than extending `guidance.py`.** `guidance.py` was already 4 prompts deep; a 5th surface with 5 context-builders would push it past the comprehension threshold.
3. **Per-element entry points on `/my-build` + sticky FAB**, not just the FAB. Each entry point pre-narrows context, tightens the token budget, and matches the "ask right where the question forms" UX win.
4. **MCP function calling enabled (4-tool allowlist).** Without it Gemma must punt every "what if" follow-up. With it the long-tail of student questions gets honest answers.
5. **Helper-bracket convention.** Forbidden tokens stay in Gemma's reasoning context but never echo. Static `test_context_blocks_never_leak_forbidden_tokens` enforces it.
6. **Temperature 0.4 (not 0.7) for Ask Gemma.** Suppresses speculative tool calls under `tool_choice="auto"` — Gemma 4 prefers context when temperature is lower.

## Spec Workflow Compliance

| Step | Agent | Verdict |
|---|---|---|
| 1. Architecture Review | @fp-architect + @genai-architect | CHANGES REQUESTED → APPROVED |
| 2. Design Vision | @fp-design-visionary | DELIVERED |
| 3. Implementation | Claude Code | COMPLETE |
| 4. Testing | @test-writer | 84 new tests, all green |
| 5. Design Audit | @fp-design-auditor | CHANGES REQUIRED → fixed |
| 6. Code Review | @faang-staff-engineer | APPROVED |
| 7. Verification | @fp-builder | FAILED → PASSED |
| 8. Completion | — | This report |

---

**Originating prompt:** *"I feel like we need an Ask Gemma feature on the build compare screen."*

**Plan:** `~/.claude/plans/i-feel-like-we-gentle-deer.md`
