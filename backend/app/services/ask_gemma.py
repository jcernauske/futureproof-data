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
from collections.abc import AsyncIterator
from typing import Any

from pydantic import ValidationError

from app.models.api import (
    AskResponse,
    AskScope,
    ExplainStatReceipt,
    ReceiptSource,
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
    # School-comparison leaderboard. Powers chat questions like
    # "what other schools lead to this career for less money" and
    # "which schools have the highest ROI for this career". The MCP
    # tool's own description teaches Gemma when to reach for it
    # (compare schools FOR a career, not look up programs AT one
    # school — that's get_career_paths).
    "get_schools_for_career",
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
# Explain-this-stat — ERN structured-receipt path
#   spec: docs/specs/feature-explain-stat-receipt.md (DRAFT v1.3)
#   voice authority: .claude/skills/pentagon-stat-explanation/SKILL.md
#
# Triggers only on the sentinel opener "[explain-this:ERN]" in the
# stat-scope chat. Gemma is asked to emit a JSON object matching
# ExplainStatReceipt; the server post-processes (validates, stamps
# the build's score, builds math_line, normalizes labels) before
# returning the receipt to the frontend.
#
# The original markdown spike's appendix and helper-leak stripper
# remain in this file as the JSON-parse-failure fallback. When
# _postprocess_ern_explain_receipt returns None, the loop runs once
# more with the markdown appendix, reusing the cached tool_call_log
# so no MCP re-fetch happens.
# ---------------------------------------------------------------------------

_ERN_EXPLAIN_OPENER = "[explain-this:ERN]"
_ERN_EXPLAIN_TEMPERATURE = 0.0
_ERN_EXPLAIN_MAX_TOKENS = 1500
_ERN_EXPLAIN_RESPONSE_FORMAT: dict[str, Any] = {"type": "json_object"}

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


def _ern_explain_appendix_json(career: CareerOutcome) -> str:
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


def _ern_explain_appendix(career: CareerOutcome) -> str:
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
    soc_code: str,
) -> tuple[float | None, int | None, float | None, int | None]:
    """Pull the four needed values out of the tool_call_log.

    Returns (cip_family_earnings_rank, earnings_1yr_median,
             wage_percentile_overall, median_annual_wage). Any value
    not found in the log is None.

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
            rows = preview.get("results") if isinstance(preview, dict) else None
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                if row.get("soc_code") != soc_code:
                    continue
                cip_rank = row.get("cip_family_earnings_rank")
                earn = row.get("earnings_1yr_median")
                if isinstance(earn, (int, float)):
                    earnings = int(earn)
                break
        elif turn.tool_name == "get_occupation_data":
            row = preview if isinstance(preview, dict) else None
            if row is None:
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
    cip_rank, earnings, wage_pct, wage = _extract_tool_results(
        tool_call_log, build.career.soc_code
    )
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

    # ERN explain-this-stat path. JSON-mode appendix on the first
    # attempt; markdown fallback (with cached tool values injected) on
    # parse failure. Strictly additive, ERN-only.
    explain_ern = (
        scope.kind == "stat"
        and scope.target_id == "ERN"
        and message.strip() == _ERN_EXPLAIN_OPENER
    )
    if explain_ern:
        system = system + _ern_explain_appendix_json(builds[0].career)

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
        _ERN_EXPLAIN_USER_PROMPT
        if explain_ern
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
        "explain_ern": explain_ern,
    }

    text, tool_call_log = await gemma_client.generate_with_tools_loop(
        system=system,
        user=user_msg,
        tools=tool_schemas,
        dispatch=_dispatch,
        # 5 = up to 4 tool turns + 1 synthesis turn. Pre-trace this
        # was 3 because the tool_dispatched=True short-circuit forced
        # text on turn 2; post-trace (feature-gemma-trace.md) the
        # loop chains tool calls across turns and needs an extra
        # budget slot for the final-text synthesis turn after the
        # tools are spent. The 30s wall-time cap remains the
        # load-bearing safety against runaway loops.
        max_turns=5,
        max_wall_time_s=30.0,
        temperature=_ERN_EXPLAIN_TEMPERATURE if explain_ern else _TEMPERATURE,
        max_tokens=_ERN_EXPLAIN_MAX_TOKENS if explain_ern else 1200,
        extra=extra,
        final_turn_response_format=(
            _ERN_EXPLAIN_RESPONSE_FORMAT if explain_ern else None
        ),
    )

    # ERN explain-receipt post-processing. On success the receipt is
    # the response payload; on failure we re-run the loop ONCE with
    # the markdown appendix and the cached tool values injected (no
    # MCP re-fetch).
    if explain_ern and text:
        receipt = _postprocess_ern_explain_receipt(
            raw=text,
            build=builds[0],
            tool_call_log=tool_call_log,
            backend=_current_backend(),
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
            "ern_explain_receipt: JSON parse failed; retrying with "
            "markdown appendix + cached tool values"
        )
        cip_rank, earnings, wage_pct, wage = _extract_tool_results(
            tool_call_log, builds[0].career.soc_code
        )
        cached_values_block = _format_cached_tool_values(
            cip_rank, earnings, wage_pct, wage
        )
        markdown_system = (
            f"{system_base}\n\n{lang_block}\n\n{context_block}"
            + _ern_explain_appendix(builds[0].career)
        )
        markdown_user = f"{cached_values_block}\n\n{_ERN_EXPLAIN_USER_PROMPT}"
        text, fallback_tool_log = await gemma_client.generate_with_tools_loop(
            system=markdown_system,
            user=markdown_user,
            tools=[],  # cached values are in the user message — no tools
            dispatch=_dispatch,
            max_turns=2,
            max_wall_time_s=30.0,
            temperature=_ERN_EXPLAIN_TEMPERATURE,
            max_tokens=_ERN_EXPLAIN_MAX_TOKENS,
            extra={**extra, "fallback_after_json_parse_failure": True},
        )
        # Trace events stay on the original tool_call_log so the
        # frontend's post-hoc renderer shows the live calls that
        # actually happened.

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


def _strip_thinking_prefix(text: str) -> str:
    """Strip any chain-of-thought marker token Gemma may have emitted
    at the start of the response. Idempotent. Conservative — only
    matches known prefixes against the *start* of the text after
    light whitespace stripping; never touches the body of the answer.

    Also strips any leading ``[helper: ...]`` scratchpad block(s) Gemma
    occasionally leaks despite the system prompt's "never reproduce
    helper annotations" clause. Multi-line; loops in case Gemma emits
    more than one consecutive block. Anchored to the start, so helper-
    bracketed text appearing inside the body of the answer (rare but
    possible) is left alone.
    """
    if not text:
        return text
    while True:
        m = _HELPER_LEAK_RE.match(text)
        if not m:
            break
        text = text[m.end():]
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

    # Assemble system prompt (branch-scope adds the appendix).
    lang_block = gemma_language_instruction(norm_locale)
    system_base = (
        _SYSTEM_BASE + _BRANCH_VOICE_APPENDIX
        if scope.kind == "branch"
        else _SYSTEM_BASE
    )
    system = f"{system_base}\n\n{lang_block}\n\n{context_block}"

    # ERN explain-this-stat — see chat_ask above for the gate.
    explain_ern = (
        scope.kind == "stat"
        and scope.target_id == "ERN"
        and message.strip() == _ERN_EXPLAIN_OPENER
    )
    if explain_ern:
        system = system + _ern_explain_appendix_json(builds[0].career)

    # Fold history into the user message.
    user_msg = (
        _ERN_EXPLAIN_USER_PROMPT
        if explain_ern
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
        "explain_ern": explain_ern,
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
                # See chat_ask above — 5 = 4 tool turns + 1 synthesis.
                max_turns=5,
                max_wall_time_s=30.0,
                temperature=(
                    _ERN_EXPLAIN_TEMPERATURE if explain_ern else _TEMPERATURE
                ),
                max_tokens=(
                    _ERN_EXPLAIN_MAX_TOKENS if explain_ern else 1200
                ),
                extra=extra,
                on_turn_start=on_start,
                on_turn_event=on_turn,
                final_turn_response_format=(
                    _ERN_EXPLAIN_RESPONSE_FORMAT if explain_ern else None
                ),
            )
        )
    )

    text = ""
    tool_call_log: list[gemma_client.ToolCallTurn] = []
    # Tracked separately so the `finally` block can cancel a fallback
    # in-flight on SSE client disconnect (per @faang-staff-engineer S3
    # finding — Decision C4 contract). Only set when the JSON path
    # parse-fails AND the explain-receipt fallback fires.
    fallback_task: asyncio.Task[
        tuple[str, list[gemma_client.ToolCallTurn]]
    ] | None = None
    try:
        # Drain queue until loop_task completes. The wait_for(timeout=...)
        # idiom interleaves queue reads with loop_task done-checks
        # without busy-spinning.
        while not loop_task.done() or not queue.empty():
            try:
                ev = await asyncio.wait_for(
                    queue.get(), timeout=_TRACE_DRAIN_POLL_S
                )
                yield ev
            except asyncio.TimeoutError:
                continue

        # Loop is done — collect its return. ANY exception (transport,
        # callback bug, programmer error) collapses to the fallback
        # final_text + done. Generator never raises past its boundary.
        try:
            text, tool_call_log = await loop_task
        except Exception as exc:  # noqa: BLE001 — boundary defense
            logger.warning("chat_ask_stream: loop_task raised — %s", exc)
            text = ""
            tool_call_log = []

        # ERN explain-receipt post-processing. On success yield the
        # receipt as the final_text payload; on failure run the markdown
        # fallback ONCE more with cached tool values injected.
        if explain_ern and text:
            receipt = _postprocess_ern_explain_receipt(
                raw=text,
                build=builds[0],
                tool_call_log=tool_call_log,
                backend=_current_backend(),
            )
            if receipt is not None:
                yield TraceFinalText(response=receipt)
                yield TraceDone()
                return
            # Markdown fallback — retry once with cached tool values.
            logger.warning(
                "ern_explain_receipt: JSON parse failed; retrying "
                "with markdown appendix + cached tool values"
            )
            cip_rank, earnings, wage_pct, wage = _extract_tool_results(
                tool_call_log, builds[0].career.soc_code
            )
            cached_values_block = _format_cached_tool_values(
                cip_rank, earnings, wage_pct, wage
            )
            markdown_system = (
                f"{system_base}\n\n{lang_block}\n\n{context_block}"
                + _ern_explain_appendix(builds[0].career)
            )
            markdown_user = (
                f"{cached_values_block}\n\n{_ERN_EXPLAIN_USER_PROMPT}"
            )
            # Wrap the fallback in a task so the outer `finally`
            # block can cancel it on SSE-client disconnect (Decision
            # C4 — semaphore must release within ~100ms, not at the
            # 30s wall-time cap).
            fallback_task = asyncio.create_task(
                gemma_client.generate_with_tools_loop(
                    system=markdown_system,
                    user=markdown_user,
                    tools=[],
                    dispatch=_dispatch,
                    max_turns=2,
                    max_wall_time_s=30.0,
                    temperature=_ERN_EXPLAIN_TEMPERATURE,
                    max_tokens=_ERN_EXPLAIN_MAX_TOKENS,
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
                    "ern_explain_receipt fallback failed: %s", exc
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
    if career.net_price_annual is not None:
        lines.append(
            f"- Net price per year after aid: "
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
