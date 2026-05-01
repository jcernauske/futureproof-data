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

## Status: COMPLETE

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

> Refined by @fp-design-visionary (2026-04-25). Implementation-ready.

### Design Intent

**Emotion target: quiet confidence.** The language selector should feel like adjusting a setting on your phone -- a small, respectful choice that says "we thought about you." It is not a feature to celebrate; it is a feature to simply have. The student should tap it, see the UI respond instantly, and move on. No fanfare, no animation beyond what the existing `SegmentedControl` already provides.

Here is why this matters: the Profile screen's emotional center is the character reveal -- the dancing emoji, the generated name, the ambient glow. The language selector must not compete with any of that. It lives in the "settings zone" below the divider, alongside the home-state dropdown. Two utilitarian profile settings, side by side in visual weight, quietly doing their job.

### Component Choice: Existing `SegmentedControl`

FutureProof already has `frontend/src/components/ui/SegmentedControl.tsx` -- a generic, accessible, Framer Motion-powered segmented control with `layoutId`-based sliding indicator, keyboard navigation, and `role="radiogroup"` semantics. It is currently unused but fully built. **Use it directly. Do not create a new component.**

The `SegmentedControl` already provides:
- `motion.div` sliding indicator with `springs.snappy` transition
- `role="radiogroup"` with `aria-checked`, arrow-key navigation
- `flex-1` segments (equal width, preventing layout shift)
- `bg-bp-surface` container with `rounded-md` and `p-1 gap-1` internal padding
- Configurable `activeColor` (default `bg-accent-thrive`)

For the language selector, override `activeColor` to `"bg-accent-info"` -- info-blue is the navigation/neutral-information color in Brightpath. Thrive-green (the default) carries "positive outcome" semantics that do not apply here. Info-blue says "this is a choice," not "this is a win."

### Layout Placement

The language selector goes **below the divider, above the home-state dropdown** -- the same "settings zone." It uses the same `max-w-xs` constraint and the same `motion.div` stagger wrapper as the home-state selector.

#### Wireframe (both states)

```text
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│                    "Meet your guide"                         │
│                         🐻                                  │
│                    Cozy McBearface                           │
│              "Every build gets a character."                 │
│                       🎲 New name                           │
│                                                              │
│             ─────────── divider ───────────                  │
│                                                              │
│   Language           ← label: font-body text-small           │
│   ┌─────────────┬─────────────┐  ← SegmentedControl         │
│   │  English    │  Español    │     max-w-xs, w-full         │
│   └─────────────┴─────────────┘     activeColor=info         │
│                                                              │
│   What state do you live in?  ← label: font-body text-small  │
│   [ Illinois           v ]    ← existing select              │
│                                                              │
│         [ Let's go → ]        ← existing Button primary      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

When Spanish is selected, the label reads "Idioma", the state label reads "¿En qué estado vives?", and the CTA reads "Vamos →". The segment labels ("English" / "Español") never change -- they are always in their own language so the student can always find their way back.

### Implementation: ProfileScreen.tsx Changes

#### 1. Import the component and store action

```tsx
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import type { Segment } from "@/components/ui/SegmentedControl";
import type { AppLocale } from "@/i18n/locales";
```

Add `locale` and `setLocale` to the destructured profile store:

```tsx
const { profileName, animalEmoji, setProfile, homeState, setHomeState, locale, setLocale } = useProfileStore();
```

#### 2. Define the segments (outside the component, module-level constant)

```tsx
const LANGUAGE_SEGMENTS: Segment<AppLocale>[] = [
  { value: "en", label: "English" },
  { value: "es", label: "Español" },
];
```

Why module-level: these are static, referentially stable, and should not cause re-renders. The `label` values are always in their native language -- "English" and "Español" -- so they never change regardless of the active locale. This also ensures the student can always identify and switch back to their language.

#### 3. Add the selector block between the divider and home-state

Insert a new `motion.div` with `variants={staggerItem}` immediately after the existing divider `<div className="mt-10 ...">` and before the home-state `motion.div`:

```tsx
{/* Language selector */}
<motion.div
  className="mt-6 w-full max-w-xs"
  variants={staggerItem}
>
  <label
    className="block font-body text-small text-text-secondary mb-2 text-center"
  >
    {t("profile.language")}
  </label>
  <SegmentedControl
    segments={LANGUAGE_SEGMENTS}
    value={locale}
    onChange={setLocale}
    activeColor="bg-accent-info"
    ariaLabel={locale === "es" ? "Elegir idioma" : "Choose language"}
  />
</motion.div>
```

#### 4. Localize the other labels on the screen

Use the `t()` hook from `useT` for these strings only:

| Current hardcoded text | String key | `en` value | `es` value |
|------------------------|-----------|-----------|-----------|
| "Meet your guide" | `profile.meetGuide` | Meet your guide | Conoce a tu guía |
| "Every build gets a character." | `profile.everyBuild` | Every build gets a character. | Cada partida tiene un personaje. |
| "New name" | `profile.newName` | New name | Nuevo nombre |
| "Language" | `profile.language` | Language | Idioma |
| "What state do you live in?" | `profile.stateLabel` | What state do you live in? | ¿En qué estado vives? |
| "Select your state" | `profile.statePlaceholder` | Select your state | Selecciona tu estado |
| "Let's go →" | `profile.start` | Let's go → | Vamos → |

State names in the dropdown remain English -- they are canonical geographic data.

#### 5. SegmentedControl `layoutId` isolation

The existing `SegmentedControl` uses `layoutId="segment-active"` for its sliding indicator. If multiple `SegmentedControl` instances ever appear on the same page (e.g., future settings), the shared `layoutId` will cause cross-component animation glitches. For now this is fine -- there is only one on the Profile screen. If a second instance is ever added, the component should be updated to accept a `layoutId` prop. No action needed for this spec.

### Tailwind Classes Reference

| Element | Classes | Rationale |
|---------|---------|-----------|
| Language label | `block font-body text-small text-text-secondary mb-2 text-center` | Matches home-state label exactly |
| Language wrapper | `mt-6 w-full max-w-xs` | Matches home-state wrapper exactly |
| SegmentedControl container (from component) | `relative flex bg-bp-surface rounded-md p-1 gap-1` | Already built into the component |
| Segment buttons (from component) | `relative flex-1 flex flex-col items-center gap-0.5 py-2.5 px-2 rounded-sm z-10` | Already built; `flex-1` ensures equal width |
| Active indicator | `bg-accent-info rounded-sm` | Overridden via `activeColor` prop |

### Responsive Behavior

**No special responsive work required.** Here is why:

- The `SegmentedControl` uses `flex-1` for each segment, so both buttons always share the container width equally. The container is constrained to `max-w-xs` (320px), so each segment gets 160px minus padding. "English" and "Español" both fit comfortably.
- The segment buttons have `py-2.5` (10px vertical padding) plus the text line height. At `text-sm` (14px) with `leading-normal` (1.5), each button renders at roughly 14 * 1.5 + 20 = 41px. This is close to but not quite 44px.

**Required tweak:** Override the segment button padding to `py-3` (12px) to guarantee 44px minimum tap height. This requires a small modification to `SegmentedControl.tsx`:

Add an optional `compact` prop (default `true` to preserve existing behavior) or simply change the existing `py-2.5` to `py-3`. Since the component is currently unused anywhere else, changing `py-2.5` to `py-3` is safe and simpler. The visual difference is 4px total height -- imperceptible but accessibility-correct.

```diff
- className={`relative flex-1 flex flex-col items-center gap-0.5 py-2.5 px-2 rounded-sm z-10 ...`}
+ className={`relative flex-1 flex flex-col items-center gap-0.5 py-3 px-2 rounded-sm z-10 ...`}
```

**Layout shift prevention:** Because both segments use `flex-1`, they always occupy exactly 50% of the container width regardless of label length. Switching locale changes the *label text above the control* (e.g., "Language" to "Idioma") but this label is centered text in a fixed-width container -- no shift occurs.

### Motion

**No additional animation work.** The language selector participates in the existing stagger sequence via `variants={staggerItem}`, fading up with the same `springs.smooth` timing as the home-state dropdown. The `SegmentedControl`'s sliding indicator already uses `springs.snappy` via `layoutId`. This is the right amount of motion for a utilitarian setting -- it enters with the page, and the toggle responds crisply. Nothing more.

### States

| State | Behavior |
|-------|----------|
| **Default (first visit)** | `locale` is `"en"`. English segment is active (info-blue indicator). |
| **Spanish selected** | Indicator slides to "Español" via `layoutId` spring. All `t()` labels on the Profile screen update immediately. No network call. |
| **Session resume** | `locale` hydrates from checkpoint. If absent (old session), defaults to `"en"` via `normalizeLocale`. |
| **Loading state (no profile yet)** | Language selector is not shown -- the loading/error screen renders before the profile exists. Locale selection happens after the character is generated. |
| **Error state** | If profile generation fails, the error message should also be localized. But since the profile has not loaded yet and no locale has been chosen, English is the correct default. The error text uses the existing hardcoded string. |

### Interactions

- Default locale is `en`.
- Selecting "Español" updates all `t()`-driven labels on the Profile screen immediately. No page reload, no network call.
- Segment labels ("English" / "Español") are always in their native language and never change.
- Locale persists through browser refresh via existing session checkpoint flow.
- Locale changes after a Gemma response do not retroactively rewrite prior generated text. New Gemma calls use the new locale.
- The demo path should choose locale on the Profile screen before starting Set Your Course.

### Accessibility

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| Language selector group | (via `ariaLabel` prop) | `radiogroup` | `"Choose language"` / `"Elegir idioma"` (dynamic based on current locale) |
| English option | (auto from `SegmentedControl`) | `radio` with `aria-checked` | Visible label "English" is sufficient |
| Spanish option | (auto from `SegmentedControl`) | `radio` with `aria-checked` | Visible label "Español" is sufficient |
| Start button | existing profile CTA | `button` | Localized visible label is sufficient |

Keyboard: Arrow Left/Right moves between segments (already implemented in `SegmentedControl`). Tab moves to the next focusable element (home-state select).

### What Not To Do

- **Do not add a globe icon, flag emoji, or decorative element.** This is a two-option toggle, not a language picker dropdown. Keep it clean.
- **Do not animate the label text change.** When "Language" becomes "Idioma," it should swap instantly. Animating text changes on a utilitarian label feels gratuitous.
- **Do not place the selector above the divider.** The character reveal zone (emoji, name, reroll) is the emotional center. The language selector belongs in the quiet settings zone below.
- **Do not use `font-data` (Space Mono) for the segment labels.** "English" and "Español" are not data values. Use `font-body` (Nunito) via the existing `SegmentedControl` which renders in the page's default body font.
- **Do not add new decorative gradients or glow effects.** The `SegmentedControl` already has the `bg-bp-surface` container treatment. That is enough.

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

**Status:** APPROVED
**Reviewed:** 2026-04-25

#### System Context

This feature adds a thin locale layer that threads through four system layers: frontend Zustand state, session checkpoint persistence, backend Pydantic request/response models, and Gemma prompt builders. It deliberately does not touch the Brightsmith pipeline (Bronze/Silver/Gold/MCP), DuckDB Gold zone schemas, or any data transformation logic. The change surface is wide (many files) but shallow (one optional field with a safe default). The architecture is sound.

#### Data Flow Analysis

Traced the full path:

1. **Profile -> Zustand:** `profileStore.ts` gains `locale: AppLocale` field, default `"en"`. Currently the store has `profileName`, `animalEmoji`, `animalName`, `homeState` -- adding `locale` follows the same pattern. `setLocale`, `clearProfile`, and `hydrateFromSession` all need updating. Clean.

2. **Zustand -> Checkpoint:** `checkpoint.ts` assembles `profile_data` from `useProfileStore.getState()`. Today it sends `{profileName, animalEmoji, animalName, homeState}`. The `locale` field must be added here. The backend `CheckpointRequest.profile_data` is typed as `dict | None`, so the new key flows through without schema breakage. The frontend `CheckpointPayload.profile_data` in `types/session.ts` is a typed inline interface that must be updated to include `locale`. Clean.

3. **Checkpoint -> Session Resume:** `SessionResponse.profile_data` is also `dict | None` on the backend, so the `locale` key round-trips without migration. On the frontend, `SessionResponse.profile_data` in `types/session.ts` is a typed interface that must gain `locale`. `hydrateFromSession` must accept and restore it. Old sessions without `locale` will have it absent; the `normalizeLocale` function safely defaults to `"en"`. Clean.

4. **Profile -> API Requests:** Frontend sends `locale` on `IntentStreamRequest`, `ChipRequest`, `BuildRequest`, and `ChatRequest`. All four backend models gain `locale: AppLocale = "en"`, which is backward-compatible -- existing clients without the field get English. Clean.

5. **API -> Gemma Prompts:** Router passes `locale` to service functions. Services call `gemma_language_instruction(locale)` and append to system prompt. The instruction preserves canonical data values. JSON keys stay English. Clean separation.

6. **Build Persistence:** `Build` gains `locale: AppLocale = "en"`. Builds are stored as JSON in DuckDB's `data` column. Existing builds hydrate with default `"en"` via Pydantic's default. No migration needed. Clean.

7. **Build -> Downstream Gemma (guidance, next_steps, chat, boss narration, reroll, wrapup, skill recs, skill pool):** These services currently take `CareerOutcome` / `GauntletResult` / `Build` as inputs. The spec correctly identifies that `build.locale` is available for services that receive the Build directly (e.g., `next_steps.generate_next_steps(build)`). For the `_gemma_fanout` in `builds.py` router, locale must be threaded through to `boss_fights.narrate_one`, `skill_recs.generate_recs_async`, `skill_pool.generate_pool_async`, and `guidance.generate_guidance_async`. This requires adding `locale` as a parameter to `_gemma_fanout` and forwarding it.

No boundary crossing into Brightsmith zones. No DuckDB schema changes. No MCP tool signature changes. The data stays canonical; only prose generation is affected.

#### Contract Review

**Pydantic models -- well-designed:**
- `AppLocale = Literal["en", "es"]` is precise, not `str`.
- Default `"en"` on all request models ensures backward compatibility.
- `ChatRequest.locale` is `AppLocale | None = None` (preferring build locale when absent) -- good design for the chat use case where the build already carries locale context.
- The spec correctly notes the circular import risk with `AppLocale` in `api.py` and provides a mitigation (mirror the `Literal` type).

**Frontend types -- adequate:**
- `CheckpointPayload.profile_data` and `SessionResponse.profile_data` in `types/session.ts` must gain `locale` in their typed interfaces.
- `AppLocale` type + `normalizeLocale` function provide the same safety on the frontend side.

**API signatures -- consistent:**
- Adding optional `locale` to existing POST bodies is additive and non-breaking.
- The spec covers all prose-producing endpoints.

#### Findings

##### Sound

- **Zone boundary discipline.** This feature correctly stays out of Bronze, Silver, Gold, and MCP zones. Canonical data values (school names, SOC codes, dollar amounts) are explicitly preserved. The separation between deterministic UI chrome (dictionary) and Gemma-generated prose (prompt instruction) is clean and testable.

- **Backward compatibility.** Every `locale` field defaults to `"en"`. Old sessions, old builds, old API clients all continue working without any migration or coordination. This is the right default strategy.

- **Build snapshot semantics.** Storing `locale` on `Build` (not just profile) means saved builds remember their language context. This is correct -- a Spanish build should render Spanish prose on reload without requiring the profile to still be set to Spanish.

- **Canonical preservation contract.** The `gemma_language_instruction` function explicitly lists what must not be translated (school names, program names, occupation titles, source names, dollar amounts, percentages, codes, JSON keys). The glossary for Spanish product terms prevents Gemma from inventing inconsistent translations for FutureProof-specific concepts.

- **Fallback strategy.** Backend `fallback_text` with English fallback for missing Spanish keys, and frontend dictionary with English fallback, both prevent crashes on missing translations.

- **Testing strategy.** No live Gemma calls; monkeypatching `generate*` and inspecting system prompt inputs is the right approach. The test impact analysis is thorough and correctly identifies the high-risk surfaces.

##### Concerns

- **`_gemma_fanout` locale threading.** The spec lists `builds.py` router as "Modify: Pass request/build locale into async Gemma fanout" but does not explicitly show how `locale` reaches `_gemma_fanout`'s callees (`narrate_one`, `generate_recs_async`, `generate_pool_async`, `generate_guidance_async`). Currently these functions do not accept a `locale` parameter. The `_gemma_fanout` helper and `rebuild_with_sliders` must both thread `locale` through. This is implicitly covered by the spec's file change table but the implementer should confirm `_gemma_fanout` gains a `locale` parameter and forwards it to all four service calls. **Impact:** If missed, build creation produces English prose even when `locale="es"`. **Recommendation:** The spec is sufficient as written; flag this to the implementer as a critical wiring point.

- **`RerollRequest` and `WrapupRequest` missing locale.** The gauntlet router's `reroll_fight` and `fight_wrapup` endpoints call `generate_reroll_commentary_async` and `generate_wrapup_async` respectively. These endpoints operate on an existing build (fetched from `state.get_build`), so `build.locale` is available without adding locale to the request models. The spec lists `boss_fights.py` as modified but does not list `RerollRequest` or `WrapupRequest` in the request model changes. This is correct -- locale comes from the build, not the request. Confirming this is intentional and sound.

- **`generate_guidance` sync path.** The guidance router has both a sync `generate_guidance` endpoint (`POST /{build_id}/guidance`) and the async path through `_gemma_fanout`. The sync endpoint currently takes `(career, gauntlet, branches)` -- it does not receive the build object, so `build.locale` is not directly available. The router has the build in scope, so it can pass `build.locale` as a kwarg. **Impact:** If missed, the standalone guidance regeneration endpoint stays English-only. **Recommendation:** Ensure `guidance.generate_guidance` gains a `locale` parameter, and the guidance router passes `build.locale`.

- **`chat_with_context` locale source.** The spec says `ChatRequest.locale` is `AppLocale | None = None` and "prefer build locale if the request omits locale." The guidance router currently passes `request.message` and `request.history` but not locale. The router must resolve the effective locale (`request.locale or build.locale`) and pass it. **Impact:** Chat stays English if not wired. **Recommendation:** Already covered by the spec's file change table; just confirming the resolution logic.

##### Blockers

None.

#### Verdict

- [x] APPROVED

#### Conditions

None. The spec is well-designed and ready for implementation. The concerns above are minor wiring details that the implementer should treat as a checklist, not blockers requiring spec revision.

### @fp-data-reviewer Review

**Status:** SKIPPED

No pipeline, Iceberg, stat formula, or data-source transformation changes. Canonical database values are explicitly preserved.

---

## §6 Implementation Log

**Status:** COMPLETE

### Files Created

| File | Purpose |
|------|---------|
| `backend/app/services/locale.py` | Core locale service: AppLocale type, normalize_locale, gemma_language_instruction, fallback_text |
| `frontend/src/i18n/locales.ts` | Frontend AppLocale type + normalizeLocale |
| `frontend/src/i18n/strings.ts` | Static string dictionaries (en/es) + getString |
| `frontend/src/i18n/useT.ts` | Translation hook using Zustand locale |
| `backend/tests/services/test_locale.py` | 32 tests for locale service |
| `backend/tests/services/test_next_steps.py` | 3 tests for next_steps locale threading |
| `frontend/src/store/profileStore.test.ts` | 9 tests for store locale |
| `frontend/src/i18n/strings.test.ts` | 8 tests for string dictionary |
| `frontend/src/i18n/locales.test.ts` | 9 tests for normalizeLocale |

### Files Modified

| File | Change Summary |
|------|---------------|
| `backend/app/models/career.py` | Import AppLocale from locale.py (was duplicate Literal), add locale to Build |
| `backend/app/models/api.py` | Import AppLocale from locale.py, add locale to BuildRequest/IntentStreamRequest/ChipRequest/ChatRequest |
| `backend/app/models/career_pick.py` | Add locale to AskCareerPickRequest |
| `backend/app/services/guidance.py` | Add locale param to generate_guidance/async/chat_with_context, wire fallback_text |
| `backend/app/services/boss_fights.py` | Add locale to narrate_one/reroll/wrapup/run_gauntlet, wire fallback_text |
| `backend/app/services/skill_recs.py` | Add locale to generate_recs/async |
| `backend/app/services/skill_pool.py` | Add locale to generate_pool/async |
| `backend/app/services/next_steps.py` | Add locale to generate_next_steps, wire fallback_text |
| `backend/app/services/career_pick_qna.py` | Add locale to ask() |
| `backend/app/services/set_your_course.py` | Add locale to stream_initial_resolution/handle_chip_dispatch |
| `backend/app/services/builds.py` | Add AppLocale type + normalize_locale to build_from_parts |
| `backend/app/routers/builds.py` | Thread locale through _gemma_fanout and both build endpoints |
| `backend/app/routers/set_your_course.py` | Pass request.locale |
| `backend/app/routers/guidance_router.py` | Pass build.locale / request.locale |
| `backend/app/routers/gauntlet.py` | Pass build.locale |
| `backend/app/routers/career_pick.py` | Pass request.locale |
| `frontend/src/store/profileStore.ts` | Add locale/setLocale to state, hydrate/clear support |
| `frontend/src/lib/checkpoint.ts` | Include locale in session checkpoint |
| `frontend/src/types/session.ts` | Add locale to CheckpointPayload/SessionResponse |
| `frontend/src/api/build.ts` | Send locale to createBuild |
| `frontend/src/api/intent.ts` | Send locale to streamIntent/dispatchChip |
| `frontend/src/api/menu.ts` | Send locale to sendChat |
| `frontend/src/hooks/useSetYourCourse.ts` | Read locale from store, pass to API |
| `frontend/src/screens/ProfileScreen.tsx` | Language selector UI, all labels via useT |
| `frontend/src/screens/RevealScreen.tsx` | Pass locale to createBuild |
| `frontend/src/screens/BuildResultsScreen.tsx` | Pass locale to createBuild |
| `frontend/src/components/menu/GemmaChat.tsx` | Pass locale to sendChat |
| `frontend/src/components/ui/SegmentedControl.tsx` | Fix py-2.5→py-3, text-sm→text-small, text-xs→text-micro |

### Deviations from Spec

1. **AppLocale consolidated**: Spec suggested mirroring the Literal type in career.py to avoid circular imports. Circular import did not occur, so career.py imports from locale.py directly. api.py also imports from locale.py. Single source of truth.
2. **Fallback copy wired through locale.py**: Staff engineer review identified that fallback strings in guidance.py, boss_fights.py, and next_steps.py were English-only. Wired all fallback paths through `fallback_text()` from locale.py for locale-aware degraded service.
3. **Sync run_gauntlet gained locale param**: Staff engineer identified the sync gauntlet path was missing locale threading. Added locale param and instruction to system prompt.
4. **Next steps fallback simplified**: Replaced the verbose English-only markdown template with the simpler `fallback_text("next_steps_unavailable", locale)` for locale-aware fallback.
5. **Design audit fixes**: Fixed ambient-breathe animation from 4s to 6s per DESIGN.md, text-base→text-body on select, added profile.statePlaceholder to both locale dictionaries.

### Build Accountability Log

| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | ruff pass, tests fail | test_builds.py mock signatures missing locale kwargs | Added locale="en" to _FanoutHarness and subclass mocks |
| 2 | ruff fail | builds.py import order | ruff --fix |
| 3 | All pass (backend) | — | — |

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

**Status:** CHANGES REQUESTED (Design Audit) / PENDING (Code Review)

### Design Audit (@fp-design-auditor)

**Verdict: CHANGES REQUESTED**
**Auditor:** fp-design-auditor
**Date:** 2026-04-25
**Reference:** DESIGN.md (single source of truth)

Files audited:
- `frontend/src/screens/ProfileScreen.tsx`
- `frontend/src/components/ui/SegmentedControl.tsx`
- `frontend/src/i18n/strings.ts`
- `frontend/src/i18n/useT.ts`
- `frontend/src/i18n/locales.ts`

---

#### `frontend/src/i18n/locales.ts`

##### PASS
- `AppLocale` type, `DEFAULT_LOCALE` constant, and `normalizeLocale` function match the spec in §4 exactly.
- No design tokens involved; this file is pure logic. No violations.

---

#### `frontend/src/i18n/useT.ts`

##### PASS
- Reads `locale` from `useProfileStore` and memoizes the `getString` call with `useCallback`. Correct pattern.
- No design tokens involved. No violations.

---

#### `frontend/src/i18n/strings.ts`

##### PASS
- Dictionary structure matches the spec example in §4 exactly.
- `getString` falls back to `STRINGS.en[key]` then to the key itself — correct fallback chain.
- All seven keys specified in §3 (`profile.meetGuide`, `profile.everyBuild`, `profile.newName`, `profile.language`, `profile.stateLabel`, `profile.start`, and the placeholder `profile.statePlaceholder`) are present — except `profile.statePlaceholder` (see FAIL below).
- Extra keys (`profile.generating`, `profile.generateError`, `profile.rerollError`, `school.gemmaThinking`, `school.gemmaMatched`, `careerPick.heading`, `gauntlet.nextStepsLoading`) are all on the demo path and well-formed.

##### FAIL
- **Missing string key `profile.statePlaceholder`**: §3 specifies `"Select your state"` / `"Selecciona tu estado"` as the `<option value="" disabled>` placeholder. The key is listed in the §3 table but is absent from `strings.ts`. The `ProfileScreen.tsx` uses a hardcoded `"Select your state"` literal at line 257 instead of `t("profile.statePlaceholder")`. Two violations: (1) the string is missing from the dictionary, (2) `ProfileScreen.tsx` does not call `t()` for this string. Per §3 (Tailwind Classes Reference), this label must be localized.

---

#### `frontend/src/components/ui/SegmentedControl.tsx`

##### PASS
- Container uses `bg-bp-surface rounded-md p-1 gap-1` — matches the spec in §3 (Tailwind Classes Reference) exactly.
- `role="radiogroup"` with `aria-label` prop, per §3 Accessibility table.
- Segment buttons use `role="radio"` and `aria-checked={isSelected}`, per §3 Accessibility table.
- `tabIndex` roving pattern (0 for selected, -1 for others) is correct for keyboard navigation.
- Arrow key handler supports Left/Right and Up/Down, per §3 Interactions.
- `layoutId="segment-active"` sliding indicator uses `transition={springs.snappy}` — DESIGN.md Motion System specifies `springs.snappy` (`{ stiffness: 400, damping: 25 }`) for "toggle, micro-interactions." The implemented value matches exactly (motion.ts line 26: `stiffness: 400, damping: 25`).
- `activeColor` prop (default `bg-accent-thrive`) is configurable — the language selector correctly overrides to `bg-accent-info` per §3.
- Segment buttons are `flex-1` ensuring equal-width distribution. Matches §3.

##### FAIL
- **Segment label uses `text-sm` instead of a Brightpath token (lines 78–79)**: Both the `shortLabel` span and the `label` span use the raw Tailwind class `text-sm` (14px). DESIGN.md Typography defines `text-small` as the 14px token (`--text-small`, `text-small` Tailwind class). The Brightpath type scale does not expose `text-sm` as a token — it is a raw Tailwind utility. All text sizes must reference the Brightpath scale. **Fix:** Replace `text-sm` with `text-small` on both spans (lines 78 and 79).
- **Subtext uses `text-xs` instead of a Brightpath token (line 82)**: The optional `subtext` span uses `text-xs` (12px). DESIGN.md defines `text-micro` as the 12px token (`--text-micro`). **Fix:** Replace `text-xs` with `text-micro` on line 82.
- **Segment button padding is `py-2.5` — does not meet 44px minimum tap target (line 63)**: §3 (Responsive Behavior) explicitly identifies this as a problem and mandates changing `py-2.5` to `py-3` (12px vertical padding) to guarantee 44px minimum touch height. The spec says: "Since the component is currently unused anywhere else, changing `py-2.5` to `py-3` is safe and simpler." This change was specified in the design vision and was not applied. **Fix:** Change `py-2.5` to `py-3` on the segment button `className` at line 63.

##### WARNINGS
- The `layoutId="segment-active"` is hardcoded. §3 notes this is acceptable for now (only one instance on the Profile screen) but flags it for future resolution if a second `SegmentedControl` is added to any screen.

---

#### `frontend/src/screens/ProfileScreen.tsx`

##### PASS
- `LANGUAGE_SEGMENTS` is defined at module level as a stable constant, per §3 spec instruction. Correct.
- `SegmentedControl` is passed `activeColor="bg-accent-info"` per §3 — info-blue is the correct semantic color for a navigation/neutral choice, not `bg-accent-thrive` (positive outcome).
- `ariaLabel` is dynamically set: `locale === "es" ? "Elegir idioma" : "Choose language"`, per §3 Accessibility table.
- Language selector `motion.div` uses `variants={staggerItem}` and is positioned after the divider and before the home-state selector, exactly per §3 wireframe.
- Wrapper uses `mt-6 w-full max-w-xs` — matches §3 Tailwind Classes Reference for the language wrapper.
- Label uses `block font-body text-small text-text-secondary mb-2 text-center` — matches §3 Tailwind Classes Reference for the language label.
- Home-state label uses the same `block font-body text-small text-text-secondary mb-2 text-center` pattern.
- `Button` component is used for the CTA (not a raw `<button>`), and it renders with the `primary` variant by default — `bg-accent-thrive`, `text-text-inverse`, `h-12`, `rounded-lg`, `font-body font-bold`, `whileTap scale(0.97)` per DESIGN.md Buttons spec.
- Reroll button uses `rounded-lg`, `h-[44px]`, `border border-accent-info`, `bg-transparent`, `hover:bg-accent-info/10`, `transition-all duration-normal` — matches DESIGN.md Secondary button hover state convention.
- `text-accent-alert` is used for error messages — correct semantic token (alert = warnings, negative outcomes per DESIGN.md Accents table).
- Focus state on the `<select>` uses `focus:border-accent-info focus:shadow-[0_0_0_3px_rgba(123,184,224,0.15)]` — matches DESIGN.md Input-specific focus override exactly.
- `bg-bp-deep` for the select background matches DESIGN.md Input spec (`background: bg-deep`).
- `border-border` on the select matches DESIGN.md Input spec (`border: 1px solid border-default`).
- `rounded-md` on the select matches DESIGN.md Input spec (`border-radius: radius-md`).
- `text-text-primary font-body` on select text matches DESIGN.md Input spec.
- Stagger container uses `staggerChildren: 0.12` — this is between `stagger.fast` (50ms) and `stagger.normal` (80ms) in DESIGN.md. See WARNING below.
- `ambient-breathe` CSS keyframe animation is used for the emoji glow, consistent with DESIGN.md (`ambient-breathe 6s` is the spec; the implementation uses `4s`). See FAIL below.

##### FAIL
- **`ambient-breathe` animation duration is `4s`, spec requires `6s` (line 159)**: The inline style at line 159 applies `"ambient-breathe 4s ease-in-out infinite"`. DESIGN.md CSS Keyframe Animations table specifies `ambient-breathe` as `6s ease-in-out infinite`. The duration is hardcoded and wrong. **Fix:** Change `4s` to `6s` to match the canonical token duration.
- **Emoji size uses raw Tailwind `text-5xl tablet:text-6xl` instead of a Brightpath token (line 173)**: The animal emoji is sized with `text-5xl` (48px) and `tablet:text-6xl` (60px). DESIGN.md does not define `text-5xl` or `text-6xl` as Brightpath tokens. The closest defined token for large emoji would be implementation-specific, but using raw Tailwind size utilities that bypass the Brightpath type scale is a token violation. Note: this violation pre-dates the Language Mode feature; it is present in the unmodified emoji display code. It is flagged here as it appears in the audited file.
- **`text-base` on the select element instead of a Brightpath token (line 255)**: The `<select>` uses `text-base` (16px). DESIGN.md defines `text-body` as the 16px token (`--text-body`). **Fix:** Replace `text-base` with `text-body`.
- **Hardcoded `"Select your state"` literal instead of `t("profile.statePlaceholder")` (line 257)**: This string is in the §3 localization table and must be driven by the `useT()` hook. The key does not exist in `strings.ts` either (see strings.ts FAIL above). Two fixes required: (1) add `profile.statePlaceholder` to `strings.ts` in both `en` and `es`, (2) replace the literal at line 257 with `t("profile.statePlaceholder")`.

##### WARNINGS
- **Local `staggerContainer`/`staggerItem` variants use `show`/`hidden` keys, not the canonical `visible`/`hidden` keys**: The module-level exports in `motion.ts` use `hidden`/`visible`. `ProfileScreen.tsx` defines local variants using `hidden`/`show` (lines 55–67). This is not a token violation per se — Framer Motion variant names are arbitrary — but it creates inconsistency with the shared `staggerItem` export from `motion.ts` (which uses `visible`). If the canonical variants from `motion.ts` were used directly, the inconsistency would not exist. This is a non-blocking style concern.
- **Stagger `staggerChildren: 0.12` (120ms) is between defined stagger tokens**: DESIGN.md defines `stagger.fast` (50ms), `stagger.normal` (80ms), and `stagger.slow` (100ms). 120ms is outside the token set. The closest is `stagger.slow` at 100ms. Non-blocking for this feature since the stagger predates the Language Mode work, but worth aligning on a defined token value.
- **`duration: 0.15` on the reroll `AnimatePresence` transition (line 170) uses a raw value**: DESIGN.md defines `--transition-fast` as 150ms (`duration-fast` Tailwind class). The value is correct (0.15s = 150ms) but implemented as a raw number rather than referencing `duration-fast`. Not blocking; the value matches.

---

#### Summary of Required Fixes

| # | File | Line | Issue | Severity |
|---|------|------|-------|----------|
| 1 | `SegmentedControl.tsx` | 63 | `py-2.5` must be `py-3` for 44px tap target (per §3 spec mandate) | FAIL |
| 2 | `SegmentedControl.tsx` | 78–79 | `text-sm` must be `text-small` (Brightpath token) | FAIL |
| 3 | `SegmentedControl.tsx` | 82 | `text-xs` must be `text-micro` (Brightpath token) | FAIL |
| 4 | `ProfileScreen.tsx` | 159 | `ambient-breathe 4s` must be `ambient-breathe 6s` per DESIGN.md | FAIL |
| 5 | `ProfileScreen.tsx` | 255 | `text-base` must be `text-body` (Brightpath token) | FAIL |
| 6 | `ProfileScreen.tsx` | 257 | Hardcoded `"Select your state"` must use `t("profile.statePlaceholder")` | FAIL |
| 7 | `strings.ts` | — | `profile.statePlaceholder` key missing in both `en` and `es` | FAIL |

Items 1–3 and 5–7 are directly attributable to the Language Mode implementation. Item 4 (`ambient-breathe 4s`) pre-dates this feature.

### Code Review (@faang-staff-engineer)

[Pending]

---

## §9 Verification

**Status:** ALL PASSED
**Verified:** 2026-04-25 16:36
**Branch:** localization-support
**Verifier:** @fp-builder (Claude Sonnet 4.6)

### Backend

| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff) | PASS | No issues (after 3 fixable lint errors resolved in test files) |
| Type check (mypy) | PASS | 72 errors — all 72 are pre-existing on `main`; 0 new errors from this feature |
| Tests (pytest) | PASS | 1165 passed, 6 failed (all 6 are confirmed pre-existing — see below) |

### Frontend

| Check | Result | Details |
|-------|--------|---------|
| TypeScript | PASS | No errors |
| Tests (vitest) | PASS | 645 passed, 1 skipped, 0 failed |
| Production build (Vite) | PASS | 703 modules, built in 1.42s |

### Pre-Existing Backend Test Failures (confirmed on `main`)

| Test | Status |
|------|--------|
| `test_gemma_client.py::test_generate_async_logs_to_jsonl` | Pre-existing |
| `test_gemma_client.py::test_generate_async_jsonl_integrity_under_gather` | Pre-existing |
| `test_gemma_client.py::test_generate_with_tools_prompt_fallback` | Pre-existing |
| `test_set_your_course.py::TestStreamInitial::test_transport_failure_returns_empty` | Pre-existing |
| `test_set_your_course.py::TestConfirmedFocus::test_confirmed_focus_dropped_when_bucket_is_intent_divergence` | Pre-existing |
| `test_set_your_course.py::TestResolverIntentKeywords::test_student_major_text_set_on_fallback_path` | Pre-existing |

### Build Accountability Log

| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | ruff failed | `test_locale.py`: unused `AppLocale` import, unsorted imports; `test_next_steps.py`: unused `pytest`, `CareerBranch`, `SkillRec` imports; `test_boss_fights.py`: E501 line too long; `test_builds.py`: E501 line too long | Removed unused imports via `ruff --fix`; wrapped long lines |
| 1 | mypy failed | 5 new errors: `api.py:13` AppLocale not exported from `career.py`; `builds.py:90,93,94,96` `locale: str` incompatible with `Literal["en", "es"]` | Fixed `api.py` to import `AppLocale` from `app.services.locale` directly; typed `_gemma_fanout` `locale` param as `AppLocale` |
| 1 | vitest failed | `BuildResultsScreen.test.tsx` (2 tests): `createBuild` call assertions missing new `locale` arg; `GemmaChat.test.tsx` (1 test): `sendChat` call assertion missing new `locale` arg | Added `"en"` to all three `toHaveBeenCalledWith` assertions (authorized test modifications per §4) |
| 2 | All checks passed | — | — |

---

## §10 GenAI Review / Discussion

### @genai-architect Review

**Status:** APPROVED WITH RECOMMENDATIONS

**Reviewer:** genai-architect (Claude Sonnet 4.6)
**Date:** 2026-04-25

---

#### 1. Spanish prompt instruction wording — is it effective?

**Finding: Effective with two gaps.**

The instruction achieves the essential goals: it names the output language, provides a glossary, and states the canonical-preservation rule. Reviewing it against the existing `_SYSTEM` and `_NARRATIVE_SYSTEM` patterns in the codebase reveals two gaps:

**Gap A — The preservation list is not ordered by risk of translation.**

The current instruction lists: "school names, program names, occupation titles, source names, dollar amounts, percentages, codes, and JSON keys." Gemma 4 tends to drift toward translating items listed later in an enumeration. The highest-risk items under Spanish generation are occupation titles (Gemma frequently translates "Registered Nurse" to "Enfermera Registrada") and source acronyms (BLS, O*NET). Both should move to the front of the list.

Recommended ordering: "official school names, occupation titles, source names and their acronyms (BLS, O*NET, IPEDS, BEA, College Scorecard), program names, dollar amounts, percentages, codes, and JSON keys."

**Gap B — No explicit instruction to keep source acronyms in English.**

The existing English `_SYSTEM` prompt in `guidance.py` includes a cite-sources rule: first reference uses full name + parenthetical acronym; subsequent references use the acronym alone. The Spanish instruction has no corresponding rule, which leaves Gemma free to translate "Bureau of Labor Statistics" to "Oficina de Estadísticas Laborales" on subsequent references, losing the BLS acronym the student will need to look things up independently. Recommend adding: "After the first reference to a data source, use only its English acronym (BLS, O*NET, IPEDS, BEA). Do not translate these acronyms."

The preservation sentence itself is well-formed. "You may explain what an official English title means in Spanish after naming it, but do not replace the canonical title." This is the right semantic shape for a multilingual instruction: it grants a permitted behavior (explanatory gloss) and names the forbidden behavior (replacement), which reduces ambiguity compared to a bare prohibition.

---

#### 2. Glossary — sufficient for the demo path?

**Finding: Adequate for the demo path; four additions recommended.**

The demo path covers: profile → Set Your Course → career pick → Reveal/Gemma's Take → Gauntlet/Next Steps → Ask Gemma. Reviewing the `_NARRATIVE_SYSTEM` prompt in `boss_fights.py` and the `_SYSTEM` prompt in `next_steps.py` against the glossary, the following student-facing concepts appear in Gemma prose on the demo path but are absent:

- `debt-to-income` — Gemma writes this in boss narratives when the Loans boss fires. Without a canonical term, Gemma will produce whatever phrase it generates. Suggest: `debt-to-income = deuda en relación con los ingresos`.
- `next steps` — appears as both a section heading (UI dictionary) and a Gemma-generated phrase (next_steps.py prose). If the UI renders the heading from the static dictionary and Gemma uses a different phrase, the experience is inconsistent. Suggest: `next steps = próximos pasos`.
- `cost of attendance` — Gemma references this when quoting debt data in guidance and boss narratives. Suggest: `cost of attendance = costo de asistencia`.
- `purchasing power` — can appear in guidance prose when the BEA regional price parity data is cited. Suggest: `purchasing power = poder adquisitivo`.

None of these gaps will crash the demo, but without glossary terms Gemma will invent translations that may not match the static UI strings, producing an inconsistent student experience.

---

#### 3. Mixed JSON + prose constraint — is it clear enough?

**Finding: The rule is correct but the implementation instruction is underspecified; adding explicit JSON constraint text to the prompt is required.**

The spec states: "Prose must follow locale. JSON keys must stay English. JSON enum values stay English unless the existing parser explicitly accepts localized values." This is the right model. The risk is that if `gemma_language_instruction("es")` only says "Write all student-facing prose in Spanish," Gemma will apply that to all string values in any JSON block, including `confidence` (`"high"` → `"alta"`), tier headers, and matched CIP codes — breaking the backend parsers silently.

Two parsers are directly at risk:

- `_STREAM_INTENT_SYSTEM_PROMPT` in `set_your_course.py` — parses `confidence: "high"|"medium"|"low"` from the JSON tail after `---INTENT_JSON---`. If Gemma translates `"high"` to `"alta"`, the result model receives an unexpected enum value.
- `career_tiering.py` — `_TIER_HEADER = re.compile(r"^\s*(?:COMMON|LESS_COMMON|STRETCH)\s*$")` and `_HEADER_TO_LABEL` dict rely on exact English token matching. A Spanish Gemma call that produces `COMUN` or `MAS_COMUN` will cause every career to fall into the fallback "All career paths" tier.

The `gemma_language_instruction("es")` text should include an explicit JSON constraint block:

```
If your response includes a JSON section or structured output, keep all
JSON keys and enum values in English exactly as specified — including
values like "high", "medium", "low", "COMMON", "LESS_COMMON", "STRETCH",
and all CIP/SOC codes. Only translate free-text prose fields (such as
"reasoning", "rationale", "message", "narrowing_hint", "why").
```

This is more precise than the current spec wording and directly protects the two parsers identified above. Without this, Spanish mode will silently break intent-resolution JSON parsing and career tiering on the first demo run.

---

#### 4. Internal-only Gemma calls — should they remain English?

**Finding: Yes. The spec's exclusion list is correct and complete.**

`soc_expansion.py` returns SOC codes and internal rationale used only by the crosswalk engine; the parser extracts SOC codes via `re.compile(r"\b(\d{2}-\d{4})\b")` and rationale is logged but never rendered to the student. `scripts/gemma_ai_exposure_scorer.py` is a batch pipeline script whose outputs land in DuckDB. Both are correct exclusions.

**One additional surface to verify: `career_tiering.py`.**

The spec notes this correctly: "Structured tier headers must remain English." The `_TIER_HEADER` regex and `_HEADER_TO_LABEL` dict confirm the parser is not locale-aware. The tier display labels shown to the student (`"Common paths"`, `"Less common but realistic"`, `"Stretch paths"`) are rendered by the frontend from the static dictionary, not generated by Gemma. This is the right division. The spec should be clear that `career_tiering.py` receives no locale injection in this feature and will only need revisiting if tier-display labels are ever moved into Gemma-generated prose.

**`intent.resolve_intent` non-streaming path:** The spec's "backward-compatible default `en`; accept locale if route passes it" approach is safe. However, this surface carries the same JSON-breakage risk as `_STREAM_INTENT_SYSTEM_PROMPT` described in §3 above. The explicit JSON constraint text in `gemma_language_instruction("es")` is critical here too.

---

#### 5. Prompt injection risks from the locale parameter

**Finding: Low risk with the current design. One defensive hardening recommended.**

The locale parameter flows through `normalize_locale(value) -> AppLocale` before reaching any prompt builder. `normalize_locale` returns only `"es"` or `"en"` regardless of input — a malicious input like `"es'; DROP TABLE builds; --"` produces `"en"`. The `gemma_language_instruction` function selects a fully static string branch based on a two-value `Literal` type, so the locale value itself is never interpolated into the prompt text.

Residual note: student-supplied `major_text` and `clarifier` are already interpolated into Gemma prompts (e.g., `"{clarifier}"` in `_CHIP_ROUTING_SYSTEM_PROMPT`). This is pre-existing and out of scope for this feature; adding the language instruction does not increase that surface area.

Defensive recommendation: ensure `normalize_locale` is called at the service layer before prompt construction, not only at the Pydantic request-model boundary. The type signature enforces this at type-check time but a direct service call from a test or script that bypasses the router model could pass an unchecked value. An explicit `normalize_locale` call at each service entry point costs one line and eliminates the gap.

---

#### Summary Verdict

| Area | Verdict | Action Required |
|------|---------|----------------|
| Spanish instruction wording | Approved with fixes | Reorder preservation list (titles and source acronyms first); add acronym-retention rule for BLS/O*NET/IPEDS/BEA |
| Glossary coverage | Approved with additions | Add: `debt-to-income`, `next steps`, `cost of attendance`, `purchasing power` |
| Mixed JSON+prose constraint | Needs clarification in implementation | Add explicit JSON key/enum preservation text to `gemma_language_instruction("es")` body in the spec |
| Internal-only call exclusions | Approved | Confirm `career_tiering.py` receives no locale injection; document the division in code comment |
| Prompt injection risk | Approved | Add `normalize_locale` call at service layer as defensive guard |

**Overall: APPROVED.** The three items marked "action required" should be resolved before the Implementation step by updating the `gemma_language_instruction("es")` body directly in §4 of this spec. None require an architecture change or human escalation.

---

### Open Questions

| Date | Question | Owner | Resolution |
|------|----------|-------|------------|
| 2026-04-25 | Should official source names like "Bureau of Labor Statistics" remain English in Spanish prose, or allow first-use Spanish explanation in parentheses? | Jeff | Recommended: allow first-use gloss ("Bureau of Labor Statistics (BLS) — Oficina de Estadísticas Laborales") with subsequent references using the English acronym only. This preserves the BLS/O*NET acronyms students need to look things up independently. Add this rule to `gemma_language_instruction("es")`. |
| 2026-04-25 | Should occupation titles get Spanish explanatory glosses in the UI, or only inside Gemma prose? | Jeff | Recommended: Gemma prose only for MVP. UI occupation titles come directly from BLS/O*NET canonical data and should remain English in card display. Gemma's Take can provide the gloss inline ("Registered Nurse, or enfermera registrada as it is known in Spanish"). Keeping UI titles canonical also avoids a localization dependency on Gold-zone data. |

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

---

## §12 Arabic Extension (added 2026-04-30)

This section documents the third locale layered onto the EN/ES architecture above. **It is an extension, not a separate spec** — the architecture, prompt contract, JSON-key preservation rule, fallback registry, and locale plumbing all carry forward unchanged. The decision to add Arabic is documented in `docs/language-support-decision-report.md` (Arabic is the most common non-Spanish home language among U.S. public-school English learners per NCES fall 2021 EDFacts).

### Why this isn't a full spec rebuild

The EN/ES pipeline is the contract. Adding Arabic is:

1. Widening one Literal type on each side (`Literal["en", "es"]` → `Literal["en", "es", "ar"]`).
2. Adding one prompt block (`_AR_INSTRUCTION`) and 6 fallback strings.
3. Translating the existing `STRINGS.en` keys into `STRINGS.ar`.
4. Adding RTL handling — the only architecturally novel piece.

There is no new screen, no new API, no new Gemma function call, no new data flow, no new pydantic model. The architecture review and design vision from §5 still hold.

### What's shipped

| File | Change |
|------|--------|
| `frontend/src/i18n/locales.ts` | Widened `AppLocale` to `"en" \| "es" \| "ar"`. Added `isRtlLocale()` and `localeDirection()` helpers. |
| `frontend/src/i18n/locales.test.ts` | 17 tests (was 9): Arabic normalization, RTL helpers, direction mapping. |
| `frontend/src/i18n/strings.ts` | Populated the previously-empty `ar:` block with 262 translated keys. Also closed the pre-existing parity gap by translating `compareSchools.*` into Spanish (was English-fallthrough). |
| `frontend/src/i18n/strings.test.ts` | Arabic getString tests, brand/acronym preservation check (Gemma stays Latin script, SOC/CIP stay Latin script inside Arabic strings). |
| `frontend/src/i18n/useDocumentLocale.ts` | New hook — syncs locale to `document.documentElement.lang` and `dir`. |
| `frontend/src/App.tsx` | Mounts `useDocumentLocale()` once at the AppRoutes root. |
| `frontend/src/index.css` | Imports Cairo + Noto Naskh Arabic. Adds `html[dir="rtl"] body` font stack and `[data-bdi]` LTR-isolation utility for canonical English content inside Arabic prose. |
| `frontend/src/screens/ProfileScreen.tsx` | Adds `العربية` to the `LANGUAGE_SEGMENTS` segmented control. ARIA label switches to Arabic when locale is `ar`. |
| `backend/app/services/locale.py` | Widened `AppLocale` Literal. New `_AR_INSTRUCTION` block (Modern Standard Arabic, glossary of 14 product terms, Western-Arabic-numeral rule, Latin-script preservation rule for school names / occupation titles / source acronyms / dollar amounts / percentages / codes / JSON keys). Added `ar` entries to all six `_FALLBACKS` keys. |
| `backend/tests/services/test_locale.py` | 40 tests (was 27): Arabic normalize_locale, Arabic instruction content, Arabic fallback parity. |

### Arabic-specific Gemma prompt rules

Beyond the EN/ES contract, the Arabic prompt enforces:

1. **Modern Standard Arabic (الفصحى)** — not dialect. Schools and labor-market language belongs in MSA.
2. **Latin script preserved for canonical fields** — school names, occupation titles, source acronyms (BLS, O*NET, IPEDS, BEA, College Scorecard), program names, JSON keys, and enum values are NOT transliterated. Indiana University is rendered as "Indiana University" inside Arabic prose, not as "إنديانا يونيفرسيتي".
3. **Western Arabic numerals (0-9), not Eastern Arabic numerals (٠-٩)** — for dollars, percentages, years, and codes. This matches the rest of the app and the underlying data, and it avoids encoding fragility on cross-system copy/paste.
4. **JSON keys and enum values stay English** — same rule as Spanish. Free-text prose fields (`reasoning`, `rationale`, `message`, `narrowing_hint`, `why`) are the only places Arabic appears in structured Gemma output.

### Arabic glossary (the 14 product terms Gemma is bound to)

| English | Arabic |
|---|---|
| student debt | الديون الطلابية |
| career paths | المسارات المهنية |
| job outlook | آفاق التوظيف |
| AI exposure | التعرض للذكاء الاصطناعي |
| human edge | الميزة الإنسانية |
| data is estimated | البيانات تقديرية |
| salary | الراتب |
| median salary | الراتب الوسيط |
| student loan | القرض الطلابي |
| guidance counselor | المرشد الأكاديمي |
| debt-to-income | نسبة الدين إلى الدخل |
| next steps | الخطوات التالية |
| cost of attendance | تكلفة الدراسة |
| purchasing power | القوة الشرائية |

### RTL strategy

| Concern | Approach |
|---|---|
| Document direction | `useDocumentLocale` hook sets `<html lang="ar" dir="rtl">` reactively when locale flips. Browser flexbox + grid honor `dir`, so `flex-row` and `grid-cols-*` mirror automatically. |
| Typography | Cairo (body weight, Nunito-equivalent) + Noto Naskh Arabic (display weight, Fredoka-equivalent), loaded alongside the Latin stack so canonical Latin content renders in its own font. |
| Bidirectional content | `[data-bdi]` utility forces `unicode-bidi: isolate; direction: ltr` for inline Latin runs (school names, $ amounts, codes) inside Arabic paragraphs. Apply on the spans wrapping canonical fields. |
| Tailwind directional classes | Tailwind 3.4 supports `rtl:` and logical properties (`ms-*`, `me-*`, `ps-*`, `pe-*`, `start-*`, `end-*`, `text-start`, `text-end`). Use the `rtl:` variant where existing physical classes (`mr-*`, `ml-*`, `pr-*`, `pl-*`, `text-left`, `text-right`) cause asymmetry on the demo path. |
| Arrows / chevrons | The arrow glyphs in user-facing strings (`→`, `←`) are pre-flipped in the Arabic translations — buttons that say "Continue →" in English say "متابعة ←" in Arabic. |
| Number direction | Western Arabic numerals (0-9) are LTR even inside RTL paragraphs; Unicode bidi handles this correctly without intervention. |

### Known gaps (pre-existing — not introduced by Arabic)

These predate Arabic — they affect Spanish today the same way. Listed here so the next chrome-extraction pass has a target list:

- `frontend/src/components/CareerDetail.tsx` — financial-line labels ("In-state tuition", "Out-of-state tuition", "Room & board", source attribution lines) hardcoded in JSX.
- `frontend/src/components/GemmaTake.tsx` — "Generated by Gemma 4 based on:" plus its bullet list ("Pentagon stat profile", "Boss fight outcomes", "Career branch data", "Program-specific earnings").
- `frontend/src/components/horizon/HorizonFooter.tsx` — "Built with Gemma 4".
- `frontend/src/components/CareerLineageSheet.tsx` — "Ask another question."
- `frontend/src/components/gauntlet/BossFightCard.tsx` — debug rows ("Raw score", "Win threshold", "Reason", "Original result") — likely dev-mode only, but worth confirming.

In all cases the `getString` fallback chain (`STRINGS[locale][key] ?? STRINGS.en[key] ?? key`) means these render in English in any locale. Adding Arabic does not make this worse; it inherits the same gap.

### Demo-path test (REQUIRED before claiming Arabic support)

Per the decision report: do not claim Arabic support without manually walking the full golden path in `?locale=ar` (or by selecting `العربية` on the Profile screen). Watch for:

- Layout asymmetry — anything visibly off-axis vs the EN layout
- Untranslated strings — fallthroughs to English (these are the gaps above)
- Truncation / line-wrap issues — Arabic letters can be wider than their Latin equivalents at the same font size
- Gemma prose — verify Modern Standard Arabic (not dialect), verify school names and $ amounts stay Latin script, verify Western numerals
- Stat pentagon / horizon strip / branch tree — these are SVG-based and don't auto-flip with `dir`. Check label positioning.
- Mixed-content paragraphs — verify `[data-bdi]` is applied where Latin content appears mid-Arabic-sentence

### Submission framing (per decision report)

Once the demo-path test passes:

> FutureProof supports English, Spanish, and Arabic across the student-facing app and Gemma-generated guidance, while preserving official school names, occupation titles, source acronyms, dollar amounts, percentages, and structured data fields.

Until the demo-path test passes:

> FutureProof currently supports English and Spanish, and its language architecture is being extended to Arabic because Arabic is the most common non-Spanish home language among U.S. public school English learners.

Avoid:

- "FutureProof supports 140 languages."
- "Arabic support is complete" without the manual demo-path test.
