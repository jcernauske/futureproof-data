"""Voice contract — lock Gemma's tone across every service that talks
to the student.

The contract comes from the product direction: Gemma is candid,
factual, warm, reassuring. Interpretation layer, never a judge. Plain
teen-level English. She never uses internal app framing — stat codes
(ERN/ROI/RES/GRW/AURA), score fractions ('7/10'), outcome labels
(WIN/DRAW/LOSE), or game framing (fight/boss/gauntlet/battle).

Two layers of tests here:

1. **System-prompt contract**: each Gemma-facing service's system
   prompt must explicitly forbid the stat codes, the outcome labels,
   and the game framing. If an edit silently removes a rule, CI
   catches it before a student sees the leak.
2. **Fallback output contract**: the deterministic fallbacks shown
   when Gemma is unreachable must already obey the rules — those
   strings go straight to the UI, unfiltered.

If you're adding a new Gemma-facing service, add its system prompt
and its fallback here.
"""

from __future__ import annotations

import pytest

from app.models.career import (
    BossFightResult,
    BossScores,
    CareerOutcome,
    GauntletResult,
    PentagonStats,
)
from app.services import (
    ask_gemma,
    boss_fights,
    career_pick_qna,
    guidance,
    skill_pool,
    skill_recs,
)

# ---------------------------------------------------------------------------
# Banned tokens — what Gemma must never emit to the student.
# ---------------------------------------------------------------------------

STAT_CODES = ("ERN", "ROI", "RES", "GRW", "AURA")
OUTCOME_LABELS = ("WIN", "DRAW", "LOSE")
GAME_FRAMING = (
    "fight",
    "boss",
    "gauntlet",
    "battle",
    "beat the",
    "defeat",
    "villain",
    "level up",
)
SCORE_FRACTIONS = ("/10", "out of 10")


# ---------------------------------------------------------------------------
# System-prompt contract — every Gemma-facing service must explicitly
# name the ban rules in its system prompt.
# ---------------------------------------------------------------------------

SYSTEM_PROMPTS: list[tuple[str, str]] = [
    ("boss_fights._NARRATIVE_SYSTEM", boss_fights._NARRATIVE_SYSTEM),
    ("guidance._SYSTEM", guidance._SYSTEM),
    ("guidance._CHAT_SYSTEM", guidance._CHAT_SYSTEM),
    ("skill_recs._SYSTEM", skill_recs._SYSTEM),
    ("skill_pool._POOL_SYSTEM", skill_pool._POOL_SYSTEM),
    ("career_pick_qna.GEMMA_SYSTEM_PROMPT", career_pick_qna.GEMMA_SYSTEM_PROMPT),
    ("ask_gemma._SYSTEM_BASE", ask_gemma._SYSTEM_BASE),
]


@pytest.mark.parametrize("name, prompt", SYSTEM_PROMPTS)
def test_system_prompt_bans_stat_codes(name: str, prompt: str) -> None:
    """Every system prompt must explicitly forbid the stat codes."""
    lower = prompt.lower()
    assert "never" in lower, f"{name}: missing 'never' — voice ban list looks stripped"
    # All 5 codes appear in the prompt (they're named in the ban list);
    # what we lock in here is that the codes are mentioned AT ALL so
    # the ban can't silently disappear.
    for code in STAT_CODES:
        assert code in prompt, (
            f"{name}: stat code {code!r} not named in system prompt — "
            f"the explicit 'never use ERN/ROI/RES/GRW/AURA' ban is missing"
        )


@pytest.mark.parametrize("name, prompt", SYSTEM_PROMPTS)
def test_system_prompt_bans_outcome_labels(name: str, prompt: str) -> None:
    """Every system prompt must explicitly forbid WIN / DRAW / LOSE."""
    for label in OUTCOME_LABELS:
        assert label in prompt, (
            f"{name}: outcome label {label!r} not named in system prompt — "
            f"the 'never use WIN/DRAW/LOSE' ban is missing"
        )


@pytest.mark.parametrize("name, prompt", SYSTEM_PROMPTS)
def test_system_prompt_bans_game_framing(name: str, prompt: str) -> None:
    """Every system prompt must explicitly forbid game framing."""
    lower = prompt.lower()
    # At minimum, 'fight', 'boss', and 'gauntlet' must be in the ban
    # list. They're the three words most likely to leak from our
    # internal vocabulary into Gemma's output.
    for word in ("fight", "boss", "gauntlet"):
        assert word in lower, (
            f"{name}: game-framing word {word!r} not named in system "
            f"prompt — the 'never use fight/boss/gauntlet' ban is missing"
        )


# ---------------------------------------------------------------------------
# Fallback output contract — deterministic strings shown to the
# student when Gemma is unreachable must already obey the rules.
# ---------------------------------------------------------------------------

def _career() -> CareerOutcome:
    return CareerOutcome(
        unitid=1,
        institution_name="IU-B",
        cipcode="52.14",
        program_name="Marketing",
        soc_code="11-2021",
        occupation_title="Marketing Managers",
        stats=PentagonStats(ern=8, roi=9, res=3, grw=6, aura=7),
        bosses=BossScores(ai=7, loans=2, market=6, burnout=5, ceiling=8),
        median_annual_wage=157_620.0,
        education_level_name="Bachelor's degree",
    )


def _gauntlet_with_ai_loss() -> GauntletResult:
    return GauntletResult(
        fights=[
            BossFightResult(
                boss="ai",  # type: ignore[arg-type]
                label="Fight AI",
                result="lose",  # type: ignore[arg-type]
                raw_score=10,
                threshold_win=14,
                threshold_draw=10,
                reason="RES 3 + AURA 7 = 10",
            )
        ],
        wins=0,
        losses=1,
        draws=0,
        unknown=0,
        verdict="SOLID BUILD with a single gap.",
    )


def _assert_voice_contract(text: str, *, context: str) -> None:
    """Shared voice-contract assertion for anything shown to the student."""
    assert text, f"{context}: empty string"
    # Stat codes — check the exact token so common words like 'growth'
    # (contains 'gr') don't false-positive. We scan for the uppercase
    # 3-letter code surrounded by word boundaries, approximated by
    # checking for the code followed by a non-letter or end-of-string.
    for code in STAT_CODES:
        for suffix in (" ", ",", ".", "\n", "/", ":", ""):
            needle = code + suffix
            if suffix == "" and not text.endswith(code):
                continue
            assert needle not in text, (
                f"{context}: stat code {code!r} leaked: {text!r}"
            )
    for label in OUTCOME_LABELS:
        assert label not in text, (
            f"{context}: outcome label {label!r} leaked: {text!r}"
        )
    for fraction in SCORE_FRACTIONS:
        assert fraction not in text, (
            f"{context}: score fraction {fraction!r} leaked: {text!r}"
        )
    for word in GAME_FRAMING:
        assert word not in text.lower(), (
            f"{context}: game-framing word {word!r} leaked: {text!r}"
        )


def test_boss_unknown_fallbacks_pass_voice_contract() -> None:
    for boss_id in ("ai", "loans", "market", "burnout", "ceiling"):
        fight = BossFightResult(
            boss=boss_id,  # type: ignore[arg-type]
            label=f"Fight {boss_id}",
            result="unknown",  # type: ignore[arg-type]
            raw_score=None,
            threshold_win=7,
            threshold_draw=5,
            reason=f"{boss_id} score unavailable",
        )
        text = boss_fights._fallback_narrative(fight)
        _assert_voice_contract(text, context=f"boss_fights unknown {boss_id}")


def test_boss_degraded_fallbacks_pass_voice_contract() -> None:
    for result in ("win", "draw", "lose"):
        fight = BossFightResult(
            boss="market",  # type: ignore[arg-type]
            label="Fight the Market",
            result=result,  # type: ignore[arg-type]
            raw_score=5,
            threshold_win=6,
            threshold_draw=4,
            reason="GRW 5",
        )
        text = boss_fights._fallback_narrative(fight)
        _assert_voice_contract(text, context=f"boss_fights degraded {result}")


def test_guidance_fallback_passes_voice_contract() -> None:
    text = guidance._fallback_narrative(_career(), _gauntlet_with_ai_loss())
    _assert_voice_contract(text, context="guidance fallback")


