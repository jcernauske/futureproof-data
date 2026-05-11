# Video Review Brief — FutureProof / Gemma 4 Good Hackathon

You are reviewing a 3-minute hackathon submission video. Score it against the criteria below and give blunt, specific feedback. Don't be polite — judges aren't.

## 1. Official Kaggle Rules (verbatim)

- **Length:** "Videos must be 3 minutes or less, and should be published to YouTube." Anything over 3:00 is auto-disqualified-feeling for a judge.
- **Stated purpose:** "This is the most important part of your submission. Create a dynamic, engaging, and high-quality video that demonstrates your project in action. Your Goal: Tell a story. Show us the problem and how your Gemma 4 app solves it in a powerful way."
- **Total scoring (100 pts):**
  - Impact & Vision — **40 pts**
  - Video Pitch & Storytelling — **30 pts**
  - Technical Depth & Execution — **30 pts**
- **Video-specific rubric line (30 pts):** "How exciting, engaging, and well-produced is the video? Does it tell a powerful story that captures the viewer's imagination?"

## 2. Inferred Rubric (from Gemma 3n winners + concurrent Gemini 3 hackathon)

Judges typically don't watch past 2:00–2:30. The first 15 seconds must hook. Score on:

- **Hook strength (0–10):** Is there a specific, named human stake in the first 8 seconds? Generic "students struggle" loses; a specific person/parent/situation wins.
- **Story arc (0–10):** Problem → stakes → solution → proof → close. Not a feature tour.
- **"Show, don't tell" (0–10):** Does the screen show the product working, or does it show slides/text describing the product? Slides = penalty.
- **Gemma 4 visibility (0–10):** Does the viewer literally *see* Gemma 4 doing something — streaming reasoning, tool calls, function calling on Ollama? If Gemma is invisible, technical depth score collapses.
- **Local-first / Ollama proof (0–10):** Is it visibly running locally? Terminal with `ollama serve`, no-network demo, "any school, any hardware" framing. The 2025 Ollama track winner (LENTERA) literally showed an offline microserver in a rural classroom — that's the bar.
- **Production quality (0–10):** Audio levels, pacing, transitions, no dead air, captions readable, no jank.
- **Closer (0–5):** Does the last 10 seconds give the judge a reason to remember this over the next 200 they watch?

## 3. Past Winner Patterns (what to compare against)

- **Every Gemma 3n winner had a named protagonist.** 1st place: developer's blind brother. 3rd place: Eva, a graphic designer with cerebral palsy. The video is *about a person*, not a product.
- **Local-first is rewarded structurally.** Google's announcement copy keeps emphasizing on-device. The Ollama track is its own prize.
- **Function calling / tool use shown on camera** beats narration about it.
- **Third-party voice on camera** (a real student, counselor, teacher saying "this would help me") is worth 10x a feature list. Flag if the video has zero outside voices.

## 4. FutureProof-Specific Things This Video Must Land

The product's core thesis (per our strategy doc): **Gemma 4 is the reasoning bridge across five fragmented federal taxonomies (CIP, SOC, IPEDS, FIPS, student vocabulary) that were never designed to fit together. Without Gemma, FutureProof is a 300-entry lookup table covering 3% of student vocabulary. With Gemma, it covers everything.**

Score whether the video makes this thesis legible to a non-technical judge in under 30 seconds.

**Demo beats we wanted shown (priority order — flag any that are missing or weak):**

1. **The Pioneer moment (THE money shot):** A student types a free-text major (e.g. "marketing" at IU), Gemma resolves it via local tool call, returns career paths. Student taps "Not what I expected," Gemma re-reasons, finds the actual path. This must be visible, not narrated.
2. **Streaming token-by-token reasoning** (not a spinner).
3. **Visible tool calls** — `get_career_paths`, `get_occupation_data` — on screen.
4. **Five-stat pentagon** — ERN, ROI, RES, GRW, AURA — shown with the exact names.
5. **Boss fight + reroll mechanic** — equipping Gemma-generated skills to flip an outcome.
6. **"Structural loss" honesty** — the line "some weaknesses you can fix, some you can't" or equivalent. This is our differentiator vs. typical optimistic edtech.
7. **Local-first closer** — `ollama serve` visible, "any school, any hardware, any semester."

## 5. Voice & Tone Constraints (FutureProof brand)

The video must read as: **cool, confident, data-honest, warm without being soft. Peer to the student, not a pupil.** Flag any of the following:

- Buzzwords: "empower," "unlock," "transform," "journey," "game-changing," "revolutionary," "dream"
- Exclamation points outside rare share frames
- Fake urgency ("Don't miss out")
- Infantilizing copy ("Welcome!", "Oops!")
- Cheerleader energy. The voice is a coach, not a hype reel.
- Apology copy ("Sorry…")

**Locked vocabulary** — flag if any synonym is used:

- Stats: ERN / ROI / RES / GRW / AURA (in that order)
- Bosses: "Fight [X]" — Fight AI, Fight Student Loans, Fight the Market, Fight Burnout, Fight the Ceiling, Fight the Future
- Outcomes: WIN / DRAW / LOSE (never "victory," "tie," "defeat")
- Tiers: Common / Less Common / Stretch
- Effort: Working / Balanced / All-in
- Labels: "Gemma's Take," "Receipts," "Builds," "Reroll," "Skills," "Wrapped," "Ask Gemma," "Next Steps"

## 6. Output Format I Want From You

After watching, produce:

1. **Per-section score** with the rubric above (each line a number + one sentence why).
2. **Total /100** with the official 40/30/30 weighting.
3. **Top 3 things to fix before submission**, ranked by judge-impact-per-edit-effort. Be specific — "tighten 0:34–0:48" not "improve pacing."
4. **Top 3 things working**, so we don't accidentally edit them out.
5. **The single biggest risk** — the one thing that, if a judge clocked it, costs us the prize.
6. **Brutal honesty check:** If you were one of 1,000+ submissions and a judge had 90 seconds of attention, would this video make the shortlist? Yes/no, one paragraph why.

Be direct. Don't soften. We have until May 18, 2026 and we'd rather hear what's broken now than after submission.
