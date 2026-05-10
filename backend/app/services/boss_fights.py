"""Boss fight gauntlet.

Deterministic win/lose/draw logic against the 5 bosses plus a Final
Boss verdict that aggregates the gauntlet. Thresholds come from the
spec and are exposed as module-level constants so the CLI testing
session can tune them live.

Narratives (the 1-2 sentence coach explanation per fight) are
Gemma-generated when available. A deterministic fallback string is
used if Gemma is unavailable so the CLI never crashes mid-gauntlet.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import cast

from app.models.career import (
    BossFightResult,
    BossId,
    BossOutcome,
    CareerOutcome,
    GauntletResult,
)
from app.services import gemma_client
from app.services.locale import (
    AppLocale,
    fallback_text,
    gemma_language_instruction,
    normalize_locale,
)
from app.services.prose_sanitize import strip_markdown

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dollar formatting
# ---------------------------------------------------------------------------

def fmt_dollars(val: float | None) -> str:
    """Format a dollar amount or return 'n/a'."""
    if val is None:
        return "n/a"
    return f"${val:,.0f}"


def _published_cost_4yr(career: CareerOutcome) -> float | None:
    """Return the same 4-year published COA used by ROI and loans math."""
    if career.published_cost_4yr is not None:
        return career.published_cost_4yr
    if career.cost_of_attendance_annual is not None:
        return career.cost_of_attendance_annual * 4
    return None


# ---------------------------------------------------------------------------
# Stat explainer — plain-English descriptions for Gemma prompts
# ---------------------------------------------------------------------------

def stat_explainer(career: CareerOutcome) -> str:
    """Build a plain-English explanation of each stat with real numbers.

    Written at a 6th grade level so Gemma can reference concrete meaning
    instead of opaque scores like 'ROI 10/10'.
    """
    s = career.stats
    lines = ["Your stats explained:"]

    # ERN — earning power
    if s.ern is not None:
        earn_ctx = ""
        if career.earnings_1yr_median is not None:
            earn_ctx = (
                f" Graduates from this program start around "
                f"{fmt_dollars(career.earnings_1yr_median)}/yr."
            )
        lines.append(
            f"- ERN {s.ern}/10 (Earning Power): How much money people in "
            f"this career make compared to other careers.{earn_ctx}"
        )

    # ROI — return on investment
    if s.roi is not None:
        # ROI narrative is cost-vs-earnings only. Financing (loan_pct +
        # modeled_total_debt) belongs to the Student Loans Boss context,
        # not here. Plan: ~/.claude/plans/why-are-we-still-jaunty-curry.md
        roi_ctx = ""
        earn = (
            fmt_dollars(career.earnings_1yr_median)
            if career.earnings_1yr_median is not None
            else None
        )

        basis = career.roi_cost_basis
        if (
            basis == "cost_of_attendance"
            and career.published_cost_4yr is not None
            and earn
        ):
            roi_parts: list[str] = []
            sticker = _published_cost_4yr(career)
            roi_parts.append(
                f"Published cost is {fmt_dollars(sticker)} over 4 years"
            )
            loan_pct = career.loan_pct
            if loan_pct < 1.0 and sticker is not None:
                financed = sticker * loan_pct
                roi_parts.append(
                    f"at {int(loan_pct * 100)}% loan coverage that's"
                    f" {fmt_dollars(financed)} in student loans"
                )
            if career.net_price_annual is not None:
                avg_net = fmt_dollars(career.net_price_annual * 4)
                roi_parts.append(
                    f"the institutional average net price (aid context only) "
                    f"is {avg_net}"
                )
            roi_ctx = f" {'; '.join(roi_parts)} vs. {earn} starting salary."
        elif basis == "debt_median" and career.debt_median is not None and earn:
            # Institution-level cost data wasn't available for this
            # program row — fall back to median graduate debt as an
            # approximation of total cost.
            median_debt = fmt_dollars(career.debt_median)
            roi_ctx = (
                f" Median graduate debt is {median_debt} vs. {earn} "
                f"starting salary (program-level estimate — institution "
                f"cost data was not available)."
            )

        if roi_ctx and career.debt_to_earnings_annual is not None:
            dte = career.debt_to_earnings_annual
            if dte <= 0.5:
                roi_ctx += " That's a strong return — very manageable."
            elif dte <= 1.0:
                roi_ctx += " Cost is roughly one year of earnings."
            else:
                roi_ctx += (
                    f" That's {dte:.1f}× annual salary in cost — "
                    f"challenging return."
                )

        lines.append(
            f"- ROI {s.roi}/10 (Return on Investment): How the "
            f"total cost of your degree stacks up against your starting "
            f"salary. Doesn't depend on how you finance it — that's the "
            f"Student Loans Boss.{roi_ctx}"
        )

    # RES — AI resilience (now blended from stat_res + stat_hmn for display).
    # Note: Fight AI scores from the raw row inputs (career.raw_stat_res +
    # career.raw_stat_hmn), not this rounded display value.
    if s.res is not None:
        lines.append(
            f"- RES {s.res}/10 (AI Resilience): How well this career holds "
            f"up against AI. Blends two signals — how much the work still "
            f"needs people, and how poorly automation actually does it today."
        )

    # GRW — growth
    if s.grw is not None:
        if s.grw >= 7:
            grw_desc = "This job market is growing — employers are actively hiring."
        elif s.grw >= 4:
            grw_desc = "Hiring is steady for this job — not booming, not shrinking."
        else:
            grw_desc = "Fewer people are being hired for this job than before."
        lines.append(f"- GRW {s.grw}/10 (Growth): {grw_desc}")

    # AURA — institution-level brand gravity. Nullable for ~10% of unitids
    # without consumable.institution_aura coverage; render explicit "—".
    if s.aura is not None:
        if s.aura >= 7:
            aura_desc = (
                "This school carries serious institutional weight — strong "
                "endowment, marketing reach, athletic profile."
            )
        elif s.aura >= 4:
            aura_desc = (
                "This school has moderate brand gravity — solid presence "
                "without dominating headlines."
            )
        else:
            aura_desc = (
                "This school is light on institutional brand signal "
                "compared to peers."
            )
        lines.append(f"- AURA {s.aura}/10 (Brand Gravity): {aura_desc}")
    else:
        lines.append(
            "- AURA — (Brand Gravity): No institutional brand-gravity "
            "data is available for this school yet."
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Boss-specific context blocks
# ---------------------------------------------------------------------------

def _boss_context(career: CareerOutcome, boss_id: str) -> str:
    """Return a boss-specific data block with real dollar figures.

    Only ceiling and loans get extra context. Returns empty string for
    bosses that don't need dollar amounts or when data is unavailable.
    """
    if boss_id == "ceiling":
        parts = []
        if career.median_annual_wage is not None:
            parts.append(
                f"Occupation median wage: {fmt_dollars(career.median_annual_wage)}/yr"
            )
        if career.earnings_1yr_median is not None:
            parts.append(
                f"Program graduate median: {fmt_dollars(career.earnings_1yr_median)}/yr"
            )
        if (career.earnings_1yr_p25 is not None
                and career.earnings_1yr_p75 is not None):
            p25 = career.earnings_1yr_p25
            p75 = career.earnings_1yr_p75
            band = p75 - p25
            parts.append(
                f"Graduate earnings range: {fmt_dollars(p25)} (25th pct) to "
                f"{fmt_dollars(p75)} (75th pct)"
            )
            if band < 15_000:
                parts.append(
                    f"The 25th-to-75th range is only {fmt_dollars(band)} wide — "
                    f"this is a narrow earnings band. There is a real ceiling."
                )
            else:
                parts.append(
                    f"The 25th-to-75th range spans {fmt_dollars(band)} — "
                    f"there is meaningful room to grow within this career."
                )
        if not parts:
            return ""
        return "Earnings context: " + " ".join(parts)

    if boss_id == "ai":
        # Option B composite provenance (S4 v4). Surfaces real-world
        # AI adoption context so the Fight AI narrative can distinguish
        # "wave is here" from "wave is still arriving" instead of
        # speaking only in theoretical terms.
        parts = []
        velocity = career.velocity_label
        method = career.composite_method
        if velocity == "saturating":
            parts.append(
                "Real-world AI adoption: SATURATING. Claude and similar AI "
                "are already ubiquitous for the daily tasks of this occupation."
            )
        elif velocity == "accelerating":
            parts.append(
                "Real-world AI adoption: ACCELERATING. Adoption is moving "
                "fast across this occupation right now."
            )
        elif velocity == "emerging":
            parts.append(
                "Real-world AI adoption: EMERGING. Early-adopter signals "
                "are showing up — the wave is arriving."
            )
        elif velocity == "nascent":
            parts.append(
                "Real-world AI adoption: NASCENT. Little real-world AI "
                "usage in this occupation yet — runway still exists."
            )
        elif velocity == "unknown":
            parts.append(
                "Real-world AI adoption data is not yet available for this "
                "occupation. The score reflects theoretical capability only."
            )
        if method and method != "no_data":
            parts.append(f"Composite method: {method}.")
        if career.ai_adoption_share is not None:
            parts.append(
                f"Anthropic adoption share: {career.ai_adoption_share:.4f} "
                "(share of real Claude conversations)."
            )
        if not parts:
            return ""
        return "AI exposure context: " + " ".join(parts)

    if boss_id == "loans":
        parts = []
        loan_pct = career.loan_pct
        pct_label = f"{int(loan_pct * 100)}%"

        sticker = _published_cost_4yr(career)
        if sticker is not None:
            parts.append(
                f"Published 4-year cost (tuition, fees, and living costs): "
                f"{fmt_dollars(sticker)}"
            )
            if loan_pct < 1.0:
                parts.append(
                    f"Student is financing {pct_label} with loans: "
                    f"{fmt_dollars(sticker * loan_pct)} in student debt"
                )
            elif loan_pct >= 1.0:
                parts.append(
                    f"Student is financing 100% with loans: "
                    f"{fmt_dollars(sticker)} in student debt"
                )

        if career.net_price_annual is not None:
            avg_net_4yr = fmt_dollars(career.net_price_annual * 4)
            parts.append(
                f"Institutional average net price after typical "
                f"financial aid: {avg_net_4yr} over 4 years "
                f"(this is an average — individual aid packages vary)"
            )
            if career.net_price_annual_reference is not None:
                parts.append(
                    f"Out-of-state adjustment applied: in-state "
                    f"average net price is "
                    f"{fmt_dollars(career.net_price_annual_reference * 4)}"
                    f" over 4 years"
                )
            if sticker is None and career.modeled_total_debt is not None:
                parts.append(
                    f"Student's modeled debt (net price × {pct_label}): "
                    f"{fmt_dollars(career.modeled_total_debt)}"
                )
            ref_debt = (
                career.debt_median_reference
                if career.debt_median_reference is not None
                else career.debt_median
            )
            if ref_debt is not None:
                parts.append(
                    f"Median debt of graduates from this program: "
                    f"{fmt_dollars(ref_debt)}"
                )
        elif career.debt_median is not None:
            debt = fmt_dollars(career.debt_median)
            if loan_pct >= 1.0:
                parts.append(f"Median graduate debt: {debt}.")
            elif loan_pct <= 0.0:
                parts.append("Student is taking no loans.")
            else:
                parts.append(
                    f"Median graduate debt: {debt} "
                    f"(student covering {pct_label})."
                )
        if (career.debt_p25 is not None
                and career.debt_p75 is not None):
            parts.append(
                f"Debt range: {fmt_dollars(career.debt_p25)} "
                f"to {fmt_dollars(career.debt_p75)}."
            )
        if career.earnings_1yr_median is not None:
            parts.append(
                f"First-year earnings: {fmt_dollars(career.earnings_1yr_median)}"
            )
        # Total interest paid drives the Student Loans Boss power
        # (spec roi-net-lifetime-value, 2026-05-04). Surface it next to
        # the principal so the narrative reflects the real cost of the
        # financing choice, not just the borrowed amount.
        if (
            career.total_interest_paid is not None
            and career.total_interest_paid > 0
            and career.term_months is not None
            and career.term_months > 0
        ):
            term_years = career.term_months // 12
            interest = fmt_dollars(career.total_interest_paid)
            monthly_part = ""
            if (
                career.monthly_payment is not None
                and career.monthly_payment > 0
            ):
                monthly_part = (
                    f" Monthly payment: {fmt_dollars(career.monthly_payment)}."
                )
            parts.append(
                f"Modeled interest paid over the {term_years}-year "
                f"repayment term: {interest}.{monthly_part}"
            )
        # Financed DTE (loan_pct-aware) drives the Loans Boss score.
        # The debt_to_earnings_annual ratio is the cost-vs-earnings
        # "ROI DTE" — it belongs in the ROI narrative, not here. We
        # cite only the financed ratio in this boss' context so the
        # coach doesn't conflate the two.
        if career.financed_dte is not None:
            fdte = career.financed_dte
            pct = fdte * 100
            parts.append(
                f"Financed debt-to-earnings ratio (this loan choice): "
                f"{fdte:.2f} — the modeled debt is {pct:.0f}% of one "
                f"year's salary."
            )
        elif career.debt_to_earnings_annual is not None:
            # Fallback for rows where the loan pass wasn't computable.
            dte = career.debt_to_earnings_annual
            pct = dte * 100
            parts.append(
                f"Cost-to-earnings ratio (financing unknown): {dte:.2f} "
                f"({pct:.0f}% of one year's salary)."
            )
        if not parts:
            return ""
        return "Debt context: " + " ".join(parts)

    return ""


# ---------------------------------------------------------------------------
# Boss-specific narrative instructions
# ---------------------------------------------------------------------------

_GENERIC_INSTRUCTIONS = (
    "Explain what this piece of the student's data actually means for "
    "their real life. Translate the numbers into plain words — dollars, "
    "hours, percentages, what the work looks like. Reference the "
    "student's actual career and school. No generic advice."
)

_BOSS_INSTRUCTIONS: dict[str, str] = {
    "ceiling": (
        "Explain how high pay can go on this career path. Name the "
        "actual salary range graduates reach — what people earn at the "
        "low end and what people earn at the high end. If the range is "
        "narrow, say so plainly: there's a real limit, not that they "
        "will get rich. If the range is wide, say there's room to grow "
        "inside this career. Use the dollar figures provided."
    ),
    "loans": (
        "Explain what taking on this much debt would feel like month to "
        "month for this student. This is about THIS financing plan — "
        "the modeled debt at the current loan coverage — not the "
        "overall return on the degree. Use the modeled debt dollar "
        "amount and compare it plainly to one year of starting salary "
        "(e.g. 'the debt is about half of a year's pay'). If the "
        "numbers are strong, say why the payments would be manageable. "
        "If the numbers are rough, name one concrete way to shrink the "
        "debt — lower loan coverage, scholarships, a cheaper school."
    ),
    "ai": (
        "Explain what AI means for the daily work of this job. Name "
        "which parts of the job a computer can already do well and "
        "which parts still need a person. If AI adoption is "
        "saturating, say what's already being done by AI right now. If "
        "it's accelerating, say the gap is closing fast. If it's "
        "emerging, say the wave is arriving. If it's nascent, say "
        "there's still runway to prepare. If adoption data is missing, "
        "talk only about what's theoretically possible. Give one "
        "concrete skill or habit that keeps the student ahead of "
        "automation."
    ),
}


def _boss_instructions(boss_id: str) -> str:
    return _BOSS_INSTRUCTIONS.get(boss_id, _GENERIC_INSTRUCTIONS)


# ---------------------------------------------------------------------------
# Thresholds — tune live during high schooler testing session.
# ---------------------------------------------------------------------------
#
# Each entry defines the win/draw cutoffs. ``score_of`` computes the
# single scalar used for comparison against these bounds. The raw
# ``boss_*_score`` fields from the data layer are 1-10 ints that already
# encode the threat intensity; where spec thresholds reference pentagon
# stats (e.g. raw stat_res + stat_hmn for Fight AI — Decision 4 in
# pentagon-stat-reshape.md), we compute from the row scores instead of
# the raw boss score.

@dataclass(frozen=True)
class BossSpec:
    boss_id: str
    label: str
    win_at_or_above: int
    draw_at_or_above: int


BOSS_SPECS: dict[str, BossSpec] = {
    "ai": BossSpec(
        boss_id="ai",
        label="Fight AI",
        win_at_or_above=14,
        draw_at_or_above=10,
    ),
    "loans": BossSpec(
        boss_id="loans",
        label="Fight Student Loans",
        win_at_or_above=7,
        draw_at_or_above=5,
    ),
    "market": BossSpec(
        boss_id="market",
        label="Fight the Market",
        win_at_or_above=6,
        draw_at_or_above=4,
    ),
    "burnout": BossSpec(
        boss_id="burnout",
        label="Fight Burnout",
        # Higher is worse for burnout — we invert in score_of so that a
        # higher computed score still means "more ready to win". Score
        # is (11 - boss_burnout_score) so a low burnout risk produces a
        # high score. Thresholds apply to that inverted score.
        win_at_or_above=7,
        draw_at_or_above=5,
    ),
    "ceiling": BossSpec(
        boss_id="ceiling",
        label="Fight the Ceiling",
        win_at_or_above=7,
        draw_at_or_above=5,
    ),
}


def _safe_sum(*values: int | None) -> int | None:
    real = [v for v in values if isinstance(v, int)]
    if not real:
        return None
    return sum(real)


def _score_ai(career: CareerOutcome) -> tuple[int | None, str]:
    """Sum the RAW row inputs (stat_res + stat_hmn) using ``_safe_sum``.

    Reads from ``career.raw_stat_res`` and ``career.raw_stat_hmn`` — the
    underlying inputs preserved on CareerOutcome by ``_row_to_outcome``,
    NOT the blended ``stats.res`` display value. The blend is
    presentation-only (Decision 2 in pentagon-stat-reshape.md); Fight AI
    scores from the underlying inputs so existing thresholds (win=14,
    draw=10) and existing fixtures stay BIT-EXACT with pre-reshape
    behavior. Doubling the surviving input on the partial-null branch
    would silently flip ~1.05M rows, contradicting the bit-exact
    rationale (Decision 4 revised, v1.2 data-review fix).
    """
    raw_res = career.raw_stat_res
    raw_hmn = career.raw_stat_hmn
    score = _safe_sum(raw_res, raw_hmn)
    if score is None:
        return None, "raw stat_res and stat_hmn unavailable"
    # Match spec §6 wording: always emit both operands so downstream
    # readers (Gemma narrative prompts, audit logs) see the full math
    # even on the partial-null branch. None inputs render as "unavailable".
    res_str = f"stat_res {raw_res}" if raw_res is not None else "stat_res unavailable"
    hmn_str = f"stat_hmn {raw_hmn}" if raw_hmn is not None else "stat_hmn unavailable"
    return score, f"raw {res_str} + {hmn_str} = {score}"


def _score_loans(career: CareerOutcome) -> tuple[int | None, str]:
    """Financing-aware debt burden. Uses the loan_pct-aware boss score
    when available, falling back to the ROI stat for legacy rows."""
    if career.bosses.loans is not None:
        readiness = 11 - career.bosses.loans
        return readiness, f"loans_boss {career.bosses.loans} → readiness {readiness}"
    if career.stats.roi is None:
        return None, "ROI unavailable"
    return career.stats.roi, f"ROI {career.stats.roi} (fallback)"


def _score_market(career: CareerOutcome) -> tuple[int | None, str]:
    """GRW alone — market demand growth against the threshold."""
    if career.stats.grw is None:
        return None, "GRW unavailable"
    return career.stats.grw, f"GRW {career.stats.grw}"


def _score_burnout(career: CareerOutcome) -> tuple[int | None, str]:
    """Invert the burnout boss score.

    ``boss_burnout_score`` in the data is 1-10 where higher means the
    career is more burnout-prone. For the fight we want "win" to mean
    "low burnout risk", so we invert via (11 - boss_burnout_score).
    """
    raw = career.bosses.burnout
    if raw is None:
        return None, "burnout score unavailable"
    inverted = 11 - raw
    return inverted, f"burnout_risk {raw} → readiness {inverted}"


def _score_ceiling(career: CareerOutcome) -> tuple[int | None, str]:
    """Earnings ceiling — drawn from the pre-computed boss score if
    present, else falls back to the ERN stat as a proxy."""
    raw = career.bosses.ceiling
    if isinstance(raw, int):
        return raw, f"ceiling_score {raw}"
    if career.stats.ern is not None:
        return career.stats.ern, f"fallback ERN {career.stats.ern}"
    return None, "ceiling score unavailable"


_SCORERS = {
    "ai": _score_ai,
    "loans": _score_loans,
    "market": _score_market,
    "burnout": _score_burnout,
    "ceiling": _score_ceiling,
}


def _classify(score: int | None, spec: BossSpec) -> BossOutcome:
    if score is None:
        return "unknown"
    if score >= spec.win_at_or_above:
        return "win"
    if score >= spec.draw_at_or_above:
        return "draw"
    return "lose"


# ---------------------------------------------------------------------------
# Gemma narrative prompts
# ---------------------------------------------------------------------------

_NARRATIVE_SYSTEM = (
    "You are Gemma. A high school student is looking at one real piece "
    "of data about a career path they're considering — the school, the "
    "major, and what graduates actually earn or experience in that "
    "job. Your job is to explain, in plain words, what that piece of "
    "data means for their real life.\n\n"
    "Voice: candid, factual, warm, reassuring. Talk the way a calm "
    "older sibling with honest answers would talk — short, clear, no "
    "performance. You are the interpretation layer, not a judge. Never "
    "make the student feel small; never sugar-coat the numbers.\n\n"
    "Every sentence you write must translate the data into something "
    "real. If earnings are low compared to other graduates with this "
    "degree, say exactly that. If most of the daily work is something "
    "a computer can already do, say exactly that. If the cost is big "
    "compared to the starting salary, say exactly that. Use the actual "
    "dollar figures, years, and percentages the prompt gives you.\n\n"
    "Never use these words or framings in your output:\n"
    "- stat codes: ERN, ROI, RES, GRW, AURA, HMN. The student has never seen "
    "these letters. If a stat is low, say what it means ('earnings "
    "start low compared to other graduates from this program'), never "
    "the code or the number.\n"
    "- score fractions: never '7/10', '3 out of 10', or any numeric "
    "rating. Translate to plain words.\n"
    "- outcome labels: never WIN, DRAW, LOSE, won, lost, tied. The "
    "student already sees a label above your words; repeating it is "
    "redundant.\n"
    "- game framing: never 'fight', 'boss', 'gauntlet', 'battle', "
    "'beat', 'defeat', 'villain', 'level up', 'quest'. Those belong to "
    "the app's framing, not yours. Talk about 'how high pay can go', "
    "'what AI means for this work', 'paying off this debt' — not 'the "
    "Ceiling boss'.\n"
    "- filler: no exclamation points, bullet points, or 'as an AI'. "
    "Never 'empowering', 'journey', 'amazing', 'great news', 'just "
    "keep going', 'follow your passion', 'unfortunately'.\n\n"
    "Structure each response as 2-3 sentences of prose, written at a "
    "7th-grade reading level. First, say what the data means in real "
    "life. Then, be specific about WHY the outcome happened and WHAT "
    "could change it:\n"
    "- For a strong outcome: name the specific strength that carried "
    "it — 'your AI resilience score is high because most of this work "
    "still requires a person.'\n"
    "- For a borderline outcome: say exactly how close it was and "
    "what would tip it — 'you were one point short; picking up skills "
    "in human-centered work could push you over.'\n"
    "- For a tough outcome: name the specific gap and what kind of "
    "skill or change would close it — 'the AI exposure on this role "
    "is high and the human-essential score is low; skills in creative "
    "problem-solving or client relationships would help.'\n"
    "The prompt gives you a Scoring section with the exact threshold "
    "and gap. Use it to ground your advice in specifics, but translate "
    "the numbers into plain language — never echo stat codes or raw "
    "scores.\n"
    "Never doom-frame — a "
    "student can always change school, major, or path.\n\n"
    "If the prompt tells you there is no data for this piece of the "
    "career path, say so plainly. Do not invent a number, do not "
    "guess, do not fill silence with generic advice. A short, honest "
    "'there isn't enough data to say' is better than a made-up answer.\n\n"
    "Output format (STRICT): plain prose only. No markdown formatting "
    "of any kind — no asterisks (*, **), no underscores for emphasis, "
    "no headers, no bullet points, no horizontal rules, no triple "
    "backticks. The frontend renders your output verbatim; any "
    "markdown characters appear literally."
)

_COMPACT_NARRATIVE_SYSTEM = (
    "You are Gemma writing one short note for a high school student. "
    "Explain what one career-path risk means in real life.\n\n"
    "Rules: write 2 sentences only. Use plain English. No markdown. "
    "Do not use stat codes, score fractions, outcome labels, or game "
    "words like fight, boss, gauntlet, battle, beat, or defeat. "
    "Name the practical reason and one concrete lever the student can "
    "control."
)

_BOSS_LEVER_HINT: dict[str, str] = {
    "ai": (
        "This score comes from two inputs: how exposed the occupation is "
        "to AI automation, and how much of the daily work requires "
        "uniquely human skills (creativity, empathy, physical presence, "
        "judgment). Skills that strengthen the human side raise the score."
    ),
    "loans": (
        "This score reflects how manageable the debt is relative to "
        "starting earnings. A lower loan percentage, scholarships, or a "
        "less expensive school would improve it. Skills don't directly "
        "change this — it's about the financing plan."
    ),
    "market": (
        "This score is driven by how fast the job market for this "
        "occupation is growing according to BLS projections. Picking a "
        "specialization within the field that's in higher demand can help."
    ),
    "burnout": (
        "This score reflects how demanding the daily work environment is "
        "— long hours, physical strain, high-stakes pressure. Skills in "
        "stress management, work-life boundaries, or moving into less "
        "intense specializations can shift it."
    ),
    "ceiling": (
        "This score reflects how high earnings can go in this career — "
        "the gap between entry-level and experienced pay. Advanced "
        "credentials, leadership skills, or specializing in high-value "
        "niches can raise the ceiling."
    ),
}


def _scoring_explanation(fight: BossFightResult) -> str:
    """Plain-English scoring context: threshold, raw score, and what
    the inputs mean so Gemma can give specific guidance."""
    if fight.raw_score is None:
        return "No score data available for this risk."
    return (
        f"The student scored {fight.raw_score}. "
        f"Needed {fight.threshold_win} or higher to pass, "
        f"{fight.threshold_draw} or higher for borderline."
    )


def _gap_description(fight: BossFightResult) -> str:
    """How far the student is from the next threshold, plus the
    lever hint for this boss."""
    if fight.raw_score is None:
        return ""
    lever = _BOSS_LEVER_HINT.get(fight.boss, "")
    if fight.result == "win":
        margin = fight.raw_score - fight.threshold_win
        gap_line = (
            f"The student cleared the threshold by {margin} point(s). "
            "Explain what strength carried them."
        )
    elif fight.result == "draw":
        needed = fight.threshold_win - fight.raw_score
        gap_line = (
            f"The student is {needed} point(s) short of passing. "
            "Name what specific improvement would close that gap."
        )
    else:
        needed = fight.threshold_draw - fight.raw_score
        gap_line = (
            f"The student is {needed} point(s) below borderline and "
            f"{fight.threshold_win - fight.raw_score} point(s) from "
            f"passing. Name the biggest lever to close the gap."
        )
    if lever:
        return f"{gap_line}\n{lever}"
    return gap_line


def _narrative_prompt(
    career: CareerOutcome, fight: BossFightResult
) -> str:
    stats_explained = stat_explainer(career)
    context = _boss_context(career, fight.boss)
    instructions = _boss_instructions(fight.boss)

    parts = [
        f"Career: {career.occupation_title} (SOC {career.soc_code})",
        f"School/major: {career.institution_name} — {career.program_name}",
        "",
        stats_explained,
    ]
    if context:
        parts.append("")
        parts.append(context)
    scoring = _scoring_explanation(fight)
    gap = _gap_description(fight)

    parts.extend([
        "",
        f"Fight: {fight.label}",
        f"Result: {fight.result.upper()} — {fight.reason}",
        "",
        "Scoring:",
        scoring,
    ])
    if gap:
        parts.append(gap)
    parts.extend([
        "",
        instructions,
    ])
    return "\n".join(parts)


def _compact_outcome_phrase(fight: BossFightResult) -> str:
    if fight.result == "win":
        return "strong"
    if fight.result == "draw":
        return "mixed"
    if fight.result == "lose":
        return "tough"
    return "unclear"


def _compact_narrative_prompt(
    career: CareerOutcome, fight: BossFightResult
) -> str:
    context = _boss_context(career, fight.boss)
    parts = [
        f"Career: {career.occupation_title}",
        f"School/major: {career.institution_name} — {career.program_name}",
        f"Topic: {fight.label.replace('Fight ', '')}",
        f"Read: {_compact_outcome_phrase(fight)} — {fight.reason}",
        "",
        "Scoring context:",
        _scoring_explanation(fight),
    ]
    gap = _gap_description(fight)
    if gap:
        parts.append(gap)
    if context:
        parts.extend(["", context])
    parts.extend([
        "",
        "Write the student-facing note now. Mention actual dollar amounts "
        "only if provided above.",
    ])
    return "\n".join(parts)


def _reroll_prompt(
    career: CareerOutcome,
    fight: BossFightResult,
    original_result: str,
    original_narrative: str,
    crafted_skills: list[str],
) -> str:
    stats_explained = stat_explainer(career)
    context = _boss_context(career, fight.boss)
    skills_block = "\n".join(f"- {s}" for s in crafted_skills)

    parts = [
        f"Career: {career.occupation_title} (SOC {career.soc_code})",
        f"School/major: {career.institution_name} — {career.program_name}",
        "",
        stats_explained,
    ]
    if context:
        parts.append("")
        parts.append(context)
    parts.extend([
        "",
        f"Fight: {fight.label}",
        f"Original result: {original_result.upper()}",
        f"Your original commentary: {original_narrative}",
        "",
        f"New result after skills: {fight.result.upper()} — {fight.reason}",
        f"Skills the student chose to equip:\n{skills_block}",
        "",
        "The student applied real skills to improve their position. "
        "Write 3-4 sentences updating your original commentary to "
        "reflect the new result. Reinforce that these skills matter — "
        "the student will need to actually put in the work (courses, "
        "projects, certifications) to earn this improved outcome in "
        "real life. Reference the specific skills they chose and "
        "explain why those skills make a difference for this career. "
        "Be encouraging but honest: the skills shift the odds, they "
        "don't guarantee anything without real effort. "
        "Use actual dollar figures if available. "
        "Write at a 6th grade reading level. No jargon.",
    ])
    return "\n".join(parts)


def generate_reroll_commentary(
    career: CareerOutcome,
    fight: BossFightResult,
    original_result: str,
    original_narrative: str,
    crafted_skill_titles: list[str],
    locale: AppLocale = "en",
) -> str:
    """Generate Gemma coaching commentary for a reroll.

    Returns empty string on failure — the CLI can proceed without it.
    """
    locale = normalize_locale(locale)
    system = f"{_NARRATIVE_SYSTEM}\n\n{gemma_language_instruction(locale)}"
    try:
        text = gemma_client.generate(
            system=system,
            user=_reroll_prompt(
                career, fight, original_result, original_narrative,
                crafted_skill_titles,
            ),
            max_tokens=800,
            temperature=0.7,
        )
    except Exception as exc:
        logger.warning("reroll commentary gen failed: %s", exc)
        return ""
    return strip_markdown(text) if text else ""


async def generate_reroll_commentary_async(
    career: CareerOutcome,
    fight: BossFightResult,
    original_result: str,
    original_narrative: str,
    crafted_skill_titles: list[str],
    locale: AppLocale = "en",
) -> str:
    """Async variant of :func:`generate_reroll_commentary`."""
    locale = normalize_locale(locale)
    system = f"{_NARRATIVE_SYSTEM}\n\n{gemma_language_instruction(locale)}"
    try:
        text = await gemma_client.generate_async(
            system=system,
            user=_reroll_prompt(
                career, fight, original_result, original_narrative,
                crafted_skill_titles,
            ),
            max_tokens=800,
            temperature=0.7,
        )
    except Exception as exc:
        logger.warning("reroll commentary gen failed: %s", exc)
        return ""
    return strip_markdown(text) if text else ""


def _wrapup_prompt(
    career: CareerOutcome,
    fight: BossFightResult,
    original_result: str,
    all_skill_titles: list[str],
    all_narratives: list[str],
) -> str:
    stats_explained = stat_explainer(career)
    context = _boss_context(career, fight.boss)
    skills_block = "\n".join(f"- {s}" for s in all_skill_titles)
    narrative_block = "\n\n".join(
        f"Entry {i + 1}: {n}" for i, n in enumerate(all_narratives)
    )

    parts = [
        f"Career: {career.occupation_title} (SOC {career.soc_code})",
        f"School/major: {career.institution_name} — {career.program_name}",
        "",
        stats_explained,
    ]
    if context:
        parts.append("")
        parts.append(context)
    parts.extend([
        "",
        f"Fight: {fight.label}",
        f"Started at: {original_result.upper()}",
        f"Ended at: {fight.result.upper()} — {fight.reason}",
        "",
        f"All skills the student equipped:\n{skills_block}",
        "",
        f"Previous commentary entries:\n{narrative_block}",
        "",
        "The student has now used all available skills for this "
        "challenge. Write a 3-4 sentence final summary that ties "
        "the whole arc together. Reference where they started, what "
        "skills they chose, and where they ended up. Reinforce that "
        "these skills represent real work they need to do — courses, "
        "projects, certifications — not just checkboxes. Be "
        "encouraging but honest: the path is better now, but only "
        "if they follow through. Use actual dollar figures if "
        "available. Write at a 6th grade reading level. No jargon.",
    ])
    return "\n".join(parts)


async def generate_wrapup_async(
    career: CareerOutcome,
    fight: BossFightResult,
    original_result: str,
    all_skill_titles: list[str],
    all_narratives: list[str],
    locale: AppLocale = "en",
) -> str:
    """Generate a final wrap-up narrative after all skills are used."""
    locale = normalize_locale(locale)
    system = f"{_NARRATIVE_SYSTEM}\n\n{gemma_language_instruction(locale)}"
    try:
        text = await gemma_client.generate_async(
            system=system,
            user=_wrapup_prompt(
                career, fight, original_result, all_narratives=all_narratives,
                all_skill_titles=all_skill_titles,
            ),
            max_tokens=800,
            temperature=0.7,
        )
    except Exception as exc:
        logger.warning("wrapup commentary gen failed: %s", exc)
        return ""
    return strip_markdown(text) if text else ""


# Per-topic no-data copy. Shown verbatim when the scorer has no inputs
# for this piece of the career path. Voice must match Gemma's (candid,
# factual, warm) and must NOT reference stat codes, scores, WIN/LOSE,
# or game framing. The student sees this text where a coach note
# normally sits.
_UNKNOWN_FALLBACKS: dict[str, str] = {
    "ceiling": (
        "There isn't enough earnings data for this career path yet to "
        "say how high pay can go. When the numbers fill in, this part "
        "of your read will update."
    ),
    "ai": (
        "There isn't enough data yet on how much AI is being used in "
        "this kind of work, so there's no honest call to make here "
        "right now."
    ),
    "loans": (
        "There isn't enough cost or debt data for this program to "
        "show what borrowing for it would actually look like."
    ),
    "market": (
        "There isn't enough hiring data yet to say how this job "
        "market is changing."
    ),
    "burnout": (
        "There isn't enough data on the workload in this career to "
        "say how burnout-prone it tends to be."
    ),
}

# Degraded fallback — Gemma returned nothing for a fight that DID
# score. Extremely rare (transport failure after retries). The copy is
# deliberately generic and tone-matched; never leaks stat codes,
# outcome labels, or game framing.
_DEGRADED_FALLBACKS: dict[BossOutcome, str] = {
    "win": (
        "The numbers on this part of the path look strong. The write-up "
        "didn't load this time — you can come back to it."
    ),
    "draw": (
        "The numbers on this part of the path are mixed — some things "
        "work, some push back. The write-up didn't load this time."
    ),
    "lose": (
        "The numbers on this part of the path are tough. There's always "
        "room to change school, major, or approach. The write-up "
        "didn't load this time."
    ),
    "unknown": "",  # handled above
}


def _fallback_narrative(
    fight: BossFightResult, locale: AppLocale = "en",
) -> str:
    if fight.result == "unknown":
        localized = fallback_text(f"boss_unknown_{fight.boss}", locale)
        if localized:
            return localized
        return _UNKNOWN_FALLBACKS.get(
            fight.boss,
            "There isn't enough data here yet to make a call.",
        )
    return _DEGRADED_FALLBACKS.get(
        fight.result,
        "The write-up didn't load this time.",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def score_gauntlet(career: CareerOutcome) -> GauntletResult:
    """Run the pure-Python scoring half of the gauntlet.

    Returns a ``GauntletResult`` with every ``BossFightResult.narrative``
    left as an empty string. Callers that need narratives either call
    :func:`run_gauntlet` (sync) or :func:`narrate_one` per fight (async).
    """
    fights: list[BossFightResult] = []

    for boss_id, spec in BOSS_SPECS.items():
        score, reason = _SCORERS[boss_id](career)
        outcome = _classify(score, spec)
        fights.append(
            BossFightResult(
                boss=cast(BossId, boss_id),
                label=spec.label,
                result=outcome,
                raw_score=score,
                threshold_win=spec.win_at_or_above,
                threshold_draw=spec.draw_at_or_above,
                reason=reason,
            )
        )

    wins = sum(1 for f in fights if f.result == "win")
    losses = sum(1 for f in fights if f.result == "lose")
    draws = sum(1 for f in fights if f.result == "draw")
    unknown = sum(1 for f in fights if f.result == "unknown")
    verdict = _final_verdict(wins, losses, draws, unknown)

    return GauntletResult(
        fights=fights,
        wins=wins,
        losses=losses,
        draws=draws,
        unknown=unknown,
        verdict=verdict,
    )


async def narrate_one(
    career: CareerOutcome, fight: BossFightResult, locale: AppLocale = "en",
) -> str:
    """Generate a single boss narrative via Gemma, async.

    Transport-layer failures (network, 5xx, timeouts) are swallowed
    inside ``gemma_client.generate_async``, which returns ``""`` — we
    translate that to the deterministic fallback here. Unexpected
    exceptions (attribute errors, type errors, anything that indicates
    a real bug) are NOT caught here — the router's
    ``asyncio.gather(..., return_exceptions=True)`` is the single
    fallback gate, so the router can log them distinctly and this
    layer doesn't silently mask them.
    """
    # ``unknown`` means the scorer had no data to classify this fight.
    # The system prompt only defines WIN / DRAW / LOSE registers, so
    # asking Gemma to narrate an UNKNOWN result just gets us a prompt
    # echo ("Please provide the WIN, DRAW, or LOSE result..."). Skip
    # Gemma entirely and use the deterministic no-data fallback.
    locale = normalize_locale(locale)
    if fight.result == "unknown":
        return _fallback_narrative(fight, locale)
    profile = gemma_client.runtime_profile()
    compact = profile.tier == "compact_local"
    system_core = _COMPACT_NARRATIVE_SYSTEM if compact else _NARRATIVE_SYSTEM
    prompt = (
        _compact_narrative_prompt(career, fight)
        if compact
        else _narrative_prompt(career, fight)
    )
    system = f"{system_core}\n\n{gemma_language_instruction(locale)}"
    narrative = await gemma_client.generate_async(
        system=system,
        user=prompt,
        max_tokens=profile.build_narrative_max_tokens,
        temperature=0.7,
        timeout_s=profile.build_gemma_timeout_s,
        extra={
            "call_site": "boss_narrative",
            "boss_id": fight.boss,
            "profile_tier": profile.tier,
        },
    )
    return (
        strip_markdown(narrative)
        if narrative
        else _fallback_narrative(fight, locale)
    )


def run_gauntlet(
    career: CareerOutcome,
    *,
    with_narratives: bool = True,
    locale: AppLocale = "en",
) -> GauntletResult:
    """Run all 5 boss fights + compute the Final Boss verdict.

    Sync facade preserved for the CLI harness, scripts/, and tests. The
    router's async path calls :func:`score_gauntlet` + :func:`narrate_one`
    directly so the Gemma narratives fan out in parallel with the other
    build-time Gemma calls.
    """
    locale = normalize_locale(locale)
    gauntlet = score_gauntlet(career)

    if with_narratives:
        system = (
            f"{_NARRATIVE_SYSTEM}\n\n{gemma_language_instruction(locale)}"
        )
        for fight in gauntlet.fights:
            if fight.result == "unknown":
                fight.narrative = _fallback_narrative(fight, locale)
                continue
            try:
                narrative = gemma_client.generate(
                    system=system,
                    user=_narrative_prompt(career, fight),
                    max_tokens=800,
                    temperature=0.7,
                )
            except Exception as exc:
                logger.warning("boss narrative gen failed: %s", exc)
                narrative = ""
            fight.narrative = (
                strip_markdown(narrative)
                if narrative
                else _fallback_narrative(fight, locale)
            )

    return gauntlet


def rescore_fight(
    career: CareerOutcome,
    boss_id: str,
) -> BossFightResult:
    """Re-run a single boss fight's scorer + classifier against a
    (potentially mutated) career.

    Used by the CLI reroll flow after skills have been crafted — the
    caller passes the already-mutated career from
    ``skill_pool.apply_skills`` and uses the returned fight's
    ``result``/``raw_score``/``reason`` to update the live
    ``BossFightResult`` in place. Narrative is intentionally empty here
    because the original coach narrative still applies conceptually
    (the path didn't change; only the player's skill loadout did).
    """
    if boss_id not in BOSS_SPECS:
        raise ValueError(f"Unknown boss id: {boss_id!r}")
    spec = BOSS_SPECS[boss_id]
    score, reason = _SCORERS[boss_id](career)
    outcome = _classify(score, spec)
    return BossFightResult(
        boss=cast(BossId, boss_id),
        label=spec.label,
        result=outcome,
        raw_score=score,
        threshold_win=spec.win_at_or_above,
        threshold_draw=spec.draw_at_or_above,
        reason=reason,
    )


def recompute_totals(gauntlet: GauntletResult) -> None:
    """Recount W/L/D/unknown and the final verdict in place.

    Called by the CLI after a reroll flips one or more fights so the
    saved build and the summary panel reflect the current state of
    ``gauntlet.fights``.
    """
    fights = gauntlet.fights
    gauntlet.wins = sum(1 for f in fights if f.result == "win")
    gauntlet.losses = sum(1 for f in fights if f.result == "lose")
    gauntlet.draws = sum(1 for f in fights if f.result == "draw")
    gauntlet.unknown = sum(1 for f in fights if f.result == "unknown")
    gauntlet.verdict = _final_verdict(
        gauntlet.wins, gauntlet.losses, gauntlet.draws, gauntlet.unknown
    )


def _final_verdict(wins: int, losses: int, draws: int, unknown: int) -> str:
    scored = wins + losses + draws
    if scored == 0:
        return "Insufficient data to score the gauntlet."
    if losses == 0 and wins >= 3:
        return "DOMINANT BUILD — strong across the board."
    if wins > losses:
        if losses == 0:
            return "SOLID BUILD with minor soft spots."
        return f"SOLID BUILD with a {_weak_spot_label(losses)} gap."
    if wins == losses:
        return "MIXED BUILD — wins and losses cancel out; play to strengths."
    return "VULNERABLE BUILD — losses outweigh wins; active mitigation required."


def _weak_spot_label(loss_count: int) -> str:
    if loss_count == 1:
        return "single"
    if loss_count == 2:
        return "double"
    return f"{loss_count}-boss"
