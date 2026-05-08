# FutureProof Voice Guide

The single source of truth for FutureProof's voice. Every external and internal copy surface references this document — marketing, in-app UX, and the Gemma system prompts that generate live narratives.

If it's not here, it's not voice policy.

---

## Voice Characteristics

**Tone:** Cool. Confident. Data-honest. Warm without being soft.

**Attitude:** The app has 700K rows of public data behind every number. It can afford to state things plainly. Confidence comes from the receipts, not from adjectives.

**Humor style:** A little wry. Observational, not sarcastic. "Your college probably isn't going to mention the ceiling. That's what FutureProof is for."

**Confidence level:** High conviction, low arrogance. Never hype, never hedge.

**Posture toward students:** Peer, not pupil. They're adults making a six-figure decision. No "young learner," no "your journey."

---

## Voice Principles

1. **Knows things, doesn't over-explain them.** "Market research analysts are 82% exposed to AI automation." Period. No "did you know?" framing.

2. **Brevity is the flex.** Short sentences. Concrete nouns. Zero filler. If you delete three words and nothing is lost, delete them.

3. **Earned swagger, not posture.** Every stat has a tappable receipt. The copy doesn't need to puff itself up — the data is doing that.

4. **RPG metaphor played straight.** The bosses are the bosses. Never wink at it, apologize for it, or explain the joke.

5. **Coach, not cheerleader.** Names real threats (AI, debt, burnout) and prescribes action. Never fear-mongers. Never flatters.

6. **Loss is contemplative, win is matter-of-fact.** Never flip that register. A lost fight is a "huh, I need to think about that" moment, not a punishment. A win is a fact, not a celebration.

7. **Restraint with delight.** The plush bear emoji in loading copy works *because* errors are disciplined and buttons are minimal. Overused, charm becomes noise.

---

## Reference Points

- **Good sports writing** — direct, rhythmic, specific
- **Linear's docs and empty states** — confident, minimal, technical without being cold
- **Arc browser microcopy** — treats the user as capable
- **A coach mid-game** — clear, directive, no time for warmup
- **Bourdain, not Buzzfeed** — earned authority, zero pretension

---

## Anti-Patterns — Never Do

**Buzzwords / edtech:** "empower," "unlock," "transform your future," "your journey," "game-changing," "revolutionary," "dream career," "passion," "limitless possibilities"

**Corporate tone:** "We're excited to announce," "Our team built," "We believe"

**Punctuation hype:** exclamation points (zero tolerance outside intentional share frames and rare delight moments), ALL CAPS for emphasis, em-dashes-as-drama

**Fake urgency:** "Don't miss out," "Limited time," "Act now"

**Infantilizing:** "Oops!", "Uh oh!", "Whoops!", "Welcome!", "Let's get started!"

**Filler politeness:** "Please try again" (either it's a real polite ask or it's noise)

**Gen Z larping:** "slay," "no cap," "fr fr," "vibes" — uncool the moment an app says it

**Apology copy:** "Sorry, something went wrong" → say what went wrong and what to do

**Jargon in errors:** "500 Internal Server Error" → "Couldn't reach Gemma. Try again."

**Explaining the metaphor:** "your 'boss fight' (we know, stay with us)" — just use it

**Feature dumps:** long bullet lists without emotional context

**Overpromising:** claims about unshipped features, accuracy guarantees, or legal validity

---

## Locked Vocabulary

Never improvise synonyms. These terms are the product.

**Stats (always this casing and order in sequences):**
- **ERN** — Earning Power
- **ROI** — Return on Investment
- **RES** — AI Resilience *(blended: AI-exposure composite + the O\*NET human-essential signal that used to be HMN)*
- **GRW** — Growth Outlook
- **AURA** — Brand Gravity *(institution-level — one value per school, shared by every career in a build; can be null when the institution lacks EADA/IPEDS-Finance coverage, in which case copy says nothing rather than hedging)*

**Bosses (always "Fight [X]"):**
- Fight AI
- Fight Student Loans
- Fight the Market
- Fight Burnout
- Fight the Ceiling
- Fight the Future (composite / final)

**Fight outcomes:** WIN / DRAW / LOSE (never "victory" / "tie" / "defeat")

**Career tiers:** Common / Less Common / Stretch

**Effort levels:** Working / Balanced / All-in

**Narrative labels:**
- "Gemma's Take" — the 4–6 sentence coaching narrative at the reveal
- "Receipts" — tappable data provenance (not "sources" / "proof")
- "Builds" — saved profile+school+major+career combinations
- "Reroll" — re-fight a boss after equipping new skills
- "Skills" — Gemma-generated stat-delta buffs
- "Wrapped" — the Spotify Wrapped–style share sequence
- "Ask Gemma" — the freeform chat panel
- "Next Steps" — the post-gauntlet action checklist

**Avoid unless explicitly needed:** "user," "journey," "experience," "platform," "solution."

---

## Register by Surface

The voice is consistent — but the *register* shifts by surface.

| Surface | Register |
|---|---|
| Marketing (Kaggle, README, landing) | Confident, concrete, anti-hype |
| Onboarding | Warm but minimal. Lead with what the student gets. |
| Stat tutorial | Factual. One sentence per stat. No edu-speak warmup. |
| Gemma's Take | Coach voice. Direct second-person. Data-grounded. Prescribes action. |
| Boss fight narratives | Contemplative on loss, matter-of-fact on win. Never celebratory or punishing. |
| Next Steps | Drops RPG metaphor entirely. Concrete, verb-led action items. |
| Share / Wrapped frames | The one place restraint loosens. Celebratory, visual-first, stats-forward. |
| Receipts | Intentionally dry. `Label: value` format. The *absence* of prose is what makes the rest trustworthy. |
| Errors | State what broke, give the next step. No apology. |
| PDF / printed report | **Drops the RPG metaphor entirely.** Data sections speak like Receipts (`Label: value` dry). Questions section speaks like Next Steps (verb-led). The translation table in `feature-pdf-report-exports.md` §2 Decision #4 is non-negotiable: `boss → career risk`, `WIN/LOSE/DRAW → Low/Moderate/Elevated/High`, `gauntlet → career risk profile`, `build → plan`, etc. This is the **one register-by-surface RPG-exception** — the PDF lives outside the app on counselor desks and refrigerators where game language reads as unserious. Enforced by `RPG_TERMS_FORBIDDEN_IN_PDF` regex test against the rendered PDF text. |

---

## The Hackathon Narratives (Marketing Only)

Three story spines worth naming plainly in external copy:

1. **The equity spine** — "Every student gets the same AI-aware career guidance, regardless of which school they can afford." A private-school senior with a $400/hr counselor gets the same intel as a first-gen community college student.

2. **The Ollama spine** — "Any school can run this on their own hardware, forever, at zero cost." Infrastructure-level impact; lead with this for the Ollama track.

3. **The receipts spine** — "Every number is tappable. Every claim has a source. Your college brochure didn't do that." This is what separates FutureProof from admissions marketing.

---

## When in Doubt

- **Cut.** The best line you'll write today is one you delete.
- **Read it out loud.** If it sounds like a press release, burn it.
- **Check the receipts.** If a claim doesn't have data behind it, the copy shouldn't make it.
- **Ask: would a skeptical CS senior find this credible?** If no, rewrite.
