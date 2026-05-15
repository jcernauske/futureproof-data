# Feature: Gemma Eval Harness

## Claude Code Prompt

```
Read the spec at docs/specs/gemma-eval-harness.md in its entirety.

This is a hackathon-deadline-driven addition responding to a simulated judge gap:
"No eval methodology — 10 Gemma surfaces, zero systematic eval." Reality is 20
surfaces (see §1 inventory). The work is building golden sets, scorers, a runner,
and a results doc — NOT changing any production code paths.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review §4 (harness architecture, surface adapters,
     scorer interfaces, results schema)
   - Invoke @genai-architect to review §4.5 (LLM-as-judge prompts, rubric design,
     calibration approach)
   - Both write findings to §5
   - If APPROVED: proceed
   - If CHANGES REQUESTED: STOP, alert human

2. GOLDEN SET CONSTRUCTION (P0 surfaces only — see §2 priority tiers)
   - Build labeled cases.jsonl files for each P0 surface
   - Cases must cover happy path, edge cases, and adversarial inputs
     ("deaf education" rule from CLAUDE.md applies — labels must include
     out-of-distribution majors, fuzzy school names, ambiguous intents)
   - Log progress to §6

3. IMPLEMENTATION
   - Build runner, scorers, and surface adapters per §4
   - Instrument all 20 surfaces with latency + token logging (read-only;
     no behavior change)
   - Generate baseline results to eval/results/baseline-YYYY-MM-DD/
   - Log work to §6

4. TESTING
   - Invoke @test-writer to write tests for scorers (schema validator,
     exact-match, rubric scorer parsing)
   - Scorers are the eval ground truth — they need bulletproof unit tests
   - Run full backend pytest + frontend vitest. No production code paths
     should regress.

5. CODE REVIEW
   - Invoke @faang-staff-engineer to review eval runner + scorers
   - Particular attention to: rubric scorer prompt-injection resistance,
     latency-instrumentation overhead, results-file race conditions
   - Writes findings to §8

6. VERIFICATION
   - Invoke @fp-builder for full build verification
   - Add `make eval-p0` and `make eval-all` targets, confirm both run end-to-end
   - Log results to §9

7. SUBMISSION ARTIFACTS
   - Update README with eval methodology section + baseline results table
   - Add eval/README.md with reproducibility instructions
   - This is what the judge sees — it must look defensible
```

---

## Status: COMPLETE

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-05-12 |
| Author | Jeff + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-05-12 |
| Blocked By | — |
| Related Specs | submission-kaggle-narrative, compliance-gemma-naming-guidelines |
| Hackathon Deadline | 2026-05-18 (6 days) |

---

## §1 Feature Description

### Overview
Build a reproducible eval harness that measures FutureProof's 20 Gemma surfaces along four axes: function-calling correctness, structured-output schema/field accuracy, narrative quality (rubric-scored), and latency distribution. Publish baseline results in the README and submission package.

### Problem Statement
Simulated judges flagged: *"No eval methodology — 10 Gemma surfaces, zero systematic eval. No intent-resolution accuracy, no narrative quality scoring, no function-calling success rate, no latency distribution."*

Actual surface count is **20**, not 10 — but the gap is real. We ship Gemma-powered features without measurement, which means we can't defend quality claims, can't catch regressions, and can't show judges the rigor a hackathon submission needs.

### Surface Inventory

**Total: 20 surfaces** — 10 structured (JSON), 10 narrative, 4 with function calling.

| # | Surface | File:Line | Output Type | Tool Use | Tier |
|---|---------|-----------|-------------|----------|------|
| 1 | Ask Gemma Chat | `ask_gemma_router.py:52` | Free text + tool trace | ✅ (5 tools) | P0 |
| 2 | Career Intent Resolution | `intent.py:354` | JSON | ❌ | P0 |
| 3 | Sub-Specialty Verification (CHIP) | `set_your_course.py:1256` | JSON | ✅ | P0 |
| 4 | Explain ERN Receipt | `ask_gemma.py:~1064` | JSON | ✅ (2 tools) | P0 |
| 5 | Explain ROI Receipt | `ask_gemma.py:~1529` | JSON | ✅ (2 tools) | P0 |
| 6 | Explain RES Receipt | `ask_gemma.py:~2197` | JSON | ✅ (3 tools) | P0 |
| 7 | Explain GRW Receipt | `ask_gemma.py:~2526` | JSON | ✅ (2 tools) | P0 |
| 8 | Explain AURA Receipt | `ask_gemma.py:~2901` | JSON | ✅ (2 tools) | P0 |
| 9 | Boss Narratives | `boss_fights.py:1176` | Narrative | ❌ | P1 |
| 10 | Career Tiering | `career_tiering.py:222` | Structured | ❌ | P1 |
| 11 | Career Description | `career_description.py:542` | JSON | ❌ | P1 |
| 12 | Next Steps | `next_steps.py:166` | Narrative | ❌ | P1 |
| 13 | Guidance ("Gemma's Take") | `guidance.py:268` | Narrative | ❌ | P1 |
| 14 | Skill Pool Generation | `skill_pool.py:724` | Narrative→Struct | ❌ | P2 |
| 15 | Skill Recommendations | `skill_recs.py:201` | Narrative→Struct | ❌ | P2 |
| 16 | Reroll Commentary | `boss_fights.py:916` | Narrative | ❌ | P2 |
| 17 | Career Pick Q&A | `career_pick_qna.py:424` | Narrative | ❌ | P2 |
| 18 | Initial Major Resolution | `set_your_course.py:546` | Streaming narrative | ❌ | P2 |
| 19 | PDF Audience Questions | `pdf_questions.py:365` | JSON | ❌ | P2 |
| 20 | SOC Expansion | `soc_expansion.py:331` | JSON | ✅ | P2 |

### Success Criteria

**Required for submission (P0):**
- [ ] All 20 surfaces instrumented with latency + token logging (read-only)
- [ ] Golden sets built for 8 P0 surfaces (25 cases each → 200 labeled cases)
- [ ] Function-call accuracy reported for all 4 tool-using surfaces
- [ ] Schema-validity rate + field-level accuracy reported for all 10 structured surfaces
- [ ] Latency p50/p95/p99 reported for all 20 surfaces
- [ ] `make eval-p0` runs end-to-end in <10 minutes on Ollama
- [ ] README has an "Evaluation" section with results table + methodology link
- [ ] eval/README.md documents reproducibility (golden set format, scorer logic, how to add a new surface)

**Stretch (P1):**
- [ ] Narrative rubric scorer working for 4 P1 narrative surfaces
- [ ] 50-case human-labeled calibration set for rubric scorer (defends against Gemma-as-judge circularity)

**Aspirational (P2):**
- [ ] All 20 surfaces fully evaluated
- [ ] CI integration — eval runs on PR

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Eval lives in `eval/` at project root, not under `backend/` or `tests/` | Eval is cross-cutting (touches backend + pipeline) and is a *submission artifact*, not a test suite. Judges should find it without spelunking. | Put in `backend/eval/` — rejected: makes it look like backend-only. Put in `tests/eval/` — rejected: tests run on every commit, eval shouldn't. |
| 2 | Golden sets in JSONL, one file per surface | Append-friendly, diff-friendly in git, trivial to load with `pandas.read_json(lines=True)` | YAML — verbose for structured data. CSV — bad for nested JSON inputs. |
| 3 | Narrative rubric uses **Claude Opus 4.7 as judge**, not Gemma-as-judge | Avoids circularity. Claude judging Gemma is methodologically cleaner; judges can see we're not grading our own homework. | Gemma-as-judge — rejected, circular. Human-only — rejected, doesn't scale to 6 days. |
| 4 | Priority tiers (P0/P1/P2) for golden set construction | 20 surfaces × 25 cases × manual labeling = ~500 cases. Impossible in 6 days. Focus on what judges will demo. | Equal coverage — rejected, will ship nothing complete. Smoke test all 20 — rejected, doesn't demonstrate rigor. |
| 5 | Latency instrumentation in **all 20** surfaces, regardless of tier | Latency logging is cheap (one context manager) and gives us a complete p50/p95 table — high credibility for low effort. | Only instrument P0 — rejected, leaves an obvious hole in the results table. |
| 6 | Scorers are pure Python functions, no framework | We're not building DSPy or Promptfoo. Six days. Pure functions are testable and obvious. | LangSmith / Promptfoo / DSPy — rejected, learning curve eats the deadline. |
| 7 | Field-level accuracy uses **per-surface custom scorers**, not generic diff | A career-intent CIP code is exact-match. A confidence band is ±1 tolerant. A receipt's `headline` field is rubric-scored. Generic diff would over-penalize. | Generic JSON diff — rejected, semantically wrong. |
| 8 | Results stored as **timestamped run directories**, never overwritten | Baseline comparisons matter. We need to show "before nudge prompt → after nudge prompt" deltas. | Overwrite latest — rejected, destroys baseline. |
| 9 | Calibration: human-label 50 narrative cases, compare to Claude judge | Defends against "your judge is also an LLM" criticism. 50 is small but defensible — judges can see the methodology. | Skip calibration — rejected, leaves the biggest critique unanswered. Label 500 — rejected, time. |

### Constraints

**Technical:**
- Must run against both Ollama (local) and OpenRouter (cloud) backends — see `INFERENCE_BACKEND` env var in CLAUDE.md
- Must not modify any production Gemma call path (instrumentation is wrapper-only)
- Must run in CI-like conditions (no GPU assumptions, no user interaction)
- Golden set inputs must include "deaf education" / out-of-distribution cases per CLAUDE.md "no path is out of scope" rule

**Business:**
- 6-day deadline (2026-05-18)
- Judge-facing: the README results table is the primary artifact
- Voice: methodology doc uses FutureProof voice (per `docs/reference/voice-guide.md`) — no academic hedging

**Non-goals:**
- This spec is NOT a benchmark against other models (Llama, GPT, Claude)
- This spec is NOT a Gemma-vs-Gemma model-size comparison (that's `gemma-model-profiles.md`)
- This spec is NOT a prompt optimization framework (no DSPy-style auto-tuning)

---

## §3 UI/UX Design

**Skipped — this is a backend/infra spec with no in-app UI.**

The only "UI" is two artifacts:
1. README "Evaluation" section (Markdown table — handled by @fp-marketing-reviewer per existing voice guidelines)
2. eval/README.md methodology doc

Sample table format for README:

```markdown
## Evaluation

FutureProof has 20 distinct Gemma surfaces. We evaluate them on four axes:

| Surface | Schema Valid | Field Accuracy | Tool Call ✓ | Narrative (1-5) | p50 | p95 |
|---------|-------------:|---------------:|------------:|----------------:|----:|----:|
| Career Intent | 96.0% | 88.0% (CIP exact) | — | — | 1.2s | 2.4s |
| Ask Gemma Chat | — | — | 92.5% | 4.1 | 2.8s | 6.1s |
| Explain ERN | 100% | 94% | 98% | 4.3 | 1.9s | 3.7s |
| ... | ... | ... | ... | ... | ... | ... |

Reproduce: `make eval-p0`. Full methodology: [eval/README.md](eval/README.md).
```

---

## §4 Technical Specification

### Architecture Overview

```
eval/
├── README.md                   # Methodology, reproducibility, voice-checked
├── Makefile                    # make eval-p0, eval-p1, eval-all, eval-latency
├── pyproject.toml              # Eval deps (separate from backend)
├── runner.py                   # Main entry point — runs one or more surfaces
├── adapters/                   # One per surface — wraps the prod call
│   ├── __init__.py
│   ├── base.py                 # SurfaceAdapter protocol
│   ├── career_intent.py
│   ├── ask_gemma_chat.py
│   ├── explain_ern.py
│   └── ... (one per surface)
├── scorers/
│   ├── __init__.py
│   ├── schema.py               # Pydantic schema validity scorer
│   ├── exact_match.py          # CIP codes, SOC codes, structured fields
│   ├── tolerant_match.py       # Confidence bands ±1, fuzzy string match
│   ├── tool_call.py            # Tool name + arg match for function-calling
│   ├── rubric.py               # LLM-as-judge with 5-axis rubric
│   └── latency.py              # p50/p95/p99 aggregation
├── golden/
│   ├── career_intent/cases.jsonl
│   ├── ask_gemma_chat/cases.jsonl
│   ├── explain_ern/cases.jsonl
│   └── ... (one dir per surface)
├── results/
│   └── 2026-05-12-1430/         # Timestamped, never overwritten
│       ├── summary.json
│       ├── summary.md           # Human-readable table
│       ├── career_intent.jsonl  # Per-case results
│       └── latency.jsonl
├── calibration/
│   └── narrative_human_labels.jsonl  # 50 human-scored narratives
└── instrumentation/
    └── gemma_timer.py          # Context manager wrapping all Gemma calls
```

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `eval/` (entire tree above) | Create | New top-level directory |
| `backend/app/services/_gemma_client.py` (or equivalent) | Modify | Add latency-instrumentation hook; no behavior change |
| `Makefile` (root) | Modify | Add `eval-p0`, `eval-p1`, `eval-all`, `eval-latency` targets |
| `README.md` | Modify | Add "Evaluation" section with results table |
| `pyproject.toml` (root) | Modify | Optional `eval` extras for pandas/numpy aggregation |
| `.gitignore` | Modify | Allow `eval/results/` to be committed (per [[feedback_always_commit_reports]]) |

### Data Model Changes

#### `eval/scorers/base.py`

```python
from typing import Protocol
from pydantic import BaseModel

class GoldenCase(BaseModel):
    """One labeled example for a surface."""
    case_id: str
    inputs: dict  # Surface-specific input payload
    expected: dict  # Surface-specific expected output (or rubric criteria)
    tags: list[str] = []  # e.g., ["edge", "ood", "adversarial"]
    notes: str | None = None

class ScoreResult(BaseModel):
    case_id: str
    surface: str
    metric: str  # "schema_valid" | "field_accuracy" | "tool_call" | "rubric" | "latency"
    score: float  # 0.0–1.0 for accuracy metrics, seconds for latency
    passed: bool
    details: dict = {}  # Per-metric breakdown
    latency_seconds: float
    tokens_input: int | None = None
    tokens_output: int | None = None

class Scorer(Protocol):
    def score(self, case: GoldenCase, actual: dict) -> ScoreResult: ...
```

#### `eval/adapters/base.py`

```python
class SurfaceAdapter(Protocol):
    surface_name: str
    tier: str  # "P0" | "P1" | "P2"

    def run(self, inputs: dict) -> tuple[dict, LatencyInfo]:
        """Run the surface with given inputs. Return (actual_output, latency)."""
        ...
```

### Service Changes

#### Latency Instrumentation

Wrap every Gemma call site with `GemmaTimer`:

```python
# eval/instrumentation/gemma_timer.py
import time
from contextlib import contextmanager
from pathlib import Path

@contextmanager
def gemma_timer(surface: str, log_path: Path | None = None):
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        if log_path:
            log_path.write_text(json.dumps({...}) + "\n", mode="a")
```

Call sites get a one-line wrap:
```python
with gemma_timer("career_intent"):
    response = await client.chat.completions.create(...)
```

This is the **only** production change. No behavior change, no API change.

#### Per-Surface Adapters

Each adapter imports the production code path and replays it with golden inputs. Example:

```python
# eval/adapters/career_intent.py
from backend.app.services.intent import resolve_intent
from .base import SurfaceAdapter

class CareerIntentAdapter:
    surface_name = "career_intent"
    tier = "P0"

    async def run(self, inputs: dict) -> tuple[dict, LatencyInfo]:
        with gemma_timer(self.surface_name) as t:
            result = await resolve_intent(
                student_input=inputs["student_input"],
                school_name=inputs["school_name"],
                school_cips=inputs["school_cips"],
                crosswalk_cips=inputs["crosswalk_cips"],
            )
        return result.model_dump(), t.info
```

### §4.5 LLM-as-Judge Rubric

Five-axis rubric for narrative surfaces, scored 1–5 each, mean = surface score:

| Axis | Definition | Anchor 1 (worst) | Anchor 5 (best) |
|------|-----------|------------------|-----------------|
| **Relevance** | Addresses the actual context (career, school, stat, etc.) | Generic platitude that could apply to any career | Specifically grounded in the named career and the student's situation |
| **Specificity** | Uses real data points vs. vague language | "Good earning potential" | "Mean wage $87k in IL, top 25% earn $112k+" |
| **Voice** | Matches FutureProof voice (per docs/reference/voice-guide.md) | Corporate / hedged / academic | Cool, confident, data-honest |
| **Accuracy** | No hallucinations (fake schools, made-up salaries, wrong taxonomies) | Contains a fabricated fact | All checkable facts verified against context |
| **Length** | Within the surface's character budget | 3x over or under | Within budget, no padding |

**Judge prompt** (lives in `eval/scorers/rubric.py`):

```
You are evaluating an AI-generated response from FutureProof, a career planning tool.

Surface: {surface_name}
Surface description: {surface_description}
Character budget: {char_budget}

Input context provided to the AI:
{input_context}

AI-generated response:
{actual_output}

Score each axis 1–5 using the anchors below. Be strict. A "3" is mediocre, not "fine."

{rubric_anchors}

Output JSON only:
{
  "relevance": <1-5>, "relevance_reason": "<one sentence>",
  "specificity": <1-5>, "specificity_reason": "<one sentence>",
  "voice": <1-5>, "voice_reason": "<one sentence>",
  "accuracy": <1-5>, "accuracy_reason": "<one sentence>",
  "length": <1-5>, "length_reason": "<one sentence>",
  "flagged_hallucinations": ["<verbatim quote>", ...]
}
```

Judge model: **Claude Opus 4.7** via Anthropic API (cleanly external to Gemma — no circularity).

**Calibration:** 50 narrative cases human-labeled (10 per P1 surface). Compute Pearson correlation between Claude judge scores and human scores per axis. Target ≥ 0.7. Report correlation in README.

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `backend/tests/services/test_intent.py` | All | Low | Adapter calls `resolve_intent` unchanged; instrumentation is wrapper |
| `backend/tests/services/test_boss_fights.py` | All | Low | Same — wrapper-only change |
| Any test that times Gemma calls | — | Med | If instrumentation adds >50ms overhead, async timing tests could flake |

#### Authorized Test Modifications
None expected. If a test fails due to instrumentation overhead, increase its timeout — but escalate via §10 first.

#### Confirmed Safe
All production endpoint tests. Eval is read-only from prod code's perspective.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `eval/tests/test_scorers.py` | `test_schema_scorer_pass` | Schema scorer returns 1.0 on valid Pydantic parse |
| P0 | `eval/tests/test_scorers.py` | `test_schema_scorer_fail` | Schema scorer returns 0.0 on invalid JSON |
| P0 | `eval/tests/test_scorers.py` | `test_exact_match_cip` | CIP codes "13.1011" == "13.1011" passes, "13.1011" ≠ "13.1099" fails |
| P0 | `eval/tests/test_scorers.py` | `test_tool_call_scorer` | Tool name + args matched against golden tool call |
| P0 | `eval/tests/test_scorers.py` | `test_tolerant_match_confidence_band` | Confidence ±1 within band passes |
| P0 | `eval/tests/test_scorers.py` | `test_latency_p95` | p95 computed correctly on 100 samples |
| P0 | `eval/tests/test_rubric_scorer.py` | `test_rubric_parse_valid_response` | Parses 5-axis JSON correctly |
| P0 | `eval/tests/test_rubric_scorer.py` | `test_rubric_parse_invalid_response` | Returns null + flags malformed judge output |
| P1 | `eval/tests/test_adapters.py` | `test_each_adapter_loads` | All 20 adapters import without error |
| P1 | `eval/tests/test_instrumentation.py` | `test_gemma_timer_overhead` | Wrapper adds <5ms overhead |

#### Test Data Requirements

- Mocked Gemma responses for adapter tests (no live LLM calls in unit tests)
- Mocked Claude judge responses for rubric scorer tests
- Sample golden case files in `eval/tests/fixtures/`

---

## §5 Architecture Review

### @fp-architect Review
**Status:** PENDING
#### Findings
[Filled in by @fp-architect]

Specific questions for architect:
1. Is `eval/` at root the right home, or should it nest under `backend/`?
2. Should adapters import production code directly (current proposal) or go through HTTP to the running FastAPI server?
3. Does instrumentation belong in a shared `_gemma_client.py` wrapper or as decorators on each call site?
4. Should results be DuckDB tables (queryable) or JSONL files (simple)?

#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

### @genai-architect Review
**Status:** PENDING
#### Findings
[Filled in by @genai-architect — review §4.5 rubric design, judge prompt, calibration approach]

Specific questions for genai-architect:
1. Is 50-case human calibration enough to defend the Claude-judge methodology?
2. Should we add a "disagreement" gate — if Claude judges differ across two runs, surface as low-confidence?
3. Token-budget concern: scoring 200+ narratives × 5-axis rubric on Opus is ~$5–10 in API calls. Acceptable?
4. Should rubric scores be on a 1–5 ordinal scale or a 0–1 continuous scale?

#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

---

## §6 Implementation Log

**Status:** PENDING

### Files Modified
| File | Change Summary |
|------|---------------|

### Deviations from Spec
[Any divergence from §4 and why]

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|

---

## §7 Test Coverage

**Status:** PENDING

### Tests Added
| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest | | | | |
| vitest | | | | |
| eval scorer tests | | | | |

---

## §8 Reviews

**Status:** PENDING

### Code Review (@faang-staff-engineer)
**Status:** PENDING
#### Findings
[Particular focus areas:]
- Rubric scorer prompt-injection resistance (golden case content reaches judge prompt)
- Latency instrumentation thread-safety (concurrent requests writing same JSONL)
- Results directory race conditions if `make eval-all` parallelizes
- Secret hygiene — Anthropic API key for judge model in env, not in code

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

### Eval Harness Verification
| Check | Result |
|-------|--------|
| `make eval-p0` runs to completion | |
| `make eval-latency` runs against all 20 surfaces | |
| Results dir written with summary.json + summary.md | |
| README "Evaluation" section renders correctly | |

---

## §10 Discussion

```
[2026-05-12] Jeff → Claude
Simulated judges flagged eval gap. Drafting this spec to close it before 2026-05-18 submission.
20 surfaces (not 10 as judges thought). P0 tier focuses on the 8 surfaces judges
will demo: intent, ask-gemma, CHIP, and the 5 stat receipts. Need architect +
genai-architect sign-off on §4 / §4.5 before construction begins.
```

---

## §11 Final Notes

**Human Review:** PENDING

### Open Questions Before Implementation

1. **Scope commitment**: Will we commit to P0 only (8 surfaces, achievable in 6 days), or stretch to P0+P1 (12 surfaces, risky)?
2. **Judge model cost**: Anthropic API spend for rubric scoring — set a cap or run on a budget?
3. **Calibration set ownership**: Who hand-labels the 50 calibration cases? Jeff alone, or split with collaborators?
4. **Surface this in submission video?** A 10-second beat on "we measure what we ship" could differentiate vs. competitors who only have a demo.

### Lessons Learned
[TBD after implementation]
