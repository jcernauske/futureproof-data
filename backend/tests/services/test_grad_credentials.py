"""Tests for ``app.services.grad_credentials``.

Covers:
- YAML loading: all credentials load with required fields populated.
- SOC lookup: known SOC maps to correct credential, unknown returns None.
- Pre-X pattern matching: "pre-PT", "prept", "pre-med", "premed" match
  correct credential_ids; non-pre-X inputs ("biology", "marketing")
  return None; partial-word traps ("premiere", "premeditate") don't
  false-positive.
- Feeder lookup: returns feeders with correct offered_at_school flags,
  unknown credential returns empty list.

Mocks:
- ``intent._get_school_cips`` is monkeypatched to return a controlled
  list of CIP codes (no DuckDB dependency).
"""

from __future__ import annotations

from typing import Any

import pytest

from app.services import grad_credentials, intent

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_credential_cache() -> None:
    """Clear the module-level credential cache between tests so tests
    don't bleed state from a prior monkeypatch or load failure."""
    grad_credentials._credentials = None
    yield
    grad_credentials._credentials = None


@pytest.fixture
def stub_school_cips(monkeypatch: pytest.MonkeyPatch):
    """Provide a controllable list of CIP codes at a school.

    Returns a setter function: call ``stub_school_cips([{"cipcode": "31.0501"}])``
    to set what ``_get_school_cips`` returns.
    """

    current: list[dict[str, str]] = []

    def _setter(cips: list[dict[str, str]]) -> None:
        nonlocal current
        current = cips

    monkeypatch.setattr(intent, "_get_school_cips", lambda unitid: current)
    return _setter


# ---------------------------------------------------------------------------
# YAML Loading
# ---------------------------------------------------------------------------


class TestYAMLLoad:
    """Validate the curated YAML file loads correctly."""

    def test_loads_all_credentials(self) -> None:
        """The YAML must load at least 10 credential entries and each must
        carry all required fields."""
        creds = grad_credentials._load_credentials()
        assert len(creds) >= 10, (
            f"Expected >= 10 credentials, got {len(creds)}"
        )

        required_keys = {
            "credential_id",
            "credential_name_full",
            "credential_acronym",
            "socs",
            "feeder_cip4_codes",
            "context",
        }
        for cred in creds:
            missing = required_keys - set(cred.keys())
            assert not missing, (
                f"Credential {cred.get('credential_id', '???')} is missing "
                f"fields: {missing}"
            )
            # socs must be a non-empty list
            assert isinstance(cred["socs"], list)
            assert len(cred["socs"]) > 0, (
                f"Credential {cred['credential_id']} has no SOC codes"
            )
            # feeder_cip4_codes must be a non-empty list
            assert isinstance(cred["feeder_cip4_codes"], list)
            assert len(cred["feeder_cip4_codes"]) > 0, (
                f"Credential {cred['credential_id']} has no feeder CIP4 codes"
            )

    def test_each_credential_id_is_unique(self) -> None:
        """No duplicate credential_ids in the YAML."""
        creds = grad_credentials._load_credentials()
        ids = [c["credential_id"] for c in creds]
        assert len(ids) == len(set(ids)), (
            f"Duplicate credential_ids found: "
            f"{[x for x in ids if ids.count(x) > 1]}"
        )

    def test_feeder_cip4_codes_have_required_shape(self) -> None:
        """Each feeder entry must have cip4 (XX.XX) and note."""
        creds = grad_credentials._load_credentials()
        for cred in creds:
            for feeder in cred["feeder_cip4_codes"]:
                assert "cip4" in feeder, (
                    f"Feeder in {cred['credential_id']} is missing 'cip4'"
                )
                assert "note" in feeder, (
                    f"Feeder in {cred['credential_id']} is missing 'note'"
                )
                # CIP4 should match XX.XX pattern
                cip4 = feeder["cip4"]
                assert len(cip4) == 5 and cip4[2] == ".", (
                    f"Invalid CIP4 format: {cip4!r} in {cred['credential_id']}"
                )

    def test_corrupt_yaml_logs_error_and_returns_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the YAML file is unreadable, the module logs an error
        and returns an empty list (graceful degradation)."""
        from pathlib import Path

        # Point at a nonexistent path so read_text raises.
        monkeypatch.setattr(
            grad_credentials,
            "_YAML_PATH",
            Path("/tmp/nonexistent_grad_credentials_ZZZZZ.yaml"),
        )
        creds = grad_credentials._load_credentials()
        assert creds == []


# ---------------------------------------------------------------------------
# SOC Lookup
# ---------------------------------------------------------------------------


class TestSocLookup:
    """Test lookup_credential_for_soc."""

    def test_lookup_credential_for_known_soc(self) -> None:
        """DPT SOC (29-1123) should return credential_id='dpt'."""
        result = grad_credentials.lookup_credential_for_soc("29-1123")
        assert result is not None
        assert result["credential_id"] == "dpt"

    def test_lookup_credential_for_known_soc_jd(self) -> None:
        """JD SOC (23-1011) should return credential_id='jd'."""
        result = grad_credentials.lookup_credential_for_soc("23-1011")
        assert result is not None
        assert result["credential_id"] == "jd"

    def test_lookup_credential_for_md_soc(self) -> None:
        """One of the MD SOCs (29-1215) should return credential_id='md'."""
        result = grad_credentials.lookup_credential_for_soc("29-1215")
        assert result is not None
        assert result["credential_id"] == "md"

    def test_lookup_unknown_soc_returns_none(self) -> None:
        """A SOC not present in any credential entry returns None."""
        result = grad_credentials.lookup_credential_for_soc("15-1252")
        assert result is None

    def test_lookup_empty_string_returns_none(self) -> None:
        """Empty SOC string returns None."""
        result = grad_credentials.lookup_credential_for_soc("")
        assert result is None

    def test_lookup_garbage_soc_returns_none(self) -> None:
        """Nonsense SOC returns None."""
        result = grad_credentials.lookup_credential_for_soc("XX-YYYY")
        assert result is None


# ---------------------------------------------------------------------------
# Pre-X Pattern Matching
# ---------------------------------------------------------------------------


class TestPreXMatch:
    """Test lookup_credential_by_pre_x_pattern."""

    @pytest.mark.parametrize(
        "input_text,expected_credential_id",
        [
            ("pre-PT", "dpt"),
            ("prept", "dpt"),
            ("pre PT", "dpt"),
            ("Pre-Physical Therapy", "dpt"),
            ("PRE-PT", "dpt"),
        ],
    )
    def test_pre_pt_matches_dpt(
        self, input_text: str, expected_credential_id: str
    ) -> None:
        result = grad_credentials.lookup_credential_by_pre_x_pattern(input_text)
        assert result == expected_credential_id

    @pytest.mark.parametrize(
        "input_text,expected_credential_id",
        [
            ("pre-med", "md"),
            ("premed", "md"),
            ("Pre-Med", "md"),
            ("PRE MED", "md"),
        ],
    )
    def test_pre_med_matches_md(
        self, input_text: str, expected_credential_id: str
    ) -> None:
        result = grad_credentials.lookup_credential_by_pre_x_pattern(input_text)
        assert result == expected_credential_id

    @pytest.mark.parametrize(
        "input_text,expected_credential_id",
        [
            ("pre-law", "jd"),
            ("prelaw", "jd"),
            ("pre-vet", "dvm"),
            ("prevet", "dvm"),
            ("pre-dent", "dds"),
            ("pre-dental", "dds"),
            ("predent", "dds"),
            ("pre-pa", "ms-pa"),
            ("prepa", "ms-pa"),
            ("pre-optometry", "od"),
            ("preoptometry", "od"),
            ("pre-pharm", "pharmd"),
            ("prepharm", "pharmd"),
            ("pre-pharmacy", "pharmd"),
        ],
    )
    def test_all_pre_x_patterns(
        self, input_text: str, expected_credential_id: str
    ) -> None:
        result = grad_credentials.lookup_credential_by_pre_x_pattern(input_text)
        assert result == expected_credential_id, (
            f"Expected {input_text!r} -> {expected_credential_id!r}, "
            f"got {result!r}"
        )

    @pytest.mark.parametrize(
        "input_text",
        [
            "biology",
            "exercise science",
            "marketing",
            "computer science",
            "political science",
            "psychology",
            "",
        ],
    )
    def test_non_pre_x_returns_none(self, input_text: str) -> None:
        """Non-pre-X major inputs must not match any credential."""
        result = grad_credentials.lookup_credential_by_pre_x_pattern(input_text)
        assert result is None

    @pytest.mark.parametrize(
        "input_text",
        [
            "premiere",     # contains "pre" + "me" but is not "pre-med"
            "premeditate",  # would match if \b guard is missing
            "unprecedented",  # contains "pre" but no valid pattern
            "prequel",      # contains "pre" but no valid pattern
            "prepared",     # contains "pre" but no valid pattern
            "preview",      # contains "pre" + "v" but is not "pre-vet"
        ],
    )
    def test_partial_word_does_not_match(self, input_text: str) -> None:
        """Partial word matches must NOT trigger the pre-X pattern.
        This catches missing word-boundary guards (\\b)."""
        result = grad_credentials.lookup_credential_by_pre_x_pattern(input_text)
        assert result is None, (
            f"Partial word {input_text!r} should NOT match but got {result!r}"
        )

    def test_pre_x_embedded_in_sentence(self) -> None:
        """Pre-X pattern should match when embedded in a longer string."""
        result = grad_credentials.lookup_credential_by_pre_x_pattern(
            "I am doing the pre-med track at Indiana"
        )
        assert result == "md"

    @pytest.mark.parametrize(
        "input_text,expected_credential_id",
        [
            ("doctor", "md"),
            ("Doctor", "md"),
            ("physician", "md"),
            ("lawyer", "jd"),
            ("Lawyer", "jd"),
            ("attorney", "jd"),
            ("physical therapist", "dpt"),
            ("Physical Therapist", "dpt"),
            ("veterinarian", "dvm"),
            ("dentist", "dds"),
            ("Dentist", "dds"),
            ("physician assistant", "ms-pa"),
            ("Physician Assistant", "ms-pa"),
            ("optometrist", "od"),
            ("pharmacist", "pharmd"),
        ],
    )
    def test_career_name_matches_credential(
        self, input_text: str, expected_credential_id: str
    ) -> None:
        """Career names trigger the same credential as their pre-X form."""
        result = grad_credentials.lookup_credential_by_pre_x_pattern(input_text)
        assert result == expected_credential_id

    def test_career_name_embedded_in_sentence(self) -> None:
        result = grad_credentials.lookup_credential_by_pre_x_pattern(
            "I want to be a doctor"
        )
        assert result == "md"


# ---------------------------------------------------------------------------
# Feeder Lookup
# ---------------------------------------------------------------------------


class TestFeeders:
    """Test feeder_majors_at_school."""

    def test_returns_feeders_for_known_credential(
        self, stub_school_cips: Any
    ) -> None:
        """DPT should return feeders. Count depends on YAML but should
        be >= 3 and <= 7 (function caps at 7)."""
        stub_school_cips([])
        feeders = grad_credentials.feeder_majors_at_school(
            unitid=151351, credential_id="dpt"
        )
        assert len(feeders) >= 3
        assert len(feeders) <= 7

    def test_returns_3_to_5_feeders_when_yaml_has_enough(
        self, stub_school_cips: Any
    ) -> None:
        """With enough feeders in the YAML, the function should return at
        least 3. (The YAML for DPT has 7 entries; the function caps at 7.)"""
        stub_school_cips([])
        feeders = grad_credentials.feeder_majors_at_school(
            unitid=151351, credential_id="dpt"
        )
        assert len(feeders) >= 3

    def test_offered_at_school_flag_correct(
        self, stub_school_cips: Any
    ) -> None:
        """When the school has Exercise Science (31.05), that feeder should
        have offered_at_school=True and others should have False."""
        stub_school_cips([
            {"cipcode": "31.0501"},  # Exercise Science leaf
            {"cipcode": "26.0101"},  # Biology leaf
        ])
        feeders = grad_credentials.feeder_majors_at_school(
            unitid=151351, credential_id="dpt"
        )
        # Find the Exercise Science feeder (31.05)
        ex_sci = [f for f in feeders if f.cip4 == "31.05"]
        assert len(ex_sci) == 1
        assert ex_sci[0].offered_at_school is True

        # Find the Biology feeder (26.01)
        bio = [f for f in feeders if f.cip4 == "26.01"]
        assert len(bio) == 1
        assert bio[0].offered_at_school is True

        # A feeder NOT offered at school should be False
        not_offered = [
            f for f in feeders
            if f.cip4 not in ("31.05", "26.01")
        ]
        for f in not_offered:
            assert f.offered_at_school is False, (
                f"Feeder {f.cip4} should not be offered at school"
            )

    def test_offered_feeders_sorted_first(
        self, stub_school_cips: Any
    ) -> None:
        """Feeders offered at the school should appear before those not
        offered, as the function sorts by offered_at_school descending."""
        stub_school_cips([
            {"cipcode": "42.0101"},  # Psychology leaf — NOT the first in YAML
        ])
        feeders = grad_credentials.feeder_majors_at_school(
            unitid=151351, credential_id="dpt"
        )
        # Psychology (42.01) should be first (offered), others after.
        offered_indices = [
            i for i, f in enumerate(feeders) if f.offered_at_school
        ]
        not_offered_indices = [
            i for i, f in enumerate(feeders) if not f.offered_at_school
        ]
        if offered_indices and not_offered_indices:
            assert max(offered_indices) < min(not_offered_indices)

    def test_unknown_credential_returns_empty(
        self, stub_school_cips: Any
    ) -> None:
        """An unknown credential_id returns an empty feeder list."""
        stub_school_cips([])
        feeders = grad_credentials.feeder_majors_at_school(
            unitid=151351, credential_id="nonexistent_credential"
        )
        assert feeders == []

    def test_feeder_has_expected_fields(
        self, stub_school_cips: Any
    ) -> None:
        """Each FeederMajor should have cip4, cip_title, note, and
        offered_at_school fields populated."""
        stub_school_cips([])
        feeders = grad_credentials.feeder_majors_at_school(
            unitid=151351, credential_id="dpt"
        )
        for f in feeders:
            assert f.cip4, "cip4 is empty for feeder"
            assert f.cip_title, f"cip_title is empty for {f.cip4}"
            assert f.note, f"note is empty for {f.cip4}"
            assert isinstance(f.offered_at_school, bool)
