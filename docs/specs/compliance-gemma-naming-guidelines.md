# Compliance: Gemma Naming & Attribution Guidelines

## Claude Code Prompt

```
Read and implement the spec at docs/specs/compliance-gemma-naming-guidelines.md

This is a naming/copy compliance pass — no new features, no architectural changes.
The Google DeepMind "External Gemma Model Variant Guidelines" PDF requires:
  1. Don't use "Gemma" as a product persona / character name
  2. Add "Gemma is a trademark of Google LLC." attribution
  3. Don't use Gemma brand elements in your own branding

Work through the change tables in §2 methodically. Each table is one surface.
After implementing, run full test suite (pytest + ruff + mypy + tsc + vitest).
Update any tests that assert on changed strings.
```

---

## Status: DRAFT

| Field | Value |
|-------|-------|
| Created | 2026-05-12 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-05-12 |
| Priority | High (submission deadline 2026-05-18) |
| Blocked By | — |
| Related Specs | `docs/specs/submission-kaggle-narrative.md` |
| Source Document | `External_Gemma_Model_Variant_Guidelines.pdf` (Google DeepMind) |

---

## §1 Problem

Google's "Gemma model variant naming & attribution guidelines" PDF establishes three rules:

1. **Model naming:** Do not use "gemma" as part of your model or product name.
2. **Attribution:** Include `"Gemma is a trademark of Google LLC."` wherever the Gemma name/marks are used.
3. **Branding:** Avoid using Gemma brand elements (name, mark, colors) in your own branding. Only reference Gemma when accurately describing its distribution.

FutureProof currently **personifies** Gemma throughout the product — "Ask Gemma," "Gemma is thinking," "Written by Gemma," "Gemma's Take" — treating it as an in-app character rather than an underlying model. This risks implying Google affiliation and violates the spirit of the guidelines.

The attribution statement is missing entirely.

### What's NOT changing

- **Internal code** — variable names (`gemma_client`), file names (`ask_gemma.py`), CSS class names (`animate-gemma-shimmer`), type names (`GemmaTraceEvent`). These are developer-facing, not user-facing. No judge or user sees them.
- **Technical documentation in README** — accurate references to the Gemma 4 model, model slugs (`gemma4:e4b`, `google/gemma-4-26b-a4b-it`), architecture diagrams. These are factual tech descriptions, which the guidelines encourage.
- **About screen source card** — "Gemma 4" / "Google DeepMind" as a listed technology. This is accurate attribution.

### Success Criteria

- [ ] No user-facing string personifies Gemma as a character (no "Ask Gemma," "Gemma is thinking," "Gemma's Take")
- [ ] `"Gemma is a trademark of Google LLC."` appears on About screen, README, PDF report disclaimers, and landing page footer
- [ ] System prompts use a FutureProof-owned persona name, not "You are Gemma"
- [ ] All tests pass after string changes
- [ ] Three-language parity maintained (EN, ES, AR)

---

## §2 Change Tables

> **Naming convention decision:** Every "Ask Gemma" / "Gemma is thinking" / "Gemma's Take" reference needs a replacement name. This spec proposes **"the Guide"** as the in-app persona — short, natural in context ("Ask the Guide," "The Guide is thinking"), and entirely FutureProof-owned. Jeff should confirm or override this choice before implementation begins.
>
> Alternative names considered: "Coach," "Advisor," "Scout," "Compass," "the Reader"

---

### Table A — i18n Strings (`frontend/src/i18n/strings.ts`)

All changes apply ×3 (EN, ES, AR). Only EN values shown; translators apply the same pattern to ES/AR.

| String Key | Current (EN) | Proposed | Notes |
|------------|-------------|----------|-------|
| `syc.gemmaThinking` | "Gemma is thinking" | "Thinking…" | |
| `syc.gemmaMatched` | "Gemma matched" | "Matched" | |
| `syc.gemmaReasoning` | "Gemma is reasoning about your clarifier…" | "Reasoning about your clarifier…" | |
| `syc.softNudge` | "Gemma wasn't sure on this one. Worth a sanity check?" | "This one's a close call. Worth a sanity check?" | |
| `careerPick.askGemma` | "Ask Gemma" | "Ask the Guide" | |
| `build.analyzing` | "Gemma is analyzing your build..." | "Analyzing your build…" | |
| `build.loading4` | "Asking Gemma for advice..." | "Loading guidance…" | |
| `build.askGemma` | "Ask about build" | "Ask about build" | Already fine — no change |
| `build.writtenByGemma` | "✦ Written by Gemma" | "✦ Written by the Guide" | |
| `build.skillsLoading` | "Gemma is researching skills to help you win..." | "Researching skills to help you win…" | |
| `chat.askAboutThis` | "Ask Gemma about this" | "Ask the Guide about this" | |
| `chat.askAboutBuild` | "Ask Gemma about your whole build" | "Ask the Guide about your whole build" | |
| `chat.compareEntry` | "Chat with Gemma about this comparison" | "Chat about this comparison" | |
| `chat.opener.skeleton.reading` | "Gemma is reading your career path…" | "Reading your career path…" | |
| `chat.opener.skeleton.thinking` | "Gemma is thinking about {branch}…" | "Thinking about {branch}…" | |
| `boss.askWhy.aria.passed` | "Ask Gemma why this risk passed" | "Ask why this risk passed" | |
| `boss.askWhy.aria.didntPass` | "Ask Gemma why this risk did not pass" | "Ask why this risk did not pass" | |
| `boss.askWhy.aria.borderline` | "Ask Gemma why this risk is borderline" | "Ask why this risk is borderline" | |
| `header.inferenceLocalTitle` | "Gemma running locally via Ollama ({model})" | "Running locally via Ollama ({model})" | |
| `header.inferenceCloudTitle` | "Gemma running in the cloud via OpenRouter ({model})" | "Running in the cloud via OpenRouter ({model})" | |
| `about.sources.beaRpp.blurb` | "...ask Gemma what a salary is worth..." | "...ask what a salary is worth..." | |
| `about.sources.gemma.blurb` | "...writes Gemma's Take..." / "Gemma's job is to translate..." | "...writes The Guide's Take..." / "Its job is to translate..." | Rewrite needed |
| `menu.subtitle` | "Compare your futures, ask Gemma, or start a new build." | "Compare your futures, ask the Guide, or start a new build." | |
| `menu.askGemma` | "Ask Gemma" | "Ask the Guide" | |

**String keys to rename** (optional but recommended for code clarity):

| Current Key | Proposed Key |
|-------------|-------------|
| `careerPick.askGemma` | `careerPick.askGuide` |
| `build.askGemma` | `build.askGuide` |
| `build.writtenByGemma` | `build.writtenByGuide` |
| `menu.askGemma` | `menu.askGuide` |
| `syc.gemmaThinking` | `syc.guideThinking` |
| `syc.gemmaMatched` | `syc.guideMatched` |
| `syc.gemmaReasoning` | `syc.guideReasoning` |

> Key renames require updating every file that references the old key. A find-and-replace pass is needed. If this is too risky this close to deadline, the key names can stay — only the *values* are compliance-relevant.

---

### Table B — Hardcoded Strings in Components

| File | Line(s) | Current | Proposed |
|------|---------|---------|----------|
| `frontend/src/components/build-results/NarrativeTimeline.tsx` | 87 | `"Gemma's Summary"` | `"The Guide's Take"` |
| `frontend/src/components/build-results/NarrativeTimeline.tsx` | 212 | `"Gemma is rethinking this one..."` | `"Rethinking this one…"` |
| `frontend/src/components/build-results/InstitutionCard.tsx` | 57 | `"Gemma is writing..."` | `"Writing…"` |
| `frontend/src/components/build-results/BossBand.tsx` | 478 | `"Gemma is analyzing..."` | `"Analyzing…"` |
| `frontend/src/components/build-results/StatInfoPopover.tsx` | 83 | `` aria-label={`Ask Gemma about ${info.title}`} `` | `` aria-label={`Ask the Guide about ${info.title}`} `` |
| `frontend/src/components/gauntlet/NextSteps.tsx` | 68 | `"Gemma is writing your action plan..."` | `"Writing your action plan…"` |
| `frontend/src/components/gauntlet/NextSteps.tsx` | 83 | `"Gemma couldn't generate your action plan right now..."` | `"Couldn't generate your action plan right now..."` |
| `frontend/src/components/menu/GemmaTrace.tsx` | 107 | `"Gemma is looking something up…"` | `"Looking something up…"` |
| `frontend/src/components/menu/GemmaTrace.tsx` | 108 | `"Gemma is looking things up…"` | `"Looking things up…"` |
| `frontend/src/components/menu/GemmaTrace.tsx` | 112 | `"Gemma checked one source."` | `"Checked one source."` |
| `frontend/src/components/menu/GemmaTrace.tsx` | 113 | `` `Gemma checked ${total} sources.` `` | `` `Checked ${total} sources.` `` |
| `frontend/src/components/menu/GemmaTrace.tsx` | 139 | `aria-label="Gemma's reasoning steps for this answer"` | `aria-label="Reasoning steps for this answer"` |
| `frontend/src/components/horizon/HorizonFooter.tsx` | 327 | `"Built with Gemma 4"` | `"Powered by Gemma 4"` |
| `frontend/src/components/horizon/ChapterBookMockup.tsx` | 616 | `"Gemma matched"` | `"Matched"` |
| `frontend/src/components/horizon/HorizonStripMockup.tsx` | 535 | `"Gemma matched"` | `"Matched"` |

---

### Table C — Landing Page & Meta Tags

| File | Line(s) | Current | Proposed | Notes |
|------|---------|---------|----------|-------|
| `frontend/index.html` | 11 | `"...powered by...Gemma 4. Pick a school..."` | No change | Factual tech description — compliant |
| `frontend/index.html` | 18, 26 | `"...powered by...Gemma 4. Every number..."` | No change | Same |
| `frontend/src/components/landing/OllamaSection.tsx` | 48-49 | `"FutureProof runs on Gemma 4 through Ollama...Gemma's coaching..."` | `"FutureProof runs on Gemma 4 through Ollama...the Guide's coaching..."` | "Gemma 4" keep, "Gemma's coaching" change |
| `frontend/src/components/landing/TeamSection.tsx` | 26 | `"...Gemma 4 Good hackathon..."` | No change | Factual reference to hackathon name |
| `frontend/src/components/landing/DataSourcesSection.tsx` | 131 | `"Composite AI exposure blends Gemma 4 task-level scoring..."` | No change | Factual tech description |

---

### Table D — Backend System Prompts

These are the `"You are Gemma"` instructions sent to the model. Changing the persona name here does **not** change model behavior — Gemma 4 doesn't need to think its name is "Gemma" to function.

| File | Line | Current | Proposed |
|------|------|---------|----------|
| `backend/app/services/career_pick_qna.py` | 37 | `"You are Gemma. A high school student..."` | `"You are the Guide, FutureProof's career advisor. A high school student..."` |
| `backend/app/services/boss_fights.py` | 618 | `"You are Gemma. A high school student..."` | `"You are the Guide, FutureProof's career advisor. A high school student..."` |
| `backend/app/services/boss_fights.py` | 683 | `"You are Gemma writing one short note..."` | `"You are the Guide writing one short note..."` |
| `backend/app/services/guidance.py` | 36 | `"You are Gemma. A high school student..."` | `"You are the Guide, FutureProof's career advisor. A high school student..."` |
| `backend/app/services/guidance.py` | 94 | `"You are Gemma writing a short career-path read..."` | `"You are the Guide writing a short career-path read..."` |
| `backend/app/services/guidance.py` | 341 | `"You are Gemma, in a chat thread..."` | `"You are the Guide, in a chat thread..."` |
| `backend/app/services/ask_gemma.py` | 157 | `"You are Gemma, in a chat thread..."` | `"You are the Guide, in a chat thread..."` |
| `backend/app/services/next_steps.py` | 26 | `"You are Gemma, writing a 'Your Next Steps'..."` | `"You are the Guide, writing a 'Your Next Steps'..."` |

---

### Table E — "Gemma's Take" Feature Name

The feature currently named "Gemma's Take" needs a new name. Proposed: **"The Take"** (or "The Guide's Take").

| File | Line | Current | Proposed |
|------|------|---------|----------|
| `backend/app/services/guidance.py` | 1 (docstring) | `"'Gemma's Take'"` | `"'FutureProof's Take'"` |
| `backend/app/services/guidance.py` | 264 | `"Generate the 'Gemma's Take' narrative"` | `"Generate 'The Take' narrative"` |
| `backend/app/services/report_gen.py` | 138 | `"## Gemma's Take"` | `"## FutureProof's Take"` |
| `backend/app/services/report_gen.py` | 285 | `"Gemma's Take and skill recommendations are AI-generated..."` | `"The Take and skill recommendations are AI-generated..."` |
| `backend/app/services/report_gen.py` | 295 | `"...powered by Gemma 4."` | `"...powered by Gemma 4. Gemma is a trademark of Google LLC."` |
| `backend/app/services/report_gen.py` | 402 | `"...generated by FutureProof (Gemma 4)..."` | `"...generated by FutureProof, powered by Gemma 4. Gemma is a trademark of Google LLC."` |
| `backend/app/routers/ask_gemma_router.py` | 5 | `"(entry point under "Gemma's Take")"` | `"(entry point under "The Take")"` |
| `frontend/src/components/build-results/NarrativeTimeline.tsx` | 87 | `"Gemma's Summary"` | `"The Take"` |
| `frontend/src/i18n/strings.ts` (about blurb) | 549 | `"...writes Gemma's Take..."` | `"...writes The Take..."` |

---

### Table F — Attribution Statement (NEW — add these)

The following attribution must be added:

> **Gemma is a trademark of Google LLC.**

| File | Where to Add | Implementation |
|------|-------------|----------------|
| `frontend/src/screens/AboutScreen.tsx` | Below the Gemma 4 source card, or in a footer section | Small `text-xs text-secondary` line |
| `frontend/src/components/horizon/HorizonFooter.tsx` | Next to "Submitted to Gemma 4 Good" line | Append to existing line or add below |
| `backend/app/services/report_gen.py` | PDF disclaimer section | Add to existing disclaimer text |
| `README.md` | Bottom of file, in the acknowledgments/license area | Add as a line after "Built on Gemma 4 by Google DeepMind" |

---

### Table G — PDF Report (`backend/app/services/report_gen.py`)

| Line | Current | Proposed |
|------|---------|----------|
| 138 | `"## Gemma's Take"` | `"## FutureProof's Take"` |
| 285 | `"- Gemma's Take and skill recommendations are AI-generated..."` | `"- The Take and skill recommendations are AI-generated using Gemma 4..."` |
| 295 | `"- This report is generated by FutureProof, powered by Gemma 4. "` | `"- This report is generated by FutureProof, powered by Gemma 4. Gemma is a trademark of Google LLC."` |
| 402 | `"This comparison is generated by FutureProof (Gemma 4) and ..."` | `"This comparison is generated by FutureProof, powered by Gemma 4. Gemma is a trademark of Google LLC. ..."` |

---

### Table H — README.md

The README has 78 Gemma references. Most are appropriate tech documentation. Changes needed:

| Section | Current | Proposed | Notes |
|---------|---------|----------|-------|
| Acknowledgments (bottom) | `"Built on Gemma 4 by Google DeepMind."` | `"Built on Gemma 4 by Google DeepMind. Gemma is a trademark of Google LLC."` | Attribution |
| "Why Gemma 4 matters" body | `"Gemma routes, explains, narrates."` | No change | Factual, describing the model's role |
| Feature bullets | `"Gemma generates 3–5 career-grounded stat-delta buffs"` | No change | Factual tech description |
| "How Gemma 4 is used" table | `"What Gemma does"` column | No change | Factual |
| Row 4 | `"Gemma's Take"` | `"The Take"` | Feature rename |
| Row 10 | `"Ask Gemma"` | `"Ask the Guide"` | Feature rename |

> The README references to Gemma are overwhelmingly factual ("Gemma 4 resolves intent," "Gemma calls ten governed MCP tools"). These are compliant — they describe what the model does, not personify it as a character. Only the feature names ("Gemma's Take," "Ask Gemma") need updating.

---

## §3 Testing Impact Analysis

### Existing Tests at Risk

String-value assertions will fail after the copy changes. These are **expected** failures requiring test updates.

| Test File | Risk | Reason |
|-----------|------|--------|
| `frontend/src/components/landing/OllamaSection.test.tsx` | High | Asserts "Gemma's coaching" |
| `frontend/src/components/gauntlet/NextSteps.test.tsx` | High | Asserts "gemma is writing your action plan" |
| `frontend/src/components/menu/GemmaTrace.test.tsx` | High | Asserts "Gemma checked" / "Gemma is looking" |
| `frontend/src/components/horizon/HorizonFooter.test.tsx` | Med | Asserts "Built with Gemma 4" |
| `frontend/src/components/menu/GemmaChat.test.tsx` | Med | May assert on string values |
| `frontend/src/components/AskGemmaChipRow.test.tsx` | Med | Default aria-label "Ask Gemma about this screen" |
| `frontend/src/components/menu/AskGemmaFab.test.tsx` | Med | May assert on label text |
| `frontend/src/components/build-results/BossBand.test.tsx` | Med | May assert "Ask Gemma" aria labels |
| `frontend/src/i18n/strings.test.ts` | Low | Tests string structure, not values |
| `frontend/src/screens/AboutScreen.test.tsx` | Low | May assert on source card content |
| `backend/tests/` (various) | Med | System prompt assertions in voice contract tests |

### Authorized Test Modifications

All test changes are string-value updates only — no logic changes, no test deletions, no new skip markers.

### New Tests Required

| Priority | Test | What It Validates |
|----------|------|-------------------|
| P0 | Assert trademark line in About screen | Attribution statement renders |
| P0 | Assert trademark line in PDF disclaimers | Attribution in exported documents |
| P1 | Assert no user-facing string contains "Ask Gemma" or "Gemma is" | Regression gate for persona leaks |

---

## §5 Architecture Review

**Status:** SKIPPED — No architectural changes. Copy/string changes only.

---

## §6 Implementation Log

**Status:** PENDING

---

## §7 Test Coverage

**Status:** PENDING

---

## §8 Reviews

**Status:** PENDING

---

## §9 Verification

**Status:** PENDING

---

## §10 Discussion

```
[2026-05-12 00:15] @claude → @jeff
Key decision needed: confirm "the Guide" as the replacement persona name.
Alternatives: "Coach," "Advisor," "Scout," "Compass," "the Reader."
This choice propagates to ~30 user-facing strings × 3 languages,
8 system prompts, and the feature name "Gemma's Take" → "The Take" or "The Guide's Take."
```

---

## §11 Final Notes

**Human Review:** PENDING

**Scope boundary:** This spec deliberately excludes internal code identifiers (file names, variable names, CSS classes, type names). Renaming `ask_gemma.py` → `ask_guide.py` would be a large refactor with high test breakage risk for zero user-facing benefit. The guidelines care about what users and judges see, not what developers name their Python files.

**Deadline pressure:** May 18 submission. This is a copy pass — no features, no architecture. Estimated implementation: 2–4 hours including test updates.
