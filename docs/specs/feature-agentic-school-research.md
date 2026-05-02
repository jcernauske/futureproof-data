# Feature: Agentic Web-Enriched School Research

## Claude Code Prompt

```
Read the spec at docs/specs/feature-agentic-school-research.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review §1–§4 (system architecture, data flow,
     Brightsmith integration, Gemma function calling orchestration, API contracts,
     Pydantic models, DuckDB schema additions, async job runner design).
   - This spec touches Gemma orchestration. Also invoke @genai-architect to
     review the prompt design, scoped tool registry, loop guardrails, and
     fallback behavior. Findings to §5.
   - This spec does NOT touch Bronze/Silver/Gold pipelines. SKIP @fp-data-reviewer.
   - Both write findings to §5 (Architecture Review).
   - If APPROVED: proceed to step 2.
   - If CHANGES REQUESTED (Significant): STOP, alert human.
   - If REJECTED (Blocker): STOP, alert human.

2. PHASE 0 — VALIDATION SPIKE (BLOCKER for all subsequent phases)
   - Implement the spike script described in §4 "Phase 0 — Validation Spike".
   - Run on both INFERENCE_BACKEND=ollama and INFERENCE_BACKEND=openrouter.
   - Acceptance: Gemma completes a ≥4-step tool chain on at least one backend
     without looping or fabricating tool calls.
   - Record results in §6 with the full tool-call log per backend.
   - If BOTH backends fail → STOP, set status BLOCKED, escalate to human.
     Do NOT proceed to Phase A.
   - If only Ollama fails → record decision in §10, drop the local-laptop demo
     framing for the hackathon video, lean OpenRouter, proceed to Phase A.
   - If both succeed → proceed to Phase A.

3. DESIGN VISION
   - Invoke @fp-design-visionary to propose the premium /my-build "Research"
     section (tool-call chain visualization, citation rendering, loading/empty
     states). Visionary writes to §3 (UI/UX Design).
   - §3 becomes the pixel-perfect implementation target.
   - Reference Brightpath tokens by name. No hardcoded colors/spacing.

4. IMPLEMENTATION
   - Implement Phases A → B → C → D in order, as defined in §4.
   - BEFORE coding: review §4 Testing Impact Analysis thoroughly.
   - DURING coding: update only tests listed in "Authorized Test Modifications".
   - CRITICAL: If any test NOT in "Authorized Test Modifications" fails,
     STOP and escalate to human via §10.
   - Log all work to §6 (Implementation Log) with phase tags (Phase A / B / C / D).
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest) at the end
     of each phase to catch regressions early.
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts).
     If still broken after 3 attempts: escalate to human via §10.

5. TESTING
   - Invoke @test-writer to review the full spec.
   - @test-writer MUST review §4 Testing Impact Analysis.
   - Implement all tests listed in "New Tests Required" by priority (P0 first).
   - Backend tests: pytest in backend/tests/.
   - Frontend tests: vitest in frontend/src/**/*.test.ts(x).
   - Run ALL tests to catch regressions across the existing GemmaChat /
     AskGemma / build-creation flows.

6. DESIGN AUDIT
   - Invoke @fp-design-auditor for mechanical Brightpath token/pattern compliance
     on the new /my-build Research section.
   - Writes findings to §8 (Design Audit).
   - If CHANGES REQUIRED: route to implementer via §10.

7. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests.
   - Particular attention to: orchestration loop guardrails, secret handling
     for TAVILY_API_KEY, fail-closed behavior of WEB_SEARCH_ENABLED=false,
     job-state DB writes under concurrent build creation.
   - Writes findings to §8 (Code Review).
   - If APPROVED: proceed to step 8. If CHANGES REQUIRED: route to originator
     via §10. If BLOCKER: STOP, alert human.

8. VERIFICATION
   - Invoke @fp-builder to run full build verification.
   - Backend: ruff check, mypy, pytest.
   - Frontend: TypeScript, vitest, Vite production build.
   - Log results to §9 (Verification).
   - If all green AND Phase D demo polish is complete: mark status COMPLETE.

9. COMPLETION
   - Update top-level Spec Status to COMPLETE.
   - Check off all completed Success Criteria in §1.
   - Update §6 Implementation Log, §7 Test Coverage, §8 Reviews.
   - Generate report to reports/feature-agentic-school-research-YYYY-MM-DD.md.
```

---

## Status: DRAFT

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
| Created | 2026-05-01 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-05-01 (data-grid framing, per fp-product-partner) |
| Blocked By | Phase 0 spike acceptance (internal blocker, not external) |
| Related Specs | `docs/specs/feature-ask-gemma.md` (chat surface using Gemma), `docs/specs/cloud-gemma-deployment.md` (OpenRouter backend) |

---

## §1 Feature Description

### Overview
Demonstrate Gemma 4's headline capability — multi-turn function calling — by giving Gemma a scoped 5-tool kit (3 existing MCP data tools + new `web_search` + `fetch_url`) and an asynchronous research job that fires when a student creates a build. The job's findings render in a new "Research" section on `/my-build` (`BuildResultsScreen.tsx`) as: (1) a visible chain of tool calls, (2) a structured grid of ≤10 sourced data points (badges, pills, deltas, dated events) — the primary product wedge, and (3) a short synthesis paragraph that shows Gemma reasoning over what she found. Every claim cites a source. Gated by `WEB_SEARCH_ENABLED`; default off so existing demos and CI are unaffected.

### Problem Statement
The Gemma 4 Good hackathon (Kaggle / Google DeepMind, deadline 2026-05-18) judges on Gemma 4 capability. Today FutureProof's Gemma calls are single-turn summarizers — narratives, taglines, prompts that take a payload and return prose. That doesn't differentiate Gemma 4 from any LLM. Multi-turn function calling is Gemma 4's flagship capability, and the existing `generate_with_tools_loop` in `gemma_client.py` is dispatched at most once per call site (e.g. `soc_expansion`). We have not yet shown Gemma reasoning across multiple tool calls to combine structured (Gold zone) and unstructured (web) data.

Separately: students lack timely, decision-relevant context about the schools they are considering. Static College Scorecard data is 2–3 years stale and silent on recent events (layoffs of major employers, federal investigations, conference moves, program closures). The brochure won't surface a school's active Title IX investigation; the agent should.

### Success Criteria
- [ ] **Phase 0 spike passes:** `generate_with_tools_loop` completes a ≥4-step chain on at least one inference backend with the spike's mock toolset, no looping, no fabricated calls.
- [ ] `web_search` and `fetch_url` MCP tools exist, are pluggable across providers (Tavily / Brave / SearXNG), are unit-tested with mocked HTTP, and respect `WEB_SEARCH_ENABLED`.
- [ ] DuckDB cache tables (`web_search_cache`, `research_job`, `research_tool_call`) exist with full schemas and TTL enforcement.
- [ ] When `WEB_SEARCH_ENABLED=false`: no behavioral or visual change anywhere in the app. CI and existing demos pass identically.
- [ ] When `WEB_SEARCH_ENABLED=true` and a build is created: an async `research_job` is enqueued, runs Gemma against the 5 scoped tools, and persists tool-call log + final synthesis with citations. Job state machine: `pending → running → complete` or `pending → running → failed`.
- [ ] `/my-build` renders a new "Research" section showing: streaming/loading state if job is in flight; full visible chain of tool calls; **a data-point grid (≤10 cells, each with kind / label / value / optional direction / optional severity / optional date / citation chip)**; a short synthesis paragraph rendered below the grid with inline `[1]`-style citations linked to source URLs.
- [ ] **Data-point grid is the primary product wedge.** Each cell is one structured fact (e.g. accreditation status pill, enrollment 3yr delta, federal investigation badge, top-employer trend arrow). Variable length 0–10. If Gemma surfaces zero data points, the grid is omitted and the synthesis stands alone.
- [ ] **No new prose surfaces beyond the existing synthesis.** No "Pattern" sentence, no per-cell tooltips with paragraphs, no "Research did not find anything" copy.
- [ ] Job failure is silent to the student — `/my-build` falls back to existing layout with the Research section omitted, no error toasts.
- [ ] Same `(school_id, major_id)` does NOT re-trigger Gemma — second visit reads cache (TTL 30 days).
- [ ] Same `(provider, query, recency_days)` web_search does NOT re-hit Tavily — TTL 7 days.
- [ ] Demo path verified end-to-end on both Ollama and OpenRouter (or only OpenRouter if Phase 0 fails Ollama).
- [ ] Hero queries from §4 "Phase D — Demo Polish" all produce coherent multi-tool chains in the recorded demo.
- [ ] Edge-case queries (deaf education at small school, ambiguous "Indiana", brand-new program) do not crash; either produce a chain or fail gracefully.
- [ ] No content sanitization: prompts and tools do NOT filter scandal/lawsuit/investigation terms. (See feedback memory `feedback_no_sanitizing_negative_info.md`.) **Equally: prompt does NOT force good news, but does NOT exclude it either.** Symmetric data-honesty: surface what is there, neutrally.
- [ ] All claims in synthesis AND every data-point cell are cited; uncited assertions are a P0 test failure.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Multi-tool agentic synthesis (Tier 3), not pre-fetched summarization (Tier 1) | Hackathon judges on Gemma 4 capability; function calling is the flagship feature. Tier 1 reduces Gemma to a summarizer indistinguishable from any LLM. | Tier 1 rejected (no differentiation). Tier 2 (single-tool agent) rejected as half-measure. |
| 2 | Surface = background job triggered on build creation, rendered in `/my-build` (`BuildResultsScreen`) | Latency hidden by parallelizing with student's reading of build results. Single-build enrichment is a clean UX problem. | Compare mode (two-school picker) rejected — Jeff prefers single-build pattern. Ask Gemma chat extension deferred to a future spec. |
| 3 | Tool surface scoped to 5 tools (`get_school_programs`, `get_career_paths`, `get_occupation_data`, `web_search`, `fetch_url`) — NOT all 10 existing MCP tools | Function-calling quality degrades with tool list size. Cleaner reasoning, fewer "Gemma called the wrong tool" moments. Per-surface scoping pattern. | Exposing all 10 tools rejected (degradation risk). Building a "router" agent rejected (over-engineering for hackathon timeline). |
| 4 | Tavily as default web search provider | LLM-grounding native (returns ready-to-prompt snippets, not raw HTML), free tier 1k searches/mo, built-in domain filtering and recency. | Brave (rawer output, more post-processing). Serper/SerpAPI (Google scrapers, paywall handling). SearXNG (self-hosted, free, but ops burden). All abstracted behind `SearchProvider` interface — swappable without code changes. |
| 5 | `WEB_SEARCH_ENABLED=false` default | Fail-safe. CI must pass without internet, OPENROUTER_API_KEY must remain optional, existing demos must be unaffected. | Default-on rejected (breaks CI, leaks secrets, changes existing demo behavior). |
| 6 | DuckDB for cache + job state, in `backend/data/futureproof.duckdb` (existing app DB) | App state lives there already (builds, wrapped frames). Same connection pool. Avoid introducing sqlite or Redis as new dependencies for hackathon timeline. | Sqlite (extra dep). Redis (ops burden, ephemeral state risk). In-memory (loses cache across restarts, breaks demo prep). |
| 7 | Visible tool-call chain in `/my-build` (NOT hidden behind a "thinking…" pill) | Judges want to see Gemma working. Chain-of-tools UI is cinematic on demo video. Hiding it makes the demo look like any other LLM wrapper. | Hidden chain rejected. Optional toggle rejected (judges might miss the feature). |
| 8 | NO content sanitization, NO positive-framing prompts, NO term filtering | Student decision-making requires real information. A school under federal investigation vs. a similar-pentagon cheaper school is an obvious decision — but only if the student sees it. Sanitizing reverts FP to brochure copy and breaks the data-honest brand voice. Source quality (domain weighting) is the lever, not topic filtering. | Positive-framing prompt rejected. Term blocklist (`-scandal -lawsuit`) rejected as paternalistic and leaky. |
| 9 | Reuse existing `gemma_client.generate_with_tools_loop` rather than build new orchestration | Loop already implements wall-time cap, turn cap, semaphore, telemetry, transport-error handling. Building parallel orchestration is duplicate work. Spec adds: scoped tool registry, async job runner, persistence. | New orchestration loop rejected (duplicate, slower). Wrapping `soc_expansion`'s pattern rejected — that pattern is single-tool, not multi-tool. |
| 10 | Async job runner via FastAPI `BackgroundTasks` (not Celery / RQ / Redis) | Hackathon timeline. `BackgroundTasks` is sufficient for one-job-per-build-creation, ≤60s duration, no retries needed (failure is silent and student doesn't see it). Can swap for a queue post-hackathon. | Celery rejected (Redis dep, ops burden). RQ rejected (same). asyncio.create_task without persistence rejected (loses job state on restart, breaks /my-build polling). |
| 11 | Phase 0 spike is a BLOCKER, not "nice to have" | We are betting 6+ days of build on Gemma 4 multi-turn function calling working reliably. 4-hour spike de-risks the bet. If it fails on both backends, the entire Tier 3 thesis collapses and we pivot to Tier 1. | Skipping spike rejected (too much downside risk). |
| 12 | Spec covers all phases (A–D) even though we may not commit to D | Jeff explicit: "we are writing a spec, not committing to it — write the spec for the entire thing." Specs are reviewable artifacts; trimming phases hides design tradeoffs. | Phasing the spec into multiple files rejected (loses design coherence). |
| 13 | Output is **structured data-point grid + short synthesis prose**, not prose-only | App is already text-heavy; another paragraph adds marginal value. Grid is scannable in 3 seconds, every cell is a sourced fact tied to the build's major/cost/pentagon. Synthesis is kept (not dropped) because it is the artifact of Gemma's reasoning — judges should see her connect the data points. Bloomberg-terminal-card framing, not Wikipedia summary. | Pure prose synthesis rejected (marginal value, hype risk). Pure grid rejected (loses Gemma reasoning artifact). Adding a third "Pattern" sentence under the grid rejected — Jeff explicit "I just don't want MORE prose." |
| 14 | Data-point catalog (universal-first, conditional surface only when triggered) | Per fp-product-partner: 10 universal data points (investigations, accreditation, financial health, top-employer trend, enrollment trend, net-price-vs-CPI, recent campus events, career-market signal, alumni outcome receipt, COL-adjusted ranking) + 3 conditional (athletic conference, dominant local employer, visa policy). Variable-length grid (0–10), agent decides what to surface — UI does not reserve slots. | Fixed-slot grid rejected (forces empty cells). Conditional-always rejected (bloats grid for kids it doesn't apply to). |
| 15 | Symmetric data-honesty in prompt: don't soften bad news, don't exclude good news either | Jeff: "i am fine with good news, I just don't want to force good news. i just want news, good or bad." Calibration, not framing — counter to the agent's tendency to over-index on alarming hits when optimizing for "scannable." Distinct from sanitization (which is still banned per Decision #8). | Forced positive-framing rejected (Decision #8, brochure copy). Pure negative bias rejected (calibration error). |
| 16 | Single source of structured-output truth: Gemma must return JSON matching `ResearchResult` schema | Without schema constraint, Gemma writes prose and we lose the grid. Gemma 4 function-calling and JSON-mode adherence are different surfaces; one validates the other does not. Phase 0 spike must validate JSON adherence in addition to tool-call chain. | Post-processing prose to extract data points rejected as primary path (brittle, regex hell). Kept as documented Phase 0 fallback only. |

### Constraints
- **Hackathon deadline 2026-05-18.** 17 days from spec draft date. Spec sized accordingly.
- **No new infrastructure dependencies** beyond Tavily HTTP API. No Redis, no Celery, no separate worker process.
- **Both inference backends supported** (Ollama local + OpenRouter cloud) per existing `INFERENCE_BACKEND` pattern.
- **Secret handling:** `TAVILY_API_KEY` lives in `.env`, must never be logged, must never appear in any frontend response.
- **`/my-build` performance budget:** existing screen TTI must not regress. Research section renders independently (loading state if job still running).
- **Brightpath design system** for all new UI. Dark-first. No hardcoded tokens.
- **No Bronze/Silver/Gold pipeline changes.** This spec does not touch ingestors, transformers, or Iceberg tables.

### Out of Scope
- **Compare mode (two-school picker).** Earlier in design discussion. Deferred to a future spec.
- **Ask Gemma chat using the agentic loop.** Current `ask_gemma` service uses single-turn calls. Could be migrated to `generate_with_tools_loop` post-hackathon. Not in this spec.
- **All 10 MCP tools exposed to the research agent.** Only the 5 scoped tools listed. Adding tools later requires a new spec.
- **Per-user web search budget caps / billing alerts.** Tavily free tier (1k/mo) is sufficient for hackathon + demo. Production deployment will need a budget controller.
- **News article full-text fetch via headless browser.** `fetch_url` does straight HTTP GET + readability parse. JS-rendered pages get whatever the server returns — usually enough for a snippet, sometimes not. Acceptable for hackathon.
- **Translation / localization of research findings.** English only. Locale stays at the existing build level (narratives etc.); Research section is English regardless.
- **Persistence of tool-call telemetry beyond 30 days.** Cache TTL is the retention boundary.
- **Real-time streaming of tool calls to frontend (SSE / WebSocket).** Polling at /my-build load is sufficient given the ~30–60s job duration and the fact that the user is reading static build content during the wait. SSE would be nice, deferred.
- **Adversarial input filtering on `web_search` queries.** Gemma authors the queries; trust boundary is Gemma. We do not sanitize Gemma's queries before sending to Tavily (Tavily handles its own input validation).
- **Compliance / source verification beyond Tavily's own ranking.** No fact-checking layer. Citations link to source URLs and the student verifies.

---

## §3 UI/UX Design

> @fp-design-visionary fills this section BEFORE Phase C implementation begins. Below is the scope brief and the Brightpath token guidance the visionary works from.

### Scope
- A new "Research" section inserted into `BuildResultsScreen.tsx`. Position: below `BossBand`, above `CompareSchoolsPanel` (subject to visionary's call).
- Section is gated by `research.enabled` flag in the build response. When `false`, render nothing — no placeholder, no header, no skeleton.
- Three states: **loading** (job pending / running), **populated** (job complete with results), **silent failure** (job failed → render nothing, identical to gated-off).

### State 1 — Loading
- Visible immediately when `/my-build` mounts and `research.enabled === true` AND `research.status !== 'complete'`.
- Header: section title (visionary chooses copy in `frontend/src/i18n/strings.ts`).
- Body: animated tool-call placeholder list. Suggest 3 skeleton rows hinting at the chain to come. Brightpath plush/soft aesthetic.
- Polling cadence: 2s while `status === 'pending' | 'running'`. Stop on `complete` or `failed`. Hard cap on poll attempts (suggest 60 = 2min wall clock, longer than the 60s job timeout to absorb event-loop slack).
- Framer Motion: subtle pulse on skeletons.

### State 2 — Populated

Render order from top to bottom:

1. **Tool-call chain** — vertical timeline. Each entry: tool name (display label, not function name), single-line argument summary, single-line result preview, duration. Visionary owns iconography per tool family (data tool icon vs. web tool icon).

2. **Data-point grid** (the primary product wedge) — variable length 0–10 cells. Each cell is one of:
   - **`badge`** — count + label + opened-date (e.g. "1 OCR Title IX investigation, opened Mar 2025"). Severity color when applicable.
   - **`pill`** — single-status label (e.g. "Accreditation: ABET, reaffirmed 2024" / "Financial health: Stable" / "ERN-after-COL: top quartile"). Severity color.
   - **`delta`** — value + direction arrow + magnitude (e.g. "Net price: ▲14% over 3yr (CPI: 9%)" / "Boeing employment: ▼ layoffs Q1 2026"). Direction is up/down/flat.
   - **`event`** — single dated line (e.g. "President resigned amid donor revolt, Mar 2026" / "Indiana raised teacher pay floor to \$40k, July 2025").
   - **`number`** — single labeled stat (e.g. "37% of 2024 nursing grads placed at IU Health within 90 days").
   - **`sparkline`** — small inline trend graphic + delta caption (e.g. "Marketing enrollment 1,240 → 980 (−21% over 3yr)"). Use only when 3+ time points exist.

   Each cell carries its own citation chip linking to the corresponding source. No inline `[N]` markers in cell text — the citation chip is the affordance.

   Grid order is agent-chosen (severity/relevance, not alphabetical). Visionary owns visual layout: 2-column desktop, 1-column mobile, suggested.

3. **Synthesis paragraph** — short prose (3–6 sentences) rendered below the grid. This is Gemma's *reasoning*: how she connects the data points. Inline citations as `[1]`, `[2]` superscript-style links. Clicking a citation: jumps to the citation list at the bottom AND highlights the source row. The synthesis is kept (not replaced by the grid) because it is the artifact of Gemma's multi-step reasoning — the wedge that justifies the agent framing to judges.

4. **Citation list** at the section bottom — one row per cited source. Each row: domain favicon (when available), source title, publication date, full URL. External-link affordance.

Empty handling:
- Zero data points + non-empty synthesis: render synthesis only (no grid header, no empty grid).
- Non-empty data points + empty synthesis (rare — Gemma exhausted turns): render grid only, no synthesis section, no apology copy.
- Both empty (very rare — successful job with no findings): render the chain only. No fallback prose. Absence is information.

### State 3 — Silent failure
- Render nothing. No section header, no error message.
- Job failure is logged backend-side, never surfaced to student.

### Brightpath References (visionary fills with specifics)
- Background tier for the section card.
- Accent color for the timeline and citation links.
- Typography scale for synthesis body vs. tool-call rows vs. citation rows.
- Display vs. body vs. data fonts (per `DESIGN.md`).
- Spacing and motion presets.

### Responsive Behavior
- Desktop: chain on the left, synthesis on the right (visionary's call).
- Mobile: vertical stack (chain → synthesis → citations).

### Accessibility
| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| Research section root | `research-section` | region | "Research findings about your build" (visionary may revise) |
| Tool-call chain list | `research-chain` | list | "Steps the research agent took" |
| Each tool-call row | `research-chain-row-{idx}` | listitem | "Step {idx+1}: {tool name}" |
| Data-point grid root | `research-grid` | list | "Key facts about your build" |
| Each data-point cell | `research-grid-cell-{idx}` | listitem | "{label}: {value}" (visionary may revise per cell kind) |
| Per-cell citation chip | `research-grid-cite-{idx}` | link | "Source for {label}: {domain}" |
| Synthesis paragraph | `research-synthesis` | region | "Research synthesis" |
| Citation link (inline in synthesis) | `research-cite-{idx}` | link | "Source {idx}: {domain}" |
| Citation list row | `research-source-{idx}` | listitem | "{title}, {date}, {domain}" |
| Loading skeleton | `research-loading` | status | "Loading research findings" + `aria-live=polite` |

### Frontend Library Reference
- **Framer Motion** for the streaming-in animation of tool-call rows when transitioning loading → populated.
- **shadcn/ui** for the citation list rows and any expandable detail.
- No React Flow (this is a list, not a graph).
- No Recharts.

---

## §4 Technical Specification

### Architecture Overview

The feature splits cleanly into a backend pipeline and a frontend rendering layer, with five existing seams:

1. **MCP server (`src/mcp_server/futureproof_server.py`)** gains two new tools — `web_search` and `fetch_url` — surfaced through the existing `BaseMCPServer` mechanism.
2. **A new `SearchProvider` abstraction (`backend/app/services/search_provider.py`)** wraps Tavily / Brave / SearXNG behind a single async interface. Default provider selected via `WEB_SEARCH_PROVIDER` env var.
3. **DuckDB cache and job state** in the existing app DB at `backend/data/futureproof.duckdb`, accessed via `app.services.db`. Three new tables: `web_search_cache`, `research_job`, `research_tool_call`.
4. **An async research-job runner (`backend/app/services/research_job.py`)** is the orchestration layer. It uses the existing `gemma_client.generate_with_tools_loop` with a scoped tool registry built from `mcp_client.get_tool_openai_schema(...)` plus the two new web tools. Hooked into `routers/builds.py:create_build` via FastAPI `BackgroundTasks`.
5. **A new `/builds/{build_id}/research` endpoint** in `routers/builds.py` returns job state + results. Polled by `BuildResultsScreen`.

The existing `gemma_client.generate_with_tools_loop` already implements: turn cap, wall-time cap, semaphore-based concurrency control, transport-error handling, telemetry to `logs/gemma.jsonl`. The orchestration loop is reused as-is — no changes to `gemma_client.py` for the loop itself. The spec only adds: scoped tool dispatch, job persistence, and the prompt.

`WEB_SEARCH_ENABLED=false` short-circuits everywhere: `create_build` does not enqueue the job, `/builds/{build_id}/research` returns `{enabled: false}`, `BuildResultsScreen` reads `enabled === false` and renders nothing. The system is feature-flag-clean; flipping the var off restores today's behavior exactly.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `scripts/spike_gemma_multi_tool.py` | Create | Phase 0 spike A. Standalone script with 3 mock tools, runs `generate_with_tools_loop` against both backends, prints chain, asserts ≥4 tool calls without loops. |
| `scripts/spike_gemma_json_schema.py` | Create | Phase 0 spike B. Validates Gemma can return parseable `ResearchResult`-shape JSON after a tool-call chain. Acceptance criteria in §4 "Phase 0 — Validation Spike". |
| `backend/app/services/search_provider.py` | Create | `SearchProvider` Protocol + `TavilyProvider` impl + factory. Brave/SearXNG stubs that raise `NotImplementedError`. |
| `backend/app/services/web_tools.py` | Create | `web_search` and `fetch_url` implementations + cache layer. Returns Pydantic models for both. |
| `backend/app/services/research_job.py` | Create | Async job runner. Builds scoped tool registry, calls `generate_with_tools_loop`, persists tool calls + result. |
| `backend/app/services/research_prompt.py` | Create | System + user prompt for the research agent. No content filtering. |
| `backend/app/services/db.py` | Modify | Add migration: create `web_search_cache`, `research_job`, `research_tool_call` tables. |
| `backend/app/models/api.py` | Modify | Add `ResearchEnvelope`, `ResearchToolCallView`, `ResearchCitation`, `ResearchSynthesis` Pydantic models. |
| `backend/app/models/research.py` | Create | Internal models: `ResearchJob`, `ToolCallRecord`, `Citation`, `ResearchResult`, `JobStatus` enum. |
| `backend/app/routers/builds.py` | Modify | (a) `create_build` and `_build_stream` enqueue research job via `BackgroundTasks` when `WEB_SEARCH_ENABLED=true`. (b) Add `GET /builds/{build_id}/research` endpoint. |
| `src/mcp_server/futureproof_server.py` | Modify | Register `web_search` and `fetch_url` tools. Schemas exposed via existing schema mechanism. |
| `backend/app/services/mcp_client.py` | Modify | No structural change — the new tools are picked up automatically via `get_tool_openai_schema`. Verify tool name routing handles the two new tools. |
| `backend/.env.example` | Modify | Add `WEB_SEARCH_ENABLED`, `WEB_SEARCH_PROVIDER`, `TAVILY_API_KEY` with descriptive comments. |
| `backend/pyproject.toml` | Modify | Add `httpx` (likely already present — confirm) and `readability-lxml` (for `fetch_url`). |
| `frontend/src/api/research.ts` | Create | `getResearch(buildId): Promise<ResearchEnvelope>` typed client + polling helper. |
| `frontend/src/types/research.ts` | Create | TS types mirroring `ResearchEnvelope` and children. |
| `frontend/src/components/build-results/ResearchSection.tsx` | Create | Container component. Owns polling + state machine. |
| `frontend/src/components/build-results/ResearchChain.tsx` | Create | Tool-call timeline. |
| `frontend/src/components/build-results/ResearchGrid.tsx` | Create | Data-point grid. Renders ≤10 cells via per-kind sub-renderers (badge/pill/delta/event/number/sparkline). Each cell renders its own citation chip. |
| `frontend/src/components/build-results/ResearchSynthesis.tsx` | Create | Synthesis prose + inline citation rendering. Kept (not dropped) — see Decision #13. |
| `frontend/src/components/build-results/ResearchCitations.tsx` | Create | Citation list at section bottom. |
| `frontend/src/screens/BuildResultsScreen.tsx` | Modify | Mount `<ResearchSection buildId={build.build_id} />` at the position §3 specifies. |
| `frontend/src/i18n/strings.ts` | Modify | Add Research section copy keys (visionary owns final wording). |
| `backend/tests/services/test_search_provider.py` | Create | Unit tests for `TavilyProvider` with mocked HTTP, error paths, rate-limit handling. |
| `backend/tests/services/test_web_tools.py` | Create | Unit tests for `web_search`, `fetch_url`, cache hit/miss, TTL expiry, gated-off behavior. |
| `backend/tests/services/test_research_job.py` | Create | Job runner tests with mocked `gemma_client` and mocked `mcp_client`. Covers: success, transport failure, turn cap, wall-time cap, loop detection, gated-off no-op. |
| `backend/tests/routers/test_builds_research.py` | Create | Integration tests for `GET /builds/{build_id}/research` (pending / running / complete / failed / not-found / gated-off). |
| `backend/tests/conftest.py` | Modify | Add fixtures: `tmp_research_db`, `mock_tavily`, `mock_gemma_loop`, `enable_web_search`. |
| `frontend/src/components/build-results/ResearchSection.test.tsx` | Create | vitest covering: gated-off renders null, loading state, populated state, silent-failure renders null, polling cadence, polling stop on complete. |
| `frontend/src/components/build-results/ResearchChain.test.tsx` | Create | vitest: chain rendering, tool icon mapping, accessibility identifiers. |
| `frontend/src/components/build-results/ResearchGrid.test.tsx` | Create | vitest: per-kind renderer (badge/pill/delta/event/number/sparkline), citation chip per cell, agent-chosen ordering preserved, 0-cell case omits grid entirely, 10-cell case renders all. |
| `frontend/src/components/build-results/ResearchSynthesis.test.tsx` | Create | vitest: inline citation rendering, citation click → highlight, uncited claims pass through, empty synthesis omits component. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | Modify | Add tests for ResearchSection mount + gated-off behavior. Existing tests in "Authorized Test Modifications" — see Testing Impact Analysis. |

### Data Model Changes

#### Pydantic models (internal — `backend/app/models/research.py`)

```python
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class ToolCallRecord(BaseModel):
    """One step in Gemma's tool-call chain. Persisted to research_tool_call."""
    turn_index: int
    tool_name: str
    arguments: dict[str, Any]
    result_preview: str  # truncated to 500 chars for display
    result_size_bytes: int
    duration_ms: int
    error: str | None = None


class Citation(BaseModel):
    """One source surfaced by web_search and referenced in synthesis or grid."""
    citation_index: int  # 1-based, matches [1], [2] in synthesis text + grid cell chips
    title: str
    url: str
    domain: str
    published_date: str | None = None  # ISO; None if Tavily did not surface
    snippet: str  # original snippet returned by provider


class DataPointKind(str, Enum):
    BADGE = "badge"          # count + topic + opened-date (investigations)
    PILL = "pill"            # single-status label (accreditation, financial health, ranking)
    DELTA = "delta"          # value + direction + magnitude (price-vs-CPI, employer trend)
    EVENT = "event"          # single dated line (campus event, market signal)
    NUMBER = "number"        # single labeled stat (alumni outcome receipt)
    SPARKLINE = "sparkline"  # trend graphic + delta caption (enrollment 3yr)


class DataPointSeverity(str, Enum):
    INFO = "info"
    POSITIVE = "positive"    # neutral-good (e.g. accreditation reaffirmed)
    WARN = "warn"            # mild concern (e.g. enrollment down 5%)
    CRITICAL = "critical"    # decision-altering (e.g. open OCR investigation, distressed financials)


class DataPointDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    FLAT = "flat"


class ResearchDataPoint(BaseModel):
    """One scannable, sourced fact displayed in the grid.

    The agent decides kind, severity, and direction per cell. The
    frontend has a renderer per kind. Severity drives visual weight
    (color, icon); it is not a value judgment about the school.
    """
    kind: DataPointKind
    label: str                                # short, scannable (e.g. "Accreditation")
    value: str                                # main display value (e.g. "ABET, reaffirmed 2024")
    direction: DataPointDirection | None = None  # required for kind=delta
    severity: DataPointSeverity | None = None    # optional visual weight
    date: str | None = None                   # ISO YYYY-MM-DD when applicable
    citation_index: int                       # 1-based; every cell MUST cite (uncited cells are a P0 test failure)


class ResearchResult(BaseModel):
    """Final output of a successful research job.

    Both `data_points` and `synthesis` are populated when possible. Each
    can be empty independently — see §3 "State 2 — Populated" empty
    handling rules.
    """
    data_points: list[ResearchDataPoint]      # 0..10 cells, agent-ordered
    synthesis: str                            # 3–6 sentences with inline [N] citation markers
    citations: list[Citation]
    tool_calls: list[ToolCallRecord]
    total_duration_ms: int
    backend_used: Literal["ollama", "openrouter"]


class ResearchJob(BaseModel):
    """Persisted job state. One row per (build_id)."""
    build_id: str
    school_id: str
    major_cip: str
    status: JobStatus
    enqueued_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: ResearchResult | None = None  # populated only if status == COMPLETE
    failure_reason: str | None = None  # populated only if status == FAILED
```

#### Pydantic models (API surface — `backend/app/models/api.py`)

```python
class ResearchToolCallView(BaseModel):
    """Frontend-safe tool-call view. No internal IDs, no oversized fields."""
    turn: int
    tool: str
    args_summary: str  # one-line human summary of arguments
    result_preview: str  # already truncated
    duration_ms: int
    error: str | None = None


class ResearchCitation(BaseModel):
    """Frontend citation. Mirrors internal Citation 1:1 (already safe)."""
    index: int
    title: str
    url: str
    domain: str
    date: str | None = None


class ResearchDataPointView(BaseModel):
    """Frontend-safe data-point view. Mirrors internal ResearchDataPoint 1:1."""
    kind: str           # serialized DataPointKind
    label: str
    value: str
    direction: str | None = None     # serialized DataPointDirection
    severity: str | None = None      # serialized DataPointSeverity
    date: str | None = None
    citation_index: int


class ResearchSynthesis(BaseModel):
    text: str  # synthesis with [1]-style markers
    citations: list[ResearchCitation]


class ResearchEnvelope(BaseModel):
    """Response body for GET /builds/{build_id}/research."""
    enabled: bool  # WEB_SEARCH_ENABLED flag mirror
    status: JobStatus | None = None  # None when enabled=false
    chain: list[ResearchToolCallView] = Field(default_factory=list)
    data_points: list[ResearchDataPointView] = Field(default_factory=list)  # 0..10
    synthesis: ResearchSynthesis | None = None  # None when synthesis is empty
```

#### DuckDB schema additions (`backend/app/services/db.py`)

Three new tables in `backend/data/futureproof.duckdb`:

```sql
-- Per-build research job state
CREATE TABLE IF NOT EXISTS research_job (
    build_id        VARCHAR PRIMARY KEY,
    school_id       VARCHAR NOT NULL,
    major_cip       VARCHAR NOT NULL,        -- CIP stays string per project rule
    status          VARCHAR NOT NULL,         -- 'pending' | 'running' | 'complete' | 'failed'
    enqueued_at     TIMESTAMP NOT NULL,
    started_at      TIMESTAMP,
    completed_at    TIMESTAMP,
    synthesis       TEXT,                     -- final synthesis text or NULL
    backend_used    VARCHAR,                  -- 'ollama' | 'openrouter' | NULL
    failure_reason  VARCHAR,                  -- short reason or NULL
    -- Cache key: same (school_id, major_cip) within TTL serves prior result
    cache_key       VARCHAR NOT NULL          -- hash(school_id || ':' || major_cip)
);
CREATE INDEX IF NOT EXISTS idx_research_job_cache
    ON research_job(cache_key, completed_at);

-- Tool-call log per job
CREATE TABLE IF NOT EXISTS research_tool_call (
    build_id         VARCHAR NOT NULL,
    turn_index       INTEGER NOT NULL,
    tool_name        VARCHAR NOT NULL,
    arguments_json   TEXT NOT NULL,
    result_preview   TEXT NOT NULL,           -- truncated to 500 chars
    result_size_bytes INTEGER NOT NULL,
    duration_ms      INTEGER NOT NULL,
    error            VARCHAR,
    PRIMARY KEY (build_id, turn_index)
);

-- Citations per job (one row per cited source)
CREATE TABLE IF NOT EXISTS research_citation (
    build_id        VARCHAR NOT NULL,
    citation_index  INTEGER NOT NULL,
    title           VARCHAR NOT NULL,
    url             VARCHAR NOT NULL,
    domain          VARCHAR NOT NULL,
    published_date  VARCHAR,                  -- ISO YYYY-MM-DD or NULL
    snippet         TEXT NOT NULL,
    PRIMARY KEY (build_id, citation_index)
);

-- Data-point grid cells per job (0..10 rows per build)
CREATE TABLE IF NOT EXISTS research_data_point (
    build_id        VARCHAR NOT NULL,
    cell_index      INTEGER NOT NULL,        -- agent-chosen display order, 0-based
    kind            VARCHAR NOT NULL,         -- 'badge' | 'pill' | 'delta' | 'event' | 'number' | 'sparkline'
    label           VARCHAR NOT NULL,
    value           VARCHAR NOT NULL,
    direction       VARCHAR,                  -- 'up' | 'down' | 'flat' | NULL
    severity        VARCHAR,                  -- 'info' | 'positive' | 'warn' | 'critical' | NULL
    date            VARCHAR,                  -- ISO YYYY-MM-DD or NULL
    citation_index  INTEGER NOT NULL,        -- FK-by-convention into research_citation
    PRIMARY KEY (build_id, cell_index)
);

-- Web search cache (provider-agnostic)
CREATE TABLE IF NOT EXISTS web_search_cache (
    cache_key       VARCHAR PRIMARY KEY,      -- hash(provider || query || recency_days || domains)
    provider        VARCHAR NOT NULL,
    query           VARCHAR NOT NULL,
    recency_days    INTEGER,
    domains_json    TEXT,                     -- nullable; JSON array if domain filter applied
    response_json   TEXT NOT NULL,            -- raw provider response, JSON-encoded
    fetched_at      TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_web_search_cache_fetched
    ON web_search_cache(fetched_at);

-- URL fetch cache (deduplicated full-page fetches)
CREATE TABLE IF NOT EXISTS web_url_cache (
    url             VARCHAR PRIMARY KEY,
    content_text    TEXT NOT NULL,            -- readability-extracted plaintext
    fetched_at      TIMESTAMP NOT NULL,
    status_code     INTEGER NOT NULL
);
```

TTL enforcement is application-side (query checks `fetched_at` against `now - TTL`), not DuckDB-side. Cache invalidation utility: `python -m backend.app.services.web_tools clear-cache` for demo prep. Migration strategy: idempotent `CREATE TABLE IF NOT EXISTS` block runs at startup via the existing `db.py` connection bootstrap.

### Service Changes

#### `backend/app/services/search_provider.py`

```python
from __future__ import annotations
from typing import Protocol
from pydantic import BaseModel


class WebSearchHit(BaseModel):
    title: str
    url: str
    snippet: str
    published_date: str | None = None
    domain: str
    score: float = 0.0


class WebSearchResponse(BaseModel):
    provider: str
    query: str
    hits: list[WebSearchHit]


class SearchProvider(Protocol):
    name: str
    async def search(
        self,
        query: str,
        *,
        recency_days: int | None = None,
        domains: list[str] | None = None,
        max_results: int = 5,
    ) -> WebSearchResponse: ...


class TavilyProvider:
    name = "tavily"
    def __init__(self, api_key: str, http_client: Any | None = None) -> None: ...
    async def search(
        self,
        query: str,
        *,
        recency_days: int | None = None,
        domains: list[str] | None = None,
        max_results: int = 5,
    ) -> WebSearchResponse: ...


def get_provider() -> SearchProvider:
    """Reads WEB_SEARCH_PROVIDER + TAVILY_API_KEY from env. Returns a
    cached singleton. Raises RuntimeError if WEB_SEARCH_ENABLED is true
    but provider config is invalid."""
```

#### `backend/app/services/web_tools.py`

```python
from typing import Any
from app.models.research import Citation
from app.services.search_provider import WebSearchResponse


async def web_search(
    query: str,
    *,
    recency_days: int | None = 365,
    domains: list[str] | None = None,
    max_results: int = 5,
) -> dict[str, Any]:
    """Cached web search. Returns serializable dict for Gemma tool dispatch.
    Cache TTL: 7 days. Returns the same shape regardless of cache hit.
    If WEB_SEARCH_ENABLED is false, raises FeatureDisabledError — caller
    must check the flag before invoking."""


async def fetch_url(url: str) -> dict[str, Any]:
    """Cached URL fetch. Returns {url, content_text, status_code, cached}.
    Plaintext extracted via readability-lxml. Cache TTL: 7 days.
    Same FeatureDisabledError contract as web_search."""


class FeatureDisabledError(RuntimeError): ...
```

#### `backend/app/services/research_job.py`

```python
from typing import Any
from fastapi import BackgroundTasks
from app.models.research import (
    JobStatus, ResearchJob, ToolCallRecord, ResearchResult,
)
from app.models.career import Build


# Five tools surfaced to Gemma in this surface:
SCOPED_TOOL_NAMES = (
    "get_school_programs",
    "get_career_paths",
    "get_occupation_data",
    "web_search",
    "fetch_url",
)

# Loop guardrails (passed to gemma_client.generate_with_tools_loop)
MAX_TURNS = 8
MAX_WALL_TIME_S = 60.0


async def enqueue_research(
    build: Build,
    background_tasks: BackgroundTasks,
) -> None:
    """Idempotent enqueue. No-op if WEB_SEARCH_ENABLED=false.
    No-op if a complete job exists for (school_id, major_cip) within TTL —
    copies prior result rows under the new build_id instead of re-running.
    Otherwise inserts a pending row and schedules _run_job."""


async def _run_job(build_id: str) -> None:
    """The background task. Marks status=running, builds the scoped tool
    registry from mcp_client.get_tool_openai_schema for the 5 names,
    constructs the prompt from research_prompt, calls
    gemma_client.generate_with_tools_loop, persists tool_calls + result,
    marks status=complete or status=failed. Failure is silent to
    frontend — failure_reason is logged but never returned in API."""


async def get_research_envelope(build_id: str) -> "ResearchEnvelope":
    """Read job state + rows for the API endpoint. Returns enabled=false
    when flag is off. Otherwise returns full envelope."""
```

#### `backend/app/services/research_prompt.py`

```python
SYSTEM_PROMPT = """You are a research analyst. Given a student's college
and major selection, use the available tools to find decision-relevant
context the static data does not show. You have these tools:
get_school_programs, get_career_paths, get_occupation_data, web_search,
fetch_url.

Use the data tools first to ground in what we already know about the
school, major, and likely career outcomes. Then use web_search to find
recent context: notable employer trends, school-level news, industry
shifts that affect this career path. Use fetch_url to read a specific
source if a search snippet is incomplete.

Output two things, both required:

1. A list of 0–10 STRUCTURED DATA POINTS. Each is one scannable, sourced,
   dated fact. Prefer these kinds (universal — apply to any school and
   major):
     - Active federal/state investigations (kind=badge, severity=critical
       when count>0)
     - Accreditation status, program-level when possible (kind=pill,
       severity color-coded)
     - Financial health signal — bond rating, layoffs, program cuts
       (kind=pill, severity color-coded)
     - Top-employer concentration + 12-month trend (kind=delta per
       employer, direction=up/down/flat)
     - Program enrollment 3-year trend (kind=sparkline, direction)
     - Net price vs. CPI 3-year (kind=delta, direction)
     - Recent campus events ≤12 months — 0 to 3 (kind=event, dated)
     - Career-market signal tied to the SOC (kind=event, dated)
     - Alumni outcome receipt — single named, dated stat from a school
       outcomes report (kind=number)
     - Cost-of-living-adjusted earnings ranking among peer programs
       (kind=pill)

   Surface CONDITIONAL data points only when the school/major triggers
   them: athletic-conference move (D1 schools only), dominant local
   employer opening/closing facility (when one exists), visa/policy
   change (high-international-enrollment programs only).

   Every data point MUST cite a source by index. If a fact has no
   source, do not include it.

2. A SHORT SYNTHESIS of 3–6 sentences. This is your reasoning across the
   data points — how they connect, what pattern (if any) emerges. Cite
   sources with [1], [2] markers. Do not repeat data-point values
   verbatim — the grid already shows them. Do not editorialize. Do not
   add hedging or uncertainty disclaimers — the citations are the
   disclaimers.

VOICE — symmetric data-honesty:
- Do NOT soften negative information. A school under federal investigation
  should be surfaced as one. Layoffs at a top employer matter. Bond
  downgrades matter. Accreditation issues matter.
- Do NOT exclude positive structural facts when they exist. If
  enrollment is growing, accreditation was reaffirmed, the dominant
  employer is hiring, the financial outlook is stable — surface those
  too. Neutrality means the grid reflects what is there, in either
  direction.
- Do NOT force good news. If nothing positive surfaces, do not invent it.
  Likewise do not force bad news.
- Wire-service reporter voice. Facts, sources, dates. No commentary, no
  warnings, no encouragement.

OUTPUT FORMAT: When you are done with tool calls, return a single JSON
object matching this schema (no surrounding prose, no markdown fence):

{
  "data_points": [
    {
      "kind": "badge" | "pill" | "delta" | "event" | "number" | "sparkline",
      "label": "<short scannable label>",
      "value": "<main display value>",
      "direction": "up" | "down" | "flat" | null,
      "severity": "info" | "positive" | "warn" | "critical" | null,
      "date": "YYYY-MM-DD" | null,
      "citation_index": <1-based int into citations>
    }
  ],
  "synthesis": "<3-6 sentences with [1], [2] markers>",
  "citations": [
    {
      "citation_index": <1-based int>,
      "title": "<source title>",
      "url": "<full URL>",
      "domain": "<host>",
      "published_date": "YYYY-MM-DD" | null,
      "snippet": "<original snippet>"
    }
  ]
}

Stop searching when you have enough to populate the JSON. Do not exceed
8 tool calls."""


def build_user_prompt(school_name: str, major_label: str, top_career_soc: str | None) -> str:
    """One-shot user message describing the build."""
```

The prompt has:
- NO sanitization clauses, NO positive-framing requirements, NO term blocklist (Decision #8 / `feedback_no_sanitizing_negative_info.md`).
- A SYMMETRIC neutrality clause (Decision #15) — surface what is there, in either direction; do not force or exclude either polarity.
- Explicit JSON schema in-prompt (Decision #16) — the grid depends on parseable structured output. Phase 0 spike validates Gemma can produce this.

**Fallback if Gemma cannot produce JSON consistently:** documented in the Phase 0 spike acceptance below. Primary path is in-prompt JSON; fallback is post-processing prose with regex extraction (brittle, kept only as escape hatch).

#### `backend/app/routers/builds.py` changes

`create_build` (currently line 152) and `_build_stream` (currently line 243) gain a single line at the end of the success path:

```python
await research_job.enqueue_research(final_build, background_tasks)
```

`background_tasks: BackgroundTasks = BackgroundTasks()` is added as a FastAPI dependency on both endpoints.

New endpoint:

```python
@router.get("/{build_id}/research")
async def get_research(build_id: str) -> ResearchEnvelope:
    return await research_job.get_research_envelope(build_id)
```

Returns 200 with `{enabled: false}` when flag is off (NOT 404 — frontend checks `enabled`). Returns 200 with `{enabled: true, status: pending}` while running. Returns 200 with full envelope on complete. On `failed`, returns 200 with `{enabled: true, status: failed, chain: [], synthesis: null}` so the frontend can render-nothing. Never returns the `failure_reason` in the API.

#### `src/mcp_server/futureproof_server.py` changes

Add two new tools to the `FutureProofMCPServer`. Schemas follow OpenAI tool format already used by the server. The tool functions delegate to `backend.app.services.web_tools`, which is acceptable cross-package import (the backend already imports from `src/mcp_server` per CLAUDE.md "MCP Server" section: "The backend services can import directly from `src/mcp_server/` — same repo, same venv.").

```python
@self.tool(
    name="web_search",
    description="Search the public web for recent context about a school, "
                "employer, industry, or career topic. Returns snippets + URLs.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "recency_days": {"type": "integer", "default": 365},
            "domains": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional domain allowlist."
            },
            "max_results": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    },
)
async def web_search(query: str, recency_days: int = 365,
                     domains: list[str] | None = None,
                     max_results: int = 5) -> dict[str, Any]:
    from backend.app.services import web_tools
    return await web_tools.web_search(
        query, recency_days=recency_days,
        domains=domains, max_results=max_results,
    )

@self.tool(
    name="fetch_url",
    description="Fetch a specific URL and return its readable text content. "
                "Use after web_search when a snippet is incomplete.",
    parameters={
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    },
)
async def fetch_url(url: str) -> dict[str, Any]:
    from backend.app.services import web_tools
    return await web_tools.fetch_url(url)
```

#### Phase 0 — Validation Spike (`scripts/spike_gemma_multi_tool.py`)

```python
"""Phase 0 spike. Validates Gemma 4 multi-turn function calling.

Run manually:
    INFERENCE_BACKEND=ollama uv run python scripts/spike_gemma_multi_tool.py
    INFERENCE_BACKEND=openrouter uv run python scripts/spike_gemma_multi_tool.py

Acceptance: Gemma completes a >=4-step chain without looping or
fabricating tool calls. Prints chain on success, prints diagnostic on
failure.
"""

import asyncio
from app.services.gemma_client import generate_with_tools_loop

# Three mock tools that force a 4-step chain when used together
TOOLS = [
    {"type": "function", "function": {
        "name": "lookup_school", "description": "Look up a school by name",
        "parameters": {"type": "object",
                       "properties": {"name": {"type": "string"}},
                       "required": ["name"]}}},
    {"type": "function", "function": {
        "name": "lookup_employer", "description": "Look up an employer's recent news",
        "parameters": {"type": "object",
                       "properties": {"employer": {"type": "string"}},
                       "required": ["employer"]}}},
    {"type": "function", "function": {
        "name": "compare_outcomes", "description": "Compare two outcomes",
        "parameters": {"type": "object",
                       "properties": {"a": {"type": "string"},
                                      "b": {"type": "string"}},
                       "required": ["a", "b"]}}},
]


async def dispatch(tool_name: str, args: dict) -> str:
    # Deterministic mock responses that hint at the next call
    if tool_name == "lookup_school":
        return f"School {args['name']} top employer: Acme Corp"
    if tool_name == "lookup_employer":
        return f"{args['employer']} laid off 1000 in Q1 2026"
    if tool_name == "compare_outcomes":
        return f"Outcome A: {args['a']} beats B: {args['b']}"
    return "unknown"

async def main() -> None:
    text, log = await generate_with_tools_loop(
        system="You are a researcher. Use the tools to find context, "
               "then summarize.",
        user="Research School X. Look up the school, then look up the "
             "top employer's news, then compare outcomes for staying "
             "vs. switching, then summarize.",
        tools=TOOLS, dispatch=dispatch,
        max_turns=8, max_wall_time_s=60.0,
    )
    print(f"Final synthesis: {text}")
    print(f"Tool call log ({len(log)} steps):")
    for i, step in enumerate(log):
        print(f"  {i}: {step}")
    assert len(log) >= 4, f"FAIL: only {len(log)} tool calls"
    print("PASS")

if __name__ == "__main__":
    asyncio.run(main())
```

Spike acceptance criteria (BOTH must hold on at least one backend):

**A. Tool-call chain reliability:**
- ≥4 tool calls in the log
- No tool call repeats the exact same `(name, args)` pair
- No tool call references a tool name not in `TOOLS`
- Final response is non-empty

**B. JSON schema adherence (added per Decision #16):**

A second spike script `scripts/spike_gemma_json_schema.py` runs the loop with a system prompt that demands the `ResearchResult`-shape JSON output (subset: `data_points` + `synthesis` + `citations`) and asserts:
- The final response parses as JSON (no surrounding prose, no markdown fence required)
- The parsed object has the three top-level keys
- `data_points` is a list whose elements have all required fields and valid enum values
- Every `data_points[i].citation_index` references an entry in `citations`
- `synthesis` `[N]` markers all reference an entry in `citations`

**Result interpretation:**
- A passes + B passes (either backend) → proceed to Phase A on the strongest backend.
- A passes + B fails on both → proceed to Phase A but switch to the FALLBACK path: Gemma writes prose, a deterministic post-processing extractor parses data points by regex against a controlled vocabulary. Document the decision in §10. Adds ~0.5 day to Phase B.
- A fails on both → STOP, set status BLOCKED, escalate to human. The Tier 3 thesis collapses; pivot to Tier 1.
- Per-backend results recorded in §6 with the full chain log + the parsed JSON (or parse error) per backend.

### Gemma-Touching Discipline (per `SPEC_GUIDELINES.md`)

This spec adds new Gemma call sites and reuses an existing one. Discipline checklist:

- **Fallback per call site:** `_run_job` failure → job marked `failed`, frontend renders nothing. NO existing call sites are modified, so no existing fallback is at risk.
- **Telemetry:** `generate_with_tools_loop` already logs to `logs/gemma.jsonl`. Confirmed unchanged. Per-job timing logged separately to backend logger.
- **Both backends:** Spike validates both. Production code uses whichever `INFERENCE_BACKEND` is set. Both backends must complete a real research job in Phase D acceptance.
- **Rate-limit / concurrency:** `generate_with_tools_loop` uses an existing semaphore. New constraint: research jobs share that semaphore with all other Gemma callers. Acceptable for hackathon scale (one user at a time during demo). Documented in Decision #10.
- **No prompt sanitization:** Per Decision #8, no positive-framing layer.

### Testing Impact Analysis

> Searched `backend/tests/` and `frontend/src/` for tests that touch the modified files. Findings below.

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `backend/tests/routers/test_builds.py` (if exists) | All `create_build` tests | Med | New `BackgroundTasks` parameter on endpoint signature. FastAPI handles dep injection but tests calling the function directly need to pass `BackgroundTasks()`. |
| `backend/tests/services/test_gemma_client.py` | `test_generate_with_tools_loop_*` | Low | Loop is unchanged. Tests should pass without modification. Verify regardless. |
| `backend/tests/services/test_mcp_client.py` (if exists) | `test_get_tool_openai_schema` | Med | Two new tool names registered. Existing schema tests may assert on tool name list — update if so. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | All existing render tests | Med | New child component (`<ResearchSection>`) mounted. Existing tests must continue to pass with the gate off (default). |
| `frontend/src/App.test.tsx` | Routing tests | Low | No route changes. Should pass unchanged. |
| `backend/tests/services/test_ask_gemma.py` | All | Low | `ask_gemma` not modified. Should pass unchanged. |
| `backend/tests/services/test_set_your_course.py` | All | Low | `set_your_course` not modified. Should pass unchanged. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `backend/tests/routers/test_builds.py` | Add `BackgroundTasks()` to direct calls of `create_build` / `create_build_stream`. | Endpoint signature change is purely additive; FastAPI handles HTTP dep injection but in-process test calls must pass it. |
| `backend/tests/services/test_mcp_client.py` (if it asserts tool list) | Update assertion to include `web_search` and `fetch_url`. | Two new tools are correctly registered; the assertion is the canary. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | Update render assertions to allow `<ResearchSection>` mount. With gate off (default), `ResearchSection` returns null — should not break existing assertions. Verify and only modify if needed. | Defensive update only if existing tests are too strict on DOM shape. |

Any test failure NOT in this table is a regression — STOP and escalate per CLAUDE.md.

#### Confirmed Safe

These tests must NOT break:
- All tests in `backend/tests/services/test_ask_gemma_voice.py`, `test_gemma_voice_contract.py`, `test_set_your_course.py`, `test_career_pick_qna.py`, `test_career_tiering.py`, `test_skill_pool.py`, `test_next_steps.py`, `test_boss_fights.py`, `test_branch_tree.py`.
- All pipeline tests in `tests/raw/`, `tests/silver/`, `tests/gold/`, `tests/mcp/` (this spec touches MCP server but only adds tools — existing tool tests must pass).
- All frontend tests in `frontend/src/components/menu/` (GemmaChat, AskGemmaFab — separate Gemma surfaces, not modified).

If any of these break: STOP, escalate, do not "fix" silently.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/services/test_search_provider.py` | `test_tavily_search_success` | Mocked HTTP returns Tavily response → `WebSearchResponse` parses correctly. |
| P0 | `backend/tests/services/test_search_provider.py` | `test_tavily_search_5xx_raises` | Provider returns 500 → raises a typed error caller can catch. |
| P0 | `backend/tests/services/test_search_provider.py` | `test_tavily_search_no_api_key_raises` | Missing `TAVILY_API_KEY` with flag enabled → `RuntimeError` at provider construction. |
| P0 | `backend/tests/services/test_web_tools.py` | `test_web_search_gated_off_raises_disabled` | `WEB_SEARCH_ENABLED=false` → `FeatureDisabledError`. |
| P0 | `backend/tests/services/test_web_tools.py` | `test_web_search_cache_hit` | Same `(provider, query, recency, domains)` within TTL → no HTTP call. |
| P0 | `backend/tests/services/test_web_tools.py` | `test_web_search_cache_miss_writes_cache` | New query → HTTP fired, response cached. |
| P0 | `backend/tests/services/test_web_tools.py` | `test_web_search_cache_ttl_expired_refetches` | Cached entry older than 7 days → refetch. |
| P0 | `backend/tests/services/test_web_tools.py` | `test_fetch_url_cache_hit` | Same URL within TTL → no HTTP call. |
| P0 | `backend/tests/services/test_web_tools.py` | `test_fetch_url_4xx_returns_status` | 4xx URL → returned with `status_code`, not raised. |
| P0 | `backend/tests/services/test_research_job.py` | `test_enqueue_gated_off_noop` | Flag off → no DB row, no background task scheduled. |
| P0 | `backend/tests/services/test_research_job.py` | `test_enqueue_cache_hit_copies_result` | Existing complete job for same `(school, cip)` within TTL → new build_id rows copied, no Gemma call. |
| P0 | `backend/tests/services/test_research_job.py` | `test_run_job_success` | Mocked `generate_with_tools_loop` → status=complete, tool_calls + citations persisted. |
| P0 | `backend/tests/services/test_research_job.py` | `test_run_job_transport_failure` | Loop returns `("", [...])` → status=failed, `failure_reason` set, frontend envelope hides reason. |
| P0 | `backend/tests/services/test_research_job.py` | `test_run_job_turn_cap_hit` | Loop hits turn cap → status=complete with whatever Gemma produced (may be empty synthesis). |
| P0 | `backend/tests/services/test_research_job.py` | `test_run_job_loop_detection` | If two consecutive turns dispatch the same `(name, args)` → loop aborts with `failure_reason="loop_detected"`. |
| P0 | `backend/tests/services/test_research_job.py` | `test_scoped_tools_only` | Job is offered exactly the 5 scoped tool names — never the full 10. |
| P0 | `backend/tests/services/test_research_job.py` | `test_data_points_parsed_and_persisted` | Mocked Gemma returns the JSON schema from `research_prompt.SYSTEM_PROMPT` → data-point rows persist to `research_data_point` table with all fields. |
| P0 | `backend/tests/services/test_research_job.py` | `test_data_point_uncited_rejected` | Gemma returns a data point with `citation_index` not in citations → row rejected, logged as parse warning, job still succeeds with remaining valid points. |
| P0 | `backend/tests/services/test_research_job.py` | `test_data_point_invalid_kind_rejected` | Data point with `kind="opinion"` → rejected, others kept. |
| P0 | `backend/tests/services/test_research_job.py` | `test_data_point_grid_capped_at_10` | Gemma returns 15 data points → first 10 persisted, rest dropped, warning logged. |
| P0 | `backend/tests/services/test_research_job.py` | `test_json_parse_failure_fallback` | Gemma returns prose instead of JSON → fallback regex extractor invoked OR job marked failed (depending on Phase 0 spike outcome — implementer chooses per §10 decision). |
| P0 | `backend/tests/routers/test_builds_research.py` | `test_get_research_complete_returns_data_points` | Job complete with data points → envelope `data_points` is populated and ordered by `cell_index`. |
| P0 | `backend/tests/routers/test_builds_research.py` | `test_get_research_complete_zero_data_points` | Job complete with synthesis only, no data points → envelope `data_points` is empty list. |
| P0 | `frontend/src/components/build-results/ResearchGrid.test.tsx` | `test_zero_cells_omits_grid` | Empty `data_points` → `<ResearchGrid>` returns null. |
| P0 | `frontend/src/components/build-results/ResearchGrid.test.tsx` | `test_renders_each_kind` | One cell per `kind` → each renders via its kind-specific sub-renderer. |
| P0 | `frontend/src/components/build-results/ResearchGrid.test.tsx` | `test_cell_carries_citation_chip` | Every rendered cell has a `research-grid-cite-{idx}` link to the source URL. |
| P0 | `frontend/src/components/build-results/ResearchGrid.test.tsx` | `test_cell_order_preserved` | Cells render in API order (agent-chosen), NOT alphabetical or kind-grouped. |
| P0 | `frontend/src/components/build-results/ResearchSynthesis.test.tsx` | `test_empty_synthesis_omits_component` | Empty synthesis → component returns null (per §3 empty handling). |
| P0 | `backend/tests/routers/test_builds_research.py` | `test_get_research_gated_off_returns_disabled` | Flag off → 200, `{enabled: false}`. |
| P0 | `backend/tests/routers/test_builds_research.py` | `test_get_research_pending` | Job pending → 200, `{enabled: true, status: pending, chain: [], synthesis: null}`. |
| P0 | `backend/tests/routers/test_builds_research.py` | `test_get_research_complete` | Job complete → 200 with chain + synthesis + citations. |
| P0 | `backend/tests/routers/test_builds_research.py` | `test_get_research_failed_hides_reason` | Job failed → 200, no `failure_reason` field in response. |
| P0 | `backend/tests/routers/test_builds_research.py` | `test_get_research_unknown_build_returns_disabled` | Unknown `build_id` and flag on → 200, `{enabled: true, status: null}` (renders nothing). |
| P0 | `frontend/src/components/build-results/ResearchSection.test.tsx` | `test_gated_off_renders_null` | API returns `enabled: false` → component returns null, no DOM emitted. |
| P0 | `frontend/src/components/build-results/ResearchSection.test.tsx` | `test_loading_state_renders_skeleton` | Status pending → skeleton visible, polling started. |
| P0 | `frontend/src/components/build-results/ResearchSection.test.tsx` | `test_complete_state_renders_chain_and_synthesis` | Status complete → chain + synthesis + citations rendered. |
| P0 | `frontend/src/components/build-results/ResearchSection.test.tsx` | `test_failed_state_renders_null` | Status failed → component returns null, identical to gated-off. |
| P0 | `frontend/src/components/build-results/ResearchSection.test.tsx` | `test_polling_stops_on_complete` | Once complete arrives, no further fetches scheduled. |
| P0 | `frontend/src/components/build-results/ResearchSection.test.tsx` | `test_polling_stops_after_max_attempts` | After 60 polls, no further fetches even if still pending. |
| P1 | `frontend/src/components/build-results/ResearchSynthesis.test.tsx` | `test_inline_citation_renders_link` | Synthesis text with `[1]` → renders clickable link. |
| P1 | `frontend/src/components/build-results/ResearchSynthesis.test.tsx` | `test_citation_click_highlights_source` | Click `[1]` → corresponding citation row gets highlight class. |
| P1 | `frontend/src/components/build-results/ResearchChain.test.tsx` | `test_chain_renders_in_turn_order` | Tool calls render in turn-index order regardless of API ordering. |
| P1 | `frontend/src/components/build-results/ResearchChain.test.tsx` | `test_tool_icon_per_family` | Data tools get one icon, web tools get another. |
| P1 | `backend/tests/services/test_research_job.py` | `test_synthesis_uncited_claim_logged` | Synthesis with claims lacking `[N]` markers → logged as warning (not failure). |
| P2 | `backend/tests/services/test_search_provider.py` | `test_tavily_domain_filter_passed` | `domains=["nytimes.com"]` → request body contains the filter. |
| P2 | `backend/tests/services/test_search_provider.py` | `test_tavily_recency_passed` | `recency_days=30` → request body contains the recency. |
| P2 | `backend/tests/services/test_research_job.py` | `test_total_duration_recorded` | Job persists `total_duration_ms`. |
| P2 | `frontend/src/components/build-results/ResearchSection.test.tsx` | `test_locale_strings_used` | All visible text comes from `i18n/strings.ts`, no hardcoded strings. |

#### Test Data Requirements

- **Fixture: `tmp_research_db`** — fresh DuckDB at a tmp path with the three new tables created. Per-test isolation.
- **Fixture: `mock_tavily`** — monkeypatches the HTTP client used by `TavilyProvider`. Returns canned `WebSearchResponse` objects per query.
- **Fixture: `mock_gemma_loop`** — monkeypatches `gemma_client.generate_with_tools_loop` to return scripted `(text, log)` tuples. Allows scenario tests without LLM calls.
- **Fixture: `enable_web_search` / `disable_web_search`** — sets/unsets `WEB_SEARCH_ENABLED` for the test scope.
- **Canned data:** `tests/data/research/tavily_response_purdue_aerospace.json` (real-shape Tavily response for spike-validated query). Do not commit a real API response with PII; sanitize URLs/snippets if needed.
- **No real network calls in CI.** All HTTP mocked. Spike script is excluded from pytest collection (it's manual-run).

### Phasing — Implementation Order

Each phase ships independently green (lint + types + tests + build).

**Phase 0 — Validation Spike (BLOCKER, ~0.5 day)**
- `scripts/spike_gemma_multi_tool.py` (chain reliability — Acceptance A)
- `scripts/spike_gemma_json_schema.py` (structured-output adherence — Acceptance B)
- Run both on Ollama and OpenRouter
- Record results in §6 with full chain log + parsed JSON per backend
- Acceptance gate per Step 2 of Claude Code Prompt + the A/B matrix in §4 "Phase 0 — Validation Spike"

**Phase A — Web search foundation (~1.5 days)**
- `search_provider.py`, `web_tools.py` with full tests
- DuckDB cache tables migration in `db.py`
- Env var wiring + `.env.example` update
- MCP server registers `web_search` and `fetch_url`
- All P0 tests for these modules pass
- Phase exit: `python -c "import asyncio; from backend.app.services.web_tools import web_search; print(asyncio.run(web_search('test')))"` returns cached result on second call

**Phase B — Async research job runner (~2 days, +0.5 day if Spike B fails)**
- `research_job.py`, `research_prompt.py`, `models/research.py` (incl. `ResearchDataPoint`), `models/api.py` additions
- DuckDB job-state tables migration (incl. `research_data_point`)
- JSON-schema parsing + validation + per-cell rejection logic (or fallback regex extractor if Spike B failed)
- `routers/builds.py` enqueue hook + `GET /builds/{build_id}/research` endpoint
- All P0 tests for job runner + endpoint pass (including the data-point parsing tests)
- Phase exit: end-to-end manual run — create a build with flag on → poll endpoint → see chain + data points + synthesis in JSON. No frontend yet.

**Phase C — `/my-build` rendering (~2 days)**
- `frontend/src/api/research.ts`, `types/research.ts` (incl. `ResearchDataPointView`)
- `ResearchSection.tsx` + `ResearchChain.tsx` + **`ResearchGrid.tsx`** + `ResearchSynthesis.tsx` + `ResearchCitations.tsx`
- Per-kind sub-renderers in `ResearchGrid.tsx`: `BadgeCell`, `PillCell`, `DeltaCell`, `EventCell`, `NumberCell`, `SparklineCell` (sparkline can defer to a stub if pressed for time — render as delta)
- Mount in `BuildResultsScreen.tsx`
- All P0 + P1 frontend tests pass (including all `ResearchGrid.test.tsx` cases)
- @fp-design-visionary §3 implemented to spec
- Phase exit: hot-loaded build with flag on shows the section streaming → populated with grid + synthesis. Flag off shows no section. Zero-data-point case omits grid cleanly.

**Phase D — Demo polish (~1.5 days)**
- Hero queries validated end-to-end (suggest 3–5):
  - "IU Bloomington — Marketing"
  - "Purdue — Aerospace Engineering"
  - "Lamar — Deaf Education" (small school, niche program edge case)
  - "Western Governors — Cybersecurity" (online university edge case)
  - One school with active known recent public news (chosen at demo time to avoid stale spec data)
- Both `INFERENCE_BACKEND=ollama` and `INFERENCE_BACKEND=openrouter` verified against all hero queries
- Demo cache pre-warmed for video recording (use `clear-cache` utility to reset for live demo)
- Failure rehearsal: kill Tavily key mid-job → verify silent failure, no error toast, no broken UI
- Video script: chain-of-tools moment is the hero shot
- Phase exit: a fresh laptop with `git clone + uv sync + npm install + .env populated` reproduces the demo end-to-end

---

## §5 Architecture Review

### @fp-architect Review
**Status:** PENDING
#### Findings
[Filled in by @fp-architect — system architecture, data flow, Gemma orchestration design, async job runner, API contracts, Pydantic models, DuckDB schema additions]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

### @genai-architect Review
**Status:** PENDING
#### Findings
[Filled in by @genai-architect — research_prompt.py system prompt design, scoped tool registry, loop guardrails (turn cap, wall time, loop detection), backend-agnostic behavior, fallback under transport failure]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

### @fp-data-reviewer Review
**Status:** SKIPPED — this spec does not modify Bronze/Silver/Gold pipelines, ingestors, transformers, Iceberg tables, stat formulas, or boss-fight data.

---

## §6 Implementation Log

**Status:** PENDING

### Phase 0 — Spike Results
| Backend | Result | Tool calls | Notes |
|---------|--------|-----------|-------|
| ollama | | | |
| openrouter | | | |

### Files Modified
| File | Phase | Change Summary |
|------|-------|----------------|

### Deviations from Spec
[Any divergence from §3/§4 and why]

### Build Accountability Log
| Attempt | Phase | Result | Error | Fix Applied |
|---------|-------|--------|-------|-------------|

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
| pytest (pipeline) | | | | |
| vitest | | | | |

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@fp-design-auditor)
**Status:** PENDING
[Brightpath token compliance for the new Research section. Dark-first enforcement. Responsive behavior. Accessibility identifiers.]

### Code Review (@faang-staff-engineer)
**Status:** PENDING
#### Findings
[Particular attention areas listed in Claude Code Prompt Step 7]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

---

## §9 Verification

**Status:** PENDING

### Backend (@fp-builder)
| Check | Result |
|-------|--------|
| Lint (ruff) | |
| Type check (mypy) | |
| Tests (pytest) | |

### Frontend (@fp-builder)
| Check | Result |
|-------|--------|
| TypeScript | |
| Tests (vitest) | |
| Production build (Vite) | |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|

---

## §10 Discussion

```
[YYYY-MM-DD HH:MM] @source-agent → @target-agent
Message content.
```

---

## §11 Final Notes

**Human Review:** PENDING

[Final thoughts, lessons learned, follow-up items.]
