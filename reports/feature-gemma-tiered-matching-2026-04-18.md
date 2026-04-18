# Feature: Gemma Tiered Matching — Spec Execution Report

**Spec:** `docs/specs/feature-gemma-tiered-matching.md`
**Branch:** `spec/gemma-tiered-matching` (git worktree)
**Date:** 2026-04-18
**Status:** COMPLETE (all §1 Success Criteria checked)

---

## Summary

Replaced Gemma's binary intent-matching UX in the `/school` flow with a three-tier model driven by Gemma's self-reported `confidence`:

- **high** → existing purple match card, no alternatives. Unchanged.
- **medium** → caution-styled match card with 2–4 inline alternatives ("OR — ONE OF THESE?") between the career preview and the actions row. Click any row to confirm that alternative with the same 320ms thrive flash as the primary.
- **low** → existing clarify picker. Unchanged.

The feature closed two latent defects: the caution styling in `MatchContent` was never reachable (low routed to the picker before it rendered), and the `IntentResult.alternatives` field was shipped end-to-end but ignored by the web UI. Both are now active.

---

## What Shipped

### Backend (`backend/app/services/intent.py`, `backend/cli.py`)

- `_INTENT_SYSTEM_PROMPT` rewritten with a three-tier rubric (0 / 2–4 / up to 10 alternatives).
- Rubric moved **above** the school CIP data block so tier semantics aren't buried behind 20–60 lines of codes (genai-architect finding #3).
- JSON template now shows `"alternatives": []` rather than a populated example, preventing schema pattern-matching from defeating "Never pad" (finding #2).
- High tier gains a lexical-match tiebreaker (finding #1); high example rewritten to a colloquial input (finding #6); medium example augmented with a cross-family alternative (finding #7).
- `max_tokens` raised 500 → 700 to absorb the low-tier ceiling plus the 2-sentence reasoning cap (finding #4).
- JSON parsing hardened to strip trailing prose after the final `}` (finding #8).
- New `_sanitize_alternatives(raw, primary_cip)` function filters non-dicts, non-string types, malformed CIPs (`^\d{2}\.\d{4}$`), entries missing `cip`/`title`, duplicates of the primary CIP, and duplicates of earlier alts; clamps to 10 (findings #9, #10 + code review M2).
- Primary `matched_cip` now regex-validated on ingest; malformed values raise `ValueError` which the router translates to a fallback (code review S1 — asymmetric-defense gap closed).
- Drift-warning comments at both `_INTENT_SYSTEM_PROMPT` sites (architect concern #10).
- CLI prompt mirrored verbatim; byte-identical with the service copy (confirmed via `diff`).

### Frontend (`frontend/src/components/school/MajorInput.tsx`)

- `MatchContent` refactored from binary `isLowConfidence` to tiered `isUncertain = confidence !== "high"`.
- Parent card border-l logic lights caution on `confidence !== "high"` (was `=== "low"`, unreachable post-routing).
- New `AlternativesList` subcomponent renders inside the match card. Reuses the career-preview visual grammar (section label, `▸` glyph, accent-info title → text-primary on hover, right-aligned muted `why` truncated to 280px).
- New `confirmingAltCip` state; `handleAlternativePick` fires the same 320ms thrive flash as the primary CTA, dims siblings to 0.45 opacity, then calls `onConfirm({matched_cip, matched_title})`.
- Parent `handleConfirm(override?)` accepts an optional `{matched_cip, matched_title}` override. Careers preview and `substitutionApplied` are suppressed on alternative confirms (the preview was derived from the primary CIP).
- All new tokens sourced from Brightpath. No new raw hex or rgba introduced; `rgba(125, 212, 163, 0.45)` confirm-flash glow is a literal reuse of the primary CTA value.

### Design system

- `DESIGN.md` gains an appended "Tiered Match Card (Three-Confidence Extension)" subsection documenting the medium tier, tokens, motion, accessibility, degenerate-state policy, and copy rationale. Existing Match Card prose untouched per parallel-worktree discipline.
- `docs/mockups/brightpath-design-system-v3.html` gains an appended "Medium-tier · with alternatives" variant — two cards (default 4 alternatives, confirming-Marketing-row) plus scoped `.gemma-alternatives-*` CSS. Existing Gemma and Tone Exploration sections untouched.

### Tests (net-new)

- `backend/tests/services/test_intent.py` — **17 tests**: 5 P0 tier-behavior, 1 P1 audit-flag preservation, 2 bonus sanitizer tests, 7 parametrized malformed-primary-CIP cases, 1 null-primary-CIP, 1 non-string title/cip. First service-level coverage of `app.services.intent`.
- `frontend/src/components/school/MajorInput.test.tsx` — **6 tests**: 4 P0 (high no-list, medium list + pill, alt click overrides onConfirm, low routes to picker), 2 P1 (empty-alts caution card, flash disables siblings).
- `backend/tests/fixtures/intent_responses.json` — high/medium/low payloads referenced by the tier tests.

---

## Agent Pipeline Timeline

| Step | Agent | Verdict | Notes |
|------|-------|---------|-------|
| 1 | `@fp-architect` | APPROVED | 2 non-blocking cleanups (drift comments, medium-zero-alts policy) — both folded into §4. |
| 1 | `@genai-architect` | CHANGES REQUESTED | 6 required items + 3 non-blocking prompt improvements. All 9 incorporated into §4 Service Changes. |
| 2 | `@fp-design-visionary` | Complete | §3 filled with ASCII mockups, motion spec, component tree, token-mapped contract. Pinned section label as "OR — ONE OF THESE?". |
| 3 | Claude Code (impl) | Complete | Backend + frontend + design docs committed in four logical units. Ruff clean, no new mypy errors, tsc clean. |
| 4 | `@test-writer` | Complete | 17 backend + 6 frontend tests, all passing first run. No implementation bugs discovered. |
| 5 | `@fp-design-auditor` | APPROVED w/ minor | One FAIL — section label source copy mixed-case (visually correct via CSS uppercase, but source inconsistent with DESIGN.md). Fixed in follow-up commit. |
| 6 | `@faang-staff-engineer` | CHANGES REQUIRED → APPROVED | S1 (primary CIP unvalidated) + M2 (non-string title passthrough) both landed with a parametrized test. M1/M3/M4/N1 tracked as §11 follow-ups. |
| 7 | `@fp-builder` | PASS | Lint clean, mypy delta zero, pytest 259 passed, vitest 388 passed (2 pre-existing unrelated), Vite build 1.60s, Ollama smoke confirmed `confidence=medium` on "business" end-to-end. |

---

## Verification

| Check | Result |
|-------|--------|
| `ruff check` | ✅ All checks passed (1 auto-fix during verification) |
| `mypy app/` | ✅ Zero new errors — 88 pre-existing errors confirmed identical to baseline |
| `pytest` (backend) | ✅ 259 passed, 17 of which are new |
| `npx tsc --noEmit` (frontend) | ✅ Clean (1 non-null assertion fix during verification) |
| `npx vitest run` (frontend) | ✅ 388 passed, 6 of which are new (2 pre-existing ProfileScreen failures confirmed unrelated) |
| `npx vite build` (frontend) | ✅ 657 modules, 1.60s |
| Ollama smoke (`INFERENCE_BACKEND=ollama`) | ✅ `resolve_intent("business", …)` → `confidence=medium`, 0 alternatives, all post-parse assertions passed. `localhost:11434` reachable, models available: `gemma4:e4b`, `gemma4:e2b`, `gemma4:26b` |
| OpenRouter smoke | ⏭️ Skipped per parallel-worktree discipline (sibling session may be using the key) |

---

## Tracked Follow-ups (§11)

Not blocking; each fits a small standalone spec or a bundled "intent-hardening" spec.

| # | Item | Size |
|---|------|------|
| F1 | Consolidate duplicate `_INTENT_SYSTEM_PROMPT` into shared module | ~1 hr |
| F2 | Promote `confidence` to `Literal["high","medium","low"]` with graceful fallback | ~30 min |
| F3 | Length caps on `IntentRequest.major_text` + alternative strings | ~15 min |
| F4 | Null `confirmTimerRef.current` after fire in `MatchContent` | ~5 min |
| F5 | `logger.warning` on intent fallback for observable truncation rate | ~5 min |
| F6 | Direct test for trailing-prose JSON stripping | ~10 min |

---

## Commits (spec branch)

```
48755bf feat(intent): address code review S1 + M2; design audit copy fix
40cfce9 test(tiered-matching): P0/P1 coverage for intent tiers + alternatives
e0b35ed spec(tiered-matching): log §6 implementation complete
5ddfc41 docs(brightpath): document medium-tier alternatives extension
9ab624f feat(major-input): tiered match card with inline alternatives
3131e56 feat(intent): tiered Gemma prompts + alternatives sanitization
e16c94f spec(tiered-matching): fp-design-visionary fills §3
9260454 spec(tiered-matching): log architecture reviews + amend §4
```

Plus `chore(verify):` commits from `@fp-builder` for the ruff + TypeScript fixes during verification.

**Branch is NOT merged, NOT pushed, and has no PR** per the parallel-worktree instructions. Sibling spec `docs/specs/screen-career-pick-lineage-sheet.md` is running concurrently; the orchestrating session integrates both branches to `main` after both complete.
