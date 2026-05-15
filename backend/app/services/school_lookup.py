"""School search and program listing.

``search_schools`` and ``get_programs`` are DuckDB-backed queries routed
through the MCP server's ``get_school_programs`` handler.
"""

from __future__ import annotations

import logging
from typing import Any

from app.models.career import Program, SchoolMatch
from app.services import mcp_client

logger = logging.getLogger(__name__)

_SCHOOL_SEARCH_LIMIT = 10


def _rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    data = result.get("data")
    if isinstance(data, list):
        return data
    return []


def search_schools(query: str) -> list[SchoolMatch]:
    """Fuzzy-match schools by institution name.

    Returns up to 10 distinct ``(unitid, institution_name)`` rows. The
    underlying MCP handler normalizes punctuation (hyphens, commas,
    apostrophes) before substring matching, and additionally tests
    short queries as first-letter acronyms — so "Indiana University
    Bloomington" matches the hyphenated canonical name, and "IU",
    "UIUC", "MIT", and "ISU" all resolve to their schools.
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
                state_abbr=row.get("state_abbr"),
                net_price_annual=row.get("net_price_annual"),
                cost_of_attendance_annual=row.get("cost_of_attendance_annual"),
                tuition_in_state=row.get("tuition_in_state"),
                tuition_out_of_state=row.get("tuition_out_of_state"),
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


