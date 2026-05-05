"""Peer-school leaderboard service.

Thin shaper around ``mcp_client.call("get_schools_for_career", ...)``. The
canonical Gold-zone reader for this surface lives inside
``_handle_get_schools_for_career`` on ``FutureProofMCPServer``; this
service does NOT open DuckDB. Matches the pattern established by
``school_lookup``, ``branch_tree``, ``stat_engine``, ``intent``, and
``ask_gemma``.

See ``docs/specs/feature-compare-schools-for-career.md`` §4.
"""

from __future__ import annotations

from typing import Any

from app.models.career import (
    AnchorBuild,
    ConfidenceTier,
    LeaderboardMode,
    SchoolsForCareerResponse,
)
from app.services import mcp_client


def rank_schools_for_career(
    mode: LeaderboardMode,
    soc_code: str,
    *,
    cipcode: str | None = None,
    limit: int = 10,
    min_confidence: ConfidenceTier = "medium",
    min_program_confidence: ConfidenceTier = "low",
    state_abbr: str | None = None,
    home_state: str | None = None,
    anchor: AnchorBuild | None = None,
    anchor_stat_ern: int | None = None,
    anchor_stat_roi: int | None = None,
) -> SchoolsForCareerResponse:
    """Dispatch the leaderboard query through the MCP server and validate.

    When ``anchor`` is set and ``anchor_stat_ern + anchor_stat_roi`` are both
    provided, the MCP handler counts the build's composite score against the
    filtered universe and returns ``anchor_estimated_rank`` so the frontend
    can render a synthetic anchor row even when the build's CIP-substituted
    program is not materialized in the leaderboard table.
    """
    if mode == "by_cip_and_soc" and not cipcode:
        raise ValueError("cipcode is required when mode='by_cip_and_soc'")

    args: dict[str, Any] = {
        "mode": mode,
        "soc_code": soc_code,
        "limit": limit,
        "min_confidence": min_confidence,
        "min_program_confidence": min_program_confidence,
    }
    if cipcode is not None:
        args["cipcode"] = cipcode
    if state_abbr is not None:
        args["state_abbr"] = state_abbr
    if home_state is not None:
        args["home_state"] = home_state
    if anchor is not None:
        args["build_unitid"] = anchor.unitid
        args["build_cipcode"] = anchor.cipcode
    if anchor_stat_ern is not None:
        args["anchor_stat_ern"] = anchor_stat_ern
    if anchor_stat_roi is not None:
        args["anchor_stat_roi"] = anchor_stat_roi

    raw = mcp_client.call("get_schools_for_career", args)
    if "error" in raw:
        raise ValueError(str(raw.get("error")))
    return SchoolsForCareerResponse.model_validate(raw)
