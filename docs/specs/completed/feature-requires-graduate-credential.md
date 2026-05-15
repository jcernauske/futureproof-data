# Feature: Requires-Graduate-Credential — Tell Students When the Career They Named Is Grad-School Only

## Claude Code Prompt

```
Read the spec at docs/specs/feature-requires-graduate-credential.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review §1–§4 for: new chip-routing bucket
     (`requires_graduate_credential`) and 6th feasibility mode (`requires_grad_school`),
     new MCP tool surface (`get_occupation_education_requirements`), the
     curated `grad_credential_feeders.yaml`, the pre-flag of "pre-X"
     typed-major patterns at initial resolution, and the new
     `GradCredentialNotice` tile + frontend wiring.
   - Invoke @fp-data-reviewer to review: where the BLS `education_code`
     signal lives (`consumable.occupation_profiles`), how the new tool
     joins to it, what counts as a "grad-school-only" career
     (codes 1–2), and the cacheability rule for the new feasibility mode.
   - Invoke @genai-architect (ad-hoc) to review the bucket prompt addition,
     the pre-flag heuristic at initial-resolution time, and how the chip
     prompt avoids mis-classifying intent_divergence cases as
     requires_graduate_credential when the typed major IS a feeder.
   - All three write findings to §5.
   - If APPROVED: proceed to step 2.
   - If CHANGES REQUESTED (Significant): STOP, alert human.
   - If REJECTED (Blocker): STOP, alert human.

2. DESIGN VISION
   - Invoke @fp-design-visionary to propose the `GradCredentialNotice`
     tile in both desktop and mobile. Three deliverables: (1) tile
     wireframe in the streamed-resolution surface (above career
     preview), (2) feeder-major card row inside the tile (3–5 cards,
     tap to swap resolution), (3) the soft pre-flag treatment when a
     "pre-X" typed major is detected at initial-resolution time.
   - Writes findings to §3.

3. IMPLEMENTATION
   - Implement §3 and §4 exactly. Touch only files in the File Changes table.
   - BEFORE coding: read §4 Testing Impact Analysis. If any "Confirmed Safe"
     test fails, STOP and escalate.
   - Log all work to §6. Run backend + frontend suites to verify the
     build is green when you finish.
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts).

4. TESTING
   - Invoke @test-writer to add the cases in §4 "New Tests Required".
     P0 first. Mocked Gemma + mocked MCP tool only — no live calls in CI.

5. DESIGN AUDIT
   - Invoke @design-builder to verify Brightpath token compliance against DESIGN.md.

6. CODE REVIEW
   - Invoke @faang-staff-engineer for security/performance/error-handling review.

7. VERIFICATION
   - Invoke @fp-builder for the standard build gate.

8. COMPLETION
   - Update Status to COMPLETE.
   - Move spec to docs/specs/completed/.
   - Write completion report to reports/feature-requires-graduate-credential-YYYY-MM-DD.md.
```

---

## Status: COMPLETE

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-05-06 |
| Author | Jeff Cernauske + Claude Desktop |
| Spec Version | 1.0 |
| Last Updated | 2026-05-06 |
| Blocked By | — |
| Related Specs | `docs/specs/completed/feature-set-your-course.md` (extends), `docs/specs/feature-school-discovery.md` (CTA pattern reference) |

---

## §1 Feature Description

### Overview

Add a 6th feasibility mode and an 8th chip-routing bucket — both named for the same data fact: **the career the student named requires graduate or professional school as its entry credential**, so the student's question "what undergrad major leads to X" doesn't have a clean answer. The product reframes: it shows feeder undergrad majors offered at the student's school that students typically use to reach that grad credential, and names the credential plainly. Also adds a soft pre-flag at initial-resolution time when the student's *typed major* is itself a "pre-X" track ("pre-PT," "pre-med," "pre-law," "pre-vet," "pre-dental," "pre-PA"), surfacing the same notice without waiting for a chip tap.

The data signal already exists. `consumable.occupation_profiles` carries `education_code` (1=Doctoral/professional → 8=No formal credential) and `education_level_name` on every SOC, sourced from the Bureau of Labor Statistics (BLS) Occupational Outlook Handbook. Codes 1–2 (Doctoral/professional, Master's) are "graduate-school-only" by BLS's own definition. This spec is plumbing — surface that signal at the moment the student needs it.

### Problem Statement

Today, a student at a non-PT school who types "Marketing" and clarifies "I want to be a physical therapist" gets routed through `intent_divergence`: Gemma offers alternative majors that "lead to" Physical Therapist. That framing is wrong. **No undergrad major leads to Physical Therapist.** PT requires a Doctor of Physical Therapy (DPT). Exercise Science, Biology, Kinesiology — these are *feeder undergrads that prepare you for the prereqs of DPT school*, not paths to becoming a PT.

The same shape applies to Lawyer (JD), Physician (MD/DO), Dentist (DDS), Veterinarian (DVM), Pharmacist (PharmD), Optometrist (OD), and a long tail of master's-required clinical, counseling, and library/archival roles.

Today's product:
1. The pentagon stats engine resolves "Physical Therapist" to its SOC (29-1123) and renders ERN/GRW from the BLS data, ignoring the `education_code=1` field that says "this is grad-only" — student walks away with a build that pretends an undergrad path exists.
2. The chip routing prompt's `intent_divergence` bucket would either (a) suggest Marketing→PT (wrong) or (b) suggest Exercise Science→PT (still subtly wrong — Exercise Science → DPT school → PT, not Exercise Science → PT).
3. There's no surface for "the right answer is to switch undergrad goals AND plan for grad school," which is the *actual* answer for thousands of pre-health students every year.

This is also the same data-honesty argument that produced `school_gap`: refusing to lie when the data says the student's framing of the question doesn't have an undergrad answer.

### Success Criteria

- [ ] New chip-routing bucket `requires_graduate_credential` added to `_CHIP_ROUTING_SYSTEM_PROMPT` with one concrete inline example (Physical Therapist), per the @genai-architect bucket-coverage rule.
- [ ] New `FeasibilityMode` value `requires_grad_school` added to `backend/app/models/api.py`. Not cacheable — does not feed `community_suggestions.get_suggestions`. Same posture as `school_gap` and `genuinely_impossible`.
- [ ] `ChipBucket` Literal extended with `requires_graduate_credential` (9 buckets total).
- [ ] New MCP tool `get_occupation_education_requirements(soc_code: str) -> dict` exposed on the FutureProof MCP server. Returns `{soc_code, occupation_title, education_code, education_level_name, requires_grad_school: bool}` where `requires_grad_school = education_code IN (1, 2)`. Reads from `consumable.occupation_profiles`.
- [ ] Tool registered in `mcp_client.get_tool_openai_schema` and listed in the chip-routing prompt's tool surface.
- [ ] Chip-routing prompt updated to call `get_occupation_education_requirements` whenever the clarifier names a career (or a SOC the prompt resolved from the clarifier) — same Gemma-grounded pattern the existing `crosswalk_mismatch` and `intent_divergence` buckets use for `get_career_paths`.
- [ ] New curated `data/reference/grad_credential_feeders.yaml` with ~10–15 grad-credential entries (DPT, JD, MD, DDS, DVM, PharmD, OD, Master's-of-Social-Work, Master's-Speech-Language-Pathology, Master's-Counseling, Master's-Library-Science, Master's-Physician-Assistant). Each entry lists 5–8 typical feeder 4-digit CIPs and one paragraph of plain-English context. Schema in §4.
- [ ] New service module `backend/app/services/grad_credentials.py` with two public functions: `lookup_credential_for_soc(soc_code: str) -> GradCredentialEntry | None` and `feeder_majors_at_school(unitid: int, credential_id: str) -> list[FeederMajor]`. Reads YAML at startup; no Gemma call.
- [ ] New `ChipResponse.cta_link` use: when bucket is `requires_graduate_credential`, the response carries a `kind="grad_credential_notice"` link payload describing the credential. The frontend renders the `GradCredentialNotice` tile from this payload — no separate API endpoint.
- [ ] New frontend component `frontend/src/components/school/GradCredentialNotice.tsx`. Full-width tile, caution-stripe treatment, copy: *"Becoming a [Career Title] requires a [Credential Name] — graduate school. Here are common undergrad majors students at [School] take to get there."* Below: 3–5 feeder-major cards. Tap → swap resolution to that feeder CIP (calls existing `useSetYourCourse.acceptResolution`).
- [ ] **Pre-flag at initial resolution.** New regex-based check in `stream_initial_resolution` runs *before* Gemma is called: if the student's typed major matches `^pre-?(med|pt|law|vet|dent\w*|pa\b|optom\w*|pharm\w*)\b` (case-insensitive, applied to the normalized input), the resolver short-circuits and returns an `IntentResult` with `confidence="low"`, `pre_flag_credential_id=<credential_id>` populated, and the matching credential. The frontend reads `pre_flag_credential_id` and renders `GradCredentialNotice` directly above the streamed prose — no chip tap needed.
- [ ] `IntentResult` extended with `pre_flag_credential_id: str | None = None`. Additive, backwards-compatible. Set ONLY by the pre-flag path; chip-flow updates leave it None.
- [ ] When the chip flow's `requires_graduate_credential` bucket fires, the bucket-classification log line carries `feasibility_mode="requires_grad_school"`. The correction log records this; community suggestions filter excludes it (matches existing `school_gap` posture).
- [ ] Career tiles for grad-only SOCs are STILL shown when the student commits — the build-engine is unchanged. The notice is informational guidance at the resolution layer, not a build-time block. Students who explicitly *want* the build that frames their next steps as "go to DPT school" can still commit. Pentagon stats render normally; the pre-flag is a guidance signal, not a constraint.
- [ ] Acronym-spell-out rule: prose says "Doctor of Physical Therapy (DPT)" on first reference, "DPT" thereafter. Sources cited: "Bureau of Labor Statistics (BLS)" on first reference. No internal-taxonomy leakage (no SOC, no CIP, no numeric codes in student-facing strings).
- [ ] `requires_graduate_credential` bucket is NEVER classified when the student's clarifier names a career whose `education_code` is in 3–8. Chip prompt rule: only fire this bucket when `requires_grad_school=True` is confirmed via the new tool call. (Anti-fabrication guard.)
- [ ] When the chip clarifier names a target career that IS grad-only AND the student's *currently-resolved* typed major IS a known feeder for that credential, the chip prompt routes to `requires_graduate_credential` (not `intent_divergence`) — this is the "Bio major says they want to be a doctor" case, where the student is already on a sensible track and just needs the grad-school heads-up rather than alternative-major suggestions.
- [ ] Full test suite passes: backend + root pytest, frontend vitest, TypeScript. Ruff + mypy clean. Vite build succeeds.
- [ ] Design audit against Brightpath tokens passes (`DESIGN.md`).

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | **Two surfacing paths, not one.** Bucket on the chip flow + pre-flag at initial-resolution time. | (a) The chip bucket alone misses the most common case: a 17-year-old types "physical therapy" or "pre-PT" as their *major* and never taps a chip because the build looks plausible (Health Sciences program, ERN 6 — looks fine). The student walks away thinking they have an undergrad path to PT. (b) The pre-flag alone misses the "Marketing major + I want to be a doctor" case where the typed major is reasonable but the clarified goal is grad-only. (c) Both shipping is cheap — they share the YAML, share the notice tile, share the feeder lookup. The two paths are orthogonal, not duplicative. | (a) Chip-only — rejected, doesn't catch typed pre-X. (b) Pre-flag-only — rejected, doesn't catch clarified divergence. (c) New "did you know" toast post-commit — rejected, too late; the student has already seen a misleading build. |
| 2 | **Bucket + feasibility mode are NEW values, not reuse of `intent_divergence`.** | (a) `intent_divergence`'s contract is "offer alternative majors that lead to the clarified career." For grad-only careers, no undergrad major leads there — the offer-alternatives action is structurally wrong. (b) Naming the failure mode for what it is (requires graduate school) gives the student honest information, the engineer a clean classifier, and the demo a clean talking point. (c) Splitting the bucket also lets us track frequency separately in the correction log: how often students discover their goal needs grad school. | (a) Reuse `intent_divergence` and add a special case — rejected, conflates two distinct data observations and bloats one bucket's prompt logic. (b) Reuse `school_gap` (no school here offers a path to PT) — rejected, not a school-specific issue; even Harvard students hit this for PT. |
| 3 | **`requires_grad_school` feasibility mode is NOT cacheable.** | Same posture as `school_gap` and `genuinely_impossible` (per Set Your Course feasibility classification). The "answer" the student lands on after this notice — picking a feeder major — is captured by whichever cacheable mode (`direct_hit` / `crosswalk_quirk` / `adjacent_reachable`) the feeder career swap produces. The grad-credential notice itself is a fact about the *question*, not a recommendation worth caching. | Cacheable-as-`adjacent_reachable` — rejected, "PT is reachable through DPT school" reinforces the misleading framing in the community-suggestions surface. The signal we want to learn from is "the student picked Exercise Science after seeing the notice," and that's already captured by the resolution-swap. |
| 4 | **Curated YAML for grad-credential feeders, not Gemma-generated at runtime.** | (a) The list of feeders is small (~10–15 credentials, ~5–8 feeders each = ~100 entries total), changes slowly, and benefits from human curation. ~Half a day of work to build, not a system to maintain. (b) Gemma-generated feeders would be unstable (a JD applicant should see Political Science, History, Philosophy, English — Gemma might omit any of these). (c) The product already imports a strict no-static-lookup discipline for *student input → CIP* resolution; this is *credential → typical feeder CIPs*, a different question, and one where stability is the point. (d) Running locally on Ollama with a hackathon time budget, eliminating one tool-call round trip from the chip flow matters. | (a) Gemma-generated at chip time — rejected per (b). (b) Pull from O*NET career transitions data — rejected, O*NET career transitions is occupation-to-occupation, not credential-to-feeder-major; the data shape doesn't fit. (c) No feeders shown, just "go to grad school" — rejected, abandons the student at the moment they need the most help reframing. |
| 5 | **YAML is keyed by credential, not by SOC.** Each entry has a `credential_id` (e.g. `dpt`), `credential_name_full` (e.g. "Doctor of Physical Therapy"), `credential_acronym` (e.g. "DPT"), `socs` (list of SOCs this credential leads to — usually 1, sometimes 2–3 for credentials like JD), and `feeder_cip4_codes` (list of 4-digit CIPs). | (a) Many credentials map to a single SOC (DPT → 29-1123), but a few credentials (JD → multiple Lawyer-related SOCs) and a few SOCs (Counselor → multiple master's credentials) have many-to-many shape. Keying by credential keeps the YAML edits small and the lookup stable. (b) A credential-keyed YAML is also easier for a human curator to keep accurate — the credential IS the canonical fact; SOCs are the surface mapping. | SOC-keyed — rejected, leads to duplication (PT shows up under DPT, but also under Other-Health-Diagnosing-Workers). CIP-keyed — rejected, not the natural shape of the data ("which credentials does Biology lead to" is the inverse direction; we want "which feeders for this credential"). |
| 6 | **The career build is NOT blocked at commit when the resolved SOC is grad-only.** Pentagon stats render normally. | (a) A student who explicitly wants the PT build (so they can see the long-term ERN/GRW after grad school) deserves to see it. (b) Soft guidance > hard gating — same posture as the low-confidence soft nudge in Set Your Course Decision #10. (c) Gating commit on grad-only careers would also block legitimate "I'm already planning on grad school" students who tap "Yes, continue" intentionally. | Hard-gate commit on grad-only SOCs — rejected per (a) and (c). |
| 7 | **Pre-flag fires only on a small list of "pre-X" patterns, not every typed major.** | (a) The pre-X namespace is small and unambiguous: pre-med, pre-PT, pre-law, pre-vet, pre-dent (also "pre-dental"), pre-PA, pre-optometry, pre-pharm. Adding patterns is one regex line. (b) Other inputs that *might* indicate grad-school intent (e.g. "biochemistry" for a pre-med, "political science" for a pre-law) cannot reliably be distinguished from the legitimate undergrad track. The student who types "biochemistry" is signaling a major; the student who types "pre-med" is signaling a track. Different signals, different surfaces. (c) Anything else that should fire — student typed "Health Sciences" but clarified "I want to be a PT" — gets caught by the chip flow's `requires_graduate_credential` bucket. The two paths are designed to compose. | Fire pre-flag on any major that frequently feeds a grad credential — rejected per (b); too many false positives, and the "feeder" framing is the wrong one for a student who hasn't said anything about grad school yet. |
| 8 | **Notice tile renders ABOVE the career preview, not in place of it.** | (a) The pentagon is the product's most distinctive surface; suppressing it on grad-only careers makes the screen feel broken. (b) The student needs both signals simultaneously: "here's the build for the career as you described it" AND "here's the credential the build assumes." A stacked layout (notice → preview) communicates both honestly. | Replace preview with notice — rejected per (a). Notice as a tooltip — rejected, too easy to miss; this is the most important piece of information on the screen for these students. |
| 9 | **The new MCP tool is `get_occupation_education_requirements`, not just adding `education_code` to the existing `get_occupation_data` tool.** | (a) Single-purpose tools are easier for Gemma 4 e4b on Ollama to call correctly — function-calling reliability degrades when tool argument schemas balloon. (b) The new tool's contract is small (one input, one structured output) and named for exactly what it does. (c) Adding fields to `get_occupation_data` would require touching every existing call site (`career_pick_qna`, `ask_gemma`, etc.) to verify the new fields don't break their downstream logic. Net: less risk, less rework. | Extend existing tool — rejected per (a) and (c). |
| 10 | **Acronym-spell-out applies to credentials too, not just data sources.** First reference per rendered view: "Doctor of Physical Therapy (DPT)"; subsequent references: "DPT". | Per Set Your Course Decision #14, the acronym-spell-out rule is a journalism-style anchor that applies to anything the student might not recognize on first reading. Credentials are exactly that — students know "PT" but may not know "DPT" — so spell out + parenthetical first reference. | Always-acronym — rejected, assumes credential literacy a 17-year-old doesn't have. Always-full-name — rejected, becomes ponderous in feeder-card copy. |

### Constraints

- `consumable.occupation_profiles` — read source for `education_code` and `education_level_name`. Already populated; no pipeline changes.
- `data/reference/grad_credential_feeders.yaml` — new curated reference file. Committed to git.
- `backend/app/services/set_your_course.py::_CHIP_ROUTING_SYSTEM_PROMPT` — new bucket added; existing buckets unchanged.
- `backend/app/services/set_your_course.py::stream_initial_resolution` — new pre-flag short-circuit; existing path unchanged.
- `backend/app/models/api.py` — `FeasibilityMode` and `ChipBucket` Literals extended; `IntentResult` gets one new optional field.
- `src/mcp_server/futureproof_server.py` — new `get_occupation_education_requirements` handler. Existing tools unchanged.
- `frontend/src/components/school/GradCredentialNotice.tsx` — new component.
- `frontend/src/screens/SetYourCourseScreen.tsx` — adds one render slot for the notice tile, conditional on either (a) `currentResolution.pre_flag_credential_id` set OR (b) `lastChipResponse.cta_link?.kind === "grad_credential_notice"`. Existing layout unchanged.
- Brightpath tokens (`DESIGN.md`) — no new tokens; reuse caution-stripe, accent-caution palette per the existing `school_gap` tile.
- Build engine, pentagon stats, boss fights — UNCHANGED. The notice is informational guidance at the resolution layer.

### Out of Scope

- **Changing pentagon stat formulas for grad-only SOCs.** v2.
- **Showing grad-school cost/time alongside undergrad cost/time.** v2 — would require ingesting separate data sources for DPT/JD/MD school cost.
- **Ranking feeder majors by ERN at the school.** Tap-order in the YAML is curator-chosen; ranking is a later feature.
- **Pre-X expansion (pre-business, pre-engineering, etc.).** The pre-X namespace stays scoped to grad-credential tracks per Decision #7.
- **A separate "Grad School Boss Fight."** v2 — interesting product idea, but not Set Your Course's surface.
- **Course Catalog Crawler for school-specific feeder coverage.** Post-hackathon (already deferred per project memory). The YAML is the hackathon-grade approximation.
- **Localization of credential names.** v2 — DPT/JD/MD are US-specific; adding international credentials is a future scope expansion.

---

## §3 UI/UX Design

### Brief (for @fp-design-visionary)

The visionary should produce:

1. **GradCredentialNotice tile — desktop and mobile.** Full-width inside the streamed-resolution surface, above the career preview. Caution-stripe edge treatment matching the `school_gap` v0.5 stub (per `feature-school-discovery.md`). Header: full credential name + parenthetical acronym. Subhead: 1 sentence naming the career and the data source ("Bureau of Labor Statistics" — first reference full name + acronym). Body: 1 sentence reframing ("here are common undergrad majors students at [School] take to get there"). Below: 3–5 feeder-major cards in a horizontal row on desktop, vertical stack on mobile.

2. **Feeder-major card.** Compact card (smaller than a career tile). Carries `cip_title` (e.g. "Exercise Science"), one short note from the YAML ("Strong anatomy/physiology core"), and a tap affordance. Tapped → swaps the current resolution; the tile dismisses with `layoutId` motion (per the existing chip resolution-swap motion).

3. **Pre-flag treatment.** When `pre_flag_credential_id` is set on the initial resolution, the same notice tile renders above the streamed prose, but with a slightly different lead copy: *"Pre-PT isn't an undergrad major itself — it's a track toward DPT school..."* The streamed prose still appears below the notice (Gemma still narrates the resolution it picked, e.g. Health Sciences as the closest matching program). The notice is the first thing the student sees; the prose explains why the resolution landed where it did.

4. **Caution-stripe vs. info-only treatment.** For the chip-flow path (student tapped a chip and Gemma found grad-only), the notice carries an `accent-caution` stripe — the message is "your understanding of how to get to this career was incomplete." For the pre-flag path (student typed pre-X), the stripe is `accent-info` — softer; the student has already signaled grad-school awareness by typing pre-X. Same component, two visual variants driven by a `tone: "caution" | "info"` prop.

5. **Mobile sticky-bar interaction.** The commit bar's "Yes, continue" CTA stays enabled even when the notice is visible. No hard gate (per Decision #6). The notice does not push the commit out of the viewport; if the notice is tall, it scrolls inside its own container.

Constraints for the visionary:

- Brightpath dark-first, plush, cinematic.
- Reuse existing `accent-caution` and `accent-info` token families. No new colors.
- Tile body copy is voice-guide compliant: cool, confident, data-honest. Use the student's wording for the career when they typed it; use the BLS occupation title otherwise.
- Acronym-spell-out: full credential name first; acronym after.
- Mobile-first feeder card row: 1 card per row, scrollable horizontally if more.

### Design Vision (@fp-design-visionary)

**Reviewed:** 2026-05-05
**Verdict:** APPROVED — canonical design below.

---

#### Emotion Target

The student typed "pre-PT" or tapped a chip expecting an undergrad path to Physical Therapist. They are about to learn that their framing of the question was incomplete. This is a vulnerable moment. The emotion we are designing for is **gentle course-correction with maintained agency**: "oh, I see — there's a credential in between. What undergrads do people take to get there?" The student should feel informed and redirected, never shamed or blocked.

For the **caution** tone (chip path): The student said "I want to be a PT" and Gemma discovered the gap. The energy is "here's something important your plan is missing" — warm yellow like a thoughtful heads-up from a mentor, not a traffic-light red.

For the **info** tone (pre-flag path): The student already typed "pre-PT" — they know this is a track, not a major. The energy is calmer, more confirmatory: "you already know this; here's what that means concretely." Cool blue, informational, collegial.

Here is why this matters: the visual treatment must feel like the world is helping the student see something clearly, not punishing them for asking the wrong question. The accent-stripe is a left-edge beacon (like the existing reasoning card's `border-l-accent-insight`) — it creates the "pay attention here" signal without boxing the student in.

---

#### Wireframe — Desktop (full-width, above career tier)

```
+-- GradCredentialNotice -------------------------------------------------------+
| |                                                                              |
| |  [Header -- font-display, text-heading, 600]                                |
| |  Doctor of Physical Therapy (DPT)                                            |
| |                                                                              |
| |  [Subhead -- font-body, text-body, text-secondary]                           |
| |  According to the Bureau of Labor Statistics (BLS), becoming a Physical      |
| |  Therapist requires a DPT -- graduate school.                                |
| |                                                                              |
| |  [Body -- font-body, text-body, text-primary]                                |
| |  Here are common undergrad majors students at Indiana University take         |
| |  to prepare for DPT school.                                                  |
| |                                                                              |
| |  +----------------+ +----------------+ +----------------+ +----------------+ |
| |  | Exercise       | | Biology        | | Kinesiology    | | Health         | |
| |  | Science        | |                | |                | | Sciences       | |
| |  |                | | Strong pre-    | | Movement-      | | Broad pre-     | |
| |  | Strong A&P     | | health         | | focused;       | | health         | |
| |  | core           | | foundation     | | direct fit     | | option         | |
| |  |     [->]       | |     [->]       | |     [->]       | |     [->]       | |
| |  +----------------+ +----------------+ +----------------+ +----------------+ |
| |                                                                              |
| |  [Footer -- font-body, text-small, text-muted]                              |
| |  Tap a major to switch your build. Your career preview below still shows     |
| |  the Physical Therapist path.                                                |
+--------------------------------------------------------------------------------+

  | = left accent stripe (3px)
      tone="caution" -> accent-caution (#F2D477)
      tone="info"    -> accent-info (#7BB8E0)
```

#### Wireframe — Mobile (single column, cards scroll horizontally)

```
+-- GradCredentialNotice -------------------+
| |                                          |
| |  Doctor of Physical Therapy (DPT)        |
| |                                          |
| |  According to the Bureau of Labor        |
| |  Statistics (BLS), becoming a Physical   |
| |  Therapist requires a DPT -- graduate    |
| |  school.                                 |
| |                                          |
| |  Here are common undergrad majors        |
| |  students at Indiana University take to  |
| |  prepare for DPT school.                 |
| |                                          |
| |  +------------+ +------------+ +--(...)  |
| |  | Exercise   | | Biology    | | Kines   |
| |  | Science    | |            | |         |
| |  | Strong A&P | | Strong pre | | Movem   |
| |  |    [->]    | |    [->]    | |    [->  |
| |  +------------+ +------------+ +--(...)  |
| |  <- swipe ->                             |
| |                                          |
| |  Tap a major to switch your build.       |
+--------------------------------------------+
```

#### Wireframe — Feeder-Major Card (single card detail)

```
+--------------------------------+
|                                |   bg-bp-mid (#232545)
|  Exercise Science              |   font-display, text-body (16px), 600, text-primary
|                                |
|  Strong anatomy and            |   font-body, text-small (14px), 400, text-secondary
|  physiology core               |   max 2 lines, line-clamp-2
|                                |
|  --------------------------    |   border-t border-border-subtle
|  Switch to this major    ->    |   font-body, text-small, 600, accent-thrive
|                                |   (or accent-info for info tone)
+--------------------------------+

For offered_at_school=false:
+--------------------------------+
|  <> not offered here           |   pill-alert (micro, top-right corner)
|                                |
|  Psychology                    |
|                                |
|  Required prereqs sit          |
|  naturally inside this major   |
|                                |
|  --------------------------    |
|  Switch to this major    ->    |   text-text-muted (de-emphasized affordance)
+--------------------------------+
```

#### Wireframe — Pre-flag variant (tone="info")

```
+-- GradCredentialNotice -------------------------------------------------------+
| |                                                                              |
| |  Doctor of Physical Therapy (DPT)                             <- info stripe |
| |                                                                              |
| |  Pre-PT is not an undergrad major itself -- it is a track toward Doctor of   |
| |  Physical Therapy (DPT) school. The closest matching program at Indiana      |
| |  University is Health Sciences.                                              |
| |                                                                              |
| |  Here are common undergrad majors students at Indiana University take         |
| |  to prepare for DPT school.                                                  |
| |                                                                              |
| |  [feeder cards row -- same as above]                                         |
| |                                                                              |
| |  Tap a major to switch your build.                                           |
+--------------------------------------------------------------------------------+
```

---

#### Design Rationale

**1. Left-edge accent stripe (not a full border or banner).**

What it is: A 3px left border, matching the reasoning card's existing `border-l-[3px]` pattern (see `SetYourCourseScreen.tsx` lines 390, 491).

Why it works: The product already trains the student's eye on left-border-color = "Gemma is talking to you." This notice tile uses the same affordance but swaps the color (insight -> caution or info) to signal "different kind of message." The stripe is narrow enough to not feel like a warning banner but visible enough to create hierarchy.

How it feels: Warm, not alarming. The same way a handwritten margin note feels different from a red alert.

The details: `border-l-[3px]` with `border-l-accent-caution` or `border-l-accent-info`. No top/right/bottom colored border. The outer border remains `border-border-subtle` (the standard card border).

**2. Full-width tile inside the resolution flow, not a modal or toast.**

What it is: A stacked layout element that enters after the resolution header and before the career tier section.

Why it works: Modals break flow and demand dismissal. Toasts are ephemeral and miss-able. An inline tile is undeniable but non-blocking — the student sees it in context, above the career cards it is explaining. The commit bar stays active (Decision #6). The student can scroll past it.

How it feels: The world is informing them; they retain control. Same as how a textbook might have a callout box — you read it, you understand, you keep reading.

**3. Feeder-major cards as small, tappable surfaces.**

What it is: Compact cards (roughly 160px wide on desktop, full-width on mobile) with CIP title, curator note, and a clear tap affordance. Smaller than CareerCards. No stat bars.

Why it works: These are not careers — they are undergrad majors. They need a different visual weight. The career cards below have stat bars, ERN figures, emoji. The feeder cards are intentionally lighter: name, one sentence of context, an action. The visual hierarchy says "these are options; those below are outcomes."

How it feels: Like a menu of reasonable next steps — not overwhelming, not underwhelming. The card is small enough that 4 fit comfortably in a row on desktop, but substantial enough that the tap affordance feels intentional.

The details: `bg-bp-mid`, `border-border-subtle`, `rounded-xl`, `p-4`. 160px min-width on desktop (flex children of a row). Full-width on mobile with horizontal scroll via `overflow-x-auto` + `snap-x`. The tap area is the entire card (not just the arrow).

**4. "Not offered here" indicator as a subtle pill, not a disabled state.**

What it is: A small `pill-alert` badge in the top corner reading "not offered here" with the open-diamond glyph (per the Brightpath pill glyph convention).

Why it works: The card is still tappable (switching to it shows the student what that major leads to at other schools). Disabling would lock them out of information. The pill is informational: "this school does not report offering this major, but it is still a legitimate feeder."

How it feels: A gentle footnote, not a roadblock. The student can still explore.

**5. Horizontal scroll on mobile with snap behavior.**

What it is: On viewports below tablet (768px), feeder cards are displayed in a single row with `overflow-x-auto`, `scroll-snap-type: x mandatory`, and each card snaps on `scroll-snap-align: start`.

Why it works: Vertical stacking of 4-5 cards would push the career preview far below the fold, violating the "notice does not push commit out of viewport" constraint. Horizontal scroll keeps the tile's vertical footprint contained.

How it feels: Like swiping through options in a story — natural thumb-driven exploration. The slight peek of the next card invites scrolling.

**6. Entry animation: gentle fadeInUp, not bouncy.**

What it is: Framer Motion `initial={{ opacity: 0, y: 16 }}` with `springs.smooth` transition. Feeder cards stagger at 80ms (`stagger.normal`).

Why it works: This is corrective information, not a celebration. The smooth spring (stiffness: 200, damping: 25) communicates "here is something to consider" without the exuberance of a bouncy spring. The stagger on the cards creates a left-to-right reading flow.

How it feels: The tile materializes gently, like fog clearing. The cards waterfall in — each one a distinct option arriving into the student's awareness.

**7. Tap-to-swap uses exit animation for continuity.**

What it is: When a feeder card is tapped, it animates (scale briefly to 0.97 on press, then the entire notice tile exits with `opacity: 0, y: -12`). The resolution changes. The new career tier section enters.

Why it works: The student's action (tapping a feeder) causes a visible, understandable state change. The tile leaves; the new career cards arrive. Cause and effect. No jarring cut.

---

#### Typography Specification

| Element | Font | Size Token | Weight | Color Token | Tailwind |
|---------|------|-----------|--------|-------------|----------|
| Credential name (header) | Fredoka | `text-heading` (28px) | 600 | `text-primary` | `font-display text-heading font-semibold text-text-primary` |
| Subhead (BLS citation) | Nunito | `text-body` (16px) | 400 | `text-secondary` | `font-body text-body text-text-secondary` |
| Body (reframe sentence) | Nunito | `text-body` (16px) | 400 | `text-primary` | `font-body text-body text-text-primary` |
| Feeder card title | Fredoka | `text-body` (16px) | 600 | `text-primary` | `font-display text-body font-semibold text-text-primary` |
| Feeder card note | Nunito | `text-small` (14px) | 400 | `text-secondary` | `font-body text-small text-text-secondary` |
| Feeder card CTA | Nunito | `text-small` (14px) | 600 | `accent-thrive` / `accent-info` | `font-body text-small font-semibold text-accent-thrive` |
| Footer guidance | Nunito | `text-small` (14px) | 400 | `text-muted` | `font-body text-small text-text-muted` |
| "Not offered" pill | Nunito | `text-micro` (12px) | 600 | `accent-alert` | `font-body text-micro font-semibold text-accent-alert` |

#### Animation Specification

| Element | Initial | Animate | Spring | Delay |
|---------|---------|---------|--------|-------|
| Notice tile | `opacity: 0, y: 16` | `opacity: 1, y: 0` | `springs.smooth` (200/25) | 0ms |
| Feeder card [i] | `opacity: 0, y: 12` | `opacity: 1, y: 0` | `springs.smooth` (200/25) | `i * stagger.normal` (i * 80ms) |
| Tile exit (on feeder tap) | current | `opacity: 0, y: -12` | `springs.smooth` | 0ms |
| Card press feedback | current | `scale: 0.97` | `springs.snappy` (400/25) | 0ms |

#### Spacing Specification

| Element | Token | Value |
|---------|-------|-------|
| Tile padding | `p-5` (desktop), `p-4` (mobile) | 20px / 16px |
| Gap between text blocks | `gap-3` | 12px |
| Gap between feeder cards (desktop) | `gap-3` | 12px |
| Gap between feeder cards (mobile scroll) | `gap-3` | 12px |
| Feeder card internal padding | `p-4` | 16px |
| Feeder card min-width (desktop) | -- | 160px |
| Feeder card width (mobile) | -- | 200px (fixed for scroll uniformity) |
| Tile margin above career section | `mt-6` | 24px |

---

#### Component Implementation

See `frontend/src/components/school/GradCredentialNotice.tsx` for the canonical React + Framer Motion implementation.

---

### Mockup (canonical)

```
+======================================================================+
| |                                                                    |
| |  Doctor of Physical Therapy (DPT)                                  |
| |                                                                    |
| |  According to the Bureau of Labor Statistics (BLS), becoming a     |
| |  Physical Therapist requires a DPT -- graduate school.             |
| |                                                                    |
| |  Here are common undergrad majors students at Indiana University   |
| |  take to prepare for DPT school.                                   |
| |                                                                    |
| |  +----------------+ +----------------+ +----------------+   ...    |
| |  | Exercise       | | Biology        | | Kinesiology    |         |
| |  | Science        | |                | |                |         |
| |  |                | | Strong pre-    | | Movement-      |         |
| |  | Strong anatomy | | health         | | focused;       |         |
| |  | & physiology   | | foundation     | | direct fit     |         |
| |  | core           | |                | |                |         |
| |  | -------------- | | -------------- | | -------------- |         |
| |  | Switch ->      | | Switch ->      | | Switch ->      |         |
| |  +----------------+ +----------------+ +----------------+         |
| |                                                                    |
| |  Tap a major to switch your build. Your career preview below       |
| |  still shows the Physical Therapist path.                          |
+======================================================================+

  | = 3px border-l-accent-caution (chip path) or border-l-accent-info (pre-flag)
```

For the pre-flag path, the subhead changes to:
*"Pre-PT is not an undergrad major itself -- it is a track toward Doctor of Physical Therapy (DPT) school."*

---

## §4 Technical Specification

### Architecture Overview

This spec touches five layers, all additive:

1. **Data contract layer** (read-only). `consumable.occupation_profiles` already carries `education_code` and `education_level_name`. No pipeline change.
2. **MCP tool layer.** New `get_occupation_education_requirements` handler in `src/mcp_server/futureproof_server.py`. Reads `consumable.occupation_profiles`. Single SOC in, single dict out.
3. **Reference data layer.** New curated `data/reference/grad_credential_feeders.yaml`. Loaded at app startup by the new `grad_credentials` service module.
4. **Backend service layer.** New `backend/app/services/grad_credentials.py`. Updates to `backend/app/services/set_your_course.py` (chip prompt + pre-flag logic). Pydantic model extensions in `backend/app/models/api.py` and `backend/app/models/career.py`.
5. **Frontend layer.** New `GradCredentialNotice.tsx` component. Render-slot in `SetYourCourseScreen.tsx`. Hook update in `useSetYourCourse.ts` to read both `pre_flag_credential_id` and the `cta_link` payload.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `data/reference/grad_credential_feeders.yaml` | Create | Curated credential → feeder CIP4 list. ~10–15 entries. |
| `backend/app/services/grad_credentials.py` | Create | Loads YAML at startup; exposes `lookup_credential_for_soc` and `feeder_majors_at_school`. |
| `backend/app/services/set_your_course.py` | Modify | Add `requires_graduate_credential` bucket to `_CHIP_ROUTING_SYSTEM_PROMPT`. Add pre-flag short-circuit at the top of `stream_initial_resolution`. Add post-Gemma chip dispatch hook to populate `cta_link` for the new bucket. |
| `backend/app/models/api.py` | Modify | Add `requires_graduate_credential` to `ChipBucket`, `requires_grad_school` to `FeasibilityMode`, `kind="grad_credential_notice"` to `CtaLink`, new `GradCredentialNoticePayload` model. |
| `backend/app/models/career.py` | Modify | Add `pre_flag_credential_id: str | None = None` to `IntentResult`. |
| `src/mcp_server/futureproof_server.py` | Modify | New `_handle_get_occupation_education_requirements` handler + tool registration. |
| `backend/app/services/mcp_client.py` | Modify | Register the new tool's OpenAI schema for the chip flow's tool surface. |
| `frontend/src/components/school/GradCredentialNotice.tsx` | Create | The notice tile component. |
| `frontend/src/screens/SetYourCourseScreen.tsx` | Modify | Add render slot for the notice tile; conditional on `currentResolution.pre_flag_credential_id` OR `lastChipResponse.cta_link?.kind === "grad_credential_notice"`. |
| `frontend/src/hooks/useSetYourCourse.ts` | Modify | Read the new fields; expose a `gradCredentialNotice` derived selector to the screen. |
| `frontend/src/types/buildInput.ts` | Modify | Mirror `pre_flag_credential_id` on the `IntentResult` TypeScript type; add `GradCredentialNoticePayload` type. |
| `frontend/src/api/intent.ts` | Modify | Pass `cta_link` through from the `dispatchChip` response (already present on the backend; surface it on the frontend). |
| `backend/tests/services/test_grad_credentials.py` | Create | YAML loader + lookup tests. |
| `backend/tests/services/test_set_your_course.py` | Modify | Add `TestRequiresGradCredential` test class with bucket + pre-flag coverage. |
| `backend/tests/mcp/test_education_requirements.py` | Create | MCP handler tests. |
| `frontend/src/components/school/GradCredentialNotice.test.tsx` | Create | Component render + interaction tests. |
| `frontend/src/hooks/useSetYourCourse.test.ts` | Modify | Add notice-tile selector tests. |
| `data/reference/grad_credential_feeders.example.yaml` | Create | Documentation example showing schema. |

### Data Model Changes

#### Extension to `FeasibilityMode` (`backend/app/models/api.py`):

```python
FeasibilityMode = Literal[
    "direct_hit",
    "crosswalk_quirk",
    "adjacent_reachable",
    "school_gap",
    "genuinely_impossible",
    "requires_grad_school",  # NEW — not cacheable
]
```

#### Extension to `ChipBucket` (`backend/app/models/api.py`):

```python
ChipBucket = Literal[
    "crosswalk_mismatch",
    "semantic_drift",
    "school_gap",
    "data_suppression",
    "tier_placement",
    "intent_divergence",
    "peer_variance",
    "no_issue_found",
    "requires_graduate_credential",  # NEW
]
```

#### Extension to `CtaLink` (`backend/app/models/api.py`):

```python
class CtaLink(BaseModel):
    label: str
    href: str
    kind: Literal["school_discovery_v05", "grad_credential_notice"] = "school_discovery_v05"
    payload: GradCredentialNoticePayload | None = None  # populated when kind == "grad_credential_notice"
```

#### New `GradCredentialNoticePayload` model (`backend/app/models/api.py`):

```python
class FeederMajor(BaseModel):
    """One feeder-major card in the GradCredentialNotice tile."""
    cip4: str = Field(pattern=r"^\d{2}\.\d{2}$")
    cip_title: str
    note: str = Field(max_length=120)  # short curator-written note
    offered_at_school: bool  # True if the school's reported programs include this CIP4

class GradCredentialNoticePayload(BaseModel):
    """Payload for the GradCredentialNotice tile.

    Attached to a ChipResponse.cta_link when bucket == requires_graduate_credential,
    or returned directly on IntentResult when pre_flag_credential_id is set.
    """
    credential_id: str
    credential_name_full: str  # "Doctor of Physical Therapy"
    credential_acronym: str    # "DPT"
    target_career_title: str   # "Physical Therapist" (or the student's wording, when applicable)
    target_soc: str | None     # the BLS SOC the credential leads to; None for pre-flag path before resolution
    school_name: str
    feeders: list[FeederMajor] = Field(min_length=3, max_length=5)
    tone: Literal["caution", "info"]  # caution for chip path, info for pre-flag path
```

#### Extension to `IntentResult` (`backend/app/models/career.py`):

```python
class IntentResult(BaseModel):
    # ...existing fields unchanged...
    pre_flag_credential_id: str | None = None
    # Set by stream_initial_resolution's pre-flag short-circuit when the
    # student's typed major matches a "pre-X" pattern (pre-med, pre-PT, etc.).
    # The frontend reads this and renders GradCredentialNotice above the
    # streamed prose with tone="info". Initial-resolution-only — chip dispatch
    # never sets this field.
```

Frontend TypeScript mirror in `frontend/src/types/buildInput.ts` gets the same optional string field plus the `GradCredentialNoticePayload` type definition.

#### YAML schema — `data/reference/grad_credential_feeders.yaml`:

```yaml
# data/reference/grad_credential_feeders.yaml
#
# Curated credential -> feeder undergrad majors lookup.
# Loaded at startup by backend/app/services/grad_credentials.py.
#
# Each entry describes one graduate or professional credential whose entry
# requirement (per BLS) is education_code 1 (Doctoral/professional) or
# 2 (Master's). Each lists 5-8 typical feeder 4-digit CIPs that students
# commonly take as undergrads to prepare for that credential.
#
# Schema:
#   credentials:
#     - credential_id: "<lowercase, dash-separated>"
#       credential_name_full: "<full name with parenthetical acronym on first ref>"
#       credential_acronym: "<short form>"
#       socs: [<BLS SOC codes this credential leads to>]
#       feeder_cip4_codes:
#         - cip4: "XX.XX"
#           note: "<one short sentence; <= 120 chars>"
#       context: "<one paragraph; <= 400 chars; rendered nowhere directly,
#                 used as Gemma context in the chip prompt>"

credentials:
  - credential_id: "dpt"
    credential_name_full: "Doctor of Physical Therapy"
    credential_acronym: "DPT"
    socs: ["29-1123"]
    feeder_cip4_codes:
      - cip4: "31.05"
        note: "Exercise Science — strong anatomy and physiology core"
      - cip4: "26.01"
        note: "Biology — broad pre-health foundation"
      - cip4: "31.01"
        note: "Kinesiology — movement-focused; direct fit"
      - cip4: "51.99"
        note: "Health Sciences — broad pre-health option"
      - cip4: "42.01"
        note: "Psychology — required prereqs sit naturally inside this major"
    context: >
      DPT programs admit applicants from any undergrad major as long as they
      complete prerequisite coursework (anatomy, physiology, biology, chemistry,
      physics, statistics, psychology) and observation hours. The feeders listed
      above embed most of those prereqs in the major itself.

  - credential_id: "jd"
    credential_name_full: "Juris Doctor"
    credential_acronym: "JD"
    socs: ["23-1011", "23-1023"]
    feeder_cip4_codes:
      - cip4: "45.10"
        note: "Political Science — classic pre-law track"
      - cip4: "54.01"
        note: "History — strong reading and writing prep"
      - cip4: "38.01"
        note: "Philosophy — argument and analysis training"
      - cip4: "23.01"
        note: "English — writing and close reading"
      - cip4: "45.06"
        note: "Economics — quantitative and analytical core"
    context: >
      Law school admits applicants from any undergrad major. Bureau of Labor
      Statistics data shows lawyers come from a wide range of feeder fields;
      the listed majors are common entry points but are not requirements.

  # ... 10-13 more entries: MD, DDS, DVM, PharmD, OD, MSW, MS-SLP, MS-Counseling,
  #     MLIS, MS-PA, ... see implementation prompt for the full curated list ...
```

A separate `data/reference/grad_credential_feeders.example.yaml` ships with a single annotated entry for documentation/onboarding.

### Service Changes

#### New module — `backend/app/services/grad_credentials.py`:

```python
"""Grad-credential feeder lookup.

Loads `data/reference/grad_credential_feeders.yaml` at startup and exposes
two read functions for the Set Your Course flow:

- `lookup_credential_for_soc(soc_code)`: given a SOC, return the credential
  entry whose `socs` list contains it (or None).
- `feeder_majors_at_school(unitid, credential_id)`: given a credential and
  a school, return up to 5 feeder majors. Each FeederMajor carries a
  boolean `offered_at_school` derived from the school's reported programs.

Read-only; no Gemma calls; thread-safe (loaded once at startup).
"""

from __future__ import annotations
import threading
import yaml
from pathlib import Path
from app.models.api import FeederMajor, GradCredentialNoticePayload
from app.services import intent  # for _get_school_cips

_REL_YAML_PATH = Path("data/reference/grad_credential_feeders.yaml")
_load_lock = threading.Lock()
_credentials_by_id: dict[str, dict] = {}
_credential_id_by_soc: dict[str, str] = {}
_loaded = False


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    with _load_lock:
        if _loaded:
            return
        # ... load YAML, build indexes ...
        _loaded = True


def lookup_credential_for_soc(soc_code: str) -> dict | None:
    """Return the credential entry whose socs list contains `soc_code`, or None."""
    _ensure_loaded()
    cred_id = _credential_id_by_soc.get(soc_code)
    return _credentials_by_id.get(cred_id) if cred_id else None


def feeder_majors_at_school(
    unitid: int, credential_id: str
) -> list[FeederMajor]:
    """Build the FeederMajor list for the GradCredentialNotice tile.

    Reads the school's reported CIP4 list, intersects with the credential's
    feeder list, and returns up to 5 cards with `offered_at_school` set.
    Always returns at least 3 entries — if fewer than 3 feeders are offered
    at this school, fills from the credential's full feeder list with
    `offered_at_school=False`. The visionary's mockup expects 3-5 cards.
    """
    _ensure_loaded()
    # ... implementation ...


def lookup_credential_by_pre_x_pattern(major_text: str) -> str | None:
    """Pre-flag pattern match. Returns credential_id when major_text is
    a pre-X track, else None.

    Patterns (case-insensitive, applied to normalized input):
      pre-med | premed              -> md
      pre-pt | prept                -> dpt
      pre-law | prelaw              -> jd
      pre-vet | prevet              -> dvm
      pre-dent* | predent*          -> dds
      pre-pa | prepa                -> ms-pa
      pre-optom* | preoptom*        -> od
      pre-pharm* | prepharm*        -> pharmd
    """
    # ... regex match ...
```

#### Updates to `backend/app/services/set_your_course.py`:

**1. New bucket #9 in `_CHIP_ROUTING_SYSTEM_PROMPT`:**

```
9. requires_graduate_credential — the career the student named in the
   clarifier requires graduate or professional school as its entry
   credential. Example: student typed "Marketing" and clarified "I want
   to be a physical therapist." Becoming a physical therapist requires
   a Doctor of Physical Therapy (DPT). The student's question — "what
   undergrad major leads to PT?" — does not have an undergrad answer.
   Action: call `get_occupation_education_requirements` for the SOC the
   clarifier names. If `requires_grad_school` is true, classify as this
   bucket and respond with the credential name (full + acronym),
   citing Bureau of Labor Statistics (BLS) as the source. Do NOT offer
   "alternative undergrad majors that lead to this career" — they don't
   exist. The frontend will render a notice tile from the cta_link
   payload showing typical feeder undergrad majors at the student's
   school. Your prose should NOT enumerate the feeders — the tile does
   that. Keep it to 2-3 sentences naming the credential and the
   reframe.

   IMPORTANT: only fire this bucket when the tool call confirms
   requires_grad_school=true. If education_code is in 3-8 (associate
   through high school), classify as intent_divergence instead — the
   career has an undergrad path; the student just needs a different
   major.
```

**2. New helper in `set_your_course.py`:**

```python
def _build_grad_credential_cta(
    target_soc: str,
    target_career_title: str,
    school_name: str,
    unitid: int,
) -> CtaLink | None:
    """Build the cta_link payload for the requires_graduate_credential bucket.

    Returns None if no credential entry matches the SOC — in which case the
    chip handler should NOT classify the bucket. (Defense-in-depth: the YAML
    is the source of truth for which SOCs the product knows feeders for.)
    """
    cred = grad_credentials.lookup_credential_for_soc(target_soc)
    if cred is None:
        return None
    feeders = grad_credentials.feeder_majors_at_school(unitid, cred["credential_id"])
    if len(feeders) < 3:
        return None  # not enough feeders to render the tile
    payload = GradCredentialNoticePayload(
        credential_id=cred["credential_id"],
        credential_name_full=cred["credential_name_full"],
        credential_acronym=cred["credential_acronym"],
        target_career_title=target_career_title,
        target_soc=target_soc,
        school_name=school_name,
        feeders=feeders,
        tone="caution",
    )
    return CtaLink(
        label=f"How students at {school_name} get to {cred['credential_acronym']} school",
        href="#grad-credential-notice",  # in-page anchor; the tile renders inline
        kind="grad_credential_notice",
        payload=payload,
    )
```

**3. Update `_parse_chip_response` to populate `cta_link` when bucket is `requires_graduate_credential`:**

The chip prompt is required to emit a fourth optional structured tail when this bucket fires:

```
---GRAD_CREDENTIAL_TARGET---
{"target_soc": "29-1123", "target_career_title": "Physical Therapist"}
```

Service layer parses it, calls `_build_grad_credential_cta`, attaches the result to `ChipResponse.cta_link`. If the YAML doesn't have feeders for this SOC, the service downgrades the bucket to `intent_divergence` (so the student still gets a useful response) and logs a warning — keeps the surface honest about its own coverage.

**4. New pre-flag short-circuit at the top of `stream_initial_resolution`:**

```python
async def stream_initial_resolution(
    major_text: str,
    school_name: str,
    unitid: int,
    programs: Sequence[Mapping[str, Any]],
    locale: AppLocale = "en",
) -> AsyncIterator[dict[str, Any]]:
    input_normalized = community_suggestions.normalize_input(major_text)

    # --- Pre-flag: catch "pre-X" tracks before Gemma is called ---
    cred_id = grad_credentials.lookup_credential_by_pre_x_pattern(input_normalized)
    if cred_id is not None:
        # Build a low-confidence IntentResult that points to the
        # closest broad feeder (e.g. pre-PT -> Health Sciences if
        # offered at this school, else Biology). The frontend will
        # render GradCredentialNotice above the streamed prose with
        # tone="info".
        result = _build_pre_flag_result(
            credential_id=cred_id,
            major_text=major_text,
            programs=programs,
        )
        yield {"event": "delta", "data": {"text": _pre_flag_prose(cred_id, school_name)}}
        yield {"event": "structured", "data": result.model_dump()}
        suggestions = community_suggestions.get_suggestions(
            unitid=unitid, input_normalized=input_normalized
        )
        yield {"event": "suggestions", "data": list(suggestions)}
        yield {"event": "done", "data": {}}
        return

    # ... existing Gemma streaming flow unchanged ...
```

`_build_pre_flag_result` picks the broadest feeder offered at the school (using `programs`) and constructs an `IntentResult` with `confidence="low"`, `pre_flag_credential_id=cred_id`, and `careers_preview` populated from the feeder's CIP. `_pre_flag_prose` is a static template per credential ("Pre-PT isn't an undergrad major itself — it's a track toward Doctor of Physical Therapy (DPT) school. The closest matching program at [School] is [Feeder Title].").

#### New MCP handler — `src/mcp_server/futureproof_server.py`:

```python
def _handle_get_occupation_education_requirements(args: dict) -> dict:
    """Return BLS education-requirement signals for one SOC.

    Args:
        soc_code: SOC code in XX-XXXX format.

    Returns:
        {
          "soc_code": "29-1123",
          "occupation_title": "Physical Therapists",
          "education_code": 1,
          "education_level_name": "Doctoral or professional degree",
          "requires_grad_school": True,  # education_code in (1, 2)
        }
        Or {"error": "soc_not_found"} when the SOC isn't in
        consumable.occupation_profiles.
    """
    soc_code = str(args.get("soc_code", "")).strip()
    if not re.fullmatch(r"\d{2}-\d{4}", soc_code):
        return {"error": "invalid_soc_format"}
    # ... DuckDB query ...
```

Tool registration follows the same pattern as `get_career_paths` (OpenAI schema in `_OPENAI_TOOL_SCHEMAS`, dispatcher entry in `_handle_tool_call`).

### Pipeline Integration

None. Read-only feature on existing `consumable.occupation_profiles`. The YAML is reference data; the new tool is a thin DB read.

### Testing Impact Analysis

#### Existing Tests at Risk

**None.** This spec is purely additive:
- Existing `test_set_your_course.py` tests don't exercise the pre-flag path (no `pre_flag_credential_id` field today; default is None).
- Existing chip tests cover 8 buckets; this adds a 9th and doesn't change the parsing of the 8.
- `IntentResult` extension is additive; existing serializers ignore the new field.
- New MCP tool is registered alongside existing ones; no existing handler changes.

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `backend/tests/services/test_set_your_course.py` | All existing | **None** | New bucket added; existing assertions on 8 buckets unchanged. |
| `backend/tests/mcp/test_*.py` | All existing MCP tests | **None** | New tool added; existing tools unchanged. |
| `backend/tests/services/test_intent.py` | All | **None** | `resolve_intent` (legacy /school flow) untouched. |
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | All existing | **None** | New render slot is conditional; absent fields render the same as today. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `backend/tests/services/test_set_your_course.py` | Add `TestRequiresGradCredential` class. Existing classes untouched. | New bucket coverage. |
| `frontend/src/hooks/useSetYourCourse.test.ts` | Add `TestGradCredentialSelector` block. | New derived selector. |
| `frontend/src/types/buildInput.ts` test fixtures | Add `pre_flag_credential_id: null` defaults | Type extension. |

#### Confirmed Safe

If any of these fail, STOP and escalate:

- `backend/tests/services/test_set_your_course.py::TestChipDispatch::*`
- `backend/tests/services/test_set_your_course.py::TestStreamInitial::*`
- `backend/tests/services/test_set_your_course.py::TestConfirmedFocus::*`
- `backend/tests/services/test_correction_log.py::*`
- `backend/tests/services/test_intent.py::*`
- `backend/tests/mcp/test_cip_substitution_integration.py::*`
- `frontend/src/screens/SchoolMajorScreen.test.tsx::*`
- `frontend/src/screens/RevealScreen.test.tsx::*`

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `test_grad_credentials.py` | `TestYAMLLoad::test_loads_all_credentials` | YAML loads; ≥10 credential entries present; all required fields populated. |
| P0 | `test_grad_credentials.py` | `TestYAMLLoad::test_corrupt_yaml_raises_at_startup` | A malformed YAML raises clearly at app boot, doesn't silently degrade. |
| P0 | `test_grad_credentials.py` | `TestSocLookup::test_lookup_credential_for_known_soc` | DPT SOC (29-1123) → credential_id="dpt". |
| P0 | `test_grad_credentials.py` | `TestSocLookup::test_lookup_unknown_soc_returns_none` | SOC not in YAML → None. |
| P0 | `test_grad_credentials.py` | `TestPreXMatch::test_pre_pt_matches_dpt` | "pre-PT" / "prept" / "pre PT" all → "dpt". |
| P0 | `test_grad_credentials.py` | `TestPreXMatch::test_pre_med_matches_md` | "pre-med" / "premed" → "md". |
| P0 | `test_grad_credentials.py` | `TestPreXMatch::test_non_pre_x_returns_none` | "biology", "exercise science", "marketing" → None. |
| P0 | `test_grad_credentials.py` | `TestPreXMatch::test_partial_word_does_not_match` | "premiere" does NOT match "pre-med"; "prequel" does not match "pre-q"; precise word-boundary matching. |
| P0 | `test_grad_credentials.py` | `TestFeeders::test_returns_3_to_5_feeders` | Always returns 3–5 feeders; never 0, 1, or 2. |
| P0 | `test_grad_credentials.py` | `TestFeeders::test_offered_at_school_flag_correct` | Feeder offered at school → True; not offered → False. |
| P0 | `test_grad_credentials.py` | `TestFeeders::test_unknown_credential_returns_empty` | Unknown credential_id → []. |
| P0 | `test_education_requirements.py` (MCP) | `test_returns_education_for_known_soc` | DPT SOC → education_code=1, requires_grad_school=True. |
| P0 | `test_education_requirements.py` (MCP) | `test_returns_education_for_undergrad_soc` | Software Developer SOC → education_code=5, requires_grad_school=False. |
| P0 | `test_education_requirements.py` (MCP) | `test_invalid_soc_format_returns_error` | "11_2021" → error. |
| P0 | `test_education_requirements.py` (MCP) | `test_unknown_soc_returns_error` | Real-shape SOC not in DB → soc_not_found. |
| P0 | `test_set_your_course.py` | `TestRequiresGradCredential::test_chip_bucket_fires_when_career_is_grad_only` | Mocked Gemma classifies clarifier "I want to be a PT" as `requires_graduate_credential`; service builds the cta_link. |
| P0 | `test_set_your_course.py` | `TestRequiresGradCredential::test_chip_bucket_does_not_fire_for_undergrad_career` | Mocked Gemma classifying "I want to be a software developer" as `requires_graduate_credential` is rejected (degraded to intent_divergence) because tool returned requires_grad_school=False. |
| P0 | `test_set_your_course.py` | `TestRequiresGradCredential::test_chip_bucket_degrades_when_yaml_has_no_feeders` | Bucket=requires_graduate_credential but YAML doesn't have the SOC → bucket downgrades to intent_divergence; warning logged. |
| P0 | `test_set_your_course.py` | `TestRequiresGradCredential::test_pre_flag_pre_pt_short_circuits_gemma` | major_text="pre-PT" → no Gemma call; structured event carries `pre_flag_credential_id="dpt"`. |
| P0 | `test_set_your_course.py` | `TestRequiresGradCredential::test_pre_flag_pre_med_short_circuits_gemma` | major_text="premed" → no Gemma call; `pre_flag_credential_id="md"`. |
| P0 | `test_set_your_course.py` | `TestRequiresGradCredential::test_pre_flag_does_not_fire_for_normal_major` | major_text="biology" → normal Gemma streaming flow; `pre_flag_credential_id=None`. |
| P0 | `test_set_your_course.py` | `TestRequiresGradCredential::test_chip_does_not_set_pre_flag_credential_id` | Chip dispatch updates never set `pre_flag_credential_id`; the field is initial-resolution-only. |
| P0 | `test_set_your_course.py` | `TestRequiresGradCredential::test_feasibility_mode_not_in_community_suggestions` | A correction log row with feasibility_mode=requires_grad_school does NOT count toward `community_suggestions.get_suggestions`. |
| P1 | `test_set_your_course.py` | `TestRequiresGradCredential::test_chip_response_carries_grad_credential_payload` | ChipResponse.cta_link.payload is a GradCredentialNoticePayload with valid feeders. |
| P1 | `test_set_your_course.py` | `TestRequiresGradCredential::test_acronym_spell_out_in_prose` | Gemma's prose contains "Doctor of Physical Therapy (DPT)" on first reference. (Snapshot-style assertion on canned response.) |
| P0 | `GradCredentialNotice.test.tsx` | `test_renders_caution_tone_for_chip_path` | tone="caution" → caution-stripe class applied. |
| P0 | `GradCredentialNotice.test.tsx` | `test_renders_info_tone_for_pre_flag_path` | tone="info" → info-stripe class applied. |
| P0 | `GradCredentialNotice.test.tsx` | `test_feeder_card_tap_swaps_resolution` | Tap on feeder card → calls onAcceptFeeder with the cip4. |
| P0 | `GradCredentialNotice.test.tsx` | `test_feeder_offered_at_school_visual_diff` | Feeders with offered_at_school=False render with a "not offered here" subtle indicator. |
| P0 | `useSetYourCourse.test.ts` | `TestGradCredentialSelector::test_pre_flag_path_returns_payload` | Initial resolution with `pre_flag_credential_id` set → selector returns a payload with tone="info". |
| P0 | `useSetYourCourse.test.ts` | `TestGradCredentialSelector::test_chip_path_returns_payload` | Chip response with cta_link.kind="grad_credential_notice" → selector returns its payload with tone="caution". |
| P0 | `useSetYourCourse.test.ts` | `TestGradCredentialSelector::test_no_signal_returns_null` | Neither signal present → selector returns null. |
| P1 | `useSetYourCourse.test.ts` | `TestGradCredentialSelector::test_chip_signal_overrides_stale_pre_flag` | If both signals exist (pre-flag set AND last chip carries cta_link), the chip path wins. |
| P2 | `SetYourCourseScreen.test.tsx` | `test_notice_tile_renders_above_career_preview` | DOM order: notice tile precedes the career-tier section. |

#### Test Data Requirements

- Mocked YAML fixture `tests/fixtures/grad_credential_feeders_test.yaml` with 3 entries (DPT, JD, MD) covering the lookup paths.
- Mocked Gemma chip-response fixtures: (a) `requires_graduate_credential` bucket + valid `---GRAD_CREDENTIAL_TARGET---` tail; (b) bucket fired but tool returned requires_grad_school=False (degradation case); (c) bucket fired but YAML has no feeders for the SOC (degradation case); (d) malformed `---GRAD_CREDENTIAL_TARGET---` JSON.
- Mocked MCP `get_occupation_education_requirements` fixture for DPT (29-1123, code=1), Software Developer (15-1252, code=5), and an unknown SOC.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** COMPLETE
**Reviewed:** 2026-05-05

#### System Context

This feature inserts a new decision branch at the Set Your Course resolution layer -- both at initial-resolution time (pre-flag short-circuit) and at chip-dispatch time (new bucket classification). It touches five layers: the existing Gold zone table `consumable.occupation_profiles` (read-only), the MCP tool surface (new handler), a curated YAML reference file, the backend Set Your Course service (prompt + routing logic), and the frontend render path. The data flow is additive -- no existing contracts change shape, and the build engine remains untouched.

#### Data Flow Analysis

**Pre-flag path:**
1. Student types "pre-PT" in major input field
2. Frontend POSTs to `/intent/stream`
3. `stream_initial_resolution` calls `community_suggestions.normalize_input` (existing)
4. New: regex match via `grad_credentials.lookup_credential_by_pre_x_pattern(input_normalized)` -- pure in-memory, no DB call
5. Short-circuit: `_build_pre_flag_result` constructs an `IntentResult` with `pre_flag_credential_id="dpt"`, picks the broadest feeder offered at school from the YAML
6. Emits delta/structured/suggestions/done events in the existing SSE shape
7. Frontend reads `pre_flag_credential_id` on the structured event, renders `GradCredentialNotice` with tone="info"

**Chip path:**
1. Student types "Marketing", resolves normally, taps "Not what I expected", clarifier says "I want to be a physical therapist"
2. Frontend POSTs to `/intent/chip`
3. `handle_chip_dispatch` formats `_CHIP_ROUTING_SYSTEM_PROMPT` with bucket 9
4. Gemma calls `get_occupation_education_requirements(soc_code="29-1123")` via tool-calling loop
5. MCP handler reads `consumable.occupation_profiles` WHERE soc_code=29-1123, returns `{requires_grad_school: true}`
6. Gemma classifies bucket as `requires_graduate_credential`, emits `---GRAD_CREDENTIAL_TARGET---` tail
7. Service parses the 4th tail, calls `_build_grad_credential_cta`, builds `GradCredentialNoticePayload`
8. Response carries `ChipResponse.cta_link` with `kind="grad_credential_notice"` and `payload`
9. Frontend reads `cta_link.kind`, renders `GradCredentialNotice` with tone="caution"

Both paths converge at the same frontend component. Data crosses the API boundary exactly once per path, and the shape is fully typed (Pydantic on the backend, TypeScript interface on the frontend).

#### Contract Review

**Pydantic models -- backwards compatibility:**
- `FeasibilityMode` Literal: adding `"requires_grad_school"` to the union is backwards-compatible. Existing code that pattern-matches on the 5 existing values will simply never encounter the new value until it is explicitly dispatched. The `CommitRequest.feasibility_mode` is typed as `FeasibilityMode | None` -- clean.
- `ChipBucket` Literal: adding `"requires_graduate_credential"` is safe. The existing `_parse_bucket` function in `set_your_course.py` uses a hardcoded `allowed` tuple that must be updated in lockstep -- the spec correctly identifies this file. No external consumers pattern-match exhaustively on this type.
- `CtaLink` extension with `kind` and `payload` fields: both have defaults (`kind` defaults to `"school_discovery_v05"`, `payload` defaults to `None`), so serialization of existing `CtaLink` instances (if any were ever constructed) would not break. In practice, `cta_link` is always `None` today -- the `school_gap` bucket promises it in the prompt but never populates it. The new usage will be the first real population of this field.
- `IntentResult.pre_flag_credential_id: str | None = None` is additive with a default. Existing serialized `IntentResult` objects round-trip cleanly.

**Frontend TypeScript types:**
- The existing `CtaLink` interface in `frontend/src/api/intent.ts` has only `href` and `label`. The spec adds `kind` and `payload`. This must be updated with optional fields to maintain backward compat with the existing `cta_link: CtaLink | null` shape on `ChipResponse`.
- `IntentResult` in `frontend/src/types/buildInput.ts` needs the new optional `pre_flag_credential_id` field.

**MCP tool schema:**
- `get_occupation_education_requirements` takes one required string arg (`soc_code`) and returns a flat dict. Matches the existing handler pattern exactly (see `_handle_get_ai_exposure`, `_handle_get_occupation_data`). The return schema is small enough for Gemma e4b to parse reliably.
- Registration in `get_tools()` follows the same `ToolDef(name=..., description=..., input_schema=..., handler=...)` pattern.

#### Findings

##### Sound

1. **Zone boundaries are clean.** The new MCP tool reads from `consumable.occupation_profiles` (Gold zone, read-only) -- same table the existing `get_occupation_data` tool uses. No pipeline changes required.

2. **Separate tool is the right call.** Decision #9's reasoning is architecturally sound: a single-purpose tool (`get_occupation_education_requirements`) with one input and a small return dict gives Gemma 4 e4b the best function-calling reliability on Ollama. Adding fields to `get_occupation_data` would balloon the 25-field response dict and strain the context window for no benefit.

3. **The pre-flag short-circuit is architecturally clean.** It sits at the top of `stream_initial_resolution`, before any Gemma call or DB query. No race conditions: the function is an `async def` but the pre-flag path is synchronous (YAML lookup + list intersection + static prose template). The existing event contract (delta -> structured -> suggestions -> done) is preserved identically.

4. **YAML-at-startup with double-check lock matches the existing pattern.** The MCP server already uses this exact pattern for `_engine_init_lock` (line 607 of `futureproof_server.py`). The `grad_credentials` module's `_ensure_loaded` / `_load_lock` / `_loaded` triple mirrors it. Thread-safe for the FastAPI/uvicorn async+thread-pool model.

5. **Cacheability posture is correct.** `community_suggestions._CACHEABLE_MODES` is a frozen set of `{"direct_hit", "crosswalk_quirk", "adjacent_reachable"}`. The new `requires_grad_school` mode is excluded by omission -- no code change needed in `community_suggestions.py` to enforce exclusion.

6. **The 4th structured tail (`---GRAD_CREDENTIAL_TARGET---`) is parsed by the service layer, not the frontend.** This keeps the Gemma output contract between the backend and Gemma's structured response, never leaking to the wire. The frontend only sees the fully-typed `GradCredentialNoticePayload` on `cta_link.payload`.

7. **Build engine unchanged.** The notice is guidance at the resolution layer. Pentagon stats, boss fights, and branches continue to work normally for grad-only SOCs. This is consistent with Decision #6 and the product's "soft guidance > hard gating" philosophy.

##### Concerns

- **[C1] `_parse_bucket` hardcoded allowed tuple needs sync.** The existing `_parse_bucket` at line 993 of `set_your_course.py` uses a hardcoded `allowed: tuple[ChipBucket, ...]` that only lists 8 values. When adding bucket 9, this tuple MUST be updated in lockstep or the new bucket will silently be discarded (returns `None`). The spec's file changes table lists `set_your_course.py` as modified, which is correct, but the specific line in `_parse_bucket` is not called out explicitly. **Impact:** If missed, every `requires_graduate_credential` classification from Gemma would be swallowed as `None`, and the cta_link would never be populated. **Recommendation:** Implementation MUST add `"requires_graduate_credential"` to the `allowed` tuple at line 998. Low risk since the spec author clearly understands the flow; noting for the implementer's checklist.

- **[C2] Frontend `CtaLink` interface extension needs `kind` and `payload` as optional.** The existing `CtaLink` type at `frontend/src/api/intent.ts:32-35` only has `href` and `label`. The spec adds `kind: Literal["school_discovery_v05", "grad_credential_notice"]` and `payload: GradCredentialNoticePayload | null`. These MUST be optional (with `?:`) in the TypeScript interface so the existing `cta_link: CtaLink | null` check pattern doesn't break for callers that receive the old shape from responses already in flight during a rolling deploy. **Impact:** Type error on deploy if not optional. **Recommendation:** Define as `kind?: "school_discovery_v05" | "grad_credential_notice"` and `payload?: GradCredentialNoticePayload | null` in the TypeScript type. Defensively default `kind` to `"school_discovery_v05"` in the selector logic when absent.

- **[C3] `_build_pre_flag_result` needs access to school's CIP list.** The spec's pseudocode for the pre-flag short-circuit calls `_build_pre_flag_result(credential_id, major_text, programs)` and uses `programs` (the frontend-forwarded list) to determine which feeder is offered at the school. However, looking at the existing `stream_initial_resolution` flow, `programs` is a `Sequence[Mapping[str, Any]]` forwarded from the frontend's cached program list. This is the right source (it's the same list used to derive `parent_cip`). Just confirming: `feeder_majors_at_school` should compare CIP4 codes from the YAML against `programs[*]["cipcode"][:5]` -- not against the MCP `get_school_programs` result, which would require a DB query. The spec's description at `feeder_majors_at_school` says "reads the school's reported CIP4 list, intersects with the credential's feeder list" -- this should use the `programs` list passed in from the frontend, or `intent._get_school_cips(unitid)` for consistency with how `stream_initial_resolution` already fetches the school's catalog. **Impact:** Minor -- if the wrong list is used, `offered_at_school` flags could be inaccurate. **Recommendation:** Use `intent._get_school_cips(unitid)` inside `feeder_majors_at_school` (same source the existing resolution uses) rather than passing `programs` through. This is more reliable since `programs` depends on what the frontend cached.

- **[C4] The `GradCredentialNoticePayload.feeders` field has `min_length=3`.** The `_build_grad_credential_cta` helper already guards `if len(feeders) < 3: return None` -- good. But `_build_pre_flag_result` on the initial-resolution path also needs to handle the case where no credential entry yields 3+ feeders gracefully (fall through to normal Gemma resolution instead of erroring). The spec doesn't explicitly state what happens when the pre-flag path can't assemble 3 feeders. **Impact:** If a regex-matched credential (e.g. pre-PA) has fewer than 3 feeders in the YAML, the pre-flag short-circuit would either error or produce an invalid payload. **Recommendation:** In `_build_pre_flag_result`, if `feeder_majors_at_school` returns fewer than 3 entries, fall through to the normal Gemma streaming flow (do not short-circuit). Log a warning.

- **[C5] The chip flow needs the new tool added to the tools list in `handle_chip_dispatch`.** Today, `handle_chip_dispatch` passes a single tool schema (`get_career_paths`) to `generate_with_tools_loop`. The new bucket requires Gemma to call `get_occupation_education_requirements`. The spec says "Tool registered in `mcp_client.get_tool_openai_schema`" and "listed in the chip-routing prompt's tool surface" -- but the implementation must update the `tools=[tool_schema]` list at line 846 to include both schemas: `[tool_schema_career_paths, tool_schema_education_req]`. Without this, Gemma cannot actually invoke the new tool during a chip dispatch. **Impact:** Blocker if missed -- Gemma would reference a tool it cannot call, hallucinate a response, and potentially mis-classify. **Recommendation:** Update `handle_chip_dispatch` to pass both tool schemas in the `tools` list. The `_dispatch` function already handles arbitrary tool names via `mcp_client.call_async(tool_name, tool_args)`.

##### Blockers

None. The architecture is sound, additive, and respects all existing contracts.

#### Verdict
- [x] APPROVED

#### Conditions

None required -- all concerns above are implementer-level details that don't require spec revision. C1-C5 are noted for the implementation phase. The architecture is clean.

### @fp-data-reviewer Review
**Status:** APPROVED
**Reviewed:** 2026-05-05

#### Data Sources Affected

- **consumable.occupation_profiles** (Gold zone, read-only). Fields consumed: `soc_code`, `occupation_title`, `education_code`, `education_level_name`. No write, no schema change.
- **New curated YAML** (`data/reference/grad_credential_feeders.yaml`). Not a pipeline source; hand-curated reference keyed by credential. Analogous to the existing `data/reference/major_to_cip.yaml` in shape, but serving a different purpose (credential-to-feeder, not input-to-CIP resolution).

#### Crosswalk Impact

None. This feature reads directly from `occupation_profiles` by SOC code. No CIP-to-SOC crosswalk is traversed by the new MCP tool or the YAML lookup. The feeder CIP4 codes in the YAML are presented as "common undergrad majors," not as crosswalk-derived career paths. No confidence tiers are involved in this data path.

#### Formula Verification

No stat formulas are changed. The `education_code IN (1, 2)` rule is a boolean classification (grad-only vs. not), not a stat computation. Pentagon stats, boss fights, and branch data remain untouched.

#### Findings

##### Data Quality Sound

1. **`education_code` field is reliable and fully populated.** Verified against the live Gold zone data (`consumable/occupation_profiles` Iceberg table, snapshot of 2026-04-07). 832 unique SOC codes, zero NULLs on `education_code`. Distribution: code 1 (Doctoral/professional) = 146 occupations, code 2 (Master's) = 40, code 3 (Bachelor's) = 356, code 4 (Associate's) = 96, code 5 (Postsecondary nondegree) = 102, code 6 (Some college) = 14, code 7 (High school) = 652, code 8 (No credential) = 218. This is the BLS's own "typical entry-level education" classification. It is the authoritative source for this question.

2. **Spot-check of grad-only SOCs passes cleanly.** Every SOC referenced in the spec's YAML maps correctly:
   - 29-1123 (Physical Therapists) = code 1, confirmed DPT required.
   - 23-1011 (Lawyers) = code 1, confirmed JD required.
   - 23-1023 (Judges) = code 1, confirmed.
   - 29-1131 (Veterinarians) = code 1, confirmed DVM required.
   - 29-1051 (Pharmacists) = code 1, confirmed PharmD required.
   - 29-1041 (Optometrists) = code 1, confirmed OD required.
   - 29-1071 (Physician Assistants) = code 2, confirmed MS-PA required.
   - 29-1127 (Speech-Language Pathologists) = code 2, confirmed MS-SLP required.
   - 25-4022 (Librarians) = code 2, confirmed MLIS required.

3. **No duplicate SOC codes in the table.** The new tool's `WHERE soc_code = ?` query will always return exactly 0 or 1 rows. Safe for the single-result contract.

4. **Cacheability exclusion confirmed.** `community_suggestions._CACHEABLE_MODES` (line 35 of `community_suggestions.py`) is `frozenset({"direct_hit", "crosswalk_quirk", "adjacent_reachable"})`. The filtering at line 83 rejects any mode not in the set by returning early. The new `requires_grad_school` mode is excluded by omission with zero code changes required. This matches `school_gap` and `genuinely_impossible` posture exactly.

5. **The `education_code IN (1, 2)` rule is correctly scoped.** BLS codes 1-2 represent occupations where the BLS has determined that the *typical entry-level education* is graduate-level. This is not "some people get a Master's" -- it is "the BLS says you typically need one to enter." Verified edge cases:
   - Accountants/Auditors (13-2011) = code 3 (Bachelor's). Despite CPA 150-hour rules, BLS codes entry-level accountancy as Bachelor's. The tool correctly returns `requires_grad_school=False`. No false positive.
   - Registered Nurses (29-1141) = code 3 (Bachelor's). Only advanced-practice nurses (NP/CRNA/Midwife) are code 2. Correct.
   - Data Scientists (15-2051) = code 3 (Bachelor's). Statisticians (15-2041) = code 2. BLS correctly distinguishes.
   - Operations Research Analysts (15-2031) = code 3. Correct.

##### Data Concerns

- **[D1] Code 2 (Master's) inclusion is appropriate but merits a nuance for Mathematicians/Statisticians.** The 40 code-2 occupations include some that a student might plausibly approach via a Bachelor's track (e.g., Mathematicians 15-2021, Statisticians 15-2041, Economists 19-3011). In practice, BLS codes these as Master's because *typical entry* requires one. However, unlike DPT/JD/MD where the credential is legally required for licensure, Master's-required occupations often have "exceptional candidates with Bachelor's + experience" as an alternate entry path. **Risk:** A student who types "pre-statistics" (if the regex matched it, which it does not) would see a grad-school notice for an occupation where some people do enter with a Bachelor's. **Mitigation already present in spec:** (a) The YAML is curated per-credential, so only credentials the curator explicitly includes will fire the tile. If "MS-Statistics" is never added to the YAML, the chip flow will degrade to `intent_divergence` (safe fallback). (b) The pre-flag regex only matches the 8 well-known "pre-X" patterns (pre-med, pre-PT, pre-law, etc.) -- not "pre-statistics" or "pre-economics." The combination of YAML curation + narrow regex keeps this tight. **Verdict:** No change needed; the spec's design already handles this edge case via the YAML's gating role.

- **[D2] Dentists SOC code for YAML implementation.** The spec's YAML example only shows DPT and JD entries in detail. During implementation, the DDS credential should use SOC `29-1021` (Dentists, general) and/or `29-1029` (Dentists, all other specialists). Both are code 1 in the live data. Just noting for the implementor.

- **[D3] Social Workers split across education codes.** The social work credential surface is split: Healthcare Social Workers (21-1022) and Mental Health/Substance Abuse Social Workers (21-1023) are code 2 (Master's required -- MSW). But Child/Family/School Social Workers (21-1021) and Social Workers All Other (21-1029) are code 3 (Bachelor's). When the YAML adds the MSW credential entry, its `socs` list should only include the code-2 SOCs (21-1022, 21-1023), NOT the code-3 ones. The tool call will correctly return `requires_grad_school=True` for those SOCs and `False` for 21-1021/21-1029. This is already handled by the spec's design (the tool checks the specific SOC the student named, not a family), but calling it out because it's the exact "ambiguous credential" edge case the reviewer brief asked about.

##### Data Integrity Blockers

None. The data signal is authoritative (BLS), fully populated (zero NULLs), correctly codes the target occupations, and the classification rule (`IN (1, 2)`) aligns with the BLS's own definition of "typical entry-level education is graduate school."

#### Disclaimer Check
- [x] AI-estimated values labeled -- N/A; no AI-estimated data in this feature. All signals come from BLS `education_code` (observed/authoritative). The YAML is hand-curated, not Gemma-generated.
- [x] Confidence scores propagated where crosswalk < Tier 2 -- N/A; no crosswalk traversal in this data path.
- [x] Required disclaimer strings present in UI for this data path -- The spec requires citing "Bureau of Labor Statistics (BLS)" on first reference in the notice tile copy. Correct; this is observed federal data.
- [x] Missing data states handled (not blank, not $0, not misleading) -- The tool returns `{"error": "soc_not_found"}` for unknown SOCs. The `_build_grad_credential_cta` returns `None` (downgrades to `intent_divergence`) if YAML has no feeders. The `_build_pre_flag_result` should fall through to normal Gemma flow if fewer than 3 feeders (per @fp-architect C4). No zero/blank/misleading states reach the student.

#### YAML-as-Data-Source Assessment

Acceptable for hackathon scope. Rationale:

1. **Different purpose than major_to_cip.yaml.** The project memory "No YAML lookups" explicitly targets YAML-based *major-to-CIP resolution*. The new YAML is *credential-to-feeder-CIP* reference data -- it does not participate in the resolution pipeline. It gates a notice tile, not a CIP assignment.
2. **Small, stable, curated.** 10-15 entries, each with 5-8 feeders = ~100 total mappings. Changes when BLS reclassifies an occupation or a new professional degree is created (rarely). Human curation is the correct approach for data this small and this consequential.
3. **No runtime generation risk.** The spec correctly rejects Gemma-generated feeders (Decision #4) because instability in the feeder list would confuse students. The YAML is deterministic.
4. **Git-committed is appropriate.** The data is not sensitive, changes slowly, and benefits from PR-review-able diffs. A governance file would be structurally identical but add ceremony without benefit at hackathon scope.
5. **Precedent exists.** `data/reference/major_to_cip.yaml` (2367 lines) is already committed to git and loaded at startup by `backend/app/services/major_lookup.py` using the same double-check-lock pattern the new module proposes.

#### Verdict
- [x] APPROVED

### @genai-architect Review
**Status:** COMPLETE

Reviewer to focus on:
1. Bucket-9 prompt addition — does the inline example (PT) sufficiently disambiguate from `intent_divergence`? Should the prompt include a counter-example ("Marketing → Software Developer is intent_divergence, NOT requires_graduate_credential")?
2. The `---GRAD_CREDENTIAL_TARGET---` 4th tail — does adding a 4th tail strain Gemma 4 e4b's structured-output reliability on Ollama? (Existing 3 tails: UPDATED_RESOLUTION, BUCKET, CONFIRMED_FOCUS.)
3. Pre-flag heuristic completeness — should the pattern list include "pre-physical-therapy" / "pre-physical therapy" alongside "pre-PT"? Where does the regex draw the line between robust matching and false positives?
4. The chip-prompt rule "do NOT enumerate feeders in prose, the tile does that" — is a 2-sentence prose response feasible at temp=0.2 without Gemma drift into explaining feeders inline?

#### Findings

**Reviewed:** `backend/app/services/set_your_course.py` (chip routing prompt, `_parse_chip_response`, `_cut_at`, `_parse_bucket`), `docs/specs/feature-requires-graduate-credential.md` §1–§4.

---

**Finding 1 — Bucket-9 example does NOT sufficiently disambiguate from `intent_divergence`. A counter-example is required.**

The current bucket-9 prompt uses only the PT example. The decision boundary between `requires_graduate_credential` and `intent_divergence` is subtle and Gemma 4 e4b is likely to conflate them for careers that sound grad-credential-adjacent but are not (e.g. "I want to be a nurse" — most RN paths are bachelor's programs, education_code 5, NOT grad-only). More critically, the boundary case the spec itself calls out in §1 — the "Bio major says they want to be a doctor" case — introduces a routing direction that runs *counter* to every example of `intent_divergence` in the existing prompt. The existing `intent_divergence` description says "OFFER alternative majors that lead to the clarified career." For Biology→Doctor the model has been trained (via the existing prompt) to offer alternatives. The new bucket asks it to do the opposite — affirm the current major and announce a grad credential. That is a hard reversal of the bucket's action contract that one example cannot establish.

**Required change:** Add two sentences to bucket-9's description that state the action contrast explicitly, and add one counter-example inline:

```
   COUNTER-EXAMPLE: student typed "Marketing" and clarified "I want
   to be a software developer." Software Developer (education_code 5,
   Bachelor's typical) is NOT a grad-only career — classify as
   intent_divergence and offer alternative majors. Only classify as
   requires_graduate_credential when get_occupation_education_requirements
   returns requires_grad_school=true.

   FEEDER-TRACK CASE: when the student's currently-resolved major IS a
   known pre-professional track for a grad credential (e.g. Biology for
   Medicine, Exercise Science for DPT), do NOT offer alternative majors.
   Instead, confirm the current major is a reasonable path and announce
   that the target career requires the graduate credential. This is
   requires_graduate_credential, not intent_divergence.
```

The two sentences about the feeder-track case also close the open design question in §1 Success Criteria (last bullet). Without them the model has no way to distinguish "Biology → Doctor: student is on track, announce DPT school" from "Marketing → Doctor: student needs a different major" — both look like `intent_divergence` from the perspective of the existing prompt.

**Finding 2 — The `---GRAD_CREDENTIAL_TARGET---` 4th tail introduces real structured-output reliability risk on Ollama/e4b. The spec requires a mitigation plan before implementation.**

The existing three-tail contract (`---UPDATED_RESOLUTION---`, `---BUCKET---`, `---CONFIRMED_FOCUS---`) is already at the edge of what Gemma 4 e4b reliably produces at max_tokens=600 on Ollama. The `_cut_at` implementation in the current code has a hardcoded sentinel list — line 981 iterates `(_UPDATED_TAIL, _BUCKET_TAIL, _CONFIRMED_TAIL)`. Adding a 4th tail requires updating that list; failing to do so means `_cut_at` will not properly fence the new tail's JSON body from bleeding into adjacent tail bodies when Gemma emits them out of order or without separating newlines.

Two additional reliability concerns:

**2a. Token budget.** The chip prompt currently sets `max_tokens=600`. The 4th tail adds roughly 50–70 tokens of structured JSON (`{"target_soc": "29-1123", "target_career_title": "Physical Therapist"}`). Combined with the 2–4 sentence prose requirement, at 600 tokens there is no room for the full output when the model also emits the `---GRAD_CREDENTIAL_TARGET---` tail after the existing three. This will produce truncated JSON on Ollama regularly. Recommendation: raise `max_tokens` to 800 for the `not_expected` chip path, or shorten the 4th tail to a single compact object.

**2b. Tail ordering.** The spec does not specify where `---GRAD_CREDENTIAL_TARGET---` should appear in the output ordering relative to the other tails. The existing prompt format spec says: `---UPDATED_RESOLUTION---` (optional), then `---BUCKET---` (always), then `---CONFIRMED_FOCUS---` (conditional). If `---GRAD_CREDENTIAL_TARGET---` is placed before `---BUCKET---`, `_cut_at`'s fence-stopping logic will incorrectly fence the new marker against the `---BUCKET---` sentinel (which it does not know about) and may drop content. The 4th tail must be positioned AFTER `---BUCKET---` in the format spec and added to the sentinel list in `_cut_at`.

**Required change:** The spec's format section must (a) state explicit ordering, (b) mandate raising `max_tokens` to 800 for this path, and (c) the implementation must update the `_cut_at` sentinel list and `_parse_chip_response` to handle the 4th tail.

**Alternative to consider:** Instead of a 4th tail, the implementation could parse `target_soc` out of the tool-call log that `generate_with_tools_loop` already returns. If Gemma called `get_occupation_education_requirements` with the correct SOC, `tool_call_log[0].args["soc_code"]` already carries the SOC. This eliminates the 4th tail entirely — the service reads the SOC from the tool log, constructs the `cta_link` from that, and the prompt only needs to emit `---BUCKET---` with the new value. This alternative is strongly preferred on reliability grounds.

**Finding 3 — The pre-flag regex is incomplete for spelled-out forms of "physical therapy" and "physician assistant." The spec draws the right line but needs one clarification and one addition.**

The spec's regex `^pre-?(med|pt|law|vet|dent\w*|pa\b|optom\w*|pharm\w*)\b` has two gaps:

**3a. "pre-physical therapy" and "pre-physical-therapy"** — these are common typed inputs at 17-word-per-minute hunt-and-peck speed. The spec's open question in §10 acknowledges this but defers it. The deferral is defensible for the hackathon — adding spelled-out forms triples the regex complexity and adds false-positive risk against inputs like "pre-pharmacy technician." Confirming the deferral: the hackathon regex should stay as specified. However, the spec should add `pre-physical-therapy` to the §10 v2 expansion list so it does not get lost.

**3b. "pre-pa" vs "pre-physician-assistant"** — the `\bpa\b` segment matches "pre-pa" correctly but the word-boundary `\b` combined with the leading `pre-?` anchor means "prepa" (no hyphen) does NOT match the `\bpa\b` form because there is no word boundary between "pre" and "pa" in "prepa." The spec's `lookup_credential_by_pre_x_pattern` docstring shows "pre-pa | prepa" both claimed to route to `ms-pa`, but the regex `pre-?(pa\b)` will not match "prepa" — it matches "pre-pa" and "prepa" only if the boundary check passes, which it does not for "prepa" without a trailing boundary character. This is a bug in the regex as specified.

**Required change:** The regex for the PA case must be restructured. Recommended replacement for the PA segment: `pre-?p\.?a\.?\b` to capture "pre-pa", "prepa", "pre-P.A.", case-insensitively. Alternatively, handle "pa" as a special-case with its own alternation arm. The test case `test_pre_pt_matches_dpt` tests "prept" (no hyphen) — verify the regex handles the no-hyphen case uniformly across all alternation arms.

**3c. "pre-med" vs "pre-medicine"** — "pre-medicine" and "premedicine" are less common but present in typed inputs. The `med\b` alternation arm correctly captures "pre-med" and "premed" but would not capture "pre-medicine" or "premedicine" because `med\b` requires a word boundary immediately after "med." This is acceptable for the hackathon given Decision #7's rationale, but confirm in the P0 test `test_partial_word_does_not_match` that "premedieval" and "premeditate" do NOT match — these would be false positives on the current `med` arm without a strict boundary. The test name suggests this is already covered; make sure the fixture data includes these.

**Finding 4 — The "do NOT enumerate feeders in prose" instruction is feasible at temp=0.2 but requires explicit negative reinforcement in the prompt to hold.**

The existing chip prompt already demonstrates that Gemma 4 e4b at temp=0.2 respects the "2–4 sentences" instruction reliably across the existing 8 buckets (this is confirmed by the fact that `debug_trace` is used as-is by the frontend without post-processing for length). However, the "do NOT enumerate feeders in prose" instruction is a negative prohibition that models at this scale tend to override when they have relevant named data in-context. The chip prompt's tool-call result for `get_occupation_education_requirements` returns only `{soc_code, occupation_title, education_code, education_level_name, requires_grad_school}` — it does NOT return feeder majors. This is good: the model cannot enumerate feeders it has not seen.

The YAML context snippet from `data/reference/grad_credential_feeders.yaml` is injected only into `_build_grad_credential_cta` service-side, not into the Gemma prompt. That design is correct. As long as feeder data stays out of the Gemma tool response, the "do not enumerate feeders" prohibition has nothing to override — Gemma literally does not know the feeder list during the chip call. This is the right architectural choice.

**Residual risk:** The model's training data includes knowledge that "Exercise Science and Biology are common pre-PT majors." At temp=0.2 it may produce these from weights, not from the tool result. The prompt must include "Do NOT list specific undergraduate majors in your response — the product surfaces those separately" as a direct prohibition rather than the current indirect instruction "the tile does that." The current wording relies on Gemma inferring that it should not do something because the tile is doing it — a weaker instruction than a direct prohibition.

**Required change:** Replace the current instruction phrase "Do NOT offer 'alternative undergrad majors that lead to this career' — they don't exist. The frontend will render a notice tile from the cta_link payload showing typical feeder undergrad majors at the student's school. Your prose should NOT enumerate the feeders — the tile does that." with: "Do NOT name specific undergraduate majors in your response. Do NOT say 'Exercise Science is a common pre-PT major' or similar — the product displays those separately. Name the credential, cite BLS, and reframe in 2 sentences maximum."

---

**Interaction Assessment: `requires_graduate_credential` vs. `intent_divergence` routing when the typed major IS a feeder**

The spec's §1 rule "when the student's currently-resolved typed major IS a known feeder for that credential, route to `requires_graduate_credential` (not `intent_divergence`)" requires Gemma to know, at classification time, whether the currently-resolved CIP is a feeder. The chip prompt has access to `current_cip4` and `current_title` in the system prompt template. However, the prompt does not instruct Gemma to check this. The tool result from `get_occupation_education_requirements` does not include a feeder list. So Gemma cannot perform this check from the tool data alone — it would have to reason from training knowledge ("Biology is a pre-med major") which is exactly the kind of weights-based fabrication the product prohibits.

**Required change:** The service layer, not Gemma, must perform the feeder-overlap check. After Gemma classifies the bucket as `requires_graduate_credential` and the service constructs the `GradCredentialNoticePayload` via `_build_grad_credential_cta`, the service should check whether `current_resolution.matched_cip[:5]` appears in the YAML's `feeder_cip4_codes` for the matched credential. If it does, set `tone="info"` (student is on a reasonable track) instead of `tone="caution"` (student's framing is structurally wrong). This keeps the feeder-overlap logic in Python where it is deterministic, not in Gemma where it would be probabilistic. The spec's §4 `_build_grad_credential_cta` helper should include this tone-selection logic. As written, `tone` is hardcoded to `"caution"` for all chip-path responses, which is wrong for the "Bio major → doctor" case.

---

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

**Summary of required changes before implementation proceeds:**

| # | Location | Change |
|---|----------|--------|
| C1 | `_CHIP_ROUTING_SYSTEM_PROMPT` bucket-9 text | Add explicit counter-example (Marketing→Software Developer stays `intent_divergence`) and feeder-track case description (Biology→Doctor routes to `requires_graduate_credential`, not `intent_divergence`). |
| C2 | `_parse_chip_response` + `_cut_at` | Add `_GRAD_TARGET_TAIL` to the sentinel list; update `_parse_chip_response` to extract the 4th tail. Alternatively: drop the 4th tail and read `target_soc` from `tool_call_log[0].args`. |
| C3 | `handle_chip_dispatch` | Raise `max_tokens` from 600 to 800 for the `not_expected` path to accommodate the 4th tail, OR adopt the tool-log alternative in C2. |
| C4 | Format spec in `_CHIP_ROUTING_SYSTEM_PROMPT` | Add explicit ordering: `---GRAD_CREDENTIAL_TARGET---` must appear after `---BUCKET---` (and the `---BUCKET---` format string must include `requires_graduate_credential` in its allowed enum). |
| C5 | `lookup_credential_by_pre_x_pattern` regex | Fix the `pa\b` arm so "prepa" (no hyphen) matches. Confirm "premedieval" / "premeditate" are excluded by the `med` arm. |
| C6 | `_CHIP_ROUTING_SYSTEM_PROMPT` bucket-9 text | Replace indirect "the tile does that" with direct prohibition: "Do NOT name specific undergraduate majors in your response." |
| C7 | `_build_grad_credential_cta` | Add feeder-overlap check: if `current_resolution.matched_cip[:5]` is in the credential's `feeder_cip4_codes`, set `tone="info"`; otherwise `tone="caution"`. Remove the hardcoded `tone="caution"`. |

Changes C1, C5, C6, C7 are minor (prompt text and Python logic). Changes C2, C3, C4 are significant and affect the structured-output contract. The implementation MUST adopt either (a) the 4th-tail approach with all three of C2/C3/C4 resolved, or (b) the tool-log alternative which eliminates C2/C3/C4 entirely. The tool-log alternative is the recommended path.

---

## §6 Implementation Log

**Status:** PENDING

### Files Modified
| File | Change Summary |
|------|---------------|

### Deviations from Spec
[Any divergence from §3/§4 and why]

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

### Design Audit (@design-builder)
**Status:** CHANGES REQUESTED

**Auditor:** @fp-design-auditor
**Date:** 2026-05-06
**File audited:** `frontend/src/components/school/GradCredentialNotice.tsx`
**Reference:** `DESIGN.md` (Brightpath design system)

---

## frontend/src/components/school/GradCredentialNotice.tsx

### PASS

- **Color tokens — text:** All text color tokens are correct. `text-text-primary`, `text-text-secondary`, `text-text-muted`, `text-accent-alert`, `text-accent-thrive`, `text-accent-info` all map to defined Brightpath tokens (DESIGN.md §Color Tokens).
- **Color tokens — backgrounds:** `bg-bp-mid`, `bg-bp-surface` are correct Tailwind aliases for `--color-bg-mid` and `--color-bg-surface` (DESIGN.md §Backgrounds).
- **Color tokens — borders:** `border-border-subtle`, `border-border` are correct aliases for `--color-border-subtle` and `--color-border-default` (DESIGN.md §Borders).
- **Left-edge accent stripe:** `border-l-[3px] border-l-accent-caution` / `border-l-accent-info` matches the 3px left-stripe pattern specified in §3 Design Vision wireframe and matches the established pattern in `SetYourCourseScreen.tsx` lines 391 and 492.
- **Typography — font families:** `font-display` (Fredoka) on heading and feeder card title; `font-body` (Nunito) on all body, subhead, note, footer, and CTA spans — correct per DESIGN.md §Font Families.
- **Typography — type scale:** `text-heading` on the credential header (28px, Fredoka 600), `text-body` on subhead and body copy (16px), `text-small` on feeder card note and CTA (14px), `text-micro` on the "not offered here" pill (12px) — all correct per DESIGN.md §Type Scale.
- **Shadows:** `shadow-md` on both the tile and feeder card hover state map to `--shadow-md` (DESIGN.md §Elevation & Shadows).
- **Border radius:** `rounded-xl` (20px) on the tile and feeder cards; `rounded-full` (9999px) on the pill — both correct per DESIGN.md §Border Radii.
- **Motion — spring selection:** `springs.smooth` for the section entrance/exit and feeder card entrance is the correct spring for card entrances and panel expansions (DESIGN.md §Spring Configurations).
- **Motion — stagger:** `stagger.normal` (80ms) for feeder card stagger is correct for card grids (DESIGN.md §Stagger Delays).
- **Motion — reduced motion:** `useReducedMotion()` respected on both the section entrance and each feeder card. When `reducedMotion` is true, y-axis travel is removed and only opacity animates — correct pattern.
- **Motion — whileTap press feedback:** `whileTap={{ scale: 0.97 }}` on feeder card buttons matches `transitions.press` press feedback (DESIGN.md §Common Transitions).
- **Motion import source:** `springs` and `stagger` imported from `@/styles/motion` — correct (DESIGN.md §Motion System).
- **Breakpoints:** `tablet:` prefix used for responsive variants. `tablet` maps to 768px per DESIGN.md §Breakpoints. No `sm:`, `md:`, `lg:` Tailwind defaults used.
- **Responsive feeder row:** Mobile horizontal scroll with `snap-x snap-mandatory`, `tablet:flex-wrap tablet:overflow-x-visible tablet:snap-none` — matches spec §3 wireframe (horizontal scroll mobile, wrap on tablet).
- **Dark-first:** No light-mode assumptions. No `dark:` conditionals or `light:` overrides. All token references use CSS custom properties that are dark-first by system definition.
- **Semantic correctness — caution accent:** Used for the chip-flow tile stripe (student's plan was incomplete). Correct semantic role per DESIGN.md §Accents: "caution = draw states, moderate outcomes, attention."
- **Semantic correctness — info accent:** Used for the pre-flag tile stripe (student already signaled awareness). Correct semantic role: "info = navigation, links, neutral information."
- **Semantic correctness — accent-thrive for CTA (caution tone):** "Switch to this major" affordance in thrive on offered feeder cards in caution tone. Correct: "thrive = Growth, wins, CTAs, positive outcomes" (DESIGN.md §Accents).
- **Focus ring:** `focus-visible:ring-[color:var(--color-focus-ring)]` directly references `--color-focus-ring` via CSS variable syntax — correct value, matches `rgba(123, 184, 224, 0.4)` (DESIGN.md §States).

---

### FAIL

- **FAIL 1 — Hardcoded `rgba` on "not offered here" pill background (line 103):** `bg-[rgba(244,169,126,0.15)]` is a hardcoded RGBA value. DESIGN.md §States defines this exact value as `--color-state-error` (`rgba(244, 169, 126, 0.15)`), with Tailwind alias `bg-state-error`. The hardcoded RGBA must be replaced with `bg-state-error`.
  - **Expected (DESIGN.md §States):** `bg-state-error`
  - **Found (line 103):** `bg-[rgba(244,169,126,0.15)]`

- **FAIL 2 — `leading-relaxed` used for subhead and body text with non-relaxed line-height (lines 117, 200, 205, 233):** DESIGN.md §Line Heights defines `leading-relaxed` as 1.4 and documents its usage as "Reasoning card paragraphs, long captions." The type scale table specifies `text-body` carries its own line-height of 1.5 (`leading-normal`), and `text-small` carries 1.4 (`leading-relaxed`). The component uses `leading-relaxed` on `text-body` paragraphs (lines 200, 205), which overrides the type scale's native 1.5 line-height with 1.4 — a deviation from the type scale spec.
  - **Expected (DESIGN.md §Type Scale):** `text-body` paragraphs should use `leading-normal` (1.5) unless explicitly overriding for a documented reason; `leading-relaxed` (1.4) is the correct pairing for `text-small`.
  - **Found:** `leading-relaxed` on `text-body` paragraphs at lines 200 and 205.
  - **Note:** `leading-relaxed` on `text-small` at lines 117 and 233 is correct per the type scale (small native line-height = 1.4 = relaxed). Only the two `text-body` usages are non-compliant.

- **FAIL 3 — Arrow character rendered with `&rarr;` HTML entity rather than a token-safe approach (line 139):** Minor but mechanical: the arrow `→` in the CTA row is rendered via `&rarr;` HTML entity (line 139). The same `→` pattern used in `SetYourCourseScreen.tsx` and other components uses either a direct Unicode character or an SVG icon. The entity approach works but is inconsistent with the established codebase pattern. This is a consistency-compliance flag, not a visual token issue.
  - **Expected:** Unicode `→` directly in JSX or an SVG icon, matching the codebase pattern.
  - **Found:** `&rarr;` HTML entity at line 139.

---

### WARNINGS

- **WARNING 1 — `hover:-translate-y-0.5` on feeder cards (line 93):** The `-translate-y-0.5` hover lift (2px upward shift) is not a documented interaction pattern in DESIGN.md. The design system does not specify a translate-lift hover state for cards — hover states are expressed via background and border color changes. This is not a token violation, but it is an undocumented interaction pattern that may need design-visionary approval before it ships.

- **WARNING 2 — `transition-all duration-normal` on feeder cards (line 94):** `transition-all` is a broad transition that animates every animatable property simultaneously. DESIGN.md recommends specific property transitions for hover states. In combination with the `whileTap` Framer Motion prop, this may produce competing transitions (CSS `transition-all` and Framer Motion's spring both active). Scoping the CSS transition to `transition-colors` would be safer.

- **WARNING 3 — Hardcoded `min-w-[160px] w-[200px]` and `tablet:min-w-[160px]` card sizing (line 89):** These are arbitrary pixel values not in the spacing token table. The spacing system uses 4px base units (DESIGN.md §Spacing). 160px = 40 units and 200px = 50 units are not covered by the defined `space-*` tokens, but they are dimension values (not padding/margin/gap), so Tailwind arbitrary values are an acceptable escape hatch. Flagged for awareness — not a hard violation.

---

### Verdict: CHANGES REQUESTED

Two hard violations require fixes before this component can be marked APPROVED:

1. **Line 103:** Replace `bg-[rgba(244,169,126,0.15)]` with `bg-state-error`.
2. **Lines 200, 205:** Replace `leading-relaxed` with `leading-normal` on the two `text-body` paragraphs in the main tile (subhead and body copy).

The `&rarr;` entity at line 139 should be replaced with `→` for codebase consistency but is not a Brightpath token violation.

Both failures are one-line fixes. No structural changes required.

### Code Review (@faang-staff-engineer)
**Status:** APPROVED (with minor fixes recommended)

**Reviewer:** Staff Engineer (15 YOE, production incident survivor)
**Date:** 2026-05-06

**Files reviewed:**
- `backend/app/services/grad_credentials.py`
- `backend/app/services/set_your_course.py` (new grad-credential helpers, bucket 9, pre-flag short-circuit)
- `backend/app/models/api.py` (FeederMajor, GradCredentialNoticePayload, CtaLink extension)
- `src/mcp_server/futureproof_server.py` (`_handle_get_occupation_education_requirements`)
- `frontend/src/components/school/GradCredentialNotice.tsx`
- `frontend/src/hooks/useSetYourCourse.ts`
- `data/reference/grad_credential_feeders.yaml`

#### Summary

Look, I love Claude, BUT -- this is actually solid work. The security surface is well-defended: the MCP handler validates SOC format before querying, `query_filtered` uses parameterized SQL, YAML loading uses `safe_load`, and the regex patterns are bounded and non-catastrophic. The architecture is clean -- the pre-flag short-circuit avoids a Gemma round-trip for a deterministic case, and the chip-routing bucket integrates naturally into the existing taxonomy.

I found no critical or serious issues. The code is production-ready with minor improvements recommended. I'm saying "this time" because I reviewed every line and I want that on the record.

#### Critical Findings (none)

No critical issues found. This is great AI-generated code. It just needs... well, it doesn't need much, actually.

#### Serious Findings (none)

No serious issues found.

#### Moderate Findings

**Finding M1: Double-check lock pattern lacks memory fence guarantee**
**Severity:** Moderate
**Impact:** On CPython with the GIL, this is effectively safe. On alternative Python runtimes (PyPy, GraalPy, or a future free-threaded CPython), the pattern could theoretically allow a thread to read a partially-initialized `_credentials` list. In practice, this is a non-issue for this codebase today, but it's worth documenting why it's safe (GIL) so a future maintainer doesn't copy the pattern elsewhere.
**Location:** `backend/app/services/grad_credentials.py:41-55`
**The Problem:** The outer check `if _credentials is not None` at line 44 reads a module-global without holding the lock. In a world without the GIL, another thread could see a non-None reference to a partially-constructed list.
**Assessment:** No fix required today. CPython's GIL serializes this. Free-threaded CPython (PEP 703) would need a review, but that's a bridge to cross when the runtime ships. Flagging for awareness only.

**Finding M2: `_extract_soc_from_tool_log` uses defensive multi-attribute fallback that doesn't match the actual dataclass**
**Severity:** Moderate
**Impact:** The code works but the fallback chain (`getattr(tc, "tool_name", None) or getattr(tc, "name", "")` and the `arguments` fallback) suggests uncertainty about the shape of `tool_call_log` entries. The `ToolCallTurn` dataclass at `gemma_client.py:933` uses `tool_name` and `tool_args` -- the fallbacks to `.name` and `.arguments` are dead code paths that will never fire.
**Location:** `backend/app/services/set_your_course.py:1211-1218`
```python
tool_name = getattr(tc, "tool_name", None) or getattr(tc, "name", "")
# ...
args = getattr(tc, "tool_args", None) or getattr(tc, "args", None) or getattr(tc, "arguments", {})
```
**The Problem:** Dead fallback branches obscure what the code actually depends on. If `ToolCallTurn` ever changes its attribute names, these fallbacks would silently mask the break instead of raising an `AttributeError` that tells you something changed.
**Recommended Fix:** Use `tc.tool_name` and `tc.tool_args` directly, matching the `ToolCallTurn` dataclass. Add a type annotation to `tool_call_log` parameter.
```python
def _extract_soc_from_tool_log(
    tool_call_log: list[ToolCallTurn] | None,
) -> str | None:
    if not tool_call_log:
        return None
    for tc in tool_call_log:
        if tc.tool_name == "get_occupation_education_requirements":
            soc = str(tc.tool_args.get("soc_code", ""))
            if soc and re.match(r"^\d{2}-\d{4}$", soc):
                return soc
    return None
```

**Finding M3: Pre-flag short-circuit returns empty `careers_preview` -- frontend may show blank career tiles**
**Severity:** Moderate
**Impact:** When the pre-flag fires, `_build_pre_flag_result` returns `careers_preview=[]`. The `useSetYourCourse` hook sets this as `currentResolution`, which drives the `doCareerFetch` state machine via `parentCipOrMatched`. The fetch will succeed (it queries the feeder CIP's career paths), but there's a brief window where the frontend has a resolution with no careers_preview and the career tiles area could flash empty before the async fetch completes. The existing `outcomes-loading` shimmer state handles this, but it's worth confirming the UX is intentional.
**Assessment:** Not a bug -- the outcomes state machine handles it. But if the pre-flag path becomes latency-sensitive, consider pre-populating `careers_preview` from `intent._get_career_titles_for_cip(matched_cip)` in `_build_pre_flag_result` to avoid the flash.

#### Minor Findings

**Finding m1: `_pre_flag_prose` missing template for `msw`, `ms-slp`, `ms-counseling`, `mlis` credentials**
**Severity:** Minor
**Impact:** These credentials exist in `grad_credential_feeders.yaml` but have no entry in `_CREDENTIAL_PROSE_TEMPLATES`. The fallback template fires: "This career requires a graduate credential." -- which is accurate but less specific than the pre-X templates for medical/law/etc. Since there are no pre-X regex patterns for these credentials either (they're master's-level, not traditional "pre-X" tracks), this is a non-issue for the pre-flag path. They would only surface through the chip-routing bucket where Gemma writes the prose. No action required.

**Finding m2: SOC validation in `_extract_soc_from_tool_log` uses `re.match` instead of `re.fullmatch`**
**Severity:** Minor
**Impact:** `re.match(r"^\d{2}-\d{4}$", soc)` with the `^` and `$` anchors is functionally equivalent to `re.fullmatch` here. However, the codebase's own security note in `api.py:179` documents that `$` allows a trailing newline. Using `re.fullmatch` would be consistent with the pattern established by the `AskScope` SOC validator. The risk is negligible (the SOC comes from Gemma's tool args, not user input), but consistency matters.
**Location:** `backend/app/services/set_your_course.py:1217`
**Recommended Fix:** `if soc and re.fullmatch(r"\d{2}-\d{4}", soc):`

#### What's Good

- **SQL injection defense:** The MCP handler delegates to `query_iceberg_simple` which uses parameterized queries. The `_SOC_CODE_PATTERN` validation rejects malformed input before it reaches the query layer. Defense in depth done right.
- **YAML loading:** `yaml.safe_load` is used, not `yaml.load`. No arbitrary code execution risk from the YAML file.
- **Regex patterns are bounded:** The pre-X patterns use `\b` word boundaries and `\w*` (not `.*`) -- no catastrophic backtracking (ReDoS) vectors. I checked each pattern manually.
- **Graceful degradation:** When YAML is missing, the service logs and returns an empty list. When the YAML doesn't cover a SOC, the chip response downgrades to `intent_divergence`. When fewer than 3 feeders exist, the CTA is suppressed. Every failure mode has been thought through.
- **Pre-flag short-circuit is architecturally clean:** Deterministic regex match skips Gemma entirely for known pre-X patterns. This is the right call -- no reason to spend LLM tokens on a lookup-table answer.
- **Thread safety:** The double-check lock pattern is appropriate for the GIL-protected CPython runtime this will run on.
- **Frontend component:** `GradCredentialNotice.tsx` respects reduced motion, has proper `aria-label`, uses Brightpath tokens, and handles both tones correctly. The `onAcceptFeeder` callback is a clean interface.
- **The `ToolCallTurn` dataclass access pattern:** Despite the unnecessary fallbacks (M2), the code correctly reads `tool_args` as a dict and validates the SOC format before using it.

#### Required Changes

None blocking. The findings are all moderate-to-minor. Ship it.

If the implementing agent wants to clean up:
1. (M2) Tighten `_extract_soc_from_tool_log` to use direct attribute access and add a type annotation -- routes to implementation agent.
2. (m2) Switch `re.match` to `re.fullmatch` for SOC validation consistency -- routes to implementation agent.

#### Questions for the Author

1. The pre-flag path calls `grad_credentials._load_credentials()` (a private function) directly from `set_your_course.py` at line 408. Is there a reason this isn't exposed through a public helper like `get_credential_by_id(cred_id)`? The underscore prefix convention signals "don't call me from outside this module."
2. Has the pre-flag short-circuit been tested with mixed-case and accented input? `normalize_input` lowercases, and the regex patterns use `re.IGNORECASE`, but I want to confirm the interaction between the two (normalized input fed to case-insensitive regex) doesn't have edge cases.
3. What monitoring/alerting exists for the `requires_graduate_credential` bucket? Is there a counter or log line that fires when this path activates so you can track adoption?

---

## §9 Verification

**Status:** PENDING

---

## §10 Discussion

```
[2026-05-06] Initial draft. Filed as a follow-on to feature-set-your-course
once the team confirmed `consumable.occupation_profiles` already carries
the BLS education_code signal — meaning this feature is plumbing, not a
new data source.

Open questions for review:
- Should the YAML include `code 2 (Master's)` credentials by default
  (MSW, MS-SLP, MS-Counseling, MLIS, MS-PA), or only `code 1
  (Doctoral/professional)` credentials? Shipping both is valuable
  (Speech-Language Pathology is a real student concern), but doubles
  the curation surface. Founder call.
- Pre-flag pattern coverage: spec lists 8 patterns. Should "pre-physical-
  therapy" (spelled-out) join the regex? What about international
  spellings ("pre-physiotherapy")? Hackathon scope = ship the 8; v2 can
  expand.
- Cacheability: the Set Your Course feasibility-mode design says
  school_gap and genuinely_impossible aren't cacheable. The new
  requires_grad_school mode follows the same posture for the same
  reason — but the *resolution swap* the student does after seeing
  the notice (e.g. swapping to Exercise Science) IS captured by
  whichever cacheable mode the swap falls under. Documenting this
  inheritance to avoid confusion.
- Build-engine behavior on grad-only SOCs: spec says "do not block at
  commit." The PT build still renders ERN ~$95k and GRW high — both
  values reflect post-DPT-school career data, NOT undergrad earnings.
  Should the Pentagon stats add a footnote on grad-only careers
  ("these stats reflect post-grad-school career, not first-undergrad-
  job")? Out of scope for this spec, but worth a follow-on.
```

---

## §11 Final Notes

**Human Review:** PENDING

[Final thoughts, lessons learned, follow-up items populated at COMPLETE.]
