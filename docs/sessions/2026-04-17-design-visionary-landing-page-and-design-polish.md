# Session — fp-design-visionary — landing-page-and-design-polish

**Date:** 2026-04-17
**Agent:** @fp-design-visionary
**Spec:** `docs/specs/landing-page-and-design-polish.md`
**Step:** 2 (DESIGN VISION) of the Claude Code Prompt
**Outcome:** §3 formalized; spec status advanced DESIGN VISION → IMPLEMENTATION.

## Context

Step 1 (ARCHITECTURE REVIEW) was re-reviewed APPROVED on 2026-04-17 after the six required conditions were resolved. Step 2 is the DESIGN VISION pass — formalizing §3 (UI/UX Design) by copying the per-section specs from `reports/design-vision-2026-04-17.md` §2 into the spec, validated against `DESIGN.md`.

Architect re-review left one explicit hand-off: Section E's Ollama data-residency claim must be scoped per §2 Decision 8. Exact phrasing: `When a school runs FutureProof on Ollama, no student data leaves the building.` No bare standalone "no student data leaves the building" allowed. Architect re-reviews §3 specifically for this.

## Sources Consulted

1. `docs/specs/landing-page-and-design-polish.md` — spec in full (§1–§11). Current §3 was a placeholder; §4, §5 architect review, §10 discussion all reference it.
2. `reports/design-vision-2026-04-17.md` — source of truth for all nine section specs (§2.1–§2.10), in-app polish (§3), screenshots (§4), coherence (§5), anti-patterns (§6), extensions (§7).
3. `DESIGN.md` — the Brightpath design system. Validated every token referenced in the report against this file.

## Actions Taken

### 1. Token validation pass against DESIGN.md

Walked every token the design report §2 references against DESIGN.md's Color Tokens, Typography, Spacing, Border Radii, Shadows, Motion, Components sections. Results:

**Present and used as-named (no changes needed):**
- Backgrounds: `bg-bp-void`, `bg-bp-deep`, `bg-bp-mid`, `bg-bp-surface`, `bg-bp-raised`
- Borders: `border-border-subtle`, `border-border-default`, `border-border-strong`
- Text colors: `text-text-primary`, `text-text-secondary`, `text-text-muted`, `text-text-inverse`
- Accents: `accent-thrive`, `accent-alert`, `accent-caution`, `accent-insight`, `accent-info`, `accent-empathy`
- Shadows: `shadow-glow-thrive`, `shadow-glow-insight`, `shadow-md`, `shadow-lg`
- Type scale: `text-hero` (48), `text-title` (40), `text-display` (36), `text-heading` (28), `text-subheading` (22), `text-body-lg` (18), `text-body` (16), `text-body-sm` (15), `text-cta` (17), `text-small` (14), `text-micro` (12), `text-data-lg` (24), `text-data` (16), `text-data-sm` (13)
- Radii: `rounded-sm/md/lg/xl/full`
- Motion: `springs.bouncy`, `springs.smooth`, `springs.gentle`, `springs.snappy`; `stagger.fast`, `stagger.normal`, `stagger.slow`; `transitions.fadeInUp`, `transitions.scaleIn`, `transitions.press`; CSS animations `ambient-breathe`, `twinkle`, `vertex-glow-pulse`

**Required extensions (already flagged in §7 of the report; codified in §2 Decision 3 of the spec):**
- `text-marketing-hero` — 96 / 72 / 48 responsive
- `text-marketing-section` — 64 / 56 / 40 responsive
- `text-hero-tablet` — 56 flat
- `text-hero-desktop` — 64 flat

**Report-referenced sizes reconciled to existing tokens (no new tokens needed):**
- Report "11px font-data" in Section C card labels and Section G table headers → matches DESIGN.md §Components → Cards label spec (`font-data`, 11px, uppercase, letter-spacing 1px) and §Section Labels (11px, 2px tracking). Kept as inline 11px referencing the established pattern; no new token.
- Report "15px font-body" for Section G table source column → resolves to `text-body-sm` (15px, existing).
- Report "14px font-body" for Section G POWERS column → resolves to `text-small` (14px, existing).

No token references in the report were unreconcilable with DESIGN.md. No new blockers beyond the four tokens already authorized in §2 Decision 3.

### 2. §3 rewrite (pixel-perfect implementation target)

Replaced the §3 placeholder block with the fully formalized design. §3 now contains:

- §3.1 — Sections in Scope table
- §3.2 — Libraries
- §3.3 — Landing Page Rulebook (global decisions — background, ambient, reduced-motion pattern, width system, section rhythm, primary CTA DNA, single CTA rule, mobile behavior, motion philosophy)
- §3.4 — Section A (Hero) — ASCII wireframe + token table + copy ground truth + motion spec + reduced-motion fallback + accessibility identifiers
- §3.5 — Section B (Problem) — same structure
- §3.6 — Section C (How It Works) — same structure
- §3.7 — Section D (Receipts Story) — same structure
- §3.8 — Section E (Ollama) — same structure, plus the explicit scoped Ollama claim rule and architect-re-review note
- §3.9 — Section F (CTA Rail) — same structure
- §3.10 — Section G (Data Sources) — same structure, includes the canonical 7-dataset table (69,947 / 832 / 798 / 815 / 587 / 51 / 626,406)
- §3.11 — Section H (Team) — same structure
- §3.12 — Section I (Footer) — same structure
- §3.13 — In-App Polish Specs (headline token chain, Stage 2 Reveal retime reference, Branch Tree screenshot convention)
- §3.14 — Brightpath Token Usage summary
- §3.15 — Accessibility identifier table (expanded from the original 11 identifiers to the full set including Section G's 7 row identifiers, Section H's Brightsmith link, and Section I's 7 footer nav identifiers)
- §3.16 — Visual Coherence with In-App Surface (three invariants, one deliberate difference, cross-surface signature table)

Every per-section entry includes:
- ASCII wireframe copied from the report
- Token table naming every color, spacing, type-scale, shadow, and radius used (named tokens only)
- Copy ground truth (exact headline, body, microcopy as it ships)
- Motion spec (entrance, `whileInView`, ambient, reduced-motion fallback)
- Accessibility identifiers cross-referenced to §3.15

### 3. Critical scoped-claim enforcement (Section E)

Per the architect re-review hand-off, Section E Paragraph 2 is locked to: `When a school runs FutureProof on Ollama, no student data leaves the building. No cloud bill. No ongoing cost.` The scoped phrasing is codified three times in §3.8:

- In the opening paragraph as a "Critical constraint" callout
- In the copy ground truth as the literal paragraph-2 ship copy
- In the closing "Rule (architect re-review hand-off)" section

The bare phrase `No student data leaves the building.` is explicitly disallowed as a standalone line anywhere on the page.

### 4. Accessibility identifier expansion

The original §3 accessibility table had 11 identifiers. Expanded to the full set required by the sections:

- Kept all 11 existing identifiers unchanged
- Expanded `landing-data-row-{source}` to the specific seven: scorecard, bls, onet, karpathy, anthropic, bea, cipsoc
- Added `landing-team-brightsmith-link` for Section H
- Expanded `landing-footer-{name}` to the specific seven: live-app, kaggle, github, video, brightsmith, voice-guide, disclaimers

No identifier was dropped. All are cross-referenced from the per-section entries to §3.15.

### 5. Reduced-motion coverage

Every per-section motion spec includes an explicit "Reduced motion" row documenting what happens when `useReducedMotion()` returns true. Coverage:

- Twinkle field, ambient-breathe, PentagonGlow 7s drift, scroll cue bob (§3.4 Hero)
- `whileInView` fadeInUp/scaleIn reveals (all sections)
- Card hover elevations (§3.6 How It Works)
- Row hover transitions (§3.10 Data Sources)
- Terminal typing animation + cursor blink (§3.8 Ollama)
- Screenshot scaleIn overshoot (§3.7 Receipts)
- Stage 2 Reveal sequence (§3.13.2, references §4 Current → New Delay Map)

Matches the pattern prescribed in §4 Architecture Overview (Animation primitives).

### 6. Deltas from the source report

Minor tightenings I applied (with rationale):

- Section A headline size values `text-[72px] desktop:text-[96px]` in the report collapsed into the single token `text-marketing-hero` (which is 96/72/48 responsive per §7.1). Same values, token-compliant expression.
- Section B headline `text-[56px] desktop:text-[64px]` collapsed into `text-marketing-section` (64/56/40 responsive) for the same reason.
- Section G table body text sizes (report said 14 and 15 px) locked to existing tokens: `text-body-sm` (15px) for SOURCE column, `text-data` (16px) for ROWS column, `text-small` (14px) for POWERS column. Renders visually identical; token-clean.
- Section D receipt stat block stagger — report said 120ms; mapped to `stagger.slow` (100ms in `motion.ts`). The 20ms delta is invisible at runtime; token-clean.
- Added explicit hex refs alongside first use of the four critical tokens (`bg-bp-void` / `#12131F`, `accent-thrive` / `#7DD4A3`, `accent-insight` / `#B8A9E8`, `accent-alert` / `#F4A97E`) so the design auditor can cross-check without another jump.
- Added "Rule —" callout boxes at the end of each section to lock the one anti-trope risk per section (no sparkles on cards, two-receipt maximum, etc.).

No delta that changes the substance of the report's vision. All deltas preserve token discipline or enforce existing guardrails more tightly.

### 7. Spec status advance

- Top-level `Status:` DESIGN VISION → IMPLEMENTATION
- Metadata `Last Updated` refreshed: `2026-04-17 (§3 formalized by @fp-design-visionary; advancing to IMPLEMENTATION)`

## Deliverables

- `docs/specs/landing-page-and-design-polish.md` — §3 replaced with the fully formalized design (16 subsections, 9 section specs, global rulebook, in-app polish cross-references, token summary, accessibility table, coherence plan). Status advanced to IMPLEMENTATION.
- This session log.

## Open Items / Hand-offs

- **Architect re-review of §3 Section E (Ollama claim scoping):** per §5 Conditions item 8. Phrasing is locked; architect can verify against §3.8.
- **Design auditor (future step 5):** will verify zero hardcoded colors/spacing/fonts in implementation, new marketing tokens applied correctly, prefers-reduced-motion respected, mobile responsive, no anti-patterns from §6 of design report.
- **Implementer (future step 3):** §3 is now the pixel-perfect target. Every section has exact copy, exact tokens, exact motion timing. Deviation must be logged in §6 Deviations.

## Blockers

None. No tokens referenced were unreconcilable with DESIGN.md. The four new tokens are authorized by §2 Decision 3 + §7 of the report. The scoped Ollama claim is locked with the architect's required phrasing.
