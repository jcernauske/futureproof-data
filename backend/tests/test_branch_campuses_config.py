"""Tests for the frozen branch-campus suppression config.

Per spec ``docs/specs/feature-branch-campus-suppression.md`` §4 New
Tests Required (P0/P1).

These tests defend the integrity of three import-time constants in
``backend/app/config/branch_campuses.py``:

* ``INSTITUTION_FAMILIES`` — flagship UNITID -> list of branch UNITIDs.
* ``SUPPRESSED_BRANCH_UNITIDS`` — flat ``frozenset`` derived from the
  union of every branch list. Used by the leaderboard query as
  ``WHERE unitid NOT IN (...)``.
* ``FAMILY_SIZE_BY_FLAGSHIP_UNITID`` — flagship UNITID -> total family
  size (flagship + branches). Used to populate the ``family_size``
  column on flagship rows in the leaderboard response.

Why these tests matter (every assertion would catch a real bug):

* If the union derivation drifts from the underlying dict, suppression
  silently leaks branches back onto the leaderboard or filters extra
  rows that should have surfaced.
* If a flagship's family size disagrees with its branch count, the
  "Campuses" column lies to students about how many institutions are
  in the system.
* If a future edit slips a ``str`` UNITID into the dict, the
  leaderboard SQL ``WHERE unitid NOT IN (1, 2, "204796")`` becomes a
  type-coercion landmine in DuckDB. The all-int test fails loudly at
  test time instead of producing wrong rankings at runtime.
"""

from __future__ import annotations

from app.config.branch_campuses import (
    FAMILY_SIZE_BY_FLAGSHIP_UNITID,
    INSTITUTION_FAMILIES,
    SUPPRESSED_BRANCH_UNITIDS,
)

# ===========================================================================
# P0 — derived structures must stay in lockstep with INSTITUTION_FAMILIES
# ===========================================================================


class TestSuppressedUnitidsIsUnionOfFamilyBranches:
    def test_suppressed_unitids_is_union_of_family_branches(self) -> None:
        """``SUPPRESSED_BRANCH_UNITIDS`` must equal the union of every
        branch list across every family.

        This is the load-bearing invariant: the leaderboard query
        interpolates this set into ``WHERE unitid NOT IN (...)``. If
        the derivation drifts from the underlying dict, the wrong
        schools get suppressed (or un-suppressed) and the entire fix
        is voided silently.
        """
        expected_union: set[int] = set()
        for branches in INSTITUTION_FAMILIES.values():
            expected_union.update(branches)

        # frozenset == set comparison is set-equality, not identity.
        assert SUPPRESSED_BRANCH_UNITIDS == expected_union

        # Defensive cross-check: count, too. A subset+superset pair would
        # already be caught by ==, but counting catches a hypothetical
        # `__eq__` regression in frozenset (paranoid, but cheap).
        assert len(SUPPRESSED_BRANCH_UNITIDS) == len(expected_union)


class TestFamilySizeIncludesFlagshipPlusBranches:
    def test_family_size_includes_flagship_plus_branches(self) -> None:
        """For every flagship in the map,
        ``FAMILY_SIZE_BY_FLAGSHIP_UNITID[flagship]`` must equal
        ``len(INSTITUTION_FAMILIES[flagship]) + 1``.

        The frontend renders this number as the "Campuses" cell. Off
        by one (forgetting to count the flagship itself, or
        double-counting it) misleads students about how big the system
        actually is.
        """
        # Both maps must have identical keysets.
        assert set(FAMILY_SIZE_BY_FLAGSHIP_UNITID.keys()) == set(
            INSTITUTION_FAMILIES.keys()
        )

        # Every entry: flagship (1) + count of branches.
        for flagship, branches in INSTITUTION_FAMILIES.items():
            expected = len(branches) + 1
            actual = FAMILY_SIZE_BY_FLAGSHIP_UNITID[flagship]
            assert actual == expected, (
                f"family_size for flagship {flagship} is {actual}, "
                f"expected {expected} (flagship + {len(branches)} branches)"
            )

        # And every value is at least 2 — a "family" of one is not a
        # family. (If the config ever lists a flagship with zero
        # branches, that's a data bug — the entry should be removed.)
        for flagship, size in FAMILY_SIZE_BY_FLAGSHIP_UNITID.items():
            assert size >= 2, (
                f"flagship {flagship} has family_size={size}; "
                "a flagship with zero branches should not be in the map"
            )


# ===========================================================================
# P1 — structural integrity guards
# ===========================================================================


class TestNoUnitidAppearsInMultipleFamilies:
    def test_no_unitid_appears_in_multiple_families(self) -> None:
        """A branch UNITID belongs to at most one family.

        Two families claiming the same branch would mean the
        suppression set's count is right (set dedupes) but the family
        size is overstated for whichever flagship owns the duplicate.
        Rare but worth catching at test time, not at student-display
        time.
        """
        all_branches: list[int] = []
        for branches in INSTITUTION_FAMILIES.values():
            all_branches.extend(branches)

        # If every branch is unique, len(list) == len(set).
        assert len(all_branches) == len(set(all_branches)), (
            "A branch UNITID appears in multiple families. Duplicates: "
            f"{sorted({b for b in all_branches if all_branches.count(b) > 1})}"
        )


class TestNoFlagshipIsAlsoABranch:
    def test_no_flagship_is_also_a_branch(self) -> None:
        """No UNITID may be both a flagship key AND a branch in any
        list.

        If a flagship is also listed as a branch (its own or another
        family's), the leaderboard SQL would suppress the flagship
        itself and the entire family disappears from the leaderboard.
        The loud-failure version of "where did Ohio University go?"
        """
        flagship_keys = set(INSTITUTION_FAMILIES.keys())
        overlap = flagship_keys & set(SUPPRESSED_BRANCH_UNITIDS)
        assert overlap == set(), (
            f"UNITID(s) {sorted(overlap)} appear as both flagship and "
            "branch — the flagship would be suppressed by its own family."
        )


class TestAllUnitidsAreInt:
    def test_all_unitids_are_int(self) -> None:
        """Every UNITID in the config must be a Python ``int``.

        The leaderboard SQL builder interpolates these values directly
        into ``WHERE unitid NOT IN (1, 2, 3)``. A stringified UNITID
        like ``"204796"`` would interpolate as ``WHERE unitid NOT IN
        (1, 2, '204796')`` — which DuckDB silently accepts via type
        coercion, but the surrounding ``CASE WHEN unitid = 204796``
        clause uses an int comparison. The two paths drift and the
        suppression / family_size annotation get out of sync without
        a single error message.

        Also guards ``FAMILY_SIZE_BY_FLAGSHIP_UNITID`` symmetrically
        because the same SQL builder reads both maps.

        The config module already has a similar ``assert`` at import
        time, but this test gives the failure a name and a CI signal
        instead of a confusing ImportError.
        """
        # Flagship keys
        for flagship in INSTITUTION_FAMILIES.keys():
            assert isinstance(flagship, int) and not isinstance(flagship, bool), (
                f"flagship {flagship!r} in INSTITUTION_FAMILIES is not int"
            )

        # Branch values
        for flagship, branches in INSTITUTION_FAMILIES.items():
            assert isinstance(branches, list), (
                f"INSTITUTION_FAMILIES[{flagship}] is {type(branches).__name__}, "
                "expected list"
            )
            for branch in branches:
                assert isinstance(branch, int) and not isinstance(branch, bool), (
                    f"branch {branch!r} under flagship {flagship} is not int"
                )

        # Suppressed-branch frozenset
        for branch in SUPPRESSED_BRANCH_UNITIDS:
            assert isinstance(branch, int) and not isinstance(branch, bool), (
                f"branch {branch!r} in SUPPRESSED_BRANCH_UNITIDS is not int"
            )

        # Family-size map (both keys and values).
        for flagship, size in FAMILY_SIZE_BY_FLAGSHIP_UNITID.items():
            assert isinstance(flagship, int) and not isinstance(flagship, bool), (
                f"flagship {flagship!r} in FAMILY_SIZE_BY_FLAGSHIP_UNITID "
                "is not int"
            )
            assert isinstance(size, int) and not isinstance(size, bool), (
                f"family_size {size!r} for flagship {flagship} is not int"
            )
