"""'Gemma's Take' — the headline career guidance narrative.

Assembles the full context (school, major, career, pentagon, boss
results, branches) into a single prompt and asks Gemma for 4-6
sentences of coaching. This is the core value prop: the section
the student actually reads and acts on.

Tone: coach, not doom. Never tell a student their path is doomed;
tell them what to do about the weak spots.
"""

from __future__ import annotations

import logging
from typing import Any

from app.models.career import (
    Build,
    CareerBranch,
    CareerOutcome,
    GauntletResult,
    SkillRec,
)
from app.services import gemma_client
from app.services.boss_fights import fmt_dollars, stat_explainer
from app.services.locale import (
    AppLocale,
    fallback_text,
    gemma_language_instruction,
    normalize_locale,
)

logger = logging.getLogger(__name__)


_SYSTEM = (
    "You are Gemma. A high school student is looking at the career path "
    "that comes out of their school and major — who they'd likely become "
    "after graduating, what they'd earn, what the work actually involves. "
    "Your job is to explain, in plain words, what that whole picture "
    "means for their real life.\n\n"
    "Voice: candid, factual, warm, reassuring. Talk the way a calm older "
    "sibling with honest answers would talk — short, clear, no "
    "performance. You are the interpretation layer, not a judge. Never "
    "make the student feel small; never sugar-coat the numbers.\n\n"
    "Every sentence must translate the data into something real. If "
    "earnings are low compared to other graduates with this degree, say "
    "exactly that. If most of the daily work is something a computer can "
    "already do, say exactly that. If the cost is big compared to the "
    "starting salary, say exactly that. Use the actual dollar figures, "
    "years, and percentages the prompt gives you.\n\n"
    "Never use these words or framings in your output:\n"
    "- stat codes: ERN, ROI, RES, GRW, AURA, HMN. The student has never seen "
    "these letters. Translate to plain words — 'earnings start low "
    "compared to other graduates from this program', never the code or "
    "the number.\n"
    "- score fractions: never '7/10', '3 out of 10', or any numeric "
    "rating.\n"
    "- outcome labels: never WIN, DRAW, LOSE, won, lost, tied. The "
    "student already sees labels above your words; repeating them is "
    "redundant.\n"
    "- game framing: never 'fight', 'boss', 'gauntlet', 'battle', "
    "'beat', 'defeat', 'villain', 'level up', 'quest', 'gauntlet "
    "scored', 'receipts'. Those belong to the app's framing, not yours. "
    "Talk about 'how high pay can go', 'what AI means for this work', "
    "'paying off the debt' — not 'the Ceiling fight' or 'Fight AI'.\n"
    "- filler: no exclamation points, bullet points, or 'as an AI'. "
    "Never 'empowering', 'journey', 'amazing', 'great news', 'unlock', "
    "'transform', 'your future awaits', 'unfortunately'.\n\n"
    "Structure: two distinct paragraphs separated by a blank line.\n\n"
    "Paragraph 1 — ABOUT THE SCHOOL (4-6 sentences): Write exclusively "
    "about the institution itself. Use SPECIFIC facts you know — founding "
    "year, enrollment size, mascot, notable alumni, landmark buildings, "
    "specific academic strengths, conference affiliations, town/city "
    "character, signature traditions. Never write vague filler like "
    "'friendly atmosphere' or 'many options' — every sentence must "
    "contain a concrete, verifiable detail about THIS school that could "
    "not be said about any other school. Do NOT mention the career, "
    "salary, stats, or boss fights in this paragraph.\n\n"
    "Paragraph 2 — CAREER GUIDANCE (4-6 sentences): Now explain what "
    "the career picture means in plain terms. Cover earnings, debt, "
    "job outlook, and AI risk where relevant. Name one or two concrete "
    "things the student can do while still in school to strengthen the "
    "weakest part of the picture.\n\n"
    "Write at a 7th-grade reading level. Never doom-frame — the "
    "student can always change school, major, or path."
)


def _format_bosses(gauntlet: GauntletResult) -> str:
    lines = []
    for fight in gauntlet.fights:
        marker = {
            "win": "WIN",
            "lose": "LOSE",
            "draw": "DRAW",
            "unknown": "N/A",
        }[fight.result]
        lines.append(f"- {fight.label}: {marker} ({fight.reason})")
    return "\n".join(lines)


def _format_branches(branches: list[CareerBranch]) -> str:
    if not branches:
        return "- (no Stage 3 branches available for this occupation)"
    lines = []
    for branch in branches[:5]:
        deltas = [
            f"{name}{delta:+d}"
            for name, delta in (
                ("ERN", branch.delta_ern),
                ("ROI", branch.delta_roi),
                ("RES", branch.delta_res),
                ("GRW", branch.delta_grw),
                # AURA delta is institution-invariant (always 0 — Decision 5).
                # Skip emitting it when zero per the existing filter below.
                ("AURA", branch.delta_aura),
            )
            if isinstance(delta, int) and delta != 0
        ]
        delta_str = ", ".join(deltas) if deltas else "no stat deltas"
        lines.append(
            f"- {branch.to_title} ({branch.to_soc}): {delta_str}"
        )
    return "\n".join(lines)


def _prompt(
    career: CareerOutcome,
    gauntlet: GauntletResult,
    branches: list[CareerBranch],
) -> str:
    wage = fmt_dollars(career.median_annual_wage)
    stats_block = stat_explainer(career)
    return (
        f"Student is considering {career.institution_name}, majoring in "
        f"{career.program_name}.\n\n"
        f"Primary career after graduation: {career.occupation_title} "
        f"(SOC {career.soc_code})\n"
        f"Median salary: {wage}\n"
        f"Entry education: {career.education_level_name or 'unknown'}\n\n"
        f"{stats_block}\n\n"
        f"Boss fights:\n{_format_bosses(gauntlet)}\n\n"
        f"Career branches available:\n{_format_branches(branches)}\n\n"
        "Write two paragraphs separated by a blank line.\n\n"
        "PARAGRAPH 1 — About the school (4-6 sentences): Write exclusively "
        "about the institution using SPECIFIC facts — founding year, "
        "enrollment, mascot, notable alumni, landmark buildings, academic "
        "strengths, traditions. Every sentence must contain a concrete "
        "detail unique to THIS school. No vague filler. "
        "Do NOT mention the career, salary, or stats.\n\n"
        "PARAGRAPH 2 — Career guidance (4-6 sentences): Give career guidance "
        "specific to their school and major — not generic advice. "
        "IMPORTANT: Do NOT reference stat scores directly (like 'ROI 9/10' "
        "or 'ERN 7/10') — students don't know what those mean. Instead, "
        "explain the real-world meaning: talk about salary amounts, debt "
        "levels, job market trends, and AI risk in plain English. Use the "
        "dollar figures and explanations provided above. "
        "If they lost a boss fight, explain what they can do about it. "
        "Mention 1-2 concrete actions they can take while still in school. "
        "Write at a 6th grade reading level. No jargon."
    )


def _fallback_narrative(
    career: CareerOutcome,
    gauntlet: GauntletResult,
    locale: AppLocale = "en",
) -> str:
    """Degraded fallback — shown only when Gemma is unreachable.

    Voice contract matches ``_SYSTEM``: no stat codes, no outcome
    labels, no game framing. We name the school/major/career in plain
    terms and point the student at the weak spots in their build as
    something they can act on, without ranking them as wins or losses.
    """
    body = fallback_text("guidance_unavailable", locale)
    weak_labels = _weak_spot_phrases(gauntlet)
    if weak_labels:
        weak_clause = (
            " The parts of this path that look weakest right now are "
            f"{weak_labels} — those are the places to focus while you're "
            "still in school."
        )
    else:
        weak_clause = (
            " Nothing in this path looks broken right now — keep building on "
            "the parts that make it work."
        )
    return (
        f"{career.institution_name}'s {career.program_name} program "
        f"points toward {career.occupation_title}. {body}{weak_clause}"
    )


# Plain-language phrases for the 5 boss concepts. Used in fallbacks so
# we can name the weak spot without ever saying "fight" or "boss".
_WEAK_SPOT_PHRASES: dict[str, str] = {
    "ai": "how much of this work a computer can already do",
    "loans": "how big the debt gets compared to the starting salary",
    "market": "how much hiring is happening in this field",
    "burnout": "how demanding the work is on the people doing it",
    "ceiling": "how high pay can go over a career",
}


def _weak_spot_phrases(gauntlet: GauntletResult) -> str:
    names = [
        _WEAK_SPOT_PHRASES[f.boss]
        for f in gauntlet.fights
        if f.result == "lose" and f.boss in _WEAK_SPOT_PHRASES
    ]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def generate_guidance(
    career: CareerOutcome,
    gauntlet: GauntletResult,
    branches: list[CareerBranch],
    locale: AppLocale = "en",
) -> str:
    """Generate the 'Gemma's Take' narrative. Falls back to a template
    string if Gemma is unreachable so the CLI still renders the block."""
    locale = normalize_locale(locale)
    system = f"{_SYSTEM}\n\n{gemma_language_instruction(locale)}"
    text = gemma_client.generate(
        system=system,
        user=_prompt(career, gauntlet, branches),
        # 4-6 sentences of coaching averages ~180 words, but Gemma 4
        # frequently prefaces with a sentence or two; 1200 gives it
        # real headroom so it never gets clipped mid-thought.
        max_tokens=1200,
        temperature=0.7,
    )
    if text:
        return text

    logger.warning("guidance gen failed; using deterministic fallback")
    return _fallback_narrative(career, gauntlet, locale)


async def generate_guidance_async(
    career: CareerOutcome,
    gauntlet: GauntletResult,
    branches: list[CareerBranch],
    locale: AppLocale = "en",
) -> str:
    """Async variant — same fallback contract as :func:`generate_guidance`."""
    locale = normalize_locale(locale)
    system = f"{_SYSTEM}\n\n{gemma_language_instruction(locale)}"
    text = await gemma_client.generate_async(
        system=system,
        user=_prompt(career, gauntlet, branches),
        max_tokens=1200,
        temperature=0.7,
    )
    if text:
        return text

    logger.warning("guidance gen failed; using deterministic fallback")
    return _fallback_narrative(career, gauntlet, locale)


# ---------------------------------------------------------------------------
# Conversational mode: "Ask Gemma"
# ---------------------------------------------------------------------------


# Shared voice-rule core. Imported by ask_gemma.py so both chat surfaces
# enforce the same ban list from a single source. Voice-contract tests
# (test_gemma_voice_contract.py) assert literal token presence on the
# assembled `_CHAT_SYSTEM` constant — extraction must be byte-equivalent.
_SHARED_VOICE_RULES = (
    "Voice: candid, factual, warm, reassuring. Short, clear sentences. "
    "Interpretation layer, not a judge. Never make the student feel "
    "small; never sugar-coat the numbers. If you don't know the answer, "
    "say so — do not invent numbers.\n\n"
    "Translate every data point into something real: dollar figures, "
    "years, percentages, what the daily work looks like. If a stat is "
    "low, say what that means in the real world ('earnings start low "
    "compared to other graduates from this program'), never cite the "
    "stat code or the score.\n\n"
    "Never use these words or framings in your output:\n"
    "- stat codes: ERN, ROI, RES, GRW, AURA, HMN.\n"
    "- score fractions: never '7/10' or '3 out of 10'.\n"
    "- outcome labels: never WIN, DRAW, LOSE, won, lost, tied.\n"
    "- game framing: never 'fight', 'boss', 'gauntlet', 'battle', "
    "'beat', 'defeat', 'villain', 'level up'. Talk about the career, "
    "the work, the money, the debt — not the app's framing.\n"
    "- filler: no exclamation points, 'as an AI', 'empowering', "
    "'journey', 'amazing', 'your future awaits', 'unfortunately'."
)


_CHAT_SYSTEM = (
    "You are Gemma, in a chat thread with a high school student who is "
    "looking at the career path that comes out of their school and "
    "major. They're asking a follow-up question. Answer it plainly and "
    "specifically, using the data in the context.\n\n"
    f"{_SHARED_VOICE_RULES}\n\n"
    "If the student asks a 'what if' question about a different school "
    "or major, give your best honest read and say that the exact "
    "numbers come from running it as a new pick.\n\n"
    "Keep replies to 4-8 sentences of plain prose at a 7th-grade "
    "reading level, unless the student asks for more detail."
)


def _format_boss_summary(gauntlet: GauntletResult) -> str:
    if not gauntlet.fights:
        return "(no fights)"
    return ", ".join(
        f"{f.label}={f.result.upper()}" for f in gauntlet.fights
    )


def _format_branch_summary(branches: list[CareerBranch]) -> str:
    if not branches:
        return "(none available)"
    return "; ".join(b.to_title for b in branches[:5])


def _format_recs_summary(recs: list[SkillRec]) -> str:
    if not recs:
        return "(none)"
    return "; ".join(r.title for r in recs)


def _build_context_block(
    career: CareerOutcome,
    gauntlet: GauntletResult,
    branches: list[CareerBranch],
    skill_recs: list[SkillRec],
) -> str:
    wage = fmt_dollars(career.median_annual_wage)
    stats_block = stat_explainer(career)
    return (
        "Student's build:\n"
        f"- School: {career.institution_name}\n"
        f"- Major: {career.program_name} (CIP {career.cipcode})\n"
        f"- Primary career: {career.occupation_title} "
        f"(SOC {career.soc_code}), median {wage}\n"
        f"- Entry education: {career.education_level_name or 'unknown'}\n\n"
        f"{stats_block}\n\n"
        f"- Boss fight results: {_format_boss_summary(gauntlet)}\n"
        f"- Available career branches: {_format_branch_summary(branches)}\n"
        f"- Skill recommendations given: {_format_recs_summary(skill_recs)}"
    )


def chat_with_context(
    *,
    career: CareerOutcome,
    gauntlet: GauntletResult,
    branches: list[CareerBranch],
    skill_recs: list[SkillRec],
    conversation_history: list[dict],
    user_question: str,
    locale: AppLocale = "en",
) -> str:
    """Freeform Q&A with full build context loaded.

    The build context rides in the system prompt so every turn stays
    grounded in the student's actual numbers. ``conversation_history``
    holds prior user/assistant turns and accumulates across the session.
    """
    locale = normalize_locale(locale)
    context_block = _build_context_block(career, gauntlet, branches, skill_recs)
    lang_block = gemma_language_instruction(locale)
    system_with_context = (
        f"{_CHAT_SYSTEM}\n\n{lang_block}\n\n{context_block}"
    )
    messages: list[dict] = [
        *conversation_history,
        {"role": "user", "content": user_question},
    ]
    text = gemma_client.generate_chat(
        system=system_with_context,
        messages=messages,
        max_tokens=1200,
        temperature=0.7,
    )
    if text:
        return text

    logger.warning("chat_with_context failed; using fallback")
    return fallback_text("chat_unavailable", locale)


# ---------------------------------------------------------------------------
# Party Select comparison prompts
# ---------------------------------------------------------------------------

_MONEY_INSIGHT_SYSTEM = (
    "You are Gemma. A student is comparing 2-4 college options side by "
    "side. You are looking at the cost and salary data for each option. "
    "Your job is to surface the single most important money insight — "
    "the relationship between cost and earnings that the student might "
    "miss scanning the numbers alone.\n\n"
    "Voice: candid, factual, warm. Short, clear sentences. Use the "
    "actual dollar figures. Express debt differences in concrete terms "
    "(months of salary, not just dollar deltas).\n\n"
    "Never use these words or framings:\n"
    "- stat codes: ERN, ROI, RES, GRW, AURA, HMN\n"
    "- SOC codes: never mention SOC codes like '11-2011' or '13-1161'\n"
    "- score fractions: never '7/10'\n"
    "- outcome labels: never WIN, DRAW, LOSE\n"
    "- game framing: never 'fight', 'boss', 'gauntlet', 'battle'\n"
    "- filler: no exclamation points, bullet points, 'as an AI', "
    "'amazing', 'journey', 'unfortunately'\n"
    "- Never recommend a school or declare a winner\n\n"
    "Structure: 2-4 sentences of plain prose. Lead with the most "
    "surprising relationship. End with a one-sentence takeaway. "
    "Write at a 7th-grade reading level."
)


def _money_insight_prompt(builds: list[Build]) -> str:
    lines = ["The student is comparing these options:\n"]
    for b in builds:
        wage = fmt_dollars(b.career.median_annual_wage)
        cost = fmt_dollars(b.career.net_price_annual)
        debt = fmt_dollars(b.career.modeled_total_debt)
        loans_fight = next(
            (f for f in b.gauntlet.fights if f.boss == "loans"),
            None,
        )
        loans_result = loans_fight.result.upper() if loans_fight else "unknown"
        lines.append(
            f"- {b.school_name} ({b.major_text}) → {b.career.occupation_title}\n"
            f"  Median salary: {wage}\n"
            f"  Annual cost: {cost}\n"
            f"  Total modeled debt: {debt}\n"
            f"  Student Loans outcome: {loans_result}"
        )

    soc_codes = [b.career.soc_code for b in builds]
    if len(soc_codes) != len(set(soc_codes)):
        lines.append(
            "\nNote: Some of these options lead to the SAME career "
            "(same SOC code). If two options produce the same job at "
            "the same salary, the cost difference is pure premium — "
            "call that out explicitly."
        )

    lines.append(
        "\nWrite 2-4 sentences about the cost vs. salary picture. "
        "Use actual dollar figures. Express debt gaps as months of "
        "median salary when that makes it more concrete. "
        "Never recommend a school."
    )
    return "\n".join(lines)


async def generate_money_insight_async(
    builds: list[Build],
    locale: AppLocale = "en",
) -> str | None:
    locale = normalize_locale(locale)
    system = f"{_MONEY_INSIGHT_SYSTEM}\n\n{gemma_language_instruction(locale)}"
    text = await gemma_client.generate_async(
        system=system,
        user=_money_insight_prompt(builds),
        max_tokens=600,
        temperature=0.7,
    )
    if text:
        return text
    logger.warning("money insight gen failed; returning None")
    return None


_COMPARE_SYSTEM = (
    "You are Gemma. A student has built 2-4 career paths and is "
    "comparing them to decide which college to attend. Your job is to "
    "name the tradeoffs clearly — what each path optimizes for and "
    "what it sacrifices.\n\n"
    "Voice: candid, factual, warm. Talk the way a calm older sibling "
    "with honest answers would talk. You are the interpretation layer, "
    "not a judge. Never declare a winner. Never recommend a school.\n\n"
    "Never use these words or framings:\n"
    "- stat codes: ERN, ROI, RES, GRW, AURA, HMN\n"
    "- SOC codes: never mention SOC codes like '11-2011' or '13-1161'\n"
    "- score fractions: never '7/10'\n"
    "- outcome labels: never WIN, DRAW, LOSE\n"
    "- game framing: never 'fight', 'boss', 'gauntlet', 'battle'\n"
    "- filler: no exclamation points, bullet points, 'as an AI', "
    "'amazing', 'journey', 'unfortunately'\n\n"
    "Structure: one paragraph per build (3-4 sentences each), then a "
    "closing sentence about what the decision comes down to. "
    "Name each build by school name. "
    "Write at a 7th-grade reading level."
)


def _compare_summary_prompt(builds: list[Build]) -> str:
    schools = {b.school_name for b in builds}
    soc_codes = {b.career.soc_code for b in builds}

    if len(schools) == 1:
        frame = (
            "These are different majors at the SAME school. "
            "Focus on how the career paths differ, not the school."
        )
    elif len(soc_codes) == 1:
        frame = (
            "These are different schools leading to the SAME career. "
            "Focus on cost, risk profile, and which branches open up."
        )
    else:
        frame = (
            "These are different schools and different careers. "
            "Focus on what each path optimizes for and what it sacrifices."
        )

    lines = [f"Comparison context: {frame}\n"]

    for b in builds:
        wage = fmt_dollars(b.career.median_annual_wage)
        cost = fmt_dollars(b.career.net_price_annual)
        debt = fmt_dollars(b.career.modeled_total_debt)
        stats_block = stat_explainer(b.career)
        boss_summary = ", ".join(
            f"{f.label}={f.result.upper()}"
            + (
                f" (needed {f.reroll_count} skill{'s' if f.reroll_count != 1 else ''})"
                if f.reroll_count > 0
                else ""
            )
            for f in b.gauntlet.fights
        )
        branch_summary = (
            "; ".join(br.to_title for br in (b.branches or [])[:3]) or "(none)"
        )

        lines.append(
            f"BUILD: {b.school_name} — {b.major_text}\n"
            f"Career: {b.career.occupation_title}\n"
            f"Median salary: {wage} | Annual cost: {cost} | "
            f"Total debt: {debt}\n"
            f"{stats_block}\n"
            f"Risk results: {boss_summary}\n"
            f"Branches to: {branch_summary}\n"
        )

    lines.append(
        "Write one paragraph per build (3-4 sentences each), then a "
        "closing sentence. Name each build by school name. Translate "
        "stats into plain words — talk about earnings, debt, job "
        "growth, AI risk, burnout, and ceiling in real-world terms. "
        "Never declare a winner. Name the tradeoffs."
    )
    return "\n".join(lines)


async def generate_compare_summary_async(
    builds: list[Build],
    locale: AppLocale = "en",
) -> str | None:
    locale = normalize_locale(locale)
    system = f"{_COMPARE_SYSTEM}\n\n{gemma_language_instruction(locale)}"
    text = await gemma_client.generate_async(
        system=system,
        user=_compare_summary_prompt(builds),
        max_tokens=1200,
        temperature=0.7,
    )
    if text:
        return text
    logger.warning("compare summary gen failed; returning None")
    return None


_COMPARE_PROS_CONS_SYSTEM = (
    "You are Gemma. A student is comparing 2-4 career paths and needs "
    "tight, specific pros and cons for each option to make a decision.\n\n"
    "Voice: candid, factual, warm. No hedging, no filler, no slogans. "
    "Each bullet must contain at least one concrete number, dollar "
    "amount, percentage, or direct comparison to ANOTHER build in the "
    "set. No vague phrases like 'relies heavily on human connection' "
    "or 'unlikely to be replaced' — anchor every claim in data.\n\n"
    "Forbidden: stat codes (ERN/ROI/RES/GRW/AURA/HMN), SOC codes, score "
    "fractions like '7/10', WIN/DRAW/LOSE labels, the words 'fight', "
    "'boss', 'gauntlet', 'battle', 'journey', 'amazing', 'unfortunately', "
    "exclamation points, and bullet glyphs (no '✓' or '✗' — the UI "
    "renders those).\n\n"
    "Output format: respond ONLY with a single JSON object — no prose, "
    "no markdown fences, no commentary. Schema:\n"
    "{\n"
    '  "builds": [\n'
    '    { "build_id": "<verbatim id>", '
    '"pros": ["<≤18-word claim>", "<≤18-word claim>"], '
    '"cons": ["<≤18-word claim>", "<≤18-word claim>"] }\n'
    "  ]\n"
    "}\n\n"
    "Constraints: exactly 2 pros and 2 cons per build. Every claim ≤18 "
    "words. Each must reference real data from the build set (dollars, "
    "salary, debt, growth, exposure, etc.). Never declare a winner. "
    "Never use the word 'best'. Write at a 7th-grade reading level."
)


def _compare_pros_cons_prompt(builds: list[Build]) -> str:
    lines = [
        "Comparison set:\n",
    ]
    for b in builds:
        wage = fmt_dollars(b.career.median_annual_wage)
        cost = fmt_dollars(b.career.net_price_annual)
        debt = fmt_dollars(b.career.modeled_total_debt)
        stats_block = stat_explainer(b.career)
        boss_summary = ", ".join(
            f"{f.label}={f.result.upper()}" for f in b.gauntlet.fights
        )
        lines.append(
            f"build_id: {b.build_id}\n"
            f"School: {b.school_name}\n"
            f"Major: {b.major_text}\n"
            f"Career: {b.career.occupation_title}\n"
            f"Median salary: {wage} | Annual cost: {cost} | "
            f"Total debt: {debt}\n"
            f"{stats_block}\n"
            f"Risk results: {boss_summary}\n"
        )
    lines.append(
        "Return JSON only. Match each `build_id` exactly to the strings "
        "above. Each pro/con must compare against the OTHER builds in "
        "the set when possible (e.g., 'Pays $14k more than ASU CS')."
    )
    return "\n".join(lines)


async def generate_compare_pros_cons_async(
    builds: list[Build],
    locale: AppLocale = "en",
) -> list[dict[str, Any]] | None:
    """Return a list of {build_id, pros, cons} dicts, one per build.

    Returns None if Gemma fails or the JSON is unparseable. The endpoint
    is non-blocking — caller should treat None as "skip this section".
    """
    import json
    import re

    locale = normalize_locale(locale)
    system = f"{_COMPARE_PROS_CONS_SYSTEM}\n\n{gemma_language_instruction(locale)}"
    text = await gemma_client.generate_async(
        system=system,
        user=_compare_pros_cons_prompt(builds),
        max_tokens=900,
        temperature=0.5,
    )
    if not text:
        logger.warning("compare pros/cons gen failed; returning None")
        return None

    # Strip optional markdown fence Gemma sometimes adds despite instructions.
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.warning("compare pros/cons JSON parse failed: %s", exc)
        return None

    if not isinstance(parsed, dict) or not isinstance(parsed.get("builds"), list):
        logger.warning("compare pros/cons malformed; missing builds[]")
        return None

    valid_ids = {b.build_id for b in builds}
    out: list[dict[str, Any]] = []
    for entry in parsed["builds"]:
        if not isinstance(entry, dict):
            continue
        bid = entry.get("build_id")
        pros = entry.get("pros", [])
        cons = entry.get("cons", [])
        if bid not in valid_ids:
            continue
        if not isinstance(pros, list) or not isinstance(cons, list):
            continue
        out.append(
            {
                "build_id": bid,
                "pros": [str(p) for p in pros if isinstance(p, str)][:3],
                "cons": [str(c) for c in cons if isinstance(c, str)][:3],
            }
        )
    return out if out else None


_COMPARE_PIVOTAL_SYSTEM = (
    "You are Gemma. A high-school student (age 16-18) is comparing 2-4 "
    "college career paths. They have already seen the numbers, the "
    "pros, and the cons. Your job is to leave them with something to "
    "actually think about — not a recap.\n\n"
    "Voice: candid, factual, warm. Talk like a calm older sibling who "
    "respects the kid's intelligence but uses words a high-schooler "
    "actually says. No slogans. No hedging. No business-school jargon. "
    "No 'consider', 'imagine', 'think about'. No rhetorical questions "
    "about feelings.\n\n"
    "Forbidden words and phrases (will be rejected): stat codes "
    "(ERN/ROI/RES/GRW/AURA/HMN), SOC codes, score fractions like '3/10' or "
    "'7/10', WIN/DRAW/LOSE, 'fight', 'boss', 'gauntlet', 'battle', "
    "'journey', 'amazing', 'unfortunately', exclamation points, 'best "
    "of both worlds', 'at the end of the day', 'follow your heart', "
    "'passion', 'dream job', 'capital', 'equity', 'liability', 'asset', "
    "'liquidity', 'optionality', 'trajectory', 'profile' (as in 'risk "
    "profile'), 'leverage', 'portfolio', 'arbitrage', 'opportunity "
    "cost', 'ROI' (use 'payoff' or 'what you get back'), 'debt service', "
    "'principal', 'amortization', 'lifestyle delta'.\n\n"
    "Output ONLY a single JSON object — no prose, no markdown fences. Schema:\n"
    "{\n"
    '  "meta_tradeoff": "<3-5 word label using kid words, '
    "e.g. 'Pay Now or Pay Later'>\",\n"
    '  "meta_explanation": "<one sentence, ≤22 words, '
    'must reference one specific datum>",\n'
    '  "decade_projection": "<2-3 sentences projecting age 30: cumulative earnings, '
    "when debt is paid off, what the day-to-day feels like, branch destinations. "
    "Must compound real numbers.>\",\n"
    '  "pivot_question": "<one sharp question, ≤25 words, no easy answer, references '
    "at least one specific number or branch destination from the data>\"\n"
    "}\n\n"
    "META_TRADEOFF EXAMPLES (binary, for 2-build sets):\n"
    "GOOD (kid-friendly, plain words, names the real choice):\n"
    "  - 'Pay Now or Pay Later'\n"
    "  - 'Big Paycheck or Big Climb'\n"
    "  - 'Steady Job or Big Job'\n"
    "  - 'Same Job, Different Price'\n"
    "  - 'Easy Start, Hard Ceiling'\n"
    "  - 'Money Now or Choices Later'\n"
    "  - 'Stay Put or Move Up'\n"
    "  - 'Safe Bet vs Long Climb'\n"
    "BAD (business-school jargon, will be rejected):\n"
    "  - 'Starting Capital vs Debt Load'\n"
    "  - 'Earnings Trajectory vs ROI Profile'\n"
    "  - 'Risk Premium vs Stability'\n"
    "  - 'Optionality vs Specialization'\n"
    "  - 'Cash Flow vs Career Ceiling'\n"
    "Do not invent variations on the BAD examples. Use plain English.\n\n"
    "META_TRADEOFF EXAMPLES (3-way and 4-way, when N > 2 builds):\n"
    "If 3 builds, name THREE choices (use commas + 'or'):\n"
    "  - 'Money, Mission, or Cost'\n"
    "  - 'Big Pay, Steady Pay, or Calling'\n"
    "  - 'Climb Fast, Stay Steady, or Help People'\n"
    "  - 'Top Salary, Middle Path, or Service Work'\n"
    "If 4 builds, use a single axis-name frame:\n"
    "  - 'Four Different Tradeoffs'\n"
    "  - 'Four Bets on the Same Future'\n"
    "  - 'Pay vs Cost — Four Ways'\n"
    "When N > 2, the binary frames above are FORBIDDEN. A binary "
    "label silently drops one or more of the student's builds.\n\n"
    "OTHER CONSTRAINTS:\n"
    "- meta_explanation: explain the label using the actual numbers. "
    "Use plain words like 'paycheck', 'debt', 'school cost', 'first job'.\n"
    "- decade_projection: do real math. Cumulative salary by age 30 = "
    "median × ~8 working years. Subtract debt. Reference branch "
    "destinations the student might be at by then ('You'd likely be a "
    "<branch> by 30'). Talk about what life feels like — paying rent, "
    "saving up, free weekends. EVERY build must be named at least once "
    "in the projection. With 3 builds, write one short sentence per "
    "build. With 4 builds, group similar ones but name all four.\n"
    "- pivot_question: must NOT be answerable with 'whichever I want'. "
    "It must surface a real cost the student may not have noticed. "
    "Never start with 'Are you', 'Do you', 'Will you', 'Does'. Use "
    "specific anchors like dollar amounts, hours, branch names, ages. "
    "Avoid yes/no framing — favor 'Which / What / How much'. With "
    "more than 2 builds, the question must reference at least 2 of "
    "them — comparing only 2 of 3+ builds silently drops the others.\n"
    "- ARITHMETIC: Double-check every dollar amount and percentage "
    "before writing it. If you compute a difference, verify "
    "high − low produces the value you state.\n"
    "- Never declare a winner. Never recommend. 7th-grade reading level."
)


def _compare_pivotal_prompt(builds: list[Build]) -> str:
    n = len(builds)
    n_word = {2: "TWO", 3: "THREE", 4: "FOUR"}.get(n, str(n).upper())
    lines = [
        f"This is a {n_word}-WAY comparison ({n} builds). Every section "
        f"of your response must reflect ALL {n_word} builds — the "
        f"meta_tradeoff label, the decade_projection, and the "
        f"pivot_question. Treating it as a binary silently drops "
        f"{n - 2 if n > 2 else 0} build(s) the student took the time "
        f"to save.\n\nComparison set:\n",
    ]
    for b in builds:
        wage = fmt_dollars(b.career.median_annual_wage)
        cost = fmt_dollars(b.career.net_price_annual)
        debt = fmt_dollars(b.career.modeled_total_debt)
        stats_block = stat_explainer(b.career)
        boss_summary = ", ".join(
            f"{f.label}={f.result.upper()}" for f in b.gauntlet.fights
        )

        # Branch destinations: top 5 by relatedness, with deltas + unlock.
        branches_sorted = sorted(
            b.branches or [],
            key=lambda br: (br.relatedness if br.relatedness is not None else 999),
        )[:5]
        if branches_sorted:
            branch_lines = []
            for br in branches_sorted:
                pieces = [br.to_title]
                if br.unlock:
                    pieces.append(f"unlocks via {br.unlock}")
                if br.delta_ern is not None and br.delta_ern != 0:
                    sign = "+" if br.delta_ern > 0 else ""
                    pieces.append(f"earnings {sign}{br.delta_ern}")
                if br.experience_years is not None:
                    pieces.append(f"~{br.experience_years:.0f}y experience")
                branch_lines.append("    - " + " · ".join(pieces))
            branch_block = "\n".join(branch_lines)
        else:
            branch_block = "    (no branch data)"

        lines.append(
            f"build_id: {b.build_id}\n"
            f"School: {b.school_name}\n"
            f"Major: {b.major_text}\n"
            f"Career: {b.career.occupation_title}\n"
            f"Median salary: {wage} | Annual cost: {cost} | "
            f"Total debt: {debt}\n"
            f"{stats_block}\n"
            f"Risk results: {boss_summary}\n"
            f"  Branch destinations (top by relatedness):\n{branch_block}\n"
        )

    lines.append(
        "Use the branch destinations to color the decade_projection — "
        "many students will not stay in their first job. Use the deltas "
        "(earnings change, experience years) to estimate where they "
        "could be at age 30. Pick the meta_tradeoff that the data "
        "actually shows; do not pick a generic one."
    )
    return "\n".join(lines)


async def generate_compare_pivotal_async(
    builds: list[Build],
    locale: AppLocale = "en",
) -> dict[str, str] | None:
    """Return a single dict with meta_tradeoff, meta_explanation,
    decade_projection, and pivot_question.

    Returns None on Gemma failure or unparseable JSON.
    """
    import json
    import re

    locale = normalize_locale(locale)
    system = f"{_COMPARE_PIVOTAL_SYSTEM}\n\n{gemma_language_instruction(locale)}"
    text = await gemma_client.generate_async(
        system=system,
        user=_compare_pivotal_prompt(builds),
        max_tokens=900,
        temperature=0.6,
    )
    if not text:
        logger.warning("compare pivotal gen failed; returning None")
        return None

    cleaned = re.sub(
        r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE
    )
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.warning("compare pivotal JSON parse failed: %s", exc)
        return None

    required = (
        "meta_tradeoff",
        "meta_explanation",
        "decade_projection",
        "pivot_question",
    )
    if not isinstance(parsed, dict):
        return None
    if any(
        not isinstance(parsed.get(k), str) or not parsed[k].strip()
        for k in required
    ):
        logger.warning("compare pivotal missing required field(s)")
        return None

    return {k: parsed[k].strip() for k in required}
