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
    "You are a career coach narrating boss fights in an RPG-style career "
    "planning tool for high school students. You are direct, specific, "
    "and empowering — never doom. Keep responses to 3-4 sentences. Do "
    "NOT use bullet points. Do NOT start with platitudes."
)


def _narrative_prompt(
    career: CareerOutcome, fight: BossFightResult
) -> str:
    stats = career.stats
    return (
        f"Career: {career.occupation_title} (SOC {career.soc_code})\n"
        f"School/major: {career.institution_name} — {career.program_name}\n"
        f"Stats: ERN {stats.ern}, ROI {stats.roi}, RES {stats.res}, "
        f"GRW {stats.grw}, HMN {stats.hmn}\n"
        f"Fight: {fight.label}\n"
        f"Result: {fight.result.upper()} — {fight.reason}\n\n"
        f"Write the coach's 3-4 sentence take on this fight. "
        f"If the result is LOSE, say what the student can do about it. "
        f"If WIN, say what it actually means in practice. "
        f"Be concrete — reference the student's actual career, school, "
        f"or stats, not generic advice."
    )


def _reroll_prompt(
    career: CareerOutcome,
    fight: BossFightResult,
    original_result: str,
    crafted_skills: list[str],
) -> str:
    stats = career.stats
    skills_block = "\n".join(f"- {s}" for s in crafted_skills)
    return (
        f"Career: {career.occupation_title} (SOC {career.soc_code})\n"
        f"School/major: {career.institution_name} — {career.program_name}\n"
        f"Stats: ERN {stats.ern}, ROI {stats.roi}, RES {stats.res}, "
        f"GRW {stats.grw}, HMN {stats.hmn}\n"
        f"Fight: {fight.label}\n"
        f"Original result: {original_result.upper()}\n"
        f"New result after skills: {fight.result.upper()} — "
        f"{fight.reason}\n\n"
        f"Skills the student chose to equip:\n{skills_block}\n\n"
        f"Write the coach's 3-4 sentence take on why these skills "
        f"flipped the outcome. Explain what specifically changed in "
        f"the math and what this means for the student's path. "
        f"Reference the actual skills, school, and career — not "
        f"generic advice."
    )


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


def run_gauntlet(
    career: CareerOutcome,
    *,
    with_narratives: bool = True,
) -> GauntletResult:
    """Run all 5 boss fights + compute the Final Boss verdict."""
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

    if with_narratives:
        for fight in fights:
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
