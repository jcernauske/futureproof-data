# FutureProof — Product Review & Loop-Compression Analysis

**Date:** 2026-04-19
**Author:** fp-product-partner (brainstorm partner)
**Audience:** Jeff (founder)
**Purpose:** Single-artifact reference for scope, sequencing, and cut decisions in the final four weeks before the May 18 hackathon deadline.

---

## TL;DR

Four actions, in order of leverage:

1. **Pre-warm the Gauntlet on Career Pick, and reframe it as a scorecard.** The Gauntlet is the #1 bounce zone in the current flow — five sequential Gemma narrations = 15–25 seconds of spinners in one screen, right after the student has just committed. Fire all boss narratives + skill pool + Gemma's Take in parallel the moment the career is tapped. Reveal opens with W/L/D tiles already painted; losing tiles pulse *"Tap to fight back."* Structural loss surfaces when the reroll pool exhausts, not before. This is the single biggest UX swing still on the table.
2. **Compress the loop to under 90 seconds of input before the reveal.** Today a first-time visitor types/picks for ~2–3 minutes across school → major → career before they see their stats. That's the biggest drop risk for a judge who opens the tab cold. Cut major disambiguation by defaulting to the most common CIP, default-and-defer the Effort/Loans sliders (Balanced / 50% loans, "tune your build" pill on Reveal opens them as a bottom sheet), land a Zillow-zestimate data payoff on the School screen (typing "ISU" instantly shows median grad earnings + top 3 majors + tiny pentagon), and pre-fill a demo student on the landing so the judge can hit **See the pentagon** in one click.
3. **Make the 30-second screenshot do the work.** The pentagon + the four boss names + one line of Gemma narration is the artifact that travels in Slack, Twitter, and judge notes. Treat the reveal screen as the hero shot; everything before it is friction, everything after it is depth.
4. **Ship F7 narrow — Ask Gemma, Compare, New Build. Defer Branch Detail.** F7 (the post-build menu) is the biggest unspecced surface with ~30 days left and is the highest schedule risk in the PRD. It is *not* a candidate for the Cut list — Wrapped leads directly into it and the Menu is the second-order payoff of the whole product. The call is **scope, not kill**: spec immediately, ship Ask Gemma + Risk Compare + New Build, defer Branch Detail to post-hackathon. See §9 for why the earlier framing of "cut Compare and the chat surface" was wrong.

Everything below is the why behind those four calls, plus the ideas that didn't make the cut and why.

---

## 1. Positioning — What This Is, and What Judges Will Think It Is

**The actual product:** a data-backed RPG mirror. Pick a school and a major, and the product tells you — with real earnings, real growth, real AI exposure, real O*NET human-factor data — what your post-graduation character looks like, what's trying to kill it, and how it might evolve.

**The judge's first read:** "Another career tool with a gamified skin." Half the judges will mentally file it next to every BLS-dashboard-with-sparkles they've seen. The other half will squint and ask whether the pentagon is cosmetic or load-bearing.

**The wedge that separates FutureProof from the dashboard pile:**
- The stats are **computed from real gold-zone tables**, not vibes. 700K+ cross-source rows behind the product; 280+ DQ rules enforcing them.
- The bosses are **named threats with data behind them** (AI exposure → Fight AI, market cooling → Market boss, burnout index → Burnout boss, ceiling → Ceiling boss). Each boss is a real number dressed as a monster.
- The branch tree is **grounded in career-transitions data** (15,944 O*NET transitions), not hand-written "here's what you could become" text.
- **Gemma does real work across 10 distinct integration surfaces** — intent resolution, intent audit, career tiering, Gemma's Take, boss narrative, reroll commentary, skill pool generation, skill recs, Next Steps, freeform chat — all with deterministic fallbacks. Not a chat wrapper.
- **It runs on Gemma 4 on a laptop.** 16 backend services, 10 Gemma surfaces, one config switch for Ollama vs. cloud. Any school, any counselor, any parent, zero marginal cost, forever. That is a real moat for the submission story.

**What to emphasize in the demo narration:**
- "Every number you see came from a gold-zone table, not a model. Gemma narrates; the pipeline computes." (data-honest)
- "This runs on the laptop in front of you." (the Ollama story)
- "A counselor at a regional state school can hand this to every senior for $0." (the distribution story)
- "We re-scored every occupation using Gemma 4 at the O*NET task level rather than Karpathy's job-description approach. Gemma scores 1.75 points more conservatively on average. The correlation is strong (r=0.845) — the models agree on rank ordering — but Gemma sees more human-essential tasks in white-collar work that simpler models rate as highly automatable." (the *publishable finding* — see §10)

**What to *not* say (voice guide):** "unlock your future," "personalized AI coach," exclamation points, anything that sounds like a VC deck. The product is cool, confident, data-honest. Every piece of copy should sound like it was written by someone who respects the student's intelligence.

---

## 2. The Core Journey — Beat by Beat, with Feelings

| Beat | User does | User feels (today) | User should feel | Where it leaks |
|------|-----------|---------------------|------------------|----------------|
| **Land** | Sees landing page | Curious, mildly skeptical | Intrigued, "what is this" | Copy is still doing too much work; hero doesn't promise the payoff in one glance. No activation hook — no taste of identity before the commit |
| **Profile name** | Gets "dancing happy bear 🐻" | Small surprise, mild delight | "I have a character. I want to see what happens to it." | Name is generated *after* the CTA. Move the taste of it to the landing (see §6 — rotating-name teaser) |
| **School pick** | Types school name | Small friction, "is my school in here" | Confident, "yes, this knows my school" — plus a *data whoa* the instant it resolves | Long-tail schools; typo recovery. Plus: we spend the tap and give nothing back. Zillow-zestimate move — on resolve, flash median grad earnings + top 3 majors + tiny pentagon preview |
| **Major pick** | Types major | Anxiety spike — "am I picking the right one" | Low-stakes, "I can change this later" | Disambiguation sheet asks too much too early |
| **Effort/Loans** | Drags two sliders | Mild confusion — "what do these do" | Should not exist as a blocking step | Defaults (Balanced / 50% loans) + "tune your build" pill on Reveal opens them as a bottom sheet. Moves engage-mode work to post-payoff |
| **Career pick** | Picks a starting career from tiers | Cognitive load — "wait, I have to pick again?" | Earned choice — but this is also the *pre-warm trigger* (fire Gauntlet + skill pool + Gemma's Take in parallel here) | The biggest leak in the pre-reveal funnel, *and* the highest-leverage moment to eliminate the Gauntlet bounce |
| **Reveal** | Sees pentagon + bosses | "Oh damn." (when it works) | Pride + curiosity + a little fear | The hero moment — protect it at all costs |
| **Gauntlet** | Watches 5 boss fights resolve | Waiting, spinner fatigue | Scorecard already painted; tap to expand each fight | **#1 bounce zone in the app today.** Sequential Gemma narration × 5 bosses = 15–25s of spinners. Pre-warm on Career Pick flips this from "wait" to "skim-then-engage" |
| **Reroll on loss** | Equips skills, rescore flips outcome | Agency, small thrill | "I have levers. And when I don't, that's honest information." | Losing tiles on the reveal-as-scorecard should pulse "Tap to fight back" — the reroll is the signature interaction and needs a visual affordance to enter it |
| **Structural loss** | Exhausts reroll pool on a boss | Sobering — "some gaps I can't minor my way out of" | Exactly that — the tagline *is* the moment | "Some gaps you can't minor your way out of" — this is the unreleased tagline sitting in the PRD. Ship it as copy on the structural-loss screen and as a beat in the video. |
| **Next Steps** | Reads the action checklist | Relieved — "ok, here's what I do tomorrow" | Printable — "I can bring this to my counselor or parents" | Add a "Bring this to your counselor or parents" header with the profile name — the sheet becomes a counselor artifact, not a dead end |
| **Branches** | Explores evolution tree | Curious, playful | "I have options I didn't know about" | Branch pruning — too many, too fast, dilutes the wow |
| **Wrapped** | Taps through 6 story frames | Mild pride, "this is shareable" | "I need to send this to three people" | Wrapped frame 1 currently just names you. Reframe it as the viral ask: *"every student gets a name. what's yours?"* Wrapped frame 6 currently ends the loop; turn it into a return hook: *"Come back and add a Data Analytics minor — see if you beat the AI boss."* |
| **Menu / second build / chat** | Compares, asks Gemma, starts a second build | Engaged, curious | "The product has depth past the first build" | F7 is unspecced with ~30 days out. See §9. |

The "feeling" column is the PM work that hasn't been done yet. If a screen doesn't produce a feeling, it's wasted real estate. Career pick in particular produces *cognitive load without payoff* — the student hasn't earned the right to pick a career because they haven't seen what their stats look like yet.

**Build one spine, not two flows.** The Duolingo model: a 30-second skim path and a 3-minute engaged path live inside the same shell. The difference isn't which screens the student sees, it's which affordances they touch. The pre-warmed Gauntlet scorecard, the default-and-defer sliders, the data-payoff school screen, and the Wrapped return hook all serve this — the skimming judge gets a full story arc in under a minute; the engaged senior drills into every receipt. Don't build a "demo mode" and a "real mode." Build one progressively-disclosing spine.

---

## 3. Loop-Compression Analysis — Where Time Goes

Timed a naive first-time run through the current flow (school → major → effort/loans → career pick → reveal → gauntlet). Rough budget:

| Step | Time (est.) | Nature of time | Load type |
|------|-------------|----------------|-----------|
| Landing → CTA | 8–15s | Reading | Skim |
| School input + pick | 15–25s | Typing + disambiguation | Engage |
| Major input + pick | 20–40s | Typing + disambiguation sheet | **Engage** |
| Effort + loan sliders | 10–20s | Two slider decisions | **Engage** |
| Career pick (tiered sheet) | 30–60s | Reading + decision | **Engage** |
| Reveal load | 3–8s | Waiting | Skim |
| **Gauntlet (5 bosses, sequential Gemma narration)** | **15–25s** | **Watching spinners** | **Forced skim** |
| **Total before the first genuine dwell screen (Next Steps)** | **101–193s** | | |

**The two problems, in priority order:**

1. **The Gauntlet is the #1 bounce zone in the current app.** Five sequential Gemma narrations resolve one after another, each ~3–5s at Ollama latency. That's 15–25 seconds of spinners in a single screen, *right after* the student has just committed. They've earned the payoff; now the product makes them wait for it a second time. This is the biggest drop risk in the post-reveal half of the funnel.
2. **Three consecutive commitment decisions** (school, major, career — with the sliders wedged in) before the student sees a single data point. Each decision has a disambiguation sheet. Each sheet is a potential drop. For a judge clicking through, this is death — they want the payoff inside 30 seconds or they open the next tab.

### Tightening moves, in priority order

**Move 1 — Pre-warm the Gauntlet on Career Pick, and reframe it as a scorecard.** This is the biggest UX swing on the roadmap. The moment the student taps a career in the tier list, the backend fires all five boss narratives, the skill pool generation, and Gemma's Take in *parallel* — not sequentially after the reveal. The Gauntlet screen then opens with W/L/D tiles already painted from the scored results. The student sees a *scorecard*, not a loading sequence. Tap to expand any fight for the Gemma-narrated detail. Losing tiles pulse **"Tap to fight back"** — that's the affordance into the reroll flow, which remains the signature interaction. The structural-loss message only surfaces when the reroll pool genuinely exhausts, which is the data-honest moment the PRD calls "the most important thing this tool says." Where sequential Gemma calls are unavoidable, stream tokens — perceived latency drops to roughly 30% of block-and-spinner equivalent.

**Move 2 — Collapse career pick into the reveal flow.** Reveal on the *major*, not the major+career. Show the pentagon for the major itself (which is already what `program_career_paths` computes across careers). Then let the student pick a specific career *from the reveal screen* as the first branch of the tree. This cuts 30–60s, removes one disambiguation sheet, and turns the career pick into a *discovery moment* instead of a *commitment moment*. Risk: the pentagon-for-a-major is a weighted aggregate, and we need to be voice-honest about that ("this is what graduates of this major look like on average"). Upside: the student sees the payoff in under 60s and then picks a career with context instead of blind. (Note: Move 1's pre-warm trigger moves to *reveal-screen career pick* in this flow; the rest of the mechanic is identical.)

**Move 3 — Default-and-defer the Effort + Loans sliders.** Two sliders, two decisions, zero payoff — and they're adjusting a pentagon the student hasn't seen yet. Set defaults (Balanced effort / 50% loans), drop the standalone Effort+Loans screen from the critical path. Add a **"tune your build"** pill on the Reveal that opens the sliders as a bottom sheet with the pentagon visible behind them. Now the sliders are engage-mode work the student does *after* the payoff, with the stat changes visible live — which is also when they actually matter to the student. Cuts 10–20s off the critical path and puts the sliders in their right psychological moment.

**Move 4 — Default major CIP on first ambiguous match.** Today the major sheet shows all CIP candidates for a string like "Psychology." The student reads, compares, picks. That's engage-mode work the student doesn't want to do. Default to the highest-enrollment CIP, show a small "not quite right? pick again" link under the major card on the reveal. 80% of students will never click it. Cuts 10–20s off the critical path and moves the disambiguation to a low-stakes, post-reveal context.

**Move 5 — Data-payoff instant on the School screen (Zillow-zestimate move).** The student just typed "ISU" and the product knows everything about Illinois State. Give it back immediately: median grad earnings, top 3 majors, a tiny pentagon preview, on the School screen the instant it resolves. Whoa at tap 2, not tap 5. This is the first moment the product can demonstrate that it *has receipts* — don't waste it.

**Move 6 — Pre-fill a "demo student" on the landing.** For the hackathon demo specifically: landing page has a **See the pentagon** button wired to a real (Illinois State, Special Ed, or similar — pick a school/major with good data) student. One click, full reveal, no typing. The "make it yours" flow sits next to it but is not required. Judges and first-time visitors get the payoff in 5 seconds, and then the "what about me" curiosity pulls them into the real input flow.

**Move 7 — Stream tokens wherever sequential Gemma calls remain.** Token streaming cuts *perceived* latency to ~30% of block-and-spinner. Apply everywhere a call resolves inline (Gemma's Take, Next Steps, Ask Gemma). The Gauntlet pre-warm fixes the biggest offender; streaming handles the rest.

### Skim vs. engage framing

The student's attention has two modes:

- **Skim mode:** eyes moving, low commitment, "what is this, should I care." Any screen in skim mode that asks for engage-mode input (typing, picking from a sheet) is a drop risk.
- **Engage mode:** committed, willing to work, wants depth. Once the student is in engage mode they'll tolerate a lot.

**The transition from skim to engage should happen *on the reveal*, not before it.** Today we demand engage-mode input (school, major, career, disambiguations) while the student is still in skim mode. That's backwards. The reveal is what earns engage mode. Everything before the reveal should be as low-effort as humanly possible — typeahead, smart defaults, one-tap commit.

### Hackathon-judge pushback (the honest read)

If I were judging this for Gemma 4 Good on May 18 and I opened it cold:

- I would give it ~45 seconds before I decide whether to keep clicking. If I hit the reveal in 45s with a pentagon that made me say "huh, that's interesting" I'd spend five more minutes. If I'm still typing at 45s, I'd close the tab.
- I would look for the **Gemma moment** — where does the model do something the dashboard couldn't do on its own? Today that's the narration on the reveal and the boss cards. Make sure that moment is unmissable — ideally the first line of Gemma-generated text appears inside the hero screenshot.
- I would look for **"this couldn't exist before Gemma."** The answer is: running locally, on a counselor's laptop, with a full pentagon/boss/branch story generated from gold-zone tables. Make sure the demo narrates this explicitly.
- I would be suspicious of any stat that felt made up. The ERN/GRW/HMN/RES/Ceiling labels are great but a judge will click into one and want to know what it means. Every stat card needs a one-line "computed from [source]" footer. Data-honest, not hype.
- I would not care about the landing page beyond the hero. A polished footer, an FAQ, a features grid — none of that moves the judge's needle. The reveal moves the needle.

---

## 4. Four-Week Prioritized Roadmap (to May 18)

**Assumption:** ~4 weeks of build time, one-person-equivalent effort available. Sequence is leverage-ordered, not effort-ordered.

### Week 1 (now → Apr 26): Compress the critical path + pre-warm the Gauntlet

**P0 this week:**
- **Pre-warm the Gauntlet on Career Pick.** Move 1 in §3. Fire all 5 boss narratives + skill pool + Gemma's Take in parallel on career tap. Reveal opens with the Gauntlet as a pre-scored scorecard. This is the single highest-leverage change in the entire roadmap and must land this week so Week 2 polish has something to polish.
- **Default-and-defer Effort/Loans.** Move 3 in §3. Set defaults (Balanced / 50% loans), add "tune your build" pill on Reveal opening a bottom sheet.
- **Default major CIP + demote disambiguation to post-reveal.** Move 4 in §3.
- **Data-payoff on School screen.** Move 5 in §3. Show median grad earnings + top 3 majors + tiny pentagon preview the instant a school resolves.
- **Landing "See the pentagon" demo student.** Move 6 in §3. One hardcoded student path, one button, full reveal with no typing.
- **F7 spec written and scoped.** F7 is the biggest unspecced surface in the PRD. Write the spec this week or it does not ship. Target: Ask Gemma + Risk Compare + New Build; defer Branch Detail.

**P1 if time:**
- Collapse career pick into the reveal flow (Move 2 in §3). Larger refactor; if Week 1 is already tight, defer to Week 2 and lean harder on the pre-warm for judge-flow time.
- Token streaming on the remaining inline Gemma calls (Gemma's Take, Next Steps, Ask Gemma).
- Reveal screen hero-shot audit. Pentagon, four boss names, one line of Gemma narration, all visible in a single screenshot.

**Cut this week:** anything else.

### Week 2 (Apr 27 → May 3): Depth on the reveal, bosses, and F7 implementation

**P0:**
- **Gauntlet-as-scorecard polish.** Tap-to-expand on W/L/D tiles, pulse state on losing tiles ("Tap to fight back"), structural loss only when pool genuinely exhausts. This is the payoff of Week 1's pre-warm work.
- **F7 implementation — narrow scope.** Ask Gemma chat panel (with three seeded build-specific prompts — see §6), Risk Compare (tradeoff-focused, not stat tables), New Build. Branch Detail deferred. If Wrapped frame 6's "come back" hook lands, it must land on a Menu that exists.
- **Branch tree pruning.** Cap first-level branches at 4–6 curated options per career, ranked by transition probability × contrast. Over-showing branches dilutes the "I have real options" feeling.
- **Structural loss tagline in copy.** "Some gaps you can't minor your way out of" — land this line on the structural-loss screen; it is the video moment.

**P1:**
- Boss card depth: O*NET task-level breakdown for Burnout, Karpathy detail for Fight AI.
- Every stat card gets a "computed from [source]" footer.

**Cut:** Horizon footer, account/auth, settings surface, Branch Detail in F7.

### Week 3 (May 4 → May 10): Voice, narration, Wrapped hooks, and the Gemma moment

**P0:**
- **Gemma narration pass across all surfaces.** Reveal, bosses, branches, Next Steps, Wrapped frames. Every narration line audited against `docs/reference/voice-guide.md` — cool, confident, data-honest, never hype. No exclamation points. No "unlock."
- **Wrapped viral-ask rewrite (frame 1).** Current frame 1 names the student. Reframe it as the viral ask itself: *"every student gets a name. what's yours?"*. That one copy change makes the share carry the invitation instead of implying it.
- **Wrapped return-hook rewrite (frame 6).** Replace generic CTA with: *"Come back and add a Data Analytics minor — see if you beat the AI boss."* Hook the first build's losing boss into the return trigger.
- **Next Steps as a counselor artifact.** Header: *"Bring this to your counselor or parents."* Include the profile name. The Next Steps sheet stops being a dead end and becomes a real-world artifact that carries the product out of the browser.
- **OpenRouter failover verified for the live demo.** If the demo laptop's Ollama hiccups on stage, the judge sees nothing. Table-stakes infra.
- **Demo script writeup + rehearsal start.** Script the hero demo build end-to-end *this week*, not Week 4. Known school + major + career with every boss beat landing cleanly — one loss that rerolls to a win, one structural loss for the "some gaps" moment, one branch that opens a real pivot. This is the single most important artifact for the video, and you can only debug demo-flow bugs if you're running the demo build on repeat.

**P1:**
- Second demo student with contrasting bosses (e.g. high AI exposure vs. low AI exposure), so the demo can show the pentagon *changing* rather than just sitting there.
- Ask Gemma seeded prompts: three build-specific suggestions on arrival — "Internships at [school]?", "If I add a [minor] minor, what happens?", "[career] in [state] vs [state with higher RPP]?". Removes the empty-chat-box stall.

**Cut:** landing-page polish beyond the hero, any new data source, any new screen.

### Week 4 (May 11 → May 17): Harden, rehearse, record

**P0:**
- **Record the Ollama track video.** Local inference on laptop, unedited, one take if possible. This is a deliverable for the hackathon.
- **Record the OpenRouter/cloud track video.** Same flow, cloud inference.
- **Video scene 3 — receipts beat.** Scene 3 today skips past the drill-down. Add a 5-second beat showing a single receipt: *`net_price × 4 × loan_pct = $47,200 modeled debt — threshold: DRAW if <$50K`*. This is the adversarial-auditor / show-your-work story in one shot. Unmissable. Do not cut it.
- **Video scene 3 — structural-loss beat.** Five seconds on the "some gaps you can't minor your way out of" screen. Paired with receipts, these two beats make the data-honest story unmissable.
- **Submission copy pass.** The Kaggle submission description is the last thing the judge reads before scoring. Treat it like landing-page hero copy. One paragraph data-honest, voice-correct; ~150 words spent on the Gemma vs. Karpathy AI exposure re-scoring finding (1.75-point conservative divergence, r=0.845 correlation, task-level vs. job-description-level scoring) — this is the publishable result sitting in the pipeline and the writeup should surface it.

**P1:**
- Bug triage sweep on edge-case schools/majors that appear in the demo flow.
- Screenshot set for the submission page.

**Cut:** everything new. Week 4 is a freeze week.

---

## 5. P0 / P1 / Cut Lists

### P0 — ships by May 18 or the submission is weaker for it

- **Pre-warm the Gauntlet on Career Pick; reframe Gauntlet as a scorecard (W/L/D tiles painted, tap-to-expand, losing tiles pulse "Tap to fight back")**
- Default-and-defer Effort/Loans sliders ("tune your build" pill on Reveal opens bottom sheet)
- Default major CIP + demote disambiguation
- Data-payoff moment on School screen (median earnings + top 3 majors + tiny pentagon on resolve)
- Landing "See the pentagon" demo student (one-click demo path)
- **F7 narrow: Ask Gemma + Risk Compare + New Build** (Branch Detail deferred). Spec this week, ship by end of Week 2.
- Ask Gemma seeded prompts (three build-specific suggestions on arrival)
- Wrapped frame 1 viral-ask rewrite ("every student gets a name. what's yours?")
- Wrapped frame 6 return hook ("Come back and add a [minor] minor")
- Next Steps as counselor artifact (header + profile name)
- Structural-loss tagline landed in copy ("Some gaps you can't minor your way out of")
- Reveal hero-shot quality (pentagon + 4 boss names + 1 Gemma line in one screenshot)
- Four boss cards with threat number + personalized framing + Gemma narration
- Branch tree pruning (4–6 curated first-level branches)
- Token streaming on inline Gemma calls
- Gemma narration voice audit across all surfaces
- OpenRouter failover for live demo
- Demo build scripted end-to-end in Week 3 (not Week 4)
- Video scene 3 receipts beat (net_price × 4 × loan_pct = $47,200 receipt drill-down)
- Video scene 3 structural-loss beat
- Ollama-track + OpenRouter-track demo videos recorded
- Kaggle submission copy, voice-audited, with ~150 words on the Gemma vs. Karpathy divergence finding

### P1 — ships if there's time, every one is a real upgrade

- Collapse career pick into the reveal flow (Move 2 in §3)
- Rotating profile-name teaser on the landing ("You're about to become someone like `Dancing Happy Bear`")
- Share/screenshot card on reveal (compounding loop beyond Wrapped)
- Every stat card gets a "computed from [source]" footer
- Second demo student with contrasting bosses
- "Not quite right?" major re-pick link under the major card on reveal
- Boss card depth: O*NET task-level breakdown for Burnout, Karpathy detail for Fight AI
- Edge-case school/major bug sweep
- F7 Branch Detail (if F7 narrow lands early with runway)

### Cut — not in the May 18 scope, not even close

- **Branch Detail inside F7** — the other three F7 surfaces ship; Branch Detail is the cut. See §9.
- Horizon footer *(docs/specs/feature-horizon-footer.md)* — kill or defer; the landing page beyond the hero does not move a judge
- Account / auth / save-to-account
- Settings surface
- Gemma alias curation *(docs/specs/feature-gemma-alias-curation.md)* — useful later, not for submission
- Tiered Gemma matching polish *(reports/feature-gemma-tiered-matching-2026-04-18.md)* — already landed or not demo-critical; do not reopen
- FAQ / about page / marketing content beyond the hero
- Any new data source ingestion
- Any third demo student
- Any feature that touches the pre-reveal flow beyond the compression moves in §3

---

## 6. Copy and Flow Suggestions

### Landing hero

Current copy is doing too much explaining. The hero needs to promise the payoff in one line and offer one action.

**Proposed hero beat:**
- **Headline:** "See the graduate your degree actually builds." *(or)* "Your major, as a character sheet." — pick one, the second is more on-brand with the RPG metaphor.
- **Activation hook (rotating-name teaser, directly under the headline):** *"You're about to become someone like `Dancing Happy Bear`."* Rotate the name every ~1.5s on a subtle crossfade through the real generator. 20,000 combinations in the pool, so the user sees enough variety to *believe it's personalized*, and enough motion to feel that tapping the CTA has a reward. This is the landing's engage-mode hook — it gets the student to commit before they finish reading the sub. The rotating-name teaser is the activation energy the landing is missing today.
- **Sub:** One line, data-honest: "Real earnings, real growth, real threats. Pulled from BLS, O*NET, and College Scorecard. Narrated by Gemma 4, running locally."
- **Primary CTA:** "See the pentagon" → hardcoded demo student
- **Secondary CTA:** "Try your own" → real input flow
- **Below the fold:** *nothing that isn't earning the scroll.* Cut the footer-of-links ambition for the hackathon.

### Major input flow

- On typing "Psychology," show a single default CIP as a pill below the input, not a modal. "Psychology, General (42.0101) — change" is quieter than a disambiguation sheet.
- Submit on enter. Don't make the student tap another button to commit.
- If we absolutely must disambiguate (very ambiguous strings), do it as an inline dropdown, not a sheet.

### Reveal screen

- **Hero moment:** pentagon dead center, five stat values in-ring, four boss names arrayed around the pentagon.
- **One Gemma line** directly under the pentagon — "Your Special Ed graduate from Illinois State earns less than the national average but ranks in the top 15% on Human Factor. Here's what's coming for them." (data-honest, no hype, voice-correct).
- **Gauntlet-as-scorecard** (the pre-warmed result) inlined beneath: five tiles showing W/L/D, emoji, and threat number. Already painted by the time the screen opens. The student reads, they don't wait.
- **Losing tiles pulse "Tap to fight back"** — the affordance into the reroll flow, which is the signature interaction.
- **"Tune your build" pill** under the pentagon — opens Effort/Loans as a bottom sheet, pentagon stays behind it and updates live.
- **Career pick affordance** (if Move 2 lands) appears *here* as "Pick your starting career" — branch-first, not a separate screen.

### Boss card (expanded from scorecard tile)

- Threat number at the top, big.
- Two sentences of Gemma narration, personalized from the student's stats.
- One line of "how to fight this" — actionable, specific, not generic advice.
- "Data source: Karpathy AI Exposure / BLS OOH / O*NET / BLS growth projection" footer, small.

### Structural-loss screen

- **Headline:** "Some gaps you can't minor your way out of."
- Body: the PRD's current text works as-is. Name the specific boss and the specific career+school combo. This is the most honest thing the product says — the copy should be quiet, certain, not dramatic.

### Next Steps (the counselor artifact)

- **Header:** "Bring this to your counselor or parents." Profile name underneath in small caps: `DANCING HAPPY BEAR`.
- Body: the four sections the PRD already defines. No RPG framing.
- Footer: "Generated by FutureProof — data from BLS, O*NET, College Scorecard."
- **Print-friendly layout.** One page. This is the artifact that carries the product out of the browser and onto a guidance counselor's desk.

### Wrapped frames (viral + return mechanics)

Frame 1 (today) names the student. **Reframe as the viral ask itself:**
- **Frame 1:** *"Every student gets a name. What's yours?"* — overlaid on the student's own emoji. The caption the student screenshots now *asks the question the friend needs to answer to open the product.* Lower activation energy for the friend than "I'm Steady Bold Turtle 🐢" (which implies the question but doesn't make it).

Frame 6 (today) is a generic CTA. **Reframe as a return hook tied to the first build's losing boss:**
- **Frame 6 (losing-AI example):** *"Come back and add a Data Analytics minor — see if you beat the AI boss."* The return trigger is specific, earned, and uses a skill from the pool that already surfaced in the student's reroll. If the losing boss was Loans, swap in a realistic loan-reducing action.

### Ask Gemma (F7) — seeded prompts

On arrival in Ask Gemma, show three build-specific prompt suggestions. Empty chat boxes stall students; seeds give them somewhere to jump in:

1. *"Internships at [school name]?"*
2. *"If I add a [minor relevant to losing boss] minor, what happens?"*
3. *"[career] in [student's home state] vs [state with higher RPP]?"*

All three pull from the student's active build context. All three lead somewhere data-backed. The third one quietly shows off the purchasing-power tool from the MCP layer — which is a Gemma moment the current demo script never surfaces.

### Voice sanity checks (from voice-guide.md)

- No exclamation points. Anywhere.
- No "unlock," "discover," "journey," "empower." If you see one, replace.
- Numbers are always specific and sourced. "$47,200 median earnings (College Scorecard, 5-year post-grad)" beats "great earnings potential."
- Gemma narration should sound like a smart older sibling, not a guidance counselor.

---

## 7. Recommendation on Sequencing

If you read nothing else in this doc, read this section.

**Do the Gauntlet pre-warm and the compression moves first, this week.** They are the highest-leverage changes in the entire roadmap because they protect the reveal *and* the Gauntlet — and the reveal and Gauntlet are ~80% of the demo runtime. Every hour spent on the Gauntlet pre-warm is worth ten hours of polish anywhere else, because it converts the #1 bounce zone into the hero screen.

**Sequence rationale:**
- Week 1 (compression + pre-warm + F7 spec) must come before week 2 (depth + F7 build), because depth on a funnel that leaks is wasted depth, and F7 cannot ship in Week 3 without a Week 1 spec.
- Week 2 (Gauntlet scorecard polish + F7 build + branches) must come before week 3 (voice + Wrapped rewrite + demo script), because the voice pass needs something to voice-over, and the Wrapped frames need their hooks finalized before narration is recorded.
- Week 3 (voice + demo script + Wrapped + counselor artifact) must come before week 4 (record + submit), because week 4 is a freeze week — any change in week 4 is a risk to the submission.
- **Script the hero demo build end-to-end in Week 3, not Week 4.** The single most important Week 3 artifact. If the demo build isn't on rails by May 10, Week 4 becomes a debugging week instead of a rehearsal week, and the video suffers.

**The single biggest risk to this sequence:** falling into the "let me just polish X" trap where X is the landing, the footer, or any pre-reveal surface. Every time someone pitches an improvement to a pre-reveal surface between now and May 18, the answer should be *"does it strengthen the reveal, the Gauntlet, the bosses, the branch tree, or Wrapped? If not, defer."*

**The single biggest risk to the product overall:** the demo goes perfectly and the judge still files it next to every BLS-with-sparkles dashboard. Defense: the Gemma-local-on-laptop story *and* the 10-surface Gemma integration *and* the Gemma vs. Karpathy divergence finding all have to be narrated explicitly in the video and the submission copy. That is the moat. Don't assume the judge will infer it.

---

## 8. Distraction List — Cut These When Someone Pitches Scope Creep

Keep this section open during scope discussions. Each item has a one-line reason it's cut for May 18. If someone pitches one, ask them: *which of the P0 items are you willing to drop to make room for this?* If they can't answer, the pitch dies here.

- **Horizon footer.** Doesn't strengthen the reveal. Landing real estate below the fold is not the bottleneck.
- **Branch Detail inside F7.** The other three F7 surfaces (Ask Gemma, Risk Compare, New Build) ship narrow. Branch Detail is the cut — Stage 3 branches already appear in the main Branch Tree screen; a deeper explorer is duplicative for May 18.
- **Account / auth / save-to-account.** Zero-judge impact. Students on May 18 won't have accounts. Add post-hackathon.
- **Settings / preferences surface.** No one's tuning settings in a demo.
- **Gemma alias curation.** Useful for long-tail matching; not visible in any demo-path school/major. Defer.
- **FAQ / about page.** A judge does not read the FAQ.
- **Marketing footer / link sitemap.** Same reason. Not an artifact that travels.
- **A third demo student.** Two contrasting students is enough narrative surface for a 90-second demo.
- **New data source ingestion.** Any new bronze→silver→gold work is weeks of effort. The current gold zone is enough.
- **Stats beyond the current five.** ERN / GRW / HMN / RES / Ceiling is the right number. Six feels like six. Four feels incomplete. Five feels like D&D, which is what we want.
- **Bosses beyond the current four mini + final.** AI / Loans / Market / Burnout / Ceiling + Fight the Future is a complete threat model. A seventh boss weakens the mnemonic.
- **Any landing-page A/B test infrastructure.** One hero, one CTA, ship.
- **"Real-time" anything.** Data is pre-computed in the gold zone. Don't invent live-query needs that the pipeline doesn't serve.
- **Mobile polish beyond the reveal and Wrapped.** Reveal and Wrapped need to look good on mobile because screenshots travel on phones. Everything else can be "works on mobile" without being "beautiful on mobile."

**Important note on previously-cut items that were restored:** An earlier draft of this review had "Compare mode / compare-chat screen" and "Chat surface as a product feature" on the cut list. Those were wrong and have been reversed. See §9 for the defense.

---

## 9. F7 (Post-Build Menu) — Why It's Scope, Not Cut

An earlier version of this review put Compare mode and the chat surface on the Cut list. That framing was wrong and I'm reversing it. Here's why, so the reversal doesn't look arbitrary.

**F7 is the single biggest *schedule* risk on the PRD backlog**, and that's different from being a *scope* risk. F7 covers Screen 10 — the post-build menu — and bundles four surfaces: Risk Compare, Branch Detail, Ask Gemma (chat), and New Build. It is currently ⬜ Not started with ~30 days to ship, and Wrapped (F6, ✅) leads directly into it. If Wrapped's frame 6 says "come back" and clicks on that CTA land on a 404, the return hook we're spending Week 3 engineering is dead on arrival.

**The two surfaces that looked tempting to cut, and why I was wrong to cut them:**

1. **Risk Compare is the second-order payoff of the whole product.** The first build tells the student "here is what this degree builds." The second build tells them "here is what a *different* degree would have built — and here are the tradeoffs you'd be living with." That comparative moment — the one the PRD calls *"Build A survives AI but gets crushed by loans. Build B is the opposite. Which risk are you more willing to live with?"* — is the reason a counselor hands this tool to a student who's deciding between two majors. Cutting Compare for May 18 turns FutureProof into a single-build stat viewer. It's shippable without Compare, but it's meaningfully less of a product, and the Future of Education track ($10K) narrative depends on it.

2. **Ask Gemma is the 10th Gemma integration surface in the PRD.** "Ten distinct Gemma surfaces" is a writeup talking point and a real differentiator versus competitors that wrap a single chat call. Cutting it would force the writeup to say "nine surfaces" and undercut the "not a chat wrapper, Gemma doing real work everywhere" framing. The chat surface is *also* the only place in the product where the student can ask build-specific questions with full context loaded — that's a real Gemma moment, not a distraction from Gemma-as-narrator.

**The right call is scope, not kill.** Narrow F7 to the three surfaces that carry the most weight:
- **Ask Gemma** — with the three seeded prompts in §6.
- **Risk Compare** — tradeoff-focused, not stat tables. The backend already has `builds.compare_builds()`.
- **New Build** — which Wrapped's return hook already demands.

**Defer Branch Detail.** The main Branch Tree screen (F5, ✅) already shows Stage 3 branches with stats and boss profiles. A separate deep-dive explorer is genuinely duplicative for May 18. If Week 2 ships F7 narrow with runway to spare, add Branch Detail; otherwise it's post-hackathon.

**What this costs and what it buys.** F7 narrow is probably 5–8 days of focused work — a meaningful chunk of the Week 2 budget. The offset comes from the Week 1 pre-warm landing cleanly (so Week 2 has polish time, not rescue time) and from deferring Branch Detail. If F7 narrow doesn't spec by end of Week 1, revisit this decision — at that point the correct move is to cut further (chat-only, no Compare), not to push F7 into Week 3.

---

## 10. The Gemma vs. Karpathy AI Exposure Finding — Don't Leave This Buried

This is a publishable result sitting in the pipeline and the submission shouldn't bury it.

**The finding, in one paragraph:** The S1 spec (`gemma-ai-exposure-rescore`) re-scored 815 occupations using Gemma 4 at the O*NET task level rather than Karpathy's job-description-level approach. Gemma scores occupations **1.75 points more conservatively on average** across 372 overlapping SOCs. The correlation is strong (r=0.845) — the models agree on rank ordering — but Gemma is calibrated lower on the absolute scale. The biggest divergences are in white-collar categories Karpathy rated as highly automatable but Gemma sees as more human-essential: Sales (Δ = −3.27), Computer/IT (Δ = −2.73), Education (Δ = −2.73), Management (Δ = −2.56).

**Why it's publishable, not a bug:** Task-level scoring with O*NET data produces more nuanced, defensible AI exposure assessments than job-description-level scoring. It's the difference between *"can AI do this job?"* and *"can AI do each specific task in this job?"* — and when you decompose, white-collar jobs have more human-essential sub-tasks than a monolithic job description suggests. This is a methodological contribution.

**Where it should show up in the submission:**
- **Kaggle writeup: ~150 words.** A "Key Finding" callout with the divergence numbers, the correlation, and the methodology claim. This is the single most interesting empirical result the pipeline produced — don't leave it in `reports/gemma_vs_karpathy_comparison.md` unread.
- **Video: 10-second beat in Scene 5 (the equity/Ollama closer).** *"We re-scored every occupation using Gemma 4 at the task level. It scores 1.75 points more conservatively than the job-description baseline — task-level scoring sees more human-essential work in white-collar jobs."* A small overlay showing two ridgeline distributions or the four divergent category bars. That's it. One screen, one stat, one sentence.
- **Submission metadata ("methodology" or "key findings" field, if Kaggle has one):** surface it there too.

**Where it should *not* show up:** the in-product UI. The student doesn't need to see "Karpathy said 7, Gemma says 5" on a stat card. That's pipeline-internal methodology. But the writeup and the video are the places where pipeline-internal methodology becomes a differentiator, and this one differentiates.

---

## 11. Files & Artifacts Referenced

- `docs/futureproof_vision_roadmap.md` — long-horizon product vision
- `docs/futureproof_hackathon_prd_v8.md` — May 18 scope
- `docs/reference/voice-guide.md` — voice (cool, confident, data-honest)
- `CLAUDE.md` — stack, data sources, gold-zone tables
- `docs/specs/feature-horizon-footer.md` — recommend: defer post-hackathon
- `docs/specs/feature-gemma-alias-curation.md` — recommend: defer post-hackathon
- `reports/in-app-copy-audit-2026-04-17.md` — prior voice audit; feed into week 3 narration pass
- `reports/landing-visual-critique-2026-04-18.md` — prior landing critique; apply only to the hero
- `reports/hackathon-ship-plan-2026-04-17.md` — prior ship plan; reconcile with this roadmap
- `reports/screen-career-pick-lineage-sheet-2026-04-18.md` — relevant to Move 2 (collapsing career pick into reveal)
- `reports/perf-reveal-loading-screen-2026-04-18.md` — relevant to the reveal hero-shot + Gauntlet pre-warm work
- `reports/screen-menu-compare-chat-2026-04-16.md` — prior F7 exploration; relevant to §9 narrow-scope decision
- `reports/gemma_vs_karpathy_comparison.md` — the divergence data for §10
- `reports/gemma-ai-exposure-rescore-2026-04-16.md` — the pipeline spec that produced §10's finding
- `docs/specs/gemma-ai-exposure-rescore-v4.md` — methodology for §10
- `data/futureproof.duckdb` — the source of truth for every number in the reveal

---

*End of report. This is the artifact Jeff will reference when making scope calls between now and May 18. If it conflicts with a spec written after 2026-04-19, the later spec wins — but update this doc when that happens so it doesn't drift.*
