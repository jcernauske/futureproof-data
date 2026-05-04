# Submission: Kaggle Writeup + Video Narrative (PLACEHOLDER)

## Status: TODO

> **This is a placeholder, not a spec.** It exists to pin the pitch framing we landed on during product scoping on 2026-04-19 so it survives into the Kaggle writeup and the submission video — two deliverables that get built at the end of the project when everyone is tired and narrative precision decays. The framing below is the *starting brief* for `@fp-marketing-reviewer` when the real spec is drafted.

---

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-19 |
| Last Updated | 2026-05-03 (kaggle guidance integration analysis appended as §7; structural decisions pending Jeff input) |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 0.0 (stub) |
| Deadline | 2026-05-18 (Gemma 4 Good / Kaggle) |
| Audience | Google DeepMind judges + Kaggle community |
| Related Specs | `docs/specs/feature-set-your-course.md` (the flagship build the demo is shot against), `docs/specs/feature-gemma-availability.md` (demo safety — outage protection for the recording), `docs/specs/feature-receipts.md` (the architectural showcase the pitch foregrounds — Gemma reads federal data and reasons, every claim sourced), `docs/specs/feature-gemma-tool-calling-migration.md` (the visible tool-call moments that land in the video), `docs/specs/feature-chat-guardrails.md` (demo-safety for adversarial inputs during judging), `docs/reference/voice-guide.md` |
| Mockup reference | `docs/specs/design/set-your-course-mockup/index.html` — the visual storyboard the writeup + video are shot against. Use the mockup scenarios as the shot list. Scenario 15 is the canonical desktop composition for the opening / closing frame. Scenarios 8 + 9 are the pioneer correction money shot (THE primary demo beat). Scenarios 10 + 11 show the community-suggestions surface if the video has runway for the beneficiary beat. |

---

## §1 The Pitch Framing We Chose

Developed through product review on 2026-04-19 after parking the learned-alias cache spec (which would have reduced visible Gemma usage — the exact opposite of what this submission should showcase).

**Core thesis:**

> Gemma 4 is FutureProof's **reasoning bridge across fragmented public data**. Five federal taxonomies (CIP for programs, SOC for occupations, IPEDS for institutions, FIPS for regions, free-text student vocabulary) were never designed to fit together. No amount of hand-curation closes the gap. Reasoning does.

**Architectural showcase (foreground this, don't bury it):**

> Gemma runs **tool calls against the Gold-zone MCP server on local Ollama** — visibly, during the demo. Not "Gemma autocompletes over pre-fetched context" (that's what every LLM tutorial does). The video should show Gemma invoking `get_career_paths`, `get_occupation_data`, `get_ai_exposure` mid-response and reconciling the results into a grounded answer. See `docs/specs/feature-gemma-tool-calling-migration.md` for the broader migration plan — but for submission purposes, the two flagship surfaces (Set Your Course chip routing + boss narration) are tool-call-first and that's what the judges see.

**The reinforcement-loop thesis (stronger than the original "inverse proof"):**

> **No static lookup. Gemma reasons and tool-calls live; the product learns from use.** There is no hand-curated YAML file in the middle. Cold-start students are pioneers — their chip correction triggers Gemma to tool-call the crosswalk, verify feasibility, and surface the careers they were really after. Each click teaches the system. Next student at the same school with the same search sees the crowd signal surface alongside Gemma's live reasoning. Any school, any hardware — and the product self-heals every semester without a data engineer touching it.

This is the revised "inverse proof" framing. Earlier versions of the pitch leaned on "without Gemma, FutureProof is a 300-entry lookup table covering 3% of student vocabulary." The V1 YAML regression data forced a nuance — the YAML *does* disambiguate well when used — but the revised design retires the YAML entirely in favor of a Gemma-reasoned + community-learned approach. The stronger claim is: *no static lookup exists at all.* What would be a lookup table in another product is, in this one, a living surface built by the users it serves.

**The inverse proof:**

> Without Gemma, FutureProof is a **300-entry lookup table** wrapped in a nice UI — covering maybe 3% of real student vocabulary. The "any school, any hardware, zero cost, forever" story only matters if what runs is worth running. The YAML alone isn't. Gemma is what makes local-first meaningful — because if the reasoning has to be local (to be free), the reasoning has to be in the **model**, not in pre-computed rules we can't maintain.

**The positioning shift:**

> Powered by Gemma → **Built on Gemma.** Gemma went from narrator (decorative prose over pre-computed data) to reasoning engine (the only thing making fragmented public data usable at the scale of real student vocabulary).

---

## §2 Demo Beats to Hit (video script fodder)

Ordered by "screenshotability." The video script should engineer each of these into a distinct on-screen moment.

1. **The Pioneer (Marketing-at-IU correction) — THE primary demo beat.** First student ever. Student types "Marketing" at Indiana University. Gemma routes to Business/Commerce (IU reports it that way). Student taps "Not what I expected," clarifies "I want marketing jobs." Watch Gemma tool-call the crosswalk on local Ollama, find Marketing Manager, verify it's reachable from IU's Business degree despite the reporting quirk, and classify the feasibility as `crosswalk_quirk`. Student clicks Marketing Manager. *30-second clip. This is THE money shot — the video opens and closes on this moment, every other beat is support. If one clip gets replayed by judges, this is it. Cross-ref: `feature-set-your-course.md` §10 locks this as THE primary demo narrative.*
2. **The Beneficiary.** Next day, another student, same school, same search. Gemma resolves Business/Commerce as before — the crosswalk data didn't change. But below the career preview, a new section: "17 students searching 'marketing' at IU ended up in Marketing Manager." Pioneer taught the system. Product self-heals. *This is the second-half beat that makes the reinforcement loop visible.*
3. **Streaming resolution.** Major input debounces, Gemma's reasoning appears token-by-token on the screen. Not a spinner. Thinking.
4. **Tool-calling live on local Ollama.** Gemma invokes `get_career_paths` / `get_occupation_data` / `get_regional_price_parity` / crosswalk queries mid-response, on modest hardware. Visible, grounded, cite-able.
5. **Boss fight narration grounded in the student's pentagon.** Boss speaks to *this* student's stats, not a template.
6. **"Any school, any hardware, any semester" closer.** Shot of a Mac mini or modest laptop with the whole stack running. `ollama serve` in the terminal. No cloud dependency. No data engineer. The product maintains its own lookup through use, forever.

**Cut from the video:** anything generic ("AI-powered!"), anything hype-flavored ("unlock your future!"), anything that could be any LLM ("chat with your careers!"). Voice per `docs/reference/voice-guide.md`: cool, confident, data-honest, never hype.

---

## §3 Kaggle Writeup Spine

When the real spec is drafted, the writeup should be structured roughly:

1. **What this is, in one sentence.** The thesis sentence from §1.
2. **The problem it solves.** Fragmented federal data + real student vocabulary + career-planning stakes. Concrete example: the IU-Marketing case.
3. **Why Gemma 4 specifically.** Local-runnable + reasoning-capable + tool-calling. The combination is load-bearing.
4. **What we built on top.** Pentagon / bosses / branching tree — as *affordances*, not features. Gemma is the engine; these are how students *experience* the engine's output.
5. **Why local-first matters.** Schools can't afford per-student cloud LLM spend. Any school, any hardware, forever. This is not a nice-to-have — without it the product is unshippable to its intended audience.
6. **What we didn't build and why.** The learned-alias cache (would reduce visible Gemma use — wrong framing). Occupation-first mode (scope). The inverse framing here is itself a credibility signal to judges.
7. **The data.** Gold-zone tables, counts, sources, freshness. Link to CLAUDE.md / DESIGN.md.
8. **Try it.** Clone, `ollama serve`, run.

Length target: 1,500–2,500 words. Judges skim. Every paragraph needs to earn its existence.

---

## §4 Quantitative Anchors to Use

Do not invent numbers. These are the ones to verify before the writeup ships:

- Number of CIP codes in the IPEDS taxonomy (the "scale of real student vocabulary" claim).
- Number of SOC codes in BLS (the cross-taxonomy scope).
- Row counts in each Gold-zone table (data depth).
- 56 hand-curated YAML entries × ~5 aliases ≈ 300 exact-match surface forms (the 3%-coverage argument).
- Gemma 4 parameter count / quantization that lets it run on modest hardware (the "any school" argument).
- Wall time for a full build (latency argument).
- Cost per student session (zero on Ollama; negligible on OpenRouter).

Query DuckDB directly for the row counts. Pull Gemma model specs from the Gemma 4 Good announcement.

---

## §5 Voice Contract

The writeup and the video script MUST pass `@fp-marketing-reviewer` review against the voice guide at `docs/reference/voice-guide.md`:

- Cool, confident, data-honest.
- Never hype. No exclamation points. No "unlock your future." No "revolutionary."
- Every feature claim verifiable against shipped code by the deadline.
- Credit the data sources explicitly (College Scorecard, BLS, O*NET, BEA, Karpathy, Anthropic Economic Index).

---

## §6 Discussion

```
[2026-04-19] Placeholder captured during product scoping session.
The inverse-proof framing (without Gemma → 300-entry lookup table covering
3% of student vocabulary; with Gemma → reasoning bridge across 5 taxonomies)
emerged in direct response to the founder's question "is it fair to say
Gemma is now core to this product?" The answer was yes — and the sharper
framing is that Gemma went from narrator to reasoning engine.

Pin this framing BEFORE anyone drafts the Kaggle writeup or the video
script. Narrative precision decays between now (2026-04-19) and
submission day (2026-05-18), and the writeup always gets drafted when
everyone is tired. This placeholder is the insurance policy.
```

---

## §7 Kaggle Guidance Integration Analysis (2026-05-03)

**Source:** `docs/reference/kaggle-writeup-guidance.md` — researched playbook synthesizing the Gemma 3n predecessor winners (Dec 2025), the concurrent Gemini 3 hackathon's published rubric (40/30/30), and Google's announcement framing.

**Status:** Analysis complete; structural decisions pending Jeff input (see §7.6). Writeup draft has NOT started.

### §7.1 Where the guidance reinforces this spec

The new guidance validates many of the spec's instincts:

| Topic | Spec says | Guidance says | Net |
|---|---|---|---|
| Tool-calling on local Ollama | "Architectural showcase" — visible mid-demo | Ollama must be **architecturally non-substitutable** for the Ollama prize | Same insight; guidance is sharper on prize implications |
| Local-first | "Any school, any hardware" closer | LENTERA pattern (literal 2025 Ollama winner): offline classroom on cheap hardware | Guidance proves the spec's intuition was right — this is the exact pattern Google rewards |
| Voice / no hype | Cool, data-honest, never hype | "Generic chatbot framing loses"; "write like a Google blog post, not a NeurIPS paper" | Same posture |
| Length | 1,500–2,500 words | 1,500–2,500 words, 8 sections | Identical |
| Quantitative anchors | CIP/SOC counts, row counts, wall time | Tokens/sec on named hardware, RAM, cold-start | Both required; guidance adds the **performance** numbers the spec missed |

### §7.2 What the guidance adds (not in this spec)

1. **Inferred rubric weights** — Impact 35–40% / Video 25–30% / Tech 25–30% / Repro 10%. **This changes the work calculus**: most effort goes into video + impact framing, not the technical writeup.
2. **The video is THE deliverable, not supporting evidence.** Spec treats the writeup as primary. Guidance is unambiguous: judges may not watch past minute 2.
3. **Named-human-protagonist pattern** — every 3n winner had one (Eva, the developer's blind brother, Aisha-archetype). Spec's "Marketing-at-IU pioneer" is a *system behavior*, not a *named human*.
4. **Rubric-mirroring section headers** — winners literally use H2s like `## Impact & Vision` / `## Video Pitch` / `## Technical Depth & Execution` / `## Reproducibility`. Hand judges the scorecard. Spec's §3 spine uses different headers.
5. **Multi-track submission strategy** — name Main + Future of Education + Ollama explicitly in closing. Gemma Vision won Main + Google AI Edge with one submission.
6. **Multilingual as force multiplier** — Gemma 4 supports 140+ languages; non-English demo = instant differentiation. README has Spanish + Arabic; the writeup should foreground them, not bury them.
7. **Evaluation table** — 15–20 personas, sanity-checked, presented as a small table. Required for "serious entry" perception. (`scripts/stress_recon*.py` outputs may already feed this.)
8. **Custom Ollama Modelfile** + **multi-model routing** (E2B for fast paths / 26B MoE for hard reasoning) — extra credit for Ollama prize. README mentions both models but not as a routing strategy.
9. **Real third party on camera** (teacher/counselor saying "this would help me") — flagged as **the single highest-leverage tactic this week**. Worth 10× a feature list.
10. **One-command setup** — `git clone && ollama pull && pip install && python app.py` in 5 minutes. Current Quickstart is correct but multi-step (separate backend + frontend + uv sync). A **one-command demo path** would help reproducibility scoring.
11. **14-day day-by-day timeline** — operational schedule.
12. **WiFi-visibly-disabled moment in the video** — the LENTERA / Gemma Vision move. Massively credible.

### §7.3 Where they tension (decisions Jeff needs to make)

#### §7.3.1 Thesis-first vs. persona-first opening — the biggest tension

The spec's flagship thesis sentence:
> *"Gemma 4 is FutureProof's reasoning bridge across fragmented public data. Five federal taxonomies were never designed to fit together."*

The guidance's exemplar opener:
> *"Aisha, 17, lives in [place]. Her school's career counselor sees 800 students. Internet at school cuts out by 2pm."*

**Guidance wins this argument unambiguously**: every 3n winner opened with a person, not a thesis. The spec's framing isn't wrong — it's the *second paragraph*, not the *opening line*. This is a real edit to spec §3.1.

#### §7.3.2 Do we have a real named protagonist?

Spec uses "the pioneer at IU Marketing" as an abstract role. Guidance demands a *named person with a specific geography*. Possible angles:
- **Jeff's daughter** (the family-decision origin in the README's "The problem" paragraph). Most authentic. Already shipped product.
- **A real student you can recruit and record this week** — highest-leverage AI-for-Good move per guidance, but expensive in time.
- **A composite archetype with a name** — riskier (judges may smell stock-photo persona).

#### §7.3.3 Is Marketing-at-IU the right demo case?

Spec locks Marketing-at-IU as THE money shot (a `crosswalk_quirk` system behavior). Guidance suggests something with **higher human stakes** — deaf education, special ed, first-gen-college, rural-CTE. The reinforcement-loop story works for any of these; Marketing-at-IU is the safest data case but the lowest emotional stake.

#### §7.3.4 Inverse proof — keep or cut?

Spec's "without Gemma, FutureProof is a 300-entry lookup table" is intellectual credibility. Guidance is silent on inverse-proof framings — judges want the wow demo, not the contrastive argument. **Recommendation:** keep it in the writeup as a one-line aside; cut it from the video.

#### §7.3.5 Reinforcement-loop / community suggestions

Spec's strongest narrative beat — and **guidance's archetype doesn't cover it**. No 3n winner had this. This is genuinely differentiating: a self-improving local product. **Recommendation:** lead Technical Depth section with this; it's the unique technical move the guidance demands ("one unique technical move — fine-tuning, novel cascade, etc. Not 'we wrapped Gemma in a chatbot'").

### §7.4 What's missing from BOTH that we need

- **Performance benchmark on named consumer hardware** — both call for it; we don't have a clean number anywhere. Pick a target (M2 Air? Lenovo IdeaPad?) and measure tok/s + cold-start + RAM peak.
- **Evaluation table** — guidance requires it. We have stress-recon scripts in `scripts/` (`stress_recon.py` through `stress_recon6.py`, `stress_data_recon.py`, plus `reports/stress-test-findings.md`) that probably already contain this work — needs tabulation for the writeup.
- **Third-party validation footage** — guidance flags as highest-leverage; neither artifact accounts for whether Jeff has access to a teacher/counselor.

### §7.5 Synthesized writeup structure (merging both)

The recommended structure when drafting begins:

```
## Hook — [named persona] [PERSONA-FIRST per guidance]
## The Problem — Impact & Vision [RUBRIC HEADER per guidance]
   - 1.6B students globally; X million lack a real counselor
   - Spec's "fragmented federal data" thesis as PARAGRAPH 2 [SPEC §1 thesis]
## The Solution: FutureProof in 60 seconds [GUIDANCE §A.3]
## Why Gemma 4 (and why local) [GUIDANCE §A.4 + SPEC's "Built on Gemma" framing]
## Technical Depth & Execution [RUBRIC HEADER per guidance]
   - Reinforcement-loop architecture (THE unique technical move) [SPEC strongest beat]
   - Tool-calling on local Ollama, MCP server, 10 tools [SPEC + README]
   - Multi-model routing (E2B / 26B MoE) [GUIDANCE §F]
   - Performance: tok/s on M2 Air, RAM, cold-start [GUIDANCE]
## Demo & Evaluation [RUBRIC HEADER per guidance]
   - Embedded video at top
   - Marketing-at-IU pioneer correction as the demo beat [SPEC §2.1]
   - Eval table: N personas, accuracy, latency dist [GUIDANCE §A.6]
   - Multilingual demo (Spanish + Arabic) [GUIDANCE §E]
## Impact Story & Roadmap [RUBRIC HEADER per guidance]
## Reproducibility [RUBRIC HEADER per guidance]
   - One-command setup [GUIDANCE]
   - Apache 2.0, repo link, video link
   - Closing: "Built for Gemma 4 Good Hackathon — Main + Future of Education + Ollama tracks" [GUIDANCE multi-track]
```

### §7.6 Open questions for Jeff (resolve before drafting)

1. **Persona** — daughter (most authentic), a recruited student, or a named archetype?
2. **Demo case** — keep Marketing-at-IU per spec, or pick something with higher emotional stakes (deaf education / special ed / first-gen)?
3. **Hardware floor** — what machine to benchmark on? (Need tok/s, RAM, cold-start.)
4. **Eval table** — do the existing `scripts/stress_recon*.py` outputs already give us a 15–20-persona table, or do we need to run a fresh one?
5. **Third-party footage** — do you have access to a teacher/counselor willing to record 30 seconds this week?
6. **Multi-track** — Main + Future of Education + Ollama, or narrower?

Once these are answered, the writeup itself can be drafted in a single pass against §7.5.
