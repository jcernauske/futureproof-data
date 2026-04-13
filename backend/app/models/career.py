"""Pydantic models shared by CLI services and future FastAPI routers.

These types are the API contract. The CLI renders them and the frontend
will consume the same shapes verbatim once routers are wired up.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

EffortLevel = Literal["working", "balanced", "all_in"]
BossOutcome = Literal["win", "lose", "draw", "unknown"]
BossId = Literal["ai", "loans", "market", "burnout", "ceiling"]


class SchoolMatch(BaseModel):
    unitid: int
    institution_name: str
    institution_control: str | None = None


class Program(BaseModel):
    unitid: int
    institution_name: str
    cipcode: str
    program_name: str
    cip_family_name: str | None = None
    earnings_1yr_median: float | None = None
    debt_median: float | None = None
    confidence_tier: str | None = None


class MajorMatch(BaseModel):
    method: Literal[
        "exact", "substring", "yaml", "gemma", "gemma_intent", "unmatched"
    ]
    cipcode: str | None = None
    program_name: str | None = None
    substitution_applied: bool = False
    reported_cipcode: str | None = None
    substituted_cipcode: str | None = None
    note: str | None = None


class PentagonStats(BaseModel):
    ern: int | None
    roi: int | None
    res: int | None
    grw: int | None
    hmn: int | None


class BossScores(BaseModel):
    ai: int | None
    loans: int | None
    market: int | None
    burnout: int | None
    ceiling: int | None


class CareerOutcome(BaseModel):
    unitid: int
    institution_name: str
    cipcode: str
    program_name: str
    soc_code: str
    occupation_title: str
    soc_major_group_name: str | None = None

    median_annual_wage: float | None = None
    earnings_1yr_median: float | None = None
    earnings_1yr_p25: float | None = None
    earnings_1yr_p75: float | None = None
    debt_median: float | None = None
    debt_to_earnings_annual: float | None = None
    education_level_name: str | None = None
    growth_category: str | None = None

    stats: PentagonStats
    bosses: BossScores

    top_5_activities: list[dict[str, object]] = Field(default_factory=list)
    top_human_activities: list[dict[str, object]] = Field(default_factory=list)
    burnout_drivers: list[dict[str, object]] = Field(default_factory=list)

    stats_available_count: int | None = None
    overall_confidence: str | None = None

    substitution_applied: bool = False
    reported_cipcode: str | None = None
    substituted_cipcode: str | None = None
    data_caveat: dict[str, object] | None = None

    loan_pct: float = 1.0


class BossFightResult(BaseModel):
    boss: BossId
    label: str
    result: BossOutcome
    raw_score: int | None
    threshold_win: int
    threshold_draw: int
    reason: str
    narrative: str = ""
    # Reroll bookkeeping — set when a loss is re-scored after the
    # student crafts skills on the loss screen.
    rerolled: bool = False
    reroll_count: int = 0
    original_result: BossOutcome | None = None
    original_raw_score: int | None = None


class GauntletResult(BaseModel):
    fights: list[BossFightResult]
    wins: int
    losses: int
    draws: int
    unknown: int
    verdict: str


class CareerBranch(BaseModel):
    from_soc: str
    to_soc: str
    to_title: str
    delta_ern: int | None = None
    delta_roi: int | None = None
    delta_res: int | None = None
    delta_grw: int | None = None
    delta_hmn: int | None = None
    unlock: str | None = None
    relatedness: float | None = None


class SkillRec(BaseModel):
    title: str
    stat_impact: str
    rationale: str


class AppliedSkill(BaseModel):
    """A curated skill with structured stat deltas.

    Unlike ``SkillRec`` (Gemma-generated free text for the post-build
    recommendations section), ``AppliedSkill`` has machine-readable
    deltas so it can be equipped during a boss reroll and actually
    change the fight math.

    ``targets`` lists the bosses this skill should surface on during a
    loss screen. Stat deltas (``delta_ern`` etc.) apply build-wide once
    the skill is crafted. ``delta_burnout_raw`` and ``delta_ceiling_raw``
    nudge the raw boss scores directly — negative reduces burnout risk,
    positive raises the ceiling.
    """

    id: str
    title: str
    rationale: str
    targets: list[BossId] = Field(default_factory=list)
    delta_ern: int = 0
    delta_roi: int = 0
    delta_res: int = 0
    delta_grw: int = 0
    delta_hmn: int = 0
    delta_burnout_raw: int = 0
    delta_ceiling_raw: int = 0


class Build(BaseModel):
    build_id: str
    created_at: str
    school_name: str
    unitid: int
    major_text: str
    cipcode: str
    program_name: str
    effort: EffortLevel
    loan_pct: float = 1.0
    career: CareerOutcome
    gauntlet: GauntletResult
    branches: list[CareerBranch]
    skill_recs: list[SkillRec]
    guidance: str
    skills_crafted: list[AppliedSkill] = Field(default_factory=list)
    skill_pool: list[AppliedSkill] = Field(default_factory=list)
    next_steps: str = ""


class BuildSummary(BaseModel):
    build_id: str
    created_at: str
    school_name: str
    major_text: str
    career_title: str
    ern: int | None
    roi: int | None
    res: int | None
    grw: int | None
    hmn: int | None
    wins: int
    losses: int


class IntentResult(BaseModel):
    matched_cip: str
    matched_title: str
    confidence: str
    reasoning: str = ""
    careers_preview: list[str] = Field(default_factory=list)
    audit_flag: str | None = None
    audit_message: str | None = None
    needs_clarification: bool = False
    alternatives: list[dict] | None = None
    parent_cip: str = ""


class ProfileResult(BaseModel):
    profile_name: str
    animal_emoji: str
    animal_name: str


class ProfileLookupResult(BaseModel):
    found: bool
    profile_name: str | None = None
    animal_emoji: str | None = None
    animal_name: str | None = None
    builds: list[BuildSummary] = Field(default_factory=list)
    suggestion: str | None = None
