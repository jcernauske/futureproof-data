"""Stage 3 career branches — related occupations with stat deltas.

Thin wrapper around the MCP ``get_career_branches`` handler. Returns
``CareerBranch`` models suitable for both the CLI branch explorer
menu and the future React branch tree visualization.
"""

from __future__ import annotations

import logging
from typing import Any

from app.models.career import CareerBranch
from app.services import mcp_client

logger = logging.getLogger(__name__)


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(round(value))
    return None


def _derive_ern_delta(row: dict[str, Any]) -> int | None:
    """Career_branches doesn't carry ern_delta directly — derive it
    from the wage delta if available. Uses sign of wage_delta as a
    proxy so a $15k salary bump reads as "+1 ERN" for the CLI."""
    wage_delta = row.get("wage_delta")
    if not isinstance(wage_delta, (int, float)):
        return None
    if wage_delta >= 20_000:
        return 2
    if wage_delta >= 5_000:
        return 1
    if wage_delta <= -20_000:
        return -2
    if wage_delta <= -5_000:
        return -1
    return 0


def _derive_roi_delta(row: dict[str, Any]) -> int | None:
    """ROI shift tracks wage delta minus education creep. Without
    explicit education-delta columns in the branches table, fall
    back to the sign of wage_delta divided by 2."""
    wage_delta = row.get("wage_delta")
    if not isinstance(wage_delta, (int, float)):
        return None
    if wage_delta >= 15_000:
        return 1
    if wage_delta <= -15_000:
        return -1
    return 0


def _format_unlock(row: dict[str, Any]) -> str | None:
    parts: list[str] = []
    education = row.get("related_education_level")
    if education:
        parts.append(str(education))
    tier = row.get("relatedness_tier")
    if tier:
        parts.append(f"{tier} relatedness")
    return " · ".join(parts) if parts else None


def get_branches(
    soc_code: str, *, primary_only: bool = True
) -> list[CareerBranch]:
    """Return Stage 3 branches for a source SOC, sorted by relatedness."""
    result = mcp_client.call(
        "get_career_branches",
        {"soc_code": soc_code, "primary_only": primary_only},
    )
    rows = result.get("data") or []
    if not rows:
        logger.debug(
            "get_branches empty for %s: %s", soc_code, result.get("message")
        )
        return []

    branches: list[CareerBranch] = []
    for row in rows:
        related_soc = row.get("related_soc_code")
        related_title = row.get("related_title")
        if not related_soc or not related_title:
            continue
        branches.append(
            CareerBranch(
                from_soc=str(row.get("soc_code") or soc_code),
                to_soc=str(related_soc),
                to_title=str(related_title),
                delta_ern=_derive_ern_delta(row),
                delta_roi=_derive_roi_delta(row),
                delta_res=_as_int(row.get("res_delta")),
                delta_grw=_as_int(row.get("grw_delta")),
                delta_hmn=_as_int(row.get("hmn_delta")),
                unlock=_format_unlock(row),
                relatedness=row.get("best_index"),
            )
        )

    return branches
