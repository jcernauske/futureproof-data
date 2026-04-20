# Feature: Set Your Course — Unified School / Major / Career Screen with Conversational Correction

## Claude Code Prompt

```
Read the spec at docs/specs/feature-set-your-course.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review §1–§4 for: new resolution flow (single
     screen, live preview, streaming Gemma chat), state management
     (buildInputStore extensions), new/modified API endpoints, the
     **additive routing model** (new `/set-your-course` route alongside
     the unchanged `/school` flow; feature-flagged Menu entry; old
     screens / `major_lookup.py` untouched pending a follow-up
     deprecation spec), and **broad-CIP lookup parity** (see §10 open
     questions — does the new flow's single-CIP `IntentResult` interact
     safely with `_handle_get_career_paths`'s broad-CIP substitution
     branch that the old `/school` flow depends on? Raised by
     `reports/cip-routing-ask-gemma-diagnosis-2026-04-19.md`, which
     verified the same state-duplication bug class in the old flow).
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

## Status: COMPLETE

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
**Status:** COMPLETE
**Reviewed:** 2026-04-19

#### System Context

Set Your Course lands a second, independent resolution path alongside the existing `/school` → `/career-pick` stepped flow. The new path crosses four layers: frontend screen + hook + store extension, API client (`streamIntent`, `dispatchChip`), FastAPI router (`/intent/stream`, `/intent/chip`), and a new service (`set_your_course.py`) that owns a chip-routing prompt with MCP tool-calling and a streaming variant of `gemma_client`. It writes append-only to a new reference file (`data/reference/student_corrections.jsonl`) and reads back from an in-memory aggregate for the community-suggestions surface. Downstream of commit, it reuses the existing `RevealScreen` + `/build/*` contracts — so the new flow's promise is: *produce a `(unitid, cipcode, effort, loans, major_text, parent_cip?)` payload compatible with the store the old flow already writes.*

That last word — *compatible* — is where the architecture risk lives.

#### Data Flow Analysis

Trace the happy path, resolve → preview → commit:

1. Student types `"marketing"` at IU → 300ms debounce in `useSetYourCourse` → `streamIntent({major_text, school_name, unitid, programs})` → `POST /intent/stream`.
2. Router calls `set_your_course.stream_initial_resolution(...)` → Gemma `stream=True` via new `gemma_client.generate_stream_async` → deltas forwarded to browser + a synchronous `community_suggestions.get_suggestions(unitid, input_normalized)` appended to final payload.
3. Frontend parses the structured-tail JSON into `IntentResult`, writes `currentResolution` + `initialResolution` to `buildInputStore`.
4. Preview cards: frontend calls existing `getOutcomes(unitid, cipcode, effort, loanPct, studentMajor)` → `POST /build/outcomes` → MCP `get_career_paths` → **`_handle_get_career_paths`** in `src/mcp_server/futureproof_server.py:2013`.
5. Chip dispatch (if tapped): `POST /intent/chip` → `handle_chip_dispatch` → Gemma with tool-calling → optional `updated_resolution`, `confirmed_focus`, and `community_suggestions` refresh.
6. Commit → append correction log → `refresh_on_write` → navigate to `RevealScreen`. Reveal reads the store and calls `createBuild(…, lookupCip = major.parentCip || major.cipCode, …)` — the same contract the old flow uses.

Zone discipline: this is runtime student-facing code, not a pipeline artifact. §4 says so explicitly and it's correct. The correction log lives in `data/reference/` — not Bronze/Silver/Gold. It is `refresh_on_write` read-after-write, not a separate ingestor — acceptable for hackathon.

Where the flow is clean: the streaming contract is chunked HTTP from FastAPI (`StreamingResponse` + async generator). No new transport. Chip dispatch is one stateless POST per tap, no conversation store, no turn counter. Abort is an `AbortController` on the browser cancelling a single fetch — fits. The `buildInputStore` extension is additive (new optional fields default to `null`/`undefined`), so `RevealScreen` + the old flow keep working.

Where the flow has a gap the spec must close before coding: step 4 above. See Concern #1.

#### Contract Review

**Pydantic.** Models are Pydantic v2 compatible, but `IntentStreamRequest.programs: list[dict[str, Any]]` and `ChipRequest.programs: list[dict[str, Any]]` mirror the existing `IntentRequest.programs: list[dict]` weakness — we already have a `ProgramResult` TypedDict on the frontend (`frontend/src/types/buildInput.ts:52`) but no Pydantic model. Not a blocker (matching existing debt, not deepening it) — flagged as Concern #9.

**`IntentResult` extension** (`backend/app/models/career.py:317`): additive `confirmed_focus: str | None = None`. Backwards-compatible — existing `resolve_intent` never sets it, the Gemma-path-only chip dispatcher is the sole writer.

**`ChipResponse.bucket` enum** — nine values including `no_issue_found`, aligned with the eight prompt buckets plus `None` for non-Gemma chips. Sound.

**`CtaLink`** is referenced on `ChipResponse.cta_link` but not defined in §4's Pydantic snippet. See Concern #4.

**`FeasibilityMode` vs `bucket`.** Two independent classifications on the same response: `bucket` describes *why the student pushed back*, `feasibility_mode` describes *cacheability per candidate career*. Well-scoped, separate fields, separate tails. Rotting-apart resistance — good.

**Frontend `buildInputStore` extension.** Spec adds `currentResolution`, `initialResolution`, `hasCorrected`, `debugTrace`, `confirmed_focus`. Today's store (`frontend/src/store/buildInputStore.ts:10-30`) has only `phase`, `school`, `programs`, `major`, `effort`, `loans`. New fields must be **optional/nullable** and their setters must **coexist with** `setMajor` — old flow writes `major.parentCip`/`major.cipCode`/`major.rawText` via `setMajor`; new flow writes the full `IntentResult` via a new setter. Both must populate `major: MajorSelection` at commit time so `RevealScreen` still reads `major.parentCip || major.cipCode` (`RevealScreen.tsx:76`) unchanged.

**API client contract.** `streamIntent(input, signal)` and `dispatchChip(chipId, clarifier, currentState, signal)` — native fetch streaming with `AbortController`. Chunked-JSON vs SSE is an open question in §10; both work, chunked JSON is lighter weight and doesn't need a new dep. Recommend chunked line-delimited JSON — specify before implementation.

**Gemma function-calling.** Tool schemas (`get_career_paths`, `get_occupation_data`, `get_regional_price_parity`) already exist on the MCP server. The chip service dispatches them via `mcp_client`. Gemma 4 tool-calling maturity on local Ollama is the §10 open question — doesn't block the spec, but the implementation must have a graceful fallback when Gemma emits a malformed tool-call or none at all (§4 already covers tool-call timeouts; extend that discipline to *malformed* tool calls too).

#### Findings

##### Sound

- **Ship-alongside model is architecturally clean.** `/school` path is fully untouched. `App.tsx` gets exactly one new route. `MenuScreen` gets one feature-flagged tile. `major_lookup.py` stays. Zero risk to the existing test surface — §4 Testing Impact Analysis correctly reports zero at-risk tests.
- **Store extension is backwards-compatible.** New fields default to null/undefined. Old-flow partial writes via `setMajor` stay valid. `RevealScreen` reads the same `major.parentCip || major.cipCode` contract from either writer.
- **Zone boundaries respected.** Chip-routing prompt and streaming generation live in the backend service layer, not a pipeline stage. Correction log is reference data. MCP tools are the only data-access surface.
- **Additive Pydantic extension on `IntentResult`.** `confirmed_focus: str | None = None` is the textbook way to grow a model without breaking existing deserializers.
- **Chip dispatch stateless.** No conversation store. No turn counter. One chip tap = one POST = one optional Gemma call = zero or one resolution update. Cheap to reason about, cheap to test, cheap to roll back.
- **`bucket` / `feasibility_mode` separation.** Complaint classification vs candidate cacheability on separate fields, separate tails. Decomposition holds up.
- **Streaming contract matches OpenAI-compatible client.** Both Ollama and OpenRouter support `stream=True` natively; no new transport layer. `generate_stream_async` addition preserves the existing `generate`/`generate_async` API (additive).

##### Concerns

- **Concern #1 — Broad-CIP substitution parity is broken under the new flow.** Traced through `src/mcp_server/futureproof_server.py:2013-2124`. `_handle_get_career_paths` reads `student_major` and calls `_find_major_intent` (`futureproof_server.py:1471`), which loads `data/reference/major_to_cip.yaml` — the YAML the new flow is trying to retire from the resolution path. Today's old flow resolves `matched_cip` via Gemma + `parent_cip` via `_derive_parent_cip` (`intent.py:388`), then the frontend routes `cipcode = parent_cip || matched_cip` (see `CareerPickScreen.tsx:62, 118` and `RevealScreen.tsx:76`) to `/build/outcomes`. The MCP handler then runs its own YAML lookup to fire the substitution branch. **In the new flow, the IntentResult carries no `parent_cip` / `school_reported_cip4` field in the streaming shape §4 draws** — the `---UPDATED_RESOLUTION---` tail is `{"matched_cip", "matched_title", "confidence", "reasoning"}` only, and `IntentStreamRequest` doesn't emit one at all. If `useSetYourCourse` calls `getOutcomes(unitid, matched_cip, …, student_major=major_text)`: (1) the MCP still does a YAML lookup (not retired from that code path), (2) when no YAML entry exists for the input the handler falls into the `substitution_note` "no lookup match" branch (L2082), and (3) because the caller passed the specific leaf `52.14` rather than the school's reported broad `52.01`, the substitution branch *never fires at all* — outcomes come back from the broaden fallback, not from the targeted substituted-rows path. The `/school` flow succeeds because its `/intent` response carries `parent_cip` and the frontend routes `parentCip || cipCode`. The new flow has neither field on `IntentResult` nor the routing rule. §10 flagged this as an open question; it cannot remain open — resolve before implementation begins. **Impact:** new flow's preview cards either break outright (`/build/outcomes` returns broaden-fallback career set, not the targeted-substituted rows that make the IU-Marketing demo work) OR present systematically different careers from the `/school` flow for the same student input, which is a live demo inconsistency. `reports/cip-routing-ask-gemma-diagnosis-2026-04-19.md` raised the same state-duplication bug class — this is that bug pre-shipped into the new flow. **Recommendation:** pick option (b) from §10 — add `school_reported_cip4: str | None` to `IntentResult` (streamed resolution + structured tail + Pydantic model + frontend mirror), populate it in `stream_initial_resolution` via a `_derive_school_reported_cip4(programs, matched_cip)` helper modeled on `intent.py::_derive_parent_cip`, and have `useSetYourCourse` route `schoolReportedCip4 || matchedCip` to `/build/outcomes` (and to `/build` at commit). Option (a) (force Gemma to match at school-reported grain via prompt) is not safe — V2 regression already demonstrated Gemma drift. Option (c) (route past substitution entirely) loses the crosswalk-quirk case, which is *the IU-Marketing demo*. One-field contract extension, not a day of rework.

- **Concern #2 — MCP handler's YAML dependency is load-bearing for *both* flows, not "only the old flow."** The spec claims `major_lookup.py` stays in use by the old `/school` flow only (§4 File Changes comment on `major_lookup.py`). Misleading — the MCP handler at `futureproof_server.py:2080` calls `_find_major_intent` which loads `major_to_cip.yaml` on *every* `/build/outcomes` call, regardless of which flow originated the request. Any `student_major` the new flow sends — `"marketing"`, `"deaf education"`, `"pre-PT"` — hits the same YAML on the MCP side. The spec's "YAML retires from this flow entirely" promise only holds for the *intent resolution* step; the substitution step still reads YAML. **Impact:** documentation mismatch that will mislead the deprecation-spec author and the Kaggle narrative ("No static lookup" is false for `/build/outcomes`). **Recommendation:** update §2 Constraints + §4 File Changes to clarify that `major_lookup.py` (and `major_to_cip.yaml`) stay live for the MCP substitution path on both flows; retirement is a pipeline-side change tracked by the follow-up deprecation spec.

- **Concern #3 — `generate_stream_async` semaphore + logging contract must mirror `generate_chat_async`.** `gemma_client.py:310-360` holds `_get_semaphore()` around every Gemma call and writes one JSONL record per call (`duration_ms`, `finish_reason`, `truncated`, `response`). The streaming variant must (a) acquire the same semaphore for the full stream duration, (b) write exactly one JSONL record after the stream completes (accumulate tokens during streaming, flush on completion/error), and (c) propagate the `extra={"call_site": "set_your_course_resolve" | "set_your_course_chip", "chip_id": …}` stamping convention. **Impact:** if stream deltas are logged as separate records, data-reviewer grep tools double-count; if no record is written on stream error, we lose the failure signal the non-stream path guarantees. **Recommendation:** call out the "one JSONL record per stream, written on completion or error" invariant in the `generate_stream_async` docstring, and upgrade `test_gemma_jsonl_has_call_site_tag` from P1 to P0 with stream-path coverage.

- **Concern #4 — `CtaLink` Pydantic model is referenced but not defined.** `ChipResponse.cta_link: CtaLink | None = None` is used for the school-discovery CTA on `school_gap`, but §4 doesn't show the model's fields. **Recommendation:** add a one-stanza Pydantic definition to §4 Data Model Changes — minimum `label: str`, `href: str`, `kind: Literal["school_discovery_v05"]`.

- **Concern #5 — `ChipRequest.clarifier` missing server-side length validator.** Success Criteria line 141 says "280-character maximum (enforced both client-side and server-side Pydantic validator)." §4's Pydantic stanza declares `clarifier: str | None` with no `max_length`. **Recommendation:** `clarifier: Annotated[str, StringConstraints(max_length=280)] | None = None`. Add a P0 test `test_not_expected_clarifier_over_280_chars_422`.

- **Concern #6 — `_INTENT_SYSTEM_PROMPT` reuse for streaming is under-specified.** §4 "Gemma Prompt Design" says streaming "reuses today's `_INTENT_SYSTEM_PROMPT` but invoked via `stream=True`." But `_INTENT_SYSTEM_PROMPT` (`intent.py:82`) emits a single JSON object. Streaming that JSON token-by-token means the frontend sees partial JSON until the final brace. The §3 design lock says "streaming is paragraph-by-paragraph with a `gemma-shimmer` keyframe" — that implies prose first, structured tail second. The existing intent prompt has no prose preamble. **Impact:** if the new flow reuses `_INTENT_SYSTEM_PROMPT` verbatim, the user sees `{"matched_cip": "52.` streaming in — not prose. The §3 streaming UX doesn't work with the current prompt shape. **Recommendation:** write a new `_STREAM_INTENT_SYSTEM_PROMPT` in `set_your_course.py` that emits 1–2 sentences of reasoning followed by a `---RESOLUTION---` tail (mirror the chip-prompt shape). Do NOT modify `intent.py::_INTENT_SYSTEM_PROMPT` — don't rot the old flow.

- **Concern #7 — `community_suggestions.refresh_on_write()` thread-safety.** `correction_log.record_correction` uses a `threading.Lock` for the JSONL append. `refresh_on_write` updates an in-memory dict. Two concurrent appends → two concurrent refreshes → torn aggregate state. Rare in hackathon traffic, but will surface in a live demo with multiple clients. **Recommendation:** hold the same write lock across the refresh, or switch `refresh_on_write` to an additive single-record delta API that takes the just-written record as input (avoids re-reading the file; matches the "we've just added one row, not 10,000" comment in §4).

- **Concern #8 — Feature-flag gating is incomplete.** `VITE_SET_YOUR_COURSE_ENABLED` is read in `MenuScreen.tsx` only. That's correct for hiding the tile, but `App.tsx` always mounts `<Route path="/set-your-course">`, so a bookmarked URL bypasses the gate. **Recommendation:** either gate the `<Route>` element on the flag in `App.tsx` (recommended — inaccessible when flagged off), or explicitly accept deep-link access and document in §2 Constraints. Pick one before implementation.

- **Concern #9 — `IntentStreamRequest.programs: list[dict[str, Any]]`** — same weak-typing as existing `IntentRequest.programs`. Not a regression, not a blocker. Tech debt to consolidate under the deprecation spec.

- **Concern #10 — Route mount order.** `POST /intent/stream` + `POST /intent/chip` share the `/intent/` namespace with existing `POST /intent/` + `POST /intent/confirm`. **Recommendation:** `set_your_course.py` router uses `prefix="/intent"` with explicit `/stream` + `/chip`; register in `main.py` after the existing intent router so any accidental path reuse fails loudly at startup.

##### Blockers

None. Concern #1 is significant but solvable inside the existing §4 scope via a one-field Pydantic extension + one helper + one frontend routing rule — not a restructure.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

#### Conditions (CHANGES REQUESTED)

1. **Resolve broad-CIP parity** (Concern #1). Add `school_reported_cip4: str | None = None` to `IntentResult` (`backend/app/models/career.py:317` + frontend mirror at `frontend/src/types/buildInput.ts:62`). Populate in `stream_initial_resolution` via a `_derive_school_reported_cip4(programs, matched_cip)` helper modeled on `intent.py::_derive_parent_cip`. `useSetYourCourse` routes `schoolReportedCip4 || matchedCip` to `/build/outcomes` (and `/build` at commit). Add tests `test_routes_school_reported_cip_when_school_reports_broad_family` and `test_routes_matched_cip_when_school_reports_the_leaf_directly`.

2. **Correct the `major_lookup.py` narrative** (Concern #2) in §2 Constraints + §4 File Changes. `major_lookup.py` + `major_to_cip.yaml` stay live for BOTH flows at the MCP substitution side; only intent-resolution use is retired here.

3. **Define `CtaLink`** inline in §4 Data Model Changes (Concern #4). Minimum `label: str`, `href: str`, `kind: Literal["school_discovery_v05"]`.

4. **280-char `max_length` on `ChipRequest.clarifier`** (Concern #5). `Annotated[str, StringConstraints(max_length=280)] | None = None`. Add a P0 oversize-returns-422 test.

5. **Specify `_STREAM_INTENT_SYSTEM_PROMPT`** (Concern #6) in `set_your_course.py` — prose first, `---RESOLUTION---` tail second. Do NOT modify `intent.py::_INTENT_SYSTEM_PROMPT`.

6. **Document `generate_stream_async` invariants** (Concern #3). One JSONL record per stream, written on completion or error. Module semaphore held for full stream duration. Upgrade `test_gemma_jsonl_has_call_site_tag` to P0 with stream-path coverage.

7. **Decide feature-flag gating** (Concern #8). Recommended: also gate the `<Route>` element in `App.tsx`.

8. **Thread-safety for `refresh_on_write()`** (Concern #7). Hold the write lock across the refresh OR switch to a single-record delta API. Call out in §4 Service Changes.

When conditions 1–8 are met, implementation can proceed. Architecture is sound; contracts need tightening before code. Re-review by @fp-architect is not required — conditions are mechanical; any downstream agent can verify.

### @fp-data-reviewer Review
**Status:** COMPLETE
**Reviewed:** 2026-04-19

#### Data Sources Affected

- `consumable.program_career_paths` — read by the new flow via MCP `get_career_paths` for the live career preview and again inside each `crosswalk_mismatch` / `semantic_drift` / `tier_placement` chip debug trace for feasibility verification.
- `data/reference/major_to_cip.yaml` — still read by `src/mcp_server/futureproof_server.py::_handle_get_career_paths` via `_find_major_intent` for the broad-CIP substitution branch. The spec's claim that the YAML short-circuit is retired from this flow is true for `backend/app/services/intent.py::resolve_intent` but NOT true for the MCP tool the chip-routing prompt is told to call. See Concern #3.
- `data/reference/student_corrections.jsonl` — new append-only write target; becomes an in-memory read source for `community_suggestions`.
- Governance contract `governance/data-contracts/consumable-program-career-paths.yaml` — grain is `(unitid, cipcode, soc_code)` with a CHECK constraint `cipcode ~ '^\d{2}\.\d{2}$'` (4-digit XX.XX). Decision #15's invariant holds at the table level.

Zones: this spec is runtime-only; no Bronze/Silver/Gold transformations change.

#### Crosswalk Impact

The initial Gemma resolution bypasses the static crosswalk (YAML is gone from `resolve_intent` for this flow). Effective tier is Tier 4 (Gemma-estimated) for any `(school, input)` Gemma hasn't seen before, but Decision #15 asserts that the 4-digit pipeline grain collapses sub-leaf drift, so same-family Gemma drift is harmless for the career tiles. The chip debug trace re-grounds by forcing a tool call to `get_career_paths`, which effectively promotes the confidence to Tier 1-2 when the student clicks a verified candidate. The `feasibility_mode` filter (`direct_hit` / `crosswalk_quirk` / `adjacent_reachable` only) is a sound mechanism for preventing low-confidence mappings from propagating through the community signal.

One concrete crosswalk risk: the chip-routing prompt's `crosswalk_quirk` bucket assumes the tool call returns SOC codes even when the canonical mapping is "different." The current `get_career_paths` broad-CIP substitution path returns SOC sets keyed off `major_to_cip.yaml` — so a `crosswalk_quirk` classification is only as good as that YAML. Either (a) tool-calling `get_career_paths(school_reported_cipcode, student_major)` delegates to YAML substitution (acceptable, but document it), or (b) the chip prompt is supposed to tool-call without `student_major` and inspect raw crosswalk rows (changes the tool surface, not spec'd).

#### Formula Verification

The five pentagon stats and five boss scores continue to come from `consumable.program_career_paths` via MCP. No formula changes in this spec — it touches the resolution layer and the chip layer, not the stat layer. The existing contract guarantees stats stay in `[1, 10]` with explicit null handling. Effort slider still only drives ERN/ROI through `earnings_1yr_p25` / `earnings_1yr_p75`. No violation.

The live career preview resolves to `get_career_paths(unitid, cipcode=matched_cip, student_major=major_text, loan_pct=...)`. Because the MCP handler canonicalizes to 4-digit (`_canonical_cip4`) and the table is 4-digit-keyed, Decision #15's "identical tiles either way" claim holds for Gemma 6-digit drift within a family. No grain mismatch at the tile level.

#### Findings

##### Data Quality Sound

- **4-digit grain invariant (Decision #15) is real and enforced at the contract layer.** `consumable.program_career_paths` has `CHECK (cipcode ~ '^\d{2}\.\d{2}$')` in the contract and is the only table the career preview reads. Sub-leaf drift collapses correctly. This is the primary defense against Gemma hallucinating sub-specialties into the tiles, and it holds.
- **Confirmed-focus invariant (Decision #16) is well-specified for data integrity.** Student-driven sub-focus, tool-verified, mirrored back in student's own words, cleared on `semantic_drift` / `intent_divergence`. Tests P0 in §4 cover the anti-fabrication guards (`test_confirmed_focus_requires_tool_call_evidence`, `test_confirmed_focus_dropped_when_bucket_is_semantic_drift`, `test_confirmed_focus_dropped_when_bucket_is_intent_divergence`). Right shape for preventing a wrong room label from landing confidently.
- **Feasibility mode filter is the correct defense for community-signal cache.** Restricting `get_suggestions` to `direct_hit` / `crosswalk_quirk` / `adjacent_reachable` keeps `school_gap` and `genuinely_impossible` from ever reinforcing. That's the reinforcement-loop's honest boundary. The filter is the mechanism that prevents the GIGO reinforcement loop in the "what happens when a troll clicks weird stuff" case.
- **Separating `reasoning` (engineer-facing) from `display_reasoning` (student-facing)** in the `---CAREERS---` structured tail is a clean integrity primitive. Audit trail preserved; internal-taxonomy leakage prevented at the data shape, not just the prompt.
- **Correction log is explicitly append-only.** Threading lock mentioned, `record_correction` documented to never raise, first-run creates the parent directory. Correct discipline for a data log next to commit.

##### Data Concerns

- **Concern 1 (Significant): `input_normalized` normalization rule is undefined.** The schema names it "student's normalized query — cache key" but never specifies the normalization function. Is it `.strip().lower()`? Does it collapse whitespace? Does it strip punctuation? Unicode-normalize (NFC / NFKC)? Does "Marketing", "marketing", "Marketing " and "marketing " all collapse to the same bucket? This matters a lot — the community-suggestions surface is keyed on it, and at count >= 1 a single misnormalization splits or merges signals incorrectly. **Risk:** a student types "Marketing " with a trailing space, sees no community signal; another student types "marketing" and writes to a separate key; the surface appears empty when it shouldn't. Inversely, "nursing" and "Nursing (RN)" collapse to the same bucket and one swamps the other. **Fix:** add a concrete normalization spec in §4: pin exact transformation (suggested baseline: `" ".join(unicodedata.normalize("NFKC", raw).strip().lower().split())`), state punctuation handling (suggest: preserve, don't strip — "UX/UI" and "UX UI" are not the same intent), state that typo-correction is out-of-scope. Same function must be used by the writer (`record_correction`), the reader (`get_suggestions`), AND the chip dispatcher's `current_state`. One shared helper, imported.

- **Concern 2 (Significant): Silent 6→4 digit truncation.** The chip-routing prompt's `---UPDATED_RESOLUTION---` tail emits `"matched_cip": "XX.XXXX"` (6-digit per the prompt's own spec). The existing `IntentResult` carries 6-digit `matched_cip` (via `_promote_to_leaf_cip`). But `CorrectionLogRecord` stores `initial_cip4: str` and `final_cip4: str` — 4-digit. Nowhere in §4 is the truncation function specified. **Risk:** one engineer writes `matched_cip` directly into `initial_cip4`, storing "52.1401" where downstream code expects "52.14", and `community_suggestions.get_suggestions` groups inconsistently (some rows 6-digit, some 4-digit → split signal → the feature looks broken at count threshold). **Fix:** add an explicit truncation contract in §4: "Before writing to the correction log, `matched_cip` is truncated to 4-digit via `matched_cip[:5]` after a regex check that it conforms to `^\d{2}\.\d{4}$`. If already 4-digit, pass through. If malformed, skip the write and log a warning." Also state `clicked_soc` is the raw SOC from the MCP response (XX-XXXX), no transformation.

- **Concern 3 (Significant): Chip-flow tool-calling still depends on `major_to_cip.yaml` through the MCP layer.** Literal reading: `resolve_intent` in the new flow doesn't call `major_lookup.lookup_major`. But the chip-routing prompt calls `get_career_paths` with tool arguments including the student's typed major — and `_handle_get_career_paths` at `src/mcp_server/futureproof_server.py:2080` still calls `_find_major_intent`, which loads `major_to_cip.yaml`. The broad-CIP substitution branch fires when the school reports a broad CIP. **Risk:** the chip debug trace's feasibility classification can silently inherit a YAML decision — e.g. a `crosswalk_quirk` label on a career the student clicks comes from the YAML substitution, not from raw crosswalk reasoning. Community suggestions then cache a classification whose grounding is the very static lookup the spec claims is gone. Contradicts Decision #4's narrative and the Kaggle demo story ("No static lookup. Gemma reasons and tool-calls live"). **Fix:** add explicit language in §4 — either (a) the chip flow must NOT pass `student_major` to `get_career_paths` (bypassing the substitution branch entirely; relies on raw crosswalk behind the tool), or (b) acknowledge that substitution via YAML is still in the loop at the MCP layer and document it honestly in §10 as transitional. Option (a) is cleaner for the demo. Either way, the current spec is silent on it.

- **Concern 4 (Significant): `clicked_soc` null handling in the aggregation rule.** §4 says aggregation groups by `(school_unitid, input_normalized, clicked_soc)` and filters where `feasibility_mode IN (direct_hit, crosswalk_quirk, adjacent_reachable)`. But `clicked_soc` is `str | None` — null for chips that didn't surface a career. And `feasibility_mode` is `FeasibilityMode | None`. **Risk:** null-null-null groups become a "ghost suggestion" bucket that never surfaces (filter drops it, good) but also pollutes the aggregation index memory with phantom keys. More subtly: nothing in the Pydantic / TypedDict model forbids a row with `clicked_soc=None` AND `feasibility_mode != None` — if that slips through, the aggregator would count a row whose SOC is missing, producing a suggestion card with null career title. **Fix:** add a precondition in `record_correction` — refuse (or skip) a row where `feasibility_mode IS NOT NULL AND clicked_soc IS NULL`. And state in §4 that `get_suggestions` filters `clicked_soc IS NOT NULL AND clicked_career_title IS NOT NULL` explicitly before grouping.

- **Concern 5 (Significant): `meme_redirect` appears in the student-facing pill mapping but NOT in the 5-mode `FeasibilityMode` literal.** §4 defines `FeasibilityMode = Literal["direct_hit", "crosswalk_quirk", "adjacent_reachable", "school_gap", "genuinely_impossible"]` — five modes. The Feasibility Classification table lists the same five. But the Student-facing pill labels table has SIX rows — it adds `meme_redirect` with the note "NEVER surfaced as a pill". **Risk:** ambiguity for the implementer. Either (a) `meme_redirect` is a 6th internal mode that should appear in the Literal + correction log, or (b) it's a leftover that should be deleted from the pill table. If (a), the classification is really 6 modes and the review headline ("5-mode feasibility") is misleading; if (b), the table is stale. **Fix:** pick one. If dropping, remove the row; if keeping, add it to the Literal (cacheable: No), update the Feasibility Classification table, and add a test that verifies a `meme_redirect`-tagged row does NOT count toward community suggestions.

- **Concern 6 (Significant): Community threshold of 1 is a data-quality trap, not just a privacy-lite setting.** Founder approved count >= 1 on the "we don't track who the student is" rationale, which addresses the surveillance concern. It does NOT address the data-quality concern. At threshold 1, a single student's click — possibly the first student ever to hit this `(school, input)` combo, possibly a judge typing anything — surfaces as "Other students searching X at Y ended up here:" to every subsequent visitor. There's no way to distinguish a pioneer signal from a noise signal. **Risk:** the product's most visible social-proof surface displays "other students" authority for what is in fact n=1 — a 17-year-old reads "other students" as plural, which is materially misleading at count=1. And because the correction log is committed to git, a sloppy initial pass by any dev or QA pollutes the demo build's suggestions for every beta tester. **Fix:** two options, at least one required. (a) Raise the default to count >= 2 for the hackathon too; pioneer still gets to pioneer (their click is logged; the second student triggers surfacing). `COMMUNITY_MIN_COUNT=2` as hackathon default; post-hackathon raise to 3. (b) Keep count >= 1 but change the surface copy from "Other students searching ... ended up here:" to a truthful-at-n=1 variant, e.g. "Someone else searching 'marketing' at IU picked this:" when count == 1, and pluralize only at count >= 2. Document which in §4. **Also:** the correction log being committed to git means test-run and demo-prep clicks pollute the production demo. Add a step to §4: before merging to main, truncate `data/reference/student_corrections.jsonl` to ship with zero entries (or a curated seed set if founder wants). Otherwise the demo opens with stale clicks.

- **Concern 7 (Minor): Feasibility mode never applies to the initial resolution.** The log records the mode the chip-routing Gemma assigned to the *clicked* career. The initial resolution itself (what Gemma said first, before any chip tap) never gets a feasibility mode — the student may commit directly and that row logs `clicked_soc=null, feasibility_mode=null`. That's fine under Concern 4's proposed filter, but worth a note in §4 that initial-resolution commits are not community signal, only chip-debug-clicked commits are.

- **Concern 8 (Minor): `initial_cip4` when a student uses Community Suggestions.** Success Criteria line 152 says clicking a community suggestion "swaps the current resolution to the clicked career's canonical CIP and appends a new correction record (increments the count)". The new record's `initial_cip4` is — what? The CIP that Gemma resolved *this* session, or the CIP that was the initial at the moment the community signal was first cached? The schema's description `initial_cip4: str — what Gemma resolved first` reads as this-session's initial. Fine, but document it: "`initial_cip4` is always this session's initial Gemma resolution, regardless of whether the student accepted a community suggestion."

- **Concern 9 (Minor): No DQ budget on correction log volume.** The spec commits the log to git on every write. For a 29-day hackathon with internal dev testing, fine. For any external-audience exposure (blocked by guardrails spec, acknowledged), volume will grow quickly and every click becomes a git commit. Add a TODO in §10 pointing at a v2 compaction strategy — or note explicitly that `data/reference/student_corrections.jsonl` is wiped pre-demo per Concern 6's fix.

- **Concern 10 (Minor): `CorrectionLogRecord` schema lacks a `schema_version` field.** The log is committed to git; v2 will read it. Any field change after ship requires the reader to tolerate mixed shapes. Add `schema_version: str = "1.0"` as the first field so future readers can dispatch on shape.

##### Data Integrity Blockers

None that reject. Concern 1 is severe enough on its own to warrant CHANGES REQUESTED (a spec that doesn't define its cache key can't be implemented correctly); Concerns 2, 3, 4, 5, 6 compound the same theme — the spec is solid on the Gemma reasoning story but loose on the data-shape contracts around the community-signal layer.

#### Disclaimer Check

- [x] AI-estimated values labeled — Gemma resolutions are implicitly AI-estimated (the whole flow shows Gemma reasoning on-screen) and the student-facing pill taxonomy translates internal modes to student-legible copy (`"Direct match"`, `"Through [Business] program"`, etc.).
- [ ] Confidence scores propagated where crosswalk < Tier 2 — partially. `IntentResult.confidence` flows through to the soft-nudge on commit (Decision #10), but the community-suggestions surface itself shows no confidence signal. A suggestion at count=1 with `feasibility_mode=adjacent_reachable` reads to the student as equally authoritative as a count=17 `direct_hit`. **Fix:** surface the count visibly next to each suggestion (the mockup already does this — "(17 students)" — keep it), AND surface the mode pill consistent with the pill-label table.
- [x] Required disclaimer strings present in UI — consent-of-loop disclosure under the chip rail is documented (Success Criteria line 146). Voice guide owns final wording.
- [ ] Missing data states handled — the chip-routing `no_issue_found` bucket gives an honest "these just aren't resonating" response instead of a dead-end spinner. The empty-suggestions surface ("The section is absent entirely when no suggestions exist") is also correct. Remaining gap: there's no explicit handling for the degenerate case where the JSONL file exists but is corrupt (malformed JSON on line N). **Fix:** `community_suggestions.rebuild()` must skip malformed lines with a warning, not crash the app on startup. Add a P0 test: `test_corrupt_jsonl_line_is_skipped_on_rebuild`.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

**Rationale:** The spec's story — 4-digit grain invariant + student-driven sub-focus + feasibility-mode-filtered community signal — is the right shape for data integrity. The Gemma reasoning layer is well-scoped and the filter on cacheable modes is exactly the mechanism that prevents garbage-in-garbage-out reinforcement. But the data-shape contracts around the community-signal surface have specification gaps that will produce silent data-quality failures in implementation:

1. Pin `input_normalized` normalization function in §4 (Concern 1).
2. Explicit 6→4 digit truncation contract for `matched_cip → initial_cip4`/`final_cip4` in §4 (Concern 2).
3. State the chip flow's relationship to `major_to_cip.yaml` via MCP's substitution branch — bypass or acknowledge (Concern 3).
4. `clicked_soc` null-safety precondition in `record_correction` and filter in `get_suggestions` (Concern 4).
5. Resolve `meme_redirect` ambiguity (Concern 5).
6. Raise hackathon `COMMUNITY_MIN_COUNT` default to 2 OR pluralize copy conditionally at n=1, plus a pre-demo log-truncation step (Concern 6).
7. Add `schema_version: str` to `CorrectionLogRecord` (Concern 10).
8. Add corrupt-line-tolerance to `community_suggestions.rebuild()` with a P0 test (Disclaimer Check).

Concerns 7, 8, 9 are minor clarifications; bundle with the §4 edit pass.

These are spec-edit-level fixes, not architecture changes. A focused pass on §4 addresses them. Once §4 carries the normalization rule, the truncation contract, the YAML-in-MCP acknowledgment, the null-safety precondition, the `meme_redirect` resolution, and either the raised threshold or conditional copy, this is APPROVED.

### @genai-architect Review (ad-hoc)
**Status:** COMPLETE
#### Findings

**Scope:** §1–§4 for Gemma/LLM architecture. Reviewed against `backend/app/services/intent.py`, `backend/app/services/career_pick_qna.py`, and `backend/app/services/gemma_client.py` as live reference implementations.

---

**1. `_CHIP_ROUTING_SYSTEM_PROMPT` — 8-bucket taxonomy and structured tails**

The taxonomy is sound and the bucket list covers the realistic failure space. Findings by area:

*Bucket coverage.* Seven named failure buckets plus `no_issue_found` is the right size — small enough that Gemma can discriminate reliably at temp=0.2, large enough to route every real student complaint. The IU-Marketing worked example inside `crosswalk_mismatch` is exactly right: a concrete exemplar dramatically reduces Gemma's tendency to generalize loosely when classifying. Every other bucket should similarly carry at least one inline example before implementation. Currently only `crosswalk_mismatch` has one. The remaining six buckets receive abstract definitions only. At temp=0.2 with a single-shot classification task, an abstract definition without an example raises the ambiguity-collapse risk (Gemma picks the first bucket that fits any interpretation, rather than the best-fitting one). **Required before implementation: add one concrete one-liner example per bucket**, matching the pattern already used for `crosswalk_mismatch`. These examples are not shown to students and carry no leakage risk.

*Tail parsing fragility.* Three optional structured tails (`---UPDATED_RESOLUTION---`, `---BUCKET---`, `---CONFIRMED_FOCUS---`) are parsed by the service from a freeform streamed string. `---BUCKET---` is described as "always present" in the spec but the prompt says "Always append the classification tail" — these must be consistent in the implementation's parser. The parsing logic must handle: (a) tail markers appearing inside a code block Gemma decides to emit, (b) whitespace variants (`--- BUCKET ---`, `---BUCKET ---`), (c) the tails arriving in a different order than specified, (d) the JSON inside a tail being malformed. The existing `_call_gemma_intent` in `intent.py` shows a battle-tested pattern (rfind `}`, strip markdown fences) — the tail parser should copy the same defensive extraction approach, applied once per delimiter. The test `test_malformed_tails_are_ignored_no_crash` is P0 correct, but the test data requirements section should specify that malformed-tail fixtures cover each of the four failure modes above. **Required: explicit test fixtures for (a)–(d) before the P0 test is written.**

*`---BUCKET---` omission when bucket is null for non-Gemma chips.* The spec says `bucket` is `None` for `show_less_common` and `change_major`. The prompt instructs "Always append the classification tail." This creates an untested code path: the parser receives no `---BUCKET---` marker for two of the three chip IDs. The service must handle a missing `---BUCKET---` gracefully (return `bucket=None`, not raise). The current test suite has P0 coverage for `test_show_less_common_skips_gemma` and `test_wrong_major_skips_gemma` — those confirm no Gemma call fires, but they do not confirm that `bucket=None` propagates correctly in the `ChipResponse`. **Required: add an assertion on `response.bucket is None` to both skips-Gemma tests.**

*Voice rules — taxonomy leakage.* The prohibition on CIP/SOC/crosswalk/numeric codes in `display_reasoning` is clearly stated and backed by the separate `reasoning` (engineer-facing) / `display_reasoning` (student-facing) field split in the `---CAREERS---` tail. This is the right architecture. One gap: the prompt instructs the rule in the Rules section but the structured tail format in the Response Format section does not repeat the prohibition for `display_reasoning`. Gemma is more reliable at following a rule when the rule is restated at the point of application. **Recommended (not blocking): add a one-line reminder inside the `---CAREERS---` tail format description — e.g. `"display_reasoning": "student-facing, no CIP/SOC/crosswalk terms"` in the JSON template.**

*Source citation rules.* The acronym-spell-out rule (full name + parenthetical acronym on first reference per rendered view; abbreviated thereafter) is correct and well-specified. The `{sources_for_prompt_context}` placeholder references `feature-receipts.md` — this variable must be populated at call time with the canonical source registry before the prompt is issued to Gemma. The current `_call_gemma_intent` pattern does not populate such a variable; the `set_your_course.py` service must explicitly inject it. **Required: define the `sources_for_prompt_context` string (or a minimal subset: BLS, IPEDS, O*NET, BEA, College Scorecard) and interpolate it into the prompt before the first chip call. Leaving `{sources_for_prompt_context}` unreplaced in the prompt will cause a Python `KeyError` or a literal `{sources_for_prompt_context}` string sent to Gemma.**

*`no_issue_found` handling.* The fallback copy ("These just aren't resonating — totally fair. You can try a different major or continue with what you have.") is good. The rule "do NOT force a bucket" is slightly contradictory: the prompt tells Gemma to classify into one of 8 buckets, but `no_issue_found` is itself the bucket for unclassifiable cases. The instruction should read "classify as `no_issue_found` when no bucket fits" to avoid Gemma attempting to force-fit a real bucket. **Recommended: revise the `no_issue_found` description to say "classify as `no_issue_found`" explicitly rather than "do NOT force a bucket."**

---

**2. Streaming response shape**

The spec raises SSE vs chunked JSON fetch as an open question. **Recommendation: use SSE (Server-Sent Events) via FastAPI's `StreamingResponse` with `media_type="text/event-stream"`.**

Rationale:

- FastAPI has native SSE support via `StreamingResponse` and `EventSourceResponse` (starlette-sse). No new dependencies.
- The OpenAI Python SDK's streaming API (`client.chat.completions.create(stream=True)`) yields `ChatCompletionChunk` objects. Converting each delta to an SSE `data:` line is three lines of code and directly mirrors the existing `generate_chat` path — the async generator wraps the sync SDK call via `asyncio.to_thread` in a `generate_stream_async` function, yielding string deltas.
- React's `EventSource` API or the `fetch` + `ReadableStream` pattern both consume SSE without a library. The existing `AbortController` cancel semantics work identically — `AbortController.signal` passed to `fetch()` aborts the SSE connection mid-stream.
- Chunked JSON (ndjson) is viable but requires the frontend to maintain a partial-line buffer and handle split chunks at line boundaries, which is boilerplate SSE already handles.
- Both Ollama and OpenRouter support the OpenAI streaming protocol. Config-switching remains a backend concern only; the frontend SSE consumer is backend-agnostic.

**Implementation note for `gemma_client.generate_stream_async`:** the current `generate_async` runs the sync `generate` in a thread via `asyncio.to_thread`. The streaming variant cannot use this pattern because the streaming iterator lives in a sync context but must yield to the async caller. The correct pattern is: acquire the semaphore, open the sync streaming completion inside `asyncio.to_thread` as a generator, and then `yield` each delta in the async generator. A simpler alternative is to use `openai.AsyncOpenAI` for the streaming path only, which provides a native async streaming iterator and avoids the thread-handoff complexity. Given the codebase already uses `OpenAI` (sync) client everywhere, the cleanest low-risk path is: keep the sync `OpenAI` client for non-streaming calls, add `AsyncOpenAI` (same credentials, lazy-constructed) for the streaming endpoint only. This avoids introducing thread-wakeup latency into a latency-sensitive streaming path.

**SSE event format for the chip debug trace:** the service should emit two event types:
- `event: delta\ndata: <token text>\n\n` — prose chunks as they arrive
- `event: structured\ndata: <JSON with bucket, updated_resolution, confirmed_focus>\n\n` — the parsed tails, emitted once after the full response is received

This keeps the frontend SSE consumer simple: accumulate `delta` events into the displayed prose; apply `structured` event fields to the store once. The structured tails are extracted server-side from the completed response, not streamed mid-token. This is the cleanest separation between the streaming prose surface (student-visible) and the structured resolution update (state mutation).

**For the initial resolution stream** (`POST /intent/stream`): the existing `_INTENT_SYSTEM_PROMPT` does not produce structured tails — it outputs JSON. Streaming a JSON response token-by-token is not useful for displaying to the student. The initial resolution stream should not attempt to stream the JSON reasoning field. Instead, `stream_initial_resolution` should: (1) emit SSE deltas for any prose the resolution generates (a brief "resolving..." or the `reasoning` field streamed as prose), (2) emit one `structured` event at the end with the full `IntentResult`. If the resolution is fast enough that streaming adds no visible benefit, a non-streaming response with a progressive skeleton UI is acceptable for the initial resolution — streaming is most valuable for the chip debug trace, which is where Gemma generates the most prose.

---

**3. Conversation context threading**

The stateless design is correct and sufficient. Each chip tap sends `(chip_id, clarifier, current_resolution, initial_resolution, school_name, unitid, programs)` as a single POST body. No session ID, no conversation array, no turn counter. This is the right architecture for this surface.

What is sufficient in this payload:
- `current_resolution` gives Gemma the active CIP and confidence so it knows what state to reason about.
- `initial_resolution` lets the prompt surface whether the student has already been corrected once (current ≠ initial implies a prior correction happened). The prompt currently does not use this signal explicitly — it is present in the state but the prompt does not instruct Gemma to acknowledge that the student already corrected once. This is fine for v1; the signal is there if the prompt writer wants it later.
- `programs` (the school's reported CIP list) gives the chip routing prompt the school catalog context it needs to classify `crosswalk_mismatch` vs `school_gap` without an additional tool call.

One field is missing: **`clarifier` should be required (not optional) when `chip_id == "not_expected"`, and the Pydantic model should enforce this.** The spec's test `test_not_expected_without_clarifier_422` confirms this should return 422, which means the validator must enforce it — but the current `ChipRequest` model has `clarifier: str | None` unconditionally. The enforcement belongs either in a Pydantic `model_validator` or in the router handler before calling the service. **Required: enforce that `chip_id="not_expected"` + `clarifier is None` is a 422 at the Pydantic layer, not a service-layer runtime error.**

One minor omission: `ChipRequest` does not carry a `confirmed_focus` field for the current resolution's already-verified sub-specialty. If the student has already confirmed a sub-specialty (from a prior chip tap) and then taps the chip again with a new clarifier, Gemma will not know the prior `confirmed_focus` is set — it will start reasoning without that context. In the no-multi-turn model, the prior `confirmed_focus` lives on `current_resolution.confirmed_focus` (which IS sent). **Verify that the prompt template interpolates `current_resolution.confirmed_focus` into the prompt context when it is set, so Gemma knows not to re-verify an already-confirmed sub-specialty.** The current prompt template variables in the spec show `{current_cip4}`, `{current_title}`, `{current_confidence}` — `{current_confirmed_focus}` is not listed. **Required: add `confirmed_focus` to the prompt template variables and interpolate it into the current-state section of the prompt.**

---

**4. How corrections modify the resolved CIP and `confirmed_focus` semantics**

The `---UPDATED_RESOLUTION---` → CIP swap logic is structurally correct. The `confirmed_focus` drop rule (if bucket is `semantic_drift` or `intent_divergence`, drop `confirmed_focus`) is also correct in principle.

However, the enforcement point is ambiguous. The spec says "logic: if bucket is `semantic_drift` or `intent_divergence`, `confirmed_focus` must be dropped" — but where does this drop happen? The prompt instructs Gemma to omit the `---CONFIRMED_FOCUS---` tail in those cases ("Omit the `---CONFIRMED_FOCUS---` tail entirely if... the clarifier routed to semantic_drift / intent_divergence"). This is not a sufficient control: Gemma at temp=0.2 can and will occasionally emit a `---CONFIRMED_FOCUS---` tail even when the prompt says to omit it, especially if the clarifier names a compelling sub-specialty. **The service layer MUST enforce the drop rule, not rely on Gemma obeying it.** The test `test_confirmed_focus_dropped_when_bucket_is_semantic_drift` correctly specifies this, but the implementation must wire it: parse the bucket first, then conditionally discard `confirmed_focus` regardless of whether the tail is present. This is a one-liner in the parsing logic but it must be explicit.

Similarly, the anti-fabrication guard — `test_confirmed_focus_requires_tool_call_evidence` — is a P0 test that verifies the service strips `confirmed_focus` when no tool call was made. This requires the service to track whether at least one tool call occurred during the chip run. **Required: the service must maintain a boolean `tool_call_made` flag during the chip dispatch, and `confirmed_focus` must be stripped if `tool_call_made is False`, regardless of what the tail says.**

One additional edge case not covered by the spec: if the bucket is `crosswalk_mismatch` (which does change the effective career mapping but not necessarily the 4-digit CIP), and the student's clarifier also names a sub-specialty, is `confirmed_focus` valid? The spec is silent on this. `crosswalk_mismatch` does not change the matched CIP — only `semantic_drift` / `intent_divergence` do. Therefore, `confirmed_focus` should remain valid for `crosswalk_mismatch`. The drop rule is correctly scoped to the two CIP-changing buckets only. **No spec change needed; noting for the implementer so the `if bucket in ("semantic_drift", "intent_divergence")` check is not accidentally widened.**

The numeric-code stripping test (`test_confirmed_focus_strips_numeric_codes`, P1) is a correct defense-in-depth measure. The service should apply a regex like `r'\s*\(\d{2}\.\d{4}\)'` to strip parenthetical CIP sub-leaf codes from `confirmed_focus` before returning.

---

**5. Tool-calling loop — recommendation**

**Recommendation: pre-fetch with function-call definitions, single generation, service-side execution.** Do NOT implement a multi-step "Gemma proposes, service executes, Gemma continues" loop.

Rationale:

Gemma 4's function-calling on Ollama is functional but not robust at multi-step tool-use chains (the model was not RLHF'd for agentic tool loops the way GPT-4o or Claude 3.5 are). In practice on Ollama, multi-step tool use with a mid-generation interrupt, tool result injection, and resume frequently produces: (a) repeated tool calls to the same function, (b) incomplete JSON tool call arguments, (c) premature stop before the second generation. These failure modes compound when the model is also streaming.

The pre-fetch pattern is more reliable and keeps the demo headline: Gemma tool-calls are visible to the student through the streamed reasoning, even if the actual data fetch is a service-side pre-call. The pattern:

1. The service inspects the `chip_id` and bucket classification to determine which tool calls will likely be needed (e.g., `crosswalk_mismatch` needs `get_career_paths`, `peer_variance` needs 2–3 school queries, `tier_placement` needs no tool call).
2. The service pre-fetches the relevant tool results before issuing the Gemma call.
3. The Gemma prompt includes the pre-fetched data inline (as context), and the function call definitions are still provided in the `tools` parameter so Gemma can request additional data if it decides it needs something the service did not pre-fetch.
4. If Gemma issues an additional tool call during generation (OpenAI `finish_reason == "tool_calls"`), the service executes it (retry-once on failure), injects the result, and resumes. This is a depth-1 tool loop, not an unbounded one.

This approach gives the demo the genuine tool-calling appearance (Gemma's reasoning cites the data it retrieved), keeps the implementation tractable (depth-1 loop, one retry), and does not require Ollama's multi-step function-calling to work reliably.

**Required spec addition (minor):** document the pre-fetch dispatch table — which buckets pre-fetch which tools — so the implementer does not have to infer it. Suggested table:

| Bucket | Pre-fetch | Gemma additional tool call permitted |
|--------|-----------|--------------------------------------|
| `crosswalk_mismatch` | `get_career_paths(unitid, school_cip)` | Yes (depth-1) |
| `semantic_drift` | `get_career_paths(unitid, inferred_cip)` | Yes (depth-1) |
| `school_gap` | `get_school_programs(unitid)` | No (school catalog already in prompt) |
| `data_suppression` | None | No |
| `tier_placement` | None | No |
| `intent_divergence` | `get_career_paths(unitid, clarifier_cip)` | Yes (depth-1) |
| `peer_variance` | `get_career_paths` × 2–3 peers | No |
| `no_issue_found` | None | No |

Note: `school_gap` pre-fetch cannot be done before bucket classification (chicken-and-egg). For `school_gap`, the service should issue the school catalog query inline as a tool call result injected after the first Gemma response confirms the bucket. This is the one bucket where a single depth-1 additional tool call is necessary — document it as an exception.

---

**6. Fallback behavior**

The specified fallbacks are appropriate for a hackathon build. Two observations:

*Transport failure fallback.* "I'm having trouble reaching the model. Try again in a moment." is correct. The critical invariant — resolution is NOT modified on transport failure — is clearly stated and correct. The logging requirement (log as usual to `gemma.jsonl`) ensures the failure is observable. No change needed.

*Tool-call failure fallback.* "Retry exactly once, then note the miss in prose" is correct. One implementation note: the "noting the miss" prose must not expose internal tool names (`get_career_paths`) to the student — it should say something like "I couldn't pull the full career list for this school" rather than "the get_career_paths tool call failed." The current spec's example wording ("I couldn't pull the full career list — here's what I can confirm:") is already correct. **Required: the implementer must NOT interpolate the raw tool name into any student-facing string.**

---

**Required changes summary (blocking):**

1. Add one concrete inline example per bucket (7 additions to the `_CHIP_ROUTING_SYSTEM_PROMPT`).
2. Populate `{sources_for_prompt_context}` with the canonical source registry before the prompt is issued — or replace the placeholder with the inline text. A `KeyError` here will silently corrupt the prompt string.
3. Enforce `chip_id="not_expected"` + `clarifier is None` = 422 at the Pydantic model-validator layer.
4. Add `{current_confirmed_focus}` to the chip routing prompt template variables and interpolate it into the current-state block.
5. Service layer must drop `confirmed_focus` when `bucket in ("semantic_drift", "intent_divergence")`, regardless of prompt compliance.
6. Service layer must track `tool_call_made` and strip `confirmed_focus` if no tool call occurred during the chip run.
7. Add assertions on `response.bucket is None` to `test_show_less_common_skips_gemma` and `test_wrong_major_skips_gemma`.
8. Add explicit test fixtures for the four tail-parsing failure modes: (a) tail inside code block, (b) whitespace variants, (c) out-of-order tails, (d) malformed JSON inside a tail.
9. Document the pre-fetch dispatch table in §4 (bucket → pre-fetch tool mapping).
10. Add the `school_gap` depth-1 exception to the tool-calling loop documentation.

**Recommended changes (non-blocking):**

- Revise `no_issue_found` description to say "classify as `no_issue_found`" explicitly.
- Add `"display_reasoning": "student-facing, no CIP/SOC/crosswalk terms"` annotation to the `---CAREERS---` tail JSON template.
- Use `AsyncOpenAI` client for the streaming path only; keep sync `OpenAI` for non-streaming.
- Emit two SSE event types: `delta` (prose chunks) and `structured` (parsed tails, once at end).
- Consider whether `stream_initial_resolution` should stream at all, or return synchronously with a skeleton-UI treatment given the JSON-only output of `_INTENT_SYSTEM_PROMPT`.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

*Ten required changes listed above, all in the implementation and prompt specification layer — no architectural blocker. Implementation should not begin until items 1–10 are addressed in the spec's §4 service section and/or the prompt body. Items 7–8 can be addressed in the test spec (§7) rather than §4.*

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
**Status:** COMPLETE

#### Audit

## SetYourCourseScreen.tsx

### PASS
- Background, card, and surface colors use `bg-bp-*` tokens throughout (`bg-bp-mid`, `bg-bp-surface`). No hex literals.
- Text classes use `text-text-primary`, `text-text-secondary`, `text-text-muted`, `text-accent-alert`, `text-accent-caution`, `text-accent-insight` — all correct Brightpath tokens.
- Typography uses `font-display`, `font-body`, `font-data`; size tokens `text-display`, `text-subheading`, `text-body`, `text-body-sm`, `text-micro`, `text-small` — matches DESIGN.md scale.
- Major input at line 253: focus state uses `focus:border-accent-info focus:shadow-[0_0_0_3px_var(--color-focus-ring)] focus:outline-none` — correct per DESIGN.md Input focus spec.
- Border tokens: `border-border-subtle`, `border-border` — correct.
- Buttons use `<Button variant="primary|ghost">` — correct, no ad-hoc `<button>` styling for CTAs.
- Spring motion: `transition={springs.smooth}` used on section entrance animations (lines 241, 299, 433) — correct token.
- Mobile sticky bar uses `bg-bp-mid/95` — acceptable opacity modifier on a token.

### FAIL
- **Hardcoded CSS transition duration on streaming div**: `transition={{ duration: 0.2 }}` at line 267. DESIGN.md §Motion specifies all meaningful animations must use Framer Motion spring physics from `@/styles/motion`, not raw `duration` tweens. Expected: `transition={springs.smooth}` or `transitions.fade` (which is a defined preset in `motion.ts` for opacity-only fades). Found: `{ duration: 0.2 }`.
- **Hardcoded overlay color**: `bg-black/70` at line 505 (start-over confirm dialog backdrop). DESIGN.md §Color defines no `black` token — backgrounds use `bg-bp-void` (`#12131F`) as the deepest canvas. Expected: `bg-bp-void/70` or a token-mapped scrim. Found: Tailwind `black` (literal `#000000`), which is outside the Brightpath color set.

### WARNINGS
- `pb-[calc(var(--space-6)+96px)]` at line 206 is an arbitrary calc value for the sticky-bar offset. DESIGN.md §Spacing defines a 4px-base scale; 96px is not a named token. This is a layout-arithmetic edge case — acceptable if the 96px hard-codes the sticky bar height. Not a blocking violation but should be documented as a known deviation.

---

## CorrectionChips.tsx

### PASS
- All `<Button>` variants used correctly: `variant="primary"` for "Not what I expected", `variant="ghost"` for the two secondary chips — matches DESIGN.md chip rail spec (prominent primary + ghost secondaries).
- Clarifier textarea focus state at line 120: `focus:border-accent-info focus:shadow-[0_0_0_3px_var(--color-focus-ring)] focus:outline-none` — correct per DESIGN.md Input focus spec.
- Clarifier label uses `font-data text-micro uppercase tracking-[2px] text-text-muted` — correct token set.
- Consent-of-loop disclosure uses `font-body text-small text-text-muted border-t border-border-subtle pt-3` — correct tokens.
- Motion expansion uses `transition={springs.smooth}` — correct token.
- Container uses `bg-bp-surface`, `border-border-subtle`, `rounded-xl` — correct tokens.

### FAIL
- None.

### WARNINGS
- None.

---

## CommunitySuggestions.tsx

### PASS
- Container: `bg-bp-mid`, `border-border-subtle`, `rounded-xl` — correct.
- Suggestion button focus state at line 63: `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)]` — correct DESIGN.md focus-visible convention.
- Hover states: `hover:bg-bp-raised hover:border-border` — correct token progression.
- Typography: `font-body text-body font-semibold text-text-primary`, `font-data text-small text-text-muted` — correct.
- Motion: `stagger.normal` from `@/styles/motion`, `springs.smooth` for item transitions — correct tokens.
- Transition: `transition-colors duration-normal` — uses the `duration-normal` CSS token, correct per DESIGN.md.

### FAIL
- None.

### WARNINGS
- None.

---

## useSetYourCourse.ts

No visual code, no inline styles. Confirms clean — skip per audit instructions.

---

## MenuScreen.tsx (new additions only)

### PASS
- New `handleNewBuildSetCourse` handler and `<Button variant="secondary">Try the new flow ✦</Button>` buttons (lines 202–208, 261–267) use the `<Button>` component with `variant="secondary"` — correct for a secondary CTA per DESIGN.md.
- Motion: `transition={springs.smooth}`, `stagger.normal` — correct tokens, unchanged from existing Menu patterns.
- `✦` glyph usage on "Try the new flow ✦" and "New Build ✦" buttons is consistent with the existing `✦` used on `BuildCard` and the FutureProof wordmark (`U+2726`). DESIGN.md sanctions this glyph as the Gemma-star motif — usage is on-brand.

### FAIL
- None.

### WARNINGS
- `transition={{ duration: 0.25 }}` at line 152 (compare-mode enter/exit). This is pre-existing code, not added by this spec — flagged as a warning only since the audit scope is new additions. Existing code carries the same pattern.

---

## frontend/src/api/intent.ts

Non-visual; no markup, no inline styles. Clean per audit scope.

---

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] BLOCKER

**Two changes required before merge:**

1. `SetYourCourseScreen.tsx` line 267 — replace `transition={{ duration: 0.2 }}` with `transition={springs.smooth}` (import already present) or `transitions.fade` from `@/styles/motion`.
2. `SetYourCourseScreen.tsx` line 505 — replace `bg-black/70` with `bg-bp-void/70` to stay within the Brightpath color set.

Both are single-line fixes. No other token violations found.

### Code Review (@faang-staff-engineer)
**Status:** COMPLETE
*Reviewer: Staff Engineer (15 YOE, production incident survivor). Date: 2026-04-19.*

#### Summary
Look, I love Claude, BUT — I went in expecting three outages worth of landmines and came out with a short list. The streaming plumbing is actually correct (TextDecoder + `\n\n` re-buffering handles TCP fragmentation properly, unlike 90% of SSE parsers I've reviewed). Semaphore discipline extends to the new stream path. SQL is `int()`-cast-safe. The Pydantic validator does produce a 422. Not ready to ship without one serious fix, but nothing structural.

#### Findings

**🟠 Serious — thread + semaphore leak on client abort in `generate_stream_async`**
`backend/app/services/gemma_client.py:452–472`. When the client aborts mid-stream, the async side exits the `while` via `finally` and `await task` — but `_drain_sync` is still iterating the OpenAI HTTP stream and blocking on `q.put(...)` into a bounded (256) queue nobody is draining. Once the queue fills, the executor thread stalls until the HTTP socket times out, holding both an executor slot AND the `asyncio.Semaphore`. Under a reasonable abort cadence you exhaust the default ThreadPoolExecutor and `generate_async` begins blocking across the whole app. Fix: capture the stream return value on a shared ref and call `stream.close()` from the async `finally` (or drain the queue to `_DONE`) so `_drain_sync` exits promptly on cancel.

**🟡 Moderate — `community_suggestions` aggregate has no external-edit detection**
`backend/app/services/community_suggestions.py:159–203`. The aggregate is rebuilt from disk once per process; after that only in-process writes refresh it. If anyone edits `student_corrections.jsonl` externally (teammate commit, hand-correction, multi-worker uvicorn), the API lies until restart. Fix: stat the file's `mtime` in `_ensure_initialized`/`get_suggestions` and rebuild when it moves. Cheap (~µs), closes a predictable foot-gun.

**🟡 Moderate — cross-process write safety on `student_corrections.jsonl`**
`backend/app/services/correction_log.py:92`. The `threading.Lock` serializes writers in one process; uvicorn `--workers N` or a parallel CLI commit bypasses it entirely. POSIX `write()` atomicity only holds up to PIPE_BUF (512B on macOS); records are larger. Fix: `fcntl.flock(fh, LOCK_EX)` under the open, or document acceptance in §2. `_coerce_record` already tolerates corrupt lines, so blast radius is "one lost correction" — still worth calling out.

**🟡 Moderate — SSE `data:` parser strips significant whitespace**
`frontend/src/api/intent.ts:161`. `line.slice(5).trim()` on `data:` lines. JSON tolerates it today, but if the backend ever emits chunked prose with leading spaces, trimming eats them. Per SSE spec, strip exactly one optional leading space, not `.trim()`. Bites 18 months from now.

**🔵 Minor — `confirmed_focus` invariants are load-bearing coincidence**
`backend/app/services/set_your_course.py:659–665`. `tool_call_made=True` only when MCP returned rows; `school_gap` has no rows so the gate auto-strips `confirmed_focus`. Correct today, but add a comment so the next editor doesn't break it when MCP semantics change.

**🔵 Minor — CORS `allow_origins=["*"]` + `allow_credentials=True`**
`backend/app/main.py:30–36`. Pre-existing hackathon footgun, not new here. Browsers reject this combination anyway. Flag for its own spec.

**🔵 Minor — 422 body is `ValueError`-wrapped**
`backend/app/models/api.py:152–159`. FastAPI wraps `raise ValueError(...)` into `{"detail":[{"msg":"Value error, clarifier is required ..."}]}`. Readable, not pretty. Acceptable.

#### What's Actually Good
- SSE parser does real `\n\n` re-buffering with a streaming TextDecoder — no split-packet bugs. I looked hard.
- `normalize_input` pinned in one place; every writer and reader goes through it. That's the discipline I keep asking juniors for.
- `_drain_sync` sentinel pattern for the sync→async bridge is correct (modulo the leak above).
- `unitid` is `int()`-cast before raw-SQL interpolation — no injection via the new path.
- Frontend AbortController is load-bearing, not decorative: `fetch(...signal)` plus a `controller.signal.aborted` guard inside the `for await`. Real cancellation.
- `record_commit` returns `False` when initial == current CIP — no noise in the log.
- `_ensure_timestamp` isolates the clock for deterministic tests.

#### Required Changes (routing)
1. **Stream/semaphore leak on abort** → Claude Code (general) to re-implement `generate_stream_async` cancellation. Serious. Blocks approval.
2. **Community-suggestions staleness (mtime check)** → Claude Code (general). Small, ships now or as a follow-up.
3. **Cross-process JSONL locking** → Claude Code (general) or explicit accept in §2/§10.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUIRED — fix #1 before merge. #2 and #3 may ship as follow-ups if explicitly acknowledged in §10.
- [ ] BLOCKER

---

## §9 Verification

**Status:** COMPLETE
**Verified:** 2026-04-19 15:42

### Backend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff) | PASS | 2 auto-fixed + 3 E501 manually fixed in test file; all checks pass |
| Type check (mypy) | PASS (new files) | 4 new service/router files: 0 errors. 45 pre-existing errors in unchanged files (stat_engine, builds, branches, routers, etc.) not gated |
| Tests (pytest) | PASS | 1020 passed, 0 failed |

### Pipeline (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff src/ tests/ scripts/) | PASS (src/ tests/) | Errors only in pre-existing scripts/ spike files; no spec-owned files affected |
| Tests (pytest tests/) | PASS | 1683 passed, 1 deselected, 0 failed |

### Frontend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| TypeScript | PASS | 8 type errors in test file fixed (mock generator types + non-null assertions) |
| Tests (vitest) | PASS | 518 passed, 1 skipped, 0 failed (53 test files) |
| Production build (Vite) | PASS | 676 modules transformed; chunk size warning is pre-existing |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | backend ruff failed | 5 errors in tests/services/test_set_your_course.py (I001, F401, E501 x3) | Auto-fixed I001+F401; manually split E501 string literals |
| 2 | gemma_client.py mypy (line 377) | `list[dict]` missing type args on new `generate_stream_async` param | Changed to `list[dict[str, Any]]` |
| 3 | frontend tsc failed | 8 errors in useSetYourCourse.test.ts — mock generator not typed as `StreamEvent`, 4x TS2532 | Typed `stubStream` return + added `StreamEvent` import; non-null assertions on `.mock.calls[0]!` |

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
- Broad-CIP lookup parity: the old `/school` flow's
  `_handle_get_career_paths` substitution branch keys on the school-
  reported broad CIP (the `parentCip` pathway) because the YAML /
  intent resolver could match a leaf while the school reports the
  parent. The new flow has a single `IntentResult.matched_cip` and no
  parentCip/cipCode split. Decide before the frontend wires
  `getOutcomes` in `useSetYourCourse`: (a) require Gemma's initial
  resolution to match at the school's reported 4-digit grain (prompt
  obligation + tool-verify), (b) add a `school_reported_cip4` sibling
  field on `IntentResult` that downstream lookups use, or (c) route
  the new flow past the substitution branch entirely on the grounds
  that the 4-digit grain invariant (Decision #15) makes it moot. The
  substitution code is load-bearing for the `/school` flow shipping
  alongside — any change must preserve the old path. Raised by
  `reports/cip-routing-ask-gemma-diagnosis-2026-04-19.md` (same
  state-duplication bug class as the Ask-Gemma stale-CIP bug).
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
