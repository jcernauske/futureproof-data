"""Gemma-driven career tiering for the post-crosswalk career picker.

After ``stat_engine.compute_pentagon`` returns the full list of career
outcomes for a school+major, this module sends that list to Gemma with
the school context and asks it to group every matched occupation into
three tiers:

    **Common paths** — the 3-5 careers graduates of this school+major
    most frequently enter.
    **Less common but realistic** — the next 5-7 careers plausible for
    this school+major.
    **Stretch paths** — remaining crosswalk matches that are possible
    but less typical.

Gemma considers school tier, program emphasis, regional labor market,
and O*NET education requirements when tiering. The structured output
is parsed into an ordered mapping that the CLI renders as a grouped
menu. The student picks any career from any tier.

When Gemma fails or returns unparseable output, every outcome lands
in a single "All career paths" fallback tier so the CLI never blocks.
"""

from __future__ import annotations

import logging
import re
from collections import OrderedDict

from app.models.career import CareerOutcome
from app.services import gemma_client

logger = logging.getLogger(__name__)


TIER_COMMON = "Common paths"
TIER_LESS_COMMON = "Less common but realistic"
TIER_STRETCH = "Stretch paths"

_TIER_ORDER = [TIER_COMMON, TIER_LESS_COMMON, TIER_STRETCH]

_SOC_PATTERN = re.compile(r"\b(\d{2}-\d{4})\b")

_TIER_HEADER = re.compile(
    r"^\s*(?:COMMON|LESS_COMMON|STRETCH)\s*$",
    re.IGNORECASE,
)

_HEADER_TO_LABEL = {
    "common": TIER_COMMON,
    "less_common": TIER_LESS_COMMON,
    "stretch": TIER_STRETCH,
}


_SYSTEM = (
    "You categorize career outcomes into tiers for a college+major "
    "career planning tool. You are factual and direct. Consider: "
    "school prestige and program emphasis, regional employer demand, "
    "O*NET typical education requirements, and the frequency with "
    "which graduates of this specific program actually enter each "
    "career. No fake percentages. Output ONLY the structured format "
    "requested — no commentary, no markdown, no explanations."
)


def _prompt(
    outcomes: list[CareerOutcome],
    school_name: str,
    program_name: str,
    cipcode: str,
) -> str:
    soc_lines = "\n".join(
        f"  {o.soc_code}  {o.occupation_title}"
        + (f"  (median ${int(o.median_annual_wage):,})" if o.median_annual_wage else "")
        + (f"  [{o.education_level_name}]" if o.education_level_name else "")
        for o in outcomes
    )
    return (
        f"School: {school_name}\n"
        f"Major: {program_name} (CIP {cipcode})\n\n"
        f"The CIP-SOC crosswalk returned {len(outcomes)} matched "
        f"occupations. Tier ALL of them for this specific "
        f"school+major:\n\n"
        f"{soc_lines}\n\n"
        f"Output format — exactly three headers followed by SOC "
        f"codes, one per line:\n\n"
        f"COMMON\n"
        f"XX-XXXX\n"
        f"XX-XXXX\n"
        f"LESS_COMMON\n"
        f"XX-XXXX\n"
        f"STRETCH\n"
        f"XX-XXXX\n\n"
        f"Rules:\n"
        f"- COMMON: the 3-5 careers graduates of {program_name} at "
        f"{school_name} most frequently enter.\n"
        f"- LESS_COMMON: the next 5-7 plausible careers.\n"
        f"- STRETCH: remaining matches that are possible but atypical "
        f"for this school+major.\n"
        f"- Every SOC code from the list above must appear in exactly "
        f"one tier.\n"
        f"- Output ONLY the header+SOC format. No titles, no "
        f"commentary, no blank lines between entries."
    )


def _parse_tiers(
    text: str,
    soc_lookup: dict[str, CareerOutcome],
) -> OrderedDict[str, list[CareerOutcome]]:
    """Parse Gemma's tiered output into an ordered mapping.

    Walks line-by-line, flips current tier on header lines, and
    extracts SOC codes from content lines. Any SOC not in the lookup
    is silently dropped. Any outcome not placed by Gemma is appended
    to the last tier as a catch-all.
    """
    tiers: OrderedDict[str, list[CareerOutcome]] = OrderedDict()
    for label in _TIER_ORDER:
        tiers[label] = []

    current_tier = TIER_COMMON
    placed_socs: set[str] = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Check for tier header.
        header_match = _TIER_HEADER.match(line)
        if header_match:
            key = line.strip().lower().replace(" ", "_")
            current_tier = _HEADER_TO_LABEL.get(key, current_tier)
            continue
        # Check for SOC code.
        soc_match = _SOC_PATTERN.search(line)
        if soc_match:
            soc = soc_match.group(1)
            if soc in soc_lookup and soc not in placed_socs:
                tiers[current_tier].append(soc_lookup[soc])
                placed_socs.add(soc)

    # Catch-all: any SOC Gemma forgot goes into STRETCH.
    for soc, outcome in soc_lookup.items():
        if soc not in placed_socs:
            tiers[TIER_STRETCH].append(outcome)

    return tiers


def _fallback_tiers(
    outcomes: list[CareerOutcome],
) -> OrderedDict[str, list[CareerOutcome]]:
    """Single flat tier when Gemma fails or returns nothing parseable."""
    tiers: OrderedDict[str, list[CareerOutcome]] = OrderedDict()
    tiers["All career paths"] = list(outcomes)
    return tiers


def tier_careers(
    outcomes: list[CareerOutcome],
    school_name: str,
    program_name: str,
    cipcode: str,
) -> OrderedDict[str, list[CareerOutcome]]:
    """Tier a full crosswalk-matched career list via Gemma.

    Returns an ordered dict: tier label → list of ``CareerOutcome``.
    The CLI renders each tier as a labelled section and numbers
    entries continuously across tiers so the student can pick from
    any tier.

    Skips the Gemma call for ≤5 outcomes since tiering adds no value
    when the list is already short — all land in a single tier.
    """
    if len(outcomes) <= 5:
        return _fallback_tiers(outcomes)

    soc_lookup: dict[str, CareerOutcome] = {o.soc_code: o for o in outcomes}

    text = gemma_client.generate(
        system=_SYSTEM,
        user=_prompt(outcomes, school_name, program_name, cipcode),
        max_tokens=1500,
        temperature=0.2,
    )
    if not text:
        logger.warning("career tiering gen returned empty; using fallback")
        return _fallback_tiers(outcomes)

    tiers = _parse_tiers(text, soc_lookup)

    # If Gemma placed everything in one tier (weird), or placed
    # nothing at all, fall back.
    total_placed = sum(len(v) for v in tiers.values())
    if total_placed == 0:
        logger.warning("career tiering parsed 0 placements; using fallback")
        return _fallback_tiers(outcomes)

    # Prune empty tiers.
    return OrderedDict((k, v) for k, v in tiers.items() if v)
