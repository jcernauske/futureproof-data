"""Unit tests for context-builders in ``app.services.ask_gemma``.

These exercise the rendering layer directly (no Gemma, no router, no
HTTP). The contract is:

- Each ``_context_for_*`` builder returns a string that contains the
  ``§4`` manifest's required drivers for that scope.
- Every forbidden token (``ERN/ROI/RES/GRW/AURA/WIN/LOSE/DRAW`` etc.)
  appears ONLY inside ``[helper: ...]`` spans — never in the
  unbracketed prose Gemma might quote back to the student.

The "no leak" test (``test_context_blocks_never_leak_forbidden_tokens``)
is the binding hard gate for the voice contract on the prompt-input
side. The complement on the prompt-output side lives in
``test_ask_gemma_voice.py``.
"""

from __future__ import annotations

import re

import pytest

from app.models.career import (
    AppliedSkill,
    BossFightResult,
    BossScores,
    Build,
    CareerBranch,
    CareerOutcome,
    GauntletResult,
    PentagonStats,
    SkillRec,
)
from app.services import ask_gemma
from app.services.ask_gemma import (
    _context_for_boss,
    _context_for_branch,
    _context_for_build,
    _context_for_compare,
    _context_for_skill,
    _context_for_stat,
)

# ---------------------------------------------------------------------------
# Helpers — fully populated build fixtures.
# ---------------------------------------------------------------------------

# All five stats, all RES drivers, all ROI drivers, all five fights, all
# burnout drivers, all top-human activities, applied skills, branches,
# and skill recs. The §4 manifest tests need every field present;
# minimal fixtures elsewhere in the suite would leave gaps.


def _full_career(
    *,
    school: str = "UC Berkeley",
    program: str = "Computer Science",
    occupation: str = "Software Developers",
    soc: str = "15-1252",
    cipcode: str = "11.0701",
) -> CareerOutcome:
    return CareerOutcome(
        unitid=110635,
        institution_name=school,
        cipcode=cipcode,
        program_name=program,
        soc_code=soc,
        occupation_title=occupation,
        stats=PentagonStats(ern=8, roi=6, res=4, grw=9, aura=5),
        bosses=BossScores(ai=11, loans=8, market=10, burnout=6, ceiling=7),
        median_annual_wage=127_260.0,
        earnings_1yr_median=82_500.0,
        earnings_1yr_p25=58_000.0,
        earnings_1yr_p75=110_000.0,
        debt_median=21_000.0,
        debt_to_earnings_annual=0.32,
        education_level_name="Bachelor's degree",
        growth_category="growing_fast",
        net_price_annual=18_400.0,
        cost_of_attendance_annual=39_500.0,
        modeled_total_debt=36_800.0,
        debt_median_reference=21_000.0,
        institution_control="Public",
        state_abbr="CA",
        loan_pct=0.5,
        is_out_of_state=False,
        scoring_model="gemma-4",
        karpathy_score=4,
        task_breakdown_automatable=[
            "Writing boilerplate code",
            "Generating unit tests",
            "Refactoring small modules",
        ],
        task_breakdown_human=[
            "System design under ambiguity",
            "Negotiating product tradeoffs",
            "Debugging novel production incidents",
        ],
        ai_adoption_share=0.184,
        adoption_percentile=86.0,
        velocity_label="accelerating",
        composite_method="three_signal",
        roi_cost_basis="cost_of_attendance",
        financed_dte=0.224,
        top_5_activities=[],
        top_human_activities=[
            {"title": "Working with Computers", "importance": 0.92},
            {"title": "Thinking Creatively", "importance": 0.81},
            {"title": "Communicating with Coworkers", "importance": 0.74},
        ],
        burnout_drivers=[
            {"title": "Time Pressure", "importance": 0.85},
            {"title": "Frequent Decision Making", "importance": 0.78},
            {"title": "Importance of Being Exact", "importance": 0.71},
        ],
        stats_available_count=5,
        overall_confidence="high",
    )


def _full_gauntlet() -> GauntletResult:
    fights = [
        BossFightResult(
            boss="ai",  # type: ignore[arg-type]
            label="Fight AI",
            result="lose",  # type: ignore[arg-type]
            raw_score=9,
            threshold_win=14,
            threshold_draw=10,
            reason="RES 4 + AURA 5 = 9",
            narrative="The numbers point to AI eating into core tasks here.",
        ),
        BossFightResult(
            boss="loans",  # type: ignore[arg-type]
            label="Pay your loans",
            result="win",  # type: ignore[arg-type]
            raw_score=8,
            threshold_win=7,
            threshold_draw=5,
            reason="financed_dte 0.22",
            narrative="Salary outpaces the modeled debt by a healthy margin.",
        ),
        BossFightResult(
            boss="market",  # type: ignore[arg-type]
            label="Beat the market",
            result="win",  # type: ignore[arg-type]
            raw_score=9,
            threshold_win=6,
            threshold_draw=4,
            reason="GRW 9",
            narrative="BLS projects this field to expand sharply.",
        ),
        BossFightResult(
            boss="burnout",  # type: ignore[arg-type]
            label="Beat burnout",
            result="draw",  # type: ignore[arg-type]
            raw_score=6,
            threshold_win=7,
            threshold_draw=5,
            reason="AURA 5",
            narrative="Sustainable, but not dramatically protective.",
        ),
        BossFightResult(
            boss="ceiling",  # type: ignore[arg-type]
            label="Career ceiling",
            result="win",  # type: ignore[arg-type]
            raw_score=8,
            threshold_win=7,
            threshold_draw=5,
            reason="ERN 8",
            narrative="Strong upper-quartile earnings show real upside.",
        ),
    ]
    return GauntletResult(
        fights=fights,
        wins=3,
        losses=1,
        draws=1,
        unknown=0,
        verdict="SOLID BUILD with one gap.",
    )


def _skill_pool() -> list[AppliedSkill]:
    return [
        AppliedSkill(
            id="ai_minor",
            title="AI/ML elective track",
            rationale="Direct AI tools rather than be replaced by them.",
            targets=["ai", "market"],
            delta_res=2,
            delta_burnout_raw=-1,
        ),
        AppliedSkill(
            id="cc_first_year",
            title="Community College Transfer (Year 1)",
            rationale="Cut first-year tuition in half.",
            targets=["loans"],
            delta_roi=2,
            delta_burnout_raw=0,
        ),
    ]


def _full_build(
    *,
    build_id: str = "berkeley-cs-001",
    school: str = "UC Berkeley",
    program: str = "Computer Science",
) -> Build:
    return Build(
        build_id=build_id,
        created_at="2026-04-21T00:00:00Z",
        school_name=school,
        unitid=110635,
        major_text=program,
        cipcode="11.0701",
        program_name=program,
        effort="balanced",
        loan_pct=0.5,
        career=_full_career(school=school, program=program),
        gauntlet=_full_gauntlet(),
        branches=[
            CareerBranch(
                from_soc="15-1252",
                to_soc="15-1299",
                to_title="Tech Lead",
                delta_ern=2,
                delta_grw=-1,
            ),
            CareerBranch(
                from_soc="15-1252",
                to_soc="11-3021",
                to_title="Engineering Manager",
                delta_ern=3,
            ),
        ],
        skill_recs=[
            SkillRec(
                title="Add a CS minor",
                stat_impact="RES +2",
                rationale="Hardens against AI exposure on day-one work.",
            )
        ],
        guidance="Berkeley CS is strong on growth and earnings.",
        skills_crafted=[_skill_pool()[0]],
        skill_pool=_skill_pool(),
        next_steps="",
        profile_name="dancing happy bear",
    )


# ---------------------------------------------------------------------------
# Forbidden-token gate.
# ---------------------------------------------------------------------------

# Tokens that must NEVER appear outside a [helper: ...] span. Inside
# helpers they are expected — Gemma is instructed not to reproduce them.
FORBIDDEN_TOKENS: tuple[str, ...] = (
    "ERN",
    "ROI",
    "RES",
    "GRW",
    "AURA",
    "WIN",
    "LOSE",
    "DRAW",
    " boss",   # leading space avoids matching "labos" / "embossed" etc
    " fight",
    " gauntlet",
    "7/10",
    "out of 10",
    "8/14",
    "/10",
)

_HELPER_SPAN_RE = re.compile(r"\[helper:[^\]]*\]")


def _strip_helper_spans(text: str) -> str:
    """Return the context block with every [helper: ...] span removed.

    The remaining string is what the student would see if Gemma
    accidentally echoed the unbracketed prose verbatim. No forbidden
    token may appear in it.
    """
    return _HELPER_SPAN_RE.sub("", text)


def _assert_no_forbidden_outside_helpers(block: str, *, context: str) -> None:
    stripped = _strip_helper_spans(block)
    for token in FORBIDDEN_TOKENS:
        assert token not in stripped, (
            f"{context}: forbidden token {token!r} appears OUTSIDE a "
            f"[helper: ...] span. Stripped block:\n{stripped!r}"
        )


# ---------------------------------------------------------------------------
# Stat scope — drivers per stat code.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "stat_code",
    ["ERN", "ROI", "RES", "GRW", "AURA"],
)
def test_context_for_stat_includes_lineage_drivers(stat_code: str) -> None:
    build = _full_build()
    block = _context_for_stat(build, stat_code)

    # Header should always carry the school / program / occupation.
    assert "UC Berkeley" in block
    assert "Computer Science" in block
    assert "Software Developers" in block

    if stat_code == "ERN":
        # Median + 25th + 75th percentile dollars all rendered.
        assert "$82,500" in block
        assert "$58,000" in block
        assert "$110,000" in block
        assert "Earning Power" in block
    elif stat_code == "ROI":
        # ROI manifest: net_price_annual, debt_to_earnings_annual,
        # roi_cost_basis (the three the spec calls out by name).
        assert "$18,400" in block, "net_price_annual not rendered"
        assert "0.32" in block, "debt_to_earnings_annual not rendered"
        assert (
            "net price after aid" in block
        ), "roi_cost_basis 'cost_of_attendance' branch not rendered"
        # Plus modeled total debt / starting earnings — useful sibling drivers.
        assert "$36,800" in block
        assert "$82,500" in block
    elif stat_code == "RES":
        assert "three_signal" in block or "real-world Claude usage data" in block, (
            "composite_method not rendered"
        )
        assert "Karpathy score" in block, "karpathy_score not rendered"
        assert "18.4%" in block or "18.4" in block, "ai_adoption_share not rendered"
        assert "adoption percentile" in block, "adoption_percentile not rendered"
        # velocity_label of "accelerating" → "growing fast"
        assert "growing fast" in block, "velocity_label not translated"
    elif stat_code == "GRW":
        # qualitative growth_category renders as plain English.
        assert "growing_fast" in block or "grow much faster" in block
    elif stat_code == "AURA":
        # Pentagon-stat-reshape: AURA is institution-level brand gravity.
        # Drivers surface aura_score_basis + version, not top_human_activities
        # (which now lives on the RES side via the blended signal).
        assert (
            "Brand Gravity" in block
            or "institutional" in block
            or "endowment" in block
            or "no institutional brand-gravity data" in block
        )

    _assert_no_forbidden_outside_helpers(
        block, context=f"_context_for_stat({stat_code})"
    )


# ---------------------------------------------------------------------------
# Boss scope — thresholds + drivers per boss id.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "boss_id",
    ["ai", "loans", "market", "burnout", "ceiling"],
)
def test_context_for_boss_includes_thresholds_and_drivers(boss_id: str) -> None:
    build = _full_build()
    block = _context_for_boss(build, boss_id)

    fight = next(f for f in build.gauntlet.fights if f.boss == boss_id)

    # Raw score, win threshold, and draw threshold all live inside
    # [helper: ...] spans. Confirm the numeric values appear AND that
    # they appear inside helper brackets (not in the bare narrative).
    helper_text = "\n".join(_HELPER_SPAN_RE.findall(block))
    assert str(fight.raw_score) in helper_text, (
        f"{boss_id}: raw_score {fight.raw_score} missing from helpers"
    )
    assert str(fight.threshold_win) in helper_text, (
        f"{boss_id}: threshold_win {fight.threshold_win} missing from helpers"
    )
    assert str(fight.threshold_draw) in helper_text, (
        f"{boss_id}: threshold_draw {fight.threshold_draw} missing from helpers"
    )

    # Narrative is unbracketed — the student-facing prose may quote it.
    assert fight.narrative in block

    # Per-boss contributing drivers.
    if boss_id == "ai":
        # AI fight pulls in RES + AURA components and the
        # task_breakdown_human list (top 3, plain English).
        assert "System design under ambiguity" in block
    elif boss_id == "loans":
        # Modeled debt + starting earnings + financed_dte.
        assert "$36,800" in block
        assert "$82,500" in block
        assert "0.22" in block  # financed_dte
    elif boss_id == "market":
        assert "growing_fast" in block
    elif boss_id == "burnout":
        # Top 3 burnout drivers titles.
        assert "Time Pressure" in block
        assert "Frequent Decision Making" in block
        assert "Importance of Being Exact" in block
    elif boss_id == "ceiling":
        assert "$110,000" in block  # earnings_1yr_p75
        assert "Bachelor's degree" in block

    _assert_no_forbidden_outside_helpers(
        block, context=f"_context_for_boss({boss_id})"
    )


# ---------------------------------------------------------------------------
# Skill scope — deltas, targets, current build stats.
# ---------------------------------------------------------------------------


def test_context_for_skill_includes_deltas_and_targets() -> None:
    build = _full_build()
    skill = build.skills_crafted[0]
    block = _context_for_skill(build, skill.id)

    # Title and rationale (unbracketed — they're narrative).
    assert skill.title in block
    assert skill.rationale in block

    helper_text = "\n".join(_HELPER_SPAN_RE.findall(block))

    # Targets list must be in a helper block.
    assert "AI Resilience risk" in helper_text or "risk" in helper_text
    # Pentagon-stat-reshape: AppliedSkill no longer carries delta_hmn
    # (RES absorbed it). All non-zero deltas live in a helper:
    # delta_res=2, delta_burnout_raw=-1
    assert "+2" in helper_text or "AI Resilience +2" in helper_text
    assert "-1" in helper_text  # burnout raw delta

    # Current build stats must all be in helpers (5 stat lines).
    for alias in (
        "Earning Power",
        "Return on Investment",
        "AI Resilience",
        "Growth Outlook",
        "Brand Gravity",
    ):
        assert alias in helper_text, f"current stat alias {alias!r} missing"

    # Targeted boss outcomes (skill targets [ai, market]). At least
    # one targeted-boss line must be present in a helper span.
    assert "AI Resilience risk" in helper_text
    assert "Job Market risk" in helper_text

    _assert_no_forbidden_outside_helpers(
        block, context="_context_for_skill"
    )


def test_context_for_skill_unknown_id_raises() -> None:
    build = _full_build()
    with pytest.raises(ask_gemma.SkillNotFoundError):
        _context_for_skill(build, "nonexistent-skill")


# ---------------------------------------------------------------------------
# Whole-build scope — every stat, fight, finance, skill, branch.
# ---------------------------------------------------------------------------


def test_context_for_build_full_rich_block() -> None:
    build = _full_build()
    block = _context_for_build(build)

    helper_text = "\n".join(_HELPER_SPAN_RE.findall(block))

    # Every stat present in helpers.
    for alias in (
        "Earning Power",
        "Return on Investment",
        "AI Resilience",
        "Growth Outlook",
        "Brand Gravity",
    ):
        assert alias in helper_text, f"{alias} missing from build context helpers"

    # Every boss present in helpers.
    for alias in (
        "AI Resilience risk",
        "Student Loans risk",
        "Job Market risk",
        "Burnout risk",
        "Career Ceiling risk",
    ):
        assert alias in helper_text, f"{alias} missing from build context helpers"

    # Finances + ROI lineage (unbracketed plain dollars).
    assert "$82,500" in block  # earnings_1yr_median
    assert "$110,000" in block  # earnings_1yr_p75
    assert "$18,400" in block  # net_price_annual
    assert "$36,800" in block  # modeled_total_debt
    assert "0.32" in block  # debt_to_earnings_annual
    assert "growing_fast" in block
    assert "Bachelor's degree" in block

    # Applied skills (titles + rationales unbracketed; deltas bracketed).
    crafted = build.skills_crafted[0]
    assert crafted.title in block
    assert crafted.rationale in block

    # Branches.
    assert "Tech Lead" in block
    assert "Engineering Manager" in block

    # Skill recs.
    assert "Add a CS minor" in block

    # Fight narratives (each one is unbracketed in the build context).
    for fight in build.gauntlet.fights:
        assert fight.narrative in block

    _assert_no_forbidden_outside_helpers(
        block, context="_context_for_build"
    )


# ---------------------------------------------------------------------------
# Compare scope — pairwise dollar deltas across N=2/3/4.
# ---------------------------------------------------------------------------


def _build_for_compare(
    *, idx: int, school: str, program: str, occupation: str, soc: str
) -> Build:
    """One distinct build per comparison slot — different dollar
    figures so pairwise deltas are non-zero and meaningful."""
    base = _full_build(
        build_id=f"compare-{idx:03d}",
        school=school,
        program=program,
    )
    # Vary the headline dollars per slot so deltas are non-trivial.
    base.career.net_price_annual = 18_400.0 + idx * 5_000.0
    base.career.cost_of_attendance_annual = 39_500.0 + idx * 8_000.0
    base.career.modeled_total_debt = 36_800.0 + idx * 10_000.0
    base.career.earnings_1yr_median = 82_500.0 + idx * 7_500.0
    base.career.debt_to_earnings_annual = 0.32 + idx * 0.05
    base.career.occupation_title = occupation
    base.career.soc_code = soc
    base.career.program_name = program
    return base


@pytest.mark.parametrize("n_builds", [2, 3, 4])
def test_context_for_compare_with_2_3_4_builds(n_builds: int) -> None:
    builds = [
        _build_for_compare(
            idx=i,
            school=f"School {chr(65 + i)}",
            program=f"Major {chr(65 + i)}",
            occupation=f"Career {chr(65 + i)}",
            soc=f"15-{1252 + i}",
        )
        for i in range(n_builds)
    ]
    block = _context_for_compare(builds)

    # Header sanity — each build's school + program + career appears.
    for i in range(n_builds):
        assert f"School {chr(65 + i)}" in block
        assert f"Major {chr(65 + i)}" in block
        assert f"Career {chr(65 + i)}" in block

    # Pairwise deltas: for N builds there should be N*(N-1)/2 pairs.
    # Each pair generates at least one delta sentence with $ + "/yr higher"
    # or "more debt" or "more out of the gate". Assert the right number
    # of dollar-sign delta lines AND that the comparison sentence shape
    # the spec calls out is present.
    expected_pairs = n_builds * (n_builds - 1) // 2

    # Net-price lines — one per pair.
    net_price_lines = [
        line for line in block.split("\n") if "net price" in line and "$" in line
    ]
    assert len(net_price_lines) >= expected_pairs, (
        f"N={n_builds}: expected ≥{expected_pairs} net-price delta lines, "
        f"got {len(net_price_lines)}"
    )

    # The "X is $Y/yr higher" comparison sentence shape must appear.
    higher_lines = [
        line for line in block.split("\n") if "/yr higher" in line
    ]
    assert higher_lines, (
        f"N={n_builds}: no '/yr higher' comparison sentence found"
    )

    # Plain dollar formatting (fmt_dollars) — every delta line should
    # have at least one $-prefixed amount.
    assert "$" in block

    _assert_no_forbidden_outside_helpers(
        block, context=f"_context_for_compare(N={n_builds})"
    )


# ---------------------------------------------------------------------------
# Branch scope — feature-tree-as-map.md §4 (4 cases).
# ---------------------------------------------------------------------------


def _full_build_with_rich_branches() -> Build:
    """Branches with the full schema populated: stat deltas, unlock,
    relatedness, education_level, experience_tier."""
    base = _full_build()
    base.branches = [
        CareerBranch(
            from_soc="15-1252",
            to_soc="11-3021",
            to_title="Computer and Information Systems Managers",
            delta_ern=3,
            delta_roi=1,
            delta_res=2,
            delta_grw=-1,
            unlock="Requires master's degree",
            relatedness=0.84,
            related_education_level="Master's degree",
            experience_tier="Job Zone 5",
        ),
        CareerBranch(
            from_soc="15-1252",
            to_soc="15-1299",
            to_title="Computer Occupations, All Other",
            delta_ern=1,
            delta_grw=2,
            relatedness=0.71,
        ),
        CareerBranch(
            from_soc="15-1252",
            to_soc="11-9041",
            to_title="Architectural and Engineering Managers",
            delta_ern=2,
            delta_grw=1,
            relatedness=0.65,
        ),
        CareerBranch(
            from_soc="15-1252",
            to_soc="15-2031",
            to_title="Operations Research Analysts",
            delta_ern=-1,
            delta_res=2,
            relatedness=0.55,
        ),
    ]
    return base


@pytest.mark.asyncio
async def test_context_for_branch_full_record() -> None:
    """Full branch record: stat deltas + education + relatedness + wage
    anchor all render. Numeric values present in helper labels; no
    forbidden tokens in unbracketed prose."""
    build = _full_build_with_rich_branches()
    target = "11-3021"  # Computer and Information Systems Managers
    block = await _context_for_branch(build, target)

    helper_text = "\n".join(_HELPER_SPAN_RE.findall(block))

    # Header: school + program + root career rendered.
    assert "UC Berkeley" in block
    assert "Computer Science" in block
    assert "Software Developers" in block

    # Branch identity (unbracketed — title is plain English).
    assert "Computer and Information Systems Managers" in block

    # Stat deltas — every non-zero delta in helper bracket.
    # Pentagon-stat-reshape Decision 5: AURA is institution-invariant,
    # so branches never emit a Brand Gravity delta (delta_aura == 0).
    assert "Earning Power +3" in helper_text
    assert "Return on Investment +1" in helper_text
    assert "AI Resilience +2" in helper_text
    assert "Growth Outlook -1" in helper_text
    assert "Brand Gravity" not in helper_text  # institution-invariant

    # Education requirement — typed level preferred over unlock string.
    assert "Master's degree" in helper_text

    # Relatedness signal in helpers.
    assert "0.84" in helper_text

    # Experience tier when populated.
    assert "Job Zone 5" in helper_text

    # Wage anchor — root career median + program starting earnings.
    assert "$127,260" in block
    assert "$82,500" in block

    # Verbatim title-quoting helper appears.
    assert "exact label" in helper_text or "exact label" in block

    # No forbidden tokens leak.
    _assert_no_forbidden_outside_helpers(
        block, context="_context_for_branch full"
    )


@pytest.mark.asyncio
async def test_context_for_branch_anchored_at_root() -> None:
    """target_id == root SOC → anchor-at-root case. Up to 3 branches
    enumerated, sorted by relatedness DESC."""
    build = _full_build_with_rich_branches()
    block = await _context_for_branch(build, build.career.soc_code)

    # Header still renders.
    assert "UC Berkeley" in block
    assert "Software Developers" in block

    # Top-3 by relatedness DESC: 0.84, 0.71, 0.65 — all 3 to_titles
    # named verbatim. The 4th (0.55) must be summarized away or omitted.
    assert "Computer and Information Systems Managers" in block
    assert "Computer Occupations, All Other" in block
    assert "Architectural and Engineering Managers" in block
    # 4th-most-related branch must NOT be in the top-3 enumeration.
    # It may still appear in a "plus N more" summary.
    assert "Operations Research Analysts" not in block or (
        "plus" in block.lower() and "more" in block.lower()
    )

    # "plus N more pathway(s)" footer when there are >3 branches.
    assert "plus" in block.lower()
    assert "more" in block.lower()

    # Anchor-at-root context references the root career stats so
    # Gemma can ground the conversation.
    helper_text = "\n".join(_HELPER_SPAN_RE.findall(block))
    for alias in (
        "Earning Power",
        "Return on Investment",
        "AI Resilience",
        "Growth Outlook",
        "Brand Gravity",
    ):
        assert alias in helper_text, f"{alias} missing from root anchor"

    # Verbatim-title quoting helper is present.
    assert "exact label" in helper_text or "exact label" in block

    _assert_no_forbidden_outside_helpers(
        block, context="_context_for_branch anchored_at_root"
    )


@pytest.mark.asyncio
async def test_context_for_branch_no_branches_in_build() -> None:
    """Build has no branches AND target_id == root SOC. The thin-data
    block renders, with the SOC anchor surfaced. Does NOT fabricate
    branch information."""
    build = _full_build()
    build.branches = []
    block = await _context_for_branch(build, build.career.soc_code)

    # Thin-data acknowledgement is in plain English (NOT inside helpers).
    assert "limited transition data" in block.lower()

    # SOC anchor is on a clear line so Gemma can call get_occupation_data.
    assert build.career.soc_code in block

    # No fabricated branches — there are no hallucinated to_titles.
    assert "Tech Lead" not in block
    assert "Engineering Manager" not in block
    # The block points Gemma at occupation-level guidance.
    helper_text = "\n".join(_HELPER_SPAN_RE.findall(block))
    assert "get_occupation_data" in helper_text

    _assert_no_forbidden_outside_helpers(
        block, context="_context_for_branch no_branches"
    )


@pytest.mark.asyncio
async def test_context_for_branch_target_not_resolvable() -> None:
    """target_id doesn't match any branch AND doesn't equal root SOC.
    Service must NOT raise — degrades to thin-data block + occupation
    pointer. The router relies on this for graceful degradation."""
    build = _full_build()
    target = "99-9999"  # Not a branch, not the root.

    # Must not raise.
    block = await _context_for_branch(build, target)

    # The block surfaces the unmapped target_id and points Gemma at
    # occupation-level guidance for the root SOC.
    assert "99-9999" in block or "isn't loaded" in block.lower()
    assert build.career.soc_code in block
    helper_text = "\n".join(_HELPER_SPAN_RE.findall(block))
    assert "get_occupation_data" in helper_text

    _assert_no_forbidden_outside_helpers(
        block, context="_context_for_branch target_not_resolvable"
    )


@pytest.mark.asyncio
async def test_context_for_branch_off_build_target_enriched_via_mcp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When target_id isn't on build.branches but IS a real SOC, the
    builder calls get_occupation_data and renders an enriched 2-step
    block. /future relies on this so Gemma can talk about L2 endpoints
    (branches-of-branches) without refusing.

    The builder must call ``mcp_client.call_async`` (not ``call``) so the
    DuckDB lookup runs on a worker thread instead of blocking the
    FastAPI event loop — see staff engineer audit 2026-05-01 §S2.
    """
    build = _full_build()
    target = "15-1212"  # Information Security Analysts, not in fixture branches.

    async def fake_mcp_call_async(
        tool: str, args: dict[str, object]
    ) -> dict[str, object]:
        assert tool == "get_occupation_data"
        assert args == {"soc_code": target}
        return {
            "data": {
                "soc_code": target,
                "occupation_title": "Information Security Analysts",
                "median_annual_wage": 124910.0,
                "education_level_name": "Bachelor's degree",
                "growth_category": "Much faster than average",
                "employment_change_pct": 31.5,
                "openings_annual_avg": 17300,
            },
        }

    monkeypatch.setattr(
        ask_gemma.mcp_client, "call_async", fake_mcp_call_async
    )

    block = await _context_for_branch(build, target)

    # Title surfaces in plain prose so Gemma can echo it.
    assert "Information Security Analysts" in block
    # 2-step framing — distinct from the "branch on this build" copy.
    assert "2-step" in block
    # No "isn't loaded" stub when we have data.
    assert "isn't loaded on this build" not in block
    # Wage rendered as plain dollars (not a forbidden token).
    assert "$124,910" in block
    # Forbidden tokens (education level, growth category) live in
    # helpers, not in the prose surface.
    helper_text = "\n".join(_HELPER_SPAN_RE.findall(block))
    assert "Bachelor's degree" in helper_text
    assert "Much faster than average" in helper_text

    _assert_no_forbidden_outside_helpers(
        block, context="_context_for_branch off_build_enriched"
    )


@pytest.mark.asyncio
async def test_context_for_branch_root_anchor_with_no_relatedness_falls_back() -> None:
    """Root-anchor heuristic edge case: when every branch has
    relatedness=None, fall back to list order rather than crashing on
    the sort key. Defensive — pre-existing builds may lack the field."""
    build = _full_build()
    # Wipe relatedness on both existing branches.
    for b in build.branches:
        b.relatedness = None
    block = await _context_for_branch(build, build.career.soc_code)

    # Both list-order branches must be enumerated.
    assert "Tech Lead" in block
    assert "Engineering Manager" in block

    _assert_no_forbidden_outside_helpers(
        block, context="_context_for_branch null_relatedness"
    )


@pytest.mark.asyncio
async def test_context_for_branch_unlock_is_helper_bracketed() -> None:
    """The literal `unlock` field value must live inside a [helper: ...]
    span — Gemma is instructed never to echo helpers, and the branch
    voice rule explicitly bans echoing 'unlock' (genai-architect Finding 6).
    A leaky build context would leave the word 'unlock' in unbracketed
    prose where Gemma might quote it back to the student."""
    build = _full_build()
    build.branches = [
        CareerBranch(
            from_soc="15-1252",
            to_soc="11-3021",
            to_title="Engineering Manager",
            delta_ern=3,
            unlock="Requires master's degree",
            related_education_level=None,  # Force the unlock path.
        ),
    ]
    block = await _context_for_branch(build, "11-3021")

    # The string "Requires master's degree" must only appear inside a
    # helper span — never in unbracketed prose.
    stripped = _strip_helper_spans(block)
    assert "Requires master's degree" not in stripped, (
        "unlock string leaked outside [helper: ...] span"
    )
    helper_text = "\n".join(_HELPER_SPAN_RE.findall(block))
    assert "Requires master's degree" in helper_text


# ---------------------------------------------------------------------------
# Hard gate — no leak of forbidden tokens outside [helper: ...] spans.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_context_blocks_never_leak_forbidden_tokens() -> None:
    """Walk every scope kind on a fully-populated build. For every line
    OUTSIDE a [helper: ...] span, no forbidden token may appear.

    This is the implementation's binding contract on the helper-bracket
    formatting rule (§4 line 989). If this fails the system prompt's
    translation injunction is no longer enough — the input itself is
    leaking forbidden vocabulary into Gemma's prose context.
    """
    build = _full_build()
    second_build = _build_for_compare(
        idx=1,
        school="School B",
        program="Major B",
        occupation="Career B",
        soc="15-1253",
    )

    rich_branch_build = _full_build_with_rich_branches()

    blocks: list[tuple[str, str]] = [
        ("stat=ERN", _context_for_stat(build, "ERN")),
        ("stat=ROI", _context_for_stat(build, "ROI")),
        ("stat=RES", _context_for_stat(build, "RES")),
        ("stat=GRW", _context_for_stat(build, "GRW")),
        ("stat=AURA", _context_for_stat(build, "AURA")),
        ("boss=ai", _context_for_boss(build, "ai")),
        ("boss=loans", _context_for_boss(build, "loans")),
        ("boss=market", _context_for_boss(build, "market")),
        ("boss=burnout", _context_for_boss(build, "burnout")),
        ("boss=ceiling", _context_for_boss(build, "ceiling")),
        ("skill", _context_for_skill(build, build.skills_crafted[0].id)),
        ("build", _context_for_build(build)),
        ("compare(N=2)", _context_for_compare([build, second_build])),
        (
            "branch=full",
            await _context_for_branch(rich_branch_build, "11-3021"),
        ),
        (
            "branch=root",
            await _context_for_branch(
                rich_branch_build, rich_branch_build.career.soc_code
            ),
        ),
        (
            "branch=unresolvable",
            await _context_for_branch(rich_branch_build, "99-9999"),
        ),
    ]

    for name, block in blocks:
        _assert_no_forbidden_outside_helpers(block, context=name)
