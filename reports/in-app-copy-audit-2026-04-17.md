# In-App Copy Audit — 2026-04-17

**Auditor:** fp-copywriter
**Scope:** Every in-app surface in `frontend/src/` plus every Gemma system prompt in `backend/app/services/`
**Policy source:** `docs/reference/voice-guide.md`

---

## Executive Summary

FutureProof's copy is already above average for an app at this stage — the locked vocabulary is mostly respected, loading copy has charm (`Specing [name]...`), and `StructuralLoss` is genuinely on-brand. **But the voice guide and the shipped copy drift in four concrete ways that are already visible in the demo.**

1. **The register pin is wrong in every live Gemma prompt.** Four prompts (`guidance._SYSTEM`, `next_steps._SYSTEM`, `skill_recs._SYSTEM`, `boss_fights._NARRATIVE_SYSTEM`) prime Gemma with the banned words *empowering* and *6th grade reading level* and tell it to be a "career coach." That is the single biggest source of output drift — Gemma parrots whatever tone the system prompt sets, and "empowering" is on the voice-guide anti-pattern list.
2. **Outcome language is inconsistent.** The voice guide locks `WIN / DRAW / LOSE`. The UI actually renders `WIN ✦ / LOSS / DRAW` (`BossFightCard.tsx:33-43`) — `LOSS` is a noun; `LOSE` is the verb the guide specifies. Same drift in `FinalBoss.tsx:14-18`, `SaveConfirmation.tsx:107`, `BuildCard.tsx:83-87` (uses `W·L·D` shorthand), and the compare view (`RiskHeadlineCard.tsx:16-20` keeps `LOSE`, so there are now two different conventions in one app).
3. **Stat-tutorial names drift from the voice guide.** The guide locks `GRW = Growth Outlook`. `statExplanations.ts:58` renders `Growth Potential`. The landing pentagon (`PentagonGlow.tsx:4-8`) uses a third naming: `Earnings / ROI / Resilience / Growth / Human`.
4. **There is no locked "Welcome!" anti-pattern violation — but there is a "Welcome back" on MenuScreen.tsx:166.** Minor, but the voice guide lists `Welcome!` in the infantilizing column; "Welcome back, [name]" borders on that register. Low priority but worth a rewrite.

What's working: every error has a next step (ProfileScreen, SchoolSearch, BranchTreeScreen, MenuScreen), the `StructuralLoss` copy is pitch-perfect, Ask Gemma's starter questions are specific and well-phrased, and `BranchTreeScreen`'s loading message (`Mapping your branches... Tracing career paths from O*NET pathway data.`) is a model for every loading state in the app.

**Four-week priority:** fix the Gemma system prompts first (one-day job, highest leverage — every boss narrative and Gemma's Take improves), then harmonize outcome casing, then tighten the onboarding and reveal headlines. The copy that ships in the demo video is almost entirely runtime Gemma output, so the prompt fixes are the demo fixes.

---

## Per-Screen Findings

### 1. LandingScreen (`frontend/src/screens/LandingScreen.tsx`)

**Current headline (line 64-67):**
> A college degree isn't a destination. It's a starting position.

Good. Direct, concrete, on-brand.

**Current subhead (line 74):**
> See where every path leads — powered by real data and Gemma AI.

**Issue:** "powered by real data and Gemma AI" is press-release filler. The voice guide explicitly flags "We believe" / "Our team built" style copy. This is the same register.

**Proposed rewrite (subhead — budget ~140 chars):**
> See where your degree actually leads. 700K rows of public data, zero admissions brochure.

**Rationale:** Names the receipts spine. "Actually" is the wry observational tone the guide calls for. Drops the "powered by" tech-promo structure.

**Current CTA label (line 87):**
> See where your path leads ✦

**Issue:** Duplicates the subhead. Button labels should be action verbs in 1-3 words.

**Proposed rewrite (CTA — budget ~20 chars):**
> Start ✦

**Rationale:** Matches the existing header CTA at `AppHeader.tsx:114`. Short, one sparkle, done. Primary action should not restate the page.

**Current data footer (line 102-104):**
> 700K+ data points · 280+ quality rules · 6 public datasets
> Every number has a receipt.

Keep. This is the only receipts-spine copy in the app and it's well-pitched. The data-micro treatment with 0.4 opacity is exactly the "earned swagger" the guide describes.

**File:line summary:**
- `LandingScreen.tsx:74` — rewrite subhead **(P1)**
- `LandingScreen.tsx:87` — trim CTA **(P2)**
- `LandingScreen.tsx:84` (aria-label "Start building your future") — fine, keep.

---

### 2. ProfileScreen (`frontend/src/screens/ProfileScreen.tsx`)

**Current (line 128):**
> We'll call you

**Issue:** Voice is OK but charmless. The moment the student sees their procedurally-generated name is the one "delight" moment the guide explicitly sanctions. Lean into it gently.

**Proposed rewrite (budget ~30 chars):**
> For this session, you're

**Rationale:** Sets expectation that the name is tied to this build (users have asked about persistence). "For this session" is the quiet, confident framing — peer, not pupil.

**Current (line 178):**
> No accounts. No passwords. Just you.

Keep. Triplet rhythm. On-brand.

**Current (line 197):**
> New name

**With 🎲 dice emoji.** Fine. One emoji is the guide's "restraint with delight." Don't touch.

**Current (line 215):**
> Let's go →

**Issue:** "Let's go" is Gen-Z pep-talk coded — the "coach, not cheerleader" principle. The guide doesn't ban it outright but "Let's" is the edge of infantilizing.

**Proposed rewrite (budget ~20 chars):**
> Continue →

**Alternate:** `Start your build →` — more informative but longer.

**Rationale:** Direct. Respects the peer register.

**Current (line 222):**
> Already have a name?

Fine. Keep.

**Current error (line 62):**
> Couldn't generate a new name. Try again.

Good. Model error pattern — no apology, next step embedded. Keep.

**Current error (line 86):**
> Something went wrong. Try again.

**Issue:** Voice guide explicitly flags this as "jargon in errors" — the exact example given. Name what broke.

**Proposed rewrite:**
> Couldn't reach the profile service. Try again.

**Current lookup error (line 83):**
> No profile found with that name.

Good. Factual. Keep.

**File:line summary:**
- `ProfileScreen.tsx:128` — soften "We'll call you" **(P2)**
- `ProfileScreen.tsx:215` — rewrite "Let's go" **(P1)**
- `ProfileScreen.tsx:86, 104` — specific error text **(P1)**

---

### 3. SchoolMajorScreen + school components

**Current (SchoolMajorScreen.tsx:122):**
> Your session reset. Pick your school and major again to continue.

Good. Keep.

**Current (SchoolMajorScreen.tsx:147):**
> Where are you headed?

Fine, but slightly cute. Works for this screen because it's low-stakes. Keep.

**Current (MajorInput.tsx:130):**
> What do you want to study?

Good. Direct. Keep.

**Current (MajorInput.tsx:154):**
> Type anything — 'pre-med', 'CS', 'business'...

Good. Keep.

**Current (MajorInput.tsx:185):**
> Gemma is matching your input...

**Issue:** "input" is engineering-speak. The guide's "Avoid unless explicitly needed: 'user'" category.

**Proposed rewrite:**
> Gemma is matching what you typed...

**Current (MajorInput.tsx:316):**
> Gemma matched "{rawText}"

Fine. Keep.

**Current (MajorInput.tsx:357):**
> Where this leads

Good. Keep.

**Current (MajorInput.tsx:404):**
> That's right / Close enough

Good. The low-confidence swap to "Close enough" is smart and on-brand. Keep.

**Current (MajorInput.tsx:416):**
> Not quite

Good. Keep.

**Current (MajorInput.tsx:466):**
> Let's find the right one

**Issue:** Soft "Let's" again. Voice is peer, not counselor.

**Proposed rewrite (budget ~40 chars):**
> Pick the program that fits

**Current (MajorInput.tsx:67):**
> Gemma couldn't match that — pick from the list below.

Good. Keep.

**Current (MajorInput.tsx:277):**
> No programs available. Please go back and try a different school.

**Issue:** "Please" — voice guide filler politeness. Also "Please go back" isn't a next step, it's an instruction to abandon the flow.

**Proposed rewrite:**
> This school doesn't have program data. Try a different school.

**Current (SchoolSearch.tsx:43):**
> No schools found. Try a different name or abbreviation.

Good. Keep.

**Current (SchoolSearch.tsx:46):**
> Having trouble searching. Try again in a moment.

**Issue:** "Having trouble" — soft edge. Specific is better.

**Proposed rewrite:**
> Search is down. Try again in a moment.

**Current (SchoolSearch.tsx:135):**
> Search for your school...

Good. Keep.

**Current EffortLoansPanel (EffortLoansPanel.tsx:114):**
> How much time will you have to focus on school?

Good. Conversational question, no warmup. Keep.

**Current (EffortLoansPanel.tsx:162):**
> How much of your school costs will you cover with loans?

Good. Keep.

**Current (EffortLoansPanel.tsx:27-33) — effort labels:**
> Working two jobs / Working + school / Balanced / Strong focus / All-in

**Issue:** The voice guide's locked effort levels are `Working / Balanced / All-in`. The slider has **five** stops but only three map cleanly to the locked vocab. "Working two jobs" and "Strong focus" are new coinings.

**Recommendation:** Either (a) collapse to the locked three-stop model per the guide, or (b) rename the two middle stops to stay in-family: `Working hard / Working / Balanced / Focused / All-in`. Flag for product decision, not a copy fix alone.

**Current (EffortLoansPanel.tsx:57-67) — loan impact text:**
> no debt — Loans Boss auto-win

**Issue:** "Loans Boss" — voice guide locks `Fight Student Loans`. This is drift.

**Proposed rewrite:**
> no debt — Fight Student Loans is a WIN

**Other occurrences in same file:** "Loans Boss at full difficulty" (line 66) → `Fight Student Loans at full difficulty`.

**Current (EffortLoansPanel.tsx:232):**
> Spec my build →

Good. "Spec" is on-brand project slang that carries through from `Specing [name]...`. Keep.

**File:line summary:**
- `MajorInput.tsx:185` — "input" → "what you typed" **(P2)**
- `MajorInput.tsx:277` — rewrite "Please go back" **(P1)**
- `MajorInput.tsx:466` — rewrite "Let's find" **(P2)**
- `SchoolSearch.tsx:46` — rewrite "Having trouble" **(P2)**
- `EffortLoansPanel.tsx:27-44` — reconcile effort labels with voice guide **(P1, product call)**
- `EffortLoansPanel.tsx:57-67` — "Loans Boss" → "Fight Student Loans" **(P0)**

---

### 4. CareerPickScreen (`frontend/src/screens/CareerPickScreen.tsx`)

**Current step-indicator (line 105):**
> CHOOSE YOUR PATH

Fine. Keep.

**Current title (line 114):**
> Where could this degree take you?

Good. Keep.

**Current subtitle (line 125):**
> Gemma analyzed your program and grouped career paths by how common they are for graduates like you.

**Issue:** "graduates like you" is filler. Gemma didn't literally personalize by student profile — it tiered by program. Say that.

**Proposed rewrite (budget ~180 chars):**
> Gemma grouped every matched career by how often graduates of this program actually end up there.

**Current tier descriptions (line 11-16):**
```
common: "Where most graduates from this program end up."
less_common: "Realistic paths that take more intention."
stretch: "Possible but atypical — these take extra work to reach."
```

All three are on-brand. Keep. Minor polish: `less_common` feels slightly abstract — "intention" reads corporate. Consider: `"Realistic, but not the default path."`

**Current loading (line 132):**
> Analyzing career paths...

OK. Could be more specific.

**Proposed rewrite:**
> Gemma is tiering {N} matched careers...

Requires threading the count in. Acceptable to leave as-is if expensive.

**Current CTA (line 217):**
> See my build ✦

Good. Keep.

**Current (line 220):**
> You can always come back and pick a different path.

Fine. Reassurance without coddling. Keep.

**Current Try Again flow (line 140-150):** The error lacks a named cause. `error` is rendered raw, which can read as technical gibberish.

**Proposed error pattern:**
- Replace raw `{error}` render with: `Couldn't tier the career paths. Try again, or pick a different major.`
- Keep the `Try Again` button.

**File:line summary:**
- `CareerPickScreen.tsx:124-126` — tighten subtitle **(P2)**
- `CareerPickScreen.tsx:140-150` — structured error copy **(P1)**

---

### 5. RevealScreen (`frontend/src/screens/RevealScreen.tsx`)

**Current (line 192):**
> at {build.school_name}

Good. Keep.

**Current (line 198):**
> ${career.median_annual_wage}/yr median

Good. Keep.

**Current `Fight the Bosses` CTA (line 265):**
> Fight the Bosses →

**Issue:** Voice guide locks `Fight [X]` — `Fight the Bosses` isn't a named boss, it's the gauntlet entry. The existing copy works but the guide's locked composite is `Fight the Future`. Recommend aligning.

**Proposed rewrite:**
> Enter the Gauntlet →

**Rationale:** `Gauntlet` is already the locked surface name (per `GauntletIntro.tsx:28` where the micro label reads `THE GAUNTLET`). "Enter the Gauntlet" is on-brand and doesn't reify a non-canonical boss.

**Current (line 269):**
> 5 bosses stand between you and your future.

Good. Matches `GauntletIntro.tsx:36`. Keep. (Note the Gauntlet has 5 normal bosses + 1 Fight the Future = 6 per voice guide — the "5" line is accurate for the pre-gauntlet screen.)

**LoadingScreen (`LoadingScreen.tsx:12-19`) — loading messages:**

Current:
```
Specing {name} {emoji}...
Crunching salary data...
Sizing up the bosses...
Mapping your branches...
Asking Gemma for advice...
Almost there...
```

Excellent. Specific to each step, first one personalized. **Keep exactly.** This is the model.

**Current error (line 33):**
> Something went wrong — let's try again

**Issue:** Same anti-pattern as before. "Something went wrong" is the exact phrase the voice guide bans.

**Proposed rewrite:**
> Build failed. Tap retry to try again.

**Current tutorial skip (line 48):**
> Skip tutorial

Fine. Keep.

**Current stat tutorial (StatTutorial.tsx + statExplanations.ts):**

`statExplanations.ts:58` — **`"Growth Potential"` should be `"Growth Outlook"`.** Voice guide locks `GRW = Growth Outlook`. **P0 fix.**

`statExplanations.ts:68` — **`"Human Edge"` is correct.** Keep.

`statExplanations.ts:46` — **`"AI Resilience"` is correct.** Keep.

`statExplanations.ts:24` — **`"Earning Power"` is correct.** Keep.

`statExplanations.ts:34` — **`"Return on Investment"` is correct.** Keep.

**Current explanation for ROI (statExplanations.ts:37-38):**
> Compares the total cost of attending this program (4 years) to your starting salary. Doesn't depend on how you finance it — that's the Student Loans Boss.

**Issue:** `Student Loans Boss` again — should be `Fight Student Loans`.

**Proposed rewrite:**
> Compares the 4-year cost of this program to your starting salary. Doesn't depend on how you finance it — that's Fight Student Loans.

**Current RES explanation (statExplanations.ts:48-49):**
> How exposed is this career to AI automation? Higher means the work needs humans.

Good. Keep.

**Current (CareerDetail.tsx:284):**
> This career has {low/moderate/high} AI exposure

Good. Factual. Keep.

**Current (CareerDetail.tsx:293-297):**
> Note: Broad CIP data was used for this career because program-level data wasn't available. Results are still meaningful but may be less precise.

**Issue:** `MEMORY.md` says "Don't show 'Limited data' warnings on career cards from CIP substitution." This note does exactly that on the detail panel. Flag for product decision — the memo may mean cards specifically, not detail panels. If the rule extends to detail view too, remove.

**Current (GemmaTake.tsx:23):**
> GEMMA'S TAKE

Good. Exact match with voice guide. Keep.

**Current (GemmaTake.tsx:30-38) — receipt contents:**
> Generated by Gemma 4 based on:
> - Pentagon stat profile
> - Boss fight outcomes
> - Career branch data
> - Program-specific earnings

Good. Dry label-list format per guide. Keep.

**File:line summary:**
- `RevealScreen.tsx:265` — `Fight the Bosses` → `Enter the Gauntlet` **(P1)**
- `LoadingScreen.tsx:33` — rewrite error message **(P1)**
- `statExplanations.ts:58` — `Growth Potential` → `Growth Outlook` **(P0)**
- `statExplanations.ts:38` — `Student Loans Boss` → `Fight Student Loans` **(P0)**
- `CareerDetail.tsx:293-297` — confirm MEMORY.md scope **(P1, product)**

---

### 6. GauntletScreen + gauntlet components

**Current (GauntletIntro.tsx:28):**
> THE GAUNTLET

Good. Keep.

**Current (GauntletIntro.tsx:36):**
> 5 threats stand between you and your future.

Good. Keep.

**Current (BossFightCard.tsx:33-48) — result pills:**
```
win:  "WIN ✦"
lose: "LOSS"
draw: "DRAW"
unknown: "NO DATA"
```

**Issue:** Voice guide locks `WIN / DRAW / LOSE`. `LOSS` is a noun (the event); `LOSE` is the verb (the outcome). The rest of the app is also inconsistent:
- `BossFightCard.tsx:33` — `WIN ✦` / `LOSS` / `DRAW` / `NO DATA`
- `FinalBoss.tsx:14-18` — `WIN` / `LOSS` / `DRAW` / `N/A`
- `SaveConfirmation.tsx:107` — `W · D · L` (three-letter)
- `BuildCard.tsx:83-87` — `W·L·D` (three-letter, different order)
- `RiskHeadlineCard.tsx:16-20` — `WIN` / `LOSE` / `DRAW` (the voice-guide-compliant version)
- `TreeNodeDetailPanel.tsx:27-43` — uses raw `win/lose/draw` (compliant after uppercase)

**Fix:** Standardize on `WIN / DRAW / LOSE` everywhere. This is a P0 because it's visible in every boss card and every share frame.

**Current `WIN ✦`:** drop the sparkle from result pills. Per voice guide, "win is matter-of-fact." The sparkle is celebratory treatment and undercuts the register. Keep sparkles for CTAs and build-saved confirmations; remove from result pills.

**Current (BossFightCard.tsx:240-242):**
> Score: {raw_score} (win ≥ {threshold_win}, draw ≥ {threshold_draw})

Good. Receipts format. Keep.

**Current reroll CTA (BossFightCard.tsx:298):**
> Equip skills to fight again

Good. Keep.

**Current (RerollFlow.tsx:43):**
> Equip skills to fight again

Duplicates the CTA label. Expected — it's also the section heading. Keep.

**Current (RerollFlow.tsx:55):**
> Pick skills that boost your stats, then rescore the fight.

Good. Direct. Keep.

**Current (RerollFlow.tsx:57-58):**
> Last attempt.

Good, minimal. Keep.

**Current (RerollFlow.tsx:88, 98):**
> Accept result / Rescore Fight ✦

Good. Keep the ✦ on the primary CTA per guide's "one sparkle per primary CTA" pattern.

**Current StructuralLoss (StructuralLoss.tsx:20-27):**
> Every available skill for this fight has been equipped, and the result is still a loss. That's the most important signal this tool can give you: the gap isn't a skill-tree problem. It's structural to this school + major + career combination. Worth taking seriously.
>
> This doesn't mean the path is wrong — it means this specific risk needs a different strategy. Your Next Steps checklist will address this.

**Exemplary.** Contemplative register, names the threat honestly, points to the next step. This is the voice guide made flesh. Keep exactly.

**Current FinalBoss (FinalBoss.tsx:76):**
> Fight the Future

Good. Matches voice guide. Keep.

**Current FinalBoss verdicts (GauntletScreen.tsx:29-38):**
```
DOMINANT BUILD — strong across the board.
SOLID BUILD with minor soft spots.
SOLID BUILD with a gap.
MIXED BUILD — wins and losses cancel out; play to strengths.
VULNERABLE BUILD — losses outweigh wins; active mitigation required.
```

**Issue (mixed):**
- `DOMINANT BUILD` / `SOLID BUILD` / `VULNERABLE BUILD` — the ALL CAPS treatment violates the voice guide's "ALL CAPS for emphasis" anti-pattern. It's acceptable as a label if rendered in small-caps/data-micro CSS, but it's currently emitted as literal uppercase string.
- The verdicts are punishing ("VULNERABLE") — the voice guide's "matter-of-fact on win, contemplative on loss" principle asks for lower-temperature language.

**Proposed rewrites (verdict text content only):**
- `DOMINANT BUILD — strong across the board.` → `Strong build. Wins across every fight.`
- `SOLID BUILD with minor soft spots.` → `Solid build with minor soft spots.`
- `SOLID BUILD with a gap.` → `Solid build, with one gap to close.`
- `MIXED BUILD — wins and losses cancel out; play to strengths.` → `Mixed result. Wins and losses cancel out — play to your strengths.`
- `VULNERABLE BUILD — losses outweigh wins; active mitigation required.` → `Losses outweigh wins. This path needs active mitigation.`

**Rationale:** Drops the mandatory CAPS-first treatment (let the CSS handle visual weight). Drops "BUILD" label-doubling when the verdict is a sentence. "Active mitigation required" reads like a compliance document — "needs active mitigation" is direct without being prescriptive-corporate.

**Current FinalBoss scorecard labels (FinalBoss.tsx:116):** `boss.label.replace("Fight ", "")`

**Issue:** Strips the "Fight" prefix to show just `AI / Student Loans / the Market / Burnout / the Ceiling`. Voice guide locks `Fight [X]`. The strip happens for horizontal space — understandable — but the locked vocabulary is the entire string. If display width requires abbreviation, use the icon plus the locked name at a smaller size.

**Proposed:** Leave "Fight " on the label. If too long, put the emoji above and the word below: `🤖 / AI` stacked, with the full phrase in the aria-label.

**Current CTA (FinalBoss.tsx:185):**
> Your Next Steps ✦

Good. Keep.

**Current (NextSteps.tsx:68):**
> Gemma is writing your action plan...

Good. Specific. Keep.

**Current NextSteps error (NextSteps.tsx:83-85):**
> Gemma couldn't generate your action plan right now. You can still explore your branches and compare builds.

Good. Error + next step. Keep.

**Current NextSteps intro (NextSteps.tsx:132-134):**
> No more bosses. No more stats. Here's what you actually do next.

**Excellent.** This is the register shift the voice guide explicitly calls for ("Next Steps drops the RPG metaphor entirely"). Keep.

**Current (NextSteps.tsx:122, 177):**
> See Where This Path Leads →

Good. Keep.

**Current (GauntletCTA.tsx:33):**
> Save & Share

Good. Keep.

**Current (GauntletCTA.tsx:36):**
> Back to My Build

**Issue:** "My Build" is fine but the nav pattern elsewhere is `Back to Gauntlet` (no "my"). Inconsistent possessive handling across the app.

**Proposed:** Settle on one. Either `Back to your build` (peer voice, lowercase) or `Back to build`. Recommend `Back to build` for parity with `Back to Gauntlet`.

**File:line summary:**
- `BossFightCard.tsx:33-43` — `LOSS` → `LOSE`, drop ✦ from win pill **(P0)**
- `FinalBoss.tsx:14-18` — `LOSS` → `LOSE` **(P0)**
- `FinalBoss.tsx:116` — preserve `Fight ` prefix **(P1)**
- `GauntletScreen.tsx:29-38` — rewrite verdicts to drop mandatory CAPS **(P1)**
- `GauntletCTA.tsx:36` — reconcile `My Build` casing **(P2)**
- Keep `StructuralLoss.tsx` exactly as-is (canonical example).

---

### 7. BranchTreeScreen (`frontend/src/screens/BranchTreeScreen.tsx`)

**Current loading (line 133-138):**
> Mapping your branches...
> Tracing career paths from O*NET pathway data.

**Model copy.** Specific data source, second-person-implied, cool register. Hold this up as the target for every loading state.

**Current error (line 247-251):**
> Couldn't load the branch tree right now.
> {error}

Good. Keep.

**Current CTA (line 172):**
> Save & Share →

Good. Keep.

**Current TreeFallback (TreeFallback.tsx:13):**
> We're mapping career branches for {careerTitle}. Check back soon.

**Issue:** "We're mapping... Check back soon" implies an ongoing product team effort, not a data limitation. The actual reason is that this SOC has no Stage 3 branches in O*NET pathway data. Be honest.

**Proposed rewrite (budget ~160 chars):**
> No branching data yet for {careerTitle}. O*NET hasn't published pathway matches for this occupation.

**Rationale:** Honest about the data limit. The receipts spine demands this.

**Current TreeNodeDetailPanel boss labels (TreeNodeDetailPanel.tsx:19-25):**
```
ai: "Fight AI"
loans: "Student Loans"        // should be "Fight Student Loans"
market: "The Market"          // should be "Fight the Market"
burnout: "Burnout"            // should be "Fight Burnout"
ceiling: "The Ceiling"        // should be "Fight the Ceiling"
```

**Issue:** Four out of five drift from locked vocabulary. **P0 fix.**

**Proposed:** Replace with `BOSS_METADATA` from `bossMetadata.ts` — that file already has the correct strings (`Fight AI / Fight Student Loans / Fight the Market / Fight Burnout / Fight the Ceiling`).

**Current (TreeNodeDetailPanel.tsx:98, 144):**
> Stats at this node / Boss fight projection

Good. Keep.

**File:line summary:**
- `TreeFallback.tsx:13` — honest data-gap copy **(P2)**
- `TreeNodeDetailPanel.tsx:19-25` — replace ad-hoc boss map with BOSS_METADATA **(P0)**

---

### 8. MenuScreen (`frontend/src/screens/MenuScreen.tsx`) + menu components

**Current (line 164):**
> Your builds

Good. Keep.

**Current (line 166):**
> Welcome back, {profileName} {animalEmoji}

**Issue:** "Welcome back" is on the edge of infantilizing. Voice guide: "Welcome!" in the anti-patterns list. This is softer but same family.

**Proposed rewrite (budget ~50 chars):**
> {profileName} {animalEmoji}

**Rationale:** The name alone with emoji is plenty. Let the hero typography do the work.

**Alternate (if some context needed):**
> Back, {profileName} {animalEmoji}

**Current (line 169):**
> Compare your futures, ask Gemma, or start a new build.

Good. Three crisp options. Keep.

**Current empty state (line 188-196):**
> No builds yet.
> Start your first one to see it here.
> [Button: Start your first build]

Good. Model empty state. Keep.

**Current loading (line 180):**
> Loading your builds…

**Issue:** Voice guide "Never 'Loading...' alone." But this is `Loading your builds…` which is specific enough. Keep, but consider pulling a beat: `Reading your builds…` — reads more like a person and matches the tone of the comparison loader (`Reading the tradeoffs…`, CompareView.tsx:164).

**Current list error (line 54):**
> Couldn't load builds.

Good. Keep.

**Current (line 227):**
> Loading build…

Fine. Keep.

**Current buttons (line 246-278):**
- `New Build ✦` — good
- `Compare {n}/3` — good
- `Cancel` — good
- `Compare Builds` — good
- `Ask Gemma` — good, locked vocab

Keep all.

**Current GemmaChat header (GemmaChat.tsx:120-128):**
> Ask Gemma
> Context: {school} · {career} · {wlcd}

Good. Receipts-in-header pattern. Keep.

**Current chat starters (GemmaChat.tsx:13-18):**
```
What internships should I look for?
Is this career better in-state or out-of-state?
What if I add a minor?
```

Good. Specific, concrete, action-oriented. Keep.

**Current chat error (GemmaChat.tsx:81):**
> Gemma couldn't respond.

**Issue:** Too terse for a chat context where the student just typed a question. They need a next step.

**Proposed rewrite (budget ~120 chars):**
> Gemma didn't respond in time. Try your question again, or swap the backend in settings.

**Current chat placeholder (GemmaChat.tsx:228):**
> Ask anything about your build...

Good. Keep.

**Current CompareView loading (CompareView.tsx:72-73):**
> Comparing your builds…

Good. Keep.

**Current CompareView error (CompareView.tsx:81-86):**
> Couldn't load the comparison.
> {error ?? "Something went wrong."}

**Issue:** The fallback text `Something went wrong.` is the voice-guide-banned phrase. Fix the fallback.

**Proposed rewrite:**
> Couldn't load the comparison. The compare API didn't respond.

**Current (CompareView.tsx:104):**
> Risk comparison

Good. Keep.

**Current (CompareView.tsx:114):**
> Where each build wins, loses, or draws

**Issue:** "wins, loses, or draws" — verb forms. Voice guide locks `WIN / DRAW / LOSE`. This reads OK conversationally but keep an eye if it shifts pill labels.

Keep as prose.

**Current (CompareView.tsx:142):**
> Stat overlay

Good. Keep.

**Current (CompareView.tsx:152):**
> Gemma's comparison

**Issue:** Not a locked term. The narrative label for the reveal is `Gemma's Take`. For compare, a natural locked extension would be `Gemma's Compare` or `Gemma on the Tradeoffs`.

**Proposed rewrite:**
> Gemma's take on the tradeoffs

**Rationale:** Reuses the `Gemma's Take` pattern from the reveal. Natural scaling.

**Current (CompareView.tsx:164):**
> Reading the tradeoffs…

Exemplary loading phrase. Keep.

**Current (RiskHeadlineCard.tsx:73):**
> Your builds disagree here.

Good. Simple, factual. Keep.

**Current CompareView back button:**
> ← Back to builds

Good. Keep.

**File:line summary:**
- `MenuScreen.tsx:166` — drop "Welcome back" **(P2)**
- `GemmaChat.tsx:81` — specific error with next step **(P1)**
- `CompareView.tsx:86` — replace fallback "Something went wrong" **(P0)**
- `CompareView.tsx:152` — rename to align with `Gemma's Take` family **(P1)**

---

### 9. SaveWrappedScreen (`frontend/src/screens/SaveWrappedScreen.tsx`)

**Current (SaveConfirmation.tsx:89):**
> Build saved ✦

Good. Matter-of-fact confirmation. Keep.

**Current (SaveConfirmation.tsx:107):**
> {wins}W · {draws}D · {losses}L

Good. Receipts format. Keep.

**Current (SaveConfirmation.tsx:116):**
> Developing your wrapped…

**Charming.** Photography metaphor lands. This is the wrapped-frame register the voice guide explicitly allows ("the one place restraint loosens"). Keep.

**Current rendering phase copy (SaveWrappedScreen.tsx:157-162):**
> Developing your wrapped
> Printing six frames of your build. This takes a few seconds.

Good. Keep.

**Current error (SaveWrappedScreen.tsx:194-195):**
> Your wrapped didn't develop.
> {error || "Something went wrong while rendering your frames."}

**Issue:** Again the voice-guide-banned fallback phrase.

**Proposed rewrite:**
> Your wrapped didn't develop.
> {error || "The renderer didn't respond. Try again, or skip to the menu."}

Good. Photography-metaphor headline carries the error.

**Current buttons (SaveWrappedScreen.tsx:209-213):**
> Try again
> Skip to menu

Good. Keep.

**Current (WrappedViewer.tsx:142, 150):**
> Download this frame
> Download all frames

Good. Keep.

**Current (WrappedViewer.tsx:159):**
> Done →

Good. Keep.

**File:line summary:**
- `SaveWrappedScreen.tsx:198` — replace fallback text **(P1)**

---

### 10. PlaceholderScreen (`frontend/src/screens/PlaceholderScreen.tsx`)

**Current (line 11):**
> Back to start

Fine. Keep. (This screen is a stub; once features ship it disappears.)

---

### 11. Cross-cutting components

**AppHeader (`AppHeader.tsx`):**

- `FutureProof` wordmark (line 66) — keep.
- `Start ✦` (line 114) — good, keep.
- `+ New` (line 125) — good, keep.
- aria-labels `"Go to menu"` / `"Go back"` (line 74) — good, keep.

**BuildSummaryBar (`BuildSummaryBar.tsx:21-26`):**

Renders: `🏫 {schoolName} · 📚 {majorTitle}`

Good — minimal, icon+label format. Keep.

**Button component (`Button.tsx`):** correctly uses `loading` prop with spinner instead of text. No copy to fix.

**StatHelpTooltip (`StatHelpTooltip.tsx`):** factual 1-sentence tooltip format per voice guide. Keep.

**ReceiptPanel (referenced inside `GemmaTake`, `BossFightCard`, `CareerDetail`):** consistent dry `Label: value` format throughout. Keep.

---

## Gemma-Prompt Findings

The runtime prompts are where the biggest wins live. Gemma parrots whatever voice the system prompt pins — and every prompt currently pins the wrong one.

### P0 — `guidance.py:28-39` (`_SYSTEM`, Gemma's Take)

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

### P0 — `boss_fights.py:515-520` (`_NARRATIVE_SYSTEM`, boss narratives)

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

### P0 — `next_steps.py:18-34` (`_SYSTEM`, Next Steps)

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

### P1 — `guidance.py:142-159` (`_CHAT_SYSTEM`, Ask Gemma)

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

### P1 — `career_tiering.py:56-64` (`_SYSTEM`)

**Current is mostly fine** — already says "factual and direct" and "No fake percentages." Small polish:

**Add at the end:**
> Tier names: Common / Less Common / Stretch (exactly those three, lowercase headers in output — COMMON / LESS_COMMON / STRETCH per format).

**Rationale:** Locks tier names. Currently Gemma can output minor variants which the parser silently eats.

---

### P1 — `skill_recs.py:23-34` and `skill_pool.py:349-358` (both `_SYSTEM` / `_POOL_SYSTEM`)

**Current skill_recs:**
> You generate skill and coursework recommendations for high school students choosing a college major. You are concrete, specific, and empowering.

**Drop "empowering."** Replace with `"You are concrete and specific. Every recommendation names something the student could enroll in, email, or start within 30 days at their current school."`

**Current skill_pool** is already cleaner — say `"grounded in the student's actual school, major, and career path — never generic"` is on-brand. Small polish: add `"Never use 'journey', 'unlock', 'empower', or exclamation points in titles or rationales."` at the end.

---

### P2 — `intent.py:22-55` (`_INTENT_SYSTEM_PROMPT`)

Structured JSON output — voice matters less. Keep.

### P2 — `intent.py:57-80` (`_AUDIT_SYSTEM_PROMPT`)

> Be real with them. This is a $100K+ decision. Don't be mean, but don't play along.

**On-brand.** This is the voice working. Keep exactly.

### P2 — `school_lookup.py:23-27` (`_GEMMA_RESOLVE_SYSTEM`)

Structured CIP output — voice doesn't leak. Keep.

---

### Gemma-Prompt Summary Table

| File | Prompt | Severity | Fix |
|---|---|---|---|
| `guidance.py:28` | `_SYSTEM` (Gemma's Take) | P0 | Full rewrite — drop "empowering", lock vocab, pin register |
| `boss_fights.py:515` | `_NARRATIVE_SYSTEM` | P0 | Full rewrite — register per outcome |
| `next_steps.py:18` | `_SYSTEM` | P0 | Full rewrite — imperative + drop "empowering" twice |
| `guidance.py:142` | `_CHAT_SYSTEM` | P1 | Full rewrite — peer register |
| `career_tiering.py:56` | `_SYSTEM` | P1 | Add tier-name lock |
| `skill_recs.py:23` | `_SYSTEM` | P1 | Drop "empowering" |
| `skill_pool.py:349` | `_POOL_SYSTEM` | P1 | Add anti-pattern block |
| `intent.py:22` | `_INTENT_SYSTEM_PROMPT` | P2 | No change |
| `intent.py:57` | `_AUDIT_SYSTEM_PROMPT` | P2 | No change — exemplary |
| `school_lookup.py:23` | `_GEMMA_RESOLVE_SYSTEM` | P2 | No change |

---

## Missing Copy Surfaces

These surfaces don't exist yet but the screens imply them. Adding them is demo polish.

### 1. Offline / backend-down banner

**Where:** global (AppHeader area or bottom of viewport).
**Current:** Most screens will silently fail with generic error text if the backend is down. No app-level banner.
**Proposed copy (60 chars):**
> Backend offline. Live features paused.

### 2. Gemma-backend banner (Ollama vs OpenRouter)

**Where:** Settings / debug surface — currently no user-facing setting exposed.
**Current:** Backend is switched via `.env`. The copy in `GemmaChat.tsx:81` suggests the user can "swap the backend in settings" but there are no settings.
**Recommendation:** Either wire a minimal settings screen with:
> Inference backend
> Ollama (local) — Free. Runs on this machine.
> OpenRouter (cloud) — Uses Gemma 4 26B. Requires API key.

Or remove the "in settings" language from every error message. Choose one.

### 3. First-build tutorial dismissal confirmation

**Where:** StatTutorial.
**Current:** Skip button bounces to the next step without confirming. If the student dismisses early they don't see RES/GRW/HMN.
**Proposed dialog:**
> Skip the tutorial?
> You'll see quick (?) explainers on each stat card if you change your mind.
> [Skip] [Keep going]

**Priority:** P2 — low risk, but a student confused by RES mid-gauntlet has no fallback.

### 4. Build deletion confirmation

**Where:** MenuScreen / BuildCard.
**Current:** No delete UI. If added per the PRD:
**Proposed dialog copy:**
> Delete this build?
> Removes {career} at {school}. This can't be undone.
> [Delete] [Cancel]

### 5. Empty states for zero-result searches

**SchoolSearch.tsx:43** covers 1-char input silently. For "returned empty after ≥2 chars", the current copy is good. Also add: when the user has typed but not yet searched, a hint:
> Type your school name — at least 2 characters.

**Priority:** P2.

### 6. Compare with only 1 build

**MenuScreen.tsx:249-262** — "Compare Builds" is disabled when there's only 1 build. Add a hover/focus hint:
> Need 2+ builds to compare.

**Priority:** P2.

### 7. Aria-labels — gaps

- `SchoolSearch.tsx:117` aria-label "Clear school selection" — good.
- `CareerPickScreen.tsx:204` aria-label "Build your career path" — good.
- `LandingScreen.tsx:84` aria-label "Start building your future" — good, but doesn't match button text. Consider: `Generate your profile and start`.
- `ProfileScreen.tsx:186` aria-label "Generate a new profile name" — good.
- **Missing:** `BossFightCard.tsx` reroll button — has an aria-label via Button but pill `role="status"` at line 208 uses `aria-label` correctly. Good.
- **Missing:** `MajorInput.tsx:167` submit button — has `aria-label="Submit major"`. Good.
- **Missing:** `WrappedViewer.tsx:110-124` — forward/back tap zones have generic `"Previous frame"` / `"Next frame"` aria-labels. Good.
- **Missing:** `TreeNodeDetailPanel.tsx` close button (line 69-73) uses aria-label. Good.

**Aria coverage is solid.** The one gap: reroll attempts indicator (`RerollFlow.tsx:48`) has `aria-label="Attempt {n} of {max}"` — good.

### 8. Loading copy that's just "Loading…"

- `MenuScreen.tsx:180` — `"Loading your builds…"` — acceptable but could be `"Reading your builds…"` for voice parity with CompareView.
- `MenuScreen.tsx:227` — `"Loading build…"` — acceptable.

All other loading copy is specific. No critical gaps.

### 9. Time-to-wait expectation on long operations

- Wrapped render (`SaveWrappedScreen.tsx:162`): `"Printing six frames of your build. This takes a few seconds."` — good, sets expectation.
- Tree render: no expectation set. If it takes >3s, add "Tracing pathways takes a few seconds" in `BranchTreeScreen.tsx:137`.

**Priority:** P2.

---

## Prioritized Punch List

### P0 — Breaks the demo or the voice spine

1. **`guidance.py:28` — `_SYSTEM` for Gemma's Take.** Rewrite to drop "empowering" and lock vocab. Every reveal narrative depends on this.
2. **`boss_fights.py:515` — `_NARRATIVE_SYSTEM`.** Rewrite per-outcome register. Every boss narrative in the gauntlet.
3. **`next_steps.py:18` — `_SYSTEM`.** Rewrite to drop "empowering" (twice) and pin imperative register.
4. **`statExplanations.ts:58` — `"Growth Potential"` → `"Growth Outlook"`.** Voice-guide locked term.
5. **`statExplanations.ts:38` — `"Student Loans Boss"` → `"Fight Student Loans"`.**
6. **`EffortLoansPanel.tsx:57-67` — `"Loans Boss"` → `"Fight Student Loans"`** (two occurrences).
7. **`BossFightCard.tsx:33-48`, `FinalBoss.tsx:14-18` — `"LOSS"` → `"LOSE"`.** Voice-guide locked outcome word.
8. **`BossFightCard.tsx:34` — drop ✦ from WIN pill.** Voice-guide "win is matter-of-fact."
9. **`TreeNodeDetailPanel.tsx:19-25` — boss labels drift from locked vocabulary.** Replace with `BOSS_METADATA` import.
10. **`CompareView.tsx:86` — `"Something went wrong."`** — voice-guide banned fallback.

### P1 — Hurts polish or credibility

11. **`guidance.py:142` — `_CHAT_SYSTEM`.** Rewrite for peer register.
12. **`skill_recs.py:23` — drop "empowering."**
13. **`skill_pool.py:349` — add anti-pattern block.**
14. **`career_tiering.py:56` — lock tier names.**
15. **`LandingScreen.tsx:74` — rewrite subhead** (drop "powered by").
16. **`RevealScreen.tsx:265` — `"Fight the Bosses"` → `"Enter the Gauntlet"`.**
17. **`LoadingScreen.tsx:33` — rewrite error message** from "Something went wrong."
18. **`GauntletScreen.tsx:29-38` — rewrite Final Boss verdicts** to drop mandatory CAPS and soften "VULNERABLE BUILD."
19. **`FinalBoss.tsx:116` — preserve `"Fight "` prefix** on scorecard tiles.
20. **`ProfileScreen.tsx:215` — `"Let's go →"` → `"Continue →"`.**
21. **`ProfileScreen.tsx:86, 104` — specific error text.**
22. **`CareerPickScreen.tsx:140-150` — structured error copy** (not raw `{error}`).
23. **`MajorInput.tsx:277` — rewrite "Please go back and try a different school."**
24. **`GemmaChat.tsx:81` — specific error with next step.**
25. **`CompareView.tsx:152` — rename `"Gemma's comparison"` → `"Gemma's take on the tradeoffs"`.**
26. **`SaveWrappedScreen.tsx:198` — replace fallback text.**
27. **`CareerDetail.tsx:293-297` — confirm MEMORY.md scope** (product decision, then remove or keep).
28. **`EffortLoansPanel.tsx:27-44` — reconcile effort-label set with voice guide's locked 3-stop vocab** (product decision).

### P2 — Nice to have / demo-week polish

29. **`LandingScreen.tsx:87` — `"See where your path leads ✦"` → `"Start ✦"`.**
30. **`ProfileScreen.tsx:128` — soften `"We'll call you"` → `"For this session, you're"`.**
31. **`MajorInput.tsx:466` — `"Let's find the right one"` → `"Pick the program that fits"`.**
32. **`MajorInput.tsx:185` — `"Gemma is matching your input..."` → `"Gemma is matching what you typed..."`.**
33. **`SchoolSearch.tsx:46` — `"Having trouble searching..."` → `"Search is down..."`.**
34. **`CareerPickScreen.tsx:124-126` — tighten subtitle.**
35. **`TreeFallback.tsx:13` — honest data-gap copy.**
36. **`MenuScreen.tsx:166` — drop `"Welcome back"`.**
37. **`MenuScreen.tsx:180` — `"Loading your builds…"` → `"Reading your builds…"` for parity.**
38. **`GauntletCTA.tsx:36` — reconcile `"Back to My Build"` casing with `"Back to Gauntlet"`.**
39. **Add missing surface:** backend-offline global banner.
40. **Add missing surface:** Gemma-backend settings screen OR strip "in settings" language from errors.
41. **Add missing surface:** StatTutorial skip confirmation.
42. **Add missing surface:** compare-disabled hint when `builds.length < 2`.
43. **Add missing surface:** school-search pre-input hint.

---

## Canonical Examples to Protect

As you work the P0/P1 list, these surfaces are already voice-perfect — **do not touch them**:

- `StructuralLoss.tsx:20-34` — contemplative loss narrative, named threat, next step.
- `LoadingScreen.tsx:12-19` — loading message sequence.
- `BranchTreeScreen.tsx:133-138` — branch-loading copy with data source cited.
- `SaveConfirmation.tsx:89-117` — build-saved confirmation with stats strip.
- `SaveWrappedScreen.tsx:157-162` — "Developing your wrapped" photography metaphor.
- `NextSteps.tsx:132-134` — metaphor-drop intro ("No more bosses. No more stats. Here's what you actually do next.")
- `CompareView.tsx:164` — `"Reading the tradeoffs…"`
- `GemmaChat.tsx:13-17` — chat starter prompts.
- `intent.py:57-80` (`_AUDIT_SYSTEM_PROMPT`) — "Be real with them. This is a $100K+ decision."
- Every data footer / receipt block — dry `Label: value` format.

Use these as the reference when rewriting the rest.

---

**End of audit.**
