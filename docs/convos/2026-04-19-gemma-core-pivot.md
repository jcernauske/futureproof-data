# Session Summary — Gemma Moves to the Core

**Date:** 2026-04-19
**Participants:** Jeff Cernauske (founder) + Claude Code
**Entry point:** `docs/specs/feature-gemma-alias-curation.md` handed off for execution
**Exit state:** Cache spec DEFERRED, Gemma-determinism shipped, flagship `feature-set-your-course.md` drafted + design-locked, five placeholder / skeleton specs landed, Brightpath HTML mockup shipped, V2 YAML regression running in background window.

---

## 🚪 Re-entry Index (open these first when resuming context)

| Artifact | Path | Purpose |
|----------|------|---------|
| **This conversation log** | `docs/convos/2026-04-19-gemma-core-pivot.md` | Full narrative + decisions + rationale |
| **Flagship spec** | `docs/specs/feature-set-your-course.md` | The May-18 build; unified screen, chip flow, community suggestions, receipts |
| **Brightpath HTML mockup** | `docs/specs/design/set-your-course-mockup/index.html` | 15 scenarios, sticky left-rail index, `open <path>` directly in a browser |
| **Visionary design proposal** | `docs/specs/design/set-your-course-visionary-proposal.md` | Wireframes, motion specs, tokens, component tree, 40-second demo walk |
| **PM critique** | `docs/specs/design/set-your-course-pm-critique.md` | Product stress-test of the spec's design intent |
| **V2 YAML regression** | `docs/specs/completed/bugfix-disable-intent-yaml-regression.md` | REOPENED with anchored methodology; running in the other window |
| **Receipts spec (sources-as-feature)** | `docs/specs/feature-receipts.md` | Data provenance discipline across every prose surface |
| **School Discovery (v0.5 stub carved)** | `docs/specs/feature-school-discovery.md` | Destination for the `school_gap` CTA from Set Your Course |
| **Kaggle narrative pin** | `docs/specs/submission-kaggle-narrative.md` | Writeup + video beats, the "reasoning bridge" + "no static lookup" thesis |
| **Guardrails TODO** | `docs/specs/feature-chat-guardrails.md` | Injection defense, meme redirect (§3), probe-flip (§3.1) — blocks external ship |
| **Gemma availability TODO** | `docs/specs/feature-gemma-availability.md` | Outage mitigation strategy (YAML break-glass, community fallback, pre-warm) |
| **Tool-calling migration TODO** | `docs/specs/feature-gemma-tool-calling-migration.md` | P0-P2 priority plan for migrating pre-inject call sites to MCP tool-calling |
| **Cache spec (DEFERRED)** | `docs/specs/feature-learned-alias-cache.md` | Superseded conceptually by Set Your Course + Receipts |
| **Alias-curation spec (SUPERSEDED)** | `docs/specs/feature-gemma-alias-curation.md` | Original YAML-alias-generation spec; architecturally dead |

**Code shipped this session:** `backend/app/services/gemma_client.py` (added `seed` param), `backend/app/services/intent.py` (temperature=0, `_derive_intent_seed`), `backend/tests/services/test_intent.py` (+4 determinism tests). 37 + 137 tests pass, ruff clean, mypy unchanged from main.

---

---

## Executive Summary

This session started as a routine spec execution and ended with a fundamental repositioning of the product. The pivot: **Gemma moved from "decorative narrator" to "core reasoning engine"** in both the architecture and the Kaggle submission narrative.

Three cascading realizations drove it:

1. **The spec in front of us was wrong for the hackathon.** `feature-gemma-alias-curation.md` would have used Gemma at pipeline time to pre-generate aliases — the exact opposite of "watch Gemma reason on stage." A product-partner review (brought in per founder's ask) called it directly: judges reward ambitious Gemma use, not efficient avoidance.
2. **With temperature=0 + input-derived seed shipped this session, the YAML's only remaining advantage collapsed.** Determinism was its raison d'être; Gemma can now deliver the same guarantee. Latency (500ms–2s) becomes a *feature* in a Gemma-sponsored demo, not a bug.
3. **The founder's insight — "the student should be able to push back on Gemma when it gets it wrong" — became the flagship feature.** Unified School/Major/Careers screen with a kid-voiced correction chip that triggers visible Gemma debug reasoning. This displaced boss narration as the #1 Gemma-maximal build for the remaining 29 days.

Along the way we shipped a deterministic-Gemma bugfix, parked the original alias-curation spec, drafted a standalone YAML regression bugfix spec, scoped the flagship Set Your Course spec to §1–§11 completeness, and captured four placeholders (chat guardrails, Kaggle narrative, Gemma availability mitigation, and the Set Your Course feature itself before it was filled in).

The final reframe: **without Gemma, FutureProof is a 300-entry lookup table covering 3% of real student vocabulary. With Gemma, it's the reasoning bridge across five fragmented federal taxonomies that every school can afford to run locally.** That is the Kaggle pitch.

---

## Topic 1: Architecture Review of `feature-gemma-alias-curation.md`

### What was discussed

The spec proposed using Gemma at pipeline time (not runtime) to pre-generate 2–8 aliases per hand-curated YAML entry, then ship them baked into `data/reference/major_to_cip.yaml`. Three agents reviewed in parallel per the spec's Claude Code Prompt:

| Reviewer | Scope | Verdict |
|----------|-------|---------|
| `@fp-architect` | Data flow, idempotence, atomic writes, pipeline placement | CHANGES REQUESTED |
| `@fp-data-reviewer` | Alias validation rules, collision detection, coverage floor | CHANGES REQUESTED |
| `@genai-architect` | Gemma prompt body, JSON schema, fallback, rate limits | CHANGES REQUESTED |

### Key findings (pros/cons of the spec as written)

**Material design issues (con):**
- `@fp-architect`: "Atomic YAML write" was promised but the mechanism (tempfile + `os.replace`) was never named. A Ctrl-C mid-write could truncate the file. Log/YAML write ordering was unspecified. Cross-entry collision checking was racy under concurrency=4.
- `@fp-data-reviewer`: The "SOC ≥ 3 floor" was documented as "enforced upstream" but the regenerator's `_fetch_crosswalk_cip4s` selects the column and *never gates on it* — false claim. Worse: generic `XX.01` entries with empty aliases would absorb plain tokens like `"business"`, shadowing Finance/Marketing/etc via first-match-wins. And the spec's `argparse` patch referenced scaffolding that didn't exist.
- `@genai-architect`: `max_tokens=200` was marginal (verbose 8-alias responses could hit `finish_reason=length`). Missing `rfind("}")` trailing-prose guard. `_request_aliases_for_entry` was using sync `generate` instead of `generate_async`, bypassing the module semaphore.

**Pros of the spec (what was defensible):**
- Idempotence via JSONL sidecar log.
- Preservation of hand-curated entries byte-for-byte.
- Validator structure was reasonable.
- Cost estimate (< $1 for a full pass) was defensible.

### Decision
- **STOP and escalate per the Claude Code Prompt's rule for CHANGES REQUESTED.** No implementation.
- Flagged findings in §5 of the spec file itself.

### What this set up
The reviews exposed that the work was worth doing technically but the founder hadn't been asked whether the *feature* was even right for the hackathon. That question was asked next.

---

## Topic 2: Founder's Strategic Reframe — "Can't Gemma Just Figure It Out?"

### What was discussed

Jeff's pushback: "Why are we screwing around with the YAML? Can't Gemma just figure it out on the fly? Student says ISU, enters marketing, it gets mapped to Business/Commerce, no marketing jobs. Can't Gemma step in and augment the mapped careers with careers the student probably wants?"

This collapsed two separate problems:

1. **Major resolution** — "what did the student mean?" The YAML + Gemma tiered path already handles this.
2. **CIP substitution at a specific school** — "this school doesn't offer that exact CIP, now what?" This is the actual source of the IU-Marketing-gets-Business/Commerce pain.

### Pros / cons of the reframe

**Pro:** Gemma as a real-time reasoner on top of fragmented data is genuinely more powerful than any pre-computed alias list. It addresses the *product* problem (student feeling misunderstood), not just the *technical* problem (typed-input-doesn't-match-YAML).

**Con:** Conflates two surfaces. Alias curation is about input normalization; career augmentation on substitution is about output reconciliation. Fixing one doesn't fix the other.

### Decision
- Acknowledge both problems as separate specs.
- Alias curation spec still has the conversation's attention but is now "probably wrong work."
- Career augmentation idea is noted as a future spec.

### What this set up
Jeff then proposed a reinforcement loop — which became the learned-alias-cache spec.

---

## Topic 3: The Reinforcement Loop Idea → Learned Alias Cache

### What was discussed

Jeff: "Can we build a reinforce loop? Gemma presents options, student accepts, that gets logged, we build up a cache of matches on the fly so something like the YAML evolves over time based on user responses."

Architecture proposed: three layers (YAML curated → learned cache from student behavior → Gemma creative fallback). Every resolution logged to `data/reference/learned_aliases.jsonl`. Every student confirmation = acceptance signal. When `accepted_count >= 3 AND accepted_count / seen_count >= 0.6`, the cache serves future matches for that input.

### Deliverables at this stage
- `reports/proposal-learned-alias-cache-2026-04-19.md` — proposal document, design decisions, scope for hackathon, open questions.
- `docs/specs/feature-learned-alias-cache.md` — full §1–§11 spec: 10 decisions, 22 P0/P1/P2 tests, resolution_id round-trip design, threshold math, JSONL schemas, integration with existing `POST /intent/confirm`.
- Supersedes the original alias-curation spec (on COMPLETE).

### Pros
- Self-improving — the system gets better with every student.
- Kaggle-narrative-strong: "gets smarter every student; Gemma needed less every day."
- Tight hackathon scope (append-only log, no auto-promotion to YAML).

### Cons (this became the next topic)
- Designs infrastructure whose explicit purpose is to *avoid calling Gemma*.
- Demo story is the absence of a thing (cache hit = no Gemma).
- Optimization work masquerading as a feature when visible Gemma usage is the submission goal.

### Decision at this stage
- Draft the spec + proposal.
- Open in Typora for review.
- Founder asked: "make YAML optional via config for testing AND consult the new PM agent."

### What this set up
The PM agent said the cache was the wrong feature. That tore everything down and rebuilt the plan.

---

## Topic 4: Product Partner Review — "Wrong Feature for the Hackathon"

### What was discussed

`fp-product-partner` agent (new, not-yet-registered — invoked via general-purpose with its persona loaded) evaluated whether "a system designed to reduce Gemma calls" is smart in a Gemma-sponsored hackathon.

### PM's verdict (pros / cons in their voice)

**Core argument against the cache:**
1. **Judge psychology.** DeepMind judges reward *ambitious Gemma use that couldn't happen without Gemma.* Not "efficient avoidance." The submission track is literally named for Gemma.
2. **Narrative coherence.** "The system gets smarter; Gemma needed less" reads as "we're proud Gemma is increasingly unnecessary" — actively corrosive at a sponsor's hackathon.
3. **Demo math.** 3 minutes of video. Cache hit = absence of a thing. "Watch Gemma figure out what this student means" = presence of a thing. Every second of video should be visible Gemma work.
4. **Counterfactual is weak.** Latency is fine (tape is controlled), determinism is fine (inputs are controlled), cost is zero (local Ollama). The cache solves problems we don't have until October.
5. **Real demo risk** — Gemma resolving "CS" differently across runs — is solved with a 15-minute `temperature=0` + seed change. Not a 12-decision spec.

**PM's proposed alternatives (Gemma-maximal builds, ordered by leverage):**
1. **Boss fight narration** grounded in the student's pentagon + occupation_profiles + ai_exposure. 3–5 days. Visceral "only Gemma could do this" beat.
2. **"Why this path?" rationale** on Stage-3 branch edges. Structured data in, one-sentence rationale out per edge.
3. **Compare-mode chat with tool-calling.** Extends existing shipped compare screen. Local Ollama + tool-calling = headline-grade.

### Decision

Founder chose **option (3) Hybrid:**
- Ship the temperature/seed fix immediately.
- Park the cache spec as DEFERRED.
- Pivot to Gemma-maximal work (spec TBD).

### What this set up
A 30-minute code change and a major strategic redirect.

---

## Topic 5: Shipped — Deterministic Intent Resolution

### What was shipped

Live code changes in `backend/app/services/`:

**`gemma_client.py`:**
- Added optional `seed: int | None` parameter to `generate`, `generate_chat`, `generate_async`, `generate_chat_async`.
- Forwarded to `chat.completions.create` when set.
- Logged in `logs/gemma.jsonl`.

**`intent.py`:**
- `_call_gemma_intent` now uses `temperature=0.0` (down from 0.1).
- Added `_derive_intent_seed(prompt_input)` — normalizes input and returns a 32-bit uint from the SHA-256 digest.
- Passes the derived seed into `gemma_client.generate`.

**Tests (`backend/tests/services/test_intent.py`):**
- Loosened the one strict mock to `**kwargs` (was blocking new `seed` kwarg).
- Added `TestDeterministicIntentCall` class with 4 tests: seed determinism, input variance, 32-bit range, wire-through verification.

**Validation:**
- 37/37 intent + gemma_client tests pass.
- 137/137 gemma-mocking tests across the broader surface pass.
- Ruff clean. Mypy errors unchanged from main (actually dropped 1 due to the `completion_kwargs` refactor).

**Cache spec parked:**
- `docs/specs/feature-learned-alias-cache.md` status → DEFERRED with PM reasoning.
- `reports/proposal-learned-alias-cache-2026-04-19.md` status → DEFERRED with link back.

### Pros / cons of the approach

**Pros:**
- Solves the real demo risk (non-deterministic output) in 30 minutes.
- Purely additive API change — no existing callers break.
- Seed derivation is deterministic across Python processes (SHA-256, not `hash()`).

**Cons:**
- Cli.py still uses `temperature=0.1` in its copy of `_call_gemma_intent`. Left alone (CLI isn't in the Kaggle demo path) but flagged.

### Decision
- Shipped. Validated. Moved on.

---

## Topic 6: Full App-Flow Walkthrough + The Real Flagship

### What was discussed

Jeff walked through the app flow:
> "Landing → name → school/major/career search, Gemma matches (how in new model?) → focus/loan slider → where could this degree take you? How does Gemma analyze career paths? YAML out?"

I explored the codebase to answer concretely. Findings:

| Step | Screen | Gemma activity |
|------|--------|----------------|
| 1 | Landing (static) | — |
| 2 | Profile/Name | Gemma-generated animal emoji (already live) |
| 3 | **SchoolMajorScreen** — school + major + effort/loans **on ONE screen, but presented as separate steps** | `POST /intent/` — YAML → Gemma tiered match |
| 4 | CareerPickScreen | `POST /build/tier` — Gemma classifies careers into common/less-common/stretch |
| 5 | RevealScreen | `POST /build` — **8 concurrent Gemma calls:** 5 boss narrations + skill recs + skill pool + guidance |

**My position on "YAML out?":** Strong case to pull it now.
- Determinism (YAML's defining advantage) just evaporated with temp=0 + seed.
- Latency (500ms–2s) is a *feature* in this demo — visible Gemma work.
- Narrative hygiene: "Powered by Gemma" + "we hardcoded 56 entries to avoid calling it" sit uneasily together.
- Keep the file as a test fixture + NCES-name canonical doc; bypass in `resolve_intent()`.

### Jeff's correction + strategic leap

Jeff corrected me: the screens are *presented as separate steps* to the user, even if they're implementation-coupled. Then the big insight:

> "Each screen has a bunch of intertwined intentions: what school, what field, what degree, what jobs does it lead to. Seeing all four at once lets the student have the key insight: 'I was wrong about what I wanted to study.' Separate screens hide that insight."

And:

> "If we disable YAML, Gemma might get it wrong. Student at IU types Marketing, gets Business/Commerce, says 'where the FK are the marketing jobs?' — student needs to be able to course-correct Gemma. Gemma says 'this school reports data in a funky way, let me get what you want.' That's a strong Gemma showcase moment."

And:

> "Record that, provide as hint next time."

And:

> "Two modes? (a) backfill from target occupation, (b) project from school/major. Students often know what they want to BE more than what they want to STUDY."

### PM consulted again

`fp-product-partner` reacted:

1. **Does this displace boss narration as #1?** Yes — partially. Boss narration is decorative Gemma. This is *load-bearing* Gemma on the critical path of the product's thesis. Judges have seen 200 narration demos; they've seen zero "student argues with the model and the model concedes with data" demos.
2. **Unified screen vs stepped.** Founder is right. Zillow/Kayak, not Tinder. Interdependent decisions need simultaneous visibility.
3. **Conversational correction.** Genuinely different from the cache. The cache *avoided* Gemma calls; this *multiplies and exposes* them.
4. **Two modes.** Cut occupation-first for v2. Scope can't hold two at ship quality.
5. **Sequence:** unified screen (2 weeks) → boss narration (1 week) → demo polish (final week).
6. **Ruthless cut:** drop "record the correction as a hint." The correction IS the magic; persistence is v2.

### I partially dissented on the PM's ruthless cut

Keep an append-only log (`data/reference/student_corrections.jsonl`) that the app *never reads* — 2-line code cost, free demo artifact ("here's real beta-week student feedback"), v2 option value preserved. The PM said cut persistence; I said cut the *read path*, keep the *write path*.

### Decision

Founder chose:
1. **Unify the screens** (yes).
2. **Spec the YAML disable + regression separately** (yes).
3. **Add a guardrails spec placeholder** — we don't need to figure it out now, but don't lose it.

### What this set up
Three specs landed in parallel. See Topic 7.

---

## Topic 7: Three Specs Drafted

### Specs created in parallel

**`docs/specs/feature-chat-guardrails.md` (TODO stub)** — captures the obligation: prompt injection, off-topic requests, adversarial input, PII, hallucinated facts, brand/voice risk, rate limits, demo safety, local-vs-cloud parity. Blocks external-audience ship of Set Your Course; does not block dev-team build.

**`docs/specs/bugfix-disable-intent-yaml-regression.md` (DRAFT, standalone)** — small spec:
- Add `INTENT_YAML_ENABLED` env var gate to `resolve_intent` (default `true` preserves today's behavior).
- Script: `scripts/yaml_regression.py` — enumerates every (major, alias) pair from the 56 hand-curated YAML entries, runs each through live Gemma at temp=0+seed with YAML disabled, writes a markdown comparison report.
- Architecture/design/code-review phases SKIPPED by the Claude Code Prompt — low-risk additive toggle + offline script.
- Unblocks Set Your Course's commitment to disable YAML in prod.

**`docs/specs/feature-set-your-course.md` (DRAFT, flagship, §1–§11 + §12)**:
- Unified screen replacing three current screens.
- Streaming Gemma resolution on major input change.
- Ask Gemma chat surface (at this stage — later revised to chips).
- Correction log (append-only, never read).
- No occupation-first mode (v2).
- No cache reads (v2).
- No multi-turn persistence (v2).
- §12 **Shipping Gate** — hard block on external-audience release until `feature-chat-guardrails.md` is a real spec + implemented.

### YAML regression spec launched into background execution.

---

## Topic 8: The Gemma-as-Core Reframe

### What was discussed

Jeff's question: "Is it fair to say that Gemma now becomes core to this product, as it serves as the bridge across inconsistently reported or fragmented data?"

### The shift articulated

**Before:** Gemma was a *narrator*. Data was pre-computed (YAML → CIP → substitution → tiering → DuckDB joins), Gemma painted prose on top. Pull Gemma out; product still works, mutely.

**After:** Gemma is the *reasoning bridge* across five taxonomies that were never designed to fit together — CIP (programs), SOC (occupations), IPEDS (institutions), FIPS (regions), and free-text student vocabulary. Pull Gemma out; the student gets a static crosswalk — the reductive view the product exists to transcend.

### The inverse proof (Jeff's sharpening)

> "If we didn't have Gemma we'd only have this stupid little YAML file that would cover some x% (miniscule) of the scenarios."

I quantified:
- 56 curated entries × ~5 aliases = ~300 exact-match surface forms.
- Real student vocabulary: 1,500+ CIP codes × dozens of variants × typos ≈ 10,000+ possible inputs.
- **YAML-only coverage: ~3%.**

Without Gemma, every surface degrades:
- Intent resolution: 97% fall-off rate.
- Crosswalk weirdness: silent wrong substitutions.
- Career tiering: impossible without per-family hand rules.
- Boss narration: templates.
- Guidance: gone.
- "I was wrong about my major" insight: never surfaces.

The one-line thesis that emerged:
> *"Without Gemma, FutureProof is a 300-entry lookup table wrapped in a nice UI. With Gemma, it's the career-planning tool every school can actually afford to run."*

### Decision

- Create two more placeholders to pin the framing and the risk.

---

## Topic 9: Two More Placeholders

**`docs/specs/submission-kaggle-narrative.md` (TODO)** — pins:
- The "Gemma as reasoning bridge across fragmented public data" thesis.
- The inverse proof (300 entries = 3% coverage).
- Five demo beats ordered by screenshotability (Marketing-at-IU correction is the money shot).
- Kaggle writeup spine (8-section structure).
- Quantitative anchors to verify before ship.
- Voice contract (`docs/reference/voice-guide.md`).

**`docs/specs/feature-gemma-availability.md` (TODO)** — captures the new risk and mitigations:
- Risk: Gemma on critical path = Gemma outage = product outage. No static fallback for *reasoning*.
- Five candidate mitigations ordered by strength:
  - (a) Break-glass YAML fallback.
  - (b) Last-good-resolution cache (narrower cut of the deferred cache spec).
  - (c) Local Ollama as hot fallback when OpenRouter fails.
  - (d) Graceful degradation with explicit messaging.
  - (e) Demo pre-warm.
- Eight specific failure scenarios the real spec must address.
- Observability requirements.

---

## Topic 10: Chips vs Chat (Final Design Pivot)

### What was discussed

Jeff's question:
> "Could we get away with chips? Are the reasons why something is not shown limited and known? Instead of saying 'Why are you not seeing Marketing?' user clicks a chip that calls a detailed prompt directing Gemma through a known debugging loop."

### The seven-bucket taxonomy of "I don't see X"

| # | Failure mode |
|---|-------------|
| 1 | School reports program under broader CIP (IU-Marketing case) |
| 2 | Jobs exist but in less-common tier the student hasn't revealed |
| 3 | Student's school doesn't offer the target program |
| 4 | Privacy-suppressed small program (IPEDS small-n) |
| 5 | Semantic mismatch in major name |
| 6 | Target SOC not well-mapped in crosswalk |
| 7 | Peer school variance |

Seven buckets. Bounded, not open-ended.

### Pros/cons of chips vs open chat

**Pros of chips:**
- Demo-tighter (reproducible on video).
- Guardrails surface collapses to one scoped clarifier — days of work, not weeks.
- Smaller build — no conversation store, no multi-turn state, no message history.
- More Gemma-maximal per tap — each chip's prompt is longer and more specific than a free-form turn.

**Pros of open chat:**
- "Open dialogue" feel.
- Handles questions outside the seven buckets.

**Cons of chips (original engineer-voiced labels):**
- Jeff: "A kid is never going to tap 'this school reports oddly,' they're going to tap 'I don't see my shit.'"
- Seven chips asks the student to self-diagnose.

### The collapse (decision)

**Three chips, one Gemma-heavy:**

| Chip | Kid voice | Gemma? |
|------|-----------|--------|
| "Not what I expected" | Honest about the feeling | **Yes** — opens scoped clarifier ("What were you hoping to see?"), then Gemma classifies internally into one of 7 buckets (+ 8th "no_issue_found") and runs the right debug trace with tool calls |
| "Show me less common paths" | Utility | No — frontend toggle on existing tier data |
| "Wrong major" | Reset | No — clears the major input |

**One Gemma-heavy chip** = the money-shot demo moment. **Two mechanical chips** = no Gemma cost, still useful UX.

**Gemma does more reasoning per tap** (classify + respond + optionally update resolution) than an open-chat turn would. The student never sees the buckets.

### Impact on specs

**`feature-set-your-course.md` heavily revised** (same session):
- §1 Overview rewritten: three kid-voiced chips + scoped clarifier, not chat.
- §1 Success Criteria: chip-specific behaviors.
- §2 Decision #3: "interaction is chip-based, not chat-based" replaces "conversation is session-local."
- §2 Decision #5: `_CHIP_ROUTING_SYSTEM_PROMPT` with full 8-bucket taxonomy + IU-Marketing worked example + dual structured tails (`---UPDATED_RESOLUTION---` optional, `---BUCKET---` always).
- §2 Decision #10: soft nudge on low-confidence commit (not hard gate).
- §3 UX brief: chip rail + clarifier modal, not conversation thread.
- §4 Architecture: no conversation history in state. `POST /intent/chip` replaces `POST /intent/chat`.
- §4 Data Models: `ChipRequest` / `ChipResponse` with 8-value `bucket` literal. `ChatTurn` removed.
- §4 Testing: `TestChipDispatch` replaces `TestChatTurn`. New tests for skip-gemma mechanical chips, bucket-parsing, missing-clarifier 422.
- §10 Discussion: documents the chat→chips evolution with Jeff's exact framing ("a 17-year-old is not going to tap 'this school reports oddly,' they're going to tap 'I don't see my shit'").

**`feature-chat-guardrails.md` narrowed**:
- Scope collapsed from "open chat surface" to "one bounded free-text clarifier + existing major-text field."
- Multi-turn jailbreak resistance, persona drift, long-context PII leakage — all removed as applicable concerns.
- What remains: clarifier injection, PII masking, hallucination discipline, rate limits, voice enforcement.
- Effort estimate: weeks → 2–3 days.

---

## Topic 11: Pre-Inject vs Tool-Calling — The Architectural Half-Finish

### What was discussed

Jeff: "It seems weird that we've built this beautiful pipeline of bronze/silver/gold products, built MCP servers, and then just pass text?"

The observation is correct. The runtime architecture is inconsistent with what we built:

- **What we built:** Brightsmith Bronze → Silver → Gold pipeline with data contracts; a DuckDB Gold warehouse; an MCP server exposing eight Gold-zone tools (`get_career_paths`, `get_occupation_data`, `get_ai_exposure`, etc.) — a complete navigation layer for a Gemma reasoning agent.
- **What we actually run:** ~90% of Gemma calls use pre-inject — backend Python queries DuckDB, string-formats the results, injects into the prompt via `.format()`, ships it to Gemma. The MCP server is bypassed by the only app that was supposed to use it.

The effect is that we've quietly demoted Gemma from "reasoning engine" to "template autocompleter" for most call sites. That undermines the "Gemma as reasoning bridge across fragmented data" thesis — Gemma can't *navigate* the data; it just stares at what we pre-selected.

### Pros / cons of each pattern

**Pre-inject (current default):**
- Pro: simpler, no function-calling round trips, no parsing of tool calls, predictable token/latency cost.
- Pro: works uniformly across backends even when Ollama-side function-calling maturity is uneven.
- Con: Gemma can't ask for data we didn't think to inject.
- Con: token waste (we inject data Gemma ignores).
- Con: product decisions about what Gemma should see happen before Gemma sees the student — the opposite of adaptive reasoning.
- Con: weakens the Kaggle narrative. "Gemma reasons over fragmented data" is hollow if Gemma isn't navigating it.

**Tool-calling via MCP:**
- Pro: lets Gemma ask for third-order context we didn't think to inject.
- Pro: grounded claims (Gemma can only cite what it fetched).
- Pro: no token ceiling on what Gemma can reach.
- Pro: tool-calling on local Ollama is a headline-grade demo moment.
- Con: reliability varies per-backend.
- Con: can runaway-loop if not capped.
- Con: latency (N round trips).

### Decision

**Don't do a full migration in the 29 days before 2026-05-18.** Scope risk.

**Do insist that every new flagship Gemma surface is tool-call-first.** That already applies to Set Your Course (§4 Decision #6). The boss-narration spec (PM's #2 priority, not yet drafted) should be tool-call-first too. Outcome: the two headline Gemma moments in the demo video both showcase tool-calling on local Ollama — enough to prove the architecture works and demo what the MCP server exists to do.

**Post-hackathon**, migrate existing pre-inject call sites in priority order (captured in the new placeholder spec).

### Priority order for post-hackathon migration

1. **P0 — `boss_fights.py::narrate_one`** — demo headline if not shipped as tool-call-first in Week 4 already.
2. **P0 — `guidance.py::generate_guidance_async`** — "Gemma's Take" is the post-reveal flagship; grounding it in live tool calls is a big UX + narrative upgrade.
3. **P1 — `career_tiering.py::tier_careers`** — explainable tier placement beats single-shot classification.
4. **P1 — `skill_recs.py`** — cite specific O*NET tasks via `get_task_breakdown`.
5. **P2 — `skill_pool.py`** — secondary surface; tool-calling is nice-to-have.
6. **Leave alone** — `intent._call_gemma_intent` (pre-inject fits small deterministic context well); `career_pick_qna.ask` (chip surface is already bounded); `school_lookup._gemma_resolve_major` (narrow fallback path).

### Impact

- New placeholder spec: `docs/specs/feature-gemma-tool-calling-migration.md` — TODO, captures the migration plan with the priority ordering above.
- When the boss-narration spec is drafted, it must be tool-call-first from day one (cross-referenced from the placeholder).
- `submission-kaggle-narrative.md` updated to note that *MCP tool-calling on local Ollama* is the architectural showcase the submission should foreground, not an implementation detail.

---

## Topic 16: Receipts — Data Provenance as a First-Class Feature

### The founder's follow-up catch

After the Topic 15 voice-rule fix (no CIP / SOC / crosswalk / numeric codes to students) landed, the founder immediately flagged the replacement copy as having its own problem:

> *"At IU, Marketing coursework is filed under the broader Business program — so that's what lands on the card first. Filed with whom? Marketing at IU maps to Business/Commerce — maps where? Perhaps we need to promote the 'receipts' concept to a first-class feature under this spec."*

Passive voice ("filed," "maps") without a named authority is worse than jargon — it raises *mystery* where jargon raised *gibberish*. The real answer is: *filed to the Integrated Postsecondary Education Data System (IPEDS) — the U.S. Department of Education's federal school-reporting system.* Saying so by name is both specific and trust-building.

### The fix — promote "receipts" to a first-class product surface

Data provenance becomes its own feature, not an offhand comment in prose:

1. **New spec: `docs/specs/feature-receipts.md`** — DRAFT (SKELETON) + v0.5 STUB carved for hackathon. Establishes the canonical source registry, the acronym spell-out rule, inline Gemma citation discipline, and card-footer attribution.
2. **`feature-set-your-course.md` amendments:**
   - §2 Decision #13 (Receipts) — every factual claim cites its source; career preview cards carry footer attribution.
   - §2 Decision #14 (Acronym spell-out rule) — first reference per view uses full name + parenthetical acronym.
   - Chip-routing prompt extended: new mandatory citation rule + `{sources_for_prompt_context}` interpolation slot.
3. **Mockup + visionary proposal scrubbed** — example passage rewritten from *"IU files Marketing coursework under its Business program"* (mysterious) to *"In IU's submission to the Integrated Postsecondary Education Data System (IPEDS), Marketing is filed within its Business program. The Bureau of Labor Statistics (BLS) still tracks graduate placements in marketing roles…"* (specific, sourced, parent-respectable).

### Founder-introduced acronym rule

> *"Any acronyms must spell out the whole thing and then include the acronym in (). Bureau of Labor Statistics (BLS)."*

Codified as §2 Decision #14. First reference **per rendered view** (not per-session, not per-app — views are the right granularity because students bounce between surfaces). Subsequent references within the same view may use the acronym alone. Applies to sources (BLS, IPEDS, O*NET, BEA, College Scorecard, Karpathy AI Exposure Index, Anthropic Economic Index). Does NOT apply to taxonomies (CIP, SOC, crosswalk — those stay forbidden outright).

### Why this matters beyond copy

- **Trust.** Large language models hallucinate. FutureProof reads public federal data and reasons with Gemma; every claim has a receipt. Surfacing that explicitly is the product's anti-hallucination flex.
- **Parents.** "According to the Bureau of Labor Statistics (BLS)…" is the register parents respect. It converts a suspicious LLM tool into a credible career-planning resource.
- **Demo.** A career card showing *"Data from Bureau of Labor Statistics (BLS) · College Scorecard 2023 · Occupational Information Network (O*NET)"* is screenshot-worthy in the Kaggle video. It's the opposite of what a typical LLM demo looks like.
- **Voice integrity.** The voice guide already says "data-honest." Hiding sources is not data-honest. Citing them is.

### Impact on specs

- New: `docs/specs/feature-receipts.md` — DRAFT / SKELETON with v0.5 hackathon scope.
- `feature-set-your-course.md` — §2 gains Decisions #13 + #14; chip-routing prompt extended with citation rule.
- `docs/specs/design/set-your-course-visionary-proposal.md` — amendment note updated to reference all three stacked voice rules (taxonomy + receipts + acronyms).
- `docs/specs/design/set-your-course-mockup/index.html` — 4 copy passages rewritten to cite sources explicitly.
- Future dependencies: every Gemma prompt that produces student-facing prose (boss narration, guidance, skill recs, etc., when their specs land) inherits the citation rule + acronym rule. `feature-gemma-tool-calling-migration.md` implementers should pick up the prompt template from receipts.py.

---

## Topic 15: Voice Rule — No Internal Taxonomy Leakage to Students

### What the founder caught

Reviewing the mockup, the founder: *"Students won't know wtf a CIP is. They won't know what a crosswalk is. They won't know what these codes mean. They won't know what a SOC is."*

Correct, and embarrassing. The mockup was leaking `CIP 52.02` as a rendered pill, `crosswalk quirk` as a pill label, `52.14` and `reachable from 52.02` in prose — every surface a 17-year-old would bounce off. The spec's chip-routing prompt also had no explicit rule forbidding Gemma from echoing these terms back to the student.

### Fix (applied same session)

1. **New spec rule** — `feature-set-your-course.md` §2 Decision #12: "Zero internal-taxonomy leakage to students." No `CIP`, `SOC`, `crosswalk`, or numeric codes in UI or Gemma output. Enforced at four layers:
   - Prompt: the chip-routing system prompt has an explicit forbidden-terms rule.
   - Schema: the `---CAREERS---` structured tail now has a `display_reasoning` field (student-facing, scrubbed) alongside `reasoning` (engineer-facing, free to use taxonomy for logs/audits).
   - Frontend: student-facing pill labels are mapped per §4 Feasibility Classification (e.g. `crosswalk_quirk` → "Through [Business] program", `direct_hit` → "Direct match").
   - CI / pre-merge audit: a regex check `CIP|SOC|crosswalk|\d{2}\.\d{2}` against JSX strings in the Set Your Course screen catches regressions.

2. **Mockup scrubbed** — every `CIP 52.02` pill removed, every "crosswalk quirk" pill relabeled to "Through Business program", every numeric code stripped from prose. The two grep false positives that remain are (a) the word "social" (not "SOC") and (b) the `cip=52.14` URL query parameter, which students never see.

3. **Visionary proposal amended** — a voice-rule note at the top references §2 Decision #12; all student-facing copy references in the doc were corrected. Internal mode names stay in engineer-facing sections.

### Why this matters beyond copy hygiene

- The product's posture is that students are the ones with agency — we're a tool helping them map their plan to data. Leaking `CIP 52.02` onto a card tells them "this was built for bureaucrats, not for you." That corrodes trust the rest of the UI is trying to build.
- The Kaggle demo is also affected: if the judge screenshots a career card and it reads `CIP 52.02 · crosswalk quirk`, the clip is dead. The correction hardens the demo moments in §1 of `submission-kaggle-narrative.md`.

### Impact on specs

- `feature-set-your-course.md` — §1 Success Criteria adds a zero-leakage requirement + regex-lint check; §2 Decision #12 new; §4 Feasibility Classification adds student-facing pill label mapping + `display_reasoning` field; §4 chip-routing prompt has explicit forbidden-terms rule.
- `docs/specs/design/set-your-course-mockup/index.html` + `styles.css` — scrubbed.
- `docs/specs/design/set-your-course-visionary-proposal.md` — voice-rule note at top; student-facing copy scrubbed throughout.

---

## Topic 14: Design Lock — Visionary Proposal + PM Critique + Founder Calls

### Visionary + PM ran in parallel during V2 regression wait

- **@fp-design-visionary** produced a complete visual design proposal at `docs/specs/design/set-your-course-visionary-proposal.md` — 17 sections covering wireframes (desktop + mobile, all 4 states), motion primitives, token usage map, component tree, interaction timings, accessibility, and a 40-second demo-case walk.
- **Product partner (general-purpose with persona)** produced a critique at `docs/specs/design/set-your-course-pm-critique.md` — stress-tested the spec's design intent, surfaced missing pieces, proposed concrete cuts and non-negotiables.
- **Brightpath HTML mockup** produced by the visionary at `docs/specs/design/set-your-course-mockup/index.html` — 15 labeled scenarios rendering every decision point side-by-side for visual review. No React, no build — vanilla HTML/CSS with Brightpath tokens inlined.

### Synthesis — where they agreed (shipped)

- Clarifier: inline-expansion desktop / bottom-sheet mobile (never modal).
- Paragraph-by-paragraph streaming (not token-by-token, not a spinner) with `gemma-shimmer` keyframe.
- Career preview animates on resolution change via `layoutId`.
- Chip debug trace MUST stream + include at least one visible tool call (non-negotiable).
- IU-Marketing correction is THE primary demo beat (Kaggle narrative updated to name this explicitly).

### Synthesis — where they diverged (founder made calls from the mockup)

| Decision | Visionary position | PM position | Founder call |
|----------|-------------------|-------------|--------------|
| Community Suggestions threshold | Ship with counts visible | Cut below n=3 (creepy at n=1) | **Ship at n=1. Founder: "it's fine, we don't track who the student is."** |
| Chip label: "Show me less common paths" vs "Show me weirder jobs" | Kept spec's original | Proposed "weirder jobs" for kid-voice | **Kept 5A. Founder: "weird jobs is like reptile wrangler, not marketing analyst."** |
| `school_gap` CTA | Full tile treatment | Cut — unbuilt screen | **Ship v0.5 stub.** New §v0.5 Stub Scope carved in `feature-school-discovery.md`: static top-10, no zip, no sort. |
| Soft-nudge copy | Spec default | "Gemma wasn't sure on this one. Worth a sanity check?" | **Adopted PM's wording.** |
| Start Over | No confirm | Add confirm | **Ship the confirm dialog.** |
| Consent-of-loop disclosure | Silent | Recommended one-liner | **Ship with founder draft: "We don't track any identifying info — just that someone found this mapping useful." Flagged for @fp-copywriter polish.** |

### Founder's philosophical correction (biggest change)

> *"The major is never wrong, that's what the student wants. Our mapping of major to job might be wrong."*

Two renames applied across the spec:

1. **Chip label:** "Wrong major" → **"Change my major."** Honors the student revising their plan; does not frame revision as failure.
2. **Chip-routing bucket:** `major_mismatch` → **`intent_divergence`.** Describes a data observation (typed major and clarified career goal don't align in the crosswalk), not a student failure. Bucket #6 rewritten to frame alternative majors as options the student can consider, never as corrections. `ChipId` literal also updated: `wrong_major` → `change_major`.

### Technical additions folded in same pass (from PM critique)

- **280-char clarifier cap** — client-side + server-side Pydantic validator.
- **Chip-stream abort policy** — `AbortController` cancels the in-flight chip stream if the student edits the major; clean slate.
- **`no_issue_found` copy-through** — no more silent dead-end; honest acknowledgment + student stays in control.
- **Tool-call failure retry** — retry once, then note the miss in prose and continue with whatever data Gemma had. No silent swallows, no cascading loops.

### Impact on specs (all propagated this session)

- `feature-set-your-course.md` — §1 success criteria updated, §2 Decision #10 copy + new Decision #11 ("the major is never wrong"), §4 Pydantic models (`ChipId` + `ChipResponse.bucket` literals), §4 chip-routing prompt (bucket taxonomy rewritten, `intent_divergence` scope explicit), §4 tool-call failure policy added, §3 points to the visionary proposal + mockup, §10 Discussion records the design-lock revision.
- `feature-school-discovery.md` — new §v0.5 Stub Scope carved out with file changes and success criteria.
- `submission-kaggle-narrative.md` — IU-Marketing correction named as THE primary demo beat; other beats are support.

---

## Topic 13: Reinforcement Loop Replaces the YAML Entirely

### What was discussed

After Topic 12 confirmed V1 was a flawed test (methodology corrected, V2 pending), the founder pushed back on the premise that we might need to keep the YAML "just in case" Gemma is unreliable. Direct quote: *"I do not want to stick a YAML file in the middle, that's inelegant, doesn't scale, and isolates Gemma."*

Proposal: a **reinforcement loop** that uses the UI itself to manage a dynamically-built replacement for the YAML.

### The flow

1. Student searches (school, major). Gemma resolves live (always — no YAML short-circuit).
2. If the career preview doesn't feel right, student taps "Not what I expected" and types a clarifier ("I want marketing jobs").
3. Gemma runs a **chip-routing debug trace** that actively tool-calls the crosswalk and careers data, finds candidate careers matching the clarifier, and classifies each into one of 5 feasibility modes.
4. Student clicks a surfaced career. The click writes a correction record.
5. Future students with the same (school, input) see Gemma's live resolution PLUS a "Other students searching X at Y ended up here:" community-suggestions section, ranked by click count. Click-to-accept increments the rank.

### Cold-start without YAML pre-seed

Founder's refinement: no pre-seeding needed. The chip's clarifier flow IS the cold-start mechanism. Pioneer student uses Gemma's tool-calling to find their real target; click teaches the system; subsequent students benefit. Demo video actually gets stronger — two beats (pioneer + beneficiary) in the same recording.

### The 5-mode feasibility classification

The self-defending property of the cache. Gemma must classify every candidate career it surfaces in the chip debug trace:

| Mode | Meaning | Cacheable |
|------|---------|-----------|
| `direct_hit` | School offers the canonical CIP for this career | Yes |
| `crosswalk_quirk` | School reports under broader CIP but graduates do land here (IU-Marketing case) | **Yes — the valuable case** |
| `adjacent_reachable` | Career is a track/concentration inside a broader degree | Yes, with caveat |
| `school_gap` | Reachable only at peer schools, not this one | No (school-switch CTA) |
| `genuinely_impossible` | No plausible path in the CIP→SOC crosswalk | No (honest "not reachable") |

Only the three "reachable" modes increment community-suggestion counts. This is what prevents "penis → Marketing Manager" from polluting the cache: Gemma's tool-call verification classifies it as `genuinely_impossible` and it never surfaces. The attack surface collapses from "free-text injection" to "social-engineer the ordering of legitimate suggestions," which is manageable with post-hackathon guardrails (unique-session threshold, report-abuse link, admin blacklist).

### Decision

- **YAML retires from the resolution path entirely.** No short-circuit, no seeding, no middle layer.
- **`backend/app/services/major_lookup.py` stays during transition** as break-glass for Gemma outage (per `feature-gemma-availability.md`), then deletes post-demo.
- **Community-suggestions surface added to Set Your Course** as a new UI section under the career preview.
- **Correction log schema extended** to capture `clicked_soc`, `clicked_career_title`, `feasibility_mode`, and `input_normalized` — which is now the cache key.
- **V2 anchored regression** remains relevant for availability strategy (how much do we need YAML break-glass coverage) but NOT for the main design decision — YAML goes either way.

### Kaggle narrative upgrade

The inverse-proof framing ("without Gemma, 300 entries, 3% coverage") is replaced with a stronger claim: **"No static lookup exists at all. Gemma reasons and tool-calls live; the product learns from use."** Two demo beats in the video now: the pioneer's chip flow (Gemma does the work), and the beneficiary's screen (crowd signal surfaces). That's a new Kaggle-video pattern — self-healing career planning — that judges won't have seen in other submissions.

### Impact on specs (propagated this session)

- `feature-set-your-course.md` — retires YAML from the flow, adds the 5-mode feasibility classification, adds the Community Suggestions surface (new §4 sections), extends correction log schema, flags `major_lookup.py` for post-V2 deletion.
- `submission-kaggle-narrative.md` — adds the reinforcement-loop thesis alongside the reasoning-bridge thesis. Pioneer + beneficiary added to demo beats.
- `feature-gemma-availability.md` — fallback strategy updated (community-suggestions is now option (b); YAML break-glass reframed as last-resort, post-transition).
- `feature-chat-guardrails.md` — new surface (community suggestions) added to the guardrails obligation; poisoning / offensive-input vectors called out; report-abuse + admin blocklist + unique-session threshold named.
- `feature-gemma-tool-calling-migration.md` — adds a P0 Tier 0 entry: `set_your_course.py::handle_chip_dispatch` is tool-call-first from day one. Non-negotiable for the flagship.

---

## Topic 12: Regression Results — YAML Earns Its Keep

### The data (2026-04-19, end of session)

The YAML regression spec completed against OpenRouter (`google/gemma-4-26b-a4b-it`), ~16 minutes, under $0.05:

- **219 inputs tested**
- **20 matches (9.1%)** — Gemma agreed with the hand-curated YAML
- **182 mismatches** — Gemma resolved to a different CIP
- **17 errors** — 2 malformed Gemma JSON + 15 OpenRouter rate-limit clusters at the tail

Per-family breakdown:

| CIP family | Inputs | Matches | Notes |
|-----------|--------|---------|-------|
| 13 (Education) | 147 | 0 | Gemma scattered across 6 different families without school context |
| 52 (Business) | 72 | 20 (28%) | Only Marketing, MIS, Business Analytics, Entrepreneurship, Supply Chain hit ≥50% |

### Methodology caveat (load-bearing)

The regression script ran with `unitid=0` + `programs=[]` — **no school context.** Production passes the actual school's CIP list (the `programs` kwarg) to `_call_gemma_intent`, which interpolates it into the prompt and materially disambiguates resolution. The 9.1% number is the *worst-case, unanchored* signal. A school-anchored re-run would likely raise the match rate substantially — the report flags this explicitly as a separate follow-up spec.

### Verdict

**Do not disable the YAML in production.** The `INTENT_YAML_ENABLED` gate ships defaulted to `true`, so the no-op outcome is also the correct outcome — the data confirmed the YAML earns its keep for the initial resolution step.

### What this changes for Set Your Course

The flagship spec was designed on the premise that "every student input is resolved by live Gemma with YAML disabled, so the student sees Gemma reasoning live on every keystroke." That premise doesn't hold. The revised premise:

- **YAML stays enabled** in the Set Your Course flow — matches today's production behavior.
- **Common inputs short-circuit to YAML** instantly — no visible Gemma on the initial resolution for those.
- **Novel / missing-from-YAML inputs fall through to Gemma** with streaming — Gemma visibility is preserved for exactly the cases YAML can't handle.
- **Chip correction ("Not what I expected")** fires regardless of whether the initial resolve was YAML or Gemma — this is where the flagship Gemma showcase actually lives.
- **All downstream Gemma surfaces** (boss narration, guidance, skill recs, career tiering, tool-calling) are unchanged — untouched by this finding.

### What this changes for the Kaggle narrative

The "inverse proof" (300 entries = 3% coverage) was written with the assumption that YAML is vestigial. The data says otherwise — YAML is doing real disambiguation work at the entry point that Gemma without school context cannot reproduce. Revised framing:

- YAML handles a bounded routing step at the front door (~300 common inputs).
- Gemma handles every reasoning-hard surface downstream: fallback resolution on YAML miss, chip correction, career tiering, boss narration, guidance, skill recs, tool-calling debug traces.
- The "reasoning bridge across fragmented public data" thesis is unchanged — the bridge just has one small hand-curated deck at the approach, not a dirt trail. That's an honest description, not a weakened one.

### Follow-up: school-anchored regression re-run

Before any future disable-YAML decision, a re-run with realistic production context (unitid + programs) is needed. That gets its own placeholder spec (`feature-yaml-regression-school-anchored.md`).

### Impact on other specs

- `feature-set-your-course.md` — updated (§1 Overview, §1 Success Criteria, §4 Architecture flow diagram) to reflect YAML stays on.
- `feature-gemma-availability.md` — YAML repositioned from "break-glass fallback" to "primary resolver for the common path"; the outage risk surface shrinks because YAML hits don't care about Gemma's health.
- `submission-kaggle-narrative.md` — inverse proof nuanced to honest description.
- New placeholder `feature-yaml-regression-school-anchored.md` — captures the follow-up.

---

## Specs Impacted (Final State)

| Spec | Status at end of session | Summary |
|------|-------------------------|---------|
| `docs/specs/feature-gemma-alias-curation.md` | Still DRAFT, has CHANGES REQUESTED in §5 | Will be marked SUPERSEDED when `feature-set-your-course.md` completes |
| `docs/specs/feature-learned-alias-cache.md` | **DEFERRED (post-hackathon)** | Parked with PM reasoning; correction-log idea preserved inside `feature-set-your-course.md` as write-only log |
| `docs/specs/completed/bugfix-disable-intent-yaml-regression.md` | **REOPENED — V1 COMPLETE (unanchored, 9.1%), V2 ANCHORED RERUN RUNNING** | V1 methodology was flawed (`unitid=0`, `programs=[]` — stripped school context production always provides). V2 uses 3-schools-per-input anchored sampling against live Gemma. Results drive go/no-go on disabling YAML in production — but reinforcement-loop design (Topic 13) retires the YAML regardless, so V2 informs availability strategy rather than the core architecture call. |
| `docs/specs/feature-set-your-course.md` | **DRAFT — flagship** | Unified School + Major + Effort/Loans + live career preview + three-chip correction rail (one Gemma-heavy). §12 hard-blocks external ship until guardrails spec ships. |
| `docs/specs/feature-chat-guardrails.md` | **TODO placeholder, scope narrowed** | Days of work, not weeks, thanks to chip-based design |
| `docs/specs/submission-kaggle-narrative.md` | **TODO placeholder** | Pins the "reasoning bridge" thesis + inverse proof + demo beats + writeup spine |
| `docs/specs/feature-gemma-availability.md` | **TODO placeholder** | Outage mitigation menu (YAML break-glass, last-good cache, local Ollama hot fallback, graceful degradation, demo pre-warm) |
| `docs/specs/feature-gemma-tool-calling-migration.md` | **TODO placeholder** | Priority-ordered migration of existing pre-inject Gemma call sites to MCP tool-calling. Non-blocking for hackathon; new flagships must be tool-call-first. |
| `docs/specs/feature-school-discovery.md` | **BACKLOG (SKELETON) + v0.5 STUB CARVED** | "Top schools for a program" discovery screen as the destination for Set Your Course's `school_gap` feasibility CTA. National ranking default; opt-in zip for distance sort; never stores zip. Exposes new MCP tool `get_top_schools_for_cip`. **v0.5 stub ships for hackathon** — static top-10 list, no sort/zip/MCP tool — to give the `school_gap` CTA a real destination. Full screen is post-hackathon. |
| `docs/specs/feature-receipts.md` | **DRAFT (SKELETON) + v0.5 STUB CARVED** | Data provenance as a first-class product feature. Gemma cites sources inline using the acronym spell-out rule (e.g. "Bureau of Labor Statistics (BLS)" on first mention). Career cards carry subtle footer attribution. Canonical source registry in `backend/app/services/receipts.py`. Hackathon v0.5: inline Gemma citations + card footers + acronym rule in prompts. Post-hackathon: "Our Sources" page, per-stat hover tooltips, parent explainer. |

### Supporting artifacts

| File | Status |
|------|--------|
| `reports/proposal-learned-alias-cache-2026-04-19.md` | DEFERRED (linked to parked spec) |

---

## Code Shipped This Session

| File | Change |
|------|--------|
| `backend/app/services/gemma_client.py` | Added `seed: int \| None` param to `generate`, `generate_chat`, `generate_async`, `generate_chat_async`. Forwarded to `chat.completions.create`. Logged in `logs/gemma.jsonl`. |
| `backend/app/services/intent.py` | `_call_gemma_intent` now uses `temperature=0.0` (was 0.1). Added `_derive_intent_seed()` helper — SHA-256 of normalized input → 32-bit uint. Seed passed to `gemma_client.generate`. |
| `backend/tests/services/test_intent.py` | Loosened strict mock to `**kwargs`. Added `TestDeterministicIntentCall` (4 tests). |

**Validation:**
- 37/37 intent + gemma_client tests pass.
- 137/137 gemma-mocking tests across boss_fights, guidance, builds, school_lookup, career_pick pass.
- Ruff clean. Mypy unchanged from main (dropped 1 pre-existing error via `completion_kwargs` refactor).

**Not touched:** `backend/cli.py:787` still uses `temperature=0.1` in its duplicate `_call_gemma_intent`. CLI is not in the Kaggle demo path. Flagged for later cleanup.

---

## Key Frames That Emerged

### Frame 1: Gemma moved from narrator to reasoning bridge

Decorative prose over pre-computed data → load-bearing reasoning on the critical path. Pull it out and the product degrades from a career planner to a 300-entry lookup table.

### Frame 2: The inverse proof as the Kaggle pitch

**Without Gemma, FutureProof covers ~3% of real student vocabulary and has no mechanism for fragmented-data reconciliation.** That's the one-liner for the writeup and the video.

### Frame 3: Demo psychology favors visible Gemma

- Spinner = bug. Streaming text = reasoning.
- Cache hit = absence of a thing. Chip-triggered debug trace = presence of a thing.
- Every second of a 3-minute video should be visible Gemma work.

### Frame 4: Kid voice, engineer routing

- Chip labels match how 17-year-olds think ("not what I expected"), not how engineers think ("crosswalk mismatch at the reporting level").
- Gemma does the diagnostic taxonomy internally. The student never sees the seven buckets.

### Frame 5: Correction log is free option value

- Write-only append JSONL (`data/reference/student_corrections.jsonl`).
- The app never reads it. 2-line code cost.
- Pays out as a demo artifact ("real beta-week feedback") AND as v2 input if/when persistence becomes worth building.

### Frame 6: Availability is the new architectural risk

- Gemma on critical path = Gemma outage = product outage.
- No static substitute for reasoning. Deterministic fallbacks that worked for narration don't work here.
- Must be addressed before the Kaggle demo recording.

---

## Sequence for the Remaining 29 Days (as of 2026-04-19)

| Week | Ship | Gemma surface |
|------|------|---------------|
| **This week** (Apr 19–25) | YAML regression spec (in flight) + Set Your Course architecture review | Tightens deterministic intent resolver |
| **Weeks 2–3** (Apr 26–May 9) | `feature-set-your-course.md` flagship build | Primary flagship — chip-triggered Gemma reasoning, tool-calling, streaming |
| **Week 4** (May 10–16) | Upgrade boss narration (second Gemma-maximal build) | Sizzle-reel Gemma moment |
| **Final days** (May 17–18) | Demo video + judging-safe polish + availability mitigation (from `feature-gemma-availability.md`) | — |

---

## Open Items When Session Resumed

1. **YAML regression spec** — executing in background when the session closed. Next action: read its completion report + decide whether to flip `INTENT_YAML_ENABLED=false` as default in the Set Your Course build.
2. **`feature-set-your-course.md` architecture review** — needs `@fp-architect` + `@fp-data-reviewer` + `@genai-architect` per its Claude Code Prompt. Not yet kicked off.
3. **Guardrails spec promotion** — stay TODO until the flagship is nearly shippable, then promote (estimated 2–3 days of work).
4. **`feature-gemma-availability.md` strategy selection** — the real spec picks one or more of the five mitigations. Should happen before the demo is recorded.
5. **`backend/cli.py:787`** — still has `temperature=0.1`. Cleanup follow-up, out of demo path.
6. **Career augmentation on substitution** — the original "marketing jobs at IU" UX problem is partially solved by the Set Your Course chip flow; verify during implementation whether it still needs its own spec.
7. **Boss narration spec** — PM's #2 priority after Set Your Course; spec not yet drafted. **Must be tool-call-first from day one** per the tool-calling migration placeholder.
8. **Tool-calling migration post-hackathon** — `feature-gemma-tool-calling-migration.md` is TODO; convert into real spec after May 18. Priority order: boss narration → guidance → career tiering → skill recs → skill pool. Leave intent + career_pick_qna + school_lookup on pre-inject.

---

## Reference — Conversation Arc

1. Load `feature-gemma-alias-curation.md`, run architecture review → CHANGES REQUESTED.
2. Plain-language objections explained.
3. Founder reframes: "why are we screwing around with YAML?"
4. Reinforcement loop idea → learned-alias-cache proposal + spec drafted.
5. Specs opened in Typora.
6. Founder asks for YAML toggle + PM review.
7. PM review: cache is wrong for hackathon.
8. Founder picks hybrid → ship determinism, park cache, pivot.
9. Ship `temperature=0` + seed. Tests green.
10. Flow walkthrough → "YAML out?" → "screens unified" → conversational correction → PM back in → chips.
11. Three specs drafted (guardrails TODO, YAML regression, Set Your Course flagship).
12. YAML regression spec kicked off.
13. "Is Gemma now core?" → yes, reasoning bridge. Inverse proof = Kaggle pitch.
14. Two more placeholders (Kaggle narrative, Gemma availability).
15. Chips vs chat → chips win, seven buckets.
16. Kid-voice correction → three chips, one Gemma-heavy, internal bucket routing.
17. Specs revised.
18. Session saved here.
19. "Weird that we built the pipeline + MCP and just pass text?" → pre-inject vs tool-calling inconsistency surfaced.
20. Tool-calling migration placeholder created with priority ordering; boss narration flagged as must-be-tool-call-first.
21. Convos doc updated with Topic 11.
22. V1 YAML regression ran (9.1% unanchored, bad methodology caught by founder).
23. `bugfix-disable-intent-yaml-regression.md` reopened with V2 anchored methodology + 3-schools-per-input sampling.
24. Reinforcement loop proposed as YAML replacement — pioneer flow + community suggestions + 5-mode feasibility.
25. YAML retires from resolution path entirely; `major_lookup.py` flagged for post-V2 deletion.
26. Kaggle narrative upgraded to "no static lookup" framing.
27. Specs propagated: Set Your Course, Kaggle narrative, availability, guardrails, tool-calling migration.
28. Meme-redirect easter egg captured in guardrails §3 (with probe-flip escalation in §3.1 — infosec career suggestion when adversarial probing is detected).
29. School Discovery skeleton spec drafted — escape hatch for `school_gap` feasibility; national ranking default, opt-in zip sort, no tracking.
30. Design visionary produced full design proposal + Brightpath HTML mockup (15 scenarios); PM ran critique in parallel.
31. Founder reviewed mockup and made six design calls + one philosophical correction: "the major is never wrong" — ChipId `wrong_major`→`change_major`, bucket `major_mismatch`→`intent_divergence`.
32. School Discovery v0.5 stub carved for hackathon; full spec stays BACKLOG.
33. 13 design + copy + technical decisions folded into set-your-course spec in one pass.
34. Founder caught internal-taxonomy leakage in the mockup (CIP / SOC / crosswalk / numeric codes shown to students). Voice rule added as §2 Decision #12; mockup + visionary proposal scrubbed; `display_reasoning` vs `reasoning` field split in the chip response structured tail.
35. Founder caught that the replacement copy replaced jargon with passive-voice mystery ("filed with whom?"). Response: promote receipts to a first-class feature. New `feature-receipts.md` spec (v0.5 hackathon + backlog). Set Your Course §2 gains Decisions #13 (receipts) + #14 (acronym spell-out rule per founder direction: "Bureau of Labor Statistics (BLS)"). Chip-routing prompt extended with citation rule. Mockup + visionary proposal rewritten to cite IPEDS and BLS by name.
36. Final pass: cross-references wired across every spec, mockup referenced from every student-facing UX spec, SUPERSEDED banners applied to `feature-gemma-alias-curation.md` and reinforced on `feature-learned-alias-cache.md`, re-entry index added at the top of this convo log.
