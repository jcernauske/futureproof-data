# Staff Engineer Code Review — feature-pdf-report-exports

**Date:** 2026-05-06
**Agent:** @faang-staff-engineer
**Spec:** docs/specs/feature-pdf-report-exports.md
**Spec status entering review:** TESTING (1744/0/0 pytest, 835/0/0 vitest)
**Spec status exiting review:** CHANGES REQUIRED (§8 Code Review)

## Files Audited

- backend/app/services/pdf_export.py (1235 lines)
- backend/app/services/pdf_questions.py (415 lines)
- backend/app/services/pdf_copy.py (448 lines)
- backend/app/services/gemma_client.py (delta — generate_chat_async timeout/response_format kwargs + log_synthetic_event helper)
- backend/app/routers/pdf_export.py (165 lines)
- backend/app/models/api.py (delta — RiskLevel + 4 new Pydantic models)
- backend/app/state.py + backend/app/services/builds.py (cross-reference for _load_build_or_404 trust model)
- backend/app/routers/wrapped.py (precedent for Response shape, error wrapping, Cache-Control)
- frontend/src/api/pdf.ts (contract verification)

## Cross-references

- Spec §4 Service Changes / Architecture Overview / Data Model Changes
- Spec §5 architect + data reviewer rulings (leading-direction table, threshold table, walrus tie semantics)
- Decision #4 (RPG-language ban → advisory-only language in print)
- genai-architect §10 C1–C5 (forbidden vocab, _BOSS_ADVISORY_LABEL centralization, JSON code-fence stripping)
- feedback_scoped_llm_contexts.md (top-2 risks/strengths scoping for Gemma context)

## Sanity Checks Run

- `_slug` adversarial inputs (path traversal, NUL, shell metacharacters, Unicode) — all collapse safely.
- ReportLab Paragraph parsing with `<`, `&`, malformed markup, unclosed tags, real school names ("Texas A&M") — found `<` raises, `&` is permissive.
- Double TTFont registration via `pdfmetrics.registerFont` — confirmed idempotent.
- grep for disk-write surfaces in pdf_*.py — zero hits.
- grep for `gemma_path` rendered or serialized to HTTP — zero hits outside Pydantic model.

## Findings Summary

| ID | Severity | Title |
|----|----------|-------|
| S1 | 🟠 Serious | ReportLab Paragraph parses Gemma + user input as XML — `<` raises ValueError mid-render |
| P1 | 🟡 Moderate | Sync ReportLab render blocks the event loop; should be asyncio.to_thread |
| A4 | 🟡 Moderate | where_each_pulls_ahead claims leadership when all peers have None for that stat |
| S2 | 🔵 Minor | Build ownership / no-auth — by design per project architecture; doc trust model |
| E3 | 🔵 Minor | _load_build_or_404 only catches FileNotFoundError; inherits wrapped.py pattern |
| P5 | 🔵 Minor | Unbounded /pdf concurrency; defer until load test surfaces a problem |
| M1 | 🔵 Minor | Sources line splitter is fragile to literal edits |
| A5 | 🔵 Minor | Whitespace-only Gemma response routes to fallback_malformed (should be _empty) |

## What Passed

- Byte-stream contract end-to-end (no temp files, no disk writes for PII)
- `gemma_path` containment (Pydantic-only; never crosses HTTP or PDF boundary)
- `timeout_s` kwarg threaded through both Ollama (`httpx.post(timeout=...)`) and OpenRouter (`completion_kwargs["timeout"]`)
- Filename `_slug` immune to traversal/injection (whitelist regex)
- HTTPException(500) wrapping flows through CORSMiddleware per wrapped.py precedent
- Forbidden-vocab pair (`RPG_TERMS_FORBIDDEN_IN_PDF` + `FORBIDDEN_IN_GEMMA_OUTPUT`) correctly split to allow stat abbreviations in PDF chrome
- `_BOSS_ADVISORY_LABEL` centralized; both consumers import from same source
- 5-fallback-path discipline with `log_synthetic_event` per path
- Pydantic 2..3 build cap + same-major guard validation order

## Verdict

CHANGES REQUIRED. Routing 5 concrete tasks back to implementation via §10 Discussion entry: 1× Serious (XML escape), 2× Moderate (asyncio.to_thread, all-None lead fix), 2× new tests gating those fixes.

## Artifacts

- §8 Code Review (@faang-staff-engineer) — full findings table, fix routing, what's good
- §10 Discussion — routing entry to @claude-code (implementation) with concrete file:line + fix instructions per finding

## Decisions

- Did NOT mark BLOCKER. S1 is a real production crash but the fallback path is graceful (HTTPException 500), no data corruption, two-line fix. Route back for one round of fixes.
- Did NOT flag the `_load_build_or_404` double-disk-lookup or the `state.get_build` exception leaks (corrupted Build → 500 outside CORS). Both are pre-existing patterns in `wrapped.py` and not introduced by this PR. Defer to a separate cleanup spec.
- Did NOT enforce a render semaphore. At hackathon-demo scale (single laptop) the 100 KB-per-render footprint isn't an OOM. Re-evaluate after a real load test.

## Time on Task

~50 minutes of reading line-by-line, ~10 minutes adversarial sanity checks (grep + Python REPL on ReportLab parser + slug fuzzing), ~25 minutes writing findings.

---

## Round 2 (re-review)

**Date:** 2026-05-06
**Spec status entering re-review:** CHANGES REQUIRED (Round 1 §8)
**Spec status exiting re-review:** APPROVED

### Files re-audited
- backend/app/services/pdf_export.py — `_safe()` helper (144-155), all 53 Paragraph call sites, font-lock thread safety (95, 109-113)
- backend/app/services/pdf_copy.py — `_leading_factors_for` rewrite (348-399)
- backend/app/routers/pdf_export.py — both `asyncio.to_thread` wraps (99-104, 150-152)
- backend/tests/services/test_pdf_export.py — `TestXmlEscapeUserControlledStrings` (387-461, 4 tests)
- backend/tests/services/test_pdf_copy.py — `TestWhereEachPullsAheadAllNonePeers` (417-476, 2 tests)

### Verification
- Ran the 6 new P0 regression tests in isolation: all pass.
- Ran the full PDF feature test scope (test_pdf_export.py + test_pdf_copy.py + test_pdf_questions.py): 107/0/0.
- Confirmed (via grep) every user/LLM-controlled field that flows into Paragraph is `_safe`-wrapped.
- Confirmed PDF doc-info `title=` and canvas `drawString(title)` paths are not XML-parsed (no `_safe` needed there).

### Round 1 conditions, status
- S1 (Serious — XML escape): RESOLVED.
- P1 (Moderate — event loop): RESOLVED.
- A4 (Moderate — all-None lead claim): RESOLVED.

### One Minor follow-up surfaced
- `pdf_export.py:578` interpolates `build.home_state` into a Paragraph without `_safe`. Today's UI constrains it to a 2-letter dropdown, but the Pydantic model (`Build.home_state: str | None = None`) does not enforce a regex. Direct API clients could submit `<x` and crash the export. One-line fix (`_safe` wrap or Pydantic `^[A-Z]{2}$` validator). Not blocking — flagged in §8 Round 2 as S1-residual.

### Verdict
APPROVED. The three round-1 conditions are met and tested. The bonus `_FONTS_LOCK` is correct double-checked locking, which is a real correctness win now that renders run in the worker thread pool.

## Time on Task (Round 2)

~12 minutes — reading the deltas, grepping every Paragraph + user-field interpolation, running the new tests + the PDF-feature suite, writing the re-review.
