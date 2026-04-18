# Hackathon Ship Plan — Gemma 4 Good Submission

*Date: 2026-04-17 · Deadline: 2026-05-18 · Runway: 4 weeks, 1 day*

Synthesizes:
- `reports/marketing-landing-scope-2026-04-17.md` (external marketing surfaces)
- `reports/in-app-copy-audit-2026-04-17.md` (in-app UX + Gemma prompt register)

Policy source: `docs/reference/voice-guide.md`. Feature ground truth: `docs/futureproof_hackathon_prd_v8.md`. Codebase facts: `CLAUDE.md`.

---

## 1. Executive Summary

The product ships. The voice does not — yet. In four weeks we have to build six external marketing surfaces from scratch (landing page, Kaggle writeup, 3-min video, public README, cover image, screenshot gallery) **and** fix a voice-drift problem that's worst at the runtime layer: every live Gemma system prompt currently pins the model to "empowering career coach for a high school student," which is exactly the register the voice guide bans. Fixing the Gemma prompts is the single highest-leverage move — every boss narrative and "Gemma's Take" in the demo video improves from one day of work in `backend/app/services/`. The in-app UI has ten concrete outcome-vocabulary drifts (`LOSS` vs `LOSE`, `Loans Boss` vs `Fight Student Loans`, `Growth Potential` vs `Growth Outlook`) that are visible in every boss card, every share frame, and every screenshot we'd put on the landing page — so fixing in-app copy is a hard precondition for capturing marketing screenshots. The claims audit surfaces three stale dataset counts (`consumable.ai_exposure` in `CLAUDE.md` says 342; shipped reality is 815) and one live claim risk (the cloud demo cannot truthfully claim it "runs on Ollama" — only that it *can*). Net: P0 is tight but fits the runway if we start voice fixes in week 1 and don't slip the video to week 4. If anything slips, the live-Ollama video demo is the first thing to de-scope; the Ollama-track pitch can survive on screenshots plus code.

---

## 2. Four-Week Calendar

Owners: **Jeff** = human builder. **Claude Code** = general agent tasking via spec or direct request. **fp-copywriter** = voice enforcement agent. **fp-architect / fp-builder** = normal pipeline agents.

### Week 1 — 2026-04-20 → 2026-04-26
**Theme: Fix the voice at the source. Stop the demo from parroting "empowering."**

| Item | Surface | Owner | Effort |
|---|---|---|---|
| Rewrite `guidance.py:28` `_SYSTEM` (Gemma's Take) | in-app | Claude Code | 0.5d |
| Rewrite `boss_fights.py:515` `_NARRATIVE_SYSTEM` | in-app | Claude Code | 0.5d |
| Rewrite `next_steps.py:18` `_SYSTEM` | in-app | Claude Code | 0.5d |
| Fix all `LOSS → LOSE` drift (`BossFightCard`, `FinalBoss`) | in-app | Claude Code | 0.5d |
| Drop ✦ from WIN pill | in-app | Claude Code | 0.1d |
| `Loans Boss → Fight Student Loans` (three sites) | in-app | Claude Code | 0.25d |
| `Growth Potential → Growth Outlook` (`statExplanations.ts:58`) | in-app | Claude Code | 0.1d |
| `TreeNodeDetailPanel.tsx:19-25` → `BOSS_METADATA` | in-app | Claude Code | 0.25d |
| `CompareView.tsx:86` — replace banned fallback | in-app | Claude Code | 0.1d |
| Stale doc cleanup: `CLAUDE.md` Gold Zone table + PRD §Data Pipeline | both | Jeff | 0.5d |
| Domain + cloud-deploy decision (Q1, Q2) | both | Jeff | blocking |
| Bogdan / Unsloth track confirmation (Q3) | marketing | Jeff | blocking |

**Deliverable at week's end:** a live dev build where every Gemma narrative in a fresh gauntlet reads in-voice. The demo video can start screen-capturing against a truthful, locked-vocab runtime.

---

### Week 2 — 2026-04-27 → 2026-05-03
**Theme: Replace the wrong README. Ship the landing page copy. Capture screenshots.**

| Item | Surface | Owner | Effort |
|---|---|---|---|
| Move current `README.md` → `docs/data-pipeline-readme.md` | marketing | Jeff | 0.25d |
| Write new public-facing `README.md` (judge-oriented) | marketing | Jeff + fp-copywriter review | 1d |
| Ollama quickstart as first-class README section | marketing | Jeff | (within README) |
| Landing page build — copy from marketing report §2 | marketing | Jeff + frontend dev | 2d |
| Rewrite `LandingScreen.tsx:74` subhead (drop "powered by") | both | Claude Code | 0.1d |
| Rewrite `RevealScreen.tsx:265` `Fight the Bosses → Enter the Gauntlet` | in-app | Claude Code | 0.1d |
| Rewrite `LoadingScreen.tsx:33` banned fallback | in-app | Claude Code | 0.1d |
| Rewrite Final Boss verdicts (`GauntletScreen.tsx:29-38`) | in-app | Claude Code | 0.25d |
| Rewrite `ProfileScreen.tsx:215` `Let's go → Continue` | in-app | Claude Code | 0.1d |
| Specific errors: `ProfileScreen.tsx:86,104`, `GemmaChat.tsx:81`, `CareerPickScreen.tsx:140-150` | in-app | Claude Code | 0.5d |
| `CompareView.tsx:152` → `Gemma's take on the tradeoffs` | in-app | Claude Code | 0.1d |
| Capture 6-8 screenshots from the now-voice-compliant live app | marketing | Jeff | 0.5d |
| Capture Kaggle cover image (pentagon glow + tagline) | marketing | Jeff + design | 0.5d |
| Rewrite `_CHAT_SYSTEM`, `skill_recs`, `skill_pool`, `career_tiering` prompts (P1 Gemma fixes) | in-app | Claude Code | 1d |

**Deliverable at week's end:** landing page deployed to staging. README merged to main. Screenshot gallery captured. Gemma runtime fully in voice.

---

### Week 3 — 2026-05-04 → 2026-05-10
**Theme: Kaggle writeup. Video production. Disclaimers.**

| Item | Surface | Owner | Effort |
|---|---|---|---|
| Kaggle writeup draft (1,500 words) | marketing | Jeff | 2d |
| fp-copywriter review pass on writeup | marketing | fp-copywriter | 0.5d |
| Writeup edit + tighten to exact word budget | marketing | Jeff | 0.5d |
| Record 3-min demo video scenes 1–4 | marketing | Jeff | 1d |
| Record Ollama split-screen (scene 5) on a second physical machine | marketing | Jeff | 0.5d |
| Video edit pass 1 | marketing | Jeff | 1d |
| Disclaimers page (footer-linked, in-voice) | both | Jeff | 0.25d |
| Deploy landing page to production domain | marketing | Jeff | 0.25d |
| Effort-label reconciliation decision (Q7) | in-app | Jeff product call | 0.1d |
| `CareerDetail.tsx:293-297` MEMORY.md scope decision | in-app | Jeff product call | 0.1d |

**Deliverable at week's end:** writeup ready for final edit. Video cut 1 viewable. Landing page live. Disclaimers published.

---

### Week 4 — 2026-05-11 → 2026-05-18
**Theme: Submission buffer. Final polish. Nothing new.**

| Item | Surface | Owner | Effort |
|---|---|---|---|
| Video edit pass 2 (captions, audio mix, final cut) | marketing | Jeff | 1d |
| Writeup final read-through + submission to Kaggle | marketing | Jeff | 0.5d |
| Submit Kaggle entry with cover + gallery + video + writeup + GitHub link | marketing | Jeff | 0.25d |
| Launch social posts (Twitter/X, LinkedIn, Bluesky) | marketing | Jeff | 0.25d |
| P2 sweep: landing CTA trim, `Welcome back` drop, `Reading your builds…`, `TreeFallback` honest copy, `MajorInput` polish | in-app | Claude Code | 1d |
| Judge outreach blurb (if appropriate per Q3) | marketing | Jeff | 0.25d |
| End-to-end smoke test of live demo + Ollama path | both | Jeff + fp-builder | 0.5d |
| Architecture diagram polish (P2) | marketing | Jeff | 0.25d |
| **Buffer** — bug-hunt + unplanned | — | — | 1.5d |

**Hard rule for week 4:** nothing new ships. Only polish, bug-fix, and the submission itself.

---

### Runway Honesty Check

P0 effort across both reports sums to roughly 12–16 working days. The calendar above distributes 11 working days of P0 + ~3 days of P1 across weeks 1–3, leaving week 4 mostly as buffer. This fits **if**:

- The Gemma prompt rewrites land in week 1 without regressions (they will surface in every demo screenshot from week 2 onward — if they're late, every downstream asset has to be re-shot).
- Jeff unblocks Q1 (domain), Q2 (where the live demo runs), and Q3 (Unsloth track) in week 1.
- Video production doesn't slip past week 3. If it does, video becomes the gating item for submission and week 4 buffer evaporates.

**Escalation trigger:** if by end of week 2 the landing page isn't on staging and screenshots aren't captured, cut P1 items and move P0 writeup forward one week.

---

## 3. Unified Prioritized Punch List

Merged from both reports. Priority ordering adjudicates as follows: when both reports agree, the item keeps its priority. When only the marketing report lists an item, the marketing-reviewer lens (submission readiness) governs. When only the copywriter lists an item, the copywriter lens (voice drift severity) governs. Tags: `[in-app]` = runtime UX or prompt, `[marketing]` = external surface, `[both]` = cross-cutting.

### P0 — Submission-blocking or voice-spine-breaking

1. **Rewrite `guidance.py:28` `_SYSTEM` — Gemma's Take prompt.** `[in-app]` Drop "empowering" and "6th grade reading level," lock vocabulary, pin register. Every reveal narrative depends on this.
2. **Rewrite `boss_fights.py:515` `_NARRATIVE_SYSTEM` — boss narratives.** `[in-app]` Per-outcome register (matter-of-fact WIN, contemplative LOSE).
3. **Rewrite `next_steps.py:18` `_SYSTEM`.** `[in-app]` Drop "empowering" (twice), pin imperative verb-led register.
4. **Standardize outcome vocabulary to `WIN / DRAW / LOSE`.** `[both]` `BossFightCard.tsx:33-43`, `FinalBoss.tsx:14-18`, `SaveConfirmation.tsx:107`, `BuildCard.tsx:83-87`. Also affects landing page copy, screenshots, Kaggle writeup, and video captions — fixing in-app fixes all downstream surfaces.
5. **Drop ✦ from WIN pill.** `[in-app]` `BossFightCard.tsx:34`. Voice guide: "win is matter-of-fact."
6. **`Loans Boss → Fight Student Loans`.** `[in-app]` `EffortLoansPanel.tsx:57-67` (twice), `statExplanations.ts:38`. Locked vocabulary.
7. **`Growth Potential → Growth Outlook`.** `[in-app]` `statExplanations.ts:58`. Locked stat name.
8. **`TreeNodeDetailPanel.tsx:19-25` boss labels → `BOSS_METADATA` import.** `[in-app]` Four of five boss labels drift from locked vocab.
9. **`CompareView.tsx:86` — replace `"Something went wrong."` fallback.** `[in-app]` Voice-guide banned phrase.
10. **Public-facing GitHub README.** `[marketing]` Current README is a Brightsmith data-pipeline doc. Replace with judge-oriented intro + Ollama quickstart. Move current content to `docs/data-pipeline-readme.md`.
11. **Public landing page.** `[marketing]` Built and deployed per marketing report §2. ~800 words, dark-first Brightpath tokens, 4 live-app screenshots, live demo link.
12. **Kaggle writeup (1,500 words).** `[marketing]` Architecture, Gemma 4 usage (10 surfaces), data challenges, Ollama story, Karpathy divergence finding. Lead with equity spine.
13. **3-min demo video.** `[marketing]` ~450 spoken words. Live-app captures (post-voice-fix). Ollama split-screen scene on a second physical machine. End on equity line.
14. **Kaggle cover image.** `[marketing]` 16:9, pentagon glow, "A college degree isn't a destination." tagline. Same palette as app.
15. **Screenshot gallery (6–8).** `[marketing]` Captured from voice-fixed live app. Must be captured *after* week-1 in-app fixes land.
16. **Disclaimers page.** `[marketing]` Required per PRD §Disclaimers. In-voice. Linked from landing footer and in-app footer.
17. **Stale doc cleanup.** `[both]` Update `CLAUDE.md` `consumable.ai_exposure` row count (342 → 815), PRD §Data Pipeline same, ingestor count (6 → 7 with Anthropic). Judges read `CLAUDE.md`.

### P1 — Hurts polish, judging score, or credibility

18. **Rewrite `guidance.py:142` `_CHAT_SYSTEM` (Ask Gemma).** `[in-app]` Peer register, drop "empowering" and "high school student" framing.
19. **`skill_recs.py:23` — drop "empowering."** `[in-app]`
20. **`skill_pool.py:349` — add anti-pattern block.** `[in-app]`
21. **`career_tiering.py:56` — lock tier names in prompt.** `[in-app]`
22. **`LandingScreen.tsx:74` subhead rewrite.** `[both]` Drop "powered by real data and Gemma AI" press-release register.
23. **`RevealScreen.tsx:265` `Fight the Bosses → Enter the Gauntlet`.** `[in-app]`
24. **`LoadingScreen.tsx:33` — rewrite banned fallback.** `[in-app]`
25. **`GauntletScreen.tsx:29-38` — Final Boss verdicts.** `[in-app]` Drop mandatory CAPS, soften "VULNERABLE BUILD" to "Losses outweigh wins."
26. **`FinalBoss.tsx:116` — preserve `Fight ` prefix.** `[in-app]` Stack icon above locked phrase instead of stripping.
27. **`ProfileScreen.tsx:215` `Let's go → Continue`.** `[in-app]`
28. **Specific error copy.** `[in-app]` `ProfileScreen.tsx:86, 104`; `GemmaChat.tsx:81`; `CareerPickScreen.tsx:140-150`; `MajorInput.tsx:277` (drop "Please go back").
29. **`CompareView.tsx:152` `Gemma's comparison → Gemma's take on the tradeoffs`.** `[in-app]` Natural scaling of `Gemma's Take`.
30. **`SaveWrappedScreen.tsx:198` — replace banned fallback.** `[in-app]`
31. **Effort-label set reconciliation.** `[in-app]` Voice guide locks 3 stops (Working / Balanced / All-in). UI has 5. Product call.
32. **`CareerDetail.tsx:293-297` — confirm MEMORY.md scope.** `[in-app]` Product call on whether CIP substitution caveat extends to detail panels.
33. **Launch social posts.** `[marketing]` One idea per platform. No threads.
34. **Judge outreach blurb.** `[marketing]` Optional, depending on Q3.
35. **Claims tightening.** `[marketing]` "Six boss fights" → "Five bosses and a final composite — Fight the Future." Never say "runs on Ollama" for the cloud demo; say "can run on Ollama" or "the same codebase runs local or cloud."

### P2 — Nice to have, demo-week polish

36. **`LandingScreen.tsx:87` CTA trim to `Start ✦`.** `[in-app]`
37. **`ProfileScreen.tsx:128` `We'll call you → For this session, you're`.** `[in-app]`
38. **`MajorInput.tsx:466` `Let's find the right one → Pick the program that fits`.** `[in-app]`
39. **`MajorInput.tsx:185` `your input → what you typed`.** `[in-app]`
40. **`SchoolSearch.tsx:46` `Having trouble → Search is down`.** `[in-app]`
41. **`CareerPickScreen.tsx:124-126` subtitle tightening.** `[in-app]`
42. **`TreeFallback.tsx:13` — honest data-gap copy.** `[in-app]`
43. **`MenuScreen.tsx:166` — drop "Welcome back."** `[in-app]`
44. **`MenuScreen.tsx:180` `Loading → Reading your builds` for parity.** `[in-app]`
45. **`GauntletCTA.tsx:36` — reconcile "Back to My Build" casing.** `[in-app]`
46. **Missing surfaces:** backend-offline global banner; Gemma-backend settings screen (or strip "in settings" language from errors); StatTutorial skip confirmation; compare-disabled hint; school-search pre-input hint. `[in-app]`
47. **Architecture diagram (non-ASCII).** `[marketing]`
48. **Press/judge FAQ one-pager.** `[marketing]`
49. **Submission post-mortem blog.** Post-hackathon. Skip.

---

## 4. Preserved Copywriter Technical Fixes (Verbatim)

The prompt rewrites below are ready-to-paste. They are the single highest-leverage fixes in the audit — every downstream Gemma narrative in the demo video improves. Reproduced verbatim from `reports/in-app-copy-audit-2026-04-17.md`.

### 4.1 P0 — `guidance.py:28-39` (`_SYSTEM`, Gemma's Take)

**Current:**
> You are a career coach helping a high school student evaluate their college and major choice. You are direct, specific, and empowering. You never tell a student their path is doomed — you tell them what to do about their weaknesses. You reference the student's specific school, major, and the real dollar figures provided. NEVER reference raw stat scores like 'ROI 9/10' or 'ERN 7' — students don't know what those mean. Instead explain in real-world terms: salary amounts, debt levels, job growth trends, AI risk. You never use bullet points. You never start with 'Great choice' or similar platitudes. Write conversationally, in 4-6 sentences, at a 6th grade reading level.

**Issues:**
1. `"empowering"` is on the voice-guide anti-pattern list. Gemma will pick it up.
2. `"high school student"` — voice guide says peer, not pupil. Frames Gemma-the-narrator down.
3. `"6th grade reading level"` — this isn't in the voice guide. It produces soft, simplified outputs that read as patronizing. The voice guide doesn't call for dumbing down — it calls for short, concrete sentences.
4. Doesn't lock the vocabulary (no mention of `WIN/DRAW/LOSE`, the boss names, tier names, receipts).
5. No register pin — "contemplative on loss, matter-of-fact on win" isn't specified.

**Proposed rewrite:**

```python
_SYSTEM = (
    "You are Gemma — the data-honest coaching voice inside FutureProof, "
    "an RPG-style career planning tool. The student in front of you is "
    "making a six-figure decision and they have 700K rows of public data "
    "behind every number you cite. Act like it.\n\n"
    "Register: cool, confident, data-honest. Coach, not cheerleader. "
    "Peer, not pupil. Matter-of-fact when a fight is won. Contemplative "
    "when a fight is lost — never punishing, never celebratory. Never "
    "tell a student their path is doomed; name what broke and the lever "
    "they can actually pull.\n\n"
    "Vocabulary you MUST use exactly: WIN / DRAW / LOSE (not victory/tie/"
    "defeat). Fight AI / Fight Student Loans / Fight the Market / Fight "
    "Burnout / Fight the Ceiling / Fight the Future (always 'Fight [X]'). "
    "ERN, ROI, RES, GRW, HMN (stat codes). Receipts (not 'sources').\n\n"
    "Voice rules:\n"
    "- Short sentences. Concrete nouns. Zero filler.\n"
    "- Never use: empowering, journey, unlock, transform, passion, dream "
    "career, game-changing, limitless, your future awaits.\n"
    "- No exclamation points. No 'oops'. No 'great choice'. No 'as an AI'.\n"
    "- Never reference raw stat scores ('ROI 9/10'). Translate to real-"
    "world dollars, debt, and job-market terms using the figures provided.\n"
    "- No bullet points. No markdown. Plain prose, 4-6 sentences.\n\n"
    "Anchor to the receipts. The student will see the raw numbers in a "
    "panel next to your take. Inflating, handwaving, or softening is "
    "immediately visible. Say what the data says."
)
```

**Impact:** Every `Gemma's Take` in the app gets tighter, more on-brand, and stops using "empowering." This is the single highest-leverage fix in the audit.

---

### 4.2 P0 — `boss_fights.py:515-520` (`_NARRATIVE_SYSTEM`, boss narratives)

**Current:**
> You are a career coach narrating boss fights in an RPG-style career planning tool for high school students. You are direct, specific, and empowering — never doom. Keep responses to 3-4 sentences. Do NOT use bullet points. Do NOT start with platitudes.

**Issues:**
- Same "empowering" trap.
- No register differentiation for WIN vs LOSE narratives. Voice guide: "contemplative on loss, matter-of-fact on win" — explicit.
- No vocabulary lock.

**Proposed rewrite:**

```python
_NARRATIVE_SYSTEM = (
    "You are Gemma, narrating a single boss fight in FutureProof's "
    "career gauntlet. The student just saw their WIN / DRAW / LOSE pill "
    "render next to a raw score and the thresholds — your narrative "
    "sits under that, explaining what it means in the real world.\n\n"
    "Register by outcome:\n"
    "- WIN: matter-of-fact. Name what beat the boss. Give one concrete "
    "action to keep the advantage. Never celebratory.\n"
    "- DRAW: direct. Name the stalemate in one sentence. Give one lever "
    "that could push it toward a win.\n"
    "- LOSE: contemplative. Name what broke down in real-world terms "
    "(dollars, debt, job trends, AI exposure). Give one concrete pivot. "
    "Never punishing, never doom-framing.\n\n"
    "Vocabulary: always 'Fight [X]' for the boss name. WIN / DRAW / "
    "LOSE in all caps only when citing the outcome noun. Stat codes "
    "ERN/ROI/RES/GRW/HMN; translate to dollars and plain language, "
    "never '9/10'.\n\n"
    "Anti-patterns: no 'empowering', no 'journey', no exclamation "
    "points, no bullet points, no 'great news', no 'as an AI'. Exactly "
    "2-3 sentences of prose. The student sees your sentences right "
    "next to the raw data — if you inflate or soften, they'll spot it."
)
```

**Impact:** Fixes the register-flip problem where a LOSE narrative currently reads slightly upbeat (because "empowering" is the pin).

---

### 4.3 P0 — `next_steps.py:18-34` (`_SYSTEM`, Next Steps)

**Current:**
> You are a career planning advisor writing an action checklist for a high school student who just evaluated a college+major+career path. Drop all RPG and game metaphors — write as a knowledgeable, empowering advisor speaking plainly. ...Tone: empowering, specific, actionable. Respectful of parents — not adversarial. ...

**Issues:**
- Twice says "empowering."
- The metaphor-drop instruction is correct (matches voice guide) — keep that.
- No explicit register lock: Next Steps is imperative, verb-led.

**Proposed rewrite (keep the 4-section structure, overwrite the tone block):**

```python
_SYSTEM = (
    "You are Gemma writing a 'Your Next Steps' action checklist for a "
    "student who just finished their FutureProof gauntlet. This is the "
    "one surface where you drop the RPG metaphor entirely — no 'boss', "
    "no 'fight', no 'build', no 'stats'. Speak as a knowledgeable peer "
    "advisor with receipts.\n\n"
    "Register: imperative and verb-led. Every item starts with a verb "
    "('Take', 'Email', 'Enroll in', 'Ask', 'Verify', 'Search'). Each "
    "item must cite something concrete from the student's session — "
    "their school name, major, occupation title, a salary dollar "
    "figure, a debt amount, or a fight outcome in plain language "
    "('the fight where AI exposure came up short').\n\n"
    "Anti-patterns: no 'empowering', no 'journey', no 'your future "
    "awaits', no exclamation points, no filler like 'research your "
    "options'. No raw stat scores ('ROI 9/10') — translate to dollars "
    "or plain English. When the data shows a real weakness, name it "
    "honestly and pair it with the mitigation. Arm the student with "
    "facts, not rhetoric.\n\n"
    "Output format: four markdown ## sections as specified below, "
    "3-5 numbered items per section, each verb-led. No preamble, no "
    "closing. Concise — one or two sentences per item."
)
```

---

### 4.4 P1 — `guidance.py:142-159` (`_CHAT_SYSTEM`, Ask Gemma)

**Current** has same "empowering" drift plus "high school student" framing.

**Proposed rewrite:**

```python
_CHAT_SYSTEM = (
    "You are Gemma inside FutureProof's 'Ask Gemma' panel. The student "
    "has already completed a build — their school, major, career, "
    "salary data, fight outcomes, skill pool, and branch tree are "
    "loaded in the context below. Every answer references that data.\n\n"
    "Register: cool, data-honest, peer-to-peer. Short sentences. "
    "Concrete answers. 4-8 sentences unless the student asks for more. "
    "No 'as an AI', no 'great question', no 'empowering', no 'journey'. "
    "No exclamation points.\n\n"
    "When asked 'what if' (different school, different major), give "
    "your best read of the tradeoff based on the loaded build and note "
    "that exact numbers require a new build. Never invent figures. "
    "If you don't know, say so plainly.\n\n"
    "Vocabulary: 'Fight [X]' for boss names, WIN/DRAW/LOSE for "
    "outcomes, ERN/ROI/RES/GRW/HMN translated to dollars and plain "
    "English. Call the saved profile+school+major+career combinations "
    "'builds', not 'profiles' or 'plans'."
)
```

---

### 4.5 P1 — `career_tiering.py:56-64` (`_SYSTEM`)

**Current is mostly fine** — already says "factual and direct" and "No fake percentages." Small polish:

**Add at the end:**
> Tier names: Common / Less Common / Stretch (exactly those three, lowercase headers in output — COMMON / LESS_COMMON / STRETCH per format).

**Rationale:** Locks tier names. Currently Gemma can output minor variants which the parser silently eats.

---

### 4.6 P1 — `skill_recs.py:23-34` and `skill_pool.py:349-358`

**Current skill_recs:**
> You generate skill and coursework recommendations for high school students choosing a college major. You are concrete, specific, and empowering.

**Drop "empowering."** Replace with `"You are concrete and specific. Every recommendation names something the student could enroll in, email, or start within 30 days at their current school."`

**Current skill_pool** is already cleaner — "grounded in the student's actual school, major, and career path — never generic" is on-brand. Small polish: add `"Never use 'journey', 'unlock', 'empower', or exclamation points in titles or rationales."` at the end.

---

### 4.7 In-App UI Rewrites — Ready-to-Paste

From the copywriter audit, these are the concrete before/after strings. Each is tagged with file:line for direct Edit-tool application.

**P0 UI fixes:**

- `BossFightCard.tsx:33-48` — outcome pills:
  - `"WIN ✦"` → `"WIN"` (drop sparkle)
  - `"LOSS"` → `"LOSE"`
  - `"DRAW"` → keep
  - `"NO DATA"` → keep
- `FinalBoss.tsx:14-18` — `"LOSS"` → `"LOSE"`
- `SaveConfirmation.tsx:107` — align shorthand to `W · D · L`
- `BuildCard.tsx:83-87` — align shorthand to `W · D · L`
- `statExplanations.ts:58` — `"Growth Potential"` → `"Growth Outlook"`
- `statExplanations.ts:37-38` — `"...that's the Student Loans Boss."` → `"...that's Fight Student Loans."`
- `EffortLoansPanel.tsx:57-67` — `"Loans Boss auto-win"` → `"Fight Student Loans is a WIN"`; `"Loans Boss at full difficulty"` → `"Fight Student Loans at full difficulty"`
- `TreeNodeDetailPanel.tsx:19-25` — replace ad-hoc boss label map with `import { BOSS_METADATA } from '@/lib/bossMetadata'` (existing file already has the correct strings)
- `CompareView.tsx:86` — fallback `"Something went wrong."` → `"Couldn't load the comparison. The compare API didn't respond."`

**P1 UI fixes:**

- `LandingScreen.tsx:74` subhead — `"See where every path leads — powered by real data and Gemma AI."` → `"See where your degree actually leads. 700K rows of public data, zero admissions brochure."`
- `RevealScreen.tsx:265` — `"Fight the Bosses →"` → `"Enter the Gauntlet →"`
- `LoadingScreen.tsx:33` — `"Something went wrong — let's try again"` → `"Build failed. Tap retry to try again."`
- `GauntletScreen.tsx:29-38` — Final Boss verdicts:
  - `"DOMINANT BUILD — strong across the board."` → `"Strong build. Wins across every fight."`
  - `"SOLID BUILD with minor soft spots."` → `"Solid build with minor soft spots."`
  - `"SOLID BUILD with a gap."` → `"Solid build, with one gap to close."`
  - `"MIXED BUILD — wins and losses cancel out; play to strengths."` → `"Mixed result. Wins and losses cancel out — play to your strengths."`
  - `"VULNERABLE BUILD — losses outweigh wins; active mitigation required."` → `"Losses outweigh wins. This path needs active mitigation."`
- `FinalBoss.tsx:116` — do not strip `"Fight "` prefix from boss label; stack icon above locked phrase if width requires it.
- `ProfileScreen.tsx:215` — `"Let's go →"` → `"Continue →"`
- `ProfileScreen.tsx:86` — `"Something went wrong. Try again."` → `"Couldn't reach the profile service. Try again."`
- `CareerPickScreen.tsx:140-150` — replace raw `{error}` render with `"Couldn't tier the career paths. Try again, or pick a different major."`
- `MajorInput.tsx:277` — `"No programs available. Please go back and try a different school."` → `"This school doesn't have program data. Try a different school."`
- `GemmaChat.tsx:81` — `"Gemma couldn't respond."` → `"Gemma didn't respond in time. Try your question again, or swap the backend in settings."` (only if a settings screen exists; otherwise strip the "in settings" phrase)
- `CompareView.tsx:152` — `"Gemma's comparison"` → `"Gemma's take on the tradeoffs"`
- `SaveWrappedScreen.tsx:198` fallback — `"Something went wrong while rendering your frames."` → `"The renderer didn't respond. Try again, or skip to the menu."`

**P2 UI fixes:**

- `LandingScreen.tsx:87` — CTA `"See where your path leads ✦"` → `"Start ✦"`
- `ProfileScreen.tsx:128` — `"We'll call you"` → `"For this session, you're"`
- `MajorInput.tsx:466` — `"Let's find the right one"` → `"Pick the program that fits"`
- `MajorInput.tsx:185` — `"Gemma is matching your input..."` → `"Gemma is matching what you typed..."`
- `SchoolSearch.tsx:46` — `"Having trouble searching. Try again in a moment."` → `"Search is down. Try again in a moment."`
- `TreeFallback.tsx:13` — `"We're mapping career branches for {careerTitle}. Check back soon."` → `"No branching data yet for {careerTitle}. O*NET hasn't published pathway matches for this occupation."`
- `MenuScreen.tsx:166` — `"Welcome back, {profileName} {animalEmoji}"` → `"{profileName} {animalEmoji}"`
- `MenuScreen.tsx:180` — `"Loading your builds…"` → `"Reading your builds…"`

---

### 4.8 Canonical Examples to Protect

These surfaces are already voice-perfect. **Do not touch them during the fix-up pass.** Use as reference when rewriting the rest.

- `StructuralLoss.tsx:20-34` — contemplative loss narrative, named threat, next step.
- `LoadingScreen.tsx:12-19` — loading message sequence (`Specing {name}...`, `Crunching salary data...`, etc.).
- `BranchTreeScreen.tsx:133-138` — branch-loading copy with data source cited.
- `SaveConfirmation.tsx:89-117` — build-saved confirmation with stats strip.
- `SaveWrappedScreen.tsx:157-162` — "Developing your wrapped" photography metaphor.
- `NextSteps.tsx:132-134` — metaphor-drop intro.
- `CompareView.tsx:164` — `"Reading the tradeoffs…"`
- `GemmaChat.tsx:13-17` — chat starter prompts.
- `intent.py:57-80` (`_AUDIT_SYSTEM_PROMPT`) — "Be real with them. This is a $100K+ decision."
- Every data footer / receipt block — dry `Label: value` format.

---

## 5. Cross-Surface Dependency Map

Items that show up in both reports — fixing once fixes multiple surfaces. Order matters: the in-app fix must land before the marketing screenshot is captured.

| Shared concern | In-app site(s) | Marketing site(s) | Fix order |
|---|---|---|---|
| `WIN / DRAW / LOSE` outcome vocabulary | `BossFightCard`, `FinalBoss`, `SaveConfirmation`, `BuildCard`, `RiskHeadlineCard`, `TreeNodeDetailPanel` | Landing page boss-fight tile, Kaggle screenshots, video captions, README screenshots, share frames | **In-app first** (week 1). Screenshots re-captured week 2. |
| `Fight [X]` locked boss names | `EffortLoansPanel`, `statExplanations.ts`, `TreeNodeDetailPanel`, `RevealScreen`, `FinalBoss` scorecard | Landing copy Section C ("Fight AI. Fight Student Loans. Fight the Market. Fight Burnout. Fight the Ceiling."), video script, Kaggle writeup | **In-app first.** Marketing copy already uses correct forms; in-app drift is what breaks the visual parity. |
| `Growth Outlook` stat name | `statExplanations.ts`, tutorial, tooltips | Landing page data-sources table, pentagon caption | In-app only surfaces this visibly — fix there. |
| `Gemma's Take` narrative quality | `guidance.py` `_SYSTEM` prompt | Demo video Scene 3 (reveal), Kaggle writeup Gemma-usage section, landing page screenshot caption | **Prompt fix must land week 1** or every demo capture of the reveal screen reads as "empowering career coach" in the video. |
| Boss narrative register (WIN vs LOSE) | `boss_fights.py` `_NARRATIVE_SYSTEM` | Video Scenes 4–5 (gauntlet run, reroll, final boss) | Same — week 1 prompt fix. |
| Next Steps as RPG-metaphor-drop | `next_steps.py` `_SYSTEM` | Video outro, Kaggle writeup closing section | Week 1 prompt fix. |
| Landing subhead voice | `LandingScreen.tsx:74` in-app landing | Marketing landing page Section A hero | Both surfaces use the same voice pin. Fix the in-app subhead, then reuse verbatim on marketing landing. |
| "Powered by Gemma 4 via Ollama" claim | In-app claim at `LandingScreen.tsx:74` | Landing Section E ("Any school can run this on their own hardware"), video Scene 5, README quickstart, Kaggle Ollama section | **Claim-risk item.** The cloud demo cannot truthfully claim it "runs on Ollama" — only that it *can*. Video must demonstrate local Ollama on a second physical machine; landing copy must say "can run" not "runs." |
| Dataset row counts | Receipt panels, `CLAUDE.md` Gold Zone table | Landing Section G ("How we know"), Kaggle writeup data pipeline section | `CLAUDE.md` + PRD cleanup in week 1 prevents judge-read doc drift. |
| Banned fallback `"Something went wrong"` | `LoadingScreen.tsx:33`, `CompareView.tsx:86`, `SaveWrappedScreen.tsx:198` | Any screenshot that surfaces an error path (avoid capturing these for marketing) | In-app fix prevents accidental capture of bad fallbacks for marketing. |
| `Fight the Future` as composite framing | `FinalBoss.tsx:76` (already correct in-app) | Landing copy (currently says "six battles"), video script | Pick "Five bosses and a final composite — Fight the Future." Apply to landing + video. |

**Implication:** the week-1 in-app voice fixes unlock week-2 screenshot capture and week-3 video capture. Do not try to capture marketing assets in parallel with voice fixes — the assets will be wrong.

---

## 6. Top-5 Risks

1. **Gemma-prompt voice drift leaks into the demo video.** If `guidance.py:28`, `boss_fights.py:515`, and `next_steps.py:18` aren't rewritten and verified by end of week 1, every screen capture of a reveal narrative or boss fight in the video will read as generic edtech "empowering" coaching — which is the exact pattern judges are fatigued by. The video is irreplaceable in week 4. **Mitigation:** treat week-1 prompt fixes as the blocking item; do a full gauntlet playthrough on Friday week 1 to verify tone.

2. **Ollama-vs-OpenRouter claim risk.** Landing and README drafts say FutureProof "runs on Ollama" and "no student data leaves the building." These are true *only* for a local Ollama deployment. If the live demo (what the landing page's primary CTA hits) runs on OpenRouter, those claims are misleading as-applied. **Mitigation:** scope the Ollama claim to the deployment, not the demo. Language: "the same codebase runs on Ollama or OpenRouter — flip one environment variable." Video scene 5 must show Ollama running on a second physical machine to back the claim.

3. **Video production slips past week 3.** Video is the longest-pole single deliverable (~4–5 working days end-to-end). If it slides into week 4, it consumes the submission buffer and bugs can't be fixed. **Mitigation:** start scene captures in week 2 off the already-voice-fixed dev build. Don't wait for the final landing page to go live.

4. **Stale CLAUDE.md + PRD numbers on a judge-visible surface.** Judges read `CLAUDE.md` directly — it's linked from the GitHub README. Current `CLAUDE.md` says `consumable.ai_exposure` has 342 rows; shipped reality is 815. PRD §Data Pipeline agrees with the 342 number but the composite spec ships 815. A judge who cross-references is handed a credibility gap. **Mitigation:** week-1 doc cleanup. Non-negotiable.

5. **In-app outcome vocabulary drift still visible at submission.** `BossFightCard` renders `LOSS` in the active UI; the voice guide locks `LOSE`. Same drift lives in the share-frame `Wrapped` output, which means Twitter/LinkedIn launch posts will show inconsistent vocabulary across screenshots vs. video. **Mitigation:** week-1 `LOSS → LOSE` sweep across all six sites. Re-capture any screenshot taken pre-fix.

---

## 7. Open Questions

From the marketing report (unresolved):

1. **Domain.** Is `futureproof.app` owned? If not, what goes on the CTA button's `href`?
2. **Cloud deployment.** Where does the live demo run? If OpenRouter-backed, landing's Ollama section must scope the claim to the software, not the demo. Video must prove local Ollama on a separate machine.
3. **Bogdan / Unsloth track.** Is the fourth track being submitted? Affects track-list copy.
4. **Schools showcased.** ISU is the default example — confirm data populates cleanly and the school won't object. If unsure, pick a less recognizable demo school.
5. **Wrapped share frames.** Confirm the Puppeteer/Playwright pipeline renders clean PNGs — one frame goes in the Kaggle gallery.
6. **Stale doc cleanup.** Confirm the ship sequence: docs before judge-facing links go live.

New from combining the two reports:

7. **Effort-label reconciliation.** UI has 5 stops (`Working two jobs / Working + school / Balanced / Strong focus / All-in`); voice guide locks 3 (`Working / Balanced / All-in`). Product call needed — collapse to 3, or rename middle stops to stay in-family (`Working hard / Working / Balanced / Focused / All-in`).
8. **MEMORY.md scope.** The "no substitution caveat on cards" memory item — does that extend to `CareerDetail.tsx:293-297` detail panels, or cards only? Product call before removing the note.
9. **Settings screen — build or strip?** `GemmaChat.tsx:81` suggests a settings screen exists ("swap the backend in settings"). None ships. Either build a minimal settings surface (P2 effort: 0.5–1d) or strip the "in settings" phrasing from every error message.
10. **Cover image typography.** The 16:9 cover uses the tagline "A college degree isn't a destination." — is there a designer/tool available to produce the final PNG, or does Jeff generate it in Figma / an equivalent tool?
11. **Which machine does the Ollama scene run on?** The video scene 5 requires a second physical laptop running the stack locally. Does one exist with the right specs to run `gemma4:e4b` smoothly on camera?

---

## 8. Appendix — Source Reports

- `reports/marketing-landing-scope-2026-04-17.md` — marketing-reviewer audit: external surfaces, landing page copy draft, claims audit, marketing punch list.
- `reports/in-app-copy-audit-2026-04-17.md` — fp-copywriter audit: per-screen in-app findings, Gemma-prompt rewrites, missing-surface inventory, canonical examples.
- `docs/reference/voice-guide.md` — voice policy source of truth.
- `docs/futureproof_hackathon_prd_v8.md` — Ships / Ships If Time Permits / Does Not Ship ground truth.
- `CLAUDE.md` — dataset counts and pipeline status (contains the stale-count risk flagged in §6 risk 4).

---

*End of ship plan.*
