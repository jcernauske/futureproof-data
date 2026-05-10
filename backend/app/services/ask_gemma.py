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
- Turn-cap exhaustion (``max_turns=5`` reached — 4 tool + 1 synthesis).
- Wall-time exhaustion (``max_wall_time_s=30.0`` reached).

See docs/specs/feature-ask-gemma.md.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from pydantic import ValidationError

from app.models.api import (
    AskResponse,
    AskScope,
    ExplainStatReceipt,
    ReceiptSource,
    ScoringTier,
    StatComponent,
    TraceDone,
    TraceEvent,
    TraceEventPayload,
    TraceFinalText,
    TraceTurnComplete,
    TraceTurnStart,
)
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
from app.services.receipts import _humanize_basis

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
# Excluded tools still have explicit reachability paths via these:
#   - get_school_programs is fuzzy-search front-door (resolved via get_career_paths).
#   - get_ai_exposure data is already embedded in the build context.
_TOOLS: tuple[str, ...] = (
    "get_career_paths",
    "get_occupation_data",
    "get_regional_price_parity",
    "compare_purchasing_power",
    "get_career_branches",
    # School-comparison leaderboard. Powers chat questions like
    # "what other schools lead to this career for less money" and
    # "which schools have the highest ROI for this career". The MCP
    # tool's own description teaches Gemma when to reach for it
    # (compare schools FOR a career, not look up programs AT one
    # school — that's get_career_paths).
    "get_schools_for_career",
    "get_institution_aura",
    "get_task_breakdown",
)

# 0.5 — middle ground. Pre-trace this was 0.4 (suppressed all
# speculative tool calls). Trace shipping briefly bumped it to 0.7
# (encouraged tool use but Gemma 4 started leaking chain-of-thought
# narration into the response). 0.5 keeps the tool-exploration bias
# while suppressing the rambling. The system prompt's "Never write
# your reasoning" clause is the load-bearing fix; this just helps.
_TEMPERATURE = 0.5


# ---------------------------------------------------------------------------
# Aliases (binding for context-block formatting rule, §4)
# ---------------------------------------------------------------------------

_STAT_ALIAS: dict[str, str] = {
    "ERN": "Earning Power",
    "ROI": "Return on Investment",
    "RES": "AI Resilience",
    "GRW": "Growth Outlook",
    "AURA": "Brand Gravity",
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
    "You have five tools available — get_career_paths, "
    "get_occupation_data, get_regional_price_parity, "
    "compare_purchasing_power, get_career_branches. Use them generously "
    "any time fresh data would make your answer more accurate, more "
    "specific, or more verifiable than what you can pull from the "
    "loaded context. The student values seeing you check sources rather "
    "than answer from memory. If you can verify with a tool, verify.\n\n"
    "The narrow exception: if the question is purely about the "
    "student's OWN build state — their pentagon stats, their risk "
    "outcomes, their applied skills, their existing branches — that "
    "data is already in the context block and a tool call would just "
    "fetch what's already in front of you. Answer from context for "
    "those.\n\n"
    "For 'what if I picked a different major?' questions: looking up "
    "a major requires a CIP code. If you don't know the exact CIP "
    "code for the major the student is asking about, tell them to "
    "start a new build with that major rather than guessing — do not "
    "call a tool with a made-up code.\n\n"
    "RESIDENCY-AWARE COST COMPARISONS: When you compare schools and "
    "the context block says the student is paying out-of-state "
    "tuition at their current school, you MUST surface this in your "
    "answer. The leaderboard tool (get_schools_for_career) returns "
    "each school's average net_price_annual across ALL its students "
    "— mostly in-state residents paying low rates. An out-of-state "
    "student would NOT pay that listed average; they would pay "
    "closer to that school's tuition_out_of_state figure. State "
    "this gotcha plainly in the answer (e.g. 'as an out-of-state "
    "student you'd pay closer to $X, not the $Y school average'). "
    "Use the per-school tuition_out_of_state field from the "
    "leaderboard response when it's available; if it isn't, still "
    "name the issue and tell the student to verify the OOS rate. "
    "When the student is paying in-state at their current school, "
    "no caveat is needed — the leaderboard average is the right "
    "number to compare to.\n\n"
    "CRITICAL: Never write your reasoning, deliberation, or "
    "decision-making process in the response. The student sees only "
    "your finished answer — never narration like 'I should check', "
    "'Wait, let me think', 'Actually, I'll', 'Let's see if', 'One "
    "more thought', or any other thinking-out-loud. If a tool fits, "
    "call it silently and use the result. If no tool fits the "
    "question exactly, answer plainly with what you know in two to "
    "four sentences — do not apologize for the limits of the tools, "
    "do not enumerate alternatives you considered, do not explain why "
    "the question is hard. Skip directly to the answer.\n\n"
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

_COMPARE_VOICE_APPENDIX = (
    "\n\nCompare-specific rules for this conversation:\n"
    "- The context block contains MULTIPLE builds — the student's full "
    "portfolio of explored paths. Answer about all of them, not just one.\n"
    "- When the student asks a question, compare across all builds in "
    "context. Rank, contrast, and recommend — don't ask which build "
    "they mean.\n"
    "- Refer to each build by school name and career title so the "
    "student can tell them apart.\n"
    "- If a tool call would help compare (e.g. get_career_branches for "
    "each career's SOC code), call it for the most relevant builds — "
    "you don't need to call it for all of them if the answer is clear "
    "from a subset."
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
# Explain-this-stat — structured-receipt path
#   spec: docs/specs/feature-explain-stat-receipt.md (ERN, COMPLETE)
#   spec: docs/specs/feature-explain-stat-receipt-roi-res-grw.md
#   voice authority: .claude/skills/pentagon-stat-explanation/SKILL.md
#
# Triggers on the sentinel opener "[explain-this:{STAT}]" in the
# stat-scope chat. Gemma is asked to emit a JSON object matching
# ExplainStatReceipt; the server post-processes (validates, stamps
# the build's score, builds math_line, normalizes labels) before
# returning the receipt to the frontend.
#
# The original markdown spike's appendix and helper-leak stripper
# remain in this file as the JSON-parse-failure fallback. When
# a per-stat postprocessor returns None, the loop runs once more
# with the markdown appendix, reusing the cached tool_call_log
# so no MCP re-fetch happens.
# ---------------------------------------------------------------------------

_EXPLAIN_SENTINEL_RE = re.compile(r"^\[explain-this:([A-Z]+)\]$")
_EXPLAIN_TEMPERATURE = 0.0
_EXPLAIN_MAX_TOKENS = 1500
_EXPLAIN_RESPONSE_FORMAT: dict[str, Any] = {"type": "json_object"}


# Per-stat plain-English name used by the explain-this dispatch.
# Mirrors _STAT_ALIAS but typed for the explain-receipt path. The
# upcoming ROI/RES/GRW/AURA receipt specs already share this mapping.
_EXPLAIN_STAT_NAME: dict[str, str] = {
    "ERN": "Earning Power",
    "ROI": "Return on Investment",
    "RES": "AI Resilience",
    "GRW": "Growth Outlook",
    "AURA": "Brand Gravity",
}


def _get_build_stat(build: Build, stat_code: str) -> int | None:
    """Read the build's score for a given stat code (lowercase attr on
    PentagonStats). Centralized so the explain-stat dispatch and any
    future helper agree on the field-name mapping."""
    return getattr(build.career.stats, stat_code.lower(), None)


# ---------------------------------------------------------------------------
# Score-null receipt path (server-built, no Gemma call)
#   spec: docs/specs/bugfix-explain-stat-trigger-null-score-guard.md
#
# When build.career.stats.<stat> is None, the explain-this-stat path
# can't honestly produce a score. Instead of hiding the affordance
# (worse — the student's first question is "why don't I have a
# score?"), we still render the receipt: open-ring score callout,
# the universal one-liner / sources / why-mix paragraph, and per-
# component bullets where each missing input drives a plain-English
# missing_reason line.
#
# The path is fully server-deterministic: the two MCP tools fire so
# we know which input is null, then the receipt is constructed from
# canned templates substituted with the build's identifiers. Gemma
# is never called → no fabrication risk.
# ---------------------------------------------------------------------------

_ERN_ONE_LINER = (
    "Earning Power tells you how much your degree usually pays right "
    "after graduation."
)

_ERN_WHY_MIX_PARAGRAPH = (
    "Picture two students. One in a top-ranked Computer Science "
    "program at a regional school, the other in a top-ranked "
    "Philosophy program at a flagship. School rank alone would "
    "mislead you — Computer Science pays more than Philosophy almost "
    "everywhere. Mixing in the career's pay rank grounds the score "
    "in real U.S. salaries."
)


def _render_missing_score_math_line(
    cip_rank: float | None,
    wage_pct: float | None,
) -> str:
    """Math line for the score-null path. Renders the same `0.6 × A +
    0.4 × B` shape as the score-present path, but with `n/a` in place
    of any missing input and a `→ no score available` tail."""
    school_part = f"{cip_rank:.2f}" if cip_rank is not None else "n/a"
    career_part = f"{wage_pct:.2f}" if wage_pct is not None else "n/a"
    return f"0.6 × {school_part} + 0.4 × {career_part} → no score available"


async def _dispatch_ern_explain_tools(
    build: Build,
) -> list[gemma_client.ToolCallTurn]:
    """Fire the same two MCP tools the score-present path uses
    (get_career_paths, get_occupation_data) so the score-null receipt
    can read the actual null inputs from the response. Returns a
    tool_call_log shaped like generate_with_tools_loop's so the trace
    rail and AskResponse.tool_calls surface the calls identically."""
    career = build.career
    plan: list[tuple[str, dict[str, Any]]] = [
        (
            "get_career_paths",
            {"unitid": career.unitid, "cipcode": career.cipcode},
        ),
        (
            "get_occupation_data",
            {"soc_code": career.soc_code},
        ),
    ]
    log: list[gemma_client.ToolCallTurn] = []
    for dispatch_index, (tool_name, args) in enumerate(plan):
        start = time.monotonic()
        error: str | None = None
        try:
            result = await _dispatch(tool_name, args)
        except Exception as exc:  # noqa: BLE001 — boundary defense
            logger.warning(
                "ern missing-score receipt: %s dispatch failed — %s",
                tool_name,
                exc,
            )
            result = {}
            error = str(exc)
        duration_ms = int((time.monotonic() - start) * 1000)
        result_str = json.dumps(result, default=str)
        log.append(
            gemma_client.ToolCallTurn(
                turn_number=0,
                tool_name=tool_name,
                tool_args=args,
                tool_result_size_bytes=len(result_str),
                duration_ms=duration_ms,
                error=error,
                tool_result_preview=result_str[:500],
                tool_result_full=result_str,
                dispatch_index=dispatch_index,
            )
        )
    return log


def _build_ern_missing_score_receipt(
    build: Build,
    cip_rank: float | None,
    earnings: int | None,
    wage_pct: float | None,
    wage: int | None,
) -> ExplainStatReceipt:
    """Construct the ExplainStatReceipt for the score-null path. Each
    component bullet either shows its value (if the input is present)
    or carries a plain-English missing_reason that names the absent
    data source."""
    career = build.career
    school_label = career.institution_name
    program_label = career.program_name or build.major_text
    career_label = career.occupation_title or "this career"
    school_anchor = f"{school_label} {program_label} grads"

    # 60% bullet — school × program rank.
    if cip_rank is not None and earnings is not None:
        school_explainer = (
            f"How {school_label}'s {program_label} graduates' median "
            f"earnings rank against peers in the same field of study "
            f"(Classification of Instructional Programs family, or CIP "
            f"family)."
        )
        school_value_pct: int | None = int(cip_rank * 100 + 0.5)
        school_missing: str | None = None
    else:
        school_explainer = (
            f"How {school_label}'s {program_label} graduates' median "
            f"earnings would rank against peers in the same field of "
            f"study — if this number were reported."
        )
        school_value_pct = None
        if earnings is None:
            school_missing = (
                f"College Scorecard doesn't report median earnings "
                f"for {school_label}'s {program_label} graduates yet "
                f"— usually because the cohort is small enough that "
                f"publishing earnings would identify individual "
                f"students."
            )
        else:
            school_missing = (
                f"College Scorecard reports median earnings for "
                f"{school_label}'s {program_label} graduates "
                f"(${earnings:,}), but doesn't yet rank that figure "
                f"against peer programs in the same field of study."
            )

    # 40% bullet — career × occupation pay rank.
    if wage_pct is not None and wage is not None:
        career_explainer = (
            f"How {career_label}'s median wage ranks against all U.S. "
            f"occupations (Standard Occupational Classification code, "
            f"or SOC code)."
        )
        career_value_pct: int | None = int(wage_pct * 100 + 0.5)
        career_missing: str | None = None
    else:
        career_explainer = (
            f"How {career_label}'s median wage would rank against all "
            f"U.S. occupations — if this number were reported."
        )
        career_value_pct = None
        if wage is None:
            career_missing = (
                f"The Bureau of Labor Statistics (BLS) hasn't "
                f"published a median wage for {career_label} yet."
            )
        else:
            career_missing = (
                f"The Bureau of Labor Statistics (BLS) reports "
                f"median pay for {career_label} (${wage:,}/year), "
                f"but doesn't yet rank that figure against all U.S. "
                f"occupations."
            )

    return ExplainStatReceipt(
        kind="receipt",
        stat_code="ERN",
        stat_name="Earning Power",
        score=None,
        score_max=10,
        one_liner=_ERN_ONE_LINER,
        components=[
            StatComponent(
                weight_pct=60,
                label="your school's program rank",
                explainer=school_explainer,
                value_pct=school_value_pct,
                anchor_text=school_anchor,
                anchor_dollars=earnings,
                missing_reason=school_missing,
            ),
            StatComponent(
                weight_pct=40,
                label="this career's pay rank",
                explainer=career_explainer,
                value_pct=career_value_pct,
                anchor_text=career_label,
                anchor_dollars=wage,
                missing_reason=career_missing,
            ),
        ],
        math_line=_render_missing_score_math_line(cip_rank, wage_pct),
        sources=list(_ERN_RECEIPT_SOURCES),
        why_mix_paragraph=_ERN_WHY_MIX_PARAGRAPH,
    )


async def _ern_missing_score_receipt_path(
    build: Build,
) -> tuple[ExplainStatReceipt, list[gemma_client.ToolCallTurn]]:
    """Score-null entry point. Dispatches the two MCP tools, extracts
    the four input values (any may still be None), constructs the
    receipt server-side. Returns the receipt + tool_call_log so the
    caller can surface the trace events."""
    tool_call_log = await _dispatch_ern_explain_tools(build)
    cip_rank, earnings, wage_pct, wage = _extract_tool_results(tool_call_log)
    receipt = _build_ern_missing_score_receipt(
        build,
        cip_rank=cip_rank,
        earnings=earnings,
        wage_pct=wage_pct,
        wage=wage,
    )
    gemma_client._log_exchange({
        "call_site": "explain_ern_missing_receipt",
        "build_id": build.build_id,
        "reason": "build_score_null",
        "cip_rank": cip_rank,
        "wage_pct": wage_pct,
        "earnings": earnings,
        "wage": wage,
    })
    return receipt, tool_call_log

# What we send to Gemma in place of the sentinel.
_ERN_EXPLAIN_USER_PROMPT = (
    "Explain my Earning Power score with the receipts. Show me the actual "
    "numbers behind it, not just the definition."
)

# Per-stat label allowlist (Decision 14). Keyed by weight_pct so the
# normalizer matches the right canonical label even when Gemma swaps
# the components (puts the 60% label on the 40% component).
_ERN_LABEL_ALLOWLIST: dict[int, str] = {
    60: "your school's program rank",
    40: "this career's pay rank",
}

# Friendly effort labels for the math_line's effort sentence
# (Decision 13). Keys must match the EffortLevel literal in
# backend/app/models/career.py:16. effort.capitalize() would render
# "Working_hard" / "All_in" — both read as broken copy.
_EFFORT_LABELS: dict[str, str] = {
    "working_hard": "Working Hard",
    "working": "Working",
    "balanced": "Balanced",
    "focused": "Focused",
    "all_in": "All-In",
}

# ERN's two data sources. Server-stamped; Gemma's emitted sources
# field is discarded so the citations stay canonical across runs.
_ERN_RECEIPT_SOURCES: tuple[ReceiptSource, ...] = (
    ReceiptSource(
        label="Graduate earnings",
        name="College Scorecard (U.S. Department of Education)",
    ),
    ReceiptSource(
        label="Occupation wages",
        name=(
            "Occupational Outlook Handbook, published by the Bureau "
            "of Labor Statistics (BLS)"
        ),
    ),
)

# Template included in the system appendix. Filled-in JSON example
# with __FILL_IN__ sentinels for prose fields and realistic numeric
# placeholders. Gemma 4 is a strong few-shot learner; this format
# materially outperforms a Pydantic-model-as-Python-code template
# (per @genai-architect v1.1 finding 2).
_RECEIPT_JSON_TEMPLATE = """{
  "kind": "receipt",
  "stat_code": "ERN",
  "stat_name": "Earning Power",
  "score": 7,
  "score_max": 10,
  "one_liner": "__FILL_IN__: ONE-SENTENCE DEFINITION OF WHAT THIS SCORE MEASURES, in plain English a 16-year-old reads as English (no jargon, no /10, no percentiles).",
  "components": [
    {
      "weight_pct": 60,
      "label": "your school's program rank",
      "explainer": "__FILL_IN__: 1-2 sentences naming the school + program + median earnings (in $) and where the program ranks against peers in the same field of study (Classification of Instructional Programs family, or CIP family). On the FIRST percentile mentioned in the response, write it INLINE as 'Nth percentile (out of 100 programs, this one ranks higher than about N-1)'. Do NOT repeat the percentile in a separate sentence. Do NOT include the X/10 score in this string.",
      "value_pct": 87,
      "anchor_text": "Indiana University's Computer Science grads",
      "anchor_dollars": 94200,
      "missing_reason": null
    },
    {
      "weight_pct": 40,
      "label": "this career's pay rank",
      "explainer": "__FILL_IN__: 1-2 sentences naming the career + median wage (in $) and where the career ranks against all U.S. occupations (Standard Occupational Classification code, or SOC code). Do NOT repeat the percentile gloss — it was already given in the 60% bullet. Do NOT include the X/10 score in this string.",
      "value_pct": 92,
      "anchor_text": "Software Developer",
      "anchor_dollars": 132270,
      "missing_reason": null
    }
  ],
  "math_line": "0.6 × 0.87 + 0.4 × 0.92 → score 9/10",
  "sources": [
    {"label": "Graduate earnings", "name": "College Scorecard (U.S. Department of Education)"},
    {"label": "Occupation wages", "name": "Occupational Outlook Handbook, published by the Bureau of Labor Statistics (BLS)"}
  ],
  "why_mix_paragraph": "__FILL_IN__: ~3-sentence 'two students contrast' paragraph. Picture a top-ranked Computer Science program vs. a top-ranked Philosophy program. Show why using only the school rank would mislead and why the occupation blend grounds the score in real U.S. salaries. Do NOT reference the student's actual numbers — this paragraph is the universal explanation of the formula, not their personal score. Do NOT include the X/10 score in this string."
}"""


def _ern_explain_appendix_json(career: CareerOutcome, *, home_state: str | None = None) -> str:
    """JSON-mode appendix for the ERN explain-this-stat receipt path.

    Substitutes the build's identifiers so Gemma calls the tools with
    exact arguments. The voice rules in ``_SYSTEM_BASE`` relax in a
    SCOPED way for this turn (Decision 15 voice-rule split):
      - lifted for the JSON numeric fields (value_pct, anchor_dollars)
        which carry integers, not prose;
      - retained for prose fields (one_liner, explainer,
        why_mix_paragraph) which must NOT contain numeric score refs.
    """
    return f"""

EXPLAIN-THIS-STAT (ERN) — JSON-MODE OUTPUT REQUIRED

The student tapped 'Explain this to me' on their Earning Power score.
You will produce a single JSON object matching the structure shown in
the TEMPLATE below. Do not write any text outside the JSON object.

REQUIRED TOOL CALLS — call BOTH on your first turn (in parallel). Use
these exact arguments from the student's build:

  • get_career_paths(unitid={career.unitid}, cipcode="{career.cipcode}")
    From the result row where soc_code = "{career.soc_code}", pull
    `cip_family_earnings_rank` and `earnings_1yr_median`.

  • get_occupation_data(soc_code="{career.soc_code}")
    Pull `wage_percentile_overall` and `median_annual_wage`.

After both tool calls return, emit the JSON receipt. If a tool result
field is null, set the corresponding receipt field to null and the
matching `missing_reason` to a plain-English explanation. Do not
hallucinate values.

VOICE-RULE SCOPING (this turn only):
  • LIFTED for the numeric JSON fields `value_pct` and `anchor_dollars`:
    quote the actual percentile and dollar values precisely.
  • RETAINED for the prose JSON fields `one_liner`,
    `components[*].explainer`, `components[*].anchor_text`, and
    `why_mix_paragraph`: do NOT write 'N/10', 'your score is N',
    or any numeric score reference. The score callout is the UI's
    responsibility — it lives outside your prose.

PERCENTILE GLOSS — on the FIRST percentile mentioned anywhere in any
prose field, write it INLINE as a single phrase with the explanation
in parentheses immediately after the number. Format:
'Nth percentile (out of 100 <thing>, this one ranks higher than about
N-1)'. Examples — substitute the actual numbers and noun:
  ✓ "87th percentile (out of 100 programs, this one ranks higher than about 86)"
  ✓ "92nd percentile (out of 100 careers, this one pays more than about 91)"
  ✗ DO NOT write 'This is the Nth percentile...' as a separate sentence.
  ✗ DO NOT mention the percentile twice in the same field.
After the first use, later percentiles in the response stand alone:
write "99th percentile" with no gloss.

ACRONYMS — every acronym (CIP, SOC, BLS) is expanded once on first
use, then the abbreviation is fine.

TEMPLATE (replace every `__FILL_IN__` string with your written content;
keep all other field values as shown for structure but substitute real
data values):

{_RECEIPT_JSON_TEMPLATE}

CRITICAL — SENTINEL HANDLING. The strings `__FILL_IN__`, `[FILL_IN]`,
`<FILL_IN>`, `ONE-SENTENCE DEFINITION HERE`, and `PLACEHOLDER` are
placeholders ONLY — they MUST be replaced with your actual content.
Echoing them back verbatim will fail validation and the receipt will
not render. Write real prose in every prose field.
"""


def _ern_explain_appendix(career: CareerOutcome, *, home_state: str | None = None) -> str:
    """Markdown-mode appendix retained as the JSON-parse-failure
    fallback path. When `_postprocess_ern_explain_receipt` returns
    None, the loop re-runs with this appendix and the cached
    tool_call_log values pre-injected into the user message (so no
    MCP re-fetch happens — see ``_format_cached_tool_values``).
    """
    return f"""

EXPLAIN-THIS-STAT MODE — ERN (markdown fallback)

The structured-JSON path failed validation; produce the markdown
fallback. Voice rules above relax in three specific ways for this
turn ONLY:

1. You MUST quote the actual numeric values: percentile ranks (e.g. 0.92),
   the X/10 score, and the 0.6 × A + 0.4 × B math.
2. Use a structured response with the four labeled sections below.
3. Reading level lifts to high-school junior. Technical terms are OK
   when introduced in plain English first with the term in parens.

The cached tool values are already injected into the user message —
do NOT re-call get_career_paths or get_occupation_data. Read the
percentile values from the message and produce the receipt.

REQUIRED RESPONSE STRUCTURE — exactly four sections in this order:

### Earning Power — <SCORE>/10

**The one-liner.** One sentence naming what the score measures.

**How it works.**
  - **60% — your school's program rank.** {career.institution_name}'s
    {career.program_name} grads earn a median of $<earnings_1yr_median> —
    that lands at the <cip_family_earnings_rank × 100>th percentile of all
    {career.program_name} programs nationally (Classification of
    Instructional Programs family {career.cipcode}).
  - **40% — this career's pay rank.** {career.occupation_title}'s
    median wage is $<median_annual_wage>, which sits at the
    <wage_percentile_overall × 100>th percentile of all U.S. occupations
    (Standard Occupational Classification code {career.soc_code}).

  Math: 0.6 × <cip_family_earnings_rank> + 0.4 ×
  <wage_percentile_overall> = <raw> → rounds to <SCORE>/10.

**Where the data comes from.**
  - Graduate earnings: College Scorecard (U.S. Department of Education).
  - Occupation wages: Occupational Outlook Handbook, published by the
    Bureau of Labor Statistics (BLS).

**Why we mix both pieces.** A two-students contrast in ~3 sentences.

VOICE — every acronym (CIP, SOC, BLS) is expanded once on first use.
On the FIRST percentile mentioned, write it INLINE as
'Nth percentile (out of 100 <thing>, this one ranks higher than
about N-1)'. After the first time, percentiles stand alone.
"""


# ---------------------------------------------------------------------------
# Receipt post-processing helpers (Decision 7, 8, 13, 14, 15 of the spec).
# ---------------------------------------------------------------------------


def _ordinal_suffix(n: int) -> str:
    """Return the ordinal suffix for an integer (1 -> 'st', 2 -> 'nd', ...)."""
    if 11 <= (n % 100) <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def _format_pct(value: float | None) -> str:
    """Render a 0-1 percentile as '87' (the integer part of value*100)
    or 'n/a' when None. Round half-up for consistency with the Gold-zone
    rounding convention.
    """
    if value is None:
        return "n/a"
    return str(int(value * 100 + 0.5))


def _extract_tool_results(
    tool_call_log: list[gemma_client.ToolCallTurn],
) -> tuple[float | None, int | None, float | None, int | None]:
    """Pull the four needed values out of the tool_call_log.

    Returns (cip_family_earnings_rank, earnings_1yr_median,
             wage_percentile_overall, median_annual_wage). Any value
    not found in the log is None.

    All four are dimension-level values:
      - cip_family_earnings_rank, earnings_1yr_median are
        (school, CIP)-level — same across every soc_code fanout row
        in a get_career_paths response.
      - wage_percentile_overall, median_annual_wage are SOC-level
        and come from get_occupation_data, which is queried with a
        single SOC.

    No soc_code matching is required. (An earlier version filtered
    get_career_paths rows by soc_code before reading the CIP-level
    fields, which silently failed under CIP substitution / SOC-format
    drift — Gemma's prose then claimed values the server couldn't
    surface. See bugfix-explain-stat-trigger-null-score-guard.md.)

    Reads ``tool_result_full`` (the un-truncated server-only string)
    rather than ``tool_result_preview``. The preview is capped at
    ~500 bytes which mid-truncates real ``get_career_paths`` results
    on cipcode-family flows; the full string is required for reliable
    JSON parsing (per @faang-staff-engineer S1 finding).
    """
    cip_rank: float | None = None
    earnings: int | None = None
    wage_pct: float | None = None
    wage: int | None = None
    for turn in tool_call_log:
        if turn.error:
            continue
        # Prefer the un-truncated full string; fall back to preview
        # for older callers that don't populate the new field.
        result_json = turn.tool_result_full or turn.tool_result_preview
        try:
            preview = json.loads(result_json)
        except (json.JSONDecodeError, ValueError):
            continue
        if turn.tool_name == "get_career_paths":
            # MCP wraps list responses in {"data": [...], "row_count": N, ...};
            # the rows we need live under "data".
            rows = preview.get("data") if isinstance(preview, dict) else None
            if not isinstance(rows, list):
                continue
            # cip_family_earnings_rank and earnings_1yr_median are
            # (school, CIP)-level — the same value lives on every
            # soc_code fanout row for a given (unitid, cipcode). Reading
            # only the row whose soc_code matches the build's career
            # leaves the extractor returning None when CIP substitution
            # or SOC-format drift means that exact soc_code isn't in the
            # response, even though the values ARE present on every
            # other row. Gemma's prose then claims a value the server
            # can't surface — the 60% bullet shows ◦ — + "no median
            # earnings reported" while the prose says "$X / Nth
            # percentile". Read from any non-null row instead.
            for row in rows:
                if not isinstance(row, dict):
                    continue
                if cip_rank is None:
                    rank_val = row.get("cip_family_earnings_rank")
                    if isinstance(rank_val, (int, float)):
                        cip_rank = float(rank_val)
                if earnings is None:
                    earn = row.get("earnings_1yr_median")
                    if isinstance(earn, (int, float)):
                        earnings = int(earn)
                if cip_rank is not None and earnings is not None:
                    break
        elif turn.tool_name == "get_occupation_data":
            # MCP wraps the single-row response in {"data": {...}, "row_count": 1, ...}.
            row = preview.get("data") if isinstance(preview, dict) else None
            if not isinstance(row, dict):
                continue
            wp = row.get("wage_percentile_overall")
            if isinstance(wp, (int, float)):
                wage_pct = float(wp)
            ma = row.get("median_annual_wage")
            if isinstance(ma, (int, float)):
                wage = int(ma)
    return cip_rank, earnings, wage_pct, wage


def _render_math_line(
    cip_rank: float | None,
    wage_pct: float | None,
    build_score: int,
    score_max: int,
    effort: str,
) -> str:
    """Build the receipt's math_line string from raw inputs.

    Format: '0.6 × 0.87 + 0.4 × 0.92 → score 9/10'

    Effort line (Decision 13) appears on a second line when
    ``effort != "balanced"`` AND the receipt has effort signal to
    surface. Three cases:

    1. Both percentiles present → render the unshifted derivation
       in the arrow; if it differs from build_score, append an
       effort line ("lifts"/"brings" to N/M).
    2. One percentile null (halfway case) → can't derive the
       unshifted score. Render build_score in the arrow with an n/a
       in the missing slot. For non-balanced effort, append an
       effort line that doesn't claim a from-N-to-M delta:
       "Your **Focused** effort setting is reflected in this score."
    3. Both percentiles null → same as halfway, no derivation
       claimable.
    """
    cip_str = f"{cip_rank:.2f}" if cip_rank is not None else "n/a"
    wage_str = f"{wage_pct:.2f}" if wage_pct is not None else "n/a"

    # Compute the unshifted score derivation when both inputs present.
    unshifted: int | None
    if cip_rank is not None and wage_pct is not None:
        raw = 0.6 * cip_rank + 0.4 * wage_pct
        unshifted = int(1.0 + 9.0 * raw + 0.5)  # half-up round to 1-10
        unshifted = max(1, min(score_max, unshifted))
        base_score = unshifted
    else:
        # Halfway / both-missing: math can't be derived; show
        # build_score in the arrow.
        unshifted = None
        base_score = build_score

    base = (
        f"0.6 × {cip_str} + 0.4 × {wage_str} → score "
        f"{base_score}/{score_max}"
    )

    if effort == "balanced":
        return base
    # When the unshifted derivation matches the build score, the
    # effort delta is zero — no effort line.
    if unshifted is not None and unshifted == build_score:
        return base

    # Unknown effort string — defensive: no effort line. Both
    # _EFFORT_LABELS and the EffortLevel literal must agree on
    # the label set.
    label = _EFFORT_LABELS.get(effort)
    if label is None:
        return base

    if unshifted is None:
        # No derivation available — say the effort applies, without
        # claiming a from-N-to-M delta.
        return (
            f"{base}\n"
            f"Your **{label}** effort setting is reflected in this score"
        )

    direction = "lifts" if build_score > unshifted else "brings"
    return (
        f"{base}\n"
        f"Your **{label}** effort setting {direction} this to "
        f"{build_score}/{score_max}"
    )


def _normalize_label(
    weight_pct: int,
    gemma_label: str,
    allowlist: dict[int, str],
) -> tuple[str, bool]:
    """Match Gemma's label against the per-weight allowlist.

    Returns (canonical_label, was_normalized). Match strategy:
      1. Look up the canonical label by weight_pct (Decision 14 — match
         by weight first to catch the swap-component-labels case).
      2. If gemma_label != canonical, return (canonical, True) so the
         caller can log a WARNING with both values.
    """
    canonical = allowlist.get(weight_pct)
    if canonical is None:
        # No allowlist entry — keep Gemma's label as-is.
        return gemma_label, False
    if gemma_label.strip().lower() == canonical.lower():
        return canonical, False
    return canonical, True


def _log_receipt_parse(
    *,
    call_site: str,
    parse_success: bool,
    failure_reason: str | None,
    json_prefix: str,
    build_id: str,
    backend: str,
) -> None:
    """Append one structured record to logs/gemma.jsonl per parse attempt.

    Schema enables a parse_success_rate metric: filter records by
    `call_site == "explain_ern_receipt"` and aggregate.
    """
    record = {
        "call_site": call_site,
        "parse_success": parse_success,
        "failure_reason": failure_reason,
        "json_prefix": json_prefix[:500],
        "build_id": build_id,
        "backend": backend,
    }
    if parse_success:
        logger.info("ern_explain_receipt parsed: %s", record)
    else:
        logger.warning("ern_explain_receipt parse failed: %s", record)
    gemma_client._log_exchange(record)


def _format_cached_tool_values(
    cip_rank: float | None,
    earnings: int | None,
    wage_pct: float | None,
    wage: int | None,
) -> str:
    """Build a string injected into the markdown-fallback user message
    so the fallback path doesn't need to re-issue tool calls.
    """
    return (
        "Cached tool values from your build (use these directly — do not "
        "call get_career_paths or get_occupation_data again):\n"
        f"  cip_family_earnings_rank = {cip_rank}\n"
        f"  earnings_1yr_median = {earnings}\n"
        f"  wage_percentile_overall = {wage_pct}\n"
        f"  median_annual_wage = {wage}\n"
    )


def _format_cached_tool_values_generic(
    tool_call_log: list[gemma_client.ToolCallTurn],
) -> str:
    """Build a generic cached-tool-values block for the markdown fallback
    from the full tool_call_log. Extracts all key-value pairs from the
    tool results and formats them for the user message."""
    lines = [
        "Cached tool values from your build (use these directly — do not "
        "re-call any tools):"
    ]
    for turn in tool_call_log:
        if turn.error:
            continue
        result_json = turn.tool_result_full or turn.tool_result_preview
        try:
            preview = json.loads(result_json)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(preview, dict):
            data = preview.get("data", preview)
            if isinstance(data, list):
                for row in data[:3]:
                    if isinstance(row, dict):
                        for k, v in row.items():
                            lines.append(f"  {k} = {v}")
                        break
            elif isinstance(data, dict):
                for k, v in data.items():
                    lines.append(f"  {k} = {v}")
    return "\n".join(lines)


def _postprocess_ern_explain_receipt(
    raw: str,
    build: Build,
    tool_call_log: list[gemma_client.ToolCallTurn],
    backend: str,
) -> ExplainStatReceipt | None:
    """Parse Gemma's JSON output, validate via Pydantic, stamp server-
    controlled fields, return a fully-realized ExplainStatReceipt.

    Returns None on any failure — the caller falls back to the markdown
    spike path with the cached tool_call_log injected (no MCP re-fetch).

    Pipeline (10 steps; see spec §4 Architecture Overview point 3):
      1. _extract_json_objects(raw) — strip markdown fences, brace-depth
         extract; handles ```json{...}``` and trailing-prose wrappers.
      2. Locate a parseable object in the candidates list.
      3. ExplainStatReceipt.model_validate(parsed). On ValidationError
         (including the sentinel-passthrough validator firing) -> None.
      4. Assert receipt.stat_code == "ERN". Mismatch -> None.
      5. If build.career.stats.ern is None -> None.
      6. Server-stamp receipt.score = build.career.stats.ern.
      7. Server-build receipt.math_line via _render_math_line.
      8. Normalize each receipt.components[i].label.
      9. For each component, server-stamp value_pct, anchor_dollars,
         missing_reason from tool_call_log.
     10. _log_receipt_parse appends a structured record to gemma.jsonl.
    """
    json_prefix = raw[:500] if raw else ""
    build_id = build.build_id

    # Step 1-2: extract + parse.
    candidates = gemma_client._extract_json_objects(raw or "")
    parsed: dict[str, Any] | None = next(
        (c for c in candidates if isinstance(c, dict)), None
    )
    if parsed is None:
        _log_receipt_parse(
            call_site="explain_ern_receipt",
            parse_success=False,
            failure_reason="json_decode",
            json_prefix=json_prefix,
            build_id=build_id,
            backend=backend,
        )
        return None

    # Step 3: Pydantic-validate (also fires sentinel-passthrough validator).
    try:
        receipt = ExplainStatReceipt.model_validate(parsed)
    except ValidationError as exc:
        # Distinguish sentinel-passthrough from other validation errors
        # for log granularity. Both route to the markdown fallback.
        reason = "pydantic_validation"
        if "unreplaced template sentinel" in str(exc):
            reason = "sentinel_passthrough"
        _log_receipt_parse(
            call_site="explain_ern_receipt",
            parse_success=False,
            failure_reason=reason,
            json_prefix=json_prefix,
            build_id=build_id,
            backend=backend,
        )
        return None

    # Step 4: stat_code assertion (catches Gemma cross-stat drift).
    if receipt.stat_code != "ERN":
        _log_receipt_parse(
            call_site="explain_ern_receipt",
            parse_success=False,
            failure_reason="stat_code_mismatch",
            json_prefix=json_prefix,
            build_id=build_id,
            backend=backend,
        )
        return None

    # Step 5: null-build-stat guard.
    build_score = build.career.stats.ern
    if build_score is None:
        _log_receipt_parse(
            call_site="explain_ern_receipt",
            parse_success=False,
            failure_reason="score_null",
            json_prefix=json_prefix,
            build_id=build_id,
            backend=backend,
        )
        return None

    # Step 6: server-stamp score AND score_max. Whatever Gemma emits
    # in either field is overwritten; Decision 7 + reviewer S4 finding.
    # v1.0 fixes score_max = 10 per spec docstring.
    receipt.score = build_score
    receipt.score_max = 10

    # Step 7: server-build math_line.
    cip_rank, earnings, wage_pct, wage = _extract_tool_results(tool_call_log)
    receipt.math_line = _render_math_line(
        cip_rank=cip_rank,
        wage_pct=wage_pct,
        build_score=build_score,
        score_max=receipt.score_max,
        effort=getattr(build, "effort", "balanced") or "balanced",
    )

    # Step 8: normalize labels.
    for comp in receipt.components:
        canonical, was_normalized = _normalize_label(
            comp.weight_pct, comp.label, _ERN_LABEL_ALLOWLIST
        )
        if was_normalized:
            logger.warning(
                "ern_explain_receipt: label normalized weight=%d "
                "gemma=%r canonical=%r",
                comp.weight_pct, comp.label, canonical,
            )
            comp.label = canonical

    # Step 9: server-stamp per-component numeric fields + missing_reason.
    for comp in receipt.components:
        if comp.weight_pct == 60:
            comp.value_pct = (
                int(cip_rank * 100 + 0.5) if cip_rank is not None else None
            )
            comp.anchor_dollars = earnings
            if cip_rank is None or earnings is None:
                comp.missing_reason = (
                    "no median earnings reported for this program yet"
                )
            else:
                comp.missing_reason = None
        elif comp.weight_pct == 40:
            comp.value_pct = (
                int(wage_pct * 100 + 0.5) if wage_pct is not None else None
            )
            comp.anchor_dollars = wage
            if wage_pct is None or wage is None:
                comp.missing_reason = (
                    "no wage data for this occupation in the BLS handbook"
                )
            else:
                comp.missing_reason = None

    # Server-stamp sources (canonical citations; Gemma's emitted list is
    # discarded so the citations stay consistent across runs).
    receipt.sources = list(_ERN_RECEIPT_SOURCES)

    # Step 10: structured log on success.
    _log_receipt_parse(
        call_site="explain_ern_receipt",
        parse_success=True,
        failure_reason=None,
        json_prefix=json_prefix,
        build_id=build_id,
        backend=backend,
    )
    return receipt


# ---------------------------------------------------------------------------
# ROI receipt helpers
# ---------------------------------------------------------------------------

_ROI_LABEL_ALLOWLIST: dict[int, str] = {
    100: "your 15-year payback multiplier",
}

_ROI_RECEIPT_SOURCES: tuple[ReceiptSource, ...] = (
    ReceiptSource(
        label="Published cost",
        name="College Scorecard (U.S. Department of Education)",
    ),
    ReceiptSource(
        label="Graduate earnings",
        name="College Scorecard (U.S. Department of Education)",
    ),
)

_ROI_TIER_LABELS: tuple[str, ...] = (
    "Underwater",
    "Poor return",
    "Below average",
    "Modest return",
    "Average return",
    "Above average",
    "Strong return",
    "Excellent return",
    "Exceptional return",
    "Elite return",
)


def _build_roi_scoring_scale() -> list[ScoringTier]:
    """Derive the ROI scoring scale from `ROI_MULTIPLIER_THRESHOLDS`.

    Single source of truth — if the calibration ladder is retuned, this
    table updates without a manual edit. Each threshold entry maps a
    multiplier upper bound to a score; the bottom band starts at 0 and
    the top band starts at the last threshold (16.0x → score 10).
    """
    from gold.futureproof_engine import (  # type: ignore[import-not-found]
        ROI_MULTIPLIER_THRESHOLDS,
    )

    tiers: list[ScoringTier] = []
    lower = 0.0
    for upper, score in ROI_MULTIPLIER_THRESHOLDS:
        if score == 1:
            range_str = f"< {upper}x"
        else:
            range_str = f"{lower:g} – {upper:g}x"
        tiers.append(
            ScoringTier(
                label=_ROI_TIER_LABELS[score - 1],
                range=range_str,
                score=str(score),
            )
        )
        lower = upper
    # Top band — no upper bound.
    tiers.append(
        ScoringTier(
            label=_ROI_TIER_LABELS[9],
            range=f"≥ {lower:g}x",
            score="10",
        )
    )
    return tiers


_ROI_SCORING_SCALE: list[ScoringTier] = _build_roi_scoring_scale()

_ROI_ONE_LINER = (
    "Return on Investment is a 15-year payback multiplier — projected "
    "cumulative earnings over a typical 15-year repayment window divided "
    "by the program's 4-year published cost. A higher multiplier means "
    "the degree pays back faster relative to what it costs."
)

_ROI_WHY_MIX_PARAGRAPH = (
    "Picture two students at the 15-year mark. One pays $80,000 total and "
    "earns about $50,000/yr to start — over fifteen years their earnings "
    "cumulate to roughly $930,000, an 11.6x payback. Another pays "
    "$240,000 and starts at the same $50,000 — same cumulative earnings, "
    "but only a 3.9x payback. Same career, wildly different value. The "
    "multiplier turns long-horizon program value into one number you can "
    "compare across any school and career."
)


def _render_math_line_roi(
    *,
    published_cost_4yr: float | None,
    earnings_1yr_median: float | None,
    build_score: int,
    score_max: int,
) -> str:
    """Build ROI's math-line string under the 15-year payback multiplier.

    Format: 'Lifetime $1,458,154 ÷ Cost $112,400 = 12.97x → ROI score 8/10'

    Lifetime earnings = earnings_1yr_median × 18.5989 (closed-form sum at
    flat 3% nominal growth, see spec roi-net-lifetime-value §2 Decision #10).
    """
    from app.services.stat_engine import LIFETIME_EARNINGS_MULTIPLIER

    if published_cost_4yr is None and earnings_1yr_median is None:
        return f"Lifetime n/a ÷ Cost n/a = n/a → ROI score {build_score}/{score_max}"
    if published_cost_4yr is None:
        lifetime = earnings_1yr_median * LIFETIME_EARNINGS_MULTIPLIER  # type: ignore[operator]
        lifetime_str = f"${int(lifetime):,}"
        return (
            f"Lifetime {lifetime_str} ÷ Cost n/a = n/a → ROI score "
            f"{build_score}/{score_max}"
        )
    if earnings_1yr_median is None or earnings_1yr_median == 0:
        cost_str = f"${int(published_cost_4yr):,}"
        return (
            f"Lifetime n/a ÷ Cost {cost_str} = n/a → ROI score "
            f"{build_score}/{score_max}"
        )
    lifetime = earnings_1yr_median * LIFETIME_EARNINGS_MULTIPLIER
    multiplier = lifetime / published_cost_4yr
    lifetime_str = f"${int(lifetime):,}"
    cost_str = f"${int(published_cost_4yr):,}"
    return (
        f"Lifetime {lifetime_str} ÷ Cost {cost_str} = {multiplier:.2f}x → "
        f"ROI score {build_score}/{score_max}"
    )


_ROI_RECEIPT_JSON_TEMPLATE = """{
  "kind": "receipt",
  "stat_code": "ROI",
  "stat_name": "Return on Investment",
  "score": 8,
  "score_max": 10,
  "one_liner": "__FILL_IN__: ONE-SENTENCE DEFINITION of what this score measures. Plain English a 16-year-old reads. Frame it as a 15-year payback multiplier — projected lifetime earnings vs. 4-year sticker cost. No jargon, no /10, no percentiles.",
  "components": [
    {
      "weight_pct": 100,
      "label": "your 15-year payback multiplier",
      "explainer": "__FILL_IN__: 1-3 sentences. Name the school + program + 4-year published cost (in $), the median starting salary one year after graduation (in $), and the resulting 15-year cumulative earnings (in $) at flat 3% wage growth. State the multiplier: lifetime earnings divided by cost = X.XXx, meaning the program returns roughly $X.XX for every $1 of cost over the typical repayment window. Do NOT include the X/10 score.",
      "value_pct": null,
      "anchor_text": "Indiana University Computer Science 4-year published cost",
      "anchor_dollars": 112400,
      "missing_reason": null
    }
  ],
  "math_line": "Lifetime $1,458,154 \\u00f7 Cost $112,400 = 12.97x \\u2192 ROI score 8/10",
  "sources": [
    {"label": "Published cost", "name": "College Scorecard (U.S. Department of Education)"},
    {"label": "Graduate earnings", "name": "College Scorecard (U.S. Department of Education)"}
  ],
  "why_mix_paragraph": "__FILL_IN__: ~3-sentence explanation of WHY a 15-year payback multiplier is the right yardstick. Use a two-students contrast at the 15-year mark — same career, different costs, different cumulative payoffs. Do NOT include the X/10 score."
}"""


def _roi_explain_appendix_json(career: CareerOutcome, *, home_state: str | None = None) -> str:
    home_state_kwarg = (
        f', home_state="{home_state}"' if home_state else ""
    )
    home_state_note = (
        (
            f"The build's home_state is {home_state!r}. Pass it to "
            f"get_career_paths so the MCP server applies the residency "
            f"adjustment server-side and returns the same residency-aware "
            f"cost the user sees in the FINANCES card. Without "
            f"home_state, the tool returns the in-state baseline — "
            f"which is fine for in-state students but understates the "
            f"cost for out-of-state public-school applicants."
        )
        if home_state
        else (
            "The student has not set a home state. The tool returns "
            "the in-state baseline; that is the correct value to cite. "
            "Do NOT invent a home_state."
        )
    )
    return f"""

EXPLAIN-THIS-STAT (ROI) — JSON-MODE OUTPUT REQUIRED

The student tapped 'Explain this to me' on their Return on Investment score.
You will produce a single JSON object matching the structure shown in
the TEMPLATE below. Do not write any text outside the JSON object.

REQUIRED TOOL CALL — call on your first turn:

  • get_career_paths(unitid={career.unitid}, cipcode="{career.cipcode}"{home_state_kwarg})
    {home_state_note}
    From the result row where soc_code = "{career.soc_code}", pull
    `earnings_1yr_median`, `lifetime_earnings_15yr` (= earnings × 18.5989),
    `roi_raw_multiplier` (residency-aware when you passed home_state),
    and `published_cost_4yr` (residency-aware sticker; this is the cost
    figure to cite in your prose). The row also carries
    `roi_raw_multiplier_in_state` and `stat_roi_in_state` shadow fields
    if the user is OOS at a public school — only mention them if the
    student would benefit from the contrast.

After the tool call returns, emit the JSON receipt. If a tool result
field is null, set the corresponding receipt field to null and the
matching `missing_reason` to a plain-English explanation. Do not
hallucinate values.

VOICE — ROI is a 15-year payback multiplier. We project starting
salary forward at flat 3% nominal annual growth for fifteen years
(matching the OBBBA Tiered Standard repayment term for a typical debt
load and the realistic median time-to-payoff for bachelor's borrowers,
17–21 years per Education Data Initiative / The College Investor 2026
/ ELFI). That cumulative earnings figure is divided by the school's
4-year published cost (sticker price — in-state for public schools
when home_state matches the school's state, out-of-state when it
doesn't). We use the published sticker, NOT the average aided net
price, because at the exploration phase you don't know what aid you
will receive. ROI is **financing-agnostic** — the loan slider does
not move it. The score answers "is this program priced fairly
relative to what it produces?", not "can I afford the loans?". ROI
deliberately does NOT model career progression — it measures what the
*program* delivers (the first job); what graduates do after that is
their outcome, not the program's. See spec
`docs/specs/roi-net-lifetime-value.md` §2 Decision #10.

SCORING SCALE (the UI renders this table below the math line — you may
reference it conversationally in the explainer or why_mix_paragraph):
  < 1.5x   → 1  (Underwater — degree underwater over 15 yrs)
  1.5–2.5x → 2  (Poor return)
  2.5–3.5x → 3  (Below average)
  3.5–4.5x → 4  (Modest return)
  4.5–5.5x → 5  (Average return)
  5.5–7.0x → 6  (Above average)
  7.0–9.0x → 7  (Strong return)
  9.0–12.0x → 8 (Excellent return)
  12.0–16.0x → 9 (Exceptional return)
  ≥ 16.0x   → 10 (Elite return — typically cheap-public + high-earning major)

VOICE-RULE SCOPING (this turn only):
  • LIFTED for the numeric JSON fields `anchor_dollars`: quote the
    actual dollar values precisely.
  • RETAINED for the prose JSON fields `one_liner`,
    `components[*].explainer`, and `why_mix_paragraph`: do NOT write
    'N/10', 'your score is N', or any numeric score reference.

TEMPLATE (replace every `__FILL_IN__` string with your written content):

{_ROI_RECEIPT_JSON_TEMPLATE}

CRITICAL — SENTINEL HANDLING. The strings `__FILL_IN__`, `[FILL_IN]`,
`<FILL_IN>`, `ONE-SENTENCE DEFINITION HERE`, and `PLACEHOLDER` are
placeholders ONLY — they MUST be replaced with your actual content.
Echoing them back verbatim will fail validation and the receipt will
not render. Write real prose in every prose field.

Do NOT include `[helper: ...]` blocks, `<thinking>...</thinking>` blocks,
or any meta-commentary.
"""


def _roi_explain_appendix_markdown(career: CareerOutcome, *, home_state: str | None = None) -> str:
    return f"""

EXPLAIN-THIS-STAT MODE — ROI (markdown fallback)

The structured-JSON path failed validation; produce the markdown
fallback. Voice rules above relax for this turn ONLY.

The cached tool values are already injected into the user message —
do NOT re-call get_career_paths. Read the values from the message
and produce the receipt.

REQUIRED RESPONSE STRUCTURE — exactly four sections in this order:

### Return on Investment — <SCORE>/10

**The one-liner.** One sentence naming what the score measures —
a 15-year payback multiplier (projected lifetime earnings ÷ 4-year
sticker cost).

**How it works.**
  - **100% — your 15-year payback multiplier.** {career.institution_name}'s
    {career.program_name} 4-year published cost is $<published_cost_4yr>.
    Graduates start at $<earnings_1yr_median>/yr; grown at flat 3% per
    year for fifteen years that cumulates to $<lifetime_earnings_15yr>.
    Multiplier = $<lifetime_earnings_15yr> / $<published_cost_4yr> =
    <multiplier>x.

  Math: Lifetime $<lifetime_earnings_15yr> ÷ Cost $<published_cost_4yr> =
  <multiplier>x → ROI score <SCORE>/10.

**Where the data comes from.**
  - Published cost: College Scorecard (U.S. Department of Education).
  - Graduate earnings: College Scorecard (U.S. Department of Education).
  - 15-year window: spec roi-net-lifetime-value §2 Decision #3, calibrated
    against actual median bachelor's-degree payoff timelines (17–21 years
    per Education Data Initiative / The College Investor 2026 / ELFI).

**Why we use this number.** A two-students contrast at the 15-year
mark in ~3 sentences. Same career, different costs, different cumulative
payoffs.
"""


def _postprocess_roi_explain_receipt(
    raw: str,
    build: Build,
    tool_call_log: list[gemma_client.ToolCallTurn],
    backend: str,
) -> ExplainStatReceipt | None:
    """ROI-specific 10-step pipeline. Mirrors _postprocess_ern_explain_receipt."""
    json_prefix = raw[:500] if raw else ""
    build_id = build.build_id
    call_site = "explain_roi_receipt"

    candidates = gemma_client._extract_json_objects(raw or "")
    parsed: dict[str, Any] | None = next(
        (c for c in candidates if isinstance(c, dict)), None
    )
    if parsed is None:
        _log_receipt_parse(
            call_site=call_site, parse_success=False,
            failure_reason="json_decode", json_prefix=json_prefix,
            build_id=build_id, backend=backend,
        )
        return None

    try:
        receipt = ExplainStatReceipt.model_validate(parsed)
    except ValidationError as exc:
        reason = "pydantic_validation"
        if "unreplaced template sentinel" in str(exc):
            reason = "sentinel_passthrough"
        _log_receipt_parse(
            call_site=call_site, parse_success=False,
            failure_reason=reason, json_prefix=json_prefix,
            build_id=build_id, backend=backend,
        )
        return None

    if receipt.stat_code != "ROI":
        _log_receipt_parse(
            call_site=call_site, parse_success=False,
            failure_reason="stat_code_mismatch", json_prefix=json_prefix,
            build_id=build_id, backend=backend,
        )
        return None

    build_score = build.career.stats.roi
    if build_score is None:
        _log_receipt_parse(
            call_site=call_site, parse_success=False,
            failure_reason="score_null", json_prefix=json_prefix,
            build_id=build_id, backend=backend,
        )
        return None

    receipt.score = build_score
    receipt.score_max = 10

    published_cost_4yr = build.career.published_cost_4yr
    earnings_1yr_median = build.career.earnings_1yr_median

    receipt.math_line = _render_math_line_roi(
        published_cost_4yr=published_cost_4yr,
        earnings_1yr_median=earnings_1yr_median,
        build_score=build_score,
        score_max=receipt.score_max,
    )

    for comp in receipt.components:
        canonical, was_normalized = _normalize_label(
            comp.weight_pct, comp.label, _ROI_LABEL_ALLOWLIST
        )
        if was_normalized:
            logger.warning(
                "roi_explain_receipt: label normalized weight=%d "
                "gemma=%r canonical=%r",
                comp.weight_pct, comp.label, canonical,
            )
            comp.label = canonical

    for comp in receipt.components:
        if comp.weight_pct == 100:
            comp.value_pct = None
            comp.anchor_dollars = (
                int(published_cost_4yr) if published_cost_4yr is not None else None
            )
            if published_cost_4yr is None:
                comp.missing_reason = (
                    "no published cost data for this institution yet"
                )
            elif earnings_1yr_median is None:
                comp.missing_reason = (
                    "no median earnings reported for this program yet"
                )
            else:
                comp.missing_reason = None

    receipt.sources = list(_ROI_RECEIPT_SOURCES)
    receipt.scoring_scale = _ROI_SCORING_SCALE

    _log_receipt_parse(
        call_site=call_site, parse_success=True,
        failure_reason=None, json_prefix=json_prefix,
        build_id=build_id, backend=backend,
    )
    return receipt


# ---------------------------------------------------------------------------
# RES receipt helpers
# ---------------------------------------------------------------------------

_RES_LABEL_ALLOWLIST: list[tuple[int, str]] = [
    (50, "AI exposure"),
    (50, "human-essential skills"),
]

_RES_RECEIPT_SOURCES: tuple[ReceiptSource, ...] = (
    ReceiptSource(
        label="AI exposure composite",
        name="Karpathy AI Exposure Index + Anthropic Economic Index",
    ),
    ReceiptSource(
        label="Human-essential skills",
        name="O*NET (Occupational Information Network, U.S. Department of Labor)",
    ),
)

_RES_SCORING_SCALE: list[ScoringTier] = [
    ScoringTier(label="AI-proof", range="9 – 10", score="9 – 10"),
    ScoringTier(label="Well-protected", range="7 – 8", score="7 – 8"),
    ScoringTier(label="Moderate exposure", range="5 – 6", score="5 – 6"),
    ScoringTier(label="Vulnerable", range="3 – 4", score="3 – 4"),
    ScoringTier(label="Highly exposed", range="1 – 2", score="1 – 2"),
]

_RES_ONE_LINER = (
    "AI Resilience blends how automatable a career's tasks are with "
    "how much the work depends on human judgment and social awareness."
)

_RES_WHY_MIX_PARAGRAPH = (
    "Two signals are mixed 50/50: AI exposure (a composite of Karpathy "
    "+ Anthropic + Gemma scoring how automatable the work is) and "
    "human-essential ratio (from the federal Occupational Information "
    "Network, O*NET, scoring how much the work depends on judgment, "
    "social awareness, or physical presence). The blend hedges against "
    "either signal being too pessimistic or too generous on its own."
)


def _normalize_label_by_position(
    idx: int,
    gemma_label: str,
    allowlist: list[tuple[int, str]],
) -> tuple[str, bool]:
    """Match Gemma's label against the per-position canonical allowlist.

    Used for stats where multiple components share the same weight_pct
    (RES has two 50% components) — position is the disambiguator.
    Returns (canonical_label, was_normalized).
    """
    if idx >= len(allowlist):
        return gemma_label, False
    _, canonical = allowlist[idx]
    if gemma_label.strip().lower() == canonical.lower():
        return canonical, False
    return canonical, True


def _render_math_line_res(
    *,
    stat_res_raw: int | None,
    stat_hmn_raw: int | None,
    build_score: int,
    score_max: int,
) -> str:
    """Build RES's math-line string.

    Format: '0.5 × 8 + 0.5 × 7 → score 8/10'
    """
    res_str = str(stat_res_raw) if stat_res_raw is not None else "n/a"
    hmn_str = str(stat_hmn_raw) if stat_hmn_raw is not None else "n/a"
    return (
        f"0.5 × {res_str} + 0.5 × {hmn_str} → score "
        f"{build_score}/{score_max}"
    )


def _extract_res_raw_scores(
    tool_call_log: list[gemma_client.ToolCallTurn],
    soc_code: str | None = None,
) -> tuple[int | None, int | None]:
    """Pull stat_res and stat_hmn from the get_career_paths tool result."""
    stat_res: int | None = None
    stat_hmn: int | None = None
    for turn in tool_call_log:
        if turn.error or turn.tool_name != "get_career_paths":
            continue
        result_json = turn.tool_result_full or turn.tool_result_preview
        try:
            preview = json.loads(result_json)
        except (json.JSONDecodeError, ValueError):
            continue
        rows = preview.get("data") if isinstance(preview, dict) else None
        if not isinstance(rows, list):
            continue
        matching_rows = [
            row for row in rows
            if isinstance(row, dict)
            and soc_code is not None
            and str(row.get("soc_code", "")).strip() == soc_code
        ]
        candidate_rows = matching_rows if matching_rows else rows
        for row in candidate_rows:
            if not isinstance(row, dict):
                continue
            if stat_res is None:
                val = row.get("stat_res")
                if isinstance(val, (int, float)):
                    stat_res = int(val)
            if stat_hmn is None:
                val = row.get("stat_hmn")
                if isinstance(val, (int, float)):
                    stat_hmn = int(val)
            if stat_res is not None and stat_hmn is not None:
                break
        if stat_res is not None and stat_hmn is not None:
            break
    return stat_res, stat_hmn


def _clean_task_evidence(values: list[Any]) -> list[str] | None:
    bullets: list[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, dict):
            text_raw = (
                value.get("activity")
                or value.get("task")
                or value.get("name")
                or value.get("title")
                or value.get("description")
            )
        else:
            text_raw = value
        if not isinstance(text_raw, str):
            continue
        text = " ".join(text_raw.strip().split())
        if not text or text.lower() in seen:
            continue
        seen.add(text.lower())
        bullets.append(text)
        if len(bullets) >= 4:
            break
    return bullets or None


def _extract_res_task_evidence(
    tool_call_log: list[gemma_client.ToolCallTurn],
) -> tuple[list[str] | None, list[str] | None]:
    """Pull task evidence from get_task_breakdown if Gemma called it."""
    automatable: list[str] | None = None
    human: list[str] | None = None
    for turn in tool_call_log:
        if turn.error or turn.tool_name != "get_task_breakdown":
            continue
        result_json = turn.tool_result_full or turn.tool_result_preview
        try:
            preview = json.loads(result_json)
        except (json.JSONDecodeError, ValueError):
            continue
        row = preview.get("data") if isinstance(preview, dict) else None
        if not isinstance(row, dict):
            continue
        auto_raw = row.get("task_breakdown_automatable") or row.get("top_5_activities")
        human_raw = row.get("task_breakdown_human") or row.get("top_human_activities")
        if isinstance(auto_raw, list):
            automatable = _clean_task_evidence(auto_raw)
        if isinstance(human_raw, list):
            human = _clean_task_evidence(human_raw)
        if automatable or human:
            break
    return automatable, human


def _fetch_res_task_evidence(
    soc_code: str,
) -> tuple[list[str] | None, list[str] | None]:
    """Synchronously fetch task evidence for RES receipts.

    This keeps task bullets deterministic. Gemma is allowed to write the
    explainer prose, but the concrete examples should come from trusted MCP
    data rather than from the model's choice to call a tool.
    """
    try:
        result = mcp_client.call("get_task_breakdown", {"soc_code": soc_code})
    except Exception as exc:  # noqa: BLE001 - receipt should still render
        logger.warning(
            "res_explain_receipt: get_task_breakdown failed for %s: %s",
            soc_code,
            exc,
        )
        return None, None
    row = result.get("data") if isinstance(result, dict) else None
    if not isinstance(row, dict):
        return None, None
    auto_raw = row.get("task_breakdown_automatable") or row.get("top_5_activities")
    human_raw = row.get("task_breakdown_human") or row.get("top_human_activities")
    auto = _clean_task_evidence(auto_raw) if isinstance(auto_raw, list) else None
    human = _clean_task_evidence(human_raw) if isinstance(human_raw, list) else None
    return auto, human


def _contextualize_res_task_evidence(
    automatable: list[str] | None,
    human: list[str] | None,
    occupation_title: str,
) -> tuple[list[str] | None, list[str] | None]:
    """Translate generic O*NET activity labels into occupation-shaped bullets.

    O*NET activity labels are trustworthy but broad ("Working with Computers").
    For receipts, those labels need enough context for a student to picture the
    actual work. Keep the original activity meaning, but specialize known broad
    labels for high-visibility occupations where the generic label is too vague.
    """
    occupation_key = occupation_title.lower()
    if "microbiologist" not in occupation_key:
        return automatable, human

    auto_map = {
        "working with computers": (
            "Running bioinformatics tools, lab databases, or genome-sequencing "
            "analysis software"
        ),
        "analyzing data or information": (
            "Interpreting culture results, assay readouts, or genetic data"
        ),
        "getting information": (
            "Reviewing lab observations, research papers, and sample data"
        ),
        "documenting/recording information": (
            "Recording protocols, sample results, and lab notes"
        ),
    }
    human_map = {
        "making decisions and solving problems": (
            "Choosing experimental methods and interpreting unexpected lab results"
        ),
        "thinking creatively": (
            "Designing experiments or troubleshooting contamination problems"
        ),
        "establishing and maintaining interpersonal relationships": (
            "Coordinating with lab teams, clinicians, or public-health partners"
        ),
        "training and teaching others": (
            "Teaching lab protocols and safety procedures"
        ),
    }

    def apply_map(values: list[str] | None, mapping: dict[str, str]) -> list[str] | None:
        if values is None:
            return None
        return [mapping.get(value.lower(), value) for value in values]

    return apply_map(automatable, auto_map), apply_map(human, human_map)


def _resolve_res_task_evidence(
    build: Build,
    tool_call_log: list[gemma_client.ToolCallTurn],
) -> tuple[list[str] | None, list[str] | None]:
    auto_evidence = _clean_task_evidence(build.career.task_breakdown_automatable)
    human_evidence = _clean_task_evidence(build.career.task_breakdown_human)
    if auto_evidence is None or human_evidence is None:
        tool_auto, tool_human = _extract_res_task_evidence(tool_call_log)
        if auto_evidence is None:
            auto_evidence = tool_auto
        if human_evidence is None:
            human_evidence = tool_human
    if auto_evidence is None or human_evidence is None:
        fetched_auto, fetched_human = _fetch_res_task_evidence(build.career.soc_code)
        if auto_evidence is None:
            auto_evidence = fetched_auto
        if human_evidence is None:
            human_evidence = fetched_human
    return _contextualize_res_task_evidence(
        auto_evidence,
        human_evidence,
        build.career.occupation_title or "",
    )



def _res_level_word(score: int | None, *, exposure: bool) -> str:
    if score is None:
        return "unknown"
    if score >= 7:
        return "high" if exposure else "strong"
    if score >= 4:
        return "moderate"
    return "low" if exposure else "thin"


def _build_res_receipt_from_context(
    *,
    build: Build,
    tool_call_log: list[gemma_client.ToolCallTurn],
    backend: str,
    failure_reason: str,
    json_prefix: str,
) -> ExplainStatReceipt | None:
    """Build a RES receipt without trusting Gemma's JSON.

    The RES explainer has enough deterministic inputs in the Build and MCP
    task profile to avoid the markdown retry. If JSON-mode output is malformed,
    we still return the structured receipt so the student gets the task-level
    evidence instead of a weaker fallback paragraph.
    """
    build_score = build.career.stats.res
    if build_score is None:
        return None

    stat_res_raw = build.career.raw_stat_res
    stat_hmn_raw = build.career.raw_stat_hmn
    if stat_res_raw is None or stat_hmn_raw is None:
        tool_res, tool_hmn = _extract_res_raw_scores(
            tool_call_log,
            build.career.soc_code,
        )
        if stat_res_raw is None:
            stat_res_raw = tool_res
        if stat_hmn_raw is None:
            stat_hmn_raw = tool_hmn

    auto_evidence, human_evidence = _resolve_res_task_evidence(build, tool_call_log)
    career_label = build.career.occupation_title or "this career"
    exposure_word = _res_level_word(stat_res_raw, exposure=True)
    human_word = _res_level_word(stat_hmn_raw, exposure=False)

    receipt = ExplainStatReceipt(
        kind="receipt",
        stat_code="RES",
        stat_name="AI Resilience",
        score=build_score,
        score_max=10,
        one_liner=_RES_ONE_LINER,
        components=[
            StatComponent(
                weight_pct=50,
                label="AI exposure",
                explainer=(
                    f"{career_label} has {exposure_word} exposure to automation. "
                    "The tasks listed below are the parts of the work most likely "
                    "to be compressed by software, especially in entry-level roles."
                ),
                value_pct=(
                    min(max(stat_res_raw * 10, 0), 100)
                    if stat_res_raw is not None else None
                ),
                anchor_text=(
                    f"AI-exposure rating: {stat_res_raw}/10"
                    if stat_res_raw is not None else "AI-exposure rating unavailable"
                ),
                anchor_dollars=None,
                missing_reason=(
                    None if stat_res_raw is not None
                    else "no AI-exposure score available for this career yet"
                ),
                evidence_bullets=auto_evidence,
            ),
            StatComponent(
                weight_pct=50,
                label="human-essential skills",
                explainer=(
                    f"{career_label} has a {human_word} human-essential buffer. "
                    "The tasks listed below are the parts where judgment, people "
                    "skills, or creative decisions still matter most."
                ),
                value_pct=(
                    min(max(stat_hmn_raw * 10, 0), 100)
                    if stat_hmn_raw is not None else None
                ),
                anchor_text=(
                    f"Human-essential rating: {stat_hmn_raw}/10"
                    if stat_hmn_raw is not None
                    else "Human-essential rating unavailable"
                ),
                anchor_dollars=None,
                missing_reason=(
                    None if stat_hmn_raw is not None
                    else "no human-essential score available for this career yet"
                ),
                evidence_bullets=human_evidence,
            ),
        ],
        math_line=_render_math_line_res(
            stat_res_raw=stat_res_raw,
            stat_hmn_raw=stat_hmn_raw,
            build_score=build_score,
            score_max=10,
        ),
        sources=list(_RES_RECEIPT_SOURCES),
        why_mix_paragraph=_RES_WHY_MIX_PARAGRAPH,
    )
    _log_receipt_parse(
        call_site="explain_res_receipt",
        parse_success=False,
        failure_reason=f"{failure_reason}_server_built",
        json_prefix=json_prefix,
        build_id=build.build_id,
        backend=backend,
    )
    return receipt


_RES_RECEIPT_JSON_TEMPLATE = """{
  "kind": "receipt",
  "stat_code": "RES",
  "stat_name": "AI Resilience",
  "score": 8,
  "score_max": 10,
  "one_liner": "__FILL_IN__: ONE-SENTENCE DEFINITION of what this score measures. Plain English a 16-year-old reads. No jargon, no /10, no percentiles.",
  "components": [
    {
      "weight_pct": 50,
      "label": "AI exposure",
      "explainer": "__FILL_IN__: 1-2 sentences. How automatable is this career's task profile? Reference the composite score (from Karpathy, Anthropic, and Gemma). Higher is MORE exposed to AI automation. Do NOT include the X/10 score.",
      "value_pct": 80,
      "anchor_text": "AI-exposure rating: 8/10",
      "anchor_dollars": null,
      "missing_reason": null,
      "evidence_bullets": null
    },
    {
      "weight_pct": 50,
      "label": "human-essential skills",
      "explainer": "__FILL_IN__: 1-2 sentences. How much does this career depend on judgment, social awareness, or physical presence that resists automation? Reference O*NET (the federal Occupational Information Network). Higher is MORE human-dependent. Do NOT include the X/10 score.",
      "value_pct": 70,
      "anchor_text": "Human-essential rating: 7/10",
      "anchor_dollars": null,
      "missing_reason": null,
      "evidence_bullets": null
    }
  ],
  "math_line": "0.5 \\u00d7 8 + 0.5 \\u00d7 7 \\u2192 score 8/10",
  "sources": [
    {"label": "AI exposure composite", "name": "Karpathy AI Exposure Index + Anthropic Economic Index"},
    {"label": "Human-essential skills", "name": "O*NET (Occupational Information Network, U.S. Department of Labor)"}
  ],
  "why_mix_paragraph": "__FILL_IN__: ~3-sentence explanation of WHY we blend two signals (AI exposure + human-essential). Show why using only one signal would mislead. Do NOT include the X/10 score."
}"""


def _res_explain_appendix_json(career: CareerOutcome, *, home_state: str | None = None) -> str:
    return f"""

EXPLAIN-THIS-STAT (RES) — JSON-MODE OUTPUT REQUIRED

The student tapped 'Explain this to me' on their AI Resilience score.
You will produce a single JSON object matching the structure shown in
the TEMPLATE below. Do not write any text outside the JSON object.

REQUIRED TOOL CALL — call on your first turn:

  • get_career_paths(unitid={career.unitid}, cipcode="{career.cipcode}")
    From the result row where soc_code = "{career.soc_code}", pull
    `stat_res` (AI exposure), `stat_hmn` (human-essential),
    `task_breakdown_automatable`, and `task_breakdown_human`.

After the tool call returns, emit the JSON receipt.

VOICE — two signals are mixed 50/50: AI exposure (a composite of
Karpathy + Anthropic + Gemma scoring how automatable the work is) and
human-essential ratio (from the federal Occupational Information
Network, O*NET, scoring how much the work depends on judgment, social
awareness, or physical presence). The blend hedges against either
signal being too pessimistic or too generous on its own.

SCORING SCALE (the UI renders this table below the math line — you may
reference it conversationally in the explainer or why_mix_paragraph):
  9–10 → AI-proof
  7–8  → Well-protected
  5–6  → Moderate exposure
  3–4  → Vulnerable
  1–2  → Highly exposed

TRANSPARENCY REQUIREMENT:
  • Explain vulnerability, not just definitions. A student should leave
    understanding which parts of the work AI can already eat and which
    parts still require people.
  • The task categories (e.g. "Working with Computers", "Analyzing Data")
    come from O*NET and are generic across all occupations. Your job is to
    make them SPECIFIC to this occupation. For every task you mention,
    describe what it concretely looks like for a {career.occupation_title}
    — e.g. for a microbiologist, "Working with Computers" means running
    bioinformatics pipelines and analyzing genome sequencing data, NOT
    just "using a computer." A student reading this should picture their
    actual daily work, not a generic job description.
  • For the AI exposure explainer, name 2-3 automatable tasks from
    task_breakdown_automatable when available. For each one, say what AI
    can already do in that area for this specific role. Say that AI may
    reduce or compress junior work even when it does not replace the
    whole career.
  • For the human-essential explainer, name 2-3 human-buffer tasks from
    task_breakdown_human when available. For each one, explain WHY this
    specific task requires a human in this occupation — not just that it
    does.
  • Do not invent task examples. If task evidence is unavailable, say the
    receipt has the score inputs but not task-level evidence.
  • Leave evidence_bullets as null. The server stamps trusted task bullets
    from the build context or deterministic MCP lookup.

VOICE-RULE SCOPING (this turn only):
  • LIFTED for the numeric JSON fields `value_pct`: quote the actual
    percentile values precisely.
  • RETAINED for the prose JSON fields `one_liner`,
    `components[*].explainer`, and `why_mix_paragraph`: do NOT write
    'N/10', 'your score is N', or any numeric score reference.

TEMPLATE (replace every `__FILL_IN__` string with your written content):

{_RES_RECEIPT_JSON_TEMPLATE}

CRITICAL — SENTINEL HANDLING. The strings `__FILL_IN__`, `[FILL_IN]`,
`<FILL_IN>`, `ONE-SENTENCE DEFINITION HERE`, and `PLACEHOLDER` are
placeholders ONLY — they MUST be replaced with your actual content.
Echoing them back verbatim will fail validation and the receipt will
not render. Write real prose in every prose field.

Do NOT include `[helper: ...]` blocks, `<thinking>...</thinking>` blocks,
or any meta-commentary.
"""


def _res_explain_appendix_markdown(career: CareerOutcome, *, home_state: str | None = None) -> str:
    return f"""

EXPLAIN-THIS-STAT MODE — RES (markdown fallback)

The structured-JSON path failed validation; produce the markdown
fallback.

The cached tool values are already injected into the user message —
do NOT re-call get_career_paths.

REQUIRED RESPONSE STRUCTURE — exactly four sections in this order:

### AI Resilience — <SCORE>/10

**The one-liner.** One sentence naming what the score measures.

**How it works.**
  - **50% — AI exposure.** {career.occupation_title} scores <stat_res>/10
    on the AI-exposure side.
  - **50% — human-essential skills.** {career.occupation_title} scores
    <stat_hmn>/10 on the human-essential side (O*NET).

  Math: 0.5 × <stat_res> + 0.5 × <stat_hmn> = <blend> → RES score <SCORE>/10.

**Where the data comes from.**
  - AI exposure composite: Karpathy AI Exposure Index + Anthropic Economic Index.
  - Human-essential skills: O*NET (U.S. Department of Labor).

**Why we mix both pieces.** A ~3-sentence explanation of the blend.
"""


def _postprocess_res_explain_receipt(
    raw: str,
    build: Build,
    tool_call_log: list[gemma_client.ToolCallTurn],
    backend: str,
) -> ExplainStatReceipt | None:
    """RES-specific 10-step pipeline."""
    json_prefix = raw[:500] if raw else ""
    build_id = build.build_id
    call_site = "explain_res_receipt"

    candidates = gemma_client._extract_json_objects(raw or "")
    parsed: dict[str, Any] | None = next(
        (c for c in candidates if isinstance(c, dict)), None
    )
    if parsed is None:
        return _build_res_receipt_from_context(
            build=build,
            tool_call_log=tool_call_log,
            backend=backend,
            failure_reason="json_decode",
            json_prefix=json_prefix,
        )

    try:
        receipt = ExplainStatReceipt.model_validate(parsed)
    except ValidationError as exc:
        reason = "pydantic_validation"
        if "unreplaced template sentinel" in str(exc):
            reason = "sentinel_passthrough"
        return _build_res_receipt_from_context(
            build=build,
            tool_call_log=tool_call_log,
            backend=backend,
            failure_reason=reason,
            json_prefix=json_prefix,
        )

    if receipt.stat_code != "RES":
        return _build_res_receipt_from_context(
            build=build,
            tool_call_log=tool_call_log,
            backend=backend,
            failure_reason="stat_code_mismatch",
            json_prefix=json_prefix,
        )

    build_score = build.career.stats.res
    if build_score is None:
        _log_receipt_parse(
            call_site=call_site, parse_success=False,
            failure_reason="score_null", json_prefix=json_prefix,
            build_id=build_id, backend=backend,
        )
        return None

    if len(receipt.components) != 2:
        return _build_res_receipt_from_context(
            build=build,
            tool_call_log=tool_call_log,
            backend=backend,
            failure_reason="component_count_mismatch",
            json_prefix=json_prefix,
        )

    receipt.score = build_score
    receipt.score_max = 10

    stat_res_raw = build.career.raw_stat_res
    stat_hmn_raw = build.career.raw_stat_hmn
    if stat_res_raw is None or stat_hmn_raw is None:
        tool_res, tool_hmn = _extract_res_raw_scores(
            tool_call_log,
            build.career.soc_code,
        )
        if stat_res_raw is None:
            stat_res_raw = tool_res
        if stat_hmn_raw is None:
            stat_hmn_raw = tool_hmn

    receipt.math_line = _render_math_line_res(
        stat_res_raw=stat_res_raw,
        stat_hmn_raw=stat_hmn_raw,
        build_score=build_score,
        score_max=receipt.score_max,
    )

    auto_evidence, human_evidence = _resolve_res_task_evidence(build, tool_call_log)

    for idx, comp in enumerate(receipt.components):
        canonical, was_normalized = _normalize_label_by_position(
            idx, comp.label, _RES_LABEL_ALLOWLIST
        )
        if was_normalized:
            logger.warning(
                "res_explain_receipt: label normalized idx=%d "
                "gemma=%r canonical=%r",
                idx, comp.label, canonical,
            )
            comp.label = canonical

    # Position 0 = AI exposure (stat_res), Position 1 = human-essential (stat_hmn)
    receipt.components[0].value_pct = (
        min(max(stat_res_raw * 10, 0), 100) if stat_res_raw is not None else None
    )
    receipt.components[0].anchor_dollars = None
    receipt.components[0].evidence_bullets = auto_evidence
    if stat_res_raw is None:
        receipt.components[0].missing_reason = (
            "no AI-exposure score available for this career yet"
        )
    else:
        receipt.components[0].missing_reason = None

    receipt.components[1].value_pct = (
        min(max(stat_hmn_raw * 10, 0), 100) if stat_hmn_raw is not None else None
    )
    receipt.components[1].anchor_dollars = None
    receipt.components[1].evidence_bullets = human_evidence
    if stat_hmn_raw is None:
        receipt.components[1].missing_reason = (
            "no human-essential score available for this career yet"
        )
    else:
        receipt.components[1].missing_reason = None

    receipt.sources = list(_RES_RECEIPT_SOURCES)
    receipt.scoring_scale = _RES_SCORING_SCALE

    _log_receipt_parse(
        call_site=call_site, parse_success=True,
        failure_reason=None, json_prefix=json_prefix,
        build_id=build_id, backend=backend,
    )
    return receipt


# ---------------------------------------------------------------------------
# GRW receipt helpers
# ---------------------------------------------------------------------------

_GRW_SCORING_SCALE: list[ScoringTier] = [
    ScoringTier(label="Booming", range="+20% or more", score="9 – 10"),
    ScoringTier(label="Strong growth", range="+10% to +20%", score="8 – 9"),
    ScoringTier(label="Above average", range="+5% to +10%", score="7 – 8"),
    ScoringTier(label="Average growth", range="+1% to +5%", score="5 – 7"),
    ScoringTier(label="Flat", range="-1% to +1%", score="4 – 5"),
    ScoringTier(label="Declining", range="-10% to -1%", score="3 – 4"),
    ScoringTier(label="Shrinking fast", range="-20% or worse", score="1 – 3"),
]

_GRW_LABEL_ALLOWLIST: dict[int, str] = {
    100: "this career's projected employment change",
}

_GRW_RECEIPT_SOURCES: tuple[ReceiptSource, ...] = (
    ReceiptSource(
        label="Employment projections",
        name=(
            "Occupational Outlook Handbook, published by the Bureau "
            "of Labor Statistics (BLS)"
        ),
    ),
)

_GRW_ONE_LINER = (
    "Growth Outlook reads the federal 10-year projection of how many "
    "more or fewer people will work in this career a decade from now."
)

_GRW_WHY_MIX_PARAGRAPH = (
    "This score reads BLS's 10-year employment-change projection — a "
    "forecast of how many more (or fewer) people will be working in "
    "this career a decade from now — and maps it through a bucket. "
    "We use a projection (not past growth) because for a college "
    "decision you care about the world you'll enter, not the world "
    "you'd have entered in 2018."
)


def _render_math_line_grw(
    *,
    employment_change_pct: float | None,
    build_score: int,
    score_max: int,
) -> str:
    """Build GRW's math-line string.

    Format: '+15.2% employment change → GRW score 8/10'
    """
    if employment_change_pct is None:
        return f"n/a employment change → score {build_score}/{score_max}"
    if employment_change_pct > 0:
        pct_str = f"+{employment_change_pct:.1f}%"
    elif employment_change_pct == 0:
        pct_str = "0.0%"
    else:
        pct_str = f"{employment_change_pct:.1f}%"
    return (
        f"{pct_str} employment change → GRW score "
        f"{build_score}/{score_max}"
    )


def _extract_grw_employment_change(
    tool_call_log: list[gemma_client.ToolCallTurn],
) -> float | None:
    """Pull employment_change_pct from the get_occupation_data tool result."""
    for turn in tool_call_log:
        if turn.error or turn.tool_name != "get_occupation_data":
            continue
        result_json = turn.tool_result_full or turn.tool_result_preview
        try:
            preview = json.loads(result_json)
        except (json.JSONDecodeError, ValueError):
            continue
        row = preview.get("data") if isinstance(preview, dict) else None
        if not isinstance(row, dict):
            continue
        val = row.get("employment_change_pct")
        if isinstance(val, (int, float)):
            return float(val)
    return None


_GRW_RECEIPT_JSON_TEMPLATE = """{
  "kind": "receipt",
  "stat_code": "GRW",
  "stat_name": "Growth Outlook",
  "score": 8,
  "score_max": 10,
  "one_liner": "__FILL_IN__: ONE-SENTENCE DEFINITION of what this score measures. Plain English a 16-year-old reads. No jargon, no /10, no percentiles.",
  "components": [
    {
      "weight_pct": 100,
      "label": "this career's projected employment change",
      "explainer": "__FILL_IN__: 1-3 sentences. Name the career and the BLS 10-year employment-change projection (in %). State the BLS growth category (e.g., 'Much faster than average'). Do NOT include the X/10 score.",
      "value_pct": null,
      "anchor_text": "+15.2% projected change over 10 years",
      "anchor_dollars": null,
      "missing_reason": null
    }
  ],
  "math_line": "+15.2% employment change \\u2192 GRW score 8/10",
  "sources": [
    {"label": "Employment projections", "name": "Occupational Outlook Handbook, published by the Bureau of Labor Statistics (BLS)"}
  ],
  "why_mix_paragraph": "__FILL_IN__: ~3-sentence explanation of WHY a 10-year projection matters for a college decision. Emphasize that you care about the world you'll ENTER, not past growth. Do NOT include the X/10 score."
}"""


def _grw_explain_appendix_json(career: CareerOutcome, *, home_state: str | None = None) -> str:
    return f"""

EXPLAIN-THIS-STAT (GRW) — JSON-MODE OUTPUT REQUIRED

The student tapped 'Explain this to me' on their Growth Outlook score.
You will produce a single JSON object matching the structure shown in
the TEMPLATE below. Do not write any text outside the JSON object.

REQUIRED TOOL CALL — call on your first turn:

  • get_occupation_data(soc_code="{career.soc_code}")
    Pull `employment_change_pct` and `growth_category`.

After the tool call returns, emit the JSON receipt.

VOICE — this score reads BLS's 10-year employment-change projection
— a forecast of how many more (or fewer) people will be working in
this career a decade from now — and maps it through a bucket:
-20% or worse is a 1, flat is 4-5, +10% is 7.5, +20% or better is
9-10. We use a projection (not past growth) because for a college
decision you care about the world you'll enter, not the world you'd
have entered in 2018.

VOICE-RULE SCOPING (this turn only):
  • LIFTED for the `anchor_text` JSON field: quote the actual
    percentage precisely (e.g., "+15.2% projected change over 10 years").
  • RETAINED for the prose JSON fields `one_liner`,
    `components[*].explainer`, and `why_mix_paragraph`: do NOT write
    'N/10', 'your score is N', or any numeric score reference.

TEMPLATE (replace every `__FILL_IN__` string with your written content):

{_GRW_RECEIPT_JSON_TEMPLATE}

CRITICAL — SENTINEL HANDLING. The strings `__FILL_IN__`, `[FILL_IN]`,
`<FILL_IN>`, `ONE-SENTENCE DEFINITION HERE`, and `PLACEHOLDER` are
placeholders ONLY — they MUST be replaced with your actual content.
Echoing them back verbatim will fail validation and the receipt will
not render. Write real prose in every prose field.

Do NOT include `[helper: ...]` blocks, `<thinking>...</thinking>` blocks,
or any meta-commentary.
"""


def _grw_explain_appendix_markdown(career: CareerOutcome, *, home_state: str | None = None) -> str:
    return f"""

EXPLAIN-THIS-STAT MODE — GRW (markdown fallback)

The structured-JSON path failed validation; produce the markdown
fallback.

The cached tool values are already injected into the user message —
do NOT re-call get_occupation_data.

REQUIRED RESPONSE STRUCTURE — exactly four sections in this order:

### Growth Outlook — <SCORE>/10

**The one-liner.** One sentence naming what the score measures.

**How it works.**
  - **100% — this career's projected employment change.**
    {career.occupation_title}'s BLS 10-year projection: <employment_change_pct>%.

  Math: <employment_change_pct>% employment change → GRW score <SCORE>/10.

**Where the data comes from.**
  - Employment projections: Occupational Outlook Handbook, published by
    the Bureau of Labor Statistics (BLS).

**Why we use this number.** A ~3-sentence explanation of the projection.
"""


def _postprocess_grw_explain_receipt(
    raw: str,
    build: Build,
    tool_call_log: list[gemma_client.ToolCallTurn],
    backend: str,
) -> ExplainStatReceipt | None:
    """GRW-specific 10-step pipeline."""
    json_prefix = raw[:500] if raw else ""
    build_id = build.build_id
    call_site = "explain_grw_receipt"

    candidates = gemma_client._extract_json_objects(raw or "")
    parsed: dict[str, Any] | None = next(
        (c for c in candidates if isinstance(c, dict)), None
    )
    if parsed is None:
        _log_receipt_parse(
            call_site=call_site, parse_success=False,
            failure_reason="json_decode", json_prefix=json_prefix,
            build_id=build_id, backend=backend,
        )
        return None

    # GRW has a single 100%-weight component; value_pct is server-
    # stamped (always overwritten to None below). Gemma often fills it
    # with the employment_change_pct float (e.g. 4.1), which fails
    # Pydantic's int coercion. Null it before validation.
    for comp in parsed.get("components", []):
        if isinstance(comp, dict):
            comp["value_pct"] = None

    try:
        receipt = ExplainStatReceipt.model_validate(parsed)
    except ValidationError as exc:
        reason = "pydantic_validation"
        if "unreplaced template sentinel" in str(exc):
            reason = "sentinel_passthrough"
        _log_receipt_parse(
            call_site=call_site, parse_success=False,
            failure_reason=reason, json_prefix=json_prefix,
            build_id=build_id, backend=backend,
        )
        return None

    if receipt.stat_code != "GRW":
        _log_receipt_parse(
            call_site=call_site, parse_success=False,
            failure_reason="stat_code_mismatch", json_prefix=json_prefix,
            build_id=build_id, backend=backend,
        )
        return None

    build_score = build.career.stats.grw
    if build_score is None:
        _log_receipt_parse(
            call_site=call_site, parse_success=False,
            failure_reason="score_null", json_prefix=json_prefix,
            build_id=build_id, backend=backend,
        )
        return None

    receipt.score = build_score
    receipt.score_max = 10

    employment_change_pct = _extract_grw_employment_change(tool_call_log)

    receipt.math_line = _render_math_line_grw(
        employment_change_pct=employment_change_pct,
        build_score=build_score,
        score_max=receipt.score_max,
    )

    for comp in receipt.components:
        canonical, was_normalized = _normalize_label(
            comp.weight_pct, comp.label, _GRW_LABEL_ALLOWLIST
        )
        if was_normalized:
            logger.warning(
                "grw_explain_receipt: label normalized weight=%d "
                "gemma=%r canonical=%r",
                comp.weight_pct, comp.label, canonical,
            )
            comp.label = canonical

    for comp in receipt.components:
        if comp.weight_pct == 100:
            comp.value_pct = None
            comp.anchor_dollars = None
            if employment_change_pct is not None:
                if employment_change_pct > 0:
                    pct_str = f"+{employment_change_pct:.1f}%"
                elif employment_change_pct == 0:
                    pct_str = "0.0%"
                else:
                    pct_str = f"{employment_change_pct:.1f}%"
                comp.anchor_text = (
                    f"{pct_str} projected change over 10 years"
                )
                comp.missing_reason = None
            else:
                comp.anchor_text = "employment projection not available"
                comp.missing_reason = (
                    "no 10-year employment projection reported for this "
                    "occupation yet"
                )

    receipt.sources = list(_GRW_RECEIPT_SOURCES)
    receipt.scoring_scale = _GRW_SCORING_SCALE

    _log_receipt_parse(
        call_site=call_site, parse_success=True,
        failure_reason=None, json_prefix=json_prefix,
        build_id=build_id, backend=backend,
    )
    return receipt


# ---------------------------------------------------------------------------
# AURA explain-stat receipt
#   spec: docs/specs/feature-explain-stat-receipt-aura.md
# ---------------------------------------------------------------------------

_AURA_SCORING_SCALE: list[ScoringTier] = [
    ScoringTier(label="Elite brand", range="9 – 10", score="9 – 10"),
    ScoringTier(label="Strong brand", range="7 – 8", score="7 – 8"),
    ScoringTier(label="Solid brand", range="5 – 6", score="5 – 6"),
    ScoringTier(label="Modest brand", range="3 – 4", score="3 – 4"),
    ScoringTier(label="Low profile", range="1 – 2", score="1 – 2"),
]

_AURA_LABEL_ALLOWLIST: dict[int, str] = {
    100: "your school's brand gravity",
}

_AURA_RECEIPT_SOURCES: tuple[ReceiptSource, ...] = (
    ReceiptSource(
        label="Endowment + marketing",
        name=(
            "Integrated Postsecondary Education Data System (IPEDS), "
            "U.S. Department of Education"
        ),
    ),
    ReceiptSource(
        label="Athletics",
        name=(
            "Equity in Athletics Disclosure Act (EADA), "
            "U.S. Department of Education"
        ),
    ),
)

_AURA_ONE_LINER = (
    "Brand Gravity measures how much weight your school's name carries "
    "— for networking, alumni access, recruiter shortlists, and "
    "graduate-school admissions."
)

_AURA_WHY_MIX_PARAGRAPH = (
    "Most college tools pretend prestige doesn't matter — but it "
    "absolutely does for networking, alumni access, recruiter "
    "shortlists, and graduate-school admissions. Three signals, "
    "measured per student so big and small schools are on the same "
    "scale: endowment per full-time student (how much money the "
    "school has invested per kid), marketing reach per student, and "
    "athletic spending per student. The MAX rewards being elite at "
    "any one (Stanford has the endowment; Notre Dame has the "
    "football); the MEAN keeps it balanced."
)

_AURA_SIGNAL_DEFINITIONS: dict[str, tuple[str, str]] = {
    "endowment_per_fte": (
        "Endowment",
        "how much savings the school holds per student",
    ),
    "marketing_ratio": (
        "Marketing",
        "how much the school spends getting its name out there, per student",
    ),
    "athletic_spend_per_fte": (
        "Athletics",
        "how much the school puts into sports programs per student",
    ),
}

_AURA_BASIS_SIGNALS: dict[str, list[str]] = {
    "three_term": ["endowment_per_fte", "marketing_ratio", "athletic_spend_per_fte"],
    "two_term_finance_only": ["endowment_per_fte", "marketing_ratio"],
    "two_term_no_endowment": ["marketing_ratio", "athletic_spend_per_fte"],
    "one_term_marketing_only": ["marketing_ratio"],
}

_AURA_EXPLAIN_USER_PROMPT = (
    "Explain my Brand Gravity score with the receipts. Show me the "
    "actual numbers behind it, not just the definition."
)

_AURA_RECEIPT_JSON_TEMPLATE = """{
  "kind": "receipt",
  "stat_code": "AURA",
  "stat_name": "Brand Gravity",
  "score": 8,
  "score_max": 10,
  "one_liner": "__FILL_IN__: ONE-SENTENCE DEFINITION of what this score measures. Plain English a 16-year-old reads. No jargon, no /10, no percentiles.",
  "components": [
    {
      "weight_pct": 100,
      "label": "your school's brand gravity",
      "explainer": "__FILL_IN__: 1-3 sentences. Name the school and describe how endowment, marketing, and athletic spending per student combine to measure institutional weight. Do NOT include the X/10 score.",
      "value_pct": null,
      "anchor_text": "__FILL_IN__: Describe the school's institutional weight signals in plain English.",
      "anchor_dollars": null,
      "missing_reason": null
    }
  ],
  "math_line": "MAX-MEAN blend of 3 signals \\u2192 composite 0.72 \\u2192 AURA score 8/10",
  "sources": [
    {"label": "Endowment + marketing", "name": "Integrated Postsecondary Education Data System (IPEDS), U.S. Department of Education"},
    {"label": "Athletics", "name": "Equity in Athletics Disclosure Act (EADA), U.S. Department of Education"}
  ],
  "why_mix_paragraph": "__FILL_IN__: ~3-sentence explanation of WHY brand gravity matters for a college decision. Emphasize the three signals (endowment, marketing, athletics), the MAX-then-MEAN blend, and per-student normalization. Do NOT include the X/10 score."
}"""


def _aura_explain_appendix_json(career: CareerOutcome, *, home_state: str | None = None) -> str:
    return f"""

EXPLAIN-THIS-STAT (AURA) — JSON-MODE OUTPUT REQUIRED

The student tapped 'Explain this to me' on their Brand Gravity score.
You will produce a single JSON object matching the structure shown in
the TEMPLATE below. Do not write any text outside the JSON object.

REQUIRED TOOL CALL — call on your first turn:

  • get_institution_aura(unitid={career.unitid})
    Pull the school's AURA score details, basis, and signal values.

After the tool call returns, emit the JSON receipt.

VOICE — Brand Gravity measures how much weight the school's name
carries. Three signals, all measured per student so big and small
schools are on the same scale: endowment per full-time student (how
much money the school has invested per kid), marketing reach per
student, and athletic spending per student. The MAX rewards being elite
at any one (Stanford has the endowment; Notre Dame has the football);
the MEAN keeps it balanced. Final score gets stretched to a 1–10 scale.

VOICE-RULE SCOPING (this turn only):
  • LIFTED for the `anchor_text` JSON field: describe the school's
    institutional signals plainly (e.g., the school's per-student
    endowment, marketing reach, and athletic spending).
  • RETAINED for the prose JSON fields `one_liner`,
    `components[*].explainer`, and `why_mix_paragraph`: do NOT write
    'N/10', 'your score is N', or any numeric score reference.

Do NOT include a `score_provenance` field in your output. The server
stamps this field — your job is the prose voice; the basis label is
server-controlled.

TEMPLATE (replace every `__FILL_IN__` string with your written content):

{_AURA_RECEIPT_JSON_TEMPLATE}

CRITICAL — SENTINEL HANDLING. The strings `__FILL_IN__`, `[FILL_IN]`,
`<FILL_IN>`, `ONE-SENTENCE DEFINITION HERE`, and `PLACEHOLDER` are
placeholders ONLY — they MUST be replaced with your actual content.
Echoing them back verbatim will fail validation and the receipt will
not render. Write real prose in every prose field.

Do NOT include `[helper: ...]` blocks, `<thinking>...</thinking>` blocks,
or any meta-commentary.
"""


def _aura_explain_appendix_markdown(career: CareerOutcome, *, home_state: str | None = None) -> str:
    return f"""

EXPLAIN-THIS-STAT MODE — AURA (markdown fallback)

The structured-JSON path failed validation; produce the markdown
fallback.

The cached tool values are already injected into the user message —
do NOT re-call get_institution_aura.

REQUIRED RESPONSE STRUCTURE — exactly four sections in this order:

### Brand Gravity — <SCORE>/10

**The one-liner.** One sentence naming what the score measures.

**How it works.**
  - **100% — your school's brand gravity.**
    {career.institution_name}'s per-student endowment, marketing reach, and
    athletic spending combined into one composite signal.

  Math: composite <value> → AURA score <SCORE>/10.

**Where the data comes from.**
  - Endowment + marketing: Integrated Postsecondary Education Data
    System (IPEDS), U.S. Department of Education.
  - Athletics: Equity in Athletics Disclosure Act (EADA), U.S.
    Department of Education.

**Why we use this number.** A ~3-sentence explanation of brand gravity.
"""


def _render_math_line_aura(
    *,
    aura_score_continuous: float | None,
    build_score: int,
    score_max: int,
    signal_count: int | None = None,
) -> str:
    blend = (
        f"MAX-MEAN blend of {signal_count} signal{'s' if signal_count != 1 else ''}"
        if signal_count
        else "institutional signals"
    )
    if aura_score_continuous is not None:
        return (
            f"{blend} → composite {aura_score_continuous:.2f} → AURA score "
            f"{build_score}/{score_max}"
        )
    return f"{blend} → AURA score {build_score}/{score_max}"


def _extract_aura_tool_data(
    tool_call_log: list[gemma_client.ToolCallTurn],
) -> dict | None:
    for turn in tool_call_log:
        if turn.error or turn.tool_name != "get_institution_aura":
            continue
        result_json = turn.tool_result_full or turn.tool_result_preview
        try:
            preview = json.loads(result_json)
        except (json.JSONDecodeError, ValueError):
            continue
        row = preview.get("data") if isinstance(preview, dict) else None
        if isinstance(row, dict):
            return row
    return None


def _build_aura_evidence_bullets(
    tool_data: dict | None,
    basis: str | None,
) -> list[str] | None:
    if tool_data is None or basis is None:
        return None
    signal_keys = _AURA_BASIS_SIGNALS.get(basis)
    if signal_keys is None:
        return None

    bullets: list[str] = []
    for key in signal_keys:
        defn = _AURA_SIGNAL_DEFINITIONS.get(key)
        if defn is None:
            continue
        display_name, description = defn
        value = tool_data.get(key)
        if value is None or not isinstance(value, (int, float)):
            continue
        if key == "marketing_ratio":
            val_str = f"{value:.3f} ratio"
        else:
            val_str = f"${int(value):,}/student"
        bullets.append(f"{display_name}: {val_str} — {description}")

    return bullets if bullets else None


def _postprocess_aura_explain_receipt(
    raw: str,
    build: Build,
    tool_call_log: list[gemma_client.ToolCallTurn],
    backend: str,
) -> ExplainStatReceipt | None:
    """AURA-specific 10-step pipeline."""
    json_prefix = raw[:500] if raw else ""
    build_id = build.build_id
    call_site = "explain_aura_receipt"

    candidates = gemma_client._extract_json_objects(raw or "")
    parsed: dict[str, Any] | None = next(
        (c for c in candidates if isinstance(c, dict)), None
    )
    if parsed is None:
        _log_receipt_parse(
            call_site=call_site, parse_success=False,
            failure_reason="json_decode", json_prefix=json_prefix,
            build_id=build_id, backend=backend,
        )
        return None

    for comp in parsed.get("components", []):
        if isinstance(comp, dict):
            comp["value_pct"] = None

    try:
        receipt = ExplainStatReceipt.model_validate(parsed)
    except ValidationError as exc:
        reason = "pydantic_validation"
        if "unreplaced template sentinel" in str(exc):
            reason = "sentinel_passthrough"
        _log_receipt_parse(
            call_site=call_site, parse_success=False,
            failure_reason=reason, json_prefix=json_prefix,
            build_id=build_id, backend=backend,
        )
        return None

    if receipt.stat_code != "AURA":
        _log_receipt_parse(
            call_site=call_site, parse_success=False,
            failure_reason="stat_code_mismatch", json_prefix=json_prefix,
            build_id=build_id, backend=backend,
        )
        return None

    build_score = build.career.stats.aura
    if build_score is None:
        _log_receipt_parse(
            call_site=call_site, parse_success=False,
            failure_reason="score_null", json_prefix=json_prefix,
            build_id=build_id, backend=backend,
        )
        return None

    receipt.score = build_score
    receipt.score_max = 10

    # Server-stamp score_provenance from the build's aura_score_basis.
    basis = build.career.aura_score_basis
    if basis is not None:
        receipt.score_provenance = _humanize_basis(basis)
    else:
        receipt.score_provenance = None

    # Extract tool data for math line and evidence bullets.
    tool_data = _extract_aura_tool_data(tool_call_log)
    aura_score_continuous: float | None = None
    if tool_data is not None:
        raw_continuous = tool_data.get("aura_score_continuous")
        if isinstance(raw_continuous, (int, float)):
            aura_score_continuous = float(raw_continuous)

    signal_keys = _AURA_BASIS_SIGNALS.get(basis or "") or []
    receipt.math_line = _render_math_line_aura(
        aura_score_continuous=aura_score_continuous,
        build_score=build_score,
        score_max=receipt.score_max,
        signal_count=len(signal_keys) if signal_keys else None,
    )

    for comp in receipt.components:
        canonical, was_normalized = _normalize_label(
            comp.weight_pct, comp.label, _AURA_LABEL_ALLOWLIST
        )
        if was_normalized:
            logger.warning(
                "aura_explain_receipt: label normalized weight=%d "
                "gemma=%r canonical=%r",
                comp.weight_pct, comp.label, canonical,
            )
            comp.label = canonical

    for comp in receipt.components:
        if comp.weight_pct == 100:
            comp.value_pct = None
            comp.anchor_dollars = None
            comp.missing_reason = None
            comp.evidence_bullets = _build_aura_evidence_bullets(
                tool_data, basis,
            )

    receipt.sources = list(_AURA_RECEIPT_SOURCES)
    receipt.scoring_scale = _AURA_SCORING_SCALE

    _log_receipt_parse(
        call_site=call_site, parse_success=True,
        failure_reason=None, json_prefix=json_prefix,
        build_id=build_id, backend=backend,
    )
    return receipt


# ---------------------------------------------------------------------------
# Explain-stat registry (Decision 1 of feature-explain-stat-receipt-roi-res-grw)
# ---------------------------------------------------------------------------

_PostprocessFn = Callable[
    [str, Build, list[gemma_client.ToolCallTurn], str],
    ExplainStatReceipt | None,
]
# Callable signature includes the keyword-only ``home_state`` so the ROI
# appendix can pass the user's home state through to Gemma's tool call,
# enabling residency-aware ROI in the receipt (spec roi-net-lifetime-value
# Decision #11 followup). Stats that don't need home_state accept the kwarg
# and ignore it.
class _AppendixJsonFn(Protocol):
    def __call__(
        self, career: CareerOutcome, *, home_state: str | None = None
    ) -> str: ...


class _AppendixMarkdownFn(Protocol):
    def __call__(
        self, career: CareerOutcome, *, home_state: str | None = None
    ) -> str: ...


@dataclass(frozen=True)
class _StatExplainConfig:
    """Per-stat dispatch config for the explain-receipt JSON path."""
    stat_code: Literal["ERN", "ROI", "RES", "GRW", "AURA"]
    appendix_json_fn: _AppendixJsonFn
    appendix_markdown_fn: _AppendixMarkdownFn
    label_allowlist: dict[int, str] | list[tuple[int, str]]
    postprocessor: _PostprocessFn
    log_call_site: str
    user_prompt: str
    missing_score_one_liner: str
    missing_score_why_mix: str


_ROI_EXPLAIN_USER_PROMPT = (
    "Explain my Return on Investment score with the receipts. Show me the "
    "actual numbers behind it, not just the definition."
)
_RES_EXPLAIN_USER_PROMPT = (
    "Explain my AI Resilience score with the receipts. Show me the actual "
    "numbers behind it, not just the definition."
)
_GRW_EXPLAIN_USER_PROMPT = (
    "Explain my Growth Outlook score with the receipts. Show me the actual "
    "numbers behind it, not just the definition."
)


_STAT_EXPLAIN_REGISTRY: dict[str, _StatExplainConfig] = {
    "ERN": _StatExplainConfig(
        stat_code="ERN",
        appendix_json_fn=_ern_explain_appendix_json,
        appendix_markdown_fn=_ern_explain_appendix,
        label_allowlist=_ERN_LABEL_ALLOWLIST,
        postprocessor=_postprocess_ern_explain_receipt,
        log_call_site="explain_ern_receipt",
        user_prompt=_ERN_EXPLAIN_USER_PROMPT,
        missing_score_one_liner=_ERN_ONE_LINER,
        missing_score_why_mix=_ERN_WHY_MIX_PARAGRAPH,
    ),
    "ROI": _StatExplainConfig(
        stat_code="ROI",
        appendix_json_fn=_roi_explain_appendix_json,
        appendix_markdown_fn=_roi_explain_appendix_markdown,
        label_allowlist=_ROI_LABEL_ALLOWLIST,
        postprocessor=_postprocess_roi_explain_receipt,
        log_call_site="explain_roi_receipt",
        user_prompt=_ROI_EXPLAIN_USER_PROMPT,
        missing_score_one_liner=_ROI_ONE_LINER,
        missing_score_why_mix=_ROI_WHY_MIX_PARAGRAPH,
    ),
    "RES": _StatExplainConfig(
        stat_code="RES",
        appendix_json_fn=_res_explain_appendix_json,
        appendix_markdown_fn=_res_explain_appendix_markdown,
        label_allowlist=_RES_LABEL_ALLOWLIST,
        postprocessor=_postprocess_res_explain_receipt,
        log_call_site="explain_res_receipt",
        user_prompt=_RES_EXPLAIN_USER_PROMPT,
        missing_score_one_liner=_RES_ONE_LINER,
        missing_score_why_mix=_RES_WHY_MIX_PARAGRAPH,
    ),
    "GRW": _StatExplainConfig(
        stat_code="GRW",
        appendix_json_fn=_grw_explain_appendix_json,
        appendix_markdown_fn=_grw_explain_appendix_markdown,
        label_allowlist=_GRW_LABEL_ALLOWLIST,
        postprocessor=_postprocess_grw_explain_receipt,
        log_call_site="explain_grw_receipt",
        user_prompt=_GRW_EXPLAIN_USER_PROMPT,
        missing_score_one_liner=_GRW_ONE_LINER,
        missing_score_why_mix=_GRW_WHY_MIX_PARAGRAPH,
    ),
    "AURA": _StatExplainConfig(
        stat_code="AURA",
        appendix_json_fn=_aura_explain_appendix_json,
        appendix_markdown_fn=_aura_explain_appendix_markdown,
        label_allowlist=_AURA_LABEL_ALLOWLIST,
        postprocessor=_postprocess_aura_explain_receipt,
        log_call_site="explain_aura_receipt",
        user_prompt=_AURA_EXPLAIN_USER_PROMPT,
        missing_score_one_liner=_AURA_ONE_LINER,
        missing_score_why_mix=_AURA_WHY_MIX_PARAGRAPH,
    ),
}


def _current_backend() -> str:
    """Return the active inference backend label for log records."""
    try:
        _client, config = gemma_client._cached_client()
        return str(config.backend)
    except Exception:
        return "unknown"


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

    NOTE: Unlike the streaming intent, guidance, and boss-narrative
    surfaces, this surface intentionally preserves markdown. The
    frontend ``ChatMessage.tsx`` renders chat replies through
    ``react-markdown`` with an allowlist (p/strong/em/ul/ol/li/links/
    inline-code), so bold and lists are part of the contract.
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
        context_block = await _context_for_branch(builds[0], scope.target_id)
    elif scope.kind == "career":
        assert scope.target_id is not None
        context_block = _context_for_career(scope.target_id)
    else:  # compare
        context_block = _context_for_compare(builds)

    # Assemble the full system prompt. Branch and compare scopes append
    # voice appendixes to keep the shared voice rules untouched.
    lang_block = gemma_language_instruction(norm_locale)
    if scope.kind == "branch":
        system_base = _SYSTEM_BASE + _BRANCH_VOICE_APPENDIX
    elif scope.kind == "compare":
        system_base = _SYSTEM_BASE + _COMPARE_VOICE_APPENDIX
    else:
        system_base = _SYSTEM_BASE
    system = f"{system_base}\n\n{lang_block}\n\n{context_block}"

    # Explain-this-stat dispatch via registry. Matches sentinels like
    # "[explain-this:ERN]", "[explain-this:ROI]", etc.
    explain_config: _StatExplainConfig | None = None
    if scope.kind == "stat" and scope.target_id is not None:
        m = _EXPLAIN_SENTINEL_RE.match(message.strip())
        if m:
            stat_key = m.group(1)
            explain_config = _STAT_EXPLAIN_REGISTRY.get(stat_key)

    if explain_config is not None:
        # ERN score-null path: server-built receipt, no Gemma call.
        # Score-null server-built receipt: only ERN for now.
        # ROI/RES/GRW fall through to Gemma markdown path when score is null.
        if explain_config.stat_code == "ERN":
            if _get_build_stat(builds[0], "ERN") is None:
                missing_receipt, missing_log = (
                    await _ern_missing_score_receipt_path(builds[0])
                )
                missing_tool_calls = [
                    TraceEventPayload(
                        turn=t.dispatch_index,
                        tool=t.tool_name,
                        args=t.tool_args,
                        result_preview=t.tool_result_preview,
                        duration_ms=t.duration_ms,
                        error=t.error,
                    )
                    for t in missing_log
                ]
                return AskResponse(
                    response=missing_receipt, tool_calls=missing_tool_calls
                )
        else:
            stat_val = _get_build_stat(
                builds[0], explain_config.stat_code
            )
            if stat_val is None:
                logger.info(
                    "%s_explain_receipt: score is null, falling back to "
                    "markdown path",
                    explain_config.stat_code.lower(),
                )
        system = system + explain_config.appendix_json_fn(builds[0].career, home_state=builds[0].home_state)

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
        return AskResponse(
            response=_strip_thinking_prefix(text), tool_calls=[]
        )

    # Fold history into the user message. ``generate_with_tools_loop``
    # accepts a single user string; multi-turn fidelity for tool-loop
    # callers is a future enhancement (see spec §2 Out of Scope).
    user_msg = (
        explain_config.user_prompt
        if explain_config is not None
        else _fold_history(history, message)
    )

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
        "explain_stat": explain_config.stat_code if explain_config else None,
    }

    text, tool_call_log = await gemma_client.generate_with_tools_loop(
        system=system,
        user=user_msg,
        tools=tool_schemas,
        dispatch=_dispatch,
        max_turns=5,
        max_wall_time_s=45.0,
        temperature=_EXPLAIN_TEMPERATURE if explain_config else _TEMPERATURE,
        max_tokens=_EXPLAIN_MAX_TOKENS if explain_config else 1200,
        extra=extra,
        final_turn_response_format=(
            _EXPLAIN_RESPONSE_FORMAT if explain_config else None
        ),
    )

    # Explain-receipt post-processing via registry. On success the
    # receipt is the response payload; on failure we re-run the loop
    # ONCE with the markdown appendix and cached tool values (no MCP
    # re-fetch).
    if explain_config is not None and text:
        receipt = explain_config.postprocessor(
            text,
            builds[0],
            tool_call_log,
            _current_backend(),
        )
        if receipt is not None:
            tool_calls = [
                TraceEventPayload(
                    turn=t.dispatch_index,
                    tool=t.tool_name,
                    args=t.tool_args,
                    result_preview=t.tool_result_preview,
                    duration_ms=t.duration_ms,
                    error=t.error,
                )
                for t in tool_call_log
            ]
            return AskResponse(response=receipt, tool_calls=tool_calls)
        # JSON parse failed → markdown fallback retry with cached values.
        logger.warning(
            "%s: JSON parse failed; retrying with markdown appendix "
            "+ cached tool values",
            explain_config.log_call_site,
        )
        markdown_system = (
            f"{system_base}\n\n{lang_block}\n\n{context_block}"
            + explain_config.appendix_markdown_fn(builds[0].career, home_state=builds[0].home_state)
        )
        cached_values_block = _format_cached_tool_values_generic(
            tool_call_log
        )
        markdown_user = (
            f"{cached_values_block}\n\n{explain_config.user_prompt}"
        )
        text, fallback_tool_log = await gemma_client.generate_with_tools_loop(
            system=markdown_system,
            user=markdown_user,
            tools=[],
            dispatch=_dispatch,
            max_turns=2,
            max_wall_time_s=30.0,
            temperature=_EXPLAIN_TEMPERATURE,
            max_tokens=_EXPLAIN_MAX_TOKENS,
            extra={**extra, "fallback_after_json_parse_failure": True},
        )

    if not text:
        logger.warning(
            "ask_gemma %s scope: empty text from tool loop, using fallback",
            scope.kind,
        )
        text = fallback_text("chat_unavailable", norm_locale)

    # Surface tool-call telemetry on AskResponse for the routing/E2E
    # test AND for <GemmaTrace>'s post-hoc fallback render — when SSE
    # is unavailable, the frontend reads this list and synthesizes
    # turn_start + turn_complete events from it (feature-gemma-trace.md
    # §4 Service Changes). The ``turn`` field carries the per-dispatch
    # monotonic ``dispatch_index`` so live and post-hoc feeds use the
    # same row-correlation key.
    tool_calls = [
        TraceEventPayload(
            turn=tc.dispatch_index,
            tool=tc.tool_name,
            args=tc.tool_args,
            result_preview=tc.tool_result_preview,
            duration_ms=tc.duration_ms,
            error=tc.error,
        )
        for tc in tool_call_log
    ]
    return AskResponse(
        response=_strip_thinking_prefix(text), tool_calls=tool_calls
    )


async def _dispatch(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Trivial passthrough to MCP. Notably does NOT inject
    ``student_cip`` the way ``set_your_course.py`` does — Ask Gemma
    answers questions, it does not resolve the student's CIP."""
    return await mcp_client.call_async(name, args)


# Chain-of-thought prefix tokens Gemma 4 occasionally emits despite the
# system prompt's "never write your reasoning" clause. Small list of
# observed prefixes; strip them defensively at the boundary so the
# student never sees `thought\n` or similar bleed into the answer.
_THINKING_PREFIXES: tuple[str, ...] = (
    "thought\n",
    "thinking\n",
    "reasoning\n",
    "let me think\n",
)


_HELPER_LEAK_RE = re.compile(r"\A\s*\[helper:.*?\]\s*", re.DOTALL)

# Gemma 4 occasionally hallucinates a stray HTML/XML tag at the start of
# its answer (most often ``</div>``, sometimes ``<p>`` or ``</p>``). The
# downstream Markdown renderer escapes these to literal text, so the
# student sees raw "</div>" before the prose. Strip leading tags
# defensively at the boundary. Conservative pattern: anchored to start,
# matches a single tag of letters-only (no attributes, no content), with
# optional surrounding whitespace. Loops to handle a stack of stray tags.
_LEADING_HTML_TAG_RE = re.compile(r"\A\s*</?[a-zA-Z][a-zA-Z0-9]*\s*/?>\s*")


def _strip_thinking_prefix(text: str) -> str:
    """Strip any chain-of-thought marker token Gemma may have emitted
    at the start of the response. Idempotent. Conservative — only
    matches known prefixes against the *start* of the text after
    light whitespace stripping; never touches the body of the answer.

    Also strips any leading ``[helper: ...]`` scratchpad block(s) Gemma
    occasionally leaks despite the system prompt's "never reproduce
    helper annotations" clause, plus any leading stray HTML/XML tag
    Gemma occasionally hallucinates. Multi-line; loops in case Gemma
    emits more than one consecutive block. Anchored to the start, so
    helper-bracketed text or HTML appearing inside the body of the
    answer (rare but possible) is left alone.
    """
    if not text:
        return text
    while True:
        m = _HELPER_LEAK_RE.match(text)
        if m:
            text = text[m.end():]
            continue
        m = _LEADING_HTML_TAG_RE.match(text)
        if m:
            text = text[m.end():]
            continue
        break
    stripped = text.lstrip()
    lowered = stripped.lower()
    for prefix in _THINKING_PREFIXES:
        if lowered.startswith(prefix):
            return stripped[len(prefix):].lstrip()
    return text


# ---------------------------------------------------------------------------
# Streaming variant — POST /chat/ask/stream
# ---------------------------------------------------------------------------

# Bounded queue size for the per-request trace event channel
# (Decision #14). Worst-case event count per chat turn is
# max_turns(3) * max_tools_per_turn(~5) * 2 events (start + complete)
# = ~30. 256 is ~8x headroom; the bound is documented and not reachable
# under the configured loop limits — but bounded prevents accidental
# unbounded growth if a future loop change ever changes the bound.
_TRACE_QUEUE_MAXSIZE = 256

# Polling interval used to interleave queue draining with loop_task
# completion checks. Short enough to feel live; long enough to not
# burn CPU. Matches the cadence of the build SSE stream's drain loop.
_TRACE_DRAIN_POLL_S = 0.05


async def chat_ask_stream(
    *,
    scope: AskScope,
    builds: list[Build],
    message: str,
    history: list[dict[str, Any]],
    locale: AppLocale | None,
) -> AsyncIterator[TraceEvent]:
    """Streaming variant of ``chat_ask``.

    Yields ``TraceEvent`` objects in order: zero or more
    ``(turn_start, turn_complete)`` pairs, exactly one ``final_text``,
    exactly one ``done``.

    Failure modes — all converge on a graceful ``final_text`` carrying
    the localized ``chat_unavailable`` fallback string + a ``done``
    trailer. Generator NEVER raises past its boundary (Decision: C3).

    Cancellation — when the SSE client disconnects, FastAPI calls
    ``aclose()`` on this generator. The ``try/finally`` block cancels
    the in-flight Gemma loop_task and awaits its completion so the
    Gemma semaphore is released within ~100ms rather than after the
    wall-time cap (Decision: C4).
    """
    norm_locale = normalize_locale(locale)

    # Branch-scope opener path (no tool loop, no trace events) —
    # mirrors chat_ask. Yields only final_text + done.
    if scope.kind == "branch" and not history:
        text = await _branch_opener_text(scope, builds, norm_locale)
        yield TraceFinalText(response=_strip_thinking_prefix(text))
        yield TraceDone()
        return

    # Build context block per scope kind. Mirrors chat_ask exactly.
    context_block = await _build_context_block(scope, builds)

    # Assemble system prompt (branch/compare scopes add appendixes).
    lang_block = gemma_language_instruction(norm_locale)
    if scope.kind == "branch":
        system_base = _SYSTEM_BASE + _BRANCH_VOICE_APPENDIX
    elif scope.kind == "compare":
        system_base = _SYSTEM_BASE + _COMPARE_VOICE_APPENDIX
    else:
        system_base = _SYSTEM_BASE
    system = f"{system_base}\n\n{lang_block}\n\n{context_block}"

    # Explain-this-stat dispatch via registry (mirrors chat_ask).
    explain_config: _StatExplainConfig | None = None
    if scope.kind == "stat" and scope.target_id is not None:
        m = _EXPLAIN_SENTINEL_RE.match(message.strip())
        if m:
            stat_key = m.group(1)
            explain_config = _STAT_EXPLAIN_REGISTRY.get(stat_key)

    if explain_config is not None:
        # ERN score-null path (mirror of chat_ask).
        if explain_config.stat_code == "ERN":
            if _get_build_stat(builds[0], "ERN") is None:
                missing_receipt, missing_log = (
                    await _ern_missing_score_receipt_path(builds[0])
                )
                for turn in missing_log:
                    yield TraceTurnStart(
                        turn=turn.dispatch_index,
                        tool=turn.tool_name,
                        args=turn.tool_args,
                    )
                    yield TraceTurnComplete(
                        turn=turn.dispatch_index,
                        tool=turn.tool_name,
                        args=turn.tool_args,
                        result_preview=turn.tool_result_preview,
                        duration_ms=turn.duration_ms,
                        error=turn.error,
                    )
                yield TraceFinalText(response=missing_receipt)
                yield TraceDone()
                return
        system = system + explain_config.appendix_json_fn(builds[0].career, home_state=builds[0].home_state)

    # Fold history into the user message.
    user_msg = (
        explain_config.user_prompt
        if explain_config is not None
        else _fold_history(history, message)
    )

    # Load tool schemas. Skip any tool the MCP server doesn't publish.
    tool_schemas: list[dict[str, Any]] = []
    for tool_name in _TOOLS:
        schema = mcp_client.get_tool_openai_schema(tool_name)
        if schema is not None:
            tool_schemas.append(schema)

    extra = {
        "call_site": f"ask_gemma_stream_{scope.kind}",
        "scope_target_id": scope.target_id,
        "scope_build_count": len(scope.build_ids),
        "explain_stat": explain_config.stat_code if explain_config else None,
    }

    # Per-request bounded queue. Both callbacks enqueue here; the
    # generator drains and yields events as they arrive.
    queue: asyncio.Queue[TraceEvent] = asyncio.Queue(
        maxsize=_TRACE_QUEUE_MAXSIZE
    )

    async def on_start(
        dispatch_index: int, name: str, args: dict[str, Any]
    ) -> None:
        await queue.put(
            TraceTurnStart(turn=dispatch_index, tool=name, args=args)
        )

    async def on_turn(turn: gemma_client.ToolCallTurn) -> None:
        await queue.put(
            TraceTurnComplete(
                turn=turn.dispatch_index,
                tool=turn.tool_name,
                args=turn.tool_args,
                result_preview=turn.tool_result_preview,
                duration_ms=turn.duration_ms,
                error=turn.error,
            )
        )

    loop_task: asyncio.Task[tuple[str, list[gemma_client.ToolCallTurn]]] = (
        asyncio.create_task(
            gemma_client.generate_with_tools_loop(
                system=system,
                user=user_msg,
                tools=tool_schemas,
                dispatch=_dispatch,
                max_turns=5,
                max_wall_time_s=45.0,
                temperature=(
                    _EXPLAIN_TEMPERATURE if explain_config else _TEMPERATURE
                ),
                max_tokens=(
                    _EXPLAIN_MAX_TOKENS if explain_config else 1200
                ),
                extra=extra,
                on_turn_start=on_start,
                on_turn_event=on_turn,
                final_turn_response_format=(
                    _EXPLAIN_RESPONSE_FORMAT if explain_config else None
                ),
            )
        )
    )

    text = ""
    tool_call_log: list[gemma_client.ToolCallTurn] = []
    fallback_task: asyncio.Task[
        tuple[str, list[gemma_client.ToolCallTurn]]
    ] | None = None
    try:
        while not loop_task.done() or not queue.empty():
            try:
                ev = await asyncio.wait_for(
                    queue.get(), timeout=_TRACE_DRAIN_POLL_S
                )
                yield ev
            except asyncio.TimeoutError:
                continue

        try:
            text, tool_call_log = await loop_task
        except Exception as exc:  # noqa: BLE001 — boundary defense
            logger.warning("chat_ask_stream: loop_task raised — %s", exc)
            text = ""
            tool_call_log = []

        # Explain-receipt post-processing via registry.
        if explain_config is not None and text:
            receipt = explain_config.postprocessor(
                text,
                builds[0],
                tool_call_log,
                _current_backend(),
            )
            if receipt is not None:
                yield TraceFinalText(response=receipt)
                yield TraceDone()
                return
            logger.warning(
                "%s: JSON parse failed; retrying with markdown "
                "appendix + cached tool values",
                explain_config.log_call_site,
            )
            markdown_system = (
                f"{system_base}\n\n{lang_block}\n\n{context_block}"
                + explain_config.appendix_markdown_fn(builds[0].career, home_state=builds[0].home_state)
            )
            cached_values_block = _format_cached_tool_values_generic(
                tool_call_log
            )
            markdown_user = (
                f"{cached_values_block}\n\n{explain_config.user_prompt}"
            )
            fallback_task = asyncio.create_task(
                gemma_client.generate_with_tools_loop(
                    system=markdown_system,
                    user=markdown_user,
                    tools=[],
                    dispatch=_dispatch,
                    max_turns=2,
                    max_wall_time_s=30.0,
                    temperature=_EXPLAIN_TEMPERATURE,
                    max_tokens=_EXPLAIN_MAX_TOKENS,
                    extra={
                        **extra,
                        "fallback_after_json_parse_failure": True,
                    },
                )
            )
            try:
                text, _ = await fallback_task
            except Exception as exc:  # noqa: BLE001 — boundary defense
                logger.warning(
                    "%s fallback failed: %s",
                    explain_config.log_call_site, exc,
                )
                text = ""

        if not text:
            text = fallback_text("chat_unavailable", norm_locale)

        yield TraceFinalText(response=_strip_thinking_prefix(text))
        yield TraceDone()
    finally:
        # Client disconnect path. If the SSE consumer aborts mid-
        # stream, FastAPI calls aclose() on this generator, which
        # raises GeneratorExit at the active `yield ev` and bypasses
        # the try-block exit. The finally cancels loop_task and the
        # explain-receipt fallback_task (when in-flight) so both
        # Gemma calls release their semaphore immediately rather
        # than after the wall-time cap (≤30s).
        pending: list[asyncio.Task[Any]] = []
        if not loop_task.done():
            loop_task.cancel()
            pending.append(loop_task)
        if fallback_task is not None and not fallback_task.done():
            fallback_task.cancel()
            pending.append(fallback_task)
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)


async def _branch_opener_text(
    scope: AskScope,
    builds_in_scope: list[Build],
    norm_locale: AppLocale,
) -> str:
    """Branch opener path — extracted from chat_ask so chat_ask_stream
    can reuse the same logic. Tools are disabled for the opener; the
    context block has every numeric driver needed."""
    assert scope.target_id is not None  # branch scope validator guarantees
    context_block = await _context_for_branch(
        builds_in_scope[0], scope.target_id
    )
    lang_block = gemma_language_instruction(norm_locale)
    system_base = f"{_SYSTEM_BASE}{_BRANCH_VOICE_APPENDIX}"
    system = f"{system_base}\n\n{lang_block}\n\n{context_block}"
    opener_user = (
        _OPENER_PROMPT
        if scope.target_id == builds_in_scope[0].career.soc_code
        else _OPENER_PROMPT_BRANCH
    )
    text = await gemma_client.generate_async(
        system=system,
        user=opener_user,
        max_tokens=400,
        temperature=_TEMPERATURE,
        extra={
            "call_site": "ask_gemma_stream_branch_opener",
            "scope_target_id": scope.target_id,
        },
    )
    if not text:
        logger.warning(
            "ask_gemma stream branch opener: empty text, using fallback"
        )
        text = fallback_text("chat_unavailable", norm_locale)
    return text


async def _build_context_block(
    scope: AskScope, builds_in_scope: list[Build]
) -> str:
    """Dispatch to the right per-scope context-builder. Extracted so
    chat_ask and chat_ask_stream share one implementation."""
    if scope.kind == "stat":
        assert scope.target_id is not None
        return _context_for_stat(builds_in_scope[0], scope.target_id)
    if scope.kind == "boss":
        assert scope.target_id is not None
        return _context_for_boss(builds_in_scope[0], scope.target_id)
    if scope.kind == "skill":
        assert scope.target_id is not None
        return _context_for_skill(builds_in_scope[0], scope.target_id)
    if scope.kind == "build":
        return _context_for_build(builds_in_scope[0])
    if scope.kind == "branch":
        assert scope.target_id is not None
        return await _context_for_branch(builds_in_scope[0], scope.target_id)
    if scope.kind == "career":
        assert scope.target_id is not None
        return _context_for_career(scope.target_id)
    return _context_for_compare(builds_in_scope)


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
        if career.cost_of_attendance_annual is not None:
            lines.append(
                f"- Sticker cost of attendance per year (before aid): "
                f"{fmt_dollars(career.cost_of_attendance_annual)}"
            )
        if career.net_price_annual is not None:
            lines.append(
                f"- Average net price per year after grants/scholarships "
                f"(aid context only, NOT the scoring basis): "
                f"{fmt_dollars(career.net_price_annual)}"
            )
        if career.earnings_1yr_median is not None:
            lines.append(
                f"- Starting median earnings (year 1): "
                f"{fmt_dollars(career.earnings_1yr_median)}"
            )
        # Intentionally NOT precomputing the residency-aware
        # published_cost_4yr, the projected 15-year cumulative earnings,
        # or the payback multiplier here. The student tapped "Explain
        # this to me" to see the model use a tool — `get_career_paths`
        # returns those values residency-aware (when home_state is
        # passed) so Gemma quotes verifiable, single-source numbers
        # rather than recomputing in prose.
        lines.append(
            "- This stat is financing-agnostic by design — the loan slider "
            "does NOT move it. Modeled debt and the financed debt-to-earnings "
            "ratio belong to the Student Loans Boss."
        )
        lines.append(
            "- The stat does NOT model career progression. It captures what "
            "the *program* delivers (the first job, per College Scorecard "
            "earnings_1yr_median); years 2-15 are projected at flat 3% "
            "growth, no occupation-specific curve."
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

    elif stat_code == "AURA":
        lines.append("")
        lines.append("Brand Gravity drivers (translate into plain English):")
        basis = career.aura_score_basis
        if basis:
            lines.append(
                "- Composite basis (raw enum, do NOT echo): "
                + _helper(f"aura_score_basis = {basis}")
            )
        version = career.aura_score_version
        if version:
            lines.append(_helper(f"aura_score_version = {version}"))
        if career.stats.aura is None:
            lines.append(
                "- No institutional brand-gravity data is available "
                "for this school yet — the pentagon renders this slot "
                "as an em-dash. Acknowledge the missing data honestly "
                "instead of guessing a number."
            )
        else:
            lines.append(
                "- Institution-level signal: blends endowment per "
                "student, marketing reach, and athletic spending into "
                "a single 1-10 score. Higher means the school carries "
                "more weight beyond classroom outcomes."
            )

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
        # ``"raw stat_res 4 + stat_hmn 5 = 9"``). It contains stat
        # codes, so it MUST live inside a [helper: ...] span — Gemma
        # reads it for math but the system prompt instructs her never
        # to echo helper spans verbatim.
        lines.append("")
        lines.append(_helper(f"reason summary = {fight.reason}"))

    if boss_id == "ai":
        if career.raw_stat_res is not None:
            lines.append(_helper(
                f"raw stat_res (AI exposure resilience input) = "
                f"{career.raw_stat_res}/10"
            ))
        if career.raw_stat_hmn is not None:
            lines.append(_helper(
                f"raw stat_hmn (O*NET human-essential input) = "
                f"{career.raw_stat_hmn}/10"
            ))
        if career.stats.res is not None:
            lines.append(_helper(
                f"display blended RES = {career.stats.res}/10 "
                f"(50/50 mean of the two raw inputs above; not used "
                f"for the fight score)"
            ))
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
        # Burnout no longer reads HMN (RES absorbed it). Surface AURA
        # for institutional context — students at higher-resourced
        # institutions often have richer support infrastructure.
        if career.stats.aura is not None:
            lines.append(_helper(f"Brand Gravity score = {career.stats.aura}/10"))
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
    if skill.delta_loans_raw:
        sign = "+" if skill.delta_loans_raw > 0 else ""
        raw_parts.append(f"Student Loans raw score {sign}{skill.delta_loans_raw}")
    if raw_parts:
        lines.append(_helper("raw-score deltas if applied: " + "; ".join(raw_parts)))

    # Current stats (so Gemma can reason about post-application values)
    lines.append("")
    lines.append("Current build stats (translate into plain English):")
    for stat_code in ("ERN", "ROI", "RES", "GRW", "AURA"):
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
    ]

    # Tool-call codes — surfaced as helper-bracketed identifiers so
    # Gemma can pass them to tools (get_schools_for_career,
    # get_occupation_data, get_career_branches, etc.) without first
    # firing get_career_paths to rediscover what's already loaded.
    lines.append("Identifiers for tool calls (pass these to tools when needed):")
    lines.append(_helper(f"unitid = {career.unitid}"))
    lines.append(_helper(f"cipcode = {career.cipcode}"))
    lines.append(_helper(f"soc_code = {career.soc_code}"))

    lines.append("")
    lines.append("Pentagon stats (translate into plain English):")
    for stat_code in ("ERN", "ROI", "RES", "GRW", "AURA"):
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
    if career.published_cost_4yr is not None:
        lines.append(
            f"- Published 4-year cost used for ROI and modeled debt: "
            f"{fmt_dollars(career.published_cost_4yr)}"
        )
    if career.net_price_annual is not None:
        lines.append(
            f"- Average net price per year after aid (context only): "
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

    # Residency + tuition detail. Critical for honest school-comparison
    # answers — a leaderboard's "average net price" is school-wide and
    # not residency-aware, so an OOS student comparing their personal
    # OOS-aid-adjusted cost to a peer school's school-wide average will
    # mislead. Expose the underlying tuition figures + the residency
    # flag so Gemma can frame the comparison honestly.
    lines.append("")
    lines.append("School cost detail and student's residency:")
    if career.institution_control:
        lines.append(f"- Institution type: {career.institution_control}")
    if career.is_out_of_state:
        lines.append(
            "- The student is paying OUT-OF-STATE tuition at this school."
        )
    else:
        lines.append(
            "- The student is paying in-state tuition at this school."
        )
    if career.tuition_in_state is not None:
        lines.append(
            f"- This school's in-state tuition: "
            f"{fmt_dollars(career.tuition_in_state)}"
        )
    if career.tuition_out_of_state is not None:
        lines.append(
            f"- This school's out-of-state tuition: "
            f"{fmt_dollars(career.tuition_out_of_state)}"
        )
    # The behavioral instruction for handling residency-aware school
    # comparisons now lives in _SYSTEM_BASE (RESIDENCY-AWARE COST
    # COMPARISONS section) rather than here, so Gemma treats it as a
    # directive she must follow rather than helper-bracketed
    # background she silently absorbs.

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


def _context_for_career(soc_code: str) -> str:
    """Career-pick scope: the student is exploring a SOC before they've
    built anything, so we have no school/program context yet.

    Hand Gemma the SOC code as a tool-callable identifier and trust the
    tool loop to fill in occupation detail (``get_occupation_data``,
    ``get_task_breakdown``, ``get_career_branches``). No synthetic
    fallback data — every concrete number Gemma cites should come from
    a real tool call so we don't lie to the student during pick.
    """
    lines: list[str] = [
        "[CONTEXT — already loaded, no tool call needed for this data]",
        "",
        "The student is exploring a career before they've built anything.",
        "There is no school or major context yet — they're deciding.",
        "",
        "Identifiers for tool calls (pass these to tools when needed):",
        _helper(f"soc_code = {soc_code}"),
        "",
        (
            "To answer well, call get_occupation_data and get_task_breakdown "
            "for this SOC to pull the day-to-day work, growth, and "
            "wage detail. If the student asks about adjacent paths, "
            "call get_career_branches. If they ask which schools "
            "produce this career, call get_schools_for_career."
        ),
    ]
    return "\n".join(lines)


async def _context_for_branch(build: Build, target_id: str) -> str:
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
        for stat_code in ("ERN", "ROI", "RES", "GRW", "AURA"):
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

    # Case 3: target_id is not on build.branches and isn't the root.
    # Hits when /future selects an L2 endpoint (branch-of-branch via
    # career_transitions, never materialized into build.branches). Try
    # an inline get_occupation_data lookup so Gemma can speak to the
    # role the student clicked on instead of refusing.
    occ_row: dict[str, Any] | None = None
    try:
        occ_result = await mcp_client.call_async(
            "get_occupation_data", {"soc_code": target_id}
        )
        candidate = occ_result.get("data") if isinstance(occ_result, dict) else None
        if isinstance(candidate, dict):
            occ_row = candidate
    except Exception:  # noqa: BLE001 — MCP outage falls through to stub
        logger.warning(
            "get_occupation_data lookup failed for %s in branch context",
            target_id,
            exc_info=True,
        )
        occ_row = None

    if occ_row is not None:
        title = occ_row.get("occupation_title") or "this role"
        lines.append(
            f'The student is asking about a downstream career, "{title}" '
            f"({target_id}), reachable as a 2-step path from their current "
            f"career, {career.occupation_title}."
        )
        lines.append(
            "It isn't a direct branch on the build; treat this as an "
            "occupation-level question."
        )

        wage = occ_row.get("median_annual_wage")
        if isinstance(wage, (int, float)):
            lines.append(f"- Median annual wage: {fmt_dollars(wage)}")
        edu_level = occ_row.get("education_level_name")
        if edu_level:
            lines.append(_helper(f"typical education required: {edu_level}"))
        growth_cat = occ_row.get("growth_category")
        if growth_cat:
            lines.append(_helper(f"BLS growth outlook: {growth_cat}"))
        change_pct = occ_row.get("employment_change_pct")
        if isinstance(change_pct, (int, float)):
            lines.append(
                _helper(
                    f"projected 10-year employment change: "
                    f"{change_pct:+.1f}%"
                )
            )
        openings = occ_row.get("openings_annual_avg")
        if isinstance(openings, (int, float)):
            lines.append(
                _helper(f"average annual openings nationwide: {int(openings):,}")
            )

        # Wage anchor for delta translation.
        if career.median_annual_wage is not None:
            lines.append("")
            lines.append(
                f"Current career wage reference: "
                f"{fmt_dollars(career.median_annual_wage)} "
                f"({career.occupation_title})"
            )

        lines.append("")
        lines.append(
            _helper(
                "this is a 2-step transition, not a direct branch — frame "
                "answers honestly about what's required to get there. If "
                "you need task-level detail, call get_task_breakdown for "
                f"SOC {target_id}."
            )
        )
        return "\n".join(lines)

    # No occupation row either — true thin-data fallback.
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
        for stat_code in ("ERN", "ROI", "RES", "GRW", "AURA"):
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
