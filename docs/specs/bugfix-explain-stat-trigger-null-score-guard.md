# Bugfix: Explain-Stat Receipt Must Render Honestly When Score Is Null

## Claude Code Prompt

```
Read and implement the spec at
docs/specs/bugfix-explain-stat-trigger-null-score-guard.md.

The bug: clicking "✦ Explain this to me" on a stat row whose build
score is null (e.g. ERN row when stats.ern === null) fires the chat
opener, the JSON path postprocessor returns None at the existing
null-guard, the fallback markdown-spike retries WITHOUT a score-null
guard of its own, and Gemma fabricates a score from partial inputs
(observed: ERN — on pentagon, 3.7/10 in the chat).

This bugfix replaces the fabricated-score path with an honest
"missing-data receipt" rendered through the existing
ExplainStatReceiptCard. The fix has three coordinated parts:

  1. Schema: ExplainStatReceipt.score relaxes from `int` (1-10) to
     `int | None`. Pydantic + Zod mirror.
  2. Frontend: ExplainStatReceiptCard learns to render an open-ring
     callout (◦ —) when score is null, matching the pentagon vertex
     missing-data treatment. The "✦ Explain this to me" trigger stays
     visible on null-score rows; the click opens the same receipt
     card with score=null.
  3. Backend: when the explain-this-stat sentinel fires AND
     build.career.stats.<stat> is None, ask_gemma SKIPS the Gemma
     loop entirely. Instead it dispatches the same two MCP tools
     (get_career_paths, get_occupation_data) and constructs an
     ExplainStatReceipt server-side with score=None,
     value_pct/anchor_dollars from the live tool results, and a
     plain-English missing_reason on each component bullet whose
     input is null. No Gemma call → no fabrication risk.

Key files:
  - frontend/src/types/chat.ts (Zod: score nullable)
  - frontend/src/components/menu/ExplainStatReceipt.tsx (open-ring score)
  - frontend/src/screens/BuildResultsScreen.tsx (button always visible)
  - backend/app/models/api.py (Pydantic: score: int | None)
  - backend/app/services/ask_gemma.py (server-built missing receipt)

After implementing, run full test suite (pytest + ruff + mypy +
TypeScript + vitest + Vite build). Manual smoke verification on the
Millikin → Chemistry → Food Science Technicians build (the production
case in the screenshot): clicking "✦ Explain this to me" on the ERN
row must open the receipt with an open-ring score callout and a 60%
bullet whose missing_reason names College Scorecard. Tail
logs/gemma.jsonl and confirm: ONE
`call_site="explain_ern_missing_receipt"` record, ZERO Gemma exchange
records.
```

---

**Spec Status:** IMPLEMENTED
**Created:** 2026-05-02
**Updated:** 2026-05-02
**Priority:** High (live bug, user-visible, undermines the trust the ERN explain-receipt feature was built to create)
**Blocked By:** —
**Related Specs:**
- `docs/specs/feature-explain-stat-receipt.md` (the ERN receipt spec; this bugfix adds the missing-data-receipt path that complements its happy-path JSON contract)
- `docs/specs/feature-explain-stat-receipt-roi-res-grw.md` (DRAFT — will inherit the schema relaxation and the per-stat missing-receipt builder pattern when ROI/RES/GRW triggers wire up)
- `docs/specs/feature-explain-stat-receipt-aura.md` (DRAFT — its missing-data convention from §1g is the source pattern this bugfix generalizes)

**Related References:**
- `docs/reference/stat-display-surfaces.md` (§1a legend trigger; §1b open-ring vertex treatment for null stats; §1g AURA missing-data popover convention; §1i ExplainStatReceiptCard)
- Memory: `feedback_no_substitution_caveat` — N/A; this is not a CIP-substitution caveat, it's a genuine "no data" state for the underlying inputs to a stat formula.
- Memory: `feedback_stat_blast_radius_check` — verified: this bugfix touches the legend trigger (§1a), the receipt card (§1i), and the per-stat dispatch in `ask_gemma.py`. No other surfaces affected.

---

## §1 Problem

### What's broken

Clicking "✦ Explain this to me" on the ERN legend row when `build.career.stats.ern === null` produces a fabricated score in the chat. Observed: Millikin University → Chemistry → Food Science Technicians, pentagon shows `ERN —`, ROI also `—`, AURA 7, GRW 6, RES 6 — yet the chat panel renders "Earning Power — 3.7/10" with the spike's free-form prose template ("The one-liner. ... How it works. ... 60% — your school's program rank. I do not have the specific median earnings for Millikin University's Chemistry graduates...").

### Reproduction

1. Open `/build/<id>` for the Millikin-Chemistry-FoodScienceTechnicians build (or any build where `cip_family_earnings_rank` is null in the underlying `program_career_paths` row, producing `stats.ern = None` per `compute_stat_ern`).
2. Pentagon vertex for ERN renders as `—` (open-ring + em-dash, the standard missing-data treatment).
3. Click "✦ Explain this to me" on the ERN row of the legend.
4. Slide-in chat opens, fires sentinel `[explain-this:ERN]`, streams the trace rail, returns a free-form prose bubble (NOT the structured receipt card) with a fabricated `3.7/10` score.

### Root cause

The ERN spec's Decision 7 ("`_postprocess_ern_explain_receipt` returns None when `build.career.stats.ern is None`") is implemented and works — but the contract only governs the JSON path. When the postprocessor returns None, the dispatch falls back to the markdown-spike retry, which has **no equivalent score-null guard**. The spike's appendix asks Gemma to compute and render a score from the available signals; with one of two percentile inputs missing, Gemma fabricates from partial data.

### Why "just hide the button" was rejected

The first cut of this bugfix gated the button on `stats.ern !== null` and short-circuited the backend with a generic "this isn't available" string. That ships the worst version of the affordance: the student sees `ERN —` on the pentagon, has the obvious question — *why don't I have an Earning Power score?* — and the explain CTA disappears at the exact moment they need it most. Hiding the affordance is the opposite of what the receipt was built to do (close the trust loop on stats).

The right behavior: the button stays visible. Clicking it opens the same receipt card the score-present path uses — but the card renders an honest "no score, here's why" state, with the missing input named at the source.

---

## §2 Solution

### 2a. Schema: relax `score` to nullable

**Modify:** `backend/app/models/api.py`

```python
class ExplainStatReceipt(BaseModel):
    ...
    score: int | None = Field(
        default=None,
        ge=1,
        le=10,
        description=(
            "The student's score on this stat. Server-stamped from "
            "build.career.stats.<stat>; null when the underlying "
            "inputs are missing — the renderer shows an open-ring "
            "callout instead of a number, and per-component "
            "missing_reason fields explain which input is unavailable."
        ),
    )
```

**Modify:** `frontend/src/types/chat.ts`

```typescript
score: z.number().int().min(1).max(10).nullable(),
```

The Zod schema is the SSE-boundary truth; relaxing it lets the existing `isExplainStatReceipt` guard accept score-null payloads without sniffing.

### 2b. Frontend: open-ring score callout

**Modify:** `frontend/src/components/menu/ExplainStatReceipt.tsx`

The score callout already lives in a single `<header>` block. Branch on `payload.score === null`:

- **Score-present (existing):** number + `/score_max`, accent color.
- **Score-null (new):** `◦` open-ring glyph + em-dash + `/score_max`, all in `var(--color-text-muted)`. Mirrors the pentagon vertex treatment from `stat-display-surfaces.md` §1b. `aria-label` reads "{stat name} score not available for this combination yet" so screen readers announce the missing state honestly. Sets `data-score-missing="true"` for testability.

The component-row missing-data treatment is unchanged — `value_pct === null` already renders `◦ —` and `missing_reason` already renders below the percentile callout. The only new render branch is the score callout itself.

### 2c. Frontend: button always visible

**Modify:** `frontend/src/screens/BuildResultsScreen.tsx`

The "✦ Explain this to me" trigger renders unconditionally on the ERN row (matching its score-present visibility). The earlier `canExplainStat` gate is deleted — when the student has no score, that's *exactly* when they want the explanation.

### 2d. Backend: server-built missing-score receipt

**Modify:** `backend/app/services/ask_gemma.py`

When `build.career.stats.<stat> is None` AND the explain-this sentinel fires, ask_gemma takes a deterministic server-built path that never calls Gemma:

```python
if explain_ern:
    if _get_build_stat(builds[0], "ERN") is None:
        receipt, log = await _ern_missing_score_receipt_path(builds[0])
        # Surface tool calls so the trace rail shows the same rhythm
        # as the score-present path; return AskResponse(response=receipt).
        ...
        return
    system = system + _ern_explain_appendix_json(builds[0].career)
```

`_ern_missing_score_receipt_path(build)` does three things:

1. **Dispatch the same two MCP tools the score-present path uses** (`get_career_paths`, `get_occupation_data`) via the existing `_dispatch` so we know which input is null.
2. **Run `_extract_tool_results`** on the resulting `ToolCallTurn` log — same extractor the score-present postprocessor uses; same envelope handling.
3. **Construct the receipt server-side** via `_build_ern_missing_score_receipt` from canned prose templates substituted with the build's identifiers + the live tool values. `score=None`. `score_max=10`. Per-component `value_pct` and `anchor_dollars` come from the tool results when present, `None` when null. Per-component `missing_reason`:
   - 60% bullet, no earnings: "College Scorecard doesn't report median earnings for {school}'s {program} graduates yet — usually because the cohort is small enough that publishing earnings would identify individual students."
   - 60% bullet, earnings present but rank missing: "College Scorecard reports median earnings for {school}'s {program} graduates (${earnings:,}), but doesn't yet rank that figure against peer programs in the same field of study."
   - 40% bullet, no wage: "The Bureau of Labor Statistics (BLS) hasn't published a median wage for {career_title} yet."
   - 40% bullet, wage present but percentile missing: "The Bureau of Labor Statistics (BLS) reports median pay for {career_title} (${wage:,}/year), but doesn't yet rank that figure against all U.S. occupations."
4. The math line replaces missing inputs with `n/a` and the `→ score N/10` tail with `→ no score available`. Example: `0.6 × n/a + 0.4 × 0.92 → no score available`.

The `one_liner`, `sources`, and `why_mix_paragraph` are universal — the same text whether the score is null or not. They explain what ERN measures and why we mix the two pieces; that doesn't change because one input is missing.

### 2e. Trace events parity

The score-null path emits `TraceTurnStart` + `TraceTurnComplete` for each MCP fetch (in `chat_ask_stream`) and a populated `tool_calls` list (in `chat_ask`) so the trace rail shows the same two-tool rhythm the student sees on the score-present path. The only differences from a happy-path turn: no Gemma synthesis turn, and the `final_text` payload is a server-built receipt with `score=None`.

### 2f. Logging

The server-built path appends one structured record to `logs/gemma.jsonl` (no Gemma exchange record because no Gemma call happened):

```json
{
  "call_site": "explain_ern_missing_receipt",
  "build_id": "<id>",
  "reason": "build_score_null",
  "cip_rank": null,
  "wage_pct": 0.92,
  "earnings": null,
  "wage": 50300
}
```

Lets us track which inputs are most often null per build, which feeds the data-pipeline backfill conversation.

### 2g. Reference index

**Modify:** `docs/reference/stat-display-surfaces.md`

- §1a (Pentagon legend): note the trigger stays visible regardless of score nullity; the receipt itself absorbs the missing-data treatment.
- §1i (`ExplainStatReceiptCard`): note the new score-null render path + the backend `_ern_missing_score_receipt_path`.

### 2h. Bonus fix: `_extract_tool_results` must not require SOC match for CIP-level fields

**Modify:** `backend/app/services/ask_gemma.py` (`_extract_tool_results`)

Surfaced after the missing-receipt path shipped: a real production case (IU-Bloomington → Business → Market research analysts, ERN=9) showed the receipt rendering with Gemma's prose claiming "$63,371 / 90th percentile" while the structured row stamped `◦ —` and "no median earnings reported for this program yet" — the exact prose-vs-data mismatch the receipt was built to prevent.

Root cause: `_extract_tool_results` filtered `get_career_paths` rows by `soc_code == build.career.soc_code` BEFORE reading `cip_family_earnings_rank` and `earnings_1yr_median`. Both fields are `(school, CIP)`-level — same value across every soc_code fanout row — so requiring SOC match silently fails when:
- CIP substitution returns rows whose soc_codes are a different fanout set than the build was computed from.
- The build's `career.soc_code` formatting drifts from the response (extra precision, missing dot, etc.).
- The matching row exists but its CIP-level fields are individually null (storage-quirk per row).

Gemma reads the same field from any row in the response (because the values ARE present), the server discards them due to the strict match, and the receipt ends up internally contradictory.

Fix: read `cip_family_earnings_rank` and `earnings_1yr_median` from any non-null row in the response. The `soc_code` parameter is now dead weight on `_extract_tool_results`'s signature — removed at all four call sites (the score-null builder, the score-present postprocessor, the markdown-fallback in `chat_ask`, the markdown-fallback in `chat_ask_stream`). The `get_occupation_data` branch is unchanged — that tool is queried with a single SOC and returns a single row, no matching needed.

Coverage:
- `test_extract_tool_results_reads_cip_fields_when_soc_code_in_first_row` — happy path stays green.
- `test_extract_tool_results_reads_cip_fields_from_any_row` — one row missing values, another row carries them; extractor reads from the row that has them.
- `test_extract_tool_results_when_build_soc_absent_from_response` — the actual bug: no row matches the build's SOC, but every row carries the CIP-level values. Old behavior: `(None, None, ...)` → prose/data mismatch. New behavior: values extracted correctly.
- `test_extract_tool_results_genuine_null_when_no_rows_have_value` — when every row's CIP-level field IS null, the extractor still returns None (driving the missing-receipt path correctly).

### 2i. What is NOT changing

- The score-present JSON path's contract (Decisions 7 and 13 of `feature-explain-stat-receipt.md`) is untouched. Same Gemma loop, same postprocessor, same markdown fallback for parse failures.
- The "?" StatInfoPopover trigger on every legend row is unchanged.
- The pentagon vertex labels (`ERN —` etc.) for null stats stay unchanged.
- The component-row missing-data render (`◦ —` glyph + missing_reason note) was already in place from the original ERN spec — we reuse it.
- AURA's per-stat receipt is still out of scope (handled by `feature-explain-stat-receipt-aura.md`).

---

## §3 Testing

### Frontend (vitest)

1. **`frontend/src/components/menu/ExplainStatReceipt.test.tsx` (modify)**
   - `renders an open-ring score callout when score is null` — payload with `score: null`, one component bullet missing, one present. Assert: `data-score-missing="true"`, no fabricated `\d{1,2}/10` substring, `aria-label` contains "not available for this combination yet". The 60% bullet has a `receipt-missing-60` element; the 40% bullet has values. Math card contains `n/a` and `no score available`.

2. **`frontend/src/screens/BuildResultsScreen.test.tsx` (modify)**
   - `ern_explain_link_visible_when_score_present` — fixture build with `stats.ern=7` → trigger renders.
   - `ern_explain_link_visible_when_score_null` — fixture build with `stats.ern=null` → trigger STILL renders.

### Backend (pytest)

3. **`backend/tests/services/test_ask_gemma.py` (modify)**
   - `test_get_build_stat_reads_correct_attr` × 5 (parametrized over ERN/ROI/RES/GRW/AURA).

4. **`backend/tests/services/test_ask_gemma_explain_integration.py` (modify)**
   - `test_chat_ask_ern_explain_returns_missing_receipt_when_score_null` — sync variant: `stats.ern=None`, dispatch patched with `cip_rank=None, earnings=None`. Asserts: response is `ExplainStatReceipt` with `score=None`, the 60% bullet's `missing_reason` mentions "College Scorecard" and the school name, the 40% bullet has values, math line contains `n/a` and `no score available`, `tool_calls` has both MCP calls, Gemma loop call_count == 0.
   - `test_chat_ask_ern_explain_missing_receipt_handles_both_inputs_null` — both inputs null → both bullets carry missing_reason; math line has two `n/a` placeholders.
   - `test_chat_ask_stream_ern_explain_emits_missing_receipt` — stream variant: emits two `TraceTurnStart`/`TraceTurnComplete` pairs (one per MCP fetch) + one `TraceFinalText` (carrying the receipt) + one `TraceDone`.
   - `test_score_null_path_logs_structured_record` — `logs/gemma.jsonl` gains one `call_site="explain_ern_missing_receipt"` record per call, with `build_id`, `reason`, and the four input values.
   - `test_score_present_path_unchanged` — non-null `stats.ern` → JSON path runs normally; the score-null branch is not entered (sentinel-fail dispatch confirms).

### Expected results

- All new tests pass.
- All existing tests continue to pass — specifically:
  - The full ERN explain-receipt test suite (`test_ask_gemma_explain_receipt.py` happy-path tests) passes unchanged because those tests use builds with non-null `stats.ern`.
  - `test_postprocess_returns_none_when_build_score_null` (existing) passes unchanged because the postprocessor's null-guard contract is unchanged — it's now unreachable on the production score-null path (the server-built receipt fires before the Gemma loop), but the unit-level invariant remains.
  - `test_chat_ask_ern_explain_falls_back_on_parse_failure` (existing) passes unchanged because the markdown fallback only fires on JSON-parse failures with non-null scores.
  - All boss/skill/build/branch/compare scope tests pass — non-stat scopes are untouched.

### Manual smoke verification (Millikin → Chemistry → Food Science Technicians)

- Open the build, click "✦ Explain this to me" on the ERN row → the receipt panel opens.
- Score callout renders an open ring + em-dash, NOT a number.
- 60% bullet shows "your school's program rank" with a `◦ —` percentile-callout slot, the school anchor text, and a `missing_reason` line naming College Scorecard.
- 40% bullet shows "this career's pay rank" — either values (if BLS has data for SOC 19-4031) or its own missing_reason naming BLS.
- Math line: `0.6 × n/a + 0.4 × {value or n/a} → no score available`.
- Sources pills + why-mix paragraph render normally.
- Tail `logs/gemma.jsonl` and confirm: ONE `call_site="explain_ern_missing_receipt"` record per click, ZERO Gemma exchange records (no `_log_exchange` from `gemma_client.generate*`).

### Out of scope for this bugfix

- Generalizing the score-null receipt to ROI/RES/GRW/AURA — those triggers don't exist yet; they ship in the per-stat follow-up specs and consume the same schema relaxation + a stat-specific `_build_<stat>_missing_score_receipt` function.
- Backfilling missing data in `consumable.program_career_paths` for the affected program / career pairs — that's a data-pipeline question routed to the relevant ingestor specs.
- Changing the pentagon vertex `—` rendering or the legend row's missing-data treatment — those are correct as-is.
- Caching the two MCP fetches per build_id — the current cost is bounded (~1-2s for two read-only Gold-zone queries) and the cache layer is a separate optimization spec.

---

## §5 Architecture Review
**Status:** SKIPPED (lightweight bugfix — extends an existing schema by one nullable field, adds one server-side receipt builder, reuses existing tool-dispatch + extraction infrastructure)

## §6 Implementation Log
**Status:** COMPLETE

### Files Modified
| File | Change Summary |
|------|---------------|
| `backend/app/models/api.py` | `ExplainStatReceipt.score` relaxed from `int` (ge=1, le=10) to `int \| None` with the same range when not None. |
| `backend/app/services/ask_gemma.py` | Added `_get_build_stat`, `_render_missing_score_math_line`, `_dispatch_ern_explain_tools`, `_build_ern_missing_score_receipt`, `_ern_missing_score_receipt_path` + universal copy constants `_ERN_ONE_LINER` and `_ERN_WHY_MIX_PARAGRAPH`. Wired the score-null branch into both `chat_ask` (returns `AskResponse(response=receipt, tool_calls=[…])`) and `chat_ask_stream` (yields `TraceTurnStart`/`TraceTurnComplete` per MCP fetch, then `TraceFinalText(receipt)` + `TraceDone`) BEFORE the JSON-mode appendix is appended. Logs one `call_site="explain_ern_missing_receipt"` record. **Also:** dropped the unnecessary `soc_code` filter in `_extract_tool_results` for `get_career_paths`. The `cip_family_earnings_rank` and `earnings_1yr_median` columns are `(school, CIP)`-level — same on every soc fanout row — so requiring a SOC match silently failed under CIP-substitution / SOC-format drift, leaving Gemma's prose claiming a value the server then couldn't surface (◦ — vs `$X / Nth percentile` mismatch). |
| `backend/tests/services/test_ask_gemma_explain_receipt.py` | Added 4 `_extract_tool_results` tests covering the SOC-mismatch regression case, the happy path, the partial-null-row case, and the genuine all-null fallthrough. |
| `backend/tests/services/test_ask_gemma.py` | Added 5 parameterized `_get_build_stat` tests. |
| `backend/tests/services/test_ask_gemma_explain_integration.py` | Replaced the previous null-fallback test with five new tests covering the missing-receipt path: school-only-null, both-null, stream variant, structured-log record, score-present-unchanged control. |
| `frontend/src/types/chat.ts` | Zod `score` relaxed to `.nullable()`. |
| `frontend/src/components/menu/ExplainStatReceipt.tsx` | Score callout branches on `payload.score === null` — renders `◦ —` + `/score_max` in `text-muted`, `data-score-missing="true"`, with an honest `aria-label`. |
| `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | Added `renders an open-ring score callout when score is null` test. |
| `frontend/src/screens/BuildResultsScreen.tsx` | Removed the `canExplainStat` gate; the "✦ Explain this to me" trigger renders unconditionally on the ERN row. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | Replaced the suppression test with `ern_explain_link_visible_when_score_null`. |
| `docs/reference/stat-display-surfaces.md` | §1a notes the trigger is always visible; §1i notes the server-built missing-score receipt path. |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | PASS | — | — |
| 2 | PASS (after mypy fix) | Two new mypy errors in `ask_gemma.py` from variable-name shadowing on `receipt`. | Renamed score-null variables to `missing_receipt`/`missing_log`/`missing_tool_calls` so the score-present `receipt: ExplainStatReceipt \| None` retains its declared type. |
| 3 | PASS | Real-world bug surfaced post-merge: prose-vs-data mismatch on the IU → Business → Market research analysts receipt (ERN=9). | Dropped the SOC-match filter in `_extract_tool_results` for `get_career_paths`; CIP-level fields now read from any row. Added 4 regression tests. |

## §7 Test Coverage
**Status:** COMPLETE

### Tests Added
| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|
| `frontend/src/screens/BuildResultsScreen.test.tsx` | `ern_explain_link_visible_when_score_present` | Trigger renders when `stats.ern=7`. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | `ern_explain_link_visible_when_score_null` | Trigger STILL renders when `stats.ern=null`. |
| `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | `renders an open-ring score callout when score is null` | Open-ring score, no fabricated number, honest aria-label, per-component missing/present mix, math card with n/a + "no score available". |
| `backend/tests/services/test_ask_gemma.py` | `test_get_build_stat_reads_correct_attr` × 5 | Reads `build.career.stats.{lower}` for all five stat codes. |
| `backend/tests/services/test_ask_gemma_explain_integration.py` | `test_chat_ask_ern_explain_returns_missing_receipt_when_score_null` | Sync `chat_ask`: returns `ExplainStatReceipt` with `score=None`, missing_reason names College Scorecard, both MCP tools dispatched, Gemma loop call_count == 0. |
| `backend/tests/services/test_ask_gemma_explain_integration.py` | `test_chat_ask_ern_explain_missing_receipt_handles_both_inputs_null` | Both inputs null → both bullets carry missing_reason; math line has two n/a placeholders. |
| `backend/tests/services/test_ask_gemma_explain_integration.py` | `test_chat_ask_stream_ern_explain_emits_missing_receipt` | Stream variant: 2 turn pairs + 1 final_text(receipt) + 1 done. |
| `backend/tests/services/test_ask_gemma_explain_integration.py` | `test_score_null_path_logs_structured_record` | One `call_site="explain_ern_missing_receipt"` record per call. |
| `backend/tests/services/test_ask_gemma_explain_integration.py` | `test_score_present_path_unchanged` | Non-null `stats.ern` → JSON path runs normally; direct dispatch is NOT called. |
| `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_extract_tool_results_reads_cip_fields_when_soc_code_in_first_row` | Happy path stays green after the SOC-filter removal. |
| `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_extract_tool_results_reads_cip_fields_from_any_row` | Values on a non-matching-SOC row are extracted when the matching row's fields are null. |
| `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_extract_tool_results_when_build_soc_absent_from_response` | REGRESSION: build's SOC isn't in the response at all → CIP-level values still extracted from any row. |
| `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_extract_tool_results_genuine_null_when_no_rows_have_value` | When every row has null CIP-level fields, extractor correctly returns None. |

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest | 1412 | 0 | 0 | 1412 |
| vitest | 793 | 0 | 0 | 793 |

## §8 Code Review
**Status:** SKIPPED (lightweight bugfix)

## §9 Verification
**Status:** COMPLETE (automated); manual smoke deferred to human.

### Backend
| Check | Result |
|-------|--------|
| Lint (ruff) | PASS for changed files. One pre-existing unrelated failure in `app/services/stat_engine.py:339` (introduced in commit f06fa6e, untouched by this bugfix). |
| Type check (mypy) | PASS for `app/services/ask_gemma.py`. 18 pre-existing errors in `app/models/api.py`, `app/services/gemma_client.py`, `app/services/guidance.py` (unchanged from baseline). |
| Tests (pytest) | 1412/1412 passed in 5.32s. |

### Frontend
| Check | Result |
|-------|--------|
| TypeScript | PASS (`tsc --noEmit`, no output). |
| Tests (vitest) | 793/793 passed in 15.75s across 68 files. |
| Production build (Vite) | PASS (`vite build`, 904 modules transformed, 1.65s). |

### Manual smoke (deferred to human)
| Step | Result |
|------|--------|
| ERN button still renders on Millikin → Chemistry → Food Science Technicians build | DEFERRED |
| Click opens the receipt with an open-ring `◦ —` score callout | DEFERRED |
| 60% bullet's missing_reason names College Scorecard + the school + the program | DEFERRED |
| `logs/gemma.jsonl` shows exactly one `explain_ern_missing_receipt` record per click and zero Gemma exchange records | DEFERRED |

## §10 Discussion

```
[2026-05-02] Direction change mid-implementation.
First cut shipped a hide-the-button + canned-string short-circuit
("ERN isn't available for this combination yet…") and was correctly
rejected: removing the affordance at the exact moment the student
asks "why don't I have a score?" is the worst version of this. The
implemented design keeps the receipt visible, renders an honest
open-ring score, and names the missing input at its source.
```

## §11 Final Notes
**Human Review:** PENDING

The bugfix is intentionally ERN-only — the same pattern (relaxed schema, server-built receipt builder, per-stat missing_reason templates) generalizes to ROI/RES/GRW/AURA when their explain-receipt specs land. The schema change (`score: int | None`) ships now so those follow-up specs don't need to re-relax the contract.
