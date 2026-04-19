# Feature: Set Your Course — Unified School / Major / Career Screen with Conversational Correction

## Claude Code Prompt

```
Read the spec at docs/specs/feature-set-your-course.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review §1–§4 for: new resolution flow (single
     screen, live preview, streaming Gemma chat), state management
     (buildInputStore extensions), new/modified API endpoints, and the
     **additive routing model** (new `/set-your-course` route alongside
     the unchanged `/school` flow; feature-flagged Menu entry; old
     screens / `major_lookup.py` untouched pending a follow-up
     deprecation spec).
   - Invoke @fp-data-reviewer to review: live career preview semantics, the
     "correction log" append-only file shape, the accuracy floor when
     Gemma routes ambiguous input (e.g. "Marketing" at IU).
   - Invoke @genai-architect (ad-hoc) to review: the chat Gemma prompt,
     streaming response shape, how conversation context is threaded
     across turns, how corrections modify the resolved CIP.
   - All three write findings to §5.
   - If APPROVED: proceed to step 2.
   - If CHANGES REQUESTED (Significant): STOP, alert human.
   - If REJECTED (Blocker): STOP, alert human.

2. DESIGN VISION
   - Invoke @fp-design-visionary to propose the unified screen layout.
     Three deliverables: (1) wireframe of the screen in both empty and
     filled states; (2) streaming response visual treatment (how does
     "Gemma is thinking" feel?); (3) conversation-thread UI.
   - Writes findings to §3.

3. DATA REVIEW — covered in step 1 (@fp-data-reviewer).

4. IMPLEMENTATION
   - Implement §4 exactly. Touch only files in the File Changes table.
   - BEFORE coding: read §4 Testing Impact Analysis. Note which tests
     are Confirmed Safe — if any of those fail, STOP and escalate.
   - Log all work to §6. Run backend + frontend suites to verify the
     build is green when you finish.
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts).

5. TESTING
   - Invoke @test-writer to add the cases in §4 "New Tests Required".
     P0 first. Mocked Gemma only — no live calls in CI.

6. DESIGN AUDIT
   - Invoke @fp-design-auditor to verify Brightpath token compliance
     against DESIGN.md.

7. CODE REVIEW
   - Invoke @faang-staff-engineer for security/performance/error-handling
     review. Writes verdict to §8.

8. VERIFICATION
   - Invoke @fp-builder for the standard build gate.

9. COMPLETION
   - Update Status to COMPLETE.
   - Move spec to docs/specs/completed/.
   - Write completion report to reports/feature-set-your-course-YYYY-MM-DD.md.

10. HARD BLOCK ON GUARDRAILS
   - THIS SPEC SHIPS TO THE DEV TEAM. It does NOT ship to judges, beta
     users, or pilot schools until docs/specs/feature-chat-guardrails.md
     is a real spec and has been implemented + reviewed. Any PR that
     exposes the chat surface to an external audience is blocked until
     that spec completes.
```

---

## Status: DRAFT

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-19 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-04-19 |
| Blocked By | `docs/specs/bugfix-disable-intent-yaml-regression.md` (need regression data before committing to Gemma-only resolution in prod) |
| External-Audience Blocker | `docs/specs/feature-chat-guardrails.md` (must be real spec + shipped before the chat surface is exposed outside the dev team) |
| Related Specs | `docs/specs/completed/feature-gemma-tiered-matching.md`, `docs/specs/completed/bugfix-broad-cip-substitution-and-intent.md`, `docs/specs/feature-chat-guardrails.md` (TODO), `docs/specs/feature-learned-alias-cache.md` (DEFERRED — superseded by this spec's conversational correction model) |
| Proposal | `reports/proposal-learned-alias-cache-2026-04-19.md` (historical — the idea evolved) |

---

## §1 Feature Description

### Overview

Add **one unified screen** that shows school + major + effort/loans + a *live* career preview in a single interaction. The new screen ships at its own route alongside the existing `SchoolMajorScreen` + `EffortLoansPanel` + pre-build `CareerPickScreen` flow — not replacing them. Beta testers (founder's wife, daughter's friends) and judges reach the new flow through a new entry point; the existing flow stays fully wired up and reachable. Deprecation of the old screens is a **separate spec** that lands after this one ships, beta feedback is collected, and the new flow is proven on real users. When the career preview feels wrong to the student, three **kid-voiced chips** give them a way to push back: "Not what I expected" (the Gemma-heavy one), "Show me less common paths" (reveal stretch tiers — no Gemma call), and "Change my major" (reset the major input). When the student taps the Gemma-heavy chip, a small clarifier prompt appears — *"What were you hoping to see? Name a job, a field, whatever's missing."* — and Gemma receives (input, current state, clarifier) and reasons out loud through a known debug loop: is this a crosswalk mismatch? a semantic drift? a school-level gap? Gemma's reasoning streams to the screen, the resolution updates if the debug changes the CIP, and the career preview refreshes.

This screen is the product's thesis rendered in a single interaction: "I was wrong about what I wanted to study — and watching Gemma reason changed my mind." It is also FutureProof's flagship Gemma-visible moment for the Kaggle demo.

**Why chips, not open chat.** A 17-year-old is not going to type "I think this school reports my program under a broader CIP than I expected." They're going to tap a chip that honestly says *"not what I expected."* The technical taxonomy of seven failure modes (crosswalk mismatch, semantic drift, data suppression, etc.) is Gemma's job to classify internally — the student never sees the buckets, only the reasoning. Chips also keep the guardrails surface narrow: the only free-text is a scoped clarifier anchored to career lookup, not open chat.

### Problem Statement

Today's flow hides the product's core insight:

- `SchoolMajorScreen` asks for school + major + effort/loans. Student hits Go.
- `CareerPickScreen` shows tiered careers. Student sees "Business/Commerce" careers after typing "Marketing" at IU. **No way to push back.** They pick whatever's shown or bail.
- `RevealScreen` shows the full build.

Two real problems:

1. **Stepped nav hides the feedback loop.** The student can't iterate on major ↔ careers in one place. By the time they see the careers, they've committed to the major. The "wait, I should change my major" insight — which is FutureProof's most valuable moment — requires a round trip through three screens to surface.
2. **Zero Gemma visibility during resolution.** Students see a picker; they don't see Gemma working. In a Gemma-sponsored hackathon, every interaction is an opportunity to show the model reasoning on-screen. Today's resolution is invisible.

Constraints that shape the design:

- **The YAML short-circuit is retired from this flow entirely.** `major_lookup.lookup_major` is not called. Every student input is resolved by live Gemma at temperature=0 + input-derived seed. The YAML file itself stays in the repo during transition (break-glass per `feature-gemma-availability.md`) but is not consulted on the Set Your Course resolution path. Post-hackathon, `backend/app/services/major_lookup.py` is deleted outright.
- Gemma is slow (500ms–2s per call). The screen must feel alive during those seconds, not frozen. Streaming partial responses is part of the design for both the initial resolution and the chip-triggered debug trace.
- The correction surface is a fixed set of three chips, not open chat. The only free-text is a scoped clarifier ("What were you hoping to see?") that appears when the student taps "Not what I expected." Guardrails are tracked separately (`docs/specs/feature-chat-guardrails.md`) and BLOCK external-audience shipment, not dev-team build.
- **Corrections ARE read now.** `data/reference/student_corrections.jsonl` is the data layer behind the community-suggestions surface (§4 new section). The app reads this file on startup, builds an in-memory aggregate keyed by `(unitid, input_normalized)`, and surfaces ranked crowd signals under the career preview. Click-to-accept increments the suggestion's count.
- No occupation-first mode in this spec. Forward mode only (school + major → careers). Occupation-first is v2.
- No multi-turn chat. Each chip tap is a single, stateless Gemma call. No conversation history.
- **No YAML pre-seed.** Cold start is handled by Gemma's own tool-calling reasoning in the chip debug trace. The first student at a new (school, input) combo pays the full Gemma cost; every student after benefits from the crowd signal. The YAML is not a seed, a fallback, or a cache — it's gone from the resolution path.

### Success Criteria

- [ ] New React screen component `frontend/src/screens/SetYourCourseScreen.tsx` ships at a **new route** (`/set-your-course`) alongside the existing `/school` flow. The existing `SchoolMajorScreen`, `EffortLoansPanel`, and pre-build `CareerPickScreen` components are **NOT modified, deprecated, or marked unused** by this spec. A follow-up deprecation spec — written after beta testing and explicit founder go-ahead — retires them.
- [ ] A parallel entry point routes beta testers and judges into the new flow. Scope for the entry point: (a) a new tile/button on the Menu screen labeled "Set Your Course (beta)" or equivalent per copywriter, feature-flagged behind a Vite env var (`VITE_SET_YOUR_COURSE_ENABLED=true` in the demo build, default `false` in production until the deprecation spec lifts the flag); (b) the existing Menu entry to the old `/school` flow stays unchanged. Both flows are independently navigable during the coexistence period.
- [ ] No router entries are removed or rewritten. `frontend/src/App.tsx` gets **one new `<Route>`** for the new screen; the existing `/school` route is untouched.
- [ ] Both flows can commit a build to `RevealScreen` independently. `RevealScreen` does not distinguish which flow produced the committed `(unitid, cip4, effort, loans, confirmed_focus)` payload — it reads `buildInputStore` and renders. The store stays compatible with both writers.
- [ ] Screen renders: school picker, major text input, effort slider, loans slider, live career preview (tier cards), a three-chip correction rail.
- [ ] On major input change (debounced 300ms), backend resolves CIP via Gemma (`INTENT_YAML_ENABLED=false` in this flow regardless of env). Preview career tiles update in-place.
- [ ] Gemma resolution response **streams** to the screen — the student sees text tokens arrive, not a spinner-then-result. Shape: SSE from `POST /intent/stream` or chunked JSON via fetch streaming.
- [ ] Correction chips: `[Not what I expected]`, `[Show me less common paths]`, `[Change my major]`. Kid-voiced. Always visible under the career preview once a resolution renders. **The major is never "wrong" — the student said what they want.** The third chip acknowledges a student revising their own plan, not a failed guess.
- [ ] **"Not what I expected"** opens a clarifier prompt ("What were you hoping to see? Name a job, a field, whatever's missing.") with a **280-character maximum** (enforced both client-side and server-side Pydantic validator). On submit fires `POST /intent/chip` with `{chip_id: "not_expected", clarifier: <text>, current_state: ...}`. Gemma's debug-loop response streams; when it updates the CIP, the resolution + career preview refresh in place with a `layoutId`-driven animation (not a hard cut) — see the visionary proposal for the motion spec.
- [ ] **"Show me less common paths"** is a pure frontend toggle — reveals the less-common and stretch tiers already computed. **Zero Gemma calls.**
- [ ] **"Change my major"** clears the major input and refocuses it. **Zero Gemma calls.** No "this was wrong" framing — the student is revising their plan, which is honored, not corrected.
- [ ] Each chip tap is a single stateless request. No multi-turn history is threaded to the backend. The clarifier free-text is the only scoped input the student provides.
- [ ] **Chip-stream abort policy:** if a chip debug trace is streaming when the student edits the major input, the in-flight stream is cancelled via `AbortController`; the major re-resolves from scratch; the chip state resets to at-rest. Clean slate.
- [ ] **Consent-of-loop disclosure:** a one-liner renders under the chip rail. Placeholder copy (pending `@fp-copywriter` polish): *"Your choices help other students find their path. We don't track any identifying info — just that someone found this mapping useful."* Voice guide owns final wording.
- [ ] **Start Over** triggers a one-tap confirm dialog ("This clears your progress. Sure?" or equivalent per copywriter) before resetting state. Prevents mis-click data loss on a multi-step screen.
- [ ] **Zero internal-taxonomy leakage.** Students never see "CIP," "SOC," "crosswalk," or numeric taxonomy codes anywhere in the UI or in Gemma's `display_reasoning`. Enforced via (a) explicit prompt rule in the chip-routing system prompt, (b) separate `reasoning` (engineer-facing) + `display_reasoning` (student-facing) fields in the `---CAREERS---` structured tail, (c) frontend pill labels mapped per §4 Feasibility Classification, (d) a pre-merge copy audit linted by a simple regex check (`CIP|SOC|crosswalk|\d{2}\.\d{2}`) against all JSX strings in `frontend/src/screens/SetYourCourseScreen.tsx` and its subcomponents.
- [ ] "Yes, continue" button commits: (a) appends a correction log record if Gemma's current resolution differs from the initial one, (b) navigates to `RevealScreen` with the committed CIP + effort/loans.
- [ ] "Start over" button resets state to empty school / empty major without leaving the screen.
- [ ] Correction log schema defined in §4. File is `data/reference/student_corrections.jsonl`, append-only, committed to git.
- [ ] **Community Suggestions surface.** Under the career preview, when crowd signals exist for `(unitid, input_normalized)`, the screen renders a "Other students searching [input] at [school] ended up here:" section showing up to 3 ranked `(career_title, count)` cards. Clicking a card swaps the current resolution to the clicked career's canonical CIP and appends a new correction record (increments the count).
- [ ] Community Suggestions service: `backend/app/services/community_suggestions.py` with one public function `get_suggestions(unitid: int, input_normalized: str, top_k: int = 3) -> list[Suggestion]`. Reads the in-memory aggregate built from `student_corrections.jsonl` at startup; refreshes on each `record_correction()` write.
- [ ] Community Suggestions aggregation: group correction records by `(unitid, input_normalized, clicked_soc)`, filter to cacheable feasibility modes only (`direct_hit`, `crosswalk_quirk`, `adjacent_reachable` — see §4 Feasibility Classification), count, order desc by count, return top_k.
- [ ] Hackathon threshold: minimum count of 1 before a suggestion surfaces. Post-hackathon: raise to 3 via env var `COMMUNITY_MIN_COUNT` (default 1 during hackathon per founder decision 2026-04-19).
- [ ] Gemma's chip-routing prompt emits **5-mode feasibility classifications** for each career it surfaces in the debug trace (§4 Feasibility Classification). Only the three "reachable" modes cause the log record to count toward community suggestions; the two "not-reachable" modes log for audit but do not surface.
- [ ] The three current screens (`SchoolMajorScreen`, `EffortLoansPanel`, pre-build `CareerPickScreen`) are **left alone.** No deletion, no "mark unused," no router removal. They remain fully functional for users on the existing `/school` route. Their deprecation is tracked as a follow-up spec that requires beta feedback + founder sign-off before landing.
- [ ] Full test suite passes: backend + root pytest, frontend vitest, TypeScript. Ruff + mypy clean. Vite build succeeds.
- [ ] Design audit against Brightpath tokens passes (`DESIGN.md`).
- [ ] Ship-gate: this feature is **blocked from external-audience release** until `feature-chat-guardrails.md` is a real spec and implemented. The PR merge comment states this explicitly.
- [ ] Every Gemma call logs to `logs/gemma.jsonl` (global invariant) with `call_site: "set_your_course_resolve"` or `"set_your_course_chip"` + chip_id.
- [ ] No cache, no persistence of corrections as input to future resolutions. The correction log is write-only from this spec's perspective (v2 may read it).
- [ ] **Student-correctable sub-focus.** The pipeline's `program_career_paths` table is 4-digit-CIP-keyed (verified against the data contract at `governance/data-contracts/consumable-program-career-paths.yaml`). Initial Gemma resolution narrates at the 4-digit program level only — never names a specific sub-specialty it inferred on its own. When the student's clarifier names a sub-specialty (e.g. "deaf education," "UX design," "forensic accounting"), the chip-routing prompt is required to verify it is a legitimate sub-area of the resolved 4-digit CIP via a tool call (crosswalk lookup or `get_career_paths`) and emit a `confirmed_focus` string in the structured tail. Once set, `confirmed_focus` persists on the resolution for the remainder of the session and every downstream Gemma prose surface (boss narration, Gemma's Take, skill recs, skill pool, career-tiering prompts that render prose) interpolates it. Career tiles are unchanged — the 4-digit grain invariant holds — but the voice sharpens to the student's actual interest.
- [ ] If the student's clarifier names something that is NOT a legitimate sub-area of the resolved CIP (e.g. clarifier names a career on a different 4-digit family), the chip-routing prompt does NOT set `confirmed_focus` — it either routes to `semantic_drift` (change the 4-digit resolution) or returns an honest floor-level response. No fabricated sub-specialties.
- [ ] `confirmed_focus` is free-form student-typed vocabulary, mirrored back after verification. It is NOT a CIP sub-leaf code, NOT a crosswalk artifact, and does NOT appear in any numeric form in the UI or in prose.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | **Ship the new unified screen ALONGSIDE the three existing screens — not as a replacement.** A new route (`/set-your-course`) renders `SetYourCourseScreen`; the existing `/school` flow stays wired up. Beta testers and demo judges are routed into the new flow via a feature-flagged Menu entry. Deprecation of the three existing screens is a **separate spec**, written after beta feedback + founder go-ahead, and after the new flow has proven itself on real users. | (a) The thesis ("I was wrong about my major") still requires seeing school + major + careers together — the new screen's internal design does that. (b) Keeping the old flow live during transition de-risks the build: a broken new flow does not break the existing product; beta testers have a working fallback; the deprecation decision is informed by real usage, not a guess. (c) Competitive analogue for a single-screen internal layout: Kayak, Zillow. (d) Founder direction (2026-04-19): "can you modify the spec to make these pages separate from the existing pages? we can deprecate old when new is done." Ship-alongside is the stated shape of the work. | (a) Replace the three screens in one cut-over — rejected per founder direction and because it couples a UX experiment (does the unified screen actually surface the "I was wrong" moment?) to a destructive change (the old flow is gone). De-risk by separating. (b) Keep stepped flow, add Ask Gemma to the CareerPick screen only — rejected, the insight moment is hidden behind two transitions. (c) Progressive disclosure on the existing screen — rejected, same nav-transition friction without the unified-view payoff. |
| 2 | **Stream Gemma responses** token-by-token. | (a) 500ms–2s of silence feels broken. Streaming converts latency from a bug to a Gemma moment — the student sees thinking. (b) The OpenAI-compatible API supports streaming natively (`stream=True`); both Ollama and OpenRouter do. (c) Demo psychology: a spinning dot says "loading." Streaming says "reasoning." | (a) Spinner — rejected per above. (b) Fake-typing animation over a completed response — rejected, dishonest; a judge will test it live. |
| 3 | **Interaction is chip-based, not chat-based.** Three fixed chips ("Not what I expected", "Show me less common paths", "Wrong major") plus a scoped clarifier field behind one of them. No message history, no multi-turn state. | (a) Kids don't self-diagnose their frustration — "not what I expected" is what a 17-year-old thinks; "this school reports my program under a broader CIP" is what an engineer thinks. Chips let the student express the feeling; Gemma does the debug routing internally. (b) Narrow guardrails surface. The only free-text is one scoped clarifier ("what were you hoping to see?") anchored to career lookup. No open-chat drift. (c) Smaller build. No conversation store, no turn counting, no multi-turn tool-calling state machine. Fits in 29 days. (d) Demo-tighter. A chip tap that triggers a targeted Gemma debug trace is more reproducible on video than free-form typing. | (a) Open chat input + multi-turn — rejected, blows out guardrails scope + build scope + demo reproducibility. (b) Seven chips, one per failure mode — rejected, forces the student to self-diagnose. |
| 4 | **Log corrections append-only, never read.** | (a) The log is a demo artifact ("here's real student feedback from beta week") and v2 input — for free. (b) Reading it in this spec reintroduces the cache we already cut. (c) 2-line addition in the backend handler. | (a) Don't log — rejected, loses v2 option value. (b) Log + read with threshold — rejected, that's the DEFERRED cache spec. |
| 5 | **Chip-routing prompt is a separate system prompt** from the intent resolver prompt. Lives in `backend/app/services/set_your_course.py` (new module). | (a) Different task: the chip prompt receives a chip_id + optional clarifier + full resolution context, classifies the complaint into one of seven internal failure-mode buckets (crosswalk mismatch / semantic drift / school gap / data suppression / tier placement / major mismatch / peer variance), executes the corresponding debug trace (with tool calls as needed), and optionally emits an updated resolution. The intent prompt is a single-shot classifier with no tool-calling. Conflating them would weaken both. (b) Voice guide applies to both, but the chip prompt needs specific per-bucket reasoning templates that the intent prompt doesn't need. | (a) Reuse `_INTENT_SYSTEM_PROMPT` with appended chip context — rejected, structurally different tasks. |
| 6 | **Tool-calling: chip prompt can call `get_career_paths`, `get_occupation_data`, `get_regional_price_parity`.** | (a) The MCP server already exposes these (`src/mcp_server/futureproof_server.py`). Letting Gemma use them in the chip debug trace converts "Gemma guesses" into "Gemma looks it up" — the difference between a confident-sounding LLM and a grounded one. (b) Headline-grade demo beat: tool-calling on local Ollama. (c) Existing call sites (`career_pick_qna.py`) already do single-tool calls; extending the pattern is ergonomic. | No tool calls — rejected, limits the "why aren't there marketing jobs?" investigation surface. |
| 7 | **Debounce major input at 300ms** before firing `/intent/stream`. Re-fire on edit mid-stream (cancel-and-restart). | (a) Students type "Marketing" as `M-a-r-k-e-t-i-n-g` — we don't want 9 resolution calls. (b) 300ms is the edit-input-debounce default for responsive-but-not-spammy feel across most edtech apps. (c) Cancel-and-restart matches `AbortController` semantics in fetch. | Manual submit button — rejected, adds a tap and breaks the "live feedback" feel. |
| 8 | **Effort + loans sliders are visible but collapsed by default** on mobile; expanded by default on desktop. | (a) Mobile vertical budget is tight; the primary interaction is school + major + career preview + chips. Sliders default-collapsed keeps the correction surface prominent. (b) Desktop has room; expand by default. (c) Sliders also never drive the Gemma resolution — they're downstream build parameters — so hiding them initially doesn't block the main flow. | (a) Always expanded — rejected, mobile gets crowded. (b) Always collapsed — rejected, desktop users will miss them. |
| 9 | **No occupation-first mode** in this spec. | Out of scope by founder decision + PM recommendation. Forward mode (school + major → careers) only. Occupation-first is v2. | Include both modes — rejected, doubles surface area for a 29-day build. |
| 10 | **"Not what I expected" chip is softly encouraged before "Yes, continue"** when initial resolution has `confidence: "low"` or `confidence: "medium"` with alternatives. Soft: the commit button is enabled but shows a subtle nudge — *"Gemma wasn't sure on this one. Worth a sanity check?"* | (a) Encourages a Gemma debug moment on ambiguous input without blocking the happy path. (b) Hard-gating commit on low confidence frustrates students who know what they meant — and Gemma's confidence is a heuristic, not ground truth. (c) For `confidence: "high"` the nudge is absent; frictionless commit. (d) Naming Gemma as the uncertain party (not the student) is on-voice — cool, confident, data-honest. | (a) Hard-gate — rejected, punishes the student for Gemma's hedging. (b) Never nudge — rejected, means ambiguous resolutions get auto-committed with no Gemma showcase moment. (c) Copy "Want to double-check this first?" — rejected, doesn't name the source of the uncertainty. |
| 11 | **The major is never "wrong."** The student said what they want. The third chip is labeled "Change my major," not "Wrong major." The chip routing prompt's bucket for "typed major and clarifier career don't align" is `intent_divergence`, not `major_mismatch`. | (a) The product's posture is: the student is doing the telling, we're doing the listening. Calling the student's own major "wrong" misreads the interaction — they're not taking a quiz. (b) What might mismatch is the student's typed major and their clarified career goal (e.g. "Marketing" typed + "be a doctor" clarified). That's Gemma's observation about the data, not the student's error. (c) "Change my major" honors a legitimate act — students revise their plans routinely; the UI should treat that as honorable, not a correction. | (a) "Wrong major" label — rejected per founder direction on 2026-04-19: "the major is never wrong, that's what the student wants. Our mapping of major to job might be wrong." (b) `major_mismatch` bucket name — rejected for the same reason; renamed to `intent_divergence` throughout the chip-routing prompt. |
| 12 | **Zero internal-taxonomy leakage to students.** Students never see the strings "CIP," "SOC," "crosswalk," or any numeric taxonomy code (e.g. "52.02," "11-2021") anywhere in the UI or in Gemma's student-facing output. These terms are internal to the pipeline; they show up in code, schemas, logs, and specs only. | (a) Students are 17-year-olds picking a college path — "CIP 52.02" reads as gibberish and breaks the trust the rest of the UI tries to build. (b) The framing students need is "program" (not CIP), "career" (not SOC), and plain-English descriptions of data quirks (not "crosswalk mismatch"). (c) The feasibility classification's internal bucket names (`crosswalk_quirk`, `direct_hit`, etc.) are engineer-facing; student-facing pill labels are separate and human — see §4 Feasibility Classification student-facing pill mapping. (d) The chip-routing Gemma prompt has an explicit rule forbidding these terms in its output; the failure mode is "Gemma says 'this is a crosswalk quirk'" which must never land on the student's screen. | (a) Show CIP codes in a tooltip for "transparency" — rejected, the codes have no meaning to the audience and their presence signals "this product was built for bureaucrats, not for me." (b) Translate in the frontend only — rejected, Gemma's streamed reasoning is also student-facing, and post-hoc translation is fragile. The rule lives in the prompt AND the frontend. |
| 13 | **Receipts — data sources are NAMED, not hidden.** Every factual claim Gemma makes to the student cites its source by full name on first reference with acronym in parentheses. Example: *"Bureau of Labor Statistics (BLS)"* on first mention, *"BLS"* thereafter. Career preview cards carry a subtle footer attribution (*"Data from Bureau of Labor Statistics (BLS) · College Scorecard 2023 · Occupational Information Network (O*NET)"*). See `docs/specs/feature-receipts.md` for the full feature spec; this spec's obligation is to ship the v0.5 slice (inline Gemma citation + card footer). | (a) Replacing taxonomy jargon (per Decision #12) with passive voice like "Marketing is filed under Business" leaves the authority unnamed — founder caught this same session with "filed with whom?" The real answer (reported to IPEDS, tracked by BLS) is both specific and trust-building. (b) Citing sources is the anti-hallucination flex vs. typical LLM tools. Data-honest voice (per voice guide) requires naming the data. (c) Parents respect "according to the Bureau of Labor Statistics (BLS)" — it's the language of journalism, not of software. (d) Demo-strong: a card showing "Source: BLS OOH · College Scorecard 2023" is screenshot-worthy on its own. | (a) Hide sources entirely — rejected, black-box framing is antithetical to the product. (b) Cite only on a dedicated "Sources" page — rejected, the claim and the receipt have to sit next to each other or the receipt isn't trust-building. (c) Show sources only via hover tooltips — rejected, mobile has no hover, and streaming prose can't rely on it anyway. |
| 14 | **Acronym spell-out rule: first reference per rendered view uses full name with parenthetical acronym; subsequent references may abbreviate.** Example: first mention on a screen uses "Bureau of Labor Statistics (BLS)," the same screen's second reference may use "BLS." | (a) Standard journalism / report-writing style — students and parents have read this format their whole lives. (b) Per-view (not per-session, not per-app) is the right granularity: students may land on any screen cold and need re-anchoring; overusing the full name everywhere becomes ponderous. (c) Applies to SOURCES (BLS, IPEDS, O*NET, BEA, etc.), not to internal taxonomies (CIP, SOC — those stay forbidden per Decision #12). (d) Founder-introduced 2026-04-19: *"any acronyms must spell out the whole thing and then include the acronym in (). Bureau of Labor Statistics (BLS)."* | (a) Always-full-name everywhere — rejected, reads stiff. (b) Always-acronym — rejected, assumed jargon knowledge. (c) Spell-out once per entire app session — rejected, students bounce between surfaces; first-reference-per-view is the honest granularity. |
| 15 | **The pipeline joins careers at 4-digit CIP granularity.** Every student-facing surface — career tiles, earnings, debt, pentagon stats, boss fight scores — derives from `consumable.program_career_paths`, which is keyed on 4-digit CIP (XX.XX format) with a data-contract CHECK constraint enforcing it (`governance/data-contracts/consumable-program-career-paths.yaml`). Any 6-digit sub-leaf Gemma returns is truncated to its 4-digit prefix before joining to career data. This means: (a) if Gemma and the YAML disagree about sub-leaves within the same 4-digit family, the student sees identical tiles either way; (b) V2 anchored regression's "0% match" on 33 Education sub-leaf entries is measuring precision the downstream data joins do not use and does not correspond to a student-visible defect; (c) initial Gemma resolution must narrate at the 4-digit program level only — naming a specific sub-specialty Gemma inferred without student confirmation would leak a wrong room label into prose even though the tiles are right. | (a) The V2 report's hybrid allowlist (22 disable / 33 keep-in-YAML) — rejected, reinstates a static lookup in the middle to preserve sub-leaf fidelity the rest of the pipeline does not use. Also reinstates a coverage discipline the reinforcement-loop design retired on principle (Topic 13 of `docs/convos/2026-04-19-gemma-core-pivot.md`). (b) Re-key `program_career_paths` on 6-digit CIP — rejected, out of scope + data-contract breaking change + Scorecard is 4-digit at source. (c) Leave the narration-granularity rule implicit in Decision #12 — rejected, Decision #12 forbids code leakage but does not forbid naming a free-text sub-specialty; the sub-leaf drift failure mode needs its own explicit rule. |
| 16 | **Sub-focus is student-driven, not Gemma-driven.** Gemma does not invent sub-specialty labels on first resolution; the student names a sub-specialty through the clarifier; Gemma verifies via tool call that the named sub-specialty is legitimately inside the resolved 4-digit CIP; once verified, `confirmed_focus` is set and every downstream prose surface in the session uses it. If the clarifier names something outside the resolved family, the chip routes to `semantic_drift` (update the 4-digit resolution) or returns an honest floor-level response. If the clarifier names something that doesn't exist at all, Gemma says so plainly and leaves `confirmed_focus` unset. | (a) Gemma picks a sub-specialty on first resolution — rejected, V2 data shows Gemma cannot recover curator-specific sub-leaves from school context alone (0% match on 33 sub-leaves even with anchor), so auto-picking invites hallucinated room labels. (b) Never allow sub-focus in narration (the defensive rule from the 4-digit finding discussion) — rejected, strips legitimate specificity from the conversation for students who explicitly name their sub-interest. A deaf-ed teacher searching "deaf education" deserves Gemma to say "Deaf Education" back, not "Special Education in general." (c) Mirror the clarifier verbatim without verification — rejected, invites fabricated sub-specialties (student types a subfield that doesn't exist; Gemma echoes it; looks authoritative; isn't). Verification is the honest middle path. |

### Constraints

- `backend/app/services/intent.py::resolve_intent` — unchanged contract. The set-your-course backend uses it (or a streaming variant) for the initial resolution.
- `backend/app/services/gemma_client.py` — EXTENDED with a `generate_stream_async` function if one doesn't exist; otherwise unchanged.
- `backend/app/services/major_lookup.py` — UNCHANGED. The YAML is disabled at the `resolve_intent` layer for this flow, not removed.
- `src/mcp_server/futureproof_server.py` — the Gemma chat tool-calling path invokes the existing MCP tools; no MCP changes.
- `logs/gemma.jsonl` — same invariant, tagged with `call_site: "set_your_course"`.
- `data/reference/student_corrections.jsonl` — new append-only log. Committed to git. Schema in §4.
- Frontend state lives in `buildInputStore` (zustand) — extended with current-resolution fields (including `confirmed_focus`) that BOTH the existing `/school` flow and the new `/set-your-course` flow can read/write. Store shape stays backwards-compatible: new fields default to `null` / `undefined` so the existing flow writes partial payloads the store still accepts. NOT new stores.
- Brightpath tokens (`DESIGN.md`) — no new tokens; reuse.
- Route/URL: the new screen ships at `/set-your-course` (or equivalent — copywriter may override). The existing `/school` route and every component rendered under it are unchanged. Both routes land into `RevealScreen` via the existing commit path.
- The existing `SchoolMajorScreen`, `EffortLoansPanel`, and pre-build `CareerPickScreen` components — UNCHANGED. No import changes, no "mark unused" comments, no prop-shape changes. Their tests stay green without modification.

### Out of Scope

- **Occupation-first mode.** V2.
- **Persisting chat history across sessions.** V2.
- **Reading the correction log.** V2 (becomes the basis of an actual cache or a hint-surfacing feature).
- **Cross-school hint transfer.** Same input at different schools gets independent Gemma resolutions.
- **Multi-user admin view of corrections.** V2.
- **Rate limiting / abuse controls.** Covered in `feature-chat-guardrails.md`.
- **Prompt injection defense.** Covered in `feature-chat-guardrails.md`.
- **Voice / speech input.** V2.
- **Saving drafts (partial school/major) across visits.** V2.
- **Changing the intent `_INTENT_SYSTEM_PROMPT` body.** If the chat needs a different prompt, it gets its own prompt (§2 Decision #5).
- **Changing the boss / reveal path.** This spec ends at commit; the reveal flow is unchanged.

---

## §3 UI/UX Design

**@fp-design-visionary proposal COMPLETE** — see `docs/specs/design/set-your-course-visionary-proposal.md` for the full visual design spec (wireframes desktop + mobile, motion primitives, token usage map, component tree, interaction timings, accessibility notes). A Brightpath HTML mockup of all 15 scenarios is at `docs/specs/design/set-your-course-mockup/index.html` — open directly in a browser. Design decisions locked as of 2026-04-19 per that proposal.

Key locked decisions carried from the visionary proposal into this spec:
- Clarifier is inline-expansion on desktop, bottom-sheet on mobile (never a modal).
- Streaming is paragraph-by-paragraph with a `gemma-shimmer` keyframe (not token-by-token, not a spinner).
- Chip rail: one prominent primary chip + two ghost secondaries. Labels locked: "Not what I expected" / "Show me less common paths" / "Change my major."
- Community suggestions appear above the commit CTA, card treatment, honest-not-creepy copy ("Other students searching ... ended up here:").
- Career tiles animate on resolution change via `layoutId` — not a hard cut.
- Sticky mobile commit bar; desktop renders commit inline with the screen.
- school_gap renders as a full-width tile with a caution-stripe treatment and CTA to the v0.5 stub — see `feature-school-discovery.md` §v0.5 carve-out.

Original PENDING section retained below as the brief the visionary was working from:

### Brief (for history)

The visionary agent proposed:

1. **Wireframe** — empty state and filled state of the unified screen. Must show how school picker, major input, sliders, career preview, and the three correction chips coexist without feeling like a spreadsheet.
2. **Streaming reasoning visual** — what does "Gemma is thinking" look like while the initial resolution or chip-triggered debug trace streams? Token-by-token typing? A subtle shimmer? The goal is "reasoning visible," not "loading spinner." Applies to both the initial resolution and the chip debug-trace response.
3. **Chip rail** — the three correction chips under the career preview. Kid-voiced labels, Brightpath treatment. How do they look at rest vs pressed vs disabled?
4. **Clarifier prompt** — when "Not what I expected" is tapped, a scoped text input appears ("What were you hoping to see? Name a job, a field, whatever's missing"). How does this affordance feel — modal, inline expansion, bottom sheet on mobile?
5. **Commit action** — "Yes, continue" visual hierarchy vs "Start over." Include the soft-nudge treatment for low-confidence resolutions per §2 Decision #10.
6. **Low-confidence affordance** — when Gemma returns `confidence: "low"` with alternatives, how does the screen encourage the student to tap "Not what I expected" without hard-gating commit?

Constraints for the visionary:
- Brightpath dark-first, plush, cinematic.
- Mobile + desktop both first-class.
- No new design tokens — reuse `DESIGN.md`.
- Tone: cool, confident, data-honest, never hype. Chip labels are kid-voiced and honest — not engineer-voiced and diagnostic.

---

## §4 Technical Specification

### Architecture Overview

**Frontend:**
- New screen: `frontend/src/screens/SetYourCourseScreen.tsx`.
- New hook: `frontend/src/hooks/useSetYourCourse.ts` — orchestrates debounced major resolution, chip dispatch, streaming response handling, commit flow. **No conversation history.**
- Store extension: `frontend/src/store/buildInputStore.ts` — adds `currentResolution`, `initialResolution`, `hasCorrected`, `debugTrace` (the last chip debug response, if any) fields. **No `conversation` array.**
- API client: `frontend/src/api/intent.ts` — adds `streamIntent(input, signal)` and `dispatchChip(chipId, clarifier, currentState, signal)` functions using native fetch streaming.
- Career preview rendering: reuse `CareerTierSection` component; adapt for live-update.
- Chip components: three kid-voiced labels per §1 Success Criteria.

**Backend:**
- New router: `backend/app/routers/set_your_course.py` with `POST /intent/stream` and `POST /intent/chip`.
- New service: `backend/app/services/set_your_course.py` — owns the chip-routing system prompt, the seven internal debug-loop templates, the MCP tool-call dispatcher, streaming response generation, correction-log writer.
- Gemma client extension: `generate_stream_async` in `gemma_client.py` if not present; exposes OpenAI-compatible `stream=True` as an async generator yielding content deltas.
- Correction log writer: `backend/app/services/correction_log.py` — one public function, `record_correction(...)`, appends one JSONL line.

**Data:**
- `data/reference/student_corrections.jsonl` — new file, empty on creation.

**Routing:**
- `frontend/src/App.tsx` — **adds** one new `<Route path="/set-your-course" element={<SetYourCourseScreen />} />`. Existing routes (including `/school` → `SchoolMajorScreen`) are untouched.
- `frontend/src/screens/MenuScreen.tsx` — adds a new entry tile "Set Your Course (beta)" that links to `/set-your-course`. The entry renders only when `import.meta.env.VITE_SET_YOUR_COURSE_ENABLED === "true"`. Existing Menu entries (including the entry into the `/school` flow) are unchanged.
- Feature flag wiring: `VITE_SET_YOUR_COURSE_ENABLED` is read in `MenuScreen.tsx`; no runtime env reads anywhere else. Flag defaults to `false` in `.env.example`; the hackathon demo build + beta-tester builds set it to `true`.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/screens/SetYourCourseScreen.tsx` | Create | The unified screen component. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/hooks/useSetYourCourse.ts` | Create | Orchestration hook: debounced resolution, chip dispatch, streaming, commit. No multi-turn state. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/api/intent.ts` | Modify (or create if absent) | Add `streamIntent`, `dispatchChip` functions. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/store/buildInputStore.ts` | Modify | Add currentResolution / initialResolution / hasCorrected / debugTrace fields. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/school/CorrectionChips.tsx` | Create | The three-chip rail. Kid-voiced labels. Handles the clarifier-input open/close state for the Gemma-heavy chip. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/App.tsx` | Modify | **Add** one new `<Route>` for `/set-your-course`. Existing routes unchanged. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/screens/MenuScreen.tsx` | Modify | **Add** a feature-flagged "Set Your Course (beta)" entry. Existing Menu entries untouched. |
| `/Users/jcernauske/code/bright/futureproof-data/.env.example` | Modify | Document `VITE_SET_YOUR_COURSE_ENABLED` (default `false`). |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/screens/SchoolMajorScreen.tsx` | UNCHANGED | Stays wired up behind `/school`. Deprecation deferred to follow-up spec. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/school/EffortLoansPanel.tsx` | UNCHANGED | Stays in use under `SchoolMajorScreen`. The new screen imports a fresh instance of the same component (shared, not moved). |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/screens/CareerPickScreen.tsx` | UNCHANGED | Pre-reveal logic stays. Post-reveal Ask Gemma surface stays. No behavior changes from this spec. |
| `/Users/jcernauske/code/bright/futureproof-data/backend/app/routers/set_your_course.py` | Create | `POST /intent/stream`, `POST /intent/chip` endpoints. |
| `/Users/jcernauske/code/bright/futureproof-data/backend/app/services/set_your_course.py` | Create | Chip-routing system prompt, seven debug-loop templates, MCP tool-call dispatcher, streaming handler, correction-log writer wrapper. |
| `/Users/jcernauske/code/bright/futureproof-data/backend/app/services/correction_log.py` | Create | One public function `record_correction(...)`. Append-only JSONL writer. Calls `community_suggestions.refresh_on_write()` after each append. |
| `/Users/jcernauske/code/bright/futureproof-data/backend/app/services/community_suggestions.py` | Create | In-memory aggregate of the correction log, keyed by `(unitid, input_normalized)`. Rebuilds from JSONL on startup. Exposes `get_suggestions(...)` and `refresh_on_write(...)`. |
| `/Users/jcernauske/code/bright/futureproof-data/backend/app/services/major_lookup.py` | UNCHANGED | Stays in use by the existing `/school` flow via `backend/app/services/intent.py::resolve_intent`. The new Set Your Course flow calls a dedicated resolution path (`backend/app/services/set_your_course.py::stream_initial_resolution`) that bypasses `major_lookup` entirely. Deletion of `major_lookup.py` is tracked under the follow-up deprecation spec, gated on old-flow retirement. |
| `/Users/jcernauske/code/bright/futureproof-data/backend/app/services/gemma_client.py` | Modify | Add `generate_stream_async` if not already present. Preserves existing `generate`/`generate_async` API. |
| `/Users/jcernauske/code/bright/futureproof-data/backend/app/models/api.py` | Modify | Add Pydantic models for chat request/response. |
| `/Users/jcernauske/code/bright/futureproof-data/backend/app/main.py` | Modify | Register the new router. |
| `/Users/jcernauske/code/bright/futureproof-data/data/reference/student_corrections.jsonl` | Create | Empty file, committed. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/screens/SetYourCourseScreen.test.tsx` | Create | Vitest coverage. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/hooks/useSetYourCourse.test.ts` | Create | Hook logic coverage. |
| `/Users/jcernauske/code/bright/futureproof-data/backend/tests/routers/test_set_your_course_router.py` | Create | FastAPI test client coverage. |
| `/Users/jcernauske/code/bright/futureproof-data/backend/tests/services/test_set_your_course.py` | Create | Service-level coverage with mocked Gemma. |
| `/Users/jcernauske/code/bright/futureproof-data/backend/tests/services/test_correction_log.py` | Create | JSONL append + schema coverage. |

### Data Model Changes

**Pydantic — `backend/app/models/api.py`:**

```python
ChipId = Literal["not_expected", "show_less_common", "change_major"]

class IntentStreamRequest(BaseModel):
    major_text: str
    school_name: str
    unitid: int
    programs: list[dict[str, Any]]

class ChipRequest(BaseModel):
    chip_id: ChipId
    clarifier: str | None           # free-text from the clarifier prompt; required for "not_expected", ignored for others
    current_resolution: IntentResult
    initial_resolution: IntentResult
    school_name: str
    unitid: int
    programs: list[dict[str, Any]]

class ChipResponse(BaseModel):
    debug_trace: str                # prose shown to student (the Gemma reasoning)
    updated_resolution: IntentResult | None  # None if the chip debug did not change the CIP
    cta_link: CtaLink | None = None # populated only when the school_gap feasibility surfaces — links to feature-school-discovery.md v0.5 stub
    bucket: Literal[                # which analytical bucket Gemma classified the student's clarifier into
        "crosswalk_mismatch",
        "semantic_drift",
        "school_gap",
        "data_suppression",
        "tier_placement",
        "intent_divergence",        # renamed from major_mismatch — the major is never "wrong"; this bucket means "typed major + clarified career goal don't align in the crosswalk"
        "peer_variance",
        "no_issue_found",
    ] | None                        # None for the non-Gemma chips (show_less_common, change_major)
    confirmed_focus: str | None = None
    # Student-named sub-specialty (e.g. "Deaf Education", "UX Design") that
    # Gemma verified via tool call as a legitimate sub-area of the resolved
    # 4-digit CIP. Free-form, student-vocabulary label — NOT a CIP code, NOT
    # a crosswalk artifact. When set, the frontend persists it on the
    # resolution state and every downstream Gemma prose surface (boss
    # narration, Gemma's Take, skill recs, skill pool) interpolates it. When
    # unset, downstream surfaces narrate at the 4-digit program level only.
    # See §2 Decision #16.
```

**Extension to `IntentResult` in `backend/app/models/career.py:317`** — additive, backwards-compatible:

```python
class IntentResult(BaseModel):
    # ...existing fields unchanged...
    confirmed_focus: str | None = None
    # Set by the chip-routing prompt via ChipResponse.confirmed_focus when
    # the student's clarifier names a sub-specialty Gemma verified is inside
    # the resolved 4-digit CIP. Carried forward on the resolution so
    # downstream surfaces see it. Initial resolution never sets this — only
    # confirmed via the chip flow. See §2 Decision #16.
```

Frontend mirror in `frontend/src/types/buildInput.ts` gets the same optional string field.

**Correction log schema — `data/reference/student_corrections.jsonl`** (append-only, one JSON per line):

```python
FeasibilityMode = Literal[
    "direct_hit", "crosswalk_quirk", "adjacent_reachable",
    "school_gap", "genuinely_impossible",
]
# Only the first three contribute to community suggestions.

class CorrectionLogRecord(TypedDict):
    kind: Literal["correction"]
    timestamp: str                      # ISO8601 UTC
    school_unitid: int
    school_name: str
    input_normalized: str               # student's normalized query — cache key
    initial_major_text: str             # raw, pre-normalization
    initial_cip4: str                   # what Gemma resolved first
    final_cip4: str                     # the student's committed CIP (post any chip swap)
    clicked_soc: str | None             # SOC code of the career the student clicked from a debug trace (set for crosswalk_mismatch, semantic_drift, tier_placement buckets; null otherwise)
    clicked_career_title: str | None    # human title of the clicked career
    feasibility_mode: FeasibilityMode | None  # Gemma-assigned mode for the clicked career; drives cacheability
    chips_tapped: list[ChipId]          # every chip the student tapped this session
    clarifier: str | None               # first 280 chars of any clarifier text, audit trail only
    bucket: str | None                  # last Gemma-classified bucket, if any
    backend: Literal["ollama", "openrouter"]
    model: str
```

Aggregation rule for community suggestions:
- Group by `(school_unitid, input_normalized, clicked_soc)`.
- Filter where `feasibility_mode IN ("direct_hit", "crosswalk_quirk", "adjacent_reachable")`.
- Count rows per group; order by count desc.
- Return top_k per `(school_unitid, input_normalized)` key.

### Service Changes

**New module — `backend/app/services/set_your_course.py`** (structure):

```python
"""Set Your Course — unified-screen chip dispatch service.

Owns the chip-routing system prompt, the seven internal debug-loop
templates, the MCP tool-call dispatcher, streaming response generation,
and the commit-time correction-log write.

See docs/specs/feature-set-your-course.md.
"""

# DUPLICATE: this prompt body is the sole Gemma chip-routing prompt for
# set-your-course. If it is ever copied elsewhere, add a DUPLICATE banner
# to the other copy pointing here — mirror the discipline in
# backend/app/services/intent.py:67.
_CHIP_ROUTING_SYSTEM_PROMPT = """\
You are FutureProof's career-planning assistant, triggered when a student
tapped "Not what I expected" on their Set Your Course screen. Your job is
to classify why the student's expectation missed the data, run the right
debug trace, and either confirm the current resolution or update it.

# Student's clarifier
The student filled in a scoped prompt ("What were you hoping to see?")
with: "{clarifier}"

# Current state
- School: {school_name} (unitid {unitid})
- Initial major input: "{initial_major_text}"
- Current resolution: {current_cip4} {current_title} (confidence: {current_confidence})
- Initial resolution: {initial_cip4} {initial_title}
- Career tiles currently shown: {current_tile_titles}

# Debug-bucket taxonomy — classify the clarifier into ONE of these
1. crosswalk_mismatch — the school reports the program under a broader
   or sibling CIP than the student expects. Example: student at IU types
   "marketing" and is seeing Business/Commerce jobs because IU reports
   Marketing under 52.02, not 52.14. Action: call get_career_paths on
   the narrower CIP and surface those jobs, flag the reporting quirk.
2. semantic_drift — the student's word means something different than
   the program it maps to. Example: student says "design" meaning UX
   design; CIP resolves to graphic design. Action: re-resolve using
   the clarifier as additional intent signal.
3. school_gap — this school genuinely does not offer the program the
   student wanted. Action: say so plainly; emit a cta_link to the
   School Discovery v0.5 stub so the student can explore top schools
   offering the program nationally.
4. data_suppression — the program exists but IPEDS suppressed the
   detail for privacy (small n). Action: explain the suppression rule;
   don't pretend the data is there.
5. tier_placement — the target jobs exist for this CIP but are in a
   less-common or stretch tier the student hasn't revealed. Action:
   point them to the tier toggle.
6. intent_divergence — the student's typed major and their clarified
   career goal don't align in the CIP→SOC crosswalk. Example: student
   typed "Marketing" but clarifier says "I want to be a doctor." This
   is NOT "student picked the wrong major" — the student's major is
   what they want. This bucket describes an observation about the data,
   not a failure of the student. Action: honestly surface the gap and
   OFFER (not impose) alternative majors that lead to the clarified
   career. Frame as options the student can consider, never as
   corrections.
7. peer_variance — other schools report this program differently and
   the student is comparing. Action: query 2–3 peers and show variance.
8. no_issue_found — the clarifier doesn't match any debug bucket
   cleanly (e.g. "I just don't like these jobs"). Action: acknowledge
   plainly, do NOT force a bucket, do NOT update the resolution. Render
   a brief honest response ("These just aren't resonating — totally
   fair. You can try a different major or continue with what you have.")
   and leave the student in control. Never a dead-end spinner.

# Rules
- Ground every claim in the data. If you don't have data for a school
  or program, say so plainly. Do not invent careers, salaries, or
  schools.
- Voice: cool, confident, data-honest. No hype. No "unlock your future."
  Don't tell students what to do; show them what the data says.

- **Narrate at the 4-digit program level unless the student has confirmed
  a sub-specialty.** The career data this product serves is keyed at the
  4-digit program granularity; any sub-specialty label narrower than that
  (e.g. "Deaf Education," "UX Design," "Forensic Accounting") is legitimate
  to say ONLY IF the student named it first in their clarifier AND a tool
  call verified it is a real sub-area of the resolved program. Do not
  invent or auto-select a sub-specialty from your training data; a wrong
  room label lands as confident and wrong. If the student named a sub-
  specialty, verify it with get_career_paths / crosswalk lookup, then
  mirror it back using the student's own wording in your prose AND emit
  it in the structured tail's `confirmed_focus` field. If the student did
  not name one, keep your prose at the program level ("Special Education
  program at your school") and leave `confirmed_focus` absent. If the
  student named something that is not a sub-area of the resolved program
  (e.g. typed "Marketing," clarified "I want to be a nurse"), route to
  `semantic_drift` or `intent_divergence` as appropriate — do not claim
  the nurse path is "inside Marketing."
- **NEVER use internal taxonomy terms in your student-facing prose or
  in the display_reasoning field.** Specifically forbidden in any
  student-visible output: "CIP," "SOC," "crosswalk," or any numeric
  code like "52.02" or "11-2021." These are invisible to the student
  by design. Translate instead:
    * CIP → "program" or the plain-English program title (e.g.
      "Business program," "Marketing")
    * SOC → "career" or the plain-English job title (e.g. "Marketing
      Manager")
    * crosswalk → "the data" or rephrase around it entirely; and
      when the claim requires attribution, name the actual source
      (e.g. "In Indiana University's submission to the Integrated
      Postsecondary Education Data System (IPEDS), Marketing is filed
      within its Business program" — NOT "the crosswalk shows").
    * Numeric codes → drop them; the title alone is enough
  Your internal `reasoning` field CAN reference these terms (it's
  engineer-facing / audit trail). Your `display_reasoning` MUST NOT.

- **CITE SOURCES with the acronym-spell-out rule.** When your response
  makes a factual claim drawn from the data, name the source. First
  reference in your response uses full name + parenthetical acronym
  (e.g. "Bureau of Labor Statistics (BLS)"); subsequent references may
  use the acronym alone. Applies to sources (BLS, IPEDS, O*NET, BEA,
  College Scorecard, and others) — NOT to internal taxonomies (CIP,
  SOC) which stay forbidden per the rule above. Do not invent sources.
  If you're not sure which source supplied a claim, phrase the claim
  in a way that doesn't need a specific source attribution. See
  feature-receipts.md for the canonical source registry interpolated
  into your prompt as {sources_for_prompt_context}.
- Use your tools (get_career_paths, get_occupation_data,
  get_regional_price_parity) when the bucket's debug trace needs them.
  Don't tool-call to pad.
- If you change the resolution, emit the structured tail. If not, omit.
- Keep the prose to 2–4 sentences — the clarifier is a moment, not a
  lecture.

# Your response format
Reply with 2–4 sentences of student-facing reasoning (plain English,
no CIP/SOC/crosswalk/numeric-code terms). Use the student's own wording
for any sub-specialty they named in their clarifier, but only after you
have tool-verified it is a real sub-area of the resolved program.
If you're changing the resolution, append:
  ---UPDATED_RESOLUTION---
  {{"matched_cip": "XX.XXXX", "matched_title": "...", "confidence": "high|medium|low", "reasoning": "..."}}
Always append the classification tail (even if no resolution change):
  ---BUCKET---
  {{"bucket": "crosswalk_mismatch" | "semantic_drift" | ... | "no_issue_found"}}
If the student named a sub-specialty in their clarifier AND you verified
it via tool call as a legitimate sub-area of the resolved program, also
append:
  ---CONFIRMED_FOCUS---
  {{"confirmed_focus": "<student's own words for the sub-specialty>"}}
Omit the ---CONFIRMED_FOCUS--- tail entirely if (a) the student did not
name a sub-specialty, (b) your verification failed, or (c) the clarifier
routed to semantic_drift / intent_divergence (sub-focus is meaningless
when the 4-digit resolution itself is changing).
"""

async def stream_initial_resolution(...):
    """Stream the initial intent resolution response."""

async def handle_chip_dispatch(request: ChipRequest) -> ChipResponse:
    """One stateless chip tap. For chip_id='not_expected', runs the
    Gemma chip-routing prompt with MCP tools available. For
    'show_less_common' and 'wrong_major', no Gemma call — those are
    frontend-only mechanics and the backend endpoint exists only for
    symmetry (logging)."""

def record_commit(request: CommitRequest) -> None:
    """Write one correction log line on commit. No-op if the committed
    CIP matches the initial resolution (no correction happened)."""
```

**New module — `backend/app/services/correction_log.py`:**

```python
"""Append-only correction log.

Write-only from this spec's perspective. The app never reads this file.
Lives at data/reference/student_corrections.jsonl, committed to git.

See docs/specs/feature-set-your-course.md §2 Decision #4.
"""

_REL_LOG_PATH = Path("data/reference/student_corrections.jsonl")
_write_lock = threading.Lock()


def record_correction(record: CorrectionLogRecord) -> None:
    """Append one JSONL line. Never raises — logging must not crash the
    commit path. Single write() call under a threading.Lock; matches the
    discipline of logs/gemma.jsonl."""
```

### Feasibility Classification (the 5 Modes)

When the chip-routing prompt runs the `crosswalk_mismatch`, `semantic_drift`, or `tier_placement` debug trace and Gemma surfaces candidate careers in response to the student's clarifier, each candidate MUST be classified into one of five feasibility modes. Only the first three are cacheable — they increment community-suggestion counts. The last two are logged for audit but never surface as suggestions, which is what keeps the reinforcement loop from learning garbage.

| Mode | Meaning | Gemma must verify via tool-call | Cacheable |
|------|---------|----------------------------------|-----------|
| `direct_hit` | This school offers the canonical CIP for this career. Gemma just surfaces it plainly. | `get_school_programs(unitid)` returns the CIP that maps to this SOC | **Yes** |
| `crosswalk_quirk` | School reports under a broader CIP than canonical, but graduates ARE in this SOC. The IU-Marketing case. This is the valuable cache entry. | `get_career_paths(unitid, school_cip)` returns the SOC even though canonical mapping is different | **Yes** |
| `adjacent_reachable` | Career exists as a track/concentration inside a broader degree at this school, not as standalone. "Marketing track within Business." | `get_career_paths` shows the SOC with small-n but nonzero | **Yes, with caveat** |
| `school_gap` | Career is reachable from the canonical CIP but this school doesn't offer that CIP. Not a correction — a school-switch prompt. | Peer schools query confirms availability elsewhere | No — surface as school-switch CTA linking to `feature-school-discovery.md`'s `/discover?cip=<target_cip4>` screen (see that spec for the full destination design) |
| `genuinely_impossible` | No plausible path from anything this school offers to this career in the CIP→SOC crosswalk. | Multiple crosswalk queries return empty | No — honest "this isn't a path from here" |

The classification is the structured-tail output of the chip debug trace. The `reasoning` field is **engineer-facing** (lands in logs + audit trails); the `display_reasoning` field is the **student-facing** translation with all internal taxonomy terms removed:

```
---CAREERS---
[
  {"soc": "11-2021", "title": "Marketing Manager", "mode": "crosswalk_quirk",
   "reasoning": "IU reports Marketing under 52.02 but graduates do land here.",
   "display_reasoning": "IU files Marketing coursework under its Business program, but graduates regularly land in core marketing roles."},
  {"soc": "13-1161", "title": "Market Research Analyst", "mode": "direct_hit",
   "reasoning": "Available via 52.14 offered at IU.",
   "display_reasoning": "Available at IU as a direct match."},
  ...
]
```

**Student-facing pill labels** (per §2 Decision #12 — never the internal mode name on screen):

| Internal mode | Student-facing pill | Tone |
|---------------|--------------------|-----|
| `direct_hit` | "Direct match" (or omit pill when the surface already makes availability clear) | success (green) |
| `crosswalk_quirk` | "Through [Business] program" — specific to the broader program the school uses | caution (amber) |
| `adjacent_reachable` | "As a concentration" or "Inside [Business]" | info (blue) |
| `school_gap` | "Not offered here" | info (blue, muted) |
| `genuinely_impossible` | NEVER surfaced — the career isn't rendered at all | — |
| `meme_redirect` | NEVER surfaced as a pill — the redirect response carries its own tonal framing | — |

The frontend consumes `mode` as a semantic signal for pill color + behavior, and `display_reasoning` as the copy. `reasoning` is never rendered in the UI.

When the student clicks one of the surfaced careers, the correction log record carries `clicked_soc`, `clicked_career_title`, and `feasibility_mode`. Only records with cacheable modes are counted by `community_suggestions.get_suggestions`.

**Why this is Gemma-maximal:** the chip debug trace is forced to tool-call at least once per candidate career (for feasibility verification), on top of any initial tool calls for discovery. Local Ollama shows the reasoning happening in real time. This is the headline tool-calling demo beat.

### Community Suggestions Surface

Under the career preview on Set Your Course, when the backend finds `(unitid, input_normalized)` has any cacheable corrections with count ≥ `COMMUNITY_MIN_COUNT` (default 1 for hackathon), the screen renders:

```
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Other students searching "marketing" at IU ended up here:
    → Marketing Manager (17 students)
    → Market Research Analyst (3 students)
```

UX details:
- Up to 3 suggestions shown; more hidden behind a "Show more" expand.
- Clicking a suggestion swaps the current resolution + career preview + appends a new correction log record (kind `correction`, feasibility_mode inherited from the originating click's record). The count increments.
- The section is absent entirely when no suggestions exist — a cold `(unitid, input)` combo looks clean, not broken.
- Copy is kid-voiced and honest ("Other students..." not "People also searched..."). Per `docs/reference/voice-guide.md`.

Backend read path:

```python
# backend/app/services/community_suggestions.py

class Suggestion(TypedDict):
    clicked_soc: str
    clicked_career_title: str
    canonical_cip4: str
    count: int

def get_suggestions(
    unitid: int,
    input_normalized: str,
    top_k: int = 3,
) -> list[Suggestion]:
    """Read the in-memory aggregate and return top_k suggestions ranked
    by count. Only cacheable feasibility modes contribute."""
    ...

def refresh_on_write() -> None:
    """Called by record_correction() after a new line is appended to
    the log. Rebuilds the aggregate incrementally — we've just added
    one row, not 10,000."""
    ...
```

The `/intent/stream` response now carries a `community_suggestions: list[Suggestion]` field (may be empty). The streaming side returns Gemma's reasoning; the community field is a synchronous lookup appended to the final payload — no additional Gemma call.

### Gemma Prompt Design

Reviewed by `@genai-architect` in §5.

- **Streaming resolution prompt:** reuses today's `_INTENT_SYSTEM_PROMPT` but invoked via `stream=True` so the reasoning+JSON arrive progressively. Frontend shows a "Gemma is reading your input..." label that morphs into the reasoning text as it streams.
- **Chip-routing prompt:** new `_CHIP_ROUTING_SYSTEM_PROMPT` per above. Key design notes:
  - Data-grounded voice (voice guide).
  - Permission-granted tool-calling (see §2 Decision #6).
  - Eight explicit buckets in-prompt so Gemma always emits a classification — the `bucket` tail drives observability even when no resolution change happens.
  - Concrete IU-Marketing worked example lives in the `crosswalk_mismatch` bucket description so Gemma has a template.
  - Two structured tails: `---UPDATED_RESOLUTION---` (optional) and `---BUCKET---` (always present).
- **Generation config:** `temperature=0.2`, `max_tokens=600`. Slightly warmer than intent (temp=0) because classifying + explaining benefits from mild variation. Low enough that structured tails stay reliable.
- **Fallback:** on Gemma transport failure, chip dispatch returns the static string: "I'm having trouble reaching the model. Try again in a moment." Resolution is NOT modified. `bucket` is `null`. Log to `logs/gemma.jsonl` as usual. See `feature-gemma-availability.md` (TODO) for the real outage strategy.
- **Tool-call failure inside a chip debug trace:** if a single MCP tool call fails mid-stream (e.g. `get_career_paths` times out), the service retries exactly ONCE with the same args. On second failure, the service notes the tool miss in the prose output ("I couldn't pull the full career list — here's what I can confirm:") and continues with whatever data Gemma had before the tool call. No silent swallow, no cascading retry loops, no frozen stream.

### Pipeline Integration

None. This is runtime student-facing code, not a pipeline artifact.

### Testing Impact Analysis

> **IMPORTANT:** Before finalizing this section, search the test directories for tests related to files being modified.

#### Existing Tests at Risk

**None.** This spec is purely additive to the existing flow. Every existing test file stays untouched. Risk only appears in the follow-up deprecation spec when the old screens come down.

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `frontend/src/screens/SchoolMajorScreen.test.tsx` | All | **None** | Screen stays in place; no code change required. |
| `frontend/src/components/school/EffortLoansPanel.test.tsx` | All | **None** | Component unchanged; still imported by `SchoolMajorScreen`. |
| `frontend/src/screens/CareerPickScreen.test.tsx` | All | **None** | Both pre-reveal and post-reveal paths stay. |
| `backend/tests/services/test_intent.py` | All | **None** | `resolve_intent` unchanged. New flow calls a separate service. |
| `backend/tests/routers/test_intent_router.py` (if exists) | All | **None** | `POST /intent/` path unchanged. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `buildInputStore.test.ts` | Add coverage for new resolution fields (including `confirmed_focus`). Existing assertions on current fields must continue to pass. | Store extended with optional new fields; backwards-compatible. |
| `MenuScreen.test.tsx` | Add one test for the feature-flagged "Set Your Course (beta)" entry (renders when flag set, absent when unset). Existing Menu entry assertions untouched. | New Menu entry is additive. |

No other existing tests are modified. Any test that currently exercises `SchoolMajorScreen`, `EffortLoansPanel`, `CareerPickScreen`, `resolve_intent`, or the `/intent/` router must keep passing without changes.

#### Confirmed Safe

Tests that must NOT break. If any fail, STOP and escalate:

- `backend/tests/services/test_intent.py::*` — intent resolver and YAML path unchanged.
- `backend/tests/services/test_boss_fights.py::*` — boss fight path unchanged.
- `backend/tests/services/test_guidance.py::*` — guidance path unchanged.
- `backend/tests/services/test_builds.py::*` — build orchestration unchanged.
- `backend/tests/services/test_gemma_voice_contract.py::*` — voice contract must not regress.
- `frontend/src/screens/SchoolMajorScreen.test.tsx::*` — old flow stays fully functional.
- `frontend/src/components/school/EffortLoansPanel.test.tsx::*` — component unchanged.
- `frontend/src/screens/CareerPickScreen.test.tsx::*` — old flow stays fully functional.
- `frontend/src/screens/RevealScreen.test.tsx::*` — reveal path unchanged; still reads `buildInputStore`.
- `tests/mcp/test_cip_substitution_integration.py::*` — MCP path unchanged.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/services/test_set_your_course.py` | `TestStreamInitial::test_happy_path_streams_content` | Mocked streaming Gemma; assert deltas are forwarded in order. |
| P0 | `backend/tests/services/test_set_your_course.py` | `TestStreamInitial::test_transport_failure_returns_empty` | Gemma raises; stream completes with empty body; no crash. |
| P0 | `backend/tests/services/test_set_your_course.py` | `TestChipDispatch::test_not_expected_runs_gemma_with_clarifier` | `chip_id="not_expected"` + clarifier → Gemma call happens with clarifier interpolated into the prompt. |
| P0 | `backend/tests/services/test_set_your_course.py` | `TestChipDispatch::test_not_expected_without_clarifier_422` | Missing clarifier on the Gemma-heavy chip is a 422, not a Gemma call. |
| P0 | `backend/tests/services/test_set_your_course.py` | `TestChipDispatch::test_show_less_common_skips_gemma` | `chip_id="show_less_common"` makes no Gemma call. |
| P0 | `backend/tests/services/test_set_your_course.py` | `TestChipDispatch::test_wrong_major_skips_gemma` | `chip_id="wrong_major"` makes no Gemma call. |
| P0 | `backend/tests/services/test_set_your_course.py` | `TestChipDispatch::test_bucket_tail_parsed_into_response` | Gemma response includes `---BUCKET---` JSON; parsed into the `bucket` field. |
| P0 | `backend/tests/services/test_set_your_course.py` | `TestChipDispatch::test_resolution_tail_parsed_when_present` | Optional `---UPDATED_RESOLUTION---` tail parses into `updated_resolution`. |
| P0 | `backend/tests/services/test_set_your_course.py` | `TestChipDispatch::test_no_resolution_tail_returns_none` | Response without `---UPDATED_RESOLUTION---` → `updated_resolution` is None. |
| P0 | `backend/tests/services/test_set_your_course.py` | `TestChipDispatch::test_tool_call_results_get_merged_into_prompt` | When Gemma emits a tool call, the service executes the MCP tool and feeds results back. |
| P0 | `backend/tests/services/test_set_your_course.py` | `TestChipDispatch::test_malformed_tails_are_ignored_no_crash` | Half-written tails are silently dropped; endpoint still returns 200. |
| P0 | `backend/tests/services/test_set_your_course.py` | `TestConfirmedFocus::test_confirmed_focus_tail_parsed_into_response` | Gemma response with `---CONFIRMED_FOCUS---` tail → `ChipResponse.confirmed_focus` populated. |
| P0 | `backend/tests/services/test_set_your_course.py` | `TestConfirmedFocus::test_no_confirmed_focus_tail_leaves_field_none` | Response without the tail → `confirmed_focus` is None. |
| P0 | `backend/tests/services/test_set_your_course.py` | `TestConfirmedFocus::test_initial_stream_never_sets_confirmed_focus` | `stream_initial_resolution` does NOT emit `confirmed_focus` under any input. Only the chip dispatch path can set it. |
| P0 | `backend/tests/services/test_set_your_course.py` | `TestConfirmedFocus::test_confirmed_focus_dropped_when_bucket_is_semantic_drift` | If Gemma emits both `---UPDATED_RESOLUTION---` (bucket=semantic_drift) and `---CONFIRMED_FOCUS---`, the service drops `confirmed_focus` — sub-focus is meaningless when the 4-digit resolution itself changed. |
| P0 | `backend/tests/services/test_set_your_course.py` | `TestConfirmedFocus::test_confirmed_focus_dropped_when_bucket_is_intent_divergence` | Same invariant as semantic_drift — intent_divergence changes the 4-digit scope; sub-focus does not carry. |
| P0 | `backend/tests/services/test_set_your_course.py` | `TestConfirmedFocus::test_confirmed_focus_requires_tool_call_evidence` | Mock a chip run where Gemma claims `confirmed_focus` in the tail without having made a tool call; assert the service strips it. (Anti-fabrication guard — sub-focus is legitimate only when verification happened.) |
| P1 | `backend/tests/services/test_set_your_course.py` | `TestConfirmedFocus::test_confirmed_focus_strips_numeric_codes` | If Gemma accidentally emits `"confirmed_focus": "Deaf Education (13.1003)"`, the service strips the parenthetical numeric code before returning. Defense-in-depth against Decision #12 violation. |
| P1 | `frontend/src/hooks/useSetYourCourse.test.ts` | `TestConfirmedFocus::test_confirmed_focus_persists_on_resolution_state` | Chip response with `confirmed_focus` → store's `currentResolution.confirmed_focus` updated. |
| P1 | `frontend/src/hooks/useSetYourCourse.test.ts` | `TestConfirmedFocus::test_major_edit_clears_confirmed_focus` | Editing the major input (which re-resolves from scratch) clears any prior `confirmed_focus` — the student changed topic, the sub-focus does not carry. |
| P0 | `backend/tests/services/test_correction_log.py` | `TestAppend::test_writes_one_line` | `record_correction` writes exactly one JSON line. |
| P0 | `backend/tests/services/test_correction_log.py` | `TestAppend::test_missing_dir_creates_it` | First-run creates the parent directory. |
| P0 | `backend/tests/services/test_correction_log.py` | `TestAppend::test_concurrent_writes_do_not_interleave` | Two threads calling `record_correction` produce two complete lines. |
| P0 | `backend/tests/routers/test_set_your_course_router.py` | `TestStream::test_streams_to_client` | Via FastAPI test client, assert chunked response. |
| P0 | `backend/tests/routers/test_set_your_course_router.py` | `TestChip::test_returns_chip_response` | Mocked service returns a valid response; router forwards it. |
| P0 | `frontend/src/hooks/useSetYourCourse.test.ts` | `TestDebounce::test_debounces_major_input` | Rapid keystrokes produce one resolution call after settle. |
| P0 | `frontend/src/hooks/useSetYourCourse.test.ts` | `TestDebounce::test_cancels_in_flight_on_edit` | Editing mid-stream aborts the prior request. |
| P0 | `frontend/src/hooks/useSetYourCourse.test.ts` | `TestChip::test_not_expected_opens_clarifier_then_dispatches` | Tapping the Gemma-heavy chip opens the clarifier field; submitting it calls `/intent/chip`. |
| P0 | `frontend/src/hooks/useSetYourCourse.test.ts` | `TestChip::test_updated_resolution_replaces_current` | `updated_resolution` in the response swaps `currentResolution` in the store. |
| P0 | `frontend/src/hooks/useSetYourCourse.test.ts` | `TestChip::test_show_less_common_toggles_tiers_no_fetch` | Chip tap mutates local state only; no network request fires. |
| P0 | `frontend/src/hooks/useSetYourCourse.test.ts` | `TestChip::test_wrong_major_resets_major_field` | Chip tap clears the major input; no network request fires. |
| P0 | `frontend/src/hooks/useSetYourCourse.test.ts` | `TestCommit::test_commits_and_logs_correction_when_resolved_cip_changed` | Commit sends the correction payload when current ≠ initial. |
| P0 | `frontend/src/hooks/useSetYourCourse.test.ts` | `TestCommit::test_commits_without_correction_when_resolution_unchanged` | No correction payload when current == initial. |
| P0 | `frontend/src/screens/SetYourCourseScreen.test.tsx` | `TestRender::test_renders_all_sections` | School, major, sliders, preview, three-chip rail all present. |
| P0 | `frontend/src/screens/SetYourCourseScreen.test.tsx` | `TestFlow::test_commit_navigates_to_reveal` | Committing routes to `/reveal`. |
| P1 | `frontend/src/screens/SetYourCourseScreen.test.tsx` | `TestLowConfidence::test_commit_shows_nudge_not_gate` | Low-confidence resolution → commit button enabled with a visible soft nudge. |
| P1 | `frontend/src/screens/SetYourCourseScreen.test.tsx` | `TestStartOver::test_resets_state` | Start-over clears school / major / resolution / debug trace. |
| P1 | `backend/tests/services/test_set_your_course.py` | `TestObservability::test_gemma_jsonl_has_call_site_tag` | Every Gemma call carries `call_site: "set_your_course_resolve"` or `"set_your_course_chip"` + chip_id. |
| P2 | `frontend/src/screens/SetYourCourseScreen.test.tsx` | `TestMobileCollapse::test_sliders_collapsed_by_default_below_breakpoint` | Responsive collapse. |

#### Test Data Requirements

- Mocked Gemma responses for the chip route: a set of canned JSONs covering (a) prose + bucket tail only, (b) prose + bucket + updated-resolution tails, (c) response with tool call, (d) malformed tails, (e) each of the 8 bucket values at least once across the suite.
- Mocked MCP server: reuse existing fixtures; extend with `get_career_paths` mock returning predictable career rows.
- Tmp `student_corrections.jsonl` via `tmp_path` in each test — no state leakage.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** PENDING
#### Findings
[Filled in by @fp-architect — new flow, state management, endpoint contracts, screen replacement.]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

### @fp-data-reviewer Review
**Status:** PENDING
#### Findings
[Filled in by @fp-data-reviewer — live preview semantics, correction log shape, accuracy floor for ambiguous input.]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

### @genai-architect Review (ad-hoc)
**Status:** PENDING
#### Findings
[Filled in by @genai-architect — chat prompt, streaming shape, tool-calling loop, conversation threading.]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

---

## §6 Implementation Log

**Status:** PENDING

### Files Modified
| File | Change Summary |
|------|---------------|

### Deviations from Spec
[Any divergence from §4 and why]

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|

---

## §7 Test Coverage

**Status:** PENDING

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest (backend) | | | | |
| pytest (root) | | | | |
| vitest | | | | |

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@fp-design-auditor)
**Status:** PENDING

### Code Review (@faang-staff-engineer)
**Status:** PENDING
#### Findings
[Filled in by reviewer — security, performance, error handling, streaming correctness, concurrency.]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

---

## §9 Verification

**Status:** PENDING

### Backend (@fp-builder)
| Check | Result |
|-------|--------|
| Lint (ruff) | |
| Type check (mypy) | |
| Tests (pytest) | |

### Pipeline (@fp-builder)
| Check | Result |
|-------|--------|
| Lint (ruff src/ tests/ scripts/) | |
| Tests (pytest tests/) | |

### Frontend (@fp-builder)
| Check | Result |
|-------|--------|
| TypeScript | |
| Tests (vitest) | |
| Production build (Vite) | |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|

---

## §10 Discussion

```
[2026-04-19] Initial draft. Evolved out of the parked feature-learned-alias-cache
spec after product review with @fp-product-partner. The prior cache was
optimization work masquerading as a feature; this spec puts Gemma ON the
student path as the flagship demo moment — tool-calling, streaming, and
student-visible correction.

[2026-04-19 revision] Correction surface narrowed from open chat to three
kid-voiced chips ("Not what I expected" + free-text clarifier, "Show me
less common paths", "Wrong major") after founder pushback on engineer-voiced
chip labels ("a 17-year-old is not going to tap 'this school reports oddly',
they're going to tap 'I don't see my shit'"). Benefits: (a) guardrails
surface collapses to one scoped clarifier field, not open chat; (b) Gemma
does more reasoning per tap — it classifies the complaint into one of
seven internal buckets AND runs the debug trace AND responds; (c) smaller
build — no conversation store, no multi-turn state; (d) demo-tighter — a
chip tap is more reproducible on video than free-form typing.

[2026-04-19 design-lock revision] Design visionary + product partner
reviewed the revised spec; founder reviewed the Brightpath HTML mockup
at docs/specs/design/set-your-course-mockup/index.html and locked the
following calls:

- Community suggestions visible at count >= 1 (not 3). Founder: "it's fine,
  we don't track who the student is." Panopticon concern resolved.
- Chip label stays "Show me less common paths" (A), not "Show me weirder
  jobs" (B). Founder: "weird jobs is like reptile wrangler, not marketing
  analyst" — the chip is about surfacing the stretch/less-common tiers,
  not about wandering.
- school_gap ships a v0.5 stub (pre-computed top-10 list, no zip sort, no
  MCP tool wiring) rather than cutting the CTA entirely. See
  feature-school-discovery.md for the carve-out.
- Soft nudge copy upgraded per PM critique: "Gemma wasn't sure on this
  one. Worth a sanity check?" (names the source of uncertainty; stays
  on-voice).
- Start Over ships with a one-tap confirm dialog. Protects against
  mis-click loss on a multi-step screen.
- Consent-of-loop disclosure line ships under the chip rail with founder
  placeholder: "We don't track any identifying info — just that someone
  found this mapping useful." Flagged for @fp-copywriter final polish.

Founder also corrected the spec's framing: "the major is never wrong,
that's what the student wants. Our mapping of major to job might be
wrong." Two renames follow:
- Chip label "Wrong major" -> "Change my major" (honors the student
  revising their plan; does not blame them).
- Chip-routing bucket `major_mismatch` -> `intent_divergence` (describes
  a data observation, not a student failure). Bucket #6 rewritten to
  explicitly frame alternatives as options the student can consider,
  never as corrections.

[2026-04-19 ship-alongside revision] Founder direction: "can you modify
the spec to make these pages separate from the existing pages? we can
deprecate old when new is done."

Spec restructured from a cut-over replacement to an additive, coexisting
flow:

- New screen ships at `/set-your-course`. Existing `/school` flow stays
  fully wired up, fully tested, fully functional.
- Menu gains a feature-flagged "Set Your Course (beta)" entry gated on
  `VITE_SET_YOUR_COURSE_ENABLED`. Default off in production, on in the
  hackathon demo + beta-tester builds.
- Existing components (`SchoolMajorScreen`, `EffortLoansPanel`, pre-
  build `CareerPickScreen`) and their tests are **UNCHANGED** by this
  spec. No mark-unused, no router removal, no import rewiring.
- `major_lookup.py` stays in use for the existing flow; the new flow
  bypasses it via the new `set_your_course.py` service. Deletion moves
  to the follow-up deprecation spec.
- `buildInputStore` gains new optional fields (including `confirmed_focus`)
  that default to null / undefined so the existing flow's partial writes
  remain valid.
- `RevealScreen` reads the store the same way from both writers.
- Both flows commit independently; the store shape is the contract.

Benefits of the ship-alongside shape:
(a) de-risks the build — a broken new flow does not break the existing
    product.
(b) gives beta testers (founder's wife — a deaf-education teacher; founder's
    daughter and her friends — unpredictable input) a working fallback
    while the new flow collects real-world signal.
(c) separates the unified-screen UX experiment from the destructive act
    of removing working code; the deprecation decision is made on
    evidence, not prediction.
(d) removes all `Existing Tests at Risk` from this spec — §4 Testing
    Impact Analysis now reports zero tests at risk and zero authorized
    destructive modifications.

The deprecation spec will land post-beta and is out of scope here. It
will cover: deletion of the three old screens, removal of the feature
flag, removal of `major_lookup.py`, migration of any still-useful tests
into the new screen's suite, and the commit that makes `/set-your-course`
the canonical route for school+major+career selection.

[2026-04-19 pipeline-grain + confirmed_focus revision] V2 anchored
regression completed (`reports/bugfix-disable-intent-yaml-regression-v2-
2026-04-19.md`) with headline 42.3% match vs the YAML. The report's
per-entry breakdown showed a sharp split: Family 52 Business and
Family 13 4-digit entries anchor to 99%+, while 33 Family 13 6-digit
sub-leaves score 0% (Gemma picks a same-family different-leaf). The
report proposed a hybrid allowlist keeping YAML for the 33 sub-leaves.

That recommendation was rejected after verifying the pipeline grain: the
data contract at `governance/data-contracts/consumable-program-career-
paths.yaml` specifies cipcode as 4-digit XX.XX format with a CHECK
constraint regex enforcing it. Every student-facing surface — tiles,
pentagon stats, boss scores, ROI — joins on the 4-digit prefix. Gemma's
6-digit sub-leaf drift collapses to the same 4-digit family and produces
identical tiles. The V2 script's match check was measuring sub-leaf
precision the pipeline does not use.

So V2 does not change the "YAML retires from the resolution path
entirely" lock from Topic 13. What it surfaced is a narration hygiene
risk: Gemma's free-form prose, if it names a specific sub-specialty
Gemma inferred on its own, will confidently mislabel the student's
program even when the tiles are right. A deaf-ed teacher who types
"deaf education" could see correct Special Education career tiles
accompanied by prose calling it "Learning Disabilities Education"
because Gemma's unconfirmed sub-leaf guess landed there.

The fix is two new decisions (#15 + #16) and one structured-tail
extension:

- Decision #15 declares the 4-digit pipeline grain as the invariant the
  spec relies on. Also explicitly rejects the V2 report's hybrid
  allowlist — it would reinstate a static lookup in the middle to
  preserve sub-leaf fidelity the rest of the pipeline does not use,
  contradicting the reinforcement-loop design locked 2026-04-19.
- Decision #16 says sub-focus labels are student-driven, not Gemma-
  driven. Initial resolution narrates at the 4-digit level. The student
  names any sub-specialty in their clarifier. Gemma verifies via tool
  call. If verified, `confirmed_focus` is set and every downstream prose
  surface in the session (boss narration, Gemma's Take, skill recs, etc.)
  uses it. If not verified, Gemma stays at the 4-digit level and does
  not fabricate.
- `ChipResponse` gains a `confirmed_focus: str | None` field. `IntentResult`
  gains the same field (additive, backwards-compatible) so the frontend
  can persist it on `currentResolution` and downstream requests that
  include the resolution auto-propagate it. The chip-routing prompt
  grows a third optional structured tail (`---CONFIRMED_FOCUS---`) that
  the service reads and attaches to the response.

Net: the architecture does not change, the demo story does not change,
and students who name a sub-specialty get a product that uses their
words. The V2 data, read through the pipeline grain, became a design
refinement — not a retreat.

[2026-04-19 reinforcement-loop revision] After the V1 YAML regression
returned 9.1% unanchored and the founder rejected YAML-in-the-middle as
inelegant, the design pivoted to a reinforcement loop + community
suggestions surface:

- YAML short-circuit retired from the resolution path entirely (stays as
  break-glass during V2 transition; deleted post-demo).
- Chip debug trace now actively tool-calls the crosswalk / careers data
  to find what the student was really after, then classifies each
  candidate into one of 5 feasibility modes (direct_hit, crosswalk_quirk,
  adjacent_reachable, school_gap, genuinely_impossible). Only the first
  three feed the cache — that's the self-defending property.
- Student-clicked careers append to the correction log; the community_
  suggestions service aggregates and surfaces "Other students searching
  X at Y ended up here:" under the career preview.
- No pre-seed. Cold start = pioneer student uses the chip flow; Gemma's
  tool-calling finds the right career; click = cache entry. Subsequent
  students benefit from the crowd signal. Self-healing.
- Kaggle narrative updates accordingly: "No static lookup. Gemma reasons
  and tool-calls live; the product learns from use." The pioneer flow
  and the beneficiary flow are both visible demo beats.

Open questions for architecture review:
- Streaming: SSE vs chunked JSON fetch streaming — which fits FastAPI +
  React idiomatically without dragging in new deps?
- Tool-calling loop: single-turn-with-pre-fetch vs multi-step "Gemma
  proposes, service executes, Gemma continues" — which is feasible given
  Gemma 4's function-calling maturity on Ollama?
- Screen replacement vs coexistence: RESOLVED 2026-04-19 per founder
  direction. Ship alongside. See the [2026-04-19 ship-alongside revision]
  entry above and §2 Decision #1. Deprecation is a follow-up spec gated
  on beta feedback + founder sign-off.
- Correction log: committed to git at every write means constant small
  diffs. Acceptable for hackathon; revisit for production.
- Soft-nudge on low-confidence commit: does the nudge wording belong
  in the design spec or in the fp-copywriter pass?

Cut list (v2):
- Occupation-first mode.
- Open chat / multi-turn conversation.
- Reading the correction log (any form of cache).
- Cross-school hint transfer.
- Voice input.
- Admin view of corrections.
```

---

## §11 Final Notes

**Human Review:** PENDING

[Final thoughts, lessons learned, follow-up items populated at COMPLETE.]

---

## §12 Shipping Gate (Not Standard, But Load-Bearing)

**This feature ships internally to the dev team on COMPLETE of the workflow above.**
**This feature does NOT ship to judges, beta users, or pilot schools until `docs/specs/feature-chat-guardrails.md` is a real spec, reviewed, and implemented.**

The PR that closes this spec must state the blocker in its description. Reviewers are empowered to reject any subsequent PR that exposes the chat surface externally until the guardrails gate lifts.
