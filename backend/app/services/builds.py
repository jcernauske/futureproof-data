"""Save, load, list, and compare CLI builds.

Builds live as JSON files at ``backend/data/builds/<build_id>.json``.
The directory is created on first write. The frontend will eventually
read from a database or API endpoint, but the CLI harness only needs
filesystem persistence.

Build IDs are short, human-readable slugs (``iub-marketing-001``)
that stay stable across runs so the compare flow can reference
builds by name rather than UUID.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app.models.career import (
    AppliedSkill,
    Build,
    BuildSummary,
    CareerBranch,
    CareerOutcome,
    EffortLevel,
    GauntletResult,
    SkillRec,
)
from app.services.mcp_client import project_root

logger = logging.getLogger(__name__)


def _builds_dir() -> Path:
    root = project_root() / "backend" / "data" / "builds"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "build"


def _next_id_for(base: str) -> str:
    directory = _builds_dir()
    existing = [p.stem for p in directory.glob(f"{base}-*.json")]
    used_numbers: set[int] = set()
    for stem in existing:
        suffix = stem.rsplit("-", 1)[-1]
        if suffix.isdigit():
            used_numbers.add(int(suffix))
    counter = 1
    while counter in used_numbers:
        counter += 1
    return f"{base}-{counter:03d}"


def build_from_parts(
    *,
    school_name: str,
    unitid: int,
    major_text: str,
    cipcode: str,
    program_name: str,
    effort: EffortLevel,
    career: CareerOutcome,
    gauntlet: GauntletResult,
    branches: list[CareerBranch],
    skill_recs: list[SkillRec],
    guidance: str,
    loan_pct: float = 1.0,
    skills_crafted: list[AppliedSkill] | None = None,
    skill_pool: list[AppliedSkill] | None = None,
) -> Build:
    base = _slug(f"{school_name}-{major_text}")
    build_id = _next_id_for(base)
    return Build(
        build_id=build_id,
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        school_name=school_name,
        unitid=unitid,
        major_text=major_text,
        cipcode=cipcode,
        program_name=program_name,
        effort=effort,
        loan_pct=loan_pct,
        career=career,
        gauntlet=gauntlet,
        branches=branches,
        skill_recs=skill_recs,
        guidance=guidance,
        skills_crafted=list(skills_crafted) if skills_crafted else [],
        skill_pool=list(skill_pool) if skill_pool else [],
    )


def save_build(build: Build) -> Path:
    path = _builds_dir() / f"{build.build_id}.json"
    path.write_text(
        json.dumps(build.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    return path


def load_build(build_id: str) -> Build:
    path = _builds_dir() / f"{build_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"No build with id {build_id!r}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Build.model_validate(raw)


def list_builds() -> list[BuildSummary]:
    summaries: list[BuildSummary] = []
    for path in sorted(_builds_dir().glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            build = Build.model_validate(raw)
        except Exception as exc:
            logger.debug("skipping unreadable build %s: %s", path, exc)
            continue
        summaries.append(
            BuildSummary(
                build_id=build.build_id,
                created_at=build.created_at,
                school_name=build.school_name,
                major_text=build.major_text,
                career_title=build.career.occupation_title,
                ern=build.career.stats.ern,
                roi=build.career.stats.roi,
                res=build.career.stats.res,
                grw=build.career.stats.grw,
                hmn=build.career.stats.hmn,
                wins=build.gauntlet.wins,
                losses=build.gauntlet.losses,
            )
        )
    summaries.sort(key=lambda s: s.created_at, reverse=True)
    return summaries


def compare_builds(build_ids: list[str]) -> dict[str, Any]:
    """Return a dict with per-stat side-by-side for 2-3 builds.

    Not a Pydantic model because the CLI renders it via ``rich.Table``
    directly and the shape is flexible. When the API ships, this will
    become a proper ``ComparisonResult`` model.
    """
    builds = [load_build(bid) for bid in build_ids]
    if not builds:
        return {"builds": [], "rows": []}

    def _stat_values(getter: Callable[[Build], int | None]) -> list[int | None]:
        return [getter(b) for b in builds]

    stat_rows: list[dict[str, Any]] = [
        {"label": "ERN", "values": _stat_values(lambda b: b.career.stats.ern)},
        {"label": "ROI", "values": _stat_values(lambda b: b.career.stats.roi)},
        {"label": "RES", "values": _stat_values(lambda b: b.career.stats.res)},
        {"label": "GRW", "values": _stat_values(lambda b: b.career.stats.grw)},
        {"label": "HMN", "values": _stat_values(lambda b: b.career.stats.hmn)},
    ]

    boss_rows: list[dict[str, Any]] = []
    boss_ids = ["ai", "loans", "market", "burnout", "ceiling"]
    boss_labels = {
        "ai": "AI",
        "loans": "Loans",
        "market": "Market",
        "burnout": "Burnout",
        "ceiling": "Ceiling",
    }
    for boss_id in boss_ids:
        row_values: list[str] = []
        for build in builds:
            match = next(
                (f for f in build.gauntlet.fights if f.boss == boss_id),
                None,
            )
            row_values.append(match.result.upper() if match else "—")
        boss_rows.append({"label": boss_labels[boss_id], "values": row_values})

    return {
        "builds": [
            {
                "build_id": b.build_id,
                "label": f"{b.school_name} — {b.major_text}",
                "career": b.career.occupation_title,
            }
            for b in builds
        ],
        "stats": stat_rows,
        "bosses": boss_rows,
    }
