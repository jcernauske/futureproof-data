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
from datetime import datetime, timezone
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
from app.services import db as _db

logger = logging.getLogger(__name__)

# Legacy aliases — kept so test fixtures that monkeypatch these still work.
_conns = _db._conns
_conn_lock = _db._conn_lock


def _db_path():  # type: ignore[override]
    return _db._db_path()


def _conn() -> duckdb.DuckDBPyConnection:
    return _db.conn()


_db.register_schema_initializer(lambda c: _init_schema(c))


def _execute(
    sql: str, params: list[Any] | None = None
) -> list[tuple[Any, ...]]:
    return _db.execute(sql, params)


def _execute_one(
    sql: str, params: list[Any] | None = None
) -> tuple[Any, ...] | None:
    return _db.execute_one(sql, params)


def _execute_write(sql: str, params: list[Any] | None = None) -> None:
    _db.execute_write(sql, params)


def _add_column_if_missing(
    connection: duckdb.DuckDBPyConnection,
    table: str,
    column: str,
    dtype: str,
) -> None:
    cols = connection.execute(
        "SELECT column_name FROM information_schema.columns"
        f" WHERE table_name = '{table}'"
    ).fetchall()
    if column not in {r[0] for r in cols}:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {dtype}")


_ANIMAL_EMOJI_MAP = {
    "bear": "\U0001f43b",
    "bunny": "\U0001f430",
    "turtle": "\U0001f422",
    "chipmunk": "\U0001f43f️",
    "fox": "\U0001f98a",
    "owl": "\U0001f989",
    "penguin": "\U0001f427",
    "cat": "\U0001f431",
}


def _backfill_animal_emoji(connection: duckdb.DuckDBPyConnection) -> None:
    """Patch builds whose JSON data is missing animal_emoji."""
    try:
        rows = connection.execute(
            """SELECT build_id, profile_name, data FROM builds
               WHERE json_extract_string(data, '$.animal_emoji') IS NULL"""
        ).fetchall()
    except duckdb.CatalogException:
        return
    if not rows:
        return
    import json
    for build_id, profile_name, data_str in rows:
        name_lower = (profile_name or "").lower()
        emoji = None
        for animal, em in _ANIMAL_EMOJI_MAP.items():
            if animal in name_lower:
                emoji = em
                break
        if emoji and data_str:
            data = json.loads(data_str)
            data["animal_emoji"] = emoji
            connection.execute(
                "UPDATE builds SET data = ? WHERE build_id = ?",
                [json.dumps(data), build_id],
            )
    logger.info("Backfilled animal_emoji for %d builds", len(rows))


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
            parent_build_id VARCHAR,
            data VARCHAR
        )
        """
    )
    _add_column_if_missing(connection, "builds", "parent_build_id", "VARCHAR")
    _backfill_animal_emoji(connection)
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
    parent_build_id: str | None = None,
    home_state: str | None = None,
    animal_emoji: str | None = None,
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
        parent_build_id=parent_build_id,
        home_state=home_state,
        animal_emoji=animal_emoji,
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
             career_title, ern, roi, res, grw, hmn, wins, losses, draws,
             parent_build_id, data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            build.parent_build_id,
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
               career_title, ern, roi, res, grw, hmn, wins, losses, draws,
               parent_build_id,
               json_extract_string(data, '$.effort') AS effort,
               json_extract(data, '$.loan_pct') AS loan_pct,
               json_extract_string(data, '$.animal_emoji') AS animal_emoji
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
            parent_build_id=r[14],
            effort=r[15] or "balanced",
            loan_pct=float(r[16]) if r[16] is not None else 1.0,
            animal_emoji=r[17],
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
    with _db.get_lock():
        connection = _db.conn()
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
