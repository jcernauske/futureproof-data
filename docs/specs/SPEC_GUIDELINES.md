# Spec Writing Guidelines — Future Proof

## Principles

1. **Prompt-first** — The Claude Code Prompt is the most important section. Write it first. Copy-paste ready.
2. **Be specific** — File paths, code snippets, exact interfaces. Ambiguity creates bugs.
3. **Test everything** — Every spec needs a Testing Impact Analysis in §4.
4. **Type hints everywhere** — Every interface in the spec must show full type signatures.
5. **Update dates** — Keep `Last Updated` current.
6. **Iceberg schemas explicit** — Every table creation or schema evolution documents the full schema.

## File Naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature-name.md` | `feature-iceberg-ingestion.md` |
| Bugfix | `bugfix-description.md` | `bugfix-ollama-timeout.md` |
| Refactor | `refactor-description.md` | `refactor-pipeline-abc.md` |
| Test coverage | `test-coverage-area.md` | `test-coverage-storage-layer.md` |
| Performance | `performance-description.md` | `performance-iceberg-reads.md` |
| Tech debt | `tech-debt-description.md` | `tech-debt-error-handling.md` |
| Spike | `spike-description.md` | `spike-gemma-tool-use.md` |

## Claude Code Prompt Calibration

### Full Pipeline (new module, pipeline stage, schema changes, LLM integration, new screen)
```
1. ARCH REVIEW (@fp-architect + @fp-data-reviewer) → 2. DESIGN VISION (@fp-design-visionary, UI specs) → 3. IMPLEMENTATION → 4. TESTING (@test-writer) → 5. DESIGN AUDIT (@design-builder, UI specs) → 6. CODE REVIEW (@faang-staff-engineer) → 7. VERIFICATION (@fp-builder) → 8. COMPLETION
```

### Standard (3-5 files, no major architecture)
Skip Architecture Review + Design Vision:
```
1. IMPLEMENTATION → 2. TESTING → 3. CODE REVIEW → 4. VERIFICATION → 5. COMPLETION
```

### Lightweight (bugfix, small change, spike)
```
1. IMPLEMENTATION → 2. Run all tests → 3. COMPLETION
```

| Signal | Weight |
|--------|--------|
| 1-2 files, no schema changes | Lightweight |
| 3-5 files, minor pipeline change | Standard |
| New Iceberg table, new pipeline stage | Full |
| New data schema or schema evolution | Full |
| Ollama/Gemma integration change | Full (@genai-architect ad-hoc) |
| New module or public API surface | Full |
| New screen or major UI component | Full (@fp-design-visionary mandatory) |
| Stat formula or boss fight logic change | Full (@fp-data-reviewer mandatory) |
| "I'm not sure this is right" energy | Full |

## §3 (UI/UX) Tips

- `@fp-design-visionary` fills §3 BEFORE implementation begins — this is the pixel-perfect target
- ASCII mockups in §3 are requirements, not suggestions
- Show multiple states: default, loading, empty, error, populated
- Reference Cozy Quest design tokens by name (background tier, accent, text tier) — never hardcode
- Typography: display (Fredoka One / Nunito Black), body (Nunito / Quicksand), data (Space Mono)
- Dark-first: `#1B1D30` is home. No light mode.
- Every interactive element gets an accessibility identifier
- Show both desktop (primary) and mobile-responsive behavior
- The branch tree visualization (Screen 6) is cinematic — full viewport, animated branches
- Boss fight sequences: plush/soft aesthetic, funny-scary, Framer Motion transitions

### Frontend Library Reference
Specs should reference which libraries are needed for each component:

| Library | Use For | Example |
|---------|---------|---------|
| **React Flow** | Branch tree (Screen 6), any node-based visualization | Career path nodes, branch connections |
| **Recharts** | Pentagon radar charts, any data visualization | Five-stat pentagon, stat comparisons |
| **Framer Motion** | Animations, transitions, reveals | Boss fight sequences, Stage 2 reveal, branch glow |
| **shadcn/ui** | Buttons, dialogs, sliders, dropdowns, cards | Effort slider, school search, save dialog |
| **Google Fonts** | Typography only | Fredoka One (display), Nunito (body), Space Mono (data) |

## §4 (Technical Spec) Tips

### Pipeline Interfaces
Every pipeline module documents its inputs, outputs, and Iceberg table interactions:

```python
class MyPipeline:
    async def run(
        self,
        input_table: str,
        output_table: str,
        config: PipelineConfig,
    ) -> PipelineResult: ...
```

### Testing Impact Analysis
Before finalizing §4:
1. Search `tests/` for tests related to modified files
2. List existing tests at risk with risk level
3. Authorize test modifications explicitly
4. Identify confirmed-safe tests (if they break → escalation)
5. Prioritize new tests: P0 (must), P1 (should), P2 (nice to have)

### Iceberg Schema Changes
When modifying or creating Iceberg tables, document:
- Table name and namespace
- Full schema (field names, types, nullability)
- Partition spec
- Sort order (if applicable)
- Migration strategy for existing data

## Agent Quick Reference

| Agent | When to Invoke | What It Does |
|-------|---------------|-------------|
| `@fp-architect` | New modules, pipeline changes, API surface changes | System architecture review |
| `@fp-design-visionary` | New screens, major UI components | Proposes premium Cozy Quest design for §3 |
| `@fp-data-reviewer` | Pipeline changes, stat formulas, boss fight logic, crosswalk changes | Data quality gate |
| `@test-writer` | Every spec with code changes | Writes pytest + vitest tests |
| `@design-builder` | UI specs after implementation | Audits Cozy Quest token compliance |
| `@faang-staff-engineer` | Standard + Full pipeline specs | Security, performance, error handling review |
| `@genai-architect` | Gemma prompts, function calling schemas, agent role design | LLM integration review (ad-hoc) |
| `@fp-builder` | Every spec with code changes | Full build verification |

## Status Tracking

DRAFT → ARCH REVIEW → DESIGN VISION → IMPLEMENTATION → TESTING → DESIGN AUDIT → CODE REVIEW → VERIFICATION → COMPLETE

Always update `Last Updated` when changing status.

---

*FutureProof spec guidelines. Python pipelines, Iceberg storage, Ollama/Gemma LLM, React frontend, Cozy Quest design system.*
