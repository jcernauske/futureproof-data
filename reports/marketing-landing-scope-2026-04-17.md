# Marketing & Landing Scope — Gemma 4 Good Submission

*Date: 2026-04-17 · Deadline: 2026-05-18 (4 weeks, 3 days)*

Grounded in `docs/reference/voice-guide.md`, `docs/futureproof_hackathon_prd_v8.md`, `CLAUDE.md`, the
`docs/specs/completed/` spec list, and the live frontend in `frontend/src/screens/`.

---

## 1. Executive Summary

The product ships. Ten screens are live, the data pipeline is done (700K+ rows across 6 public sources,
280+ DQ rules, 7 data contracts), the MCP server exposes 8 Gemma-callable tools, and the backend runs
on Ollama by default (`gemma4:e4b`) with a single-config swap to OpenRouter for the cloud demo.

**What the hackathon still needs that isn't built:**

1. **A public marketing landing page.** The in-app `LandingScreen` is the first screen of the app,
   not a marketing surface. Judges, press, and first-time visitors have nowhere to land that pitches
   the product before it demands they generate a profile.
2. **Kaggle writeup (1,500 words).** Required by the contest. Does not exist.
3. **3-minute demo video.** Required by the contest. Scripted in PRD §Video Strategy but not shot.
4. **Public-facing GitHub README.** The current `README.md` is a Brightsmith data-pipeline readme — it
   opens with ERD diagrams and column types. Not remotely readable for a judge arriving from Kaggle.
5. **Kaggle cover image + screenshot gallery.** Required by the contest. Not produced.
6. **Launch copy for social.** Needed for the growth loop the PRD bets on.

**4-week honest assessment:** All six surfaces are shippable by 2026-05-18 if we start now. Landing
page and README are the longest poles because they're the most voice-sensitive and the most linked-to.
Video script and Kaggle writeup can share source material. Cover image and screenshots are derivative
of the landing page assets.

**The one thing that worries me:** the claims audit (§4). The PRD and CLAUDE.md disagree with the
shipped codebase on three dataset counts, and the in-app landing tagline leans on "powered by real
data and Gemma AI" which is fine for in-app but thin for marketing. Everything else is copy work.

---

## 2. Landing Page Content Inventory

**URL:** `futureproof.app` (or wherever the live demo gets deployed). Single-page, dark-first, built
against existing Brightpath tokens so we don't spin up a separate design system.

**Word budget:** ~800 words total across the page. Any more and it reads like a pitch deck.

**Primary conversion goal:** Get the visitor to click through to the live app and generate a profile.
Secondary: Kaggle submission link, GitHub repo, demo video.

### Section A — Above the Fold (Hero)

**Assets needed:** Pentagon constellation glow (reuse `PentagonGlow` from `frontend/src/components/landing/`),
hero-sized. Ambient background (same `#1B1D30` as in-app). Single primary CTA button. Secondary link to video.

**Draft copy (~60 words):**

> # A college degree isn't a destination.
> # It's a **starting position.**
>
> FutureProof shows you where your school and your major actually lead — five stats, five boss fights,
> and a branching career tree powered by 700,000 rows of public labor data.
>
> **[ See where your path leads ✦ ]**   [ Watch the 3-min demo → ]

Word count: 58. Uses the locked in-app tagline verbatim — keeps brand consistency between marketing
and product. The "700,000 rows of public labor data" is the first receipt on the page.

**Voice check:** Opens with a claim, not a mission statement. No "your journey." No "empower."
Subhead is concrete numbers, not adjectives. Passes the voice guide.

---

### Section B — The Problem (Why This Exists)

**Assets needed:** None visual — typography does the work. Optional: small animated counter showing
"$1,640,000,000,000 — U.S. student loan debt" or similar receipt. I'd skip it; restraint matters here.

**Draft copy (~110 words):**

> ## Your college probably isn't going to mention the ceiling.
>
> Admissions brochures tell you about the first job. They don't tell you what the tenth one pays, or
> which careers are 82% exposed to AI, or whether your major survives the next decade of automation.
> Your guidance counselor has 400 other students and a quarter-hour with you.
>
> A private-school senior with a $400/hour counselor gets a different answer than a first-gen
> community-college student. That's the gap FutureProof closes.
>
> Every school, every major, every career path — scored against the same public data, using the same
> open model. No admissions spin. No $400/hour counselor required.

Word count: 114. Names real frustrations (ceiling, AI exposure, counselor access) with specific
numbers. Uses a voice-guide example line verbatim ("Your college probably isn't going to mention the
ceiling"). Hits the **equity spine** without saying "democratizes" or "levels the playing field."

---

### Section C — How It Works (The Core Loop)

**Assets needed:** Three screenshot tiles in a horizontal row on desktop, stacked on mobile. Pulled
from the live app (not mockups):
- Tile 1: `RevealScreen.tsx` output — pentagon + Gemma's Take narrative visible
- Tile 2: `GauntletScreen.tsx` — boss fight mid-reroll, skill card equipped
- Tile 3: `BranchTreeScreen.tsx` — branch tree with detail panel open

Each tile needs an unobtrusive caption (12-16 words). No "discover" or "unlock" verbs.

**Draft copy (~180 words):**

> ## Three things happen when you spec a build.
>
> **You see the stats.**
> Five numbers, one to ten. Earning power. Return on investment. AI resilience. Growth outlook.
> Human edge. Every stat comes from public data — College Scorecard, BLS, O*NET, Karpathy. Every
> stat has a tappable receipt.
>
> **You fight the bosses.**
> Fight AI. Fight Student Loans. Fight the Market. Fight Burnout. Fight the Ceiling. Six battles
> against the real threats to the career you picked. When you lose a fight, Gemma generates three
> to five skills you can equip to try again — a data analytics minor, a specific certification,
> a switch to a state with better purchasing power. When nothing in the skill pool flips the fight,
> that's the signal: the gap isn't a skill problem, it's structural to this build.
>
> **You see the branches.**
> A degree isn't one job. It's a starting position. Tap any career and the tree unfolds — up to
> three levels deep, each node carrying its own stats and fight results.

Word count: 183. Three short sections mirroring the three act structure of the video. Introduces the
locked vocabulary (stats, bosses, skills, reroll, structural loss, branches) in context. No feature
dumps. Specific numbers where they matter. Ends on the same line the hero opens with — intentional
echo.

**Voice check:** Uses "Fight [X]" per the locked list. "Gemma generates three to five skills" —
matches PRD §Skill Crafting exactly. Structural loss framing is the PRD §Boss Fight System language.
Passes.

---

### Section D — The Receipts Story

**Assets needed:** A screenshot of an expanded receipt panel from the live app (stat receipt with
raw inputs, thresholds, sources visible). This is the visual proof.

**Draft copy (~80 words):**

> ## Every number is tappable.
>
> Your stats aren't vibes. Tap any number and you get the raw inputs, the thresholds, the source
> datasets, and the exact computation that produced it.
>
> 700,000 cross-source rows. 280 data quality rules. Seven data contracts. A chaos-monkey-hardened
> pipeline that catches its own mistakes before they reach you.
>
> Your college brochure didn't do that.

Word count: 76. Hits the **receipts spine** from the voice guide. Final line is intentionally the
voice guide's own example. The chaos monkey line earns its place because it's genuinely true and
differentiates from every "we used AI" pitch.

---

### Section E — Run It Yourself (Gemma + Ollama)

**Assets needed:** Side-by-side visual — cloud icon vs. laptop icon, same UI under each. Or one
terminal screenshot showing `INFERENCE_BACKEND=ollama` working. The video will do the full split-screen
treatment; on the landing page, one still image suffices.

**Draft copy (~90 words):**

> ## Any school can run this on their own hardware. Forever. At zero cost.
>
> FutureProof runs on Gemma 4 through [Ollama](https://ollama.com). Flip one environment variable
> and the whole stack — stats, boss fights, Gemma's coaching, the branch tree — works on a school's
> own server. No cloud bill. No student data leaves the building. No ongoing cost.
>
> A guidance counselor's laptop can be a $400/hour advisor, for every student in the school, for
> as long as the hardware lasts.

Word count: 92. Leads with the **Ollama spine** verbatim from the voice guide. Specific about what
"flip one variable" means (it's literally true — see `backend/app/services/gemma_client.py:71`).
"A guidance counselor's laptop" is the concrete image that earns the abstraction.

---

### Section F — Live Demo / CTA Rail

**Assets needed:** Primary CTA button (same style as hero). Secondary: Kaggle link, GitHub link,
YouTube video link.

**Draft copy (~40 words):**

> ## Spec your first build.
>
> Takes about two minutes. No signup, no email. You'll get a three-word name and emoji — that's your
> identity. Come back and type it in to find your saved builds.
>
> **[ See where your path leads ✦ ]**

Word count: 42. Repeats the hero CTA deliberately — it's the one action the page wants. "No signup,
no email" is the real anti-friction pitch. "Three-word name and emoji" previews the product's most
shareable moment.

---

### Section G — Data Sources (Transparency Block)

**Assets needed:** Six-column grid of dataset cards, each with source name, row count, and what it
powers. Pulled from `CLAUDE.md` Gold Zone table and PRD §Data Pipeline — but **verify against the
live DuckDB before ship; some counts are stale in the docs.**

**Draft copy (a header + a table of receipts):**

> ## How we know.
>
> Every number FutureProof shows you traces back to one of these public datasets. Click any row
> to see how it flows through the pipeline.
>
> | Source | Rows | What it powers |
> |---|---|---|
> | College Scorecard (Field of Study) | 69,947 | ERN, ROI, Student Loans boss |
> | BLS Occupational Outlook Handbook | 832 | Growth, Ceiling boss, Market boss |
> | O*NET Task & Work Context | 798 occupations, 15,944 transitions | Human Edge, Burnout boss, branch tree |
> | Karpathy AI Exposure | 815 composite scores* | AI Resilience, Fight AI |
> | Anthropic Economic Index | 587 SOCs | AI exposure velocity signal |
> | BEA Regional Price Parities | 51 | Purchasing-power adjustment by state |
> | CIP-SOC Crosswalk | 626,406 school+major→career paths | The core query |
>
> *Composite AI exposure blends Gemma 4 task-level scoring, Karpathy's job-description baseline, and
> Anthropic's observed adoption share. Gemma scores 1.75 points more conservatively than Karpathy on
> average across the 372 overlapping occupations — it sees more human-essential tasks in white-collar
> work that simpler models rate as highly automatable.

Word count: ~120 including table. The asterisked footnote is the key A/B finding from the S1 spec —
it's one of the strongest writeup hooks and deserves surfacing on the landing page.

**Voice check:** Header is three words and a period. Table is a receipt in table form. Footnote is
data-honest — it names the delta without dressing it up as a win or a concern.

---

### Section H — Team / About

**Assets needed:** Single paragraph, optional small photo.

**Draft copy (~60 words):**

> ## Who built this.
>
> FutureProof is a Gemma 4 Good hackathon submission by Jeff Cernauske. Built on
> [Brightsmith](https://github.com/jcernauske/brightsmith) — a spec-driven, adversarially-audited
> data pipeline that processes public labor data through Bronze → Silver → Gold zones before any
> of it reaches a student.
>
> Source code is open. Every assumption is in the specs. Every number is in the receipts.

Word count: 58. Names the hackathon, the builder, and the framework without self-congratulation.
"Every assumption is in the specs" is a real claim because the specs actually exist.

---

### Section I — Footer

**Assets needed:** Standard nav row.

**Draft content:**

- Live app link (primary)
- Kaggle submission
- GitHub repo
- Demo video (YouTube)
- Brightsmith (the framework)
- Voice guide / about
- Disclaimers link — **required per PRD §Disclaimers.** "AI-estimated," "not a substitute for
  professional career counseling," etc. Footer disclosure is fine; a full modal on the hero is not.

---

### Landing Page Total

- ~800 words of copy across 9 sections
- 4 screenshots from the live app (reveal, gauntlet, branch tree, receipt expanded)
- 1 pentagon glow asset (reusable from `frontend/src/components/landing/PentagonGlow`)
- 1 Ollama visual (split-screen still or terminal screenshot)
- 0 stock illustrations, 0 hero portraits, 0 "empower your future" patterns

---

## 3. Marketing Surface Gap Table

| Surface | Status | P | Owner | Rough scope |
|---|---|---|---|---|
| **Public landing page** (`futureproof.app`) | Missing | **P0** | Jeff + frontend dev | ~800 words copy (drafted above) + 4 app screenshots + deploy to Vercel/Netlify under domain. 2-3 days build. |
| **Kaggle writeup** (1,500 words) | Missing | **P0** | Jeff | Architecture, Gemma 4 usage (10 surfaces), challenges (CIP-SOC crosswalk gap, Gemma vs. Karpathy calibration finding, reroll mechanic design). Lead with equity spine. 1-2 days draft, 1 day edit. |
| **3-min demo video script** | Drafted in PRD §Video Strategy, not shot | **P0** | Jeff | Scene beats exist. Need voice-over script (~450 spoken words), screen capture, final cut. Hit Ollama split-screen in Scene 5. 3-5 days end-to-end including edit passes. |
| **Public-facing GitHub README** | Wrong README (pipeline docs) | **P0** | Jeff | Replace current `README.md` with a judge-oriented intro + quickstart. Move existing data-pipeline content to `docs/data-pipeline-readme.md`. Must include Ollama setup section (first-class — it's the Ollama track). 1 day. |
| **Kaggle cover image** | Missing | **P0** | Jeff + design | One 16:9 image. Pentagon glow + "A college degree isn't a destination." Reuses landing hero composition. 0.5 day. |
| **Screenshot gallery for Kaggle + landing** | Missing | **P0** | Jeff | 6-8 captured stills from live app. Each shot = one product truth: pentagon reveal, Gemma's Take, boss loss + reroll cards, branch tree, receipt expanded, Wrapped share frame, compare screen, Ask Gemma. 0.5-1 day. |
| **Launch tweet / LinkedIn / Bluesky** | Missing | **P1** | Jeff | One post per platform. One idea each. Screenshot or video clip. No thread-bait. 2 hours. |
| **Judge outreach blurb** (cold email / DM template) | Missing | **P1** | Jeff | 3-sentence pitch, same voice as landing hero. 1 hour. |
| **Disclaimers page** | Missing | **P1** | Jeff | Required per PRD §Disclaimers. Legal copy in-voice (calm, direct, not scared). 2 hours. |
| **Press / judge FAQ** | Missing | **P2** | Jeff | One-pager covering: "why Gemma, not GPT-4?", "is this a startup?", "what's the data source story?", "how accurate is AI exposure?" Deflects predictable questions that waste video runtime. 2-3 hours. |
| **Static architecture diagram** | Partial (PRD has ASCII) | **P2** | Jeff | Cleaner visual for the Kaggle writeup + a blog-style post. PRD has the stack diagram; just needs to not be ASCII. 2 hours. |
| **Submission post-mortem blog** | N/A | **P2** | Jeff | Post-hackathon. Not a submission surface. Skip for now. |

**P0 total effort:** ~10-14 working days. **4 weeks to deadline.** This is shippable but tight.
Two days of slippage on any P0 starts compressing the other P0s.

---

## 4. Claims Audit

Every marketing claim I'd consider shipping, pressure-tested against PRD v8 Ships/Ships-If/Does-Not-Ship,
`CLAUDE.md`, and the actual codebase.

### Claims that hold

| Claim | Evidence | Verdict |
|---|---|---|
| "Five stats, five boss fights, branching career tree" | PRD §What Ships, locked vocabulary in voice guide, shipped in `RevealScreen`/`GauntletScreen`/`BranchTreeScreen` | Clean |
| "Powered by Gemma 4 via Ollama" | `backend/app/services/gemma_client.py:45` defaults to `gemma4:e4b` on Ollama | Clean |
| "700,000+ rows of public data" | `CLAUDE.md` Gold Zone tables sum >700K; `program_career_paths` alone = 626,406 | Clean |
| "280+ data quality rules" | PRD §Pipeline stats | Clean |
| "Six public datasets" | Scorecard, BLS, O*NET, Karpathy, BEA, CIP-SOC, Anthropic = 7 (include Anthropic) or 6 (don't) | Clean if we name "6 public datasets" referring to the original six; **recommend saying "seven" and listing Anthropic** since the three-signal composite is now shipped per `docs/specs/completed/three-signal-ai-exposure-composite-v3.md` |
| "Every number has a receipt" | `backend/app/services/receipts.py`, shipped in every screen that displays a stat | Clean |
| "Chaos-monkey-hardened pipeline" | PRD §Pipeline Architecture; Brightsmith methodology | Clean but obscure — keep for Kaggle writeup, consider dropping from landing if space is tight |
| "Any school can run this on their own hardware, forever, at zero cost" | `INFERENCE_BACKEND=ollama` is the default per `gemma_client.py`. Verified config switch works; the same codebase runs local or cloud. | Clean — but the video needs to actually demonstrate this on a separate machine to back up "any school" |
| "10 Gemma integration surfaces" | PRD §Gemma Integration Surfaces table lists all 10 | Clean — good Kaggle writeup hook |
| "Gemma scores 1.75 points more conservatively than Karpathy" | PRD §Key Findings, S1 spec completion notes | Clean, high-value finding for writeup and video |

### Claims that need tightening

| Claim in drafts | Issue | Rewrite |
|---|---|---|
| "No student data leaves the building" (Ollama section) | True only if the school deploys it locally. If a student uses the cloud demo, data goes to OpenRouter. | Reword: "When a school runs FutureProof on Ollama, no student data leaves the building." Specific to the deployment, not a global claim. |
| "Six boss fights" | PRD has 5 mini-bosses + Fight the Future (composite). Video script counts 5; landing draft above says "six battles." Both framings are true but inconsistent. | Pick one. I recommend: "Five boss fights and a final composite — Fight the Future." Matches the locked vocabulary in the voice guide. |
| "Your college brochure didn't do that" | Clean on voice but the voice guide example applies it to receipts. Don't overuse it. | Use once, in Section D. Never again on the page. |
| "3-5 skills" (in boss fight copy) | PRD says "3-5 skills per losing boss." Copy must match. | Draft above uses "three to five skills" — clean. Hold that. |
| "600,000 career paths" / "626K paths" | `program_career_paths` is exactly 626,406 per PRD Gold table and `three-signal-ai-exposure-composite-v3.md:701`. Older CLAUDE.md memory might say different. | Use "626,406 school+major→career paths" or "over 600,000" — never "hundreds of thousands" (vague). |
| "815 AI exposure scores" | Correct per S1+S2 specs. CLAUDE.md table says 342, PRD §Data Pipeline says 389 — **both stale**. Trust the spec completion record. | Use 815. Flag CLAUDE.md + PRD for update separately. |
| "Four tracks" framing | Unsloth track is "Ships If Bogdan joins" per PRD §Hackathon Tracks. Don't claim it unless confirmed. | Landing should say "We're submitting to the Main, Future of Education, and Ollama tracks." Drop Unsloth unless teammate confirms. |

### Claims that cannot ship (violate PRD §Does Not Ship)

None of the drafted landing copy makes these mistakes, but guard against them during edits:

- **Do not say "any device" or "works on iPhone/Android"** — native mobile is explicitly in "Does Not Ship"
- **Do not claim "full school coverage" or "every U.S. college"** — "full school coverage (4,000+ institutions)" is explicitly "Does Not Ship." The app covers the schools in College Scorecard Field of Study with CIP coverage, which is many but not all.
- **Do not show/claim "animated share cards" or "TikTok variant"** — explicitly does not ship
- **Do not say "personalized for your financial aid package"** — financial aid overlay on ROI does not ship; loans are a slider percentage, not an aid calculation
- **Do not claim Notable Alumni enrichment, Course Catalog Crawler, Brightforge Lineage UI, or Career Pathfinding skill gap analysis** — all in "Does Not Ship"
- **Do not say "legally reviewed" or "career counseling"** — PRD disclaimers explicitly call this out: "not a substitute for professional career counseling"

### Claims the PRD and CLAUDE.md disagree on

Flag for cleanup (not blocking marketing, but the Kaggle writeup should cite the correct numbers):

1. **`consumable.ai_exposure`:** CLAUDE.md says 342, PRD §Gold Consumable Tables says 389, shipped spec says **815**. Use 815.
2. **`program_career_paths`:** CLAUDE.md says 626,406; PRD §Gold Consumable Tables says "626K"; shipped spec confirms **626,406**. Use exact number in writeup, "626K" in landing is fine.
3. **Ingestor count:** CLAUDE.md lists 6 sources. PRD lists 6 in §Data Sources but 7 if Anthropic is counted. Anthropic Economic Index ingestor is in `docs/specs/completed/`. Landing should say **7** and list Anthropic explicitly.

---

## 5. Prioritized Punch List

### P0 — Submission won't accept, or will tank judging, without it

1. **Public-facing GitHub README rewrite** — 1 day
   - Move current pipeline README to `docs/data-pipeline-readme.md`
   - New README: one-paragraph pitch (reuse landing Section A + B), quickstart (Ollama path first, OpenRouter second), demo URL, video URL, Kaggle URL, screenshots section
   - First-class "Run It Yourself (Ollama)" section — clone, `uv sync`, `ollama pull gemma4:e4b`, `INFERENCE_BACKEND=ollama`, backend start, frontend start
   - Link to specs directory and voice guide for credibility

2. **Public landing page built and deployed** — 2-3 days
   - Copy per Section 2 of this report
   - 4 live-app screenshots captured post-F3.1 close-out (to catch any final mock-flag fixes)
   - Deploy under `futureproof.app` or `demo.futureproof.app`
   - Lighthouse 95+ score — the page is a judge's first technical impression
   - Working live demo link (critical dependency: backend + frontend deployed and stable)

3. **Kaggle writeup (1,500 words)** — 2-3 days
   - Outline: hook (equity spine) → architecture diagram → Gemma 4 usage (10 surfaces with receipts) → data challenges (CIP-SOC crosswalk, three-signal composite, Karpathy divergence finding) → Ollama deployment story → what shipped vs. what didn't → receipts and disclaimers
   - Hit exactly 1,500 words. Judges respect the constraint.
   - Lead with a number, never a mission statement

4. **3-minute demo video** — 4-5 days including production
   - Script based on PRD §Video Strategy, tightened to ~450 spoken words
   - Screen captures from live app, not mockups
   - Ollama split-screen scene (Scene 5) shot on a separate physical laptop running locally
   - Ends on the equity line, not the CTA
   - Captions burned in for accessibility and for judges watching on mute

5. **Kaggle cover image** — 0.5 day
   - 16:9, pentagon glow, tagline "A college degree isn't a destination."
   - No text hierarchy beyond the tagline
   - Same dark palette as the app — visual continuity when a judge clicks through

6. **Screenshot gallery (6-8 images)** — 0.5-1 day
   - Curated from the live app at submission-quality polish
   - Captions that are the punchline, not the setup
   - Usable on Kaggle, landing page, README, and social launch

7. **Disclaimers page** — 2 hours
   - Required content per PRD §Disclaimers, in voice
   - Linked from landing footer and from in-app footer

**P0 subtotal: 10-14 days across 4 weeks. Tight but achievable.**

### P1 — Hurts judging score or growth loop but not submission-blocking

8. **Launch social posts (Twitter/X, LinkedIn, Bluesky)** — 2 hours
   - One post per platform. One idea each. Screenshot or 15-second clip.
   - Do not thread. Do not @ the judges.
   - Voice: matter-of-fact about what shipped

9. **Judge outreach blurb** — 1 hour
   - 3-sentence email/DM template the submitter can send to individual judges if appropriate
   - Opens with a number, not an introduction

### P2 — Nice to have, ship if time remains

10. **Static architecture diagram (non-ASCII)** — 2 hours
11. **Press/judge FAQ one-pager** — 2-3 hours
12. **Deeper Ollama quickstart blog** — post-submission, not pre

---

## 6. Open Questions for the Builder

Answer these before copy goes to ship:

1. **Domain.** Is `futureproof.app` owned? If not, what goes on the CTA button's `href`?
2. **Cloud deployment.** Where does the live demo run? If it's OpenRouter-backed, the landing page's Ollama section should not claim that the *demo* runs on Ollama — only that the software *can*. The video is the place to prove local.
3. **Bogdan / Unsloth track.** Is the fourth track being submitted? Affects track-list copy on landing and writeup.
4. **Schools showcased.** If we screenshot a specific school (ISU is used in the video script), confirm the data populates cleanly for it and the school wouldn't object to being the example. If unsure, use a demo school that's less recognizable.
5. **Wrapped share frames.** Confirm the Puppeteer/Playwright rendering pipeline produces social-sharable PNGs without visual glitches — one of those frames should be in the Kaggle gallery.
6. **Stale doc cleanup.** Update `CLAUDE.md` (`consumable.ai_exposure` row count) and the PRD (same) before the repo gets judged. Judges *do* read CLAUDE.md now.

---

*End of scope report.*
