"""Tests for the Silver zone Karpathy AI Exposure transformer."""

import datetime

import pytest

from silver.karpathy_ai_exposure_transformer import (
    _dedup_by_soc_code,
    _is_broad_soc,
    _is_valid_soc,
    _normalize_soc_code,
    build_bls_prefix_map,
    build_bls_soc_lookup,
    build_bls_soc_set,
    get_silver_schema,
    title_match,
    transform_rows,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bronze_row():
    """A typical Bronze row with a detailed SOC code."""
    return {
        "slug": "financial-analysts",
        "occupation_title": "Financial analysts",
        "category": "business-and-financial",
        "soc_code": "13-2051",
        "exposure_score": 8,
        "rationale": "Financial analysts work almost entirely on computers, processing data, building models, and generating reports. AI tools are already handling data aggregation and basic forecasting, making the core analytical tasks highly automatable. The profession's heavy reliance on quantitative analysis and pattern recognition makes it particularly susceptible to AI disruption.",
        "median_pay_annual": 99890.0,
        "num_jobs_2024": 328600,
        "entry_education": "Bachelor's degree",
        "source_url": "https://raw.githubusercontent.com/karpathy/jobs/master/scores.json",
        "ingested_at": datetime.datetime(2026, 4, 9, 12, 0, 0),
        "source_method": "github_download",
        "load_date": datetime.date(2026, 4, 9),
    }


@pytest.fixture
def null_soc_row():
    """A Bronze row with null SOC code."""
    return {
        "slug": "nurse-anesthetists-nurse-midwives-and-nurse-practitioners",
        "occupation_title": "Nurse anesthetists, nurse midwives, and nurse practitioners",
        "category": "healthcare",
        "soc_code": None,
        "exposure_score": 4,
        "rationale": "While these advanced practice nurses deal with complex clinical decisions, many of their routine tasks like documentation, patient education, and protocol-based care decisions could be assisted by AI. However, the hands-on patient care and critical judgment aspects remain firmly human. The blend of cognitive and physical tasks provides moderate protection.",
        "median_pay_annual": 129480.0,
        "num_jobs_2024": 327000,
        "entry_education": "Master's degree",
        "source_url": "https://raw.githubusercontent.com/karpathy/jobs/master/scores.json",
        "ingested_at": datetime.datetime(2026, 4, 9, 12, 0, 0),
        "source_method": "github_download",
        "load_date": datetime.date(2026, 4, 9),
    }


@pytest.fixture
def broad_soc_row():
    """A Bronze row with a broad SOC code (XX-XXX0)."""
    return {
        "slug": "drafters",
        "occupation_title": "Drafters",
        "category": "architecture-and-engineering",
        "soc_code": "17-3010",
        "exposure_score": 9,
        "rationale": "Drafters create technical drawings and plans using computer-aided design (CAD) software. This is precisely the kind of work that AI excels at, with generative AI already capable of producing architectural and engineering drawings from specifications. The work is almost entirely computer-based, making it highly susceptible to automation through AI-powered design tools.",
        "median_pay_annual": 60290.0,
        "num_jobs_2024": 204300,
        "entry_education": "Associate's degree",
        "source_url": "https://raw.githubusercontent.com/karpathy/jobs/master/scores.json",
        "ingested_at": datetime.datetime(2026, 4, 9, 12, 0, 0),
        "source_method": "github_download",
        "load_date": datetime.date(2026, 4, 9),
    }


@pytest.fixture
def bls_rows():
    """Sample BLS OOH rows for cross-validation."""
    return [
        {"soc_code": "13-2051", "occupation_title": "Financial analysts"},
        {"soc_code": "13-2020", "occupation_title": "Property appraisers and assessors"},
        {"soc_code": "17-3011", "occupation_title": "Architectural and civil drafters"},
        {"soc_code": "17-3012", "occupation_title": "Electrical and electronics drafters"},
        {"soc_code": "17-3013", "occupation_title": "Mechanical drafters"},
        {"soc_code": "17-3019", "occupation_title": "Drafters, all other"},
        {"soc_code": "29-1151", "occupation_title": "Nurse anesthetists"},
        {"soc_code": "29-1161", "occupation_title": "Nurse midwives"},
        {"soc_code": "29-1171", "occupation_title": "Nurse practitioners"},
        {"soc_code": "15-1252", "occupation_title": "Software developers"},
        {"soc_code": "35-2011", "occupation_title": "Cooks, fast food"},
        {"soc_code": "35-2012", "occupation_title": "Cooks, institution and cafeteria"},
        {"soc_code": "35-2013", "occupation_title": "Cooks, private household"},
        {"soc_code": "35-2014", "occupation_title": "Cooks, restaurant"},
        {"soc_code": "35-2015", "occupation_title": "Cooks, short order"},
        {"soc_code": "35-2019", "occupation_title": "Cooks, all other"},
    ]


# ---------------------------------------------------------------------------
# TestNormalizeSocCode
# ---------------------------------------------------------------------------

class TestNormalizeSocCode:
    """Tests for SOC code normalization."""

    def test_strips_whitespace(self):
        assert _normalize_soc_code("  13-2051  ") == "13-2051"

    def test_none_returns_none(self):
        assert _normalize_soc_code(None) is None

    def test_empty_returns_none(self):
        assert _normalize_soc_code("") is None

    def test_whitespace_only_returns_none(self):
        assert _normalize_soc_code("   ") is None

    def test_clean_value_passes_through(self):
        assert _normalize_soc_code("15-1252") == "15-1252"


# ---------------------------------------------------------------------------
# TestSocPatterns
# ---------------------------------------------------------------------------

class TestSocPatterns:
    """Tests for SOC code pattern detection."""

    def test_valid_detailed_code(self):
        assert _is_valid_soc("13-2051") is True

    def test_valid_broad_code(self):
        assert _is_valid_soc("17-3010") is True

    def test_invalid_no_hyphen(self):
        assert _is_valid_soc("132051") is False

    def test_invalid_alpha(self):
        assert _is_valid_soc("AB-CDEF") is False

    def test_invalid_too_short(self):
        assert _is_valid_soc("13-205") is False

    def test_broad_soc_detected(self):
        assert _is_broad_soc("17-3010") is True

    def test_detailed_soc_not_broad(self):
        assert _is_broad_soc("17-3011") is False

    def test_major_group_code_is_broad(self):
        """XX-X000 is still a broad pattern (last digit is 0)."""
        assert _is_broad_soc("19-5000") is True


# ---------------------------------------------------------------------------
# TestBuildBlsLookups
# ---------------------------------------------------------------------------

class TestBuildBlsLookups:
    """Tests for BLS lookup construction."""

    def test_soc_set_contains_all_codes(self, bls_rows):
        soc_set = build_bls_soc_set(bls_rows)
        assert "13-2051" in soc_set
        assert "17-3011" in soc_set
        assert len(soc_set) == 16

    def test_title_lookup_lowercase(self, bls_rows):
        lookup = build_bls_soc_lookup(bls_rows)
        assert "financial analysts" in lookup
        assert lookup["financial analysts"] == "13-2051"

    def test_prefix_map_excludes_broad_codes(self, bls_rows):
        soc_set = build_bls_soc_set(bls_rows)
        prefix_map = build_bls_prefix_map(soc_set)
        # 13-2020 is a broad code and should not appear as a value
        all_codes = [c for codes in prefix_map.values() for c in codes]
        assert "13-2020" not in all_codes

    def test_prefix_map_groups_detailed_codes(self, bls_rows):
        soc_set = build_bls_soc_set(bls_rows)
        prefix_map = build_bls_prefix_map(soc_set)
        assert "17-301" in prefix_map
        assert set(prefix_map["17-301"]) == {"17-3011", "17-3012", "17-3013", "17-3019"}


# ---------------------------------------------------------------------------
# TestTitleMatch
# ---------------------------------------------------------------------------

class TestTitleMatch:
    """Tests for title-based SOC resolution."""

    def test_exact_match(self, bls_rows):
        lookup = build_bls_soc_lookup(bls_rows)
        result = title_match("Financial analysts", lookup)
        assert result == ["13-2051"]

    def test_substring_match_bls_in_karpathy(self, bls_rows):
        lookup = build_bls_soc_lookup(bls_rows)
        result = title_match(
            "Nurse anesthetists, nurse midwives, and nurse practitioners",
            lookup,
        )
        assert "29-1151" in result
        assert "29-1161" in result
        assert "29-1171" in result

    def test_no_match_returns_empty(self, bls_rows):
        lookup = build_bls_soc_lookup(bls_rows)
        result = title_match("Military careers", lookup)
        assert result == []

    def test_case_insensitive(self, bls_rows):
        lookup = build_bls_soc_lookup(bls_rows)
        result = title_match("FINANCIAL ANALYSTS", lookup)
        assert result == ["13-2051"]


# ---------------------------------------------------------------------------
# TestTransformRows
# ---------------------------------------------------------------------------

class TestTransformRows:
    """Tests for the main transformation logic."""

    def test_direct_match_produces_one_row(self, bronze_row, bls_rows):
        rows = transform_rows([bronze_row], bls_rows)
        assert len(rows) == 1
        assert rows[0]["soc_code"] == "13-2051"
        assert rows[0]["soc_resolved_method"] == "direct"
        assert rows[0]["bls_match"] is True

    def test_record_id_prefix(self, bronze_row, bls_rows):
        rows = transform_rows([bronze_row], bls_rows)
        assert rows[0]["record_id"].startswith("kai-")

    def test_record_id_deterministic(self, bronze_row, bls_rows):
        r1 = transform_rows([bronze_row], bls_rows)
        r2 = transform_rows([bronze_row], bls_rows)
        assert r1[0]["record_id"] == r2[0]["record_id"]

    def test_exposure_score_passthrough(self, bronze_row, bls_rows):
        rows = transform_rows([bronze_row], bls_rows)
        assert rows[0]["exposure_score"] == 8

    def test_rationale_passthrough(self, bronze_row, bls_rows):
        rows = transform_rows([bronze_row], bls_rows)
        assert rows[0]["rationale"] == bronze_row["rationale"]

    def test_slug_preserved(self, bronze_row, bls_rows):
        rows = transform_rows([bronze_row], bls_rows)
        assert rows[0]["slug"] == "financial-analysts"

    def test_source_load_date_from_load_date(self, bronze_row, bls_rows):
        rows = transform_rows([bronze_row], bls_rows)
        assert rows[0]["source_load_date"] == datetime.date(2026, 4, 9)

    def test_ingested_at_is_utc(self, bronze_row, bls_rows):
        rows = transform_rows([bronze_row], bls_rows)
        assert isinstance(rows[0]["ingested_at"], datetime.datetime)
        assert rows[0]["ingested_at"].tzinfo is not None

    def test_source_metadata_dropped(self, bronze_row, bls_rows):
        rows = transform_rows([bronze_row], bls_rows)
        assert "source_url" not in rows[0]
        assert "source_method" not in rows[0]
        assert "median_pay_annual" not in rows[0]
        assert "entry_education" not in rows[0]

    def test_temp_fields_removed(self, bronze_row, bls_rows):
        rows = transform_rows([bronze_row], bls_rows)
        assert "_num_jobs_2024" not in rows[0]

    def test_broad_code_expands(self, broad_soc_row, bls_rows):
        rows = transform_rows([broad_soc_row], bls_rows)
        soc_codes = {r["soc_code"] for r in rows}
        assert soc_codes == {"17-3011", "17-3012", "17-3013", "17-3019"}
        for row in rows:
            assert row["soc_resolved_method"] == "broad_expansion"
            assert row["bls_match"] is True
            assert row["slug"] == "drafters"
            assert row["exposure_score"] == 9

    def test_broad_to_broad_exact_match(self, bls_rows):
        """Broad code 13-2020 exists in BLS as a broad code -> direct match."""
        bronze = {
            "slug": "property-appraisers",
            "occupation_title": "Property appraisers and assessors",
            "category": "business-and-financial",
            "soc_code": "13-2020",
            "exposure_score": 6,
            "rationale": "x" * 300,
            "num_jobs_2024": 100000,
            "load_date": datetime.date(2026, 4, 9),
        }
        rows = transform_rows([bronze], bls_rows)
        assert len(rows) == 1
        assert rows[0]["soc_code"] == "13-2020"
        assert rows[0]["soc_resolved_method"] == "direct"
        assert rows[0]["bls_match"] is True

    def test_unmatched_broad_code_marked_unresolved(self, bls_rows):
        """Broad code with no BLS match at all -> unresolved."""
        bronze = {
            "slug": "grounds-maintenance-workers",
            "occupation_title": "Grounds maintenance workers",
            "category": "building-and-grounds",
            "soc_code": "37-3000",
            "exposure_score": 1,
            "rationale": "x" * 300,
            "num_jobs_2024": 50000,
            "load_date": datetime.date(2026, 4, 9),
        }
        rows = transform_rows([bronze], bls_rows)
        assert len(rows) == 1
        assert rows[0]["soc_code"] == "37-3000"
        assert rows[0]["bls_match"] is False
        assert rows[0]["soc_resolved_method"] == "unresolved"

    def test_null_soc_title_match(self, null_soc_row, bls_rows):
        """Null SOC resolves via title matching."""
        rows = transform_rows([null_soc_row], bls_rows)
        soc_codes = {r["soc_code"] for r in rows}
        # Should match nurse anesthetists, midwives, practitioners
        assert "29-1151" in soc_codes
        assert "29-1161" in soc_codes
        assert "29-1171" in soc_codes
        for row in rows:
            assert row["soc_resolved_method"] == "title_match"

    def test_null_soc_no_match_stays_unresolved(self, bls_rows):
        """Null SOC with no title match -> unresolved."""
        bronze = {
            "slug": "military-careers",
            "occupation_title": "Military careers",
            "category": "military",
            "soc_code": None,
            "exposure_score": 3,
            "rationale": "x" * 300,
            "num_jobs_2024": None,
            "load_date": datetime.date(2026, 4, 9),
        }
        rows = transform_rows([bronze], bls_rows)
        assert len(rows) == 1
        assert rows[0]["soc_code"] is None
        assert rows[0]["soc_resolved_method"] == "unresolved"
        assert rows[0]["bls_match"] is False

    def test_null_soc_uses_slug_for_record_id(self, bls_rows):
        """Unresolved null SOC should use slug for grain hash."""
        bronze = {
            "slug": "military-careers",
            "occupation_title": "Military careers",
            "category": "military",
            "soc_code": None,
            "exposure_score": 3,
            "rationale": "x" * 300,
            "num_jobs_2024": None,
            "load_date": datetime.date(2026, 4, 9),
        }
        rows = transform_rows([bronze], bls_rows)
        assert rows[0]["record_id"].startswith("kai-")
        # Verify it uses slug not soc_code
        from brightsmith.infra.grain import compute_grain_id
        expected_id = compute_grain_id({"slug": "military-careers"}, ["slug"], prefix="kai")
        assert rows[0]["record_id"] == expected_id

    def test_direct_no_bls_match(self, bls_rows):
        """Detailed SOC code not in BLS -> bls_match = False."""
        bronze = {
            "slug": "test-occupation",
            "occupation_title": "Test occupation",
            "category": "test",
            "soc_code": "99-9999",
            "exposure_score": 5,
            "rationale": "x" * 300,
            "num_jobs_2024": 10000,
            "load_date": datetime.date(2026, 4, 9),
        }
        rows = transform_rows([bronze], bls_rows)
        assert len(rows) == 1
        assert rows[0]["bls_match"] is False
        assert rows[0]["soc_resolved_method"] == "direct"


# ---------------------------------------------------------------------------
# TestDedup
# ---------------------------------------------------------------------------

class TestDedup:
    """Tests for post-expansion deduplication."""

    def test_no_duplicates_no_change(self):
        rows = [
            {"soc_code": "13-2051", "slug": "a", "_num_jobs_2024": 100},
            {"soc_code": "15-1252", "slug": "b", "_num_jobs_2024": 200},
        ]
        result = _dedup_by_soc_code(rows)
        assert len(result) == 2

    def test_duplicate_keeps_highest_num_jobs(self):
        rows = [
            {"soc_code": "13-2051", "slug": "a", "_num_jobs_2024": 100},
            {"soc_code": "13-2051", "slug": "b", "_num_jobs_2024": 500},
        ]
        result = _dedup_by_soc_code(rows)
        assert len(result) == 1
        assert result[0]["slug"] == "b"

    def test_duplicate_ties_broken_by_slug_alpha(self):
        rows = [
            {"soc_code": "13-2051", "slug": "zzz", "_num_jobs_2024": 100},
            {"soc_code": "13-2051", "slug": "aaa", "_num_jobs_2024": 100},
        ]
        result = _dedup_by_soc_code(rows)
        assert len(result) == 1
        assert result[0]["slug"] == "aaa"

    def test_null_soc_not_deduped(self):
        rows = [
            {"soc_code": None, "slug": "a", "_num_jobs_2024": 100},
            {"soc_code": None, "slug": "b", "_num_jobs_2024": 200},
        ]
        result = _dedup_by_soc_code(rows)
        assert len(result) == 2

    def test_null_num_jobs_treated_as_zero(self):
        rows = [
            {"soc_code": "13-2051", "slug": "a", "_num_jobs_2024": None},
            {"soc_code": "13-2051", "slug": "b", "_num_jobs_2024": 50},
        ]
        result = _dedup_by_soc_code(rows)
        assert len(result) == 1
        assert result[0]["slug"] == "b"


# ---------------------------------------------------------------------------
# TestSilverSchema
# ---------------------------------------------------------------------------

class TestSilverSchema:
    """Tests for the Silver Iceberg schema."""

    def test_schema_field_count(self):
        schema = get_silver_schema()
        assert len(schema.fields) == 11

    def test_required_fields(self):
        schema = get_silver_schema()
        required = {f.name for f in schema.fields if f.required}
        expected_required = {
            "record_id", "slug", "occupation_title", "category",
            "exposure_score", "rationale", "bls_match",
            "soc_resolved_method", "source_load_date", "ingested_at",
        }
        assert expected_required == required

    def test_nullable_fields(self):
        schema = get_silver_schema()
        nullable = {f.name for f in schema.fields if not f.required}
        assert nullable == {"soc_code"}

    def test_soc_code_is_nullable(self):
        schema = get_silver_schema()
        soc_field = next(f for f in schema.fields if f.name == "soc_code")
        assert not soc_field.required


# ---------------------------------------------------------------------------
# TestSocWhitespace
# ---------------------------------------------------------------------------

class TestSocWhitespace:
    """Test that SOC codes with whitespace are properly handled."""

    def test_trailing_whitespace_stripped(self, bls_rows):
        bronze = {
            "slug": "financial-analysts",
            "occupation_title": "Financial analysts",
            "category": "business-and-financial",
            "soc_code": "13-2051 ",
            "exposure_score": 8,
            "rationale": "x" * 300,
            "num_jobs_2024": 328600,
            "load_date": datetime.date(2026, 4, 9),
        }
        rows = transform_rows([bronze], bls_rows)
        assert rows[0]["soc_code"] == "13-2051"

    def test_leading_whitespace_stripped(self, bls_rows):
        bronze = {
            "slug": "financial-analysts",
            "occupation_title": "Financial analysts",
            "category": "business-and-financial",
            "soc_code": " 13-2051",
            "exposure_score": 8,
            "rationale": "x" * 300,
            "num_jobs_2024": 328600,
            "load_date": datetime.date(2026, 4, 9),
        }
        rows = transform_rows([bronze], bls_rows)
        assert rows[0]["soc_code"] == "13-2051"
