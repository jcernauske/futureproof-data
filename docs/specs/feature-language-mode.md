# Feature: Language Mode (Localized UI + Gemma Prose)

## Claude Code Prompt

```
Read the spec at docs/specs/feature-language-mode.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 for app architecture, API shape, session persistence, and blast radius.
   - Invoke @genai-architect to review all Gemma localization prompt contracts in §4 and write findings to §10.
   - If APPROVED: proceed to step 2.
   - If CHANGES REQUESTED (Significant): STOP, alert human.
   - If REJECTED (Blocker): STOP, alert human.

2. DESIGN VISION
   - Invoke @fp-design-visionary to refine §3 UI/UX Design before implementation.
   - §3 becomes the pixel-perfect target.

3. IMPLEMENTATION
   - Implement the spec as written in §3 and §4.
   - BEFORE coding: Review §4 Testing Impact Analysis thoroughly.
   - DURING coding: Update any broken tests listed in "Authorized Test Modifications".
   - CRITICAL: If any test NOT in the "Authorized Test Modifications" list fails, STOP and escalate to human.
   - Log all work to §6 Implementation Log.
   - Run backend and frontend checks listed in §9.

4. TESTING
   - Invoke @test-writer to review the full spec.
   - Implement all tests listed in "New Tests Required" by priority.
   - Backend tests: pytest in backend/tests/.
   - Frontend tests: vitest in frontend/src/**/*.test.ts(x).

5. DESIGN AUDIT
   - Invoke @design-builder for token/pattern compliance.
   - Design audit writes findings to §8.

6. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests.
   - If APPROVED: proceed to verification.
   - If CHANGES REQUIRED: route to originating agent via §10 Discussion.
   - If BLOCKER: STOP, alert human.

7. VERIFICATION
   - Invoke @fp-builder to run:
     - Backend: ruff check, mypy, pytest for impacted files
     - Frontend: TypeScript, vitest for impacted files, Vite build
   - Log results to §9.

8. COMPLETION
   - Update Status to COMPLETE.
   - Check off §1 Success Criteria.
   - Generate report to reports/feature-language-mode-YYYY-MM-DD.md.
```

---

## Status: DRAFT

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
| ARCH REVIEW | Awaiting architecture approval |
| DESIGN VISION | Design target being finalized |
| IMPLEMENTATION | Implementing |
| TESTING | Test coverage being added |
| DESIGN AUDIT | UI compliance review |
| CODE REVIEW | Staff review |
| VERIFICATION | Full build verification |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-25 |
| Author | Jeff + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-04-25 |
| Blocked By | — |
| Related Specs | `feature-set-your-course.md`, `feature-chat-guardrails.md`, `feature-save-build.md`, `submission-kaggle-narrative.md` |

---

## §1 Feature Description

### Overview

Add a student-selected Language Mode that localizes fixed UI chrome with deterministic strings and asks Gemma 4 to generate student-facing prose in the selected language while preserving canonical public-data values.

MVP scope supports English and Spanish:

- English: `en`
- Spanish: `es`

### Problem Statement

FutureProof is a career-decision tool for high-school students and families. The current experience assumes English. That weakens the Digital Equity & Inclusivity story for the Gemma 4 Good Hackathon and misses a high-impact use of Gemma 4's multilingual capabilities.

The product should let a student choose a language during profile/character setup, then keep the experience in that language for the rest of the main flow. The data must remain auditable and canonical: school names, program names, occupation titles, source names, dollar amounts, percentages, codes, and IDs are not translated ad hoc.

### Success Criteria

- [ ] Profile setup includes a language selector with English and Spanish.
- [ ] Selected locale persists in Zustand profile state and session checkpoint/resume.
- [ ] `locale` is included in build creation and stored on `Build`.
- [ ] Main-path static UI text can render from an `en`/`es` dictionary.
- [ ] Gemma prompts for initial resolution, chip dispatch, guidance, next steps, chat, career-pick Q&A, boss narratives, reroll commentary, skill pools, and skill recommendations include locale instructions.
- [ ] Structured JSON keys, IDs, school names, program names, occupation titles, source names, dollar amounts, percentages, and codes remain canonical.
- [ ] Spanish demo path works for: profile selection → Set Your Course → career pick → reveal/Gemma's Take → gauntlet/next steps → Ask Gemma.
- [ ] Fallback copy has Spanish coverage for the main demo path or explicitly falls back to English with no crash.
- [ ] Tests prove locale propagation and Gemma prompt localization without calling a live model.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Deterministic UI localization for fixed chrome | Buttons/headings/labels should be fast, stable, testable, and consistent | Ask Gemma to translate all UI strings at runtime; rejected as slower and less reliable |
| 2 | Gemma generates prose directly in the selected language | This showcases Gemma's multilingual capability where it matters: personalized, data-grounded explanation | Generate English then translate; rejected because it doubles latency and can lose grounding |
| 3 | Canonical database values are preserved | Public-data labels must remain auditable, searchable, and source-aligned | Translate BLS/O*NET/IPEDS values directly; rejected due ambiguity and provenance risk |
| 4 | Glossary constrains Gemma vocabulary | Prevents "AI exposure" or "human edge" from changing terms across surfaces | Fully handwrite all explanations; rejected because it minimizes Gemma's useful work |
| 5 | MVP supports `en` and `es` only | Spanish is high-value for U.S. education equity and feasible to QA | Support many languages immediately; rejected as test/design scope blow-up |
| 6 | Locale stored on profile and copied to build | Profile drives current session; build snapshot preserves historical output context | Store only globally in localStorage; rejected because saved builds need their own language context |
| 7 | JSON keys stay English | Existing Pydantic/TypeScript contracts stay stable | Localize API field names; rejected as unnecessary API churn |

### Constraints

- Do not translate canonical database values in-place.
- Do not introduce a full i18n framework unless the design review explicitly approves it. A tiny dictionary/hook is enough for MVP.
- Do not localize archived mockups or deprecated CLI spike.
- Do not add a new database table.
- No Iceberg schema changes.
- Backend defaults to `locale="en"` for backward compatibility.
- Spanish should be demo-quality on the main path, not necessarily exhaustive across every historical screen.

---

## §3 UI/UX Design

> This is a first-pass target. @fp-design-visionary must refine before implementation.

### Mockups

#### Profile Screen Language Selector

Add a compact segmented control below the generated character/name and above the home-state selector.

Desktop:

```text
┌────────────────────────────────────────────────────────────┐
│                    dancing happy bear                      │
│                         🐻                                │
│                                                            │
│  Language                                                 │
│  ┌───────────────┬───────────────┐                        │
│  │ English       │ Español       │                        │
│  └───────────────┴───────────────┘                        │
│                                                            │
│  Home state                                               │
│  [ Illinois  v ]                                          │
│                                                            │
│                                      [ Start your build ]  │
└────────────────────────────────────────────────────────────┘
```

Spanish selected:

```text
┌────────────────────────────────────────────────────────────┐
│                    dancing happy bear                      │
│                         🐻                                │
│                                                            │
│  Idioma                                                   │
│  ┌───────────────┬───────────────┐                        │
│  │ English       │ Español       │  ← selected             │
│  └───────────────┴───────────────┘                        │
│                                                            │
│  Estado de residencia                                     │
│  [ Illinois  v ]                                          │
│                                                            │
│                                      [ Empezar ]           │
└────────────────────────────────────────────────────────────┘
```

### Interactions

- Default locale is `en`.
- Selecting `Español` updates UI labels immediately.
- Locale persists through browser refresh via existing session checkpoint.
- Locale changes after a Gemma response do not retroactively rewrite prior generated text. New Gemma calls use the new locale.
- The demo path should choose locale on the profile screen before starting Set Your Course.

### Responsive Behavior

- Desktop: segmented control inline, max width aligned with other profile controls.
- Mobile: full-width two-segment control with 44px minimum tap target.
- Language choice must not cause layout shifts when labels lengthen in Spanish. Buttons should allow wrapping or use responsive width.

### Cozy Quest Design References

- Use existing button/segmented-control patterns if present.
- Use `font-body` for labels, `font-data` only for compact code/source chips.
- Do not add new decorative gradients or landing-page framing.
- Language selector is a utilitarian profile setting, not a hero element.

### Accessibility

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| Language selector group | `language-selector` | radiogroup / segmented control | `Choose language` / `Elegir idioma` |
| English option | `language-option-en` | radio/button | `Use English` |
| Spanish option | `language-option-es` | radio/button | `Usar español` |
| Start button | existing profile CTA id | button | localized visible label is sufficient |

---

## §4 Technical Specification

### Architecture Overview

Add a small locale layer shared by frontend state and backend prompt builders:

1. Frontend profile state stores `locale`.
2. Session checkpoint persists `locale` inside `profile_data`.
3. Build input/API sends `locale` to backend calls that can produce user-facing prose.
4. Backend request models default `locale` to `"en"`.
5. Gemma prompt helpers append a locale contract to system prompts.
6. Static UI strings come from deterministic dictionaries.

The split:

- UI chrome: deterministic dictionary.
- DB values: canonical.
- Gemma prose: generated in selected language with glossary constraints.

### Locale Types

#### Frontend

Create `frontend/src/i18n/locales.ts`:

```ts
export type AppLocale = "en" | "es";

export const DEFAULT_LOCALE: AppLocale = "en";

export function normalizeLocale(value: unknown): AppLocale {
  return value === "es" ? "es" : "en";
}
```

#### Backend

Create `backend/app/services/locale.py`:

```python
from __future__ import annotations

from typing import Literal

AppLocale = Literal["en", "es"]
DEFAULT_LOCALE: AppLocale = "en"

def normalize_locale(value: object) -> AppLocale:
    return "es" if value == "es" else "en"

def gemma_language_instruction(locale: AppLocale) -> str:
    ...
```

`gemma_language_instruction("en")` should be short and preserve existing behavior:

```text
Write student-facing prose in English.
Preserve official school names, program names, occupation titles, source names,
dollar amounts, percentages, codes, and JSON keys exactly.
```

`gemma_language_instruction("es")`:

```text
Write all student-facing prose in Spanish.
Use the glossary below for product concepts when they appear.
Preserve official school names, program names, occupation titles, source names,
dollar amounts, percentages, codes, and JSON keys exactly.
You may explain what an official English title means in Spanish after naming it,
but do not replace the canonical title.

Glossary:
- student debt = deuda estudiantil
- career paths = trayectorias profesionales
- job outlook = perspectiva laboral
- AI exposure = exposición a la IA
- human edge = ventaja humana
- data is estimated = los datos son estimados
- salary = salario
- median salary = salario medio
- student loan = préstamo estudiantil
- guidance counselor = consejero escolar
```

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/i18n/locales.ts` | Create | Locale type, default, normalizer |
| `frontend/src/i18n/strings.ts` | Create | `en`/`es` static string dictionary for main path |
| `frontend/src/i18n/useT.ts` | Create | Hook returning `t(key)` from profile locale |
| `frontend/src/store/profileStore.ts` | Modify | Add `locale`, `setLocale`, hydrate/clear behavior |
| `frontend/src/lib/checkpoint.ts` | Modify | Include `locale` in `profile_data` |
| `frontend/src/types/session.ts` | Modify | Include locale in session profile payload if typed there |
| `frontend/src/types/buildInput.ts` | Modify | Add locale to build input types where needed |
| `frontend/src/api/build.ts` | Modify | Send `locale` in build creation and prose-producing calls |
| `frontend/src/hooks/useSetYourCourse.ts` | Modify | Send `locale` in `/intent/stream` and chip dispatch payloads |
| `frontend/src/screens/ProfileScreen.tsx` | Modify | Add language selector UI |
| `frontend/src/screens/SetYourCourseScreen.tsx` | Modify | Localize main labels/loading/status text |
| `frontend/src/screens/CareerPickScreen.tsx` | Modify | Localize main labels/loading/status text |
| `frontend/src/screens/RevealScreen.tsx` | Modify | Localize main labels around Gemma's Take |
| `frontend/src/screens/GauntletScreen.tsx` | Modify | Localize main labels/status text on demo path |
| `frontend/src/components/gauntlet/NextSteps.tsx` | Modify | Localize loading/error/static labels |
| `frontend/src/components/menu/GemmaChat.tsx` | Modify | Send locale with chat request and localize chrome |
| `backend/app/services/locale.py` | Create | Locale normalizer and Gemma instruction helper |
| `backend/app/models/career.py` | Modify | Add locale fields to `Build` and related model(s) |
| `backend/app/models/api.py` | Modify | Add `locale: AppLocale = "en"` to relevant request models |
| `backend/app/services/set_your_course.py` | Modify | Accept locale and inject language instruction into streaming/chip prompts |
| `backend/app/services/guidance.py` | Modify | Add locale arg to guidance/chat prompt builders |
| `backend/app/services/boss_fights.py` | Modify | Add locale arg to narrative/reroll/wrapup generation |
| `backend/app/services/skill_recs.py` | Modify | Add locale arg to recommendation generation |
| `backend/app/services/skill_pool.py` | Modify | Add locale arg to skill-pool generation |
| `backend/app/services/next_steps.py` | Modify | Use `build.locale` in prompt |
| `backend/app/services/career_pick_qna.py` | Modify | Add locale to canned Q&A prompt |
| `backend/app/routers/builds.py` | Modify | Pass request/build locale into async Gemma fanout |
| `backend/app/routers/set_your_course.py` | Modify | Pass locale from request body |
| `backend/app/routers/guidance_router.py` | Modify | Pass build locale or request locale to chat/guidance |
| `backend/app/services/report_gen.py` | Modify | Preserve build locale in generated report metadata; no full report localization in MVP |

### Data Model Changes

No Iceberg schema changes.

Pydantic additions:

```python
from app.services.locale import AppLocale

class Build(BaseModel):
    ...
    locale: AppLocale = "en"
```

Add to request models:

```python
class IntentRequest(BaseModel):
    ...
    locale: AppLocale = "en"

class IntentStreamRequest(BaseModel):
    ...
    locale: AppLocale = "en"

class ChipRequest(BaseModel):
    ...
    locale: AppLocale = "en"

class BuildRequest(BaseModel):
    ...
    locale: AppLocale = "en"

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    locale: AppLocale | None = None
```

If importing `AppLocale` into `api.py` creates circular imports, keep the alias in `app.models.api` and mirror the `Literal["en", "es"]` type there.

DuckDB `builds` table stores full build JSON in the `data` column, so adding `Build.locale` requires no table migration. Existing builds hydrate with default `en`.

### Frontend Static Strings

Create a narrow dictionary for demo-path chrome. Example:

```ts
export const STRINGS = {
  en: {
    "profile.language": "Language",
    "profile.start": "Start your build",
    "school.gemmaThinking": "Gemma is thinking",
    "school.gemmaMatched": "Gemma matched",
    "careerPick.heading": "Choose a career path",
    "gauntlet.nextStepsLoading": "Gemma is writing your action plan...",
  },
  es: {
    "profile.language": "Idioma",
    "profile.start": "Empezar",
    "school.gemmaThinking": "Gemma está pensando",
    "school.gemmaMatched": "Gemma encontró una opción",
    "careerPick.heading": "Elige una trayectoria profesional",
    "gauntlet.nextStepsLoading": "Gemma está escribiendo tu plan de acción...",
  },
} as const;
```

Rules:

- Keep dictionary keys stable and English.
- Add only main-path strings for MVP.
- Do not translate official DB values through this dictionary.

### Backend Prompt Changes

Every Gemma system prompt producing student-facing prose must include:

```python
from app.services.locale import gemma_language_instruction, normalize_locale

system = f"{_SYSTEM}\n\n{gemma_language_instruction(locale)}"
```

For prompts that produce mixed prose + JSON:

- Prose must follow locale.
- JSON keys must stay English.
- JSON enum values stay English unless the existing parser explicitly accepts localized values.
- Student-facing JSON values like `reasoning`, `rationale`, `message`, and `debug_trace` may be in Spanish.

High-priority prompt surfaces:

1. `set_your_course.stream_initial_resolution`
2. `set_your_course.handle_chip_dispatch`
3. `guidance.generate_guidance(_async)`
4. `guidance.chat_with_context`
5. `next_steps.generate_next_steps`
6. `boss_fights.narrate_one`, `generate_reroll_commentary(_async)`, `generate_wrapup_async`
7. `skill_recs.generate_recs(_async)`
8. `skill_pool.generate_pool(_async)`
9. `career_pick_qna.answer_question`

Medium priority:

- `intent.resolve_intent` old non-streaming path. Keep backward-compatible default `en`; accept locale if route passes it.
- `career_tiering.tier_careers`: structured tier headers must remain English (`COMMON`, `LESS_COMMON`, `STRETCH`) because the parser expects them. UI can translate display labels later.

Do not localize:

- `soc_expansion.py` tool call outputs. It returns SOC codes/rationale for internal expansion, not direct student prose.
- `scripts/gemma_ai_exposure_scorer.py`. Batch data scoring should stay English/canonical.

### API Plumbing

`POST /intent/stream`:

```json
{
  "major_text": "quiero ser doctor",
  "school_name": "Indiana University Bloomington",
  "unitid": 151351,
  "programs": [],
  "locale": "es"
}
```

`POST /set-your-course/chip` / existing chip route:

```json
{
  "...": "...",
  "locale": "es"
}
```

`POST /build`:

```json
{
  "...": "...",
  "locale": "es"
}
```

Chat:

- Prefer build locale if the request omits locale.
- If request includes locale, normalize and use it for that turn.

### Fallback Copy

Add localized fallback helpers where the main path can show fallback text:

```python
def fallback_text(key: str, locale: AppLocale) -> str:
    ...
```

Minimum backend fallback keys:

- `gemma_unreachable`
- `guidance_unavailable`
- `next_steps_unavailable`
- `boss_unknown_ai`
- `boss_unknown_loans`
- `chat_unavailable`

If a fallback key is missing in Spanish, return English rather than failing.

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `frontend/src/App.test.tsx` | profile/session resume tests | Medium | Profile store gains `locale` |
| `frontend/src/store/*` tests if present | store hydration tests | Medium | New state field |
| `frontend/src/hooks/useSetYourCourse.test.ts` | streaming/chip payload tests | High | `/intent/stream` and chip payloads gain locale |
| `frontend/src/screens/ProfileScreen` tests if present | auto-profile/reroll tests | Medium | New selector on screen |
| `frontend/src/screens/CareerPickScreen.test.tsx` | loading/chrome expectations | Low | Some visible strings may localize |
| `frontend/src/components/gauntlet/NextSteps.test.tsx` | loading/error text | Medium | Localized static strings |
| `backend/tests/services/test_set_your_course.py` | streaming and chip prompt tests | High | Prompt now includes locale instruction |
| `backend/tests/services/test_guidance.py` | Gemma prompt/fallback tests | High | Function signatures gain locale |
| `backend/tests/services/test_boss_fights.py` | narrative generation tests | Medium | Function signatures gain locale |
| `backend/tests/services/test_skill_recs.py` | rec prompt tests | Medium | Function signatures gain locale |
| `backend/tests/services/test_career_pick_qna.py` | prompt/call metadata tests | Medium | Locale in prompt/log extra |
| `backend/tests/routers/test_set_your_course_router.py` if present | request model tests | Medium | Request accepts optional locale |
| `backend/tests/services/test_builds.py` | build serialization tests | Medium | Build includes locale |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| Prompt snapshot/assertion tests | Add assertions for locale instruction and canonical preservation text | Expected prompt contract change |
| Store/session tests | Include `locale: "en"` default and `"es"` hydration | New persisted field |
| Router payload tests | Include optional locale or assert default `en` | New request fields |
| Visible UI text tests | Use dictionary values or set locale explicitly | Static chrome now locale-aware |

#### Confirmed Safe

These should not change behavior and should not fail because of this feature:

- `tests/silver/*`
- `tests/gold/*`
- `tests/mcp/*`
- `backend/tests/services/test_soc_expansion.py`
- `tests/silver/test_gemma_ai_exposure_transformer.py`
- `backend/tests/services/test_gemma_client.py`

If any confirmed-safe test fails, stop and escalate.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/services/test_locale.py` | `test_gemma_language_instruction_spanish_preserves_canonical_values` | Spanish instruction includes glossary and preservation rules |
| P0 | `backend/tests/services/test_set_your_course.py` | `test_stream_initial_resolution_includes_spanish_locale_instruction` | Streaming prompt asks Gemma for Spanish prose and English JSON keys |
| P0 | `backend/tests/services/test_guidance.py` | `test_generate_guidance_passes_spanish_instruction` | Gemma's Take prompt localizes prose |
| P0 | `backend/tests/services/test_next_steps.py` | `test_next_steps_uses_build_locale` | Next Steps prompt uses `build.locale` |
| P0 | `backend/tests/routers/test_builds_collection.py` or relevant build test | `test_create_build_persists_locale` | Build serialization/hydration defaults and Spanish persistence |
| P0 | `frontend/src/store/profileStore.test.ts` | `persists_and_hydrates_locale` | Store defaults to `en`, accepts `es`, clears/hydrates |
| P0 | `frontend/src/lib/checkpoint.test.ts` | `checkpoint_includes_profile_locale` | Session persistence includes locale |
| P0 | `frontend/src/hooks/useSetYourCourse.test.ts` | `intent_stream_payload_includes_locale` | Frontend sends selected locale |
| P1 | `frontend/src/screens/ProfileScreen.test.tsx` | `language_selector_updates_profile_locale` | UI selector changes locale and labels |
| P1 | `frontend/src/i18n/useT.test.ts` | `falls_back_to_english_for_missing_key` | Dictionary safety |
| P1 | `backend/tests/services/test_career_pick_qna.py` | `spanish_locale_added_to_qna_prompt` | Ask-Gemma chip answers localize |
| P1 | `backend/tests/services/test_boss_fights.py` | `narrate_one_accepts_locale` | Boss narrative prompt localizes |

#### Test Data Requirements

- No live Gemma calls.
- Monkeypatch `gemma_client.generate*` functions and inspect `system` prompt inputs.
- Frontend tests should set `useProfileStore.setState({ locale: "es" })` before rendering localized surfaces.

---

## §5 Architecture Review

### @fp-architect Review

**Status:** PENDING

#### Findings

[Filled in by @fp-architect]

#### Verdict

- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

### @fp-data-reviewer Review

**Status:** SKIPPED

No pipeline, Iceberg, stat formula, or data-source transformation changes. Canonical database values are explicitly preserved.

---

## §6 Implementation Log

**Status:** PENDING

### Files Modified

| File | Change Summary |
|------|---------------|
| | |

### Deviations from Spec

[Any divergence from §3/§4 and why]

### Build Accountability Log

| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| | | | |

---

## §7 Test Coverage

**Status:** PENDING

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|
| | | |

### Test Results

| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest | | | | |
| vitest | | | | |

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@design-builder)

[Pending]

### Code Review (@faang-staff-engineer)

[Pending]

---

## §9 Verification

**Status:** PENDING

Required commands:

```bash
uv run pytest backend/tests/services/test_locale.py \
  backend/tests/services/test_set_your_course.py \
  backend/tests/services/test_guidance.py \
  backend/tests/services/test_next_steps.py \
  backend/tests/services/test_boss_fights.py \
  backend/tests/services/test_skill_recs.py \
  backend/tests/services/test_career_pick_qna.py

cd frontend && npm run typecheck
cd frontend && npx vitest run \
  src/store/profileStore.test.ts \
  src/hooks/useSetYourCourse.test.ts \
  src/screens/ProfileScreen.test.tsx \
  src/components/gauntlet/NextSteps.test.tsx
cd frontend && npm run build
```

Full verification should also run the repo's normal backend/frontend test suites if time allows.

---

## §10 GenAI Review / Discussion

### @genai-architect Review

**Status:** PENDING

Review focus:

- Prompt wording for Spanish output while preserving canonical facts.
- Whether JSON/prose mixed outputs are sufficiently constrained.
- Whether glossary coverage is enough for the demo path.
- Whether any internal-only Gemma calls should remain English.

### Open Questions

| Date | Question | Owner | Resolution |
|------|----------|-------|------------|
| 2026-04-25 | Should official source names like "Bureau of Labor Statistics" remain English in Spanish prose, or allow first-use Spanish explanation in parentheses? | Jeff | Pending |
| 2026-04-25 | Should occupation titles get Spanish explanatory glosses in the UI, or only inside Gemma prose? | Jeff | Pending |

---

## §11 Hackathon Demo Notes

Recommended video beat:

1. Profile screen: select `Español`.
2. Type `quiero ser doctor`.
3. Gemma streams Spanish reasoning but preserves canonical program/source values.
4. Show career data as the same canonical public data.
5. Show Gemma's Take and Next Steps in Spanish.
6. Emphasize that schools can run the same localized experience locally through Ollama.

Submission language:

> FutureProof uses deterministic localization for interface chrome, then uses Gemma 4 for the higher-value multilingual task: adapting complex, data-grounded career guidance into the student's selected language while preserving official public-data labels and every numeric receipt.

Non-goals for hackathon:

- Full many-language localization.
- Freeform runtime translation of every UI string.
- Translating canonical database values in-place.
- Multimodal school-logo recognition.
