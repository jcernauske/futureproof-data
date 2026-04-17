---
name: fp-spec-writer
description: Draft FutureProof specs following the project's §1–§11 skeleton, Claude Code Prompt calibration, and agent pipeline conventions. Use when asked to write, draft, or scope a new FP spec for a feature, bugfix, refactor, performance work, test coverage, tech debt, or spike. Triggers on "write a spec", "draft a spec", "new spec", "scope this out", "draft a spec for".
---

# fp-spec-writer

Draft a new FutureProof spec file in `docs/specs/`. This skill **drafts** specs (leaves status `DRAFT`); it does not execute them. For execution — the multi-agent pipeline that turns a draft into shipped code — use the existing `spec-workflow` skill instead.

---

## Step 1 — Read the authoritative sources

Every invocation starts by reading these two files in full. They are kept current in the repo; do **not** reinvent them.

1. `docs/specs/_TEMPLATE.md` — the §1–§11 skeleton, Claude Code Prompt block, status progression, lightweight variant.
2. `docs/specs/SPEC_GUIDELINES.md` — principles, file-naming patterns, prompt weight calibration, agent quick reference, author discipline rules.

If either file is missing, stop and tell the user — something upstream is broken.

## Step 2 — Gather intent

Before drafting, confirm the following with the user via **AskUserQuestion** (one batched call with 2–4 questions). Skip questions whose answers are already obvious from the conversation.

1. **Spec filename** — must follow `SPEC_GUIDELINES.md` naming (`feature-*`, `bugfix-*`, `refactor-*`, `test-coverage-*`, `performance-*`, `tech-debt-*`, `spike-*`). Propose a default; offer 1–2 alternatives.
2. **Prompt weight** — Lightweight / Standard / Full. Use the decision signals in `SPEC_GUIDELINES.md` ("Claude Code Prompt Calibration" section). If signals point to one weight clearly, state the recommendation and ask only if you're genuinely uncertain.
3. **Any scope-limiting decisions** — what is explicitly OUT of this spec. Captures future work that a reader might expect to be in scope.

Do not ask about implementation details the spec itself is meant to propose. Ask about *scope and framing*, not engineering choices.

## Step 3 — Draft the spec

Copy the skeleton from `_TEMPLATE.md` into the target file at `docs/specs/<chosen-name>.md` and fill it in. Order of authoring matters:

### 3a. Claude Code Prompt (authored first)

This is the most-used section of the finished spec. Tailor it to the chosen prompt weight using the templates in `SPEC_GUIDELINES.md` ("Claude Code Prompt Calibration"):

- **Full pipeline:** `ARCH REVIEW → DESIGN VISION → IMPLEMENTATION → TESTING → DESIGN AUDIT → CODE REVIEW → VERIFICATION → COMPLETION`
- **Standard:** `IMPLEMENTATION → TESTING → CODE REVIEW → VERIFICATION → COMPLETION`
- **Lightweight:** `IMPLEMENTATION → Run all tests → COMPLETION`

Include build accountability wording ("If build breaks, YOU fix it, max 3 attempts") in Standard and Full prompts. Reference the correct agents at each step using the table in `SPEC_GUIDELINES.md` — never invent agent names.

### 3b. §1 Feature Description

- Overview: 1–2 sentence summary.
- Problem Statement: what's broken / missing, why this is on the docket now.
- Success Criteria: checklist of observable outcomes, not implementation steps. One criterion per line.

### 3c. §2 Design Decisions

Decision Log table with the non-obvious calls: *what was decided, why, what alternatives were considered and rejected.* A reader six months from now will ask "why not X?" — this table is the answer.

Include an explicit **Out of Scope** list of things nearby in the design space that were intentionally excluded. Park them as future specs.

### 3d. §3 UI/UX Design

- **Backend-only specs:** mark `SKIPPED (backend-only spec)` and move on.
- **UI specs:** leave as a stub for `@fp-design-visionary` to fill in during the DESIGN VISION step. Note what screens/components are in scope and reference Brightpath design tokens by name (per `SPEC_GUIDELINES.md` §3 tips). Do not invent pixel values here — that's the visionary's job.

### 3e. §4 Technical Specification

This is the longest section and the one implementers actually work from. It must contain:

1. **Architecture Overview** — one paragraph on how this fits into the existing codebase and which modules are touched.
2. **File Changes** table — every file: absolute path, action (Create / Modify / Delete), one-sentence description. Favor exactness over breadth — if you don't know a file will change, leave it out.
3. **Data Model Changes** — new Pydantic models with full type signatures, Iceberg schema changes with full field tables, new DuckDB/MCP tables.
4. **Service Changes** — new modules, new public function signatures (type-annotated), dependency changes.
5. **Testing Impact Analysis** — required for every code-touching spec. Subsections:
   - *Existing Tests at Risk* — table: test file, test name, risk level (High/Med/Low), reason.
   - *Authorized Test Modifications* — tests the implementer is explicitly allowed to change.
   - *Confirmed Safe* — tests that must NOT break. If they fail, escalate.
   - *New Tests Required* — P0 / P1 / P2 priority table.
   - *Test Data Requirements* — fixtures, mocks, env state.

### 3f. Gemma-touching work (extra discipline)

If the spec modifies any call site of `gemma_client.generate` or `gemma_client.generate_chat`, also include:

- Fallback behavior per call site (every existing Gemma caller has a deterministic fallback — don't regress them).
- Verification that `logs/gemma.jsonl` still captures every call.
- Behavior under both `INFERENCE_BACKEND=ollama` and `INFERENCE_BACKEND=openrouter`.
- Rate-limit / concurrency considerations for the cloud demo.

### 3g. §5 through §11 (placeholders)

Leave these as `PENDING` stubs with the agent/status callouts from `_TEMPLATE.md`. They get filled in during spec execution, not during drafting:

- §5 Architecture Review — `PENDING` or `SKIPPED` per prompt weight.
- §6 Implementation Log — `PENDING`.
- §7 Test Coverage — `PENDING`.
- §8 Reviews (Design Audit + Code Review) — `PENDING` / `SKIPPED` per weight.
- §9 Verification — `PENDING` (template tables intact).
- §10 Discussion — empty block.
- §11 Final Notes — `Human Review: PENDING`.

### 3h. Metadata header

- `Status: DRAFT` always.
- `Created: <today's date ISO>` and `Last Updated: <today's date ISO>`.
- `Author: <human name + Claude Code>` — ask the user if their name isn't already in memory.
- `Blocked By: —` unless the user has named blockers.
- `Related Specs:` list any specs in `docs/specs/` or `docs/specs/completed/` the reader should read first.

## Step 4 — Author discipline checklist (from `SPEC_GUIDELINES.md`)

Before handoff, self-check:

- [ ] Every new interface in §4 has full type hints (no bare `Any`).
- [ ] Every Iceberg / DuckDB table change documents the full schema.
- [ ] Every file path in §4 is absolute (`backend/app/...`, `frontend/src/...`).
- [ ] Every test reference in §4 includes the test file path + test function name.
- [ ] Dates are ISO (`YYYY-MM-DD`).
- [ ] `CIPCODE` is referenced as a string type if present, never float (project rule from `CLAUDE.md`).
- [ ] `PrivacySuppressed` handling mentioned if College Scorecard data is touched.
- [ ] Status header left as `DRAFT`.
- [ ] Claude Code Prompt is copy-paste ready — the user should be able to paste it into a fresh session and have the spec execute.

## Step 5 — Handoff

Report back to the user with:

1. The spec file path.
2. The prompt weight chosen and a one-sentence justification.
3. What's explicitly out of scope (from §2).
4. The next action they can take (typically: "when ready, run the Claude Code Prompt in §0 to kick off the pipeline").

Do **not** auto-invoke `@fp-architect`, `@fp-design-visionary`, or any other agent. Drafting and executing are separate phases — that's what makes specs reviewable.

## What this skill is NOT

- It is not `spec-workflow` — that skill runs the multi-agent pipeline to turn a `DRAFT` into `COMPLETE`. This one produces the draft.
- It is not a copy of `_TEMPLATE.md` — the template is the source of truth. This skill points to it so template edits propagate automatically.
- It is not a free pass to skip the Testing Impact Analysis. Every code-touching spec gets one. No exceptions.
