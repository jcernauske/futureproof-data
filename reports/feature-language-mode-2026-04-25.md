# Feature Report: Language Mode (Localized UI + Gemma Prose)

**Date:** 2026-04-25
**Spec:** `docs/specs/feature-language-mode.md`
**Branch:** `localization-support`
**Status:** COMPLETE

## Summary

Added English/Spanish language mode to FutureProof. Students select their language on the profile screen; the choice persists through session checkpoints, build creation, and all Gemma-generated prose. Deterministic UI chrome uses static dictionaries; Gemma prose is constrained via language instructions appended to system prompts.

## Architecture

- **Single locale type**: `AppLocale = Literal["en", "es"]` defined once in `backend/app/services/locale.py`, imported everywhere
- **Defensive normalizer**: `normalize_locale()` at every service entry point — strict equality, defaults to "en"
- **Prompt injection**: `gemma_language_instruction(locale)` appended to all Gemma system prompts
- **Canonical preservation**: School names, occupation titles, SOC/CIP codes, dollar amounts, JSON keys, and data source acronyms always stay in English
- **Spanish glossary**: 15 product-specific terms with canonical translations prevent Gemma from inventing inconsistent translations
- **Backward compatible**: All locale fields default to "en"; existing builds, sessions, and clients work unchanged

## Flow

```
Profile Screen (SegmentedControl) → Zustand store → Session checkpoint
    → API request body → Backend service → gemma_language_instruction(locale) → Gemma system prompt
    → Build model (locale persisted) → Downstream Gemma calls use build.locale
```

## Files Changed

- **9 files created** (locale service, i18n module, 5 test files)
- **28 files modified** (models, services, routers, frontend screens/hooks/API)
- **0 files deleted**

## Test Coverage

| Suite | New Tests | Total Passed |
|-------|-----------|-------------|
| Backend (pytest) | 49 | 1165 |
| Frontend (vitest) | 26 | 645 |
| **Total** | **75** | **1810** |

All 75 new tests pass. 6 pre-existing backend failures unrelated to this feature.

## Reviews

| Step | Agent | Verdict |
|------|-------|---------|
| Architecture | @fp-architect | APPROVED |
| GenAI Prompts | @genai-architect | APPROVED WITH RECOMMENDATIONS (all incorporated) |
| Design Vision | @fp-design-visionary | Refined §3 |
| Design Audit | @fp-design-auditor | 7 issues found, all fixed |
| Code Review | @faang-staff-engineer | 3 blocking + 2 moderate findings, all addressed |
| Verification | @fp-builder | ALL PASSED |

## Staff Engineer Findings Addressed

1. **Fallback strings wired through locale.py** — guidance, chat, boss, and next_steps fallbacks now use `fallback_text()` for locale-aware degraded service
2. **Sync `run_gauntlet` gained locale param** — CLI/script path now threads locale through to Gemma narratives
3. **`build_from_parts` typed as `AppLocale`** — was `str`, now uses proper Literal type + `normalize_locale()`
4. **AppLocale consolidated** — single definition in `locale.py`, imported by both `career.py` and `api.py`

## Design Audit Fixes

- SegmentedControl: `py-2.5` → `py-3` (44px tap target), `text-sm` → `text-small`, `text-xs` → `text-micro`
- ProfileScreen: `ambient-breathe 4s` → `6s`, `text-base` → `text-body`, state placeholder localized
- Added `profile.statePlaceholder` key to both locale dictionaries
