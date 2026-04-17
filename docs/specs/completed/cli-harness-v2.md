# Spec: CLI Harness v2 — Pacing + Conversational Mode

*Make Gemma earn its keep*

**Status:** DEPRECATED — CLI harness no longer needed; product loop vetted in-app
**Owner:** Jeff
**Priority:** P0 — iterate on existing CLI
**Created:** 2026-04-11
**Repo:** `~/code/bright/futureproof-data/` (monorepo)

---

## Problem

The CLI dumps everything at once — pentagon, gauntlet, branches, skill recs, Gemma's Take — in a wall of text. By the time the student reaches Gemma's guidance it's an afterthought buried under tables. The boss fight narratives flash by with no drama. And once the build is displayed, the student can't ask follow-up questions. Gemma has good context but no room to use it.

## What Changes

Three changes to `backend/cli.py` and supporting services:

### 1. Reorder: Gemma's Take comes first

After building the character, the display order becomes:

```
1. Career header (title, salary, education)
2. Gemma's Take (the narrative — lead with the story)
3. Pentagon stats (the proof)
4. Boss Gauntlet (interactive — one at a time)
5. Career Branches
6. Skill Recommendations
7. Menu (save / new / compare / explore / ASK GEMMA)
```

Gemma's Take sets the frame: "Here's what your path looks like." Then the stats and boss fights back it up with data. The student reads the narrative first and looks at the numbers with context, not the other way around.

### 2. Paced boss gauntlet

Instead of rendering all 5 boss fights + Final Boss in a single table, show them one at a time with a pause:

```
══════════════════════════════════════
  ⚔️  Boss Gauntlet
══════════════════════════════════════

  🤖 Fight AI

  Your AI Resilience (RES 3) + Human Edge (HMN 7) = 10

  .............. LOSE

  "Marketing analytics, A/B testing, and campaign
   optimization are already being automated at scale.
   But the strategic side — brand positioning, client
   relationships, creative direction — stays human.
   Your move: learn to direct the AI tools, not
   compete with them."

  [Press Enter to continue]

  💰 Fight Student Loans

  Your ROI (9) vs. IU-B's debt load

  .............. WIN

  "Kelley's in-state tuition keeps your debt-to-earnings
   ratio strong. Most IU business grads are cash-flow
   positive within 3 years."

  [Press Enter to continue]

  ... (3 more bosses) ...

  🏆 Fight the Future — 3W / 1L / 1D
  SOLID BUILD with an AI exposure gap.
```

Each boss gets its own screen. The narrative has room to breathe. The student processes one threat at a time instead of scanning a table. Press Enter to advance.

**Implementation:** The `_render_gauntlet` function changes from returning a single Panel to yielding individual fight displays with `Prompt.ask("", default="")` between them.

### 3. Conversational mode: "Ask Gemma"

Add option `[5] Ask Gemma a question` to the menu. This opens a freeform chat loop where the student can ask follow-up questions with their full build context loaded.

```
══════════════════════════════════════
  💬 Ask Gemma
══════════════════════════════════════

  Your build context is loaded. Ask anything about
  your school, major, career paths, or what to do
  while in school. Type 'done' to go back.

  You: What if I add a computer science minor?

  Gemma: "A CS minor at IU-B would meaningfully shift
   your AI Resilience from 3 to roughly 5-6. You'd
   pick up Python, data structures, and enough ML
   literacy to direct AI marketing tools rather than
   being replaced by them. The Kelley + CS combo is
   increasingly common — about 12% of Kelley grads
   now double with Luddy CS courses. It adds one
   semester but your Fight AI result likely flips
   from LOSE to DRAW. Worth it if you're worried
   about the automation angle."

  You: How does IU compare to Purdue for marketing?

  Gemma: "Different paths. Purdue's Daniels School
   doesn't have Kelley's brand recognition in
   marketing specifically — most Purdue business
   grads land in operations and supply chain roles
   (SOC 11-3071), not marketing management. Your
   ERN would be similar but the career branch tree
   looks different: more operations branches, fewer
   creative/brand paths. If marketing management
   is the target, Kelley's alumni network in that
   specific field is stronger. If you're open to
   operations, Purdue's supply chain program is
   top-5 nationally."

  You: done

  [Back to menu]
```

**Implementation:**

New function in `backend/app/services/guidance.py`:

```python
def chat_with_context(
    career: CareerOutcome,
    gauntlet: GauntletResult,
    branches: list[CareerBranch],
    skill_recs: list[SkillRec],
    conversation_history: list[dict],  # {"role": "user"/"assistant", "content": "..."}
    user_question: str,
) -> str:
    """Freeform Q&A with full build context loaded."""
```

The system prompt for conversational mode is different from the one-shot guidance prompt:

```
You are a career coach with deep knowledge of college programs and
career paths. A high school student has just built their FutureProof
character and is asking follow-up questions.

Their build:
- School: {school}
- Major: {major}
- Primary career: {career_title} ({soc_code}), median ${wage}
- Stats: ERN {ern}, ROI {roi}, RES {res}, GRW {grw}, HMN {hmn}
- Boss fight results: {boss_summary}
- Available career branches: {branches_summary}
- Skill recommendations given: {recs_summary}

Answer their question directly and specifically. Reference their
actual stats, school, and career data. If they ask "what if" 
questions about different schools or majors, give your best
assessment but note that you'd need to run a new build to get
exact numbers.

Be conversational. Be specific. Never give generic advice. If you
don't know something, say so — don't make it up.
```

The conversation history accumulates so Gemma has context of prior Q&A within the session. Each exchange appends to the history list.

**In the CLI:**

```python
def _ask_gemma_flow(build: Build) -> None:
    console.print(Panel(
        "Your build context is loaded. Ask anything about your "
        "school, major, career paths, or what to do in school.\n"
        "Type [bold]done[/bold] to go back.",
        title="[bold]💬 Ask Gemma[/bold]",
        border_style="bright_blue",
    ))
    history: list[dict] = []
    while True:
        question = Prompt.ask("[bold cyan]You[/bold cyan]").strip()
        if question.lower() in ("done", "quit", "exit", "back", "q"):
            break
        if not question:
            continue
        with console.status("[cyan]thinking...[/cyan]"):
            answer = guidance.chat_with_context(
                career=build.career,
                gauntlet=build.gauntlet,
                branches=build.branches,
                skill_recs=build.skill_recs,
                conversation_history=history,
                user_question=question,
            )
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})
        console.print()
        console.print(Panel(
            Text(answer, style="italic"),
            title="[bold]Gemma[/bold]",
            border_style="bright_blue",
            padding=(1, 2),
        ))
        console.print()
```

### Updated menu

```python
MENU = """
[1] Save this build
[2] Try a different school or major
[3] Compare saved builds
[4] Explore a career branch in detail
[5] Ask Gemma a question        ← NEW
[q] Quit
"""
```

---

## What Does NOT Change

- Service modules (stat_engine, boss_fights, branch_tree, school_lookup, builds, mcp_client, gemma_client) — untouched
- Pydantic models — untouched
- All existing tests — untouched
- Boss fight thresholds — untouched
- Save/compare flow — untouched

This is a CLI display + Gemma prompt change only. No backend logic changes.

---

## Testing

### Automated
- `tests/services/test_guidance.py` — add test for `chat_with_context()` (mocked Gemma, verify prompt assembly and history accumulation)
- Existing 59 service tests must still pass

### Manual (the real test)
Put the kid in front of it again. Watch for:
- Does leading with Gemma's Take change how they read the stats?
- Do the paced boss fights land better than the table dump?
- Do they actually use "Ask Gemma"? What do they ask?
- Does Gemma's conversational response feel specific or generic?
- How many questions do they ask before they're satisfied?

---

## Estimated Effort

| Step | Estimate |
|------|----------|
| Reorder display in cli.py | 30 min |
| Paced boss gauntlet | 45 min |
| `chat_with_context()` in guidance.py | 1 hr |
| Ask Gemma flow in cli.py | 45 min |
| Test for chat_with_context | 30 min |
| **Total** | **~3-4 hrs** |

---

*— End of Spec —*
