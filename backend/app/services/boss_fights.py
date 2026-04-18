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

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dollar formatting
# ---------------------------------------------------------------------------

def fmt_dollars(val: float | None) -> str:
    """Format a dollar amount or return 'n/a'."""
    if val is None:
        return "n/a"
    return f"${val:,.0f}"


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
            and career.net_price_annual is not None
            and earn
        ):
            four_year_cost = fmt_dollars(career.net_price_annual * 4)
            roi_ctx = (
                f" The 4-year cost to attend is about {four_year_cost} "
                f"vs. {earn} starting salary."
            )
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

    # RES — AI resilience
    if s.res is not None:
        lines.append(
            f"- RES {s.res}/10 (AI Resilience): How safe this job is from "
            f"being replaced by AI. Higher means the job needs skills that "
            f"computers can't do yet."
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

    # HMN — human touch
    if s.hmn is not None:
        if s.hmn >= 7:
            hmn_desc = (
                "Most of this job involves uniquely human skills — "
                "empathy, creativity, judgment."
            )
        elif s.hmn >= 4:
            hmn_desc = (
                "This job mixes human skills with technical/routine work."
            )
        else:
            hmn_desc = (
                "Much of this job is routine or technical work that "
                "doesn't rely heavily on human judgment."
            )
        lines.append(f"- HMN {s.hmn}/10 (Human Touch): {hmn_desc}")

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
        # Cost-of-attendance block — only shown when institution-level
        # net_price_annual is available. Gives Gemma the actual school
        # cost so the narrative can talk about the student's modeled
        # debt instead of just citing the median graduate's debt.
        if career.net_price_annual is not None:
            parts.append(
                f"School net price: "
                f"{fmt_dollars(career.net_price_annual)}/year"
            )
            if career.modeled_total_debt is not None:
                parts.append(
                    f"Student's modeled 4-year debt: "
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
            loan_pct = career.loan_pct
            pct_label = f"{int(loan_pct * 100)}%"
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
    "Write the coach's 3-4 sentence take on this fight. "
    "If the result is LOSE, say what the student can do about it. "
    "If WIN, say what it actually means in practice. "
    "Be concrete — reference the student's actual career, school, "
    "or stats, not generic advice. "
    "Write at a 6th grade reading level. No jargon."
)

_BOSS_INSTRUCTIONS: dict[str, str] = {
    "ceiling": (
        "Write the coach's 3-4 sentence take on this fight. "
        "Use the actual dollar figures — cite them. "
        "If WIN but the earnings band is narrow, be honest: a win means "
        "the student is near the top of a limited range, not that they'll "
        "get rich. Name the actual salary range. "
        "If LOSE, name the dollar ceiling and what it means for their "
        "lifestyle. "
        "Write at a 6th grade reading level. No jargon."
    ),
    "loans": (
        "Write the coach's 3-4 sentence take on this fight. "
        "This fight is specifically about the student's FINANCING "
        "choice — their modeled debt at the current loan coverage % — "
        "NOT the overall program ROI. Cite the modeled debt dollar "
        "figure and the financed debt-to-earnings ratio. "
        "Explain what that ratio means (e.g. 'modeled debt is about "
        "half of one year's salary'). "
        "If WIN, say how manageable THIS financing plan is. "
        "If LOSE, describe the month-to-month burden and suggest the "
        "student explore lower loan coverage or scholarships. "
        "Write at a 6th grade reading level. No jargon."
    ),
    "ai": (
        "Write the coach's 3-4 sentence take on this fight. "
        "Explain what AI exposure means for this specific job's daily "
        "tasks — which parts could be automated and which can't. "
        "If a velocity label is present, lean on it: SATURATING means "
        "name what's already automated, ACCELERATING means warn the "
        "gap is closing fast, EMERGING means the wave is arriving, "
        "NASCENT means there's runway to prepare, UNKNOWN means talk "
        "about theoretical exposure only. "
        "If LOSE, say what the student can do to stay ahead. "
        "If WIN, say why this job is hard for AI to replace. "
        "Write at a 6th grade reading level. No jargon."
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
# stats (e.g. RES + HMN for Fight AI), we compute from the stats
# instead of the raw boss score.

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
    """RES + HMN — AI resilience stacked with uniquely-human work."""
    score = _safe_sum(career.stats.res, career.stats.hmn)
    if score is None:
        return None, "RES + HMN stats unavailable"
    return score, f"RES {career.stats.res} + HMN {career.stats.hmn} = {score}"


def _score_loans(career: CareerOutcome) -> tuple[int | None, str]:
    """Pure ROI — debt burden against earnings. Higher ROI = easier win."""
    if career.stats.roi is None:
        return None, "ROI unavailable"
    return career.stats.roi, f"ROI {career.stats.roi}"


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
    "You are Gemma, narrating a single boss fight in FutureProof's "
    "career gauntlet. The student just saw their WIN / DRAW / LOSE pill "
    "render next to a raw score and the thresholds — your narrative "
    "sits under that, explaining what it means in the real world.\n\n"
    "Register by outcome:\n"
    "- WIN: matter-of-fact. Name what beat the boss. Give one concrete "
    "action to keep the advantage. Never celebratory.\n"
    "- DRAW: direct. Name the stalemate in one sentence. Give one lever "
    "that could push it toward a win.\n"
    "- LOSE: contemplative. Name what broke down in real-world terms "
    "(dollars, debt, job trends, AI exposure). Give one concrete pivot. "
    "Never punishing, never doom-framing.\n\n"
    "Vocabulary: always 'Fight [X]' for the boss name. WIN / DRAW / "
    "LOSE in all caps only when citing the outcome noun. Stat codes "
    "ERN/ROI/RES/GRW/HMN; translate to dollars and plain language, "
    "never '9/10'.\n\n"
    "Anti-patterns: no 'empowering', no 'journey', no exclamation "
    "points, no bullet points, no 'great news', no 'as an AI'. Exactly "
    "2-3 sentences of prose. The student sees your sentences right "
    "next to the raw data — if you inflate or soften, they'll spot it."
)


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
    parts.extend([
        "",
        f"Fight: {fight.label}",
        f"Result: {fight.result.upper()} — {fight.reason}",
        "",
        instructions,
    ])
    return "\n".join(parts)


def _reroll_prompt(
    career: CareerOutcome,
    fight: BossFightResult,
    original_result: str,
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
        f"New result after skills: {fight.result.upper()} — {fight.reason}",
        "",
        f"Skills the student chose to equip:\n{skills_block}",
        "",
        "Write the coach's 3-4 sentence take on why these skills "
        "flipped the outcome. Explain what specifically changed and "
        "what this means for the student's path. Use actual dollar "
        "figures if available. Reference the actual skills, school, "
        "and career — not generic advice. "
        "Write at a 6th grade reading level. No jargon.",
    ])
    return "\n".join(parts)


def generate_reroll_commentary(
    career: CareerOutcome,
    fight: BossFightResult,
    original_result: str,
    crafted_skill_titles: list[str],
) -> str:
    """Generate Gemma coaching commentary for a successful reroll.

    Called only when a reroll flips the fight result (LOSE→WIN,
    LOSE→DRAW, etc). Returns empty string on failure — the CLI can
    proceed without it.
    """
    try:
        text = gemma_client.generate(
            system=_NARRATIVE_SYSTEM,
            user=_reroll_prompt(career, fight, original_result, crafted_skill_titles),
            max_tokens=800,
            temperature=0.7,
        )
    except Exception as exc:
        logger.warning("reroll commentary gen failed: %s", exc)
        return ""
    return text or ""


def _fallback_narrative(fight: BossFightResult) -> str:
    if fight.result == "unknown":
        return "No data to score this boss yet — flagged for review."
    return f"{fight.label}: {fight.result.upper()} ({fight.reason})"


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
    career: CareerOutcome, fight: BossFightResult
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
    narrative = await gemma_client.generate_async(
        system=_NARRATIVE_SYSTEM,
        user=_narrative_prompt(career, fight),
        max_tokens=800,
        temperature=0.7,
    )
    return narrative or _fallback_narrative(fight)


def run_gauntlet(
    career: CareerOutcome,
    *,
    with_narratives: bool = True,
) -> GauntletResult:
    """Run all 5 boss fights + compute the Final Boss verdict.

    Sync facade preserved for the CLI harness, scripts/, and tests. The
    router's async path calls :func:`score_gauntlet` + :func:`narrate_one`
    directly so the Gemma narratives fan out in parallel with the other
    build-time Gemma calls.
    """
    gauntlet = score_gauntlet(career)

    if with_narratives:
        for fight in gauntlet.fights:
            try:
                narrative = gemma_client.generate(
                    system=_NARRATIVE_SYSTEM,
                    user=_narrative_prompt(career, fight),
                    # 3-4 sentences is ~150 tokens of real content,
                    # but Gemma 4 burns plenty on preamble — 800 keeps
                    # narratives from getting clipped mid-thought on
                    # the paced gauntlet screens.
                    max_tokens=800,
                    temperature=0.7,
                )
            except Exception as exc:
                logger.warning("boss narrative gen failed: %s", exc)
                narrative = ""
            fight.narrative = narrative or _fallback_narrative(fight)

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
