# Set Your Course — Visionary Design Proposal

**Spec:** `docs/specs/feature-set-your-course.md`
**Author:** @fp-design-visionary
**Date:** 2026-04-19
**Target audience:** the engineer implementing §4. You should not need to make a single visual decision after reading this.

> **Voice-rule amendments (2026-04-19, late session).** Three stacked rules now govern student-facing copy across this proposal and any future rendering:
>
> 1. **No internal taxonomy codes.** Per `feature-set-your-course.md` §2 Decision #12 — students never see `CIP`, `SOC`, `crosswalk`, or numeric codes (`52.02`, `11-2021`). Internal mode names (`direct_hit`, `crosswalk_quirk`, `adjacent_reachable`) stay in code and engineer-facing prose.
> 2. **Receipts: sources are named.** Per `feature-set-your-course.md` §2 Decision #13 + `feature-receipts.md` — every factual claim cites its source. Gemma prose carries inline attribution; career cards carry a subtle footer attribution.
> 3. **Acronym spell-out rule.** Per `feature-set-your-course.md` §2 Decision #14 — first reference per rendered view uses the full name with the acronym in parentheses (e.g. *"Bureau of Labor Statistics (BLS)"*); subsequent references may use the acronym alone. Applies to sources (BLS, IPEDS, O*NET, BEA), not to taxonomies (which stay forbidden per rule 1).
>
> The design decisions in this proposal (layout, motion, color, tokens, component structure) are unchanged. Only student-facing *words* were corrected. See `docs/specs/design/set-your-course-mockup/index.html` for the corrected renderings.

---

## 0. Emotion First

Before a single token, name what this screen is for.

The student arrives at Set Your Course expecting a form. Three inputs, a Go button, wait for results. That is the wrong mental model and it is the reason the existing three-screen flow buries our thesis.

What Set Your Course is **actually** for: **a student watches their own choice resolve into a future, in public, alongside the model that is doing the resolving.** They watch Gemma reason. They get to disagree. When they disagree, Gemma reasons again — with receipts. When the crowd has been here before them, the crowd's answer is right there.

The target emotion across the four states:

| State | Emotion | Design implication |
|---|---|---|
| Empty | **Quiet invitation.** | A waiting planetarium, not a form. One thing to do. |
| Mid-resolution | **Witnessing thought.** | Not loading. Reasoning. The student is watching something work. |
| Resolved | **"Huh — is that right?"** | The data is confident and the chip rail gives them a graceful way to push back. |
| Post-chip / community | **"I'm not the first person to land here."** | Honest. Grounded. Never creepy. |

Every decision below serves one of those four feelings. If a pixel doesn't serve the feeling, it doesn't belong.

---

## 1. Opinionated Decisions (Where The Spec Left Room)

| Decision point | Call |
|---|---|
| Clarifier affordance: modal vs inline vs bottom sheet | **Inline expansion on desktop, bottom sheet on mobile.** Rationale below (§4). Never a modal — a modal steals focus from the reasoning stream, which is the product. |
| Streaming cadence | **Paragraph-by-paragraph with a token shimmer on the paragraph currently arriving.** Token-by-token is jittery and makes the layout jump; paragraph-by-paragraph reads like thought, not like a teletype. |
| Chip visual hierarchy | **"Not what I expected" is primary** (filled caution tint, Gemma star prefix). The other two are ghost-equivalent. Spec §2 Decision #10 already privileges this chip via the soft-nudge; the visual reinforces the same bias. |
| Community suggestions placement | **Directly under the chip rail, above "Yes, continue."** So the student sees "here's where the crowd went" before they commit. |
| Debug trace layout (post-chip) | **Replaces the career preview in place, with a breadcrumb ("from your clarifier") and a back affordance.** Not stacked, not a side panel. The resolution IS the trace now. |
| Commit CTA position mobile | **Sticky bottom bar.** The form scrolls; the commit never leaves view once a resolution exists. |
| School-gap CTA | **A full-width tile, not a chip.** Linking to another screen is a different gesture than correcting here; its affordance has to read as "leave this screen," not "keep working here." |

---

## 2. Component Tree

```
<SetYourCourseScreen>                                  # screens/SetYourCourseScreen.tsx
  <PageContainer variant="grid">                       # existing, 12-col grid
    <Section.Intro>                                    # §3 wireframes show this
      <Eyebrow>SET YOUR COURSE</Eyebrow>               # SectionLabel primitive
      <H1>Where does this take you?</H1>
    </Section.Intro>

    <Section.Inputs>                                   # col-span-12 desktop:col-span-7
      <SchoolPicker />                                 # existing — no changes
      <MajorInput />                                   # existing, wired to useSetYourCourse
      <DetailsPanel collapsedByDefault={isMobile}>     # §2 Decision #8
        <EffortSlider />                               # existing EffortLoansPanel bits
        <LoansSlider />
      </DetailsPanel>
    </Section.Inputs>

    <Section.Preview>                                  # col-span-12 desktop:col-span-5
      <ResolutionHeader />                             # "Gemma is reading…" → resolved title
      <StreamingReasoning />                           # NEW — see §5
      <CareerTierSection />                            # existing, adapted for live-update
      <CommunitySuggestions />                         # NEW — see §6
      <CorrectionChips />                              # NEW — see §3
      <ClarifierSheet />                               # NEW — inline or bottom-sheet, see §4
      <DebugTraceReader />                             # NEW — replaces CareerTierSection post-chip
      <SchoolGapCTA />                                 # NEW — when feasibility is school_gap
    </Section.Preview>

    <Section.CommitBar>                                # sticky bottom on mobile, inline on desktop
      <CommitButton />
      <StartOverButton />
      <LowConfidenceNudge />                           # §2 Decision #10 soft copy
    </Section.CommitBar>
  </PageContainer>
</SetYourCourseScreen>
```

Hook: `useSetYourCourse()` owns all of it. Store: `buildInputStore` extended per §4. No new state managers.

---

## 3. Wireframes — Four States

### Conventions
- Box characters are structural only. Real UI uses Brightpath tokens throughout.
- `[GS]` = `GemmaStar` primitive (`components/ui/GemmaStar.tsx`). `[GT]` = `GemmaThinking` composite.
- `[chip]` = pill per §3 Chip Rail spec below.
- `( )` = input. `[ ]` = button. `{ }` = live-updating data.
- `━` = full-bleed rule (`border-border-subtle`). `·` = list divider (`border-border-subtle`).
- Dashed borders `┊ ┊` indicate collapsed or placeholder regions.

---

### State A — Empty (Landing, No School, No Major)

**Emotion:** Quiet invitation. A waiting planetarium. One thing to do.

#### Desktop (≥1200px)

```
════════════════════════════════════════════════════════════════════════════════
                                   FutureProof                         [header]
════════════════════════════════════════════════════════════════════════════════

                         SET YOUR COURSE
                         Where does this take you?
                         Pick a school and a major. The careers
                         follow.

 ┌──────────────────────────────────────┐   ┌────────────────────────────────┐
 │  YOUR SCHOOL                         │   │                                │
 │  (School name or nickname         ↓) │   │                                │
 │                                      │   │                                │
 │                                      │   │            ·   ·   ·           │
 │  YOUR MAJOR                          │   │                                │
 │  (What are you studying?          ⌯) │   │         The careers will       │
 │                                      │   │         show up here as        │
 │                                      │   │         you type.              │
 │  ▸ Show effort & loans               │   │                                │
 │                                      │   │            ·   ·   ·           │
 └──────────────────────────────────────┘   │                                │
                                            │                                │
                                            └────────────────────────────────┘

 ┌──────────────────────────────────────────────────────────────────────────┐
 │                                                                          │
 │                   [Yes, continue]  disabled       [Start over]  ghost    │
 │                                                                          │
 └──────────────────────────────────────────────────────────────────────────┘
════════════════════════════════════════════════════════════════════════════════
```

**What it is:**
- Left column (col-span-7): inputs. School picker on top (existing `SchoolPicker` component, `bg-deep` input at `height: 56px` per DESIGN.md "Large variant"), major input directly below. Effort & loans collapsed under a `▸` disclosure — `font-body text-small text-text-muted`, hover tints to `text-text-secondary`.
- Right column (col-span-5): empty-preview placeholder. Three faint `text-muted` dots on a baseline, copy in `font-body text-body text-text-muted italic`: *"The careers will show up here as you type."* No spinner, no skeleton rows, no fake shimmer. This is a waiting planetarium; it is supposed to feel still.
- Commit bar: `Yes, continue` rendered disabled (see §8 for exact treatment), `Start over` ghost and also effectively inert until something has been entered.

**Tokens:**
- Eyebrow "SET YOUR COURSE" → `font-data text-[11px] font-bold tracking-[2px] uppercase text-accent-info`, `mb-2`.
- H1 "Where does this take you?" → `font-display text-heading font-semibold text-text-primary`.
- Supporting line → `font-body text-body text-text-secondary`, `mt-3 max-w-[44ch]`.
- Placeholder text → `font-body text-body text-text-muted italic`.
- Empty-preview dots → three 4px circles in `bg-bp-raised` at `opacity-40`, centered, `gap-4`.

**Motion:**
- On mount: `transitions.fadeInUp` on the intro block, then `staggerContainer(0, 80)` with `staggerItem` children for (school input, major input, disclosure). Right column (empty preview) uses `transitions.fade` with `delay 0.2s`. Nothing bounces — this is the "before the show begins" state.

#### Mobile (<768px)

```
══════════════════════════════════════════
             FutureProof         [header]
══════════════════════════════════════════

  SET YOUR COURSE
  Where does this take you?
  Pick a school and a major. The
  careers follow.

  ┌────────────────────────────────────┐
  │ YOUR SCHOOL                        │
  │ (School name or nickname        ↓) │
  └────────────────────────────────────┘

  ┌────────────────────────────────────┐
  │ YOUR MAJOR                         │
  │ (What are you studying?         ⌯) │
  └────────────────────────────────────┘

  ▸ Show effort & loans

  ┌────────────────────────────────────┐
  │                                    │
  │         ·   ·   ·                  │
  │                                    │
  │    The careers will show up here   │
  │    as you type.                    │
  │                                    │
  │         ·   ·   ·                  │
  │                                    │
  └────────────────────────────────────┘

                                   [v spacer v]
 ┌────────────────────────────────────────┐   sticky bottom, frosted
 │  [Start over]       [Yes, continue]    │   — disabled
 └────────────────────────────────────────┘
══════════════════════════════════════════
```

**What changes on mobile:**
- Single column, gutters `16px` (`gap-grid-mobile`).
- Effort + loans **collapsed by default** (§2 Decision #8). The disclosure row is a 48px-tall tap target.
- Commit bar is **sticky to the viewport bottom**, `bg-bp-deep/92 backdrop-blur-md`, `border-t border-border-subtle`, safe-area inset respected. Two buttons, `Start over` (ghost, left) and `Yes, continue` (primary, right, weighted 2:3 by width).

---

### State B — Mid-Resolution (Streaming Gemma Reasoning Visible, Partial)

**Emotion:** Witnessing thought. Something is working. The student is not waiting — they're watching.

This state appears 300ms after the student stops typing a recognizable major. It persists until the final paragraph of Gemma's reasoning arrives, plus an additional 200ms hold so the eye doesn't whiplash.

#### Desktop

```
════════════════════════════════════════════════════════════════════════════════
                                   FutureProof                         [header]
════════════════════════════════════════════════════════════════════════════════

                         SET YOUR COURSE
                         Where does this take you?

 ┌──────────────────────────────────────┐   ┌─────────────────────────────────────┐
 │ YOUR SCHOOL                          │   │ [GT] Gemma is reading your input…   │
 │ (Indiana University Bloomington   ✓) │   │                                     │
 │                                      │   │ ┌─────────────────────────────────┐ │
 │ YOUR MAJOR                           │   │ │ Marketing at IU maps to         │ │
 │ (Marketing                        │) │   │ │ Business/Commerce       │ │
 │                                      │   │ │ because the school reports      │ │
 │ ▸ Show effort & loans                │   │ │ marketing coursework under a    │ │
 │                                      │   │ │ broader Business program. █         │ │
 └──────────────────────────────────────┘   │ │ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │ │
                                            │ └─────────────────────────────────┘ │
                                            │                                     │
                                            │ ┊ careers populate here when        │
                                            │ ┊ reasoning resolves                │
                                            └─────────────────────────────────────┘

 ┌──────────────────────────────────────────────────────────────────────────────┐
 │                                                                              │
 │                   [Yes, continue]  disabled         [Start over]  ghost      │
 │                                                                              │
 └──────────────────────────────────────────────────────────────────────────────┘
════════════════════════════════════════════════════════════════════════════════
```

**What it is:**
- Left column is now **populated and locked-feeling** — both inputs show values with a `✓` glyph (`text-accent-thrive`) at the right edge of the school input (confirmed match) and a caret `│` in the major input showing it still has focus.
- Right column header: `GemmaThinking` composite — `GemmaSpinner` (28px, breathing `shadow-glow-insight`) + attribution text *"Gemma is reading your input…"* (`font-body text-small text-text-secondary`, per DESIGN.md Gemma Interactions family).
- Reasoning card below the header: `bg-bp-deep/60` (slightly darker than `bg-bp-mid`) with `border-l-[3px] border-accent-insight` — a vertical stripe that matches the Gemma Match Card's "this is Gemma's" stripe. Padding `20px`. Paragraph just arriving gets a subtle **shimmer sweep** (see §5). Cursor `█` is `text-accent-insight`, blinks at `animate-pulse` 1.2s.
- A **dashed-border** placeholder region below the reasoning card hints at where the career preview will materialize: `border border-dashed border-border-subtle`, `rounded-xl`, `py-8`, copy `font-body text-small text-text-muted italic` — *"careers populate here when reasoning resolves"*. This is honest about what's next without faking data.

**Tokens:**
- Reasoning paragraph text → `font-body text-body text-text-primary`, `leading-relaxed`.
- Reasoning card container → `bg-[rgb(27,29,48)]/60` (i.e. `bg-bp-deep/60`), `border border-border-subtle border-l-[3px] border-l-accent-insight`, `rounded-xl`, `p-5`, `shadow-md`.
- Breathing glow around the card → CSS `ambient-breathe` adapted: box-shadow pulses between `0 0 16px rgba(184, 169, 232, 0.08)` and `0 0 28px rgba(184, 169, 232, 0.18)` over 4s. This is the signature "thinking" beat. Reuse `shadow-glow-insight` value space; don't invent a new shadow.

**Motion (see §5 for the shimmer specifically):**
- The reasoning card fades in with `transitions.fadeInUp`, `springs.smooth`.
- Paragraphs arrive one at a time. See §5.

#### Mobile

```
══════════════════════════════════════════
             FutureProof         [header]
══════════════════════════════════════════

  SET YOUR COURSE
  Where does this take you?

  ┌────────────────────────────────────┐
  │ YOUR SCHOOL                        │
  │ (Indiana University…            ✓) │
  └────────────────────────────────────┘

  ┌────────────────────────────────────┐
  │ YOUR MAJOR                         │
  │ (Marketing                      │) │
  └────────────────────────────────────┘

  ▸ Show effort & loans

  [GT] Gemma is reading your input…

  ┌────────────────────────────────────┐
  │ In IU's submission to the          │
  │ Integrated Postsecondary Education │
  │ Data System (IPEDS), Marketing is  │
  │ filed within its Business program. │
  │ BLS tracks graduate placements —   │
  │ I can pull them if you ask. █      │
  │ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░    │
  └────────────────────────────────────┘

  ┊ careers populate here when        ┊
  ┊ reasoning resolves                ┊

 ┌────────────────────────────────────────┐  sticky bottom
 │  [Start over]  [Yes, continue] disabled│
 └────────────────────────────────────────┘
══════════════════════════════════════════
```

- Reasoning card is full-width below the collapsed Details disclosure.
- Sticky commit bar still at the viewport bottom, still disabled.

---

### State C — Resolved With Career Preview + Chip Rail Visible

**Emotion:** Quiet confidence, then the first invitation to push back.

The reasoning card has finished streaming. Its content compresses into a single resolved-header line ("Gemma matched *Marketing* at IU"). The career preview fills its tile. The chip rail sits directly beneath — kid-voiced, honest.

#### Desktop

```
════════════════════════════════════════════════════════════════════════════════
                                   FutureProof                         [header]
════════════════════════════════════════════════════════════════════════════════

                         SET YOUR COURSE
                         Where does this take you?

 ┌──────────────────────────────────────┐   ┌─────────────────────────────────────┐
 │ YOUR SCHOOL                          │   │ [GS] Gemma matched "marketing"      │
 │ (Indiana University Bloomington   ✓) │   │     → Business/Commerce     │
 │                                      │   │                                     │
 │ YOUR MAJOR                           │   │ WHERE THIS LEADS                    │
 │ (Marketing                        ✎) │   │ ┌─────────────────────────────────┐ │
 │                                      │   │ │ ▸ Financial Analyst             │ │
 │ ▸ Show effort & loans                │   │ │ ▸ Operations Analyst            │ │
 │                                      │   │ │ ▸ Management Consultant         │ │
 └──────────────────────────────────────┘   │ │ ▸ Market Research Analyst       │ │
                                            │ └─────────────────────────────────┘ │
                                            │                                     │
                                            │ OTHER STUDENTS AT IU…               │
                                            │ ┊ (this state hides community card  │
                                            │ ┊  when no suggestions exist —      │
                                            │ ┊  see State D)                     │
                                            │                                     │
                                            │ ─── Something feel off? ───         │
                                            │                                     │
                                            │ [GS][ Not what I expected ]  primary│
                                            │ [ Show me less common paths ] ghost │
                                            │ [ Wrong major ]             ghost   │
                                            └─────────────────────────────────────┘

 ┌──────────────────────────────────────────────────────────────────────────────┐
 │                                                                              │
 │        [Yes, continue]  primary           [Start over]  ghost                │
 │                                                                              │
 └──────────────────────────────────────────────────────────────────────────────┘
════════════════════════════════════════════════════════════════════════════════
```

**Anatomy of the right column, top to bottom:**

1. **Resolution header row** — `GemmaStar` (14px, info→insight gradient) + *"Gemma matched `"marketing"`"* in `font-body text-small text-text-muted`, raw input in `font-semibold text-accent-insight`. Second line, indented: `→ Business/Commerce` where the title is `font-display text-subheading font-semibold text-accent-insight`. No numeric code rendered — student-facing per §2 Decision #12. This is the resolution in compressed form — the full reasoning collapsed after stream-complete.

2. **Section label** — `SECTION_LABEL` primitive, copy `WHERE THIS LEADS`. `font-data text-[11px] font-bold tracking-[2px] uppercase text-accent-info`, `mt-6 mb-3`. This label is already the convention in GemmaMatchCard — we inherit it verbatim.

3. **CareerTierSection** — existing component. Each career row: `font-body text-body-sm font-semibold text-accent-info` with an `▸` glyph prefix, hover brightens to `text-text-primary`. Stagger entrance at `stagger.fast` (50ms per row). No changes to the component; we just feed it the live-updating resolution.

4. **(Hidden in state C.)** Community suggestions card. See State D.

5. **Chip rail separator** — `mt-6 pt-5 border-t border-border-subtle`. A tiny label: *"Something feel off?"* in `font-body text-small text-text-muted italic`, centered in a `─── … ───` rule pair. This phrasing is the kid-voiced invitation: an engineer would write "Correct the resolution." A 17-year-old will read "Something feel off?" and know exactly what it means.

6. **Chip rail** — three chips, stacked vertically on narrow columns, wrapped on wide. Full treatment in §3-chips. First chip is primary-weight, other two are ghost-weight.

7. **(Sticky below:)** the commit bar. Commit button is now enabled and `accent-thrive`. Start-over is ghost.

#### Mobile

```
══════════════════════════════════════════
             FutureProof         [header]
══════════════════════════════════════════

  SET YOUR COURSE
  Where does this take you?

  (IU…  ✓)
  (Marketing  ✎)
  ▸ Show effort & loans

  [GS] Gemma matched "marketing"
       → Business/Commerce

  WHERE THIS LEADS
  ┌─ Financial Analyst                ─┐
  ┌─ Operations Analyst               ─┐
  ┌─ Management Consultant            ─┐
  ┌─ Market Research Analyst          ─┐

  ─── Something feel off? ───

  ┌──────────────────────────────────┐
  │ [GS] Not what I expected         │ primary
  └──────────────────────────────────┘
  ┌──────────────────────────────────┐
  │ Show me less common paths        │ ghost
  └──────────────────────────────────┘
  ┌──────────────────────────────────┐
  │ Wrong major                      │ ghost
  └──────────────────────────────────┘

 ┌────────────────────────────────────────┐  sticky bottom
 │  [Start over]       [Yes, continue]    │
 └────────────────────────────────────────┘
══════════════════════════════════════════
```

---

### State D — Post-Chip (Community Suggestions Visible OR Debug Trace Visible)

Two sub-states share this slot. Either the community is populated (more common as the hackathon runs) OR the student tapped a chip and we're showing a debug trace. They don't coexist: if the debug trace is open, community is suppressed underneath it because the student is already mid-correction.

#### D.1 — Community Suggestions Visible (Desktop)

```
════════════════════════════════════════════════════════════════════════════════
                                   FutureProof                         [header]
════════════════════════════════════════════════════════════════════════════════

 (…left column as State C…)                 ┌─────────────────────────────────────┐
                                            │ [GS] Gemma matched "marketing"      │
                                            │     → Business/Commerce     │
                                            │                                     │
                                            │ WHERE THIS LEADS                    │
                                            │ ▸ Financial Analyst                 │
                                            │ ▸ Operations Analyst                │
                                            │ ▸ Management Consultant             │
                                            │ ▸ Market Research Analyst           │
                                            │                                     │
                                            │ ─────────────────────────────────── │
                                            │                                     │
                                            │ OTHER STUDENTS SEARCHING            │
                                            │ "MARKETING" AT IU ENDED UP HERE     │
                                            │                                     │
                                            │ ┌─────────────────────────────────┐ │
                                            │ │ → Marketing Manager             │ │
                                            │ │   17 students                   │ │
                                            │ ├─────────────────────────────────┤ │
                                            │ │ → Market Research Analyst       │ │
                                            │ │   3 students                    │ │
                                            │ ├─────────────────────────────────┤ │
                                            │ │ → Advertising Specialist        │ │
                                            │ │   1 student                     │ │
                                            │ └─────────────────────────────────┘ │
                                            │                                     │
                                            │ ─── Something feel off? ───         │
                                            │ [GS][ Not what I expected ] primary │
                                            │ [ Show me less common paths ] ghost │
                                            │ [ Wrong major ]             ghost   │
                                            └─────────────────────────────────────┘
```

**What it is:**
- Section label above the cards: `OTHER STUDENTS SEARCHING "MARKETING" AT IU ENDED UP HERE`. Rendered in `font-data text-[11px] font-bold tracking-[2px] uppercase text-accent-info`. The input and school are interpolated in the same `font-data` face so they read as data, not copy.
- Card list: up to 3 stacked rows in a single container `bg-bp-mid border border-border-subtle rounded-xl` with `border-t border-border-subtle` between rows (first row no rule). Each row uses the **List Item** pattern from DESIGN.md Inputs section — `padding: 12px 18px`, hover `bg-bp-surface`, selected-look transient on click before swap.
- Row content: left column is the career title (`font-body text-body-sm font-semibold text-accent-info`, brightens to `text-text-primary` on hover, `▸` glyph prefix). Right column is the count in `font-data text-data-sm text-text-muted`, right-aligned — e.g. `17 students`.
- Expansion: if `> 3` suggestions exist, a `Show 4 more` ghost button appears below the list. `font-body text-small text-accent-info`, hover adds an `rgba(123, 184, 224, 0.08)` background wash.
- **Honest, not creepy.** Per voice guide: "Other students" not "people also viewed." No "98% of students chose…" No "trending." Just a count, in `font-data`, which reads as fact, not social pressure. Per §2 Decision #4 of the voice guide: *the absence of prose is what makes the rest trustworthy.*

**Click interaction (see §12 for full timing):**
- Click a row → row flashes `bg-[rgba(125,212,163,0.12)]` for 180ms, title color animates from `accent-info` to `accent-thrive`, right-column count pulses once. Simultaneously, the Resolution header + career preview begin a 280ms crossfade to the new resolution. Community list remains; the count on the clicked row increments by one after the fade (the correction log has been written).

**Empty state — no suggestions exist:**
- The entire `OTHER STUDENTS SEARCHING…` block is **absent**. No "No results yet." No "Be the first!" No empty card. The separator rule above it is also absent. A cold `(unitid, input)` combo looks clean, not broken. This is the honest move per voice guide: *filler politeness is noise.*

#### D.2 — Debug Trace Visible (Post-Chip, Desktop)

When the student taps "Not what I expected," submits the clarifier, and Gemma starts streaming the debug response, the right column transforms. The resolution header stays. The career preview is replaced by the streaming debug trace with a feasibility-tagged career list.

```
 ┌─────────────────────────────────────┐
 │ [GS] Gemma matched "marketing"      │
 │     → Business/Commerce     │
 │                                     │
 │ [GT] Gemma is investigating…        │
 │ ─ from your clarifier: "I wanted    │
 │   actual marketing jobs"            │
 │                                     │
 │ ┌─────────────────────────────────┐ │
 │ │ IU reports marketing coursework │ │
 │ │ under a broader Business program    │ │
 │ │ a Business program, but grads   │ │
 │ │ in core marketing roles. Here's │ │
 │ │ what the data shows. █          │ │
 │ └─────────────────────────────────┘ │
 │                                     │
 │ THIS SCHOOL → THESE CAREERS         │
 │ ┌─────────────────────────────────┐ │
 │ │ → Marketing Manager      ◆ fits │ │
 │ │ ├ Through Business program      │ │
 │ │ → Market Research Analyst ◆ fits│ │
 │ │ ├ direct hit                    │ │
 │ │ → Advertising Specialist ◆ fits │ │
 │ │ ├ adjacent path                 │ │
 │ └─────────────────────────────────┘ │
 │                                     │
 │ [ ◂ Back to original ]  ghost       │
 └─────────────────────────────────────┘
```

**Anatomy:**
- **Breadcrumb** beneath the reasoning header: *"from your clarifier: 'I wanted actual marketing jobs'"* in `font-body text-small text-text-muted italic`. Echoes the user's input back so the student knows what Gemma is reacting to. Truncated at 120 chars with ellipsis on overflow.
- **Reasoning paragraph card** — identical treatment to State B: `border-l-[3px] border-accent-insight`, breathing glow, shimmer on the arriving paragraph.
- **Feasibility-tagged career list** — section label `THIS SCHOOL → THESE CAREERS`. Each row is a clickable List Item pattern card. Title in `text-accent-info → text-primary on hover`. Feasibility badge on the right:
  - `◆ fits` in `pill-thrive` (internal modes: direct_hit, crosswalk_quirk, adjacent_reachable — names stay in code, never rendered)
  - `◇ not here` in `pill-caution` (school_gap) — row is not clickable; instead triggers the school-gap CTA below
  - `◇ no path` in `pill-alert` (genuinely_impossible) — row is not clickable, shown for honesty
- Below each row, a `font-body text-small text-text-muted` caption with the feasibility mode in **human words** — per §2 Decision #12, never the internal mode name. Student-facing copy map: `direct_hit` → "Direct match" (or omit pill entirely); `crosswalk_quirk` → "Through [Program] program" (name the broader program specifically); `adjacent_reachable` → "As a concentration" or "Inside [Program]"; `school_gap` → "Not offered here"; `genuinely_impossible` / `meme_redirect` never surface. Sentence-case so it reads like a thought, not a schema value.
- **Back-to-original ghost button** — `◂ Back to original`. Returns the preview to its pre-chip state (resolution unchanged, debug trace dismissed).

**When Gemma's response includes a new resolution (`updated_resolution`):**
- The resolution header in the top of the card animates — `updated_resolution.matched_title` crossfades from `accent-insight` to a brief `accent-thrive` flash (the same 320ms confirm-flash pattern from the Tiered Match Card), then settles back to `accent-insight`. The program title updates in place via Framer Motion `layout` animation. The career list below transitions to the new resolution's tiers once the trace is acknowledged (by clicking a career, or by tapping `Back to original` which also reverts).

#### D Mobile Considerations

- Community card: same content, full width, each row a `py-4` tap target (≥44px).
- Debug trace: same structure, the reasoning card is full-width. Feasibility list rows stack the caption below the title (not beside) on mobile for readability.
- Back-to-original button: full-width ghost in the inline flow (not sticky — it belongs to the content zone, not the commit zone).

---

## 3-chips. The Chip Rail — Full Treatment

Three chips. Kid-voiced labels. Fixed order.

| Slot | Label (kid-voiced) | Gemma? | Weight |
|---|---|---|---|
| 1 | **Not what I expected** | Yes (the heavy one) | Primary |
| 2 | **Show me less common paths** | No (pure frontend tier toggle) | Ghost |
| 3 | **Wrong major** | No (clears the major input) | Ghost |

**Why those labels:**
- "Not what I expected" is what a 17-year-old actually thinks. An engineer would write "Resolution mismatch." Per founder feedback on 2026-04-19, we use the student's voice, not ours.
- "Show me less common paths" is honest about what the toggle does — it reveals stretch tiers that were already computed. Not "Explore more" (vague) or "Advanced" (cold). It says what it does.
- "Wrong major" is the bluntest affordance. Two words. The student knows exactly what happens: the major input clears. No ambiguity, no undo anxiety.

### Visual Hierarchy — "Not what I expected" is primary

Rationale: §2 Decision #10 already softly privileges this chip via the low-confidence nudge. Visual weight reinforces the same preference. The Gemma-heavy chip is the product's flagship correction moment; if it looks like any other chip, we're hiding our best beat.

### Chip Specs

**Primary chip — "Not what I expected":**

```
Label:       "Not what I expected"  with <GemmaStar size={14} /> prefix
Font:        font-body, font-weight 700, text-small (14px)
Color:       text-accent-caution — "caution" is the chip's visual language,
             because tapping it means "I'm uncertain, re-check this."
Background:  rgba(242, 212, 119, 0.12)  (caution at 12% — see DESIGN.md
             "pill-caution" pattern, slightly subtler)
Border:      1px solid rgba(242, 212, 119, 0.28)
Radius:      radius-full (9999px — it's a pill)
Padding:     10px 18px   mobile: 12px 16px (full-width)
Icon:        GemmaStar to the left of the label, gap-2
Shadow:      subtle shadow-sm; hover escalates to shadow-glow-caution at 0.18 alpha
```

States:
- **Default:** as above. The GemmaStar gradient (info→insight) signals "Gemma will be invoked" without having to say it.
- **Hover:** background to `rgba(242, 212, 119, 0.18)`, border to `rgba(242, 212, 119, 0.42)`, `shadow-glow-caution` (0.18 alpha), translateY(-1px), `cursor: pointer`.
- **Pressed:** `scale(0.97)` via `transitions.press`.
- **Disabled (no resolution present yet):** background to `--color-state-disabled` (already defined), text to `text-text-muted`, GemmaStar desaturates to `text-muted`, `cursor: not-allowed`. No hover effect. `aria-disabled="true"`.

**Ghost chips — "Show me less common paths" and "Wrong major":**

```
Label:       (as above)
Font:        font-body, font-weight 600, text-small (14px)
Color:       text-text-secondary
Background:  transparent
Border:      1px solid border-default (rgba 255,255,255,0.1)
Radius:      radius-full
Padding:     10px 18px   mobile: 12px 16px (full-width)
Icon:        none
```

States:
- **Hover:** background `rgba(255, 255, 255, 0.04)`, border `border-strong`, text brightens to `text-text-primary`.
- **Pressed:** `scale(0.97)`.
- **Disabled:** "Show me less common paths" disables when the resolution has no less-common tier (feature flag). "Wrong major" disables when the major field is already empty. Disabled rules identical to primary.
- **Active ("Show me less common paths" after toggle ON):** background `--color-state-active` (rgba 125,212,163,0.1), border `rgba(125, 212, 163, 0.28)`, label prefixed with `✓` in `text-accent-thrive`. Tapping again toggles OFF and reverts to default.

**Layout rules:**
- Desktop: chips wrap in a `flex flex-wrap gap-2` row. Primary chip first. If the three chips fit on one line, single-line. If not, wrap (primary on its own line, ghosts on the second).
- Mobile: vertical stack, each chip full-width with `gap-2`. Primary on top. This is the only place we use full-width chips — the rail design doesn't fight small screens.

**Accessibility:**
- Each chip is a `<button type="button">`.
- Primary chip `aria-label="Not what I expected — get Gemma to re-check"`.
- Disabled states use `aria-disabled`, not the HTML `disabled` attribute (so screen readers still announce them).
- Focus ring: `--color-focus-ring` (already defined — rgba 123,184,224,0.4).

**Motion:**
- Rail entrance: `staggerContainer(0.15, 0.05)` wrapping the chips; children use `staggerItem` (fade up, y:8).
- On low-confidence resolution (§2 Decision #10), the primary chip gets a one-time breathing-glow pulse: `shadow-glow-caution` alpha animates from 0 → 0.28 → 0.14 over 1.6s, loops twice, then stops. This is the visual of the soft-nudge — the chip is literally glowing at you without being intrusive. See §8 for full nudge treatment.

---

## 4. The Clarifier — Inline Expansion on Desktop, Bottom Sheet on Mobile

When the student taps "Not what I expected," Gemma doesn't fire yet. We need the clarifier first: *"What were you hoping to see? Name a job, a field, whatever's missing."*

### Why inline / sheet, not modal

A modal steals the viewport. It would also steal focus from the career preview the student is correcting — which defeats the purpose (the preview is context for what the student is reacting against). On desktop, inline expansion keeps the career preview visible above. On mobile, a bottom sheet is the native-feeling gesture for a scoped text input that needs the keyboard — the preview scrolls out of frame naturally as the keyboard rises.

### Desktop — Inline Expansion

The primary chip expands downward into a text input. The other two chips remain visible.

```
 ─── Something feel off? ───
 ┌────────────────────────────────────┐
 │ [GS] Not what I expected         ▼ │   ← chip is now "active," border glows
 │ ┌────────────────────────────────┐ │
 │ │ What were you hoping to see?   │ │   ← label
 │ │ Name a job, a field, whatever's│ │
 │ │ missing.                       │ │
 │ │                                │ │
 │ │ (I wanted actual marketing…  ⌯)│ │   ← text input, 48px tall
 │ │                                │ │
 │ │   [Cancel] ghost   [Ask Gemma] │ │   ← primary CTA
 │ └────────────────────────────────┘ │
 └────────────────────────────────────┘
 [ Show me less common paths ] ghost
 [ Wrong major ]             ghost
```

**Anatomy:**
- Chip transforms into a container. Same caution border, now slightly expanded: `border-accent-caution/50`. `shadow-glow-caution` persists subtly (0.14 alpha).
- Inside, a labeled input. Label: `font-body text-small font-semibold text-text-secondary mb-1`. Sub-label: `font-body text-small text-text-muted`.
- Input: standard input spec (`bg-bp-deep`, `border-default`, `rounded-md`, 48px). Placeholder: *"e.g. brand manager, UX designer, something with less math…"* in `text-text-muted italic`. Placeholder echoes the prompt's permissive framing.
- Submit label: **"Ask Gemma"**. Primary thrive button, 44px tall, 0 24px padding. `GemmaStar` prefix inside the button label, `gap-2`. When clicked, button disables, label morphs to "Asking…" with the `GemmaThinking` spinner inline (replacing the star).
- Cancel: ghost button, collapses the expansion and returns the chip to default state. No Gemma call.
- Keyboard: `Enter` in the input submits. `Escape` cancels. Focus lands in the input on expand.

**Motion:**
- Expand: container height animates from chip-height to expanded-height with `springs.smooth`, `layout` transition. The two sibling chips reflow downward via `layout` animation.
- Submit button → morph: the button does NOT swap to a spinner inside itself. Instead, the button scales to `0.97` on press, then the entire clarifier panel transitions to the debug-trace card (see State D.2). One continuous gesture.
- Cancel: reverse of expand. `springs.smooth`, 200ms.

### Mobile — Bottom Sheet

Tap the primary chip → bottom sheet rises from the viewport bottom. Covers the lower ~55% of the screen. Preview content above dims to `bg-bp-void/60`.

```
 (dimmed content above)
 ──────────────────────────────────────
 ╭──────────────────────────────────╮
 │  ⎯ (grab handle)                 │
 │                                  │
 │  What were you hoping to see?    │
 │  Name a job, a field, whatever's │
 │  missing.                        │
 │                                  │
 │  ┌────────────────────────────┐  │
 │  │ (I wanted actual marketing │  │
 │  │  jobs                   ⌯) │  │
 │  └────────────────────────────┘  │
 │                                  │
 │  ┌────────────────────────────┐  │
 │  │     [GS] Ask Gemma         │  │  primary, full-width, 48px
 │  └────────────────────────────┘  │
 │                                  │
 │       Cancel                     │  ghost, inline text
 ╰──────────────────────────────────╯
```

**Anatomy:**
- Sheet container: `bg-bp-mid rounded-t-[20px]` (only top corners), `border-t border-border-strong`, `shadow-lg`, safe-area inset respected at the bottom.
- Drag handle: a 4px-tall, 40px-wide rounded bar in `bg-bp-raised/40` at the top-center, `mt-2 mb-4`. Visual only on mobile; not interactive in MVP (no drag-to-dismiss — tap Cancel or submit).
- Same copy as desktop. Input gets an autofocus → keyboard rises.
- Backdrop: `bg-bp-void/70 backdrop-blur-[6px]`. Tapping backdrop dismisses (acts as Cancel).

**Motion:**
- Enter: slide up from y:100% to y:0 with `springs.smooth`. Backdrop fades in with `transitions.fade` (200ms).
- Exit: reverse.
- On submit: sheet slides down, backdrop fades out, and the streaming debug trace begins in the right column of the underlying screen. The student should feel the clarifier hand off its intent to the reasoning stream.

### Commit Behavior

- On submit, call `dispatchChip({chip_id: "not_expected", clarifier: text, …})`.
- While the request is in flight, keep the clarifier panel open on desktop and the sheet open on mobile? **No.** Dismiss the clarifier immediately on submit. The streaming trace below is now the affordance. Leaving the clarifier open creates two competing focus points.
- On response arrival, the trace renders (State D.2). If `updated_resolution` is non-null, the resolution header updates. If `bucket == "no_issue_found"`, the response is the trace itself with no resolution change; the chip returns to default state once the student dismisses via `Back to original`.
- If the chip response includes `confirmed_focus` (per `feature-set-your-course.md` §2 Decision #16), the resolution header grows a small secondary label below the main program title: `font-body text-caption text-text-secondary`, prefixed with a soft dot glyph (`•`) and the focus string (student's own words). Example: program title reads "Special Education program," the sub-label reads "• Deaf Education." The sub-label uses `accent-insight` for the dot. Tile content is unchanged — the 4-digit grain invariant holds; this is a voice-layer signal to the student that Gemma heard them. The sub-label persists through streaming updates of downstream surfaces in the same session and clears if the student edits the major input (which re-resolves from scratch).

---

## 5. Streaming Gemma Reasoning — The Visual Treatment

This is the product's flagship Gemma moment. Do not ship a spinner.

### The Goal

- "Gemma is reading" should feel like a person reading, not like a page loading.
- Text should arrive at a cadence that matches how a thoughtful response is composed, not how HTTP chunks happen to be shaped.
- The student's eye should follow the reasoning in real time. If the student looks away, they can look back and the text is still there — it's not a ticker.

### The Cadence: Paragraph-By-Paragraph With Shimmer-On-Arriving-Sentence

**Token-by-token is rejected.** It causes layout jitter, text reflow, and a teletype feel that reads as "bot," not "thought." We watched this in the prototype. It felt broken.

**Paragraph-by-paragraph with a sentence-level shimmer** is the call:

1. Each streamed chunk accumulates in a buffer.
2. When the buffer ends with terminal punctuation (`.`, `!`, `?`, newline), we flush a **sentence** into the DOM.
3. Sentences within a paragraph accumulate. Each just-arrived sentence gets a 320ms shimmer sweep: a soft `accent-insight` gradient glides left-to-right across the text, then settles.
4. When a newline arrives, the paragraph is finalized (cursor moves to a new line). Previous paragraphs are "settled" — no shimmer, full opacity.
5. The cursor `█` stays at the end of the latest paragraph. It's `text-accent-insight`, blinks on a 1.2s pulse, and disappears when the stream closes.

**Why shimmer instead of opacity-ramp or typing-out:**
- Typing-out is deceptive when Gemma isn't actually typing at that rate.
- Opacity ramp (fade each word in) is subtle but visually weak.
- Shimmer reads as "this text is still cooling" — like a bar of metal that just came out of a forge. It's the same metaphor as the breathing glow. It ties the reasoning visually to the rest of the Gemma family.

### Shimmer Technical Details

The shimmer is a pseudo-element `::after` on each arriving sentence, positioned absolute, `width: 100%`, `height: 100%`, with a horizontal linear gradient:

```css
background: linear-gradient(
  90deg,
  transparent 0%,
  rgba(184, 169, 232, 0.22) 50%,
  transparent 100%
);
background-size: 50% 100%;
animation: gemma-shimmer 320ms ease-out forwards;
```

Where `gemma-shimmer` is a keyframe sweeping `background-position` from `-50% 0%` to `150% 0%` — left edge to right edge. After 320ms the gradient is gone and the text settles to `text-text-primary`.

**Pre-shimmer text color:** `text-text-primary` at `opacity: 0.6`. **Post-shimmer:** `opacity: 1`. The transition from 0.6 to 1 happens under the shimmer sweep so the eye reads "this sentence just got real."

**Add the keyframe to `index.css`** alongside `vertex-glow-pulse` and `ambient-breathe`. No new tokens — the color is `rgba(184, 169, 232, 0.22)`, which is the existing insight glow color at a specific alpha. It's an inline value, not a new token.

### Applies To Both Flows

The exact same shimmer cadence applies to:
- The initial resolution reasoning stream (State B).
- The chip-triggered debug trace (State D.2).

Consistency is the point. The student learns once: "text with a purple sweep is Gemma reasoning, live."

### Framer Motion Wrapping

```tsx
<AnimatePresence mode="wait">
  {phase === "streaming" && (
    <motion.div
      key="stream"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.98 }}
      transition={springs.smooth}
      className="reasoning-card"
    >
      <StreamingReasoning paragraphs={streamed} cursor={streamOpen} />
    </motion.div>
  )}
</AnimatePresence>
```

The card itself fades in with `springs.smooth`, but the internal paragraph/sentence shimmer is CSS keyframe — Framer Motion is for the container, CSS is for the live text. (We do not want Framer re-rendering every sentence append; DOM-append with a CSS-only shimmer is cheaper and smoother.)

### Stream-End Transition

When Gemma finishes, the reasoning card compresses into the one-line resolution header. The mechanic:
1. Cursor `█` fades out (200ms).
2. 180ms beat.
3. Reasoning card `layout` animates its height down to 0 while paragraphs fade out (`scale 0.96`, `opacity → 0`, `springs.smooth`).
4. Simultaneously the one-line resolution header fades in from below (`y: 8 → 0`, `opacity → 1`, `springs.smooth`, delay 120ms).
5. The career preview entrance begins at the same moment as the resolution header (`staggerContainer(0.25, 0.05)` wrapping `CareerTierSection` rows).

Total transition: ~700ms. Deliberately calm. The student should feel Gemma handing off to the career data.

---

## 6. Community Suggestions Section

Covered structurally in State D.1 above. Additional detail:

### Copy Conventions

All copy follows voice guide (`docs/reference/voice-guide.md`).

- Header: `OTHER STUDENTS SEARCHING "<input>" AT <SCHOOL> ENDED UP HERE`. Section-label treatment (`font-data`, uppercase, tracking-wide, `text-accent-info`). School name is truncated with ellipsis after 30 chars; input is truncated after 24 chars. Full values are preserved in `title` attribute.
- Row count: `<N> students`. Zero pluralization edge case: count is always ≥1 (threshold per §1 is min count 1 during hackathon). On count of exactly 1: `1 student`. Never `0 students` — that row doesn't render.
- Empty state: **absent**. No "No community suggestions yet." No card. No rule. Nothing. Per voice guide: filler politeness is noise.
- Expansion label (when >3 suggestions): `Show <N> more`. When expanded, the label is `Show fewer`. Both in `font-body text-small text-accent-info`.

### Click → Swap Animation

Timing (see §12):
1. `t=0`: click.
2. `0–180ms`: row flashes `bg-[rgba(125,212,163,0.12)]`, title morphs from `accent-info` to `accent-thrive`, count pulses scale 1 → 1.08 → 1.
3. `180ms`: resolution header crossfade begins. Old title fades to 0 (`springs.smooth`), new title fades in from `y:6` simultaneously. Old career list fades/slides out with a stagger (`stagger.fast`, reversed — bottom rows exit first). Inbound career list queues.
4. `280ms`: new career list streams in with `staggerContainer(0, 0.05)`.
5. `460ms`: row settles back to default appearance (title still `accent-info`; the thrive flash is the commit moment, not the resting state). Count now shows the incremented value.

Total feel: <500ms. The swap is confident, not slow — community suggestions are the fastest path in the product.

### The "Feels Honest, Not Creepy" Rule

- We show counts, not percentages. A count is a fact; a percentage feels like a nudge.
- We show schools + input as presented, not inferred traits ("students like you"). The voice guide forbids infantilizing copy; "students like you" implies profiling.
- We cap at 3 visible and hide the tail behind an expand. If the tail is long, we're not forcing a student to scroll past a social-proof stack.
- The section is absent when empty. It does not announce itself to populate itself.
- No names. No avatars. No timestamps. Just career + count.

---

## 7. Career Preview — Live-Update Adaptation of `CareerTierSection`

The spec calls for reusing the existing `CareerTierSection` component. It already handles:
- Tier rendering (Common / Less Common / Stretch)
- Row styling (`font-body text-body-sm font-semibold text-accent-info`, `▸` glyph)
- Hover and selection states

### What Changes For Live-Update

1. **Transition between resolutions.** When `currentResolution` swaps (either via streaming-completion, chip-swap, or community-click), `CareerTierSection` should not remount. It should animate between states.

   Implementation: wrap each row in a Framer Motion `<motion.li key={soc}>` with `layoutId={soc}`. Cross-resolution shared rows will `layout`-animate to their new positions. New rows fade in with `transitions.fadeInUp`. Removed rows fade out with `transitions.fade` (scale 0.98).

   This creates a fluid reshuffle — if "Financial Analyst" is common in resolution A and less-common in resolution B, it physically moves. The student sees relationships between resolutions, not just two separate lists.

2. **"Show me less common paths" toggle.** When active (chip 2 toggled ON), the Less Common and Stretch tiers become visible with `springs.smooth` entrance. Section labels (`LESS COMMON`, `STRETCH`) follow the existing `SectionLabel` primitive — `text-accent-info`. Toggling OFF collapses them back with the reverse motion.

3. **Feasibility badges in debug-trace mode.** In State D.2, each row gets a right-aligned feasibility badge (`◆ fits`, `◇ not here`, `◇ no path`) per §3 State D.2. In normal mode, no badges.

### Row Click

In normal (non-debug) mode, rows are not primary-clickable. The student commits via the commit bar, not by clicking a career. This is deliberate: the Set Your Course screen is about resolving the major → career map, not picking a single career. Career picking happens downstream.

In debug-trace mode (State D.2), rows are clickable — clicking commits to that career's resolution (via the correction-log write with the clicked career's feasibility mode). Same visual treatment as community-suggestion click: 180ms thrive flash, resolution crossfade, trace dismisses.

---

## 8. Commit CTA + Low-Confidence Nudge + Start Over

### Commit Button

`<Button variant="primary">` per DESIGN.md spec:
- Background: `accent-thrive` (#7DD4A3)
- Text color: `text-inverse`
- Height: 48px
- Padding: 0 28px
- Font: `font-body font-weight 700 text-cta (17px)`
- Label: **"Yes, continue"**

Label rationale: a 17-year-old responding to a preview says "yes, that's me." "Continue" alone is transactional; "Yes, continue" is confirmatory. It's a small but important kid-voice cue.

### Start Over

`<Button variant="ghost">` per DESIGN.md:
- Background: transparent
- Text: `text-text-secondary`, hover brightens to `text-text-primary`
- Height: 40px
- Padding: 0 16px
- Label: **"Start over"**

On click, the store resets to the empty state (school cleared, major cleared, resolution cleared, effort/loans back to default). Stay on the screen. The commit bar returns to its disabled styling. The preview returns to State A.

### Low-Confidence Soft Nudge (per §2 Decision #10)

When the current resolution has `confidence: "low"` or `confidence: "medium"`:

1. The primary chip ("Not what I expected") gets the one-time breathing pulse described in §3-chips.
2. A small nudge line appears directly above the commit button in the commit bar: *"Want to double-check this first?"* — `font-body text-small text-text-muted italic`, right-aligned on desktop, centered on mobile.
3. The commit button is **enabled, not gated**. Hovering it still works. Clicking it still commits. We do not block the student.
4. The nudge disappears once the student either commits or dispatches any chip (even the ghost chips — tapping any chip satisfies the "double-check" framing).

**What this looks like on desktop:**

```
 ┌──────────────────────────────────────────────────────────────────────────┐
 │                               Want to double-check this first?           │
 │        [Yes, continue]  primary          [Start over]  ghost             │
 └──────────────────────────────────────────────────────────────────────────┘
```

**What this looks like on mobile (sticky bar):**

```
 ┌────────────────────────────────────────┐
 │      Want to double-check this first?  │
 │  [Start over]       [Yes, continue]    │
 └────────────────────────────────────────┘
```

The nudge is one line, 14px, muted. It is a whisper, not a warning. On `confidence: "high"`, the nudge is absent; the commit is frictionless.

### Commit → Navigate Transition

On commit:
1. `t=0`: click. Button scales to 0.97 (`transitions.press`).
2. `0–200ms`: commit fires — correction log write if applicable (silent, non-blocking), state handoff.
3. `200ms`: full-screen transition begins. Entire screen fades out (`transitions.fade`, 250ms) while the underlying page color shifts toward `bg-void` (for the cinematic reveal that follows).
4. `450ms`: navigate to `/reveal`.

No celebratory moment here. Commit is matter-of-fact. The cinematic beat is the reveal that follows, not the commit itself.

---

## 9. School-Gap CTA Link

When Gemma's chip-debug response classifies a candidate career as `feasibility_mode: "school_gap"`, the `ChipResponse` includes a CTA linking to `/discover?cip=<cip4>`. This is a leave-the-screen gesture — it belongs to a different affordance family than the correction chips or community cards.

### Where It Renders

Inside the debug-trace card (State D.2), directly below the feasibility-tagged career list, as a **full-width tile** (not a chip, not a pill). Rationale: a tile signals "go somewhere"; a chip signals "refine here." Mixing them muddles the mental model.

### Visual

```
 ┌─────────────────────────────────────────────────┐
 │  ◇  This school doesn't offer that path.         │
 │                                                  │
 │  Marketing Manager comes from a Marketing degree │
 │  (Marketing). IU doesn't offer that program.     │
 │                                                  │
 │  [ Find schools with this major  ▸ ]             │
 └─────────────────────────────────────────────────┘
```

**Tokens:**
- Container: `bg-bp-mid border border-border-subtle rounded-xl p-5`, left border `border-l-[3px] border-accent-caution`. Same visual family as the reasoning card, different semantic accent — caution says "this is a constraint, not a failure."
- Icon: `◇` glyph (24px, `text-accent-caution`) floating top-left, complementing the border stripe.
- Title: *"This school doesn't offer that path."* — `font-display text-subheading font-semibold text-text-primary`.
- Detail: *"`<Career>` typically comes from a `<program_title>` degree. `<School>` doesn't offer that program."* — `font-body text-body text-text-secondary`. Data interpolated from the chip response's careers list. Per §2 Decision #12, **never render the numeric CIP4** in student-facing detail copy. The `cip4` value lives in the href query string, not in the rendered prose.
- CTA: `<Button variant="secondary">` — per DESIGN.md: transparent background, `text-accent-info`, border `border-accent-info/50`, hover adds `rgba(123, 184, 224, 0.1)` background. Label: **"Find schools with this major"** + `▸` glyph (`gap-2`). Font: `font-body font-weight 700 text-small`.
- Click: navigates to `/discover?cip=<cip4>` with a route-level transition (screen fades to `bg-void`, then Discover screen fades in). The current Set Your Course state is preserved in `buildInputStore` so the student can come back.

**Motion:** tile entrance is `transitions.fadeInUp` with `springs.smooth`, 120ms delay after the feasibility-list rows have settled.

### Multiple School-Gap Candidates

If the debug trace surfaces multiple `school_gap` careers, render ONE tile that batches them: *"These paths aren't at this school."* Career list is a dense line inside the tile (`font-body text-body-sm text-text-muted`, comma-separated titles). Single CTA that links to `/discover?cip=<primary_cip>` where `primary_cip` is the highest-confidence gap target.

---

## 10. Brightpath Tokens — Exhaustive Usage Map

Every surface on this screen maps to a specific token. No new tokens are introduced.

### Backgrounds

| Surface | Token |
|---|---|
| Page background | `--color-bg-deep` + existing radial gradient overlay (unchanged from global treatment) |
| Input fields (`bg-deep`) | `--color-bg-deep` |
| Reasoning card interior | `--color-bg-deep` at 60% alpha (composed: `bg-bp-deep/60`) |
| Community suggestions card | `--color-bg-mid` |
| Debug-trace feasibility list | `--color-bg-mid` |
| Chip active bg (less-common ON) | `--color-state-active` |
| Chip disabled bg | `--color-state-disabled` |
| Clarifier bottom-sheet bg | `--color-bg-mid` |
| Bottom-sheet backdrop | `--color-bg-void/70` + `backdrop-blur-[6px]` |
| Sticky commit bar (mobile) | `--color-bg-deep/92` + `backdrop-blur-md` |

### Accents

| Element | Token |
|---|---|
| Resolution title (default) | `--color-accent-insight` |
| Resolution title (low-confidence) | `--color-accent-caution` |
| Resolution title (confirm flash, 320ms) | `--color-accent-thrive` |
| Gemma attribution star gradient | `--color-accent-info` → `--color-accent-insight` |
| Reasoning card left stripe | `--color-accent-insight` |
| Debug-trace reasoning card left stripe | `--color-accent-insight` |
| School-gap tile left stripe | `--color-accent-caution` |
| Primary chip bg wash | rgba derived from `--color-accent-caution` at 0.12 |
| Primary chip text + icon | `--color-accent-caution` |
| Ghost chip text | `--color-text-secondary` (default) / `--color-text-primary` (hover) |
| Commit button | `--color-accent-thrive` |
| Community row title | `--color-accent-info` (default) → `--color-text-primary` (hover) → `--color-accent-thrive` (180ms click flash) |
| Feasibility `fits` badge | `pill-thrive` pattern |
| Feasibility `not here` badge | `pill-caution` pattern |
| Feasibility `no path` badge | `pill-alert` pattern |

### Text

| Element | Token |
|---|---|
| H1 "Where does this take you?" | `--color-text-primary` + `font-display text-heading font-semibold` |
| Eyebrow "SET YOUR COURSE" | `--color-accent-info` + `font-data text-[11px] font-bold tracking-[2px] uppercase` |
| Supporting subhead | `--color-text-secondary` + `font-body text-body` |
| Input labels | `--color-text-secondary` + `font-body text-small font-semibold` |
| Placeholder copy | `--color-text-muted` italic |
| Resolved reasoning paragraph (settled) | `--color-text-primary` + `font-body text-body` |
| Resolved reasoning paragraph (arriving, pre-shimmer) | `--color-text-primary` at `opacity-60` |
| ~~CIP code~~ — per §2 Decision #12 never rendered in student-facing UI | Internal IDs only (logs, schemas, URL query strings, engineer tooltips); no visible surface. Token assignment N/A. |
| Community suggestion count | `--color-text-muted` + `font-data text-data-sm` |
| Low-confidence nudge | `--color-text-muted` + `font-body text-small italic` |
| Section labels ("WHERE THIS LEADS", "OTHER STUDENTS…") | `--color-accent-info` + `font-data text-[11px] font-bold tracking-[2px] uppercase` |
| School-gap tile title | `--color-text-primary` + `font-display text-subheading font-semibold` |
| School-gap tile body | `--color-text-secondary` + `font-body text-body` |

### Borders

| Element | Token |
|---|---|
| Input default border | `--color-border-default` |
| Input focus border | `--color-accent-info` + 3px ring at `--color-focus-ring` |
| Reasoning card border | `--color-border-subtle` + 3px left in `--color-accent-insight` |
| Community card border + row dividers | `--color-border-subtle` |
| Chip primary border | rgba derived from `--color-accent-caution` at 0.28 |
| Chip ghost border | `--color-border-default` (hover: `--color-border-strong`) |
| School-gap tile border | `--color-border-subtle` + 3px left in `--color-accent-caution` |
| Commit bar top border (mobile sticky) | `--color-border-subtle` |
| Details panel rule | `--color-border-subtle` |
| Feasibility list row dividers | `--color-border-subtle` |

### Radii

| Element | Token |
|---|---|
| Inputs | `--radius-md` (10px) |
| Inputs (large variant — school picker) | `--radius-lg` (14px) |
| Reasoning card, community card, debug-trace card, school-gap tile | `--radius-xl` (20px) |
| Chips (pills) | `--radius-full` |
| Commit button, Ask Gemma button | `--radius-lg` (14px — DESIGN.md button spec) |
| Bottom sheet | `--radius-xl` top corners only |

### Shadows

| Element | Token |
|---|---|
| Default cards | `--shadow-md` |
| Reasoning card breathing glow | Inline composition of two `--shadow-glow-insight`-family values (0.08 and 0.18 alpha) in a keyframe |
| Primary chip hover glow | `--shadow-glow-caution` at 0.18 alpha |
| Primary chip nudge pulse | `--shadow-glow-caution` animating 0 → 0.28 → 0.14 over 1.6s |
| Commit button hover | `--shadow-glow-thrive` |
| Bottom sheet | `--shadow-lg` |

### Spacing (page-level)

| Slot | Value |
|---|---|
| PageContainer horizontal padding (desktop) | `--layout-grid-gutter-desktop` (32px) |
| PageContainer horizontal padding (tablet) | `--layout-grid-gutter-tablet` (24px) |
| PageContainer horizontal padding (mobile) | `--layout-grid-gutter-mobile` (16px) |
| Between major sections (intro → inputs, etc.) | `--space-10` (40px) desktop, `--space-6` (24px) mobile |
| Between inputs within left column | `--space-6` (24px) |
| Reasoning card padding | `--space-5` (20px) |
| Community card row padding | `12px 18px` (List Item pattern) |
| Chip padding | `10px 18px` (desktop), `12px 16px` (mobile full-width) |
| Commit bar padding (sticky mobile) | `--space-4` (16px) top/bottom, `--space-4` horizontal + safe-area inset |

### Motion Tokens

| Interaction | Motion token |
|---|---|
| Screen entrance (intro, inputs) | `transitions.fadeInUp` + `staggerContainer(0, 80ms)` wrapping `staggerItem` children |
| Reasoning card entrance | `transitions.fadeInUp`, `springs.smooth` |
| Reasoning card exit (compressing to header) | `springs.smooth`, 200ms |
| Chip hover | `transitions.press`-like `scale(1.02)` on hover, `scale(0.97)` on press |
| Chip rail entrance | `staggerContainer(0.15, 50ms)` + `staggerItem` |
| Low-confidence chip pulse | CSS keyframe pulsing `shadow-glow-caution` alpha, 1.6s, 2 iterations |
| Clarifier expand (desktop inline) | `springs.smooth`, `layout` animation |
| Clarifier sheet enter (mobile) | `springs.smooth`, y:100% → 0 |
| Debug-trace replace career preview | `springs.smooth` with `layoutId` shared on matching career rows |
| Community row click → swap | 180ms thrive flash (CSS), 280ms resolution crossfade (`springs.smooth`) |
| Commit press | `transitions.press` |
| Commit → navigate | `transitions.fade` 250ms, then router transition |

**No new motion tokens are introduced.** Every interaction composes from the existing four springs, three stagger delays, and four transitions.

---

## 11. Component Breakdown — Full File-Level Map

Aligns with §4 of the spec.

```
frontend/src/screens/SetYourCourseScreen.tsx              [NEW — screen root]
├── Uses: PageContainer (existing)
├── Uses: SchoolPicker (existing)
├── Uses: MajorInput (existing, wired to useSetYourCourse)
├── Uses: DetailsPanel (existing EffortLoansPanel bits, wrapped in collapsing <details>)
├── Uses: ResolutionHeader (NEW — components/school/ResolutionHeader.tsx)
├── Uses: StreamingReasoning (NEW — components/school/StreamingReasoning.tsx)
├── Uses: CareerTierSection (existing, with layoutId prop added)
├── Uses: CommunitySuggestions (NEW — components/school/CommunitySuggestions.tsx)
├── Uses: CorrectionChips (NEW per spec — components/school/CorrectionChips.tsx)
├── Uses: ClarifierSheet (NEW — components/school/ClarifierSheet.tsx; renders inline on desktop, bottom-sheet on mobile via responsive composition)
├── Uses: DebugTraceReader (NEW — components/school/DebugTraceReader.tsx; renders reasoning card + feasibility list)
├── Uses: SchoolGapCTA (NEW — components/school/SchoolGapCTA.tsx)
├── Uses: CommitBar (NEW — components/school/CommitBar.tsx; handles desktop-inline vs mobile-sticky)
└── Uses: LowConfidenceNudge (NEW — components/school/LowConfidenceNudge.tsx; small single-line nudge, rendered from CommitBar)

frontend/src/hooks/useSetYourCourse.ts                    [NEW per spec]
├── Owns: debounced major resolution (300ms)
├── Owns: AbortController lifecycle for streaming
├── Owns: chip dispatch for all 3 chips
├── Owns: clarifier open/close state
├── Owns: community-suggestion click handler
├── Owns: commit handler (correction-log write + navigate)
├── Reads: buildInputStore (school, major, effort, loans, resolutions)
├── Writes: buildInputStore (currentResolution, initialResolution, hasCorrected, debugTrace)
└── Returns: { state, chips: { onNotExpected, onShowLessCommon, onWrongMajor }, onCommit, onStartOver, onCommunityClick, onClarifierSubmit, onBackToOriginal }

frontend/src/api/intent.ts                                [MODIFY per spec]
├── streamIntent(input, signal)        — NEW, SSE or chunked JSON stream
└── dispatchChip(chipId, clarifier, currentState, signal)  — NEW

frontend/src/store/buildInputStore.ts                     [MODIFY per spec]
├── + currentResolution: IntentResult | null
├── + initialResolution: IntentResult | null
├── + hasCorrected: boolean
├── + debugTrace: ChipResponse | null
└── + communitySuggestions: Suggestion[]
```

### `ResolutionHeader.tsx` (new)

Renders the one-line resolved header: `[GS] Gemma matched "input" → Title`. Props: `{ input, resolvedTitle, cip, confidence }` — `cip` is passed for analytics / URL purposes but **never rendered**. Switches title color per the tiered-match pattern: `accent-insight` default, `accent-caution` low-confidence, `accent-thrive` on confirm flash.

### `StreamingReasoning.tsx` (new)

Receives a ReadableStream-like source of paragraphs. Accumulates into local state. Renders paragraphs in a `bg-bp-deep/60` card with the left stripe + breathing glow. Current paragraph gets the shimmer-on-arriving-sentence treatment described in §5. Cursor `█` is rendered conditionally while `streamOpen`.

### `CommunitySuggestions.tsx` (new)

Props: `{ suggestions: Suggestion[], input, schoolName, onClick(s: Suggestion) }`. Renders section label + list of up to 3 rows + optional "Show N more" expand. Absent when `suggestions.length === 0`.

### `CorrectionChips.tsx` (new per spec §4)

Props: `{ confidence, hasLessCommonTier, majorIsEmpty, onNotExpected, onShowLessCommon, onWrongMajor, showLessCommonActive }`. Renders three chips with the hierarchy and states specified in §3-chips. Owns the low-confidence breathing-pulse animation (via `AnimatePresence` and a one-shot keyframe).

### `ClarifierSheet.tsx` (new)

Responsive: on `≥tablet`, renders as inline expansion inside the first chip's location (using Framer `layout` animation to grow the chip into the container). On `<tablet`, renders as a bottom sheet with a backdrop. Shared internal form logic; the only difference is the wrapper.

### `DebugTraceReader.tsx` (new)

Replaces the career preview area when `debugTrace` is present. Renders breadcrumb, reasoning card (reusing `StreamingReasoning`), and a feasibility-tagged career list. Also renders the `Back to original` ghost button and conditionally embeds `SchoolGapCTA` when any candidate has `feasibility_mode: "school_gap"`.

### `SchoolGapCTA.tsx` (new)

Props: `{ careers: Career[], school, onNavigate(cip4) }`. Renders the single-career tile (§9) or the batched-multi tile per the multiple-school-gap rule.

### `CommitBar.tsx` (new)

Renders on desktop as inline bottom row, on mobile as sticky viewport-bottom bar. Includes `LowConfidenceNudge` when confidence warrants it. Responsive responsibility is isolated here; the rest of the screen stays layout-simple.

### `LowConfidenceNudge.tsx` (new)

Single-line whisper: *"Want to double-check this first?"*. Mounts/unmounts via `AnimatePresence` on confidence change and chip-tap-clears.

---

## 12. Interaction Timing — Precise Values

Every timing value is explicit. No hand-waving.

### Major Input Debounce

- `300ms` per §2 Decision #7.
- Implemented via `useDebounce` or `setTimeout` in `useSetYourCourse`. On every keystroke, the prior timer is cancelled and a new one starts.
- On fire: if an in-flight stream exists, abort it via its `AbortController`. Then call `streamIntent(input, newController.signal)`.
- User-typed characters during stream: abort and re-fire (cancel-and-restart per §2 Decision #7).

### Streaming Chunk Flush Cadence

- Stream source: SSE or chunked JSON — either is fine; both FastAPI and the fetch API support them. **Preference:** chunked JSON via `fetch().body.getReader()`. Rationale: no new deps, simpler backend. SSE's reconnection semantics are not needed because we abort-and-restart on edit.
- Each chunk: parse delta → append to buffer.
- Flush to DOM when the buffer contains terminal punctuation or 80 characters (whichever first). This avoids a pathological case where Gemma emits a long unpunctuated string.
- Paragraph boundary on `\n\n` → finalize the current paragraph (stop shimmering old sentences), start a new one.
- Shimmer per arriving sentence: `320ms` via the CSS keyframe defined in §5.

### Chip Tap → Clarifier Open

| Step | Time | Action |
|---|---|---|
| 0 | 0ms | Chip tap registered. Button scales to 0.97 (`transitions.press`). |
| 1 | 80ms | Button releases. Clarifier animation begins. |
| 2 | 80–380ms | Desktop: chip height animates from chip-height to expanded-height via `springs.smooth`. Mobile: bottom sheet translates from `y:100%` to `y:0` via `springs.smooth`. |
| 3 | 280ms | Input autofocuses. Keyboard rises on mobile (system-driven). |
| 4 | 380ms | Siblings (other two chips) finalize reflow. |

Total open gesture: ~380ms. Feels immediate without being abrupt.

### Clarifier Submit → Debug-Trace Stream

| Step | Time | Action |
|---|---|---|
| 0 | 0ms | Ask Gemma tap. Button scale 0.97. |
| 1 | 120ms | Dismiss clarifier — inline on desktop collapses (`springs.smooth`), bottom sheet slides down. |
| 2 | 120ms | `dispatchChip()` request fires in parallel. |
| 3 | 320ms | Clarifier is gone. Debug-trace reasoning card entrance begins (`transitions.fadeInUp`, `springs.smooth`). |
| 4 | 320ms + first chunk | Streaming begins. Paragraph-by-paragraph, sentence shimmer per §5. |
| 5 | stream end + 200ms hold | Reasoning settles. Feasibility-tagged career list entrance begins (`staggerContainer`, `stagger.fast`). |

### Community Suggestion Click → Resolution Swap

| Step | Time | Action |
|---|---|---|
| 0 | 0ms | Row click. |
| 1 | 0–180ms | Row flash: `bg-[rgba(125,212,163,0.12)]`, title → `accent-thrive`, count pulse 1 → 1.08 → 1 (`springs.snappy`). |
| 2 | 180ms | Resolution header old-title fade-out + new-title fade-in (280ms total, `springs.smooth`). Old career list staggered-fade-out (reversed stagger). |
| 3 | 280ms | New career list entrance (`staggerContainer(0, 50ms)`, `transitions.fadeInUp`). |
| 4 | 460ms | Row settles back to default. Count shows incremented value. |

Total swap: ~460ms.

### Commit → Navigate

| Step | Time | Action |
|---|---|---|
| 0 | 0ms | Button click, scale 0.97. |
| 1 | 80ms | Button releases. Correction-log write fires (non-blocking, silent; failure doesn't block nav per §2 Decision #4). |
| 2 | 200ms | Full-screen fade begins (`transitions.fade`, 250ms, ease-out). Background shifts toward `bg-void` simultaneously. |
| 3 | 450ms | Navigate to `/reveal`. |

Total: ~450ms from click to route change. Not celebratory. The celebration is the reveal screen.

### Start Over

| Step | Time | Action |
|---|---|---|
| 0 | 0ms | Button click, scale 0.97. |
| 1 | 120ms | Store reset. Inputs clear. Preview returns to State A with `transitions.fade` (300ms). |
| 2 | 420ms | Focus returns to school input. |

No navigation. The student stays on the screen.

---

## 13. Motion — Named Primitives in One Place

Consolidated from §10 and §12 for the implementing engineer.

### Springs Used

| Spring | Use sites |
|---|---|
| `springs.smooth` | Reasoning card enter/exit, resolution crossfade, clarifier expand/sheet, community swap, debug-trace transitions, card entrances |
| `springs.snappy` | Community row count pulse, chip hover scale |
| `springs.bouncy` | (reserved for downstream screens — not used on Set Your Course; this screen is deliberately calm) |
| `springs.gentle` | (reserved — not used here) |

### Staggers Used

| Stagger | Use sites |
|---|---|
| `stagger.fast` (50ms) | Career rows, feasibility-list rows, community rows |
| `stagger.normal` (80ms) | Intro block + inputs on mount |
| `stagger.slow` (100ms) | (not used here) |

### Transitions Used

| Transition | Use sites |
|---|---|
| `transitions.fadeInUp` | Reasoning card, debug-trace card, school-gap tile, community card, chips (individual) |
| `transitions.scaleIn` | (reserved — not used here; Set Your Course avoids bounce) |
| `transitions.fade` | Commit-out, start-over reset, empty-state preview |
| `transitions.press` | All button press feedback, chip press |

### Framer Motion `layout` Prop

Used on:
- `CareerTierSection` rows (`layoutId={soc}`) — for fluid tier reshuffle when resolution changes
- The primary chip's container during clarifier expansion
- The commit bar nudge line appearance/disappearance

### CSS Keyframes (defined in `index.css`)

| Keyframe | Use |
|---|---|
| `gemma-shimmer` (NEW — add alongside existing `vertex-glow-pulse`) | Sentence-arrival sweep |
| `ambient-breathe` (EXISTING) | Reasoning card breathing glow — reuse with adjusted alpha values inline |
| `chip-pulse-caution` (NEW — add alongside `vertex-glow-pulse`) | Low-confidence chip one-time breathing pulse, 1.6s × 2 iterations |

Only two new keyframes. Everything else is composition of existing tokens + Framer primitives.

---

## 14. Accessibility Notes

- All interactive elements have visible focus rings using `--color-focus-ring`.
- Chips are buttons with descriptive `aria-label`s (see §3-chips).
- The clarifier input has `aria-label` matching the label text.
- The reasoning card is wrapped in `<div role="status" aria-live="polite">` so screen readers announce the arriving text. Cursor `█` is `aria-hidden="true"` — it's decorative.
- The community list uses `<ul role="list" aria-label="Other students' resolutions at <school>">` and `<li>` for each row, each containing a `<button>` with the row content.
- Low-confidence nudge is `aria-describedby`-associated with the commit button so SR users understand the context without needing to find the nudge line separately.
- Bottom sheet has `role="dialog" aria-modal="true"` and a labeled close affordance. Tapping outside dismisses; `Escape` also dismisses.
- Tier toggle ("Show me less common paths") uses `aria-pressed` to reflect its active state.
- Stream end: when the reasoning card compresses, focus does not move (student may still be reading). But the resolution header is marked `role="status" aria-live="polite"` and announces the resolved title.

---

## 15. What Judging Sees (The 30% Demo Case)

The 3-minute hackathon video will almost certainly show this screen. Here is what makes it demo-gold:

1. **Type "marketing" at IU.** The reasoning card breathes into view. Paragraphs arrive with the insight-colored shimmer. The judge watches Gemma think in real time. No spinner.

2. **See Business/Commerce come back.** The student (demo narrator) reacts: "That's not marketing." They tap the caution-glowing primary chip.

3. **Clarifier rises.** The student types: "I wanted actual marketing jobs." Taps Ask Gemma.

4. **Debug trace streams.** Gemma reasons about IU's reporting quirk in plain English. The feasibility-tagged career list materializes: Marketing Manager `◆ fits · Through Business program`, Market Research Analyst `◆ fits · Direct match`.

5. **Click Marketing Manager.** The resolution header flashes thrive, swaps. The community count on this combo ticks up from whatever it was to one more.

6. **Commit.** The screen fades to the reveal.

That sequence — in under 40 seconds — demonstrates streaming inference, tool-calling-grounded reasoning, student-visible correction, a self-defending feasibility classifier, and the beginning of a crowd-signal reinforcement loop. No other hackathon submission will show all five in one interaction.

If the video shows anything else before this sequence, the video is wrong.

---

## 16. What I'm Explicitly Not Designing (And Why)

- **A modal for the clarifier.** Rejected in §1. Modals steal the preview context.
- **A typing indicator (the three-dot bubble).** Rejected. We're showing reasoning, not a chat. Three dots is chat UI; shimmer is reasoning UI.
- **"People are viewing this" social-pressure UI.** Rejected per voice guide and §6.
- **A "confidence meter" visualization.** The chip nudge + title color (insight/caution) already communicate confidence. A meter is data hype.
- **Avatars on community suggestions.** Rejected per §6. No names, no faces, no timestamps.
- **A secondary "I'm not sure, help me" chat affordance.** The three chips are the correction surface. Anything else bloats guardrails scope (§2 Decision #3).
- **A "back" button inside the reasoning card during stream.** You can't cancel Gemma mid-thought; you edit the input, which aborts the stream via the debounce cancel-and-restart. That's the cancel.
- **Animation on every single token.** Rejected in §5. Jitter reads as bot, not as mind.

---

## 17. Handoff Checklist for the Implementation Engineer

You should be able to start coding from this document without asking the designer anything.

- [ ] All component files to create are listed in §11.
- [ ] All tokens to use are listed in §10, mapped to surface.
- [ ] All motion primitives are listed in §13.
- [ ] All interaction timings are listed in §12.
- [ ] All copy strings are in §1, §3-chips, §4, §6, §8, §9 (bolded exact strings).
- [ ] The two new CSS keyframes (`gemma-shimmer`, `chip-pulse-caution`) are named in §13 and described in §3-chips and §5.
- [ ] Accessibility is covered in §14.
- [ ] Wireframes are in §3 for four states, mobile + desktop.
- [ ] Responsive breakpoints: use `tablet:` (768px) and `desktop:` (1200px) Tailwind prefixes. The `DetailsPanel` collapses at `< tablet`; the commit bar becomes sticky at `< tablet`; chips become full-width stacked at `< tablet`. The clarifier becomes a bottom sheet at `< tablet`. Nothing else is breakpoint-sensitive.

If you find a visual decision that isn't answered here, that's a design bug — ping @fp-design-visionary and we'll decide on the spot rather than guess.

---

*End of proposal.*
