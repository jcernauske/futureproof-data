"""Tests for the Gold zone O*NET career transitions transformer.

Covers title enrichment, work profile availability flags, static fields,
record IDs, and edge cases. Combined with test_onet_work_profiles.py,
these exceed the minimum 15 tests for consumable zone.
"""

import datetime

import pytest

from gold.onet_career_transitions import (
    GRAIN_FIELDS,
    GRAIN_PREFIX,
    add_record_ids,
    derive_gold_rows,
    get_gold_schema,
)
from brightsmith.infra.grain import compute_grain_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_occupation(bls_soc_code="15-1252", primary_title="Software Developers"):
    return {
        "bls_soc_code": bls_soc_code,
        "primary_title": primary_title,
    }


def _make_transition(
    bls_soc_code="15-1252",
    related_bls_soc_code="15-1256",
    best_index=1,
    relatedness_tier="Primary-Short",
    is_primary=True,
    relationship_type="similarity",
    source_load_date=datetime.date(2026, 4, 8),
):
    return {
        "bls_soc_code": bls_soc_code,
        "related_bls_soc_code": related_bls_soc_code,
        "best_index": best_index,
        "relatedness_tier": relatedness_tier,
        "is_primary": is_primary,
        "relationship_type": relationship_type,
        "source_load_date": source_load_date,
    }


def _make_work_profile(bls_soc_code="15-1252", activity_profile_available=True):
    return {
        "bls_soc_code": bls_soc_code,
        "activity_profile_available": activity_profile_available,
    }


# ---------------------------------------------------------------------------
# Tests: Title Enrichment
# ---------------------------------------------------------------------------


class TestTitleEnrichment:
    """Tests for title lookups from occupations."""

    def test_source_title_enriched(self):
        """Source title should come from occupation lookup."""
        transitions = [_make_transition()]
        occupations = [
            _make_occupation("15-1252", "Software Developers"),
            _make_occupation("15-1256", "Software Quality Assurance Analysts"),
        ]
        work_profiles = [_make_work_profile("15-1252"), _make_work_profile("15-1256")]

        result = derive_gold_rows(transitions, occupations, work_profiles)
        assert result[0]["source_title"] == "Software Developers"

    def test_related_title_enriched(self):
        """Related title should come from occupation lookup."""
        transitions = [_make_transition()]
        occupations = [
            _make_occupation("15-1252", "Software Developers"),
            _make_occupation("15-1256", "Software Quality Assurance Analysts"),
        ]
        work_profiles = [_make_work_profile("15-1252"), _make_work_profile("15-1256")]

        result = derive_gold_rows(transitions, occupations, work_profiles)
        assert result[0]["related_title"] == "Software Quality Assurance Analysts"

    def test_missing_title_defaults_to_unknown(self):
        """Missing SOC in occupation lookup should default to 'Unknown'."""
        transitions = [_make_transition(related_bls_soc_code="99-9999")]
        occupations = [_make_occupation("15-1252", "Software Developers")]
        work_profiles = [_make_work_profile("15-1252")]

        result = derive_gold_rows(transitions, occupations, work_profiles)
        assert result[0]["related_title"] == "Unknown"


# ---------------------------------------------------------------------------
# Tests: Work Profile Flags
# ---------------------------------------------------------------------------


class TestWorkProfileFlags:
    """Tests for work profile availability flags."""

    def test_source_has_work_profile_true(self):
        """Source SOC with activity_profile_available=True -> True."""
        transitions = [_make_transition()]
        occupations = [
            _make_occupation("15-1252"),
            _make_occupation("15-1256"),
        ]
        work_profiles = [
            _make_work_profile("15-1252", activity_profile_available=True),
            _make_work_profile("15-1256", activity_profile_available=True),
        ]

        result = derive_gold_rows(transitions, occupations, work_profiles)
        assert result[0]["source_has_work_profile"] is True

    def test_related_has_work_profile_false_partial(self):
        """Related SOC with activity_profile_available=False -> False."""
        transitions = [_make_transition()]
        occupations = [
            _make_occupation("15-1252"),
            _make_occupation("15-1256"),
        ]
        work_profiles = [
            _make_work_profile("15-1252", activity_profile_available=True),
            _make_work_profile("15-1256", activity_profile_available=False),
        ]

        result = derive_gold_rows(transitions, occupations, work_profiles)
        assert result[0]["related_has_work_profile"] is False

    def test_missing_work_profile_defaults_false(self):
        """SOC not in work profiles table defaults to False."""
        transitions = [_make_transition(related_bls_soc_code="99-9999")]
        occupations = [
            _make_occupation("15-1252"),
            _make_occupation("99-9999"),
        ]
        work_profiles = [_make_work_profile("15-1252")]

        result = derive_gold_rows(transitions, occupations, work_profiles)
        assert result[0]["related_has_work_profile"] is False


# ---------------------------------------------------------------------------
# Tests: Static Fields & Record IDs
# ---------------------------------------------------------------------------


class TestStaticFieldsAndRecordIds:
    """Tests for static fields and record ID generation."""

    def test_backs_feature_always_stage3branching(self):
        """backs_feature should always be 'Stage3Branching'."""
        transitions = [_make_transition()]
        occupations = [_make_occupation("15-1252"), _make_occupation("15-1256")]
        work_profiles = [_make_work_profile("15-1252"), _make_work_profile("15-1256")]

        result = derive_gold_rows(transitions, occupations, work_profiles)
        assert result[0]["backs_feature"] == "Stage3Branching"

    def test_record_id_deterministic(self):
        """record_id should be deterministic for same composite key."""
        transitions = [_make_transition()]
        occupations = [_make_occupation("15-1252"), _make_occupation("15-1256")]
        work_profiles = [_make_work_profile("15-1252"), _make_work_profile("15-1256")]

        result = derive_gold_rows(transitions, occupations, work_profiles)
        promoted_at = datetime.datetime(2026, 4, 8, 12, 0, 0, tzinfo=datetime.timezone.utc)
        add_record_ids(result, promoted_at)

        expected = compute_grain_id(
            {"bls_soc_code": "15-1252", "related_bls_soc_code": "15-1256"},
            GRAIN_FIELDS,
            prefix=GRAIN_PREFIX,
        )
        assert result[0]["record_id"] == expected
        assert result[0]["record_id"].startswith("tr-")

    def test_schema_column_count(self):
        """Schema should have exactly 14 columns."""
        schema = get_gold_schema()
        assert len(schema.fields) == 14


# ---------------------------------------------------------------------------
# Tests: Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_transitions_returns_empty(self):
        """Empty transition list returns empty result."""
        result = derive_gold_rows([], [], [])
        assert result == []

    def test_carried_fields_preserved(self):
        """Carried fields from Silver should be preserved exactly."""
        transitions = [_make_transition(
            bls_soc_code="15-1252",
            related_bls_soc_code="15-1256",
            best_index=3,
            relatedness_tier="Primary-Long",
            is_primary=True,
            relationship_type="similarity",
        )]
        occupations = [_make_occupation("15-1252"), _make_occupation("15-1256")]
        work_profiles = [_make_work_profile("15-1252"), _make_work_profile("15-1256")]

        result = derive_gold_rows(transitions, occupations, work_profiles)
        assert result[0]["best_index"] == 3
        assert result[0]["relatedness_tier"] == "Primary-Long"
        assert result[0]["is_primary"] is True
        assert result[0]["relationship_type"] == "similarity"

    def test_multiple_transitions_processed(self):
        """Multiple transitions should all be processed."""
        transitions = [
            _make_transition(bls_soc_code="15-1252", related_bls_soc_code="15-1256", best_index=1),
            _make_transition(bls_soc_code="15-1252", related_bls_soc_code="29-1141", best_index=2),
            _make_transition(bls_soc_code="29-1141", related_bls_soc_code="15-1252", best_index=1),
        ]
        occupations = [
            _make_occupation("15-1252", "Software Developers"),
            _make_occupation("15-1256", "Software QA"),
            _make_occupation("29-1141", "Registered Nurses"),
        ]
        work_profiles = [
            _make_work_profile("15-1252"),
            _make_work_profile("15-1256"),
            _make_work_profile("29-1141"),
        ]

        result = derive_gold_rows(transitions, occupations, work_profiles)
        assert len(result) == 3
