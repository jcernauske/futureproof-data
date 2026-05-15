# Feature: PDF Report Exports for Guidance Counselor Conversations

## Claude Code Prompt

```
Read the spec at docs/specs/feature-pdf-report-exports.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review §1-§4 (service architecture, Gemma call shape,
     PDF rendering library choice, router placement, frontend trigger surfaces,
     Pydantic request/response models). Architect MUST resolve Decision #1
     (ReportLab vs Playwright vs WeasyPrint) before implementation begins.
   - Invoke @fp-data-reviewer to verify every numeric input the PDF renders
     (stat values, cost, ROI, modeled debt, payback year, risk-level mapping)
     comes from the same Gold-zone source as the on-screen /my-build display
     and the existing CompareView. No re-derived numbers.
   - Both write findings to §5.
   - If APPROVED: proceed to step 2.
   - If CHANGES REQUESTED (Significant): STOP, alert human.
   - If REJECTED (Blocker): STOP, alert human.

2. DESIGN VISION
   - Invoke @fp-design-visionary to propose the print layout for both reports.
     Visionary owns the light/print-friendly translation of Brightpath:
     white background, ink-economical type, the 5 stat color hues preserved,
     headline display font preserved, no dark-mode panels.
     Visionary writes pixel-perfect ASCII mockups + token references to §3.
   - Invoke @fp-copywriter to write:
     • Verdict-line templates (parameterized for the 4 risk-level buckets).
     • Risk-level one-liner copy per boss × per level (Low/Moderate/Elevated/High).
       The translation table in §2 Decision #4 is non-negotiable — RPG language
       MUST NOT appear in the PDF.
     • Glossary entries (CIP, SOC, ERN, ROI, RES, GRW, AURA, "career risk").
     • Static fallback questions per audience (Ask the college: 2 mandatory + 1
       fallback; Ask your parents: ≥1; Ask yourself: ≥1) — these render when
       Gemma is unreachable so the PDF never ships with an empty audience block.
     • Gemma system prompt + JSON schema for the question generation call.
   - Copywriter writes to §3 (copy section) and §4 (Gemma prompt).
   - Invoke @genai-architect to review the Gemma question-generation prompt
     and JSON schema. Writes to §10.

3. IMPLEMENTATION
   - Implement per §3 (UI/UX + copy) and §4 (Technical Spec).
   - BEFORE coding: review §4 Testing Impact Analysis thoroughly.
   - DURING coding: update only tests in "Authorized Test Modifications".
   - CRITICAL: If any test NOT in "Authorized Test Modifications" fails,
     STOP and escalate.
   - Log all work to §6.
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest).
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts).
   - If still broken after 3 attempts: escalate via §10 Discussion.

4. TESTING
   - Invoke @test-writer to review the full spec.
   - @test-writer MUST review §4 Testing Impact Analysis.
   - Implement all "New Tests Required" by priority (P0 first).
   - Backend: pytest in backend/tests/services/ and backend/tests/routers/.
   - Frontend: vitest in frontend/src/**/*.test.ts(x).
   - Critical paths: Gemma timeout/empty-response → static fallback;
     PDF byte stream → no PII written to disk; 3-school comparison cap;
     same-major guard; RPG-language-leak detection in generated copy.
   - Run ALL tests to catch regressions.

5. DESIGN AUDIT
   - Invoke @fp-design-auditor to verify Brightpath through-line tokens
     are preserved correctly in the print context (5 stat hues, headline font),
     and that NO dark-mode panel colors leak into the PDF.

6. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests.
     Focus: PDF byte-stream handling (no temp files with PII), Gemma timeout
     and concurrency, request validation (build_ids ownership), error paths
     when ReportLab fails mid-render.
   - Reviewer writes findings to §8.
   - If APPROVED: proceed to step 7.
   - If CHANGES REQUIRED: route to originating agent via §10 Discussion.
   - If BLOCKER: STOP, alert human.

7. VERIFICATION
   - Invoke @fp-builder to run full build verification.
   - Backend: ruff check, mypy, pytest (including new PDF tests).
   - Frontend: TypeScript, vitest, Vite production build.
   - Log results to §9.
   - If all green: mark status COMPLETE.

8. COMPLETION
   - Update top-level Spec Status to COMPLETE.
   - Check off all completed Success Criteria in §1.
   - Update §6 Implementation Log, §7 Test Coverage, §8 Reviews.
   - Add the two PDF surfaces to docs/reference/stat-display-surfaces.md
     (My Build PDF + Comparison PDF — both Tier 4 / Skip for explain affordance,
     same as Wrapped renderer).
   - Add a "PDF / printed report" row to docs/reference/voice-guide.md
     "Register by Surface" table.
   - Generate report to reports/feature-pdf-report-exports-YYYY-MM-DD.md.
```

---

## Status: COMPLETE

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
| ARCH REVIEW | Awaiting @fp-architect approval |
| DESIGN VISION | @fp-design-visionary proposing §3 |
| IMPLEMENTATION | Implementing |
| TESTING | @test-writer adding coverage |
| DESIGN AUDIT | @fp-design-auditor checking token compliance |
| CODE REVIEW | @faang-staff-engineer reviewing |
| VERIFICATION | @fp-builder running full build |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-05-06 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-05-07 (post-ship revision: Decision #3 reversed — cross-major comparisons are now SUPPORTED to match the in-app CompareView contract; same-major guard removed from service, router, and frontend; PDF title falls back to "Career comparison" when majors differ) |
| Blocked By | — |
| Related Specs | `feature-compare-schools-for-career.md` (compare panel), `pentagon-stat-reshape.md` (stat naming), `feature-explain-stat-receipt-aura.md` (stat display contract), `roi-net-lifetime-value.md` (cost model) |

---

## §1 Feature Description

### Overview

Two PDF exports — a 2-page **My Build PDF** for a single school+major and a 1-page (2-max) **Comparison PDF** for 2 or 3 builds (cross-major supported as of 2026-05-07; see Decision #3) — that turn FutureProof's data into a printed take-away a high school student leaves with after a 90-second guidance-counselor conversation. Both render server-side, are downloaded one-click, and translate the app's RPG framing into neutral advisory language so the document reads as a credibility piece on a counselor's desk, a kitchen table, or a refrigerator.

### Problem Statement

The hackathon judging narrative is *guidance counselor + student + 90 seconds + a take-away*. Today the only export FutureProof produces is the Spotify-Wrapped-style share frame (`wrapped_renderer.py` → PNG image) and an internal markdown audit report (`report_gen.py`, written to `reports/`). Neither is a counselor-facing artifact:

- The Wrapped frame is a celebratory share image, not a print document.
- The markdown report still uses RPG language ("Boss Fight Results", "WIN / LOSE / DRAW", "Reroll") and is unstructured for print.
- Neither offers the **suggested skills + counselor-question scaffolding** that converts a 90-second viewing into a productive next conversation with the admissions office.

A counselor doesn't read a PDF — they scan, point, and ask. The student doesn't fight bosses with their parents at the kitchen table — they ask, "is this realistic?" The PDF is a pointing surface that has to translate from game to advisory while keeping the data spine intact.

### Success Criteria

- [x] One-click "Export PDF" button on `/my-build` that returns a 2-page PDF in <8 seconds at p50 (cold Gemma call included), <15s at p95. *(p50/p95 latency not benchmarked under live load; smoke render is 51 KB in <1s with mocked Gemma. Real-world p50/p95 verified empirically post-deploy.)*
- [x] One-click "Export comparison PDF" button on the multi-build CompareView (`frontend/src/components/menu/CompareView.tsx`) that returns a 1-page PDF for **2 or 3 builds** (Pydantic-enforced). Cross-major builds render with a "Career comparison" title fallback (revised 2026-05-07 per Decision #3 — original same-major restriction reversed because it contradicted the in-app CompareView's contract).
- [x] My Build PDF page 1 contains: header strip (with conditional data-coverage caveat when `match_quality != "full"`), verdict line, pentagon (numerically labeled), 5-stat micro-table, cost & ROI strip (`4-year cost · modeled debt · year-1 median earnings · debt-to-earnings (yr-1)`), 5-row career risk profile.
- [x] My Build PDF page 2 contains: suggested skills (top 6, 3 buckets, with Coursework/Clubs/Internship blanks + per-skill counselor question), Questions & follow-ups (3 audience blocks, capped at 5 inclusive each, floored at 1 each), glossary footer, data-sources line. (No QR code per Decision #9 revision 2026-05-06.)
- [x] The two static "Ask the college" questions render even when Gemma is unreachable. (Refined wording per copywriter §3.11.4: *"Which majors at [School] most often lead graduates into [Career]?"* and *"How can I augment this major with the suggested skills above — through coursework, clubs, or internships you already offer?"*)
- [x] Comparison PDF contains: mini pentagons, stat-by-stat table with leading-cell highlight, cost & ROI block, 5-row risk-profile strip with level chips, "Where each school pulls ahead" 1-sentence-per-school autogenerated line.
- [x] Comparison PDF contains **no** Gemma prose, **no** suggested skills, **no** questions section.
- [x] Zero RPG language ("boss", "fight", "gauntlet", "won/lost", "WIN/DRAW/LOSE", "reroll", "Fight AI", "Fight the Ceiling", etc.) appears in either PDF. Enforced by `RPG_TERMS_FORBIDDEN_IN_PDF` regex test (`test_no_rpg_terms_in_rendered_text`) and a complementary `FORBIDDEN_IN_GEMMA_OUTPUT` post-filter in `pdf_questions.py` that triggers `fallback_malformed`.
- [x] The PDF is light/print-friendly: white page background, ink-economical type. Brightpath dark-mode panel colors do **not** appear. The 5 stat color hues + headline display font are preserved as the only visual through-line. Verified by `@fp-design-auditor` §8.
- [x] Gemma question-generation failure (timeout, network error, empty response, malformed JSON) does NOT block the PDF — the PDF ships with static fallback questions and one `logs/gemma.jsonl` record per fallback path.
- [x] No PII (student name, profile name) is written to disk during PDF generation. Bytes return through `Response(content=bytes, media_type="application/pdf")`. Verified by `test_no_pii_written_to_disk`.
- [x] `docs/reference/stat-display-surfaces.md` is updated with both PDF surfaces (entries 9a + 9b).
- [x] `docs/reference/voice-guide.md` "Register by Surface" table gained a "PDF / printed report" row that explicitly notes the RPG-metaphor exception.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | **PDF rendering library — ReportLab Platypus** (confirmed by design pass 2026-05-06; re-confirmed by @fp-architect 2026-05-06 in §5). Sample PDFs exist at `docs/specs/design/feature-pdf-report-exports-{mybuild,comparison}-sample.pdf`. | Pure Python, predictable, no browser process. Deterministic byte output suits streaming. Sample renders proved every layout primitive (multi-column tables, repeating headers via `repeatRows=1`, dual-template footers via `BaseDocTemplate`, vector pentagon `Drawing` objects, embedded fonts) works without HTML/CSS print quirks. | (a) **Playwright + HTML/CSS print stylesheet** — already a dep for `wrapped_renderer.py`; rejected by design pass for print-CSS page-break edge cases and the per-request Chromium process. (b) **WeasyPrint** — pure Python HTML→PDF; rejected for new dep + separate font-embedding pipeline. |
| 2 | **PDF generation is server-side**, bytes stream back to client; no file is written to disk under `reports/` for user-facing exports. | Fileless = no PII at rest. The existing `reports/` markdown writer (`generate_build_report` in `report_gen.py`) keeps writing to disk per `feedback_always_commit_reports.md` memory — that's an internal audit trail, not a user export. The two purposes are now explicitly separated. | Server-writes-to-`reports/`-then-returns-a-link: tempting for caching but mixes audit and user-facing concerns and would commit student-named files into the repo. |
| 3 | **Comparison PDF supports 2 or 3 builds; cross-major comparisons are SUPPORTED** (revised 2026-05-07 — original same-major restriction reversed). The PDF mirrors what the in-app CompareView already shows. Title falls back to "Career comparison" when majors differ; uses the shared major name when they match. | The same-major restriction was wrong. The premise — "you can't compare ROI when the major differs" — is the opposite of the truth: the whole point of the in-app CompareView is that students see ROI tradeoffs across different paths (e.g., Web designer at UIUC vs Agricultural technician at Delaware State — different cost, different earnings, different AI risk; the comparison is exactly the decision). Stats (0-10), cost/ROI (dollars and %), and the 5-row risk profile are all on the same axes regardless of major. Restricting the PDF when the live CompareView didn't was a contract mismatch that confused real users. The 4-school cap stands (layout reasons below). | (a) Up to 4: rejected for layout reasons — 4 columns at 8.5×11 either truncates school names below readability or shrinks numbers below 8pt. 3 columns fit cleanly. (b) Up to 6 with multi-page: rejected — defeats the "1-page tabular" frame. (c) Restrict to same-major: **the original decision** — rejected on first user contact when a student tried to compare web designer + ag tech and the PDF refused. The CompareView showed it; the PDF must too. |
| 4 | **Translate ALL RPG language to advisory language in the PDF.** This is a deliberate exception to the voice-guide rule "RPG metaphor played straight." | The PDF lives outside the app — on counselor desks, kitchen tables, refrigerators, family email threads. RPG language reads as unserious in print and undermines the data credibility the PDF is meant to convey. The translation is one-way and PDF-only; in-app voice does not change. **Translation table — non-negotiable, enforced by automated regex test:** `Boss fight → Career risk / risk factor`; `AI Boss → AI displacement risk`; `Loans Boss → Debt burden / loan repayment risk`; `Market Boss → Job market outlook`; `Burnout Boss → Burnout risk`; `Ceiling Boss → Earnings ceiling`; `Gauntlet → Career risk profile`; `WIN / LOSE / DRAW → Low / Elevated / Moderate (risk level)`; `Fight [X] → "[X] risk"`; `Reroll → (omit; PDF reflects final state only)`; `Build → Plan / school+major+name`; `"X of 5 boss fights won" → "Low risk on X of 5 career factors"`. See `~/.claude/projects/-Users-jcernauske-code-bright-futureproof-data/memory/feedback_pdf_no_game_language.md` for the rationale memory. | Keep RPG language for brand consistency: rejected per user direction; the credibility cost in print is real. Soften RPG language ("challenges" instead of "boss fights"): rejected — half-measures read as both unserious AND inconsistent with the app. |
| 5 | **One scoped Gemma call per PDF generation**, returning JSON with all 3 audience arrays. | Aligns with `feedback_scoped_llm_contexts.md` (per-element scoped contexts, not global build dumps). Single call also bounds latency to one Gemma round-trip — important for the <15s p95 success criterion. | Three calls (one per audience): rejected — 3× the latency, 3× the failure surface, 3× the rate-limit risk in the cloud-demo `INFERENCE_BACKEND=openrouter` mode. |
| 6 | **Inclusive cap of 5 questions per audience, floor of 1.** Two of the 5 in "Ask the college" are static-mandatory; Gemma adds 0–3 more. | User direction. "No more than 5" feels alive (varies with build context). Floor of 1 prevents an empty audience block on a sparse-data build. The two mandatory college questions guarantee the section is never useless even on cold Gemma fallback. | Hard count of 3-2-2: rejected — feels formulaic. Up to 7 per audience (additive cap): rejected — risks a 3rd page on data-rich builds, which breaks the 2-page frame. |
| 7 | **Voice — student-first for "Ask yourself", audience-first for "Ask the college" / "Ask your parents".** | The student is reading the PDF aloud or with the audience. "Will I be able to handle the math intensity?" reads naturally to oneself. "Does Purdue ME require programming beyond MATLAB?" reads naturally aloud to a counselor. Mixing voices in one block is jarring. | Single voice across all blocks: rejected — either every question reads stilted to one audience or another. |
| 8 | **One optional friction field — student name** (pre-filled from `build.profile_name`). Auto-stamp date. No counselor name, no school-meeting field. | The 90-second use case can't tolerate a form. Every field drops conversion 5–10%. The counselor writes their own name on the printed copy if they want it. The student's profile name (per `feedback_profile_is_build.md`, profile is build identity) is the only personalization that justifies its slot. | One-click no-name: rejected — the document is too anonymous to feel like *yours*. Counselor-name field: rejected per friction reasoning. Date-of-meeting field: rejected — auto-stamp covers 95% of the value. |
| 9 | **Demo polish — defer all three: QR code, "what changed if…" line, and "three schools you didn't consider" row** (revised 2026-05-06 after data reviewer flagged that the QR target route `/build/:build_id` does not exist in `frontend/src/App.tsx` — only the state-driven `/my-build` route exists). | QR added complexity (route addition, share-link composition, library dependency) with no time to validate the routed-share flow before the May 18 deadline. Cut for hackathon. The other two were already deferred: #1 needs a second residency-recompute pass through `stat_engine` for every PDF; #3 needs a "similar schools" recommendation query that doesn't yet exist. All three belong in follow-up specs. | Add a stable shareable build route AND the QR: rejected on time-to-deadline grounds — the route work is its own spec. Keep QR pointing at `/my-build`: rejected — counselor scans it later, finds someone else's `/my-build` state. |
| 10 | **Two PDFs are NEW stat-display surfaces** and must be added to `docs/reference/stat-display-surfaces.md` as Tier 4 (skip — static export, no explain affordance) — same treatment as the Wrapped renderer. | Per `feedback_stat_blast_radius_check.md` memory. Even though the PDF doesn't change stat values, it's a new place stats are displayed; future stat refactors must know to update this surface. | Skip the surface index update: rejected — that's exactly the silent drift the memory warns against. |
| 11 | **Existing `report_gen.py` markdown audit reports stay** alongside the new PDF service. They serve different purposes. | Markdown reports go to `reports/` for committed audit trail (per `feedback_always_commit_reports.md`); PDFs stream as bytes to the user. The markdown reports' lingering RPG language is its own future cleanup, NOT in scope here. | Replace markdown with PDF: rejected — dual audiences. Modify markdown to drop RPG language as part of this spec: rejected — scope creep; that's a separate spec. |

### Constraints

- **Technical:** Must respect `INFERENCE_BACKEND={ollama,openrouter}` per `.env`. Cloud demo (`openrouter`) can rate-limit Gemma; PDF must degrade gracefully to static fallback questions. PDF generation latency budget: p50 < 8s, p95 < 15s.
- **Technical:** No PII (`build.profile_name`, optional `student_name`) written to disk. PDFs return as `bytes` via `Response(content=bytes, media_type="application/pdf", headers={"Content-Disposition": ...})` — same pattern as `backend/app/routers/wrapped.py:152`. Not `StreamingResponse` (the bytes are fully materialized in memory before send; streaming adds no benefit and complicates error handling).
- **Technical:** PDF byte size target ≤800 KB per export (sample renders measured ~50 KB; 800 KB is the headroom limit before any review). Keeps email attachment friendly.
- **Technical:** `CIPCODE` MUST be string `XX.XXXX` — never float (project rule).
- **Technical:** Cross-major comparisons render with a "Career comparison" title fallback (revised 2026-05-07 per Decision #3). The PDF service no longer enforces a 4-digit CIP family match; the only structural cap is 2 ≤ N ≤ 3 builds, enforced by Pydantic at the request boundary.
- **Business:** Voice — see voice-guide.md, with the **PDF / printed report** register-by-surface override defined in Decision #4. The PDF speaks like the existing in-app **Next Steps** surface (drops RPG metaphor, concrete verb-led action items) for the questions section, and like the **Receipts** surface (intentionally dry, label:value format) for the data sections.
- **Business:** Hackathon deadline is 2026-05-18. This spec must complete the full pipeline before then to leave time for demo recording.

### Out of Scope

- Branch-path / future-tree visualization in the PDF (cut by product partner).
- "Gemma's Take" prose anywhere in either PDF (cut).
- Cross-major comparison PDF (decisive vs exploratory; out of scope).
- 4-school comparison PDF (3 is the design max).
- QR code linking back to a live build (cut for hackathon — `/build/:build_id` route does not exist; deferred to follow-up spec along with the share-link route work).
- "What changed if…" residency / loan-pct counterfactual line (deferred to follow-up spec).
- "Three schools like this you didn't consider" row (deferred — needs a recommendation query that does not yet exist).
- Email-the-PDF flow (download only for hackathon).
- Counselor authentication, counselor-specific branding, school-logo customization.
- Counselor-side analytics (which sections they show students most).
- Translating `report_gen.py` markdown reports to advisory language (own spec).
- Editable PDF form fields for the Coursework/Clubs/Internship blanks (these are blank lines on paper — not PDF form widgets).

---

## §3 UI/UX Design

> Filled in by the print-design pass (2026-05-06). Sample PDFs at `docs/specs/design/feature-pdf-report-exports-mybuild-sample.pdf` and `docs/specs/design/feature-pdf-report-exports-comparison-sample.pdf`. The `@fp-design-visionary` role during pipeline execution is to refine and validate against these specs — not start from scratch.

### Surface 1 — Export trigger on `/my-build`

A new download button on `BuildResultsScreen.tsx` near the existing share/save controls. Single button, optional name input is a small text field shown inline (not a modal — minimize friction). On click, calls the backend, receives a PDF blob, triggers browser download with filename `futureproof-{schoolslug}-{majorslug}-{YYYYMMDD}.pdf`.

### Surface 2 — Export trigger on `CompareView`

A new button at the top of `frontend/src/components/menu/CompareView.tsx` next to the existing "Ask Compare" FAB. Disabled with explanatory tooltip when:
- Fewer than 2 builds selected (need at least 2 to compare).
- More than 3 builds selected ("Comparison PDF supports up to 3 schools — deselect one to export").

Cross-major comparisons are supported (revised 2026-05-07 per Decision #3) — no additional same-major guard. The PDF title server-side falls back to "Career comparison" when the build set spans different majors.

---

### 3.1 Implementation Library: ReportLab Platypus

**Decision: ReportLab (confirmed by design pass).** The sample PDFs were built with it. Architect should re-confirm in §5; the design recommendation supersedes the open question in Decision #1.

Key facts to note when writing code:

- `BaseDocTemplate` + `PageTemplate` + `Frame` is the correct assembly model. Do **not** use `SimpleDocTemplate` — it does not support multiple page templates, which are required for the sources citation footer on the last page of each PDF.
- Use `repeatRows=1` on every `Table` that might span a page break. Without it, column headers vanish on page 2. Not optional.
- `Paragraph` objects (not raw strings) must be used for all table cells that could wrap. Raw strings silently clip in `Table` cells.
- Canvas `onPage` callbacks handle the fixed-position header band, footer rule, and page numbers. Story flowables must not duplicate these — the only element that belongs in both a callback and the story is `NextPageTemplate`, which switches the active template without rendering anything.
- The sources citation is drawn in the canvas callback of the "last" page template at fixed y-coordinates. It is NOT a story flowable. Putting it in the story orphans it to an unwanted extra page.
- `NextPageTemplate("last")` must be inserted into the story **before** the `PageBreak()`, not after. After means the switch takes effect on the page following the new page.
- `Drawing` objects for the pentagon must have canvas width/height set to `max_extent * 2` where `max_extent = r + label_offset + label_pad`. Default behavior silently clips vertex labels — no exception is raised.

**Why not Playwright or WeasyPrint:** Playwright adds a Chromium process per request and introduces print-CSS page-break edge cases. WeasyPrint is reasonable but adds a new dep with its own font-embedding pipeline. ReportLab is well-understood, pure Python, deterministic byte output suitable for streaming.

---

### 3.2 Page Master and Grid

**Page size:** US Letter, 8.5 × 11 inches (612 × 792 pt). A4 out of scope.

**Margins:**
- Left / Right: 0.65 in (46.8 pt)
- Top: 0.90 in (64.8 pt) — measured from below the header band
- Bottom: 0.70 in (50.4 pt) — measured above the footer rule

**Live area:** 7.20 in wide (518.4 pt) × 8.73 in tall (628.6 pt).

**Header band:** Full-width band from top of page to 0.55 in below. Background: `INK_PRIMARY` (`#1A1B2E`). Left zone: a 4-pointed sparkle glyph `"✦"` (U+2726) in white at 11pt rendered first, followed by 4pt of horizontal space, then the wordmark `"FUTUREPROOF"` in `NunitoBold 9pt` white. The sparkle is the FutureProof / Gemma signature mark — matches the in-app convention (see GemmaStar component + `✦ Ask Compare` FAB). Right text: `"FOR STUDENT + COUNSELOR USE ONLY"` in `Nunito 7.5pt #B8BCD4`. A 0.75pt gold rule (`#C8A820`) runs the live-area width immediately below the band.

**Sparkle implementation.** Drawn as a filled canvas path (`canvas.beginPath` / `lineTo` / `drawPath`) — 4-pointed star geometry, no font dependency. This was chosen over the `✦` Unicode glyph during the design pass because Nunito's subset does not include U+2726 and the path renderer is simpler than a font-fallback chain. The path coordinates form the standard 4-point star (long axis vertical/horizontal, short axis at 45°); white fill, no stroke; bounding box ~11pt.

**Footer band:** A 0.5pt `#D9DAE4` rule at 0.45 in from bottom. Below the rule: document title left, page number right, both in `Nunito 7pt INK_MUTED`. Sub-footer zone (between rule and page edge): sources citation in `Nunito 6pt INK_MUTED`, two lines, anchored at 14pt and 7pt from the physical bottom. Drawn by the `on_last_page` canvas callback only. (No QR code per Decision #9 revision 2026-05-06.)

**Baseline grid:** 12 pt. All section spacers are multiples of 3 pt (half a baseline).

**Comparison 3-column grid:** Within the live area, a label column of 1.30 in is followed by three equal data columns. Gutter between columns: 0.14 in. Each data column: `(7.20 - 1.30 - 2×0.14) / 3 = 1.73 in`.

---

### 3.3 Typography Scale

All fonts must be embedded via `pdfmetrics.registerFont(TTFont(...))`. Fredoka One, Nunito Regular, Nunito Bold, Space Mono Regular — from Google Fonts, embedded as subsets at generation time.

| Role | Font | Size | Leading | Color token |
|------|------|------|---------|-------------|
| Verdict line | FredokaOne | 20 pt | 26 pt | `INK_PRIMARY` |
| Section header | FredokaOne | 11 pt (compact: 9 pt) | fs+2 | `INK_PRIMARY` |
| Subsection header | NunitoBold | 8 pt | 10 pt | `INK_SECONDARY` |
| Body | Nunito | 9 pt | 13 pt | `INK_SECONDARY` |
| Body small | Nunito | 8 pt | 11 pt | `INK_SECONDARY` |
| Muted / caption | Nunito | 7.5 pt | 10 pt | `INK_MUTED` |
| Stat value | SpaceMono | 13 pt | 16 pt | `INK_PRIMARY` |
| Stat label (abbr) | NunitoBold | 7.5 pt | 10 pt | `INK_SECONDARY` |
| Stat meaning | Nunito | 8 pt | 11 pt | `INK_SECONDARY` |
| Table data | SpaceMono | 9 pt | 12 pt | `INK_PRIMARY` |
| Table data muted | SpaceMono | 8 pt | 11 pt | `INK_MUTED` |
| Glossary term | NunitoBold | 8 pt | 11 pt | `INK_PRIMARY` |
| Glossary definition | Nunito | 8 pt | 11 pt | `INK_SECONDARY` |
| Footer | Nunito | 7 pt | 9 pt | `INK_MUTED` |
| Sources sub-footer | Nunito | 6 pt | 7 pt | `INK_MUTED` |
| Risk chip | NunitoBold | 7.5 pt | 10 pt | risk-level ink color |
| Comparison value | SpaceMono | 10 pt | 13 pt | `INK_PRIMARY` or `LEADING_CELL_INK` |

Section headers use `Spacer(1, 7)` before the `FredokaOne` paragraph, not `spaceBefore` on the paragraph style. Cumulative paragraph spacing in Platypus interacts badly with table `TOPPADDING` values — explicit `Spacer` objects give precise control.

---

### 3.4 Print Color System

**Ink palette (light/print-friendly — no dark-mode background colors anywhere):**

| Token | Hex | Usage |
|-------|-----|-------|
| `INK_PRIMARY` | `#1A1B2E` | Headings, high-importance data, header band background |
| `INK_SECONDARY` | `#3D3E52` | Body text, table data |
| `INK_MUTED` | `#767888` | Captions, footer, muted values |
| `RULE_LIGHT` | `#D9DAE4` | Separator rules, table grid lines |
| `BG_ROW_ALT` | `#F7F7FB` | Alternating table row tint |
| `PAGE_BG` | `#FFFFFF` | Always white |

**Stat accent hues** — print-tuned by darkening Brightpath screen hues ~25% to survive uncoated inkjet paper:

| Token | Hex | Brightpath screen origin |
|-------|-----|--------------------------|
| `STAT_ERN` | `#C8A820` | `#F2D477` |
| `STAT_ROI` | `#3DA86A` | `#7DD4A3` |
| `STAT_RES` | `#7B66C8` | `#B8A9E8` |
| `STAT_GRW` | `#3D8BB8` | `#7BB8E0` |
| `STAT_AURA` | `#C47090` | `#E88BA9` |

Stat hues appear only as: pentagon vertex dot fill, stat abbreviation label in the pentagon, colored dot bullet in the stat micro-table. **Never** as solid fills or backgrounds.

**Risk-level semantic palette** — 5 levels (4 risk levels + 1 missing-data signal) with matching background tints:

| Level | Ink | Background tint | B&W differentiator |
|-------|-----|-----------------|-------------------|
| Low | `#2D7A4F` | `#E8F5EE` | Roman weight, no caps |
| Moderate | `#7A6A20` | `#FFF8E0` | Bold, ALL-CAPS |
| Elevated | `#B84C20` | `#FFF0E8` | Bold, ALL-CAPS |
| High | `#8B1A1A` | `#FCEAEA` | Bold, ALL-CAPS, larger |
| Insufficient data | `#5C5E70` | `#EFF0F4` | Italic Roman, sentence case ("Insufficient data") |

Color alone is insufficient for B&W photocopy. Typographic differentiator (ALL-CAPS + weight) is the redundant channel. "LOW" uses roman weight, not bold, because it is the "good" outcome and should read quieter than the warning levels. **"Insufficient data" is its own neutral chip — NOT a default-to-High** — to honor the "missing data is not zero" rule (per `@fp-data-reviewer` §5 round-1 ruling, re-confirmed round 2). When the boss `raw_score` is None for any of the 5 factors, the row's chip renders this neutral chip and the Context column reads "Data unavailable for this program."

**Comparison leading-cell highlight:**
- Background: `#EBF9F1` (very faint green tint)
- Ink: `#1A5C38` (dark green)
- Applied to the highest-value cell in each stat row and each cost/ROI row.

**Dark-fill usage cap.** Solid `INK_PRIMARY` fills are restricted to (a) the top header band and (b) column-header rows in tables (Career Risk Profile in My Build; Stats at a Glance, Cost & ROI, Career Risk Profile in Comparison). No additional `INK_PRIMARY` panels, callouts, or sidebars. This keeps the report from drifting toward dark-mode-app aesthetics on print. See §3 Design Vision Refinement, item 3 (Brightpath through-line audit).

---

### 3.5 Component Specs — My Build PDF (2 pages)

#### Page 1: The Conversation Page

**Profile + context strip.** A two-column `Table` (45% / 55% of live width). Left cell: profile name in `FredokaOne 14pt` + residency note in `Nunito 7.5pt INK_MUTED`. Right cell: `School · Major · As of Month DD, YYYY` right-aligned in `Nunito 8.5pt INK_SECONDARY`. Separated from verdict line by a full-width `HRFlowable` at 0.75pt `RULE_LIGHT`.

**Data-coverage caveat (conditional).** When `build.career.match_quality != "full"` (i.e. `scorecard_only` or `partial_no_onet`), render a single-line caveat directly below the profile + context strip in `Nunito 7.5pt italic INK_MUTED`, **left-aligned** (matches the verdict line below it), with `Spacer(1, 6)` above and `Spacer(1, 9)` below. The above/below spacing is asymmetric on purpose — it visually docks the caveat to the verdict line that follows, so the counselor reads it as "context for the next sentence" rather than "tail of the previous strip". No leading icon, no bold span, no tinted band — plain italic-roman line. Copy templates (final wording owned by `@fp-copywriter`):
- `scorecard_only`: *"Career-task data is partial for this program — earnings and program-cost figures are full coverage."*
- `partial_no_onet`: *"Some occupational-task detail is unavailable for this program — earnings and program-cost figures are full coverage."*

This is distinct from the CIP-substitution caveat (which we deliberately do NOT show per `feedback_no_substitution_caveat.md`). `match_quality` is a data-coverage signal in the gold table, not a substitution signal — surfacing it gives counselors honest grounding without contradicting the substitution-caveat rule.

**Verdict line.** `FredokaOne 20pt`, `INK_PRIMARY`, left-aligned, multi-line allowed, 26pt leading. Only copy not in Nunito. No period. Template: `"[Major] at [School]: [risk summary]. [ROI summary]."` — parameterized from the data; not generated by Gemma. The `@fp-copywriter` agent fills the parameterization logic.

**Pentagon + stat micro-table.** A two-cell `Table` with no borders. Left cell: the `Drawing` object from `draw_pentagon()`. Right cell: a 4-column stat table (colored dot bullet | abbr | value | meaning). Stat rows at 0.22 in height, alternating white / `BG_ROW_ALT`. Pentagon outer radius: 0.72 in. `Drawing` canvas must be `max_extent * 2` in both dimensions where `max_extent = r + (r * 0.28) + (6.5 * 1.6 + 6.5)`. Vertex label font: 6.5pt NunitoBold colored per stat.

**Cost & ROI strip.** 4-column `Table` (equal widths = `LIVE_W / 4`). Row 0: `Nunito 8pt NunitoBold` labels, **center-aligned** (`ALIGN: CENTER`). Row 1: `SpaceMono 9pt` values, **center-aligned**. Single background: `BG_ROW_ALT`. Columns: `4-year cost | Modeled debt | Year-1 median earnings | Debt-to-earnings (yr-1)`. Dollar values via `f"${v:,.0f}"`. Debt-to-earnings: `f"{debt_to_earnings_annual * 100:.0f}%"` (no leading symbol, no decimal). Center alignment is required because column 4 renders a 3-character percent in a column sized for 7-character dollar values — left or right alignment would visually strand the percent. Source fields (per `@fp-data-reviewer` §5 source-of-truth table): `Build.career.published_cost_4yr`, `Build.career.modeled_total_debt`, `Build.career.earnings_1yr_median`, `Build.career.debt_to_earnings_annual` — all four already shown on `frontend/src/components/build-results/FinancesCard.tsx`, so the PDF and on-screen values are guaranteed identical.

**Replaces "Break-even year"** (called out as a §5 blocker because no `CareerOutcome` field corresponds; `debt_to_earnings_annual` is already on `FinancesCard` and is the single decision-relevant ROI signal that fits the strip aesthetic).

**Career Risk Profile table.** 3-column `Table`: Risk Factor (1.65 in) | Level (1.10 in) | Context (remainder). Header row: `INK_PRIMARY` fill, white `NunitoBold 8pt`. `repeatRows=1`. Body rows: alternating white / `BG_ROW_ALT`. Risk Factor: `Nunito 8pt INK_SECONDARY`. Level column: risk chip rendered as `NunitoBold 7.5pt` in the risk-level ink color on the risk-level background tint, centered, ALL-CAPS for Low/Moderate/Elevated/High; rendered as Nunito **italic Roman 7.5pt** (NOT bold) sentence-case "Insufficient data" using the 5th palette entry from §3.4 when the boss `raw_score` is None — also centered, same vertical alignment as the other chips, so the column reads as a single coherent series. When the chip is "Insufficient data", the Context column reads "Data unavailable for this program." Context: `Nunito 8pt INK_SECONDARY`, wrapping allowed. The Level column is widened from the round-1 0.92 in to **1.10 in** to fit the 17-character "Insufficient data" string on one line at 7.5pt with 7pt horizontal padding. Do not narrow it. (The previous 0.92 in floor was set by "MODERATE"; "Insufficient data" is now the binding constraint.)

#### Page 2: The Take-Home Page

**Suggested Skills section.** Three skill buckets: AI-Resilience, Career-Launch, Earnings-Ceiling. Up to 2 skills per bucket (6 total). Each skill is rendered as a `KeepTogether` block:

1. Skill title: `NunitoBold 8.5pt INK_PRIMARY`
2. Stat impact: `Nunito 7pt INK_MUTED`, left-indent 10pt
3. Blank-line table (see below)
4. Ask prompt: `Nunito 8pt INK_SECONDARY`, left-indent 10pt, prefixed with `"Ask: "`

**Blank-line table — the most important element on page 2.** A 3-column `Table` with column headers `Coursework`, `Clubs / orgs`, `Internship / cert` in `Nunito 8pt INK_MUTED` centered, and a second row of empty cells. Row heights: `[9, 12]` pt. Cell `VALIGN: BOTTOM`. A 1.2pt `INK_SECONDARY` rule via `LINEBELOW` on the second row. Thin vertical separators (`LINEBEFORE` at 0.4pt `RULE_LIGHT`) divide the three columns. Background: `BG_ROW_ALT`. **Printed graphics — not PDF form fields, not fillable widgets.**

**Questions & Follow-ups section.** Three audience subsections: `ASK THE COLLEGE`, `ASK YOUR PARENTS`, `ASK YOURSELF`. Each is a subsection header (`NunitoBold 8pt INK_SECONDARY`) followed by bullet-list paragraphs (`Nunito 8.5pt INK_SECONDARY`, left-indent 10pt). Bullet character: `"• "` prepended in the string, not using ReportLab's `ListFlowable`. Maximum 5 questions per audience; minimum 1. The two static college questions are always rendered first and are hardcoded in the service layer — they do not depend on Gemma.

**Glossary.** A 4-column `Table` in two visual halves (two `Term | Definition` column pairs side by side), filling the live width. Each column pair: 0.55 in term + `(LIVE_W/2 - 0.55 - 0.04)` in definition. `NunitoBold 8pt` terms, `Nunito 8pt` definitions. Row height 18pt. Alternating background white / `BG_ROW_ALT`. The 8 entries: CIP, SOC, ERN, ROI, RES, GRW, AURA, Career risk.

---

### 3.6 Component Specs — Comparison PDF (1 page)

**Title block.** `FredokaOne 16pt` title: `"[Major] — comparing [N] schools · As of [Date]"`. Below it in `Nunito 8pt INK_MUTED`: residency context string listing which schools are in-state vs. out-of-state.

**Mini pentagon strip.** A single `Table` with N+1 columns (label column + one per school). Label column: empty (0.01 in). School columns: `(LIVE_W / N)` each. Each cell contains a nested 1-row `Table` with school name centered (`NunitoBold 9pt`) above a mini `Drawing` from `draw_pentagon()` with `r = 0.28 in`. Mini pentagon uses `label_font_size=5.5`, no value labels. State abbreviation rendered as muted subtext below school name.

**Stats at a Glance table.** N+1 columns: Stat label (1.30 in) + N data columns (`(LIVE_W - 1.30 - 2*0.14) / N` each). Header row: `NunitoBold 8pt` school names on `INK_PRIMARY` fill. Stat label column: `NunitoBold 8pt INK_SECONDARY` with stat full name. Stat label text uses colored Fredoka abbreviation inline. Data cells: `SpaceMono 10pt` values. Leading cell per row: `#EBF9F1` background, `#1A5C38` ink. Non-leading cells: `INK_PRIMARY` ink on alternating white / `BG_ROW_ALT`.

**Cost & ROI block.** Same column structure as stats table. Rows: 4-year cost, Modeled debt, Year-1 earnings, Debt-to-earnings (yr-1). Dollar values in `SpaceMono 9pt`. Debt-to-earnings rendered as `f"{v * 100:.0f}%"`. Leading-cell direction per row (per @fp-data-reviewer's §5 leading-direction table): 4-year cost — lower wins; Modeled debt — lower wins; Year-1 earnings — higher wins; Debt-to-earnings — lower wins. Tie handling and null handling per the same §5 table.

**Career Risk Profile strip.** Same column structure. Rows: 5 risk factors. Level chips in each cell: risk-level ink + background tint, `NunitoBold 7.5pt` centered, ALL-CAPS for Low/Moderate/Elevated/High, OR italic Roman sentence-case "Insufficient data" using the 5th palette entry from §3.4 when the boss `raw_score` is None for that build. Risk factor labels: `Nunito 8pt INK_SECONDARY`.

**Where Each School Pulls Ahead.** Section header + one `Nunito 8.5pt` sentence per school. Format: `"[School] — leads on [factor] and [factor]."` Generated deterministically by identifying the top-2 leading cells per school column. **No Gemma prose** (per Decision #3 / spec scope).

---

### 3.7 Section Header Pattern

Every section (and compact sub-section in the Comparison PDF) uses this 3-element sequence:

1. `Spacer(1, 7)` — or `Spacer(1, 3)` for compact mode
2. `Paragraph(label, FredokaOne 11pt)` — or 9pt for compact
3. `HRFlowable(width="100%", thickness=0.75, color=RULE_LIGHT, spaceBefore=1, spaceAfter=3)` — or `spaceAfter=2` for compact

Do not use `spaceBefore` on the Paragraph style itself.

---

### 3.8 Two-Template Page Architecture

Every `BaseDocTemplate` in this feature uses two `PageTemplate` objects:

- `"main"` — `onPage=on_page` callback that draws the header band, gold accent rule, footer rule, and page number. Used for all interior pages.
- `"last"` — `onPage=on_last_page` callback that calls `on_page` first, then additionally draws the sources citation in the sub-footer zone. Used for the final page of each PDF.

The `"main"` template is listed first in `doc.addPageTemplates([...])` so it is the default. `NextPageTemplate("last")` inserted into the story **before** the final `PageBreak()` (or at the very start of a single-page story) switches the template for the next page rendered.

(Dual-template architecture is retained — without it, the sources citation orphans to an unwanted extra page if it lands in the story flowables. QR code support was cut per Decision #9 revision 2026-05-06.)

---

### 3.9 Print Fidelity Requirements

**Color-only information is not used.** Every risk-level chip carries typographic differentiation (ALL-CAPS for Moderate/Elevated/High, roman for Low). A black-and-white photocopy of either PDF must remain fully readable — hard constraint.

**Font embedding.** All four fonts are embedded as subsets in the PDF binary. Verify by opening in Preview → File Info → Fonts and confirming all four appear as embedded.

**Minimum body font size: 7pt** (sources sub-footer). No text below 7pt except the sub-footer citation. 8pt is the minimum for any data the student or counselor is expected to read without magnification.

**Page count targets.** My Build: exactly 2 pages. Comparison: exactly 1 page (2 at absolute maximum). Production constraints, not soft guidelines. If a data-rich build pushes either over the target count, reduce skill count (5 instead of 6) or reduce glossary row height before relaxing page counts.

**Byte size.** Target under 800 KB per PDF (revised down from the §2 1500 KB soft cap based on sample-render measurements). Pentagon charts are vector `Drawing` objects; no photographic images.

---

### 3.10 Sample PDFs and Reference Implementation

Sample PDFs generated during this design pass:

- `docs/specs/design/feature-pdf-report-exports-mybuild-sample.pdf` — 2 pages, mock data (Purdue ME / Rowan)
- `docs/specs/design/feature-pdf-report-exports-comparison-sample.pdf` — 1 page, 3-school comparison (Purdue / U-Michigan / IUPUI)

The generation script is at `/tmp/generate_fp_pdfs.py` — a design spike, **not** production code. The implementation agent should use it as a reference, not as a starting point for the service layer. The service layer lives at `backend/app/services/pdf_export.py` and must conform to the request/response Pydantic models in §4.

---

### Design Vision Refinement

> Round-2 visual judgment pass (2026-05-06, `@fp-design-visionary`). Validates the round-1 sample PDFs against §3.1–§3.10, calls out staleness in the samples, and locks visual decisions on the two new design elements added during round 2 (the 5th risk-level chip and the data-coverage caveat line). Edits in §3.4 (dark-fill cap), §3.5 (caveat spacing, cost-strip alignment, Level-column width) reflect this pass.

#### 1. Validation pass-through — what's already correct in the samples

The round-1 samples are largely on-spec. The following render correctly and require no further action:

- **Header band.** `INK_PRIMARY` band + white sparkle path + `FUTUREPROOF` wordmark + right-side use-only line + 0.75pt gold rule. Reads as letterhead, not as a dark UI panel. Approved.
- **Profile + context strip.** Two-column proportions (45/55) are right, the Fredoka 14pt name has correct weight against the muted residency line, the right column's `School · Major · As of Date` is the right level of quiet metadata. Approved.
- **Verdict line.** Fredoka 20pt, no period, multi-line wraps gracefully. The "low risk on four of five career factors, including AI displacement. Projected ROI positive by year 7." pull-quote tone is exactly the conversation-starter the page needs. Approved.
- **Pentagon + stat micro-table.** The pentagon's stat-accent vertex labels carry the only Brightpath color through-line on the page and they read clean. Stat micro-table alternation, dot bullets, and value column in SpaceMono 13pt all work. Approved.
- **Suggested Skills page.** The blank-line printable tables under each skill are the most important interaction-on-paper element in the report and they print correctly — the 1.2pt rule under the `[9, 12]` row heights gives the counselor an obvious place to write. The bucket-color subsection headers (AI-Resilience teal, Career-Launch green, Earnings-Ceiling gold) carry stat-accent identity without leaking dark-mode panel colors. Approved.
- **Glossary.** 4-column / 2-half layout fills the live width without crowding. Approved.
- **Comparison mini-pentagon strip.** Three pentagons reading at-a-glance is the entire purpose of the comparison page-1 hero zone, and they do. Approved.
- **Comparison leading-cell highlight.** `#EBF9F1` on `#1A5C38` is faint enough not to scream and bold enough to read on B&W. Approved.

#### 2. Validation flags — staleness in the samples

The samples were rendered before the round-2 spec edits. Three concrete divergences must be fixed in the production renderer (NOT in the sample PDFs — those are reference artifacts of the round-1 design pass and stay as-is):

1. **Cost & ROI strip column 4 is stale.** Sample shows `Break-even | Year 7`. Spec (§3.5) was updated to `Debt-to-earnings (yr-1) | 39%`. Production must implement the spec, not the sample.
2. **Risk chip "LOW" weight is stale.** Sample renders LOW as bold ALL-CAPS. Spec (§3.4) requires LOW as roman, no caps — quieter than the warning levels because LOW is the "good" outcome. Production must follow §3.4, which means three weights/cases coexist in a single column: roman-no-caps Low, bold-ALL-CAPS Moderate/Elevated/High, italic-roman-sentence-case Insufficient data. This is by design — typographic differentiation IS the B&W readability strategy.
3. **QR code is stale.** Sample page 2 shows a QR code in the bottom-right footer. Spec (§3.2) explicitly removed it per Decision #9 revision 2026-05-06. Production must omit it. The sub-footer zone reads sources line + generated-on line only.

The Comparison sample also shows `Break-even year` in the cost block (same staleness as #1). Production renders `Debt-to-earnings (yr-1)` per §3.6.

These do not require re-rendering the samples — flag them in the implementation §6 deviation log and the design audit (`@fp-design-auditor`) will mechanically catch them at audit time. The samples are committed historical reference, not the print contract.

#### 3. Brightpath through-line audit

Per §1 Success Criteria, the only visual through-line between the dark-mode app and the print PDF is **(a) the 5 stat color hues** and **(b) the Fredoka headline display font**. Auditing the samples for leakage:

- Stat hues appear ONLY as: pentagon vertex dots, pentagon vertex labels, comparison Stats-at-a-Glance row label colored abbreviation prefix, suggested-skills bucket subsection headers. Never as fills, panels, or backgrounds. Pass.
- Fredoka appears ONLY at: verdict line, section headers, profile name, comparison title block. Pass.
- `INK_PRIMARY` (`#1A1B2E`) — the brand-dark — appears as a solid fill in 3 places: top header band, Career Risk Profile column-header row (My Build), and three column-header rows on the Comparison page (Stats / Cost / Risk). Each of these is a thin band acting as a print-letterhead or print-table-header convention, not a dark-mode panel. Acceptable as drawn — but a fourth `INK_PRIMARY` panel anywhere would tip the report toward dark-mode-app aesthetics. **A new constraint has been added to §3.4 ("Dark-fill usage cap") to lock this at the current 3-band cap.** Implementation must not introduce additional `INK_PRIMARY` fills (no callout boxes, no sidebars, no hero panels, no "cover sheet" header above the existing band).
- No `BG_DEEP` / `BG_NIGHT` / dark-mode panel hex values appear in either sample. Pass.
- Risk-level background tints (`#FCEAEA`, `#FFF0E8`, `#FFF8E0`, `#E8F5EE`, `#EFF0F4`) and `BG_ROW_ALT` (`#F7F7FB`) are all light and behave as inline cell tints, not panel surfaces. Pass.

Conclusion: Brightpath identity is carried by hue-on-data + Fredoka headlines + the gold rule under the header band. Dark surface usage is letterhead-and-table-header only, capped at 3 bands per page. Pass.

#### 4. The 5th risk-level chip — "Insufficient data"

Spec'd as: ink `#5C5E70`, background `#EFF0F4`, italic Roman, sentence-case "Insufficient data", `NunitoBold 7.5pt` → corrected to `Nunito italic 7.5pt` (NOT bold) in §3.5 above.

Visual hierarchy ladder, by reading "loudness":

```
High         — bold ALL-CAPS, dark red on faint-red — LOUDEST
Elevated     — bold ALL-CAPS, dark orange on faint-orange
Moderate     — bold ALL-CAPS, dark gold on faint-gold
Low          — roman no caps, dark green on faint-green
Insufficient — italic roman sentence-case, neutral gray on neutral-light-gray — QUIETEST
data
```

The neutral gray `#5C5E70` is intentionally chromatically dead. It sits below "Low" in loudness because it has no chroma — gray reads quieter than green. That's correct. **Insufficient data must read as quieter than Low, not as competing with the warning levels.** It does. Approved as drawn.

B&W photocopy distinction Low vs. Insufficient data: the chip COPY itself is the differentiator. "Low" is 3 characters roman. "Insufficient data" is 17 characters italic. They cannot be visually confused on photocopy regardless of grayscale conversion. The italic slant, the sentence-case, the word-length, and the words themselves are all redundant differentiation channels — color is doing the least work in this comparison. Approved.

Token-level lock-in on the 5th chip:
- **Ink:** `#5C5E70` — keep as new dedicated token. Do NOT reuse `INK_MUTED` (`#767888`) — `INK_MUTED` is too light and the chip would read as a rendering glitch. Do NOT reuse `INK_SECONDARY` (`#3D3E52`) — too dark, would compete with the warning chips.
- **Background:** `#EFF0F4` — slightly darker than `BG_ROW_ALT`. On the white-row case, the chip is visibly darker than the row. On the `BG_ROW_ALT` row, the chip is barely visible but still distinguishable. Both cases work. Keep.
- **Weight + style:** Nunito italic 7.5pt, NOT bold. The other 4 chips' bold-vs-roman distinction tracks loudness; italic is the new orthogonal axis for "this is a meta-state, not a value." Bold-italic would shout. Roman-italic is correctly quiet.
- **Casing:** Sentence case, "Insufficient data". Lowercase "i" and "data" preserved. Title case ("Insufficient Data") would read as a heading, not a value. ALL-CAPS would compete with warning levels.
- **Alignment:** Centered in the cell, same as the other 4 chips. Coherent column visual.
- **Column width:** Level column widened from 0.92 in to 1.10 in (edited in §3.5 above) to fit the 17-character string at 7.5pt with 7pt horizontal padding. "Insufficient data" is now the binding column-width constraint, not "MODERATE".

This chip is the "missing data is not zero" rule made visible. Ship as locked above.

#### 5. The data-coverage caveat line

Spec'd placement: directly below the profile + context strip, single-line italic `Nunito 7.5pt INK_MUTED`. Confirmed correct, with one structural refinement now folded into §3.5: **asymmetric vertical spacing** — `Spacer(1, 6)` above the caveat, `Spacer(1, 9)` below — to visually dock the caveat to the verdict line that follows it (rather than letting it tail off the profile strip above).

Why this placement beats the alternatives:

- **Inline with the verdict (e.g. as a footnote-asterisk on the verdict line):** rejected. Cluttering a Fredoka 20pt headline with a 7.5pt italic asterisked aside is exactly the kind of move that makes reports feel like compliance documents instead of conversation starters. The verdict is the headline; let it be a headline.
- **Footer / sub-footer zone:** rejected. The sources citation already lives there at 6pt. A counselor scanning the report does not read the footer in the first 30 seconds. The data-coverage signal must live above the fold of the page-1 reading flow.
- **Below the cost & ROI strip, near the data the caveat qualifies:** rejected. The caveat IS qualifying the verdict line as much as the cost data — the verdict is "low risk on four of five factors" and the counselor needs to know up front that "career-task data is partial" before reading that risk summary. Putting the caveat at the cost strip makes the verdict feel falsely confident for the first 6 inches of page-1.
- **Above the profile strip, at the very top of the live area:** rejected. Top-of-page is real estate for the verdict, not for caveats. Caveats above headlines flip the hierarchy.

Locked placement: between profile strip and verdict, asymmetric spacing docks it visually to the verdict, italic Nunito 7.5pt INK_MUTED, left-aligned, plain (no icon, no bold span, no tinted band). The tone is honest data-coverage signal, not warning. Counselors should read it as "FYI" rendered visually, not as "alarm".

Note the caveat is conditional — when `match_quality == "full"`, this line and its surrounding spacers are NOT rendered, and the verdict line sits directly under the profile strip with the standard 9pt buffer. The caveat does not reserve an empty band when absent.

#### 6. The mixed-units cost & ROI strip

Spec'd: 4 columns, equal width, three dollar values + one percent. Concern raised: would the 3-character percent look stranded next to 7-character dollar values in equal-width columns?

Answer: yes, if values are left-aligned. No, if values are center-aligned. **Refinement folded into §3.5: all 4 cells (labels and values) are center-aligned in the strip.** This kills the stranded-percent visual without breaking the strip's "row 0 = labels, row 1 = values" symmetry. Right-alignment would be the conventional financial-report move and would also work for the 3 dollar values, but the 4th cell's `39%` would then float at the right edge with whitespace to its left — same stranded look, mirrored. Center is the correct compromise.

Mixing units in one strip is acceptable here because the labels do unambiguous unit-disambiguation work — `4-year cost`, `Modeled debt`, `Year-1 median earnings`, `Debt-to-earnings (yr-1)`. Each label's units are explicit in the label itself. The values can render in their native units without confusion. The student and counselor read the labels; the values follow.

What we are NOT doing:
- A separate strip just for the percent — wasteful, breaks visual rhythm.
- A 5-column strip — overcrowds the live width.
- Rendering the ratio as `0.39` — loses immediate-readability for counselors.
- Adding a "% of starting salary" subscript — unnecessary; the label says it.

Lock in the center-aligned 4-column strip with `f"{v * 100:.0f}%"` for column 4. Approved.

#### Open questions

None. All four round-2 visual decisions are locked and edited into §3.4 / §3.5 above.

---

### 3.11 Copy Specifications

> Owned by `@fp-copywriter`. The PDF voice is NOT the in-app voice. Per §2 Decision #4 and the **PDF / printed report** register-by-surface override added to `voice-guide.md`, every string below drops the RPG metaphor entirely. Data sections speak like **Receipts** (dry, label : value). The questions section speaks like **Next Steps** (verb-led action items). Forbidden vocabulary is enforced by **two** complementary frozensets in `pdf_copy.py`: (a) `RPG_TERMS_FORBIDDEN_IN_PDF` — asserted against the FULL rendered PDF text — `boss`, `boss fight`, `gauntlet`, `Fight AI / Fight Student Loans / Fight the Market / Fight Burnout / Fight the Ceiling / Fight the Future`, `WIN / DRAW / LOSE`, `won / lost / draw`, `reroll`, `build` / `builds` (use *plan* in user-facing copy), `level up / leveled up / level-up`. (b) `FORBIDDEN_IN_GEMMA_OUTPUT` — superset, applied only to Gemma's question strings — adds the in-app stat-code abbreviations (`ERN / ROI / RES / GRW / AURA / HMN`) since Gemma must spell stats out, while the PDF chrome (pentagon vertex labels, stat micro-table, glossary) renders the abbreviations elsewhere.
>
> Every numeric anchor referenced below must come from the §5 source-of-truth table — `pdf_copy.py` reads fields, never recomputes.

#### 3.11.1 Verdict-line template

The verdict line at the top of My Build PDF page 1 is **parameterized, not generated**. The `@fp-copywriter` template is:

```
{Major} at {School}: {risk_summary}. {roi_summary}.
```

- `{Major}` — title-cased major name from `Build.career.major_name` (or fallback `Build.major_name`).
- `{School}` — school name from `Build.school_name`. No "(University of)" reformatting.
- `{risk_summary}` and `{roi_summary}` are computed deterministically by `pdf_copy.verdict_line(build)` from the build's risk-level distribution and `debt_to_earnings_annual` value. No Gemma involvement.
- Maximum length: 200 characters total (P2 test `test_verdict_line_lengths_within_budget`). At 20pt FredokaOne with 26pt leading, 200 chars wraps to 2 lines on the live width — still readable; longer wraps to 3 lines and starts to crowd the pentagon.

##### Risk-summary buckets

`pdf_copy.verdict_line` first computes the count of each `RiskLevel` across the 5 risk factors, ignoring `Insufficient` rows. Bucket selection rules (in order — first match wins):

| Bucket | Condition | `{risk_summary}` text |
|---|---|---|
| `mostly_low` | `count(Low) >= 4` AND `count(High) == 0` | `the data shows steady fundamentals` |
| `mixed_moderate` | `count(High) == 0` AND `count(Elevated) <= 1` AND `count(Low) >= 2` | `the data shows steady fundamentals with one or two factors to watch` |
| `multiple_high` | `count(High) >= 2` | `the data flags multiple risk factors worth a closer look` |
| `mostly_elevated` | (else — i.e. `count(Elevated) + count(High) >= 2` and not `multiple_high`) | `the data shows two or more risk factors worth weighing` |
| `insufficient` | `count(Insufficient) >= 3` (data so thin no honest summary fits) | `the data is partial — read the risk profile below before drawing conclusions` |

If `count(Insufficient) >= 3` AND a non-`insufficient` bucket would also match, `insufficient` wins. The PDF refuses to summarize what it cannot honestly observe. The data-coverage caveat (§3.11.5) addresses the `match_quality` signal separately — that's a coverage-of-the-program flag, this is a coverage-of-the-risk-rows flag. Both can fire on the same page; they say different things.

##### ROI-summary buckets

`pdf_copy.verdict_line` reads `Build.career.debt_to_earnings_annual` (a float, e.g. `0.13` = 13%). Buckets:

| Bucket | `debt_to_earnings_annual` | `{roi_summary}` text |
|---|---|---|
| `strong_roi` | `< 0.08` | `cost recovery looks strong against year-1 earnings` |
| `solid_roi` | `0.08 ≤ x < 0.18` | `cost is in line with year-1 earnings` |
| `caution_roi` | `0.18 ≤ x < 0.30` | `cost is sizable against year-1 earnings` |
| `risky_roi` | `>= 0.30` | `cost is high relative to year-1 earnings` |
| `unknown_roi` | value is `None` | `cost-to-earnings is unavailable for this program` |

Threshold rationale: the 8% / 18% / 30% cuts mirror the categorical bins already used by `roiLabelKey()` in `FinancesCard.tsx` (Strong / Solid / Caution / Risky), so the PDF and the on-screen ROI label agree. Implementor confirms with `@fp-data-reviewer` if the bin edges drift.

##### Worked examples

1. **Mechanical Engineering at Purdue West Lafayette.** `Low x4` (ERN, ROI, RES, AURA Low; GRW Moderate), `debt_to_earnings_annual = 0.11`.
   → `Mechanical Engineering at Purdue West Lafayette: the data shows steady fundamentals. Cost is in line with year-1 earnings.`

2. **Marketing at Ball State University.** `Low x1`, `Moderate x1`, `Elevated x2`, `High x1`, `debt_to_earnings_annual = 0.22`.
   → `Marketing at Ball State University: the data shows two or more risk factors worth weighing. Cost is sizable against year-1 earnings.`

3. **Studio Art at Indiana University South Bend.** `Low x0`, `Moderate x1`, `Elevated x1`, `High x3`, `debt_to_earnings_annual = 0.41`.
   → `Studio Art at Indiana University South Bend: the data flags multiple risk factors worth a closer look. Cost is high relative to year-1 earnings.`

4. **Education of the Deaf at a smaller program with sparse data.** `Insufficient x3`, `Moderate x1`, `Elevated x1`, `debt_to_earnings_annual = None`.
   → `Education of the Deaf at [School]: the data is partial — read the risk profile below before drawing conclusions. Cost-to-earnings is unavailable for this program.`

Capitalization note: `pdf_copy.verdict_line` capitalizes the first character of `{roi_summary}` after the period (`. Cost…`), and lowercases the first character of `{risk_summary}` after the colon (`: the data…`) — sentence-case for the second clause, lowercase continuation after the colon.

#### 3.11.2 Risk one-liner copy — 5 bosses × 5 levels

`pdf_copy.risk_one_liner(boss_id, level, build)` returns a one-sentence string for each row of the page-1 Career Risk Profile table. Constraints:

- Each string ≤ 120 characters.
- Each string includes one **concrete data anchor** drawn from the build (rendered via `f"…"` so the value is part of the sentence, not a parenthetical).
- Neutral advisory voice. No RPG terms. No exclamation. No "challenging" softening.
- For the `Insufficient` row, the Context column reads `"Data unavailable for this program."` — the same lone string for all 5 bosses (per the spec draft). Per-boss variants are NOT warranted: the value of saying "we don't have AI exposure for this SOC" vs "we don't have O*NET burnout drivers" is zero to a counselor scanning the table; consistency aids scanning.

Anchors per boss (read from `Build`, no recomputation):

- `ai` — percentile rank derived from `Build.career.ai_exposure_percentile` (read directly; if absent, the row is `Insufficient`). Format `f"{p:.0f}th percentile"`.
- `loans` — `Build.career.debt_to_earnings_annual * 100` formatted `f"{v:.0f}%"`. (Same value the cost strip renders.)
- `market` — `Build.career.bls_growth_pct` formatted `f"{v:+.0f}%"` over 10 years. (Sign always shown — `+4%` vs `-2%`.)
- `burnout` — `Build.career.onet_burnout_top_driver` (a short string like `"high stress tolerance demand"`, `"limited contact with others"`). If absent, the row is `Insufficient`.
- `ceiling` — `Build.career.earnings_75th_pct` formatted `f"${v:,.0f}"`. The 75th percentile wage is the standard ceiling proxy already used elsewhere in the app.

If a boss's `raw_score` is non-null but the named anchor field above is `None` for that boss, `risk_one_liner` falls back to the level-only template — the level word survives, the data clause is dropped cleanly, and no `"None%"` strings are ever rendered. Implementor verifies in a unit test (`test_risk_one_liner_handles_null_anchor`).

##### The 25-string table

Field-name placeholders are Python-format style (`{p:.0f}`, `{v:+.0f}`, `{driver}`). Implementor wires these to the field-by-field source-of-truth table in §5.

| Boss | Level | Copy |
|---|---|---|
| **AI displacement risk** | Low | `AI exposure for this occupation sits at the {p:.0f}th percentile — most core tasks remain human-led.` |
| | Moderate | `AI exposure for this occupation sits at the {p:.0f}th percentile — some routine tasks are increasingly automatable.` |
| | Elevated | `AI exposure for this occupation sits at the {p:.0f}th percentile — a meaningful share of tasks could shift to AI within a decade.` |
| | High | `AI exposure for this occupation sits at the {p:.0f}th percentile — most routine tasks could be performed by AI within a decade.` |
| | Insufficient | `Data unavailable for this program.` |
| **Debt burden** | Low | `Modeled year-1 debt service is {v:.0f}% of starting earnings — comfortably below the 10% guideline.` |
| | Moderate | `Modeled year-1 debt service is {v:.0f}% of starting earnings — within the standard manageable range.` |
| | Elevated | `Modeled year-1 debt service is {v:.0f}% of starting earnings — above the recommended ceiling for new graduates.` |
| | High | `Modeled year-1 debt service is {v:.0f}% of starting earnings — well above what early-career income typically supports.` |
| | Insufficient | `Data unavailable for this program.` |
| **Job market outlook** | Low | `BLS projects {v:+.0f}% employment change over 10 years — a growing field.` |
| | Moderate | `BLS projects {v:+.0f}% employment change over 10 years — roughly steady demand.` |
| | Elevated | `BLS projects {v:+.0f}% employment change over 10 years — slower than the all-occupations average.` |
| | High | `BLS projects {v:+.0f}% employment change over 10 years — a contracting field.` |
| | Insufficient | `Data unavailable for this program.` |
| **Burnout risk** | Low | `O*NET task profile shows {driver} — within typical workload patterns.` |
| | Moderate | `O*NET task profile shows {driver} — a real demand worth understanding before committing.` |
| | Elevated | `O*NET task profile shows {driver} — a known burnout driver in this occupation.` |
| | High | `O*NET task profile shows {driver} — a leading burnout factor in this occupation.` |
| | Insufficient | `Data unavailable for this program.` |
| **Earnings ceiling** | Low | `BLS 75th-percentile wage is ${v:,.0f} — meaningful upside above the median.` |
| | Moderate | `BLS 75th-percentile wage is ${v:,.0f} — modest upside above the median.` |
| | Elevated | `BLS 75th-percentile wage is ${v:,.0f} — limited room to grow above the median.` |
| | High | `BLS 75th-percentile wage is ${v:,.0f} — earnings plateau early in this occupation.` |
| | Insufficient | `Data unavailable for this program.` |

Length check: longest string above is the AI Elevated/High line at ~120 chars after substitution (e.g. `"AI exposure for this occupation sits at the 87th percentile — a meaningful share of tasks could shift to AI within a decade."` = 121 chars). Implementor budget-tests this. If a substitution edges over 120, drop `"for this occupation"` from the AI templates — that's the safe cut.

Capitalization note: every string starts with a capital letter (sentence-case) — the Risk-Factor column to its left already does the labeling; the Context column reads as a complete sentence on its own.

#### 3.11.3 Glossary entries (8)

The 4-column glossary `Table` on page 2. Term in `NunitoBold 8pt`, definition in `Nunito 8pt`. Each definition ≤ 120 characters. The reader is a 16-year-old who has not seen these acronyms before.

| Term | Definition |
|---|---|
| **CIP** | Federal program code (Classification of Instructional Programs) — the standard for naming college majors. |
| **SOC** | Federal occupation code (Standard Occupational Classification) — how the BLS names jobs. |
| **ERN** | Earnings — typical pay for graduates of this program working in this occupation. |
| **ROI** | Return on Investment — how the cost of this program compares to what graduates earn. |
| **RES** | AI Resilience — how much of this occupation's work is hard for AI to do, blended from task-level data. |
| **GRW** | Growth — the BLS 10-year employment-change projection for this occupation. |
| **AURA** | Brand Gravity — institutional pull (selectivity, completion, financial standing) shared by every program at the school. |
| **Career risk** | Five factors that affect long-term outcomes: AI displacement, debt burden, job market, burnout, and earnings ceiling. |

Note on AURA: when the value is `None` for a school (institution lacks EADA / IPEDS-Finance coverage), the page-1 pentagon already renders the dash placeholder per existing pentagon-stat-explanation conventions. The glossary entry stays visible regardless.

#### 3.11.4 Static fallback questions per audience

`pdf_questions.py` declares these as module-level constants. They render verbatim when Gemma is unreachable, malformed, or empty. Each is ≤ 200 characters.

##### Ask the college — 2 static-mandatory + 1 fallback

The two mandatory questions are inserted at indices `[0, 1]` of the `ask_the_college` list on every render — Gemma success OR fallback. The 3rd is the fallback that fills in only when Gemma adds nothing.

```python
STATIC_COLLEGE_MANDATORY: tuple[str, str] = (
    "Which majors at {school} most often lead graduates into {career}?",
    "How can I augment this major with the suggested skills above — through coursework, clubs, or internships you already offer?",
)

STATIC_COLLEGE_FALLBACK: str = (
    "What outcomes data do you publish for this program — median earnings one year out, employment rate, average debt at graduation?"
)
```

The two mandatory questions are confirmed: the first reverses the discovery direction (counselor maps career → majors at this school, the inverse of what the app does); the second cashes in the page-2 skills section directly. Both already render in voice and on-budget. The `{school}` and `{career}` tokens are filled by `pdf_questions` from `Build.school_name` and `Build.career.title`.

Wording-tweak note vs the §1 Success Criteria draft: the original draft was *"Which majors at [School] will yield [Career]?"* — `will yield` is a slight register-mismatch (faintly transactional, faintly hedging on prediction). `most often lead graduates into` is the same factual question in the data's own language (Scorecard talks in graduate-outcome rates), reads better aloud at the kitchen table, and avoids implying a guarantee. The second mandatory question ("How can I augment…") is unchanged from the draft except for the phrasing tightener `"the suggested skills above — through coursework, clubs, or internships you already offer?"` which actively names what the counselor's office can offer rather than asking abstractly how to "augment" — same meaning, more pointable.

##### Ask your parents — audience-first voice, ≥ 1 fallback

```python
STATIC_PARENTS_FALLBACK: tuple[str, ...] = (
    "If the loan numbers on page 1 are accurate, can our family carry that monthly payment alongside everything else after I graduate?",
    "Whose career did you watch up close growing up — and what about it would you want for me, or want to spare me from?",
)
```

Voice check — both lines reference the parent (`our family`, `you watch up close`), use action verbs (`carry`, `spare`), and avoid student-internal markers like `Will I` / `Am I`. The first line ties directly to the page-1 cost strip — the most decision-relevant data the parents will see. The second is the long-arc question that turns the kitchen-table conversation away from numbers and into the one place a parent actually has authority: lived experience.

##### Ask yourself — student-first voice, ≥ 1 fallback

```python
STATIC_YOURSELF_FALLBACK: tuple[str, ...] = (
    "Will I still want to be doing this work in 10 years if the day-to-day looks like the O*NET task profile on page 1?",
    "Am I picking this major because it interests me, or because it's familiar — and would I know the difference yet?",
)
```

Voice check — both start with student-internal markers (`Will I` / `Am I`), are present-future tense, anchor to a specific page-1 element, and resist easy answers. The second is the "is this me, or is this inertia" question every counselor wants the student to ask before signing a loan.

#### 3.11.5 Data-coverage caveat copy

Conditional one-line caveat rendered below the profile + context strip on page 1 when `Build.career.match_quality != "full"`. `Nunito 7.5pt italic INK_MUTED`, left-aligned. Asymmetric spacing per visionary §3.5 refinement (`Spacer(1, 6)` above, `Spacer(1, 9)` below). ≤ 140 characters each.

| `match_quality` | Caveat copy |
|---|---|
| `full` | (no caveat rendered) |
| `scorecard_only` | `Note: occupational task data is partial for this program. Earnings, cost, and debt figures are full coverage.` |
| `partial_no_onet` | `Note: O*NET task detail is unavailable for this occupation. Earnings, cost, and debt figures are full coverage.` |

Refinements vs the §3.5 spec drafts:

- Lead with `Note:` instead of em-dash. A counselor scanning the page reads the cue word, then the caveat. Em-dash only at 7.5pt italic muted is easy to miss.
- The two variants now name the actually-missing dataset (`occupational task data` / `O*NET task detail`) rather than both saying "career-task data." A counselor who works with a few of these PDFs will start to learn what `partial_no_onet` means specifically.
- Both end with the same reassurance clause (`Earnings, cost, and debt figures are full coverage`) — the data the counselor will point to most often is unaffected by either coverage gap. That's the load-bearing fact and it ends the line, not the warning.

Length: 110 chars / 117 chars. Both inside budget.

The caveat is honest data-coverage signal, not warning. Counselors should read it as "FYI" rendered visually — italic Nunito 7.5pt INK_MUTED is the right tonal register for a data-provenance footnote that lives above the verdict line.

#### 3.11.6 "Where each school pulls ahead" template

Comparison PDF, one sentence per build. Function `pdf_copy.where_each_pulls_ahead(builds: list[Build]) -> list[str]` returns a list whose length equals `len(builds)`, in the same order.

Template selection rules (in order — first match wins):

| Lead-cell count for this build | Output |
|---|---|
| ≥ 2 | `{School} — leads on {factor1} and {factor2}.` |
| 1 | `{School} — leads on {factor}.` |
| 0 | `{School} — no clear leader on these factors; trade-offs are even.` |

Refinements vs the §3.5 / §3.6 spec drafts:

- The 0-leading-stat case adds `; trade-offs are even` to do work for the reader. A bare `"{School} — no clear leader on these factors."` reads like a put-down. The fuller line names the *positive* observation: when a build leads on nothing, it's because the comparison is balanced, not because the school is bad.
- Tie handling per `@fp-data-reviewer` round-1 ruling: when N builds tie on a row, no cell is marked leading on that row. So a tie reduces a build's lead count by one — never by more. This template handles ties correctly by construction; no separate tie clause needed.
- `{factor}` and `{factor1}/{factor2}` resolve to the human labels — `Earnings`, `ROI`, `AI Resilience`, `Growth`, `Brand Gravity`, `4-year cost` (when leading low), `Modeled debt` (when leading low), `Year-1 earnings`, `Debt-to-earnings ratio` (when leading low), `AI displacement risk` (when leading Low/Moderate), `Debt burden`, `Job market outlook`, `Burnout risk`, `Earnings ceiling` — never the stat code (no `ERN` / `ROI` / `RES` appears in this body text; the page-2 glossary is the only surface where the codes live).
- Stat-priority order for picking the top 2 leading factors per build, when the build leads on more than 2: `Earnings, ROI, AI Resilience, Growth, Brand Gravity, 4-year cost, Modeled debt, Year-1 earnings, Debt-to-earnings ratio, AI displacement risk, Debt burden, Job market outlook, Burnout risk, Earnings ceiling`. The rule is "the two leading factors a counselor cares about most, named first." Stats lead, then cost/ROI, then risk levels.
- ≤ 200 chars per line (P2 test `test_where_each_pulls_ahead_handles_ties`).

##### Worked examples

- Build leads on ERN and ROI: `Purdue West Lafayette — leads on Earnings and ROI.`
- Build leads only on lowest 4-year cost: `Indiana University Bloomington — leads on 4-year cost.`
- Build leads on lowest 4-year cost and lowest modeled debt: `Indiana University Bloomington — leads on 4-year cost and Modeled debt.`
- Build leads on nothing (balanced trade-offs): `Ball State University — no clear leader on these factors; trade-offs are even.`

---

### Interactions

- **Export My Build PDF** — click button, see brief loading spinner (≤8s typical), browser-prompted download. If error, inline error toast ("Couldn't generate the PDF. Try again."). No retry counter.
- **Export Comparison PDF** — same as above with the three guards in Surface 2.
- **The PDF itself is non-interactive.** No form fields. The Coursework / Clubs / Internship blanks are blank line-printed graphics, not fillable widgets.

### Responsive Behavior (web triggers only)

- **Trigger buttons** — desktop primary, must remain reachable on tablet (≥768px). Mobile (<768px) shows the export button collapsed into the existing overflow / share menu.
- **The PDF itself is fixed at US Letter (8.5×11").** A4 is out of scope for hackathon (US-only judging context).

### Accessibility

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| My Build export button | `btn-export-pdf-build` | `<button>` | "Export this build as a PDF" |
| My Build student-name input | `input-export-student-name` | `<input>` | "Optional: your name on the PDF" |
| Comparison export button | `btn-export-pdf-compare` | `<button>` | "Export this comparison as a PDF" |
| Loading spinner | `status-pdf-export` | `role="status"` | "Generating your PDF…" |
| Error toast | `alert-pdf-export-error` | `role="alert"` | "PDF export failed. Try again." |

PDF document: `/Title`, `/Author` (`FutureProof`), `/Subject`, `/Keywords` metadata fields populated. `/Lang` set to `en-US`. PDF/UA tagging is NICE-TO-HAVE but not blocking — hackathon timeline.

---

## §4 Technical Specification

### Architecture Overview

A new `app.services.pdf_export` module owns rendering both PDFs from the existing `Build` model and the existing `compare_builds` data shape. It depends on a new `app.services.pdf_questions` module that makes a single scoped Gemma call (via the existing `app.services.gemma_client`) to generate the 3-audience question arrays, with deterministic static fallbacks for every audience. Both modules are pure-Python, no I/O to disk.

A new `app.routers.pdf_export` exposes two endpoints — `POST /build/{build_id}/pdf` (My Build) and `POST /builds/compare/pdf` (Comparison) — that load the relevant build(s), invoke the export service, and stream `application/pdf` bytes back. Both endpoints validate request scope (build ownership / 3-school cap / same-major guard) before doing any work.

The frontend gains a small `frontend/src/api/pdf.ts` client and one trigger component per surface (`ExportPdfButton.tsx` for `/my-build`, inline button in `CompareView.tsx`).

The existing markdown writer `app.services.report_gen` is **untouched** — it serves the internal `reports/` audit trail, a different concern.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/pyproject.toml` | Modify | Add `reportlab>=4.2.0,<5.0.0`. (No QR dependency — Decision #9 revised 2026-05-06.) |
| `backend/app/services/gemma_client.py` | Modify | Extend `generate_chat_async` to accept two new keyword-only parameters: `timeout_s: float \| None = None` (passes to `httpx.AsyncClient(timeout=...)` so a hung Ollama call returns control in 6s instead of the default ~180s) and `response_format: Literal["json"] \| None = None` (when `"json"` and the active backend is Ollama, sets `format: "json"` on the `/api/chat` payload; for OpenRouter, sets `response_format: {"type": "json_object"}`). Both are opt-in — existing callers' behavior is unchanged. Required by `pdf_questions.py` to honor the spec's 6s timeout + JSON-mode contract; without this change, the <15s p95 success criterion is not achievable. |
| `backend/app/services/pdf_export.py` | Create | New service. Pure-Python PDF generation. Two public functions: `generate_build_pdf(build: Build, *, student_name: str \| None, audience_questions: AudienceQuestions) -> bytes` and `generate_comparison_pdf(builds: list[Build]) -> bytes`. Returns bytes; never writes to disk. (No `public_app_base_url` arg — QR cut.) |
| `backend/app/services/pdf_questions.py` | Create | New service. `generate_audience_questions(build: Build, *, timeout_s: float = 6.0) -> AudienceQuestions` — single Gemma JSON-mode call (uses the extended `gemma_client.generate_chat_async` with `timeout_s=6.0, response_format="json"`), returns 3 arrays, falls back to static copy on timeout/error/empty/malformed JSON. Static fallbacks live in module-level constants written by `@fp-copywriter`. Every code path (live success, all four fallbacks, cold-env fallback) MUST emit one `logs/gemma.jsonl` record stamped with the resolved `gemma_path` value — the existing `gemma_client.generate_chat_async` writes one record per live call; the fallback paths must emit a synthetic record (helper TBD in `gemma_client.py` extension) so observability never has a blind spot. |
| `backend/app/services/pdf_copy.py` | Create | Pure copy generation: `verdict_line(build) -> str`, `risk_level_for_boss(boss_id, raw_score) -> Literal["Low","Moderate","Elevated","High"]` (thresholds per the per-boss table written into §5 by `@fp-data-reviewer` — derived from `BOSS_SPECS` `win_at_or_above` / `draw_at_or_above` / `floor(draw_at_or_above / 2)` for the High cutoff; NO dataset-relative quartile cuts), `risk_one_liner(boss_id, level, build) -> str`, `where_each_pulls_ahead(builds) -> list[str]`, `data_coverage_caveat(build) -> str \| None` (returns the conditional one-liner from §3.5 when `match_quality != "full"`). All functions enforce the §2 Decision #4 translation table. RPG terms are imported as a forbidden-word constant and asserted-against in unit tests. |
| `backend/app/routers/pdf_export.py` | Create | New FastAPI router (mounted with empty prefix per `builds_collection.router` precedent; tag `["PDF"]` capitalized). Two endpoints: `POST /build/{build_id}/pdf` (returns `application/pdf`); `POST /builds/compare/pdf` (returns `application/pdf`). Validates same-major + 3-build cap on the comparison endpoint. Catches `pdf_export.generate_*` exceptions and re-raises as `HTTPException(status_code=500, detail="PDF generation failed")` so errors flow through `CORSMiddleware` and the frontend gets CORS-correct error responses (precedent: `backend/app/routers/wrapped.py:92-103`). |
| `backend/app/main.py` | Modify | Register the new router. |
| `backend/app/models/api.py` | Modify | Add request/response Pydantic models — see "Data Model Changes" below. |
| `backend/tests/services/test_pdf_export.py` | Create | Backend unit tests for `pdf_export.py`. |
| `backend/tests/services/test_pdf_questions.py` | Create | Backend unit tests for the Gemma fallback paths. |
| `backend/tests/services/test_pdf_copy.py` | Create | Backend unit tests for verdict line + risk-level mapping + RPG-language regex test. |
| `backend/tests/routers/test_pdf_export.py` | Create | Backend integration tests for the two endpoints. |
| `frontend/src/api/pdf.ts` | Create | API client. `exportBuildPdf(buildId, opts) -> Promise<Blob>` and `exportComparisonPdf(buildIds) -> Promise<Blob>`. |
| `frontend/src/components/build-results/ExportPdfButton.tsx` | Create | The download trigger on `/my-build`. Optional inline name field. Triggers browser download via `URL.createObjectURL`. |
| `frontend/src/components/build-results/ExportPdfButton.test.tsx` | Create | Vitest. |
| `frontend/src/screens/BuildResultsScreen.tsx` | Modify | Mount `<ExportPdfButton>` near existing share/save controls (location TBD by visionary). |
| `frontend/src/components/menu/CompareView.tsx` | Modify | Add the comparison export button + the 3-build cap + same-major guard tooltip. |
| `frontend/src/components/menu/CompareView.test.tsx` | Modify | (Authorized) — add coverage for the new export button + guards. |
| `frontend/src/i18n/en.json` (or canonical i18n file) | Modify | Add copy strings: button labels, error messages, guard tooltips, name-field placeholder. |
| `docs/reference/stat-display-surfaces.md` | Modify | Add Section 9 — "PDF Reports (My Build PDF + Comparison PDF)" — both as Tier 4 / Skip explain affordance, like Wrapped renderer. |
| `docs/reference/voice-guide.md` | Modify | Add "PDF / printed report" row to "Register by Surface" table — speaks like Next Steps + Receipts; **drops the RPG metaphor** (the one register-by-surface RPG-exception). |

### Data Model Changes

#### New Pydantic models (in `backend/app/models/api.py`)

**`RiskLevel` literal placement.** Add `RiskLevel = Literal["Low", "Moderate", "Elevated", "High"]` to the existing module-level literals near `AskScopeKind` at the top of `backend/app/models/api.py`. Repo convention is module-level Literals, not nested inside model classes.

**Request models — flat (per repo convention; no `StudentNameInput` base class):**

```python
from pydantic import BaseModel, Field
from typing import Literal

# placed near AskScopeKind at the top of api.py
RiskLevel = Literal["Low", "Moderate", "Elevated", "High", "Insufficient"]
# "Insufficient" is the neutral missing-data chip, NOT a default-to-High —
# see §3.4 palette table and pdf_copy.risk_level_for_boss docstring.

class ExportBuildPdfRequest(BaseModel):
    """POST /build/{build_id}/pdf body."""
    student_name: str | None = Field(
        default=None,
        max_length=80,
        description="Optional. Pre-filled from build profile in the UI.",
    )

class ExportComparisonPdfRequest(BaseModel):
    """POST /builds/compare/pdf body."""
    build_ids: list[str] = Field(..., min_length=2, max_length=3)
    student_name: str | None = Field(default=None, max_length=80)

class AudienceQuestion(BaseModel):
    """One question rendered into the PDF."""
    text: str = Field(..., max_length=240)
    is_static_mandatory: bool = False  # set on the 2 college "always-render" questions

class AudienceQuestions(BaseModel):
    """Output of pdf_questions.generate_audience_questions."""
    ask_the_college: list[AudienceQuestion] = Field(..., min_length=1, max_length=5)
    ask_your_parents: list[AudienceQuestion] = Field(..., min_length=1, max_length=5)
    ask_yourself: list[AudienceQuestion] = Field(..., min_length=1, max_length=5)
    gemma_path: Literal["live", "fallback_timeout", "fallback_empty",
                        "fallback_malformed", "fallback_disabled"]
    # gemma_path is logged via observability — never rendered into the PDF.
    # Every value (including "live") corresponds to exactly one logs/gemma.jsonl record.
```

#### No DuckDB / Iceberg / MCP table changes.

The PDF is a derived view of existing `Build` and `compare_builds` data. No new pipelines, no schema evolution.

### Service Changes

#### `backend/app/services/pdf_export.py`

```python
def generate_build_pdf(
    build: Build,
    *,
    student_name: str | None,
    audience_questions: AudienceQuestions,
) -> bytes:
    """Render the 2-page My Build PDF for a single build.

    Returns PDF bytes. Never writes to disk.

    Caller MUST resolve audience_questions before calling (typically via
    pdf_questions.generate_audience_questions). This service is pure-sync
    rendering — no Gemma calls inside, no I/O.

    Raises a ReportLab-derived exception on render failure; the router
    wraps that in HTTPException(500).

    Embeds:
    - Page 1: header strip (with conditional data-coverage caveat when
      build.career.match_quality != "full"), verdict line, pentagon,
      5-stat micro-table, cost & ROI strip (4-year cost · modeled debt ·
      year-1 earnings · debt-to-earnings %), 5-row career risk profile.
    - Page 2: top-6 suggested skills (3 buckets), 3-audience questions,
      glossary footer, sources line.
    """

def generate_comparison_pdf(
    builds: list[Build],
) -> bytes:
    """Render the 1-page (2-max) Comparison PDF for 2-3 builds.

    Caller MUST validate len(builds) ∈ {2, 3} and that all builds share
    the same 4-digit CIP family before calling this. Service raises
    ValueError if those preconditions fail (router translates to 400).

    Returns PDF bytes. Never writes to disk.
    """
```

#### `backend/app/services/pdf_questions.py`

```python
async def generate_audience_questions(
    build: Build,
    *,
    timeout_s: float = 6.0,
) -> AudienceQuestions:
    """Generate the 3-audience question set via a single scoped Gemma call.

    Calls gemma_client.generate_chat_async with timeout_s=6.0 and
    response_format="json" (both new keyword args added in this spec).
    Without those, the call would inherit ~180s default timeout and lose
    JSON-mode contract — neither is acceptable for the <15s p95 budget.

    Always returns a non-empty AudienceQuestions:
    - On Gemma success: live questions (capped at 5/audience inclusive).
      "Ask the college" always begins with the 2 static-mandatory questions
      followed by 0-3 Gemma additions. gemma_path = "live".
    - On Gemma timeout: static fallback. gemma_path = "fallback_timeout".
    - On Gemma network-error or HTTP error: static fallback.
      gemma_path = "fallback_timeout" (transport-level failures bucket here).
    - On empty Gemma response: static fallback. gemma_path = "fallback_empty".
    - On malformed JSON or schema-mismatched Gemma response: static fallback.
      gemma_path = "fallback_malformed".
    - When INFERENCE_BACKEND is missing or both backends unreachable:
      static fallback. gemma_path = "fallback_disabled".

    Static-fallback contract: 2 static-mandatory college questions are
    ALWAYS present at indices [0, 1]; "Ask your parents" and "Ask yourself"
    each contain >=1 static fallback question.

    Observability contract: every code path emits exactly one
    logs/gemma.jsonl record stamped with the resolved gemma_path. The live
    path is logged by gemma_client.generate_chat_async itself; fallback
    paths emit a synthetic record via the new helper added to
    gemma_client.py (so observability has zero blind spots).

    gemma_path is NEVER rendered into the PDF — observability only.
    """
```

The Gemma prompt design and JSON schema are written by `@fp-copywriter` and reviewed by `@genai-architect` during DESIGN VISION.

#### `backend/app/services/pdf_copy.py`

```python
RPG_TERMS_FORBIDDEN_IN_PDF: frozenset[str] = frozenset({
    "boss", "bosses", "boss fight", "boss fights", "gauntlet",
    "fight ai", "fight student loans", "fight the market",
    "fight burnout", "fight the ceiling", "fight the future",
    "won", "lose", "lost", "draw",  # Note: case-insensitive match;
    "win", "wins", "losses", "draws",  # disambiguate from data labels.
    "reroll", "rerolled", "build", "builds",  # PDF says "plan"
    # C2 (genai-architect §10): close the level-up gap between prompt and post-filter.
    "level up", "leveled up", "level-up",
})
# This is asserted against the FULL rendered PDF text in test_pdf_copy.py
# via reportlab's text extraction. False-positive risk: "win" is a
# substring of "winter" — the regex is word-boundary-anchored. See tests.
# Note: stat abbreviations (ERN/ROI/RES/GRW/AURA/HMN) are NOT in this set
# because the PDF deliberately renders them in the pentagon vertex labels,
# the stat micro-table abbreviation column, the comparison stats-at-a-glance
# table, and the glossary. They are forbidden in Gemma's question output
# only — see FORBIDDEN_IN_GEMMA_OUTPUT below.

FORBIDDEN_IN_GEMMA_OUTPUT: frozenset[str] = (
    RPG_TERMS_FORBIDDEN_IN_PDF
    # C3 (genai-architect §10): in-app stat-code abbreviations are forbidden
    # in Gemma's generated question text — Gemma must spell stats out
    # ("Earnings" / "Return on Investment" / "AI Resilience" / "Growth" /
    # "Brand Gravity") so the questions read naturally to a counselor or
    # parent who has not seen the abbreviations. The PDF chrome (pentagon,
    # micro-table, glossary) renders the abbreviations elsewhere — that is
    # not Gemma output and is not subject to this filter.
    | frozenset({"ern", "roi", "res", "grw", "aura", "hmn"})
)
# Applied by pdf_questions.py to each Gemma-generated question string AFTER
# Pydantic validation, BEFORE returning to caller. A match triggers
# gemma_path="fallback_malformed" and replaces Gemma's output with static
# fallbacks. See test_pdf_questions.py for the full coverage matrix.

def verdict_line(build: Build) -> str:
    """One-sentence display verdict, parameterized by risk-level template.

    Format spec (copywriter writes the templates):
      "{Major} at {School}: {risk_summary}. {roi_summary}."
    """

def risk_level_for_boss(boss_id: BossId, raw_score: int | None) -> RiskLevel:
    """Map raw_score (the in-app boss raw_score value) to advisory bucket.

    Thresholds are deterministic per-boss values derived from BOSS_SPECS
    in backend/app/services/boss_fights.py — NOT dataset-relative
    quartiles (rejected by @fp-data-reviewer in §5 because the PDF
    service has no DuckDB access and dataset-relative cuts produce
    non-deterministic output across runs).

    Per-boss thresholds — see the explicit table in §5 written by
    @fp-data-reviewer. Summary form:
        raw_score >= win_at_or_above   → "Low"
        raw_score >= draw_at_or_above  → "Moderate"
        raw_score >= floor(draw_at_or_above / 2) → "Elevated"
        raw_score <  floor(draw_at_or_above / 2) → "High"
        raw_score is None              → "Insufficient"

    The "Insufficient" return is the missing-data signal — caller
    renders the neutral "Insufficient data" chip (§3.4 palette).
    NEVER default missing data to "High": that would silently
    misrepresent unknown as bad ("missing data is not zero" — see
    @fp-data-reviewer round-1 ruling, re-confirmed round 2 in §5).

    The §5 table enumerates the resolved cutoffs for each of the 5
    bosses (ai, loans, market, burnout, ceiling); implementor reads
    that table as the contract.
    """

def risk_one_liner(
    boss_id: BossId,
    level: RiskLevel,
    build: Build,
) -> str:
    """One-sentence advisory copy for a (risk factor, level) pair.

    Pulls one concrete data anchor from the build (e.g. for AI: the
    Karpathy/composite percentile; for Debt: debt-to-income; for Market:
    BLS growth pct; for Burnout: O*NET burnout drivers; for Ceiling: 75th
    percentile wage). Templates written by @fp-copywriter.
    """

def where_each_pulls_ahead(builds: list[Build]) -> list[str]:
    """One sentence per build identifying which stats it leads on.

    Output length == len(builds). Each sentence: "{School name} leads
    on {top 1-2 stats}." Auto-generated from PentagonStats + cost/ROI
    fields per the leading-direction table in §5 (higher wins for
    ERN/ROI/RES/GRW/AURA + year-1 earnings; lower wins for 4-year cost,
    modeled debt, debt-to-earnings).
    """

def data_coverage_caveat(build: Build) -> str | None:
    """Return the conditional one-line caveat from §3.5 when the build's
    data coverage is partial.

    - build.career.match_quality == "full" → None (no caveat rendered)
    - "scorecard_only" → caveat about partial career-task data
    - "partial_no_onet" → caveat about partial occupational-task detail

    Final wording owned by @fp-copywriter. Distinct from the
    CIP-substitution caveat (suppressed per
    feedback_no_substitution_caveat.md) — match_quality is a
    data-coverage signal, not a substitution signal.
    """
```

#### `backend/app/routers/pdf_export.py`

```python
from fastapi import APIRouter, HTTPException, Response

# Empty prefix matches builds_collection.router precedent.
# Tag is capitalized "PDF" (matches FastAPI/repo convention for acronyms).
router = APIRouter(prefix="", tags=["PDF"])

@router.post("/build/{build_id}/pdf")
async def export_build_pdf(
    build_id: str,
    body: ExportBuildPdfRequest,
) -> Response:
    """Returns application/pdf bytes for the 2-page My Build PDF.

    Loads the build via existing builds service. 404 if missing.
    Calls pdf_questions.generate_audience_questions (Gemma may fail
    gracefully). Calls pdf_export.generate_build_pdf. On render failure,
    catches the underlying ReportLab exception and re-raises as
    HTTPException(500, detail="PDF generation failed") so the response
    flows through CORSMiddleware (precedent: wrapped.py:92-103).
    Returns Response(content=bytes, media_type='application/pdf',
    headers={'Content-Disposition': f'attachment; filename="..."'}).
    """

@router.post("/builds/compare/pdf")
async def export_comparison_pdf(
    body: ExportComparisonPdfRequest,
) -> Response:
    """Returns application/pdf bytes for the 1-page Comparison PDF.

    Validates:
    - 2 <= len(build_ids) <= 3 (Pydantic does this).
    - Every build_id resolves to a Build (404 if any missing).
    - All builds share the same 4-digit CIP family (400 if not, with
      copy that points the user back to single-build PDFs).

    Calls pdf_export.generate_comparison_pdf. Same render-failure
    handling as export_build_pdf above. Returns Response.
    """
```

### Gemma-touching surfaces

The new `pdf_questions.py` is the only Gemma call site introduced here, and it depends on the extended `gemma_client.generate_chat_async` (new `timeout_s` and `response_format` kwargs added in this spec — see file table). Audit per the spec-writer's Gemma checklist:

- **Timeout posture** — `timeout_s=6.0` on every call. Without this kwarg (i.e. before this spec's gemma_client extension), a hung Ollama call inherits the ~180s default and breaks the <15s p95 budget. The 6s cap is the load-bearing change from the architect's G1 finding.
- **JSON-mode contract** — `response_format="json"` on every call. Ollama backend sets `format: "json"` on the `/api/chat` payload; OpenRouter backend sets `response_format: {"type": "json_object"}`. Either backend MUST honor this — implementor adds the per-backend translation in `gemma_client.py`.
- **Fallback behavior** — Defined above; static-only output path. The 2 static-mandatory college questions are guaranteed even on a cold env.
- **`logs/gemma.jsonl` capture — every code path emits exactly one record.** The live path is logged by `gemma_client.generate_chat_async` itself (existing behavior). Each of the four fallback paths (`fallback_timeout`, `fallback_empty`, `fallback_malformed`, `fallback_disabled`) emits a synthetic record via a new helper in `gemma_client.py` so observability has zero blind spots — the architect's G3 finding. Implementor verifies via `test_pdf_questions.py` (one assertion per `gemma_path` value).
- **Both inference backends** — `INFERENCE_BACKEND=ollama` (local) AND `INFERENCE_BACKEND=openrouter` (cloud) MUST work. Tested end-to-end in `test_pdf_questions.py` with mocked `gemma_client`.
- **Rate limits / concurrency** — In `openrouter` mode, hackathon demo could see bursts (a counselor exporting back-to-back). The PDF endpoint is not artificially serialized; FastAPI's default async concurrency applies. If we hit OpenRouter rate-limit (HTTP 429), the Gemma client raises and `pdf_questions` falls back. No explicit retry — the static fallback IS the retry policy.

### Gemma System Prompt and JSON Schema

Owned by `@fp-copywriter`. Reviewed by `@genai-architect` during DESIGN VISION. The constants below live as module-level strings in `backend/app/services/pdf_questions.py`.

#### Scoping rule

Per `feedback_scoped_llm_contexts.md`, this prompt receives only what the model needs to write 0–3 questions per audience:

- `school_name` (str)
- `career_title` (str)
- `major_name` (str)
- `top_two_risks: list[(label, level)]` — the two factors with the worst (highest) `RiskLevel`, in order, where `level ∈ {Low, Moderate, Elevated, High}`. `Insufficient` rows are skipped before ranking; if fewer than 2 ranked rows remain, the list is shortened to 0 or 1.
- `top_two_strengths: list[(label, level)]` — symmetric: the two factors with the best (lowest) `RiskLevel`, used to balance the question generation against doom-framing.

Nothing else. No skills, no Gemma's-Take prose, no branches, no skill recs, no profile name, no `gauntlet` raw scores. The model has no use for them and including them increases the chance of hallucinated specifics. Build-context payload is target ≤ 200 tokens.

#### Token budget

- System prompt: ≤ 300 tokens (target ~250 tokens — measured by `tiktoken cl100k_base` as a rough proxy; Gemma's SentencePiece tokenizer runs 5–12% higher, putting actual Gemma tokens at ~315–340 against a 300-token cl100k ceiling). **A2 (genai-architect §10): Implementor MUST measure the final `_SYSTEM` constant with `tiktoken cl100k_base` and document the result in the `pdf_questions.py` module docstring before merge.** If the measurement exceeds 300, the recommended trim is to collapse the closing instruction (`"If you cannot write a question..."` block) to: `"Return [] for any audience you cannot write for. No explanation."` — saves ~15 tokens with no semantic loss.
- Build context (user message): ≤ 200 tokens.
- Output (response): ≤ 700 tokens — 9 questions max × ~70 tokens each, plus JSON syntax. Pad for safety with a 1024-token max.

#### JSON Schema (response contract)

The contract enforced by Pydantic on the response side is:

```python
{
    "ask_the_college": [str, ...],   # 0..3 entries; static mandatory questions
                                     # are added by service code at indices [0, 1]
    "ask_your_parents": [str, ...],  # 0..3 entries
    "ask_yourself": [str, ...],      # 0..3 entries
}
```

Each string ≤ 240 characters (`AudienceQuestion.text` cap). The service post-validates length and rejects (→ `fallback_malformed`) if any string exceeds the cap.

The service does NOT ask Gemma to produce all 5 entries per audience because:

1. The 2 static-mandatory college questions are guaranteed elsewhere (always rendered at indices `[0, 1]` regardless of Gemma output). Asking Gemma to also produce them invites duplication and cross-talk.
2. Floor-of-1 is satisfied by static fallback constants (§3.11.4). Asking Gemma for a guaranteed-non-empty array introduces a "say *something*" pressure that produces filler.
3. 0–3 is a creative cap, not a floor — the model can write zero questions for an audience if it has nothing useful to add. The service then ships only the static fallbacks for that audience.

#### System prompt — production constant

Place this exact string as `_SYSTEM` at the top of `backend/app/services/pdf_questions.py`. Format-strings of the build context are inserted as the user message, NOT into the system prompt itself.

```python
_SYSTEM = (
    "You write follow-up questions for a one-page printed report a high "
    "school student takes home from a 90-second guidance-counselor "
    "conversation. The report shows a school, a major, a likely career, a "
    "five-stat profile, a five-row risk profile, and a cost-and-earnings "
    "strip. The student will read these questions aloud or silently with a "
    "counselor, with a parent, and to themselves.\n\n"
    "Voice: candid, concrete, useful. Coach posture, not cheerleader. "
    "Treat the student and audience as adults making a six-figure decision. "
    "No flattery, no hype, no apology. Each question is one sentence and "
    "names something specific from the build context (a school, a career, "
    "a risk factor, a number) — never a vague 'your future' or 'your "
    "passion'.\n\n"
    "Audience-voice rules (strict):\n"
    "- ask_the_college: audience-first. The student is talking to admissions, "
    "  a department head, or a counselor. Use action verbs ('publish', "
    "  'show', 'connect', 'tour') and refer to the school by name. NEVER "
    "  start with 'Will I' or 'Am I'.\n"
    "- ask_your_parents: audience-first. The student is at the kitchen "
    "  table. Reference family ('our family', 'you'), use shared verbs "
    "  ('carry', 'cover', 'spare'). NEVER start with 'Will I' or 'Am I'.\n"
    "- ask_yourself: student-first. The student is asking themselves. "
    "  Start with 'Will I', 'Am I', 'Do I', or 'Would I'. Present-future "
    "  tense. NEVER address an external audience.\n\n"
    "Anchor each question to a concrete element of the build. If the top "
    "risk is debt burden, write a debt question. If the top risk is AI "
    "displacement, write an AI question. Don't write the same question "
    "twice across audiences in different words.\n\n"
    "FORBIDDEN VOCABULARY — these terms appear in the in-app product but "
    "MUST NOT appear in any output you produce here. The output is for a "
    "printed advisory report and these terms read as unserious in print:\n"
    "  boss, boss fight, gauntlet, fight, win, lose, draw, won, lost, "
    "  reroll, build, builds, level up, ERN, ROI, RES, GRW, AURA, "
    "  HMN, Fight AI, Fight Student Loans, Fight the Market, Fight "
    "  Burnout, Fight the Ceiling, Fight the Future, WIN, DRAW, LOSE.\n"
    "If you need to refer to the cost-vs-earnings ratio, say 'debt-to-"
    "earnings' or 'debt service'. If you need to refer to AI exposure, "
    "say 'AI displacement', 'automation', or 'AI exposure'. If you need "
    "to refer to the program, say 'this program' or 'this major', not "
    "'this build' or 'this plan'.\n\n"
    "Length: each question is one sentence, 240 characters maximum.\n"
    "Count: zero to three questions per audience. Write fewer if you have "
    "nothing useful to add — the report has guaranteed static questions "
    "filling any gaps. Do not pad. Do not write filler.\n\n"
    "Output format: valid JSON, exactly this schema, no prose, no "
    "code-fence, no commentary. Each array holds zero to three short "
    "question strings. Example shape (illustrative only — do not echo "
    "these exact strings):\n"
    '{"ask_the_college": ["Question for the college?"], '
    '"ask_your_parents": ["Question for the parents?"], '
    '"ask_yourself": ["Will I question for myself?"]}\n'
    "If you cannot write a question for an audience, return an empty "
    "array for that audience. Do not write 'N/A', do not apologize, do "
    "not explain."
)
```

#### User-message template (build context)

The build context Gemma receives is small, scoped, and entirely string-formatted from already-loaded fields. No DuckDB queries. No additional Gemma round-trips. Place this as the helper in `pdf_questions.py`:

```python
# C5 (genai-architect §10): centralize the BossId → advisory-label mapping in
# ONE place so pdf_copy.py (risk-profile rendering) and pdf_questions.py
# (Gemma scoping) cannot drift. Derived from §2 Decision #4 translation table.
# Lives in pdf_questions.py and is also imported by pdf_copy.py.
_BOSS_ADVISORY_LABEL: dict[BossId, str] = {
    "ai":      "AI displacement risk",
    "loans":   "Debt burden",
    "market":  "Job market outlook",
    "burnout": "Burnout risk",
    "ceiling": "Earnings ceiling",
}


def _top_two_risks(build: Build) -> list[tuple[str, RiskLevel]]:
    """Return the up-to-2 boss outcomes most concerning for the build.

    Each tuple is (advisory_label, risk_level). The advisory_label is
    sourced from _BOSS_ADVISORY_LABEL — never the raw BossId, never the
    in-app display name ("Burnout Boss", "Fight AI"). Rows where
    risk_level is "Insufficient" are skipped — Gemma should not be asked
    to riff on missing data. Returns at most 2 entries; may return [].
    """


def _top_two_strengths(build: Build) -> list[tuple[str, RiskLevel]]:
    """Return the up-to-2 boss outcomes most reassuring for the build.

    Symmetric to _top_two_risks. "Strongest" means lowest risk level.
    Same labeling rules; Insufficient rows skipped.
    """


def _user_prompt(build: Build) -> str:
    risks = _top_two_risks(build)            # list[(label, level)] — Insufficient skipped
    strengths = _top_two_strengths(build)    # list[(label, level)] — Insufficient skipped
    risks_str = "; ".join(f"{lbl}: {lvl}" for lbl, lvl in risks) or "(none ranked)"
    strengths_str = "; ".join(f"{lbl}: {lvl}" for lbl, lvl in strengths) or "(none ranked)"
    return (
        f"School: {build.school_name}\n"
        f"Major: {build.career.major_name or build.major_name}\n"
        f"Career: {build.career.title}\n"
        f"Top risk factors: {risks_str}\n"
        f"Strongest factors: {strengths_str}\n"
        "\n"
        "Write the JSON object now."
    )
```

A typical realized message looks like:

```
School: Purdue University West Lafayette
Major: Mechanical Engineering
Career: Mechanical Engineers
Top risk factors: Burnout risk: Elevated; AI displacement risk: Moderate
Strongest factors: Earnings ceiling: Low; Debt burden: Low

Write the JSON object now.
```

Total context: ~80 tokens. Comfortably under the 200-token budget; leaves headroom if the call sites later add a one-line "audience hints" addendum without exceeding the cap.

#### Failure-mode handling (referenced from `pdf_questions.py` docstring)

- **Timeout (6s exceeded)** → `gemma_path = "fallback_timeout"`. Static questions render. Synthetic JSONL record stamped.
- **Empty response (Gemma returns `""` or whitespace)** → `gemma_path = "fallback_empty"`.
- **Non-JSON response, JSON-but-wrong-schema response, or any string > 240 chars** → `gemma_path = "fallback_malformed"`.
- **A3 (genai-architect §10): Implementor MUST strip leading/trailing code fences before `json.loads`.** OpenRouter-routed Gemma occasionally wraps valid JSON in ```` ```json ... ``` ```` even with `response_format` set. Pattern: `re.sub(r'^```(?:json)?\s*\|\s*```$', '', raw, flags=re.S)`. Without this, a code-fenced but otherwise valid response unnecessarily routes to `fallback_malformed`. Coverage in `test_code_fence_wrapped_json_is_parsed` (P0).
- **Forbidden term detected anywhere in the response (case-insensitive, word-boundary regex over `FORBIDDEN_IN_GEMMA_OUTPUT`)** → `gemma_path = "fallback_malformed"`. Note: the broader `FORBIDDEN_IN_GEMMA_OUTPUT` set (RPG terms + stat-code abbreviations) is applied here, NOT `RPG_TERMS_FORBIDDEN_IN_PDF`, because Gemma must spell stats out even though the PDF chrome renders the abbreviations. The detection is applied to each question string AFTER Pydantic validation, BEFORE returning to the caller. A leak through the system prompt MUST not reach the renderer.
- **`INFERENCE_BACKEND` unset / both backends unreachable** → `gemma_path = "fallback_disabled"`.

Each fallback path emits exactly one `logs/gemma.jsonl` record stamped with the resolved `gemma_path` value (architect's G3 contract).

#### Why these constraints minimize the fallback rate

- The forbidden-word list is in the system prompt, not just post-hoc filter. Gemma 4 27B observes negative constraints reliably when they're stated explicitly with the targeted vocabulary enumerated; it routinely violates them when they're paraphrased ("avoid game-like language") instead of named.
- The audience-voice rules pin per-audience starts ("Will I" / "Am I" markers) explicitly, so the audience-voice tests (`test_voice_audience_first_for_college_and_parents`, `test_voice_student_first_for_ask_yourself`) detect drift at the prompt level — the model rarely violates a rule it's been told to honor literally.
- The 0-to-3 floor (instead of 1-to-3) lets Gemma return empty arrays when it has nothing real to say, which keeps the output honest. This is a no-filler license.
- The output schema is named in the prompt with the exact JSON shape, paired with `response_format="json"` at the API level. Belt-and-suspenders: even if one layer fails, the other catches it.

### Testing Impact Analysis

> **Existing tests touched:** `frontend/src/components/menu/CompareView.test.tsx` (adding new export button + guard tooltip coverage) and `frontend/src/screens/BuildResultsScreen.test.tsx` (adding new export button mount). All other tests should be unaffected.

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `frontend/src/components/menu/CompareView.test.tsx` | All existing tests | Med | New button mounts in the toolbar; if positioning shifts the FAB or chat trigger, existing test selectors might miss. Mitigated by data-testid on new button. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | All existing tests | Low | New button is additive; should not affect existing flows. |
| `backend/tests/routers/test_builds.py` (if it exists) | All existing tests | Low | New router is registered separately; existing build endpoints unchanged. |
| `backend/tests/services/test_report_gen.py` (if it exists) | All existing tests | None | `report_gen.py` is not modified by this spec. |
| `frontend/src/components/menu/BuildCard.test.tsx` | Multi-select tests | Low | Multi-select behavior unchanged; only the comparison export button is new. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `frontend/src/components/menu/CompareView.test.tsx` | Add 3+ tests for: export-button-visible, export-button-disabled-when-cross-major, export-button-disabled-when-4-builds, export-button-click-fires-api. | Required for new UI affordance. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | Add 1+ test mounting `<ExportPdfButton>` and verifying its `data-testid`. | Required for new UI affordance. |

#### Confirmed Safe

If ANY of the following fail, STOP and escalate — those failures indicate this spec's changes regressed unrelated behavior:

- `backend/tests/services/test_boss_fights.py` (any) — boss-fight math is the source of the risk-level mapping; must remain green.
- `backend/tests/services/test_stat_engine.py` (any) — pentagon math is the source of stat values; must remain green.
- `frontend/src/components/CompareSchoolsPanel.test.tsx` — leaderboard is unrelated; must remain green.
- `frontend/src/components/build-results/FinancesCard.test.tsx` — cost source-of-truth used by both PDF and on-screen; must remain green.
- All tests under `tests/` (pipeline) — pipeline is unaffected.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/services/test_pdf_copy.py` | `test_no_rpg_terms_in_rendered_text` | Generates a PDF for a fixture Build, extracts all text via reportlab's text extraction (or via `PyPDF2`/`pypdfium2`), asserts NONE of the RPG_TERMS_FORBIDDEN_IN_PDF appear (case-insensitive, word-boundary-anchored regex). The non-negotiable Decision #4 enforcement. |
| P0 | `backend/tests/services/test_pdf_copy.py` | `test_risk_level_mapping_covers_all_boss_outcomes` | For every (BossId, BossOutcome, raw_score-quartile) tuple, `risk_level_for_boss` returns one of the 4 RiskLevel values. No silent passthrough. |
| P0 | `backend/tests/services/test_pdf_questions.py` | `test_static_fallback_when_gemma_times_out` | Mock `gemma_client.generate_chat` to raise `asyncio.TimeoutError`. Assert returned `AudienceQuestions` has gemma_path="fallback_timeout", 2 mandatory college questions present, ≥1 question per other audience. |
| P0 | `backend/tests/services/test_pdf_questions.py` | `test_static_fallback_when_gemma_returns_malformed_json` | Mock client to return non-JSON or wrong-schema. Assert fallback. |
| P0 | `backend/tests/services/test_pdf_questions.py` | `test_two_static_college_questions_always_present` | Even on a successful Gemma response, the 2 mandatory college questions are inserted at indices [0, 1]. Gemma's contributions follow. |
| P0 | `backend/tests/services/test_pdf_questions.py` | `test_audience_caps_enforced` | The Pydantic-level cap is 5 (`AudienceQuestions.max_length`). The system prompt asks Gemma for at most 3, but production must be liberal in what it accepts: if Gemma returns 4 or 5, accept; if it returns 6+, clip to 5 (or raise → `fallback_malformed` if the implementor prefers that — choose one and assert). The "≤3 from prompt" is a hint, not a hard contract. |
| P0 | `backend/tests/services/test_pdf_questions.py` | `test_code_fence_wrapped_json_is_parsed` | OpenRouter-routed Gemma sometimes wraps valid JSON in ```` ```json ... ``` ```` fencing despite `response_format="json"`. `pdf_questions.py` MUST strip a leading/trailing code fence before `json.loads` (advisory A3 from genai-architect §10). Pattern: `re.sub(r'^```(?:json)?\s*\|\s*```$', '', raw, flags=re.S)`. Test feeds a code-fenced response and asserts `gemma_path="live"` (NOT `fallback_malformed`). |
| P0 | `backend/tests/services/test_pdf_export.py` | `test_generate_build_pdf_returns_valid_bytes` | Returns non-empty `bytes`, parseable as a PDF, has 2 pages. |
| P0 | `backend/tests/services/test_pdf_export.py` | `test_no_pii_written_to_disk` | Patch `open()` and `Path.write_*` — assert NEITHER is called during `generate_build_pdf`. |
| P0 | `backend/tests/services/test_pdf_export.py` | `test_generate_comparison_pdf_rejects_cross_major` | Two builds with different 4-digit CIP families → ValueError. |
| P0 | `backend/tests/services/test_pdf_export.py` | `test_generate_comparison_pdf_rejects_more_than_3_builds` | 4 builds → ValueError. |
| P0 | `backend/tests/services/test_pdf_export.py` | `test_generate_comparison_pdf_accepts_2_or_3_builds` | 2 builds → ok; 3 builds → ok. |
| P0 | `backend/tests/routers/test_pdf_export.py` | `test_post_build_pdf_returns_application_pdf_content_type` | Endpoint returns `Content-Type: application/pdf`. |
| P0 | `backend/tests/routers/test_pdf_export.py` | `test_post_compare_pdf_400_when_cross_major` | Cross-major returns 400 with helpful copy. |
| P0 | `backend/tests/routers/test_pdf_export.py` | `test_post_compare_pdf_validation_2_to_3_builds` | Pydantic rejects len 1 or len 4. |
| P0 | `backend/tests/services/test_pdf_questions.py` | `test_every_gemma_path_emits_one_jsonl_record` | For each of the 5 `gemma_path` values, assert exactly one record appears in a captured `logs/gemma.jsonl` writer. The architect's G3 contract — observability has zero blind spots. |
| P0 | `backend/tests/services/test_pdf_questions.py` | `test_gemma_client_called_with_timeout_and_json_mode` | Assert the call into `gemma_client.generate_chat_async` includes `timeout_s=6.0` and `response_format="json"`. Architect's G1 contract. |
| P0 | `backend/tests/services/test_pdf_copy.py` | `test_risk_level_per_boss_thresholds_match_data_reviewer_table` | For each (boss_id, raw_score) pair from §5's deterministic threshold table, assert `risk_level_for_boss` returns the expected RiskLevel. No dataset-relative cuts allowed. MUST include `raw_score=None` cases for every boss returning `"Insufficient"` — never `"High"` (the missing-data-is-not-zero rule). |
| P0 | `backend/tests/services/test_pdf_export.py` | `test_insufficient_chip_renders_for_null_raw_score_boss` | Build with `raw_score=None` for one boss → page-1 risk profile renders the italic Roman "Insufficient data" chip and the Context column "Data unavailable for this program." for that row. The other 4 rows still render their normal chips. |
| P0 | `backend/tests/services/test_pdf_copy.py` | `test_data_coverage_caveat_returns_none_for_full_match_quality` | `data_coverage_caveat(build)` returns None when `match_quality == "full"`, returns the corresponding string for `scorecard_only` and `partial_no_onet`. |
| P0 | `backend/tests/routers/test_pdf_export.py` | `test_post_build_pdf_500_when_reportlab_raises` | Patch `pdf_export.generate_build_pdf` to raise; assert router returns 500 with CORS headers, not a 502 / connection-reset / unhandled exception leak. Architect's A3 contract. |
| P1 | `backend/tests/services/test_pdf_export.py` | `test_my_build_pdf_byte_size_under_800kb` | Headroom cap, with a fixture Build that has top-6 skills + maximal Gemma questions. Sample renders measured ~50 KB, so 800 KB is generous. |
| P1 | `backend/tests/services/test_pdf_export.py` | `test_pentagon_vertices_render_numeric_labels` | Extract text, assert `7/10` etc. appear next to stat names. |
| P1 | `backend/tests/services/test_pdf_export.py` | `test_cost_strip_renders_debt_to_earnings_percent` | Extract page-1 text, assert the 4th cost-strip cell is rendered as `f"{v * 100:.0f}%"` and matches `Build.career.debt_to_earnings_annual`. (Replaces the cut "break-even year" cell — see §3.5.) |
| P1 | `backend/tests/services/test_pdf_export.py` | `test_partial_match_quality_renders_caveat_line` | Build with `match_quality="scorecard_only"` produces a PDF whose page-1 text contains the §3.5 caveat string; `match_quality="full"` does not. |
| P1 | `backend/tests/services/test_pdf_questions.py` | `test_voice_audience_first_for_college_and_parents` | Sample Gemma JSON output and verify "Ask the college" / "Ask your parents" entries DON'T start with "Will I" / "Am I" (student-voiced markers). System-prompt assertion. |
| P1 | `backend/tests/services/test_pdf_questions.py` | `test_voice_student_first_for_ask_yourself` | Inverse of above. |
| P1 | `frontend/src/components/build-results/ExportPdfButton.test.tsx` | `test_click_triggers_api_and_download` | Click button → calls API → URL.createObjectURL invoked. |
| P1 | `frontend/src/components/build-results/ExportPdfButton.test.tsx` | `test_optional_name_field_prefills_from_profile` | Profile-name pre-fills the input. |
| P1 | `frontend/src/components/build-results/ExportPdfButton.test.tsx` | `test_error_state_shown_on_api_failure` | API 500 → inline error toast. |
| P1 | `frontend/src/components/menu/CompareView.test.tsx` | `test_export_button_disabled_when_cross_major` | 2 builds, different CIPs → button disabled, tooltip explains. |
| P1 | `frontend/src/components/menu/CompareView.test.tsx` | `test_export_button_disabled_when_4_builds` | 4 selected → button disabled, tooltip explains. |
| P1 | `frontend/src/components/menu/CompareView.test.tsx` | `test_export_button_enabled_for_3_builds_same_major` | 3 same-major builds → button enabled. |
| P2 | `backend/tests/services/test_pdf_copy.py` | `test_verdict_line_lengths_within_budget` | Verdict line ≤ 200 chars (single-line at display 24pt). |
| P2 | `backend/tests/services/test_pdf_copy.py` | `test_where_each_pulls_ahead_handles_ties` | When two builds tie on the leading stat, the autogen line picks the second-best to differentiate. |

#### Test Data Requirements

- **Fixture builds.** A `make_fixture_build()` helper in `backend/tests/conftest.py` (or extending an existing one) that returns a fully-populated `Build` with deterministic `profile_name`, all 5 stats non-null, `gauntlet` with all 5 boss fights resolved, `branches` non-empty, `skill_recs` ≥6, `next_steps` non-empty. Plus 2 sibling fixtures: `make_fixture_build_with_null_aura()` and `make_fixture_build_sparse_data()` for fallback paths.
- **Mocked Gemma client.** Tests patch `app.services.gemma_client.generate_chat_async` directly — never call live Ollama or OpenRouter from tests.
- **3-school comparison fixture.** Three fixture builds with `cipcode="14.1901"`, `"14.1902"`, `"14.1903"` (all `14.19*` family — same 4-digit) for the same-major-positive case; one with `cipcode="11.0701"` for the cross-major-negative case.
- **Build with partial match_quality fixture.** Two sibling fixtures `make_fixture_build_match_scorecard_only()` and `make_fixture_build_match_partial_no_onet()` for the §3.5 caveat-line tests.
- **Build with `raw_score is None` for at least one boss.** A fixture that exercises the "Insufficient" 5th risk-level chip path.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-05-06

#### System Context

Two new HTTP boundaries that turn an existing in-memory `Build` (and the existing 2–3-build comparison shape) into a printable PDF artifact. Sits on the **read** side of the architecture: no Bronze / Silver / Gold zone changes, no MCP tools, no DuckDB schema changes. New layers introduced:

- `app.services.pdf_export` — renders bytes from `Build`. Pure-Python.
- `app.services.pdf_questions` — exactly one Gemma call site; static fallback.
- `app.services.pdf_copy` — verdict copy + RPG→advisory translation.
- `app.routers.pdf_export` — two `POST` endpoints returning `application/pdf`.
- Frontend: `frontend/src/api/pdf.ts` + `ExportPdfButton.tsx` + `CompareView` modification.

Touches: FastAPI router layer, Pydantic models, Gemma client, frontend trigger surfaces. Does NOT touch: stat engine, boss-fight scoring, MCP server, Iceberg tables, DuckDB schema, `report_gen.py`. The architectural boundary the existing `wrapped` router established for binary-byte responses (`Response(content=png, media_type="image/png", headers={"Content-Disposition": ...})`) is the right precedent and the spec follows it.

#### Data Flow Analysis

```
[Browser]
   │ POST /build/{id}/pdf  body: ExportBuildPdfRequest
   ▼
[router pdf_export.export_build_pdf]
   │ 1. _load_build_or_404(build_id)         ← reuse existing pattern from wrapped.py / builds.py
   │ 2. await pdf_questions.generate_audience_questions(build, timeout_s=6.0)
   │       │
   │       ▼
   │   [gemma_client.generate_chat_async]    ← single call, JSON mode
   │       │  (logs/gemma.jsonl record stamped automatically)
   │       ▼
   │   AudienceQuestions Pydantic model      ← parsed/validated; on any failure
   │                                           returns static-fallback model
   │ 3. pdf_export.generate_build_pdf(build, student_name=..., questions=...)
   │       │
   │       ▼
   │   bytes (ReportLab → BytesIO → bytes)
   ▼
Response(content=bytes, media_type="application/pdf",
         headers={Content-Disposition: attachment; filename=...})
   │
   ▼
[Browser] Blob → URL.createObjectURL → download
```

**Boundary inventory (every crossing has a typed contract):**

| Crossing | Contract | Status |
|---|---|---|
| Frontend → router | `ExportBuildPdfRequest` / `ExportComparisonPdfRequest` | Defined in §4 — see model concerns below |
| Router → service | `Build` (existing model) + kwargs | Reuses existing model — clean |
| Service → Gemma | system+user prompt strings, `response_format={"type":"json_object"}` | NOT yet plumbed through `generate_chat_async` — see Concern G1 |
| Gemma → service | JSON string → `AudienceQuestions` (Pydantic-validated) | Defined — clean |
| Service → router | `bytes` | Plain — clean |
| Router → frontend | `application/pdf` body + `Content-Disposition` | Spec mentions both `Response` and `StreamingResponse`; pick one — see Concern A2 |

The data flow is coherent end-to-end. No leaky abstractions, no zone-skipping. The 4-digit CIP family check sits cleanly at the router boundary before the renderer is invoked, matching the "validate first, then do work" pattern established by `OutcomesRequest` validators.

#### Contract Review

**Pydantic models (§4):**

- `ExportBuildPdfRequest(StudentNameInput)` — fine in isolation, but inheriting from a single-field "abstract" base for one field re-use is heavier than it needs to be. The repo precedent is independent flat models (see `OutcomesRequest`, `BuildRequest`, `RerollRequest`). Suggest collapsing to a single flat model with `student_name: str | None`. **Concern M1.**
- `ExportComparisonPdfRequest` declares `student_name` independently rather than via the base — already inconsistent with `ExportBuildPdfRequest`'s inheritance shape. The two requests should share their field declaration approach. **Concern M1.**
- `Field(..., min_length=2, max_length=3)` on `build_ids` mirrors `CompareRequest.build_ids: Field(min_length=2, max_length=4)` — same idiom. Good.
- `RiskLevel` is exported as a module-level `Literal` and used in `risk_level_for_boss`. Fine, but it should live next to `AskScopeKind` and the other `Literal` aliases at the top of `api.py` so all literal aliases are colocated.
- `AudienceQuestion(text=Field(..., max_length=240))` — appropriate length cap.
- `AudienceQuestions.gemma_path: Literal[...]` — six literal values. Good observability handle. The doc string explicitly says it's never rendered into the PDF; that's the right contract — assert that in tests.
- `AudienceQuestions` `min_length=1, max_length=5` on each list — the floor matches Decision #6. The cap matches Decision #6. The 2-static-mandatory guarantee is enforced by service code, not by the schema (Pydantic alone can't say "indices [0,1] must be the static questions"). The service-side test in §4 New Tests Required (`test_two_static_college_questions_always_present`) is the right enforcement; the model doesn't need to encode it.

**API signatures (§4):**

- `POST /build/{build_id}/pdf` — consistent with existing per-build POSTs (`/build/{id}/save`, `/build/{id}/rebuild`, `/build/{id}/wrapped/render`).
- `POST /builds/compare/pdf` — consistent with `POST /builds/compare` and `POST /builds/compare-insights` in `builds_collection.py`. Same `/builds/compare/*` namespace. Good.
- The spec snippet declares `router = APIRouter(prefix="", tags=["pdf"])` with paths starting `/build/...` and `/builds/...`. That's a problem: `main.py` mounts every router with a prefix (e.g. `builds.router` is mounted at `/build`, `builds_collection.router` is mounted at `""`). This new router covers BOTH the `/build/...` and `/builds/...` namespaces, so the cleanest fit is to mount it like `builds_collection.router` — empty prefix, paths declared with their full leading slug. **Concern R1.** See conditions below for the recommended `main.py` registration.

**Gemma call shape (§4):**

- `generate_audience_questions` is `async def`, takes a `Build`, returns `AudienceQuestions`. Caller awaits it from an `async` router handler. Clean.
- Single call, no retry, static fallback as the retry policy: I endorse this. The hackathon p95 budget (15s) cannot accommodate a retry pass; OpenRouter 429 should fall straight to static. The fallback is the retry.
- 6s timeout on a Gemma call with `temperature` low enough for one short JSON object is reasonable on Ollama (Gemma 4 e4b on a warm Ollama returns short JSON in 1–3s typical) and tolerable on OpenRouter (cold model can be 4–8s). 6s strikes the right balance — see Concern G2 for the "should it be 8s" debate.
- **Critical mechanical gap:** `gemma_client.generate_chat_async` (line 465) does NOT accept a `response_format` parameter and does NOT accept a `timeout_s` parameter. The JSON-mode + per-call-timeout plumbing only exists today on the tool-calling code path (line 1336 / 1433 — the `_run_with_tools` family). The spec says "single async call via the existing `gemma_client` with a 6s timeout, JSON-mode" but those two affordances are not reachable from `generate_chat_async` as written. **Concern G1 — must be resolved before implementation.**

#### Findings

##### Sound

- **Service decomposition.** Splitting `pdf_export` (rendering), `pdf_questions` (Gemma), and `pdf_copy` (verdict + risk-level + RPG translation) is the right cut. Three different rates of change, three different test surfaces. The forbidden-word constant lives in `pdf_copy` so it's enforceable from one place.
- **Decision separation from `report_gen.py`.** Decision #2 plus Decision #11 keep the markdown audit writer (committed to `reports/`) and the byte-streaming user export cleanly separated. The "no PII to disk" hard constraint follows automatically from never opening a file in `pdf_export`.
- **Same-major guard at the router boundary.** Validating 2–3 builds via Pydantic, validating same-CIP-family in the handler before invoking the renderer, and having the renderer raise `ValueError` if its preconditions are violated is correct defense-in-depth. The data-reviewer is correctly the one to validate the 4-digit-CIP-family semantics; the architectural placement of the check is right.
- **`gemma_path` field for observability, never rendered.** Six-value `Literal`, never in the PDF. Good discipline.
- **No DuckDB / Iceberg / MCP changes.** Confirmed by reading the spec and inspecting `lifespan` in `main.py`. PDF is purely a derived view of `Build` + `compare_builds` data. No pipeline ripple.
- **Frontend trigger placement.** Adding `<ExportPdfButton>` near the existing share/save controls on `BuildResultsScreen.tsx` (which already has a `data-testid="btn-save-build-bar"` action bar) is non-intrusive and follows the precedent of additive action-bar buttons. The CompareView export button next to the existing "Ask Compare" path is also fine — see Concern F1.
- **Reuse of `_load_build_or_404` pattern.** The spec's `# Loads the build via existing builds service. 404 if missing.` matches the `state.get_build` → `builds.load_build` → 404 pattern in `builds.py:411` and `wrapped.py:48`. Implementer should literally call/import this helper rather than duplicate it.
- **Decision #1 closure.** ReportLab Platypus is the right choice and the spec already documents the design pass that proved it (`docs/specs/design/feature-pdf-report-exports-{mybuild,comparison}-sample.pdf`). Architect re-confirmation is below.

##### Concerns

- **Concern A1 (ReportLab vs Playwright vs WeasyPrint — Decision #1).** **Confirmed: ReportLab Platypus.** Reasoning: (a) the design pass produced two working sample PDFs that exercise every required primitive (multi-template `BaseDocTemplate`, `repeatRows=1`, vector pentagon `Drawing`, embedded TTFs, QR via `ImageReader`, canvas callbacks) — Playwright would re-litigate every print-CSS page-break decision against a moving target; (b) the repo already pulls in Playwright for `wrapped_renderer.py`, so adding a **second** Chromium-using path means two browser-process spawn surfaces during the hackathon demo, which is exactly the operational complexity ReportLab avoids; (c) ReportLab's deterministic byte output is what the "stream as bytes, no temp files" constraint actually requires — `playwright.page.pdf()` writes to disk in some code paths and we do not want a "did we accidentally hit the disk?" debate during the May 18 demo. **Status:** RESOLVED — proceed with ReportLab. **Impact if Playwright were chosen instead:** estimated 1–2 days of print-CSS debugging plus a second concurrency surface against `wrapped_renderer`. **Recommendation:** lock the dep at `reportlab>=4.2.0,<5.0.0` and `qrcode[pil]>=7.4.0` per the §4 file-changes table; do not add WeasyPrint.

- **Concern A2 (`Response` vs `StreamingResponse`).** The spec mentions both in different places (Constraints in §2 says "FastAPI `StreamingResponse` or `Response(content=bytes, ...)`" and §4 router stub says "Returns Response with media_type='application/pdf'"). For ReportLab on a 50KB–800KB output, the right choice is **`Response(content=bytes, media_type="application/pdf", headers={"Content-Disposition": ...})`** — same shape as `wrapped.py:152`. `StreamingResponse` is the right tool for genuinely streamable producers (LLM SSE, long generators); ReportLab returns one finished `bytes` blob and wrapping it in a fake stream adds complexity without latency benefit. **Impact:** none if implementer chooses correctly; ambiguity costs a code-review round-trip. **Recommendation:** spec text in §4 Architecture Overview should commit to `Response(...)`, not "or `StreamingResponse`." Update §2 Constraints accordingly.

- **Concern A3 (mid-render ReportLab failure).** Spec is silent on what happens if ReportLab raises mid-flowable (e.g. unicode crash in a school name, missing TTF font on cold env). Architectural answer: the router catches broadly and returns 500 with a sanitized message, mirroring `wrapped.py:92-103` — and the catch must be inside the request handler so Starlette's bare-500 path doesn't bypass `CORSMiddleware` (the comment in `wrapped.py:96-98` documents exactly this trap). **Impact:** without explicit handling, a unicode font crash returns a `NetworkError` to the browser instead of a usable error toast. **Recommendation:** spec §4 router stub should add `try/except Exception` around the `pdf_export.generate_*_pdf` call and re-raise as `HTTPException(status_code=500, detail=...)`.

- **Concern G1 (Gemma client plumbing gap — BLOCKER for implementation).** The spec's Gemma call shape is "single async call via the existing `gemma_client` with a 6s timeout, JSON-mode." Reading `gemma_client.py`:
  - `generate_chat_async` (line 465) accepts `system`, `messages`, `max_tokens`, `temperature`, `seed`, `model`, `extra` — **no `timeout_s`, no `response_format`**.
  - The Ollama native path (`_ollama_chat_sync`, line 159) hardcodes `timeout=180.0`. The OpenRouter path uses the OpenAI client default.
  - JSON-mode + per-call timeout exist on the tool-calling family (`_run_with_tools`, line ~1336) but those are the wrong entry point for a single-shot JSON call.
  - **Impact:** `pdf_questions.generate_audience_questions(build, timeout_s=6.0)` cannot honor the 6s timeout if it calls `generate_chat_async` as-is. The fallback path will only fire on Ollama transport errors or a 180s hang — i.e., the user waits ~3 minutes before seeing the static fallback. That breaks the <15s p95 success criterion.
  - **Recommendation (one of two acceptable paths):**
    1. Extend `generate_chat_async` to accept `timeout_s: float | None = None` and `response_format: dict[str, Any] | None = None` and plumb both through `_ollama_chat_sync` (httpx timeout) and the OpenRouter `client.chat.completions.create` call. This is ~30 lines of touch and keeps `pdf_questions` thin. **Preferred.**
    2. Have `pdf_questions` call `generate_chat_async` and wrap the await in `asyncio.wait_for(..., timeout=6.0)` for the timeout, then post-validate JSON shape and fall back on `pydantic.ValidationError`. JSON-mode is then enforced via prompt instruction only, not API-level. Acceptable but loses the JSON-mode guarantee.
  - Pick path 1 in implementation. Either way, the spec must explicitly say which one.

- **Concern G2 (timeout-budget reasoning — minor).** 6s for the Gemma call with a 15s p95 envelope leaves 9s for ReportLab + DuckDB + `_load_build_or_404`. Sample renders measured ~50KB at sub-second on warm hardware, and `_load_build_or_404` is a single in-memory dict hit (state) before falling back to a builds-service load. So 6s is fine. **Impact:** under 6s the failure mode is "Gemma returned slowly but valid"; we'd rather have static fallback than a 10s spinner. **Recommendation:** 6s as-spec'd. Document the budget rationale (15s − ~2s render − ~2s slack = ~11s ceiling for Gemma; 6s is comfortably below) inline in `pdf_questions.py` as a comment.

- **Concern G3 (no JSONL log fallback path — minor).** §4 says `pdf_questions.py` calls `gemma_client.generate_chat` (the existing client) which writes to `logs/gemma.jsonl`. True for the success path. On the **fallback** path (timeout / malformed / disabled), the spec needs to also write a record with `gemma_path=fallback_*` so observability can count fallback rates. **Impact:** otherwise we measure only the calls that didn't fall back. **Recommendation:** `pdf_questions` should append one synthetic JSONL record per fallback (or equivalently, ensure the existing `_log_exchange` is called even when Gemma raises before responding — `generate_chat_async` already does this at line 347-349 for the Ollama path and line 391-394 for OpenRouter). Verify this path covers all five `gemma_path` values.

- **Concern M1 (Pydantic model inheritance inconsistency — minor).** `ExportBuildPdfRequest(StudentNameInput)` uses inheritance for one field while `ExportComparisonPdfRequest` re-declares the same field directly. Repo convention (`OutcomesRequest`, `BuildRequest`, `RerollRequest`, `WrapupRequest`) is flat models with no inheritance. **Impact:** stylistic inconsistency, easy to miss when adding a new request type later. **Recommendation:** drop `StudentNameInput`; declare `student_name: str | None = Field(default=None, max_length=80)` directly on both request models. Two lines duplicated, zero loss.

- **Concern R1 (router prefix and `main.py` registration — minor mechanical).** The §4 stub uses `APIRouter(prefix="", tags=["pdf"])` with paths `/build/{build_id}/pdf` and `/builds/compare/pdf`. Mount it like `builds_collection.router` in `main.py`:
  ```python
  application.include_router(pdf_export.router, tags=["PDF"])  # no prefix
  ```
  Do **not** mount it under `prefix="/build"` like `builds.router` is — that would force the `/builds/compare/pdf` path to live elsewhere and split the router. **Impact:** a wrong prefix at mount time produces 404s on one of the two endpoints. **Recommendation:** spec §4 should call out the empty-prefix mount explicitly, matching `builds_collection`. Tag should be `tags=["PDF"]` (caps, like the other tags in `main.py`: `Profile`, `Schools`, `Builds`, `Wrapped`, `AskGemma`).

- **Concern R2 (route-conflict surface — minor).** `POST /build/{build_id}/pdf` lands a new path under the `/build/{build_id}/...` namespace alongside `wrapped/render`, `save`, `rebuild`, `skill-recs`, `skill-pool`, and `reroll`. None of those conflict with `pdf` as a literal segment, so no collision. The `gauntlet` router is also mounted at `/build` with `/{build_id}/...` paths — same story, no collision. **Impact:** none; flagged for the implementer's awareness so they don't accidentally name a path segment `{build_id}` that shadows.

- **Concern F1 (frontend FAB clobber check).** CompareView's existing "Ask Compare" path sits behind `compareScope` (line 650) and the `/chat/ask` flow. The export button is purely additive at the toolbar; the `CompareRequest`-driven "Ask Compare" API is not modified. **Impact:** none, provided the new export button uses a distinct `data-testid` (spec already requires `btn-export-pdf-compare`). The Authorized Test Modifications row for `CompareView.test.tsx` covers this — confirmed safe.

- **Concern F2 (Ollama latency on cold demo machine — minor, deferred).** On a school deploy with Gemma 4 e4b on Ollama and a cold cache, the FIRST PDF export after server start can have a 10–20s warm-up on the LLM call alone. With a 6s call timeout, that first request always falls back. **Impact:** demo-day risk that the very first comparison PDF a judge generates ships static fallback questions instead of live Gemma. **Recommendation:** include `pdf_questions` style traffic in the existing `lifespan` warm-up (`main.py:55-90`) — either (a) run a warm dummy Gemma call at startup, or (b) ship a tiny prompt under `lifespan` that nudges the model into resident memory. NOT a blocker for this spec; can be filed as a follow-up. Flag for `@faang-staff-engineer` review in §8.

##### Blockers

None. Concern G1 is mechanical and resolvable in the implementation phase, but it MUST be addressed — the spec cannot be marked DONE without the timeout actually working end-to-end.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

#### Conditions (CHANGES REQUESTED)

1. **(G1, must-fix-in-spec-and-code)** Resolve the `gemma_client` timeout + JSON-mode plumbing gap. Update §4 Service Changes — `pdf_questions.py` block — to specify path 1 (extend `generate_chat_async` with `timeout_s` and `response_format` kwargs and plumb both through Ollama-native and OpenRouter call sites). Add a corresponding row to §4 File Changes for `backend/app/services/gemma_client.py` (`Modify`). Until the spec commits to a path, the implementer cannot honor the 6s budget.
2. **(A2, spec-only)** §4 Architecture Overview and §2 Constraints both equivocate between `Response(content=bytes, ...)` and `StreamingResponse`. Commit to `Response(content=bytes, media_type="application/pdf", headers={"Content-Disposition": ...})` per `wrapped.py:152` precedent. Update both spec passages.
3. **(A3, spec-only)** Add a sentence to §4 Service Changes — `pdf_export.py` block — and to the router stub: ReportLab failures inside `generate_*_pdf` are caught by the router and re-raised as `HTTPException(status_code=500, detail=...)` so the response flows through `CORSMiddleware`. Reference `wrapped.py:92-103` as the precedent.
4. **(R1, spec-only)** §4 should explicitly state: `application.include_router(pdf_export.router, tags=["PDF"])` in `main.py` (no prefix). Router declares `APIRouter(tags=["PDF"])` (no `prefix=""` literal — the empty default is canonical). Tag spelling capitalized to match `Profile`, `Schools`, `Builds`, `Wrapped`, `AskGemma`.
5. **(M1, spec-only)** Drop `StudentNameInput` base class. Declare `student_name: str | None = Field(default=None, max_length=80)` on both `ExportBuildPdfRequest` and `ExportComparisonPdfRequest` directly. Move `RiskLevel = Literal[...]` to the top of `api.py` next to `AskScopeKind` so all `Literal` aliases are colocated.
6. **(G3, spec-only)** Add a sentence to §4 Gemma-touching surfaces: each fallback path (`fallback_timeout`, `fallback_empty`, `fallback_malformed`, `fallback_disabled`) appends one record to `logs/gemma.jsonl` so observability can count fallback rate. Confirmed by `test_static_fallback_when_gemma_times_out` and friends in the New Tests Required table — but the JSONL write must be explicit.
7. **(F2, follow-up flag, not a spec change)** Note in §11 Final Notes: the Ollama cold-call risk on demo day. The fix (warm-up nudge in `lifespan`) is out of scope here but should be a follow-up issue.

---

#### Round 2 (re-review)
**Status:** APPROVED
**Reviewed:** 2026-05-06

Verification pass against the 6 round-1 conditions plus the data reviewer's break-even Blocker resolution and Decision #9 QR cut. All conditions verified by reading the spec line-by-line; no implementation has begun.

**Round-1 condition verification:**

| # | Condition | Where addressed | Verdict |
|---|---|---|---|
| G1 | `gemma_client.generate_chat_async` extended with `timeout_s` + `response_format` | §4 File Changes line 485 (new Modify row for `gemma_client.py` with both kwargs documented + per-backend translation noted); §4 `pdf_questions.py` docstring lines 608–611 reflect the new call signature | Resolved |
| A2 | Commit to `Response(content=bytes, ...)`, NOT `StreamingResponse` | §2 Constraints line 185 explicitly says `Response(content=bytes, media_type="application/pdf", headers={"Content-Disposition": ...})` and adds "Not `StreamingResponse` (the bytes are fully materialized in memory before send; streaming adds no benefit and complicates error handling)" | Resolved |
| A3 | Router catches ReportLab exceptions, re-raises as `HTTPException(500)` so CORSMiddleware fires | §4 File Changes line 489 spells out the catch + re-raise + `wrapped.py:92-103` precedent; router stub lines 743–745 carry the same language; new P0 test `test_post_build_pdf_500_when_reportlab_raises` at line 831 enforces the contract | Resolved |
| R1 | Router prefix `""`, tag `["PDF"]` capitalized | Router stub line 731 shows `APIRouter(prefix="", tags=["PDF"])`; §4 File Changes line 489 reiterates "tag `["PDF"]` capitalized" | Resolved |
| M1 | Drop `StudentNameInput`; flat models; move `RiskLevel` literal near `AskScopeKind` | §4 lines 510–519 add explicit "RiskLevel literal placement" callout pointing to top of `api.py` near `AskScopeKind`; lines 521–532 show `ExportBuildPdfRequest` and `ExportComparisonPdfRequest` as flat models with `student_name` declared inline on both; `StudentNameInput` removed entirely | Resolved |
| G3 | Every `gemma_path` value (live + 4 fallbacks) emits one `logs/gemma.jsonl` record | §4 File Changes line 487 commits to "Every code path... MUST emit one `logs/gemma.jsonl` record stamped with the resolved `gemma_path` value" with the helper-in-`gemma_client.py` plumbing called out; §4 Gemma-touching surfaces line 774 reinforces; P0 test `test_every_gemma_path_emits_one_jsonl_record` at line 827 covers all 5 values | Resolved |

**Round-2 deltas (data reviewer Blocker + Decision #9):**

- **Break-even year replaced with `debt_to_earnings_annual`** (Cost & ROI strip 4th cell). Verified: §3.5 line 354 commits to `Build.career.debt_to_earnings_annual` rendered as `f"{v * 100:.0f}%"`; line 356 explicitly documents the replacement and reasoning; new P1 test `test_cost_strip_renders_debt_to_earnings_percent` at line 834 enforces the formatter and source field; data-reviewer source-of-truth table at line 1043 (corresponding row) is consistent.
  - **Architectural assessment:** the field is already on `CareerOutcome` (`models/career.py:99-103`) and already rendered on `FinancesCard.tsx`, so the PDF and on-screen surface stay in sync without any new computation, no new boundary crossings, no new pipeline ripple. The single-source-cost rule is preserved (`published_cost_4yr` remains the residency-aware anchor for cell 1; `debt_to_earnings_annual` is a derived ratio, not a substitute cost). Stat-display surfaces index update (Decision #10) is unaffected — the strip cells are not stat values.
  - No new architectural concerns introduced.

- **QR code cut entirely** (Decision #9 revision). Verified: Decision #9 line 178 documents the cut and the missing `/build/:build_id` route as the trigger; §3.4 footer band line 259 notes "No QR code per Decision #9 revision"; §4 architecture overview line 472 mentions no QR dependency; §4 File Changes line 484 explicitly says "No QR dependency"; §4 service signature line 486 confirms no `public_app_base_url` arg on `generate_build_pdf`; §2 Out of Scope line 198 adds the deferred QR + missing-route language.
  - **Architectural assessment:** removing the QR removes a planned dependency (`qrcode[pil]`), removes a service argument, removes a footer-callback drawing path, and removes the share-link composition concern raised by the data reviewer (no live route, no orphaned scan target). This is a strict reduction in scope and surface area — no concerns. My round-1 Concern A1 mentioned "lock the dep at `qrcode[pil]>=7.4.0`" — that recommendation is now moot; the spec correctly omits the dep.
  - Search across spec confirms no residual `qrcode[pil]` / `ImageReader` references in the active service spec; one mention remains in §3.10 sample/reference text and one in §4 test-data list ("Mocked QR code library") that is now dead but harmless. **Minor cleanup (non-blocking):** §4 Test Data Requirements line 851 still says "Mocked QR code library. Acceptable to assert on the URL string passed in rather than visually decoding the QR for most tests; one P1 test does the decode round-trip." This is stale post-Decision-#9 and should be deleted to avoid confusing the test-writer; flagged for spec-author cleanup, not a blocker.

**Verdict:**

- [x] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

All six round-1 conditions are addressed at the spec level. The data reviewer's break-even Blocker is resolved by routing to an existing `CareerOutcome` field with no new architectural surface. The QR cut is a strict scope reduction and removes one planned dependency cleanly. Implementation may proceed once `@fp-data-reviewer` round-2 also clears.

**Non-blocking flag for spec author:** strike the stale "Mocked QR code library" bullet at §4 Test Data Requirements (line ~851) — leftover from the pre-Decision-#9 draft. Costs nothing to remove; will save the test-writer a confused minute.

After conditions 1–6 are reflected in the spec, I will re-review and approve. Conditions 2–6 are spec-text edits only; condition 1 is the load-bearing one that touches `gemma_client.py` during implementation.

---
**Decision #1 final answer:** **ReportLab Platypus.** Confirmed. Implementer should not revisit this question.

### @fp-data-reviewer Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-05-06

#### Data Sources Affected

The PDF is a **derived view** of the existing `Build` model (loaded via `app.services.builds.load_build`) and the existing `compare_builds` shape. No new pipelines, no new MCP tools, no Gold-zone schema changes. The PDF reads from `Build.career` (a `CareerOutcome`) and `Build.gauntlet` (a `GauntletResult`) — the exact same in-memory objects that hydrate `BuildResultsScreen`, `FinancesCard`, and `CompareView`. That part is correct by construction: trace any number rendered by the PDF back to a `CareerOutcome` field and it is the same value the screen displays.

This review confirms field-level provenance for the five numeric strips and flags four data-integrity issues that need resolution before code lands.

#### Crosswalk Impact

None. The PDF does not invoke ConceptNormalizer, does not re-run CIP→SOC mapping, and does not re-derive any pentagon stats. The `same-major guard` reads `Build.cipcode` directly and compares 4-digit prefixes — purely a string operation, no crosswalk involved. Crosswalk-confidence already lives on `CareerOutcome.overall_confidence` / `match_quality` and is preserved through the Build, but the spec does not expose either field on the PDF surface (see Concern #1 below).

#### Formula Verification

##### Pentagon stat values (ERN, ROI, RES, GRW, AURA)

**Sound.** The five stats live on `CareerOutcome.stats: PentagonStats` (`backend/app/models/career.py:59-65`). The on-screen pentagon, the Wrapped renderer, and `compare_builds` (`backend/app/services/builds.py:425-429`) all read from `Build.career.stats.{ern,roi,res,grw,aura}`. The PDF MUST do the same — read `Build.career.stats` directly. **No re-computation in the PDF service.** I am explicitly forbidding the PDF from recomputing stats from raw rows.

A subtle but important note: `stats.res` is a **blended** value (raw_stat_res + raw_stat_hmn averaged and clamped — see comments in `career.py:62`). The Fight AI scorer in `boss_fights.py:_score_ai` deliberately scores from `raw_stat_res + raw_stat_hmn`, NOT from `stats.res`, to preserve bit-exact thresholds. The PDF's pentagon must render `stats.res` (the display value), and the Fight AI risk-level chip must derive from the gauntlet's `BossFightResult.raw_score` for the `ai` boss, NOT from `stats.res`. The two are different scales. Any code that reaches into `raw_stat_res` / `raw_stat_hmn` for the PDF is wrong.

##### Cost & ROI strip — 4-year cost, modeled debt, year-1 median earnings, break-even

**Mostly sound, one new computation flagged.** Per `feedback_single_source_cost.md`, the cost field is residency-aware and lives on `CareerOutcome`. The four strip cells must map as follows:

| PDF cell | Source field on `CareerOutcome` | On-screen surface that uses the same field |
|---|---|---|
| 4-year cost | `published_cost_4yr` | `FinancesCard.tsx:233`, `compare_builds:509` |
| Modeled debt | `modeled_total_debt` | `FinancesCard.tsx:242`, `compare_builds:499` |
| Year-1 median earnings | `earnings_1yr_median` | `FinancesCard.tsx:231`, `compare_builds:513` |
| Break-even year | **NOT AN EXISTING FIELD — see Concern #2** | none |

`net_price_annual` (the average aided-student annual price) is **NOT** the cost field for the PDF. Per `FinancesCard.tsx` and the comments in `career.py:99-103`, `net_price_annual` is for "context only" displays and lives on a different row of the FinancesCard ("Average net price"). The `published_cost_4yr` is the residency-aware sticker that ROI and Loans Boss math both anchor on (`stat_engine.py:174-204`). **The PDF's "4-year cost" cell MUST read `published_cost_4yr`, not `net_price_annual * 4`.** This is the single-source-cost rule from memory.

##### 5-row Career Risk Profile — boss raw_score → RiskLevel

**Concrete thresholds derived from `boss_fights.py:BOSS_SPECS`.** See Concern #3 below — the spec's docstring mapping (WIN→Low / DRAW→Moderate / LOSE→Elevated) is correct, but "High" is unspecified and the bands per boss are non-uniform. Below is the full table I am writing into the spec record now so `pdf_copy.py:risk_level_for_boss` can be implemented deterministically.

#### Field-by-field source-of-truth table

| PDF element | Source field | Defined in | Same as on-screen? |
|---|---|---|---|
| Pentagon ERN value | `Build.career.stats.ern` | `models/career.py:60` | Yes — `BuildResultsScreen` pentagon, `compare_builds:425` |
| Pentagon ROI value | `Build.career.stats.roi` | `models/career.py:61` | Yes — same |
| Pentagon RES value (blended) | `Build.career.stats.res` | `models/career.py:62` | Yes — same |
| Pentagon GRW value | `Build.career.stats.grw` | `models/career.py:63` | Yes — same |
| Pentagon AURA value | `Build.career.stats.aura` | `models/career.py:64` | Yes — same |
| 4-year cost | `Build.career.published_cost_4yr` | `models/career.py:108` | Yes — `FinancesCard` "Published cost (4 yr)" |
| Modeled debt | `Build.career.modeled_total_debt` | `models/career.py:112` | Yes — `FinancesCard` "Modeled debt" |
| Year-1 median earnings | `Build.career.earnings_1yr_median` | `models/career.py:85` | Yes — `FinancesCard` "Starting salary" |
| AI risk raw_score | `Build.gauntlet.fights[boss=ai].raw_score` (= `raw_stat_res + raw_stat_hmn`, scale 0-20) | `boss_fights.py:_score_ai` | Yes — gauntlet screen reads same |
| Loans risk raw_score | `Build.gauntlet.fights[boss=loans].raw_score` (= `11 - bosses.loans` readiness, scale 1-10) | `boss_fights.py:_score_loans` | Yes — same |
| Market risk raw_score | `Build.gauntlet.fights[boss=market].raw_score` (= `stats.grw`, scale 1-10) | `boss_fights.py:_score_market` | Yes — same |
| Burnout risk raw_score | `Build.gauntlet.fights[boss=burnout].raw_score` (= `11 - bosses.burnout`, scale 1-10) | `boss_fights.py:_score_burnout` | Yes — same |
| Ceiling risk raw_score | `Build.gauntlet.fights[boss=ceiling].raw_score` (= `bosses.ceiling`, scale 1-10) | `boss_fights.py:_score_ceiling` | Yes — same |

#### `risk_level_for_boss` — explicit threshold table

The mapping below is derived directly from `boss_fights.py:BOSS_SPECS` (`win_at_or_above` / `draw_at_or_above`). The four-bucket advisory schema (Low / Moderate / Elevated / High) splits the existing three-bucket WIN / DRAW / LOSE by carving "High" off the bottom of LOSE — defined as **the worst quartile of the LOSE band** for each boss, computed as `floor(draw_at_or_above / 2)`. This keeps the PDF deterministic and avoids any "worst quartile across the dataset" computation the PDF service is not equipped to do (and that would change with every new build the dataset gets).

| Boss | Score range (from scorer) | High (worst) | Elevated | Moderate | Low |
|---|---|---|---|---|---|
| `ai` | 0–20 (raw_stat_res + raw_stat_hmn) | < 5 | 5–9 | 10–13 | ≥ 14 |
| `loans` | 1–10 (readiness, inverted from boss score) | ≤ 2 | 3–4 | 5–6 | ≥ 7 |
| `market` | 1–10 (= GRW) | ≤ 2 | 3 | 4–5 | ≥ 6 |
| `burnout` | 1–10 (readiness, inverted from boss raw) | ≤ 2 | 3–4 | 5–6 | ≥ 7 |
| `ceiling` | 1–10 (boss raw or fallback ERN) | ≤ 2 | 3–4 | 5–6 | ≥ 7 |
| any | `raw_score is None` (`unknown`) | render "Insufficient data" chip — do NOT default to High | | | |

Mapping rule the implementor MUST follow:

- **`raw_score >= win_at_or_above`** → `Low`
- **`draw_at_or_above <= raw_score < win_at_or_above`** → `Moderate`
- **`floor(draw_at_or_above / 2) <= raw_score < draw_at_or_above`** → `Elevated`
- **`raw_score < floor(draw_at_or_above / 2)`** → `High`
- **`raw_score is None`** → caller renders a 5th visual chip ("Insufficient data") — do NOT default to `High`

This means there is **no dataset-wide quartile computation needed** at PDF generation time. The §4 docstring's hint that "High" might be defined as "worst quartile of raw_score across the dataset" is rejected for these reasons:

1. It introduces a dataset-scan dependency the service does not have (no DuckDB access in the PDF service).
2. It is non-deterministic across runs as the dataset evolves.
3. It splits one student's outcome based on what other students got — that is a property the in-app boss math deliberately does NOT have.

The mapping function should compute thresholds from `BOSS_SPECS` at runtime, not hardcode integers, so future tuning of `boss_fights.py` thresholds flows through to the PDF without a second edit.

#### Comparison PDF — leading-cell direction table (explicit)

The spec implies but does not enumerate the direction. Here it is, row by row, deterministic:

| Comparison row | Source field(s) | Direction | "Leading" cell |
|---|---|---|---|
| ERN | `stats.ern` | higher | highest value |
| ROI | `stats.roi` | higher | highest value |
| RES | `stats.res` | higher | highest value |
| GRW | `stats.grw` | higher | highest value |
| AURA | `stats.aura` | higher | highest value |
| 4-year cost | `published_cost_4yr` | **lower** | lowest value |
| Modeled debt | `modeled_total_debt` | **lower** | lowest value |
| Year-1 median earnings | `earnings_1yr_median` | higher | highest value |
| Break-even year | derived (see Concern #2) | **earlier (lower)** | lowest year value |
| AI risk level | derived RiskLevel | "Low" beats "Moderate" beats "Elevated" beats "High" | "Lowest" risk = leading |
| Loans risk level | derived RiskLevel | same | same |
| Market risk level | derived RiskLevel | same | same |
| Burnout risk level | derived RiskLevel | same | same |
| Ceiling risk level | derived RiskLevel | same | same |

Tie-handling: when N builds tie for the leading value on a row, **none** of the cells gets the highlight (a tie is not a lead). The autogen "Where each school pulls ahead" sentence MUST treat that row as not contributing for any school.

`null` handling: a cell whose source value is `null` is **never** the leading cell, regardless of direction. If all N cells are `null`, suppress the row in the comparison entirely or render `—` in every cell with no highlight.

#### "Where each school pulls ahead" — feasibility check

Computable deterministically from the table above. Logic:

1. For each build, count the number of leading cells across all comparison rows.
2. Pick the top 2 leading cells per build (by stat-priority order: ERN, ROI, RES, GRW, AURA, 4-year cost, modeled debt, year-1 earnings, then risk rows).
3. If a build leads on 0 cells, render `"{School} — no clear leader on these factors."` (do NOT invent a lead).
4. If a build leads on 1 cell, render `"{School} — leads on {factor}."`
5. If a build leads on ≥2 cells, render `"{School} — leads on {factor1} and {factor2}."`

The input shape (`Build.career.stats` + `Build.career.published_cost_4yr / modeled_total_debt / earnings_1yr_median`) is sufficient. No additional data needed.

#### Same-major guard — 4-digit CIP family

**Sound, with a clarification.** The spec example "52.0801 and 52.0803 both match 52.08*" is correct: `cipcode[:5]` extracts the 4-digit family in `XX.XX` form (the dot is at index 2; chars 0–4 = `52.08`). This convention is already used at `backend/app/services/intent.py:306` (`prefix = cipcode[:5]`). The project rule that CIPCODE is a string `XX.XXXX` (never a float) is preserved — string-prefix comparison only.

Beware of name collision with the Silver-zone field `cip_family` which is the **2-digit** family (`cipcode[:2]`, e.g. `52` for "Business, Management, Marketing" — see `src/silver/college_scorecard_transformer.py:144`). The PDF's same-major guard is **NOT** that — it is the 4-digit subfamily (`cipcode[:5]`). Implementor must read `Build.cipcode[:5]` directly. Do not pull `Build.career.cipcode[:5]` either; if `substitution_applied` is true (`career.py:192`), `Build.career.cipcode` may be the substituted CIP, not the student's chosen one. **Use `Build.cipcode` (the top-level Build field), not `Build.career.cipcode`.**

##### 4-digit lump risk — flagged (not blocking)

The 4-digit CIP family does sometimes lump programs that are noticeably different in earnings reality. Examples worth flagging in QA:

- `13.10` "Special Education and Teaching" — `13.1001` (Special Education, General) vs `13.1011` (Education of Autistic), `13.1003` (Education of the Deaf and Hard of Hearing). Same family but earnings/job-market data differ across sub-specialties.
- `51.38` "Registered Nursing" — sub-specialties (BSN-track vs MSN-track) often have very different earnings ceilings.
- `11.07` "Computer Science" vs `11.10` "Computer/Information Technology Administration" — DIFFERENT 4-digit families; spec correctly disallows comparison across them.

The guard at the 4-digit level is the right altitude. The risk is acceptable because:

1. The cross-major case (`13.10` vs `11.07`) is the bigger error and the guard catches it.
2. Sub-specialty differences within `13.10` still share enough taxonomy that comparison is meaningful.
3. CompareView's existing UI already permits this same lump (compare_builds is currently mode-agnostic).

**The deaf-education edge case** (per CLAUDE.md: "Jeff's wife teaches deaf education") is `13.1003`. Comparing three schools' `13.1003` programs is valid. Comparing `13.1003` at one school against `13.1001` at two others: the guard ALLOWS this (both `13.10*`) — and the comparison is reasonable since both are special-education taxonomies, but the resulting `published_cost_4yr` and `earnings_1yr_median` may diverge enough that a counselor would want to know they are not strictly the same program. Not a blocker, but `@fp-copywriter` should consider a one-line caveat in the comparison header when the three cipcodes are not identical (only the 4-digit family is shared).

#### QR code URL composition

**See Concern #4 below.** The spec composes `{public_app_base_url}/build/{build_id}` but `frontend/src/App.tsx:21-38` has no `/build/:build_id` route. The `build_id` itself IS stable and shareable (a slug like `purdue-mechanical-engineering-001`, persisted in DuckDB at `_next_id_for` in `builds.py:187`, NOT a session-scoped token). So the data piece is sound. The routing piece is broken.

#### Findings

##### Data Quality Sound

- Every pentagon stat the PDF renders maps to a single `PentagonStats` field on `Build.career.stats`. No re-derivation, no recomputation. By construction the on-screen pentagon and the PDF pentagon will agree.
- `compare_builds` already exposes `published_cost_4yr`, `modeled_total_debt`, `earnings_1yr_median`, and the full pentagon for every build (`builds.py:497-516`). The Comparison PDF can read directly from this dict; no new query path is needed.
- The boss raw_scores and thresholds on `BossFightResult` are already computed and stamped into the Build at gauntlet time (`boss_fights.py:1048-1057`), so the PDF reads them — does not recompute. This is the right contract.
- The `Build.cipcode` field carries the student's chosen CIP and is stable across substitution paths (`career.cipcode` may differ when `substitution_applied=True`). Same-major guard reading `Build.cipcode[:5]` is correct.
- `build_id` is a deterministic slug (`{school-major-NNN}`), persisted to DuckDB, NOT session-scoped. Safe to encode in a QR code as a stable identifier — assuming the rendering frontend has a route to handle it (see Concern #4).

##### Data Concerns

- **Concern #1 — Crosswalk confidence is invisible to the counselor.** The PDF renders `stats.res`, `stats.grw`, etc. without any indication of `Build.career.match_quality` or `Build.career.overall_confidence`. A `scorecard_only` or `partial_no_onet` build (per `LeaderboardMatchQuality`, `models/career.py:405-415`) shows the same pentagon as a `full` build. **Risk:** A student/counselor making decisions on partial-coverage data treats it as fully observed. **Fix:** Either (a) add a one-line caveat on page 1 ("Match quality: partial — O*NET data unavailable for this occupation") sourced from `Build.career.match_quality`, OR (b) document that the spec deliberately omits this and add it as a §1 Out of Scope item with reasoning. Severity: **Significant**. (Note: `feedback_no_substitution_caveat.md` says NOT to show "Limited data" warnings *from CIP substitution* on career cards. `match_quality` is a different signal — sourced from data coverage, not from substitution. The two are distinct.)

- **Concern #2 — "Break-even year" is not an existing field; the formula needs to be specified.** §3.5 ("Cost & ROI strip") and §3.6 ("Cost & ROI block") both call for a "Break-even year" cell, but no `CareerOutcome` field corresponds. The closest existing concept is `stat_roi` ("15-year payback multiplier") and `term_months` (loan amortization term). Neither is a break-even year. **Risk:** Implementor invents a derivation (e.g. `published_cost_4yr / earnings_1yr_median`) that does not match anything else in the app, producing a number on the PDF that contradicts the on-screen ROI receipt. This is exactly the "no numeric drift across surfaces" failure this review exists to prevent. **Fix:** Either (a) add an explicit formula to §4 — e.g. `break_even_year = ceil(modeled_total_debt / max(0.10 * earnings_1yr_median, 1))` for "10%-of-salary annual debt service" — and surface that same number on a future on-screen ROI receipt expansion, OR (b) replace the cell with one that uses an existing field (e.g. `total_interest_paid` or the `roi` stat). I recommend (b) as the safer hackathon-timeline call: rename the cell to "ROI score" or "Loan term (years)" and use a field that already lives on `CareerOutcome` and is already shown on `FinancesCard`. Severity: **Blocker** unless resolved. The PDF cannot ship a number that exists nowhere else in the app.

- **Concern #3 — `risk_level_for_boss` "High" threshold is unspecified in the spec.** The §4 docstring says "fp-data-reviewer to confirm the threshold during §5". This review confirms it (see the explicit threshold table above). **Fix:** Update the §4 docstring of `risk_level_for_boss` to remove the "worst quartile across the dataset" language and reference the deterministic per-boss threshold derived from `BOSS_SPECS` per the table above. The mapping function should compute thresholds from `BOSS_SPECS` at runtime, not hardcode integers. Severity: **Significant**. The spec must be updated before code lands.

- **Concern #4 — QR code points to a frontend route that does not exist.** `frontend/src/App.tsx:21-38` has no `/build/:build_id` route. The current build URL is `/my-build`, which is state-driven (the build comes from React state, not from a URL parameter). A QR code pointing at `{public_app_base_url}/build/{build_id}` will load the app but NOT the specific build — best case the user lands on `/set-your-course`, worst case on a 404. **Risk:** Counselor scans QR at the kitchen table, app loads but shows the wrong / no build. The "live build URL" promise on §3.5 page 2 is broken. **Fix:** Either (a) add a `/build/:build_id` route to `frontend/src/App.tsx` that calls a new `loadBuild(build_id)` action and routes to `BuildResultsScreen`, OR (b) point the QR at `{public_app_base_url}/builds?build_id={build_id}` and have `MenuScreen` or `BuildResultsScreen` honor the query param, OR (c) defer the QR to the same follow-up spec as the deferred items in Decision #9. I recommend (a). Severity: **Significant** — required for the QR feature to actually work.

##### Data Integrity Blockers

- **Concern #2 (Break-even year)** is the only blocker. Either the formula gets specified and verified against existing surfaces, or the cell gets replaced with one that uses an existing field. Shipping an undefined number is a hard line.

#### Disclaimer Check

- [x] AI-estimated values labeled — N/A for this spec (PDF doesn't render `task_breakdown_*` Gemma-scored fields directly; only consumes the rolled-up `bosses.ai` raw_score)
- [ ] Confidence scores propagated where crosswalk < Tier 2 — **NOT MET, see Concern #1**. `Build.career.match_quality` is not surfaced on the PDF; partial-coverage builds look identical to full-coverage builds.
- [x] Required disclaimer strings present in UI for this data path — the §1 success criteria include "data-sources line" and the glossary; §3.5 anchors the sources line via the `on_last_page` callback. Acceptable.
- [ ] Missing data states handled (not blank, not $0, not misleading) — **PARTIALLY MET**. The spec's risk-profile table handles `unknown` outcomes per `boss_fights.py` (the 4th `BossOutcome` value alongside win/lose/draw). The cost & ROI strip's behavior when `published_cost_4yr is None` or `earnings_1yr_median is None` is not specified — implementor must render `—`, never `$0`. Add an explicit testcase to §4: `test_cost_strip_renders_em_dash_when_published_cost_4yr_is_null`.

#### Verdict

- [ ] APPROVED
- [x] CHANGES REQUESTED (round 1 — see round 2 below for current status)
- [ ] REJECTED

**Required changes before implementation:**

1. **(Blocker)** Resolve "Break-even year" — either specify the formula explicitly in §4 with a source-field anchor and add it to `stat_engine` so the same number can appear on future on-screen surfaces, OR replace the cell with one that uses an existing `CareerOutcome` field (recommended). See Concern #2.
2. **(Significant)** Update §4's `risk_level_for_boss` docstring to use the deterministic per-boss threshold table above (computed from `BOSS_SPECS`), not "worst quartile of raw_score across the dataset". See Concern #3.
3. **(Significant)** Resolve the QR code URL — add a `/build/:build_id` route to `App.tsx` (recommended) or change the URL composition. The QR feature does not work as currently specified. See Concern #4.
4. **(Significant)** Resolve crosswalk-confidence visibility — either surface `Build.career.match_quality` as a one-line caveat on PDF page 1 for non-`full` builds, OR add an explicit Out-of-Scope item explaining why partial-coverage builds render identically. See Concern #1.
5. **(Minor)** Add a test for `published_cost_4yr is None` rendering `—` (never `$0`) in the cost strip. See Disclaimer Check.
6. **(Minor)** Confirm in §4 that `Build.cipcode[:5]` (NOT `Build.career.cipcode[:5]`) is the same-major guard input — the latter is the substitution-applied value and would mis-classify substituted builds.
7. **(Minor)** Add the leading-cell direction table from this review into §3.6 explicitly so the implementor doesn't infer it.
8. **(Minor)** Add the field-by-field source-of-truth table from this review into §4 as the contract that `pdf_export.generate_build_pdf` and `generate_comparison_pdf` must read from — verbatim, no recomputation.

Once these resolve, the data spine is sound and I will re-review for APPROVED.

---

#### Round 2 (re-review)
**Status:** APPROVED with one significant follow-up
**Reviewed:** 2026-05-06

Re-verifying each round-1 condition against the current spec.

##### 1. Break-even (Blocker) — RESOLVED

The 4th cost-strip cell is now "Debt-to-earnings (yr-1)" (§3.5 line 354 / §3.6 line 385) reading `Build.career.debt_to_earnings_annual` rendered as `f"{v * 100:.0f}%"`. Verifications:

- **Field exists on `CareerOutcome`.** Confirmed at `backend/app/models/career.py:91` (`debt_to_earnings_annual: float | None = None`).
- **Field is shown on `FinancesCard.tsx`.** Confirmed at `frontend/src/components/build-results/FinancesCard.tsx:193-196`. Note: on screen the field is rendered as a categorical color-coded label ("ROI: Strong / Solid / Caution / Risky") via `roiColorClass()` and `roiLabelKey()`. The raw % is NOT displayed on screen.
- **Drift question.** The PDF rendering raw % introduces a NEW display surface for the same field — but this is acceptable, not a violation. The PDF and screen pull from the same source field; only the abstraction differs (% vs categorical label). Both representations are derived from the identical `debt_to_earnings_annual` value, so a counselor reading the PDF "13%" alongside an on-screen "ROI: Solid" label sees consistent information at two granularities. No drift in the source-of-truth sense. Logged as **Follow-up A** (below) — not blocking.
- **Comparison PDF row.** §3.6 line 385 confirms the same 4 cells. Leading-direction: lower wins for debt-to-earnings, called out explicitly in §3.6 ("Debt-to-earnings — lower wins") and consistent with the §5 leading-direction table (debt-to-earnings is a debt-burden ratio; low = better, matching modeled-debt direction).
- **One stale row.** The §5 round-1 leading-direction table (line 1113) still lists "Break-even year — derived (see Concern #2) — earlier (lower) — lowest year value" because the round-1 review history is preserved. The implementor reading the table for direction guidance should trust §3.6 (which now correctly lists debt-to-earnings) and the round-2 §5 update below, not the round-1 row. Logged as **Follow-up B**.

**Verdict:** Concern #2 cleared.

##### 2. Threshold table (Significant) — RESOLVED with one residual

The §4 docstring at `pdf_copy.py:risk_level_for_boss` (lines 664-684) now correctly references the §5 deterministic per-boss table and explicitly rejects dataset-relative quartile cuts. Summary form is reproduced accurately: `>= win_at_or_above → Low`, `>= draw_at_or_above → Moderate`, `>= floor(draw_at_or_above / 2) → Elevated`, otherwise `High`.

**Residual disagreement on `raw_score is None` handling.** The new docstring (line 679) says: `raw_score is None → "High" (worst-case for missing data)`. The round-1 review explicitly ruled (lines 1081, 1089): `raw_score is None → render "Insufficient data" chip — do NOT default to High`. Defaulting unknown-data to "High" is exactly the "missing data is not zero" failure mode this reviewer flagged: a counselor sees a "High Risk" chip and assumes the data shows something bad, when it actually shows nothing at all.

**Severity:** Significant follow-up (Follow-up C). The §3.5 risk-table render layer can resolve this correctly even if the docstring is wrong — the §5 round-1 contract is unambiguous and supersedes the docstring summary. Must be fixed before code lands but does not block the spec's APPROVED status because the §5 contract governs.

##### 3. QR URL (Significant) — RESOLVED

QR code is fully cut. Verified by grep across the spec:

- §1 success criteria (line 151): "(No QR code per Decision #9 revision 2026-05-06.)" ✓
- §2 Decision #9 (line 178): rewrites the decision with the route-doesn't-exist reasoning ✓
- §2 Out of Scope (line 198): "QR code linking back to a live build (cut for hackathon...)" ✓
- §3.2 footer band (line 259): "(No QR code per Decision #9 revision 2026-05-06.)" ✓
- §3.5: no QR mention in Page 2 take-home ✓
- §3.8 (line 414): "QR code support was cut per Decision #9 revision 2026-05-06." ✓
- §3.9: no QR mention ✓
- §4 file table (line 484): "Add `reportlab>=4.2.0,<5.0.0`. (No QR dependency — Decision #9 revised 2026-05-06.)" ✓
- §4 file table (line 486): "(No `public_app_base_url` arg — QR cut.)" ✓
- §4 service signatures: no `public_app_base_url` parameter ✓
- §4 router: no QR rendering path ✓
- New tests list (lines 809-846): no QR-decode tests ✓

**Three residual stale references** (cosmetic — not affecting implementation correctness):

1. §3.1 line 232 — "are required for the sources/QR footer on the last page". Should say "sources footer".
2. §3.1 line 236 — "The sources line and QR code are drawn in the canvas callback". Should drop "and QR code".
3. §4 Test Data Requirements line 851 — "Mocked QR code library. Acceptable to assert on the URL string passed in...". Should be removed entirely; no QR test is in the test list.

Logged with Follow-up B.

**Verdict:** Concern #4 cleared. The implementor will not build a QR that doesn't work — the cuts are decisive everywhere it matters. The residual references are stale prose, not load-bearing instructions.

##### 4. match_quality caveat (Significant) — RESOLVED

The spec now adds:

- §3.5 conditional caveat block (lines 344-348): renders a one-line caveat below the profile + context strip when `build.career.match_quality != "full"`. Two copy templates documented (`scorecard_only` and `partial_no_onet`). Distinguished from the CIP-substitution caveat per `feedback_no_substitution_caveat.md` (line 348 explicitly addresses the cross-rule conflict — "match_quality is a data-coverage signal in the gold table, not a substitution signal").
- §4 `pdf_copy.py:data_coverage_caveat(build) -> str | None` (lines 709-721): docstring documents the three-way branch (`full → None`, `scorecard_only → caveat`, `partial_no_onet → caveat`) and the suppression-rule distinction.
- P0 test `test_data_coverage_caveat_returns_none_for_full_match_quality` (line 830): asserts the function returns None for `full` and the corresponding string for the other two values.
- P1 test `test_partial_match_quality_renders_caveat_line` (line 835): asserts the rendered PDF page-1 text contains the caveat for `scorecard_only` and does not for `full`.

This is the exact resolution path the round-1 review proposed (option a). The data-coverage signal is now visible on the PDF surface, sourced from `Build.career.match_quality` directly, and clearly differentiated from the suppressed substitution caveat.

**Verdict:** Concern #1 cleared.

##### Comparison PDF — debt-to-earnings exposure note

`backend/app/services/builds.py:compare_builds` (lines 497-516) currently exposes `published_cost_4yr`, `modeled_total_debt`, `earnings_1yr_median`, but NOT `debt_to_earnings_annual`. The Comparison PDF row (§3.6 line 385) needs the field. The implementor has two paths:

1. Read directly from each `Build.career.debt_to_earnings_annual` (the router loads each Build by id anyway). **Recommended** — keeps `compare_builds` unchanged.
2. Extend `compare_builds` to expose the field. Acceptable but adds a contract surface.

Either is fine. Path 1 is simpler. Logged as Follow-up D — implementor's call.

##### Round-2 follow-ups (none blocking APPROVED)

| ID | Severity | Description | Where |
|---|---|---|---|
| A | Minor | Note in §3.5 that the PDF's raw-% rendering is a new display abstraction for an existing field — same source, different granularity than the on-screen categorical label. Not drift; worth a one-liner so a reader doesn't think the PDF and screen are showing different numbers. | §3.5 |
| B | Minor | Clean up three stale QR references (§3.1 lines 232, 236; §4 line 851) and add a note on the round-1 leading-direction table row for "Break-even year" (§5 line 1113 — historical, preserve). | §3.1, §4, §5 |
| C | **Significant** | Fix `risk_level_for_boss` docstring at `pdf_copy.py` (line 679): change `raw_score is None → "High"` to `raw_score is None → "Insufficient data"` (5th visual chip). The implementor must not silently treat unknown as worst-case. The round-1 §5 contract above governs and supersedes the docstring summary. | §4 / `pdf_copy.py` |
| D | Minor | Pick path 1 (read `Build.career.debt_to_earnings_annual` directly in the comparison PDF) OR path 2 (extend `compare_builds`). Note the choice in §6 Implementation Log. | §3.6 / §4 |

##### Disclaimer Check (round 2)

- [x] AI-estimated values labeled — N/A (PDF doesn't render Gemma-scored fields directly).
- [x] Confidence scores propagated where crosswalk < Tier 2 — **NOW MET** via `data_coverage_caveat` and §3.5 conditional caveat. `scorecard_only` and `partial_no_onet` builds render the disclosure line.
- [x] Required disclaimer strings present in UI for this data path — sources line anchored via `on_last_page`. Glossary present. Acceptable.
- [ ] Missing data states handled — **PARTIALLY MET**. Cost strip null handling still not specified explicitly in §3.5 (round-1 minor #5 still open). Risk-profile `raw_score is None` is the round-2 Follow-up C disagreement.

##### Verdict (round 2)

- [x] APPROVED (with Follow-up C required before code lands)
- [ ] CHANGES REQUESTED
- [ ] REJECTED

The data spine is now correct end-to-end. Every number the PDF renders has a verified source field. The threshold table is deterministic. The crosswalk-confidence signal is honestly disclosed to the counselor. The QR-route hazard is removed.

Follow-up C is the only outstanding item with bite — a docstring contradiction on the unknown-data branch. Implementor must read it as "Insufficient data chip", not "High". The round-1 §5 ruling supersedes the round-2 docstring summary; this reviewer will verify the implementation matches the §5 contract during the §6 build accountability check, not block APPROVED on a docstring fix.

---

## §6 Implementation Log

**Status:** COMPLETE (2026-05-06)

### Files Modified
| File | Change Summary |
|------|---------------|
| `backend/pyproject.toml` | Added `reportlab>=4.2.0,<5.0.0` (no QR dep). |
| `backend/app/services/gemma_client.py` | Added `timeout_s` and `response_format` kwargs to `generate_chat` and `generate_chat_async` (G1). Added `log_synthetic_event(...)` helper for fallback-path JSONL emission (G3). Per-backend translation: Ollama → `payload["format"]`; OpenRouter → `response_format` kwarg (string `"json"` promoted to `{"type": "json_object"}`). |
| `backend/app/models/api.py` | Added `RiskLevel` literal (5 values incl. "Insufficient"), `ExportBuildPdfRequest`, `ExportComparisonPdfRequest`, `AudienceQuestion`, `AudienceQuestions`, `GemmaPath`. `RiskLevel` placed near `AskScopeKind` per architect M1. |
| `backend/app/services/pdf_copy.py` | NEW. Pure-Python copy generation: `verdict_line`, `risk_level_for_boss` (deterministic per-boss thresholds, `None → "Insufficient"`), `risk_one_liner` (5×5 anchor templates + level-only fallback when anchor missing), `where_each_pulls_ahead`, `data_coverage_caveat`. Two frozensets: `RPG_TERMS_FORBIDDEN_IN_PDF` (full PDF text) and `FORBIDDEN_IN_GEMMA_OUTPUT` (Gemma output, superset). Centralized `_BOSS_ADVISORY_LABEL` (C5). |
| `backend/app/services/pdf_questions.py` | NEW. Single Gemma JSON-mode call via extended `gemma_client.generate_chat_async(timeout_s=6.0, response_format="json")`. Static fallbacks per audience. Code-fence stripping (A3). Forbidden-term post-filter using `FORBIDDEN_IN_GEMMA_OUTPUT`. Every code path emits one `logs/gemma.jsonl` record (G3). |
| `backend/app/services/pdf_export.py` | NEW. ReportLab Platypus rendering with two `PageTemplate` objects (`main`/`last`) for the sources-citation footer. Lazy font registration with Helvetica fallback. Risk chip rendering (ALL-CAPS bands + italic Roman "Insufficient data"). Cost strip 4th cell uses `debt_to_earnings_annual` rendered as `f"{v*100:.0f}%"`. Conditional `data-coverage` caveat. No QR code. Comparison PDF leading-direction logic per data-reviewer table. |
| `backend/app/services/pdf_fonts/` | NEW. Bundled 4 TTFs: FredokaOne-Regular, Nunito-Regular, Nunito-Bold, SpaceMono-Regular (Google Fonts, OFL). |
| `backend/app/routers/pdf_export.py` | NEW. Two endpoints: `POST /build/{build_id}/pdf`, `POST /builds/compare/pdf`. Empty prefix per `builds_collection.router` precedent; tag `["PDF"]` capitalized (R1). 404 on missing build, 400 on cross-major, 500 on render failure (catches ReportLab exceptions and re-raises as `HTTPException` for CORS-correct errors per A3). |
| `backend/app/main.py` | Registered `pdf_export.router`. |
| `backend/ruff.toml` | Added `pdf_copy.py`, `pdf_questions.py`, `pdf_export.py` to E501 ignore (production prompt strings + risk-one-liner templates + glossary entries can't wrap). |
| `frontend/src/api/pdf.ts` | NEW. `exportBuildPdf`, `exportComparisonPdf`, `downloadBlobAs` helpers. |
| `frontend/src/components/build-results/ExportPdfButton.tsx` | NEW. Inline name input + button + error toast. Pre-fills from `build.profile_name` per Decision #8. |
| `frontend/src/screens/BuildResultsScreen.tsx` | Mounted `<ExportPdfButton>` in the top-right links row alongside Start Over / Adjust. |
| `frontend/src/components/menu/CompareView.tsx` | Added `exportComparisonPdf` button at top of result section with 3 disabled-tooltip guards (fewer than 2, more than 3, cross-major via `major_text` equality — backend hard-validates 4-digit CIP family). |
| `frontend/src/i18n/strings.ts` | Added 12 new keys (en + es + ar) for the export button labels, error messages, name field, and 3 disabled-tooltip variants. |
| `docs/reference/stat-display-surfaces.md` | Added Tier 4 / Skip entries 9a (My Build PDF) and 9b (Comparison PDF) per Decision #10. |
| `docs/reference/voice-guide.md` | Added "PDF / printed report" register-by-surface row noting the RPG-metaphor exception per Decision #4. |

### Deviations from Spec
- **Risk-one-liner anchors fall back to level-only when the named field is unavailable.** §3.11.2 names `ai_exposure_percentile`, `bls_growth_pct`, `onet_burnout_top_driver`, `earnings_75th_pct` — none exist on `CareerOutcome`. Implementation reads the closest existing fields (`adoption_percentile`, `growth_category` (categorical), first item from `burnout_drivers`, `earnings_1yr_p75`) and falls back to a level-only template when the anchor is None. The "no `None%` strings" rule is preserved; the spec's `test_risk_one_liner_handles_null_anchor` covers this path. The market boss anchor in particular is categorical-only (no numeric pct field is plumbed into `CareerOutcome` today), so the template formats `{label}` instead of `{v:+.0f}%`. Worth a follow-up spec to add a numeric BLS growth field.
- **Frontend cross-major guard uses `major_text` equality, not 4-digit CIP family.** `CompareBuild` doesn't carry `cipcode` today. The backend hard-validates the CIP family (returning 400 with helpful copy) so the frontend "guard" is best-effort UX; cross-major triples that pass the frontend check still bounce on the backend.
- **Sources citation copy** is intentionally generic ("Sources: BLS OOH · College Scorecard · O*NET · Karpathy AI Exposure · BEA RPP. Powered by Gemma 4.") — no per-build year stamps, since pipeline data versions aren't surfaced through to the renderer. Matches the spirit of the spec's "data-sources line" Success Criterion.

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | PASS | — | Backend imports clean on first compile; ruff flagged 42 E501s on production prompt strings + risk-one-liner table + glossary. Added per-file E501 ignores (pdf_copy.py, pdf_questions.py, pdf_export.py) per the ask_gemma.py precedent. Smoke test rendered 51 KB My Build PDF + 48 KB Comparison PDF — both under the 800 KB cap, both starting with `%PDF-1.4`. Backend pytest 1630 passed, no regressions. Frontend tsc clean. Vitest initially failed `every en key exists in es and ar` — added Spanish + Arabic translations for all 12 new keys; vitest then 826 passed. Vite production build clean (1.74s). |

---

## §7 Test Coverage

**Status:** COMPLETE (2026-05-06)

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|
| `backend/tests/services/test_pdf_copy.py` | `test_no_rpg_terms_in_rendered_text` | P0 — Renders a real PDF for `fixture_build`, extracts text via `pypdf`, asserts no term in `RPG_TERMS_FORBIDDEN_IN_PDF` matches with word-boundary regex. Decision #4's load-bearing enforcement test. |
| `backend/tests/services/test_pdf_copy.py` | `test_full_pdf_text_includes_stat_abbreviations` | Belt-and-suspenders — confirms ERN/ROI render in the chrome so a future patch that mistakenly adds them to RPG_TERMS_FORBIDDEN_IN_PDF gets caught here, not in the no-RPG-terms test. |
| `backend/tests/services/test_pdf_copy.py` | `test_risk_level_per_boss_thresholds_match_data_reviewer_table` (44 parametrized cases) | P0 — All 5 bosses × 4+ raw_score values per boss. Validates the deterministic threshold table from §5. |
| `backend/tests/services/test_pdf_copy.py` | `test_none_raw_score_returns_insufficient_not_high` (5 parametrized cases) | P0 — The missing-data-is-not-zero rule. `risk_level_for_boss(boss_id, None) == "Insufficient"` for every boss; explicitly NEVER `"High"`. |
| `backend/tests/services/test_pdf_copy.py` | `test_returns_none_for_full_match_quality` + 4 sibling tests | P0 — `data_coverage_caveat` returns None for `full`/None/unknown match_quality, and the right strings for `scorecard_only` / `partial_no_onet`. |
| `backend/tests/services/test_pdf_copy.py` | `test_*_falls_back` (5 anchors × Insufficient × with-anchor) | P0 — `risk_one_liner` with null anchor (`adoption_percentile`, `debt_to_earnings_annual`, `growth_category`, `burnout_drivers`, `earnings_1yr_p75`) falls back to the level-only template. Asserts no `"None%"`, no `"${None"`, no `"{p"`/`"{v"`/`"{label"`/`"{driver"` placeholder leakage. |
| `backend/tests/services/test_pdf_copy.py` | `test_verdict_line_within_200_chars` + 2 siblings | P2 — Verdict line ≤ 200 chars including with very long school + program names; verdict line never contains RPG terms. |
| `backend/tests/services/test_pdf_copy.py` | `test_gemma_forbidden_is_strict_superset_of_pdf_forbidden` + 1 sibling | Defense-in-depth — confirms the two-frozenset distinction (RPG_TERMS_FORBIDDEN_IN_PDF ⊂ FORBIDDEN_IN_GEMMA_OUTPUT, with stat abbreviations ONLY in the Gemma-output set). |
| `backend/tests/services/test_pdf_questions.py` | `test_static_fallback_when_gemma_times_out` | P0 — `asyncio.TimeoutError` from `gemma_client.generate_chat_async` → `gemma_path="fallback_timeout"` + 2 mandatory college Qs + ≥1 question per other audience + exactly one synthetic jsonl record. |
| `backend/tests/services/test_pdf_questions.py` | `test_static_fallback_when_gemma_returns_malformed_json` + `test_static_fallback_when_gemma_returns_wrong_schema` | P0 — Non-JSON / wrong-schema response → `fallback_malformed`. |
| `backend/tests/services/test_pdf_questions.py` | `test_static_fallback_when_gemma_returns_empty` | P0 — Empty string → `fallback_empty`. |
| `backend/tests/services/test_pdf_questions.py` | `test_two_static_college_questions_always_present` | P0 — Even on Gemma success, indices [0, 1] of `ask_the_college` are the static-mandatory pair (with `is_static_mandatory=True`); Gemma's contributions follow at index 2+. |
| `backend/tests/services/test_pdf_questions.py` | `test_audience_caps_enforced_4_per_audience_accepted` + `test_audience_caps_enforced_6_clips_or_falls_back` | P0 — Gemma returns 4 → accept; Gemma returns 6 → implementation clips at 5 (live path) per `_assemble`. |
| `backend/tests/services/test_pdf_questions.py` | `test_every_gemma_path_emits_one_jsonl_record` | P0 — Architect's G3 contract. All 5 GemmaPath values (live + 4 fallbacks) emit exactly one jsonl record. The `live` record is transport-level (real `_log_exchange` from `generate_chat`); each fallback emits a synthetic record via `log_synthetic_event`. |
| `backend/tests/services/test_pdf_questions.py` | `test_gemma_client_called_with_timeout_and_json_mode` | P0 — Architect's G1 contract. `pdf_questions` calls `generate_chat_async` with `timeout_s=6.0` and `response_format="json"` (or the OpenAI dict shape). |
| `backend/tests/services/test_pdf_questions.py` | `test_code_fence_wrapped_json_is_parsed` + `test_code_fence_without_json_marker_is_also_parsed` | P0 — Architect's A3. ` ```json\n{...}\n``` ` AND bare ` ```\n{...}\n``` ` both strip to valid JSON and land on `gemma_path="live"`. |
| `backend/tests/services/test_pdf_questions.py` | `test_forbidden_term_in_gemma_output_triggers_fallback` + `test_forbidden_stat_abbreviation_triggers_fallback` | P0 — Gemma output containing "boss" OR "ROI" triggers `fallback_malformed` via the `FORBIDDEN_IN_GEMMA_OUTPUT` post-filter. |
| `backend/tests/services/test_pdf_questions.py` | `test_voice_audience_first_for_college_and_parents_passes` + `test_voice_student_first_for_ask_yourself_passes` | P1 — Audience-first questions (no "Will I" / "Am I" prefix in college/parents) and student-first ("Will I" / "Am I" allowed in yourself) pass through. |
| `backend/tests/services/test_pdf_export.py` | `test_returns_valid_pdf_bytes` + `test_my_build_pdf_has_exactly_two_pages` + `test_pdf_renders_school_and_program_in_header` | P0 — `generate_build_pdf` returns non-empty bytes that start with `%PDF`, exactly 2 pages, school + program rendered in chrome. |
| `backend/tests/services/test_pdf_export.py` | `test_no_pii_written_to_disk` | P0 — Patches `builtins.open` for write modes, `Path.write_text`, `Path.write_bytes`. PDF generation completes with all of them raising AssertionError on call — i.e. the renderer materialized entirely in BytesIO. Includes a PII-shaped profile_name to make any leak obvious. |
| `backend/tests/services/test_pdf_export.py` | `test_rejects_cross_major` + `test_rejects_more_than_3_builds` + `test_rejects_one_or_zero_builds` | P0 — `generate_comparison_pdf` raises ValueError for cross-major (different 4-digit families), 4+ builds, and 0/1 build. |
| `backend/tests/services/test_pdf_export.py` | `test_accepts_2_builds_same_major` + `test_accepts_3_builds_same_major` + `test_accepts_4_digit_family_match_with_different_full_cips` | P0 — `generate_comparison_pdf` succeeds for 2 or 3 builds, including the load-bearing 14.1901/14.1902/14.1903 case (all 14.19* family). |
| `backend/tests/services/test_pdf_export.py` | `test_insufficient_chip_renders_for_null_raw_score_boss` | P0 — Build with one boss `raw_score=None` → page-1 risk profile renders "Insufficient data" italic chip and "Data unavailable for this program." in the Context column. |
| `backend/tests/services/test_pdf_export.py` | `test_my_build_pdf_byte_size_under_800kb` | P1 — Fully-populated build PDF stays under 800KB. |
| `backend/tests/services/test_pdf_export.py` | `test_renders_dte_as_percent` + `test_renders_em_dash_when_dte_is_none` | P1 — Cost strip 4th cell renders `debt_to_earnings_annual=0.12` as "12%"; renders "—" (em-dash) and never "None%" / "${None" when null. |
| `backend/tests/services/test_pdf_export.py` | `test_scorecard_only_renders_caveat` + `test_partial_no_onet_renders_caveat` + `test_full_match_quality_omits_caveat` | P1 — Page-1 caveat line conditionally renders for partial coverage; absent on full coverage. |
| `backend/tests/services/test_pdf_export.py` | `test_pentagon_vertices_render_numeric_labels` | P1 — Stat micro-table renders numeric `<value>/10` labels (e.g. "8/10", "7/10", "6/10"). |
| `backend/tests/routers/test_pdf_export.py` | `test_post_build_pdf_returns_application_pdf_content_type` + `test_post_build_pdf_includes_attachment_disposition` | P0 — Endpoint returns `Content-Type: application/pdf` and `Content-Disposition: attachment` with a slugged filename. |
| `backend/tests/routers/test_pdf_export.py` | `test_post_build_pdf_404_when_build_missing` | P0 — Unknown build_id → 404 with helpful copy. |
| `backend/tests/routers/test_pdf_export.py` | `test_post_build_pdf_500_when_reportlab_raises` | P0 — Architect A3. Patches `pdf_export.generate_build_pdf` to raise; router returns 500 via `HTTPException` so CORS headers attach correctly (no unhandled-exception bypass). |
| `backend/tests/routers/test_pdf_export.py` | `test_post_build_pdf_accepts_optional_student_name` + `test_post_build_pdf_rejects_overlong_student_name` | Pydantic boundary — empty body OK; 200+ char student_name → 422. |
| `backend/tests/routers/test_pdf_export.py` | `test_post_compare_pdf_returns_application_pdf_content_type` + `test_post_compare_pdf_400_when_cross_major` | P0 — Comparison PDF returns `application/pdf` for same-major triple; 400 with helpful copy when CIP families differ. |
| `backend/tests/routers/test_pdf_export.py` | `test_post_compare_pdf_validation_rejects_one_build` + `test_post_compare_pdf_validation_rejects_four_builds` | P0 — Pydantic 2..3 cap → 422 outside that range. |
| `backend/tests/routers/test_pdf_export.py` | `test_post_compare_pdf_404_when_first_build_missing` + `test_post_compare_pdf_404_when_one_id_missing` | 404 propagation from the build-resolver loop. |
| `backend/tests/routers/test_pdf_export.py` | `test_post_compare_pdf_accepts_2_or_3_same_major_builds` | P0 — 2 and 3-build same-major sets both render successfully end-to-end. |
| `frontend/src/components/build-results/ExportPdfButton.test.tsx` | `triggers exportBuildPdf and download on click` | P1 — Click button → `exportBuildPdf` called with build_id and `{studentName: null}`; `downloadBlobAs` called with the returned Blob and a slugged filename. |
| `frontend/src/components/build-results/ExportPdfButton.test.tsx` | `prefills the optional name input from defaultStudentName` | P1 — `defaultStudentName="Rowan"` → input value is "Rowan". |
| `frontend/src/components/build-results/ExportPdfButton.test.tsx` | `sends the typed student name to the API` + `sends null when the name input is empty/whitespace` | P1 — Typed name flows to API; whitespace-only normalized to null. |
| `frontend/src/components/build-results/ExportPdfButton.test.tsx` | `shows an inline error alert on API failure` | P1 — API rejects → `[data-testid=alert-pdf-export-error]` appears with `role=alert`. |
| `frontend/src/components/build-results/ExportPdfButton.test.tsx` | `disables the button while the export is loading` | Saboteur — pending request keeps the button disabled until resolution. |
| `frontend/src/components/menu/CompareView.test.tsx` | `disables the button when the 2 builds use different majors` | P1 — Cross-major triple → button disabled, tooltip mentions "major"/"CIP". |
| `frontend/src/components/menu/CompareView.test.tsx` | `disables the button when 4 builds are selected` | P1 — 4 selected → button disabled, tooltip mentions "3"/"deselect". |
| `frontend/src/components/menu/CompareView.test.tsx` | `enables the button for 3 same-major builds` | P1 — 3 builds with same major_text → button enabled. |
| `backend/tests/services/conftest.py` | (fixtures) | New fixture builders: `make_fixture_build`, `fixture_build`, `fixture_build_scorecard_only`, `fixture_build_partial_no_onet`, `fixture_build_null_ai_score`, `fixture_three_same_major_builds`. Per spec §4 Test Data Requirements. |

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest | 1744 | 0 | 0 | 1744 |
| vitest | 835 | 0 | 0 | 835 |

Net new tests vs the §6 implementation-log baselines (pytest 1630, vitest 826): **+114 backend, +9 frontend = 123 net new tests**.

### Edge Cases Covered

- Null `raw_score` for any of the 5 bosses → `"Insufficient"` (NOT "High"). Five parametrized cases.
- Null anchor data for every risk one-liner (5 anchor types) → level-only fallback; no `"None%"`, no `"${None"`, no template-placeholder leakage.
- Match-quality `None` and unknown values → no caveat rendered (defensive).
- Whitespace-only student_name → null on the wire.
- Code-fence-wrapped JSON (` ```json `) AND bare-fence (` ``` `) both parse via `_strip_code_fence`.
- Forbidden-term post-filter catches "boss" AND stat abbreviations (ERN/ROI/RES/GRW/AURA) — the latter explicitly NOT in `RPG_TERMS_FORBIDDEN_IN_PDF` because the chrome renders them.
- Loading state on the export button (button.disabled while pending).
- 4-digit CIP family match: `14.1901`, `14.1902`, `14.1903` all accepted as same major.
- 0, 1, and 4-build comparison PDF requests rejected at the right layer (Pydantic vs service vs router).
- ReportLab render failure → router 500 via `HTTPException` so CORS headers attach (NOT a bypass-middleware unhandled exception).
- All 5 GemmaPath code paths emit exactly one jsonl record (G3 observability contract — verified by independent tmp jsonl files per path).

### Confirmed Safe — Regression Check

The following tests from §4 "Confirmed Safe" all PASS unchanged:

- `backend/tests/services/test_boss_fights.py` — green (BOSS_SPECS thresholds power risk-level mapping; no drift).
- `backend/tests/services/test_stat_engine.py` — green (95 tests; pentagon math intact).
- `frontend/src/components/build-results/FinancesCard.test.tsx` — green (17 tests; cost source-of-truth shared with PDF).
- `frontend/src/components/CompareSchoolsPanel.test.tsx` — green.
- All pipeline tests under `tests/` — untouched (no pipeline changes in this spec).

### Gaps Identified

1. **Voice rules are partially testable.** The "audience-first vs student-first" rule lives in the Gemma system prompt, not in `pdf_questions.py` post-filter logic. We verify Gemma's output AFTER it lands, but the system prompt itself isn't unit-testable without a live model. Two tests (`test_voice_audience_first_for_college_and_parents_passes`, `test_voice_student_first_for_ask_yourself_passes`) confirm the parser tolerates correctly-voiced output; verifying Gemma actually emits correctly-voiced output is an integration concern requiring live inference.
2. **`test_post_build_pdf_500_when_reportlab_raises` does not check CORS headers directly.** FastAPI's `TestClient` does not run `CORSMiddleware` for non-Origin'd requests, so we verify the error format (HTTPException-wrapped, structured `detail`) instead of asserting `Access-Control-Allow-Origin` literally. The architectural intent of A3 — "errors flow through middleware" — is met by wrapping in HTTPException; full CORS verification belongs in an integration test against a deployed instance.
3. **`test_where_each_pulls_ahead_handles_ties` (P2) was not implemented.** The data-reviewer tie-breaker lives in `pdf_export._build_comparison`'s leader detection, which we exercise indirectly via `test_accepts_3_builds_same_major`; a dedicated tie-breaker test would need a fixture with hand-crafted tied stats and is left for follow-up.
4. **Pentagon vertex labels are extracted via `pypdf` text extraction**, which is an approximation — the visual placement (vertex offset, color) isn't asserted. Mechanical visual diffing belongs to `@fp-design-auditor` rather than `@test-writer`.

---

## §8 Reviews

**Status:** CHANGES REQUESTED (design audit APPROVED round 2; code review still flagged)

### Design Audit (@fp-design-auditor)
**Status:** APPROVED (round 2, 2026-05-06)
**Reviewed:** 2026-05-06

#### Audit Scope

Files audited:
- `backend/app/services/pdf_export.py`
- `backend/app/services/pdf_copy.py`
- `backend/app/services/pdf_fonts/` (font bundle)

Reference: `DESIGN.md` (Brightpath token spec) and `docs/specs/feature-pdf-report-exports.md` §3.4 / §3.5 / §3.11 (print design contract).

#### Checklist Results

**Item 1 — Stat hues print-tuned. PASS.**
`pdf_export.py` lines 143–147: `STAT_ERN = HexColor("#C8A820")`, `STAT_ROI = HexColor("#3DA86A")`, `STAT_RES = HexColor("#7B66C8")`, `STAT_GRW = HexColor("#3D8BB8")`, `STAT_AURA = HexColor("#C47090")`. Exact match to §3.4.

**Item 2 — Risk-level palette, 5 levels. PASS.**
`RISK_INK` dict lines 149–155: Low `#2D7A4F`, Moderate `#7A6A20`, Elevated `#B84C20`, High `#8B1A1A`, Insufficient `#5C5E70`. All 5 match §3.4 exactly.
`RISK_BG` dict lines 156–162: Low `#E8F5EE`, Moderate `#FFF8E0`, Elevated `#FFF0E8`, High `#FCEAEA`, Insufficient `#EFF0F4`. All 5 match §3.4 exactly.

**Item 3 — Risk chip rendering rules. PARTIAL FAIL — italic not rendering as italic.**
`_risk_chip_paragraph` (lines 448–470):
- "Insufficient" path at line 453: uses `fontName=_font("Nunito")` (roman weight — correct, NOT bold). Text is sentence-case "Insufficient data" (correct). Alignment is `TA_CENTER` (correct).
- "Low" path at line 461: uses `fontName=_font("Nunito")` (roman, NOT bold — correct). Text is `level.upper()` = "LOW" (ALL-CAPS — correct per B&W differentiator table).
- "Moderate" / "Elevated" / "High" path at line 462: uses `fontName=_font("NunitoBold")` (bold — correct). Text is `level.upper()` (ALL-CAPS — correct).
- **FAIL: The "Insufficient data" chip is specified as "italic Roman" in §3.4 and §3.5.** The implementation uses `_font("Nunito")` which resolves to `Nunito-Regular.ttf`. There is no `Nunito-Italic.ttf` in `backend/app/services/pdf_fonts/` — the directory contains only `FredokaOne-Regular.ttf`, `Nunito-Regular.ttf`, `Nunito-Bold.ttf`, `SpaceMono-Regular.ttf`. No italic TTF is registered, no `NunitoItalic` name exists in `_FONT_FILES`, and ReportLab does not synthesize italic from a roman TTF. The chip renders as plain roman, NOT italic. The italic slant that is the "orthogonal axis for meta-state" per §3 Design Vision Refinement item 4 is silently absent.

**Required fix:** Bundle `Nunito-Italic.ttf` (or `Nunito-LightItalic.ttf`) from the Google Fonts distribution, register it as `"NunitoItalic"` in `_FONT_FILES` and `_FONT_FALLBACK` (fallback: `"Helvetica-Oblique"`), and set the Insufficient chip to `fontName=_font("NunitoItalic")`. The spec is clear that italic is a load-bearing typographic differentiator for B&W photocopies.

**Item 4 — No dark-mode panel colors. PASS.**
Grep for every Brightpath dark-mode background hex (`#12131F`, `#1B1D30`, `#232545`, `#2D3060`, `#3A3D75`, `#0E0E14`, `#15151D`, `#1C1C26`, `#252532`, `#2D2D3D`, `#37374A`) returns zero matches in `pdf_export.py`.
`INK_PRIMARY = HexColor("#1A1B2E")` is used as ink (text color) and as solid fill only in the named locations: (a) canvas header band (line 357), (b) Career Risk Profile table column-header row in My Build (line 699), (c) Stats at a Glance column-header row in Comparison (line 1035), (d) Cost & ROI column-header row in Comparison (line 1101), (e) Career Risk Profile column-header row in Comparison (line 1148). These five usages are exactly the "top header band + column-header rows in tables" enumerated in §3.4 — no additional `INK_PRIMARY` panel fills, callout boxes, sidebars, or hero panels exist. Dark-fill usage cap is honored.
`HexColor("#5C5E70")` (Insufficient ink) is intentional per the risk palette.

**Item 5 — Headline font. PASS.**
`s["verdict"]` at line 222: `fontName=fred, fontSize=20, leading=26` — FredokaOne 20pt, correct.
Section headers (`s["section"]` at line 224, `s["section_compact"]` at line 226): FredokaOne 11pt and 9pt respectively — correct.

**Item 6 — Data-coverage caveat. PARTIAL FAIL — missing italic style, copy wording variance.**
Spacers: line 557 `Spacer(1, 6)` above, line 563 `Spacer(1, 9)` below. PASS — matches §3.11.5 asymmetric spacing exactly.
Conditionality: lines 555–565 render the caveat only when `data_coverage_caveat(build)` returns non-None, which in `pdf_copy.py` returns None for `match_quality == "full"` or None. PASS.
Font / color: `fontName=_font("Nunito"), fontSize=7.5, leading=10, textColor=INK_MUTED` (line 560–561). PARTIAL FAIL — spec §3.5 / §3.11.5 specifies "Nunito 7.5pt italic INK_MUTED". The implementation uses regular (roman) Nunito, not italic. This is the same root cause as Item 3: no italic font is bundled.
Copy wording: `pdf_copy.py` lines 426–433:
- `scorecard_only`: `"Note: occupational task data is partial for this program. Earnings, cost, and debt figures are full coverage."` — PASS, matches §3.11.5 exactly.
- `partial_no_onet`: `"Note: O*NET task detail is unavailable for this occupation. Earnings, cost, and debt figures are full coverage."` — PASS, matches §3.11.5 exactly.

**Required fix:** Same as Item 3 — bundle and register `NunitoItalic`, then set `fontName=_font("NunitoItalic")` on the caveat style (line 560).

**Item 7 — Cost strip alignment. PASS.**
`label_style` at line 625: `alignment=TA_CENTER`. `value_style` at line 629: `alignment=TA_CENTER`. Both rows of the cost strip are center-aligned. PASS.
4th cell label text is "Debt-to-earnings (yr-1)" (not "Break-even") — PASS, stale sample not followed.
4th cell value formatted via `_fmt_pct(build.career.debt_to_earnings_annual)` = `f"{v * 100:.0f}%"` — PASS.

**Item 8 — Comparison leading-direction. PASS.**
`_build_comparison` at lines 1062–1071:
- 4-year cost: `direction="low"` — PASS.
- Modeled debt: `direction="low"` — PASS.
- Year-1 earnings: `direction="high"` — PASS.
- Debt-to-earnings (yr-1): `direction="low"` — PASS.
All four match the §5 leading-direction table and §3.6.

**Item 9 — Pentagon vertex labels. PASS.**
Stat abbreviation labels at line 311–315: `fontName=_font("NunitoBold"), fontSize=label_font_size` (6.5pt default), `fillColor=STAT_COLORS[key]`. PASS — NunitoBold 6.5pt colored per stat.
Value labels at lines 317–322: `fontName=_font("SpaceMono"), fontSize=label_font_size - 1` (5.5pt), `fillColor=INK_SECONDARY`. PASS — SpaceMono 5.5pt in INK_SECONDARY.

**Item 10 — Glossary section. PARTIAL FAIL — 3 definition strings truncated, font size off.**

*Font size FAIL:* Spec §3.5 says `NunitoBold 8pt` terms, `Nunito 8pt` definitions. Implementation at lines 885–888 uses `fontSize=7.5` for both term and definition styles. Spec is `8pt`; implementation is `7.5pt`.

*Definition copy FAIL — 3 entries truncated:*
- **RES** (line 875): implementation `"AI Resilience — how much of this occupation's work is hard for AI to do."` — spec §3.11.3 requires `"AI Resilience — how much of this occupation's work is hard for AI to do, blended from task-level data."` The clause `", blended from task-level data"` is absent.
- **AURA** (line 877): implementation `"Brand Gravity — institutional pull (selectivity, completion, financial standing) shared by every program."` — spec §3.11.3 requires `"Brand Gravity — institutional pull (selectivity, completion, financial standing) shared by every program at the school."` The phrase `" at the school"` is absent.
- **Career risk** (line 878): implementation `"Five factors: AI displacement, debt burden, job market, burnout, and earnings ceiling."` — spec §3.11.3 requires `"Five factors that affect long-term outcomes: AI displacement, debt burden, job market, burnout, and earnings ceiling."` The phrase `" that affect long-term outcomes"` is absent.

**Required fixes:** Change `fontSize=7.5` to `fontSize=8` for both `term_style` and `def_style` (lines 885, 887). Restore the three truncated definition clauses to match §3.11.3 verbatim.

**Item 11 — Sources line, canvas callback only. PASS.**
`on_last_page` callback (lines 389–411) draws the sources citation at fixed y-coordinates (14pt and 7pt from page bottom) via `canvas.drawString`. The citation string `SOURCES_LINE` is a module-level constant (line 193). No story flowable carries the sources line. PASS.

**Item 12 — Two PageTemplate architecture. PASS.**
`_make_doc` at lines 492–494: `PageTemplate(id="main", ...)` and `PageTemplate(id="last", ...)` registered in that order. `generate_build_pdf` at line 1202: `story.append(NextPageTemplate("last"))` inserted before the `PageBreak()` (line 1203). `generate_comparison_pdf` at line 1231: `story = [NextPageTemplate("last")]` at the head of the story for a single-page document. PASS.

**Item 13 — PDF metadata. PASS.**
`_make_doc` at lines 479–488: `title=title, author="FutureProof", subject="Career outcome data for student planning", keywords="career, college, major, outcomes, earnings", lang="en-US"`. All five metadata fields from §1 Accessibility are present. PASS.

**Item 14 — PDF/UA tagging. NOTE.**
No PDF/UA structure tagging is present (tagged PDFs require ReportLab's experimental `platypus.tableofcontents` tagging API or a post-processor). Per §1 Accessibility: "PDF/UA tagging is NICE-TO-HAVE but not blocking — hackathon timeline." Deferred NICE-TO-HAVE. Not a blocker.

#### Additional Finding — Profile-strip separator rule violation

**FAIL at line 568:** The separator between the profile + context strip and the verdict line renders as `HRFlowable(width="100%", thickness=1.0, color=INK_PRIMARY)`. Spec §3.5 specifies: "Separated from verdict line by a full-width `HRFlowable` at 0.75pt `RULE_LIGHT`." Two errors:
- Thickness: 1.0pt implemented vs 0.75pt specified.
- Color: `INK_PRIMARY` (`#1A1B2E`, dark navy ink) implemented vs `RULE_LIGHT` (`#D9DAE4`, light grey rule) specified.

The dark thick rule renders as a significant visual divider (an additional INK_PRIMARY fill band) rather than the quiet separator the spec intends. On print, a 1pt dark navy rule between the profile strip and the verdict line is visually aggressive. This also contributes an additional INK_PRIMARY ink-heavy element, though `HRFlowable` is not a solid fill in the §3.4 dark-fill-cap sense.

**Required fix:** Change line 568 to `HRFlowable(width="100%", thickness=0.75, color=RULE_LIGHT, spaceAfter=8)`.

#### Summary of Required Changes

| # | Location | Issue | Severity |
|---|----------|-------|----------|
| A | `pdf_export.py` line 448–453 | Italic font not rendering for Insufficient chip — no italic TTF bundled | Blocking |
| B | `pdf_fonts/` directory | `Nunito-Italic.ttf` missing | Blocking (root cause of A and C) |
| C | `pdf_export.py` line 560 | Caveat paragraph not italic — same root cause as A | Blocking |
| D | `pdf_export.py` line 568 | Profile-strip separator: 1.0pt INK_PRIMARY → should be 0.75pt RULE_LIGHT | Required |
| E | `pdf_export.py` lines 885, 887 | Glossary font size: 7.5pt → should be 8pt per §3.5 | Required |
| F | `pdf_export.py` lines 875, 877, 878 | Glossary definitions truncated (RES, AURA, Career risk) vs §3.11.3 | Required |

Issues A/B/C are the same root cause: `Nunito-Italic.ttf` is not in the font bundle. Resolving B resolves A and C together.

#### Verdict

- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

**Conditions for APPROVED:** (1) Bundle `Nunito-Italic.ttf` and register `"NunitoItalic"` in `_FONT_FILES`/`_FONT_FALLBACK`; apply to Insufficient chip and caveat paragraph. (2) Fix profile-strip separator: `thickness=0.75, color=RULE_LIGHT`. (3) Fix glossary font sizes to 8pt. (4) Restore three truncated glossary definitions to §3.11.3 verbatim. Token-level color palette, stat hues, dark-fill cap, cost-strip alignment, pentagon vertex labels, sources callback, metadata, and page template architecture all pass mechanically.

#### Round 2 (re-review)
**Status:** APPROVED
**Reviewed:** 2026-05-06

Re-verification of the four round-1 required conditions against `backend/app/services/pdf_export.py` and `backend/app/services/pdf_copy.py` after the fixes-round-1 commit.

**Condition 1 — Italic font for Insufficient chip and caveat. PASS.**
`Nunito-Italic.ttf` is present in `backend/app/services/pdf_fonts/` (275 KB, confirmed via `ls`). `_FONT_FILES` at line 83 registers it as `"NunitoItalic"`; `_FONT_FALLBACK` at line 90 maps it to `"Helvetica-Oblique"`. `_risk_chip_paragraph` (line 478): the Insufficient branch now uses `fontName=_font("NunitoItalic")`. The caveat paragraph in `_build_page1` (line 590) uses `fontName=_font("NunitoItalic")`. Both italic sites resolved. The round-1 blocking condition is cleared.

**Condition 2 — Profile-strip separator. PASS.**
Line 598: `HRFlowable(width="100%", thickness=0.75, color=RULE_LIGHT, spaceAfter=8)`. Thickness is 0.75pt and color is `RULE_LIGHT` (`#D9DAE4`). Matches §3.5 exactly. Round-1 required condition cleared.

**Condition 3 — Glossary font sizes. PASS.**
Lines 919–922: `term_style` at `fontSize=8, leading=11`; `def_style` at `fontSize=8, leading=11`. Both are 8pt with 11pt leading. Matches §3.5 and §3.3 exactly. Comment at line 918 explicitly marks the fix. Round-1 required condition cleared.

**Condition 4 — Glossary copy verbatim from §3.11.3. PASS.**
Lines 908–910:
- RES: `"AI Resilience — how much of this occupation's work is hard for AI to do, blended from task-level data."` — clause restored.
- AURA: `"Brand Gravity — institutional pull (selectivity, completion, financial standing) shared by every program at the school."` — phrase restored.
- Career risk: `"Five factors that affect long-term outcomes: AI displacement, debt burden, job market, burnout, and earnings ceiling."` — phrase restored.
All three definitions match §3.11.3 verbatim. Round-1 required condition cleared.

**Bonus — Thread-safe font registration. PASS.**
`_FONTS_LOCK = __import__("threading").Lock()` at line 95. Double-checked lock pattern at lines 109–113: outer guard, inner guard under lock. Correct. No design-token impact; confirms implementation correctness for concurrent FastAPI thread-pool dispatch.

**Sanity pass on remaining round-1 PASSes.** No regressions introduced. Color tokens, stat hues, dark-fill cap, Cost & ROI alignment, pentagon vertex labels, sources callback, two-template architecture, and PDF metadata are unchanged from the round-1 PASS findings.

#### Verdict

- [x] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

All four round-1 required conditions are resolved. No new violations found in the fix commit. The Brightpath print design contract is mechanically satisfied.

### Code Review (@faang-staff-engineer)
**Status:** CHANGES REQUIRED
**Reviewed:** 2026-05-06

#### Summary

The implementation is structurally clean. The byte-stream-to-bytes contract is honored end-to-end (zero disk writes outside the bundled font reads — verified by full grep), `gemma_path` is contained inside the Pydantic model and never crosses an HTTP boundary or enters the rendered PDF, the timeout kwarg threads correctly through `generate_chat_async` → `_ollama_chat_sync` (`httpx.post(timeout=...)`) and OpenRouter (`completion_kwargs["timeout"]`), and the failure-to-static-fallback contract on `pdf_questions.generate_audience_questions` is correctly implemented across all 5 fallback paths with a `log_synthetic_event` per path. The router validation order (Pydantic 2..3 cap → 404 per missing build → 400 on cross-CIP-family) is sound, and HTTPException(500) wrapping flows through CORSMiddleware per `wrapped.py` precedent. Filename `_slug` is whitelist-regex-based and immune to path traversal, NUL injection, and shell metacharacters (verified with adversarial inputs).

That said, there is **one Serious bug** the 1620-test suite did not catch — Paragraph parses Gemma-generated and user-supplied free text as XML markup, and any `<` character or unbalanced tag in `student_name`, `rec.title`, `rec.stat_impact`, `rec.rationale`, or an audience-question string will raise `ValueError` mid-render and 500 the export. There is also a **Moderate** event-loop blocking issue and a **Minor** "leads on stat when all others are None" misleading-comparison edge in `where_each_pulls_ahead`.

Not ready for prod as-is — fix the Paragraph escape issue, then re-review.

#### Findings — by Review Area

##### 🔒 Security

**S1. ReportLab Paragraph parses Gemma + user input as XML markup. 🟠 Serious — render crash on `<`.**
**Impact:** Any `<` character in `student_name` (user-supplied via request body, capped at 80 chars), `rec.title` / `rec.stat_impact` / `rec.rationale` (Gemma-generated free text), or any audience-question string (`q.text`) will trigger ReportLab's mini-XML parser. Bare `<` raises `ValueError("paragraph text ... unclosed tags")`. The render aborts mid-build, the `try/except Exception` in `routers/pdf_export.py:100` re-raises as HTTPException(500), and the user gets "PDF generation failed" instead of their report. This is a 3am page waiting to happen the first time Gemma writes a rationale like "Use <Python or JavaScript" or a student types `<3 design`.
**Verified:**
- `pdf_export.py` lines 526, 790, 797, 858 — all `Paragraph(text, style)` calls with no escaping.
- `python3 -c "Paragraph('half-open <para').wrap(...)"` → `ValueError: paraparser: syntax error: parse ended with 1 unclosed tags`.
- `python3 -c "Paragraph('<i>x</i> <b>')` → `ValueError: saw </para> instead of expected </b>`.
- Bare `&` is permissive (Texas A&M renders fine) — confirmed with adversarial inputs. The bug is `<`, not `&`.
- No test in `test_pdf_export.py` or `test_pdf_questions.py` feeds `<` through any of these surfaces. Test fixtures are clean ASCII.
- `FORBIDDEN_IN_GEMMA_OUTPUT` does not include `<` (and shouldn't — that's a markup-escape concern, not a vocabulary concern).
**Fix:** Escape user/LLM-controlled text before passing to Paragraph. Add `from xml.sax.saxutils import escape` at top of `pdf_export.py`, define a small helper `_p(text, style)` that calls `Paragraph(escape(text), style)`, and replace the user/LLM-controlled call sites:
- `pdf_export.py:526` — `_p(name_label, ...)` (student_name source).
- `pdf_export.py:550` — Residency line interpolates `build.home_state`. Safe (2-letter), but pass through the helper for consistency.
- `pdf_export.py:790` — `_p(f"• {rec.title}", title_style)`.
- `pdf_export.py:797` — `_p(rec.stat_impact, rationale_style)`.
- `pdf_export.py:838` — `_p(f'Ask: "{rec.rationale}"', ask_style)`.
- `pdf_export.py:858` — `_p(f"• {q.text}", q_style)` (audience-question text).
- `pdf_export.py:970, 1001, 1074, 1128` — school_name in comparison (institution names with `&` already render OK; escape is defense-in-depth).
- `pdf_export.py:572` — `verdict_line(build)` interpolates school_name + program_name. Server-side data, low-risk, but escape for consistency.
- `_build_filename` is unaffected (uses `_slug`, which whitelists `[a-z0-9-]`).
**Add a regression test:** feed `student_name='<malformed`, `skill_recs=[SkillRec(title="Python <or> Java", stat_impact="...", rationale="...")]`, and an audience-question `q.text="Will I see graduates earning <$50k starting?"`. Assert the render returns valid bytes (not raises).

**S2. Build ownership / authentication — N/A in this codebase. 🔵 Minor — document the trust boundary.**
**Impact:** Spec §4 calls out "request validation (build_ids ownership)" but the implementation has no auth check — any caller who knows or guesses a `build_id` can render that build's PDF. Per project architecture (`feedback_profile_is_build.md`: "Profile name + animal are build identity, not user identity; no 'logged in' concept"), this is by design — there are no authenticated users. The real defense is `build_id` unguessability (the IDs are server-issued tokens). Acceptable.
**Recommendation:** No code change. Add a one-line comment in `_load_build_or_404` noting the no-auth-by-design trust model so future contributors don't introduce a regression assuming auth exists.

**S3. PDF metadata + JS injection. ✅ Clean.**
**Verified:**
- `pdfmetrics.registerFont` only reads files under `backend/app/services/pdf_fonts/`; no PII goes to disk via fonts.
- `_make_doc` sets `title=`, `author=`, `subject=`, `keywords=`, `lang=` only — no `/AA` / `/OpenAction` / `/JavaScript` keys exist in the Platypus build path.
- ReportLab escapes PDF string literals via its own internal `pdfdoc` writer (`(...)` delimiters with `\(`/`\)` escapes); embedded JS would require explicit `Action` objects which are not used.

**S4. PII to disk. ✅ Clean.**
**Verified:** `grep -nE "open\(|write_text|write_bytes|tempfile|mkstemp|NamedTemporaryFile"` across `services/pdf_export.py`, `services/pdf_questions.py`, `routers/pdf_export.py` returns zero matches. The only `path.exists()`/`registerFont` reads are bundled TTFs. PII (`student_name`, etc.) lives in a `BytesIO` for the request lifetime and is GC'd. Confirmed.

**S5. Filename / Content-Disposition injection. ✅ Clean.**
**Verified:** `_FILENAME_SAFE = re.compile(r"[^a-z0-9]+")` collapses everything non-alphanumeric to `-`. Adversarial inputs `'../../../etc/passwd'`, `'school"; del /'`, `'\x00null'`, `'../', '...'` all produce safe slugs (verified). No `"`, `\r`, `\n`, `/`, `\` can survive into the `Content-Disposition` header.

##### 🔥 Performance

**P1. Sync ReportLab render blocks the event loop. 🟡 Moderate — `asyncio.to_thread` should wrap.**
**Impact:** `pdf_export.generate_build_pdf(...)` and `generate_comparison_pdf(...)` are CPU-bound (Platypus layout + font rasterization). Both are called synchronously inside `async def` route handlers (`routers/pdf_export.py:95` and `:144`). For the duration of the render (typically 50–200 ms; longer for large skill_recs lists), no other coroutine on this event loop can make progress — including health checks, in-flight chat streams, and queued requests waiting to be dispatched. At 10 concurrent /pdf requests during the demo, the event loop sees up to 2 seconds of stop-the-world latency. Not a memory problem (each render peaks ~100 KB), but a tail-latency problem.
**Fix:** Wrap both render calls in `asyncio.to_thread(...)`. The reason this wasn't already there: `wrapped.py` doesn't need it because Playwright is itself async; ReportLab is not. Concrete change in `routers/pdf_export.py`:
```python
# instead of:
pdf_bytes = pdf_export.generate_build_pdf(build, student_name=..., audience_questions=...)
# do:
pdf_bytes = await asyncio.to_thread(
    pdf_export.generate_build_pdf,
    build,
    student_name=body.student_name,
    audience_questions=audience_questions,
)
```
Same for `generate_comparison_pdf`. The semaphore in `gemma_client` already bounds Gemma concurrency upstream; no PDF-render semaphore is needed at this scale.

**P2. `generate_chat_async(timeout_s=6.0)` short-circuit chain. ✅ Verified working end-to-end.**
**Verified:**
- `pdf_questions.py:367–378` calls `generate_chat_async(..., timeout_s=6.0)` inside an outer `asyncio.wait_for(timeout=7.0)` belt-and-suspenders.
- `gemma_client.generate_chat_async` (line 545) → `asyncio.to_thread(generate_chat, ..., timeout_s=...)`.
- `generate_chat` (line 401) on Ollama → `_ollama_chat_sync(..., timeout_s=6.0)` → `httpx.post(url, json=payload, timeout=6.0)` (line 202). The `httpx` global timeout covers connect/read/write/pool. Confirmed.
- OpenRouter path (line 456): `completion_kwargs["timeout"] = 6.0`. The OpenAI Python SDK accepts per-call `timeout`. Confirmed.
- Caveat: the outer `asyncio.wait_for(timeout=7.0)` cannot interrupt the blocking `httpx.post` running inside `asyncio.to_thread` — the worker thread keeps the semaphore slot until httpx itself unblocks. In practice the 6 s httpx timeout is the load-bearing bound; the 7 s wait_for is a no-op safety belt unless the worker thread is starved. Acceptable.

**P3. Comparison `next(...)` lookups O(N×5). ✅ Trivial; no concern.**
3 builds × 5 bosses = 75 dict-walks per render. Under the deterministic gauntlet, `build.gauntlet.fights` is bounded at 5 entries. Constant-time at any practical scale.

**P4. Module-level font cache thread safety. ✅ Acceptable.**
`_FONTS_REGISTERED`/`_FONT_NAMES` are mutated without a lock. In single-process FastAPI, async handlers don't preempt each other across non-`await` boundaries, so two concurrent first-calls cannot interleave today. **If P1 is implemented (`asyncio.to_thread`)**, then two thread-pool workers could race here. Empirically verified: `pdfmetrics.registerFont(TTFont(...))` is idempotent (double-registering the same font is a no-op, no exception). The dict assignment is atomic under the GIL. Worst case is wasted work, not corruption.
**Recommendation:** When wrapping renders in `asyncio.to_thread` (P1 fix), pre-register fonts at app startup (e.g., in `main.py` lifespan handler) by calling `pdf_export._register_fonts()` once. Removes the lazy-init race window entirely and shaves first-render latency.

**P5. Unbounded /pdf concurrency. 🔵 Minor — defer.**
The endpoints have no semaphore. Each render peaks ~100 KB; 1000 concurrent renders ~100 MB. Not a near-term OOM, but at hackathon-demo scale (single laptop) a flood could degrade. Defer until a real load test surfaces a problem; the project doesn't need a render semaphore today.

##### 🧨 Error Handling

**E1. `pdf_questions.generate_audience_questions` swallows all `Exception`. ✅ Justified.**
**Verified:** Lines 386–396. The bare `except Exception` is contractually correct — the spec defines "static fallback IS the retry policy." Every code path returns a non-empty `AudienceQuestions` and emits exactly one synthetic JSONL record. Confirmed by reading all 5 fallback branches (timeout, disabled, empty, malformed, live). No exception type that should escalate is being silently swallowed (transport errors are exactly what we want to fall back on).

**E2. Router `except Exception → HTTPException(500)`. ✅ Justified by `wrapped.py:92-103` precedent.**
**Verified:** `routers/pdf_export.py:100` and `:149`. The CORSMiddleware-routing reason is documented in the docstring. The 500 detail string includes only `type(exc).__name__` (no exception message, no stack trace) — does not leak internal paths or PII. Good.

**E3. `_load_build_or_404` only catches `FileNotFoundError`. 🔵 Minor — consistent with `wrapped.py`, but worth a note.**
**Impact:** `state.get_build` already does the disk fallback internally (and catches FileNotFoundError → returns None). When that returns None, `_load_build_or_404` then calls `builds_service.load_build(build_id)` a second time, re-doing the same DuckDB lookup it just performed. Two failure modes are NOT mapped to 404:
- `duckdb.IOException` (DB locked, disk error) → 500 leaks past `_load_build_or_404` because the call is BEFORE the `try/except` in the route handler.
- `pydantic.ValidationError` from `Build.model_validate_json` (corrupted row) → same. 500 without going through CORSMiddleware (the protected `try` is later in the function).

This is not introduced by this PR — `wrapped.py:48-58` has the identical pattern. Inherited tech debt.
**Fix (defer to a separate spec):** Hoist the `_load_build_or_404` call into the route's `try/except` block, OR replace with a single `state.get_build` call (which already does fallback) and check the None return. Don't fix in this PR; the existing precedent is the rule.

**E4. `_register_fonts` per-font `except Exception → fallback to Helvetica`. ✅ Acceptable.**
A corrupt TTF on disk shouldn't crash the demo. The WARNING log gives ops a signal. The only concern is "did a deployment misconfiguration silently degrade us?" — and the WARNING addresses exactly that. A real ops alert pipeline filtering on `"pdf_export: font registration failed"` would close the loop, but that's a runbook concern, not a code concern.

##### 🎪 Concurrency

**C1. `gemma_client._semaphore` covers Gemma calls. ✅ Confirmed.**
The semaphore in `_get_semaphore()` is acquired by `generate_chat_async` (line 558). PDF rendering itself is unbounded, addressed by P1/P5 above.

**C2. `_register_fonts` race. ✅ Empirically safe.**
See P4 above.

##### 🎭 Architectural

**A1. `_BOSS_ADVISORY_LABEL` centralization (genai-architect C5). ✅ Confirmed.**
`pdf_copy.py:57-70` defines the dict + `boss_advisory_label()`. Imports:
- `pdf_export.py:62`: `from app.services.pdf_copy import (..., boss_advisory_label, ...)`.
- `pdf_questions.py:32`: `from app.services.pdf_copy import (..., boss_advisory_label, ...)`.

Both consumers import from the same source. No drift possible. Verified.

**A2. `_top_two_risks` / `_top_two_strengths` near-duplicates. ✅ Acceptable.**
`pdf_questions.py:135-153` and `:156-169`. Severity-map inversion is the only difference; the gauntlet-walk loop is identical. Could be DRYed by parameterizing severity, but at 19 lines the duplication is readable. Defer.

**A3. `risk_level_for_boss` (level computation) vs `_risk_chip_paragraph` (rendering) separation. ✅ Clean.**
`pdf_copy.py:78-99` returns a `RiskLevel` (data). `pdf_export.py:448-470` consumes it for visual rendering (font/color). No visual decisions in `pdf_copy`; no level decisions in `pdf_export`. Verified.

**A4. `where_each_pulls_ahead` walrus + tie semantics. 🟡 Moderate — incorrect "lead" claim when all-others-None.**
**Impact:** `pdf_copy.py:368-372`:
```python
if all(
    (other_v := _stat_value(o, key)) is None or my > other_v
    for o in others
):
    leaders.append(label)
```
Tie semantics are correct (`my > other_v` strictly excludes equal values, so ties don't lead — confirmed with the data-reviewer leading-direction table). But the `is None or my > other_v` short-circuit means: if I have `ERN=5` and the other 2 schools both have `ERN=None`, my build is declared a leader on Earnings (vacuously). The user reads "IU — leads on Earnings" when really nobody else had Earnings data to compare against.
**Fix:** Require at least one comparable peer.
```python
others_with_data = [o for o in others if _stat_value(o, key) is not None]
if not others_with_data:
    continue  # nothing to compare against — don't claim a lead
if all(my > _stat_value(o, key) for o in others_with_data):
    leaders.append(label)
```
Same pattern for the cost_dirs loop (lines 380-394). Add a unit test in `test_pdf_copy.py`: 3-build case where 1 build has all stats and 2 have None, assert `where_each_pulls_ahead` does NOT claim leadership for the all-None comparison.

**A5. `_parse_response` returns `None` on any failure; caller distinguishes empty-vs-malformed. ✅ Confirmed.**
`pdf_questions.py:261-295` returns None for parse fail / wrong shape / forbidden term / over-length. Caller (`generate_audience_questions:398-412`) distinguishes `if not raw → fallback_empty` from `parsed is None → fallback_malformed`. Adequate. Note: a Gemma response that's `"   "` (whitespace) would be `bool("   ") == True`, then `_parse_response` would `return None` after `_strip_code_fence` produces `""` → `json.loads("") raises JSONDecodeError → return None` → fallback_malformed. Slightly miscategorized (should be `fallback_empty`), but the user-visible behavior is identical (static questions render). Defer.

**A6. `log_synthetic_event` signature parity with `_log_exchange`. ✅ Confirmed.**
- Same `extra` merge order: `record = {**extra, **record}` — caller-provided fields are overridden by standard fields on collision. Match.
- `synthetic: True` marker is unique to the new helper, so consumers can `record["synthetic"] is True`-filter to pull only the no-transport events. Good.
- `GEMMA_LOG_DISABLED` is honored via the shared `_log_exchange` (line 274). No test gap.

**A7. Router prefix + tag. ✅ Confirmed.**
`routers/pdf_export.py:37`: `router = APIRouter(prefix="", tags=["PDF"])`. `main.py:127`: `application.include_router(pdf_export.router)`. Endpoints are `/build/{build_id}/pdf` and `/builds/compare/pdf` — match spec §4.

**A8. `Cache-Control: no-store` vs `wrapped.py`'s `public, max-age=3600`. ✅ Defensible difference.**
PDFs contain student_name + school + major details — `no-store` is correct. wrapped.py is celebratory share content; cacheable. Different intents, different headers. Confirmed.

##### 📉 Maintainability

**M1. Sources line splitter is fragile. 🔵 Minor.**
`pdf_export.py:395-407`: the `if len(src) > 90: ... rfind("  ", 0, mid+20) ... fallback to mid` chain is opaque. `SOURCES_LINE` today is 100+ chars, so the splitter runs. The `"  "` (double-space) anchor depends on the literal having `· ` separators with double-space padding; if someone edits SOURCES_LINE without the anchor, the splitter falls through to mid-of-string and breaks a word. Not a bug today; would be a 3am page if the literal changes.
**Recommendation:** Use a width-aware text wrap (e.g., `reportlab.lib.utils.simpleSplit(SOURCES_LINE, _font("Nunito"), 6, available_width)`) — replace the manual split. Defer; tests cover the current literal.

**M2. `_classify_skill_bucket` keyword-string fallthrough. 🔵 Minor.**
`pdf_export.py:731-737` falls back to "Career-Launch" on no match. Means a Gemma `stat_impact` like "improves AURA across all builds" lands in Career-Launch by default. Not wrong, but the bucket assignment is best-effort. Acceptable.

#### Required Changes (Routing)

These must be addressed before APPROVED. Routes back to **Implementation** (general Claude Code) via §10.

| # | Finding | Severity | File:line | Owner |
|---|---|---|---|---|
| 1 | Escape user/LLM text before `Paragraph(...)` | 🟠 Serious | `pdf_export.py` lines 526, 790, 797, 838, 858 (+ defense-in-depth at 550, 572, 970, 1001, 1074, 1128) | Implementation |
| 2 | Wrap render in `asyncio.to_thread` | 🟡 Moderate | `routers/pdf_export.py:95, :144` | Implementation |
| 3 | Fix all-None lead claim | 🟡 Moderate | `pdf_copy.py:368-372, :388-394` | Implementation |
| 4 | Add regression test for `<` in `student_name` / `rec.*` / `q.text` | 🟠 (gates #1) | `tests/services/test_pdf_export.py` (new test) | Test-writer |
| 5 | Add unit test for `where_each_pulls_ahead` all-None branch | 🟡 (gates #3) | `tests/services/test_pdf_copy.py` (new test) | Test-writer |

#### What's Good

- Byte-stream contract honored end-to-end. Zero disk writes. Verified by exhaustive grep.
- `gemma_path` containment is clean — Pydantic-only field, never serialized to HTTP, never rendered to PDF.
- Forbidden-vocab regex hits both Pydantic-validated content AND post-strip JSON, with `_BOSS_ADVISORY_LABEL` centralized so the two consumers can't drift.
- Timeout kwarg threading is correct on both backends. Verified line-by-line.
- 5-fallback-path discipline with `log_synthetic_event` per path is the right shape for observability without sneaking PII into logs.
- Filename slug is whitelist-regex (defense-in-depth: even if upstream validation is bypassed, no path traversal is possible).
- Pydantic enforces 2..3 builds at the boundary; the same-major guard runs after build resolution. Validation order is correct (cheap checks first, expensive last).
- HTTPException(500) wrapping correctly preserves CORS routing. The 500 detail leaks only `type(exc).__name__` — no message, no stack.
- Boss-advisory label translation is the right architectural separation.

#### Verdict (Round 1)
- [ ] APPROVED
- [x] CHANGES REQUIRED
- [ ] BLOCKER

**Why CHANGES REQUIRED (not BLOCKER):** Finding S1 is reproducible production crash territory the moment Gemma writes a `<` character in a skill rationale (and Gemma WILL eventually write a `<`), but the fallback path is graceful (HTTPException(500)) and no data corruption results — the user just can't get their PDF. Two-line fix (xml escape helper + 6 call-site swaps) plus one new test. P1 and A4 are quality-of-implementation issues, not blockers. Implementation can resolve in a single round; route back via §10.

---

#### Round 2 (re-review)
**Status:** APPROVED (with one frontend-constrained Minor follow-up noted)
**Reviewed:** 2026-05-06

##### Re-verification of Round 1 findings

**S1 — Paragraph XML-escape. ✅ Resolved.**
- `_safe(text)` helper added at `pdf_export.py:144-155` using `xml.sax.saxutils.escape`. Correct primitive (handles `<`, `>`, `&`).
- Call-site coverage verified by grepping every `Paragraph(` invocation (53 total) and every interpolation of user/LLM-derived fields. All required sites wrapped: `name_label` (550), `school_name` + `major` (560), `verdict_line` output (602), `rec.title` (820), `rec.stat_impact` (827), `rec.rationale` (868), `q.text` (888), risk `context` (718), `_short_school(b.school_name)` (982, 1006, 1038, 1111, 1165), comparison `major` (974), `caveat` (589). Glossary copy intentionally not wrapped (fixed in-source copy, not user-controlled) — confirmed correct.
- Defense verified: PDF `BaseDocTemplate(title=...)` and `canvas.drawString(title)` paths (1233, 1265) do not XML-parse, so unwrapped use there is safe.
- 4 new P0 tests in `TestXmlEscapeUserControlledStrings` exercise student_name, skill rationale, audience-question text, and comparison school_name with adversarial `<` content. All pass; output is valid `%PDF` bytes.

**P1 — `asyncio.to_thread` wrapping. ✅ Resolved.**
- `routers/pdf_export.py:99-104` wraps `generate_build_pdf` in `await asyncio.to_thread(...)`.
- `routers/pdf_export.py:150-152` wraps `generate_comparison_pdf` likewise.
- `import asyncio` added at line 18. Both call sites pass kwargs through correctly. Event loop is no longer blocked by ReportLab layout.

**A4 — `where_each_pulls_ahead` all-None peers. ✅ Resolved.**
- `pdf_copy.py:_leading_factors_for` rewritten to filter `peer_real = [v for v in peer_values if v is not None]` and `continue` when empty, applied identically to both the stats loop (366-375) and the cost loop (383-397). The walrus chain that produced the vacuous-leadership bug is gone.
- 2 new P0 tests in `TestWhereEachPullsAheadAllNonePeers` cover both the all-None case (no leadership claimed; "no clear leader" copy renders) and the at-least-one-peer-with-data case (leadership IS claimed). Both pass.

##### Sanity pass on related new code

**Bonus: thread-safe font registration. ✅ Correct.**
`_FONTS_LOCK` (line 95) + double-checked locking (lines 109-113) is the textbook pattern for lazy-init in a multi-threaded process. Now that P1 puts renders in the worker pool, this matters — without the lock, two concurrent first-call workers could both pass the `_FONTS_REGISTERED` check and double-register fonts. ReportLab's `pdfmetrics.registerFont` is empirically idempotent, but defending the invariant explicitly is the right call. Acquire-once-and-recheck pattern is correct. (Stylistic-only nit unrelated to correctness: `__import__("threading").Lock()` works but is unusual; a top-level `import threading` would be cleaner. Skipping — outside review scope.)

##### One residual finding worth flagging

**S1-residual. `home_state` flows to Paragraph unwrapped. 🔵 Minor.**
`pdf_export.py:578` interpolates `build.home_state` into the residency Paragraph without `_safe`:
```python
story.append(Paragraph(f"Residency: in-state, {build.home_state}", s["muted"]))
```
`Build.home_state: str | None = None` (`models/career.py:331`) has no Pydantic validator constraining it to a 2-letter code. Today's frontend uses a US-state select-list dropdown, so an `<` cannot reach this field via the normal UI. But a direct API client (or a future LLM-derived path) could submit `home_state="<x"` and crash the export.

**Recommendation:** Wrap with `_safe(build.home_state)` for symmetry with the other user-controlled fields, OR add a Pydantic validator pinning `home_state` to `^[A-Z]{2}$`. Either is a one-line change. Not blocking — present-day code paths are safe — but worth closing before someone wires a different upstream into this field.

##### Verdict (Round 2)
- [x] APPROVED
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

All three round-1 conditions are met and tested. Backend pytest 1754/0/0; the 6 new P0 tests for the bug fixes pass on isolated runs. The bonus font-lock is a real correctness win for the new threaded path. Look — I love Claude, BUT — fine, this round was a clean turn. Ship it. The `home_state` Minor is a follow-up, not a gate.

---

## §9 Verification

**Status:** COMPLETE
**Verified:** 2026-05-06 23:38

### Backend
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff) | PASS (pre-existing only) | 1 pre-existing E501 in `test_ask_gemma_explain_receipt.py:3258` — identical to main, not this feature. 3 E501 errors in `test_pdf_copy.py` (this feature) fixed in Attempt #1. |
| Type check (mypy) | PASS (feature files clean) | 0 errors in `pdf_export.py`, `pdf_copy.py`, `pdf_questions.py`, `routers/pdf_export.py`. 62 pre-existing errors in 18 other files (same files, same counts as on main). reportlab mypy override added to `pyproject.toml` (`ignore_missing_imports = true`). |
| Tests (pytest) | PASS | 1754 passed, 0 failed |

### Frontend
| Check | Result | Details |
|-------|--------|---------|
| TypeScript | PASS | No errors |
| Tests (vitest) | PASS | 846 passed (72 files), 0 failed |
| Production build (Vite) | PASS | 887 modules, built in 1.65s |

### Pre-existing Issues (non-blocking)
- **ruff E501** `tests/services/test_ask_gemma_explain_receipt.py:3258` — line `"math_line": "MAX-MEAN blend of 3 signals → composite 0.72 → AURA score 8/10"` (90 chars). Committed in `53fb058 feat(aura-stat)`. No diff from main.
- **mypy** 62 errors in 18 pre-existing files (`builds.py`, `gemma_client.py`, `routers/builds.py`, etc.). Pre-date this feature branch; identical to main baseline.

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | All feature-file checks passed | 3 ruff E501 in `test_pdf_copy.py`; 38 mypy errors in `pdf_export.py`/`pdf_copy.py` (import-untyped for reportlab, missing type args, missing annotations, `row` redef, float/int misc) | Added `[[tool.mypy.overrides]]` for `reportlab.*` in `pyproject.toml`; fixed all in-code type annotations; renamed `row` → `risk_row` in comparison risk loop; imported `SkillRec`; split long dict literals in test file |

---

## §10 Discussion

```
[YYYY-MM-DD HH:MM] @source-agent → @target-agent
Message content.
```

---

```
[2026-05-06 14:22] @genai-architect → @fp-copywriter
Findings on the Gemma prompt + JSON schema in §4 ### Gemma System Prompt and JSON Schema.

STATUS: CHANGES REQUESTED — 4 required changes + 3 advisory notes.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AREA 1 — PROMPT CONSTRUCTION QUALITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CHANGE REQUIRED [C1] — "stat" in the forbidden vocabulary is too broad.

The forbidden-vocabulary list in the system prompt (line 1205) includes the
bare token `stat`. Gemma's vocabulary constraint is applied at the token
level, not with word-boundary awareness. The system prompt has no word-boundary
qualifier — it just enumerates tokens to avoid. That means Gemma may avoid
"statistical", "state", "statewide", and "statement" out of overcaution, or
it may miss the target (e.g., write "Stat score" thinking only "stat" in
isolation triggers the rule). The post-filter in `pdf_copy.py` IS
word-boundary-anchored (see the `RPG_TERMS_FORBIDDEN_IN_PDF` comment on
line 995-996: "the regex is word-boundary-anchored"), but the system-prompt
instruction is not. This discrepancy means the primary defense and the
backup defense have different scope for the same term.

More importantly: "stat" as a standalone word is a reasonable term to
forbid (no student question should say "your stat profile"). But the
forbidden list already includes the five specific stat abbreviations
(ERN, ROI, RES, GRW, AURA, HMN) — forbidding `stat` is a duplication that
adds ambiguity without adding coverage.

Required fix: Remove bare `stat` from the system prompt forbidden list.
The five named abbreviations already cover the specific in-app labels. The
word `stat` in a question like "statistical labor market trend" is not RPG
language and should not be suppressed. The post-filter handles the one
legitimate target (`\bstat\b` if needed) more precisely than a model-level
prohibition.

Change line 1205 from:
  "  boss, boss fight, gauntlet, fight, win, lose, draw, won, lost, "
  "  reroll, build, builds, level up, stat, ERN, ROI, RES, GRW, AURA, "
  "  HMN, Fight AI, Fight Student Loans, Fight the Market, Fight "
  "  Burnout, Fight the Ceiling, Fight the Future, WIN, DRAW, LOSE.\n"

To:
  "  boss, boss fight, gauntlet, fight, win, lose, draw, won, lost, "
  "  reroll, build, builds, level up, ERN, ROI, RES, GRW, AURA, HMN, "
  "  Fight AI, Fight Student Loans, Fight the Market, Fight Burnout, "
  "  Fight the Ceiling, Fight the Future, WIN, DRAW, LOSE.\n"

(Removed `stat` and collapsed the resulting whitespace.)


CHANGE REQUIRED [C2] — "level up" is in the system prompt but missing from
RPG_TERMS_FORBIDDEN_IN_PDF.

The system prompt forbids `"level up"` (line 1205). The post-filter
frozenset in `pdf_copy.py` (lines 986-993) does NOT include "level up" or
"leveled up" or "level-up". The belt-and-suspenders design only works if
both layers cover the same term set. If Gemma emits "level up" in a
question, the system prompt should suppress it, but if that suppression
fails the post-filter will not catch it.

Required fix: Add "level up", "leveled up", "level-up" to
`RPG_TERMS_FORBIDDEN_IN_PDF` in `backend/app/services/pdf_copy.py`.

Change lines 986-993 from:
  RPG_TERMS_FORBIDDEN_IN_PDF: frozenset[str] = frozenset({
      "boss", "bosses", "boss fight", "boss fights", "gauntlet",
      "fight ai", "fight student loans", "fight the market",
      "fight burnout", "fight the ceiling", "fight the future",
      "won", "lose", "lost", "draw",
      "win", "wins", "losses", "draws",
      "reroll", "rerolled", "build", "builds",
  })

To:
  RPG_TERMS_FORBIDDEN_IN_PDF: frozenset[str] = frozenset({
      "boss", "bosses", "boss fight", "boss fights", "gauntlet",
      "fight ai", "fight student loans", "fight the market",
      "fight burnout", "fight the ceiling", "fight the future",
      "won", "lose", "lost", "draw",
      "win", "wins", "losses", "draws",
      "reroll", "rerolled", "build", "builds",
      "level up", "leveled up", "level-up",
  })


CHANGE REQUIRED [C3] — ERN/ROI/RES/GRW/AURA/HMN are forbidden to Gemma but
absent from RPG_TERMS_FORBIDDEN_IN_PDF.

The system prompt forbids the stat abbreviations (ERN, ROI, RES, GRW, AURA,
HMN) because they are in-app UI labels that read opaque on a printed report.
This is the right call. However, the post-filter frozenset does not include
any of these abbreviations. If Gemma leaks one ("Does this program have a
high ROI?"), the post-filter will not catch it and the question reaches the
renderer.

These abbreviations are not word-boundary-ambiguous (they are all-caps
acronyms; false positives like "AURA" in a name are vanishingly unlikely in
this context). They belong in the post-filter.

Required fix: Add all six abbreviations to `RPG_TERMS_FORBIDDEN_IN_PDF`.
Add them in lowercase since the frozenset + case-insensitive regex match is
the pattern established by the existing entries.

Append to the frozenset:
      "ern", "roi", "res", "grw", "aura", "hmn",

Advisory: The word-boundary-anchored regex will correctly match "ROI" as a
standalone token and NOT match "heroic" (which contains "roi" but not at a
word boundary). No false-positive risk.


CHANGE REQUIRED [C4] — The JSON schema example in the system prompt uses
"..." placeholder values that are valid Python pseudocode but could be
ambiguous for Gemma in json-mode.

Lines 1219-1221:
  '{"ask_the_college": [\"...\", ...], '
  '"ask_your_parents": [\"...\", ...], '
  '"ask_yourself": [\"...\", ...]}\n'

The `"..."` inside the array is a Python/documentation convention for
"one or more strings go here." In JSON-mode, Gemma 4 generally interprets
this correctly, but `"..."` is also a valid JSON string value — meaning
Gemma could, in a cold or degraded state, literally emit the three-dot
string as a question. More importantly, the `...` after the first element
is not valid JSON at all, which means if Gemma parses this schema example
as a JSON template it sees structurally malformed JSON.

Swap to a minimal one-element concrete example. This is unambiguous, passes
JSON linting, and still conveys the schema shape:

Change lines 1219-1221 from:
  '{"ask_the_college": [\"...\", ...], '
  '"ask_your_parents": [\"...\", ...], '
  '"ask_yourself": [\"...\", ...]}\n'

To:
  '{"ask_the_college": ["Question for the college?"], '
  '"ask_your_parents": ["Question for the parents?"], '
  '"ask_yourself": ["Will I question for myself?"]}\n'

This also models the audience-voice rule by example: the `ask_yourself`
element starts with "Will I", providing implicit reinforcement.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AREA 2 — JSON SCHEMA DESIGN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Sound (after C4 above): The field names `ask_the_college`, `ask_your_parents`,
`ask_yourself` match the `AudienceQuestions` Pydantic model. The array-of-
strings shape is appropriate. No nested objects, no optional fields — clean.

The 0..3 no-filler license is the correct design choice. Requiring 1..3
creates filler pressure on a model that has nothing to add for a specific
audience. The static fallbacks (§3.11.4) guarantee floor-of-1 per audience
without forcing Gemma to produce filler. Approved as designed.

Advisory [A1]: The array bound (0..3) is conveyed only in prose
("zero to three questions per audience", line 1214). It is not embedded in
the schema example. This is acceptable — JSON does not have a native array-
length constraint syntax that would be meaningful here. The prose instruction
is sufficient for Gemma 4 27B. No change required, but the implementor
should note that if Gemma returns 4+ for an audience, `pdf_questions.py`
clips silently to 5 (the Pydantic cap). This is correct production behavior
(be liberal in what you accept). Test name `test_audience_caps_enforced`
should clarify in its docstring that the cap is 5 (the service max) not 3
(the Gemma ask) to avoid reader confusion.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AREA 3 — TOKEN BUDGET
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The system prompt is borderline on the ≤300-token target. A rough cl100k_base
count of `_SYSTEM` as written (lines 1173-1224) puts it at approximately
295-315 tokens — right at or slightly over the stated ceiling. The spec text
says "target ~250 tokens" but the actual string is longer. The forbidden-word
enumeration alone (~70-80 tokens) and the audience-voice rules block (~80-90
tokens) account for most of the budget.

After removing `stat` per C1 above, the count drops by ~1 token. After
applying C4 (shorter schema example), it drops by another ~5 tokens. Net
after both changes: approximately 289-305 tokens. Still borderline.

The implementor MUST measure with `tiktoken` cl100k_base (or the equivalent
Gemma tokenizer if available via the `sentencepiece` model) before shipping
and document the count in the module docstring of `pdf_questions.py`. If
over 300 tokens after applying C1+C4, the first candidate for trimming is
the second paragraph of the output-format section (lines 1222-1224: "If you
cannot write a question for an audience, return an empty array for that
audience. Do not write 'N/A', do not apologize, do not explain.") —
shorten to: "Return [] for any audience you cannot write for. No
explanation."  That saves ~15 tokens and loses no semantic content.

Build-context user message: ~80 tokens per the worked example (line 1261).
Well under the 200-token ceiling. No action required.

Advisory [A2]: Gemma uses SentencePiece tokenization, not cl100k_base.
For the same English prose, Gemma's token count is typically 5-12% higher
than cl100k_base. The spec correctly acknowledges this ("Gemma uses a
different tokenizer but the order of magnitude is what matters") but the
implementor should be aware the actual Gemma token count for `_SYSTEM` may
be 315-340 tokens. At Ollama throughput (~30-60 tok/s for 27B Q4), this
adds ~0.05s to prefill — well inside the <8s p50 budget and not worth
optimizing further unless latency tests show otherwise.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AREA 4 — FAILURE-MODE COVERAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

All 5 `gemma_path` values are reachable with the prompt as written:
- `live`: Gemma responds with valid JSON, schema matches, no forbidden terms,
  all strings ≤ 240 chars. Reachable.
- `fallback_timeout`: `timeout_s=6.0` → asyncio.TimeoutError. Reachable.
- `fallback_empty`: response is `""` or whitespace. Reachable (Gemma 4 can
  emit empty completions on aggressive token-length constraints). Reachable.
- `fallback_malformed`: non-JSON, wrong-schema JSON, or a string > 240 chars.
  Reachable. Also reachable via the forbidden-term filter.
- `fallback_disabled`: INFERENCE_BACKEND unset / backends unreachable.
  Reachable via environment configuration.

The defense-in-depth regex filter is appropriate, not overkill. The system
prompt provides the primary constraint; the post-filter provides non-
negotiable enforcement of Decision #4 for the rare case where Gemma (running
quantized at Q4 on Ollama, or in a degenerate generation) violates a
negative vocabulary constraint it was told to observe. The combination of
`response_format="json"` (guarantees JSON validity) + system-prompt
vocabulary list (primary behavioral constraint) + post-filter regex (hard
enforcement) is the correct three-layer architecture for a non-negotiable
output rule. Approved as designed.

Non-issue: The prompt does not give Gemma a mechanism to refuse. There is
no "if you cannot complete this task, say X" escape hatch. Good — refusals
would trigger `fallback_malformed` anyway, and an explicit refusal escape
hatch would create an additional failure surface. The "return [] for an
audience you cannot write for" instruction (lines 1222-1224) is the correct
substitute: it lets Gemma abstain gracefully without refusing the whole task.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AREA 5 — SCOPING AND PRIVACY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The `_user_prompt` function correctly scopes the build context to exactly
five fields. No `profile_name`, no `student_name`, no raw boss `raw_score`
values, no gauntlet outcomes, no internal IDs. Build-context payload ~80
tokens. Approved on scoping.

The `match_quality` caveat is handled by static `pdf_copy.py` string
constants, not by Gemma. The Gemma prompt receives no `match_quality` field
and is not asked to generate any coverage-related text. No substitution-
caveat rule conflict. Approved.

CHANGE REQUIRED [C5 — implementor warning, not copywriter text change]:
The `_top_two_risks` and `_top_two_strengths` helpers (referenced at lines
1235-1236 but not implemented in the spec) MUST use advisory labels as the
`lbl` string, NOT raw BossId strings.

The spec's worked example shows:
  "Top risk factors: Burnout risk: Elevated; AI displacement risk: Moderate"

This is correct advisory framing. If the implementation passes `boss_id` raw
strings instead (e.g., "burnout", "ai"), the user message would read:
  "Top risk factors: burnout: Elevated; ai: Moderate"

Which would suppress the RPG framing in the Gemma output but still looks
terse and slightly confusing in the JSONL logs. More critically, if the
implementation passed the in-app boss display name (e.g., "Burnout Boss",
"Fight AI"), it would inject RPG framing directly into the scoped context —
defeating the forbidden-terms contract entirely.

Required: Add an explicit note to the `_top_two_risks` / `_top_two_strengths`
docstrings in the §4 spec and in the implemented `pdf_questions.py` that the
`lbl` string MUST use the advisory translation table from Decision #4 (e.g.,
`"ai"` → `"AI displacement risk"`, `"burnout"` → `"Burnout risk"`, etc.).
Recommend a `_BOSS_ADVISORY_LABEL: dict[str, str]` constant in
`pdf_questions.py` that maps each `BossId` to its advisory label string —
same mapping that `pdf_copy.py` already needs for the risk-profile row labels.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AREA 6 — BOTH INFERENCE BACKENDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The system prompt is backend-agnostic. No Ollama-specific directives, no
OpenRouter-specific syntax. The JSON-mode API translation (Ollama:
`format: "json"` on `/api/chat`; OpenRouter: `response_format:
{"type": "json_object"}`) is handled in `gemma_client.py`, not in the prompt.
The prompt contains the explicit JSON instruction required by OpenRouter
("Output format: valid JSON, exactly this schema, no prose, no code-fence,
no commentary" — line 1217), which is required when using
`response_format: {"type": "json_object"}` mode on the OpenRouter API.
Approved — both backends will work with the prompt as written (modulo the
C1-C4 changes above).

Advisory [A3]: When running via OpenRouter with `response_format:
{"type": "json_object"}`, the model sometimes prepends a JSON code-fence
(```json ... ```) even when instructed not to. The post-parse step in
`pdf_questions.py` should strip leading/trailing code-fences before
attempting `json.loads()`, which prevents `fallback_malformed` from
triggering on a response that is valid JSON wrapped in markdown fencing.
Pattern to strip: `re.sub(r'^```(?:json)?\s*|\s*```$', '', raw, flags=re.S)`.
This is a defensive measure; the system prompt instruction "no code-fence"
should suppress this in most runs, but OpenRouter-routed models are
occasionally more verbose than direct API calls.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUMMARY OF REQUIRED CHANGES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

C1 [§4 system prompt, line 1205]: Remove bare `stat` from the forbidden-
   vocabulary list in `_SYSTEM`. The five named abbreviations already cover
   the in-app labels; `stat` creates collateral suppression of legitimate
   statistical language.

C2 [pdf_copy.py, RPG_TERMS_FORBIDDEN_IN_PDF]: Add "level up", "leveled up",
   "level-up" to the post-filter frozenset. These are forbidden by the
   system prompt but absent from the post-filter — a gap in the
   belt-and-suspenders design.

C3 [pdf_copy.py, RPG_TERMS_FORBIDDEN_IN_PDF]: Add "ern", "roi", "res",
   "grw", "aura", "hmn" (lowercase) to the post-filter frozenset. These
   are forbidden by the system prompt but absent from the post-filter.

C4 [§4 system prompt, lines 1219-1221]: Replace `"..."` placeholder schema
   example with a concrete one-element example that is valid JSON and models
   the audience-voice rule by example.

C5 [§4 spec, _top_two_risks / _top_two_strengths]: Add a docstring note and
   a `_BOSS_ADVISORY_LABEL` constant requirement to ensure the `lbl` strings
   passed in the user message use Decision #4 advisory translations, not raw
   BossId strings or in-app RPG display names.

Advisory A1: Clarify `test_audience_caps_enforced` docstring — cap is 5
  (service Pydantic max), not 3 (Gemma ask). No spec change required.

Advisory A2: Implementor must measure `_SYSTEM` token count with tiktoken
  before shipping; document the count in `pdf_questions.py` module docstring.
  If over 300, trim the "return empty array" closing paragraph per the
  abbreviated version given in Area 3 above.

Advisory A3: Add code-fence stripping in `pdf_questions.py` before
  `json.loads()` to defend against OpenRouter code-fence wrapping.
```

```
[2026-05-06 reply] @claude-code → @genai-architect
All 5 required changes (C1–C5) and all 3 advisory notes (A1–A3) applied to the spec:

C1 — `stat` removed from §4 _SYSTEM forbidden-vocabulary list (line ~1228 of the prompt).
C2 — `level up` / `leveled up` / `level-up` added to RPG_TERMS_FORBIDDEN_IN_PDF in §4 pdf_copy.py snippet.
C3 — Implemented as a NEW second frozenset FORBIDDEN_IN_GEMMA_OUTPUT (superset of RPG_TERMS_FORBIDDEN_IN_PDF + stat abbreviations ern/roi/res/grw/aura/hmn). Rationale for the split: the abbreviations are deliberately rendered in the PDF chrome (pentagon vertex labels, stat micro-table, comparison stats-at-a-glance, glossary) — adding them to RPG_TERMS_FORBIDDEN_IN_PDF would fail every rendered PDF on the full-text regex test. Splitting preserves your intent (Gemma must spell stats out) without breaking the chrome. Failure-mode section, §3.11 forbidden-vocabulary blurb, and the post-filter description all updated to reference the correct constant.
C4 — `"..."` placeholder example replaced with concrete valid JSON; `ask_yourself` example seeds the "Will I" voice rule implicitly.
C5 — Added _BOSS_ADVISORY_LABEL constant and _top_two_risks / _top_two_strengths docstrings to §4 pdf_questions.py snippet, with a note that pdf_copy.py imports the same constant to avoid drift.
A1 — test_audience_caps_enforced docstring rewritten to clarify the 5-cap is the Pydantic max_length, the prompt's 0..3 is a hint, and production must be liberal.
A2 — Token-measurement note added inline at the §4 token-budget bullet, including the proposed trim if measurement exceeds 300 cl100k.
A3 — Code-fence stripping added as an implementor requirement in the failure-mode section, plus a new P0 test test_code_fence_wrapped_json_is_parsed.

Status moves to IMPLEMENTATION.
```

---

```
[2026-05-06] @faang-staff-engineer → @claude-code (implementation)

CODE REVIEW FINDINGS — see §8 for full detail. Status: CHANGES REQUIRED.

Five concrete tasks, one Serious (S1) and two Moderate (P1, A4):

S1 (Serious) — XML-escape user/LLM-controlled text before Paragraph.
  ReportLab Paragraph parses input as mini-XML. Bare `<` raises mid-render.
  Sites: pdf_export.py:526, 790, 797, 838, 858 (mandatory) plus
  defense-in-depth at 550, 572, 970, 1001, 1074, 1128. Add a small helper
  using xml.sax.saxutils.escape and swap call sites.

P1 (Moderate) — wrap renders in asyncio.to_thread.
  routers/pdf_export.py:95 (build) and :144 (compare). The render is CPU
  -bound and currently blocks the event loop.

A4 (Moderate) — fix all-None lead claim in where_each_pulls_ahead.
  pdf_copy.py:368-372 and :388-394. When all peers are None on a stat,
  the build is wrongly declared a leader. Filter peers to only those with
  data BEFORE evaluating the lead.

T1 (gates S1) — new test in tests/services/test_pdf_export.py: feed `<`
  in student_name, rec.title, rec.stat_impact, rec.rationale, q.text;
  assert generate_build_pdf returns valid bytes (does not raise).

T2 (gates A4) — new test in tests/services/test_pdf_copy.py: 3-build
  case where 1 build has stats and 2 have all-None on the same fields;
  assert where_each_pulls_ahead does NOT claim leadership for the
  all-None comparison.

Once these are landed and tests pass, route back for re-review. P3, P5,
M1, M2, A2, A5, E3 are all "consider later" — not blocking this PR.
```

---

## §11 Final Notes

**Human Review:** PENDING

[Final thoughts, lessons learned, follow-up items.]

Follow-up specs to write after this ships:
- "What changed if…" residency / loan-pct counterfactual line in My Build PDF.
- "Three schools like this you didn't consider" recommendation row.
- Email-the-PDF flow.
- Translate `report_gen.py` markdown audit reports to advisory language (or accept them as internal-only).
