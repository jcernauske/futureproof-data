"""Spike: dynamic multi-level career tree from O*NET pathway data.

Experimental — answering: how deep can the O*NET data support
branching, what does latency look like, and is the resulting tree
useful or noise?

Builds a tree starting from the primary career, expanding branches
up to 3 levels deep using the career_branches table. Each node
carries absolute stats (GRW, HMN, RES from the branch data) plus
the root build's ROI (school-level, doesn't change). ERN is shown
only for the root since it requires school+program context.

No Gemma calls — pure mechanical data chaining.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from app.models.career import Build
from app.services import boss_fights, mcp_client

logger = logging.getLogger(__name__)


@dataclass
class TreeNode:
    soc_code: str
    title: str
    level: int
    # Stats — None means not available at this depth.
    ern: int | None = None
    roi: int | None = None
    res: int | None = None
    grw: int | None = None
    hmn: int | None = None
    median_wage: float | None = None
    burnout_raw: int | None = None
    ai_boss_raw: int | None = None
    education: str | None = None
    # Boss fight results at this node (computed from absolute stats).
    boss_ai: str | None = None
    boss_loans: str | None = None
    boss_market: str | None = None
    boss_burnout: str | None = None
    boss_ceiling: str | None = None
    # Tree structure.
    children: list[TreeNode] = field(default_factory=list)


@dataclass
class TreeStats:
    total_nodes: int = 0
    max_depth_reached: int = 0
    mcp_calls: int = 0
    dead_ends: int = 0
    nodes_with_full_data: int = 0
    nodes_missing_data: int = 0
    nodes_before_pruning: int = 0
    wall_clock_ms: int = 0


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(round(value))
    return None


def _fetch_raw_branches(soc_code: str) -> list[dict[str, Any]]:
    """Call the MCP handler directly for the full row with absolute stats."""
    result = mcp_client.call(
        "get_career_branches",
        {"soc_code": soc_code, "primary_only": False},
    )
    return result.get("data") or []


def _score_boss(result: str) -> str:
    return {"win": "W", "lose": "L", "draw": "D", "unknown": "?"}.get(
        result, "?"
    )


def _compute_boss_results(node: TreeNode, roi: int | None) -> None:
    """Run the boss scorers against the node's absolute stats.

    Builds a minimal synthetic CareerOutcome just for scoring. Stats
    that are None produce 'unknown' fight results.
    """
    from app.models.career import BossScores, CareerOutcome, PentagonStats

    career = CareerOutcome(
        unitid=0,
        institution_name="",
        cipcode="",
        program_name="",
        soc_code=node.soc_code,
        occupation_title=node.title,
        stats=PentagonStats(
            ern=node.ern,
            roi=roi,
            res=node.res,
            grw=node.grw,
            hmn=node.hmn,
        ),
        bosses=BossScores(
            ai=node.ai_boss_raw,
            loans=None,
            market=None,
            burnout=node.burnout_raw,
            ceiling=None,
        ),
    )
    for boss_id in ("ai", "loans", "market", "burnout", "ceiling"):
        fight = boss_fights.rescore_fight(career, boss_id)
        setattr(node, f"boss_{boss_id}", _score_boss(fight.result))


def _node_has_full_stats(node: TreeNode) -> bool:
    return all(
        v is not None for v in (node.grw, node.hmn, node.res)
    )


def build_tree(
    build: Build,
    *,
    max_depth: int = 3,
) -> tuple[TreeNode, TreeStats]:
    """Build a multi-level career tree from the primary career.

    Returns the root node and a stats summary for spike logging.
    """
    started = time.perf_counter()
    stats = TreeStats()
    career = build.career
    root_roi = career.stats.roi

    root = TreeNode(
        soc_code=career.soc_code,
        title=career.occupation_title,
        level=0,
        ern=career.stats.ern,
        roi=career.stats.roi,
        res=career.stats.res,
        grw=career.stats.grw,
        hmn=career.stats.hmn,
        median_wage=career.median_annual_wage,
        burnout_raw=career.bosses.burnout,
        ai_boss_raw=career.bosses.ai,
    )

    seen: set[str] = {root.soc_code}
    nodes_before_prune = 1

    def expand(node: TreeNode, depth_remaining: int) -> None:
        nonlocal nodes_before_prune
        if depth_remaining <= 0:
            return

        rows = _fetch_raw_branches(node.soc_code)
        stats.mcp_calls += 1

        if not rows:
            if node.level > 0:
                stats.dead_ends += 1
            return

        for row in rows:
            related_soc = row.get("related_soc_code")
            if not related_soc or not row.get("related_title"):
                continue

            nodes_before_prune += 1

            if related_soc in seen:
                continue
            seen.add(related_soc)

            child = TreeNode(
                soc_code=str(related_soc),
                title=str(row.get("related_title")),
                level=node.level + 1,
                ern=None,
                roi=root_roi,
                res=_as_int(row.get("related_res")),
                grw=_as_int(row.get("related_grw")),
                hmn=_as_int(row.get("related_hmn")),
                median_wage=(
                    float(row["related_wage"])
                    if isinstance(row.get("related_wage"), (int, float))
                    else None
                ),
                burnout_raw=_as_int(row.get("related_burnout")),
                ai_boss_raw=_as_int(row.get("related_ai_boss")),
                education=row.get("related_education_level"),
            )
            node.children.append(child)

        for child in node.children:
            expand(child, depth_remaining - 1)

    expand(root, max_depth)

    # Compute boss fight results at every node.
    def walk(node: TreeNode) -> None:
        _compute_boss_results(node, root_roi)
        stats.total_nodes += 1
        if node.level > stats.max_depth_reached:
            stats.max_depth_reached = node.level
        if _node_has_full_stats(node):
            stats.nodes_with_full_data += 1
        else:
            stats.nodes_missing_data += 1
        for child in node.children:
            walk(child)

    walk(root)
    stats.nodes_before_pruning = nodes_before_prune
    stats.wall_clock_ms = int((time.perf_counter() - started) * 1000)
    return root, stats


# ---------------------------------------------------------------------------
# ASCII rendering
# ---------------------------------------------------------------------------

_CONNECTOR_MID = "├── "
_CONNECTOR_LAST = "└── "
_PIPE = "│   "
_SPACE = "    "


def _format_stats(node: TreeNode) -> str:
    parts: list[str] = []
    for label, val in (
        ("ERN", node.ern),
        ("ROI", node.roi),
        ("RES", node.res),
        ("GRW", node.grw),
        ("HMN", node.hmn),
    ):
        parts.append(f"{label} {val}" if val is not None else f"{label} —")
    return ", ".join(parts)


def _format_bosses(node: TreeNode) -> str:
    parts: list[str] = []
    for label, val in (
        ("AI", node.boss_ai),
        ("Loans", node.boss_loans),
        ("Mkt", node.boss_market),
        ("Burn", node.boss_burnout),
        ("Ceil", node.boss_ceiling),
    ):
        parts.append(f"{label}:{val or '?'}")
    return " ".join(parts)


def render_tree(root: TreeNode) -> str:
    """Render the tree as an ASCII string for CLI display."""
    lines: list[str] = []

    def _render(node: TreeNode, prefix: str, is_last: bool, is_root: bool) -> None:
        connector = "" if is_root else (_CONNECTOR_LAST if is_last else _CONNECTOR_MID)
        wage = f"${int(node.median_wage):,}" if node.median_wage else "—"
        stat_str = _format_stats(node)
        boss_str = _format_bosses(node)
        lines.append(
            f"{prefix}{connector}{node.title} ({stat_str})  "
            f"[{boss_str}]  {wage}"
        )
        child_prefix = prefix + ("" if is_root else (_SPACE if is_last else _PIPE))
        for i, child in enumerate(node.children):
            _render(child, child_prefix, i == len(node.children) - 1, False)

    _render(root, "", True, True)
    return "\n".join(lines)


def format_summary(stats: TreeStats) -> str:
    coverage = (
        f"{stats.nodes_with_full_data}/{stats.total_nodes} "
        f"({100 * stats.nodes_with_full_data // max(stats.total_nodes, 1)}%)"
    )
    return (
        f"Tree summary:\n"
        f"  Total nodes:        {stats.total_nodes}\n"
        f"  Before pruning:     {stats.nodes_before_pruning}\n"
        f"  Max depth reached:  {stats.max_depth_reached}\n"
        f"  Dead ends (L1+):    {stats.dead_ends}\n"
        f"  MCP lookups:        {stats.mcp_calls}\n"
        f"  Data coverage:      {coverage}\n"
        f"  Wall clock:         {stats.wall_clock_ms}ms"
    )
