from fastapi import APIRouter, HTTPException, Path, Query

from app import state
from app.services import branch_tree, career_tree

router = APIRouter()

# SOC codes follow the BLS XX-XXXX shape exactly. Mirrors the validator
# applied across careers.py and AskScope so unauthenticated path inputs
# never reach the gold-zone DuckDB lookup as arbitrary strings.
_SOC_PATTERN = r"^\d{2}-\d{4}$"

# Hard upper bound on tree depth. The /future screen requests depth=2;
# 4 leaves headroom for future deeper-explore modes without opening the
# door to fan-out abuse on an unauthenticated endpoint.
_MAX_TREE_DEPTH = 4


@router.get("/branches/{soc}")
async def get_branches(soc: str = Path(..., pattern=_SOC_PATTERN)):
    return branch_tree.get_branches(soc)


@router.get("/tree/{build_id}")
async def get_tree(
    build_id: str,
    max_depth: int = Query(3, ge=1, le=_MAX_TREE_DEPTH),
):
    build = state.get_build(build_id)
    if build is None:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")
    root, stats = career_tree.build_tree(build, max_depth=max_depth)
    return {
        "tree": _node_to_dict(root),
        "stats": {
            "total_nodes": stats.total_nodes,
            "max_depth_reached": stats.max_depth_reached,
            "mcp_calls": stats.mcp_calls,
            "dead_ends": stats.dead_ends,
            "wall_clock_ms": stats.wall_clock_ms,
        },
    }


def _node_to_dict(node) -> dict:
    return {
        "soc_code": node.soc_code,
        "title": node.title,
        "level": node.level,
        "ern": node.ern,
        "roi": node.roi,
        "res": node.res,
        "grw": node.grw,
        "aura": node.aura,
        "median_wage": node.median_wage,
        "education": node.education,
        "experience_years": node.experience_years,
        "experience_tier": node.experience_tier,
        "relatedness": node.relatedness,
        "boss_ai": node.boss_ai,
        "boss_loans": node.boss_loans,
        "boss_market": node.boss_market,
        "boss_burnout": node.boss_burnout,
        "boss_ceiling": node.boss_ceiling,
        "children": [_node_to_dict(c) for c in node.children],
    }
