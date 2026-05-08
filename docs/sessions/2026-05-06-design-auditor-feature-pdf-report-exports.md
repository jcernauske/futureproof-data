# Session Log: Design Audit — Feature PDF Report Exports

**Session ID:** 2026-05-06-design-auditor-feature-pdf-report-exports
**Date:** 2026-05-06
**Agent:** @fp-design-auditor
**Spec:** `docs/specs/feature-pdf-report-exports.md`
**Status at session start:** TESTING — advancing to DESIGN AUDIT

---

## Scope

Mechanical Brightpath token-compliance audit for the PDF Report Exports feature. Scope covers:

- `backend/app/services/pdf_export.py` — every constant, palette, style, and rendering path
- `backend/app/services/pdf_copy.py` — verdict-line copy + risk-level mapping
- `backend/app/services/pdf_fonts/` — bundled TTF files

Reference documents read in full before auditing:
- `DESIGN.md` — Brightpath design system (token source of truth)
- `docs/specs/feature-pdf-report-exports.md` §3.4 / §3.5 / §3.11 (print design contract)

---

## Actions Taken

1. Read `DESIGN.md` in full (lines 1–400+). Catalogued dark-mode background tokens, stat colors, accent colors, and typography.
2. Read the spec §1–§3.11 in full. Noted all 14 audit items from the audit brief plus the profile-strip separator rule in §3.5.
3. Read `pdf_export.py` in full (lines 1–1235). Audited all palette constants, style definitions, rendering paths, canvas callbacks, and document builder.
4. Read `pdf_copy.py` in full (lines 1–448). Audited copy strings for §3.11.3 glossary compliance, caveat copy, and risk-level mapping logic.
5. Listed `pdf_fonts/` directory contents. Found: `FredokaOne-Regular.ttf`, `Nunito-Regular.ttf`, `Nunito-Bold.ttf`, `SpaceMono-Regular.ttf`. No italic TTF present.
6. Grep: dark-mode panel colors — zero matches in `pdf_export.py`.
7. Grep: INK_PRIMARY fill usages — 5 uses; all within the §3.4 dark-fill cap.
8. Grep: italic font references — only in comments; no italic font name or TTF registered.
9. Compared glossary definition strings at lines 871–878 of `pdf_export.py` against §3.11.3 verbatim.

---

## Findings

### PASS — 9 of 14 checklist items + overall palette

- Stat hues (`STAT_ERN`–`STAT_AURA`) — exact hex match to §3.4
- Risk-level palette (`RISK_INK`, `RISK_BG`) — all 5 levels correct, including Insufficient `#5C5E70` / `#EFF0F4`
- Risk chip: Low uses roman Nunito (not bold) — correct; Moderate/Elevated/High use NunitoBold ALL-CAPS — correct
- No dark-mode panel colors leak into the PDF
- INK_PRIMARY dark fills: exactly the header band + named table column-header rows, no additional panels
- Headline font: FredokaOne 20pt verdict, 11pt/9pt section headers
- Caveat spacers: `Spacer(1, 6)` above / `Spacer(1, 9)` below — matches §3.11.5 asymmetric spec
- Caveat conditionality: renders only when `match_quality != "full"` — correct
- Caveat copy wording: exact match to §3.11.5 (`scorecard_only` and `partial_no_onet`)
- Cost strip: all 4 cells center-aligned, 4th cell "Debt-to-earnings (yr-1)" with `f"{v*100:.0f}%"` formatter
- Comparison leading-direction: 4-year cost LOW, modeled debt LOW, year-1 earnings HIGH, debt-to-earnings LOW — all correct
- Pentagon vertex labels: NunitoBold 6.5pt colored per stat; value labels SpaceMono 5.5pt INK_SECONDARY
- Glossary: 4-column 2-pair layout, 8 entries, "Career risk" (not "Boss fights") — Decision #4 compliant
- Sources citation: canvas callback `on_last_page` only, not a story flowable
- Two PageTemplate architecture: "main" + "last" registered; `NextPageTemplate("last")` before final `PageBreak()`
- PDF metadata: `/Title`, `/Author` (FutureProof), `/Subject`, `/Keywords`, `lang="en-US"` — all present

### FAIL — 4 items require changes

**FAIL A/B/C (same root cause — blocking):** No `Nunito-Italic.ttf` is bundled in `pdf_fonts/`. As a consequence:
- The "Insufficient data" risk chip (§3.4 / §3.5) renders as plain roman, not italic. Italic is the B&W differentiator that distinguishes the neutral meta-state chip from the Low/Moderate/Elevated/High value chips.
- The data-coverage caveat (§3.11.5) renders as plain roman, not italic. The spec is explicit: "Nunito 7.5pt italic INK_MUTED".

Both failures share one fix: bundle `Nunito-Italic.ttf`, register as `"NunitoItalic"` in `_FONT_FILES`/`_FONT_FALLBACK`, and apply to the Insufficient chip and caveat paragraph.

**FAIL D (required):** Profile-strip separator at line 568 uses `thickness=1.0, color=INK_PRIMARY`. Spec §3.5 specifies `HRFlowable` at `0.75pt RULE_LIGHT`. Both thickness and color are wrong. The dark navy thick rule is visually aggressive on print and is the opposite of the quiet separator the spec intends.

**FAIL E (required):** Glossary font sizes at lines 885 and 887 are `7.5pt` for both terms and definitions. Spec §3.5 specifies `NunitoBold 8pt` terms, `Nunito 8pt` definitions.

**FAIL F (required):** Three glossary definition strings are truncated vs §3.11.3:
- RES: missing `", blended from task-level data"`
- AURA: missing `" at the school"` (final words)
- Career risk: missing `" that affect long-term outcomes"` clause

### NOTE — PDF/UA tagging

No PDF/UA structure tagging present. Per spec §1 Accessibility: "NICE-TO-HAVE but not blocking — hackathon timeline." Deferred, not a blocker.

---

## Decisions Made

- Flagged italic as a blocking violation because the spec explicitly calls out italic as the B&W differentiator channel for the Insufficient chip (§3 Design Vision Refinement item 4) — it is not a cosmetic preference, it is the mechanism that distinguishes the neutral meta-state from the 4 risk-level chips on black-and-white photocopy.
- Treated the profile-strip separator as a required (not blocking) change: the wrong color/thickness deviates from spec but does not break a critical readability path the way the italic does.
- Glossary font-size and copy truncations are required changes: they are direct deviations from §3.5 and §3.11.3 spec text.

---

## Verdict

**CHANGES REQUESTED**

Required before APPROVED:
1. Bundle `Nunito-Italic.ttf`, register `"NunitoItalic"`, apply to Insufficient chip and caveat paragraph.
2. Profile-strip separator: `thickness=0.75, color=RULE_LIGHT`.
3. Glossary font sizes: `8pt` for both terms and definitions.
4. Restore 3 truncated glossary definition strings to §3.11.3 verbatim.

Findings written to §8 of the spec (`docs/specs/feature-pdf-report-exports.md`).

---

## Round 2 Re-review

**Date:** 2026-05-06
**Trigger:** Implementor applied all four round-1 required conditions plus a bonus thread-safety fix.

### Re-review Actions

1. Listed `backend/app/services/pdf_fonts/` — confirmed `Nunito-Italic.ttf` present (275 KB).
2. Read `pdf_export.py` lines 79–95 (font registration table and lock). Confirmed `"NunitoItalic": "Nunito-Italic.ttf"` in `_FONT_FILES`, `"NunitoItalic": "Helvetica-Oblique"` in `_FONT_FALLBACK`, and `_FONTS_LOCK` threading lock with double-checked locking at lines 109–113.
3. Read `_risk_chip_paragraph` (lines 473–498). Insufficient branch at line 478 now uses `fontName=_font("NunitoItalic")`. Low branch at line 489 uses `_font("Nunito")` (roman, correct). Bold branch at line 490 uses `_font("NunitoBold")` (correct).
4. Read `_build_page1` caveat block (lines 585–599). Caveat paragraph at line 590 uses `fontName=_font("NunitoItalic")`, correct. Profile-strip separator at line 598: `HRFlowable(width="100%", thickness=0.75, color=RULE_LIGHT, spaceAfter=8)` — matches §3.5 exactly.
5. Read glossary block (lines 894–944). `term_style` at line 919: `fontSize=8, leading=11`. `def_style` at line 921: `fontSize=8, leading=11`. Both 8pt. Comment at line 918 marks the fix.
6. Read glossary entry list (lines 903–912). Confirmed all three restored definitions verbatim: RES ends `"...blended from task-level data."`, AURA ends `"...shared by every program at the school."`, Career risk reads `"Five factors that affect long-term outcomes: ..."`.
7. Grep confirmed no regressions: color tokens, dark-fill cap, stat hues, canvas callbacks, page template architecture all unchanged.

### Round 2 Findings

| Condition | Status |
|-----------|--------|
| 1 — Italic font (`NunitoItalic`) bundled + applied to chip + caveat | PASS |
| 2 — Profile-strip separator: 0.75pt RULE_LIGHT | PASS |
| 3 — Glossary font sizes: 8pt / 11pt leading | PASS |
| 4 — Three truncated glossary definitions restored verbatim | PASS |
| Bonus — Thread-safe font registration (double-checked lock) | PASS |
| No regressions to round-1 PASSes | PASS |

### Round 2 Verdict

**APPROVED**

All four required conditions cleared. No new violations. The Brightpath print design contract is mechanically satisfied.
