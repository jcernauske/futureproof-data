"""FutureProof interactive CLI harness.

Walks a user through the full experience: school search → major
resolution → effort choice → pentagon → boss gauntlet → branch
tree → skill recs → Gemma's Take → save/compare/explore menu.

Run with ``uv run python backend/cli.py`` from the project root
(the root venv has brightsmith/pyiceberg installed — the CLI does
not need its own venv). ``cd backend && python cli.py`` also works
as long as ``..`` is on ``sys.path`` via the shim below.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Make ``app.*`` importable whether invoked from project root or
# from the ``backend/`` subdirectory.
_BACKEND_ROOT = Path(__file__).resolve().parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from rich.console import Console  # noqa: E402
from rich.markdown import Markdown  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.prompt import IntPrompt, Prompt  # noqa: E402
from rich.table import Table  # noqa: E402
from rich.text import Text  # noqa: E402

from app.models.career import (  # noqa: E402
    AppliedSkill,
    BossFightResult,
    Build,
    CareerBranch,
    CareerOutcome,
    EffortLevel,
    MajorMatch,
    PentagonStats,
    Program,
    SchoolMatch,
    SkillRec,
)
from app.services import (  # noqa: E402
    boss_fights,
    branch_tree,
    builds,
    career_tiering,
    career_tree,
    gemma_client,
    guidance,
    intent,
    mcp_client,
    next_steps,
    receipts,
    report_gen,
    school_lookup,
    skill_pool,
    skill_recs,
    stat_engine,
)

console = Console()

EFFORT_CHOICES: list[tuple[str, EffortLevel, str]] = [
    ("Working two jobs — very limited focus (10th percentile)", "working_hard", "10th"),
    ("Working + school — limited focus (25th percentile)", "working", "25th"),
    ("Balanced — solid effort (50th percentile)", "balanced", "50th"),
    ("Strong focus — academic priority (75th percentile)", "focused", "75th"),
    ("All-in — maximum focus (90th percentile)", "all_in", "90th"),
]

# How much of this program's debt the student expects to finance with
# loans. Feeds into stat_engine → compute_pentagon as the loan_pct knob
# that scales DTE before ROI/loans-boss derivation.
LOAN_CHOICES: list[tuple[str, float]] = [
    ("No loans (0%) — scholarships, savings, or family cover it", 0.0),
    ("Some loans (25%)", 0.25),
    ("Half loans (50%)", 0.50),
    ("Mostly loans (75%)", 0.75),
    ("All loans (100%) — full published debt load", 1.0),
]

STAT_LABELS = [
    ("ERN", "ern"),
    ("ROI", "roi"),
    ("RES", "res"),
    ("GRW", "grw"),
    ("HMN", "hmn"),
]

STAT_COLORS = {
    "ERN": "green",
    "ROI": "cyan",
    "RES": "magenta",
    "GRW": "yellow",
    "HMN": "bright_blue",
}

BOSS_ICONS = {
    "ai": "🤖",
    "loans": "💰",
    "market": "📈",
    "burnout": "🔥",
    "ceiling": "📊",
}

BOSS_RESULT_STYLE = {
    "win": "bold green",
    "draw": "bold yellow",
    "lose": "bold red",
    "unknown": "dim",
}


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def _receipt_box(lines: list[str], title: str = "Receipts") -> None:
    body = "\n".join(lines)
    console.print(Panel(
        Text(body, style="dim"),
        title=f"[dim]📋 {title}[/dim]",
        border_style="bright_black",
        padding=(0, 2),
    ))


def _banner() -> None:
    text = Text.assemble(
        ("✦ ", "bold cyan"),
        ("FutureProof", "bold white"),
        (" — See Where Every Path Leads ", "dim"),
        ("✦", "bold cyan"),
    )
    console.print(Panel(text, border_style="cyan", padding=(1, 2)))


def _render_pentagon(stats: PentagonStats) -> Table:
    table = Table(
        show_header=False,
        box=None,
        padding=(0, 1),
        pad_edge=False,
    )
    table.add_column(style="bold")
    table.add_column()
    table.add_column(justify="right")
    for label, attr in STAT_LABELS:
        value = getattr(stats, attr)
        color = STAT_COLORS.get(label, "white")
        bar = _bar(value, color)
        display = str(value) if isinstance(value, int) else "—"
        table.add_row(f"[{color}]{label}[/{color}]", bar, display)
    return table


def _bar(value: int | None, color: str, width: int = 10) -> str:
    if not isinstance(value, int):
        return f"[dim]{'░' * width}[/dim]"
    filled = max(0, min(width, value))
    empty = width - filled
    return f"[{color}]{'█' * filled}[/{color}][dim]{'░' * empty}[/dim]"


def _render_career_header(career: CareerOutcome) -> Panel:
    wage = (
        f"${int(career.median_annual_wage):,}"
        if career.median_annual_wage
        else "N/A"
    )
    body = Text()
    body.append(f"Career: {career.occupation_title} ({career.soc_code})\n", "bold")
    body.append(f"Median Salary: {wage}\n", "green")
    body.append(
        f"Entry Education: {career.education_level_name or 'N/A'}\n", "dim"
    )
    if career.substitution_applied and career.data_caveat:
        body.append("\n")
        body.append("ℹ ", "yellow")
        body.append(str(career.data_caveat.get("message", "")), "yellow")
    return Panel(
        body,
        title="[bold]📊 Your Build[/bold]",
        border_style="cyan",
        padding=(1, 2),
    )


def _print_fight(fight: BossFightResult) -> None:
    """Print a single boss fight — icon, reason line, result, narrative."""
    icon = BOSS_ICONS.get(fight.boss, "⚔️")
    style = BOSS_RESULT_STYLE.get(fight.result, "white")
    result_label = fight.result.upper()
    console.print()
    console.print(f"  {icon}  [bold]{fight.label}[/bold]")
    console.print()
    if fight.reason:
        console.print(f"  [dim]{fight.reason}[/dim]")
    console.print(f"  ............ [{style}]{result_label}[/{style}]")
    if fight.narrative:
        console.print()
        for line in _wrap_narrative(fight.narrative, width=60).split("\n"):
            console.print(f"  [italic]{line}[/italic]")
    console.print()
    _receipt_box([receipts.fight_receipt(fight)], title="Receipt")


def _run_gauntlet_paced(build: Build) -> None:
    """Render the boss gauntlet one fight at a time, pausing between fights.

    Each fight gets its own screen so the narrative has room to breathe.
    On a loss the student enters the reroll flow: crafted skills stack
    on ``build.skills_crafted``, mutate the fight in place, and the
    final verdict reflects the rerolled gauntlet.
    """
    console.print()
    console.print(Panel(
        Text("⚔️  Boss Gauntlet", style="bold magenta", justify="center"),
        border_style="magenta",
        padding=(0, 2),
    ))
    fights = build.gauntlet.fights
    for idx, fight in enumerate(fights):
        # Skills from earlier rerolls apply build-wide. Re-score this
        # fight with the current skill stack before rendering — a
        # prior craft may have already flipped a later fight.
        _apply_prior_skills_to_fight(build, fight)
        _print_fight(fight)
        if fight.result in ("lose", "draw"):
            _reroll_loss_flow(build, fight)
        if idx < len(fights) - 1:
            console.input("  [dim][Press Enter to continue][/dim] ")

    # Any reroll that flipped an outcome leaves the gauntlet totals
    # stale. Recompute before we print the summary and save the build.
    boss_fights.recompute_totals(build.gauntlet)
    gauntlet = build.gauntlet

    summary_bits: list[tuple[str, str]] = [
        ("🏆 Fight the Future — ", "bold"),
        (
            f"{gauntlet.wins}W / {gauntlet.losses}L / {gauntlet.draws}D\n",
            "bold cyan",
        ),
        (gauntlet.verdict, "italic"),
    ]
    if build.skills_crafted:
        crafted_summary = ", ".join(s.title for s in build.skills_crafted)
        summary_bits.append(("\n\nSkills crafted this run: ", "dim"))
        summary_bits.append((crafted_summary, "dim italic"))

    console.print()
    console.print(Panel(
        Text.assemble(*summary_bits),
        border_style="magenta",
        padding=(0, 2),
    ))

    console.print()
    console.print("[dim]Generating your next steps…[/dim]")
    checklist = next_steps.generate_next_steps(build)
    build.next_steps = checklist
    console.print()
    console.print(Panel(
        Markdown(checklist),
        title="[bold green]Your Next Steps[/bold green]",
        border_style="green",
        padding=(1, 2),
    ))
    _receipt_box(
        receipts.next_steps_receipt(build),
        title="Receipts: Next Steps Input",
    )


def _render_skill_options(
    skills: list[AppliedSkill],
    crafted_ids: set[str],
) -> None:
    """Numbered list of the skills the student can craft for this fight."""
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(style="dim", justify="right")
    table.add_column(style="bold")
    table.add_column(style="cyan")
    table.add_column()
    for idx, skill in enumerate(skills, start=1):
        marker = "✓" if skill.id in crafted_ids else f"{idx}."
        table.add_row(
            marker,
            skill.title,
            skill_pool.format_impact(skill),
            Text(skill.rationale, style="dim"),
        )
    console.print(table)


def _prompt_craft_selection(
    skills: list[AppliedSkill],
) -> list[AppliedSkill]:
    """Ask which skills to equip this iteration.

    Empty input / ``skip`` exits the reroll loop. Any other input is
    parsed as a comma-separated list of 1-based indices. Bad input
    re-prompts without equipping anything.
    """
    raw = Prompt.ask(
        "  [bold]Craft which?[/bold] [dim](numbers, comma-separated — "
        "[bold]Enter[/bold] to skip)[/dim]",
        default="",
        show_default=False,
    ).strip().lower()
    if not raw or raw in ("skip", "s", "no", "n", "done"):
        return []
    picks: list[AppliedSkill] = []
    for token in raw.split(","):
        token = token.strip()
        if not token.isdigit():
            console.print(f"  [red]'{token}' is not a number — skipping.[/red]")
            continue
        idx = int(token)
        if not 1 <= idx <= len(skills):
            console.print(
                f"  [red]{idx} is out of range (1-{len(skills)}).[/red]"
            )
            continue
        picks.append(skills[idx - 1])
    return picks


_OUTCOME_RANK: dict[str, int] = {"win": 3, "draw": 2, "lose": 1, "unknown": 0}


def _apply_prior_skills_to_fight(
    build: Build, fight: BossFightResult
) -> None:
    """Re-score a fight using skills already crafted in earlier fights.

    Skills are build-wide: if the student crafted RES+1 during Fight
    Student Loans, that +1 should already be live when Fight AI fires.
    The gauntlet scored all fights against the *original* career, so
    fights after the first reroll have stale scores. This helper
    patches that by re-running the scorer with the full crafted stack.
    """
    if not build.skills_crafted:
        return
    mutated = skill_pool.apply_skills(build.career, build.skills_crafted)
    rescored = boss_fights.rescore_fight(mutated, fight.boss)
    if rescored.result != fight.result:
        if not fight.rerolled:
            fight.original_result = fight.result
            fight.original_raw_score = fight.raw_score
        fight.rerolled = True
        fight.result = rescored.result
        fight.raw_score = rescored.raw_score
        fight.reason = rescored.reason


def _reroll_loss_flow(build: Build, fight: BossFightResult) -> None:
    """Offer skill crafting + reroll on a lost or drawn fight.

    Fires for any fight that is LOSE or DRAW. Always shows the student
    available skills and lets them craft + reroll. The "structural"
    message only appears *after* the pool is exhausted and the result
    still hasn't improved — as an outcome the student experienced, not
    a gate that blocked them from trying.

    Loops until:
    (a) the result strictly improves from the starting outcome
        (lose→draw, lose→win, draw→win),
    (b) the student skips (presses Enter without picking), or
    (c) the eligible skill pool is exhausted after at least one
        attempt.

    Skills crafted here join ``build.skills_crafted`` and apply
    build-wide to all subsequent fights in the same gauntlet.
    """
    starting_result = fight.result
    starting_rank = _OUTCOME_RANK.get(starting_result, 0)
    attempted_reroll = False

    while True:
        crafted_ids = {s.id for s in build.skills_crafted}
        effective_pool = build.skill_pool or skill_pool.FALLBACK_POOL
        eligible = skill_pool.get_skills_for_boss(
            fight.boss, effective_pool, exclude_ids=crafted_ids
        )

        if not eligible:
            # Only show the structural message if the student has
            # actually crafted skills and the result still hasn't
            # improved. If we get here on the very first iteration
            # (pool was empty from the start), that means either all
            # skills for this boss were consumed in earlier fights or
            # the pool generation missed this boss — still show the
            # message so the student understands the situation.
            if fight.result in ("lose", "draw"):
                console.print()
                label = (
                    "Structural loss"
                    if fight.result == "lose"
                    else "Structural draw"
                )
                msg = (
                    "Every available skill for this fight has been "
                    f"equipped, and the result is still a {fight.result}."
                    if attempted_reroll
                    else (
                        "No skills remain for this fight"
                        + (
                            " — earlier crafted skills already applied."
                            if build.skills_crafted
                            else "."
                        )
                    )
                )
                console.print(Panel(
                    Text(
                        f"{msg} That's the most important signal this "
                        "tool can give you: the gap isn't a skill-tree "
                        "problem. It's structural to this school + "
                        "major + career combination. Worth taking "
                        "seriously.",
                        style="italic",
                    ),
                    title=f"[bold]{label}[/bold]",
                    border_style="red",
                    padding=(1, 2),
                ))
            return

        console.print()
        console.print(Panel(
            Text(
                "Here's what would have changed that —",
                style="bold",
            ),
            title="[bold]🔧 Reroll: craft a skill[/bold]",
            border_style="yellow",
            padding=(0, 2),
        ))
        _render_skill_options(eligible, crafted_ids)

        picks = _prompt_craft_selection(eligible)
        if not picks:
            return

        build.skills_crafted.extend(picks)
        attempted_reroll = True

        pre_score = fight.raw_score
        pre_result = fight.result

        mutated_career = skill_pool.apply_skills(
            build.career, build.skills_crafted
        )
        rescored = boss_fights.rescore_fight(mutated_career, fight.boss)

        if not fight.rerolled:
            fight.original_result = fight.result
            fight.original_raw_score = fight.raw_score
        fight.rerolled = True
        fight.reroll_count += 1
        fight.result = rescored.result
        fight.raw_score = rescored.raw_score
        fight.reason = rescored.reason

        before = (fight.original_result or starting_result).upper()
        before_style = BOSS_RESULT_STYLE.get(
            fight.original_result or starting_result, "white"
        )
        after = fight.result.upper()
        after_style = BOSS_RESULT_STYLE.get(fight.result, "white")

        console.print()
        console.print(Text.assemble(
            ("  ", ""),
            (f"{before} → ", before_style),
            (after, after_style),
            (f"    [{fight.reason}]", "dim"),
        ))
        _receipt_box(
            receipts.reroll_receipt(fight, picks, pre_score, pre_result),
            title="Receipt: Reroll",
        )

        new_rank = _OUTCOME_RANK.get(fight.result, 0)
        if new_rank > starting_rank:
            console.print()
            console.print(
                "  [green]Crafted:[/green] "
                + ", ".join(s.title for s in picks)
            )
            with console.status("[cyan]thinking...[/cyan]"):
                commentary = boss_fights.generate_reroll_commentary(
                    career=build.career,
                    fight=fight,
                    original_result=fight.original_result or starting_result,
                    original_narrative=fight.narrative or "",
                    crafted_skill_titles=[
                        s.title for s in build.skills_crafted
                    ],
                )
            if commentary:
                console.print()
                console.print(Panel(
                    Text(commentary, style="italic"),
                    title="[bold]Gemma[/bold]",
                    border_style="bright_blue",
                    padding=(1, 2),
                ))
            return

        result_label = fight.result.lower()
        console.print()
        console.print(
            f"  [yellow]Still a {result_label}.[/yellow] "
            "[dim]Try equipping more skills, or press Enter to skip.[/dim]"
        )


def _wrap_narrative(text: str, width: int = 58) -> str:
    import textwrap

    return "\n".join(textwrap.wrap(text, width=width)) or text


def _render_branches(branches: list[CareerBranch]) -> Panel:
    if not branches:
        return Panel(
            Text("No Stage 3 branches available for this occupation.", style="dim"),
            title="[bold]🌳 Career Branches[/bold]",
            border_style="green",
        )
    table = Table(show_header=True, header_style="bold green", box=None)
    table.add_column("Branch")
    table.add_column("SOC")
    table.add_column("Deltas")
    table.add_column("Unlock")
    for branch in branches[:8]:
        deltas = [
            f"{name}{delta:+d}"
            for name, delta in (
                ("ERN", branch.delta_ern),
                ("ROI", branch.delta_roi),
                ("RES", branch.delta_res),
                ("GRW", branch.delta_grw),
                ("HMN", branch.delta_hmn),
            )
            if isinstance(delta, int) and delta != 0
        ]
        table.add_row(
            branch.to_title,
            branch.to_soc,
            ", ".join(deltas) or "—",
            branch.unlock or "—",
        )
    return Panel(
        table,
        title="[bold]🌳 Career Branches (Stage 3)[/bold]",
        border_style="green",
        padding=(1, 2),
    )


def _render_skill_recs(recs: list[SkillRec]) -> Panel:
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(style="bold")
    table.add_column(style="cyan")
    table.add_column()
    for rec in recs:
        table.add_row(
            f"• {rec.title}",
            rec.stat_impact,
            Text(rec.rationale, style="dim"),
        )
    return Panel(
        table,
        title="[bold]🎓 Skill Recommendations[/bold]",
        border_style="yellow",
        padding=(1, 2),
    )


def _render_guidance(text: str) -> Panel:
    return Panel(
        Text(text, style="italic"),
        title="[bold]💬 Gemma's Take[/bold]",
        border_style="bright_blue",
        padding=(1, 2),
    )


# ---------------------------------------------------------------------------
# Gemma intent resolution cache + flow (spike)
# ---------------------------------------------------------------------------

_intent_cache: dict[tuple[str, int], dict[str, Any]] = {}

# DUPLICATE: this prompt is mirrored in
# backend/app/services/intent.py:_INTENT_SYSTEM_PROMPT. Edits here MUST
# be applied to the service copy (consolidation tracked as follow-up in
# docs/specs/feature-gemma-tiered-matching.md §11).
_INTENT_SYSTEM_PROMPT = """\
You map a student's free-text major to a CIP (Classification of \
Instructional Programs) code. Pick the most specific CIP that matches \
their intent. Full stop.

Students, parents, counselors, and registrars describe the same program \
differently:
- Students: "pre-med", "CS", "business", "art"
- Parents: "Physical Therapy", "Deaf Education", "Criminal Justice"
- Counselors: "Special Ed", "STEM", "Allied Health"
- Registrars: "CIP 51.2308 Physical Therapy/Therapist"

Read through the surface form to the program underneath.

Confidence tiers drive how many alternatives you return.

- "high": The input resolves to exactly one CIP — no ambiguity, even if \
the phrasing is colloquial. Output exactly "alternatives": [].
  Example: "pre-PT" -> 51.2308 Physical Therapy/Therapist.

- "medium": The input is a well-known shorthand or umbrella term that \
maps to a primary CIP but reasonable students mean different things. \
Return 2-4 alternatives, ordered by how likely you'd pick each if the \
student had phrased it differently. Alternatives must be genuinely \
distinct programs and may span CIP families when a cross-family reading \
is plausible.
  Example: "business" (primary: 52.0201 Business Administration; \
alternatives: 52.0801 Finance, 52.1401 Marketing, 52.0701 \
Entrepreneurship, 42.2804 Industrial-Organizational Psychology).

- "low": The input is too vague, ambiguous, or non-program-like for you \
to stake a primary match confidently. Still return your best primary, \
but include up to 10 alternatives spanning the plausible CIP \
neighborhoods. The frontend will show a picker rather than your primary.
  Examples: "helping people", "something with computers but not coding".

Never pad. If you are high-confident, "alternatives" MUST be []. \
Never exceed 10.

The student typed: "{student_input}"
School: {school_name}

Candidate CIPs — programs reported by this school:
{school_cip_list}

Candidate CIPs — specific programs in the same families from the \
national crosswalk:
{crosswalk_cip_list}

Both lists above are equally valid match candidates. Do NOT prefer a \
school-reported CIP over a crosswalk CIP to "preserve earnings data" — \
the backend blends earnings automatically when it substitutes a broad \
school CIP with a specific cousin. Your job is the match; the blending \
is not yours to protect.

Respond in JSON only, no preamble, no markdown.

"matched_cip" MUST be the full 6-digit leaf format XX.XXXX (e.g. \
13.1001, 51.2308, 52.0201). NEVER put a 4-digit umbrella like XX.XX \
there — if the student's intent lands on a whole family rather than \
one specific program, pick the single most representative leaf from the \
candidates above and put the 4-digit family code in "parent_cip".

"reasoning" is shown to the student. Keep it to one or two sentences. \
Name the program and the tell that anchored the match. Direct, \
confident, no hedging. Do not say "based on" or "as an AI" or "I'm \
not certain" — state the call.

{{"matched_cip": "XX.XXXX", "matched_title": "Program Title", \
"confidence": "high|medium|low", \
"reasoning": "One or two sentences naming the program and why it fits.", \
"parent_cip": "XX.XX (4-digit family code, may equal matched_cip[:5] \
when matched_cip is already a leaf in this family)", \
"alternatives": []}}\
"""


def _get_school_cips(unitid: int) -> list[dict[str, str]]:
    """Get distinct CIP codes and program names for a school."""
    server = mcp_client.get_server()
    sql = (
        "SELECT DISTINCT cipcode, program_name "
        "FROM consumable_career_outcomes "
        f"WHERE unitid = {int(unitid)} "
        "ORDER BY cipcode"
    )
    try:
        rows = server.query_iceberg(sql)
    except Exception:
        return []
    return [
        {"cipcode": str(r["cipcode"]), "program_name": str(r.get("program_name", ""))}
        for r in rows
        if r.get("cipcode")
    ]


def _get_crosswalk_cips_for_families(
    family_prefixes: list[str],
) -> list[dict[str, str]]:
    """Get specific CIPs from the crosswalk for given families."""
    if not family_prefixes:
        return []
    server = mcp_client.get_server()
    conditions = " OR ".join(
        f"SUBSTR(cipcode, 1, 2) = '{p[:2]}'" for p in family_prefixes
    )
    sql = (
        f"SELECT DISTINCT cipcode, cip_title "
        f"FROM base_cip_soc_crosswalk "
        f"WHERE ({conditions}) "
        f"ORDER BY cipcode"
    )
    try:
        rows = server.query_iceberg(sql)
    except Exception:
        return []
    return [
        {"cipcode": str(r["cipcode"]), "cip_title": str(r.get("cip_title", ""))}
        for r in rows
        if r.get("cipcode")
    ]


def _get_career_titles_for_cip(cipcode: str) -> list[str]:
    """Get occupation titles from the crosswalk for a CIP code."""
    server = mcp_client.get_server()
    prefix = cipcode[:5] if len(cipcode) >= 5 else cipcode
    if not re.match(r"^\d{2}\.\d{2}", prefix):
        return []
    sql = (
        "SELECT DISTINCT soc_title "
        "FROM base_cip_soc_crosswalk "
        f"WHERE SUBSTR(cipcode, 1, 5) = '{prefix}' "
        "AND soc_title IS NOT NULL "
        "ORDER BY soc_title "
        "LIMIT 5"
    )
    try:
        rows = server.query_iceberg(sql)
    except Exception:
        return []
    return [str(r["soc_title"]) for r in rows if r.get("soc_title")]


def _call_gemma_intent(
    student_input: str,
    school_name: str,
    school_cips: list[dict[str, str]],
    crosswalk_cips: list[dict[str, str]],
    clarification: str | None = None,
) -> tuple[dict[str, Any] | None, float, dict[str, Any]]:
    """Call Gemma for intent resolution."""
    school_cip_list = "\n".join(
        f"- {c['cipcode']} {c['program_name']}" for c in school_cips
    )
    crosswalk_cip_list = "\n".join(
        f"- {c['cipcode']} {c['cip_title']}"
        for c in intent._sample_crosswalk(crosswalk_cips, max_total=60)
    )

    prompt_input = student_input
    if clarification:
        prompt_input = f"{student_input} (clarification: {clarification})"

    system = _INTENT_SYSTEM_PROMPT.format(
        student_input=prompt_input,
        school_name=school_name,
        school_cip_list=school_cip_list or "(no programs reported)",
        crosswalk_cip_list=crosswalk_cip_list or "(no crosswalk data)",
    )

    start = time.perf_counter()
    raw_response = gemma_client.generate(
        system=system,
        user=f'Match this student input to a CIP code: "{prompt_input}"',
        max_tokens=700,
        temperature=0.1,
    )
    latency = time.perf_counter() - start

    config = gemma_client.current_config()
    stats: dict[str, Any] = {
        "latency_s": round(latency, 2),
        "model": config.model,
        "backend": config.backend,
        "raw_response": raw_response,
    }

    if not raw_response:
        return None, latency, stats

    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    last_brace = cleaned.rfind("}")
    if last_brace != -1:
        cleaned = cleaned[: last_brace + 1]

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        stats["parse_error"] = f"Could not parse JSON: {cleaned[:200]}"
        return None, latency, stats

    return parsed, latency, stats


def _prompt_major_gemma_intent(
    school: SchoolMatch,
) -> tuple[Program, MajorMatch] | None:
    """Gemma intent resolution flow: free text → cache → Gemma → confirm."""
    status_msg = f"[cyan]loading programs for {school.institution_name}...[/cyan]"
    with console.status(status_msg):
        programs = school_lookup.get_programs(school.unitid)
    if not programs:
        console.print("[red]No programs found for this school.[/red]")
        return None

    while True:
        console.print()
        raw_input = Prompt.ask(
            "[bold]What do you want to study?[/bold]"
        ).strip()
        if not raw_input:
            return None
        if raw_input.lower() == "list":
            _show_programs(programs)
            continue

        # Numeric direct pick (unchanged from original flow)
        if raw_input.isdigit():
            idx = int(raw_input)
            if not 1 <= idx <= len(programs):
                console.print(
                    f"[red]{idx} is out of range (1-{len(programs)}). "
                    f"Type 'list' to see the picker.[/red]"
                )
                continue
            picked = programs[idx - 1]
            console.print(
                f"[green]Picked #{idx}:[/green] {picked.program_name} "
                f"[dim](CIP {picked.cipcode})[/dim]"
            )
            return picked, MajorMatch(
                method="exact",
                cipcode=picked.cipcode,
                program_name=picked.program_name,
            )

        normalized = raw_input.lower().strip()
        cache_key = (normalized, school.unitid)

        # --- Step 2: Cache check ---
        if cache_key in _intent_cache:
            cached = _intent_cache[cache_key]
            console.print()
            console.print(
                f"[cyan]🔁 Cache hit[/cyan] — using previous mapping: "
                f"[bold]{cached['title']}[/bold] (CIP {cached['cip']})"
            )
            return _build_program_from_intent(
                school, programs, cached, raw_input
            )

        # --- Step 3: Cache miss → Gemma intent resolution ---
        console.print()
        console.print("[dim]Cache miss — calling Gemma for intent resolution...[/dim]")

        with console.status("[cyan]loading school CIP data...[/cyan]"):
            school_cips = _get_school_cips(school.unitid)
            family_prefixes = list({c["cipcode"][:2] for c in school_cips})
            crosswalk_cips = _get_crosswalk_cips_for_families(family_prefixes)

        with console.status("[cyan]🤖 Gemma is thinking...[/cyan]"):
            parsed, latency, stats = _call_gemma_intent(
                raw_input,
                school.institution_name,
                school_cips,
                crosswalk_cips,
            )

        # Log spike metrics
        console.print()
        _receipt_box(
            [
                f"Latency: {stats['latency_s']:.2f}s",
                f"Model: {stats.get('model', '?')}",
                f"Backend: {stats.get('backend', '?')}",
                "Cache: MISS",
            ],
            title="Spike: Gemma Intent Resolution",
        )

        if parsed is None:
            console.print(
                f"[red]Gemma could not resolve '{raw_input}'.[/red]"
            )
            if stats.get("parse_error"):
                console.print(f"[dim]{stats['parse_error']}[/dim]")
            console.print("[dim]Try rephrasing or type 'list' to pick directly.[/dim]")
            continue

        # --- Step 4: Present to student for confirmation ---
        result = _present_intent_for_confirmation(
            school, programs, raw_input, parsed, stats,
            school_cips, crosswalk_cips,
        )
        if result is not None:
            return result
        # If None, loop back to ask again


def _present_intent_for_confirmation(
    school: SchoolMatch,
    programs: list[Program],
    student_input: str,
    parsed: dict[str, Any],
    stats: dict[str, Any],
    school_cips: list[dict[str, str]],
    crosswalk_cips: list[dict[str, str]],
) -> tuple[Program, MajorMatch] | None:
    """Show Gemma's match and let the student confirm, clarify, or pick alt."""
    matched_cip = str(parsed.get("matched_cip", ""))
    matched_title = str(parsed.get("matched_title", ""))
    confidence = str(parsed.get("confidence", "unknown"))
    reasoning = str(parsed.get("reasoning", ""))
    alternatives = parsed.get("alternatives") or []

    career_titles = _get_career_titles_for_cip(matched_cip)
    career_list = (
        "\n".join(f"   - {t}" for t in career_titles)
        if career_titles
        else "   (career data pending)"
    )

    console.print()
    console.print(Panel(
        Text.assemble(
            ("🤖 Gemma thinks ", ""),
            (f'"{student_input}"', "bold cyan"),
            (" maps to:\n", ""),
            (f"   {matched_title}", "bold"),
            (f" (CIP {matched_cip})\n\n", "dim"),
            ("   This would show you careers like:\n", ""),
            (f"{career_list}\n\n", "green"),
            ("   Gemma's reasoning: ", "dim"),
            (f'"{reasoning}"\n\n', "italic"),
            ("   Confidence: ", "dim"),
            (
                confidence,
                "bold cyan"
                if confidence == "high"
                else "bold yellow"
                if confidence == "medium"
                else "bold red",
            ),
        ),
        border_style="bright_blue",
        padding=(1, 2),
    ))

    console.print("  [bold][1][/bold] Yes, that's right")
    console.print("  [bold][2][/bold] Not quite — let me clarify")
    console.print("  [bold][3][/bold] Show me other options")

    choice = Prompt.ask(
        "", choices=["1", "2", "3"], default="1"
    ).strip()

    if choice == "1":
        # Confirmed — audit then save to cache
        return _audit_and_save(
            student_input, school.unitid, parsed, stats,
            career_titles, programs, school,
        )

    if choice == "2":
        # Clarification round
        clarification = Prompt.ask(
            "  [bold]What did you mean?[/bold]"
        ).strip()
        if not clarification:
            return None

        with console.status("[cyan]🤖 Gemma is re-thinking...[/cyan]"):
            parsed2, latency2, stats2 = _call_gemma_intent(
                student_input,
                school.institution_name,
                school_cips,
                crosswalk_cips,
                clarification=clarification,
            )

        console.print()
        _receipt_box(
            [
                f"Latency: {stats2['latency_s']:.2f}s",
                "Round: clarification",
                "Cache: MISS (clarification)",
            ],
            title="Spike: Gemma Intent Resolution (round 2)",
        )

        if parsed2 is None:
            console.print("[red]Gemma still couldn't resolve. Try 'list'.[/red]")
            return None

        return _present_intent_for_confirmation(
            school, programs, student_input, parsed2, stats2,
            school_cips, crosswalk_cips,
        )

    if choice == "3":
        # Show alternatives
        if not alternatives:
            console.print("[yellow]No alternatives suggested by Gemma.[/yellow]")
            return None
        console.print()
        for idx, alt in enumerate(alternatives, start=1):
            console.print(
                f"  [bold]{idx}.[/bold] {alt.get('title', '?')} "
                f"[dim](CIP {alt.get('cip', '?')})[/dim] — "
                f"{alt.get('why', '')}"
            )
        alt_choice = Prompt.ask(
            "  [bold]Pick one[/bold]",
            choices=[str(i) for i in range(1, len(alternatives) + 1)],
            default="1",
        ).strip()
        alt_idx = int(alt_choice) - 1
        alt_entry = alternatives[alt_idx]
        # Build a parsed dict from the alternative
        alt_parsed = {
            "matched_cip": alt_entry.get("cip", ""),
            "matched_title": alt_entry.get("title", ""),
            "confidence": "medium",
            "reasoning": alt_entry.get("why", "Selected from alternatives"),
            "parent_cip": parsed.get("parent_cip", ""),
            "alternatives": [],
        }
        alt_cip = str(alt_entry.get("cip", ""))
        alt_careers = _get_career_titles_for_cip(alt_cip)
        return _audit_and_save(
            student_input, school.unitid, alt_parsed, stats,
            alt_careers, programs, school,
        )

    return None


_AUDIT_SYSTEM_PROMPT = """\
You are an auditor checking whether a student's major selection makes sense.

The student typed: "{student_input}"
The system mapped it to: {matched_cip} — {matched_title}
Career outcomes for this mapping include: {top_3_career_titles}

Does the student's input plausibly refer to this academic program?

Respond in JSON only, no preamble, no markdown:
{{"valid": true|false, "tone": "clean|playful_warning|hard_reject", \
"message": "Your message to the student"}}

Rules:
- If the mapping is legitimate: valid=true, tone="clean", message is \
a brief encouraging confirmation
- If the input is vaguely off but close enough: valid=true, \
tone="playful_warning", message gently notes the mismatch but accepts it
- If the input is obviously nonsense, adversarial, or a joke: \
valid=false, tone="hard_reject", message calls it out directly. \
Be real with them. This is a $100K+ decision. Don't be mean, but \
don't play along. Example energy: "Look, this is one of the biggest \
financial decisions of your life. The tool works better when you give \
it something real. Try again."
- Keep it short — 1-2 sentences max
- Match the energy of a cool older sibling, not a guidance counselor\
"""


def _audit_intent_mapping(
    student_input: str,
    matched_cip: str,
    matched_title: str,
    career_titles: list[str],
) -> dict[str, Any] | None:
    """Call Gemma to audit a confirmed mapping. Returns parsed JSON."""
    top_3 = ", ".join(career_titles[:3]) or "unknown"
    system = _AUDIT_SYSTEM_PROMPT.format(
        student_input=student_input,
        matched_cip=matched_cip,
        matched_title=matched_title,
        top_3_career_titles=top_3,
    )
    raw = gemma_client.generate(
        system=system,
        user=(
            f'Student typed: "{student_input}"\n'
            f"Mapped to: {matched_cip} — {matched_title}\n"
            f"Careers: {top_3}\n"
            "Is this a valid mapping?"
        ),
        max_tokens=200,
        temperature=0.3,
    )
    if not raw:
        return None
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def _audit_and_save(
    student_input: str,
    unitid: int,
    parsed: dict[str, Any],
    stats: dict[str, Any],
    career_titles: list[str],
    programs: list[Program],
    school: SchoolMatch,
) -> tuple[Program, MajorMatch] | None:
    """Audit a confirmed mapping, save to cache if valid."""
    matched_cip = str(parsed.get("matched_cip", ""))
    matched_title = str(parsed.get("matched_title", ""))

    with console.status("[cyan]🔍 Gemma is auditing...[/cyan]"):
        audit = _audit_intent_mapping(
            student_input, matched_cip, matched_title, career_titles,
        )

    if audit is None:
        console.print(
            "[yellow]Audit inconclusive — saving anyway.[/yellow]"
        )
        cache_entry = _save_to_cache(
            student_input, unitid, parsed, stats,
        )
        return _build_program_from_intent(
            school, programs, cache_entry, student_input,
        )

    tone = str(audit.get("tone", "clean"))
    message = str(audit.get("message", ""))
    valid = bool(audit.get("valid", True))

    _receipt_box(
        [
            f"Valid: {valid}",
            f"Tone: {tone}",
            f"Message: {message[:80]}",
        ],
        title="Spike: Gemma Audit",
    )

    if valid and tone == "clean":
        console.print(f"\n[green]✅ {message}[/green]")
        cache_entry = _save_to_cache(
            student_input, unitid, parsed, stats,
        )
        return _build_program_from_intent(
            school, programs, cache_entry, student_input,
        )

    if valid and tone == "playful_warning":
        console.print(f"\n[yellow]⚠️  {message}[/yellow]")
        cache_entry = _save_to_cache(
            student_input, unitid, parsed, stats,
        )
        console.print(
            "[dim]💾 Mapping saved anyway — "
            "but keep that in mind.[/dim]"
        )
        return _build_program_from_intent(
            school, programs, cache_entry, student_input,
        )

    # hard_reject or any other invalid state
    console.print(f"\n[red]🚫 {message}[/red]")
    console.print("[dim]Let's try again.[/dim]")
    return None


def _save_to_cache(
    student_input: str,
    unitid: int,
    parsed: dict[str, Any],
    stats: dict[str, Any],
) -> dict[str, Any]:
    """Save a confirmed mapping to the intent cache."""
    normalized = student_input.lower().strip()
    config = gemma_client.current_config()
    entry = {
        "cip": str(parsed.get("matched_cip", "")),
        "title": str(parsed.get("matched_title", "")),
        "confidence": str(parsed.get("confidence", "unknown")),
        "reasoning": str(parsed.get("reasoning", "")),
        "parent_cip": str(parsed.get("parent_cip", "")),
        "confirmed_by_student": True,
        "confirmation_count": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "gemma_model": config.model,
        "original_input": student_input,
    }
    _intent_cache[(normalized, unitid)] = entry
    console.print(
        f"\n[green]💾 Mapping saved to cache:[/green] "
        f'"{student_input}" → {entry["cip"]} ({entry["title"]})'
    )
    return entry


def _build_program_from_intent(
    school: SchoolMatch,
    programs: list[Program],
    cache_entry: dict[str, Any],
    student_input: str,
) -> tuple[Program, MajorMatch]:
    """Build a Program + MajorMatch from a confirmed intent cache entry."""
    matched_cip = cache_entry["cip"]
    matched_title = cache_entry["title"]
    parent_cip = cache_entry.get("parent_cip", "")

    # If parent_cip differs from matched_cip, use parent for earnings lookup
    use_substitution = (
        parent_cip
        and parent_cip != matched_cip
        and len(parent_cip) >= 5
    )

    if use_substitution:
        broad = next(
            (p for p in programs if p.cipcode == parent_cip),
            None,
        )
        if broad is None:
            broad = next(
                (p for p in programs if p.cipcode.startswith(parent_cip[:2])),
                None,
            )
        chosen = Program(
            unitid=school.unitid,
            institution_name=school.institution_name,
            cipcode=parent_cip if broad else matched_cip,
            program_name=matched_title,
            cip_family_name=broad.cip_family_name if broad else None,
            earnings_1yr_median=broad.earnings_1yr_median if broad else None,
            debt_median=broad.debt_median if broad else None,
            confidence_tier=broad.confidence_tier if broad else None,
        )
        match = MajorMatch(
            method="gemma_intent",
            cipcode=matched_cip,
            program_name=matched_title,
            substitution_applied=True,
            reported_cipcode=parent_cip if broad else None,
            substituted_cipcode=matched_cip,
            note=(
                f"Gemma intent resolution: '{student_input}' → "
                f"{matched_title} ({matched_cip}). "
                f"School reports {parent_cip}; substituting for career paths."
            ),
        )
    else:
        direct = next(
            (p for p in programs if p.cipcode == matched_cip),
            None,
        )
        if direct is None:
            direct = next(
                (p for p in programs if p.cipcode.startswith(matched_cip[:5])),
                None,
            )
        chosen = direct or Program(
            unitid=school.unitid,
            institution_name=school.institution_name,
            cipcode=matched_cip,
            program_name=matched_title,
        )
        match = MajorMatch(
            method="gemma_intent",
            cipcode=matched_cip,
            program_name=matched_title,
            note=(
                f"Gemma intent resolution: '{student_input}' → "
                f"{matched_title} ({matched_cip})."
            ),
        )

    return chosen, match


# ---------------------------------------------------------------------------
# Interactive steps
# ---------------------------------------------------------------------------


def _prompt_school() -> SchoolMatch | None:
    while True:
        query = Prompt.ask("\n[bold]What school are you looking at?[/bold]").strip()
        if not query:
            return None
        with console.status("[cyan]searching schools...[/cyan]"):
            matches = school_lookup.search_schools(query)
        if not matches:
            console.print(f"[red]No schools matched '{query}'.[/red] Try again.")
            continue
        if len(matches) == 1:
            console.print(
                f"[green]Matched:[/green] {matches[0].institution_name} "
                f"({matches[0].unitid})"
            )
            return matches[0]
        console.print(f"\nFound {len(matches)} matches:")
        for idx, match in enumerate(matches, start=1):
            console.print(f"  {idx}. {match.institution_name} ({match.unitid})")
        choice = IntPrompt.ask(
            "Which one?",
            default=1,
            choices=[str(i) for i in range(1, len(matches) + 1)],
            show_choices=False,
        )
        return matches[choice - 1]


def _prompt_major(
    school: SchoolMatch,
) -> tuple[Program, MajorMatch] | None:
    status_msg = f"[cyan]loading programs for {school.institution_name}...[/cyan]"
    with console.status(status_msg):
        programs = school_lookup.get_programs(school.unitid)
    if not programs:
        console.print("[red]No programs found for this school.[/red]")
        return None

    while True:
        console.print(
            f"\nFound [bold]{len(programs)}[/bold] programs. "
            f"[dim]Type 'list' to see numbered picker, or a number "
            f"to pick directly.[/dim]"
        )
        major_text = Prompt.ask("[bold]What's your major?[/bold]").strip()
        if major_text.lower() == "list":
            _show_programs(programs)
            continue
        if not major_text:
            return None

        # Numeric input is a direct pick by 1-based index into the
        # program list. Resolves to the program name *before* any
        # Gemma calls, so the CIP mapper never sees a raw menu index.
        if major_text.isdigit():
            idx = int(major_text)
            if not 1 <= idx <= len(programs):
                console.print(
                    f"[red]{idx} is out of range (1-{len(programs)}). "
                    f"Type 'list' to see the picker.[/red]"
                )
                continue
            picked = programs[idx - 1]
            console.print(
                f"[green]Picked #{idx}:[/green] {picked.program_name} "
                f"[dim](CIP {picked.cipcode})[/dim]"
            )
            return picked, MajorMatch(
                method="exact",
                cipcode=picked.cipcode,
                program_name=picked.program_name,
            )

        with console.status("[cyan]resolving major...[/cyan]"):
            match = school_lookup.resolve_major(major_text, programs)

        if match.method == "unmatched":
            console.print(f"[red]{match.note}[/red]")
            continue

        # Pick a canonical Program to carry into the flow. When the
        # YAML lookup flagged substitution, pass the school's REPORTED
        # (broad) cipcode down to the MCP handler and let it swap in
        # the specific one — the handler does the blending. For exact
        # or substring matches the cipcode the user typed already
        # exists at the school so no substitution is required.
        if match.substitution_applied and match.reported_cipcode:
            broad = next(
                (p for p in programs if p.cipcode == match.reported_cipcode),
                None,
            )
            chosen = Program(
                unitid=school.unitid,
                institution_name=school.institution_name,
                cipcode=match.reported_cipcode,
                program_name=match.program_name or major_text,
                cip_family_name=broad.cip_family_name if broad else None,
                earnings_1yr_median=broad.earnings_1yr_median if broad else None,
                debt_median=broad.debt_median if broad else None,
                confidence_tier=broad.confidence_tier if broad else None,
            )
        else:
            direct = next(
                (p for p in programs if p.cipcode == match.cipcode),
                None,
            )
            chosen = direct or Program(
                unitid=school.unitid,
                institution_name=school.institution_name,
                cipcode=str(match.cipcode or ""),
                program_name=match.program_name or major_text,
            )

        console.print(
            f"[green]Matched:[/green] {chosen.program_name} "
            f"(CIP {chosen.cipcode}) [dim]via {match.method}[/dim]"
        )
        if match.note:
            console.print(f"  [yellow]ℹ {match.note}[/yellow]")
        return chosen, match


def _show_programs(programs: list[Program]) -> None:
    """Numbered program table. Index matches 1-based picker input."""
    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("#", style="dim", justify="right")
    table.add_column("CIP", style="dim")
    table.add_column("Program")
    for idx, program in enumerate(programs, start=1):
        table.add_row(str(idx), program.cipcode, program.program_name)
    console.print(table)


TIER_STYLES: dict[str, str] = {
    career_tiering.TIER_COMMON: "bold green",
    career_tiering.TIER_LESS_COMMON: "bold yellow",
    career_tiering.TIER_STRETCH: "bold magenta",
}


def _prompt_tiered_career_pick(
    tiers: OrderedDict[str, list[CareerOutcome]],
) -> CareerOutcome:
    """Render a tiered career menu and let the student pick any career.

    Numbers are continuous across tiers so the student can pick from
    any tier by entering a single number. Auto-returns the sole
    outcome when only one career is present.
    """
    # Flatten for the single-career short-circuit and to build the
    # global index.
    flat: list[CareerOutcome] = []
    for careers in tiers.values():
        flat.extend(careers)
    if len(flat) <= 1:
        return flat[0]

    console.print()
    console.print(Panel(
        Text("🎯  Choose Your Career Path", style="bold cyan", justify="center"),
        border_style="cyan",
        padding=(0, 2),
    ))

    global_idx = 0
    for tier_label, careers in tiers.items():
        if not careers:
            continue
        style = TIER_STYLES.get(tier_label, "bold")
        console.print(f"\n  [{style}]{tier_label}[/{style}]")
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="dim", justify="right")
        table.add_column()
        table.add_column(justify="right")
        table.add_column(justify="center")
        table.add_column()
        for career in careers:
            global_idx += 1
            wage = (
                f"${int(career.median_annual_wage):,}"
                if career.median_annual_wage
                else "[dim]—[/dim]"
            )
            stats_avail = (
                f"{career.stats_available_count}/5"
                if isinstance(career.stats_available_count, int)
                else "[dim]—[/dim]"
            )
            res_bar = _bar(career.stats.res, "magenta", width=8)
            title = (
                f"{career.occupation_title} "
                f"[dim]({career.soc_code})[/dim]"
            )
            table.add_row(str(global_idx), title, wage, stats_avail, res_bar)
        console.print(table)

    choice = IntPrompt.ask(
        "\nWhich career do you want to build around?",
        default=1,
        choices=[str(i) for i in range(1, len(flat) + 1)],
        show_choices=False,
    )
    return flat[choice - 1]


def _prompt_effort() -> EffortLevel:
    console.print("\n[bold]How much time will you have to focus on school?[/bold]")
    for idx, (label, _, _) in enumerate(EFFORT_CHOICES, start=1):
        console.print(f"  {idx}. {label}")
    choice = IntPrompt.ask(
        "",
        default=2,
        choices=["1", "2", "3"],
        show_choices=False,
    )
    return EFFORT_CHOICES[choice - 1][1]


def _prompt_loans() -> float:
    """Ask how much of the program's debt the student will finance."""
    console.print(
        "\n[bold]How much of your school costs will you cover with loans?"
        "[/bold]"
    )
    for idx, (label, _) in enumerate(LOAN_CHOICES, start=1):
        console.print(f"  {idx}. {label}")
    choice = IntPrompt.ask(
        "",
        default=5,
        choices=[str(i) for i in range(1, len(LOAN_CHOICES) + 1)],
        show_choices=False,
    )
    return LOAN_CHOICES[choice - 1][1]


# ---------------------------------------------------------------------------
# Build assembly
# ---------------------------------------------------------------------------


def _build_full(
    school: SchoolMatch,
    program: Program,
    major_match: MajorMatch,
    major_text: str,
    effort: EffortLevel,
    loan_pct: float,
) -> Build | None:
    # Pass student_major whenever the typed text differs from the
    # program name — that's what unlocks CIP substitution in the MCP
    # handler when the school only reports a broad CIP.
    pass_student_major = (
        major_text if major_match.substitution_applied else None
    )
    try:
        with console.status("[cyan]building your character...[/cyan]"):
            outcomes = stat_engine.compute_pentagon(
                unitid=school.unitid,
                cipcode=program.cipcode,
                student_major=pass_student_major,
                effort=effort,
                loan_pct=loan_pct,
            )
    except ValueError as exc:
        console.print(f"[red]Could not build character:[/red] {exc}")
        return None

    with console.status("[cyan]tiering career paths...[/cyan]"):
        tiers = career_tiering.tier_careers(
            outcomes,
            school_name=school.institution_name,
            program_name=program.program_name,
            cipcode=program.cipcode,
        )
    total_outcomes = sum(len(v) for v in tiers.values())
    career = _prompt_tiered_career_pick(tiers)
    _receipt_box(
        receipts.tiering_receipt(career, total_outcomes),
        title="Receipts: Career Matching",
    )

    with console.status("[cyan]running boss gauntlet...[/cyan]"):
        gauntlet = boss_fights.run_gauntlet(career)

    with console.status("[cyan]fetching career branches...[/cyan]"):
        branches = branch_tree.get_branches(career.soc_code)

    with console.status("[cyan]generating skill recommendations...[/cyan]"):
        recs = skill_recs.generate_recs(career, gauntlet)

    with console.status("[cyan]building reroll skill pool...[/cyan]"):
        reroll_pool = skill_pool.generate_pool(career, gauntlet)

    with console.status("[cyan]asking Gemma for her take...[/cyan]"):
        narrative = guidance.generate_guidance(career, gauntlet, branches)

    return builds.build_from_parts(
        school_name=school.institution_name,
        unitid=school.unitid,
        major_text=major_text,
        cipcode=program.cipcode,
        program_name=program.program_name,
        effort=effort,
        loan_pct=loan_pct,
        career=career,
        gauntlet=gauntlet,
        branches=branches,
        skill_recs=recs,
        guidance=narrative,
        skill_pool=reroll_pool,
    )


def _display_build(build: Build) -> None:
    # Lead with the narrative so stats read as proof, not as the headline.
    console.print()
    console.print(_render_career_header(build.career))
    console.print()
    console.print(_render_guidance(build.guidance))
    console.print()
    console.print(_render_pentagon(build.career.stats))
    _receipt_box(
        receipts.stats_receipt(build.career, build.effort, build.loan_pct),
        title="Receipts: Stats",
    )
    _run_gauntlet_paced(build)
    console.print()
    console.print(_render_branches(build.branches))
    console.print()
    console.print(_render_skill_recs(build.skill_recs))
    _receipt_box(
        receipts.skill_recs_receipt(build.career, build.gauntlet),
        title="Receipts: Skill Recommendations",
    )


# ---------------------------------------------------------------------------
# Menu loop
# ---------------------------------------------------------------------------


def _next_action_menu(build: Build) -> str:
    console.print()
    console.print(Panel(
        Text.assemble(
            ("[1]", "bold cyan"), (" Save this build\n", ""),
            ("[2]", "bold cyan"), (" Try a different school or major\n", ""),
            ("[3]", "bold cyan"), (" Compare saved builds\n", ""),
            ("[4]", "bold cyan"), (" Explore a career branch in detail\n", ""),
            ("[5]", "bold cyan"), (" Ask Gemma a question\n", ""),
            ("[6]", "bold cyan"), (" Download build report\n", ""),
            ("[7]", "bold cyan"), (" Explore career tree (experimental)\n", ""),
            ("[q]", "bold red"), (" Quit", ""),
        ),
        title="[bold]What next?[/bold]",
        border_style="cyan",
        padding=(1, 2),
    ))
    return Prompt.ask(
        "", choices=["1", "2", "3", "4", "5", "6", "7", "q"], default="2"
    ).strip().lower()


def _ask_gemma_flow(build: Build) -> None:
    """Freeform chat loop. Build context rides inside guidance.chat_with_context."""
    console.print()
    console.print(Panel(
        Text.assemble(
            ("Your build context is loaded. Ask anything about your "
             "school, major, career paths, or what to do while in "
             "school.\n", ""),
            ("Type ", "dim"),
            ("done", "bold"),
            (" to go back.", "dim"),
        ),
        title="[bold]💬 Ask Gemma[/bold]",
        border_style="bright_blue",
        padding=(1, 2),
    ))
    history: list[dict] = []
    while True:
        console.print()
        question = Prompt.ask("[bold cyan]You[/bold cyan]", default="").strip()
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


def _compare_flow() -> None:
    summaries = builds.list_builds()
    if len(summaries) < 2:
        console.print("[yellow]Need at least 2 saved builds to compare.[/yellow]")
        return
    table = Table(title="Saved builds", header_style="bold cyan")
    table.add_column("#", style="dim")
    table.add_column("ID")
    table.add_column("School")
    table.add_column("Major")
    table.add_column("Career")
    table.add_column("W/L")
    for idx, summary in enumerate(summaries, start=1):
        table.add_row(
            str(idx),
            summary.build_id,
            summary.school_name,
            summary.major_text,
            summary.career_title,
            f"{summary.wins}/{summary.losses}",
        )
    console.print(table)
    raw = Prompt.ask("Pick 2-3 numbers, comma-separated", default="1,2")
    try:
        indices = [int(p.strip()) for p in raw.split(",") if p.strip()]
    except ValueError:
        console.print("[red]Invalid input.[/red]")
        return
    picks = [
        summaries[i - 1].build_id
        for i in indices
        if 1 <= i <= len(summaries)
    ]
    if len(picks) < 2:
        console.print("[red]Pick at least two builds.[/red]")
        return
    comparison = builds.compare_builds(picks)
    _render_comparison(comparison)
    full_builds = [builds.load_build(bid) for bid in picks]
    path = report_gen.generate_comparison_report(comparison, full_builds)
    console.print(f"\n[green]Comparison report saved →[/green] {path}")


def _render_comparison(comparison: dict[str, Any]) -> None:
    build_labels = [b["label"] for b in comparison["builds"]]
    table = Table(show_header=True, header_style="bold cyan", title="Stat comparison")
    table.add_column("Stat")
    for label in build_labels:
        table.add_column(label)
    for row in comparison["stats"]:
        table.add_row(
            row["label"],
            *[str(v) if v is not None else "—" for v in row["values"]],
        )
    console.print(table)

    boss_table = Table(
        show_header=True, header_style="bold magenta", title="Boss results"
    )
    boss_table.add_column("Boss")
    for label in build_labels:
        boss_table.add_column(label)
    for row in comparison["bosses"]:
        boss_table.add_row(row["label"], *row["values"])
    console.print(boss_table)


def _branch_explore_flow(build: Build) -> None:
    if not build.branches:
        console.print("[yellow]No branches to explore for this career.[/yellow]")
        return
    table = Table(header_style="bold green")
    table.add_column("#", style="dim")
    table.add_column("Branch")
    table.add_column("SOC")
    table.add_column("Unlock")
    for idx, branch in enumerate(build.branches[:8], start=1):
        table.add_row(
            str(idx), branch.to_title, branch.to_soc, branch.unlock or "—"
        )
    console.print(table)
    raw = Prompt.ask("Branch number", default="1")
    try:
        idx = int(raw)
    except ValueError:
        return
    if not 1 <= idx <= len(build.branches):
        return
    branch = build.branches[idx - 1]
    console.print(Panel(
        Text.assemble(
            ("Branch: ", "bold"),
            (f"{branch.to_title} ({branch.to_soc})\n", "cyan"),
            ("Unlock: ", "bold"),
            (f"{branch.unlock or 'n/a'}\n", ""),
            ("Deltas: ", "bold"),
            (
                ", ".join(
                    f"{name}{delta:+d}"
                    for name, delta in (
                        ("ERN", branch.delta_ern),
                        ("ROI", branch.delta_roi),
                        ("RES", branch.delta_res),
                        ("GRW", branch.delta_grw),
                        ("HMN", branch.delta_hmn),
                    )
                    if isinstance(delta, int) and delta != 0
                )
                or "none",
                "",
            ),
        ),
        title="Branch detail",
        border_style="green",
    ))


def _career_tree_flow(build: Build) -> None:
    """Spike: generate and display a multi-level career tree."""
    console.print()
    console.print(Panel(
        Text(
            "Building a 3-level career tree from O*NET pathway data.\n"
            "This is experimental — testing data depth and quality.",
            style="dim",
        ),
        title="[bold]🌳 Career Tree (Experimental)[/bold]",
        border_style="green",
        padding=(1, 2),
    ))
    with console.status("[cyan]expanding career tree...[/cyan]"):
        root, stats = career_tree.build_tree(build, max_depth=3)
    console.print()
    tree_text = career_tree.render_tree(root)
    console.print(tree_text)
    console.print()
    console.print(Panel(
        Text(career_tree.format_summary(stats)),
        title="[bold]Spike metrics[/bold]",
        border_style="dim",
        padding=(0, 2),
    ))


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main() -> int:
    _banner()
    current_build: Build | None = None

    while True:
        if current_build is None:
            school = _prompt_school()
            if school is None:
                return 0
            prompt_result = _prompt_major_gemma_intent(school)
            if prompt_result is None:
                return 0
            program, major_match = prompt_result
            major_text = Prompt.ask(
                "[dim]Major label to save as[/dim]",
                default=program.program_name,
            )
            effort = _prompt_effort()
            loan_pct = _prompt_loans()
            build = _build_full(
                school, program, major_match, major_text, effort, loan_pct
            )
            if build is None:
                continue
            current_build = build
            _display_build(current_build)

        action = _next_action_menu(current_build)
        if action == "q":
            console.print("[dim]Good luck out there.[/dim]")
            return 0
        if action == "1":
            builds.save_build(current_build)
            console.print(
                f"[green]Saved →[/green] {current_build.build_id}"
            )
        elif action == "2":
            current_build = None
        elif action == "3":
            _compare_flow()
        elif action == "4":
            _branch_explore_flow(current_build)
        elif action == "5":
            _ask_gemma_flow(current_build)
        elif action == "6":
            console.print("[dim]Building career tree for report…[/dim]")
            try:
                tree_data: tuple | None = career_tree.build_tree(
                    current_build, max_depth=3
                )
            except Exception:
                tree_data = None
            path = report_gen.generate_build_report(
                current_build, tree=tree_data
            )
            console.print(f"[green]Report saved →[/green] {path}")
            try:
                subprocess.Popen(
                    ["open", "-a", "Typora", str(path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except FileNotFoundError:
                pass
        elif action == "7":
            _career_tree_flow(current_build)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")
        sys.exit(130)
