# Session Log — Architecture Review: PDF Report Exports

**Session ID:** 2026-05-06-architect-feature-pdf-report-exports
**Timestamp:** 2026-05-06
**Agent:** @fp-architect
**Spec:** `docs/specs/feature-pdf-report-exports.md`
**Spec Status entering session:** ARCH REVIEW
**Spec Status exiting session:** ARCH REVIEW (CHANGES REQUESTED — pending conditions in §5)

## Scope

Review §1–§4 of the spec: service architecture, Gemma call shape, PDF rendering library choice, router placement, frontend trigger surfaces, Pydantic request/response models. Resolve Decision #1 (ReportLab vs Playwright vs WeasyPrint) before the implementation agent begins.

Out of scope (other agents own these):
- Print layout, color tokens, typography → @fp-design-visionary
- Stat-source provenance, risk-level threshold mapping, same-major CIP semantics → @fp-data-reviewer (running in parallel)
- Code quality, security, perf → @faang-staff-engineer (later)

## Actions Taken

1. Read spec end-to-end (§1 through §11). 902 lines total.
2. Read backend reference files to ground the review against the actual codebase, not the spec's claims about it:
   - `backend/app/main.py` — router registration patterns and `lifespan` warm-up.
   - `backend/app/routers/builds.py` — `/build/{id}/...` route patterns and `_load_build_or_404` precedent.
   - `backend/app/routers/builds_collection.py` — `/builds/...` collection-namespace router that mounts at empty prefix.
   - `backend/app/routers/wrapped.py` — closest existing precedent for binary-byte response (`Response(content=png, media_type="image/png", headers={"Content-Disposition": ...})`) and for the CORS-friendly mid-render error trap.
   - `backend/app/routers/skills.py`, `gauntlet.py` — confirmed `/build/{build_id}/...` namespace has no path-segment collision with `pdf`.
   - `backend/app/services/gemma_client.py` — verified the `generate_chat_async` signature, the JSON-mode + per-call-timeout path on `_run_with_tools`, and the JSONL log write policy.
   - `backend/app/models/api.py` — confirmed conventions for `Literal` aliases, flat-vs-inheriting request models, and validator placement.
3. Wrote the full review into §5 of the spec under `### @fp-architect Review`, replacing the `**Status:** PENDING` line and filling in Findings + Verdict + Conditions sections. Did NOT touch the `### @fp-data-reviewer Review` block.
4. Resolved Decision #1: **ReportLab Platypus**, confirmed.
5. Identified one spec gap that requires both a spec edit and a code change (Concern G1 — `generate_chat_async` lacks `timeout_s` and `response_format` parameters).
6. Identified five additional spec-text-only concerns (A2, A3, R1, M1, G3) and one follow-up flag (F2 — Ollama cold-call risk on demo day).

## Decisions Made

| # | Decision | Rationale |
|---|---|---|
| D1 | Decision #1 closed: **ReportLab Platypus** | Sample PDFs at `docs/specs/design/feature-pdf-report-exports-{mybuild,comparison}-sample.pdf` already prove every required primitive works; pure Python avoids a second Chromium spawn surface alongside `wrapped_renderer.py`; deterministic byte output is what "no temp files" actually requires. |
| D2 | `Response(content=bytes, ...)` over `StreamingResponse` | ReportLab returns a finished `bytes` blob (50KB–800KB target). Wrapping it in a fake stream adds complexity without latency benefit. Mirrors `wrapped.py:152` precedent. |
| D3 | Router mounted at empty prefix in `main.py` (like `builds_collection.router`) | Router covers both `/build/{id}/pdf` and `/builds/compare/pdf` namespaces; mounting under `prefix="/build"` would force the comparison endpoint into a different router and split the surface. |
| D4 | Status set to CHANGES REQUESTED (not REJECTED) | All concerns are mechanical / cosmetic. None invalidate the architecture. The biggest one (G1) is a 30-line touch on `gemma_client.py` plus a spec-text update — not a six-week rewrite. |
| D5 | Concern G1 must be resolved before APPROVAL | The spec says "6s timeout, JSON-mode" but neither is plumbed through `generate_chat_async`. Without resolving this, the static fallback path won't fire fast enough to honor the <15s p95 budget — student waits ~3 minutes on a hung Ollama call. |

## Rationale Highlights

- **Why APPROVE-with-conditions instead of REJECT?** Architecture is structurally sound. Service decomposition (`pdf_export` / `pdf_questions` / `pdf_copy`) cuts at the right boundaries. Zone discipline is preserved (read-only consumer of `Build`; no Bronze / Silver / Gold / MCP changes). Single Gemma call with static fallback aligns with `feedback_scoped_llm_contexts.md`. The `report_gen.py` (committed audit trail) and PDF byte-stream (no PII to disk) split cleanly per Decision #2. Issues are at the contract-detail layer, not the architecture layer.

- **Why is G1 the load-bearing concern?** Because the spec's stated Gemma posture ("6s timeout, JSON-mode, fallback on any failure") is the contract that makes the <15s p95 success criterion hold. If `generate_chat_async` doesn't honor `timeout_s`, the fallback can't fire in time and the success criterion silently fails on Ollama in the field. Catching this in the spec phase costs ~30 lines of `gemma_client.py`; catching it after implementation costs a regression cycle with @test-writer.

- **Why drop `StudentNameInput`?** Reading the existing `api.py`: every other request model in the file is flat (no inheritance). Repo-wide consistency wins over micro-DRY for a single-field re-use. Future-self reading `api.py` should not have to know whether a request inherits from a single-field base — declare and move on.

- **Why call the F2 (Ollama cold-call) risk a follow-up rather than a spec condition?** Because the warm-up nudge belongs in `lifespan` (where Iceberg metadata is already warmed), not in this spec. Filing it as a follow-up keeps this spec's scope tight against the May 18 deadline.

## Artifacts Produced

- §5 `### @fp-architect Review` of `docs/specs/feature-pdf-report-exports.md` filled in: Status, System Context, Data Flow Analysis, Contract Review, Findings (Sound + Concerns + Blockers), Verdict (CHANGES REQUESTED), and seven numbered Conditions.
- This session log at `docs/sessions/2026-05-06-architect-feature-pdf-report-exports.md`.

## Handoff

- Status entering: ARCH REVIEW
- Status exiting: ARCH REVIEW with CHANGES REQUESTED
- Next agent: spec author (or human routing the conditions). Conditions 2–6 are spec-text edits; condition 1 (G1) requires both a spec edit and a planned code change to `backend/app/services/gemma_client.py`.
- After conditions are reflected, request architect re-review. APPROVAL is contingent on conditions 1–6 being addressed.
- @fp-data-reviewer review (running in parallel) is untouched and still owed.

---

## Round 2 (re-review) — 2026-05-06

**Spec Status entering re-review:** ARCH REVIEW (CHANGES REQUESTED applied to §1–§4 by spec author)
**Spec Status exiting re-review:** ARCH REVIEW — APPROVED by @fp-architect

### Scope of round 2

Verification pass only. Confirm each of the 6 round-1 conditions (G1, A2, A3, R1, M1, G3) is addressed in §1–§4, and assess whether the data reviewer's break-even Blocker resolution (option b: `debt_to_earnings_annual` rendered as percent) and the Decision #9 QR cut introduce any architectural concerns missed in round 1.

### Verification results

| # | Condition | Where addressed in §1–§4 | Verdict |
|---|---|---|---|
| G1 | `gemma_client.generate_chat_async` extended with `timeout_s` + `response_format` | §4 File Changes line 485 (new Modify row); `pdf_questions.py` docstring lines 608–611 | Resolved |
| A2 | Commit to `Response(content=bytes, ...)`, NOT `StreamingResponse` | §2 Constraints line 185 (explicit "Not StreamingResponse" callout) | Resolved |
| A3 | Router catches ReportLab, re-raises as `HTTPException(500)` so CORSMiddleware fires | §4 line 489 + router stub lines 743–745; new P0 test at line 831 | Resolved |
| R1 | Router prefix `""`, tag `["PDF"]` capitalized | Router stub line 731 | Resolved |
| M1 | Drop `StudentNameInput`; flat models; `RiskLevel` near `AskScopeKind` | §4 lines 510–532 (placement callout + flat models with inline `student_name`) | Resolved |
| G3 | Every `gemma_path` value emits one `logs/gemma.jsonl` record | §4 line 487 + Gemma-touching surfaces line 774 + P0 test line 827 | Resolved |

### Round-2 delta assessment

- **Break-even cell → `debt_to_earnings_annual` percent (data reviewer Blocker, option b chosen):** clean. Field already on `CareerOutcome` and already rendered on `FinancesCard.tsx`. PDF and on-screen surface stay in sync. No new boundary crossings, no new computation, no new pipeline ripple. Single-source-cost rule preserved (`published_cost_4yr` still anchors cell 1). New P1 test enforces the formatter. No round-2 architectural concerns.
- **QR code cut (Decision #9 revised):** strict scope reduction. Removes the planned `qrcode[pil]` dep, removes a service kwarg (`public_app_base_url`), removes a footer-callback drawing path, removes the missing-`/build/:build_id`-route concern raised by the data reviewer. My round-1 Concern A1 lock-the-dep recommendation is now moot. Two stale references remain — a "Mocked QR code library" bullet at §4 Test Data Requirements (line ~851) and brief sample/reference mentions in §3.10. Flagged for spec-author cleanup as non-blocking; nothing breaks if not removed before implementation.

### Decisions Made (round 2)

| # | Decision | Rationale |
|---|---|---|
| R2.D1 | Verdict elevated from CHANGES REQUESTED → APPROVED | All six round-1 conditions verified resolved at the spec text level. No new architectural concerns from the data reviewer's option (b) resolution or the QR cut. |
| R2.D2 | Stale "Mocked QR code library" bullet at §4 Test Data Requirements flagged as non-blocking cleanup | Removing it would tighten the test-writer's instructions, but its presence does not invalidate any other contract or test. Not worth holding the spec for. |
| R2.D3 | Did NOT re-open Concern A1 (dep lock) | The recommended `qrcode[pil]` lock is now moot; only `reportlab>=4.2.0,<5.0.0` remains, and §4 File Changes line 484 already pins it. No further architectural action. |

### Rationale Highlights

- **Why APPROVED rather than another round of CHANGES REQUESTED?** Every round-1 condition was textually addressed and the changes are mechanically correct (signatures, location, contracts all verified by reading the spec). The data reviewer's option (b) routes through an existing field — it does not introduce any new architecture. The QR cut is a strict reduction in surface area. There is no remaining work that requires an architectural decision before implementation can begin.
- **Why mention the stale "Mocked QR code library" bullet at all?** It is the only artifact of round-2 churn that could mildly confuse the test-writer downstream. Calling it out costs nothing and saves a future agent a search.
- **What I did NOT verify in round 2:** the data reviewer's round-2 acceptance of option (b), the prompt design / JSON schema for the Gemma call (owned by @fp-copywriter and @genai-architect during DESIGN VISION), and the cold-Ollama warm-up follow-up (deferred per round-1 F2). Those remain owned by their respective agents.

### Artifacts Produced (round 2)

- §5 `### @fp-architect Review` of `docs/specs/feature-pdf-report-exports.md`: appended a `#### Round 2 (re-review)` subsection with verification table, round-2 delta assessment, APPROVED verdict, and a single non-blocking cleanup flag. Round-1 findings preserved verbatim above the new heading.
- This session log update under "Round 2 (re-review)".

### Handoff

- Status entering: ARCH REVIEW (CHANGES REQUESTED applied)
- Status exiting: ARCH REVIEW — APPROVED by @fp-architect
- Next agent: @fp-data-reviewer round 2 (re-verify the break-even resolution against option b). Once that clears, the spec proceeds to DESIGN VISION (visionary + copywriter + genai-architect).
- No further architect review needed unless a downstream agent introduces a new architectural change.
