"""Ask Gemma — scope-aware chat surface for /my-build and the build
compare screen.

Single entry point ``chat_ask`` takes a discriminated ``AskScope``
(stat, boss, skill, build, compare) plus the student's message and
history, assembles a system prompt that grounds Gemma in the actual
numeric drivers behind the scope, and runs a four-tool MCP function-
calling loop for "what if" follow-ups.

Voice-contract discipline:
- The system prompt inherits ``_SHARED_VOICE_RULES`` from
  ``app.services.guidance`` so the ban list is enforced from a single
  source. ``test_gemma_voice_contract.py`` registers
  ``ask_gemma._SYSTEM_BASE`` and asserts the literal stat-code /
  outcome-label / game-framing tokens appear in the prompt.
- Context blocks wrap every stat code, outcome label, and game-framing
  word inside ``[helper: ...]`` spans so Gemma reads them but never
  echoes them. The system prompt instructs Gemma not to quote helper
  annotations verbatim.

Failure modes — all route to the localized ``chat_unavailable``
fallback string with status 200, never a 5xx:
- Gemma transport failure (returns empty string from
  ``generate_with_tools_loop``).
- Tool-dispatch error (``McpArgumentError`` from bad args from Gemma).
- Turn-cap exhaustion (``max_turns=3`` reached).
- Wall-time exhaustion (``max_wall_time_s=30.0`` reached).

See docs/specs/feature-ask-gemma.md.
"""

from __future__ import annotations

import logging
from typing import Any

from app.models.api import AskResponse, AskScope
from app.models.career import (
    AppliedSkill,
    BossFightResult,
    Build,
    CareerOutcome,
)
from app.services import gemma_client, mcp_client
from app.services.boss_fights import fmt_dollars
from app.services.guidance import _SHARED_VOICE_RULES
from app.services.locale import (
    AppLocale,
    fallback_text,
    gemma_language_instruction,
    normalize_locale,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool allowlist + tuning constants
# ---------------------------------------------------------------------------

# Five MCP tools that answer "what if" follow-ups. ``get_career_branches``
# was originally excluded (feature-ask-gemma.md Decision #6) on the
# assumption it was reachable via ``get_career_paths``; for branch-scoped
# chat (feature-tree-as-map.md Decision #2), on-demand branch fetching
# matters for "what if I pivoted to X" questions where X is not in the
# loaded build's tree, so the tool is now allowlisted at chat time.
# Excluded tools still have explicit reachability paths via these five:
#   - get_school_programs is fuzzy-search front-door (resolved via get_career_paths).
#   - get_task_breakdown / get_ai_exposure are inputs to context-builders,
#     not chat-time fetches.
_TOOLS: tuple[str, ...] = (
    "get_career_paths",
    "get_occupation_data",
    "get_regional_price_parity",
    "compare_purchasing_power",
    "get_career_branches",
)

# Lower than the 0.7 chat default. Under tool_choice="auto" Gemma 4 will
# speculatively call get_occupation_data / get_career_paths when context
# already answers the question; 0.4 strongly suppresses those redundant
# calls while keeping natural language flow. Chip dispatch uses 0.0 (it
# requires a tool call); Ask Gemma is the inverse and prefers context.
_TEMPERATURE = 0.4


# ---------------------------------------------------------------------------
# Aliases (binding for context-block formatting rule, §4)
# ---------------------------------------------------------------------------

_STAT_ALIAS: dict[str, str] = {
    "ERN": "Earning Power",
    "ROI": "Return on Investment",
    "RES": "AI Resilience",
    "GRW": "Growth Outlook",
    "HMN": "Human Edge",
}
_BOSS_ALIAS: dict[str, str] = {
    "ai": "AI Resilience risk",
    "loans": "Student Loans risk",
    "market": "Job Market risk",
    "burnout": "Burnout risk",
    "ceiling": "Career Ceiling risk",
}
_RESULT_ALIAS: dict[str, str] = {
    "win": "passed",
    "lose": "did not pass",
    "draw": "borderline",
    "unknown": "no result yet",
}


def _helper(text: str) -> str:
    """Wrap an internal annotation in a helper-bracket span. Gemma is
    instructed by ``_SYSTEM_BASE`` never to reproduce these verbatim."""
    return f"[helper: {text}]"


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_BASE = (
    "You are Gemma, in a chat thread with a high school student who is "
    "looking at the career path that comes out of their school and "
    "major. They're asking a follow-up question about one specific "
    "thing — a stat, a risk-category outcome, an applied skill, the "
    "whole build, or a comparison between builds. Answer it plainly "
    "and specifically.\n\n"
    f"{_SHARED_VOICE_RULES}\n\n"
    "The context block below already contains everything needed to "
    "answer questions about this build. Translate every figure into "
    "dollars, years, percentages, or plain comparisons before saying "
    "it back to the student. Never state a raw score, percentile, "
    "fraction (like '7/10'), or stat code in your reply.\n\n"
    "Lines beginning with `[helper:` are internal annotations for your "
    "reasoning only — never reproduce them verbatim or paraphrase "
    "their notation in your reply. Read what's inside the brackets, "
    "translate it to plain English, and write the plain-English "
    "version.\n\n"
    "Tools are available for questions that go BEYOND the loaded "
    "build: 'what if I went to school X?', 'what if I lived in state "
    "Y?', 'what does career Z look like long-term?'. For questions "
    "that can be answered from the loaded context (any question about "
    "the student's current build, stats, risk-category outcomes, or "
    "applied skills), answer from the context — do not call a tool.\n\n"
    "For 'what if I picked a different major?' questions: looking up "
    "a major requires a CIP code. If you don't know the exact CIP "
    "code for the major the student is asking about, tell them to "
    "start a new build with that major rather than guessing — do not "
    "call a tool with a made-up code.\n\n"
    "Keep replies to 4-8 sentences of plain prose at a 7th-grade "
    "reading level, unless the student asks for more detail."
)


# Appended to the system prompt only for branch-scoped chats. Keeps the
# shared voice rules untouched and surfaces the two branch-specific
# guards: noun-form labels and the verbatim-quoting convention that
# makes BranchHighlightDriver's response-text parsing reliable.
_BRANCH_VOICE_APPENDIX = (
    "\n\nBranch-specific rules for this conversation:\n"
    "- Branch labels in the context block are categories, not "
    "instructions. Do not use them as verbs. Refer to them by name "
    "with a natural noun form: 'the management track' instead of "
    "'go management,' 'the technical specialist path' instead of "
    "'specialize.'\n"
    "- When you refer to a specific branch by its exact label, put "
    "the label in quotation marks (the \"Go Management\" path, the "
    "\"Stay Technical\" track) so the student can see at a glance "
    "which branch you mean.\n"
    "- Never echo the word 'unlock' from the context block. The "
    "education-requirement is a description, not a game mechanic — "
    "say 'requires a master's degree' or 'most people who do this "
    "have a graduate degree' instead."
)


# Opener-mode user prompt — generated by the screen on first load and on
# every node click. The shape is fixed so Gemma produces a consistent
# 3-sentence orientation.
_OPENER_PROMPT = (
    "Give the student a 3-sentence orientation on this career path. "
    "Sentence 1: name the career and what it does in plain English. "
    "Sentence 2: name 1-3 of the available branches by their exact "
    "labels (in quotation marks) and what each one means as a "
    "direction. Sentence 3: invite the student to ask a follow-up "
    "question. Keep each sentence under 25 words."
)
_OPENER_PROMPT_BRANCH = (
    "Give the student a 3-sentence orientation on this branch. "
    "Sentence 1: name the branch (in quotation marks) and what it "
    "is as a direction from the current career. Sentence 2: name "
    "the strongest tradeoff (what gets better, what gets harder) "
    "in plain English using dollars/years/percentages from the "
    "context — never raw scores. Sentence 3: invite the student "
    "to ask a follow-up question. Keep each sentence under 25 words."
)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


class SkillNotFoundError(LookupError):
    """Raised when the skill_id in a skill scope is not on this build."""


async def chat_ask(
    *,
    scope: AskScope,
    builds: list[Build],
    message: str,
    history: list[dict[str, Any]],
    locale: AppLocale | None,
) -> AskResponse:
    """Single entry point for POST /chat/ask.

    The router resolves ``scope.build_ids`` to ``Build``s before
    calling. Empty string from the tool loop (any cause) routes to
    ``fallback_text("chat_unavailable", locale)`` with status 200.
    """
    norm_locale = normalize_locale(locale)

    # Build the context block per scope kind.
    if scope.kind == "stat":
        assert scope.target_id is not None  # validator guaranteed
        context_block = _context_for_stat(builds[0], scope.target_id)
    elif scope.kind == "boss":
        assert scope.target_id is not None
        context_block = _context_for_boss(builds[0], scope.target_id)
    elif scope.kind == "skill":
        assert scope.target_id is not None
        context_block = _context_for_skill(builds[0], scope.target_id)
    elif scope.kind == "build":
        context_block = _context_for_build(builds[0])
    elif scope.kind == "branch":
        assert scope.target_id is not None
        context_block = _context_for_branch(builds[0], scope.target_id)
    else:  # compare
        context_block = _context_for_compare(builds)

    # Assemble the full system prompt. Branch scope appends the
    # branch-specific voice appendix to keep the shared voice rules
    # untouched (feature-tree-as-map.md §4 voice-rule extensions).
    lang_block = gemma_language_instruction(norm_locale)
    system_base = (
        _SYSTEM_BASE + _BRANCH_VOICE_APPENDIX
        if scope.kind == "branch"
        else _SYSTEM_BASE
    )
    system = f"{system_base}\n\n{lang_block}\n\n{context_block}"

    # Branch-scope opener path: when history is empty, the call is the
    # auto-fired opener from the BranchTreeScreen mount or a node click.
    # Tools are disabled (the context block has every numeric driver
    # needed; speculative tool calls add 2-6s of latency for zero
    # accuracy gain). Subsequent turns (non-empty history) fall through
    # to the standard tool-loop path.
    if scope.kind == "branch" and not history:
        opener_user = (
            _OPENER_PROMPT
            if scope.target_id == builds[0].career.soc_code
            else _OPENER_PROMPT_BRANCH
        )
        text = await gemma_client.generate_async(
            system=system,
            user=opener_user,
            max_tokens=400,
            temperature=_TEMPERATURE,
            extra={
                "call_site": "ask_gemma_branch_opener",
                "scope_target_id": scope.target_id,
            },
        )
        if not text:
            logger.warning(
                "ask_gemma branch opener: empty text, using fallback"
            )
            text = fallback_text("chat_unavailable", norm_locale)
        return AskResponse(response=text, tool_calls=[])

    # Fold history into the user message. ``generate_with_tools_loop``
    # accepts a single user string; multi-turn fidelity for tool-loop
    # callers is a future enhancement (see spec §2 Out of Scope).
    user_msg = _fold_history(history, message)

    # Load tool schemas. Skip any tool the MCP server doesn't publish.
    tool_schemas: list[dict[str, Any]] = []
    for tool_name in _TOOLS:
        schema = mcp_client.get_tool_openai_schema(tool_name)
        if schema is not None:
            tool_schemas.append(schema)

    extra = {
        "call_site": f"ask_gemma_{scope.kind}",
        "scope_target_id": scope.target_id,
        "scope_build_count": len(scope.build_ids),
    }

    text, tool_call_log = await gemma_client.generate_with_tools_loop(
        system=system,
        user=user_msg,
        tools=tool_schemas,
        dispatch=_dispatch,
        max_turns=3,
        max_wall_time_s=30.0,
        temperature=_TEMPERATURE,
        max_tokens=1200,
        extra=extra,
    )

    if not text:
        logger.warning(
            "ask_gemma %s scope: empty text from tool loop, using fallback",
            scope.kind,
        )
        text = fallback_text("chat_unavailable", norm_locale)

    # Surface tool-call telemetry on AskResponse for the routing/E2E
    # test (test_tool_loop_dispatches_to_mcp). UI ignores it.
    tool_calls_summary = [
        {
            "tool": tc.tool_name,
            "ok": tc.error is None,
            "duration_ms": tc.duration_ms,
        }
        for tc in tool_call_log
    ]
    return AskResponse(response=text, tool_calls=tool_calls_summary)


async def _dispatch(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Trivial passthrough to MCP. Notably does NOT inject
    ``student_cip`` the way ``set_your_course.py`` does — Ask Gemma
    answers questions, it does not resolve the student's CIP."""
    return await mcp_client.call_async(name, args)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fold_history(history: list[dict[str, Any]], message: str) -> str:
    """Fold prior turns into the current user message.

    ``generate_with_tools_loop`` does not accept a message history (it
    takes ``system`` + ``user``). For v1 we fold history into the user
    message; richer multi-turn tool-loop callers are out of scope.
    """
    if not history:
        return message
    lines: list[str] = ["Previous turns in this conversation:"]
    for turn in history:
        role = turn.get("role") or "user"
        content = turn.get("content") or ""
        if not content:
            continue
        speaker = "Student" if role == "user" else "You"
        lines.append(f"  {speaker}: {content}")
    lines.append("")
    lines.append(f"Current question: {message}")
    return "\n".join(lines)


def _find_fight(build: Build, boss_id: str) -> BossFightResult | None:
    for fight in build.gauntlet.fights:
        if fight.boss == boss_id:
            return fight
    return None


def _find_skill(build: Build, skill_id: str) -> AppliedSkill | None:
    for skill in build.skills_crafted:
        if skill.id == skill_id:
            return skill
    for skill in build.skill_pool:
        if skill.id == skill_id:
            return skill
    return None


def _stat_value(career: CareerOutcome, stat_code: str) -> int | None:
    return getattr(career.stats, stat_code.lower(), None)


def _context_header(
    *,
    school: str,
    program: str,
    career_title: str,
) -> str:
    return (
        "[CONTEXT — already loaded, no tool call needed for this data]\n\n"
        f"Student's build:\n"
        f"- School: {school}\n"
        f"- Major: {program}\n"
        f"- Primary career: {career_title}\n"
    )


# ---------------------------------------------------------------------------
# Context-builders
# ---------------------------------------------------------------------------


def _context_for_stat(build: Build, stat_code: str) -> str:
    """Stat scope: the stat the student is asking about, plus its
    drivers from the §4 manifest. Codes/scores stay inside helper
    brackets; plain-English drivers (dollars, source description) are
    unbracketed."""
    career = build.career
    alias = _STAT_ALIAS[stat_code]
    score = _stat_value(career, stat_code)
    score_str = f"{score}/10" if score is not None else "no score available"

    header = _context_header(
        school=career.institution_name,
        program=career.program_name,
        career_title=career.occupation_title,
    )
    lines: list[str] = [
        header,
        f"The student is asking about: {alias}.",
        _helper(f"{alias} score = {score_str}"),
    ]

    if stat_code == "ERN":
        lines.append("")
        lines.append("Earning Power drivers (translate into dollars):")
        lines.append(
            f"- Median earnings 1 year after graduation from this program: "
            f"{fmt_dollars(career.earnings_1yr_median)}"
        )
        if career.earnings_1yr_p25 is not None and career.earnings_1yr_p75 is not None:
            lines.append(
                f"- Earnings range across this program's graduates: "
                f"{fmt_dollars(career.earnings_1yr_p25)} (25th percentile) to "
                f"{fmt_dollars(career.earnings_1yr_p75)} (75th percentile)"
            )
        if career.median_annual_wage is not None:
            lines.append(
                f"- Occupation-wide median wage (BLS, all workers in this "
                f"occupation, not just recent graduates): "
                f"{fmt_dollars(career.median_annual_wage)}"
            )
        if career.education_level_name:
            lines.append(
                f"- Typical entry education for this occupation: "
                f"{career.education_level_name}"
            )

    elif stat_code == "ROI":
        lines.append("")
        lines.append("Return on Investment drivers (translate into dollars):")
        if career.net_price_annual is not None:
            lines.append(
                f"- Net price per year after grants/scholarships: "
                f"{fmt_dollars(career.net_price_annual)}"
            )
        if career.cost_of_attendance_annual is not None:
            lines.append(
                f"- Sticker cost of attendance per year (before aid): "
                f"{fmt_dollars(career.cost_of_attendance_annual)}"
            )
        if career.modeled_total_debt is not None:
            lines.append(
                f"- Modeled total student debt at graduation: "
                f"{fmt_dollars(career.modeled_total_debt)} "
                f"(based on the student's chosen loan share of "
                f"{int(career.loan_pct * 100)}%)"
            )
        if career.earnings_1yr_median is not None:
            lines.append(
                f"- Starting median earnings: "
                f"{fmt_dollars(career.earnings_1yr_median)}"
            )
        if career.debt_to_earnings_annual is not None:
            lines.append(
                f"- Annual cost-to-earnings ratio: "
                f"{career.debt_to_earnings_annual:.2f}x "
                f"(annual cost divided by starting earnings)"
            )
        if career.financed_dte is not None:
            lines.append(
                f"- Financed debt-to-earnings ratio (loan-pct aware): "
                f"{career.financed_dte:.2f}x"
            )
        if career.roi_cost_basis:
            basis_words = {
                "cost_of_attendance": "net price after aid (preferred)",
                "debt_median": "median past-graduate debt (fallback)",
                "none": "neither input available",
            }
            lines.append(
                "- Cost basis used in the math: "
                f"{basis_words.get(career.roi_cost_basis, career.roi_cost_basis)}"
            )

    elif stat_code == "RES":
        lines.append("")
        lines.append("AI Resilience drivers (translate into plain English):")
        method = career.composite_method or "no_data"
        method_words = {
            "three_signal": (
                "based on real-world Claude usage data plus Karpathy's "
                "and Gemma's task-level estimates (the strongest signal)"
            ),
            "two_signal_no_anthropic": (
                "based on Karpathy and Gemma task-level estimates "
                "(no real-world Claude usage data yet)"
            ),
            "gemma_plus_anthropic": (
                "based on real-world Claude usage data plus Gemma's "
                "task-level estimates"
            ),
            "gemma_only": (
                "based only on Gemma's task-level estimates of how "
                "automatable each part of the work is"
            ),
            "karpathy_only": (
                "based only on Karpathy's general estimates for this "
                "career — the weaker signal"
            ),
            "observed_override": (
                "manually overridden from observed data"
            ),
            "no_data": "no source data available",
        }
        lines.append(f"- How this score was made: {method_words.get(method, method)}")
        if career.karpathy_score is not None:
            lines.append(_helper(f"Karpathy score = {career.karpathy_score}/10"))
        if career.ai_adoption_share is not None:
            pct = career.ai_adoption_share * 100
            lines.append(
                f"- Real-world Claude adoption for this kind of work: "
                f"about {pct:.1f}% of work tasks"
            )
        if career.adoption_percentile is not None:
            lines.append(
                _helper(
                    f"adoption percentile vs all SOC codes = "
                    f"{career.adoption_percentile:.0f}"
                )
            )
        if career.velocity_label and career.velocity_label != "unknown":
            velocity_words = {
                "saturating": "AI use in this work is leveling off",
                "accelerating": "AI use in this work is growing fast",
                "emerging": "AI use in this work is just starting",
                "nascent": "AI is barely used here yet",
            }
            lines.append(
                f"- Adoption trajectory: "
                f"{velocity_words.get(career.velocity_label, career.velocity_label)}"
            )
        if career.task_breakdown_human:
            human_tasks = ", ".join(career.task_breakdown_human[:3])
            lines.append(f"- Parts of the work that still need humans: {human_tasks}")
        if career.task_breakdown_automatable:
            auto_tasks = ", ".join(career.task_breakdown_automatable[:3])
            lines.append(
                f"- Parts of the work AI can already do well: {auto_tasks}"
            )
        if career.overall_confidence:
            lines.append(
                f"- Overall data confidence for this career: "
                f"{career.overall_confidence}"
            )

    elif stat_code == "GRW":
        lines.append("")
        lines.append("Growth Outlook drivers (translate into plain English):")
        gc = career.growth_category or "unknown"
        growth_words = {
            "growing_fast": (
                "BLS projects this occupation will grow much faster than "
                "average over the next 10 years"
            ),
            "growing": (
                "BLS projects this occupation will grow about as fast "
                "as average"
            ),
            "stable": (
                "BLS projects this occupation will hold roughly steady"
            ),
            "shrinking": (
                "BLS projects this occupation will shrink over the next "
                "10 years"
            ),
            "declining": (
                "BLS projects this occupation will decline meaningfully "
                "over the next 10 years"
            ),
            "unknown": "BLS does not have a growth projection for this occupation",
        }
        lines.append(
            f"- BLS 10-year projection: {growth_words.get(gc, gc)}"
        )
        lines.append(
            _helper(
                "no numeric employment_change_pct field on CareerOutcome — "
                "the qualitative growth_category is the only available signal"
            )
        )

    elif stat_code == "HMN":
        lines.append("")
        lines.append("Human Edge drivers (translate into plain English):")
        if career.top_human_activities:
            lines.append("- Top work activities that still need humans:")
            for activity in career.top_human_activities[:3]:
                title = activity.get("title") or activity.get("label") or "(unnamed)"
                importance = activity.get("importance")
                if isinstance(importance, (int, float)):
                    lines.append(
                        f"  - {title} "
                        + _helper(f"importance = {float(importance):.2f}")
                    )
                else:
                    lines.append(f"  - {title}")
        else:
            lines.append("- No human-activity breakdown available for this occupation")

    return "\n".join(lines)


def _context_for_boss(build: Build, boss_id: str) -> str:
    """Boss scope: the risk-category outcome the student is asking
    about, with raw score / thresholds / contributing drivers — all
    in helper brackets except plain-English narrative."""
    career = build.career
    fight = _find_fight(build, boss_id)
    boss_alias = _BOSS_ALIAS[boss_id]

    header = _context_header(
        school=career.institution_name,
        program=career.program_name,
        career_title=career.occupation_title,
    )
    lines: list[str] = [
        header,
        f"The student is asking about the {boss_alias} outcome.",
    ]

    if fight is None:
        lines.append(_helper("no result on this build for this risk"))
        return "\n".join(lines)

    result_alias = _RESULT_ALIAS.get(fight.result, fight.result)
    raw = fight.raw_score if fight.raw_score is not None else "n/a"
    lines.append(_helper(f"outcome = {result_alias}"))
    lines.append(
        _helper(
            f"raw score = {raw}; needed at least {fight.threshold_win} to "
            f"pass, at least {fight.threshold_draw} to be borderline"
        )
    )
    if fight.narrative:
        lines.append("")
        lines.append("Narrative shown to the student on the result screen:")
        lines.append(fight.narrative)
    if fight.reason:
        # ``reason`` is the scorer's internal summary string (e.g.
        # ``"RES 4 + HMN 5 = 9"``). It contains stat codes, so it MUST
        # live inside a [helper: ...] span — Gemma reads it for math
        # but the system prompt instructs her never to echo helper
        # spans verbatim.
        lines.append("")
        lines.append(_helper(f"reason summary = {fight.reason}"))

    if boss_id == "ai":
        if career.stats.res is not None:
            lines.append(_helper(f"AI Resilience component = {career.stats.res}/10"))
        if career.stats.hmn is not None:
            lines.append(_helper(f"Human Edge component = {career.stats.hmn}/10"))
        if career.task_breakdown_human:
            lines.append(
                "- Top parts of the work that still need humans: "
                + ", ".join(career.task_breakdown_human[:3])
            )

    elif boss_id == "loans":
        if career.stats.roi is not None:
            lines.append(_helper(f"Return on Investment score = {career.stats.roi}/10"))
        if career.financed_dte is not None:
            lines.append(
                f"- Financed debt-to-earnings ratio: {career.financed_dte:.2f}x"
            )
        if career.modeled_total_debt is not None:
            lines.append(
                f"- Modeled total debt at graduation: "
                f"{fmt_dollars(career.modeled_total_debt)}"
            )
        if career.earnings_1yr_median is not None:
            lines.append(
                f"- Starting median earnings: "
                f"{fmt_dollars(career.earnings_1yr_median)}"
            )

    elif boss_id == "market":
        if career.stats.grw is not None:
            lines.append(_helper(f"Growth Outlook score = {career.stats.grw}/10"))
        if career.growth_category:
            lines.append(f"- BLS growth category: {career.growth_category}")

    elif boss_id == "burnout":
        if career.stats.hmn is not None:
            lines.append(_helper(f"Human Edge score = {career.stats.hmn}/10"))
        if career.burnout_drivers:
            lines.append("- Top burnout-correlated work demands:")
            for driver in career.burnout_drivers[:3]:
                title = driver.get("title") or driver.get("label") or "(unnamed)"
                importance = driver.get("importance")
                if isinstance(importance, (int, float)):
                    lines.append(
                        f"  - {title} "
                        + _helper(f"importance = {float(importance):.2f}")
                    )
                else:
                    lines.append(f"  - {title}")

    elif boss_id == "ceiling":
        if career.stats.ern is not None:
            lines.append(_helper(f"Earning Power score = {career.stats.ern}/10"))
        if career.education_level_name:
            lines.append(f"- Typical entry education: {career.education_level_name}")
        if career.earnings_1yr_p75 is not None:
            lines.append(
                f"- Top-quartile starting earnings from this program: "
                f"{fmt_dollars(career.earnings_1yr_p75)} (a sense of the "
                f"upper end early in the career)"
            )

    return "\n".join(lines)


def _context_for_skill(build: Build, skill_id: str) -> str:
    """Skill scope: the AppliedSkill the student is asking about, its
    deltas, and the build's current stats so Gemma can reason about
    post-application effects."""
    career = build.career
    skill = _find_skill(build, skill_id)
    if skill is None:
        raise SkillNotFoundError(
            f"skill_id {skill_id!r} is not on build {build.build_id!r}"
        )

    header = _context_header(
        school=career.institution_name,
        program=career.program_name,
        career_title=career.occupation_title,
    )
    lines: list[str] = [
        header,
        f'The student is asking about the skill: "{skill.title}".',
        f"Why we recommended it: {skill.rationale}",
    ]
    if skill.targets:
        target_aliases = ", ".join(_BOSS_ALIAS[t] for t in skill.targets)
        lines.append(_helper(f"targets these risk categories: {target_aliases}"))

    # Stat deltas (helper-bracketed)
    delta_parts: list[str] = []
    for stat_code, attr in (
        ("ERN", "delta_ern"),
        ("ROI", "delta_roi"),
        ("RES", "delta_res"),
        ("GRW", "delta_grw"),
        ("HMN", "delta_hmn"),
    ):
        delta = getattr(skill, attr)
        if delta:
            sign = "+" if delta > 0 else ""
            delta_parts.append(f"{_STAT_ALIAS[stat_code]} {sign}{delta}")
    if delta_parts:
        lines.append(
            _helper("stat-score deltas if applied: " + "; ".join(delta_parts))
        )

    # Boss raw-score deltas
    raw_parts: list[str] = []
    if skill.delta_burnout_raw:
        sign = "+" if skill.delta_burnout_raw > 0 else ""
        raw_parts.append(f"Burnout raw score {sign}{skill.delta_burnout_raw}")
    if skill.delta_ceiling_raw:
        sign = "+" if skill.delta_ceiling_raw > 0 else ""
        raw_parts.append(f"Career Ceiling raw score {sign}{skill.delta_ceiling_raw}")
    if raw_parts:
        lines.append(_helper("raw-score deltas if applied: " + "; ".join(raw_parts)))

    # Current stats (so Gemma can reason about post-application values)
    lines.append("")
    lines.append("Current build stats (translate into plain English):")
    for stat_code in ("ERN", "ROI", "RES", "GRW", "HMN"):
        v = _stat_value(career, stat_code)
        if v is not None:
            lines.append(_helper(f"current {_STAT_ALIAS[stat_code]} = {v}/10"))

    # Targeted boss outcomes
    if skill.targets:
        lines.append("")
        lines.append("Current outcomes for the risk categories this skill targets:")
        for boss_id in skill.targets:
            fight = _find_fight(build, boss_id)
            if fight is None:
                continue
            result_alias = _RESULT_ALIAS.get(fight.result, fight.result)
            raw = fight.raw_score if fight.raw_score is not None else "n/a"
            lines.append(
                _helper(
                    f"{_BOSS_ALIAS[boss_id]} = {result_alias} "
                    f"(raw {raw}; passes at {fight.threshold_win}, "
                    f"borderline at {fight.threshold_draw})"
                )
            )

    return "\n".join(lines)


def _context_for_build(build: Build) -> str:
    """Whole-build scope: every stat with key drivers, every risk
    outcome, finances, applied skills, branches, recs."""
    career = build.career
    header = _context_header(
        school=career.institution_name,
        program=career.program_name,
        career_title=career.occupation_title,
    )
    lines: list[str] = [
        header,
        "The student is asking about their whole build.",
        "",
        "Pentagon stats (translate into plain English):",
    ]
    for stat_code in ("ERN", "ROI", "RES", "GRW", "HMN"):
        v = _stat_value(career, stat_code)
        if v is not None:
            lines.append(_helper(f"{_STAT_ALIAS[stat_code]} = {v}/10"))

    # Stat-level drivers (collapsed)
    lines.append("")
    lines.append("Key drivers behind those stats:")
    if career.earnings_1yr_median is not None:
        lines.append(
            f"- Starting median earnings: {fmt_dollars(career.earnings_1yr_median)}"
        )
    if career.earnings_1yr_p75 is not None:
        lines.append(
            f"- Top-quartile starting earnings from this program: "
            f"{fmt_dollars(career.earnings_1yr_p75)}"
        )
    if career.net_price_annual is not None:
        lines.append(
            f"- Net price per year after aid: "
            f"{fmt_dollars(career.net_price_annual)}"
        )
    if career.modeled_total_debt is not None:
        lines.append(
            f"- Modeled total student debt at graduation: "
            f"{fmt_dollars(career.modeled_total_debt)} "
            f"(loan share {int(career.loan_pct * 100)}%)"
        )
    if career.debt_to_earnings_annual is not None:
        lines.append(
            f"- Annual cost-to-earnings ratio: "
            f"{career.debt_to_earnings_annual:.2f}x"
        )
    if career.growth_category:
        lines.append(f"- BLS 10-year growth category: {career.growth_category}")
    if career.composite_method:
        lines.append(f"- AI-exposure data source: {career.composite_method}")
    if career.education_level_name:
        lines.append(f"- Typical entry education: {career.education_level_name}")

    # Risk outcomes
    lines.append("")
    lines.append("Risk-category outcomes:")
    for fight in build.gauntlet.fights:
        boss_alias = _BOSS_ALIAS.get(fight.boss, fight.boss)
        result_alias = _RESULT_ALIAS.get(fight.result, fight.result)
        raw = fight.raw_score if fight.raw_score is not None else "n/a"
        lines.append(
            _helper(
                f"{boss_alias}: {result_alias} (raw {raw}; passes at "
                f"{fight.threshold_win}, borderline at {fight.threshold_draw})"
            )
        )
        if fight.narrative:
            lines.append(f"  Narrative: {fight.narrative}")

    # Applied skills
    if build.skills_crafted:
        lines.append("")
        lines.append("Skills the student has crafted:")
        for skill in build.skills_crafted:
            lines.append(f'- "{skill.title}" — {skill.rationale}')
            delta_parts: list[str] = []
            for stat_code, attr in (
                ("ERN", "delta_ern"),
                ("ROI", "delta_roi"),
                ("RES", "delta_res"),
                ("GRW", "delta_grw"),
                ("HMN", "delta_hmn"),
            ):
                d = getattr(skill, attr)
                if d:
                    delta_parts.append(f"{_STAT_ALIAS[stat_code]} {d:+d}")
            if delta_parts:
                lines.append(
                    "  " + _helper("deltas: " + "; ".join(delta_parts))
                )

    # Branches
    if build.branches:
        lines.append("")
        lines.append("Career branches available from this build:")
        for branch in build.branches[:5]:
            lines.append(f"- {branch.to_title}")

    # Skill recs
    if build.skill_recs:
        lines.append("")
        lines.append("Skill recommendations Gemma generated for this build:")
        for rec in build.skill_recs[:5]:
            lines.append(f"- {rec.title}: {rec.rationale}")

    return "\n".join(lines)


def _context_for_branch(build: Build, target_id: str) -> str:
    """Branch scope: the career-path branch (or root career anchor)
    the student is asking about, with stat deltas + education
    requirement + relatedness signal.

    Three resolution cases:
    1. ``target_id`` matches a ``CareerBranch.to_soc`` in
       ``build.branches`` → branch-specific context block.
    2. ``target_id`` matches ``build.career.soc_code`` → root-anchored
       case: enumerate up to 3 branches, sorted by ``relatedness DESC``
       (genai-architect Finding 9; ``CareerBranch.level`` does not
       exist on the model).
    3. ``target_id`` resolves to nothing → thin-data block pointing
       Gemma at ``get_occupation_data`` for the root SOC.
    """
    career = build.career
    header = _context_header(
        school=career.institution_name,
        program=career.program_name,
        career_title=career.occupation_title,
    )
    lines: list[str] = [header]

    # Case 1: target_id matches a branch.
    matched_branch = next(
        (b for b in build.branches if b.to_soc == target_id),
        None,
    )

    if matched_branch is not None:
        lines.append(
            f'The student is asking about the branch: "{matched_branch.to_title}".'
        )
        lines.append(
            f"They're considering this as a direction from their current "
            f"career, {career.occupation_title}."
        )

        # Stat deltas — helper-bracketed; Gemma must translate to plain
        # English (dollars/years/qualitative) before output.
        delta_parts: list[str] = []
        for stat_code, attr in (
            ("ERN", "delta_ern"),
            ("ROI", "delta_roi"),
            ("RES", "delta_res"),
            ("GRW", "delta_grw"),
            ("HMN", "delta_hmn"),
        ):
            delta = getattr(matched_branch, attr)
            if delta:
                sign = "+" if delta > 0 else ""
                delta_parts.append(f"{_STAT_ALIAS[stat_code]} {sign}{delta}")
        if delta_parts:
            lines.append(
                _helper(
                    "stat-score deltas if the student takes this branch: "
                    + "; ".join(delta_parts)
                )
            )

        # Education requirement — wrap ``unlock`` in helper bracket so
        # Gemma reads but never echoes the word "unlock"
        # (genai-architect Finding 6). Prefer ``related_education_level``
        # (typed) over ``unlock`` (display string).
        if matched_branch.related_education_level:
            lines.append(
                _helper(
                    f"education required: {matched_branch.related_education_level}"
                )
            )
        elif matched_branch.unlock:
            lines.append(
                _helper(f'education required: "{matched_branch.unlock}"')
            )

        # Relatedness — helper-bracketed signal for "how close is this
        # to today's career."
        if matched_branch.relatedness is not None:
            lines.append(
                _helper(
                    f"relatedness to current career = "
                    f"{matched_branch.relatedness:.2f} "
                    f"(1.0 is identical, 0.0 is unrelated)"
                )
            )

        # O*NET experience signal when populated.
        if matched_branch.experience_tier:
            lines.append(
                _helper(
                    f"typical experience tier on this destination: "
                    f"{matched_branch.experience_tier}"
                )
            )

        # Wage anchor — root career's median wage. Branch-destination
        # wage is not on the Pydantic model; if the student asks, Gemma
        # can call get_occupation_data on the branch's to_soc.
        lines.append("")
        lines.append("Current career wage reference (for translating deltas):")
        if career.median_annual_wage is not None:
            lines.append(
                f"- Occupation-wide median wage today: "
                f"{fmt_dollars(career.median_annual_wage)}"
            )
        if career.earnings_1yr_median is not None:
            lines.append(
                f"- Starting median earnings from this program: "
                f"{fmt_dollars(career.earnings_1yr_median)}"
            )

        # Available branch labels — verbatim list so Gemma can quote
        # them exactly (BranchHighlightDriver does response-text
        # parsing against TreeNode.title; verbatim quoting makes the
        # parse reliable — Decision #4 hardening).
        if build.branches:
            lines.append("")
            lines.append(
                "All branch labels available on this build (use exact "
                "wording when referring to one):"
            )
            for b in build.branches[:8]:
                lines.append(f'- "{b.to_title}"')

        lines.append("")
        lines.append(
            _helper(
                "when you refer to a specific branch in your response, "
                "use its exact label as listed above in quotation marks. "
                "Do not paraphrase the label."
            )
        )

        return "\n".join(lines)

    # Case 2: target_id matches root SOC — anchor-at-root case.
    if target_id == career.soc_code:
        lines.append("The student is sitting at the root of their career path.")
        lines.append(
            f"Their current career is {career.occupation_title}. They're "
            f"asking about which branches open up from here."
        )

        # Pentagon stats so Gemma can root the conversation.
        lines.append("")
        lines.append("Current career stats (translate into plain English):")
        for stat_code in ("ERN", "ROI", "RES", "GRW", "HMN"):
            v = _stat_value(career, stat_code)
            if v is not None:
                lines.append(_helper(f"{_STAT_ALIAS[stat_code]} = {v}/10"))

        if career.median_annual_wage is not None:
            lines.append(
                f"- Occupation-wide median wage: "
                f"{fmt_dollars(career.median_annual_wage)}"
            )
        if career.earnings_1yr_median is not None:
            lines.append(
                f"- Starting median earnings from this program: "
                f"{fmt_dollars(career.earnings_1yr_median)}"
            )

        # Branch enumeration — relatedness-DESC selection
        # (genai-architect Finding 9). Up to 3 branches with one-line
        # positioning per branch.
        if build.branches:
            ranked = [
                b for b in build.branches if b.relatedness is not None
            ]
            ranked.sort(
                key=lambda b: b.relatedness or 0.0,
                reverse=True,
            )
            if not ranked:
                # Null relatedness on every branch — fall back to list
                # order from build.branches.
                ranked = list(build.branches)
            highlighted = ranked[:3]

            lines.append("")
            lines.append("Available branches from this career:")
            for b in highlighted:
                delta_summary_parts: list[str] = []
                for stat_code, attr in (
                    ("ERN", "delta_ern"),
                    ("RES", "delta_res"),
                    ("GRW", "delta_grw"),
                    ("HMN", "delta_hmn"),
                ):
                    delta = getattr(b, attr)
                    if delta:
                        sign = "+" if delta > 0 else ""
                        delta_summary_parts.append(
                            f"{_STAT_ALIAS[stat_code]} {sign}{delta}"
                        )
                summary_helper = (
                    " " + _helper("; ".join(delta_summary_parts))
                    if delta_summary_parts
                    else ""
                )
                lines.append(f'- "{b.to_title}"{summary_helper}')

            remaining = len(build.branches) - len(highlighted)
            if remaining > 0:
                lines.append(f"- plus {remaining} more pathway(s)")

            lines.append("")
            lines.append(
                _helper(
                    "when you refer to a specific branch in your response, "
                    "use its exact label as listed above in quotation marks. "
                    "Do not paraphrase the label."
                )
            )
        else:
            # Root anchor with empty branches — thin-data fallback.
            lines.append("")
            lines.append(
                "This career has limited transition data — no branches "
                "are mapped from it in our gold-zone tables."
            )
            lines.append(
                f"- SOC code for occupation lookup: {career.soc_code}"
            )
            lines.append(
                _helper(
                    "if the student asks about transitions or adjacencies "
                    "for this career, point them at occupation-level "
                    "guidance via get_occupation_data; do not fabricate "
                    "branches."
                )
            )

        return "\n".join(lines)

    # Case 3: target_id resolves to nothing — thin-data block.
    lines.append(
        f"The student is asking about a branch with SOC {target_id}, but "
        f"that branch isn't loaded on this build."
    )
    lines.append(
        f"- Root career SOC code for occupation lookup: {career.soc_code}"
    )
    lines.append(
        _helper(
            "this career has limited transition data — point the student "
            "at occupation-level guidance via get_occupation_data; do not "
            "fabricate branch information."
        )
    )
    return "\n".join(lines)


def _context_for_compare(builds_in_scope: list[Build]) -> str:
    """Compare scope: per-build values + pairwise plain-dollar deltas
    for headline figures."""
    if not builds_in_scope:
        return _helper("no builds passed to compare context")

    header_lines: list[str] = [
        "[CONTEXT — already loaded, no tool call needed for this data]\n",
        f"The student is comparing {len(builds_in_scope)} builds.",
        "",
        "Per-build snapshot:",
    ]

    per_build_lines: list[str] = []
    for idx, build in enumerate(builds_in_scope):
        career = build.career
        per_build_lines.append("")
        per_build_lines.append(
            f"Build {idx + 1}: {career.institution_name} — "
            f"{career.program_name} → {career.occupation_title}"
        )
        for stat_code in ("ERN", "ROI", "RES", "GRW", "HMN"):
            v = _stat_value(career, stat_code)
            if v is not None:
                per_build_lines.append(
                    "  " + _helper(f"{_STAT_ALIAS[stat_code]} = {v}/10")
                )
        for fight in build.gauntlet.fights:
            boss_alias = _BOSS_ALIAS.get(fight.boss, fight.boss)
            result_alias = _RESULT_ALIAS.get(fight.result, fight.result)
            per_build_lines.append(
                "  " + _helper(f"{boss_alias}: {result_alias}")
            )
        if career.net_price_annual is not None:
            per_build_lines.append(
                f"  - Net price per year after aid: "
                f"{fmt_dollars(career.net_price_annual)}"
            )
        if career.cost_of_attendance_annual is not None:
            per_build_lines.append(
                f"  - Sticker cost of attendance per year: "
                f"{fmt_dollars(career.cost_of_attendance_annual)}"
            )
        if career.modeled_total_debt is not None:
            per_build_lines.append(
                f"  - Modeled total debt at graduation: "
                f"{fmt_dollars(career.modeled_total_debt)} "
                f"(loan share {int(career.loan_pct * 100)}%)"
            )
        if career.debt_to_earnings_annual is not None:
            per_build_lines.append(
                f"  - Annual cost-to-earnings ratio: "
                f"{career.debt_to_earnings_annual:.2f}x"
            )
        if career.earnings_1yr_median is not None:
            per_build_lines.append(
                f"  - Starting median earnings: "
                f"{fmt_dollars(career.earnings_1yr_median)}"
            )

    delta_lines: list[str] = ["", "Headline differences (plain dollars):"]
    pairs = [
        (i, j)
        for i in range(len(builds_in_scope))
        for j in range(i + 1, len(builds_in_scope))
    ]
    for i, j in pairs:
        a = builds_in_scope[i].career
        b = builds_in_scope[j].career
        a_name = _short_school_name(a.institution_name)
        b_name = _short_school_name(b.institution_name)
        if a.net_price_annual is not None and b.net_price_annual is not None:
            diff = abs(a.net_price_annual - b.net_price_annual)
            higher = a_name if a.net_price_annual > b.net_price_annual else b_name
            delta_lines.append(
                f"- {a_name} net price: {fmt_dollars(a.net_price_annual)}/yr; "
                f"{b_name}: {fmt_dollars(b.net_price_annual)}/yr — "
                f"{higher} is {fmt_dollars(diff)}/yr higher."
            )
        if (
            a.modeled_total_debt is not None
            and b.modeled_total_debt is not None
        ):
            diff = abs(a.modeled_total_debt - b.modeled_total_debt)
            higher = a_name if a.modeled_total_debt > b.modeled_total_debt else b_name
            delta_lines.append(
                f"- {a_name} modeled total debt: "
                f"{fmt_dollars(a.modeled_total_debt)}; "
                f"{b_name}: {fmt_dollars(b.modeled_total_debt)} — "
                f"{higher} carries {fmt_dollars(diff)} more debt."
            )
        if (
            a.earnings_1yr_median is not None
            and b.earnings_1yr_median is not None
        ):
            diff = abs(a.earnings_1yr_median - b.earnings_1yr_median)
            higher = (
                a_name
                if a.earnings_1yr_median > b.earnings_1yr_median
                else b_name
            )
            delta_lines.append(
                f"- {a_name} starting earnings: "
                f"{fmt_dollars(a.earnings_1yr_median)}; "
                f"{b_name}: {fmt_dollars(b.earnings_1yr_median)} — "
                f"{higher} pays {fmt_dollars(diff)}/yr more out of the gate."
            )
        if (
            a.debt_to_earnings_annual is not None
            and b.debt_to_earnings_annual is not None
        ):
            diff = abs(
                a.debt_to_earnings_annual - b.debt_to_earnings_annual
            )
            higher = (
                a_name
                if a.debt_to_earnings_annual > b.debt_to_earnings_annual
                else b_name
            )
            delta_lines.append(
                f"- {a_name} cost-to-earnings ratio: "
                f"{a.debt_to_earnings_annual:.2f}x; "
                f"{b_name}: {b.debt_to_earnings_annual:.2f}x — "
                f"{higher} is {diff:.2f}x more expensive per dollar earned."
            )

    return "\n".join([*header_lines, *per_build_lines, *delta_lines])


def _short_school_name(name: str, limit: int = 32) -> str:
    """Lightly shorten institution names for compare-delta sentences
    so the deltas stay scannable. Falls back to full name."""
    if len(name) <= limit:
        return name
    return name[: limit - 1].rstrip() + "…"
