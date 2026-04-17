"""Save, load, list, and compare builds via DuckDB.

Builds persist in a single DuckDB database at
``backend/data/futureproof.duckdb`` — separate from the Brightsmith Gold
zone DB at ``data/futureproof.duckdb``. Application state never
pollutes pipeline products.

Build IDs are short, human-readable slugs (``iu-b-marketing-001``) so
the compare flow can reference builds by name rather than UUID.

Wrapped frames (rendered 1080×1920 PNGs) live in a sibling
``wrapped_frames`` table as BLOBs keyed by (build_id, frame_index).

Module state: a connection cache keyed by DB path so tests can swap in
a tmp DB via ``monkeypatch.setattr(builds, "_db_path", ...)``.
"""

from __future__ import annotations

import logging
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import duckdb

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

_conns: dict[Path, duckdb.DuckDBPyConnection] = {}
# RLock because _init_schema calls execute recursively while we already hold
# the lock in _conn(). DuckDB's Python connection isn't thread-safe — every
# SQL operation must hold this lock for the entire execute+fetch window.
_conn_lock = threading.RLock()


def _db_path() -> Path:
    root = project_root() / "backend" / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root / "futureproof.duckdb"


def _conn() -> duckdb.DuckDBPyConnection:
    with _conn_lock:
        path = _db_path()
        if path not in _conns:
            connection = duckdb.connect(str(path))
            _init_schema(connection)
            _conns[path] = connection
        return _conns[path]


def _execute(
    sql: str, params: list[Any] | None = None
) -> list[tuple[Any, ...]]:
    """Run a query and return all rows. Holds the connection lock."""
    with _conn_lock:
        return _conn().execute(sql, params or []).fetchall()


def _execute_one(
    sql: str, params: list[Any] | None = None
) -> tuple[Any, ...] | None:
    """Run a query and return the first row, or None. Holds the connection lock."""
    with _conn_lock:
        return _conn().execute(sql, params or []).fetchone()


def _execute_write(sql: str, params: list[Any] | None = None) -> None:
    """Run a write with no return. Holds the connection lock."""
    with _conn_lock:
        _conn().execute(sql, params or [])


def _init_schema(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS builds (
            build_id VARCHAR PRIMARY KEY,
            profile_name VARCHAR,
            created_at VARCHAR,
            school_name VARCHAR,
            major_text VARCHAR,
            career_title VARCHAR,
            ern INTEGER,
            roi INTEGER,
            res INTEGER,
            grw INTEGER,
            hmn INTEGER,
            wins INTEGER,
            losses INTEGER,
            draws INTEGER,
            data VARCHAR
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS wrapped_frames (
            build_id VARCHAR,
            frame_index INTEGER,
            png_data BLOB,
            rendered_at VARCHAR,
            PRIMARY KEY (build_id, frame_index)
        )
        """
    )


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "build"


def _next_id_for(base: str) -> str:
    rows = _execute(
        "SELECT build_id FROM builds WHERE build_id LIKE ?",
        [f"{base}-%"],
    )
    used_numbers: set[int] = set()
    for (bid,) in rows:
        suffix = bid.rsplit("-", 1)[-1]
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
    profile_name: str = "",
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
        profile_name=profile_name,
    )


def save_build(build: Build) -> None:
    """Upsert a build into DuckDB.

    Reads ``profile_name`` from ``build.profile_name`` — single source
    of truth. Existing rows with the same ``build_id`` are replaced.
    """
    _execute_write(
        """
        INSERT OR REPLACE INTO builds
            (build_id, profile_name, created_at, school_name, major_text,
             career_title, ern, roi, res, grw, hmn, wins, losses, draws, data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            build.build_id,
            build.profile_name,
            build.created_at,
            build.school_name,
            build.major_text,
            build.career.occupation_title,
            build.career.stats.ern,
            build.career.stats.roi,
            build.career.stats.res,
            build.career.stats.grw,
            build.career.stats.hmn,
            build.gauntlet.wins,
            build.gauntlet.losses,
            build.gauntlet.draws,
            build.model_dump_json(),
        ],
    )


def load_build(build_id: str) -> Build:
    """Load a build by ID.

    Raises:
        FileNotFoundError: if no row exists with that build_id. This
            contract is relied on by ``app.state.get_build`` which
            catches FileNotFoundError as its cache-miss signal.
    """
    try:
        row = _execute_one(
            "SELECT data FROM builds WHERE build_id = ?",
            [build_id],
        )
    except duckdb.CatalogException as exc:
        raise FileNotFoundError(f"No build with id {build_id!r}") from exc
    if row is None:
        raise FileNotFoundError(f"No build with id {build_id!r}")
    return Build.model_validate_json(row[0])


def list_builds(profile_name: str | None = None) -> list[BuildSummary]:
    """List build summaries, newest first.

    When ``profile_name`` is provided, filters to that profile. When None
    (default), returns every build — matches the CLI's current behavior
    of showing all builds regardless of profile.
    """
    query = """
        SELECT build_id, profile_name, created_at, school_name, major_text,
               career_title, ern, roi, res, grw, hmn, wins, losses, draws
        FROM builds
    """
    params: list[str] = []
    if profile_name is not None:
        query += " WHERE profile_name = ?"
        params.append(profile_name)
    query += " ORDER BY created_at DESC"
    rows = _execute(query, params)
    return [
        BuildSummary(
            build_id=r[0],
            profile_name=r[1] or "",
            created_at=r[2] or "",
            school_name=r[3] or "",
            major_text=r[4] or "",
            career_title=r[5] or "",
            ern=r[6],
            roi=r[7],
            res=r[8],
            grw=r[9],
            hmn=r[10],
            wins=r[11] or 0,
            losses=r[12] or 0,
            draws=r[13] or 0,
        )
        for r in rows
    ]


def compare_builds(build_ids: list[str]) -> dict[str, Any]:
    """Return a dict with per-stat side-by-side for 2-3 builds."""
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


def save_wrapped_frames(build_id: str, frames: list[tuple[int, bytes]]) -> None:
    """Persist all rendered frame PNGs as BLOBs atomically.

    Wraps DELETE + INSERTs in a BEGIN/COMMIT transaction so a concurrent
    render for the same ``build_id`` cannot observe a half-written state
    (e.g., 3 new frames + 3 stale frames). On any error, the transaction
    is rolled back and the prior frames remain intact.

    All 6 frames share a single ``rendered_at`` timestamp so the cache
    freshness check (`wrapped_frames_rendered_at` vs `build.created_at`)
    is unambiguous.
    """
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _conn_lock:
        connection = _conn()
        connection.execute("BEGIN TRANSACTION")
        try:
            connection.execute(
                "DELETE FROM wrapped_frames WHERE build_id = ?",
                [build_id],
            )
            for idx, data in frames:
                connection.execute(
                    """
                    INSERT INTO wrapped_frames
                        (build_id, frame_index, png_data, rendered_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    [build_id, idx, data, now],
                )
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise


def load_wrapped_frame(build_id: str, frame_index: int) -> bytes:
    """Fetch a single frame PNG. Raises FileNotFoundError on miss."""
    row = _execute_one(
        "SELECT png_data FROM wrapped_frames WHERE build_id = ? AND frame_index = ?",
        [build_id, frame_index],
    )
    if row is None:
        raise FileNotFoundError(
            f"No frame {frame_index} for build {build_id!r}"
        )
    return bytes(row[0])


def list_wrapped_frames(build_id: str) -> list[int]:
    """Return frame indices available for a build (0–5). Empty when not rendered."""
    rows = _execute(
        """
        SELECT frame_index FROM wrapped_frames
        WHERE build_id = ?
        ORDER BY frame_index
        """,
        [build_id],
    )
    return [r[0] for r in rows]


def wrapped_frames_rendered_at(build_id: str) -> str | None:
    """Latest rendered_at timestamp across a build's frames, or None."""
    row = _execute_one(
        "SELECT MAX(rendered_at) FROM wrapped_frames WHERE build_id = ?",
        [build_id],
    )
    return row[0] if row and row[0] else None
