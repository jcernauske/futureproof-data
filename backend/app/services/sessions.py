"""Session persistence — checkpoint, load, clear.

Stores the student's full session state as a singleton row in DuckDB.
Uses the shared ``db`` module so writes don't collide with ``builds.py``.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.models.api import CheckpointRequest, SessionResponse
from app.models.career import Build
from app.services import db as _db
from app.services.builds import load_build

logger = logging.getLogger(__name__)

_SESSION_ID = "current"


def _init_session_schema(connection: object) -> None:
    import duckdb

    assert isinstance(connection, duckdb.DuckDBPyConnection)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS student_sessions (
            session_id VARCHAR PRIMARY KEY,
            last_screen VARCHAR NOT NULL,
            profile_data VARCHAR,
            build_input_data VARCHAR,
            build_id VARCHAR,
            gauntlet_data VARCHAR,
            tiered_careers_data VARCHAR,
            selected_career_data VARCHAR,
            created_at VARCHAR NOT NULL,
            updated_at VARCHAR NOT NULL
        )
        """
    )


_db.register_schema_initializer(_init_session_schema)


def _json_or_none(data: dict | list | None) -> str | None:
    if data is None:
        return None
    return json.dumps(data)


def _parse_json(raw: str | None) -> dict | list | None:
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def save_checkpoint(request: CheckpointRequest) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _db.execute_write(
        """
        INSERT OR REPLACE INTO student_sessions
            (session_id, last_screen, profile_data, build_input_data,
             build_id, gauntlet_data, tiered_careers_data,
             selected_career_data, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE(
            (SELECT created_at FROM student_sessions WHERE session_id = ?),
            ?
        ), ?)
        """,
        [
            _SESSION_ID,
            request.screen,
            _json_or_none(request.profile_data),
            _json_or_none(request.build_input_data),
            request.build_id,
            _json_or_none(request.gauntlet_data),
            _json_or_none(request.tiered_careers_data),
            _json_or_none(request.selected_career_data),
            _SESSION_ID,
            now,
            now,
        ],
    )


def load_session() -> SessionResponse | None:
    row = _db.execute_one(
        """
        SELECT session_id, last_screen, profile_data, build_input_data,
               build_id, gauntlet_data, tiered_careers_data,
               selected_career_data, created_at, updated_at
        FROM student_sessions
        WHERE session_id = ?
        """,
        [_SESSION_ID],
    )
    if row is None:
        return None

    build: Build | None = None
    if row[4]:
        try:
            build = load_build(row[4])
        except FileNotFoundError:
            logger.warning("Session references missing build %s", row[4])

    return SessionResponse(
        session_id=row[0],
        last_screen=row[1],
        profile_data=_parse_json(row[2]),
        build_input_data=_parse_json(row[3]),
        build_id=row[4],
        build=build,
        gauntlet_data=_parse_json(row[5]),
        tiered_careers_data=_parse_json(row[6]),
        selected_career_data=_parse_json(row[7]),
        created_at=row[8],
        updated_at=row[9],
    )


def clear_session() -> None:
    _db.execute_write(
        "DELETE FROM student_sessions WHERE session_id = ?",
        [_SESSION_ID],
    )
