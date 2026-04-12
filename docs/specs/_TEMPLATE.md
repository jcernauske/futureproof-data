# Feature: [Feature Name]

## Claude Code Prompt

```
Read the spec at docs/specs/[filename].md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (system architecture, data flow, Brightsmith integration, Gemma function calling)
   - If spec involves data pipeline or stat changes: invoke @fp-data-reviewer to review data quality implications
   - Both write findings to §5 (Architecture Review)
   - If APPROVED: proceed to step 2
   - If CHANGES REQUESTED (Significant): STOP, alert human
   - If REJECTED (Blocker): STOP, alert human

2. DESIGN VISION (UI specs only — skip for backend-only specs)
   - Invoke @fp-design-visionary to propose the premium version of the UI
   - Visionary writes to §3 (UI/UX Design): layout, interactions, Cozy Quest token usage, responsive behavior
   - §3 becomes the pixel-perfect implementation target
   - If spec involves Gemma prompts or function calling: invoke @genai-architect for prompt/schema review (writes to §10)

3. IMPLEMENTATION
   - Implement the spec as written in §3 (UI/UX) and §4 (Technical Spec)
   - BEFORE coding: Review §4 Testing Impact Analysis thoroughly
   - DURING coding: Update any broken tests listed in "Authorized Test Modifications"
   - CRITICAL: If any test NOT in the "Authorized Test Modifications" list fails, STOP and escalate to human
   - Log all work to §6 (Implementation Log)
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest) to verify build
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts)
   - If still broken after 3 attempts: escalate to human via §10 Discussion

4. TESTING
   - Invoke @test-writer to review the full spec
   - @test-writer MUST review §4 Testing Impact Analysis
   - Implement all tests listed in "New Tests Required" by priority (P0 first)
   - Backend tests: pytest in backend/tests/
   - Frontend tests: vitest in frontend/src/**/*.test.ts(x)
   - Run ALL tests to catch regressions
   - If still broken after 3 attempts: escalate to human via §10 Discussion

5. DESIGN AUDIT (UI specs only — skip for backend-only specs)
   - Invoke @design-builder for mechanical token/pattern compliance against Cozy Quest design system
   - Writes findings to §8 (Design Audit section)
   - If CHANGES REQUIRED: route to implementer via §10 Discussion

6. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests
   - Reviewer writes findings to §8 (Code Review)
   - If APPROVED: proceed to step 7
   - If CHANGES REQUIRED: route to originating agent via §10 Discussion
   - If BLOCKER: STOP, alert human

7. VERIFICATION
   - Invoke @fp-builder to run full build verification
   - Backend: ruff check, mypy, pytest
   - Frontend: TypeScript, vitest, Vite production build
   - Log results to §9 (Verification)
   - If all green: mark status COMPLETE

8. COMPLETION
   - Update top-level Spec Status to COMPLETE
   - Check off all completed Success Criteria in §1
   - Update §6 Implementation Log, §7 Test Coverage, §8 Code Review
   - Generate report to reports/feature-[name]-YYYY-MM-DD.md
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
| DESIGN AUDIT | @design-builder checking token compliance |
| CODE REVIEW | @faang-staff-engineer reviewing |
| VERIFICATION | @fp-builder running full build |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | YYYY-MM-DD |
| Author | [Human] + Claude Desktop |
| Spec Version | 1.0 |
| Last Updated | YYYY-MM-DD |
| Blocked By | — |
| Related Specs | — |

---

## §1 Feature Description

### Overview
[1-2 sentence summary]

### Problem Statement
[What problem does this solve? Why now?]

### Success Criteria
- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] [Criterion 3]

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | | | |

### Constraints
- [Technical constraint]
- [Business constraint]

---

## §3 UI/UX Design

> Skip this section for backend-only specs.
> For UI specs: @fp-design-visionary fills this section BEFORE implementation begins. This becomes the pixel-perfect target.

### Mockups
[ASCII mockups or detailed visual descriptions. These are pixel-perfect requirements.]
[Reference Cozy Quest design tokens by name. Never hardcode colors, spacing, typography.]

### Interactions
[User flows, animations, transitions. Framer Motion specifications where applicable.]

### Responsive Behavior
[Desktop viewport (primary) → mobile viewport. How does the layout adapt?]

### Cozy Quest Design References
[Which design tokens apply. Background tier, accent colors, typography scale.]
[Which libraries: React Flow (tree viz), Recharts (charts), Framer Motion (animations), shadcn/ui (components).]

### Accessibility
| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| | | | |

---

## §4 Technical Specification

### Architecture Overview
[How does this fit into the existing codebase? Which modules are involved?]

### File Changes

| File | Action | Description |
|------|--------|-------------|
| | Create / Modify / Delete | |

### Data Model Changes
[New Pydantic models, Iceberg schema changes, new tables]

### Service Changes
[New modules, interface additions, dependency changes]

### Testing Impact Analysis

> **IMPORTANT**: Before finalizing this section, search the test directories for tests related to files being modified.

#### Existing Tests at Risk
| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| | | High/Med/Low | |

#### Authorized Test Modifications
| Test | Modification | Reason |
|------|-------------|--------|
| | | |

#### Confirmed Safe
[Tests that should NOT break. If any fail, STOP and escalate.]

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | | | |
| P1 | | | |

#### Test Data Requirements
[Fixtures, mocks, test state needed]

---

## §5 Architecture Review

### @fp-architect Review
**Status:** PENDING
#### Findings
[Filled in by @fp-architect]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

### @fp-data-reviewer Review (if applicable)
**Status:** PENDING (or SKIPPED if no pipeline/data changes)
#### Findings
[Filled in by @fp-data-reviewer — pipeline quality, crosswalk integrity, stat formula correctness]
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
[Any divergence from §3/§4 and why]

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

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@design-builder)
**Status:** PENDING (or SKIPPED for backend-only specs)
[Filled in by @design-builder — Cozy Quest token compliance, dark-first enforcement, responsive behavior]

### Code Review (@faang-staff-engineer)
**Status:** PENDING
#### Findings
[Filled in by reviewer]
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

---
---

# Lightweight Spec Template (Bugfixes / Small Changes)

> Copy everything below this line into a new file for bugfixes and small changes.

---

```markdown
# Bugfix: [Bug Name]

## Claude Code Prompt

Read and implement the spec at docs/specs/[filename].md
[2-3 sentence description of the bug and fix]
Key changes:
1. [File and change]
2. [File and change]
After implementing, run full test suite (pytest + ruff + mypy). Report any failures.

---

**Spec Status:** DRAFT
**Created:** YYYY-MM-DD
**Updated:** YYYY-MM-DD
**Priority:** High | Medium | Low

## §1 Problem
[What's broken, how to reproduce]

## §2 Solution
[The fix, with file paths and code changes]

## §3 Testing
[What to test, expected results]

## §5 Architecture Review
**Status:** SKIPPED (lightweight spec)

## §6 Implementation Log
**Status:** PENDING

## §7 Test Coverage
**Status:** PENDING

## §8 Code Review
**Status:** SKIPPED (lightweight spec)

## §9 Verification
**Status:** PENDING

## §10 Discussion
[If needed]

## §11 Final Notes
**Human Review:** PENDING
```
