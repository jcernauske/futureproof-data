# Set Your Course — Product Critique

**Audience:** Jeff, pre-final-design commit
**Scope:** stress-test the current spec's design intent against the real student and the real judge. Not a design proposal.
**Date:** 2026-04-19 — T-29

---

## 1. The Thesis

"I was wrong about what I wanted to study" only lands if the student can see careers *move* when they change something. The unified screen does the right thing structurally — co-locating school, major, and careers — but the spec is quieter than it should be about the **animation of change**. The insight is kinetic: a student types, careers swap in, and the gap between expectation and data becomes visceral. Streaming tokens in the *reasoning* surface covers half of this; the other half is whether career tiles animate in place or hard-cut.

Concrete ask for the design visionary: the spec should name "career tiles crossfade/reflow on resolution change" as a non-decorative requirement. Hard-cuts hide the thesis.

Second, `initialResolution` vs `currentResolution` is tracked in the store but the spec never says the UI **shows the drift**. A faint "started here → now here" breadcrumb (even one line of copy) would make the insight impossible to miss. Right now it's inferrable from career changes alone, which is subtle enough that a distracted 17-year-old will miss it.

## 2. Kid Voice Landing

"Not what I expected" — works. Honest, low-ego, no diagnosis.

"Wrong major" — works. Literal.

"Show me less common paths" — this one is the outlier. A 17-year-old does not say "less common paths." They say "weirder jobs," "stuff most people don't do," or "hit me with something else." "Less common" is LinkedIn voice, not kid voice. Founder's own quote — *"I don't see my shit"* — sets the bar; "less common paths" doesn't clear it.

Propose: **"Show me weirder jobs"** or **"Hit me with something else"** or **"What about the weird stuff"**. First one is strongest. It's also more honest about what that tier actually contains (stretch careers, unusual roles) than the taxonomic-feeling "less common."

Not a blocker. But if the other two chips were workshopped to sound kid-honest, this one deserves the same pass.

## 3. Community Suggestions Creepiness

At count=1 (the hackathon default per §1), the copy reads *"Other students searching 'marketing' at IU ended up here: → Marketing Manager (1 student)"*. One student. That's not social proof — that's surveillance with a count of one. It tells the student both "we're tracking each search" AND "almost nobody is here." Worst of both.

The threshold isn't the fix on its own; the **framing** is. Two changes:

- **Drop the count when n<3.** "Other students ended up here: Marketing Manager." No number. Number reappears once there's enough signal to feel like a crowd.
- **Reframe above the section.** "Where others landed" is honest. "Other students searching 'marketing'..." echoes the surveillance phrasing. Small edit, big tonal shift.

The deeper creepy-or-not question: does the student know their click is being recorded? The spec doesn't surface that. At minimum, the clarifier or commit affordance should carry a quiet line — "your picks help future students" or similar — so the data loop isn't invisible. Not a consent modal. Just an acknowledgment that the reinforcement loop exists. This is a demo-credibility thing too: judges will ask, and an answer that's *in the product* is stronger than one that's only in the writeup.

Also — "17 students" is a beautiful demo number and almost certainly fictional for May 18. Be honest in the demo script about whether that number is seeded or real. If seeded, seed it carefully; a judge who catches a seeded number loses trust on everything else.

## 4. Low-Confidence Soft Nudge

Decision #10 is calibrated right. Hard-gating commit on Gemma's confidence heuristic punishes students for the model's hedging — and the founder's instinct to make Gemma's confidence *visible but not gating* matches the voice guide's "high conviction, low arrogance" posture.

One concern: **"Want to double-check this first?"** is weak copy. It reads as hedge-asking-a-question. A data-honest version: *"Gemma wasn't sure on this one. Worth a sanity check?"* — names what actually happened, gives the student agency. The current phrasing could come from any edtech app; the revision sounds like FutureProof.

Second-order concern: what fraction of resolutions come back low-confidence? If it's >30%, the nudge becomes wallpaper and stops working. Worth measuring in the V2-anchored regression — if low-confidence is common, the threshold for showing the nudge needs to tighten.

## 5. Clarifier Free-Text

The clarifier is technically scoped by *where it appears* ("What were you hoping to see?") but the input box itself does nothing to enforce that scope. A bored student will type "write me a poem" and — per Decision #5 — the chip-routing prompt's bucket taxonomy doesn't have a bucket for that. The `no_issue_found` bucket catches it, but the prompt rules ("Keep prose to 2–4 sentences, don't hype") are the only guardrail. That's guardrails-by-prompt-engineering, which is fragile.

This is exactly what `feature-chat-guardrails.md` is for — and §12 correctly blocks external ship on it. Internal dev-team ship is fine. But two specifics worth naming now in this spec, before implementation:

- **Placeholder copy matters.** "Name a job, a field, whatever's missing" — good. Keep it. It anchors scope linguistically before the student types.
- **Character limit.** Correction log caps clarifier at 280 chars for audit. Enforce the same cap in the UI, so students can't paste jailbreak prompts into a nominally-scoped field. Spec is silent on UI-side cap.

Feels bounded enough for internal build. Not bounded enough for external demo, which is what the gate is for.

## 6. First-Time Student — Cold Start

This is the weakest part of the current spec.

Scenario: pioneer student at Podunk State types "marine biology." No community suggestions exist. Gemma resolves to 26.1302 (Marine Biology). Careers stream in. Student feels the data is thin or off. Taps "Not what I expected," types "I want to work with dolphins." Gemma runs the chip trace, classifies `school_gap` because Podunk State doesn't have a marine program that routes to marine-mammal research.

What does the student see?

The spec says: `school_gap` surfaces a school-switch CTA linking to `feature-school-discovery.md`'s `/discover?cip=<target>` route. That spec is SKELETON (per convo log). Meaning: on 2026-04-19, the cold-start `school_gap` student sees a CTA that either doesn't work, deep-links to an unbuilt screen, or falls back to... what? The spec is silent.

This is the bite. The hackathon demo video will showcase the beneficiary path (IU-Marketing, community suggestions surface). The pioneer path is what makes the loop credible. If the pioneer hits `school_gap` and gets a broken CTA or dead-end, the system feels hollow. The judge doesn't remember "it worked when it worked"; they remember the edge.

**Ask:** Either (a) cut `school_gap` as a surfaced classification for the hackathon build — Gemma still emits it, the log records it, but the UI treats it as `genuinely_impossible` ("this isn't a path from here; try exploring other majors at this school") until School Discovery ships. Or (b) promote `feature-school-discovery.md` from SKELETON to at least a stub destination. (a) is cheaper and safer for May 18.

## 7. Demo Narrative — The Judge-Remembered Moment

A 3-minute Kaggle video has room for exactly one *quotable* moment. The spec contains two candidates, but doesn't explicitly design for either:

1. **The correction moment.** Student types "marketing" at IU → Business/Commerce careers appear → student taps "Not what I expected" → types "where are the marketing jobs?" → Gemma's reasoning streams ("IU reports Marketing under 52.02, not 52.14...") → Marketing Manager appears. *This is the money shot.* It's the product's thesis, it's tool-calling on Ollama, and it's a pattern judges haven't seen.

2. **The community moment.** Second student hits the same screen → sees "Where others landed: Marketing Manager" → clicks through. Self-healing system.

Both are designed-for structurally, but neither is staged. A good demo designs for a single 8-second beat the judge replays. Right now the spec treats (1) and (2) as equal citizens; they're not. (1) is the emotional peak; (2) is the technical flex. The demo needs (1) to land first and (2) as the aftershock.

**Ask:** the spec should name the IU-Marketing flow as the reference demo path. The `crosswalk_quirk` classification already exists; making that flow the designated happy-path-for-video means every implementation decision (animation timing, clarifier copy, tool-call visibility) gets held against "does this make the money shot tighter?"

## 8. Missing Pieces

Concrete omissions that will bite at implementation:

- **Cancellation semantics on chip-in-flight edits.** Debounce handles the major input. What if the student taps "Not what I expected," the clarifier opens, they submit, Gemma starts streaming... and they edit the major input? Does the chip stream cancel? Does the new resolution queue? Spec is silent. `AbortController` only gets you so far.
- **What `community_suggestions` empty means visually.** Spec says "the section is absent entirely." Meaning: at cold start, there's a gap where the section will eventually be. Will the layout collapse cleanly, or jump when the first suggestion surfaces mid-session? Worth naming.
- **What happens when Gemma's chip response classifies `no_issue_found`.** Decision says "acknowledge, don't force a bucket, don't update resolution." But then what does the screen show? The debug trace text streams, sits there, and... the student is left staring at it? No next-step cue. This is the "you pushed back, we heard you, here's nothing new" state and it's undesigned.
- **Tool-call failure mid-stream.** Gemma calls `get_career_paths`, MCP tool throws. What does the student see? Spec falls back to the Gemma-transport-failure string, which isn't right — the transport worked, the tool failed. Needs its own error path.
- **The "Start over" button losing work.** No confirm. A frustrated student taps it and loses a half-formed build. Cheap fix; spec doesn't say.

## 9. Cuts (If One Thing Goes to V2)

**Cut the Community Suggestions surface from v1.**

I know. It's the self-healing demo beat. But: it depends on real usage data that won't exist at demo time (count=1 at best), it adds a backend service + aggregate + refresh-on-write, and if it gets mis-framed (see §3) it introduces surveillance vibes. The reinforcement *log* (write-only) ships; the *read surface* can wait.

What survives: the pioneer flow, the chip correction, the money shot. The demo video records a pioneer correcting marketing at IU → career tiles swap → commit. That's the thesis, intact, in under 60 seconds. "Self-healing" becomes a single line in the Kaggle writeup ("and every correction gets logged, so the next student benefits") that the judge trusts because the mechanism is obviously there even if the surface isn't.

Keeping community suggestions means you're counting on having non-trivial usage by 2026-05-18 to avoid the count=1 problem. That's a bet on a beta that doesn't exist yet.

## 10. Non-Negotiables

**The chip-triggered Gemma debug trace must be visible to the student in streaming text, with at least one tool call.** If that doesn't ship, the spec fails its purpose — it collapses back to "invisible resolver with a fancier UI." Everything else can degrade: sliders can be sloppy, community suggestions can be cut, school-gap can dead-end, the nudge copy can be imperfect. But if the student doesn't *see* Gemma reason through the IU-Marketing crosswalk quirk and swap the careers, this spec doesn't exist — it's just the old three-screen flow re-skinned.

That's the product. Ship that. Cut everything else if you have to.
