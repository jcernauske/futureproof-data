from fastapi import APIRouter, HTTPException

from app import state
from app.services import branch_tree, career_tree

router = APIRouter()


@router.get("/branches/{soc}")
async def get_branches(soc: str):
    return branch_tree.get_branches(soc)


@router.get("/tree/{build_id}")
async def get_tree(build_id: str, max_depth: int = 3):
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
        "hmn": node.hmn,
        "median_wage": node.median_wage,
        "education": node.education,
        "boss_ai": node.boss_ai,
        "boss_loans": node.boss_loans,
        "boss_market": node.boss_market,
        "boss_burnout": node.boss_burnout,
        "boss_ceiling": node.boss_ceiling,
        "children": [_node_to_dict(c) for c in node.children],
    }
