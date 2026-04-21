# Feature: Intent-Aware Tiering — Completion Report

**Spec:** `docs/specs/feature-intent-aware-tiering.md`
**Date:** 2026-04-20
**Status:** COMPLETE (pending 3 manual verification items requiring live Gemma)

---

## Summary

Plumbed `intent_keywords` and `student_major_text` from the Set Your Course resolver through to the `tier_careers` Gemma prompt. Career tiering now promotes intent-matching SOCs and demotes education-mismatched SOCs when the student's free-text input carries directional signal (e.g., "pre-med", "deaf ed", "I want to design video games").

This is Spec A of two. Spec B (`feature-soc-expansion-via-gemma-tools.md`) depends on the `intent_keywords` field shipped here.

## What Changed

### Backend
- **`IntentResult`** (`backend/app/models/career.py`): Added `student_major_text: str` and `intent_keywords: list[str]` with empty defaults for back-compat.
- **`TierRequest`** (`backend/app/models/api.py`): Added `student_major_text: str | None` and `intent_keywords: list[str]` with defaults.
- **Resolver prompt** (`backend/app/services/set_your_course.py`): Extended JSON tail with `intent_keywords` extraction rule + 5 worked examples. Added `_parse_intent_keywords()` defensive parser and `_merge_confirmed_focus_into_keywords()` utility.
- **Tiering prompt** (`backend/app/services/career_tiering.py`): Injects conditional `STUDENT INTENT` block + `INTENT MATCH RULES` (demote education mismatch, promote title match, never invent).
- **Router** (`backend/app/routers/builds.py`): Forwards intent fields to `tier_careers()`.
- **Chip flow** (`backend/app/services/set_your_course.py`): `_parse_updated_resolution` carries forward intent fields; `confirmed_focus` mirror auto-merges into `intent_keywords`.

### Frontend
- **`IntentResult` TS interface** + **`MajorSelection`** (`frontend/src/types/buildInput.ts`): Added optional intent fields.
- **`getTieredCareers`** (`frontend/src/api/build.ts`): Accepts and serializes intent fields.
- **`useSetYourCourse` hook**: Captures intent from `currentResolution`, passes to `getTieredCareers`, persists to `MajorSelection` on commit.
- **`CareerPickScreen`**: Forwards intent from `MajorSelection` to `getTieredCareers`.

## Architecture Reviews

| Reviewer | Verdict | Key Findings |
|----------|---------|--------------|
| @fp-architect | APPROVED | C1: Fixed file reference for chip-flow preservation. C2: Clarified `confirmed_focus` coupling location. |
| @genai-architect | CHANGES REQUESTED → incorporated | A: Extracted coupling utility. B: Fixed null-key back-compat. C-F: Prompt placement, demotion rule specificity, tokenization simplification. |

## Code Review

| Reviewer | Verdict | Key Findings |
|----------|---------|--------------|
| @faang-staff-engineer | APPROVED | M1: No-CIP-swap chip path doesn't merge confirmed_focus (non-blocking — initial keywords still present). m1: No input bounds on intent_keywords (low risk). m2: Raw text in prompt is standard LLM injection surface (output parser constrains blast radius). |

## Test Coverage

| Suite | Pass | Fail | Skip |
|-------|------|------|------|
| pytest (backend) | 1054 | 0 | 0 |
| vitest (frontend) | 588 | 0 | 1 (pre-existing) |

**New tests added:** 35 total (7 tiering prompt, 22 resolver/parser/chip-flow, 4 router, 2 frontend API).

## Build Verification

| Check | Result |
|-------|--------|
| ruff | PASS |
| mypy | PASS (45 pre-existing errors, 0 new) |
| pytest | PASS (1054) |
| tsc | PASS |
| vitest | PASS (588) |
| Vite build | PASS (687 modules) |

## Pending Manual Verification

These require a running Gemma instance and cannot be verified in CI:

1. "Biology + pre-med" → physician SOCs promoted, lab-tech SOCs demoted
2. "Illinois State + deaf ed" → "EXCEPT special education" SOCs land in STRETCH
3. Both `INFERENCE_BACKEND=ollama` and `openrouter` produce well-formed `intent_keywords`

## Follow-up

- **M1 from code review:** The no-CIP-swap chip path doesn't merge `confirmed_focus` into `intent_keywords`. Non-blocking because the resolver's initial keywords are still present, but should be fixed when Spec B touches the chip flow.
- **Spec B** (`feature-soc-expansion-via-gemma-tools.md`) can now proceed — it depends on the `intent_keywords` field shipped here.
