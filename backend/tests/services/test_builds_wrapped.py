"""Tests for the wrapped_frames BLOB persistence + profile_name filter.

Covers the new DuckDB functions introduced by screen-save-wrapped.md:
- save_wrapped_frames / load_wrapped_frame / list_wrapped_frames
- wrapped_frames_rendered_at (freshness vs Build.created_at)
- list_builds(profile_name=...) filter

Uses the `isolated_builds_dir` fixture from conftest.py so the real
DuckDB file is never touched.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.career import (
    BossFightResult,
    BossScores,
    Build,
    CareerBranch,
    CareerOutcome,
    GauntletResult,
    PentagonStats,
    SkillRec,
)
from app.services import builds

# --- Fixtures --------------------------------------------------------------


def _career() -> CareerOutcome:
    return CareerOutcome(
        unitid=151351,
        institution_name="Indiana University-Bloomington",
        cipcode="52.14",
        program_name="Marketing",
        soc_code="13-1131",
        occupation_title="Fundraisers",
        stats=PentagonStats(ern=8, roi=9, res=4, grw=6, hmn=6),
        bosses=BossScores(ai=7, loans=None, market=7, burnout=6, ceiling=None),
        median_annual_wage=66490.0,
    )


def _gauntlet() -> GauntletResult:
    return GauntletResult(
        fights=[
            BossFightResult(
                boss="ai",  # type: ignore[arg-type]
                label="Fight AI",
                result="win",  # type: ignore[arg-type]
                raw_score=16,
                threshold_win=14,
                threshold_draw=10,
                reason="test",
            )
        ],
        wins=1,
        losses=0,
        draws=0,
        unknown=0,
        verdict="TEST",
    )


def _make_build(*, profile_name: str = "", school: str = "IU-B") -> Build:
    return builds.build_from_parts(
        school_name=school,
        unitid=151351,
        major_text="Marketing",
        cipcode="52.14",
        program_name="Marketing",
        effort="balanced",
        career=_career(),
        gauntlet=_gauntlet(),
        branches=[
            CareerBranch(
                from_soc="13-1131",
                to_soc="11-2011",
                to_title="Advertising Managers",
                delta_ern=2,
            )
        ],
        skill_recs=[SkillRec(title="Data", stat_impact="RES+1", rationale="x")],
        guidance="g",
        profile_name=profile_name,
    )


# --- save_wrapped_frames / load_wrapped_frame ------------------------------


class TestWrappedFrameRoundTrip:
    def test_save_and_load_single_frame(self, isolated_builds_dir):
        build = _make_build()
        builds.save_build(build)
        frames = [(0, b"\x89PNG\r\n\x1a\npayload-0")]
        builds.save_wrapped_frames(build.build_id, frames)

        loaded = builds.load_wrapped_frame(build.build_id, 0)
        assert loaded == b"\x89PNG\r\n\x1a\npayload-0"

    def test_save_and_load_all_six_frames(self, isolated_builds_dir):
        """Round-trip the full Wrapped sequence (6 distinct BLOBs)."""
        build = _make_build()
        builds.save_build(build)
        frames = [
            (i, f"frame-{i}-bytes".encode("utf-8")) for i in range(6)
        ]
        builds.save_wrapped_frames(build.build_id, frames)

        for i in range(6):
            assert builds.load_wrapped_frame(build.build_id, i) == (
                f"frame-{i}-bytes".encode("utf-8")
            )

    def test_load_missing_frame_raises_file_not_found(
        self, isolated_builds_dir
    ):
        """Critical: state.py-style callers rely on FileNotFoundError."""
        build = _make_build()
        builds.save_build(build)
        # No save_wrapped_frames called — nothing stored
        with pytest.raises(FileNotFoundError):
            builds.load_wrapped_frame(build.build_id, 0)

    def test_load_frame_for_unknown_build_raises(
        self, isolated_builds_dir
    ):
        with pytest.raises(FileNotFoundError):
            builds.load_wrapped_frame("does-not-exist-999", 0)

    def test_load_out_of_range_frame_raises(self, isolated_builds_dir):
        """frame_index=99 is nonsense even if frames 0..5 exist."""
        build = _make_build()
        builds.save_build(build)
        builds.save_wrapped_frames(
            build.build_id, [(i, b"x") for i in range(6)]
        )
        with pytest.raises(FileNotFoundError):
            builds.load_wrapped_frame(build.build_id, 99)

    def test_large_binary_payload_round_trips_intact(
        self, isolated_builds_dir
    ):
        """Simulate a ~250KB PNG — DuckDB BLOB must not mangle bytes."""
        build = _make_build()
        builds.save_build(build)
        payload = bytes(range(256)) * 1024  # 256KB of all byte values
        builds.save_wrapped_frames(build.build_id, [(0, payload)])

        loaded = builds.load_wrapped_frame(build.build_id, 0)
        assert loaded == payload
        assert len(loaded) == 256 * 1024


# --- save_wrapped_frames replace-on-resave ---------------------------------


class TestWrappedFrameReplace:
    def test_second_save_replaces_first(self, isolated_builds_dir):
        """The DELETE-then-INSERT contract: re-rendering does NOT accumulate.

        Regression guard: without the DELETE, the PK constraint would
        raise; or with an UPSERT pattern, stale frame bytes could leak.
        """
        build = _make_build()
        builds.save_build(build)

        old = [(i, f"old-{i}".encode()) for i in range(6)]
        builds.save_wrapped_frames(build.build_id, old)

        new = [(i, f"new-{i}".encode()) for i in range(6)]
        builds.save_wrapped_frames(build.build_id, new)

        for i in range(6):
            assert builds.load_wrapped_frame(build.build_id, i) == (
                f"new-{i}".encode()
            )

    def test_resave_with_fewer_frames_drops_old_ones(
        self, isolated_builds_dir
    ):
        """If a rerender produces only 3 frames, old frames 3..5 must go."""
        build = _make_build()
        builds.save_build(build)

        builds.save_wrapped_frames(
            build.build_id, [(i, b"v1") for i in range(6)]
        )
        assert builds.list_wrapped_frames(build.build_id) == [0, 1, 2, 3, 4, 5]

        builds.save_wrapped_frames(
            build.build_id, [(i, b"v2") for i in range(3)]
        )
        # Old 3..5 must be gone
        assert builds.list_wrapped_frames(build.build_id) == [0, 1, 2]
        with pytest.raises(FileNotFoundError):
            builds.load_wrapped_frame(build.build_id, 3)

    def test_resave_does_not_affect_other_build_frames(
        self, isolated_builds_dir
    ):
        """Only the target build_id's frames are replaced."""
        a = _make_build(school="IU-B")
        builds.save_build(a)
        b = _make_build(school="Purdue")
        builds.save_build(b)
        assert a.build_id != b.build_id
        builds.save_wrapped_frames(a.build_id, [(0, b"a-original")])
        builds.save_wrapped_frames(b.build_id, [(0, b"b-original")])

        builds.save_wrapped_frames(a.build_id, [(0, b"a-rewritten")])

        # b's frames untouched
        assert builds.load_wrapped_frame(b.build_id, 0) == b"b-original"
        assert builds.load_wrapped_frame(a.build_id, 0) == b"a-rewritten"

    def test_save_empty_frames_list_clears_existing(
        self, isolated_builds_dir
    ):
        """Edge: passing [] should DELETE existing frames and store nothing."""
        build = _make_build()
        builds.save_build(build)
        builds.save_wrapped_frames(
            build.build_id, [(i, b"x") for i in range(6)]
        )
        assert len(builds.list_wrapped_frames(build.build_id)) == 6

        builds.save_wrapped_frames(build.build_id, [])

        assert builds.list_wrapped_frames(build.build_id) == []


# --- list_wrapped_frames ---------------------------------------------------


class TestListWrappedFrames:
    def test_returns_empty_when_unrendered(self, isolated_builds_dir):
        build = _make_build()
        builds.save_build(build)
        assert builds.list_wrapped_frames(build.build_id) == []

    def test_returns_empty_for_unknown_build(self, isolated_builds_dir):
        """Unknown build_id is an empty list — NOT an error — by design.

        The wrapped router uses this as a signal for 409 "render first",
        so any exception here would break the endpoint contract.
        """
        assert builds.list_wrapped_frames("unknown-build-xyz") == []

    def test_returns_all_indices_sorted(self, isolated_builds_dir):
        build = _make_build()
        builds.save_build(build)
        # Insert in reverse order — result must still be sorted
        builds.save_wrapped_frames(
            build.build_id,
            [(5, b"5"), (2, b"2"), (0, b"0"), (1, b"1"), (4, b"4"), (3, b"3")],
        )

        assert builds.list_wrapped_frames(build.build_id) == [0, 1, 2, 3, 4, 5]

    def test_partial_render_returns_only_available_indices(
        self, isolated_builds_dir
    ):
        """Crash mid-render scenario: only 3 frames landed."""
        build = _make_build()
        builds.save_build(build)
        builds.save_wrapped_frames(
            build.build_id, [(0, b"a"), (1, b"b"), (2, b"c")]
        )

        assert builds.list_wrapped_frames(build.build_id) == [0, 1, 2]


# --- wrapped_frames_rendered_at --------------------------------------------


class TestWrappedFramesRenderedAt:
    def test_none_when_no_frames(self, isolated_builds_dir):
        build = _make_build()
        builds.save_build(build)
        assert builds.wrapped_frames_rendered_at(build.build_id) is None

    def test_none_for_unknown_build(self, isolated_builds_dir):
        assert builds.wrapped_frames_rendered_at("no-such-build") is None

    def test_returns_iso_timestamp_after_save(self, isolated_builds_dir):
        build = _make_build()
        builds.save_build(build)
        before = datetime.now(timezone.utc)
        builds.save_wrapped_frames(build.build_id, [(0, b"x")])
        after = datetime.now(timezone.utc)

        ts = builds.wrapped_frames_rendered_at(build.build_id)
        assert ts is not None
        parsed = datetime.fromisoformat(ts)
        # Spec stamps with timespec="seconds"; allow 1s slack both ways
        assert (before - timedelta(seconds=1)) <= parsed <= (
            after + timedelta(seconds=1)
        )

    def test_all_frames_share_the_same_rendered_at(
        self, isolated_builds_dir
    ):
        """Freshness logic relies on a SINGLE timestamp per render batch.

        If different frames had different rendered_at values the
        cache-freshness check (MAX(rendered_at) vs build.created_at) could
        be fooled by a partial in-flight re-render. All six frames in one
        call must get the same timestamp.
        """
        build = _make_build()
        builds.save_build(build)
        builds.save_wrapped_frames(
            build.build_id, [(i, b"x") for i in range(6)]
        )

        # Query each row's rendered_at directly
        rows = builds._conn().execute(
            "SELECT rendered_at FROM wrapped_frames WHERE build_id = ?",
            [build.build_id],
        ).fetchall()
        timestamps = {r[0] for r in rows}
        assert len(timestamps) == 1, (
            f"All frames in one render batch should share a timestamp; "
            f"got {timestamps}"
        )

    def test_rendered_at_fresher_than_build_created_at(
        self, isolated_builds_dir
    ):
        """After saving a build then rendering, rendered_at >= created_at.

        This is the exact comparison the router uses for `cache_fresh`.
        """
        build = _make_build()
        builds.save_build(build)
        builds.save_wrapped_frames(build.build_id, [(0, b"x")])

        ts = builds.wrapped_frames_rendered_at(build.build_id)
        assert ts is not None
        # ISO-8601 strings compare lexicographically, which is what the
        # router relies on.
        assert ts >= build.created_at

    def test_rendered_at_older_than_build_created_at_is_stale(
        self, isolated_builds_dir
    ):
        """Simulate an older render where the build has been re-saved fresher.

        If we overwrite the build's created_at to "now" AFTER the frames
        were rendered, the stored rendered_at will be lexicographically
        older. The router uses rendered_at < build.created_at as the
        "rerender needed" signal.
        """
        build = _make_build()
        builds.save_build(build)
        # Render with an ancient timestamp
        builds._conn().execute(
            "INSERT INTO wrapped_frames "
            "(build_id, frame_index, png_data, rendered_at) "
            "VALUES (?, ?, ?, ?)",
            [build.build_id, 0, b"ancient", "2020-01-01T00:00:00+00:00"],
        )
        # Rebuild the same build_id with a fresh created_at (future date)
        future_build = build.model_copy(
            update={"created_at": "2099-12-31T23:59:59+00:00"}
        )
        builds.save_build(future_build)

        ts = builds.wrapped_frames_rendered_at(build.build_id)
        assert ts is not None
        # This is exactly what the router checks
        assert ts < future_build.created_at


# --- list_builds(profile_name=...) filter ----------------------------------


class TestListBuildsProfileFilter:
    def test_no_filter_returns_all(self, isolated_builds_dir):
        # Save each build before constructing the next so the id
        # generator sees existing rows and increments correctly.
        b1 = _make_build(profile_name="alice")
        builds.save_build(b1)
        b2 = _make_build(profile_name="bob")
        builds.save_build(b2)
        b3 = _make_build(profile_name="")
        builds.save_build(b3)

        assert len({b1.build_id, b2.build_id, b3.build_id}) == 3
        result = builds.list_builds()
        assert len(result) == 3

    def test_filter_by_profile_name(self, isolated_builds_dir):
        # Save each build BEFORE constructing the next one, so the id
        # generator increments correctly. (`build_from_parts` calls
        # `_next_id_for` at construction time, which only sees rows that
        # have already been saved.)
        a1 = _make_build(profile_name="steady bold turtle")
        builds.save_build(a1)
        a2 = _make_build(profile_name="steady bold turtle", school="Purdue")
        builds.save_build(a2)
        b1 = _make_build(profile_name="brave calm fox")
        builds.save_build(b1)

        assert len({a1.build_id, a2.build_id, b1.build_id}) == 3, (
            "Precondition: all three builds must have distinct build_ids"
        )

        turtles = builds.list_builds(profile_name="steady bold turtle")
        assert len(turtles) == 2
        assert {bs.build_id for bs in turtles} == {a1.build_id, a2.build_id}

    def test_filter_no_matches_returns_empty_list(
        self, isolated_builds_dir
    ):
        builds.save_build(_make_build(profile_name="alice"))
        assert builds.list_builds(profile_name="zzz-not-found") == []

    def test_filter_by_empty_string_returns_only_unnamed(
        self, isolated_builds_dir
    ):
        """profile_name="" is a legitimate value (the default).

        When a caller explicitly asks for "" we must return only the
        anonymous builds, NOT treat it as `None` / "all builds".
        This is the saboteur's question: does the code mix up the two
        sentinels? list_builds(None) != list_builds("").
        """
        b1 = _make_build(profile_name="")
        builds.save_build(b1)
        b2 = _make_build(profile_name="alice")
        builds.save_build(b2)
        b3 = _make_build(profile_name="")
        builds.save_build(b3)
        assert len({b1.build_id, b2.build_id, b3.build_id}) == 3

        anon = builds.list_builds(profile_name="")
        assert len(anon) == 2
        assert all(b.profile_name == "" for b in anon)

        all_builds = builds.list_builds()
        assert len(all_builds) == 3

    def test_filter_preserves_newest_first_ordering(
        self, isolated_builds_dir
    ):
        first = _make_build(profile_name="alice")
        builds.save_build(first)
        second = _make_build(profile_name="alice", school="Purdue")
        builds.save_build(second)
        assert first.build_id != second.build_id

        result = builds.list_builds(profile_name="alice")
        assert len(result) == 2
        assert result[0].created_at >= result[1].created_at

    def test_filter_populates_profile_name_on_summary(
        self, isolated_builds_dir
    ):
        """BuildSummary must echo the profile_name back."""
        builds.save_build(_make_build(profile_name="brave gold bear"))
        [summary] = builds.list_builds(profile_name="brave gold bear")
        assert summary.profile_name == "brave gold bear"
