"""School search, program listing, and major-to-CIP resolution.

``search_schools`` and ``get_programs`` are DuckDB-backed queries routed
through the MCP server's ``get_school_programs`` handler. ``resolve_major``
runs the four-step match flow described in the spec: exact program name,
substring, YAML lookup, Gemma fallback.

Gemma is only called for majors that miss every deterministic path —
the YAML lookup already covers CIP family 52 (Business) end-to-end.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

from app.models.career import MajorMatch, Program, SchoolMatch
from app.services import gemma_client, mcp_client

logger = logging.getLogger(__name__)

_SCHOOL_SEARCH_LIMIT = 10
_GEMMA_RESOLVE_SYSTEM = (
    "You map a student's stated college major to a CIP code. Respond "
    "with ONLY a 4-digit CIP in XX.XX format (e.g. 52.14). If no "
    "program in the list is a reasonable match, respond with NONE."
)


def _rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    data = result.get("data")
    if isinstance(data, list):
        return data
    return []


def search_schools(query: str) -> list[SchoolMatch]:
    """Fuzzy-match schools by institution name.

    Returns up to 10 distinct ``(unitid, institution_name)`` rows. The
    underlying MCP handler scans ``consumable.career_outcomes`` and
    filters by case-insensitive substring, so "iu" returns every
    Indiana University campus.
    """
    query = (query or "").strip()
    if not query:
        return []

    result = mcp_client.call("get_school_programs", {"school_name": query})
    rows = _rows(result)
    if not rows:
        logger.debug("search_schools empty result for %r", query)
        return []

    seen: dict[int, SchoolMatch] = {}
    for row in rows:
        unitid = row.get("unitid")
        name = row.get("institution_name")
        if not isinstance(unitid, int) or not name:
            continue
        if unitid not in seen:
            seen[unitid] = SchoolMatch(
                unitid=unitid,
                institution_name=str(name),
                institution_control=row.get("institution_control"),
                net_price_annual=row.get("net_price_annual"),
                cost_of_attendance_annual=row.get("cost_of_attendance_annual"),
            )
        if len(seen) >= _SCHOOL_SEARCH_LIMIT:
            break

    return sorted(seen.values(), key=lambda s: s.institution_name)


def get_programs(
    unitid: int, *, min_confidence: str = "insufficient"
) -> list[Program]:
    """List every program at a school, sorted by program name."""
    result = mcp_client.call(
        "get_school_programs",
        {"school_name": str(unitid), "min_confidence": min_confidence},
    )
    rows = _rows(result)
    programs: list[Program] = []
    for row in rows:
        try:
            programs.append(
                Program(
                    unitid=int(row["unitid"]),
                    institution_name=str(row.get("institution_name") or ""),
                    cipcode=str(row["cipcode"]),
                    program_name=str(row.get("program_name") or ""),
                    cip_family_name=row.get("cip_family_name"),
                    earnings_1yr_median=row.get("earnings_1yr_median"),
                    debt_median=row.get("debt_median"),
                    confidence_tier=row.get("confidence_tier"),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            logger.debug("skipping malformed program row: %s", exc)
    programs.sort(key=lambda p: p.program_name.lower())
    return programs


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _exact_match(major_text: str, programs: list[Program]) -> Program | None:
    target = _normalize(major_text)
    for program in programs:
        if _normalize(program.program_name) == target:
            return program
    return None


def _substring_match(major_text: str, programs: list[Program]) -> Program | None:
    target = _normalize(major_text)
    if len(target) < 3:
        return None
    for program in programs:
        name = _normalize(program.program_name)
        if target in name or name in target:
            return program
    return None


def _yaml_lookup(major_text: str) -> dict[str, Any] | None:
    """Defer to the MCP server's cached major->CIP table.

    Reuses the exact lookup logic the ``get_career_paths`` handler runs
    so CLI matches align with MCP tool matches row-for-row.
    """
    server = mcp_client.get_server()
    finder = getattr(server, "_find_major_intent", None)
    if finder is None:
        return None
    try:
        entry = finder(major_text)
    except Exception as exc:
        logger.debug("yaml lookup fail: %s", exc)
        return None
    if not entry:
        return None
    return dict(entry)


def _gemma_fallback(
    major_text: str, programs: Iterable[Program]
) -> Program | None:
    """Last-resort resolution when neither exact, substring, nor YAML hit."""
    program_lines = [
        f"- {p.cipcode} {p.program_name}" for p in list(programs)[:80]
    ]
    if not program_lines:
        return None
    user = (
        f"Student major: {major_text}\n\n"
        f"Programs offered:\n" + "\n".join(program_lines)
    )
    response = gemma_client.generate(
        system=_GEMMA_RESOLVE_SYSTEM, user=user, max_tokens=16, temperature=0.0
    )
    response = response.strip().split()[0] if response else ""
    if not response or response.upper() == "NONE":
        return None
    programs_list = list(programs)
    for program in programs_list:
        if program.cipcode == response:
            return program
    # Retry loose: match on 4-digit prefix.
    prefix = response.split(".")[0] if "." in response else ""
    if prefix:
        for program in programs_list:
            if program.cipcode.startswith(prefix):
                return program
    return None


def resolve_major(major_text: str, programs: list[Program]) -> MajorMatch:
    """Match a typed major to one of the school's programs.

    Flow, in order:

    1. Exact (case-insensitive) match against ``program_name``.
    2. Substring either direction (typed text in program name or vice versa).
    3. YAML intent table (``data/reference/major_to_cip.yaml``). Returns a
       substitution-flagged match — stats will be the school's broad CIP
       but career paths will reflect the matched specific program.
    4. Gemma fallback for anything unmapped by steps 1-3.

    Returns ``MajorMatch(method='unmatched')`` if nothing hits.
    """
    major_text = (major_text or "").strip()
    if not major_text:
        return MajorMatch(method="unmatched", note="No major provided")

    # Safety net: pure-digit input is almost certainly a menu-index
    # mistake, not a real major. Kick it back as unmatched so the
    # Gemma CIP mapper never sees "Student major: 2" and hallucinates.
    # The CLI layer is responsible for resolving numeric input to a
    # program via ``programs[idx - 1]`` before calling this function.
    if major_text.isdigit():
        return MajorMatch(
            method="unmatched",
            note=(
                f"'{major_text}' looks like a menu number, not a major "
                f"name. Type the major itself (e.g. 'Marketing') or "
                f"'list' to see the program table with picker numbers."
            ),
        )

    exact = _exact_match(major_text, programs)
    if exact is not None:
        return MajorMatch(
            method="exact",
            cipcode=exact.cipcode,
            program_name=exact.program_name,
        )

    substring = _substring_match(major_text, programs)
    if substring is not None:
        return MajorMatch(
            method="substring",
            cipcode=substring.cipcode,
            program_name=substring.program_name,
        )

    entry = _yaml_lookup(major_text)
    if entry is not None:
        cip4 = str(entry.get("cip4") or "")
        matched_name = str(entry.get("major") or major_text)
        family_prefix = cip4[:2]
        reported_broad = next(
            (
                p.cipcode
                for p in programs
                if p.cipcode.startswith(family_prefix)
                and p.cipcode.endswith(".01")
            ),
            None,
        )
        return MajorMatch(
            method="yaml",
            cipcode=cip4,
            program_name=matched_name,
            substitution_applied=reported_broad is not None,
            reported_cipcode=reported_broad,
            substituted_cipcode=cip4,
            note=(
                f"Mapped via intent lookup to {matched_name} ({cip4})."
                if reported_broad is None
                else (
                    f"School reports {reported_broad}; substituting to "
                    f"{cip4} for career paths."
                )
            ),
        )

    gemma_match = _gemma_fallback(major_text, programs)
    if gemma_match is not None:
        return MajorMatch(
            method="gemma",
            cipcode=gemma_match.cipcode,
            program_name=gemma_match.program_name,
            note="Matched by Gemma fallback.",
        )

    return MajorMatch(
        method="unmatched",
        note=(
            f"Could not resolve '{major_text}' to any program at this "
            f"school. Try typing the full program name."
        ),
    )
