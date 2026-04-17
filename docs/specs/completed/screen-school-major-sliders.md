# F2: `screen-school-major-sliders`

*Screens 3 & 4 — The Input Phase*

**Status:** COMPLETE (implementation shipped; spec file predates the §6/§9 agent-workflow convention — no per-spec implementation log. Verified 2026-04-15 via code audit: `SchoolMajorScreen.tsx` + `SchoolSearch.tsx` + `MajorInput.tsx` + `EffortLoansPanel.tsx` implemented end-to-end with backend `intent.py` + `schools.py` routers.)
**Depends on:** B1 (`fastapi-router-wiring`), F1 (`screen-landing-profile`)
**Governing doc:** PRD v8
**Reference implementation:** `backend/cli.py` → `_prompt_school()`, `_prompt_major_gemma_intent()`, `_prompt_effort()`, `_prompt_loans()`
**Design system:** Brightpath (`frontend/src/styles/tokens.css`, `frontend/tailwind.config.ts`)

-----

## What This Spec Builds

Two screens that collect the four inputs needed to compute a build: school, major, effort level, and loan percentage. The school search is fuzzy match against College Scorecard. The major input is the first Gemma showcase — free-text intent resolution with career previews, audit, and confirmation. The sliders adjust independent variables (ERN and ROI) with live stat preview. On completion, the student transitions to F3 (career pick + reveal).

This is the most Gemma-heavy frontend screen. Three distinct Gemma calls happen here (intent resolution → audit → optional clarification). The UI must make this feel fast and trustworthy, not like waiting for a chatbot.

-----

## Screen 3: School + Major

### Layout

Single-column centered layout. Max-width container (`max-w-lg`). Background: `bg-bp-deep`. The screen has two phases that transition vertically: school search (top) → major input (bottom, revealed after school is confirmed).

### 3A: School Search

**Header:** "Where are you headed?" — `font-display` (Fredoka), `text-xl`, `text-bp-text-primary`.

**Search input:** Single text field with placeholder "Search for your school..." Styled with `bg-bp-surface`, `border-bp-border-subtle`, `rounded-bp-md`. Focus ring uses `accent-insight`.

**Behavior:**

1. Student types. After 2+ characters and a 300ms debounce, call `GET /schools?q={query}`.
2. Results appear as a dropdown list below the input. Each result shows school name and city/state. Max 8 results visible, scrollable if more.
3. Student taps a result → school is selected. The search input collapses to a confirmed chip: "**Iowa State University** — Ames, IA" with an ✕ to clear and re-search.
4. On selection, fire `GET /schools/{unitid}/programs` to prefetch the program list. This list is passed to Gemma during intent resolution — it's what anchors the match to this specific school's actual offerings.

**Edge cases:**

- No results: Show "No schools found. Try a different name or abbreviation." below the input.
- Slow response: Show a subtle shimmer on the input border (Brightpath `transition-normal`, 200ms).

**Service call:** `school_lookup.search_schools(query)` → `SchoolMatch[]`

### 3B: Major Input (Gemma Intent Resolution)

Revealed after school is confirmed. Slides in below the school chip with a `transition-smooth` (300ms ease-out).

**Header:** "What do you want to study?" — same typographic treatment as school header.

**Input:** Single text field with placeholder "Type anything — 'pre-med', 'CS', 'business'..." Same styling as school search input.

**Submit:** Student hits Enter or taps a "→" button at the right edge of the input.

#### Intent Resolution Flow (3 Gemma calls)

**Call 1 — Intent Resolution:** `POST /intent`

Request body:
```json
{
  "school_unitid": 153603,
  "raw_text": "pre-med",
  "program_list": ["Biology", "Chemistry", "Nursing", ...]
}
```

Response:
```json
{
  "matched_cip": "26.0101",
  "matched_title": "Biology, General",
  "confidence": "high",
  "careers_preview": [
    "Physicians and Surgeons",
    "Medical Scientists",
    "Biological Technicians"
  ],
  "reasoning": "Pre-med students typically pursue Biology..."
}
```

**UI during Call 1:** The input text fades to `text-bp-text-muted` and a thinking indicator appears below — a pulsing dot sequence in `accent-insight` with text "Matching your input..." in `text-bp-text-secondary`. No spinner — the dots feel alive, not mechanical.

**UI after Call 1 — Match Presentation:**

A card appears below the input with a subtle `shadow-glow-insight` border:

```
Gemma matched "pre-med" →

📚 Biology, General (CIP 26.0101)

Graduates typically become:
  • Physicians and Surgeons
  • Medical Scientists
  • Biological Technicians

[✓ That's right]    [✎ Not quite]
```

The card uses `bg-bp-raised`, `rounded-bp-lg`. Career previews are `text-bp-text-secondary`. The two buttons are:

- **"That's right"** — `bg-accent-thrive`, `text-bp-text-primary`. Primary action. Confirms and moves to Call 2 (audit).
- **"Not quite"** — `bg-bp-surface`, `text-bp-text-secondary`. Ghost button. Triggers clarification round (Call 3).

**Call 2 — Audit:** Fires automatically after student confirms. This is invisible to the student unless it catches something. The audit checks for adversarial, joke, or nonsensical inputs.

Request: Same payload as Call 1, plus `confirmed_cip`.

Response:
```json
{
  "audit_pass": true,
  "message": null
}
```

If `audit_pass` is `true`: proceed silently to Screen 4.

If `audit_pass` is `false`: show the audit message in a card with `border-accent-caution` styling. The message uses the "cool older sibling" tone from the spike:

```
⚠️ "Look, this is one of the biggest financial decisions
of your life. The tool works better when you give it
something real."

[Try again]
```

The "Try again" button clears the input and refocuses it. The audit message disappears when the student starts typing.

**Call 3 — Clarification (optional):** Only fires if the student tapped "Not quite."

The match card transforms: the career preview area becomes a list of the school's actual programs (from the prefetched program list), each tappable. A secondary text input appears: "Tell us more — what career are you thinking about?"

If the student picks from the program list: that CIP is used directly, skip back to Call 2 (audit).

If the student types more text: fire `POST /intent` again with the new text as `raw_text` and `clarification: true`. Show the match card again with the new result.

Maximum 2 clarification rounds. After that, show the program list as a fallback picker: "Pick from [School Name]'s programs:" — a scrollable list of all programs, alphabetized. This is the deterministic fallback.

#### CIP Substitution (transparent to student)

When the school reports only a broad CIP code (e.g., "Business" at 52.00) but the student typed something specific (e.g., "Marketing"), the backend handles this via CIP substitution: use the specific CIP's crosswalk SOCs for career paths, fall back to the school's broad earnings data for ERN/ROI. The YAML override table maps common specific intents to their CIP codes (~150–250 rows).

The frontend does not need to know about substitution — it sees a normal match response. The career preview will reflect the specific CIP's SOCs. The receipt (tappable "?" later in the flow) will explain the earnings data source.

#### Confirmed Mapping Cache

On successful confirmation, the backend caches `{school_unitid, raw_text, matched_cip}`. Repeat queries with the same school+text resolve instantly without Gemma calls. The frontend should optimistically check the cache before showing the thinking indicator — if the response comes back in <200ms, skip the thinking state entirely.

#### Transition to Screen 4

After audit passes, the school chip + major card compact into a summary bar at the top of the screen:

```
🏫 Iowa State University  ·  📚 Biology, General
```

This bar persists through Screen 4 and transitions into the loading screen for F3. The summary bar uses `bg-bp-mid`, `rounded-bp-sm`, `text-sm`.

Screen 4 content slides in below with `transition-smooth`.

-----

## Screen 4: Effort + Loans

### Layout

Same container width as Screen 3. Summary bar at top. Two slider sections stacked vertically with clear visual separation. A live stat preview at the bottom shows how the sliders affect the build.

### 4A: Effort Slider

**Header:** "How much time will you have to focus on school?" — `font-display`, `text-lg`.

**Subtext:** "This isn't about intelligence — it's about circumstances." — `text-bp-text-muted`, `text-sm`. Important framing to prevent the slider from feeling like a self-assessment of ability.

**Control:** Three-position segmented control (not a continuous slider — there are exactly three discrete values).

| Position | Label | Subtext | Percentile | ERN Shift |
|---|---|---|---|---|
| Left | "Working + school" | Limited time to focus | 25th | −1 |
| Center | "Balanced" | Solid effort | 50th | 0 (default) |
| Right | "All-in" | Maximum focus | 75th | +1 |

**Styling:** Segmented control uses `bg-bp-surface` track with `bg-accent-thrive` for the selected segment. Unselected segments show labels in `text-bp-text-secondary`; selected segment shows labels in `text-bp-text-primary` with `font-semibold`.

**Default:** "Balanced" (center position).

**Stat impact preview:** Below the control, a single line updates live: "ERN impact: ±0" / "ERN impact: −1" / "ERN impact: +1". Uses `text-stat-ern` color. The number animates on change (counter transition, 150ms).

### 4B: Loan Percentage Slider

**Header:** "How much of your school costs will you cover with loans?" — same typographic treatment.

**Subtext:** "Scholarships, savings, family help — anything that isn't borrowed money." — `text-bp-text-muted`, `text-sm`.

**Control:** Five-position segmented control.

| Position | Label | Loan % | Effect |
|---|---|---|---|
| 1 | "No loans" | 0% | ROI maximized |
| 2 | "Some" | 25% | Moderate debt |
| 3 | "Half" | 50% | Balanced (default) |
| 4 | "Mostly" | 75% | Significant debt |
| 5 | "All loans" | 100% | Full published debt load |

**Styling:** Same segmented control pattern as effort. Selected segment uses `bg-accent-thrive`. On the two rightmost positions (75%, 100%), the selected segment shifts to `bg-accent-caution` to gently signal higher financial exposure — not alarming, just informative.

**Default:** "Half" (50%, center position).

**Stat impact preview:** "ROI impact: scales debt-to-earnings to {X}%". Uses `text-stat-roi` color. At 0%, show "ROI impact: best case — no debt". At 100%, show "ROI impact: full published debt load".

### 4C: Live Stat Preview

Below both sliders, a compact preview card shows the combined effect on ERN and ROI. This is not the full pentagon — it's a two-stat mini preview that gives the student a sense of how their choices interact before they commit.

**Layout:** Two stat badges side by side in a `bg-bp-raised` card with `rounded-bp-md`.

```
┌──────────────────────────────────┐
│   ERN  ▲ +1        ROI  ● 50%   │
│   75th percentile   Half loans   │
└──────────────────────────────────┘
```

Each badge shows the stat abbreviation in its stat color (`text-stat-ern`, `text-stat-roi`), the current modifier, and the plain-English label from the selected slider position. Badges animate on slider change (fade transition, 150ms).

**Note:** This preview does not call the backend. It's purely derived from the slider positions — no API round-trip needed. The actual pentagon computation happens on the next screen.

### CTA Button

Below the preview card: **"Spec my build →"** — full-width button, `bg-accent-thrive`, `text-bp-text-primary`, `rounded-bp-md`, `font-display`, `text-lg`. Tap submits the complete input set to the backend and transitions to F3.

On tap, the button shows a loading state: text changes to "Specing {profile_name}..." (using the student's auto-generated name from F1), and the button pulses gently with `accent-thrive` glow.

-----

## API Calls Summary

| Trigger | Endpoint | Service | When |
|---|---|---|---|
| School search typing (debounced) | `GET /schools?q={query}` | `school_lookup.search_schools()` | Screen 3A, after 2+ chars + 300ms debounce |
| School selected | `GET /schools/{unitid}/programs` | `school_lookup.get_programs()` | Screen 3A, on selection (prefetch) |
| Major submitted | `POST /intent` | Gemma intent resolution | Screen 3B, on Enter/submit |
| Major confirmed | `POST /intent` (audit) | Gemma intent audit | Screen 3B, after "That's right" |
| "Not quite" + resubmit | `POST /intent` (clarification) | Gemma intent resolution | Screen 3B, clarification round |
| "Spec my build" tapped | `POST /build` | `stat_engine` + `career_tiering` | Screen 4 CTA — transitions to F3 |

-----

## State Management

This screen produces the following state, passed forward to F3:

```typescript
interface BuildInput {
  school: {
    unitid: number;
    name: string;
    city: string;
    state: string;
  };
  major: {
    cip_code: string;
    cip_title: string;
    raw_text: string;  // what the student typed
    careers_preview: string[];
    substitution_applied: boolean;  // CIP substitution flag
  };
  effort: {
    level: 'working' | 'balanced' | 'all_in';
    percentile: 25 | 50 | 75;
    ern_shift: -1 | 0 | 1;
  };
  loans: {
    percentage: 0 | 25 | 50 | 75 | 100;
  };
  profile_name: string;  // carried from F1
}
```

This state is submitted as the `POST /build` payload when the student taps "Spec my build →".

-----

## Component Inventory

| Component | Description | Reuse |
|---|---|---|
| `SchoolSearch` | Fuzzy search input + dropdown results + confirmed chip | F2 only |
| `MajorInput` | Free-text input + thinking state + match card | F2 only |
| `IntentMatchCard` | Gemma match presentation with confirm/clarify buttons | F2 only |
| `AuditWarning` | Adversarial input warning card | F2 only |
| `ProgramPicker` | Scrollable fallback program list | F2 only (fallback) |
| `SegmentedControl` | N-position selector with labels and subtexts | F2, potentially reusable |
| `StatBadge` | Single stat with color, value, and label | F2 preview, reused in F3/F6/F7 |
| `BuildSummaryBar` | Compact school + major display | F2→F3 transition, persists |
| `PrimaryButton` | Full-width CTA with loading state | Shared across all screens |

-----

## Accessibility

- School search results navigable by keyboard (arrow keys + Enter).
- Segmented controls operable by keyboard (arrow keys to move selection).
- Match card buttons have clear focus indicators using `ring-accent-insight`.
- Audit warning is announced to screen readers via `role="alert"`.
- All interactive elements meet WCAG AA contrast on `bg-bp-deep`.
- Slider labels are associated with their controls via `aria-label`.

-----

## Error Handling

| Error | UX |
|---|---|
| School search API fails | Show "Having trouble searching. Try again in a moment." below input. Retry on next keystroke. |
| Intent resolution API fails | Show "Gemma couldn't match that — try a different description, or pick from the list below." Reveal program picker fallback. |
| Intent resolution returns low confidence | Treat as a normal match but add "(best guess)" to the title. Student can still confirm or clarify. |
| Audit API fails | Skip audit silently. Proceed to Screen 4. The audit is a quality gate, not a blocker. |
| Program list prefetch fails | Intent resolution still works (Gemma uses national crosswalk data). Clarification round won't have school-specific programs — show text input only. |
| All Gemma calls fail | Full deterministic fallback: show the school's program list as a dropdown picker. No Gemma magic, but the student can still proceed. |

-----

## Performance Targets

| Metric | Target |
|---|---|
| School search response | <300ms (95th percentile) |
| Intent resolution (Call 1) | <3s (show thinking state at 500ms) |
| Audit (Call 2) | <2s (invisible if fast; show subtle indicator if >1s) |
| Cached intent resolution | <200ms (skip thinking state) |
| Screen 3 → Screen 4 transition | <300ms animation |
| Screen 4 → F3 transition (POST /build) | <5s (show personalized loading) |

-----

## Mobile Considerations

- School search dropdown should be full-width on mobile viewports. On small screens, the dropdown overlays content below rather than pushing it down.
- Match card should be full-width with stacked buttons (confirm on top, clarify below) on viewports <640px.
- Segmented controls should show abbreviated labels on small viewports: "Working" / "Balanced" / "All-in" → "Work" / "Bal" / "All".
- The summary bar at top should truncate long school names with ellipsis.
- CTA button should be sticky at the bottom of the viewport on Screen 4 so it's always reachable without scrolling.

-----

## Design System Tokens Used

**Backgrounds:** `bg-bp-deep` (screen), `bg-bp-surface` (inputs), `bg-bp-raised` (cards, preview), `bg-bp-mid` (summary bar)

**Accents:** `accent-thrive` (CTAs, selected segments, confirm), `accent-caution` (high-loan segments, audit warning), `accent-insight` (thinking state, focus rings)

**Stat colors:** `text-stat-ern` (effort preview), `text-stat-roi` (loan preview)

**Typography:** `font-display` (Fredoka — headers), `font-body` (Nunito — all other text), `font-data` (Space Mono — stat values)

**Borders/Radii:** `rounded-bp-md` (inputs, buttons), `rounded-bp-lg` (cards), `rounded-bp-sm` (summary bar, badges)

**Shadows:** `shadow-glow-insight` (match card border glow)

**Transitions:** `transition-fast` (150ms — stat badge changes), `transition-normal` (200ms — shimmer, focus), `transition-smooth` (300ms — screen transitions, card reveals)

-----

## Spec Boundary

### This spec builds:
- Screen 3 (school search + Gemma intent resolution for majors)
- Screen 4 (effort slider + loan percentage slider + live preview + CTA)
- The transition from F1 into this screen (receiving profile name)
- The transition out to F3 (submitting build input + showing personalized loading)

### This spec does NOT build:
- The `POST /build` response handling or career tiering UI (that's F3)
- The stat tutorial or pentagon chart (that's F3)
- The profile name generation (that's F1)
- The FastAPI router wiring (that's B1)
- Gemma prompt engineering for intent resolution (that's in the spike — prompts already working)

-----

*— End of F2 Spec —*
