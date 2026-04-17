"""Tests for experience columns added to consumable.career_branches.

Spec: ``docs/specs/onet-experience-requirements.md`` §Zone 3 (2026-04-16).

Covers the 4 additive experience columns on ``career_branches``:

- ``related_experience_years`` — target occupation typical years
- ``related_experience_tier`` — target occupation experience tier
- ``source_experience_years`` — source occupation typical years
- ``experience_delta_years`` — NULL-propagating ``related - source``

Explicitly exercises:

- Both sides populated → delta = related - source
- Source NULL → delta NULL (NULL propagation, NOT ``related - 0``)
- Target NULL → delta NULL
- Both NULL → all 4 fields NULL
- ``experience_tier`` flows through verbatim from Silver
- Schema has 34 total fields after the additive change
- Backward compat: calling ``derive_br_rows`` without
  ``onet_experience_rows`` yields the original 30 fields plus 4 NULL
  experience fields
"""

from __future__ import annotations

from gold.futureproof_engine import (
    derive_br_rows,
    get_br_schema,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _transition(
    bls_soc_code: str = "15-1252",
    related_bls_soc_code: str = "11-3021",
    source_title: str = "Software Developers",
    related_title: str = "Computer and Information Systems Managers",
    best_index: int = 3,
    relatedness_tier: str = "Primary-Short",
    is_primary: bool = True,
) -> dict:
    return {
        "bls_soc_code": bls_soc_code,
        "related_bls_soc_code": related_bls_soc_code,
        "source_title": source_title,
        "related_title": related_title,
        "best_index": best_index,
        "relatedness_tier": relatedness_tier,
        "is_primary": is_primary,
    }


def _experience(
    bls_soc_code: str,
    experience_years_typical: float | None,
    experience_tier: str | None,
) -> dict:
    """Silver-shaped experience row. Mirrors base.onet_experience_profiles."""
    return {
        "bls_soc_code": bls_soc_code,
        "experience_years_typical": experience_years_typical,
        "experience_tier": experience_tier,
    }


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class TestExperienceSchema:
    """Schema gate: the additive columns must land at IDs 31-34."""

    def test_schema_has_34_fields(self):
        """30 baseline + 4 experience = 34 total fields."""
        schema = get_br_schema()
        assert len(schema.fields) == 34

    def test_schema_experience_fields_present(self):
        schema = get_br_schema()
        names = [f.name for f in schema.fields]
        for field_name in (
            "related_experience_years",
            "related_experience_tier",
            "source_experience_years",
            "experience_delta_years",
        ):
            assert field_name in names

    def test_schema_experience_fields_not_required(self):
        """All 4 experience fields must be nullable (required=False)."""
        schema = get_br_schema()
        exp_fields = {
            f.name: f
            for f in schema.fields
            if f.name
            in {
                "related_experience_years",
                "related_experience_tier",
                "source_experience_years",
                "experience_delta_years",
            }
        }
        for name, field in exp_fields.items():
            assert field.required is False, (
                f"{name} must be nullable (NULL-propagating per §Zone 3)"
            )

    def test_schema_experience_field_ids(self):
        """IDs 31-34 reserved for experience columns per §Zone 3."""
        schema = get_br_schema()
        by_id = {f.field_id: f.name for f in schema.fields}
        assert by_id[31] == "related_experience_years"
        assert by_id[32] == "related_experience_tier"
        assert by_id[33] == "source_experience_years"
        assert by_id[34] == "experience_delta_years"


# ---------------------------------------------------------------------------
# Derivation — happy path + NULL propagation
# ---------------------------------------------------------------------------


class TestExperienceDerivation:
    """Both sides populated → delta = related - source. NULL propagation."""

    def test_both_sides_populated_delta_is_difference(self):
        """When both sides have experience, delta is related - source."""
        transitions = [_transition()]
        experience = [
            _experience("15-1252", 7.0, "mid"),   # Software Developers
            _experience("11-3021", 9.0, "senior"),  # CIS Managers
        ]
        rows = derive_br_rows(
            transitions, [], [], onet_experience_rows=experience
        )
        assert len(rows) == 1
        row = rows[0]
        assert row["source_experience_years"] == 7.0
        assert row["related_experience_years"] == 9.0
        assert row["related_experience_tier"] == "senior"
        assert row["experience_delta_years"] == 2.0

    def test_source_null_propagates_null_delta(self):
        """Source NULL → delta NULL (NOT 'related - 0'). Per §Zone 3 rationale."""
        transitions = [_transition()]
        # Only the target occupation has experience data; source is missing.
        experience = [
            _experience("11-3021", 9.0, "senior"),
        ]
        rows = derive_br_rows(
            transitions, [], [], onet_experience_rows=experience
        )
        row = rows[0]
        assert row["source_experience_years"] is None
        assert row["related_experience_years"] == 9.0
        assert row["related_experience_tier"] == "senior"
        assert row["experience_delta_years"] is None, (
            "Delta must NULL-propagate — do NOT substitute 0 for a missing source"
        )

    def test_target_null_propagates_null_delta(self):
        """Target NULL → delta NULL."""
        transitions = [_transition()]
        experience = [
            _experience("15-1252", 7.0, "mid"),
        ]
        rows = derive_br_rows(
            transitions, [], [], onet_experience_rows=experience
        )
        row = rows[0]
        assert row["source_experience_years"] == 7.0
        assert row["related_experience_years"] is None
        assert row["related_experience_tier"] is None
        assert row["experience_delta_years"] is None

    def test_both_null_all_four_fields_null(self):
        """Neither source nor target in the Silver table → 4 NULLs."""
        transitions = [_transition()]
        # Experience set covers some unrelated SOC code.
        experience = [
            _experience("99-9999", 5.0, "mid"),
        ]
        rows = derive_br_rows(
            transitions, [], [], onet_experience_rows=experience
        )
        row = rows[0]
        assert row["source_experience_years"] is None
        assert row["related_experience_years"] is None
        assert row["related_experience_tier"] is None
        assert row["experience_delta_years"] is None

    def test_negative_delta_allowed(self):
        """Senior source → entry target should produce a negative delta."""
        transitions = [
            _transition(
                bls_soc_code="11-1011",
                related_bls_soc_code="41-2031",
                source_title="Chief Executives",
                related_title="Retail Salespersons",
            )
        ]
        experience = [
            _experience("11-1011", 12.0, "senior"),
            _experience("41-2031", 0.75, "entry"),
        ]
        rows = derive_br_rows(
            transitions, [], [], onet_experience_rows=experience
        )
        row = rows[0]
        assert row["source_experience_years"] == 12.0
        assert row["related_experience_years"] == 0.75
        assert row["related_experience_tier"] == "entry"
        assert row["experience_delta_years"] == -11.25

    def test_tier_flows_through_verbatim(self):
        """Tier string must be the exact value from Silver — no re-derivation."""
        # Deliberately use an off-threshold value to ensure the tier is NOT
        # recomputed from years by the Gold transformer; it must pass through.
        transitions = [_transition()]
        experience = [
            _experience("15-1252", 3.0, "early"),
            # Target uses a tier string that wouldn't match a redo from years.
            # (This specifically guards against Gold accidentally re-bucketing.)
            _experience("11-3021", 9.0, "CUSTOM_TIER_STRING"),
        ]
        rows = derive_br_rows(
            transitions, [], [], onet_experience_rows=experience
        )
        row = rows[0]
        assert row["related_experience_tier"] == "CUSTOM_TIER_STRING"


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompat:
    """``derive_br_rows`` without experience rows still produces valid rows."""

    def test_call_without_experience_rows_yields_null_experience_fields(self):
        """Omitting onet_experience_rows must not break; 4 fields must be NULL."""
        transitions = [_transition()]
        rows = derive_br_rows(transitions, [], [])
        assert len(rows) == 1
        row = rows[0]
        assert row["source_experience_years"] is None
        assert row["related_experience_years"] is None
        assert row["related_experience_tier"] is None
        assert row["experience_delta_years"] is None

    def test_call_with_none_experience_rows_yields_null_experience_fields(self):
        """Explicit None keyword arg is equivalent to omission."""
        transitions = [_transition()]
        rows = derive_br_rows(
            transitions, [], [], onet_experience_rows=None
        )
        row = rows[0]
        assert row["source_experience_years"] is None
        assert row["related_experience_years"] is None
        assert row["related_experience_tier"] is None
        assert row["experience_delta_years"] is None

    def test_backward_compat_row_has_all_original_keys(self):
        """Backward-compat call produces all 30 original keys plus 4 NULL experience keys."""
        transitions = [_transition()]
        rows = derive_br_rows(transitions, [], [])
        row = rows[0]

        # The 30 original keys (24 baseline + 6 AI Exposure backfill).
        # record_id and promoted_at are added downstream by add_br_record_ids,
        # so they are not present here — the derive step produces 28 baseline
        # data keys + 4 new experience keys = 32 keys.
        original_keys = {
            "soc_code",
            "source_title",
            "related_soc_code",
            "related_title",
            "best_index",
            "relatedness_tier",
            "is_primary",
            "source_grw",
            "source_hmn",
            "source_burnout",
            "source_wage",
            "related_grw",
            "related_hmn",
            "related_burnout",
            "related_wage",
            "related_growth_category",
            "related_education_level",
            "grw_delta",
            "hmn_delta",
            "burnout_delta",
            "wage_delta",
            "branch_has_full_data",
            "source_res",
            "source_ai_boss",
            "related_res",
            "related_ai_boss",
            "res_delta",
            "ai_boss_delta",
        }
        experience_keys = {
            "related_experience_years",
            "related_experience_tier",
            "source_experience_years",
            "experience_delta_years",
        }
        actual_keys = set(row.keys())
        assert original_keys.issubset(actual_keys), (
            f"Missing original keys: {original_keys - actual_keys}"
        )
        assert experience_keys.issubset(actual_keys), (
            f"Missing experience keys: {experience_keys - actual_keys}"
        )
        # Exact shape: no extraneous keys introduced by the change.
        assert actual_keys == original_keys | experience_keys, (
            f"Unexpected keys: {actual_keys - (original_keys | experience_keys)}"
        )
